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
from app.services.cutout_cache import CutoutCache
from app.services.image_service import ImageRenderError, render_cutout
from app.services.ztf_service import (
    ObservationNotFoundError,
    ZTFServiceError,
    fetch_science_cutout,
)
from app.validation.presets import load_blink_presets, load_frozen_observations


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
# A frame outside the frozen validation data: needs an IRSA metadata lookup.
LIVE_OBSERVATION = OBSERVATION.model_copy(update={"product_id": 123456789})


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


def test_frozen_observations_cover_every_preset_frame() -> None:
    frozen = load_frozen_observations()

    assert {pid for p in load_blink_presets() for pid in p.product_ids} <= set(frozen)
    assert frozen[OBSERVATION.product_id] == OBSERVATION


client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_caches(tmp_path):
    route._irsa_observation.cache_clear()
    cache = CutoutCache(tmp_path / "cutouts")
    app.dependency_overrides[route.get_cutout_cache] = lambda: cache
    yield cache
    app.dependency_overrides.pop(route.get_cutout_cache, None)
    route._irsa_observation.cache_clear()


PARAMS = {"product_id": LIVE_OBSERVATION.product_id, "ra": CENTER[0], "dec": CENTER[1]}
FROZEN_PARAMS = {**PARAMS, "product_id": OBSERVATION.product_id}
CUTOUT = make_cutout(ORIENTATIONS["east_left_north_up_in_fits"])


class Irsa:
    """Stand-in for the two IRSA calls of the route, counting requests."""

    def __init__(self, monkeypatch, metadata=None, cutout=None) -> None:
        self.metadata_calls = 0
        self.cutout_calls = 0
        self.metadata = metadata
        self.cutout = cutout
        monkeypatch.setattr(route, "fetch_observations", self.fetch_observations)
        monkeypatch.setattr(route, "fetch_science_cutout", self.fetch_science_cutout)

    def fetch_observations(self, ids):
        self.metadata_calls += 1
        if isinstance(self.metadata, Exception):
            raise self.metadata
        return [LIVE_OBSERVATION.model_copy(update={"product_id": ids[0]})]

    def fetch_science_cutout(self, observation, ra, dec, size):
        self.cutout_calls += 1
        if isinstance(self.cutout, Exception):
            raise self.cutout
        return self.cutout if self.cutout is not None else CUTOUT

    def outage(self) -> None:
        self.metadata = ZTFServiceError("IRSA ZTF metadata request failed: timeout")
        self.cutout = ZTFServiceError("ZTF science image cutout request failed")

    @property
    def calls(self) -> int:
        return self.metadata_calls + self.cutout_calls


def test_cutout_endpoint_returns_display_image(monkeypatch) -> None:
    Irsa(monkeypatch)

    response = client.get("/api/frames/cutout", params=PARAMS)

    assert response.status_code == 200
    body = response.json()
    assert body["orientation"] == "north_up_east_left"
    assert body["stretch"]["method"] == "zscale_linear"
    assert body["transform"] == ["flip_rows"]
    assert body["size_arcsec"] == 90.0
    pixels = base64.b64decode(body["pixels_base64"])
    assert len(pixels) == body["width"] * body["height"] == 21 * 21
    assert body["observation"]["product_id"] == LIVE_OBSERVATION.product_id


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
    Irsa(monkeypatch, **{"metadata" if target == "fetch_observations" else "cutout": exception})

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


def test_frozen_frame_needs_no_metadata_lookup(monkeypatch) -> None:
    irsa = Irsa(monkeypatch, metadata=ZTFServiceError("HTTP 504"))

    response = client.get("/api/frames/cutout", params=FROZEN_PARAMS)

    assert response.status_code == 200
    assert irsa.metadata_calls == 0
    assert irsa.cutout_calls == 1
    assert response.json()["observation"] == OBSERVATION.model_dump(mode="json")


def test_live_frame_metadata_is_looked_up_once(monkeypatch) -> None:
    irsa = Irsa(monkeypatch)

    for size in (60, 90):
        client.get("/api/frames/cutout", params={**PARAMS, "size_arcsec": size})

    assert irsa.metadata_calls == 1
    assert irsa.cutout_calls == 2


@pytest.mark.parametrize("params", [PARAMS, FROZEN_PARAMS], ids=["live", "frozen"])
def test_cache_hit_needs_no_irsa_and_matches_miss(monkeypatch, params) -> None:
    irsa = Irsa(monkeypatch)

    cold = client.get("/api/frames/cutout", params=params)
    calls_after_cold = irsa.calls
    irsa.outage()
    warm = client.get("/api/frames/cutout", params=params)

    assert cold.status_code == warm.status_code == 200
    assert cold.headers["X-Cutout-Cache"] == "miss"
    assert warm.headers["X-Cutout-Cache"] == "hit"
    assert irsa.cutout_calls == 1
    assert irsa.calls == calls_after_cold  # no IRSA request on the hit
    assert warm.json() == cold.json()  # identical FITS → display result


def test_cache_key_covers_every_cutout_parameter(monkeypatch) -> None:
    irsa = Irsa(monkeypatch)
    variants = [
        PARAMS,
        FROZEN_PARAMS,
        {**PARAMS, "ra": CENTER[0] + 1e-6},
        {**PARAMS, "dec": CENTER[1] + 1e-6},
        {**PARAMS, "size_arcsec": 60},
    ]

    for params in variants:
        response = client.get("/api/frames/cutout", params=params)
        assert response.headers["X-Cutout-Cache"] == "miss"
    # Same values, different spelling: same cutout.
    same = client.get(
        "/api/frames/cutout",
        params={**PARAMS, "ra": "120.000", "dec": "1e1", "size_arcsec": "90"},
    )

    assert irsa.cutout_calls == len(variants)
    assert same.headers["X-Cutout-Cache"] == "hit"


@pytest.mark.parametrize("params", [PARAMS, FROZEN_PARAMS], ids=["live", "frozen"])
def test_cache_miss_during_outage_is_an_explicit_error(monkeypatch, params) -> None:
    irsa = Irsa(monkeypatch)
    irsa.outage()

    response = client.get("/api/frames/cutout", params=params)

    assert response.status_code == 502
    expected = "ZTF_METADATA_FAILED" if params is PARAMS else "IMAGE_DOWNLOAD_FAILED"
    assert response.json()["error"]["code"] == expected
    # Nothing was cached: the next request goes to IRSA again.
    irsa.metadata = irsa.cutout = None
    retry = client.get("/api/frames/cutout", params=params)
    assert retry.headers["X-Cutout-Cache"] == "miss"


def test_unrenderable_cutout_is_not_cached(monkeypatch) -> None:
    irsa = Irsa(monkeypatch, cutout=b"SIMPLE  = T but not a real FITS file")

    first = client.get("/api/frames/cutout", params=PARAMS)
    irsa.cutout = None
    second = client.get("/api/frames/cutout", params=PARAMS)

    assert first.status_code == 502
    assert first.json()["error"]["code"] == "IMAGE_DOWNLOAD_FAILED"
    assert second.headers["X-Cutout-Cache"] == "miss"
    assert irsa.cutout_calls == 2


def test_unrenderable_cache_entry_is_refetched(monkeypatch, isolated_caches) -> None:
    irsa = Irsa(monkeypatch)
    isolated_caches.put(
        LIVE_OBSERVATION, CENTER[0], CENTER[1], 90.0, b"SIMPLE  = T corrupted"
    )

    response = client.get("/api/frames/cutout", params=PARAMS)

    assert response.status_code == 200
    assert response.headers["X-Cutout-Cache"] == "miss"
    assert irsa.cutout_calls == 1
    cached = isolated_caches.get(LIVE_OBSERVATION.product_id, *CENTER, 90.0)
    assert cached is not None and cached.payload == CUTOUT


# AS-030 overlay: sky positions → display pixels of the shown cutout.

STAR = (CENTER[0], CENTER[1] + 5 * SCALE)  # the synthetic star, 5" north


def rotated_cd(degrees: float) -> list[list[float]]:
    """East-left/north-up in FITS, rotated by a few degrees (like ZTF)."""
    c, s = numpy.cos(numpy.radians(degrees)), numpy.sin(numpy.radians(degrees))
    return (numpy.array([[-SCALE, 0.0], [0.0, SCALE]]) @ [[c, -s], [s, c]]).tolist()


PROJECTION_CASES = {**ORIENTATIONS, "rotated_1.4deg": rotated_cd(1.4)}


@pytest.mark.parametrize("cd", PROJECTION_CASES.values(), ids=PROJECTION_CASES.keys())
def test_projection_lands_on_the_displayed_source(cd) -> None:
    frame = render_cutout(make_cutout(cd), *CENTER)
    pixels = image(frame)
    row, column = numpy.unravel_index(pixels.argmax(), pixels.shape)

    columns, rows = frame.world_to_display_many([STAR[0], CENTER[0]], [STAR[1], CENTER[1]])

    # The star's sky position falls on its brightest display pixel ...
    assert (columns[0], rows[0]) == pytest.approx((column, row), abs=0.6)
    # ... and the cutout centre on the reported alignment centre.
    assert (columns[1], rows[1]) == pytest.approx(
        (frame.center_x, frame.center_y), abs=1e-6
    )
    assert frame.world_to_display(*STAR) == pytest.approx(
        (columns[0], rows[0]), abs=1e-9
    )


def test_projection_follows_north_up_east_left() -> None:
    frame = render_cutout(make_cutout(ORIENTATIONS["transposed"], size=41), *CENTER)
    east_ra = CENTER[0] + 4 * SCALE / numpy.cos(numpy.radians(CENTER[1]))
    columns, rows = frame.world_to_display_many(
        [CENTER[0], east_ra], [CENTER[1] + 4 * SCALE, CENTER[1]]
    )

    assert (columns[0], rows[0]) == pytest.approx(
        (frame.center_x, frame.center_y - 4), abs=0.05
    )  # north: up
    assert (columns[1], rows[1]) == pytest.approx(
        (frame.center_x - 4, frame.center_y), abs=0.05
    )  # east: left


def project_body(params, positions):
    return {
        **params,
        "size_arcsec": 90.0,
        "positions": [{"ra": ra, "dec": dec} for ra, dec in positions],
    }


@pytest.mark.parametrize("name", ORIENTATIONS)
def test_project_endpoint_matches_cutout_endpoint(monkeypatch, name) -> None:
    irsa = Irsa(monkeypatch, cutout=make_cutout(ORIENTATIONS[name]))
    cutout_body = client.get("/api/frames/cutout", params=FROZEN_PARAMS).json()
    irsa.outage()

    response = client.post(
        "/api/frames/project", json=project_body(FROZEN_PARAMS, [STAR, CENTER])
    )

    assert response.status_code == 200
    assert response.headers["X-Cutout-Cache"] == "hit"
    assert irsa.cutout_calls == 1  # no second download for the overlay
    body = response.json()
    pixels = numpy.frombuffer(
        base64.b64decode(cutout_body["pixels_base64"]), dtype=numpy.uint8
    ).reshape(cutout_body["height"], cutout_body["width"])
    row, column = numpy.unravel_index(pixels.argmax(), pixels.shape)
    star, centre = body["points"]
    assert (star["x"], star["y"]) == pytest.approx((column, row), abs=0.6)
    assert (centre["x"], centre["y"]) == pytest.approx(
        (cutout_body["center_x"], cutout_body["center_y"])
    )
    for key in ("width", "height", "center_x", "center_y"):
        assert body[key] == cutout_body[key]


def test_project_endpoint_uncached_during_outage_is_an_error(monkeypatch) -> None:
    Irsa(monkeypatch).outage()

    response = client.post(
        "/api/frames/project", json=project_body(PARAMS, [STAR])
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "ZTF_METADATA_FAILED"


@pytest.mark.parametrize(
    "override",
    [{"positions": [{"ra": 360.0, "dec": 0.0}]}, {"size_arcsec": 301}, {"dec": 91}],
)
def test_project_endpoint_validates_input(override) -> None:
    body = {**project_body(PARAMS, [STAR]), **override}

    assert client.post("/api/frames/project", json=body).status_code == 422


def test_project_endpoint_accepts_no_positions(monkeypatch) -> None:
    Irsa(monkeypatch)

    response = client.post("/api/frames/project", json=project_body(PARAMS, []))

    assert response.status_code == 200
    assert response.json()["points"] == []
