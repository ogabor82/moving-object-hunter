"""Validation runs, one-at-a-time parameter sweeps and report rendering."""

import statistics
from collections.abc import Callable, Sequence
from datetime import datetime, timezone

import httpx
from pydantic import BaseModel

from app.models.identification import IdentificationStatus
from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG
from app.models.tracklet import TrackletStatus
from app.validation.data import FieldData, load_field_data
from app.validation.evaluate import evaluate_field
from app.validation.models import (
    FieldRunResult,
    FieldSnapshot,
    PipelineConfig,
    TargetSelectionRule,
    TrackletFeatures,
    ValidationField,
    ValidationTarget,
)
from app.validation.selection import select_targets


# Reference point of the sweep: the experimental defaults (not calibrated).
REFERENCE_CONFIG = EXPERIMENTAL_DEFAULT_CONFIG
SWEEP_GRID: dict[str, list[float]] = {
    "stationary_tolerance_arcsec": [0.5, 1.0, 1.5, 2.0, 3.0],
    "max_rate_arcsec_per_min": [0.5, 0.75, 1.0, 1.5, 2.0],
    "search_radius_arcsec": [0.5, 1.0, 2.0, 3.0],
    "max_residual_arcsec": [0.25, 0.5, 1.0, 2.0],
    "match_radius_arcsec": [0.5, 1.0, 2.0, 5.0],
}


class SweepPoint(BaseModel):
    """Results of one configuration on every field (no tracklet features)."""

    parameter: str
    value: float
    config: PipelineConfig
    results: list[FieldRunResult]


class ValidationReport(BaseModel):
    """Machine-readable outcome of a validation run."""

    generated_at: datetime
    selection_rule: TargetSelectionRule
    reference_config: PipelineConfig
    snapshots: list[FieldSnapshot]
    reference_results: list[FieldRunResult]
    sweep: list[SweepPoint]


def sweep_configs(
    reference: PipelineConfig,
    grid: dict[str, list[float]],
) -> list[tuple[str, float, PipelineConfig]]:
    """One-at-a-time variations of `reference` (reference itself excluded)."""
    points = []
    for parameter, values in grid.items():
        for value in values:
            if getattr(reference, parameter) == value:
                continue
            points.append(
                (parameter, value, reference.model_copy(update={parameter: value}))
            )
    return points


def run_validation(
    fields: Sequence[ValidationField],
    rule: TargetSelectionRule = TargetSelectionRule(),
    reference: PipelineConfig = REFERENCE_CONFIG,
    grid: dict[str, list[float]] | None = None,
    client: httpx.Client | None = None,
    loader: Callable[[ValidationField, httpx.Client | None], FieldData] = (
        load_field_data
    ),
    progress: Callable[[str], None] = lambda message: None,
) -> ValidationReport:
    """Load every field once, select targets, run reference and sweep."""
    loaded: list[tuple[FieldData, list[ValidationTarget]]] = []
    for field in fields:
        progress(f"loading {field.field_id}")
        data = loader(field, client)
        targets = select_targets(
            field.field_id,
            data.frame_metadata,
            data.skybot_fields,
            rule,
            frozenset(field.control_designations),
        )
        loaded.append((data, targets))

    def run(config: PipelineConfig, keep_features: bool) -> list[FieldRunResult]:
        results = []
        for data, targets in loaded:
            result = evaluate_field(
                data.field.field_id,
                data.frames,
                data.skybot_fields,
                targets,
                config,
                data.sharp_by_source_id,
            )
            if not keep_features:
                result = result.model_copy(update={"tracklets": []})
            results.append(result)
        return results

    progress("reference config")
    reference_results = run(reference, keep_features=True)
    sweep = []
    for parameter, value, config in sweep_configs(reference, grid or SWEEP_GRID):
        progress(f"sweep {parameter}={value}")
        sweep.append(
            SweepPoint(
                parameter=parameter,
                value=value,
                config=config,
                results=run(config, keep_features=False),
            )
        )

    return ValidationReport(
        generated_at=datetime.now(timezone.utc),
        selection_rule=rule,
        reference_config=reference,
        snapshots=[
            FieldSnapshot(
                field=data.field,
                observations=data.observations,
                frame_metadata=data.frame_metadata,
                skybot_fields=data.skybot_fields,
                source_counts=[frame.source_count for frame in data.frames],
                targets=targets,
            )
            for data, targets in loaded
        ],
        reference_results=reference_results,
        sweep=sweep,
    )


def render_markdown(report: ValidationReport) -> str:
    """Human-readable summary tables generated from a ValidationReport."""
    lines = [
        "# AS-022 validation run",
        "",
        f"Generated: {report.generated_at.isoformat()}",
        "",
        "Reference config (sweep centre, not a validated default): "
        + _config_text(report.reference_config),
        "",
        "## Fields",
        "",
        "| field | frames (UTC) | filters | maglimit | sources | SkyBoT objects "
        "| primary | marginal | control |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for snapshot in report.snapshots:
        roles = [target.role for target in snapshot.targets]
        lines.append(
            f"| {snapshot.field.field_id} "
            f"| {', '.join(o.observed_at.strftime('%H:%M:%S') for o in snapshot.observations)} "
            f"| {''.join(o.filter_code[-1] for o in snapshot.observations)} "
            f"| {', '.join(f'{m.maglimit:.2f}' for m in snapshot.frame_metadata)} "
            f"| {', '.join(str(count) for count in snapshot.source_counts)} "
            f"| {', '.join(str(len(f.objects)) for f in snapshot.skybot_fields)} "
            f"| {roles.count('primary')} | {roles.count('marginal')} "
            f"| {roles.count('control')} |"
        )

    lines += [
        "",
        "## Targets at the reference config",
        "",
        "| field | designation | name | role | V | pred. rate (\"/min) "
        "| nearest det. (\") | cand. frames | result |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for snapshot, result in zip(report.snapshots, report.reference_results):
        targets = {target.designation: target for target in snapshot.targets}
        for outcome in result.targets:
            target = targets[outcome.designation]
            nearest = ", ".join(
                "-" if value is None else f"{value:.2f}"
                for value in outcome.nearest_detection_arcsec
            )
            verdict = (
                f"recovered ({outcome.tracklet_id}, "
                f"{outcome.max_residual_arcsec:.2f}\")"
                if outcome.recovered
                else _failure_reason(outcome)
            )
            lines.append(
                f"| {result.field_id} | {target.designation} | {target.name} "
                f"| {target.role} | {target.v_magnitude:.1f} "
                f"| {target.predicted_rate_arcsec_per_min:.3f} | {nearest} "
                f"| {outcome.candidate_frames}/3 | {verdict} |"
            )

    lines += [
        "",
        "## Parameter sweep (one at a time, all fields summed)",
        "",
        "| parameter | value | primary rec. | marginal rec. | control rec. "
        "| tracklets | built | known | unknown built | ambiguous |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    rows = [("reference", None, report.reference_results)] + [
        (point.parameter, point.value, point.results) for point in report.sweep
    ]
    for parameter, value, results in rows:
        lines.append(
            f"| {parameter} | {'' if value is None else value} "
            f"| {_ratio(results, 'primary')} | {_ratio(results, 'marginal')} "
            f"| {_ratio(results, 'control')} "
            f"| {sum(r.tracklet_count for r in results)} "
            f"| {sum(r.built_count for r in results)} "
            f"| {sum(r.known_count for r in results)} "
            f"| {sum(r.unknown_built_count for r in results)} "
            f"| {sum(r.ambiguous_count for r in results)} |"
        )

    lines += [
        "",
        "## Tracklet features at the reference config",
        "",
        "Groups: known = identified as KNOWN; unknown built = UNKNOWN with an "
        "accepted fit. Values: median [10th-90th percentile].",
        "",
        "| feature | known (n) | unknown built (n) |",
        "|---|---|---|",
    ]
    features = [f for result in report.reference_results for f in result.tracklets]
    known = [
        f for f in features if f.identification_status is IdentificationStatus.KNOWN
    ]
    unknown_built = [
        f
        for f in features
        if f.identification_status is IdentificationStatus.UNKNOWN
        and f.tracklet_status is TrackletStatus.TRACKLET_BUILT
    ]
    for label, getter in FEATURE_GETTERS.items():
        lines.append(
            f"| {label} | {_distribution(known, getter)} "
            f"| {_distribution(unknown_built, getter)} |"
        )
    lines += [
        "",
        "| known-object motion check | median [10th-90th] |",
        "|---|---|",
        "| fitted - predicted rate (\"/min) | "
        + _distribution(known, lambda f: f.rate_difference_arcsec_per_min)
        + " |",
        "| fitted - predicted PA (deg) | "
        + _distribution(known, lambda f: f.position_angle_difference_deg)
        + " |",
        "",
    ]
    return "\n".join(lines)


FEATURE_GETTERS: dict[str, Callable[[TrackletFeatures], float | None]] = {
    "min SNR": lambda f: f.min_snr,
    "median SNR": lambda f: f.median_snr,
    "magnitude spread (mag)": lambda f: f.magnitude_spread,
    "flagged detections": lambda f: float(f.flagged_detections),
    "min sharp": lambda f: min(
        (value for value in f.sharp_values if value is not None), default=None
    ),
    "max sharp": lambda f: max(
        (value for value in f.sharp_values if value is not None), default=None
    ),
    "rate (\"/min)": lambda f: f.rate_arcsec_per_min,
    "fit max residual (\")": lambda f: f.fit_max_residual_arcsec,
}


def _distribution(
    items: Sequence[TrackletFeatures],
    getter: Callable[[TrackletFeatures], float | None],
) -> str:
    values = sorted(v for v in (getter(item) for item in items) if v is not None)
    if not values:
        return "n/a (0)"
    if len(values) == 1:
        return f"{values[0]:.2f} (1)"
    deciles = statistics.quantiles(values, n=10, method="inclusive")
    return (
        f"{statistics.median(values):.2f} [{deciles[0]:.2f}-{deciles[-1]:.2f}] "
        f"({len(values)})"
    )


def _ratio(results: Sequence[FieldRunResult], role: str) -> str:
    targets = sum(getattr(r, f"{role}_targets") for r in results)
    recovered = sum(getattr(r, f"{role}_recovered") for r in results)
    return f"{recovered}/{targets}"


def _failure_reason(outcome) -> str:
    if outcome.detected_frames < 3:
        return f"missed: detected in {outcome.detected_frames}/3 frames"
    if outcome.candidate_frames < 3:
        return (
            f"missed: {3 - outcome.candidate_frames} detection(s) "
            "flagged stationary"
        )
    if outcome.identification_status is not None:
        return f"linked but {outcome.identification_status.value}"
    return "missed: detections not linked"


def _config_text(config: PipelineConfig) -> str:
    return ", ".join(f"{name}={value}" for name, value in config)
