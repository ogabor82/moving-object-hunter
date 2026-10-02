# AS-038 findings — candidate feature evaluation (stage 1, development only)

Generated evidence: `as038_evaluation.md` / `.json` (all metrics, strata,
Spearman matrices, sensitivity, counterexamples), the development feature
table `as038_feature_table.csv.gz` (one row per built tracklet), the
quadrant-night conditions `as038_fields.json`, and the frozen list
`as038_frozen_features.json`. Regenerate:

```
python -m app.validation.feature_evaluation table --out-dir validation/results/as038     # IRSA + VizieR, ~1 h
python -m app.validation.feature_evaluation evaluate --out-dir validation/results/as038  # offline, ~10 s
```

Protocol: AS-037 stage 1, unchanged (commit `abb97c0`). Details AS-037
leaves open were fixed as implementation decisions D1–D9 in
`app/validation/feature_evaluation.py` and committed in `b6290eb`, before
any development feature table or outcome existed. Nothing was changed
after the outcome: no metric, direction, gate, stratum or split.

No ranker, combined score, feature weight, threshold, filter or rejection
rule was built. UNKNOWN is background, not a ground-truth false positive.
Bright-star proximity is context and stratification only. The validation
split was not loaded.

## Run and data integrity

- **All 56 development quadrant-nights processed**; no pre-registered
  failure handling was needed. IRSA returned transient HTTP 504s, so each
  quadrant-night was retried up to 4 times. IRSA products are archival and
  SkyBoT is replayed, so a retry cannot change an outcome.
- **Split guard**: `require_split(manifest, field_id,
  "feature_evaluation")` runs before every load, both in the table runner
  and in the evaluator. A validation field id raises (tested). In shared
  input files (AS-036 traces, `as036_skybot.json`), validation rows are
  dropped by field id before use. No validation feature was extracted.
- **SkyBoT replay only (D1).** No live query was made.
- **Same pipeline as the traces**: the tracklet count of every
  quadrant-night equals the AS-035/036 trace count (56/56). Field D gives
  833 built UNKNOWN and B gives 88, as in AS-031.
- **Labels reconcile exactly**: 402 positive (quadrant-night, object)
  pairs labelled by `label_tracklet`, and the same 402 are "recovered" in
  the traces (0 in either difference). That is 402 positive object-nights
  in 49 quadrant-nights, as the AS-037 manifest predicted. Weights are all
  1, since no development object-night has copies.
- **Ranked tracklets**: 18 366 built (402 positive, 40 auxiliary,
  17 924 background).
- **Reproducibility**:
  - A fresh live rerun of N11 and C reproduces their rows exactly.
  - Re-running `evaluate` gives a bit-identical JSON apart from
    `generated_at`, because the bootstrap seeds are fixed.
  - The table gzip carries no name or mtime.
  - Tests check the table hash against the evaluation, and re-derive the
    frozen list from the committed metrics.

## Results per feature (pre-registered direction)

AUC = within-field AUC (object-night weighted mean of 1 − q). Intervals
are 95 % group bootstrap (2000). Gate:

- AUC lower bound > 0.55;
- MARGINAL point AUC ≥ 0.5;
- zone+outer point AUC ≥ 0.5;
- missing ≤ 5 %.

| feature | dir | AUC [95 %] | recall@5 % [95 %] | MARGINAL AUC [95 %] | zone+outer AUC [95 %] | missing | gate | AS-039 |
|---|---|---|---|---|---|---|---|---|
| `min_snr` | + | 0.827 [0.791, 0.873] | 0.512 [0.434, 0.617] | 0.635 [0.539, 0.731] | 0.892 [0.829, 0.945] | 0 % | PASS | **frozen** |
| `median_snr` | + | 0.820 [0.778, 0.874] | 0.517 [0.427, 0.642] | 0.614 [0.498, 0.720] | 0.865 [0.787, 0.932] | 0 % | PASS | **frozen** |
| `fit_rms_residual_arcsec` | − | 0.897 [0.872, 0.918] | 0.525 [0.430, 0.613] | 0.824 [0.788, 0.859] | 0.855 [0.819, 0.896] | 0 % | PASS | **frozen** |
| `fit_max_residual_arcsec` | − | 0.897 [0.873, 0.918] | 0.525 [0.426, 0.617] | 0.824 [0.790, 0.861] | 0.855 [0.816, 0.897] | 0 % | PASS | dropped: redundant with fit_rms (ρ = 0.999) |
| `magnitude_range_mag` | − | 0.800 [0.752, 0.854] | 0.209 [0.084, 0.383] | 0.808 [0.752, 0.865] | 0.818 [0.772, 0.872] | 0 % | PASS | **frozen** |
| `magnitude_range_sigma` | − | 0.602 [0.530, 0.676] | 0.087 [0.020, 0.198] | 0.763 | 0.661 | 0 % | **FAIL**: lower 0.530 ≤ 0.55 | — |
| `magnitude_chi2` | − | 0.601 [0.528, 0.679] | 0.082 [0.016, 0.190] | 0.760 | 0.668 | 0 % | **FAIL**: lower 0.528 ≤ 0.55 | — |
| `flagged_detection_count` | − | 0.817 [0.755, 0.862] | 0.331 [0.166, 0.497] | 0.834 | 0.722 [0.676, 0.773] | 0 % | PASS | **frozen** |
| `masked_detection_count` | − | 0.780 [0.721, 0.826] | 0.276 [0.149, 0.416] | 0.792 | 0.697 [0.650, 0.745] | 0 % | PASS | **frozen** |
| `edge_detection_count` | − | 0.546 [0.513, 0.604] | 0.000 [0.000, 0.000] | 0.555 | 0.529 | 0 % | **FAIL**: lower 0.513 ≤ 0.55 | — |
| `sharp_abs_max` | − | 0.930 [0.898, 0.952] | 0.709 [0.627, 0.773] | 0.861 [0.811, 0.904] | 0.924 [0.864, 0.961] | 0 % | PASS | **frozen** |
| `shared_detection_tracklets` | − | 0.805 [0.746, 0.851] | 0.192 [0.053, 0.372] | 0.809 [0.741, 0.865] | 0.722 [0.647, 0.802] | 0 % | PASS | **frozen** |

**No feature is reversed**: every overall AUC is above 0.5 in its
pre-registered direction. No feature fails on missingness. The SNR and
fit features never miss. `magnitude_range_sigma` and `magnitude_chi2`
have a positive error on every detection, and `sharp` is complete for
every development tracklet (as in AS-031).

**Redundancy** (|Spearman| > 0.90 on pooled development background, D4):

- Only one pair of passing features is redundant: `fit_rms` and
  `fit_max`, with ρ = 0.9995.
- With three detections and a two-parameter linear fit per axis, the
  residual vector has one shape per epoch spacing. So rms and max are
  nearly monotone in each other, and their AUCs are equal to 15 digits.
- The pre-committed tie rule drops the later one in CANDIDATE_FEATURES
  order, `fit_max_residual_arcsec`.
- `magnitude_range_mag` has ρ 0.93 with `_sigma` and `_chi2`, but both of
  those failed the gate, so nothing is dropped.

**Frozen for AS-039 (8):**

- `min_snr` (+)
- `median_snr` (+)
- `fit_rms_residual_arcsec` (−)
- `magnitude_range_mag` (−)
- `flagged_detection_count` (−)
- `masked_detection_count` (−)
- `sharp_abs_max` (−)
- `shared_detection_tracklets` (−)

Each enters only as its within-quadrant-night percentile.

## Observations, counterexamples and unexpected behaviour

These are reported and not acted on. They do not change the gate outcome.

O1. **Faint objects are ranked much worse by the strongest features.** The
stage-1 gate only asks for MARGINAL AUC ≥ 0.5, and every frozen feature
meets it. But on recall@5 % the faint gap is far larger than the AS-037
0.20 guard margin for four of them:

| feature | recall@5 % MARGINAL − PRIMARY |
|---|---|
| `min_snr` | 0.15 − 0.72 = −0.57 |
| `median_snr` | 0.19 − 0.71 = −0.52 |
| `sharp_abs_max` | 0.44 − 0.87 = −0.42 |
| `fit_rms_residual_arcsec` | 0.30 − 0.66 = −0.35 |

`magnitude_range_mag`, `flagged`, `masked` and `shared` are roughly
neutral (−0.01 to +0.08).

- Of the 58 positives that `min_snr` puts in the bottom half of their
  background, 54 are MARGINAL with a depth margin < 0.5 mag.
- The `min_snr` MARGINAL AUC lower bound is 0.539. The point (0.635)
  passes, but the interval reaches near chance.
- This is the AS-031/AS-037 brightness confound, now quantified.

Consequence for AS-039: the faint guard (MARGINAL recall ≥ PRIMARY − 0.20)
will be hard to pass for any mix dominated by the SNR, sharp or fit
features. AS-039 must apply its pre-registered guard. Nothing is changed
here.

O2. **Mask features demote real objects near bright stars, which is the
implicit proximity rejection AS-037 §8 warned about.**

- For `flagged` and `masked`, the zone+outer AUC (0.72 / 0.70) passes the
  ≥ 0.5 gate. But the zone-only AUC is 0.44 / 0.36. That stratum has only
  6 objects, so it is descriptive only, and 5 of the 6 rank in the bottom
  half.
- The 16 positives whose positive tracklet is masked on every detection
  have AUC 0.35 (`flagged`) and 0.25 (`masked`). All 16 sit in the bottom
  half of their background:
  - zone: 61384 (C12), 72582 (N6), 149159 (C4), 190831 (N3), 183143 (C7);
  - outer: 700974 (N4), 15523 (N14), 15019 (N11);
  - intermediate: 7 objects;
  - control: 1 object.
- recall@5 %: zone+outer 0.11 / 0.09 vs intermediate+control 0.36 /
  0.30. That is a −0.25 / −0.21 near-star gap, beyond the 0.20 margin.

The gate is applied as pre-registered, and both features are frozen. But
these two are the features the AS-039 / AS-040 near-star guard exists to
catch. Proximity was not used to remove them.

O3. **`magnitude_range_sigma` and `magnitude_chi2` fail.**

- They are near-duplicates of each other (ρ 0.99).
- Their AUC is 0.60, and their AUC is below 0.5 in 9 (`_sigma`) and 10
  (`_chi2`) of the 42 quadrant-nights with ≥ 3 positives.
- Their AUC is 0.38 / 0.39 for objects with a depth margin ≥ 1.5 mag:
  bright objects have small errors, so real variation becomes many σ
  (AS-031 H3).
- They do help faint objects (MARGINAL AUC 0.76). So the pre-registered
  chi² does not rescue the σ-scaled range.
- `magnitude_range_mag`, the unscaled range in magnitudes, passes.

O4. **`edge_detection_count` fails** (AUC 0.546 [0.513, 0.604], recall@5 %
0). Almost every tracklet has 0 edge detections, so positives tie with
most of the background and get q ≈ 0.5.

O5. **Per-quadrant-night counterexamples among the frozen features**
(quadrant-nights with ≥ 3 positives and AUC < 0.5):

- `min_snr`: S4-q2, 0.41 (n 3);
- `median_snr`: S4-q2, 0.31;
- `shared_detection_tracklets`: D-q2, 0.49 (n 5).

The other frozen features have none.

O6. **`sharp_abs_max` is the strongest single feature** (AUC 0.93, recall@5 %
0.71, 14× enrichment). It is research-path only: `sharp` is not in the
API's `SourceDetection`. A ranker that uses it cannot run in the
production path without a mapping change. This is a deployment
limitation, not a gate criterion.

O7. **`fit_rms` has a residual leak.** Positives must be identified, and
identification needs every residual to the SkyBoT prediction to be ≤ 2″.
This is far above typical fit RMS (AS-037 §9), but part of the AUC of
0.90 may restate selection. This is documented and not corrected.

O8. **The two redundancy measures differ for one pair.** `flagged` and
`masked` have a pooled ρ of 0.887, below the 0.90 rule, so both are kept.
Their per-quadrant-night median ρ is 0.99 (descriptive). Under D4, the
pooled value decides. AS-039 will see two highly collinear inputs.

O9. **Sensitivity is negligible.**

- Removing background that shares a detection with a positive changes
  any AUC by ≤ 0.001 and any recall@5 % by ≤ 0.003.
- Removing 105890 changes nothing at 3 decimals.

O10. **Single features reach about 0.5 recall@5 % already** on
development, in-sample for a single fixed-direction feature:

- `sharp_abs_max` 0.71;
- `fit_rms` 0.53;
- `min_snr` / `median_snr` 0.51 / 0.52.

This is not a ranker result and says nothing about validation.

## Deviations from the AS-037 handoff text

- Handoff item 1 asks for `TrackletQualityFeatures` "with raw sharp".
  The committed table stores the derived `sharp_abs_max` and
  `sharp_availability` (complete for all 18 366 rows), plus
  `mask_bits_union`. It does not store the three per-detection `sharp`
  values or `sharp_min` / `sharp_max`. No pre-registered metric uses them,
  and the runner can regenerate them from the same archival catalogs.
  No outcome depends on this.
- After the outcome, the only code change was a markdown column separator
  in the missingness table of the generated report. The JSON is identical
  apart from `generated_at`.

## Limitations

- Development only. The R quadrant-nights were inspected in AS-031–034, so
  these numbers are optimistic for R-like fields and are not evidence for
  validation.
- Only 6 zone positives. The near-star gate uses zone + outer (54)
  according to AS-037. Zone-only statements are descriptive.
- Positives are main-belt dominated, rate ≤ 1″/min and baseline ≥ 3″.
  Nothing here speaks to NEOs or slow movers.
- Background is a mixture. A feature that ranks real unknown objects low
  would look "good" here as long as it ranks known objects high.

## Handoff to AS-039 (not started)

- Use exactly the 8 frozen features (`as038_frozen_features.json`) as
  within-quadrant-night percentiles in their frozen directions.
- Use the AS-037 ranker family B0 / B1 / M1 / M2, grouped 5-fold CV on
  development, and the selection rule with the 0.20 near-star (zone +
  outer) and MARGINAL guards.
- O1 and O2 make it likely that some candidates fail those guards. That is
  the guard's job, not a reason to change the list.
- Proximity, speed, PA and identification columns of the table are not
  inputs.
- The validation split stays sealed until AS-039 commits a frozen ranker.
