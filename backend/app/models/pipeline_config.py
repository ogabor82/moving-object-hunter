from pydantic import BaseModel, Field

from app.models.identification import IdentificationConfig
from app.models.matching import StationaryMatchingConfig
from app.models.tracklet import TrackletBuildConfig


class PipelineConfig(BaseModel):
    """All tunable thresholds of one detection → identification run."""

    stationary_tolerance_arcsec: float = Field(gt=0)
    max_rate_arcsec_per_min: float = Field(gt=0)
    search_radius_arcsec: float = Field(gt=0)
    max_residual_arcsec: float = Field(gt=0)
    match_radius_arcsec: float = Field(gt=0)

    def stationary_matching(self) -> StationaryMatchingConfig:
        return StationaryMatchingConfig(
            stationary_tolerance_arcsec=self.stationary_tolerance_arcsec
        )

    def tracklet_build(self) -> TrackletBuildConfig:
        return TrackletBuildConfig(
            max_rate_arcsec_per_min=self.max_rate_arcsec_per_min,
            search_radius_arcsec=self.search_radius_arcsec,
            max_residual_arcsec=self.max_residual_arcsec,
        )

    def identification(self) -> IdentificationConfig:
        return IdentificationConfig(match_radius_arcsec=self.match_radius_arcsec)


# Experimental defaults (human decision after AS-022): the values used in
# AS-017..AS-022. They are NOT scientifically calibrated; see
# backend/validation/results/as022_findings.md for their measured behaviour.
EXPERIMENTAL_DEFAULT_CONFIG = PipelineConfig(
    stationary_tolerance_arcsec=1.5,
    max_rate_arcsec_per_min=1.0,
    search_radius_arcsec=2.0,
    max_residual_arcsec=0.5,
    match_radius_arcsec=2.0,
)
