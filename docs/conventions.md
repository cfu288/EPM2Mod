# Conventions

## Commits: Conventional Commits

`<type>(<scope>)?: <summary>`. The `.githooks/commit-msg` hook enforces it. Enable the hook once per clone:

```bash
git config core.hooksPath .githooks
```

| Type | Use for |
|---|---|
| `feat` | new tool capability or new patch spec |
| `fix` | bug fix in tools or a patch spec |
| `docs` | docs, camera log entries |
| `test` | tests |
| `refactor`, `chore`, `build`, `ci`, `perf`, `style`, `revert` | as usual |
| `exp` | ad-hoc work in `experiments/` |

Suggested scopes: `oetool`, `build`, `patch/<name>`, `flash`, `camera-log`, `format`, `exp/<slug>`.

Examples: `feat(patch/movie-limit): raise 29-min cap to 9 h`, `docs(camera-log): record movie-limit flash`.

## Where things go

- **`tools/`:** reusable, tested code.
- **`patches/`:** one JSON spec per mod. Every op states the bytes it expects to replace. Add `expected_sha256` and `status` once a build has been camera-tested.
- **`docs/`:** durable knowledge. Facts there must be sourced or reproducible.
- **`experiments/YYYY-MM-DD-slug/`:** ad-hoc scripts and `NOTES.md`. Anything bulky goes in its `out/` subfolder, which is git-ignored. Promote findings into `docs/` or `tools/` once they hold up.
- **`builds/`:** one description per firmware build (see *Making firmware*). `pinned-build.json` names the last camera-tested one.
- **`firmware/` and `build/`:** binaries are never committed. `firmware/SHA256SUMS` is.

## Making firmware

**All firmware that goes on a camera is made with `tools/make_firmware.py` from a build description.**
Do not call `tools/build.py` by hand for a flash. This is the same command that the README gives to
users, so every flash also tests the install path.

A build description is a file in `builds/`: name, what the build is, the stock firmware, and the
patch specs in order. `pinned-build.json` names the description of the last camera-tested build.

1. **New build:** write `builds/NAME.json` with `name`, `what`, `base`, `base_sha256` and `specs`.
   Leave out `sha256` and `camera_tested`. Copy an existing description and change it.
2. **Make it:** `uv run tools/make_firmware.py builds/NAME.json`. For a build without a recorded
   sha256 the script runs `tools/freespace.py check` first, then prints the sha256 and says that the
   build is a candidate.
3. **Log it** in [camera-log.md](camera-log.md) with that sha256, then flash
   `build/card/DCOLYMP/E1019999.BIN` (or `build/NAME.BIN`).
4. **If the camera test passes:** `uv run tools/make_firmware.py builds/NAME.json --pin YYYY-MM-DD`.
   This writes the sha256 and the date into the description and makes it the pinned build. Then update
   the build name and sha256 in the README, write the result in the camera log, and commit.
5. **If it fails:** write the result in the camera log. Keep or delete the description; never pin it.

`tests/test_firmware.py` builds every description that has a sha256 and compares the result.

## Camera-testing rule

Never flash a build that hasn't been recorded in [camera-log.md](camera-log.md) before and after: file, sha256, lamp timings, result. Keep the stock BIN at hand for recovery.
