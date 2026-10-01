# AS-036 findings — near-star PRIMARY recovery confirmation

Generated evidence: `as036_evidence.md` / `.json` (decision, secondary
contrasts, per-target stage traces, leave-one-star-out, strips), traces
`as036_traces_C.json`, the frozen search result `as036_selection.json`,
C SkyBoT predictions `as036_skybot.json` (replayed on re-runs), strips in
`strips/`, agent visual labels in `visual_review.json` (not ground truth).

Pre-registration: commit `fc9d971` (search stars and order, search
expansion, trigger, budget, unchanged AS-035 definitions, minimum sample,
decision rule, strip rule), made before any AS-036 search or outcome. The
selection C was frozen in `43531ed` before any C target was traced. Nothing
in the protocol was changed afterwards.

No filter, exclusion radius, score, rank, threshold, rejection rule or
candidate policy was introduced. SkyBoT prediction ≠ detectability;
KNOWN is a selected population; proximity ≠ causation; agent labels ≠
ground truth.

## Method in one paragraph

C (new, blind): Tycho-2 V < 6 and 6–8 stars (Dec ≥ −25°, |β| ≤ 10°,
2018-03-17 – 2021-01-01) in SHA-256('AS-036:<id>') order, classes
alternating. Per star, the first 20 qualifying quadrant-nights (AS-035
sequence rule) that are not AS-035 N/R quadrant-nights each got one SkyBoT
cone. A night triggers when an AS-022 PRIMARY, rate- and baseline-eligible
object inside the footprint passes inside the star's zone (< 120″ V < 6,
< 60″ 6–8). At most 3 nights per star. Budget per class: 15 trigger
objects, 300 stars or 3000 cones. Every AS-022-rule target of the selected
quadrant-nights (triggers and by-catch) is traced through the AS-035
six-stage tracer. Zone and control use the unchanged AS-035 definitions.
The decision rule applies to C only.

## Search and sample

- Budget used: V < 6 done (15 trigger objects) after 66 of 731 eligible
  stars and 675 cones; 6–8 done (15) after 172 of 5415 stars and 1741 cones.
  Budget was not exhausted (limit 300 stars / 3000 cones per class).
- 30 quadrant-nights C1–C30 (15 per search class), 50 AS-035
  quadrant-nights excluded. Night log: 23 SkyBoT errors after 3 attempts
  (not used, per the rule), 4 triggering nights without archived products,
  1 night skipped as already selected.
- 630 AS-022-rule targets (292 PRIMARY, 338 MARGINAL).
- Run note: the first `evidence` attempt stopped on an IRSA metadata read
  timeout. The rerun replayed the SkyBoT predictions already stored, and
  IRSA products are archival, so the rerun cannot change any outcome. A
  fresh live trace of C14 (new SkyBoT query) reproduces the committed
  traces exactly (26/26 targets).

## OBSERVATIONS

O1. **Pre-registered decision (C only, PRIMARY, rate- and
baseline-eligible).**

| scope | zone | control | zone − control [Newcombe 95 %] | Fisher p | MH OR (quadrants) | verdict |
|---|---|---|---|---|---|---|
| **AS-036 C (deciding)** | **17/33 (52 %, 35–67)** | **114/149 (77 %, 69–83)** | **−0.25 [−0.42, −0.07]** | **0.0055** | **0.28 (27)** | **CONFIRMED** |

All four conditions hold: zone n = 33 ≥ 20 and control n = 149 ≥ 20, zone
lower, p < 0.05, MH OR < 1.

O2. **Short baseline cannot enter the comparison.** C contains 0
short-baseline targets (every trigger had to be baseline-eligible, and no
by-catch target fell below 3″). 3 targets are too fast (> 1″/min: 2
PRIMARY control, 526315 and 2010 DK66; 1 MARGINAL intermediate) and are
excluded and listed separately.

O3. **Zone composition (PRIMARY eligible; class of the star that puts the
target in the zone).** V < 6: 16 targets (0–30″ 1, 30–60″ 1, 60–120″ 14),
recovered 9. 6–8: 16 (0–30″ 5, 30–60″ 11), recovered 8. 8–10: 1 (0–30″),
recovered 0. 30 of the 33 are triggers and 3 are by-catch (61384, 36804,
560401). V 14.0–20.7. The median minimum global margin is 1.28 mag in the
zone and 1.31 mag in the control, so expected depth is comparable.

O4. **First failures.** Zone losses (16): detection 12 (10 miss one epoch
of three, 2 miss two), stationary 4 (all matched to *another* source). None
at association, fit or identification. Control losses (35): detection 16,
stationary 13 (all "other"), fit 6. Outer: 23/31 recovered (detection 4,
stationary 4). Intermediate: 60/77 (detection 11, stationary 5, fit 1).

O5. **Bit 12 (bright-star halo) on at least one detection:** zone 18/33
(9 recovered, 9 lost), outer 6/31, intermediate 5/77, control 0/149.

O6. **Local depth (descriptive).** 11 of the 12 zone detection losses are
"locally detectable" (local margin ≥ 0). Unlike AS-035, the local
estimator does not argue that these objects were too faint locally.

O7. **Secondary (descriptive, never deciding).**

| scope | zone | control | Fisher p | MH OR |
|---|---|---|---|---|
| C, trigger objects only | 16/30 (53 %) | 114/149 (77 %) | 0.013 | 0.32 |
| C, search class V < 6 | 8/16 (50 %) | 49/71 (69 %) | 0.16 | 0.29 |
| C, search class 6–8 | 9/17 (53 %) | 65/78 (83 %) | 0.011 | 0.27 |
| AS-035 alone (N + R; exploratory) | 3/7 (43 %) | 131/154 (85 %) | 0.016 | 0.07 |
| **POOLED AS-035 + AS-036 (secondary)** | 20/40 (50 %) | 245/303 (81 %) | 0.0001 | 0.23 |

Each search class alone is below the n ≥ 20 minimum. The V < 6 class alone
is not significant (p = 0.16) and its point estimate is smaller (−19
points).

O8. **Leave one search star out (26 stars).** Zone recovery 15/31–17/32,
Fisher p 0.0023–0.046. The largest p (0.046) comes from removing
TYC 1942-375-1 (C29 + C30, 37 controls).

O9. **C29/C30 overlap.** C29 and C30 are the same night on two overlapping
ZTF fields (617 and 1613), so 14 eligible PRIMARY objects are traced twice.
The rule keys on quadrant-nights, so both remain in the deciding sample.
Descriptively, dropping the duplicate copies from either field leaves zone
17/32 vs 104/138 (p = 0.017, MH OR 0.32) or 16/32 vs 103/138 (p = 0.0096,
MH OR 0.26).

O10. **Visual sample (16 strips, agent labels, SHA-256 order).** Zone lost
(6): 2 land on a saturated core / bleed trail or column in the epoch they
miss (4979 at 13″ from a 6–8 star, 36804 at 43″). 1 is at the edge of a
bleed column (26340). 1 is visible in all epochs on a 6–8 star's halo
edge but lost to a stationary match (135224, 29″). 2 are crowded-field
blends with star structure out of view or only nearby (48173 at 98″,
107974 at 92″ beside a bleed streak). Zone recovered (6): 3 lie on or
beside a halo, spike or bleed column (125093, 544, 146081), 1 is on a halo
outskirt (74293), and 2 are clean (61384, 24822). Controls: 2 clean
recovered. 2 lost in very crowded Milky Way fields (46401 detection,
158288 stationary) with no bright star.

## Counterexamples

- **125093 (C29 vs C30)**: the same object on the same night, 47–48″ from
  the same V 7.0 star. It was lost at detection in field 617 (E2 nearest
  source 4.6″) and recovered in field 1613. Proximity does not decide the
  outcome by itself. Position on the detector, and on the star's
  artefacts, matters.
- Recovered inside the zone despite star structure: 544 (31″, on the spike;
  V 14.0), 146081 (27″, halo edge), 125093/C30 (beside the bleed column),
  15009 (16″ from a V < 6 star, bit 12), 149159 (44″ from V < 6), and 31302
  (24″ from a 6–8 star). 17 of 33 zone targets were recovered.
- Zone losses that look like crowding rather than star structure: 48173,
  107974 (V < 6 star ~ 90–100″ away, out of view).
- Control losses in crowded fields with no bright star: 46401, 158288.
  Control recovery is 77 %, not 100 %.
- V < 6 search class alone: −19 points, p = 0.16. The confirmation is
  carried by the combined sample, not by each class.

## HYPOTHESES (not tested here)

H1. The penalty comes from the image footprint of the star (saturated
core, bleed columns/trails, spikes, halo), which one epoch of three hits
as the object moves. It does not come from a smooth function of distance.
Supported by O4 (mostly single-epoch detection losses), O10 and the
125093 pair, but not tested.
H2. Some near-star stationary losses come from glow fragments or
deblended halo sources acting as "other" stationary matches (135224).
Others are ordinary crowding (107974).
H3. The V < 6 class may have a smaller penalty at 60–120″ than the 6–8
class at < 60″. The per-class samples are too small (O7).

## CONCLUSIONS

C1. **CONFIRMED under the pre-registered rule.** In the new, blind sample
C, PRIMARY recovery of eligible known objects inside the AS-035 star zone
was 17/33 (52 %) vs 114/149 (77 %) in the same-quadrant control:
−25 points (95 % CI −42 to −7), Fisher p = 0.0055, MH OR 0.28 over 27
quadrant-nights. The AS-035 suggestion reproduces with a sample that meets
the pre-registered minimum.
C2. The penalty is real at the population level, but its size is
uncertain. A 7-point penalty is still compatible with the data. The
AS-035 point estimate (−42 points) was larger than C's (−25).
C3. Where zone targets are lost, it is at detection (12/16) or stationary
matching (4/16). They are never lost at association, fit or
identification. The short-baseline failure mode is absent from C and
cannot contribute.
C4. This says nothing about an individual candidate: half of the zone
objects were recovered, including objects on star artefacts. No radius,
magnitude limit or per-candidate rule follows from it.

Confidence: moderate–high that a near-star PRIMARY recovery penalty exists
in this pipeline (pre-registered, blind, robust to leave-one-star-out and
to C29/C30 deduplication). Low for its size per class or distance bin.

## What we can and cannot claim

Can: under a pre-registered, blind confirmation, eligible PRIMARY known
objects passing inside the AS-035 star zone (< 120″ V < 6, < 60″ 6–8,
< 30″ 8–10) are recovered less often than same-quadrant controls (about
25 points lower, CI 7–42). The losses are detection/stationary-stage
losses.
Cannot: its size per magnitude class or distance bin; a production
exclusion radius or threshold; that a near-star UNKNOWN is false; that the
mechanism is the star (H1 is untested); that it generalises beyond
2018–2020 ZTF, |β| ≤ 10°.

## Limitations

- The deciding sample counts 14 objects twice (C29/C30, O9). The
  dedup sensitivity is descriptive, but it does not change the
  classification direction.
- 23 SkyBoT-error nights were skipped per the rule. Selection therefore
  depends slightly on transient service state. The frozen selection is the
  record.
- Tycho-2 is incomplete beyond V ≈ 11. Saturated fainter stars and crowded
  Milky Way fields affect the control (O10), which makes the contrast
  conservative rather than inflated.
- Several C quadrant-nights are crowded low-latitude fields. Crowding
  losses occur in both groups. MH stratification holds the quadrant fixed,
  but not the position within it.
- 3 nights from one star (TYC 6274-1663-1, C18–C20) and 2 from
  TYC 3-1464-1 and TYC 1942-375-1. Leave-one-star-out covers this (O8).
- The local-depth estimator remains unreliable inside glow (AS-035 O7).
  Detectability rests on the global maglimit.
- Visual labels are the agent's; a human should review the 16 strips.

## Decision support (for the human)

The AS-035 near-star PRIMARY penalty is now confirmed by the
pre-registered rule. For later candidate-ranking research, bright-star
proximity (zone membership) is supported as a **risk context** for loss
of real objects. It is not supported as a reason to discard candidates:
half of the real objects in the zone were recovered. Any ranking
experiment would need to protect near-star real objects explicitly. The
next decisions are the human's: whether candidate-ranking research
should use zone membership as a descriptive feature, and whether the
detection-stage loss mechanism (H1/H2) merits its own investigation.
Neither is started here.
