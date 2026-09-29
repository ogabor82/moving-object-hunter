"""AS-024: scientific acceptance test on the canonical validation targets.

Levels follow 05 – Scientific Validation, per canonical target:

A. Software      – the pipeline ran on the target's field.
B. Geometric     – a tracklet at the target's predicted positions exists,
                   has >= 3 detections and an accepted fit (tracklet_built).
C. Astrometric   – every detection is within `max_position_residual_arcsec`
                   of the frozen SkyBoT prediction, and the fitted motion
                   agrees with the predicted motion (rate and direction).
D. Identification – the tracklet is identified as KNOWN with the target's
                   own designation.

A target PASSES only if all four levels pass. The suite PASSES when no
identified target violates C or is misidentified, and at least
`regression_floor` canonical targets pass.

Reproducibility: by default SkyBoT predictions are replayed from the frozen
AS-022 snapshot (the SkyBoT database changes daily); IRSA products are
archival. `--live-skybot` queries SkyBoT instead.

Usage (from backend/):
    python -m app.validation.acceptance \
        --out-json validation/results/as024_acceptance.json \
        --out-md validation/results/as024_acceptance.md
"""

import argparse
import math
from datetime import datetime, timezone
from pathlib import Path

import httpx
from pydantic import BaseModel, Field

from app.models.identification import IdentificationStatus, TrackletIdentification
from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG, PipelineConfig
from app.models.tracklet import Tracklet, TrackletStatus
from app.services.astrometry import angular_distance_arcsec
from app.services.identification_service import (
    identify_tracklets,
    match_tracklets_to_known_objects,
)
from app.services.pipeline_service import build_tracklets_from_observations
from app.services.ztf_service import fetch_observations
from app.validation.end_to_end import CanonicalField, load_canonical_fields
from app.validation.models import ValidationTarget


class AcceptanceTolerances(BaseModel):
    """Explicit acceptance tolerances.

    Derived a priori from the error budget, then checked against AS-022:
    - position: ZTF PSF-catalog astrometry ~0.1-0.5" per detection plus
      SkyBoT ephemeris error (<= 1" by the target selection rule); AS-022
      recovered primaries: max 0.41".
    - rate: ~0.3" position error over a >= 60 min baseline gives
      sigma ~0.007"/min; tolerance ~3 sigma. AS-022 primaries: max 0.007.
    - direction: sigma_PA ~ sigma_rate / rate ~ 0.8 deg at 0.5"/min;
      tolerance ~2.5 sigma. AS-022 primaries: max 0.35 deg.
    """

    max_position_residual_arcsec: float = Field(default=1.0, gt=0)
    max_rate_difference_arcsec_per_min: float = Field(default=0.02, gt=0)
    max_position_angle_difference_deg: float = Field(default=2.0, gt=0)


# AS-022 baseline at the experimental defaults: 16/21 primary targets
# recovered. A regression floor, not a scientific requirement.
REGRESSION_FLOOR = 16


class TargetAcceptance(BaseModel):
    """Acceptance result of one canonical target."""

    field_id: str
    designation: str
    name: str
    v_magnitude: float
    software: bool
    geometric: bool
    astrometric: bool
    identification: bool
    passed: bool
    failed_level: str | None
    reason: str
    tracklet_id: str | None
    detections: int | None
    fit_max_residual_arcsec: float | None
    max_position_residual_arcsec: float | None
    rate_difference_arcsec_per_min: float | None
    position_angle_difference_deg: float | None
    identification_status: IdentificationStatus | None
    identified_as: str | None


class AcceptanceReport(BaseModel):
    generated_at: datetime
    skybot_mode: str
    config: PipelineConfig
    tolerances: AcceptanceTolerances
    regression_floor: int
    targets: list[TargetAcceptance]
    passed_targets: int
    misidentified_targets: int
    identified_but_astrometric_fail: int
    passed: bool
    verdict_reason: str


def evaluate_target(
    field_id: str,
    target: ValidationTarget,
    product_ids: list[int],
    tracklets: list[Tracklet],
    identifications: dict[str, TrackletIdentification],
    config: PipelineConfig,
    tolerances: AcceptanceTolerances,
) -> TargetAcceptance:
    """Apply levels A-D to one target (pure; the pipeline already ran)."""
    predicted = dict(zip(product_ids, target.predicted_positions))

    def residuals(tracklet: Tracklet) -> list[float] | None:
        values = []
        for item in tracklet.detections:
            position = predicted.get(item.detection.observation_product_id)
            if position is None:
                return None
            values.append(
                angular_distance_arcsec(
                    item.detection.ra, item.detection.dec, *position
                )
            )
        return values

    linked = []
    for tracklet in tracklets:
        values = residuals(tracklet)
        if values is not None and max(values) <= config.match_radius_arcsec:
            linked.append((tracklet, max(values)))
    # Prefer an accepted fit, then the closest to the prediction.
    linked.sort(
        key=lambda pair: (
            pair[0].status is not TrackletStatus.TRACKLET_BUILT,
            pair[1],
        )
    )

    base = dict(
        field_id=field_id,
        designation=target.designation,
        name=target.name,
        v_magnitude=target.v_magnitude,
        software=True,
    )
    if not linked:
        return TargetAcceptance(
            **base,
            geometric=False,
            astrometric=False,
            identification=False,
            passed=False,
            failed_level="geometric",
            reason="no tracklet at the predicted positions",
            tracklet_id=None,
            detections=None,
            fit_max_residual_arcsec=None,
            max_position_residual_arcsec=None,
            rate_difference_arcsec_per_min=None,
            position_angle_difference_deg=None,
            identification_status=None,
            identified_as=None,
        )

    tracklet, max_residual = linked[0]
    identification = identifications[tracklet.tracklet_id]
    rate_difference = (
        tracklet.angular_velocity_arcsec_per_min
        - target.predicted_rate_arcsec_per_min
    )
    angle_difference = (
        tracklet.position_angle_deg - target.predicted_position_angle_deg + 180.0
    ) % 360.0 - 180.0

    geometric = (
        len(tracklet.detections) >= 3
        and tracklet.status is TrackletStatus.TRACKLET_BUILT
    )
    astrometric = (
        max_residual <= tolerances.max_position_residual_arcsec
        and abs(rate_difference) <= tolerances.max_rate_difference_arcsec_per_min
        and abs(angle_difference) <= tolerances.max_position_angle_difference_deg
    )
    identified_as = (
        identification.best_match.designation if identification.best_match else None
    )
    identified = (
        identification.status is IdentificationStatus.KNOWN
        and identified_as == target.designation
    )

    failed_level = next(
        (
            level
            for level, ok in (
                ("geometric", geometric),
                ("astrometric", astrometric),
                ("identification", identified),
            )
            if not ok
        ),
        None,
    )
    reason = {
        None: "all levels pass",
        "geometric": f"tracklet fit status {tracklet.status.value}",
        "astrometric": (
            f"max residual {max_residual:.2f}\", rate diff "
            f"{rate_difference:+.4f}\"/min, PA diff {angle_difference:+.2f} deg"
        ),
        "identification": (
            f"identified {identification.status.value}"
            + (f" as {identified_as}" if identified_as else "")
        ),
    }[failed_level]

    return TargetAcceptance(
        **base,
        geometric=geometric,
        astrometric=astrometric,
        identification=identified,
        passed=failed_level is None,
        failed_level=failed_level,
        reason=reason,
        tracklet_id=tracklet.tracklet_id,
        detections=len(tracklet.detections),
        fit_max_residual_arcsec=tracklet.fit_max_residual_arcsec,
        max_position_residual_arcsec=max_residual,
        rate_difference_arcsec_per_min=rate_difference,
        position_angle_difference_deg=angle_difference,
        identification_status=identification.status,
        identified_as=identified_as,
    )


def run_acceptance(
    fields: list[CanonicalField],
    config: PipelineConfig = EXPERIMENTAL_DEFAULT_CONFIG,
    tolerances: AcceptanceTolerances = AcceptanceTolerances(),
    regression_floor: int = REGRESSION_FLOOR,
    live_skybot: bool = False,
    client: httpx.Client | None = None,
    progress=lambda message: None,
) -> AcceptanceReport:
    """Run the pipeline on every canonical field and judge every target."""
    results: list[TargetAcceptance] = []
    for field in fields:
        progress(f"{field.field_id}: running pipeline")
        observations = fetch_observations(field.product_ids, client)
        pipeline = build_tracklets_from_observations(observations, config, client)
        tracklets = pipeline.build.tracklets
        if live_skybot:
            identification = identify_tracklets(
                tracklets, observations, config.identification(), client=client
            )
        else:
            identification = match_tracklets_to_known_objects(
                tracklets,
                dict(zip(field.product_ids, field.skybot_snapshot)),
                config.identification(),
            )
        by_id = {i.tracklet_id: i for i in identification.identifications}
        results += [
            evaluate_target(
                field.field_id,
                target,
                field.product_ids,
                tracklets,
                by_id,
                config,
                tolerances,
            )
            for target in field.targets
        ]

    passed = sum(result.passed for result in results)
    misidentified = sum(
        result.identification_status is IdentificationStatus.KNOWN
        and result.identified_as != result.designation
        for result in results
    )
    astrometric_fail = sum(
        result.identification and not result.astrometric for result in results
    )
    problems = []
    if misidentified:
        problems.append(f"{misidentified} misidentified")
    if astrometric_fail:
        problems.append(f"{astrometric_fail} identified outside tolerance")
    if passed < regression_floor:
        problems.append(f"{passed} passed < regression floor {regression_floor}")
    return AcceptanceReport(
        generated_at=datetime.now(timezone.utc),
        skybot_mode="live" if live_skybot else "AS-022 snapshot",
        config=config,
        tolerances=tolerances,
        regression_floor=regression_floor,
        targets=results,
        passed_targets=passed,
        misidentified_targets=misidentified,
        identified_but_astrometric_fail=astrometric_fail,
        passed=not problems,
        verdict_reason="; ".join(problems) or (
            f"{passed}/{len(results)} targets pass, no misidentification, "
            "no identified target outside tolerance"
        ),
    )


def render_markdown(report: AcceptanceReport) -> str:
    t = report.tolerances
    lines = [
        "# AS-024 scientific acceptance",
        "",
        f"Generated: {report.generated_at.isoformat()} — SkyBoT: "
        f"{report.skybot_mode}",
        "",
        "Config (experimental defaults): "
        + ", ".join(f"{k}={v}" for k, v in report.config),
        "",
        f"Tolerances: position <= {t.max_position_residual_arcsec}\", "
        f"|rate diff| <= {t.max_rate_difference_arcsec_per_min}\"/min, "
        f"|PA diff| <= {t.max_position_angle_difference_deg} deg; "
        f"regression floor {report.regression_floor} targets.",
        "",
        f"**Verdict: {'PASS' if report.passed else 'FAIL'}** — "
        f"{report.verdict_reason}",
        "",
        "| field | target | V | A | B | C | D | tracklet | max res. (\") "
        "| rate diff | PA diff | identified | result |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    mark = {True: "✓", False: "✗"}
    for r in report.targets:
        lines.append(
            f"| {r.field_id} | {r.designation} {r.name} | {r.v_magnitude:.1f} "
            f"| {mark[r.software]} | {mark[r.geometric]} | {mark[r.astrometric]} "
            f"| {mark[r.identification]} | {r.tracklet_id or '-'} "
            f"| {_fmt(r.max_position_residual_arcsec, 2)} "
            f"| {_fmt(r.rate_difference_arcsec_per_min, 4)} "
            f"| {_fmt(r.position_angle_difference_deg, 2)} "
            f"| {r.identified_as or '-'} "
            f"| {'PASS' if r.passed else 'FAIL: ' + r.reason} |"
        )
    lines.append("")
    return "\n".join(lines)


def _fmt(value: float | None, digits: int) -> str:
    return "-" if value is None or math.isnan(value) else f"{value:.{digits}f}"


def main() -> None:
    parser = argparse.ArgumentParser(description="AS-024 scientific acceptance")
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    parser.add_argument("--live-skybot", action="store_true")
    args = parser.parse_args()

    report = run_acceptance(
        load_canonical_fields(),
        live_skybot=args.live_skybot,
        progress=lambda message: print(message, flush=True),
    )
    args.out_json.write_text(report.model_dump_json() + "\n")
    args.out_md.write_text(render_markdown(report))
    print(f"{'PASS' if report.passed else 'FAIL'}: {report.verdict_reason}")
    raise SystemExit(0 if report.passed else 1)


if __name__ == "__main__":
    main()
