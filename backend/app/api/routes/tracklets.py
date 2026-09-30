import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from app.api.errors import ApiError, ErrorResponse
from app.api.tracklet_store import TrackletStore, get_tracklet_store
from app.models.identification import IdentificationConfig, TrackletIdentification
from app.models.known_object import KnownObjectField
from app.models.observation import Observation
from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG, PipelineConfig
from app.models.tracklet import Tracklet, TrackletBuildDiagnostics
from app.services.catalog_service import CatalogNormalizationError
from app.services.identification_service import identify_tracklets
from app.services.pipeline_service import build_tracklets_from_observations
from app.services.skybot_service import SkyBoTServiceError
from app.services.ztf_service import (
    InsufficientFramesError,
    ObservationNotFoundError,
    ZTFMetadataMappingError,
    ZTFServiceError,
    fetch_observations,
)
from app.validation.presets import load_frozen_observations


router = APIRouter(prefix="/tracklets", tags=["tracklets"])

# Bounds the synchronous request (each frame downloads a PSF catalog).
MAX_OBSERVATIONS = 10


class TrackletBuildRequest(BaseModel):
    observation_ids: list[int] = Field(
        min_length=3,
        max_length=MAX_OBSERVATIONS,
        description="ZTF science product ids (pid) of one frame sequence",
    )
    config: PipelineConfig = Field(
        default=EXPERIMENTAL_DEFAULT_CONFIG,
        description="Experimental defaults if omitted (not calibrated)",
    )

    @field_validator("observation_ids")
    @classmethod
    def unique_ids(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value):
            raise ValueError("observation_ids must be unique")
        return value


class TrackletBuildResponse(BaseModel):
    build_id: str
    config: PipelineConfig
    observations: list[Observation]
    source_counts: list[int]
    candidate_counts: list[int]
    diagnostics: TrackletBuildDiagnostics
    tracklets: list[Tracklet]


@router.post(
    "/build",
    response_model=TrackletBuildResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
def build(
    request: TrackletBuildRequest,
    store: TrackletStore = Depends(get_tracklet_store),
) -> TrackletBuildResponse:
    """Build tracklets from a ZTF frame sequence (synchronous).

    Tracklet ids are `<build_id>.<tracklet id>` and stay available for
    POST /api/tracklets/{tracklet_id}/identify while the build is kept.
    """
    try:
        observations = _observations(request.observation_ids)
    except ObservationNotFoundError as exc:
        raise ApiError(404, "NO_ZTF_OBSERVATIONS", str(exc)) from exc
    except (ZTFServiceError, ZTFMetadataMappingError) as exc:
        raise ApiError(502, "ZTF_METADATA_FAILED", str(exc)) from exc

    try:
        result = build_tracklets_from_observations(observations, request.config)
    except InsufficientFramesError as exc:
        raise ApiError(400, "INSUFFICIENT_FRAMES", str(exc)) from exc
    except (ZTFServiceError, CatalogNormalizationError) as exc:
        raise ApiError(502, "CATALOG_DOWNLOAD_FAILED", str(exc)) from exc
    except ValueError as exc:
        raise ApiError(400, "TRACKLET_BUILD_FAILED", str(exc)) from exc

    build_id = uuid.uuid4().hex[:12]
    tracklets = [
        tracklet.model_copy(
            update={"tracklet_id": f"{build_id}.{tracklet.tracklet_id}"}
        )
        for tracklet in result.build.tracklets
    ]
    store.add_build(build_id, tracklets, observations, request.config)
    return TrackletBuildResponse(
        build_id=build_id,
        config=request.config,
        observations=observations,
        source_counts=[frame.source_count for frame in result.frames],
        candidate_counts=[frame.candidate_count for frame in result.candidate_frames],
        diagnostics=result.build.diagnostics,
        tracklets=tracklets,
    )


def _observations(product_ids: list[int]) -> list[Observation]:
    """Frozen validation metadata when every frame has it, else IRSA
    (same order as fetch_observations: time, then product id)."""
    frozen = load_frozen_observations()
    if all(pid in frozen for pid in product_ids):
        return sorted(
            (frozen[pid] for pid in product_ids),
            key=lambda observation: (observation.observed_at, observation.product_id),
        )
    return fetch_observations(product_ids)


class IdentifyRequest(BaseModel):
    match_radius_arcsec: float | None = Field(
        default=None,
        gt=0,
        description="Defaults to the match radius of the build's config",
    )


class IdentifyResponse(BaseModel):
    tracklet_id: str
    config: IdentificationConfig
    identification: TrackletIdentification
    skybot_fields: list[KnownObjectField]


@router.post(
    "/{tracklet_id}/identify",
    response_model=IdentifyResponse,
    responses={404: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
def identify(
    tracklet_id: str,
    request: IdentifyRequest | None = None,
    store: TrackletStore = Depends(get_tracklet_store),
) -> IdentifyResponse:
    """Identify one built tracklet against SkyBoT (live, one query per frame).

    Status is known / unknown / ambiguous (05 – Scientific Validation);
    unknown is not a discovery. A SkyBoT failure is a 502, never unknown.
    """
    stored = store.get(tracklet_id)
    if stored is None:
        raise ApiError(
            404,
            "TRACKLET_NOT_FOUND",
            f"Tracklet {tracklet_id} is not known (built tracklets are kept "
            "in memory for the most recent builds only).",
        )
    radius = (
        request.match_radius_arcsec
        if request is not None and request.match_radius_arcsec is not None
        else stored.config.match_radius_arcsec
    )
    config = IdentificationConfig(match_radius_arcsec=radius)

    try:
        result = identify_tracklets([stored.tracklet], stored.observations, config)
    except SkyBoTServiceError as exc:
        raise ApiError(502, "SKYBOT_LOOKUP_FAILED", str(exc)) from exc
    except ValueError as exc:
        raise ApiError(400, "IDENTIFICATION_FAILED", str(exc)) from exc

    [identification] = result.identifications
    return IdentifyResponse(
        tracklet_id=tracklet_id,
        config=config,
        identification=identification,
        skybot_fields=result.fields,
    )
