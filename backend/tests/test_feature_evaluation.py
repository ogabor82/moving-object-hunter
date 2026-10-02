import gzip
import json
import math
from pathlib import Path

import pytest

from app.validation import feature_evaluation as fe
from app.validation import ranking_design as rd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "validation/results/as038"


@pytest.fixture(scope="module")
def manifest() -> dict:
    return fe.load_manifest(ROOT)


def validation_ids(manifest) -> list[str]:
    return [q["field_id"] for q in manifest["quadrant_nights"] if q["split"] == rd.VALIDATION]


# --- split guard and inputs -------------------------------------------------


def test_development_nights_are_the_56_guarded_development_quadrant_nights(manifest) -> None:
    nights = fe.development_nights(manifest)
    assert len(nights) == 56
    assert {q["split"] for q in nights} == {rd.DEVELOPMENT}
    assert not {q["field_id"] for q in nights} & set(validation_ids(manifest))


def test_replay_field_refuses_a_validation_quadrant_night_before_loading(manifest) -> None:
    field_id = validation_ids(manifest)[0]
    with pytest.raises(rd.SplitError):
        fe.replay_field(ROOT, manifest, field_id, [1, 2, 3])


def test_development_traces_hold_no_validation_row(manifest) -> None:
    traces = fe.load_development_traces(ROOT, manifest)
    assert not set(traces) & set(validation_ids(manifest))
    assert {"C4-2019-08-20-335-c11-q1", "C20-2019-07-28-282-c13-q1"} <= set(traces)
    recovered = [
        t for rows in traces.values() for t in rows
        if t["rate_eligible"] and t["baseline_eligible"] and t["recovered"]
    ]
    # AS-037 manifest: 402 development positive tracklet-targets.
    assert len(recovered) == manifest["positive_availability"]["development"]["positive_tracklet_targets"]


def test_eligible_targets_need_rate_and_baseline() -> None:
    rows = [
        {"designation": "a", "role": "primary", "rate_eligible": True, "baseline_eligible": True},
        {"designation": "b", "role": "marginal", "rate_eligible": True, "baseline_eligible": False},
        {"designation": "c", "role": "marginal", "rate_eligible": False, "baseline_eligible": True},
    ]
    assert fe.eligible_targets(rows) == {"a": "primary"}


def test_read_table_refuses_validation_rows(tmp_path, manifest) -> None:
    row = {k: "" for k in fe.TABLE_COLUMNS}
    row.update(field_id=validation_ids(manifest)[0], label=rd.BACKGROUND, tracklet_id="t")
    fe.write_table(tmp_path / "t.csv.gz", [row])
    with pytest.raises(rd.SplitError):
        fe.read_table(tmp_path / "t.csv.gz", manifest)


# --- leakage: what a ranker may see -----------------------------------------


def test_ranker_inputs_are_exactly_the_preregistered_candidate_features() -> None:
    assert fe.RANKER_INPUT_COLUMNS == tuple(rd.CANDIDATE_FEATURES)
    for column in (*fe.IDENTITY_COLUMNS, *fe.CONTEXT_COLUMNS):
        assert column not in fe.RANKER_INPUT_COLUMNS
    assert "ctx_proximity_group" in fe.CONTEXT_COLUMNS
    assert "ctx_angular_velocity_arcsec_per_min" in fe.CONTEXT_COLUMNS


def test_table_round_trip_is_byte_deterministic(tmp_path) -> None:
    row = {k: None for k in fe.TABLE_COLUMNS}
    row.update(field_id="F", label=rd.BACKGROUND, tracklet_id="t", min_snr=3.5)
    fe.write_table(tmp_path / "a.csv.gz", [row])
    fe.write_table(tmp_path / "b.csv.gz", [row])
    assert (tmp_path / "a.csv.gz").read_bytes() == (tmp_path / "b.csv.gz").read_bytes()
    with gzip.open(tmp_path / "a.csv.gz", "rt") as handle:
        assert handle.readline().strip().split(",") == list(fe.TABLE_COLUMNS)


# --- derived features -------------------------------------------------------


def test_sharp_abs_max_only_when_complete() -> None:
    assert fe.sharp_abs_max([0.1, -0.4, 0.2], complete=True) == 0.4
    assert fe.sharp_abs_max([0.1, None, 0.2], complete=False) is None
    assert fe.sharp_abs_max([], complete=True) is None


def test_shared_detection_tracklets_counts_other_tracklets() -> None:
    shared = fe.shared_detection_tracklets(
        {"t1": ["a", "b", "c"], "t2": ["a", "d", "e"], "t3": ["b", "d", "f"], "t4": ["x", "y", "z"]}
    )
    assert shared == {"t1": 2, "t2": 2, "t3": 2, "t4": 0}


def test_magnitude_chi2_definition() -> None:
    # equal errors: weighted mean = mean; chi2 = sum of squared deviations / sigma^2
    assert rd.magnitude_chi2([10.0, 10.2, 10.4], [0.1, 0.1, 0.1]) == pytest.approx(8.0)
    assert rd.magnitude_chi2([10.0, 10.2, 10.4], [0.1, 0.0, 0.1]) is None


# --- ranking one feature ----------------------------------------------------


def row(tid, label, value, designation=None, field="F1"):
    return {
        "field_id": field, "group": "G1", "night": "2020-01-01", "tracklet_id": tid,
        "label": label, "eval_designation": designation, "x": value,
        "shares_detection_with_positive": "0",
    }


def test_missing_values_rank_after_every_present_value(monkeypatch) -> None:
    monkeypatch.setitem(rd.CANDIDATE_FEATURES, "x", +1)
    rows = [
        row("p1", rd.POSITIVE, None, "A"),
        row("p2", rd.POSITIVE, 5.0, "B"),
        row("b1", rd.BACKGROUND, 1.0),
        row("b2", rd.BACKGROUND, None),
        row("a1", rd.AUXILIARY, 100.0),
    ]
    strata = {("F1", "A"): {}, ("F1", "B"): {}}
    ranked = {p.designation: p for p in fe.rank_feature({"F1": rows}, "x", strata)}
    assert ranked["A"].q == pytest.approx(0.75)  # above b1, tied with missing b2
    assert ranked["B"].q == 0.0  # auxiliary does not count against a positive
    assert fe.oriented_score(None, -1) == -math.inf
    assert fe.oriented_score(2.0, -1) == -2.0


def test_best_scored_positive_tracklet_counts_once(monkeypatch) -> None:
    monkeypatch.setitem(rd.CANDIDATE_FEATURES, "x", -1)  # lower first
    rows = [
        row("p1", rd.POSITIVE, 9.0, "A"),
        row("p2", rd.POSITIVE, 1.0, "A"),
        row("b1", rd.BACKGROUND, 2.0),
        row("b2", rd.BACKGROUND, 3.0),
    ]
    ranked = fe.rank_feature({"F1": rows}, "x", {("F1", "A"): {}})
    assert len(ranked) == 1 and ranked[0].q == 0.0 and ranked[0].weight == 1.0


def test_sensitivity_exclusions(monkeypatch) -> None:
    monkeypatch.setitem(rd.CANDIDATE_FEATURES, "x", +1)
    rows = [row("p1", rd.POSITIVE, 1.0, "A"), row("b1", rd.BACKGROUND, 2.0), row("b2", rd.BACKGROUND, 0.0)]
    rows[1]["shares_detection_with_positive"] = "1"
    strata = {("F1", "A"): {}}
    assert fe.rank_feature({"F1": rows}, "x", strata)[0].q == 0.5
    alt = fe.rank_feature(
        {"F1": rows}, "x", strata, exclude_background=lambda r: r["shares_detection_with_positive"] == "1"
    )
    assert alt[0].q == 0.0
    assert fe.rank_feature({"F1": rows}, "x", strata, exclude_designations=frozenset({"A"})) == []


# --- gate and redundancy ----------------------------------------------------


def result(lower=0.6, marginal=0.6, near=0.6, missing=0.0, point=0.7) -> fe.FeatureResult:
    return fe.FeatureResult(
        feature="x", direction=1, objects=100, fields_with_positive=10,
        auc=fe.Interval(point=point, lower=lower, upper=0.9),
        recall_5=fe.Interval(point=0.2, lower=0.1, upper=0.3),
        recall={}, recall_at_budget={}, enrichment={}, median_q=0.3,
        missing_ranked=int(missing * 1000), ranked=1000, missing_rate=missing,
        missing_by_label={}, fields=[], sensitivity={},
        strata=[
            fe.StratumResult(key="role", value="marginal", objects=40, auc=marginal, recall_5=0.1),
            fe.StratumResult(key="near_star", value="zone+outer", objects=40, auc=near, recall_5=0.1),
        ],
    )


def test_gate_is_the_preregistered_rule() -> None:
    assert fe.gate_check(result()).passed
    assert not fe.gate_check(result(lower=0.55)).passed  # strict >
    assert fe.gate_check(result(marginal=0.5, near=0.5)).passed  # >= 0.5
    assert not fe.gate_check(result(marginal=0.4999)).passed
    assert not fe.gate_check(result(near=0.4999)).passed
    assert fe.gate_check(result(missing=0.05)).passed  # <= 5 %
    assert not fe.gate_check(result(missing=0.051)).passed
    reversed_ = fe.gate_check(result(lower=0.2, point=0.3))
    assert not reversed_.passed and any("reversed" in r for r in reversed_.reasons)


def test_redundancy_rule_is_pairwise_and_keeps_the_higher_auc() -> None:
    names = list(rd.CANDIDATE_FEATURES)[:3]
    a, b, c = names
    rho = {x: {y: (1.0 if x == y else 0.0) for y in names} for x in names}
    rho[a][b] = rho[b][a] = 0.95
    rho[b][c] = rho[c][b] = -0.93
    auc = {a: 0.80, b: 0.70, c: 0.60}
    # literal pairwise: b loses to a, c loses to b (even though b is dropped)
    assert fe.redundancy_drops(names, auc, rho) == {b: a, c: b}
    rho[b][c] = rho[c][b] = 0.90  # not > 0.90
    assert fe.redundancy_drops(names, auc, rho) == {b: a}
    # equal AUC: the later feature in CANDIDATE_FEATURES order is dropped
    assert fe.redundancy_drops([a, b], {a: 0.7, b: 0.7}, rho) == {b: a}


def test_spearman_with_ties_and_missing() -> None:
    assert fe.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert fe.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert fe.average_ranks([5, 1, 5, 2]) == [3.5, 1.0, 3.5, 2.0]
    assert fe.spearman([1, None, 3, 4, 5], [1, 7, 3, 4, 5]) == pytest.approx(1.0)
    assert fe.spearman([1, 1, 1], [1, 2, 3]) is None


# --- committed AS-038 outputs -----------------------------------------------


@pytest.fixture(scope="module")
def evaluation() -> dict:
    path = OUT / fe.RESULTS_FILE
    if not path.exists():
        pytest.skip("AS-038 evaluation not generated yet")
    return json.loads(path.read_text())


def test_committed_table_is_development_only_and_matches_the_evaluation(evaluation, manifest) -> None:
    assert evaluation["table_sha256"] == rd.file_sha256(OUT / fe.TABLE_FILE)
    assert evaluation["manifest_sha256"] == rd.file_sha256(ROOT / fe.MANIFEST_FILE)
    rows = fe.read_table(OUT / fe.TABLE_FILE, manifest)  # guards every field
    assert {r["field_id"] for r in rows} <= {q["field_id"] for q in fe.development_nights(manifest)}
    assert {r["label"] for r in rows} <= {rd.POSITIVE, rd.AUXILIARY, rd.BACKGROUND}
    assert len(rows) == evaluation["ranked_tracklets"]


def test_frozen_list_follows_mechanically_from_the_committed_metrics(evaluation) -> None:
    results = {f["feature"]: fe.FeatureResult.model_validate(f) for f in evaluation["features"]}
    assert list(results) == list(rd.CANDIDATE_FEATURES)
    passing = [n for n, r in results.items() if fe.gate_check(r).passed]
    assert passing == evaluation["passing_gate"]
    drops = fe.redundancy_drops(passing, {n: r.auc.point for n, r in results.items()}, evaluation["spearman_pooled"])
    assert [n for n in passing if n not in drops] == evaluation["frozen_features"]
    frozen = json.loads((OUT / fe.FROZEN_FILE).read_text())
    assert [f["feature"] for f in frozen["features"]] == evaluation["frozen_features"]
    for f in frozen["features"]:
        assert f["direction"] == rd.CANDIDATE_FEATURES[f["feature"]]
        assert "star" not in f["feature"] and "proximity" not in f["feature"]
