import csv
from io import StringIO

import httpx


ZTF_SCIENCE_METADATA_URL = (
    "https://irsa.ipac.caltech.edu/ibe/search/ztf/products/sci"
)

# Fixed POC target documented by IRSA as having ZTF science coverage.
HARDCODED_RA_DEGREES = 255.57691
HARDCODED_DEC_DEGREES = 12.28378

# 2018-04-11 00:00:00 UTC (inclusive) to 2018-04-12 00:00:00 UTC (exclusive).
HARDCODED_START_JD = 2458219.5
HARDCODED_END_JD = 2458220.5

METADATA_COLUMNS = (
    "obsdate",
    "obsjd",
    "field",
    "filtercode",
    "ccdid",
    "qid",
    "pid",
    "filefracday",
    "imgtypecode",
)
MAX_RESULTS = 10


class ZTFServiceError(RuntimeError):
    """Raised when the IRSA ZTF metadata query cannot be completed."""


def fetch_hardcoded_ztf_metadata(
    client: httpx.Client | None = None,
) -> list[dict[str, str]]:
    """Fetch the first metadata rows for the fixed AS-003 sky/time window."""
    params = {
        "POS": f"{HARDCODED_RA_DEGREES},{HARDCODED_DEC_DEGREES}",
        "WHERE": (
            f"obsjd >= {HARDCODED_START_JD} AND obsjd < {HARDCODED_END_JD}"
        ),
        "COLUMNS": ",".join(METADATA_COLUMNS),
        "ct": "csv",
    }
    request = client.get if client is not None else httpx.get

    try:
        response = request(ZTF_SCIENCE_METADATA_URL, params=params, timeout=30.0)
    except httpx.HTTPError as exc:
        raise ZTFServiceError(f"IRSA ZTF metadata request failed: {exc}") from exc

    if not response.is_success:
        raise ZTFServiceError(
            f"IRSA ZTF metadata request failed with HTTP {response.status_code}."
        )

    rows = csv.DictReader(StringIO(response.text))
    return [dict(row) for row in rows][:MAX_RESULTS]
