import hashlib
import math
from pathlib import Path

import numpy as np
import pytest

from app.validation import feature_evaluation as fe
from app.validation import ranker_construction as rc
from app.validation import ranking_design as rd

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def manifest() -> dict:
    return fe.load_manifest(ROOT)


# --- inputs, split guard and leakage ------------------------------------------


def test_frozen_features_are_the_eight_as038_features_in_as037_directions() -> None:
    features = rc.load_frozen_features(ROOT)
    assert [n for n, _ in features] == list(rc.FROZEN_FEATURES)
    assert len(features) == 8
    assert all(rd.CANDIDATE_FEATURES[n] == d for n, d in features)
    for excluded in ("fit_max_residual_arcsec", "magnitude_range_sigma", "magnitude_chi2", "edge_detection_count"):
        assert excluded not in rc.FROZEN_FEATURES


def test_ranker_inputs_hold_no_identity_or_context_column() -> None:
    for column in (*fe.IDENTITY_COLUMNS, *fe.CONTEXT_COLUMNS, "label", "mask_bits_union"):
        assert column not in rc.FROZEN_FEATURES


def test_stage_two_split_guard_refuses_validation(manifest) -> None:
    validation = next(q["field_id"] for q in manifest["quadrant_nights"] if q["split"] == rd.VALIDATION)
    with pytest.raises(rd.SplitError):
        rd.require_split(manifest, validation, rc.STAGE)
    assert rc.STAGE == rd.STAGE_RANKING_CONSTRUCTION


def test_development_groups_are_the_27_manifest_groups(manifest) -> None:
    groups = rc.development_groups(manifest)
    assert len(groups) == 27
    validation_groups = {q["group"] for q in manifest["quadrant_nights"] if q["split"] == rd.VALIDATION}
    assert not set(groups) & validation_groups


def test_folds_follow_sha256_group_order_round_robin(manifest) -> None:
    groups = rc.development_groups(manifest)
    folds = rc.fold_of_groups(groups)
    order = sorted(groups, key=lambda g: hashlib.sha256(f"AS-037:{g}".encode()).hexdigest())
    assert [folds[g] for g in order] == [i % 5 for i in range(len(order))]
    sizes = sorted(list(folds.values()).count(k) for k in range(5))
    assert sizes == [5, 5, 5, 6, 6]
    assert rc.fold_of_groups(list(reversed(groups))) == folds


# --- representation and rankers -------------------------------------------------


def _rows(values, labels=None, extra=None):
    labels = labels or [rd.BACKGROUND] * len(values)
    rows = []
    for i, (v, label) in enumerate(zip(values, labels)):
        row = {name: v for name in rc.FROZEN_FEATURES}
        row.update(tracklet_id=f"t{i}", label=label, group="G", night="n", eval_designation=None)
        row.update(extra or {})
        rows.append(row)
    return rows


def test_percentiles_are_oriented_label_free_and_missing_ranks_last() -> None:
    features = [("min_snr", +1), ("fit_rms_residual_arcsec", -1)]
    rows = _rows([1.0, 2.0, None, 3.0])
    x = rc.percentile_matrix({"f": rows}, features)["f"]
    assert list(x[:, 0]) == [pytest.approx(1 / 6), pytest.approx(0.5), 0.0, pytest.approx(5 / 6)]
    assert list(x[:, 1]) == [pytest.approx(5 / 6), pytest.approx(0.5), 0.0, pytest.approx(1 / 6)]
    relabelled = rc.percentile_matrix({"f": _rows([1.0, 2.0, None, 3.0], [rd.POSITIVE] * 4)}, features)["f"]
    assert np.array_equal(x, relabelled)


def test_context_columns_cannot_change_a_score() -> None:
    features = rc.load_frozen_features(ROOT)
    a = _rows([1.0, 2.0, 3.0], extra={"ctx_proximity_group": "zone", "eval_role": "marginal"})
    b = _rows([1.0, 2.0, 3.0], extra={"ctx_proximity_group": "control", "eval_role": "primary"})
    xa = rc.percentile_matrix({"f": a}, features)["f"]
    xb = rc.percentile_matrix({"f": b}, features)["f"]
    for name in ("M1", "B1:min_snr", "B0"):
        assert rc.fixed_scores(name, "f", a, xa, features) == rc.fixed_scores(name, "f", b, xb, features)


def test_m1_is_the_unweighted_mean_of_percentiles() -> None:
    features = [("min_snr", +1), ("median_snr", +1)]
    x = np.array([[0.2, 0.6], [0.9, 0.1]])
    assert rc.fixed_scores("M1", "f", _rows([0, 0]), x, features) == [pytest.approx(0.4), pytest.approx(0.5)]
    assert rc.fixed_scores("B1:median_snr", "f", _rows([0, 0]), x, features) == [0.6, 0.1]


def test_family_is_exactly_b0_b1_m1_and_four_m2() -> None:
    names = rc.ranker_names(rc.load_frozen_features(ROOT))
    assert names[0] == "B0"
    assert [n for n in names if n.startswith("B1:")] == [f"B1:{f}" for f in rc.FROZEN_FEATURES]
    assert [n for n in names if rc.is_combined(n)] == ["M1", "M2:C=0.01", "M2:C=0.1", "M2:C=1", "M2:C=10"]
    assert len(names) == 1 + 8 + 1 + 4


def test_logistic_fit_reaches_the_penalised_optimum() -> None:
    rng = np.random.default_rng(0)
    x = rng.random((400, 3))
    y = (x @ np.array([3.0, -2.0, 0.0]) + rng.normal(0, 0.5, 400) > 0.5).astype(float)
    s = np.full(400, 1 / 400)
    for c in rd.LOGISTIC_C_GRID:
        w, b = rc.logistic_fit(x, y, s, c)
        p = 1 / (1 + np.exp(-(x @ w + b)))
        assert np.allclose(w + c * x.T @ (s * (p - y)), 0, atol=1e-8)
        assert abs(c * np.sum(s * (p - y))) < 1e-8  # intercept unpenalised
    small, _ = rc.logistic_fit(x, y, s, 0.01)
    large, _ = rc.logistic_fit(x, y, s, 10.0)
    assert np.linalg.norm(small) < np.linalg.norm(large)


def test_training_set_weights_quadrant_nights_equally_and_drops_auxiliary() -> None:
    rows = {
        "a": _rows([1, 2, 3, 4], [rd.POSITIVE, rd.BACKGROUND, rd.BACKGROUND, rd.AUXILIARY]),
        "b": _rows([1, 2], [rd.BACKGROUND, rd.BACKGROUND]),
    }
    x = {f: np.arange(len(r) * 8, dtype=float).reshape(len(r), 8) for f, r in rows.items()}
    X, y, s = rc.training_set(rows, x, ["a", "b"])
    assert len(y) == 5 and y.tolist() == [1, 0, 0, 0, 0]
    assert s[:3].sum() == pytest.approx(1) and s[3:].sum() == pytest.approx(1)


def test_cross_validated_m2_never_scores_a_field_with_a_model_that_saw_it() -> None:
    features = [(n, rd.CANDIDATE_FEATURES[n]) for n in rc.FROZEN_FEATURES]
    rng = np.random.default_rng(1)
    rows_by_field, percentiles = {}, {}
    for i in range(10):
        labels = [rd.POSITIVE] + [rd.BACKGROUND] * 9
        rows_by_field[f"f{i}"] = _rows(list(range(10)), labels)
        percentiles[f"f{i}"] = rng.random((10, 8))
    fold_of_field = {f"f{i}": i % 5 for i in range(10)}
    group_of_field = {f"f{i}": f"G{i}" for i in range(10)}
    scores, models = rc.cross_validated_scores(
        "M2:C=1", rows_by_field, percentiles, features, fold_of_field, group_of_field
    )
    for m in models:
        assert set(m.fields) == {f for f, k in fold_of_field.items() if k == m.fold}
        train = [f for f, k in fold_of_field.items() if k != m.fold]
        w, b = rc.logistic_fit(*rc.training_set(rows_by_field, percentiles, train), 1.0)
        for f in m.fields:
            assert scores[f] == pytest.approx(list(percentiles[f] @ w + b))


# --- guards and selection -------------------------------------------------------


_SERIAL = iter(range(10**6))


def _positive(q, role="primary", group="control", field="f"):
    p = rd.RankedPositive(
        field_id=field, group="G", designation=f"obj{next(_SERIAL)}",
        night="n", q=q, rank=1,
        strata={"role": role, "proximity_group": group,
                "near_star": "zone+outer" if group in ("zone", "outer") else "intermediate+control"},
    )
    return p


def test_stage_two_near_star_guard_is_zone_plus_outer_vs_control() -> None:
    positives = (
        [_positive(0.01, group="outer") for _ in range(6)]
        + [_positive(0.5, group="zone") for _ in range(6)]
        + [_positive(0.01, group="control") for _ in range(10)]
        + [_positive(0.5, group="intermediate") for _ in range(10)]
    )
    rd.object_weights(positives)
    faint, near = rc.stage2_guards(positives)
    assert near.protected_n == 12 and near.reference_n == 10
    assert near.difference == pytest.approx(0.5 - 1.0)
    assert near.passed is False
    assert faint.evaluable is False  # no MARGINAL


def _result(name, recall, passed=True):
    guard = rd.Guard(name="g", protected_n=50, reference_n=50, protected_recall=0.5, reference_recall=0.5,
                     difference=0.0 if passed else -0.3, newcombe_95=(None, None), evaluable=True, passed=passed)
    interval = rc.Interval(point=recall, lower=None, upper=None)
    return rc.RankerResult(
        ranker=name, family=rc.family_of(name), selectable=rc.is_combined(name), objects=1,
        fields_with_positive=1, recall_5=interval, auc=interval, recall={}, recall_at_budget={},
        enrichment={}, median_q=None, fold_recall_5={}, guards=[guard, guard], guards_passed=passed,
        descriptive_guards=[], development_level="", strata=[], fields=[], fold_models=[],
        sensitivity={}, paired_difference={},
    )


def test_selection_takes_the_best_guard_passing_combined_ranker() -> None:
    sel = rc.select([
        _result("B0", 0.05), _result("B1:a", 0.7), _result("B1:b", 0.6),
        _result("M1", 0.50), _result("M2:C=0.1", 0.60), _result("M2:C=1", 0.80, passed=False),
    ])
    assert sel.outcome == rc.ADVANCE and sel.selected == "M2:C=0.1"
    assert sel.comparator == "B1:a"
    assert "M2:C=1" in sel.excluded and not sel.tie_rule_applied


def test_selection_prefers_m1_within_0_02() -> None:
    sel = rc.select([_result("B1:a", 0.5), _result("M1", 0.581), _result("M2:C=1", 0.60)])
    assert sel.selected == "M1" and sel.tie_rule_applied and sel.best_eligible == "M2:C=1"


def test_tie_rule_cannot_rescue_a_guard_failing_m1() -> None:
    sel = rc.select([_result("B1:a", 0.5), _result("M1", 0.60, passed=False), _result("M2:C=1", 0.59)])
    assert sel.selected == "M2:C=1"


def test_no_advance_when_every_combined_ranker_fails_a_guard() -> None:
    sel = rc.select([
        _result("B1:a", 0.9), _result("M1", 0.7, passed=False), _result("M2:C=10", 0.8, passed=False),
    ])
    assert sel.outcome == rc.NO_ADVANCE and sel.selected is None
    assert set(sel.excluded) == {"M1", "M2:C=10"}
    assert sel.comparator == "B1:a"  # reported, B1 never selectable


def test_development_level_is_descriptive_mapping_of_the_as037_thresholds() -> None:
    assert rc.development_level(rc.Interval(point=0.6, lower=0.4, upper=0.7)).startswith("useful")
    assert rc.development_level(rc.Interval(point=0.3, lower=0.2, upper=0.45)).startswith("below")
    assert rc.development_level(rc.Interval(point=0.55, lower=0.25, upper=0.7)) == "indeterminate"
