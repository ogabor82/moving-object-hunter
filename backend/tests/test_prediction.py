import json
from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.models.motion import PredictedPosition, PredictionSearchConfig
from app.services.astrometry import angular_distance_arcsec
from app.services.motion_service import find_detections_near, predict_position
from tests.synthetic_frames import ARCSEC, START_TIME, make_detection


def predict(
    first: tuple[float, float],
    second: tuple[float, float],
    second_minutes: float,
    target_minutes: float,
) -> PredictedPosition:
    return predict_position(
        make_detection(1, 0, *first),
        START_TIME,
        make_detection(2, 0, *second),
        START_TIME + timedelta(minutes=second_minutes),
        START_TIME + timedelta(minutes=target_minutes),
    )


def test_linear_extrapolation_along_declination() -> None:
    prediction = predict((120.0, 10.0), (120.0, 10.0 + 30 * ARCSEC), 30, 60)

    assert prediction.time == START_TIME + timedelta(minutes=60)
    assert prediction.ra == pytest.approx(120.0, abs=1e-9)
    assert prediction.dec == pytest.approx(10.0 + 60 * ARCSEC, abs=1e-9)


def test_extrapolation_uses_time_ratio_not_frame_index() -> None:
    # Unequal spacing: 30 min between the first two, 10 min to the third.
    prediction = predict((120.0, 10.0), (120.0, 10.0 + 30 * ARCSEC), 30, 40)

    assert prediction.dec == pytest.approx(10.0 + 40 * ARCSEC, abs=1e-9)


def test_diagonal_motion_keeps_rate_and_direction() -> None:
    first = (200.0, -30.0)
    second = (200.0 + 20 * ARCSEC, -30.0 + 15 * ARCSEC)

    prediction = predict(first, second, 20, 40)

    step = angular_distance_arcsec(*first, *second)
    assert angular_distance_arcsec(
        *second, prediction.ra, prediction.dec
    ) == pytest.approx(step, rel=1e-4)
    assert angular_distance_arcsec(
        *first, prediction.ra, prediction.dec
    ) == pytest.approx(2 * step, rel=1e-4)


def test_extrapolation_across_ra_wrap_around() -> None:
    prediction = predict((359.9998, 0.0), (359.9999, 0.0), 10, 30)

    assert prediction.ra == pytest.approx(0.0001, abs=1e-7)
    assert 0.0 <= prediction.ra < 360.0


def test_find_detections_near_uses_configured_radius() -> None:
    prediction = PredictedPosition(time=START_TIME, ra=120.0, dec=10.0)
    detections = [
        make_detection(3, 0, 120.0, 10.0 + 1.5 * ARCSEC),
        make_detection(3, 1, 120.0, 10.0 + 0.5 * ARCSEC),
        make_detection(3, 2, 120.0, 10.0 + 5.0 * ARCSEC),
    ]

    narrow = find_detections_near(
        prediction, detections, PredictionSearchConfig(search_radius_arcsec=1.0)
    )
    wide = find_detections_near(
        prediction, detections, PredictionSearchConfig(search_radius_arcsec=2.0)
    )

    assert [match.detection.source_id for match in narrow] == ["3-1"]
    assert [match.detection.source_id for match in wide] == ["3-1", "3-0"]
    assert wide[0].distance_arcsec == pytest.approx(0.5, rel=1e-6)


def test_find_detections_near_handles_no_detections() -> None:
    prediction = PredictedPosition(time=START_TIME, ra=120.0, dec=10.0)

    assert (
        find_detections_near(
            prediction, [], PredictionSearchConfig(search_radius_arcsec=1.0)
        )
        == []
    )


def test_prediction_is_json_serializable() -> None:
    prediction = predict((120.0, 10.0), (120.0, 10.0 + 30 * ARCSEC), 30, 60)

    payload = json.loads(prediction.model_dump_json())

    assert set(payload) == {"time", "ra", "dec"}


@pytest.mark.parametrize("radius", [0.0, -1.0])
def test_search_config_rejects_non_positive_radius(radius: float) -> None:
    with pytest.raises(ValidationError):
        PredictionSearchConfig(search_radius_arcsec=radius)
