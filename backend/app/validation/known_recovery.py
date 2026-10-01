"""AS-035: recovery of known moving objects near bright stars.

Research/characterisation only — no filter, exclusion radius, score, rank,
threshold, rejection rule or candidate policy is derived here. SkyBoT
predictions are not proof of detectability; UNKNOWN is not a false
positive; agent visual labels are not ground truth.

Everything in the PRE-REGISTRATION block below was fixed and committed
before any recovery outcome of this ticket was computed.

    python -m app.validation.known_recovery select \\
        --out validation/results/as035/as035_selection.json
"""

import argparse
import csv
import hashlib
import math
from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import httpx
from pydantic import BaseModel

from app.services.ztf_service import (
    METADATA_COLUMNS,
    ZTF_SCIENCE_METADATA_URL,
    ZTFServiceError,
    map_ztf_metadata_to_observation,
)
from app.validation.bright_stars import (
    SELECTION_END_JD,
    SELECTION_MAX_ECLIPTIC_LATITUDE,
    SELECTION_MIN_DEC,
    SELECTION_START_JD,
    TychoStar,
    ecliptic_latitude,
    products_available,
    query_tycho,
)
from app.validation.models import ValidationField
from app.validation.presets import AS022_REPORT


# ---------------------------------------------------------------------------
# PRE-REGISTRATION (AS-035, 2026-10-01; committed before any outcome run)
# ---------------------------------------------------------------------------

# --- Populations ---
# N (new, blind): quadrant-nights found by the star-driven search below.
# R (retrospective, not blind): the 26 AS-034 quadrants
# (validation/results/as034/as034_population.json). AS-034 reported
# aggregate loss stages for them, so R is analysed separately as well as
# pooled; N alone is the sensitivity check.

# --- Star-driven search for N (predictions only, no pipeline output) ---
SELECTION_SALT = "AS-035"
# Tycho-2 (I/259), V = VT - 0.090 (BT - VT) as in AS-033/034. Search stars
# are V < 8 (V 8-10 stars are far too many to list; they enter as by-catch
# in the selected quadrants and in R). Two search classes, alternated.
SEARCH_QUERY_MAX_VT = 8.5
SEARCH_CLASSES = ((-math.inf, 6.0), (6.0, 8.0))  # V < 6, 6 <= V < 8
QUADRANTS_PER_CLASS = 12
MAX_STARS_PER_CLASS = 60
MAX_NIGHTS_PER_STAR = 15
# Same sky/time window as AS-033: Dec >= -25 deg, |ecliptic lat| <= 10 deg,
# 2018-03-17 .. 2021-01-01.

# Sequence rule (temporal baseline, fixed before any outcome): within one
# (field, CCD, quadrant, UTC date) group, E1 = earliest exposure, E3 =
# latest exposure with E3 - E1 <= MAX_SPAN_MIN, E2 = the exposure closest
# in time to (E1 + E3) / 2 among those >= MIN_GAP_MIN from both E1 and E3
# (ties: earlier); exposures without maglimit/corners are not used. A group without such a triple does not qualify. All
# three exposures must have archived PSF catalogs and science images
# (AS-033 amendment 1). Reason: S3 (AS-033/034) had a 0.66-minute E1-E2
# gap and lost all 78 KNOWN objects; spans much longer than the AS-022
# fields (<= 169 min) add non-linear (parallax) motion the 0.5" fit limit
# was never checked against.
MIN_GAP_MIN = 15.0
MAX_SPAN_MIN = 150.0

# Trigger (decides which night of a search star is used): one SkyBoT cone
# (radius TRIGGER_CONE_ARCSEC, I41) at the search star at E2's mid-exposure;
# each object's E1/E3 positions extrapolated linearly from its SkyBoT rates.
# A night triggers when an object (a) comes within TRIGGER_NEAR_ARCSEC of the
# search star at E1, E2 or E3, (b) has V <= faintest maglimit + 0.5 and
# position error <= 1" (AS-022 target rule), (c) is rate- and baseline-
# eligible (below), (d) lies inside the quadrant footprint at all three
# epochs. The earliest triggering night with archived products is used;
# stars without one in MAX_NIGHTS_PER_STAR qualifying nights are skipped.
# Quadrant-nights already in R or already selected are skipped.
TRIGGER_CONE_ARCSEC = 300.0
TRIGGER_NEAR_ARCSEC = 120.0

# --- Targets (both populations) ---
# Every object the AS-022 target rule (TargetSelectionRule defaults) accepts
# from full-quadrant SkyBoT predictions at the three epochs: PRIMARY
# (V <= faintest maglimit - 0.5) and MARGINAL (<= + 0.5). Predictions only.
#
# Eligibility (from predictions; the S3 confound is separated here):
# - rate-eligible: predicted rate <= max_rate_arcsec_per_min (1.0"/min);
#   the builder cannot link faster objects.
# - baseline-eligible: predicted displacement between every pair of the
#   three epochs >= BASELINE_MIN_DISPLACEMENT_ARCSEC = 2 x the stationary
#   tolerance (1.5"). Below it, stationary self-matching is expected.
# Objects that fail either are reported in their own stratum ("short
# baseline" / "too fast") and never counted as near-star losses.
BASELINE_TOLERANCE_FACTOR = 2.0
#
# Detectability: per frame, expected magnitude in the frame's band
# m = V + BAND_OFFSET (typical asteroid colours g-r ~ 0.55, r-i ~ 0.15;
# uncertain by ~0.2 mag, SkyBoT V by ~0.3 mag); global margin = frame
# maglimit - m; local 5-sigma depth from the PSF catalog: median of
# (mag + 2.5 log10(snr / 5)) over sources with LOCAL_DEPTH_SNR within
# LOCAL_DEPTH_RADIUS_ARCSEC of the predicted position (null if fewer than
# LOCAL_DEPTH_MIN_SOURCES), and the same median over the whole frame;
# local margin = local depth - m. Reported per object and used to stratify
# detection-stage losses (locally detectable or not); not a selection cut.
BAND_OFFSET = {"zg": 0.33, "zr": -0.22, "zi": -0.37}
LOCAL_DEPTH_RADIUS_ARCSEC = 60.0
LOCAL_DEPTH_SNR = (3.0, 20.0)
LOCAL_DEPTH_MIN_SOURCES = 5

# --- Star proximity strata (predicted positions, closest approach over E1-E3)
# Stars: Tycho-2 V <= 11 in the footprint circle + 15' (AS-034
# field_stars). Classes for recovery tables: V < 6, 6-8, 8-10 (10-11 only
# as a control condition). Distance bins 0-30-60-120-240". An object is
# counted once per class, in the bin of its closest approach to that class.
RECOVERY_CLASSES = ((-math.inf, 6.0), (6.0, 8.0), (8.0, 10.0))
DISTANCE_EDGES = (0.0, 30.0, 60.0, 120.0, 240.0)
# Star zone (prior evidence: AS-034 O1, where the built-UNKNOWN excess
# reaches): within 120" of V < 6, 60" of 6 <= V < 8, 30" of 8 <= V < 10.
ZONE_REACH = ((6.0, 120.0), (8.0, 60.0), (10.0, 30.0))  # (V upper, arcsec)
# Outer: within 240" of a V < 10 star, not in the zone.
# Control: >= 480" from every V < 10 star and >= 60" from every V 10-11
# star. Everything else is "intermediate" (reported, not compared).
OUTER_ARCSEC = 240.0
CONTROL_V10_ARCSEC = 480.0
CONTROL_V11_ARCSEC = 60.0

# --- Stage-by-stage trace (each target; first failing stage = loss point)
# 1 expected position: inside the footprint in every frame (rule) — plus
#   eligibility and detectability above.
# 2 source detection: a PSF-catalog source within match_radius (2.0") of
#   the predicted position in every frame (nearest one is the target's).
# 3 stationary/moving: each of those sources is a moving candidate (not
#   stationary-matched); for a stationary one, what it matched (the
#   target's own source in another frame, or another source).
# 4 association: a tracklet (any status) contains all three target sources.
# 5 fit acceptance: that tracklet is TRACKLET_BUILT.
# 6 identification: it is identified KNOWN with the target as best match.
# Recovered = all six. The AS-022 outcome (any tracklet identified as the
# target) is recorded alongside.

# --- Comparison and claim rule ---
# Primary contrast: PRIMARY, rate- and baseline-eligible targets, zone vs
# control, N and R pooled; N-only and R-only reported. Wilson 95 %
# intervals; Fisher exact two-sided p; Mantel-Haenszel odds ratio over
# quadrants having both zone and control targets (same frames, filters,
# seeing, baseline). A near-star recovery penalty is CLAIMED only if the
# zone has >= MIN_ZONE_TARGETS targets, Fisher p < 0.05 with zone recovery
# lower, and the MH odds ratio (if defined) also < 1. Otherwise: "not
# demonstrated" (insufficient evidence is an acceptable result).
MIN_ZONE_TARGETS = 10
CLAIM_ALPHA = 0.05

# --- Visual sample (strips E1|E2|E3, markers = predicted positions) ---
# SHA-256('AS-035:<field>:<designation>') order, from rate- and baseline-
# eligible PRIMARY + MARGINAL targets within 120" of a V < 10 star: up to 8
# recovered and 8 lost; plus 2 recovered and 2 lost controls; plus 288181
# and 408599 (AS-034 revisit) if they are R targets — named, not sampled.
VISUAL_SALT = "AS-035"
VISUAL_NEAR_ARCSEC = 120.0
VISUAL_NEAR_PER_OUTCOME = 8
VISUAL_CONTROL_PER_OUTCOME = 2
REVISIT = ("288181", "408599")

PREREGISTRATION = (
    "Populations: N = star-driven search (Tycho-2 V<6 and 6-8 stars, Dec>=-25, "
    "|beta|<=10, SHA-256('AS-035:<id>') order, alternating classes, 12 "
    "quadrant-nights per class, <=60 stars and <=15 nights per star; trigger = "
    'SkyBoT object passing within 120" of the star at E1/E2/E3 that meets the '
    "AS-022 target rule, rate <= 1\"/min and baseline rule, inside the footprint); "
    "R = the 26 AS-034 quadrants (not blind). Sequence rule: E1 first, E3 last "
    "within 150 min, E2 closest to the midpoint with >=15 min gaps, archived "
    "products. Targets: AS-022 rule (primary/marginal). Eligibility: rate <= "
    '1.0"/min; every pairwise predicted displacement >= 3.0" (2x stationary '
    "tolerance); failures form their own strata. Detectability: band offsets "
    "g +0.33, r -0.22, i -0.37; local 5-sigma depth from PSF sources (3<=snr<=20) "
    'within 60". Strata: classes V<6, 6-8, 8-10 x closest approach 0-30-60-120-'
    '240"; zone = <120" of V<6, <60" of 6-8, <30" of 8-10; control = >=480" from '
    'V<10 and >=60" from V10-11. Trace: expected position, detection (2.0"), '
    "stationary/moving, association, fit, identification; first failure. Claim "
    "rule: zone PRIMARY eligible n>=10, Fisher two-sided p<0.05 (lower in zone) "
    "and MH odds ratio over shared quadrants < 1; else not demonstrated. Strips: "
    'SHA-256 order, <=8 recovered + <=8 lost within 120" of V<10, 2+2 controls, '
    "plus 288181/408599 if R targets. No outcome was looked at."
)


# ---------------------------------------------------------------------------
# Selection (N)
# ---------------------------------------------------------------------------

SEARCH_METADATA_COLUMNS = (
    *METADATA_COLUMNS,
    "maglimit",
    "ra1",
    "dec1",
    "ra2",
    "dec2",
    "ra3",
    "dec3",
    "ra4",
    "dec4",
)


def search_class(v_mag: float | None) -> int | None:
    if v_mag is None:
        return None
    for index, (low, high) in enumerate(SEARCH_CLASSES):
        if low <= v_mag < high:
            return index
    return None


def search_order(stars: Sequence[TychoStar]) -> list[list[TychoStar]]:
    """Eligible search stars per class, in SHA-256 order."""
    classes: list[list[TychoStar]] = [[] for _ in SEARCH_CLASSES]
    for star in stars:
        index = search_class(star.v_mag)
        if (
            index is None
            or star.dec < SELECTION_MIN_DEC
            or abs(ecliptic_latitude(star.ra, star.dec))
            > SELECTION_MAX_ECLIPTIC_LATITUDE
        ):
            continue
        classes[index].append(star)
    return [
        sorted(
            group,
            key=lambda s: hashlib.sha256(
                f"{SELECTION_SALT}:{s.tycho_id}".encode()
            ).hexdigest(),
        )
        for group in classes
    ]


def _jd(row: dict[str, str]) -> float:
    return float(row["obsjd"])


def pick_triple(group: Sequence[dict[str, str]]) -> list[dict[str, str]] | None:
    """The pre-registered E1/E2/E3 of one quadrant-night, or None."""
    rows = sorted(group, key=lambda r: (_jd(r), int(r["pid"])))
    if len(rows) < 3:
        return None
    first = rows[0]
    later = [r for r in rows[1:] if (_jd(r) - _jd(first)) * 1440.0 <= MAX_SPAN_MIN]
    if not later:
        return None
    last = later[-1]
    middle_jd = (_jd(first) + _jd(last)) / 2.0
    middles = [
        r
        for r in rows
        if (_jd(r) - _jd(first)) * 1440.0 >= MIN_GAP_MIN
        and (_jd(last) - _jd(r)) * 1440.0 >= MIN_GAP_MIN
    ]
    if not middles:
        return None
    middle = min(middles, key=lambda r: (abs(_jd(r) - middle_jd), _jd(r)))
    return [first, middle, last]


def quadrant_nights(rows: Sequence[dict[str, str]]) -> list[list[dict[str, str]]]:
    """Qualifying triples of all quadrant-nights, earliest first."""
    groups: dict[tuple, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if not all((row.get(k) or "").strip() for k in SEARCH_METADATA_COLUMNS[-9:]):
            continue  # no maglimit or corners: exposure not usable
        key = (row["field"], row["ccdid"], row["qid"], row["obsdate"][:10])
        groups[key].append(row)
    triples = [t for g in groups.values() if (t := pick_triple(g)) is not None]
    return sorted(triples, key=lambda t: (_jd(t[0]), int(t[0]["pid"])))


def baseline_eligible(positions: Sequence[tuple[float, float]], tolerance: float) -> bool:
    from itertools import combinations

    from app.services.astrometry import angular_distance_arcsec

    return all(
        angular_distance_arcsec(*a, *b) >= BASELINE_TOLERANCE_FACTOR * tolerance
        for a, b in combinations(positions, 2)
    )


def extrapolate(ephemeris, minutes: float) -> tuple[float, float]:
    """Linear sky motion from SkyBoT rates (arcsec/h), small offsets."""
    dec = ephemeris.predicted_dec + ephemeris.motion_dec_arcsec_per_hour * minutes / 60.0 / 3600.0
    ra = ephemeris.predicted_ra + (
        ephemeris.motion_ra_cos_dec_arcsec_per_hour
        * minutes
        / 60.0
        / 3600.0
        / math.cos(math.radians(ephemeris.predicted_dec))
    )
    return ra % 360.0, dec


class TriggerObject(BaseModel):
    designation: str
    v_magnitude: float
    rate_arcsec_per_min: float
    closest_approach_arcsec: float
    positions: list[tuple[float, float]]


def trigger_objects(
    star: TychoStar,
    triple: Sequence[dict[str, str]],
    objects: Sequence,
    config,
) -> list[TriggerObject]:
    """Objects of a SkyBoT cone at E2 that fulfil the trigger rule."""
    from app.services.astrometry import angular_distance_arcsec
    from app.validation.models import FrameMetadata, TargetSelectionRule
    from app.validation.selection import inside_footprint, predicted_motion

    rule = TargetSelectionRule()
    min_maglimit = min(float(r["maglimit"]) for r in triple)
    frames = [_frame_metadata(r) for r in triple]
    offsets = [(_jd(r) - _jd(triple[1])) * 1440.0 for r in triple]
    found = []
    for ephemeris in objects:
        if ephemeris.v_magnitude is None:
            continue
        if ephemeris.v_magnitude > min_maglimit + rule.marginal_margin_mag:
            continue
        if ephemeris.position_error_arcsec > rule.max_position_error_arcsec:
            continue
        rate, _ = predicted_motion(ephemeris)
        if rate > config.max_rate_arcsec_per_min:
            continue
        positions = [extrapolate(ephemeris, m) for m in offsets]
        if not baseline_eligible(positions, config.stationary_tolerance_arcsec):
            continue
        if not all(
            inside_footprint(ra, dec, frame)
            for (ra, dec), frame in zip(positions, frames)
        ):
            continue
        closest = min(angular_distance_arcsec(ra, dec, star.ra, star.dec) for ra, dec in positions)
        if closest >= TRIGGER_NEAR_ARCSEC:
            continue
        found.append(
            TriggerObject(
                designation=ephemeris.designation,
                v_magnitude=ephemeris.v_magnitude,
                rate_arcsec_per_min=round(rate, 4),
                closest_approach_arcsec=round(closest, 2),
                positions=positions,
            )
        )
    return sorted(found, key=lambda t: t.designation)


def _frame_metadata(row: dict[str, str]):
    from app.validation.models import FrameMetadata

    from app.validation.masked import _mean

    corners = [(float(row[f"ra{i}"]), float(row[f"dec{i}"])) for i in range(1, 5)]
    center = _mean(corners)  # only the offset origin of the footprint test
    return FrameMetadata(
        product_id=int(row["pid"]),
        center_ra=center[0],
        center_dec=center[1],
        corners=corners,
        maglimit=float(row["maglimit"]),
        seeing_arcsec=0.0,
        airmass=0.0,
    )


def star_metadata(
    ra: float, dec: float, client: httpx.Client | None = None
) -> list[dict[str, str]]:
    """IRSA science exposures covering a position in the search window."""
    request = client.get if client is not None else httpx.get
    response = request(
        ZTF_SCIENCE_METADATA_URL,
        params={
            "POS": f"{ra},{dec}",
            "WHERE": f"obsjd >= {SELECTION_START_JD} AND obsjd < {SELECTION_END_JD}",
            "COLUMNS": ",".join(SEARCH_METADATA_COLUMNS),
            "ct": "csv",
        },
        timeout=120.0,
    )
    if not response.is_success:
        raise ZTFServiceError(f"IRSA metadata HTTP {response.status_code}")
    return list(csv.DictReader(StringIO(response.text)))


def skybot_cone(star: TychoStar, row: dict[str, str], client=None) -> list:
    from app.services.identification_service import mid_exposure_jd_utc
    from app.services.skybot_service import ZTF_OBSERVATORY_CODE, query_known_objects

    observation = map_ztf_metadata_to_observation(row)
    return query_known_objects(
        star.ra,
        star.dec,
        TRIGGER_CONE_ARCSEC / 3600.0,
        mid_exposure_jd_utc(observation),
        observer=ZTF_OBSERVATORY_CODE,
        client=client,
    ).objects


class SelectedSequence(BaseModel):
    field: ValidationField
    search_class: str
    search_star: TychoStar
    night_index: int  # among the star's qualifying nights, 0-based
    filters: list[str]
    minutes_from_first: list[float]
    trigger: list[TriggerObject]


class SelectionLog(BaseModel):
    star: str
    search_class: str
    outcome: str


class Selection(BaseModel):
    generated_at: datetime
    preregistration: str
    tycho_query: str
    eligible_stars: list[int]
    sequences: list[SelectedSequence]
    skybot_queries: int
    log: list[SelectionLog]


def class_name(index: int) -> str:
    low, high = SEARCH_CLASSES[index]
    return f"V<{high:g}" if math.isinf(low) else f"{low:g}<=V<{high:g}"


def r_quadrant_nights() -> set[tuple[str, str, str, str]]:
    """(field, ccd, qid, date) of every R quadrant-night (AS-034)."""
    from app.validation.star_contamination import Population

    population = Population.model_validate_json(
        (AS022_REPORT.parent / "as034" / "as034_population.json").read_text()
    )
    keys = set()
    for entry in population.fields:
        # field id: <name>-<YYYY-MM-DD>-<field>-c<ccd>-q<qid>
        parts = entry.field.field_id.split("-")
        keys.add((parts[4], parts[5][1:], parts[6][1:], "-".join(parts[1:4])))
    return keys


def select_sequences(
    client: httpx.Client | None = None,
    tycho: Callable[..., tuple[str, list[TychoStar]]] = query_tycho,
    metadata: Callable[..., list[dict[str, str]]] = star_metadata,
    cone: Callable[..., list] = skybot_cone,
    available: Callable[..., bool] = products_available,
    excluded: set[tuple[str, str, str, str]] | None = None,
    progress: Callable[[str], None] = lambda message: None,
) -> Selection:
    from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG as CONFIG

    url, stars = tycho(
        {"DE(ICRS)": f">{SELECTION_MIN_DEC - 1}", "VTmag": f"<{SEARCH_QUERY_MAX_VT}"},
        client,
    )
    ordered = search_order(stars)
    used = set(r_quadrant_nights() if excluded is None else excluded)
    selected: list[SelectedSequence] = []
    log: list[SelectionLog] = []
    queries = 0
    done = [0] * len(SEARCH_CLASSES)
    tried = [0] * len(SEARCH_CLASSES)
    while any(
        done[c] < QUADRANTS_PER_CLASS
        and tried[c] < min(MAX_STARS_PER_CLASS, len(ordered[c]))
        for c in range(len(SEARCH_CLASSES))
    ):
        for c in range(len(SEARCH_CLASSES)):
            if done[c] >= QUADRANTS_PER_CLASS or tried[c] >= min(
                MAX_STARS_PER_CLASS, len(ordered[c])
            ):
                continue
            star = ordered[c][tried[c]]
            tried[c] += 1
            name = class_name(c)
            progress(f"{name} {star.tycho_id} (V {star.v_mag:.2f})")
            try:
                rows = metadata(star.ra, star.dec, client)
            except Exception as exc:  # logged; the rule moves on
                log.append(SelectionLog(star=star.tycho_id, search_class=name, outcome=f"metadata error: {exc}"))
                continue
            nights = quadrant_nights(rows)
            outcome = f"no triggering night in {min(len(nights), MAX_NIGHTS_PER_STAR)} of {len(nights)} qualifying nights"
            for night_index, triple in enumerate(nights[:MAX_NIGHTS_PER_STAR]):
                first = triple[0]
                key = (
                    str(int(first["field"])),
                    str(int(first["ccdid"])),
                    str(int(first["qid"])),
                    first["obsdate"][:10],
                )
                if key in used:
                    continue
                try:
                    objects = cone(star, triple[1], client)
                    queries += 1
                except Exception as exc:
                    outcome = f"SkyBoT error on night {night_index}: {exc}"
                    break
                trigger = trigger_objects(star, triple, objects, CONFIG)
                if not trigger:
                    continue
                if not available(triple, client):
                    log.append(SelectionLog(star=star.tycho_id, search_class=name, outcome=f"night {night_index} {key}: products missing"))
                    continue
                used.add(key)
                field_id = (
                    f"N{len(selected) + 1}-{key[3]}-{key[0]}-c{key[1]}-q{key[2]}"
                )
                selected.append(
                    SelectedSequence(
                        field=ValidationField(
                            field_id=field_id,
                            description=f"AS-035 near-star search: {star.tycho_id} (V {star.v_mag:.2f})",
                            product_ids=[int(r["pid"]) for r in triple],
                            selection_note=PREREGISTRATION,
                        ),
                        search_class=name,
                        search_star=star,
                        night_index=night_index,
                        filters=[r["filtercode"] for r in triple],
                        minutes_from_first=[round((_jd(r) - _jd(first)) * 1440.0, 2) for r in triple],
                        trigger=trigger,
                    )
                )
                done[c] += 1
                outcome = f"selected as {field_id} (night {night_index})"
                break
            log.append(SelectionLog(star=star.tycho_id, search_class=name, outcome=outcome))
    return Selection(
        generated_at=datetime.now(timezone.utc),
        preregistration=PREREGISTRATION,
        tycho_query=url,
        eligible_stars=[len(group) for group in ordered],
        sequences=selected,
        skybot_queries=queries,
        log=log,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    select = commands.add_parser("select", help="pre-registered star-driven search (N)")
    select.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "select":
        selection = select_sequences(progress=lambda m: print(m, flush=True))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(selection.model_dump_json(indent=1) + "\n")
        print(f"wrote {args.out} ({len(selection.sequences)} sequences, {selection.skybot_queries} SkyBoT queries)")


if __name__ == "__main__":
    main()
