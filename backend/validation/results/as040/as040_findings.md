# AS-040 findings — sealed validation of the frozen candidate ranker (stage 3)

Generated evidence:

- `as040_frozen_check.json`: the 25 frozen-input checks, run and committed
  before any validation quadrant-night was opened (`ca2d1d9`);
- `as040_feature_table.csv.gz`, `as040_fields.json`: the validation table
  (24 quadrant-nights, built once);
- `as040_validation.md` / `.json`: verdict, every metric, guard, stratum,
  per-quadrant-night value, comparator analysis, end-to-end, sensitivity,
  failure list, development-vs-validation comparison;
- `strips/` + `visual_review.json`: the 32 pre-registered evidence strips
  with agent labels (not ground truth).

Regenerate (offline, about 10 s, bit-identical apart from timestamps and
code commit):

```
python -m app.validation.sealed_validation evaluate
```

## Protocol and sealing

AS-037 stage 3, unchanged (`abb97c0`). The AS-039 frozen ranker and
comparator (`0b2de88`) were applied as they are. Details AS-037 leaves
open were fixed as implementation decisions V1–V14 in
`app/validation/sealed_validation.py`. They were committed in `ca2d1d9`
while `.cache/as040` was empty, so no validation feature, score or
outcome existed yet.

**Order of events:**

1. **Frozen inputs verified (V1)**, all 25 checks passed:
   - manifest `63e12b9f…`, AS-038 table `da670e38…`, AS-038 list
     `a8182bc6…`, AS-039 frozen ranker `875a0647…`;
   - the ranker records the same three hashes and comes from clean commit
     `f041720`;
   - the manifest rebuilds identically and all 7 of its inputs are
     unchanged;
   - validation digest `a549b6bc…`, 24 quadrant-nights, 22 groups, no
     group spans both splits;
   - the ranker is exactly M1 (8 features in AS-037 directions, 0.125
     each, intercept 0, not fitted);
   - the comparator is exactly B1 `sharp_abs_max` (−);
   - missing percentile is 0.
2. **Runner committed (`ca2d1d9`).** It includes a test showing that the
   new scorer reproduces the committed AS-039 development M1 (0.955) and
   comparator recall@5 % / AUC exactly.
3. **Validation table built once.**
   - Unchanged AS-038 pipeline, SkyBoT replayed.
   - Every quadrant-night passed `require_split(..., "validation")`.
   - Labels reconcile with the AS-036 recovery traces: 283/283
     (field, object) pairs, none missing either way.
4. **`evaluate` run once.** Verdict: USEFUL, PROTECTED.
5. **Strips rendered and labelled.**
   - One display-only fix after the outcome (`d012f52`): strip file names
     had a doubled `t` prefix. No number depends on it.
   - The rerun is identical apart from timestamps and commit.

**Nothing was changed after the outcome:** no feature, weight, transform,
ranker, threshold, guard, metric, label, stratum or missing-value rule.
Nothing was fitted, selected or retrained.

**Safeguards held throughout:**

- UNKNOWN is background, not a ground-truth false positive.
- Identity, SkyBoT and designation were labels only.
- Bright-star proximity, speed and PA were strata only.

## Validation population

- 24 quadrant-nights (all AS-036 C) in 22 independence groups.
  - C10/C11 and C29/C30 share groups.
  - Mean sources per frame range from 5 k to 183 k.
- 10 817 ranked (built) tracklets:
  - 10 511 background;
  - 284 positive tracklets;
  - 22 auxiliary.
- **269 positive object-nights in 24 quadrant-nights.**
  - C29/C30 copies are merged with weight ½ each; the best-scored
    tracklet per object counts.
  - By role: 173 PRIMARY, 96 MARGINAL.
  - By proximity group: zone 14, outer 30, intermediate 76, control 149.
  - Every zone positive is PRIMARY.
- Every AS-037 minimum is met: ≥ 100 object-nights, ≥ 15 quadrant-nights,
  ≥ 10 zone, ≥ 30 MARGINAL.

## Confirmatory verdict (`ranking_design.decide`, AS-037 §7, mechanical)

| step | rule | value | result |
|---|---|---|---|
| 1 minimums | ≥ 100 object-nights, ≥ 15 quadrant-nights | 269, 24 | met |
| 2 NOT USEFUL? | upper bound < 0.50 | upper 0.975 | no |
| 3 USEFUL level | recall@5 % ≥ 0.50 and lower ≥ 0.30 | **0.939 [0.902, 0.975]** | yes |
| near-star guard | zone ≥ control − 0.20 (zone ≥ 10) | 0.786 vs 0.940 = **−0.154** (n 14 / 149) | evaluable, **pass** |
| faint guard | MARGINAL ≥ PRIMARY − 0.20 (MARGINAL ≥ 30) | 0.870 vs 0.977 = **−0.107** (n 96 / 173) | evaluable, **pass** |

**Verdict: USEFUL, PROTECTED.** Both guards are evaluable and pass, so the
verdict follows mechanically. This headline is close to its limits on one
guard. The caveats under "Guards" are reported; they do not change the
verdict.

The deciding interval uses bootstrap label `AS-040/M1/recall5`. The
secondary table uses `AS-040/M1/recall@0.05`, which gives
[0.904, 0.974]. Both were fixed in V5/V6 before the outcome.

## M1 primary and secondary metrics (95 % group bootstrap, 2000)

| metric | M1 | comparator B1 `sharp_abs_max` | B0 hash (null) |
|---|---|---|---|
| **recall@5 %** | **0.939 [0.904, 0.974]** | 0.695 [0.605, 0.766] | 0.032 [0.014, 0.050] |
| recall@1 % | 0.881 [0.846, 0.923] | 0.353 [0.190, 0.513] | 0.004 |
| recall@2 % | 0.913 [0.881, 0.947] | 0.515 [0.365, 0.639] | 0.009 |
| recall@10 % | 0.967 [0.939, 0.992] | 0.861 [0.817, 0.904] | 0.076 |
| recall@20 % | 0.989 [0.974, 1.000] | 0.929 [0.890, 0.959] | 0.175 |
| recall@K 10 | 0.952 [0.919, 0.984] | 0.688 [0.583, 0.829] | 0.045 |
| recall@K 25 | 0.981 [0.960, 1.000] | 0.881 [0.828, 0.936] | 0.195 |
| recall@K 50 | 0.981 [0.959, 1.000] | 0.963 [0.925, 0.987] | 0.400 |
| enrichment @1 / 2 / 5 / 10 / 20 % | 88.1 / 45.6 / 18.8 / 9.7 / 4.9× | 35.3 / 25.7 / 13.9 / 8.6 / 4.6× | ≈ 1× |
| within-field AUC | 0.990 [0.982, 0.995] | 0.939 [0.921, 0.951] | 0.467 |
| median q | 0.000 [0.000, 0.000] | 0.019 [0.009, 0.029] | 0.542 |

- No validation positive lies in the bottom half (q > 0.5). The worst is
  q 0.486.
- No quadrant-night with ≥ 3 positives has AUC < 0.5.
- **Per quadrant-night M1 recall@5 %:**
  - 1.00 in 15 of 24 quadrant-nights;
  - lowest: C6 0.00 (a single positive), C1 0.67 (n 3), C27 0.75 (n 8),
    C29 0.81, C11 / C24 0.86.
- **Sensitivity**: dropping background that shares a detection with a
  positive leaves 0.939; dropping 105890 gives 0.938.

## Comparator analysis (secondary, never deciding)

- **Paired recall@5 %, M1 − `sharp_abs_max`**: **+0.243 [0.160, 0.339]**.
  M1 − B0 is +0.907 [0.866, 0.944].
- **Top 5 % by M1 only**: 71 positives.
- **Top 5 % by the comparator only**: 3 positives, all MARGINAL in C30
  (533784, 2016 JU15, 2025 HJ43).
  - Comparator q is 0.002–0.008; M1 q is 0.11–0.21.
  - Their SNR percentiles are ≈ 0.01 in a 3545-background field. The two
    SNR features (2/8 of M1's weight) outweigh their near-perfect sharp
    and fit.
- **Comparator guards** (descriptive): the faint guard **fails** at −0.45
  (0.41 vs 0.86); the zone guard passes (+0.01). Run through `decide()`,
  the comparator would be "USEFUL, NOT PROTECTED". That is not a verdict;
  it shows that the faint guard does real work.

## Guards (deciding) and the honest caveats

**Faint guard: MARGINAL 0.870 vs PRIMARY 0.977, −0.107.** Newcombe
interval [−0.18, −0.04].

- It passes with 0.09 of headroom, but the interval excludes 0: **a real
  faint penalty remains**.
- It matches development (−0.121). This is the AS-038 O1 SNR / sharp /
  fit brightness confound, diluted by averaging but not removed.
- Within control alone, MARGINAL vs PRIMARY is −0.17 (descriptive).

**Near-star guard: zone 0.786 (11/14) vs control 0.940, −0.154.**
Newcombe interval [−0.42, −0.01].

- It passes with 0.046 of headroom on 14 object-nights. One more zone
  miss would make it 10/14 = 0.714, a difference of −0.226: **FAIL**.
- The interval excludes 0: **a near-star penalty in the ranking itself is
  likely**, on top of the confirmed AS-036 recovery penalty.
- Descriptive views (not deciding):
  - zone PRIMARY vs control PRIMARY: 0.79 vs 1.00 = −0.21 (this one
    would fail);
  - zone + outer vs control, the AS-039 definition: −0.00;
  - outer alone: 30/30.
- So the penalty is concentrated in the zone itself.
- All 3 zone misses are PRIMARY:
  - C1 31302: halo edge, crowded field;
  - C24 146081: scattered-light gradient, blended;
  - C11 82840: V < 6 star, all-masked.
- Their flagged, masked and/or shared-detection percentiles are low
  (0.05–0.35). This is exactly the AS-038 O2 risk: **mask/flag features
  acting as an implicit proximity proxy**.
- **End-to-end** (secondary, eligible targets recovered *and* in the top
  5 %):
  - zone 0.40 (10.5 / 26), control 0.48 (137.5 / 285), all 0.48 (249 /
    514);
  - PRIMARY 0.72, MARGINAL 0.29.
  - The AS-036 recovery penalty and the ranking penalty compound.

**Reading.** The pre-registered rule says PROTECTED, and that is the
verdict. The evidence behind "protected" is thin for the zone: n = 14,
the margin is one object, and both guard intervals exclude zero. Any
deployment should treat zone and faint objects as at risk, not as safe.

## Development (AS-039 CV) vs validation (descriptive only)

| | development (56 qn, 402 obj) | validation (24 qn, 269 obj) | Δ |
|---|---|---|---|
| M1 recall@5 % | 0.955 [0.941, 0.974] | 0.939 [0.904, 0.974] | −0.017 |
| M1 recall@1 / 10 / 20 % | 0.878 / 0.978 / 0.990 | 0.881 / 0.967 / 0.989 | +0.003 / −0.011 / −0.001 |
| M1 recall@K 10 / 25 / 50 | 0.950 / 0.980 / 0.990 | 0.952 / 0.981 / 0.981 | ≈ 0 |
| M1 AUC | 0.990 | 0.990 | −0.000 |
| M1 faint guard | −0.121 | −0.107 | +0.014 |
| M1 zone+outer vs control | −0.001 | −0.004 | −0.003 |
| M1 zone vs control | n/e (6 zone) | −0.154 | — |
| comparator recall@5 % | 0.709 | 0.695 | −0.014 |
| comparator faint guard | −0.423 | −0.449 | −0.027 |
| B0 recall@5 % | 0.055 | 0.032 | −0.023 |

The development figure was optimistic, as AS-039 warned: the features
were gated on the same data. Even so, M1 generalises with essentially no
shrinkage, and the comparator gap is the same (+0.246 → +0.243). The one
new piece of information is the zone-only contrast. Development could not
measure it (6 zone positives), and on validation it is the weakest
number.

## Counterexamples and failure cases

**F1. 17 positives (16.5 object-nights) outside the M1 top 5 %.** The
full list with features, percentiles and strata is in
`as040_validation.md`.

- 13 MARGINAL, all with depth < 0.5 mag. The 4 lowest-ranked are
  C27 267663 (q 0.49), C27 148050, C29 450990 and C30 533784.
- 4 PRIMARY: the 3 zone objects above and C6 197971 (dense Milky Way
  field, |sharp| p 0.16, blended).
- By proximity group: control 10, intermediate 4, zone 3, outer 0.
- 2 all-masked, 2 partial (the partial mask stratum is 4/6 = 0.67 recall).

**F2. Strips of 12 missed positives** (agent labels):

- 9 are real but faint, at or near the noise level in at least one epoch;
  two of them touch a brighter star in one epoch;
- 2 are real near-star objects (halo edge or gradient, blends);
- 1 is unclear (crowding).

None looks like a mislabelled artefact. **The misses are faint or
near-star real objects**: exactly the population a human reviewer would
most want to see, and the one an UNKNOWN real object also belongs to.

**F3. Strips of 20 shortlist background tracklets** (in the M1 top 5 % of
their quadrant-night). By agent label, **20/20 look like artefacts or
mislinks, and none looks like a real mover**:

- 17 on bright-light structure: bleed columns (4), saturated-star halos
  or wings or spikes (8), detector-edge scattered-light gradients (5);
- 3 are crowded-field mislinks of stationary stars (C25 ×2, C6).

The shortlist (525 background tracklets over 24 quadrant-nights, against
269 positive object-nights) is therefore mostly artefacts. q measures
where real objects land relative to the background; it says nothing about
how clean the shortlist is. This estimate rests on 20 strips.

**F4. Quantisation in sparse fields.**

- C15: 26 background tracklets; C27: 36; C5: 42.
- With so few background tracklets, the top 5 % holds 1–2 slots, so
  recall@5 % per quadrant-night is coarse.
- C27's 2 misses come from 36 background tracklets.

**F5. Crowding.** In the ≥ 80 k stratum (14 object-nights in C1/C6/C24/C25),
recall is 0.79 against 0.94 below 20 k.

**Post-hoc (exploratory; not pre-registered; does not affect the
verdict).** I tabulated the proximity group of the 525 shortlist
background tracklets against all 10 511 background tracklets:

| | control | intermediate | outer | zone | flagged > 0 | masked > 0 |
|---|---|---|---|---|---|---|
| all background | 0.52 | 0.17 | 0.10 | 0.22 | 0.79 | 0.39 |
| M1 shortlist background | 0.56 | 0.19 | 0.14 | 0.11 | 0.68 | 0.25 |

The shortlist is depleted in Tycho-zone background (0.11 vs 0.22), yet
its artefacts are visibly bright-light structure. The strips suggest
three causes:

- edge glow from stars off the quadrant;
- halos of stars that are not in the zone's V/radius classes;
- bleed columns far from the star centre.

A later shortlist cleaner would need an artefact signal other than Tycho
proximity, but this is a hypothesis. Nothing here was tuned or tested.

## Known limitations carried forward (AS-038/039), with validation evidence

- **Faint disadvantage (O1)**: confirmed on validation (−0.107, interval
  excludes 0). 13 of 17 misses are MARGINAL. Half of M1's weight sits on
  SNR, sharp and fit features.
- **Mask/flag proxy near bright stars (O2)**: there is no zone+outer
  penalty (−0.004), but zone-only is −0.154 with an interval that
  excludes 0. All 3 zone misses have low flag/mask/shared percentiles.
  The guard passed, by one object.
- **Fit-residual leakage (O7)**: `fit_rms_residual_arcsec` (1/8 of M1)
  partly restates the ≤ 2″ identification that defines positives. This
  holds on validation too and is not corrected, so validation recall for
  *known* objects may overstate recall for real *unknown* objects.
- **`sharp` / M1 availability (O6)**: M1 (1/8) and the comparator need
  `sharp_abs_max`. `sharp` is not in the API `SourceDetection`, so the
  validated M1 runs only in the research path until a mapping change.
- **Population**: the C sample is near-star-selected, 2018–2020 ZTF,
  three-exposure sequences. Positives are main-belt dominated, ≤ 1″/min
  and have a baseline ≥ 3″. The claim covers this population only.
- **Background is a mixture**: recall measures known objects against
  UNKNOWN tracklets. It does not show that real unknowns rank as well,
  and (F3) the shortlist is mostly artefacts.

## What this establishes, and the handoff

**Confirmatory result: USEFUL, PROTECTED** (AS-037 rule applied once,
mechanically).

The frozen M1 is recorded as the **validated research ranker**, exactly as
specified in `validation/results/as039/as039_frozen_ranker.json`:

- equal-weight mean (0.125 each) of within-quadrant-night mid-rank
  percentiles of:
  - `min_snr` (+), `median_snr` (+);
  - `fit_rms_residual_arcsec` (−), `magnitude_range_mag` (−);
  - `flagged_detection_count` (−), `masked_detection_count` (−);
  - `sharp_abs_max` (−), `shared_detection_tracklets` (−);
- missing percentile 0, intercept 0, nothing fitted, higher = reviewed
  earlier.

Handoff to productization / Human Review (not started here):

- M1 is a ranking for ordering review, never a filter or rejection rule.
- Zone and faint objects are its weak spots (F1, guards). A reserved
  review quota per proximity stratum or depth stratum is the AS-037 §7
  suggestion for protection. It is not decided here.
- The shortlist will mostly contain bright-light artefacts and crowding
  mislinks (F3).
- `sharp` must be mapped into the API path before M1 can run outside the
  research path.
