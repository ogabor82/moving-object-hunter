import os

import pytest

from app.models.identification import IdentificationConfig, IdentificationStatus
from app.models.matching import StationaryMatchingConfig
from app.models.tracklet import TrackletBuildConfig
from app.services.catalog_service import load_frame_sources
from app.services.identification_service import identify_tracklets
from app.services.matching_service import (
    extract_moving_candidates,
    match_stationary_sources,
)
from app.services.skybot_service import query_known_objects, query_skybot_cone
from app.services.tracklet_service import build_tracklets
from app.services.ztf_service import (
    HARDCODED_DEC_DEGREES,
    HARDCODED_END_JD,
    HARDCODED_RA_DEGREES,
    HARDCODED_START_JD,
    find_observation_sequence,
)


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_SKYBOT_INTEGRATION") != "1",
        reason="Set RUN_SKYBOT_INTEGRATION=1 to query the live SkyBoT service.",
    ),
]

# POC ZTF field (535/c11/q3) at the mid-exposure of the 2018-04-11 10:09:45
# UTC frame, seen from ZTF (I41).
POC_FIELD = {
    "ra_degrees": 255.577,
    "dec_degrees": 12.284,
    "radius_degrees": 0.65,
    "epoch_jd_utc": 2458219.9234375 + 15 / 86400,
}


def test_live_skybot_cone_search_returns_known_objects() -> None:
    rows = query_skybot_cone(**POC_FIELD)

    assert rows
    assert "2001 HM48" in {row["Name"] for row in rows}


def test_live_skybot_rows_normalize_without_rejections() -> None:
    field = query_known_objects(**POC_FIELD)

    assert field.objects
    assert field.rejected_rows == []
    assert "285862" in {ephemeris.designation for ephemeris in field.objects}


@pytest.mark.skipif(
    os.getenv("RUN_ZTF_INTEGRATION") != "1",
    reason="Also set RUN_ZTF_INTEGRATION=1 to query the live IRSA service.",
)
def test_live_pipeline_identifies_known_asteroid_1995_dh() -> None:
    # Illustrative, uncalibrated config values (calibration is AS-022+).
    observations = find_observation_sequence(
        HARDCODED_RA_DEGREES,
        HARDCODED_DEC_DEGREES,
        HARDCODED_START_JD,
        HARDCODED_END_JD,
    )
    candidates = extract_moving_candidates(
        match_stationary_sources(
            load_frame_sources(observations),
            StationaryMatchingConfig(stationary_tolerance_arcsec=1.5),
        )
    )
    tracklets = build_tracklets(
        candidates,
        TrackletBuildConfig(
            max_rate_arcsec_per_min=1.0,
            search_radius_arcsec=2.0,
            max_residual_arcsec=0.5,
        ),
    ).tracklets

    result = identify_tracklets(
        tracklets, observations, IdentificationConfig(match_radius_arcsec=2.0)
    )

    known = [
        identification
        for identification in result.identifications
        if identification.status is IdentificationStatus.KNOWN
    ]
    assert "48606" in {
        identification.best_match.designation for identification in known
    }
    assert result.diagnostics.tracklet_count == len(tracklets)
