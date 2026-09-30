"""Tracklet → TrackletQualityFeatures (AS-031), a pure function.

Reads the tracklet (and optionally raw `sharp` values); never changes the
tracklet, its fit or any identification, and applies no threshold.
"""

import math
import statistics
from collections.abc import Mapping
from functools import reduce

from app.models.quality import SharpAvailability, TrackletQualityFeatures
from app.models.tracklet import Tracklet


def extract_quality_features(
    tracklet: Tracklet,
    sharp_by_source_id: Mapping[str, float] | None = None,
) -> TrackletQualityFeatures:
    """Quality features of one tracklet; deterministic for equal input.

    `sharp_by_source_id` maps SourceDetection.source_id to the raw ZTF PSF
    catalog `sharp`; omit it when the raw catalog is not at hand (the
    features then say `unavailable`, nothing is estimated).
    """
    detections = [item.detection for item in tracklet.detections]
    snrs = [detection.snr for detection in detections]
    # min()/max() return the first extreme, so ties resolve in time order.
    brightest = min(detections, key=lambda detection: detection.magnitude)
    faintest = max(detections, key=lambda detection: detection.magnitude)
    magnitude_range = faintest.magnitude - brightest.magnitude
    range_error = math.hypot(brightest.magnitude_error, faintest.magnitude_error)

    edge = [detection.on_image_edge for detection in detections]
    masked = [detection.mask_bits != 0 for detection in detections]

    if sharp_by_source_id is None:
        sharp_values: list[float | None] = []
        availability = SharpAvailability.UNAVAILABLE
    else:
        sharp_values = [
            _finite(sharp_by_source_id.get(detection.source_id))
            for detection in detections
        ]
        availability = (
            SharpAvailability.COMPLETE
            if all(value is not None for value in sharp_values)
            else SharpAvailability.PARTIAL
        )
    complete = availability is SharpAvailability.COMPLETE

    return TrackletQualityFeatures(
        tracklet_id=tracklet.tracklet_id,
        tracklet_status=tracklet.status,
        detection_count=len(detections),
        min_snr=min(snrs),
        median_snr=statistics.median(snrs),
        magnitude_range_mag=magnitude_range,
        magnitude_range_sigma=(
            magnitude_range / range_error if range_error > 0 else None
        ),
        edge_detection_count=sum(edge),
        masked_detection_count=sum(masked),
        flagged_detection_count=sum(e or m for e, m in zip(edge, masked)),
        mask_bits_union=reduce(
            lambda bits, detection: bits | detection.mask_bits, detections, 0
        ),
        sharp_availability=availability,
        sharp_values=sharp_values,
        sharp_min=min(sharp_values) if complete else None,
        sharp_max=max(sharp_values) if complete else None,
        angular_velocity_arcsec_per_min=tracklet.angular_velocity_arcsec_per_min,
        position_angle_deg=tracklet.position_angle_deg,
        fit_rms_residual_arcsec=tracklet.fit_rms_residual_arcsec,
        fit_max_residual_arcsec=tracklet.fit_max_residual_arcsec,
    )


def _finite(value: float | None) -> float | None:
    return float(value) if value is not None and math.isfinite(value) else None
