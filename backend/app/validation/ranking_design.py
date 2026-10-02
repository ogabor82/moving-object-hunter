"""AS-037: candidate-ranking experiment design and pre-registration.

Design only. No ranking model, score, threshold, filter, exclusion radius,
rejection rule or candidate policy is built or applied here, and no ranking
outcome is computed. The module fixes, before any ranking outcome exists:

- the evaluation population and the frozen development / validation split
  of the 80 existing quadrant-nights (AS-034 R, AS-035 N, AS-036 C);
- the positive-control rule (recovered AS-022-rule known objects) and the
  label of every other tracklet;
- the ranking metrics (background-rank fraction, recall at a review
  fraction / budget, enrichment, within-field AUC) with duplicate weights
  and group (cluster) bootstrap intervals;
- the protection guards (near-star zone, faint objects) and the decision
  rule applied once to the validation split;
- the split guard that keeps the validation quadrant-nights sealed until a
  ranker is frozen.

Design document: validation/results/as037/as037_preregistration.md.

    python -m app.validation.ranking_design manifest \\
        --out validation/results/as037/as037_manifest.json
"""

import argparse
import bisect
import hashlib
import json
import math
import random
import re
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from app.validation.near_star_confirmation import newcombe

# ---------------------------------------------------------------------------
# PRE-REGISTRATION (AS-037, 2026-10-02; committed before any ranking
# feature table, ranking score or ranking outcome exists for any split)
# ---------------------------------------------------------------------------

SALT = "AS-037"

# --- Evaluation population ---
# Unit: one quadrant-night (three exposures, unchanged pipeline,
# EXPERIMENTAL_DEFAULT_CONFIG). Ranked list: every BUILT tracklet of the
# quadrant-night (rejected tracklets are never ranked), identity-blind:
# the ranker sees no identification output, SkyBoT prediction, designation
# or residual against a known object.
# Sources (frozen, no new search): AS-034 R (26 quadrants), AS-035 N (24),
# AS-036 C (30). SkyBoT predictions are replayed from the stored snapshots.
POPULATION_FILES = {
    "R": "validation/results/as034/as034_population.json",
    "N": "validation/results/as035/as035_selection.json",
    "C": "validation/results/as036/as036_selection.json",
}
TRACE_FILES = {
    "R": "validation/results/as035/as035_traces_R.json",
    "N": "validation/results/as035/as035_traces_N.json",
    "C": "validation/results/as036/as036_traces_C.json",
}
STAR_FILE_R = "validation/results/as033/as033_fields.json"

# --- Independence groups and split ---
# Quadrant-nights are linked (union-find) when they share (a) the UTC
# night, (b) a search / selection star, or (c) the ZTF field with nights at
# most LINK_SAME_FIELD_DAYS apart (same sky, possibly the same objects and
# artefacts). A connected component is a group; groups are the resampling
# unit of every interval and are never split between development and
# validation.
LINK_SAME_FIELD_DAYS = 3
# Split rule: a group containing any R or N quadrant-night is DEVELOPMENT
# (R features were explored in AS-031-034, N is the exploratory AS-035
# sample); every other group (C only) is VALIDATION. C features have never
# been extracted or looked at; only C recovery traces exist (AS-036).
DEVELOPMENT = "development"
VALIDATION = "validation"

# --- Stages (kept apart) ---
# 1. feature evaluation   - development only (AS-038)
# 2. ranking construction - development only, grouped CV (AS-039)
# 3. validation           - validation only, once, frozen ranker (AS-040)
STAGE_FEATURE_EVALUATION = "feature_evaluation"
STAGE_RANKING_CONSTRUCTION = "ranking_construction"
STAGE_VALIDATION = "validation"
STAGE_SPLITS = {
    STAGE_FEATURE_EVALUATION: DEVELOPMENT,
    STAGE_RANKING_CONSTRUCTION: DEVELOPMENT,
    STAGE_VALIDATION: VALIDATION,
}

# --- Labels (positive controls) ---
# POSITIVE: built tracklet identified KNOWN whose best match is an AS-022-
#   rule target (PRIMARY or MARGINAL) of the quadrant-night that is rate-
#   and baseline-eligible (AS-035 definitions) - exactly the AS-035/036
#   "recovered" outcome.
# AUXILIARY: built KNOWN tracklet of any other object (non-target, or an
#   ineligible target) and every AMBIGUOUS tracklet. Real or possibly real:
#   ranked (they use review slots) but neither positive nor background.
# BACKGROUND: built UNKNOWN tracklet. A mixture (artefacts, mislinks, real
#   unknown objects) - not a ground-truth false positive.
# NOT_RANKED: rejected tracklets.
# A failed SkyBoT lookup is never UNKNOWN: the quadrant-night is not
# evaluated until the stored snapshot replays.
POSITIVE = "positive"
AUXILIARY = "auxiliary"
BACKGROUND = "background"
NOT_RANKED = "not_ranked"

# --- Primary metric ---
# Background-rank fraction of a positive p in its own quadrant-night:
#   q(p) = (#background scored above p + 0.5 #background tied with p)
#          / #background.
# Other positives and auxiliary tracklets do not count against p, so q
# does not depend on how many known objects a field happens to contain
# (known objects stand in for the one or two real unknowns a field may
# hold). Recall at review fraction f: share of positive object-nights with
# q <= f. Enrichment = recall / f. Within-field AUC = mean (1 - q).
# Budget form: background rank r(p) = 1 + #above + 0.5 #tied; recall@K =
# share with r <= K.
# Object-night = (designation, UTC night). A real object seen in k
# quadrant-nights of the same night (overlapping ZTF fields, e.g. C29/C30)
# has total weight 1 (1/k per copy). If an object has several POSITIVE
# tracklets in one quadrant-night, its best-scored one counts.
PRIMARY_FRACTION = 0.05
SECONDARY_FRACTIONS = (0.01, 0.02, 0.10, 0.20)
SECONDARY_BUDGETS = (10, 25, 50)

# --- Decision rule (applied once, to the validation split) ---
USEFUL_RECALL = 0.50  # point estimate of recall@5 % (10x enrichment)
USEFUL_LOWER = 0.30  # 95 % group-bootstrap lower bound (6x enrichment)
PROTECTION_MARGIN = 0.20  # smallest difference that matters (AS-036)
MIN_POSITIVE_OBJECTS = 100
MIN_POSITIVE_FIELDS = 15  # quadrant-nights with >= 1 positive
MIN_ZONE_POSITIVES = 10
MIN_FAINT_POSITIVES = 30
BOOTSTRAP_RESAMPLES = 2000
CI_LEVEL = 0.95
# Verdicts:
# - INCONCLUSIVE: a minimum (objects, fields) unmet, or the interval
#   neither reaches USEFUL nor excludes it.
# - NOT USEFUL: bootstrap upper bound of recall@5 % < USEFUL_RECALL.
# - USEFUL: recall@5 % >= USEFUL_RECALL and lower bound >= USEFUL_LOWER;
#   then the guards qualify it:
#   - near-star guard: zone recall@5 % >= control recall@5 % - 0.20;
#   - faint guard: MARGINAL recall@5 % >= PRIMARY recall@5 % - 0.20;
#   USEFUL, PROTECTED: both guards evaluable (zone >= 10, MARGINAL >= 30
#   object-nights) and passing; USEFUL, NOT PROTECTED: a guard fails;
#   USEFUL, PROTECTION UNVERIFIED: a guard is not evaluable.
# Guards use object-night point estimates (weighted shares); the Newcombe
# interval of each difference is reported, not deciding.
INCONCLUSIVE = "INCONCLUSIVE"
NOT_USEFUL = "NOT USEFUL"
USEFUL_PROTECTED = "USEFUL, PROTECTED"
USEFUL_NOT_PROTECTED = "USEFUL, NOT PROTECTED"
USEFUL_UNVERIFIED = "USEFUL, PROTECTION UNVERIFIED"

# --- Candidate features (stage 1) with pre-registered direction ---
# +1: higher ranks first; -1: lower ranks first. Every feature enters a
# ranker only as its within-quadrant-night percentile (crowding / depth
# differ by orders of magnitude between fields).
CANDIDATE_FEATURES = {
    "min_snr": +1,
    "median_snr": +1,
    "fit_rms_residual_arcsec": -1,
    "fit_max_residual_arcsec": -1,
    "magnitude_range_mag": -1,
    "magnitude_range_sigma": -1,
    "magnitude_chi2": -1,  # sum ((m - weighted mean) / sigma)^2, dof 2
    "flagged_detection_count": -1,
    "masked_detection_count": -1,
    "edge_detection_count": -1,
    "sharp_abs_max": -1,  # max |sharp|; research path only (no sharp in API)
    "shared_detection_tracklets": -1,  # other built tracklets sharing a detection
}
# Context only - reported, stratified on, never in a primary ranker:
CONTEXT_FEATURES = (
    "star_separation_by_class",  # StarProximity (AS-034)
    "proximity_group",  # zone / outer / intermediate / control (AS-035)
    "angular_velocity_arcsec_per_min",  # known-population prior
    "position_angle_deg",  # known-population prior (ecliptic motion)
)
# detection_count is constant (3 frames) and not evaluated.

# --- Stage 1: feature evaluation gate (development, AS-038) ---
# Per candidate feature, scored in its pre-registered direction: within-
# field AUC (mean 1 - q) with 95 % group-bootstrap interval, overall and per
# stratum. A feature passes when the overall lower bound > AUC_GATE_LOWER,
# the MARGINAL and the near-star (zone + outer) point AUCs are >= 0.5 (it
# does not reverse for faint or near-star real objects), and it is missing
# for <= MAX_MISSING of ranked tracklets. Of two passing features with
# |Spearman| > REDUNDANCY_SPEARMAN on development background, the one with
# the lower AUC is dropped. The passing list is frozen before stage 2.
AUC_GATE_LOWER = 0.55
MAX_MISSING = 0.05
REDUNDANCY_SPEARMAN = 0.90
# Development has only 6 zone positives, so development-side protection
# checks use zone + outer (54 positives) as the near-star stratum.
DEVELOPMENT_NEAR_GROUPS = ("zone", "outer")

# --- Stage 2: ranking construction (development, AS-039) ---
# Finite ranker family, nothing else may be tried:
#   B0 hash order (null); B1 each passing feature alone;
#   M1 unweighted mean of the passing features' within-field percentiles;
#   M2 L2 logistic regression on the same percentiles, positive vs
#      background, quadrant-nights weighted equally, C from LOGISTIC_C_GRID.
# Estimates: grouped CV_FOLDS-fold CV over development groups (folds by
# SHA-256('AS-037:<group>') order), never in-sample. Selection: highest CV
# recall@5 % among M1/M2 whose CV near-star (zone + outer) and MARGINAL
# guards pass (same 0.20 margin); ties within 0.02 -> M1 (no fitted
# weights). The best B1 by CV recall@5 % is the frozen comparator. The
# frozen ranker (features, direction, weights, commit) is committed before
# stage 3. A proximity-including variant may be reported in stage 2 as
# exploratory and is never selectable.
CV_FOLDS = 5
LOGISTIC_C_GRID = (0.01, 0.1, 1.0, 10.0)
SELECTION_TIE = 0.02
RANKER_FAMILY = ("B0", "B1", "M1", "M2")

PREREGISTRATION = (
    "AS-037 candidate-ranking design. Population: every BUILT tracklet of the 80 "
    "frozen quadrant-nights (AS-034 R 26, AS-035 N 24, AS-036 C 30), unchanged "
    "pipeline, identity-blind ranking per quadrant-night. Groups: union of shared UTC "
    "night, shared search/selection star, same ZTF field within 3 nights. Split: groups "
    "with any R or N member = development, others = validation (sealed until a ranker "
    "is frozen). Stages: feature evaluation and ranking construction on development "
    "only (grouped CV), validation once. Positive = built KNOWN tracklet of a rate- and "
    "baseline-eligible AS-022-rule target (PRIMARY/MARGINAL); auxiliary = other KNOWN "
    "and AMBIGUOUS; background = built UNKNOWN. Primary metric: recall of positive "
    "object-nights (designation, night; weight 1 split over copies) whose background-"
    "rank fraction q <= 0.05 in their own quadrant-night (ties half); secondary 1/2/10/"
    "20 %, K = 10/25/50, enrichment, within-field AUC; 95 % group bootstrap (2000, "
    "SHA-256 seed). Decision on validation: USEFUL if recall@5% >= 0.50 and lower bound "
    ">= 0.30; NOT USEFUL if upper bound < 0.50; else INCONCLUSIVE (also if < 100 "
    "positive object-nights or < 15 fields with a positive). Guards: zone recall >= "
    "control - 0.20 (zone n >= 10), MARGINAL recall >= PRIMARY - 0.20 (n >= 30); "
    "bright-star proximity is context only, never a ranker input or rejection rule. "
    "No ranking outcome was looked at."
)


# ---------------------------------------------------------------------------
# Population and frozen split
# ---------------------------------------------------------------------------

FIELD_ID_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})-(\d+)-c(\d+)-q(\d)$")
TYCHO_PATTERN = re.compile(r"TYC \d+-\d+-\d+")


@dataclass(frozen=True)
class QuadrantNight:
    field_id: str
    population: str  # R / N / C
    night: str  # UTC date of the first exposure
    ztf_field: int
    ccd: int
    quadrant: int
    product_ids: tuple[int, ...]
    stars: tuple[str, ...] = ()


def parse_field_id(field_id: str) -> tuple[str, int, int, int]:
    """(UTC night, ZTF field, CCD, quadrant) from a frozen field id."""
    match = FIELD_ID_PATTERN.search(field_id)
    if match is None:
        raise ValueError(f"unparseable field id: {field_id}")
    night, ztf_field, ccd, quadrant = match.groups()
    return night, int(ztf_field), int(ccd), int(quadrant)


def quadrant_night(field_id: str, population: str, product_ids, stars=()) -> QuadrantNight:
    night, ztf_field, ccd, quadrant = parse_field_id(field_id)
    return QuadrantNight(
        field_id=field_id,
        population=population,
        night=night,
        ztf_field=ztf_field,
        ccd=ccd,
        quadrant=quadrant,
        product_ids=tuple(int(p) for p in product_ids),
        stars=tuple(sorted(set(stars))),
    )


def load_quadrant_nights(root: Path) -> list[QuadrantNight]:
    """The 80 frozen quadrant-nights; stars are the AS-033 selection star of
    R's S fields (siblings inherit it) and the search star of N / C."""
    r_stars: dict[str, tuple[str, ...]] = {}
    as033 = json.loads((root / STAR_FILE_R).read_text())
    for entry in as033["fields"]:
        f = entry["field"]
        r_stars[f["field_id"]] = tuple(TYCHO_PATTERN.findall(f["description"]))

    result: list[QuadrantNight] = []
    population = json.loads((root / POPULATION_FILES["R"]).read_text())
    for entry in population["fields"]:
        f = entry["field"]
        origin = entry["origin"]
        parent = origin.removeprefix("sibling of ") if origin.startswith("sibling") else None
        stars = r_stars.get(f["field_id"]) or r_stars.get(parent or "", ())
        result.append(quadrant_night(f["field_id"], "R", f["product_ids"], stars))
    for name in ("N", "C"):
        selection = json.loads((root / POPULATION_FILES[name]).read_text())
        for entry in selection["sequences"]:
            f = entry["field"]
            star = entry["search_star"]["tycho_id"]
            result.append(quadrant_night(f["field_id"], name, f["product_ids"], (star,)))
    return result


def link_reasons(a: QuadrantNight, b: QuadrantNight) -> list[str]:
    reasons = []
    if a.night == b.night:
        reasons.append("same night")
    shared = sorted(set(a.stars) & set(b.stars))
    if shared:
        reasons.append("same star " + ", ".join(shared))
    if a.ztf_field == b.ztf_field and a.night != b.night:
        gap = abs((date.fromisoformat(a.night) - date.fromisoformat(b.night)).days)
        if gap <= LINK_SAME_FIELD_DAYS:
            reasons.append(f"ZTF field {a.ztf_field} {gap} d apart")
    return reasons


def independence_groups(
    nights: Sequence[QuadrantNight],
) -> tuple[dict[str, str], list[tuple[str, str, list[str]]]]:
    """field_id -> group id (G-<smallest member field id>) and every link."""
    parent = {q.field_id: q.field_id for q in nights}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    links = []
    for i, a in enumerate(nights):
        for b in nights[i + 1 :]:
            reasons = link_reasons(a, b)
            if reasons:
                links.append((a.field_id, b.field_id, reasons))
                ra, rb = find(a.field_id), find(b.field_id)
                if ra != rb:
                    parent[max(ra, rb)] = min(ra, rb)
    members: dict[str, list[str]] = defaultdict(list)
    for q in nights:
        members[find(q.field_id)].append(q.field_id)
    group_of = {}
    for ids in members.values():
        gid = "G-" + min(ids)
        for fid in ids:
            group_of[fid] = gid
    return group_of, links


def assign_splits(nights: Sequence[QuadrantNight], group_of: Mapping[str, str]) -> dict[str, str]:
    """Pre-registered split: any R/N member makes the whole group DEVELOPMENT."""
    development_groups = {group_of[q.field_id] for q in nights if q.population in ("R", "N")}
    return {
        q.field_id: DEVELOPMENT if group_of[q.field_id] in development_groups else VALIDATION
        for q in nights
    }


def split_digest(field_ids: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(sorted(field_ids)).encode()).hexdigest()


class SplitError(RuntimeError):
    """A stage asked for a quadrant-night outside its split."""


def require_split(manifest: Mapping, field_id: str, stage: str) -> None:
    """Guard for the AS-038+ runners: feature evaluation and ranking
    construction may touch development quadrant-nights only, validation
    only validation ones (and only with a frozen ranker, checked there)."""
    if stage not in STAGE_SPLITS:
        raise SplitError(f"unknown stage {stage!r}")
    splits = {q["field_id"]: q["split"] for q in manifest["quadrant_nights"]}
    if field_id not in splits:
        raise SplitError(f"{field_id} is not in the frozen AS-037 manifest")
    if splits[field_id] != STAGE_SPLITS[stage]:
        raise SplitError(f"{field_id} is {splits[field_id]}; stage {stage} may not use it")


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


def label_tracklet(
    tracklet_status: str,
    identification_status: str | None,
    best_match: str | None,
    eligible_targets: Mapping[str, str],
) -> str:
    """Pre-registered label. eligible_targets: designation -> role
    ("primary" / "marginal") of the quadrant-night's rate- and baseline-
    eligible AS-022-rule targets."""
    if tracklet_status != "built":
        return NOT_RANKED
    if identification_status is None:
        raise ValueError("unidentified tracklet: a SkyBoT failure is never UNKNOWN")
    if identification_status == "unknown":
        return BACKGROUND
    if identification_status == "known" and best_match in eligible_targets:
        return POSITIVE
    if identification_status in ("known", "ambiguous"):
        return AUXILIARY
    raise ValueError(f"unexpected identification status {identification_status!r}")


def hash_score(field_id: str, tracklet_id: str) -> float:
    """B0 null ranker: a feature-independent order in [0, 1)."""
    digest = hashlib.sha256(f"{SALT}:{field_id}:{tracklet_id}".encode()).hexdigest()
    return int(digest[:15], 16) / 16**15


def within_field_percentile(values: Sequence[float | None], direction: int) -> list[float | None]:
    """Mid-rank percentile in (0, 1) within one quadrant-night, oriented so
    that higher = ranked earlier; missing stays missing."""
    present = sorted(direction * v for v in values if v is not None)
    n = len(present)
    out: list[float | None] = []
    for v in values:
        if v is None:
            out.append(None)
            continue
        x = direction * v
        below = _count_below(present, x)
        tied = _count_below(present, x, inclusive=True) - below
        out.append((below + 0.5 * tied) / n)
    return out


def _count_below(ordered: Sequence[float], x: float, inclusive: bool = False) -> int:
    return (bisect.bisect_right if inclusive else bisect.bisect_left)(ordered, x)


def magnitude_chi2(magnitudes: Sequence[float], errors: Sequence[float]) -> float | None:
    """chi^2 of the detections' magnitudes about their inverse-variance
    weighted mean; None when any error is not positive."""
    if len(magnitudes) < 2 or any(e <= 0 for e in errors):
        return None
    weights = [1.0 / (e * e) for e in errors]
    mean = sum(w * m for w, m in zip(weights, magnitudes)) / sum(weights)
    return sum(w * (m - mean) ** 2 for w, m in zip(weights, magnitudes))


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def background_rank_fraction(score: float, background: Sequence[float]) -> float:
    """q: share of background scored above (ties half). 0 without background."""
    if not background:
        return 0.0
    above = sum(1 for b in background if b > score)
    tied = sum(1 for b in background if b == score)
    return (above + 0.5 * tied) / len(background)


def background_rank(score: float, background: Sequence[float]) -> float:
    above = sum(1 for b in background if b > score)
    tied = sum(1 for b in background if b == score)
    return 1 + above + 0.5 * tied


@dataclass
class RankedPositive:
    field_id: str
    group: str
    designation: str
    night: str
    q: float
    rank: float
    strata: dict[str, str] = field(default_factory=dict)
    weight: float = 1.0  # set by object_weights


def rank_field(
    field_id: str,
    group: str,
    night: str,
    scores: Mapping[str, float],
    labels: Mapping[str, str],
    designations: Mapping[str, str],
    strata: Mapping[str, Mapping[str, str]] | None = None,
) -> list[RankedPositive]:
    """Positives of one quadrant-night against its background. scores /
    labels by tracklet id; designations: positive tracklet -> best match.
    One entry per object (its best-scored positive tracklet)."""
    background = [scores[t] for t, label in labels.items() if label == BACKGROUND]
    best: dict[str, str] = {}
    for t, label in labels.items():
        if label != POSITIVE:
            continue
        d = designations[t]
        if d not in best or scores[t] > scores[best[d]]:
            best[d] = t
    return [
        RankedPositive(
            field_id=field_id,
            group=group,
            designation=d,
            night=night,
            q=background_rank_fraction(scores[t], background),
            rank=background_rank(scores[t], background),
            strata=dict((strata or {}).get(d, {})),
        )
        for d, t in sorted(best.items())
    ]


def object_weights(positives: Sequence[RankedPositive]) -> list[RankedPositive]:
    """Weight 1 per object-night, split over its copies."""
    copies: dict[tuple[str, str], int] = defaultdict(int)
    for p in positives:
        copies[(p.designation, p.night)] += 1
    for p in positives:
        p.weight = 1.0 / copies[(p.designation, p.night)]
    return list(positives)


def _weighted_share(positives: Sequence[RankedPositive], hit: Callable[[RankedPositive], bool]):
    total = sum(p.weight for p in positives)
    if total == 0:
        return None
    return sum(p.weight for p in positives if hit(p)) / total


def recall_at_fraction(positives: Sequence[RankedPositive], fraction: float) -> float | None:
    return _weighted_share(positives, lambda p: p.q <= fraction)


def recall_at_budget(positives: Sequence[RankedPositive], budget: int) -> float | None:
    return _weighted_share(positives, lambda p: p.rank <= budget)


def enrichment(positives: Sequence[RankedPositive], fraction: float) -> float | None:
    recall = recall_at_fraction(positives, fraction)
    return None if recall is None else recall / fraction


def within_field_auc(positives: Sequence[RankedPositive]) -> float | None:
    total = sum(p.weight for p in positives)
    if total == 0:
        return None
    return sum(p.weight * (1.0 - p.q) for p in positives) / total


def object_count(positives: Sequence[RankedPositive]) -> float:
    return sum(p.weight for p in positives)


def stratum(positives: Sequence[RankedPositive], key: str, value: str) -> list[RankedPositive]:
    return [p for p in positives if p.strata.get(key) == value]


def bootstrap_seed(label: str) -> int:
    return int(hashlib.sha256(f"{SALT}:{label}".encode()).hexdigest()[:16], 16)


def group_bootstrap(
    positives: Sequence[RankedPositive],
    statistic: Callable[[Sequence[RankedPositive]], float | None],
    label: str,
    resamples: int = BOOTSTRAP_RESAMPLES,
    level: float = CI_LEVEL,
) -> tuple[float | None, float | None]:
    """Percentile interval, resampling independence groups with replacement."""
    by_group: dict[str, list[RankedPositive]] = defaultdict(list)
    for p in positives:
        by_group[p.group].append(p)
    groups = sorted(by_group)
    if not groups:
        return None, None
    rng = random.Random(bootstrap_seed(label))
    values = []
    for _ in range(resamples):
        sample = [p for g in rng.choices(groups, k=len(groups)) for p in by_group[g]]
        value = statistic(sample)
        if value is not None:
            values.append(value)
    if not values:
        return None, None
    values.sort()
    alpha = (1 - level) / 2
    lo = values[max(0, math.floor(alpha * len(values)))]
    hi = values[min(len(values) - 1, math.ceil((1 - alpha) * len(values)) - 1)]
    return lo, hi


# ---------------------------------------------------------------------------
# Decision rule
# ---------------------------------------------------------------------------


class Guard(BaseModel):
    name: str
    protected_n: float
    reference_n: float
    protected_recall: float | None
    reference_recall: float | None
    difference: float | None
    newcombe_95: tuple[float | None, float | None]
    evaluable: bool
    passed: bool | None


class Decision(BaseModel):
    verdict: str
    recall: float | None
    ci_95: tuple[float | None, float | None]
    positive_objects: float
    positive_fields: int
    guards: list[Guard]
    reasons: list[str]


def guard(
    name: str,
    protected: Sequence[RankedPositive],
    reference: Sequence[RankedPositive],
    min_protected: int,
    fraction: float = PRIMARY_FRACTION,
) -> Guard:
    n_p, n_r = object_count(protected), object_count(reference)
    r_p, r_r = recall_at_fraction(protected, fraction), recall_at_fraction(reference, fraction)
    difference = None if r_p is None or r_r is None else r_p - r_r
    interval: tuple[float | None, float | None] = (None, None)
    if r_p is not None and r_r is not None:
        interval = newcombe(round(r_p * n_p), round(n_p), round(r_r * n_r), round(n_r))
    evaluable = n_p >= min_protected and n_r > 0
    passed = None if not evaluable else difference >= -PROTECTION_MARGIN
    return Guard(
        name=name,
        protected_n=n_p,
        reference_n=n_r,
        protected_recall=r_p,
        reference_recall=r_r,
        difference=difference,
        newcombe_95=interval,
        evaluable=evaluable,
        passed=passed,
    )


def decide(positives: Sequence[RankedPositive], label: str = "validation") -> Decision:
    """Apply the pre-registered rule. Strata used: 'proximity_group'
    (zone / control) and 'role' (primary / marginal)."""
    recall = recall_at_fraction(positives, PRIMARY_FRACTION)
    lo, hi = group_bootstrap(
        positives, lambda s: recall_at_fraction(s, PRIMARY_FRACTION), label
    )
    n_objects = object_count(positives)
    n_fields = len({p.field_id for p in positives})
    guards = [
        guard(
            "near-star zone vs control",
            stratum(positives, "proximity_group", "zone"),
            stratum(positives, "proximity_group", "control"),
            MIN_ZONE_POSITIVES,
        ),
        guard(
            "faint (MARGINAL) vs PRIMARY",
            stratum(positives, "role", "marginal"),
            stratum(positives, "role", "primary"),
            MIN_FAINT_POSITIVES,
        ),
    ]
    reasons = []
    if n_objects < MIN_POSITIVE_OBJECTS:
        reasons.append(f"{n_objects:g} < {MIN_POSITIVE_OBJECTS} positive object-nights")
    if n_fields < MIN_POSITIVE_FIELDS:
        reasons.append(f"{n_fields} < {MIN_POSITIVE_FIELDS} fields with a positive")
    if reasons or recall is None or lo is None:
        verdict = INCONCLUSIVE
    elif hi < USEFUL_RECALL:
        verdict = NOT_USEFUL
    elif recall >= USEFUL_RECALL and lo >= USEFUL_LOWER:
        if any(g.evaluable and not g.passed for g in guards):
            verdict = USEFUL_NOT_PROTECTED
        elif all(g.evaluable for g in guards):
            verdict = USEFUL_PROTECTED
        else:
            verdict = USEFUL_UNVERIFIED
    else:
        verdict = INCONCLUSIVE
        reasons.append("interval neither reaches nor excludes the useful level")
    return Decision(
        verdict=verdict,
        recall=recall,
        ci_95=(lo, hi),
        positive_objects=n_objects,
        positive_fields=n_fields,
        guards=guards,
        reasons=reasons,
    )


# ---------------------------------------------------------------------------
# Frozen manifest (inputs only; no feature, score or ranking outcome)
# ---------------------------------------------------------------------------


def positive_availability(traces: Sequence[Mapping], split_of: Mapping[str, str]) -> dict:
    """Positive-control counts per split from the published AS-035/036
    recovery traces (recovered = built KNOWN tracklet of the target, i.e.
    the POSITIVE label). Feasibility of the minimums, not a ranking outcome."""
    out: dict[str, dict] = {}
    for split in (DEVELOPMENT, VALIDATION):
        rows = [
            t
            for t in traces
            if split_of[t["field_id"]] == split
            and t["rate_eligible"]
            and t["baseline_eligible"]
            and t["recovered"]
        ]
        nights = {t["field_id"]: parse_field_id(t["field_id"])[0] for t in rows}
        objects = {(t["designation"], nights[t["field_id"]]) for t in rows}
        by: dict[str, int] = defaultdict(int)
        for t in rows:
            by[f"{t['role']}/{t['group']}"] += 1
        out[split] = {
            "positive_tracklet_targets": len(rows),
            "positive_object_nights": len(objects),
            "fields_with_positive": len(nights),
            "zone": sum(1 for t in rows if t["group"] == "zone"),
            "zone_or_outer": sum(1 for t in rows if t["group"] in ("zone", "outer")),
            "marginal": sum(1 for t in rows if t["role"] == "marginal"),
            "by_role_group": dict(sorted(by.items())),
        }
    return out


def cross_split_designations(traces: Sequence[Mapping], split_of: Mapping[str, str]) -> list[str]:
    """Validation targets that are also targets of a development
    quadrant-night (another night): reported, sensitivity analysis only."""
    dev = {t["designation"] for t in traces if split_of[t["field_id"]] == DEVELOPMENT}
    val = {t["designation"] for t in traces if split_of[t["field_id"]] == VALIDATION}
    return sorted(dev & val)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest(root: Path) -> dict:
    nights = load_quadrant_nights(root)
    group_of, links = independence_groups(nights)
    split_of = assign_splits(nights, group_of)
    traces = []
    for name in ("R", "N", "C"):
        traces.extend(json.loads((root / TRACE_FILES[name]).read_text())["targets"])
    groups: dict[str, list[str]] = defaultdict(list)
    for q in nights:
        groups[group_of[q.field_id]].append(q.field_id)
    validation_ids = [fid for fid, s in split_of.items() if s == VALIDATION]
    inputs = sorted({*POPULATION_FILES.values(), *TRACE_FILES.values(), STAR_FILE_R})
    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "preregistration": PREREGISTRATION,
        "inputs": {p: file_sha256(root / p) for p in inputs},
        "split_counts": {
            s: sum(1 for v in split_of.values() if v == s) for s in (DEVELOPMENT, VALIDATION)
        },
        "validation_digest": split_digest(validation_ids),
        "quadrant_nights": [
            {
                "field_id": q.field_id,
                "population": q.population,
                "night": q.night,
                "ztf_field": q.ztf_field,
                "ccd": q.ccd,
                "quadrant": q.quadrant,
                "product_ids": list(q.product_ids),
                "stars": list(q.stars),
                "group": group_of[q.field_id],
                "split": split_of[q.field_id],
            }
            for q in nights
        ],
        "groups": [
            {"group": g, "split": split_of[ids[0]], "members": sorted(ids)}
            for g, ids in sorted(groups.items())
        ],
        "links": [{"a": a, "b": b, "reasons": r} for a, b, r in links],
        "positive_availability": positive_availability(traces, split_of),
        "cross_split_designations": cross_split_designations(traces, split_of),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    m = sub.add_parser("manifest", help="write the frozen AS-037 split manifest")
    m.add_argument("--root", type=Path, default=Path("."))
    m.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "manifest":
        manifest = build_manifest(args.root)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(manifest, indent=1) + "\n")
        counts = manifest["split_counts"]
        print(f"{counts} validation digest {manifest['validation_digest'][:12]}")


if __name__ == "__main__":
    main()
