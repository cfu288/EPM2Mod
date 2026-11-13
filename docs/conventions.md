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

## Production code and research code

- **`src/epm2mod/` is production code.** It makes the firmware that goes on a camera. Rules:
  formatted with black (line length 88), type-checked with `mypy --strict`, a docstring on every
  module, class and function, and tests in `tests/test_package.py`. The pre-commit hook formats the
  staged files of the package and runs mypy. By hand: `uv run black src tests/test_package.py`,
  `uv run mypy`, `uv run python -m unittest discover -s tests`.
- **`experiments/` is research code.** It may be rough. It may import the package; the package never
  imports from `experiments/`. When a result becomes part of how firmware is made, move the code
  into the package and the data into a top-level folder (as `looks/` was).
- **`tools/`** holds stand-alone scripts. `make_firmware.py`, `fetch_stock.py`, `build.py` and
  `oetool.py` are thin commands over the package. The others (`freespace.py`, `fwmap.py`,
  `disasm.py`, `memmap_svg.py`, `emu/`) are analysis tools.
- **Generated, not written by hand:** the README parts between `GENERATED` markers
  (`uv run epm2mod readme`), and the three film patch specs (`uv run epm2mod looks --write`, from
  `looks/films.json` and `looks/fits/`). A build's name is the file name of its description. Tests
  fail if a generated part is out of date.
- **One environment:** `uv sync` makes `.venv` with the package, the development tools and the
  packages that the research scripts import (`pyproject.toml`, groups `dev` and `research`).

## Making firmware

**All firmware that goes on a camera is made with `tools/make_firmware.py` (the same as
`epm2mod make`) from a build description.** Do not apply specs by hand for a flash. This is the same
command that the README gives to users, so every flash also tests the install path.

A build description is a file in `builds/`: what the build is, and the patch specs in order. The
build's name is the file name. `pinned-build.json` names the description of the last camera-tested
build.

1. **New build:** write `builds/NAME.json` with `what` and `specs`. Leave out `sha256` and
   `camera_tested`. Copy an existing description and change it.
2. **Make it:** `uv run tools/make_firmware.py builds/NAME.json`. For a build without a recorded
   sha256 the script runs `tools/freespace.py check` first, then prints the sha256 and says that the
   build is a candidate.
3. **Log it** in [camera-log.md](camera-log.md) with that sha256, then flash
   `build/card/DCOLYMP/E1019999.BIN` (or `build/NAME.BIN`).
4. **If the camera test passes:** `uv run tools/make_firmware.py builds/NAME.json --pin YYYY-MM-DD`.
   This writes the sha256 and the date into the description and makes it the pinned build. Then run
   `uv run epm2mod readme`, write the result in the camera log, and commit.
5. **If it fails:** write the result in the camera log. Keep or delete the description; never pin it.

The tests build every description that has a sha256 and compare the result.

## Camera-testing rule

Never flash a build that hasn't been recorded in [camera-log.md](camera-log.md) before and after: file, sha256, lamp timings, result. Keep the stock BIN at hand for recovery.
