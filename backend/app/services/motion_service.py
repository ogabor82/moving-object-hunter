from collections.abc import Sequence
from datetime import datetime

import astropy.units as u
from astropy.coordinates import SkyCoord

from app.models.motion import (
    MotionVector,
    PredictedPosition,
    PredictionMatch,
    PredictionSearchConfig,
)
from app.models.source_detection import SourceDetection
from app.services.astrometry import find_pairs_within


def compute_motion_vector(
    first: SourceDetection,
    first_time: datetime,
    second: SourceDetection,
    second_time: datetime,
) -> MotionVector:
    """Motion from the earlier detection to the later one.

    Times are the frames' observation times (Observation.observed_at). All
    frames use the same timestamp convention, so the offset of that
    timestamp within the exposure cancels in the time delta.
    """
    time_delta_minutes = (second_time - first_time).total_seconds() / 60.0
    if time_delta_minutes <= 0:
        raise ValueError("second_time must be later than first_time.")

    start = _sky_coord(first)
    end = _sky_coord(second)
    separation_arcsec = float(start.separation(end).to_value(u.arcsec))
    position_angle_deg = float(start.position_angle(end).wrap_at(360 * u.deg).deg)
    if position_angle_deg >= 360.0:
        position_angle_deg = 0.0

    return MotionVector(
        time_delta_minutes=time_delta_minutes,
        separation_arcsec=separation_arcsec,
        rate_arcsec_per_min=separation_arcsec / time_delta_minutes,
        position_angle_deg=position_angle_deg,
    )


def predict_position(
    first: SourceDetection,
    first_time: datetime,
    second: SourceDetection,
    second_time: datetime,
    target_time: datetime,
) -> PredictedPosition:
    """Extrapolate the motion of two detections to `target_time`.

    Assumes constant angular rate along the great circle through the two
    detections, which is only valid over short time spans.
    """
    motion = compute_motion_vector(first, first_time, second, second_time)
    start = _sky_coord(first)
    end = _sky_coord(second)
    # Direction of travel at the second point, continuing the great circle.
    heading = end.position_angle(start) + 180 * u.deg
    minutes_after_second = (target_time - second_time).total_seconds() / 60.0
    predicted = end.directional_offset_by(
        heading,
        motion.rate_arcsec_per_min * minutes_after_second * u.arcsec,
    )
    return PredictedPosition(
        time=target_time,
        ra=float(predicted.ra.wrap_at(360 * u.deg).deg) % 360.0,
        dec=float(predicted.dec.deg),
    )


def find_detections_near(
    prediction: PredictedPosition,
    detections: Sequence[SourceDetection],
    config: PredictionSearchConfig,
) -> list[PredictionMatch]:
    """Detections within the configured radius of a prediction, nearest first."""
    _, indices, distances = find_pairs_within(
        [prediction.ra],
        [prediction.dec],
        [detection.ra for detection in detections],
        [detection.dec for detection in detections],
        config.search_radius_arcsec,
    )
    return [
        PredictionMatch(detection=detections[index], distance_arcsec=distance)
        for distance, index in sorted(zip(distances.tolist(), indices.tolist()))
    ]


def _sky_coord(detection: SourceDetection) -> SkyCoord:
    return SkyCoord(detection.ra * u.deg, detection.dec * u.deg, frame="icrs")
