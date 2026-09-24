from datetime import datetime

from pydantic import BaseModel


class Observation(BaseModel):
    """Provider-independent metadata for one astronomical observation."""

    product_id: int
    observed_at: datetime
    field: int
    filter_code: str
    ccd_id: int
    quadrant_id: int
    file_frac_day: str
