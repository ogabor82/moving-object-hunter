import base64
import os
from io import BytesIO

import numpy
import pytest
from astropy.io import fits
from fastapi.testclient import TestClient

from app.api.routes import frames as frames_route
from app.main import app
from app.models.matching import StationaryMatchingConfig
from app.models.observation import Observation
from app.models.tracklet import TrackletBuildConfig
from app.services.astrometry import angular_distance_arcsec
from app.services.catalog_service import (
    load_frame_sources,
    normalize_psf_catalog,
)
from app.services.matching_service import (
    extract_moving_candidates,
    match_stationary_sources,
)
from app.services.tracklet_service import build_tracklets
from app.services.cutout_cache import CutoutCache
from app.services.ztf_service import (
    HARDCODED_DEC_DEGREES,
    HARDCODED_END_JD,
    HARDCODED_RA_DEGREES,
    HARDCODED_START_JD,
    fetch_hardcoded_ztf_observations,
    fetch_psf_catalog,
    fetch_science_image,
    find_observation_sequence,
)
from app.validation.presets import AS022_REPORT, load_blink_presets
from app.validation.runner import ValidationReport


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_ZTF_INTEGRATION") != "1",
        reason="Set RUN_ZTF_INTEGRATION=1 to query the live IRSA service.",
    ),
]


def test_live_irsa_query_and_science_image_retrieval() -> None:
    observations = fetch_hardcoded_ztf_observations()

    assert observations
    assert isinstance(observations[0], Observation)

    payload = fetch_science_image(observations[0])

    assert payload
    with fits.open(BytesIO(payload)) as hdul:
        assert hdul[0].data is not None
        assert len(hdul[0].data.shape) == 2


def test_live_irsa_psf_catalog_retrieval() -> None:
    observations = fetch_hardcoded_ztf_observations()

    catalog = fetch_psf_catalog(observations[0])

    assert len(catalog.rows) > 0
    assert catalog.magnitude_zero_point is not None


def test_live_irsa_full_observation_normalization() -> None:
    observation = fetch_hardcoded_ztf_observations()[0]
    catalog = fetch_psf_catalog(observation)

    result = normalize_psf_catalog(observation, catalog)

    assert result.detections
    assert len(result.detections) + len(result.rejected_rows) == len(
        catalog.rows
    )


def test_live_irsa_observation_sequence() -> None:
    observations = find_observation_sequence(
        HARDCODED_RA_DEGREES,
        HARDCODED_DEC_DEGREES,
        HARDCODED_START_JD,
        HARDCODED_END_JD,
    )

    assert len(observations) >= 3
    times = [observation.observed_at for observation in observations]
    assert times == sorted(times)


def test_live_irsa_multi_frame_source_loading() -> None:
    observations = find_observation_sequence(
        HARDCODED_RA_DEGREES,
        HARDCODED_DEC_DEGREES,
        HARDCODED_START_JD,
        HARDCODED_END_JD,
    )

    frames = load_frame_sources(observations)

    assert len(frames) == len(observations)
    assert all(frame.source_count > 0 for frame in frames)


def test_live_irsa_sequence_to_tracklets_pipeline() -> None:
    # Pipeline smoke test only: the config values are illustrative, not
    # calibrated (calibration belongs to the Validation Set work).
    observations = find_observation_sequence(
        HARDCODED_RA_DEGREES,
        HARDCODED_DEC_DEGREES,
        HARDCODED_START_JD,
        HARDCODED_END_JD,
    )
    frames = load_frame_sources(observations)
    candidates = extract_moving_candidates(
        match_stationary_sources(
            frames, StationaryMatchingConfig(stationary_tolerance_arcsec=1.5)
        )
    )

    result = build_tracklets(
        candidates,
        TrackletBuildConfig(
            max_rate_arcsec_per_min=1.0,
            search_radius_arcsec=2.0,
            max_residual_arcsec=0.5,
        ),
    )

    assert result.diagnostics.frame_count == len(observations)
    assert result.diagnostics.tracklet_count == len(result.tracklets)
    assert all(len(tracklet.detections) >= 3 for tracklet in result.tracklets)


def test_live_observation_search_endpoint() -> None:
    client = TestClient(app)

    response = client.get(
        "/api/observations/search",
        params={
            "ra": HARDCODED_RA_DEGREES,
            "dec": HARDCODED_DEC_DEGREES,
            "radius_deg": 0.05,
            "start_time": "2018-04-11T00:00:00Z",
            "end_time": "2018-04-12T00:00:00Z",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 3
    times = [o["observed_at"] for o in body["observations"]]
    assert times == sorted(times)


def test_live_tracklet_build_endpoint() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/tracklets/build",
        json={"observation_ids": [465423434215, 465467854215, 465495204215]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_counts"] == [13455, 12553, 8678]
    assert body["diagnostics"]["tracklet_count"] == len(body["tracklets"]) > 0
    assert all(t["tracklet_id"].startswith(body["build_id"]) for t in body["tracklets"])


def test_live_blink_frames_show_1995_dh_moving(monkeypatch, tmp_path) -> None:
    """Real ZTF cutouts of the 1995 DH preset: a bright source sits at the
    frozen SkyBoT prediction in every frame, and it moves between frames.
    A second load comes from the cutout cache, identical and without IRSA."""
    preset = next(p for p in load_blink_presets() if p.designation == "48606")
    report = ValidationReport.model_validate_json(AS022_REPORT.read_text())
    target = next(
        t for s in report.snapshots for t in s.targets if t.designation == "48606"
    )
    cache = CutoutCache(tmp_path)  # cold: never a developer's warm cache
    monkeypatch.setitem(
        app.dependency_overrides, frames_route.get_cutout_cache, lambda: cache
    )
    client = TestClient(app)
    positions = []
    cold = []
    for product_id, (ra, dec) in zip(preset.product_ids, target.predicted_positions):
        response = client.get(
            "/api/frames/cutout",
            params={
                "product_id": product_id,
                "ra": preset.center_ra,
                "dec": preset.center_dec,
                "size_arcsec": preset.size_arcsec,
            },
        )
        assert response.status_code == 200, response.json()
        assert response.headers["X-Cutout-Cache"] == "miss"
        cold.append(response)
        body = response.json()
        pixels = numpy.frombuffer(
            base64.b64decode(body["pixels_base64"]), dtype=numpy.uint8
        ).reshape(body["height"], body["width"])
        # North up, east left: offsets from the requested centre in pixels.
        east = (ra - preset.center_ra) * numpy.cos(numpy.radians(dec)) * 3600
        north = (dec - preset.center_dec) * 3600
        column = body["center_x"] - east / body["pixel_scale_arcsec"]
        row = body["center_y"] - north / body["pixel_scale_arcsec"]
        c, r = int(round(column)), int(round(row))
        assert pixels[r - 2 : r + 3, c - 2 : c + 3].max() > numpy.percentile(
            pixels, 95
        )
        positions.append((column, row))

    # Moves north (up) and slightly west (right) by several pixels per frame.
    assert positions[0][1] - positions[2][1] > 20
    assert positions[2][0] > positions[0][0]

    def irsa_down(*args, **kwargs):
        raise AssertionError("warm load must not call IRSA")

    monkeypatch.setattr(frames_route, "fetch_observations", irsa_down)
    monkeypatch.setattr(frames_route, "fetch_science_cutout", irsa_down)
    for response in cold:
        warm = client.get("/api/frames/cutout", params=response.request.url.params)
        assert warm.headers["X-Cutout-Cache"] == "hit"
        assert warm.json() == response.json()


def test_live_overlay_marks_1995_dh_on_every_frame(monkeypatch, tmp_path) -> None:
    """AS-030: the pipeline's 1995 DH tracklet, projected onto the preset's
    real cutouts by /api/frames/project, sits on the bright moving source,
    and moves north like the frozen SkyBoT prediction."""
    preset = next(p for p in load_blink_presets() if p.designation == "48606")
    report = ValidationReport.model_validate_json(AS022_REPORT.read_text())
    target = next(
        t for s in report.snapshots for t in s.targets if t.designation == "48606"
    )
    cache = CutoutCache(tmp_path)
    monkeypatch.setitem(
        app.dependency_overrides, frames_route.get_cutout_cache, lambda: cache
    )
    client = TestClient(app)
    build = client.post(
        "/api/tracklets/build", json={"observation_ids": preset.product_ids}
    )
    assert build.status_code == 200, build.json()
    tracklets = build.json()["tracklets"]
    # The tracklet whose detections lie on the frozen prediction (< 2").
    [dh] = [
        t
        for t in tracklets
        if all(
            angular_distance_arcsec(
                d["detection"]["ra"], d["detection"]["dec"], ra, dec
            )
            < 2.0
            for d, (ra, dec) in zip(t["detections"], target.predicted_positions)
        )
    ]
    assert [d["detection"]["observation_product_id"] for d in dh["detections"]] == (
        preset.product_ids
    )

    shown = []
    for epoch, product_id in enumerate(preset.product_ids):
        params = {
            "product_id": product_id,
            "ra": preset.center_ra,
            "dec": preset.center_dec,
            "size_arcsec": preset.size_arcsec,
        }
        body = client.get("/api/frames/cutout", params=params).json()
        projected = client.post(
            "/api/frames/project",
            json={
                **params,
                "positions": [
                    {"ra": d["detection"]["ra"], "dec": d["detection"]["dec"]}
                    for d in dh["detections"]
                ],
            },
        )
        assert projected.status_code == 200
        assert projected.headers["X-Cutout-Cache"] == "hit"
        point = projected.json()["points"][epoch]
        pixels = numpy.frombuffer(
            base64.b64decode(body["pixels_base64"]), dtype=numpy.uint8
        ).reshape(body["height"], body["width"])
        c, r = int(round(point["x"])), int(round(point["y"]))
        # Same criterion as the AS-029 blink test (the source saturates).
        assert pixels[r - 1 : r + 2, c - 1 : c + 2].max() > numpy.percentile(
            pixels, 95
        )
        shown.append((point["x"], point["y"]))

    # North up: y decreases; the fitted position angle agrees (~347 deg).
    assert shown[0][1] - shown[2][1] > 20
    assert dh["position_angle_deg"] == pytest.approx(
        target.predicted_position_angle_deg, abs=2.0
    )
