import base64
from functools import lru_cache

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel

from app.api.errors import ApiError, ErrorResponse
from app.models.observation import Observation
from app.services.cutout_cache import CutoutCache, default_cutout_cache
from app.services.image_service import (
    ORIENTATION,
    STRETCH_METHOD,
    ImageRenderError,
    RenderedFrame,
    render_cutout,
)
from app.services.ztf_service import (
    ObservationNotFoundError,
    ZTFMetadataMappingError,
    ZTFServiceError,
    fetch_observations,
    fetch_science_cutout,
)
from app.validation.presets import (
    BlinkPreset,
    load_blink_presets,
    load_frozen_observations,
)


router = APIRouter(prefix="/frames", tags=["frames"])

MAX_CUTOUT_ARCSEC = 300.0
CACHE_HEADER = "X-Cutout-Cache"


@lru_cache(maxsize=256)
def _irsa_observation(product_id: int) -> Observation:
    """IRSA metadata of one frame; archival, so safe to cache per process.

    Failures are not cached (lru_cache does not store exceptions).
    """
    [observation] = fetch_observations([product_id])
    return observation


def _observation(product_id: int) -> Observation:
    """Frozen validation metadata if the frame has it, else IRSA."""
    frozen = load_frozen_observations().get(product_id)
    return frozen if frozen is not None else _irsa_observation(product_id)


def get_cutout_cache() -> CutoutCache:
    return default_cutout_cache()


class Stretch(BaseModel):
    method: str
    vmin: float
    vmax: float


class FrameCutoutResponse(BaseModel):
    """One science-image cutout as an 8-bit display image.

    `pixels_base64` holds width*height bytes, row-major, row 0 at the top
    (north up, east left). (`center_x`, `center_y`) is the requested sky
    position in display pixels, used to align frames.
    """

    observation: Observation
    ra: float
    dec: float
    size_arcsec: float
    width: int
    height: int
    pixel_scale_arcsec: float
    center_x: float
    center_y: float
    orientation: str
    rotation_deg: float
    transform: list[str]
    stretch: Stretch
    pixels_base64: str


@router.get("/presets", response_model=list[BlinkPreset])
def presets() -> list[BlinkPreset]:
    """Frame sequences of known validation objects (frozen AS-022 data)."""
    return list(load_blink_presets())


@router.get(
    "/cutout",
    response_model=FrameCutoutResponse,
    responses={404: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
def cutout(
    response: Response,
    product_id: int = Query(description="ZTF science product id (pid)"),
    ra: float = Query(ge=0.0, lt=360.0, description="Cutout centre RA [deg]"),
    dec: float = Query(ge=-90.0, le=90.0, description="Cutout centre Dec [deg]"),
    size_arcsec: float = Query(default=90.0, gt=0.0, le=MAX_CUTOUT_ARCSEC),
    cache: CutoutCache = Depends(get_cutout_cache),
) -> FrameCutoutResponse:
    """Square cutout of one ZTF science frame, stretched for display.

    Served from the local cutout cache when possible (no IRSA call; the
    `X-Cutout-Cache` header says `hit` or `miss`). On a miss the frame
    metadata comes from the frozen validation data or IRSA, the cutout from
    IRSA, and it is cached once it has rendered successfully.
    """
    cached = cache.get(product_id, ra, dec, size_arcsec)
    if cached is not None:
        try:
            frame = render_cutout(cached.payload, ra, dec)
        except ImageRenderError:
            cache.discard(product_id, ra, dec, size_arcsec)
        else:
            response.headers[CACHE_HEADER] = "hit"
            return _response(cached.observation, ra, dec, size_arcsec, frame)

    try:
        observation = _observation(product_id)
    except ObservationNotFoundError as exc:
        raise ApiError(404, "NO_ZTF_OBSERVATIONS", str(exc)) from exc
    except (ZTFServiceError, ZTFMetadataMappingError) as exc:
        raise ApiError(502, "ZTF_METADATA_FAILED", str(exc)) from exc

    try:
        payload = fetch_science_cutout(observation, ra, dec, size_arcsec)
        frame = render_cutout(payload, ra, dec)
    except (ZTFServiceError, ImageRenderError) as exc:
        raise ApiError(502, "IMAGE_DOWNLOAD_FAILED", str(exc)) from exc

    cache.put(observation, ra, dec, size_arcsec, payload)
    response.headers[CACHE_HEADER] = "miss"
    return _response(observation, ra, dec, size_arcsec, frame)


def _response(
    observation: Observation,
    ra: float,
    dec: float,
    size_arcsec: float,
    frame: RenderedFrame,
) -> FrameCutoutResponse:
    return FrameCutoutResponse(
        observation=observation,
        ra=ra,
        dec=dec,
        size_arcsec=size_arcsec,
        width=frame.width,
        height=frame.height,
        pixel_scale_arcsec=frame.pixel_scale_arcsec,
        center_x=frame.center_x,
        center_y=frame.center_y,
        orientation=ORIENTATION,
        rotation_deg=frame.rotation_deg,
        transform=list(frame.transform),
        stretch=Stretch(method=STRETCH_METHOD, vmin=frame.vmin, vmax=frame.vmax),
        pixels_base64=base64.b64encode(frame.pixels).decode("ascii"),
    )
