"""AS-034: bright/saturated-star contamination as magnitude × distance.

Research/characterisation only — no filter, exclusion radius, score, rank,
threshold, rejection rule or candidate policy is derived here. UNKNOWN is
not a ground-truth false positive; KNOWN is a small, selected population.

Everything in the PRE-REGISTRATION block below was fixed and committed
before any evidence of this ticket was computed.

    python -m app.validation.star_contamination select \\
        --out validation/results/as034/as034_population.json
    python -m app.validation.star_contamination evidence \\
        --population validation/results/as034/as034_population.json \\
        --out-dir validation/results/as034
"""

import argparse
import math
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path

import httpx
from pydantic import BaseModel

from app.services.ztf_service import (
    METADATA_COLUMNS,
    ZTF_SCIENCE_METADATA_URL,
    ZTFServiceError,
)
from app.validation.bright_stars import FieldSelection, products_available
from app.validation.models import ValidationField
from app.validation.presets import AS022_REPORT
from app.validation.runner import ValidationReport


# ---------------------------------------------------------------------------
# PRE-REGISTRATION (AS-034, 2026-10-01; committed before any evidence run)
# ---------------------------------------------------------------------------

# Stars: Tycho-2 (VizieR I/259/tyc2) with the AS-033 V estimate
# V = VT - 0.090 (BT - VT) (V = VT without BT; no VT -> no magnitude, not
# used). V <= 11 keeps the range where Tycho-2 is close to complete and
# which covers stars saturated in a 30 s ZTF exposure; no star is treated
# as "clean" because it is fainter than 6.5.
STAR_V_MAX = 11.0
STAR_QUERY_MAX_VT = 11.5
STAR_CONE_MARGIN_ARCSEC = 900.0
# Magnitude classes: fixed 2-mag steps (open-ended at the bright end).
MAG_EDGES = (-math.inf, 4.0, 6.0, 8.0, 10.0, STAR_V_MAX)
# Distance annuli around each star [arcsec]: doubling widths; the last one
# (480"-900") is the local background of the same stars. Not derived from
# the AS-032/033 measurements.
ANNULUS_EDGES = (0.0, 15.0, 30.0, 60.0, 120.0, 240.0, 480.0, 900.0)
BACKGROUND_ANNULUS = len(ANNULUS_EDGES) - 2
# Primary profiles use isolated stars: no brighter (smaller V) Tycho-2
# star within 900". Profiles over all stars are reported too.
ISOLATION_ARCSEC = 900.0
# Annulus area inside the quadrant: polar sampling around each star.
AREA_RADIAL_STEPS = 24
AREA_ANGULAR_STEPS = 360

# Population: the eight AS-022/AS-033 fields, plus the three sibling
# quadrants (same exposures, same CCD) of each field that was selected
# around a bright star (B, D, S1-S4). A sibling is used only if all three
# exposures have an archived PSF catalog and science image (AS-033
# amendment 1). No pipeline output is consulted.
SIBLING_PARENTS = (
    "B-2019-01-25-565-c13-q3",
    "D-2019-06-02-281-c16-q3",
    "S1-2018-09-19-508-c10-q4",
    "S2-2018-09-27-509-c14-q4",
    "S3-2019-07-01-335-c7-q1",
    "S4-2018-11-07-615-c5-q3",
)
AS033_FIELDS = AS022_REPORT.parent / "as033" / "as033_fields.json"

# KNOWN objects searched near stars: every object the AS-022 target rule
# (TargetSelectionRule defaults: in every frame and footprint, position
# error <= 1", V <= faintest maglimit + 0.5) accepts in each field —
# primary and marginal alike. Their predicted positions, not pipeline
# output, decide their proximity.

# Visual sample (strips, SHA-256 order of '<salt>:<field>:<id>'):
VISUAL_SALT = "AS-034"
VISUAL_KNOWN_NEAR_ARCSEC = 120.0  # KNOWN with a V <= 10 star this close
VISUAL_KNOWN_MAX = 12
VISUAL_UNKNOWN_NEAR_ARCSEC = 60.0  # built UNKNOWN near a 6 <= V <= 11 star
VISUAL_UNKNOWN_PER_CLASS = 3
VISUAL_BACKGROUND_FAR_ARCSEC = 240.0  # built UNKNOWN with no V <= 11 star
VISUAL_BACKGROUND_MAX = 4

PREREGISTRATION = (
    "Stars: Tycho-2, V = VT - 0.090 (BT - VT), V <= 11. Magnitude classes "
    "<4, 4-6, 6-8, 8-10, 10-11. Annuli 0-15-30-60-120-240-480\" around each "
    "star, 480-900\" = local background of the same stars; primary profiles "
    "use isolated stars (no brighter Tycho-2 star within 900\"), all-star "
    "profiles reported too. Population: POC, B, C, D (AS-022), S1-S4 "
    "(AS-033) and the three sibling quadrants (same exposures and CCD) of "
    "B, D, S1-S4 with archived products. KNOWN: all objects passing the "
    "AS-022 target rule (primary + marginal), proximity from predicted "
    "positions, loss stage from the AS-022 outcome logic. Visual: up to 12 "
    "KNOWN within 120\" of a V <= 10 star; 3 built UNKNOWN within 60\" of a "
    "star per class 6-8, 8-10, 10-11; 4 built UNKNOWN with no V <= 11 star "
    "within 240\"; SHA-256 order. No outcome was looked at."
)


class PopulationField(BaseModel):
    field: ValidationField
    origin: str  # AS-022 | AS-033 | sibling of <field id>
    skybot: str  # AS-022 snapshot | AS-033 snapshot | live (stored)


class Population(BaseModel):
    generated_at: datetime
    preregistration: str
    fields: list[PopulationField]
    log: list[str]


def _metadata_rows(where: str, client: httpx.Client | None) -> list[dict[str, str]]:
    import csv
    from io import StringIO

    request = client.get if client is not None else httpx.get
    response = request(
        ZTF_SCIENCE_METADATA_URL,
        params={
            "WHERE": where,
            "COLUMNS": ",".join((*METADATA_COLUMNS, "expid")),
            "ct": "csv",
        },
        timeout=120.0,
    )
    if not response.is_success:
        raise ZTFServiceError(f"IRSA metadata HTTP {response.status_code}")
    return list(csv.DictReader(StringIO(response.text)))


def sibling_sequences(
    rows: Sequence[dict[str, str]],
) -> dict[int, list[dict[str, str]]]:
    """Sibling-quadrant rows grouped by quadrant id, each in exposure order."""
    by_quadrant: dict[int, list[dict[str, str]]] = {}
    for row in rows:
        by_quadrant.setdefault(int(row["qid"]), []).append(row)
    return {
        qid: sorted(group, key=lambda r: (float(r["obsjd"]), int(r["pid"])))
        for qid, group in sorted(by_quadrant.items())
    }


def build_population(
    client: httpx.Client | None = None,
    metadata: Callable[[str, httpx.Client | None], list[dict[str, str]]] = (
        _metadata_rows
    ),
    available: Callable[..., bool] = products_available,
) -> Population:
    report = ValidationReport.model_validate_json(AS022_REPORT.read_text())
    selection = FieldSelection.model_validate_json(AS033_FIELDS.read_text())
    fields = [
        PopulationField(field=s.field, origin="AS-022", skybot="AS-022 snapshot")
        for s in report.snapshots
    ] + [
        PopulationField(field=s.field, origin="AS-033", skybot="AS-033 snapshot")
        for s in selection.fields
    ]
    by_id = {f.field.field_id: f.field for f in fields}
    log = []
    for parent_id in SIBLING_PARENTS:
        parent = by_id[parent_id]
        own = metadata(
            "pid IN (" + ",".join(map(str, parent.product_ids)) + ")", client
        )
        expids = sorted({int(r["expid"]) for r in own})
        ccd = int(own[0]["ccdid"])
        own_qid = int(own[0]["qid"])
        rows = metadata(
            "expid IN (" + ",".join(map(str, expids)) + f") AND ccdid = {ccd}",
            client,
        )
        for qid, sequence in sibling_sequences(rows).items():
            if qid == own_qid:
                continue
            if len(sequence) != len(expids):
                log.append(f"{parent_id} q{qid}: {len(sequence)} exposures, skipped")
                continue
            if not available(sequence, client):
                log.append(f"{parent_id} q{qid}: products missing, skipped")
                continue
            field_id = f"{parent_id.split('-q')[0]}-q{qid}"
            fields.append(
                PopulationField(
                    field=ValidationField(
                        field_id=field_id,
                        description=f"AS-034 sibling quadrant of {parent_id}",
                        product_ids=[int(r["pid"]) for r in sequence],
                        selection_note=PREREGISTRATION,
                    ),
                    origin=f"sibling of {parent_id}",
                    skybot="live (stored in as034_skybot.json)",
                )
            )
            log.append(f"{parent_id} q{qid}: added as {field_id}")
    return Population(
        generated_at=datetime.now(timezone.utc),
        preregistration=PREREGISTRATION,
        fields=fields,
        log=log,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    select = commands.add_parser("select", help="build the pre-registered population")
    select.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "select":
        population = build_population()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(population.model_dump_json(indent=1) + "\n")
        print("\n".join(population.log))
        print(f"wrote {args.out} ({len(population.fields)} fields)")


if __name__ == "__main__":
    main()
