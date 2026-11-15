# Build descriptions

One file per firmware build: what the build is, the patch specs in order, and, once the build has
been tested on a camera, the sha256 of the result and the date of the test. The build's name is the
file name. Every build starts from the stock E-PM2 v1.6 firmware.

```bash
uv run tools/make_firmware.py                      # the pinned build (pinned-build.json names it)
uv run tools/make_firmware.py builds/NAME.json     # another build
uv run epm2mod pin builds/NAME.json --date YYYY-MM-DD --sha256 HEX   # after a passed camera test
```

All firmware that goes on a camera is made this way. The procedure for a new build is in
[`docs/conventions.md`](../docs/conventions.md), "Making firmware".

## Tested builds

<!-- BEGIN GENERATED: builds -->
| Build | What | Patch specs | Camera-tested | sha256 |
|---|---|---|---|---|
| `peaking-menu-names` (pinned) | Seven film looks named in all 34 languages, interval shooting with up to 240 frames, the level gauge with Level Adjust, and focus peaking with the setting Off / White / Black | 15 | 2026-11-15 | `4ea4ffd773d6f05d16867f55b9fef4bce5d53fc8659a9b16362f7ac771a6bc30` |
| `peaking-direct-4` | Focus peaking, fourth build: light edge lines in live view while MF Assist runs, on top of the build seven-films-6-interval-240-level-adjust. Fixes the crash of peaking-direct-3 at the Velvia entry | 12 | 2026-11-14 | `eea187a958de410bca0448367408998099fde177548d0b9010baf510a3452482` |
| `peaking-gain-2x` | Seven film looks as art filters, interval shooting with up to 240 frames, the level gauge with Level Adjust, and focus peaking | 13 | 2026-11-14 | `ce1037cda6c9ff87e600272383dfe97b649a5ef24d6928e319b581191b4ca2c8` |
| `seven-films-6` | Seven film looks as art filters | 7 | 2026-11-13 | `5badb0796731b40a27ef015e57da134d7d793486d4c6262a3f483c1aae60fd05` |
| `seven-films-6-interval` | Seven film looks as art filters, and interval shooting with up to 99 frames | 8 | 2026-11-13 | `f52ea6976ac2e9c567b2c07d7556b96b6431c8fcd2d90de195abdb76059e0104` |
| `seven-films-6-interval-240` | Seven film looks as art filters, and interval shooting with up to 240 frames | 9 | 2026-11-13 | `01837f962f8a8ca0d189d9cd65ad9b5b35402ca3f3ed54a3872af044e050de11` |
| `seven-films-6-interval-240-level` | Seven film looks as art filters, interval shooting with up to 240 frames, and the level gauge | 10 | 2026-11-14 | `3e7f793ea74b21dab19c61eac33fe1f818d9c627e4fa522a2551ea62fc32c7f6` |
| `seven-films-6-interval-240-level-adjust` | Seven film looks as art filters, interval shooting with up to 240 frames, the level gauge, and Level Adjust (calibrate the level gauge) | 11 | 2026-11-14 | `e93d1589b3406ec991e3f32225acf6e2c2074aa58fc5394ca06a93da83797b66` |
<!-- END GENERATED: builds -->
