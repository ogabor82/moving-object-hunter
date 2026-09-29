from datetime import datetime

import astropy.units as u
from astropy.coordinates import SkyCoord

from app.models.motion import MotionVector
from app.models.source_detection import SourceDetection


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


def _sky_coord(detection: SourceDetection) -> SkyCoord:
    return SkyCoord(detection.ra * u.deg, detection.dec * u.deg, frame="icrs")
