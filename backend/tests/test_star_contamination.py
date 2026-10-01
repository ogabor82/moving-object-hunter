import math

import pytest

from app.validation import star_contamination as sc
from app.validation.star_contamination import build_population, sibling_sequences


def row(pid, expid, qid, jd, ccd=13):
    return {
        "pid": str(pid), "expid": str(expid), "qid": str(qid), "ccdid": str(ccd),
        "obsjd": str(jd), "obsdate": "2019-01-25 05:00:00+00", "field": "565",
        "filtercode": "zr", "filefracday": "20190125204845", "exptime": "30",
    }


def test_preregistered_bins_are_monotonic_and_fixed() -> None:
    assert list(sc.MAG_EDGES[1:]) == [4.0, 6.0, 8.0, 10.0, 11.0]
    assert math.isinf(sc.MAG_EDGES[0])
    assert sc.ANNULUS_EDGES == (0.0, 15.0, 30.0, 60.0, 120.0, 240.0, 480.0, 900.0)
    assert sc.BACKGROUND_ANNULUS == 6
    assert all(a < b for a, b in zip(sc.ANNULUS_EDGES, sc.ANNULUS_EDGES[1:]))


def test_sibling_sequences_group_by_quadrant_in_time_order() -> None:
    rows = [row(13, 2, 1, 2.0), row(11, 1, 1, 1.0), row(12, 1, 2, 1.0), row(14, 3, 1, 3.0)]

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
            return [row(p, 100 + i, 3, i) for i, p in enumerate(parents["B-2019-01-25-565-c13-q3"])]
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
    assert [f.field.field_id for f in first.fields] == [f.field.field_id for f in again.fields]
    assert any("q2: 2 exposures, skipped" in line for line in first.log)
    assert any("q4: products missing" in line for line in first.log)
    assert len([f for f in first.fields if f.origin != f"sibling of {next(iter(parents))}"]) == 8


def test_committed_population() -> None:
    population = sc.Population.model_validate_json(
        (sc.AS022_REPORT.parent / "as034" / "as034_population.json").read_text()
    )

    ids = [f.field.field_id for f in population.fields]
    assert len(ids) == len(set(ids)) == 26
    assert population.preregistration == sc.PREREGISTRATION
    assert all(len(f.field.product_ids) == 3 for f in population.fields)
