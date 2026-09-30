"""Live loading of a frozen validation field (IRSA + SkyBoT)."""

import csv
import math
from collections import Counter
from dataclasses import dataclass
from io import StringIO

import astropy.units as u
import httpx
from astropy.coordinates import SkyCoord

from app.models.frame_sources import FrameSources
from app.models.known_object import KnownObjectField
from app.models.observation import Observation
from app.services.catalog_service import normalize_psf_catalog
from app.services.identification_service import mid_exposure_jd_utc
from app.services.skybot_service import ZTF_OBSERVATORY_CODE, query_known_objects
from app.services.ztf_service import (
    METADATA_COLUMNS,
    ZTF_SCIENCE_METADATA_URL,
    ZTFServiceError,
    fetch_psf_catalog,
    map_ztf_metadata_to_observation,
)
from app.validation.models import FrameMetadata, ValidationField


FRAME_METADATA_COLUMNS = (
    "ra",
    "dec",
    "ra1",
    "dec1",
    "ra2",
    "dec2",
    "ra3",
    "dec3",
    "ra4",
    "dec4",
    "maglimit",
    "seeing",
    "airmass",
)
# Extra cone margin beyond the quadrant corners for the SkyBoT query.
SKYBOT_CONE_MARGIN_ARCSEC = 60.0


@dataclass(frozen=True)
class FieldData:
    """Live data of one validation field, frames in time order."""

    field: ValidationField
    observations: list[Observation]
    frame_metadata: list[FrameMetadata]
    frames: list[FrameSources]
    sharp_by_source_id: dict[str, float]
    skybot_fields: list[KnownObjectField]


def load_field_data(
    field: ValidationField,
    client: httpx.Client | None = None,
) -> FieldData:
    """Fetch metadata, PSF catalogs and per-frame SkyBoT predictions."""
    observations, metadata = fetch_frame_metadata(field.product_ids, client)
    catalogs = load_catalog_frames(observations, client)

    skybot_fields = [
        query_known_objects(
            frame.center_ra,
            frame.center_dec,
            _cone_radius_degrees(frame),
            mid_exposure_jd_utc(observation),
            observer=ZTF_OBSERVATORY_CODE,
            client=client,
        )
        for observation, frame in zip(observations, metadata)
    ]
    return FieldData(
        field=field,
        observations=observations,
        frame_metadata=metadata,
        frames=catalogs.frames,
        sharp_by_source_id=catalogs.sharp_by_source_id,
        skybot_fields=skybot_fields,
    )


@dataclass(frozen=True)
class CatalogFrames:
    """Normalized frames plus raw PSF catalog values the domain drops.

    `sharp` is not mapped to SourceDetection (docs/ztf_psf_catalog_mapping
    .md), so it is kept here by source_id for research use; non-finite
    values are left out. `negative_flag_counts` counts raw `flags` values
    below 0: -1 becomes on_image_edge, any other negative value would map
    to on_image_edge=False, mask_bits=0 and so be lost.
    """

    frames: list[FrameSources]
    sharp_by_source_id: dict[str, float]
    negative_flag_counts: dict[int, int]


def load_catalog_frames(
    observations: list[Observation],
    client: httpx.Client | None = None,
) -> CatalogFrames:
    """Fetch and normalize each frame's PSF catalog, keeping raw `sharp`."""
    frames: list[FrameSources] = []
    sharp_by_source_id: dict[str, float] = {}
    negative_flags: Counter[int] = Counter()
    for observation in observations:
        catalog = fetch_psf_catalog(observation, client)
        result = normalize_psf_catalog(observation, catalog)
        frames.append(
            FrameSources(
                observation=observation,
                detections=result.detections,
                rejected_row_count=len(result.rejected_rows),
            )
        )
        for row in catalog.rows:
            source_id = f"{observation.product_id}-{int(row['sourceid'])}"
            sharp = float(row["sharp"])
            if math.isfinite(sharp):
                sharp_by_source_id[source_id] = sharp
            if int(row["flags"]) < 0:
                negative_flags[int(row["flags"])] += 1
    return CatalogFrames(
        frames, sharp_by_source_id, dict(sorted(negative_flags.items()))
    )


def fetch_frame_metadata(
    product_ids: list[int],
    client: httpx.Client | None = None,
) -> tuple[list[Observation], list[FrameMetadata]]:
    """Observations and quality/footprint metadata, sorted by time."""
    params = {
        "WHERE": "pid IN (" + ",".join(str(pid) for pid in product_ids) + ")",
        "COLUMNS": ",".join((*METADATA_COLUMNS, *FRAME_METADATA_COLUMNS)),
        "ct": "csv",
    }
    request = client.get if client is not None else httpx.get
    try:
        response = request(ZTF_SCIENCE_METADATA_URL, params=params, timeout=60.0)
    except httpx.HTTPError as exc:
        raise ZTFServiceError(f"IRSA ZTF metadata request failed: {exc}") from exc
    if not response.is_success:
        raise ZTFServiceError(
            f"IRSA ZTF metadata request failed with HTTP {response.status_code}."
        )

    rows = list(csv.DictReader(StringIO(response.text)))
    found = {int(row["pid"]) for row in rows}
    missing = sorted(set(product_ids) - found)
    if missing:
        raise ZTFServiceError(f"IRSA returned no metadata for pid(s) {missing}.")

    pairs = sorted(
        (
            (map_ztf_metadata_to_observation(row), _frame_metadata(row))
            for row in rows
        ),
        key=lambda pair: (pair[0].observed_at, pair[0].product_id),
    )
    return [pair[0] for pair in pairs], [pair[1] for pair in pairs]


def _frame_metadata(row: dict[str, str]) -> FrameMetadata:
    return FrameMetadata(
        product_id=int(row["pid"]),
        center_ra=float(row["ra"]),
        center_dec=float(row["dec"]),
        corners=[
            (float(row[f"ra{index}"]), float(row[f"dec{index}"]))
            for index in range(1, 5)
        ],
        maglimit=float(row["maglimit"]),
        seeing_arcsec=float(row["seeing"]),
        airmass=float(row["airmass"]),
    )


def _cone_radius_degrees(frame: FrameMetadata) -> float:
    center = SkyCoord(frame.center_ra * u.deg, frame.center_dec * u.deg)
    corners = SkyCoord(
        [corner[0] for corner in frame.corners] * u.deg,
        [corner[1] for corner in frame.corners] * u.deg,
    )
    radius = center.separation(corners).max() + SKYBOT_CONE_MARGIN_ARCSEC * u.arcsec
    return float(radius.to_value(u.deg))
