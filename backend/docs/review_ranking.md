# Ranked candidate review API (AS-041)

Model: `app/models/review_ranking.py`.
Scorer: `app/services/review_ranking_service.py` (`rank_for_review`).
Endpoint: `GET /api/tracklets/builds/{build_id}/review-ranking`.
Equivalence evidence: `validation/results/as041/`.

## What it is — and is not

The endpoint orders **every** tracklet of one build for human review with
the validated research ranker **M1** (AS-039 frozen, AS-040 sealed
validation: USEFUL, PROTECTED, recall@5 % 0.939 [0.902, 0.975]).

- The rank is **review priority only**. M1 is **not a classifier**.
- `review_priority_score` is **not a probability or confidence** that a
  tracklet is a real or new object. No value of it is a threshold.
- **Nothing is filtered.** Every built tracklet is in `candidates`, every
  rejected tracklet in `unranked`;
  `candidate_count + unranked_count == tracklet_count`. No score, rank,
  top-k or top-5 % cut, mask/flag state, faintness or star proximity
  removes a candidate. The AS-040 "top 5 %" is an evaluation metric, not a
  rejection rule. Pagination or shortlists, if a UI adds them, are
  presentation only.
- The same statements are in every response (`semantics`), together with
  the known limitations (`semantics.known_limitations`).

## M1, exactly as frozen

For the built tracklets of one build (one ZTF quadrant-night):

    score = 0 + Σ_k 0.125 · p_k        (k over the 8 features, frozen order)

| feature | direction | definition (unchanged from AS-038) |
|---|---|---|
| `min_snr` | + | min `SourceDetection.snr` |
| `median_snr` | + | median `SourceDetection.snr` |
| `fit_rms_residual_arcsec` | − | `Tracklet.fit_rms_residual_arcsec` |
| `magnitude_range_mag` | − | max − min `SourceDetection.magnitude` |
| `flagged_detection_count` | − | detections on the edge or masked |
| `masked_detection_count` | − | detections with `mask_bits != 0` |
| `sharp_abs_max` | − | max \|raw ZTF PSF `sharp`\|; missing unless every detection has a finite value |
| `shared_detection_tracklets` | − | other **built** tracklets of the build sharing a detection |

- `p_k` is the oriented mid-rank percentile of the feature among the
  build's built tracklets (higher = reviewed earlier, ties count half). A
  missing value has `p = 0`.
- Floats use the AS-038 table precision (rounded to 6 decimals), so the
  production values equal the table values.
- Only built tracklets are ranked (AS-037: rejected tracklets are never
  ranked); they are returned unranked with their reason.
- **Ties**: equal scores keep the build's tracklet order, so the order is
  deterministic. `review_rank` is 1..n with no gaps.
- **Inputs**: only these 8 features. Identification, SkyBoT, designation,
  known/unknown, bright-star proximity, speed and position angle are never
  read by the scorer (`rank_for_review` has no such argument; tests check
  that motion, position and time do not change a score).

The production constants are checked against
`validation/results/as039/as039_frozen_ranker.json` by a test.

## `sharp` in the production path

`sharp` stays out of the provider-independent `SourceDetection`
(`docs/ztf_psf_catalog_mapping.md`). Instead:

- `catalog_service.psf_sharp_by_source_id` is the single definition of the
  per-detection raw `sharp`: finite values only, keyed by
  `SourceDetection.source_id`. The research loader
  (`validation.data.load_catalog_frames`) now uses the same function.
- `load_frame_sources` (the API build path) keeps these values on each
  `FrameSources.sharp_by_source_id`.
- `TrackletPipelineResult.sharp_by_source_id()` returns them for the
  build's tracklet detections; the build endpoint stores them with the
  build.
- `sharp_abs_max` and `shared_detection_tracklets` are defined once, in
  `quality_service`; `validation.feature_evaluation` imports them.

So the API computes `sharp_abs_max` with the same code and the same raw
values as AS-038/039/040. Nothing is estimated: a detection without a
finite `sharp` makes the feature missing (percentile 0), reported in
`sharp_availability` and `domain_notes`.

## Response

`ReviewRankingResponse`:

- `build_id`, `config`, `observations` (frame sequence, time order);
- `tracklet_count`, `candidate_count`, `unranked_count`;
- `ranker`: the applied spec (inputs, directions, weights, intercept,
  missing percentile, percentile population, tie order);
- `semantics`: review-priority-only flags, statement, known limitations;
- `domain_notes`: how this build differs from the validated unit (frame
  count ≠ 3, more than one quadrant or night, non-default config, missing
  `sharp`). Informational only; nothing is filtered because of it;
- `candidates[]`, in review order:
  - `review_rank` (1 = first), `tracklet_id`, `review_priority_score`;
  - `evidence[]`: per feature `value`, `direction`, `percentile`,
    `weight`, `contribution`;
  - `sharp_availability`;
  - `tracklet`: detections (source id, frame, sky and pixel position,
    magnitude, SNR, flags), motion and fit;
  - `view`: `product_ids`, `center_ra`, `center_dec`, `size_arcsec` (the
    blink-preset cutout rule around the track).
- `unranked[]`: `tracklet_id`, `reason`, `tracklet`, `view`.

**Opening a candidate** in the existing blink / overlay workflow:
`GET /api/frames/cutout?product_id=…&ra=center_ra&dec=center_dec&size_arcsec=…`
for each `view.product_ids`, `POST /api/frames/project` with the
detections' `ra`/`dec`, and `POST /api/tracklets/{tracklet_id}/identify`
for SkyBoT (shown to the reviewer, never fed back into the rank).

The build is kept in the process-local store (latest 20 builds), as for
identify; ranking is deterministic, offline and cheap, so it is computed on
request.

## Known limitations (AS-040, carried into the response)

- Faint objects rank lower (MARGINAL 0.870 vs PRIMARY 0.977).
- Objects near bright stars rank lower (zone 0.786 vs control 0.940,
  n = 14); mask / flag features act partly as a proximity proxy.
- The top of the order is mostly bright-light artefacts and crowded-field
  mislinks (AS-040 F3).
- `fit_rms_residual_arcsec` partly restates the known-object selection.
- Validated on 3-exposure quadrant-nights with the experimental default
  config, main-belt dominated, ≤ 1″/min.
