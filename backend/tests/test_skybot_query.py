import httpx
import pytest

from app.services.skybot_service import (
    SKYBOT_CONESEARCH_URL,
    SkyBoTServiceError,
    query_skybot_cone,
)


# Trimmed real SkyBoT JSON rows (POC field, JD 2458219.9236111, I41).
SKYBOT_ROWS = [
    {
        "Num": 285862,
        "Name": "2001 HM48",
        "RA (hms)": "17 01 47.8476",
        "DEC (dms)": "+12 08 48.528",
        "Class": "MB>Outer",
        "VMag (mag)": 20,
        "Err (arcsec)": 0.059,
        "d (arcsec)": 667.523,
        "dRA (arcsec/h)": 6.0568,
        "dDEC (arcsec/h)": 33.7814,
        "dg (ua)": 1.89450407965,
        "dh (ua)": 2.5576201268,
    },
    {
        "Name": "2018 LN15",
        "RA (hms)": "17 03 14.7298",
        "DEC (dms)": "+12 07 58.663",
        "Class": "Mars-Crosser",
        "VMag (mag)": 22.5,
        "Err (arcsec)": 0.197,
        "d (arcsec)": 987.794,
        "dRA (arcsec/h)": -0.2695,
        "dDEC (arcsec/h)": 22.422,
        "dg (ua)": 1.3904809524,
        "dh (ua)": 2.08650965053,
    },
]
QUERY = {
    "ra_degrees": 255.577,
    "dec_degrees": 12.284,
    "radius_degrees": 0.65,
    "epoch_jd_utc": 2458219.9236111,
}


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.skybot_service.time.sleep", lambda _: None)


def query_with(handler) -> list:
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        return query_skybot_cone(**QUERY, client=client)


def test_query_sends_documented_parameters_and_returns_rows() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith(SKYBOT_CONESEARCH_URL)
        params = request.url.params
        assert params["-ep"] == "2458219.92361110"
        assert float(params["-ra"]) == pytest.approx(255.577)
        assert float(params["-dec"]) == pytest.approx(12.284)
        assert float(params["-rd"]) == pytest.approx(0.65)
        assert params["-mime"] == "json"
        assert params["-observer"] == "I41"
        assert params["-filter"] == "0"
        assert params["-refsys"] == "EQJ2000"
        return httpx.Response(200, json=SKYBOT_ROWS)

    assert query_with(handler) == SKYBOT_ROWS


def test_observer_can_be_overridden() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["-observer"] == "500"
        return httpx.Response(200, json=[])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert query_skybot_cone(**QUERY, observer="500", client=client) == []


def test_http_204_means_no_known_objects() -> None:
    assert query_with(lambda request: httpx.Response(204)) == []


def test_http_error_is_a_service_error_not_an_empty_result() -> None:
    body = {"flag": -1, "status": 400, "message": "Bad request: epoch"}

    with pytest.raises(SkyBoTServiceError, match="HTTP 400: Bad request"):
        query_with(lambda request: httpx.Response(400, json=body))


def test_error_flag_with_http_200_is_a_service_error() -> None:
    body = {"flag": -1, "status": 200, "message": "computeEphemeris: SIGBUS"}

    with pytest.raises(SkyBoTServiceError, match="SIGBUS"):
        query_with(lambda request: httpx.Response(200, json=body))


def test_timeout_is_a_service_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(SkyBoTServiceError, match="timed out"):
        query_with(handler)


def test_connection_error_is_a_service_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("unreachable", request=request)

    with pytest.raises(SkyBoTServiceError, match="failed"):
        query_with(handler)


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="<html>maintenance</html>"),
        httpx.Response(200, json={"unexpected": True}),
        httpx.Response(200, json=[1, 2]),
    ],
)
def test_unexpected_payload_is_a_service_error(response: httpx.Response) -> None:
    with pytest.raises(SkyBoTServiceError):
        query_with(lambda request: response)


@pytest.mark.parametrize(
    "override",
    [
        {"ra_degrees": 360.0},
        {"ra_degrees": -1.0},
        {"dec_degrees": 91.0},
        {"radius_degrees": 0.0},
        {"radius_degrees": 10.5},
        {"epoch_jd_utc": 2400000.0},
    ],
)
def test_invalid_query_is_rejected_before_calling_skybot(override: dict) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("SkyBoT must not be called")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError):
            query_skybot_cone(**{**QUERY, **override}, client=client)


def counting_handler(responses: list):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return responses[min(len(calls), len(responses)) - 1]

    return handler, calls


def test_transient_error_flag_is_retried_then_succeeds() -> None:
    crash = httpx.Response(200, json={"flag": -1, "message": "SIGBUS"})
    handler, calls = counting_handler(
        [crash, httpx.Response(200, json=SKYBOT_ROWS)]
    )

    assert query_with(handler) == SKYBOT_ROWS
    assert len(calls) == 2


def test_server_error_is_retried_up_to_max_attempts() -> None:
    handler, calls = counting_handler([httpx.Response(503, text="down")])

    with pytest.raises(SkyBoTServiceError, match="HTTP 503") as error:
        query_with(handler)
    assert len(calls) == 3
    assert type(error.value) is SkyBoTServiceError
    assert "after 3 attempt(s)" in str(error.value)


def test_bad_request_is_not_retried() -> None:
    handler, calls = counting_handler(
        [httpx.Response(400, json={"flag": -1, "message": "Bad request"})]
    )

    with pytest.raises(SkyBoTServiceError, match="HTTP 400"):
        query_with(handler)
    assert len(calls) == 1


def test_max_attempts_must_be_positive() -> None:
    with pytest.raises(ValueError, match="max_attempts"):
        query_skybot_cone(**QUERY, max_attempts=0)
