"""Builders for synthetic multi-frame test data."""

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

from app.models.frame_sources import FrameSources
from app.models.observation import Observation
from app.models.source_detection import SourceDetection


START_TIME = datetime(2018, 4, 11, 10, 0, tzinfo=timezone.utc)
ARCSEC = 1 / 3600


def make_detection(
    product_id: int,
    index: int,
    ra: float,
    dec: float,
) -> SourceDetection:
    return SourceDetection(
        source_id=f"{product_id}-{index}",
        observation_product_id=product_id,
        ra=ra,
        dec=dec,
        x=100.0 + index,
        y=200.0 + index,
        magnitude=19.0,
        magnitude_error=0.05,
        snr=20.0,
        on_image_edge=False,
        mask_bits=0,
    )


def make_frame(
    product_id: int,
    minutes_after_start: float,
    positions: Sequence[tuple[float, float]],
) -> FrameSources:
    observation = Observation(
        product_id=product_id,
        observed_at=START_TIME + timedelta(minutes=minutes_after_start),
        field=535,
        filter_code="zr",
        ccd_id=11,
        quadrant_id=3,
        file_frac_day="20180411467847",
    )
    return FrameSources(
        observation=observation,
        detections=[
            make_detection(product_id, index, ra, dec)
            for index, (ra, dec) in enumerate(positions)
        ],
        rejected_row_count=0,
    )
