import json

from app.models.matching import StationaryMatchingConfig
from app.services.matching_service import (
    extract_moving_candidates,
    match_stationary_sources,
)
from tests.synthetic_frames import ARCSEC, make_frame


CONFIG = StationaryMatchingConfig(stationary_tolerance_arcsec=1.0)
STAR = (120.0, 10.0)


def test_candidates_are_unmatched_sources_per_frame() -> None:
    frames = [
        make_frame(1, 0, [STAR, (120.005, 10.0)]),
        make_frame(2, 30, [STAR, (120.005 + 30 * ARCSEC, 10.0)]),
        make_frame(3, 60, [STAR]),
    ]

    candidate_frames = extract_moving_candidates(
        match_stationary_sources(frames, CONFIG)
    )

    assert [frame.observation.product_id for frame in candidate_frames] == [
        1,
        2,
        3,
    ]
    assert [
        [candidate.source_id for candidate in frame.candidates]
        for frame in candidate_frames
    ] == [["1-1"], ["2-1"], []]
    assert [frame.candidate_count for frame in candidate_frames] == [1, 1, 0]


def test_candidates_keep_observation_time_and_serialize() -> None:
    frames = [
        make_frame(1, 0, [STAR, (120.005, 10.0)]),
        make_frame(2, 30, [STAR]),
    ]

    [first, second] = extract_moving_candidates(
        match_stationary_sources(frames, CONFIG)
    )
    payload = json.loads(first.model_dump_json())

    assert first.observation.observed_at < second.observation.observed_at
    assert payload["candidate_count"] == 1
    assert payload["candidates"][0]["source_id"] == "1-1"
