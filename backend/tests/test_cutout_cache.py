import json
from datetime import datetime, timezone

import pytest

from app.models.observation import Observation
from app.services import cutout_cache
from app.services.cutout_cache import CutoutCache, cutout_key, default_cutout_cache


OBSERVATION = Observation(
    product_id=465423434215,
    observed_at=datetime(2018, 4, 11, 10, 9, 45, tzinfo=timezone.utc),
    field=535,
    filter_code="zr",
    ccd_id=11,
    quadrant_id=3,
    file_frac_day="20180411423368",
    exposure_seconds=30.0,
)
PID = OBSERVATION.product_id
REQUEST = (PID, 255.5, 12.3, 90.0)
PAYLOAD = b"SIMPLE  =                    T" + b"\0" * 50


def test_key_is_deterministic_and_covers_every_parameter() -> None:
    key = cutout_key(*REQUEST)

    assert key == cutout_key(PID, 255.5, 12.3, 90.0)
    assert key == cutout_key(PID, 255.50, 12.300, 90)  # same values
    assert len(key) == 64
    variants = [
        (PID + 1, 255.5, 12.3, 90.0),
        (PID, 255.5 + 1e-9, 12.3, 90.0),
        (PID, 255.5, 12.3 + 1e-9, 90.0),
        (PID, 255.5, 12.3, 91.0),
    ]
    assert len({key, *(cutout_key(*v) for v in variants)}) == len(variants) + 1


def test_key_includes_cache_version(monkeypatch) -> None:
    key = cutout_key(*REQUEST)
    monkeypatch.setattr(cutout_cache, "CUTOUT_CACHE_VERSION", 2)

    assert cutout_key(*REQUEST) != key


def test_put_then_get_round_trips(tmp_path) -> None:
    cache = CutoutCache(tmp_path / "cutouts")

    assert cache.get(*REQUEST) is None
    cache.put(OBSERVATION, *REQUEST[1:], PAYLOAD)
    cached = cache.get(*REQUEST)

    assert cached is not None
    assert cached.payload == PAYLOAD
    assert cached.observation == OBSERVATION
    # Two files per entry, no temp files left behind.
    assert sorted(p.suffix for p in (tmp_path / "cutouts").iterdir()) == [
        ".fits",
        ".json",
    ]


def entry_paths(cache: CutoutCache):
    key = cutout_key(*REQUEST)
    return cache.directory / f"{key}.fits", cache.directory / f"{key}.json"


@pytest.mark.parametrize(
    "corrupt",
    ["missing_fits", "missing_json", "bad_json", "not_fits", "wrong_key"],
)
def test_damaged_entry_is_a_miss(tmp_path, corrupt) -> None:
    cache = CutoutCache(tmp_path)
    cache.put(OBSERVATION, *REQUEST[1:], PAYLOAD)
    fits_path, meta_path = entry_paths(cache)

    if corrupt == "missing_fits":
        fits_path.unlink()
    elif corrupt == "missing_json":
        meta_path.unlink()
    elif corrupt == "bad_json":
        meta_path.write_text("{")
    elif corrupt == "not_fits":
        fits_path.write_bytes(b"<html>504 Gateway Timeout</html>")
    else:
        meta = json.loads(meta_path.read_text())
        meta["key"]["size_arcsec"] = "60.0"
        meta_path.write_text(json.dumps(meta))

    assert cache.get(*REQUEST) is None


def test_discard_removes_entry(tmp_path) -> None:
    cache = CutoutCache(tmp_path)
    cache.put(OBSERVATION, *REQUEST[1:], PAYLOAD)

    cache.discard(*REQUEST)

    assert cache.get(*REQUEST) is None
    assert list(tmp_path.iterdir()) == []


def test_unwritable_cache_does_not_fail(tmp_path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("")
    cache = CutoutCache(blocker / "cutouts")  # parent is a file

    cache.put(OBSERVATION, *REQUEST[1:], PAYLOAD)

    assert cache.get(*REQUEST) is None


def test_cache_directory_from_environment(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv(cutout_cache.CACHE_DIR_ENV, str(tmp_path))
    assert default_cutout_cache().directory == tmp_path

    monkeypatch.delenv(cutout_cache.CACHE_DIR_ENV)
    assert default_cutout_cache().directory == cutout_cache.DEFAULT_CACHE_DIR
