from pydantic import BaseModel, Field

from app.models.identification import IdentificationStatus
from app.models.known_object import KnownObjectField
from app.models.observation import Observation
from app.models.tracklet import TrackletStatus


class ValidationField(BaseModel):
    """A frozen ZTF quadrant sequence used as a validation field."""

    field_id: str
    description: str
    product_ids: list[int] = Field(min_length=3)
    selection_note: str
    control_designations: list[str] = Field(
        default_factory=list,
        description=(
            "Known objects included by human choice (role 'control'); kept "
            "out of the rule-based primary/marginal statistics"
        ),
    )


class FrameMetadata(BaseModel):
    """IRSA per-frame metadata needed for target selection."""

    product_id: int
    center_ra: float
    center_dec: float
    corners: list[tuple[float, float]] = Field(min_length=4, max_length=4)
    maglimit: float
    seeing_arcsec: float
    airmass: float


class TargetSelectionRule(BaseModel):
    """Pre-registered rule deciding which known objects are targets.

    Uses only SkyBoT predictions and IRSA frame metadata, never pipeline
    output, to avoid circular validation.
    """

    primary_margin_mag: float = Field(
        default=0.5,
        description="Primary if V <= min frame maglimit - margin",
    )
    marginal_margin_mag: float = Field(
        default=0.5,
        description="Marginal if V <= min frame maglimit + margin",
    )
    max_position_error_arcsec: float = Field(default=1.0, gt=0)


class ValidationTarget(BaseModel):
    """A known object expected in every frame of a validation field."""

    field_id: str
    designation: str
    name: str
    object_class: str
    role: str = Field(description="primary | marginal | control")
    v_magnitude: float
    position_error_arcsec: float
    predicted_rate_arcsec_per_min: float
    predicted_position_angle_deg: float
    predicted_positions: list[tuple[float, float]]


class PipelineConfig(BaseModel):
    """All tunable pipeline thresholds of one validation run."""

    stationary_tolerance_arcsec: float = Field(gt=0)
    max_rate_arcsec_per_min: float = Field(gt=0)
    search_radius_arcsec: float = Field(gt=0)
    max_residual_arcsec: float = Field(gt=0)
    match_radius_arcsec: float = Field(gt=0)


class TargetOutcome(BaseModel):
    """What happened to one validation target in one run."""

    designation: str
    role: str
    nearest_detection_arcsec: list[float | None]
    detected_frames: int
    candidate_frames: int
    recovered: bool
    identification_status: IdentificationStatus | None
    tracklet_id: str | None
    tracklet_status: TrackletStatus | None
    max_residual_arcsec: float | None


class TrackletFeatures(BaseModel):
    """Quality features of one tracklet for filter/scoring research."""

    tracklet_id: str
    tracklet_status: TrackletStatus
    identification_status: IdentificationStatus
    known_designation: str | None
    is_validation_target: bool
    min_snr: float
    median_snr: float
    magnitude_spread: float
    flagged_detections: int
    sharp_values: list[float | None]
    rate_arcsec_per_min: float
    position_angle_deg: float
    fit_rms_residual_arcsec: float
    fit_max_residual_arcsec: float
    predicted_rate_arcsec_per_min: float | None
    predicted_position_angle_deg: float | None
    rate_difference_arcsec_per_min: float | None
    position_angle_difference_deg: float | None


class FieldRunResult(BaseModel):
    """Pipeline outcome for one field and one configuration."""

    field_id: str
    config: PipelineConfig
    candidate_counts: list[int]
    tracklet_count: int
    built_count: int
    rejected_count: int
    known_count: int
    unknown_count: int
    ambiguous_count: int
    unknown_built_count: int
    primary_targets: int
    primary_recovered: int
    marginal_targets: int
    marginal_recovered: int
    control_targets: int
    control_recovered: int
    targets: list[TargetOutcome]
    tracklets: list[TrackletFeatures]


class FieldSnapshot(BaseModel):
    """Everything fetched live for one field, kept for reproducibility."""

    field: ValidationField
    observations: list[Observation]
    frame_metadata: list[FrameMetadata]
    skybot_fields: list[KnownObjectField]
    source_counts: list[int]
    targets: list[ValidationTarget]
