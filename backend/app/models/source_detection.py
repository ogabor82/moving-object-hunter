from pydantic import BaseModel, ConfigDict, Field


class SourceDetection(BaseModel):
    """Provider-independent source detected on one observation frame.

    See docs/ztf_psf_catalog_mapping.md for how ZTF catalog columns map here.
    """

    model_config = ConfigDict(allow_inf_nan=False)

    source_id: str = Field(min_length=1)
    observation_product_id: int
    ra: float = Field(ge=0.0, lt=360.0, description="Right Ascension [deg]")
    dec: float = Field(ge=-90.0, le=90.0, description="Declination [deg]")
    x: float = Field(description="Image x position [pixel]")
    y: float = Field(description="Image y position [pixel]")
    magnitude: float = Field(description="Calibrated magnitude [mag]")
    magnitude_error: float = Field(ge=0.0, description="1-sigma error [mag]")
    snr: float = Field(ge=0.0)
    on_image_edge: bool
    mask_bits: int = Field(ge=0, description="Pixel mask bits; 0 = none set")
