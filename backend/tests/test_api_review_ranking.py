import pytest
from fastapi.testclient import TestClient

from app.api.routes import tracklets as route
from app.api.routes.frames import ProjectRequest
from app.api.tracklet_store import TrackletStore, get_tracklet_store
from app.main import app
from app.services import pipeline_service
from app.services import review_ranking_service as rr
from tests.synthetic_frames import ARCSEC
from tests.test_validation_tooling import PRODUCT_IDS, STAR_A, STAR_B, TARGET_START, frames_with, mover


client = TestClient(app)
SECOND_START = (TARGET_START[0] + 60 * ARCSEC, TARGET_START[1] + 40 * ARCSEC)


@pytest.fixture
def store():
    store = TrackletStore()
    app.dependency_overrides[get_tracklet_store] = lambda: store
    yield store
    app.dependency_overrides.clear()


@pytest.fixture
def frames(monkeypatch):
    frames = frames_with(
        lambda minute: [STAR_A, STAR_B, mover(TARGET_START, minute), mover(SECOND_START, minute)]
    )
    # Raw sharp for every source except one detection of the second mover.
    frames = [
        frame.model_copy(update={"sharp_by_source_id": {
            d.source_id: 0.05 * (i + 1) for i, d in enumerate(frame.detections) if not (k == 1 and i == 3)
        }})
        for k, frame in enumerate(frames)
    ]
    monkeypatch.setattr(route, "fetch_observations", lambda ids: [f.observation for f in frames])
    monkeypatch.setattr(pipeline_service, "load_frame_sources", lambda observations, client: frames)
    return frames


def build() -> dict:
    response = client.post("/api/tracklets/build", json={"observation_ids": PRODUCT_IDS})
    assert response.status_code == 200
    return response.json()


def test_review_ranking_returns_every_tracklet_in_review_order(store, frames) -> None:
    built = build()

    response = client.get(f"/api/tracklets/builds/{built['build_id']}/review-ranking")

    assert response.status_code == 200
    body = response.json()
    assert body["build_id"] == built["build_id"]
    assert body["tracklet_count"] == len(built["tracklets"]) == 2
    assert body["candidate_count"] + body["unranked_count"] == body["tracklet_count"]
    assert sorted(c["tracklet_id"] for c in body["candidates"]) == sorted(t["tracklet_id"] for t in built["tracklets"])
    assert [c["review_rank"] for c in body["candidates"]] == [1, 2]
    scores = [c["review_priority_score"] for c in body["candidates"]]
    assert scores == sorted(scores, reverse=True)
    assert body["semantics"]["purpose"] == "review_priority_only"
    assert body["semantics"]["is_classifier"] is False
    assert body["semantics"]["score_is_probability"] is False
    assert body["semantics"]["candidates_filtered"] is False
    assert [i["feature"] for i in body["ranker"]["inputs"]] == [n for n, _ in rr.M1_INPUTS]
    candidate = body["candidates"][0]
    assert len(candidate["evidence"]) == 8
    assert candidate["tracklet"]["tracklet_id"] == candidate["tracklet_id"]
    # The second mover lacks one raw sharp value: missing, not dropped.
    states = sorted(c["sharp_availability"] for c in body["candidates"])
    assert states == ["complete", "partial"]


def test_ranked_candidate_opens_in_the_blink_overlay_and_identify_workflow(store, frames) -> None:
    built = build()
    body = client.get(f"/api/tracklets/builds/{built['build_id']}/review-ranking").json()

    for candidate in body["candidates"]:
        view = candidate["view"]
        assert view["product_ids"] == PRODUCT_IDS
        # Valid input of POST /api/frames/project for each frame of the sequence.
        for detection in candidate["tracklet"]["detections"]:
            ProjectRequest(
                product_id=detection["detection"]["observation_product_id"],
                ra=view["center_ra"],
                dec=view["center_dec"],
                size_arcsec=view["size_arcsec"],
                positions=[{"ra": detection["detection"]["ra"], "dec": detection["detection"]["dec"]}],
            )
        # The identify endpoint knows the candidate's tracklet id.
        assert store.get(candidate["tracklet_id"]) is not None


def test_review_ranking_is_deterministic(store, frames) -> None:
    build_id = build()["build_id"]

    first = client.get(f"/api/tracklets/builds/{build_id}/review-ranking").json()
    second = client.get(f"/api/tracklets/builds/{build_id}/review-ranking").json()

    assert first == second


def test_unknown_build_is_404(store) -> None:
    response = client.get("/api/tracklets/builds/missing/review-ranking")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "BUILD_NOT_FOUND"


def test_store_keeps_only_the_sharp_of_tracklet_detections(store, frames) -> None:
    built = build()

    stored = store.get_build(built["build_id"])

    detection_ids = {d["detection"]["source_id"] for t in built["tracklets"] for d in t["detections"]}
    assert set(stored.sharp_by_source_id) <= detection_ids
    assert len(stored.sharp_by_source_id) == len(detection_ids) - 1
