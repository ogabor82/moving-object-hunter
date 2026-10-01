"""AS-036: confirmation of the AS-035 near-star PRIMARY recovery penalty.

Confirmatory, not exploratory. AS-035 observed PRIMARY recovery 3/7 in its
pre-registered star zone vs 131/154 in the control, below its own n >= 10
claim rule. AS-036 draws a new, prospectively selected sample (C) with the
AS-035 definitions and a search aimed at PRIMARY passages inside the zone.

Research/characterisation only — no filter, exclusion radius, score, rank,
threshold, rejection rule or candidate policy is derived here. SkyBoT
predictions are not proof of detectability; proximity does not make an
individual candidate false; agent visual labels are not ground truth.

Everything in the PRE-REGISTRATION block below was fixed and committed
before any AS-036 search or recovery outcome was computed.

    python -m app.validation.near_star_confirmation select \\
        --out validation/results/as036/as036_selection.json
    python -m app.validation.near_star_confirmation evidence \\
        --selection validation/results/as036/as036_selection.json \\
        --out-dir validation/results/as036
    python -m app.validation.near_star_confirmation analyse \\
        --selection validation/results/as036/as036_selection.json \\
        --out-dir validation/results/as036
    python -m app.validation.near_star_confirmation render \\
        --out-dir validation/results/as036
"""

import argparse
import hashlib
import math
from collections.abc import Callable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import httpx
from pydantic import BaseModel

from app.validation import known_recovery as kr
from app.validation.bright_stars import (
    SELECTION_MAX_ECLIPTIC_LATITUDE,
    SELECTION_MIN_DEC,
    TychoStar,
    ecliptic_latitude,
    products_available,
    query_tycho,
)
from app.validation.models import ValidationField
from app.validation.presets import AS022_REPORT

# ---------------------------------------------------------------------------
# PRE-REGISTRATION (AS-036, 2026-10-01; committed before any search or
# recovery outcome of this ticket was computed)
# ---------------------------------------------------------------------------

# --- Unchanged AS-035 definitions (imported, not copied) ---
# Sequence rule (temporal baseline): kr.pick_triple — E1 first, E3 last
#   within 150 min, E2 nearest the midpoint with >= 15 min gaps, archived
#   PSF catalogs + science images for all three exposures.
# Target rule: AS-022 TargetSelectionRule from full-quadrant SkyBoT
#   predictions at E1/E2/E3. PRIMARY = V <= faintest frame maglimit - 0.5
#   and position error <= 1" (the established detectability logic).
# Eligibility: predicted rate <= 1.0"/min and every pairwise predicted
#   displacement >= 3.0" (2 x stationary tolerance); everything else is a
#   separate stratum ("too fast" / "short baseline") and never enters the
#   primary comparison.
# Star zone (kr.ZONE_REACH, kr.proximity_group): closest predicted approach
#   (E1-E3) < 120" of a Tycho-2 V < 6 star, < 60" of 6 <= V < 8, < 30" of
#   8 <= V < 10. Stars: Tycho-2 V <= 11 in the footprint circle + 15'.
# Control (same quadrant-nights): >= 480" from every V < 10 star and
#   >= 60" from every V 10-11 star.
# Trace: kr.trace_target — expected position, detection (2.0"),
#   stationary/moving, association, fit, identification; first failure.
# Local catalog depth: descriptive only, never an exclusion (AS-035 O7:
#   it collapses in stellar glare).
# The zone, control, PRIMARY rule and eligibility are NOT widened or
# re-tuned for AS-036.

# --- Confirmatory sample C (new, blind) ---
SELECTION_SALT = "AS-036"
# Search stars: Tycho-2 V < 6 and 6 <= V < 8 (kr.SEARCH_CLASSES), Dec >=
# -25 deg, |ecliptic latitude| <= 10 deg, 2018-03-17 .. 2021-01-01 (AS-033
# window), ordered by SHA-256('AS-036:<tycho id>') per class; classes
# alternate (V<6 star, 6-8 star, ...) until a class is done.
#
# Search expansion (vs AS-035: earliest night only, 120" trigger, any role):
# - per star, the first MAX_NIGHTS_PER_STAR qualifying quadrant-nights
#   (earliest first) that are not AS-035 N or R quadrant-nights are each
#   checked with one SkyBoT cone (300", I41) at the star at E2's
#   mid-exposure; up to MAX_SELECTED_PER_STAR triggering nights per star
#   are selected, earliest first (limits clustering on one star).
# - trigger aligned with the scientific zone and the primary question: an
#   object that is AS-022 PRIMARY (V <= faintest maglimit - 0.5, error
#   <= 1"), rate- and baseline-eligible, inside the footprint at E1/E2/E3
#   (linear extrapolation from SkyBoT rates) and whose closest approach to
#   the search star is inside the zone of the star's class (< 120" for
#   V < 6, < 60" for 6 <= V < 8).
# - a night already selected (by another star) is skipped; a night whose
#   SkyBoT query fails (3 attempts) is logged and not used; a triggering
#   night without archived products is logged and not used.
MAX_NIGHTS_PER_STAR = 20
MAX_SELECTED_PER_STAR = 3
TRIGGER_REACH_ARCSEC = (120.0, 60.0)  # per search class = kr.ZONE_REACH[:2]
# Stopping rule / search budget (per class): a class is done when its
# selected nights hold >= TRIGGERS_PER_CLASS trigger objects, or after
# MAX_STARS_PER_CLASS stars, or once MAX_QUERIES_PER_CLASS SkyBoT cones
# have been spent (checked before each star). Total budget: 600 stars,
# 6000 cones. Exhausting it with too few targets is a valid
# (inconclusive) outcome.
TRIGGERS_PER_CLASS = 15
MAX_STARS_PER_CLASS = 300
MAX_QUERIES_PER_CLASS = 3000

# --- Primary comparison (sample C only) ---
# PRIMARY, rate- and baseline-eligible targets of the C quadrant-nights;
# zone vs control by the AS-035 definition (triggers and by-catch alike:
# every eligible PRIMARY zone target counts, none is dropped or added by
# outcome). Wilson 95 % intervals; Fisher exact two-sided p; Mantel-
# Haenszel odds ratio over quadrant-nights having both zone and control
# targets; Newcombe (hybrid Wilson score) 95 % interval of the recovery
# difference zone - control.
#
# Minimum sample: MIN_ZONE_TARGETS eligible PRIMARY zone targets and
# MIN_CONTROL_TARGETS controls. Rationale: twice AS-035's n >= 10; with
# ~100 controls at 85 % recovery, 20 zone targets give ~78 % power for a
# 30-point penalty (zone 55 %) and ~95 % for the AS-035 point estimate
# (zone ~45 %) at two-sided alpha 0.05 (simulation, 2000 draws).
MIN_ZONE_TARGETS = 20
MIN_CONTROL_TARGETS = 20
CONFIRM_ALPHA = 0.05
# Smallest penalty that matters: 20 percentage points.
NOT_REPRODUCED_MARGIN = 0.20
#
# Decision rule (applied once, to sample C):
# - CONFIRMED: zone n >= 20 and control n >= 20, zone recovery < control
#   recovery, Fisher two-sided p < 0.05, and the MH odds ratio (when
#   defined) < 1.
# - NOT REPRODUCED: both minimums met, not confirmed, and the Newcombe 95 %
#   lower bound of (zone - control) > -0.20 (a penalty of >= 20 points is
#   excluded).
# - INCONCLUSIVE: everything else, including too few targets after the
#   search budget is exhausted.
# Secondary, descriptive, never deciding: AS-035 (N + R) + AS-036 pooled
# (labelled; AS-035 is exploratory and R not blind); trigger objects only;
# per search class; leave-one-search-star-out range; MARGINAL zone/control.

# --- Visual sample (small, deterministic) ---
# SHA-256('AS-036:<field>:<designation>') order among eligible PRIMARY
# targets of C: up to 6 zone recovered, 6 zone lost, 2 control recovered,
# 2 control lost.
VISUAL_ZONE_PER_OUTCOME = 6
VISUAL_CONTROL_PER_OUTCOME = 2

PREREGISTRATION = (
    "AS-036 confirmatory sample C: Tycho-2 V<6 and 6-8 search stars (Dec>=-25, "
    "|beta|<=10, 2018-03-17..2021-01-01), SHA-256('AS-036:<id>') order, alternating "
    "classes; per star the first 20 qualifying quadrant-nights (AS-035 sequence rule: "
    "E1 first, E3 last within 150 min, E2 nearest midpoint with >=15 min gaps, "
    "archived products) not in AS-035 N/R, one SkyBoT cone each; trigger = AS-022 "
    "PRIMARY object (V<=faintest maglimit-0.5, err<=1\"), rate<=1\"/min, every "
    "pairwise displacement >=3\", inside the footprint, closest approach to the star "
    "<120\" (V<6) / <60\" (6-8); <=3 triggering nights per star, earliest first. "
    "Budget per class: stop at >=15 trigger objects, 300 stars or 3000 cones. "
    "Unchanged AS-035 definitions: target rule, eligibility strata, zone (<120\" "
    "V<6, <60\" 6-8, <30\" 8-10), control (>=480\" from V<10, >=60\" from V10-11), "
    "six-stage trace with first failure; local depth descriptive only. Primary "
    "comparison: C only, PRIMARY eligible zone vs control. CONFIRMED: zone n>=20, "
    "control n>=20, zone lower, Fisher two-sided p<0.05, MH OR<1 if defined. NOT "
    "REPRODUCED: minimums met, not confirmed, Newcombe 95% lower bound of zone-"
    "control > -0.20. Otherwise INCONCLUSIVE. Pooled AS-035+036 secondary only. "
    "Strips: SHA-256 order, <=6+6 zone, 2+2 control. No outcome was looked at."
)


# ---------------------------------------------------------------------------
# Selection (C)
# ---------------------------------------------------------------------------


def search_order(stars: Sequence[TychoStar]) -> list[list[TychoStar]]:
    """Eligible search stars per class, in SHA-256('AS-036:<id>') order."""
    classes: list[list[TychoStar]] = [[] for _ in kr.SEARCH_CLASSES]
    for star in stars:
        index = kr.search_class(star.v_mag)
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


def night_key(triple: Sequence[dict[str, str]]) -> tuple[str, str, str, str]:
    first = triple[0]
    return (
        str(int(first["field"])),
        str(int(first["ccdid"])),
        str(int(first["qid"])),
        first["obsdate"][:10],
    )


def zone_triggers(
    star: TychoStar,
    search_class: int,
    triple: Sequence[dict[str, str]],
    objects: Sequence,
    config,
) -> list[kr.TriggerObject]:
    """AS-035 trigger objects narrowed to PRIMARY passages inside the zone
    of the star's class (the AS-035 trigger already enforces the target
    rule's error/marginal cut, rate, baseline and footprint)."""
    from app.validation.models import TargetSelectionRule

    rule = TargetSelectionRule()
    min_maglimit = min(float(r["maglimit"]) for r in triple)
    return [
        t
        for t in kr.trigger_objects(star, triple, objects, config)
        if t.v_magnitude <= min_maglimit - rule.primary_margin_mag
        and t.closest_approach_arcsec < TRIGGER_REACH_ARCSEC[search_class]
    ]


def excluded_nights(as035_selection: Path | None = None) -> set[tuple[str, str, str, str]]:
    """AS-035 N and R quadrant-nights (C must not reuse them)."""
    path = as035_selection or AS022_REPORT.parent / "as035" / "as035_selection.json"
    selection = kr.Selection.model_validate_json(path.read_text())
    keys = set(kr.r_quadrant_nights())
    for sequence in selection.sequences:
        parts = sequence.field.field_id.split("-")
        keys.add((parts[4], parts[5][1:], parts[6][1:], "-".join(parts[1:4])))
    return keys


class NightLog(BaseModel):
    night_index: int
    key: tuple[str, str, str, str]
    outcome: str  # no trigger | selected as <id> | skipped: ... | SkyBoT error | products missing
    triggers: int


class StarLog(BaseModel):
    star: str
    v_mag: float
    search_class: str
    qualifying_nights: int  # after excluding AS-035 nights
    examined_nights: int
    skybot_queries: int
    outcome: str
    nights: list[NightLog]


class ConfirmationSelection(BaseModel):
    generated_at: datetime
    preregistration: str
    tycho_query: str
    eligible_stars: list[int]
    excluded_nights: int
    sequences: list[kr.SelectedSequence]
    stars_examined: list[int]
    skybot_queries: list[int]
    triggers: list[int]
    class_outcome: list[str]
    log: list[StarLog]


def _scan_star(star, excluded, client, metadata, cone, pool):
    """IRSA metadata and the SkyBoT cones of one star's examined nights."""
    rows = metadata(star.ra, star.dec, client)
    nights = [t for t in kr.quadrant_nights(rows) if night_key(t) not in excluded]

    def query(triple):
        try:
            return cone(star, triple[1], client)
        except Exception as exc:  # logged; the rule moves on
            return exc

    examined = nights[:MAX_NIGHTS_PER_STAR]
    return len(nights), examined, list(pool.map(query, examined))


def select_sequences(
    client: httpx.Client | None = None,
    tycho: Callable[..., tuple[str, list[TychoStar]]] = query_tycho,
    metadata: Callable[..., list[dict[str, str]]] = kr.star_metadata,
    cone: Callable[..., list] = kr.skybot_cone,
    available: Callable[..., bool] = products_available,
    excluded: set[tuple[str, str, str, str]] | None = None,
    progress: Callable[[str], None] = lambda message: None,
    star_workers: int = 2,
    cone_workers: int = 4,
    lookahead: int = 4,
) -> ConfirmationSelection:
    """The pre-registered C search. Network calls run concurrently, but the
    rule consumes stars strictly in SHA-256 order, so the result does not
    depend on the concurrency."""
    from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG as CONFIG

    url, stars = tycho(
        {"DE(ICRS)": f">{SELECTION_MIN_DEC - 1}", "VTmag": f"<{kr.SEARCH_QUERY_MAX_VT}"},
        client,
    )
    ordered = search_order(stars)
    static = excluded_nights() if excluded is None else set(excluded)
    used: set[tuple[str, str, str, str]] = set()
    n_classes = len(kr.SEARCH_CLASSES)
    pointer = [0] * n_classes
    queries = [0] * n_classes
    triggers = [0] * n_classes
    selected: list[kr.SelectedSequence] = []
    log: list[StarLog] = []
    futures: dict[tuple[int, int], Future] = {}

    def limit(c: int) -> int:
        return min(MAX_STARS_PER_CLASS, len(ordered[c]))

    def active(c: int) -> bool:
        return (
            triggers[c] < TRIGGERS_PER_CLASS
            and pointer[c] < limit(c)
            and queries[c] < MAX_QUERIES_PER_CLASS
        )

    with ThreadPoolExecutor(cone_workers) as cone_pool, ThreadPoolExecutor(
        star_workers
    ) as star_pool:

        def prefetch(c: int, start: int) -> None:
            for i in range(start, min(start + lookahead, limit(c))):
                if (c, i) not in futures:
                    futures[(c, i)] = star_pool.submit(
                        _scan_star, ordered[c][i], static, client, metadata, cone, cone_pool
                    )

        while any(active(c) for c in range(n_classes)):
            for c in range(n_classes):
                if not active(c):
                    continue
                index = pointer[c]
                star = ordered[c][index]
                pointer[c] += 1
                prefetch(c, index)
                name = kr.class_name(c)
                progress(
                    f"{name} #{index} {star.tycho_id} (V {star.v_mag:.2f}); "
                    f"triggers {triggers}, cones {queries}"
                )
                try:
                    qualifying, examined, results = futures.pop((c, index)).result()
                except Exception as exc:  # metadata error: logged, next star
                    log.append(StarLog(star=star.tycho_id, v_mag=star.v_mag, search_class=name,
                                       qualifying_nights=0, examined_nights=0, skybot_queries=0,
                                       outcome=f"metadata error: {exc}", nights=[]))
                    continue
                queries[c] += len(examined)
                nights_log: list[NightLog] = []
                taken = 0
                for night_index, (triple, objects) in enumerate(zip(examined, results)):
                    key = night_key(triple)
                    if isinstance(objects, Exception):
                        nights_log.append(NightLog(night_index=night_index, key=key,
                                                   outcome=f"SkyBoT error: {str(objects)[:160]}", triggers=0))
                        continue
                    if taken >= MAX_SELECTED_PER_STAR:
                        continue  # examined (cone spent) but no longer selectable
                    if key in used:
                        nights_log.append(NightLog(night_index=night_index, key=key,
                                                   outcome="skipped: already selected", triggers=0))
                        continue
                    found = zone_triggers(star, c, triple, objects, CONFIG)
                    if not found:
                        continue
                    if not available(triple, client):
                        nights_log.append(NightLog(night_index=night_index, key=key,
                                                   outcome="products missing", triggers=len(found)))
                        continue
                    used.add(key)
                    taken += 1
                    triggers[c] += len(found)
                    field_id = f"C{len(selected) + 1}-{key[3]}-{key[0]}-c{key[1]}-q{key[2]}"
                    first = triple[0]
                    selected.append(
                        kr.SelectedSequence(
                            field=ValidationField(
                                field_id=field_id,
                                description=f"AS-036 near-star confirmation: {star.tycho_id} (V {star.v_mag:.2f})",
                                product_ids=[int(r["pid"]) for r in triple],
                                selection_note=PREREGISTRATION,
                            ),
                            search_class=name,
                            search_star=star,
                            night_index=night_index,
                            filters=[r["filtercode"] for r in triple],
                            minutes_from_first=[
                                round((kr._jd(r) - kr._jd(first)) * 1440.0, 2) for r in triple
                            ],
                            trigger=found,
                        )
                    )
                    nights_log.append(NightLog(night_index=night_index, key=key,
                                               outcome=f"selected as {field_id}", triggers=len(found)))
                ids = [n.outcome.split()[-1] for n in nights_log if n.outcome.startswith("selected")]
                log.append(
                    StarLog(
                        star=star.tycho_id,
                        v_mag=star.v_mag,
                        search_class=name,
                        qualifying_nights=qualifying,
                        examined_nights=len(examined),
                        skybot_queries=len(examined),
                        outcome=f"selected {', '.join(ids)}" if ids else "no triggering night",
                        nights=nights_log,
                    )
                )
        for future in futures.values():
            future.cancel()

    outcomes = []
    for c in range(n_classes):
        if triggers[c] >= TRIGGERS_PER_CLASS:
            outcomes.append(f"done: {triggers[c]} trigger objects")
        elif queries[c] >= MAX_QUERIES_PER_CLASS:
            outcomes.append(f"budget exhausted: {queries[c]} cones")
        else:
            outcomes.append(f"budget exhausted: {pointer[c]} of {len(ordered[c])} stars")
    return ConfirmationSelection(
        generated_at=datetime.now(timezone.utc),
        preregistration=PREREGISTRATION,
        tycho_query=url,
        eligible_stars=[len(group) for group in ordered],
        excluded_nights=len(static),
        sequences=selected,
        stars_examined=pointer,
        skybot_queries=queries,
        triggers=triggers,
        class_outcome=outcomes,
        log=log,
    )


# ---------------------------------------------------------------------------
# Evidence and decision (written before any C outcome was computed)
# ---------------------------------------------------------------------------


def confirmation_fields(selection: ConfirmationSelection) -> list[tuple[str, ValidationField, str]]:
    return [
        ("C", s.field, f"search {s.search_class} {s.search_star.tycho_id}")
        for s in selection.sequences
    ]


def run_traces(
    selection: ConfirmationSelection,
    out_dir: Path,
    only: set[str] | None = None,
    progress: Callable[[str], None] = lambda message: None,
) -> kr.TracePart:
    """Stage-by-stage traces of every target of C (AS-035 tracer)."""
    return kr.run_traces(
        kr.empty_selection(),
        "C",
        out_dir,
        only=only,
        progress=progress,
        fields=confirmation_fields(selection),
        skybot_name="as036_skybot.json",
    )


def newcombe(k1: int, n1: int, k2: int, n2: int) -> tuple[float | None, float | None]:
    """Newcombe hybrid score 95 % interval of p1 - p2 (method 10)."""
    if n1 == 0 or n2 == 0:
        return None, None
    l1, u1 = kr.wilson(k1, n1)
    l2, u2 = kr.wilson(k2, n2)
    p1, p2 = k1 / n1, k2 / n2
    d = p1 - p2
    return (
        d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2),
        d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2),
    )


def eligible_primary(traces: Sequence[kr.TargetTrace]) -> list[kr.TargetTrace]:
    return [t for t in traces if t.role == "primary" and t.rate_eligible and t.baseline_eligible]


class Decision(BaseModel):
    scope: str
    deciding: bool  # only the C primary comparison decides
    zone_n: int
    zone_recovered: int
    control_n: int
    control_recovered: int
    difference: float | None  # zone - control recovery
    newcombe_low: float | None
    newcombe_high: float | None
    fisher_p: float | None
    mh_odds_ratio: float | None
    mh_quadrants: int
    classification: str  # CONFIRMED | NOT REPRODUCED | INCONCLUSIVE
    reason: str


def decide(traces: Sequence[kr.TargetTrace], scope: str, deciding: bool = False) -> Decision:
    """The pre-registered decision rule on PRIMARY eligible zone vs control."""
    eligible = eligible_primary(traces)
    zone = [t for t in eligible if t.group == "zone"]
    control = [t for t in eligible if t.group == "control"]
    zk, ck = sum(t.recovered for t in zone), sum(t.recovered for t in control)
    zn, cn = len(zone), len(control)
    p = kr.fisher_two_sided(zk, zn - zk, ck, cn - ck) if zn and cn else None
    tables = []
    for field_id in sorted({t.field_id for t in zone} & {t.field_id for t in control}):
        z = [t for t in zone if t.field_id == field_id]
        c = [t for t in control if t.field_id == field_id]
        zr, cr = sum(t.recovered for t in z), sum(t.recovered for t in c)
        tables.append((zr, len(z) - zr, cr, len(c) - cr))
    mh = kr.mantel_haenszel(tables)
    difference = zk / zn - ck / cn if zn and cn else None
    low, high = newcombe(zk, zn, ck, cn)
    enough = zn >= MIN_ZONE_TARGETS and cn >= MIN_CONTROL_TARGETS
    if not enough:
        classification = "INCONCLUSIVE"
        reason = (
            f"minimum sample not met: zone {zn} (need {MIN_ZONE_TARGETS}), "
            f"control {cn} (need {MIN_CONTROL_TARGETS})"
        )
    elif (
        difference < 0
        and p is not None
        and p < CONFIRM_ALPHA
        and (mh is None or mh < 1)
    ):
        classification = "CONFIRMED"
        reason = "zone lower, Fisher p < 0.05, MH odds ratio < 1 (or undefined)"
    elif low is not None and low > -NOT_REPRODUCED_MARGIN:
        classification = "NOT REPRODUCED"
        reason = (
            f"not confirmed and Newcombe 95 % lower bound {low:+.3f} > "
            f"-{NOT_REPRODUCED_MARGIN:.2f}"
        )
    else:
        classification = "INCONCLUSIVE"
        parts = []
        if difference >= 0:
            parts.append("zone not lower")
        if p is None or p >= CONFIRM_ALPHA:
            parts.append(f"Fisher p {p:.3f} >= 0.05" if p is not None else "no Fisher p")
        if mh is not None and mh >= 1:
            parts.append(f"MH odds ratio {mh:.2f} >= 1")
        parts.append(
            f"a {NOT_REPRODUCED_MARGIN:.0%} penalty not excluded "
            f"(Newcombe lower bound {low:+.3f})"
        )
        reason = "; ".join(parts)
    return Decision(
        scope=scope,
        deciding=deciding,
        zone_n=zn,
        zone_recovered=zk,
        control_n=cn,
        control_recovered=ck,
        difference=difference,
        newcombe_low=low,
        newcombe_high=high,
        fisher_p=p,
        mh_odds_ratio=mh,
        mh_quadrants=len(tables),
        classification=classification,
        reason=reason,
    )


class LeaveOneOut(BaseModel):
    search_star: str
    fields: list[str]
    zone_n: int
    zone_recovered: int
    control_n: int
    control_recovered: int
    fisher_p: float | None


def leave_one_star_out(
    traces: Sequence[kr.TargetTrace], selection: ConfirmationSelection
) -> list[LeaveOneOut]:
    """Descriptive robustness: the C comparison without each search star."""
    by_star: dict[str, list[str]] = {}
    for s in selection.sequences:
        by_star.setdefault(s.search_star.tycho_id, []).append(s.field.field_id)
    rows = []
    for star, fields in by_star.items():
        rest = [t for t in traces if t.field_id not in set(fields)]
        d = decide(rest, f"without {star}")
        rows.append(
            LeaveOneOut(
                search_star=star, fields=fields, zone_n=d.zone_n, zone_recovered=d.zone_recovered,
                control_n=d.control_n, control_recovered=d.control_recovered, fisher_p=d.fisher_p,
            )
        )
    return rows


def trigger_set(selection: ConfirmationSelection) -> set[tuple[str, str]]:
    return {(s.field.field_id, t.designation) for s in selection.sequences for t in s.trigger}


class ConfirmationEvidence(BaseModel):
    generated_at: datetime
    preregistration: str
    fields: list[kr.FieldConditions]
    targets: list[kr.TargetTrace]
    triggers: list[tuple[str, str]]  # (field, designation)
    search_star_by_field: dict[str, str]
    search_class_by_field: dict[str, str]
    primary: Decision  # the deciding comparison: C only
    secondary: list[Decision]  # descriptive only
    leave_one_out: list[LeaveOneOut]
    strips: list[kr.Strip]


def strip_key(field_id: str, designation: str) -> str:
    return hashlib.sha256(f"{SELECTION_SALT}:{field_id}:{designation}".encode()).hexdigest()


def pick_strips(traces: Sequence[kr.TargetTrace]) -> list[tuple[str, kr.TargetTrace]]:
    eligible = eligible_primary(traces)
    picks = []
    for group, per in (("zone", VISUAL_ZONE_PER_OUTCOME), ("control", VISUAL_CONTROL_PER_OUTCOME)):
        for recovered, outcome in ((True, "recovered"), (False, "lost")):
            members = sorted(
                (t for t in eligible if t.group == group and t.recovered is recovered),
                key=lambda t: strip_key(t.field_id, t.designation),
            )
            picks += [(f"{group}_{outcome}", t) for t in members[:per]]
    return picks


def analyse(
    part: kr.TracePart,
    selection: ConfirmationSelection,
    prior: Sequence[kr.TracePart] = (),
    out_dir: Path | None = None,
    progress: Callable[[str], None] = lambda message: None,
) -> ConfirmationEvidence:
    """Decision on C, secondary descriptive contrasts, strips."""
    traces = part.targets
    triggers = trigger_set(selection)
    star_by_field = {s.field.field_id: s.search_star.tycho_id for s in selection.sequences}
    class_by_field = {s.field.field_id: s.search_class for s in selection.sequences}
    secondary = [
        decide([t for t in traces if (t.field_id, t.designation) in triggers or t.group == "control"],
               "C, trigger objects only (vs all C controls)"),
    ]
    for name in sorted(set(class_by_field.values())):
        secondary.append(
            decide([t for t in traces if class_by_field[t.field_id] == name], f"C, search class {name}")
        )
    prior_traces = [t for p in prior for t in p.targets]
    if prior_traces:
        secondary.append(decide(prior_traces, "AS-035 alone (N + R; exploratory, R not blind)"))
        secondary.append(
            decide(list(traces) + prior_traces, "POOLED AS-035 (N + R) + AS-036 C — secondary, not deciding")
        )
    strips: list[kr.Strip] = []
    if out_dir is not None:
        from fastapi.testclient import TestClient

        from app.main import app
        from app.validation.masked import render_strip, strip_geometry, write_png

        products = {c.field_id: c.product_ids for c in part.fields}
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
            bright = [s for s in kr.class_separations(t.proximity)[:3] if s is not None]
            strips.append(
                kr.Strip(
                    population=t.population, field_id=t.field_id, designation=t.designation,
                    reason=reason, image=image, first_failure=t.first_failure,
                    nearest_v10_arcsec=min(bright) if bright else None,
                    note="markers = SkyBoT predicted positions (crosshair: this epoch)",
                )
            )
    return ConfirmationEvidence(
        generated_at=datetime.now(timezone.utc),
        preregistration=PREREGISTRATION,
        fields=part.fields,
        targets=traces,
        triggers=sorted(triggers),
        search_star_by_field=star_by_field,
        search_class_by_field=class_by_field,
        primary=decide(traces, "AS-036 C (confirmatory, deciding)", deciding=True),
        secondary=secondary,
        leave_one_out=leave_one_star_out(traces, selection),
        strips=strips,
    )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

_fmt = kr._fmt
_rate = kr._rate
_stages = kr._stages
CLASS_LABELS = ("V<6", "6<=V<8", "8<=V<10")


def zone_reason(t: kr.TargetTrace) -> tuple[int, float]:
    """(class, separation) that puts a target in the zone, brightest first."""
    reach = [r for _, r in kr.ZONE_REACH]
    for index, separation in enumerate(kr.class_separations(t.proximity)[:3]):
        if separation is not None and separation < reach[index]:
            return index, separation
    raise ValueError("not a zone target")


def _decision_row(d: Decision) -> str:
    return (
        f"| {d.scope} | {d.zone_recovered}/{d.zone_n} ({_pct(d.zone_recovered, d.zone_n)}) "
        f"| {d.control_recovered}/{d.control_n} ({_pct(d.control_recovered, d.control_n)}) "
        f"| {_fmt(d.difference, 3)} [{_fmt(d.newcombe_low, 3)}, {_fmt(d.newcombe_high, 3)}] "
        f"| {_fmt(d.fisher_p, 4)} | {_fmt(d.mh_odds_ratio, 2)} ({d.mh_quadrants}) "
        f"| {d.classification if d.deciding else '(descriptive) ' + d.classification} | {d.reason} |"
    )


def _pct(k: int, n: int) -> str:
    if n == 0:
        return "–"
    low, high = kr.wilson(k, n)
    return f"{100 * k / n:.0f} %, {100 * low:.0f}–{100 * high:.0f}"


def _candidate(t: kr.TargetTrace) -> str:
    return "/".join(
        "–" if f.candidate is None else ("y" if f.candidate else "n:" + (f.stationary_match or "?"))
        for f in t.frames
    )


def render_markdown(
    evidence: ConfirmationEvidence, selection: ConfirmationSelection, reviews: Sequence = ()
) -> str:
    targets = evidence.targets
    triggers = {tuple(x) for x in evidence.triggers}
    eligible = [t for t in targets if t.rate_eligible and t.baseline_eligible]
    d = evidence.primary
    lines = [
        "# AS-036 near-star PRIMARY recovery confirmation (generated)",
        "",
        f"Generated {evidence.generated_at:%Y-%m-%d %H:%M UTC}. Descriptive only; no filter, "
        "radius, score, rank or threshold. Interpretation: `as036_findings.md`.",
        "",
        f"Pre-registration: {evidence.preregistration}",
        "",
        "## Decision (pre-registered rule, sample C only)",
        "",
        f"**{d.classification}** — {d.reason}.",
        "",
        "| scope | zone recovered | control recovered | zone − control [Newcombe 95 %] "
        "| Fisher p | MH OR (quadrants) | classification | reason |",
        "|---|---|---|---|---|---|---|---|",
        _decision_row(d),
        "",
        "## Secondary (descriptive, never deciding)",
        "",
        "| scope | zone recovered | control recovered | zone − control [Newcombe 95 %] "
        "| Fisher p | MH OR (quadrants) | classification | reason |",
        "|---|---|---|---|---|---|---|---|",
        *(_decision_row(s) for s in evidence.secondary),
        "",
        "## Search",
        "",
        f"Eligible search stars per class: {selection.eligible_stars}; stars examined "
        f"{selection.stars_examined}; SkyBoT cones {selection.skybot_queries}; trigger "
        f"objects {selection.triggers}; class outcome {selection.class_outcome}; AS-035 "
        f"quadrant-nights excluded: {selection.excluded_nights}; selected quadrant-nights "
        f"{len(selection.sequences)}.",
        "",
        "| field | search star | class | V | night index | filters | minutes | trigger objects "
        '(V, closest ") |',
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in selection.sequences:
        lines.append(
            f"| {s.field.field_id} | {s.search_star.tycho_id} | {s.search_class} "
            f"| {s.search_star.v_mag:.2f} | {s.night_index} | {'/'.join(s.filters)} "
            f"| {'/'.join(f'{m:.0f}' for m in s.minutes_from_first)} "
            f"| {', '.join(f'{t.designation} ({t.v_magnitude:.1f}, {t.closest_approach_arcsec:.0f})' for t in s.trigger)} |"
        )

    lines += [
        "",
        "## Population",
        "",
        "| field | filters | minutes | sources/frame | maglimit | catalog depth | seeing "
        "| stars V<=11 by class | targets | tracklets |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for c in evidence.fields:
        lines.append(
            f"| {c.field_id} | {'/'.join(c.filters)} "
            f"| {'/'.join(f'{m:.0f}' for m in c.minutes_from_first)} "
            f"| {'/'.join(map(str, c.sources_per_frame))} "
            f"| {'/'.join(f'{m:.1f}' for m in c.maglimit_per_frame)} "
            f"| {'/'.join(_fmt(m, 1) for m in c.frame_depth_per_frame)} "
            f"| {'/'.join(f'{m:.1f}' for m in c.seeing_per_frame)} "
            f"| {'/'.join(map(str, c.stars_per_class))} | {c.targets} | {c.tracklets} |"
        )

    lines += [
        "",
        "## Eligibility strata (short baseline and rate separated first)",
        "",
        "Stage columns: first failure detection / stationary / association / fit / identification.",
        "",
        "| role | group | targets | too fast | short baseline | eligible | eligible recovered "
        "| eligible stages | short-baseline recovered | short-baseline stages |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for role in ("primary", "marginal"):
        for group in ("zone", "outer", "intermediate", "control"):
            members = [t for t in targets if t.role == role and t.group == group]
            fast = [t for t in members if not t.rate_eligible]
            short = [t for t in members if t.rate_eligible and not t.baseline_eligible]
            ok = [t for t in members if t.rate_eligible and t.baseline_eligible]
            lines.append(
                f"| {role} | {group} | {len(members)} | {len(fast)} | {len(short)} | {len(ok)} "
                f"| {_rate(ok)} | {_stages(ok)} | {_rate(short)} | {_stages(short)} |"
            )

    zone = sorted(
        (t for t in eligible if t.role == "primary" and t.group == "zone"),
        key=lambda t: (zone_reason(t), t.field_id, t.designation),
    )
    lines += [
        "",
        "## Zone composition (PRIMARY, eligible)",
        "",
        "Class and closest approach of the star that puts the target in the zone "
        "(brightest qualifying class).",
        "",
        "| class | closest approach | targets | of which triggers | recovered | stages |",
        "|---|---|---|---|---|---|",
    ]
    for index, label in enumerate(CLASS_LABELS):
        for b in range(len(kr.DISTANCE_EDGES) - 1):
            members = [
                t for t in zone
                if zone_reason(t)[0] == index and kr.distance_bin(zone_reason(t)[1]) == b
            ]
            if members:
                lines.append(
                    f'| {label} | {kr.DISTANCE_EDGES[b]:g}-{kr.DISTANCE_EDGES[b + 1]:g}" | {len(members)} '
                    f"| {sum((t.field_id, t.designation) in triggers for t in members)} "
                    f"| {_rate(members)} | {_stages(members)} |"
                )

    def target_rows(group: Sequence[kr.TargetTrace], with_star: bool) -> list[str]:
        rows = []
        for t in group:
            star = ""
            if with_star:
                index, separation = zone_reason(t)
                star = f"{separation:.0f}, {CLASS_LABELS[index]} | "
            local = [f.local_margin_mag for f in t.frames if f.local_margin_mag is not None]
            bits = "/".join(
                "–" if f.source_mask_bits is None else str(f.source_mask_bits) for f in t.frames
            )
            rows.append(
                f"| {t.field_id} | {t.designation} | {'trigger' if (t.field_id, t.designation) in triggers else 'by-catch'} "
                f"| {t.v_magnitude:.1f} | {t.rate_arcsec_per_min:.2f} | {t.min_pair_displacement_arcsec:.1f} | {star}"
                f"{'/'.join(_fmt(f.nearest_arcsec, 1) for f in t.frames)} | {bits} | {_candidate(t)} "
                f"| {min(f.global_margin_mag for f in t.frames):.1f} / {_fmt(min(local) if local else None, 1)} "
                f"| {t.tracklet_id or '–'} {t.tracklet_status or ''} "
                f"| {'RECOVERED' if t.recovered else 'lost'} | {t.first_failure or '–'} |"
            )
        return rows

    head = (
        '| field | object | origin | V | rate ("/min) | min disp. (") | {star}nearest src (") '
        "E1/E2/E3 | mask bits | candidate | global / local margin (min) | tracklet | outcome "
        "| first failure |"
    )
    lines += [
        "",
        "## Every eligible PRIMARY zone target (stage-by-stage)",
        "",
        head.format(star='star (", class) | '),
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        *target_rows(zone, True),
    ]
    for title, members in (
        ("Every eligible PRIMARY control target", [t for t in eligible if t.role == "primary" and t.group == "control"]),
        ("Every eligible PRIMARY outer / intermediate target", [t for t in eligible if t.role == "primary" and t.group in ("outer", "intermediate")]),
        ("Every non-eligible PRIMARY target (short baseline / too fast; excluded from the comparison)", [t for t in targets if t.role == "primary" and not (t.rate_eligible and t.baseline_eligible)]),
    ):
        lines += [
            "",
            f"## {title}",
            "",
            head.format(star=""),
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
            *target_rows(sorted(members, key=lambda t: (t.field_id, t.designation)), False),
        ]

    lines += [
        "",
        "## Detection-stage losses and local depth (eligible PRIMARY; descriptive)",
        "",
        "| group | detection losses | locally detectable (margin >= 0) | locally below | no local depth |",
        "|---|---|---|---|---|",
    ]
    for group in ("zone", "outer", "intermediate", "control"):
        losses = [
            t for t in eligible
            if t.role == "primary" and t.group == group and t.first_failure == "detection"
        ]
        margins = []
        for t in losses:
            values = [f.local_margin_mag for f in t.frames if not f.detected]
            margins.append(None if any(v is None for v in values) else min(values))
        lines.append(
            f"| {group} | {len(losses)} | {sum(m is not None and m >= 0 for m in margins)} "
            f"| {sum(m is not None and m < 0 for m in margins)} | {sum(m is None for m in margins)} |"
        )

    lines += [
        "",
        "## Leave one search star out (C, descriptive)",
        "",
        "| without | fields | zone | control | Fisher p |",
        "|---|---|---|---|---|",
    ]
    for r in evidence.leave_one_out:
        lines.append(
            f"| {r.search_star} | {', '.join(f.split('-')[0] for f in r.fields)} "
            f"| {r.zone_recovered}/{r.zone_n} | {r.control_recovered}/{r.control_n} | {_fmt(r.fisher_p, 4)} |"
        )

    by_key = {(r.field_id, r.tracklet_id): r for r in reviews}
    lines += [
        "",
        "## Visual sample",
        "",
        '| field | object | reason | nearest V<10 (") | first failure | agent label | context | image |',
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in evidence.strips:
        r = by_key.get((s.field_id, s.designation))
        lines.append(
            f"| {s.field_id} | {s.designation} | {s.reason} | {_fmt(s.nearest_v10_arcsec, 0)} "
            f"| {s.first_failure or 'recovered'} | {r.same_source_all_epochs if r else 'not reviewed'} "
            f"| {r.context if r else ''} | [{s.image}]({s.image}) |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    import json

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    select = commands.add_parser("select", help="pre-registered search for sample C")
    select.add_argument("--out", type=Path, required=True)
    evidence = commands.add_parser("evidence", help="trace every target of C")
    evidence.add_argument("--selection", type=Path, required=True)
    evidence.add_argument("--out-dir", type=Path, required=True)
    analysed = commands.add_parser("analyse", help="decision, secondary contrasts, strips")
    analysed.add_argument("--selection", type=Path, required=True)
    analysed.add_argument("--out-dir", type=Path, required=True)
    render = commands.add_parser("render", help="markdown from the evidence JSON")
    render.add_argument("--selection", type=Path, required=True)
    render.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "select":
        with httpx.Client() as client:
            selection = select_sequences(client=client, progress=lambda m: print(m, flush=True))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(selection.model_dump_json(indent=1) + "\n")
        print(
            f"wrote {args.out} ({len(selection.sequences)} sequences, cones "
            f"{selection.skybot_queries}, triggers {selection.triggers})"
        )
        return
    selection = ConfirmationSelection.model_validate_json(args.selection.read_text())
    if args.command == "evidence":
        args.out_dir.mkdir(parents=True, exist_ok=True)
        part = run_traces(selection, args.out_dir, progress=lambda m: print(m, flush=True))
        path = args.out_dir / "as036_traces_C.json"
        path.write_text(part.model_dump_json() + "\n")
        print(f"wrote {path}")
        return
    if args.command == "analyse":
        part = kr.TracePart.model_validate_json((args.out_dir / "as036_traces_C.json").read_text())
        as035 = AS022_REPORT.parent / "as035"
        prior = [
            kr.TracePart.model_validate_json((as035 / f"as035_traces_{n}.json").read_text())
            for n in ("N", "R")
        ]
        result = analyse(part, selection, prior, args.out_dir, progress=lambda m: print(m, flush=True))
        (args.out_dir / "as036_evidence.json").write_text(result.model_dump_json() + "\n")
        print(f"decision: {result.primary.classification} — {result.primary.reason}")
    from app.validation.masked import VisualReview

    result = ConfirmationEvidence.model_validate_json((args.out_dir / "as036_evidence.json").read_text())
    review_path = args.out_dir / "visual_review.json"
    reviews = (
        [VisualReview.model_validate(r) for r in json.loads(review_path.read_text())]
        if review_path.exists()
        else []
    )
    (args.out_dir / "as036_evidence.md").write_text(render_markdown(result, selection, reviews))
    print(f"wrote {args.out_dir / 'as036_evidence.md'}")


if __name__ == "__main__":
    main()
