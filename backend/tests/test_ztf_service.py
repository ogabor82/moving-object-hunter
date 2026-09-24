import httpx
import pytest

from app.services.ztf_service import (
    HARDCODED_DEC_DEGREES,
    HARDCODED_END_JD,
    HARDCODED_RA_DEGREES,
    HARDCODED_START_JD,
    ZTFServiceError,
    fetch_hardcoded_ztf_metadata,
)


CSV_HEADER = "obsdate,obsjd,field,filtercode,ccdid,qid,pid,filefracday,imgtypecode"


def test_fetch_hardcoded_ztf_metadata_returns_csv_rows() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["POS"] == (
            f"{HARDCODED_RA_DEGREES},{HARDCODED_DEC_DEGREES}"
        )
        assert request.url.params["WHERE"] == (
            f"obsjd >= {HARDCODED_START_JD} AND obsjd < {HARDCODED_END_JD}"
        )
        return httpx.Response(
            200,
            text=(
                f"{CSV_HEADER}\n"
                "2018-04-11 11:13:43+00,2458219.967858800,535,zr,11,3,"
                "465467854215,20180411467847,o\n"
            ),
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        rows = fetch_hardcoded_ztf_metadata(client)

    assert rows == [
        {
            "obsdate": "2018-04-11 11:13:43+00",
            "obsjd": "2458219.967858800",
            "field": "535",
            "filtercode": "zr",
            "ccdid": "11",
            "qid": "3",
            "pid": "465467854215",
            "filefracday": "20180411467847",
            "imgtypecode": "o",
        }
    ]


def test_fetch_hardcoded_ztf_metadata_handles_empty_result() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text=f"{CSV_HEADER}\n")
    )

    with httpx.Client(transport=transport) as client:
        rows = fetch_hardcoded_ztf_metadata(client)

    assert rows == []


def test_fetch_hardcoded_ztf_metadata_handles_http_error() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(503, text="Service unavailable")
    )

    with httpx.Client(transport=transport) as client:
        with pytest.raises(ZTFServiceError, match="HTTP 503"):
            fetch_hardcoded_ztf_metadata(client)
