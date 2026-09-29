from pydantic import BaseModel, Field, computed_field

from app.models.observation import Observation
from app.models.source_detection import SourceDetection


class FrameSources(BaseModel):
    """Normalized source detections of one observation frame."""

    observation: Observation
    detections: list[SourceDetection]
    rejected_row_count: int = Field(ge=0)

    @computed_field
    @property
    def source_count(self) -> int:
        return len(self.detections)
