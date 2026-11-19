# 2026-11-17: patches/osd-battery.json

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-17 (not yet flashed) | the pinned specs + `patches/osd-battery.json` (`builds/osd-battery.json`) | `f99c1841f855bccb7975db94027543f33a172cfcc7b9dde299185f69ab7d7e48` | **Pending.** A battery percentage on the live-view screen (top left): one new text label in the panel's unused slot, filled from the 10-bit battery reading (`bchk_ad_read(4)`), read at most once in 2 s and not in the first 3 s after power-on. 382 bytes in the segment-2 area and 6 bytes of RAM. Emulator: start-up and update-path tests pass; the label shows 75 % and 30 % at two readings and is hidden in Image Only. Unknown: the scale on this body (taken from the E-PL3 mod fenykl), the A/D read from the GUI task on the camera, the look over a live picture. Details: `experiments/2026-11-17-osd-info/NOTES.md`. |
