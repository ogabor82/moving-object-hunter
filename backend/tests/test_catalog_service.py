import math
from datetime import datetime, timezone

import pytest

from app.models.observation import Observation
from app.services.catalog_service import (
    CatalogNormalizationError,
    normalize_psf_catalog,
)
from app.services.ztf_service import ZTFPSFCatalog


OBSERVATION = Observation(
    product_id=465467854215,
    observed_at=datetime(2018, 4, 11, 11, 13, 43, tzinfo=timezone.utc),
    field=535,
    filter_code="zr",
    ccd_id=11,
    quadrant_id=3,
    file_frac_day="20180411467847",
)
MAGZP = 26.3084802135098


def make_row(**overrides: float | int) -> dict[str, float | int]:
    row: dict[str, float | int] = {
        "sourceid": 0,
        "xpos": 898.747,
        "ypos": 1.257,
        "ra": 255.7590124,
        "dec": 12.7174256,
        "flux": 187.13213,
        "sigflux": 55.825806,
        "mag": -5.68,
        "sigmag": 0.324,
        "snr": 3.35,
        "chi": 0.877,
        "sharp": 0.083,
        "flags": 0,
    }
    row.update(overrides)
    return row


def test_normalize_psf_catalog_maps_row_to_source_detection() -> None:
    catalog = ZTFPSFCatalog(rows=[make_row()], magnitude_zero_point=MAGZP)

    result = normalize_psf_catalog(OBSERVATION, catalog)

    assert result.rejected_rows == []
    [detection] = result.detections
    assert detection.source_id == "465467854215-0"
    assert detection.observation_product_id == 465467854215
    assert detection.ra == pytest.approx(255.7590124)
    assert detection.dec == pytest.approx(12.7174256)
    assert detection.x == pytest.approx(898.747)
    assert detection.y == pytest.approx(1.257)
    assert detection.magnitude == pytest.approx(-5.68 + MAGZP)
    assert detection.magnitude_error == pytest.approx(0.324)
    assert detection.snr == pytest.approx(3.35)
    assert detection.on_image_edge is False
    assert detection.mask_bits == 0


@pytest.mark.parametrize(
    ("flags", "on_image_edge", "mask_bits"),
    [(0, False, 0), (-1, True, 0), (64, False, 64), (256, False, 256)],
)
def test_normalize_psf_catalog_maps_quality_flags(
    flags: int,
    on_image_edge: bool,
    mask_bits: int,
) -> None:
    catalog = ZTFPSFCatalog(
        rows=[make_row(flags=flags)], magnitude_zero_point=MAGZP
    )

    [detection] = normalize_psf_catalog(OBSERVATION, catalog).detections

    assert detection.on_image_edge is on_image_edge
    assert detection.mask_bits == mask_bits


def test_normalize_psf_catalog_normalizes_full_observation() -> None:
    rows = [
        make_row(sourceid=index, flags=-1 if index % 2 else 0)
        for index in range(50)
    ]
    catalog = ZTFPSFCatalog(rows=rows, magnitude_zero_point=MAGZP)

    result = normalize_psf_catalog(OBSERVATION, catalog)

    assert len(result.detections) == 50
    assert result.rejected_rows == []
    assert len({detection.source_id for detection in result.detections}) == 50


def test_normalize_psf_catalog_rejects_invalid_rows_and_keeps_valid_ones() -> None:
    rows = [
        make_row(sourceid=0),
        make_row(sourceid=1, ra=math.nan),
        make_row(sourceid=2, dec=95.0),
        make_row(sourceid=3, snr=-2.0),
        make_row(sourceid=4, mag=math.inf),
        {"sourceid": 5, "ra": 255.0},
        make_row(sourceid=6),
    ]
    catalog = ZTFPSFCatalog(rows=rows, magnitude_zero_point=MAGZP)

    result = normalize_psf_catalog(OBSERVATION, catalog)

    assert [d.source_id for d in result.detections] == [
        "465467854215-0",
        "465467854215-6",
    ]
    assert [rejected.row_index for rejected in result.rejected_rows] == [
        1,
        2,
        3,
        4,
        5,
    ]
    reasons = [rejected.reason for rejected in result.rejected_rows]
    assert reasons[0].startswith("ra:")
    assert reasons[1].startswith("dec:")
    assert reasons[2].startswith("snr:")
    assert reasons[3].startswith("magnitude:")
    assert reasons[4].startswith("unreadable row")


def test_normalize_psf_catalog_handles_empty_catalog() -> None:
    catalog = ZTFPSFCatalog(rows=[], magnitude_zero_point=MAGZP)

    result = normalize_psf_catalog(OBSERVATION, catalog)

    assert result.detections == []
    assert result.rejected_rows == []


def test_normalize_psf_catalog_requires_zero_point() -> None:
    catalog = ZTFPSFCatalog(rows=[make_row()], magnitude_zero_point=None)

    with pytest.raises(CatalogNormalizationError, match="MAGZP"):
        normalize_psf_catalog(OBSERVATION, catalog)
