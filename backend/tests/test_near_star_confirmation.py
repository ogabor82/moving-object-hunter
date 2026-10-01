import math

from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG
from app.validation import known_recovery as kr
from app.validation import near_star_confirmation as nsc
from tests.test_known_recovery import ephemeris, make_trace, proximity, row, star


def test_preregistered_constants_are_fixed() -> None:
    assert nsc.SELECTION_SALT == "AS-036"
    assert nsc.MAX_NIGHTS_PER_STAR == 20 and nsc.MAX_SELECTED_PER_STAR == 3
    assert nsc.TRIGGERS_PER_CLASS == 15
    assert nsc.MAX_STARS_PER_CLASS == 300 and nsc.MAX_QUERIES_PER_CLASS == 3000
    assert nsc.MIN_ZONE_TARGETS == 20 and nsc.MIN_CONTROL_TARGETS == 20
    assert nsc.CONFIRM_ALPHA == 0.05 and nsc.NOT_REPRODUCED_MARGIN == 0.20
    # The scientific zone and the AS-035 definitions are reused, not widened.
    assert nsc.TRIGGER_REACH_ARCSEC == tuple(r for _, r in kr.ZONE_REACH[:2])
    assert kr.ZONE_REACH == ((6.0, 120.0), (8.0, 60.0), (10.0, 30.0))
    assert kr.SEARCH_CLASSES == ((-math.inf, 6.0), (6.0, 8.0))
    assert kr.MIN_GAP_MIN == 15.0 and kr.MAX_SPAN_MIN == 150.0


def test_search_order_uses_the_as036_salt() -> None:
    stars = [star(f"TYC 1-{i}-1", v=5.0 if i % 2 else 7.0) for i in range(1, 30)]
    stars.append(star("TYC 9-9-1", v=5.0, dec=-40.0))

    ordered = nsc.search_order(stars)
    old = kr.search_order(stars)

    assert [len(g) for g in ordered] == [15, 14]
    assert sorted(s.tycho_id for s in ordered[0]) == sorted(s.tycho_id for s in old[0])
    assert [s.tycho_id for s in ordered[0]] != [s.tycho_id for s in old[0]]


def test_zone_trigger_is_primary_and_inside_the_class_reach() -> None:
    triple = [row(1, 0), row(2, 45), row(3, 90)]  # maglimit 20.5 -> PRIMARY V <= 20.0
    objects = [
        ephemeris("p90", ra=150.0 + 90 / 3600, east=30.0),
        ephemeris("p50", ra=150.0 + 50 / 3600, east=30.0),
        ephemeris("marginal", v=20.3, ra=150.0 + 20 / 3600, east=30.0),
        ephemeris("slow", ra=150.0 + 20 / 3600, east=1.0),
    ]

    bright = nsc.zone_triggers(star(v=5.0), 0, triple, objects, EXPERIMENTAL_DEFAULT_CONFIG)
    fainter = nsc.zone_triggers(star(v=7.0), 1, triple, objects, EXPERIMENTAL_DEFAULT_CONFIG)

    # p90 passes ~68-112" from the star (moves 45" either side of E2).
    assert [t.designation for t in bright] == ["p50", "p90"]
    assert [t.designation for t in fainter] == ["p50"]
    assert all(t.closest_approach_arcsec < 60.0 for t in fainter)


def test_excluded_nights_are_the_as035_n_and_r_quadrant_nights() -> None:
    keys = nsc.excluded_nights()
    assert len(keys) == 50
    assert ("468", "12", "1", "2018-11-25") in keys  # N1
    assert ("565", "13", "3", "2019-01-25") in keys  # R


def nights_for(qids, date="2019-03-01"):
    rows = []
    for k, qid in enumerate(qids):
        d = f"2019-03-{k + 1:02d}"
        rows += [row(100 * k + 1, 0, qid=qid, date=d), row(100 * k + 2, 45, qid=qid, date=d),
                 row(100 * k + 3, 90, qid=qid, date=d)]
    return rows


def run_select(monkeypatch, stars, metadata, cone, excluded=frozenset(), **limits):
    monkeypatch.setattr(
        nsc,
        "search_order",
        lambda found: [[s for s in found if s.v_mag < 6], [s for s in found if s.v_mag >= 6]],
    )
    for name, value in limits.items():
        monkeypatch.setattr(nsc, name, value)
    return nsc.select_sequences(
        tycho=lambda params, client: ("url", stars),
        metadata=metadata,
        cone=cone,
        available=lambda rows, client: True,
        excluded=set(excluded),
    )


def test_select_takes_several_nights_per_star_and_skips_as035_nights(monkeypatch) -> None:
    stars = [star("TYC 1-1-1", v=5.0)]
    # Nights 1..5 (dates 03-01..03-05); night of 03-02 belongs to AS-035.
    excluded = {("565", "13", "3", "2019-03-02")}

    selection = run_select(
        monkeypatch, stars,
        metadata=lambda ra, dec, client: nights_for(["3"] * 5),
        cone=lambda s, middle, client: [ephemeris("near", ra=s.ra + 60 / 3600)],
        excluded=excluded,
    )

    dates = [s.field.field_id.split("-", 1)[1][:10] for s in selection.sequences]
    assert dates == ["2019-03-01", "2019-03-03", "2019-03-04"]  # 3 per star, earliest first
    assert [s.field.field_id.split("-")[0] for s in selection.sequences] == ["C1", "C2", "C3"]
    assert selection.skybot_queries == [4, 0]  # 4 non-excluded nights examined
    assert selection.triggers == [3, 0]
    assert selection.log[0].qualifying_nights == 4


def test_select_logs_skybot_errors_and_stops_at_the_trigger_quota(monkeypatch) -> None:
    stars = [star("TYC 1-1-1", v=5.0), star("TYC 1-2-1", v=5.5, ra=150.001),
             star("TYC 1-3-1", v=5.2, ra=150.002)]
    calls = []

    def cone(s, middle, client):
        calls.append(s.tycho_id)
        if s.tycho_id == "TYC 1-1-1":
            raise RuntimeError("SIGBUS")
        return [ephemeris("near", ra=s.ra + 30 / 3600), ephemeris("near2", ra=s.ra - 30 / 3600)]

    selection = run_select(
        monkeypatch, stars,
        metadata=lambda ra, dec, client: nights_for(["3"] if ra == 150.0 else ["1"] if ra == 150.001 else ["2"]),
        cone=cone,
        TRIGGERS_PER_CLASS=2,
    )

    assert selection.log[0].nights[0].outcome.startswith("SkyBoT error")
    assert [s.search_star.tycho_id for s in selection.sequences] == ["TYC 1-2-1"]
    assert selection.triggers == [2, 0]
    assert selection.stars_examined == [2, 0]  # third star never consumed
    assert selection.class_outcome[0].startswith("done")


def test_select_respects_the_cone_budget_and_skips_used_nights(monkeypatch) -> None:
    stars = [star("TYC 1-1-1", v=7.0), star("TYC 1-2-1", v=7.5, ra=150.001),
             star("TYC 1-3-1", v=7.2, ra=150.002)]

    selection = run_select(
        monkeypatch, stars,
        metadata=lambda ra, dec, client: nights_for(["3", "3"]),  # same two nights for every star
        cone=lambda s, middle, client: [ephemeris("near", ra=s.ra + 30 / 3600)],
        MAX_QUERIES_PER_CLASS=4,
    )

    assert len(selection.sequences) == 2  # star 2 finds both nights already selected
    assert [n.outcome for n in selection.log[1].nights] == ["skipped: already selected"] * 2
    assert selection.skybot_queries == [0, 4] and selection.stars_examined == [0, 2]
    assert selection.class_outcome[1].startswith("budget exhausted: 4 cones")


def test_select_does_not_depend_on_concurrency(monkeypatch) -> None:
    stars = [star(f"TYC 1-{i}-1", v=5.0 + 0.1 * i, ra=150.0 + 0.001 * i) for i in range(6)]

    def metadata(ra, dec, client):
        return nights_for(["1", "2", "3"][: 1 + round((ra - 150.0) * 1000) % 3])

    def cone(s, middle, client):
        return [ephemeris("near", ra=s.ra + 30 / 3600)] if int(middle["pid"]) % 200 != 2 else []

    serial = run_select(monkeypatch, stars, metadata, cone, TRIGGERS_PER_CLASS=3)
    parallel = nsc.select_sequences(
        tycho=lambda params, client: ("url", stars), metadata=metadata, cone=cone,
        available=lambda rows, client: True, excluded=set(), star_workers=5, cone_workers=7,
        lookahead=6,
    )
    single = nsc.select_sequences(
        tycho=lambda params, client: ("url", stars), metadata=metadata, cone=cone,
        available=lambda rows, client: True, excluded=set(), star_workers=1, cone_workers=1,
        lookahead=1,
    )

    def ids(s):
        return [q.field.field_id for q in s.sequences]

    assert ids(serial) == ids(parallel) == ids(single)
    assert serial.log == parallel.log == single.log


def test_newcombe_matches_the_published_example() -> None:
    # Newcombe (1998) example: 56/70 vs 48/80 -> 0.0524 .. 0.3339.
    low, high = nsc.newcombe(56, 70, 48, 80)
    assert math.isclose(low, 0.0524, abs_tol=5e-4) and math.isclose(high, 0.3339, abs_tol=5e-4)
    assert nsc.newcombe(0, 0, 1, 2) == (None, None)


def traces(zone_k, zone_n, control_k, control_n, field="A"):
    return [make_trace(field, f"z{i}", "zone", i < zone_k) for i in range(zone_n)] + [
        make_trace(field, f"c{i}", "control", i < control_k) for i in range(control_n)
    ]


def test_decision_rule_classifications() -> None:
    confirmed = nsc.decide(traces(9, 20, 85, 100), "C", deciding=True)
    assert confirmed.classification == "CONFIRMED" and confirmed.deciding
    assert confirmed.fisher_p < 0.05 and confirmed.mh_odds_ratio < 1

    null = nsc.decide(traces(38, 40, 85, 100), "C")
    assert null.classification == "NOT REPRODUCED" and null.newcombe_low > -0.20

    ambiguous = nsc.decide(traces(15, 20, 85, 100), "C")  # 75 % vs 85 %
    assert ambiguous.classification == "INCONCLUSIVE"
    assert "not excluded" in ambiguous.reason

    small = nsc.decide(traces(3, 7, 131, 154), "C")  # AS-035 numbers
    assert small.classification == "INCONCLUSIVE" and small.reason.startswith("minimum sample")

    few_controls = nsc.decide(traces(2, 25, 15, 15), "C")
    assert few_controls.classification == "INCONCLUSIVE"


def test_decision_counts_only_primary_baseline_and_rate_eligible_targets() -> None:
    base = traces(9, 20, 85, 100)
    short = [
        make_trace("A", f"s{i}", "zone", False).model_copy(update={"baseline_eligible": False})
        for i in range(30)
    ]
    fast = [
        make_trace("A", f"f{i}", "zone", False).model_copy(update={"rate_eligible": False})
        for i in range(5)
    ]
    marginal = [make_trace("A", f"m{i}", "zone", False, role="marginal") for i in range(30)]

    result = nsc.decide(base + short + fast + marginal, "C")

    assert (result.zone_n, result.zone_recovered, result.control_n) == (20, 9, 100)


def test_mh_uses_only_quadrants_with_both_groups() -> None:
    mixed = traces(4, 10, 40, 50, field="A") + traces(5, 10, 45, 50, field="B")
    mixed += [make_trace("Z", f"zz{i}", "zone", False) for i in range(5)]  # no control there
    result = nsc.decide(mixed, "C")
    assert result.mh_quadrants == 2 and result.zone_n == 25


def test_leave_one_star_out_and_strips_are_deterministic() -> None:
    selection = nsc.ConfirmationSelection(
        generated_at="2026-10-01T00:00:00Z", preregistration="", tycho_query="",
        eligible_stars=[], excluded_nights=0, stars_examined=[], skybot_queries=[], triggers=[],
        class_outcome=[], log=[],
        sequences=[
            kr.SelectedSequence(
                field=kr.ValidationField(field_id=f, description="", product_ids=[1, 2, 3],
                                         selection_note=""),
                search_class="V<6", search_star=star(s), night_index=0, filters=[],
                minutes_from_first=[], trigger=[],
            )
            for f, s in (("A", "TYC 1-1-1"), ("B", "TYC 1-1-1"), ("C", "TYC 2-2-1"))
        ],
    )
    all_traces = traces(2, 6, 10, 12, "A") + traces(3, 6, 10, 12, "B") + traces(1, 4, 5, 6, "C")

    rows = nsc.leave_one_star_out(all_traces, selection)

    assert [(r.search_star, r.fields, r.zone_n) for r in rows] == [
        ("TYC 1-1-1", ["A", "B"], 4), ("TYC 2-2-1", ["C"], 12)
    ]
    picks = nsc.pick_strips(all_traces)
    assert [(r, t.designation, t.field_id) for r, t in picks] == [
        (r, t.designation, t.field_id) for r, t in nsc.pick_strips(list(reversed(all_traces)))
    ]
    reasons = [r for r, _ in picks]
    assert reasons.count("zone_recovered") == 6 and reasons.count("zone_lost") == 6
    assert reasons.count("control_recovered") == 2 and reasons.count("control_lost") == 2


def test_zone_reason_prefers_the_brightest_qualifying_class() -> None:
    t = make_trace("A", "x", "zone", True).model_copy(
        update={"proximity": proximity(v6=100.0, v10=10.0)}
    )
    assert nsc.zone_reason(t) == (0, 100.0)
    t = t.model_copy(update={"proximity": proximity(v6=200.0, v8=50.0)})
    assert nsc.zone_reason(t) == (1, 50.0)
