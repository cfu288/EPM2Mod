# Engineering plan

An audit of how the repository is built, checked and released, and a plan to clean it up. The text below the
status table is the plan as written before the work: sections A and B describe the repository at the audited
commit, not today's.

**Status, 2026-11-25** (branch `chore/engineering-cleanup`). The current rules are in
[conventions.md](conventions.md), sections Checks and Releases. Where the work differs from the plan:

| Plan | What was done |
|---|---|
| Step 1, `tools/setup.sh` | `uv run epm2mod init` and `init --check` replace `tools/setup.sh` and `emulator/setup.sh` |
| Step 3, `--allow-unchecked` | No flag: `make` stops (exit status 6) when a start-up check cannot run |
| Step 6, a cache for the stock firmware | Not done: Olympus's firmware is downloaded in each run and stored nowhere |
| Step 8, a file of waived builds | Not done: no build is exempt |
| Step 10 | Also dropped: the checks of the superseded spec families films12 and log-core |
| Step 11, `epm2mod check`, the cache of `tools/checks.py` | No `check` command. `tools/checks.py` keeps no results. The allow list names each word with its target |
| Step 13, `epm2mod release --dry-run`, the version from the label | `epm2mod release` only plans (`--json`, `--day`); `--dry-run` and `--push` are gone. The version is the day of the release, and the release holds the pinned build with that day as its label |
| Layer 4, "Everything else follows from the commit" | The version and the image also follow from the day: the input `day` of `release.yml` |

Open: the full tier of `tools/checks.py` shows `save-guard` FAIL and S6 FAIL on the pinned build (hidden behind SKIP
before); the workflows have not run on GitHub yet; the environment `release` must allow `main`.

**The plan as written.** Nothing in it was done at that time. Date: 2026-11-25. Audited commit: `3b68278` (main). The fresh-clone test ran on `ccbad1a`, one merge
earlier; the files it used did not change in between.

Labels: **V** verified (a command was run, or the file says so), **I** inferred, **U** unknown.

The target has four layers:

1. **CLI**: local development, tests, builds. As far from the checkout as it can be.
2. **Commit hooks**: format and lint, and a soft check that warns when a build may be harmful.
3. **CI**: hard checks and hard blocks. Deterministic. No soft findings, no warnings.
4. **Release**: a manual `workflow_dispatch`. A merge to main does not release. Deterministic but for the text.

And one rule over all four: a person who clones the repository and opens a pull request can run every layer.

## A. Current state per layer

| Layer | What exists | Files |
|---|---|---|
| CLI | The package `epm2mod`: standard library only, 17 commands, typed, tested (280 tests). It finds the project by the manifest `epm2mod.json` and holds no other path of the project. A wheel of it runs outside a checkout with `--project DIR` (V). `make` of a candidate starts three scripts of the checkout by path. | `cli/pyproject.toml`, `cli/src/epm2mod/` (`paths.py`, `cli.py`, `pipeline.py`), `epm2mod.json`, `docs/reference/cli.md` |
| CLI, scripts beside it | Set-up, the free-space check, the firmware map, the disassembler, the check runner, the generators, the emulator harness. Research style: no black, no mypy. | `tools/setup.sh`, `tools/freespace.py`, `tools/fwmap.py`, `tools/checks.py`, `tools/toolchain.py`, `tools/space-ledger/*.tsv`, `gen/run.sh`, `emulator/` (`setup.sh`, `hookcheck.py`, `boot-test`, `update-path-test`, submodule `emulator/om-emu`) |
| Commit hooks | `pre-commit`: refuses machine paths, runs `doclint.py` on staged `.md`, black and mypy on the package. `commit-msg`: Conventional Commits, removes AI attribution lines. Switched on by `tools/setup.sh` or by hand. All hard. No soft check. | `.githooks/pre-commit`, `.githooks/commit-msg`, `.githooks/doclint.py` |
| Agent hook | Names the files that repeat a fact when the agent edits one of them. Runs for Claude Code only. | `.claude/settings.json`, `.claude/hooks/doc_links.py`, `docs/links.json` |
| CI | `python`: black, mypy, unit tests, a cold `make` of the pinned build; `gen/run.sh --check`, the firmware map, the free-space check of the pinned build. `web`: prettier, eslint, tsc, vitest, both builds, Playwright; deploys the site from main. `release` on pull requests and main: builds the zip, starts it on three systems, makes the disk image. | `.github/workflows/python.yml`, `web.yml`, `release.yml`, `.github/scripts/release_smoke.py` |
| Release | `uv run epm2mod release --push` on the owner's computer checks the tree and CI, names the version, writes the notes into an annotated tag and pushes it. The tag push starts `release.yml`, which builds, smoke-tests, signs and publishes. | `cli/src/epm2mod/releasing.py`, `release.py`, `.github/workflows/release.yml`, `release/` (launchers, `mac/make-dmg.sh`, `NOTES.md`) |
| Data | Build descriptions, the pinned pointer, patch specs, film data, the event dictionary. Git ignores the firmware and `build/`. | `data/builds/`, `data/pinned-build.json`, `data/specs/`, `data/films/`, `data/logdict/`, `firmware/SHA256SUMS`, `.gitignore` |

## B. Findings

### The fresh-clone test

A clone of origin into an empty folder, with only the steps of `README.md`, `CONTRIBUTING.md` and `web/README.md`.
The computer: Linux, uv 0.13.7, gcc and make, no bison or flex, Node 22 as the default and Node 26 in nvm. All V.

| Step | Result | Time |
|---|---|---|
| `git clone` | pass | 6 s |
| `uv run python -m unittest discover -s cli/tests`, before set-up | pass, **16 skipped** | 14 s |
| `uv run epm2mod fetch-stock` | pass: 43 MB from `dl01.om-digitalsolutions.net`, sha256 checked | 2 s |
| `tools/setup.sh` | pass: built binutils, fetched bison and flex with `apt-get download`, found Node 26 in nvm, initialised `emulator/om-emu` | 73 s |
| `uv run python tools/fwmap.py build` | pass | 54 s |
| unit tests again | pass, **6 skipped** (they need the built app page) | 70 s |
| black, mypy, `epm2mod generate --check` | pass | 4 s |
| `gen/run.sh --check` | pass. Two generators print "no E-PL6 firmware" and skip a comparison | 30 s |
| `uv run epm2mod make spot-af-2` (the pinned build then) | pass, the recorded sha256 | 2 s |
| a candidate: the pinned description without `sha256` and `camera_tested`, then `epm2mod make` | pass: free-space check, `boot-test`, `update-path-test` | 22 s |
| `tools/checks.py`, tier quick | 4 PASS | 13 s |
| `tools/checks.py --tier full` | 4 PASS, **3 SKIP**: "needs build/peaking-fast.BIN" | 0 s |
| `emulator/hookcheck.py`, `emulator/boot-test`, `emulator/update-path-test` | pass | 15 s |
| `npm ci` in `web/`, with the default Node 22 | pass with `npm warn EBADENGINE` | 3 s |
| `npm run check`, Node 22 | **FAIL**: prettier and eslint pass, then vitest: "Failed to start forks worker ... Cannot read properties of undefined (reading 'bind')" | 20 s |
| `npm run build:app`, Node 22 | pass | 1 s |
| `npm run e2e`, Node 22 | **FAIL**: "Timed out waiting 60000ms from config.webServer" | 67 s |
| `npm run check` and `npm run e2e`, Node 26 on PATH | pass. The Playwright browser was on the computer already | 40 s |
| `npm run check`, Node 24 | pass | 20 s |
| unit tests, after `build:app` | pass, 0 skipped | 70 s |

Size after all steps: 2.1 GB (`build/` 765 MB, `third_party/` 336 MB, `.git` 315 MB, `web/node_modules` 265 MB, `.venv`
146 MB).

**The firmware path works.** A contributor gets from a clone to a checked candidate build in about four minutes,
and no step of it failed. **The web path fails** on a computer whose default Node is older than 24, with errors
that do not name Node (H3). The other gaps are in what the steps hide, skip or leave out.

### Hidden dependencies

| Id | Finding | Evidence | Cost to a contributor |
|---|---|---|---|
| H1 | **Four checks run scripts in `experiments/`.** The full tier of the check runner takes its scenario and colour-stage scripts from four experiment folders. Those scripts need reference images that no step makes. | V: `tools/checks.py` lines 35 to 38 (`PEAKING`, `FILMS`, `DOUBLEX`, `LOG`). V: `checks.py --tier full` gave 3 SKIP, exit status 0. | The full tier looks green and has not run. A clean-up of `experiments/` breaks a check. |
| H2 | **The free-space check reads `experiments/` and a document folder.** Its ledger takes specs from `experiments/*/patches/*.json` (6 files) and `emulator/specs/`, and reads `docs/camera-log/` for the areas where code has run. | V: `tools/freespace.py` `SPEC_GLOBS`, `CAMERA_LOG`. | A note or an experiment file can change the verdict of a build check. |
| H3 | **Node: the set-up says "present" and the web checks then fail.** `tools/setup.sh` finds Node 26 in nvm and reports it, but the shell's `node` stays the default. `npm ci` on that Node only warns. `.nvmrc` says 26, `web/package.json` says `>=24.15`, `emulator/emuenv.py` has `NODE_MAJOR = 26`; `setup.sh` and `emuenv.py` each search `~/.nvm`. | V: the fresh-clone rows above: Node 22 fails `npm run check` and `npm run e2e`; Node 24 and 26 pass. The emulator found Node 26 by itself and passed. | The one step of the test that failed. The messages name vitest and a time-out, not Node. |
| H4 | **`make` skips the start-up checks when the emulator is not set up, and exits 0.** | V: `pipeline.check_in_emulator`: "SKIPPED, the emulator is not set up ... Do not flash this build", no error. | The one failure with no known way back ([feasibility](feasibility.md)) depends on a line of text that a person can miss. |
| H5 | **The set-up is three commands, and `--check` covers half.** `tools/setup.sh --check` reports binutils, Node and the emulator. It does not report the stock firmware, the firmware map, the commit hooks, `web/node_modules` or the Playwright browser. | V: `tools/setup.sh`; `CONTRIBUTING.md` "Set up". | No one command says "this clone is ready". |
| H6 | **Tests skip in silence when a file is absent.** 16 skip without the stock firmware, 6 without the built app page. | V: the fresh-clone runs above. | A green run does not say what it proved. |
| H7 | **Two generators compare with an E-PL6 firmware that is in no documented place.** Its default path is under `experiments/2026-11-08-feature-map/out/`, which git ignores. | V: `gen/interval/mkspec_v2.py` line 13, `gen/level-gauge/mkspec_step_b.py` line 60; the log of `gen/run.sh`. | The comparison runs for the owner only. |
| H8 | **Site assets need files that only the owner has.** `web/scripts/film_photos.py` reads `.local/site-photos/` and `.local/raws/`. `web/scripts/render_previews.py` names a build and an emulator state that no step makes. | V: the scripts' first lines. | A contributor cannot regenerate the committed pictures. Acceptable if the document says so. |
| H9 | **The flash step is an owner command.** `epm2flash` is in 10 notes under `experiments/` and in no tool of the repository. | V: `grep -rl epm2flash`. | None for a contributor: `epm2mod install --card DIR` is the documented way. The notes mislead a reader who copies them. |
| H10 | **The emulator scripts read event names from an experiment.** | V: `emulator/boot/evnames.mjs` reads `experiments/2026-11-08-feature-map/sections/*.tsv`. | As H1. |
| H11 | **The commit hooks and the agent hook use `python3` from the system.** The project rule is `uv run python`. | V: `.githooks/pre-commit`, `.claude/settings.json`. | Works where `python3` is 3.10 or newer. Low. |
| H12 | **`tools/setup.sh` needs Debian tools for a missing bison or flex,** and `m4`, which `CONTRIBUTING.md` does not list. | V: `tools/setup.sh` (`apt-get download`, `dpkg -x`, the `m4` test). | On macOS or Fedora without bison the script stops; the message says what to install. Low. |

### Checks in the wrong layer

| Id | Finding | Evidence | Cost |
|---|---|---|---|
| L1 | **CI checks only the pinned build.** A pull request that adds `data/builds/NEW.json` is not made, not started in the emulator and not checked for load order or free space by CI. | V: `python.yml` reads `data/pinned-build.json` in both jobs. | The reviewer must run a contributor's build by hand. This is the first idea of the load-order note, section 6 (branch `docs/segment-rules`). |
| L2 | **CI does not run the emulator.** `boot-test` and `update-path-test` run only on a developer's computer. | V: no workflow initialises `emulator/om-emu`. V: both tests took 15 s in the fresh clone. | The most important hard check has no hard block. |
| L3 | **The document lint, the machine-path check and the commit-message check run only in the local hook.** The hook is off until `tools/setup.sh` or `git config` switches it on. | V: no workflow calls `doclint.py`. | A pull request from a clone without the hook brings what the hook refuses. |
| L4 | **Format and lint cover part of the Python.** black: the package and two test files. mypy: the package and three test files. Nothing lints `tools/`, `gen/`, `emulator/`, `web/scripts/` (48 Python files, among them every script that `make` and CI start); one test checks their imports. | V: `python.yml`, `cli/pyproject.toml`, `cli/tests/test_script_imports.py`. | A syntax-level fault in a check script shows only when the check runs. |
| L5 | **Soft findings sit inside hard checks.** `tools/checks.py` has the results REVIEW (a person reads the output) and SKIP, both with exit status 0. `freespace.py` answers UNKNOWN without the map. `make` prints FIRST CODE and SKIPPED lines. | V: `tools/checks.py` `judged`, `skip`; `tools/freespace.py`. | A reader cannot tell "passed" from "not looked at". |
| L6 | **No soft check exists for a build that may be harmful.** The allow list of the load-order check accepts 87 transfers, 85 of them safe by timing only. No tool prints the rows a build uses, or the free early-loaded bytes it spends (22 B in the kernel range, 366 B in segment 1). | V: `TODO.md`; load-order note sections 3 and 6. | Issue #6 was a jump of this kind. The next one is found by a user. |
| L7 | **Things only the owner or an agent runs.** The doc-links reminder is a Claude Code hook. `epm2mod release` needs the owner's `gh` login and push right. The feature-list check (`readme.feature_problems`) runs only inside `release`. | V: `.claude/settings.json`, `releasing.py`. | A contributor cannot know that a README change left the site's list behind until the owner releases. |
| L8 | **The web code has no commit hook.** prettier and eslint run in `npm run check` and CI. | V: `.githooks/pre-commit`. | A format slip costs a CI round. Low. |

### CI steps that are not deterministic or that warn

| Id | Finding | Evidence |
|---|---|---|
| N1 | **The unit tests run before the stock firmware is there.** The `check` job skips 17 tests, among them every test of a real build. The next step then downloads the firmware for `make`. | V: run 45534128012, job `check`: "Ran 280 tests ... OK (skipped=17)", then "downloading OLY_E_". |
| N2 | **Each run downloads Olympus's firmware from the maker's server.** Three jobs, no cache. When the server is down or changes its answer, every pull request is red. | V: `python.yml` (`make`, `fetch-stock`), `release_smoke.py`. |
| N3 | **Tool versions float.** `pip install uv` without a version (the launchers pin uv 0.13.6). `uv sync` without `--locked`. `ubuntu-latest`, `macos-latest`. `apt-get install bison flex texinfo`. Python 3.12 in CI, `>=3.10` in the package. | V: the workflows. |
| N4 | **Every `python` run carries a warning annotation:** `actions/cache` targets Node 20. | V: run 45524745609, annotations. |
| N5 | **The dev zip is named by the clock.** On a branch the version is `date -u +%Y.%m.%d`-dev. | V: `release.yml`, step `zip`. |
| N6 | **The pinned build's name is worked out by an inline Python line, twice.** | V: `python.yml` lines 34 and 60. |
| N7 | **A pull request that makes a check stricter turns CI red on the pinned build,** which is camera-tested and cannot change. | V: run 45524745609 failed in "freespace.py check" of the pinned build until a new build was pinned; `TODO.md` said so in advance. |

### Release coupled to a local tree and to tag pushes

| Id | Finding | Evidence |
|---|---|---|
| R1 | **A release starts on the owner's computer.** `epm2mod release` needs a clean tree at `origin/main`, `gh` with a login, and the right to push a tag. Version, notes and tag are made there. | V: `releasing.plan`, `releasing.tag`. |
| R2 | **A tag push publishes.** Any push of a tag `v*` runs the publishing job. A tag pushed again fails after the build: "a release with the same tag name already exists". | V: run 45531933159 (`v2026.11.20-rc.6`, pushed again on 2026-11-25; its release is from 2026-11-23). |
| R3 | **One workflow is both a check and the release.** `release.yml` runs on pull requests and on main (build, smoke, disk image) and on tags (the same, signed, then publish). `workflow_dispatch` is there and takes no input, so it publishes nothing. | V: `release.yml` `on:` and the `if:` of `publish`. |
| R4 | **The release notes travel in the tag message.** The publishing job reads them back with the GitHub API and tests for a first line "EPM2Mod ". | V: `release.yml`, job `publish`. |
| R5 | **The readiness checks run before the tag, on another computer than the build.** CI state is read with `gh run list`; a workflow added later is not checked until someone adds it to `epm2mod.json` `workflows` (`python.yml` is not in that list today). | V: `epm2mod.json`, `releasing._ci_problems`. |
| R6 | **The signing environment `release` accepts tags `v*` only.** | V: `conventions.md`, "Releases". A dispatch from main needs this rule changed. |

### The CLI and the checkout

| What the package needs | From | Could it ship in the package |
|---|---|---|
| Its own code | `cli/src/epm2mod/` | It does. No dependency; numpy only for `films pack`. |
| The manifest | `epm2mod.json` | No: it is what makes a folder a project. Keep. |
| Build descriptions, patch specs, pinned pointer, film data, event dictionary | `data/` | No: this is the product, and a pull request changes it. The release zip already carries the part that camera owners need. |
| The stock firmware | downloaded into `firmware/stock/E-PM2/` (`--cache`, `--stock`) | No: not ours to distribute. |
| The free-space check and the two start-up checks, for a candidate | `tools/freespace.py`, `emulator/boot-test`, `emulator/update-path-test`, started as programs | Not now: they are research code with their own inputs (`build/map`, `build/blocks`, `tools/space-ledger/`, the emulator submodule, Node). The manifest names them, which is the right seam. |
| Documents, guides, the site's feature list, the camera log, workflow names | `README.md`, `docs/`, `web/apps/site/src/features.ts` | No: `generate` and `release` are checkout commands by their purpose. |
| The built installer page | `cli/src/epm2mod/app/`, made by `npm run build:app`, ignored by git | It ships in the release zip. A wheel built from a clean checkout has no page (V), so `serve` from a wheel has nothing to show. |

Findings:

| Id | Finding | Evidence |
|---|---|---|
| P1 | **The CLI is the entry point for half of the work.** Set-up, the check runner, the load-order check, the generators and the firmware map are scripts with their own arguments: `tools/setup.sh`, `tools/checks.py`, `emulator/hookcheck.py`, `gen/run.sh`, `tools/fwmap.py`. | V: `CONTRIBUTING.md` names seven different programs. |
| P2 | **The package's version is `0.1.0`; a release is `2026.11.20`.** | V: `uv build --wheel cli`. |
| P3 | **The package is decoupled in code already.** A wheel run in an empty folder says "no epm2mod.json ... give --project DIR". | V: `uvx --from WHEEL epm2mod builds`. |

### Production code that depends on experiments

The package imports nothing from `experiments/` (V: a test scans for it). The scripts that the package and CI start
do: H1, H2, H7, H10. The generators in `gen/` name experiment notes in comments and spec descriptions only (V), which
is a record and stays.

### Duplicated sources of truth

| Id | Fact | Places |
|---|---|---|
| D1 | The commands CI runs | `python.yml`; `CONTRIBUTING.md` "Check your clone" (lists `generate --check`, which CI runs only through a unit test, and omits black); `conventions.md` "To run the checks by hand" |
| D2 | The Node version | `.nvmrc`, `web/package.json` `engines`, `emulator/emuenv.py`, `web/README.md`, `emulator/README.md` |
| D3 | Where objdump is | `tools/toolchain.py`; again in `emulator/hookcheck.py` and `emulator/scenario.py` (`OM_OBJDUMP`, a second variable beside `EPM2_BINUTILS`) |
| D4 | The stock file's path and sha256 | `cli/src/epm2mod/stock.py`, `tools/freespace.py`, `emulator/emuenv.py`, `firmware/SHA256SUMS` |
| D5 | The files black and mypy cover | `.githooks/pre-commit`, `python.yml`, `cli/pyproject.toml`, `conventions.md` |
| D6 | The uv version | pinned in `release/start.sh` and `start.ps1`; free in CI |
| D7 | The name of the doc-links file | `docs/links.json`; `conventions.md` calls it `doc_links.json` |
| D8 | The submodule's name | `.gitmodules` section `third_party/om-emu`, path `emulator/om-emu` |
| D9 | Release notes | the tag message and `release/NOTES.md`, joined in the workflow |

## C. Target design per layer

### Layer 1, the CLI

One command per task. The scripts stay where they are; the CLI starts them through the manifest, as `make` does.

| Task | Command | What it runs |
|---|---|---|
| Set up a clone, and say what is missing | `tools/setup.sh`, `tools/setup.sh --check` | today's steps, and: `fetch-stock`, the firmware map. `--check` lists every item with "present" or the command that makes it, the `node` on PATH among them. Exit status 1 when one is missing. |
| Make a build | `uv run epm2mod make NAME` | as today. For a candidate, a start-up check that cannot run is an error, exit status 4, with the flag `--allow-unchecked` (H4). |
| Check a build before a flash | `uv run epm2mod check NAME` | `tools/checks.py`, then the soft report of layer 2. A check that is skipped says which command makes its input. |
| Run what CI runs | `tools/ci.sh` | the hard checks below, in CI's order. |

The package stays a checkout tool that also runs from a wheel with `--project`. It is not published to PyPI: its
data lives in the repository, and the release zip is the form for camera owners.

### Layer 2, the commit hooks

Hard, fast, on staged files: what the hooks do today, and prettier on staged files of `web/` when `node_modules` is
there.

Soft, never blocks: **`uv run epm2mod lint NAME`**, also the last part of `epm2mod check` and of `make` for a
candidate. It prints WARN lines and exits 0. The pre-commit hook runs it for each staged build description whose
image is in `build/`, and prints "not linted" otherwise. It warns about:

| Warning | Source |
|---|---|
| Each allow-list row the build uses that is safe by inference or by timing only, with its evidence | a new column `class` (proof, inferred, timing) in `emulator/hookcheck-allow.tsv`; `hookcheck.py` prints the rows |
| Free early-loaded bytes after this build, and what the build spends of them | `tools/freespace.py` ledger: kernel range, segment 1 |
| `first_code` in the description: code in an area where none has run | the description |
| A word in new early-loaded bytes that is a late-loaded address (a pointer or a table read that `hookcheck` does not see) | a scan of the patched bytes, all four address aliases |
| A check that was skipped, and results marked REVIEW | `tools/checks.py` |
| A build that touches early-loaded code: "the camera test needs a cold start, 2 minutes off" | the changed ranges |

These are the ideas of the load-order note, section 6, that need no new emulator work. The cold-RAM run and the
caller table of that section are later work.

### Layer 3, CI

Hard blocks. One script, `tools/ci.sh`, which a contributor runs too. CI prints no WARN line: the soft report is not
run there.

| Check | Today | Target |
|---|---|---|
| black, mypy | package and some tests | the same files, named once in `cli/pyproject.toml` |
| A syntax and undefined-name pass over `tools/`, `gen/`, `emulator/`, `web/scripts/` | none | `pyflakes` (today in the workspace's `research` group; it moves to `dev`) |
| Unit tests | 17 skipped | after `fetch-stock`; a skip for a missing file fails when `CI` is set |
| `doclint.py --all`, the machine-path check on the pull request's diff, Conventional Commits on its title | local hook only | in CI |
| `epm2mod generate --check`, `gen/run.sh --check` | yes | yes |
| Feature lists agree (`readme.feature_problems`) | at release time | in CI |
| Every build description the pull request adds or changes, and the pinned build: `make`, free-space check, load-order check, `boot-test`, `update-path-test` | pinned build only, no emulator | all of them. Needs Node from `.nvmrc` and `emulator/om-emu` (a public repository) |
| Web: `npm run check`, `npm run e2e` | yes | yes |
| The zip: build, start on three systems, disk image signed ad hoc | in `release.yml` | the same jobs in a workflow named `package` |

**How CI gets the stock firmware.** Today each job runs the package's own download: a request to OM Digital
Solutions' update catalog, the file from their server, and a sha256 test. No copy is in the repository or in a
release. That is acceptable: the file is fetched from its maker, as a user's computer does, and the hash makes the
result deterministic. The weak point is availability (N2). The target adds `actions/cache` with the sha256 as its
key, so the server is asked once per cache life. The cache is a private copy on GitHub's runners. Whether that is
acceptable is the owner's decision (D, step 6).

Pins: uv by version, `uv sync --locked`, `ubuntu-24.04`, actions at versions without deprecation notes.

### Layer 4, the release

`release.yml` runs on `workflow_dispatch` only.

| Input | Values | Default |
|---|---|---|
| `kind` | `rc`, `final` | `rc` |
| `build` | a build name, for a test release of a build that is not pinned | empty: the pinned build |
| `notes` | free text, put above the generated notes | empty |
| `dry_run` | true: everything but the tag and the publication | true |

Steps, all on GitHub, from the commit of main that the run was started on:

1. `epm2mod release --dry-run --json`: the readiness checks of today (camera test, camera-log row, generated
   documents), the version from the build's label and the existing tags, the notes from the feat and fix commits.
2. Wait for the `python`, `web` and `package` runs of that commit. Fail when one failed.
3. Build the zip, smoke-test it on three systems, make and sign the disk image (the jobs of `package`, called with
   `workflow_call`).
4. With `dry_run` false: create the tag and the GitHub release in one step. The notes are a file of the run.

The owner types `gh workflow run release.yml -f kind=final -f dry_run=false`, or uses the button. The environment
`release` asks for the owner's approval before the signing step. `epm2mod release` stays as the local preview
(`--dry-run`); `--push` is removed. A pushed tag starts nothing.

Not deterministic: the `notes` input, and Apple's notarization ticket. Everything else follows from the commit
(and, since the release holds the day as its label, from the `day` input: see the status table).

## D. The plan

One pull request per step. Steps 1 to 5 make a fresh clone complete. "Owner" marks a decision to take first.

| # | Step | Changes | Unblocks | Risk | Verified by | Owner |
|---|---|---|---|---|---|---|
| 1 | One set-up command | `tools/setup.sh` also runs `fetch-stock` and `fwmap.py build`; `--check` covers stock, map, hooks, `node_modules`, Playwright and exits 1 when one is missing. `CONTRIBUTING.md` "Set up" becomes one command; `m4`, bison and flex are named. | H5, H12 | Low: additions to a script that is safe to run again | the fresh-clone test with one command | |
| 2 | Node fails early and by name | `web/.npmrc` with `engine-strict=true`, so `npm ci` on an old Node stops and names the version. `setup.sh` says when the `node` on PATH is not the one it found, with the `nvm use` line. `emuenv.py` reads its major from `.nvmrc`. `web/README.md` says: 24.15 or newer for the web apps, 26 for the emulator. | H3, D2 | Low | `npm ci` on Node 22 refuses; `npm run check` passes on 24 and 26; `boot-test` passes with 26 in nvm only | |
| 3 | `make` refuses a candidate without its start-up checks | exit status 4 and `--allow-unchecked` in `pipeline.py`, `cli.py`; tests; `generate` for `cli.md` | H4 | Low. Changes a command's behaviour | a unit test with no emulator; the fresh clone before `setup.sh` | Yes: a behaviour change of `make` |
| 4 | Tests say what they skipped | a skip for a missing file fails when `CI=1`; the run ends with one line that lists the missing inputs and the command for each | H6, N1 | Low | `CI=1` run in a clone without stock fails; with stock and the app page, 0 skipped | |
| 5 | `tools/ci.sh` | one script with the hard checks; `python.yml` calls it after `fetch-stock`; `CONTRIBUTING.md` and `conventions.md` name it and drop their own lists | D1, D5, N6 | Low | the script in a fresh clone; the workflow on the pull request | |
| 6 | CI is pinned and quiet | uv version, `--locked`, runner image, the cache action; a cache for the stock firmware keyed by its sha256 | N2, N3, N4 | Low | two runs: the second does not download; no annotation | Yes: a cached copy of Olympus's firmware on GitHub's runners |
| 7 | CI runs the emulator on the pinned build | checkout of the submodule `emulator/om-emu`, Node from `.nvmrc`, `boot-test` and `update-path-test` in `ci.sh` (the free-space check already runs `hookcheck.py`) | L2 | Low: 15 s of run time. U: the emulator's result on a GitHub runner | the two PASS lines in the pull request's run, equal to the local ones | |
| 8 | CI checks every build a pull request touches | `ci.sh` makes each added or changed `data/builds/*.json` and runs step 7's checks and the free-space check on it. A pinned build that fails a newer check is listed in a file with the reason, in place of a red main | L1, N7 | Medium: old descriptions do not pass today's free-space check, so only changed files are taken | a pull request that adds a candidate with an overlap fails | |
| 9 | The local hooks' rules in CI | `doclint.py --all`, the machine-path pattern on the diff, the title's form, `feature_problems`; `pyflakes` on the script folders | L3, L4, L7 | Medium: `doclint --all` and `pyflakes` may fail on files of today; fix or list them in the same pull request | a pull request with a bad heading fails | |
| 10 | Checks leave `experiments/` | move the scenario scripts that `tools/checks.py` runs, and the event-name tables, to `emulator/scenarios/`; `checks.py` makes its reference builds or says the command; `freespace.py` takes experiment specs from a list in `tools/space-ledger/`, not from a glob | H1, H2, H10 | Medium: file moves under working checks. No change to their logic | `checks.py --tier full` on the pinned build: no SKIP, the same results as before the move | |
| 11 | The soft report | the `class` column; `hookcheck.py` prints the rows a build uses; `freespace.py` prints the free early-loaded bytes; `epm2mod lint NAME` and `epm2mod check NAME`; the pre-commit call. REVIEW and SKIP move from the check runner's results to WARN lines | L5, L6, P1 | Medium: a person must class the 25 lines of the allow list from their evidence text | `lint` on the pinned build prints the timing rows and the free early-loaded bytes of the load-order note, and exits 0 | Yes: the class of each row |
| 12 | Split `package` from `release` | the build, smoke and disk-image jobs move to `package.yml` (pull requests, main, `workflow_call`). The dev version is the commit's date and short hash | R3, N5 | Low | the pull request's own run | |
| 13 | Release by dispatch | `release.yml` as in C; `epm2mod release` gets `--json` and loses `--push`; the tag trigger goes; `conventions.md` "Releases" rewritten | R1, R2, R4, R5 | Medium: the first release after it is the test. Mitigation: `dry_run` is the default | a dry run on main; then one `rc` | Yes: the environment `release` must accept main and ask for approval (R6); and whether a tag pushed by hand should still do anything |
| 14 | Small duplicates | prettier on staged `web/` files in the pre-commit hook; `OM_OBJDUMP` lookups use `tools/toolchain.py`; `conventions.md` names `docs/links.json`; the package's version comes from the pinned build's label at release time; the hooks call `uv run python` | L8, D3, D7, P2, H11 | Low | unit tests; `hookcheck.py` with `EPM2_BINUTILS` set | |
| 15 | Say what only the owner can regenerate | `web/README.md` and `gen/README.md`: the photos, the previews and the E-PL6 comparison need files that are not in the repository, and where they come from | H7, H8 | None | read as a new contributor | |

## E. What to leave alone

| Thing | Why |
|---|---|
| `tools/freespace.py`, `tools/fwmap.py`, `emulator/*.py` as research-style code outside the package | They work, a camera-tested build depends on their verdicts, and a rewrite to package rules (black, mypy, docstrings) is tidiness with a real chance of changing a verdict. Step 9 adds `pyflakes`; no more. |
| The manifest `epm2mod.json` and the start of scripts by path | It is already the seam between the package and the checkout. A plug-in interface would add code and remove nothing. |
| `data/` in the repository, not in the package | The data is the product. A wheel with a copy would be a second source of truth. |
| Publishing to PyPI | No reader needs it: owners use the zip, contributors the clone. |
| The download of the stock firmware from the maker | It is the reason the project distributes no Olympus file. |
| binutils built from the submodule | 73 s once, cached in CI, and no binary of unknown origin. |
| The camera test, the camera log, `epm2mod pin` | These are the owner's by nature: they need the camera. A pull request without a camera test says so (`CONTRIBUTING.md`). |
| Superseded specs, old build descriptions, `experiments/` notes that name `epm2flash` | Dated records (AGENTS.md, rule 20). Step 10 moves live scripts out; the notes stay. |
| The `.claude` doc-links hook | It is advice for one tool. The hard form of the same rule is step 9's `feature_problems` in CI. |
| The release launchers and `make-dmg.sh` | They are tested on three systems in every run and carry pinned downloads. |
| unittest as the test runner | 280 tests in 11 s. A move to pytest buys nothing here. |
