# AS-031 tracklet quality features (descriptive)

Generated 2026-09-30 19:44 UTC; SkyBoT: AS-022 snapshot; config: experimental defaults ({'stationary_tolerance_arcsec': 1.5, 'max_rate_arcsec_per_min': 1.0, 'search_radius_arcsec': 2.0, 'max_residual_arcsec': 0.5, 'match_radius_arcsec': 2.0}).

Measurements only. No feature is a filter, score or rank; group differences are observations, not classifier evidence (see as031_findings.md for selection effects).

## Fields

| field | sources/frame | candidates/frame | tracklets | catalog load (s) | build (s) | raw flags < 0 | detections without sharp |
|---|---|---|---|---|---|---|---|
| POC-2018-04-11-535-c11-q3 | 13455, 12553, 8678 | 3465, 2465, 1060 | 80 | 9.6 | 0.2 | {-1: 102} | 0 |
| B-2019-01-25-565-c13-q3 | 9349, 14211, 11256 | 1557, 4629, 1777 | 494 | 9.4 | 0.6 | {-1: 98} | 0 |
| C-2018-10-06-448-c9-q3 | 7863, 7569, 5117 | 3721, 3578, 2435 | 154 | 6.8 | 0.2 | {-1: 454} | 0 |
| D-2019-06-02-281-c16-q3 | 150253, 131401, 149649 | 15581, 5663, 14939 | 5634 | 62.8 | 14.0 | {-1: 1146} | 0 |

## Control 48606 (1995 DH)

POC-2018-04-11-535-c11-q3, trk-0005, known:

| feature | value |
|---|---|
| tracklet_status | tracklet_built |
| detection_count | 3 |
| min_snr | 5.42 |
| median_snr | 8.23 |
| magnitude_range_mag | 0.3768 |
| magnitude_range_sigma | 1.573 |
| edge_detection_count | 0 |
| masked_detection_count | 0 |
| flagged_detection_count | 0 |
| mask_bits_union | 0 |
| sharp_availability | complete |
| sharp_values | [0.02, 0.144, 0.105] |
| sharp_min | 0.02 |
| sharp_max | 0.144 |
| angular_velocity_arcsec_per_min | 0.4103 |
| position_angle_deg | 347 |
| fit_rms_residual_arcsec | 0.1295 |
| fit_max_residual_arcsec | 0.1815 |


## Group summaries

Cells: median [10th–90th percentile] (n with a value). Built tracklets unless the group says otherwise.

| feature | validation_target_known | control_known | other_known | known_crowded_field | unknown_built:POC-2018-04-11-535-c11-q3 | unknown_built:B-2019-01-25-565-c13-q3 | unknown_built:C-2018-10-06-448-c9-q3 | unknown_built:D-2019-06-02-281-c16-q3 | unknown_rejected:D-2019-06-02-281-c16-q3 |
|---|---|---|---|---|---|---|---|---|---|
| tracklets | 16 | 1 | 15 | 9 | 13 | 88 | 26 | 833 | 4792 |
| min_snr | 14.1 [7.46–29.3] (16) | 5.42 [5.42–5.42] (1) | 5.56 [3.63–8.68] (15) | 10.8 [5.67–17] (9) | 3.29 [3.04–3.98] (13) | 6.05 [3.16–9.15] (88) | 3.2 [3.05–5.12] (26) | 3.52 [3.09–5.87] (833) | 3.5 [3.07–5.81] (4792) |
| median_snr | 18 [10.4–32.7] (16) | 8.23 [8.23–8.23] (1) | 6.85 [5.18–10.6] (15) | 11.6 [6.79–25.3] (9) | 4.4 [3.23–6.41] (13) | 7.83 [4.24–12.9] (88) | 4.03 [3.18–10.3] (26) | 4.38 [3.41–7.93] (833) | 4.37 [3.39–7.73] (4792) |
| magnitude_range_mag | 0.58 [0.148–0.889] (16) | 0.377 [0.377–0.377] (1) | 0.672 [0.365–0.935] (15) | 0.228 [0.119–0.444] (9) | 0.922 [0.603–1.93] (13) | 2.75 [0.282–9.3] (88) | 1.52 [0.698–9.21] (26) | 0.658 [0.222–2.13] (833) | 0.693 [0.228–2.16] (4792) |
| magnitude_range_sigma | 5.07 [1.4–11.9] (16) | 1.57 [1.57–1.57] (1) | 2.4 [1.43–5.52] (15) | 1.68 [0.919–4.34] (9) | 2.16 [1.53–5.34] (13) | 13.9 [1.46–46] (88) | 4.21 [1.8–23.9] (26) | 1.84 [0.551–8.43] (833) | 1.99 [0.57–8.5] (4792) |
| sharp_min | -0.0715 [-0.136–0.0135] (16) | 0.02 [0.02–0.02] (1) | -0.178 [-0.349–-0.071] (15) | -0.132 [-0.312–-0.0396] (9) | -0.234 [-0.423–-0.0448] (13) | 0.001 [-0.507–0.243] (88) | -0.291 [-0.529–0.098] (26) | -0.319 [-0.54–0.106] (833) | -0.322 [-0.536–0.081] (4792) |
| sharp_max | 0.02 [-0.013–0.06] (16) | 0.144 [0.144–0.144] (1) | 0.018 [-0.111–0.17] (15) | 0.019 [-0.0246–0.124] (9) | 0.282 [-0.105–0.71] (13) | 0.491 [0.121–1.15] (88) | 0.129 [-0.141–0.43] (26) | 0.024 [-0.192–0.437] (833) | 0.032 [-0.188–0.435] (4792) |
| angular_velocity_arcsec_per_min | 0.583 [0.49–0.638] (16) | 0.41 [0.41–0.41] (1) | 0.617 [0.537–0.764] (15) | 0.567 [0.472–0.626] (9) | 0.609 [0.0761–0.911] (13) | 0.592 [0.176–0.959] (88) | 0.578 [0.167–0.917] (26) | 0.695 [0.276–0.941] (833) | 0.676 [0.293–0.944] (4792) |
| fit_rms_residual_arcsec | 0.0476 [0.0161–0.0947] (16) | 0.13 [0.13–0.13] (1) | 0.0959 [0.0594–0.168] (15) | 0.0853 [0.0245–0.126] (9) | 0.235 [0.129–0.349] (13) | 0.235 [0.121–0.343] (88) | 0.28 [0.135–0.348] (26) | 0.251 [0.105–0.334] (833) | 0.714 [0.445–0.899] (4792) |
| fit_max_residual_arcsec | 0.0671 [0.0221–0.134] (16) | 0.181 [0.181–0.181] (1) | 0.136 [0.0801–0.236] (15) | 0.121 [0.0346–0.178] (9) | 0.329 [0.181–0.488] (13) | 0.331 [0.17–0.484] (88) | 0.378 [0.183–0.469] (26) | 0.355 [0.148–0.473] (833) | 1.01 [0.63–1.27] (4792) |
| detection_count | 3: 16 | 3: 1 | 3: 15 | 3: 9 | 3: 13 | 3: 88 | 3: 26 | 3: 833 | 3: 4792 |
| flagged_detection_count | 0: 15, 1: 1 | 0: 1 | 0: 15 | 0: 8, 1: 1 | 0: 12, 1: 1 | 0: 12, 1: 7, 2: 1, 3: 68 | 0: 20, 1: 2, 2: 3, 3: 1 | 0: 607, 1: 24, 2: 5, 3: 197 | 0: 3486, 1: 194, 2: 41, 3: 1071 |
| edge_detection_count | 0: 16 | 0: 1 | 0: 15 | 0: 9 | 0: 12, 1: 1 | 0: 88 | 0: 25, 2: 1 | 0: 803, 1: 23, 2: 5, 3: 2 | 0: 4594, 1: 177, 2: 13, 3: 8 |
| tracklets per mask bit | bit 12: 1 | — | — | bit 12: 1 | — | bit 0: 65, bit 8: 46, bit 12: 66 | bit 8: 5 | bit 0: 17, bit 4: 1, bit 8: 10, bit 12: 190 | bit 0: 108, bit 4: 1, bit 8: 59, bit 12: 1079 |
| sharp availability | complete: 16 | complete: 1 | complete: 15 | complete: 9 | complete: 13 | complete: 88 | complete: 26 | complete: 833 | complete: 4792 |

Group definitions:

- `validation_target_known`: KNOWN, best match is a canonical (primary) AS-022 target; built; all fields
- `control_known`: KNOWN, best match is a human-chosen POC control; built
- `other_known`: KNOWN, best match is any other known object (incl. marginal); built; all fields
- `known_crowded_field`: any KNOWN tracklet in D-2019-06-02-281-c16-q3; built
- `unknown_built:POC-2018-04-11-535-c11-q3`: UNKNOWN: no known object matched (not a discovery); built; POC-2018-04-11-535-c11-q3
- `unknown_built:B-2019-01-25-565-c13-q3`: UNKNOWN: no known object matched (not a discovery); built; B-2019-01-25-565-c13-q3
- `unknown_built:C-2018-10-06-448-c9-q3`: UNKNOWN: no known object matched (not a discovery); built; C-2018-10-06-448-c9-q3
- `unknown_built:D-2019-06-02-281-c16-q3`: UNKNOWN: no known object matched (not a discovery); built; D-2019-06-02-281-c16-q3
- `unknown_rejected:D-2019-06-02-281-c16-q3`: UNKNOWN: no known object matched (not a discovery); rejected by the fit residual limit; D-2019-06-02-281-c16-q3
- `ambiguous`: AMBIGUOUS identification; any status; all fields
