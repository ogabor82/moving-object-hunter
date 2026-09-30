"""Blink-comparator presets from the frozen AS-022 validation data.

One preset per canonical primary target and POC control: the frozen frame
sequence (product ids) and a cutout centred on the mean of the target's
frozen SkyBoT predictions, large enough to contain its whole track. The
same report holds the IRSA metadata of every frozen frame, so those frames
need no metadata lookup (`load_frozen_observations`).
"""

import math
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType

from pydantic import BaseModel

from app.models.observation import Observation
from app.services.astrometry import angular_distance_arcsec
from app.validation.runner import ValidationReport


AS022_REPORT = Path(__file__).parents[2] / "validation" / "results" / (
    "as022_validation.json"
)
PRESET_ROLES = ("control", "primary")
# Margin around the track and the smallest cutout, in arcsec.
TRACK_MARGIN_ARCSEC = 30.0
MIN_SIZE_ARCSEC = 60.0


class BlinkPreset(BaseModel):
    preset_id: str
    label: str
    designation: str
    name: str
    role: str
    v_magnitude: float
    predicted_rate_arcsec_per_min: float
    field_id: str
    product_ids: list[int]
    center_ra: float
    center_dec: float
    size_arcsec: float


def presets_from_report(report: ValidationReport) -> list[BlinkPreset]:
    presets = []
    for snapshot in report.snapshots:
        product_ids = [o.product_id for o in snapshot.observations]
        for role in PRESET_ROLES:
            for target in snapshot.targets:
                if target.role != role:
                    continue
                positions = target.predicted_positions
                center_ra, center_dec = _mean_position(positions)
                extent = max(
                    angular_distance_arcsec(center_ra, center_dec, ra, dec)
                    for ra, dec in positions
                )
                size = max(
                    MIN_SIZE_ARCSEC,
                    10.0 * math.ceil((2 * extent + 2 * TRACK_MARGIN_ARCSEC) / 10.0),
                )
                presets.append(
                    BlinkPreset(
                        preset_id=f"{snapshot.field.field_id}:{target.designation}",
                        label=(
                            f"{target.designation} {target.name}"
                            if target.name != target.designation
                            else target.designation
                        ),
                        designation=target.designation,
                        name=target.name,
                        role=role,
                        v_magnitude=target.v_magnitude,
                        predicted_rate_arcsec_per_min=(
                            target.predicted_rate_arcsec_per_min
                        ),
                        field_id=snapshot.field.field_id,
                        product_ids=product_ids,
                        center_ra=center_ra,
                        center_dec=center_dec,
                        size_arcsec=size,
                    )
                )
    return presets


@lru_cache(maxsize=1)
def _load_report(report_path: Path) -> ValidationReport:
    return ValidationReport.model_validate_json(report_path.read_text())


@lru_cache(maxsize=1)
def load_blink_presets(report_path: Path = AS022_REPORT) -> tuple[BlinkPreset, ...]:
    return tuple(presets_from_report(_load_report(report_path)))


@lru_cache(maxsize=1)
def load_frozen_observations(
    report_path: Path = AS022_REPORT,
) -> Mapping[int, Observation]:
    """IRSA metadata of the frozen validation frames, by product id."""
    return MappingProxyType(
        {
            observation.product_id: observation
            for snapshot in _load_report(report_path).snapshots
            for observation in snapshot.observations
        }
    )


def _mean_position(positions: list[tuple[float, float]]) -> tuple[float, float]:
    """Mean of positions via unit vectors (safe across RA = 0)."""
    x = y = z = 0.0
    for ra, dec in positions:
        ra_rad, dec_rad = math.radians(ra), math.radians(dec)
        x += math.cos(dec_rad) * math.cos(ra_rad)
        y += math.cos(dec_rad) * math.sin(ra_rad)
        z += math.sin(dec_rad)
    ra = math.degrees(math.atan2(y, x)) % 360.0
    dec = math.degrees(math.atan2(z, math.hypot(x, y)))
    return ra, dec
