import os
from io import BytesIO

import pytest
from astropy.io import fits

from app.models.matching import StationaryMatchingConfig
from app.models.observation import Observation
from app.models.tracklet import TrackletBuildConfig
from app.services.catalog_service import (
    load_frame_sources,
    normalize_psf_catalog,
)
from app.services.matching_service import (
    extract_moving_candidates,
    match_stationary_sources,
)
from app.services.tracklet_service import build_tracklets
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
