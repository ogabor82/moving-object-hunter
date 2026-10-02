from pydantic import BaseModel, Field, computed_field

from app.models.observation import Observation
from app.models.source_detection import SourceDetection


class FrameSources(BaseModel):
    """Normalized source detections of one observation frame.

    `sharp_by_source_id` keeps the raw ZTF PSF catalog `sharp` (DAOPhot
    shape metric) beside, not inside, the provider-independent
    SourceDetection (docs/ztf_psf_catalog_mapping.md): finite values only,
    by SourceDetection.source_id; empty when the source has no `sharp`.
    It feeds the M1 review ranking (`sharp_abs_max`, AS-041) and is never
    used to filter or match detections.
    """

    observation: Observation
    detections: list[SourceDetection]
    rejected_row_count: int = Field(ge=0)
    sharp_by_source_id: dict[str, float] = Field(default_factory=dict, repr=False)

    @computed_field
    @property
    def source_count(self) -> int:
        return len(self.detections)
