# AS-041 — production M1 vs frozen research M1

Generated 2026-10-02T22:25:41.219543Z — **EQUIVALENT**

Production: `app/services/review_ranking_service.py` (API path). Research: `sealed_validation.frozen_scores` with `as039_frozen_ranker.json` (sha256 `875a0647a61f…`). Production constants equal the frozen ranker: **True**.

## Offline: committed feature tables

| table | quadrant-nights | tracklets | identical scores | identical order | max abs diff | M1 recall@5 % committed / production | M1 AUC committed / production |
|---|---|---|---|---|---|---|---|
| development (AS-038 table) | 56 | 18366 | 56/56 | 56/56 | 0.0e+00 | 0.955224 / 0.955224 | 0.989881 / 0.989881 |
| validation (AS-040 table) | 24 | 10817 | 24/24 | 24/24 | 0.0e+00 | 0.938662 / 0.938662 | 0.989752 / 0.989752 |

## Live: production API path from raw ZTF PSF catalogs

`fetch_observations` → `build_tracklets_from_observations` (`load_frame_sources`, `sharp` kept by `catalog_service.psf_sharp_by_source_id`) → `rank_for_review`, compared with the committed table rows of the same quadrant-night.

| quadrant-night | split | sources / frame | built (prod / table) | rejected (unranked) | sharp complete | same tracklets | feature mismatches | score mismatches | same order | s |
|---|---|---|---|---|---|---|---|---|---|---|
| POC-2018-04-11-535-c11-q3 | development | 13455, 12553, 8678 | 14 / 14 | 66 | 14 | True | 0 | 0 | True | 26.7 |
| C-2018-10-06-448-c9-q3 | development | 7863, 7569, 5117 | 39 / 39 | 115 | 39 | True | 0 | 0 | True | 12.4 |
| D-2019-06-02-281-c16-q3 | development | 150253, 131401, 149649 | 842 / 842 | 4792 | 842 | True | 0 | 0 | True | 82.5 |
| C15-2019-01-04-500-c15-q4 | validation | 7144, 3973, 4478 | 29 / 29 | 495 | 29 | True | 0 | 0 | True | 15.7 |
| C27-2020-11-15-392-c7-q4 | validation | 3275, 6524, 6424 | 44 / 44 | 149 | 44 | True | 0 | 0 | True | 12.8 |
| C11-2020-08-27-447-c2-q1 | validation | 6557, 5006, 3600 | 110 / 110 | 481 | 110 | True | 0 | 0 | True | 19.5 |
| C24-2019-06-29-279-c5-q2 | validation | 95532, 85912, 102293 | 76 / 76 | 479 | 76 | True | 0 | 0 | True | 52.4 |
