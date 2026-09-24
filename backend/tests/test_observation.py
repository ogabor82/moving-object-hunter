import json
from datetime import datetime, timezone

import pytest

from app.models.observation import Observation
from app.services.ztf_service import (
    ZTFMetadataMappingError,
    map_ztf_metadata_to_observation,
)


RAW_METADATA_ROW = {
    "obsdate": "2018-04-11 11:13:43+00",
    "obsjd": "2458219.967858800",
    "field": "535",
    "filtercode": "zr",
    "ccdid": "11",
    "qid": "3",
    "pid": "465467854215",
    "filefracday": "20180411467847",
    "imgtypecode": "o",
}


def test_valid_ztf_row_maps_to_observation() -> None:
    observation = map_ztf_metadata_to_observation(RAW_METADATA_ROW)

    assert observation == Observation(
        product_id=465467854215,
        observed_at=datetime(2018, 4, 11, 11, 13, 43, tzinfo=timezone.utc),
        field=535,
        filter_code="zr",
        ccd_id=11,
        quadrant_id=3,
        file_frac_day="20180411467847",
    )


def test_ztf_mapping_converts_raw_value_types() -> None:
    observation = map_ztf_metadata_to_observation(RAW_METADATA_ROW)

    assert isinstance(observation.product_id, int)
    assert isinstance(observation.observed_at, datetime)
    assert isinstance(observation.field, int)
    assert isinstance(observation.ccd_id, int)
    assert isinstance(observation.quadrant_id, int)
    assert isinstance(observation.file_frac_day, str)


def test_ztf_mapping_rejects_missing_required_field() -> None:
    raw = dict(RAW_METADATA_ROW)
    raw.pop("pid")

    with pytest.raises(ZTFMetadataMappingError, match="pid"):
        map_ztf_metadata_to_observation(raw)


def test_observation_is_json_serializable() -> None:
    observation = map_ztf_metadata_to_observation(RAW_METADATA_ROW)

    payload = json.loads(observation.model_dump_json())

    assert payload == {
        "product_id": 465467854215,
        "observed_at": "2018-04-11T11:13:43Z",
        "field": 535,
        "filter_code": "zr",
        "ccd_id": 11,
        "quadrant_id": 3,
        "file_frac_day": "20180411467847",
    }
