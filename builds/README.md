# Build descriptions

One file per firmware build: what the build is, the patch specs in order, and, once the build has
been tested on a camera, the sha256 of the result and the date of the test. The build's name is the
file name. Every build starts from the stock E-PM2 v1.6 firmware.

```bash
uv run tools/make_firmware.py                      # the pinned build (pinned-build.json names it)
uv run tools/make_firmware.py builds/NAME.json     # another build
```

All firmware that goes on a camera is made this way. The procedure for a new build is in
[`docs/conventions.md`](../docs/conventions.md), "Making firmware".
