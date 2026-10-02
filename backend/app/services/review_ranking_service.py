"""Built tracklets of one build → M1 review order (AS-041), pure functions.

Applies the AS-039 frozen ranker M1 exactly as AS-040 validated it
(sealed_validation.frozen_scores on the AS-038 feature table):

- inputs: the 8 frozen features of every BUILT tracklet, computed by the
  same code as the research tables (quality_service), floats at the
  table's 6-decimal precision;
- per feature, the oriented mid-rank percentile among the build's built
  tracklets (ties count half; missing → percentile 0);
- score = intercept + Σ weight_k · p_k in frozen feature order (the same
  floating-point operations as the research scorer).

The ranker never sees identification, SkyBoT, designation, known/unknown,
star proximity, speed or position angle. Nothing is filtered: every built
tracklet is returned in review order, every rejected tracklet unranked.
"""

import bisect
from collections.abc import Mapping, Sequence

from app.models.observation import Observation
from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG, PipelineConfig
from app.models.quality import SharpAvailability
from app.models.review_ranking import (
    M1FeatureEvidence,
    M1Features,
    M1Input,
    M1Spec,
    RankedCandidate,
    ReviewDirection,
    ReviewRanking,
    ReviewView,
    UnrankedTracklet,
)
from app.models.tracklet import Tracklet, TrackletStatus
from app.services.astrometry import track_window
from app.services.quality_service import (
    extract_quality_features,
    shared_detection_tracklets,
    sharp_abs_max,
)


# Frozen M1 (validation/results/as039/as039_frozen_ranker.json); a test
# checks these against the committed file. Never tuned here.
M1_INPUTS: tuple[tuple[str, int], ...] = (
    ("min_snr", 1),
    ("median_snr", 1),
    ("fit_rms_residual_arcsec", -1),
    ("magnitude_range_mag", -1),
    ("flagged_detection_count", -1),
    ("masked_detection_count", -1),
    ("sharp_abs_max", -1),
    ("shared_detection_tracklets", -1),
)
M1_WEIGHT = 0.125
M1_INTERCEPT = 0.0
MISSING_PERCENTILE = 0.0
# AS-038 feature-table precision (feature_evaluation._round).
FEATURE_DECIMALS = 6

# The validated unit (ranking_design: one quadrant-night, three exposures,
# EXPERIMENTAL_DEFAULT_CONFIG).
VALIDATED_FRAME_COUNT = 3

REJECTED_REASON = (
    "rejected by the tracklet fit (max residual above the configured "
    "limit); outside the M1 population (only built tracklets are ranked)"
)


def m1_spec() -> M1Spec:
    return M1Spec(
        inputs=[
            M1Input(feature=name, direction=direction, weight=M1_WEIGHT)
            for name, direction in M1_INPUTS
        ],
        intercept=M1_INTERCEPT,
        missing_percentile=MISSING_PERCENTILE,
    )


def m1_features(
    tracklets: Sequence[Tracklet],
    sharp_by_source_id: Mapping[str, float],
) -> list[tuple[M1Features, SharpAvailability]]:
    """The 8 M1 inputs of each built tracklet (same order as given).

    `tracklets` must be exactly the build's built tracklets: the shared-
    detection count is taken among them, as in the research tables.
    """
    if any(t.status is not TrackletStatus.TRACKLET_BUILT for t in tracklets):
        raise ValueError("M1 ranks built tracklets only")
    shared = shared_detection_tracklets(
        {t.tracklet_id: [d.detection.source_id for d in t.detections] for t in tracklets}
    )
    out = []
    for tracklet in tracklets:
        q = extract_quality_features(tracklet, sharp_by_source_id)
        complete = q.sharp_availability is SharpAvailability.COMPLETE
        features = M1Features(
            min_snr=_round(q.min_snr),
            median_snr=_round(q.median_snr),
            fit_rms_residual_arcsec=_round(q.fit_rms_residual_arcsec),
            magnitude_range_mag=_round(q.magnitude_range_mag),
            flagged_detection_count=q.flagged_detection_count,
            masked_detection_count=q.masked_detection_count,
            sharp_abs_max=_round(sharp_abs_max(q.sharp_values, complete)),
            shared_detection_tracklets=shared[tracklet.tracklet_id],
        )
        out.append((features, q.sharp_availability))
    return out


def oriented_percentiles(values: Sequence[float | None], direction: int) -> list[float | None]:
    """Mid-rank percentile in (0, 1] of each value among the present ones,
    oriented so that higher = reviewed earlier; ties count half; missing
    stays None (ranking_design.within_field_percentile)."""
    present = sorted(direction * v for v in values if v is not None)
    n = len(present)
    out: list[float | None] = []
    for v in values:
        if v is None:
            out.append(None)
            continue
        x = direction * v
        below = bisect.bisect_left(present, x)
        tied = bisect.bisect_right(present, x) - below
        out.append((below + 0.5 * tied) / n)
    return out


def m1_scores(
    features: Sequence[M1Features],
) -> tuple[list[float], list[list[M1FeatureEvidence]]]:
    """M1 score and per-feature evidence of each tracklet of one build."""
    totals = [M1_INTERCEPT] * len(features)
    evidence: list[list[M1FeatureEvidence]] = [[] for _ in features]
    for name, direction in M1_INPUTS:
        values = [getattr(f, name) for f in features]
        percentiles = oriented_percentiles(values, direction)
        for i, (value, p) in enumerate(zip(values, percentiles)):
            used = MISSING_PERCENTILE if p is None else p
            totals[i] = totals[i] + M1_WEIGHT * used
            evidence[i].append(
                M1FeatureEvidence(
                    feature=name,
                    direction=(
                        ReviewDirection.HIGHER_FIRST
                        if direction > 0
                        else ReviewDirection.LOWER_FIRST
                    ),
                    value=value,
                    percentile=p,
                    weight=M1_WEIGHT,
                    contribution=M1_WEIGHT * used,
                )
            )
    return totals, evidence


def review_order(scores: Sequence[float]) -> list[int]:
    """Indices by descending score; equal scores keep input order."""
    return sorted(range(len(scores)), key=lambda i: -scores[i])


def rank_for_review(
    tracklets: Sequence[Tracklet],
    sharp_by_source_id: Mapping[str, float],
    observations: Sequence[Observation],
    config: PipelineConfig = EXPERIMENTAL_DEFAULT_CONFIG,
) -> ReviewRanking:
    """Every tracklet of one build: built ones in M1 review order (all of
    them), then the rejected ones unranked, in build order.

    `tracklets` is the build's full tracklet list in build order (the tie
    order). `observations` and `config` only describe the build (frame
    sequence for the view, validated-domain notes); they are not inputs of
    the score.
    """
    product_ids = [o.product_id for o in observations]
    built = [t for t in tracklets if t.status is TrackletStatus.TRACKLET_BUILT]
    rejected = [t for t in tracklets if t.status is not TrackletStatus.TRACKLET_BUILT]

    featured = m1_features(built, sharp_by_source_id)
    scores, evidence = m1_scores([f for f, _ in featured])
    candidates = [
        RankedCandidate(
            review_rank=rank,
            tracklet_id=built[i].tracklet_id,
            review_priority_score=scores[i],
            evidence=evidence[i],
            sharp_availability=featured[i][1],
            tracklet=built[i],
            view=_view(built[i], product_ids),
        )
        for rank, i in enumerate(review_order(scores), start=1)
    ]
    unranked = [
        UnrankedTracklet(
            tracklet_id=t.tracklet_id,
            reason=REJECTED_REASON,
            tracklet=t,
            view=_view(t, product_ids),
        )
        for t in rejected
    ]
    return ReviewRanking(
        ranker=m1_spec(),
        domain_notes=domain_notes(observations, config, featured),
        candidates=candidates,
        unranked=unranked,
    )


def domain_notes(
    observations: Sequence[Observation],
    config: PipelineConfig,
    featured: Sequence[tuple[M1Features, SharpAvailability]] = (),
) -> list[str]:
    """Differences from the AS-040 validated unit (informational only)."""
    notes = []
    if len(observations) != VALIDATED_FRAME_COUNT:
        notes.append(
            f"{len(observations)} frames; M1 was validated on "
            f"{VALIDATED_FRAME_COUNT}-exposure sequences"
        )
    quadrants = {(o.field, o.ccd_id, o.quadrant_id) for o in observations}
    if len(quadrants) > 1:
        notes.append(
            "frames from more than one ZTF field/CCD/quadrant; M1 percentiles "
            "were validated within one quadrant-night"
        )
    nights = {o.observed_at.date() for o in observations}
    if len(nights) > 1:
        notes.append(
            "frames from more than one UTC night; M1 was validated within one "
            "quadrant-night"
        )
    if config != EXPERIMENTAL_DEFAULT_CONFIG:
        notes.append(
            "pipeline config differs from EXPERIMENTAL_DEFAULT_CONFIG, the "
            "config M1 was validated with"
        )
    missing_sharp = sum(1 for f, _ in featured if f.sharp_abs_max is None)
    if missing_sharp:
        notes.append(
            f"{missing_sharp} built tracklet(s) without a complete raw sharp: "
            "sharp_abs_max is missing and counts as percentile 0"
        )
    return notes


def _view(tracklet: Tracklet, product_ids: list[int]) -> ReviewView:
    center_ra, center_dec, size = track_window(
        [(d.detection.ra, d.detection.dec) for d in tracklet.detections]
    )
    return ReviewView(
        product_ids=product_ids,
        center_ra=center_ra,
        center_dec=center_dec,
        size_arcsec=size,
    )


def _round(value: float | None) -> float | None:
    return None if value is None else round(float(value), FEATURE_DECIMALS)
