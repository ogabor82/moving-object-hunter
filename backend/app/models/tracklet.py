from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.models.source_detection import SourceDetection


class TrackletBuildConfig(BaseModel):
    """Tracklet linking parameters.

    Rate limit, search radius and residual limit have no defaults: per
    02 – Research / Evidence they must be calibrated from the Validation
    Set. The minimum of 3 detections comes from 04 – Baby Steps (AS-017).
    """

    max_rate_arcsec_per_min: float = Field(gt=0)
    search_radius_arcsec: float = Field(gt=0)
    max_residual_arcsec: float = Field(gt=0)
    min_detections: int = Field(default=3, ge=3)


class TrackletStatus(StrEnum):
    """Tracklet states, named after 05 – Scientific Validation."""

    TRACKLET_BUILT = "tracklet_built"
    REJECTED = "rejected"


class TrackletDetection(BaseModel):
    """One detection of a tracklet with its frame time."""

    time: datetime
    detection: SourceDetection


class Tracklet(BaseModel):
    """Time-ordered detections linked as one moving source, with its fit.

    Motion is a constant-rate linear fit in sky offsets around the first
    detection; residuals are distances of the detections from that fit.
    The status is REJECTED when the maximum residual exceeds the configured
    `max_residual_arcsec`.
    """

    model_config = ConfigDict(allow_inf_nan=False)

    tracklet_id: str
    detections: list[TrackletDetection] = Field(min_length=3)
    angular_velocity_arcsec_per_min: float = Field(ge=0.0)
    position_angle_deg: float = Field(
        ge=0.0,
        lt=360.0,
        description="Direction of motion, east of north [deg]",
    )
    fit_rms_residual_arcsec: float = Field(ge=0.0)
    fit_max_residual_arcsec: float = Field(ge=0.0)
    status: TrackletStatus
    status_reason: str | None = None


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
    rejected_tracklet_count: int
    detections_in_multiple_tracklets: int


class TrackletBuildResult(BaseModel):
    """Tracklets found in a frame sequence plus build diagnostics."""

    config: TrackletBuildConfig
    tracklets: list[Tracklet]
    diagnostics: TrackletBuildDiagnostics
