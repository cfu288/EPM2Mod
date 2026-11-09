# 16c. Platform, drivers and libraries 0x7E421020–0x7E6211E0: generated function index (E-PM2 v1.6, rounds D4–D6)

Scope: block 0 from the reset entry 0x7E421020 to the end of the fcs function 0x7E620C6F (0x7E6211E0). This covers boot, the kernel, the drivers, the C runtime and the `sc` library, UI input, MEC, lens, power, BC, firmup, the IMG library, `buff`, WB, TAKE, the file system, strobe and AF.

- **Labels:** **V** = read in the code or the bytes, by a rule with 0 errors in its D6 precision sample. **I** = inferred, or made by a rule that failed its precision sample; I rows start with “probably”, and names quoted from I rows inside other rows also start with “probably”.
- **Index:** `16c-platform-function-index.tsv`, one row for each of the **8,783** database functions in the range (build/map functions.tsv; the 7 `data_page` and 22 `suspect` rows are left out). Columns: `addr`, `size`, `component` (component `>` family), `role`, `basis`, `V/I`. The format is unchanged from D4.
- **Scripts** in `$S/d6/plat/` (D6; copied from `$S/d5/plat/`; run with `python3 -I`). D6 adds `subroots.py` (sub-group roots), `cur_d6fix.py` (D6 corrections, loaded first), `work/mksample.py` / `work/final_sample.py` (precision samples) and `check/` (samples, the checker brief and the verdicts `res_*.tsv`). Older list:
  - `mkidx.py` builds the TSV; `stats.py` gives the levels; `diffidx.py` compares two TSVs; `sample.py` draws the check samples; `q.py ADDR…` is a quick reader;
  - `leaf.py` is the new leaf-summary rule (D5);
  - `cur_<topic>.py` hold the D5 function reads (CUR roles, RAM names, NOTES with the details): `dcf`, `fat`, `dpof` (DPOF + VFS + logsec), `eyefi` (FILECLBK, file shells, EYEFI), `af1`, `af2`, `drv` (BBM/STL, accelerometer, ADC, IOE), `stb`, `prm` (prm, SYSFMEM, USR_FAST_APP), `ui`, `mine`;
  - `lib.py`, `feat.py`, `anchors.py`, `comps.py`, `curated.py` as in D4.

## 1. Area and boundaries (changes in D5 and D6)

The component ranges are in `comps.py`. Each runs to the start of the next one. D5 changes (V: the callers and the code of the edge functions):

| New start | Component | Basis |
|---|---|---|
| 0x7E452343 | **BBM bad-block layer** (bad-block scan, reservoir, two-copy `REPL` table with `PART` page, region table 0x60315244, format 0x7E453B45, mount 0x7E454305, re-layout 0x7E4544B1) | drv reads |
| 0x7E4546CA | **STL core = log-block sector translation runtime** (free-block allocator 0x7E454867, GC/merge 0x7E45583D, map commit 0x7E45471A). The old "STL core (sector map)" started at 0x7E452343 | drv reads |
| 0x7E45AB01 | ADC per_adc. 0x7E45AAD4 is still the accelerometer (transfer-done wait, flag `PER_ACC_SPI2`) | V |
| 0x7E5B5DE5 | FAT file system: 0x7E5B5DE5–0x7E5B6232 are FAT/exFAT dir-entry and first-cluster accessors, not DCF | dcf, fat reads |
| 0x7E5BDF36 | **FAT text-file line reader** (0x7E5BDF36–0x7E5BE155; users: prm CSV 0x7E456561, DPOF 0x7E5BF77E, 0x7E5C2F71) | fat, dpof reads |
| 0x7E5BE156 | **DPOF starts here** (counts, print lists, AUTPRINT.MRK writer/reader), not at 0x7E5BE823 | fat and dpof agree on 15 rows |
| 0x7E5CEB41 | strobe exposure starts here: 0x7E5CEB41–0x7E5CEC4A (flash target and amount calculation, caller 0x7E5D0F5C) were in "SD host driver" | stb reads |

**D6 component changes** (C7 review F003 and the D6 precision checks; V from callers and the D5 reads of the edge functions):

| New start | Component | Basis |
|---|---|---|
| 0x7E4613DD | PER_EYE_SENSOR empty task and a constant stub (were EMS1/EMS2) | code |
| 0x7E4613E5 | **pin-op dispatch layer**: 7 units, pin = unit << 24 \| n; 14 op tables of 7 pointers at 0x7E4C584C + 28·op; init 0x7E4613E5 calls op 0 of all units; dispatchers 0x7E4613FD (op 2), 418 (3), 433 (4), 44E (5), 469 (6), 484 (7), 4A0 (9), 4BB (11), 4D6 (12), 4F1 (13); ops 1, 8, 10 have no dispatcher. Unit 0 = GIO 0x9A100000 (op 4 configure from a record, 5 read input bit 4, 6 write output d1 & 1, 7 irq_attach), unit 3 = pin bank 0x98B00780–0x98B007A4 (op 0 0x7E462252 sets ROM defaults), units 1/2/4/5/6 = `retf`/constant stubs. The DB merged many stubs into 0x7E461FE9, 0x7E46204D, 0x7E462160, 0x7E462252 (real end +138), 0x7E462321, 0x7E461AD1; their rows list the entries | C7 F003, D6 read |
| 0x7E45E820 | cpudma (0x7E45E206–0x7E45E81D are CCD-temperature ADC code, table 0x7E4C4DF0 of the ccd_temp dispatcher 0x7E45DC2C) | D6 check |
| 0x7E50C992 | UI LED / UI_OUT (LED engine 0x7E50C998–0x7E50D654 was under UI input) | D5 ui reads |
| 0x7E5C0A05 | EYEFI requests … (0x7E5C0960/0x7E5C09C4 are DPOF text writers) | D5 dpof reads |
| 0x7E5C8F22 | file wrapper / VFS (VFS init, file-object pool, dir cache) | D5 eyefi reads |
| 0x7E5CBA12 | logsec (request execute/dispatch 0x7E5CBA12/0x7E5CBA48) | D6 check |
| 0x7E5CBCB6 | SD host driver (SD host stack init, R1 status decode) | D5 eyefi reads |

All other ranges are as in D4 (regions table, 01, 13a, 13f, 14b, 15b §1, 15d §5).

## 2. How the index is built (rules, in priority order)

`mkidx.py` collects every fact for a function. The first fact is the primary role, up to two more follow, then a call-graph context when the role is weak.

| # | Rule | Source / signature | Rows (primary) |
|---|---|---|---|
| 0 | **D5 read** | `cur_*.py`: roles read in the code by topic; they replace the curated and section facts of the same row, and their first clause is the short name used for callers. **D6:** topics af1, af2, dcf, fat, eyefi and ui are demoted to I (see §2a) | 2,029 (D6: 1,195 V, 834 I) |
| 0a | **pin-op layer** (D6) | tables 0x7E4C584C + 28·op (14 ops × 7 units), dispatchers 0x7E4613E5–0x7E4614F1; also names the pin-op entries that the DB merged into one row | 31 |
| 1 | curated | roles from the sections and D4 reads | 586 |
| 2 | task | CPU0/CPU1 task tables | 6 |
| 3 | TAKE tables | 0x7E790860 states, A/B event tables, TakeExp/TakeFcs hashes, next state | 186 |
| 4 | section anchors | table rows and `` `name` 0xADDR `` in the sections; **the 16x indexes are no longer sources** (D5). **D6: always I** | 266 |
| 5 | data-word table scan | aligned words in rodata/.data equal to a function start. **D6:** only named tables (curated `TABLES`) give a slot; other words are reported as “pointed to by the data word at W”; no entry count, no “used by”; uITRON task-record entry fields and the pin tables are skipped | 510 |
| 6 | linear jump table | `mov TAB,aN; mov (dX,aN),aN; jmp (aN)`; reported as “first call after case label X” (D6 wording; other cases can reach the same call). **D6:** `mov N,dY; sub dY,dX` bases are decoded | 156 |
| 7 | IRQ | `mov irq,d0; mov lvl,d1; mov H,a0; call 0x7E463C8E/9E`. **D6:** `clr d1` = level 0; a register loaded from memory or another register is “not decoded” (was “None”, or an older constant) | 22 |
| 8 | shape | lone return, constant/global/field getters and setters, per-channel stub, thunk (**D5:** absolute stores before the call are reported as "sets …, then calls"; a thunk that stores through `(off,aN)` is no longer a thunk), two-entry pointer prologue | 1,038 |
| 9 | **leaf summary** (new) | straight-line function without a call (a `setlb`/`Lcc` loop is allowed; ≤ 24 insns): symbolic run of mov/add/shift/and/or/mul; prints the stores and the return value with RAM names, e.g. `leaf: u32[u32[a0+8]+220+d0*4] = d1`. In a loop it prints the first-pass values and the count when it is visible | 216 (+459 as 2nd fact) |
| 10 | own strings | `[tag]name`, `name(`, `name: message` count as a name. **D6:** field labels (`name   :`, `name: %d`) and functions that print more than 2 such labels (dumpers) give no name | 577 |
| 11 | error codes | `mov CODE,d0` before 0x7E426D4B / 0x7E579DBF | 283 |
| 12 | MMIO | operands 0x98000000–0x9AFFFFFF | 118 |
| 13 | address taken (was “callback”) | entry loaded by `mov imm32`, with the store (D6: “+N of aK”, `(aK)` = +0, none when the register is overwritten first) and the next call. **D6 wording:** “address taken (no direct caller)”: a table seed or a task entry reads the same, so no use is claimed | 629 |
| 14 | callee signatures | 60 services with constant arguments (prm tags with names, CamCommand, TAKE, lens pool, timers, ADC, Oimf …) | 499 |
| 15 | kernel services | Oly* wrappers and the 15d kernel rows | 90 |
| 16 | call graph | single caller / shared helper with named callers, ancestor, callees, RAM state | 1,572 |

**Sub-group labels (component `>` family), D6 rule.** The families in `curated.SUBS` were address ranges. In D6 a function gets the family label only when it is linked to the family roots (`subroots.py`: direct calls, `mov imm32` loads, table slots, prologue fall-through) **and** every function that refers to it is itself a member or a root. Shared helpers lose the label. Ranges without roots (IMG art kernels, IMG value-mapping switches, IMG rec/movie helpers, IMG float helpers, TakeExp backlight/face) give no label. Labels fell from 2,879 rows to 1,081. The `lens` debug shell family now holds only the dispatcher 0x7E524C76 tree (0x7E523E5E–…); the lens timed-transmit hook 0x7E52463F (0x7E51C129 → 0x7E524169 → hook 0x604F9070), 0x7E524169, the lens controller 0x7E524284/0x7E52431E and their helpers are no longer in it. The AF family is renamed “FCS_MOVIE task call tree (…, S-AF run 0x7E5EDD24 called by the frame step 0x7E6110C3)”.

**Byte signatures for new functions (V):**
- **FS work-buffer heap** (not a request pair): `call 0x7E5C8497` (alloc d0 = size ≤ 128 → 128-B slot list, ≤ 512 → 512-B list; 16-KB arena *(0x6054754C)) … `call 0x7E5C856E` (free; errors 0x1000C401/03/04/05). A function between them fills a request and calls one of the executors below.
- **FS executors** (request +4 = class << 12 | op; the class only names the caller layer: 0 direct, 1 DCF/DPOF/FAT, 2 FILECLBK, 3 VFS, 5 VFS EYEFI):
  - low 0x7E5B6233: op 0 MOUNT, 1 UNMOUNT, 2 SYNC, 3 CHAIN_READ, 4 CHAIN_WRITE, 5 FORMAT, 6 CHAIN_WRITE_EX (may extend), 7 REMOUNT (media re-init); other ops → 0xE05;
  - high 0x7E5BB51A: op 0 mount check, 1 FIND, 2 DELETE_FILE, 3 DELETE_DIR, 4 CREATE_FILE, 5 CREATE_DIR, 6/7 LOCK/UNLOCK (read-only), 8/9 = 2/3 without flush, 10 FIND_CVCHK;
  - the op names are confirmed by the FS command-log name function 0x7E5C816A (log id = group base 0x50 FAT_ / 0x60 FILE_ + op), which fat and eyefi decoded independently;
  - media request executor 0x7E5CBA12 (31 callers, waits) / logsec dispatch 0x7E5CBA48 (async) → SD layer 0x7E5CD4D4.
- **DCF node cache:** `call 0x7E5B2A8E` with d0 = cmd (1 open, 2 close, 3 suspend, 4 resume, 5 lookup, 6 flush), d1 = drive; file operations are bracketed by cmd 3 … cmd 4.
- **AF trace pair:** `call 0x7E627500(mask)` (print mask 0x6054C7A4) / `0x7E62754B(mask)` (log mask 0x6054C7A8) then `0x7E627A50` (20-B {tag, time, d0, d1, a1} record to the ring 0x6054C79C): a 4-char tag `Xyz` / `Xyz/` is one trace record plus one printed line.
- **FCS OS layer** 0x7E611E24–0x7E6121EF: flag set/wait, queue, Oimf, sleep; 0x7E6120C7 before each wait logs 0x0F8010C0 when the task ran > 3000 µs.
- **IOE request** (32 B): type 0x00/0x40 set register pointer, 0x02/0x42 read N, 0x11/0x51 write one register, 0x13/0x53 write N, 0x20 read and test a mask, 0x31 set/clear output bits, 0x80 raw read.
- **ADC request** (52 B): +0 channel, +1 type (1 single, 0x81 repeat, 0xF1 stop), +4 period, +8 sample count, +12 result buffer, +16 trigger, +32 callback, +36 start hook, +44 average flag.

## 2a. Rule precision (D6)

Method: for every rule (basis value, or group of similar values) with more than 50 rows, a random sample of its facts (seed 6101: 10 per rule, 12 for rules with > 1,000 rows) was checked against the disassembly and the table bytes by blind checkers (`$S/d6/plat/check/CHECK_BRIEF.md`; verdicts `check/res_*.tsv`). A fact counts as wrong when any concrete detail is false (address, offset, slot, count, order, role). Rules with a wrong fact were fixed and re-sampled (seeds 6202, 6303) or demoted. Rows = facts made by the rule in the final build (a row can hold up to three facts).

| Rule (basis) | Rows | Checked | Wrong | Precision | Action |
|---|---|---|---|---|---|
| call graph (helper of / shared helper / under / RAM state) | 5,524 | 12 | 0 | 12/12 | V |
| callee signatures (service calls) | 2,009 | 12 | 0 | 12/12 | V |
| own strings | 1,325 | 12 | 0 | 12/12 | V; **fixed** after the final check (a dumper was named from one of its 29 field labels) |
| callback (`mov imm32`) | 1,104 | 12 + 10 | 2 + 0 | 10/12 → 10/10 | **fixed**: store offset of `(aN)` stores and of a register overwritten before the store; store is now “+N of aK”; after the final check (a table seed called a callback) reworded to “address taken” |
| shape: thunk | 693 | 10 | 0 | 10/10 | V |
| shape: getters, setters, stubs, prologue entries | 637 | 10 | 0 | 10/10 | V |
| leaf summary | 675 | 10 | 0 | 10/10 | V |
| kernel wrappers | 638 | 10 | 0 | 10/10 | V |
| curated (sections, D4 reads) | 584 | 10 | 0 | 10/10 | V (plus the multi-row texts re-read, below); 0x7E53E2CD was named `sc_get_stabtype` from a printed label (final check), now its dump role |
| data-word table scan | 537 | 10 + 10 + 10 | 5 + 3 + 0 | 5/10 → 7/10 → 10/10 | **fixed twice**: entry counts and “used by” removed (counts were DB starts only; an equal immediate can be another table’s end bound); task-record entry fields skipped; the run start is not always the table base (12-B records), so unnamed tables report only “pointed to by the data word at W” |
| error codes | 462 | 10 | 0 | 10/10 | V |
| section anchors | 359 | 10 | 3 | 7/10 | **demoted to I** (a wrong table address from 13a, a “HUGE constant” that is 0.0, a 13a text copied to 3 rows) |
| MMIO constants | 238 | 10 | 0 | 10/10 | V |
| TAKE tables | 189 | 10 | 0 | 10/10 | V |
| linear jump table | 185 | 10 + 10 + 10 | 1 + 2 + 1 | → fact reworded | **fixed**: `sub` bases; then reworded to the certain fact “first call after entry k of jump table T (switch in D)”: the entry index and first call were right in all 30 checks, the case value and “handler” were not |
| task table | 65 | 10 | 0 | 10/10 | V |
| IRQ attach sites | 53 | 10 + 10 + 10 | 3 + 1 + 0 | → 10/10 | **fixed**: `clr d1` = level 0; a level, IRQ or handler loaded from memory or a register is “not decoded” (was None, or an older constant: a handler table was named as the handler) |
| D5 read: dcf | 339 | 10 | 2 | 8/10 | **demoted to I** |
| D5 read: af2 | 224 | 10 | 4 | 6/10 | **demoted to I** |
| D5 read: fat | 221 | 10 | 1 | 9/10 | **demoted to I** |
| D5 read: eyefi | 208 | 10 | 1 | 9/10 | **demoted to I** |
| D5 read: af1 | 176 | 10 | 3 | 7/10 | **demoted to I** |
| D5 read: ui | 141 | 10 | 1 | 9/10 | **demoted to I** |
| D5 read: stb, dpof, drv, prm | 179, 173, 167, 160 | 10 each | 0 | 10/10 each | V (as read) |
| component range | 8,783 | 11 + 10 | 1 + 2 | 10/11, 8/10 | boundaries fixed (§1); a range rule, so it stays a known limit (§7) |
| sub-group label (family) | 1,081 | 12 + 10 | 1 + 0 | 11/12 → 10/10 | **rebuilt** as a linked-family rule (§2); one root removed (0x7E53053F) |
| pin-op layer (D6), D5 mine, D6 fixes | 31, 27, 19 | – | – | < 50 rows | V where read |

All wrong facts found by the samples were corrected in `cur_d6fix.py` (19 rows; those in demoted topics stay I). Every I row and every I fact inside a V row now starts with “probably”; names quoted from I rows in other rows (e.g. “helper of 0x7E5B108F (probably DCF mount …)”) are hedged the same way.

**Curated texts applied to more than one row** (D6 re-read): scheap wrappers 0x7E5072ED…0x7E507387 (12 rows: `mov fn,a0` + call 0x7E507395 / `mov fn,a1` + call 0x7E5073B8; a0/a1 are function pointers; the cores run the fn with task dispatch disabled through sns_dsp/dis_dsp/ena_dsp, there is no pool pointer and no lock); “WB gain/colour getter” ×4 (0x7E579E7F is the 3×3 colour matrix: prm tag from table 0x7E78F028/0x7E78F05C × ROM matrix 0xAA6A/0xAA4A via 0x7E57F0DF into obj+18, +14 = +16 = 4095, no WB gain; the other 3 are I); “colour-matrix computation (26 entries)” ×2 → I; “PWM duty helper” ×2 → the Oimf facts; “WB state getter” ×2, “external flash state record read” ×2 → the copies they make; IMG job builder ×3 (0x7E545590 runs a caller-given job, it fills no descriptor); 13a anchor texts “one of the row A / B / C” → I. The shared labels used in many caller rows were corrected: `FAT request` → `FAT text-file line reader` (0x7E5BDF36, 19 rows), `APPEVENT/status trigger` → `key status read by id`, `FAT NO_FAT_CHAIN check` → `FS low executor`; and three curated rows that D5 had corrected only in its notes (0x7E5C816A FS command-log id → name; 0x7E5C8AEE event-flag set wrapper; 0x7E50C26B → I). Checked and kept: EMS2 decoders, console UART inits, system-controller/EMS/IMG/CPUCONN ISRs, SIO hooks, EYEFI requests, FILEFGND posts, IMG_PRECON cmds, u16 min.

## 3. Tables and structures decoded in D5 (V unless marked)

- **File system:** FAT drive table 0x6053D070 (u16 per drive) and volume records 0x6053CF94 + 92·drive; FAT32/exFAT FAT cache (32 × 4 KB, hash 0x6053CF7C, lists free/clean/dirty, dirty list head/count 0x6053CE18/1C); exFAT bitmap cache; FS command-log ring (400 entries at 0x605455E4); DCF drive state 0x6053C688 (1 closed, 2 open, 3 suspended, 4 error), node-cache slots 0x6052EB98 + 120·drive (0 head, 1 tail, 2/3/4 windows of 60 indices, window loads by DCFPROC_SUB 0x7E5B34CE through queues 0x7E43ECD6/0x7E43ECD4), 548 file nodes × 96 B, 1,800 folder records × 48 B, root records DCIM/MISC/PARAMDT 0x6053C890 + 52·drive; dcfnum cmds 0–9 (MOUNT, RECNUM, RECNODE, FORMAT, DELMOUNT, UNMOUNT, 6 (RECABORT, I), RECNUM2, RECCANCEL, CLEARFLASH); dcfedit ops 0–9; dcfsearch_exec subcommands 1–8.
- **FILE object** (VFS slot): size +264/+268 (64 bit), attr +272, times +276/+280, first cluster +288, position +304/+308, flags +312, op mask +452; fopen mode table 0x7E79A594; libc-like fopen 0x7E5C97C1, fclose 0x7E5C9A5F, fwrite 0x7E5C9DCC → core 0x7E5C9E14 (sector read-modify-write) / 0x7E5CA053, fread 0x7E5CA3FB, rename 0x7E5CA752, remove 0x7E5CA7B5, mkdir 0x7E5CA8C5, findfirst/next/close 0x7E5CB81B/8D2/95C.
- **FILECLBK:** class 0 = group dispatcher 0x7E5C1BC6 (hash 0x7E795E78: media, DCFED, DCFNUM, DCFPMARK, FAT, FILE, DOSMEM, DOSFSTRM, DCFSEARCH); class 1 = fileif 0x10001–0x1000D; class 2 = 0x20004–0x20020. EYEFI requests 0x200001–0x200007. FILEFGND job kinds 0/1/2 in a 32-slot ring 0x60545454.
- **DPOF:** dpofnode pool 1,999 × 12 B, per-drive print lists A/B with edit begin/commit/cancel, AUTPRINT.MRK writer 0x7E5BE547/0x7E5C0366 and reader 0x7E5BF77E → line parser 0x7E5BF85B; status codes 0x58xx.
- **AF:** FCS command hash 0x7E7A04F8 (24 commands; start 0x1100/0x1200/0x1202/0x1400/0x1600/0x1700/0x1800/0x3000); FCS_MOVIE hash 0x7E7A896C; AF context `mvbuf` 16 KB at 0xBC3C8040 (magic 0xDEADBEEF); **AF grid** table 0x7E7A1C60 (35 points, 7 × 5, 640 × 480 coordinates, point 17 = centre; used by 0x7E5E7EAE); S-AF 0x7E5EDD24 phases (3-point fit on 256·log2 of the AF values, 0x7E5F27B4); HPF tables 0x7E7A0E8C/0x7E7A0CEC; `fcs_lens_mfts_*` = 84-B LENS_CTRL, class 3, mode 0x60, act mode 0xFF/1/2/3/4, through the lens controller 0x7E524284/0x7E52431E.
- **Strobe:** STB_EXPOSE_INFO 15,968 B; `cam_bright[i]` = 36 B at ctx+28+36·i (0 ambient, 1/2 external pre-flash, 3/4 internal pre-flash, 5 second AE frame); pre-flash sequences 0x7E5D1FDC (RC commander), 0x7E5D247F (internal), 0x7E5D2708 (external; C6 F011); external-flash serial packet {0x55, cmd, data, sum}.
- **prm:** bank descriptor pool 6 × 28 B at 0xA074AF7C (FLASH, EEROM, MODE, BKRAM, CPRAM, CSV); image head {u16 id, u16 checksum, u32 counter}; tag index 0x603A0E38 + 8·(tag >> 4) (CSV overlay 0x603A8E38).
- **Drivers:** ADC channel table 0x7E4C4908 (9 × 16 B: channels 04 0D 0F 16 15 26 22 29 27, all mode 1 except 0x27 mode 9); accelerometer on SIO ch3 in I2C mode, address 0x18, WHO_AM_I 0x0F = 0x32 (I: ST LIS331DLH); IOE scan table 0x7E4C7294, ID map 0x7E4C726C.
- **UI:** key status groups ROM 0x7E7355A4 (12 × 12 B; E-PM2 uses groups 1, 2, 6, 7, 9, 11); key-state ring 0x604F3898 (10 × 6 B); event codes 0x0200_0000|id press, 0x0201… release, 0x0202… switch, 0x0203… jog step; ADC ladder → key table 0x7E7354A8; jog state 0x604F385C + 28·slot; LED engine (34 request ids → 4 PWM LEDs); sound engine (Oimf sub-ops 65/69/73/36/37 to 0x7E43ECCC).
- **Heap checker link (C6 F001, V):** SCHEAPDBG 0x7E507A3A → 0x7E507AA4 (saves the bad block at 0xA074FA34/38/3C) → 0x7E44EE29(3) writes cause 3 to 0x8FF000B4 and 1 to ICU 0x99300300 → IRQ 122 ISR 0x7E44EE39 prints `Heap Destroy!`, dumps the lists (0x7E507AC2 → 0x7E507ACB(4, blk)), calls the DEVELOP_PHASE stub 0x7E50796D, then `CPU1 Yo-in De Reboot!` and spins. The NMI handler 0x7E463CD9 sends cause 1.

## 4. Coverage (rows with a role / all rows)

**8,783 / 8,783 rows have a role (0 blank).** Levels from `stats.py` (D6 classifier: A = own specific role, rules 0–13 or a string name, **marked V**; B = partial: callee signatures, kernel services, unnamed strings, a call-graph role that names a caller or ancestor, **or any I row**; C = context only: call graph without a named caller). The D6 classifier counts I rows as B, so the D5 column is recomputed with it:

| Level | D5 TSV (D6 classifier) | D6 TSV |
|---|---|---|
| A specific (V) | 5,872 (66.9 %) | **4,560 (51.9 %)** |
| B partial (incl. I rows) | 2,574 (29.3 %) | 3,882 (44.2 %) |
| C context only | 337 (3.8 %) | 341 (3.9 %) |

- V/I: D5 8,409 V / 374 I → **D6 7,134 V / 1,649 I**. The drop in A is the demotion of six D5 read topics (1,276 rows V → I) and of the section anchors; the rows keep their text, hedged with “probably”.
- **Rows changed against the D5 TSV: 5,254** (role text 4,158; main component 98; sub-group label dropped 1,798; V → I 1,276).
- Lowest level-A shares now: DCF 5 %, uITRON kernel 6 %, C runtime 6 % (section anchors, now I), FAT 7 %, AF 22 % (D5 dcf/fat/af reads, now I).

## 5. Measured accuracy

A row counts as an **error** when any un-hedged fact in it is false (vague but true facts are not errors).
- **D5:** sample 1 2/30 (rule fixes), sample 2 0/30. The D6 rule samples (§2a) show that these 30-row samples were too small: 28 of 301 facts were wrong in the first D6 rule sample (most in D5 reads, section anchors, table slots, IRQ and callback rows).
- **D6 full-row checks** (blind checkers, whole row incl. component; `check/final*.tsv`, verdicts `check/res_fin*.tsv`, `res_f3*.tsv`):

| Round | Build | Rows (V / I) | Wrong V | Wrong I (hedged) | Causes, all fixed afterwards |
|---|---|---|---|---|---|
| seed 7313 | after rule fixes | 40 (35 / 5) | 1 | 1 | unnamed table “used by” was another table's end bound; a hedged D5 ui row |
| seed 8424 | + table/case/IRQ rewording | 24 checked (24 / 0) | 3 | – | a curated name and an own-string name taken from printed field labels; a table seed called a callback |
| **seed 9535** | **final build** | **40 (34 / 6)** | **1** | 0 | the quoted ancestor name of 0x7E432A3F came from a 15d role-I kernel row without a hedge (the call path itself exists); 15d role-I names are now quoted as “probably …” |

- **Final error rate among V rows: 1 / 34 = 2.9 %** on the final-build sample (0 / 6 I rows wrong); over the three rounds 5 / 93 V rows (5.4 %), every cause fixed by a rule change (§7). The target 0 was not reached in a fresh sample of the shipped build; the last fix (hedged 15d names, 230 rows) was not re-sampled.
- Rule-level precision after the fixes: every rule that still asserts V had 0 wrong facts in its last ≥ 10-fact sample (§2a).

## 6. Corrections to older sections and to the D4 index

1. **0x7E5C8497 / 0x7E5C856E are the file-system work-buffer heap alloc/free**, not "file-system request alloc / submit" (D4 curated + §2 signature; 145 D4 rows quoted them). 0x7E5B9184 "issues one 128-B I/O request" → writes one FAT cache block to each FAT copy; 0x7E5BF77E "DPOF file-request builder (128-B request)" → AUTPRINT.MRK reader driver.
2. **prm:** 0x7E457C52 returns the tag's data pointer and 0x7E457C62 its element count (not "prm get" / "prm set2"; 55 D4 rows). `prm size` rebuilds the EEROM/MODE/BKRAM images from the defaults (side effect).
3. **FAT:** 0x7E5B906C moves a FAT-cache block to list n (0 free, 1 clean, 2 dirty), not "unlink from list 1 of 3"; 0x7E5B9145 writes back the dirty list (not a pending request-list flush); 0x7E5B9D07 is a general sector read/write helper; 0x7E5BA075 only builds the exFAT boot sector (0x7E5B9EBB writes it).
4. **DCF:** 0x7E5AF0EA's dummy folder is `100OLYMP` (`xxxOLYMP` is the copy worker's template); 0x7E5AEC58 is case 7 only (case 6 ALL_DELETE → 0x7E5AE6A5, with case 8); the 52-B record 0x6053C890 is per drive (root entries DCIM/MISC/PARAMDT), not per entry; C6 F009's "number N" is the DCF index (node +40).
5. **0x7E5C816A** is the FS command-log id → name function, not the DCFNUM command handler (also section 02); 0x7E5C8AEE is a generic event-flag set, not "FILEFGND wake"; 0x7E5C0CCB/0E4B/0E89 are Eye-Fi attach/detach code called from FAT mount/unmount; 0x7E5C920F is the path-walk entry callback, not a `.`/`..` lister; C6 F010's "checks write mode" is a handle-valid check (0x9414 = invalid handle or no access).
6. **STL/BBM:** 0x7E453B45 is the full format after chip erase (not "map build"), 0x7E4544B1 a re-layout without chip erase (not "maintenance"), 0x7E455A6D a REPL table rewrite (not "recovery"); no 0x1C SYSFMEM codes or error-recorder calls in the range (return codes −1 … −42).
7. **ADC:** ADCONV init has exactly two start-up requests, channel 0x82 (0x7E45B8D6, C6 F003) and channel 0x81 (0x7E45B980); **both are dead on the E-PM2**, as are the engines for modes 2, 3, 7 and 8. The ADC unit is at 0x98C00000 (0x99800000 is only printed by the shell). Firmware quirk: the mode-7/8 engines call 0x7E45B71D(2)/(3), which matches no case, so those slots stay busy after a stop (harmless, unused modes).
8. **Accelerometer:** I2C on SIO ch3, not SPI; 0x7E458938 is the completion callback of the ADC request 0x60414908 (temperature channel), not a timer callback (11-version-history).
9. **UI:** 0x7E50A15C is the key-state ring consumer (no key matrix); 0x7E50B4C7 is an ADC poll start for configurations without a press IRQ (it does nothing here); 0x7E509CA3 is a key status read (0 = active), not an APPEVENT trigger; 0x7E50B0A8 serves all 12 groups. UI_IN flag bit 0x02 comes from the 10-tick soft timer 0x7E509088 (callback 0x7E5090F5): this answers 01 open question 7.
10. **AF:** 0x7E5E2B70 is the FCS command dispatcher; the AF grid table exists (0x7E7A1C60; answers 12 §2.4/§2.5 Q2); 15b §5.4: codes 0x1101/0x1201/0x1701/0x1704/0x1801/0x3001 reach the default 0x7E610CCA (error 0x0F80F001, reply 0x2703), they are not "no action"; the `fcs_lens_mfts_*` requests go through the lens controller, not 0x7E51F98E; 0x7E611515 is CONTSTILL (C6 F012; 16d's `FCS_END` name is wrong).
11. **Strobe:** 0x7E5CEB41–0x7E5CEC4A are strobe-exposure code (were in the SD driver). The kernel "create" calls 0x7E4491E8, 0x7E449000 and 0x7E4493D9 are stubs that return 0 (the STB_*, USR_FAST and acc objects are pre-assigned).
12. **USR_FAST_APP:** bit 0x20 is TakeFunc (0x7E502391/0x7E502467), not 2ndEnd; the lens reply wait in 0x7E502C7B never runs (0x7E5027D7 always returns 1).
13. **buff (C6 F008):** 0x7E579B45 = pool method 0, get the buffer address of id n (returns 0 taken / 2 free / 4 bad id); 3 slots of vtable 0x7E78EEBC are base-class code.
14. Section 13f/D4 "lock pair 0x7E4215A2/0x7E4215B6" and "SIO open counter" corrections stand as in D4.
15. **D6:** 0x7E579E7F is a 3×3 colour-matrix computation, not a WB gain getter (14b §3); 0x7E507395/0x7E5073B8 run a function pointer with task dispatch disabled (14b §2 “alloc core, pool by pointer, lock 0x7E436593” is wrong); 0x7E545590 runs a caller-given IMG job (13a §3.2 “job builder, 320-B descriptor” fits only 0x7E545276/0x7E5453CA); 13a: the sin polynomial table is 0x7E7316CC (not 0x7E7371CC) and 0x7E4FFD20 returns 0.0 (not a HUGE constant); 0x7E5C816A is the FS command-log id → name function and 0x7E5C8AEE a generic event-flag set wrapper (02 §6, 13f §2.4); 0x7E53E2CD is the `bc_main` debug-info dump, not `sc_get_stabtype`; 13f: 0x98B00780–0x98B007A4 is the unit-3 pin bank of the pin-op layer (13f lists 0x98B00000 only as SDRAM controller/arbiter/bus monitor); cpudma starts at 0x7E45E820 (0x7E45E206… is CCD-temperature ADC code).

## 7. Known rule errors and limits

Fixed in D5: (a) FS heap pair named as request alloc/submit; (b) prm get/set2 names; (c) data-word slot numbering; (d) thunk rule reading stores as arguments; (e) section anchors citing the 16x indexes; (f) curated short names winning over newer reads.

Fixed in D6 (TSV regenerated; details in §2/§2a):
- **(g) sub-group labels by address range** (e.g. the `lens` debug shell range held the lens timed-transmit hook 0x7E52463F and the lens controller 0x7E524284/0x7E52431E): replaced by the linked-family rule; 1,798 labels dropped.
- **(h) pin-op layer** 0x7E4613E5–0x7E4614F1 filed under EMS1/EMS2, with table-slot rows giving wrong slots and entry counts: own component and decode (§1); the DB-merged stub rows list their entries.
- **(i) curated texts copied to several rows**: scheap wrappers/cores, WB getters (0x7E579E7F = colour matrix), colour-matrix pair, PWM helpers, strobe record copies, IMG job builders, shared labels (`FAT request`, `APPEVENT trigger`, `FAT NO_FAT_CHAIN check`); curated rows corrected only in D5 notes (0x7E5C816A, 0x7E5C8AEE, 0x7E50C26B).
- **(j) data-word table scan**: entry counts (DB starts only), “used by” (end-bound immediates), task-record entry fields read as 1-entry tables, run start taken as the base of 12-B record tables.
- **(k) linear jump tables**: `sub` bases not decoded, so case values were off by the base (0x20019 reported as 0x18); now the entry index is reported.
- **(l) IRQ rule**: `clr d1` reported as level None; a handler table read through `mov (d0,a0),a0` reported as the handler.
- **(m) callback rule**: wrong store offset (`(aN)` stores, overwritten registers); table seeds called callbacks → “address taken”.
- **(n) own-string names from field labels** (`face_area_count   :`, `sc_get_stabtype: %d`).
- **(p) 15d role-I kernel names** (e.g. 0x7E432A3F “static object creation walker”) were quoted un-hedged in caller/ancestor references; now “probably …”.
- **(o) hand example** 0x7E5C8D48: the path has the 2-char drive prefix (`C:/DCIM/100OLYMP/PA010001.JPG`).
- Demoted: section anchors and D5 topics af1, af2, dcf, fat, eyefi, ui (I, “probably”).

Still open:
- **Component ranges**: 2 of 21 sampled components were wrong (both fixed, §1); other boundaries were not all re-checked, and the large components (AF, DCF, FAT, lens, IMG) contain helpers shared with neighbours.
- **I rows (1,649)**: the demoted D5 topics hold mostly true text (they scored 6–9 of 10), but no row there is guaranteed; re-read before quoting.
- **Leaf summary** shows first-pass values inside loops and does not track stack arguments beyond `stack(+off)`.
- **F019** (coverage/round7-review1.md, 0x7E704E01) is a 16d row, outside this index: its condition should read “15000 := 0 when 556 changed, or when 556 ≠ 4 and AE BKT (480) is off” (480 is not compared before/after). Not edited here.

## 8. How to classify a new function in this range

1. Look it up in the TSV (component, role, rule).
2. For an extra start inside a row, use that row and the signatures in §2.
3. A function that allocates from 0x7E5C8497, fills +4 and calls 0x7E5B6233/0x7E5BB51A/0x7E5CBA12 issues the FS op named in §2 for that class/op.
4. An “address taken” row with a `next call` is often a completion or event callback for that service (but table seeds and task entries look the same) (lens submit 0x7E51F98E → req+4; MEC 0x7E512AE0/0x7E512A57; CamCommand 0x7E628303 → +40/+44; SC_TTIMER 0x7E506FF6 / tmr_start 0x7E4650A2 → timer).

## 9. Open questions

1. What runs at 0x7E401400 (below block 0), the flash service used by the BML/STL API when 0x600011DC is 0.
2. FS media ops 9/13/14 and whether op 2 (ALLOW) is a real unmount; the SD driver command meanings (cmd 2/3/4/10/13/14) are I.
3. dcfnum cmd 6 name; DCF drive ids 2–6 (0x7E5B2092, 0x7E5B0FF5); prm 0x4091, 0x85C1, 0x8A41, 0x36C1.
4. The C-AF phase codes 0x1D00, 0x1D20, 0x1500, 0x1F00, 0x2706 and the time unit of 0x7E626E79.
5. The prm element-size rules: layout from tag & 3 but typed get/set from tag & 7; whether any tag hits the mismatch.
6. 0x7E45D444 ("backup-register write"): the UI code uses its d0 as the power-key state byte; recheck.
7. Strobe req+83 values 3/5 (RC level selector) and the area statistics in 0x7E5D7471/0x7E5D7828/0x7E5D70E9/0x7E5D893D.
