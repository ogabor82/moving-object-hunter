import os

import pytest

from app.services.skybot_service import query_skybot_cone


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
