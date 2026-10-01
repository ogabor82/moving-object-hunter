import math

from app.models.known_object import KnownObjectEphemeris
from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG
from app.validation import known_recovery as kr
from app.validation.bright_stars import TychoStar


def row(pid, minutes, field="565", ccd="13", qid="3", date="2019-03-01", maglimit="20.5"):
    jd = 2458543.5 + minutes / 1440.0
    corners = {
        "ra1": "149.5", "dec1": "9.5", "ra2": "150.5", "dec2": "9.5",
        "ra3": "150.5", "dec3": "10.5", "ra4": "149.5", "dec4": "10.5",
    }
    return {
        "pid": str(pid),
        "obsjd": f"{jd:.6f}",
        "obsdate": f"{date} 05:00:00+00",
        "field": field,
        "ccdid": ccd,
        "qid": qid,
        "filtercode": "zr",
        "filefracday": "20190301204845",
        "imgtypecode": "o",
        "exptime": "30",
        "maglimit": maglimit,
        **corners,
    }


def star(tycho_id="TYC 1-1-1", ra=150.0, dec=10.0, v=5.0):
    return TychoStar(
        tycho_id=tycho_id, ra=ra, dec=dec, vt_mag=v, bt_mag=None, v_mag=v,
        position_source="mean J2000",
    )


def ephemeris(designation="1234", ra=150.0, dec=10.0, v=19.0, east=30.0, north=0.0, err=0.1):
    return KnownObjectEphemeris(
        designation=designation, name=designation, object_class="MB>Inner",
        predicted_ra=ra, predicted_dec=dec, v_magnitude=v,
        position_error_arcsec=err, distance_from_field_center_arcsec=0.0,
        motion_ra_cos_dec_arcsec_per_hour=east, motion_dec_arcsec_per_hour=north,
    )


def test_preregistered_constants_are_fixed() -> None:
    assert kr.MIN_GAP_MIN == 15.0 and kr.MAX_SPAN_MIN == 150.0
    assert kr.TRIGGER_NEAR_ARCSEC == 120.0
    assert kr.DISTANCE_EDGES == (0.0, 30.0, 60.0, 120.0, 240.0)
    assert kr.ZONE_REACH == ((6.0, 120.0), (8.0, 60.0), (10.0, 30.0))
    assert kr.BASELINE_TOLERANCE_FACTOR * EXPERIMENTAL_DEFAULT_CONFIG.stationary_tolerance_arcsec == 3.0
    assert kr.REVISIT == ("288181", "408599")


def test_pick_triple_takes_midpoint_with_minimum_gaps() -> None:
    group = [row(1, 0), row(2, 1), row(3, 30), row(4, 50), row(5, 100), row(6, 200)]

    triple = kr.pick_triple(group)

    # E3 = last within 150 min (100), E2 nearest 50 with >= 15 min gaps.
    assert [r["pid"] for r in triple] == ["1", "4", "5"]


def test_pick_triple_rejects_short_baselines() -> None:
    # S3-like: all exposures within a few minutes.
    assert kr.pick_triple([row(1, 0), row(2, 0.66), row(3, 1.3)]) is None
    # Span ok but no exposure 15 min from both ends.
    assert kr.pick_triple([row(1, 0), row(2, 5), row(3, 25)]) is None
    assert kr.pick_triple([row(1, 0), row(2, 15)]) is None


def test_quadrant_nights_groups_and_orders_and_skips_unusable_rows() -> None:
    rows = [
        row(11, 0, date="2019-03-02"), row(12, 40, date="2019-03-02"), row(13, 80, date="2019-03-02"),
        row(21, 0, qid="1"), row(22, 40, qid="1"), row(23, 80, qid="1", maglimit=""),
        row(31, -1000), row(32, -960), row(33, -920),
    ]

    triples = kr.quadrant_nights(rows)

    assert [[r["pid"] for r in t] for t in triples] == [["31", "32", "33"], ["11", "12", "13"]]


def test_search_order_classes_and_window() -> None:
    stars = [
        star("TYC 1-1-1", v=5.0),
        star("TYC 1-2-1", v=7.0),
        star("TYC 1-3-1", v=8.5),
        star("TYC 1-4-1", v=5.0, dec=-40.0),
        star("TYC 1-5-1", v=5.0, ra=270.0, dec=60.0),  # far from the ecliptic
    ]

    ordered = kr.search_order(stars)

    assert [[s.tycho_id for s in group] for group in ordered] == [["TYC 1-1-1"], ["TYC 1-2-1"]]


def test_baseline_eligibility_uses_every_pair() -> None:
    a, b, c = (150.0, 10.0), (150.0 + 4 / 3600, 10.0), (150.0 + 8 / 3600, 10.0)
    assert kr.baseline_eligible([a, b, c], 1.5)
    assert not kr.baseline_eligible([a, (150.0 + 1 / 3600, 10.0), c], 1.5)


def test_extrapolate_moves_along_rates() -> None:
    ra, dec = kr.extrapolate(ephemeris(east=36.0, north=-18.0), 60.0)
    assert math.isclose((ra - 150.0) * math.cos(math.radians(10.0)) * 3600, 36.0, rel_tol=1e-9)
    assert math.isclose((dec - 10.0) * 3600, -18.0, rel_tol=1e-9)


def test_trigger_requires_target_rule_eligibility_and_proximity() -> None:
    triple = [row(1, 0), row(2, 45), row(3, 90)]
    objects = [
        ephemeris("near", ra=150.0 + 60 / 3600, east=30.0),  # 0.5"/min, ~60" away
        ephemeris("far", ra=150.0 + 400 / 3600, east=30.0),
        ephemeris("faint", v=21.5),
        ephemeris("badorbit", err=3.0),
        ephemeris("fast", east=90.0 * 60),  # 90"/min
        ephemeris("slow", east=1.0),  # 1.5" in 90 min
    ]

    found = kr.trigger_objects(star(), triple, objects, EXPERIMENTAL_DEFAULT_CONFIG)

    assert [t.designation for t in found] == ["near"]
    assert 30.0 < found[0].closest_approach_arcsec < 120.0
    assert len(found[0].positions) == 3


def test_select_sequences_alternates_classes_and_skips_used_nights(monkeypatch) -> None:
    stars = [
        star("TYC 1-1-1", v=5.0),
        star("TYC 1-2-1", v=7.0, ra=150.001),
        star("TYC 1-3-1", v=7.5, ra=150.002),
    ]
    nights = {
        150.0: [row(1, 0), row(2, 45), row(3, 90)],
        150.001: [row(1, 0), row(2, 45), row(3, 90)],  # same night: used
        150.002: [row(7, 0, qid="2"), row(8, 45, qid="2"), row(9, 90, qid="2")],
    }
    monkeypatch.setattr(
        kr,
        "search_order",
        lambda found: [[s for s in found if s.v_mag < 6], [s for s in found if s.v_mag >= 6]],
    )
    monkeypatch.setattr(kr, "QUADRANTS_PER_CLASS", 1)

    selection = kr.select_sequences(
        tycho=lambda params, client: ("url", stars),
        metadata=lambda ra, dec, client: nights[ra],
        cone=lambda s, middle, client: [ephemeris("near", ra=s.ra + 60 / 3600)],
        available=lambda rows, client: True,
        excluded=set(),
    )

    assert [s.field.field_id for s in selection.sequences] == [
        "N1-2019-03-01-565-c13-q3",
        "N2-2019-03-01-565-c13-q2",
    ]
    assert [s.search_star.tycho_id for s in selection.sequences] == ["TYC 1-1-1", "TYC 1-3-1"]
    assert [entry.outcome.split(" ")[0] for entry in selection.log] == ["selected", "no", "selected"]
    assert selection.skybot_queries == 2


def test_r_quadrant_nights_parse_the_as034_population() -> None:
    keys = kr.r_quadrant_nights()
    assert len(keys) == 26
    assert ("565", "13", "3", "2019-01-25") in keys
    assert ("335", "7", "2", "2019-07-01") in keys


# --- evidence part ---------------------------------------------------------

from app.models.known_object import KnownObjectField  # noqa: E402
from app.services.identification_service import (  # noqa: E402
    match_tracklets_to_known_objects,
    mid_exposure_jd_utc,
)
from app.services.pipeline_service import build_tracklets_from_frames  # noqa: E402
from app.validation.models import FrameMetadata, ValidationTarget  # noqa: E402
from app.validation.star_contamination import Star, StarProximity  # noqa: E402
from tests.synthetic_frames import ARCSEC, make_frame  # noqa: E402

RA0, DEC0 = 150.0, 10.0
MINUTES = (0.0, 30.0, 60.0)


def target_positions(rate=0.5, minutes=MINUTES):
    return [(RA0 + rate * m * ARCSEC / math.cos(math.radians(DEC0)), DEC0) for m in minutes]


def run_trace(positions_per_frame, predicted, minutes=MINUTES, stars=()):
    frames = [
        make_frame(100 + i, m, positions)
        for i, (m, positions) in enumerate(zip(minutes, positions_per_frame))
    ]
    frames = [
        f.model_copy(update={"observation": f.observation.model_copy(update={"exposure_seconds": 30.0})})
        for f in frames
    ]
    config = EXPERIMENTAL_DEFAULT_CONFIG
    pipeline = build_tracklets_from_frames(frames, config)
    fields = {
        f.observation.product_id: KnownObjectField(
            epoch_jd_utc=mid_exposure_jd_utc(f.observation),
            field_ra=RA0, field_dec=DEC0, field_radius_degrees=1.0, observer="I41",
            objects=[ephemeris("1234", ra=ra, dec=dec, east=30.0)],
            rejected_rows=[],
        )
        for f, (ra, dec) in zip(frames, predicted)
    }
    identifications = match_tracklets_to_known_objects(
        pipeline.build.tracklets, fields, config.identification()
    ).identifications
    corners = [(149.5, 9.5), (150.5, 9.5), (150.5, 10.5), (149.5, 10.5)]
    metadata = [
        FrameMetadata(product_id=100 + i, center_ra=RA0, center_dec=DEC0, corners=corners,
                      maglimit=20.5, seeing_arcsec=2.0, airmass=1.2)
        for i in range(3)
    ]
    target = ValidationTarget(
        field_id="F", designation="1234", name="1234", object_class="MB", role="primary",
        v_magnitude=19.0, position_error_arcsec=0.1,
        predicted_rate_arcsec_per_min=0.5, predicted_position_angle_deg=90.0,
        predicted_positions=predicted,
    )
    return kr.trace_target(
        "N", "F", target, frames, metadata, pipeline.candidate_frames,
        pipeline.build.tracklets, identifications, config, list(stars), {}, [20.5] * 3,
    )


FIELD_STAR = (RA0 - 100 * ARCSEC, DEC0 + 100 * ARCSEC)


def test_trace_recovered_target() -> None:
    predicted = target_positions()
    trace = run_trace([[p, FIELD_STAR] for p in predicted], predicted)

    assert trace.recovered and trace.first_failure is None and trace.as022_recovered
    assert trace.detected_frames == 3 and trace.candidate_frames == 3
    assert trace.tracklet_status == "tracklet_built" and trace.best_match == "1234"
    assert trace.baseline_eligible and trace.rate_eligible
    assert trace.group == "control"


def test_trace_missing_detection_is_the_first_failure() -> None:
    predicted = target_positions()
    frames = [[predicted[0], FIELD_STAR], [FIELD_STAR], [predicted[2], FIELD_STAR]]

    trace = run_trace(frames, predicted)

    assert trace.first_failure == "detection" and not trace.recovered
    assert [f.detected for f in trace.frames] == [True, False, True]


def test_trace_stationary_match_to_another_source() -> None:
    predicted = target_positions()
    blend = (predicted[0][0] + 1.0 * ARCSEC, DEC0)  # another source in E3 only
    frames = [[predicted[0], FIELD_STAR], [predicted[1], FIELD_STAR], [predicted[2], blend, FIELD_STAR]]

    trace = run_trace(frames, predicted)

    assert trace.first_failure == "stationary"
    assert trace.frames[0].candidate is False
    assert trace.frames[0].stationary_match == "other"


def test_trace_short_baseline_self_match_is_its_own_stratum() -> None:
    minutes = (0.0, 1.0, 60.0)  # S3-like E1-E2 gap
    predicted = target_positions(minutes=minutes)
    trace = run_trace([[p, FIELD_STAR] for p in predicted], predicted, minutes=minutes)

    assert not trace.baseline_eligible
    assert trace.first_failure == "stationary"
    assert trace.frames[0].stationary_match == "self"


def test_trace_uses_star_proximity_of_predicted_positions() -> None:
    predicted = target_positions()
    stars = [Star(tycho_id="T", ra=predicted[1][0], dec=DEC0 + 20 * ARCSEC, v_mag=7.0,
                  mag_class=2, isolated=True, in_footprint=True)]

    trace = run_trace([[p, FIELD_STAR] for p in predicted], predicted, stars=stars)

    assert trace.group == "zone"
    assert math.isclose(trace.proximity.separation_by_class[2], 20.0, abs_tol=0.05)


def proximity(v4=None, v6=None, v8=None, v10=None, v11=None):
    values = [v4, v6, v8, v10, v11]
    present = [v for v in values if v is not None]
    return StarProximity(
        separation_by_class=values,
        nearest_separation_arcsec=min(present) if present else None,
        nearest_v_mag=None,
    )


def test_proximity_groups_follow_the_preregistered_reach() -> None:
    assert kr.proximity_group(proximity(v6=100.0)) == "zone"
    assert kr.proximity_group(proximity(v8=59.0)) == "zone"
    assert kr.proximity_group(proximity(v8=61.0)) == "outer"
    assert kr.proximity_group(proximity(v10=29.0)) == "zone"
    assert kr.proximity_group(proximity(v10=31.0)) == "outer"
    assert kr.proximity_group(proximity(v10=300.0)) == "intermediate"
    assert kr.proximity_group(proximity(v10=480.0, v11=60.0)) == "control"
    assert kr.proximity_group(proximity(v10=600.0, v11=59.0)) == "intermediate"
    assert kr.proximity_group(proximity()) == "control"
    assert kr.class_separations(proximity(v4=50.0, v6=10.0)) == (10.0, None, None, None)


def test_distance_bins() -> None:
    assert [kr.distance_bin(v) for v in (0.0, 29.9, 30.0, 119.0, 239.9, 240.0, None)] == [
        0, 0, 1, 2, 3, None, None
    ]


def test_frame_depth_needs_enough_faint_sources() -> None:
    assert kr.frame_depth([20.0] * 4, [5.0] * 4) is None
    assert math.isclose(kr.frame_depth([19.0] * 5 + [15.0], [10.0] * 5 + [200.0]),
                        19.0 + 2.5 * math.log10(2.0))


def test_edge_distance_inside_square() -> None:
    corners = [(149.5, 9.5), (150.5, 9.5), (150.5, 10.5), (149.5, 10.5)]
    # nearest edge: the RA sides, 0.5 deg x cos(10 deg) away
    assert math.isclose(kr.edge_distance_arcsec(150.0, 10.0, corners), 1800.0 * math.cos(math.radians(10.0)), rel_tol=0.001)
    assert kr.edge_distance_arcsec(150.0, 10.49, corners) < 40.0


def test_statistics() -> None:
    low, high = kr.wilson(5, 10)
    assert math.isclose(low, 0.2366, abs_tol=1e-3) and math.isclose(high, 0.7634, abs_tol=1e-3)
    assert kr.wilson(0, 0) == (None, None)
    # Classic tea-tasting table: two-sided p = 0.4857.
    assert math.isclose(kr.fisher_two_sided(3, 1, 1, 3), 0.4857, abs_tol=1e-4)
    assert kr.fisher_two_sided(0, 10, 10, 0) < 1e-4
    assert math.isclose(kr.mantel_haenszel([(1, 1, 1, 1), (2, 0, 0, 2)]), (0.25 + 1.0) / (0.25 + 0.0))
    assert kr.mantel_haenszel([]) is None


def make_trace(field, designation, group, recovered, role="primary", population="N", v10=None):
    return kr.TargetTrace(
        population=population, field_id=field, designation=designation, object_class="MB",
        role=role, v_magnitude=19.0, rate_arcsec_per_min=0.5,
        min_pair_displacement_arcsec=15.0, rate_eligible=True, baseline_eligible=True,
        edge_distance_arcsec=500.0, proximity=proximity(v10=v10), group=group, frames=[],
        detected_frames=3, candidate_frames=3, tracklet_id=None, tracklet_status=None,
        identification_status=None, best_match=None, partial_tracklets=0,
        recovered=recovered, first_failure=None if recovered else "detection",
        as022_recovered=recovered, as022_loss_stage="recovered",
    )


def test_contrast_claim_rule() -> None:
    zone = [make_trace("A", f"z{i}", "zone", i < 2) for i in range(12)]
    control = [make_trace("A", f"c{i}", "control", i < 18) for i in range(20)]

    result = kr.contrast(zone + control, "N")

    assert (result.zone_n, result.zone_recovered, result.control_n) == (12, 2, 20)
    assert result.fisher_p < 0.05 and result.mh_odds_ratio < 1 and result.claimed

    small = kr.contrast(zone[:5] + control, "N")
    assert not small.claimed and small.verdict.startswith("not demonstrated: 5 zone")

    marginal = [make_trace("A", f"m{i}", "zone", False, role="marginal") for i in range(20)]
    assert kr.contrast(marginal + control, "N").zone_n == 0


def test_pick_strips_is_deterministic_and_adds_revisits() -> None:
    traces = (
        [make_trace("A", f"r{i}", "zone", True, v10=20.0) for i in range(10)]
        + [make_trace("A", f"l{i}", "outer", False, v10=100.0) for i in range(3)]
        + [make_trace("A", f"c{i}", "control", i % 2 == 0) for i in range(6)]
        + [make_trace("S3", "288181", "outer", False, population="R", v10=79.0)]
    )
    picks = kr.pick_strips(traces)
    again = kr.pick_strips(list(reversed(traces)))

    assert [(r, t.designation) for r, t in picks] == [(r, t.designation) for r, t in again]
    reasons = [r for r, _ in picks]
    assert reasons.count("near_recovered") == 8 and reasons.count("near_lost") == 4
    assert reasons.count("control_recovered") == 2 and reasons.count("control_lost") == 2
    assert ("near_lost", "288181") in [(r, t.designation) for r, t in picks]
    assert "revisit" not in reasons  # already sampled, not duplicated
