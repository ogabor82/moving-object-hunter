"""Local disk cache of ZTF science-image cutouts (regenerable, not in git).

The cache stores the raw FITS payload returned by the IRSA IBE cutout
service, never the rendered display image: a hit is rendered by the same
`render_cutout` call as a miss, so both give identical display output, and
changing the display transform never serves stale images.

Key: SHA-256 of the product id (which fixes the science image), the cutout
centre and size as sent to IRSA, and CUTOUT_CACHE_VERSION (bump it when the
IBE request changes, e.g. its parameters). Each entry is `<key>.fits` plus
`<key>.json` holding the key fields and the frame's Observation, so a hit
needs no IRSA metadata lookup. Entries are written atomically (temp file +
rename, FITS before JSON); an unreadable or inconsistent entry is a miss.
"""

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from app.models.observation import Observation


CUTOUT_CACHE_VERSION = 1
CACHE_DIR_ENV = "MOH_CUTOUT_CACHE_DIR"
DEFAULT_CACHE_DIR = Path(__file__).parents[2] / ".cache" / "cutouts"
FITS_MAGIC = b"SIMPLE  ="


@dataclass(frozen=True)
class CachedCutout:
    observation: Observation
    payload: bytes


def cutout_key_fields(
    product_id: int, ra: float, dec: float, size_arcsec: float
) -> dict[str, object]:
    # repr() of a float round-trips exactly: equal requests, equal keys.
    return {
        "version": CUTOUT_CACHE_VERSION,
        "product_id": int(product_id),
        "ra": repr(float(ra)),
        "dec": repr(float(dec)),
        "size_arcsec": repr(float(size_arcsec)),
    }


def cutout_key(product_id: int, ra: float, dec: float, size_arcsec: float) -> str:
    fields = cutout_key_fields(product_id, ra, dec, size_arcsec)
    encoded = json.dumps(fields, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


class CutoutCache:
    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)

    def _paths(self, key: str) -> tuple[Path, Path]:
        return self.directory / f"{key}.fits", self.directory / f"{key}.json"

    def get(
        self, product_id: int, ra: float, dec: float, size_arcsec: float
    ) -> CachedCutout | None:
        key = cutout_key(product_id, ra, dec, size_arcsec)
        fits_path, meta_path = self._paths(key)
        try:
            meta = json.loads(meta_path.read_text())
            payload = fits_path.read_bytes()
            observation = Observation.model_validate(meta["observation"])
        except (OSError, ValueError, KeyError, TypeError, ValidationError):
            return None
        if (
            meta.get("key") != cutout_key_fields(product_id, ra, dec, size_arcsec)
            or observation.product_id != product_id
            or not payload.startswith(FITS_MAGIC)
        ):
            return None
        return CachedCutout(observation=observation, payload=payload)

    def put(
        self,
        observation: Observation,
        ra: float,
        dec: float,
        size_arcsec: float,
        payload: bytes,
    ) -> None:
        """Store one cutout; failures to write only lose the cache entry."""
        product_id = observation.product_id
        key = cutout_key(product_id, ra, dec, size_arcsec)
        fits_path, meta_path = self._paths(key)
        meta = {
            "key": cutout_key_fields(product_id, ra, dec, size_arcsec),
            "observation": observation.model_dump(mode="json"),
        }
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            _write_atomic(fits_path, payload)
            _write_atomic(meta_path, json.dumps(meta, indent=1).encode())
        except OSError:
            pass

    def discard(
        self, product_id: int, ra: float, dec: float, size_arcsec: float
    ) -> None:
        for path in self._paths(cutout_key(product_id, ra, dec, size_arcsec)):
            path.unlink(missing_ok=True)


def _write_atomic(path: Path, data: bytes) -> None:
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(temp, path)
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise


def default_cutout_cache() -> CutoutCache:
    return CutoutCache(Path(os.getenv(CACHE_DIR_ENV) or DEFAULT_CACHE_DIR))
