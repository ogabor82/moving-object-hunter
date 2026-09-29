from pydantic import BaseModel, ConfigDict, Field


class KnownObjectEphemeris(BaseModel):
    """Predicted position of one known solar-system object (from SkyBoT).

    Positions are astrometric J2000 as seen from `observer` at the query
    epoch. `position_error_arcsec` reflects orbit uncertainty only (SkyBoT
    FAQ: ASTORB CEU); model and reference-frame errors are not included.
    """

    model_config = ConfigDict(allow_inf_nan=False)

    designation: str = Field(
        min_length=1,
        description="Number for numbered objects, otherwise the name",
    )
    number: int | None = None
    name: str = Field(min_length=1)
    object_class: str
    predicted_ra: float = Field(ge=0.0, lt=360.0, description="[deg]")
    predicted_dec: float = Field(ge=-90.0, le=90.0, description="[deg]")
    v_magnitude: float | None = None
    position_error_arcsec: float = Field(ge=0.0)
    distance_from_field_center_arcsec: float = Field(ge=0.0)
    motion_ra_cos_dec_arcsec_per_hour: float
    motion_dec_arcsec_per_hour: float
    observer_distance_au: float | None = None
    heliocentric_distance_au: float | None = None


class RejectedSkyBoTRow(BaseModel):
    """A SkyBoT row that could not be normalized."""

    row_index: int
    reason: str


class KnownObjectField(BaseModel):
    """Known objects in one field at one epoch, from one SkyBoT query."""

    epoch_jd_utc: float
    field_ra: float
    field_dec: float
    field_radius_degrees: float
    observer: str
    objects: list[KnownObjectEphemeris]
    rejected_rows: list[RejectedSkyBoTRow]
