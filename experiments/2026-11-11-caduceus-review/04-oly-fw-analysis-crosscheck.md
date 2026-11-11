# 04 — oly_fw_analysis (PEN-F research) cross-checked against the E-PM2 map

Reviewer scope: `$S/ext/oly_fw_analysis/` (301 files), read as text only. No external code was run, built or imported. E-PM2 checks use our tools (`fwmap.py`, `disasm.py`, `oetool.py`) on block 0 sha256 `1b7c4bb1…71468d` and on the update file sha256 `34d339ac…c3e300`.

Labels: **[V]** read in our E-PM2 bytes or map; **[X]** stated by the external source (path:line, relative to the repo root); **[I]** my inference.

## 1. What the source is and how it works

- It is a research repository for Olympus/OM firmware. It goes deepest on the **PEN-F 3.1 build 3101**, with comparisons for E-M1/E-M5/E-M10, E-P7, OM-3 and OM-5 [X README.md:7-9].
- **Docs** are arranged by topic: format, boot, protocols, color, features, safety and tooling. Every address belongs to one named build [X docs/README.md:3-5, 27-29].
- **Tools** (134 Python files, Apache-2.0) [V: SPDX count]:
  - `oly_container.py`, an OE decoder/encoder;
  - about 100 `penf_*` probes, which run native PEN-F code in a patched GNU MN103 simulator;
  - an IDA 4.9 helper;
  - a PEN-F HSL patch, built from assembly.
- **Evidence model:**
  - Every finding states the model, build, input hash and address space [X CONTRIBUTING.md:6-13].
  - Each finding says whether it rests on disassembly, emulation, a desktop renderer or a physical camera.
  - Addresses are marked S (static), N (bounded native execution) or C (connected replay from main) [X docs/boot/pen-f/FUNCTION_MAP.md:7].
- **Physical results:** HSL installs, a restore to stock and a reinstall all worked on a real PEN-F [X docs/boot/pen-f/RECOVERY.md:80-83].
- **Not established for the PEN-F:** the OK+power selection of the SD updater, and any immutable recovery ROM [X RECOVERY.md:3-5, 56-58].

## 2. What applies to the E-PM2, with evidence

### 2.1 Cross-check table

| Topic | Their claim (PEN-F unless stated) | E-PM2 | Verdict |
|---|---|---|---|
| Payload transform | Permutation `1,3,0,2,6,4,7,5,11,10,9,8,13,14,12,15`, then XOR 0xFF [X docs/format/CONTAINERS.md:33-36] | Same `LANES` in `oetool.py`; the firmware descrambler 0x7E54343F does the same per 16-byte block [V 02 §1.5] | **Agree** |
| Checksum | Header + **decoded** payload + trailer, as u32 words, sum to 0 [X CONTAINERS.md:38-41] | Same rule. The firmware checks it at 0x7E54337D over size+64 bytes after descrambling [V]. All 5 sections of v1.6 pass [V, own check] | **Agree** |
| Header fields | 0..1 `OE` "signature", 2 model, 8 address, 12 length, 16 build, 20 kind u16, 28 zero [X CONTAINERS.md:17-25] | The firmware reads byte 0 as maker `O`, byte 1 as fw_kind (`E`,`A`,`M`,…), byte 20 as sub-kind and byte 21 as the scramble flag [V 02 §1.4]. Our kinds split the same way: 0x0100 = sub 0 USR, 0x0101 = OSD, 0x0106 = ARTFIL, 0x0104 = FRAME, each with flag 1 [V bytes 20–21 = `0001`/`0101`/`0601`/`0401`] | **Differ by model** (their u16 view covers the same bits). Our split is the firmware's own |
| Header/trailer copy | Parser requires header[0:28] = trailer[0:28] and header[28:32] = 0 [X tools/oly_container.py:127-130] | The firmware compares only the first 20 bytes (5 words) [V 02 §1.5]. All v1.6 sections still satisfy 28 bytes and zeros [V own check] | **Agree**; their parser is stricter than the camera |
| Trailing `OM` data | Parser rejects any non-`OE` section [X oly_container.py:112-113] | The 65,600-byte "OM tail" is an ordinary section: maker `O`, kind `M` (BURE stabiliser), model `10 10`, size 65,536, valid checksum, header[0:28] = trailer[0:28] [V own check]. The worker sends it to the stabiliser MCU only if stab type == 1 [V 02 §1.6, §1.9]. Their tool would fail on our file [I, from their code]; their inventory marks E-PL5 `header_walk_complete: false` [X provenance/firmware-inventory.json:2537-2551] | **We are right for the E-PM2.** Our `firmware-format.md` should stop calling it "opaque" |
| Decoded blocks 1–3 | E-PL5 1.6 decoded hashes: 0x101 `97a3e75d…`, 0x106 `972d0cfe…`, 0x104 `02980862…` [X firmware-inventory.json] | E-PM2 v1.6 blocks 1–3 hash to the same three values [V own decode] | **Agree** (an independent decoder confirms ours) |
| Update modes | Mode 0 = SD validate then write; mode 2 = USB check, no write; mode 1 = USB commit [X RECOVERY.md:33-37; USB_UPDATE.md:62-67] | FIRMUP_SRV: type 1 → mode 0; type 3 FIRMUP_CHECK → mode 2 (no write); type 4 FIRMUP_USBUP → mode 1 [V 02 §1.3]. Writes are gated on mode ∈ {0,1} at 0x7E5442EE [V disasm] | **Agree** |
| Reject before write | A stale main checksum gives error **0x3211** before any flash request. A bad later component blocks all writes [X RECOVERY.md:39-42] | A sum failure on `E` returns **0x3211** [V 02 §1.5]. Writes start only after all sections pass [V 02 §1.6] | **Agree**, down to the error code |
| Write extent and address | Whole component written. Main destination 0x803a0000 = 0x80000000 \| logical [X CONTAINERS.md:69; tools/penf_repack_preflight.py:91] | Whole section including its 64-byte header. Destination = 0x7E45DB37(start_adrs) = `0x80000000 \| (a & 0x3FFFFFFF)` for 0x40000000–0x40FFFFFF [V disasm] | **Agree** |
| Version check | Same-version install accepted on the camera path [X CONTAINERS.md:71-73] | No version/downgrade check in the body path [V 02 §1.4] | **Agree** |
| Readback | Erase/program/readback seen, but some wrappers drop lower errors [X RECOVERY.md:50-54] | Normal write 0x7E4509C0: erase+write 0x7E4505D6 → read back 0x7E4217E6 → word-sum fold 0x7E450AE6, error 0x3203 if non-zero [V disasm]. Whether every caller acts on that error was not traced [I] | **Agree** (both read back; propagation is open) |
| Partial packages | A main-only package is accepted and writes only that component [X CONTAINERS.md:55-69] | Each write in worker 0x7E543DDE is gated by its own "found" bit (e.g. `and 1` USR at 0x7E5447D7, `and 0x4000` NOREXE at 0x7E544831) [V]. No "all kinds required" test seen [V for the code read]. A main-only E-PM2 file would probably be accepted [I, untested] | **Probably agree**; not tested on the E-PM2 |
| Movie limit | PEN-F routine returns 1740 (modes 3/6) and 7200 (mode 4) [X docs/features/HISTORICAL_HACKS.md:22-25] | `mov 7200,a3` / `mov 1740,a3` at block 0x2CCEC0/0x2CCF00 [V firmware-format.md] | **Agree** (same constants) |
| SD file name | `DCOLYMP`, `E122????BIN`, `9999` suffix is selection data [X RECOVERY.md:9-11; CONTAINERS.md:71] | `DCOLYMP`, `E101????BIN` … `E100????BIN` [V 02 §1.2] | **Agree**; model code differs |
| Startup tasks | Only task 1 is auto-started. USTART1 = task 47. CPU id in task-id bits. Three cores [X STARTUP.md:9-16; FUNCTION_MAP.md:26] | Only the boot task is TA_ACT. CPU in bits 12–14. **Two** cores. USTART1 = task 0x52 USRSTART_FIRST [V map §1, §5; 0x7E43EA1C = 0x52] | **Agree** on the scheme; core count differs by model |
| SD-update selection | Not found in main. The SD client (task 95) is not auto-started [X RECOVERY.md:26-29; STARTUP.md:71-74] | Found in block 0: Usr0 0x7E503DD4 calls 0x7E5436D1 → 0x7E544A6F. It returns 1 (card update) when `table[poweron_factor]` is 12/0x01000001/0x01000002 and byte 0x602A9B54 is 0 [V 02 §1.1]. The branch at 0x7E504A59 starts FIRMUP_CLI (0x14), otherwise USTART1 (0x52) [V disasm] | **Differ by model**: our map has what theirs lacks |
| Relocated SRAM helper | 6 KiB of helper code is copied to 0x47000800..0x47002000 [X docs/format/pen-f/ADDRESS_SPACES.md:45-46] | The boot task copies 2 KiB from 0x7F14B000 to SRAM 0x47001000 (watchdog kick) [V 01 §2] | **Agree** on the pattern |
| Settings store | Typed property registry with consistency rules. Mode store guarded by a halfword-sum checksum plus working/backing copies [X docs/color/pen-f/STRUCTURES.md:9-29] | prm tags (type in the low nibble). 6 storage classes. MODE/param banks kept as two flash copies with a counter and checksum (`Bank0 > Bank1`, `chksum OK/NG`, 0x7E450C4B/0x7E450E86) [V 07 §1, 01 §6]. Getter 0x7E457C75 | **Differ by model** (other generation and layer). The bank idea matches; checksum algorithm not compared [I] |
| Image processing | COLOR/HSL tables. CMIO P/T blocks (tags 0635/0636) with T encoded as `C[p]=P[p]^P[p-1]^K[p]` [X docs/color/pen-f/ORF_METADATA.md:9-14, 34-38]. MONO grain = xorshift PRNG, separate from Grainy Film [X GRAIN.md:26-27, 61-63] | No COLOR/HSL profile exists (E-PM2 predates it). Grainy Film uses the stored block-2 texture [V map §2]. ORF CMIO blob 0x7E86DD80, 76,608 B, high entropy [V 14d] | **Differ by model**; no conflict. The CMIO XOR-chain is a lead for decoding our blob [I] |
| USB update ops | 911c mode, 9119 split transfer, 9121 FirmwareCheck, **9122 CheckStatus (poll)**, 9123 UpdateInitiate [X USB_UPDATE.md:9-17] | Same op set. Our map calls 0x9122 "GetFirmwareUpdateMode OK/NG"; it reads state 0xA06E0300 (0/1/2 → 2/3/4) [V 08 l.103, 145] | **Disagree on the name only.** Their name comes from host code. The E-PM2 behaviour (state → status word) fits a status poll, so **they are right**: rename it CheckStatus [I] |
| USB transport | PTP-style vendor ops carried in Olympus SCSI commands: C0 command, C1 data, C3 response [X USB_UPDATE.md:23-27] | Overlay B PC_PTP ("OLPTP") dispatches on 192/193/194/195/196 (0xC0–0xC4) at 0x7F098533 in fn 0x7F0984A6. String `olptp_c0_idle_vender_queue_write` feeds the TPC queue [V disasm, 16d rows] | **Agree.** This is new for our map and a lead for our 08/10e "X3C / TPC requester" question |
| Recovery | Recovery shown only from the states tested. No rollback copy. The OK+power entry is unknown [X RECOVERY.md:48-58, 78-83] | `flashing.md` says recovery is "proven" from one text-patch state [V] | **Agree in substance**; our wording claims more than the evidence shows (see §3) |

### 2.2 What they know that our map lacks, checked in our bytes

1. **Stock SD parameter-CSV override** [X docs/protocols/pen-f/WIFI_DEBUG.md:11-21, 49-55: `PARAMDT/CP??????CSV`, RAM-only override, no nonvolatile write found].
   - **E-PM2:** the same path exists. 0x7E5B108F runs during the dcfnum MOUNT. If a `CP??????CSV` file exists in `PARAMDT`, it calls `prm clear 1` and then prm process op 2 = CSV load (0x7E457F63 → 0x7E4564D8). That code is at 0x7E5B113D–0x7E5B116D [V disasm]. The getter consults the CSV index first while 0x603A0E34 ≠ 0 [V 07 §1.1].
   - **Format differs:** our parser row says `TAG,count,values` [V 16c row 0x7E456667]; PEN-F uses `label,ID,count,value` [X]. Check before any use.
   - **Gap:** our map lists the function only as a probable DCF helper (I). It does not connect it to a no-patch way to change settings.
   - **Does it persist?** Whether an overridden value can reach a flash bank through a later prm save is **not checked** [I].
2. **OLPTP SCSI transport (C0–C4)** and the **CheckStatus** name for 0x9122. See the table.
3. **The flash "dump" is not read-only** on the PEN-F. A page reader with an ECC-like threshold can replace a 128 KiB block and rewrite the mapping tables. It also bypasses the flash lock [X docs/boot/pen-f/FLASH_READERS.md:1-7, 21-32, 52-59].
   - **E-PM2:** it has the same family: a BML/STL library (0x7E421C93–0x7E425F43), the `flash dump`/`tnan` shell commands, and SYSFMEM modes [V 01 §5–6].
   - Whether our `flash dump` path can replace blocks was **not traced**. Treat it as possibly writing until checked [I].
4. **Flash-access guard.** PEN-F has a guard mode word that permits mode 0x1xx or a write to 0x40120000 [X tools/penf_flash_guard_probe.py:20-29].
   - **E-PM2:** 0x7E44F197 brackets every BML operation with 0x7E4C8E40(code)…0x7E4C8E40(0). The codes are 0x101 for modes 1/6/8 and 0x204–0x208 for the others [V disasm]. 0x7E4C8E40 sets the u16 at 0x600011E0 [V 13f]. The NMI handler `FLASH_ACCESS_GARD` (string at 0x7E474A22) exists [V].
   - **Not yet linked:** the rule that connects these two is not mapped. It is probably the same kind of guard [I].
5. **Unchecked destination.** Cmdada reports, from simulation only, that an E-M10 package section aimed at 0x40000000 is written to the first boot stage [X docs/boot/e-m10/RECOVERY.md:35-46].
   - **E-PM2:** the worker passes each section's `start_adrs` unchecked through 0x7E45DB37 → 0x7E44F197 (mode 1) → 0x7E4509C0. None of those three compares the address [V disasm]. Lower BML layers were not read.
   - **Risk:** a crafted `E101` section aimed at 0x40000000–0x4005FFFF could overwrite the boot area [I].
6. **Boot chain context.** E-M10: a mask ROM, then a first stage at logical 0x40000000, then a second stage with its own `[firmup]`, then main [X e-m10/RECOVERY.md:15-22].
   - **E-PM2 evidence:** the `S101????BIN` type writes 0x60000 bytes to 0x80000000 with only a word sum. The `"BOOT"` magic check is skipped in mode 0 (0x7E880B73: `mov 0x80000000,a0`, `mov 1,d1`) [V disasm, 02 §1.3/1.5]. `flash addr` puts `adj` at 0x40060000 [V 01 §6], so the boot area is 0x40000000–0x4005FFFF [I].
   - BML calls forward to code at 0x7E401400, below block 0 [V 01 §5]. That fits a resident earlier stage [I].
   - **Differs from E-M10/PEN-F:** they use write mode `0109` for boot writes [X e-m10/RECOVERY.md:48-50]; the E-PM2 uses ordinary mode 1 [V].
7. **MAC context instructions.** The GNU simulator needed `getchx/getclx/putcx` added [X tools/mn103_strict.patch:271-298]. The E-PM2 kernel uses `getclx`/`getchx` at 0x7E4300AA/0x7E4300B2 [V disasm]. Any E-PM2 emulation needs them.
8. **Alignment blind spot.** The GNU simulator accepts unaligned u32/u16 accesses. A 2-byte-aligned structure restarted a real PEN-F [X docs/safety/VALIDATION.md:23-35; docs/tooling/EMULATOR.md:109-114]. This applies to any future E-PM2 code patch [I].
9. **FF gaps are not free space.** A gap must lie inside a section's real load and must not overlap a copied init image [X docs/safety/CODE_SPACE.md:3-21].
   - **E-PM2:** the `.data` image 0x7E8DA000 → RAM 0x602A9B40 and the segment loads are already mapped [V 01 §2, 14d §1].
   - **Not yet done:** none of our map's padding runs is qualified as code space.

## 3. Recovery and safety knowledge (compared with `docs/flashing.md`)

**What our evidence shows:**
- **Flashes so far:** two stock reflashes, the 52-byte text patch, its recovery, and the film-portra look patch [V camera-log.md]. The brief says "nothing flashed"; the camera log shows otherwise.
- **Where the OK+power path lives (E-PM2):**
  - Usr0 runs in the boot task and starts **56 tasks** before the update branch: 30 before the decision call at 0x7E5045F4 and 26 after it, up to the branch at 0x7E504A59 [V disasm, 58 `OlyTaSt` sites].
  - FIRMUP_CLI/SRV and the LED/result code are segment-1 code (0x7E5434EA–0x7E544A9F, 0x7E8808C0–0x7E880F43) [V 02].
  - The card path uses only the LED (arg 3). It draws no GUI [V 02 §1.8].
  - Segments 2/3 (C++ app, GUI, 0x7E8F5800–0x7F034000) and overlays A/B are loaded only by Usr1 (USTART1, task 0x52). Usr1 does not start on the update path [V 01 §2; 0x7E43EA1C = 0x52].
- **Consequences:**
  - A patch confined to segments 2/3 cannot run before the OK+power decision, so by itself it should not block SD recovery [I]. This matches the PEN-F result that the updater runs with the patched regions inaccessible [X RECOVERY.md:88-91].
  - A patch in the reset/kernel code, segment 1 (including its rodata, where the film-portra edits sit) or the `.data` image runs before that decision. It can disable recovery [I].
  - Recovery after a broken block 0 depends on an earlier boot stage that we have not mapped [I].

**Their discipline that we should adopt** [X README.md:27-29; provenance/README.md:3-4, 28-30; VALIDATION.md:7-16, 50-53; CONTRIBUTING.md:28-29]:
- Pin the exact SHA-256 of every input, not just the version label.
- Treat "checksum OK", "emulator OK" and "camera OK" as different claims.
- Say that a recovery test proves recovery only from the state tested.
- Before a flash, compare the whole stock file with the modified one. Rebuild the expected bytes independently and confirm that only the intended payload bytes and that block's checksum word differ.
- Note: our `build.py` already pins `base_sha256` and checks the expected bytes of every op [V].

**Add to `docs/flashing.md`** (wording proposals; not applied here):
1. **"What recovery covers."**
   - The OK+power path is main-firmware code in segment 1, reached after 56 task starts.
   - Recovery has been shown only from a data/text-patch state.
   - A patch to the reset code, kernel, segment 1 or `.data` can remove recovery.
   - There is no known independent rescue loader.
2. **Card hazards beyond E100.**
   - `S101/S100????BIN` writes the boot area with only a word sum. It is searched first.
   - `DATE????BIN`/`PICTURE1JPG` writes flash 0x40140000 with no checksum [V 02 §1.3].
   - `E` sections are written to their header `start_adrs` with no range check in the worker [V].
   - The rule "only one file in `DCOLYMP`" covers all of these. Say why.
3. **Pre-flash preflight.**
   - Model bytes `10 10` in all 5 sections, including the `OM` section.
   - header[0:28] = trailer[0:28], and header[28:32] = 0.
   - `start_adrs` and length equal stock for every section.
   - Only the intended block differs.
   - The `OM` section is byte-identical to stock.
4. **Do not use `flash dump`/`tnan`** from a debug shell until the E-PM2 read path is shown to contain no block replacement (the PEN-F reader can rewrite blocks).

## 4. Tools we could use

| Tool | Licence | What it would give us | Running external code? |
|---|---|---|---|
| `tools/oly_container.py` (decoder, checksum, round trip) | Apache-2.0 [X file header] | A second decoder. It **fails on our `OM` section** [I]; we already match its decode via the E-PL5 hashes [V] | Yes if run → needs approval. Better: copy its *checks* (header/trailer, zero field, model, round trip, refuse output in the firmware dir) into our own `oetool.py`. That is reimplementation; no external code runs |
| `penf_repack_preflight.py` method | Apache-2.0 | Builds the expected bytes independently and asserts the stale checksum is rejected | Its code pins PEN-F hashes and imports the emulator. Reuse the **method** in our own code |
| GNU MN103 simulator + `mn103_strict.patch`, `mn103_runner.c`, `prepare_mn103_sim.py` | **GPL-3.0-or-later** (patch/runner/prep), on GNU binutils-gdb (GPL-3.0) [X RIGHTS-AND-PROVENANCE.md:11-17]; builder script Apache-2.0 | Native runs of E-PM2 routines, e.g. our checksum 0x7E54337D, worker modes, the CSV parser. That would turn V-static claims into executed ones | **Yes:** a C build of binutils-gdb and their harness → needs user approval. We would also write our own E-PM2 harness. Every `penf_*` probe pins PEN-F hashes and addresses, so none runs on E-PM2 as is |
| IDA 4.9 Free + historical `mn103.w32` module | Third-party: IDA freeware licence; the module is from pentax-hack.info with its own terms [X docs/tooling/ida/README.md:140-157] | A second disassembler only. They found it agrees with GNU on 143 instructions | **Yes:** a Windows binary under Wine → needs approval. Low value: our objdump already decodes AM33, including `getclx` |
| `value-pixels.txt` | DejaVu/Bitstream notice [X RIGHTS:18-20] | Not relevant | — |

Reading their docs and implementing the checks ourselves needs no approval. Copying Apache-2.0 code needs the licence text, the copyright notice and a statement of changes. Their firmware-derived fragments are outside the grant [X RIGHTS:25-30].

## 5. Method: how they separate evidence, compared with our V/I

| Aspect | oly_fw_analysis | Our map |
|---|---|---|
| Evidence classes | S static, N bounded native execution, C connected replay, then physical camera and desktop renderer kept apart [X FUNCTION_MAP.md:7; docs/README.md:31-34] | V (read in code or bytes) / I (inferred). Camera results are kept in `camera-log.md` |
| Assumptions | Every execution result lists its modeled hardware and stops on unknown access. "A passing probe proves its scoped assertions under the named assumptions" [X REPRODUCING.md:60-63; EMULATOR.md:57-62] | No execution, so we have no modeled assumptions. V covers both "byte read" and "control-flow traced" |
| Input identity | Every probe pins sha256. Disassembly windows record address + image hash [X provenance/README.md] | `SHA256SUMS` and `base_sha256` in patch specs. **The map and `fwmap.py` do not pin the block-0 hash** (`1b7c4bb1…`) [V grep] |
| Absence claims | "A missing direct call does not rule out computed dispatch" [X RECOVERY.md:26-29] | Our audits found that absence/completeness claims fail most often (A9, A11) [V CONFIDENCE.md] — the same lesson |
| Review | Native negative controls, poisoned memory, exact replay comparison [X VALIDATION.md:37-48] | Blind coverage samples, seeded claim audits, boundary lint, 0-wrong criteria [V CONFIDENCE.md]. **Stronger on review breadth; weaker on executed evidence** |

**Proposal:**
- Keep V/I.
- Add sub-tags where they matter: **V-s** static trace, **V-x** executed (if we ever approve an emulator), **V-cam** observed on the camera.
- Make every absence claim state its search scope.
- Put the block-0 sha256 in the `firmware-map.md` header, and have `fwmap.py`/`disasm.py` refuse any other image.

## 6. Recommendations (ranked by value, then safety, then effort)

| # | Action | Value / risk / effort | Approval needed? |
|---|---|---|---|
| 1 | Add the §3 "What recovery covers" and card-hazard text to `docs/flashing.md`; reword "Proves recovery" | High / none / small | No (docs; the user may want to review the wording) |
| 2 | Harden our own `oetool.py`: parse the `OM` section as kind `M`; check header/trailer, zero field and model; add a full preflight diff against stock | High / none / small | No (our code) |
| 3 | Pin the block-0 hash in the map and tools | Medium / none / tiny | No |
| 4 | Map fixes: OE = maker+kind; kind u16 = sub-kind + scramble flag; `OM` = M section; 0x9122 = CheckStatus; OLPTP SCSI C0–C4; PARAMDT CSV path into §3 "Platform, debug and service" | Medium / none / small | No |
| 5 | Static traces: the 0x600011E0 guard and `FLASH_ACCESS_GARD` rule; lower BML destination checks; `flash dump`/`tnan` block replacement; whether a CSV override can be persisted; poweron-factor values | High for safety / none / medium | No (static mapping) |
| 6 | Try decoding the CMIO blob with their T-encoding formula (needs K or a known plaintext) | Low–medium / none / medium | No |
| 7 | Build the GNU MN103 simulator and write an E-PM2 harness for the updater/checksum/CSV parser | High for V-x evidence / low / large | **Yes:** running and building external (GPL) code |
| 8 | Camera test of a PARAMDT CSV override (RAM-only on PEN-F; unverified on E-PM2) | Medium / medium (settings persistence unknown) / small | **Yes:** a camera action. Do it only after #5 |
| 9 | A main-only E-PM2 package (block 0 only) to shorten the write | Low / medium / small | **Yes:** a patch build and a flash |
| 10 | IDA 4.9 + MN103 module | Low / low / medium | **Yes:** a third-party binary under Wine |

## 7. Licence notes

- **Apache-2.0** covers the original docs, metadata and 134 tools [X RIGHTS:3-7; SPDX headers].
  - Reuse needs the LICENSE copy, the copyright line ("Copyright 2026 fishku") and a statement of changes.
  - There is no NOTICE file [V file list].
- **GPL-3.0-or-later** covers `tools/mn103_runner.c`, `tools/mn103_strict.patch` and `tools/prepare_mn103_sim.py`. Distributing a built engine brings GPL source obligations [X RIGHTS:11-17].
- **Excluded:** vendor-derived fragments, release BINs, the IDA/MN103 module and third-party patchers are not covered by Apache [X RIGHTS:25-36].
- **Our plan:** reimplement checks (§6 #2) in our own code from the documented rules. Copy no source.

## 8. Open questions

1. Which physical key/wake causes map to `poweron_factor` table values 12/0x01000001/0x01000002 (0x7E73522C)? Who clears 0x602A9B54?
2. Does any layer below 0x7E4509C0, or the `FLASH_ACCESS_GARD` NMI, reject writes to 0x80000000–0x8005FFFF from an `E` section?
3. What is at 0x7E401400? Does the E-PM2 have an earlier stage with its own card updater, as the E-M10 does?
4. Is our `flash dump`/`tnan ndread` path free of the block-replacement branch? Does it take the flash lock?
5. Exact E-PM2 CSV syntax (is there a label field?). Does an override survive a prm save/restart? Are there debug-enable tags (like F971) that the E-PM2 reads at mount or boot?
6. Does the E-PM2 updater act on the 0x3203 readback error from every write?
7. Is our CMIO blob encoded with the PEN-F XOR chain, and with which key?
