# AS-022 findings

Run: `as022_validation.json`, generated 2026-09-29T19:56Z, against the
unchanged AS-010–AS-021 pipeline. Tables: `as022_validation.md`. Selection
rule and fields: `../README.md`, `../fields.json`.

## 1. 438973 Masci is not usable with single ZTF exposures

Reproducible with IRSA MOST (`catalog=ztf, obj_name=Masci,
obs_begin=2018-03-17, obs_end=2018-12-31`, the example in the IRSA ZTF
release notes), the IRSA science-image metadata (`maglimit`) and SkyBoT:

- MOST returns 34 exposures on 24 UT nights. Only one night has ≥ 3:
  2018-12-24. Those 3 exposures are in 3 different fields (474/c1/q3,
  1468/c9/q4, 423/c13/q2) and span 7.3 min; the first two are 79 s apart.
- The predicted brightness of Masci is **V = 22.8–23.7** on every one of
  these exposures (MOST `vmag`). SkyBoT gives V = 22.7 (2018-04-09) and
  V = 23.4 (2018-12-24).
- The 5σ limiting magnitude of the same exposures is **17.3–20.8**
  (IRSA `maglimit`), so Masci is ≥ 2 mag below the detection limit in
  every frame.

Masci is therefore not a positive control for a detector that works on
single-exposure catalogs, independently of the frame count. The IRSA
documentation uses it as a MOST API example, not as a detectable object.
The pipeline (min 3 detections, single night) was not changed.

## 2. Validation set

Four frozen quadrant-nights: the POC field and three fields found by a
position/month search near the ecliptic (B: 2019-01-25, C: 2018-10-06,
D: 2019-06-02, crowded low galactic latitude). The pre-registered rule
selected 21 primary and 32 marginal targets (all main-belt objects except
one Amor NEA, 138815, a marginal target); the POC
contributes no rule-based target because its third frame has maglimit
19.24. 48606 (1995 DH) and 285862 (2001 HM48) are human-chosen POC
controls.

Limitations of the set: all rule-based targets move 0.47–0.89"/min (three
fields are near opposition); no fast NEA and no slow (distant or
stationary-point) object is included; one field per observing condition.

## 3. Recovery at the reference config

Reference = the illustrative AS-017..021 values (stationary 1.5", rate
≤ 1.0"/min, search 2.0", fit ≤ 0.5", match 2.0"); it is not a validated
default.

| role | targets | recovered | 2/3 detected | 0-1/3 detected | lost to stationary flag |
|---|---|---|---|---|---|
| primary | 21 | 16 | 2 | 0 | 3 |
| marginal | 32 | 9 | 13 | 8 | 2 |
| control | 2 | 1 (48606) | 1 (285862) | 0 | 0 |

- No target was linked into a tracklet and then misidentified; every
  failure happens before tracklet building (missing detection or
  stationary flag).
- The two primary 2/3 cases (102841 V=17.9, 265244 V=19.4, field B) lie
  5–7" from 13.6 and 16.4 mag stars in the first (g-band) frame: the PSF
  catalog has no separate source there (blending).
- 34 tracklets are identified as KNOWN: 26 validation targets and 8 other
  known objects (fainter or outside the rule); 0 ambiguous.
- Tracklets: 6362 (POC 80, B 494, C 154, D 5634), 992 with accepted fit,
  960 of those UNKNOWN. UNKNOWN is not a discovery; almost all of these
  are expected to be chance alignments of faint sources (see §5).

## 4. Parameter sweep (one at a time around the reference)

| parameter | effect on primary recovery | effect on false candidates (UNKNOWN built) |
|---|---|---|
| max rate | 0.5"/min: 2/21 (targets move 0.47–0.66"/min); 0.75–2.0: 16/21 | 301 → 585 → 960 → 1817 → 2997 |
| stationary tolerance | 0.5": 17/21; 1.0–2.0": 16/21; 3.0": 14/21 | 8035 → 1919 → 960 → 641 → 297 |
| search radius | 16/21 for 0.5–3.0" | 426 (0.5") → 953 (1.0") → 960 (2.0", 3.0") |
| fit max residual | 16/21 for 0.25–2.0" | 264 (0.25") → 960 → 3611 → 6328 |
| match radius | 0.5": 14/21 and 7 ambiguous; 1.0–5.0": 16/21 | unchanged (identification only) |

- The pipeline is most sensitive to the **rate limit** (a hard cut on the
  target population) and the **stationary tolerance** (a direct
  recovery/false-candidate trade-off).
- **Search radius and fit residual** cut false candidates by 2–4× with no
  recovery loss on this set: KNOWN tracklets have fit max residual 0.11"
  [0.03–0.24"], UNKNOWN built ones 0.35" [0.15–0.47"]. Only one-at-a-time
  changes were measured; combined settings were not run.
- A match radius of 0.5" is below the SkyBoT position error of several
  targets (up to 0.99"), so they become AMBIGUOUS by the 05 rule; 1–5"
  gives identical recovery.
- With 21 primary targets, one recovered target is ~5 percentage points;
  differences of 1–2 targets are not significant.

## 5. Candidate-quality features (reference config)

Median [10th–90th percentile], KNOWN (n=34) vs UNKNOWN with accepted fit
(n=960):

| feature | KNOWN | UNKNOWN built |
|---|---|---|
| min SNR | 7.6 [3.9–20.1] | 3.5 [3.1–6.6] |
| median SNR | 10.0 [6.0–25.3] | 4.5 [3.4–8.5] |
| magnitude spread | 0.65 [0.23–0.93] | 0.71 [0.23–2.58] |
| flagged detections | 0 [0–0] | 0 [0–3] |
| min sharp | −0.11 [−0.33–0.01] | −0.31 [−0.54–0.12] |
| fit max residual (") | 0.11 [0.03–0.24] | 0.35 [0.15–0.47] |
| rate ("/min) | 0.60 [0.49–0.66] | 0.68 [0.24–0.94] |

Known objects only: fitted − SkyBoT rate 0.00"/min, PA difference
−0.04° [−0.28–0.23°] – the motion fit and the identification agree.

Promising scoring/filter inputs (not implemented): minimum SNR, fit
residual, flagged detections and very negative `sharp` (cosmic-ray-like),
and large magnitude spread (> ~1 mag, partly caused by mixed filters in B
and C). Rate alone does not separate the groups. None of these was turned
into a hard filter; the separation was measured on 34 known tracklets
only.

## 6. Missing detections (2001 HM48 and the 2-of-3 problem)

2001 HM48 (V=20.0) is detected 0.19" and 0.26" from its prediction in POC
frames 1 and 3; nothing is within 10" in frame 2 (maglimit 20.08). With
`min_detections=3` and 3 frames it cannot form a tracklet.

This is structural for faint objects: 13 of 32 marginal targets (41%) and
2 of 21 primary targets (10%) are detected in exactly 2 of 3 frames. A
K-of-N rule would help only with N ≥ 4 frames (e.g. 3-of-4): a 2-point
"tracklet" has no fit residual and would multiply chance links, which are
already the dominant output. Proposal for later: allow 3-of-N linking for
sequences of ≥ 4 frames; keep `min_detections=3`. Not implemented.

## 7. Stationary-flag losses

3 primary targets (19263, 37933, 12620) lose detections because another
frame has a source within the stationary tolerance at the same position.
The current rule flags a detection as stationary if any other frame has a
source within the tolerance. Options for later (not implemented): require
a match in at least 2 other frames, or check stationary candidates against
the tracklet hypothesis.

## 8. Reproducibility

- IRSA products and metadata are archival; frame ids are frozen.
- SkyBoT answers change: the old and new SkyBoT endpoints already differed
  by ~0.65" for the same object (Phase D), and the database is updated
  daily. The JSON stores every SkyBoT prediction used. For scientific
  regression tests (AS-024) a replay-from-snapshot fixture is needed; this
  was not built in AS-022.
- SkyBoT showed intermittent server errors (SIGBUS, HTTP 200 + flag −1);
  runs rely on the client retry.
