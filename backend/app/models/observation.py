from datetime import datetime, timedelta

from pydantic import BaseModel, Field


class Observation(BaseModel):
    """Provider-independent metadata for one astronomical observation."""

    product_id: int
    observed_at: datetime
    field: int
    filter_code: str
    ccd_id: int
    quadrant_id: int
    file_frac_day: str
    exposure_seconds: float | None = Field(default=None, gt=0)

    @property
    def mid_exposure_at(self) -> datetime:
        """Mid-exposure time; `observed_at` is the exposure start (ZSDS §13)."""
        if self.exposure_seconds is None:
            raise ValueError(
                "exposure_seconds is required to compute the mid-exposure time."
            )
        return self.observed_at + timedelta(seconds=self.exposure_seconds / 2)
