from datetime import datetime, timezone
from io import BytesIO

import httpx
import numpy
import pytest
from astropy.io import fits
from astropy.table import Table

from app.models.observation import Observation
from app.services.ztf_service import (
    PSF_CATALOG_COLUMNS,
    ZTFServiceError,
    build_psf_catalog_url,
    fetch_psf_catalog,
    read_psf_catalog,
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
    "ztf_20180411467847_000535_zr_c11_o_q3_psfcat.fits"
)
MAGZP = 26.3084802135098


def make_psf_catalog_payload(
    rows: int = 2,
    magzp: float | None = MAGZP,
    drop_column: str | None = None,
    extension_name: str = "PSF_CATALOG",
) -> bytes:
    table = Table(
        {
            "sourceid": numpy.arange(rows, dtype=numpy.int32),
            "xpos": numpy.linspace(898.747, 1200.5, rows).astype(numpy.float32),
            "ypos": numpy.linspace(1.257, 40.0, rows).astype(numpy.float32),
            "ra": numpy.linspace(255.7590124, 255.8, rows),
            "dec": numpy.linspace(12.7174256, 12.72, rows),
            "flux": numpy.full(rows, 187.13213, dtype=numpy.float32),
            "sigflux": numpy.full(rows, 55.825806, dtype=numpy.float32),
            "mag": numpy.full(rows, -5.68, dtype=numpy.float32),
            "sigmag": numpy.full(rows, 0.324, dtype=numpy.float32),
            "snr": numpy.full(rows, 3.35, dtype=numpy.float32),
            "chi": numpy.full(rows, 0.877, dtype=numpy.float32),
            "sharp": numpy.full(rows, 0.083, dtype=numpy.float32),
            "flags": numpy.zeros(rows, dtype=numpy.int16),
        }
    )
    if drop_column is not None:
        table.remove_column(drop_column)

    primary = fits.PrimaryHDU()
    if magzp is not None:
        primary.header["MAGZP"] = magzp
    catalog = fits.table_to_hdu(table)
    catalog.name = extension_name

    buffer = BytesIO()
    fits.HDUList([primary, catalog]).writeto(buffer)
    return buffer.getvalue()


def test_build_psf_catalog_url() -> None:
    assert build_psf_catalog_url(OBSERVATION) == EXPECTED_URL


def test_fetch_psf_catalog_returns_readable_rows() -> None:
    payload = make_psf_catalog_payload(rows=3)

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == EXPECTED_URL
        return httpx.Response(200, content=payload)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        catalog = fetch_psf_catalog(OBSERVATION, client)

    assert len(catalog.rows) == 3
    assert catalog.magnitude_zero_point == pytest.approx(MAGZP)
    first = catalog.rows[0]
    assert set(first) == set(PSF_CATALOG_COLUMNS)
    assert first["sourceid"] == 0
    assert first["ra"] == pytest.approx(255.7590124)
    assert isinstance(first["flags"], int)
    assert isinstance(first["mag"], float)


def test_read_psf_catalog_allows_missing_zero_point() -> None:
    catalog = read_psf_catalog(make_psf_catalog_payload(magzp=None))

    assert catalog.magnitude_zero_point is None


def test_read_psf_catalog_rejects_missing_extension() -> None:
    payload = make_psf_catalog_payload(extension_name="OTHER")

    with pytest.raises(ZTFServiceError, match="no PSF_CATALOG extension"):
        read_psf_catalog(payload)


def test_read_psf_catalog_rejects_missing_column() -> None:
    payload = make_psf_catalog_payload(drop_column="snr")

    with pytest.raises(ZTFServiceError, match="missing column.*snr"):
        read_psf_catalog(payload)


def test_fetch_psf_catalog_handles_http_error() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(404, text="Not found")
    )

    with httpx.Client(transport=transport) as client:
        with pytest.raises(ZTFServiceError, match="PSF catalog.*HTTP 404"):
            fetch_psf_catalog(OBSERVATION, client)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"", "response was empty"),
        (b"not a FITS file", "not a FITS file"),
    ],
)
def test_fetch_psf_catalog_rejects_invalid_payload(
    payload: bytes,
    message: str,
) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=payload)
    )

    with httpx.Client(transport=transport) as client:
        with pytest.raises(ZTFServiceError, match=message):
            fetch_psf_catalog(OBSERVATION, client)
