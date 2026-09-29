from collections.abc import Sequence
from itertools import combinations

import numpy

from app.models.frame_sources import FrameSources
from app.models.matching import (
    FrameMatchResult,
    StationaryMatchingConfig,
    StationaryMatchResult,
)
from app.services.astrometry import find_pairs_within


def match_stationary_sources(
    frames: Sequence[FrameSources],
    config: StationaryMatchingConfig,
) -> StationaryMatchResult:
    """Split each frame's detections into stationary and unmatched sources.

    A detection is stationary when at least one detection in any other
    frame lies within `stationary_tolerance_arcsec`. Everything else is
    unmatched and remains a moving-source candidate input.
    """
    if len(frames) < 2:
        raise ValueError("Stationary matching needs at least two frames.")

    positions = [
        (
            [detection.ra for detection in frame.detections],
            [detection.dec for detection in frame.detections],
        )
        for frame in frames
    ]
    matched = [numpy.zeros(len(frame.detections), dtype=bool) for frame in frames]

    for first, second in combinations(range(len(frames)), 2):
        first_indices, second_indices, _ = find_pairs_within(
            *positions[first],
            *positions[second],
            config.stationary_tolerance_arcsec,
        )
        matched[first][first_indices] = True
        matched[second][second_indices] = True

    return StationaryMatchResult(
        config=config,
        frames=[
            FrameMatchResult(
                observation=frame.observation,
                stationary=[
                    detection
                    for detection, is_matched in zip(frame.detections, flags)
                    if is_matched
                ],
                unmatched=[
                    detection
                    for detection, is_matched in zip(frame.detections, flags)
                    if not is_matched
                ],
            )
            for frame, flags in zip(frames, matched)
        ],
    )
