"""AS-032: masked UNKNOWN tracklets in AS-022 fields B and D (research).

Evidence only — no filter, score, rank or threshold is derived here.

1. Mask semantics: ZTF PSF-catalog `flags` (ZSDS Explanatory Supplement
   v5.0, §10.6) is the bitwise OR of the science-image mask (§10.3) over a
   5×5 pixel box around the source; bit 0 = aircraft/satellite track,
   bit 8 = saturated, bit 12 = halo from a bright source (a circular region
   around Tycho-2 stars with V ≤ 6.5, §6.5 step 16).
2. Every tracklet of the two fields is put in context: per-detection mask
   bits, distance to the field's bright halo star, shared detections, and
   the AS-031 quality features.
3. A deterministic, stratified sample (SHA-256 of field and tracklet id,
   not pipeline output) is rendered through the existing cutout → display
   → WCS projection endpoints as E1|E2|E3 strips for visual review.

Usage (from backend/, needs IRSA; ~1.5 min):
    python -m app.validation.masked --out-dir validation/results/as032
"""

import argparse
import base64
import hashlib
import json
import math
import statistics
import struct
import zlib
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path

import numpy
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.models.identification import IdentificationStatus
from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG
from app.models.quality import TrackletQualityFeatures
from app.models.tracklet import Tracklet, TrackletStatus
from app.services.astrometry import angular_distance_arcsec
from app.validation.data import CatalogFrames, load_catalog_frames
from app.validation.models import FieldSnapshot
from app.validation.presets import AS022_REPORT
from app.validation.quality import field_records
from app.validation.runner import ValidationReport


SOURCE = (
    "ZTF Science Data System Explanatory Supplement v5.0 (Masci et al., "
    "2020-06-10), https://irsa.ipac.caltech.edu/data/ZTF/docs/"
    "ztf_explanatory_supplement.pdf: §10.3 (p. 78) mask bits, §10.6 (p. 81) "
    "PSF-catalog flags and sharp, §6.5 steps 11 and 16 (pp. 25-26) track and "
    "halo masking, §13.3 item 1 (unmasked artifacts)."
)
MASK_BITS = {
    0: "AIRCRAFT/SATELLITE TRACK",
    1: "CONTAINS SEXTRACTOR DETECTION",
    2: "LOW RESPONSIVITY",
    3: "HIGH RESPONSIVITY",
    4: "NOISY",
    5: "GHOST FROM BRIGHT SOURCE",
    6: "GHOST FROM CHARGE SPILLAGE (ONLY FOR OBSMJD <= 58779)",
    7: "PIXEL SPIKE (POSSIBLE RAD HIT)",
    8: "SATURATED",
    9: "DEAD (UNRESPONSIVE)",
    10: "NAN (not a number)",
    11: "CONTAINS PSF-EXTRACTED SOURCE POSITION",
    12: "HALO FROM BRIGHT SOURCE",
}


class HaloStar(BaseModel):
    tycho_id: str
    ra: float
    dec: float
    vt_mag: float


# The Tycho-2 star (VizieR I/259, cone 15' around the centroid of the
# field's bit-12 detections, VT < 8, queried 2026-09-30) that the ZSDS halo
# masking (V <= 6.5) refers to. Reference data for this study only.
HALO_STARS = {
    "B-2019-01-25-565-c13-q3": HaloStar(
        tycho_id="TYC 1359-2673-1", ra=111.93481979, dec=21.44525990, vt_mag=5.283
    ),
    "D-2019-06-02-281-c16-q3": HaloStar(
        tycho_id="TYC 6246-168-1", ra=261.17512680, dec=-21.44147779, vt_mag=5.934
    ),
}
HALO_BIT = 12
TRACK_BIT = 0
SAMPLE_SALT = "AS-032"
# Sample sizes per field (stratum -> tracklets). KNOWN: all.
MASKED_SAMPLE = 8
PARTIAL_SAMPLE = 2
UNMASKED_SAMPLE = 3
MIN_STRIP_ARCSEC = 45.0
STRIP_MARGIN_ARCSEC = 15.0


class DetectionContext(BaseModel):
    epoch: int
    product_id: int
    source_id: str
    ra: float
    dec: float
    mask_bits: list[int]
    on_image_edge: bool
    snr: float
    magnitude: float
    sharp: float | None
    halo_distance_arcsec: float
    in_other_tracklets: int


class TrackletContext(BaseModel):
    field_id: str
    tracklet_id: str
    identification_status: IdentificationStatus
    known_designation: str | None
    stratum: str
    mask_pattern: int
    inside_halo: bool
    all_detections_halo_bit: bool
    any_detection_track_bit: bool
    shared_detections: int
    features: TrackletQualityFeatures
    detections: list[DetectionContext]


class GroupCount(BaseModel):
    group: str
    tracklets: int
    inside_halo: int
    halo_bit_all: int
    track_bit_any: int
    with_shared_detection: int
    median_min_snr: float | None
    median_sharp_max: float | None
    median_fit_rms_arcsec: float | None


class FieldMaskEvidence(BaseModel):
    field_id: str
    halo_star: HaloStar
    halo_radius_arcsec: float
    quadrant_area_arcmin2: float
    halo_area_fraction: float
    catalog_rows_per_bit: list[dict[int, int]]
    unflagged_detections_inside_radius: int
    groups: list[GroupCount]
    built_unknown_density_inside_per_arcmin2: float
    built_unknown_density_outside_per_arcmin2: float


class SampledTracklet(BaseModel):
    context: TrackletContext
    image: str
    cutout_center: tuple[float, float]
    cutout_size_arcsec: float


class MaskEvidenceReport(BaseModel):
    generated_at: datetime
    source: str
    mask_bits: dict[int, str]
    sample_rule: str
    fields: list[FieldMaskEvidence]
    sample: list[SampledTracklet]


def bits_of(value: int) -> list[int]:
    return [bit for bit in range(32) if value >> bit & 1]


def stratum_of(status: IdentificationStatus, features: TrackletQualityFeatures) -> str:
    """Descriptive stratum (built tracklets); no judgement implied."""
    if features.tracklet_status is not TrackletStatus.TRACKLET_BUILT:
        return "rejected"
    if status is IdentificationStatus.KNOWN:
        return "known"
    if status is IdentificationStatus.AMBIGUOUS:
        return "ambiguous"
    masked = features.masked_detection_count
    if masked == features.detection_count:
        return "masked_unknown"
    return "partially_masked_unknown" if masked else "unmasked_unknown"


def sample_key(field_id: str, tracklet_id: str) -> str:
    return hashlib.sha256(
        f"{SAMPLE_SALT}:{field_id}:{tracklet_id}".encode()
    ).hexdigest()


def allocate(sizes: dict[int, int], total: int) -> dict[int, int]:
    """Per-pattern sample sizes: >= 1 per pattern, rest by largest remainder."""
    patterns = sorted(sizes)
    if total <= len(patterns):
        # Too few slots for every pattern: the most populated patterns win.
        chosen = sorted(patterns, key=lambda p: (-sizes[p], p))[:total]
        return {p: int(p in chosen) for p in patterns}
    counts = {p: 1 for p in patterns}
    remaining = total - len(patterns)
    population = sum(sizes[p] - 1 for p in patterns)
    if population <= 0:
        return {p: min(counts[p], sizes[p]) for p in patterns}
    quotas = {p: remaining * (sizes[p] - 1) / population for p in patterns}
    for p in patterns:
        counts[p] += int(quotas[p])
    leftover = remaining - sum(int(q) for q in quotas.values())
    for p in sorted(patterns, key=lambda p: (-(quotas[p] - int(quotas[p])), p))[
        :leftover
    ]:
        counts[p] += 1
    return {p: min(counts[p], sizes[p]) for p in patterns}


def draw_sample(contexts: Sequence[TrackletContext]) -> list[TrackletContext]:
    """Deterministic stratified sample of one field's tracklets."""

    def ordered(items):
        return sorted(items, key=lambda c: sample_key(c.field_id, c.tracklet_id))

    by_stratum: dict[str, list[TrackletContext]] = {}
    for context in contexts:
        by_stratum.setdefault(context.stratum, []).append(context)

    picked = ordered(by_stratum.get("known", []))
    masked = by_stratum.get("masked_unknown", [])
    by_pattern: dict[int, list[TrackletContext]] = {}
    for context in masked:
        by_pattern.setdefault(context.mask_pattern, []).append(context)
    sizes = allocate({p: len(v) for p, v in by_pattern.items()}, MASKED_SAMPLE)
    for pattern in sorted(by_pattern):
        picked += ordered(by_pattern[pattern])[: sizes[pattern]]
    picked += ordered(by_stratum.get("partially_masked_unknown", []))[:PARTIAL_SAMPLE]
    picked += ordered(by_stratum.get("unmasked_unknown", []))[:UNMASKED_SAMPLE]
    return picked


def tracklet_contexts(
    snapshot: FieldSnapshot,
    catalogs: CatalogFrames,
    star: HaloStar,
    halo_radius: float,
) -> list[TrackletContext]:
    records, _, _ = field_records(
        snapshot, catalogs, EXPERIMENTAL_DEFAULT_CONFIG, keep_all_tracklets=True
    )
    tracklets: list[Tracklet] = [record.tracklet for record in records]
    usage = Counter(
        item.detection.source_id
        for tracklet in tracklets
        for item in tracklet.detections
    )
    epochs = {o.product_id: i for i, o in enumerate(snapshot.observations)}
    contexts = []
    for record, tracklet in zip(records, tracklets):
        detections = [
            DetectionContext(
                epoch=epochs[item.detection.observation_product_id],
                product_id=item.detection.observation_product_id,
                source_id=item.detection.source_id,
                ra=item.detection.ra,
                dec=item.detection.dec,
                mask_bits=bits_of(item.detection.mask_bits),
                on_image_edge=item.detection.on_image_edge,
                snr=item.detection.snr,
                magnitude=item.detection.magnitude,
                sharp=catalogs.sharp_by_source_id.get(item.detection.source_id),
                halo_distance_arcsec=angular_distance_arcsec(
                    item.detection.ra, item.detection.dec, star.ra, star.dec
                ),
                in_other_tracklets=usage[item.detection.source_id] - 1,
            )
            for item in tracklet.detections
        ]
        contexts.append(
            TrackletContext(
                field_id=record.field_id,
                tracklet_id=tracklet.tracklet_id,
                identification_status=record.identification_status,
                known_designation=record.known_designation,
                stratum=stratum_of(record.identification_status, record.features),
                mask_pattern=record.features.mask_bits_union,
                inside_halo=all(
                    d.halo_distance_arcsec <= halo_radius for d in detections
                ),
                all_detections_halo_bit=all(
                    HALO_BIT in d.mask_bits for d in detections
                ),
                any_detection_track_bit=any(
                    TRACK_BIT in d.mask_bits for d in detections
                ),
                shared_detections=sum(d.in_other_tracklets > 0 for d in detections),
                features=record.features,
                detections=detections,
            )
        )
    return contexts


def halo_geometry(
    snapshot: FieldSnapshot, star: HaloStar, radius_arcsec: float, grid: int = 400
) -> tuple[float, float]:
    """Quadrant area (arcmin², first frame footprint) and the fraction of it
    inside the halo disk, on a fixed grid in the tangent plane at the star."""
    corners = numpy.array(
        [_tangent(ra, dec, star) for ra, dec in snapshot.frame_metadata[0].corners]
    )
    # IRSA's corner order varies: order them around their mean first.
    center = corners.mean(axis=0)
    corners = corners[
        numpy.argsort(
            numpy.arctan2(corners[:, 1] - center[1], corners[:, 0] - center[0])
        )
    ]
    xs = numpy.linspace(corners[:, 0].min(), corners[:, 0].max(), grid)
    ys = numpy.linspace(corners[:, 1].min(), corners[:, 1].max(), grid)
    gx, gy = numpy.meshgrid(xs, ys)
    inside = _in_polygon(gx, gy, corners)
    x, y = corners[:, 0], corners[:, 1]
    area = 0.5 * abs(numpy.dot(x, numpy.roll(y, 1)) - numpy.dot(y, numpy.roll(x, 1)))
    in_halo = inside & (numpy.hypot(gx, gy) <= radius_arcsec)
    return float(area / 3600.0), float(in_halo.sum() / inside.sum())


def _tangent(ra: float, dec: float, star: HaloStar) -> tuple[float, float]:
    """Gnomonic offsets (arcsec) of (ra, dec) from the star."""
    ra0, dec0, ra1, dec1 = map(math.radians, (star.ra, star.dec, ra, dec))
    cos_c = math.sin(dec0) * math.sin(dec1) + math.cos(dec0) * math.cos(
        dec1
    ) * math.cos(ra1 - ra0)
    x = math.cos(dec1) * math.sin(ra1 - ra0) / cos_c
    y = (
        math.cos(dec0) * math.sin(dec1)
        - math.sin(dec0) * math.cos(dec1) * math.cos(ra1 - ra0)
    ) / cos_c
    return math.degrees(x) * 3600.0, math.degrees(y) * 3600.0


def _in_polygon(x, y, polygon) -> numpy.ndarray:
    """Even-odd rule; `polygon` vertices in order around the boundary."""
    inside = numpy.zeros(x.shape, dtype=bool)
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        crosses = (y1 > y) != (y2 > y)
        with numpy.errstate(divide="ignore", invalid="ignore"):
            at = (x2 - x1) * (y - y1) / (y2 - y1) + x1
        inside ^= crosses & (x < at)
    return inside


def group_counts(contexts: Sequence[TrackletContext]) -> list[GroupCount]:
    def median(values):
        values = [v for v in values if v is not None]
        return statistics.median(values) if values else None

    groups: dict[str, list[TrackletContext]] = {}
    for context in contexts:
        groups.setdefault(context.stratum, []).append(context)
    order = [
        "known",
        "masked_unknown",
        "partially_masked_unknown",
        "unmasked_unknown",
        "ambiguous",
        "rejected",
    ]
    return [
        GroupCount(
            group=name,
            tracklets=len(items),
            inside_halo=sum(c.inside_halo for c in items),
            halo_bit_all=sum(c.all_detections_halo_bit for c in items),
            track_bit_any=sum(c.any_detection_track_bit for c in items),
            with_shared_detection=sum(c.shared_detections > 0 for c in items),
            median_min_snr=median(c.features.min_snr for c in items),
            median_sharp_max=median(c.features.sharp_max for c in items),
            median_fit_rms_arcsec=median(
                c.features.fit_rms_residual_arcsec for c in items
            ),
        )
        for name in order
        if (items := groups.get(name))
    ]


def field_evidence(
    snapshot: FieldSnapshot,
    catalogs: CatalogFrames,
    star: HaloStar,
    catalog_rows_per_bit: list[dict[int, int]],
) -> tuple[FieldMaskEvidence, list[TrackletContext]]:
    detections = [d for frame in catalogs.frames for d in frame.detections]
    distances = [
        angular_distance_arcsec(d.ra, d.dec, star.ra, star.dec) for d in detections
    ]
    halo_distances = [
        r for d, r in zip(detections, distances) if d.mask_bits >> HALO_BIT & 1
    ]
    # Halo disk radius as measured: the farthest halo-flagged detection
    # (the flag covers a 5x5 box, so this includes up to ~3" of padding).
    radius = max(halo_distances)
    contexts = tracklet_contexts(snapshot, catalogs, star, radius)
    area, fraction = halo_geometry(snapshot, star, radius)
    built_unknown = [
        c
        for c in contexts
        if c.stratum
        in ("masked_unknown", "partially_masked_unknown", "unmasked_unknown")
    ]
    inside = sum(c.inside_halo for c in built_unknown)
    evidence = FieldMaskEvidence(
        field_id=snapshot.field.field_id,
        halo_star=star,
        halo_radius_arcsec=round(radius, 1),
        quadrant_area_arcmin2=round(area, 1),
        halo_area_fraction=round(fraction, 4),
        catalog_rows_per_bit=catalog_rows_per_bit,
        unflagged_detections_inside_radius=sum(
            r <= radius and not d.mask_bits >> HALO_BIT & 1
            for d, r in zip(detections, distances)
        ),
        groups=group_counts(contexts),
        built_unknown_density_inside_per_arcmin2=round(inside / (area * fraction), 4),
        built_unknown_density_outside_per_arcmin2=round(
            (len(built_unknown) - inside) / (area * (1 - fraction)), 4
        ),
    )
    return evidence, contexts


# --- evidence strips through the existing cutout/projection endpoints ---

TRACK_COLOR = (255, 181, 71)
OTHER_COLOR = (150, 105, 40)
PANEL_PIXELS = 240
GAP_PIXELS = 6


def strip_geometry(
    positions: Sequence[tuple[float, float]],
) -> tuple[tuple[float, float], float]:
    center = _mean(positions)
    extent = max(angular_distance_arcsec(*center, ra, dec) for ra, dec in positions)
    size = min(300.0, max(MIN_STRIP_ARCSEC, 2 * extent + 2 * STRIP_MARGIN_ARCSEC))
    return center, math.ceil(size)


def render_strip(
    client: TestClient,
    product_ids: Sequence[int],
    center: tuple[float, float],
    size: float,
    positions: Sequence[tuple[float, float]],
    epochs: Sequence[int],
) -> numpy.ndarray:
    """E1|E2|E3 panels: the displayed cutout of each frame with an open
    crosshair on that frame's detection and rings on the others."""
    panels = []
    for epoch, product_id in enumerate(product_ids):
        params = {
            "product_id": product_id,
            "ra": center[0],
            "dec": center[1],
            "size_arcsec": size,
        }
        body = client.get("/api/frames/cutout", params=params)
        if body.status_code != 200:
            raise RuntimeError(f"cutout {product_id}: {body.json()}")
        frame = body.json()
        projected = client.post(
            "/api/frames/project",
            json={
                **params,
                "positions": [{"ra": ra, "dec": dec} for ra, dec in positions],
            },
        ).json()["points"]
        gray = numpy.frombuffer(
            base64.b64decode(frame["pixels_base64"]), dtype=numpy.uint8
        )
        gray = gray.reshape(frame["height"], frame["width"])
        zoom = max(1, PANEL_PIXELS // max(frame["width"], frame["height"]))
        rgb = numpy.repeat(numpy.repeat(gray, zoom, 0), zoom, 1)[..., None].repeat(3, 2)
        for point, detection_epoch in zip(projected, epochs):
            if point is None:
                continue
            x = (point["x"] + 0.5) * zoom
            y = (point["y"] + 0.5) * zoom
            if detection_epoch == epoch:
                _crosshair(rgb, x, y, TRACK_COLOR)
            else:
                _ring(rgb, x, y, 5, OTHER_COLOR)
        panels.append(rgb)
    height = max(p.shape[0] for p in panels)
    padded = [
        numpy.pad(p, ((0, height - p.shape[0]), (0, GAP_PIXELS), (0, 0)))
        for p in panels
    ]
    return numpy.concatenate(padded, axis=1)[:, :-GAP_PIXELS]


def _crosshair(rgb, x, y, color, gap=6, arm=9) -> None:
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for t in range(gap, gap + arm):
            for w in (-0.5, 0.5):
                _set(rgb, x + dx * t + dy * w, y + dy * t + dx * w, color)


def _ring(rgb, x, y, radius, color) -> None:
    for step in range(64):
        angle = 2 * math.pi * step / 64
        _set(rgb, x + radius * math.cos(angle), y + radius * math.sin(angle), color)


def _set(rgb, x, y, color) -> None:
    row, column = int(math.floor(y)), int(math.floor(x))
    if 0 <= row < rgb.shape[0] and 0 <= column < rgb.shape[1]:
        rgb[row, column] = color


def write_png(path: Path, rgb: numpy.ndarray) -> None:
    """Minimal 8-bit RGB PNG writer (no imaging dependency needed)."""
    height, width, _ = rgb.shape
    raw = b"".join(
        b"\x00" + rgb[row].astype(numpy.uint8).tobytes() for row in range(height)
    )

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def _mean(positions) -> tuple[float, float]:
    x = y = z = 0.0
    for ra, dec in positions:
        ra_r, dec_r = math.radians(ra), math.radians(dec)
        x += math.cos(dec_r) * math.cos(ra_r)
        y += math.cos(dec_r) * math.sin(ra_r)
        z += math.sin(dec_r)
    return (
        math.degrees(math.atan2(y, x)) % 360.0,
        math.degrees(math.atan2(z, math.hypot(x, y))),
    )


def run_mask_evidence(
    out_dir: Path,
    report_path: Path = AS022_REPORT,
    loader: Callable[..., CatalogFrames] = load_catalog_frames,
    progress: Callable[[str], None] = lambda message: None,
) -> MaskEvidenceReport:
    from app.main import app

    report = ValidationReport.model_validate_json(report_path.read_text())
    snapshots = {s.field.field_id: s for s in report.snapshots}
    client = TestClient(app)
    fields, sample = [], []
    image_dir = out_dir / "strips"
    image_dir.mkdir(parents=True, exist_ok=True)
    for field_id, star in HALO_STARS.items():
        snapshot = snapshots[field_id]
        progress(f"{field_id}: loading PSF catalogs")
        catalogs, rows_per_bit = _load_with_bit_counts(snapshot, loader)
        evidence, contexts = field_evidence(snapshot, catalogs, star, rows_per_bit)
        fields.append(evidence)
        product_ids = [o.product_id for o in snapshot.observations]
        for context in draw_sample(contexts):
            positions = [(d.ra, d.dec) for d in context.detections]
            center, size = strip_geometry(positions)
            progress(f"{field_id}: strip {context.tracklet_id} ({context.stratum})")
            strip = render_strip(
                client,
                product_ids,
                center,
                size,
                positions,
                [d.epoch for d in context.detections],
            )
            name = f"{field_id[0]}_{context.stratum}_{context.tracklet_id}.png"
            write_png(image_dir / name, strip)
            sample.append(
                SampledTracklet(
                    context=context,
                    image=f"strips/{name}",
                    cutout_center=(round(center[0], 7), round(center[1], 7)),
                    cutout_size_arcsec=size,
                )
            )
    return MaskEvidenceReport(
        generated_at=datetime.now(timezone.utc),
        source=SOURCE,
        mask_bits=MASK_BITS,
        sample_rule=(
            "Per field: every built KNOWN tracklet; masked_unknown (all detections "
            f"masked, built) {MASKED_SAMPLE} tracklets allocated over mask patterns "
            "(>= 1 each, rest by largest remainder); "
            f"{PARTIAL_SAMPLE} partially masked and {UNMASKED_SAMPLE} unmasked built "
            "UNKNOWN. Within a stratum, order by SHA-256('AS-032:<field>:<tracklet>')."
        ),
        fields=fields,
        sample=sample,
    )


def _load_with_bit_counts(snapshot, loader):
    catalogs = loader(snapshot.observations)
    rows_per_bit = []
    for frame in catalogs.frames:
        counts: Counter[int] = Counter()
        for detection in frame.detections:
            counts.update(bits_of(detection.mask_bits))
        rows_per_bit.append(dict(sorted(counts.items())))
    return catalogs, rows_per_bit


# --- report ---


class VisualReview(BaseModel):
    """One human/agent look at a strip; free text plus coarse labels."""

    tracklet_id: str
    field_id: str
    same_source_all_epochs: str  # yes / no / unclear
    source_visible_each_epoch: str  # e.g. "yes,yes,no"
    context: str
    notes: str


def render_markdown(report: MaskEvidenceReport, reviews: Sequence[VisualReview]) -> str:
    lines = [
        "# AS-032 masked-tracklet evidence (generated)",
        "",
        f"Generated {report.generated_at:%Y-%m-%d %H:%M UTC}. Source: {report.source}",
        "",
        "Evidence only; no filter, score, rank or threshold. Interpretation: "
        "`as032_findings.md`.",
        "",
        "## ZTF mask bits seen in these catalogs (ZSDS §10.3)",
        "",
    ]
    seen = sorted(
        {b for f in report.fields for row in f.catalog_rows_per_bit for b in row}
    )
    lines += [f"- bit {b}: {report.mask_bits.get(b, 'unknown')}" for b in seen]
    for f in report.fields:
        star = f.halo_star
        lines += [
            "",
            f"## {f.field_id}",
            "",
            f"Halo star {star.tycho_id} (VT {star.vt_mag}) at ({star.ra:.5f}, "
            f'{star.dec:.5f}); measured halo radius {f.halo_radius_arcsec:.0f}" '
            f"(farthest bit-12 detection); halo covers {100 * f.halo_area_fraction:.1f}% "
            f"of the {f.quadrant_area_arcmin2:.0f} arcmin² quadrant. Detections without "
            f"bit 12 inside that radius: {f.unflagged_detections_inside_radius}.",
            "",
            "Catalog rows per mask bit (E1, E2, E3): "
            + "; ".join(str(row) for row in f.catalog_rows_per_bit),
            "",
            "| stratum | tracklets | inside halo | bit 12 on all | bit 0 on any "
            '| shared detection | median min SNR | median sharp max | median fit rms (") |',
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for g in f.groups:
            lines.append(
                f"| {g.group} | {g.tracklets} | {g.inside_halo} | {g.halo_bit_all} "
                f"| {g.track_bit_any} | {g.with_shared_detection} "
                f"| {_fmt(g.median_min_snr)} | {_fmt(g.median_sharp_max)} "
                f"| {_fmt(g.median_fit_rms_arcsec)} |"
            )
        lines += [
            "",
            "Built UNKNOWN tracklets per arcmin²: inside halo "
            f"{f.built_unknown_density_inside_per_arcmin2:.3f}, outside "
            f"{f.built_unknown_density_outside_per_arcmin2:.4f}.",
        ]

    by_id = {(r.field_id, r.tracklet_id): r for r in reviews}
    lines += [
        "",
        "## Sample and visual review",
        "",
        f"Rule: {report.sample_rule}",
        "",
        "Strips: E1 | E2 | E3 cutouts from /api/frames/cutout (per-frame zscale, "
        "north up, east left), markers from /api/frames/project: open crosshair on "
        "that frame's detection, rings on the other epochs' detections.",
        "",
        "| field | tracklet | stratum | mask bits per detection | min SNR "
        '| sharp | fit rms | halo dist (") | shared | same source? | visible '
        "| context | image |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for item in report.sample:
        c = item.context
        review = by_id.get((c.field_id, c.tracklet_id))
        lines.append(
            f"| {c.field_id[0]} | {c.tracklet_id} | {c.stratum}"
            + (f" ({c.known_designation})" if c.known_designation else "")
            + f" | {' / '.join(','.join(map(str, d.mask_bits)) or '–' for d in c.detections)}"
            f" | {c.features.min_snr:.1f}"
            f" | {' / '.join(_fmt(d.sharp, 2) for d in c.detections)}"
            f" | {c.features.fit_rms_residual_arcsec:.3f}"
            f" | {min(d.halo_distance_arcsec for d in c.detections):.0f}"
            f" | {c.shared_detections}"
            f" | {review.same_source_all_epochs if review else 'not reviewed'}"
            f" | {review.source_visible_each_epoch if review else ''}"
            f" | {review.context if review else ''}"
            f" | [{item.image}]({item.image}) |"
        )
    return "\n".join(lines) + "\n"


def _fmt(value, digits: int = 3) -> str:
    return "–" if value is None else f"{value:.{digits}f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    report = run_mask_evidence(
        args.out_dir, progress=lambda message: print(message, flush=True)
    )
    review_path = args.out_dir / "visual_review.json"
    reviews = (
        [VisualReview.model_validate(r) for r in json.loads(review_path.read_text())]
        if review_path.exists()
        else []
    )
    (args.out_dir / "as032_masked_tracklets.json").write_text(
        report.model_dump_json() + "\n"
    )
    (args.out_dir / "as032_masked_tracklets.md").write_text(
        render_markdown(report, reviews)
    )
    print(f"wrote {args.out_dir}")


if __name__ == "__main__":
    main()
