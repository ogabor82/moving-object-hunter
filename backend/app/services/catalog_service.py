from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from app.models.frame_sources import FrameSources
from app.models.observation import Observation
from app.models.source_detection import SourceDetection
from app.services.ztf_service import ZTFPSFCatalog, fetch_psf_catalog


# ZTF PSF catalog flag value for sources on/near an image edge
# (ZSDS Explanatory Supplement, section 10.6).
ZTF_EDGE_FLAG = -1


class CatalogNormalizationError(ValueError):
    """Raised when a whole source catalog cannot be normalized."""


@dataclass(frozen=True)
class RejectedCatalogRow:
    """A catalog row that could not be mapped to a SourceDetection."""

    row_index: int
    reason: str


@dataclass(frozen=True)
class CatalogNormalizationResult:
    """Normalized detections of one observation plus the rejected rows."""

    detections: list[SourceDetection]
    rejected_rows: list[RejectedCatalogRow]


def normalize_psf_catalog(
    observation: Observation,
    catalog: ZTFPSFCatalog,
) -> CatalogNormalizationResult:
    """Map every ZTF PSF catalog row of an observation to SourceDetection.

    Invalid rows are collected in `rejected_rows` instead of failing the
    whole observation. See docs/ztf_psf_catalog_mapping.md.
    """
    if catalog.magnitude_zero_point is None:
        raise CatalogNormalizationError(
            "ZTF PSF catalog has no MAGZP; magnitudes cannot be calibrated."
        )

    detections: list[SourceDetection] = []
    rejected_rows: list[RejectedCatalogRow] = []
    for index, row in enumerate(catalog.rows):
        try:
            detections.append(
                _map_psf_row(observation, row, catalog.magnitude_zero_point)
            )
        except ValidationError as exc:
            rejected_rows.append(
                RejectedCatalogRow(index, _describe_validation_error(exc))
            )
        except (KeyError, TypeError, ValueError) as exc:
            rejected_rows.append(
                RejectedCatalogRow(index, f"unreadable row: {exc!r}")
            )

    return CatalogNormalizationResult(detections, rejected_rows)


def load_frame_sources(
    observations: Sequence[Observation],
    client: httpx.Client | None = None,
) -> list[FrameSources]:
    """Fetch and normalize the PSF catalog of every observation, in order.

    A frame whose catalog cannot be fetched or normalized fails the load.
    """
    frames = []
    for observation in observations:
        result = normalize_psf_catalog(
            observation, fetch_psf_catalog(observation, client)
        )
        frames.append(
            FrameSources(
                observation=observation,
                detections=result.detections,
                rejected_row_count=len(result.rejected_rows),
            )
        )
    return frames


def _map_psf_row(
    observation: Observation,
    row: Mapping[str, float | int],
    magnitude_zero_point: float,
) -> SourceDetection:
    flags = int(row["flags"])
    return SourceDetection(
        source_id=f"{observation.product_id}-{int(row['sourceid'])}",
        observation_product_id=observation.product_id,
        ra=row["ra"],
        dec=row["dec"],
        x=row["xpos"],
        y=row["ypos"],
        magnitude=float(row["mag"]) + magnitude_zero_point,
        magnitude_error=row["sigmag"],
        snr=row["snr"],
        on_image_edge=flags == ZTF_EDGE_FLAG,
        mask_bits=max(flags, 0),
    )


def _describe_validation_error(exc: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
        for error in exc.errors()
    )
