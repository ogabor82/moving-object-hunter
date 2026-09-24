from datetime import datetime, timezone
from io import BytesIO

import httpx
import numpy
import pytest
from astropy.io import fits

from app.models.observation import Observation
from app.services.ztf_service import (
    ZTFServiceError,
    build_science_image_url,
    fetch_science_image,
)


OBSERVATION = Observation(
    product_id=465467854215,
    observed_at=datetime(2018, 4, 11, 11, 13, 43, tzinfo=timezone.utc),
    field=535,
    filter_code="zr",
    ccd_id=11,
    quadrant_id=3,
    file_frac_day="20180411467847",
)
EXPECTED_URL = (
    "https://irsa.ipac.caltech.edu/ibe/data/ztf/products/sci/"
    "2018/0411/467847/"
    "ztf_20180411467847_000535_zr_c11_o_q3_sciimg.fits"
)


def make_fits_payload() -> bytes:
    buffer = BytesIO()
    fits.PrimaryHDU(numpy.zeros((2, 3), dtype=numpy.float32)).writeto(buffer)
    return buffer.getvalue()


def test_build_science_image_url() -> None:
    assert build_science_image_url(OBSERVATION) == EXPECTED_URL


def test_fetch_science_image_returns_valid_fits_bytes() -> None:
    payload = make_fits_payload()

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == EXPECTED_URL
        return httpx.Response(200, content=payload)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = fetch_science_image(OBSERVATION, client)

    assert result == payload
    with fits.open(BytesIO(result)) as hdul:
        assert hdul[0].data.shape == (2, 3)


def test_fetch_science_image_handles_http_error() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(404, text="Not found")
    )

    with httpx.Client(transport=transport) as client:
        with pytest.raises(ZTFServiceError, match="HTTP 404"):
            fetch_science_image(OBSERVATION, client)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"", "response was empty"),
        (b"not a FITS file", "not a FITS file"),
    ],
)
def test_fetch_science_image_rejects_invalid_payload(
    payload: bytes,
    message: str,
) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=payload)
    )

    with httpx.Client(transport=transport) as client:
        with pytest.raises(ZTFServiceError, match=message):
            fetch_science_image(OBSERVATION, client)
