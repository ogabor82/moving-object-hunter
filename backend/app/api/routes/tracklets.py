import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from app.api.errors import ApiError, ErrorResponse
from app.api.tracklet_store import TrackletStore, get_tracklet_store
from app.models.identification import IdentificationConfig, TrackletIdentification
from app.models.known_object import KnownObjectField
from app.models.observation import Observation
from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG, PipelineConfig
from app.models.review_ranking import ReviewRanking
from app.models.tracklet import Tracklet, TrackletBuildDiagnostics
from app.services.catalog_service import CatalogNormalizationError
from app.services.identification_service import identify_tracklets
from app.services.pipeline_service import build_tracklets_from_observations
from app.services.review_ranking_service import rank_for_review
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
    POST /api/tracklets/{tracklet_id}/identify, and the build for
    GET /api/tracklets/builds/{build_id}/review-ranking, while the build is
    kept.
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
    store.add_build(
        build_id, tracklets, observations, request.config, result.sharp_by_source_id()
    )
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


class ReviewRankingResponse(ReviewRanking):
    """Every tracklet of one build for human review, M1 order first.

    `candidates` holds ALL built tracklets (`candidate_count` of them) in
    review order; `unranked` holds every rejected tracklet. Nothing is
    filtered: `candidate_count + unranked_count == tracklet_count`.
    """

    build_id: str
    config: PipelineConfig
    observations: list[Observation]
    tracklet_count: int
    candidate_count: int
    unranked_count: int


@router.get(
    "/builds/{build_id}/review-ranking",
    response_model=ReviewRankingResponse,
    responses={404: {"model": ErrorResponse}},
)
def review_ranking(
    build_id: str,
    store: TrackletStore = Depends(get_tracklet_store),
) -> ReviewRankingResponse:
    """All candidates of a build in M1 review-priority order (AS-041).

    Rank orders human review only: M1 is not a classifier, its score is not
    a probability or confidence, and no candidate is removed for its score,
    rank, mask / flag state, faintness or star proximity; there is no
    cutoff. Inputs are only the 8 frozen M1 features; identity (SkyBoT,
    designation, known / unknown) and star proximity are never used. Each
    candidate carries its tracklet and a `view` (frame sequence, cutout
    centre and size) to open it in the blink comparator / overlay; its
    `tracklet_id` works with POST /api/tracklets/{tracklet_id}/identify.
    Deterministic; offline (no IRSA or SkyBoT call).
    """
    stored = store.get_build(build_id)
    if stored is None:
        raise ApiError(
            404,
            "BUILD_NOT_FOUND",
            f"Build {build_id} is not known (builds are kept in memory for "
            "the most recent builds only).",
        )
    ranking = rank_for_review(
        stored.tracklets, stored.sharp_by_source_id, stored.observations, stored.config
    )
    return ReviewRankingResponse(
        **dict(ranking),
        build_id=build_id,
        config=stored.config,
        observations=stored.observations,
        tracklet_count=len(stored.tracklets),
        candidate_count=len(ranking.candidates),
        unranked_count=len(ranking.unranked),
    )


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
