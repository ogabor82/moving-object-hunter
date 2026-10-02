# AS-038 candidate feature evaluation (stage 1, development only; generated)

Generated 2026-10-02 18:00 UTC. Interpretation: `as038_findings.md`. No ranker, combined score, weight, threshold or filter; validation split not loaded.

Manifest SHA-256 `63e12b9feb8bc376…`; table SHA-256 `da670e38357503fe…`. 56 development quadrant-nights, 18366 ranked (built) tracklets: {'background': 17924, 'auxiliary': 40, 'positive': 402}. Positive object-nights 402 in 49 quadrant-nights.

## Gate summary

AUC = within-field AUC (mean 1 − q), weighted by object-night; [95 % group bootstrap]. Gate: AUC lower > 0.55, MARGINAL AUC ≥ 0.5, zone+outer AUC ≥ 0.5, missing ≤ 5 %; redundancy |Spearman| > 0.90 on development background (pooled).

| feature | dir | AUC [95 %] | recall@5 % [95 %] | MARGINAL AUC | zone+outer AUC | missing | gate | frozen | reason |
|---|---|---|---|---|---|---|---|---|---|
| `min_snr` | + | 0.827 [0.791, 0.873] | 0.512 [0.434, 0.617] | 0.635 | 0.892 | 0.00 % | PASS | yes | all conditions hold |
| `median_snr` | + | 0.820 [0.778, 0.874] | 0.517 [0.427, 0.642] | 0.614 | 0.865 | 0.00 % | PASS | yes | all conditions hold |
| `fit_rms_residual_arcsec` | − | 0.897 [0.872, 0.918] | 0.525 [0.430, 0.613] | 0.824 | 0.855 | 0.00 % | PASS | yes | all conditions hold |
| `fit_max_residual_arcsec` | − | 0.897 [0.873, 0.918] | 0.525 [0.426, 0.617] | 0.824 | 0.855 | 0.00 % | PASS | no | redundant with fit_rms_residual_arcsec |
| `magnitude_range_mag` | − | 0.800 [0.752, 0.854] | 0.209 [0.084, 0.383] | 0.808 | 0.818 | 0.00 % | PASS | yes | all conditions hold |
| `magnitude_range_sigma` | − | 0.602 [0.530, 0.676] | 0.087 [0.020, 0.198] | 0.763 | 0.661 | 0.00 % | FAIL | no | AUC lower bound 0.530 <= 0.55 |
| `magnitude_chi2` | − | 0.601 [0.528, 0.679] | 0.082 [0.016, 0.190] | 0.760 | 0.668 | 0.00 % | FAIL | no | AUC lower bound 0.528 <= 0.55 |
| `flagged_detection_count` | − | 0.817 [0.755, 0.862] | 0.331 [0.166, 0.497] | 0.834 | 0.722 | 0.00 % | PASS | yes | all conditions hold |
| `masked_detection_count` | − | 0.780 [0.721, 0.826] | 0.276 [0.149, 0.416] | 0.792 | 0.697 | 0.00 % | PASS | yes | all conditions hold |
| `edge_detection_count` | − | 0.546 [0.513, 0.604] | 0.000 [0.000, 0.000] | 0.555 | 0.529 | 0.00 % | FAIL | no | AUC lower bound 0.513 <= 0.55 |
| `sharp_abs_max` | − | 0.930 [0.898, 0.952] | 0.709 [0.627, 0.773] | 0.861 | 0.924 | 0.00 % | PASS | yes | all conditions hold |
| `shared_detection_tracklets` | − | 0.805 [0.746, 0.851] | 0.192 [0.053, 0.372] | 0.809 | 0.722 | 0.00 % | PASS | yes | all conditions hold |

**Frozen for AS-039:** `min_snr`, `median_snr`, `fit_rms_residual_arcsec`, `magnitude_range_mag`, `flagged_detection_count`, `masked_detection_count`, `sharp_abs_max`, `shared_detection_tracklets`

## Secondary metrics

| feature | recall@1/2/5/10/20 % | recall@K 10/25/50 | enrichment@5 % | median q |
|---|---|---|---|---|
| `min_snr` | 0.45 / 0.47 / 0.51 / 0.60 / 0.71 | 0.61 / 0.71 / 0.81 | 10.2 | 0.041 |
| `median_snr` | 0.42 / 0.44 / 0.52 / 0.60 / 0.72 | 0.58 / 0.71 / 0.80 | 10.3 | 0.038 |
| `fit_rms_residual_arcsec` | 0.27 / 0.33 / 0.52 / 0.67 / 0.84 | 0.58 / 0.74 / 0.82 | 10.5 | 0.047 |
| `fit_max_residual_arcsec` | 0.27 / 0.33 / 0.52 / 0.67 / 0.84 | 0.58 / 0.74 / 0.82 | 10.5 | 0.047 |
| `magnitude_range_mag` | 0.10 / 0.16 / 0.21 / 0.31 / 0.54 | 0.34 / 0.62 / 0.79 | 4.2 | 0.185 |
| `magnitude_range_sigma` | 0.02 / 0.05 / 0.09 / 0.16 / 0.29 | 0.15 / 0.40 / 0.63 | 1.7 | 0.377 |
| `magnitude_chi2` | 0.02 / 0.05 / 0.08 / 0.16 / 0.29 | 0.14 / 0.39 / 0.63 | 1.6 | 0.370 |
| `flagged_detection_count` | 0.08 / 0.15 / 0.33 / 0.39 / 0.64 | 0.40 / 0.76 / 0.84 | 6.6 | 0.130 |
| `masked_detection_count` | 0.04 / 0.10 / 0.28 / 0.32 / 0.55 | 0.40 / 0.70 / 0.77 | 5.5 | 0.176 |
| `edge_detection_count` | 0.00 / 0.00 / 0.00 / 0.06 / 0.06 | 0.07 / 0.29 / 0.47 | 0.0 | 0.499 |
| `sharp_abs_max` | 0.47 / 0.53 / 0.71 / 0.80 / 0.90 | 0.71 / 0.84 / 0.91 | 14.2 | 0.015 |
| `shared_detection_tracklets` | 0.00 / 0.09 / 0.19 / 0.30 / 0.63 | 0.18 / 0.70 / 0.84 | 3.8 | 0.155 |

## Strata (point AUC / recall@5 %, object-nights)

| feature | role=marginal (n 149) | role=primary (n 253) | near_star=intermediate+control (n 348) | near_star=zone+outer (n 54) | proximity_group=control (n 223) | proximity_group=intermediate (n 125) | proximity_group=outer (n 48) | proximity_group=zone (n 6) | depth_margin=0.5-1.5 (n 144) | depth_margin=<0.5 (n 149) | depth_margin=>=1.5 (n 109) | crowding=20-80k (n 36) | crowding=<20k (n 330) | crowding=>=80k (n 36) | filters=mixed (n 297) | filters=single (n 105) | speed=0.25-0.5 (n 120) | speed=0.5-1.0 (n 246) | speed=<0.25 (n 36) | mask_state=all (n 16) | mask_state=partial (n 6) | mask_state=unmasked (n 380) | population=C (n 45) | population=N (n 226) | population=R (n 131) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `min_snr` | 0.64 / 0.15 | 0.94 / 0.72 | 0.82 / 0.51 | 0.89 / 0.56 | 0.81 / 0.48 | 0.82 / 0.54 | 0.89 / 0.56 | 0.93 / 0.50 | 0.89 / 0.51 | 0.64 / 0.15 | 1.00 / 1.00 | 0.93 / 0.64 | 0.80 / 0.48 | 0.95 / 0.67 | 0.79 / 0.46 | 0.92 / 0.66 | 0.82 / 0.52 | 0.84 / 0.52 | 0.78 / 0.47 | 0.89 / 0.56 | 0.91 / 0.67 | 0.82 / 0.51 | 0.87 / 0.64 | 0.84 / 0.54 | 0.78 / 0.43 |
| `median_snr` | 0.61 / 0.19 | 0.94 / 0.71 | 0.81 / 0.53 | 0.87 / 0.44 | 0.81 / 0.52 | 0.82 / 0.54 | 0.87 / 0.44 | 0.85 / 0.50 | 0.89 / 0.51 | 0.63 / 0.19 | 0.99 / 0.97 | 0.89 / 0.56 | 0.80 / 0.50 | 0.95 / 0.64 | 0.79 / 0.48 | 0.90 / 0.63 | 0.83 / 0.56 | 0.82 / 0.50 | 0.79 / 0.50 | 0.85 / 0.56 | 0.88 / 0.83 | 0.82 / 0.51 | 0.85 / 0.64 | 0.84 / 0.52 | 0.78 / 0.47 |
| `fit_rms_residual_arcsec` | 0.82 / 0.30 | 0.94 / 0.66 | 0.90 / 0.54 | 0.86 / 0.44 | 0.90 / 0.54 | 0.91 / 0.54 | 0.85 / 0.42 | 0.92 / 0.67 | 0.91 / 0.54 | 0.83 / 0.32 | 0.97 / 0.79 | 0.91 / 0.56 | 0.89 / 0.52 | 0.93 / 0.56 | 0.89 / 0.54 | 0.91 / 0.49 | 0.89 / 0.53 | 0.90 / 0.52 | 0.89 / 0.58 | 0.92 / 0.50 | 0.91 / 0.50 | 0.90 / 0.53 | 0.90 / 0.49 | 0.89 / 0.50 | 0.90 / 0.59 |
| `fit_max_residual_arcsec` | 0.82 / 0.30 | 0.94 / 0.66 | 0.90 / 0.54 | 0.86 / 0.44 | 0.90 / 0.54 | 0.91 / 0.54 | 0.85 / 0.42 | 0.92 / 0.67 | 0.91 / 0.54 | 0.83 / 0.32 | 0.97 / 0.79 | 0.91 / 0.56 | 0.89 / 0.52 | 0.93 / 0.56 | 0.89 / 0.54 | 0.91 / 0.49 | 0.89 / 0.53 | 0.90 / 0.52 | 0.89 / 0.58 | 0.92 / 0.50 | 0.91 / 0.50 | 0.90 / 0.53 | 0.90 / 0.49 | 0.89 / 0.50 | 0.90 / 0.59 |
| `magnitude_range_mag` | 0.81 / 0.21 | 0.80 / 0.21 | 0.80 / 0.20 | 0.82 / 0.30 | 0.78 / 0.15 | 0.83 / 0.27 | 0.81 / 0.29 | 0.85 / 0.33 | 0.80 / 0.22 | 0.80 / 0.23 | 0.80 / 0.17 | 0.89 / 0.50 | 0.79 / 0.18 | 0.84 / 0.22 | 0.77 / 0.11 | 0.89 / 0.48 | 0.83 / 0.26 | 0.78 / 0.17 | 0.82 / 0.31 | 0.82 / 0.38 | 0.98 / 1.00 | 0.80 / 0.19 | 0.89 / 0.49 | 0.78 / 0.21 | 0.80 / 0.11 |
| `magnitude_range_sigma` | 0.76 / 0.15 | 0.51 / 0.05 | 0.59 / 0.09 | 0.66 / 0.07 | 0.56 / 0.06 | 0.65 / 0.14 | 0.65 / 0.04 | 0.76 / 0.33 | 0.61 / 0.07 | 0.76 / 0.15 | 0.38 / 0.03 | 0.76 / 0.17 | 0.59 / 0.09 | 0.56 / 0.00 | 0.56 / 0.03 | 0.73 / 0.25 | 0.64 / 0.11 | 0.58 / 0.07 | 0.63 / 0.11 | 0.69 / 0.25 | 0.86 / 0.50 | 0.59 / 0.07 | 0.78 / 0.38 | 0.59 / 0.06 | 0.56 / 0.04 |
| `magnitude_chi2` | 0.76 / 0.15 | 0.51 / 0.04 | 0.59 / 0.08 | 0.67 / 0.07 | 0.55 / 0.06 | 0.66 / 0.12 | 0.66 / 0.04 | 0.76 / 0.33 | 0.61 / 0.07 | 0.75 / 0.13 | 0.39 / 0.03 | 0.76 / 0.19 | 0.59 / 0.08 | 0.57 / 0.00 | 0.55 / 0.02 | 0.74 / 0.25 | 0.63 / 0.11 | 0.58 / 0.07 | 0.64 / 0.11 | 0.70 / 0.19 | 0.86 / 0.50 | 0.59 / 0.07 | 0.79 / 0.36 | 0.59 / 0.06 | 0.56 / 0.03 |
| `flagged_detection_count` | 0.83 / 0.38 | 0.81 / 0.30 | 0.83 / 0.36 | 0.72 / 0.11 | 0.84 / 0.36 | 0.82 / 0.37 | 0.76 / 0.12 | 0.44 / 0.00 | 0.84 / 0.32 | 0.83 / 0.40 | 0.77 / 0.26 | 0.76 / 0.00 | 0.85 / 0.40 | 0.58 / 0.00 | 0.83 / 0.33 | 0.77 / 0.33 | 0.81 / 0.36 | 0.83 / 0.34 | 0.78 / 0.17 | 0.35 / 0.00 | 0.83 / 0.50 | 0.84 / 0.34 | 0.87 / 0.71 | 0.84 / 0.39 | 0.76 / 0.09 |
| `masked_detection_count` | 0.79 / 0.31 | 0.77 / 0.26 | 0.79 / 0.30 | 0.70 / 0.09 | 0.81 / 0.30 | 0.77 / 0.30 | 0.74 / 0.10 | 0.36 / 0.00 | 0.80 / 0.26 | 0.79 / 0.32 | 0.75 / 0.23 | 0.73 / 0.00 | 0.81 / 0.34 | 0.56 / 0.00 | 0.82 / 0.33 | 0.66 / 0.12 | 0.76 / 0.26 | 0.80 / 0.30 | 0.75 / 0.17 | 0.25 / 0.00 | 0.41 / 0.00 | 0.81 / 0.29 | 0.65 / 0.22 | 0.82 / 0.39 | 0.75 / 0.09 |
| `edge_detection_count` | 0.56 / 0.00 | 0.54 / 0.00 | 0.55 / 0.00 | 0.53 / 0.00 | 0.54 / 0.00 | 0.56 / 0.00 | 0.52 / 0.00 | 0.58 / 0.00 | 0.55 / 0.00 | 0.56 / 0.00 | 0.53 / 0.00 | 0.54 / 0.00 | 0.55 / 0.00 | 0.52 / 0.00 | 0.52 / 0.00 | 0.63 / 0.00 | 0.58 / 0.00 | 0.53 / 0.00 | 0.53 / 0.00 | 0.61 / 0.00 | 0.73 / 0.00 | 0.54 / 0.00 | 0.75 / 0.00 | 0.53 / 0.00 | 0.50 / 0.00 |
| `sharp_abs_max` | 0.86 / 0.44 | 0.97 / 0.87 | 0.93 / 0.72 | 0.92 / 0.67 | 0.94 / 0.74 | 0.92 / 0.66 | 0.92 / 0.67 | 0.92 / 0.67 | 0.96 / 0.81 | 0.87 / 0.46 | 0.98 / 0.91 | 0.92 / 0.64 | 0.94 / 0.73 | 0.88 / 0.58 | 0.93 / 0.71 | 0.93 / 0.71 | 0.91 / 0.69 | 0.95 / 0.76 | 0.86 / 0.44 | 0.95 / 0.69 | 0.98 / 1.00 | 0.93 / 0.71 | 0.97 / 0.87 | 0.94 / 0.73 | 0.90 / 0.62 |
| `shared_detection_tracklets` | 0.81 / 0.25 | 0.80 / 0.16 | 0.82 / 0.21 | 0.72 / 0.07 | 0.81 / 0.20 | 0.83 / 0.22 | 0.72 / 0.06 | 0.77 / 0.17 | 0.82 / 0.17 | 0.81 / 0.23 | 0.78 / 0.17 | 0.74 / 0.00 | 0.84 / 0.23 | 0.57 / 0.00 | 0.82 / 0.18 | 0.76 / 0.24 | 0.80 / 0.30 | 0.80 / 0.15 | 0.80 / 0.14 | 0.84 / 0.31 | 0.92 / 0.50 | 0.80 / 0.18 | 0.89 / 0.56 | 0.83 / 0.18 | 0.74 / 0.09 |

Gate strata with intervals:

| feature | MARGINAL AUC [95 %] | zone+outer AUC [95 %] |
|---|---|---|
| `min_snr` | 0.635 [0.539, 0.731] | 0.892 [0.829, 0.945] |
| `median_snr` | 0.614 [0.498, 0.720] | 0.865 [0.787, 0.932] |
| `fit_rms_residual_arcsec` | 0.824 [0.788, 0.859] | 0.855 [0.819, 0.896] |
| `fit_max_residual_arcsec` | 0.824 [0.790, 0.861] | 0.855 [0.816, 0.897] |
| `magnitude_range_mag` | 0.808 [0.752, 0.865] | 0.818 [0.772, 0.872] |
| `magnitude_range_sigma` | 0.763 [0.699, 0.823] | 0.661 [0.558, 0.750] |
| `magnitude_chi2` | 0.760 [0.693, 0.823] | 0.668 [0.568, 0.755] |
| `flagged_detection_count` | 0.834 [0.773, 0.882] | 0.722 [0.676, 0.773] |
| `masked_detection_count` | 0.792 [0.735, 0.845] | 0.697 [0.650, 0.745] |
| `edge_detection_count` | 0.555 [0.509, 0.621] | 0.529 [0.506, 0.566] |
| `sharp_abs_max` | 0.861 [0.811, 0.904] | 0.924 [0.864, 0.961] |
| `shared_detection_tracklets` | 0.809 [0.741, 0.865] | 0.722 [0.647, 0.802] |

## Missingness (share of ranked tracklets)

| feature | all | positive | auxiliary | background |
|---|---|---|---|---|
| `min_snr` | 0/18366 (0.00 %) | 0.00 % | 0.00 % | 0.00 % |
| `median_snr` | 0/18366 (0.00 %) | 0.00 % | 0.00 % | 0.00 % |
| `fit_rms_residual_arcsec` | 0/18366 (0.00 %) | 0.00 % | 0.00 % | 0.00 % |
| `fit_max_residual_arcsec` | 0/18366 (0.00 %) | 0.00 % | 0.00 % | 0.00 % |
| `magnitude_range_mag` | 0/18366 (0.00 %) | 0.00 % | 0.00 % | 0.00 % |
| `magnitude_range_sigma` | 0/18366 (0.00 %) | 0.00 % | 0.00 % | 0.00 % |
| `magnitude_chi2` | 0/18366 (0.00 %) | 0.00 % | 0.00 % | 0.00 % |
| `flagged_detection_count` | 0/18366 (0.00 %) | 0.00 % | 0.00 % | 0.00 % |
| `masked_detection_count` | 0/18366 (0.00 %) | 0.00 % | 0.00 % | 0.00 % |
| `edge_detection_count` | 0/18366 (0.00 %) | 0.00 % | 0.00 % | 0.00 % |
| `sharp_abs_max` | 0/18366 (0.00 %) | 0.00 % | 0.00 % | 0.00 % |
| `shared_detection_tracklets` | 0/18366 (0.00 %) | 0.00 % | 0.00 % | 0.00 % |

## Spearman on development background, pooled (deciding)

| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 `min_snr` | 1.00 | 0.78 | -0.01 | -0.01 | 0.04 | 0.35 | 0.32 | 0.56 | 0.49 | 0.11 | -0.17 | 0.58 |
| 2 `median_snr` | 0.78 | 1.00 | 0.00 | -0.00 | 0.22 | 0.49 | 0.48 | 0.58 | 0.55 | 0.04 | -0.18 | 0.59 |
| 3 `fit_rms_residual_arcsec` | -0.01 | 0.00 | 1.00 | 1.00 | 0.04 | 0.03 | 0.03 | -0.00 | 0.01 | -0.03 | 0.01 | -0.01 |
| 4 `fit_max_residual_arcsec` | -0.01 | -0.00 | 1.00 | 1.00 | 0.03 | 0.03 | 0.03 | -0.01 | 0.01 | -0.03 | 0.00 | -0.01 |
| 5 `magnitude_range_mag` | 0.04 | 0.22 | 0.04 | 0.03 | 1.00 | 0.93 | 0.93 | 0.24 | 0.32 | -0.14 | 0.12 | 0.19 |
| 6 `magnitude_range_sigma` | 0.35 | 0.49 | 0.03 | 0.03 | 0.93 | 1.00 | 0.99 | 0.41 | 0.47 | -0.11 | 0.06 | 0.38 |
| 7 `magnitude_chi2` | 0.32 | 0.48 | 0.03 | 0.03 | 0.93 | 0.99 | 1.00 | 0.39 | 0.45 | -0.11 | 0.05 | 0.36 |
| 8 `flagged_detection_count` | 0.56 | 0.58 | -0.00 | -0.01 | 0.24 | 0.41 | 0.39 | 1.00 | 0.89 | 0.18 | 0.00 | 0.77 |
| 9 `masked_detection_count` | 0.49 | 0.55 | 0.01 | 0.01 | 0.32 | 0.47 | 0.45 | 0.89 | 1.00 | -0.27 | -0.01 | 0.68 |
| 10 `edge_detection_count` | 0.11 | 0.04 | -0.03 | -0.03 | -0.14 | -0.11 | -0.11 | 0.18 | -0.27 | 1.00 | 0.02 | 0.12 |
| 11 `sharp_abs_max` | -0.17 | -0.18 | 0.01 | 0.00 | 0.12 | 0.06 | 0.05 | 0.00 | -0.01 | 0.02 | 1.00 | -0.11 |
| 12 `shared_detection_tracklets` | 0.58 | 0.59 | -0.01 | -0.01 | 0.19 | 0.38 | 0.36 | 0.77 | 0.68 | 0.12 | -0.11 | 1.00 |

## Spearman on development background, median over quadrant-nights (descriptive)

| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 `min_snr` | 1.00 | 0.69 | -0.01 | -0.01 | -0.11 | 0.21 | 0.16 | 0.35 | 0.34 | 0.02 | 0.12 | 0.25 |
| 2 `median_snr` | 0.69 | 1.00 | 0.00 | 0.00 | 0.15 | 0.36 | 0.38 | 0.39 | 0.39 | 0.05 | 0.14 | 0.23 |
| 3 `fit_rms_residual_arcsec` | -0.01 | 0.00 | 1.00 | 1.00 | 0.04 | 0.04 | 0.05 | 0.00 | 0.01 | -0.01 | 0.02 | 0.01 |
| 4 `fit_max_residual_arcsec` | -0.01 | 0.00 | 1.00 | 1.00 | 0.04 | 0.04 | 0.05 | 0.00 | 0.01 | -0.01 | 0.02 | 0.01 |
| 5 `magnitude_range_mag` | -0.11 | 0.15 | 0.04 | 0.04 | 1.00 | 0.93 | 0.94 | 0.12 | 0.10 | 0.04 | 0.10 | 0.02 |
| 6 `magnitude_range_sigma` | 0.21 | 0.36 | 0.04 | 0.04 | 0.93 | 1.00 | 0.99 | 0.18 | 0.22 | 0.01 | 0.13 | 0.13 |
| 7 `magnitude_chi2` | 0.16 | 0.38 | 0.05 | 0.05 | 0.94 | 0.99 | 1.00 | 0.17 | 0.21 | 0.01 | 0.12 | 0.10 |
| 8 `flagged_detection_count` | 0.35 | 0.39 | 0.00 | 0.00 | 0.12 | 0.18 | 0.17 | 1.00 | 0.99 | 0.25 | 0.15 | 0.32 |
| 9 `masked_detection_count` | 0.34 | 0.39 | 0.01 | 0.01 | 0.10 | 0.22 | 0.21 | 0.99 | 1.00 | -0.16 | 0.20 | 0.33 |
| 10 `edge_detection_count` | 0.02 | 0.05 | -0.01 | -0.01 | 0.04 | 0.01 | 0.01 | 0.25 | -0.16 | 1.00 | -0.08 | -0.04 |
| 11 `sharp_abs_max` | 0.12 | 0.14 | 0.02 | 0.02 | 0.10 | 0.13 | 0.12 | 0.15 | 0.20 | -0.08 | 1.00 | 0.08 |
| 12 `shared_detection_tracklets` | 0.25 | 0.23 | 0.01 | 0.01 | 0.02 | 0.13 | 0.10 | 0.32 | 0.33 | -0.04 | 0.08 | 1.00 |

## Sensitivity (descriptive)

| feature | analysis | value |
|---|---|---|
| `min_snr` | without background sharing a detection with a positive (AUC) | 0.826 |
| `min_snr` | without background sharing a detection with a positive (recall@5%) | 0.512 |
| `min_snr` | without 105890 (AUC) | 0.827 |
| `min_snr` | without 105890 (recall@5%) | 0.512 |
| `median_snr` | without background sharing a detection with a positive (AUC) | 0.820 |
| `median_snr` | without background sharing a detection with a positive (recall@5%) | 0.520 |
| `median_snr` | without 105890 (AUC) | 0.820 |
| `median_snr` | without 105890 (recall@5%) | 0.517 |
| `fit_rms_residual_arcsec` | without background sharing a detection with a positive (AUC) | 0.897 |
| `fit_rms_residual_arcsec` | without background sharing a detection with a positive (recall@5%) | 0.525 |
| `fit_rms_residual_arcsec` | without 105890 (AUC) | 0.897 |
| `fit_rms_residual_arcsec` | without 105890 (recall@5%) | 0.525 |
| `fit_max_residual_arcsec` | without background sharing a detection with a positive (AUC) | 0.897 |
| `fit_max_residual_arcsec` | without background sharing a detection with a positive (recall@5%) | 0.525 |
| `fit_max_residual_arcsec` | without 105890 (AUC) | 0.897 |
| `fit_max_residual_arcsec` | without 105890 (recall@5%) | 0.525 |
| `magnitude_range_mag` | without background sharing a detection with a positive (AUC) | 0.800 |
| `magnitude_range_mag` | without background sharing a detection with a positive (recall@5%) | 0.209 |
| `magnitude_range_mag` | without 105890 (AUC) | 0.800 |
| `magnitude_range_mag` | without 105890 (recall@5%) | 0.209 |
| `magnitude_range_sigma` | without background sharing a detection with a positive (AUC) | 0.602 |
| `magnitude_range_sigma` | without background sharing a detection with a positive (recall@5%) | 0.087 |
| `magnitude_range_sigma` | without 105890 (AUC) | 0.602 |
| `magnitude_range_sigma` | without 105890 (recall@5%) | 0.087 |
| `magnitude_chi2` | without background sharing a detection with a positive (AUC) | 0.601 |
| `magnitude_chi2` | without background sharing a detection with a positive (recall@5%) | 0.082 |
| `magnitude_chi2` | without 105890 (AUC) | 0.601 |
| `magnitude_chi2` | without 105890 (recall@5%) | 0.082 |
| `flagged_detection_count` | without background sharing a detection with a positive (AUC) | 0.817 |
| `flagged_detection_count` | without background sharing a detection with a positive (recall@5%) | 0.331 |
| `flagged_detection_count` | without 105890 (AUC) | 0.817 |
| `flagged_detection_count` | without 105890 (recall@5%) | 0.331 |
| `masked_detection_count` | without background sharing a detection with a positive (AUC) | 0.780 |
| `masked_detection_count` | without background sharing a detection with a positive (recall@5%) | 0.276 |
| `masked_detection_count` | without 105890 (AUC) | 0.780 |
| `masked_detection_count` | without 105890 (recall@5%) | 0.276 |
| `edge_detection_count` | without background sharing a detection with a positive (AUC) | 0.546 |
| `edge_detection_count` | without background sharing a detection with a positive (recall@5%) | 0.000 |
| `edge_detection_count` | without 105890 (AUC) | 0.546 |
| `edge_detection_count` | without 105890 (recall@5%) | 0.000 |
| `sharp_abs_max` | without background sharing a detection with a positive (AUC) | 0.930 |
| `sharp_abs_max` | without background sharing a detection with a positive (recall@5%) | 0.709 |
| `sharp_abs_max` | without 105890 (AUC) | 0.930 |
| `sharp_abs_max` | without 105890 (recall@5%) | 0.709 |
| `shared_detection_tracklets` | without background sharing a detection with a positive (AUC) | 0.804 |
| `shared_detection_tracklets` | without background sharing a detection with a positive (recall@5%) | 0.192 |
| `shared_detection_tracklets` | without 105890 (AUC) | 0.805 |
| `shared_detection_tracklets` | without 105890 (recall@5%) | 0.192 |

## Per quadrant-night AUC (positives ≥ 1)

| field | positives | background | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B-2019-01-25-565-c13-q3 | 8 | 88 | 0.63 | 0.65 | 0.90 | 0.90 | 0.74 | 0.66 | 0.67 | 0.93 | 0.93 | 0.50 | 0.95 | 0.86 |
| C-2018-10-06-448-c9-q3 | 8 | 26 | 0.97 | 0.95 | 0.99 | 0.99 | 0.84 | 0.32 | 0.33 | 0.62 | 0.60 | 0.52 | 0.94 | 0.58 |
| D-2019-06-02-281-c16-q3 | 9 | 833 | 0.95 | 0.95 | 0.91 | 0.91 | 0.83 | 0.55 | 0.56 | 0.59 | 0.59 | 0.52 | 0.90 | 0.65 |
| S1-2018-09-19-508-c10-q4 | 6 | 48 | 0.54 | 0.73 | 0.86 | 0.86 | 0.82 | 0.68 | 0.64 | 0.83 | 0.82 | 0.51 | 0.94 | 0.89 |
| S2-2018-09-27-509-c14-q4 | 1 | 110 | 0.46 | 0.70 | 0.98 | 0.98 | 0.59 | 0.60 | 0.55 | 0.98 | 0.98 | 0.50 | 0.88 | 0.94 |
| S4-2018-11-07-615-c5-q3 | 9 | 3483 | 0.67 | 0.59 | 0.84 | 0.84 | 0.70 | 0.51 | 0.51 | 0.94 | 0.94 | 0.50 | 0.69 | 0.99 |
| B-2019-01-25-565-c13-q1 | 10 | 18 | 0.89 | 0.84 | 0.86 | 0.86 | 0.82 | 0.56 | 0.55 | 0.72 | 0.72 | 0.50 | 0.97 | 0.72 |
| B-2019-01-25-565-c13-q2 | 11 | 65 | 0.72 | 0.62 | 0.91 | 0.91 | 0.79 | 0.68 | 0.68 | 0.76 | 0.76 | 0.50 | 0.94 | 0.82 |
| B-2019-01-25-565-c13-q4 | 18 | 74 | 0.67 | 0.63 | 0.89 | 0.89 | 0.81 | 0.64 | 0.64 | 0.89 | 0.89 | 0.50 | 0.97 | 0.84 |
| D-2019-06-02-281-c16-q1 | 5 | 960 | 1.00 | 0.96 | 0.98 | 0.98 | 0.79 | 0.44 | 0.44 | 0.51 | 0.50 | 0.51 | 0.93 | 0.51 |
| D-2019-06-02-281-c16-q2 | 5 | 620 | 0.90 | 0.93 | 0.97 | 0.97 | 0.88 | 0.61 | 0.63 | 0.53 | 0.52 | 0.51 | 0.77 | 0.49 |
| D-2019-06-02-281-c16-q4 | 2 | 608 | 1.00 | 1.00 | 0.95 | 0.95 | 0.95 | 0.46 | 0.47 | 0.52 | 0.50 | 0.52 | 0.98 | 0.59 |
| S1-2018-09-19-508-c10-q1 | 10 | 26 | 0.94 | 0.96 | 0.98 | 0.98 | 0.87 | 0.46 | 0.42 | 0.67 | 0.67 | 0.50 | 0.92 | 0.65 |
| S1-2018-09-19-508-c10-q2 | 6 | 18 | 0.81 | 0.86 | 0.98 | 0.98 | 0.82 | 0.61 | 0.63 | 0.83 | 0.83 | 0.50 | 0.93 | 0.78 |
| S1-2018-09-19-508-c10-q3 | 4 | 21 | 0.81 | 1.00 | 1.00 | 1.00 | 0.89 | 0.62 | 0.62 | 0.74 | 0.71 | 0.52 | 0.87 | 0.76 |
| S2-2018-09-27-509-c14-q1 | 2 | 22 | 0.68 | 0.66 | 0.93 | 0.93 | 0.77 | 0.75 | 0.75 | 0.84 | 0.84 | 0.50 | 0.82 | 0.89 |
| S2-2018-09-27-509-c14-q2 | 4 | 3 | 0.58 | 0.58 | 0.75 | 0.75 | 0.67 | 0.50 | 0.50 | 0.67 | 0.67 | 0.50 | 0.50 | 0.50 |
| S2-2018-09-27-509-c14-q3 | 3 | 3 | 0.72 | 1.00 | 1.00 | 1.00 | 0.89 | 0.67 | 0.67 | 0.67 | 0.67 | 0.50 | 0.78 | 0.50 |
| S4-2018-11-07-615-c5-q1 | 3 | 15 | 0.96 | 0.98 | 0.87 | 0.87 | 0.60 | 0.07 | 0.09 | 0.60 | 0.60 | 0.50 | 0.98 | 0.57 |
| S4-2018-11-07-615-c5-q2 | 3 | 1118 | 0.41 | 0.31 | 0.54 | 0.54 | 0.79 | 0.88 | 0.89 | 0.98 | 0.98 | 0.50 | 0.90 | 0.98 |
| S4-2018-11-07-615-c5-q4 | 4 | 41 | 0.86 | 0.75 | 0.76 | 0.76 | 0.68 | 0.54 | 0.54 | 0.85 | 0.85 | 0.50 | 0.90 | 0.63 |
| N2-2019-11-05-564-c1-q2 | 5 | 251 | 0.96 | 0.91 | 0.95 | 0.95 | 0.96 | 0.93 | 0.94 | 0.92 | 0.88 | 0.56 | 0.92 | 0.87 |
| N3-2019-09-23-1441-c5-q4 | 16 | 463 | 0.79 | 0.86 | 0.74 | 0.74 | 0.98 | 0.89 | 0.90 | 0.93 | 0.92 | 0.50 | 0.97 | 0.92 |
| N4-2020-09-15-447-c3-q4 | 18 | 74 | 0.90 | 0.87 | 0.85 | 0.85 | 0.68 | 0.54 | 0.54 | 0.80 | 0.80 | 0.50 | 0.97 | 0.81 |
| N5-2019-08-27-335-c7-q4 | 3 | 96 | 0.94 | 0.91 | 0.97 | 0.97 | 0.82 | 0.58 | 0.59 | 0.84 | 0.69 | 0.66 | 0.90 | 0.71 |
| N6-2019-07-29-338-c6-q1 | 23 | 104 | 0.75 | 0.70 | 0.92 | 0.92 | 0.64 | 0.43 | 0.39 | 0.93 | 0.93 | 0.50 | 0.96 | 0.88 |
| N7-2019-12-29-611-c9-q3 | 16 | 43 | 0.83 | 0.84 | 0.84 | 0.84 | 0.70 | 0.36 | 0.38 | 0.70 | 0.72 | 0.47 | 0.92 | 0.66 |
| N8-2019-07-24-333-c8-q1 | 5 | 146 | 0.99 | 0.93 | 0.97 | 0.97 | 0.94 | 0.72 | 0.73 | 0.70 | 0.68 | 0.52 | 0.97 | 0.65 |
| N9-2019-08-31-334-c4-q3 | 1 | 280 | 1.00 | 1.00 | 0.93 | 0.93 | 0.62 | 0.12 | 0.14 | 0.56 | 0.54 | 0.53 | 0.98 | 0.67 |
| N10-2018-11-12-504-c2-q3 | 7 | 714 | 0.71 | 0.68 | 0.95 | 0.95 | 0.73 | 0.50 | 0.49 | 1.00 | 1.00 | 0.50 | 0.84 | 0.98 |
| N11-2018-10-31-559-c3-q1 | 6 | 61 | 0.78 | 0.74 | 0.88 | 0.88 | 0.76 | 0.63 | 0.64 | 0.83 | 0.83 | 0.50 | 0.89 | 0.79 |
| N12-2019-11-01-607-c1-q2 | 14 | 996 | 0.89 | 0.87 | 0.91 | 0.91 | 0.94 | 0.87 | 0.88 | 0.97 | 0.96 | 0.53 | 0.95 | 0.94 |
| N13-2018-08-21-394-c12-q4 | 19 | 1045 | 0.96 | 0.95 | 0.97 | 0.97 | 0.78 | 0.46 | 0.44 | 0.98 | 0.98 | 0.50 | 0.98 | 0.97 |
| N14-2018-11-02-562-c3-q3 | 5 | 146 | 0.96 | 0.96 | 0.80 | 0.80 | 0.99 | 0.82 | 0.83 | 0.80 | 0.79 | 0.51 | 0.91 | 0.85 |
| N15-2019-07-29-338-c13-q3 | 21 | 27 | 0.79 | 0.78 | 0.89 | 0.89 | 0.66 | 0.50 | 0.48 | 0.85 | 0.85 | 0.50 | 0.98 | 0.72 |
| N16-2019-12-29-568-c15-q4 | 15 | 541 | 0.71 | 0.76 | 0.93 | 0.93 | 0.75 | 0.62 | 0.64 | 0.95 | 0.94 | 0.67 | 0.91 | 0.96 |
| N17-2019-06-27-330-c9-q2 | 7 | 508 | 0.84 | 0.84 | 0.92 | 0.92 | 0.91 | 0.85 | 0.85 | 0.87 | 0.85 | 0.53 | 0.96 | 0.88 |
| N18-2018-07-16-333-c13-q2 | 1 | 318 | 1.00 | 1.00 | 0.95 | 0.95 | 0.88 | 0.51 | 0.55 | 0.53 | 0.52 | 0.51 | 0.93 | 0.56 |
| N19-2019-01-25-614-c2-q1 | 12 | 66 | 0.82 | 0.90 | 0.90 | 0.90 | 0.73 | 0.53 | 0.54 | 0.78 | 0.66 | 0.64 | 0.98 | 0.85 |
| N20-2018-09-27-499-c1-q2 | 3 | 11 | 0.88 | 0.76 | 0.73 | 0.73 | 1.00 | 0.91 | 0.91 | 0.82 | 0.82 | 0.50 | 0.94 | 0.68 |
| N21-2019-01-28-474-c8-q4 | 5 | 155 | 0.80 | 0.74 | 0.94 | 0.94 | 0.75 | 0.54 | 0.54 | 0.72 | 0.64 | 0.58 | 0.84 | 0.88 |
| N22-2018-09-06-553-c4-q4 | 9 | 144 | 0.92 | 0.92 | 0.91 | 0.91 | 0.80 | 0.35 | 0.33 | 0.60 | 0.53 | 0.57 | 0.97 | 0.84 |
| N23-2019-06-01-279-c6-q1 | 10 | 170 | 0.95 | 0.95 | 0.96 | 0.96 | 0.89 | 0.67 | 0.68 | 0.64 | 0.61 | 0.54 | 0.82 | 0.57 |
| N24-2019-08-21-335-c10-q3 | 5 | 50 | 0.87 | 0.78 | 0.80 | 0.80 | 0.78 | 0.64 | 0.65 | 0.57 | 0.55 | 0.53 | 0.95 | 0.58 |
| C4-2019-08-20-335-c11-q1 | 6 | 66 | 0.95 | 0.91 | 0.97 | 0.97 | 0.81 | 0.66 | 0.68 | 0.66 | 0.65 | 0.52 | 0.83 | 0.59 |
| C7-2019-01-25-565-c3-q2 | 11 | 177 | 0.81 | 0.76 | 0.96 | 0.96 | 0.86 | 0.75 | 0.76 | 0.93 | 0.93 | 0.50 | 0.98 | 0.92 |
| C12-2019-11-01-558-c7-q3 | 25 | 1095 | 0.88 | 0.87 | 0.88 | 0.88 | 0.94 | 0.84 | 0.85 | 0.93 | 0.53 | 0.94 | 0.99 | 0.99 |
| C18-2018-07-14-333-c3-q4 | 1 | 518 | 1.00 | 1.00 | 0.95 | 0.95 | 0.98 | 0.79 | 0.76 | 0.55 | 0.55 | 0.50 | 0.95 | 0.58 |
| C20-2019-07-28-282-c13-q1 | 2 | 674 | 0.83 | 0.88 | 0.62 | 0.62 | 0.61 | 0.47 | 0.50 | 0.63 | 0.61 | 0.52 | 0.97 | 0.43 |

## Counterexamples

- `min_snr`: 1 quadrant-nights (≥ 3 positives) with AUC < 0.5: S4-2018-11-07-615-c5-q2 (0.41, n 3); strata with AUC < 0.5: none
- `median_snr`: 1 quadrant-nights (≥ 3 positives) with AUC < 0.5: S4-2018-11-07-615-c5-q2 (0.31, n 3); strata with AUC < 0.5: none
- `fit_rms_residual_arcsec`: 0 quadrant-nights (≥ 3 positives) with AUC < 0.5; strata with AUC < 0.5: none
- `fit_max_residual_arcsec`: 0 quadrant-nights (≥ 3 positives) with AUC < 0.5; strata with AUC < 0.5: none
- `magnitude_range_mag`: 0 quadrant-nights (≥ 3 positives) with AUC < 0.5; strata with AUC < 0.5: none
- `magnitude_range_sigma`: 9 quadrant-nights (≥ 3 positives) with AUC < 0.5: C-2018-10-06-448-c9-q3 (0.32, n 8), D-2019-06-02-281-c16-q1 (0.44, n 5), S1-2018-09-19-508-c10-q1 (0.46, n 10), S4-2018-11-07-615-c5-q1 (0.07, n 3), N6-2019-07-29-338-c6-q1 (0.43, n 23), N7-2019-12-29-611-c9-q3 (0.36, n 16), N10-2018-11-12-504-c2-q3 (0.50, n 7), N13-2018-08-21-394-c12-q4 (0.46, n 19), N22-2018-09-06-553-c4-q4 (0.35, n 9); strata with AUC < 0.5: depth_margin=>=1.5 (0.38, n 109)
- `magnitude_chi2`: 10 quadrant-nights (≥ 3 positives) with AUC < 0.5: C-2018-10-06-448-c9-q3 (0.33, n 8), D-2019-06-02-281-c16-q1 (0.44, n 5), S1-2018-09-19-508-c10-q1 (0.42, n 10), S4-2018-11-07-615-c5-q1 (0.09, n 3), N6-2019-07-29-338-c6-q1 (0.39, n 23), N7-2019-12-29-611-c9-q3 (0.38, n 16), N10-2018-11-12-504-c2-q3 (0.49, n 7), N13-2018-08-21-394-c12-q4 (0.44, n 19), N15-2019-07-29-338-c13-q3 (0.48, n 21), N22-2018-09-06-553-c4-q4 (0.33, n 9); strata with AUC < 0.5: depth_margin=>=1.5 (0.39, n 109)
- `flagged_detection_count`: 0 quadrant-nights (≥ 3 positives) with AUC < 0.5; strata with AUC < 0.5: proximity_group=zone (0.44, n 6), mask_state=all (0.35, n 16)
- `masked_detection_count`: 0 quadrant-nights (≥ 3 positives) with AUC < 0.5; strata with AUC < 0.5: proximity_group=zone (0.36, n 6), mask_state=all (0.25, n 16), mask_state=partial (0.41, n 6)
- `edge_detection_count`: 1 quadrant-nights (≥ 3 positives) with AUC < 0.5: N7-2019-12-29-611-c9-q3 (0.47, n 16); strata with AUC < 0.5: none
- `sharp_abs_max`: 0 quadrant-nights (≥ 3 positives) with AUC < 0.5; strata with AUC < 0.5: none
- `shared_detection_tracklets`: 1 quadrant-nights (≥ 3 positives) with AUC < 0.5: D-2019-06-02-281-c16-q2 (0.49, n 5); strata with AUC < 0.5: none

### `min_snr` (frozen): positives in the bottom half of their background (58)

| field | object | q | value | role | group | depth | mask | crowding |
|---|---|---|---|---|---|---|---|---|
| S4-2018-11-07-615-c5-q2 | 236076 | 0.949 | 3.210 | marginal | control | <0.5 | unmasked | <20k |
| S1-2018-09-19-508-c10-q2 | 109539 | 0.944 | 3.190 | marginal | control | <0.5 | unmasked | <20k |
| C12-2019-11-01-558-c7-q3 | 724903 | 0.939 | 4.340 | marginal | intermediate | <0.5 | unmasked | <20k |
| N6-2019-07-29-338-c6-q1 | 190665 | 0.885 | 3.630 | marginal | intermediate | <0.5 | unmasked | <20k |
| N7-2019-12-29-611-c9-q3 | 299501 | 0.861 | 3.140 | marginal | control | <0.5 | unmasked | <20k |
| N6-2019-07-29-338-c6-q1 | 224596 | 0.837 | 4.540 | marginal | control | <0.5 | unmasked | <20k |
| S1-2018-09-19-508-c10-q4 | 236034 | 0.833 | 3.450 | marginal | intermediate | <0.5 | unmasked | <20k |
| S2-2018-09-27-509-c14-q3 | 59199 | 0.833 | 3.020 | marginal | control | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q4 | 347004 | 0.824 | 3.710 | marginal | intermediate | <0.5 | unmasked | <20k |
| N3-2019-09-23-1441-c5-q4 | 235916 | 0.823 | 3.350 | marginal | control | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q4 | 425227 | 0.811 | 3.900 | marginal | control | <0.5 | unmasked | <20k |
| N6-2019-07-29-338-c6-q1 | 287000 | 0.808 | 4.770 | marginal | control | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q3 | 144741 | 0.807 | 3.450 | marginal | outer | <0.5 | unmasked | <20k |
| C7-2019-01-25-565-c3-q2 | 294411 | 0.802 | 3.780 | marginal | control | <0.5 | unmasked | <20k |
| S1-2018-09-19-508-c10-q4 | 172959 | 0.792 | 3.730 | marginal | outer | <0.5 | unmasked | <20k |
| C7-2019-01-25-565-c3-q2 | 437215 | 0.791 | 3.830 | marginal | control | <0.5 | unmasked | <20k |
| N16-2019-12-29-568-c15-q4 | 243385 | 0.786 | 3.880 | marginal | control | <0.5 | unmasked | <20k |
| N6-2019-07-29-338-c6-q1 | 227702 | 0.784 | 4.900 | marginal | intermediate | <0.5 | unmasked | <20k |
| N16-2019-12-29-568-c15-q4 | 294094 | 0.782 | 3.920 | marginal | control | <0.5 | unmasked | <20k |
| N10-2018-11-12-504-c2-q3 | 111876 | 0.771 | 4.640 | marginal | control | <0.5 | unmasked | <20k |
| N6-2019-07-29-338-c6-q1 | 638148 | 0.769 | 4.950 | marginal | control | <0.5 | unmasked | <20k |
| N13-2018-08-21-394-c12-q4 | 461220 | 0.767 | 3.760 | marginal | control | <0.5 | unmasked | <20k |
| N19-2019-01-25-614-c2-q1 | 644121 | 0.758 | 4.080 | marginal | intermediate | <0.5 | all | <20k |
| B-2019-01-25-565-c13-q4 | 636776 | 0.757 | 4.190 | marginal | control | 0.5-1.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q3 | 255879 | 0.727 | 3.890 | marginal | control | <0.5 | unmasked | <20k |
| S4-2018-11-07-615-c5-q2 | 130420 | 0.715 | 4.720 | marginal | intermediate | <0.5 | unmasked | <20k |
| N10-2018-11-12-504-c2-q3 | 239370 | 0.700 | 5.010 | marginal | intermediate | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q2 | 162387 | 0.692 | 3.450 | marginal | intermediate | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q4 | 365815 | 0.689 | 4.850 | marginal | control | <0.5 | unmasked | <20k |
| N22-2018-09-06-553-c4-q4 | 242307 | 0.681 | 3.340 | marginal | intermediate | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q2 | 105012 | 0.677 | 3.600 | marginal | intermediate | <0.5 | unmasked | <20k |
| N6-2019-07-29-338-c6-q1 | 565228 | 0.673 | 5.540 | primary | control | <0.5 | unmasked | <20k |
| S2-2018-09-27-509-c14-q2 | 28644 | 0.667 | 4.770 | marginal | control | <0.5 | unmasked | <20k |
| S2-2018-09-27-509-c14-q2 | 99800 | 0.667 | 3.940 | marginal | intermediate | <0.5 | unmasked | <20k |
| N11-2018-10-31-559-c3-q1 | 187041 | 0.656 | 3.870 | marginal | control | <0.5 | unmasked | <20k |
| S4-2018-11-07-615-c5-q3 | 6490 | 0.638 | 5.660 | marginal | intermediate | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q3 | 647852 | 0.631 | 5.170 | marginal | control | <0.5 | unmasked | <20k |
| N3-2019-09-23-1441-c5-q4 | 447475 | 0.618 | 4.420 | marginal | intermediate | <0.5 | unmasked | <20k |
| N7-2019-12-29-611-c9-q3 | 565559 | 0.616 | 3.700 | marginal | control | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q2 | 336915 | 0.608 | 3.910 | marginal | intermediate | <0.5 | unmasked | <20k |
| S1-2018-09-19-508-c10-q4 | 109139 | 0.604 | 4.530 | marginal | control | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q2 | 203318 | 0.600 | 3.950 | marginal | intermediate | <0.5 | unmasked | <20k |
| S2-2018-09-27-509-c14-q1 | 27824 | 0.591 | 4.590 | marginal | control | <0.5 | unmasked | <20k |
| N16-2019-12-29-568-c15-q4 | 261278 | 0.591 | 4.700 | marginal | control | <0.5 | unmasked | <20k |
| S4-2018-11-07-615-c5-q3 | 140669 | 0.584 | 6.120 | marginal | intermediate | <0.5 | unmasked | <20k |
| S4-2018-11-07-615-c5-q3 | 106635 | 0.559 | 6.420 | marginal | control | 0.5-1.5 | unmasked | <20k |
| N11-2018-10-31-559-c3-q1 | 239880 | 0.557 | 4.920 | marginal | intermediate | <0.5 | unmasked | <20k |
| N15-2019-07-29-338-c13-q3 | 225013 | 0.556 | 5.540 | marginal | control | <0.5 | unmasked | <20k |
| N15-2019-07-29-338-c13-q3 | 340160 | 0.556 | 5.710 | marginal | control | <0.5 | unmasked | <20k |
| N16-2019-12-29-568-c15-q4 | 459039 | 0.539 | 4.840 | marginal | control | <0.5 | unmasked | <20k |
| S2-2018-09-27-509-c14-q4 | 32491 | 0.536 | 6.130 | primary | control | <0.5 | unmasked | <20k |
| N7-2019-12-29-611-c9-q3 | 160576 | 0.535 | 3.990 | marginal | control | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q4 | 205447 | 0.527 | 5.590 | primary | outer | 0.5-1.5 | unmasked | <20k |
| S1-2018-09-19-508-c10-q4 | 362148 | 0.521 | 4.940 | marginal | control | <0.5 | unmasked | <20k |
| N15-2019-07-29-338-c13-q3 | 2014 QM486 | 0.518 | 6.320 | primary | control | 0.5-1.5 | unmasked | <20k |
| C12-2019-11-01-558-c7-q3 | 363877 | 0.514 | 5.710 | marginal | control | <0.5 | unmasked | <20k |
| N21-2019-01-28-474-c8-q4 | 74168 | 0.510 | 4.780 | marginal | control | <0.5 | unmasked | <20k |
| N12-2019-11-01-607-c1-q2 | 640067 | 0.503 | 4.090 | marginal | intermediate | <0.5 | unmasked | <20k |

### `median_snr` (frozen): positives in the bottom half of their background (60)

| field | object | q | value | role | group | depth | mask | crowding |
|---|---|---|---|---|---|---|---|---|
| C7-2019-01-25-565-c3-q2 | 437215 | 0.966 | 4.600 | marginal | control | <0.5 | unmasked | <20k |
| N16-2019-12-29-568-c15-q4 | 294094 | 0.950 | 4.030 | marginal | control | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q4 | 347004 | 0.946 | 3.990 | marginal | intermediate | <0.5 | unmasked | <20k |
| N6-2019-07-29-338-c6-q1 | 190665 | 0.933 | 4.550 | marginal | intermediate | <0.5 | unmasked | <20k |
| N6-2019-07-29-338-c6-q1 | 224596 | 0.923 | 5.100 | marginal | control | <0.5 | unmasked | <20k |
| N6-2019-07-29-338-c6-q1 | 227702 | 0.923 | 5.350 | marginal | intermediate | <0.5 | unmasked | <20k |
| N6-2019-07-29-338-c6-q1 | 638148 | 0.923 | 5.240 | marginal | control | <0.5 | unmasked | <20k |
| N6-2019-07-29-338-c6-q1 | 287000 | 0.904 | 5.820 | marginal | control | <0.5 | unmasked | <20k |
| N6-2019-07-29-338-c6-q1 | 565228 | 0.904 | 5.840 | primary | control | <0.5 | unmasked | <20k |
| N13-2018-08-21-394-c12-q4 | 461220 | 0.898 | 4.410 | marginal | control | <0.5 | unmasked | <20k |
| C12-2019-11-01-558-c7-q3 | 724903 | 0.896 | 5.770 | marginal | intermediate | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q4 | 365815 | 0.892 | 5.190 | marginal | control | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q4 | 425227 | 0.892 | 5.230 | marginal | control | <0.5 | unmasked | <20k |
| S4-2018-11-07-615-c5-q3 | 6490 | 0.880 | 5.690 | marginal | intermediate | <0.5 | unmasked | <20k |
| S4-2018-11-07-615-c5-q2 | 236076 | 0.872 | 5.870 | marginal | control | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q2 | 162387 | 0.869 | 5.010 | marginal | intermediate | <0.5 | unmasked | <20k |
| N16-2019-12-29-568-c15-q4 | 459039 | 0.863 | 4.990 | marginal | control | <0.5 | unmasked | <20k |
| S4-2018-11-07-615-c5-q2 | 130420 | 0.854 | 6.200 | marginal | intermediate | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q3 | 144741 | 0.852 | 4.630 | marginal | outer | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q2 | 203318 | 0.839 | 5.400 | marginal | intermediate | <0.5 | unmasked | <20k |
| N11-2018-10-31-559-c3-q1 | 187041 | 0.836 | 4.400 | marginal | control | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q4 | 636776 | 0.777 | 6.690 | marginal | control | 0.5-1.5 | unmasked | <20k |
| C7-2019-01-25-565-c3-q2 | 294411 | 0.774 | 6.920 | marginal | control | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q2 | 336915 | 0.754 | 6.000 | marginal | intermediate | <0.5 | unmasked | <20k |
| S1-2018-09-19-508-c10-q4 | 362148 | 0.750 | 5.030 | marginal | control | <0.5 | unmasked | <20k |
| S4-2018-11-07-615-c5-q3 | 122386 | 0.747 | 7.780 | marginal | control | <0.5 | unmasked | <20k |
| N12-2019-11-01-607-c1-q2 | 629080 | 0.729 | 4.530 | marginal | intermediate | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q2 | 105012 | 0.723 | 6.100 | marginal | intermediate | <0.5 | unmasked | <20k |
| S1-2018-09-19-508-c10-q2 | 109539 | 0.722 | 6.070 | marginal | control | <0.5 | unmasked | <20k |
| N22-2018-09-06-553-c4-q4 | 242307 | 0.715 | 4.470 | marginal | intermediate | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q3 | 647852 | 0.705 | 6.010 | marginal | control | <0.5 | unmasked | <20k |
| N15-2019-07-29-338-c13-q3 | 225013 | 0.704 | 6.130 | marginal | control | <0.5 | unmasked | <20k |
| N4-2020-09-15-447-c3-q4 | 615848 | 0.703 | 3.900 | marginal | control | <0.5 | unmasked | <20k |
| N10-2018-11-12-504-c2-q3 | 111876 | 0.698 | 8.830 | marginal | control | <0.5 | unmasked | <20k |
| C12-2019-11-01-558-c7-q3 | 541135 | 0.690 | 6.440 | marginal | intermediate | <0.5 | partial | <20k |
| S2-2018-09-27-509-c14-q2 | 28644 | 0.667 | 5.820 | marginal | control | <0.5 | unmasked | <20k |
| S2-2018-09-27-509-c14-q2 | 99800 | 0.667 | 4.200 | marginal | intermediate | <0.5 | unmasked | <20k |
| N15-2019-07-29-338-c13-q3 | 340160 | 0.667 | 6.840 | marginal | control | <0.5 | unmasked | <20k |
| N10-2018-11-12-504-c2-q3 | 239370 | 0.647 | 9.300 | marginal | intermediate | <0.5 | unmasked | <20k |
| S2-2018-09-27-509-c14-q1 | 27824 | 0.636 | 5.380 | marginal | control | <0.5 | unmasked | <20k |
| N7-2019-12-29-611-c9-q3 | 299501 | 0.628 | 4.980 | marginal | control | <0.5 | unmasked | <20k |
| N7-2019-12-29-611-c9-q3 | 565559 | 0.628 | 5.240 | marginal | control | <0.5 | unmasked | <20k |
| N16-2019-12-29-568-c15-q4 | 243385 | 0.616 | 6.120 | marginal | control | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q3 | 255879 | 0.614 | 6.790 | marginal | control | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q1 | 204282 | 0.611 | 4.990 | marginal | outer | <0.5 | unmasked | <20k |
| N24-2019-08-21-335-c10-q3 | 114058 | 0.600 | 5.940 | marginal | outer | <0.5 | unmasked | 20-80k |
| N3-2019-09-23-1441-c5-q4 | 655444 | 0.590 | 6.950 | marginal | control | <0.5 | unmasked | <20k |
| N21-2019-01-28-474-c8-q4 | 111300 | 0.581 | 6.210 | marginal | control | <0.5 | unmasked | <20k |
| N19-2019-01-25-614-c2-q1 | 644121 | 0.576 | 7.450 | marginal | intermediate | <0.5 | all | <20k |
| N21-2019-01-28-474-c8-q4 | 74168 | 0.574 | 6.240 | marginal | control | <0.5 | unmasked | <20k |
| S4-2018-11-07-615-c5-q3 | 67755 | 0.568 | 9.310 | marginal | intermediate | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q4 | 359987 | 0.540 | 8.070 | marginal | control | <0.5 | unmasked | <20k |
| S4-2018-11-07-615-c5-q3 | 31347 | 0.529 | 9.530 | marginal | control | 0.5-1.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q4 | 235622 | 0.527 | 8.190 | marginal | control | 0.5-1.5 | unmasked | <20k |
| S4-2018-11-07-615-c5-q3 | 106635 | 0.526 | 9.550 | marginal | control | 0.5-1.5 | unmasked | <20k |
| C4-2019-08-20-335-c11-q1 | 355621 | 0.523 | 5.180 | marginal | control | <0.5 | unmasked | 20-80k |
| N16-2019-12-29-568-c15-q4 | 261278 | 0.519 | 6.470 | marginal | control | <0.5 | unmasked | <20k |
| S4-2018-11-07-615-c5-q4 | 117524 | 0.512 | 8.080 | marginal | outer | <0.5 | unmasked | <20k |
| N7-2019-12-29-611-c9-q3 | 350443 | 0.512 | 6.910 | marginal | control | 0.5-1.5 | unmasked | <20k |
| C7-2019-01-25-565-c3-q2 | 183143 | 0.511 | 8.660 | primary | zone | 0.5-1.5 | all | <20k |

### `fit_rms_residual_arcsec` (frozen): positives in the bottom half of their background (12)

| field | object | q | value | role | group | depth | mask | crowding |
|---|---|---|---|---|---|---|---|---|
| S2-2018-09-27-509-c14-q2 | 99800 | 1.000 | 0.239 | marginal | intermediate | <0.5 | unmasked | <20k |
| S4-2018-11-07-615-c5-q2 | 130420 | 0.871 | 0.330 | marginal | intermediate | <0.5 | unmasked | <20k |
| N14-2018-11-02-562-c3-q3 | 91398 | 0.856 | 0.330 | marginal | outer | <0.5 | unmasked | 20-80k |
| B-2019-01-25-565-c13-q1 | 204282 | 0.833 | 0.309 | marginal | outer | <0.5 | unmasked | <20k |
| C12-2019-11-01-558-c7-q3 | 616839 | 0.783 | 0.308 | marginal | control | <0.5 | unmasked | <20k |
| S4-2018-11-07-615-c5-q3 | 122386 | 0.764 | 0.310 | marginal | control | <0.5 | unmasked | <20k |
| N3-2019-09-23-1441-c5-q4 | 158008 | 0.616 | 0.289 | marginal | intermediate | <0.5 | unmasked | <20k |
| B-2019-01-25-565-c13-q4 | 365815 | 0.595 | 0.284 | marginal | control | <0.5 | unmasked | <20k |
| C20-2019-07-28-282-c13-q1 | 140142 | 0.585 | 0.275 | marginal | outer | 0.5-1.5 | unmasked | >=80k |
| N4-2020-09-15-447-c3-q4 | 615848 | 0.568 | 0.289 | marginal | control | <0.5 | unmasked | <20k |
| N20-2018-09-27-499-c1-q2 | 241729 | 0.545 | 0.292 | marginal | outer | <0.5 | unmasked | <20k |
| S4-2018-11-07-615-c5-q2 | 92537 | 0.518 | 0.252 | marginal | control | <0.5 | unmasked | <20k |

### `magnitude_range_mag` (frozen): positives in the bottom half of their background (12)

| field | object | q | value | role | group | depth | mask | crowding |
|---|---|---|---|---|---|---|---|---|
| C12-2019-11-01-558-c7-q3 | 1789 | 0.882 | 0.933 | primary | intermediate | >=1.5 | unmasked | <20k |
| N10-2018-11-12-504-c2-q3 | 155080 | 0.683 | 1.678 | primary | control | 0.5-1.5 | unmasked | <20k |
| S2-2018-09-27-509-c14-q2 | 28644 | 0.667 | 1.374 | marginal | control | <0.5 | unmasked | <20k |
| S2-2018-09-27-509-c14-q2 | 52263 | 0.667 | 1.234 | primary | intermediate | 0.5-1.5 | unmasked | <20k |
| S4-2018-11-07-615-c5-q3 | 67755 | 0.660 | 1.784 | marginal | intermediate | <0.5 | unmasked | <20k |
| D-2019-06-02-281-c16-q3 | 284501 | 0.619 | 0.848 | marginal | control | <0.5 | unmasked | >=80k |
| D-2019-06-02-281-c16-q1 | 387590 | 0.605 | 0.722 | marginal | intermediate | <0.5 | unmasked | >=80k |
| S1-2018-09-19-508-c10-q1 | 68877 | 0.577 | 1.290 | primary | control | >=1.5 | unmasked | <20k |
| N6-2019-07-29-338-c6-q1 | 5494 | 0.577 | 1.036 | primary | control | >=1.5 | unmasked | <20k |
| C20-2019-07-28-282-c13-q1 | 140142 | 0.550 | 1.124 | marginal | outer | 0.5-1.5 | unmasked | >=80k |
| N24-2019-08-21-335-c10-q3 | 93731 | 0.540 | 0.863 | marginal | outer | <0.5 | unmasked | 20-80k |
| N6-2019-07-29-338-c6-q1 | 48337 | 0.510 | 0.847 | primary | control | 0.5-1.5 | unmasked | <20k |

### `flagged_detection_count` (frozen): positives in the bottom half of their background (18)

| field | object | q | value | role | group | depth | mask | crowding |
|---|---|---|---|---|---|---|---|---|
| N24-2019-08-21-335-c10-q3 | 127430 | 0.890 | 3.000 | marginal | intermediate | <0.5 | all | 20-80k |
| N6-2019-07-29-338-c6-q1 | 72582 | 0.875 | 3.000 | primary | zone | 0.5-1.5 | all | <20k |
| N19-2019-01-25-614-c2-q1 | 644121 | 0.841 | 3.000 | marginal | intermediate | <0.5 | all | <20k |
| D-2019-06-02-281-c16-q3 | 80429 | 0.743 | 1.000 | primary | intermediate | 0.5-1.5 | partial | >=80k |
| N4-2020-09-15-447-c3-q4 | 700974 | 0.703 | 3.000 | primary | outer | <0.5 | all | <20k |
| C4-2019-08-20-335-c11-q1 | 149159 | 0.697 | 3.000 | primary | zone | >=1.5 | all | 20-80k |
| C4-2019-08-20-335-c11-q1 | 223043 | 0.697 | 3.000 | primary | intermediate | >=1.5 | all | 20-80k |
| N14-2018-11-02-562-c3-q3 | 15523 | 0.695 | 3.000 | primary | outer | >=1.5 | all | 20-80k |
| N3-2019-09-23-1441-c5-q4 | 190831 | 0.668 | 3.000 | primary | zone | 0.5-1.5 | all | <20k |
| N11-2018-10-31-559-c3-q1 | 15019 | 0.631 | 3.000 | primary | outer | 0.5-1.5 | all | <20k |
| N15-2019-07-29-338-c13-q3 | 717690 | 0.630 | 3.000 | marginal | intermediate | <0.5 | all | <20k |
| N7-2019-12-29-611-c9-q3 | 63715 | 0.593 | 1.000 | primary | control | >=1.5 | unmasked | <20k |
| C7-2019-01-25-565-c3-q2 | 183143 | 0.545 | 3.000 | primary | zone | 0.5-1.5 | all | <20k |
| N16-2019-12-29-568-c15-q4 | 57084 | 0.524 | 3.000 | primary | intermediate | >=1.5 | all | <20k |
| S4-2018-11-07-615-c5-q3 | 22347 | 0.518 | 3.000 | primary | control | >=1.5 | all | <20k |
| C12-2019-11-01-558-c7-q3 | 19815 | 0.516 | 3.000 | primary | intermediate | 0.5-1.5 | all | <20k |
| C12-2019-11-01-558-c7-q3 | 372178 | 0.516 | 3.000 | marginal | intermediate | <0.5 | all | <20k |
| C12-2019-11-01-558-c7-q3 | 61384 | 0.516 | 3.000 | primary | zone | 0.5-1.5 | all | <20k |

### `masked_detection_count` (frozen): positives in the bottom half of their background (20)

| field | object | q | value | role | group | depth | mask | crowding |
|---|---|---|---|---|---|---|---|---|
| C12-2019-11-01-558-c7-q3 | 19815 | 0.954 | 3.000 | primary | intermediate | 0.5-1.5 | all | <20k |
| C12-2019-11-01-558-c7-q3 | 372178 | 0.954 | 3.000 | marginal | intermediate | <0.5 | all | <20k |
| C12-2019-11-01-558-c7-q3 | 61384 | 0.954 | 3.000 | primary | zone | 0.5-1.5 | all | <20k |
| N24-2019-08-21-335-c10-q3 | 127430 | 0.890 | 3.000 | marginal | intermediate | <0.5 | all | 20-80k |
| N6-2019-07-29-338-c6-q1 | 72582 | 0.875 | 3.000 | primary | zone | 0.5-1.5 | all | <20k |
| C12-2019-11-01-558-c7-q3 | 541135 | 0.861 | 2.000 | marginal | intermediate | <0.5 | partial | <20k |
| C12-2019-11-01-558-c7-q3 | 63935 | 0.861 | 2.000 | primary | intermediate | 0.5-1.5 | partial | <20k |
| C12-2019-11-01-558-c7-q3 | 87001 | 0.861 | 2.000 | marginal | intermediate | <0.5 | partial | <20k |
| N19-2019-01-25-614-c2-q1 | 644121 | 0.841 | 3.000 | marginal | intermediate | <0.5 | all | <20k |
| D-2019-06-02-281-c16-q3 | 80429 | 0.754 | 1.000 | primary | intermediate | 0.5-1.5 | partial | >=80k |
| N4-2020-09-15-447-c3-q4 | 700974 | 0.703 | 3.000 | primary | outer | <0.5 | all | <20k |
| C4-2019-08-20-335-c11-q1 | 149159 | 0.697 | 3.000 | primary | zone | >=1.5 | all | 20-80k |
| C4-2019-08-20-335-c11-q1 | 223043 | 0.697 | 3.000 | primary | intermediate | >=1.5 | all | 20-80k |
| N14-2018-11-02-562-c3-q3 | 15523 | 0.695 | 3.000 | primary | outer | >=1.5 | all | 20-80k |
| N16-2019-12-29-568-c15-q4 | 57084 | 0.693 | 3.000 | primary | intermediate | >=1.5 | all | <20k |
| N3-2019-09-23-1441-c5-q4 | 190831 | 0.669 | 3.000 | primary | zone | 0.5-1.5 | all | <20k |
| N11-2018-10-31-559-c3-q1 | 15019 | 0.631 | 3.000 | primary | outer | 0.5-1.5 | all | <20k |
| N15-2019-07-29-338-c13-q3 | 717690 | 0.630 | 3.000 | marginal | intermediate | <0.5 | all | <20k |
| C7-2019-01-25-565-c3-q2 | 183143 | 0.545 | 3.000 | primary | zone | 0.5-1.5 | all | <20k |
| S4-2018-11-07-615-c5-q3 | 22347 | 0.518 | 3.000 | primary | control | >=1.5 | all | <20k |

### `sharp_abs_max` (frozen): positives in the bottom half of their background (12)

| field | object | q | value | role | group | depth | mask | crowding |
|---|---|---|---|---|---|---|---|---|
| S2-2018-09-27-509-c14-q2 | 52263 | 1.000 | 0.243 | primary | intermediate | 0.5-1.5 | unmasked | <20k |
| S2-2018-09-27-509-c14-q2 | 99800 | 1.000 | 0.324 | marginal | intermediate | <0.5 | unmasked | <20k |
| N23-2019-06-01-279-c6-q1 | 2020 RL147 | 0.676 | 0.389 | marginal | outer | <0.5 | unmasked | >=80k |
| S2-2018-09-27-509-c14-q3 | 59199 | 0.667 | 0.565 | marginal | control | <0.5 | unmasked | <20k |
| D-2019-06-02-281-c16-q2 | 329908 | 0.651 | 0.436 | marginal | control | <0.5 | unmasked | >=80k |
| N6-2019-07-29-338-c6-q1 | 190665 | 0.644 | 0.481 | marginal | intermediate | <0.5 | unmasked | <20k |
| S4-2018-11-07-615-c5-q3 | 6490 | 0.590 | 0.261 | marginal | intermediate | <0.5 | unmasked | <20k |
| S4-2018-11-07-615-c5-q3 | 106635 | 0.586 | 0.260 | marginal | control | 0.5-1.5 | unmasked | <20k |
| S4-2018-11-07-615-c5-q3 | 67755 | 0.566 | 0.253 | marginal | intermediate | <0.5 | unmasked | <20k |
| S4-2018-11-07-615-c5-q3 | 122386 | 0.559 | 0.249 | marginal | control | <0.5 | unmasked | <20k |
| N7-2019-12-29-611-c9-q3 | 299501 | 0.558 | 0.334 | marginal | control | <0.5 | unmasked | <20k |
| N10-2018-11-12-504-c2-q3 | 80733 | 0.514 | 0.136 | primary | intermediate | 0.5-1.5 | unmasked | <20k |

### `shared_detection_tracklets` (frozen): positives in the bottom half of their background (8)

| field | object | q | value | role | group | depth | mask | crowding |
|---|---|---|---|---|---|---|---|---|
| N24-2019-08-21-335-c10-q3 | 93731 | 0.930 | 3.000 | marginal | outer | <0.5 | unmasked | 20-80k |
| D-2019-06-02-281-c16-q2 | 657605 | 0.901 | 1.000 | marginal | outer | <0.5 | unmasked | >=80k |
| D-2019-06-02-281-c16-q1 | 157066 | 0.880 | 1.000 | primary | control | >=1.5 | unmasked | >=80k |
| N23-2019-06-01-279-c6-q1 | 39993 | 0.856 | 1.000 | primary | intermediate | >=1.5 | unmasked | >=80k |
| C20-2019-07-28-282-c13-q1 | 33033 | 0.788 | 1.000 | marginal | outer | <0.5 | unmasked | >=80k |
| C4-2019-08-20-335-c11-q1 | 355621 | 0.758 | 1.000 | marginal | control | <0.5 | unmasked | 20-80k |
| D-2019-06-02-281-c16-q3 | 227423 | 0.689 | 1.000 | marginal | control | <0.5 | unmasked | >=80k |
| S4-2018-11-07-615-c5-q4 | 117524 | 0.683 | 1.000 | marginal | outer | <0.5 | unmasked | <20k |

## Development quadrant-nights

| field | pop | group | filters | sources/frame | tracklets | built | positive / auxiliary / background |
|---|---|---|---|---|---|---|---|
| POC-2018-04-11-535-c11-q3 | R | G-POC-2018-04-11-535-c11-q3 | zr/zr/zr | 13455/12553/8678 | 80 | 14 | 0 / 1 / 13 |
| B-2019-01-25-565-c13-q3 | R | G-B-2019-01-25-565-c13-q1 | zg/zr/zr | 9349/14211/11256 | 494 | 97 | 8 / 1 / 88 |
| C-2018-10-06-448-c9-q3 | R | G-C-2018-10-06-448-c9-q3 | zr/zi/zg | 7863/7569/5117 | 154 | 39 | 8 / 5 / 26 |
| D-2019-06-02-281-c16-q3 | R | G-D-2019-06-02-281-c16-q1 | zr/zr/zr | 150253/131401/149649 | 5634 | 842 | 9 / 0 / 833 |
| S1-2018-09-19-508-c10-q4 | R | G-S1-2018-09-19-508-c10-q1 | zr/zg/zg | 8283/5833/4234 | 290 | 54 | 6 / 0 / 48 |
| S2-2018-09-27-509-c14-q4 | R | G-N20-2018-09-27-499-c1-q2 | zg/zg/zr | 5199/5802/8821 | 651 | 111 | 1 / 0 / 110 |
| S3-2019-07-01-335-c7-q1 | R | G-S3-2019-07-01-335-c7-q1 | zr/zr/zr | 68956/68403/74631 | 424 | 2 | 0 / 0 / 2 |
| S4-2018-11-07-615-c5-q3 | R | G-S4-2018-11-07-615-c5-q1 | zr/zg/zr | 11421/9345/11594 | 23803 | 3493 | 9 / 1 / 3483 |
| B-2019-01-25-565-c13-q1 | R | G-B-2019-01-25-565-c13-q1 | zg/zr/zr | 7472/11570/8896 | 131 | 29 | 10 / 1 / 18 |
| B-2019-01-25-565-c13-q2 | R | G-B-2019-01-25-565-c13-q1 | zg/zr/zr | 8781/13514/10384 | 466 | 77 | 11 / 1 / 65 |
| B-2019-01-25-565-c13-q4 | R | G-B-2019-01-25-565-c13-q1 | zg/zr/zr | 8203/12885/9938 | 479 | 92 | 18 / 0 / 74 |
| D-2019-06-02-281-c16-q1 | R | G-D-2019-06-02-281-c16-q1 | zr/zr/zr | 170571/156437/170860 | 6645 | 965 | 5 / 0 / 960 |
| D-2019-06-02-281-c16-q2 | R | G-D-2019-06-02-281-c16-q1 | zr/zr/zr | 165846/149781/166541 | 4382 | 625 | 5 / 0 / 620 |
| D-2019-06-02-281-c16-q4 | R | G-D-2019-06-02-281-c16-q1 | zr/zr/zr | 181073/155402/167544 | 4210 | 610 | 2 / 0 / 608 |
| S1-2018-09-19-508-c10-q1 | R | G-S1-2018-09-19-508-c10-q1 | zr/zg/zg | 8238/5882/4115 | 204 | 37 | 10 / 1 / 26 |
| S1-2018-09-19-508-c10-q2 | R | G-S1-2018-09-19-508-c10-q1 | zr/zg/zg | 6900/4827/3042 | 141 | 25 | 6 / 1 / 18 |
| S1-2018-09-19-508-c10-q3 | R | G-S1-2018-09-19-508-c10-q1 | zr/zg/zg | 8147/5325/3613 | 120 | 26 | 4 / 1 / 21 |
| S2-2018-09-27-509-c14-q1 | R | G-N20-2018-09-27-499-c1-q2 | zg/zg/zr | 4917/5376/6960 | 120 | 24 | 2 / 0 / 22 |
| S2-2018-09-27-509-c14-q2 | R | G-N20-2018-09-27-499-c1-q2 | zg/zg/zr | 5050/5337/7038 | 21 | 8 | 4 / 1 / 3 |
| S2-2018-09-27-509-c14-q3 | R | G-N20-2018-09-27-499-c1-q2 | zg/zg/zr | 4900/5240/7645 | 16 | 6 | 3 / 0 / 3 |
| S3-2019-07-01-335-c7-q2 | R | G-S3-2019-07-01-335-c7-q1 | zr/zr/zr | 74184/75040/83088 | 157 | 1 | 0 / 0 / 1 |
| S3-2019-07-01-335-c7-q3 | R | G-S3-2019-07-01-335-c7-q1 | zr/zr/zr | 72905/73184/80307 | 405 | 2 | 0 / 0 / 2 |
| S3-2019-07-01-335-c7-q4 | R | G-S3-2019-07-01-335-c7-q1 | zr/zr/zr | 67490/66906/72389 | 924 | 16 | 0 / 0 / 16 |
| S4-2018-11-07-615-c5-q1 | R | G-S4-2018-11-07-615-c5-q1 | zr/zg/zr | 6462/5592/8536 | 80 | 18 | 3 / 0 / 15 |
| S4-2018-11-07-615-c5-q2 | R | G-S4-2018-11-07-615-c5-q1 | zr/zg/zr | 9702/7047/10825 | 7671 | 1121 | 3 / 0 / 1118 |
| S4-2018-11-07-615-c5-q4 | R | G-S4-2018-11-07-615-c5-q1 | zr/zg/zr | 6341/5503/7826 | 316 | 48 | 4 / 3 / 41 |
| N1-2018-11-25-468-c12-q1 | N | G-N1-2018-11-25-468-c12-q1 | zr/zr/zr | 2561/3477/3073 | 604 | 125 | 0 / 0 / 125 |
| N2-2019-11-05-564-c1-q2 | N | G-N2-2019-11-05-564-c1-q2 | zr/zr/zr | 24361/24063/25778 | 1650 | 257 | 5 / 1 / 251 |
| N3-2019-09-23-1441-c5-q4 | N | G-N3-2019-09-23-1441-c5-q4 | zg/zr/zg | 10354/13403/3538 | 3001 | 480 | 16 / 1 / 463 |
| N4-2020-09-15-447-c3-q4 | N | G-N4-2020-09-15-447-c3-q4 | zr/zg/zg | 6814/4404/4452 | 470 | 93 | 18 / 1 / 74 |
| N5-2019-08-27-335-c7-q4 | N | G-N5-2019-08-27-335-c7-q4 | zr/zr/zr | 62956/67303/67485 | 760 | 99 | 3 / 0 / 96 |
| N6-2019-07-29-338-c6-q1 | N | G-N15-2019-07-29-338-c13-q3 | zg/zg/zr | 8228/8276/12027 | 768 | 128 | 23 / 1 / 104 |
| N7-2019-12-29-611-c9-q3 | N | G-N16-2019-12-29-568-c15-q4 | zr/zr/zg | 20195/21354/12988 | 366 | 59 | 16 / 0 / 43 |
| N8-2019-07-24-333-c8-q1 | N | G-C18-2018-07-14-333-c3-q4 | zr/zr/zr | 73792/72645/68893 | 900 | 151 | 5 / 0 / 146 |
| N9-2019-08-31-334-c4-q3 | N | G-N9-2019-08-31-334-c4-q3 | zr/zr/zg | 139175/127949/75699 | 1961 | 281 | 1 / 0 / 280 |
| N10-2018-11-12-504-c2-q3 | N | G-N10-2018-11-12-504-c2-q3 | zi/zg/zr | 4010/4730/4857 | 5129 | 722 | 7 / 1 / 714 |
| N11-2018-10-31-559-c3-q1 | N | G-N11-2018-10-31-559-c3-q1 | zr/zr/zg | 5495/6173/4056 | 355 | 68 | 6 / 1 / 61 |
| N12-2019-11-01-607-c1-q2 | N | G-C12-2019-11-01-558-c7-q3 | zr/zr/zr | 8174/10067/8472 | 6478 | 1011 | 14 / 1 / 996 |
| N13-2018-08-21-394-c12-q4 | N | G-N13-2018-08-21-394-c12-q4 | zi/zr/zg | 9055/10209/6819 | 7280 | 1071 | 19 / 7 / 1045 |
| N14-2018-11-02-562-c3-q3 | N | G-N14-2018-11-02-562-c3-q3 | zr/zg/zr | 25544/17978/40788 | 840 | 151 | 5 / 0 / 146 |
| N15-2019-07-29-338-c13-q3 | N | G-N15-2019-07-29-338-c13-q3 | zg/zg/zr | 8232/8149/12152 | 184 | 49 | 21 / 1 / 27 |
| N16-2019-12-29-568-c15-q4 | N | G-N16-2019-12-29-568-c15-q4 | zr/zr/zg | 8432/8523/6137 | 3463 | 557 | 15 / 1 / 541 |
| N17-2019-06-27-330-c9-q2 | N | G-N17-2019-06-27-330-c9-q2 | zr/zr/zr | 78187/73441/84489 | 3619 | 515 | 7 / 0 / 508 |
| N18-2018-07-16-333-c13-q2 | N | G-C18-2018-07-14-333-c3-q4 | zr/zr/zr | 178988/175503/177589 | 2451 | 319 | 1 / 0 / 318 |
| N19-2019-01-25-614-c2-q1 | N | G-B-2019-01-25-565-c13-q1 | zg/zr/zr | 10417/16395/13925 | 1440 | 78 | 12 / 0 / 66 |
| N20-2018-09-27-499-c1-q2 | N | G-N20-2018-09-27-499-c1-q2 | zr/zg/zg | 2503/1318/2083 | 82 | 14 | 3 / 0 / 11 |
| N21-2019-01-28-474-c8-q4 | N | G-N21-2019-01-28-474-c8-q4 | zg/zg/zr | 4175/4312/4125 | 2578 | 160 | 5 / 0 / 155 |
| N22-2018-09-06-553-c4-q4 | N | G-N22-2018-09-06-553-c4-q4 | zr/zg/zg | 7877/5407/6018 | 867 | 157 | 9 / 4 / 144 |
| N23-2019-06-01-279-c6-q1 | N | G-N23-2019-06-01-279-c6-q1 | zr/zr/zr | 99989/102729/103708 | 2319 | 181 | 10 / 1 / 170 |
| N24-2019-08-21-335-c10-q3 | N | G-C4-2019-08-20-335-c11-q1 | zr/zr/zr | 56967/51020/50121 | 273 | 55 | 5 / 0 / 50 |
| C4-2019-08-20-335-c11-q1 | C | G-C4-2019-08-20-335-c11-q1 | zr/zr/zr | 68704/74927/63126 | 438 | 72 | 6 / 0 / 66 |
| C7-2019-01-25-565-c3-q2 | C | G-B-2019-01-25-565-c13-q1 | zg/zr/zr | 10529/16240/13502 | 1327 | 188 | 11 / 0 / 177 |
| C12-2019-11-01-558-c7-q3 | C | G-C12-2019-11-01-558-c7-q3 | zr/zr/zr | 5649/6597/7509 | 5088 | 1122 | 25 / 2 / 1095 |
| C18-2018-07-14-333-c3-q4 | C | G-C18-2018-07-14-333-c3-q4 | zr/zr/zr | 185734/191035/189004 | 3541 | 519 | 1 / 0 / 518 |
| C19-2019-07-22-333-c3-q4 | C | G-C18-2018-07-14-333-c3-q4 | zr/zr/zr | 187501/186910/186133 | 4131 | 626 | 0 / 0 / 626 |
| C20-2019-07-28-282-c13-q1 | C | G-C18-2018-07-14-333-c3-q4 | zr/zr/zr | 173790/162820/155090 | 4663 | 676 | 2 / 0 / 674 |

## Label reconciliation with the AS-035/036 traces

Positive (field, object) labelled: 402; traced recovered: 402; labelled not traced: []; traced not labelled: [].
