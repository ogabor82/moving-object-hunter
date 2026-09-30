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
