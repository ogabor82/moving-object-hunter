# ZTF PSF catalog → SourceDetection mapping

Scope: AS-007. Source product: ZTF single-exposure PSF-fit catalog
(`ztf_<filefracday>_<field>_<filter>_c<ccd>_o_q<qid>_psfcat.fits`),
extension `PSF_CATALOG`, fetched by `fetch_psf_catalog` (AS-006).

Column definitions come from the ZTF Science Data System Explanatory
Supplement, section 10.6 ("Column Definitions in Aperture & PSF-fit Catalog
Files"); photometric calibration from section 10.1.1:
<https://irsa.ipac.caltech.edu/data/ZTF/docs/ztf_explanatory_supplement.pdf>

## Why the PSF catalog (not the aperture `sexcat`)

AS-006 allows either. The PSF catalog was chosen because it is small
(13 columns, ~0.7 MB per quadrant vs. 91 columns, ~4.4 MB for `sexcat`) and
directly carries `snr`. The aperture catalog stays available as a later
cross-check.

## Field mapping

| SourceDetection field     | ZTF source                      | Unit / notes |
|---------------------------|---------------------------------|--------------|
| `source_id`               | `<Observation.product_id>-<sourceid>` | String, unique across observations. `sourceid` is a sequential per-catalog counter. |
| `observation_product_id`  | `Observation.product_id`        | Links the detection to its Observation. |
| `ra`                      | `ra`                            | Degrees, J2000. |
| `dec`                     | `dec`                           | Degrees, J2000. |
| `x`                       | `xpos`                          | Pixels in the native CCD-quadrant image, copied unchanged. |
| `y`                       | `ypos`                          | Pixels in the native CCD-quadrant image, copied unchanged. |
| `magnitude`               | `mag + MAGZP`                   | Calibrated magnitude (PS1 system, AB). See calibration below. |
| `magnitude_error`         | `sigmag`                        | Mag. 1-sigma instrumental uncertainty (~1.086 · sigflux / flux). |
| `snr`                     | `snr`                           | `flux / sigflux`. |
| `on_image_edge`           | `flags == -1`                   | Source on/near an image edge. |
| `mask_bits`               | `flags` if `flags >= 0`, else `0` | Bitwise-OR of the pixel mask bits in a 5×5 region around the source (supplement §10.3). `0` = no mask bits set. |

## Photometric calibration

`mag` in the PSF catalog is instrumental (`-2.5 log10(flux)`). The supplement
(§10.1.1, Eq. 2) gives

    m_cal = m_inst + MAGZP + CLRCOEFF · (m1_PS1 - m2_PS1)

We have no per-source colour, so the colour term is set to 0, as the
supplement recommends when no colour information is available. `MAGZP` comes
from the catalog's primary FITS header. `MAGZPUNC` (~1e-6 mag in practice) is
not added to `magnitude_error`.

Worked example (POC observation, field 535 / c11 / q3, 2018-04-11):
`mag = -5.68`, `MAGZP = 26.308` → `magnitude = 20.63` at `snr = 3.35`.

## Not mapped (available in the raw catalog)

| ZTF column | Why not mapped yet |
|------------|--------------------|
| `flux`, `sigflux` | Detector DN; the calibrated magnitude and snr carry the same information for matching. |
| `chi`      | DAOPhot PSF-fit residual ratio; no downstream consumer yet. |
| `sharp`    | DAOPhot shape metric (`<< 0` cosmic ray, `>> 0` extended). Not a SourceDetection field, but kept beside the detections: `catalog_service.psf_sharp_by_source_id` → `FrameSources.sharp_by_source_id` (finite values, by `source_id`; AS-041). Used only by the M1 review ranking (`sharp_abs_max`, `docs/review_ranking.md`); never a filter. |

## Row validation (AS-009)

A row is rejected, not mapped, when:

- `ra` is outside `[0, 360)` or `dec` is outside `[-90, 90]`;
- any mapped numeric value is NaN or infinite;
- `snr` or `magnitude_error` is negative.

Rows with non-zero `flags` are **not** filtered; the quality fields are passed
through so later steps can decide.

## Open points

- **Pixel origin of `xpos` / `ypos`.** The supplement does not state whether
  they are 0- or 1-based. The values are copied unchanged. This must be
  checked against the image WCS before any overlay or pixel↔sky use.
- **Filtering on flags or `sharp`.** Not decided. This is a science-sensitive
  choice for the matching steps (AS-013+).
