import json
from datetime import datetime, timezone

import httpx
import pytest

from app.models.observation import Observation
from app.services.catalog_service import load_frame_sources
from app.services.ztf_service import ZTFServiceError
from tests.test_psf_catalog import make_psf_catalog_payload


def make_observation(product_id: int, minute: int) -> Observation:
    return Observation(
        product_id=product_id,
        observed_at=datetime(2018, 4, 11, 10, minute, tzinfo=timezone.utc),
        field=535,
        filter_code="zr",
        ccd_id=11,
        quadrant_id=3,
        file_frac_day=f"2018041142{minute:04d}",
    )


OBSERVATIONS = [
    make_observation(1001, 9),
    make_observation(1002, 13),
    make_observation(1003, 53),
]
ROWS_BY_FILE_FRAC_DAY = {
    "20180411420009": 3,
    "20180411420013": 0,
    "20180411420053": 5,
}


def make_client() -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        file_frac_day = request.url.path.rsplit("/", 1)[-1].split("_")[1]
        rows = ROWS_BY_FILE_FRAC_DAY[file_frac_day]
        return httpx.Response(200, content=make_psf_catalog_payload(rows=rows))

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_load_frame_sources_returns_one_frame_per_observation_in_order() -> None:
    with make_client() as client:
        frames = load_frame_sources(OBSERVATIONS, client)

    assert [frame.observation for frame in frames] == OBSERVATIONS
    assert [frame.source_count for frame in frames] == [3, 0, 5]
    assert all(frame.rejected_row_count == 0 for frame in frames)
    assert {
        detection.observation_product_id for detection in frames[2].detections
    } == {1003}


def test_frame_sources_serializes_source_count() -> None:
    with make_client() as client:
        [frame] = load_frame_sources(OBSERVATIONS[:1], client)

    payload = json.loads(frame.model_dump_json())

    assert payload["source_count"] == 3
    assert len(payload["detections"]) == 3
    assert payload["observation"]["product_id"] == 1001


def test_load_frame_sources_fails_when_a_catalog_is_unavailable() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(404, text="Not found")
    )

    with httpx.Client(transport=transport) as client:
        with pytest.raises(ZTFServiceError, match="HTTP 404"):
            load_frame_sources(OBSERVATIONS, client)
