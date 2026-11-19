# 2026-11-15: peaking-menu-names

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-15 | the specs of `peaking-menu-names` + `patches/peaking-colours.json` (`builds/peaking-colours.json`) | `4d6b1f26ed92d66b62b4d7dc32d26168e33fd8b153a7655d6c0d9a58267456f8` | **OK (flashed 2026-11-15).** User: "works". Before the flash: The Peaking list becomes Off / White / Red / Yellow / Blue (Black removed; a camera set to Black shows Red). New code (292 bytes at 0x7E4C93F0, kernel area with camera-tested code) writes the colour into the picture where the line image is 64 or more. Emulator: start-up equal to pinned; the list shows five values and each stays over a restart; on a synthetic frame the line pixels get exactly the colour bytes; White equals pinned, Off equals no peaking. Unknown until the camera shows it: the byte order of the picture buffer (the colours can come out swapped), the loop time, the threshold. Details: `experiments/2026-11-14-focus-peaking/NOTES.md` §16. |
