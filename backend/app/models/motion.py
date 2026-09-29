from pydantic import BaseModel, ConfigDict, Field


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
