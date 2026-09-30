"""AS-033: bright-star proximity of tracklets on several ZTF fields.

Research/evidence only — no filter, exclusion radius, score, rank,
threshold or rejection is derived here.

Bright-star catalog: Tycho-2 (Høg et al. 2000; VizieR I/259/tyc2), the
catalog the ZTF pipeline itself uses for halo masking (ZSDS Explanatory
Supplement §6.5 step 16, "V ≤ 6.5").
- Position: RAmdeg/DEmdeg (ICRS, mean position at epoch J2000); when
  absent (no proper motion in Tycho-2), RA(ICRS)/DE(ICRS) at the Tycho
  observation epoch (~J1991.25). Proper motion over 1991–2020 is at most a
  few arcsec for these stars and is ignored.
- Magnitude: Johnson V estimated as V = VT − 0.090 (BT − VT) (Tycho-2
  guide, ESA 1997 vol. 1 §1.3); V = VT when BT is missing; a star
  without VT has no magnitude and is never "bright".
- "Bright star" = V ≤ 6.5, the ZSDS halo-masking criterion (not tuned).

Proximity: the angular separation (astropy great-circle distance, ICRS)
between a tracklet's mean detection position and the nearest bright star
within the field's catalog cone; null when the cone has no bright star.

Steps (both reproducible; see validation/results/as033/):
    python -m app.validation.bright_stars select \\
        --out validation/results/as033/as033_fields.json
    python -m app.validation.bright_stars evidence \\
        --fields validation/results/as033/as033_fields.json \\
        --out-dir validation/results/as033
"""

import argparse
import hashlib
import json
import math
import statistics
from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path

import astropy.units as u
import httpx
import numpy
from astropy.coordinates import GeocentricTrueEcliptic, SkyCoord
from pydantic import BaseModel

from app.models.identification import IdentificationStatus
from app.models.known_object import KnownObjectField
from app.models.observation import Observation
from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG
from app.models.tracklet import Tracklet, TrackletStatus
from app.services.astrometry import angular_distance_arcsec
from app.services.ztf_service import fetch_ztf_metadata
from app.validation.data import CatalogFrames, load_catalog_frames, load_field_data
from app.validation.masked import (
    VisualReview,
    _mean,
    render_strip,
    sample_key,
    strip_geometry,
    write_png,
)
from app.validation.models import FieldSnapshot, FrameMetadata, ValidationField
from app.validation.presets import AS022_REPORT
from app.validation.quality import field_records
from app.validation.runner import ValidationReport


VIZIER_URL = "https://vizier.cds.unistra.fr/viz-bin/asu-tsv"
TYCHO_COLUMNS = "TYC1,TYC2,TYC3,RAmdeg,DEmdeg,RA(ICRS),DE(ICRS),BTmag,VTmag"
# A V <= 6.5 star has VT <= 6.5 + 0.09 * (BT - VT) < 7.0 for BT - VT < 5.
QUERY_MAX_VT = 7.0
BRIGHT_V_MAX = 6.5
REFERENCE_FIELDS = ("B-2019-01-25-565-c13-q3", "D-2019-06-02-281-c16-q3")

# Pre-registered field selection (fixed before any tracklet was built).
SELECTION_SALT = "AS-033"
SELECTION_MAX_ECLIPTIC_LATITUDE = 10.0  # deg, asteroid-rich band like AS-022
SELECTION_MIN_DEC = -25.0  # deg, ZTF (Palomar) coverage
SELECTION_START_JD = 2458194.5  # 2018-03-17, ZTF survey start
SELECTION_END_JD = 2459215.5  # 2021-01-01
SELECTION_FIELDS = 4
SELECTION_MAX_STARS_TRIED = 40
SELECTION_RULE = (
    "Tycho-2 stars with V <= 6.5, Dec >= -25 deg, |ecliptic latitude| <= 10 "
    "deg, ordered by SHA-256('AS-033:<Tycho id>'). For each star in turn, "
    "the IRSA ZTF science metadata covering the star's position between "
    "2018-03-17 and 2021-01-01 is grouped by (field, CCD, quadrant, UTC "
    "date); the earliest group with >= 3 exposures is taken, and its first, "
    "middle ((n-1)//2) and last exposure form the sequence (the AS-022 "
    "rule). Stars without such a group are skipped and logged. The first "
    "4 stars that yield a sequence are used. No pipeline output, source "
    "count or UNKNOWN count is looked at. Amendment 1 (2026-09-30, before "
    "any evidence output existed): a sequence qualifies only if the PSF "
    "catalog and science image of all three exposures exist in the IRSA "
    "archive (HTTP HEAD 200); otherwise the star is skipped and logged. "
    "Reason: IRSA metadata listed an exposure (pid 579341801615) whose "
    "products return 404."
)

# Radial bins [arcsec]: regular 2' annuli out to 10', a 10'-15' ring and
# everything beyond 15' as the far control. Fixed before any evidence run;
# not derived from the AS-032 halo measurement.
BIN_EDGES = (0.0, 120.0, 240.0, 360.0, 480.0, 600.0, 900.0, math.inf)
CONTROL_BIN = len(BIN_EDGES) - 2
AREA_GRID = 500
# Visual sample per new field: UNKNOWN built tracklets within 10' of a
# bright star, UNKNOWN built beyond 15', and KNOWN built (hash order).
VISUAL_NEAR = 6
VISUAL_FAR = 2
VISUAL_KNOWN = 2
NEAR_EDGE = 600.0


class TychoStar(BaseModel):
    tycho_id: str
    ra: float
    dec: float
    vt_mag: float | None
    bt_mag: float | None
    v_mag: float | None
    position_source: str  # "mean J2000" | "observed ~J1991.25"


def johnson_v(vt: float | None, bt: float | None) -> float | None:
    if vt is None:
        return None
    if bt is None:
        return vt
    return vt - 0.090 * (bt - vt)


def parse_tycho_tsv(text: str) -> list[TychoStar]:
    """Parse a VizieR asu-tsv Tycho-2 result with TYCHO_COLUMNS."""
    lines = [line for line in text.splitlines() if line and not line.startswith("#")]
    if not lines:
        return []
    header = lines[0].split("\t")
    stars = []
    for line in lines[3:]:  # header, units, dashes
        row = dict(zip(header, line.split("\t")))

        def number(key):
            value = (row.get(key) or "").strip()
            return float(value) if value else None

        mean_ra, mean_dec = number("RAmdeg"), number("DEmdeg")
        if mean_ra is not None and mean_dec is not None:
            ra, dec, source = mean_ra, mean_dec, "mean J2000"
        else:
            ra, dec, source = number("RA(ICRS)"), number("DE(ICRS)"), "observed ~J1991.25"
        if ra is None or dec is None:
            continue
        vt, bt = number("VTmag"), number("BTmag")
        stars.append(
            TychoStar(
                tycho_id="TYC {}-{}-{}".format(
                    *(row[k].strip() for k in ("TYC1", "TYC2", "TYC3"))
                ),
                ra=ra,
                dec=dec,
                vt_mag=vt,
                bt_mag=bt,
                v_mag=johnson_v(vt, bt),
                position_source=source,
            )
        )
    return stars


def query_tycho(
    params: dict[str, str], client: httpx.Client | None = None
) -> tuple[str, list[TychoStar]]:
    query = {
        "-source": "I/259/tyc2",
        "-out": TYCHO_COLUMNS,
        "-out.max": "unlimited",
        "VTmag": f"<{QUERY_MAX_VT}",
        **params,
    }
    request = client.get if client is not None else httpx.get
    response = request(VIZIER_URL, params=query, timeout=180.0)
    response.raise_for_status()
    return str(response.request.url), parse_tycho_tsv(response.text)


def bright(stars: Sequence[TychoStar]) -> list[TychoStar]:
    return [s for s in stars if s.v_mag is not None and s.v_mag <= BRIGHT_V_MAX]


# --- pre-registered field selection ---


def ecliptic_latitude(ra: float, dec: float) -> float:
    coord = SkyCoord(ra * u.deg, dec * u.deg, frame="icrs")
    return float(coord.transform_to(GeocentricTrueEcliptic()).lat.deg)


def selection_order(stars: Sequence[TychoStar]) -> list[TychoStar]:
    eligible = [
        s
        for s in bright(stars)
        if s.dec >= SELECTION_MIN_DEC
        and abs(ecliptic_latitude(s.ra, s.dec)) <= SELECTION_MAX_ECLIPTIC_LATITUDE
    ]
    return sorted(
        eligible,
        key=lambda s: hashlib.sha256(f"{SELECTION_SALT}:{s.tycho_id}".encode()).hexdigest(),
    )


def pick_sequence(rows: Sequence[dict[str, str]]) -> list[dict[str, str]] | None:
    """Earliest (field, CCD, quadrant, UTC date) group with >= 3 exposures;
    its first, middle and last exposure."""
    groups: dict[tuple, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (row["field"], row["ccdid"], row["qid"], row["obsdate"][:10])
        groups[key].append(row)
    qualifying = [g for g in groups.values() if len(g) >= 3]
    if not qualifying:
        return None
    group = min(
        qualifying, key=lambda g: min((float(r["obsjd"]), int(r["pid"])) for r in g)
    )
    group = sorted(group, key=lambda r: (float(r["obsjd"]), int(r["pid"])))
    return [group[0], group[(len(group) - 1) // 2], group[-1]]


def products_available(pids_rows: Sequence[dict[str, str]], client=None) -> bool:
    """Amendment 1: PSF catalog and science image of every exposure exist."""
    from app.services.ztf_service import (
        build_psf_catalog_url,
        build_science_image_url,
        map_ztf_metadata_to_observation,
    )

    head = client.head if client is not None else httpx.head
    for row in pids_rows:
        observation = map_ztf_metadata_to_observation(row)
        for url in (build_psf_catalog_url(observation), build_science_image_url(observation)):
            if head(url, timeout=60.0).status_code != 200:
                return False
    return True


class SelectedField(BaseModel):
    field: ValidationField
    selection_star: TychoStar
    filters: list[str]


class SelectionLog(BaseModel):
    star: str
    outcome: str


class FieldSelection(BaseModel):
    generated_at: datetime
    rule: str
    tycho_query: str
    eligible_stars: int
    fields: list[SelectedField]
    log: list[SelectionLog]


def select_fields(
    client: httpx.Client | None = None,
    metadata: Callable[..., list[dict[str, str]]] = fetch_ztf_metadata,
    tycho: Callable[..., tuple[str, list[TychoStar]]] = query_tycho,
    available: Callable[..., bool] = products_available,
    progress: Callable[[str], None] = lambda message: None,
) -> FieldSelection:
    url, stars = tycho({"DE(ICRS)": f">{SELECTION_MIN_DEC - 1}"}, client)
    ordered = selection_order(stars)
    reference_pids = {
        pid
        for s in ValidationReport.model_validate_json(AS022_REPORT.read_text()).snapshots
        for pid in (o.product_id for o in s.observations)
    }
    fields: list[SelectedField] = []
    log: list[SelectionLog] = []
    for star in ordered[:SELECTION_MAX_STARS_TRIED]:
        if len(fields) >= SELECTION_FIELDS:
            break
        progress(f"{star.tycho_id} (V {star.v_mag:.2f}): searching ZTF")
        try:
            rows = metadata(
                star.ra, star.dec, SELECTION_START_JD, SELECTION_END_JD, client
            )
        except Exception as exc:  # recorded, the rule moves to the next star
            log.append(SelectionLog(star=star.tycho_id, outcome=f"metadata error: {exc}"))
            continue
        sequence = pick_sequence(rows)
        if sequence is None:
            log.append(
                SelectionLog(
                    star=star.tycho_id,
                    outcome=f"no quadrant-night with >= 3 exposures ({len(rows)} rows)",
                )
            )
            continue
        pids = [int(r["pid"]) for r in sequence]
        if set(pids) & reference_pids:
            log.append(SelectionLog(star=star.tycho_id, outcome="overlaps AS-022 field"))
            continue
        if not available(sequence, client):
            log.append(
                SelectionLog(
                    star=star.tycho_id,
                    outcome=f"products missing in the archive for {pids} (amendment 1)",
                )
            )
            continue
        first = sequence[0]
        field_id = (
            f"S{len(fields) + 1}-{first['obsdate'][:10]}-{int(first['field'])}"
            f"-c{int(first['ccdid'])}-q{int(first['qid'])}"
        )
        fields.append(
            SelectedField(
                field=ValidationField(
                    field_id=field_id,
                    description=f"AS-033 field around {star.tycho_id} (V {star.v_mag:.2f})",
                    product_ids=pids,
                    selection_note=SELECTION_RULE,
                ),
                selection_star=star,
                filters=[r["filtercode"] for r in sequence],
            )
        )
        log.append(SelectionLog(star=star.tycho_id, outcome=f"selected as {field_id}"))
    return FieldSelection(
        generated_at=datetime.now(timezone.utc),
        rule=SELECTION_RULE,
        tycho_query=url,
        eligible_stars=len(ordered),
        fields=fields,
        log=log,
    )


# --- radial evidence ---


def bin_index(separation_arcsec: float | None) -> int | None:
    """Index of the radial bin [edge_i, edge_i+1); None without a star."""
    if separation_arcsec is None:
        return None
    for index in range(len(BIN_EDGES) - 1):
        if BIN_EDGES[index] <= separation_arcsec < BIN_EDGES[index + 1]:
            return index
    raise ValueError(f"negative separation {separation_arcsec}")


def bin_label(index: int) -> str:
    low, high = BIN_EDGES[index], BIN_EDGES[index + 1]
    return f"{low / 60:.0f}'-{high / 60:.0f}'" if math.isfinite(high) else f">={low / 60:.0f}'"


def nearest_star(
    ra: float, dec: float, stars: Sequence[TychoStar]
) -> tuple[float | None, str | None]:
    """Great-circle separation [arcsec] to the nearest star; (None, None)
    when there is no star."""
    best: tuple[float | None, str | None] = (None, None)
    for star in stars:
        separation = angular_distance_arcsec(ra, dec, star.ra, star.dec)
        if best[0] is None or separation < best[0]:
            best = (separation, star.tycho_id)
    return best


def _gnomonic_inverse(xi, eta, ra0, dec0):
    """Tangent-plane offsets (radians) about (ra0, dec0) -> ra, dec (deg)."""
    ra0r, dec0r = math.radians(ra0), math.radians(dec0)
    rho = numpy.hypot(xi, eta)
    c = numpy.arctan(rho)
    with numpy.errstate(invalid="ignore", divide="ignore"):
        dec = numpy.arcsin(
            numpy.cos(c) * math.sin(dec0r)
            + numpy.where(rho > 0, eta * numpy.sin(c) * math.cos(dec0r) / rho, 0.0)
        )
        ra = ra0r + numpy.arctan2(
            xi * numpy.sin(c),
            rho * math.cos(dec0r) * numpy.cos(c) - eta * math.sin(dec0r) * numpy.sin(c),
        )
    return numpy.degrees(ra) % 360.0, numpy.degrees(dec)


def _gnomonic(ra, dec, ra0, dec0):
    ra, dec = numpy.radians(ra), numpy.radians(dec)
    ra0r, dec0r = math.radians(ra0), math.radians(dec0)
    cos_c = numpy.sin(dec0r) * numpy.sin(dec) + numpy.cos(dec0r) * numpy.cos(dec) * numpy.cos(ra - ra0r)
    xi = numpy.cos(dec) * numpy.sin(ra - ra0r) / cos_c
    eta = (numpy.cos(dec0r) * numpy.sin(dec) - numpy.sin(dec0r) * numpy.cos(dec) * numpy.cos(ra - ra0r)) / cos_c
    return xi, eta


def _separation_arcsec(ra1, dec1, ra2, dec2):
    """Vectorised haversine great-circle distance [arcsec]."""
    ra1, dec1, ra2, dec2 = (numpy.radians(v) for v in (ra1, dec1, ra2, dec2))
    h = numpy.sin((dec2 - dec1) / 2) ** 2 + numpy.cos(dec1) * numpy.cos(dec2) * numpy.sin((ra2 - ra1) / 2) ** 2
    return numpy.degrees(2 * numpy.arcsin(numpy.sqrt(numpy.clip(h, 0, 1)))) * 3600.0


def bin_areas(
    corners: Sequence[tuple[float, float]],
    stars: Sequence[TychoStar],
    grid: int = AREA_GRID,
) -> tuple[float, list[float]]:
    """Footprint area [arcmin²] and its area in each radial bin, from a
    fixed grid in the tangent plane at the footprint centre: every grid
    cell's great-circle distance to the nearest star decides its bin."""
    ra0, dec0 = _mean(list(corners))
    xi, eta = _gnomonic(
        numpy.array([c[0] for c in corners]), numpy.array([c[1] for c in corners]), ra0, dec0
    )
    polygon = numpy.column_stack([xi, eta])
    centre = polygon.mean(axis=0)
    polygon = polygon[numpy.argsort(numpy.arctan2(polygon[:, 1] - centre[1], polygon[:, 0] - centre[0]))]
    xs = numpy.linspace(polygon[:, 0].min(), polygon[:, 0].max(), grid)
    ys = numpy.linspace(polygon[:, 1].min(), polygon[:, 1].max(), grid)
    gx, gy = numpy.meshgrid(xs, ys)
    inside = numpy.zeros(gx.shape, dtype=bool)
    for k in range(len(polygon)):
        x1, y1 = polygon[k]
        x2, y2 = polygon[(k + 1) % len(polygon)]
        with numpy.errstate(divide="ignore", invalid="ignore"):
            at = (x2 - x1) * (gy - y1) / (y2 - y1) + x1
        inside ^= ((y1 > gy) != (y2 > gy)) & (gx < at)
    x, y = polygon[:, 0], polygon[:, 1]
    area = 0.5 * abs(numpy.dot(x, numpy.roll(y, 1)) - numpy.dot(y, numpy.roll(x, 1)))
    area_arcmin2 = float(area) * (180 * 60 / math.pi) ** 2
    cell = area_arcmin2 / inside.sum()
    if not stars:
        return area_arcmin2, [0.0] * (len(BIN_EDGES) - 1)
    ra, dec = _gnomonic_inverse(gx[inside], gy[inside], ra0, dec0)
    nearest = numpy.min(
        numpy.stack([_separation_arcsec(ra, dec, s.ra, s.dec) for s in stars]), axis=0
    )
    counts = numpy.histogram(nearest, bins=numpy.array(BIN_EDGES[:-1] + (1e12,)))[0]
    return area_arcmin2, [float(c) * cell for c in counts]


class TrackletProximity(BaseModel):
    field_id: str
    tracklet_id: str
    identification_status: IdentificationStatus
    known_designation: str | None
    tracklet_status: TrackletStatus
    ra: float
    dec: float
    separation_arcsec: float | None
    nearest_star: str | None
    radial_bin: int | None
    mask_state: str  # unmasked | partially_masked | all_masked
    halo_bit_all: bool
    min_snr: float
    sharp_max: float | None
    fit_rms_residual_arcsec: float


class Summary(BaseModel):
    count: int
    median: float | None
    p25: float | None
    p75: float | None


class RadialBin(BaseModel):
    label: str
    low_arcsec: float
    high_arcsec: float | None
    area_arcmin2: float
    unknown_built: int
    unknown_built_density: float | None
    unknown_built_by_mask: dict[str, int]
    unknown_built_halo_bit_all: int
    unknown_rejected: int
    known_built: int
    known_built_density: float | None
    unknown_min_snr: Summary
    unknown_sharp_max: Summary
    unknown_fit_rms: Summary
    known_min_snr: Summary
    known_sharp_max: Summary
    known_fit_rms: Summary


class FieldConditions(BaseModel):
    role: str  # reference | new
    skybot_mode: str
    ccd_quadrant: str
    filters: list[str]
    minutes_from_first: list[float]
    sources_per_frame: list[int]
    maglimit_per_frame: list[float]
    seeing_arcsec_per_frame: list[float]
    footprint_arcmin2: float
    tycho_query: str
    bright_stars: list[TychoStar]
    bright_stars_inside_footprint: list[str]


class FieldRadial(BaseModel):
    field_id: str
    conditions: FieldConditions
    bins: list[RadialBin]
    tracklets_without_star: int
    near_to_control_density_ratio: float | None
    tracklets: list[TrackletProximity]


class SampledStrip(BaseModel):
    field_id: str
    tracklet_id: str
    group: str
    image: str
    separation_arcsec: float | None
    mask_state: str
    min_snr: float
    sharp_max: float | None
    fit_rms_residual_arcsec: float


class BrightStarReport(BaseModel):
    generated_at: datetime
    catalog: str
    bright_v_max: float
    bin_edges_arcsec: list[float | None]
    selection_rule: str
    fields: list[FieldRadial]
    strips: list[SampledStrip]


def summary(values: Sequence[float | None]) -> Summary:
    present = sorted(v for v in values if v is not None)
    if not present:
        return Summary(count=0, median=None, p25=None, p75=None)
    if len(present) == 1:
        return Summary(count=1, median=present[0], p25=present[0], p75=present[0])
    q = statistics.quantiles(present, n=4, method="inclusive")
    return Summary(count=len(present), median=statistics.median(present), p25=q[0], p75=q[2])


def mask_state(masked: int, count: int) -> str:
    if masked == 0:
        return "unmasked"
    return "all_masked" if masked == count else "partially_masked"


def radial_bins(
    tracklets: Sequence[TrackletProximity], areas: Sequence[float]
) -> list[RadialBin]:
    bins = []
    for index, area in enumerate(areas):
        members = [t for t in tracklets if t.radial_bin == index]
        built = [t for t in members if t.tracklet_status is TrackletStatus.TRACKLET_BUILT]
        unknown = [t for t in built if t.identification_status is IdentificationStatus.UNKNOWN]
        known = [t for t in built if t.identification_status is IdentificationStatus.KNOWN]
        rejected = [
            t
            for t in members
            if t.tracklet_status is TrackletStatus.REJECTED
            and t.identification_status is IdentificationStatus.UNKNOWN
        ]
        high = BIN_EDGES[index + 1]
        bins.append(
            RadialBin(
                label=bin_label(index),
                low_arcsec=BIN_EDGES[index],
                high_arcsec=high if math.isfinite(high) else None,
                area_arcmin2=round(area, 3),
                unknown_built=len(unknown),
                unknown_built_density=round(len(unknown) / area, 5) if area > 0 else None,
                unknown_built_by_mask={
                    state: sum(t.mask_state == state for t in unknown)
                    for state in ("unmasked", "partially_masked", "all_masked")
                },
                unknown_built_halo_bit_all=sum(t.halo_bit_all for t in unknown),
                unknown_rejected=len(rejected),
                known_built=len(known),
                known_built_density=round(len(known) / area, 5) if area > 0 else None,
                unknown_min_snr=summary([t.min_snr for t in unknown]),
                unknown_sharp_max=summary([t.sharp_max for t in unknown]),
                unknown_fit_rms=summary([t.fit_rms_residual_arcsec for t in unknown]),
                known_min_snr=summary([t.min_snr for t in known]),
                known_sharp_max=summary([t.sharp_max for t in known]),
                known_fit_rms=summary([t.fit_rms_residual_arcsec for t in known]),
            )
        )
    return bins


def near_to_control_ratio(bins: Sequence[RadialBin]) -> float | None:
    """UNKNOWN built density within 10' of a bright star over that beyond
    15' (descriptive; None when either side has no area or the control has
    no tracklet)."""
    near = [b for b in bins if b.high_arcsec is not None and b.high_arcsec <= NEAR_EDGE]
    near_area = sum(b.area_arcmin2 for b in near)
    control = bins[CONTROL_BIN]
    if near_area <= 0 or control.area_arcmin2 <= 0 or control.unknown_built == 0:
        return None
    near_density = sum(b.unknown_built for b in near) / near_area
    return round(near_density / (control.unknown_built / control.area_arcmin2), 3)


def field_radial(
    snapshot: FieldSnapshot,
    catalogs: CatalogFrames,
    stars: Sequence[TychoStar],
    conditions: FieldConditions,
) -> tuple[FieldRadial, dict[str, Tracklet]]:
    """Radial evidence of one field, plus its tracklets by id."""
    records, _, _ = field_records(
        snapshot, catalogs, EXPERIMENTAL_DEFAULT_CONFIG, keep_all_tracklets=True
    )
    tracklets = []
    for record in records:
        positions = [(i.detection.ra, i.detection.dec) for i in record.tracklet.detections]
        ra, dec = _mean(positions)
        separation, star_id = nearest_star(ra, dec, stars)
        f = record.features
        tracklets.append(
            TrackletProximity(
                field_id=record.field_id,
                tracklet_id=f.tracklet_id,
                identification_status=record.identification_status,
                known_designation=record.known_designation,
                tracklet_status=f.tracklet_status,
                ra=round(ra, 7),
                dec=round(dec, 7),
                separation_arcsec=None if separation is None else round(separation, 2),
                nearest_star=star_id,
                radial_bin=bin_index(separation),
                mask_state=mask_state(f.masked_detection_count, f.detection_count),
                halo_bit_all=all(
                    i.detection.mask_bits >> 12 & 1 for i in record.tracklet.detections
                ),
                min_snr=f.min_snr,
                sharp_max=f.sharp_max,
                fit_rms_residual_arcsec=f.fit_rms_residual_arcsec,
            )
        )
    _, areas = bin_areas(snapshot.frame_metadata[0].corners, stars)
    bins = radial_bins(tracklets, areas)
    radial = FieldRadial(
        field_id=snapshot.field.field_id,
        conditions=conditions,
        bins=bins,
        tracklets_without_star=sum(t.radial_bin is None for t in tracklets),
        near_to_control_density_ratio=near_to_control_ratio(bins),
        tracklets=tracklets,
    )
    return radial, {r.tracklet.tracklet_id: r.tracklet for r in records}


def field_stars(
    metadata: Sequence[FrameMetadata], client: httpx.Client | None = None
) -> tuple[str, list[TychoStar], list[str]]:
    """Bright Tycho-2 stars within the footprint's circumscribed circle +
    15' (halos of stars just outside the image reach into it)."""
    corners = metadata[0].corners
    ra0, dec0 = _mean(list(corners))
    radius = max(angular_distance_arcsec(ra0, dec0, ra, dec) for ra, dec in corners)
    url, stars = query_tycho(
        {"-c": f"{ra0:.6f} {dec0:+.6f}", "-c.rd": f"{(radius + 900.0) / 3600.0:.4f}"},
        client,
    )
    selected = sorted(bright(stars), key=lambda s: s.tycho_id)
    inside = [
        s.tycho_id
        for s in selected
        if _point_in_footprint(s.ra, s.dec, corners)
    ]
    return url, selected, inside


def _point_in_footprint(ra, dec, corners) -> bool:
    ra0, dec0 = _mean(list(corners))
    xi, eta = _gnomonic(numpy.array([c[0] for c in corners]), numpy.array([c[1] for c in corners]), ra0, dec0)
    px, py = _gnomonic(numpy.array([ra]), numpy.array([dec]), ra0, dec0)
    polygon = numpy.column_stack([xi, eta])
    centre = polygon.mean(axis=0)
    polygon = polygon[numpy.argsort(numpy.arctan2(polygon[:, 1] - centre[1], polygon[:, 0] - centre[0]))]
    inside = False
    for k in range(len(polygon)):
        x1, y1 = polygon[k]
        x2, y2 = polygon[(k + 1) % len(polygon)]
        if (y1 > py[0]) != (y2 > py[0]):
            at = (x2 - x1) * (py[0] - y1) / (y2 - y1) + x1
            inside ^= bool(px[0] < at)
    return inside


def conditions_of(
    role: str,
    skybot_mode: str,
    observations: Sequence[Observation],
    metadata: Sequence[FrameMetadata],
    catalogs: CatalogFrames,
    url: str,
    stars: Sequence[TychoStar],
    inside: Sequence[str],
) -> FieldConditions:
    t0 = observations[0].observed_at
    area, _ = bin_areas(metadata[0].corners, [])
    return FieldConditions(
        role=role,
        skybot_mode=skybot_mode,
        ccd_quadrant=f"field {observations[0].field} c{observations[0].ccd_id} q{observations[0].quadrant_id}",
        filters=[o.filter_code for o in observations],
        minutes_from_first=[round((o.observed_at - t0).total_seconds() / 60, 2) for o in observations],
        sources_per_frame=[frame.source_count for frame in catalogs.frames],
        maglimit_per_frame=[m.maglimit for m in metadata],
        seeing_arcsec_per_frame=[m.seeing_arcsec for m in metadata],
        footprint_arcmin2=round(area, 1),
        tycho_query=url,
        bright_stars=list(stars),
        bright_stars_inside_footprint=list(inside),
    )


def load_fields(
    selection: FieldSelection,
    client: httpx.Client | None = None,
    progress: Callable[[str], None] = lambda message: None,
):
    """(snapshot, catalogs, stars, conditions) for B, D and the new fields."""
    from app.validation.data import fetch_frame_metadata, query_skybot_fields

    report = ValidationReport.model_validate_json(AS022_REPORT.read_text())
    snapshots = {s.field.field_id: s for s in report.snapshots}
    for field_id in REFERENCE_FIELDS:
        snapshot = snapshots[field_id]
        progress(f"{field_id}: catalogs")
        catalogs = load_catalog_frames(snapshot.observations, client)
        url, stars, inside = field_stars(snapshot.frame_metadata, client)
        yield snapshot, catalogs, stars, conditions_of(
            "reference", "AS-022 snapshot", snapshot.observations,
            snapshot.frame_metadata, catalogs, url, stars, inside,
        )
    for selected in selection.fields:
        field = selected.field
        progress(f"{field.field_id}: metadata, catalogs, SkyBoT")
        observations, metadata = fetch_frame_metadata(field.product_ids, client)
        catalogs = load_catalog_frames(observations, client)
        skybot = query_skybot_fields(observations, metadata, client)
        snapshot = FieldSnapshot(
            field=field,
            observations=observations,
            frame_metadata=metadata,
            skybot_fields=skybot,
            source_counts=[frame.source_count for frame in catalogs.frames],
            targets=[],
        )
        url, stars, inside = field_stars(metadata, client)
        yield snapshot, catalogs, stars, conditions_of(
            "new", "live (stored in as033_skybot.json)", observations, metadata,
            catalogs, url, stars, inside,
        )


def visual_sample(field: FieldRadial) -> list[tuple[str, TrackletProximity]]:
    """Deterministic strip sample of one field (hash order, no feature)."""

    def ordered(items):
        return sorted(items, key=lambda t: sample_key(t.field_id, t.tracklet_id))

    built = [t for t in field.tracklets if t.tracklet_status is TrackletStatus.TRACKLET_BUILT]
    unknown = [t for t in built if t.identification_status is IdentificationStatus.UNKNOWN]
    near = [t for t in unknown if t.separation_arcsec is not None and t.separation_arcsec < NEAR_EDGE]
    far = [t for t in unknown if t.radial_bin == CONTROL_BIN]
    known = [t for t in built if t.identification_status is IdentificationStatus.KNOWN]
    return (
        [("near_unknown", t) for t in ordered(near)[:VISUAL_NEAR]]
        + [("control_unknown", t) for t in ordered(far)[:VISUAL_FAR]]
        + [("known", t) for t in ordered(known)[:VISUAL_KNOWN]]
    )


def run_evidence(
    selection: FieldSelection,
    out_dir: Path,
    progress: Callable[[str], None] = lambda message: None,
) -> tuple[BrightStarReport, dict[str, list[KnownObjectField]]]:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    fields, strips, skybot = [], [], {}
    (out_dir / "strips").mkdir(parents=True, exist_ok=True)
    for snapshot, catalogs, stars, conditions in load_fields(selection, progress=progress):
        progress(f"{snapshot.field.field_id}: pipeline + radial evidence")
        radial, details = field_radial(snapshot, catalogs, stars, conditions)
        fields.append(radial)
        if conditions.role != "new":
            continue
        skybot[snapshot.field.field_id] = snapshot.skybot_fields
        product_ids = [o.product_id for o in snapshot.observations]
        epochs = {pid: i for i, pid in enumerate(product_ids)}
        for group, t in visual_sample(radial):
            detections = details[t.tracklet_id].detections
            positions = [(i.detection.ra, i.detection.dec) for i in detections]
            center, size = strip_geometry(positions)
            strip = render_strip(
                client, product_ids, center, size, positions,
                [epochs[i.detection.observation_product_id] for i in detections],
            )
            name = f"{snapshot.field.field_id.split('-')[0]}_{group}_{t.tracklet_id}.png"
            write_png(out_dir / "strips" / name, strip)
            strips.append(
                SampledStrip(
                    field_id=t.field_id, tracklet_id=t.tracklet_id, group=group,
                    image=f"strips/{name}", separation_arcsec=t.separation_arcsec,
                    mask_state=t.mask_state, min_snr=t.min_snr, sharp_max=t.sharp_max,
                    fit_rms_residual_arcsec=t.fit_rms_residual_arcsec,
                )
            )
    return (
        BrightStarReport(
            generated_at=datetime.now(timezone.utc),
            catalog="Tycho-2 (Høg et al. 2000), VizieR I/259/tyc2; V = VT - 0.090 (BT - VT)",
            bright_v_max=BRIGHT_V_MAX,
            bin_edges_arcsec=[e if math.isfinite(e) else None for e in BIN_EDGES],
            selection_rule=selection.rule,
            fields=fields,
            strips=strips,
        ),
        skybot,
    )


def render_markdown(report: BrightStarReport, reviews: Sequence) -> str:
    def f(value, digits=2):
        return "–" if value is None else f"{value:.{digits}f}"

    def q(s: Summary, digits=2):
        return "–" if s.median is None else f"{s.median:.{digits}f} ({s.count})"

    lines = [
        "# AS-033 bright-star proximity evidence (generated)",
        "",
        f"Generated {report.generated_at:%Y-%m-%d %H:%M UTC}. Catalog: {report.catalog}; "
        f"bright = V <= {report.bright_v_max}. Proximity = great-circle separation of "
        "the tracklet's mean detection position from the nearest bright star. "
        "Descriptive only; no filter, radius, score or threshold. Interpretation: "
        "`as033_findings.md`.",
        "",
        f"Field selection (pre-registered, commit before evidence): {report.selection_rule}",
        "",
        "## Fields",
        "",
        "| field | role | CCD/quadrant | filters | minutes | sources/frame | maglimit "
        "| seeing (\") | bright stars (V) in cone | inside footprint | near/control "
        "UNKNOWN density |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for field in report.fields:
        c = field.conditions
        stars = ", ".join(f"{s.tycho_id} ({s.v_mag:.2f})" for s in c.bright_stars) or "none"
        lines.append(
            f"| {field.field_id} | {c.role} | {c.ccd_quadrant} | {'/'.join(c.filters)} "
            f"| {'/'.join(f'{m:.0f}' for m in c.minutes_from_first)} "
            f"| {'/'.join(map(str, c.sources_per_frame))} "
            f"| {'/'.join(f'{m:.1f}' for m in c.maglimit_per_frame)} "
            f"| {'/'.join(f'{m:.1f}' for m in c.seeing_arcsec_per_frame)} "
            f"| {stars} | {len(c.bright_stars_inside_footprint)} "
            f"| {f(field.near_to_control_density_ratio)} |"
        )
    for field in report.fields:
        lines += [
            "",
            f"## {field.field_id}",
            "",
            f"Tracklets with no bright star in the cone: {field.tracklets_without_star}.",
            "",
            "| separation | area (arcmin²) | UNKNOWN built | density /arcmin² "
            "| unmasked / partial / all-masked | bit 12 on all | UNKNOWN rejected "
            "| KNOWN built | KNOWN density | UNKNOWN min SNR | UNKNOWN sharp max "
            "| UNKNOWN fit rms (\") | KNOWN min SNR | KNOWN sharp max | KNOWN fit rms (\") |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for b in field.bins:
            m = b.unknown_built_by_mask
            lines.append(
                f"| {b.label} | {b.area_arcmin2:.1f} | {b.unknown_built} "
                f"| {f(b.unknown_built_density, 4)} "
                f"| {m['unmasked']} / {m['partially_masked']} / {m['all_masked']} "
                f"| {b.unknown_built_halo_bit_all} | {b.unknown_rejected} | {b.known_built} "
                f"| {f(b.known_built_density, 4)} | {q(b.unknown_min_snr, 1)} "
                f"| {q(b.unknown_sharp_max)} | {q(b.unknown_fit_rms, 3)} "
                f"| {q(b.known_min_snr, 1)} | {q(b.known_sharp_max)} | {q(b.known_fit_rms, 3)} |"
            )
    by_id = {(r.field_id, r.tracklet_id): r for r in reviews}
    lines += [
        "",
        "## Visual sample (new fields)",
        "",
        f"Per field: up to {VISUAL_NEAR} built UNKNOWN within {NEAR_EDGE / 60:.0f}' of a "
        f"bright star, {VISUAL_FAR} built UNKNOWN beyond {BIN_EDGES[CONTROL_BIN] / 60:.0f}', "
        f"{VISUAL_KNOWN} built KNOWN; SHA-256 order. Strips as in AS-032.",
        "",
        "| field | tracklet | group | separation (\") | mask | min SNR | sharp max "
        "| fit rms | same source? | context | image |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in report.strips:
        r = by_id.get((s.field_id, s.tracklet_id))
        lines.append(
            f"| {s.field_id.split('-')[0]} | {s.tracklet_id} | {s.group} "
            f"| {f(s.separation_arcsec, 0)} | {s.mask_state} | {s.min_snr:.1f} "
            f"| {f(s.sharp_max)} | {s.fit_rms_residual_arcsec:.3f} "
            f"| {r.same_source_all_epochs if r else 'not reviewed'} | {r.context if r else ''} "
            f"| [{s.image}]({s.image}) |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    select = commands.add_parser("select", help="run the pre-registered selection")
    select.add_argument("--out", type=Path, required=True)
    evidence = commands.add_parser("evidence", help="radial evidence + strips")
    evidence.add_argument("--fields", type=Path, required=True)
    evidence.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "select":
        selection = select_fields(progress=lambda m: print(m, flush=True))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(selection.model_dump_json(indent=1) + "\n")
        print(f"wrote {args.out}")
    else:
        selection = FieldSelection.model_validate_json(args.fields.read_text())
        report, skybot = run_evidence(
            selection, args.out_dir, progress=lambda m: print(m, flush=True)
        )
        (args.out_dir / "as033_bright_stars.json").write_text(
            report.model_dump_json() + "\n"
        )
        (args.out_dir / "as033_skybot.json").write_text(
            json.dumps(
                {k: [f.model_dump(mode="json") for f in v] for k, v in skybot.items()}
            )
            + "\n"
        )
        review_path = args.out_dir / "visual_review.json"
        reviews = (
            [VisualReview.model_validate(r) for r in json.loads(review_path.read_text())]
            if review_path.exists()
            else []
        )
        (args.out_dir / "as033_bright_stars.md").write_text(
            render_markdown(report, reviews)
        )
        print(f"wrote {args.out_dir}")


if __name__ == "__main__":
    main()
