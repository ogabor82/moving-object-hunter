from datetime import datetime

from pydantic import BaseModel, Field

from app.models.source_detection import SourceDetection


class TrackletBuildConfig(BaseModel):
    """Tracklet linking parameters.

    Rate limit and search radius have no defaults: per 02 – Research /
    Evidence they must be calibrated from the Validation Set. The minimum
    of 3 detections comes from 04 – Baby Steps (AS-017).
    """

    max_rate_arcsec_per_min: float = Field(gt=0)
    search_radius_arcsec: float = Field(gt=0)
    min_detections: int = Field(default=3, ge=3)


class TrackletDetection(BaseModel):
    """One detection of a tracklet with its frame time."""

    time: datetime
    detection: SourceDetection


class Tracklet(BaseModel):
    """Time-ordered detections linked as one moving source."""

    tracklet_id: str
    detections: list[TrackletDetection] = Field(min_length=3)


class TrackletBuildDiagnostics(BaseModel):
    """Counters describing one tracklet build run."""

    frame_count: int
    candidate_counts: list[int]
    seed_pairs: int
    linked_before_dedup: int
    duplicates_removed: int
    subsets_removed: int
    ambiguous_extensions: int
    tracklet_count: int
    detections_in_multiple_tracklets: int


class TrackletBuildResult(BaseModel):
    """Tracklets found in a frame sequence plus build diagnostics."""

    config: TrackletBuildConfig
    tracklets: list[Tracklet]
    diagnostics: TrackletBuildDiagnostics
