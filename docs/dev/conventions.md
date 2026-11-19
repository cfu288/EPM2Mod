# Conventions

See also: [feasibility.md](feasibility.md) (what is possible, the emulator), [todo.md](../../TODO.md) (open
work), [camera-log.md](../camera-log/README.md) (every update done on a camera),
[../builds/README.md](../../data/builds/README.md) (the tested builds), [../AGENTS.md](../../AGENTS.md) (rules for AI
agents), [../NOTICE.md](../../NOTICE.md) (licences and credits).

## Commit messages

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

Suggested scopes: `card-looks`, `web`, `peaking`, `looks`, `camera-log`, and for `exp` the experiment's slug (`exp(cli-redesign)`).

Examples: `feat(cli)!: revision 3 of the CLI spec`, `docs(camera-log): the build label works; the Lens line is offset`.

## Where things go

| Path | What |
|---|---|
| `src/epm2mod/` | The production package. It makes the firmware: container format, patch specs, stock download, build descriptions, build steps, film-spec generator, the look-file packer (`data/films/`), card writing (`cards.py`, `cardio.py`), the installer server (`serve.py`), release code (`release.py`, `releasing.py`), the log decoder (`eventlog.py`, `logsummary.py`). Command: `uv run epm2mod --help`, all commands in [cli.md](../reference/cli.md). See *Production code and research code*. |
| `tools/oetool.py` | The older command-line form of the container tool (unpack, pack, patch). It calls the package; `tools/_package.py` lets it import the package without an install. `gen/` and older scripts in `experiments/` import it. Do not use it to make firmware for a camera: use `uv run epm2mod make`. |
| `tools/freespace.py`, `tools/fwmap.py`, `tools/disasm.py`, `tools/memmap_svg.py`, `emulator/` | Analysis tools: the free-space check, the function database of block 0, MN103 disassembly (GNU objdump from `tools/setup.sh`, which builds it from the submodule `third_party/binutils-gdb` into `build/toolchain/`), the memory map figure, the emulator harness. |
| `tools/checks.py`, `.githooks/doclint.py`, `.claude/hooks/doc_links.py`, `docs/links.json`, `tools/toolchain.py` | `checks.py` runs the off-camera checks of a build: only those its specs call for, in parallel, with a cache. `doclint.py` checks the documents that users read. The pre-commit hook runs it on staged files. `doc_links.py` tells the agent which other files repeat a fact when it edits one of them (the groups are in `doc_links.json`). `toolchain.py` says where the MN103 binutils are. |
| `emulator/om-emu`, `emulator/setup.sh` | The emulator: our om-emu fork (branch `e101`, with the E-PM2's boot lab) as a git submodule, and the command that initialises it. Emulator code goes into the fork, not into this repository. `emulator/boot-test` and `emulator/update-path-test` are the start-up checks of a build. |
| `data/builds/`, `data/pinned-build.json` | One description per firmware build, and the pointer to the last camera-tested build. See *Making firmware*. |
| `data/specs/` | One JSON spec per mod. Each operation states the bytes that it replaces. Specs never move: superseded and failed ones stay as a record, and `tools/space-ledger/superseded.tsv` marks them (`history` for those of earlier builds; their story is in `data/specs/HISTORY.md`). |
| `gen/` | The generators whose specs ship, each with its sources. `gen/run.sh --check` (CI) fails when a committed spec is not what its generator makes. See [../gen/README.md](../../gen/README.md). |
| `web/` | Two apps (React, Vite): `apps/site`, the public site (GitHub Pages, `.github/workflows/web.yml`), and `apps/local`, the installer page, served by `src/epm2mod/serve.py`. `packages/ui` holds what they share. See [../web/README.md](../../web/README.md). |
| `data/films/` | `catalogue.json` (the film simulations), `card-looks.json` (a developer look list of fit files, the input of `epm2mod films pack`), `fits/` (the fitted values) and the generated `film-records.json`. `films.json` and `more-films.json` serve older builds. |
| `data/logdict/` | The event dictionary of the Debug Log. The log's patch specs and the decoder (`epm2mod log`) read it. See [logging.md](../reference/logging.md). |
| `docs/` | Knowledge that lasts. Each fact there must have a source or must be reproducible. |
| `experiments/YYYY-MM-DD-slug/` | Ad-hoc scripts and `NOTES.md`. Put large files in the `out/` subfolder, which git ignores. When a result is reliable, move it into `docs/`, `tools/`, `gen/` or the package. |
| `tests/` | The unittest suite. See *Tests*. |
| `firmware/`, `build/` | Firmware files and build outputs. Git ignores them. `firmware/SHA256SUMS` is in git. |
| `.local/` | Files of this computer only, never committed: reference manuals, raw photos, drafts. |

## Production code and research code

- **`src/epm2mod/` is production code.** It makes the firmware that goes on a camera. Rules:
  formatted with black (line length 88), type-checked with `mypy --strict`, a docstring on every
  module, class and function of the package (a test checks this; the test files need docstrings
  on helpers only where the name does not say enough), and a test for each behaviour (see *Tests*). The pre-commit hook
  formats the staged files of the package and its tests and runs mypy. It also refuses machine paths and hosts
  in the staged changes, and runs `.githooks/doclint.py` on the staged `.md` files. `.githooks/commit-msg` checks the
  Conventional Commits form and removes AI attribution lines. To run the checks by hand:

  ```bash
  uv run black src tests/support.py tests/test_package.py tests/test_looks.py
  uv run mypy
  uv run python -m unittest discover -s tests
  ```

  The hook has one limit. `git commit PATH` and `git commit -a` do not commit the result of black.
  Run `git add` first, then `git commit` without paths.
- **`experiments/` is research code.** It may be rough. It may import the package; the package never
  imports from `experiments/`, and a build description may only name patch specs in `data/specs/`.
  When a result becomes part of how firmware is made, move the code into the package, the data into
  a top-level folder (as `data/films/` was) and the spec into `data/specs/`.
- **`tools/`** holds stand-alone scripts. `make_firmware.py`, `fetch_stock.py`, `build.py` and
  `oetool.py` are thin commands over the package. The others (`freespace.py`, `fwmap.py`,
  `disasm.py`, `memmap_svg.py`, `emu/`) are analysis tools. `checks.py` runs the off-camera checks of a build,
  `doclint.py` checks the documents that users read, `doc_links.py` names the files that repeat a fact, and
  `toolchain.py` finds the MN103 binutils.
- **Generated, not written by hand:** the parts of the documents between `GENERATED` markers and
  the CLI reference [cli.md](../reference/cli.md) and the film patch specs of the older builds (from `data/films/films.json`,
  `data/films/more-films.json` and `data/films/fits/`): `uv run epm2mod generate` writes them. `data/films/film-records.json`
  comes from `data/films/catalogue.json` and the fits: `uv run python web/scripts/export_films.py` writes it. A build's
  name is the file name of its description. Tests
  fail if a generated part is out of date.
- **One environment:** `uv sync` makes `.venv` with the package, the development tools and the
  packages that the research scripts import (`pyproject.toml`, groups `dev` and `research`).

## Making firmware

**All firmware that goes on a camera is made by `epm2mod make` or `epm2mod install` from a build
description.** Both run the same steps (`pipeline.firmware`). Do not apply specs by hand for a flash.
Write a candidate to the card with `install`, the command that the README gives to users, so every
flash also tests the install path.

A build description is a file in `data/builds/`: what the build is, and the patch specs in order. The
build's name is the file name. `data/pinned-build.json` names the description of the last camera-tested
build.

1. **New build:** write `data/builds/NAME.json` with `what` and `specs` (files in `data/specs/`). Leave out
   `sha256` and `camera_tested`. Copy an existing description and change it.
2. **Make it:** `uv run epm2mod make NAME`. For a build without a recorded
   sha256 the script runs `tools/freespace.py check` first, then prints the sha256 and says that the
   build is a candidate. The check needs the firmware map in `build/map/`, which a fresh clone
   does not have. To make the map: `python3 tools/fwmap.py build`. This needs GNU objdump for the
   MN103 processor (`tools/setup.sh`, which builds it from the submodule `third_party/binutils-gdb` into `build/toolchain/`).

   A tested build does not need the map: its result is compared with the recorded sha256.

   The check also refuses new code in an area where no camera-tested build runs code yet, because
   only a flash can show that code runs there. When a build is meant to be that test, add
   `"first_code": true` to its description. The script then accepts the area if it passes every
   static check, and prints a FIRST CODE line. Say in the camera log which area is new.
3. **Log it** in [camera-log.md](../camera-log/README.md) with that sha256. Write it to the card with
   `uv run epm2mod install --card DIR --build NAME --allow-untested`, then flash it.
4. **If the camera test passes:**
   `uv run epm2mod pin NAME --date YYYY-MM-DD --sha256 THE_SHA256_FROM_THE_LOG`.
   The command makes the build again in memory and records the test only if the result has that
   sha256, so a spec that changed after the flash cannot be recorded as tested. It writes the sha256
   and the date into the description and makes it the pinned build. Then:
   - run `uv run epm2mod generate`. It refreshes the generated parts of the documents
     (`README.md`, `docs/user/install.md`, `docs/guide/film-looks.md`, `data/builds/README.md`, `docs/reference/cli.md`).
   - update what is written by hand: the feature list in `README.md` (one line and a link per
     feature), the feature's guide in `docs/guide/` (how to switch it on and use it, with
     screenshots from the emulator, and its limits).
   - write the result in the camera log, and commit.
5. **If it fails:** write the result in the camera log. Keep or delete the description; never pin it.

A test record is never changed. A build that changes after its test gets a description with a new
name.

## Releases

A release is a tag; GitHub makes, tests and publishes it (`.github/workflows/release.yml`).

1. Give the candidate build a label, the date its Firmware screen shows: `"label": "2026.11.19"` and the spec
   `data/specs/build-label.json` in `data/builds/NAME.json` (the screen then reads "Body : 1.6  EPM2Mod 2026.11.19"). The label
   is part of the firmware, so it is set before the camera test. Pin the camera-tested build (`uv run epm2mod pin ...`)
   and push.
2. `uv run epm2mod release --dry-run` checks and shows the release: the pinned build has a camera test and a row in
   `docs/camera-log/`, the tree is clean and pushed, the generated documents and the feature lists are current,
   and the newest CI runs on main passed. It names the version from the label (`v2026.11.19-rc.N`, or `v2026.11.19`
   with `--final`) and writes the notes: the build, the feat and fix commits since the last tag, the sha256.
3. `uv run epm2mod release --push` tags and pushes it. The tag's message becomes the release notes.

`uv run epm2mod package --release-version V` makes the same zip locally, without publishing. It refuses a version that does not start with
the pinned build's label.

## Tests

`uv run python -m unittest discover -s tests` runs all tests. What a test run proves depends on
what is there:

| Needs | What the tests prove |
|---|---|
| Nothing more than the repository | The package works on a small made-up firmware: container, patch specs, build steps, card copy, download (with a stand-in for the network), every command. The README's generated parts are current. The film specs record the digest of the film list and fit files that are in the repository. |
| numpy (`uv run` installs it) | The film-spec generator works on a made-up firmware (`tests/test_looks.py`). |
| The maker's firmware file (`uv run epm2mod fetch-stock`) | Each build description that has a sha256 gives that sha256. The film specs in `data/specs/` are exactly the generated ones. The stock file survives a parse and a write without a change. |

Without the maker's firmware file the run skips the last group and says so. Run the full set before
you pin a build.

## Camera-testing rule

Never flash a build that hasn't been recorded in [camera-log.md](../camera-log/README.md) before and after: file, sha256, lamp timings, result. Keep the stock BIN at hand for recovery.
