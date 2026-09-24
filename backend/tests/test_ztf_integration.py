import os

import pytest

from app.services.ztf_service import fetch_hardcoded_ztf_metadata


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_ZTF_INTEGRATION") != "1",
        reason="Set RUN_ZTF_INTEGRATION=1 to query the live IRSA service.",
    ),
]


def test_live_irsa_query_returns_ztf_observation() -> None:
    rows = fetch_hardcoded_ztf_metadata()

    assert rows
    assert {
        "obsdate",
        "field",
        "filtercode",
        "ccdid",
        "qid",
        "pid",
        "filefracday",
    } <= rows[0].keys()
