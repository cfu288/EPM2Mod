# Build descriptions

One file per firmware build: the stock firmware it starts from, the patch specs in order, and,
once the build has been tested on a camera, the sha256 of the result and the date of the test.

```bash
uv run tools/make_firmware.py                      # the pinned build (pinned-build.json names it)
uv run tools/make_firmware.py builds/NAME.json     # another build
```

All firmware that goes on a camera is made this way. The procedure for a new build is in
[`docs/conventions.md`](../docs/conventions.md), "Making firmware".
