from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.models.known_object import KnownObjectField
from app.models.tracklet import TrackletStatus


class IdentificationConfig(BaseModel):
    """Known-object matching parameters.

    No default radius: per 02 – Research / Evidence it must be calibrated
    from the Validation Set.
    """

    match_radius_arcsec: float = Field(gt=0)


class IdentificationStatus(StrEnum):
    """Identification outcome (04 – Baby Steps AS-021, 05 – Scientific
    Validation: Known object / Unidentified candidate / Ambiguous).

    UNKNOWN means no known object matched; it is not a discovery.
    """

    KNOWN = "known"
    UNKNOWN = "unknown"
    AMBIGUOUS = "ambiguous"


class DetectionResidual(BaseModel):
    """Observed vs predicted position of one tracklet detection."""

    model_config = ConfigDict(allow_inf_nan=False)

    observation_product_id: int
    epoch_jd_utc: float
    observed_ra: float
    observed_dec: float
    predicted_ra: float
    predicted_dec: float
    residual_arcsec: float = Field(ge=0.0)


class KnownObjectMatch(BaseModel):
    """A known object consistent with every detection of a tracklet."""

    model_config = ConfigDict(allow_inf_nan=False)

    designation: str
    name: str
    object_class: str
    v_magnitude: float | None
    position_error_arcsec: float = Field(ge=0.0)
    residuals: list[DetectionResidual]
    rms_residual_arcsec: float = Field(ge=0.0)
    max_residual_arcsec: float = Field(ge=0.0)


class TrackletIdentification(BaseModel):
    """Identification of one tracklet against known objects."""

    tracklet_id: str
    tracklet_status: TrackletStatus
    status: IdentificationStatus
    status_reason: str
    best_match: KnownObjectMatch | None
    candidate_matches: list[KnownObjectMatch]


class IdentificationDiagnostics(BaseModel):
    """Counters describing one identification run."""

    tracklet_count: int
    known_count: int
    unknown_count: int
    ambiguous_count: int
    known_objects_per_frame: list[int]


class IdentificationResult(BaseModel):
    """Identification of a set of tracklets, with the SkyBoT fields used."""

    config: IdentificationConfig
    fields: list[KnownObjectField]
    identifications: list[TrackletIdentification]
    diagnostics: IdentificationDiagnostics
