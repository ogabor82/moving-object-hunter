"""AS-040: stage-3 one-shot sealed validation of the frozen candidate ranker.

Executes stage 3 of the AS-037 pre-registration
(validation/results/as037/as037_preregistration.md, PRE-REGISTRATION block
of app/validation/ranking_design.py) unchanged, with the ranker and
comparator AS-039 froze (validation/results/as039/as039_frozen_ranker.json):

- verify, before any validation quadrant-night is loaded, that the frozen
  manifest, split, AS-038 feature list, AS-039 ranker spec and their
  hashes are exactly the committed ones (stop on any mismatch, never
  repair);
- build the validation feature table of the 24 sealed quadrant-nights with
  the unchanged AS-038 pipeline, every quadrant-night through
  `ranking_design.require_split(manifest, field_id, STAGE_VALIDATION)`;
- apply the frozen M1 and the frozen comparator B1 `sharp_abs_max` once;
- the AS-037 primary and secondary metrics with group-bootstrap
  intervals, the near-star (zone vs control) and faint (MARGINAL vs
  PRIMARY) guards, `ranking_design.decide()` for the verdict, the paired
  M1 - comparator difference, strata, end-to-end recall, sensitivity,
  failure analysis with evidence strips, and the descriptive
  development-vs-validation comparison.

No feature, weight, transform, ranker, threshold, guard, metric or label
is changed, fitted or selected here. UNKNOWN is background, not a ground-
truth false positive. Identity, SkyBoT, proximity, speed and PA are
evaluation / stratification only.

    python -m app.validation.sealed_validation verify      # frozen inputs only, offline
    python -m app.validation.sealed_validation table \\
        --out-dir validation/results/as040                  # IRSA + VizieR, resumable
    python -m app.validation.sealed_validation evaluate \\
        --out-dir validation/results/as040                  # offline, from the table
    python -m app.validation.sealed_validation strips \\
        --out-dir validation/results/as040                  # cutouts (IRSA), evidence only
"""

import argparse
import csv
import gzip
import hashlib
import json
import statistics
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from app.validation import feature_evaluation as fe
from app.validation import ranker_construction as rc
from app.validation import ranking_design as rd

# ---------------------------------------------------------------------------
# IMPLEMENTATION DECISIONS (AS-040, 2026-10-02; fixed and committed before
# any validation feature, score or ranking outcome existed). They fill in
# details AS-037 leaves open; none changes an AS-037 rule, the split, a
# metric, a guard, a threshold, a label, a feature, a direction, a weight or
# the AS-039 frozen ranker / comparator.
# ---------------------------------------------------------------------------

STAGE = rd.STAGE_VALIDATION
AS039_DIR = "validation/results/as039"
FROZEN_RANKER_FILE = f"{AS039_DIR}/as039_frozen_ranker.json"
CONSTRUCTION_FILE = f"{AS039_DIR}/as039_construction.json"

# V1 Frozen inputs, verified before anything of a validation quadrant-night
# is read (`verify_frozen_inputs`; `table`, `evaluate` and `strips` call it
# first). Any mismatch raises FrozenInputError; nothing is repaired.
# - file SHA-256 of the committed AS-037 manifest, AS-038 table, AS-038
#   frozen list and AS-039 frozen ranker equal the values below (the first
#   three also equal the ones the frozen ranker records);
# - the manifest rebuilds identically from its inputs (apart from
#   generated_at), every input file hash matches, and the validation split
#   is the AS-037 one: 24 quadrant-nights, 22 groups, digest below;
# - the ranker is exactly M1: the 8 AS-038 features in AS-037 directions,
#   weight 1/8 each, intercept 0, not fitted; the comparator is exactly B1
#   sharp_abs_max (-), weight 1, intercept 0; selection ADVANCE / M1 /
#   B1:sharp_abs_max;
# - the representation is unchanged: missing percentile 0.0
#   (ranker_construction.MISSING_PERCENTILE).
FROZEN_SHA256 = {
    fe.MANIFEST_FILE: "63e12b9feb8bc3761a0b43ecebd1a68b6bbe00ef83de3e627cf7baaa4b9f423c",
    f"{rc.AS038_DIR}/{fe.TABLE_FILE}": "da670e38357503fe6d6d5239097523d08e939d8c8c28c133a0d873d7d6dd5fd9",
    rc.FROZEN_FEATURES_FILE: "a8182bc63649f6f035ca3b19a4db9dcc1c9701abc07df149b68d52c82de0cf42",
    FROZEN_RANKER_FILE: "875a0647a61f9bac25f5932e2f5f3b5d6b0d082de0ffc3944c4a1824f4eda897",
}
VALIDATION_DIGEST = "a549b6bc22a54f14d136b41de3047cce627ce792d8f5308b69e22f96e603aa3d"
VALIDATION_FIELDS = 24
VALIDATION_GROUPS = 22
FROZEN_RANKER = "M1"
FROZEN_COMPARATOR = "B1:sharp_abs_max"

# V2 Validation feature table: ranking_design / AS-038 `field_rows`
# unchanged (EXPERIMENTAL_DEFAULT_CONFIG, SkyBoT replayed from the stored
# snapshots only, eligible targets from the AS-036 C traces, the same
# columns), run under the validation split guard. Trace rows and SkyBoT
# entries of any non-validation quadrant-night are dropped by field id. Per
# built tracklet the detections' "product_id ra dec" are kept
# (`det_positions`) for the evidence strips; they never reach a score.
# Per-field parts are cached (resumable; archival IRSA products, replayed
# SkyBoT, so a rerun cannot change an outcome).

# V3 Scores: exactly the frozen spec. Per quadrant-night, over all its
# built tracklets and without labels, p_k =
# ranking_design.within_field_percentile(values_k, direction_k), missing
# -> 0.0; score = sum_k weight_k * p_k + intercept with the weights,
# directions and intercept read from as039_frozen_ranker.json. Nothing is
# fitted. The same for the comparator. B0 (SHA-256 hash order) is scored as
# the pre-registered null reference, descriptive only.

# V4 Labels and strata: ranking_design.label_tracklet (unchanged) and AS-038
# D5 (feature_evaluation.positive_strata) from the AS-036 C traces. Added
# strata AS-037 section 9 lists for validation: star class of the nearest
# V < 10 Tycho-2 star of the target trace ("V<6" for classes V < 4 and
# 4-6, "6-8", "8-10", "none" without a V < 10 star; context only).

# V5 Verdict: ranking_design.decide(M1 positives, "AS-040/M1/recall5")
# verbatim: minimums 100 object-nights / 15 quadrant-nights; NOT USEFUL if
# the bootstrap upper bound of recall@5 % < 0.50; USEFUL if recall@5 % >=
# 0.50 and lower bound >= 0.30, qualified by the near-star guard (zone vs
# control, zone >= 10 object-nights) and the faint guard (MARGINAL vs
# PRIMARY, MARGINAL >= 30), 0.20 margin, point estimates; else
# INCONCLUSIVE. The verdict is copied from decide(); nothing overrides it.
DECISION_LABEL = "AS-040/M1/recall5"

# V6 Secondary metrics (never deciding), for M1, the comparator and B0:
# recall at 1 / 2 / 5 / 10 / 20 %, recall@K 10 / 25 / 50, enrichment,
# within-field AUC, median q; each with a 95 % group bootstrap (2000,
# seed SHA-256('AS-037:AS-040/<ranker>/<statistic>')). The comparator's
# decide()-level and guards are reported, descriptive only.

# V7 Comparator analysis (AS-037 section 7, secondary): paired group-
# bootstrap difference of recall@5 % M1 - B1 sharp_abs_max (and M1 - B0),
# ranker_construction.paired_difference, label 'AS-040/M1/minus-<name>';
# plus the positives in the top 5 % of one ranker only.

# V8 Descriptive guard views (never deciding): zone + outer vs control
# (the AS-039 development definition, for the development-vs-validation
# comparison), zone + outer vs intermediate + control, and per role within
# the near-star stratum.

# V9 End-to-end (AS-037 section 5, secondary): per eligible target
# (rate- and baseline-eligible trace row), hit = recovered (POSITIVE) and
# q <= 0.05 for that object in that quadrant-night; object-night weights
# over the eligible copies; zone vs control (and every proximity group).

# V10 Sensitivity (descriptive): AS-038 D9 (a) background sharing a
# detection with a positive removed; (b) 105890 removed.

# V11 Failure analysis (AS-037 section 9): every validation positive with
# M1 q > 0.05 is listed with its raw features, oriented percentiles and
# strata. Counterexamples as AS-039 E10: quadrant-nights with >= 3
# positives and AUC < 0.5; strata with recall@5 % more than 0.20 below
# overall; positives in the bottom half.

# V12 Evidence strips (AS-037 section 9): up to 12 missed positives (q >
# 0.05) in SHA-256('AS-040:<field>:<designation>') order, and 20 of the
# background tracklets in their quadrant-night's M1 top 5 % (background-
# rank fraction <= 0.05 among the background) in SHA-256('AS-040:<field>:
# <tracklet>') order. E1|E2|E3 cutouts with the tracklet's detections
# marked. Agent labels are written after viewing into visual_review.json:
# a visual impression, not ground truth; the share of shortlist background
# that looks like an artefact is an estimate from 20 strips.
STRIP_MISSED = 12
STRIP_BACKGROUND = 20
STRIP_SALT = "AS-040"

# V13 Development vs validation (descriptive only): M1 and comparator
# metrics and guards from the committed as039_construction.json next to
# the validation values, with differences. No conclusion feeds back.

# V14 One shot: no command fits, selects or re-scores anything with
# altered inputs. A rerun of `evaluate` on the same table is deterministic
# (it recomputes the identical numbers); it is not a second look with
# different choices.

TABLE_FILE = "as040_feature_table.csv.gz"
FIELDS_FILE = "as040_fields.json"
VERIFY_FILE = "as040_frozen_check.json"
RESULTS_FILE = "as040_validation.json"
REPORT_FILE = "as040_validation.md"
REVIEW_FILE = "visual_review.json"
TABLE_COLUMNS = (*fe.TABLE_COLUMNS, "det_positions")
CACHE_DIR = Path(".cache/as040")


class FrozenInputError(RuntimeError):
    """A frozen AS-037 / AS-038 / AS-039 input differs from the committed one."""


# ---------------------------------------------------------------------------
# V1 frozen-input verification
# ---------------------------------------------------------------------------


class FrozenCheck(BaseModel):
    checked_at: datetime
    file_sha256: dict[str, str]
    validation_digest: str
    validation_fields: int
    validation_groups: int
    ranker: dict
    comparator: dict
    selection: dict
    checks: list[str]


def _expected_m1() -> dict:
    return {
        "ranker": "M1",
        "inputs": [{"feature": n, "direction": rd.CANDIDATE_FEATURES[n]} for n in rc.FROZEN_FEATURES],
        "weights": {n: 1 / len(rc.FROZEN_FEATURES) for n in rc.FROZEN_FEATURES},
        "intercept": 0.0,
        "fitted": False,
    }


def _expected_comparator() -> dict:
    return {
        "ranker": FROZEN_COMPARATOR,
        "inputs": [{"feature": "sharp_abs_max", "direction": -1}],
        "weights": {"sharp_abs_max": 1.0},
        "intercept": 0.0,
        "fitted": False,
    }


def verify_frozen_inputs(root: Path) -> FrozenCheck:
    """V1. Raises FrozenInputError on any mismatch; reads no validation
    feature, image or score (only committed design files)."""
    checks: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            raise FrozenInputError(message)
        checks.append(message)

    hashes = {path: rd.file_sha256(root / path) for path in FROZEN_SHA256}
    for path, expected in FROZEN_SHA256.items():
        require(hashes[path] == expected, f"{path} SHA-256 = {expected[:16]}…")
    frozen = json.loads((root / FROZEN_RANKER_FILE).read_text())
    require(frozen["manifest_sha256"] == hashes[fe.MANIFEST_FILE], "frozen ranker bound to this manifest")
    require(
        frozen["table_sha256"] == hashes[f"{rc.AS038_DIR}/{fe.TABLE_FILE}"],
        "frozen ranker bound to this AS-038 table",
    )
    require(
        frozen["frozen_features_sha256"] == hashes[rc.FROZEN_FEATURES_FILE],
        "frozen ranker bound to this AS-038 feature list",
    )
    require(not str(frozen.get("code_commit", "")).endswith("+dirty"), "frozen ranker from a clean commit")
    features = rc.load_frozen_features(root)
    require(tuple(n for n, _ in features) == rc.FROZEN_FEATURES, "AS-038 frozen list = the 8 AS-039 features")

    manifest = fe.load_manifest(root)
    for path, digest in manifest["inputs"].items():
        require(rd.file_sha256(root / path) == digest, f"manifest input {path} unchanged")
    rebuilt = rd.build_manifest(root)
    committed = {k: v for k, v in manifest.items() if k != "generated_at"}
    rebuilt.pop("generated_at")
    require(rebuilt == committed, "manifest rebuilds identically from its inputs")
    validation = [q for q in manifest["quadrant_nights"] if q["split"] == rd.VALIDATION]
    digest = rd.split_digest([q["field_id"] for q in validation])
    require(digest == VALIDATION_DIGEST, f"validation digest = {VALIDATION_DIGEST[:12]}…")
    require(len(validation) == VALIDATION_FIELDS, f"{VALIDATION_FIELDS} validation quadrant-nights")
    groups = {q["group"] for q in validation}
    require(len(groups) == VALIDATION_GROUPS, f"{VALIDATION_GROUPS} validation groups")
    development_groups = {q["group"] for q in manifest["quadrant_nights"] if q["split"] == rd.DEVELOPMENT}
    require(not groups & development_groups, "no group spans both splits")

    ranker, comparator = frozen["ranker"], frozen["comparator"]
    keys = ("ranker", "inputs", "weights", "intercept", "fitted")
    require({k: ranker[k] for k in keys} == _expected_m1(), "ranker = M1, 8 features, weight 1/8, intercept 0, no fit")
    require(
        {k: comparator[k] for k in keys} == _expected_comparator(),
        "comparator = B1 sharp_abs_max (-), weight 1, intercept 0",
    )
    selection = frozen["selection"]
    require(
        selection["outcome"] == rc.ADVANCE
        and selection["selected"] == FROZEN_RANKER
        and selection["comparator"] == FROZEN_COMPARATOR,
        "AS-039 selection ADVANCE, M1, comparator B1:sharp_abs_max",
    )
    require(rc.MISSING_PERCENTILE == 0.0, "missing percentile 0.0")
    return FrozenCheck(
        checked_at=datetime.now(timezone.utc),
        file_sha256=hashes,
        validation_digest=digest,
        validation_fields=len(validation),
        validation_groups=len(groups),
        ranker=ranker,
        comparator=comparator,
        selection=selection,
        checks=checks,
    )


# ---------------------------------------------------------------------------
# V2 split-guarded validation inputs and table
# ---------------------------------------------------------------------------


def validation_nights(manifest: Mapping) -> list[dict]:
    nights = [q for q in manifest["quadrant_nights"] if q["split"] == rd.VALIDATION]
    for q in nights:
        rd.require_split(manifest, q["field_id"], STAGE)
    return nights


def load_validation_traces(root: Path, manifest: Mapping) -> dict[str, list[dict]]:
    """Trace rows of validation quadrant-nights only (all C), by field id."""
    allowed = {q["field_id"] for q in validation_nights(manifest)}
    by_field: dict[str, list[dict]] = defaultdict(list)
    for name in ("R", "N", "C"):
        for t in json.loads((root / rd.TRACE_FILES[name]).read_text())["targets"]:
            if t["field_id"] in allowed:
                by_field[t["field_id"]].append(t)
    return dict(by_field)


def build_table(
    root: Path,
    out_dir: Path,
    cache_dir: Path = CACHE_DIR,
    only: set[str] | None = None,
    progress: Callable[[str], None] = lambda message: None,
) -> None:
    verify_frozen_inputs(root)
    manifest = fe.load_manifest(root)
    nights = validation_nights(manifest)
    traces = load_validation_traces(root, manifest)
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
        for attempt in range(1, fe.FIELD_ATTEMPTS + 1):
            try:
                rows, conditions = fe.field_rows(
                    root, manifest, night, traces.get(field_id, []), stage=STAGE, positions=True
                )
                break
            except Exception as exc:  # IRSA / VizieR hiccups; archival data, so a retry is safe
                if attempt == fe.FIELD_ATTEMPTS:
                    raise
                progress(f"{field_id}: attempt {attempt} failed ({exc}); retrying")
                time.sleep(30 * attempt)
        conditions["seconds"] = round(time.perf_counter() - started, 1)
        part.write_text(json.dumps({"rows": rows, "conditions": conditions}) + "\n")
        progress(f"{field_id}: {conditions['built_tracklets']} built, {conditions['seconds']} s")
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
                "manifest_sha256": rd.file_sha256(root / fe.MANIFEST_FILE),
                "stage": STAGE,
                "fields": conditions,
            },
            indent=1,
        )
        + "\n"
    )


def write_table(path: Path, rows: Sequence[Mapping]) -> None:
    from io import StringIO

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=TABLE_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: "" if r.get(k) is None else r[k] for k in TABLE_COLUMNS})
    with open(path, "wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz:
        gz.write(buffer.getvalue().encode())


def read_table(path: Path, manifest: Mapping) -> list[dict]:
    with gzip.open(path, "rt") as handle:
        rows = list(csv.DictReader(handle))
    for field_id in {r["field_id"] for r in rows}:
        rd.require_split(manifest, field_id, STAGE)
    for r in rows:
        for name in fe.RANKER_INPUT_COLUMNS:
            r[name] = float(r[name]) if r[name] != "" else None
    return rows


# ---------------------------------------------------------------------------
# V3 frozen scores
# ---------------------------------------------------------------------------


def frozen_scores(rows: Sequence[Mapping], spec: Mapping) -> list[float]:
    """score = sum_k w_k p_k + intercept over one quadrant-night (label-free)."""
    total = [float(spec["intercept"])] * len(rows)
    for item in spec["inputs"]:
        name, direction = item["feature"], int(item["direction"])
        weight = float(spec["weights"][name])
        p = rd.within_field_percentile([r[name] for r in rows], direction)
        total = [t + weight * (rc.MISSING_PERCENTILE if v is None else v) for t, v in zip(total, p)]
    return total


def null_scores(field_id: str, rows: Sequence[Mapping]) -> list[float]:
    return [rd.hash_score(field_id, r["tracklet_id"]) for r in rows]


# ---------------------------------------------------------------------------
# V4 strata
# ---------------------------------------------------------------------------

STAR_CLASSES = ("V<6", "V<6", "6-8", "8-10")


def star_class(proximity: Mapping) -> str:
    seps = proximity["separation_by_class"][:4]
    present = [(s, i) for i, s in enumerate(seps) if s is not None]
    if not present:
        return "none"
    return STAR_CLASSES[min(present)[1]]


def validation_strata(
    rows: Sequence[Mapping], fields: Sequence[Mapping], traces: Mapping[str, Sequence[Mapping]]
) -> dict[tuple[str, str], dict[str, str]]:
    strata = fe.positive_strata(rows, fields)
    for (field_id, designation), s in strata.items():
        trace = next(t for t in traces[field_id] if t["designation"] == designation)
        s["star_class"] = star_class(trace["proximity"])
    return strata


STRATA_KEYS = (*fe.STRATA_KEYS, "star_class")


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class Interval(BaseModel):
    point: float | None
    lower: float | None
    upper: float | None


class StratumResult(BaseModel):
    key: str
    value: str
    objects: float
    recall_5: float | None
    auc: float | None


class FieldResult(BaseModel):
    field_id: str
    group: str
    positives: float
    background: int
    auxiliary: int
    recall_5: float | None
    auc: float | None
    comparator_recall_5: float | None


class RankerResult(BaseModel):
    ranker: str
    role: str  # frozen ranker / frozen comparator / null reference
    objects: float
    fields_with_positive: int
    recall: dict[str, Interval]
    recall_at_budget: dict[str, Interval]
    enrichment: dict[str, float | None]
    auc: Interval
    median_q: Interval
    decision_level: rd.Decision
    descriptive_guards: list[rd.Guard]
    strata: list[StratumResult]
    sensitivity: dict[str, float | None]
    paired_difference: dict[str, Interval]


FRACTIONS = (rd.PRIMARY_FRACTION, *rd.SECONDARY_FRACTIONS)


def _ci(positives, statistic, label: str, resamples: int) -> Interval:
    lo, hi = rd.group_bootstrap(positives, statistic, label, resamples=resamples)
    return Interval(point=statistic(positives), lower=lo, upper=hi)


def _median_q(positives: Sequence[rd.RankedPositive]) -> float | None:
    """Weighted median of q (object-night weights)."""
    items = sorted((p.q, p.weight) for p in positives)
    total = sum(w for _, w in items)
    if total == 0:
        return None
    running = 0.0
    for q, w in items:
        running += w
        if running >= total / 2:
            return q
    return items[-1][0]


def descriptive_guards(positives: Sequence[rd.RankedPositive]) -> list[rd.Guard]:
    """V8 (never deciding)."""
    near = [p for p in positives if p.strata["proximity_group"] in rd.DEVELOPMENT_NEAR_GROUPS]
    return [
        rd.guard(
            "near-star (zone+outer) vs control [AS-039 development definition]",
            near,
            rd.stratum(positives, "proximity_group", "control"),
            rd.MIN_ZONE_POSITIVES,
        ),
        rd.guard(
            "near-star (zone+outer) vs intermediate+control",
            rd.stratum(positives, "near_star", "zone+outer"),
            rd.stratum(positives, "near_star", "intermediate+control"),
            rd.MIN_ZONE_POSITIVES,
        ),
        rd.guard(
            "zone PRIMARY vs control PRIMARY",
            [p for p in positives if p.strata["proximity_group"] == "zone" and p.strata["role"] == "primary"],
            [p for p in positives if p.strata["proximity_group"] == "control" and p.strata["role"] == "primary"],
            rd.MIN_ZONE_POSITIVES,
        ),
        rd.guard(
            "control MARGINAL vs control PRIMARY",
            [p for p in positives if p.strata["proximity_group"] == "control" and p.strata["role"] == "marginal"],
            [p for p in positives if p.strata["proximity_group"] == "control" and p.strata["role"] == "primary"],
            rd.MIN_FAINT_POSITIVES,
        ),
    ]


def evaluate_ranker(
    name: str,
    role: str,
    positives: Sequence[rd.RankedPositive],
    sensitivity: Mapping[str, float | None],
    resamples: int,
) -> RankerResult:
    tag = f"AS-040/{name}"
    decision = rd.decide(positives, DECISION_LABEL if name == FROZEN_RANKER else f"{tag}/recall5")
    strata_out = []
    for key in STRATA_KEYS:
        for value in sorted({p.strata[key] for p in positives}):
            members = rd.stratum(positives, key, value)
            strata_out.append(
                StratumResult(
                    key=key,
                    value=value,
                    objects=rd.object_count(members),
                    recall_5=rd.recall_at_fraction(members, rd.PRIMARY_FRACTION),
                    auc=rd.within_field_auc(members),
                )
            )
    recall = {
        f"{f:g}": _ci(positives, lambda s, f=f: rd.recall_at_fraction(s, f), f"{tag}/recall@{f:g}", resamples)
        for f in FRACTIONS
    }
    return RankerResult(
        ranker=name,
        role=role,
        objects=rd.object_count(positives),
        fields_with_positive=len({p.field_id for p in positives}),
        recall=recall,
        recall_at_budget={
            str(k): _ci(positives, lambda s, k=k: rd.recall_at_budget(s, k), f"{tag}/recall@K{k}", resamples)
            for k in rd.SECONDARY_BUDGETS
        },
        enrichment={f"{f:g}": rd.enrichment(positives, f) for f in FRACTIONS},
        auc=_ci(positives, rd.within_field_auc, f"{tag}/auc", resamples),
        median_q=_ci(positives, _median_q, f"{tag}/median_q", resamples),
        decision_level=decision,
        descriptive_guards=descriptive_guards(positives),
        strata=strata_out,
        sensitivity=dict(sensitivity),
        paired_difference={},
    )


def end_to_end(
    positives: Sequence[rd.RankedPositive], fields: Sequence[Mapping]
) -> dict[str, dict[str, float | None]]:
    """V9: eligible targets whose object is in the top 5 %, by proximity group."""
    q = {(p.field_id, p.designation): p.q for p in positives}
    rows = []
    for f in fields:
        for t in f["targets"]:
            hit = (f["field_id"], t["designation"]) in q and q[(f["field_id"], t["designation"])] <= rd.PRIMARY_FRACTION
            rows.append((t["designation"], f["night"], t["group"], t["role"], hit))
    copies = Counter((d, n) for d, n, *_ in rows)
    out = {}
    for name, keep in (
        ("all", lambda g, r: True),
        ("zone", lambda g, r: g == "zone"),
        ("outer", lambda g, r: g == "outer"),
        ("intermediate", lambda g, r: g == "intermediate"),
        ("control", lambda g, r: g == "control"),
        ("primary", lambda g, r: r == "primary"),
        ("marginal", lambda g, r: r == "marginal"),
    ):
        members = [(1 / copies[(d, n)], hit) for d, n, g, r, hit in rows if keep(g, r)]
        total = sum(w for w, _ in members)
        out[name] = {
            "eligible_object_nights": total,
            "top5_object_nights": sum(w for w, hit in members if hit),
            "end_to_end_recall_5": (sum(w for w, hit in members if hit) / total) if total else None,
        }
    return out


# ---------------------------------------------------------------------------
# Failure analysis (V11) and strips (V12)
# ---------------------------------------------------------------------------


def best_rows(
    rows_by_field: Mapping[str, Sequence[Mapping]], scores: Mapping[str, Sequence[float]]
) -> dict[tuple[str, str], tuple[Mapping, int]]:
    """(field, designation) -> (best-scored positive row, its index)."""
    best: dict[tuple[str, str], tuple[Mapping, int]] = {}
    for field_id, rows in rows_by_field.items():
        for i, r in enumerate(rows):
            if r["label"] != rd.POSITIVE:
                continue
            key = (field_id, r["eval_designation"])
            if key not in best or scores[field_id][i] > scores[field_id][best[key][1]]:
                best[key] = (r, i)
    return best


def missed_positives(
    positives: Sequence[rd.RankedPositive],
    comparator: Sequence[rd.RankedPositive],
    rows_by_field: Mapping[str, Sequence[Mapping]],
    scores: Mapping[str, Sequence[float]],
    spec: Mapping,
) -> list[dict]:
    best = best_rows(rows_by_field, scores)
    cq = {(p.field_id, p.designation): p.q for p in comparator}
    percentiles = {}
    for field_id, rows in rows_by_field.items():
        percentiles[field_id] = {
            item["feature"]: rd.within_field_percentile([r[item["feature"]] for r in rows], int(item["direction"]))
            for item in spec["inputs"]
        }
    out = []
    for p in sorted(positives, key=lambda p: (-p.q, p.field_id, p.designation)):
        if p.q <= rd.PRIMARY_FRACTION:
            continue
        row, i = best[(p.field_id, p.designation)]
        out.append(
            {
                "field_id": p.field_id,
                "designation": p.designation,
                "tracklet_id": row["tracklet_id"],
                "weight": p.weight,
                "q": round(p.q, 4),
                "rank": p.rank,
                "comparator_q": round(cq[(p.field_id, p.designation)], 4),
                "score": round(scores[p.field_id][i], 4),
                "features": {item["feature"]: row[item["feature"]] for item in spec["inputs"]},
                "percentiles": {
                    name: (None if v[i] is None else round(v[i], 4)) for name, v in percentiles[p.field_id].items()
                },
                "strata": p.strata,
            }
        )
    return out


def counterexamples(
    result: RankerResult,
    positives: Sequence[rd.RankedPositive],
    comparator: Sequence[rd.RankedPositive],
    fields: Sequence[FieldResult],
) -> dict:
    overall = result.recall["0.05"].point or 0.0
    cq = {(p.field_id, p.designation): p.q for p in comparator}
    missed = [p for p in positives if p.q > rd.PRIMARY_FRACTION]

    def entry(p: rd.RankedPositive) -> dict:
        return {
            "field_id": p.field_id,
            "designation": p.designation,
            "q": round(p.q, 4),
            "comparator_q": round(cq[(p.field_id, p.designation)], 4),
            "strata": p.strata,
        }

    return {
        "fields_auc_below_half": [
            f.model_dump() for f in fields
            if f.auc is not None and f.positives >= fe.COUNTEREXAMPLE_MIN_POSITIVES and f.auc < 0.5
        ],
        "strata_recall_gap": [
            s.model_dump() for s in result.strata
            if s.recall_5 is not None and s.recall_5 < overall - rc.STRATUM_GAP_REPORT
        ],
        "bottom_half_positives": [entry(p) for p in sorted(positives, key=lambda p: -p.q) if p.q > 0.5],
        "missed_top5_by_stratum": {
            key: dict(sorted(Counter(p.strata[key] for p in missed).items()))
            for key in ("role", "proximity_group", "star_class", "depth_margin", "mask_state", "crowding", "speed")
        },
        "comparator_only_top5": [
            entry(p) for p in positives
            if p.q > rd.PRIMARY_FRACTION and cq[(p.field_id, p.designation)] <= rd.PRIMARY_FRACTION
        ],
        "ranker_only_top5": [
            entry(p) for p in positives
            if p.q <= rd.PRIMARY_FRACTION and cq[(p.field_id, p.designation)] > rd.PRIMARY_FRACTION
        ],
    }


def strip_key(field_id: str, item: str) -> str:
    return hashlib.sha256(f"{STRIP_SALT}:{field_id}:{item}".encode()).hexdigest()


def shortlist_background(
    rows_by_field: Mapping[str, Sequence[Mapping]], scores: Mapping[str, Sequence[float]]
) -> list[dict]:
    """Background tracklets in their quadrant-night's M1 top 5 %."""
    out = []
    for field_id, rows in rows_by_field.items():
        background = [s for r, s in zip(rows, scores[field_id]) if r["label"] == rd.BACKGROUND]
        for r, s in zip(rows, scores[field_id]):
            if r["label"] != rd.BACKGROUND:
                continue
            q = rd.background_rank_fraction(s, background)
            if q <= rd.PRIMARY_FRACTION:
                out.append({"field_id": field_id, "tracklet_id": r["tracklet_id"], "q": round(q, 4),
                            "score": round(s, 4), "proximity_group": r["ctx_proximity_group"]})
    return out


def pick_strips(missed: Sequence[Mapping], shortlist: Sequence[Mapping]) -> list[dict]:
    picks = [
        {"reason": "missed_positive", **m}
        for m in sorted(missed, key=lambda m: strip_key(m["field_id"], m["designation"]))[:STRIP_MISSED]
    ]
    picks += [
        {"reason": "shortlist_background", **b}
        for b in sorted(shortlist, key=lambda b: strip_key(b["field_id"], b["tracklet_id"]))[:STRIP_BACKGROUND]
    ]
    return picks


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


class Validation(BaseModel):
    generated_at: datetime
    stage: str
    code_commit: str | None
    frozen_check: FrozenCheck
    table_sha256: str
    validation_fields: int
    validation_groups: int
    ranked_tracklets: int
    labels: dict[str, int]
    positive_objects: float
    positive_fields: int
    verdict: str
    decision: rd.Decision
    rankers: list[RankerResult]
    fields: list[FieldResult]
    end_to_end: dict[str, dict[str, float | None]]
    shortlist_background: int
    shortlist_by_field: dict[str, int]
    missed: list[dict]
    counterexamples: dict
    strips: list[dict]
    development: dict


def load_validation(root: Path, out_dir: Path) -> tuple[dict, list[dict], list[dict], dict[str, list[dict]]]:
    manifest = fe.load_manifest(root)
    nights = validation_nights(manifest)
    rows = read_table(out_dir / TABLE_FILE, manifest)
    fields = json.loads((out_dir / FIELDS_FILE).read_text())["fields"]
    if sorted(f["field_id"] for f in fields) != sorted(q["field_id"] for q in nights):
        raise FrozenInputError("validation table does not hold exactly the 24 sealed quadrant-nights")
    for f in fields:
        rd.require_split(manifest, f["field_id"], STAGE)
    return manifest, rows, fields, load_validation_traces(root, manifest)


def rank(
    rows_by_field: Mapping[str, Sequence[Mapping]],
    scores: Mapping[str, Sequence[float]],
    strata: Mapping,
    **kwargs,
) -> list[rd.RankedPositive]:
    return rc.rank_positives(rows_by_field, scores, strata, **kwargs)


def development_comparison(root: Path, results: Mapping[str, RankerResult]) -> dict:
    """V13, descriptive only."""
    construction = json.loads((root / CONSTRUCTION_FILE).read_text())
    by_name = {r["ranker"]: r for r in construction["rankers"]}
    out = {
        "development_fields": construction["development_fields"],
        "development_positive_objects": construction["positive_objects"],
        "rankers": {},
    }
    for name in (FROZEN_RANKER, FROZEN_COMPARATOR, "B0"):
        dev, val = by_name[name], results[name]
        guards = {g["name"]: g for g in dev["guards"]}
        val_faint = next(g for g in val.decision_level.guards if g.name.startswith("faint"))
        val_near_dev = val.descriptive_guards[0]
        rows = {
            "recall@5%": (dev["recall_5"]["point"], val.recall["0.05"].point),
            "recall@1%": (dev["recall"]["0.01"], val.recall["0.01"].point),
            "recall@2%": (dev["recall"]["0.02"], val.recall["0.02"].point),
            "recall@10%": (dev["recall"]["0.1"], val.recall["0.1"].point),
            "recall@20%": (dev["recall"]["0.2"], val.recall["0.2"].point),
            "recall@K10": (dev["recall_at_budget"]["10"], val.recall_at_budget["10"].point),
            "recall@K25": (dev["recall_at_budget"]["25"], val.recall_at_budget["25"].point),
            "recall@K50": (dev["recall_at_budget"]["50"], val.recall_at_budget["50"].point),
            "AUC": (dev["auc"]["point"], val.auc.point),
            "faint guard difference": (guards["faint (MARGINAL) vs PRIMARY"]["difference"], val_faint.difference),
            "MARGINAL recall@5%": (guards["faint (MARGINAL) vs PRIMARY"]["protected_recall"], val_faint.protected_recall),
            "PRIMARY recall@5%": (guards["faint (MARGINAL) vs PRIMARY"]["reference_recall"], val_faint.reference_recall),
            "zone+outer vs control difference": (
                guards["near-star (zone+outer) vs control"]["difference"], val_near_dev.difference
            ),
        }
        out["rankers"][name] = {
            k: {
                "development": d,
                "validation": v,
                "validation_minus_development": None if d is None or v is None else v - d,
            }
            for k, (d, v) in rows.items()
        }
        out["rankers"][name]["development_recall_5_ci"] = [dev["recall_5"]["lower"], dev["recall_5"]["upper"]]
        out["rankers"][name]["validation_recall_5_ci"] = [val.recall["0.05"].lower, val.recall["0.05"].upper]
    return out


def evaluate(
    root: Path,
    out_dir: Path,
    resamples: int = rd.BOOTSTRAP_RESAMPLES,
    progress: Callable[[str], None] = lambda m: None,
) -> Validation:
    check = verify_frozen_inputs(root)
    frozen = json.loads((root / FROZEN_RANKER_FILE).read_text())
    manifest, rows, fields, traces = load_validation(root, out_dir)
    rows_by_field: dict[str, list[Mapping]] = defaultdict(list)
    for r in rows:
        rows_by_field[r["field_id"]].append(r)
    strata = validation_strata(rows, fields, traces)

    specs = {FROZEN_RANKER: frozen["ranker"], FROZEN_COMPARATOR: frozen["comparator"]}
    scores: dict[str, dict[str, list[float]]] = {
        name: {f: frozen_scores(rs, spec) for f, rs in rows_by_field.items()} for name, spec in specs.items()
    }
    scores["B0"] = {f: null_scores(f, rs) for f, rs in rows_by_field.items()}
    roles = {FROZEN_RANKER: "frozen ranker", FROZEN_COMPARATOR: "frozen comparator", "B0": "null reference"}

    ranked: dict[str, list[rd.RankedPositive]] = {}
    results: dict[str, RankerResult] = {}
    for name in (FROZEN_RANKER, FROZEN_COMPARATOR, "B0"):
        progress(f"scoring {name}")
        positives = rank(rows_by_field, scores[name], strata)
        sensitivity = {}
        for label, kwargs in (
            ("without background sharing a detection with a positive",
             {"exclude_background": lambda r: r["shares_detection_with_positive"] == "1"}),
            (f"without {fe.CROSS_SPLIT_DESIGNATION}",
             {"exclude_designations": frozenset({fe.CROSS_SPLIT_DESIGNATION})}),
        ):
            alt = rank(rows_by_field, scores[name], strata, **kwargs)
            sensitivity[label + " (recall@5%)"] = rd.recall_at_fraction(alt, rd.PRIMARY_FRACTION)
            sensitivity[label + " (AUC)"] = rd.within_field_auc(alt)
        ranked[name] = positives
        results[name] = evaluate_ranker(name, roles[name], positives, sensitivity, resamples)

    m1 = results[FROZEN_RANKER]
    m1.paired_difference = {
        f"- {other}": rc.paired_difference(
            ranked[FROZEN_RANKER], ranked[other], f"AS-040/{FROZEN_RANKER}/minus-{other}", resamples
        )
        for other in (FROZEN_COMPARATOR, "B0")
    }
    decision = m1.decision_level

    field_results = []
    for f in fields:
        field_id = f["field_id"]
        members = [p for p in ranked[FROZEN_RANKER] if p.field_id == field_id]
        comp = [p for p in ranked[FROZEN_COMPARATOR] if p.field_id == field_id]
        labels = Counter(r["label"] for r in rows_by_field[field_id])
        field_results.append(
            FieldResult(
                field_id=field_id,
                group=f["group"],
                positives=rd.object_count(members),
                background=labels[rd.BACKGROUND],
                auxiliary=labels[rd.AUXILIARY],
                recall_5=rd.recall_at_fraction(members, rd.PRIMARY_FRACTION),
                auc=rd.within_field_auc(members),
                comparator_recall_5=rd.recall_at_fraction(comp, rd.PRIMARY_FRACTION),
            )
        )
    missed = missed_positives(
        ranked[FROZEN_RANKER], ranked[FROZEN_COMPARATOR], rows_by_field, scores[FROZEN_RANKER], specs[FROZEN_RANKER]
    )
    shortlist = shortlist_background(rows_by_field, scores[FROZEN_RANKER])
    reference = ranked[FROZEN_RANKER]
    return Validation(
        generated_at=datetime.now(timezone.utc),
        stage=STAGE,
        code_commit=rc.git_commit(root),
        frozen_check=check,
        table_sha256=rd.file_sha256(out_dir / TABLE_FILE),
        validation_fields=len(rows_by_field),
        validation_groups=len({r["group"] for r in rows}),
        ranked_tracklets=len(rows),
        labels=dict(Counter(r["label"] for r in rows)),
        positive_objects=rd.object_count(reference),
        positive_fields=len({p.field_id for p in reference}),
        verdict=decision.verdict,
        decision=decision,
        rankers=list(results.values()),
        fields=field_results,
        end_to_end=end_to_end(reference, fields),
        shortlist_background=len(shortlist),
        shortlist_by_field=dict(sorted(Counter(b["field_id"] for b in shortlist).items())),
        missed=missed,
        counterexamples=counterexamples(m1, reference, ranked[FROZEN_COMPARATOR], field_results),
        strips=pick_strips(missed, shortlist),
        development=development_comparison(root, results),
    )


def render_strips(root: Path, out_dir: Path, progress: Callable[[str], None] = lambda m: None) -> None:
    """V12: E1|E2|E3 cutouts of the pre-picked strips (evidence only)."""
    from fastapi.testclient import TestClient

    from app.main import app
    from app.validation.masked import render_strip, strip_geometry, write_png

    verify_frozen_inputs(root)
    manifest, rows, _, _ = load_validation(root, out_dir)
    validation = json.loads((out_dir / RESULTS_FILE).read_text())
    products = {q["field_id"]: q["product_ids"] for q in validation_nights(manifest)}
    by_key = {(r["field_id"], r["tracklet_id"]): r for r in rows}
    client = TestClient(app)
    (out_dir / "strips").mkdir(parents=True, exist_ok=True)
    for pick in validation["strips"]:
        row = by_key[(pick["field_id"], pick["tracklet_id"])]
        detections = [d.split() for d in row["det_positions"].split(";")]
        product_ids = products[pick["field_id"]]
        positions = [(float(ra), float(dec)) for _, ra, dec in detections]
        epochs = [product_ids.index(int(pid)) for pid, _, _ in detections]
        name = pick.get("designation") or f"t{pick['tracklet_id']}"
        image = f"strips/{pick['reason']}_{pick['field_id'].split('-')[0]}_{name.replace(' ', '_')}.png"
        progress(f"strip {image}")
        center, size = strip_geometry(positions)
        write_png(out_dir / image, render_strip(client, product_ids, center, size, positions, epochs))


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

_f = fe._f


def _ci_text(i: Interval, digits: int = 3) -> str:
    return f"{_f(i.point, digits)} [{_f(i.lower, digits)}, {_f(i.upper, digits)}]"


def _guard_text(g: rd.Guard) -> str:
    return rc._guard_text(g)


def render_markdown(v: Validation, review: Sequence[Mapping] = ()) -> str:
    d = v.decision
    by_name = {r.ranker: r for r in v.rankers}
    m1 = by_name[FROZEN_RANKER]
    lines = [
        "# AS-040 sealed validation of the frozen candidate ranker (stage 3; generated)",
        "",
        f"Generated {v.generated_at:%Y-%m-%d %H:%M UTC} from code `{v.code_commit}`. Interpretation: "
        "`as040_findings.md`. One-shot: nothing was fitted, selected or tuned.",
        "",
        "Frozen inputs verified before the validation table was built or read "
        f"({len(v.frozen_check.checks)} checks, `{VERIFY_FILE}`): manifest "
        f"`{v.frozen_check.file_sha256[fe.MANIFEST_FILE][:16]}…`, AS-038 table "
        f"`{v.frozen_check.file_sha256[f'{rc.AS038_DIR}/{fe.TABLE_FILE}'][:16]}…`, AS-038 list "
        f"`{v.frozen_check.file_sha256[rc.FROZEN_FEATURES_FILE][:16]}…`, AS-039 frozen ranker "
        f"`{v.frozen_check.file_sha256[FROZEN_RANKER_FILE][:16]}…`; validation digest "
        f"`{v.frozen_check.validation_digest[:16]}…`.",
        "",
        f"{v.validation_fields} validation quadrant-nights in {v.validation_groups} groups; {v.ranked_tracklets} "
        f"ranked tracklets {v.labels}; validation table `{v.table_sha256[:16]}…`. Positive object-nights "
        f"{v.positive_objects:g} in {v.positive_fields} quadrant-nights.",
        "",
        "## Confirmatory verdict (ranking_design.decide, AS-037 §7)",
        "",
        f"**{v.verdict}**",
        "",
        f"- M1 recall@5 % = {_f(d.recall)} [95 % group bootstrap {_f(d.ci_95[0])}, {_f(d.ci_95[1])}]; "
        f"thresholds: point ≥ {rd.USEFUL_RECALL}, lower ≥ {rd.USEFUL_LOWER}; NOT USEFUL if upper < {rd.USEFUL_RECALL}.",
        f"- Minimums: {d.positive_objects:g} ≥ {rd.MIN_POSITIVE_OBJECTS} object-nights, {d.positive_fields} ≥ "
        f"{rd.MIN_POSITIVE_FIELDS} quadrant-nights with a positive.",
    ]
    for g in d.guards:
        lines.append(f"- Guard {g.name}: {_guard_text(g)}")
    lines += [f"- {r}" for r in d.reasons]
    lines += [
        "",
        "## Primary and secondary metrics (95 % group bootstrap, 2000)",
        "",
        "| ranker | role | recall@1 % | recall@2 % | **recall@5 %** | recall@10 % | recall@20 % | AUC | median q |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in v.rankers:
        lines.append(
            f"| `{r.ranker}` | {r.role} | " + " | ".join(_ci_text(r.recall[k]) for k in ("0.01", "0.02", "0.05", "0.1", "0.2"))
            + f" | {_ci_text(r.auc)} | {_ci_text(r.median_q)} |"
        )
    lines += ["", "| ranker | recall@K10 | recall@K25 | recall@K50 | enrichment@1/2/5/10/20 % |", "|---|---|---|---|---|"]
    for r in v.rankers:
        lines.append(
            f"| `{r.ranker}` | " + " | ".join(_ci_text(r.recall_at_budget[k]) for k in ("10", "25", "50"))
            + " | " + " / ".join(_f(r.enrichment[k], 1) for k in ("0.01", "0.02", "0.05", "0.1", "0.2")) + " |"
        )
    lines += [
        "",
        "## Comparator analysis (secondary, never deciding)",
        "",
        "| contrast | recall@5 % difference [95 % paired group bootstrap] |",
        "|---|---|",
    ]
    for name, i in m1.paired_difference.items():
        lines.append(f"| `M1` {name} | {_ci_text(i)} |")
    ce = v.counterexamples
    lines += [
        "",
        f"Top 5 % by M1 only: {len(ce['ranker_only_top5'])}; by `{FROZEN_COMPARATOR}` only: "
        f"{len(ce['comparator_only_top5'])}.",
        "",
        "| ranker | decide() level on validation (descriptive for non-M1) | faint guard | zone guard |",
        "|---|---|---|---|",
    ]
    for r in v.rankers:
        g = {x.name: x for x in r.decision_level.guards}
        lines.append(
            f"| `{r.ranker}` | {r.decision_level.verdict} | {_guard_text(g['faint (MARGINAL) vs PRIMARY'])} "
            f"| {_guard_text(g['near-star zone vs control'])} |"
        )
    lines += ["", "## Descriptive guard views (never deciding)", "", "| ranker | view | result |", "|---|---|---|"]
    for r in v.rankers:
        for g in r.descriptive_guards:
            lines.append(f"| `{r.ranker}` | {g.name} | {_guard_text(g)} |")
    lines += ["", "## Strata (recall@5 % / AUC, object-nights)", "", "| stratum | n | " + " | ".join(f"`{r.ranker}`" for r in v.rankers) + " |", "|---|---|" + "---|" * len(v.rankers)]
    for i, s in enumerate(m1.strata):
        lines.append(
            f"| {s.key}={s.value} | {s.objects:g} | "
            + " | ".join(f"{_f(r.strata[i].recall_5, 2)} / {_f(r.strata[i].auc, 2)}" for r in v.rankers) + " |"
        )
    lines += [
        "",
        "## End-to-end (secondary): eligible targets recovered and in the top 5 % (M1)",
        "",
        "| stratum | eligible object-nights | recovered + top 5 % | end-to-end recall |",
        "|---|---|---|---|",
    ]
    for name, e in v.end_to_end.items():
        lines.append(
            f"| {name} | {e['eligible_object_nights']:g} | {e['top5_object_nights']:g} | {_f(e['end_to_end_recall_5'])} |"
        )
    lines += ["", "## Sensitivity (descriptive)", "", "| ranker | analysis | value |", "|---|---|---|"]
    for r in v.rankers:
        for name, value in r.sensitivity.items():
            lines.append(f"| `{r.ranker}` | {name} | {_f(value)} |")
    lines += [
        "",
        "## Per quadrant-night",
        "",
        "| field | group | positives | background | auxiliary | M1 recall@5 % | M1 AUC | comparator recall@5 % | shortlist background |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for f in v.fields:
        lines.append(
            f"| {f.field_id} | {f.group} | {f.positives:g} | {f.background} | {f.auxiliary} | {_f(f.recall_5, 2)} "
            f"| {_f(f.auc, 3)} | {_f(f.comparator_recall_5, 2)} | {v.shortlist_by_field.get(f.field_id, 0)} |"
        )
    lines += ["", "## Development (AS-039 CV) vs validation (descriptive only)", ""]
    for name, rows in v.development["rankers"].items():
        lines += [f"### `{name}`", "", "| metric | development | validation | validation − development |", "|---|---|---|---|"]
        for metric, x in rows.items():
            if isinstance(x, dict):
                lines.append(
                    f"| {metric} | {_f(x['development'])} | {_f(x['validation'])} | {_f(x['validation_minus_development'])} |"
                )
        lines.append(
            f"| recall@5 % 95 % CI | {_f(rows['development_recall_5_ci'][0])}–{_f(rows['development_recall_5_ci'][1])} "
            f"| {_f(rows['validation_recall_5_ci'][0])}–{_f(rows['validation_recall_5_ci'][1])} | |"
        )
        lines.append("")
    lines += [
        "## Counterexamples and failure cases (M1)",
        "",
        f"- Quadrant-nights (≥ 3 positives) with AUC < 0.5: "
        + (", ".join(f"{x['field_id']} ({_f(x['auc'], 2)})" for x in ce["fields_auc_below_half"]) or "none"),
        "- Strata with recall@5 % more than 0.20 below overall: "
        + (", ".join(f"{s['key']}={s['value']} ({_f(s['recall_5'], 2)}, n {s['objects']:g})" for s in ce["strata_recall_gap"]) or "none"),
        f"- Positives in the bottom half (q > 0.5): {len(ce['bottom_half_positives'])}",
        "- Missed (q > 0.05) by stratum: "
        + "; ".join(f"{k}: " + ", ".join(f"{a} {b}" for a, b in c.items()) for k, c in ce["missed_top5_by_stratum"].items()),
        "",
        f"### Every validation positive outside the M1 top 5 % ({len(v.missed)})",
        "",
        "| field | object | w | q | comparator q | role | group | star | depth | mask | crowding | "
        + " | ".join(f"p `{n}`" for n in rc.FROZEN_FEATURES) + " |",
        "|---|---|---|---|---|---|---|---|---|---|---|" + "---|" * len(rc.FROZEN_FEATURES),
    ]
    for m in v.missed:
        s = m["strata"]
        lines.append(
            f"| {m['field_id'].split('-')[0]} | {m['designation']} | {m['weight']:g} | {m['q']:.3f} | {m['comparator_q']:.3f} "
            f"| {s['role']} | {s['proximity_group']} | {s['star_class']} | {s['depth_margin']} | {s['mask_state']} "
            f"| {s['crowding']} | " + " | ".join(_f(m["percentiles"][n], 2) for n in rc.FROZEN_FEATURES) + " |"
        )
    lines += [
        "",
        f"## Evidence strips (agent labels, not ground truth)",
        "",
        f"Shortlist background (M1 top 5 % of each quadrant-night's background): {v.shortlist_background} tracklets.",
        "",
    ]
    reviewed = {(x["field_id"], x["tracklet_id"]): x for x in review}
    if v.strips:
        lines += ["| strip | field | tracklet | q | label | notes |", "|---|---|---|---|---|---|"]
        for p in v.strips:
            x = reviewed.get((p["field_id"], p["tracklet_id"]), {})
            name = p.get("designation") or f"t{p['tracklet_id']}"
            lines.append(
                f"| {p['reason']} {name} | {p['field_id'].split('-')[0]} | {p['tracklet_id']} | {p['q']:.3f} "
                f"| {x.get('label', '–')} | {x.get('notes', '')} |"
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name, text in (
        ("verify", "verify the frozen inputs only (offline, no validation data)"),
        ("table", "validation feature table (IRSA + VizieR)"),
        ("evaluate", "one-shot frozen-ranker evaluation and verdict (offline)"),
        ("strips", "evidence strips of the pre-picked tracklets (IRSA cutouts)"),
    ):
        p = sub.add_parser(name, help=text)
        p.add_argument("--root", type=Path, default=Path("."))
        p.add_argument("--out-dir", type=Path, default=Path("validation/results/as040"))
        if name == "table":
            p.add_argument("--cache-dir", type=Path, default=CACHE_DIR)
            p.add_argument("--field", action="append")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    progress = lambda m: print(m, flush=True)  # noqa: E731
    if args.command == "verify":
        check = verify_frozen_inputs(args.root)
        (args.out_dir / VERIFY_FILE).write_text(check.model_dump_json(indent=1) + "\n")
        print(f"frozen inputs verified: {len(check.checks)} checks")
    elif args.command == "table":
        build_table(args.root, args.out_dir, args.cache_dir,
                    only=set(args.field) if args.field else None, progress=progress)
    elif args.command == "evaluate":
        validation = evaluate(args.root, args.out_dir, progress=progress)
        (args.out_dir / RESULTS_FILE).write_text(validation.model_dump_json(indent=1) + "\n")
        review_path = args.out_dir / REVIEW_FILE
        review = json.loads(review_path.read_text()) if review_path.exists() else []
        (args.out_dir / REPORT_FILE).write_text(render_markdown(validation, review))
        print(f"verdict: {validation.verdict}")
    else:
        render_strips(args.root, args.out_dir, progress=progress)


if __name__ == "__main__":
    main()
