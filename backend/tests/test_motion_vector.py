import json
from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.models.motion import MotionVector
from app.services.motion_service import compute_motion_vector
from tests.synthetic_frames import ARCSEC, START_TIME, make_detection


def motion(
    start: tuple[float, float],
    end: tuple[float, float],
    minutes: float,
) -> MotionVector:
    return compute_motion_vector(
        make_detection(1, 0, *start),
        START_TIME,
        make_detection(2, 0, *end),
        START_TIME + timedelta(minutes=minutes),
    )


def test_northward_motion() -> None:
    vector = motion((120.0, 10.0), (120.0, 10.0 + 30 * ARCSEC), 30)

    assert vector.time_delta_minutes == pytest.approx(30.0)
    assert vector.separation_arcsec == pytest.approx(30.0, rel=1e-6)
    assert vector.rate_arcsec_per_min == pytest.approx(1.0, rel=1e-6)
    assert vector.position_angle_deg == pytest.approx(0.0, abs=1e-6)


@pytest.mark.parametrize(
    ("end", "expected_angle"),
    [
        ((120.0 + 20 * ARCSEC, 10.0), 90.0),
        ((120.0, 10.0 - 20 * ARCSEC), 180.0),
        ((120.0 - 20 * ARCSEC, 10.0), 270.0),
    ],
)
def test_position_angle_is_east_of_north(
    end: tuple[float, float],
    expected_angle: float,
) -> None:
    vector = motion((120.0, 10.0), end, 20)

    assert vector.position_angle_deg == pytest.approx(expected_angle, abs=1e-3)


def test_eastward_rate_accounts_for_cos_declination() -> None:
    vector = motion((120.0, 60.0), (120.0 + 60 * ARCSEC, 60.0), 30)

    assert vector.separation_arcsec == pytest.approx(30.0, rel=1e-4)
    assert vector.rate_arcsec_per_min == pytest.approx(1.0, rel=1e-4)


def test_motion_across_ra_wrap_around() -> None:
    vector = motion((359.9999, 0.0), (0.0001, 0.0), 10)

    assert vector.separation_arcsec == pytest.approx(0.72, rel=1e-6)
    assert vector.position_angle_deg == pytest.approx(90.0, abs=1e-3)


def test_explicit_time_delta_uses_seconds() -> None:
    vector = motion((120.0, 10.0), (120.0, 10.0 + 10 * ARCSEC), 0.5)

    assert vector.time_delta_minutes == pytest.approx(0.5)
    assert vector.rate_arcsec_per_min == pytest.approx(20.0, rel=1e-6)


@pytest.mark.parametrize("minutes", [0, -5])
def test_rejects_non_increasing_time(minutes: float) -> None:
    with pytest.raises(ValueError, match="later"):
        motion((120.0, 10.0), (120.0, 10.001), minutes)


def test_motion_vector_is_json_serializable() -> None:
    vector = motion((120.0, 10.0), (120.0, 10.0 + 30 * ARCSEC), 30)

    payload = json.loads(vector.model_dump_json())

    assert set(payload) == {
        "time_delta_minutes",
        "separation_arcsec",
        "rate_arcsec_per_min",
        "position_angle_deg",
    }


def test_motion_vector_rejects_zero_time_delta() -> None:
    with pytest.raises(ValidationError):
        MotionVector(
            time_delta_minutes=0.0,
            separation_arcsec=1.0,
            rate_arcsec_per_min=1.0,
            position_angle_deg=0.0,
        )
