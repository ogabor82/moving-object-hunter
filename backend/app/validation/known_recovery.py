"""AS-035: recovery of known moving objects near bright stars.

Research/characterisation only — no filter, exclusion radius, score, rank,
threshold, rejection rule or candidate policy is derived here. SkyBoT
predictions are not proof of detectability; UNKNOWN is not a false
positive; agent visual labels are not ground truth.

Everything in the PRE-REGISTRATION block below was fixed and committed
before any recovery outcome of this ticket was computed.

    python -m app.validation.known_recovery select \\
        --out validation/results/as035/as035_selection.json
    python -m app.validation.known_recovery evidence --population R \\
        --selection validation/results/as035/as035_selection.json \\
        --out-dir validation/results/as035          # and --population N
    python -m app.validation.known_recovery combine --out-dir validation/results/as035
    python -m app.validation.known_recovery render --out-dir validation/results/as035
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
from app.validation.runner import ValidationReport
from app.validation.star_contamination import StarProximity


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


# ---------------------------------------------------------------------------
# Evidence (written after the pre-registration commit fa4cd97)
# ---------------------------------------------------------------------------

STAGES = ("detection", "stationary", "association", "fit", "identification")


class FrameTrace(BaseModel):
    """One target in one frame."""

    product_id: int
    filter_code: str
    predicted: tuple[float, float]
    expected_mag: float
    global_margin_mag: float  # frame maglimit - expected magnitude
    local_depth_mag: float | None
    local_margin_mag: float | None
    local_sources: int  # PSF sources within LOCAL_DEPTH_RADIUS_ARCSEC
    nearest_arcsec: float | None  # nearest PSF source within 10"
    detected: bool  # nearest source within match_radius
    source_id: str | None
    source_mag: float | None
    source_snr: float | None
    source_mask_bits: int | None
    source_sharp: float | None
    candidate: bool | None  # None when not detected
    # For a stationary source: what it matched within the stationary
    # tolerance in another frame — "self" (the target's own source there),
    # "other" (another source), with that source's distance and magnitude.
    stationary_match: str | None
    stationary_match_arcsec: float | None
    stationary_match_mag: float | None


class TargetTrace(BaseModel):
    population: str  # N | R
    field_id: str
    designation: str
    object_class: str
    role: str
    v_magnitude: float
    rate_arcsec_per_min: float
    min_pair_displacement_arcsec: float
    rate_eligible: bool
    baseline_eligible: bool
    edge_distance_arcsec: float  # min over frames, to the footprint edge
    proximity: StarProximity  # AS-034 classes, min over E1-E3 positions
    group: str  # zone | outer | intermediate | control
    frames: list[FrameTrace]
    detected_frames: int
    candidate_frames: int
    tracklet_id: str | None  # tracklet holding all three target sources
    tracklet_status: str | None
    identification_status: str | None
    best_match: str | None
    partial_tracklets: int  # tracklets holding 1-2 of the target sources
    recovered: bool
    first_failure: str | None  # one of STAGES, None when recovered
    as022_recovered: bool
    as022_loss_stage: str


def class_separations(proximity: StarProximity) -> tuple[float | None, ...]:
    """(V<6, 6-8, 8-10, 10-11) closest approaches from the AS-034 classes."""
    s = proximity.separation_by_class

    def smallest(*values):
        values = [v for v in values if v is not None]
        return min(values) if values else None

    return smallest(s[0], s[1]), s[2], s[3], s[4]


def proximity_group(proximity: StarProximity) -> str:
    v6, v8, v10, v11 = class_separations(proximity)
    reach = dict(zip((0, 1, 2), (r for _, r in ZONE_REACH)))
    for index, separation in enumerate((v6, v8, v10)):
        if separation is not None and separation < reach[index]:
            return "zone"
    bright = [s for s in (v6, v8, v10) if s is not None]
    if bright and min(bright) < OUTER_ARCSEC:
        return "outer"
    if (not bright or min(bright) >= CONTROL_V10_ARCSEC) and (
        v11 is None or v11 >= CONTROL_V11_ARCSEC
    ):
        return "control"
    return "intermediate"


def distance_bin(separation: float | None) -> int | None:
    if separation is None:
        return None
    for index in range(len(DISTANCE_EDGES) - 1):
        if DISTANCE_EDGES[index] <= separation < DISTANCE_EDGES[index + 1]:
            return index
    return None


def frame_depth(magnitudes, snrs) -> float | None:
    """Median 5-sigma depth estimate mag + 2.5 log10(snr / 5) of sources
    with LOCAL_DEPTH_SNR; None with fewer than LOCAL_DEPTH_MIN_SOURCES."""
    import numpy

    magnitudes = numpy.asarray(magnitudes, float)
    snrs = numpy.asarray(snrs, float)
    use = (snrs >= LOCAL_DEPTH_SNR[0]) & (snrs <= LOCAL_DEPTH_SNR[1])
    if use.sum() < LOCAL_DEPTH_MIN_SOURCES:
        return None
    return float(numpy.median(magnitudes[use] + 2.5 * numpy.log10(snrs[use] / 5.0)))


def edge_distance_arcsec(ra: float, dec: float, corners) -> float:
    """Distance from a position to the nearest footprint edge (tangent
    plane), positive inside."""
    import numpy

    from app.validation.bright_stars import _gnomonic

    xs, ys = _gnomonic(
        numpy.array([c[0] for c in corners]), numpy.array([c[1] for c in corners]), ra, dec
    )
    points = numpy.degrees(numpy.column_stack([xs, ys])) * 3600.0
    center = points.mean(axis=0)
    points = points[numpy.argsort(numpy.arctan2(points[:, 1] - center[1], points[:, 0] - center[0]))]
    best = math.inf
    for k in range(len(points)):
        a, b = points[k], points[(k + 1) % len(points)]
        ab = b - a
        t = max(0.0, min(1.0, float(numpy.dot(-a, ab) / numpy.dot(ab, ab))))
        best = min(best, float(numpy.hypot(*(a + t * ab))))
    return best


def trace_target(
    population: str,
    field_id: str,
    target,
    frames,
    metadata,
    candidate_frames,
    tracklets,
    identifications,
    config,
    stars,
    sharp_by_source_id: dict[str, float],
    depth_by_frame: Sequence[float | None],
) -> TargetTrace:
    """Stage-by-stage trace of one target (pre-registered definitions)."""
    from itertools import combinations

    import numpy

    from app.models.identification import IdentificationStatus
    from app.models.tracklet import TrackletStatus
    from app.services.astrometry import angular_distance_arcsec, find_pairs_within
    from app.validation.evaluate import NEAREST_DETECTION_RADIUS_ARCSEC, _target_outcome
    from app.validation.star_contamination import loss_stage, min_proximity

    positions = target.predicted_positions
    traces: list[FrameTrace] = []
    sources: list[str | None] = []
    for frame, candidate_frame, meta, (ra, dec), depth in zip(
        frames, candidate_frames, metadata, positions, depth_by_frame
    ):
        detections = frame.detections
        ras = numpy.array([d.ra for d in detections])
        decs = numpy.array([d.dec for d in detections])
        _, near_idx, near_sep = find_pairs_within(
            [ra], [dec], ras, decs, max(LOCAL_DEPTH_RADIUS_ARCSEC, NEAREST_DETECTION_RADIUS_ARCSEC)
        )
        local = near_idx[near_sep <= LOCAL_DEPTH_RADIUS_ARCSEC]
        local_depth = frame_depth(
            [detections[i].magnitude for i in local], [detections[i].snr for i in local]
        )
        expected = target.v_magnitude + BAND_OFFSET.get(frame.observation.filter_code, 0.0)
        close = near_sep <= NEAREST_DETECTION_RADIUS_ARCSEC
        nearest = source = None
        if close.any():
            best = int(numpy.argmin(numpy.where(close, near_sep, numpy.inf)))
            nearest = float(near_sep[best])
            source = detections[int(near_idx[best])]
        detected = nearest is not None and nearest <= config.match_radius_arcsec
        source = source if detected else None
        sources.append(source.source_id if source else None)
        candidate_ids = {c.source_id for c in candidate_frame.candidates}
        traces.append(
            FrameTrace(
                product_id=frame.observation.product_id,
                filter_code=frame.observation.filter_code,
                predicted=(ra, dec),
                expected_mag=round(expected, 3),
                global_margin_mag=round(meta.maglimit - expected, 3),
                local_depth_mag=None if local_depth is None else round(local_depth, 3),
                local_margin_mag=None if local_depth is None else round(local_depth - expected, 3),
                local_sources=int(len(local)),
                nearest_arcsec=None if nearest is None else round(nearest, 3),
                detected=detected,
                source_id=source.source_id if source else None,
                source_mag=source.magnitude if source else None,
                source_snr=source.snr if source else None,
                source_mask_bits=source.mask_bits if source else None,
                source_sharp=sharp_by_source_id.get(source.source_id) if source else None,
                candidate=(source.source_id in candidate_ids) if source else None,
                stationary_match=None,
                stationary_match_arcsec=None,
                stationary_match_mag=None,
            )
        )
    # What a stationary target source matched in the other frames.
    for index, trace in enumerate(traces):
        if trace.candidate is not False:
            continue
        own = next(d for d in frames[index].detections if d.source_id == trace.source_id)
        best = None
        for other, frame in enumerate(frames):
            if other == index:
                continue
            _, idx, sep = find_pairs_within(
                [own.ra], [own.dec],
                [d.ra for d in frame.detections], [d.dec for d in frame.detections],
                config.stationary_tolerance_arcsec,
            )
            for i, s in zip(idx, sep):
                match = frame.detections[int(i)]
                kind = "self" if match.source_id == sources[other] else "other"
                key = (kind != "self", float(s))
                if best is None or key < best[0]:
                    best = (key, kind, float(s), match.magnitude)
        if best is not None:
            trace.stationary_match = best[1]
            trace.stationary_match_arcsec = round(best[2], 3)
            trace.stationary_match_mag = best[3]

    wanted = {s for s in sources if s is not None}
    full = partial = None
    partial_count = 0
    for tracklet, identification in zip(tracklets, identifications):
        ids = {d.detection.source_id for d in tracklet.detections}
        shared = len(ids & wanted)
        if len(wanted) == len(sources) and wanted <= ids:
            if full is None or (
                full[0].status is not TrackletStatus.TRACKLET_BUILT
                and tracklet.status is TrackletStatus.TRACKLET_BUILT
            ):
                full = (tracklet, identification)
        elif shared:
            partial_count += 1
    detected_frames = sum(t.detected for t in traces)
    candidate_frames_count = sum(bool(t.candidate) for t in traces)
    built = full is not None and full[0].status is TrackletStatus.TRACKLET_BUILT
    identified = (
        built
        and full[1].status is IdentificationStatus.KNOWN
        and full[1].best_match is not None
        and full[1].best_match.designation == target.designation
    )
    if detected_frames < len(traces):
        failure = "detection"
    elif candidate_frames_count < len(traces):
        failure = "stationary"
    elif full is None:
        failure = "association"
    elif not built:
        failure = "fit"
    elif not identified:
        failure = "identification"
    else:
        failure = None
    outcome = _target_outcome(target, frames, candidate_frames, tracklets, identifications, config)
    proximity = min_proximity(positions, stars)
    return TargetTrace(
        population=population,
        field_id=field_id,
        designation=target.designation,
        object_class=target.object_class,
        role=target.role,
        v_magnitude=target.v_magnitude,
        rate_arcsec_per_min=round(target.predicted_rate_arcsec_per_min, 4),
        min_pair_displacement_arcsec=round(
            min(angular_distance_arcsec(*a, *b) for a, b in combinations(positions, 2)), 3
        ),
        rate_eligible=target.predicted_rate_arcsec_per_min <= config.max_rate_arcsec_per_min,
        baseline_eligible=baseline_eligible(positions, config.stationary_tolerance_arcsec),
        edge_distance_arcsec=round(
            min(edge_distance_arcsec(ra, dec, m.corners) for (ra, dec), m in zip(positions, metadata)), 1
        ),
        proximity=proximity,
        group=proximity_group(proximity),
        frames=traces,
        detected_frames=detected_frames,
        candidate_frames=candidate_frames_count,
        tracklet_id=full[0].tracklet_id if full else None,
        tracklet_status=full[0].status.value if full else None,
        identification_status=full[1].status.value if full else None,
        best_match=(full[1].best_match.designation if full and full[1].best_match else None),
        partial_tracklets=partial_count,
        recovered=failure is None,
        first_failure=failure,
        as022_recovered=outcome.recovered,
        as022_loss_stage=loss_stage(outcome),
    )


# --- statistics (descriptive; no scipy dependency) ---


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float | None, float | None]:
    if n == 0:
        return None, None
    p = k / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Fisher exact test of [[a, b], [c, d]], two-sided (sum of tables no
    more likely than the observed one)."""
    row1, row2, col1 = a + b, c + d, a + c
    n = row1 + row2

    def probability(x: int) -> float:
        return math.comb(row1, x) * math.comb(row2, col1 - x) / math.comb(n, col1)

    observed = probability(a)
    low, high = max(0, col1 - row2), min(row1, col1)
    return min(
        1.0,
        sum(
            p
            for x in range(low, high + 1)
            if (p := probability(x)) <= observed * (1 + 1e-9)
        ),
    )


def mantel_haenszel(tables: Sequence[tuple[int, int, int, int]]) -> float | None:
    """MH common odds ratio of (zone recovered, zone lost, control
    recovered, control lost) tables; None when undefined."""
    numerator = denominator = 0.0
    for a, b, c, d in tables:
        n = a + b + c + d
        if n == 0 or a + b == 0 or c + d == 0:
            continue
        numerator += a * d / n
        denominator += b * c / n
    if denominator == 0:
        return None if numerator == 0 else math.inf
    return numerator / denominator


class Contrast(BaseModel):
    scope: str
    zone_n: int
    zone_recovered: int
    control_n: int
    control_recovered: int
    fisher_p: float | None
    mh_odds_ratio: float | None
    mh_quadrants: int
    claimed: bool
    verdict: str


def contrast(traces: Sequence[TargetTrace], scope: str) -> Contrast:
    eligible = [
        t for t in traces if t.role == "primary" and t.rate_eligible and t.baseline_eligible
    ]
    zone = [t for t in eligible if t.group == "zone"]
    control = [t for t in eligible if t.group == "control"]
    zk, ck = sum(t.recovered for t in zone), sum(t.recovered for t in control)
    p = (
        fisher_two_sided(zk, len(zone) - zk, ck, len(control) - ck)
        if zone and control
        else None
    )
    tables = []
    for field_id in sorted({t.field_id for t in zone} & {t.field_id for t in control}):
        z = [t for t in zone if t.field_id == field_id]
        c = [t for t in control if t.field_id == field_id]
        zr, cr = sum(t.recovered for t in z), sum(t.recovered for t in c)
        tables.append((zr, len(z) - zr, cr, len(c) - cr))
    mh = mantel_haenszel(tables)
    lower = bool(zone and control and zk / len(zone) < ck / len(control))
    claimed = (
        len(zone) >= MIN_ZONE_TARGETS
        and p is not None
        and p < CLAIM_ALPHA
        and lower
        and (mh is None or mh < 1)
    )
    if claimed:
        verdict = "penalty claimed"
    elif len(zone) < MIN_ZONE_TARGETS:
        verdict = f"not demonstrated: {len(zone)} zone targets < {MIN_ZONE_TARGETS}"
    elif p is None or p >= CLAIM_ALPHA:
        verdict = "not demonstrated: no significant zone/control difference"
    else:
        verdict = "not demonstrated: difference not lower in zone or not in shared quadrants"
    return Contrast(
        scope=scope,
        zone_n=len(zone),
        zone_recovered=zk,
        control_n=len(control),
        control_recovered=ck,
        fisher_p=p,
        mh_odds_ratio=mh,
        mh_quadrants=len(tables),
        claimed=claimed,
        verdict=verdict,
    )


# --- strips ---


class Strip(BaseModel):
    population: str
    field_id: str
    designation: str
    reason: str  # near_recovered | near_lost | control_recovered | control_lost | revisit
    image: str
    first_failure: str | None
    nearest_v10_arcsec: float | None
    note: str


def strip_key(field_id: str, designation: str) -> str:
    return hashlib.sha256(f"{VISUAL_SALT}:{field_id}:{designation}".encode()).hexdigest()


def pick_strips(traces: Sequence[TargetTrace]) -> list[tuple[str, TargetTrace]]:
    eligible = [t for t in traces if t.rate_eligible and t.baseline_eligible]

    def near(t: TargetTrace) -> bool:
        bright = [s for s in class_separations(t.proximity)[:3] if s is not None]
        return bool(bright) and min(bright) < VISUAL_NEAR_ARCSEC

    def ordered(items):
        return sorted(items, key=lambda t: strip_key(t.field_id, t.designation))

    picks = []
    for recovered, label in ((True, "near_recovered"), (False, "near_lost")):
        group = [t for t in eligible if near(t) and t.recovered is recovered]
        picks += [(label, t) for t in ordered(group)[:VISUAL_NEAR_PER_OUTCOME]]
    for recovered, label in ((True, "control_recovered"), (False, "control_lost")):
        group = [t for t in eligible if t.group == "control" and t.recovered is recovered]
        picks += [(label, t) for t in ordered(group)[:VISUAL_CONTROL_PER_OUTCOME]]
    chosen = {(t.field_id, t.designation) for _, t in picks}
    for designation in REVISIT:
        for t in traces:
            if (
                t.population == "R"
                and t.designation == designation
                and (t.field_id, t.designation) not in chosen
            ):
                picks.append(("revisit", t))
    return picks


# --- run ---


class FieldConditions(BaseModel):
    population: str
    field_id: str
    origin: str
    product_ids: list[int]
    filters: list[str]
    minutes_from_first: list[float]
    sources_per_frame: list[int]
    maglimit_per_frame: list[float]
    seeing_per_frame: list[float]
    frame_depth_per_frame: list[float | None]
    stars_per_class: list[int]
    targets: int
    tracklets: int
    tycho_query: str


class TracePart(BaseModel):
    """Traces of one population run (combined later)."""

    generated_at: datetime
    population: str
    fields: list[FieldConditions]
    targets: list[TargetTrace]


class Evidence(BaseModel):
    generated_at: datetime
    preregistration: str
    fields: list[FieldConditions]
    targets: list[TargetTrace]
    contrasts: list[Contrast]
    strips: list[Strip]


def empty_selection() -> Selection:
    return Selection(
        generated_at=datetime.now(timezone.utc),
        preregistration=PREREGISTRATION,
        tycho_query="",
        eligible_stars=[],
        sequences=[],
        skybot_queries=0,
        log=[],
    )


def population_fields(selection: Selection) -> list[tuple[str, ValidationField, str]]:
    """(population, field, origin) in run order: N first, then R."""
    from app.validation.star_contamination import Population

    population = Population.model_validate_json(
        (AS022_REPORT.parent / "as034" / "as034_population.json").read_text()
    )
    return [
        ("N", s.field, f"search {s.search_class} {s.search_star.tycho_id}")
        for s in selection.sequences
    ] + [("R", f.field, f"AS-034 ({f.origin})") for f in population.fields]


def load_field(
    population: str,
    field: ValidationField,
    out_dir: Path,
    stored: dict,
    skybot_name: str = "as035_skybot.json",
):
    """Observations, metadata and full-quadrant SkyBoT fields; R replays
    the AS-022/033/034 snapshots, N queries SkyBoT once and stores it."""
    import json

    from app.models.known_object import KnownObjectField
    from app.validation.data import fetch_frame_metadata, query_skybot_fields

    report = ValidationReport.model_validate_json(AS022_REPORT.read_text())
    frozen = {s.field.field_id: s for s in report.snapshots}
    if field.field_id in frozen:
        snapshot = frozen[field.field_id]
        return snapshot.observations, snapshot.frame_metadata, snapshot.skybot_fields
    observations, metadata = fetch_frame_metadata(field.product_ids)
    as033 = json.loads((AS022_REPORT.parent / "as033" / "as033_skybot.json").read_text())
    as034 = json.loads((AS022_REPORT.parent / "as034" / "as034_skybot.json").read_text())
    if field.field_id in as033:
        raw = as033[field.field_id]
    elif field.field_id in as034:
        raw = as034[field.field_id]
    elif field.field_id in stored:
        raw = stored[field.field_id]
    else:
        raw = [f.model_dump(mode="json") for f in query_skybot_fields(observations, metadata)]
        stored[field.field_id] = raw
        (out_dir / skybot_name).write_text(json.dumps(stored) + "\n")
    return observations, metadata, [KnownObjectField.model_validate(f) for f in raw]


def run_traces(
    selection: Selection,
    population_name: str,
    out_dir: Path,
    only: set[str] | None = None,
    progress: Callable[[str], None] = lambda message: None,
    fields: Sequence[tuple[str, ValidationField, str]] | None = None,
    skybot_name: str = "as035_skybot.json",
) -> TracePart:
    """Trace every target of one population. `fields` / `skybot_name`
    default to AS-035 (N + R, as035_skybot.json); AS-036 passes its own."""
    import json

    import numpy
    from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG as CONFIG
    from app.services.identification_service import match_tracklets_to_known_objects
    from app.services.pipeline_service import build_tracklets_from_frames
    from app.validation.data import load_catalog_frames
    from app.validation.models import TargetSelectionRule
    from app.validation.selection import select_targets
    from app.validation.star_contamination import field_stars

    skybot_path = out_dir / skybot_name
    stored = json.loads(skybot_path.read_text()) if skybot_path.exists() else {}
    conditions: list[FieldConditions] = []
    traces: list[TargetTrace] = []
    for population, field, origin in (
        population_fields(selection) if fields is None else fields
    ):
        if population != population_name or (only is not None and field.field_id not in only):
            continue
        progress(f"{population} {field.field_id}: loading")
        observations, metadata, skybot = load_field(
            population, field, out_dir, stored, skybot_name
        )
        catalogs = load_catalog_frames(observations)
        progress(f"{population} {field.field_id}: pipeline")
        pipeline = build_tracklets_from_frames(catalogs.frames, CONFIG)
        tracklets = pipeline.build.tracklets
        identifications = match_tracklets_to_known_objects(
            tracklets,
            {o.product_id: f for o, f in zip(observations, skybot)},
            CONFIG.identification(),
        ).identifications
        url, stars = field_stars(metadata)
        depths = [
            frame_depth(
                numpy.array([d.magnitude for d in f.detections]),
                numpy.array([d.snr for d in f.detections]),
            )
            for f in catalogs.frames
        ]
        targets = select_targets(field.field_id, metadata, skybot, TargetSelectionRule())
        progress(f"{population} {field.field_id}: tracing {len(targets)} targets")
        for target in targets:
            traces.append(
                trace_target(
                    population, field.field_id, target, catalogs.frames, metadata,
                    pipeline.candidate_frames, tracklets, identifications, CONFIG,
                    stars, catalogs.sharp_by_source_id, depths,
                )
            )
        conditions.append(
            FieldConditions(
                population=population,
                field_id=field.field_id,
                origin=origin,
                product_ids=[o.product_id for o in observations],
                filters=[o.filter_code for o in observations],
                minutes_from_first=[
                    round((o.observed_at - observations[0].observed_at).total_seconds() / 60, 2)
                    for o in observations
                ],
                sources_per_frame=[len(f.detections) for f in catalogs.frames],
                maglimit_per_frame=[m.maglimit for m in metadata],
                seeing_per_frame=[m.seeing_arcsec for m in metadata],
                frame_depth_per_frame=[None if d is None else round(d, 3) for d in depths],
                stars_per_class=[
                    sum(s.mag_class == c for s in stars) for c in range(5)
                ],
                targets=len(targets),
                tracklets=len(tracklets),
                tycho_query=url,
            )
        )
        del pipeline, catalogs, tracklets, identifications

    return TracePart(
        generated_at=datetime.now(timezone.utc),
        population=population_name,
        fields=conditions,
        targets=traces,
    )


def combine(
    parts: Sequence[TracePart],
    out_dir: Path,
    strips: bool = True,
    progress: Callable[[str], None] = lambda message: None,
) -> Evidence:
    """Contrasts and the strip sample over all traced populations."""
    from fastapi.testclient import TestClient

    from app.main import app
    from app.validation.masked import render_strip, strip_geometry, write_png

    conditions = [c for part in parts for c in part.fields]
    traces = [t for part in parts for t in part.targets]
    products = {c.field_id: c.product_ids for c in conditions}
    contrasts = [
        contrast(traces, "N + R"),
        contrast([t for t in traces if t.population == "N"], "N"),
        contrast([t for t in traces if t.population == "R"], "R"),
    ]
    strips_out: list[Strip] = []
    if strips:
        client = TestClient(app)
        (out_dir / "strips").mkdir(parents=True, exist_ok=True)
        for reason, t in pick_strips(traces):
            image = f"strips/{reason}_{t.field_id.split('-')[0]}_{t.designation.replace(' ', '_')}.png"
            progress(f"strip {image}")
            positions = [f.predicted for f in t.frames]
            center, size = strip_geometry(positions)
            write_png(
                out_dir / image,
                render_strip(client, products[t.field_id], center, size, positions, [0, 1, 2]),
            )
            bright = [s for s in class_separations(t.proximity)[:3] if s is not None]
            strips_out.append(
                Strip(
                    population=t.population,
                    field_id=t.field_id,
                    designation=t.designation,
                    reason=reason,
                    image=image,
                    first_failure=t.first_failure,
                    nearest_v10_arcsec=min(bright) if bright else None,
                    note="markers = SkyBoT predicted positions (crosshair: this epoch)",
                )
            )
    return Evidence(
        generated_at=datetime.now(timezone.utc),
        preregistration=PREREGISTRATION,
        fields=conditions,
        targets=traces,
        contrasts=contrasts,
        strips=strips_out,
    )


def _fmt(value, digits: int = 2) -> str:
    return "–" if value is None else f"{value:.{digits}f}"


def _rate(group: Sequence[TargetTrace]) -> str:
    k, n = sum(t.recovered for t in group), len(group)
    if n == 0:
        return "0/0"
    low, high = wilson(k, n)
    return f"{k}/{n} ({100 * k / n:.0f} %, {100 * low:.0f}–{100 * high:.0f})"


def _stages(group: Sequence[TargetTrace]) -> str:
    return " / ".join(str(sum(t.first_failure == s for t in group)) for s in STAGES)


def render_markdown(evidence: Evidence, reviews: Sequence) -> str:
    targets = evidence.targets
    eligible = [t for t in targets if t.rate_eligible and t.baseline_eligible]
    lines = [
        "# AS-035 known-object recovery near bright stars (generated)",
        "",
        f"Generated {evidence.generated_at:%Y-%m-%d %H:%M UTC}. Descriptive only; no "
        "filter, radius, score, rank or threshold. Interpretation: `as035_findings.md`.",
        "",
        f"Pre-registration (commit fa4cd97): {evidence.preregistration}",
        "",
        "Recovery cells: recovered/n (%, Wilson 95 % interval). Stage columns: first "
        "failure detection / stationary / association / fit / identification.",
        "",
        "## Population",
        "",
        "| pop | field | origin | filters | minutes | sources/frame | maglimit | catalog depth "
        "| seeing | stars V<=11 by class | targets | tracklets |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for c in evidence.fields:
        lines.append(
            f"| {c.population} | {c.field_id} | {c.origin} | {'/'.join(c.filters)} "
            f"| {'/'.join(f'{m:.0f}' for m in c.minutes_from_first)} "
            f"| {'/'.join(map(str, c.sources_per_frame))} "
            f"| {'/'.join(f'{m:.1f}' for m in c.maglimit_per_frame)} "
            f"| {'/'.join(_fmt(m, 1) for m in c.frame_depth_per_frame)} "
            f"| {'/'.join(f'{m:.1f}' for m in c.seeing_per_frame)} "
            f"| {'/'.join(map(str, c.stars_per_class))} | {c.targets} | {c.tracklets} |"
        )

    lines += [
        "",
        "## Eligibility strata (temporal baseline and rate separated first)",
        "",
        "| pop | role | targets | too fast | short baseline | eligible | eligible recovered "
        "| short-baseline recovered | short-baseline stages |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for pop in ("N", "R"):
        for role in ("primary", "marginal"):
            group = [t for t in targets if t.population == pop and t.role == role]
            fast = [t for t in group if not t.rate_eligible]
            short = [t for t in group if t.rate_eligible and not t.baseline_eligible]
            ok = [t for t in group if t.rate_eligible and t.baseline_eligible]
            lines.append(
                f"| {pop} | {role} | {len(group)} | {len(fast)} | {len(short)} | {len(ok)} "
                f"| {_rate(ok)} | {_rate(short)} | {_stages(short)} |"
            )

    lines += [
        "",
        "## Recovery by proximity group (rate- and baseline-eligible)",
        "",
        'zone: <120" of V<6, <60" of 6-8, <30" of 8-10; outer: other <240" of V<10; '
        'control: >=480" from V<10 and >=60" from V10-11; intermediate: the rest.',
        "",
        "| scope | role | group | recovered | first-failure stages |",
        "|---|---|---|---|---|",
    ]
    for scope, pops in (("N + R", ("N", "R")), ("N", ("N",)), ("R", ("R",))):
        for role in ("primary", "marginal"):
            for group in ("zone", "outer", "intermediate", "control"):
                members = [
                    t for t in eligible
                    if t.population in pops and t.role == role and t.group == group
                ]
                lines.append(f"| {scope} | {role} | {group} | {_rate(members)} | {_stages(members)} |")

    lines += [
        "",
        "## Pre-registered claim rule (PRIMARY, eligible, zone vs control)",
        "",
        "| scope | zone | control | Fisher p (two-sided) | MH odds ratio (quadrants) | verdict |",
        "|---|---|---|---|---|---|",
    ]
    for c in evidence.contrasts:
        lines.append(
            f"| {c.scope} | {c.zone_recovered}/{c.zone_n} | {c.control_recovered}/{c.control_n} "
            f"| {_fmt(c.fisher_p, 3)} | {_fmt(c.mh_odds_ratio, 2)} ({c.mh_quadrants}) | {c.verdict} |"
        )

    labels = ("V<6", "6<=V<8", "8<=V<10")
    lines += [
        "",
        "## Star magnitude × closest approach (N + R, eligible)",
        "",
        "Each target once per class, in the bin of its closest predicted approach "
        "(E1-E3) to a star of that class.",
        "",
        "| class | closest approach | role | recovered | first-failure stages |",
        "|---|---|---|---|---|",
    ]
    for index, label in enumerate(labels):
        for b in range(len(DISTANCE_EDGES) - 1):
            for role in ("primary", "marginal"):
                members = [
                    t for t in eligible
                    if t.role == role
                    and distance_bin(class_separations(t.proximity)[index]) == b
                ]
                if members:
                    lines.append(
                        f'| {label} | {DISTANCE_EDGES[b]:g}-{DISTANCE_EDGES[b + 1]:g}" | {role} '
                        f"| {_rate(members)} | {_stages(members)} |"
                    )

    lines += [
        "",
        "## Detection-stage losses and local depth (eligible)",
        "",
        "Local margin = local 5σ catalog depth − expected band magnitude, minimum over "
        "the frames where the target was not detected.",
        "",
        "| group | detection losses | locally detectable (margin >= 0) | locally below "
        "| no local depth |",
        "|---|---|---|---|---|",
    ]
    for group in ("zone", "outer", "intermediate", "control"):
        losses = [t for t in eligible if t.group == group and t.first_failure == "detection"]
        margins = []
        for t in losses:
            values = [f.local_margin_mag for f in t.frames if not f.detected]
            margins.append(None if any(v is None for v in values) else min(values))
        lines.append(
            f"| {group} | {len(losses)} | {sum(m is not None and m >= 0 for m in margins)} "
            f"| {sum(m is not None and m < 0 for m in margins)} | {sum(m is None for m in margins)} |"
        )

    near = sorted(
        (
            t for t in targets
            if any(s is not None and s < OUTER_ARCSEC for s in class_separations(t.proximity)[:3])
        ),
        key=lambda t: min(s for s in class_separations(t.proximity)[:3] if s is not None),
    )
    lines += [
        "",
        '## Every target within 240" of a V<10 star (all strata)',
        "",
        '| pop | field | object | role | V | rate ("/min) | min disp. (") | eligible | nearest V<10 (", class) '
        '| group | nearest src (") E1/E2/E3 | candidate | global / local margin (min) '
        "| tracklet | first failure | AS-022 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for t in near:
        sep, cls = min(
            (s, c) for c, s in enumerate(class_separations(t.proximity)[:3]) if s is not None
        )
        local = [f.local_margin_mag for f in t.frames if f.local_margin_mag is not None]
        lines.append(
            f"| {t.population} | {t.field_id} | {t.designation} | {t.role} | {t.v_magnitude:.1f} "
            f"| {t.rate_arcsec_per_min:.2f} | {t.min_pair_displacement_arcsec:.1f} "
            f"| {'yes' if t.rate_eligible and t.baseline_eligible else ('short baseline' if t.rate_eligible else 'too fast')} "
            f"| {sep:.0f}, {labels[cls]} | {t.group} "
            f"| {'/'.join(_fmt(f.nearest_arcsec, 1) for f in t.frames)} "
            f"| {'/'.join('–' if f.candidate is None else ('y' if f.candidate else 'n:' + (f.stationary_match or '?')) for f in t.frames)} "
            f"| {min(f.global_margin_mag for f in t.frames):.1f} / {_fmt(min(local) if local else None, 1)} "
            f"| {t.tracklet_id or '–'} {t.tracklet_status or ''} | {t.first_failure or 'recovered'} | {t.as022_loss_stage} |"
        )

    lines += ["", "## AS-034 revisit", ""]
    for designation in REVISIT:
        for t in (t for t in targets if t.designation == designation):
            lines.append(
                f"- **{t.designation}** ({t.population}, {t.field_id}, {t.role}, V {t.v_magnitude:.1f}): "
                f"rate {t.rate_arcsec_per_min:.3f}\"/min, min pairwise displacement "
                f"{t.min_pair_displacement_arcsec:.2f}\" → "
                f"{'baseline-eligible' if t.baseline_eligible else 'short-baseline stratum'}; "
                f"group {t.group}; nearest source per frame "
                f"{'/'.join(_fmt(f.nearest_arcsec, 2) for f in t.frames)}\"; candidate "
                f"{'/'.join('–' if f.candidate is None else ('y' if f.candidate else 'n:' + (f.stationary_match or '?')) for f in t.frames)}; "
                f"first failure {t.first_failure or 'none (recovered)'}."
            )

    by_key = {(r.field_id, r.tracklet_id): r for r in reviews}
    lines += [
        "",
        "## Visual sample",
        "",
        '| pop | field | object | reason | nearest V<10 (") | first failure | agent label | context | image |',
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for s in evidence.strips:
        r = by_key.get((s.field_id, s.designation))
        lines.append(
            f"| {s.population} | {s.field_id} | {s.designation} | {s.reason} "
            f"| {_fmt(s.nearest_v10_arcsec, 0)} | {s.first_failure or 'recovered'} "
            f"| {r.same_source_all_epochs if r else 'not reviewed'} | {r.context if r else ''} "
            f"| [{s.image}]({s.image}) |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    select = commands.add_parser("select", help="pre-registered star-driven search (N)")
    select.add_argument("--out", type=Path, required=True)
    evidence = commands.add_parser("evidence", help="trace the targets of N or R")
    evidence.add_argument("--selection", type=Path)
    evidence.add_argument("--population", choices=("N", "R"), required=True)
    evidence.add_argument("--out-dir", type=Path, required=True)
    combined = commands.add_parser("combine", help="contrasts and strips over N + R")
    combined.add_argument("--out-dir", type=Path, required=True)
    render = commands.add_parser("render", help="markdown from the evidence JSON")
    render.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "select":
        selection = select_sequences(progress=lambda m: print(m, flush=True))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(selection.model_dump_json(indent=1) + "\n")
        print(
            f"wrote {args.out} ({len(selection.sequences)} sequences, "
            f"{selection.skybot_queries} SkyBoT queries)"
        )
    elif args.command == "evidence":
        selection = (
            Selection.model_validate_json(args.selection.read_text())
            if args.population == "N"
            else empty_selection()  # R needs no search result
        )
        part = run_traces(
            selection,
            args.population,
            args.out_dir,
            progress=lambda m: print(m, flush=True),
        )
        path = args.out_dir / f"as035_traces_{args.population}.json"
        path.write_text(part.model_dump_json() + "\n")
        print(f"wrote {path}")
    elif args.command == "combine":
        parts = [
            TracePart.model_validate_json(
                (args.out_dir / f"as035_traces_{name}.json").read_text()
            )
            for name in ("N", "R")
        ]
        evidence = combine(parts, args.out_dir, progress=lambda m: print(m, flush=True))
        (args.out_dir / "as035_evidence.json").write_text(
            evidence.model_dump_json() + "\n"
        )
        print(f"wrote {args.out_dir}")
    if args.command in ("combine", "render"):
        import json

        from app.validation.masked import VisualReview

        evidence = Evidence.model_validate_json(
            (args.out_dir / "as035_evidence.json").read_text()
        )
        review_path = args.out_dir / "visual_review.json"
        reviews = (
            [VisualReview.model_validate(r) for r in json.loads(review_path.read_text())]
            if review_path.exists()
            else []
        )
        (args.out_dir / "as035_evidence.md").write_text(
            render_markdown(evidence, reviews)
        )


if __name__ == "__main__":
    main()
