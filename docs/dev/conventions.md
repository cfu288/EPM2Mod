# Conventions

See also: [feasibility.md](feasibility.md) (what is possible, the emulator), [todo.md](../../TODO.md) (open
work), [camera log](../camera-log/README.md) (every update done on a camera),
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
| `cli/src/epm2mod/` | The production package. It makes the firmware: container format, patch specs, stock download, build descriptions, build steps, film-spec generator, the look-file packer (`data/films/`), card writing (`cards.py`, `cardio.py`), the installer server (`serve.py`), release code (`release.py`, `releasing.py`), the log decoder (`eventlog.py`, `logsummary.py`). Command: `uv run epm2mod --help`, all commands in [cli.md](../reference/cli.md). See *Production code and research code*. |
| `tools/oetool.py` | The older command-line form of the container tool (unpack, pack, patch). It calls the package; `tools/_package.py` lets it import the package without an install. `gen/` and older scripts in `experiments/` import it. Do not use it to make firmware for a camera: use `uv run epm2mod make`. |
| `tools/freespace.py`, `tools/fwmap.py`, `tools/disasm.py`, `tools/memmap_svg.py`, `emulator/` | Analysis tools: the free-space check, the function database of block 0, MN103 disassembly (GNU objdump from `uv run epm2mod init`, which builds it from the submodule `third_party/binutils-gdb` into `build/toolchain/`), the memory map figure, the emulator harness. |
| `tools/ci.sh`, `tools/buildlint.py`, `tools/node.sh` | The hard checks, the soft report of a build (`epm2mod lint`), and the command that runs a program with the Node of `.nvmrc`. See *Checks*. |
| `tools/checks.py`, `.githooks/doclint.py`, `.claude/hooks/doc_links.py`, `docs/links.json`, `tools/toolchain.py` | `checks.py` runs the off-camera checks of a build: only those its specs call for, in parallel. It keeps no results. `doclint.py` checks the documents that users read. The pre-commit hook runs it on staged files. `doc_links.py` tells the agent which other files repeat a fact when it edits one of them (the groups are in `docs/links.json`). `toolchain.py` says where the MN103 binutils are. |
| `emulator/om-emu` | The emulator: our om-emu fork (branch `e101`, with the E-PM2's boot lab) as a git submodule; `uv run epm2mod init` initialises it. Emulator code goes into the fork, not into this repository. `emulator/boot-test` and `emulator/update-path-test` are the start-up checks of a build. |
| `data/builds/`, `data/pinned-build.json` | One description per firmware build, and the pointer to the last camera-tested build. See *Making firmware*. |
| `data/specs/` | One JSON spec per mod. Each operation states the bytes that it replaces. Specs never move: superseded and failed ones stay as a record, and `tools/space-ledger/superseded.tsv` marks them (`history` for those of earlier builds; their story is in `data/specs/HISTORY.md`). |
| `gen/` | The generators whose specs ship, each with its sources. `gen/run.sh --check` (CI) fails when a committed spec is not what its generator makes. See [../gen/README.md](../../gen/README.md). |
| `web/` | Two apps (React, Vite): `apps/site`, the public site (GitHub Pages, `.github/workflows/web.yml`), and `apps/local`, the installer page, served by `cli/src/epm2mod/serve.py`. `packages/ui` holds what they share. See [../web/README.md](../../web/README.md). |
| `data/films/` | `catalogue.json` (the film simulations), `card-looks.json` (a developer look list of fit files, the input of `epm2mod films pack`), `fits/` (the fitted values) and the generated `film-records.json`. |
| `data/logdict/` | The event dictionary of the Debug Log. The log's patch specs and the decoder (`epm2mod log`) read it. See [logging.md](../reference/logging.md). |
| `docs/` | Knowledge that lasts. Each fact there must have a source or must be reproducible. |
| `experiments/YYYY-MM-DD-slug/` | Ad-hoc scripts and `NOTES.md`. Put large files in the `out/` subfolder, which git ignores. When a result is reliable, move it into `docs/`, `tools/`, `gen/` or the package. |
| `cli/` | The Python project of the `epm2mod` package: `cli/pyproject.toml`, the package in `cli/src/epm2mod/`, the unittest suite in `cli/tests/` (see *Tests*). The root `pyproject.toml` is the uv workspace: one environment for the package and the research scripts. |
| `firmware/`, `build/` | Firmware files and build outputs. Git ignores them. `firmware/SHA256SUMS` is in git. |
| `.local/` | Files of this computer only, never committed: reference manuals, raw photos, drafts. |

## The project manifest

`epm2mod.json` at the top of a project names every file and folder that the `epm2mod` package reads or writes. The
package holds no other name of the project; a test scans the package for one. The commands use the nearest folder at
or above the current folder that holds `epm2mod.json`, or the folder that `--project DIR` names. A checkout and the
release folder each have one.

The manifest is one flat JSON object: a key for each location, and as its value a path relative to the manifest's
folder (a list of paths for `documents`, `workflows`, `emulator_checks` and `release_files`). The release folder's
manifest also has `release`, its version, and names only what the commands for camera owners use. Paths in build
descriptions, patch specs and film lists are data: they are also relative to the manifest's folder.

| Key | Location |
|---|---|
| `pinned`, `builds` | The pointer to the pinned build, and the build descriptions |
| `specs`, `label_spec` | The patch specs (every spec that a build or a film list names is in this folder), and the spec of the build label |
| `films`, `more_films`, `bw_films`, `card_looks`, `catalogue`, `film_records` | The film data: the film lists of older builds, the developer look list, the catalogue, the film records |
| `events` | The event dictionary of the Debug Log. The other JSON files in its folder are the dictionaries of older builds |
| `readme`, `documents`, `cli_reference`, `guides`, `site_features`, `camera_log` | The documents with generated parts, the CLI reference, the feature guides and the site's feature list, the camera log |
| `free_space_tool`, `emulator_checks`, `firmware_map` | The checks of a candidate build |
| `lint_tool` | The soft report of a build (`epm2mod lint`) |
| `toolchain`, `binutils_source`, `emulator`, `node_tool`, `firmware_map_tool`, `hooks`, `web` | What `epm2mod init` sets up or reports |
| `output` | The output folder (`make --out-dir DIR` replaces it) |
| `cache` | The folder that keeps Olympus's firmware (`--cache DIR` replaces it; `--stock FILE` uses a copy) |
| `app`, `package`, `release_files` | The installer page, the package, and the files at the top of the release zip |

## Production code and research code

- **`cli/src/epm2mod/` is production code.** It makes the firmware that goes on a camera. Rules:
  formatted with black (line length 88), type-checked with `mypy --strict`, a docstring on every
  module, class and function of the package (a test checks this; the test files need docstrings
  on helpers only where the name does not say enough), and a test for each behaviour (see *Tests*). The pre-commit hook
  formats the staged files that `cli/pyproject.toml` names and runs mypy. It also refuses machine paths and hosts
  in the staged changes, runs `.githooks/doclint.py` on the staged `.md` files and prettier on staged files of
  `web/`. `.githooks/commit-msg` checks the Conventional Commits form and removes AI attribution lines.

  The hook has one limit. `git commit PATH` and `git commit -a` do not commit the result of black.
  Run `git add` first, then `git commit` without paths.
- **`experiments/` is research code.** It may be rough. It may import the package; the package never
  imports from `experiments/`, and a build description may only name patch specs in `data/specs/`.
  When a result becomes part of how firmware is made, move the code into the package, the data into
  a folder of `data/` (as `data/films/` was) and the spec into `data/specs/`.
- **`tools/`** holds stand-alone scripts. `oetool.py` is a thin command over the package. The others
  (`freespace.py`, `fwmap.py`, `disasm.py`, `memmap_svg.py`) are analysis tools. `checks.py` runs the off-camera
  checks of a build and `toolchain.py` finds the MN103 binutils. The emulator harness is in `emulator/`.
- **Generated, not written by hand:** the parts of the documents between `GENERATED` markers and
  the CLI reference [cli.md](../reference/cli.md): `uv run epm2mod generate` writes them. `data/films/film-records.json`
  comes from `data/films/catalogue.json` and the fits: `uv run python web/scripts/export_films.py` writes it. A build's
  name is the file name of its description. Tests
  fail if a generated part is out of date.
- **One environment:** `uv sync` makes `.venv` with the package and the development tools (`pyproject.toml`,
  group `dev`). The scripts in `experiments/` need more packages: `uv sync --group research` adds them, and a
  later `uv sync` without the option removes them.

## Making firmware

**All firmware that goes on a camera is made by `epm2mod make` or `epm2mod install` from a build
description.** Both run the same steps (`pipeline.firmware`). Do not apply specs by hand for a flash.
Write a candidate to the card with `install`, the command that the README gives to users, so every
flash also tests the install path.

A build description is a file in `data/builds/`: what the build is, and the patch specs in order. The
build's name is the file name. `data/pinned-build.json` names the description of the last camera-tested
build.

1. **New build:** write `data/builds/NAME.json` with `what` and `specs` (files in `data/specs/`). Leave out
   `sha256` and `camera_tested`. Copy the pinned build's description and change it: the free-space check
   knows the specs of the pinned build, and it refuses most older builds.
2. **Make it:** `uv run epm2mod make NAME`. For a build without a recorded
   sha256 the script runs `tools/freespace.py check` first, then prints the sha256 and says that the
   build is a candidate. The check needs the firmware map in `build/map/`, which a fresh clone
   does not have. To make the map: `uv run python tools/fwmap.py build` (about 1 minute, 470 MB). This needs GNU objdump for the
   MN103 processor (`uv run epm2mod init`, which builds it from the submodule `third_party/binutils-gdb` into `build/toolchain/`).

   The command then starts the result in the emulator (`emulator/boot-test`, `emulator/update-path-test`). When
   a start-up check fails or cannot run (the emulator is not set up: `uv run epm2mod init`), the build is not made
   (exit status 6 for "cannot run"). No flag overrides this.

   A tested build does not need the map or the emulator: its result is compared with the recorded sha256.

   The check also refuses new code in an area where no camera-tested build runs code yet, because
   only a flash can show that code runs there. When a build is meant to be that test, add
   `"first_code": true` to its description. The script then accepts the area if it passes every
   static check, and prints a FIRST CODE line. Say in the camera log which area is new.
3. **Log it** in the [camera log](../camera-log/README.md) with that sha256. Write it to the card with
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

A release is made on GitHub by the workflow `.github/workflows/release.yml`, which a person starts by hand. A merge
to main does not release. Nobody pushes a tag: the workflow creates it, and a tag pushed by hand starts nothing.

```sh
uv run epm2mod release                                   # the local preview: ready or not, the version, the notes
gh workflow run release.yml -f kind=rc                                    # a dry run: everything but the tag and the publication
gh workflow run release.yml -f kind=rc -f day=YYYY.MM.DD -f dry_run=false  # the release, with the day that the dry run printed
```

The day decides the version and the image. Without `day` it is today in UTC, so a release started after midnight
UTC would not be the one a dry run checked the day before: pass the day.

1. **The version is the day of the release** (the input `day`, `epm2mod release --day`; default today in UTC): `vYYYY.MM.DD-rc.N`. N is 1 for the first release of a day and
   one more than the highest existing tag of that day after that. Every release is a pre-release (`-rc.N`) for now;
   `kind=final` (`epm2mod release --final`) gives a plain `vYYYY.MM.DD`. A test release of a camera-tested build that
   is not pinned (`-f build=NAME`, `epm2mod release --build NAME`) is `vYYYY.MM.DD-NAME.N`; record its test first
   with `uv run epm2mod pin NAME --no-pin --date YYYY-MM-DD --sha256 HEX`.
2. **The Firmware screen shows the same date.** A build's `"label"` (with the spec `data/specs/build-label.json`) is
   the date on its Firmware screen ("Body : 1.6  EPM2Mod 2026.11.19"). The release holds the pinned, camera-tested
   build with the label set to the day of the release (`release.stamp`). So the label of the description does not
   have to be the release's day. When it is that day already, the tested image is released as it is; the checks of
   item 3 run on it all the same.
3. **The stamped image is not the image that was on the camera.** The tool releases it only when all of this holds,
   and stops when one does not:
   - it differs from the camera-tested image (the pinned sha256) only in the 20 bytes of the date and in the
     checksum of block 0 (`release.check_only_the_label_differs`; the date has a fixed length, so nothing moves);
   - the free-space check, which holds the load-order check, passes on the build's specs. It reads the specs and
     not the image, and the specs are the tested build's: this shows that they pass today's rules. The stamped
     bytes are text in late-loaded segment 2, which the first rule covers;
   - `emulator/boot-test` and `emulator/update-path-test` pass on it.
   The release notes give both: "Firmware: EPM2Mod LABEL, sha256 RELEASED. Camera-tested as sha256 TESTED (label
   L); differs only in the Firmware-screen date." The zip's manifest records the tested sha256 and label under
   `camera_tested_as`, and the zip's build description holds the released sha256, which the installer checks.
   The description in `data/builds/` is not changed.
4. **`epm2mod release` checks** that the build has a camera test and a file in `docs/camera-log/`, the tree is clean
   and at `origin/main`, the generated documents and the feature lists are current, and the newest `python`, `web`
   and `package` runs on main passed. It writes the notes: the firmware line, the build's description, the feat and
   fix commits since the last release, and "The camera-tested firmware is unchanged since vX" when it is.
5. **The workflow** runs that command (job `plan`), makes the zip and the Mac disk image and starts them on three
   systems (`package.yml`), and then creates the tag and the GitHub release in one step (`gh release create`), unless
   `dry_run` is true, the default.

`uv run epm2mod package --release-version V` makes the same zip locally, without publishing. `package.yml` also runs
for pull requests and main, as a check, with the version `DATE-dev` (the commit's date): a `-dev` zip holds the tested
image as it is.

A release also publishes `EPM2Mod-V.dmg` for Macs (job `dmg` of `package.yml`, `release/mac/make-dmg.sh`): EPM2Mod.app
with the zip's folder in it, signed with the owner's Developer ID Application certificate and notarized by Apple, so
macOS opens it without Open Anyway. The signing secrets are in the GitHub environment `release`: `MAC_CERT_P12` (the
certificate and its key as a base64 `.p12`), `MAC_CERT_PASSWORD`, `APPLE_ID`, `APPLE_TEAM_ID` and
`APPLE_APP_PASSWORD`. The environment must allow the branch `main` (the workflow runs there, not on a tag) and
should require the owner's approval. If the certificate expires or the Apple Developer membership lapses, the job
fails and nothing is published. Renew it, then set the secrets again with `gh secret set NAME --env release`. On a
Mac, `release/mac/make-dmg.sh ZIP` makes the disk image locally, signed ad hoc unless `EPM2MOD_SIGN_IDENTITY` and
`EPM2MOD_NOTARY_PROFILE` are set.

## Checks

Three layers. Each check is in one of them.

| Layer | What | Where |
|---|---|---|
| Commit hooks | Fast and hard: machine paths, the document rules, prettier, black, mypy, the commit message. And one soft part: `epm2mod lint` of each staged build description, which prints warnings and never refuses | `.githooks/` |
| Hard checks | `tools/ci.sh`: `epm2mod init --check` first (the set-up is the pinned one, and a variable that replaces a pinned tool is refused), then black, mypy, the unit tests (they hold pyflakes on the scripts, the document rules and the feature lists), the generated documents, the code-space map and the generated specs (a spec that git does not hold fails), the web checks. Then, for the pinned build and each build description that differs from the base commit, committed or not (the script prints the list): `epm2mod make` and the quick tier of `tools/checks.py` (free space with load order, op check, `boot-test`, `update-path-test`). A check that cannot run fails. No warnings | CI (`python.yml`, `web.yml`) runs this script and nothing else. Run it before a pull request |
| Soft report | `uv run epm2mod lint NAME` (`tools/buildlint.py`): the allow-list rows of the load-order check that the build uses and that are safe by timing or inference only, the early-loaded space it uses, first code, words in new early-loaded bytes that can be late-loaded addresses, the cold start for the camera test. Exit status 0 with any number of warnings, 6 when the report cannot be made | by hand and from the commit hook. Never in CI |

`tools/checks.py NAME.json --tier full` adds the scenario runs of `emulator/scenarios/` (20 minutes). Run it before a
build is offered for a flash. Its WARN results have RESULT lines that a person reads.

`tools/checks.py` keeps no results and makes the build again in memory first: it stops when `build/NAME.BIN` is not
what the description and its specs make now. No build is exempt from a check. When a newer check refuses a
camera-tested build that a pull request must touch, the pull request says so and the owner decides.

The quick tier runs `boot-test --strict-times`: time stamps that moved are a FAIL there, not a line to read.

`emulator/hookcheck-allow.tsv` accepts a transfer by its address and its target together, one word per entry. The
same address with another target fails. The check's last line counts the entries that match nothing in the build.

What decides a check's result is pinned where it can be:

| Tool | Pinned by |
|---|---|
| Node | `.nvmrc`, a full version, matched exactly by `tools/node.sh` (the emulator, the web checks, CI). A test holds `web/package.json` `engines` to it |
| The MN103 objdump | Built from the submodule `third_party/binutils-gdb`. `epm2mod init` records the source commit in `build/toolchain/source-commit` and reports the build as missing when it is another one. An objdump on PATH is never used; `EPM2_BINUTILS` is said on stderr in each run |
| The emulator | The submodule `emulator/om-emu`; `epm2mod init --check` compares its commit |
| Python packages, npm packages | `uv.lock` (`uv sync --locked` in CI), `web/package-lock.json` (`npm ci`) |
| uv, Python, actions and runner images in CI | uv by version and wheel hash (`.github/uv-requirements.txt`), Python by its full version, actions by commit, images by release (`ubuntu-24.04`) |

Not pinned: bison, flex and texinfo, which build the objdump in CI (`apt-get` gives the image's versions and Ubuntu
keeps no old ones to name; the built objdump's version line is in the run's log); the patch level of the runner
images; a contributor's own Python (3.10 or newer) and gcc.

Production tools and checks do not import or run anything under `experiments/`. A check script or an input that a
tool needs moves to `emulator/`, `tools/` or `data/`.

## Tests

`uv run python -m unittest discover -s cli/tests` runs all tests. What a test run proves depends on
what is there:

| Needs | What the tests prove |
|---|---|
| Nothing more than the repository | The package works on a small made-up firmware: container, patch specs, build steps, card copy, download (with a stand-in for the network), every command. The README's generated parts are current. The film specs record the digest of the film list and fit files that are in the repository. |
| numpy (`uv run` installs it) | Look packs made from the fit files are the ones the film records hold (`cli/tests/test_lookfile.py`). |
| The maker's firmware file (`uv run epm2mod fetch-stock`) | Each build description that has a sha256 gives that sha256. The stock file survives a parse and a write without a change. |
| The built installer page (`cd web && npm ci && npm run build:app`) | The release zip holds the page and installs from it. |

Without one of these files the run skips its tests, and each skip names the command that makes the file
(`cli/tests/support.py`, `needs`). When the environment has `CI`, the same tests fail: CI does not skip. Run the
full set before you pin a build. A test that is skipped because it is a bad test is deleted.

## Camera-testing rule

Never flash a build that hasn't been recorded in the [camera log](../camera-log/README.md) before and after: file, sha256, lamp timings, result. Keep the stock BIN at hand for recovery.
