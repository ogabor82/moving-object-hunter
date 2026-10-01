# AS-035 known-object recovery near bright stars (generated)

Generated 2026-10-01 18:19 UTC. Descriptive only; no filter, radius, score, rank or threshold. Interpretation: `as035_findings.md`.

Pre-registration (commit fa4cd97): Populations: N = star-driven search (Tycho-2 V<6 and 6-8 stars, Dec>=-25, |beta|<=10, SHA-256('AS-035:<id>') order, alternating classes, 12 quadrant-nights per class, <=60 stars and <=15 nights per star; trigger = SkyBoT object passing within 120" of the star at E1/E2/E3 that meets the AS-022 target rule, rate <= 1"/min and baseline rule, inside the footprint); R = the 26 AS-034 quadrants (not blind). Sequence rule: E1 first, E3 last within 150 min, E2 closest to the midpoint with >=15 min gaps, archived products. Targets: AS-022 rule (primary/marginal). Eligibility: rate <= 1.0"/min; every pairwise predicted displacement >= 3.0" (2x stationary tolerance); failures form their own strata. Detectability: band offsets g +0.33, r -0.22, i -0.37; local 5-sigma depth from PSF sources (3<=snr<=20) within 60". Strata: classes V<6, 6-8, 8-10 x closest approach 0-30-60-120-240"; zone = <120" of V<6, <60" of 6-8, <30" of 8-10; control = >=480" from V<10 and >=60" from V10-11. Trace: expected position, detection (2.0"), stationary/moving, association, fit, identification; first failure. Claim rule: zone PRIMARY eligible n>=10, Fisher two-sided p<0.05 (lower in zone) and MH odds ratio over shared quadrants < 1; else not demonstrated. Strips: SHA-256 order, <=8 recovered + <=8 lost within 120" of V<10, 2+2 controls, plus 288181/408599 if R targets. No outcome was looked at.

Recovery cells: recovered/n (%, Wilson 95 % interval). Stage columns: first failure detection / stationary / association / fit / identification.

## Population

| pop | field | origin | filters | minutes | sources/frame | maglimit | catalog depth | seeing | stars V<=11 by class | targets | tracklets |
|---|---|---|---|---|---|---|---|---|---|---|---|
| N | N1-2018-11-25-468-c12-q1 | search V<6 TYC 243-1975-1 | zr/zr/zr | 0/89/118 | 2561/3477/3073 | 19.3/19.8/19.5 | 19.1/19.8/19.4 | 3.9/2.6/3.5 | 0/1/0/8/17 | 1 | 604 |
| N | N2-2019-11-05-564-c1-q2 | search V<6 TYC 1344-1281-1 | zr/zr/zr | 0/65/131 | 24361/24063/25778 | 20.7/20.6/20.7 | 20.5/20.6/20.7 | 1.7/1.7/1.6 | 0/2/5/31/74 | 9 | 1650 |
| N | N3-2019-09-23-1441-c5-q4 | search V<6 TYC 4672-1255-1 | zg/zr/zg | 0/42/145 | 10354/13403/3538 | 22.2/21.9/20.5 | 22.0/21.7/20.5 | 2.0/2.1/2.2 | 0/1/1/12/10 | 29 | 3001 |
| N | N4-2020-09-15-447-c3-q4 | search 6<=V<8 TYC 2-1641-1 | zr/zg/zg | 0/65/107 | 6814/4404/4452 | 20.6/20.6/20.6 | 20.7/21.0/20.9 | 1.5/2.0/1.9 | 0/0/5/13/19 | 27 | 470 |
| N | N5-2019-08-27-335-c7-q4 | search V<6 TYC 6301-2322-1 | zr/zr/zr | 0/42/84 | 62956/67303/67485 | 20.4/20.6/20.5 | 20.4/20.5/20.5 | 1.9/1.8/1.7 | 1/1/5/35/57 | 9 | 760 |
| N | N6-2019-07-29-338-c6-q1 | search V<6 TYC 6348-1259-1 | zg/zg/zr | 0/22/40 | 8228/8276/12027 | 20.6/20.6/20.5 | 20.6/20.6/20.5 | 2.3/2.2/2.2 | 0/1/3/13/28 | 36 | 768 |
| N | N7-2019-12-29-611-c9-q3 | search 6<=V<8 TYC 1870-903-1 | zr/zr/zg | 0/58/117 | 20195/21354/12988 | 20.4/20.6/20.8 | 20.4/20.5/20.8 | 2.5/2.4/2.6 | 0/0/3/37/64 | 26 | 366 |
| N | N8-2019-07-24-333-c8-q1 | search V<6 TYC 6269-4008-1 | zr/zr/zr | 0/45/93 | 73792/72645/68893 | 20.5/20.5/20.5 | 20.3/20.3/20.2 | 2.0/2.0/2.1 | 0/1/6/61/164 | 19 | 900 |
| N | N9-2019-08-31-334-c4-q3 | search 6<=V<8 TYC 6288-1682-1 | zr/zr/zg | 0/52/104 | 139175/127949/75699 | 19.9/19.6/19.5 | 19.6/19.5/19.6 | 3.0/3.2/3.6 | 0/0/3/29/52 | 12 | 1961 |
| N | N10-2018-11-12-504-c2-q3 | search V<6 TYC 632-1491-1 | zi/zg/zr | 0/54/92 | 4010/4730/4857 | 19.3/20.6/20.3 | 19.2/20.4/20.1 | 3.8/3.2/2.9 | 0/1/1/13/15 | 7 | 5129 |
| N | N11-2018-10-31-559-c3-q1 | search 6<=V<8 TYC 1264-758-1 | zr/zr/zg | 0/71/120 | 5495/6173/4056 | 20.2/20.3/20.3 | 20.0/20.2/20.4 | 2.8/2.5/2.7 | 0/1/5/9/20 | 11 | 355 |
| N | N12-2019-11-01-607-c1-q2 | search V<6 TYC 1799-1441-1 | zr/zr/zr | 0/50/147 | 8174/10067/8472 | 20.4/20.7/20.5 | 20.4/20.8/20.5 | 2.2/1.6/1.9 | 3/4/13/29/24 | 17 | 6478 |
| N | N13-2018-08-21-394-c12-q4 | search 6<=V<8 TYC 5821-453-1 | zi/zr/zg | 0/54/94 | 9055/10209/6819 | 20.5/21.0/21.4 | 20.4/21.0/21.2 | 1.7/1.8/2.2 | 0/2/4/8/14 | 22 | 7280 |
| N | N14-2018-11-02-562-c3-q3 | search V<6 TYC 1299-1090-1 | zr/zg/zr | 0/29/98 | 25544/17978/40788 | 20.3/20.3/21.8 | 20.3/20.4/21.8 | 2.2/2.7/2.0 | 0/1/1/18/51 | 11 | 840 |
| N | N15-2019-07-29-338-c13-q3 | search V<6 TYC 5782-1505-1 | zg/zg/zr | 0/22/40 | 8232/8149/12152 | 20.7/20.7/20.7 | 20.7/20.7/20.6 | 2.4/2.4/2.0 | 0/1/0/11/32 | 31 | 184 |
| N | N16-2019-12-29-568-c15-q4 | search V<6 TYC 1399-2905-1 | zr/zr/zg | 0/43/105 | 8432/8523/6137 | 20.8/20.8/21.0 | 20.8/20.8/21.0 | 2.0/1.9/2.3 | 0/1/0/17/24 | 26 | 3463 |
| N | N17-2019-06-27-330-c9-q2 | search V<6 TYC 6232-1333-1 | zr/zr/zr | 0/46/88 | 78187/73441/84489 | 20.6/20.5/20.7 | 20.5/20.4/20.6 | 2.0/2.2/1.8 | 1/1/4/21/32 | 18 | 3619 |
| N | N18-2018-07-16-333-c13-q2 | search 6<=V<8 TYC 5703-3416-1 | zr/zr/zr | 0/45/89 | 178988/175503/177589 | 20.0/20.1/20.3 | 19.4/19.3/19.3 | 2.5/2.4/2.4 | 0/0/5/31/63 | 7 | 2451 |
| N | N19-2019-01-25-614-c2-q1 | search 6<=V<8 TYC 1896-63-1 | zg/zr/zr | 0/31/76 | 10417/16395/13925 | 20.7/20.8/20.4 | 20.6/20.8/20.4 | 2.8/1.9/2.2 | 0/1/1/20/55 | 29 | 1440 |
| N | N20-2018-09-27-499-c1-q2 | search 6<=V<8 TYC 595-1125-1 | zr/zg/zg | 0/122/138 | 2503/1318/2083 | 19.7/19.1/19.9 | 19.7/19.3/20.0 | 1.8/3.9/1.8 | 0/0/4/9/11 | 4 | 82 |
| N | N21-2019-01-28-474-c8-q4 | search 6<=V<8 TYC 292-377-1 | zg/zg/zr | 0/77/141 | 4175/4312/4125 | 20.5/20.7/20.1 | 20.6/20.7/20.0 | 2.2/2.0/2.9 | 0/0/2/6/8 | 11 | 2578 |
| N | N22-2018-09-06-553-c4-q4 | search 6<=V<8 TYC 1197-491-1 | zr/zg/zg | 0/36/107 | 7877/5407/6018 | 21.1/21.3/21.3 | 21.1/21.5/21.5 | 1.9/2.1/1.9 | 0/0/2/11/14 | 14 | 867 |
| N | N23-2019-06-01-279-c6-q1 | search 6<=V<8 TYC 6813-809-1 | zr/zr/zr | 0/46/92 | 99989/102729/103708 | 20.6/20.7/20.8 | 20.7/20.7/20.7 | 2.0/1.8/1.8 | 0/0/6/22/34 | 30 | 2319 |
| N | N24-2019-08-21-335-c10-q3 | search 6<=V<8 TYC 6297-25-1 | zr/zr/zr | 0/46/88 | 56967/51020/50121 | 20.5/20.3/20.2 | 20.4/20.2/20.1 | 2.0/2.3/2.3 | 0/0/4/25/46 | 14 | 273 |
| R | POC-2018-04-11-535-c11-q3 | AS-034 (AS-022) | zr/zr/zr | 0/64/103 | 13455/12553/8678 | 20.8/20.1/19.2 | 20.5/20.2/19.4 | 3.0/3.5/3.6 | 0/0/0/13/30 | 0 | 80 |
| R | B-2019-01-25-565-c13-q3 | AS-034 (AS-022) | zg/zr/zr | 0/31/75 | 9349/14211/11256 | 20.8/20.8/20.4 | 20.7/20.8/20.3 | 2.5/1.9/2.4 | 0/1/6/27/44 | 23 | 494 |
| R | C-2018-10-06-448-c9-q3 | AS-034 (AS-022) | zr/zi/zg | 0/53/69 | 7863/7569/5117 | 21.0/20.4/21.2 | 21.1/20.5/21.4 | 1.6/1.8/1.9 | 0/0/2/9/19 | 13 | 154 |
| R | D-2019-06-02-281-c16-q3 | AS-034 (AS-022) | zr/zr/zr | 0/46/92 | 150253/131401/149649 | 20.3/20.2/20.3 | 20.2/20.1/20.2 | 2.4/2.7/2.4 | 0/1/1/9/21 | 17 | 5634 |
| R | S1-2018-09-19-508-c10-q4 | AS-034 (AS-033) | zr/zg/zg | 0/53/94 | 8283/5833/4234 | 21.1/21.3/20.5 | 21.2/21.5/20.6 | 1.8/1.8/1.7 | 0/0/3/8/19 | 8 | 290 |
| R | S2-2018-09-27-509-c14-q4 | AS-034 (AS-033) | zg/zg/zr | 0/46/102 | 5199/5802/8821 | 20.0/20.1/20.0 | 19.9/20.1/20.1 | 1.7/1.7/2.3 | 0/1/4/3/29 | 3 | 651 |
| R | S3-2019-07-01-335-c7-q1 | AS-034 (AS-033) | zr/zr/zr | 0/1/58 | 68956/68403/74631 | 20.6/20.6/20.7 | 20.5/20.5/20.7 | 2.0/2.0/1.8 | 1/1/3/29/64 | 22 | 424 |
| R | S4-2018-11-07-615-c5-q3 | AS-034 (AS-033) | zr/zg/zr | 0/95/169 | 11421/9345/11594 | 20.1/20.7/20.4 | 20.2/20.6/20.3 | 3.7/3.3/3.2 | 1/0/1/12/29 | 11 | 23803 |
| R | B-2019-01-25-565-c13-q1 | AS-034 (sibling of B-2019-01-25-565-c13-q3) | zg/zr/zr | 0/31/75 | 7472/11570/8896 | 20.6/20.6/20.2 | 20.6/20.6/20.1 | 2.7/2.0/2.5 | 0/0/2/22/44 | 18 | 131 |
| R | B-2019-01-25-565-c13-q2 | AS-034 (sibling of B-2019-01-25-565-c13-q3) | zg/zr/zr | 0/31/75 | 8781/13514/10384 | 20.8/20.7/20.3 | 20.7/20.7/20.2 | 2.6/2.0/2.5 | 0/0/5/29/40 | 20 | 466 |
| R | B-2019-01-25-565-c13-q4 | AS-034 (sibling of B-2019-01-25-565-c13-q3) | zg/zr/zr | 0/31/75 | 8203/12885/9938 | 20.7/20.7/20.3 | 20.7/20.7/20.2 | 2.5/2.0/2.4 | 0/0/1/19/43 | 30 | 479 |
| R | D-2019-06-02-281-c16-q1 | AS-034 (sibling of D-2019-06-02-281-c16-q3) | zr/zr/zr | 0/46/92 | 170571/156437/170860 | 20.5/20.5/20.6 | 20.4/20.3/20.4 | 2.4/2.5/2.3 | 0/0/1/13/19 | 13 | 6645 |
| R | D-2019-06-02-281-c16-q2 | AS-034 (sibling of D-2019-06-02-281-c16-q3) | zr/zr/zr | 0/46/92 | 165846/149781/166541 | 20.2/20.2/20.3 | 20.2/20.1/20.2 | 2.4/2.6/2.3 | 0/1/2/14/18 | 17 | 4382 |
| R | D-2019-06-02-281-c16-q4 | AS-034 (sibling of D-2019-06-02-281-c16-q3) | zr/zr/zr | 0/46/92 | 181073/155402/167544 | 20.4/20.3/20.4 | 20.2/20.0/20.1 | 2.3/2.7/2.5 | 0/0/1/12/27 | 25 | 4210 |
| R | S1-2018-09-19-508-c10-q1 | AS-034 (sibling of S1-2018-09-19-508-c10-q4) | zr/zg/zg | 0/53/94 | 8238/5882/4115 | 21.0/21.3/20.4 | 21.1/21.5/20.5 | 2.0/1.9/1.8 | 0/0/4/6/20 | 14 | 204 |
| R | S1-2018-09-19-508-c10-q2 | AS-034 (sibling of S1-2018-09-19-508-c10-q4) | zr/zg/zg | 0/53/94 | 6900/4827/3042 | 20.9/21.2/20.3 | 21.0/21.4/20.5 | 2.2/2.1/2.1 | 0/0/4/10/19 | 9 | 141 |
| R | S1-2018-09-19-508-c10-q3 | AS-034 (sibling of S1-2018-09-19-508-c10-q4) | zr/zg/zg | 0/53/94 | 8147/5325/3613 | 21.0/21.3/20.4 | 21.2/21.5/20.5 | 1.9/1.9/1.8 | 0/0/1/9/16 | 6 | 120 |
| R | S2-2018-09-27-509-c14-q1 | AS-034 (sibling of S2-2018-09-27-509-c14-q4) | zg/zg/zr | 0/46/102 | 4917/5376/6960 | 19.9/20.1/19.7 | 19.9/20.1/19.9 | 1.8/1.8/2.8 | 0/1/5/10/20 | 4 | 120 |
| R | S2-2018-09-27-509-c14-q2 | AS-034 (sibling of S2-2018-09-27-509-c14-q4) | zg/zg/zr | 0/46/102 | 5050/5337/7038 | 20.0/20.1/19.8 | 20.0/20.1/20.0 | 1.8/1.8/2.6 | 0/0/3/10/25 | 4 | 21 |
| R | S2-2018-09-27-509-c14-q3 | AS-034 (sibling of S2-2018-09-27-509-c14-q4) | zg/zg/zr | 0/46/102 | 4900/5240/7645 | 20.0/20.1/20.0 | 20.0/20.1/20.2 | 1.7/1.7/2.2 | 0/0/1/11/27 | 8 | 16 |
| R | S3-2019-07-01-335-c7-q2 | AS-034 (sibling of S3-2019-07-01-335-c7-q1) | zr/zr/zr | 0/1/58 | 74184/75040/83088 | 20.5/20.5/20.7 | 20.5/20.5/20.7 | 2.2/2.1/1.8 | 0/0/1/36/78 | 20 | 157 |
| R | S3-2019-07-01-335-c7-q3 | AS-034 (sibling of S3-2019-07-01-335-c7-q1) | zr/zr/zr | 0/1/58 | 72905/73184/80307 | 20.5/20.5/20.7 | 20.5/20.5/20.6 | 2.0/2.0/1.7 | 0/1/2/39/56 | 14 | 405 |
| R | S3-2019-07-01-335-c7-q4 | AS-034 (sibling of S3-2019-07-01-335-c7-q1) | zr/zr/zr | 0/1/58 | 67490/66906/72389 | 20.6/20.6/20.7 | 20.6/20.5/20.7 | 1.9/1.9/1.7 | 1/1/5/36/59 | 22 | 924 |
| R | S4-2018-11-07-615-c5-q1 | AS-034 (sibling of S4-2018-11-07-615-c5-q3) | zr/zg/zr | 0/95/169 | 6462/5592/8536 | 19.7/20.2/20.0 | 20.2/20.5/20.3 | 4.6/4.3/3.9 | 0/0/1/16/31 | 5 | 80 |
| R | S4-2018-11-07-615-c5-q2 | AS-034 (sibling of S4-2018-11-07-615-c5-q3) | zr/zg/zr | 0/95/169 | 9702/7047/10825 | 20.7/20.8/20.6 | 20.3/20.6/20.4 | 3.6/3.5/3.2 | 0/1/1/18/33 | 5 | 7671 |
| R | S4-2018-11-07-615-c5-q4 | AS-034 (sibling of S4-2018-11-07-615-c5-q3) | zr/zg/zr | 0/95/169 | 6341/5503/7826 | 19.6/20.3/20.2 | 20.1/20.4/20.2 | 4.7/4.1/3.8 | 0/0/4/16/29 | 4 | 316 |

## Eligibility strata (temporal baseline and rate separated first)

| pop | role | targets | too fast | short baseline | eligible | eligible recovered | short-baseline recovered | short-baseline stages |
|---|---|---|---|---|---|---|---|---|
| N | primary | 191 | 4 | 2 | 185 | 150/185 (81 %, 75–86) | 0/2 (0 %, 0–66) | 0 / 2 / 0 / 0 / 0 |
| N | marginal | 229 | 0 | 2 | 227 | 76/227 (33 %, 28–40) | 0/2 (0 %, 0–66) | 2 / 0 / 0 / 0 / 0 |
| R | primary | 127 | 0 | 27 | 100 | 75/100 (75 %, 66–82) | 0/27 (0 %, 0–12) | 3 / 24 / 0 / 0 / 0 |
| R | marginal | 208 | 0 | 51 | 157 | 56/157 (36 %, 29–43) | 0/51 (0 %, 0–7) | 24 / 27 / 0 / 0 / 0 |

## Recovery by proximity group (rate- and baseline-eligible)

zone: <120" of V<6, <60" of 6-8, <30" of 8-10; outer: other <240" of V<10; control: >=480" from V<10 and >=60" from V10-11; intermediate: the rest.

| scope | role | group | recovered | first-failure stages |
|---|---|---|---|---|
| N + R | primary | zone | 3/7 (43 %, 16–75) | 4 / 0 / 0 / 0 / 0 |
| N + R | primary | outer | 24/31 (77 %, 60–89) | 4 / 2 / 0 / 1 / 0 |
| N + R | primary | intermediate | 67/93 (72 %, 62–80) | 10 / 16 / 0 / 0 / 0 |
| N + R | primary | control | 131/154 (85 %, 79–90) | 9 / 14 / 0 / 0 / 0 |
| N + R | marginal | zone | 0/11 (0 %, 0–26) | 11 / 0 / 0 / 0 / 0 |
| N + R | marginal | outer | 19/61 (31 %, 21–44) | 38 / 4 / 0 / 0 / 0 |
| N + R | marginal | intermediate | 42/119 (35 %, 27–44) | 64 / 13 / 0 / 0 / 0 |
| N + R | marginal | control | 71/193 (37 %, 30–44) | 105 / 14 / 0 / 3 / 0 |
| N | primary | zone | 3/7 (43 %, 16–75) | 4 / 0 / 0 / 0 / 0 |
| N | primary | outer | 18/23 (78 %, 58–90) | 2 / 2 / 0 / 1 / 0 |
| N | primary | intermediate | 43/59 (73 %, 60–83) | 5 / 11 / 0 / 0 / 0 |
| N | primary | control | 86/96 (90 %, 82–94) | 5 / 5 / 0 / 0 / 0 |
| N | marginal | zone | 0/9 (0 %, 0–30) | 9 / 0 / 0 / 0 / 0 |
| N | marginal | outer | 13/42 (31 %, 19–46) | 27 / 2 / 0 / 0 / 0 |
| N | marginal | intermediate | 25/77 (32 %, 23–44) | 43 / 9 / 0 / 0 / 0 |
| N | marginal | control | 38/99 (38 %, 29–48) | 55 / 4 / 0 / 2 / 0 |
| R | primary | zone | 0/0 | 0 / 0 / 0 / 0 / 0 |
| R | primary | outer | 6/8 (75 %, 41–93) | 2 / 0 / 0 / 0 / 0 |
| R | primary | intermediate | 24/34 (71 %, 54–83) | 5 / 5 / 0 / 0 / 0 |
| R | primary | control | 45/58 (78 %, 65–86) | 4 / 9 / 0 / 0 / 0 |
| R | marginal | zone | 0/2 (0 %, 0–66) | 2 / 0 / 0 / 0 / 0 |
| R | marginal | outer | 6/19 (32 %, 15–54) | 11 / 2 / 0 / 0 / 0 |
| R | marginal | intermediate | 17/42 (40 %, 27–56) | 21 / 4 / 0 / 0 / 0 |
| R | marginal | control | 33/94 (35 %, 26–45) | 50 / 10 / 0 / 1 / 0 |

## Pre-registered claim rule (PRIMARY, eligible, zone vs control)

| scope | zone | control | Fisher p (two-sided) | MH odds ratio (quadrants) | verdict |
|---|---|---|---|---|---|
| N + R | 3/7 | 131/154 | 0.016 | 0.07 (6) | not demonstrated: 7 zone targets < 10 |
| N | 3/7 | 86/96 | 0.006 | 0.07 (6) | not demonstrated: 7 zone targets < 10 |
| R | 0/0 | 45/58 | – | – (0) | not demonstrated: 0 zone targets < 10 |

## Star magnitude × closest approach (N + R, eligible)

Each target once per class, in the bin of its closest predicted approach (E1-E3) to a star of that class.

| class | closest approach | role | recovered | first-failure stages |
|---|---|---|---|---|
| V<6 | 60-120" | primary | 2/6 (33 %, 10–70) | 4 / 0 / 0 / 0 / 0 |
| V<6 | 60-120" | marginal | 0/5 (0 %, 0–43) | 5 / 0 / 0 / 0 / 0 |
| V<6 | 120-240" | primary | 2/2 (100 %, 34–100) | 0 / 0 / 0 / 0 / 0 |
| V<6 | 120-240" | marginal | 0/1 (0 %, 0–79) | 1 / 0 / 0 / 0 / 0 |
| 6<=V<8 | 0-30" | marginal | 0/1 (0 %, 0–79) | 1 / 0 / 0 / 0 / 0 |
| 6<=V<8 | 30-60" | primary | 1/1 (100 %, 21–100) | 0 / 0 / 0 / 0 / 0 |
| 6<=V<8 | 30-60" | marginal | 0/2 (0 %, 0–66) | 2 / 0 / 0 / 0 / 0 |
| 6<=V<8 | 60-120" | primary | 1/3 (33 %, 6–79) | 0 / 1 / 0 / 1 / 0 |
| 6<=V<8 | 60-120" | marginal | 4/12 (33 %, 14–61) | 7 / 1 / 0 / 0 / 0 |
| 6<=V<8 | 120-240" | primary | 3/4 (75 %, 30–95) | 0 / 1 / 0 / 0 / 0 |
| 6<=V<8 | 120-240" | marginal | 1/2 (50 %, 9–91) | 1 / 0 / 0 / 0 / 0 |
| 8<=V<10 | 0-30" | marginal | 0/3 (0 %, 0–56) | 3 / 0 / 0 / 0 / 0 |
| 8<=V<10 | 30-60" | primary | 5/7 (71 %, 36–92) | 1 / 1 / 0 / 0 / 0 |
| 8<=V<10 | 30-60" | marginal | 0/2 (0 %, 0–66) | 2 / 0 / 0 / 0 / 0 |
| 8<=V<10 | 60-120" | primary | 3/3 (100 %, 44–100) | 0 / 0 / 0 / 0 / 0 |
| 8<=V<10 | 60-120" | marginal | 3/14 (21 %, 8–48) | 11 / 0 / 0 / 0 / 0 |
| 8<=V<10 | 120-240" | primary | 11/14 (79 %, 52–92) | 3 / 0 / 0 / 0 / 0 |
| 8<=V<10 | 120-240" | marginal | 11/32 (34 %, 20–52) | 18 / 3 / 0 / 0 / 0 |

## Detection-stage losses and local depth (eligible)

Local margin = local 5σ catalog depth − expected band magnitude, minimum over the frames where the target was not detected.

| group | detection losses | locally detectable (margin >= 0) | locally below | no local depth |
|---|---|---|---|---|
| zone | 15 | 6 | 9 | 0 |
| outer | 42 | 17 | 19 | 6 |
| intermediate | 74 | 31 | 23 | 20 |
| control | 114 | 39 | 35 | 40 |

## Every target within 240" of a V<10 star (all strata)

| pop | field | object | role | V | rate ("/min) | min disp. (") | eligible | nearest V<10 (", class) | group | nearest src (") E1/E2/E3 | candidate | global / local margin (min) | tracklet | first failure | AS-022 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| N | N11-2018-10-31-559-c3-q1 | 157539 | marginal | 20.3 | 0.40 | 19.6 | yes | 1, 8<=V<10 | zone | 0.7/2.0/6.0 | y/n:other/– | -0.3 / -1.6 | –  | detection | not_detected |
| N | N18-2018-07-16-333-c13-q2 | 332829 | marginal | 20.4 | 0.50 | 22.0 | yes | 6, 6<=V<8 | zone | 3.9/2.7/3.7 | –/–/– | -0.2 / -1.0 | –  | detection | not_detected |
| R | S2-2018-09-27-509-c14-q1 | 34131 | marginal | 20.1 | 0.29 | 13.1 | yes | 16, 8<=V<10 | zone | 0.0/–/0.4 | y/–/y | -0.5 / -1.4 | –  | detection | not_detected |
| R | D-2019-06-02-281-c16-q4 | 434592 | marginal | 20.5 | 0.60 | 27.7 | yes | 21, 8<=V<10 | zone | 2.1/0.2/0.9 | –/y/n:other | 0.0 / -0.2 | –  | detection | not_detected |
| N | N2-2019-11-05-564-c1-q2 | 116749 | marginal | 20.8 | 0.20 | 12.9 | yes | 38, 6<=V<8 | zone | 7.5/0.2/2.5 | –/y/– | 0.0 / -0.9 | –  | detection | not_detected |
| N | N7-2019-12-29-611-c9-q3 | 9686 | primary | 18.2 | 0.66 | 38.4 | yes | 40, 8<=V<10 | outer | 0.3/0.3/0.3 | y/y/y | 2.3 / 2.3 | trk-0009 tracklet_built | recovered | recovered |
| N | N7-2019-12-29-611-c9-q3 | 112871 | primary | 18.5 | 0.53 | 30.7 | yes | 43, 8<=V<10 | outer | 0.2/0.2/0.4 | y/y/y | 2.0 / 1.8 | trk-0008 tracklet_built | recovered | recovered |
| N | N11-2018-10-31-559-c3-q1 | 172379 | primary | 18.6 | 0.53 | 25.9 | yes | 46, 6<=V<8 | zone | 0.5/0.7/0.7 | y/y/y | 1.4 / -6.2 | trk-0003 tracklet_built | recovered | recovered |
| R | D-2019-06-02-281-c16-q4 | 268001 | primary | 19.4 | 0.62 | 28.6 | yes | 47, 8<=V<10 | outer | 0.2/2.1/0.2 | y/–/y | 1.1 / 0.9 | –  | detection | not_detected |
| N | N5-2019-08-27-335-c7-q4 | 35231 | primary | 17.7 | 0.21 | 8.8 | yes | 48, 8<=V<10 | outer | 0.1/0.1/0.1 | y/y/y | 2.9 / 2.8 | trk-0056 tracklet_built | recovered | recovered |
| N | N21-2019-01-28-474-c8-q4 | 161277 | marginal | 20.4 | 0.13 | 8.4 | yes | 51, 6<=V<8 | zone | 0.7/0.5/4.4 | y/n:other/– | -0.2 / -1.9 | –  | detection | not_detected |
| N | N14-2018-11-02-562-c3-q3 | 15523 | primary | 18.1 | 0.21 | 6.1 | yes | 51, 8<=V<10 | outer | 0.1/0.1/0.0 | y/y/y | 1.9 / 2.0 | trk-0150 tracklet_built | recovered | recovered |
| N | N9-2019-08-31-334-c4-q3 | 36463 | marginal | 19.7 | 0.10 | 5.0 | yes | 52, 8<=V<10 | outer | 1.9/0.4/– | n:other/n:other/– | -0.5 / -0.4 | –  | detection | not_detected |
| N | N8-2019-07-24-333-c8-q1 | 241030 | primary | 19.9 | 0.43 | 19.2 | yes | 54, 8<=V<10 | outer | 0.1/0.0/0.2 | y/y/y | 0.8 / 0.6 | trk-0012 tracklet_built | recovered | recovered |
| N | N23-2019-06-01-279-c6-q1 | 331332 | marginal | 20.8 | 0.52 | 23.9 | yes | 55, 8<=V<10 | outer | 0.5/4.7/6.6 | y/–/– | -0.0 / 0.0 | –  | detection | not_detected |
| N | N24-2019-08-21-335-c10-q3 | 67559 | primary | 18.8 | 0.22 | 8.9 | yes | 60, 8<=V<10 | outer | 0.4/0.3/0.8 | y/y/n:other | 1.6 / 1.5 | –  | stationary | not_candidate |
| R | S3-2019-07-01-335-c7-q2 | 89616 | primary | 18.9 | 0.57 | 0.4 | short baseline | 60, 8<=V<10 | outer | 0.1/0.1/0.8 | n:self/n:self/n:other | 1.8 / 1.8 | –  | stationary | not_candidate |
| N | N23-2019-06-01-279-c6-q1 | 134387 | marginal | 20.4 | 0.67 | 30.9 | yes | 60, 8<=V<10 | outer | 0.6/0.3/0.2 | y/y/y | 0.4 / 0.5 | trk-1521 tracklet_built | recovered | recovered |
| N | N5-2019-08-27-335-c7-q4 | 439843 | marginal | 20.8 | 0.07 | 3.0 | yes | 60, 8<=V<10 | outer | 6.3/0.2/0.3 | –/y/y | -0.2 / -0.2 | –  | detection | not_detected |
| N | N19-2019-01-25-614-c2-q1 | 342893 | marginal | 20.9 | 0.51 | 16.1 | yes | 67, 6<=V<8 | outer | –/1.1/0.2 | –/y/y | -0.6 / -0.8 | –  | detection | not_detected |
| N | N20-2018-09-27-499-c1-q2 | 127639 | marginal | 19.4 | 0.81 | 12.8 | yes | 68, 6<=V<8 | outer | 0.3/–/0.0 | y/–/y | -0.7 / 0.4 | –  | detection | not_detected |
| R | S3-2019-07-01-335-c7-q2 | 441255 | marginal | 20.8 | 0.55 | 0.4 | short baseline | 72, 8<=V<10 | outer | 0.1/0.1/0.3 | n:self/n:self/y | -0.1 / -0.1 | –  | stationary | not_candidate |
| R | D-2019-06-02-281-c16-q2 | 657605 | marginal | 20.1 | 0.56 | 25.7 | yes | 75, 6<=V<8 | outer | 0.3/0.4/0.4 | y/y/y | 0.3 / 0.2 | trk-0329 tracklet_built | recovered | recovered |
| N | N13-2018-08-21-394-c12-q4 | 167518 | marginal | 20.7 | 0.44 | 17.8 | yes | 76, 6<=V<8 | outer | 0.4/0.4/– | y/y/– | 0.2 / -0.1 | –  | detection | not_detected |
| R | S4-2018-11-07-615-c5-q4 | 23139 | primary | 19.1 | 0.35 | 25.4 | yes | 77, 8<=V<10 | outer | 0.9/0.8/0.6 | y/y/y | 0.7 / 1.0 | trk-0101 tracklet_built | recovered | recovered |
| N | N3-2019-09-23-1441-c5-q4 | 307705 | primary | 18.8 | 0.76 | 31.4 | yes | 78, 6<=V<8 | outer | 0.1/0.3/0.2 | y/y/y | 1.3 / 2.6 | trk-1952 rejected | fit | recovered |
| R | S3-2019-07-01-335-c7-q2 | 288181 | marginal | 20.9 | 0.57 | 0.4 | short baseline | 79, 8<=V<10 | outer | –/0.5/0.4 | –/y/y | -0.2 / -0.3 | –  | detection | not_detected |
| R | S3-2019-07-01-335-c7-q2 | 230748 | marginal | 20.5 | 0.47 | 0.3 | short baseline | 81, 8<=V<10 | outer | –/0.2/0.1 | –/y/y | 0.2 / 0.2 | –  | detection | not_detected |
| N | N8-2019-07-24-333-c8-q1 | 188826 | primary | 19.7 | 0.43 | 19.4 | yes | 82, V<6 | zone | 8.5/0.4/0.3 | –/y/y | 1.0 / 0.7 | –  | detection | not_detected |
| R | D-2019-06-02-281-c16-q4 | 373923 | marginal | 20.0 | 0.62 | 28.5 | yes | 85, 8<=V<10 | outer | 0.4/2.7/0.6 | n:other/–/n:other | 0.5 / 0.3 | –  | detection | not_detected |
| R | D-2019-06-02-281-c16-q1 | 2008 OD8 | marginal | 20.3 | 0.52 | 24.3 | yes | 86, 8<=V<10 | outer | 0.2/3.9/0.7 | y/–/n:other | 0.4 / 0.3 | –  | detection | not_detected |
| R | B-2019-01-25-565-c13-q4 | 278678 | marginal | 19.8 | 0.56 | 17.6 | yes | 87, 8<=V<10 | outer | 0.4/–/0.2 | y/–/y | 0.6 / 0.5 | –  | detection | not_detected |
| R | S3-2019-07-01-335-c7-q4 | 99170 | primary | 19.8 | 0.57 | 0.4 | short baseline | 88, 8<=V<10 | outer | 0.3/0.3/0.3 | n:self/n:self/y | 1.0 / 1.0 | –  | stationary | not_candidate |
| N | N7-2019-12-29-611-c9-q3 | 231583 | marginal | 20.1 | 0.52 | 30.3 | yes | 88, 6<=V<8 | outer | 0.2/3.7/0.2 | y/–/y | 0.4 / 0.3 | –  | detection | not_detected |
| N | N4-2020-09-15-447-c3-q4 | 91047 | primary | 20.0 | 0.58 | 24.5 | yes | 90, 8<=V<10 | outer | 0.2/0.4/0.2 | y/y/y | 0.3 / 0.6 | trk-0039 tracklet_built | recovered | recovered |
| N | N16-2019-12-29-568-c15-q4 | 284210 | marginal | 20.5 | 0.40 | 17.1 | yes | 90, V<6 | zone | 0.4/0.4/3.5 | y/y/– | 0.2 / -0.9 | –  | detection | not_detected |
| N | N9-2019-08-31-334-c4-q3 | 101094 | marginal | 19.3 | 0.29 | 15.1 | yes | 90, 6<=V<8 | outer | 0.3/1.9/1.3 | y/n:other/n:other | -0.1 / -0.0 | –  | stationary | not_candidate |
| N | N5-2019-08-27-335-c7-q4 | 172333 | marginal | 20.4 | 0.20 | 8.4 | yes | 90, V<6 | zone | 0.2/1.8/4.9 | y/n:other/– | 0.2 / 0.1 | –  | detection | not_detected |
| N | N14-2018-11-02-562-c3-q3 | 22613 | marginal | 20.0 | 0.27 | 7.9 | yes | 91, 8<=V<10 | outer | 1.2/5.4/0.0 | y/–/y | -0.0 / 0.0 | –  | detection | not_detected |
| N | N3-2019-09-23-1441-c5-q4 | 190831 | primary | 19.3 | 0.65 | 27.1 | yes | 91, V<6 | zone | 0.1/0.1/0.1 | y/y/y | 0.8 / -7.5 | trk-0062 tracklet_built | recovered | recovered |
| N | N23-2019-06-01-279-c6-q1 | 625513 | marginal | 20.9 | 0.52 | 24.2 | yes | 92, 6<=V<8 | outer | 3.8/0.3/1.0 | –/y/n:other | -0.1 / -0.1 | –  | detection | not_detected |
| N | N17-2019-06-27-330-c9-q2 | 700826 | primary | 19.8 | 0.52 | 22.0 | yes | 93, V<6 | zone | 0.3/2.2/0.2 | y/–/y | 0.9 / 0.0 | –  | detection | not_detected |
| N | N2-2019-11-05-564-c1-q2 | 247549 | marginal | 20.4 | 0.30 | 19.2 | yes | 94, V<6 | zone | 0.1/0.4/7.2 | y/y/– | 0.4 / -0.4 | –  | detection | not_detected |
| R | B-2019-01-25-565-c13-q4 | 305928 | marginal | 20.6 | 0.54 | 16.9 | yes | 94, 8<=V<10 | outer | 0.5/0.2/– | y/y/– | -0.2 / -0.2 | –  | detection | not_detected |
| N | N4-2020-09-15-447-c3-q4 | 303169 | marginal | 21.0 | 0.53 | 22.6 | yes | 94, 8<=V<10 | outer | –/–/– | –/–/– | -0.7 / -0.4 | –  | detection | not_detected |
| N | N22-2018-09-06-553-c4-q4 | 566711 | marginal | 20.9 | 0.38 | 13.8 | yes | 95, 6<=V<8 | outer | 0.2/0.2/– | y/y/– | 0.0 / 0.2 | –  | detection | not_detected |
| N | N24-2019-08-21-335-c10-q3 | 114058 | marginal | 20.2 | 0.32 | 13.4 | yes | 98, 6<=V<8 | outer | 0.2/0.5/0.2 | y/y/y | 0.2 / 0.1 | trk-0042 tracklet_built | recovered | recovered |
| R | B-2019-01-25-565-c13-q1 | 659292 | marginal | 20.4 | 0.62 | 19.5 | yes | 101, 8<=V<10 | outer | –/0.1/4.0 | –/y/– | -0.1 / -0.1 | –  | detection | not_detected |
| N | N11-2018-10-31-559-c3-q1 | 245063 | marginal | 20.3 | 0.39 | 19.0 | yes | 101, 8<=V<10 | outer | 0.1/–/0.1 | y/–/y | -0.3 / -0.0 | –  | detection | not_detected |
| R | S4-2018-11-07-615-c5-q4 | 45302 | marginal | 19.5 | 0.31 | 22.3 | yes | 102, 6<=V<8 | outer | 0.9/0.9/0.5 | y/y/y | 0.3 / 0.5 | trk-0051 tracklet_built | recovered | recovered |
| N | N6-2019-07-29-338-c6-q1 | 72582 | primary | 19.4 | 0.51 | 9.2 | yes | 103, V<6 | zone | 0.3/0.3/0.2 | y/y/y | 0.9 / 0.9 | trk-0027 tracklet_built | recovered | recovered |
| R | B-2019-01-25-565-c13-q3 | 465280 | marginal | 20.3 | 0.60 | 18.7 | yes | 103, 6<=V<8 | outer | –/0.3/– | –/y/– | 0.2 / -0.0 | –  | detection | not_detected |
| N | N4-2020-09-15-447-c3-q4 | 700974 | primary | 19.9 | 0.61 | 25.7 | yes | 104, 6<=V<8 | outer | 0.3/0.2/0.4 | y/y/y | 0.4 / 0.4 | trk-0086 tracklet_built | recovered | recovered |
| N | N1-2018-11-25-468-c12-q1 | 29559 | marginal | 19.6 | 0.34 | 9.6 | yes | 105, V<6 | zone | –/0.4/0.8 | –/y/y | -0.1 / -0.4 | –  | detection | not_detected |
| R | B-2019-01-25-565-c13-q3 | 144741 | marginal | 20.6 | 0.49 | 15.3 | yes | 106, 8<=V<10 | outer | 0.1/0.4/0.5 | y/y/y | -0.1 / 0.1 | trk-0006 tracklet_built | recovered | recovered |
| N | N15-2019-07-29-338-c13-q3 | 203683 | primary | 18.7 | 0.71 | 12.8 | yes | 107, V<6 | zone | 5.7/0.0/0.2 | –/y/y | 1.7 / -6.8 | –  | detection | not_detected |
| R | S3-2019-07-01-335-c7-q2 | 408599 | marginal | 20.9 | 0.52 | 0.3 | short baseline | 107, 8<=V<10 | outer | 0.2/0.5/0.3 | n:self/n:self/y | -0.2 / -0.2 | –  | stationary | not_candidate |
| N | N8-2019-07-24-333-c8-q1 | 396601 | marginal | 20.0 | 0.55 | 24.4 | yes | 109, 8<=V<10 | outer | 4.2/0.1/0.1 | –/y/y | 0.7 / 0.6 | –  | detection | not_detected |
| N | N24-2019-08-21-335-c10-q3 | 93731 | marginal | 19.9 | 0.29 | 12.3 | yes | 110, 8<=V<10 | outer | 0.5/0.3/0.8 | y/y/y | 0.5 / 0.1 | trk-0140 tracklet_built | recovered | recovered |
| R | S3-2019-07-01-335-c7-q1 | 64939 | primary | 18.8 | 0.59 | 0.4 | short baseline | 113, 8<=V<10 | outer | 0.1/0.3/0.2 | n:self/n:self/y | 2.0 / 2.0 | –  | stationary | not_candidate |
| N | N14-2018-11-02-562-c3-q3 | 242915 | marginal | 20.0 | 0.19 | 5.6 | yes | 114, V<6 | zone | 0.1/–/0.2 | y/–/y | -0.0 / 0.1 | –  | detection | not_detected |
| R | S4-2018-11-07-615-c5-q2 | 162485 | marginal | 20.8 | 0.33 | 23.9 | yes | 115, 8<=V<10 | outer | 0.6/–/0.5 | y/–/y | -0.3 / -0.2 | –  | detection | not_detected |
| N | N13-2018-08-21-394-c12-q4 | 400310 | marginal | 20.5 | 0.53 | 21.3 | yes | 115, 6<=V<8 | outer | 0.1/0.2/0.1 | y/y/y | 0.4 / 0.2 | trk-0189 tracklet_built | recovered | recovered |
| N | N12-2019-11-01-607-c1-q2 | 409309 | primary | 19.6 | 0.50 | 25.2 | yes | 116, V<6 | zone | 0.3/0.3/8.5 | y/y/– | 1.0 / 1.0 | –  | detection | not_detected |
| R | S3-2019-07-01-335-c7-q1 | 725711 | marginal | 20.2 | 0.62 | 0.4 | short baseline | 118, 8<=V<10 | outer | 0.2/0.1/0.3 | n:self/n:self/y | 0.6 / 0.5 | –  | stationary | not_candidate |
| N | N14-2018-11-02-562-c3-q3 | 4446 | primary | 18.1 | 0.21 | 6.1 | yes | 120, 8<=V<10 | outer | 0.1/0.1/0.1 | y/y/y | 1.9 / 1.9 | trk-0038 tracklet_built | recovered | recovered |
| N | N24-2019-08-21-335-c10-q3 | 19979 | primary | 17.0 | 0.32 | 13.4 | yes | 121, 8<=V<10 | outer | 0.1/0.1/0.1 | y/y/y | 3.4 / 3.3 | trk-0013 tracklet_built | recovered | recovered |
| N | N9-2019-08-31-334-c4-q3 | 233887 | marginal | 19.4 | 0.14 | 7.5 | yes | 122, 8<=V<10 | outer | 0.5/3.8/4.9 | n:other/–/– | -0.2 / -0.1 | –  | detection | not_detected |
| R | D-2019-06-02-281-c16-q2 | 323600 | marginal | 20.3 | 0.51 | 23.6 | yes | 123, 8<=V<10 | outer | 0.3/0.2/0.4 | y/y/n:other | 0.1 / 0.1 | –  | stationary | not_candidate |
| N | N8-2019-07-24-333-c8-q1 | 21345 | primary | 18.5 | 0.47 | 21.2 | yes | 123, 8<=V<10 | outer | 0.2/0.2/0.1 | y/y/y | 2.2 / 2.0 | trk-0086 tracklet_built | recovered | recovered |
| N | N8-2019-07-24-333-c8-q1 | 74035 | primary | 19.1 | 0.39 | 17.6 | yes | 130, 8<=V<10 | outer | 0.2/0.2/0.3 | y/y/y | 1.6 / 1.4 | trk-0042 tracklet_built | recovered | recovered |
| N | N9-2019-08-31-334-c4-q3 | 49455 | marginal | 19.4 | 0.15 | 7.9 | yes | 132, 8<=V<10 | outer | 1.2/1.3/0.7 | n:other/n:other/n:other | -0.2 / -0.2 | –  | stationary | not_candidate |
| R | D-2019-06-02-281-c16-q4 | 76917 | primary | 18.8 | 0.64 | 29.7 | yes | 132, 8<=V<10 | outer | 2.5/0.7/0.3 | –/n:other/y | 1.7 / 1.5 | –  | detection | not_detected |
| N | N9-2019-08-31-334-c4-q3 | 2064 | primary | 13.9 | 1.03 | 53.7 | too fast | 133, 8<=V<10 | outer | 0.4/0.4/0.7 | y/n:other/y | 5.3 / 5.4 | –  | stationary | not_candidate |
| N | N12-2019-11-01-607-c1-q2 | 117867 | marginal | 20.0 | 0.48 | 23.9 | yes | 135, 8<=V<10 | outer | 0.2/0.1/0.3 | y/y/y | 0.6 / -7.5 | trk-0434 tracklet_built | recovered | recovered |
| N | N3-2019-09-23-1441-c5-q4 | 192151 | primary | 19.1 | 0.62 | 25.8 | yes | 138, 8<=V<10 | outer | 0.1/0.1/0.2 | y/y/y | 1.0 / 1.2 | trk-0020 tracklet_built | recovered | recovered |
| N | N17-2019-06-27-330-c9-q2 | 685126 | marginal | 21.0 | 0.51 | 21.5 | yes | 139, 8<=V<10 | outer | 0.3/–/0.4 | y/–/y | -0.3 / -0.3 | –  | detection | not_detected |
| N | N24-2019-08-21-335-c10-q3 | 267158 | marginal | 20.6 | 0.36 | 15.0 | yes | 149, 6<=V<8 | outer | 0.0/4.6/0.8 | y/–/n:other | -0.2 / -0.2 | –  | detection | not_detected |
| N | N7-2019-12-29-611-c9-q3 | 19397 | primary | 18.1 | 0.65 | 38.0 | yes | 150, 8<=V<10 | outer | 0.0/0.1/0.0 | y/y/y | 2.4 / 2.3 | trk-0001 tracklet_built | recovered | recovered |
| N | N2-2019-11-05-564-c1-q2 | 130075 | marginal | 20.6 | 0.14 | 8.8 | yes | 152, V<6 | outer | 4.6/0.2/0.4 | –/n:other/y | 0.2 / -0.1 | –  | detection | not_detected |
| N | N16-2019-12-29-568-c15-q4 | 2010 DL79 | marginal | 21.1 | 0.38 | 16.3 | yes | 152, 8<=V<10 | outer | –/0.5/0.4 | –/y/y | -0.4 / -0.5 | –  | detection | not_detected |
| N | N14-2018-11-02-562-c3-q3 | 91398 | marginal | 19.8 | 0.24 | 7.1 | yes | 152, 8<=V<10 | outer | 0.1/0.5/0.1 | y/y/y | 0.2 / 0.3 | trk-0139 tracklet_built | recovered | recovered |
| R | B-2019-01-25-565-c13-q4 | 205447 | primary | 19.5 | 0.67 | 21.0 | yes | 155, 8<=V<10 | outer | 0.4/0.2/0.3 | y/y/y | 0.9 / 0.9 | trk-0077 tracklet_built | recovered | recovered |
| R | B-2019-01-25-565-c13-q1 | 253689 | primary | 18.6 | 0.60 | 18.7 | yes | 155, 8<=V<10 | outer | 0.5/0.6/0.5 | y/y/y | 1.7 / 1.8 | trk-0004 tracklet_built | recovered | recovered |
| N | N20-2018-09-27-499-c1-q2 | 241729 | marginal | 19.3 | 0.57 | 9.0 | yes | 155, 8<=V<10 | outer | 0.1/0.6/0.2 | y/y/y | -0.6 / – | trk-0022 tracklet_built | recovered | recovered |
| R | S3-2019-07-01-335-c7-q1 | 394177 | marginal | 20.5 | 0.53 | 0.4 | short baseline | 156, 8<=V<10 | outer | 0.3/0.3/0.1 | n:self/n:self/y | 0.3 / 0.2 | –  | stationary | not_candidate |
| N | N8-2019-07-24-333-c8-q1 | 170590 | primary | 19.2 | 0.47 | 21.1 | yes | 157, 8<=V<10 | outer | 1.6/0.2/3.9 | n:other/y/– | 1.5 / 1.2 | –  | detection | not_detected |
| N | N17-2019-06-27-330-c9-q2 | 103244 | marginal | 20.1 | 0.59 | 24.9 | yes | 168, 8<=V<10 | outer | 0.1/0.4/0.1 | y/y/y | 0.6 / 0.6 | trk-1366 tracklet_built | recovered | recovered |
| R | S3-2019-07-01-335-c7-q1 | 261612 | marginal | 20.6 | 0.49 | 0.3 | short baseline | 170, V<6 | outer | 0.3/0.3/0.2 | n:self/n:self/y | 0.2 / 0.1 | –  | stationary | not_candidate |
| R | D-2019-06-02-281-c16-q3 | 752137 | marginal | 20.7 | 0.57 | 26.1 | yes | 175, 8<=V<10 | outer | 0.6/0.2/1.2 | y/y/n:other | -0.3 / -0.4 | –  | stationary | not_candidate |
| N | N4-2020-09-15-447-c3-q4 | 288967 | marginal | 20.4 | 0.50 | 21.1 | yes | 177, 8<=V<10 | outer | 0.2/0.2/0.4 | y/y/y | -0.1 / 0.4 | trk-0042 tracklet_built | recovered | recovered |
| R | S3-2019-07-01-335-c7-q4 | 752086 | marginal | 21.0 | 0.64 | 0.4 | short baseline | 177, 8<=V<10 | outer | 9.3/0.3/4.4 | –/y/– | -0.2 / -0.2 | –  | detection | not_detected |
| N | N15-2019-07-29-338-c13-q3 | 88001 | primary | 19.6 | 0.52 | 9.4 | yes | 179, 8<=V<10 | outer | 0.2/0.2/0.2 | y/y/y | 0.8 / 0.6 | trk-0015 tracklet_built | recovered | recovered |
| N | N8-2019-07-24-333-c8-q1 | 111878 | marginal | 20.1 | 0.45 | 19.9 | yes | 179, 8<=V<10 | outer | 0.3/0.6/4.8 | y/y/– | 0.6 / 0.3 | –  | detection | not_detected |
| R | S3-2019-07-01-335-c7-q1 | 36463 | primary | 19.4 | 0.55 | 0.4 | short baseline | 182, V<6 | outer | 0.2/0.3/0.3 | n:self/n:self/y | 1.4 / 1.3 | –  | stationary | not_candidate |
| N | N18-2018-07-16-333-c13-q2 | 640892 | marginal | 19.9 | 0.56 | 24.7 | yes | 183, 8<=V<10 | outer | 2.4/1.3/5.6 | –/n:other/– | 0.3 / -0.3 | –  | detection | not_detected |
| R | S3-2019-07-01-335-c7-q2 | 115936 | primary | 19.6 | 0.60 | 0.4 | short baseline | 185, 8<=V<10 | outer | 3.5/3.5/0.1 | –/–/y | 1.1 / 1.1 | –  | detection | not_detected |
| R | B-2019-01-25-565-c13-q4 | 111030 | primary | 19.2 | 0.59 | 18.5 | yes | 186, 8<=V<10 | outer | 0.2/0.1/0.2 | y/y/y | 1.2 / 1.1 | trk-0020 tracklet_built | recovered | recovered |
| N | N8-2019-07-24-333-c8-q1 | 349224 | marginal | 20.7 | 0.45 | 20.2 | yes | 193, 8<=V<10 | outer | 2.3/0.2/0.3 | –/y/y | -0.0 / -0.1 | –  | detection | not_detected |
| N | N4-2020-09-15-447-c3-q4 | 151296 | primary | 19.9 | 0.55 | 23.3 | yes | 195, 8<=V<10 | outer | 0.1/0.2/0.1 | y/y/y | 0.4 / – | trk-0041 tracklet_built | recovered | recovered |
| R | B-2019-01-25-565-c13-q4 | 99131 | primary | 19.5 | 0.55 | 17.1 | yes | 197, 6<=V<8 | outer | 0.1/0.1/0.1 | y/y/y | 0.9 / 0.8 | trk-0008 tracklet_built | recovered | recovered |
| N | N7-2019-12-29-611-c9-q3 | 85495 | primary | 17.7 | 0.61 | 35.8 | yes | 199, 8<=V<10 | outer | 0.1/0.1/0.2 | y/y/y | 2.8 / 2.8 | trk-0119 tracklet_built | recovered | recovered |
| N | N8-2019-07-24-333-c8-q1 | 104410 | primary | 19.8 | 0.49 | 21.7 | yes | 200, 8<=V<10 | outer | 0.3/3.4/0.6 | y/–/y | 0.9 / 0.6 | –  | detection | not_detected |
| N | N24-2019-08-21-335-c10-q3 | 236766 | primary | 18.9 | 0.19 | 7.8 | yes | 200, 6<=V<8 | outer | 0.0/0.2/0.2 | y/y/y | 1.5 / 1.5 | trk-0097 tracklet_built | recovered | recovered |
| N | N15-2019-07-29-338-c13-q3 | 138045 | marginal | 20.6 | 0.63 | 11.5 | yes | 202, 8<=V<10 | outer | 1.3/–/0.0 | y/–/y | -0.2 / -0.2 | –  | detection | not_detected |
| N | N23-2019-06-01-279-c6-q1 | 105890 | primary | 18.9 | 0.53 | 24.6 | yes | 202, 6<=V<8 | outer | 0.2/0.3/0.2 | n:other/y/y | 1.9 / 2.0 | –  | stationary | not_candidate |
| N | N8-2019-07-24-333-c8-q1 | 487307 | marginal | 20.2 | 0.37 | 16.4 | yes | 205, 8<=V<10 | outer | –/0.2/0.4 | –/y/y | 0.5 / 0.3 | –  | detection | not_detected |
| N | N11-2018-10-31-559-c3-q1 | 15019 | primary | 19.0 | 0.50 | 24.3 | yes | 205, V<6 | outer | 0.2/0.1/0.1 | y/y/y | 1.0 / 1.1 | trk-0022 tracklet_built | recovered | recovered |
| R | S3-2019-07-01-335-c7-q3 | 128638 | primary | 19.6 | 0.59 | 0.4 | short baseline | 206, 8<=V<10 | outer | 0.1/0.1/2.8 | n:self/n:self/– | 1.1 / 1.1 | –  | detection | not_detected |
| R | S1-2018-09-19-508-c10-q4 | 172959 | marginal | 20.6 | 0.30 | 12.3 | yes | 207, 8<=V<10 | outer | 0.2/0.4/0.5 | y/y/y | -0.5 / – | trk-0027 tracklet_built | recovered | recovered |
| R | D-2019-06-02-281-c16-q2 | 189720 | primary | 18.9 | 0.58 | 26.6 | yes | 210, 6<=V<8 | outer | 0.3/0.3/0.2 | y/y/y | 1.6 / 1.5 | trk-1161 tracklet_built | recovered | recovered |
| N | N6-2019-07-29-338-c6-q1 | 341954 | marginal | 20.6 | 0.62 | 11.1 | yes | 210, 8<=V<10 | outer | 0.4/5.0/0.3 | y/–/y | -0.3 / -0.3 | –  | detection | not_detected |
| N | N13-2018-08-21-394-c12-q4 | 256977 | marginal | 20.2 | 0.51 | 20.3 | yes | 212, 8<=V<10 | outer | 0.0/0.1/0.1 | y/y/y | 0.7 / 0.6 | trk-0180 tracklet_built | recovered | recovered |
| R | S4-2018-11-07-615-c5-q4 | 117524 | marginal | 20.0 | 0.41 | 29.8 | yes | 214, 8<=V<10 | outer | 0.9/0.5/0.7 | y/y/y | -0.2 / 0.2 | trk-0142 tracklet_built | recovered | recovered |
| R | B-2019-01-25-565-c13-q1 | 204282 | marginal | 20.0 | 0.70 | 22.1 | yes | 216, 8<=V<10 | outer | 0.7/0.3/0.1 | y/y/y | 0.3 / 0.4 | trk-0117 tracklet_built | recovered | recovered |
| R | S3-2019-07-01-335-c7-q1 | 379647 | marginal | 20.9 | 0.63 | 0.4 | short baseline | 216, 8<=V<10 | outer | 0.4/6.6/0.4 | y/–/y | -0.1 / -0.2 | –  | detection | not_detected |
| N | N23-2019-06-01-279-c6-q1 | 482907 | marginal | 21.0 | 0.58 | 26.6 | yes | 218, 8<=V<10 | outer | 0.6/0.5/2.1 | y/y/– | -0.2 / -0.2 | –  | detection | not_detected |
| N | N19-2019-01-25-614-c2-q1 | 605266 | marginal | 20.8 | 0.60 | 18.8 | yes | 219, 8<=V<10 | outer | –/0.1/0.4 | –/y/y | -0.5 / -0.4 | –  | detection | not_detected |
| R | S3-2019-07-01-335-c7-q2 | 181388 | marginal | 20.7 | 0.55 | 0.4 | short baseline | 219, 8<=V<10 | outer | 7.7/0.2/0.3 | –/y/y | -0.0 / 0.0 | –  | detection | not_detected |
| R | B-2019-01-25-565-c13-q4 | 2014 TE104 | marginal | 20.4 | 0.60 | 18.7 | yes | 220, 8<=V<10 | outer | –/–/0.8 | –/–/y | -0.0 / -0.1 | –  | detection | not_detected |
| R | B-2019-01-25-565-c13-q1 | 2005 VF146 | marginal | 20.4 | 0.69 | 21.8 | yes | 220, 8<=V<10 | outer | –/0.3/– | –/y/– | -0.1 / 0.4 | –  | detection | not_detected |
| N | N12-2019-11-01-607-c1-q2 | 406040 | marginal | 20.4 | 0.61 | 30.7 | yes | 226, 8<=V<10 | outer | 0.3/0.2/0.1 | y/y/y | 0.2 / 0.1 | trk-0460 tracklet_built | recovered | recovered |
| R | B-2019-01-25-565-c13-q3 | 161588 | marginal | 20.8 | 0.48 | 15.0 | yes | 229, 8<=V<10 | outer | –/–/– | –/–/– | -0.3 / -0.3 | –  | detection | not_detected |
| R | S1-2018-09-19-508-c10-q4 | 213265 | marginal | 20.9 | 0.75 | 31.1 | yes | 229, 8<=V<10 | outer | –/0.6/– | –/y/– | -0.8 / 0.3 | –  | detection | not_detected |
| N | N23-2019-06-01-279-c6-q1 | 2020 RL147 | marginal | 20.3 | 0.66 | 30.6 | yes | 230, 6<=V<8 | outer | 0.1/0.1/0.1 | y/y/y | 0.5 / 0.6 | trk-1314 tracklet_built | recovered | recovered |
| N | N23-2019-06-01-279-c6-q1 | 299705 | marginal | 20.4 | 0.56 | 25.7 | yes | 233, 8<=V<10 | outer | 0.5/0.6/0.4 | y/y/y | 0.4 / 0.4 | trk-1309 tracklet_built | recovered | recovered |
| R | S3-2019-07-01-335-c7-q1 | 102989 | marginal | 20.5 | 0.57 | 0.4 | short baseline | 234, 8<=V<10 | outer | 2.9/2.9/0.3 | –/–/y | 0.3 / 0.2 | –  | detection | not_detected |
| N | N23-2019-06-01-279-c6-q1 | 252111 | marginal | 20.4 | 0.52 | 24.2 | yes | 238, 8<=V<10 | outer | 0.2/4.9/0.3 | y/–/y | 0.4 / 0.5 | –  | detection | not_detected |
| R | S3-2019-07-01-335-c7-q1 | 36731 | primary | 16.4 | 0.64 | 0.4 | short baseline | 238, 8<=V<10 | outer | 0.2/0.3/0.2 | n:self/n:self/y | 4.4 / 4.4 | –  | stationary | not_candidate |

## AS-034 revisit

- **288181** (R, S3-2019-07-01-335-c7-q2, marginal, V 20.9): rate 0.568"/min, min pairwise displacement 0.37" → short-baseline stratum; group outer; nearest source per frame –/0.55/0.37"; candidate –/y/y; first failure detection.
- **408599** (R, S3-2019-07-01-335-c7-q2, marginal, V 20.9): rate 0.524"/min, min pairwise displacement 0.34" → short-baseline stratum; group outer; nearest source per frame 0.23/0.50/0.26"; candidate n:self/n:self/y; first failure stationary.

## Visual sample

| pop | field | object | reason | nearest V<10 (") | first failure | agent label | context | image |
|---|---|---|---|---|---|---|---|---|
| N | N14-2018-11-02-562-c3-q3 | 4446 | near_recovered | 120 | recovered | yes | clean sky | [strips/near_recovered_N14_4446.png](strips/near_recovered_N14_4446.png) |
| R | D-2019-06-02-281-c16-q2 | 657605 | near_recovered | 75 | recovered | yes | crowded D field | [strips/near_recovered_D_657605.png](strips/near_recovered_D_657605.png) |
| N | N24-2019-08-21-335-c10-q3 | 114058 | near_recovered | 98 | recovered | yes | field stars nearby | [strips/near_recovered_N24_114058.png](strips/near_recovered_N24_114058.png) |
| N | N7-2019-12-29-611-c9-q3 | 9686 | near_recovered | 40 | recovered | yes | clean sky; V 8-10 star 40" away, not visibly affecting | [strips/near_recovered_N7_9686.png](strips/near_recovered_N7_9686.png) |
| N | N7-2019-12-29-611-c9-q3 | 112871 | near_recovered | 43 | recovered | yes | E2 next to a bright field star | [strips/near_recovered_N7_112871.png](strips/near_recovered_N7_112871.png) |
| R | S4-2018-11-07-615-c5-q4 | 23139 | near_recovered | 77 | recovered | yes | clean sky; V 9.8 star 77" away out of view | [strips/near_recovered_S4_23139.png](strips/near_recovered_S4_23139.png) |
| N | N24-2019-08-21-335-c10-q3 | 93731 | near_recovered | 110 | recovered | yes | E2/E3 on a bright diffuse glow/spike band of a star off panel | [strips/near_recovered_N24_93731.png](strips/near_recovered_N24_93731.png) |
| N | N13-2018-08-21-394-c12-q4 | 400310 | near_recovered | 115 | recovered | yes | bleed/bad column near E2/E3 | [strips/near_recovered_N13_400310.png](strips/near_recovered_N13_400310.png) |
| R | S2-2018-09-27-509-c14-q1 | 34131 | near_lost | 16 | detection | yes | on the edge of a V 8-10 star's glow/spike 16" away | [strips/near_lost_S2_34131.png](strips/near_lost_S2_34131.png) |
| N | N1-2018-11-25-468-c12-q1 | 29559 | near_lost | 105 | detection | unclear | V 5.9 star 105" away, out of view; diffuse horizontal band (star halo/ghost) and high noise | [strips/near_lost_N1_29559.png](strips/near_lost_N1_29559.png) |
| R | B-2019-01-25-565-c13-q4 | 305928 | near_lost | 94 | detection | unclear | clean sky; V 8-10 star 94" away, out of view | [strips/near_lost_B_305928.png](strips/near_lost_B_305928.png) |
| N | N23-2019-06-01-279-c6-q1 | 331332 | near_lost | 55 | detection | unclear | crowded field with an arc of sources (halo of a star off panel) | [strips/near_lost_N23_331332.png](strips/near_lost_N23_331332.png) |
| N | N9-2019-08-31-334-c4-q3 | 36463 | near_lost | 52 | detection | unclear | crowded; slow mover (0.10"/min) next to bright neighbours | [strips/near_lost_N9_36463.png](strips/near_lost_N9_36463.png) |
| R | B-2019-01-25-565-c13-q3 | 465280 | near_lost | 103 | detection | unclear | bad column at the left; V 6-8 star 103" away, out of view; E1 zg | [strips/near_lost_B_465280.png](strips/near_lost_B_465280.png) |
| N | N14-2018-11-02-562-c3-q3 | 242915 | near_lost | 114 | detection | yes | V 6.0 star 114" away, not in view; an unrelated bright field star 20" below | [strips/near_lost_N14_242915.png](strips/near_lost_N14_242915.png) |
| N | N17-2019-06-27-330-c9-q2 | 700826 | near_lost | 93 | detection | unclear | V 5.7 star 93" away: bright glow, halo arc and a spike/trail cross the panel | [strips/near_lost_N17_700826.png](strips/near_lost_N17_700826.png) |
| N | N6-2019-07-29-338-c6-q1 | 135022 | control_recovered | 495 | recovered | yes | clean sky | [strips/control_recovered_N6_135022.png](strips/control_recovered_N6_135022.png) |
| N | N19-2019-01-25-614-c2-q1 | 49061 | control_recovered | 764 | recovered | yes | field stars nearby | [strips/control_recovered_N19_49061.png](strips/control_recovered_N19_49061.png) |
| N | N14-2018-11-02-562-c3-q3 | 165846 | control_lost | 1007 | detection | yes | E3 lands on a saturated star with spikes that is NOT in Tycho-2 V<=11 (nearest V<=11 star 320") | [strips/control_lost_N14_165846.png](strips/control_lost_N14_165846.png) |
| N | N23-2019-06-01-279-c6-q1 | 237824 | control_lost | 573 | stationary | yes | crowded; E2 on/next to a brighter field star | [strips/control_lost_N23_237824.png](strips/control_lost_N23_237824.png) |
| R | S3-2019-07-01-335-c7-q2 | 288181 | revisit | 79 | detection | yes | E1 on a bright vertical column artifact; V 9.6 star 79" away (the bright blob); E1-E2 0.66 min | [strips/revisit_S3_288181.png](strips/revisit_S3_288181.png) |
| R | S3-2019-07-01-335-c7-q2 | 408599 | revisit | 107 | stationary | yes | compact field star under E1/E2; E1-E2 0.66 min | [strips/revisit_S3_408599.png](strips/revisit_S3_408599.png) |
