from datetime import timedelta

import pytest

from app.models.identification import IdentificationStatus
from app.models.matching import CandidateFrame
from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG
from app.models.tracklet import TrackletDetection
from app.services import pipeline_service
from app.services.identification_service import match_tracklets_to_known_objects
from app.services.tracklet_service import build_tracklets
from app.validation import acceptance
from app.validation.acceptance import (
    AcceptanceTolerances,
    evaluate_target,
    render_markdown,
    run_acceptance,
)
from app.validation.end_to_end import CanonicalField
from app.validation.models import ValidationTarget
from tests.synthetic_frames import ARCSEC
from tests.test_validation_tooling import (
    PRODUCT_IDS,
    STAR_A,
    TARGET_START,
    ephemeris,
    frames_with,
    mover,
    skybot_fields,
)


TOLERANCES = AcceptanceTolerances()
MINUTES = (0, 30, 60)
# On-sky rate of the synthetic mover (0.5"/min in RA at Dec 10).
TRUE_RATE = 0.5 * 0.98481


def target(
    designation: str = "100",
    rate: float = TRUE_RATE,
    angle: float = 90.0,
    dec_offset_arcsec: float = 0.0,
) -> ValidationTarget:
    return ValidationTarget(
        field_id="F",
        designation=designation,
        name=f"Object {designation}",
        object_class="MB>Middle",
        role="primary",
        v_magnitude=19.0,
        position_error_arcsec=0.1,
        predicted_rate_arcsec_per_min=rate,
        predicted_position_angle_deg=angle,
        predicted_positions=[
            (
                mover(TARGET_START, minute)[0],
                TARGET_START[1] + dec_offset_arcsec * ARCSEC,
            )
            for minute in MINUTES
        ],
    )


def pipeline(positions_at_minute, known: str | None = "100"):
    frames = frames_with(positions_at_minute)
    candidates = [
        CandidateFrame(observation=frame.observation, candidates=frame.detections)
        for frame in frames
    ]
    tracklets = build_tracklets(
        candidates, EXPERIMENTAL_DEFAULT_CONFIG.tracklet_build()
    ).tracklets
    objects = (
        (lambda minute: [ephemeris(known, mover(TARGET_START, minute))])
        if known
        else (lambda minute: [])
    )
    identification = match_tracklets_to_known_objects(
        tracklets,
        dict(zip(PRODUCT_IDS, skybot_fields(objects))),
        EXPERIMENTAL_DEFAULT_CONFIG.identification(),
    )
    return tracklets, {i.tracklet_id: i for i in identification.identifications}


def judge(expected: ValidationTarget, positions_at_minute, known="100"):
    tracklets, identifications = pipeline(positions_at_minute, known)
    return evaluate_target(
        "F",
        expected,
        PRODUCT_IDS,
        tracklets,
        identifications,
        EXPERIMENTAL_DEFAULT_CONFIG,
        TOLERANCES,
    )


def on_track(minute: float) -> list[tuple[float, float]]:
    return [mover(TARGET_START, minute)]


def test_consistent_known_target_passes_all_levels() -> None:
    result = judge(target(), on_track)

    assert result.passed
    assert (result.software, result.geometric, result.astrometric) == (
        True,
        True,
        True,
    )
    assert result.identification
    assert result.failed_level is None
    assert result.max_position_residual_arcsec == pytest.approx(0.0, abs=1e-6)
    assert result.rate_difference_arcsec_per_min == pytest.approx(0.0, abs=1e-3)


def test_missing_tracklet_fails_geometric() -> None:
    result = judge(target(), lambda minute: [] if minute == 30 else on_track(minute))

    assert not result.passed
    assert result.failed_level == "geometric"
    assert result.tracklet_id is None


def test_position_residual_above_tolerance_fails_astrometric() -> None:
    # Detections 1.2" north of the frozen prediction (tolerance 1.0").
    result = judge(target(dec_offset_arcsec=-1.2), on_track)

    assert result.failed_level == "astrometric"
    assert result.max_position_residual_arcsec == pytest.approx(1.2, rel=1e-3)
    assert result.identification  # identification itself still succeeds


def test_rate_disagreement_fails_motion_sanity() -> None:
    result = judge(target(rate=TRUE_RATE + 0.05), on_track)

    assert result.failed_level == "astrometric"
    assert result.rate_difference_arcsec_per_min == pytest.approx(-0.05, abs=1e-3)


def test_direction_disagreement_fails_motion_sanity() -> None:
    result = judge(target(angle=95.0), on_track)

    assert result.failed_level == "astrometric"
    assert result.position_angle_difference_deg == pytest.approx(-5.0, abs=0.05)


def test_position_angle_difference_wraps_around_north() -> None:
    result = judge(target(angle=90.0 + 359.0), on_track)

    assert result.position_angle_difference_deg == pytest.approx(1.0, abs=0.05)


def test_wrong_designation_fails_identification() -> None:
    result = judge(target(), on_track, known="999")

    assert result.failed_level == "identification"
    assert result.identified_as == "999"
    assert result.identification_status is IdentificationStatus.KNOWN


def test_unknown_identification_fails_identification() -> None:
    result = judge(target(), on_track, known=None)

    assert result.failed_level == "identification"
    assert result.identified_as is None


def run_suite(monkeypatch, known: str | None, floor: int = 1):
    frames = frames_with(lambda minute: [STAR_A, mover(TARGET_START, minute)])
    monkeypatch.setattr(
        acceptance,
        "fetch_observations",
        lambda ids, client=None: [frame.observation for frame in frames],
    )
    monkeypatch.setattr(
        pipeline_service, "load_frame_sources", lambda observations, client: frames
    )
    objects = (
        (lambda minute: [ephemeris(known, mover(TARGET_START, minute))])
        if known
        else (lambda minute: [])
    )
    field = CanonicalField(
        field_id="F",
        product_ids=PRODUCT_IDS,
        targets=[target()],
        skybot_snapshot=skybot_fields(objects),
    )
    return run_acceptance([field], regression_floor=floor)


def test_suite_passes_and_is_reproducible(monkeypatch) -> None:
    first = run_suite(monkeypatch, known="100")
    second = run_suite(monkeypatch, known="100")

    assert first.passed
    assert first.skybot_mode == "AS-022 snapshot"
    assert [t.model_dump() for t in first.targets] == [
        t.model_dump() for t in second.targets
    ]
    assert "**Verdict: PASS**" in render_markdown(first)


def test_suite_fails_on_misidentification(monkeypatch) -> None:
    report = run_suite(monkeypatch, known="999")

    assert not report.passed
    assert report.misidentified_targets == 1
    assert "misidentified" in report.verdict_reason


def test_suite_fails_below_regression_floor(monkeypatch) -> None:
    report = run_suite(monkeypatch, known=None, floor=1)

    assert not report.passed
    assert "regression floor" in report.verdict_reason


def test_tolerances_are_explicit_defaults() -> None:
    assert TOLERANCES.max_position_residual_arcsec == 1.0
    assert TOLERANCES.max_rate_difference_arcsec_per_min == 0.02
    assert TOLERANCES.max_position_angle_difference_deg == 2.0
    assert acceptance.REGRESSION_FLOOR == 16


def test_tracklet_detection_times_are_used() -> None:
    # Guards the fixture: detection times follow the frame times.
    tracklets, _ = pipeline(on_track)
    [tracklet] = tracklets
    times = [item.time for item in tracklet.detections]
    assert times[1] - times[0] == timedelta(minutes=30)
    assert isinstance(tracklet.detections[0], TrackletDetection)
