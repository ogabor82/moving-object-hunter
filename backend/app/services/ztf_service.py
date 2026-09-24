import csv
from collections.abc import Mapping
from datetime import datetime
from io import BytesIO, StringIO

import httpx
from astropy.io import fits

from app.models.observation import Observation


ZTF_SCIENCE_METADATA_URL = (
    "https://irsa.ipac.caltech.edu/ibe/search/ztf/products/sci"
)
ZTF_SCIENCE_DATA_BASE_URL = (
    "https://irsa.ipac.caltech.edu/ibe/data/ztf/products/sci"
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


class ZTFMetadataMappingError(ValueError):
    """Raised when a ZTF metadata row cannot be mapped to an Observation."""


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


def map_ztf_metadata_to_observation(raw: Mapping[str, str]) -> Observation:
    """Map one raw IRSA ZTF metadata row to the domain model."""
    required_fields = (
        "pid",
        "obsdate",
        "field",
        "filtercode",
        "ccdid",
        "qid",
        "filefracday",
    )
    missing_fields = [name for name in required_fields if not raw.get(name)]
    if missing_fields:
        raise ZTFMetadataMappingError(
            "Missing required ZTF metadata field(s): " + ", ".join(missing_fields)
        )

    try:
        return Observation(
            product_id=raw["pid"],
            observed_at=datetime.fromisoformat(raw["obsdate"]),
            field=raw["field"],
            filter_code=raw["filtercode"],
            ccd_id=raw["ccdid"],
            quadrant_id=raw["qid"],
            file_frac_day=raw["filefracday"],
        )
    except (TypeError, ValueError) as exc:
        raise ZTFMetadataMappingError(
            f"Invalid ZTF metadata row: {exc}"
        ) from exc


def fetch_hardcoded_ztf_observations(
    client: httpx.Client | None = None,
) -> list[Observation]:
    """Fetch and map the fixed AS-003 query to domain observations."""
    rows = fetch_hardcoded_ztf_metadata(client)
    return [map_ztf_metadata_to_observation(row) for row in rows]


def build_science_image_url(observation: Observation) -> str:
    """Build the IRSA archive URL for an Observation's primary science image."""
    file_frac_day = observation.file_frac_day
    if len(file_frac_day) != 14 or not file_frac_day.isdigit():
        raise ZTFServiceError(
            "Cannot build ZTF science image URL: file_frac_day must contain "
            "14 digits."
        )

    year = file_frac_day[:4]
    month_day = file_frac_day[4:8]
    fractional_day = file_frac_day[8:]
    filename = (
        f"ztf_{file_frac_day}_{observation.field:06d}_"
        f"{observation.filter_code}_c{observation.ccd_id:02d}_"
        f"o_q{observation.quadrant_id}_sciimg.fits"
    )
    return (
        f"{ZTF_SCIENCE_DATA_BASE_URL}/{year}/{month_day}/"
        f"{fractional_day}/{filename}"
    )


def fetch_science_image(
    observation: Observation,
    client: httpx.Client | None = None,
) -> bytes:
    """Download and minimally validate a ZTF single-exposure science FITS image."""
    image_url = build_science_image_url(observation)
    request = client.get if client is not None else httpx.get

    try:
        response = request(image_url, timeout=120.0)
    except httpx.HTTPError as exc:
        raise ZTFServiceError(f"ZTF science image request failed: {exc}") from exc

    if not response.is_success:
        raise ZTFServiceError(
            f"ZTF science image request failed with HTTP {response.status_code}."
        )

    payload = response.content
    if not payload:
        raise ZTFServiceError("ZTF science image response was empty.")
    if not payload.startswith(b"SIMPLE  ="):
        raise ZTFServiceError("ZTF science image response is not a FITS file.")

    try:
        with fits.open(BytesIO(payload), memmap=False) as hdul:
            hdul.verify("exception")
            if not hdul or hdul[0].data is None:
                raise ZTFServiceError(
                    "ZTF science image FITS contains no primary image data."
                )
            hdul[0].data.shape
    except (OSError, ValueError) as exc:
        raise ZTFServiceError(
            f"ZTF science image response is not a valid FITS file: {exc}"
        ) from exc

    return payload
