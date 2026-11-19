# The emulator moves into the om-emu fork (2026-11-16)

The E-PM2 emulator was two patches to om-emu (`emulator/om-emu-patches/`) and our drivers
(`emulator/e101/`, `emulator/boot/`). It is now our fork of om-emu, the submodule
`emulator/om-emu` ([github.com/cfu288/om-emu](https://github.com/cfu288/om-emu), branch `e101`),
in upstream's layout. What the fork has: `emulator/om-emu/docs/e101-boot-spec.md`.

## What changed

| Before | In the fork |
|---|---|
| patch 0002: `S.relax`, a CPU-wide mode that let undefined flags and divides by 0 pass | two stand-ins for the only two sites (V: probe of every run below): S-ROLC at 0x7E5018FC, S-DIV0 at 0x7E6A3203; the CPU is upstream's |
| patch 0002: storage for unknown INTC offsets | removed: 0 accesses in every run (V) |
| patch 0002: `irq_kick`, `ctl: 0x3fc` | `irq_kick` was `irq_ipi + 1`; `ctl: null` |
| patch 0001: `function_only`, E143 facts for E101 | a real port (`bin/port.mjs E101`: 907 addresses, 238 unmapped) and 4 hand facts |
| plain storage for every MMIO address | 30 declared blocks (6 models, 24 plain); any other access faults (reason 2) |
| drivers read `process.env`, `fs`, `Buffer` | `src/boot/` is pure (upstream's purity test: 0 violations); files in `host/boot.mjs` |
| `oetool.py` unpacked folders | the `.BIN` through upstream's container reader |

`emulator/e101/*.mjs` and `emulator/boot/{play,crawl,stage2-boot,update-boot,shot}.mjs` keep their
names as thin layers over the fork, for the scripts in `experiments/`.

## Checks

- `scripts/baseline.sh OUT`: boot reports (stock, films-12), the update path, a menu walk with 8
  screenshots, a card with the clock, a crawl. Run before the move and after it, through the same
  commands: all exits equal, all 12 PNGs byte-identical, the update, play, card and crawl outputs
  equal (V). The boot reports differ only in stand-in names and in instruction counts (+130 on CPU0,
  +5000 on CPU1: the two new site hooks stop the CPU, so lab time moves at other points).
- The FAT16 card image from a folder with sub-folders: byte-identical to the old builder's (V).
- `emulator/boot-test` and `update-path-test` on films-12 and peaking-colours: PASS (V).
- `emulator/emurun.py run` on rec_limit, strlen, memcpy, gamma_select, matrix_choice,
  curve_select: 1462 rows, 0 failing, through the fork's `bin/debug.mjs` with no special case (V).
- In the fork: `bin/test-pure.mjs` all passed; `test/test_boot.mjs` units 11/11 and session 7/7 (V).
- Open, in the fork: with E101's blocks unpacked, 8 checks of `test_facts.mjs` fail (rules and the
  test's own scans disagree, or no pin yet); see the fork's spec, "Function calls".
