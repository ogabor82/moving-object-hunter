"""Frames → stationary matching → candidates → tracklets, in one call."""

from dataclasses import dataclass

import httpx

from app.models.frame_sources import FrameSources
from app.models.matching import CandidateFrame
from app.models.observation import Observation
from app.models.pipeline_config import PipelineConfig
from app.models.tracklet import TrackletBuildResult
from app.services.catalog_service import load_frame_sources
from app.services.matching_service import (
    extract_moving_candidates,
    match_stationary_sources,
)
from app.services.tracklet_service import build_tracklets
from app.services.ztf_service import MIN_SEQUENCE_FRAMES, InsufficientFramesError


@dataclass(frozen=True)
class TrackletPipelineResult:
    """Everything produced from a frame sequence up to tracklets."""

    observations: list[Observation]
    frames: list[FrameSources]
    candidate_frames: list[CandidateFrame]
    build: TrackletBuildResult


def build_tracklets_from_frames(
    frames: list[FrameSources],
    config: PipelineConfig,
) -> TrackletPipelineResult:
    """Run stationary matching, candidate extraction and tracklet building."""
    candidate_frames = extract_moving_candidates(
        match_stationary_sources(frames, config.stationary_matching())
    )
    return TrackletPipelineResult(
        observations=[frame.observation for frame in frames],
        frames=frames,
        candidate_frames=candidate_frames,
        build=build_tracklets(candidate_frames, config.tracklet_build()),
    )


def build_tracklets_from_observations(
    observations: list[Observation],
    config: PipelineConfig,
    client: httpx.Client | None = None,
) -> TrackletPipelineResult:
    """Load the PSF catalogs of time-ordered observations and build tracklets."""
    if len(observations) < MIN_SEQUENCE_FRAMES:
        raise InsufficientFramesError(
            f"{len(observations)} observation(s) given; at least "
            f"{MIN_SEQUENCE_FRAMES} are required."
        )
    return build_tracklets_from_frames(
        load_frame_sources(observations, client), config
    )
