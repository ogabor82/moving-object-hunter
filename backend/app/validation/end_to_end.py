"""AS-023: hard-coded end-to-end run on the canonical validation targets.

Runs the production path live, with no validation shortcuts:
IRSA metadata by product id → PSF catalogs → SourceDetection → stationary
matching → tracklets + fit → SkyBoT identification (identify_tracklets,
one live query per frame at mid-exposure, observer I41).

Usage (from backend/):
    python -m app.validation.end_to_end \
        --out-json validation/results/as023_end_to_end.json \
        --out-md validation/results/as023_end_to_end.md
"""

import argparse
from datetime import datetime, timezone
from pathlib import Path

import httpx
from pydantic import BaseModel

from app.models.identification import (
    IdentificationDiagnostics,
    IdentificationStatus,
    TrackletIdentification,
)
from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG, PipelineConfig
from app.models.tracklet import Tracklet, TrackletBuildDiagnostics
from app.services.astrometry import angular_distance_arcsec
from app.services.identification_service import identify_tracklets
from app.services.pipeline_service import build_tracklets_from_observations
from app.services.ztf_service import fetch_observations
from app.validation.models import ValidationTarget
from app.validation.runner import ValidationReport


AS022_REPORT = Path(__file__).parents[2] / "validation" / "results" / (
    "as022_validation.json"
)
CANONICAL_ROLE = "primary"


class CanonicalField(BaseModel):
    """A frozen validation field with its canonical (primary) targets."""

    field_id: str
    product_ids: list[int]
    targets: list[ValidationTarget]


class TargetEndToEnd(BaseModel):
    """End-to-end outcome for one canonical target."""

    designation: str
    name: str
    v_magnitude: float
    linked_tracklets: list[TrackletIdentification]
    correctly_identified: bool
    misidentified: bool


class FieldEndToEnd(BaseModel):
    field_id: str
    product_ids: list[int]
    source_counts: list[int]
    candidate_counts: list[int]
    build_diagnostics: TrackletBuildDiagnostics
    identification_diagnostics: IdentificationDiagnostics
    known_objects_per_frame: list[int]
    targets: list[TargetEndToEnd]


class EndToEndReport(BaseModel):
    generated_at: datetime
    config: PipelineConfig
    fields: list[FieldEndToEnd]
    canonical_targets: int
    correctly_identified: int
    misidentified: int
    passed: bool


def load_canonical_fields(report_path: Path = AS022_REPORT) -> list[CanonicalField]:
    """Frozen fields and primary targets from the AS-022 report."""
    report = ValidationReport.model_validate_json(report_path.read_text())
    fields = []
    for snapshot in report.snapshots:
        targets = [t for t in snapshot.targets if t.role == CANONICAL_ROLE]
        if targets:
            fields.append(
                CanonicalField(
                    field_id=snapshot.field.field_id,
                    product_ids=[o.product_id for o in snapshot.observations],
                    targets=targets,
                )
            )
    return fields


def run_end_to_end(
    fields: list[CanonicalField],
    config: PipelineConfig = EXPERIMENTAL_DEFAULT_CONFIG,
    client: httpx.Client | None = None,
    progress=lambda message: None,
) -> EndToEndReport:
    """Run the live production pipeline on every canonical field.

    PASS when at least one canonical target is linked and identified as
    KNOWN with its own designation, and no tracklet at a target's
    predicted positions is identified as a different known object.
    """
    results = []
    for field in fields:
        progress(f"{field.field_id}: fetching observations and catalogs")
        observations = fetch_observations(field.product_ids, client)
        pipeline = build_tracklets_from_observations(observations, config, client)
        progress(
            f"{field.field_id}: {len(pipeline.build.tracklets)} tracklets, "
            "identifying with SkyBoT"
        )
        identification = identify_tracklets(
            pipeline.build.tracklets,
            observations,
            config.identification(),
            client=client,
        )
        by_id = {i.tracklet_id: i for i in identification.identifications}
        product_order = [o.product_id for o in observations]
        results.append(
            FieldEndToEnd(
                field_id=field.field_id,
                product_ids=product_order,
                source_counts=[f.source_count for f in pipeline.frames],
                candidate_counts=[f.candidate_count for f in pipeline.candidate_frames],
                build_diagnostics=pipeline.build.diagnostics,
                identification_diagnostics=identification.diagnostics,
                known_objects_per_frame=[len(f.objects) for f in identification.fields],
                targets=[
                    _target_result(
                        target,
                        field.product_ids,
                        pipeline.build.tracklets,
                        by_id,
                        config.match_radius_arcsec,
                    )
                    for target in field.targets
                ],
            )
        )

    targets = [target for field in results for target in field.targets]
    correct = sum(target.correctly_identified for target in targets)
    wrong = sum(target.misidentified for target in targets)
    return EndToEndReport(
        generated_at=datetime.now(timezone.utc),
        config=config,
        fields=results,
        canonical_targets=len(targets),
        correctly_identified=correct,
        misidentified=wrong,
        passed=correct > 0 and wrong == 0,
    )


def _target_result(
    target: ValidationTarget,
    frozen_product_ids: list[int],
    tracklets: list[Tracklet],
    identifications: dict[str, TrackletIdentification],
    radius_arcsec: float,
) -> TargetEndToEnd:
    predicted = dict(zip(frozen_product_ids, target.predicted_positions))
    linked = [
        identifications[tracklet.tracklet_id]
        for tracklet in tracklets
        if all(
            item.detection.observation_product_id in predicted
            and angular_distance_arcsec(
                item.detection.ra,
                item.detection.dec,
                *predicted[item.detection.observation_product_id],
            )
            <= radius_arcsec
            for item in tracklet.detections
        )
    ]
    return TargetEndToEnd(
        designation=target.designation,
        name=target.name,
        v_magnitude=target.v_magnitude,
        linked_tracklets=linked,
        correctly_identified=any(
            i.status is IdentificationStatus.KNOWN
            and i.best_match.designation == target.designation
            for i in linked
        ),
        misidentified=any(
            i.status is IdentificationStatus.KNOWN
            and i.best_match.designation != target.designation
            for i in linked
        ),
    )


def render_markdown(report: EndToEndReport) -> str:
    lines = [
        "# AS-023 end-to-end run",
        "",
        f"Generated: {report.generated_at.isoformat()}",
        "",
        "Config (experimental defaults): "
        + ", ".join(f"{k}={v}" for k, v in report.config),
        "",
        f"**Verdict: {'PASS' if report.passed else 'FAIL'}** — "
        f"{report.correctly_identified}/{report.canonical_targets} canonical "
        f"targets linked and identified as the correct known object; "
        f"{report.misidentified} misidentified.",
        "",
        "| field | sources | candidates | tracklets (built) | known | unknown "
        "| ambiguous | SkyBoT objects |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for field in report.fields:
        build = field.build_diagnostics
        ident = field.identification_diagnostics
        built = build.tracklet_count - build.rejected_tracklet_count
        lines.append(
            f"| {field.field_id} | {', '.join(map(str, field.source_counts))} "
            f"| {', '.join(map(str, field.candidate_counts))} "
            f"| {build.tracklet_count} ({built}) "
            f"| {ident.known_count} | {ident.unknown_count} | {ident.ambiguous_count} "
            f"| {', '.join(map(str, field.known_objects_per_frame))} |"
        )
    lines += [
        "",
        "| field | designation | name | V | linked tracklets | identified as "
        "| max residual (\") | result |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for field in report.fields:
        for target in field.targets:
            identified = ", ".join(
                f"{i.status.value}:{i.best_match.designation}"
                if i.best_match
                else i.status.value
                for i in target.linked_tracklets
            )
            residuals = ", ".join(
                f"{i.best_match.max_residual_arcsec:.2f}"
                for i in target.linked_tracklets
                if i.best_match
            )
            result = (
                "correct"
                if target.correctly_identified and not target.misidentified
                else "MISIDENTIFIED"
                if target.misidentified
                else "not linked"
                if not target.linked_tracklets
                else "linked, not known"
            )
            lines.append(
                f"| {field.field_id} | {target.designation} | {target.name} "
                f"| {target.v_magnitude:.1f} "
                f"| {', '.join(i.tracklet_id for i in target.linked_tracklets) or '-'} "
                f"| {identified or '-'} | {residuals or '-'} | {result} |"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="AS-023 end-to-end run")
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args()

    report = run_end_to_end(
        load_canonical_fields(), progress=lambda m: print(m, flush=True)
    )
    args.out_json.write_text(report.model_dump_json() + "\n")
    args.out_md.write_text(render_markdown(report))
    print(render_markdown(report).split("\n")[6])
    raise SystemExit(0 if report.passed else 1)


if __name__ == "__main__":
    main()
