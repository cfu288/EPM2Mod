# Camera log

Every flash on real hardware gets a row: what was flashed, the sha256, the lamp timings, and the result. Times are in UTC.

Body: Olympus PEN E-PM2. It was on body 1.6 and lens 1.1 before the first flash.

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-08 12:47 | stock v1.6 | `34d339ac…c3e300` | **OK.** Lamp solid for about 1.5 min (12:47:50 to 12:49:30), then blinking for more than 23 min until powered off. Booted normally; body 1.6. Establishes that **blinking = done** on the E-PM2. |
| 2026-11-08 13:18 | `patches/pixel-hacking.json` | `20fbb83f…3867` | **OK. First modified flash.** Lamp solid for about 1 min 10 s (13:18:27 to 13:19:36), then blinking. Booted normally. Custom Menu → J. Utility shows "Pixel Hacking" (photo IMG_7317). The updater accepts modified content, and block 1 has no hidden check that blocks equal-length text edits. |
| 2026-11-08 13:3x | stock v1.6 (recovery test) | `34d339ac…c3e300` | **OK.** Reflashed from the modified state. Booted normally and the entry reads "Pixel Mapping" again. **Proves recovery from modified firmware.** |
