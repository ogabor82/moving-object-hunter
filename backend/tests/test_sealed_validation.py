import json
from collections import defaultdict
from pathlib import Path

import pytest

from app.validation import feature_evaluation as fe
from app.validation import ranker_construction as rc
from app.validation import ranking_design as rd
from app.validation import sealed_validation as sv

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def manifest() -> dict:
    return fe.load_manifest(ROOT)


@pytest.fixture(scope="module")
def frozen() -> dict:
    return json.loads((ROOT / sv.FROZEN_RANKER_FILE).read_text())


# --- V1 frozen inputs -------------------------------------------------------------


def test_committed_frozen_inputs_verify() -> None:
    check = sv.verify_frozen_inputs(ROOT)
    assert check.validation_fields == 24
    assert check.validation_groups == 22
    assert check.validation_digest == sv.VALIDATION_DIGEST
    assert check.ranker["ranker"] == "M1"
    assert check.comparator["ranker"] == "B1:sharp_abs_max"


def test_frozen_hashes_are_the_ones_the_frozen_ranker_records(frozen) -> None:
    assert sv.FROZEN_SHA256[fe.MANIFEST_FILE] == frozen["manifest_sha256"]
    assert sv.FROZEN_SHA256[f"{rc.AS038_DIR}/{fe.TABLE_FILE}"] == frozen["table_sha256"]
    assert sv.FROZEN_SHA256[rc.FROZEN_FEATURES_FILE] == frozen["frozen_features_sha256"]


@pytest.mark.parametrize("path", list(sv.FROZEN_SHA256))
def test_any_changed_frozen_file_stops_verification(monkeypatch, path) -> None:
    monkeypatch.setitem(sv.FROZEN_SHA256, path, "0" * 64)
    with pytest.raises(sv.FrozenInputError):
        sv.verify_frozen_inputs(ROOT)


def test_changed_representation_or_split_stops_verification(monkeypatch) -> None:
    monkeypatch.setattr(rc, "MISSING_PERCENTILE", 0.5)
    with pytest.raises(sv.FrozenInputError):
        sv.verify_frozen_inputs(ROOT)
    monkeypatch.undo()
    monkeypatch.setattr(sv, "VALIDATION_DIGEST", "0" * 64)
    with pytest.raises(sv.FrozenInputError):
        sv.verify_frozen_inputs(ROOT)


def test_expected_specs_are_m1_and_sharp_comparator(frozen) -> None:
    keys = ("ranker", "inputs", "weights", "intercept", "fitted")
    assert {k: frozen["ranker"][k] for k in keys} == sv._expected_m1()
    assert {k: frozen["comparator"][k] for k in keys} == sv._expected_comparator()
    assert set(frozen["ranker"]["weights"].values()) == {0.125}


# --- V2 split guard -------------------------------------------------------------------


def test_validation_nights_are_the_sealed_24(manifest) -> None:
    nights = sv.validation_nights(manifest)
    assert len(nights) == 24
    assert rd.split_digest([q["field_id"] for q in nights]) == sv.VALIDATION_DIGEST
    assert {q["population"] for q in nights} == {"C"}


def test_validation_stage_refuses_development(manifest) -> None:
    development = next(q["field_id"] for q in manifest["quadrant_nights"] if q["split"] == rd.DEVELOPMENT)
    with pytest.raises(rd.SplitError):
        rd.require_split(manifest, development, sv.STAGE)
    with pytest.raises(rd.SplitError):
        fe.replay_field(ROOT, manifest, development, [], stage=sv.STAGE)


def test_validation_traces_hold_only_validation_rows(manifest) -> None:
    traces = sv.load_validation_traces(ROOT, manifest)
    allowed = {q["field_id"] for q in sv.validation_nights(manifest)}
    assert set(traces) <= allowed
    rows = [t for ts in traces.values() for t in ts]
    eligible = [t for t in rows if t["rate_eligible"] and t["baseline_eligible"] and t["recovered"]]
    assert len(eligible) == manifest["positive_availability"]["validation"]["positive_tracklet_targets"]


def test_read_table_refuses_a_development_row(tmp_path, manifest) -> None:
    development = next(q["field_id"] for q in manifest["quadrant_nights"] if q["split"] == rd.DEVELOPMENT)
    row = {k: "" for k in sv.TABLE_COLUMNS} | {"field_id": development, "tracklet_id": "1", "label": rd.BACKGROUND}
    sv.write_table(tmp_path / "t.csv.gz", [row])
    with pytest.raises(rd.SplitError):
        sv.read_table(tmp_path / "t.csv.gz", manifest)


def test_ranker_inputs_hold_no_identity_context_or_position_column(frozen) -> None:
    inputs = {i["feature"] for spec in (frozen["ranker"], frozen["comparator"]) for i in spec["inputs"]}
    assert inputs <= set(rc.FROZEN_FEATURES)
    for column in (*fe.IDENTITY_COLUMNS, *fe.CONTEXT_COLUMNS, "det_positions", "label"):
        assert column not in inputs


# --- V3 scores ------------------------------------------------------------------------


def _rows(values, labels=None):
    labels = labels or [rd.BACKGROUND] * len(values)
    rows = []
    for i, (v, label) in enumerate(zip(values, labels)):
        row = {name: v for name in rc.FROZEN_FEATURES}
        row.update(tracklet_id=f"t{i}", label=label, group="G", night="n", eval_designation=None)
        rows.append(row)
    return rows


def test_frozen_scores_equal_the_as039_representation(frozen) -> None:
    features = [(n, rd.CANDIDATE_FEATURES[n]) for n in rc.FROZEN_FEATURES]
    rows = _rows([1.0, 2.0, None, 3.0, 2.0])
    x = rc.percentile_matrix({"f": rows}, features)["f"]
    m1 = sv.frozen_scores(rows, frozen["ranker"])
    assert m1 == pytest.approx(list(x.mean(axis=1)))
    sharp = sv.frozen_scores(rows, frozen["comparator"])
    assert sharp == pytest.approx(list(x[:, rc.FROZEN_FEATURES.index("sharp_abs_max")]))
    assert sharp[2] == 0.0  # missing -> percentile 0


def test_frozen_scorer_reproduces_as039_m1_and_comparator_on_development(frozen) -> None:
    """M1 and B1 have no fitted parameter, so the AS-039 CV value is the
    fixed score: the new scorer must give the committed numbers exactly."""
    _, rows, fields = rc.load_development(ROOT)
    by_field = defaultdict(list)
    for r in rows:
        by_field[r["field_id"]].append(r)
    strata = fe.positive_strata(rows, fields)
    for name, spec in (("M1", frozen["ranker"]), ("B1:sharp_abs_max", frozen["comparator"])):
        scores = {f: sv.frozen_scores(rs, spec) for f, rs in by_field.items()}
        positives = rc.rank_positives(by_field, scores, strata)
        assert rd.recall_at_fraction(positives, rd.PRIMARY_FRACTION) == frozen["development_cv"][name]["recall_5"]["point"]
        assert rd.within_field_auc(positives) == pytest.approx(frozen["development_cv"][name]["auc"]["point"], abs=1e-12)


# --- V4, V9, V12 helpers -----------------------------------------------------------------


def test_star_class_is_the_nearest_bright_star_class() -> None:
    assert sv.star_class({"separation_by_class": [None, 50.0, 30.0, 10.0, 5.0]}) == "8-10"
    assert sv.star_class({"separation_by_class": [20.0, None, 30.0, None, 5.0]}) == "V<6"
    assert sv.star_class({"separation_by_class": [None, None, None, None, 5.0]}) == "none"


def _positive(field_id, designation, q, night="n", strata=None):
    return rd.RankedPositive(field_id=field_id, group="G", designation=designation, night=night, q=q, rank=1,
                             strata=strata or {})


def test_end_to_end_counts_unrecovered_targets_and_splits_copies() -> None:
    fields = [
        {"field_id": "A", "night": "n", "targets": [
            {"designation": "x", "group": "zone", "role": "primary"},
            {"designation": "y", "group": "control", "role": "marginal"},
        ]},
        {"field_id": "B", "night": "n", "targets": [{"designation": "x", "group": "zone", "role": "primary"}]},
    ]
    positives = [_positive("A", "x", 0.01), _positive("B", "x", 0.2)]
    out = sv.end_to_end(positives, fields)
    assert out["all"]["eligible_object_nights"] == pytest.approx(2.0)
    assert out["zone"]["end_to_end_recall_5"] == pytest.approx(0.5)
    assert out["control"]["end_to_end_recall_5"] == 0.0


def test_strip_picks_follow_sha256_order_and_caps() -> None:
    missed = [{"field_id": "F", "designation": str(i), "tracklet_id": str(i), "q": 0.5} for i in range(20)]
    shortlist = [{"field_id": "F", "tracklet_id": str(i), "q": 0.01} for i in range(30)]
    picks = sv.pick_strips(missed, shortlist)
    assert sum(p["reason"] == "missed_positive" for p in picks) == sv.STRIP_MISSED
    assert sum(p["reason"] == "shortlist_background" for p in picks) == sv.STRIP_BACKGROUND
    keys = [sv.strip_key("F", p["designation"]) for p in picks if p["reason"] == "missed_positive"]
    assert keys == sorted(keys)
    assert sv.pick_strips(list(reversed(missed)), list(reversed(shortlist))) == picks


def test_shortlist_background_is_the_top_five_percent_of_background() -> None:
    rows = _rows([0.0] * 40, [rd.BACKGROUND] * 39 + [rd.POSITIVE])
    for r in rows:
        r["ctx_proximity_group"] = "control"
    scores = {"F": [float(i) for i in range(40)]}
    out = sv.shortlist_background({"F": rows}, scores)
    assert [b["tracklet_id"] for b in out] == ["t37", "t38"]


# --- full evaluate path on a synthetic table (no real validation outcome) ---------------


def test_evaluate_runs_end_to_end_on_a_synthetic_validation_table(tmp_path, manifest) -> None:
    import random

    rng = random.Random(0)
    traces = sv.load_validation_traces(ROOT, manifest)
    rows, fields = [], []
    for night in sv.validation_nights(manifest):
        fid = night["field_id"]
        targets = [t for t in traces.get(fid, []) if t["rate_eligible"] and t["baseline_eligible"]]
        fields.append({
            "field_id": fid, "population": "C", "group": night["group"], "night": night["night"],
            "filters": ["zr", "zr", "zr"], "sources_per_frame": [10000, 10000, 10000],
            "targets": [{
                "designation": t["designation"], "role": t["role"], "group": t["group"],
                "rate_arcsec_per_min": t["rate_arcsec_per_min"],
                "min_global_margin_mag": min(f["global_margin_mag"] for f in t["frames"]),
                "trace_recovered": t["recovered"], "trace_tracklet_id": t["tracklet_id"],
            } for t in targets],
        })
        labelled = [(rd.BACKGROUND, None, None, None)] * 40 + [
            (rd.POSITIVE, t["designation"], t["role"], t["group"]) for t in targets if t["recovered"]
        ]
        for i, (label, designation, role, group) in enumerate(labelled):
            row = {k: "" for k in sv.TABLE_COLUMNS}
            row.update(field_id=fid, population="C", group=night["group"], night=night["night"],
                       tracklet_id=str(i), label=label, eval_designation=designation or "",
                       eval_role=role or "", eval_target_group=group or "",
                       shares_detection_with_positive="0", ctx_proximity_group="control",
                       det_positions="1 10.0 10.0;2 10.001 10.0;3 10.002 10.0")
            for name in rc.FROZEN_FEATURES:
                row[name] = round(rng.random(), 4)
            row["masked_detection_count"] = rng.choice([0, 0, 1, 3])
            rows.append(row)
    sv.write_table(tmp_path / sv.TABLE_FILE, rows)
    (tmp_path / sv.FIELDS_FILE).write_text(json.dumps({"fields": fields}))
    v = sv.evaluate(ROOT, tmp_path, resamples=20)
    assert v.validation_fields == 24
    assert v.positive_objects == pytest.approx(269)
    assert v.verdict == v.decision.verdict
    assert v.verdict in {rd.USEFUL_PROTECTED, rd.USEFUL_NOT_PROTECTED, rd.USEFUL_UNVERIFIED,
                         rd.NOT_USEFUL, rd.INCONCLUSIVE}
    assert [r.ranker for r in v.rankers] == ["M1", "B1:sharp_abs_max", "B0"]
    zone = next(g for g in v.decision.guards if g.name == "near-star zone vs control")
    assert zone.evaluable and zone.protected_n >= rd.MIN_ZONE_POSITIVES
    faint = next(g for g in v.decision.guards if g.name.startswith("faint"))
    assert faint.evaluable and faint.protected_n >= rd.MIN_FAINT_POSITIVES
    assert len(v.strips) <= sv.STRIP_MISSED + sv.STRIP_BACKGROUND
    text = sv.render_markdown(v, [])
    assert "Confirmatory verdict" in text and v.verdict in text
