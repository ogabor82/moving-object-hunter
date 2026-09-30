# AS-032 masked-tracklet evidence (generated)

Generated 2026-09-30 20:39 UTC. Source: ZTF Science Data System Explanatory Supplement v5.0 (Masci et al., 2020-06-10), https://irsa.ipac.caltech.edu/data/ZTF/docs/ztf_explanatory_supplement.pdf: §10.3 (p. 78) mask bits, §10.6 (p. 81) PSF-catalog flags and sharp, §6.5 steps 11 and 16 (pp. 25-26) track and halo masking, §13.3 item 1 (unmasked artifacts).

Evidence only; no filter, score, rank or threshold. Interpretation: `as032_findings.md`.

## ZTF mask bits seen in these catalogs (ZSDS §10.3)

- bit 0: AIRCRAFT/SATELLITE TRACK
- bit 2: LOW RESPONSIVITY
- bit 4: NOISY
- bit 8: SATURATED
- bit 12: HALO FROM BRIGHT SOURCE

## B-2019-01-25-565-c13-q3

Halo star TYC 1359-2673-1 (VT 5.283) at (111.93482, 21.44526); measured halo radius 368" (farthest bit-12 detection); halo covers 4.1% of the 2695 arcmin² quadrant. Detections without bit 12 inside that radius: 12.

Catalog rows per mask bit (E1, E2, E3): {0: 426, 4: 4, 8: 301, 12: 668}; {0: 197, 4: 7, 8: 209, 12: 824}; {0: 211, 4: 3, 8: 367, 12: 718}

| stratum | tracklets | inside halo | bit 12 on all | bit 0 on any | shared detection | median min SNR | median sharp max | median fit rms (") |
|---|---|---|---|---|---|---|---|---|
| known | 9 | 0 | 0 | 0 | 0 | 6.080 | 0.008 | 0.089 |
| masked_unknown | 68 | 65 | 65 | 65 | 68 | 6.780 | 0.579 | 0.252 |
| partially_masked_unknown | 8 | 0 | 0 | 0 | 7 | 5.355 | 0.337 | 0.197 |
| unmasked_unknown | 12 | 0 | 0 | 0 | 5 | 3.625 | 0.168 | 0.215 |
| rejected | 397 | 285 | 285 | 281 | 367 | 5.440 | 0.512 | 0.697 |

Built UNKNOWN tracklets per arcmin²: inside halo 0.592, outside 0.0089.

## D-2019-06-02-281-c16-q3

Halo star TYC 6246-168-1 (VT 5.934) at (261.17513, -21.44148); measured halo radius 367" (farthest bit-12 detection); halo covers 1.7% of the 2695 arcmin² quadrant. Detections without bit 12 inside that radius: 117.

Catalog rows per mask bit (E1, E2, E3): {0: 197, 4: 24, 8: 101, 12: 2282}; {0: 132, 4: 34, 8: 113, 12: 1996}; {0: 764, 2: 1, 4: 26, 8: 103, 12: 2289}

| stratum | tracklets | inside halo | bit 12 on all | bit 0 on any | shared detection | median min SNR | median sharp max | median fit rms (") |
|---|---|---|---|---|---|---|---|---|
| known | 9 | 0 | 0 | 0 | 8 | 10.800 | 0.019 | 0.085 |
| masked_unknown | 177 | 172 | 172 | 1 | 176 | 5.500 | 0.421 | 0.266 |
| partially_masked_unknown | 37 | 18 | 0 | 16 | 34 | 4.020 | 0.325 | 0.231 |
| unmasked_unknown | 619 | 0 | 0 | 0 | 472 | 3.380 | -0.030 | 0.247 |
| rejected | 4792 | 1058 | 937 | 108 | 3941 | 3.500 | 0.032 | 0.714 |

Built UNKNOWN tracklets per arcmin²: inside halo 4.197, outside 0.2426.

## Sample and visual review

Rule: Per field: every built KNOWN tracklet; masked_unknown (all detections masked, built) 8 tracklets allocated over mask patterns (>= 1 each, rest by largest remainder); 2 partially masked and 3 unmasked built UNKNOWN. Within a stratum, order by SHA-256('AS-032:<field>:<tracklet>').

Strips: E1 | E2 | E3 cutouts from /api/frames/cutout (per-frame zscale, north up, east left), markers from /api/frames/project: open crosshair on that frame's detection, rings on the other epochs' detections.

| field | tracklet | stratum | mask bits per detection | min SNR | sharp | fit rms | halo dist (") | shared | same source? | visible | context | image |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B | trk-0014 | known (2018 YG5) | – / – / – | 5.9 | -0.18 / 0.07 / -0.11 | 0.052 | 563 | 0 | yes | faint,faint,faint | clean sky | [strips/B_known_trk-0014.png](strips/B_known_trk-0014.png) |
| B | trk-0031 | known (647852) | – / – / – | 5.2 | -0.16 / -0.13 / -0.20 | 0.169 | 927 | 0 | unclear | faint,yes,faint | next to a small star group | [strips/B_known_trk-0031.png](strips/B_known_trk-0031.png) |
| B | trk-0006 | known (144741) | – / – / – | 3.5 | 0.04 / 0.20 / -0.36 | 0.166 | 1288 | 0 | yes | faint,yes,faint | clean sky | [strips/B_known_trk-0006.png](strips/B_known_trk-0006.png) |
| B | trk-0034 | known (126232) | – / – / – | 9.3 | 0.02 / 0.06 / 0.05 | 0.089 | 987 | 0 | yes | yes,yes,yes | clean sky | [strips/B_known_trk-0034.png](strips/B_known_trk-0034.png) |
| B | trk-0405 | known (204140) | – / – / – | 7.9 | 0.04 / -0.04 / -0.09 | 0.057 | 2454 | 0 | yes | yes,yes,faint | clean sky | [strips/B_known_trk-0405.png](strips/B_known_trk-0405.png) |
| B | trk-0040 | known (93745) | – / – / – | 16.5 | -0.01 / -0.04 / -0.10 | 0.051 | 2753 | 0 | yes | yes,yes,yes | clean sky | [strips/B_known_trk-0040.png](strips/B_known_trk-0040.png) |
| B | trk-0144 | known (255879) | – / – / – | 3.9 | -0.33 / -0.06 / -0.14 | 0.127 | 2859 | 0 | unclear | unclear,faint,unclear | near a bright star | [strips/B_known_trk-0144.png](strips/B_known_trk-0144.png) |
| B | trk-0039 | known (43029) | – / – / – | 38.1 | 0.01 / -0.05 / -0.01 | 0.025 | 3019 | 0 | yes | yes,yes,yes | clean sky | [strips/B_known_trk-0039.png](strips/B_known_trk-0039.png) |
| B | trk-0038 | known (140570) | – / – / – | 6.1 | -0.11 / -0.05 / 0.00 | 0.129 | 1926 | 0 | yes | faint,yes,yes | clean sky | [strips/B_known_trk-0038.png](strips/B_known_trk-0038.png) |
| B | trk-0282 | masked_unknown | 8 / 8 / 8 | 8.6 | 0.09 / 0.86 / 0.22 | 0.322 | 658 | 2 | no | no,no,no | saturated-star bleed column (outside halo) | [strips/B_masked_unknown_trk-0282.png](strips/B_masked_unknown_trk-0282.png) |
| B | trk-0239 | masked_unknown | 0,12 / 0,12 / 12 | 5.7 | -0.10 / 0.44 / 0.14 | 0.284 | 68 | 3 | no | no,no,no | horizontal linear feature near halo star | [strips/B_masked_unknown_trk-0239.png](strips/B_masked_unknown_trk-0239.png) |
| B | trk-0142 | masked_unknown | 0,12 / 12 / 0,12 | 3.1 | -0.37 / 0.37 / 0.10 | 0.286 | 40 | 3 | no | no,no,no | halo glow / diffraction spikes | [strips/B_masked_unknown_trk-0142.png](strips/B_masked_unknown_trk-0142.png) |
| B | trk-0459 | masked_unknown | 0,12 / 12 / 0,12 | 6.9 | 0.18 / 0.77 / 0.55 | 0.045 | 20 | 3 | no | no,no,no | saturated core + bleed column | [strips/B_masked_unknown_trk-0459.png](strips/B_masked_unknown_trk-0459.png) |
| B | trk-0226 | masked_unknown | 0,8,12 / 0,12 / 12 | 3.3 | 2.44 / 0.06 / -0.43 | 0.349 | 51 | 2 | no | no,no,no | bleed column / spike / glow | [strips/B_masked_unknown_trk-0226.png](strips/B_masked_unknown_trk-0226.png) |
| B | trk-0298 | masked_unknown | 0,12 / 12 / 8,12 | 6.2 | 0.42 / 0.49 / 0.00 | 0.242 | 14 | 3 | no | no,no,no | bleed column and spikes | [strips/B_masked_unknown_trk-0298.png](strips/B_masked_unknown_trk-0298.png) |
| B | trk-0079 | masked_unknown | 0,12 / 0,12 / 8,12 | 4.2 | -0.22 / 0.26 / 0.70 | 0.311 | 45 | 1 | no | no,no,no | glow + bleed column | [strips/B_masked_unknown_trk-0079.png](strips/B_masked_unknown_trk-0079.png) |
| B | trk-0216 | masked_unknown | 0,8,12 / 0,8,12 / 8,12 | 9.5 | 1.38 / 0.00 / 0.29 | 0.339 | 32 | 2 | no | no,no,no | bleed column | [strips/B_masked_unknown_trk-0216.png](strips/B_masked_unknown_trk-0216.png) |
| B | trk-0329 | partially_masked_unknown | – / – / 8 | 3.1 | -0.19 / -0.20 / -0.88 | 0.319 | 2062 | 1 | no | no,no,no | saturated star glow / bleed | [strips/B_partially_masked_unknown_trk-0329.png](strips/B_partially_masked_unknown_trk-0329.png) |
| B | trk-0098 | partially_masked_unknown | – / – / 8 | 3.2 | -0.23 / -0.27 / 0.42 | 0.165 | 665 | 3 | no | no,no,no | bleed column + diagonal streak | [strips/B_partially_masked_unknown_trk-0098.png](strips/B_partially_masked_unknown_trk-0098.png) |
| B | trk-0419 | unmasked_unknown | – / – / – | 4.1 | 0.06 / 0.22 / -0.35 | 0.341 | 1621 | 1 | no | no,no,no | faint diagonal linear feature (unmasked) | [strips/B_unmasked_unknown_trk-0419.png](strips/B_unmasked_unknown_trk-0419.png) |
| B | trk-0102 | unmasked_unknown | – / – / – | 5.8 | -0.05 / 0.47 / 0.27 | 0.111 | 704 | 1 | no | no,no,no | edge of bright-star glow with spikes (unmasked) | [strips/B_unmasked_unknown_trk-0102.png](strips/B_unmasked_unknown_trk-0102.png) |
| B | trk-0146 | unmasked_unknown | – / – / – | 4.0 | -0.09 / 0.11 / -0.13 | 0.299 | 1930 | 0 | unclear | unclear,no,no | clean sky | [strips/B_unmasked_unknown_trk-0146.png](strips/B_unmasked_unknown_trk-0146.png) |
| D | trk-0923 | known (227423) | – / – / – | 6.1 | -0.33 / 0.02 / -0.06 | 0.107 | 3715 | 3 | yes | yes,yes,yes | crowded star field | [strips/D_known_trk-0923.png](strips/D_known_trk-0923.png) |
| D | trk-0501 | known (135898) | – / – / – | 11.6 | -0.13 / -0.12 / 0.02 | 0.076 | 1246 | 2 | yes | yes,yes,yes | crowded star field | [strips/D_known_trk-0501.png](strips/D_known_trk-0501.png) |
| D | trk-2102 | known (80429) | – / – / 12 | 14.8 | -0.07 / 0.02 / -0.14 | 0.044 | 359 | 2 | yes | yes,yes,yes | halo edge (bit 12 on E3) | [strips/D_known_trk-2102.png](strips/D_known_trk-2102.png) |
| D | trk-5291 | known (284501) | – / – / – | 6.0 | 0.16 / -0.12 / 0.21 | 0.096 | 2057 | 1 | yes | yes,yes,faint | crowded star field | [strips/D_known_trk-5291.png](strips/D_known_trk-5291.png) |
| D | trk-0981 | known (186803) | – / – / – | 13.8 | 0.03 / 0.01 / 0.08 | 0.028 | 2839 | 0 | yes | yes,yes,yes | crowded star field | [strips/D_known_trk-0981.png](strips/D_known_trk-0981.png) |
| D | trk-0838 | known (22969) | – / – / – | 10.8 | -0.07 / -0.15 / -0.07 | 0.100 | 3639 | 2 | yes | faint,yes,faint | crowded star field | [strips/D_known_trk-0838.png](strips/D_known_trk-0838.png) |
| D | trk-3309 | known (7172) | – / – / – | 25.7 | -0.05 / -0.01 / -0.00 | 0.011 | 1692 | 1 | yes | yes,yes,yes | crowded star field | [strips/D_known_trk-3309.png](strips/D_known_trk-3309.png) |
| D | trk-1667 | known (158780) | – / – / – | 7.0 | -0.01 / -0.11 / -0.06 | 0.085 | 1352 | 1 | unclear | faint,faint,faint | crowded star field | [strips/D_known_trk-1667.png](strips/D_known_trk-1667.png) |
| D | trk-2868 | known (427554) | – / – / – | 4.5 | -0.31 / 0.10 / 0.08 | 0.199 | 2351 | 1 | yes | faint,yes,faint | crowded star field | [strips/D_known_trk-2868.png](strips/D_known_trk-2868.png) |
| D | trk-2332 | masked_unknown | 8 / 8 / 8 | 10.3 | -0.01 / -0.62 / 0.63 | 0.218 | 1685 | 2 | no | no,no,no | saturated-star bleed column (outside halo) | [strips/D_masked_unknown_trk-2332.png](strips/D_masked_unknown_trk-2332.png) |
| D | trk-4946 | masked_unknown | 0,8 / 8 / 8 | 9.9 | 0.25 / 0.64 / -1.35 | 0.215 | 1704 | 2 | no | no,no,no | saturated-star bleed column (outside halo) | [strips/D_masked_unknown_trk-4946.png](strips/D_masked_unknown_trk-4946.png) |
| D | trk-5113 | masked_unknown | 12 / 12 / 12 | 8.1 | 0.58 / 0.41 / 0.41 | 0.211 | 93 | 3 | no | no,no,no | inside halo: blotchy halo texture | [strips/D_masked_unknown_trk-5113.png](strips/D_masked_unknown_trk-5113.png) |
| D | trk-2252 | masked_unknown | 12 / 12 / 12 | 7.2 | 0.18 / 0.41 / 0.60 | 0.271 | 91 | 3 | no | no,no,no | inside halo: blotchy halo texture | [strips/D_masked_unknown_trk-2252.png](strips/D_masked_unknown_trk-2252.png) |
| D | trk-5122 | masked_unknown | 12 / 12 / 12 | 4.1 | 0.33 / 0.32 / -0.26 | 0.323 | 107 | 3 | unclear | no,no,unclear | halo outskirts | [strips/D_masked_unknown_trk-5122.png](strips/D_masked_unknown_trk-5122.png) |
| D | trk-3150 | masked_unknown | 12 / 12 / 12 | 5.6 | -0.06 / 0.32 / 0.24 | 0.270 | 76 | 3 | no | no,no,no | inside halo: blotchy halo texture | [strips/D_masked_unknown_trk-3150.png](strips/D_masked_unknown_trk-3150.png) |
| D | trk-5272 | masked_unknown | 12 / 12 / 12 | 5.9 | 0.24 / 0.37 / 0.25 | 0.155 | 115 | 3 | no | no,no,no | inside halo: blotchy halo texture | [strips/D_masked_unknown_trk-5272.png](strips/D_masked_unknown_trk-5272.png) |
| D | trk-0143 | masked_unknown | 12 / 12 / 12 | 5.1 | -0.04 / 0.32 / 0.20 | 0.350 | 110 | 3 | no | no,no,no | inside halo: blotchy halo texture | [strips/D_masked_unknown_trk-0143.png](strips/D_masked_unknown_trk-0143.png) |
| D | trk-3110 | partially_masked_unknown | – / 12 / 12 | 4.6 | -0.40 / -0.00 / 0.32 | 0.174 | 68 | 3 | no | no,no,no | halo edge | [strips/D_partially_masked_unknown_trk-3110.png](strips/D_partially_masked_unknown_trk-3110.png) |
| D | trk-2212 | partially_masked_unknown | – / 12 / 12 | 4.2 | 0.08 / 0.05 / 0.37 | 0.220 | 67 | 3 | no | no,no,no | inside halo: blotchy halo texture | [strips/D_partially_masked_unknown_trk-2212.png](strips/D_partially_masked_unknown_trk-2212.png) |
| D | trk-0883 | unmasked_unknown | – / – / – | 3.0 | -0.52 / -0.22 / -0.33 | 0.215 | 3727 | 2 | unclear | unclear,unclear,unclear | crowded star field | [strips/D_unmasked_unknown_trk-0883.png](strips/D_unmasked_unknown_trk-0883.png) |
| D | trk-3761 | unmasked_unknown | – / – / – | 3.4 | -0.04 / -0.57 / -0.37 | 0.274 | 3361 | 2 | unclear | unclear,faint,unclear | crowded star field | [strips/D_unmasked_unknown_trk-3761.png](strips/D_unmasked_unknown_trk-3761.png) |
| D | trk-2629 | unmasked_unknown | – / – / – | 4.8 | -0.09 / -0.16 / 0.12 | 0.185 | 1239 | 0 | unclear | unclear,faint,unclear | crowded star field | [strips/D_unmasked_unknown_trk-2629.png](strips/D_unmasked_unknown_trk-2629.png) |
