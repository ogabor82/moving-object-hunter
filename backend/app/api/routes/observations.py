from datetime import datetime, timedelta, timezone

from astropy.time import Time
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.errors import ApiError, ErrorResponse
from app.models.observation import Observation
from app.services.ztf_service import (
    ZTFMetadataMappingError,
    ZTFServiceError,
    search_observations,
)


router = APIRouter(prefix="/observations", tags=["observations"])

# Guards against archive-wide queries from the MVP API.
MAX_RADIUS_DEGREES = 2.0
MAX_TIME_SPAN = timedelta(days=31)


class ObservationSearchResponse(BaseModel):
    ra: float
    dec: float
    radius_deg: float
    start_time: datetime
    end_time: datetime
    count: int
    observations: list[Observation]


@router.get(
    "/search",
    response_model=ObservationSearchResponse,
    responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
def search(
    ra: float = Query(ge=0.0, lt=360.0, description="Right Ascension [deg]"),
    dec: float = Query(ge=-90.0, le=90.0, description="Declination [deg]"),
    radius_deg: float = Query(
        gt=0.0,
        le=MAX_RADIUS_DEGREES,
        description=(
            "Search radius [deg]; IRSA is queried with the circumscribing "
            "box of side 2 * radius"
        ),
    ),
    start_time: datetime = Query(description="Window start, UTC if no offset"),
    end_time: datetime = Query(description="Window end (exclusive)"),
) -> ObservationSearchResponse:
    """Normalized ZTF observations near a position within a time range."""
    start = _as_utc(start_time)
    end = _as_utc(end_time)
    if end <= start:
        raise ApiError(400, "INVALID_SKY_QUERY", "end_time must be after start_time.")
    if end - start > MAX_TIME_SPAN:
        raise ApiError(
            400,
            "INVALID_SKY_QUERY",
            f"The time range may span at most {MAX_TIME_SPAN.days} days.",
        )

    try:
        observations = search_observations(
            ra,
            dec,
            radius_deg,
            Time(start, scale="utc").jd,
            Time(end, scale="utc").jd,
        )
    except (ZTFServiceError, ZTFMetadataMappingError) as exc:
        raise ApiError(502, "ZTF_METADATA_FAILED", str(exc)) from exc

    return ObservationSearchResponse(
        ra=ra,
        dec=dec,
        radius_deg=radius_deg,
        start_time=start,
        end_time=end,
        count=len(observations),
        observations=observations,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
