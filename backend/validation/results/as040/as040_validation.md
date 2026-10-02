# AS-040 sealed validation of the frozen candidate ranker (stage 3; generated)

Generated 2026-10-02 21:47 UTC from code `d012f52c3872c73c8c99d7d6bee46fc6a254272c`. Interpretation: `as040_findings.md`. One-shot: nothing was fitted, selected or tuned.

Frozen inputs verified before the validation table was built or read (25 checks, `as040_frozen_check.json`): manifest `63e12b9feb8bc376…`, AS-038 table `da670e38357503fe…`, AS-038 list `a8182bc63649f6f0…`, AS-039 frozen ranker `875a0647a61f9bac…`; validation digest `a549b6bc22a54f14…`.

24 validation quadrant-nights in 22 groups; 10817 ranked tracklets {'background': 10511, 'positive': 284, 'auxiliary': 22}; validation table `efa5713392519099…`. Positive object-nights 269 in 24 quadrant-nights.

## Confirmatory verdict (ranking_design.decide, AS-037 §7)

**USEFUL, PROTECTED**

- M1 recall@5 % = 0.939 [95 % group bootstrap 0.902, 0.975]; thresholds: point ≥ 0.5, lower ≥ 0.3; NOT USEFUL if upper < 0.5.
- Minimums: 269 ≥ 100 object-nights, 24 ≥ 15 quadrant-nights with a positive.
- Guard near-star zone vs control: 0.79 vs 0.94 = -0.15 [-0.42, -0.01] (n 14/149) PASS
- Guard faint (MARGINAL) vs PRIMARY: 0.87 vs 0.98 = -0.11 [-0.18, -0.04] (n 96/173) PASS

## Primary and secondary metrics (95 % group bootstrap, 2000)

| ranker | role | recall@1 % | recall@2 % | **recall@5 %** | recall@10 % | recall@20 % | AUC | median q |
|---|---|---|---|---|---|---|---|---|
| `M1` | frozen ranker | 0.881 [0.846, 0.923] | 0.913 [0.881, 0.947] | 0.939 [0.904, 0.974] | 0.967 [0.939, 0.992] | 0.989 [0.974, 1.000] | 0.990 [0.982, 0.995] | 0.000 [0.000, 0.000] |
| `B1:sharp_abs_max` | frozen comparator | 0.353 [0.190, 0.513] | 0.515 [0.365, 0.639] | 0.695 [0.605, 0.766] | 0.861 [0.817, 0.904] | 0.929 [0.890, 0.959] | 0.939 [0.921, 0.951] | 0.019 [0.009, 0.029] |
| `B0` | null reference | 0.004 [0.000, 0.011] | 0.009 [0.000, 0.019] | 0.032 [0.014, 0.050] | 0.076 [0.045, 0.111] | 0.175 [0.121, 0.225] | 0.467 [0.434, 0.493] | 0.542 [0.493, 0.603] |

| ranker | recall@K10 | recall@K25 | recall@K50 | enrichment@1/2/5/10/20 % |
|---|---|---|---|---|
| `M1` | 0.952 [0.919, 0.984] | 0.981 [0.960, 1.000] | 0.981 [0.959, 1.000] | 88.1 / 45.6 / 18.8 / 9.7 / 4.9 |
| `B1:sharp_abs_max` | 0.688 [0.583, 0.829] | 0.881 [0.828, 0.936] | 0.963 [0.925, 0.987] | 35.3 / 25.7 / 13.9 / 8.6 / 4.6 |
| `B0` | 0.045 [0.017, 0.077] | 0.195 [0.132, 0.289] | 0.400 [0.292, 0.543] | 0.4 / 0.5 / 0.6 / 0.8 / 0.9 |

## Comparator analysis (secondary, never deciding)

| contrast | recall@5 % difference [95 % paired group bootstrap] |
|---|---|
| `M1` - B1:sharp_abs_max | 0.243 [0.160, 0.339] |
| `M1` - B0 | 0.907 [0.866, 0.944] |

Top 5 % by M1 only: 71; by `B1:sharp_abs_max` only: 3.

| ranker | decide() level on validation (descriptive for non-M1) | faint guard | zone guard |
|---|---|---|---|
| `M1` | USEFUL, PROTECTED | 0.87 vs 0.98 = -0.11 [-0.18, -0.04] (n 96/173) PASS | 0.79 vs 0.94 = -0.15 [-0.42, -0.01] (n 14/149) PASS |
| `B1:sharp_abs_max` | USEFUL, NOT PROTECTED | 0.41 vs 0.86 = -0.45 [-0.55, -0.33] (n 96/173) FAIL | 0.71 vs 0.71 = 0.01 [-0.27, 0.19] (n 14/149) PASS |
| `B0` | NOT USEFUL | 0.02 vs 0.04 = -0.02 [-0.06, 0.04] (n 96/173) PASS | 0.00 vs 0.03 = -0.03 [-0.07, 0.19] (n 14/149) PASS |

## Descriptive guard views (never deciding)

| ranker | view | result |
|---|---|---|
| `M1` | near-star (zone+outer) vs control [AS-039 development definition] | 0.93 vs 0.94 = -0.00 [-0.13, 0.06] (n 44/149) PASS |
| `M1` | near-star (zone+outer) vs intermediate+control | 0.93 vs 0.94 = -0.01 [-0.13, 0.05] (n 44/225) PASS |
| `M1` | zone PRIMARY vs control PRIMARY | 0.79 vs 1.00 = -0.21 [-0.48, -0.07] (n 14/92) FAIL |
| `M1` | control MARGINAL vs control PRIMARY | 0.83 vs 1.00 = -0.17 [-0.27, -0.08] (n 57/92) PASS |
| `B1:sharp_abs_max` | near-star (zone+outer) vs control [AS-039 development definition] | 0.68 vs 0.71 = -0.03 [-0.19, 0.11] (n 44/149) PASS |
| `B1:sharp_abs_max` | near-star (zone+outer) vs intermediate+control | 0.68 vs 0.70 = -0.02 [-0.17, 0.12] (n 44/225) PASS |
| `B1:sharp_abs_max` | zone PRIMARY vs control PRIMARY | 0.71 vs 0.86 = -0.15 [-0.42, 0.03] (n 14/92) PASS |
| `B1:sharp_abs_max` | control MARGINAL vs control PRIMARY | 0.46 vs 0.86 = -0.41 [-0.55, -0.26] (n 57/92) FAIL |
| `B0` | near-star (zone+outer) vs control [AS-039 development definition] | 0.05 vs 0.03 = 0.02 [-0.03, 0.13] (n 44/149) PASS |
| `B0` | near-star (zone+outer) vs intermediate+control | 0.05 vs 0.03 = 0.02 [-0.03, 0.13] (n 44/225) PASS |
| `B0` | zone PRIMARY vs control PRIMARY | 0.00 vs 0.04 = -0.04 [-0.11, 0.17] (n 14/92) PASS |
| `B0` | control MARGINAL vs control PRIMARY | 0.02 vs 0.04 = -0.02 [-0.09, 0.05] (n 57/92) PASS |

## Strata (recall@5 % / AUC, object-nights)

| stratum | n | `M1` | `B1:sharp_abs_max` | `B0` |
|---|---|---|---|---|
| role=marginal | 96 | 0.87 / 0.98 | 0.41 / 0.89 | 0.02 / 0.49 |
| role=primary | 173 | 0.98 / 1.00 | 0.86 / 0.97 | 0.04 / 0.45 |
| near_star=intermediate+control | 225 | 0.94 / 0.99 | 0.70 / 0.94 | 0.03 / 0.47 |
| near_star=zone+outer | 44 | 0.93 / 0.99 | 0.68 / 0.94 | 0.05 / 0.47 |
| proximity_group=control | 149 | 0.94 / 0.99 | 0.71 / 0.94 | 0.03 / 0.47 |
| proximity_group=intermediate | 76 | 0.95 / 0.99 | 0.68 / 0.94 | 0.03 / 0.45 |
| proximity_group=outer | 30 | 1.00 / 1.00 | 0.67 / 0.94 | 0.07 / 0.45 |
| proximity_group=zone | 14 | 0.79 / 0.97 | 0.71 / 0.93 | 0.00 / 0.51 |
| depth_margin=0.5-1.5 | 106 | 0.97 / 0.99 | 0.75 / 0.96 | 0.04 / 0.46 |
| depth_margin=<0.5 | 89.5 | 0.85 / 0.98 | 0.40 / 0.88 | 0.01 / 0.49 |
| depth_margin=>=1.5 | 73.5 | 1.00 / 1.00 | 0.97 / 0.98 | 0.05 / 0.45 |
| crowding=20-80k | 29 | 0.97 / 1.00 | 0.55 / 0.94 | 0.00 / 0.38 |
| crowding=<20k | 226 | 0.94 / 0.99 | 0.72 / 0.94 | 0.03 / 0.48 |
| crowding=>=80k | 14 | 0.79 / 0.97 | 0.57 / 0.85 | 0.07 / 0.49 |
| filters=mixed | 172 | 0.93 / 0.99 | 0.66 / 0.93 | 0.02 / 0.47 |
| filters=single | 97 | 0.95 / 0.99 | 0.76 / 0.95 | 0.05 / 0.46 |
| speed=0.25-0.5 | 85 | 0.96 / 0.99 | 0.72 / 0.93 | 0.05 / 0.48 |
| speed=0.5-1.0 | 155 | 0.93 / 0.99 | 0.70 / 0.94 | 0.02 / 0.46 |
| speed=<0.25 | 29 | 0.93 / 0.99 | 0.59 / 0.96 | 0.03 / 0.49 |
| mask_state=all | 14 | 0.86 / 0.98 | 0.79 / 0.97 | 0.07 / 0.62 |
| mask_state=partial | 6 | 0.67 / 0.95 | 0.33 / 0.89 | 0.00 / 0.40 |
| mask_state=unmasked | 249 | 0.95 / 0.99 | 0.70 / 0.94 | 0.03 / 0.46 |
| population=C | 269 | 0.94 / 0.99 | 0.70 / 0.94 | 0.03 / 0.47 |
| star_class=6-8 | 55 | 0.95 / 0.99 | 0.65 / 0.94 | 0.04 / 0.50 |
| star_class=8-10 | 193 | 0.94 / 0.99 | 0.70 / 0.94 | 0.03 / 0.45 |
| star_class=V<6 | 21 | 0.90 / 0.99 | 0.71 / 0.96 | 0.05 / 0.56 |

## End-to-end (secondary): eligible targets recovered and in the top 5 % (M1)

| stratum | eligible object-nights | recovered + top 5 % | end-to-end recall |
|---|---|---|---|
| all | 514 | 249 | 0.484 |
| zone | 26 | 10.5 | 0.404 |
| outer | 57 | 30 | 0.526 |
| intermediate | 146 | 71 | 0.486 |
| control | 285 | 137.5 | 0.482 |
| primary | 229 | 166 | 0.725 |
| marginal | 285 | 83 | 0.291 |

## Sensitivity (descriptive)

| ranker | analysis | value |
|---|---|---|
| `M1` | without background sharing a detection with a positive (recall@5%) | 0.939 |
| `M1` | without background sharing a detection with a positive (AUC) | 0.990 |
| `M1` | without 105890 (recall@5%) | 0.938 |
| `M1` | without 105890 (AUC) | 0.990 |
| `B1:sharp_abs_max` | without background sharing a detection with a positive (recall@5%) | 0.691 |
| `B1:sharp_abs_max` | without background sharing a detection with a positive (AUC) | 0.940 |
| `B1:sharp_abs_max` | without 105890 (recall@5%) | 0.694 |
| `B1:sharp_abs_max` | without 105890 (AUC) | 0.939 |
| `B0` | without background sharing a detection with a positive (recall@5%) | 0.032 |
| `B0` | without background sharing a detection with a positive (AUC) | 0.466 |
| `B0` | without 105890 (recall@5%) | 0.032 |
| `B0` | without 105890 (AUC) | 0.467 |

## Per quadrant-night

| field | group | positives | background | auxiliary | M1 recall@5 % | M1 AUC | comparator recall@5 % | shortlist background |
|---|---|---|---|---|---|---|---|---|
| C1-2020-06-17-333-c11-q1 | G-C1-2020-06-17-333-c11-q1 | 3 | 368 | 1 | 0.67 | 0.921 | 0.00 | 18 |
| C2-2019-08-01-553-c11-q3 | G-C2-2019-08-01-553-c11-q3 | 7 | 1340 | 0 | 1.00 | 1.000 | 0.86 | 67 |
| C3-2018-12-13-559-c9-q2 | G-C3-2018-12-13-559-c9-q2 | 6 | 519 | 0 | 1.00 | 0.998 | 1.00 | 26 |
| C5-2020-09-21-447-c9-q1 | G-C5-2020-09-21-447-c9-q1 | 12 | 42 | 3 | 1.00 | 0.996 | 0.92 | 2 |
| C6-2018-07-12-283-c15-q1 | G-C6-2018-07-12-283-c15-q1 | 1 | 348 | 0 | 0.00 | 0.825 | 0.00 | 17 |
| C8-2020-11-14-613-c4-q2 | G-C8-2020-11-14-613-c4-q2 | 9 | 118 | 1 | 0.89 | 0.991 | 0.00 | 6 |
| C9-2020-04-17-373-c1-q1 | G-C9-2020-04-17-373-c1-q1 | 39 | 397 | 4 | 1.00 | 0.997 | 0.67 | 20 |
| C10-2020-08-14-447-c2-q1 | G-C10-2020-08-14-447-c2-q1 | 19 | 128 | 1 | 1.00 | 0.998 | 0.68 | 6 |
| C11-2020-08-27-447-c2-q1 | G-C10-2020-08-14-447-c2-q1 | 14 | 96 | 0 | 0.86 | 0.986 | 0.71 | 5 |
| C13-2018-09-16-393-c14-q1 | G-C13-2018-09-16-393-c14-q1 | 16 | 126 | 0 | 1.00 | 0.998 | 0.69 | 6 |
| C14-2019-02-08-518-c16-q4 | G-C14-2019-02-08-518-c16-q4 | 18 | 114 | 1 | 1.00 | 1.000 | 0.61 | 6 |
| C15-2019-01-04-500-c15-q4 | G-C15-2019-01-04-500-c15-q4 | 3 | 26 | 0 | 1.00 | 1.000 | 1.00 | 1 |
| C16-2020-01-29-511-c13-q3 | G-C16-2020-01-29-511-c13-q3 | 3 | 210 | 0 | 1.00 | 0.998 | 1.00 | 11 |
| C17-2020-09-22-561-c15-q2 | G-C17-2020-09-22-561-c15-q2 | 15 | 116 | 1 | 0.93 | 0.991 | 0.53 | 6 |
| C21-2020-08-23-452-c15-q3 | G-C21-2020-08-23-452-c15-q3 | 9 | 347 | 0 | 1.00 | 0.999 | 1.00 | 17 |
| C22-2020-02-24-517-c15-q3 | G-C22-2020-02-24-517-c15-q3 | 9 | 141 | 0 | 0.89 | 0.991 | 0.56 | 7 |
| C23-2020-11-17-659-c4-q2 | G-C23-2020-11-17-659-c4-q2 | 8 | 80 | 1 | 1.00 | 1.000 | 0.88 | 4 |
| C24-2019-06-29-279-c5-q2 | G-C24-2019-06-29-279-c5-q2 | 7 | 69 | 0 | 0.86 | 0.990 | 0.71 | 3 |
| C25-2018-07-05-331-c9-q4 | G-C25-2018-07-05-331-c9-q4 | 3 | 1159 | 0 | 1.00 | 0.999 | 1.00 | 58 |
| C26-2020-11-26-612-c3-q1 | G-C26-2020-11-26-612-c3-q1 | 9 | 53 | 0 | 1.00 | 1.000 | 0.67 | 3 |
| C27-2020-11-15-392-c7-q4 | G-C27-2020-11-15-392-c7-q4 | 8 | 36 | 0 | 0.75 | 0.918 | 0.50 | 2 |
| C28-2020-01-04-657-c4-q3 | G-C28-2020-01-04-657-c4-q3 | 4 | 1062 | 0 | 1.00 | 0.998 | 0.75 | 53 |
| C29-2020-01-28-617-c2-q2 | G-C29-2020-01-28-617-c2-q2 | 18 | 71 | 4 | 0.81 | 0.980 | 0.44 | 4 |
| C30-2020-01-28-1613-c9-q2 | G-C29-2020-01-28-617-c2-q2 | 29 | 3545 | 5 | 0.90 | 0.984 | 1.00 | 177 |

## Development (AS-039 CV) vs validation (descriptive only)

### `M1`

| metric | development | validation | validation − development |
|---|---|---|---|
| recall@5% | 0.955 | 0.939 | -0.017 |
| recall@1% | 0.878 | 0.881 | 0.003 |
| recall@2% | 0.915 | 0.913 | -0.003 |
| recall@10% | 0.978 | 0.967 | -0.011 |
| recall@20% | 0.990 | 0.989 | -0.001 |
| recall@K10 | 0.950 | 0.952 | 0.001 |
| recall@K25 | 0.980 | 0.981 | 0.001 |
| recall@K50 | 0.990 | 0.981 | -0.009 |
| AUC | 0.990 | 0.990 | -0.000 |
| faint guard difference | -0.121 | -0.107 | 0.014 |
| MARGINAL recall@5% | 0.879 | 0.870 | -0.009 |
| PRIMARY recall@5% | 1.000 | 0.977 | -0.023 |
| zone+outer vs control difference | -0.001 | -0.004 | -0.003 |
| recall@5 % 95 % CI | 0.941–0.974 | 0.904–0.974 | |

### `B1:sharp_abs_max`

| metric | development | validation | validation − development |
|---|---|---|---|
| recall@5% | 0.709 | 0.695 | -0.014 |
| recall@1% | 0.465 | 0.353 | -0.112 |
| recall@2% | 0.527 | 0.515 | -0.012 |
| recall@10% | 0.803 | 0.861 | 0.057 |
| recall@20% | 0.900 | 0.929 | 0.029 |
| recall@K10 | 0.709 | 0.688 | -0.021 |
| recall@K25 | 0.841 | 0.881 | 0.040 |
| recall@K50 | 0.905 | 0.963 | 0.057 |
| AUC | 0.930 | 0.939 | 0.009 |
| faint guard difference | -0.423 | -0.449 | -0.027 |
| MARGINAL recall@5% | 0.443 | 0.406 | -0.037 |
| PRIMARY recall@5% | 0.866 | 0.855 | -0.010 |
| zone+outer vs control difference | -0.078 | -0.026 | 0.051 |
| recall@5 % 95 % CI | 0.628–0.773 | 0.605–0.766 | |

### `B0`

| metric | development | validation | validation − development |
|---|---|---|---|
| recall@5% | 0.055 | 0.032 | -0.023 |
| recall@1% | 0.017 | 0.004 | -0.014 |
| recall@2% | 0.025 | 0.009 | -0.016 |
| recall@10% | 0.095 | 0.076 | -0.018 |
| recall@20% | 0.201 | 0.175 | -0.027 |
| recall@K10 | 0.147 | 0.045 | -0.102 |
| recall@K25 | 0.323 | 0.195 | -0.128 |
| recall@K50 | 0.475 | 0.400 | -0.075 |
| AUC | 0.510 | 0.467 | -0.043 |
| faint guard difference | -0.012 | -0.017 | -0.004 |
| MARGINAL recall@5% | 0.047 | 0.021 | -0.026 |
| PRIMARY recall@5% | 0.059 | 0.038 | -0.022 |
| zone+outer vs control difference | -0.049 | 0.015 | 0.064 |
| recall@5 % 95 % CI | 0.033–0.086 | 0.014–0.050 | |

## Counterexamples and failure cases (M1)

- Quadrant-nights (≥ 3 positives) with AUC < 0.5: none
- Strata with recall@5 % more than 0.20 below overall: mask_state=partial (0.67, n 6)
- Positives in the bottom half (q > 0.5): 0
- Missed (q > 0.05) by stratum: role: marginal 13, primary 4; proximity_group: control 10, intermediate 4, zone 3; star_class: 6-8 3, 8-10 12, V<6 2; depth_margin: 0.5-1.5 3, <0.5 14; mask_state: all 2, partial 2, unmasked 13; crowding: 20-80k 1, <20k 13, >=80k 3; speed: 0.25-0.5 3, 0.5-1.0 12, <0.25 2

### Every validation positive outside the M1 top 5 % (17)

| field | object | w | q | comparator q | role | group | star | depth | mask | crowding | p `min_snr` | p `median_snr` | p `fit_rms_residual_arcsec` | p `magnitude_range_mag` | p `flagged_detection_count` | p `masked_detection_count` | p `sharp_abs_max` | p `shared_detection_tracklets` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C27 | 267663 | 1 | 0.486 | 0.556 | marginal | control | 8-10 | <0.5 | unmasked | <20k | 0.03 | 0.02 | 0.40 | 0.56 | 0.77 | 0.77 | 0.38 | 0.76 |
| C1 | 31302 | 1 | 0.223 | 0.420 | primary | zone | 6-8 | 0.5-1.5 | partial | >=80k | 0.88 | 0.72 | 0.93 | 0.87 | 0.23 | 0.21 | 0.58 | 0.26 |
| C30 | 533784 | 1 | 0.208 | 0.002 | marginal | control | 6-8 | <0.5 | unmasked | <20k | 0.01 | 0.00 | 0.97 | 0.11 | 0.99 | 0.56 | 1.00 | 0.99 |
| C6 | 197971 | 1 | 0.175 | 0.836 | primary | intermediate | 8-10 | 0.5-1.5 | unmasked | >=80k | 0.80 | 0.43 | 0.98 | 0.73 | 0.56 | 0.55 | 0.16 | 0.57 |
| C27 | 148050 | 1 | 0.167 | 0.361 | marginal | control | 8-10 | <0.5 | unmasked | <20k | 0.19 | 0.38 | 0.42 | 0.62 | 0.77 | 0.77 | 0.56 | 0.76 |
| C30 | 2016 JU15 | 1 | 0.152 | 0.007 | marginal | intermediate | 8-10 | <0.5 | unmasked | <20k | 0.01 | 0.01 | 0.99 | 0.26 | 0.99 | 0.56 | 0.98 | 0.99 |
| C29 | 450990 | 1 | 0.134 | 0.155 | marginal | intermediate | 8-10 | <0.5 | unmasked | <20k | 0.10 | 0.39 | 0.56 | 0.38 | 0.72 | 0.60 | 0.69 | 0.67 |
| C30 | 2025 HJ43 | 1 | 0.108 | 0.008 | marginal | control | 8-10 | <0.5 | unmasked | <20k | 0.01 | 0.01 | 0.83 | 0.58 | 0.99 | 0.56 | 0.98 | 0.99 |
| C17 | 176965 | 1 | 0.103 | 0.103 | marginal | intermediate | V<6 | <0.5 | all | <20k | 0.06 | 0.59 | 0.62 | 0.77 | 0.43 | 0.43 | 0.80 | 0.87 |
| C29 | 470924 | 1 | 0.099 | 0.155 | marginal | control | 8-10 | <0.5 | unmasked | <20k | 0.45 | 0.53 | 0.29 | 0.36 | 0.72 | 0.60 | 0.70 | 0.67 |
| C11 | 373647 | 1 | 0.094 | 0.125 | marginal | control | 8-10 | <0.5 | unmasked | <20k | 0.15 | 0.05 | 0.74 | 0.64 | 0.87 | 0.87 | 0.78 | 0.86 |
| C29 | 520875 | 0.5 | 0.085 | 0.493 | marginal | control | 8-10 | <0.5 | unmasked | <20k | 0.36 | 0.62 | 0.40 | 0.66 | 0.72 | 0.60 | 0.36 | 0.67 |
| C22 | 682258 | 1 | 0.078 | 0.418 | marginal | control | 8-10 | <0.5 | unmasked | <20k | 0.15 | 0.30 | 0.78 | 0.63 | 0.86 | 0.86 | 0.56 | 0.83 |
| C24 | 146081 | 1 | 0.072 | 0.188 | primary | zone | 6-8 | 0.5-1.5 | unmasked | >=80k | 0.84 | 0.93 | 0.80 | 0.38 | 0.57 | 0.55 | 0.74 | 0.05 |
| C8 | 71563 | 1 | 0.068 | 0.076 | marginal | control | 8-10 | <0.5 | partial | 20-80k | 0.43 | 0.39 | 0.86 | 0.92 | 0.41 | 0.41 | 0.90 | 0.84 |
| C11 | 82840 | 1 | 0.062 | 0.146 | primary | zone | V<6 | <0.5 | all | <20k | 0.84 | 0.68 | 0.83 | 0.76 | 0.35 | 0.35 | 0.75 | 0.61 |
| C29 | 792421 | 1 | 0.056 | 0.366 | marginal | control | 8-10 | <0.5 | unmasked | <20k | 0.30 | 0.29 | 0.86 | 0.69 | 0.72 | 0.60 | 0.53 | 0.67 |

## Evidence strips (agent labels, not ground truth)

Shortlist background (M1 top 5 % of each quadrant-night's background): 525 tracklets.

| strip | field | tracklet | q | label | notes |
|---|---|---|---|---|---|
| missed_positive 682258 | C22 | trk-0220 | 0.078 | real, faint | MARGINAL. E1/E2 faint point source, E3 at the noise level. Near-limit object. Agent label. |
| missed_positive 2016 JU15 | C30 | trk-16458 | 0.152 | real, faint | MARGINAL. Faint in all three epochs, clean sky. Low SNR (p 0.01) outweighs its excellent fit and sharp (p 0.99/0.98). Agent label. |
| missed_positive 31302 | C1 | trk-1628 | 0.223 | real, near star | Zone PRIMARY. Moving point source on the halo/spike edge of a bright star, crowded field. Flagged/masked/shared at p 0.21-0.26 demote it. Star-proxy effect of the mask features. Agent label. |
| missed_positive 533784 | C30 | trk-0128 | 0.208 | real, faint | MARGINAL. Faint point source in all epochs, clean sky. SNR p 0.00-0.01. Agent label. |
| missed_positive 148050 | C27 | trk-0083 | 0.167 | real, faint | MARGINAL. E1 at noise level, E2 faint, E3 visible. Agent label. |
| missed_positive 520875 | C29 | trk-1448 | 0.085 | real, faint (blend E1) | MARGINAL. E1 position touches a bright field star (blend), E2/E3 at noise level. Agent label. |
| missed_positive 176965 | C17 | trk-0029 | 0.103 | real, faint | MARGINAL, all-masked. Faint in E1/E2, marginal in E3. Agent label. |
| missed_positive 267663 | C27 | trk-0053 | 0.486 | real, very faint | MARGINAL. Not visibly above noise in E1/E2; faint compact source in E3. Lowest validation miss (q 0.49). Agent label. |
| missed_positive 470924 | C29 | trk-1470 | 0.099 | real, faint (blend E3) | MARGINAL. E1 noise level, E2 faint, E3 next to a brighter star. Agent label. |
| missed_positive 450990 | C29 | trk-1319 | 0.134 | real, faint | MARGINAL. Near noise level in all epochs. Agent label. |
| missed_positive 146081 | C24 | trk-0479 | 0.072 | real, near star | Zone PRIMARY in the scattered-light gradient of a bright star; E2 blended with a brighter source; shares detections with many tracklets (p 0.05). Agent label. |
| missed_positive 197971 | C6 | trk-1059 | 0.175 | unclear, crowding | PRIMARY in a dense Milky Way field; positions sit among blended stars, mover not separable by eye. |sharp| high (p 0.16): blend. Agent label. |
| shortlist_background trk-1074 | C2 | trk-1074 | 0.027 | artefact (star halo) | Inside a broad diffuse halo band; no point source at any epoch. Agent label. |
| shortlist_background trk-4879 | C25 | trk-4879 | 0.003 | mislink (crowding) | Dense Milky Way field; three different stationary stars linked. Agent label. |
| shortlist_background trk-3604 | C2 | trk-3604 | 0.012 | artefact (star halo) | Detections on the halo of a bright extended source. Agent label. |
| shortlist_background trk-2651 | C28 | trk-2651 | 0.004 | artefact (edge glow) | Along the bright lower-edge scattered-light gradient. Agent label. |
| shortlist_background trk-13519 | C30 | trk-13519 | 0.043 | artefact (edge glow) | On the bright upper-edge scattered-light gradient. Agent label. |
| shortlist_background trk-1742 | C21 | trk-1742 | 0.045 | artefact (star halo/spikes) | Around a saturated star with diffraction spikes and halo. Agent label. |
| shortlist_background trk-0490 | C16 | trk-0490 | 0.007 | artefact (bleed column) | Along a saturation bleed column. Agent label. |
| shortlist_background trk-0558 | C2 | trk-0558 | 0.016 | artefact (star halo) | Diffuse halo / scattered-light structure, no source. Agent label. |
| shortlist_background trk-0365 | C26 | trk-0365 | 0.047 | artefact (bleed column) | Beside the bleed column of a saturated star. Agent label. |
| shortlist_background trk-2331 | C25 | trk-2331 | 0.040 | mislink (crowding) | Dense Milky Way field; stationary stars linked. Agent label. |
| shortlist_background trk-0853 | C16 | trk-0853 | 0.050 | artefact (star halo/ghost) | Halo edge / ghost of a bright star with a diagonal streak. Agent label. |
| shortlist_background trk-1223 | C30 | trk-1223 | 0.038 | artefact (edge glow) | On the upper-edge scattered-light gradient. Agent label. |
| shortlist_background trk-2503 | C28 | trk-2503 | 0.011 | artefact (edge glow) | Along the lower-edge scattered-light gradient. Agent label. |
| shortlist_background trk-0418 | C10 | trk-0418 | 0.043 | artefact (bleed column) | Along a saturation bleed trail of a bright star. Agent label. |
| shortlist_background trk-14025 | C30 | trk-14025 | 0.025 | artefact (edge glow) | On the upper-edge scattered-light gradient. Agent label. |
| shortlist_background trk-1178 | C2 | trk-1178 | 0.008 | artefact (bleed column) | Along a saturation bleed column. Agent label. |
| shortlist_background trk-0554 | C24 | trk-0554 | 0.036 | artefact (star wing) | On the PSF wing of a saturated star. Agent label. |
| shortlist_background trk-0169 | C26 | trk-0169 | 0.009 | artefact (star halo) | Around a saturated star with bleed. Agent label. |
| shortlist_background trk-0478 | C15 | trk-0478 | 0.019 | artefact (star wing) | On the wings of a saturated star. Agent label. |
| shortlist_background trk-0195 | C6 | trk-0195 | 0.004 | mislink (crowding) | Dense Milky Way field; stationary stars linked. Agent label. |
