# AS-037 — Candidate-ranking experiment design and pre-registration

Status: **pre-registered, no ranking outcome exists.** This document, the
frozen split manifest `as037_manifest.json` and the PRE-REGISTRATION block of
`app/validation/ranking_design.py` are committed together, before any
feature table, score or ranking for any quadrant-night was computed or
looked at.
No ranking model, score, threshold, hard filter, exclusion radius, rejection
rule or UI was built.

Regenerate the manifest (offline, deterministic apart from `generated_at`):

```
python -m app.validation.ranking_design manifest \
    --out validation/results/as037/as037_manifest.json
```

`tests/test_ranking_design.py` rebuilds the manifest and checks that it
matches the committed file.

## 1. Question and what "useful" means

We need a way to put a short list of the thousands of built UNKNOWN
tracklets per quadrant-night (AS-023: 5634 tracklets in the crowded D field)
in front of a human, without burying real moving objects. Real unknown
objects cannot be labelled. **Recovered known objects stand in for them.**
They are ranked identity-blind among the UNKNOWN background of their own
quadrant-night, and we ask where they land.

The question to answer: does a ranking built only from tracklet quality
features put most real objects into the top 5 % of their quadrant-night's
background? And does it do so for faint objects and for objects near bright
stars as well as for the rest?

## 2. Evidence this design rests on (AS-031–AS-036)

| evidence | consequence for the design |
|---|---|
| AS-031: KNOWN vs UNKNOWN differ in min SNR and fit RMS, but targets are bright by construction | SNR is confounded with target brightness → faint-object guard, stratification by role / depth margin |
| AS-031: B/C mixed filters inflate magnitude range | magnitude features stratified by single / mixed filter |
| AS-031: D field holds 833 of 960 built unknowns | ranking and metrics are **within quadrant-night**; features enter as within-field percentiles |
| AS-032/033: masked ≠ false (80429 carries bit 12); unmasked artefacts exist | mask counts are candidate features only; no mask rule |
| AS-034: contamination graded in star magnitude × distance; masks and sharp partly track proximity | proximity is context; mask/sharp features are watched by the near-star guard because they act as proximity proxies |
| AS-035: short baseline (S3) is its own failure mode; losses before tracklets cannot be ranked | positives must be rate- and baseline-eligible; end-to-end recall reported separately |
| AS-036: zone PRIMARY recovery 17/33 vs 114/149 (confirmed penalty) | a ranking must not add a second penalty → near-star guard on the validation split |
| AS-036: C29/C30 hold the same objects on the same night | object-night weights; independence groups |

## 3. Evaluation population (frozen)

- **Unit**: one quadrant-night (three exposures), unchanged pipeline,
  `EXPERIMENTAL_DEFAULT_CONFIG`, SkyBoT replayed from the stored snapshots
  (AS-022, AS-033, `as034_skybot.json`, `as035_skybot.json`,
  `as036_skybot.json`).
- **Ranked list**: every **built** tracklet of the quadrant-night. Rejected
  tracklets are never ranked.
- **Identity-blind**: the ranker gets no identification status, designation,
  SkyBoT prediction or residual against a known object.
- **Source**: the 80 already frozen quadrant-nights. No new search was run:
  - AS-034 R: 26 quadrants (AS-022 POC/B/C/D, AS-033 S1–S4 and siblings);
  - AS-035 N: 24 near-star quadrant-nights;
  - AS-036 C: 30 near-star quadrant-nights.

### Independence groups

Quadrant-nights are linked (union-find) when they share:

- the UTC night, or
- a search / selection star, or
- the ZTF field with nights ≤ 3 days apart (same sky, possibly the same
  objects and artefacts).

A connected component is a **group**. Groups are the resampling unit of
every interval and are never split between development and validation. The
manifest lists all 80 quadrant-nights with group and split, every link with
its reason, and the SHA-256 of every input file.

### Split

| split | rule | quadrant-nights | groups |
|---|---|---|---|
| **development** | any group with an R or N member (R features were explored in AS-031–034; N is the exploratory AS-035 sample) | 56 (R 26, N 24, C 6) | 27 |
| **validation** | all other groups: C only, features never extracted | 24 | 22 |

Six C quadrant-nights moved to development by the link rule, with no outcome
involved:

- C7 (same night as B and N19);
- C12 (same night as N12);
- C4 (ZTF field 335, 1 day from N24);
- C18 and C19 (field 333, 2 days from N18 and N8);
- C20 (same star as C18 and C19).

Validation = C1, C2, C3, C5, C6, C8, C9, C10, C11, C13–C17, C21–C30. The
SHA-256 of the sorted field ids is `a549b6bc22a5…` (full value in the
manifest). Mean sources per frame range from 5 k to 183 k: 4 crowded
quadrant-nights above 90 k and 20 below 30 k.

**Sealing.** The stage-1 and stage-2 runners must call
`ranking_design.require_split(manifest, field_id, stage)` for every
quadrant-night they load. It raises for any validation quadrant-night. The
validation runner (stage 3) accepts only validation quadrant-nights, and
only with a committed frozen-ranker spec. Validation features are not
extracted before that commit.

## 4. Positive controls and labels

| label | rule | role in metrics |
|---|---|---|
| **POSITIVE** | built tracklet identified KNOWN whose best match is an AS-022-rule target (PRIMARY or MARGINAL) of that quadrant-night that is rate-eligible (≤ 1″/min) and baseline-eligible (every pairwise predicted displacement ≥ 3″). This is the AS-035/036 "recovered" outcome. | ranked against the background |
| **AUXILIARY** | built KNOWN tracklet of any other object (non-target, or an ineligible target), and every AMBIGUOUS tracklet | ranked (it uses review slots), but neither positive nor background |
| **BACKGROUND** | built UNKNOWN tracklet. A mixture of artefacts, mislinks and possibly real unknowns; not a ground-truth false positive | the list the positives compete with |
| NOT RANKED | rejected tracklet | — |

A failed SkyBoT lookup is never UNKNOWN (`label_tracklet` raises). The
quadrant-night waits until the snapshot replays.

Positive-control availability, counted from the published AS-035/036
recovery traces (recovery outcomes, not ranking outcomes):

| | development | validation | validation minimum |
|---|---|---|---|
| positive object-nights | 402 | 269 (283 tracklet-targets; C29/C30 copies merged) | ≥ 100 |
| quadrant-nights with a positive | 49 | 24 | ≥ 15 |
| zone positives (AS-035 zone) | 6 | 14 | ≥ 10 |
| zone + outer (< 240″ of V < 10) | 54 | 45 | — |
| MARGINAL (faint) positives | 149 | 97 | ≥ 30 |

**All validation minimums are met before any ranking exists.** Development
has only 6 zone positives, so development-side protection checks use
zone + outer (54).

## 5. Metrics (pre-registered)

For a positive *p* in its own quadrant-night, with score *s*:

- **background-rank fraction** q(p) = (#background with score > s + ½ #ties)
  / #background;
- **background rank** r(p) = 1 + #above + ½ #ties.

Other positives and auxiliary tracklets do not count against *p*. So q does
not depend on how many known objects a field happens to contain: known
objects stand in for the one or two real unknowns a field may hold. Rank
direction: a higher score is reviewed earlier.

- **Primary: recall@5 %**: weighted share of positive object-nights with
  q ≤ 0.05.
- Secondary:
  - recall at 1 / 2 / 10 / 20 %;
  - recall@K for K = 10 / 25 / 50 per quadrant-night (r ≤ K);
  - enrichment = recall@f / f (random = 1);
  - within-field AUC = mean (1 − q);
  - median q.
- **Object-nights and duplicates**: the key is (designation, UTC night). An
  object seen in k quadrant-nights of one night has total weight 1 (1/k per
  copy; this applies to C29/C30). If one object has several positive
  tracklets in a quadrant-night, its best-scored one counts. The other
  copies stay in the list and use slots.
- **Intervals**: 95 % percentile bootstrap over independence groups, 2000
  resamples, seed SHA-256('AS-037:<label>'). Differences of shares get a
  Newcombe interval (descriptive).
- **End-to-end** (secondary, never deciding): (eligible targets whose
  tracklet has q ≤ 0.05) / (all eligible targets). This shows the AS-036
  recovery penalty and the ranking together, zone vs control.

## 6. Stages, kept apart

| stage | data | what may happen | ticket |
|---|---|---|---|
| 1 Feature evaluation | development only | extract the candidate features; per feature, within-field AUC in its pre-registered direction with group-bootstrap CI, overall and per stratum; freeze the passing feature list | AS-038 |
| 2 Ranking construction | development only, grouped 5-fold CV | fit and select only within the finite ranker family below; freeze one ranker + one comparator | AS-039 |
| 3 Validation | validation only, once | apply the frozen ranker and comparator; decision rule; failure analysis; **no tuning, no re-selection** | AS-040 |

### Candidate features (stage 1) and direction

Every feature enters a ranker only as its **within-quadrant-night
percentile** (mid-rank, oriented so that higher = reviewed earlier).

| feature | direction | note |
|---|---|---|
| `min_snr`, `median_snr` | higher first | brightness-confounded → faint guard |
| `fit_rms_residual_arcsec`, `fit_max_residual_arcsec` | lower first | identification needs ≤ 2″, far above typical RMS; partial restatement of selection, documented |
| `magnitude_range_mag`, `magnitude_range_sigma` | lower first | colour in mixed-filter fields → filter stratum |
| `magnitude_chi2` | lower first | defined now: Σ((m − m̄_w)/σ)², inverse-variance weighted mean (AS-031 H3) |
| `flagged_ / masked_ / edge_detection_count` | lower first | proximity proxies (bit 12) → near-star guard |
| `sharp_abs_max` | lower first | max \|sharp\|; research path only (`sharp` is not in the API path) |
| `shared_detection_tracklets` | lower first | number of other built tracklets that share a detection (AS-032 O3) |

**Context only. These are never inputs of a selectable ranker:**

- bright-star proximity: `StarProximity` separations by class, zone /
  outer / intermediate / control;
- speed and position angle. These are known-population priors and would
  demote NEOs and unusual motion.

`detection_count` is constant (3 frames) and is not evaluated.

**Stage-1 gate.** A feature passes when all of these hold:

- the overall within-field AUC lower bound is > 0.55;
- the MARGINAL point AUC is ≥ 0.5;
- the zone + outer point AUC is ≥ 0.5;
- it is missing for ≤ 5 % of ranked tracklets.

When two passing features have |Spearman| > 0.90 on development background,
the one with the lower AUC is dropped.

### Ranker family (stage 2), nothing else may be tried

- **B0**: SHA-256 hash order (null, expected recall@5 % = 0.05).
- **B1**: each passing feature alone.
- **M1**: unweighted mean of the passing features' percentiles (no fitted
  weights).
- **M2**: L2 logistic regression, positive vs background, on the same
  percentiles, quadrant-nights weighted equally, C ∈ {0.01, 0.1, 1, 10}.

All estimates are grouped CV (folds in SHA-256('AS-037:<group>') order) and
never in-sample.

**Selection**:

- pick the highest CV recall@5 % among M1/M2 whose CV near-star
  (zone + outer) and MARGINAL guards pass with the 0.20 margin;
- if they are within 0.02, take M1;
- the best B1 is the frozen comparator.

A proximity-including variant may be reported in stage 2 as exploratory
and can never be selected.

## 7. Decision rule (stage 3, applied once to validation)

`ranking_design.decide()` implements it:

1. **INCONCLUSIVE** when either holds: fewer than 100 positive
   object-nights, or fewer than 15 quadrant-nights with a positive.
2. **NOT USEFUL** when the bootstrap upper bound of recall@5 % is < 0.50.
3. **USEFUL** when recall@5 % ≥ 0.50 (10× enrichment) and its lower bound
   ≥ 0.30 (6×). Then the guards qualify it:
   - **near-star guard**: zone recall@5 % ≥ control recall@5 % − 0.20
     (evaluable with ≥ 10 zone object-nights);
   - **faint guard**: MARGINAL recall@5 % ≥ PRIMARY recall@5 % − 0.20
     (≥ 30 MARGINAL object-nights);
   - outcomes: **USEFUL, PROTECTED** (both evaluable and pass), **USEFUL,
     NOT PROTECTED** (a guard fails), **USEFUL, PROTECTION UNVERIFIED** (a
     guard is not evaluable).
4. Otherwise **INCONCLUSIVE** (the interval neither reaches nor excludes the
   useful level).

The 0.20 margin is the smallest difference that matters (AS-036). Guards
use point estimates; their Newcombe intervals are reported.

Secondary, never deciding:

- frozen ranker vs comparator (paired group-bootstrap difference of
  recall@5 %);
- all secondary metrics;
- every stratum below.

**USEFUL, NOT PROTECTED** means the shortlist may not be used on its own.
Any later use would need an explicit protection mechanism, for example a
reserved quota of review slots per proximity stratum. That is not decided
here.

## 8. Bright-star proximity: risk context, never rejection

- Proximity is not an input of any selectable ranker. It is not a filter,
  radius or demotion rule.
- It stays a reported column and a stratification variable: zone / outer /
  intermediate / control, and star class V < 6 / 6–8 / 8–10.
- Mask counts and |sharp| can act as **implicit proximity rejection**
  (bit 12 marks the V < 6 halo; sharp rises near V 4–10 stars). The
  near-star guard on validation and the zone + outer check in stage 2
  exist to catch this.
- The end-to-end metric shows whether the ranking adds a penalty on top of
  the confirmed AS-036 recovery penalty.

## 9. Confounders, leakage, duplicates, strata

**Confounders.**

- Positive brightness: targets are V ≤ maglimit + 0.5 and PRIMARY ≤
  maglimit − 0.5, so SNR partly restates selection. Handled by the faint
  guard and the depth-margin stratum.
- Crowding: 5 k–183 k sources per frame. Handled by within-field ranking
  and percentiles, plus a crowding stratum.
- Mixed filters inflate the magnitude range: filter stratum.
- Positives are main-belt dominated: motion features are excluded from
  rankers.
- Seeing and detector position: not modelled, reported per quadrant-night.
- Near-star selection: every N/C quadrant-night has a bright star passage,
  so validation is near-star-enriched while still mostly general field.
  Results are claimed for this population only.

**Leakage.**

- No identification-derived input (status, designation, residual to a
  prediction, SkyBoT match).
- No per-field statistic computed with labels.
- Percentiles are computed over the whole ranked list of the quadrant-night
  without labels.
- Development features (R) were inspected in AS-031–034, so R is never
  validation.
- C validation features have never been extracted.
- Hyper-parameters (C grid, feature list) are fixed on development only.
- Residual leak: fit quality relates to identification success. This is
  documented and is the reason for the faint guard and the failure
  analysis.

**Duplicates.**

- The same object in overlapping fields on one night gets object-night
  weights.
- Several positive tracklets of one object: the best one counts.
- A background tracklet that shares a detection with a positive stays
  background (conservative). A sensitivity analysis drops these
  tracklets.
- Across splits, one designation (105890) is a target in both development
  and validation on different nights. A sensitivity analysis excludes it.

**Strata (reported on validation, descriptive)**:

- role (PRIMARY / MARGINAL);
- minimum global depth margin (< 0.5 / 0.5–1.5 / ≥ 1.5 mag);
- proximity group and star class;
- crowding (< 20 k / 20–80 k / ≥ 80 k sources per frame);
- single vs mixed filter;
- speed (< 0.25 / 0.25–0.5 / 0.5–1.0 ″/min);
- mask state of the positive (unmasked / partial / all);
- per quadrant-night.

**Failure analysis (stage 3)**:

- every validation positive with q > 0.05 is listed with features and
  strata;
- strips of up to 12 such positives and of 20 top-5 % background
  tracklets, in SHA-256 order, with agent labels (not ground truth). This
  estimates the artefact share of the shortlist.

## 10. What this design cannot show

- That an individual UNKNOWN is real or false. The background is a mixture.
- Ranking of real objects lost before tracklet building (AS-035/036
  detection / stationary losses). Ranking cannot recover them; the
  end-to-end metric only makes that visible.
- Behaviour for NEOs, slow movers (< 3″ baseline) or objects faster than
  1″/min. None of these are positives.
- Generalisation beyond 2018–2020 ZTF, |β| ≤ 10°, three-exposure
  sequences.

## 11. Handoff: AS-038 (stage 1, development only)

1. Build the development feature table: run the unchanged pipeline on the
   56 development quadrant-nights (SkyBoT replayed). For every built
   tracklet, write the `TrackletQualityFeatures` (with raw sharp), the
   derived `magnitude_chi2`, `sharp_abs_max` and
   `shared_detection_tracklets`, the context columns (StarProximity,
   proximity group, speed, PA) and the pre-registered label (eligible
   targets from the AS-035/036 traces). Call `require_split` for every
   quadrant-night.
2. Evaluate each candidate feature with the pre-registered direction:
   within-field AUC and recall@5 % with group-bootstrap CIs, overall and
   per stratum. Report missingness and the Spearman redundancy matrix on
   background.
3. Apply the stage-1 gate and commit the frozen passing feature list.
   Nothing beyond the gate: no weights, no ranker, no CV and no validation
   access.

AS-039 (ranking construction) and AS-040 (one-shot validation) follow
sections 6–7 unchanged.
