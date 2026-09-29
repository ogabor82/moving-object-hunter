import json
from collections.abc import Sequence

import numpy
import pytest
from pydantic import ValidationError

from app.models.matching import CandidateFrame
from app.models.tracklet import TrackletBuildConfig
from app.services.tracklet_service import build_tracklets
from tests.synthetic_frames import ARCSEC, make_frame


CONFIG = TrackletBuildConfig(max_rate_arcsec_per_min=5.0, search_radius_arcsec=2.0)


def candidate_frames(
    minutes: Sequence[float],
    positions_per_frame: Sequence[Sequence[tuple[float, float]]],
) -> list[CandidateFrame]:
    frames = []
    for index, (minute, positions) in enumerate(zip(minutes, positions_per_frame)):
        frame = make_frame(index + 1, minute, positions)
        frames.append(
            CandidateFrame(observation=frame.observation, candidates=frame.detections)
        )
    return frames


def mover(
    start: tuple[float, float],
    rate_ra_arcsec_per_min: float,
    rate_dec_arcsec_per_min: float,
    minute: float,
) -> tuple[float, float]:
    return (
        start[0] + rate_ra_arcsec_per_min * minute * ARCSEC,
        start[1] + rate_dec_arcsec_per_min * minute * ARCSEC,
    )


def tracklet_source_ids(result) -> list[list[str]]:
    return [
        [item.detection.source_id for item in tracklet.detections]
        for tracklet in result.tracklets
    ]


def test_links_linear_mover_across_three_frames() -> None:
    minutes = [0, 30, 60]
    frames = candidate_frames(
        minutes, [[mover((120.0, 10.0), 0.8, 0.3, minute)] for minute in minutes]
    )

    result = build_tracklets(frames, CONFIG)

    assert tracklet_source_ids(result) == [["1-0", "2-0", "3-0"]]
    tracklet = result.tracklets[0]
    assert tracklet.tracklet_id == "trk-0001"
    assert [item.time for item in tracklet.detections] == [
        frame.observation.observed_at for frame in frames
    ]
    diagnostics = result.diagnostics
    assert diagnostics.frame_count == 3
    assert diagnostics.candidate_counts == [1, 1, 1]
    assert diagnostics.seed_pairs == 3
    assert diagnostics.linked_before_dedup == 3
    assert diagnostics.duplicates_removed == 2
    assert diagnostics.tracklet_count == 1


def test_links_mover_with_unequal_spacing_and_diagonal_motion() -> None:
    minutes = [0, 64, 103]
    frames = candidate_frames(
        minutes, [[mover((255.5, 12.3), -0.4, 0.25, minute)] for minute in minutes]
    )

    result = build_tracklets(frames, CONFIG)

    assert tracklet_source_ids(result) == [["1-0", "2-0", "3-0"]]


def test_links_mover_across_ra_wrap_around() -> None:
    minutes = [0, 30, 60]
    frames = candidate_frames(
        minutes,
        [
            [(mover((359.995, 0.0), 0.5, 0.0, minute)[0] % 360, 0.0)]
            for minute in minutes
        ],
    )

    result = build_tracklets(frames, CONFIG)

    assert len(result.tracklets) == 1


def test_four_frames_give_one_maximal_tracklet() -> None:
    minutes = [0, 20, 40, 60]
    frames = candidate_frames(
        minutes, [[mover((120.0, 10.0), 1.0, 0.0, minute)] for minute in minutes]
    )

    result = build_tracklets(frames, CONFIG)

    assert tracklet_source_ids(result) == [["1-0", "2-0", "3-0", "4-0"]]
    assert result.diagnostics.subsets_removed == 0
    assert result.diagnostics.duplicates_removed == 5


def test_missing_detection_in_one_frame_still_links_three() -> None:
    minutes = [0, 20, 40, 60]
    positions = [[mover((120.0, 10.0), 1.0, 0.0, minute)] for minute in minutes]
    positions[2] = []
    frames = candidate_frames(minutes, positions)

    result = build_tracklets(frames, CONFIG)

    assert tracklet_source_ids(result) == [["1-0", "2-0", "4-0"]]


def test_min_detections_is_configurable() -> None:
    minutes = [0, 20, 40, 60]
    positions = [[mover((120.0, 10.0), 1.0, 0.0, minute)] for minute in minutes]
    positions[2] = []
    frames = candidate_frames(minutes, positions)
    config = CONFIG.model_copy(update={"min_detections": 4})

    assert build_tracklets(frames, config).tracklets == []


def test_rejects_motion_faster_than_max_rate() -> None:
    minutes = [0, 30, 60]
    frames = candidate_frames(
        minutes, [[mover((120.0, 10.0), 6.0, 0.0, minute)] for minute in minutes]
    )

    result = build_tracklets(frames, CONFIG)

    assert result.tracklets == []
    assert result.diagnostics.seed_pairs == 0


def test_rejects_inconsistent_third_point() -> None:
    minutes = [0, 30, 60]
    positions = [[mover((120.0, 10.0), 1.0, 0.0, minute)] for minute in minutes]
    positions[2] = [(positions[2][0][0], positions[2][0][1] + 5 * ARCSEC)]
    frames = candidate_frames(minutes, positions)

    result = build_tracklets(frames, CONFIG)

    assert result.tracklets == []
    assert result.diagnostics.seed_pairs == 3


def test_search_radius_comes_from_config() -> None:
    minutes = [0, 30, 60]
    positions = [[mover((120.0, 10.0), 1.0, 0.0, minute)] for minute in minutes]
    # 2.5" off: every seed pair predicts the remaining point >= 1.25" away.
    positions[2] = [(positions[2][0][0], positions[2][0][1] + 2.5 * ARCSEC)]
    frames = candidate_frames(minutes, positions)

    tight = build_tracklets(
        frames, CONFIG.model_copy(update={"search_radius_arcsec": 1.0})
    )
    loose = build_tracklets(
        frames, CONFIG.model_copy(update={"search_radius_arcsec": 3.0})
    )

    assert tight.tracklets == []
    assert len(loose.tracklets) == 1


def test_two_movers_among_random_noise() -> None:
    rng = numpy.random.default_rng(7)
    minutes = [0, 30, 60]
    positions = []
    for minute in minutes:
        noise = list(
            zip(rng.uniform(120.0, 120.1, 40), rng.uniform(10.0, 10.1, 40))
        )
        positions.append(
            [
                mover((120.03, 10.03), 0.7, 0.2, minute),
                mover((120.07, 10.06), -0.3, -0.9, minute),
                *noise,
            ]
        )
    frames = candidate_frames(minutes, positions)

    result = build_tracklets(frames, CONFIG)

    linked = tracklet_source_ids(result)
    assert ["1-0", "2-0", "3-0"] in linked
    assert ["1-1", "2-1", "3-1"] in linked


def test_random_noise_can_form_chance_alignments() -> None:
    # Documents a known limitation: 3-point linking of dense unmatched
    # sources yields chance tracklets that later fit/identification steps
    # must reject.
    rng = numpy.random.default_rng(7)
    minutes = [0, 30, 60]
    positions = [
        list(zip(rng.uniform(120.0, 120.1, 40), rng.uniform(10.0, 10.1, 40)))
        for _ in minutes
    ]

    result = build_tracklets(candidate_frames(minutes, positions), CONFIG)

    assert result.diagnostics.seed_pairs > 0
    assert len(result.tracklets) > 0
    assert result.diagnostics.tracklet_count == len(result.tracklets)


def test_ambiguous_extension_is_counted_and_alternatives_are_reported() -> None:
    minutes = [0, 30, 60]
    positions = [[mover((120.0, 10.0), 1.0, 0.0, minute)] for minute in minutes]
    exact = positions[2][0]
    positions[2] = [(exact[0], exact[1] + 1.5 * ARCSEC), exact]
    frames = candidate_frames(minutes, positions)

    result = build_tracklets(frames, CONFIG)

    # Seeding from frames 1-2 links the exact point (nearest); seeding from
    # frames 1-3 with the offset point also predicts frame 2 within radius.
    assert sorted(tracklet_source_ids(result)) == [
        ["1-0", "2-0", "3-0"],
        ["1-0", "2-0", "3-1"],
    ]
    assert result.diagnostics.ambiguous_extensions >= 1
    assert result.diagnostics.detections_in_multiple_tracklets == 2


def test_two_frames_cannot_form_a_tracklet() -> None:
    frames = candidate_frames([0, 30], [[(120.0, 10.0)], [(120.0, 10.01)]])

    assert build_tracklets(frames, CONFIG).tracklets == []


def test_frames_must_be_time_ordered() -> None:
    frames = candidate_frames([30, 0, 60], [[], [], []])

    with pytest.raises(ValueError, match="time order"):
        build_tracklets(frames, CONFIG)


def test_result_is_json_serializable() -> None:
    minutes = [0, 30, 60]
    frames = candidate_frames(
        minutes, [[mover((120.0, 10.0), 0.8, 0.3, minute)] for minute in minutes]
    )

    payload = json.loads(build_tracklets(frames, CONFIG).model_dump_json())

    assert payload["config"]["min_detections"] == 3
    assert payload["diagnostics"]["tracklet_count"] == 1
    assert len(payload["tracklets"][0]["detections"]) == 3


@pytest.mark.parametrize(
    "fields",
    [
        {"max_rate_arcsec_per_min": 0.0, "search_radius_arcsec": 1.0},
        {"max_rate_arcsec_per_min": 1.0, "search_radius_arcsec": 0.0},
        {
            "max_rate_arcsec_per_min": 1.0,
            "search_radius_arcsec": 1.0,
            "min_detections": 2,
        },
    ],
)
def test_config_validation(fields: dict) -> None:
    with pytest.raises(ValidationError):
        TrackletBuildConfig(**fields)
