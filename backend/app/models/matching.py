from pydantic import BaseModel, Field, computed_field

from app.models.observation import Observation
from app.models.source_detection import SourceDetection


class StationaryMatchingConfig(BaseModel):
    """Stationary matching parameters.

    No default tolerance: per 02 – Research / Evidence the value must be
    calibrated from the Validation Set, not guessed.
    """

    stationary_tolerance_arcsec: float = Field(gt=0)


class FrameMatchResult(BaseModel):
    """Stationary matching outcome for one frame."""

    observation: Observation
    stationary: list[SourceDetection]
    unmatched: list[SourceDetection]


class StationaryMatchResult(BaseModel):
    """Stationary matching outcome for a frame sequence, in frame order."""

    config: StationaryMatchingConfig
    frames: list[FrameMatchResult]


class CandidateFrame(BaseModel):
    """Moving-source candidates of one frame, i.e. its unmatched sources."""

    observation: Observation
    candidates: list[SourceDetection]

    @computed_field
    @property
    def candidate_count(self) -> int:
        return len(self.candidates)
