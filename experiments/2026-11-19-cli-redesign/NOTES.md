# CLI redesign: spec for approval (2026-11-19)

Status: **proposal, not built.** Nothing here changes code until the owner approves it.

## Why

A blind review read only `epm2mod --help` and runs of the read-only commands, as a third party would (summary in the
session of 2026-11-19). Main findings: user, developer and release commands sit in one flat list; bare `looks` runs a
developer check; `-o` and `--card` mean different things in different commands; output is not made for scripts;
`make --card` does not say how to flash; nothing says which commands need the repository or the network.

## Owner's decisions

- Balance local development and user clarity: commands stay at the top level (no `dev …` namespace); the help is
  grouped by audience instead.
- Renames for clarity are allowed. **No aliases:** a renamed or moved command is changed everywhere in the same
  commit, and the old name stops working.
- The CLI is the preferred user route (the installer is unsigned).

## The commands

Grouped as `epm2mod --help` will show them.

**For camera owners**

| Command | Does | Was |
|---|---|---|
| `cards` | List the SD cards in this computer | `cards` |
| `install --card DIR [ARTn=FILM ...] [--dry-run]` | Make the firmware, write it and the film file to the card, print the camera steps (flash, then Load Looks). No choices: the 12 default films. A slot left out keeps its Olympus art filter | new (`make --card` + `looks pack`) |
| `films` | List the film simulations: menu name, command-line name, film, type | `looks list` |
| `films set (--card DIR \| -o PATH) [ARTn=FILM ...] [--dry-run]` | Write only the film file | `looks pack` |
| `films show FILE` | List the films in a film file and check it | `looks show` |
| `restore (--card DIR \| -o PATH) [--dry-run]` | Olympus's original firmware, to remove EPM2Mod | `restore` |
| `installer [--port PORT] [--no-browser]` | Open the installer page | `serve` |
| `inspect FILE` | Say what a file is: EPM2Mod or Olympus firmware (build, version, sha256) or a film file | `info` |

**For developers**

| Command | Does | Was |
|---|---|---|
| `make [BUILD] [-o PATH] [--card DIR]` | Make a build (default: the pinned one) into `build/` | `make` |
| `builds` | List the build descriptions and the pinned one | `builds` |
| `pin BUILD --date --sha256` | Record a passed camera test; the build becomes the default | `pin` |
| `apply SPEC ... -o PATH` | Apply patch specs without a build description | `apply` |
| `fetch-stock` | Download Olympus's firmware and check it | `fetch-stock` |
| `looks (--check \| --write)` | Compare or write the film patch specs that the fit files generate. Bare `looks` prints its help | `looks` (the check was the default) |
| `log FILE [--summary]` | Decode `EPM2LOG.BIN` | `log` |
| `docs [--check]` | Regenerate the generated parts of the documents | `readme` |

**For releases**

| Command | Does | Was |
|---|---|---|
| `package [-o DIR] [--version V]` | Write the release zip | `package` |
| `release [--final] [--yes] [--push]` | Check and tag the next release | `release` |

## Rules for every command

1. **Destinations.** `--card DIR` is the top folder of an SD card; the command writes the camera's file names there.
   `-o PATH` is a file, or a folder that gets the usual file name. A command that writes takes one of them or says
   its default in its help.
2. **Output.** Results on stdout, hints and progress on stderr. Exception kept on purpose: `make`'s numbered step
   lines (`4/5 sha256 …`) stay on stdout, because the release smoke test reads them.
3. **`--json`** on `cards`, `films`, `films show`, `inspect`, `builds`: one JSON document on stdout.
4. **Exit codes.** 0 done, 1 failed, 2 wrong usage, 3 nothing found (`cards` with no card).
5. **`--dry-run`** on `install`, `films set`, `restore`: print what would be written and replaced, write nothing.
6. **Every card write** ends by printing the camera steps that come next.
7. **The help of each command** says its default output, and whether it needs the repository (`make`, `pin`,
   `apply`, `looks`, `docs`, `package`, `release`) or the network (`install`, `make`, `restore`, `fetch-stock`,
   when Olympus's firmware is not downloaded yet).

## Shared code

`install` and the installer page both write firmware and a film file to a card. Both call one function in
`pipeline.py`, so they cannot drift apart. The installer page does not call the CLI; it needs no other change.

## Migration (one commit, no aliases)

| Where | Change |
|---|---|
| `src/epm2mod/cli.py` | The commands above, help groups, rules 1-7 |
| `src/epm2mod/pipeline.py`, `serve.py` | The shared install function |
| `release/start.sh`, `start.ps1` | Default command `serve` → `installer`; the comment's example `make` → `install` |
| `.github/scripts/release_smoke.py` | Starts the page with `installer`; still runs `make` and `cards` |
| `.github/workflows/release.yml` | No change (`package`) |
| `src/epm2mod/release.py`, `releasing.py`, `looks/records.py`, `looks/lookpack.py`, `cards.py`, `eventlog.py`, `readme.py`, `tools/oetool.py` | Messages and docstrings that name old commands |
| `tests/` (`test_package`, `test_eventlog`, `test_lookfile`, `test_serve`) | New names; tests for `install`, `films`, `inspect`, `--json`, exit code 3, `--dry-run` |
| `web/apps/local` (`api.ts`, `App.tsx`, tests, `vite.config.ts`, `package.json`) | Mentions of `epm2mod serve` |
| `web/apps/site` Install page | Command-line tab: `install --card`, `films`, `films set` |
| README, `docs/guide/*`, `docs/install.md`, `docs/look-file-format.md`, `docs/logging.md`, `docs/conventions.md`, `docs/feasibility.md`, `AGENTS.md`, `looks/README.md`, `web/README.md`, `release/README.txt` | New names |
| `tools/doc_links.json` | The command-line group |
| `experiments/*/scripts` that run the CLI (`2026-11-18-log-menu/scripts/run_logmenu.sh`, ...) | New names |
| Dated experiment notes and `docs/camera-log.md` | **Not changed:** they record what was run that day |

## Open question for the owner

- Dated experiment notes and the camera log keep the old command names as history (proposal above). Agree?
