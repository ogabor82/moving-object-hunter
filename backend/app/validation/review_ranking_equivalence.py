"""AS-041: production M1 review ranking vs the frozen research scorer.

Two checks, both read-only on every frozen AS-037..040 artefact:

- `offline`: the production scorer (review_ranking_service.m1_scores) on
  the committed AS-038 development and AS-040 validation feature tables,
  quadrant-night by quadrant-night, against the research scorer
  sealed_validation.frozen_scores with the committed AS-039 frozen ranker.
  Scores must be bit-identical, so the review order is identical; the
  committed AS-039 development and AS-040 validation M1 recall@5 % / AUC
  are recomputed from the production scores.
- `live`: the API path from raw ZTF data (fetch_observations →
  build_tracklets_from_observations → rank_for_review, live IRSA PSF
  catalogs, no research loader) on selected quadrant-nights, against the
  committed table rows of the same quadrant-nights: the same built
  tracklets, the same 8 feature values, the same scores and the same
  review order.

Nothing is tuned, selected or re-evaluated: this only checks that the
production code computes the frozen M1.

    python -m app.validation.review_ranking_equivalence \\
        --out-dir validation/results/as041 [--live FIELD_ID ...]
"""

import argparse
import json
import time
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

from app.models.pipeline_config import EXPERIMENTAL_DEFAULT_CONFIG
from app.models.review_ranking import M1Features
from app.services import review_ranking_service as rr
from app.validation import feature_evaluation as fe
from app.validation import ranker_construction as rc
from app.validation import ranking_design as rd
from app.validation import sealed_validation as sv

RESULTS_FILE = "as041_equivalence.json"
REPORT_FILE = "as041_equivalence.md"
AS040_DIR = "validation/results/as040"
AS040_RESULTS = f"{AS040_DIR}/{sv.RESULTS_FILE}"

# Representative quadrant-nights for the live check: both splits, sparse
# and crowded (up to ~140 k sources per frame), masked / near-star fields,
# the AS-022 / AS-024 canonical fields and the blink-comparator default.
DEFAULT_LIVE_FIELDS = (
    "POC-2018-04-11-535-c11-q3",
    "C-2018-10-06-448-c9-q3",
    "D-2019-06-02-281-c16-q3",
    "C15-2019-01-04-500-c15-q4",
    "C27-2020-11-15-392-c7-q4",
    "C11-2020-08-27-447-c2-q1",
    "C24-2019-06-29-279-c5-q2",
)


def features_from_row(row: Mapping) -> M1Features:
    """A research table row's 8 M1 inputs as the production model."""
    values = {name: row[name] for name, _ in rr.M1_INPUTS}
    for name in ("flagged_detection_count", "masked_detection_count", "shared_detection_tracklets"):
        values[name] = int(values[name])
    return M1Features(**values)


def frozen_spec(root: Path) -> dict:
    return json.loads((root / sv.FROZEN_RANKER_FILE).read_text())["ranker"]


def check_spec(root: Path) -> dict:
    """The production constants equal the committed frozen ranker."""
    spec = frozen_spec(root)
    production = rr.m1_spec()
    frozen_inputs = [(i["feature"], int(i["direction"])) for i in spec["inputs"]]
    ok = (
        spec["ranker"] == production.ranker
        and frozen_inputs == list(rr.M1_INPUTS)
        and spec["weights"] == {name: rr.M1_WEIGHT for name, _ in rr.M1_INPUTS}
        and float(spec["intercept"]) == rr.M1_INTERCEPT
        and spec["fitted"] is False
        and rc.MISSING_PERCENTILE == rr.MISSING_PERCENTILE
    )
    return {"frozen_ranker_sha256": rd.file_sha256(root / sv.FROZEN_RANKER_FILE), "equal": ok}


def compare_field(rows: Sequence[Mapping], spec: Mapping) -> dict:
    """Production vs research scores of one quadrant-night's table rows."""
    research = sv.frozen_scores(rows, spec)
    production, _ = rr.m1_scores([features_from_row(r) for r in rows])
    research_order = sorted(range(len(rows)), key=lambda i: -research[i])
    return {
        "tracklets": len(rows),
        "scores_identical": production == research,
        "order_identical": rr.review_order(production) == research_order,
        "max_abs_difference": max((abs(p - r) for p, r in zip(production, research)), default=0.0),
    }


def _by_field(rows: Sequence[Mapping]) -> dict[str, list[Mapping]]:
    out: dict[str, list[Mapping]] = defaultdict(list)
    for r in rows:
        out[r["field_id"]].append(r)
    return out


def _production_scores(by_field: Mapping[str, Sequence[Mapping]]) -> dict[str, list[float]]:
    return {f: rr.m1_scores([features_from_row(r) for r in rs])[0] for f, rs in by_field.items()}


def offline(root: Path) -> dict:
    spec = frozen_spec(root)
    _, dev_rows, dev_fields = rc.load_development(root)
    _, val_rows, val_fields, traces = sv.load_validation(root, root / AS040_DIR)
    out: dict = {"spec": check_spec(root), "splits": {}}
    committed = json.loads((root / AS040_RESULTS).read_text())
    m1_committed = next(r for r in committed["rankers"] if r["ranker"] == sv.FROZEN_RANKER)
    construction = json.loads((root / sv.FROZEN_RANKER_FILE).read_text())["development_cv"]["M1"]
    for split, rows, strata, expected in (
        ("development (AS-038 table)", dev_rows, fe.positive_strata(dev_rows, dev_fields),
         {"recall_5": construction["recall_5"]["point"], "auc": construction["auc"]["point"]}),
        ("validation (AS-040 table)", val_rows, sv.validation_strata(val_rows, val_fields, traces),
         {"recall_5": m1_committed["recall"]["0.05"]["point"], "auc": m1_committed["auc"]["point"]}),
    ):
        by_field = _by_field(rows)
        fields = {f: compare_field(rs, spec) for f, rs in by_field.items()}
        positives = rc.rank_positives(by_field, _production_scores(by_field), strata)
        recomputed = {
            "recall_5": rd.recall_at_fraction(positives, rd.PRIMARY_FRACTION),
            "auc": rd.within_field_auc(positives),
        }
        out["splits"][split] = {
            "quadrant_nights": len(fields),
            "tracklets": sum(f["tracklets"] for f in fields.values()),
            "scores_identical_fields": sum(f["scores_identical"] for f in fields.values()),
            "order_identical_fields": sum(f["order_identical"] for f in fields.values()),
            "max_abs_difference": max(f["max_abs_difference"] for f in fields.values()),
            "m1_committed": expected,
            "m1_from_production_scores": recomputed,
            "metrics_identical": recomputed["recall_5"] == expected["recall_5"]
            and abs(recomputed["auc"] - expected["auc"]) <= 1e-12,
        }
    return out


def live_field(root: Path, field_id: str, table_rows: Sequence[Mapping], spec: Mapping) -> dict:
    """Run the production API path on one quadrant-night and compare."""
    from app.services.pipeline_service import build_tracklets_from_observations
    from app.services.ztf_service import fetch_observations

    manifest = fe.load_manifest(root)
    [night] = [q for q in manifest["quadrant_nights"] if q["field_id"] == field_id]
    started = time.perf_counter()
    observations = fetch_observations(list(night["product_ids"]))
    result = build_tracklets_from_observations(observations, EXPERIMENTAL_DEFAULT_CONFIG)
    ranking = rr.rank_for_review(
        result.build.tracklets, result.sharp_by_source_id(), observations, EXPERIMENTAL_DEFAULT_CONFIG
    )
    seconds = round(time.perf_counter() - started, 1)

    research_scores = sv.frozen_scores(table_rows, spec)
    research_ids = [r["tracklet_id"] for r in table_rows]
    research_order = [research_ids[i] for i in sorted(range(len(table_rows)), key=lambda i: -research_scores[i])]
    research = dict(zip(research_ids, zip(table_rows, research_scores)))

    candidates = {c.tracklet_id: c for c in ranking.candidates}
    feature_mismatches = []
    score_mismatches = []
    for tracklet_id, candidate in candidates.items():
        if tracklet_id not in research:
            continue
        row, score = research[tracklet_id]
        expected = features_from_row(row)
        got = {e.feature: e.value for e in candidate.evidence}
        if got != expected.model_dump():
            feature_mismatches.append(tracklet_id)
        if candidate.review_priority_score != score:
            score_mismatches.append(tracklet_id)
    return {
        "field_id": field_id,
        "split": night["split"],
        "frames": len(observations),
        "sources_per_frame": [f.source_count for f in result.frames],
        "tracklets": len(result.build.tracklets),
        "built_production": len(ranking.candidates),
        "built_research": len(table_rows),
        "unranked_rejected": len(ranking.unranked),
        "same_built_tracklets": sorted(candidates) == sorted(research_ids),
        "sharp_complete": sum(1 for c in ranking.candidates if c.sharp_availability.value == "complete"),
        "feature_mismatches": feature_mismatches,
        "score_mismatches": score_mismatches,
        "order_identical": [c.tracklet_id for c in ranking.candidates] == research_order,
        "domain_notes": ranking.domain_notes,
        "seconds": seconds,
    }


def live(root: Path, field_ids: Sequence[str], progress=lambda m: None) -> list[dict]:
    spec = frozen_spec(root)
    _, dev_rows, _ = rc.load_development(root)
    _, val_rows, _, _ = sv.load_validation(root, root / AS040_DIR)
    by_field = _by_field([*dev_rows, *val_rows])
    out = []
    for field_id in field_ids:
        progress(f"{field_id}: production pipeline (live IRSA)")
        out.append(live_field(root, field_id, by_field[field_id], spec))
        progress(f"{field_id}: {json.dumps(out[-1])}")
    return out


def passed(result: Mapping) -> bool:
    ok = result["offline"]["spec"]["equal"] and all(
        s["scores_identical_fields"] == s["quadrant_nights"]
        and s["order_identical_fields"] == s["quadrant_nights"]
        and s["metrics_identical"]
        for s in result["offline"]["splits"].values()
    )
    return ok and all(
        f["same_built_tracklets"] and not f["feature_mismatches"] and not f["score_mismatches"] and f["order_identical"]
        for f in result["live"]
    )


def render_markdown(result: Mapping) -> str:
    lines = [
        "# AS-041 — production M1 vs frozen research M1",
        "",
        f"Generated {result['generated_at']} — **{'EQUIVALENT' if result['equivalent'] else 'NOT EQUIVALENT'}**",
        "",
        "Production: `app/services/review_ranking_service.py` (API path). Research: "
        "`sealed_validation.frozen_scores` with `as039_frozen_ranker.json` "
        f"(sha256 `{result['offline']['spec']['frozen_ranker_sha256'][:12]}…`). "
        f"Production constants equal the frozen ranker: **{result['offline']['spec']['equal']}**.",
        "",
        "## Offline: committed feature tables",
        "",
        "| table | quadrant-nights | tracklets | identical scores | identical order | max abs diff "
        "| M1 recall@5 % committed / production | M1 AUC committed / production |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, s in result["offline"]["splits"].items():
        c, p = s["m1_committed"], s["m1_from_production_scores"]
        lines.append(
            f"| {name} | {s['quadrant_nights']} | {s['tracklets']} | {s['scores_identical_fields']}/{s['quadrant_nights']} "
            f"| {s['order_identical_fields']}/{s['quadrant_nights']} | {s['max_abs_difference']:.1e} "
            f"| {c['recall_5']:.6f} / {p['recall_5']:.6f} | {c['auc']:.6f} / {p['auc']:.6f} |"
        )
    lines += [
        "",
        "## Live: production API path from raw ZTF PSF catalogs",
        "",
        "`fetch_observations` → `build_tracklets_from_observations` (`load_frame_sources`, "
        "`sharp` kept by `catalog_service.psf_sharp_by_source_id`) → `rank_for_review`, "
        "compared with the committed table rows of the same quadrant-night.",
        "",
        "| quadrant-night | split | sources / frame | built (prod / table) | rejected (unranked) "
        "| sharp complete | same tracklets | feature mismatches | score mismatches | same order | s |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for f in result["live"]:
        lines.append(
            f"| {f['field_id']} | {f['split']} | {', '.join(str(n) for n in f['sources_per_frame'])} "
            f"| {f['built_production']} / {f['built_research']} | {f['unranked_rejected']} | {f['sharp_complete']} "
            f"| {f['same_built_tracklets']} | {len(f['feature_mismatches'])} | {len(f['score_mismatches'])} "
            f"| {f['order_identical']} | {f['seconds']} |"
        )
    if not result["live"]:
        lines.append("| (not run) | | | | | | | | | | |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--live", nargs="*", default=None,
                        help="quadrant-nights for the live check (no value: the default set)")
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    live_fields = [] if args.live is None else (args.live or list(DEFAULT_LIVE_FIELDS))
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "offline": offline(args.root),
        "live": live(args.root, live_fields, progress=lambda m: print(m, flush=True)),
    }
    result["equivalent"] = passed(result)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / RESULTS_FILE).write_text(json.dumps(result, indent=1) + "\n")
    (args.out_dir / REPORT_FILE).write_text(render_markdown(result))
    print(f"equivalent: {result['equivalent']}")


if __name__ == "__main__":
    main()
