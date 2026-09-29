import json
from datetime import timedelta

import httpx
import pytest
from pydantic import ValidationError

from app.models.identification import IdentificationConfig, IdentificationStatus
from app.models.known_object import KnownObjectEphemeris, KnownObjectField
from app.models.observation import Observation
from app.models.tracklet import Tracklet, TrackletDetection, TrackletStatus
from app.services.identification_service import (
    identify_tracklets,
    match_tracklets_to_known_objects,
    mid_exposure_jd_utc,
)
from app.services.skybot_service import SkyBoTServiceError
from tests.synthetic_frames import ARCSEC, START_TIME, make_detection


CONFIG = IdentificationConfig(match_radius_arcsec=2.0)
MINUTES = [0, 30, 60]
PRODUCT_IDS = [101, 102, 103]


def mover_position(minute: float) -> tuple[float, float]:
    return (120.0 + 0.5 * minute * ARCSEC, 10.0 + 0.2 * minute * ARCSEC)


def make_tracklet(
    tracklet_id: str = "trk-0001",
    status: TrackletStatus = TrackletStatus.TRACKLET_BUILT,
) -> Tracklet:
    return Tracklet(
        tracklet_id=tracklet_id,
        detections=[
            TrackletDetection(
                time=START_TIME + timedelta(minutes=minute),
                detection=make_detection(product_id, 0, *mover_position(minute)),
            )
            for minute, product_id in zip(MINUTES, PRODUCT_IDS)
        ],
        angular_velocity_arcsec_per_min=0.53,
        position_angle_deg=68.0,
        fit_rms_residual_arcsec=0.0,
        fit_max_residual_arcsec=0.0,
        status=status,
    )


def ephemeris(
    designation: str,
    ra: float,
    dec: float,
    position_error: float = 0.05,
) -> KnownObjectEphemeris:
    return KnownObjectEphemeris(
        designation=designation,
        number=int(designation) if designation.isdigit() else None,
        name=f"Object {designation}",
        object_class="MB>Middle",
        predicted_ra=ra,
        predicted_dec=dec,
        v_magnitude=19.8,
        position_error_arcsec=position_error,
        distance_from_field_center_arcsec=100.0,
        motion_ra_cos_dec_arcsec_per_hour=29.5,
        motion_dec_arcsec_per_hour=12.0,
    )


def make_fields(objects_per_minute) -> dict[int, KnownObjectField]:
    return {
        product_id: KnownObjectField(
            epoch_jd_utc=2458219.9 + minute / 1440,
            field_ra=120.0,
            field_dec=10.0,
            field_radius_degrees=0.1,
            observer="I41",
            objects=objects_per_minute(minute),
            rejected_rows=[],
        )
        for minute, product_id in zip(MINUTES, PRODUCT_IDS)
    }


def offset(position: tuple[float, float], dec_arcsec: float) -> tuple[float, float]:
    return (position[0], position[1] + dec_arcsec * ARCSEC)


def test_single_consistent_object_is_known_with_residuals() -> None:
    fields = make_fields(
        lambda minute: [ephemeris("48606", *offset(mover_position(minute), 0.5))]
    )

    result = match_tracklets_to_known_objects([make_tracklet()], fields, CONFIG)

    [identification] = result.identifications
    assert identification.status is IdentificationStatus.KNOWN
    assert identification.best_match.designation == "48606"
    assert identification.best_match.max_residual_arcsec == pytest.approx(
        0.5, rel=1e-3
    )
    assert identification.best_match.rms_residual_arcsec == pytest.approx(
        0.5, rel=1e-3
    )
    residual = identification.best_match.residuals[1]
    assert residual.observation_product_id == 102
    assert residual.epoch_jd_utc == fields[102].epoch_jd_utc
    assert residual.residual_arcsec == pytest.approx(0.5, rel=1e-3)
    assert result.diagnostics.known_count == 1


def test_no_object_within_radius_is_unknown_not_a_discovery() -> None:
    fields = make_fields(
        lambda minute: [ephemeris("48606", *offset(mover_position(minute), 3.0))]
    )

    [identification] = match_tracklets_to_known_objects(
        [make_tracklet()], fields, CONFIG
    ).identifications

    assert identification.status is IdentificationStatus.UNKNOWN
    assert identification.best_match is None
    assert identification.candidate_matches == []
    assert "no known object" in identification.status_reason


def test_empty_fields_give_unknown() -> None:
    fields = make_fields(lambda minute: [])

    result = match_tracklets_to_known_objects([make_tracklet()], fields, CONFIG)

    assert result.identifications[0].status is IdentificationStatus.UNKNOWN
    assert result.diagnostics.known_objects_per_frame == [0, 0, 0]


def test_object_must_match_every_detection() -> None:
    # Matches the first two detections but is 3 arcsec off at the third.
    fields = make_fields(
        lambda minute: [
            ephemeris(
                "48606",
                *offset(mover_position(minute), 3.0 if minute == 60 else 0.2),
            )
        ]
    )

    [identification] = match_tracklets_to_known_objects(
        [make_tracklet()], fields, CONFIG
    ).identifications

    assert identification.status is IdentificationStatus.UNKNOWN


def test_object_missing_from_one_frame_cannot_match() -> None:
    fields = make_fields(
        lambda minute: []
        if minute == 30
        else [ephemeris("48606", *mover_position(minute))]
    )

    [identification] = match_tracklets_to_known_objects(
        [make_tracklet()], fields, CONFIG
    ).identifications

    assert identification.status is IdentificationStatus.UNKNOWN


def test_two_objects_within_radius_are_ambiguous_with_best_first() -> None:
    fields = make_fields(
        lambda minute: [
            ephemeris("111", *offset(mover_position(minute), 1.5)),
            ephemeris("222", *offset(mover_position(minute), 0.3)),
        ]
    )

    [identification] = match_tracklets_to_known_objects(
        [make_tracklet()], fields, CONFIG
    ).identifications

    assert identification.status is IdentificationStatus.AMBIGUOUS
    assert identification.best_match.designation == "222"
    assert [match.designation for match in identification.candidate_matches] == [
        "222",
        "111",
    ]
    assert "2 known objects" in identification.status_reason


def test_large_ephemeris_uncertainty_is_ambiguous() -> None:
    fields = make_fields(
        lambda minute: [
            ephemeris("2016 CL29", *mover_position(minute), position_error=157301.5)
        ]
    )

    [identification] = match_tracklets_to_known_objects(
        [make_tracklet()], fields, CONFIG
    ).identifications

    assert identification.status is IdentificationStatus.AMBIGUOUS
    assert identification.best_match.designation == "2016 CL29"
    assert "position error" in identification.status_reason


def test_match_radius_comes_from_config() -> None:
    fields = make_fields(
        lambda minute: [ephemeris("48606", *offset(mover_position(minute), 1.5))]
    )
    tracklet = make_tracklet()

    tight = match_tracklets_to_known_objects(
        [tracklet], fields, IdentificationConfig(match_radius_arcsec=1.0)
    )
    loose = match_tracklets_to_known_objects(
        [tracklet], fields, IdentificationConfig(match_radius_arcsec=2.0)
    )

    assert tight.identifications[0].status is IdentificationStatus.UNKNOWN
    assert loose.identifications[0].status is IdentificationStatus.KNOWN


def test_rejected_tracklet_is_identified_and_keeps_its_fit_status() -> None:
    fields = make_fields(lambda minute: [ephemeris("48606", *mover_position(minute))])

    [identification] = match_tracklets_to_known_objects(
        [make_tracklet(status=TrackletStatus.REJECTED)], fields, CONFIG
    ).identifications

    assert identification.tracklet_status is TrackletStatus.REJECTED
    assert identification.status is IdentificationStatus.KNOWN


def test_missing_frame_field_is_an_error_not_unknown() -> None:
    fields = make_fields(lambda minute: [])
    del fields[102]

    with pytest.raises(ValueError, match="102"):
        match_tracklets_to_known_objects([make_tracklet()], fields, CONFIG)


def test_result_is_json_serializable() -> None:
    fields = make_fields(lambda minute: [ephemeris("48606", *mover_position(minute))])

    payload = json.loads(
        match_tracklets_to_known_objects(
            [make_tracklet()], fields, CONFIG
        ).model_dump_json()
    )

    assert payload["identifications"][0]["status"] == "known"
    assert payload["identifications"][0]["tracklet_status"] == "tracklet_built"
    assert payload["config"] == {"match_radius_arcsec": 2.0}
    assert len(payload["fields"]) == 3


@pytest.mark.parametrize("radius", [0.0, -1.0])
def test_config_rejects_non_positive_radius(radius: float) -> None:
    with pytest.raises(ValidationError):
        IdentificationConfig(match_radius_arcsec=radius)


def make_observations() -> list[Observation]:
    return [
        Observation(
            product_id=product_id,
            observed_at=START_TIME + timedelta(minutes=minute),
            field=535,
            filter_code="zr",
            ccd_id=11,
            quadrant_id=3,
            file_frac_day="20180411467847",
            exposure_seconds=30.0,
        )
        for minute, product_id in zip(MINUTES, PRODUCT_IDS)
    ]


def test_mid_exposure_epoch_is_utc_julian_day() -> None:
    [first, *_] = make_observations()

    # 2018-04-11 10:00:15 UTC
    assert mid_exposure_jd_utc(first) == pytest.approx(
        2458219.5 + (10 * 3600 + 15) / 86400, abs=1e-9
    )


def test_identify_tracklets_queries_each_frame_at_mid_exposure() -> None:
    observations = make_observations()
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        epoch = float(request.url.params["-ep"])
        minute = (epoch - mid_exposure_jd_utc(observations[0])) * 1440
        ra, dec = mover_position(round(minute))
        return httpx.Response(
            200,
            json=[
                {
                    "Num": 48606,
                    "Name": "1995 DH",
                    "RA (hms)": _hms(ra),
                    "DEC (dms)": _dms(dec),
                    "Class": "MB>Middle",
                    "VMag (mag)": 19.8,
                    "Err (arcsec)": 0.028,
                    "d (arcsec)": 10.0,
                    "dRA (arcsec/h)": 30.0,
                    "dDEC (arcsec/h)": 12.0,
                    "dg (ua)": 2.68,
                    "dh (ua)": 3.30,
                }
            ],
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = identify_tracklets(
            [make_tracklet()], observations, CONFIG, client=client
        )

    assert [float(request.url.params["-ep"]) for request in requests] == [
        pytest.approx(mid_exposure_jd_utc(observation), abs=1e-8)
        for observation in observations
    ]
    assert {request.url.params["-observer"] for request in requests} == {"I41"}
    cone_radius = float(requests[0].url.params["-rd"])
    assert 0 < cone_radius < 0.01
    assert result.identifications[0].status is IdentificationStatus.KNOWN
    assert result.identifications[0].best_match.designation == "48606"


def test_identify_tracklets_raises_on_skybot_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.skybot_service.time.sleep", lambda _: None)
    transport = httpx.MockTransport(lambda request: httpx.Response(503))

    with httpx.Client(transport=transport) as client:
        with pytest.raises(SkyBoTServiceError):
            identify_tracklets(
                [make_tracklet()], make_observations(), CONFIG, client=client
            )


def test_identify_tracklets_without_tracklets_makes_no_queries() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("SkyBoT must not be called")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = identify_tracklets([], make_observations(), CONFIG, client=client)

    assert result.identifications == []
    assert result.diagnostics.tracklet_count == 0


def _hms(ra_degrees: float) -> str:
    hours = ra_degrees / 15
    h = int(hours)
    m = int((hours - h) * 60)
    s = ((hours - h) * 60 - m) * 60
    return f"{h:02d} {m:02d} {s:.6f}"


def _dms(dec_degrees: float) -> str:
    sign = "-" if dec_degrees < 0 else "+"
    value = abs(dec_degrees)
    d = int(value)
    m = int((value - d) * 60)
    s = ((value - d) * 60 - m) * 60
    return f"{sign}{d:02d} {m:02d} {s:.5f}"
