import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes import tracklets as route
from app.api.tracklet_store import TrackletStore, get_tracklet_store
from app.main import app
from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG
from app.services import identification_service, pipeline_service
from app.services.identification_service import mid_exposure_jd_utc
from tests.test_identification import _dms, _hms
from tests.test_validation_tooling import TARGET_START, frames_with, mover


client = TestClient(app)
FRAMES = frames_with(lambda minute: [mover(TARGET_START, minute)])
OBSERVATIONS = [frame.observation for frame in FRAMES]
TRACKLET = pipeline_service.build_tracklets_from_frames(
    FRAMES, EXPERIMENTAL_DEFAULT_CONFIG
).build.tracklets[0].model_copy(update={"tracklet_id": "b1.trk-0001"})


@pytest.fixture
def store():
    store = TrackletStore()
    store.add_build("b1", [TRACKLET], OBSERVATIONS, EXPERIMENTAL_DEFAULT_CONFIG)
    app.dependency_overrides[get_tracklet_store] = lambda: store
    yield store
    app.dependency_overrides.clear()


def skybot_row(designation: int, ra: float, dec: float, error: float = 0.05):
    return {
        "Num": designation,
        "Name": f"Object {designation}",
        "RA (hms)": _hms(ra),
        "DEC (dms)": _dms(dec),
        "Class": "MB>Middle",
        "VMag (mag)": 19.0,
        "Err (arcsec)": error,
        "d (arcsec)": 1.0,
        "dRA (arcsec/h)": 29.5,
        "dDEC (arcsec/h)": 0.0,
        "dg (ua)": 2.0,
        "dh (ua)": 2.8,
    }


def skybot_returning(rows_for_minute):
    """Patch identify_tracklets' HTTP client with a SkyBoT mock."""
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        minute = round(
            (float(request.url.params["-ep"]) - mid_exposure_jd_utc(OBSERVATIONS[0]))
            * 1440
        )
        rows = rows_for_minute(minute)
        return httpx.Response(200, json=rows) if rows else httpx.Response(204)

    return handler, requests


@pytest.fixture
def skybot(monkeypatch):
    def install(rows_for_minute):
        handler, requests = skybot_returning(rows_for_minute)
        transport = httpx.MockTransport(handler)
        original = identification_service.identify_tracklets

        def patched(tracklets, observations, config, **kwargs):
            with httpx.Client(transport=transport) as http:
                return original(tracklets, observations, config, client=http)

        monkeypatch.setattr(route, "identify_tracklets", patched)
        return requests

    return install


def test_known_object_with_residuals(store, skybot) -> None:
    requests = skybot(lambda minute: [skybot_row(48606, *mover(TARGET_START, minute))])

    response = client.post("/api/tracklets/b1.trk-0001/identify")

    assert response.status_code == 200
    body = response.json()
    assert body["tracklet_id"] == "b1.trk-0001"
    assert body["config"] == {"match_radius_arcsec": 2.0}
    identification = body["identification"]
    assert identification["status"] == "known"
    assert identification["best_match"]["designation"] == "48606"
    residuals = identification["best_match"]["residuals"]
    assert len(residuals) == 3
    assert all(r["residual_arcsec"] < 0.01 for r in residuals)
    assert {"predicted_ra", "predicted_dec", "epoch_jd_utc"} <= set(residuals[0])
    assert len(body["skybot_fields"]) == 3
    assert {r.url.params["-observer"] for r in requests} == {"I41"}


def test_unknown_when_no_known_object(store, skybot) -> None:
    skybot(lambda minute: [])

    response = client.post("/api/tracklets/b1.trk-0001/identify")

    assert response.status_code == 200
    assert response.json()["identification"]["status"] == "unknown"
    assert response.json()["identification"]["best_match"] is None


def test_ambiguous_is_a_result_not_an_error(store, skybot) -> None:
    skybot(
        lambda minute: [
            skybot_row(1, *mover(TARGET_START, minute)),
            skybot_row(2, *mover(TARGET_START, minute)),
        ]
    )

    response = client.post("/api/tracklets/b1.trk-0001/identify")

    assert response.status_code == 200
    identification = response.json()["identification"]
    assert identification["status"] == "ambiguous"
    assert len(identification["candidate_matches"]) == 2


def test_match_radius_override(store, skybot) -> None:
    # 1.5" north of the track: known at the default 2", unknown at 1".
    skybot(
        lambda minute: [
            skybot_row(
                48606,
                mover(TARGET_START, minute)[0],
                TARGET_START[1] + 1.5 / 3600,
            )
        ]
    )

    tight = client.post(
        "/api/tracklets/b1.trk-0001/identify", json={"match_radius_arcsec": 1.0}
    )
    default = client.post("/api/tracklets/b1.trk-0001/identify")

    assert tight.json()["config"] == {"match_radius_arcsec": 1.0}
    assert tight.json()["identification"]["status"] == "unknown"
    assert default.json()["identification"]["status"] == "known"


def test_unknown_tracklet_is_404(store) -> None:
    response = client.post("/api/tracklets/nope.trk-0001/identify")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TRACKLET_NOT_FOUND"


def test_skybot_failure_is_502_not_unknown(store, monkeypatch) -> None:
    monkeypatch.setattr("app.services.skybot_service.time.sleep", lambda _: None)
    transport = httpx.MockTransport(lambda request: httpx.Response(503))
    original = identification_service.identify_tracklets

    def patched(tracklets, observations, config, **kwargs):
        with httpx.Client(transport=transport) as http:
            return original(tracklets, observations, config, client=http)

    monkeypatch.setattr(route, "identify_tracklets", patched)

    response = client.post("/api/tracklets/b1.trk-0001/identify")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "SKYBOT_LOOKUP_FAILED"


def test_invalid_radius_is_rejected(store) -> None:
    response = client.post(
        "/api/tracklets/b1.trk-0001/identify", json={"match_radius_arcsec": 0}
    )

    assert response.status_code == 422
