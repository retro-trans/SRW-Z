# Export pairing trust, per record
Generated 2026-08-24 against v0.8.72. For each record: of the JP rows that are
dialogue, how many resolve to an English string that is ALSO dialogue.

A low score does NOT mean the game is damaged - the image was verified clean
(68,340 dialogue strings, 0 corrupted). It means the EXPORT mislabels which
Japanese line goes with which English line, so an agent proofreading that
record would be reading the wrong source text.

| band | records | meaning |
|---|---|---|
| >=95% | 109 | export is trustworthy, safe to proofread |
| 60-94% | 3 | partially trustworthy, spot-check before use |
| <60% | 55 | DO NOT proofread from this export |

## Worst 25

| rec | dialogue rows | sane pairs | %% |
|---|---|---|---|
| 12 | 208 | 0 | 0.0 |
| 13 | 238 | 0 | 0.0 |
| 56 | 434 | 0 | 0.0 |
| 92 | 266 | 0 | 0.0 |
| 104 | 688 | 0 | 0.0 |
| 125 | 237 | 0 | 0.0 |
| 137 | 145 | 0 | 0.0 |
| 37 | 440 | 2 | 0.5 |
| 71 | 194 | 1 | 0.5 |
| 98 | 893 | 5 | 0.6 |
| 22 | 349 | 2 | 0.6 |
| 79 | 204 | 2 | 1.0 |
| 64 | 293 | 3 | 1.0 |
| 86 | 195 | 2 | 1.0 |
| 83 | 612 | 7 | 1.1 |
| 99 | 279 | 4 | 1.4 |
| 23 | 202 | 3 | 1.5 |
| 100 | 437 | 7 | 1.6 |
| 119 | 975 | 22 | 2.3 |
| 43 | 458 | 11 | 2.4 |
| 45 | 604 | 15 | 2.5 |
| 115 | 75 | 2 | 2.7 |
| 52 | 456 | 16 | 3.5 |
| 21 | 446 | 16 | 3.6 |
| 73 | 510 | 19 | 3.7 |

## Trustworthy (>=95%)

132, 33, 1, 49, 89, 2, 39, 185, 93, 25, 82, 4, 149, 55, 14, 66, 186, 32, 102, 95, 88, 30, 26, 10, 27, 138, 148, 136, 108, 118, 128, 111, 131, 135, 3, 9, 11, 15, 17, 28, 35, 40, 41, 42, 44, 46, 47, 51, 54, 57, 58, 59, 60, 61, 62, 63, 65, 67, 68, 69, 70, 75, 76, 78, 80, 81, 87, 90, 94, 97, 103, 106, 109, 110, 112, 113, 114, 116, 117, 120, 121, 122, 123, 124, 126, 129, 130, 134, 140, 141, 142, 143, 145, 146, 147, 150, 151, 152, 153, 155, 156, 157, 160, 163, 164, 169, 170, 175, 176
