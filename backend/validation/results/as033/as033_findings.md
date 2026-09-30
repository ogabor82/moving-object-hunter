# AS-033 findings — bright-star contamination on independent ZTF fields

Generated evidence: `as033_bright_stars.md` / `.json`, strips in
`strips/`, visual labels in `visual_review.json`, field selection in
`as033_fields.json`, SkyBoT predictions of the new fields in
`as033_skybot.json`. Regenerate (IRSA + VizieR; SkyBoT replayed from the
stored snapshot; strips and numbers are identical across runs):

```
python -m app.validation.bright_stars evidence \
    --fields validation/results/as033/as033_fields.json \
    --out-dir validation/results/as033
```

No filter, exclusion radius, score, rank, threshold or rejection was
implemented. UNKNOWN is not a ground-truth false positive and "masked" is
not a ground-truth artifact.

## Method

**Catalog.** Tycho-2 (VizieR I/259/tyc2), the catalog the ZTF pipeline
uses for halo masking. Position RAmdeg/DEmdeg (ICRS, J2000 mean), else
RA/DE(ICRS) at ~J1991.25; proper motion ignored (≲ few arcsec). V is
estimated as VT − 0.090 (BT − VT); V = VT when BT is missing; no VT →
no magnitude. **Bright = V ≤ 6.5**, the ZSDS halo criterion — not tuned.
Per field, the Tycho-2 cone covers the footprint's circumscribed circle
+ 15′ (so stars just outside the image count).

**Proximity.** Great-circle separation (ICRS) between a tracklet's mean
detection position and the nearest bright star of the cone.

**Bins.** 0–2′, 2–4′, 4–6′, 6–8′, 8–10′, 10–15′, ≥ 15′ (control), fixed
before any evidence run: regular 2′ annuli, one 5′ ring, and the rest of
the quadrant. The AS-032 367″ figure was not used. Bin areas are the
quadrant footprint (first frame, IRSA corners) split by each point's
distance to the nearest bright star on a 500×500 tangent-plane grid.

**Fields.** B and D (AS-022, frozen SkyBoT) as references; four new
fields from the pre-registered rule (committed in `39628c2`, amended in
`77d4ee6` before any evidence existed): Tycho-2 V ≤ 6.5, Dec ≥ −25°,
|β| ≤ 10°, SHA-256 order; earliest ZTF quadrant-night with ≥ 3 exposures
(2018-03-17 … 2021-01-01), first/middle/last exposure as in AS-022;
amendment 1 requires every exposure's archived PSF catalog and science
image (one listed exposure returned 404). Two stars were skipped by the
amendment and logged.

| field | star (V) | inside footprint | filters | minutes | sources/frame | maglimit | seeing |
|---|---|---|---|---|---|---|---|
| B (ref) | TYC 1359-2673-1 (5.24) | yes | zg/zr/zr | 0/31/75 | 9–14 k | 20.4–20.8 | 1.9–2.5″ |
| D (ref) | TYC 6246-168-1 (5.84) | no (just outside) | zr/zr/zr | 0/46/92 | 131–150 k | 20.2–20.3 | 2.4–2.7″ |
| S1 | TYC 676-1224-1 (6.40) | yes | zr/zg/zg | 0/53/94 | 4–8 k | 20.5–21.3 | 1.7–1.8″ |
| S2 | TYC 696-1788-1 (4.75), 696-1789-1 (6.29) | yes | zg/zg/zr | 0/46/102 | 5–9 k | 20.0–20.1 | 1.7–2.3″ |
| S3 | TYC 6301-2457-1 (3.91), 6301-2322-1 (5.85) | yes | zr/zr/zr | **0/1/58** | 68–75 k | 20.6–20.7 | 1.8–2.0″ |
| S4 | TYC 1916-2156-1 (3.56) | yes | zr/zg/zr | 0/95/169 | 9–12 k | 20.1–20.7 | 3.2–3.7″ |

## OBSERVATIONS

O1. **Built UNKNOWN density within 2′ of the bright star vs the ≥ 15′
control** (area-normalised): B ≈ 850×, D ≈ 240×, S1 ≈ 710×, S2 ≈ 3300×,
S4 ≈ 290×. S3 has only 2 built UNKNOWN tracklets in the whole quadrant
(both 2′–6′ from the star), so no ratio exists.

O2. **B/D reproduced with the new method.** B: 65 built UNKNOWN within 4′,
all all-masked with bit 12 (AS-032: 65 inside the halo). D: 190 within
6′ (AS-032: 172 all-masked + 18 partially masked inside the halo).

O3. **Radial extent differs by field** (bins above the control density):
0–2′ in S1 (V 6.40; 2′–4′ holds 1 tracklet); 0–4′ in B (V 5.24; 2′–4′
≈ 9× control), S2 (V 4.75; 2′–4′ ≈ 400×) and D (V 5.84, star just outside
the image; 2′–4′ ≈ 19×, 4′–6′ below control); 0–6′ in S4 (V 3.56; 4′–6′
≈ 7×), with 8′–10′ at ≈ 2× and 6′–8′ below its control.

O4. **Mask state is field-dependent, not a constant of the effect.** In
B, S2 and S4 every built UNKNOWN within 2′ is all-masked with bit 12. In
S1 the 36 tracklets within 2′ carry **no bit 12**: 11 unmasked, 19
partially and 6 all-masked (bits 0 and 8). The S1 star has VT 6.556 but
V ≈ 6.40 by the Tycho conversion.

O5. **S3 is the counterexample for built tracklets**: 0 built UNKNOWN
within 2′, but 139 *rejected* UNKNOWN tracklets there (≈ 124× the
control density of rejected ones). S3 is the only field whose first two
exposures are 1 minute apart (AS-022 first/middle/last rule on a
quadrant-night with a near-duplicate exposure). S3 also has no built
KNOWN tracklet at all.

O6. **Rejected UNKNOWN tracklets follow the same radial pattern**:
0–2′/control density ratio B ≈ 650×, D ≈ 210×, S1 ≈ 490×, S2 ≈ 5200×,
S3 ≈ 120×, S4 ≈ 330×.

O7. **S4 has a second, non-radial population**: the 10′–15′ ring holds 1527
built UNKNOWN (6.1 /arcmin²) and the control 624, most with mask bit 6
(ZSDS §10.3: "ghost from charge spillage", only for OBSMJD ≤ 58779; this
night is MJD 58429). Its bin-6 tracklets have higher median min SNR (8.4)
than those within 2′ (4.7).

O8. **Quality features within 2′ vs control (built UNKNOWN medians)**:
sharp max 0.54 vs 0.11 (B), 0.41 vs −0.02 (D), 0.63 vs 0.24 (S1), 0.60
vs −0.03 (S2), 0.19 vs 0.18 (S4); min SNR 6.8 vs 3.5 (B), 5.2 vs 3.4
(D), 5.3 vs 4.0 (S1), 5.7 vs 3.1 (S2), 4.7 vs 7.2 (S4); fit rms is
0.25–0.27″ in every field and bin (control 0.23–0.25″), i.e. not
different near the star. KNOWN medians (all fields, control): fit rms
0.05–0.11″, sharp max 0.01–0.07.

O9. **KNOWN control**: 0 built KNOWN within 6′ in any field, but the
expected number from each field's control KNOWN density is only 0.08–0.40
per field — the absence carries no information. 33 of 35 built KNOWN
tracklets lie ≥ 10′ from the star; 1 in D at 6′–8′ and 1 in B at 8′–10′.

O10. **Visual sample (31 strips, hash order, agent-labelled)**:

| group | strips | markers on bright-star / saturated-star structure | on nothing / unclear | one moving point source |
|---|---|---|---|---|
| UNKNOWN within 10′ | 20 | 19 (glow, spikes, bleed columns, core, halo rings; S3 streak) | 1 (S1 trk-0026, 6′ out, faint) | 0 |
| UNKNOWN control (≥ 15′) | 6 | 4 (S1 ×2 and S4 ×1 on *other* saturated stars; S4 ×1 on a broad diffuse band with bit 6) | 2 (S2, faint, clean sky) | 0 |
| KNOWN | 5 | 0 | 0 | 5 |

## HYPOTHESES (not tested)

H1. Any saturated star produces extended, frame-to-frame different
catalog "sources" (glow, spikes, bleed trails, halo texture) that pass
the 1.5″ stationary match and are linked by the 3-point line fit; the
affected radius grows with the star's brightness (O3). Stars fainter than
V 6.5 do the same on a smaller scale (control strips in S1/S4).
H2. The ZTF halo mask is applied on a magnitude that excludes the S1 star
(e.g. VT or another V estimate > 6.5), so bit 12 is absent while the
contamination is present (O4).
H3. S3's missing built tracklets are a consequence of the 1-minute E1–E2
baseline (the fit/linking geometry differs), not of the star (O5).
H4. S4's bit-6 population is a distinct ghost failure mode that is not
radial around the selected star.

## CONCLUSIONS

C1. **The AS-032 bright-star failure mode generalises on this sample**: in
5 of 6 fields (B, D, S1, S2, S4 — three of them new) built UNKNOWN
tracklets are concentrated around the V ≤ 6.5 star by factors of ~240–
3300 within 2′ relative to the far control, and every reviewed near-star
UNKNOWN strip in the new fields but one sits on stationary bright-star
structure. S3 shows the same concentration in rejected tracklets only.
C2. **Mask bit 12 is not a reliable marker of it**: the effect appears
without bit 12 around a V 6.40 star (S1), and it extends beyond any fixed
radius — the AS-032 367″ does not transfer (S1 ≲ 2′, S4 ~6′).
C3. **Positive `sharp` is associated with the near-star population in 4
of 5 fields but not in S4**, and fit rms does not distinguish near-star
from control UNKNOWN tracklets. Neither is a separator on this evidence.
C4. The far "control" is itself not artifact-free (fainter saturated
stars, S4 ghosts), so the density ratios are lower bounds on the
contrast with clean sky.

Confidence: high that the concentration is real and repeated on
independent fields (large counts, pre-registered selection, 4 new fields);
moderate on the morphology
generalisation (20 near-star strips, agent-labelled); low on anything
about KNOWN tracklets near stars (expected counts < 0.5 per field).

## What we do NOT know

- Whether real asteroids near bright stars are lost or kept (no KNOWN
  tracklet expected there in this sample).
- The magnitude dependence of the affected radius beyond six stars
  (V 3.56–6.40); stars fainter than V 6.5 are not in the proximity
  variable at all.
- Whether H3 (short baseline) explains S3; only one such field.
- The origin of the S4 bit-6 population (H4) — outside AS-033 scope.
- How the selection's ecliptic band / northern sky biases this; all
  fields are 2018–2019, ZTF public survey, 3 exposures per night.
- Visual labels are the agent's; no human review yet.
