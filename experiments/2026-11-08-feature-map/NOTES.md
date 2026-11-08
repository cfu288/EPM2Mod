# Feature map of E-PM2 v1.6 block 0 (2026-11-08)

**Goal:** map and understand every feature in the main firmware. Mapping only: no patches, nothing flashed.

## Method

- `tools/fwmap.py build` makes a function database in `build/map/` (git-ignored). Current numbers, after the data-page fixes below:
  - 66,169 entries: 52,613 start at `call` targets, 13,466 more are pointer targets with a `movm` prologue, plus the task-table entries. 85 entries are "data blocks" that mark where runs of data pages start.
  - 302,507 call edges and 42,916 code→string references, plus an index of data-table pointers.
  - Pages are 4 KiB aligned to runtime addresses. A page is data if more than half its bytes are strings or more than 60% of its words look like table entries.
  - The investigator sections were written against the first database (66,094 entries). All but 3 of the 1,354 function starts they cite are still starts; the 3 are in data ranges that sections 05 and 01 themselves identify as data.
- Query commands: `fn ADDR [--dis]`, `str REGEX`, `range LO HI`, `xref ADDR`, `tasks`.
- **Link-order property (verified):** the code of each source file is contiguous, and its strings are laid out in the same order. There are zero inversions across 1,149 file-name references. So a function's strings place it in the link order, and unlabeled functions between two functions of one module belong to that module.
- Runtime base 0x7E421020 (verified: see `../2026-11-08-disassembly/NOTES.md`).

## Fixed points

- **Task names:** block-0 offset 0x4D222. Records of u16 id + char[24], 147 names, sorted by name.
- **Task configuration (CPU0):** block-0 offset 0x17CB0. Records of 28 bytes `{id, attr, exinf, entry, pri, stack size, stack}`, 147 tasks, ending with a zero record.
  - Name = `names[(id & 0x7FFF) − 1]`, checked against the boot code's `OlyTaSt(id)` labels (section 01): S_SHELL = 0x3C, MOV_EDIT = 0x84, CPUCONN = 0x8F.
  - Exceptions: 0x8085 (entry 0x7E5065EF) is DBG_OUT in the boot code but PWR_STANDBY in the name table. ID 1 (entry 0x7E44A043, attr 2 = TA_ACT) is the boot task, while the name table says DBG_OUT.
  - Proof of the layout: the only TA_ACT row is the boot task; a zero id ends the table; 0x8085 sits right before the first entry.
  - `fwmap.py tasks` prints both tables.
  - Correction history: first read at 0x17D9C, then at 0x17CBC with a `cfg_id − 2` rule. Both were one field off; section 01 found the real layout.
- **Task configuration (CPU1):** block-0 offset 0x1C490, same layout, 30 tasks. Bit 12 of the id marks CPU1, and `OlyTaSt` forwards such ids to the other core. Names come from the boot code's labels (section 01): DBG_MESS1, MOV_AVCHD/MOV_AVCHDI/MOV_ENCODE, ART_SUB, C3D_EXE, CPUCONN1, an 11-task worker pool (entry 0x7EE8FBB1), and the CPU1 boot task 0x1001.
- **Default interrupt vector table:** block-0 offset 0x4CDD0; every entry points to 0x7E44ACB0.
- **OS wrappers:** `OlyTa*` (task), `OlyEv*` (event flag), `OlyQe*` (queue), `OlySm*` (semaphore). The OS is uITRON.
- **Settings getter:** `0x7E457C75(id, a0=0, d1=index)`, with 2,168 call sites. Example: the movie routine reads id 26225 (format) and id 33105/index 7.

## Layout by region (256 KiB buckets; tags = most frequent string prefixes)

See `sections/` for each subsystem. A summary is in `../../docs/firmware-map.md` once compiled.

## Spot checks of investigator sections

Claims re-checked by hand against the disassembly before compiling them into the map.

- **02 (firmware update): the model check accepts the E-PL5 id for main packages. Confirmed.** In worker 0x7E543DDE, `fw_kind == 69` ('E') at 0x7E543E9C → maker check 0x7E506C83 → `cmp 4112` (0x1010) at 0x7E543ED8, then `cmp 4096` (0x1000) at 0x7E543EE9; either one passes. The other kinds compare with 4112 only. The accessor 0x7E506C06 reads header bytes 2–3 big-endian. Together with `E100????BIN` in the file-name table, this means the updater would **not** reject an E-PL5 main package. The camera-safety rule against E-PL5 files on the card is therefore a needed protection.
- **02: the descramble matches `tools/oetool.py`.** The per-word byte order in the section equals LANES (1,3,0,2 | 6,4,7,5 | 11,10,9,8 | 13,14,12,15) followed by NOT of every word, which is the XOR 0xFF that oetool applies.
- **03 (camera core): CAM_MAIN is an empty task. Confirmed:** its entry 0x7E62970B is a single `retf [],0`. The task table really starts 3 rows earlier than first assumed, at 0x17CBC. Confirmed; `fwmap.py tasks` is fixed.
- **03: `udfu01 N,reg` behaves as multiply-by-N.** Ring indexing in 0x7E45F14D uses `udfu01 12,d1` with 12-byte entries. This fits the ×30 and ×600 reading in the movie time-limit routine; that reading is still not proven there.
- **06 (app layer): the picture database is stubbed. Confirmed for `api_oldb_dummy_Get_DB_Existence`** (0x7E682EC3): `mov 15,d0`, load the name string, call the logger 0x7E678422, return 1. Nothing else.
- **Correction to the briefs:** the E-PM2 has **no accessory port**, so the PENPAL (Bluetooth) and VF-2/VF-3 code paths are probably dormant on this body. This comes from product knowledge, not from the firmware; what gates them in code is still open.
- **04 (movie): where the time limit stops recording. Confirmed.** 0x7E6EE006 (called each frame from 0x7E6EE9BC, which the QT/AVCHD encode paths call): if the flag at 0x605B1FA2 == 1 and the frame count (96,ctx) ≥ 30 and the limit (40,ctx) ≤ count − 15, it sets state 5, clears the recording flags, logs `[AVCHD] APPEVENT RECMOVIE_TIME_LIMIT` and posts event 0x04070026. The stop fires 15 frames after the limit. The log tag says AVCHD, but the function is shared.
- **04: the time-limit units are settled.** The rates are bitrate/4096 (512-byte sectors per second). The MOV overhead of 375 sectors/s × 512 = 192,000 B/s, which is exactly 48 kHz × 2 channels × 16-bit PCM. This replaces the "inferred" units in `../2026-11-08-disassembly/NOTES.md`.
- **05 (Bluetooth): the BT gate is a hardware input. Confirmed.** 0x7E91367A (22 callers in the BT code) calls the status reader 0x7E509CA3 with signal 5897 (0x1709) and returns 1 only if the signal reads 0. That is an active-low input, consistent with an accessory-detect pin. On a body with no accessory port the stack would never start (inferred: the pin level on an E-PM2 board is not known).
- **08 (libraries): 0x7EEE1020–0x7F021020 is read-only data, not code. Confirmed:** it disassembles as `break`/`clr`/`movbu (0x0)` noise, and 1,337 "functions" plus 1,644 call edges from it were false. Fix: `fwmap.py` now also marks pages whose aligned words are mostly small ints or addresses as data (907 pages; real code pages score ~0.08 against the 0.6 threshold). **The function database must be rebuilt** for this to take effect; that is deferred until all investigators finish, so section numbers so far use the old database.
- **01 (platform) corrected the task-table layout.** Checked in the raw bytes; see the fixed points above.
- **Database fixes after section 08:** (1) table pages counted as data; (2) pages aligned to runtime addresses — the BASIC overlay starts at runtime 0x7F05C000, which was 0x20 bytes before the end of an offset-aligned page, so it had been swallowed into a 160 KiB padding block; (3) every non-data page counts as code for pointer targets, because pages of pointer-only functions (e.g. USRSTART_FIRST 0x7E504AF9) have no call targets; (4) task-table entries are function starts. 168 call edges from mixed pointer/data pages in 0x7EEE–0x7F02 remain; they are noise (0.06%).
- **07 (GUI): block-1 string ids. Confirmed:** in the English table (blob at block-1 offset 0x3781E0, pointer array 0x38B758, load address 0xBFF3D000), id 207 → 0xBFF3E0AA → offset 0x37928A = `Pixel Mapping`. That is the string the camera-tested pixel-hacking patch changed. The setter 0x7E457CED has 211 call sites, as claimed.
- **03 (art filters): extra modules confirmed; their names are not.** The filter dispatch at 0x7E72A635 loads 0x7E71E705 (star light), 0x7E7259A9 (Key Line), 0x7E726F53 (mirror), 0x7E727103 (composite) and others. Mirror is a real 2-pass module: pass table 0x7E85A56C → `art_mirror_pass1` 0x7E726FC4, `art_mirror_pass2` 0x7E72702D, `art_mirror_pass_err` 0x7E727096. Block 0 has **no** table of user-facing filter names: 0x7E7FE240 is a code table, and "NOT ART" is a single pointer. So "Crystal", "Pastel I/II" and the others in section 03 are inferred labels; the source module names (`art_effect_10_star_light`, `art_filter_1c_mirror`, `art_filter_1d_composite`, `art_filter_21_pastel_art`) are verified. The earlier summary "six art filters" counted Pastel I/II as two and Pin Hole III (a variant) as one; it is four modules plus one variant.
