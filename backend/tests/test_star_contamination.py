import math

import pytest

from app.validation import star_contamination as sc
from app.validation.star_contamination import build_population, sibling_sequences


def row(pid, expid, qid, jd, ccd=13):
    return {
        "pid": str(pid),
        "expid": str(expid),
        "qid": str(qid),
        "ccdid": str(ccd),
        "obsjd": str(jd),
        "obsdate": "2019-01-25 05:00:00+00",
        "field": "565",
        "filtercode": "zr",
        "filefracday": "20190125204845",
        "exptime": "30",
    }


def test_preregistered_bins_are_monotonic_and_fixed() -> None:
    assert list(sc.MAG_EDGES[1:]) == [4.0, 6.0, 8.0, 10.0, 11.0]
    assert math.isinf(sc.MAG_EDGES[0])
    assert sc.ANNULUS_EDGES == (0.0, 15.0, 30.0, 60.0, 120.0, 240.0, 480.0, 900.0)
    assert sc.BACKGROUND_ANNULUS == 6
    assert all(a < b for a, b in zip(sc.ANNULUS_EDGES, sc.ANNULUS_EDGES[1:]))


def test_sibling_sequences_group_by_quadrant_in_time_order() -> None:
    rows = [
        row(13, 2, 1, 2.0),
        row(11, 1, 1, 1.0),
        row(12, 1, 2, 1.0),
        row(14, 3, 1, 3.0),
    ]

    groups = sibling_sequences(rows)

    assert list(groups) == [1, 2]
    assert [r["pid"] for r in groups[1]] == ["11", "13", "14"]


def test_build_population_adds_complete_siblings_only(monkeypatch) -> None:
    parents = {
        "B-2019-01-25-565-c13-q3": [754204845015, 754226595015, 754256675015],
    }
    monkeypatch.setattr(sc, "SIBLING_PARENTS", tuple(parents))

    def metadata(where, client):
        if where.startswith("pid IN"):
            return [
                row(p, 100 + i, 3, i)
                for i, p in enumerate(parents["B-2019-01-25-565-c13-q3"])
            ]
        assert "ccdid = 13" in where and "expid IN (100,101,102)" in where
        rows = []
        for qid in (1, 2, 3, 4):
            for i in range(3 if qid != 2 else 2):  # q2 misses one exposure
                rows.append(row(1000 * qid + i, 100 + i, qid, i))
        return rows

    def available(sequence, client):
        return int(sequence[0]["qid"]) != 4  # q4 products missing

    first = build_population(metadata=metadata, available=available)
    again = build_population(metadata=metadata, available=available)

    siblings = [f for f in first.fields if f.origin.startswith("sibling")]
    assert [f.field.field_id for f in siblings] == ["B-2019-01-25-565-c13-q1"]
    assert siblings[0].field.product_ids == [1000, 1001, 1002]
    assert [f.field.field_id for f in first.fields] == [
        f.field.field_id for f in again.fields
    ]
    assert any("q2: 2 exposures, skipped" in line for line in first.log)
    assert any("q4: products missing" in line for line in first.log)
    assert (
        len(
            [f for f in first.fields if f.origin != f"sibling of {next(iter(parents))}"]
        )
        == 8
    )


def test_committed_population() -> None:
    population = sc.Population.model_validate_json(
        (sc.AS022_REPORT.parent / "as034" / "as034_population.json").read_text()
    )

    ids = [f.field.field_id for f in population.fields]
    assert len(ids) == len(set(ids)) == 26
    assert population.preregistration == sc.PREREGISTRATION
    assert all(len(f.field.product_ids) == 3 for f in population.fields)


# --- evidence helpers ---

from types import SimpleNamespace  # noqa: E402

from app.services.astrometry import angular_distance_arcsec  # noqa: E402
from app.validation.star_contamination import (  # noqa: E402
    KnownRecord,
    Star,
    TrackletRow,
    accumulate,
    annulus_areas,
    annulus_index,
    footprint_mask,
    loss_stage,
    magnitude_class,
    min_proximity,
    pick_visual,
    star_proximity,
    summarise,
)


@pytest.mark.parametrize(
    ("v", "expected"),
    [
        (None, None),
        (-1.0, 0),
        (3.99, 0),
        (4.0, 1),
        (6.5, 2),
        (9.99, 3),
        (10.0, 4),
        (11.0, 4),
        (11.01, None),
    ],
)
def test_magnitude_class(v, expected) -> None:
    assert magnitude_class(v) == expected


@pytest.mark.parametrize(
    ("separation", "expected"),
    [
        (0.0, 0),
        (14.99, 0),
        (15.0, 1),
        (479.9, 5),
        (480.0, 6),
        (899.9, 6),
        (900.0, None),
    ],
)
def test_annulus_index(separation, expected) -> None:
    assert annulus_index(separation) == expected


def make_star(tycho_id, ra, dec, v, isolated=True) -> Star:
    return Star(
        tycho_id=tycho_id,
        ra=ra,
        dec=dec,
        v_mag=v,
        mag_class=magnitude_class(v),
        isolated=isolated,
        in_footprint=True,
    )


def test_star_proximity_per_class_and_nearest() -> None:
    stars = [
        make_star("A", 100.0, 10.0, 5.0),
        make_star("B", 100.01, 10.0, 9.0),
        make_star("C", 100.1, 10.0, 9.5),
    ]

    proximity = star_proximity(100.012, 10.0, stars)

    assert proximity.separation_by_class[1] == pytest.approx(
        angular_distance_arcsec(100.012, 10.0, 100.0, 10.0), abs=0.01
    )
    assert proximity.separation_by_class[3] == pytest.approx(
        angular_distance_arcsec(100.012, 10.0, 100.01, 10.0), abs=0.01
    )
    assert proximity.separation_by_class[0] is None
    assert proximity.nearest_v_mag == 9.0
    empty = star_proximity(0.0, 0.0, [])
    assert empty.nearest_separation_arcsec is None
    assert empty.separation_by_class == [None] * 5


def test_min_proximity_takes_closest_approach_per_class() -> None:
    stars = [make_star("A", 100.0, 10.0, 5.0), make_star("B", 100.2, 10.0, 9.0)]
    positions = [(100.01, 10.0), (100.1, 10.0), (100.195, 10.0)]

    proximity = min_proximity(positions, stars)

    assert proximity.separation_by_class[1] == pytest.approx(
        angular_distance_arcsec(100.01, 10.0, 100.0, 10.0), abs=0.01
    )
    assert proximity.separation_by_class[3] == pytest.approx(
        angular_distance_arcsec(100.195, 10.0, 100.2, 10.0), abs=0.01
    )
    assert proximity.nearest_v_mag == 9.0  # 0.005 deg from B beats 0.01 deg from A


def square(ra0, dec0, half):
    s = math.cos(math.radians(dec0))
    return [
        (ra0 - half / s, dec0 - half),
        (ra0 + half / s, dec0 - half),
        (ra0 + half / s, dec0 + half),
        (ra0 - half / s, dec0 + half),
    ]


def test_footprint_mask_and_corner_order() -> None:
    corners = square(150.0, 20.0, 0.25)
    import numpy

    ras = numpy.array([150.0, 150.0, 151.0])
    decs = numpy.array([20.0, 20.3, 20.0])

    assert list(footprint_mask(ras, decs, corners)) == [True, False, False]
    assert list(footprint_mask(ras, decs, [corners[i] for i in (0, 2, 1, 3)])) == [
        True,
        False,
        False,
    ]


def test_annulus_areas_inside_and_at_the_edge() -> None:
    corners = square(150.0, 20.0, 0.25)  # 30' square
    centred = annulus_areas(make_star("A", 150.0, 20.0, 5.0), corners)
    for index, area in enumerate(centred):
        r1, r2 = sc.ANNULUS_EDGES[index], sc.ANNULUS_EDGES[index + 1]
        expected = math.pi * (r2**2 - r1**2) / 3600
        assert area == pytest.approx(expected, rel=0.01)
    # A star on the right edge sees about half of each small annulus.
    edge_ra = 150.0 + 0.25 / math.cos(math.radians(20.0))
    edge = annulus_areas(make_star("B", edge_ra, 20.0, 5.0), corners)
    assert edge[2] == pytest.approx(centred[2] / 2, rel=0.05)


def trow(tid, ra, dec, group="unknown_built", mask="all_masked"):
    return TrackletRow(
        tracklet_id=tid,
        ra=ra,
        dec=dec,
        group=group,
        mask_state=mask,
        halo_bit_all=mask == "all_masked",
        sharp_max=0.5,
        min_snr=6.0,
        fit_rms=0.25,
    )


def test_accumulate_counts_pairs_by_star_class_and_annulus() -> None:
    corners = square(150.0, 20.0, 0.25)
    star_a = make_star("A", 150.0, 20.0, 5.0)  # class 1, isolated
    star_b = make_star("B", 150.0, 20.05, 9.0, isolated=False)  # class 3, 180" north
    deg = 1 / 3600
    rows = [
        trow("u1", 150.0, 20.0 + 10 * deg),  # 10" from A, 170" from B
        trow("u2", 150.0, 20.0 - 40 * deg, mask="unmasked"),  # 40" from A
        trow("k1", 150.0, 20.05 + 20 * deg, group="known_built", mask="unmasked"),
        trow("r1", 150.0, 20.0 + 100 * deg, group="unknown_rejected"),
    ]
    cells = {}

    accumulate(cells, [star_a, star_b], rows, corners)

    a0 = cells[(1, True, 0)]
    assert (
        a0.unknown_built,
        a0.unknown_by_mask["all_masked"],
        a0.unknown_halo_bit,
    ) == (1, 1, 1)
    assert cells[(1, True, 2)].unknown_built == 1  # u2 at 40"
    assert cells[(1, True, 3)].unknown_rejected == 1  # r1 at 100"
    assert cells[(1, True, 0)].stars == 1
    assert (3, True, 0) not in cells  # B is not isolated
    assert cells[(3, False, 1)].known_built == 1  # k1 20" from B
    assert cells[(3, False, 4)].unknown_built == 2  # u1 170", u2 220" from B
    assert cells[(1, False, 0)].unknown_built == 1  # all-stars scope too


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        (
            dict(
                recovered=True, detected_frames=3, candidate_frames=3, tracklet_id="t"
            ),
            "recovered",
        ),
        (
            dict(
                recovered=False, detected_frames=2, candidate_frames=2, tracklet_id=None
            ),
            "not_detected",
        ),
        (
            dict(
                recovered=False, detected_frames=3, candidate_frames=1, tracklet_id=None
            ),
            "not_candidate",
        ),
        (
            dict(
                recovered=False, detected_frames=3, candidate_frames=3, tracklet_id=None
            ),
            "not_linked",
        ),
        (
            dict(
                recovered=False, detected_frames=3, candidate_frames=3, tracklet_id="t"
            ),
            "not_identified",
        ),
    ],
)
def test_loss_stage(outcome, expected) -> None:
    assert loss_stage(SimpleNamespace(**outcome)) == expected


def known(designation, separations) -> KnownRecord:
    return KnownRecord(
        field_id="F",
        designation=designation,
        role="primary",
        v_magnitude=18.0,
        predicted_positions=[(0.0, 0.0)] * 3,
        proximity=sc.StarProximity(
            separation_by_class=separations,
            nearest_separation_arcsec=None,
            nearest_v_mag=None,
        ),
        detected_frames=3,
        candidate_frames=3,
        recovered=True,
        identification_status="known",
        tracklet_status="tracklet_built",
        loss_stage="recovered",
    )


def test_pick_visual_rule_is_deterministic() -> None:
    knowns = [
        known(f"K{i}", [None, None, 100.0 if i % 2 else 500.0, None, 50.0])
        for i in range(30)
    ]
    unknown = [
        (
            "F",
            f"t{i}",
            sc.StarProximity(
                separation_by_class=[
                    None,
                    None,
                    30.0 if i < 10 else 999.0,
                    40.0 if i < 5 else None,
                    None,
                ],
                nearest_separation_arcsec=30.0 if i < 10 else 300.0,
                nearest_v_mag=7.0,
            ),
        )
        for i in range(20)
    ]

    first = pick_visual(knowns, unknown)
    second = pick_visual(knowns[::-1], unknown[::-1])

    assert [k.designation for k in first[0]] == [k.designation for k in second[0]]
    assert [p[2] for p in first[1]] == [p[2] for p in second[1]]
    # Only K with odd index have a class-2 star within 120"; class 4 (V>10) does not count.
    assert all(int(k.designation[1:]) % 2 for k in first[0])
    assert len(first[0]) == sc.VISUAL_KNOWN_MAX
    groups = [p[0] for p in first[1]]
    assert groups.count("unknown_near_6<=V<8") == 3
    assert groups.count("unknown_near_8<=V<10") == 3
    assert groups.count("unknown_near_10<=V<=11") == 0
    assert groups.count("unknown_background") == 4


def test_summarise() -> None:
    assert summarise([]).count == 0
    s = summarise([1.0, 2.0, 3.0, 4.0, 5.0])
    assert (s.count, s.median, s.p25, s.p75) == (5, 3.0, 2.0, 4.0)


# --- committed evidence ---

import json  # noqa: E402

from app.validation.masked import VisualReview  # noqa: E402

AS034 = sc.AS022_REPORT.parent / "as034"


def committed() -> sc.Evidence:
    return sc.Evidence.model_validate_json((AS034 / "as034_evidence.json").read_text())


def test_committed_evidence_covers_the_population_and_is_reviewed() -> None:
    evidence = committed()
    population = sc.Population.model_validate_json(
        (AS034 / "as034_population.json").read_text()
    )
    reviews = [
        VisualReview.model_validate(r)
        for r in json.loads((AS034 / "visual_review.json").read_text())
    ]

    assert [f.field_id for f in evidence.fields] == [
        f.field.field_id for f in population.fields
    ]
    assert evidence.preregistration == sc.PREREGISTRATION
    reviewed = {(r.field_id, r.tracklet_id) for r in reviews}
    for strip in evidence.strips:
        assert (AS034 / strip.image).is_file()
        assert (strip.field_id, strip.item_id) in reviewed
    assert len(reviewed) == len(evidence.strips)


def test_committed_pooled_cells_are_sums_of_field_cells() -> None:
    cells = committed().cells
    for key, pooled in cells.items():
        if not key.startswith("ALL|"):
            continue
        suffix = key[len("ALL") :]
        parts = [
            c
            for k, c in cells.items()
            if not k.startswith("ALL|")
            and k.endswith(suffix)
            and k.split("|", 1)[1] == suffix[1:]
        ]
        assert pooled.stars == sum(p.stars for p in parts)
        assert pooled.unknown_built == sum(p.unknown_built for p in parts)
        # Each cell's area is rounded to 4 decimals independently.
        assert pooled.area_arcmin2 == pytest.approx(
            sum(p.area_arcmin2 for p in parts), abs=5e-5 * (len(parts) + 1)
        )


def test_committed_known_records_follow_the_target_rule() -> None:
    evidence = committed()
    assert evidence.known
    assert {k.role for k in evidence.known} <= {"primary", "marginal"}
    assert all(len(k.predicted_positions) == 3 for k in evidence.known)
    assert {k.loss_stage for k in evidence.known} <= {
        "recovered",
        "not_detected",
        "not_candidate",
        "not_linked",
        "not_identified",
    }


def test_committed_visual_sample_matches_the_rule() -> None:
    evidence = committed()
    known_strips = [s for s in evidence.strips if s.group == "known_near"]
    expected, _ = pick_visual(evidence.known, [])
    assert [s.item_id for s in known_strips] == [k.designation for k in expected]
