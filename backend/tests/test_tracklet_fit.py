import json
from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.models.tracklet import (
    Tracklet,
    TrackletBuildConfig,
    TrackletDetection,
    TrackletStatus,
)
from app.services.tracklet_service import build_tracklets, fit_tracklet_motion
from tests.synthetic_frames import ARCSEC, START_TIME, make_detection
from tests.test_tracklet_builder import candidate_frames, mover


def tracklet_detections(
    minutes: list[float],
    positions: list[tuple[float, float]],
) -> list[TrackletDetection]:
    return [
        TrackletDetection(
            time=START_TIME + timedelta(minutes=minute),
            detection=make_detection(index + 1, 0, ra, dec),
        )
        for index, (minute, (ra, dec)) in enumerate(zip(minutes, positions))
    ]


def test_fit_recovers_rate_and_direction_of_linear_motion() -> None:
    minutes = [0, 30, 45, 80]
    positions = [mover((120.0, 10.0), 0.0, 1.2, minute) for minute in minutes]

    fit = fit_tracklet_motion(tracklet_detections(minutes, positions))

    assert fit.angular_velocity_arcsec_per_min == pytest.approx(1.2, rel=1e-4)
    assert fit.position_angle_deg == pytest.approx(0.0, abs=1e-3)
    assert fit.rms_residual_arcsec == pytest.approx(0.0, abs=1e-3)
    assert fit.max_residual_arcsec == pytest.approx(0.0, abs=1e-3)


@pytest.mark.parametrize(
    ("rate_ra", "rate_dec", "expected_angle"),
    [(1.0, 0.0, 90.0), (0.0, -1.0, 180.0), (-1.0, 0.0, 270.0), (0.5, 0.5, 45.0)],
)
def test_fit_position_angle_is_east_of_north(
    rate_ra: float,
    rate_dec: float,
    expected_angle: float,
) -> None:
    minutes = [0, 30, 60]
    positions = [
        mover((120.0, 0.0), rate_ra, rate_dec, minute) for minute in minutes
    ]

    fit = fit_tracklet_motion(tracklet_detections(minutes, positions))

    assert fit.position_angle_deg == pytest.approx(expected_angle, abs=1e-2)


def test_fit_rate_accounts_for_cos_declination() -> None:
    minutes = [0, 30, 60]
    # 2 arcsec/min in RA coordinate at Dec 60 is 1 arcsec/min on sky.
    positions = [mover((120.0, 60.0), 2.0, 0.0, minute) for minute in minutes]

    fit = fit_tracklet_motion(tracklet_detections(minutes, positions))

    assert fit.angular_velocity_arcsec_per_min == pytest.approx(1.0, rel=1e-3)


def test_fit_across_ra_wrap_around() -> None:
    minutes = [0, 30, 60]
    positions = [
        (mover((359.995, 0.0), 0.5, 0.0, minute)[0] % 360, 0.0)
        for minute in minutes
    ]

    fit = fit_tracklet_motion(tracklet_detections(minutes, positions))

    assert fit.angular_velocity_arcsec_per_min == pytest.approx(0.5, rel=1e-4)
    assert fit.position_angle_deg == pytest.approx(90.0, abs=1e-2)
    assert fit.max_residual_arcsec == pytest.approx(0.0, abs=1e-3)


def test_fit_residual_exposes_a_deviating_detection() -> None:
    minutes = [0, 30, 60]
    positions = [mover((120.0, 10.0), 1.0, 0.0, minute) for minute in minutes]
    positions[1] = (positions[1][0], positions[1][1] + 3 * ARCSEC)

    fit = fit_tracklet_motion(tracklet_detections(minutes, positions))

    # Straight-line fit through (0, 3, 0) arcsec in north at equal spacing:
    # residuals are (-1, 2, -1) arcsec.
    assert fit.max_residual_arcsec == pytest.approx(2.0, rel=1e-3)
    assert fit.rms_residual_arcsec == pytest.approx(2**0.5, rel=1e-3)


def test_fit_requires_three_detections() -> None:
    minutes = [0, 30]
    positions = [mover((120.0, 10.0), 1.0, 0.0, minute) for minute in minutes]

    with pytest.raises(ValueError, match="three"):
        fit_tracklet_motion(tracklet_detections(minutes, positions))


def build(positions: list[list[tuple[float, float]]], max_residual: float):
    config = TrackletBuildConfig(
        max_rate_arcsec_per_min=5.0,
        search_radius_arcsec=3.0,
        max_residual_arcsec=max_residual,
    )
    return build_tracklets(candidate_frames([0, 30, 60], positions), config)


def test_builder_marks_good_fit_as_built() -> None:
    positions = [[mover((120.0, 10.0), 0.8, 0.3, minute)] for minute in [0, 30, 60]]

    result = build(positions, max_residual=0.5)

    [tracklet] = result.tracklets
    assert tracklet.status is TrackletStatus.TRACKLET_BUILT
    assert tracklet.status_reason is None
    assert tracklet.angular_velocity_arcsec_per_min == pytest.approx(
        (0.8**2 * 0.9848**2 + 0.3**2) ** 0.5, rel=1e-3
    )
    assert result.diagnostics.rejected_tracklet_count == 0


def test_builder_marks_poor_fit_as_rejected_but_keeps_it() -> None:
    positions = [[mover((120.0, 10.0), 1.0, 0.0, minute)] for minute in [0, 30, 60]]
    middle = positions[1][0]
    positions[1] = [(middle[0], middle[1] + 2.4 * ARCSEC)]

    result = build(positions, max_residual=0.5)

    [tracklet] = result.tracklets
    assert tracklet.status is TrackletStatus.REJECTED
    assert "exceeds 0.5 arcsec" in tracklet.status_reason
    assert tracklet.fit_max_residual_arcsec == pytest.approx(1.6, rel=1e-3)
    assert result.diagnostics.rejected_tracklet_count == 1


def test_tracklet_is_json_serializable() -> None:
    positions = [[mover((120.0, 10.0), 0.8, 0.3, minute)] for minute in [0, 30, 60]]
    [tracklet] = build(positions, max_residual=0.5).tracklets

    payload = json.loads(tracklet.model_dump_json())

    assert payload["status"] == "tracklet_built"
    assert payload["status_reason"] is None
    assert {
        "tracklet_id",
        "detections",
        "angular_velocity_arcsec_per_min",
        "position_angle_deg",
        "fit_rms_residual_arcsec",
        "fit_max_residual_arcsec",
    } <= set(payload)
    assert Tracklet.model_validate(payload) == tracklet


def test_tracklet_requires_three_detections() -> None:
    minutes = [0, 30]
    positions = [mover((120.0, 10.0), 1.0, 0.0, minute) for minute in minutes]

    with pytest.raises(ValidationError):
        Tracklet(
            tracklet_id="trk-0001",
            detections=tracklet_detections(minutes, positions),
            angular_velocity_arcsec_per_min=1.0,
            position_angle_deg=90.0,
            fit_rms_residual_arcsec=0.0,
            fit_max_residual_arcsec=0.0,
            status=TrackletStatus.TRACKLET_BUILT,
        )
