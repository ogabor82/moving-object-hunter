import json
import math

import pytest
from pydantic import ValidationError

from app.models.source_detection import SourceDetection


VALID_FIELDS = {
    "source_id": "465467854215-0",
    "observation_product_id": 465467854215,
    "ra": 255.7590124,
    "dec": 12.7174256,
    "x": 898.747,
    "y": 1.257,
    "magnitude": 20.63,
    "magnitude_error": 0.324,
    "snr": 3.35,
    "on_image_edge": False,
    "mask_bits": 0,
}
ZTF_COLUMN_NAMES = {
    "sourceid",
    "xpos",
    "ypos",
    "flux",
    "sigflux",
    "mag",
    "sigmag",
    "chi",
    "sharp",
    "flags",
    "magzp",
    "pid",
    "field",
    "ccdid",
    "qid",
    "filefracday",
}


def test_source_detection_is_json_serializable() -> None:
    detection = SourceDetection(**VALID_FIELDS)

    payload = json.loads(detection.model_dump_json())

    assert payload == VALID_FIELDS
    assert SourceDetection.model_validate(payload) == detection


def test_source_detection_exposes_no_ztf_specific_fields() -> None:
    field_names = {name.lower() for name in SourceDetection.model_fields}

    assert field_names.isdisjoint(ZTF_COLUMN_NAMES)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ra", 360.0),
        ("ra", -0.1),
        ("dec", 90.5),
        ("dec", -91.0),
        ("magnitude", math.nan),
        ("x", math.inf),
        ("snr", -1.0),
        ("magnitude_error", -0.1),
        ("mask_bits", -1),
        ("source_id", ""),
    ],
)
def test_source_detection_rejects_invalid_values(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        SourceDetection(**{**VALID_FIELDS, field: value})
