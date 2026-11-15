# The emulator comes into the repository (2026-11-15)

Question: can the full-boot emulator work move from a folder outside the repository into the
repository, on an om-emu commit that has the MIT licence, with the same results as before?

Answer: yes. Labels: **V** = ran here; **I** = inferred.

## What was done

- om-emu is the git submodule `third_party/om-emu`, pinned to upstream commit
  `0819080133f6ca7edd455dfdfa209bd9eed291cc` (2026-11-14, the newest commit of `main` on 2026-11-15).
  The licence came with commit 18a8162; the pin is 70 commits after it, and 231 after the old base 96bf756.
- Our changes to om-emu are two patch files in `tools/emu/om-emu-patches/`. `tools/emu/setup.sh`
  exports the submodule to `build/om-emu/` and applies them there. The submodule is not edited.
- Our drivers moved to `tools/emu/e101/` and our tools to `tools/emu/boot/`. Every path in them comes
  from the environment or from the repository (`tools/emu/e101/paths.mjs`, `tools/emu/emuenv.py`,
  `tools/emu/boot/env.sh`).
- New commands: `tools/emu/boot-test`, `tools/emu/update-path-test`, `tools/emu/emu-run`,
  `tools/emu/mkstate`. See `tools/emu/boot/README.md`.
- `tools/emu/omemu.py` (and with it `emurun.py` and `scenario.py`) uses `build/om-emu` when it exists.

## The patches on the newer commit

The old tree was on upstream commit 96bf756. Between it and the pin upstream changed four of the seven
files we patch (`cpu.mjs`, `interp.mjs`, `models.mjs`, `hle.mjs`), 269 lines added and 44 removed in all. None of our hunks
overlaps an upstream change: both old diffs apply to the pin with no fuzz and no offset error (V,
`git apply --check`, and `patch --fuzz=0` in `setup.sh`). The one old diff of 246 lines is now two
files: `0001` is the function-only model (what `tools/emu/omemu.py` needs), `0002` is the rest (the
full boot). `0002` changes one line that `0001` adds (the INTC facts of the E101 entry).

Upstream changes near our code, and why they do not change our results (V by the equal reports below):

- `cpu.mjs`, `interp.mjs`: a fetch guard `FG` and exec probes. Both are off unless a caller sets
  them. Our driver does not.
- `mem.mjs`: regions that are misaligned or overlap are refused. Our regions pass.
- `hle.mjs`, `machine.mjs`, `debug/`: lab and debugger features (patch audit, calls into the middle of
  a function). Our driver does not use the lab. `bin/debug.mjs --serve` still speaks the protocol
  that `omemu.py` uses (V: `emurun.py run memcpy`, `run rec_limit`, and S12 to S14 below).

Upstream did not add the E-PM2 or its generation: `docs/ROADMAP.md` still lists E101 in tier D, "not
tried", "no work planned". Nothing upstream replaces our port.

## Checks

`scripts/verify.sh SCRATCH OLD_WORK` runs them from a clean state (submodule de-initialised and
initialised again, a fresh working tree, fresh unpacked images). Outputs are in `results/`.

| Check | Result | File |
|---|---|---|
| Set-up from a clean state; second run does nothing | V | `setup.txt` |
| `boot-test stock` | PASS, exit 0 | `boot-test-stock.txt`, `boot-report-stock.txt` |
| `boot-test builds/peaking-colours.json` (sha256 4d6b1f26…) | PASS, exit 0. Against stock two lines have allowed differences: the instruction count of CPU1 and one idle count | `boot-test-peaking-colours.txt`, `boot-report-pinned.txt` |
| `boot-test builds/debug-log.json` | PASS, exit 0. Allowed differences: instruction counts, one idle count, one time stamp of an error entry (37.6 → 37.7 ms) | `boot-test-debug-log.txt`, `boot-report-debug.txt` |
| Boot report of the pinned image, old tree against new tree | Equal in every line but the wall time. The instruction counts are equal too (cpu0 30,661,113, cpu1 2,765,217). So the newer upstream commit changes nothing that this boot reaches | `boot-report-old-vs-new.txt` |
| `update-path-test` for stock and the pinned build | PASS, exit 0: file found, 84,766 blocks read, 39 console lines equal, segment 2 not loaded | `update-path-test-*.txt`, `update-report-pinned.txt` |
| Menu sequence MENU → Custom Menu → A → Peaking list on the pinned image, old tree against new tree | 8 of 8 PNG files byte-equal; the state files after the run are byte-equal | `menu-sequence-old-vs-new.txt` |
| The withdrawn build (level build + `peaking-direct-2`, sha256 b5493233…, made by `scripts/build_withdrawn.py`) | `boot-test` FAILS, exit 1: CPU1 faults, the start-up does not end. The same image and the same failure as on 2026-11-14 | `boot-test-peaking-direct-2-withdrawn.txt` |
| Function harness on the new tree: `emurun.py run memcpy`, `run rec_limit` | 0 failing | `emurun-*.txt` |
| Scenario tests of the pinned build, `scen_colours.py` S12, S13, S14 | Output equal to the stored `experiments/2026-11-14-focus-peaking/results/scen-colours-s12.txt`, `-s13.txt`, `-s14.txt` but for the folder name of the PNG files | `scen-colours-new-tree.txt` |
| `.venv/bin/python -m unittest discover -s tests` | 168 tests, OK | |

Also tried once each on the new tree, each with a plausible result (V, no stored reference):
`shotdiff.sh` (stock against pinned: Shooting Menu 2 differs), `crawl-all.sh` with two units and
`crawldiff.py`, `lang-all.sh` for one language, `logplay.mjs` with a card and `epm2mod log` on the
file it wrote.

## Left outside the repository

- Screenshots and crawl outputs (about 1 GB, thousands of PNG files). They are outputs, and camera
  screens belong in `docs/images/ui/` only.
- Settings state files. They hold data that the firmware wrote. `tools/emu/mkstate` makes them again.
- One-off probes of the port (`setup-*.mjs`, `probe.mjs`, `waits.mjs`, `bt.mjs`, `calltrace.mjs` and
  about 30 more short files), `demo.sh` (its sequences are in the guides' screenshots and in
  `mkstate`), and the checks of single builds, which are already in their experiments
  (`experiments/2026-11-14-level-gauge/scripts/step-b-emu/`,
  `experiments/2026-11-14-focus-peaking/scripts/menu-emu/` and `colours-emu/`,
  `experiments/2026-11-15-log/scripts/log-emu/`). Those copies still name the old work folder; with
  the tools of `tools/emu/boot/` they need `tools/emu/emu-run` in place of `$NODE` and `BLOCKS`.
- The lab notebook of the port. Its durable content is `tools/emu/boot/README.md`.

## For epm2mod make

Not wired in (another session was building). The call for a candidate:

```python
for check in ("boot-test", "update-path-test"):
    done = subprocess.run([sys.executable, str(repo / "tools" / "emu" / check), str(image_path)],
                          cwd=repo, capture_output=True, text=True)
    # done.returncode: 0 pass, 1 fail (done.stdout has the reason), 2 usage, 3 emulator not set up
```

`boot-test` takes about 6 s and `update-path-test` about 12 s (8 cores; each runs two emulators at the same time).
