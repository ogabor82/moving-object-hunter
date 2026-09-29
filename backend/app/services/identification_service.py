from collections.abc import Mapping, Sequence

import astropy.units as u
import httpx
import numpy
from astropy.coordinates import SkyCoord, angular_separation
from astropy.time import Time

from app.models.identification import (
    DetectionResidual,
    IdentificationConfig,
    IdentificationDiagnostics,
    IdentificationResult,
    IdentificationStatus,
    KnownObjectMatch,
    TrackletIdentification,
)
from app.models.known_object import KnownObjectEphemeris, KnownObjectField
from app.models.observation import Observation
from app.models.source_detection import SourceDetection
from app.models.tracklet import Tracklet
from app.services.skybot_service import ZTF_OBSERVATORY_CODE, query_known_objects


def identify_tracklets(
    tracklets: Sequence[Tracklet],
    observations: Sequence[Observation],
    config: IdentificationConfig,
    observer: str = ZTF_OBSERVATORY_CODE,
    client: httpx.Client | None = None,
) -> IdentificationResult:
    """Query SkyBoT once per frame and identify every tracklet.

    Each frame is queried at its mid-exposure epoch (UTC) over a cone that
    covers all tracklet detections plus the match radius. A SkyBoT failure
    raises SkyBoTServiceError; it is never reported as an unknown tracklet.
    """
    used_product_ids = {
        item.detection.observation_product_id
        for tracklet in tracklets
        for item in tracklet.detections
    }
    frames = [
        observation
        for observation in observations
        if observation.product_id in used_product_ids
    ]
    fields: dict[int, KnownObjectField] = {}
    if frames:
        center_ra, center_dec, radius_degrees = _covering_cone(
            tracklets, config.match_radius_arcsec
        )
        for observation in frames:
            fields[observation.product_id] = query_known_objects(
                center_ra,
                center_dec,
                radius_degrees,
                mid_exposure_jd_utc(observation),
                observer=observer,
                client=client,
            )
    return match_tracklets_to_known_objects(tracklets, fields, config)


def match_tracklets_to_known_objects(
    tracklets: Sequence[Tracklet],
    fields: Mapping[int, KnownObjectField],
    config: IdentificationConfig,
) -> IdentificationResult:
    """Compare observed tracklet positions with SkyBoT predictions.

    `fields` maps observation product id to the known objects predicted
    for that frame. A known object matches a tracklet when it is predicted
    within `match_radius_arcsec` of every detection. Status (05 – Scientific
    Validation): exactly one match -> KNOWN; several matches, or one whose
    ephemeris position error exceeds the match radius -> AMBIGUOUS; none ->
    UNKNOWN.
    """
    identifications = [
        _identify(tracklet, fields, config.match_radius_arcsec)
        for tracklet in tracklets
    ]
    statuses = [identification.status for identification in identifications]
    return IdentificationResult(
        config=config,
        fields=list(fields.values()),
        identifications=identifications,
        diagnostics=IdentificationDiagnostics(
            tracklet_count=len(identifications),
            known_count=statuses.count(IdentificationStatus.KNOWN),
            unknown_count=statuses.count(IdentificationStatus.UNKNOWN),
            ambiguous_count=statuses.count(IdentificationStatus.AMBIGUOUS),
            known_objects_per_frame=[
                len(field.objects) for field in fields.values()
            ],
        ),
    )


def mid_exposure_jd_utc(observation: Observation) -> float:
    """Julian Day (UTC scale) of the observation's mid-exposure time."""
    return float(Time(observation.mid_exposure_at, scale="utc").jd)


def _identify(
    tracklet: Tracklet,
    fields: Mapping[int, KnownObjectField],
    match_radius_arcsec: float,
) -> TrackletIdentification:
    missing = {
        item.detection.observation_product_id
        for item in tracklet.detections
        if item.detection.observation_product_id not in fields
    }
    if missing:
        raise ValueError(
            f"No known-object field for observation(s) {sorted(missing)} of "
            f"tracklet {tracklet.tracklet_id}."
        )

    candidates = sorted(
        _candidate_matches(tracklet, fields, match_radius_arcsec),
        key=lambda match: (match.max_residual_arcsec, match.rms_residual_arcsec),
    )

    if not candidates:
        status = IdentificationStatus.UNKNOWN
        reason = (
            "no known object predicted within "
            f"{match_radius_arcsec} arcsec of every detection"
        )
    elif len(candidates) > 1:
        status = IdentificationStatus.AMBIGUOUS
        reason = (
            f"{len(candidates)} known objects within {match_radius_arcsec} "
            "arcsec of every detection"
        )
    elif candidates[0].position_error_arcsec > match_radius_arcsec:
        status = IdentificationStatus.AMBIGUOUS
        reason = (
            f"ephemeris position error {candidates[0].position_error_arcsec} "
            f"arcsec exceeds the match radius {match_radius_arcsec} arcsec"
        )
    else:
        status = IdentificationStatus.KNOWN
        reason = (
            f"single known object within {match_radius_arcsec} arcsec "
            "of every detection"
        )

    return TrackletIdentification(
        tracklet_id=tracklet.tracklet_id,
        tracklet_status=tracklet.status,
        status=status,
        status_reason=reason,
        best_match=candidates[0] if candidates else None,
        candidate_matches=candidates,
    )


def _candidate_matches(
    tracklet: Tracklet,
    fields: Mapping[int, KnownObjectField],
    match_radius_arcsec: float,
) -> list[KnownObjectMatch]:
    """Known objects in every detection's frame and within the radius of each.

    Residuals of all common objects are computed at once with numpy; model
    objects are built only for the (few) matches.
    """
    per_frame = [
        {
            ephemeris.designation: ephemeris
            for ephemeris in fields[item.detection.observation_product_id].objects
        }
        for item in tracklet.detections
    ]
    common = sorted(set.intersection(*(set(frame) for frame in per_frame)))
    if not common:
        return []

    # residual_table[detection, object] in arcsec.
    residual_table = numpy.array(
        [
            _separations_arcsec(
                item.detection,
                [frame[designation] for designation in common],
            )
            for item, frame in zip(tracklet.detections, per_frame)
        ]
    )
    within = numpy.flatnonzero(
        residual_table.max(axis=0) <= match_radius_arcsec
    )

    matches = []
    for column in within:
        designation = common[column]
        ephemerides = [frame[designation] for frame in per_frame]
        values = residual_table[:, column]
        residuals = [
            _residual(item.detection, ephemeris, fields, float(value))
            for item, ephemeris, value in zip(
                tracklet.detections, ephemerides, values
            )
        ]
        reference = ephemerides[0]
        matches.append(
            KnownObjectMatch(
                designation=designation,
                name=reference.name,
                object_class=reference.object_class,
                v_magnitude=reference.v_magnitude,
                position_error_arcsec=max(
                    ephemeris.position_error_arcsec for ephemeris in ephemerides
                ),
                residuals=residuals,
                rms_residual_arcsec=float(numpy.sqrt(numpy.mean(values**2))),
                max_residual_arcsec=float(values.max()),
            )
        )
    return matches


def _separations_arcsec(
    detection: SourceDetection,
    ephemerides: Sequence[KnownObjectEphemeris],
) -> numpy.ndarray:
    """Great-circle distances (Vincenty) from a detection to predictions."""
    return (
        numpy.rad2deg(
            angular_separation(
                numpy.deg2rad(detection.ra),
                numpy.deg2rad(detection.dec),
                numpy.deg2rad([e.predicted_ra for e in ephemerides]),
                numpy.deg2rad([e.predicted_dec for e in ephemerides]),
            )
        )
        * 3600.0
    )


def _residual(
    detection: SourceDetection,
    ephemeris: KnownObjectEphemeris,
    fields: Mapping[int, KnownObjectField],
    residual_arcsec: float,
) -> DetectionResidual:
    return DetectionResidual(
        observation_product_id=detection.observation_product_id,
        epoch_jd_utc=fields[detection.observation_product_id].epoch_jd_utc,
        observed_ra=detection.ra,
        observed_dec=detection.dec,
        predicted_ra=ephemeris.predicted_ra,
        predicted_dec=ephemeris.predicted_dec,
        residual_arcsec=residual_arcsec,
    )


def _covering_cone(
    tracklets: Sequence[Tracklet],
    margin_arcsec: float,
) -> tuple[float, float, float]:
    """Center and radius (deg) of a cone covering all tracklet detections."""
    coords = SkyCoord(
        [item.detection.ra for tracklet in tracklets for item in tracklet.detections]
        * u.deg,
        [item.detection.dec for tracklet in tracklets for item in tracklet.detections]
        * u.deg,
    )
    mean = coords.cartesian.xyz.mean(axis=1)
    center = SkyCoord(
        x=mean[0], y=mean[1], z=mean[2], representation_type="cartesian"
    )
    center = SkyCoord(center.spherical.lon, center.spherical.lat)
    radius = coords.separation(center).max() + margin_arcsec * u.arcsec
    return (
        float(center.ra.wrap_at(360 * u.deg).deg) % 360.0,
        float(center.dec.deg),
        float(radius.to_value(u.deg)),
    )
