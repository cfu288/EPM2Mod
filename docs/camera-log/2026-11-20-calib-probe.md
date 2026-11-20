# 2026-11-20: data/builds/calib-probe.json

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-20 | `data/builds/calib-probe.json`, a test build (not for use): films-look-exif-artbkt + `calib-probe` (data only: 12-region test tables in ART 1, 3, 4, 5, 6, `experiments/2026-11-20-model-calibration/NOTES.md`). Film files `build/calib/EPM2LOOK-1.BIN` … `-4.BIN` (`27e9f329…`, `e92fdb43…`, `a80e0e13…`, `50041991…`); test RAWs PB200002 (the twelve-region RAW, `e82e18a6…`) and PB130001 | `5a575639033c6d104cf3aeb5faafb0f6809a8327f5d3850b1b139b4955e57d3b` | **Candidate, not flashed.** Emulator: each film code selects its table (ART 1 off, 3–5 fitted film tables, 6 Natural's with flat curves, 2 and 7–12 table A); 43 stock codes keep their table pointers. |
