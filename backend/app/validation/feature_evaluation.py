"""AS-038: stage-1 candidate feature evaluation (development split only).

Executes stage 1 of the AS-037 pre-registration
(validation/results/as037/as037_preregistration.md, PRE-REGISTRATION block
of app/validation/ranking_design.py) unchanged: for every built tracklet of
the 56 development quadrant-nights, the candidate quality features, the
three pre-registered derived features, context columns and the
pre-registered label; then, per candidate feature in its pre-registered
direction, within-field AUC and recall@5 % with group-bootstrap intervals,
overall and per stratum, missingness and Spearman redundancy on
development background; then the stage-1 gate and the frozen feature list
for AS-039.

No ranker, combined score, weight, threshold, filter or rejection rule is
built here, and the validation split is never loaded: every quadrant-night
passes `ranking_design.require_split(manifest, field_id,
STAGE_FEATURE_EVALUATION)` before anything of it is read, and validation
rows of shared input files (AS-036 traces, SkyBoT snapshot) are dropped by
field id before use.

    python -m app.validation.feature_evaluation table \\
        --out-dir validation/results/as038          # IRSA + VizieR, ~1.5 h
    python -m app.validation.feature_evaluation evaluate \\
        --out-dir validation/results/as038          # offline, from the table
"""

import argparse
import csv
import gzip
import json
import math
import statistics
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from app.validation import ranking_design as rd

# ---------------------------------------------------------------------------
# IMPLEMENTATION DECISIONS (AS-038, 2026-10-02; fixed and committed before
# any development feature table or feature outcome existed). They fill in
# details AS-037 does not spell out; none changes an AS-037 rule.
# ---------------------------------------------------------------------------

STAGE = rd.STAGE_FEATURE_EVALUATION
MANIFEST_FILE = "validation/results/as037/as037_manifest.json"

# D1 SkyBoT is replayed only (AS-022 report, as033/as034/as035/as036
# snapshots). A quadrant-night without a stored snapshot raises; it is
# never queried live (a live query could differ from the AS-035/036 traces
# the labels come from).
SKYBOT_SNAPSHOTS = (
    "validation/results/as033/as033_skybot.json",
    "validation/results/as034/as034_skybot.json",
    "validation/results/as035/as035_skybot.json",
    "validation/results/as036/as036_skybot.json",
)

# D2 Eligible targets (POSITIVE rule) of a quadrant-night: its AS-035/036
# trace rows with rate_eligible and baseline_eligible, role primary /
# marginal. The label itself is ranking_design.label_tracklet, unchanged.

# D3 Missing feature values (magnitude_range_sigma when both errors are 0,
# magnitude_chi2 when an error is not positive, sharp_abs_max unless sharp
# is complete) rank AFTER every present value of the quadrant-night (score
# -inf after orientation; missing-vs-missing is a tie, counted half). This
# is the conservative choice: a missing value never helps a positive.

# D4 Spearman redundancy: rank correlation of the raw feature values over
# ALL development background tracklets pooled, pairwise complete (average
# ranks for ties). The per-quadrant-night median Spearman is reported,
# descriptive only. The AS-037 drop rule is applied literally pairwise:
# a passing feature is dropped when some other passing feature with a
# higher overall point AUC has |Spearman| > 0.90 with it (also when that
# partner is itself dropped). Equal AUCs: the feature later in
# CANDIDATE_FEATURES order is dropped.

# D5 Positive strata come from the AS-035/036 trace of the target (not
# from the tracklet): role, proximity group (zone / outer / intermediate /
# control; the gate's near-star stratum is zone + outer), minimum global
# depth margin, predicted rate. Quadrant-night strata: crowding (mean
# sources per frame of the run), single / mixed filter, population R / N /
# C. Mask state: masked_detection_count of the object's positive tracklet
# with the fewest masked detections (0 unmasked, 3 all, else partial).

# D6 Bootstrap: ranking_design.group_bootstrap (2000 resamples over
# independence groups, seed SHA-256('AS-037:<label>')), label
# 'AS-038/<feature>/<statistic>[/<stratum>]'.

# D7 The gate (AS-037 section 6, ranking_design constants) is applied
# mechanically: overall AUC 95 % lower bound > AUC_GATE_LOWER (strict);
# MARGINAL point AUC >= 0.5; zone + outer point AUC >= 0.5; missing share
# over all ranked (built) development tracklets <= MAX_MISSING. A feature
# whose overall AUC is below 0.5 is reported as reversed and fails; its
# direction is never flipped.

# D8 Counterexamples (reported, never acted on): quadrant-nights with
# >= COUNTEREXAMPLE_MIN_POSITIVES positives and point AUC < 0.5; every
# reported stratum with point AUC < 0.5; for frozen features, every
# positive object ranked in the bottom half (q > 0.5) of its background.
COUNTEREXAMPLE_MIN_POSITIVES = 3

# D9 Sensitivity (descriptive, never deciding): (a) background tracklets
# sharing a detection with a positive tracklet removed; (b) designation
# 105890 (target in both splits) removed.
CROSS_SPLIT_DESIGNATION = "105890"

DEPTH_BINS = ((-math.inf, 0.5, "<0.5"), (0.5, 1.5, "0.5-1.5"), (1.5, math.inf, ">=1.5"))
CROWDING_BINS = ((0, 20_000, "<20k"), (20_000, 80_000, "20-80k"), (80_000, math.inf, ">=80k"))
SPEED_BINS = ((0.0, 0.25, "<0.25"), (0.25, 0.5, "0.25-0.5"), (0.5, math.inf, "0.5-1.0"))

# Columns a ranker may ever see: exactly the candidate features. Everything
# else in the table (label, designation, role, proximity, speed, PA) is for
# evaluation and stratification only.
RANKER_INPUT_COLUMNS = tuple(rd.CANDIDATE_FEATURES)
IDENTITY_COLUMNS = ("label", "eval_designation", "eval_role", "eval_target_group")
CONTEXT_COLUMNS = (
    "ctx_sep_v_lt4",
    "ctx_sep_v4_6",
    "ctx_sep_v6_8",
    "ctx_sep_v8_10",
    "ctx_sep_v10_11",
    "ctx_nearest_star_arcsec",
    "ctx_nearest_star_v",
    "ctx_proximity_group",
    "ctx_angular_velocity_arcsec_per_min",
    "ctx_position_angle_deg",
)
TABLE_COLUMNS = (
    "field_id",
    "population",
    "group",
    "night",
    "tracklet_id",
    *IDENTITY_COLUMNS,
    *RANKER_INPUT_COLUMNS,
    "sharp_availability",
    "mask_bits_union",
    "shares_detection_with_positive",
    *CONTEXT_COLUMNS,
)

FIELD_ATTEMPTS = 4
TABLE_FILE = "as038_feature_table.csv.gz"
FIELDS_FILE = "as038_fields.json"
RESULTS_FILE = "as038_evaluation.json"
REPORT_FILE = "as038_evaluation.md"
FROZEN_FILE = "as038_frozen_features.json"


# ---------------------------------------------------------------------------
# Split-guarded inputs
# ---------------------------------------------------------------------------


def load_manifest(root: Path) -> dict:
    return json.loads((root / MANIFEST_FILE).read_text())


def development_nights(manifest: Mapping) -> list[dict]:
    """Development quadrant-nights in manifest order, each passed through
    the AS-037 split guard."""
    nights = [q for q in manifest["quadrant_nights"] if q["split"] == rd.DEVELOPMENT]
    for q in nights:
        rd.require_split(manifest, q["field_id"], STAGE)
    return nights


def load_development_traces(root: Path, manifest: Mapping) -> dict[str, list[dict]]:
    """Trace rows of development quadrant-nights only, by field id. Rows of
    any other quadrant-night are dropped by id before use."""
    allowed = {q["field_id"] for q in development_nights(manifest)}
    by_field: dict[str, list[dict]] = defaultdict(list)
    for name in ("R", "N", "C"):
        for t in json.loads((root / rd.TRACE_FILES[name]).read_text())["targets"]:
            if t["field_id"] in allowed:
                by_field[t["field_id"]].append(t)
    return dict(by_field)


def eligible_targets(traces: Sequence[Mapping]) -> dict[str, str]:
    """designation -> role of the rate- and baseline-eligible targets (D2)."""
    return {
        t["designation"]: t["role"]
        for t in traces
        if t["rate_eligible"] and t["baseline_eligible"]
    }


def replay_field(root: Path, manifest: Mapping, field_id: str, product_ids, client=None):
    """Observations, frame metadata and SkyBoT fields; SkyBoT replay only."""
    from app.models.known_object import KnownObjectField
    from app.validation.data import fetch_frame_metadata
    from app.validation.presets import AS022_REPORT
    from app.validation.runner import ValidationReport

    rd.require_split(manifest, field_id, STAGE)
    report = ValidationReport.model_validate_json(AS022_REPORT.read_text())
    frozen = {s.field.field_id: s for s in report.snapshots}
    if field_id in frozen:
        s = frozen[field_id]
        return s.observations, s.frame_metadata, s.skybot_fields
    raw = None
    for path in SKYBOT_SNAPSHOTS:
        stored = json.loads((root / path).read_text())
        if field_id in stored:
            raw = stored[field_id]
            break
    if raw is None:
        raise RuntimeError(f"{field_id}: no stored SkyBoT snapshot (never queried live)")
    observations, metadata = fetch_frame_metadata(list(product_ids), client)
    return observations, metadata, [KnownObjectField.model_validate(f) for f in raw]


# ---------------------------------------------------------------------------
# Derived features (AS-037 definitions)
# ---------------------------------------------------------------------------


def sharp_abs_max(sharp_values: Sequence[float | None], complete: bool) -> float | None:
    """max |sharp| over the detections; None unless sharp is complete."""
    if not complete or not sharp_values:
        return None
    return max(abs(v) for v in sharp_values)


def shared_detection_tracklets(detections_by_tracklet: Mapping[str, Sequence[str]]) -> dict[str, int]:
    """Per built tracklet: number of OTHER built tracklets that share at
    least one detection (source id) with it (AS-032 O3)."""
    owners: dict[str, set[str]] = defaultdict(set)
    for tracklet_id, sources in detections_by_tracklet.items():
        for source in sources:
            owners[source].add(tracklet_id)
    return {
        tracklet_id: len(set().union(*(owners[s] for s in sources)) - {tracklet_id})
        for tracklet_id, sources in detections_by_tracklet.items()
    }


# ---------------------------------------------------------------------------
# Table (network: IRSA PSF catalogs + metadata, VizieR Tycho-2)
# ---------------------------------------------------------------------------


def _round(value: float | None, digits: int = 6) -> float | None:
    return None if value is None else round(float(value), digits)


def field_rows(root: Path, manifest: Mapping, night: Mapping, traces: Sequence[Mapping]) -> tuple[list[dict], dict]:
    """Run the unchanged pipeline on one development quadrant-night and
    return its built-tracklet rows and field conditions."""
    from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG as CONFIG
    from app.models.quality import SharpAvailability
    from app.models.tracklet import TrackletStatus
    from app.services.identification_service import match_tracklets_to_known_objects
    from app.services.pipeline_service import build_tracklets_from_frames
    from app.services.quality_service import extract_quality_features
    from app.validation import known_recovery as kr
    from app.validation.data import load_catalog_frames
    from app.validation.star_contamination import field_stars, min_proximity

    field_id = night["field_id"]
    rd.require_split(manifest, field_id, STAGE)
    observations, metadata, skybot = replay_field(root, manifest, field_id, night["product_ids"])
    catalogs = load_catalog_frames(observations)
    pipeline = build_tracklets_from_frames(catalogs.frames, CONFIG)
    tracklets = pipeline.build.tracklets
    identifications = match_tracklets_to_known_objects(
        tracklets, {o.product_id: f for o, f in zip(observations, skybot)}, CONFIG.identification()
    ).identifications
    _, stars = field_stars(metadata)
    targets = eligible_targets(traces)
    trace_by_designation = {t["designation"]: t for t in traces}

    built = [
        (t, i) for t, i in zip(tracklets, identifications) if t.status is TrackletStatus.TRACKLET_BUILT
    ]
    shared = shared_detection_tracklets(
        {t.tracklet_id: [d.detection.source_id for d in t.detections] for t, _ in built}
    )
    rows = []
    for tracklet, identification in built:
        best = identification.best_match.designation if identification.best_match else None
        label = rd.label_tracklet("built", identification.status.value, best, targets)
        features = extract_quality_features(tracklet, catalogs.sharp_by_source_id)
        detections = [d.detection for d in tracklet.detections]
        complete = features.sharp_availability is SharpAvailability.COMPLETE
        proximity = min_proximity([(d.ra, d.dec) for d in detections], stars)
        seps = proximity.separation_by_class
        trace = trace_by_designation.get(best or "") if label == rd.POSITIVE else None
        rows.append(
            {
                "field_id": field_id,
                "population": night["population"],
                "group": night["group"],
                "night": night["night"],
                "tracklet_id": tracklet.tracklet_id,
                "label": label,
                "eval_designation": best if label in (rd.POSITIVE, rd.AUXILIARY) else None,
                "eval_role": targets.get(best or "") if label == rd.POSITIVE else None,
                "eval_target_group": trace["group"] if trace else None,
                "min_snr": _round(features.min_snr),
                "median_snr": _round(features.median_snr),
                "fit_rms_residual_arcsec": _round(features.fit_rms_residual_arcsec),
                "fit_max_residual_arcsec": _round(features.fit_max_residual_arcsec),
                "magnitude_range_mag": _round(features.magnitude_range_mag),
                "magnitude_range_sigma": _round(features.magnitude_range_sigma),
                "magnitude_chi2": _round(
                    rd.magnitude_chi2(
                        [d.magnitude for d in detections], [d.magnitude_error for d in detections]
                    )
                ),
                "flagged_detection_count": features.flagged_detection_count,
                "masked_detection_count": features.masked_detection_count,
                "edge_detection_count": features.edge_detection_count,
                "sharp_abs_max": _round(sharp_abs_max(features.sharp_values, complete)),
                "shared_detection_tracklets": shared[tracklet.tracklet_id],
                "sharp_availability": features.sharp_availability.value,
                "mask_bits_union": features.mask_bits_union,
                "shares_detection_with_positive": None,  # filled below
                "ctx_sep_v_lt4": seps[0],
                "ctx_sep_v4_6": seps[1],
                "ctx_sep_v6_8": seps[2],
                "ctx_sep_v8_10": seps[3],
                "ctx_sep_v10_11": seps[4],
                "ctx_nearest_star_arcsec": proximity.nearest_separation_arcsec,
                "ctx_nearest_star_v": proximity.nearest_v_mag,
                "ctx_proximity_group": kr.proximity_group(proximity),
                "ctx_angular_velocity_arcsec_per_min": _round(features.angular_velocity_arcsec_per_min),
                "ctx_position_angle_deg": _round(features.position_angle_deg),
                "_sources": [d.source_id for d in detections],
            }
        )
    positive_sources = {s for r in rows if r["label"] == rd.POSITIVE for s in r["_sources"]}
    for r in rows:
        sources = set(r.pop("_sources"))
        r["shares_detection_with_positive"] = int(
            r["label"] == rd.BACKGROUND and bool(positive_sources & sources)
        )

    labels = Counter(r["label"] for r in rows)
    conditions = {
        "field_id": field_id,
        "population": night["population"],
        "group": night["group"],
        "night": night["night"],
        "filters": [o.filter_code for o in observations],
        "sources_per_frame": [len(f.detections) for f in catalogs.frames],
        "tracklets": len(tracklets),
        "built_tracklets": len(built),
        "labels": {k: labels.get(k, 0) for k in (rd.POSITIVE, rd.AUXILIARY, rd.BACKGROUND)},
        "eligible_targets": len(targets),
        "targets": [
            {
                "designation": t["designation"],
                "role": t["role"],
                "group": t["group"],
                "rate_arcsec_per_min": t["rate_arcsec_per_min"],
                "min_global_margin_mag": min(f["global_margin_mag"] for f in t["frames"]),
                "trace_recovered": t["recovered"],
                "trace_tracklet_id": t["tracklet_id"],
            }
            for t in traces
            if t["designation"] in targets
        ],
    }
    del pipeline, catalogs
    return rows, conditions


def build_table(
    root: Path,
    out_dir: Path,
    cache_dir: Path,
    only: set[str] | None = None,
    progress: Callable[[str], None] = lambda message: None,
) -> None:
    """Per-field parts are cached (resumable after an IRSA hiccup; IRSA
    products are archival and SkyBoT is replayed, so a rerun cannot change
    an outcome), then combined into the committed table."""
    manifest = load_manifest(root)
    nights = development_nights(manifest)
    traces = load_development_traces(root, manifest)
    cache_dir.mkdir(parents=True, exist_ok=True)
    for night in nights:
        field_id = night["field_id"]
        if only is not None and field_id not in only:
            continue
        part = cache_dir / f"{field_id}.json"
        if part.exists():
            continue
        started = time.perf_counter()
        progress(f"{field_id}: pipeline")
        for attempt in range(1, FIELD_ATTEMPTS + 1):
            try:
                rows, conditions = field_rows(root, manifest, night, traces.get(field_id, []))
                break
            except Exception as exc:  # IRSA / VizieR hiccups; archival data, so a retry is safe
                if attempt == FIELD_ATTEMPTS:
                    raise
                progress(f"{field_id}: attempt {attempt} failed ({exc}); retrying")
                time.sleep(30 * attempt)
        conditions["seconds"] = round(time.perf_counter() - started, 1)
        part.write_text(json.dumps({"rows": rows, "conditions": conditions}) + "\n")
        progress(f"{field_id}: {conditions['built_tracklets']} built, {conditions['labels']}, {conditions['seconds']} s")
    if only is not None:
        return
    rows, conditions = [], []
    for night in nights:
        data = json.loads((cache_dir / f"{night['field_id']}.json").read_text())
        rows += data["rows"]
        data["conditions"].pop("seconds", None)
        conditions.append(data["conditions"])
    write_table(out_dir / TABLE_FILE, rows)
    (out_dir / FIELDS_FILE).write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "manifest_sha256": rd.file_sha256(root / MANIFEST_FILE),
                "stage": STAGE,
                "fields": conditions,
            },
            indent=1,
        )
        + "\n"
    )


def write_table(path: Path, rows: Sequence[Mapping]) -> None:
    # No name, mtime=0: the gzip bytes depend only on the content.
    with open(path, "wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz:
        text = _csv_text(rows)
        gz.write(text.encode())


def _csv_text(rows: Sequence[Mapping]) -> str:
    from io import StringIO

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=TABLE_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: "" if r.get(k) is None else r[k] for k in TABLE_COLUMNS})
    return buffer.getvalue()


def read_table(path: Path, manifest: Mapping) -> list[dict]:
    """Rows of the development table; every quadrant-night is guarded."""
    with gzip.open(path, "rt") as handle:
        rows = list(csv.DictReader(handle))
    for field_id in {r["field_id"] for r in rows}:
        rd.require_split(manifest, field_id, STAGE)
    for r in rows:
        for name in RANKER_INPUT_COLUMNS:
            r[name] = float(r[name]) if r[name] != "" else None
    return rows


# ---------------------------------------------------------------------------
# Evaluation (offline, from the table)
# ---------------------------------------------------------------------------


def oriented_score(value: float | None, direction: int) -> float:
    """Higher = reviewed earlier; missing ranks after every value (D3)."""
    return -math.inf if value is None else direction * value


def _bin(value: float | None, bins) -> str:
    if value is None:
        return "n/a"
    for low, high, name in bins:
        if low <= value < high:
            return name
    return "n/a"


def positive_strata(rows: Sequence[Mapping], fields: Sequence[Mapping]) -> dict[tuple[str, str], dict[str, str]]:
    """(field id, designation) -> strata of each positive object (D5)."""
    conditions = {f["field_id"]: f for f in fields}
    masked: dict[tuple[str, str], int] = {}
    for r in rows:
        if r["label"] != rd.POSITIVE:
            continue
        key = (r["field_id"], r["eval_designation"])
        m = int(r["masked_detection_count"])
        masked[key] = min(m, masked.get(key, m))
    out = {}
    for key, m in masked.items():
        field_id, designation = key
        c = conditions[field_id]
        target = next(t for t in c["targets"] if t["designation"] == designation)
        crowding = statistics.mean(c["sources_per_frame"])
        group = target["group"]
        out[key] = {
            "role": target["role"],
            "proximity_group": group,
            "near_star": "zone+outer" if group in rd.DEVELOPMENT_NEAR_GROUPS else "intermediate+control",
            "depth_margin": _bin(target["min_global_margin_mag"], DEPTH_BINS),
            "crowding": _bin(crowding, CROWDING_BINS),
            "filters": "single" if len(set(c["filters"])) == 1 else "mixed",
            "speed": _bin(target["rate_arcsec_per_min"], SPEED_BINS),
            "mask_state": "unmasked" if m == 0 else ("all" if m == 3 else "partial"),
            "population": c["population"],
        }
    return out


def rank_feature(
    rows_by_field: Mapping[str, Sequence[Mapping]],
    feature: str,
    strata: Mapping[tuple[str, str], Mapping[str, str]],
    exclude_background: Callable[[Mapping], bool] = lambda r: False,
    exclude_designations: frozenset[str] = frozenset(),
) -> list[rd.RankedPositive]:
    """Every positive object of every quadrant-night ranked by one feature
    in its pre-registered direction against its own background."""
    direction = rd.CANDIDATE_FEATURES[feature]
    positives: list[rd.RankedPositive] = []
    for field_id, rows in rows_by_field.items():
        kept = [
            r
            for r in rows
            if not (r["label"] == rd.BACKGROUND and exclude_background(r))
            and not (r["label"] == rd.POSITIVE and r["eval_designation"] in exclude_designations)
        ]
        scores = {r["tracklet_id"]: oriented_score(r[feature], direction) for r in kept}
        labels = {r["tracklet_id"]: r["label"] for r in kept}
        designations = {r["tracklet_id"]: r["eval_designation"] for r in kept if r["label"] == rd.POSITIVE}
        first = rows[0]
        positives += rd.rank_field(
            field_id,
            first["group"],
            first["night"],
            scores,
            labels,
            designations,
            {d: strata[(field_id, d)] for d in set(designations.values())},
        )
    return rd.object_weights(positives)


class Interval(BaseModel):
    point: float | None
    lower: float | None
    upper: float | None


class StratumResult(BaseModel):
    key: str
    value: str
    objects: float
    auc: float | None
    recall_5: float | None
    auc_ci: tuple[float | None, float | None] | None = None


class FieldAuc(BaseModel):
    field_id: str
    positives: float
    background: int
    auc: float | None


class Counterexample(BaseModel):
    field_id: str
    designation: str
    q: float
    value: float | None
    strata: dict[str, str]


class GateCheck(BaseModel):
    auc_lower_gt: bool
    marginal_auc_ge_half: bool
    near_star_auc_ge_half: bool
    missing_le: bool
    passed: bool
    reasons: list[str]


class FeatureResult(BaseModel):
    feature: str
    direction: int
    objects: float
    fields_with_positive: int
    auc: Interval
    recall_5: Interval
    recall: dict[str, float | None]  # fraction -> recall
    recall_at_budget: dict[str, float | None]
    enrichment: dict[str, float | None]
    median_q: float | None
    missing_ranked: int
    ranked: int
    missing_rate: float
    missing_by_label: dict[str, float]
    strata: list[StratumResult]
    fields: list[FieldAuc]
    sensitivity: dict[str, Interval]
    gate: GateCheck | None = None
    redundancy_dropped_by: str | None = None
    frozen: bool = False


STRATA_KEYS = (
    "role",
    "near_star",
    "proximity_group",
    "depth_margin",
    "crowding",
    "filters",
    "speed",
    "mask_state",
    "population",
)
# Strata whose point AUC is a gate condition get a bootstrap interval too.
GATE_STRATA = (("role", "marginal"), ("near_star", "zone+outer"))


def _ci(positives, statistic, label: str, resamples: int) -> Interval:
    lo, hi = rd.group_bootstrap(positives, statistic, label, resamples=resamples)
    return Interval(point=statistic(positives), lower=lo, upper=hi)


def evaluate_feature(
    feature: str,
    rows: Sequence[Mapping],
    rows_by_field: Mapping[str, Sequence[Mapping]],
    strata: Mapping[tuple[str, str], Mapping[str, str]],
    resamples: int = rd.BOOTSTRAP_RESAMPLES,
) -> FeatureResult:
    positives = rank_feature(rows_by_field, feature, strata)
    tag = f"AS-038/{feature}"
    auc = _ci(positives, rd.within_field_auc, f"{tag}/auc", resamples)
    recall5 = _ci(
        positives, lambda s: rd.recall_at_fraction(s, rd.PRIMARY_FRACTION), f"{tag}/recall5", resamples
    )
    fractions = (rd.PRIMARY_FRACTION, *rd.SECONDARY_FRACTIONS)
    strata_out = []
    for key in STRATA_KEYS:
        for value in sorted({p.strata[key] for p in positives}):
            members = rd.stratum(positives, key, value)
            ci = None
            if (key, value) in GATE_STRATA:
                ci = rd.group_bootstrap(members, rd.within_field_auc, f"{tag}/auc/{key}={value}", resamples=resamples)
            strata_out.append(
                StratumResult(
                    key=key,
                    value=value,
                    objects=rd.object_count(members),
                    auc=rd.within_field_auc(members),
                    recall_5=rd.recall_at_fraction(members, rd.PRIMARY_FRACTION),
                    auc_ci=ci,
                )
            )
    fields_out = []
    for field_id, field_rows_ in rows_by_field.items():
        members = [p for p in positives if p.field_id == field_id]
        fields_out.append(
            FieldAuc(
                field_id=field_id,
                positives=rd.object_count(members),
                background=sum(r["label"] == rd.BACKGROUND for r in field_rows_),
                auc=rd.within_field_auc(members),
            )
        )
    missing = sum(r[feature] is None for r in rows)
    by_label = {}
    for label in (rd.POSITIVE, rd.AUXILIARY, rd.BACKGROUND):
        group = [r for r in rows if r["label"] == label]
        by_label[label] = sum(r[feature] is None for r in group) / len(group) if group else 0.0
    sensitivity = {}
    for name, kwargs in (
        ("without background sharing a detection with a positive",
         {"exclude_background": lambda r: r["shares_detection_with_positive"] == "1"}),
        (f"without {CROSS_SPLIT_DESIGNATION}", {"exclude_designations": frozenset({CROSS_SPLIT_DESIGNATION})}),
    ):
        alt = rank_feature(rows_by_field, feature, strata, **kwargs)
        sensitivity[name + " (AUC)"] = Interval(point=rd.within_field_auc(alt), lower=None, upper=None)
        sensitivity[name + " (recall@5%)"] = Interval(
            point=rd.recall_at_fraction(alt, rd.PRIMARY_FRACTION), lower=None, upper=None
        )
    qs = sorted(p.q for p in positives)
    return FeatureResult(
        feature=feature,
        direction=rd.CANDIDATE_FEATURES[feature],
        objects=rd.object_count(positives),
        fields_with_positive=len({p.field_id for p in positives}),
        auc=auc,
        recall_5=recall5,
        recall={f"{f:g}": rd.recall_at_fraction(positives, f) for f in fractions},
        recall_at_budget={str(k): rd.recall_at_budget(positives, k) for k in rd.SECONDARY_BUDGETS},
        enrichment={f"{f:g}": rd.enrichment(positives, f) for f in fractions},
        median_q=statistics.median(qs) if qs else None,
        missing_ranked=missing,
        ranked=len(rows),
        missing_rate=missing / len(rows) if rows else 0.0,
        missing_by_label=by_label,
        strata=strata_out,
        fields=fields_out,
        sensitivity=sensitivity,
    )


def _stratum_auc(result: FeatureResult, key: str, value: str) -> float | None:
    for s in result.strata:
        if s.key == key and s.value == value:
            return s.auc
    return None


def gate_check(result: FeatureResult) -> GateCheck:
    """The AS-037 stage-1 gate, mechanically (D7)."""
    marginal = _stratum_auc(result, "role", "marginal")
    near = _stratum_auc(result, "near_star", "zone+outer")
    checks = {
        "auc_lower_gt": result.auc.lower is not None and result.auc.lower > rd.AUC_GATE_LOWER,
        "marginal_auc_ge_half": marginal is not None and marginal >= 0.5,
        "near_star_auc_ge_half": near is not None and near >= 0.5,
        "missing_le": result.missing_rate <= rd.MAX_MISSING,
    }
    reasons = []
    if not checks["auc_lower_gt"]:
        reasons.append(f"AUC lower bound {_f(result.auc.lower)} <= {rd.AUC_GATE_LOWER}")
    if not checks["marginal_auc_ge_half"]:
        reasons.append(f"MARGINAL AUC {_f(marginal)} < 0.5")
    if not checks["near_star_auc_ge_half"]:
        reasons.append(f"zone+outer AUC {_f(near)} < 0.5")
    if not checks["missing_le"]:
        reasons.append(f"missing {100 * result.missing_rate:.1f} % > {100 * rd.MAX_MISSING:g} %")
    if result.auc.point is not None and result.auc.point < 0.5:
        reasons.append("reversed: overall AUC < 0.5 in the pre-registered direction")
    return GateCheck(**checks, passed=all(checks.values()), reasons=reasons)


def average_ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(x: Sequence[float | None], y: Sequence[float | None]) -> float | None:
    """Spearman rank correlation, pairwise complete, average ranks."""
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    if len(pairs) < 3:
        return None
    rx = average_ranks([a for a, _ in pairs])
    ry = average_ranks([b for _, b in pairs])
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def spearman_matrices(
    rows: Sequence[Mapping], features: Sequence[str]
) -> tuple[dict[str, dict[str, float | None]], dict[str, dict[str, float | None]]]:
    """Pooled development-background Spearman (deciding, D4) and the
    per-quadrant-night median (descriptive)."""
    background = [r for r in rows if r["label"] == rd.BACKGROUND]
    by_field: dict[str, list[Mapping]] = defaultdict(list)
    for r in background:
        by_field[r["field_id"]].append(r)
    pooled: dict[str, dict[str, float | None]] = {a: {} for a in features}
    median: dict[str, dict[str, float | None]] = {a: {} for a in features}
    for i, a in enumerate(features):
        for b in features[i:]:
            if a == b:
                pooled[a][b] = median[a][b] = 1.0
                continue
            rho = spearman([r[a] for r in background], [r[b] for r in background])
            per = [
                v
                for group in by_field.values()
                if len(group) >= 10
                and (v := spearman([r[a] for r in group], [r[b] for r in group])) is not None
            ]
            med = statistics.median(per) if per else None
            pooled[a][b] = pooled[b][a] = rho
            median[a][b] = median[b][a] = med
    return pooled, median


def redundancy_drops(
    passing: Sequence[str], auc: Mapping[str, float], pooled: Mapping[str, Mapping[str, float | None]]
) -> dict[str, str]:
    """feature -> the higher-AUC passing feature it is redundant with (D4)."""
    order = {name: i for i, name in enumerate(rd.CANDIDATE_FEATURES)}
    dropped = {}
    for a in passing:
        for b in passing:
            if a == b:
                continue
            rho = pooled[a][b]
            if rho is None or abs(rho) <= rd.REDUNDANCY_SPEARMAN:
                continue
            b_wins = auc[b] > auc[a] or (auc[b] == auc[a] and order[b] < order[a])
            if b_wins and a not in dropped:
                dropped[a] = b
    return dropped


def counterexamples(
    result: FeatureResult,
    positives: Sequence[rd.RankedPositive],
    values: Mapping[tuple[str, str], float | None],
) -> dict:
    return {
        "fields_auc_below_half": [
            f.model_dump()
            for f in result.fields
            if f.auc is not None and f.positives >= COUNTEREXAMPLE_MIN_POSITIVES and f.auc < 0.5
        ],
        "strata_auc_below_half": [
            s.model_dump() for s in result.strata if s.auc is not None and s.auc < 0.5
        ],
        "bottom_half_positives": [
            Counterexample(
                field_id=p.field_id,
                designation=p.designation,
                q=round(p.q, 4),
                value=values.get((p.field_id, p.designation)),
                strata=p.strata,
            ).model_dump()
            for p in sorted(positives, key=lambda p: -p.q)
            if p.q > 0.5
        ],
    }


class Evaluation(BaseModel):
    generated_at: datetime
    stage: str
    manifest_sha256: str
    table_sha256: str
    development_fields: int
    ranked_tracklets: int
    labels: dict[str, int]
    positive_objects: float
    positive_fields: int
    reconciliation: dict
    features: list[FeatureResult]
    spearman_pooled: dict[str, dict[str, float | None]]
    spearman_field_median: dict[str, dict[str, float | None]]
    passing_gate: list[str]
    frozen_features: list[str]
    counterexamples: dict[str, dict]


def reconcile(rows: Sequence[Mapping], fields: Sequence[Mapping]) -> dict:
    """Positive labels vs the AS-035/036 'recovered' traces (same pipeline)."""
    labelled = {(r["field_id"], r["eval_designation"]) for r in rows if r["label"] == rd.POSITIVE}
    traced = {
        (f["field_id"], t["designation"]) for f in fields for t in f["targets"] if t["trace_recovered"]
    }
    return {
        "positive_targets_labelled": len(labelled),
        "positive_targets_traced_recovered": len(traced),
        "labelled_not_traced": sorted(map(list, labelled - traced)),
        "traced_not_labelled": sorted(map(list, traced - labelled)),
    }


def evaluate(out_dir: Path, root: Path, resamples: int = rd.BOOTSTRAP_RESAMPLES,
             progress: Callable[[str], None] = lambda m: None) -> Evaluation:
    manifest = load_manifest(root)
    development_nights(manifest)
    rows = read_table(out_dir / TABLE_FILE, manifest)
    fields = json.loads((out_dir / FIELDS_FILE).read_text())["fields"]
    for f in fields:
        rd.require_split(manifest, f["field_id"], STAGE)
    rows_by_field: dict[str, list[Mapping]] = defaultdict(list)
    for r in rows:
        rows_by_field[r["field_id"]].append(r)
    strata = positive_strata(rows, fields)

    results: list[FeatureResult] = []
    for feature in rd.CANDIDATE_FEATURES:
        progress(f"evaluating {feature}")
        result = evaluate_feature(feature, rows, rows_by_field, strata, resamples)
        result.gate = gate_check(result)
        results.append(result)
    names = list(rd.CANDIDATE_FEATURES)
    progress("spearman")
    pooled, median = spearman_matrices(rows, names)
    passing = [r.feature for r in results if r.gate.passed]
    drops = redundancy_drops(passing, {r.feature: r.auc.point for r in results}, pooled)
    frozen = [f for f in passing if f not in drops]
    examples = {}
    for r in results:
        r.redundancy_dropped_by = drops.get(r.feature)
        r.frozen = r.feature in frozen
        positives = rank_feature(rows_by_field, r.feature, strata)
        values = {}
        for row in rows:
            if row["label"] == rd.POSITIVE:
                key = (row["field_id"], row["eval_designation"])
                v = row[r.feature]
                old = values.get(key)
                score = oriented_score(v, r.direction)
                if key not in values or score > oriented_score(old, r.direction):
                    values[key] = v
        examples[r.feature] = counterexamples(r, positives, values)
        if not r.frozen:
            examples[r.feature]["bottom_half_positives"] = examples[r.feature]["bottom_half_positives"][:10]
    first = results[0]
    positives = rank_feature(rows_by_field, first.feature, strata)
    return Evaluation(
        generated_at=datetime.now(timezone.utc),
        stage=STAGE,
        manifest_sha256=rd.file_sha256(root / MANIFEST_FILE),
        table_sha256=rd.file_sha256(out_dir / TABLE_FILE),
        development_fields=len(rows_by_field),
        ranked_tracklets=len(rows),
        labels=dict(Counter(r["label"] for r in rows)),
        positive_objects=rd.object_count(positives),
        positive_fields=len({p.field_id for p in positives}),
        reconciliation=reconcile(rows, fields),
        features=results,
        spearman_pooled=pooled,
        spearman_field_median=median,
        passing_gate=passing,
        frozen_features=frozen,
        counterexamples=examples,
    )


def frozen_spec(evaluation: Evaluation) -> dict:
    return {
        "ticket": "AS-038",
        "stage": STAGE,
        "for": "AS-039 ranking construction (development only); AS-037 sections 6-7 unchanged",
        "manifest_sha256": evaluation.manifest_sha256,
        "table_sha256": evaluation.table_sha256,
        "features": [
            {
                "feature": r.feature,
                "direction": r.direction,
                "input": "within-quadrant-night mid-rank percentile, oriented higher = earlier",
                "auc": r.auc.point,
                "auc_ci_95": [r.auc.lower, r.auc.upper],
            }
            for r in evaluation.features
            if r.frozen
        ],
        "not_allowed": [
            "any feature not listed here",
            "bright-star proximity / proximity group / star separations (context only)",
            "speed and position angle (context only)",
            "identification status, designation, SkyBoT prediction or residual",
        ],
        "gate_failed_or_dropped": {
            r.feature: (r.gate.reasons or [f"redundant with {r.redundancy_dropped_by}"])
            for r in evaluation.features
            if not r.frozen
        },
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _f(value, digits: int = 3) -> str:
    return "–" if value is None else f"{value:.{digits}f}"


def _ci_text(i: Interval) -> str:
    return f"{_f(i.point)} [{_f(i.lower)}, {_f(i.upper)}]"


def render_markdown(e: Evaluation, fields: Sequence[Mapping]) -> str:
    lines = [
        "# AS-038 candidate feature evaluation (stage 1, development only; generated)",
        "",
        f"Generated {e.generated_at:%Y-%m-%d %H:%M UTC}. Interpretation: `as038_findings.md`. "
        "No ranker, combined score, weight, threshold or filter; validation split not loaded.",
        "",
        f"Manifest SHA-256 `{e.manifest_sha256[:16]}…`; table SHA-256 `{e.table_sha256[:16]}…`. "
        f"{e.development_fields} development quadrant-nights, {e.ranked_tracklets} ranked (built) "
        f"tracklets: {e.labels}. Positive object-nights {e.positive_objects:g} in "
        f"{e.positive_fields} quadrant-nights.",
        "",
        "## Gate summary",
        "",
        "AUC = within-field AUC (mean 1 − q), weighted by object-night; [95 % group bootstrap]. "
        "Gate: AUC lower > 0.55, MARGINAL AUC ≥ 0.5, zone+outer AUC ≥ 0.5, missing ≤ 5 %; "
        "redundancy |Spearman| > 0.90 on development background (pooled).",
        "",
        "| feature | dir | AUC [95 %] | recall@5 % [95 %] | MARGINAL AUC | zone+outer AUC | missing | gate | frozen | reason |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in e.features:
        reason = "; ".join(r.gate.reasons) or (
            f"redundant with {r.redundancy_dropped_by}" if r.redundancy_dropped_by else "all conditions hold"
        )
        lines.append(
            f"| `{r.feature}` | {'+' if r.direction > 0 else '−'} | {_ci_text(r.auc)} | {_ci_text(r.recall_5)} "
            f"| {_f(_stratum_auc(r, 'role', 'marginal'))} | {_f(_stratum_auc(r, 'near_star', 'zone+outer'))} "
            f"| {100 * r.missing_rate:.2f} % | {'PASS' if r.gate.passed else 'FAIL'} "
            f"| {'yes' if r.frozen else 'no'} | {reason} |"
        )
    lines += ["", f"**Frozen for AS-039:** {', '.join(f'`{f}`' for f in e.frozen_features) or 'none'}", ""]

    lines += [
        "## Secondary metrics",
        "",
        "| feature | recall@1/2/5/10/20 % | recall@K 10/25/50 | enrichment@5 % | median q |",
        "|---|---|---|---|---|",
    ]
    for r in e.features:
        lines.append(
            f"| `{r.feature}` | {' / '.join(_f(r.recall[k], 2) for k in ('0.01', '0.02', '0.05', '0.1', '0.2'))} "
            f"| {' / '.join(_f(r.recall_at_budget[k], 2) for k in ('10', '25', '50'))} "
            f"| {_f(r.enrichment['0.05'], 1)} | {_f(r.median_q)} |"
        )

    lines += ["", "## Strata (point AUC / recall@5 %, object-nights)", ""]
    keys = [(s.key, s.value) for s in e.features[0].strata]
    lines.append("| feature | " + " | ".join(f"{k}={v} (n {s.objects:g})" for (k, v), s in zip(keys, e.features[0].strata)) + " |")
    lines.append("|---|" + "---|" * len(keys))
    for r in e.features:
        lines.append(
            f"| `{r.feature}` | " + " | ".join(f"{_f(s.auc, 2)} / {_f(s.recall_5, 2)}" for s in r.strata) + " |"
        )
    lines += ["", "Gate strata with intervals:", "", "| feature | MARGINAL AUC [95 %] | zone+outer AUC [95 %] |", "|---|---|---|"]
    for r in e.features:
        cells = []
        for key, value in GATE_STRATA:
            s = next(s for s in r.strata if s.key == key and s.value == value)
            cells.append(f"{_f(s.auc)} [{_f(s.auc_ci[0])}, {_f(s.auc_ci[1])}]" if s.auc_ci else _f(s.auc))
        lines.append(f"| `{r.feature}` | " + " | ".join(cells) + " |")

    lines += [
        "",
        "## Missingness (share of ranked tracklets)",
        "",
        "| feature | all | positive | auxiliary | background |",
        "|---|---|---|---|---|",
    ]
    for r in e.features:
        lines.append(
            f"| `{r.feature}` | {r.missing_ranked}/{r.ranked} ({100 * r.missing_rate:.2f} %) "
            + " | ".join(f"{100 * r.missing_by_label[k]:.2f} %" for k in (rd.POSITIVE, rd.AUXILIARY, rd.BACKGROUND))
            + " |"
        )

    names = [r.feature for r in e.features]
    for title, matrix in (
        ("Spearman on development background, pooled (deciding)", e.spearman_pooled),
        ("Spearman on development background, median over quadrant-nights (descriptive)", e.spearman_field_median),
    ):
        lines += ["", f"## {title}", "", "| | " + " | ".join(f"{i + 1}" for i in range(len(names))) + " |", "|---|" + "---|" * len(names)]
        for i, a in enumerate(names):
            lines.append(f"| {i + 1} `{a}` | " + " | ".join(_f(matrix[a][b], 2) for b in names) + " |")

    lines += ["", "## Sensitivity (descriptive)", "", "| feature | analysis | value |", "|---|---|---|"]
    for r in e.features:
        for name, i in r.sensitivity.items():
            lines.append(f"| `{r.feature}` | {name} | {_f(i.point)} |")

    lines += ["", "## Per quadrant-night AUC (positives ≥ 1)", ""]
    field_ids = [f.field_id for f in e.features[0].fields if f.positives > 0]
    lines.append("| field | positives | background | " + " | ".join(str(i + 1) for i in range(len(names))) + " |")
    lines.append("|---|---|---|" + "---|" * len(names))
    for fid in field_ids:
        per = [next(f for f in r.fields if f.field_id == fid) for r in e.features]
        lines.append(
            f"| {fid} | {per[0].positives:g} | {per[0].background} | " + " | ".join(_f(p.auc, 2) for p in per) + " |"
        )

    lines += ["", "## Counterexamples", ""]
    for r in e.features:
        ce = e.counterexamples[r.feature]
        lines.append(
            f"- `{r.feature}`: {len(ce['fields_auc_below_half'])} quadrant-nights (≥ {COUNTEREXAMPLE_MIN_POSITIVES} positives) "
            f"with AUC < 0.5"
            + (": " + ", ".join(f"{c['field_id']} ({_f(c['auc'], 2)}, n {c['positives']:g})" for c in ce["fields_auc_below_half"]) if ce["fields_auc_below_half"] else "")
            + f"; strata with AUC < 0.5: "
            + (", ".join(f"{s['key']}={s['value']} ({_f(s['auc'], 2)}, n {s['objects']:g})" for s in ce["strata_auc_below_half"]) or "none")
        )
    for r in e.features:
        if not r.frozen:
            continue
        rows_ = e.counterexamples[r.feature]["bottom_half_positives"]
        lines += [
            "",
            f"### `{r.feature}` (frozen): positives in the bottom half of their background ({len(rows_)})",
            "",
            "| field | object | q | value | role | group | depth | mask | crowding |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for c in rows_:
            s = c["strata"]
            lines.append(
                f"| {c['field_id']} | {c['designation']} | {c['q']:.3f} | {_f(c['value'], 3)} | {s['role']} "
                f"| {s['proximity_group']} | {s['depth_margin']} | {s['mask_state']} | {s['crowding']} |"
            )

    lines += [
        "",
        "## Development quadrant-nights",
        "",
        "| field | pop | group | filters | sources/frame | tracklets | built | positive / auxiliary / background |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for f in fields:
        l = f["labels"]
        lines.append(
            f"| {f['field_id']} | {f['population']} | {f['group']} | {'/'.join(f['filters'])} "
            f"| {'/'.join(map(str, f['sources_per_frame']))} | {f['tracklets']} | {f['built_tracklets']} "
            f"| {l[rd.POSITIVE]} / {l[rd.AUXILIARY]} / {l[rd.BACKGROUND]} |"
        )
    rec = e.reconciliation
    lines += [
        "",
        "## Label reconciliation with the AS-035/036 traces",
        "",
        f"Positive (field, object) labelled: {rec['positive_targets_labelled']}; traced recovered: "
        f"{rec['positive_targets_traced_recovered']}; labelled not traced: {rec['labelled_not_traced']}; "
        f"traced not labelled: {rec['traced_not_labelled']}.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    t = sub.add_parser("table", help="development feature table (IRSA + VizieR)")
    t.add_argument("--root", type=Path, default=Path("."))
    t.add_argument("--out-dir", type=Path, required=True)
    t.add_argument("--cache-dir", type=Path, default=Path(".cache/as038"))
    t.add_argument("--field", action="append")
    ev = sub.add_parser("evaluate", help="stage-1 metrics, gate and frozen list (offline)")
    ev.add_argument("--root", type=Path, default=Path("."))
    ev.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args.command == "table":
        build_table(
            args.root, args.out_dir, args.cache_dir,
            only=set(args.field) if args.field else None,
            progress=lambda m: print(m, flush=True),
        )
    else:
        evaluation = evaluate(args.out_dir, args.root, progress=lambda m: print(m, flush=True))
        (args.out_dir / RESULTS_FILE).write_text(evaluation.model_dump_json(indent=1) + "\n")
        (args.out_dir / FROZEN_FILE).write_text(json.dumps(frozen_spec(evaluation), indent=1) + "\n")
        fields = json.loads((args.out_dir / FIELDS_FILE).read_text())["fields"]
        (args.out_dir / REPORT_FILE).write_text(render_markdown(evaluation, fields))
        print(f"frozen: {evaluation.frozen_features}")


if __name__ == "__main__":
    main()
