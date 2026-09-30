import math
from datetime import datetime, timedelta, timezone

import pytest

from app.models.identification import IdentificationStatus
from app.models.quality import SharpAvailability
from app.models.source_detection import SourceDetection
from app.models.tracklet import Tracklet, TrackletDetection, TrackletStatus
from app.services.quality_service import extract_quality_features
from app.validation.runner import ValidationReport
from app.validation.presets import AS022_REPORT
from app.validation.quality import (
    AMBIGUOUS,
    CONTROL,
    OTHER_KNOWN,
    UNKNOWN,
    VALIDATION_TARGET,
    QualityEvidenceReport,
    QualityRecord,
    classify,
    numeric_summary,
    summarize,
)


START = datetime(2018, 4, 11, 10, 0, tzinfo=timezone.utc)


def detection(i: int, **overrides) -> SourceDetection:
    fields = {
        "source_id": f"{100 + i}-{i}",
        "observation_product_id": 100 + i,
        "ra": 120.0 + i * 1e-4,
        "dec": 10.0,
        "x": 10.0,
        "y": 10.0,
        "magnitude": 19.0,
        "magnitude_error": 0.1,
        "snr": 10.0,
        "on_image_edge": False,
        "mask_bits": 0,
    }
    return SourceDetection(**{**fields, **overrides})


def tracklet(*detections: SourceDetection, **overrides) -> Tracklet:
    fields = {
        "tracklet_id": "trk-0001",
        "detections": [
            TrackletDetection(time=START + timedelta(minutes=30 * i), detection=d)
            for i, d in enumerate(detections)
        ],
        "angular_velocity_arcsec_per_min": 0.41,
        "position_angle_deg": 347.0,
        "fit_rms_residual_arcsec": 0.13,
        "fit_max_residual_arcsec": 0.18,
        "status": TrackletStatus.TRACKLET_BUILT,
    }
    return Tracklet(**{**fields, **overrides})


def three(**per_index) -> Tracklet:
    """Three detections; per_index maps field -> list of 3 values."""
    return tracklet(
        *(
            detection(i, **{key: values[i] for key, values in per_index.items()})
            for i in range(3)
        )
    )


def test_snr_and_count() -> None:
    features = extract_quality_features(three(snr=[12.0, 5.0, 8.0]))

    assert features.detection_count == 3
    assert features.min_snr == 5.0
    assert features.median_snr == 8.0


def test_median_of_even_detection_count() -> None:
    t = tracklet(*(detection(i, snr=s) for i, s in enumerate([4.0, 6.0, 10.0, 20.0])))

    features = extract_quality_features(t)

    assert features.detection_count == 4
    assert features.median_snr == 8.0


def test_fit_and_motion_are_copied_unchanged() -> None:
    t = three()

    features = extract_quality_features(t)

    assert features.angular_velocity_arcsec_per_min == t.angular_velocity_arcsec_per_min
    assert features.position_angle_deg == t.position_angle_deg
    assert features.fit_rms_residual_arcsec == t.fit_rms_residual_arcsec
    assert features.fit_max_residual_arcsec == t.fit_max_residual_arcsec
    assert features.tracklet_status is TrackletStatus.TRACKLET_BUILT


def test_magnitude_range_and_significance() -> None:
    features = extract_quality_features(
        three(magnitude=[19.5, 19.0, 19.9], magnitude_error=[0.1, 0.3, 0.4])
    )

    assert features.magnitude_range_mag == pytest.approx(0.9)
    # brightest 19.0 +- 0.3, faintest 19.9 +- 0.4
    assert features.magnitude_range_sigma == pytest.approx(0.9 / 0.5)


def test_constant_magnitude_is_zero_range() -> None:
    features = extract_quality_features(three())

    assert features.magnitude_range_mag == 0.0
    assert features.magnitude_range_sigma == 0.0


def test_zero_photometric_errors_leave_significance_missing() -> None:
    features = extract_quality_features(
        three(magnitude=[19.0, 19.2, 19.1], magnitude_error=[0.0, 0.0, 0.0])
    )

    assert features.magnitude_range_mag == pytest.approx(0.2)
    assert features.magnitude_range_sigma is None


def test_equal_extremes_resolve_in_time_order() -> None:
    features = extract_quality_features(
        three(magnitude=[19.0, 19.0, 19.5], magnitude_error=[0.3, 0.1, 0.4])
    )

    # First brightest (error 0.3) is used, not the later one (0.1).
    assert features.magnitude_range_sigma == pytest.approx(0.5 / 0.5)


def test_flag_aggregation() -> None:
    features = extract_quality_features(
        three(on_image_edge=[True, False, False], mask_bits=[0, 0b1010, 0b0011])
    )

    assert features.edge_detection_count == 1
    assert features.masked_detection_count == 2
    assert features.flagged_detection_count == 3
    assert features.mask_bits_union == 0b1011


def test_edge_and_mask_on_one_detection_count_once() -> None:
    features = extract_quality_features(
        three(on_image_edge=[True, False, False], mask_bits=[4, 0, 0])
    )

    assert features.flagged_detection_count == 1


def test_clean_detections_have_no_flags() -> None:
    features = extract_quality_features(three())

    assert (
        features.edge_detection_count,
        features.masked_detection_count,
        features.flagged_detection_count,
        features.mask_bits_union,
    ) == (0, 0, 0, 0)


def test_sharp_unavailable_without_raw_catalog() -> None:
    features = extract_quality_features(three())

    assert features.sharp_availability is SharpAvailability.UNAVAILABLE
    assert features.sharp_values == []
    assert features.sharp_min is None and features.sharp_max is None


def test_sharp_complete() -> None:
    t = three()
    sharp = {"100-0": 0.05, "101-1": -0.2, "102-2": 0.4}

    features = extract_quality_features(t, sharp)

    assert features.sharp_availability is SharpAvailability.COMPLETE
    assert features.sharp_values == [0.05, -0.2, 0.4]
    assert (features.sharp_min, features.sharp_max) == (-0.2, 0.4)


@pytest.mark.parametrize(
    "sharp",
    [
        {"100-0": 0.05, "102-2": 0.4},  # one detection missing
        {"100-0": 0.05, "101-1": math.nan, "102-2": 0.4},  # non-finite
        {},  # supplied but empty
    ],
    ids=["missing", "nan", "empty"],
)
def test_sharp_partial_is_never_filled_in(sharp) -> None:
    features = extract_quality_features(three(), sharp)

    assert features.sharp_availability is SharpAvailability.PARTIAL
    assert features.sharp_values[1] is None
    assert features.sharp_min is None and features.sharp_max is None


def test_extraction_is_deterministic_and_leaves_input_unchanged() -> None:
    t = three(snr=[12.0, 5.0, 8.0], magnitude=[19.5, 19.0, 19.9], mask_bits=[0, 2, 0])
    before = t.model_dump()
    sharp = {"100-0": 0.05, "101-1": -0.2, "102-2": 0.4}

    runs = [extract_quality_features(t, dict(sharp)) for _ in range(3)]

    assert runs[0] == runs[1] == runs[2]
    assert runs[0].model_dump_json() == runs[1].model_dump_json()
    assert t.model_dump() == before


def test_features_round_trip_through_json() -> None:
    features = extract_quality_features(three(), {"100-0": 0.1})

    assert type(features).model_validate_json(features.model_dump_json()) == features


ROLES = {"48606": "control", "102841": "primary", "900": "marginal"}


@pytest.mark.parametrize(
    ("status", "designation", "expected"),
    [
        (IdentificationStatus.KNOWN, "102841", VALIDATION_TARGET),
        (IdentificationStatus.KNOWN, "48606", CONTROL),
        (IdentificationStatus.KNOWN, "900", OTHER_KNOWN),
        (IdentificationStatus.KNOWN, "12345", OTHER_KNOWN),
        (IdentificationStatus.AMBIGUOUS, "102841", AMBIGUOUS),
        (IdentificationStatus.UNKNOWN, None, UNKNOWN),
    ],
)
def test_population_comes_from_identification_only(
    status, designation, expected
) -> None:
    assert classify(status, designation, ROLES) is expected


def test_numeric_summary() -> None:
    summary = numeric_summary([float(v) for v in range(1, 12)] + [None])

    assert (summary.count, summary.missing) == (11, 1)
    assert (summary.min, summary.median, summary.max) == (1.0, 6.0, 11.0)
    assert (summary.p10, summary.p25, summary.p75, summary.p90) == (2.0, 3.5, 8.5, 10.0)


def test_numeric_summary_edge_cases() -> None:
    assert numeric_summary([None, None]).count == 0
    assert numeric_summary([None, None]).median is None
    single = numeric_summary([3.0])
    assert single.p10 == single.median == single.p90 == 3.0


def test_group_summary_aggregates_categorical_features() -> None:
    def record(t: Tracklet, sharp=None) -> QualityRecord:
        return QualityRecord(
            field_id="F",
            population=UNKNOWN.name,
            identification_status=IdentificationStatus.UNKNOWN,
            known_designation=None,
            target_role=None,
            features=extract_quality_features(t, sharp),
        )

    records = [
        record(three(mask_bits=[0, 2, 0])),
        record(three(on_image_edge=[True, False, False], mask_bits=[0, 6, 0])),
        record(three(), {"100-0": 0.1, "101-1": 0.2, "102-2": 0.3}),
    ]

    group = summarize("g", "test", records)

    assert group.count == 3
    assert group.detection_count == {3: 3}
    assert group.flagged_detection_count == {0: 1, 1: 1, 2: 1}
    assert group.edge_detection_count == {0: 2, 1: 1}
    assert group.mask_bit_tracklets == {1: 2, 2: 1}
    assert group.sharp_availability == {"unavailable": 2, "partial": 0, "complete": 1}
    assert group.numeric["sharp_max"].count == 1
    assert group.numeric["sharp_max"].missing == 2
    assert group.numeric["min_snr"].median == 10.0


# 48606 (1995 DH), POC control: frozen AS-031 evidence ↔ AS-022 reference.

AS031_REPORT = AS022_REPORT.parent / "as031_quality_features.json"


def control_record(report: QualityEvidenceReport) -> QualityRecord:
    [record] = [r for r in report.records if r.known_designation == "48606"]
    return record


def test_1995_dh_features_reproduce_from_the_stored_tracklet() -> None:
    record = control_record(
        QualityEvidenceReport.model_validate_json(AS031_REPORT.read_text())
    )
    sharp = {
        item.detection.source_id: value
        for item, value in zip(record.tracklet.detections, record.features.sharp_values)
    }

    assert extract_quality_features(record.tracklet, sharp) == record.features


def test_1995_dh_tracklet_fit_and_identification_match_as022() -> None:
    """AS-031 changed neither the tracklet, its fit nor its identification."""
    record = control_record(
        QualityEvidenceReport.model_validate_json(AS031_REPORT.read_text())
    )
    as022 = ValidationReport.model_validate_json(AS022_REPORT.read_text())
    [poc] = [r for r in as022.reference_results if r.field_id == record.field_id]
    [reference] = [f for f in poc.tracklets if f.known_designation == "48606"]
    [outcome] = [t for t in poc.targets if t.designation == "48606"]
    features = record.features

    assert record.identification_status is IdentificationStatus.KNOWN
    assert record.population == CONTROL.name
    assert features.tracklet_id == reference.tracklet_id == outcome.tracklet_id
    assert features.angular_velocity_arcsec_per_min == reference.rate_arcsec_per_min
    assert features.position_angle_deg == reference.position_angle_deg
    assert features.fit_rms_residual_arcsec == reference.fit_rms_residual_arcsec
    assert features.fit_max_residual_arcsec == reference.fit_max_residual_arcsec
    assert features.min_snr == reference.min_snr
    assert features.median_snr == reference.median_snr
    assert features.magnitude_range_mag == reference.magnitude_spread
    assert features.flagged_detection_count == reference.flagged_detections
    assert features.sharp_values == reference.sharp_values
    assert record.identification_max_residual_arcsec == outcome.max_residual_arcsec
