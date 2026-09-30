import pytest
from fastapi.testclient import TestClient

from app.api.routes import tracklets as route
from app.api.tracklet_store import TrackletStore, get_tracklet_store
from app.main import app
from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG
from app.services import pipeline_service
from app.services.catalog_service import CatalogNormalizationError
from app.services.ztf_service import ObservationNotFoundError, ZTFServiceError
from app.validation.presets import load_frozen_observations
from tests.test_validation_tooling import (
    PRODUCT_IDS,
    STAR_A,
    STAR_B,
    TARGET_START,
    frames_with,
    mover,
)


@pytest.fixture
def store():
    store = TrackletStore()
    app.dependency_overrides[get_tracklet_store] = lambda: store
    yield store
    app.dependency_overrides.clear()


@pytest.fixture
def frames(monkeypatch):
    frames = frames_with(
        lambda minute: [STAR_A, STAR_B, mover(TARGET_START, minute)]
    )
    monkeypatch.setattr(
        route,
        "fetch_observations",
        lambda ids: [frame.observation for frame in frames],
    )
    monkeypatch.setattr(
        pipeline_service, "load_frame_sources", lambda observations, client: frames
    )
    return frames


client = TestClient(app)


def test_build_returns_tracklets_and_stores_them(store, frames) -> None:
    response = client.post(
        "/api/tracklets/build", json={"observation_ids": PRODUCT_IDS}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["config"] == EXPERIMENTAL_DEFAULT_CONFIG.model_dump()
    assert [o["product_id"] for o in body["observations"]] == PRODUCT_IDS
    assert body["source_counts"] == [3, 3, 3]
    assert body["candidate_counts"] == [1, 1, 1]
    assert body["diagnostics"]["tracklet_count"] == 1
    [tracklet] = body["tracklets"]
    assert tracklet["tracklet_id"] == f"{body['build_id']}.trk-0001"
    assert tracklet["status"] == "tracklet_built"
    assert len(tracklet["detections"]) == 3
    stored = store.get(tracklet["tracklet_id"])
    assert stored is not None
    assert [o.product_id for o in stored.observations] == PRODUCT_IDS


def test_build_ids_are_unique_across_builds(store, frames) -> None:
    first = client.post("/api/tracklets/build", json={"observation_ids": PRODUCT_IDS})
    second = client.post(
        "/api/tracklets/build", json={"observation_ids": PRODUCT_IDS}
    )

    first_id = first.json()["tracklets"][0]["tracklet_id"]
    second_id = second.json()["tracklets"][0]["tracklet_id"]
    assert first_id != second_id
    assert store.get(first_id) is not None and store.get(second_id) is not None


def test_config_is_applied(store, frames) -> None:
    config = EXPERIMENTAL_DEFAULT_CONFIG.model_copy(
        update={"max_rate_arcsec_per_min": 0.1}
    )

    response = client.post(
        "/api/tracklets/build",
        json={"observation_ids": PRODUCT_IDS, "config": config.model_dump()},
    )

    assert response.status_code == 200
    assert response.json()["config"]["max_rate_arcsec_per_min"] == 0.1
    assert response.json()["tracklets"] == []


@pytest.mark.parametrize(
    "payload",
    [
        {"observation_ids": [1, 2]},
        {"observation_ids": [1, 1, 2]},
        {"observation_ids": list(range(11))},
        {
            "observation_ids": [1, 2, 3],
            "config": {
                **EXPERIMENTAL_DEFAULT_CONFIG.model_dump(),
                "search_radius_arcsec": 0,
            },
        },
        {},
    ],
)
def test_invalid_requests_are_rejected(store, payload) -> None:
    assert client.post("/api/tracklets/build", json=payload).status_code == 422


def failing(exception):
    def raiser(*args, **kwargs):
        raise exception

    return raiser


@pytest.mark.parametrize(
    ("target", "exception", "status", "code"),
    [
        (
            "fetch_observations",
            ObservationNotFoundError("no metadata for pid(s) [3]"),
            404,
            "NO_ZTF_OBSERVATIONS",
        ),
        ("fetch_observations", ZTFServiceError("HTTP 503"), 502, "ZTF_METADATA_FAILED"),
        (
            "build_tracklets_from_observations",
            ZTFServiceError("ZTF PSF catalog request failed with HTTP 404."),
            502,
            "CATALOG_DOWNLOAD_FAILED",
        ),
        (
            "build_tracklets_from_observations",
            CatalogNormalizationError("no MAGZP"),
            502,
            "CATALOG_DOWNLOAD_FAILED",
        ),
        (
            "build_tracklets_from_observations",
            ValueError("Frames must be in strictly increasing time order."),
            400,
            "TRACKLET_BUILD_FAILED",
        ),
    ],
)
def test_domain_errors_are_mapped(
    store, frames, monkeypatch, target, exception, status, code
) -> None:
    monkeypatch.setattr(route, target, failing(exception))

    response = client.post(
        "/api/tracklets/build", json={"observation_ids": PRODUCT_IDS}
    )

    assert response.status_code == status
    assert response.json()["error"]["code"] == code


def test_store_evicts_oldest_build() -> None:
    frames = frames_with(lambda minute: [mover(TARGET_START, minute)])
    tracklets = pipeline_service.build_tracklets_from_frames(
        frames, EXPERIMENTAL_DEFAULT_CONFIG
    ).build.tracklets
    store = TrackletStore(max_builds=2)
    observations = [frame.observation for frame in frames]

    for build_id in ("a", "b", "c"):
        store.add_build(
            build_id,
            [t.model_copy(update={"tracklet_id": f"{build_id}.x"}) for t in tracklets],
            observations,
            EXPERIMENTAL_DEFAULT_CONFIG,
        )

    assert store.get("a.x") is None
    assert store.get("b.x") is not None
    assert store.get("c.x") is not None
    assert store.get("missing") is None


def test_build_of_frozen_sequence_needs_no_metadata_lookup(
    store, frames, monkeypatch
) -> None:
    frozen = load_frozen_observations()
    poc_ids = [465495204215, 465423434215, 465467854215]  # 1995 DH, unordered

    def metadata_down(ids):
        raise ZTFServiceError("IRSA ZTF metadata request failed: HTTP 504")

    monkeypatch.setattr(route, "fetch_observations", metadata_down)
    seen = []
    monkeypatch.setattr(
        pipeline_service,
        "load_frame_sources",
        lambda observations, client: seen.append(observations) or frames,
    )

    response = client.post("/api/tracklets/build", json={"observation_ids": poc_ids})

    assert response.status_code == 200
    assert seen == [[frozen[pid] for pid in sorted(poc_ids)]]  # time order
    assert [o["product_id"] for o in response.json()["observations"]] == sorted(poc_ids)


def test_build_of_mixed_sequence_uses_irsa_metadata(store, frames, monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        route,
        "fetch_observations",
        lambda ids: calls.append(ids) or [frame.observation for frame in frames],
    )

    client.post(
        "/api/tracklets/build",
        json={"observation_ids": [465423434215, 465467854215, 999]},
    )

    assert calls == [[465423434215, 465467854215, 999]]
