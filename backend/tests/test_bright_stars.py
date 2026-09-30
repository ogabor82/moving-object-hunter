import json
import math
from datetime import datetime, timezone

import pytest

from app.models.identification import IdentificationStatus
from app.models.tracklet import TrackletStatus
from app.services.astrometry import angular_distance_arcsec
from app.validation import bright_stars
from app.validation.bright_stars import (
    BIN_EDGES,
    CONTROL_BIN,
    BrightStarReport,
    FieldRadial,
    FieldSelection,
    SampledStrip,
    TrackletProximity,
    TychoStar,
    bin_areas,
    bin_index,
    bright,
    compact,
    johnson_v,
    mask_state,
    near_to_control_ratio,
    nearest_star,
    parse_tycho_tsv,
    pick_sequence,
    radial_bins,
    select_fields,
    selection_order,
    visual_sample,
)
from app.validation.masked import VisualReview
from app.validation.presets import AS022_REPORT


TSV = """#
#   VizieR Astronomical Server
TYC1\tTYC2\tTYC3\tRAmdeg\tDEmdeg\tRA(ICRS)\tDE(ICRS)\tBTmag\tVTmag
 \t \t \tdeg\tdeg\tdeg\tdeg\tmag\tmag
----\t-----\t-\t------------\t------------\t------------\t------------\t------\t------
   2\t 1558\t1\t  3.44822769\t  1.38358368\t  3.44828611\t  1.38361944\t 8.430\t 6.917
   6\t 1362\t1\t\t\t  6.56869417\t  3.82575611\t\t 6.200
   7\t    1\t1\t 10.0\t 5.0\t 10.0\t 5.0\t 7.000\t
"""


def test_parse_tycho_positions_and_magnitudes() -> None:
    stars = parse_tycho_tsv(TSV)

    assert [s.tycho_id for s in stars] == ["TYC 2-1558-1", "TYC 6-1362-1", "TYC 7-1-1"]
    first, second, third = stars
    assert (first.ra, first.position_source) == (3.44822769, "mean J2000")
    assert first.v_mag == pytest.approx(6.917 - 0.090 * (8.430 - 6.917))
    # No mean position: observed position; no BT: V = VT.
    assert (second.ra, second.position_source) == (6.56869417, "observed ~J1991.25")
    assert second.v_mag == 6.2
    # No VT: no magnitude, never bright.
    assert third.v_mag is None
    assert bright(stars) == [second]


def test_johnson_v_missing_values() -> None:
    assert johnson_v(None, 7.0) is None
    assert johnson_v(6.0, None) == 6.0
    assert johnson_v(6.0, 7.0) == pytest.approx(5.91)


def star(tycho_id: str, ra: float, dec: float, v: float | None = 5.0) -> TychoStar:
    return TychoStar(
        tycho_id=tycho_id,
        ra=ra,
        dec=dec,
        vt_mag=v,
        bt_mag=None,
        v_mag=v,
        position_source="mean J2000",
    )


def test_selection_order_filters_and_is_input_order_independent() -> None:
    stars = [
        star("TYC 1-1-1", 0.0, 0.0),  # ecliptic, eligible
        star("TYC 2-2-1", 180.0, 1.0),  # ecliptic, eligible
        star("TYC 3-3-1", 90.0, 1.0, v=7.0),  # too faint
        star("TYC 4-4-1", 0.0, 60.0),  # far from the ecliptic
        star("TYC 5-5-1", 270.0, -30.0),  # below Dec -25
        star("TYC 6-6-1", 45.0, 16.0, v=None),  # no magnitude
    ]

    ordered = [s.tycho_id for s in selection_order(stars)]

    assert sorted(ordered) == ["TYC 1-1-1", "TYC 2-2-1"]
    assert ordered == [s.tycho_id for s in selection_order(list(reversed(stars)))]


def row(pid, jd, date, field="500", ccd="1", qid="1", filt="zr"):
    return {
        "pid": str(pid),
        "obsjd": str(jd),
        "obsdate": f"{date} 05:00:00+00",
        "field": field,
        "ccdid": ccd,
        "qid": qid,
        "filtercode": filt,
    }


def test_pick_sequence_takes_earliest_qualifying_group_first_middle_last() -> None:
    rows = [
        row(1, 10.1, "2018-05-01"),
        row(2, 10.2, "2018-05-01"),  # only 2
        row(9, 20.4, "2018-06-01"),
        row(7, 20.1, "2018-06-01"),
        row(8, 20.2, "2018-06-01"),
        row(6, 20.3, "2018-06-01"),
        row(5, 30.1, "2018-07-01"),
        row(4, 30.2, "2018-07-01"),
        row(3, 30.3, "2018-07-01"),
        row(10, 15.1, "2018-05-20", qid="2"),
        row(11, 15.2, "2018-05-20", qid="3"),
    ]

    picked = pick_sequence(rows)

    # 4 exposures on 06-01: first, index (4-1)//2 = 1, last.
    assert [r["pid"] for r in picked] == ["7", "8", "9"]


def test_pick_sequence_without_group() -> None:
    assert pick_sequence([row(1, 1.0, "2018-05-01"), row(2, 1.1, "2018-05-01")]) is None


def test_select_fields_logs_skips_and_stops_at_quota(monkeypatch) -> None:
    stars = [star(f"TYC {i}-1-1", 10.0 * i, 0.0) for i in range(1, 8)]
    monkeypatch.setattr(bright_stars, "SELECTION_FIELDS", 2)
    monkeypatch.setattr(bright_stars, "SELECTION_MAX_ECLIPTIC_LATITUDE", 90.0)

    def metadata(ra, dec, start, end, client):
        if ra == 10.0 * 2:
            return []  # no coverage for this star
        base = int(ra * 1000)
        return [row(base + k, 100 + k / 10, "2019-01-01") for k in range(3)]

    def available(rows, client):
        return int(rows[0]["pid"]) != 30000  # star 3's products are missing

    first = select_fields(
        metadata=metadata,
        tycho=lambda params, client: ("url", stars),
        available=available,
    )
    again = select_fields(
        metadata=metadata,
        tycho=lambda params, client: ("url", list(reversed(stars))),
        available=available,
    )

    assert len(first.fields) == 2
    assert [f.field.product_ids for f in first.fields] == [
        f.field.product_ids for f in again.fields
    ]
    assert all(len(f.field.product_ids) == 3 for f in first.fields)
    outcomes = [entry.outcome for entry in first.log]
    assert sum(o.startswith("selected") for o in outcomes) == 2
    assert all(
        o.startswith(("selected", "no quadrant-night", "products missing"))
        for o in outcomes
    )
    assert first.rule == bright_stars.SELECTION_RULE


# --- radial geometry ---


@pytest.mark.parametrize(
    ("separation", "expected"),
    [
        (None, None),
        (0.0, 0),
        (119.999, 0),
        (120.0, 1),
        (599.9, 4),
        (600.0, 5),
        (899.9, 5),
        (900.0, CONTROL_BIN),
        (1e6, CONTROL_BIN),
    ],
)
def test_bin_index(separation, expected) -> None:
    assert bin_index(separation) == expected


def test_bin_index_rejects_negative() -> None:
    with pytest.raises(ValueError):
        bin_index(-1.0)


def test_nearest_star_uses_great_circle_distance() -> None:
    stars = [star("TYC A", 10.0, 60.0), star("TYC B", 10.5, 60.0)]

    separation, star_id = nearest_star(10.4, 60.0, stars)

    # 0.1 deg of RA at Dec 60 is ~180", not 360".
    assert star_id == "TYC B"
    assert separation == pytest.approx(angular_distance_arcsec(10.4, 60.0, 10.5, 60.0))
    assert separation == pytest.approx(180.0, rel=0.01)
    assert nearest_star(0.0, 0.0, []) == (None, None)


def square(ra0: float, dec0: float, half_deg: float):
    scale = math.cos(math.radians(dec0))
    return [
        (ra0 - half_deg / scale, dec0 - half_deg),
        (ra0 + half_deg / scale, dec0 - half_deg),
        (ra0 + half_deg / scale, dec0 + half_deg),
        (ra0 - half_deg / scale, dec0 + half_deg),
    ]


def test_bin_areas_of_a_centred_star_are_annuli() -> None:
    corners = square(150.0, 20.0, 0.25)  # 30' x 30'
    total, areas = bin_areas(corners, [star("TYC C", 150.0, 20.0)])

    assert total == pytest.approx(900.0, rel=0.01)
    assert sum(areas) == pytest.approx(total, rel=1e-6)
    for index in range(5):  # 2' annuli fully inside the square
        expected = math.pi * (
            (BIN_EDGES[index + 1] / 60) ** 2 - (BIN_EDGES[index] / 60) ** 2
        )
        assert areas[index] == pytest.approx(expected, rel=0.03)


def test_bin_areas_with_star_outside_and_without_stars() -> None:
    corners = square(150.0, 20.0, 0.25)
    # A star 20' east of the centre: 5' outside the edge -> first bins empty.
    outside = star("TYC D", 150.0 + (20 / 60) / math.cos(math.radians(20.0)), 20.0)
    total, areas = bin_areas(corners, [outside])

    assert areas[0] == areas[1] == 0.0
    assert areas[2] > 0.0  # 4'-6' reaches in
    assert sum(areas) == pytest.approx(total, rel=1e-6)
    assert bin_areas(corners, [])[1] == [0.0] * (len(BIN_EDGES) - 1)


def test_bin_areas_do_not_depend_on_corner_order() -> None:
    corners = square(150.0, 20.0, 0.25)
    stars = [star("TYC E", 150.05, 20.02)]

    assert bin_areas(corners, stars) == bin_areas(
        [corners[0], corners[2], corners[1], corners[3]], stars
    )


def test_mask_state() -> None:
    assert [mask_state(0, 3), mask_state(1, 3), mask_state(3, 3)] == [
        "unmasked",
        "partially_masked",
        "all_masked",
    ]


def proximity(
    tid,
    bin_,
    status=IdentificationStatus.UNKNOWN,
    built=True,
    mask="all_masked",
    bits=4096,
    sep=None,
) -> TrackletProximity:
    return TrackletProximity(
        field_id="F",
        tracklet_id=tid,
        identification_status=status,
        known_designation=None,
        tracklet_status=(
            TrackletStatus.TRACKLET_BUILT if built else TrackletStatus.REJECTED
        ),
        ra=0.0,
        dec=0.0,
        separation_arcsec=(
            sep
            if sep is not None
            else (None if bin_ is None else BIN_EDGES[bin_] + 1.0)
        ),
        nearest_star="TYC" if bin_ is not None else None,
        radial_bin=bin_,
        mask_state=mask,
        mask_bits_union=bits,
        halo_bit_all=bool(bits >> 12 & 1),
        min_snr=5.0,
        sharp_max=0.5,
        fit_rms_residual_arcsec=0.25,
    )


def test_radial_bins_counts_and_densities() -> None:
    tracklets = [
        proximity("u1", 0),
        proximity("u2", 0, mask="unmasked", bits=0),
        proximity("r1", 0, built=False),
        proximity(
            "k1",
            CONTROL_BIN,
            status=IdentificationStatus.KNOWN,
            mask="unmasked",
            bits=0,
        ),
        proximity("u3", CONTROL_BIN, mask="unmasked", bits=0),
        proximity("a1", 0, status=IdentificationStatus.AMBIGUOUS),
        proximity("n1", None),
    ]
    areas = [2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 100.0]

    bins = radial_bins(tracklets, areas)

    first, control = bins[0], bins[CONTROL_BIN]
    assert (first.unknown_built, first.unknown_rejected, first.known_built) == (2, 1, 0)
    assert first.unknown_built_density == 1.0
    assert first.unknown_built_by_mask == {
        "unmasked": 1,
        "partially_masked": 0,
        "all_masked": 1,
    }
    assert first.unknown_built_halo_bit_all == 1
    assert first.unknown_built_per_mask_bit == {12: 1}
    assert (control.unknown_built, control.known_built) == (1, 1)
    assert control.known_built_density == 0.01
    assert first.label == "0'-2'" and control.label == ">=15'"
    # near (< 10'): 2 in 6 arcmin²; control: 1 in 100 -> 33.3x
    assert near_to_control_ratio(bins) == pytest.approx((2 / 6) / (1 / 100), rel=1e-3)


def test_zero_area_bin_and_empty_control() -> None:
    bins = radial_bins([proximity("u1", 0)], [0.0, 1, 1, 1, 1, 1, 10.0])

    assert bins[0].unknown_built_density is None
    assert near_to_control_ratio(bins) is None  # no control tracklet


def test_visual_sample_is_deterministic_and_stratified() -> None:
    tracklets = (
        [proximity(f"n{i}", 0, sep=30.0 + i) for i in range(10)]
        + [proximity(f"c{i}", CONTROL_BIN, sep=2000.0) for i in range(5)]
        + [
            proximity(
                f"k{i}", CONTROL_BIN, status=IdentificationStatus.KNOWN, sep=2000.0
            )
            for i in range(4)
        ]
        + [proximity(f"r{i}", 0, built=False, sep=10.0) for i in range(5)]
    )
    field = FieldRadial.model_construct(field_id="F", tracklets=tracklets)
    reversed_field = FieldRadial.model_construct(
        field_id="F", tracklets=tracklets[::-1]
    )

    picked = [(g, t.tracklet_id) for g, t in visual_sample(field)]

    assert picked == [(g, t.tracklet_id) for g, t in visual_sample(reversed_field)]
    groups = [g for g, _ in picked]
    assert groups.count("near_unknown") == bright_stars.VISUAL_NEAR
    assert groups.count("control_unknown") == bright_stars.VISUAL_FAR
    assert groups.count("known") == bright_stars.VISUAL_KNOWN
    assert not any(t.startswith("r") for _, t in picked)


def test_compact_keeps_known_and_sampled_records_only() -> None:
    tracklets = [
        proximity("u1", 0),
        proximity("u2", 0),
        proximity("k1", CONTROL_BIN, status=IdentificationStatus.KNOWN),
    ]
    report = BrightStarReport.model_construct(
        generated_at=datetime.now(timezone.utc),
        fields=[
            FieldRadial.model_construct(field_id="F", tracklets=tracklets, bins=[])
        ],
        strips=[SampledStrip.model_construct(field_id="F", tracklet_id="u2")],
    )

    kept = [t.tracklet_id for t in compact(report).fields[0].tracklets]

    assert kept == ["u2", "k1"]


# --- committed evidence ---


AS033 = AS022_REPORT.parent / "as033"


def committed() -> BrightStarReport:
    return BrightStarReport.model_validate_json(
        (AS033 / "as033_bright_stars.json").read_text()
    )


def test_committed_evidence_is_complete_and_reviewed() -> None:
    report = committed()
    reviews = {
        (r["field_id"], r["tracklet_id"])
        for r in json.loads((AS033 / "visual_review.json").read_text())
    }
    for strip in report.strips:
        assert (AS033 / strip.image).is_file()
        assert (strip.field_id, strip.tracklet_id) in reviews
    assert len(reviews) == len(report.strips)
    VisualReview.model_validate(
        json.loads((AS033 / "visual_review.json").read_text())[0]
    )
    ids = [f.field_id for f in report.fields]
    assert ids[:2] == list(bright_stars.REFERENCE_FIELDS)
    assert len(ids) == 2 + bright_stars.SELECTION_FIELDS


def test_committed_bins_cover_the_footprint() -> None:
    for field in committed().fields:
        areas = sum(b.area_arcmin2 for b in field.bins)
        assert areas == pytest.approx(field.conditions.footprint_arcmin2, rel=1e-3)
        assert all(
            s.v_mag is not None and s.v_mag <= 6.5
            for s in field.conditions.bright_stars
        )


def test_committed_selection_matches_evidence_fields() -> None:
    selection = FieldSelection.model_validate_json(
        (AS033 / "as033_fields.json").read_text()
    )
    new = [f for f in committed().fields if f.conditions.role == "new"]

    assert [s.field.field_id for s in selection.fields] == [f.field_id for f in new]
    assert "Amendment 1" in selection.rule
