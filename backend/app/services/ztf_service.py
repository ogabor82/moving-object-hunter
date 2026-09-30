import csv
from collections.abc import Mapping
from dataclasses import dataclass
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
    "exptime",
)
MAX_RESULTS = 10
# IRSA metadata searches have been observed to take 20-40 s under load.
METADATA_TIMEOUT_SECONDS = 90.0
# Minimum frames for a tracklet sequence (04 – Baby Steps, AS-010).
MIN_SEQUENCE_FRAMES = 3

SCIENCE_IMAGE_SUFFIX = "sciimg.fits"
PSF_CATALOG_SUFFIX = "psfcat.fits"
PSF_CATALOG_EXTENSION = "PSF_CATALOG"
# Column definitions: ZSDS Explanatory Supplement, section 10.6.
PSF_CATALOG_COLUMNS = (
    "sourceid",
    "xpos",
    "ypos",
    "ra",
    "dec",
    "flux",
    "sigflux",
    "mag",
    "sigmag",
    "snr",
    "chi",
    "sharp",
    "flags",
)


class ZTFServiceError(RuntimeError):
    """Raised when the IRSA ZTF metadata query cannot be completed."""


class InsufficientFramesError(ZTFServiceError):
    """Raised when a sky position has too few observations for a sequence."""


class ObservationNotFoundError(ZTFServiceError):
    """Raised when IRSA has no metadata for requested product ids."""


class ZTFMetadataMappingError(ValueError):
    """Raised when a ZTF metadata row cannot be mapped to an Observation."""


@dataclass(frozen=True)
class ZTFPSFCatalog:
    """Raw ZTF PSF-fit catalog rows with the header photometric zero point."""

    rows: list[dict[str, float | int]]
    magnitude_zero_point: float | None


def fetch_ztf_metadata(
    ra_degrees: float,
    dec_degrees: float,
    start_jd: float,
    end_jd: float,
    client: httpx.Client | None = None,
    size_degrees: float | None = None,
) -> list[dict[str, str]]:
    """Fetch metadata of ZTF science exposures at a sky position.

    The time window is [start_jd, end_jd) in Julian Date. Without
    `size_degrees` the exposures covering the position are returned; with
    it, those overlapping a box of that full width (IRSA IBE SIZE, degrees,
    INTERSECT=OVERLAPS) centred on the position.
    """
    params = {
        "POS": f"{ra_degrees},{dec_degrees}",
        "WHERE": f"obsjd >= {start_jd} AND obsjd < {end_jd}",
        "COLUMNS": ",".join(METADATA_COLUMNS),
        "ct": "csv",
    }
    if size_degrees is not None:
        params["SIZE"] = f"{size_degrees}"
        params["INTERSECT"] = "OVERLAPS"
    request = client.get if client is not None else httpx.get

    try:
        response = request(
            ZTF_SCIENCE_METADATA_URL, params=params, timeout=METADATA_TIMEOUT_SECONDS
        )
    except httpx.HTTPError as exc:
        raise ZTFServiceError(f"IRSA ZTF metadata request failed: {exc}") from exc

    if not response.is_success:
        raise ZTFServiceError(
            f"IRSA ZTF metadata request failed with HTTP {response.status_code}."
        )

    rows = csv.DictReader(StringIO(response.text))
    return [dict(row) for row in rows]


def fetch_hardcoded_ztf_metadata(
    client: httpx.Client | None = None,
) -> list[dict[str, str]]:
    """Fetch the first metadata rows for the fixed AS-003 sky/time window."""
    rows = fetch_ztf_metadata(
        HARDCODED_RA_DEGREES,
        HARDCODED_DEC_DEGREES,
        HARDCODED_START_JD,
        HARDCODED_END_JD,
        client,
    )
    return rows[:MAX_RESULTS]


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
            exposure_seconds=raw.get("exptime") or None,
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


def fetch_observations(
    product_ids: list[int],
    client: httpx.Client | None = None,
) -> list[Observation]:
    """Fetch the Observations of the given ZTF product ids, in time order.

    Raises ZTFServiceError if IRSA has no metadata for any of the ids.
    """
    if not product_ids:
        raise ValueError("At least one product id is required.")
    params = {
        "WHERE": "pid IN (" + ",".join(str(int(pid)) for pid in product_ids) + ")",
        "COLUMNS": ",".join(METADATA_COLUMNS),
        "ct": "csv",
    }
    request = client.get if client is not None else httpx.get

    try:
        response = request(
            ZTF_SCIENCE_METADATA_URL, params=params, timeout=METADATA_TIMEOUT_SECONDS
        )
    except httpx.HTTPError as exc:
        raise ZTFServiceError(f"IRSA ZTF metadata request failed: {exc}") from exc

    if not response.is_success:
        raise ZTFServiceError(
            f"IRSA ZTF metadata request failed with HTTP {response.status_code}."
        )

    observations = [
        map_ztf_metadata_to_observation(row)
        for row in csv.DictReader(StringIO(response.text))
    ]
    missing = sorted(
        set(product_ids) - {observation.product_id for observation in observations}
    )
    if missing:
        raise ObservationNotFoundError(
            f"IRSA returned no metadata for pid(s) {missing}."
        )
    return sorted(
        observations,
        key=lambda observation: (observation.observed_at, observation.product_id),
    )


def search_observations(
    ra_degrees: float,
    dec_degrees: float,
    radius_degrees: float,
    start_jd: float,
    end_jd: float,
    client: httpx.Client | None = None,
) -> list[Observation]:
    """Time-ordered ZTF observations near a position in [start_jd, end_jd).

    IRSA IBE searches rectangular regions, so the query uses the box of
    side 2 * radius that circumscribes the requested circle; exposures that
    only touch the box corners outside the circle can be included.
    """
    if not 0.0 <= ra_degrees < 360.0:
        raise ValueError("ra_degrees must be in [0, 360).")
    if not -90.0 <= dec_degrees <= 90.0:
        raise ValueError("dec_degrees must be in [-90, 90].")
    if radius_degrees <= 0:
        raise ValueError("radius_degrees must be positive.")
    if not start_jd < end_jd:
        raise ValueError("start_jd must be earlier than end_jd.")

    rows = fetch_ztf_metadata(
        ra_degrees,
        dec_degrees,
        start_jd,
        end_jd,
        client,
        size_degrees=2 * radius_degrees,
    )
    return sorted(
        (map_ztf_metadata_to_observation(row) for row in rows),
        key=lambda observation: (observation.observed_at, observation.product_id),
    )


def find_observation_sequence(
    ra_degrees: float,
    dec_degrees: float,
    start_jd: float,
    end_jd: float,
    min_frames: int = MIN_SEQUENCE_FRAMES,
    client: httpx.Client | None = None,
) -> list[Observation]:
    """Find the time-ordered ZTF observations covering one sky position.

    Raises InsufficientFramesError when fewer than `min_frames` exist.
    """
    if not start_jd < end_jd:
        raise ValueError("start_jd must be earlier than end_jd.")

    rows = fetch_ztf_metadata(ra_degrees, dec_degrees, start_jd, end_jd, client)
    observations = sorted(
        (map_ztf_metadata_to_observation(row) for row in rows),
        key=lambda observation: (observation.observed_at, observation.product_id),
    )
    if len(observations) < min_frames:
        raise InsufficientFramesError(
            f"Found {len(observations)} ZTF observation(s) at "
            f"RA={ra_degrees}, Dec={dec_degrees}; at least {min_frames} "
            "are required."
        )
    return observations


def _build_science_product_url(observation: Observation, suffix: str) -> str:
    """Build the IRSA archive URL for one science-exposure product file."""
    file_frac_day = observation.file_frac_day
    if len(file_frac_day) != 14 or not file_frac_day.isdigit():
        raise ZTFServiceError(
            "Cannot build ZTF science product URL: file_frac_day must contain "
            "14 digits."
        )

    year = file_frac_day[:4]
    month_day = file_frac_day[4:8]
    fractional_day = file_frac_day[8:]
    filename = (
        f"ztf_{file_frac_day}_{observation.field:06d}_"
        f"{observation.filter_code}_c{observation.ccd_id:02d}_"
        f"o_q{observation.quadrant_id}_{suffix}"
    )
    return (
        f"{ZTF_SCIENCE_DATA_BASE_URL}/{year}/{month_day}/"
        f"{fractional_day}/{filename}"
    )


def build_science_image_url(observation: Observation) -> str:
    """Build the IRSA archive URL for an Observation's primary science image."""
    return _build_science_product_url(observation, SCIENCE_IMAGE_SUFFIX)


def build_psf_catalog_url(observation: Observation) -> str:
    """Build the IRSA archive URL for an Observation's PSF-fit source catalog."""
    return _build_science_product_url(observation, PSF_CATALOG_SUFFIX)


def _download_fits_product(
    url: str,
    label: str,
    client: httpx.Client | None,
    params: dict[str, str] | None = None,
) -> bytes:
    """Download one ZTF FITS product and check that it looks like FITS."""
    request = client.get if client is not None else httpx.get

    try:
        response = request(url, params=params, timeout=120.0)
    except httpx.HTTPError as exc:
        raise ZTFServiceError(f"{label} request failed: {exc}") from exc

    if not response.is_success:
        raise ZTFServiceError(
            f"{label} request failed with HTTP {response.status_code}."
        )

    payload = response.content
    if not payload:
        raise ZTFServiceError(f"{label} response was empty.")
    if not payload.startswith(b"SIMPLE  ="):
        raise ZTFServiceError(f"{label} response is not a FITS file.")
    return payload


def fetch_science_image(
    observation: Observation,
    client: httpx.Client | None = None,
) -> bytes:
    """Download and minimally validate a ZTF single-exposure science FITS image."""
    payload = _download_fits_product(
        build_science_image_url(observation),
        "ZTF science image",
        client,
    )

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


def fetch_science_cutout(
    observation: Observation,
    ra_degrees: float,
    dec_degrees: float,
    size_arcsec: float,
    client: httpx.Client | None = None,
) -> bytes:
    """Download a square FITS cutout of an Observation's science image.

    Uses the IRSA IBE cutout service (center/size query on the image URL,
    https://irsa.ipac.caltech.edu/ibe/cutouts.html). The cutout keeps the
    parent image's pixel grid and orientation, and is clipped at the image
    edge; a cutout that does not overlap the image is an error.
    """
    if not 0.0 <= ra_degrees < 360.0:
        raise ValueError("ra_degrees must be in [0, 360).")
    if not -90.0 <= dec_degrees <= 90.0:
        raise ValueError("dec_degrees must be in [-90, 90].")
    if size_arcsec <= 0:
        raise ValueError("size_arcsec must be positive.")
    return _download_fits_product(
        build_science_image_url(observation),
        "ZTF science image cutout",
        client,
        params={
            "center": f"{ra_degrees},{dec_degrees}deg",
            "size": f"{size_arcsec}arcsec",
            "gzip": "false",
        },
    )


def read_psf_catalog(payload: bytes) -> ZTFPSFCatalog:
    """Parse a ZTF PSF-fit catalog FITS payload into rows and zero point."""
    try:
        with fits.open(BytesIO(payload), memmap=False) as hdul:
            catalog_hdu = (
                hdul[PSF_CATALOG_EXTENSION]
                if PSF_CATALOG_EXTENSION in hdul
                else None
            )
            if not isinstance(catalog_hdu, fits.BinTableHDU):
                raise ZTFServiceError(
                    "ZTF PSF catalog FITS has no "
                    f"{PSF_CATALOG_EXTENSION} extension."
                )
            missing_columns = [
                name
                for name in PSF_CATALOG_COLUMNS
                if name not in catalog_hdu.columns.names
            ]
            if missing_columns:
                raise ZTFServiceError(
                    "ZTF PSF catalog is missing column(s): "
                    + ", ".join(missing_columns)
                )
            columns = {
                name: catalog_hdu.data[name].tolist()
                if catalog_hdu.data is not None
                else []
                for name in PSF_CATALOG_COLUMNS
            }
            magzp = hdul[0].header.get("MAGZP")
    except (OSError, ValueError) as exc:
        raise ZTFServiceError(
            f"ZTF PSF catalog response is not a valid FITS file: {exc}"
        ) from exc

    rows = [
        dict(zip(PSF_CATALOG_COLUMNS, values))
        for values in zip(*columns.values())
    ]
    return ZTFPSFCatalog(
        rows=rows,
        magnitude_zero_point=float(magzp) if magzp is not None else None,
    )


def fetch_psf_catalog(
    observation: Observation,
    client: httpx.Client | None = None,
) -> ZTFPSFCatalog:
    """Download and read the ZTF PSF-fit source catalog of an Observation."""
    payload = _download_fits_product(
        build_psf_catalog_url(observation),
        "ZTF PSF catalog",
        client,
    )
    return read_psf_catalog(payload)
