from datetime import datetime, timezone

import httpx
import pytest

from app.services.ztf_service import (
    InsufficientFramesError,
    ZTFServiceError,
    find_observation_sequence,
)


CSV_HEADER = "obsdate,obsjd,field,filtercode,ccdid,qid,pid,filefracday,imgtypecode"
# Real IRSA rows for the POC position on 2018-04-11, in IRSA's response order.
UNSORTED_ROWS = (
    "2018-04-11 11:13:43+00,2458219.967858800,535,zr,11,3,"
    "465467854215,20180411467847,o\n"
    "2018-04-11 11:53:06+00,2458219.995208300,535,zr,11,3,"
    "465495204215,20180411495208,o\n"
    "2018-04-11 10:09:45+00,2458219.923437500,535,zr,11,3,"
    "465423434215,20180411423368,o\n"
)


def make_client(body: str) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["POS"] == "120.5,-10.25"
        assert request.url.params["WHERE"] == (
            "obsjd >= 2458219.5 AND obsjd < 2458220.5"
        )
        return httpx.Response(200, text=f"{CSV_HEADER}\n{body}")

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_find_observation_sequence_returns_time_ordered_observations() -> None:
    with make_client(UNSORTED_ROWS) as client:
        observations = find_observation_sequence(
            120.5, -10.25, 2458219.5, 2458220.5, client=client
        )

    assert [observation.product_id for observation in observations] == [
        465423434215,
        465467854215,
        465495204215,
    ]
    assert observations[0].observed_at == datetime(
        2018, 4, 11, 10, 9, 45, tzinfo=timezone.utc
    )


def test_find_observation_sequence_is_not_capped_at_ten_results() -> None:
    body = "".join(
        f"2018-04-11 10:{minute:02d}:00+00,2458219.9,535,zr,11,3,"
        f"{1000 + minute},201804114{minute:05d},o\n"
        for minute in range(12)
    )

    with make_client(body) as client:
        observations = find_observation_sequence(
            120.5, -10.25, 2458219.5, 2458220.5, client=client
        )

    assert len(observations) == 12


def test_find_observation_sequence_requires_minimum_frames() -> None:
    two_rows = "".join(UNSORTED_ROWS.splitlines(keepends=True)[:2])

    with make_client(two_rows) as client:
        with pytest.raises(InsufficientFramesError, match="Found 2"):
            find_observation_sequence(
                120.5, -10.25, 2458219.5, 2458220.5, client=client
            )


def test_insufficient_frames_is_a_ztf_service_error() -> None:
    assert issubclass(InsufficientFramesError, ZTFServiceError)


def test_find_observation_sequence_rejects_empty_time_window() -> None:
    with pytest.raises(ValueError, match="start_jd"):
        find_observation_sequence(120.5, -10.25, 2458220.5, 2458220.5)
