# Caduceus review 01: method, tooling and safety practices

Date 2026-11-11. Sources: `caduceus-ep7` (E-P7 1.1) and `caduceus-om3` (OM-3 1.1), read as text only; nothing from
them was run. E-PM2 checks used our block 0 (`build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin`), the stock BIN,
`tools/disasm.py` and our map. Paths below are relative to each repository's root. "EP7:" = `caduceus-ep7/`, "OM3:" =
`caduceus-om3/`.

Labels: **[V]** read in our E-PM2 bytes or our map; **[X]** stated by an external source (file:line); **[I]** inference.

**Status correction [V]:** the brief says nothing has been flashed. `docs/camera-log.md` records four flashes on
2026-11-08 and 2026-11-11: two stock reflashes and two modified, data-only builds (a menu label, and the Portra look
tables). There are no code patches yet: every op in `patches/*.json` is a `bytes` or `utf16-replace-all` data op.

## 1. What the source is and how it works

### 1.1 Build pipeline (E-P7)

- **No OM firmware in the repo.** A release is an edit list plus hashes. `caduceus.py` downloads or takes the stock
  file, checks its SHA-256, applies `releases/<v>/edits.json` and writes card files only if every output hash matches
  `releases/<v>/SHA256SUMS` [X EP7:caduceus.py:4-8, 267-276].
- **Edit-list format** [X EP7:tools/build_package.py:8-12]: `{"components": ["0x100", ...], "edits": [{"kind",
  "addr" (CPU address for main, or "off:0x.."), "expect" hex, "new" hex, "why", "source"}]}`. v0.31d has 446 edits,
  34,865 changed bytes, in components 0x100 and 0x101 [X EP7:releases/v0.31d/build.json].
- **Checks before anything is written** [X EP7:caduceus.py:92-178; tools/build_package.py:14-21]:
  - stock SHA-256 exact; parse plus exact round trip; per block: `OE`, one model id, size % 16,
    header[0:28] == trailer[0:28], checksum 0;
  - per edit: `expect` == stock bytes, equal lengths, in range, no overlap;
  - output re-parsed; untouched components byte-identical; changed-byte count == sum of the edits' changed bytes;
    restore = the exact stock byte slices of the same components.
  Output goes to a temporary folder that is then renamed into place. The card copy is `fsync`ed and re-hashed on the card
  [X EP7:caduceus.py:278-292, 430-482].
- **Component-selective packages.** Only the listed components go in the package. The E-P7 updater accepts a
  main-only package [X EP7:docs/SD_UPDATE.md:153]. Developer outputs are named `*.pkg.bin` so they cannot be loaded by
  name; renaming to `DCOLYMP/` is a separate manual step [X EP7:tools/build_package.py:4-6].
- **Free-space proof**, two kinds:
  1. **FF tail inside a loaded section.** Section bounds come from the loader's descriptor table (0x60027068) and its
     end-address getter (0x60045786), not from FF runs. The tool then scans the whole image for literal references
     (runtime, uncached +0x40000000 and logical flash aliases) and for PC-relative branches at every byte offset. It
     says itself that static absence does not rule out computed or DMA access
     [X EP7:tools/ep7_code_space.py:1-12, 33-96]. Claims keep 16-byte FF guard bands on each side
     [X EP7:docs/CODE_SPACE_MAP.md:10, 15].
  2. **Dead tables.** EVF gamma tables on a body with no EVF. The only reference is a step-table word, and scan false
     positives are pinned in `build.py` [X EP7:docs/CODE_SPACE_MAP.md:35, 48, 65].
  `CODE_SPACE_MAP.md` is the single allocation table: "every new patch must claim a range here first"
  [X EP7:docs/CODE_SPACE_MAP.md:3].
- **OM-3 differences** [X OM3:firmware/patch.py:158-184; firmware/build.py:232-252, 316-321]: the release
  `patch.json` holds only new byte runs, with no per-run `expect`; safety comes from SHA-256 of the input, of decoded
  main before and after, and of the result. The output is the full package; restore = the official file renamed.
  `build.py` asserts stock bytes at every hook, the exact count of every re-pointed word, and that each code region is
  all-FF with a non-FF byte just before it. It also **moved section 6's loader end word** to load 64 KiB and then
  256 KiB more, each step camera-probed (GX1–GX3) [X OM3:research/NOTES.md:795-840; CLAUDE.md:63-70].

**Container and checksum: theirs and ours.**

| Item | EP7 `caduceus.py` | OM3 `patch.py` | Ours `oetool.py` / `build.py` |
|---|---|---|---|
| Decode | LANES permutation + XOR 0xFF [X :64-79] | same [X :31-52] | same [V oetool.py:18-33] |
| Checksum | word sum of header + decoded + trailer = 0; resealed in trailer +28 | same | same [V oetool.py:36-68] |
| Bad checksum or header/trailer mismatch | refuses | refuses | `parse` records `ok=False`; `build` and `patch` still write a file. No header/trailer or model check [V oetool.py:40-54, 57-68] |
| Data after the OE blocks | refused | refused | kept as an opaque tail, its checksum not checked [V] |
| Output | changed components only | full package | full file: 4 blocks + `OM` tail [V build.py:120-138] |
| Per-edit stock check | `expect` | none (whole-main hashes) | `expect` for `bytes`; count for `utf16` [V build.py:88-114] |
| Output hash | must equal the release | must equal the release | checked only for a single spec with `expected_sha256` [V build.py:141-144] |
| Restore file | stock slices of the same components | official file | the stock BIN itself (proven 2026-11-08 [V camera-log]) |

### 1.2 Runtime design

- **What loads from the card, and when.**
  - **E-P7:** data only (`EP7MOD/BUNDLES.BIN`, `LOOKS.BIN`, `MOVIE.BIN`, `AP.BIN`), at the first shutter half-press,
    never at power-on [X EP7:README.md:334-336]. A jmp stub in the HLS_EVENT trigger tracker (0x602c805f) gates on all
    sections loaded, the task id and a mounted card, then does malloc(1024), fopen and size/CRC/range checks; every
    miss runs stock code [X EP7:docs/SD_V2_CRASH.md:28-75; docs/FIRMWARE_GUIDE.md:460, 527].
  - **OM-3:** code as well. `GUIDES.BIN` ends with a relocatable code block, tagged from the firmware image and
    relocated into a heap buffer [X OM3:docs/FORMATS.md:75-80]. v0.26.2–v0.27 loaded at power-on via a polling task
    [X OM3:docs/SD_LOADER.md:9-23]; **v0.27.1 removed that** after sporadic freezes at switch-on (battery pull needed)
    [X OM3:releases/v0.27.1/NOTES.md:3-8]. `EDITS.BIN` is a camera-written data file (edits per film), CRC-checked,
    ignored if bad; card writes go to `*.NEW`, are read back, then replace the file [X OM3:docs/FORMATS.md:37, 42-58].
- **The "log hook" and the debug log.** In Caduceus, "log hook" means the **log-video** hook `vlog_hook`
  (0x60210c90), not logging [X EP7:docs/CODE_SPACE_MAP.md:16; README.md:296-297]. E-P7 diagnostics were temporary card
  files (`LOGDBG.TXT`, `GRAIND.BIN`) or Firmware-screen records, removed before release
  [X EP7:docs/FIRMWARE_GUIDE.md:553-566].
  - OM-3 v0.27 ships an opt-in log: if `OM3MOD/DEBUG.TXT` exists, each shutter event rewrites `OM3MOD/CADLOG.TXT`
    (build, loaded files, last save, last 32 events) [X OM3:debug-log/README.md:59-71; firmware/src/editor.s:8634-8639].
- **"Runtime state only in heap memory the loader allocates"** [X EP7:README.md:319-320].
  - Rule: no absolute stores into the loaded image; state goes in the heap block P or proven `.bss` padding
    (0x622cbcc2); the builds run a store audit and the verifiers map the image read-only
    [X EP7:docs/FIRMWARE_GUIDE.md:517-519]. Origin: test 7, where a byte store into section-3 RAM crashed the camera at
    the first half-press [X EP7:docs/FIRMWARE_GUIDE.md:539].
  - OM-3 does not keep the rule strictly: its debug-log variables live in the loaded `ext12` region
    [X OM3:firmware/src/editor.s:8637-8638].
- **How patches hook stock code** [X EP7:docs/FIRMWARE_GUIDE.md:501-527]:
  - **rel32 call retarget:** the stub runs on the caller's frame and tail-jumps to the old target on a miss.
  - **jmp stub:** at least 5 bytes of whole instructions become `jmp d32`; the stub replays the displaced instructions
    exactly, then jumps back. This is the trampoline form.
  - **Data-only:** re-point a vtable word, record word, `.data` init word or list pointer.
  - **Chaining:** re-point a word that is already ours and fall through to its previous owner.
  - Constraints, enforced by the builds: stock `expect` bytes at every site; no branch into bytes +1..+N−1 of a stub
    site; MDR and PSW preserved; no `mul`/`div`/`setlb` and no `0xfb`-prefixed forms (they misbehaved on the OM-3
    camera); `.balign` on all data; a hook calls only code in an already-loaded section; every miss path is stock.

### 1.3 Testing

- **E-P7 (function-level).** fishcu's MN103 engine runs the patched code taken from the built package, beside stock
  code, on synthetic jobs and contexts.
  - Pass criteria: the run returns to the caller; sp, callee-saved registers, MDR, PSW and the live stack equal stock;
    the output bytes equal stock except the intended fields; every changed byte lies inside an edit span.
  - The package must decode to exactly the emulated image, and the restore file to exactly stock
    [X EP7:tools/ep7_verify_package.py:1-10, 46-90; README.md:316-318; docs/FIRMWARE_GUIDE.md:516].
  - The SD updater's own validator was also run on synthetic containers (19/19)
    [X EP7:docs/SD_UPDATE.md:8-13].
- **OM-3 (whole firmware).** om-emu "play sessions": UI navigation, a card image, screenshots, in-session native calls
  [X OM3:tools/emulator/session_autoload.mjs:1-30].
- **Blind spots both projects found:** no alignment faults, screen stack, DMA or cache, or ISP pixels
  [X EP7:docs/FIRMWARE_GUIDE.md:553-556]. And the emulator maps the gaps between sections, but **the camera does not
  load them**: code placed in such a gap ran in om-emu but was absent on the camera
  [X OM3:research/NOTES.md:795-806; CLAUDE.md:63-66].

### 1.4 Recovery (E-P7 updater)

- **Trigger:** hold OK at power-on, file `DCOLYMP/E1429999.BIN`. LED steady while writing, then about 2 Hz blink = done
  [X EP7:README.md:328-330].
- **LED misread:** code analysis first read the 2 Hz blink as failure. A harmless 7-byte OSD probe corrected it
  [X EP7:docs/SD_REJECT.md:91-99; WORKLOG.md:184-185; docs/FIRMWARE_GUIDE.md lesson 13].
- **Corrupt files:** every component is validated before the first write; a corrupt file gives 0x3211 and 0 writes
  (emulator) [X EP7:docs/SD_UPDATE.md:155]. A zero-write trigger test with a checksum-flipped copy was the first camera
  step [X EP7:WORKLOG.md:159-161].
- **How writes work:** no block skip (each component is erased and reprogrammed in full); read-back without a
  compare; no rollback; USR (main) is written last [X EP7:docs/SD_UPDATE.md:39-51, 182-221].
- **Bootloop recovered:** test 3 bootlooped. Battery out, then OK + power with the stock main restore → stock again
  [X EP7:WORKLOG.md:190].
- **Recovery reach:** they listed the code the SD updater depends on and showed which faults keep it reachable
  [X EP7:docs/SD_UPDATE.md:237-267].

### 1.5 Porting and CI

- **`port_sigmatch.py`** looks for each edit's `expect` bytes plus 32/16/8 bytes of context in the target image and
  classifies it same / shifted / ambiguous / absent. PC-relative operands are not masked, so it undercounts. A match
  does not show the edit is correct [X EP7:tools/port_sigmatch.py:1-15, 25-41].
- **E-M5 III result:** 106 of 294 v0.20 edits = 36 %. Recording limit and LCD tint match; the SD loader and the log
  hook do not [X EP7:docs/PORT_EM5III.md, "Signature match"; README.md:296-297]. Other methods: shape match, string
  anchors, table shapes [X EP7:docs/FIRMWARE_GUIDE.md:621-646].
- **Test ladder on a new body:** (1) the official file, (2) a stock restore round trip, (3) a text change, (4) a data
  edit, (5) a do-nothing hook, (6) features one at a time [X EP7:docs/FIRMWARE_GUIDE.md:659-668].
- **CI:** EP7 `.github/workflows/pages.yml` only builds, tests and deploys the web app; OM3
  `.github/workflows/releases.yml` only publishes release folders. **Neither CI runs firmware checks**: the stock
  firmware cannot be in CI [X].

## 2. What applies to the E-PM2

### 2.1 SD updater: E-P7 against E-PM2

| Item | E-P7 [X] | E-PM2 |
|---|---|---|
| Trigger | OK + power | OK + power, 4 times on the camera [V camera-log]. In code: 0x7E544A6F, poweron_factor table 0x7E73522C; which key gives which factor is open [V map 02 §1.1] |
| Where the updater lives | section 6; FIRMUP_SRV started late (USRSTART5) [X SD_UPDATE.md:251] | block 0, loaded by the boot task. Usr0 starts about 60 tasks, including FIRMUP_SRV, then decides firmup or normal boot at 0x7E504A59 [V 01 §2, 02 §1.1] |
| Validate before write | all components first | all sections first ("writes are done after all sections pass") [V 02 §1.6] |
| Model id | 0x1420 only | 0x1010, **and 0x1000 for kind `E`** [V 0x7E543ED8/0x7E543EE9] |
| Version check | none | none [V 02 §1.4] |
| Duplicate kinds | last `E` copy wins | rejected, error 0x3321 [V 02 §1.4] |
| Write order | ... USR last | LENS, FLASH, BURE, LANG, ..., OSD, USR last [V 02 §1.6] |
| LED codes | 250 success, 100 fail; 2 Hz = success on the camera | same codes, 250 and 100 [V 02 §1.8]. "Solid, then blinking" seen only with good flashes [V camera-log]. **The failure blink has never been seen.** |
| Hazard files | S142 goes through the same validator | `S101/S100????BIN` → word sum only, write to the boot block 0x80000000; `DATE????BIN` → flash 0x40140000 with no checksum [V 02 §1.3, §1.5] |

So these E-P7 lessons carry over with E-PM2 evidence: validation before any write, no version check, USR last. The
bootloop recovery does **not** carry over yet (§2.4).

### 2.2 Our flashes write more than they change [V]

- The stock BIN has five sections: four `OE` blocks and, at 0x2940000, header `4f 4d 10 10` = maker `O`, fw_kind
  `M` (BURE, the stabiliser), model 0x1010, flag 1. The worker sends BURE to the stabiliser controller (ERASE → WRITE →
  VERIFY over serial) when stab type == 1 [V 02 §1.4–1.6]. So every full-file flash we made re-sent the IS
  controller's firmware and rewrote blocks 1–3 [I: assumes stab type is 1 on this body].
- Caduceus's component-selective package (only the changed block) avoids this. Whether the E-PM2 worker accepts a
  subset is **not traced**. No required-set check is recorded in our map [I: likely accepted].

### 2.3 Free space: the 0xFF padding at 0x7E880F5C–0x7E8D9FFF

- **E-PM2 has no single section table.** Loading is done by separate copy calls [V]:

| Copy | Runtime range | FF tail inside the copy | Source |
|---|---|---|---|
| reset code, call 0x7E421228 | 0x7E430000–0x7E4C9800 | 0x7E4C90CA–0x7E4C97FF, 1,846 B | [V disasm: src 0x402CF000, end 0x7E4C9800] |
| boot task, call 0x7E44A080 | 0x7E4FE000–0x7E881000 | **0x7E880F5C–0x7E880FFF, 164 B** | [V disasm: end immediate at 0x7E44A076; map 01 §2] |
| reset code `.data`, call 0x7E42124D | from 0x7E8DA000 (size from 0x604DA484) | — | [V map 14d §3.8] |
| Usr1 | 0x7E8F5800–0x7ECB1000 | 0x7ECB0888–0x7ECB0FFF, 1,912 B | [V map 01 table; own byte scan] |
| Usr1 | 0x7ECCB800–0x7F034000 | 0x7F033B7C–0x7F033FFF, 1,156 B | [V] |
| Usr1 | 0x7F100000–0x7F119000 | 0x7F118F64–0x7F118FFF, 156 B | [V] |
| overlays A, B (on demand) | 0x7F05C000–0x7F06B000, 0x7F080000–0x7F0EB800 | 574 B, 892 B | [V] |

- **Of the 364,708-byte padding, only 164 bytes are inside any copy we know.** 0x7E881000–0x7E8D9FFF (364,544 B) is
  in the file but no known load copies it into RAM [V for the known loads; I that no other load exists]. This is the
  OM-3 "sliders" trap: code there would be absent on the camera. Do not plan code there.
- **The padding is not all 0xFF.** 0x7E881000–0x7E881002 = `de 00 00` [V]. The map row "0xFF 0x7E880F5C–0x7E8D9FFF"
  should be corrected.
- **References** (own unaligned abs32 scan over block 0): no word points into the 164 in-load bytes. 126 runtime and
  180 uncached (0xBE…) hits point into the gap; the only real instruction is the copy-end immediate at 0x7E44A076 [V].
  The rest look like instruction bytes or float data (0xBE8A8000 ×64 = a float table at 0x7F0284F4) [V spot check; I].
- **We have not verified that the 164 bytes are never read** (computed addresses, DMA). That needs a GAPTEST-style
  camera probe, as OM-3 did [X OM3:research/NOTES.md:795-806].
- **The dead-EVF-table trick does not transfer:** the E-PM2 drives the VF-2/3/4 EVF [V docs/firmware-map.md:171].
- **Usable code space today:** about 5.3 KB of FF tails inside copies, plus heap buffers. Each tail must stay within
  load-order rules: Usr1 and overlay code is not present during Usr0 or the firmup path [I].

### 2.4 Recovery reach on the E-PM2 [I, from V control flow]

- **The card updater is part of block 0.** It runs from Usr0, which first starts about 60 tasks (LENS_MAIN, UI,
  DISPLAY, BC_MAIN, FILECLBK, ...). A patch in code those starts run, or in the kernel, SYSFMEM, FILECLBK, the flash
  driver or FIRMUP_*, can make SD recovery impossible.
- **Code reached only after USTART1** (normal UI, shooting) is outside that path. A crash there should still let
  OK + power reflash stock, as on the E-P7. This is **not proven on the E-PM2**: we have recovered only from a
  booting, modified camera [V camera-log row 3].
- **A torn write of block 0 (USR is written last) probably cannot be recovered over SD.** The E-P7 project reached the
  same conclusion [X EP7:docs/SD_UPDATE.md:332-333]. Whether the S boot block has its own recovery is unknown.
- **Our data-only patches** (look tables 0x7E75F2F0/0x7E7696B4, label strings) do not change control flow [I].

### 2.5 Runtime design and test tools on the E-PM2

- **Building blocks that exist [V map]:** heap alloc 0x7E507325 and free 0x7E507333 (13a:186); a stock `dbg` log
  module 0x7E53A981 with one 16 KiB heap block (02, BC row); the putc ring at 0xA0731828 (10f).
- **Not mapped:** a card file API patch code could call, and the event to hook for a "first half-press" loader. So an
  EP7MOD-style loader or a CADLOG-style log cannot be designed yet.
- **No emulator.** om-emu marks E101 (E-PM2) "not tried" [X om-emu:docs/model-survey.md:71; docs/ROADMAP.md:134].
  Our tools are objdump-based disassembly and `fwmap.py`. Our only end-to-end test so far is the camera-JPEG model
  comparison (camera-log row 4), which plays the role of Caduceus's "measure camera JPEGs" [V].

### 2.6 Porting

- **Anchor strings [V own count].** E-PM2 block 0 has 1 `PROFILE` string and 44 `COLORTONE` strings. Caduceus reports
  21 and 213 for the E-P7 [X EP7:docs/PORT_EM5III.md, table "What was checked"].
- **Other differences:** no Colour Profile system [I]; a different runtime base (0x7E421020 against 0x60020020)
  [V/X]; an older TruePic generation.
- **Conclusion [I]:** porting Caduceus *edits* by signature would score below the E-M5 III's 36 %; port the *methods*
  (checks, hook rules, test ladder). `port_sigmatch` cannot run here (no E-P7 image; no running their code).

## 3. Recommendations

**What to adopt, practice by practice.** "Ours" is what our tooling has today [V].

| # | Practice | Ours today | What to build | Depends on (map) |
|---|---|---|---|---|
| 1 | Strict container parse | `ok` flag only; still writes | Refuse: bad checksum, header[0:28] ≠ trailer[0:28], model ≠ 0x1010 (block 0x1000 = E-PL5), bad `OM` tail checksum | firmware-format.md |
| 2 | Per-edit stock checks | `expect` per `bytes` op; `utf16` count | Overlap check; re-parse the output; changed bytes == edit spans | — |
| 3 | Published hashes | `expected_sha256` for single specs only; `film-portra-xp` hash only in camera-log (shortened); its spec still says "NOT camera-tested" | `build.json` beside each build (input, spec and output hashes); expected hash for multi-spec builds; a test that rebuilds it | — |
| 4 | Component-selective package + stock-slice restore | full 5-section file | Option to emit only changed blocks, plus the matching stock slices | Trace the found-mask logic in worker 0x7E543DDE for subset acceptance (02 §1.4); then a camera test |
| 5 | Code-space map + checker | none (no code yet) | `CODE_SPACE.md` table; a tool that reads the copy calls (§2.3), finds in-copy FF tails and scans references through all aliases (0x7E…, 0xBE…, flash 0x402C0020+off, 0x80…) | 01 §2, 14d |
| 6 | No stores into the image | n/a | Store audit in the build; state in a heap block | 13a heap |
| 7 | Recovery-reach list | none | List of functions on the boot → Usr0 → FIRMUP path; the build refuses hook sites on it | 01 §2, 02 §1, 13f |
| 8 | Zero-write rejection test | never done | Checksum-flipped copy: learn the E-PM2 failure blink | 02 §1.5–1.8 |
| 9 | Test ladder, one feature group per flash | so far one patch per flash | Add "do-nothing hook" before the first code patch | — |
| 10 | Emulator check | none | Function-level MN103 harness (own code), or E101 support in om-emu | — |
| 11 | Opt-in debug log | none | Later: needs a card-write API | not mapped |
| 12 | CI | `.githooks/commit-msg` only | Optional: run `unittest` without firmware (tests skip) | — |

**Ranked (value ÷ risk ÷ effort).** Items 1–5 are offline tool or doc work: no approval needed beyond normal edits to
our tools.

1. **Strict parse + overlap + changed-span checks** (items 1–2). Small. It closes the gap where `build.py` would write
   a file with a bad checksum.
2. **Build manifests and pinned hashes** (item 3). Also fix the stale `film-portra-xp.json` status. Small.
3. **Recovery-reach list** (item 7). Static map work. It is a precondition for any code patch, and it states which
   faults stay recoverable.
4. **Correct the padding row and write a code-space table** (item 5). Mark 0x7E881000–0x7E8D9FFF as not loaded, and
   list the ~5.3 KB of in-copy tails as candidates.
5. **Trace subset acceptance in the worker** (item 4, static part).
6. **Zero-write rejection test** (item 8). **Needs the user's approval** (it is an updater run on the camera). The code
   says nothing is written when validation fails [V 02 §1.6]. Expected: solid for the file read, then a blink faster
   than the success blink. Battery full; stock BIN at hand.
7. **Component-selective flash** (item 4, camera part). **Needs approval** (flashing). Recommend block 1 only, with a
   one-string change: lowest risk, and it proves subset acceptance.
8. **In-copy tail probe** (GAPTEST-style), before any code goes into a tail. **Needs approval** (writing a code patch
   and flashing it).
9. **Emulator** (item 10). Large. Writing our own runner needs no approval. Running fishcu's runner or om-emu
   **needs approval** (external code), and fishcu's code is GPL-3.0 (§4).
10. **Debug log and card loader** (item 11). Only after the file API and a safe hook event are mapped. **Needs approval**
    (code patches, flashing).

## 4. Licence notes

- **Caduceus E-P7 and OM-3: Apache-2.0** [X EP7:LICENSE, NOTICE; OM3:LICENSE, NOTICE]. To reuse code: ship the
  licence, keep their NOTICE text, mark changed files. `caduceus.py` is self-contained (stdlib only) and says it is an
  independent implementation [X EP7:caduceus.py:16-22].
- **`tools/build_package.py` and the verifiers import fishcu's `oly_container` and MN103 emulator, which are
  GPL-3.0** [X EP7:NOTICE "Third-party"; tools/build_package.py:26-27]. Do not copy those imports into our tools.
- **om-emu** keeps its own licence (not checked here) [X OM3:NOTICE].
- **No reuse is needed.** Every recommendation above is a method or check we can reimplement in our own code (the
  project prefers no external code). Our `oetool.py` already implements the container independently [V].

## 5. Open questions

1. Does another load copy 0x7E881000–0x7E8D9FFF into RAM, or does something use that RAM? What are the bytes
   `de 00 00` at 0x7E881000?
2. What loads 0x7E421020–0x7E430000 (pre-main boot code?)? Does the S boot block have its own recovery path?
3. Does worker 0x7E543DDE accept a subset (block 0 only, no `OM` section)? Is stab type 0x604F3464 == 1 here?
4. Which poweron_factor values (table 0x7E73522C) does OK + power produce? Who sets 0x602A9B54?
5. What does the failure blink (LED mode 3, code 100) look like on the E-PM2, compared with success (code 250)?
6. Which tasks started by Usr0 before 0x7E504A59 run code we might patch? That list is the recovery-reach boundary.
7. Does the E-PM2 have an NMI bus guard like the E-P7's 0x99700000? Our map names `FLASH_ACCESS_GARD` and `dbgsup`
   [V map 01 §2] without ranges.
8. Is there a card file API (open/read/write) callable from patch code, and a shutter half-press event to hook for
   an EP7MOD-style loader?
