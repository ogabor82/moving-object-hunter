import os
from io import BytesIO

import pytest
from astropy.io import fits

from app.models.observation import Observation
from app.services.ztf_service import (
    fetch_hardcoded_ztf_observations,
    fetch_science_image,
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
