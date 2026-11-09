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
- ~~Default interrupt vector table at block-0 offset 0x4CDD0~~ **Corrected (13f, checked by coordinator):** the 26 words at 0x7E46DDF0 all point to 0x7E44ACB0, which prints `start:throug` for the `busmes through` debug command (called from the shell at 0x7E44A9A7). They are a debug-command table, not interrupt vectors. The real interrupt path: vector registers 0x8000–0x801C → stubs 0x7E430020–0x7E430070 → common entry 0x7E432648; `irq_attach` 0x7E463C8E (57 call sites) → `irq_register` 0x7E44B57F.
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
- **09 (art deep dive): Watercolor is stored picture mode 120, and the earlier "hidden Pastel" was wrong. Confirmed.** Three independent checks:
  - The ART BKT builder 0x7EA7633A pairs info 469 with 120 and info 424 with 119.
  - The menu table labels info 469 "Watercolor" (1717) and info 424 "Key Line" (1452).
  - `rec_art_set_exif_data` 0x7E70DC24 (table 0x7E852300; earlier notes said 0x7E852200 by mistake) writes 33/34 for 120.

  The mode-controller tables `gui[]` 0x7E83F70C and `raw[]` 0x7E844CC0 were re-dumped by hand: they give 19 pairs, art GUI 8–17 → 100–109, 18 → 119, 19 → 120, and nothing for 110–118.
- **09b: the Fragmented random generator is xorshift32. Confirmed:** 0x7E54594F is `x ^= x<<13; x ^= x>>17; x ^= x<<5` and maps 0 to 1.
- **09 cross-body: E-PL7 Exif writer 0x7DE40D28. Confirmed by hand:** case 111 stores 12, 115 stores 23, 117 stores 28 and 118 stores 29 (Fish Eye, Sparkle, Reflection, Fragmented in ExifTool's table).

## Second pass: re-checking every "hidden" feature (sections 10a–10f)

The art-filter deep dive (section 09) showed that the first pass named features from strings and assumed reachability. Every feature marked hidden, dormant, stub, unknown or "active (inferred)" in `docs/firmware-map.md` is now re-checked with the same method:
1. read the code;
2. trace reachability (menu tables, mode-controller value tables, setting writes, model and hardware gates, debug shells);
3. compare across bodies;
4. use external sources only as corroboration;
5. give each earlier claim a verdict.

Resources built for this pass, outside the repo:
- function databases for E-PL5 1.6, E-PL6 1.4, E-P5 1.8, E-M10 1.4, E-PL7 1.4, E-M5 II 4.1 and PEN-F 3.1 (`fwmap.py --fw/--base/--out`);
- each body's English UI strings, from `scripts/lang_dump_en.py`. It reads the block-1 directory and solves each language blob's load base, e.g. E-PM2 0xBFF3D000 / 1970 ids, E-P5 0xBFF2A200 / 2317, PEN-F 0xA2CE3C00 / 2892.

English-string counts not present in the E-PM2: E-PL5 0 (block 1 identical), E-PL6 71, E-P5 544, E-M10 651, E-PL7 672, E-M5 II 979, PEN-F 1199. Shared block-1 text proves nothing about whether a body offers a feature.
- **10a: interval shooting is missing only its menu row. Confirmed.** E-PM2 top menu (36 rows from 0x7EFFE13C): `… 182, 526, 262 …`, and 1357 is absent. E-PL6 1.4: the run `182, 1357, 526, 262` at 0x7EFFF8BE.
- **10b: 3D Photo is selectable. Confirmed.** The SCN list (u8) at 0x7E84976D is the 23 entries `9 67 11 17 8 12 18 47 40 46 41 23 49 31 21 26 14 20 29 110 111 112 115`.
- **10c: AVCHD is not in the movie-quality list. Confirmed.** The info-45 record 0x7E84A554 holds raw[] 0x7E846500 and gui[] 0x7E83F890, i.e. 6 entries {quality, format, F/N}: (6,3,1) (6,3,2) (3,3,1) (3,3,2) (3,1,2) (4,1,2). There is no format 2.
- **10e: the E-PL5 carries the same menus and accessory tables. Confirmed:** the E-PM2 top menu table (370 B) is byte-identical in the E-PL5 at 0x7EFFEA28, and the accessory ID/config tables (148 B) at 0x7E4C7264. The sub-item table is not byte-identical; no claim depends on it.
- **10d: Wind Noise Reduction is a user setting. Confirmed:** 0x7E95136C reads prm 30833 (0x7871); a non-zero value calls wind cut 0x7E951BDE, otherwise the other branch is taken.
- **10f: the ADJ accept table. Confirmed:** 0x7F0D25A2 holds 22 {op, flag} pairs (0x1002/0x1003/0x1014–0x1017 and vendor ops 0x9005–0x902B, including 0x902B).
- **CORRECTION (2026-11-09): the E-PM2 has an accessory port.** Olympus's official E-PM2 release notes (archived in ep5-fw-reverse `firmware/notes/release_notes/1010_i06.html`) list for **Ver.1.2 (Jun.12 2013): "Supported VF-4 electronic view finder."** The VF-4 attaches to the accessory port. The earlier note "the E-PM2 has no accessory port" came from product knowledge and was wrong. It made the PENPAL/EVF code look dormant; 10e had already found the detection code and tables identical to the E-PL5's. The PENPAL/EVF/SEMA-1 paths are therefore hardware-gated: active with the accessory attached.
- **13a (C runtime / image library): spot checks confirmed.**
  - 0x7E4C90CA–0x7E4FDFFF is 216,886 bytes of 0xFF.
  - `memset` 0x7E500D73 (1,367 call sites) is a byte-store loop over [a0, a0+d1) with value d0.
  - `sprintf` 0x7E4FFDE3 has 1,664 call sites.
- **13e (mcon/sequencers): the TAKE command tables are keyed by cmd + 1. Confirmed:** `inc d1` at 0x7E582A48 / 0x7E588321, then index (d1 & 31)·8 and compare key == d1. Table keys start 0x1, 0x2, 0x101, 0x102, …. Section 02 §4 now carries the correction.
- **13d (GUI toolkit): 0x7EE02095–0x7EE21020 is a GL library for C3D, not GUI. Confirmed:** all 89 external callers are in the C3D region 0x7EE21020–0x7EE41020 or the C3D tasks 0x7F09–0x7F0A, and none are in GUI code. `GM_*` message names: 56 strings match `^GM_[A-Z_]+$` against the claimed 61 (detail to recheck).
- **13b (face/AV): the overlay-A library is red-eye correction. Confirmed:** `play_face_redeye_adjust` 0x7E94318E passes command 5 (`mov 5,d1`) to the sender 0x7E50689F. The library ends where the BASIC keyword table starts at 0x7F0691C8 (`list run new bye next return goto gosub …`). This corrects the C1 note "face-scoring library".
- **13c (C++ framework): the OMReactive vtable. Confirmed:** slot 15 of 0x7EC91FE8 is 0x7EBA6D64 = `mov (104,a0),a0; retf`, i.e. getCurrentEvent returns this+104. Section 13c and 13b agree that the OXF runtime ends at ~0x7EBA7BB5 and that 0x7EBA7BC1– is an OKAO library (Smart Skin per 13b).
- **Correction pass F1 rejected 13a §5 #4. Confirmed:** the image job library writes image-engine registers directly: `mov d3,(0x99400008)` at 0x7E54DABB, `mov d0,(0x99400000)` at 0x7E557514. Section 09b's "image-engine driver" wording stands.
- **C2 batch 4: the GL library runs past 0x7EE21020. Confirmed:**
  - The `{name, fn}` table at 0x7F023C74 has 194 `gl*` entries. 89 of them point above 0x7EE21020 (the reviewer said 91), and the highest is glPointSize at 0x7EE29468.
  - `$Revision: #88 $` (0x7F027CC4) is referenced by 0x7EE295EE, in the module that follows.
  - So the GL library ends at ~0x7EE294B4, not 0x7EE21020. Fix pending in the regions table and in sections 08 and 13d.
- **Fix pass A5+C2: the touch-panel image end. Confirmed** by arithmetic: 0x7E7F0F78 + 470 × 85 − 1 = 0x7E7FAB85, as the editor says (the review's 0x7E7FAB34 was wrong).
