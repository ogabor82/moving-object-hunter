import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from app.api.errors import ApiError, ErrorResponse
from app.api.tracklet_store import TrackletStore, get_tracklet_store
from app.models.observation import Observation
from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG, PipelineConfig
from app.models.tracklet import Tracklet, TrackletBuildDiagnostics
from app.services.catalog_service import CatalogNormalizationError
from app.services.pipeline_service import build_tracklets_from_observations
from app.services.ztf_service import (
    InsufficientFramesError,
    ObservationNotFoundError,
    ZTFMetadataMappingError,
    ZTFServiceError,
    fetch_observations,
)


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
        observations = fetch_observations(request.observation_ids)
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
