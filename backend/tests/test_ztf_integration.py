import os

import pytest

from app.models.observation import Observation
from app.services.ztf_service import fetch_hardcoded_ztf_observations


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_ZTF_INTEGRATION") != "1",
        reason="Set RUN_ZTF_INTEGRATION=1 to query the live IRSA service.",
    ),
]


def test_live_irsa_query_returns_ztf_observation() -> None:
    observations = fetch_hardcoded_ztf_observations()

    assert observations
    assert isinstance(observations[0], Observation)
