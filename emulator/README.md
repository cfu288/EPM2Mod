# Emulator harness

Two things are here. The **function harness** (this file) runs single functions and call chains of block 0.
The **full boot** ([boot/README.md](boot/README.md)) boots the whole firmware from reset, draws its menus, and has the
two checks `boot-test` and `update-path-test`. Both run our om-emu fork, the submodule `emulator/om-emu`
([github.com/cfu288/om-emu](https://github.com/cfu288/om-emu), branch `e101`).

The function harness runs single E-PM2 v1.6 block-0 functions in om-emu's MN10300 machine. It runs each input row on stock block 0 and on a patched block 0, then compares the outputs. It follows the caduceus-ep7 contract: run the real code, patched against stock, and check that only the intended outputs change.

Labels: **V** = ran in the emulator and checked against an independent Python model or the notes; **I** = inferred.

## Setup

```sh
uv run epm2mod init          # initialises emulator/om-emu at the pinned commit
```

- **om-emu** is the git submodule `emulator/om-emu`, our fork. The tools run its files as they are: nothing is copied or patched. E-PM2 support belongs in the fork, in upstream's layout; the fork's `docs/e101-boot-spec.md` says what it has.
- **`OM_EMU_DIR`** overrides the checkout. The defaults are in `emuenv.py`.
- **Node, exactly the version in `.nvmrc`:** `node` on PATH when it is that version, else the one nvm has (`tools/node.sh`). The tools find it themselves. `uv run epm2mod init` gets one. Override it with `OM_EMU_NODE`.
- **Stock block 0:** `build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin`. This is the descrambled OE payload, sha256 `1b7c4bb1…71468d`; the harness checks it.

The fork has a port of om-emu's lab to the E-PM2 (`MODELS.E101`, `src/fw/ports.mjs`), so its debug API (`emu/bin/debug.mjs`) runs E-PM2 functions with `OM_EMU_MODEL=E101`. No lab session runs on the E-PM2. A read of a device page om-emu does not model faults with reason 2 (**V**); `scenario.py` handles it.

## Files

| File | What it does |
|---|---|
| `omemu.py` | Driver. Starts `emu/bin/debug.mjs --serve` with `OM_EMU_MODEL=E101` and speaks its JSON-lines protocol. `Emu.call()` calls a function through a real `call` instruction in scratch RAM, using the callee's register list and frame size from its call sites in the image. Stubs are breakpoints: Python sets the return registers, then the CPU returns through a `retf` that has the frame of the call that reached the stub. Each call records an exec trace, and the caller rejects code that ran outside the case's ranges. The call also checks that sp is balanced on return. |
| `patchblock.py` | Builds a patched block 0 from `data/specs/*.json`-style specs, with the same base-hash and expected-byte checks as `epm2mod make` (it calls the package's `apply_specs`). It prints the changed runtime ranges. Ops on other blocks are checked and reported as not emulated. |
| `cases.py` | Named cases: entry, allowed code ranges, stubs, input rows, outputs, and a Python model of the expected outputs. |
| `emurun.py` | CLI: `list`, `run CASE` (one image, checked against the model) and `diff CASE --patch SPEC…` or `--image BLOCK0` (stock against patched). Exits 1 on any mismatch, fault, stray code or unexpected change. |
| `bootmem.py`, `scenario.py`, `osmodel.py`, `liveview.py`, `hookcheck.py` | Scenario runs; see "Scenario runs" below. |
| `specs/rec-limit-3600.json` | Emulator test input only, not a camera patch: changes the recording-limit imm16 1740 to 3600 (2 bytes). |
| `filmcheck.py` | The film check: `uv run python emulator/filmcheck.py data/builds/NAME.json`, after `gen/stock-films/structure.py` has written the layout of that build. As flashed, every Olympus art code selects in each colour stage (tone, look, matrix, six-axis, saturation, chroma, 12-region) what it selects on stock. With every entry loaded, each film code selects its RAM block, the identity look and a 12-region table with no record on. It also builds the blocks that the firmware packs for a job (gamma buffer, block A and the third block of a still, block B of live view) for six synthetic jobs: as flashed they are byte-equal to stock for every Olympus code, and a loaded film's blocks differ from Natural's only in the bytes of those seven stages, so a stage that nobody listed shows too. The script's docstring says what is not covered. Exit status 1 on any mismatch; about 35 s. Run it before you offer a build that changes the film structure or the loader. |
| `emuenv.py` | Where om-emu, Node and the unpacked images are; used by every Python tool here. |
| `boot-test`, `update-path-test`, `bootcheck.py`, `emu-run`, `mkstate`, `e101/`, `boot/` | The full boot: see [boot/README.md](boot/README.md). |

## Usage

```sh
python3 emulator/emurun.py list
python3 emulator/emurun.py run rec_limit
python3 emulator/emurun.py diff rec_limit \
    --patch emulator/specs/rec-limit-3600.json
python3 emulator/emurun.py diff curve_select \
    --patch data/specs/film-portra.json --json /tmp/out.json
python3 emulator/patchblock.py data/specs/film-portra-xp.json \
    -o /tmp/xp.block0.bin
```

Calling om-emu's debugger directly, for example memcpy through a hand-written `call 0x7E5081FA,[d2,a2],8` at 0x7D000000:

```sh
cd emulator/om-emu && OM_EMU_MODEL=E101 node emu/bin/debug.mjs \
  --image ../../build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin \
  --entry 0x7D000000 --write 0x7D000000=ddfa815001a008 \
  --write 0x7D200000=000102030405060708090a0b0c0d0e0f \
  --reg a0=0x7D300000 --reg a1=0x7D200000 --reg d0=16 --reg sp=0x7D100000 \
  --stop 0x7D000007 --read 0x7D300000:20
```

The harness uses scratch RAM at 0x7D000000–0x7D2FFFFF: the trampoline, the return pads, the stack (sp 0x7D100000) and the data buffers. All other RAM starts at zero. `.data` is not preloaded.

## Cases and results

| Case | Entry | Rows | Stubs | Result |
|---|---|---|---|---|
| `memcpy` | 0x7E5081FA | 7 (byte, halfword and word paths, n = 0) | none | matches the model; guard bytes kept; d2 and a2 kept (**V**) |
| `strlen` | 0x7E508346 | 5 | none | matches the model (**V**) |
| `rec_limit` | 0x7E6EDE08 | 48 (MOV q6/q3/q4/q7, AVCHD q5/q3/q4, format 1; rate hi/lo; free space 500 sectors, 1 GiB, 64 GiB) | 4, listed below | matches the model on stock and patched (**V**) |
| `curve_select` | 0x7E56E837 | 229 (7 modes × contrast −3…+3, High/Low Key, the identity flag, art codes 8–184) | none (its only callee, 0x7E56E80F, runs natively) | the 52 modelled rows match; art codes 85/87 → 0x7E75F2F0 and 167 → 0x7E7616F0, as film-portra NOTES §11.1 says (**V**) |
| `rate_table` | 0x7E6EE4D5 (pc range, not a call) | 18 (MOV q6/q3/q4/q5/q7, AVCHD q5/q3/q4, format 1; Fine/Normal) | none | peak/average written to 0xA0753564/68 match the table immediates (**V**) |
| `enc_param_check` | 0x7EEA338C | 23 (peaks 4 M…62.5 M, peak < average, flag, mode, fps, size) | none | accept/reject matches a model that reads the cap from the image (**V**) |
| `enc_rate_fields` | 0x7EEA57D4 / 0x7EEA5C4C | 22 (rates 4 M…50 M × both builders) | as `qp_setup` | kb/s, HRD kb/s − 1 and the 6/2 class (≥ 15.5 M) match the model (**V**) |

`rec_limit` (2026-11-12): the model reads every rate, reserve, overhead and limit from the image, and each row also reports `fill_4g`: the file size at the stop point if video ran at the bitrate-table peak, as a share of 4 GiB, and whether the time-limit rate is ceil(peak/4096) (`rate_in_step`). See experiments/2026-11-12-hardware/06-bitrate-and-limit.md.

**`rec_limit` stubs** (every call is logged, with its arguments):

| Address | What it is | What the stub does |
|---|---|---|
| 0x7E6ED536 | movie-context getter | returns a0 = a zeroed 256-byte buffer |
| 0x7E457C75 | settings getter | returns the row's value for id 33105 index 7 (rate hi/lo) and id 26225 index 0 (format); any other id is an error |
| 0x7E6D13E0 | debug print | returns without printing; its format string and value are logged |
| 0x7E6D1429 | error print | returns without printing; its format string and value are logged |

The two print helpers would also return at once natively, because their mask word 0xA07511E0 is 0.

**Diffs:**
- **`rec_limit` with `rec-limit-3600.json`:** 6 of 48 rows change. They are exactly the rows that stock clamps at 1740 s, all on 64 GiB of free space. Each new limit is the 4 GiB file cap, because each cap is below 3600: MOV q6 lo 1853 s, MOV q3 hi 2363 s, MOV q3 lo 2977 s, AVCHD q5 lo and q3 hi 1762 s, AVCHD q3 lo 2049 s. MOV q4 (limit 7200) does not change, and neither do the free-space-limited rows. This confirms the gains given in experiments/2026-11-08-disassembly/NOTES.md (**V**).
- **`curve_select` with `data/specs/film-portra.json`:** 12 of 229 rows change. 7 are Portrait (mode 4) at contrast −3…+3. The other 5 are **art codes 9, 13, 55, 129 and 133**, which also select Portrait's Contrast 0 table 0x7E75DAF0 through the jump table 0x7E78C8E4 (**V**). So that patch changes more than Portrait. What those art codes are (scene modes?) is **I**, not traced.
- **`curve_select` with `data/specs/film-portra-xp.json`:** 2 rows change, art codes 85 and 87 (Cross Process I, table 0x7E75F2F0). The patch's 24 base-gamma tables are not read by this selector, so this case does not test them.
- **`curve_select` read check:** in all three diffs, every row that changed read patched bytes, and every row that read patched bytes changed.

**Side findings (V in the emulator):**
- With an unknown MOV quality, `rec_limit` takes the reserve from the caller's a2, because the code never sets it on that path. It also prints `[QT] Parameter Error quality` twice.
- The `rec_limit` limit for MOV q4 on 64 GiB is 6202 s: the 4 GiB cap binds below 7200.

## Scenario runs

A scenario runs a top-level routine, or whole firmware tasks, and lets them call down through the real code.
Only what the emulator cannot give is replaced. RAM is kept from one call to the next. The single-function
cases above did not change.

| File | What it does |
|---|---|
| `bootmem.py` | Gives RAM the content that the boot code gives it: the `.data` image (0x7E8DA000–0x7E8F3114 → 0x602A9B40) and the two reset word tables, and zero in the runtime ranges of block 0 that no boot copy loads. The ranges come from `tools/freespace.py`'s load model, not from typed numbers. om-emu maps 0x60… and 0xA0… to the same RAM, so one write serves both aliases. |
| `scenario.py` | `Scenario`: calls (`call`, `call_site`, `piece`), tasks with their own stack (`task`, `run`), stubs, probes, the settings getter, device accesses, write watches, pc sets, call trees, backtraces. Helpers `diff_pcs`, `diff_writes`, `patch_ranges`, `print_calls`. |
| `osmodel.py` | A Python model of the uITRON services behind the `Oly*` wrappers: event flags, queues, data queues, semaphores, sleep, software timers. `schedule()` runs the ready tasks until all wait. |
| `liveview.py` | `LiveView`: a rig for the mov layer and the art tasks. It runs the static constructors, 12 module init functions and 10 task bodies from their real entries, sends "Through Start", and then steps frame events. It tracks the image-work heap (alloc, free, mode, re-partition), firmware error reports and addresses given to devices. |
| `hookcheck.py` | S0, a static check with no emulator. It makes the build's block 0 and decodes the built bytes of every op in the kernel or segment 1, and lists every jump that leaves them and every changed table pointer, with the load segment of its source and target. A transfer from the kernel or segment 1 to segment 2 or 3 FAILS (that code is not in RAM yet when the boot task runs, and never on the update path). Give it a build description, or all specs of a build in order. |
| `opcheck.py` | Two static checks of a whole build: a byte that one spec covers and keeps and a later spec changes, and a call from the code that runs in SRAM into an op. |
| `hookcheck-allow.tsv` | The jumps and pointers that `hookcheck.py` would fail and that are accepted, each with its evidence. |

### How to write a scenario

```python
import sys; sys.path.insert(0, "emulator")
from liveview import LiveView
from scenario import RAM_AND_IMAGE, diff_pcs, diff_writes, patch_ranges

lv = LiveView("/tmp/scratch/pinned.block0.bin", log_writes=RAM_AND_IMAGE)
lv.settings[38017] = 119          # Picture Mode: Key Line (the settings getter 0x7E457C75 answers from this)
lv.settings[17601] = 1            # art filter type I
lv.start()                        # constructors, inits, tasks to their first wait, Through Start
f = lv.frame()                    # one frame event; every task runs until it waits
print(f.summary()); print(f.path()); print(f.events); print(f.faults)
```

Run the same steps on a second image and compare: `diff_writes(a.writes, b.writes)` gives the bytes whose final
value differs, and `diff_pcs(a.pcs, b.pcs, new_code, hook_sites)` gives the stock code that ran only in one image
and the new code that ran (`patch_ranges(base_bytes, patched_bytes)` gives the two range lists).
`emulator/scenarios/scen_peaking.py` is a full example (S1 to S5).

For code outside live view use `Scenario` directly:

- `sc.call(entry, regs, frame=(regs_byte, imm))` calls a function; `sc.call_site(site)` takes the frame from a stock call instruction; `sc.piece(start, [stop])` runs a code piece.
- `sc.stub(addr, fn, name)` replaces a function. `sc.stub_module(lo, hi, name)` stubs every entry of a module that outside code calls. `sc.probe(addr, fn)` reads registers at any instruction and lets the code run on.
- `sc.settings[(id, index)] = value`. Ids that the scenario did not set read 0 and are listed in `sc.settings_missing`.
- `log_writes=[(lo, hi)]` logs every CPU write in the ranges (om-emu watchpoints). `stop_writes` stops at the first write and reports the pc and a backtrace.
- `calltrace=True` keeps the ordered list of functions entered; `print_calls` shows it.
- A task is `t = sc.task(name, entry, stack_size=...)`. A stub that returns `BLOCK` parks the task; `osmodel` does this for every wait that cannot be met.
- A fault, the instruction limit or a stuck wait ends the run. `Result.fault` has the reason and `Result.backtrace` the return addresses found on the stack.
- `EMU_TMP` names the folder for the trace files (one JSON line per instruction; a 3 M instruction limit keeps them below about 400 MB).

### What a scenario does not prove

- **Devices are not modelled.** A write to a device register is dropped and logged. A read gives 0 unless the scenario sets `sc.mmio_values`. "The image processor finished the job" is a flag that the model sets at once. No pixel is computed; buffers hold zeros.
- **The kernel is a model.** Tasks run one at a time until they wait. There is no pre-emption, no time-out that expires, no interrupt. A race between two tasks cannot show.
- **Settings are what the scenario says.** The store that the camera fills from its EEPROM is not there. A wrong value gives a wrong path. In the live-view rig all ids but the ones set read 0, and the mov layer prints `[mov]img_ctrl_size err` in every frame because no geometry was given.
- **Stubbed whole:** the white-balance module, the CPU cache control, the soft-float multiply 0x7E5018E8 (done in Python).
- **Division by zero:** om-emu traps; the MN103 sets the V flag and goes on. The harness goes on and counts them (`Result.notes`).
- **`hookcheck.py` sees only `jmp`/`call`/branch instructions with a constant target in the built bytes of the ops, and stock pointers that an op changes.** A pointer in new code or in a new table, and a register jump, are not seen. A data op in early-loaded space is decoded as code too.
- **Not started:** capture (TAKE_*, REC_* tasks), the GUI, the C++ state framework. `IMG0_LOCAL` spins on a hardware semaphore and is left out.

### Requests for om-emu

1. An option to map a device page as "write ignored, read 0" (now each access faults and the harness skips the instruction through the `disasm` op).
2. An option for the MN103 divide-by-zero behaviour (V flag, no trap).
3. A float unit that does not fault on zero, tiny or non-normal inputs for the E-PM2 soft-float helpers.
4. A "set of executed pcs" trace, so that a long run does not need one line per instruction.
5. `tools/mn10300-objdump` is not in om-emu's repository; the harness sets `OM_OBJDUMP` to the mn10300 binutils objdump.

## Limits of the single-function cases

- **Function level only.** Nothing boots here (the full boot is in `boot/`); there is no kernel, no tasks, no interrupts, no timers in use and no second core. The IMG engine, DMA, the display, the sensor and all other devices are not modelled. The cases are leaf functions or functions with stubbed callees, and a stub's answer is our assumption.
- **RAM.** RAM starts at zero, and `.data` (0x7E8DA000 → 0x602A9B40) is not copied. A function that reads globals needs them written by its case.
- **Memory map.** The whole block is mapped at 0x7E421020. On the camera the boot copies only up to 0x7E881000, and later parts load as overlays. A case that reads beyond 0x7E881000 sees bytes that may not be there at run time.
- **UDF.** om-emu's UDF semantics (`udfu01` as a multiply, the float stubs) were established on the OM-1. On the E-PM2 they are confirmed only where a case checks them: `rec_limit`'s `udfu01 30` and `udfu01 600` match the model, and fsub at 0x7E5018BC gave 3.0 − 1.0 = 2.0.
- **Stray code.** Code outside a case's ranges is an error. Unmodelled MMIO faults (lab-stub deny). A misaligned access faults, as om-emu enforces.
- **No proof of safety.** Passing these tests does not prove a patch is safe on the camera. They show only that the tested function, with these inputs and stubs, changes only the intended outputs. Caches, timing, other readers of the same bytes, and everything the stubs replace are not tested.

`python3 tools/freespace.py check SPEC...` runs the load-order check and the SRAM-caller check too, and
`epm2mod make` runs that command for every build that is not camera-tested. `epm2mod make` itself refuses a
spec that changes a byte another spec covers and keeps.
