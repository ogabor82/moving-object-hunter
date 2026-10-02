"""AS-039: stage-2 candidate ranker construction (development split only).

Executes stage 2 of the AS-037 pre-registration
(validation/results/as037/as037_preregistration.md, PRE-REGISTRATION block
of app/validation/ranking_design.py) unchanged, on the AS-038 development
feature table and the 8 features AS-038 froze
(validation/results/as038/as038_frozen_features.json):

- the finite ranker family B0 (hash order), B1 (each frozen feature
  alone), M1 (unweighted mean of the frozen features' within-field
  percentiles) and M2 (L2 logistic regression on the same percentiles,
  positive vs background, quadrant-nights weighted equally, C in
  {0.01, 0.1, 1, 10}), nothing else;
- grouped 5-fold cross-validation over the development independence
  groups (folds in SHA-256('AS-037:<group>') order), never in-sample;
- recall@5 % with its group-bootstrap interval, the secondary metrics,
  strata, the near-star (zone + outer) and faint (MARGINAL) guards with
  the 0.20 margin, counterexamples;
- the mechanical AS-037 selection rule, and the frozen AS-040 ranker +
  comparator, or a recorded no-advance result.

The validation split is never loaded: every quadrant-night passes
`ranking_design.require_split(manifest, field_id,
STAGE_RANKING_CONSTRUCTION)` before it is read. Ranker inputs are only the
frozen features' within-quadrant-night percentiles; identification,
designation, SkyBoT, proximity, speed and PA columns are evaluation /
stratification only. UNKNOWN is background, not a ground-truth false
positive. No filter, threshold or rejection rule is built.

    python -m app.validation.ranker_construction evaluate \\
        --out-dir validation/results/as039     # offline, from the AS-038 table
"""

import argparse
import hashlib
import json
import statistics
import subprocess
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from pydantic import BaseModel

from app.validation import feature_evaluation as fe
from app.validation import ranking_design as rd

# ---------------------------------------------------------------------------
# IMPLEMENTATION DECISIONS (AS-039, 2026-10-02; fixed and committed before
# any ranker score, cross-validated metric or selection outcome existed).
# They fill in details AS-037 does not spell out; none changes an AS-037
# rule, the split, a metric, a guard, a feature, a direction or the frozen
# AS-038 feature list.
# ---------------------------------------------------------------------------

STAGE = rd.STAGE_RANKING_CONSTRUCTION
AS038_DIR = "validation/results/as038"
FROZEN_FEATURES_FILE = f"{AS038_DIR}/as038_frozen_features.json"

# E1 Inputs: the committed AS-038 development table and the AS-038 frozen
# list, read as they are (table SHA-256 checked against the frozen list).
# The ranker input columns are exactly the frozen features; nothing else of
# the table (label, eval_*, ctx_*, mask_bits_union, sharp_availability,
# shares_detection_with_positive) ever reaches a score.
FROZEN_FEATURES = (
    "min_snr",
    "median_snr",
    "fit_rms_residual_arcsec",
    "magnitude_range_mag",
    "flagged_detection_count",
    "masked_detection_count",
    "sharp_abs_max",
    "shared_detection_tracklets",
)

# E2 Representation: per quadrant-night, over ALL its ranked (built)
# tracklets and without labels, ranking_design.within_field_percentile of
# each frozen feature in its AS-037 direction (mid-rank, higher = earlier).
# A missing value gets percentile 0.0 (after every present value; AS-038
# D3). No other transform (no standardisation, interaction or clipping).
MISSING_PERCENTILE = 0.0

# E3 Folds: development groups (manifest) sorted by
# SHA-256('AS-037:<group>') hex digest; the i-th group goes to fold
# i mod CV_FOLDS. A quadrant-night is scored only by a ranker fitted
# without its fold. B0, B1 and M1 have no fitted parameter, so their
# out-of-fold score is their fixed score.

# E4 Cross-validated metrics: the out-of-fold ranked positives of all five
# folds are pooled (each positive is scored once, by the model that did
# not see its group) and every AS-037 metric is computed on the pool;
# intervals: ranking_design.group_bootstrap over development groups
# (2000, seed SHA-256('AS-037:AS-039/<ranker>/<statistic>')). Per-fold
# recall@5 % is reported, descriptive only.

# E5 M2: minimise 0.5 * |w|^2 + C * sum_i s_i * logloss_i over the eight
# percentiles with an unpenalised intercept (the scikit-learn definition
# of C), solved by damped Newton steps to max |gradient| < 1e-9 (the
# problem is strictly convex, so the optimum is unique and
# solver-independent). Note: the first run of commit 9c358ab stopped
# with "did not converge" in M2(C=1) before any output was written or
# read: backtracking rejected steps whose objective change was below
# float rounding. Full Newton steps are now taken once the Newton
# decrement is < 1e-12; the optimum, tolerance and recipe are unchanged.
# Training rows: positive (y = 1) and background
# (y = 0) tracklets of the training folds; auxiliary tracklets are not
# training rows (they are still ranked). Quadrant-nights weighted
# equally: s_i = 1 / (#positive + #background of its quadrant-night), so
# each training quadrant-night has total weight 1. Score = linear
# predictor w . x + b (monotone in the probability). Each C of the grid is
# its own family member M2(C); there is no inner tuning loop.

# E6 Guards in stage 2 (point estimates of the pooled CV ranks, 0.20
# margin, ranking_design.guard):
# - faint: MARGINAL recall@5 % >= PRIMARY recall@5 % - 0.20 (MARGINAL
#   >= 30 object-nights);
# - near-star: zone + outer recall@5 % >= control recall@5 % - 0.20
#   (zone + outer >= 10 object-nights). AS-037 replaces only the
#   protected stratum (zone -> zone + outer, 6 zone positives on
#   development); the reference stays control.
# A guard passes only when it is evaluable and the difference is
# >= -0.20. zone + outer vs intermediate + control (the AS-038 O2 view)
# and zone-only vs control are reported, descriptive only.

# E7 Selection, mechanically: eligible = M1 and every M2(C) whose two
# guards pass. None eligible -> NO ADVANCE: no AS-040 ranker is frozen and
# no other candidate is constructed. Otherwise best = highest CV
# recall@5 % (exact ties: M1, then M2 in ascending C). If best is an M2
# and M1 is eligible with recall@5 % >= best - 0.02, M1 is selected.
# Comparator = B1 with the highest CV recall@5 % (exact ties: frozen-list
# order), no guard condition. B0 is the null reference, never selectable.
# A recall@5 % at the USEFUL level is NOT a selection condition (AS-037
# does not make it one); the development-side decision-rule level is
# reported, descriptive only.

# E8 Frozen AS-040 spec (if a ranker advances): M1 -> feature list,
# directions, equal weights 1/8, no fit. M2(C) -> refit once on all 56
# development quadrant-nights with the selected C (same E5 recipe); the
# coefficients and intercept are frozen. Plus the comparator, the E2
# representation, the q / tie rule and the code commit that produced it.

# E9 Proximity-including variant: AS-037 allows reporting one as
# exploratory; it is NOT run (nothing to gain for selection, and it would
# put proximity into a score).

# E10 Counterexamples (reported, never acted on), per combined ranker
# (M1, M2(C)): quadrant-nights with >= 3 positives and AUC < 0.5; strata
# with recall@5 % below the overall value - 0.20; positives in the bottom
# half (q > 0.5). For the selected ranker (or, without one, every
# combined ranker): positives outside the top 5 % by stratum, and the
# positives the comparator puts in the top 5 % that the ranker does not
# (and vice versa).

# E11 Sensitivity (descriptive): AS-038 D9 (a) background sharing a
# detection with a positive removed, (b) 105890 removed - re-scored with
# the same out-of-fold scores.

# E12 Paired difference of recall@5 % (ranker - comparator, ranker - B0):
# group bootstrap over the same resampled groups, descriptive only.

CV_SEED_PREFIX = rd.SALT
NEWTON_TOLERANCE = 1e-9
NEWTON_MAX_ITER = 200
NEWTON_FULL_STEP_DECREMENT = 1e-12
STRATUM_GAP_REPORT = 0.20

RESULTS_FILE = "as039_construction.json"
REPORT_FILE = "as039_construction.md"
SELECTION_FILE = "as039_selection.json"
FROZEN_FILE = "as039_frozen_ranker.json"


# ---------------------------------------------------------------------------
# Inputs (split-guarded)
# ---------------------------------------------------------------------------


def load_frozen_features(root: Path) -> list[tuple[str, int]]:
    """The AS-038 frozen list, checked against E1 and the AS-037 directions."""
    spec = json.loads((root / FROZEN_FEATURES_FILE).read_text())
    features = [(f["feature"], int(f["direction"])) for f in spec["features"]]
    if tuple(name for name, _ in features) != FROZEN_FEATURES:
        raise ValueError(f"AS-038 frozen list changed: {features}")
    for name, direction in features:
        if rd.CANDIDATE_FEATURES[name] != direction:
            raise ValueError(f"{name}: direction {direction} differs from AS-037")
    return features


def load_development(root: Path) -> tuple[dict, list[dict], list[dict]]:
    """Manifest, table rows and field conditions; every quadrant-night guarded."""
    manifest = fe.load_manifest(root)
    spec = json.loads((root / FROZEN_FEATURES_FILE).read_text())
    table = root / AS038_DIR / fe.TABLE_FILE
    if rd.file_sha256(table) != spec["table_sha256"]:
        raise ValueError("AS-038 table differs from the one the frozen list was derived from")
    if rd.file_sha256(root / fe.MANIFEST_FILE) != spec["manifest_sha256"]:
        raise ValueError("AS-037 manifest differs from the AS-038 one")
    rows = fe.read_table(table, manifest)
    fields = json.loads((root / AS038_DIR / fe.FIELDS_FILE).read_text())["fields"]
    for field_id in {r["field_id"] for r in rows} | {f["field_id"] for f in fields}:
        rd.require_split(manifest, field_id, STAGE)
    return manifest, rows, fields


def development_groups(manifest: Mapping) -> list[str]:
    groups = sorted({q["group"] for q in manifest["quadrant_nights"] if q["split"] == rd.DEVELOPMENT})
    for q in manifest["quadrant_nights"]:
        if q["split"] == rd.DEVELOPMENT:
            rd.require_split(manifest, q["field_id"], STAGE)
    return groups


def fold_of_groups(groups: Sequence[str], folds: int = rd.CV_FOLDS) -> dict[str, int]:
    """E3: SHA-256('AS-037:<group>') order, round-robin."""
    order = sorted(groups, key=lambda g: hashlib.sha256(f"{CV_SEED_PREFIX}:{g}".encode()).hexdigest())
    return {g: i % folds for i, g in enumerate(order)}


# ---------------------------------------------------------------------------
# Representation (E2)
# ---------------------------------------------------------------------------


def percentile_matrix(
    rows_by_field: Mapping[str, Sequence[Mapping]], features: Sequence[tuple[str, int]]
) -> dict[str, np.ndarray]:
    """field id -> (n tracklets x n features) oriented percentiles, label-free."""
    out = {}
    for field_id, rows in rows_by_field.items():
        columns = []
        for name, direction in features:
            p = rd.within_field_percentile([r[name] for r in rows], direction)
            columns.append([MISSING_PERCENTILE if v is None else v for v in p])
        out[field_id] = np.array(columns, dtype=float).T
    return out


# ---------------------------------------------------------------------------
# Rankers
# ---------------------------------------------------------------------------


def logistic_fit(x: np.ndarray, y: np.ndarray, s: np.ndarray, c: float) -> tuple[np.ndarray, float]:
    """E5: argmin 0.5 |w|^2 + c * sum s_i logloss_i, intercept unpenalised."""
    n, k = x.shape
    design = np.hstack([x, np.ones((n, 1))])
    theta = np.zeros(k + 1)
    penalty = np.ones(k + 1)
    penalty[-1] = 0.0

    def objective(t: np.ndarray) -> float:
        z = design @ t
        loss = np.logaddexp(0.0, z) - y * z
        return 0.5 * float(np.sum(penalty * t * t)) + c * float(s @ loss)

    current = objective(theta)
    for _ in range(NEWTON_MAX_ITER):
        z = design @ theta
        p = 1.0 / (1.0 + np.exp(-z))
        gradient = penalty * theta + c * design.T @ (s * (p - y))
        if np.max(np.abs(gradient)) < NEWTON_TOLERANCE:
            break
        hessian = np.diag(penalty) + c * (design.T * (s * p * (1 - p))) @ design
        step = np.linalg.solve(hessian, gradient)
        size = 1.0
        # Near the optimum the objective change is below float rounding:
        # take the full Newton step instead of backtracking (E5 note).
        while float(gradient @ step) > NEWTON_FULL_STEP_DECREMENT:
            candidate = theta - size * step
            value = objective(candidate)
            if value <= current or size < 1e-12:
                break
            size /= 2
        else:
            candidate = theta - step
            value = objective(candidate)
        theta, current = candidate, value
    else:
        raise RuntimeError("logistic regression did not converge")
    return theta[:k], float(theta[-1])


def training_set(
    rows_by_field: Mapping[str, Sequence[Mapping]],
    percentiles: Mapping[str, np.ndarray],
    field_ids: Sequence[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """E5: positive vs background rows, each quadrant-night total weight 1."""
    xs, ys, ss = [], [], []
    for field_id in field_ids:
        rows = rows_by_field[field_id]
        keep = [i for i, r in enumerate(rows) if r["label"] in (rd.POSITIVE, rd.BACKGROUND)]
        if not keep:
            continue
        xs.append(percentiles[field_id][keep])
        ys.append(np.array([1.0 if rows[i]["label"] == rd.POSITIVE else 0.0 for i in keep]))
        ss.append(np.full(len(keep), 1.0 / len(keep)))
    return np.vstack(xs), np.concatenate(ys), np.concatenate(ss)


def ranker_names(features: Sequence[tuple[str, int]]) -> list[str]:
    return [
        "B0",
        *(f"B1:{name}" for name, _ in features),
        "M1",
        *(f"M2:C={c:g}" for c in rd.LOGISTIC_C_GRID),
    ]


def is_combined(name: str) -> bool:
    return name == "M1" or name.startswith("M2:")


def m2_c(name: str) -> float:
    return float(name.removeprefix("M2:C="))


def fixed_scores(
    name: str, field_id: str, rows: Sequence[Mapping], x: np.ndarray, features: Sequence[tuple[str, int]]
) -> list[float]:
    """Scores of the parameter-free rankers (B0, B1, M1)."""
    if name == "B0":
        return [rd.hash_score(field_id, r["tracklet_id"]) for r in rows]
    if name == "M1":
        return [float(v) for v in x.mean(axis=1)]
    feature = name.removeprefix("B1:")
    column = [n for n, _ in features].index(feature)
    return [float(v) for v in x[:, column]]


class FoldModel(BaseModel):
    fold: int
    groups: list[str]
    fields: list[str]
    coefficients: dict[str, float] | None = None
    intercept: float | None = None


def cross_validated_scores(
    name: str,
    rows_by_field: Mapping[str, Sequence[Mapping]],
    percentiles: Mapping[str, np.ndarray],
    features: Sequence[tuple[str, int]],
    fold_of_field: Mapping[str, int],
    group_of_field: Mapping[str, str],
) -> tuple[dict[str, list[float]], list[FoldModel]]:
    """Out-of-fold scores of every ranked tracklet (E3/E4)."""
    scores: dict[str, list[float]] = {}
    models = []
    for fold in range(rd.CV_FOLDS):
        test = [f for f in rows_by_field if fold_of_field[f] == fold]
        train = [f for f in rows_by_field if fold_of_field[f] != fold]
        model = FoldModel(
            fold=fold, groups=sorted({group_of_field[f] for f in test}), fields=sorted(test)
        )
        if name.startswith("M2:"):
            x, y, s = training_set(rows_by_field, percentiles, train)
            w, b = logistic_fit(x, y, s, m2_c(name))
            model.coefficients = {n: float(v) for (n, _), v in zip(features, w)}
            model.intercept = b
            for f in test:
                scores[f] = [float(v) for v in percentiles[f] @ w + b]
        else:
            for f in test:
                scores[f] = fixed_scores(name, f, rows_by_field[f], percentiles[f], features)
        models.append(model)
    return scores, models


def rank_positives(
    rows_by_field: Mapping[str, Sequence[Mapping]],
    scores: Mapping[str, Sequence[float]],
    strata: Mapping[tuple[str, str], Mapping[str, str]],
    exclude_background: Callable[[Mapping], bool] = lambda r: False,
    exclude_designations: frozenset[str] = frozenset(),
) -> list[rd.RankedPositive]:
    """Every positive object ranked against its own background (AS-037)."""
    positives: list[rd.RankedPositive] = []
    for field_id, rows in rows_by_field.items():
        kept = [
            (r, s)
            for r, s in zip(rows, scores[field_id])
            if not (r["label"] == rd.BACKGROUND and exclude_background(r))
            and not (r["label"] == rd.POSITIVE and r["eval_designation"] in exclude_designations)
        ]
        by_id = {r["tracklet_id"]: s for r, s in kept}
        labels = {r["tracklet_id"]: r["label"] for r, _ in kept}
        designations = {r["tracklet_id"]: r["eval_designation"] for r, _ in kept if r["label"] == rd.POSITIVE}
        positives += rd.rank_field(
            field_id,
            rows[0]["group"],
            rows[0]["night"],
            by_id,
            labels,
            designations,
            {d: strata[(field_id, d)] for d in set(designations.values())},
        )
    return rd.object_weights(positives)


# ---------------------------------------------------------------------------
# Metrics, guards, selection
# ---------------------------------------------------------------------------


class Interval(BaseModel):
    point: float | None
    lower: float | None
    upper: float | None


class StratumResult(BaseModel):
    key: str
    value: str
    objects: float
    auc: float | None
    recall_5: float | None


class FieldResult(BaseModel):
    field_id: str
    fold: int
    positives: float
    background: int
    auc: float | None
    recall_5: float | None


class RankerResult(BaseModel):
    ranker: str
    family: str
    selectable: bool
    objects: float
    fields_with_positive: int
    recall_5: Interval
    auc: Interval
    recall: dict[str, float | None]
    recall_at_budget: dict[str, float | None]
    enrichment: dict[str, float | None]
    median_q: float | None
    fold_recall_5: dict[str, float | None]
    guards: list[rd.Guard]
    guards_passed: bool
    descriptive_guards: list[rd.Guard]
    development_level: str
    strata: list[StratumResult]
    fields: list[FieldResult]
    fold_models: list[FoldModel]
    sensitivity: dict[str, float | None]
    paired_difference: dict[str, Interval]


STRATA_KEYS = fe.STRATA_KEYS


def _ci(positives, statistic, label: str, resamples: int) -> Interval:
    lo, hi = rd.group_bootstrap(positives, statistic, label, resamples=resamples)
    return Interval(point=statistic(positives), lower=lo, upper=hi)


def recall5(positives: Sequence[rd.RankedPositive]) -> float | None:
    return rd.recall_at_fraction(positives, rd.PRIMARY_FRACTION)


def stage2_guards(positives: Sequence[rd.RankedPositive]) -> list[rd.Guard]:
    """E6 deciding guards."""
    near = [p for p in positives if p.strata["proximity_group"] in rd.DEVELOPMENT_NEAR_GROUPS]
    return [
        rd.guard(
            "faint (MARGINAL) vs PRIMARY",
            rd.stratum(positives, "role", "marginal"),
            rd.stratum(positives, "role", "primary"),
            rd.MIN_FAINT_POSITIVES,
        ),
        rd.guard(
            "near-star (zone+outer) vs control",
            near,
            rd.stratum(positives, "proximity_group", "control"),
            rd.MIN_ZONE_POSITIVES,
        ),
    ]


def descriptive_guards(positives: Sequence[rd.RankedPositive]) -> list[rd.Guard]:
    """E6 descriptive views (never deciding)."""
    return [
        rd.guard(
            "near-star (zone+outer) vs intermediate+control",
            rd.stratum(positives, "near_star", "zone+outer"),
            rd.stratum(positives, "near_star", "intermediate+control"),
            rd.MIN_ZONE_POSITIVES,
        ),
        rd.guard(
            "zone vs control",
            rd.stratum(positives, "proximity_group", "zone"),
            rd.stratum(positives, "proximity_group", "control"),
            rd.MIN_ZONE_POSITIVES,
        ),
    ]


def development_level(recall: Interval) -> str:
    """The AS-037 decision-rule level on development CV (descriptive only)."""
    if recall.point is None or recall.lower is None:
        return "n/a"
    if recall.upper < rd.USEFUL_RECALL:
        return "below useful (upper < 0.50)"
    if recall.point >= rd.USEFUL_RECALL and recall.lower >= rd.USEFUL_LOWER:
        return "useful level (>= 0.50, lower >= 0.30)"
    return "indeterminate"


def paired_difference(
    a: Sequence[rd.RankedPositive], b: Sequence[rd.RankedPositive], label: str, resamples: int
) -> Interval:
    """E12: recall@5 %(a) - recall@5 %(b) on the same resampled groups."""
    b_q = {(p.field_id, p.designation): p.q for p in b}

    def statistic(sample: Sequence[rd.RankedPositive]) -> float | None:
        total = sum(p.weight for p in sample)
        if total == 0:
            return None
        hit_a = sum(p.weight for p in sample if p.q <= rd.PRIMARY_FRACTION)
        hit_b = sum(p.weight for p in sample if b_q[(p.field_id, p.designation)] <= rd.PRIMARY_FRACTION)
        return (hit_a - hit_b) / total

    return _ci(a, statistic, label, resamples)


def family_of(name: str) -> str:
    return name.split(":")[0]


def evaluate_ranker(
    name: str,
    positives: Sequence[rd.RankedPositive],
    rows_by_field: Mapping[str, Sequence[Mapping]],
    fold_of_field: Mapping[str, int],
    models: Sequence[FoldModel],
    sensitivity: Mapping[str, float | None],
    resamples: int,
) -> RankerResult:
    tag = f"AS-039/{name}"
    fractions = (rd.PRIMARY_FRACTION, *rd.SECONDARY_FRACTIONS)
    recall = _ci(positives, recall5, f"{tag}/recall5", resamples)
    guards = stage2_guards(positives)
    strata_out = []
    for key in STRATA_KEYS:
        for value in sorted({p.strata[key] for p in positives}):
            members = rd.stratum(positives, key, value)
            strata_out.append(
                StratumResult(
                    key=key,
                    value=value,
                    objects=rd.object_count(members),
                    auc=rd.within_field_auc(members),
                    recall_5=recall5(members),
                )
            )
    fields_out = []
    for field_id, rows in rows_by_field.items():
        members = [p for p in positives if p.field_id == field_id]
        fields_out.append(
            FieldResult(
                field_id=field_id,
                fold=fold_of_field[field_id],
                positives=rd.object_count(members),
                background=sum(r["label"] == rd.BACKGROUND for r in rows),
                auc=rd.within_field_auc(members),
                recall_5=recall5(members),
            )
        )
    fold_recall = {
        str(k): recall5([p for p in positives if fold_of_field[p.field_id] == k]) for k in range(rd.CV_FOLDS)
    }
    qs = sorted(p.q for p in positives)
    return RankerResult(
        ranker=name,
        family=family_of(name),
        selectable=is_combined(name),
        objects=rd.object_count(positives),
        fields_with_positive=len({p.field_id for p in positives}),
        recall_5=recall,
        auc=_ci(positives, rd.within_field_auc, f"{tag}/auc", resamples),
        recall={f"{f:g}": rd.recall_at_fraction(positives, f) for f in fractions},
        recall_at_budget={str(k): rd.recall_at_budget(positives, k) for k in rd.SECONDARY_BUDGETS},
        enrichment={f"{f:g}": rd.enrichment(positives, f) for f in fractions},
        median_q=statistics.median(qs) if qs else None,
        fold_recall_5=fold_recall,
        guards=guards,
        guards_passed=all(g.evaluable and g.passed for g in guards),
        descriptive_guards=descriptive_guards(positives),
        development_level=development_level(recall),
        strata=strata_out,
        fields=fields_out,
        fold_models=list(models),
        sensitivity=dict(sensitivity),
        paired_difference={},
    )


class Selection(BaseModel):
    outcome: str  # "ADVANCE" / "NO ADVANCE"
    selected: str | None
    comparator: str
    eligible: list[str]
    excluded: dict[str, list[str]]
    best_eligible: str | None
    tie_rule_applied: bool
    reasons: list[str]


ADVANCE = "ADVANCE"
NO_ADVANCE = "NO ADVANCE"


def _guard_reasons(r: RankerResult) -> list[str]:
    out = []
    for g in r.guards:
        if not g.evaluable:
            out.append(f"{g.name}: not evaluable (n {g.protected_n:g})")
        elif not g.passed:
            out.append(
                f"{g.name}: {g.protected_recall:.3f} - {g.reference_recall:.3f} = {g.difference:+.3f} "
                f"< -{rd.PROTECTION_MARGIN:.2f}"
            )
    return out


def select(results: Sequence[RankerResult]) -> Selection:
    """E7, mechanically."""
    combined = [r for r in results if r.selectable]
    order = {r.ranker: i for i, r in enumerate(sorted(combined, key=lambda r: (r.ranker != "M1", m2_c(r.ranker) if r.ranker != "M1" else 0)))}
    eligible = [r for r in combined if r.guards_passed]
    excluded = {r.ranker: _guard_reasons(r) for r in combined if not r.guards_passed}
    b1 = [r for r in results if r.family == "B1"]
    comparator = max(b1, key=lambda r: (r.recall_5.point, -b1.index(r)))
    reasons = []
    if not eligible:
        reasons.append("no M1/M2 candidate passes both development guards")
        return Selection(
            outcome=NO_ADVANCE,
            selected=None,
            comparator=comparator.ranker,
            eligible=[],
            excluded=excluded,
            best_eligible=None,
            tie_rule_applied=False,
            reasons=reasons,
        )
    best = max(eligible, key=lambda r: (r.recall_5.point, -order[r.ranker]))
    selected, tie = best, False
    m1 = next((r for r in eligible if r.ranker == "M1"), None)
    if best.ranker != "M1" and m1 is not None and m1.recall_5.point >= best.recall_5.point - rd.SELECTION_TIE:
        selected, tie = m1, True
        reasons.append(
            f"M1 {m1.recall_5.point:.3f} within {rd.SELECTION_TIE} of {best.ranker} {best.recall_5.point:.3f}"
        )
    reasons.append(f"selected {selected.ranker}: highest CV recall@5 % among guard-passing M1/M2")
    return Selection(
        outcome=ADVANCE,
        selected=selected.ranker,
        comparator=comparator.ranker,
        eligible=[r.ranker for r in eligible],
        excluded=excluded,
        best_eligible=best.ranker,
        tie_rule_applied=tie,
        reasons=reasons,
    )


# ---------------------------------------------------------------------------
# Counterexamples (E10)
# ---------------------------------------------------------------------------


def _positive_entry(p: rd.RankedPositive) -> dict:
    return {"field_id": p.field_id, "designation": p.designation, "q": round(p.q, 4), "strata": p.strata}


def counterexamples(
    result: RankerResult,
    positives: Sequence[rd.RankedPositive],
    comparator: Sequence[rd.RankedPositive] | None,
    detailed: bool,
) -> dict:
    overall = result.recall_5.point or 0.0
    out = {
        "fields_auc_below_half": [
            f.model_dump()
            for f in result.fields
            if f.auc is not None and f.positives >= fe.COUNTEREXAMPLE_MIN_POSITIVES and f.auc < 0.5
        ],
        "strata_recall_gap": [
            s.model_dump()
            for s in result.strata
            if s.recall_5 is not None and s.recall_5 < overall - STRATUM_GAP_REPORT
        ],
        "bottom_half_positives": [_positive_entry(p) for p in sorted(positives, key=lambda p: -p.q) if p.q > 0.5],
    }
    if detailed:
        missed = [p for p in positives if p.q > rd.PRIMARY_FRACTION]
        out["missed_top5_by_stratum"] = {
            key: dict(sorted(Counter(p.strata[key] for p in missed).items()))
            for key in ("role", "proximity_group", "depth_margin", "mask_state", "crowding")
        }
        if comparator is not None:
            cq = {(p.field_id, p.designation): p.q for p in comparator}
            out["comparator_only_top5"] = [
                _positive_entry(p)
                | {"comparator_q": round(cq[(p.field_id, p.designation)], 4)}
                for p in positives
                if p.q > rd.PRIMARY_FRACTION and cq[(p.field_id, p.designation)] <= rd.PRIMARY_FRACTION
            ]
            out["ranker_only_top5"] = [
                _positive_entry(p)
                | {"comparator_q": round(cq[(p.field_id, p.designation)], 4)}
                for p in positives
                if p.q <= rd.PRIMARY_FRACTION and cq[(p.field_id, p.designation)] > rd.PRIMARY_FRACTION
            ]
    return out


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


class Construction(BaseModel):
    generated_at: datetime
    stage: str
    code_commit: str | None
    manifest_sha256: str
    table_sha256: str
    frozen_features_sha256: str
    features: list[tuple[str, int]]
    development_fields: int
    development_groups: int
    ranked_tracklets: int
    labels: dict[str, int]
    positive_objects: float
    positive_fields: int
    folds: dict[str, list[str]]  # fold -> groups
    fold_positive_objects: dict[str, float]
    rankers: list[RankerResult]
    selection: Selection
    counterexamples: dict[str, dict]


def git_commit(root: Path) -> str | None:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--", "app/validation"],
            cwd=root, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return head + ("+dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return None


def construct(
    root: Path,
    resamples: int = rd.BOOTSTRAP_RESAMPLES,
    progress: Callable[[str], None] = lambda m: None,
) -> tuple[Construction, dict[str, list[rd.RankedPositive]], dict]:
    manifest, rows, fields = load_development(root)
    features = load_frozen_features(root)
    groups = development_groups(manifest)
    fold_of_group = fold_of_groups(groups)
    rows_by_field: dict[str, list[Mapping]] = defaultdict(list)
    for r in rows:
        rows_by_field[r["field_id"]].append(r)
    group_of_field = {f: rs[0]["group"] for f, rs in rows_by_field.items()}
    fold_of_field = {f: fold_of_group[g] for f, g in group_of_field.items()}
    strata = fe.positive_strata(rows, fields)
    percentiles = percentile_matrix(rows_by_field, features)

    results: list[RankerResult] = []
    ranked: dict[str, list[rd.RankedPositive]] = {}
    for name in ranker_names(features):
        progress(f"cross-validating {name}")
        scores, models = cross_validated_scores(
            name, rows_by_field, percentiles, features, fold_of_field, group_of_field
        )
        positives = rank_positives(rows_by_field, scores, strata)
        sensitivity = {}
        for label, kwargs in (
            ("without background sharing a detection with a positive",
             {"exclude_background": lambda r: r["shares_detection_with_positive"] == "1"}),
            (f"without {fe.CROSS_SPLIT_DESIGNATION}",
             {"exclude_designations": frozenset({fe.CROSS_SPLIT_DESIGNATION})}),
        ):
            alt = rank_positives(rows_by_field, scores, strata, **kwargs)
            sensitivity[label + " (recall@5%)"] = recall5(alt)
            sensitivity[label + " (AUC)"] = rd.within_field_auc(alt)
        results.append(
            evaluate_ranker(name, positives, rows_by_field, fold_of_field, models, sensitivity, resamples)
        )
        ranked[name] = positives

    selection = select(results)
    for r in results:
        if r.selectable:
            r.paired_difference = {
                f"- {selection.comparator}": paired_difference(
                    ranked[r.ranker], ranked[selection.comparator], f"AS-039/{r.ranker}/minus-comparator", resamples
                ),
                "- B0": paired_difference(ranked[r.ranker], ranked["B0"], f"AS-039/{r.ranker}/minus-B0", resamples),
            }
    examples = {}
    for r in results:
        if r.selectable or r.ranker == selection.comparator:
            detailed = r.selectable and (selection.selected in (None, r.ranker))
            examples[r.ranker] = counterexamples(
                r, ranked[r.ranker], ranked[selection.comparator] if detailed else None, detailed
            )
    reference = ranked["B0"]
    construction = Construction(
        generated_at=datetime.now(timezone.utc),
        stage=STAGE,
        code_commit=git_commit(root),
        manifest_sha256=rd.file_sha256(root / fe.MANIFEST_FILE),
        table_sha256=rd.file_sha256(root / AS038_DIR / fe.TABLE_FILE),
        frozen_features_sha256=rd.file_sha256(root / FROZEN_FEATURES_FILE),
        features=features,
        development_fields=len(rows_by_field),
        development_groups=len(groups),
        ranked_tracklets=len(rows),
        labels=dict(Counter(r["label"] for r in rows)),
        positive_objects=rd.object_count(reference),
        positive_fields=len({p.field_id for p in reference}),
        folds={str(k): sorted(g for g, f in fold_of_group.items() if f == k) for k in range(rd.CV_FOLDS)},
        fold_positive_objects={
            str(k): rd.object_count([p for p in reference if fold_of_field[p.field_id] == k])
            for k in range(rd.CV_FOLDS)
        },
        rankers=results,
        selection=selection,
        counterexamples=examples,
    )
    frozen = frozen_spec(construction, rows_by_field, percentiles, features) if selection.outcome == ADVANCE else None
    return construction, ranked, frozen


def ranker_spec(
    name: str,
    rows_by_field: Mapping[str, Sequence[Mapping]],
    percentiles: Mapping[str, np.ndarray],
    features: Sequence[tuple[str, int]],
) -> dict:
    inputs = [{"feature": n, "direction": d} for n, d in features]
    if name == "M1":
        return {
            "ranker": "M1",
            "kind": "unweighted mean of oriented within-quadrant-night percentiles",
            "inputs": inputs,
            "weights": {n: 1 / len(features) for n, _ in features},
            "intercept": 0.0,
            "fitted": False,
        }
    if name.startswith("M2:"):
        c = m2_c(name)
        x, y, s = training_set(rows_by_field, percentiles, list(rows_by_field))
        w, b = logistic_fit(x, y, s, c)
        return {
            "ranker": name,
            "kind": "L2 logistic regression linear predictor on oriented within-quadrant-night percentiles",
            "inputs": inputs,
            "C": c,
            "weights": {n: float(v) for (n, _), v in zip(features, w)},
            "intercept": b,
            "fitted": True,
            "fit": "refit once on all 56 development quadrant-nights (E5/E8); positive vs background, "
                   "each quadrant-night total weight 1, intercept unpenalised",
            "training_rows": int(len(y)),
            "training_positive_rows": int(y.sum()),
        }
    feature = name.removeprefix("B1:")
    return {
        "ranker": name,
        "kind": "single frozen feature, oriented within-quadrant-night percentile",
        "inputs": [i for i in inputs if i["feature"] == feature],
        "weights": {feature: 1.0},
        "intercept": 0.0,
        "fitted": False,
    }


def frozen_spec(
    construction: Construction,
    rows_by_field: Mapping[str, Sequence[Mapping]],
    percentiles: Mapping[str, np.ndarray],
    features: Sequence[tuple[str, int]],
) -> dict:
    sel = construction.selection
    by_name = {r.ranker: r for r in construction.rankers}
    return {
        "ticket": "AS-039",
        "stage": STAGE,
        "for": "AS-040 one-shot validation (validation split only, AS-037 section 7 unchanged)",
        "code_commit": construction.code_commit,
        "manifest_sha256": construction.manifest_sha256,
        "table_sha256": construction.table_sha256,
        "frozen_features_sha256": construction.frozen_features_sha256,
        "representation": {
            "unit": "one quadrant-night; every BUILT tracklet is ranked",
            "percentile": "ranking_design.within_field_percentile(values, direction) over all built tracklets "
                          "of the quadrant-night, label-free (mid-rank, higher = reviewed earlier)",
            "missing": f"percentile {MISSING_PERCENTILE} (after every present value)",
            "score": "sum_k weight_k * percentile_k + intercept; higher = reviewed earlier",
            "q": "ranking_design.background_rank_fraction (ties count half); best-scored positive per object",
        },
        "ranker": ranker_spec(sel.selected, rows_by_field, percentiles, features),
        "comparator": ranker_spec(sel.comparator, rows_by_field, percentiles, features),
        "development_cv": {
            name: {
                "recall_5": by_name[name].recall_5.model_dump(),
                "auc": by_name[name].auc.model_dump(),
                "guards": [g.model_dump() for g in by_name[name].guards],
            }
            for name in (sel.selected, sel.comparator)
        },
        "selection": sel.model_dump(),
        "not_allowed": [
            "any feature, transform, weight, intercept or C other than the above",
            "bright-star proximity / proximity group / star separations (context only)",
            "speed and position angle (context only)",
            "identification status, designation, SkyBoT prediction or residual",
            "re-selection or tuning on validation",
        ],
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

_f = fe._f


def _ci_text(i: Interval) -> str:
    return f"{_f(i.point)} [{_f(i.lower)}, {_f(i.upper)}]"


def _guard_text(g: rd.Guard) -> str:
    lo, hi = g.newcombe_95
    state = "n/e" if not g.evaluable else ("PASS" if g.passed else "FAIL")
    return (
        f"{_f(g.protected_recall, 2)} vs {_f(g.reference_recall, 2)} = {_f(g.difference, 2)} "
        f"[{_f(lo, 2)}, {_f(hi, 2)}] (n {g.protected_n:g}/{g.reference_n:g}) {state}"
    )


def render_markdown(c: Construction) -> str:
    sel = c.selection
    lines = [
        "# AS-039 candidate ranker construction (stage 2, development only; generated)",
        "",
        f"Generated {c.generated_at:%Y-%m-%d %H:%M UTC} from code `{c.code_commit}`. Interpretation: "
        "`as039_findings.md`. Validation split not loaded.",
        "",
        f"Manifest `{c.manifest_sha256[:16]}…`, AS-038 table `{c.table_sha256[:16]}…`, frozen list "
        f"`{c.frozen_features_sha256[:16]}…`. {c.development_fields} development quadrant-nights in "
        f"{c.development_groups} groups, {c.ranked_tracklets} ranked tracklets {c.labels}; "
        f"{c.positive_objects:g} positive object-nights in {c.positive_fields} quadrant-nights.",
        "",
        "Inputs: " + ", ".join(f"`{n}` ({'+' if d > 0 else '−'})" for n, d in c.features)
        + " as within-quadrant-night percentiles.",
        "",
        "Folds (groups / positive object-nights): "
        + "; ".join(f"{k}: {len(g)} / {c.fold_positive_objects[k]:g}" for k, g in c.folds.items()),
        "",
        "## Selection",
        "",
        f"**{sel.outcome}**" + (f": `{sel.selected}`" if sel.selected else "")
        + f"; comparator `{sel.comparator}`. Eligible (both guards pass): "
        + (", ".join(f"`{e}`" for e in sel.eligible) or "none") + ".",
        "",
    ]
    for name, reasons in sel.excluded.items():
        lines.append(f"- `{name}` excluded: " + "; ".join(reasons))
    lines += [f"- {r}" for r in sel.reasons]
    lines += [
        "",
        "## All rankers (grouped 5-fold CV, pooled out-of-fold)",
        "",
        "recall@5 % and AUC with 95 % group bootstrap (2000). Guards: recall@5 % protected vs reference "
        "= difference [Newcombe 95 %] (n), pass if ≥ −0.20.",
        "",
        "| ranker | recall@5 % [95 %] | AUC [95 %] | faint guard (MARGINAL vs PRIMARY) | near-star guard (zone+outer vs control) | both pass | dev level (descriptive) |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in c.rankers:
        lines.append(
            f"| `{r.ranker}` | {_ci_text(r.recall_5)} | {_ci_text(r.auc)} | {_guard_text(r.guards[0])} "
            f"| {_guard_text(r.guards[1])} | {'yes' if r.guards_passed else 'no'} | {r.development_level} |"
        )
    lines += [
        "",
        "## Secondary metrics",
        "",
        "| ranker | recall@1/2/5/10/20 % | recall@K 10/25/50 | enrichment@1/5 % | median q | per-fold recall@5 % |",
        "|---|---|---|---|---|---|",
    ]
    for r in c.rankers:
        lines.append(
            f"| `{r.ranker}` | {' / '.join(_f(r.recall[k], 2) for k in ('0.01', '0.02', '0.05', '0.1', '0.2'))} "
            f"| {' / '.join(_f(r.recall_at_budget[k], 2) for k in ('10', '25', '50'))} "
            f"| {_f(r.enrichment['0.01'], 1)} / {_f(r.enrichment['0.05'], 1)} | {_f(r.median_q)} "
            f"| {' / '.join(_f(r.fold_recall_5[str(k)], 2) for k in range(rd.CV_FOLDS))} |"
        )
    lines += [
        "",
        "## Descriptive guard views (never deciding)",
        "",
        "| ranker | zone+outer vs intermediate+control | zone only vs control |",
        "|---|---|---|",
    ]
    for r in c.rankers:
        lines.append(f"| `{r.ranker}` | " + " | ".join(_guard_text(g) for g in r.descriptive_guards) + " |")
    lines += ["", "## Strata (recall@5 % / AUC, object-nights)", ""]
    first = c.rankers[0].strata
    lines.append("| ranker | " + " | ".join(f"{s.key}={s.value} (n {s.objects:g})" for s in first) + " |")
    lines.append("|---|" + "---|" * len(first))
    for r in c.rankers:
        lines.append(f"| `{r.ranker}` | " + " | ".join(f"{_f(s.recall_5, 2)} / {_f(s.auc, 2)}" for s in r.strata) + " |")
    lines += [
        "",
        "## Paired recall@5 % differences (descriptive, group bootstrap)",
        "",
        "| ranker | difference [95 %] |",
        "|---|---|",
    ]
    for r in c.rankers:
        for name, i in r.paired_difference.items():
            lines.append(f"| `{r.ranker}` {name} | {_ci_text(i)} |")
    lines += ["", "## M2 fold coefficients (descriptive)", ""]
    names = [n for n, _ in c.features]
    lines.append("| ranker | fold | " + " | ".join(f"`{n}`" for n in names) + " | intercept |")
    lines.append("|---|---|" + "---|" * len(names) + "---|")
    for r in c.rankers:
        for m in r.fold_models:
            if m.coefficients is None:
                continue
            lines.append(
                f"| `{r.ranker}` | {m.fold} | " + " | ".join(f"{m.coefficients[n]:.3f}" for n in names)
                + f" | {m.intercept:.3f} |"
            )
    lines += ["", "## Sensitivity (descriptive)", "", "| ranker | analysis | value |", "|---|---|---|"]
    for r in c.rankers:
        if r.selectable:
            for name, v in r.sensitivity.items():
                lines.append(f"| `{r.ranker}` | {name} | {_f(v)} |")
    lines += ["", "## Counterexamples", ""]
    for name, ce in c.counterexamples.items():
        lines.append(
            f"- `{name}`: {len(ce['fields_auc_below_half'])} quadrant-nights (≥ 3 positives) with AUC < 0.5"
            + (": " + ", ".join(f"{x['field_id']} ({_f(x['auc'], 2)}, n {x['positives']:g})" for x in ce["fields_auc_below_half"]) if ce["fields_auc_below_half"] else "")
            + "; strata with recall@5 % more than 0.20 below overall: "
            + (", ".join(f"{s['key']}={s['value']} ({_f(s['recall_5'], 2)}, n {s['objects']:g})" for s in ce["strata_recall_gap"]) or "none")
            + f"; bottom-half positives: {len(ce['bottom_half_positives'])}"
        )
    for name, ce in c.counterexamples.items():
        if "missed_top5_by_stratum" not in ce:
            continue
        lines += ["", f"### `{name}`: positives outside the top 5 %", ""]
        for key, counts in ce["missed_top5_by_stratum"].items():
            lines.append(f"- {key}: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
        if "comparator_only_top5" in ce:
            lines.append(
                f"- top 5 % by comparator `{sel.comparator}` only: {len(ce['comparator_only_top5'])}; "
                f"by `{name}` only: {len(ce['ranker_only_top5'])}"
            )
        rows_ = ce["bottom_half_positives"]
        if rows_:
            lines += ["", "| field | object | q | role | group | depth | mask | crowding |", "|---|---|---|---|---|---|---|---|"]
            for x in rows_:
                s = x["strata"]
                lines.append(
                    f"| {x['field_id']} | {x['designation']} | {x['q']:.3f} | {s['role']} | {s['proximity_group']} "
                    f"| {s['depth_margin']} | {s['mask_state']} | {s['crowding']} |"
                )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    ev = sub.add_parser("evaluate", help="stage-2 CV, guards, selection and frozen ranker (offline)")
    ev.add_argument("--root", type=Path, default=Path("."))
    ev.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    construction, _, frozen = construct(args.root, progress=lambda m: print(m, flush=True))
    (args.out_dir / RESULTS_FILE).write_text(construction.model_dump_json(indent=1) + "\n")
    (args.out_dir / SELECTION_FILE).write_text(construction.selection.model_dump_json(indent=1) + "\n")
    (args.out_dir / REPORT_FILE).write_text(render_markdown(construction))
    frozen_path = args.out_dir / FROZEN_FILE
    if frozen is not None:
        frozen_path.write_text(json.dumps(frozen, indent=1) + "\n")
    elif frozen_path.exists():
        frozen_path.unlink()
    print(f"{construction.selection.outcome}: {construction.selection.selected}; "
          f"comparator {construction.selection.comparator}")


if __name__ == "__main__":
    main()
