# 2026-11-20: data/builds/twelve-region-probe.json

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-20 | `data/builds/twelve-region-probe.json`, a test build (not for use): films-look-exif + `raw-edit-art-bkt` (RAW Data Edit → ART BKT, first code at 0x7EBB2AC4) + `twelve-region-probe` (data only: each ART entry gets its own 12-region table, `experiments/2026-11-20-twelve-region/NOTES.md`). Film file `build/twelve-probe/EPM2LOOK.BIN` (`a71c78b1…`); test RAWs PB200001 (`e82e18a6…`) and PB130001 | `d492e3c853b60fbef5c7e3d2dcf85cfd677096873806f3ae709286f46e2608df` | **Candidate, not flashed.** Emulator: each film code builds its probe table; 43 stock codes keep theirs; the ART BKT row, frame list and Picture Mode restore (`experiments/2026-11-20-raw-edit-art-bkt/NOTES.md` §8); boot-test, update-path-test PASS; hookcheck 0 FAIL. |
