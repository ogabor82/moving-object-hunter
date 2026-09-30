# AS-033 bright-star proximity evidence (generated)

Generated 2026-09-30 21:26 UTC. Catalog: Tycho-2 (Høg et al. 2000), VizieR I/259/tyc2; V = VT - 0.090 (BT - VT); bright = V <= 6.5. Proximity = great-circle separation of the tracklet's mean detection position from the nearest bright star. Descriptive only; no filter, radius, score or threshold. Interpretation: `as033_findings.md`.

Field selection (pre-registered, commit before evidence): Tycho-2 stars with V <= 6.5, Dec >= -25 deg, |ecliptic latitude| <= 10 deg, ordered by SHA-256('AS-033:<Tycho id>'). For each star in turn, the IRSA ZTF science metadata covering the star's position between 2018-03-17 and 2021-01-01 is grouped by (field, CCD, quadrant, UTC date); the earliest group with >= 3 exposures is taken, and its first, middle ((n-1)//2) and last exposure form the sequence (the AS-022 rule). Stars without such a group are skipped and logged. The first 4 stars that yield a sequence are used. No pipeline output, source count or UNKNOWN count is looked at. Amendment 1 (2026-09-30, before any evidence output existed): a sequence qualifies only if the PSF catalog and science image of all three exposures exist in the IRSA archive (HTTP HEAD 200); otherwise the star is skipped and logged. Reason: IRSA metadata listed an exposure (pid 579341801615) whose products return 404.

## Fields

| field | role | CCD/quadrant | filters | minutes | sources/frame | maglimit | seeing (") | bright stars (V) in cone | inside footprint | near/control UNKNOWN density |
|---|---|---|---|---|---|---|---|---|---|---|
| B-2019-01-25-565-c13-q3 | reference | field 565 c13 q3 | zg/zr/zr | 0/31/75 | 9349/14211/11256 | 20.8/20.8/20.4 | 2.5/1.9/2.4 | TYC 1359-2673-1 (5.24) | 1 | 46.16 |
| D-2019-06-02-281-c16-q3 | reference | field 281 c16 q3 | zr/zr/zr | 0/46/92 | 150253/131401/149649 | 20.3/20.2/20.3 | 2.4/2.7/2.4 | TYC 6246-168-1 (5.84) | 0 | 7.10 |
| S1-2018-09-19-508-c10-q4 | new | field 508 c10 q4 | zr/zg/zg | 0/53/94 | 8283/5833/4234 | 21.1/21.3/20.5 | 1.8/1.8/1.7 | TYC 676-1224-1 (6.40) | 1 | 30.05 |
| S2-2018-09-27-509-c14-q4 | new | field 509 c14 q4 | zg/zg/zr | 0/46/102 | 5199/5802/8821 | 20.0/20.1/20.0 | 1.7/1.7/2.3 | TYC 696-1788-1 (4.75), TYC 696-1789-1 (6.29) | 1 | 142.85 |
| S3-2019-07-01-335-c7-q1 | new | field 335 c7 q1 | zr/zr/zr | 0/1/58 | 68956/68403/74631 | 20.6/20.6/20.7 | 2.0/2.0/1.8 | TYC 6301-2322-1 (5.85), TYC 6301-2457-1 (3.91) | 1 | – |
| S4-2018-11-07-615-c5-q3 | new | field 615 c5 q3 | zr/zg/zr | 0/95/169 | 11421/9345/11594 | 20.1/20.7/20.4 | 3.7/3.3/3.2 | TYC 1916-2156-1 (3.56) | 1 | 18.06 |

## B-2019-01-25-565-c13-q3

Tracklets with no bright star in the cone: 0.

| separation | area (arcmin²) | UNKNOWN built | density /arcmin² | unmasked / partial / all-masked | bit 12 on all | tracklets per mask bit | UNKNOWN rejected | KNOWN built | KNOWN density | UNKNOWN min SNR | UNKNOWN sharp max | UNKNOWN fit rms (") | KNOWN min SNR | KNOWN sharp max | KNOWN fit rms (") |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0'-2' | 12.6 | 63 | 5.0147 | 0 / 0 / 63 | 63 | 0: 63, 8: 35, 12: 63 | 280 | 0 | 0.0000 | 6.8 (63) | 0.54 (63) | 0.253 (63) | – | – | – |
| 2'-4' | 37.7 | 2 | 0.0530 | 0 / 0 / 2 | 2 | 0: 2, 8: 1, 12: 2 | 3 | 0 | 0.0000 | 6.5 (2) | 0.72 (2) | 0.181 (2) | – | – | – |
| 4'-6' | 55.5 | 0 | 0.0000 | 0 / 0 / 0 | 0 | – | 2 | 0 | 0.0000 | – | – | – | – | – | – |
| 6'-8' | 64.2 | 1 | 0.0156 | 0 / 1 / 0 | 0 | 12: 1 | 0 | 0 | 0.0000 | 3.4 (1) | -0.14 (1) | 0.087 (1) | – | – | – |
| 8'-10' | 76.1 | 1 | 0.0131 | 0 / 1 / 0 | 0 | 8: 1 | 1 | 1 | 0.0131 | 8.9 (1) | 0.23 (1) | 0.128 (1) | 5.9 (1) | 0.07 (1) | 0.052 (1) |
| 10'-15' | 243.7 | 8 | 0.0328 | 2 / 3 / 3 | 0 | 8: 6 | 35 | 0 | 0.0000 | 6.4 (8) | 0.59 (8) | 0.197 (8) | – | – | – |
| >=15' | 2204.7 | 13 | 0.0059 | 10 / 3 / 0 | 0 | 8: 3 | 76 | 8 | 0.0036 | 3.5 (13) | 0.11 (13) | 0.225 (13) | 7.0 (8) | 0.01 (8) | 0.108 (8) |

## D-2019-06-02-281-c16-q3

Tracklets with no bright star in the cone: 0.

| separation | area (arcmin²) | UNKNOWN built | density /arcmin² | unmasked / partial / all-masked | bit 12 on all | tracklets per mask bit | UNKNOWN rejected | KNOWN built | KNOWN density | UNKNOWN min SNR | UNKNOWN sharp max | UNKNOWN fit rms (") | KNOWN min SNR | KNOWN sharp max | KNOWN fit rms (") |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0'-2' | 2.1 | 121 | 57.6548 | 0 / 18 / 103 | 103 | 12: 121 | 622 | 0 | 0.0000 | 5.2 (121) | 0.41 (121) | 0.270 (121) | – | – | – |
| 2'-4' | 14.3 | 65 | 4.5330 | 0 / 0 / 65 | 65 | 12: 65 | 403 | 0 | 0.0000 | 5.1 (65) | 0.43 (65) | 0.251 (65) | – | – | – |
| 4'-6' | 26.9 | 4 | 0.1486 | 0 / 0 / 4 | 4 | 12: 4 | 43 | 0 | 0.0000 | 3.5 (4) | -0.14 (4) | 0.225 (4) | – | – | – |
| 6'-8' | 35.4 | 3 | 0.0847 | 3 / 0 / 0 | 0 | – | 50 | 1 | 0.0282 | 3.7 (3) | 0.01 (3) | 0.276 (3) | 14.8 (1) | 0.02 (1) | 0.044 (1) |
| 8'-10' | 39.7 | 11 | 0.2774 | 11 / 0 / 0 | 0 | – | 65 | 0 | 0.0000 | 3.2 (11) | -0.06 (11) | 0.290 (11) | – | – | – |
| 10'-15' | 125.3 | 34 | 0.2713 | 34 / 0 / 0 | 0 | – | 163 | 0 | 0.0000 | 3.3 (34) | -0.07 (34) | 0.244 (34) | – | – | – |
| >=15' | 2451.1 | 595 | 0.2427 | 571 / 19 / 5 | 0 | 0: 17, 4: 1, 8: 10 | 3446 | 8 | 0.0033 | 3.4 (595) | -0.02 (595) | 0.247 (595) | 8.9 (8) | 0.02 (8) | 0.091 (8) |

## S1-2018-09-19-508-c10-q4

Tracklets with no bright star in the cone: 0.

| separation | area (arcmin²) | UNKNOWN built | density /arcmin² | unmasked / partial / all-masked | bit 12 on all | tracklets per mask bit | UNKNOWN rejected | KNOWN built | KNOWN density | UNKNOWN min SNR | UNKNOWN sharp max | UNKNOWN fit rms (") | KNOWN min SNR | KNOWN sharp max | KNOWN fit rms (") |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0'-2' | 12.6 | 36 | 2.8581 | 11 / 19 / 6 | 0 | 0: 15, 8: 22 | 169 | 0 | 0.0000 | 5.3 (36) | 0.63 (36) | 0.268 (36) | – | – | – |
| 2'-4' | 37.7 | 1 | 0.0265 | 0 / 1 / 0 | 0 | 8: 1 | 1 | 0 | 0.0000 | 3.9 (1) | 0.02 (1) | 0.157 (1) | – | – | – |
| 4'-6' | 62.8 | 0 | 0.0000 | 0 / 0 / 0 | 0 | – | 0 | 0 | 0.0000 | – | – | – | – | – | – |
| 6'-8' | 88.0 | 1 | 0.0114 | 1 / 0 / 0 | 0 | – | 4 | 0 | 0.0000 | 3.1 (1) | -0.20 (1) | 0.288 (1) | – | – | – |
| 8'-10' | 113.2 | 0 | 0.0000 | 0 / 0 / 0 | 0 | – | 1 | 0 | 0.0000 | – | – | – | – | – | – |
| 10'-15' | 392.9 | 2 | 0.0051 | 1 / 1 / 0 | 0 | 0: 1 | 7 | 1 | 0.0026 | 3.3 (2) | 0.13 (2) | 0.260 (2) | 3.7 (1) | 0.04 (1) | 0.127 (1) |
| >=15' | 1988.3 | 8 | 0.0040 | 4 / 1 / 3 | 0 | 8: 4 | 54 | 5 | 0.0025 | 4.0 (8) | 0.24 (8) | 0.249 (8) | 4.9 (5) | 0.07 (5) | 0.046 (5) |

## S2-2018-09-27-509-c14-q4

Tracklets with no bright star in the cone: 0.

| separation | area (arcmin²) | UNKNOWN built | density /arcmin² | unmasked / partial / all-masked | bit 12 on all | tracklets per mask bit | UNKNOWN rejected | KNOWN built | KNOWN density | UNKNOWN min SNR | UNKNOWN sharp max | UNKNOWN fit rms (") | KNOWN min SNR | KNOWN sharp max | KNOWN fit rms (") |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0'-2' | 12.5 | 73 | 5.8186 | 0 / 0 / 73 | 73 | 0: 51, 8: 54, 12: 73 | 419 | 0 | 0.0000 | 5.7 (73) | 0.60 (73) | 0.247 (73) | – | – | – |
| 2'-4' | 42.8 | 30 | 0.7017 | 0 / 0 / 30 | 30 | 0: 29, 8: 29, 12: 30 | 90 | 0 | 0.0000 | 7.2 (30) | 0.60 (30) | 0.234 (30) | – | – | – |
| 4'-6' | 82.6 | 1 | 0.0121 | 0 / 0 / 1 | 1 | 0: 1, 8: 1, 12: 1 | 12 | 0 | 0.0000 | 9.7 (1) | 1.12 (1) | 0.329 (1) | – | – | – |
| 6'-8' | 120.6 | 0 | 0.0000 | 0 / 0 / 0 | 0 | – | 1 | 0 | 0.0000 | – | – | – | – | – | – |
| 8'-10' | 158.2 | 0 | 0.0000 | 0 / 0 / 0 | 0 | – | 0 | 0 | 0.0000 | – | – | – | – | – | – |
| 10'-15' | 561.3 | 3 | 0.0053 | 2 / 1 / 0 | 0 | 8: 1 | 7 | 0 | 0.0000 | 3.1 (3) | 0.14 (3) | 0.307 (3) | – | – | – |
| >=15' | 1717.0 | 3 | 0.0018 | 3 / 0 / 0 | 0 | – | 11 | 1 | 0.0006 | 3.1 (3) | -0.03 (3) | 0.237 (3) | 6.1 (1) | 0.03 (1) | 0.045 (1) |

## S3-2019-07-01-335-c7-q1

Tracklets with no bright star in the cone: 0.

| separation | area (arcmin²) | UNKNOWN built | density /arcmin² | unmasked / partial / all-masked | bit 12 on all | tracklets per mask bit | UNKNOWN rejected | KNOWN built | KNOWN density | UNKNOWN min SNR | UNKNOWN sharp max | UNKNOWN fit rms (") | KNOWN min SNR | KNOWN sharp max | KNOWN fit rms (") |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0'-2' | 12.6 | 0 | 0.0000 | 0 / 0 / 0 | 0 | – | 139 | 0 | 0.0000 | – | – | – | – | – | – |
| 2'-4' | 37.8 | 1 | 0.0265 | 0 / 0 / 1 | 1 | 0: 1, 12: 1 | 21 | 0 | 0.0000 | 4.9 (1) | 0.15 (1) | 0.392 (1) | – | – | – |
| 4'-6' | 62.8 | 1 | 0.0159 | 0 / 0 / 1 | 1 | 12: 1 | 56 | 0 | 0.0000 | 5.6 (1) | 0.50 (1) | 0.394 (1) | – | – | – |
| 6'-8' | 88.0 | 0 | 0.0000 | 0 / 0 / 0 | 0 | – | 20 | 0 | 0.0000 | – | – | – | – | – | – |
| 8'-10' | 113.1 | 0 | 0.0000 | 0 / 0 / 0 | 0 | – | 0 | 0 | 0.0000 | – | – | – | – | – | – |
| 10'-15' | 369.3 | 0 | 0.0000 | 0 / 0 / 0 | 0 | – | 7 | 0 | 0.0000 | – | – | – | – | – | – |
| >=15' | 2012.6 | 0 | 0.0000 | 0 / 0 / 0 | 0 | – | 179 | 0 | 0.0000 | – | – | – | – | – | – |

## S4-2018-11-07-615-c5-q3

Tracklets with no bright star in the cone: 0.

| separation | area (arcmin²) | UNKNOWN built | density /arcmin² | unmasked / partial / all-masked | bit 12 on all | tracklets per mask bit | UNKNOWN rejected | KNOWN built | KNOWN density | UNKNOWN min SNR | UNKNOWN sharp max | UNKNOWN fit rms (") | KNOWN min SNR | KNOWN sharp max | KNOWN fit rms (") |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0'-2' | 12.5 | 1030 | 82.0937 | 0 / 0 / 1030 | 1030 | 0: 1010, 8: 460, 12: 1030 | 6265 | 0 | 0.0000 | 4.7 (1030) | 0.19 (1030) | 0.251 (1030) | – | – | – |
| 2'-4' | 37.7 | 123 | 3.2630 | 0 / 0 / 123 | 123 | 0: 118, 8: 59, 12: 123 | 610 | 0 | 0.0000 | 5.1 (123) | 0.18 (123) | 0.239 (123) | – | – | – |
| 4'-6' | 60.3 | 121 | 2.0074 | 0 / 3 / 118 | 109 | 0: 93, 8: 43, 12: 121 | 714 | 0 | 0.0000 | 4.6 (121) | 0.18 (121) | 0.236 (121) | – | – | – |
| 6'-8' | 68.3 | 12 | 0.1757 | 0 / 1 / 11 | 0 | 0: 11, 8: 11, 12: 7 | 145 | 0 | 0.0000 | 12.3 (12) | 0.07 (12) | 0.275 (12) | – | – | – |
| 8'-10' | 79.4 | 46 | 0.5791 | 0 / 1 / 45 | 0 | 0: 45, 8: 46 | 190 | 0 | 0.0000 | 12.1 (46) | 0.06 (46) | 0.266 (46) | – | – | – |
| 10'-15' | 251.4 | 1527 | 6.0742 | 3 / 35 / 1489 | 0 | 0: 59, 5: 37, 6: 1428, 8: 59 | 9035 | 2 | 0.0080 | 8.4 (1527) | 0.19 (1527) | 0.252 (1527) | 15.3 (2) | 0.07 (2) | 0.127 (2) |
| >=15' | 2185.3 | 624 | 0.2855 | 16 / 64 / 544 | 0 | 0: 75, 5: 6, 6: 527, 8: 75 | 3350 | 8 | 0.0037 | 7.2 (624) | 0.18 (624) | 0.250 (624) | 7.6 (8) | 0.05 (8) | 0.087 (8) |

## Visual sample (new fields)

Per field: up to 6 built UNKNOWN within 10' of a bright star, 2 built UNKNOWN beyond 15', 2 built KNOWN; SHA-256 order. Strips as in AS-032.

| field | tracklet | group | separation (") | mask | min SNR | sharp max | fit rms | same source? | context | image |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 | trk-0261 | near_unknown | 31 | unmasked | 4.4 | 0.68 | 0.263 | no | bright-star glow / spikes / bleed | [strips/S1_near_unknown_trk-0261.png](strips/S1_near_unknown_trk-0261.png) |
| S1 | trk-0274 | near_unknown | 29 | partially_masked | 5.3 | 0.89 | 0.296 | no | bleed column / glow | [strips/S1_near_unknown_trk-0274.png](strips/S1_near_unknown_trk-0274.png) |
| S1 | trk-0243 | near_unknown | 25 | partially_masked | 5.9 | 0.59 | 0.339 | no | bright-star glow / spikes | [strips/S1_near_unknown_trk-0243.png](strips/S1_near_unknown_trk-0243.png) |
| S1 | trk-0270 | near_unknown | 25 | unmasked | 4.4 | 0.71 | 0.190 | no | bright-star glow / bleed | [strips/S1_near_unknown_trk-0270.png](strips/S1_near_unknown_trk-0270.png) |
| S1 | trk-0026 | near_unknown | 364 | unmasked | 3.1 | -0.20 | 0.288 | unclear | clean sky (6' from the star) | [strips/S1_near_unknown_trk-0026.png](strips/S1_near_unknown_trk-0026.png) |
| S1 | trk-0192 | near_unknown | 18 | partially_masked | 4.8 | 0.73 | 0.311 | no | bright-star core / spikes | [strips/S1_near_unknown_trk-0192.png](strips/S1_near_unknown_trk-0192.png) |
| S1 | trk-0060 | control_unknown | 911 | partially_masked | 5.1 | 1.09 | 0.249 | no | another saturated star (control region) | [strips/S1_control_unknown_trk-0060.png](strips/S1_control_unknown_trk-0060.png) |
| S1 | trk-0174 | control_unknown | 932 | all_masked | 7.9 | 1.85 | 0.154 | no | another saturated star core (control region) | [strips/S1_control_unknown_trk-0174.png](strips/S1_control_unknown_trk-0174.png) |
| S1 | trk-0027 | known | 877 | unmasked | 3.7 | 0.04 | 0.127 | yes | clean sky | [strips/S1_known_trk-0027.png](strips/S1_known_trk-0027.png) |
| S1 | trk-0037 | known | 1540 | unmasked | 3.5 | -0.04 | 0.198 | yes | clean sky | [strips/S1_known_trk-0037.png](strips/S1_known_trk-0037.png) |
| S2 | trk-0105 | near_unknown | 181 | all_masked | 7.8 | 0.90 | 0.209 | no | long bleed column | [strips/S2_near_unknown_trk-0105.png](strips/S2_near_unknown_trk-0105.png) |
| S2 | trk-0415 | near_unknown | 95 | all_masked | 7.3 | 1.40 | 0.158 | no | bleed column + spikes | [strips/S2_near_unknown_trk-0415.png](strips/S2_near_unknown_trk-0415.png) |
| S2 | trk-0448 | near_unknown | 164 | all_masked | 7.2 | 0.02 | 0.211 | no | bleed column | [strips/S2_near_unknown_trk-0448.png](strips/S2_near_unknown_trk-0448.png) |
| S2 | trk-0444 | near_unknown | 213 | all_masked | 7.3 | 0.01 | 0.200 | no | bleed column | [strips/S2_near_unknown_trk-0444.png](strips/S2_near_unknown_trk-0444.png) |
| S2 | trk-0481 | near_unknown | 89 | all_masked | 5.4 | 0.66 | 0.334 | no | spikes / bleed / glow | [strips/S2_near_unknown_trk-0481.png](strips/S2_near_unknown_trk-0481.png) |
| S2 | trk-0245 | near_unknown | 198 | all_masked | 7.2 | 1.13 | 0.221 | no | bleed column | [strips/S2_near_unknown_trk-0245.png](strips/S2_near_unknown_trk-0245.png) |
| S2 | trk-0020 | control_unknown | 964 | unmasked | 3.1 | -0.08 | 0.098 | unclear | clean sky; E3 next to a galaxy/star | [strips/S2_control_unknown_trk-0020.png](strips/S2_control_unknown_trk-0020.png) |
| S2 | trk-0001 | control_unknown | 1832 | unmasked | 3.1 | 0.02 | 0.237 | unclear | clean sky | [strips/S2_control_unknown_trk-0001.png](strips/S2_control_unknown_trk-0001.png) |
| S2 | trk-0030 | known | 949 | unmasked | 6.1 | 0.03 | 0.045 | yes | clean sky | [strips/S2_known_trk-0030.png](strips/S2_known_trk-0030.png) |
| S3 | trk-0323 | near_unknown | 255 | all_masked | 5.6 | 0.50 | 0.394 | no | glow of a saturated star (4' from the bright star) | [strips/S3_near_unknown_trk-0323.png](strips/S3_near_unknown_trk-0323.png) |
| S3 | trk-0252 | near_unknown | 137 | all_masked | 4.9 | 0.15 | 0.392 | no | linear streak / glow | [strips/S3_near_unknown_trk-0252.png](strips/S3_near_unknown_trk-0252.png) |
| S4 | trk-13016 | near_unknown | 41 | all_masked | 7.8 | 0.06 | 0.207 | no | bleed column / core of the bright star | [strips/S4_near_unknown_trk-13016.png](strips/S4_near_unknown_trk-13016.png) |
| S4 | trk-6254 | near_unknown | 72 | all_masked | 3.8 | 0.37 | 0.246 | no | bright-star glow / spikes | [strips/S4_near_unknown_trk-6254.png](strips/S4_near_unknown_trk-6254.png) |
| S4 | trk-2209 | near_unknown | 28 | all_masked | 5.1 | 0.32 | 0.163 | no | bright-star core, spikes, halo rings | [strips/S4_near_unknown_trk-2209.png](strips/S4_near_unknown_trk-2209.png) |
| S4 | trk-7573 | near_unknown | 57 | all_masked | 4.0 | 0.11 | 0.251 | no | next to bleed column | [strips/S4_near_unknown_trk-7573.png](strips/S4_near_unknown_trk-7573.png) |
| S4 | trk-14724 | near_unknown | 61 | all_masked | 5.7 | 0.08 | 0.211 | no | diffuse glow / spike | [strips/S4_near_unknown_trk-14724.png](strips/S4_near_unknown_trk-14724.png) |
| S4 | trk-4258 | near_unknown | 120 | all_masked | 3.1 | 0.47 | 0.196 | no | glow / spikes | [strips/S4_near_unknown_trk-4258.png](strips/S4_near_unknown_trk-4258.png) |
| S4 | trk-14449 | control_unknown | 1952 | all_masked | 4.3 | -0.01 | 0.343 | no | bleed column of another star (control region) | [strips/S4_control_unknown_trk-14449.png](strips/S4_control_unknown_trk-14449.png) |
| S4 | trk-0731 | control_unknown | 924 | all_masked | 4.4 | 0.12 | 0.090 | no | broad diffuse vertical band (control region) | [strips/S4_control_unknown_trk-0731.png](strips/S4_control_unknown_trk-0731.png) |
| S4 | trk-5013 | known | 1271 | unmasked | 6.1 | 0.04 | 0.099 | yes | clean sky | [strips/S4_known_trk-5013.png](strips/S4_known_trk-5013.png) |
| S4 | trk-6895 | known | 1275 | unmasked | 7.2 | 0.25 | 0.310 | yes | clean sky | [strips/S4_known_trk-6895.png](strips/S4_known_trk-6895.png) |
