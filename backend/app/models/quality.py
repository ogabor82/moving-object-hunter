"""Descriptive quality features of one tracklet (AS-031).

Measurements only: no score, rank or threshold is derived from them here.
Each field documents its source, computation, unit and missing semantics;
see also docs/tracklet_quality_features.md.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.models.tracklet import TrackletStatus


class SharpAvailability(StrEnum):
    """How much of the DAOPhot `sharp` shape metric reached the features.

    `sharp` is not part of the provider-independent SourceDetection (it is
    dropped in catalog_service._map_psf_row by design); it is only known
    when the caller supplies it from the raw ZTF PSF catalog.
    """

    UNAVAILABLE = "unavailable"  # no raw catalog values supplied
    PARTIAL = "partial"  # supplied, but missing/non-finite for some detection
    COMPLETE = "complete"  # a finite value for every detection


class TrackletQualityFeatures(BaseModel):
    """Per-tracklet quality features, computed from the tracklet alone."""

    model_config = ConfigDict(allow_inf_nan=False)

    tracklet_id: str
    tracklet_status: TrackletStatus = Field(
        description="Tracklet.status (built / rejected by the fit residual limit)"
    )
    detection_count: int = Field(
        ge=3, description="len(Tracklet.detections); one detection per frame"
    )
    min_snr: float = Field(
        ge=0.0, description="min of SourceDetection.snr (ZTF flux/sigflux), unitless"
    )
    median_snr: float = Field(
        ge=0.0, description="median of SourceDetection.snr, unitless"
    )
    magnitude_range_mag: float = Field(
        ge=0.0,
        description=(
            "max - min of SourceDetection.magnitude (calibrated, no colour "
            "term) [mag]"
        ),
    )
    magnitude_range_sigma: float | None = Field(
        default=None,
        ge=0.0,
        description=(
            "magnitude_range_mag / hypot(magnitude_error of the brightest, of "
            "the faintest detection) [sigma]; null if both errors are 0"
        ),
    )
    edge_detection_count: int = Field(
        ge=0, description="detections with SourceDetection.on_image_edge (flags == -1)"
    )
    masked_detection_count: int = Field(
        ge=0, description="detections with SourceDetection.mask_bits != 0"
    )
    flagged_detection_count: int = Field(
        ge=0, description="detections that are on the edge or masked"
    )
    mask_bits_union: int = Field(
        ge=0, description="bitwise OR of SourceDetection.mask_bits over detections"
    )
    sharp_availability: SharpAvailability
    sharp_values: list[float | None] = Field(
        description=(
            "raw ZTF PSF catalog `sharp` per detection in time order; null "
            "where not supplied or non-finite; empty list when unavailable"
        )
    )
    sharp_min: float | None = Field(
        default=None, description="min of sharp_values; only when complete"
    )
    sharp_max: float | None = Field(
        default=None, description="max of sharp_values; only when complete"
    )
    angular_velocity_arcsec_per_min: float = Field(
        ge=0.0,
        description="Tracklet.angular_velocity_arcsec_per_min (fit) [arcsec/min]",
    )
    position_angle_deg: float = Field(
        ge=0.0, lt=360.0, description="Tracklet.position_angle_deg, east of north [deg]"
    )
    fit_rms_residual_arcsec: float = Field(
        ge=0.0, description="Tracklet.fit_rms_residual_arcsec [arcsec]"
    )
    fit_max_residual_arcsec: float = Field(
        ge=0.0, description="Tracklet.fit_max_residual_arcsec [arcsec]"
    )
