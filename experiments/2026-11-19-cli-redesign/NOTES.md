# CLI redesign: spec for approval (2026-11-19, revision 2)

Status: **proposal, not built.** Nothing here changes code until the owner approves it.

Revision 2 adds the results of a blind review of revision 1 (a reviewer who saw only the proposed commands and rules)
and of a coupling review. Revision 1 is in git history.

## Why

A first blind review read only `epm2mod --help` and runs of the read-only commands. Findings: user, developer and
release commands sit in one flat list; bare `looks` runs a developer check; `-o` and `--card` mean different things in
different commands; output is not made for scripts; `make --card` does not say how to flash; nothing says which
commands need the repository or the network. The coupling review found that the CLI, the installer page and the docs
each hold their own copy of the install logic, the camera steps and the film data paths, and that the release smoke
test parses `make`'s human-readable output.

## Owner's decisions

- Balance local development and user clarity: commands stay at the top level (no `dev …` namespace); the help is
  grouped by audience.
- Renames are allowed. **No aliases:** a renamed or moved command is changed everywhere in the same commit.
- The CLI is the preferred user route (the installer is unsigned).
- A film slot left out keeps its Olympus art filter (no `ARTn=olympus`).
- No support channel is offered.

## 1. Structure: a library under the CLI

Every command's work is a plain function in the package (`install`, `set_films`, `restore`, `inspect_card`,
`inspect_file`, ...). The CLI only parses arguments and formats results; the installer page's server and the tests
call the same functions. Three single sources:

| Source | Holds | Used by |
|---|---|---|
| `epm2mod.camera_steps` | The flash steps and the Load Looks path, as data | CLI output, the installer page (from the server), the docs generator |
| `epm2mod.catalogue` (one data module) | The films, the 12 default choices, the build to install | User commands, the installer page, the docs and site generators. Reads the repository or the files bundled in the release zip, so user commands need no checkout |
| `epm2mod.cardio` | Card checks, writes, read-back | Every command that writes to a card |

### No knowledge of the folder layout in the CLI (owner, 2026-11-19)

The CLI runs with no knowledge of the repository's folder structure, for every command. The CLI module never names
or builds a folder or data path (`builds/`, `patches/`, `looks/`, `logs/`, `build/`, `firmware/`,
`pinned-build.json`, ...). It asks one locator for everything: films and defaults, build descriptions by name, the
pinned build, patch specs, event dictionaries, output and cache folders. The repository layout is one implementation
of the locator, the release zip another; an installed package can be added later without changing the CLI.
Arguments name things, not paths (`make BUILD`, `install --build BUILD` take a build name); help texts do not mention
internal folders, and results print the resolved paths. Commands whose resources the locator lacks (developer
commands outside a checkout) exit 5 with a clear message. Tests: a source scan fails if the CLI module names an
internal folder; every user command's `--dry-run --json` runs against a folder laid out like the release zip.

## 2. The commands

Grouped as `epm2mod --help` shows them. Every `--help` ends with one or two examples.

**For camera owners** (work from the release zip, no checkout)

| Command | Does |
|---|---|
| `cards [--json]` | List the SD cards in this computer. Exit 3 if none |
| `install --card DIR [ARTn=FILM ...] [--build BUILD --untested] [--dry-run] [--eject] [--json]` | Make the firmware and write it and the film file to the card, then print the camera steps. No choices: the 12 default films. With choices: only the named slots get a film; the others keep their Olympus art filter. `--build` takes another build; a build without a passed camera test needs `--untested` |
| `films [--json]` | List the film simulations: menu name, command-line name, film, type |
| `films set (--card DIR \| -o PATH) [ARTn=FILM ...] [--dry-run] [--eject] [--json]` | Write only the film file. Same slot rule as `install` |
| `restore (--card DIR \| -o PATH) [--dry-run] [--eject] [--json]` | Write Olympus's original firmware, to remove EPM2Mod |
| `inspect (FILE \| --card DIR) [--json]` | Say what a firmware file or film file is (model, build, version, sha256, films). With `--card`: what is on the card, and what will not work (a film file with Olympus firmware, a damaged film file, extra files in `DCOLYMP`). Exit 3 if the file is not one it knows |
| `serve [--port PORT] [--no-browser]` | Open the installer page |

**For developers** (need a checkout)

| Command | Does |
|---|---|
| `make [BUILD] [-o PATH] [--dry-run] [--json]` | Make a build (default: the pinned one) into `build/`. No `--card`: cards are written by `install --build` |
| `builds [--json]` | List the build descriptions and the pinned one |
| `pin BUILD --date YYYY-MM-DD --sha256 HEX [--dry-run]` | Record a passed camera test. Refuses a hash that `make BUILD` does not produce |
| `apply SPEC ... -o PATH [--from FILE]` | Apply patch specs without a build description. Input: `--from`, default the downloaded Olympus firmware |
| `fetch-stock [--json]` | Download Olympus's firmware, check it, print where it is kept |
| `looks [--write]` | Compare (default) or write the film patch specs that the fit files generate. Exit 1 if they differ |
| `log FILE [--summary]` | Decode `EPM2LOG.BIN` |
| `docs [--write]` | Compare (default) or write the generated parts of the documents. Exit 1 if they differ |

**For releases** (need a checkout)

| Command | Does |
|---|---|
| `package [-o DIR] [--version V] [--dry-run] [--json]` | Write the release zip |
| `release [--final] [--yes] [--push]` | Check and tag the next release; without `--yes` only check |

## 3. Rules for every command

1. **Destinations.** `--card DIR` is the top folder of an SD card; the camera's file names are used. `-o PATH`: an
   existing folder or a path ending in `/` gets the usual file name; anything else is the file. Each writing command
   takes one, or its help states its default.
2. **Output.** Results on stdout; progress, hints and the camera steps on stderr. No exceptions.
3. **`--json`** on every command that lists, describes or writes: one document on stdout, with a `schema` version,
   the files written or replaced, their sha256, and the camera steps as data.
4. **Exit codes.** 0 done; 1 failed; 2 wrong usage; 3 nothing found or not recognised; 4 a check failed (checksum,
   read-back, model, untested build); 5 environment (no network, no checkout, card not writable or full).
5. **`--dry-run`** on every writing command: print (or `--json`) what would be written and replaced; write nothing.
6. **No prompts.** Every command runs unattended. Safety comes from explicit `--card`, `--dry-run`, and refusals
   that need a named flag (`--untested`).
7. **Help.** Each command says its default output, whether it needs a checkout, and whether it uses the network
   (`install`, `restore`, `make`, `fetch-stock`, when Olympus's firmware is not downloaded yet).
8. **Arguments.** `ARTn` is ART1 to ART12, as in the camera's ART menu (ART1 Pop Art ... ART12 Watercolor); a slot
   named twice is an error; an unknown film name lists the valid ones.

## 4. Card safety (`epm2mod.cardio`)

- Refuse a folder that does not look like a camera card (no `DCIM`, not removable), and a card without enough
  space.
- Write to a temporary name, flush to the card, rename; then read back and compare the sha256.
- Remove macOS `._` files and other extra files from `DCOLYMP` (the folder must hold only the firmware file).
  Probe: whether the camera ignores `._` files is unknown; one camera test settles it.
- Refuse firmware whose model is not the E-PM2 (the updater would accept an E-PL5 file).
- `--eject` ejects the card after a write; the camera steps begin with "eject the card".
- No backup files on the card: they would break the single-file rule of `DCOLYMP`. Undo is `films set` or
  `restore` again.

## 5. Stability

- User commands and their JSON are a public interface: the schema is versioned; changes are listed under "CLI
  changes" in the release notes. Renames are breaking changes (no aliases).
- Developer and release commands carry no promise.
- A CLI reference page (every command, flag, default, JSON shape, exit code) is generated from the command
  definitions by `docs --write`; the hand-written docs link to it instead of repeating flags.

## 6. Migration (one change, no aliases)

| Where | Change |
|---|---|
| `src/epm2mod/cli.py` | The commands and rules above |
| `src/epm2mod/` new modules | `camera_steps`, `catalogue`, `cardio`; the user functions in `pipeline.py` |
| `src/epm2mod/serve.py` | Uses the shared functions and `camera_steps` |
| `release/start.sh`, `start.ps1` | Example `make` → `install` (the default stays `serve`) |
| `.github/scripts/release_smoke.py` | Reads `make --json`; also runs `install --dry-run --json` and `inspect` from the unpacked zip |
| `src/epm2mod/release.py`, `releasing.py`, `looks/records.py`, `looks/lookpack.py`, `cards.py`, `eventlog.py`, `readme.py`, `tools/oetool.py` | Messages and docstrings that name old commands |
| `tests/` | New names; tests for every command, `--json` schemas, exit codes 3-5, `--dry-run`, the card checks |
| `web/apps/local` | Camera steps from the server |
| `web/apps/site` Install page | Command-line tab: `install`, `films`, `films set`, `restore`, `inspect --card` |
| README, `docs/guide/*`, `docs/install.md`, `docs/look-file-format.md`, `docs/logging.md`, `docs/conventions.md`, `docs/feasibility.md`, `AGENTS.md`, `looks/README.md`, `web/README.md`, `release/README.txt` | New names; link the generated CLI reference |
| `docs/links.json` | The command-line group; the CLI reference as generated |
| `experiments/*/scripts` that run the CLI | New names |
| Dated experiment notes, `docs/camera-log.md` | Not changed: they are dated records of what was run (owner) |

## 7. Order of work

1. Library and single sources (`camera_steps`, `catalogue`, `cardio`, user functions), with tests. No CLI change.
2. The installer server switches to them (no visible change; its tests pass).
3. The CLI: new commands, renames, rules; tests; the generated reference.
4. Callers: launchers, smoke test, docs, site, experiments scripts; the doc-link map.
5. Camera probe: `._` files in `DCOLYMP` (one flash with a Mac-written card).

## Decisions on the open questions

1. Settled: dated experiment notes and the camera log keep the old command names (owner).
2. Kept after owner review: `serve` (camera owners never type it; the launchers start it) and `restore` (it puts
   Olympus's firmware back; it does not remove the film file or any films kept in the camera).

## Revision 3: design review (2026-11-19)

Three blind reviewers (conventions, design from scratch, scripts and card safety) read only `--help`, `docs/cli.md`
and sample runs, and challenged every choice. Each finding was checked against the real CLI. Owner decisions:
`--film`, and no film set in the CLI. The other choices follow common CLI practice; the owner can overrule any of
them.

### Films (owner)

- `--film ARTn=FILM`, repeatable, replaces the positional `ARTn=FILM` (install, films set). A slot named twice is a
  usage error.
- **The CLI has no film set.** The base is the firmware's own: Olympus's 12 art filters. No `--film`: `install` and
  `make` write the firmware only (no `EPM2LOOK.BIN`); `films set` with no `--film` is a usage error. Each `--film`
  puts one film simulation in one slot; a slot that is not named keeps its Olympus art filter (by design; one camera
  test with a two-film file is still to be done).
- The 12-film preset is the installer page's own data (`web/apps/local`), sent as 12 choices. The catalogue keeps
  the films and each slot's Olympus filter name; `builtIn`, `default_art`, `default_choices` and "In the default look
  file" go. `looks/card-looks.json` stays a developer look list (input of `films pack`).

### Commands and arguments

| Before | After | Why |
|---|---|---|
| `looks` (compare) / `looks --write`, `docs` / `docs --write` | `generate` (writes) / `generate --check` (compare, exit 1, lists the files) | Generators write by default and take `--check` (cargo fmt, black, terraform fmt); one CI check, so specs and docs cannot drift apart |
| `looks pack LIST` | `films pack LIST` | One noun for the film file |
| `--untested` | `--allow-untested` | Override flags say what they allow (cargo --allow-dirty) |
| `release` checks; `--yes` acts | `release` acts; `--dry-run` checks | A missing flag must not turn into a silent success; same idiom as every writer |
| `package -o DIR`, `--version V` | `package --out-dir DIR`, `--release-version V` | `-o` is a file everywhere; `--version` is the tool's version |
| `-o PATH`: folder if it exists or ends in `/` | `-o FILE` is always a file; refused when it is on a listed SD card (use `--card`) | `restore -o /Volumes/CARD/` put the file where the camera does not look; `-o ./newdir` made a file |
| `--eject` fails | a warning: exit 0, `"ejected": false` with the reason; the eject step stays | The write succeeded |
| `log` prints JSON lines; `--summary` | summary by default; `--json` one document with the events | Same as every other command |
| `epm2mod --help` in the release folder lists developer commands | the developer and release groups are hidden when there is no checkout (typed, they still exit with the message) | Owners see only what runs |
| Help and examples say `epm2mod` | the launchers pass their own name (`./start.sh`, `.\start.ps1`) for usage lines, examples and hints | Copying an example must work |
| `films` usage shows ACTION as required; no slot map | ACTION optional; `films` also prints the 12 slots with their Olympus filter names | Users choose by slot |

### Defaults the CLI must not assume (owner: "whatever recommends a set of films should store it")

A default is allowed only when it is data that its owner stores (the pinned build, which `pin` records in the
repository or the release folder) or a plain convention (`--port` 0 = a free port; `serve` opens the browser). A
default that decides for the user is removed.

| Default | After |
|---|---|
| The 12-film set (`install`, `make`, `films set`, the installer server) | Gone from the CLI and the library (see Films). The installer page stores its own preset |
| `make` with no BUILD makes the pinned build | `make BUILD`: the build is required |
| `apply --from` defaults to Olympus's firmware 1.6 | `--from FILE` is required |
| `package --version` defaults to today | `--release-version` is required |
| The stock firmware: `stock=EPM2_V16` is a default argument in the library and the CLI | Each build description names its stock firmware; `restore` writes the stock firmware of the pinned build; no library function has a default stock firmware |
| The check step says "Firmware reads Body : 1.6 EPM2Mod and the release date" for every build | The text comes from the build: its label (`Body : 1.6  EPM2Mod 2026.11.19`), or `Body : 1.6` for a build without one |
| `camera_steps` functions default `art_shows` to "film names, such as Portra 400" | No default; the caller names what was written (the first film and its slot, or the art filters) |
| `inspect` with neither FILE nor `--card` | Usage error: one of them is required |
| The installer page selects the first card when several are listed | It selects a card only when exactly one is listed |
| (proposed in review) `pin --date` defaults to today | Not adopted: the date of the camera test is a fact the caller states |
| (proposed in review) eject by default | Not adopted: the CLI does not assume what the user does next; `--eject` stays opt-in |

Kept: `install --build` defaults to the pinned build (data that `pin` stores); `release` makes a test release unless
`--final` (the safe side); `package --out-dir` defaults to the locator's output folder; `log --dict` tries the
dictionaries of the known builds.

### Output and exit codes

| Code | Meaning | What a caller does |
|---|---|---|
| 0 | done (also: an empty `cards` list) | |
| 1 | a check found a difference or a problem (`generate --check`, `inspect` "will not work", `release --dry-run` not ready) | show it; like diff and grep |
| 2 | wrong usage | fix the command |
| 3 | not found: no such path, file not recognised, unknown build | fix the name or path |
| 4 | refused; a named flag overrides it (`--allow-untested`) | ask the user, then pass the flag |
| 5 | not safe: a checksum, read-back or download sha256 differs, firmware for another model | stop; never retry with a flag |
| 6 | environment: no network, no checkout, the card is not a camera card, not writable or full | fix the setup, then retry |
| 7 | failed: an input is wrong (a build description, a patch spec, a fit, a file that does not fit) | fix the input (added in review: without it, these failures shared 1 with "a check found a difference") |
| 70 | internal error (an uncaught exception) | report |
| 130 | interrupted (any signal); no file half-written | |

- `--json`: success and failure print one document on stdout. Every document has `schema` 2, `command`, `version`
  (the tool's) and `ok`; a failure has `error` {`code` (a stable name), `exit`, `message`, `override` (the flag, or
  null)}. Usage errors too, when `--json` is in the arguments. Policy: added keys do not change `schema`; a removed or
  renamed key or a changed type does; consumers ignore keys they do not know. `docs/cli.md` lists every key,
  nested keys included, and a test compares it with real output.
- Writes: a file whose sha256 on the card is already right is not written again (`"unchanged": true`). Removed
  `DCOLYMP` files are printed ("would remove" / "removed"), not only in JSON.

### Kept after challenge

`install` and `films set` stay separate (no flash for films); `restore`; `--card` required, no auto-pick (Etcher,
rpi-imager); results on stdout, the rest on stderr; no prompts; `--dry-run` on every writer; `apply`; the build is
positional on `make` and `pin` (the thing they act on), a flag on `install`; `serve` (owner).

### Known limits (not changed)

- The read-back may come from the computer's cache, so a fake-capacity card can pass it.
- A partial film file (fewer than 12 slots) is not camera-tested yet.

## Revision 4: no folder in the code (owner, 2026-11-19)

Owner: "the cli should not be hard coded to any folder, and if params are needed things should be passed in as
args". The pattern is a project manifest found by walking up from the current folder (package.json, Cargo.toml,
pyproject.toml), with output and cache locations as arguments.

- **Manifest.** `epm2mod.json` at the top of a project names every file and folder the tools read or write: build
  descriptions, patch specs, the pinned build, film data (catalogue, film records, look lists, older film lists),
  event dictionaries, documents with generated blocks, emulator and space tools, the output folder, the cache folder
  for Olympus's firmware, and the installer page. A checkout and the release zip each have one; the zip's replaces
  `release.json` and says it is a release. No folder or file name of the project is in `src/epm2mod` (a test scans
  the whole package, not only `cli.py`); the camera's own names (`DCOLYMP`, `E1019999.BIN`, `EPM2LOOK.BIN`) stay.
- **Finding it.** `--project DIR` (global option) names the project folder. Without it: the nearest folder at or
  above the current folder that holds `epm2mod.json`. Not found: exit 6 with the message. `EPM2MOD_ROOT` and the
  fallback to the package's own folder go (no alias).
- **Arguments for locations.** `make --out-dir DIR` (default: the manifest's output folder). `--cache DIR` on the
  commands that use Olympus's firmware (`install`, `restore`, `fetch-stock`, `make`, `apply`): where it is downloaded
  and kept (default: the manifest's cache folder). `--stock FILE` on the same commands: use this copy of Olympus's
  firmware (checked by its sha256) and download nothing.
- **Defaults.** A default location is always the manifest's value: data the project stores, not code.
