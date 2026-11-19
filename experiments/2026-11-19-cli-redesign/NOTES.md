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
| `tools/doc_links.json` | The command-line group; the CLI reference as generated |
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
