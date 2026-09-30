import math

import pytest

from app.validation import bright_stars
from app.validation.bright_stars import (
    TychoStar,
    bright,
    johnson_v,
    parse_tycho_tsv,
    pick_sequence,
    select_fields,
    selection_order,
)


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
        tycho_id=tycho_id, ra=ra, dec=dec, vt_mag=v, bt_mag=None, v_mag=v,
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
    return {"pid": str(pid), "obsjd": str(jd), "obsdate": f"{date} 05:00:00+00",
            "field": field, "ccdid": ccd, "qid": qid, "filtercode": filt}


def test_pick_sequence_takes_earliest_qualifying_group_first_middle_last() -> None:
    rows = [
        row(1, 10.1, "2018-05-01"), row(2, 10.2, "2018-05-01"),  # only 2
        row(9, 20.4, "2018-06-01"), row(7, 20.1, "2018-06-01"),
        row(8, 20.2, "2018-06-01"), row(6, 20.3, "2018-06-01"),
        row(5, 30.1, "2018-07-01"), row(4, 30.2, "2018-07-01"), row(3, 30.3, "2018-07-01"),
        row(10, 15.1, "2018-05-20", qid="2"), row(11, 15.2, "2018-05-20", qid="3"),
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

    first = select_fields(
        metadata=metadata, tycho=lambda params, client: ("url", stars)
    )
    again = select_fields(
        metadata=metadata, tycho=lambda params, client: ("url", list(reversed(stars)))
    )

    assert len(first.fields) == 2
    assert [f.field.product_ids for f in first.fields] == [
        f.field.product_ids for f in again.fields
    ]
    assert all(len(f.field.product_ids) == 3 for f in first.fields)
    outcomes = [entry.outcome for entry in first.log]
    assert sum(o.startswith("selected") for o in outcomes) == 2
    assert all(o.startswith(("selected", "no quadrant-night")) for o in outcomes)
    assert first.rule == bright_stars.SELECTION_RULE
