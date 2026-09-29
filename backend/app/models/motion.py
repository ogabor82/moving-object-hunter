from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.source_detection import SourceDetection


class MotionVector(BaseModel):
    """Apparent on-sky motion between two detections."""

    model_config = ConfigDict(allow_inf_nan=False)

    time_delta_minutes: float = Field(gt=0.0)
    separation_arcsec: float = Field(ge=0.0)
    rate_arcsec_per_min: float = Field(ge=0.0)
    position_angle_deg: float = Field(
        ge=0.0,
        lt=360.0,
        description="Direction of motion, east of north [deg]",
    )


class PredictedPosition(BaseModel):
    """Expected position of a moving source at a given time."""

    model_config = ConfigDict(allow_inf_nan=False)

    time: datetime
    ra: float = Field(ge=0.0, lt=360.0, description="Right Ascension [deg]")
    dec: float = Field(ge=-90.0, le=90.0, description="Declination [deg]")


class PredictionSearchConfig(BaseModel):
    """Search around a predicted position.

    No default radius: it must be calibrated from the Validation Set.
    """

    search_radius_arcsec: float = Field(gt=0)


class PredictionMatch(BaseModel):
    """A detection found near a predicted position."""

    detection: SourceDetection
    distance_arcsec: float = Field(ge=0.0)
