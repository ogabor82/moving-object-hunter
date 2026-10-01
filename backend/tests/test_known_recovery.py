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
