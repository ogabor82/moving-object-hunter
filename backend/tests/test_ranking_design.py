import json
from pathlib import Path

import pytest

from app.validation import known_recovery as kr
from app.validation import ranking_design as rd

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "validation/results/as037/as037_manifest.json"


def qn(field_id, population="C", stars=()):
    return rd.quadrant_night(field_id, population, [1, 2, 3], stars)


def pos(field="F1", group="G1", designation="1", night="2020-01-01", q=0.0, rank=1.0, **strata):
    return rd.RankedPositive(
        field_id=field, group=group, designation=designation, night=night, q=q, rank=rank,
        strata=strata,
    )


# --- pre-registered constants ----------------------------------------------


def test_preregistered_constants_are_fixed() -> None:
    assert rd.SALT == "AS-037"
    assert rd.PRIMARY_FRACTION == 0.05
    assert rd.SECONDARY_FRACTIONS == (0.01, 0.02, 0.10, 0.20)
    assert rd.SECONDARY_BUDGETS == (10, 25, 50)
    assert rd.USEFUL_RECALL == 0.50 and rd.USEFUL_LOWER == 0.30
    assert rd.PROTECTION_MARGIN == 0.20
    assert rd.MIN_POSITIVE_OBJECTS == 100 and rd.MIN_POSITIVE_FIELDS == 15
    assert rd.MIN_ZONE_POSITIVES == 10 and rd.MIN_FAINT_POSITIVES == 30
    assert rd.BOOTSTRAP_RESAMPLES == 2000 and rd.CI_LEVEL == 0.95
    assert rd.LINK_SAME_FIELD_DAYS == 3
    assert rd.AUC_GATE_LOWER == 0.55 and rd.CV_FOLDS == 5
    # The near-star zone is the AS-035/036 definition, not re-tuned.
    assert kr.ZONE_REACH == ((6.0, 120.0), (8.0, 60.0), (10.0, 30.0))


def test_proximity_is_context_only_never_a_candidate_feature() -> None:
    for name in rd.CANDIDATE_FEATURES:
        assert "star" not in name and "proximity" not in name
    assert "proximity_group" in rd.CONTEXT_FEATURES
    assert "star_separation_by_class" in rd.CONTEXT_FEATURES
    assert set(rd.CANDIDATE_FEATURES.values()) <= {-1, 1}


# --- population, groups, split ---------------------------------------------


def test_parse_field_id() -> None:
    assert rd.parse_field_id("C30-2020-01-28-1613-c9-q2") == ("2020-01-28", 1613, 9, 2)
    assert rd.parse_field_id("POC-2018-04-11-535-c11-q3") == ("2018-04-11", 535, 11, 3)
    with pytest.raises(ValueError):
        rd.parse_field_id("not-a-field")


def test_link_reasons() -> None:
    a = qn("C1-2020-01-28-617-c2-q2", stars=("TYC 1-1-1",))
    same_night = qn("C2-2020-01-28-1613-c9-q2")
    same_star = qn("C3-2020-05-01-100-c1-q1", stars=("TYC 1-1-1",))
    near_field = qn("C4-2020-01-31-617-c5-q1")
    far_field = qn("C5-2020-02-01-617-c5-q1")
    assert rd.link_reasons(a, same_night) == ["same night"]
    assert rd.link_reasons(a, same_star) == ["same star TYC 1-1-1"]
    assert rd.link_reasons(a, near_field) == ["ZTF field 617 3 d apart"]
    assert rd.link_reasons(a, far_field) == []


def test_groups_are_transitive_and_any_dev_member_makes_the_group_dev() -> None:
    nights = [
        qn("R1-2019-01-25-565-c13-q3", "R"),
        qn("C7-2019-01-25-565-c3-q2", "C", ("TYC 2-2-2",)),
        qn("C8-2019-05-01-700-c1-q1", "C", ("TYC 2-2-2",)),  # linked via the star
        qn("C9-2020-05-01-800-c1-q1", "C"),
    ]
    group_of, links = rd.independence_groups(nights)
    split = rd.assign_splits(nights, group_of)
    assert group_of["C8-2019-05-01-700-c1-q1"] == group_of["R1-2019-01-25-565-c13-q3"]
    assert group_of["C8-2019-05-01-700-c1-q1"] == "G-C7-2019-01-25-565-c3-q2"
    assert split["C7-2019-01-25-565-c3-q2"] == rd.DEVELOPMENT
    assert split["C8-2019-05-01-700-c1-q1"] == rd.DEVELOPMENT
    assert split["C9-2020-05-01-800-c1-q1"] == rd.VALIDATION
    assert len(links) == 2


def test_frozen_manifest_matches_the_rule() -> None:
    manifest = json.loads(MANIFEST.read_text())
    rebuilt = rd.build_manifest(ROOT)
    for key in ("quadrant_nights", "groups", "links", "validation_digest", "inputs",
                "positive_availability", "cross_split_designations", "preregistration"):
        assert manifest[key] == rebuilt[key], key
    assert manifest["split_counts"] == {"development": 56, "validation": 24}
    nights = manifest["quadrant_nights"]
    assert len(nights) == 80
    assert all(q["population"] == "C" for q in nights if q["split"] == rd.VALIDATION)
    # No group straddles the split.
    for g in manifest["groups"]:
        assert {q["split"] for q in nights if q["group"] == g["group"]} == {g["split"]}
    # The C quadrant-nights tied to development by night / field / star.
    moved = {q["field_id"][:3].rstrip("-") for q in nights
             if q["population"] == "C" and q["split"] == rd.DEVELOPMENT}
    assert moved == {"C4", "C7", "C12", "C18", "C19", "C20"}


def test_validation_minimums_are_available() -> None:
    val = json.loads(MANIFEST.read_text())["positive_availability"][rd.VALIDATION]
    assert val["positive_object_nights"] >= rd.MIN_POSITIVE_OBJECTS
    assert val["fields_with_positive"] >= rd.MIN_POSITIVE_FIELDS
    assert val["zone"] >= rd.MIN_ZONE_POSITIVES
    assert val["marginal"] >= rd.MIN_FAINT_POSITIVES


def test_require_split_guards_the_stages() -> None:
    manifest = {"quadrant_nights": [
        {"field_id": "D1", "split": rd.DEVELOPMENT},
        {"field_id": "V1", "split": rd.VALIDATION},
    ]}
    rd.require_split(manifest, "D1", rd.STAGE_FEATURE_EVALUATION)
    rd.require_split(manifest, "D1", rd.STAGE_RANKING_CONSTRUCTION)
    rd.require_split(manifest, "V1", rd.STAGE_VALIDATION)
    for field_id, stage in (("V1", rd.STAGE_FEATURE_EVALUATION),
                            ("V1", rd.STAGE_RANKING_CONSTRUCTION),
                            ("D1", rd.STAGE_VALIDATION),
                            ("X1", rd.STAGE_VALIDATION),
                            ("D1", "tuning")):
        with pytest.raises(rd.SplitError):
            rd.require_split(manifest, field_id, stage)


# --- labels and helpers ----------------------------------------------------


def test_label_tracklet() -> None:
    targets = {"1995 DH": "primary", "2001 X": "marginal"}
    assert rd.label_tracklet("rejected", "known", "1995 DH", targets) == rd.NOT_RANKED
    assert rd.label_tracklet("built", "known", "1995 DH", targets) == rd.POSITIVE
    assert rd.label_tracklet("built", "known", "2001 X", targets) == rd.POSITIVE
    assert rd.label_tracklet("built", "known", "other", targets) == rd.AUXILIARY
    assert rd.label_tracklet("built", "ambiguous", "1995 DH", targets) == rd.AUXILIARY
    assert rd.label_tracklet("built", "unknown", None, targets) == rd.BACKGROUND
    with pytest.raises(ValueError):
        rd.label_tracklet("built", None, None, targets)  # SkyBoT failure


def test_hash_score_is_deterministic_and_feature_free() -> None:
    a = rd.hash_score("C1", "trk-0001")
    assert a == rd.hash_score("C1", "trk-0001")
    assert 0.0 <= a < 1.0
    assert a != rd.hash_score("C1", "trk-0002")


def test_within_field_percentile() -> None:
    assert rd.within_field_percentile([1.0, 2.0, 3.0, None], +1) == [1 / 6, 0.5, 5 / 6, None]
    assert rd.within_field_percentile([1.0, 2.0, 3.0], -1) == [5 / 6, 0.5, 1 / 6]
    assert rd.within_field_percentile([2.0, 2.0], +1) == [0.5, 0.5]


def test_magnitude_chi2() -> None:
    assert rd.magnitude_chi2([20.0, 20.0, 20.0], [0.1, 0.1, 0.1]) == 0.0
    assert rd.magnitude_chi2([20.0, 20.2], [0.1, 0.1]) == pytest.approx(2.0)
    assert rd.magnitude_chi2([20.0, 20.2], [0.1, 0.0]) is None


# --- metrics ---------------------------------------------------------------


def test_background_rank_fraction_and_rank_count_ties_half() -> None:
    background = [5.0, 4.0, 3.0, 3.0]
    assert rd.background_rank_fraction(6.0, background) == 0.0
    assert rd.background_rank_fraction(3.0, background) == (2 + 1) / 4
    assert rd.background_rank_fraction(1.0, background) == 1.0
    assert rd.background_rank_fraction(1.0, []) == 0.0
    assert rd.background_rank(3.0, background) == 4.0
    assert rd.background_rank(6.0, background) == 1.0


def test_rank_field_ignores_other_positives_and_auxiliary() -> None:
    scores = {"p1": 0.9, "p2": 0.8, "p1b": 0.1, "a": 0.95, "b1": 0.85, "b2": 0.2, "r": 1.0}
    labels = {"p1": rd.POSITIVE, "p2": rd.POSITIVE, "p1b": rd.POSITIVE, "a": rd.AUXILIARY,
              "b1": rd.BACKGROUND, "b2": rd.BACKGROUND, "r": rd.NOT_RANKED}
    designations = {"p1": "X", "p1b": "X", "p2": "Y"}
    ranked = rd.rank_field("F", "G", "2020-01-01", scores, labels, designations,
                           {"X": {"role": "primary"}})
    by = {p.designation: p for p in ranked}
    assert set(by) == {"X", "Y"}  # one entry per object, best copy
    assert by["X"].q == 0.0 and by["X"].rank == 1.0
    assert by["Y"].q == 0.5 and by["Y"].rank == 2.0
    assert by["X"].strata == {"role": "primary"} and by["Y"].strata == {}


def test_duplicate_object_nights_share_weight_one() -> None:
    ps = rd.object_weights([
        pos("C29", designation="125093", q=0.5),
        pos("C30", designation="125093", q=0.0),
        pos("C1", designation="7", q=0.0),
        pos("C2", designation="7", night="2020-02-01", q=0.0),
    ])
    assert [p.weight for p in ps] == [0.5, 0.5, 1.0, 1.0]
    assert rd.object_count(ps) == 3.0
    assert rd.recall_at_fraction(ps, 0.05) == pytest.approx(2.5 / 3)


def test_recall_enrichment_budget_auc() -> None:
    ps = rd.object_weights([pos(designation=str(i), q=q, rank=r)
                            for i, (q, r) in enumerate([(0.0, 1), (0.04, 5), (0.3, 30), (1.0, 99)])])
    assert rd.recall_at_fraction(ps, 0.05) == 0.5
    assert rd.enrichment(ps, 0.05) == pytest.approx(10.0)
    assert rd.recall_at_budget(ps, 10) == 0.5
    assert rd.recall_at_budget(ps, 50) == 0.75
    assert rd.within_field_auc(ps) == pytest.approx((1 + 0.96 + 0.7 + 0) / 4)
    assert rd.recall_at_fraction([], 0.05) is None


def test_group_bootstrap_is_deterministic_and_resamples_groups() -> None:
    ps = rd.object_weights([pos(field=f"F{i}", group=f"G{i % 5}", designation=str(i),
                                q=0.0 if i % 2 else 1.0) for i in range(40)])
    stat = lambda s: rd.recall_at_fraction(s, 0.05)  # noqa: E731
    a = rd.group_bootstrap(ps, stat, "t", resamples=300)
    assert a == rd.group_bootstrap(ps, stat, "t", resamples=300)
    assert a[0] <= 0.5 <= a[1]
    # One group only -> no between-group variance.
    single = [pos(group="G", designation=str(i), q=0.0 if i < 3 else 1.0) for i in range(4)]
    assert rd.group_bootstrap(rd.object_weights(single), stat, "t", resamples=50) == (0.75, 0.75)


# --- decision rule ---------------------------------------------------------


def population(n_fields=20, per_field=8, hit=0.8, zone_hit=0.8, marginal_hit=0.8,
               zone_n=12, marginal_n=40):
    ps = []
    i = 0
    for f in range(n_fields):
        for k in range(per_field):
            ps.append(pos(field=f"F{f}", group=f"G{f}", designation=f"d{i}",
                          q=0.0 if (k / per_field) < hit else 1.0,
                          role="primary", proximity_group="control"))
            i += 1
    for j in range(zone_n):
        ps.append(pos(field=f"F{j % n_fields}", group=f"G{j % n_fields}", designation=f"z{j}",
                      q=0.0 if j < zone_hit * zone_n else 1.0,
                      role="primary", proximity_group="zone"))
    for j in range(marginal_n):
        ps.append(pos(field=f"F{j % n_fields}", group=f"G{j % n_fields}", designation=f"m{j}",
                      q=0.0 if j < marginal_hit * marginal_n else 1.0,
                      role="marginal", proximity_group="control"))
    return rd.object_weights(ps)


def test_decide_useful_protected() -> None:
    d = rd.decide(population())
    assert d.verdict == rd.USEFUL_PROTECTED
    assert all(g.evaluable and g.passed for g in d.guards)


def test_decide_flags_near_star_burial() -> None:
    d = rd.decide(population(zone_hit=0.25))
    assert d.verdict == rd.USEFUL_NOT_PROTECTED
    near = d.guards[0]
    assert near.name.startswith("near-star") and near.passed is False


def test_decide_flags_faint_burial() -> None:
    d = rd.decide(population(marginal_hit=0.4))
    assert d.verdict == rd.USEFUL_NOT_PROTECTED
    assert d.guards[1].passed is False


def test_decide_unverified_when_zone_too_small() -> None:
    d = rd.decide(population(zone_n=5))
    assert d.verdict == rd.USEFUL_UNVERIFIED
    assert d.guards[0].evaluable is False


def test_decide_not_useful_and_inconclusive() -> None:
    assert rd.decide(population(hit=0.1, zone_hit=0.1, marginal_hit=0.1)).verdict == rd.NOT_USEFUL
    few = rd.decide(population(n_fields=5, per_field=4, zone_n=0, marginal_n=0))
    assert few.verdict == rd.INCONCLUSIVE
    assert any("positive object-nights" in r for r in few.reasons)
    assert any("fields with a positive" in r for r in few.reasons)
