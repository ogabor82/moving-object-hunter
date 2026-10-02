# Tracklet quality features (AS-031)

Model: `app/models/quality.py` (`TrackletQualityFeatures`).
Extraction: `app/services/quality_service.py` (`extract_quality_features`).
Evidence runner: `app/validation/quality.py`.

The features are **measurements**. No score, rank, filter or threshold is
derived from them; the extraction reads a `Tracklet` and never changes it,
its fit or any identification. Equal input gives an equal result (pure
function; ties resolve in detection time order).

## Features

| feature | source field(s) | computation | unit | missing |
|---|---|---|---|---|
| `detection_count` | `Tracklet.detections` | count (one detection per frame) | – | never |
| `min_snr` | `SourceDetection.snr` (ZTF `flux/sigflux`) | minimum | – | never |
| `median_snr` | `SourceDetection.snr` | median (mean of the middle two for an even count) | – | never |
| `magnitude_range_mag` | `SourceDetection.magnitude` (`mag + MAGZP`, no colour term) | max − min | mag | never |
| `magnitude_range_sigma` | `magnitude`, `magnitude_error` (`sigmag`) | range / hypot(error of the brightest, error of the faintest detection) | σ | null when both errors are 0 |
| `edge_detection_count` | `SourceDetection.on_image_edge` (raw `flags == -1`) | count true | – | never |
| `masked_detection_count` | `SourceDetection.mask_bits` (raw `flags` if ≥ 0) | count non-zero | – | never |
| `flagged_detection_count` | both of the above | count of detections that are on the edge or masked | – | never |
| `mask_bits_union` | `SourceDetection.mask_bits` | bitwise OR | bit mask | never (0 = none) |
| `sharp_availability` | caller-supplied raw `sharp` | `unavailable` / `partial` / `complete` | – | – |
| `sharp_values` | raw ZTF PSF catalog `sharp`, by `source_id` | per detection, time order | DAOPhot sharpness | `[]` if unavailable; null per detection if absent or non-finite |
| `sharp_min`, `sharp_max` | `sharp_values` | min / max | DAOPhot sharpness | null unless `complete` |
| `angular_velocity_arcsec_per_min` | `Tracklet.angular_velocity_arcsec_per_min` | copied (linear fit) | arcsec/min | never |
| `position_angle_deg` | `Tracklet.position_angle_deg` | copied (east of north) | deg | never |
| `fit_rms_residual_arcsec` | `Tracklet.fit_rms_residual_arcsec` | copied | arcsec | never |
| `fit_max_residual_arcsec` | `Tracklet.fit_max_residual_arcsec` | copied | arcsec | never |

`tracklet_status` (built / rejected) is carried along: rejected tracklets
exceed `max_residual_arcsec` by definition, so fit residuals of the two
statuses are not comparable.

## Mask semantics (checked in AS-032)

ZSDS Explanatory Supplement v5.0 §10.6: the PSF-catalog `flags` is the
bitwise OR of the science-image mask (§10.3) over a 5×5 pixel box centred on
the source. "Masked" here therefore means *some mask bit is set near the
source*, not that the detection itself is bad: bit 12 (halo from bright
source) marks a whole circular region around a Tycho-2 star with V ≤ 6.5,
and bit 8 (saturated) is set when a saturated pixel of a neighbour falls in
the box. Bits 1 and 11 (pixels containing an extracted source) would also
count as masked, but they do not occur in the AS-022 catalogs. See
`validation/results/as032/` for the per-bit evidence.

## Where upstream data is lost

- **`sharp`** (and `chi`) are read from the ZTF PSF catalog
  (`ztf_service.PSF_CATALOG_COLUMNS`) but deliberately not mapped to the
  provider-independent `SourceDetection` (`catalog_service._map_psf_row`;
  `docs/ztf_psf_catalog_mapping.md`, "Not mapped";
  `test_source_detection_exposes_no_ztf_specific_fields`). Since AS-041
  the raw `sharp` is kept beside the detections in both paths, by one
  function (`catalog_service.psf_sharp_by_source_id`, finite values by
  `source_id`): the API build path stores it on
  `FrameSources.sharp_by_source_id` and passes it to the review ranking
  (`docs/review_ranking.md`); the research tooling
  (`validation.data.load_catalog_frames`) passes the same values in.
  Callers that pass nothing (AS-023/024 tooling) still get `unavailable`.
  Non-finite raw values become null. Nothing is estimated. `chi` is still
  dropped.
- **Raw `flags` below −1.** `flags == -1` becomes `on_image_edge`,
  `flags ≥ 0` becomes `mask_bits`; any other negative value would reach the
  domain as a clean detection. `load_catalog_frames` counts such raw values
  (`negative_flag_counts` in the evidence report) so the loss is visible.
- **Magnitude colour term** is 0 (no per-source colour), as in the mapping
  document. When a sequence mixes filters (AS-022 fields B: zg/zr/zr,
  C: zr/zi/zg) the magnitude range includes the source's colour; the
  feature does not correct for it.
