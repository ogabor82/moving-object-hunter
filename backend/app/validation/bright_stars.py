"""AS-033: bright-star proximity of tracklets on several ZTF fields.

Research/evidence only — no filter, exclusion radius, score, rank,
threshold or rejection is derived here.

Bright-star catalog: Tycho-2 (Høg et al. 2000; VizieR I/259/tyc2), the
catalog the ZTF pipeline itself uses for halo masking (ZSDS Explanatory
Supplement §6.5 step 16, "V ≤ 6.5").
- Position: RAmdeg/DEmdeg (ICRS, mean position at epoch J2000); when
  absent (no proper motion in Tycho-2), RA(ICRS)/DE(ICRS) at the Tycho
  observation epoch (~J1991.25). Proper motion over 1991–2020 is at most a
  few arcsec for these stars and is ignored.
- Magnitude: Johnson V estimated as V = VT − 0.090 (BT − VT) (Tycho-2
  guide, ESA 1997 vol. 1 §1.3); V = VT when BT is missing; a star
  without VT has no magnitude and is never "bright".
- "Bright star" = V ≤ 6.5, the ZSDS halo-masking criterion (not tuned).

Proximity: the angular separation (astropy great-circle distance, ICRS)
between a tracklet's mean detection position and the nearest bright star
within the field's catalog cone; null when the cone has no bright star.

Steps (both reproducible; see validation/results/as033/):
    python -m app.validation.bright_stars select \\
        --out validation/results/as033/as033_fields.json
    python -m app.validation.bright_stars evidence \\
        --fields validation/results/as033/as033_fields.json \\
        --out-dir validation/results/as033
"""

import argparse
import csv
import hashlib
import math
import statistics
from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import astropy.units as u
import httpx
import numpy
from astropy.coordinates import GeocentricTrueEcliptic, SkyCoord
from pydantic import BaseModel

from app.models.identification import IdentificationStatus
from app.models.known_object import KnownObjectField
from app.models.observation import Observation
from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG
from app.models.tracklet import TrackletStatus
from app.services.astrometry import angular_distance_arcsec
from app.services.ztf_service import fetch_ztf_metadata
from app.validation.data import CatalogFrames, load_catalog_frames, load_field_data
from app.validation.masked import (
    _mean,
    render_strip,
    sample_key,
    strip_geometry,
    write_png,
)
from app.validation.models import FieldSnapshot, FrameMetadata, ValidationField
from app.validation.presets import AS022_REPORT
from app.validation.quality import field_records
from app.validation.runner import ValidationReport


VIZIER_URL = "https://vizier.cds.unistra.fr/viz-bin/asu-tsv"
TYCHO_COLUMNS = "TYC1,TYC2,TYC3,RAmdeg,DEmdeg,RA(ICRS),DE(ICRS),BTmag,VTmag"
# A V <= 6.5 star has VT <= 6.5 + 0.09 * (BT - VT) < 7.0 for BT - VT < 5.
QUERY_MAX_VT = 7.0
BRIGHT_V_MAX = 6.5
REFERENCE_FIELDS = ("B-2019-01-25-565-c13-q3", "D-2019-06-02-281-c16-q3")

# Pre-registered field selection (fixed before any tracklet was built).
SELECTION_SALT = "AS-033"
SELECTION_MAX_ECLIPTIC_LATITUDE = 10.0  # deg, asteroid-rich band like AS-022
SELECTION_MIN_DEC = -25.0  # deg, ZTF (Palomar) coverage
SELECTION_START_JD = 2458194.5  # 2018-03-17, ZTF survey start
SELECTION_END_JD = 2459215.5  # 2021-01-01
SELECTION_FIELDS = 4
SELECTION_MAX_STARS_TRIED = 40
SELECTION_RULE = (
    "Tycho-2 stars with V <= 6.5, Dec >= -25 deg, |ecliptic latitude| <= 10 "
    "deg, ordered by SHA-256('AS-033:<Tycho id>'). For each star in turn, "
    "the IRSA ZTF science metadata covering the star's position between "
    "2018-03-17 and 2021-01-01 is grouped by (field, CCD, quadrant, UTC "
    "date); the earliest group with >= 3 exposures is taken, and its first, "
    "middle ((n-1)//2) and last exposure form the sequence (the AS-022 "
    "rule). Stars without such a group are skipped and logged. The first "
    "4 stars that yield a sequence are used. No pipeline output, source "
    "count or UNKNOWN count is looked at."
)

# Radial bins [arcsec]: regular 2' annuli out to 10', a 10'-15' ring and
# everything beyond 15' as the far control. Fixed before any evidence run;
# not derived from the AS-032 halo measurement.
BIN_EDGES = (0.0, 120.0, 240.0, 360.0, 480.0, 600.0, 900.0, math.inf)
CONTROL_BIN = len(BIN_EDGES) - 2
AREA_GRID = 500
# Visual sample per new field: UNKNOWN built tracklets within 10' of a
# bright star, UNKNOWN built beyond 15', and KNOWN built (hash order).
VISUAL_NEAR = 6
VISUAL_FAR = 2
VISUAL_KNOWN = 2
NEAR_EDGE = 600.0


class TychoStar(BaseModel):
    tycho_id: str
    ra: float
    dec: float
    vt_mag: float | None
    bt_mag: float | None
    v_mag: float | None
    position_source: str  # "mean J2000" | "observed ~J1991.25"


def johnson_v(vt: float | None, bt: float | None) -> float | None:
    if vt is None:
        return None
    if bt is None:
        return vt
    return vt - 0.090 * (bt - vt)


def parse_tycho_tsv(text: str) -> list[TychoStar]:
    """Parse a VizieR asu-tsv Tycho-2 result with TYCHO_COLUMNS."""
    lines = [line for line in text.splitlines() if line and not line.startswith("#")]
    if not lines:
        return []
    header = lines[0].split("\t")
    stars = []
    for line in lines[3:]:  # header, units, dashes
        row = dict(zip(header, line.split("\t")))

        def number(key):
            value = (row.get(key) or "").strip()
            return float(value) if value else None

        mean_ra, mean_dec = number("RAmdeg"), number("DEmdeg")
        if mean_ra is not None and mean_dec is not None:
            ra, dec, source = mean_ra, mean_dec, "mean J2000"
        else:
            ra, dec, source = number("RA(ICRS)"), number("DE(ICRS)"), "observed ~J1991.25"
        if ra is None or dec is None:
            continue
        vt, bt = number("VTmag"), number("BTmag")
        stars.append(
            TychoStar(
                tycho_id="TYC {}-{}-{}".format(
                    *(row[k].strip() for k in ("TYC1", "TYC2", "TYC3"))
                ),
                ra=ra,
                dec=dec,
                vt_mag=vt,
                bt_mag=bt,
                v_mag=johnson_v(vt, bt),
                position_source=source,
            )
        )
    return stars


def query_tycho(
    params: dict[str, str], client: httpx.Client | None = None
) -> tuple[str, list[TychoStar]]:
    query = {
        "-source": "I/259/tyc2",
        "-out": TYCHO_COLUMNS,
        "-out.max": "unlimited",
        "VTmag": f"<{QUERY_MAX_VT}",
        **params,
    }
    request = client.get if client is not None else httpx.get
    response = request(VIZIER_URL, params=query, timeout=180.0)
    response.raise_for_status()
    return str(response.request.url), parse_tycho_tsv(response.text)


def bright(stars: Sequence[TychoStar]) -> list[TychoStar]:
    return [s for s in stars if s.v_mag is not None and s.v_mag <= BRIGHT_V_MAX]


# --- pre-registered field selection ---


def ecliptic_latitude(ra: float, dec: float) -> float:
    coord = SkyCoord(ra * u.deg, dec * u.deg, frame="icrs")
    return float(coord.transform_to(GeocentricTrueEcliptic()).lat.deg)


def selection_order(stars: Sequence[TychoStar]) -> list[TychoStar]:
    eligible = [
        s
        for s in bright(stars)
        if s.dec >= SELECTION_MIN_DEC
        and abs(ecliptic_latitude(s.ra, s.dec)) <= SELECTION_MAX_ECLIPTIC_LATITUDE
    ]
    return sorted(
        eligible,
        key=lambda s: hashlib.sha256(f"{SELECTION_SALT}:{s.tycho_id}".encode()).hexdigest(),
    )


def pick_sequence(rows: Sequence[dict[str, str]]) -> list[dict[str, str]] | None:
    """Earliest (field, CCD, quadrant, UTC date) group with >= 3 exposures;
    its first, middle and last exposure."""
    groups: dict[tuple, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (row["field"], row["ccdid"], row["qid"], row["obsdate"][:10])
        groups[key].append(row)
    qualifying = [g for g in groups.values() if len(g) >= 3]
    if not qualifying:
        return None
    group = min(
        qualifying, key=lambda g: min((float(r["obsjd"]), int(r["pid"])) for r in g)
    )
    group = sorted(group, key=lambda r: (float(r["obsjd"]), int(r["pid"])))
    return [group[0], group[(len(group) - 1) // 2], group[-1]]


class SelectedField(BaseModel):
    field: ValidationField
    selection_star: TychoStar
    filters: list[str]


class SelectionLog(BaseModel):
    star: str
    outcome: str


class FieldSelection(BaseModel):
    generated_at: datetime
    rule: str
    tycho_query: str
    eligible_stars: int
    fields: list[SelectedField]
    log: list[SelectionLog]


def select_fields(
    client: httpx.Client | None = None,
    metadata: Callable[..., list[dict[str, str]]] = fetch_ztf_metadata,
    tycho: Callable[..., tuple[str, list[TychoStar]]] = query_tycho,
    progress: Callable[[str], None] = lambda message: None,
) -> FieldSelection:
    url, stars = tycho({"DE(ICRS)": f">{SELECTION_MIN_DEC - 1}"}, client)
    ordered = selection_order(stars)
    reference_pids = {
        pid
        for s in ValidationReport.model_validate_json(AS022_REPORT.read_text()).snapshots
        for pid in (o.product_id for o in s.observations)
    }
    fields: list[SelectedField] = []
    log: list[SelectionLog] = []
    for star in ordered[:SELECTION_MAX_STARS_TRIED]:
        if len(fields) >= SELECTION_FIELDS:
            break
        progress(f"{star.tycho_id} (V {star.v_mag:.2f}): searching ZTF")
        try:
            rows = metadata(
                star.ra, star.dec, SELECTION_START_JD, SELECTION_END_JD, client
            )
        except Exception as exc:  # recorded, the rule moves to the next star
            log.append(SelectionLog(star=star.tycho_id, outcome=f"metadata error: {exc}"))
            continue
        sequence = pick_sequence(rows)
        if sequence is None:
            log.append(
                SelectionLog(
                    star=star.tycho_id,
                    outcome=f"no quadrant-night with >= 3 exposures ({len(rows)} rows)",
                )
            )
            continue
        pids = [int(r["pid"]) for r in sequence]
        if set(pids) & reference_pids:
            log.append(SelectionLog(star=star.tycho_id, outcome="overlaps AS-022 field"))
            continue
        first = sequence[0]
        field_id = (
            f"S{len(fields) + 1}-{first['obsdate'][:10]}-{int(first['field'])}"
            f"-c{int(first['ccdid'])}-q{int(first['qid'])}"
        )
        fields.append(
            SelectedField(
                field=ValidationField(
                    field_id=field_id,
                    description=f"AS-033 field around {star.tycho_id} (V {star.v_mag:.2f})",
                    product_ids=pids,
                    selection_note=SELECTION_RULE,
                ),
                selection_star=star,
                filters=[r["filtercode"] for r in sequence],
            )
        )
        log.append(SelectionLog(star=star.tycho_id, outcome=f"selected as {field_id}"))
    return FieldSelection(
        generated_at=datetime.now(timezone.utc),
        rule=SELECTION_RULE,
        tycho_query=url,
        eligible_stars=len(ordered),
        fields=fields,
        log=log,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    select = commands.add_parser("select", help="run the pre-registered selection")
    select.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "select":
        selection = select_fields(progress=lambda m: print(m, flush=True))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(selection.model_dump_json(indent=1) + "\n")
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
