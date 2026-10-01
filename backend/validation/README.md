# AS-022 positive-control validation

Frozen ZTF field definitions, a pre-registered known-object target rule and
a reproducible run of the unchanged AS-010–AS-021 pipeline on them.

- `fields.json` – frozen validation fields (ZTF product ids).
- `results/as022_validation.json` – machine-readable run: IRSA frame
  metadata, the SkyBoT predictions used (snapshot), selected targets,
  reference-config results with per-tracklet features, and the parameter
  sweep.
- `results/as022_validation.md` – tables generated from the JSON.
- `results/as022_findings.md` – interpretation of the run.

Run (from `backend/`, needs network access to IRSA and SkyBoT):

```
python -m app.validation --fields validation/fields.json \
    --out-json validation/results/as022_validation.json \
    --out-md validation/results/as022_validation.md
```

## How fields were chosen

A field is one ZTF CCD quadrant observed at least 3 times in one night.
Candidate positions were chosen near the ecliptic at different dates
without looking at pipeline output. IRSA was searched by position and
month, and the quadrant-nights with ≥ 3 exposures were taken. When a night
had more than 3 exposures, the first, middle and last were used (rule fixed
before any run). The POC field is also included.

## How targets were chosen (pre-registered, no pipeline output used)

For every frame, SkyBoT is queried at mid-exposure (UTC, observer I41) over
the whole quadrant. A known object is a target when:

1. SkyBoT lists it in every frame;
2. its predicted position is inside the quadrant footprint (IRSA corner
   coordinates) in every frame;
3. its SkyBoT position error is ≤ 1 arcsec;
4. its V magnitude is ≤ (faintest frame 5σ `maglimit`) − 0.5 → **primary**,
   or ≤ that maglimit + 0.5 → **marginal**.

`control_designations` in `fields.json` are added by human choice (role
**control**, reported separately): 48606 (1995 DH) and 285862 (2001 HM48)
in the POC field. Neither passes the rule, because the POC's third frame
has maglimit 19.24.

A target is **recovered** when a tracklet is identified as KNOWN with that
target as best match.

## Reproducibility notes

- IRSA products are archival and fixed; the product ids are frozen here.
- SkyBoT ephemerides change as orbits are updated (the SkyBoT database is
  updated daily). The JSON keeps the exact predictions used, but a re-run
  queries SkyBoT again and may differ slightly (sub-arcsec for well-known
  orbits). The AS-024 acceptance replays these frozen predictions by
  default.

## AS-023 end-to-end run

`python -m app.validation.end_to_end --out-json validation/results/as023_end_to_end.json --out-md validation/results/as023_end_to_end.md`

Runs the production path live (IRSA metadata by product id → PSF catalogs
→ stationary matching → tracklets → live SkyBoT `identify_tracklets`) on
the 21 canonical primary targets. PASS when at least one target is
identified correctly and none is misidentified. Exit code 0 = PASS.

## AS-024 scientific acceptance

`python -m app.validation.acceptance --out-json validation/results/as024_acceptance.json --out-md validation/results/as024_acceptance.md [--live-skybot]`

Per target, levels from 05 – Scientific Validation: A software, B geometric
(tracklet at the predicted positions, ≥ 3 detections, accepted fit),
C astrometric (every detection ≤ 1.0" from the frozen prediction,
|rate − predicted| ≤ 0.02"/min, |PA − predicted| ≤ 2°), D identification
(KNOWN with the target's designation). Tolerances and their derivation are
in `app/validation/acceptance.py`. Suite PASS: no misidentified target, no
identified target outside tolerance, and ≥ 16 passing targets (AS-022
regression floor, not a scientific requirement). By default SkyBoT is
replayed from the AS-022 snapshot so PASS/FAIL does not drift with the
SkyBoT database. Exit code 0 = PASS.

## AS-031 tracklet quality features

`python -m app.validation.quality --out-json validation/results/as031_quality_features.json --out-md validation/results/as031_quality_features.md [--all-records]`

Runs the unchanged pipeline (experimental defaults) on the four AS-022
fields, identifies against the frozen AS-022 SkyBoT snapshot and extracts
`TrackletQualityFeatures` (`docs/tracklet_quality_features.md`) for every
tracklet, with the raw PSF-catalog `sharp` supplied. Output: per-field
data checks, group summaries (count, missing, min, 10/25/50/75/90th
percentile, max; categorical counts for flags) and the per-tracklet records
of identified tracklets (`--all-records` adds the ~6000 UNKNOWN ones,
~5 MB). Descriptive only — no score, rank or threshold. Interpretation and
selection effects: `results/as031_findings.md`. Needs IRSA; ~2 min, ~5 GB
peak memory (crowded field D).

## AS-032 masked-tracklet investigation

`python -m app.validation.masked --out-dir validation/results/as032`

Fields B and D only. Puts every tracklet in context (per-detection ZTF
mask bits with their ZSDS §10.3 meaning, distance to the field's
bit-12 halo star, shared detections, AS-031 features), draws a
deterministic stratified sample (SHA-256 of field and tracklet id) and
renders E1|E2|E3 strips through `/api/frames/cutout` + `/api/frames/project`
(GAB-100 cache, AS-030 projection). `visual_review.json` holds the visual
labels (written by hand, merged into the generated report). Evidence
only — no filter, score, rank or threshold. Interpretation:
`results/as032/as032_findings.md`. Needs IRSA; ~1.5 min.

## AS-033 bright-star contamination on independent fields

```
python -m app.validation.bright_stars select --out validation/results/as033/as033_fields.json
python -m app.validation.bright_stars evidence --fields validation/results/as033/as033_fields.json --out-dir validation/results/as033 [--all-records]
```

`select` applies the pre-registered field rule (Tycho-2 V <= 6.5 stars in
the ecliptic band, SHA-256 order; earliest ZTF quadrant-night with >= 3
exposures and archived products; first/middle/last exposure). `evidence`
runs B and D (frozen SkyBoT) and the selected fields (SkyBoT replayed from
`as033_skybot.json` when present), measures each tracklet's great-circle
separation from the nearest V <= 6.5 Tycho-2 star, and reports
area-normalised densities, mask composition and quality features in
fixed radial bins (0-10' in 2' steps, 10-15', >= 15' control), plus a
hash-ordered visual sample. Evidence only — no filter, radius, score,
rank or threshold. Interpretation: `results/as033/as033_findings.md`.
Needs IRSA and VizieR; ~4 min, ~5.5 GB peak memory (field D).

## AS-034 contamination as star magnitude × distance

```
python -m app.validation.star_contamination select --out validation/results/as034/as034_population.json
python -m app.validation.star_contamination evidence --population validation/results/as034/as034_population.json --out-dir validation/results/as034
python -m app.validation.star_contamination render --out-dir validation/results/as034
```

Pre-registered (commit e805002): Tycho-2 stars to V <= 11 in 2-mag
classes, doubling annuli 0-480" around each star with 480-900" as the
local background, isolated-star primary profiles, the 26-quadrant
population (AS-022/033 fields + sibling quadrants), the KNOWN rule (AS-022
target rule) and the strip rule. Produces explicit per-position proximity
features (`StarProximity`), stacked area-normalised profiles of built /
rejected UNKNOWN and built KNOWN tracklets with mask and quality summaries,
KNOWN loss stages by closest approach to a star, and a reviewed strip
sample. Evidence only — no filter, radius, score, rank or threshold.
Interpretation: `results/as034/as034_findings.md`. ~35 min, ~8.6 GB peak.

## AS-035 known-object recovery near bright stars

```
python -m app.validation.known_recovery select --out validation/results/as035/as035_selection.json
python -m app.validation.known_recovery evidence --population N --selection validation/results/as035/as035_selection.json --out-dir validation/results/as035
python -m app.validation.known_recovery evidence --population R --out-dir validation/results/as035
python -m app.validation.known_recovery combine --out-dir validation/results/as035
python -m app.validation.known_recovery render --out-dir validation/results/as035
```

Pre-registered (commit fa4cd97) before any AS-035 outcome: `select` finds
new quadrant-nights (N) where SkyBoT predicts an AS-022-rule object
passing within 120" of a Tycho-2 V < 8 star (SHA-256 star order,
alternating V < 6 / 6-8, 12 per class), with a temporal-baseline sequence
rule (E2/E3 >= 15 min apart, span <= 150 min); R is the 26 AS-034
quadrants (not blind). `evidence` traces every AS-022-rule target of a
population stage by stage (expected position → detection → stationary /
moving → association → fit → identification; first failure point), with
rate / baseline eligibility, band-corrected global and local catalog
depth, and the closest predicted approach to Tycho-2 stars by class.
`combine` applies the pre-registered zone/control contrast and claim rule
and renders the strip sample. N SkyBoT predictions are stored in
`as035_skybot.json` and replayed. Evidence only — no filter, radius,
score, rank or threshold. Interpretation:
`results/as035/as035_findings.md`.

## AS-036 near-star PRIMARY recovery confirmation

```
python -m app.validation.near_star_confirmation select --out validation/results/as036/as036_selection.json
python -m app.validation.near_star_confirmation evidence --selection validation/results/as036/as036_selection.json --out-dir validation/results/as036
python -m app.validation.near_star_confirmation analyse --selection validation/results/as036/as036_selection.json --out-dir validation/results/as036
python -m app.validation.near_star_confirmation render --selection validation/results/as036/as036_selection.json --out-dir validation/results/as036
```

Confirmatory. Pre-registered (PRE-REGISTRATION block of
`app/validation/near_star_confirmation.py`) before any AS-036 search or
outcome: a new sample C of quadrant-nights (none of the AS-035 N/R ones)
from a star-driven search (Tycho-2 V < 6 and 6-8, SHA-256 'AS-036' order)
that examines up to 20 qualifying nights per star and triggers only on an
AS-022 PRIMARY, rate- and baseline-eligible object passing inside the
AS-035 zone of the star (< 120" V < 6, < 60" 6-8); budget per class 15
trigger objects / 300 stars / 3000 SkyBoT cones. AS-035 definitions
(sequence rule, target rule, eligibility strata, zone, control, six-stage
trace) are reused unchanged. Decision rule on C only: CONFIRMED (zone
n >= 20, control n >= 20, zone lower, Fisher p < 0.05, MH OR < 1),
NOT REPRODUCED (minimums met, Newcombe 95 % lower bound of zone - control
> -0.20), else INCONCLUSIVE. Pooled AS-035 + AS-036 is secondary only.
C SkyBoT predictions are stored in `as036_skybot.json` and replayed.
Evidence only — no filter, radius, score, rank or threshold.
Interpretation: `results/as036/as036_findings.md`.
