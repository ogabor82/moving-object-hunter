"""AS-034: bright/saturated-star contamination as magnitude × distance.

Research/characterisation only — no filter, exclusion radius, score, rank,
threshold, rejection rule or candidate policy is derived here. UNKNOWN is
not a ground-truth false positive; KNOWN is a small, selected population.

Everything in the PRE-REGISTRATION block below was fixed and committed
before any evidence of this ticket was computed.

    python -m app.validation.star_contamination select \\
        --out validation/results/as034/as034_population.json
    python -m app.validation.star_contamination evidence \\
        --population validation/results/as034/as034_population.json \\
        --out-dir validation/results/as034
"""

import argparse
import math
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path

import httpx
from pydantic import BaseModel

from app.services.ztf_service import (
    METADATA_COLUMNS,
    ZTF_SCIENCE_METADATA_URL,
    ZTFServiceError,
)
from app.validation.bright_stars import FieldSelection, products_available
from app.validation.models import ValidationField
from app.validation.presets import AS022_REPORT
from app.validation.runner import ValidationReport


# ---------------------------------------------------------------------------
# PRE-REGISTRATION (AS-034, 2026-10-01; committed before any evidence run)
# ---------------------------------------------------------------------------

# Stars: Tycho-2 (VizieR I/259/tyc2) with the AS-033 V estimate
# V = VT - 0.090 (BT - VT) (V = VT without BT; no VT -> no magnitude, not
# used). V <= 11 keeps the range where Tycho-2 is close to complete and
# which covers stars saturated in a 30 s ZTF exposure; no star is treated
# as "clean" because it is fainter than 6.5.
STAR_V_MAX = 11.0
STAR_QUERY_MAX_VT = 11.5
STAR_CONE_MARGIN_ARCSEC = 900.0
# Magnitude classes: fixed 2-mag steps (open-ended at the bright end).
MAG_EDGES = (-math.inf, 4.0, 6.0, 8.0, 10.0, STAR_V_MAX)
# Distance annuli around each star [arcsec]: doubling widths; the last one
# (480"-900") is the local background of the same stars. Not derived from
# the AS-032/033 measurements.
ANNULUS_EDGES = (0.0, 15.0, 30.0, 60.0, 120.0, 240.0, 480.0, 900.0)
BACKGROUND_ANNULUS = len(ANNULUS_EDGES) - 2
# Primary profiles use isolated stars: no brighter (smaller V) Tycho-2
# star within 900". Profiles over all stars are reported too.
ISOLATION_ARCSEC = 900.0
# Annulus area inside the quadrant: polar sampling around each star.
AREA_RADIAL_STEPS = 24
AREA_ANGULAR_STEPS = 360

# Population: the eight AS-022/AS-033 fields, plus the three sibling
# quadrants (same exposures, same CCD) of each field that was selected
# around a bright star (B, D, S1-S4). A sibling is used only if all three
# exposures have an archived PSF catalog and science image (AS-033
# amendment 1). No pipeline output is consulted.
SIBLING_PARENTS = (
    "B-2019-01-25-565-c13-q3",
    "D-2019-06-02-281-c16-q3",
    "S1-2018-09-19-508-c10-q4",
    "S2-2018-09-27-509-c14-q4",
    "S3-2019-07-01-335-c7-q1",
    "S4-2018-11-07-615-c5-q3",
)
AS033_FIELDS = AS022_REPORT.parent / "as033" / "as033_fields.json"

# KNOWN objects searched near stars: every object the AS-022 target rule
# (TargetSelectionRule defaults: in every frame and footprint, position
# error <= 1", V <= faintest maglimit + 0.5) accepts in each field —
# primary and marginal alike. Their predicted positions, not pipeline
# output, decide their proximity.

# Visual sample (strips, SHA-256 order of '<salt>:<field>:<id>'):
VISUAL_SALT = "AS-034"
VISUAL_KNOWN_NEAR_ARCSEC = 120.0  # KNOWN with a V <= 10 star this close
VISUAL_KNOWN_MAX = 12
VISUAL_UNKNOWN_NEAR_ARCSEC = 60.0  # built UNKNOWN near a 6 <= V <= 11 star
VISUAL_UNKNOWN_PER_CLASS = 3
VISUAL_BACKGROUND_FAR_ARCSEC = 240.0  # built UNKNOWN with no V <= 11 star
VISUAL_BACKGROUND_MAX = 4

PREREGISTRATION = (
    "Stars: Tycho-2, V = VT - 0.090 (BT - VT), V <= 11. Magnitude classes "
    '<4, 4-6, 6-8, 8-10, 10-11. Annuli 0-15-30-60-120-240-480" around each '
    'star, 480-900" = local background of the same stars; primary profiles '
    'use isolated stars (no brighter Tycho-2 star within 900"), all-star '
    "profiles reported too. Population: POC, B, C, D (AS-022), S1-S4 "
    "(AS-033) and the three sibling quadrants (same exposures and CCD) of "
    "B, D, S1-S4 with archived products. KNOWN: all objects passing the "
    "AS-022 target rule (primary + marginal), proximity from predicted "
    "positions, loss stage from the AS-022 outcome logic. Visual: up to 12 "
    'KNOWN within 120" of a V <= 10 star; 3 built UNKNOWN within 60" of a '
    "star per class 6-8, 8-10, 10-11; 4 built UNKNOWN with no V <= 11 star "
    'within 240"; SHA-256 order. No outcome was looked at.'
)


class PopulationField(BaseModel):
    field: ValidationField
    origin: str  # AS-022 | AS-033 | sibling of <field id>
    skybot: str  # AS-022 snapshot | AS-033 snapshot | live (stored)


class Population(BaseModel):
    generated_at: datetime
    preregistration: str
    fields: list[PopulationField]
    log: list[str]


def _metadata_rows(where: str, client: httpx.Client | None) -> list[dict[str, str]]:
    import csv
    from io import StringIO

    request = client.get if client is not None else httpx.get
    response = request(
        ZTF_SCIENCE_METADATA_URL,
        params={
            "WHERE": where,
            "COLUMNS": ",".join((*METADATA_COLUMNS, "expid")),
            "ct": "csv",
        },
        timeout=120.0,
    )
    if not response.is_success:
        raise ZTFServiceError(f"IRSA metadata HTTP {response.status_code}")
    return list(csv.DictReader(StringIO(response.text)))


def sibling_sequences(
    rows: Sequence[dict[str, str]],
) -> dict[int, list[dict[str, str]]]:
    """Sibling-quadrant rows grouped by quadrant id, each in exposure order."""
    by_quadrant: dict[int, list[dict[str, str]]] = {}
    for row in rows:
        by_quadrant.setdefault(int(row["qid"]), []).append(row)
    return {
        qid: sorted(group, key=lambda r: (float(r["obsjd"]), int(r["pid"])))
        for qid, group in sorted(by_quadrant.items())
    }


def build_population(
    client: httpx.Client | None = None,
    metadata: Callable[[str, httpx.Client | None], list[dict[str, str]]] = (
        _metadata_rows
    ),
    available: Callable[..., bool] = products_available,
) -> Population:
    report = ValidationReport.model_validate_json(AS022_REPORT.read_text())
    selection = FieldSelection.model_validate_json(AS033_FIELDS.read_text())
    fields = [
        PopulationField(field=s.field, origin="AS-022", skybot="AS-022 snapshot")
        for s in report.snapshots
    ] + [
        PopulationField(field=s.field, origin="AS-033", skybot="AS-033 snapshot")
        for s in selection.fields
    ]
    by_id = {f.field.field_id: f.field for f in fields}
    log = []
    for parent_id in SIBLING_PARENTS:
        parent = by_id[parent_id]
        own = metadata(
            "pid IN (" + ",".join(map(str, parent.product_ids)) + ")", client
        )
        expids = sorted({int(r["expid"]) for r in own})
        ccd = int(own[0]["ccdid"])
        own_qid = int(own[0]["qid"])
        rows = metadata(
            "expid IN (" + ",".join(map(str, expids)) + f") AND ccdid = {ccd}",
            client,
        )
        for qid, sequence in sibling_sequences(rows).items():
            if qid == own_qid:
                continue
            if len(sequence) != len(expids):
                log.append(f"{parent_id} q{qid}: {len(sequence)} exposures, skipped")
                continue
            if not available(sequence, client):
                log.append(f"{parent_id} q{qid}: products missing, skipped")
                continue
            field_id = f"{parent_id.split('-q')[0]}-q{qid}"
            fields.append(
                PopulationField(
                    field=ValidationField(
                        field_id=field_id,
                        description=f"AS-034 sibling quadrant of {parent_id}",
                        product_ids=[int(r["pid"]) for r in sequence],
                        selection_note=PREREGISTRATION,
                    ),
                    origin=f"sibling of {parent_id}",
                    skybot="live (stored in as034_skybot.json)",
                )
            )
            log.append(f"{parent_id} q{qid}: added as {field_id}")
    return Population(
        generated_at=datetime.now(timezone.utc),
        preregistration=PREREGISTRATION,
        fields=fields,
        log=log,
    )


# ---------------------------------------------------------------------------
# Evidence (written after the pre-registration commit)
# ---------------------------------------------------------------------------


def magnitude_class(v_mag: float | None) -> int | None:
    """Index of the magnitude class [edge_i, edge_i+1], V <= 11 only."""
    if v_mag is None or v_mag > STAR_V_MAX:
        return None
    for index in range(len(MAG_EDGES) - 1):
        if v_mag < MAG_EDGES[index + 1] or index == len(MAG_EDGES) - 2:
            return index
    return None


def class_label(index: int) -> str:
    low, high = MAG_EDGES[index], MAG_EDGES[index + 1]
    return (
        f"V<{high:g}"
        if math.isinf(low)
        else (
            f"{low:g}<=V<{high:g}"
            if index < len(MAG_EDGES) - 2
            else f"{low:g}<=V<={high:g}"
        )
    )


def annulus_index(separation: float) -> int | None:
    for index in range(len(ANNULUS_EDGES) - 1):
        if ANNULUS_EDGES[index] <= separation < ANNULUS_EDGES[index + 1]:
            return index
    return None


def annulus_label(index: int) -> str:
    return f'{ANNULUS_EDGES[index]:g}-{ANNULUS_EDGES[index + 1]:g}"'


class Star(BaseModel):
    tycho_id: str
    ra: float
    dec: float
    v_mag: float
    mag_class: int
    isolated: bool
    in_footprint: bool


class StarProximity(BaseModel):
    """Explicit proximity features of one sky position (AS-034).

    `separation_by_class[c]`: great-circle distance [arcsec] to the nearest
    Tycho-2 star of magnitude class c (MAG_EDGES), null when the field's
    star cone has none. `nearest_*`: the nearest star with V <= 11.
    """

    separation_by_class: list[float | None]
    nearest_separation_arcsec: float | None
    nearest_v_mag: float | None


def star_proximity(ra: float, dec: float, stars: Sequence[Star]) -> StarProximity:
    from app.services.astrometry import angular_distance_arcsec

    by_class: list[float | None] = [None] * (len(MAG_EDGES) - 1)
    nearest: tuple[float, float] | None = None
    for star in stars:
        separation = angular_distance_arcsec(ra, dec, star.ra, star.dec)
        current = by_class[star.mag_class]
        if current is None or separation < current:
            by_class[star.mag_class] = separation
        if nearest is None or separation < nearest[0]:
            nearest = (separation, star.v_mag)
    return StarProximity(
        separation_by_class=[None if v is None else round(v, 2) for v in by_class],
        nearest_separation_arcsec=None if nearest is None else round(nearest[0], 2),
        nearest_v_mag=None if nearest is None else nearest[1],
    )


def field_stars(metadata, client=None) -> tuple[str, list[Star]]:
    """Tycho-2 stars with V <= 11 in the footprint's circle + 15'."""
    import numpy

    from app.services.astrometry import angular_distance_arcsec
    from app.validation.bright_stars import _mean, query_tycho

    corners = metadata[0].corners
    ra0, dec0 = _mean(list(corners))
    radius = max(angular_distance_arcsec(ra0, dec0, ra, dec) for ra, dec in corners)
    url, catalog = query_tycho(
        {
            "-c": f"{ra0:.6f} {dec0:+.6f}",
            "-c.rd": f"{(radius + STAR_CONE_MARGIN_ARCSEC) / 3600.0:.4f}",
            "VTmag": f"<{STAR_QUERY_MAX_VT}",
        },
        client,
    )
    usable = sorted(
        (t for t in catalog if magnitude_class(t.v_mag) is not None),
        key=lambda t: t.tycho_id,
    )
    ras = numpy.array([t.ra for t in usable])
    decs = numpy.array([t.dec for t in usable])
    inside = footprint_mask(ras, decs, corners) if usable else numpy.array([])
    stars = []
    for index, t in enumerate(usable):
        separations = _haversine(t.ra, t.dec, ras, decs)
        brighter_near = (separations < ISOLATION_ARCSEC) & (
            numpy.array([u.v_mag for u in usable]) < t.v_mag
        )
        brighter_near[index] = False
        stars.append(
            Star(
                tycho_id=t.tycho_id,
                ra=t.ra,
                dec=t.dec,
                v_mag=round(t.v_mag, 3),
                mag_class=magnitude_class(t.v_mag),
                isolated=not bool(brighter_near.any()),
                in_footprint=bool(inside[index]),
            )
        )
    return url, stars


def _haversine(ra, dec, ras, decs):
    import numpy

    ra1, dec1 = numpy.radians(ra), numpy.radians(dec)
    ra2, dec2 = numpy.radians(ras), numpy.radians(decs)
    h = (
        numpy.sin((dec2 - dec1) / 2) ** 2
        + numpy.cos(dec1) * numpy.cos(dec2) * numpy.sin((ra2 - ra1) / 2) ** 2
    )
    return numpy.degrees(2 * numpy.arcsin(numpy.sqrt(numpy.clip(h, 0, 1)))) * 3600.0


def footprint_mask(ras, decs, corners):
    """Vectorised point-in-quadrant test in the tangent plane."""
    import numpy

    from app.validation.bright_stars import _gnomonic, _mean

    ra0, dec0 = _mean(list(corners))
    cx, cy = _gnomonic(
        numpy.array([c[0] for c in corners]),
        numpy.array([c[1] for c in corners]),
        ra0,
        dec0,
    )
    polygon = numpy.column_stack([cx, cy])
    center = polygon.mean(axis=0)
    polygon = polygon[
        numpy.argsort(
            numpy.arctan2(polygon[:, 1] - center[1], polygon[:, 0] - center[0])
        )
    ]
    x, y = _gnomonic(numpy.asarray(ras, float), numpy.asarray(decs, float), ra0, dec0)
    inside = numpy.zeros(numpy.shape(x), dtype=bool)
    for k in range(len(polygon)):
        x1, y1 = polygon[k]
        x2, y2 = polygon[(k + 1) % len(polygon)]
        with numpy.errstate(divide="ignore", invalid="ignore"):
            at = (x2 - x1) * (y - y1) / (y2 - y1) + x1
        inside ^= ((y1 > y) != (y2 > y)) & (x < at)
    return inside


def annulus_areas(star: Star, corners) -> list[float]:
    """Area [arcmin²] of each annulus around the star inside the quadrant,
    from a polar sample (fraction inside × exact annulus area)."""
    import numpy

    areas = []
    angles = numpy.linspace(0, 2 * numpy.pi, AREA_ANGULAR_STEPS, endpoint=False)
    for index in range(len(ANNULUS_EDGES) - 1):
        r1, r2 = ANNULUS_EDGES[index], ANNULUS_EDGES[index + 1]
        # Radii at equal-area steps, so each sample covers the same area.
        steps = (numpy.arange(AREA_RADIAL_STEPS) + 0.5) / AREA_RADIAL_STEPS
        radii = numpy.sqrt(r1**2 + steps * (r2**2 - r1**2))
        rr, aa = numpy.meshgrid(radii, angles)
        # Offsets on the sphere: small-angle destination point.
        dec = star.dec + (rr * numpy.cos(aa)) / 3600.0
        ra = star.ra + (rr * numpy.sin(aa)) / 3600.0 / math.cos(math.radians(star.dec))
        fraction = footprint_mask(ra.ravel(), dec.ravel(), corners).mean()
        areas.append(float(fraction * math.pi * (r2**2 - r1**2) / 3600.0))
    return areas


class Cell(BaseModel):
    """One (magnitude class, annulus) cell, summed over stars."""

    stars: int
    area_arcmin2: float
    unknown_built: int
    unknown_rejected: int
    known_built: int
    unknown_by_mask: dict[str, int]
    unknown_halo_bit: int
    unknown_sharp_max: list[float]
    unknown_min_snr: list[float]
    unknown_fit_rms: list[float]


def empty_cell() -> Cell:
    return Cell(
        stars=0,
        area_arcmin2=0.0,
        unknown_built=0,
        unknown_rejected=0,
        known_built=0,
        unknown_by_mask={"unmasked": 0, "partially_masked": 0, "all_masked": 0},
        unknown_halo_bit=0,
        unknown_sharp_max=[],
        unknown_min_snr=[],
        unknown_fit_rms=[],
    )


class TrackletRow(BaseModel):
    """What the profiles need of one tracklet (no outcome judgement)."""

    tracklet_id: str
    ra: float
    dec: float
    group: str  # unknown_built | unknown_rejected | known_built | other
    mask_state: str
    halo_bit_all: bool
    sharp_max: float | None
    min_snr: float
    fit_rms: float


def accumulate(
    cells: dict[tuple[int, bool, int], Cell],
    stars: Sequence[Star],
    rows: Sequence[TrackletRow],
    corners,
) -> None:
    """Add every (star, tracklet) pair within 900" to its cell; a tracklet
    near several stars counts once per star (stacked profiles)."""
    import numpy

    ras = numpy.array([r.ra for r in rows])
    decs = numpy.array([r.dec for r in rows])
    for star in stars:
        areas = annulus_areas(star, corners)
        if sum(areas) == 0.0:
            continue
        separations = (
            _haversine(star.ra, star.dec, ras, decs) if rows else numpy.array([])
        )
        for scope in (True, False):  # isolated-only, all stars
            if scope and not star.isolated:
                continue
            for index, area in enumerate(areas):
                cell = cells.setdefault((star.mag_class, scope, index), empty_cell())
                cell.stars += 1
                cell.area_arcmin2 += area
            for row_index in numpy.nonzero(separations < ANNULUS_EDGES[-1])[0]:
                row = rows[row_index]
                cell = cells[
                    (
                        star.mag_class,
                        scope,
                        annulus_index(float(separations[row_index])),
                    )
                ]
                if row.group == "unknown_built":
                    cell.unknown_built += 1
                    cell.unknown_by_mask[row.mask_state] += 1
                    cell.unknown_halo_bit += row.halo_bit_all
                    if row.sharp_max is not None:
                        cell.unknown_sharp_max.append(row.sharp_max)
                    cell.unknown_min_snr.append(row.min_snr)
                    cell.unknown_fit_rms.append(row.fit_rms)
                elif row.group == "unknown_rejected":
                    cell.unknown_rejected += 1
                elif row.group == "known_built":
                    cell.known_built += 1


class KnownRecord(BaseModel):
    field_id: str
    designation: str
    role: str  # primary | marginal (AS-022 rule)
    v_magnitude: float
    predicted_positions: list[tuple[float, float]]
    proximity: StarProximity  # minimum over the three predicted positions
    detected_frames: int
    candidate_frames: int
    recovered: bool
    identification_status: str | None
    tracklet_status: str | None
    loss_stage: (
        str  # recovered | not_detected | not_candidate | not_linked | not_identified
    )


def loss_stage(outcome) -> str:
    if outcome.recovered:
        return "recovered"
    if outcome.detected_frames < 3:
        return "not_detected"
    if outcome.candidate_frames < 3:
        return "not_candidate"
    if outcome.tracklet_id is None:
        return "not_linked"
    return "not_identified"


def min_proximity(positions, stars) -> StarProximity:
    each = [star_proximity(ra, dec, stars) for ra, dec in positions]

    def smallest(values):
        values = [v for v in values if v is not None]
        return min(values) if values else None

    nearest = min(
        (p for p in each if p.nearest_separation_arcsec is not None),
        key=lambda p: p.nearest_separation_arcsec,
        default=None,
    )
    return StarProximity(
        separation_by_class=[
            smallest(p.separation_by_class[c] for p in each)
            for c in range(len(MAG_EDGES) - 1)
        ],
        nearest_separation_arcsec=(
            None if nearest is None else nearest.nearest_separation_arcsec
        ),
        nearest_v_mag=None if nearest is None else nearest.nearest_v_mag,
    )


class FieldConditions(BaseModel):
    field_id: str
    origin: str
    skybot: str
    filters: list[str]
    minutes_from_first: list[float]
    sources_per_frame: list[int]
    maglimit_per_frame: list[float]
    seeing_per_frame: list[float]
    stars_per_class: list[int]
    stars_in_footprint_per_class: list[int]
    tracklets: int
    unknown_built: int
    known_built: int
    tycho_query: str


class Strip(BaseModel):
    field_id: str
    item_id: str
    group: str
    image: str
    proximity: StarProximity
    note: str


def visual_key(field_id: str, item_id: str) -> str:
    import hashlib

    return hashlib.sha256(f"{VISUAL_SALT}:{field_id}:{item_id}".encode()).hexdigest()


def pick_visual(
    known: Sequence[KnownRecord],
    unknown: Sequence[tuple[str, str, StarProximity]],
) -> tuple[list[KnownRecord], list[tuple[str, str, str, StarProximity]]]:
    """Pre-registered strip sample. `unknown`: (field, tracklet, proximity)
    of built UNKNOWN tracklets."""
    near_known = [
        k
        for k in known
        if any(
            s is not None and s < VISUAL_KNOWN_NEAR_ARCSEC
            for s in k.proximity.separation_by_class[:4]  # classes up to V < 10
        )
    ]
    near_known = sorted(
        near_known, key=lambda k: visual_key(k.field_id, k.designation)
    )[:VISUAL_KNOWN_MAX]
    picks: list[tuple[str, str, str, StarProximity]] = []
    for mag_class in (2, 3, 4):  # 6-8, 8-10, 10-11
        near = [
            u
            for u in unknown
            if u[2].separation_by_class[mag_class] is not None
            and u[2].separation_by_class[mag_class] < VISUAL_UNKNOWN_NEAR_ARCSEC
        ]
        near.sort(key=lambda u: visual_key(u[0], u[1]))
        picks += [
            (f"unknown_near_{class_label(mag_class)}", *u)
            for u in near[:VISUAL_UNKNOWN_PER_CLASS]
        ]
    far = [
        u
        for u in unknown
        if u[2].nearest_separation_arcsec is None
        or u[2].nearest_separation_arcsec >= VISUAL_BACKGROUND_FAR_ARCSEC
    ]
    far.sort(key=lambda u: visual_key(u[0], u[1]))
    picks += [("unknown_background", *u) for u in far[:VISUAL_BACKGROUND_MAX]]
    return near_known, picks


class Summary(BaseModel):
    count: int
    median: float | None
    p25: float | None
    p75: float | None


def summarise(values: Sequence[float]) -> Summary:
    import statistics

    values = sorted(values)
    if not values:
        return Summary(count=0, median=None, p25=None, p75=None)
    if len(values) == 1:
        return Summary(count=1, median=values[0], p25=values[0], p75=values[0])
    q = statistics.quantiles(values, n=4, method="inclusive")
    return Summary(
        count=len(values), median=statistics.median(values), p25=q[0], p75=q[2]
    )


class CellOut(BaseModel):
    stars: int
    area_arcmin2: float
    unknown_built: int
    unknown_rejected: int
    known_built: int
    unknown_by_mask: dict[str, int]
    unknown_halo_bit: int
    unknown_sharp_max: Summary
    unknown_min_snr: Summary
    unknown_fit_rms: Summary


def cell_out(cell: Cell) -> CellOut:
    return CellOut(
        stars=cell.stars,
        area_arcmin2=round(cell.area_arcmin2, 4),
        unknown_built=cell.unknown_built,
        unknown_rejected=cell.unknown_rejected,
        known_built=cell.known_built,
        unknown_by_mask=cell.unknown_by_mask,
        unknown_halo_bit=cell.unknown_halo_bit,
        unknown_sharp_max=summarise(cell.unknown_sharp_max),
        unknown_min_snr=summarise(cell.unknown_min_snr),
        unknown_fit_rms=summarise(cell.unknown_fit_rms),
    )


class Evidence(BaseModel):
    generated_at: datetime
    preregistration: str
    fields: list[FieldConditions]
    cells: dict[str, CellOut]  # "<field>|<class>|<isolated|all>|<annulus>", "ALL|..."
    known: list[KnownRecord]
    strips: list[Strip]


def cell_key(field: str, mag_class: int, isolated: bool, annulus: int) -> str:
    return f"{field}|{mag_class}|{'isolated' if isolated else 'all'}|{annulus}"


def run_evidence(
    population: Population,
    out_dir: Path,
    progress: Callable[[str], None] = lambda message: None,
) -> Evidence:
    import json

    from fastapi.testclient import TestClient

    from app.main import app
    from app.models.identification import IdentificationStatus
    from app.models.known_object import KnownObjectField
    from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG as CONFIG
    from app.models.tracklet import TrackletStatus
    from app.services.identification_service import match_tracklets_to_known_objects
    from app.services.pipeline_service import build_tracklets_from_frames
    from app.services.quality_service import extract_quality_features
    from app.validation.bright_stars import _mean
    from app.validation.data import (
        fetch_frame_metadata,
        load_catalog_frames,
        query_skybot_fields,
    )
    from app.validation.evaluate import _target_outcome
    from app.validation.masked import render_strip, strip_geometry, write_png
    from app.validation.models import TargetSelectionRule
    from app.validation.selection import select_targets

    report = ValidationReport.model_validate_json(AS022_REPORT.read_text())
    frozen = {s.field.field_id: s for s in report.snapshots}
    as033_skybot = json.loads((AS033_FIELDS.parent / "as033_skybot.json").read_text())
    skybot_path = out_dir / "as034_skybot.json"
    stored = json.loads(skybot_path.read_text()) if skybot_path.exists() else {}

    client = TestClient(app)
    (out_dir / "strips").mkdir(parents=True, exist_ok=True)
    conditions, known, strips_out = [], [], []
    cells: dict[str, Cell] = {}
    unknown_proximity: list[tuple[str, str, StarProximity]] = []
    strip_sources: dict[str, dict] = {}

    for entry in population.fields:
        field = entry.field
        progress(f"{field.field_id}: loading")
        if field.field_id in frozen:
            snapshot = frozen[field.field_id]
            observations, metadata = snapshot.observations, snapshot.frame_metadata
            skybot = snapshot.skybot_fields
        else:
            observations, metadata = fetch_frame_metadata(field.product_ids)
            if field.field_id in as033_skybot:
                raw = as033_skybot[field.field_id]
            elif field.field_id in stored:
                raw = stored[field.field_id]
            else:
                skybot_live = query_skybot_fields(observations, metadata)
                raw = [f.model_dump(mode="json") for f in skybot_live]
                stored[field.field_id] = raw
                skybot_path.write_text(json.dumps(stored) + "\n")
            skybot = [KnownObjectField.model_validate(f) for f in raw]
        catalogs = load_catalog_frames(observations)
        progress(f"{field.field_id}: pipeline")
        pipeline = build_tracklets_from_frames(catalogs.frames, CONFIG)
        tracklets = pipeline.build.tracklets
        identifications = match_tracklets_to_known_objects(
            tracklets,
            {o.product_id: f for o, f in zip(observations, skybot)},
            CONFIG.identification(),
        ).identifications
        url, stars = field_stars(metadata)

        rows = []
        by_id = {}
        for tracklet, identification in zip(tracklets, identifications):
            features = extract_quality_features(tracklet, catalogs.sharp_by_source_id)
            ra, dec = _mean(
                [(i.detection.ra, i.detection.dec) for i in tracklet.detections]
            )
            built = tracklet.status is TrackletStatus.TRACKLET_BUILT
            status = identification.status
            group = (
                "known_built"
                if built and status is IdentificationStatus.KNOWN
                else (
                    "unknown_built"
                    if built and status is IdentificationStatus.UNKNOWN
                    else (
                        "unknown_rejected"
                        if status is IdentificationStatus.UNKNOWN
                        else "other"
                    )
                )
            )
            masked = features.masked_detection_count
            rows.append(
                TrackletRow(
                    tracklet_id=tracklet.tracklet_id,
                    ra=ra,
                    dec=dec,
                    group=group,
                    mask_state=(
                        "unmasked"
                        if masked == 0
                        else (
                            "all_masked"
                            if masked == features.detection_count
                            else "partially_masked"
                        )
                    ),
                    halo_bit_all=all(
                        i.detection.mask_bits >> 12 & 1 for i in tracklet.detections
                    ),
                    sharp_max=features.sharp_max,
                    min_snr=features.min_snr,
                    fit_rms=features.fit_rms_residual_arcsec,
                )
            )
            if group == "unknown_built":
                by_id[tracklet.tracklet_id] = tracklet
        progress(
            f"{field.field_id}: profiles ({len(stars)} stars, {len(rows)} tracklets)"
        )
        local: dict[tuple[int, bool, int], Cell] = {}
        accumulate(local, stars, rows, metadata[0].corners)
        for (mag_class, isolated, annulus), cell in local.items():
            cells[cell_key(field.field_id, mag_class, isolated, annulus)] = cell
            pooled = cells.setdefault(
                cell_key("ALL", mag_class, isolated, annulus), empty_cell()
            )
            _merge(pooled, cell)

        unknown_rows = [r for r in rows if r.group == "unknown_built"]
        for r in unknown_rows:
            unknown_proximity.append(
                (field.field_id, r.tracklet_id, star_proximity(r.ra, r.dec, stars))
            )
        strip_sources[field.field_id] = {
            "product_ids": [o.product_id for o in observations],
            "tracklets": by_id,
        }

        targets = select_targets(
            field.field_id, metadata, skybot, TargetSelectionRule()
        )
        for target in targets:
            outcome = _target_outcome(
                target,
                catalogs.frames,
                pipeline.candidate_frames,
                tracklets,
                identifications,
                CONFIG,
            )
            known.append(
                KnownRecord(
                    field_id=field.field_id,
                    designation=target.designation,
                    role=target.role,
                    v_magnitude=target.v_magnitude,
                    predicted_positions=target.predicted_positions,
                    proximity=min_proximity(target.predicted_positions, stars),
                    detected_frames=outcome.detected_frames,
                    candidate_frames=outcome.candidate_frames,
                    recovered=outcome.recovered,
                    identification_status=(
                        outcome.identification_status.value
                        if outcome.identification_status
                        else None
                    ),
                    tracklet_status=(
                        outcome.tracklet_status.value
                        if outcome.tracklet_status
                        else None
                    ),
                    loss_stage=loss_stage(outcome),
                )
            )
        conditions.append(
            FieldConditions(
                field_id=field.field_id,
                origin=entry.origin,
                skybot=entry.skybot,
                filters=[o.filter_code for o in observations],
                minutes_from_first=[
                    round(
                        (o.observed_at - observations[0].observed_at).total_seconds()
                        / 60,
                        2,
                    )
                    for o in observations
                ],
                sources_per_frame=[f.source_count for f in catalogs.frames],
                maglimit_per_frame=[m.maglimit for m in metadata],
                seeing_per_frame=[m.seeing_arcsec for m in metadata],
                stars_per_class=[
                    sum(s.mag_class == c for s in stars)
                    for c in range(len(MAG_EDGES) - 1)
                ],
                stars_in_footprint_per_class=[
                    sum(s.mag_class == c and s.in_footprint for s in stars)
                    for c in range(len(MAG_EDGES) - 1)
                ],
                tracklets=len(rows),
                unknown_built=len(unknown_rows),
                known_built=sum(r.group == "known_built" for r in rows),
                tycho_query=url,
            )
        )
        del pipeline, catalogs, tracklets, identifications, rows

    near_known, picks = pick_visual(known, unknown_proximity)
    for record in near_known:
        source = strip_sources[record.field_id]
        progress(f"strip KNOWN {record.designation}")
        image = f"strips/known_{record.field_id.split('-')[0]}_{record.designation.replace(' ', '_')}.png"
        center, size = strip_geometry(record.predicted_positions)
        write_png(
            out_dir / image,
            render_strip(
                client,
                source["product_ids"],
                center,
                size,
                record.predicted_positions,
                [0, 1, 2],
            ),
        )
        strips_out.append(
            Strip(
                field_id=record.field_id,
                item_id=record.designation,
                group="known_near",
                image=image,
                proximity=record.proximity,
                note=f"markers = SkyBoT predicted positions; loss stage {record.loss_stage}",
            )
        )
    for group, field_id, tracklet_id, proximity in picks:
        source = strip_sources[field_id]
        tracklet = source["tracklets"][tracklet_id]
        epochs = {pid: i for i, pid in enumerate(source["product_ids"])}
        positions = [(i.detection.ra, i.detection.dec) for i in tracklet.detections]
        center, size = strip_geometry(positions)
        image = f"strips/{group.replace('<', 'lt').replace('=', '')}_{field_id.split('-')[0]}_{tracklet_id}.png"
        progress(f"strip {group} {field_id} {tracklet_id}")
        write_png(
            out_dir / image,
            render_strip(
                client,
                source["product_ids"],
                center,
                size,
                positions,
                [
                    epochs[i.detection.observation_product_id]
                    for i in tracklet.detections
                ],
            ),
        )
        strips_out.append(
            Strip(
                field_id=field_id,
                item_id=tracklet_id,
                group=group,
                image=image,
                proximity=proximity,
                note="markers = tracklet detections",
            )
        )
    return Evidence(
        generated_at=datetime.now(timezone.utc),
        preregistration=population.preregistration,
        fields=conditions,
        cells={key: cell_out(cell) for key, cell in sorted(cells.items())},
        known=known,
        strips=strips_out,
    )


def _merge(into: Cell, cell: Cell) -> None:
    into.stars += cell.stars
    into.area_arcmin2 += cell.area_arcmin2
    into.unknown_built += cell.unknown_built
    into.unknown_rejected += cell.unknown_rejected
    into.known_built += cell.known_built
    for state, count in cell.unknown_by_mask.items():
        into.unknown_by_mask[state] += count
    into.unknown_halo_bit += cell.unknown_halo_bit
    into.unknown_sharp_max += cell.unknown_sharp_max
    into.unknown_min_snr += cell.unknown_min_snr
    into.unknown_fit_rms += cell.unknown_fit_rms


def excess(
    cells: dict[str, CellOut],
    field: str,
    mag_class: int,
    scope: str,
    annulus: int,
    kind: str = "unknown_built",
) -> tuple[float | None, float | None]:
    """(density /arcmin², ratio to the same stars' 480-900" background)."""
    cell = cells.get(f"{field}|{mag_class}|{scope}|{annulus}")
    background = cells.get(f"{field}|{mag_class}|{scope}|{BACKGROUND_ANNULUS}")
    if cell is None or cell.area_arcmin2 <= 0:
        return None, None
    density = getattr(cell, kind) / cell.area_arcmin2
    if (
        background is None
        or background.area_arcmin2 <= 0
        or getattr(background, kind) == 0
    ):
        return density, None
    return density, density / (getattr(background, kind) / background.area_arcmin2)


def render_markdown(evidence: Evidence, reviews: Sequence) -> str:
    def f(value, digits=2):
        return "–" if value is None else f"{value:.{digits}f}"

    classes = range(len(MAG_EDGES) - 1)
    lines = [
        "# AS-034 bright/saturated-star contamination (generated)",
        "",
        f"Generated {evidence.generated_at:%Y-%m-%d %H:%M UTC}. Descriptive only; "
        "no filter, radius, score, rank or threshold. Interpretation: "
        "`as034_findings.md`.",
        "",
        f"Pre-registration (commit e805002): {evidence.preregistration}",
        "",
        "## Population",
        "",
        '| field | origin | filters | minutes | sources/frame | maglimit | seeing (") '
        "| stars V<=11 in cone (by class) | in footprint | tracklets | built UNKNOWN "
        "| built KNOWN |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for c in evidence.fields:
        lines.append(
            f"| {c.field_id} | {c.origin} | {'/'.join(c.filters)} "
            f"| {'/'.join(f'{m:.0f}' for m in c.minutes_from_first)} "
            f"| {'/'.join(map(str, c.sources_per_frame))} "
            f"| {'/'.join(f'{m:.1f}' for m in c.maglimit_per_frame)} "
            f"| {'/'.join(f'{m:.1f}' for m in c.seeing_per_frame)} "
            f"| {'/'.join(map(str, c.stars_per_class))} "
            f"| {'/'.join(map(str, c.stars_in_footprint_per_class))} "
            f"| {c.tracklets} | {c.unknown_built} | {c.known_built} |"
        )
    for scope, title in (
        ("isolated", "isolated stars (primary)"),
        ("all", "all stars"),
    ):
        lines += [
            "",
            f"## Pooled profiles — {title}",
            "",
            "Per magnitude class and annulus, summed over stars of all fields: "
            "built UNKNOWN pairs, density, ratio to the same stars' 480-900\" "
            "background, mask composition (unmasked/partial/all), bit 12 on all "
            "detections, medians of sharp max / min SNR / fit rms; rejected UNKNOWN "
            "and built KNOWN ratios likewise.",
            "",
            "| class | annulus | stars | area (arcmin²) | UNKNOWN | density | ratio "
            "| mask u/p/a | bit 12 | sharp max | min SNR | fit rms | rejected ratio "
            "| KNOWN | KNOWN density |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for c in classes:
            for a in range(len(ANNULUS_EDGES) - 1):
                cell = evidence.cells.get(f"ALL|{c}|{scope}|{a}")
                if cell is None:
                    continue
                density, ratio = excess(evidence.cells, "ALL", c, scope, a)
                _, rejected_ratio = excess(
                    evidence.cells, "ALL", c, scope, a, "unknown_rejected"
                )
                known_density, _ = excess(
                    evidence.cells, "ALL", c, scope, a, "known_built"
                )
                m = cell.unknown_by_mask
                lines.append(
                    f"| {class_label(c)} | {annulus_label(a)} | {cell.stars} "
                    f"| {cell.area_arcmin2:.2f} | {cell.unknown_built} | {f(density, 3)} "
                    f"| {f(ratio, 1)} | {m['unmasked']}/{m['partially_masked']}/{m['all_masked']} "
                    f"| {cell.unknown_halo_bit} | {f(cell.unknown_sharp_max.median)} "
                    f"| {f(cell.unknown_min_snr.median, 1)} | {f(cell.unknown_fit_rms.median, 3)} "
                    f"| {f(rejected_ratio, 1)} | {cell.known_built} | {f(known_density, 4)} |"
                )
    lines += [
        "",
        '## Per-field ratio, 0-60" (three inner annuli pooled) over background, isolated stars',
        "",
        "| field | " + " | ".join(class_label(c) for c in classes) + " |",
        "|---|" + "---|" * len(classes),
    ]
    for c_field in evidence.fields:
        cells_row = []
        for c in classes:
            inner = [
                evidence.cells.get(f"{c_field.field_id}|{c}|isolated|{a}")
                for a in range(3)
            ]
            background = evidence.cells.get(
                f"{c_field.field_id}|{c}|isolated|{BACKGROUND_ANNULUS}"
            )
            if not all(inner) or background is None:
                cells_row.append("–")
                continue
            area = sum(x.area_arcmin2 for x in inner)
            count = sum(x.unknown_built for x in inner)
            if area <= 0:
                cells_row.append("–")
            elif background.unknown_built == 0 or background.area_arcmin2 <= 0:
                cells_row.append(f"{count} / bg 0 ({inner[0].stars}★)")
            else:
                ratio = (count / area) / (
                    background.unknown_built / background.area_arcmin2
                )
                cells_row.append(f"{ratio:.1f} ({count}, {inner[0].stars}★)")
        lines.append(f"| {c_field.field_id} | " + " | ".join(cells_row) + " |")

    lines += [
        "",
        "## KNOWN objects (AS-022 target rule) by closest approach to a star",
        "",
        "Counts by loss stage. An object appears once per magnitude class, in the "
        "annulus of its closest approach to a star of that class (predicted positions).",
        "",
        "| class | closest approach | objects | recovered | not detected | not candidate "
        "| not linked | not identified |",
        "|---|---|---|---|---|---|---|---|",
    ]
    stages = (
        "recovered",
        "not_detected",
        "not_candidate",
        "not_linked",
        "not_identified",
    )
    for c in classes:
        for a in range(len(ANNULUS_EDGES) - 1):
            members = [
                k
                for k in evidence.known
                if k.proximity.separation_by_class[c] is not None
                and annulus_index(k.proximity.separation_by_class[c]) == a
            ]
            if not members:
                continue
            counts = [sum(k.loss_stage == s for k in members) for s in stages]
            lines.append(
                f"| {class_label(c)} | {annulus_label(a)} | {len(members)} | "
                + " | ".join(map(str, counts))
                + " |"
            )
    total = [sum(k.loss_stage == s for k in evidence.known) for s in stages]
    lines.append(
        f"| any | all | {len(evidence.known)} | " + " | ".join(map(str, total)) + " |"
    )
    near = sorted(
        (
            k
            for k in evidence.known
            if any(
                s is not None and s < ANNULUS_EDGES[5]
                for s in k.proximity.separation_by_class[:4]
            )
        ),
        key=lambda k: min(
            s for s in k.proximity.separation_by_class[:4] if s is not None
        ),
    )
    lines += [
        "",
        'KNOWN objects with a V < 10 star within 240" (closest approach):',
        "",
        '| field | object | role | V | nearest V<10 star (") | star V | detected | '
        "candidate | stage |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for k in near:
        sep, cls = min(
            (s, c)
            for c, s in enumerate(k.proximity.separation_by_class[:4])
            if s is not None
        )
        lines.append(
            f"| {k.field_id} | {k.designation} | {k.role} | {k.v_magnitude:.1f} | {sep:.0f} "
            f"| {class_label(cls)} | {k.detected_frames}/3 | {k.candidate_frames}/3 | {k.loss_stage} |"
        )

    by_id = {(r.field_id, r.tracklet_id): r for r in reviews}
    lines += [
        "",
        "## Visual sample",
        "",
        '| field | item | group | nearest star (", V) | note | agent label | context | image |',
        "|---|---|---|---|---|---|---|---|",
    ]
    for strip in evidence.strips:
        r = by_id.get((strip.field_id, strip.item_id))
        p = strip.proximity
        lines.append(
            f"| {strip.field_id} | {strip.item_id} | {strip.group} "
            f"| {f(p.nearest_separation_arcsec, 0)}, {f(p.nearest_v_mag, 1)} | {strip.note} "
            f"| {r.same_source_all_epochs if r else 'not reviewed'} | {r.context if r else ''} "
            f"| [{strip.image}]({strip.image}) |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    select = commands.add_parser("select", help="build the pre-registered population")
    select.add_argument("--out", type=Path, required=True)
    evidence = commands.add_parser("evidence", help="profiles, KNOWN search, strips")
    evidence.add_argument("--population", type=Path, required=True)
    evidence.add_argument("--out-dir", type=Path, required=True)
    render = commands.add_parser("render", help="markdown from the evidence JSON")
    render.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "select":
        population = build_population()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(population.model_dump_json(indent=1) + "\n")
        print("\n".join(population.log))
        print(f"wrote {args.out} ({len(population.fields)} fields)")
    elif args.command == "evidence":
        population = Population.model_validate_json(args.population.read_text())
        evidence = run_evidence(
            population, args.out_dir, progress=lambda m: print(m, flush=True)
        )
        (args.out_dir / "as034_evidence.json").write_text(
            evidence.model_dump_json() + "\n"
        )
        print(f"wrote {args.out_dir}")
    if args.command in ("evidence", "render"):
        import json

        from app.validation.masked import VisualReview

        evidence = Evidence.model_validate_json(
            (args.out_dir / "as034_evidence.json").read_text()
        )
        review_path = args.out_dir / "visual_review.json"
        reviews = (
            [
                VisualReview.model_validate(r)
                for r in json.loads(review_path.read_text())
            ]
            if review_path.exists()
            else []
        )
        (args.out_dir / "as034_evidence.md").write_text(
            render_markdown(evidence, reviews)
        )


if __name__ == "__main__":
    main()
