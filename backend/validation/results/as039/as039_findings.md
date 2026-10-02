# AS-039 findings — candidate ranker construction (stage 2, development only)

Generated evidence:

- `as039_construction.md` / `.json`: every ranker, metric, guard,
  stratum, per-quadrant-night value, fold model, sensitivity and
  counterexample;
- `as039_selection.json`: the mechanical selection;
- `as039_frozen_ranker.json`: the ranker and comparator frozen for AS-040.

Regenerate (offline, about 5 s, bit-identical apart from `generated_at`):

```
python -m app.validation.ranker_construction evaluate --out-dir validation/results/as039
```

Protocol: AS-037 stage 2, unchanged (commit `abb97c0`), on the AS-038
development table and frozen list (commit `24745a1`). Details AS-037
leaves open were fixed as implementation decisions E1–E12 in
`app/validation/ranker_construction.py`, committed in `9c358ab` before
any ranker score existed.

**Solver fix.** The first run of `9c358ab` stopped inside M2(C=1) with
"did not converge". It wrote nothing, and nothing was read. The
backtracking line search rejected Newton steps whose objective change was
below float rounding.

- `f041720` takes the full Newton step once the Newton decrement is
  < 1e-12. It changes no rule, tolerance or recipe. The problem is
  strictly convex, so the optimum is unique.
- A regression test fits every fold's training set. It fails on
  `9c358ab` and passes on `f041720`.
- All results come from `f041720`.

Nothing was changed after the outcome.

Safeguards held throughout:

- No validation quadrant-night was loaded. `require_split(...,
  "ranking_construction")` runs on every development quadrant-night, and
  validation rows were already absent from the AS-038 table.
- Ranker inputs were only the 8 frozen features, as label-free
  within-quadrant-night percentiles.
- Identification, designation, SkyBoT, bright-star proximity, speed and PA
  were evaluation or stratification only.
- UNKNOWN is background, not a ground-truth false positive.
- No filter, threshold or rejection rule was built. The optional
  proximity-including exploratory variant was not run (E9).

## Data

- 56 development quadrant-nights in 27 independence groups.
- 18 366 ranked tracklets: 402 positive, 40 auxiliary, 17 924 background.
- 402 positive object-nights in 49 quadrant-nights:
  - 253 PRIMARY, 149 MARGINAL;
  - zone 6, outer 48, intermediate 125, control 223.
- Grouped 5-fold CV. Groups were assigned in SHA-256('AS-037:<group>')
  order, round-robin:

  | fold | groups | positive object-nights |
  |---|---|---|
  | 0 | 6 | 133 |
  | 1 | 6 | 49 |
  | 2 | 5 | 144 |
  | 3 | 5 | 62 |
  | 4 | 5 | 14 |

## All rankers (pooled out-of-fold, 95 % group bootstrap, 2000)

Guards: recall@5 % of the protected stratum minus the reference
stratum. A guard passes if the difference is ≥ −0.20. Newcombe intervals
are in the generated report.

- **Faint guard**: MARGINAL (n 149) vs PRIMARY (n 253).
- **Near-star guard**: zone+outer (n 54) vs control (n 223).

| ranker | recall@5 % [95 %] | AUC [95 %] | faint guard | near-star guard | selectable / eligible |
|---|---|---|---|---|---|
| B0 hash | 0.055 [0.033, 0.086] | 0.510 [0.483, 0.545] | −0.01 pass | −0.05 pass | null, no |
| B1 `min_snr` | 0.512 [0.429, 0.618] | 0.827 [0.790, 0.878] | **−0.57 FAIL** | +0.07 pass | comparator pool |
| B1 `median_snr` | 0.517 [0.423, 0.635] | 0.820 [0.779, 0.871] | **−0.52 FAIL** | −0.08 pass | comparator pool |
| B1 `fit_rms_residual_arcsec` | 0.525 [0.424, 0.615] | 0.897 [0.873, 0.918] | **−0.35 FAIL** | −0.09 pass | comparator pool |
| B1 `magnitude_range_mag` | 0.209 [0.085, 0.374] | 0.800 [0.751, 0.853] | +0.01 pass | +0.14 pass | comparator pool |
| B1 `flagged_detection_count` | 0.331 [0.161, 0.517] | 0.817 [0.761, 0.860] | +0.08 pass | **−0.25 FAIL** | comparator pool |
| B1 `masked_detection_count` | 0.276 [0.142, 0.419] | 0.780 [0.719, 0.827] | +0.05 pass | **−0.21 FAIL** | comparator pool |
| B1 `sharp_abs_max` | **0.709** [0.628, 0.773] | 0.930 [0.896, 0.952] | **−0.42 FAIL** | −0.08 pass | **comparator** |
| B1 `shared_detection_tracklets` | 0.192 [0.051, 0.359] | 0.805 [0.746, 0.857] | +0.09 pass | −0.13 pass | comparator pool |
| **M1** mean percentile | **0.955 [0.941, 0.974]** | 0.990 [0.984, 0.995] | −0.12 pass (0.88 vs 1.00) | −0.00 pass (0.96 vs 0.96) | **eligible, selected** |
| M2 C = 0.01 | 0.933 [0.910, 0.966] | 0.987 [0.981, 0.992] | −0.18 pass | +0.00 pass | eligible |
| M2 C = 0.1 | 0.933 [0.909, 0.967] | 0.987 [0.980, 0.993] | −0.18 pass | +0.00 pass | eligible |
| M2 C = 1 | 0.938 [0.914, 0.969] | 0.988 [0.981, 0.993] | −0.17 pass | +0.02 pass | eligible |
| M2 C = 10 | 0.948 [0.929, 0.972] | 0.989 [0.983, 0.994] | −0.14 pass | +0.00 pass | eligible |

The B1 rankers have no guard condition. AS-037 makes the best B1 the
comparator; it is never a selectable ranker. Their B1 values match AS-038
to 3 decimals (B1 has no parameter, so CV equals in-sample). The CIs
differ slightly because the bootstrap labels differ.

### Secondary metrics

| ranker | recall@1/2/10/20 % | recall@K 10/25/50 | enrichment@1/5 % | median q |
|---|---|---|---|---|
| M1 | 0.88 / 0.92 / 0.98 / 0.99 | 0.95 / 0.98 / 0.99 | 87.8× / 19.1× | 0.000 |
| M2 C = 10 | 0.88 / 0.92 / 0.97 / 0.99 | 0.96 / 0.98 / 0.99 | 87.6× / 19.0× | 0.000 |
| M2 C = 1 | 0.86 / 0.90 / 0.97 / 0.99 | 0.95 / 0.97 / 0.99 | 86.3× / 18.8× | 0.000 |
| M2 C = 0.01 / 0.1 | 0.86 / 0.90 / 0.97 / 0.99 | 0.94 / 0.97 / 0.99 | 85.8× / 18.7× | 0.000 |
| B1 `sharp_abs_max` | 0.47 / 0.53 / 0.80 / 0.90 | 0.71 / 0.84 / 0.91 | 46.5× / 14.2× | 0.015 |
| B0 | 0.02 / 0.02 / 0.09 / 0.20 | 0.15 / 0.32 / 0.48 | 1.7× / 1.1× | 0.501 |

- **M1 recall@5 % per fold**: 0.93 / 0.96 / 0.96 / 0.98 / 1.00.
- **Paired difference** (descriptive, group bootstrap):
  - M1 − `sharp_abs_max` = +0.246 [0.183, 0.332];
  - M1 − B0 = +0.900 [0.870, 0.929].
- On the AS-037 decision-rule thresholds, all five M1/M2 rankers reach
  the useful level on development (≥ 0.50, lower bound ≥ 0.30). This is
  descriptive; it is not a selection condition and not a validation
  claim.

## Selection (AS-037 rule, applied mechanically)

1. **Eligible**: M1/M2 candidates whose faint and near-star guards both
   pass. All five are eligible: M1, M2(0.01), M2(0.1), M2(1) and M2(10).
   None was excluded.
2. **Best by CV recall@5 %**: M1, 0.955. The best M2 is C = 10 at 0.948.
   The 0.02 tie rule was not needed (`tie_rule_applied: false`).
3. **Comparator**: the best B1 by CV recall@5 %, `sharp_abs_max` (0.709).

**Outcome: ADVANCE. Frozen ranker M1, comparator B1 `sharp_abs_max`.**

The headline numbers did not decide this:

- The single features with the highest recall, `sharp_abs_max` (0.71)
  and the SNR/fit features (0.51–0.53), would all fail the faint guard
  (−0.35 to −0.57).
- `flagged` and `masked` would fail the near-star guard (−0.25, −0.21).
- None of them was selectable anyway (B1).
- Among the selectable rankers, the guards excluded none.

## Frozen for AS-040 (`as039_frozen_ranker.json`, code `f041720`)

- **Ranker M1**, with no fitted parameter. For each built tracklet of a
  quadrant-night:

  `score = (1/8) · Σ_k p_k`

  - p_k = `ranking_design.within_field_percentile(values_k, direction_k)`
    over all built tracklets of that quadrant-night (mid-rank, label-free,
    higher = reviewed earlier).
  - A missing value has p = 0.
  - Inputs and directions:
    - `min_snr` (+);
    - `median_snr` (+);
    - `fit_rms_residual_arcsec` (−);
    - `magnitude_range_mag` (−);
    - `flagged_detection_count` (−);
    - `masked_detection_count` (−);
    - `sharp_abs_max` (−);
    - `shared_detection_tracklets` (−).
  - Weights 0.125 each, intercept 0.
- **Comparator B1 `sharp_abs_max`**: score = p(`sharp_abs_max`, −).
- **Metric rule**: q = `background_rank_fraction` (ties count half), using
  the best-scored positive per object and object-night weights.
- **Bound to inputs**: manifest `63e12b9f…`, AS-038 table `da670e38…`,
  frozen list `a8182bc6…`.
- **Not allowed in AS-040**: any other feature, transform, weight or C;
  proximity, speed, PA or identity as input; re-selection or tuning.

## Guards, faint and near-star behaviour

- **Faint**: M1 ranks every PRIMARY in its top 5 % (253/253) and 0.88 of
  MARGINAL (131/149). The difference is −0.12, Newcombe [−0.18, −0.08].
  It passes the 0.20 margin, but the interval excludes 0: **a real faint
  penalty remains**.
  - All 18 positives M1 misses at 5 % are MARGINAL with a depth margin
    < 0.5 mag.
  - This is the AS-038 O1 brightness confound, diluted but not removed.
  - The M2 rankers are worse on this guard (−0.14 to −0.18).
- **Near-star**: zone+outer is 0.963 (52/54) vs control 0.964, a
  difference of −0.00, Newcombe [−0.09, +0.04].
  - Descriptive views:
    - zone+outer vs intermediate+control: +0.01;
    - zone only: 6/6 (n < 10, not evaluable).
  - The AS-038 O2 mask penalty does not carry over to M1. Of the 16
    positives masked on every detection, M1 ranks 14 in the top 5 %;
    `flagged` alone ranks 0 of 16 there.
  - Averaging dilutes the proxy, but `flagged` and `masked` still carry
    2/8 of the weight. Proximity was not used to achieve this.
- **On validation** (AS-040), the guards switch to zone vs control (≥ 10
  zone) and MARGINAL vs PRIMARY (≥ 30) per AS-037 §7. The −0.12 faint
  gap leaves 0.08 of headroom.

## Counterexamples and failure modes (reported, not acted on)

C1. **The 18 M1 misses** are all MARGINAL with depth < 0.5:

- 99800 in S2-q2: q 1.00 (sparse field, 3 background);
- 644121 in N19: q 0.33 (all-masked);
- 299501 in N7: q 0.33;
- 190665 in N6: q 0.22;
- 109539 in S1-q2: q 0.17;
- 717690 in N15: q 0.15 (all-masked);
- 615848 in N4: q 0.12;
- 204282 in B-q1: q 0.11;
- 225013 in N15: q 0.11;
- 122386 in S4-q3: q 0.09;
- 242307 in N22: q 0.08;
- 565559 in N7: q 0.08;
- 144741 in B-q3: q 0.07;
- 162387 and 203318 in B-q2: q 0.06 each;
- 461220 in N13: q 0.06;
- 130420 in S4-q2: q 0.055;
- 329908 in D-q2: q 0.053.

By proximity group: 8 control, 8 intermediate, 2 outer. Eight of the 18
are within 0.04 of the cut.

C2. **Sparse fields quantise q.** S2-q2 has 3 background tracklets, so a
positive is in the top 5 % only if it outranks all of them. 99800 (SNR
3.9, fit RMS 0.24″, |sharp| 0.32) loses to all three. They have fit RMS
0.14–0.15″ and |sharp| 0.20–0.22, and two of them have higher SNR.
Low-background fields make recall@5 % an all-or-nothing test.

C3. **Comparator vs M1.**

- Top 5 % by M1 only: 102 positives.
- Top 5 % by `sharp_abs_max` only: 3 positives, all MARGINAL (615848 N4,
  225013 and 717690 N15).

So for a few faint objects, sharp alone ranks better than the average.

C4. **No quadrant-night with ≥ 3 positives has M1 AUC < 0.5.** The
lowest recall@5 % fields are:

- S4-q2: 0.67 (n 3, 1118 background);
- S2-q2: 0.75 (n 4, 3 background);
- D-q2: 0.80 (n 5, 620 background).

The other quadrant-nights with > 500 background are 0.89–1.00. These are
D-q1/q3/q4, S4-q3 (3483 background) and the N/C fields.

C5. **Why the average wins** (descriptive):

- 341 of 402 positives are in the bottom quartile of no feature, and 0
  are in the bottom quartile of more than 3.
- Most background tracklets (14 394 of 17 924) are in the bottom quartile
  of at least one feature.
- The background that M1 puts in its top 5 % is median 0.53–0.55 on
  `flagged` / `masked`, and 0.76–0.85 on SNR / fit / sharp.

The average rewards "no weak spot". That is also why an UNKNOWN real
object that is faint, or close to a star, can still lose (C1).

C6. **Sensitivity**: dropping background that shares a detection with a
positive, or dropping 105890, changes M1 recall@5 % by < 0.001.

## Known AS-038 risks, carried forward explicitly

- **SNR / sharp faint disadvantage (O1)**: present in M1 as a −0.12 faint
  gap with an interval excluding 0. 4/8 of M1's weight sits on SNR, sharp
  and fit features. Not tuned away.
- **Mask / flag near-star disadvantage (O2)**: about −0.25 / −0.21 in the
  single features, diluted to −0.00 in M1 on development. Development
  has only 6 zone positives. The real test is the AS-040 zone guard (14
  validation zone positives).
- **Fit-residual leakage (O7)**: `fit_rms_residual_arcsec` is 1/8 of M1.
  Positives had to be identified within 2″ of SkyBoT, so part of its
  contribution may restate selection. This is not corrected, and it
  makes the development numbers optimistic.
- **API availability of `sharp` (O6)**: both the frozen ranker (1/8
  weight) and the comparator need `sharp_abs_max`. `sharp` is not in the
  API's `SourceDetection`, so M1 runs only in the research path until a
  mapping change. AS-040 runs in the research path (as AS-038 did), so
  this does not block validation. It is a deployment limitation, not a
  selection criterion.

## Limitations

- **Optimistic.** CV protects only the M2 weights. The 8 features were
  gated on these same 56 quadrant-nights (AS-038), and R was inspected in
  AS-031–034. M1 has no parameter, so its "CV" number is an in-sample
  application of a feature list chosen on the same data. Only AS-040
  measures it.
- Fold 4 holds 14 positives, so per-fold values are noisy (descriptive).
- The background is a mixture. A high recall@5 % means known objects
  outrank most UNKNOWN tracklets; it does not mean the top 5 % is free
  of artefacts, or that real unknown objects rank as well as known ones.
- Positives are main-belt dominated, ≤ 1″/min, baseline ≥ 3″.

## Handoff to AS-040 (not started)

- Apply `as039_frozen_ranker.json` (M1 + comparator `sharp_abs_max`)
  once to the 24 validation quadrant-nights. Build their feature table
  with the AS-038 pipeline under `require_split(..., "validation")`.
- Use `ranking_design.decide()` with the AS-037 §7 guards (zone vs
  control, MARGINAL vs PRIMARY), the comparator paired difference and
  the failure analysis.
- No tuning and no re-selection.
