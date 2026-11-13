# 03 — om-emu as a safety net for E-PM2 work

Review of `$S/ext/om-emu/` (flatpanda/om-emu, read as text only; nothing run), with the MN103 harness of
`$S/ext/oly_fw_analysis/` and the way caduceus-ep7 / caduceus-om3 test with an emulator.
`$S` = `/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad`.
Labels: **[V]** read in our E-PM2 bytes or map; **[X]** stated by an external source (file:line, paths relative to
the source's root); **[I]** my inference. My check scripts are in `$S/emu03/` (own code, run with `python3 -I`).

## 1. What om-emu is and how it works

**Scope.**
- A JavaScript lab that runs Olympus/OM firmware. It emulates the MN10300 CPU and the devices the UI needs: the
  interrupt controller, the timers, the OSD engine, the VSC display compositor and the SCPU interface. It runs the
  firmware's own uITRON kernel, GUI and camera application natively [X: README.md:3-7].
- It is not a full-system emulator. There is no boot from reset: the kernel init runs with some boot steps stood in,
  then a harness task starts the display, the GUI and the application. The sensor, AF, release and movie are named
  stand-ins (S-SCENE, S-CARD, ...) [X: README.md:11-15].
- Reference body: OM-1 (E143) v1.9. 19 other bodies run through ports [X: README.md:41-45; src/fw/models.mjs:138-1179].
  The E-PM2 (E101) has no `MODELS` entry [X: same lines].

**Architecture** [X: emu/ARCHITECTURE.md:9-22, 42-58]:
- **Core.** A CPU, a decode-cache interpreter and paged memory. The main block is mapped at `0x50000000`
  ("disassembly notation") and at its run-time base in DRAM (`0x60000000`, with an uncached alias at `0xA0000000`)
  [X: src/machine.mjs:117-119, 177-180].
- **Devices.** Built from a per-family board table (`src/fw/board.mjs`): the INTC banks, timer, VSC, OSD engine,
  hardware semaphores ("ISC"), SCPU interface and SRAM; optional HDMI, audio and a second core.
- **HLE labs.** An eight-class chain that installs address hooks and stand-ins and runs the kernel natively
  ("K-native").
- **Hosts.** A node HTTP player, a browser Worker, and a JSON-lines debugger (`bin/debug.mjs`: registers, memory,
  breakpoints, watchpoints, exec/MMIO/IRQ traces).

**CPU.**
- Base MN10300 only (AM30/31/32). Every AM33 form (the `F7` prefix, extended registers, EPSW) faults
  [X: docs/mn10300-isa-spec.md:31, 194].
- UDF forms are implemented only where firmware evidence supports them: integer multiply `udf00/udf01/udfu01`, float
  `udf02..06` and `udf14`, `udf07`, and context save/restore `udf12/13/15/20/21`. Everything else faults
  [X: docs/om1-udf-spec.md:42-60].
- A misaligned 16/32-bit access faults [X: docs/mn10300-isa-spec.md:129].
- **Not modelled:** caches and DMA coherence [X: emu/FIDELITY-NOTES.md:159-167]. Unclaimed MMIO in 0x8000_0000–0x9FFF_FFFF
  goes to a stub that returns the last value written or 0, unless the harness allowed the address
  [X: emu/FIDELITY-NOTES.md:169-177].

**How a body is "ported".**
- Every E143 address in the lab goes through `A()`, which looks it up in `PORTS[model]` (`src/fw/ports.mjs`, written by
  `bin/port.mjs`) [X: src/fw/model.mjs:1-5, 28-33].
- The table comes from a cross-build map [X: src/fw/xmap.mjs:6-11]:
  - instructions are compared with their 16/32-bit immediates and displacements masked;
  - a window of K instructions that occurs once in each build is an anchor;
  - from each anchor both builds are walked in step;
  - call/jump targets of equal pairs seed new walks, and equal pairs' imm32 operands vote for data addresses.
- An address the map cannot place becomes an `UNMAPPED` sentinel that throws where the lab uses it. Hand `overrides`
  place it, each with its evidence [X: bin/port.mjs:5-9].
- Things that are shape, not address (key matrix, menu tables, resource form, image base, vector page, core-id
  byte, ...) are read per body by rules in `src/fw/facts.mjs` [X: docs/ROADMAP.md:138-143].
- A body can chain through a closer, already-ported body (`port_via`) [X: docs/model-survey.md:7-10].

## 2. What applies to the E-PM2, with evidence

### 2.1 What om-emu says about E101 / E100

- **Survey rows** [X: docs/model-survey.md:70-72]. Both are fw 1600, main block 13.5 MiB, base `0x7e421020`
  (8.3 % of pointers land on strings), plain resources, "not tried (base)". E100 pairs 0.30M instructions with E143
  and leaves 215 of the lab's addresses unplaced. E101 pairs 0.30M and leaves 216. E112 (E-PL6) has the same base.
  "Unmapped" counts the lab's E143 addresses (out of 936 literals) that the map cannot place
  [X: docs/model-survey.md:77-78].
- **Tier D, "not tried"** [X: docs/ROADMAP.md:134; README.md:45].
- **Shared container, scramble and AM33 reset head** across all 32 bodies [X: docs/model-survey.md:82-85].
- **MMIO family.** "E144's (ISC 0x8fe00000, VSC 0x9c000000)", with E100/E101 among the bodies **without** the OSD
  engine at 0x9c100000 [X: docs/model-survey.md:86-90; docs/firmware-container.md:105-106].
- **No `udf07` bit-search helper** and none of its callers' sequences in E100/E101 [X: docs/om1-udf-spec.md:254-256].
- **No SCPU (Cortex-M) firmware block** in the 23 older bodies [X: docs/om1-scpu-spec.md:34].
- Nothing else in om-emu names E101 or E100. `analysis/om-c-firmware/README.md:90,94` only lists them.

### 2.2 Their claims checked against our bytes and map

| Claim | om-emu | E-PM2 v1.6 (our check) | Verdict |
|---|---|---|---|
| Run-time base | 0x7e421020 [X: model-survey.md:71] | Their `imageBase` rule (one `mov imm32,a0; jmp (a0)` in the first 0x400 bytes) re-implemented: hit at block 0xD2 → 0x7E421115 → base 0x7E421020. Same as our verified base [V: firmware-map.md §4] | agree |
| Reset head bytes | `fafcfff0 cbcb f8fefc fcff..` [X: model-survey.md:84] | block 0 starts `fafcfff0 cbcb f8fefc fcff dc00…` [V] | agree |
| Main block size | 13.5 MiB | 14,155,712 B [V] | agree |
| Hardware semaphores ("ISC") at 0x8FE00000 | E144 and E118 families [X: src/fw/board.mjs:194-195, 290] | 15 loads of 0x8FE00000 and 2 of +4, all in kernel code. The lock helper 0x7E432851 is `bset d0,(a0)` test-and-set, `bclr` at 0x7E43285E; 9 callers [V] | agree (base); stride/groups differ: E-PM2 uses +0 and +4 [V] |
| VSC at 0x9C000000 | "E144 family" [X: model-survey.md:87] | The 18 loads of 0x9C000000 are all in the IMG library (0x7E54D5A7…0x7E5503CD). Each is `cmp (0x8050)`: CPU0 → 0x9C000000, CPU1 → 0x9E000000, a per-CPU window, not a display unit [V: disasm 0x7E54D59A, 0x7E5501AF]. Our display controller is 0x9A900000 and the OSD 0x9AA00000 [V: 13f §2.1]. Their classifier counts loads and falls back to "E144" when neither family's addresses win (`x > ix ? E143 : E144`) [X: bin/fw-survey.mjs:107-108] | **disagree** for the VSC; the family label is a fallback |
| No OSD engine at 0x9C100000 | [X: model-survey.md:88] | 0 loads [V]. E-PM2 OSD = 0x9AA00000, `[OSD_DRV]`, IRQ 111 [V: 13f §2.1] | agree (absent); the E-PM2 OSD lives elsewhere |
| Two cores / INTC banks | E143: 4 banks; E144 and E118: 3 banks [X: board.mjs:27, 200, 302] | 2 banks: `irq_register` 0x7E44B57F picks 0x99200000 or 0x99300000 by (0x8050). 0x99B00000 is AE statistics, not an INTC [V: 13f §2.1-2.2] | differs from all om-emu families |
| INTC registers | E118 family: presented +0x200, IPI set/clear +0x308/+0x30C, kick +0x310, +0x314, irqs < 122 [X: board.mjs:296-303] | +0x200… pending vector (0x7E44B524), doorbell status/ack +0x308/+0x30C (CPUCONN, IRQ 123), raise +0x310 (0x7E430091 writes 0x99200310 = 1); irq < 125 [V: 13f §2.2; bytes] | matches the **E118 family** layout, not E144's (+0x4xx) |
| Timers | E118 family: 10 channels, reload +0x28, counter +0x50, IE +0x78, status +0x7C, µs channel 9, reload 0x3FFFFFFF, prescaler 191 [X: board.mjs:306-319] | 0x98900000: 10 channels, reload +0x28+4n, count +0x50+4n, IE +0x78, ack +0x7C, ch9 free-run 0x3FFFFFFF, ch0 prescaler 161, ch1 tick IRQ 69 [V: 13f §2.5] | **same layout**; prescaler and IRQ numbers differ |
| SCPU interface 0x98E00000 | E144 family: command +0xA4, parameter +0x8C, clock +0x98/+0x9C, word +0x48, commit 0x20041001 [X: board.mjs:232-243; src/dev/scpu.mjs:10] | Our "system controller" 0x98E00000: `wdt_set_time` writes +0x8C, ORs +0xA0, commits 0x20041001 to +0xA4, polls +0x48 bit 7 (0x7E45D269–0x7E45D28D); +0x98/+0x9C are read by SRAM code [V: 13f §2.6; bytes] | agree. om-emu's "SCPU interface" **is** our system controller. E-PM2 has no separate SCPU MCU [V: PER_SCPU_POLLING empty] |
| Interrupt vector page | rule `vectorPage`: 7 `mov imm32; movhu (0x80LL)` stores [X: src/fw/facts.mjs:221-249] | Rule re-implemented: run at 0x7E42109C → 0x7E430020..70, page 0x7E430000 (same as our 13f §2.2). A second run at 0x7E426812 → 0x7E448020.. (CPU1's vectors, I) [V] | agree; page is in the image, not 0x6003/0x6041 RAM |
| Core-id byte getter | rule `coreByte`: one `movbu (abs32),d0; retf` into SRAM 0x8FF00000 [X: facts.mjs:202-216] | **0 hits** [V]. The E-PM2 reads the CPU number from (0x8050), 843 readers [V: 13f] | rule would throw; hand fact needed |
| kcb pointers at 0x8FF00004 | E144 family [X: board.mjs:192] | Kernel entry reads (0x8FF00004 + cpu·4) [V: 13f §2.2]; 331 literals of 0x8FF00004 [V] | agree |
| Static task table | kcb+124: 28-byte rows {id, atr, exinf, task, pri, stksz, stk}; ids `cpu<<12 \| index` [X: docs/om1-kernel-spec.md:30, 49] | Tables at block 0x17CB0 / 0x1C490 have the same 7×u32 rows (e.g. `0x8085,0,0,0x7E5065EF,0xC,0x800,0x604DEB80`; CPU1 `0x9004,…`) [V] | agree |
| A-unit context save | `getclx/getchx/udf15`, restore `udf20/21` (E143 0x5000f25c) [X: om1-udf-spec.md:57-58] | Same sequence at 0x7E4300A7–0x7E4300D0 [V] | agree |
| UDF forms in use | rows 1-16 implemented, others fault [X: om1-udf-spec.md:42-60] | In real code (functions without the data_page/suspect flag, code ranges only; 2.88M instructions) [V]: udf00 (reg/imm8/16/32), udf01, udfu01 imm8/16/32, the float stubs udf02–udf06 at 0x7E5018BC–0x7E5018F9 (fsub 0x7E5018BC has 445 callers), udf12/13/15/20/21 context save, udf15 at 0x7E501919. Every other form hit was in a data page. No udf07 [V] | every form used is in their implemented set; the E-PM2 unit's semantics are unproven (§5) |
| AM33-only instructions | fault [X] | 0 `F7`/extended-register instructions in real code. The only hits were in data pages, or were `F5` UDF forms that our objdump decodes as `mov a1,r1` [V] | om-emu's base-ISA CPU fits |

**Side findings for our own tools and map** [V]:
- `tools/disasm.py` (objdump in am33-2 mode) prints `F6 3x` as `mcst9` and `F6 6x` as `mcst48`. In the E-PM2 they are the
  float stubs udf03 (fsub) and udf06 (fcompare).
- Our MMIO census (0x98000000–0x9AFFFFFF, 13f) misses the per-CPU window 0x9C000000 / 0x9E000000 that the IMG library
  uses.

### 2.3 What a port of the E-PM2 would need

- **CPU.** No change for the instruction set: the E-PM2 uses only base MN10300 and the implemented UDF forms [V + X].
  The open risk is whether the TruePic VI UDF unit has the same semantics as the OM-1's (see 5.1) [I].
- **Machine and board.**
  - A new `MODELS` entry (`image_base` 0x7E421020, `rom_len` 0xD7FFC0, digests).
  - DRAM 512 MiB: the image ends at 0x7F1A0FE0. This fits the lab's maximum (`DRAM_MAX` 512 MiB), but not E143's
    384 MiB [X: src/core/mem.mjs:108; board.mjs:151; machine.mjs:178].
  - A new board family:
    - 2 INTC banks, ~125 IRQs, IPI 123;
    - E118-style timers with prescaler 161 and IRQ base 68;
    - ISC at 0x8FE00000 (+0/+4);
    - SCPU at E144's offsets;
    - vector page 0x7E43xxxx;
    - a hand-given core byte [V for the values].
- **Devices to write.** The display controller at 0x9A900000 (IRQs 14/15) and the OSD at 0x9AA00000 (IRQ 111) match
  none of om-emu's VSC kinds 1–3 or its OSD engines [X: board.mjs:43-56, 218-231, 320-355; V: 13f]. They would be new
  models built from the E-PM2 drivers 0x7E6B75C2–0x7E6B990E and 0x7ECCD276–0x7ECCDDED [V]. Per our map, the SoC is the
  E-P5's generation, not the E-M5 II/PEN-F one that om-emu ported last [V: 13f §2.1 cross-body check].
- **Kernel init.**
  - K-native needs the E-PM2 kernel's entry points. The kernel internals are at 0x7E4300D7–0x7E438BF1 [V: 15d], and
    `OlyTaWu`, `OlyTaSt`, `OlyEvWt`, `OlyQeWr`, `OlyQeRd` strings are present [V].
  - The reset code copies `.data` (0x7E8DA000 → 0x602A9B40). The lab's flash-copy rule would have to handle it [V: map §1].
  - CPU1 hosts AVPI, art, C3D and AV tasks [V]. om-emu runs one core plus an optional second core [X: src/core/cores.mjs:1-20].
- **GUI start-up.**
  - The lab's harness is written against E143 functions. 216 of its addresses do not place in E101 [X].
  - The string rules om-emu relies on do not match: `[CHG] CHG MAIN S` 0, `Menu_ListMenu_Tab_Menu_` 0, `ScpuBkupW` 0
    [V: string counts].
  - The E-PM2 GUI is a different toolkit generation: `[OSD_CONTROL]` at 0x7ECCB800, CA_MAIN, `[GUI App]` 209 strings [V].
- **Effort, honestly** [I, scaled from om-emu's own record: E134 took 12 stops and E137 10, each "one session step of
  reading the firmware", docs/model-survey.md:121-129; the E118 family took about 30 findings, model-survey.md table rows]:

| Goal | Needs | Estimate |
|---|---|---|
| A. One leaf function (no MMIO, no kernel calls) | scratch `MODELS` + board entry; `.data` preload if globals are read | 1–2 days |
| B. A module or state machine with kernel services | + stand-ins for `Oly*` wrappers or K-native init on CPU0 | 1–3 weeks |
| C. Kernel bring-up, tick and IRQs on CPU0 | + reset-head/.data rules, INTC/timer devices for 2 banks | 2–4 weeks |
| D. GUI start-up to a drawn screen | + two new display devices, GUI harness re-pointed from E143, many stops | months; the author lists E101 as untried |

A port of E101 would also serve E100 and E112, which have the same base and nearly the same code [X: survey rows; I].

### 2.4 Testing patches without a full port

- **om-emu debugger, standalone machine.**
  - `bin/debug.mjs --image FILE --entry ADDR --reg … --write … --stop ADDR --read …` runs code from an entry point
    without the lab and prints JSON [X: emu/bin/debug.mjs:1-27, 140-183]. `--patch FILE` applies byte patches in
    memory after checking their `old` bytes [X: emu/README.md:598-630].
  - The image is mapped at the model's `image_base`, and an unknown model is refused [X: src/fw/model.mjs:18-22]. So
    E-PM2 code needs a local `E101` entry (tier A). With E143's entry the E-PM2's absolute addresses would point at
    unmapped memory (E143's DRAM ends at 0x77FFFFFF) [X: board.mjs:151; I].
  - This is enough for leaf functions and table readers, such as the readers of the tables our film-portra patches change
    (`fwmap xref 0x7E75D6F0` → 0x7E56EA68, IMG library) [V]. Run them stock against patched and compare the outputs, as
    caduceus-ep7 does.
- **oly_fw_analysis MN103 harness.**
  - A patched GNU `sim` driven from Python [X: docs/tooling/EMULATOR.md:3-8, 35-41]. `penf_emulator.firmware()`
    accepts only the PEN-F hash [X: :47], but `Region`/`execute` take any image: caduceus-ep7 runs E-P7 routines with
    it [X: caduceus-ep7/tools/ep7_verify_lcd_tint.py:12-24].
  - Caveats for the E-PM2:
    - No alignment checks [X: EMULATOR.md:109-114].
    - GNU's UDF semantics differ from om-emu's evidence-based ones: GNU sign-extends the `udfu01` immediate and treats
      udf04/udf05 as AM30 operations, not floats [X: om-emu docs/om1-udf-spec.md:34-35, 94-97]. The E-PM2 has 268
      `udfu01 imm8 ≥ 0x80` and 39 `imm16 ≥ 0x8000` sites, plus float stubs with 445+ callers [V]. Those paths would
      compute wrong values unless they are patched.
- **How the Caduceus projects use emulators.**
  - caduceus-ep7: every patch has an emulator test that runs the real code patched against stock and checks that only
    the intended values change; every package must decode to exactly the emulated image [X: caduceus-ep7/README.md:316-318].
  - caduceus-om3: drives full om-emu E147 play sessions by importing `Player` with its patched image, pressing keys and
    reading memory [X: caduceus-om3/tools/emulator/session_ed1.mjs:1-30; README.md:132, 153]. That works because E147 is
    a ported body.
- **Lesson from oly_fw_analysis.** A misaligned structure passed their simulator but restarted the camera
  [X: EMULATOR.md:109-114]. om-emu's alignment fault would have caught it [X: mn10300-isa-spec.md:129]. Passing an
  emulator test is not proof of safety on the camera [X: EMULATOR.md:120-124].

## 3. Recommendations (ranked by value / safety / effort)

1. **Use the cross-checks above in our map.** No approval needed: notes only, no edits made here.
   - Name 0x98E00000 as om-emu's "SCPU interface" and record the E144-family offsets.
   - Record that the INTC and timer layouts match om-emu's E118 family.
   - Add the 0x9C000000 / 0x9E000000 per-CPU window as an unmapped MMIO region.
   - Note the `mcst9`/`mcst48` mis-decode in `tools/disasm.py` output.
   - Value high, risk none, effort hours.
2. **Adopt the caduceus-ep7 test contract for any future patch.** No approval to write the checks; patches stay as the
   user decides.
   - stock vs patched;
   - only the intended outputs change;
   - alignment of every structure we hand to stock code;
   - negative controls (unmapped/poisoned memory, non-zero inputs).
3. **Tier-A om-emu function harness** for patch readers. **Needs approval:** running external JavaScript; installing
   node ≥ 26 (here: v22.22.1 [V]); local edits in a scratch copy of code that has no licence (§4). Best fit of the
   three tools for E-PM2 code, because of its UDF and alignment strictness [I].
4. **GNU-sim harness (oly_fw_analysis).** **Needs approval:** building GPL code and running their Python. Use it only
   with a UDF fix, or for paths free of `udfu01`-with-high-immediate and float stubs [I].
5. **Full port (tiers C–D).** Not recommended now: months of work, with weak payoff for data patches [I]. Instead the
   user could ask flatpanda: E101/E100/E112 is one port for three bodies, and it is in their tier D [X: ROADMAP.md:134].
6. Nothing in this review needs flashing.

### Running it: exactly what we would run (only after approval)

```sh
S=/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad
mkdir -p "$S/run" && cp -a "$S/ext/om-emu" "$S/run/om-emu"     # work copy; ext/ stays untouched
# hand edits in $S/run/om-emu/emu/src/fw/models.mjs (+ board.mjs): an E101 entry with
#   image_base 0x7E421020, rom_len 0xD7FFC0, rom_sha256 of our block 0, a board family "E101" with the §2.3 values
cd "$S/run/om-emu"
OM_EMU_MODEL=E101 node emu/bin/debug.mjs \
  --image /path/to/EPM2Mod/build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin \
  --entry 0x7E5018BC --reg d0=0x40400000 --reg d1=0x3F800000 --reg mdr=0x7E421020 \
  --stop 0x7E421020 --insn-limit 1000                    # fsub stub, retf to MDR; expect d0 = 0x40000000
```

- **Reads.**
  - The om-emu ES modules under `$S/run/om-emu/emu/` (statically imported by `bin/debug.mjs`: `src/`, `checks/lib/`,
    `host/debughost.mjs`) [X: bin/debug.mjs:34-46].
  - Our block-0 file, read-only.
- **Writes.**
  - stdout JSON only (stderr with device/trap lines on a fault) [X: bin/debug.mjs:170-183].
  - Trace files only if `--trace/--exec-trace/--mmio-trace/--irq-trace PATH` is given.
- **Network and subprocesses.**
  - No network: `node:http` is used only with `--attach` to 127.0.0.1 [X: bin/debug.mjs:132, 212].
  - A subprocess (`tools/mn10300-objdump`) only with `--disasm` [X: bin/debug.mjs:32].
  - `fetch-fw.mjs`, `fw-survey.mjs` and `play.sh` download from the vendor or open a browser: do not run them [X: README.md:57-63].
- **Before running.** Read `src/lab/sim.mjs` and `checks/lib/env.mjs` for import-time file access; I checked only the
  imports and the `debug.mjs` main path [I].
- **Optional smoke test.** `node emu/bin/test-pure.mjs` needs no firmware and runs the ISA vectors [X: README.md:80-87].
  Its file writes are not checked here [I].

## 4. Licence notes

- **om-emu** has no repository licence [V: searched the whole tree]:
  - there is no LICENSE, COPYING or NOTICE file;
  - `emu/package.json` has no `license` field and has `"private": true`;
  - the project's own sources have no SPDX or copyright headers.
- **Exceptions:**
  - `tools/a53-oracle/om-isc.c` and `om-isc-qemu.patch` are GPL-2.0-or-later
    [X: tools/a53-oracle/README.md:12-15; om-isc-qemu.patch:2-5];
  - `emu/refs/mt19937.mjs` carries the MT19937 BSD-style notice and PSF licence text [X: emu/refs/mt19937.mjs:11-42].
- **What this means** [I, not legal advice]:
  - Treat om-emu as all rights reserved. We may read it and cite facts (addresses, register offsets) with attribution.
  - Do not copy or adapt its code into EPM2Mod.
  - Running a modified private copy is a grey area for the user to decide.
  - caduceus-om3 handles it the same way: om-emu is "not included and keeps its own licence"
    [X: caduceus-om3/NOTICE:21].
- **oly_fw_analysis.**
  - Apache-2.0, except `tools/mn103_runner.c`, `mn103_strict.patch` and `prepare_mn103_sim.py`, which are
    GPL-3.0-or-later [X: RIGHTS-AND-PROVENANCE.md:3-16].
  - `penf_emulator.py` and `penf_probe.py` carry `SPDX-License-Identifier: Apache-2.0` [X: their line 3].
  - om-emu's own study recorded "no repository-wide licence" for an earlier revision
    [X: om-emu analysis/oly-fw-analysis/README.md:18]. Our copy has the Apache LICENSE.
- **Firmware.** Neither tool licenses the vendor firmware [X: oly_fw_analysis RIGHTS-AND-PROVENANCE.md:31-36;
  om-emu README.md:113-122].

## 5. Open questions

1. **UDF semantics.** Does the E-PM2's (TruePic VI) UDF unit behave like the OM-1's? om-emu established float
   udf04/udf05 and BSCH polarity on E143 only [X: om1-udf-spec.md:94-97, 254-256]. The E-PM2 stubs have the same shape [V], but
   no known-answer test has been run on E-PM2 code.
2. **The 0x9C000000 / 0x9E000000 window.** What is the per-CPU window in the IMG library? Local RAM, or job descriptors?
3. **Display and OSD registers.** How far do the E-PM2 display (0x9A900000) and OSD (0x9AA00000) layouts resemble any
   om-emu VSC/OSD kind? I did not compare them register by register.
4. **Rules on E101.** Which om-emu `facts.mjs` rules throw on E101 besides `coreByte`? Only running `bin/port.mjs`
   (approval) would tell.
5. **Is the brief out of date?** `patches/pixel-hacking.json` says "camera-tested 2026-11-08 (works)", and
   `experiments/2026-11-09-film-portra/NOTES.md` says `film-portra-xp-labelled` "is flashed" [V]. The brief says nothing
   was flashed.
6. **Author's view.** Would flatpanda grant a licence, or port E101/E100/E112 themselves?
