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

| Path | What |
|---|---|
| `src/epm2mod/` | The production package. It makes the firmware: container format, patch specs, stock download, build descriptions, build steps, film-spec generator. Command: `uv run epm2mod --help`. See *Production code and research code*. |
| `tools/make_firmware.py`, `tools/fetch_stock.py` | The two main commands of the package as stand-alone scripts. `tools/_package.py` lets them import the package without an install. |
| `tools/build.py`, `tools/oetool.py` | Older command-line forms. They call the package. Older scripts in `tools/` and `experiments/` import them. Do not use them to make firmware for a camera. |
| `tools/freespace.py`, `tools/fwmap.py`, `tools/disasm.py`, `tools/memmap_svg.py`, `tools/emu/` | Analysis tools: the free-space check, the function database of block 0, MN103 disassembly (GNU objdump from `scripts/build-binutils-mn10300.sh`), the memory map figure, the emulator harness. |
| `builds/`, `pinned-build.json` | One description per firmware build, and the pointer to the last camera-tested build. See *Making firmware*. |
| `patches/` | One JSON spec per mod. Each operation states the bytes that it replaces. `patches/history/` holds superseded and failed specs as a record. |
| `looks/` | The film list and the fitted values. The three film patch specs are generated from them. |
| `docs/` | Knowledge that lasts. Each fact there must have a source or must be reproducible. |
| `experiments/YYYY-MM-DD-slug/` | Ad-hoc scripts and `NOTES.md`. Put large files in the `out/` subfolder, which git ignores. When a result is reliable, move it into `docs/`, `tools/` or the package. |
| `tests/` | The unittest suite. See *Tests*. |
| `firmware/`, `build/` | Firmware files and build outputs. Git ignores them. `firmware/SHA256SUMS` is in git. |

## Production code and research code

- **`src/epm2mod/` is production code.** It makes the firmware that goes on a camera. Rules:
  formatted with black (line length 88), type-checked with `mypy --strict`, a docstring on every
  module, class and function of the package (a test checks this; the test files need docstrings
  on helpers only where the name does not say enough), and a test for each behaviour (see *Tests*). The pre-commit hook
  formats the staged files of the package and its tests and runs mypy. To run the checks by hand:

  ```bash
  uv run black src tests/support.py tests/test_package.py tests/test_looks.py
  uv run mypy
  uv run python -m unittest discover -s tests
  ```

  The hook has one limit. `git commit PATH` and `git commit -a` do not commit the result of black.
  Run `git add` first, then `git commit` without paths.
- **`experiments/` is research code.** It may be rough. It may import the package; the package never
  imports from `experiments/`, and a build description may only name patch specs in `patches/`.
  When a result becomes part of how firmware is made, move the code into the package, the data into
  a top-level folder (as `looks/` was) and the spec into `patches/`.
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

1. **New build:** write `builds/NAME.json` with `what` and `specs` (files in `patches/`). Leave out
   `sha256` and `camera_tested`. Copy an existing description and change it.
2. **Make it:** `uv run tools/make_firmware.py builds/NAME.json`. For a build without a recorded
   sha256 the script runs `tools/freespace.py check` first, then prints the sha256 and says that the
   build is a candidate. The check needs the firmware map in `build/map/`, which a fresh clone
   does not have. To make the map: `python3 tools/fwmap.py build`. This needs GNU objdump for the
   MN103 processor (`scripts/build-binutils-mn10300.sh`).

   A tested build does not need the map: its result is compared with the recorded sha256.
3. **Log it** in [camera-log.md](camera-log.md) with that sha256, then flash
   `build/card/DCOLYMP/E1019999.BIN` (or `build/NAME.BIN`).
4. **If the camera test passes:**
   `uv run epm2mod pin builds/NAME.json --date YYYY-MM-DD --sha256 THE_SHA256_FROM_THE_LOG`.
   The command makes the build again in memory and records the test only if the result has that
   sha256, so a spec that changed after the flash cannot be recorded as tested. It writes the sha256
   and the date into the description and makes it the pinned build. Then:
   - run `uv run epm2mod readme`. It refreshes the generated parts of `README.md`.
   - update the parts of `README.md` that are written by hand: the feature table at the top, step 8
     of the install steps (what the user sees after the update), and "Limits of this build".
   - write the result in the camera log, and commit.
5. **If it fails:** write the result in the camera log. Keep or delete the description; never pin it.

A test record is never changed. A build that changes after its test gets a description with a new
name.

## Tests

`uv run python -m unittest discover -s tests` runs all tests. What a test run proves depends on
what is there:

| Needs | What the tests prove |
|---|---|
| Nothing more than the repository | The package works on a small made-up firmware: container, patch specs, build steps, card copy, download (with a stand-in for the network), every command. The README's generated parts are current. The film specs record the digest of the film list and fit files that are in the repository. |
| numpy (`uv run` installs it) | The film-spec generator works on a made-up firmware (`tests/test_looks.py`). |
| The maker's firmware file (`uv run tools/fetch_stock.py`) | Each build description that has a sha256 gives that sha256. The film specs in `patches/` are exactly the generated ones. The stock file survives a parse and a write without a change. |

Without the maker's firmware file the run skips the last group and says so. Run the full set before
you pin a build.

## Camera-testing rule

Never flash a build that hasn't been recorded in [camera-log.md](camera-log.md) before and after: file, sha256, lamp timings, result. Keep the stock BIN at hand for recovery.
