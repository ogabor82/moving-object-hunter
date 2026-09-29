import httpx
import pytest

from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG
from app.services import pipeline_service
from app.services.identification_service import match_tracklets_to_known_objects
from app.services.pipeline_service import (
    build_tracklets_from_frames,
    build_tracklets_from_observations,
)
from app.services.ztf_service import (
    InsufficientFramesError,
    ZTFServiceError,
    fetch_observations,
)
from app.validation import end_to_end
from app.validation.end_to_end import (
    CanonicalField,
    load_canonical_fields,
    render_markdown,
    run_end_to_end,
)
from app.validation.models import ValidationTarget
from tests.test_validation_tooling import (
    PRODUCT_IDS,
    STAR_A,
    STAR_B,
    TARGET_START,
    ephemeris,
    frames_with,
    mover,
    skybot_fields,
)


# --- ztf_service.fetch_observations ------------------------------------------

HEADER = "obsdate,obsjd,field,filtercode,ccdid,qid,pid,filefracday,imgtypecode,exptime"


def row(pid: int, time: str) -> str:
    return (
        f"2018-04-11 {time}+00,2458219.9,535,zr,11,3,{pid},20180411467847,o,30.000"
    )


def client_for(body: str, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["WHERE"].startswith("pid IN (")
        return httpx.Response(status, text=body)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_observations_returns_time_ordered_observations() -> None:
    body = "\n".join([HEADER, row(2, "11:13:43"), row(1, "10:09:45")])

    with client_for(body) as client:
        observations = fetch_observations([1, 2], client)

    assert [o.product_id for o in observations] == [1, 2]
    assert observations[0].exposure_seconds == 30.0


def test_fetch_observations_reports_unknown_product_ids() -> None:
    body = "\n".join([HEADER, row(1, "10:09:45")])

    with client_for(body) as client:
        with pytest.raises(ZTFServiceError, match=r"\[2\]"):
            fetch_observations([1, 2], client)


def test_fetch_observations_handles_http_error() -> None:
    with client_for("down", status=503) as client:
        with pytest.raises(ZTFServiceError, match="HTTP 503"):
            fetch_observations([1], client)


def test_fetch_observations_requires_ids() -> None:
    with pytest.raises(ValueError):
        fetch_observations([])


# --- pipeline_service --------------------------------------------------------


def test_pipeline_builds_tracklet_from_frames() -> None:
    frames = frames_with(lambda minute: [STAR_A, STAR_B, mover(TARGET_START, minute)])

    result = build_tracklets_from_frames(frames, EXPERIMENTAL_DEFAULT_CONFIG)

    assert [c.candidate_count for c in result.candidate_frames] == [1, 1, 1]
    assert len(result.build.tracklets) == 1
    assert result.observations == [frame.observation for frame in frames]


def test_pipeline_requires_three_observations() -> None:
    frames = frames_with(lambda minute: [])

    with pytest.raises(InsufficientFramesError):
        build_tracklets_from_observations(
            [frame.observation for frame in frames[:2]], EXPERIMENTAL_DEFAULT_CONFIG
        )


def test_pipeline_config_stage_configs() -> None:
    config = EXPERIMENTAL_DEFAULT_CONFIG

    assert config.stationary_matching().stationary_tolerance_arcsec == 1.5
    assert config.tracklet_build().max_rate_arcsec_per_min == 1.0
    assert config.tracklet_build().min_detections == 3
    assert config.identification().match_radius_arcsec == 2.0


# --- end_to_end --------------------------------------------------------------


def canonical_field(designation: str = "100") -> CanonicalField:
    return CanonicalField(
        field_id="F",
        product_ids=PRODUCT_IDS,
        targets=[
            ValidationTarget(
                field_id="F",
                designation=designation,
                name=f"Object {designation}",
                object_class="MB>Middle",
                role="primary",
                v_magnitude=19.0,
                position_error_arcsec=0.1,
                predicted_rate_arcsec_per_min=0.49,
                predicted_position_angle_deg=90.0,
                predicted_positions=[
                    mover(TARGET_START, minute) for minute in (0, 30, 60)
                ],
            )
        ],
    )


def run_with(monkeypatch, known_designation: str | None):
    frames = frames_with(lambda minute: [STAR_A, mover(TARGET_START, minute)])
    monkeypatch.setattr(
        end_to_end,
        "fetch_observations",
        lambda ids, client=None: [frame.observation for frame in frames],
    )
    monkeypatch.setattr(
        pipeline_service, "load_frame_sources", lambda observations, client: frames
    )
    objects = (
        (lambda minute: [ephemeris(known_designation, mover(TARGET_START, minute))])
        if known_designation
        else (lambda minute: [])
    )
    fields = dict(zip(PRODUCT_IDS, skybot_fields(objects)))
    monkeypatch.setattr(
        end_to_end,
        "identify_tracklets",
        lambda tracklets, observations, config, client=None: (
            match_tracklets_to_known_objects(tracklets, fields, config)
        ),
    )
    return run_end_to_end([canonical_field()])


def test_end_to_end_passes_when_target_is_identified_correctly(monkeypatch) -> None:
    report = run_with(monkeypatch, known_designation="100")

    [target] = report.fields[0].targets
    assert target.correctly_identified
    assert not target.misidentified
    assert report.passed
    assert "**Verdict: PASS**" in render_markdown(report)


def test_end_to_end_fails_on_misidentification(monkeypatch) -> None:
    report = run_with(monkeypatch, known_designation="999")

    [target] = report.fields[0].targets
    assert target.misidentified
    assert not report.passed


def test_end_to_end_fails_when_nothing_is_identified(monkeypatch) -> None:
    report = run_with(monkeypatch, known_designation=None)

    [target] = report.fields[0].targets
    assert len(target.linked_tracklets) == 1
    assert not target.correctly_identified
    assert not report.passed
    assert "linked, not known" in render_markdown(report)


def test_load_canonical_fields_uses_frozen_primary_targets() -> None:
    fields = load_canonical_fields()

    assert sum(len(field.targets) for field in fields) == 21
    assert {t.role for field in fields for t in field.targets} == {"primary"}
    assert all(len(field.product_ids) == 3 for field in fields)
