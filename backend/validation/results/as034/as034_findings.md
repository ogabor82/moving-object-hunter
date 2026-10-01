# AS-034 findings — bright/saturated-star contamination as magnitude × distance

Generated evidence: `as034_evidence.md` / `.json`, strips in `strips/`,
agent visual labels in `visual_review.json` (not ground truth), the
pre-registered population in `as034_population.json`, sibling-quadrant
SkyBoT predictions in `as034_skybot.json`. Pre-registration: commit
`e805002` (bins, classes, population, KNOWN rule, visual rule), made
before any AS-034 evidence existed. Regenerate:

```
python -m app.validation.star_contamination evidence \
    --population validation/results/as034/as034_population.json \
    --out-dir validation/results/as034      # ~35 min, ~8.6 GB peak (D quadrants)
python -m app.validation.star_contamination render --out-dir validation/results/as034
```

No filter, exclusion radius, score, rank, threshold, rejection rule or
candidate policy was introduced. UNKNOWN is not a false positive by
definition; KNOWN is a small, selected population.

## Proximity features (explicit, reproducible)

`StarProximity` (`app/validation/star_contamination.py`) for any sky
position: `separation_by_class[c]` — great-circle distance (ICRS) to the
nearest Tycho-2 star of magnitude class c ∈ {V<4, 4–6, 6–8, 8–10, 10–11}
(V = VT − 0.090 (BT − VT); V = VT without BT; no VT → not used), null when
the field's cone (footprint circle + 15′) has no such star; plus the
nearest V ≤ 11 star's separation and V. For tracklets the mean detection
position is used, for KNOWN objects the closest approach over the three
predicted positions. Stars are "isolated" when no brighter Tycho-2 star
lies within 900″.

## Population (26 quadrants)

POC, B, C, D (AS-022), S1–S4 (AS-033) and the three sibling quadrants of
B, D, S1–S4 (same exposures and CCD; all 18 had archived products):
58 018 tracklets, 8 234 built UNKNOWN, 148 built KNOWN; 1 371 Tycho-2
V ≤ 11 stars in the cones (summed over quadrants), 1 036 of them with
annuli overlapping a footprint, 262 of those isolated; 335 KNOWN objects
under the AS-022 target rule. Conditions per quadrant (crowding
4–181 k sources/frame, seeing 1.6–4.7″, mixed filters in B/C/S1/S2/S4,
1-minute E1–E2 baseline in all S3 quadrants) are in the generated report.

## OBSERVATIONS

O1. **Magnitude × distance (isolated stars, pooled; ratio = built UNKNOWN
density over the same stars' 480–900″ background)**:

| class | 0–15″ | 15–30″ | 30–60″ | 60–120″ | 120–240″ | 240–480″ | stars |
|---|---|---|---|---|---|---|---|
| V < 4 | 125 | 62 | 37 | 13 | 0.9 | 0.3 | 3 |
| 4–6 | 181 | 175 | 65 | 16 | 2.3 | 0.1 | 8 |
| 6–8 | 132 | 74 | 17 | 1.1 | 0.6 | 0.3 | 41 |
| 8–10 | 28 | 15 | 0.8 | 0.7 | 0.7 | 0.9 | 145 |
| 10–11 | 2.9 (1 tracklet) | 1.9 (2) | 1.9 (8) | 0.4 | 0.9 | 0.9 | 65 |

The excess falls off with distance in every class and reaches farther for
brighter stars: (reading the table, post hoc) ≳ 60–120″ for V < 6, ~30–60″
for 6–8, ~15–30″ for 8–10, and no clear excess for isolated 10–11 stars.
Rejected UNKNOWN tracklets follow the same profile (ratios within ~30 % of
the built ones in every inner cell).

O2. **V > 6.5 stars contaminate**: 6–8 and 8–10 stars produce 200 and 58
built UNKNOWN tracklets above background within 60″ / 30″ (206 vs 5.9 and
61 vs 3.3 expected). Under AS-033's V ≤ 6.5 definition these sat in the
"control". Per field, 6–8 stars show 0–60″ ratios from 6.6 (D) to ~2700
(S1) and 8–10 stars from 0 (B, S1-q1, S3) to ~930 (S1-q2).

O3. **All-star vs isolated profiles**: without the isolation condition the
10–11 class shows 9.7× / 5.4× / 2.7× at 0–15″ / 15–30″ / 30–60″ (645 stars),
the 8–10 class 14× at 0–15″ (330 stars) — lower for 8–10 and higher for
10–11 than the isolated profiles. Faint stars near brighter ones inherit
the brighter star's excess.

O4. **Mask coverage of the excess** (inner annuli read from O1, isolated):
V < 6 — all 1 649 near-star tracklets masked, all with bit 12 on every
detection; 6–8 — 56 unmasked / 98 partial / 52 all-masked, **no bit 12**;
8–10 — 19 / 26 / 16, no bit 12. In the backgrounds, the unmasked share is
0 % (V < 4, dominated by S4's bit-6 band), 10 % (4–6), 33 % (6–8), 64 %
(8–10), 90 % (10–11): masks are frequent far from the stars too.

O5. **sharp / SNR / fit RMS in the excess cells vs background** (built
UNKNOWN medians, isolated): sharp max 0.37–0.59 near 4–6 stars vs 0.31
background; 0.33–0.51 near 6–8 vs 0.26; 0.12–0.46 near 8–10 vs 0.08; but
0.14–0.22 near V < 4 vs 0.19 (no difference). Min SNR is higher near 6–8
and 8–10 stars (e.g. 7.5 vs 5.1 for 6–8 at 0–15″), mixed near 4–6 stars
(5.2–7.5 vs 6.3) and lower near V < 4 stars (3.8–7.4 vs 8.4, whose
background is S4's ghost band).
**Fit RMS is 0.24–0.28″ in every cell, near and far.**

O6. **KNOWN objects near stars** (335 objects, AS-022 rule): 22 come within
120″ of a V < 10 star, 25 within 120–240″, 288 farther.

| role | stars | near < 120″ | 120–240″ | ≥ 240″ |
|---|---|---|---|---|
| primary, all quadrants | V < 10 | 1/5 recovered | 5/10 | 69/112 |
| marginal, all quadrants | V < 10 | 3/17 | 3/15 | 51/176 |
| primary, without S3 quadrants | V < 10 | 1/2 | 5/6 | 69/92 |
| marginal, without S3 quadrants | V < 10 | 3/12 | 3/9 | 51/136 |

Closest KNOWN approaches: 16″ and 21″ to V 8–10 stars (both marginal, both
lost before detection in 3 frames); no KNOWN object came within 60″ of a
V < 8 star. 0 built KNOWN tracklets lie within 60″ of any isolated star.

O7. **Counterexamples and confounds**
- All 78 KNOWN objects in the four S3 quadrants are lost (51 at the
  candidate stage, 27 at detection), near stars or not; the strips show
  them visible but barely moving between E1 and E2 (1-minute baseline).
- KNOWN 408599 (S3-q2) is lost because it is blended with an ordinary field
  star in E1/E2 — not a bright-star effect.
- Some strong per-field inner ratios are absent elsewhere: 8–10 stars in
  B-q3, S1-q1, S2 and S3 show none (0 near-star tracklets).
- The two V 10–11 near-star UNKNOWN strips in S4 sit on S4's broad diffuse
  ghost band, not on the faint star's light; S4 also dominates the V < 4
  background (bit-6 band), which makes that background high and its 240–480″
  ratio 0.3.
- The D background strip trk-0264 shows a faint compact source at each
  epoch — not every far-from-star UNKNOWN looks like an artifact.

O8. **Visual sample (25 strips, hash order, agent labels)**: 6/6 UNKNOWN
near V 6–10 stars sit on the star's core, glow, spikes or bleed column;
2/3 near V 10–11 stars sit on the S4 ghost band, 1 unclear; 4 background
UNKNOWN: 1 ghost band, 3 unclear crowded-field (1 possibly a real faint
mover). KNOWN near stars (12): 5 visible moving sources (2 recovered, 2 lost to
the S3 baseline, 1 — 373923 — with only 2/3 detections in the D crowd),
1 blend with a field star (408599), 1 lost E3 detection on the outskirts
of a bright star (288181), 5 faint/unclear in crowded D/S3 fields.

## HYPOTHESES (not tested)

H1. A saturated star's extended light (glow, spikes, bleed, halo texture)
is split into frame-to-frame different catalog sources whose spatial scale
grows with the star's brightness; this is a continuous function of
magnitude and distance, not a halo radius.
H2. The ZTF bit-12 halo mask covers only the brightest part of this
(V ≲ 6; O4), bits 0/8 cover part of the 6–10 range, and ~30 % of the
6–10 excess carries no mask bit at all.
H3. Real asteroids passing within ~1′ of V ≲ 10 stars are lost more often
at the detection stage (blending/glow), as 288181 suggests; the KNOWN
sample cannot confirm or exclude this (O6).
H4. Positive sharp traces extended star light for V 4–10 but not for the
V < 4 sample, whose near-star population is dominated by S4 and whose
background is itself a ghost band.

## CONCLUSIONS

C1. **Magnitude + distance is informative**: the contamination excess is
graded in both variables and reproduces across many stars and quadrants;
a single V ≤ 6.5 cut or a single radius hides 6–10 mag stars (≈ 260
excess built UNKNOWN tracklets within 30–60″ of them) in the control.
C2. **Other features add partial, overlapping and field-dependent
information**: masks mark all V < 6 contamination (bit 12) but only
~70 % of the 6–10 contamination (no bit 12 there) and are common far from
stars; sharp is elevated near V 4–10 stars but not in the V < 4 sample;
min SNR is higher near 6–10 stars only; **fit RMS carries no near/far
difference**. None of
these substitutes for the proximity features.
C3. **KNOWN recovery near bright stars is not characterised**: 14 objects
within 120″ of a V < 10 star outside S3, 2 primaries, none within 60″ of a
V < 8 star. The lower recovery fractions near stars are within small-number
noise. This is a limitation, not evidence of safety.

Confidence: high for the UNKNOWN magnitude × distance pattern (thousands
of tracklets, 262 isolated stars, pre-registered bins); moderate for the
mask/sharp statements (field-dependent); low for anything about real
objects near stars.

## What we can and cannot claim

Can: proximity to Tycho-2 stars down to at least V 10 is a reproducible,
graded descriptor of where UNKNOWN tracklets concentrate; the V ≤ 6.5 /
bit-12 / 367″ picture of AS-032/033 was too narrow; fit RMS does not
separate near-star contamination.
Cannot: that any individual near-star tracklet is an artifact; that real
asteroids near stars are or are not lost by the pipeline; a radius,
magnitude limit or cut for any production use.

## Limitations / unknowns

- KNOWN near-star sample is tiny; a targeted search (fields chosen for an
  asteroid passing a bright star) would be needed.
- Tycho-2 is incomplete beyond V ≈ 11 and lacks the very brightest stars;
  V is an estimate from VT/BT; proper motion ignored.
- Few stars in the brightest classes (3 isolated V < 4, 8 at 4–6), two of
  which dominate their class; S4's ghost band biases the V < 4 background.
- Pairs are stacked over stars; isolation removes the main overlap but the
  backgrounds still contain other stars' light.
- Crowding (D quadrants), seeing (S4: up to 4.7″), mixed filters and the S3
  baseline differ between quadrants and are not modelled.
- Visual labels are the agent's; a human should review the 25 strips.
