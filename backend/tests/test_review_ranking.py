import inspect
import json
import os
import random
from datetime import timedelta
from pathlib import Path

import pytest

from app.models.quality import SharpAvailability
from app.models.review_ranking import M1Features, RankedCandidate, ReviewSemantics
from app.models.tracklet import TrackletStatus
from app.services import review_ranking_service as rr
from app.services import catalog_service
from app.services.catalog_service import load_frame_sources, psf_sharp_by_source_id
from app.services.ztf_service import ZTFPSFCatalog
from app.validation import ranking_design as rd
from app.validation import review_ranking_equivalence as eq
from app.validation import sealed_validation as sv
from tests.test_catalog_service import MAGZP, OBSERVATION, make_row
from tests.test_quality_features import detection, tracklet

ROOT = Path(__file__).resolve().parents[1]
M1_NAMES = [name for name, _ in rr.M1_INPUTS]


def trk(n: int, snr=(10.0, 10.0, 10.0), rms=0.1, mask=(0, 0, 0), status=TrackletStatus.TRACKLET_BUILT,
        sources=None, **overrides):
    """Tracklet trk-<n> with distinct detections (or the given source ids)."""
    sources = sources or [f"{100 + i}-{n * 10 + i}" for i in range(3)]
    return tracklet(
        *(
            detection(i, source_id=sources[i], snr=snr[i], mask_bits=mask[i])
            for i in range(3)
        ),
        tracklet_id=f"trk-{n:04d}",
        fit_rms_residual_arcsec=rms,
        fit_max_residual_arcsec=max(rms, 0.18),
        status=status,
        **overrides,
    )


def sharp_for(*tracklets, value=0.1) -> dict[str, float]:
    return {d.detection.source_id: value for t in tracklets for d in t.detections}


def rank(tracklets, sharp=None):
    observations = [OBSERVATION.model_copy(update={"product_id": 100 + i}) for i in range(3)]
    return rr.rank_for_review(tracklets, sharp if sharp is not None else sharp_for(*tracklets), observations)


# --- frozen specification ------------------------------------------------------------


def test_production_constants_are_the_frozen_m1() -> None:
    frozen = json.loads((ROOT / sv.FROZEN_RANKER_FILE).read_text())["ranker"]
    assert eq.check_spec(ROOT)["equal"]
    assert [(i["feature"], i["direction"]) for i in frozen["inputs"]] == list(rr.M1_INPUTS)
    assert set(frozen["weights"].values()) == {rr.M1_WEIGHT} == {0.125}
    assert rr.M1_INTERCEPT == frozen["intercept"] == 0.0 and frozen["fitted"] is False
    assert rr.MISSING_PERCENTILE == 0.0
    # Directions are the AS-037 pre-registered ones.
    assert all(rd.CANDIDATE_FEATURES[name] == direction for name, direction in rr.M1_INPUTS)


def test_ranker_inputs_are_exactly_the_eight_frozen_features() -> None:
    assert list(M1Features.model_fields) == M1_NAMES
    spec = rr.m1_spec()
    assert [i.feature for i in spec.inputs] == M1_NAMES
    # No identity / SkyBoT / proximity / motion input anywhere in the scorer.
    forbidden = ("ident", "skybot", "designation", "known", "star", "proximity", "velocity", "angle")
    for function in (rr.m1_features, rr.m1_scores, rr.rank_for_review):
        parameters = " ".join(inspect.signature(function).parameters).lower()
        assert not any(word in parameters for word in forbidden)


# --- feature semantics (same definitions as the AS-038 tables) -----------------------


def test_feature_values_follow_the_as038_definitions() -> None:
    a = trk(1, snr=(12.3456789, 5.0, 8.0), rms=0.1234567, mask=(0, 4, 0))
    a = a.model_copy(update={"detections": [
        d.model_copy(update={"detection": d.detection.model_copy(update={"magnitude": m, "on_image_edge": e})})
        for d, m, e in zip(a.detections, (19.0, 19.75, 19.5), (False, False, True))
    ]})
    b = trk(2, sources=[a.detections[0].detection.source_id, "101-99", "102-99"])
    sharp = {**sharp_for(a, b), a.detections[1].detection.source_id: -0.42}

    [(fa, availability), (fb, _)] = rr.m1_features([a, b], sharp)

    assert fa.min_snr == 5.0 and fa.median_snr == 8.0
    assert fa.fit_rms_residual_arcsec == 0.123457  # AS-038 table precision
    assert fa.magnitude_range_mag == 0.75
    assert fa.masked_detection_count == 1
    assert fa.flagged_detection_count == 2  # masked or on the edge
    assert fa.sharp_abs_max == 0.42  # max |sharp|
    assert availability is SharpAvailability.COMPLETE
    assert fa.shared_detection_tracklets == 1 and fb.shared_detection_tracklets == 1


def test_sharp_abs_max_is_missing_unless_sharp_is_complete() -> None:
    a = trk(1)
    partial = sharp_for(a)
    del partial[a.detections[2].detection.source_id]

    [(f_partial, partial_state)] = rr.m1_features([a], partial)
    [(f_none, none_state)] = rr.m1_features([a], {})

    assert f_partial.sharp_abs_max is None and partial_state is SharpAvailability.PARTIAL
    assert f_none.sharp_abs_max is None and none_state is SharpAvailability.PARTIAL


def test_shared_detection_count_is_taken_among_built_tracklets_only() -> None:
    a = trk(1)
    rejected = trk(2, sources=[a.detections[0].detection.source_id, "101-77", "102-77"],
                   status=TrackletStatus.REJECTED)

    ranking = rank([a, rejected])

    [candidate] = ranking.candidates
    shared = next(e for e in candidate.evidence if e.feature == "shared_detection_tracklets")
    assert shared.value == 0
    with pytest.raises(ValueError):
        rr.m1_features([rejected], {})


# --- percentiles, directions, ties, missing ------------------------------------------


def test_oriented_percentiles_equal_the_research_definition() -> None:
    rng = random.Random(41)
    for _ in range(200):
        values = [rng.choice([None, *range(6)]) if rng.random() < 0.3 else rng.random() for _ in range(rng.randint(1, 30))]
        for direction in (1, -1):
            assert rr.oriented_percentiles(values, direction) == rd.within_field_percentile(values, direction)


def test_percentile_directions_ties_and_missing() -> None:
    assert rr.oriented_percentiles([1.0, 2.0, 3.0], 1) == [1 / 6, 0.5, 5 / 6]
    assert rr.oriented_percentiles([1.0, 2.0, 3.0], -1) == [5 / 6, 0.5, 1 / 6]
    assert rr.oriented_percentiles([2.0, 2.0, 1.0], 1) == [2 / 3, 2 / 3, 1 / 6]  # ties count half
    assert rr.oriented_percentiles([None, 1.0], -1) == [None, 0.5]


def test_score_is_the_equal_weight_sum_and_missing_counts_zero() -> None:
    high = trk(1, snr=(20.0, 20.0, 20.0), rms=0.05)
    low = trk(2, snr=(4.0, 4.0, 4.0), rms=0.4, mask=(1, 1, 1))
    sharp = sharp_for(high)  # `low` has no sharp: missing

    ranking = rank([low, high], sharp)

    first, second = ranking.candidates
    assert first.tracklet_id == high.tracklet_id  # higher SNR, lower RMS, unmasked first
    for c in ranking.candidates:
        assert c.review_priority_score == pytest.approx(sum(e.contribution for e in c.evidence), abs=1e-15)
        assert all(e.weight == 0.125 for e in c.evidence)
        assert [e.feature for e in c.evidence] == M1_NAMES
    sharp_low = next(e for e in second.evidence if e.feature == "sharp_abs_max")
    assert sharp_low.value is None and sharp_low.percentile is None and sharp_low.contribution == 0.0
    assert any("without a complete raw sharp" in note for note in ranking.domain_notes)


def test_equal_scores_keep_build_order_deterministically() -> None:
    tracklets = [trk(n) for n in (7, 3, 12, 1)]  # identical features -> identical scores

    first = rank(tracklets)
    second = rank(tracklets)

    assert [c.tracklet_id for c in first.candidates] == ["trk-0007", "trk-0003", "trk-0012", "trk-0001"]
    assert len({c.review_priority_score for c in first.candidates}) == 1
    assert first == second
    assert rr.review_order([0.5, 0.7, 0.5, 0.7]) == [1, 3, 0, 2]


def test_input_order_changes_only_the_tie_order_not_the_scores() -> None:
    rng = random.Random(7)
    tracklets = [trk(n, snr=(rng.uniform(3, 30),) * 3, rms=rng.uniform(0.01, 0.5)) for n in range(1, 25)]
    shuffled = tracklets[:]
    rng.shuffle(shuffled)

    a = {c.tracklet_id: c.review_priority_score for c in rank(tracklets).candidates}
    b = {c.tracklet_id: c.review_priority_score for c in rank(shuffled).candidates}

    assert a == b


# --- input isolation -----------------------------------------------------------------


def test_motion_position_and_time_do_not_change_scores() -> None:
    tracklets = [trk(n, snr=(5.0 + n,) * 3, rms=0.05 * n) for n in range(1, 6)]
    moved = [
        t.model_copy(update={
            "angular_velocity_arcsec_per_min": 0.9,
            "position_angle_deg": 123.0,
            "detections": [
                d.model_copy(update={
                    "time": d.time + timedelta(days=30),
                    "detection": d.detection.model_copy(update={"ra": 10.0 + i, "dec": -40.0}),
                })
                for i, d in enumerate(t.detections)
            ],
        })
        for t in tracklets
    ]

    before = [(c.tracklet_id, c.review_priority_score) for c in rank(tracklets).candidates]
    after = [(c.tracklet_id, c.review_priority_score) for c in rank(moved).candidates]

    assert before == after


# --- no filtering --------------------------------------------------------------------


def test_every_tracklet_is_returned_none_filtered() -> None:
    rng = random.Random(3)
    built = [
        trk(n, snr=(rng.uniform(3, 6),) * 3, rms=rng.uniform(0.01, 0.5), mask=(4096,) * 3 if n % 3 == 0 else (0, 0, 0))
        for n in range(1, 101)
    ]
    rejected = [trk(n, status=TrackletStatus.REJECTED, rms=0.9) for n in range(101, 104)]
    sharp = sharp_for(*built[::2])  # half without sharp

    ranking = rank([*built, *rejected], sharp)

    assert sorted(c.tracklet_id for c in ranking.candidates) == sorted(t.tracklet_id for t in built)
    assert [c.review_rank for c in ranking.candidates] == list(range(1, 101))
    assert [u.tracklet_id for u in ranking.unranked] == [t.tracklet_id for t in rejected]
    scores = [c.review_priority_score for c in ranking.candidates]
    assert scores == sorted(scores, reverse=True)
    # The lowest-ranked (faint, masked, no sharp) candidates are still there in full.
    assert ranking.candidates[-1].tracklet.detections
    assert ranking.semantics == ReviewSemantics()
    assert ranking.semantics.candidates_filtered is False and ranking.semantics.complete is True


def test_score_is_not_presented_as_a_probability() -> None:
    semantics = ReviewSemantics()
    description = RankedCandidate.model_fields["review_priority_score"].description
    assert semantics.purpose == "review_priority_only"
    assert semantics.is_classifier is False and semantics.score_is_probability is False
    assert "NOT a probability" in description
    assert not any(word in RankedCandidate.model_fields for word in ("probability", "confidence", "label", "is_real"))


def test_view_references_the_build_frames_and_the_track() -> None:
    t = trk(1)

    [candidate] = rank([t]).candidates

    assert candidate.view.product_ids == [100, 101, 102]
    assert candidate.view.size_arcsec >= 60.0
    assert candidate.view.center_dec == pytest.approx(10.0, abs=1e-6)
    assert min(d.detection.ra for d in t.detections) <= candidate.view.center_ra <= max(
        d.detection.ra for d in t.detections
    )


# --- sharp in the production catalog path --------------------------------------------


def test_catalog_path_keeps_finite_sharp_beside_the_detections(monkeypatch) -> None:
    catalog = ZTFPSFCatalog(
        rows=[make_row(sourceid=1, sharp=-0.3), make_row(sourceid=2, sharp=float("nan")), make_row(sourceid=3)],
        magnitude_zero_point=MAGZP,
    )
    monkeypatch.setattr(catalog_service, "fetch_psf_catalog", lambda observation, client: catalog)

    [frame] = load_frame_sources([OBSERVATION])

    expected = {f"{OBSERVATION.product_id}-1": -0.3, f"{OBSERVATION.product_id}-3": 0.083}
    assert psf_sharp_by_source_id(OBSERVATION, catalog) == expected
    assert frame.sharp_by_source_id == expected
    assert {d.source_id for d in frame.detections} >= set(expected)


# --- research vs production equivalence on the committed AS-038/040 tables ------------


def test_production_scorer_is_bit_identical_to_the_frozen_research_scorer() -> None:
    result = eq.offline(ROOT)

    assert result["spec"]["equal"]
    dev, val = result["splits"].values()
    assert (dev["quadrant_nights"], dev["tracklets"]) == (56, 18366)
    assert (val["quadrant_nights"], val["tracklets"]) == (24, 10817)
    for split in (dev, val):
        assert split["scores_identical_fields"] == split["order_identical_fields"] == split["quadrant_nights"]
        assert split["max_abs_difference"] == 0.0
        assert split["metrics_identical"]
    assert dev["m1_from_production_scores"]["recall_5"] == pytest.approx(0.955, abs=5e-4)
    assert val["m1_from_production_scores"]["recall_5"] == pytest.approx(0.939, abs=5e-4)


# --- live: the API path from raw IRSA catalogs equals the research table ---------------


@pytest.mark.integration
@pytest.mark.skipif(os.environ.get("RUN_ZTF_INTEGRATION") != "1", reason="set RUN_ZTF_INTEGRATION=1")
def test_live_api_path_reproduces_the_research_m1_on_the_poc_quadrant_night() -> None:
    field_id = "POC-2018-04-11-535-c11-q3"
    rows = [r for r in eq.rc.load_development(ROOT)[1] if r["field_id"] == field_id]

    result = eq.live_field(ROOT, field_id, rows, eq.frozen_spec(ROOT))

    assert result["same_built_tracklets"] and result["built_production"] == 14
    assert result["sharp_complete"] == 14
    assert result["feature_mismatches"] == [] and result["score_mismatches"] == []
    assert result["order_identical"]
