# Check audit

Every check of the repository, the fault it is for, what it caught, and what was done with it. Date: 2026-11-25.
"Before" is commit `f41e8fd` of `chore/engineering-cleanup`. The rules that came out of it are in
[conventions.md](conventions.md), section Checks.

A check stays when it finds a real fault, gives the same answer each time, and nothing else finds the fault. CI history:
the newest 200 runs on 2026-11-25 (`gh run list`): 103 of `python`, 69 of `release`, 28 of `web`, 11 of them red. Two of
the 11 were faults of a workflow file (44485426703, 45531933159).

## What a contributor sees

Three sample changes: a sentence in a document, a line in the site, a new spec of 2 bytes in segment 1 with its build
description. Times on one computer with other work running. An actionable line is one that is about the change.

| Sample | Step | Before | After | Actionable lines, before and after |
|---|---|---|---|---|
| document | hook | 0 lines, 0.1 s | 0 lines, 0.1 s | 0, 0 |
| document | `tools/ci.sh python` | 249 lines, 311 s | CI_DOC_AFTER | 0, 0 |
| site | hook | 2 lines, 0.6 s | 2 lines, 0.6 s | 0, 0 |
| site | `tools/ci.sh web` | 225 lines, 42 s | CI_WEB_AFTER | 0, 0 |
| firmware | hook (`epm2mod lint`) | 26 lines, 10 s | LINT_AFTER | 1, 1 (the cold start for the camera test) |
| firmware | `tools/ci.sh python` | 268 lines, 367 s | CI_FW_AFTER | 0, 0 |

## The hard checks

| Check | The fault it is for | What it caught, and its noise | Verdict |
|---|---|---|---|
| `epm2mod init --check` | another tool version gives another verdict | nothing recorded; 0.5 s | keep. `python.yml` ran it twice: once removed |
| the installer page is built first | a stale page in the release tests | nothing recorded; 75 lines of output | keep, quiet |
| black, mypy | format, types | no red run; the hook stops it before | keep, quiet |
| unit tests | see "Unit tests" | 229 s of the 311 s, 93 s of it the tests of the allow list | keep, shorter |
| ResourceWarning and `skipped=` in the test log | an unclosed file; a skipped test | nothing recorded. `support.needs` fails a skip under `CI` already | keep; a proposal below |
| `epm2mod generate --check` | a generated document that is out of date | in unit tests since 2026-11-16; stale text found by hand several times | keep, quiet |
| code-space map comparison | a stale map document | no fault; the map is a reference, regenerated 17 times by hand | **deleted from CI**. `freespace.py map` stays a command |
| `gen/run.sh --check` | a spec that its generator does not make, or that git does not hold | run 44486887847: a generator could not run on a fresh clone. 113 lines of output | keep, quiet |
| writing rules (doclint) in CI and in a unit test | style | a judgement; hits are style only | **hook only** |
| machine paths in CI (`--since`), and its 3 tests | a home path in the history | none in main's files (`git grep`). A pattern has both misses and false alarms | **hook only**, inline as it was |
| `epm2mod make` of the pinned build: recorded sha256 | a spec or code change that changes a tested build | no red run with a wrong hash; exact, 2 s | keep |
| free-space check | two specs on the same bytes; code in space that is not free | six red runs, all on the pinned build: 44955625475 and 44955507828 (`log-menu-3` against the probe `peaking-mf`, repaired by 60d9c65); 44675762648, 44680249802 and 44684802218 after a candidate's specs were committed, green when it was pinned (40a1b02; inferred, the logs are gone); 45524745609, the stricter load-order check on issue #6 | keep; a proposal below |
| SRAM callers (part of the free-space check) | code over a routine that SRAM code calls | `peaking-direct-3`, the sleep routine, found after the flash; the check was written for it | keep. `emulator/opcheck.py` repeated it and the rule of `spec.py` for kept bytes (camera crash on ART 7): **deleted**, as was its row in `tools/checks.py` |
| load-order check, with `hookcheck-allow.tsv` (91 entries, 78 lines) | early code that jumps to code not in RAM yet | found `spot-af-2` (issue #6) after the decode repair of 2026-11-25; earlier it listed the known hook of 2026-11-14 in every run. 85 of the 87 accepted transfers of the pinned build are a judgement and printed as PASS | **replaced** by a computed comparison with the pinned build. The 59 build descriptions that can be made give the same verdict under both rules but `debug-log-movie-ab` (see proposals) |
| `boot-test` | a build that does not start | `peaking-direct-2`: a crash at every start, before any flash. A battery read during start-up (2026-11-17), a loader task that moved the start by 5.5 ms | keep. TIMES MOVED now fails (before: exit 0 without `--strict-times`). Run on all 60 descriptions: 59 PASS, and `peaking-direct-3` is refused earlier; no existing build changes |
| `update-path-test` | an update file that is not found with OK held | no failure recorded; the failure has no known way back | keep |
| `tools/checks.py`, tiers, RESULT parsing | a runner for the checks | repeated `make` for a candidate. The full tier (20 minutes): S1 to S7 gave REVIEW or a reference's FAIL in every note that reports it (model calibration, twelve-region, peaking-mf, slow-boot); none stopped a build. Nine review rounds on it | **deleted** |
| scenarios S1 to S7 | a peaking change that touches stock behaviour | found one thing: the Debug Log's stack residue in ART Key Line. It is no defined stock state. `git show f41e8fd:docs/dev/conventions.md` describes it | **records** in `experiments/2026-11-14-focus-peaking/scripts/`, as they are on main |
| save guard S19 to S26 | the heap divided again under a still block | a user's report of 2026-11-16; the scenarios were written for it | **by hand**, before a peaking change |
| web: prettier, eslint, tsc, vitest, builds, Playwright | format, types, page behaviour | run 45068569375: a Playwright locator that matched two elements; 225 lines of output | keep, quiet |
| pull request title | a bad commit subject after a squash merge | nothing recorded; deterministic | keep |

## Workflows and release

| Check | Evidence | Verdict |
|---|---|---|
| `package.yml`: zip, start on three systems, disk image | run 44980243941: the Windows smoke step; real. 3 runners for each matching pull request | keep. The disk-image step has a 45 minute limit (it hung for 6 hours on 2026-11-25) |
| release plan: camera-log text search | looks for a hash in text; `epm2mod pin` records the camera test with the sha256 | **deleted** |
| release plan: `_ci_problems` (GitHub runs, YAML paths read by hand, 6 tests) | repeats GitHub's own rules; had a defect in each review round | **deleted**: `release.yml` runs `tools/ci.sh` on the commit |
| release plan: clean tree at origin/main, camera test, label, date, stamped image differs only in the date, `boot-test` and `update-path-test` on it | exact; the stamped image is not the tested one | keep |
| release plan: free-space check, generated documents, feature lists | the workflow runs them too; here they serve the local preview | keep |

## Commit hooks and reminders

| Check | Evidence | Verdict |
|---|---|---|
| `commit-msg` | nothing recorded; exact | keep |
| machine paths, doclint, prettier, black, mypy on staged files | lint and format; the hook reads the working tree for documents and web files | keep |
| `epm2mod lint` of a staged build description | 26 lines for one spec of 2 bytes, 18 of them the allow list, 2 a Python deprecation warning | **simplified**: 6 or 7 lines, the transfers as one count |
| `.claude/hooks/doc_links.py` | advice for the agent; 4 tests hold that `docs/links.json` names files that exist | keep |

## Unit tests

| Group | Tests | Kind | Verdict |
|---|---|---|---|
| `test_package`, `test_install`, `test_serve`, `test_cards`, `test_eventlog`, `test_lookfile`, `test_label`, `test_firmware` | 250 | the product: container, specs, card writing, installer, log decoder. `test_every_tested_build_gives_its_sha256` (41 s) makes every tested build | keep |
| `test_release` | 13 | the stamped image and the zip. Holds the flipped byte | keep |
| `test_releasing` | 19, before 25 | the plan. The six that faked GitHub went with `_ci_problems` | simplified |
| `test_hookcheck` | 3, before 7 | the load-order check on real builds, with issue #6. The rest tested the list | simplified, 20 s from 93 s |
| `test_bootcheck` | 5 | the comparison rule | keep |
| `test_tools` | 23, before 39 | half is made-up input for a check, five match the text of a file. The scenario, runner, machine-path and allow-list tests went | simplified; proposals below |
| `test_script_imports` | 2, before 3 | pyflakes and imports on scripts that no type check reads | keep |
| `test_doc_links` | 4 | the agent hook | keep |

## Proposals

Not applied: each changes what a check says or decides.

1. **The load-order check has no way through for a new transfer that is proven safe.** It affects
   `debug-log-movie-ab` (four movie hooks, never on the camera) and any new task entry. A key in the description, as
   `first_code` is, would let the pull request name it; or the comparison takes the address and the target's segment,
   not the target. With the target, a film-structure change that moves its segment-2 code fails for up to 101 known
   words (the older film builds do).
2. **The free-space check of the pinned build against specs that are not in it** made main red five times for a
   conflict between two lines of work, and the pinned build cannot change. Check a build against the specs of its
   own description and the pinned ones; keep the ledger for the map.
3. **`epm2mod lint`: early-loaded space and late-loaded words compare with the pinned build.** Today each candidate
   prints the same 22 words (any byte position, nobody has gone through them) and the same two areas. With the
   comparison a change prints what it adds.
4. **Tests that match text:** `test_ci_does_not_pick_up_descriptions_that_git_does_not_hold`, the `assertIn` on the
   source of `emuenv.py`, `test_the_documents_do_not_promise_the_pinned_label_or_sha256_for_a_release`, and
   `SourceTests`, which fails on a path in a docstring (it stopped this work once). Delete or make them run the code.
5. **The tests of pinned tools** (`ToolchainTests`, `EmulatorPinTests`, `FirmwareMapTests`, `UnpackedImageTests`,
   the Node and Python version tests, about 150 lines) protect against tool drift that has not happened. Keep
   `init --check`; delete those that repeat it.
6. **`ResourceWarning` and `skipped=`** in `tools/ci.sh`: style, and a repeat of `support.needs`. Delete both.
7. **`TestStock.test_round_trip`** (`test_firmware`) repeats `test_the_stock_file_round_trips` through `oetool.py`.
8. **Hooks that refuse:** the model says that hooks are lint, format and soft warnings. Document rules and machine
   paths refuse a commit. Decide if they should warn.
