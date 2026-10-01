# AS-035 findings — known-object recovery near bright stars

Generated evidence: `as035_evidence.md` / `.json` (per-target stage traces,
contrasts, strips), per-population traces `as035_traces_N.json` /
`as035_traces_R.json`, the frozen search result `as035_selection.json`,
N SkyBoT predictions `as035_skybot.json` (replayed on re-runs), strips in
`strips/`, agent visual labels in `visual_review.json` (not ground truth).

Pre-registration: commit `fa4cd97` (populations, search rule, sequence and
per-object baseline rules, detectability, strata, zone/control, trace
stages, claim rule, strip rule), made before any AS-035 outcome. The N
selection was frozen in `56d445d` before any N target was traced. R (the
26 AS-034 quadrants) is not blind: AS-034 had reported its aggregate loss
stages.

No filter, exclusion radius, score, rank, threshold, rejection rule or
candidate policy was introduced. SkyBoT prediction ≠ detectability;
KNOWN is a selected population; proximity ≠ causation; agent labels ≠
ground truth.

## Method in one paragraph

N: Tycho-2 V < 6 and 6–8 stars (Dec ≥ −25°, |β| ≤ 10°) in SHA-256 order;
for each, the earliest ZTF quadrant-night (2018-03-17 – 2021-01-01) with a
qualifying E1/E2/E3 (gaps ≥ 15 min, span ≤ 150 min, archived products)
where SkyBoT predicts an AS-022-rule, rate- and baseline-eligible object
within 120″ of the star → 24 quadrant-nights (12 per class, 546 SkyBoT
queries, 91 stars tried incl. 6 skipped after SkyBoT errors). Every AS-022-rule target (PRIMARY / MARGINAL)
of the 24 + 26 quadrants (755 objects) is traced through six stages with
its first failure; closest predicted approach (E1–E3 positions) to Tycho-2
stars by class; zone = < 120″ of V < 6, < 60″ of 6–8, < 30″ of 8–10
(AS-034 contamination reach); control = ≥ 480″ from V < 10 and ≥ 60″ from
V 10–11 stars, same quadrant-nights.

## OBSERVATIONS

O1. **Temporal baseline separated first.** 82 targets fail the per-object
baseline rule (pairwise predicted displacement < 3″): 78 in the four S3
quadrants (0.66-min E1–E2) and 4 slow movers in N1/N2. 0/82 recovered
(first failure: stationary 53, detection 29). In the stationary failures
of this stratum, 104 of 108 stationary frames matched the object's *own*
source in another frame ("self"). Among the 669 eligible targets, all 63 stationary failures
matched *another* source ("other"); none matched itself. The rule
therefore isolates the S3 failure mode, and those objects are not counted
below. 4 objects are too fast (> 1″/min) and reported separately.

O2. **Eligible recovery overall**: PRIMARY 225/285 (79 %), MARGINAL 132/384
(34 %). First failures: PRIMARY detection 27, stationary 32, fit 1;
MARGINAL detection 218, stationary 31, fit 3. No eligible target was lost
at association or identification.

O3. **Zone vs control (pre-registered contrast, PRIMARY, eligible)**:

| scope | zone | control | Fisher p | MH OR (quadrants) | rule verdict |
|---|---|---|---|---|---|
| N + R | 3/7 (43 %, 16–75) | 131/154 (85 %, 79–90) | 0.016 | 0.07 (6) | not demonstrated: 7 < 10 zone targets |
| N | 3/7 | 86/96 (90 %) | 0.006 | 0.07 (6) | not demonstrated: 7 < 10 |
| R | 0/0 | 45/58 (78 %) | – | – | not demonstrated: 0 zone targets |

MARGINAL: zone 0/11 (0 %, 0–26) vs control 71/193 (37 %, 30–44). Outer
(< 240″, outside the zone): PRIMARY 24/31 (77 %), MARGINAL 19/61 (31 %).
Intermediate: 67/93 (72 %), 42/119 (35 %).

O4. **Where zone targets are lost: always at source detection.** 15/15
zone losses (4 PRIMARY, 11 MARGINAL) fail at detection, 13 of them by
missing exactly one of three epochs. No zone target was lost at the
stationary, association, fit or identification stage. 12/18 zone targets
have ZTF bit 12 (bright-star halo) on at least one detection; 0/347
control targets do. The four PRIMARY zone losses (V 18.7–19.8, global
margin ≥ 0.9 mag in every frame) are:
- 700826 (N17, 93″ from V 5.7): E2 nearest source 2.2″ away (just outside
  the 2.0″ match radius); E1/E3 detected with bit 12.
- 188826 (N8, 82″ from V 5.8): E1 nothing within 8.5″; E2/E3 bit 12.
- 203683 (N15, 107″ from V 6.0): E1 nothing within 5.7″ (zg); E2/E3 bit 12.
- 409309 (N12, 116″ from V 3.7): E3 nothing within 8.5″; E1/E2 bit 12.
The three recovered PRIMARY zone targets are 172379 (46″ from V 7.8),
190831 (91″ from V 5.9) and 72582 (103″ from V 5.8).

O5. **Magnitude × closest approach** (eligible, PRIMARY/MARGINAL; full
table in the generated report): no PRIMARY target came within 60″ of a
V < 6 star or within 30″ of a 6–10 star. The closest cases are all
MARGINAL and all lost at detection: 157539 (1″ from V 8–10), 332829 (6″,
6–8), 34131 (16″, 8–10), 434592 (21″, 8–10), 116749 (38″, 6–8). V 8–10
at 30–60″: PRIMARY 5/7; at 60–120″: PRIMARY 3/3, MARGINAL 3/14.

O6. **Losses elsewhere are not bright-star-specific.** In the control
group PRIMARY targets are lost at stationary (14) as often as at detection
(9); the stationary losses (all "other") are blends with field sources in
crowded or merely busy fields (strip N23 237824).

O7. **Local depth descriptor.** Zone detection losses: 6 locally
detectable (local catalog depth − expected magnitude ≥ 0), 9 locally
below. The estimator breaks down inside bright-star glow: 190831 and
172379 were recovered with local margins of −7.5 and −6.2 mag, because
the glow fragments are bright, low-SNR catalog sources. It is reported,
but it cannot separate "physically undetectable" from "pipeline loss"
near V < 8 stars.

O8. **Visual sample (22 strips, agent labels).** Near-lost (8): 1 on a
V 8–10 star's glow edge with the object visible in E1/E3 (34131); 1 on the
halo arc / spike region of a V 5.7 star with no clear source (700826);
4 faint/at the noise level with no star structure in view (29559, 305928,
465280, 331332); 1 visible but uncatalogued in a fainter g-band epoch
(242915); 1 blend with field stars, slow mover (36463). Near-recovered
(8): 7 clean or crowded-field moving sources. 1 (93731) is recovered while
on a bright star's diffuse glow/spike band (counterexample). Controls (4):
2 recovered clean. 1 lost to a blend with a field star (237824). 1
(165846) lost when E3 lands on a saturated star with spikes that is
**not** in Tycho-2 V ≤ 11 (nearest V ≤ 11 star 320″).

O9. **AS-034 revisit (both fall in R by the pre-registered rule, not
special-cased).** 288181: predicted E1–E2 displacement 0.37″ → short-
baseline stratum. E1 is not detected: it sits on a bright vertical column
artifact. E3 is on the outskirts of the V 9.6 star 79″ away. 408599:
0.34″ → short-baseline stratum. It is stationary-matched to its *own*
source in E1/E2 (self), on top of a compact field star, and moves off in
E3. Neither enters the near-star contrast. Neither is evidence of a
bright-star penalty: 408599 is a short-baseline + blend case, and 288181
is short-baseline + column artifact.

O10. **Definition note.** The AS-022 outcome counts a KNOWN
identification on a *rejected* tracklet as recovered (R: 297773; N:
307705, 715287, 296676). The pre-registered trace requires fit
acceptance, so these four are "fit" losses here. Otherwise the AS-022 loss stages of all 335 R targets
reproduce AS-034 exactly.

## Counterexamples

- 93731 (N24): recovered while E2/E3 lie on a bright star's glow band.
- 172379 (N11, 46″ from V 7.8), 190831 (91″ from V 5.9), 72582 (103″
  from V 5.8): PRIMARY zone targets recovered.
- 165846 (N14): a "control" object lost on a saturated star that Tycho-2
  V ≤ 11 does not list — star effects reach into the control group.
- 242915, 305928, 465280, 29559: "near-star" losses with no visible star
  structure at the position (depth / band / noise).
- Most near-star MARGINAL losses resemble the control MARGINAL losses
  (single-epoch misses at the depth limit).

## HYPOTHESES (not tested here)

H1. Within ≈ 2′ of V < 6 stars (and likely closer to 6–10 stars), the
loss mechanism is a single-epoch source-detection dropout inside the halo
(bit 12) region (background structure / deblending in the ZTF PSF
catalog), not a later pipeline stage. The 2.2″ miss of 700826 suggests
centroid shifts near halos may also matter.
H2. The MARGINAL zone result (0/11) is partly ordinary depth loss, because
MARGINAL control recovery is only 37 %. A raised local background near
the star would push MARGINAL objects below detection more often than in
the control.
H3. Saturated stars fainter than Tycho-2's completeness (V ≳ 11) affect
recovery like brighter ones at smaller radii, and so dilute the control.

## CONCLUSIONS

C1. **Temporal baseline is a separate failure mode**, now explicitly
controlled: every S3-like object (min pairwise displacement < 3″) is lost
at stationary/detection regardless of stars, and none of the 63
stationary losses among eligible objects is a self-match.
C2. **Near-star losses, where they occur, are detection-stage losses.** No
eligible near-star target was lost at stationary matching, association,
fit or identification.
C3. **A near-star recovery penalty is suggested but NOT demonstrated under
the pre-registered rule.** PRIMARY zone recovery is 3/7 vs 131/154
(p = 0.016, MH OR 0.07), but n = 7 < 10. The direction is consistent
across MARGINAL (0/11 vs 71/193) and in N alone. The current data are
**insufficient to claim** the penalty; they are also not evidence that
bright-star proximity is safe for real objects.

Confidence: high for C1 and C2 (mechanism counts, all strata). Low to
moderate for the size of any penalty (7 PRIMARY zone targets, 6 shared
quadrants, no PRIMARY within 60″ of V < 6 or 30″ of 6–10 stars).

## What we can and cannot claim

Can: S3-like baseline failures are separable and were separated; near-star
KNOWN losses in these data are source-detection losses (mostly one epoch
of three, typically in the bit-12 region); recovery in the pre-registered
star zone was lower in every population/role cut available.
Cannot: that the pipeline has a near-star recovery penalty (pre-registered
claim rule not met); its size; any radius or magnitude limit; that any
individual near-star UNKNOWN or lost KNOWN is or is not real.

## Limitations

- 7 PRIMARY zone targets; the search triggered on 120″ approaches, but the
  zone for 6–8 stars is 60″, and 14 of the 23 trigger objects that are
targets are MARGINAL (9 PRIMARY).
  Within 30″ of any V < 10 star there are only MARGINAL objects (4).
- Tycho-2 is incomplete beyond V ≈ 11; saturated fainter stars leak into
  the control (165846).
- The local-depth estimator fails inside glow (O7); detectability near
  V < 8 stars therefore rests on the global frame maglimit plus band
  offsets (± 0.2 mag colour, ± 0.3 mag SkyBoT V).
- R is not blind; N is blind. The direction is the same, but R has no
  zone PRIMARY targets.
- Mixed filters, seeing, crowding and detector position differ between
  quadrants. The MH comparison holds them fixed only within the 6 shared
  quadrants.
- 6 search stars were skipped after SkyBoT errors (logged, per the rule);
  SkyBoT ephemerides drift slightly over time (snapshots stored).
- Visual labels are the agent's; a human should review the 22 strips.

## Decision support (for the human)

Bright-star proximity can enter a later candidate-ranking experiment as a
descriptive risk feature only together with explicit protection or an
interaction term for real-object recovery. The KNOWN evidence points the
same way as the UNKNOWN contamination (losses concentrate in the same
zone), but it cannot show whether real objects there are separable. A
targeted search for PRIMARY objects closer than 60″ to V < 8 stars (more
nights per star, or a trigger radius matched to the zone) would be needed
to meet the pre-registered n ≥ 10.
