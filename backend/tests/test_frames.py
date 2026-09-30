import base64
from datetime import datetime, timezone
from io import BytesIO

import httpx
import numpy
import pytest
from astropy.io import fits
from astropy.wcs import WCS
from fastapi.testclient import TestClient

from app.api.routes import frames as route
from app.main import app
from app.models.observation import Observation
from app.services.image_service import ImageRenderError, render_cutout
from app.services.ztf_service import (
    ObservationNotFoundError,
    ZTFServiceError,
    fetch_science_cutout,
)
from app.validation.presets import load_blink_presets


SCALE = 1.0 / 3600  # 1 arcsec per pixel
CENTER = (120.0, 10.0)
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


def make_cutout(cd: list[list[float]], size: int = 21, nan: bool = False) -> bytes:
    """Synthetic cutout: flat sky, one bright star 5" north of centre."""
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = list(CENTER)
    wcs.wcs.crpix = [(size + 1) / 2, (size + 1) / 2]
    wcs.wcs.cd = numpy.array(cd)
    rng = numpy.random.default_rng(1)
    data = rng.normal(100.0, 5.0, (size, size))
    x, y = wcs.world_to_pixel_values(CENTER[0], CENTER[1] + 5 * SCALE)
    data[int(round(float(y))), int(round(float(x)))] = 5000.0
    if nan:
        data[0, 0] = numpy.nan
    buffer = BytesIO()
    fits.PrimaryHDU(data=data, header=wcs.to_header()).writeto(buffer)
    return buffer.getvalue()


def image(frame) -> numpy.ndarray:
    return numpy.frombuffer(frame.pixels, dtype=numpy.uint8).reshape(
        frame.height, frame.width
    )


ORIENTATIONS = {
    # FITS CD matrices (d(RA,Dec)/d(x,y)) for the four axis-aligned cases.
    "east_left_north_up_in_fits": [[-SCALE, 0.0], [0.0, SCALE]],
    "east_right": [[SCALE, 0.0], [0.0, SCALE]],
    "north_down_in_fits": [[-SCALE, 0.0], [0.0, -SCALE]],
    "transposed": [[0.0, -SCALE], [SCALE, 0.0]],
}


@pytest.mark.parametrize("cd", ORIENTATIONS.values(), ids=ORIENTATIONS.keys())
def test_render_puts_north_up_and_east_left(cd) -> None:
    frame = render_cutout(make_cutout(cd), *CENTER)
    pixels = image(frame)

    # The star is 5" north of centre: straight above it on screen.
    row, column = numpy.unravel_index(pixels.argmax(), pixels.shape)
    assert (column, row) == pytest.approx(
        (frame.center_x, frame.center_y - 5), abs=0.6
    )
    # A point 3" east of centre is 3 pixels to the left.
    east_ra = CENTER[0] + 3 * SCALE / numpy.cos(numpy.radians(CENTER[1]))
    east = frame.world_to_display(east_ra, CENTER[1])
    assert east == pytest.approx((frame.center_x - 3, frame.center_y), abs=0.05)
    assert frame.rotation_deg == pytest.approx(0.0, abs=0.01)
    assert frame.pixel_scale_arcsec == pytest.approx(1.0, rel=1e-6)


def transform_of(name: str) -> tuple[str, ...]:
    return render_cutout(make_cutout(ORIENTATIONS[name]), *CENTER).transform


def test_render_reports_applied_transform() -> None:
    assert transform_of("east_left_north_up_in_fits") == ("flip_rows",)
    assert transform_of("north_down_in_fits") == ()
    assert "transpose" in transform_of("transposed")


def test_zscale_linear_stretch_and_nan_handling() -> None:
    frame = render_cutout(
        make_cutout(ORIENTATIONS["north_down_in_fits"], nan=True), *CENTER
    )
    pixels = image(frame)

    assert frame.vmin < 100.0 < frame.vmax
    assert pixels.max() == 255  # the star saturates the display range
    assert 60 < numpy.median(pixels) < 200  # sky sits mid-range
    assert frame.transform == ()  # FITS pixel (0, 0) stays at (0, 0)
    assert pixels[0, 0] == 0  # the NaN pixel


def test_render_rejects_bad_input() -> None:
    with pytest.raises(ImageRenderError):
        render_cutout(b"not a fits file", *CENTER)
    buffer = BytesIO()
    fits.PrimaryHDU(data=numpy.full((5, 5), numpy.nan)).writeto(buffer)
    with pytest.raises(ImageRenderError):
        render_cutout(buffer.getvalue(), *CENTER)


def test_fetch_science_cutout_uses_ibe_cutout_parameters() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("_sciimg.fits")
        assert request.url.params["center"] == "255.5,12.3deg"
        assert request.url.params["size"] == "90.0arcsec"
        assert request.url.params["gzip"] == "false"
        return httpx.Response(200, content=make_cutout(ORIENTATIONS["transposed"]))

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        payload = fetch_science_cutout(OBSERVATION, 255.5, 12.3, 90.0, client)

    assert payload.startswith(b"SIMPLE  =")


def test_fetch_science_cutout_reports_http_error() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(500))

    with httpx.Client(transport=transport) as client:
        with pytest.raises(ZTFServiceError, match="HTTP 500"):
            fetch_science_cutout(OBSERVATION, 255.5, 12.3, 90.0, client)


def test_presets_come_from_frozen_validation_data() -> None:
    presets = load_blink_presets()

    assert len(presets) == 23
    assert {p.role for p in presets} == {"control", "primary"}
    dh = next(p for p in presets if p.designation == "48606")
    assert dh.product_ids == [465423434215, 465467854215, 465495204215]
    assert dh.size_arcsec >= 60
    assert dh.center_dec == pytest.approx(12.678, abs=0.01)


client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_observation_cache():
    route._observation.cache_clear()
    yield
    route._observation.cache_clear()


PARAMS = {"product_id": 465423434215, "ra": CENTER[0], "dec": CENTER[1]}


def test_cutout_endpoint_returns_display_image(monkeypatch) -> None:
    monkeypatch.setattr(route, "fetch_observations", lambda ids: [OBSERVATION])
    monkeypatch.setattr(
        route,
        "fetch_science_cutout",
        lambda observation, ra, dec, size: make_cutout(
            ORIENTATIONS["east_left_north_up_in_fits"]
        ),
    )

    response = client.get("/api/frames/cutout", params=PARAMS)

    assert response.status_code == 200
    body = response.json()
    assert body["orientation"] == "north_up_east_left"
    assert body["stretch"]["method"] == "zscale_linear"
    assert body["transform"] == ["flip_rows"]
    assert body["size_arcsec"] == 90.0
    pixels = base64.b64decode(body["pixels_base64"])
    assert len(pixels) == body["width"] * body["height"] == 21 * 21
    assert body["observation"]["product_id"] == 465423434215


@pytest.mark.parametrize(
    ("target", "exception", "status", "code"),
    [
        (
            "fetch_observations",
            ObservationNotFoundError("no pid"),
            404,
            "NO_ZTF_OBSERVATIONS",
        ),
        (
            "fetch_observations",
            ZTFServiceError("HTTP 504"),
            502,
            "ZTF_METADATA_FAILED",
        ),
        (
            "fetch_science_cutout",
            ZTFServiceError("HTTP 500"),
            502,
            "IMAGE_DOWNLOAD_FAILED",
        ),
    ],
)
def test_cutout_endpoint_errors(monkeypatch, target, exception, status, code) -> None:
    monkeypatch.setattr(route, "fetch_observations", lambda ids: [OBSERVATION])

    def failing(*args, **kwargs):
        raise exception

    monkeypatch.setattr(route, target, failing)

    response = client.get("/api/frames/cutout", params=PARAMS)

    assert response.status_code == status
    assert response.json()["error"]["code"] == code


@pytest.mark.parametrize(
    "override", [{"ra": 400}, {"dec": -100}, {"size_arcsec": 0}, {"size_arcsec": 301}]
)
def test_cutout_endpoint_validates_input(override) -> None:
    response = client.get("/api/frames/cutout", params={**PARAMS, **override})

    assert response.status_code == 422


def test_presets_endpoint() -> None:
    response = client.get("/api/frames/presets")

    assert response.status_code == 200
    assert any(p["designation"] == "48606" for p in response.json())
