# tools/emu: E-PM2 functions in om-emu, stock against patched

This harness runs single E-PM2 v1.6 block-0 functions in [om-emu](https://github.com/flatpanda/om-emu)'s MN10300 machine. It runs each input row on stock block 0 and on a patched block 0, then compares the outputs. It follows the caduceus-ep7 contract: run the real code, patched against stock, and check that only the intended outputs change.

Labels: **V** = ran in the emulator and checked against an independent Python model or the notes; **I** = inferred.

## Setup

- **Node 26:** `~/opt/node26/bin/node` (v26.13.1). The system node 22 is too old. Override it with `OM_EMU_NODE`.
- **om-emu:** `~/opt/om-emu`, with the local E101 changes in `om-emu-E101.patch` (also kept at `~/opt/om-emu-E101.patch`). Override the path with `OM_EMU_DIR`. To set up a fresh copy: `cd ~/opt/om-emu && patch -p1 < .../tools/emu/om-emu-E101.patch`.
- **Stock block 0:** `build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin`. This is the descrambled OE payload, sha256 `1b7c4bb1…71468d`; the harness checks it.

### What the om-emu patch adds

om-emu refuses an unknown model. Its lab is written for the OM-1 (E143), so the patch adds the E-PM2 as a **function-only** model.

- **`src/fw/models.mjs`: a new `E101` entry.**
  - Image base 0x7E421020, block length 0xD7FFC0 and the block-0 digest.
  - `function_only: true`.
  - A board on om-emu's E118 family. That family's INTC and timer layout matches the E-PM2's (caduceus review 03 §2.2). The entry gives these values by hand:
    - hardware semaphores at 0x8FE00000, 2 groups, stride 4;
    - 2 INTC banks (0x99200000, 0x99300000), 125 IRQs, IPI 123;
    - timer prescaler 161, IRQ base 68;
    - CPU-number byte 0x8050 (low lab RAM, so CPU 0);
    - vector page 0x7E430000;
    - **512 MiB DRAM**, so that 0x7E421020 + block fits under 0x80000000. This is om-emu's `DRAM_MAX`. Its ROM view (`ROM_SIZE` 32 MiB) already fits the 13.5 MiB block;
    - no scratch region and no reset-head rule.
  - om-emu's VSC model normally sits at 0x9C000000. On the E-PM2 that address is the IMG library's per-CPU window, so the patch **parks** the VSC and the OSD engine at 0x9F600000 and 0x9F610000, pages no E-PM2 code loads. E-PM2 accesses to 0x9C000000 then reach om-emu's default-deny stub: a CPU read there faults with reason 2 (**V**).
- **`src/fw/model.mjs`:** on a function-only model, `fact()` returns E143's value. The lab modules still load when `bin/debug.mjs` starts, and some read facts at load time; nothing in a debug run reads them.
- **`src/lab/hle.mjs`:** the lab (`HLE`) refuses to start on a function-only model. This keeps the E143 placeholder facts from being used.

## Files

| File | What it does |
|---|---|
| `omemu.py` | Driver. Starts `emu/bin/debug.mjs --serve` with `OM_EMU_MODEL=E101` and speaks its JSON-lines protocol. `Emu.call()` calls a function through a real `call` instruction in scratch RAM, using the callee's register list and frame size from its call sites in the image. Stubs are breakpoints: Python sets the return registers, then the CPU returns through a `retf` that has the frame of the call that reached the stub. Each call records an exec trace, and the caller rejects code that ran outside the case's ranges. The call also checks that sp is balanced on return. |
| `patchblock.py` | Builds a patched block 0 from `patches/*.json`-style specs, with the same base-hash and expected-byte checks as `tools/build.py` (it imports `build.apply_op` and `oetool.parse`). It prints the changed runtime ranges. Ops on other blocks are checked and reported as not emulated. |
| `cases.py` | Named cases: entry, allowed code ranges, stubs, input rows, outputs, and a Python model of the expected outputs. |
| `emurun.py` | CLI: `list`, `run CASE` (one image, checked against the model) and `diff CASE --patch SPEC…` or `--image BLOCK0` (stock against patched). Exits 1 on any mismatch, fault, stray code or unexpected change. |
| `specs/rec-limit-3600.json` | Emulator test input only, not a camera patch: changes the recording-limit imm16 1740 to 3600 (2 bytes). |
| `om-emu-E101.patch` | The om-emu changes above (`patch -p1` in the om-emu root). |

## Usage

```sh
python3 tools/emu/emurun.py list
python3 tools/emu/emurun.py run rec_limit
python3 tools/emu/emurun.py diff rec_limit \
    --patch tools/emu/specs/rec-limit-3600.json
python3 tools/emu/emurun.py diff curve_select \
    --patch patches/film-portra.json --json /tmp/out.json
python3 tools/emu/patchblock.py patches/film-portra-xp.json \
    -o /tmp/xp.block0.bin
```

Calling om-emu's debugger directly, for example memcpy through a hand-written `call 0x7E5081FA,[d2,a2],8` at 0x7D000000:

```sh
cd ~/opt/om-emu && OM_EMU_MODEL=E101 ~/opt/node26/bin/node emu/bin/debug.mjs \
  --image /path/to/EPM2Mod/build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin \
  --entry 0x7D000000 --write 0x7D000000=ddfa815001a008 \
  --write 0x7D200000=000102030405060708090a0b0c0d0e0f \
  --reg a0=0x7D300000 --reg a1=0x7D200000 --reg d0=16 --reg sp=0x7D100000 \
  --stop 0x7D000007 --read 0x7D300000:20
```

The harness uses scratch RAM at 0x7D000000–0x7D2FFFFF: the trampoline, the return pads, the stack (sp 0x7D100000) and the data buffers. All other RAM starts at zero. `.data` is not preloaded.

## Cases, results and stubs (2026-11-12)

| Case | Entry | Rows | Stubs | Result |
|---|---|---|---|---|
| `memcpy` | 0x7E5081FA | 7 (byte, halfword and word paths, n = 0) | none | matches the model; guard bytes kept; d2 and a2 kept (**V**) |
| `strlen` | 0x7E508346 | 5 | none | matches the model (**V**) |
| `rec_limit` | 0x7E6EDE08 | 48 (MOV q6/q3/q4/q7, AVCHD q5/q3/q4, format 1; rate hi/lo; free space 500 sectors, 1 GiB, 64 GiB) | 4, listed below | matches the model on stock and patched (**V**) |
| `curve_select` | 0x7E56E837 | 229 (7 modes × contrast −3…+3, High/Low Key, the identity flag, art codes 8–184) | none (its only callee, 0x7E56E80F, runs natively) | the 52 modelled rows match; art codes 85/87 → 0x7E75F2F0 and 167 → 0x7E7616F0, as film-portra NOTES §11.1 says (**V**) |

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
- **`curve_select` with `patches/film-portra.json`:** 12 of 229 rows change. 7 are Portrait (mode 4) at contrast −3…+3. The other 5 are **art codes 9, 13, 55, 129 and 133**, which also select Portrait's Contrast 0 table 0x7E75DAF0 through the jump table 0x7E78C8E4 (**V**). So that patch changes more than Portrait. What those art codes are (scene modes?) is **I**, not traced.
- **`curve_select` with `patches/film-portra-xp.json`:** 2 rows change, art codes 85 and 87 (Cross Process I, table 0x7E75F2F0). The patch's 24 base-gamma tables are not read by this selector, so this case does not test them.
- **`curve_select` read check:** in all three diffs, every row that changed read patched bytes, and every row that read patched bytes changed.

**Side findings (V in the emulator):**
- With an unknown MOV quality, `rec_limit` takes the reserve from the caller's a2, because the code never sets it on that path. It also prints `[QT] Parameter Error quality` twice.
- The `rec_limit` limit for MOV q4 on 64 GiB is 6202 s: the 4 GiB cap binds below 7200.

## Limits

- **Function level only.** Nothing boots; there is no kernel, no tasks, no interrupts, no timers in use and no second core. The IMG engine, DMA, the display, the sensor and all other devices are not modelled. The cases are leaf functions or functions with stubbed callees, and a stub's answer is our assumption.
- **RAM.** RAM starts at zero, and `.data` (0x7E8DA000 → 0x602A9B40) is not copied. A function that reads globals needs them written by its case.
- **Memory map.** The whole block is mapped at 0x7E421020. On the camera the boot copies only up to 0x7E881000, and later parts load as overlays. A case that reads beyond 0x7E881000 sees bytes that may not be there at run time.
- **UDF.** om-emu's UDF semantics (`udfu01` as a multiply, the float stubs) were established on the OM-1. On the E-PM2 they are confirmed only where a case checks them: `rec_limit`'s `udfu01 30` and `udfu01 600` match the model, and fsub at 0x7E5018BC gave 3.0 − 1.0 = 2.0.
- **Stray code.** Code outside a case's ranges is an error. Unmodelled MMIO faults (lab-stub deny). A misaligned access faults, as om-emu enforces.
- **No proof of safety.** Passing these tests does not prove a patch is safe on the camera. They show only that the tested function, with these inputs and stubs, changes only the intended outputs. Caches, timing, other readers of the same bytes, and everything the stubs replace are not tested.
