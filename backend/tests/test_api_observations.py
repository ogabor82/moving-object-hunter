from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes import observations as route
from app.main import app
from app.models.observation import Observation
from app.services.ztf_service import ZTFServiceError, search_observations


client = TestClient(app)
PARAMS = {
    "ra": 255.57691,
    "dec": 12.28378,
    "radius_deg": 0.1,
    "start_time": "2018-04-11T00:00:00Z",
    "end_time": "2018-04-12T00:00:00Z",
}
OBSERVATION = Observation(
    product_id=465423434215,
    observed_at=datetime(2018, 4, 11, 10, 9, 45, tzinfo=timezone.utc),
    field=535,
    filter_code="zr",
    ccd_id=11,
    quadrant_id=3,
    file_frac_day="20180411423368",
    exposure_seconds=30.0,
)


def test_search_returns_normalized_observations(monkeypatch) -> None:
    calls = []

    def fake_search(ra, dec, radius, start_jd, end_jd):
        calls.append((ra, dec, radius, start_jd, end_jd))
        return [OBSERVATION]

    monkeypatch.setattr(route, "search_observations", fake_search)

    response = client.get("/api/observations/search", params=PARAMS)

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["observations"][0]["product_id"] == 465423434215
    assert body["observations"][0]["exposure_seconds"] == 30.0
    assert set(body["observations"][0]) == set(Observation.model_fields)
    ra, dec, radius, start_jd, end_jd = calls[0]
    assert (ra, dec, radius) == (255.57691, 12.28378, 0.1)
    assert start_jd == pytest.approx(2458219.5)
    assert end_jd == pytest.approx(2458220.5)


def test_naive_times_are_treated_as_utc(monkeypatch) -> None:
    captured = {}

    def fake_search(ra, dec, radius, start_jd, end_jd):
        captured["start_jd"] = start_jd
        return []

    monkeypatch.setattr(route, "search_observations", fake_search)

    response = client.get(
        "/api/observations/search",
        params={**PARAMS, "start_time": "2018-04-11T00:00:00"},
    )

    assert response.status_code == 200
    assert response.json()["count"] == 0
    assert captured["start_jd"] == pytest.approx(2458219.5)


@pytest.mark.parametrize(
    "override",
    [
        {"ra": 360.0},
        {"dec": -91.0},
        {"radius_deg": 0.0},
        {"radius_deg": 2.5},
        {"start_time": "not-a-date"},
    ],
)
def test_invalid_parameters_are_rejected(override: dict) -> None:
    response = client.get("/api/observations/search", params={**PARAMS, **override})

    assert response.status_code == 422


def test_missing_parameter_is_rejected() -> None:
    params = dict(PARAMS)
    del params["end_time"]

    assert client.get("/api/observations/search", params=params).status_code == 422


@pytest.mark.parametrize(
    ("start", "end", "message"),
    [
        ("2018-04-12T00:00:00Z", "2018-04-11T00:00:00Z", "after"),
        ("2018-01-01T00:00:00Z", "2018-03-01T00:00:00Z", "31 days"),
    ],
)
def test_invalid_time_range_is_a_sky_query_error(start, end, message) -> None:
    response = client.get(
        "/api/observations/search",
        params={**PARAMS, "start_time": start, "end_time": end},
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "INVALID_SKY_QUERY"
    assert message in error["message"]


def test_irsa_failure_is_reported_as_bad_gateway(monkeypatch) -> None:
    def failing(*args):
        raise ZTFServiceError("IRSA ZTF metadata request failed with HTTP 503.")

    monkeypatch.setattr(route, "search_observations", failing)

    response = client.get("/api/observations/search", params=PARAMS)

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "ZTF_METADATA_FAILED"


def test_search_service_sends_box_size_and_overlaps() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["SIZE"] == "0.2"
        assert request.url.params["INTERSECT"] == "OVERLAPS"
        return httpx.Response(
            200,
            text=(
                "obsdate,obsjd,field,filtercode,ccdid,qid,pid,filefracday,"
                "imgtypecode,exptime\n"
                "2018-04-11 11:13:43+00,2458219.97,535,zr,11,3,2,20180411467847,o,30\n"
                "2018-04-11 10:09:45+00,2458219.92,535,zr,11,3,1,20180411423368,o,30\n"
            ),
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        observations = search_observations(
            255.5, 12.3, 0.1, 2458219.5, 2458220.5, http
        )

    assert [o.product_id for o in observations] == [1, 2]


@pytest.mark.parametrize(
    "arguments",
    [
        (360.0, 0.0, 0.1, 1.0, 2.0),
        (10.0, 95.0, 0.1, 1.0, 2.0),
        (10.0, 0.0, 0.0, 1.0, 2.0),
        (10.0, 0.0, 0.1, 2.0, 2.0),
    ],
)
def test_search_service_validates_input(arguments) -> None:
    with pytest.raises(ValueError):
        search_observations(*arguments)
