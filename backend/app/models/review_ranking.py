"""Review-priority ranking of built tracklets with the validated M1 (AS-041).

M1 orders candidates for human review. It is not a classifier: its score is
not a probability, confidence or likelihood that a tracklet is a real or a
new object, no candidate is filtered, hidden or rejected because of it, and
there is no cutoff (the AS-040 "top 5 %" is an evaluation metric, never a
rejection rule). Frozen specification:
validation/results/as039/as039_frozen_ranker.json; validation:
validation/results/as040/as040_findings.md.
"""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.quality import SharpAvailability
from app.models.tracklet import Tracklet


class M1Features(BaseModel):
    """The 8 frozen M1 inputs of one built tracklet, nothing else.

    Values use the AS-038 feature-table precision (floats rounded to 6
    decimals). Only `sharp_abs_max` can be missing (null): when the raw
    `sharp` is not finite for every detection.
    """

    model_config = ConfigDict(allow_inf_nan=False, frozen=True)

    min_snr: float = Field(description="min SourceDetection.snr")
    median_snr: float = Field(description="median SourceDetection.snr")
    fit_rms_residual_arcsec: float = Field(description="Tracklet fit RMS [arcsec]")
    magnitude_range_mag: float = Field(description="max - min magnitude [mag]")
    flagged_detection_count: int = Field(description="detections on edge or masked")
    masked_detection_count: int = Field(description="detections with mask bits")
    sharp_abs_max: float | None = Field(
        description="max |raw ZTF PSF sharp|; null unless sharp is complete"
    )
    shared_detection_tracklets: int = Field(
        description="other built tracklets of the build sharing a detection"
    )


class ReviewDirection(StrEnum):
    HIGHER_FIRST = "higher_reviewed_first"
    LOWER_FIRST = "lower_reviewed_first"


class M1FeatureEvidence(BaseModel):
    """How one feature placed the tracklet within its build."""

    feature: str
    direction: ReviewDirection
    value: float | None = Field(description="feature value; null = missing")
    percentile: float | None = Field(
        description=(
            "oriented mid-rank percentile among the build's built tracklets "
            "(higher = reviewed earlier; ties count half); null when the "
            "value is missing"
        )
    )
    weight: float
    contribution: float = Field(
        description="weight * percentile, with a missing percentile counted as 0"
    )


class ReviewView(BaseModel):
    """What the blink comparator / overlay needs to open the candidate:
    the build's frame sequence and a cutout window around the track (same
    centre and size rule as the blink presets). The detections' sky
    positions per frame are in `tracklet.detections`."""

    product_ids: list[int] = Field(description="frames of the build, time order")
    center_ra: float = Field(ge=0.0, lt=360.0)
    center_dec: float = Field(ge=-90.0, le=90.0)
    size_arcsec: float = Field(gt=0.0)


class RankedCandidate(BaseModel):
    """One built tracklet in M1 review order."""

    review_rank: int = Field(
        ge=1, description="1 = review first; a position in the order, not a grade"
    )
    tracklet_id: str
    review_priority_score: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "M1 score: equal-weight (0.125) sum of the 8 oriented percentiles. "
            "Orders review only; NOT a probability or confidence that the "
            "tracklet is a real or new object, and no value of it is a cutoff."
        ),
    )
    evidence: list[M1FeatureEvidence] = Field(
        description="the 8 M1 inputs in frozen order"
    )
    sharp_availability: SharpAvailability
    tracklet: Tracklet = Field(description="detections, motion and fit")
    view: ReviewView


class UnrankedTracklet(BaseModel):
    """A tracklet outside the M1 population, still returned in full."""

    tracklet_id: str
    reason: str
    tracklet: Tracklet
    view: ReviewView


class M1Input(BaseModel):
    feature: str
    direction: Literal[1, -1]
    weight: float


class M1Spec(BaseModel):
    """The frozen ranker as the production scorer applies it."""

    ranker: Literal["M1"] = "M1"
    source: str = (
        "AS-039 frozen ranker (as039_frozen_ranker.json), "
        "AS-040 sealed validation: USEFUL, PROTECTED"
    )
    inputs: list[M1Input]
    intercept: float
    missing_percentile: float
    percentile_population: str = (
        "every built tracklet of the build (one ZTF quadrant-night); "
        "rejected tracklets are not ranked"
    )
    tie_order: str = (
        "equal scores keep the build's tracklet order (deterministic)"
    )


class ReviewSemantics(BaseModel):
    """Machine-readable statement of what the ranking is and is not."""

    purpose: Literal["review_priority_only"] = "review_priority_only"
    is_classifier: Literal[False] = False
    score_is_probability: Literal[False] = False
    candidates_filtered: Literal[False] = False
    complete: Literal[True] = Field(
        default=True,
        description="every tracklet of the build is returned (ranked or unranked)",
    )
    statement: str = (
        "Rank orders human review only. M1 is not a classifier and its score "
        "is not a probability or confidence. Low-ranked candidates are "
        "returned and remain reviewable; no score, rank, top-k / top-5 % "
        "cut, mask or flag state, faintness or star proximity removes a "
        "candidate. Identity (SkyBoT, designation, known/unknown) and "
        "bright-star proximity are not ranker inputs."
    )
    known_limitations: list[str] = [
        "Faint objects rank lower: AS-040 recall@5 % MARGINAL 0.870 vs "
        "PRIMARY 0.977 (interval excludes 0).",
        "Objects close to bright stars rank lower: AS-040 zone 0.786 vs "
        "control 0.940 (n = 14, passed by one object); mask / flag features "
        "act partly as a proximity proxy.",
        "The top of the order is mostly bright-light artefacts and crowded-"
        "field mislinks (AS-040 F3: 20/20 shortlist background strips).",
        "fit_rms_residual_arcsec partly restates the known-object selection, "
        "so recall for real unknown objects may be lower than for known ones.",
        "Validated on 3-exposure ZTF quadrant-nights with the experimental "
        "default config, main-belt dominated, <= 1\"/min.",
    ]


class ReviewRanking(BaseModel):
    """Every tracklet of one build: built ones in M1 review order, then the
    rejected ones (unranked)."""

    ranker: M1Spec
    semantics: ReviewSemantics = ReviewSemantics()
    domain_notes: list[str] = Field(
        description=(
            "how this build differs from the validated unit; empty when it "
            "matches. Informational: nothing is filtered because of it."
        )
    )
    candidates: list[RankedCandidate]
    unranked: list[UnrankedTracklet]
