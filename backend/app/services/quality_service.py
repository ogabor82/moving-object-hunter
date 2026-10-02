"""Tracklet → TrackletQualityFeatures (AS-031), a pure function.

Reads the tracklet (and optionally raw `sharp` values); never changes the
tracklet, its fit or any identification, and applies no threshold.
"""

import math
import statistics
from collections import defaultdict
from collections.abc import Mapping, Sequence
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


# Derived tracklet features of the AS-037 pre-registration, used by the
# AS-038/039/040 research tables and the M1 review ranking (AS-041). They
# are defined only here; app.validation.feature_evaluation imports them.


def sharp_abs_max(sharp_values: Sequence[float | None], complete: bool) -> float | None:
    """max |sharp| over the detections; None unless sharp is complete."""
    if not complete or not sharp_values:
        return None
    return max(abs(v) for v in sharp_values)


def shared_detection_tracklets(detections_by_tracklet: Mapping[str, Sequence[str]]) -> dict[str, int]:
    """Per built tracklet: number of OTHER built tracklets that share at
    least one detection (source id) with it (AS-032 O3)."""
    owners: dict[str, set[str]] = defaultdict(set)
    for tracklet_id, sources in detections_by_tracklet.items():
        for source in sources:
            owners[source].add(tracklet_id)
    return {
        tracklet_id: len(set().union(*(owners[s] for s in sources)) - {tracklet_id})
        for tracklet_id, sources in detections_by_tracklet.items()
    }
