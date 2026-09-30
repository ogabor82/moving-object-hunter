# AS-032 findings — masked UNKNOWN tracklets in fields B and D

Inputs: the AS-031 pipeline run (experimental defaults, frozen AS-022
SkyBoT snapshot) on AS-022 fields B (2019-01-25, 565/c13/q3) and D
(2019-06-02, 281/c16/q3). Generated evidence: `as032_masked_tracklets.md`
/ `.json`, strips in `strips/`, visual labels in `visual_review.json`.
Regenerate with `python -m app.validation.masked --out-dir
validation/results/as032` (IRSA; strips are byte-identical across runs).

No filter, score, rank, threshold or rejection was implemented.

## 1. Mask semantics (primary source)

ZTF Science Data System Explanatory Supplement v5.0 (Masci et al. 2020):

- §10.6 (p. 81): PSF-catalog `flags` = −1 for sources on/near an image
  edge; otherwise the **bitwise OR of the science-image mask over a 5×5
  pixel box centred on the source**.
- §10.3 (p. 78): bit 0 = AIRCRAFT/SATELLITE TRACK; bit 8 = SATURATED;
  bit 12 = HALO FROM BRIGHT SOURCE (also: 2 low responsivity, 4 noisy;
  1 and 11 mark pixels containing an extracted source).
- §6.5 step 16 (p. 26): halos ("co-moving ghosts") are masked as a
  **circular region of fixed radius** around Tycho-2 stars with V ≤ 6.5.
  Step 11 (p. 25): tracks are found as linear patterns of bright
  connected pixels.
- §13.3 item 1: masking of artifacts is best effort; unmasked artifacts
  remain in the images and catalogs.

Pipeline check. `catalog_service` maps `flags == -1` → `on_image_edge`,
`flags ≥ 0` → `mask_bits`; AS-031 counts a detection as masked when
`mask_bits != 0`. This matches the documented encoding. What the name
"masked" can hide: the flag describes the **neighbourhood**, not the
detection — bit 12 is a sky region, bit 8 can come from a neighbour's
saturated pixels. Bits 1/11 would also count as "masked" but never occur
in these catalogs (per-bit row counts in the generated report: only bits
0, 2, 4, 8, 12). No code change was needed; the semantics are now
documented in `docs/tracklet_quality_features.md`. AS-031 wording error
corrected: "197 D tracklets with all detections masked" were 197
*flagged* (masked or edge), of which 177 masked.

## 2. Sample

Per field: every built KNOWN tracklet (control, 9 + 9); 8 all-masked
built UNKNOWN tracklets allocated over mask patterns (≥ 1 per pattern,
rest by largest remainder); 2 partially masked and 3 unmasked built
UNKNOWN as within-field comparison. Order inside a stratum: SHA-256 of
`AS-032:<field>:<tracklet id>` — independent of any feature value. 44
strips, each E1 | E2 | E3 through `/api/frames/cutout` (same display
transform as the viewer) with markers from `/api/frames/project` (AS-030
WCS projection): open crosshair on that frame's detection, rings on the
other epochs' detections.

Visual labels were assigned by the implementing agent, **not yet by a
human**; they are recorded per strip with free-text notes.

## OBSERVATIONS

O1. Bit 12 forms exactly one disk per field, at the same sky position in
all three frames, centred on one bright Tycho-2 star: B TYC 1359-2673-1
(VT 5.28, 0.15′ from the bit-12 centroid), D TYC 6246-168-1 (VT 5.93; the
disk is clipped by the quadrant edge). Measured radius 368″ (B) and 367″
(D) — the same in both fields, as the ZSDS rule says. The disks cover
4.1 % (B) and 1.7 % (D) of the quadrant.

O2. Whole-population counts (built tracklets):

| | B | D |
|---|---|---|
| all-masked UNKNOWN | 68 | 177 |
| … entirely inside the halo disk, bit 12 on every detection | 65 | 172 |
| … outside the halo (bit 8 only / bit 0+8) | 3 | 5 |
| KNOWN inside the halo | 0 of 9 | 0 of 9 |
| built UNKNOWN per arcmin², inside / outside halo | 0.592 / 0.0089 | 4.20 / 0.243 |

In B every halo tracklet also carries bit 0 (track) on at least one
detection; 87–97 % of B's bit-0 catalog rows lie inside the halo disk in
each frame (370/426, 191/197, 182/211) — the same place every time, where
a satellite track would move. In D, bit 0 appears on streaks at
different places per frame and on only 1 of the 177.

O3. Every all-masked UNKNOWN tracklet in B (68/68) and 176/177 in D share
at least one detection with another tracklet; KNOWN: 0/9 (B), 8/9 (D,
crowded field).

O4. Visual review of the sample:

| stratum | strips | marker on one moving compact source | markers on stationary structure / nothing | unclear |
|---|---|---|---|---|
| masked UNKNOWN (B 8, D 8) | 16 | 0 | 15 | 1 (D trk-5122) |
| partially masked UNKNOWN | 4 | 0 | 4 | 0 |
| unmasked UNKNOWN, B | 3 | 0 | 2 | 1 |
| unmasked UNKNOWN, D (crowded) | 3 | 0 | 0 | 3 |
| KNOWN (control) | 18 | 14 | 0 | 4 (faint) |

The structures under the masked UNKNOWN markers: saturated-star bleed
columns (B trk-0216, -0282, -0298; D trk-2332, -4946), diffuse glow and
diffraction spikes next to the saturated halo star (B trk-0142, -0459,
-0079, -0226), a bright horizontal linear feature (B trk-0239), and the
blotchy texture of the halo (D trk-5113, -2252, -3150, -5272, -0143).
These structures look the same in all three frames; the three linked
detections are different points on them. Two unmasked B UNKNOWN
tracklets lie on the same kind of bright-star structure without any mask
bit (trk-0419 on a faint diagonal line, trk-0102 on glow/spikes).

O5. KNOWN controls show a compact source at each crosshair that is
absent at the other epochs' rings (14/18; the 4 unclear ones are faint,
min SNR 3.5–7). One KNOWN asteroid, 80429 (D trk-2102), carries bit 12
on E3 because it passes 359″ from the halo star; it is a clear point
source in all frames.

O6. Features (medians, built): masked UNKNOWN vs KNOWN — B min SNR
6.8 vs 6.1, sharp max 0.58 vs 0.01, fit rms 0.252″ vs 0.089″; D 5.5 vs
10.8, 0.42 vs 0.02, 0.266″ vs 0.085″. Unmasked UNKNOWN: B 3.6 / 0.17 /
0.215″, D 3.4 / −0.03 / 0.247″.

## HYPOTHESES (not tested here)

H1. The mechanism is: a bright (V ≈ 5–6) star produces extended,
structured light (halo texture, spikes, bleed columns) that the PSF
catalog breaks into many "sources" whose positions differ from frame to
frame; they fail the 1.5″ stationary match and get linked by the 3-point
line fit. Positive `sharp` (extended) and high SNR fit bright extended
light.
H2. B's bit 0 inside the halo comes from the ZSDS track finder tagging
the star's spikes as linear "tracks" (§6.5 step 11), not from a satellite.
H3. Bright-star proximity, not the mask bit itself, is the underlying
variable: bit 12 covers only V ≤ 6.5 stars within a fixed radius, and O4
shows bleed/spike artifacts both outside the halo (bit 8) and without any
bit (B trk-0419, -0102).
H4. The unmasked UNKNOWN population of the crowded D field (619 built) is
a different failure mode (chance alignment of faint sources in crowding);
nothing here speaks to it.

## CONCLUSIONS (what the evidence supports)

C1. In these two fields the "all detections masked" UNKNOWN population is
**field-specific**: 237 of 245 lie inside the bit-12 disk of the single
V ≈ 5–6 star in the quadrant, and the halo multiplies the built-UNKNOWN
density by ~66× (B) and ~17× (D).
C2. For the sampled tracklets, the masked UNKNOWN linkages are **not
following one moving source**: 15 of 16 put their markers on stationary
bright-star structure (none on a moving compact source; 1 unclear).
These 15 are image artifacts of bright stars linked by the pipeline.
C3. Masked does not mean false: the mask is a neighbourhood/region flag,
and a real asteroid (80429) carries bit 12. Unmasked tracklets can be
artifacts of the same kind.
C4. There is enough evidence to open a **separate research ticket on
bright-star artifacts** (halo/spike/bleed proximity as the variable,
with the mask bits as one input), after a human confirms the visual
labels. The evidence does **not** support a mask-bit rule.

## What we do NOT know

- Whether any real moving object is among the 229 unreviewed halo
  tracklets (sampled 16 of 245 masked; a real asteroid crossing a halo
  would look like 80429 and carry bit 12).
- Whether the result holds for other fields and other bright stars: two
  fields, one halo star each; no POC or C tracklet carries bit 12
  (AS-031), and their catalogs were not checked for halo regions.
- The halo radius parameter (`bshaloradius`) is not stated in the
  supplement; 367–368″ is the measured extent including the 5×5 box.
- H2 (track finder on spikes) is not verified against the mask images.
- The unmasked crowded-field UNKNOWNs (H4) are untouched.
- The visual labels are an agent's; no human review yet.
