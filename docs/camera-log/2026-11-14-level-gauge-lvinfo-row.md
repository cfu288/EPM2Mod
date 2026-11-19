# 2026-11-14: patches/level-gauge-lvinfo-row.json

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-14 | the pinned specs + `patches/level-gauge-lvinfo-row.json` (`builds/seven-films-6-interval-240-level.json`; flashed as `build/level-gauge-a.BIN`, the same bytes) | `3e7f793ea74b21dab19c61eac33fe1f818d9c627e4fa522a2551ea62fc32c7f6` | **OK. Level gauge works.** Data only (3 edits, 56 bytes, no code). Custom Menu D → Info Settings → LV-Info shows the new row Level Gauge; the user switched it on, and INFO in live view shows the gauge. User: "works". So the gauge images are in this body's resource block. Not reported: accuracy on a level surface (factory offsets), portrait orientation, a viewfinder's info menu (the row re-uses the unused panel 594). Details: `experiments/2026-11-14-level-gauge/NOTES.md`. |
