import json
import struct
import zlib
from datetime import datetime, timedelta, timezone

import numpy
import pytest

from app.models.identification import IdentificationStatus
from app.models.tracklet import TrackletStatus
from app.services.quality_service import extract_quality_features
from app.validation import masked
from app.validation.masked import (
    HaloStar,
    MaskEvidenceReport,
    TrackletContext,
    VisualReview,
    allocate,
    bits_of,
    draw_sample,
    halo_geometry,
    render_markdown,
    sample_key,
    stratum_of,
    write_png,
)
from app.validation.models import FieldSnapshot, FrameMetadata
from app.validation.presets import AS022_REPORT
from tests.test_quality_features import detection, three, tracklet


def test_bits_of() -> None:
    assert bits_of(0) == []
    assert bits_of(4353) == [0, 8, 12]
    assert bits_of(4096) == [12]


def features(**per_index):
    return extract_quality_features(three(**per_index))


@pytest.mark.parametrize(
    ("status", "masks", "built", "expected"),
    [
        (IdentificationStatus.KNOWN, [0, 0, 0], True, "known"),
        (IdentificationStatus.KNOWN, [4096, 0, 0], True, "known"),
        (IdentificationStatus.UNKNOWN, [4096, 4096, 4096], True, "masked_unknown"),
        (IdentificationStatus.UNKNOWN, [0, 256, 0], True, "partially_masked_unknown"),
        (IdentificationStatus.UNKNOWN, [0, 0, 0], True, "unmasked_unknown"),
        (IdentificationStatus.AMBIGUOUS, [0, 0, 0], True, "ambiguous"),
        (IdentificationStatus.UNKNOWN, [4096, 4096, 4096], False, "rejected"),
    ],
)
def test_stratum(status, masks, built, expected) -> None:
    t = tracklet(
        *(detection(i, mask_bits=m) for i, m in enumerate(masks)),
        status=TrackletStatus.TRACKLET_BUILT if built else TrackletStatus.REJECTED,
    )

    assert stratum_of(status, extract_quality_features(t)) == expected


def test_edge_only_detection_is_not_masked() -> None:
    f = features(on_image_edge=[True, True, True])

    assert stratum_of(IdentificationStatus.UNKNOWN, f) == "unmasked_unknown"


def test_allocate_gives_every_pattern_one_then_proportional() -> None:
    assert allocate({4097: 30, 4353: 35, 256: 3}, 8) == {256: 1, 4097: 3, 4353: 4}
    assert sum(allocate({1: 100, 2: 50, 3: 1}, 8).values()) == 8
    assert allocate({1: 2}, 8) == {1: 2}  # never more than available


def test_allocate_with_fewer_slots_than_patterns() -> None:
    assert allocate({1: 5, 2: 9, 3: 1}, 2) == {1: 1, 2: 1, 3: 0}


def context(tracklet_id: str, stratum: str, pattern: int = 0) -> TrackletContext:
    return TrackletContext(
        field_id="F",
        tracklet_id=tracklet_id,
        identification_status=IdentificationStatus.UNKNOWN,
        known_designation=None,
        stratum=stratum,
        mask_pattern=pattern,
        inside_halo=False,
        all_detections_halo_bit=False,
        any_detection_track_bit=False,
        shared_detections=0,
        features=features(),
        detections=[],
    )


def population():
    items = [context(f"k{i}", "known") for i in range(3)]
    items += [context(f"m{i}", "masked_unknown", 4096) for i in range(40)]
    items += [context(f"s{i}", "masked_unknown", 256) for i in range(5)]
    items += [context(f"p{i}", "partially_masked_unknown", 256) for i in range(9)]
    items += [context(f"u{i}", "unmasked_unknown") for i in range(20)]
    items += [context(f"r{i}", "rejected") for i in range(50)]
    return items


def test_sample_is_deterministic_stratified_and_order_independent() -> None:
    items = population()

    first = [c.tracklet_id for c in draw_sample(items)]
    shuffled = [c.tracklet_id for c in draw_sample(list(reversed(items)))]

    assert first == shuffled
    strata = [next(c for c in items if c.tracklet_id == t).stratum for t in first]
    assert strata.count("known") == 3  # every KNOWN
    assert strata.count("masked_unknown") == masked.MASKED_SAMPLE
    assert strata.count("partially_masked_unknown") == masked.PARTIAL_SAMPLE
    assert strata.count("unmasked_unknown") == masked.UNMASKED_SAMPLE
    assert "rejected" not in strata
    assert any(t.startswith("s") for t in first)  # the rare pattern is present


def test_sample_order_follows_the_hash_not_the_pipeline() -> None:
    items = [context(f"u{i}", "unmasked_unknown") for i in range(20)]

    picked = [c.tracklet_id for c in draw_sample(items)]

    expected = sorted((c.tracklet_id for c in items), key=lambda t: sample_key("F", t))
    assert picked == expected[: masked.UNMASKED_SAMPLE]


def test_halo_geometry_of_a_disk_inside_a_square() -> None:
    star = HaloStar(tycho_id="T", ra=120.0, dec=0.0, vt_mag=5.0)
    half = 0.25  # deg
    corners = [
        (120 - half, -half),
        (120 + half, -half),
        (120 + half, half),
        (120 - half, half),
    ]
    snapshot = FieldSnapshot.model_construct(
        frame_metadata=[
            FrameMetadata(
                product_id=1,
                center_ra=120.0,
                center_dec=0.0,
                corners=corners,
                maglimit=20.0,
                seeing_arcsec=2.0,
                airmass=1.0,
            )
        ]
    )
    radius = 600.0  # arcsec

    area, fraction = halo_geometry(snapshot, star, radius)

    assert area == pytest.approx(30.0**2, rel=0.01)  # 30' x 30'
    # Same result whatever order IRSA lists the corners in.
    shuffled = snapshot.model_copy(
        update={
            "frame_metadata": [
                snapshot.frame_metadata[0].model_copy(
                    update={"corners": [corners[0], corners[2], corners[1], corners[3]]}
                )
            ]
        }
    )
    assert halo_geometry(shuffled, star, radius) == (area, fraction)
    assert fraction == pytest.approx(3.14159 * 10.0**2 / 900.0, rel=0.02)


def test_png_writer_produces_a_valid_rgb_png(tmp_path) -> None:
    rgb = numpy.zeros((3, 4, 3), dtype=numpy.uint8)
    rgb[1, 2] = (255, 181, 71)
    path = tmp_path / "x.png"

    write_png(path, rgb)

    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    width, height, depth, color = struct.unpack(">IIBB", data[16:26])
    assert (width, height, depth, color) == (4, 3, 8, 2)
    idat = data.index(b"IDAT")
    length = struct.unpack(">I", data[idat - 4 : idat])[0]
    raw = zlib.decompress(data[idat + 4 : idat + 4 + length])
    rows = [raw[i * 13 + 1 : (i + 1) * 13] for i in range(3)]
    assert rows[1][6:9] == bytes((255, 181, 71))


# Committed evidence (validation/results/as032): consistency checks.

AS032 = AS022_REPORT.parent / "as032"


def committed() -> MaskEvidenceReport:
    return MaskEvidenceReport.model_validate_json(
        (AS032 / "as032_masked_tracklets.json").read_text()
    )


def test_every_sampled_strip_exists_and_is_reviewed() -> None:
    report = committed()
    reviews = [
        VisualReview.model_validate(r)
        for r in json.loads((AS032 / "visual_review.json").read_text())
    ]
    reviewed = {(r.field_id, r.tracklet_id) for r in reviews}

    for item in report.sample:
        assert (AS032 / item.image).is_file()
        assert (item.context.field_id, item.context.tracklet_id) in reviewed
    assert len(reviewed) == len(report.sample)
    assert "not reviewed" not in render_markdown(report, reviews)


def test_committed_sample_matches_the_sampling_rule() -> None:
    report = committed()
    for field in {i.context.field_id for i in report.sample}:
        sampled = [i.context for i in report.sample if i.context.field_id == field]
        assert [c.tracklet_id for c in draw_sample(sampled)] == [
            c.tracklet_id for c in sampled
        ]


def test_committed_mask_semantics_cite_the_primary_source() -> None:
    report = committed()

    assert "Explanatory Supplement" in report.source
    assert report.mask_bits[0] == "AIRCRAFT/SATELLITE TRACK"
    assert report.mask_bits[8] == "SATURATED"
    assert report.mask_bits[12] == "HALO FROM BRIGHT SOURCE"
