import json
from datetime import timedelta

import httpx
import pytest

from app.models.frame_sources import FrameSources
from app.models.known_object import KnownObjectEphemeris, KnownObjectField
from app.services.ztf_service import ZTFServiceError
from app.validation.data import FieldData, fetch_frame_metadata
from app.validation.evaluate import evaluate_field
from app.validation.models import (
    FrameMetadata,
    PipelineConfig,
    TargetSelectionRule,
    ValidationField,
)
from app.validation.runner import (
    REFERENCE_CONFIG,
    render_markdown,
    run_validation,
    sweep_configs,
)
from app.validation.selection import (
    inside_footprint,
    predicted_motion,
    select_targets,
)
from tests.synthetic_frames import ARCSEC, make_detection, make_frame


MINUTES = [0, 30, 60]
PRODUCT_IDS = [1, 2, 3]
CENTER = (120.0, 10.0)
HALF_SIZE = 0.4  # deg, synthetic quadrant half-width
CONFIG = PipelineConfig(
    stationary_tolerance_arcsec=1.5,
    max_rate_arcsec_per_min=1.0,
    search_radius_arcsec=2.0,
    max_residual_arcsec=0.5,
    match_radius_arcsec=2.0,
)
RATE_RA_ARCSEC_PER_MIN = 0.5  # coordinate RA rate; on-sky ~0.49"/min at Dec 10


def frame_metadata(product_id: int, maglimit: float = 20.5) -> FrameMetadata:
    ra, dec = CENTER
    return FrameMetadata(
        product_id=product_id,
        center_ra=ra,
        center_dec=dec,
        corners=[
            (ra + HALF_SIZE, dec + HALF_SIZE),
            (ra - HALF_SIZE, dec + HALF_SIZE),
            (ra - HALF_SIZE, dec - HALF_SIZE),
            (ra + HALF_SIZE, dec - HALF_SIZE),
        ],
        maglimit=maglimit,
        seeing_arcsec=2.0,
        airmass=1.2,
    )


def mover(start: tuple[float, float], minute: float) -> tuple[float, float]:
    return (start[0] + RATE_RA_ARCSEC_PER_MIN * minute * ARCSEC, start[1])


def ephemeris(
    designation: str,
    position: tuple[float, float],
    v_magnitude: float = 19.0,
    position_error: float = 0.1,
) -> KnownObjectEphemeris:
    return KnownObjectEphemeris(
        designation=designation,
        number=int(designation) if designation.isdigit() else None,
        name=f"Object {designation}",
        object_class="MB>Middle",
        predicted_ra=position[0],
        predicted_dec=position[1],
        v_magnitude=v_magnitude,
        position_error_arcsec=position_error,
        distance_from_field_center_arcsec=100.0,
        motion_ra_cos_dec_arcsec_per_hour=RATE_RA_ARCSEC_PER_MIN * 60 * 0.9848,
        motion_dec_arcsec_per_hour=0.0,
    )


def skybot_fields(objects_at_minute) -> list[KnownObjectField]:
    return [
        KnownObjectField(
            epoch_jd_utc=2458219.9 + minute / 1440,
            field_ra=CENTER[0],
            field_dec=CENTER[1],
            field_radius_degrees=0.6,
            observer="I41",
            objects=objects_at_minute(minute),
            rejected_rows=[],
        )
        for minute in MINUTES
    ]


def frames_with(positions_at_minute) -> list[FrameSources]:
    frames = []
    for product_id, minute in zip(PRODUCT_IDS, MINUTES):
        frame = make_frame(product_id, minute, positions_at_minute(minute))
        observation = frame.observation.model_copy(
            update={"exposure_seconds": 30.0}
        )
        frames.append(frame.model_copy(update={"observation": observation}))
    return frames


STAR_A = (120.1, 10.1)
STAR_B = (119.9, 9.95)
TARGET_START = (120.02, 10.02)


# --- selection -------------------------------------------------------------


def test_inside_footprint() -> None:
    metadata = frame_metadata(1)

    assert inside_footprint(120.0, 10.0, metadata)
    assert inside_footprint(120.35, 9.7, metadata)
    assert not inside_footprint(120.5, 10.0, metadata)
    assert not inside_footprint(120.0, 10.45, metadata)


def test_predicted_motion_rate_and_angle() -> None:
    ephem = ephemeris("1", CENTER).model_copy(
        update={
            "motion_ra_cos_dec_arcsec_per_hour": -30.0,
            "motion_dec_arcsec_per_hour": 30.0,
        }
    )

    rate, angle = predicted_motion(ephem)

    assert rate == pytest.approx((2 * 30.0**2) ** 0.5 / 60)
    assert angle == pytest.approx(315.0)


def test_selection_roles_follow_the_pre_registered_rule() -> None:
    metadata = [
        frame_metadata(pid, maglimit)
        for pid, maglimit in zip(PRODUCT_IDS, [20.8, 20.5, 20.6])
    ]
    fields = skybot_fields(
        lambda minute: [
            ephemeris("100", mover(TARGET_START, minute), v_magnitude=19.9),
            ephemeris("200", mover(TARGET_START, minute), v_magnitude=20.9),
            ephemeris("300", mover(TARGET_START, minute), v_magnitude=21.1),
            ephemeris(
                "400", mover(TARGET_START, minute), position_error=5.0
            ),
            ephemeris("500", (121.0, 10.0)),  # outside the footprint
        ]
    )

    targets = select_targets("F", metadata, fields, TargetSelectionRule())

    assert {t.designation: t.role for t in targets} == {
        "100": "primary",  # 19.9 <= 20.5 - 0.5
        "200": "marginal",  # 20.9 <= 20.5 + 0.5
    }
    assert targets[0].predicted_positions[2] == pytest.approx(
        mover(TARGET_START, 60)
    )


def test_selection_requires_the_object_in_every_frame() -> None:
    metadata = [frame_metadata(pid) for pid in PRODUCT_IDS]
    fields = skybot_fields(
        lambda minute: []
        if minute == 30
        else [ephemeris("100", mover(TARGET_START, minute))]
    )

    assert select_targets("F", metadata, fields, TargetSelectionRule()) == []


def test_controls_bypass_brightness_and_error_cuts_only() -> None:
    metadata = [frame_metadata(pid) for pid in PRODUCT_IDS]
    fields = skybot_fields(
        lambda minute: [
            ephemeris("48606", mover(TARGET_START, minute), v_magnitude=21.5),
            ephemeris("999", (121.0, 10.0), v_magnitude=15.0),
        ]
    )

    targets = select_targets(
        "F",
        metadata,
        fields,
        TargetSelectionRule(),
        frozenset({"48606", "999"}),
    )

    assert [(t.designation, t.role) for t in targets] == [("48606", "control")]


# --- evaluation ------------------------------------------------------------


def evaluate(positions_at_minute, objects_at_minute):
    metadata = [frame_metadata(pid) for pid in PRODUCT_IDS]
    fields = skybot_fields(objects_at_minute)
    targets = select_targets("F", metadata, fields, TargetSelectionRule())
    frames = frames_with(positions_at_minute)
    return evaluate_field("F", frames, fields, targets, CONFIG)


def test_target_moving_through_star_field_is_recovered() -> None:
    result = evaluate(
        lambda minute: [STAR_A, STAR_B, mover(TARGET_START, minute)],
        lambda minute: [ephemeris("100", mover(TARGET_START, minute))],
    )

    [outcome] = result.targets
    assert outcome.recovered
    assert outcome.detected_frames == 3
    assert outcome.candidate_frames == 3
    assert result.primary_recovered == result.primary_targets == 1
    assert result.known_count == 1
    [features] = result.tracklets
    assert features.is_validation_target
    assert features.rate_difference_arcsec_per_min == pytest.approx(0.0, abs=0.01)
    assert features.position_angle_difference_deg == pytest.approx(0.0, abs=0.5)


def test_missing_detection_is_reported_as_two_of_three() -> None:
    result = evaluate(
        lambda minute: [STAR_A]
        + ([] if minute == 30 else [mover(TARGET_START, minute)]),
        lambda minute: [ephemeris("100", mover(TARGET_START, minute))],
    )

    [outcome] = result.targets
    assert not outcome.recovered
    assert outcome.detected_frames == 2
    assert outcome.nearest_detection_arcsec[1] is None


def test_target_on_a_star_position_is_flagged_stationary() -> None:
    # In the last frame the asteroid sits 1 arcsec from where a star
    # appears in the first frame.
    blend = mover(TARGET_START, 60)
    star = (blend[0], blend[1] + 1.0 * ARCSEC)
    result = evaluate(
        lambda minute: [mover(TARGET_START, minute)]
        + ([star] if minute == 0 else []),
        lambda minute: [ephemeris("100", mover(TARGET_START, minute))],
    )

    [outcome] = result.targets
    assert not outcome.recovered
    assert outcome.detected_frames == 3
    assert outcome.candidate_frames == 2


def test_unknown_tracklet_features_have_no_prediction() -> None:
    result = evaluate(
        lambda minute: [mover(TARGET_START, minute)],
        lambda minute: [],
    )

    [features] = result.tracklets
    assert features.known_designation is None
    assert features.predicted_rate_arcsec_per_min is None
    assert result.unknown_built_count == 1


# --- runner ----------------------------------------------------------------


def test_sweep_configs_vary_one_parameter_at_a_time() -> None:
    points = sweep_configs(
        REFERENCE_CONFIG,
        {"match_radius_arcsec": [1.0, 2.0], "max_rate_arcsec_per_min": [0.5]},
    )

    assert [(name, value) for name, value, _ in points] == [
        ("match_radius_arcsec", 1.0),
        ("max_rate_arcsec_per_min", 0.5),
    ]
    changed = points[0][2]
    assert changed.match_radius_arcsec == 1.0
    assert changed.max_rate_arcsec_per_min == REFERENCE_CONFIG.max_rate_arcsec_per_min


def test_run_validation_with_fake_loader_produces_report() -> None:
    field = ValidationField(
        field_id="F",
        description="synthetic",
        product_ids=PRODUCT_IDS,
        selection_note="test",
    )
    frames = frames_with(lambda minute: [STAR_A, mover(TARGET_START, minute)])

    def loader(field, client) -> FieldData:
        return FieldData(
            field=field,
            observations=[frame.observation for frame in frames],
            frame_metadata=[frame_metadata(pid) for pid in PRODUCT_IDS],
            frames=frames,
            sharp_by_source_id={},
            skybot_fields=skybot_fields(
                lambda minute: [ephemeris("100", mover(TARGET_START, minute))]
            ),
        )

    report = run_validation(
        [field],
        reference=CONFIG,
        grid={"match_radius_arcsec": [0.5, 2.0]},
        loader=loader,
    )

    assert report.reference_results[0].primary_recovered == 1
    assert report.reference_results[0].tracklets
    assert [point.value for point in report.sweep] == [0.5]
    assert report.sweep[0].results[0].tracklets == []
    markdown = render_markdown(report)
    assert "| F | 100 |" in markdown
    assert "recovered" in markdown
    assert json.loads(report.model_dump_json())["snapshots"][0]["targets"]


# --- IRSA metadata ---------------------------------------------------------


METADATA_HEADER = (
    "obsdate,obsjd,field,filtercode,ccdid,qid,pid,filefracday,imgtypecode,"
    "exptime,ra,dec,ra1,dec1,ra2,dec2,ra3,dec3,ra4,dec4,maglimit,seeing,airmass"
)


def metadata_row(pid: int, time: str) -> str:
    return (
        f"2018-04-11 {time}+00,2458219.9,535,zr,11,3,{pid},20180411467847,o,"
        "30.000,255.57,12.28,256.0,12.7,255.1,12.7,255.1,11.8,256.0,11.8,"
        "20.75,2.96,1.15"
    )


def test_fetch_frame_metadata_sorts_by_time() -> None:
    body = "\n".join(
        [METADATA_HEADER, metadata_row(2, "11:13:43"), metadata_row(1, "10:09:45")]
    )
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=body))

    with httpx.Client(transport=transport) as client:
        observations, metadata = fetch_frame_metadata([1, 2], client)

    assert [o.product_id for o in observations] == [1, 2]
    assert metadata[0].maglimit == pytest.approx(20.75)
    assert metadata[0].corners[2] == (255.1, 11.8)
    assert observations[0].exposure_seconds == 30.0


def test_fetch_frame_metadata_reports_missing_frames() -> None:
    body = "\n".join([METADATA_HEADER, metadata_row(1, "10:09:45")])
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=body))

    with httpx.Client(transport=transport) as client:
        with pytest.raises(ZTFServiceError, match=r"\[2\]"):
            fetch_frame_metadata([1, 2], client)


def test_start_times_are_consistent_with_minutes() -> None:
    frames = frames_with(lambda minute: [])

    assert frames[2].observation.observed_at - frames[0].observation.observed_at == (
        timedelta(minutes=60)
    )
