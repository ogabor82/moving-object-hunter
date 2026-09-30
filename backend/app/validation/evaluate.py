"""Evaluate the unchanged pipeline on a loaded validation field."""

from collections.abc import Sequence

from app.models.frame_sources import FrameSources
from app.models.identification import (
    IdentificationStatus,
    TrackletIdentification,
)
from app.models.known_object import KnownObjectField
from app.models.matching import CandidateFrame
from app.models.tracklet import Tracklet, TrackletStatus
from app.services.astrometry import find_pairs_within
from app.services.identification_service import match_tracklets_to_known_objects
from app.services.matching_service import (
    extract_moving_candidates,
    match_stationary_sources,
)
from app.services.quality_service import extract_quality_features
from app.services.tracklet_service import build_tracklets
from app.validation.models import (
    FieldRunResult,
    PipelineConfig,
    TargetOutcome,
    TrackletFeatures,
    ValidationTarget,
)
from app.validation.selection import predicted_motion


# Radius for the config-independent "nearest detection" diagnostic.
NEAREST_DETECTION_RADIUS_ARCSEC = 10.0


def evaluate_field(
    field_id: str,
    frames: Sequence[FrameSources],
    skybot_fields: Sequence[KnownObjectField],
    targets: Sequence[ValidationTarget],
    config: PipelineConfig,
    sharp_by_source_id: dict[str, float] | None = None,
) -> FieldRunResult:
    """Run stationary matching, tracklet building and identification.

    Frames and SkyBoT fields must be aligned and in time order. A target is
    recovered when a tracklet is identified as KNOWN with the target as
    best match.
    """
    candidates = extract_moving_candidates(
        match_stationary_sources(frames, config.stationary_matching())
    )
    tracklets = build_tracklets(candidates, config.tracklet_build()).tracklets
    fields_by_product_id = {
        frame.observation.product_id: field
        for frame, field in zip(frames, skybot_fields)
    }
    identifications = match_tracklets_to_known_objects(
        tracklets,
        fields_by_product_id,
        config.identification(),
    ).identifications

    target_designations = {target.designation for target in targets}
    features = [
        _tracklet_features(
            tracklet,
            identification,
            skybot_fields[0],
            target_designations,
            sharp_by_source_id or {},
        )
        for tracklet, identification in zip(tracklets, identifications)
    ]
    outcomes = [
        _target_outcome(
            target, frames, candidates, tracklets, identifications, config
        )
        for target in targets
    ]
    statuses = [identification.status for identification in identifications]

    def counts(role: str) -> tuple[int, int]:
        selected = [outcome for outcome in outcomes if outcome.role == role]
        return len(selected), sum(outcome.recovered for outcome in selected)

    primary, primary_recovered = counts("primary")
    marginal, marginal_recovered = counts("marginal")
    control, control_recovered = counts("control")
    built = sum(t.status is TrackletStatus.TRACKLET_BUILT for t in tracklets)
    return FieldRunResult(
        field_id=field_id,
        config=config,
        candidate_counts=[frame.candidate_count for frame in candidates],
        tracklet_count=len(tracklets),
        built_count=built,
        rejected_count=len(tracklets) - built,
        known_count=statuses.count(IdentificationStatus.KNOWN),
        unknown_count=statuses.count(IdentificationStatus.UNKNOWN),
        ambiguous_count=statuses.count(IdentificationStatus.AMBIGUOUS),
        unknown_built_count=sum(
            identification.status is IdentificationStatus.UNKNOWN
            and tracklet.status is TrackletStatus.TRACKLET_BUILT
            for tracklet, identification in zip(tracklets, identifications)
        ),
        primary_targets=primary,
        primary_recovered=primary_recovered,
        marginal_targets=marginal,
        marginal_recovered=marginal_recovered,
        control_targets=control,
        control_recovered=control_recovered,
        targets=outcomes,
        tracklets=features,
    )


def _target_outcome(
    target: ValidationTarget,
    frames: Sequence[FrameSources],
    candidates: Sequence[CandidateFrame],
    tracklets: Sequence[Tracklet],
    identifications: Sequence[TrackletIdentification],
    config: PipelineConfig,
) -> TargetOutcome:
    nearest: list[float | None] = []
    candidate_frames = 0
    for frame, candidate_frame, (ra, dec) in zip(
        frames, candidates, target.predicted_positions
    ):
        distance, source_id = _nearest(
            ra, dec, frame.detections, NEAREST_DETECTION_RADIUS_ARCSEC
        )
        nearest.append(distance)
        if distance is not None and distance <= config.match_radius_arcsec:
            candidate_ids = {c.source_id for c in candidate_frame.candidates}
            candidate_frames += source_id in candidate_ids

    matches = [
        (tracklet, identification)
        for tracklet, identification in zip(tracklets, identifications)
        if identification.best_match is not None
        and identification.best_match.designation == target.designation
    ]
    # Prefer an accepted fit, then the smallest identification residual.
    matches.sort(
        key=lambda pair: (
            pair[0].status is not TrackletStatus.TRACKLET_BUILT,
            pair[1].best_match.max_residual_arcsec,
        )
    )
    best = matches[0] if matches else None
    return TargetOutcome(
        designation=target.designation,
        role=target.role,
        nearest_detection_arcsec=nearest,
        detected_frames=sum(
            distance is not None and distance <= config.match_radius_arcsec
            for distance in nearest
        ),
        candidate_frames=candidate_frames,
        recovered=best is not None
        and best[1].status is IdentificationStatus.KNOWN,
        identification_status=best[1].status if best else None,
        tracklet_id=best[0].tracklet_id if best else None,
        tracklet_status=best[0].status if best else None,
        max_residual_arcsec=best[1].best_match.max_residual_arcsec
        if best
        else None,
    )


def _nearest(
    ra: float,
    dec: float,
    detections: Sequence,
    radius_arcsec: float,
) -> tuple[float | None, str | None]:
    _, indices, distances = find_pairs_within(
        [ra],
        [dec],
        [detection.ra for detection in detections],
        [detection.dec for detection in detections],
        radius_arcsec,
    )
    if len(indices) == 0:
        return None, None
    best = int(distances.argmin())
    return float(distances[best]), detections[int(indices[best])].source_id


def _tracklet_features(
    tracklet: Tracklet,
    identification: TrackletIdentification,
    first_field: KnownObjectField,
    target_designations: set[str],
    sharp_by_source_id: dict[str, float],
) -> TrackletFeatures:
    quality = extract_quality_features(tracklet, sharp_by_source_id)
    designation = (
        identification.best_match.designation
        if identification.best_match
        else None
    )
    predicted_rate = predicted_angle = rate_difference = angle_difference = None
    ephemeris = next(
        (e for e in first_field.objects if e.designation == designation), None
    )
    if ephemeris is not None:
        predicted_rate, predicted_angle = predicted_motion(ephemeris)
        rate_difference = tracklet.angular_velocity_arcsec_per_min - predicted_rate
        angle_difference = (
            tracklet.position_angle_deg - predicted_angle + 180.0
        ) % 360.0 - 180.0
    return TrackletFeatures(
        tracklet_id=tracklet.tracklet_id,
        tracklet_status=tracklet.status,
        identification_status=identification.status,
        known_designation=designation,
        is_validation_target=designation in target_designations,
        min_snr=quality.min_snr,
        median_snr=quality.median_snr,
        magnitude_spread=quality.magnitude_range_mag,
        flagged_detections=quality.flagged_detection_count,
        sharp_values=quality.sharp_values,
        rate_arcsec_per_min=tracklet.angular_velocity_arcsec_per_min,
        position_angle_deg=tracklet.position_angle_deg,
        fit_rms_residual_arcsec=tracklet.fit_rms_residual_arcsec,
        fit_max_residual_arcsec=tracklet.fit_max_residual_arcsec,
        predicted_rate_arcsec_per_min=predicted_rate,
        predicted_position_angle_deg=predicted_angle,
        rate_difference_arcsec_per_min=rate_difference,
        position_angle_difference_deg=angle_difference,
    )
