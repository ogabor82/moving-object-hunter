import json

import httpx
import pytest

from app.services.skybot_service import (
    SkyBoTServiceError,
    normalize_skybot_rows,
    query_known_objects,
)
from tests.test_skybot_query import QUERY, SKYBOT_ROWS


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.skybot_service.time.sleep", lambda _: None)


def test_numbered_object_is_normalized() -> None:
    [numbered, _], rejected = normalize_skybot_rows(SKYBOT_ROWS)

    assert rejected == []
    assert numbered.designation == "285862"
    assert numbered.number == 285862
    assert numbered.name == "2001 HM48"
    assert numbered.object_class == "MB>Outer"
    # 17h01m47.8476s, +12d08m48.528s
    assert numbered.predicted_ra == pytest.approx(
        (17 + 1 / 60 + 47.8476 / 3600) * 15, abs=1e-9
    )
    assert numbered.predicted_dec == pytest.approx(
        12 + 8 / 60 + 48.528 / 3600, abs=1e-9
    )
    assert numbered.v_magnitude == 20.0
    assert numbered.position_error_arcsec == 0.059
    assert numbered.distance_from_field_center_arcsec == 667.523
    assert numbered.motion_ra_cos_dec_arcsec_per_hour == 6.0568
    assert numbered.motion_dec_arcsec_per_hour == 33.7814
    assert numbered.observer_distance_au == pytest.approx(1.89450407965)
    assert numbered.heliocentric_distance_au == pytest.approx(2.5576201268)


def test_unnumbered_object_uses_name_as_designation() -> None:
    [_, unnumbered], _ = normalize_skybot_rows(SKYBOT_ROWS)

    assert unnumbered.number is None
    assert unnumbered.designation == "2018 LN15"
    assert unnumbered.name == "2018 LN15"


@pytest.mark.parametrize(
    ("dec_text", "expected"),
    [("-00 05 3.100", -(5 / 60 + 3.1 / 3600)), ("+89 59 59.000", 89.99972222)],
)
def test_signed_declinations_are_parsed(dec_text: str, expected: float) -> None:
    row = {**SKYBOT_ROWS[0], "DEC (dms)": dec_text}

    [ephemeris], _ = normalize_skybot_rows([row])

    assert ephemeris.predicted_dec == pytest.approx(expected, abs=1e-7)


def test_right_ascension_near_24h_stays_in_range() -> None:
    row = {**SKYBOT_ROWS[0], "RA (hms)": "23 59 59.9999"}

    [ephemeris], _ = normalize_skybot_rows([row])

    assert 359.99 < ephemeris.predicted_ra < 360.0


def test_missing_optional_values_become_none() -> None:
    row = {**SKYBOT_ROWS[1], "VMag (mag)": None, "Num": "-"}
    del row["dg (ua)"]

    [ephemeris], rejected = normalize_skybot_rows([row])

    assert rejected == []
    assert ephemeris.v_magnitude is None
    assert ephemeris.observer_distance_au is None
    assert ephemeris.number is None


def test_malformed_rows_are_rejected_and_valid_rows_kept() -> None:
    missing_ra = {k: v for k, v in SKYBOT_ROWS[0].items() if k != "RA (hms)"}
    bad_dec = {**SKYBOT_ROWS[0], "DEC (dms)": "not an angle"}
    negative_error = {**SKYBOT_ROWS[0], "Err (arcsec)": -1.0}

    objects, rejected = normalize_skybot_rows(
        [missing_ra, SKYBOT_ROWS[1], bad_dec, negative_error]
    )

    assert [ephemeris.name for ephemeris in objects] == ["2018 LN15"]
    assert [row.row_index for row in rejected] == [0, 2, 3]
    assert rejected[2].reason.startswith("position_error_arcsec")


def test_query_known_objects_wraps_field_metadata_and_serializes() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=SKYBOT_ROWS)
    )

    with httpx.Client(transport=transport) as client:
        field = query_known_objects(**QUERY, client=client)

    assert field.epoch_jd_utc == QUERY["epoch_jd_utc"]
    assert field.observer == "I41"
    assert field.field_radius_degrees == 0.65
    assert [ephemeris.designation for ephemeris in field.objects] == [
        "285862",
        "2018 LN15",
    ]
    payload = json.loads(field.model_dump_json())
    assert payload["objects"][0]["position_error_arcsec"] == 0.059


def test_query_known_objects_distinguishes_empty_field_from_failure() -> None:
    empty = httpx.MockTransport(lambda request: httpx.Response(204))
    failing = httpx.MockTransport(lambda request: httpx.Response(503))

    with httpx.Client(transport=empty) as client:
        assert query_known_objects(**QUERY, client=client).objects == []
    with httpx.Client(transport=failing) as client:
        with pytest.raises(SkyBoTServiceError):
            query_known_objects(**QUERY, client=client)
