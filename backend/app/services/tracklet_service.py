import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations

import astropy.units as u
import numpy
from astropy.coordinates import SkyCoord

from app.models.matching import CandidateFrame
from app.models.tracklet import (
    Tracklet,
    TrackletBuildConfig,
    TrackletBuildDiagnostics,
    TrackletBuildResult,
    TrackletDetection,
    TrackletStatus,
)
from app.services.astrometry import find_pairs_within


# Seed pairs are extended in chunks to bound memory use.
SEED_CHUNK_SIZE = 200_000


@dataclass(frozen=True)
class TrackletFit:
    """Constant-rate linear motion fit of a tracklet's detections."""

    angular_velocity_arcsec_per_min: float
    position_angle_deg: float
    rms_residual_arcsec: float
    max_residual_arcsec: float


def build_tracklets(
    frames: Sequence[CandidateFrame],
    config: TrackletBuildConfig,
) -> TrackletBuildResult:
    """Link moving-source candidates across frames into tracklets.

    Every pair of candidates from two frames whose implied rate is at most
    `max_rate_arcsec_per_min` is a seed. The seed's motion is extrapolated
    at constant rate along its great circle (as in predict_position) to
    every other frame, and the nearest candidate within
    `search_radius_arcsec` is linked. Seeds reaching `min_detections` become
    tracklets; exact duplicates and strict subsets are then removed.
    """
    times = [frame.observation.observed_at for frame in frames]
    if any(later <= earlier for earlier, later in zip(times, times[1:])):
        raise ValueError("Frames must be in strictly increasing time order.")

    ra = [
        numpy.array([candidate.ra for candidate in frame.candidates], dtype=float)
        for frame in frames
    ]
    dec = [
        numpy.array([candidate.dec for candidate in frame.candidates], dtype=float)
        for frame in frames
    ]
    minutes = [(time - times[0]).total_seconds() / 60.0 for time in times]

    linked: list[tuple[tuple[int, int], ...]] = []
    seed_pairs = 0
    ambiguous_extensions = 0

    for first, second in combinations(range(len(frames)), 2):
        seed_minutes = minutes[second] - minutes[first]
        seed_first, seed_second, seed_separation = find_pairs_within(
            ra[first],
            dec[first],
            ra[second],
            dec[second],
            config.max_rate_arcsec_per_min * seed_minutes,
        )
        seed_pairs += len(seed_first)

        for start in range(0, len(seed_first), SEED_CHUNK_SIZE):
            chunk = slice(start, start + SEED_CHUNK_SIZE)
            members, ambiguous = _extend_seeds(
                ra,
                dec,
                minutes,
                first,
                second,
                seed_first[chunk],
                seed_second[chunk],
                seed_separation[chunk],
                config.search_radius_arcsec,
            )
            ambiguous_extensions += ambiguous
            linked.extend(
                tracklet_members
                for tracklet_members in members
                if len(tracklet_members) >= config.min_detections
            )

    unique = set(linked)
    maximal = _remove_subsets(unique)
    maximal.sort(key=lambda members: (members[0][0], members[0][1], members))

    tracklets = [
        _make_tracklet(
            f"trk-{number:04d}",
            [
                TrackletDetection(
                    time=times[frame_index],
                    detection=frames[frame_index].candidates[candidate_index],
                )
                for frame_index, candidate_index in members
            ],
            config.max_residual_arcsec,
        )
        for number, members in enumerate(maximal, start=1)
    ]
    usage = Counter(member for members in maximal for member in members)

    return TrackletBuildResult(
        config=config,
        tracklets=tracklets,
        diagnostics=TrackletBuildDiagnostics(
            frame_count=len(frames),
            candidate_counts=[len(frame.candidates) for frame in frames],
            seed_pairs=seed_pairs,
            linked_before_dedup=len(linked),
            duplicates_removed=len(linked) - len(unique),
            subsets_removed=len(unique) - len(maximal),
            ambiguous_extensions=ambiguous_extensions,
            tracklet_count=len(tracklets),
            rejected_tracklet_count=sum(
                1
                for tracklet in tracklets
                if tracklet.status is TrackletStatus.REJECTED
            ),
            detections_in_multiple_tracklets=sum(
                1 for count in usage.values() if count > 1
            ),
        ),
    )


def fit_tracklet_motion(detections: Sequence[TrackletDetection]) -> TrackletFit:
    """Least-squares constant-rate fit in offsets around detection 0.

    Offsets are Astropy SkyOffsetFrame coordinates centred on the first
    detection (east, north in arcsec; flat to well below 0.01 arcsec over
    tracklet scales of arcminutes). East(t) and north(t) are fitted with
    straight lines; residuals are distances from the fitted positions.
    """
    if len(detections) < 3:
        raise ValueError("A tracklet fit needs at least three detections.")

    coords = SkyCoord(
        [item.detection.ra for item in detections] * u.deg,
        [item.detection.dec for item in detections] * u.deg,
    )
    offsets = coords.transform_to(coords[0].skyoffset_frame())
    east = offsets.lon.wrap_at(180 * u.deg).to_value(u.arcsec)
    north = offsets.lat.to_value(u.arcsec)
    minutes = numpy.array(
        [
            (item.time - detections[0].time).total_seconds() / 60.0
            for item in detections
        ]
    )

    east_rate, east_start = numpy.polyfit(minutes, east, 1)
    north_rate, north_start = numpy.polyfit(minutes, north, 1)
    residuals = numpy.hypot(
        east - (east_start + east_rate * minutes),
        north - (north_start + north_rate * minutes),
    )
    position_angle = math.degrees(math.atan2(east_rate, north_rate)) % 360.0

    return TrackletFit(
        angular_velocity_arcsec_per_min=float(math.hypot(east_rate, north_rate)),
        position_angle_deg=0.0 if position_angle >= 360.0 else position_angle,
        rms_residual_arcsec=float(numpy.sqrt(numpy.mean(residuals**2))),
        max_residual_arcsec=float(residuals.max()),
    )


def _make_tracklet(
    tracklet_id: str,
    detections: list[TrackletDetection],
    max_residual_arcsec: float,
) -> Tracklet:
    fit = fit_tracklet_motion(detections)
    is_poor_fit = fit.max_residual_arcsec > max_residual_arcsec
    return Tracklet(
        tracklet_id=tracklet_id,
        detections=detections,
        angular_velocity_arcsec_per_min=fit.angular_velocity_arcsec_per_min,
        position_angle_deg=fit.position_angle_deg,
        fit_rms_residual_arcsec=fit.rms_residual_arcsec,
        fit_max_residual_arcsec=fit.max_residual_arcsec,
        status=(
            TrackletStatus.REJECTED if is_poor_fit else TrackletStatus.TRACKLET_BUILT
        ),
        status_reason=(
            f"max fit residual {fit.max_residual_arcsec:.2f} arcsec exceeds "
            f"{max_residual_arcsec} arcsec"
            if is_poor_fit
            else None
        ),
    )


def _remove_subsets(
    unique: set[tuple[tuple[int, int], ...]],
) -> list[tuple[tuple[int, int], ...]]:
    """Drop member sets that are strict subsets of another member set."""
    containing: dict[tuple[int, int], list[frozenset[tuple[int, int]]]] = {}
    for members in unique:
        member_set = frozenset(members)
        for member in members:
            containing.setdefault(member, []).append(member_set)

    return [
        members
        for members in unique
        if not any(
            frozenset(members) < other for other in containing[members[0]]
        )
    ]


def _extend_seeds(
    ra: list[numpy.ndarray],
    dec: list[numpy.ndarray],
    minutes: list[float],
    first: int,
    second: int,
    seed_first: numpy.ndarray,
    seed_second: numpy.ndarray,
    seed_separation: numpy.ndarray,
    search_radius_arcsec: float,
) -> tuple[list[tuple[tuple[int, int], ...]], int]:
    """Extend seed pairs into every other frame.

    Returns, per seed, its time-ordered (frame index, candidate index)
    members, and the number of extensions with more than one candidate
    inside the search radius.
    """
    seed_count = len(seed_first)
    if seed_count == 0:
        return [], 0

    start = SkyCoord(ra[first][seed_first] * u.deg, dec[first][seed_first] * u.deg)
    end = SkyCoord(
        ra[second][seed_second] * u.deg, dec[second][seed_second] * u.deg
    )
    heading = end.position_angle(start) + 180 * u.deg
    seed_minutes = minutes[second] - minutes[first]

    extensions: dict[int, numpy.ndarray] = {
        first: seed_first,
        second: seed_second,
    }
    ambiguous = 0
    for other in range(len(ra)):
        if other in (first, second) or len(ra[other]) == 0:
            continue
        offset = seed_separation * (minutes[other] - minutes[second]) / seed_minutes
        predicted = end.directional_offset_by(heading, offset * u.arcsec)
        seed_index, candidate_index, distance = find_pairs_within(
            predicted.ra.wrap_at(360 * u.deg).deg,
            predicted.dec.deg,
            ra[other],
            dec[other],
            search_radius_arcsec,
        )
        nearest = numpy.full(seed_count, -1, dtype=numpy.intp)
        if len(seed_index):
            order = numpy.lexsort((distance, seed_index))
            seed_index = seed_index[order]
            candidate_index = candidate_index[order]
            is_first = numpy.ones(len(seed_index), dtype=bool)
            is_first[1:] = seed_index[1:] != seed_index[:-1]
            nearest[seed_index[is_first]] = candidate_index[is_first]
            ambiguous += int(
                numpy.count_nonzero(numpy.bincount(seed_index) > 1)
            )
        extensions[other] = nearest

    frame_order = sorted(extensions)
    members = [
        tuple(
            (frame_index, int(extensions[frame_index][seed]))
            for frame_index in frame_order
            if extensions[frame_index][seed] >= 0
        )
        for seed in range(seed_count)
    ]
    return members, ambiguous
