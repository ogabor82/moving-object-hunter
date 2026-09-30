"""AS-031 quality-feature evidence on the frozen AS-022 fields.

Descriptive only: runs the unchanged pipeline (experimental default config)
on every AS-022 field, identifies against the frozen AS-022 SkyBoT snapshot
(as AS-024 does, so results do not drift with the SkyBoT database), extracts
TrackletQualityFeatures for every tracklet and summarises them per
population. No score, rank, filter or threshold is computed.

Usage (from backend/, needs IRSA for the archival PSF catalogs; ~2 min,
~5 GB peak memory for the crowded D field):
    python -m app.validation.quality \\
        --out-json validation/results/as031_quality_features.json \\
        --out-md validation/results/as031_quality_features.md
"""

import argparse
import statistics
import time
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path

import httpx
from pydantic import BaseModel

from app.models.identification import IdentificationStatus
from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG, PipelineConfig
from app.models.quality import SharpAvailability, TrackletQualityFeatures
from app.models.tracklet import Tracklet, TrackletStatus
from app.services.identification_service import match_tracklets_to_known_objects
from app.services.pipeline_service import build_tracklets_from_frames
from app.services.quality_service import extract_quality_features
from app.validation.data import CatalogFrames, load_catalog_frames
from app.validation.models import FieldSnapshot
from app.validation.presets import AS022_REPORT
from app.validation.runner import ValidationReport


CONTROL_DESIGNATION = "48606"  # 1995 DH, POC control


class Population(BaseModel):
    """Which descriptive group a tracklet belongs to (no quality judgement)."""

    name: str
    description: str


VALIDATION_TARGET = Population(
    name="validation_target_known",
    description="KNOWN, best match is a canonical (primary) AS-022 target",
)
CONTROL = Population(
    name="control_known",
    description="KNOWN, best match is a human-chosen POC control",
)
OTHER_KNOWN = Population(
    name="other_known",
    description="KNOWN, best match is any other known object (incl. marginal)",
)
AMBIGUOUS = Population(name="ambiguous", description="AMBIGUOUS identification")
UNKNOWN = Population(
    name="unknown",
    description="UNKNOWN: no known object matched (not a discovery)",
)


class QualityRecord(BaseModel):
    field_id: str
    population: str
    identification_status: IdentificationStatus
    known_designation: str | None
    target_role: str | None
    identification_max_residual_arcsec: float | None = None
    features: TrackletQualityFeatures
    tracklet: Tracklet | None = None  # kept for identified tracklets only


class FieldQuality(BaseModel):
    field_id: str
    product_ids: list[int]
    source_counts: list[int]
    candidate_counts: list[int]
    tracklet_count: int
    catalog_load_seconds: float
    build_seconds: float
    negative_flag_counts: dict[int, int]
    detections_without_sharp: int


class NumericSummary(BaseModel):
    count: int
    missing: int
    min: float | None
    p10: float | None
    p25: float | None
    median: float | None
    p75: float | None
    p90: float | None
    max: float | None


class GroupSummary(BaseModel):
    name: str
    description: str
    count: int
    numeric: dict[str, NumericSummary]
    detection_count: dict[int, int]
    flagged_detection_count: dict[int, int]
    edge_detection_count: dict[int, int]
    mask_bit_tracklets: dict[int, int]
    sharp_availability: dict[str, int]


class QualityEvidenceReport(BaseModel):
    generated_at: datetime
    config: PipelineConfig
    skybot_mode: str
    fields: list[FieldQuality]
    groups: list[GroupSummary]
    records: list[QualityRecord]


# Linear features summarised by percentiles. position_angle_deg is circular
# and depends on the field's sky position, so it is not pooled.
NUMERIC_FEATURES: dict[str, Callable[[TrackletQualityFeatures], float | None]] = {
    "min_snr": lambda f: f.min_snr,
    "median_snr": lambda f: f.median_snr,
    "magnitude_range_mag": lambda f: f.magnitude_range_mag,
    "magnitude_range_sigma": lambda f: f.magnitude_range_sigma,
    "sharp_min": lambda f: f.sharp_min,
    "sharp_max": lambda f: f.sharp_max,
    "angular_velocity_arcsec_per_min": lambda f: f.angular_velocity_arcsec_per_min,
    "fit_rms_residual_arcsec": lambda f: f.fit_rms_residual_arcsec,
    "fit_max_residual_arcsec": lambda f: f.fit_max_residual_arcsec,
}


def classify(
    status: IdentificationStatus,
    designation: str | None,
    roles: dict[str, str],
) -> Population:
    """Population of one identified tracklet, from its identification only."""
    if status is IdentificationStatus.UNKNOWN:
        return UNKNOWN
    if status is IdentificationStatus.AMBIGUOUS:
        return AMBIGUOUS
    role = roles.get(designation or "")
    if role == "primary":
        return VALIDATION_TARGET
    if role == "control":
        return CONTROL
    return OTHER_KNOWN


def field_records(
    snapshot: FieldSnapshot,
    catalogs: CatalogFrames,
    config: PipelineConfig,
    keep_all_tracklets: bool = False,
) -> tuple[list[QualityRecord], list[int], float]:
    """Build, identify (frozen SkyBoT) and extract features for one field.

    Records keep their Tracklet unless UNKNOWN (all with keep_all_tracklets).
    """
    started = time.perf_counter()
    pipeline = build_tracklets_from_frames(catalogs.frames, config)
    build_seconds = time.perf_counter() - started
    tracklets = pipeline.build.tracklets
    fields_by_product_id = {
        observation.product_id: skybot_field
        for observation, skybot_field in zip(
            snapshot.observations, snapshot.skybot_fields
        )
    }
    identifications = match_tracklets_to_known_objects(
        tracklets, fields_by_product_id, config.identification()
    ).identifications
    roles = {target.designation: target.role for target in snapshot.targets}

    records = []
    for tracklet, identification in zip(tracklets, identifications):
        designation = (
            identification.best_match.designation
            if identification.best_match
            else None
        )
        population = classify(identification.status, designation, roles)
        records.append(
            QualityRecord(
                field_id=snapshot.field.field_id,
                population=population.name,
                identification_status=identification.status,
                known_designation=designation,
                target_role=roles.get(designation or ""),
                identification_max_residual_arcsec=(
                    identification.best_match.max_residual_arcsec
                    if identification.best_match
                    else None
                ),
                features=extract_quality_features(
                    tracklet, catalogs.sharp_by_source_id
                ),
                tracklet=(
                    tracklet
                    if keep_all_tracklets or population is not UNKNOWN
                    else None
                ),
            )
        )
    candidate_counts = [frame.candidate_count for frame in pipeline.candidate_frames]
    return records, candidate_counts, build_seconds


def summarize(
    name: str, description: str, records: Sequence[QualityRecord]
) -> GroupSummary:
    features = [record.features for record in records]

    def counts(values) -> dict[int, int]:
        return dict(sorted(Counter(values).items()))

    bits: Counter[int] = Counter()
    for f in features:
        bits.update(bit for bit in range(32) if f.mask_bits_union >> bit & 1)
    return GroupSummary(
        name=name,
        description=description,
        count=len(features),
        numeric={
            key: numeric_summary([getter(f) for f in features])
            for key, getter in NUMERIC_FEATURES.items()
        },
        detection_count=counts(f.detection_count for f in features),
        flagged_detection_count=counts(f.flagged_detection_count for f in features),
        edge_detection_count=counts(f.edge_detection_count for f in features),
        mask_bit_tracklets=dict(sorted(bits.items())),
        sharp_availability={
            availability.value: sum(
                f.sharp_availability is availability for f in features
            )
            for availability in SharpAvailability
        },
    )


def numeric_summary(values: Sequence[float | None]) -> NumericSummary:
    present = sorted(v for v in values if v is not None)
    missing = len(values) - len(present)
    if not present:
        return NumericSummary(
            count=0, missing=missing, min=None, p10=None, p25=None,
            median=None, p75=None, p90=None, max=None,
        )
    if len(present) == 1:
        p10 = p25 = p75 = p90 = present[0]
    else:
        deciles = statistics.quantiles(present, n=10, method="inclusive")
        quartiles = statistics.quantiles(present, n=4, method="inclusive")
        p10, p90 = deciles[0], deciles[-1]
        p25, p75 = quartiles[0], quartiles[-1]
    return NumericSummary(
        count=len(present),
        missing=missing,
        min=present[0],
        p10=p10,
        p25=p25,
        median=statistics.median(present),
        p75=p75,
        p90=p90,
        max=present[-1],
    )


def summary_groups(
    records: Sequence[QualityRecord], crowded_field_id: str
) -> list[GroupSummary]:
    """The descriptive comparison groups (built tracklets unless noted)."""

    def pick(**conditions) -> list[QualityRecord]:
        status = conditions.pop("status", TrackletStatus.TRACKLET_BUILT)
        return [
            r
            for r in records
            if (status is None or r.features.tracklet_status is status)
            and all(getattr(r, key) == value for key, value in conditions.items())
        ]

    groups = [
        summarize(
            "validation_target_known",
            VALIDATION_TARGET.description + "; built; all fields",
            pick(population=VALIDATION_TARGET.name),
        ),
        summarize(
            "control_known",
            CONTROL.description + "; built",
            pick(population=CONTROL.name),
        ),
        summarize(
            "other_known",
            OTHER_KNOWN.description + "; built; all fields",
            pick(population=OTHER_KNOWN.name),
        ),
        summarize(
            "known_crowded_field",
            f"any KNOWN tracklet in {crowded_field_id}; built",
            [
                r
                for r in pick(field_id=crowded_field_id)
                if r.identification_status is IdentificationStatus.KNOWN
            ],
        ),
    ]
    for field_id in dict.fromkeys(r.field_id for r in records):
        groups.append(
            summarize(
                f"unknown_built:{field_id}",
                UNKNOWN.description + f"; built; {field_id}",
                pick(population=UNKNOWN.name, field_id=field_id),
            )
        )
    groups.append(
        summarize(
            f"unknown_rejected:{crowded_field_id}",
            UNKNOWN.description
            + f"; rejected by the fit residual limit; {crowded_field_id}",
            pick(
                population=UNKNOWN.name,
                field_id=crowded_field_id,
                status=TrackletStatus.REJECTED,
            ),
        )
    )
    groups.append(
        summarize(
            "ambiguous",
            AMBIGUOUS.description + "; any status; all fields",
            pick(population=AMBIGUOUS.name, status=None),
        )
    )
    return groups


def run_quality_evidence(
    report_path: Path = AS022_REPORT,
    config: PipelineConfig = EXPERIMENTAL_DEFAULT_CONFIG,
    field_ids: Sequence[str] | None = None,
    client: httpx.Client | None = None,
    loader: Callable[..., CatalogFrames] = load_catalog_frames,
    progress: Callable[[str], None] = lambda message: None,
) -> QualityEvidenceReport:
    """Features and group summaries for the AS-022 fields (all by default)."""
    report = ValidationReport.model_validate_json(report_path.read_text())
    snapshots = [
        s
        for s in report.snapshots
        if field_ids is None or s.field.field_id in field_ids
    ]
    records: list[QualityRecord] = []
    fields: list[FieldQuality] = []
    for snapshot in snapshots:
        progress(f"{snapshot.field.field_id}: loading PSF catalogs")
        started = time.perf_counter()
        catalogs = loader(snapshot.observations, client)
        load_seconds = time.perf_counter() - started
        progress(f"{snapshot.field.field_id}: building tracklets")
        field_result, candidate_counts, build_seconds = field_records(
            snapshot, catalogs, config
        )
        progress(
            f"{snapshot.field.field_id}: {len(field_result)} tracklets, "
            f"build {build_seconds:.1f} s"
        )
        records += field_result
        detection_ids = [
            d.source_id for frame in catalogs.frames for d in frame.detections
        ]
        fields.append(
            FieldQuality(
                field_id=snapshot.field.field_id,
                product_ids=[o.product_id for o in snapshot.observations],
                source_counts=[frame.source_count for frame in catalogs.frames],
                candidate_counts=candidate_counts,
                tracklet_count=len(field_result),
                catalog_load_seconds=round(load_seconds, 2),
                build_seconds=round(build_seconds, 2),
                negative_flag_counts=catalogs.negative_flag_counts,
                detections_without_sharp=sum(
                    source_id not in catalogs.sharp_by_source_id
                    for source_id in detection_ids
                ),
            )
        )

    crowded = max(fields, key=lambda f: f.tracklet_count).field_id if fields else ""
    return QualityEvidenceReport(
        generated_at=datetime.now(timezone.utc),
        config=config,
        skybot_mode="AS-022 snapshot",
        fields=fields,
        groups=summary_groups(records, crowded),
        records=records,
    )


def render_markdown(report: QualityEvidenceReport) -> str:
    lines = [
        "# AS-031 tracklet quality features (descriptive)",
        "",
        f"Generated {report.generated_at:%Y-%m-%d %H:%M UTC}; SkyBoT: "
        f"{report.skybot_mode}; config: experimental defaults "
        f"({report.config.model_dump()}).",
        "",
        "Measurements only. No feature is a filter, score or rank; group "
        "differences are observations, not classifier evidence (see "
        "as031_findings.md for selection effects).",
        "",
        "## Fields",
        "",
        "| field | sources/frame | candidates/frame | tracklets | catalog load (s) "
        "| build (s) | raw flags < 0 | detections without sharp |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for f in report.fields:
        lines.append(
            f"| {f.field_id} | {', '.join(map(str, f.source_counts))} "
            f"| {', '.join(map(str, f.candidate_counts))} | {f.tracklet_count} "
            f"| {f.catalog_load_seconds:.1f} | {f.build_seconds:.1f} "
            f"| {f.negative_flag_counts or 'none'} | {f.detections_without_sharp} |"
        )

    control = [
        r for r in report.records if r.known_designation == CONTROL_DESIGNATION
    ]
    lines += ["", "## Control 48606 (1995 DH)", ""]
    for record in control:
        lines += [
            f"{record.field_id}, {record.features.tracklet_id}, "
            f"{record.identification_status.value}:",
            "",
            "| feature | value |",
            "|---|---|",
            *(
                f"| {key} | {_value(value)} |"
                for key, value in record.features.model_dump(mode="json").items()
                if key not in ("tracklet_id",)
            ),
            "",
        ]
    if not control:
        lines.append("Not identified in this run.")

    lines += [
        "",
        "## Group summaries",
        "",
        "Cells: median [10th–90th percentile] (n with a value). "
        "Built tracklets unless the group says otherwise.",
        "",
    ]
    groups = [g for g in report.groups if g.count]
    lines.append("| feature | " + " | ".join(g.name for g in groups) + " |")
    lines.append("|---|" + "---|" * len(groups))
    lines.append("| tracklets | " + " | ".join(str(g.count) for g in groups) + " |")
    for key in NUMERIC_FEATURES:
        cells = []
        for g in groups:
            s = g.numeric[key]
            cells.append(
                "n/a"
                if s.median is None
                else f"{s.median:.3g} [{s.p10:.3g}–{s.p90:.3g}] ({s.count})"
            )
        lines.append(f"| {key} | " + " | ".join(cells) + " |")
    for key in ("detection_count", "flagged_detection_count", "edge_detection_count"):
        lines.append(
            f"| {key} | "
            + " | ".join(_counts(getattr(g, key)) for g in groups)
            + " |"
        )
    lines.append(
        "| tracklets per mask bit | "
        + " | ".join(_counts(g.mask_bit_tracklets, "bit ") for g in groups)
        + " |"
    )
    lines.append(
        "| sharp availability | "
        + " | ".join(_counts(g.sharp_availability) for g in groups)
        + " |"
    )
    lines += ["", "Group definitions:", ""]
    lines += [f"- `{g.name}`: {g.description}" for g in report.groups]
    return "\n".join(lines) + "\n"


def _counts(counts: dict, prefix: str = "") -> str:
    shown = {k: v for k, v in counts.items() if v}
    return ", ".join(f"{prefix}{k}: {v}" for k, v in shown.items()) or "—"


def _value(value) -> str:
    if isinstance(value, float):
        return f"{value:.4g}"
    if isinstance(value, list):
        return "[" + ", ".join(_value(v) for v in value) + "]"
    return "null" if value is None else str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    parser.add_argument("--field", action="append", help="limit to field id(s)")
    parser.add_argument(
        "--all-records",
        action="store_true",
        help="also write the per-tracklet features of UNKNOWN tracklets "
        "(~5 MB; the group summaries always cover them)",
    )
    args = parser.parse_args()

    report = run_quality_evidence(
        field_ids=args.field, progress=lambda message: print(message, flush=True)
    )
    if not args.all_records:
        report = report.model_copy(
            update={
                "records": [r for r in report.records if r.population != UNKNOWN.name]
            }
        )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(report.model_dump_json() + "\n")
    args.out_md.write_text(render_markdown(report))
    print(f"wrote {args.out_json} and {args.out_md}")


if __name__ == "__main__":
    main()
