import json

import pytest
from pydantic import ValidationError

from app.models.matching import StationaryMatchingConfig
from app.services.matching_service import match_stationary_sources
from tests.synthetic_frames import ARCSEC, make_frame


CONFIG = StationaryMatchingConfig(stationary_tolerance_arcsec=1.0)
STAR_A = (120.0, 10.0)
STAR_B = (120.01, 10.02)


def source_ids(detections: list) -> list[str]:
    return [detection.source_id for detection in detections]


def test_stars_are_stationary_and_moving_object_is_unmatched() -> None:
    frames = [
        make_frame(1, 0, [STAR_A, STAR_B, (120.005, 10.0)]),
        make_frame(2, 30, [STAR_A, STAR_B, (120.005 + 30 * ARCSEC, 10.0)]),
        make_frame(3, 60, [STAR_A, STAR_B, (120.005 + 60 * ARCSEC, 10.0)]),
    ]

    result = match_stationary_sources(frames, CONFIG)

    for frame_result, product_id in zip(result.frames, (1, 2, 3)):
        assert source_ids(frame_result.stationary) == [
            f"{product_id}-0",
            f"{product_id}-1",
        ]
        assert source_ids(frame_result.unmatched) == [f"{product_id}-2"]


def test_tolerance_comes_from_config() -> None:
    frames = [
        make_frame(1, 0, [STAR_A]),
        make_frame(2, 30, [(STAR_A[0], STAR_A[1] + 1.5 * ARCSEC)]),
    ]

    tight = match_stationary_sources(
        frames, StationaryMatchingConfig(stationary_tolerance_arcsec=1.0)
    )
    loose = match_stationary_sources(
        frames, StationaryMatchingConfig(stationary_tolerance_arcsec=2.0)
    )

    assert [len(frame.unmatched) for frame in tight.frames] == [1, 1]
    assert [len(frame.stationary) for frame in loose.frames] == [1, 1]


def test_match_in_any_other_frame_is_enough() -> None:
    # A source missing from one frame (e.g. below threshold) still matches.
    frames = [
        make_frame(1, 0, [STAR_A, STAR_B]),
        make_frame(2, 30, [STAR_A]),
        make_frame(3, 60, [STAR_A, STAR_B]),
    ]

    result = match_stationary_sources(frames, CONFIG)

    assert [len(frame.unmatched) for frame in result.frames] == [0, 0, 0]


def test_source_seen_in_only_one_frame_is_unmatched() -> None:
    frames = [
        make_frame(1, 0, [STAR_A, STAR_B]),
        make_frame(2, 30, [STAR_A]),
    ]

    result = match_stationary_sources(frames, CONFIG)

    assert source_ids(result.frames[0].unmatched) == ["1-1"]
    assert result.frames[1].unmatched == []


def test_empty_frame_is_handled() -> None:
    frames = [make_frame(1, 0, [STAR_A]), make_frame(2, 30, [])]

    result = match_stationary_sources(frames, CONFIG)

    assert source_ids(result.frames[0].unmatched) == ["1-0"]
    assert result.frames[1].stationary == []
    assert result.frames[1].unmatched == []


def test_matching_across_ra_wrap_around() -> None:
    frames = [
        make_frame(1, 0, [(359.99999, 0.0)]),
        make_frame(2, 30, [(0.00001, 0.0)]),
    ]

    result = match_stationary_sources(frames, CONFIG)

    assert [len(frame.stationary) for frame in result.frames] == [1, 1]


def test_result_is_json_serializable_and_keeps_config() -> None:
    frames = [make_frame(1, 0, [STAR_A]), make_frame(2, 30, [STAR_A])]

    payload = json.loads(match_stationary_sources(frames, CONFIG).model_dump_json())

    assert payload["config"] == {"stationary_tolerance_arcsec": 1.0}
    assert len(payload["frames"]) == 2


def test_requires_at_least_two_frames() -> None:
    with pytest.raises(ValueError, match="two frames"):
        match_stationary_sources([make_frame(1, 0, [STAR_A])], CONFIG)


@pytest.mark.parametrize("tolerance", [0.0, -1.0])
def test_config_rejects_non_positive_tolerance(tolerance: float) -> None:
    with pytest.raises(ValidationError):
        StationaryMatchingConfig(stationary_tolerance_arcsec=tolerance)
