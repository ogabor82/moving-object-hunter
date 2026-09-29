"""Pre-registered selection of known-object validation targets."""

import math

import astropy.units as u
from astropy.coordinates import SkyCoord

from app.models.known_object import KnownObjectEphemeris, KnownObjectField
from app.validation.models import (
    FrameMetadata,
    TargetSelectionRule,
    ValidationTarget,
)


def select_targets(
    field_id: str,
    frame_metadata: list[FrameMetadata],
    skybot_fields: list[KnownObjectField],
    rule: TargetSelectionRule,
    control_designations: frozenset[str] = frozenset(),
) -> list[ValidationTarget]:
    """Known objects expected in every frame, from predictions only.

    An object qualifies when SkyBoT lists it for every frame, its predicted
    position lies inside every frame's quadrant footprint, its position
    error is at most `max_position_error_arcsec`, and its V magnitude is
    bright enough relative to the faintest frame's 5-sigma maglimit.
    Pipeline results are never consulted. Designations in
    `control_designations` bypass the brightness and position-error cuts
    (not the coverage/footprint check) and get role "control".
    """
    min_maglimit = min(frame.maglimit for frame in frame_metadata)
    per_frame = [
        {ephemeris.designation: ephemeris for ephemeris in field.objects}
        for field in skybot_fields
    ]
    common = set.intersection(*(set(frame) for frame in per_frame))

    targets = []
    for designation in sorted(common):
        ephemerides = [frame[designation] for frame in per_frame]
        first = ephemerides[0]
        if first.v_magnitude is None:
            continue
        if not all(
            inside_footprint(e.predicted_ra, e.predicted_dec, frame)
            for e, frame in zip(ephemerides, frame_metadata)
        ):
            continue
        if designation in control_designations:
            role = "control"
        elif max(e.position_error_arcsec for e in ephemerides) > (
            rule.max_position_error_arcsec
        ):
            continue
        elif first.v_magnitude <= min_maglimit - rule.primary_margin_mag:
            role = "primary"
        elif first.v_magnitude <= min_maglimit + rule.marginal_margin_mag:
            role = "marginal"
        else:
            continue
        rate, angle = predicted_motion(first)
        targets.append(
            ValidationTarget(
                field_id=field_id,
                designation=designation,
                name=first.name,
                object_class=first.object_class,
                role=role,
                v_magnitude=first.v_magnitude,
                position_error_arcsec=max(
                    e.position_error_arcsec for e in ephemerides
                ),
                predicted_rate_arcsec_per_min=rate,
                predicted_position_angle_deg=angle,
                predicted_positions=[
                    (e.predicted_ra, e.predicted_dec) for e in ephemerides
                ],
            )
        )
    return targets


def predicted_motion(ephemeris: KnownObjectEphemeris) -> tuple[float, float]:
    """SkyBoT apparent motion as (arcsec/min, position angle east of north)."""
    east = ephemeris.motion_ra_cos_dec_arcsec_per_hour
    north = ephemeris.motion_dec_arcsec_per_hour
    rate = math.hypot(east, north) / 60.0
    angle = math.degrees(math.atan2(east, north)) % 360.0
    return rate, angle


def inside_footprint(ra: float, dec: float, frame: FrameMetadata) -> bool:
    """Point-in-quadrilateral test in sky offsets around the frame center."""
    center = SkyCoord(frame.center_ra * u.deg, frame.center_dec * u.deg)
    offset_frame = center.skyoffset_frame()

    def project(point_ra: float, point_dec: float) -> tuple[float, float]:
        offset = SkyCoord(point_ra * u.deg, point_dec * u.deg).transform_to(
            offset_frame
        )
        return (
            float(offset.lon.wrap_at(180 * u.deg).deg),
            float(offset.lat.deg),
        )

    x, y = project(ra, dec)
    polygon = [project(*corner) for corner in frame.corners]
    inside = False
    for (x1, y1), (x2, y2) in zip(polygon, polygon[1:] + polygon[:1]):
        if (y1 > y) != (y2 > y):
            crossing = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < crossing:
                inside = not inside
    return inside
