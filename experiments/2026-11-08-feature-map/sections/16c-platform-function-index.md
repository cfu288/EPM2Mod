# 16c. Platform, drivers and libraries 0x7E421020–0x7E6211E0: generated function index (E-PM2 v1.6, rounds D4–D5)

Scope: block 0 from the reset entry 0x7E421020 to the end of the fcs function 0x7E620C6F (0x7E6211E0). This covers boot, the kernel, the drivers, the C runtime and the `sc` library, UI input, MEC, lens, power, BC, firmup, the IMG library, `buff`, WB, TAKE, the file system, strobe and AF.

- **Labels:** **V** = read in the code or the bytes. **I** = inferred from names, order, layout or call position.
- **Index:** `16c-platform-function-index.tsv`, one row for each of the **8,783** database functions in the range (build/map functions.tsv; the 7 `data_page` and 22 `suspect` rows are left out). Columns: `addr`, `size`, `component` (component `>` family), `role`, `basis`, `V/I`. The format is unchanged from D4.
- **Scripts** in `$S/d5/plat/` (copied from `$S/d4/plat/`; run with `python3 -I`):
  - `mkidx.py` builds the TSV; `stats.py` gives the levels; `diffidx.py` compares two TSVs; `sample.py` draws the check samples; `q.py ADDR…` is a quick reader;
  - `leaf.py` is the new leaf-summary rule (D5);
  - `cur_<topic>.py` hold the D5 function reads (CUR roles, RAM names, NOTES with the details): `dcf`, `fat`, `dpof` (DPOF + VFS + logsec), `eyefi` (FILECLBK, file shells, EYEFI), `af1`, `af2`, `drv` (BBM/STL, accelerometer, ADC, IOE), `stb`, `prm` (prm, SYSFMEM, USR_FAST_APP), `ui`, `mine`;
  - `lib.py`, `feat.py`, `anchors.py`, `comps.py`, `curated.py` as in D4.

## 1. Area and boundaries (changes in D5)

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

All other ranges are as in D4 (regions table, 01, 13a, 13f, 14b, 15b §1, 15d §5).

## 2. How the index is built (rules, in priority order)

`mkidx.py` collects every fact for a function. The first fact is the primary role, up to two more follow, then a call-graph context when the role is weak.

| # | Rule | Source / signature | Rows (primary) |
|---|---|---|---|
| 0 | **D5 read** (new) | `cur_*.py`: roles read in the code by topic; they replace the curated and section facts of the same row, and their first clause is the short name used for callers | 2,029 (1,773 V, 256 I) |
| 1 | curated | roles from the sections and D4 reads | 586 |
| 2 | task | CPU0/CPU1 task tables | 6 |
| 3 | TAKE tables | 0x7E790860 states, A/B event tables, TakeExp/TakeFcs hashes, next state | 186 |
| 4 | section anchors | table rows and `` `name` 0xADDR `` in the sections; **the 16x indexes are no longer sources** (D5) | 266 |
| 5 | data-word table scan | aligned words in rodata/.data equal to a function start; slot = (word − table base) / stride (**D5 fix**) | 510 |
| 6 | linear jump table | `mov TAB,aN; mov (dX,aN),aN; jmp (aN)`; first call after each case label | 156 |
| 7 | IRQ | `mov irq,d0; mov lvl,d1; mov H,a0; call 0x7E463C8E/9E` | 22 |
| 8 | shape | lone return, constant/global/field getters and setters, per-channel stub, thunk (**D5:** absolute stores before the call are reported as "sets …, then calls"; a thunk that stores through `(off,aN)` is no longer a thunk), two-entry pointer prologue | 1,038 |
| 9 | **leaf summary** (new) | straight-line function without a call (a `setlb`/`Lcc` loop is allowed; ≤ 24 insns): symbolic run of mov/add/shift/and/or/mul; prints the stores and the return value with RAM names, e.g. `leaf: u32[u32[a0+8]+220+d0*4] = d1`. In a loop it prints the first-pass values and the count when it is visible | 216 (+459 as 2nd fact) |
| 10 | own strings | `[tag]name`, `name(`, `name:` count as a name | 577 |
| 11 | error codes | `mov CODE,d0` before 0x7E426D4B / 0x7E579DBF | 283 |
| 12 | MMIO | operands 0x98000000–0x9AFFFFFF | 118 |
| 13 | callback | entry loaded by `mov imm32`, with the store offset and the next call | 629 |
| 14 | callee signatures | 60 services with constant arguments (prm tags with names, CamCommand, TAKE, lens pool, timers, ADC, Oimf …) | 499 |
| 15 | kernel services | Oly* wrappers and the 15d kernel rows | 90 |
| 16 | call graph | single caller / shared helper with named callers, ancestor, callees, RAM state | 1,572 |

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

**8,783 / 8,783 rows have a role (0 blank).** Levels from `stats.py` (A = own specific role: rules 0–13 or a string name; B = partial: callee signatures, kernel services, unnamed strings, or a call-graph role that names a caller or ancestor; C = context only: call graph without a named caller). The same classifier is used before and after:

| Level | D4 TSV | D5 TSV |
|---|---|---|
| A specific | 4,209 (47.9 %) | **6,246 (71.1 %)** |
| B partial | 3,859 (43.9 %) | 2,200 (25.0 %) |
| C context only | 715 (8.1 %) | 337 (3.8 %) |

- Of the 6,246 A rows, 2,029 come from D5 reads (256 of them I: mainly the C-AF/IAF engine bodies in af1/af2, labelled from strings and callees) and 216 from the leaf summary (a mechanical, but true, description).
- Level-A share per component, D4 → D5: DCF 21 → 100 %, FAT 23 → 100 %, DPOF 11 → 100 %, file wrapper/VFS 27 → 100 %, EYEFI/FILECLBK/shells 38 → 100 %, AF 25 → 100 %, BBM/STL 31 → 100 %, ADCONV 22 → 100 %, accelerometer 21 → 100 %, IOE 60 → 100 %, strobe exposure 41 → 100 %, strobe module 51 → 100 %, prm 17 → 100 %, USR_FAST_APP 9 → 100 %, UI input 44 → 100 %, UI LED/OUT 41 → 100 %. Lowest now: MEC request decoders 33 %, S_SHELL dumpers 35 %, kernel internals 36 %, SD host driver 42 %, WB 45 %, TakeFcs 48 %, IMG 50 %, lens 52 %.
- V/I: 8,409 rows V, 374 I.
- **Diff against the D4 TSV:** 3,260 rows changed role (2,249 changed primary rule); level moves B → A 1,687, C → A 352, C → B 26, A → B 2 (thunks that store through a pointer). 10 changed rows were checked against the code (0x7E5B05F6, 0x7E5AE5F1, 0x7E5B936B, 0x7E608F69, 0x7E558021, 0x7E509609, 0x7E508FD6, 0x7E5C8891, 0x7E5C5439, 0x7E456200): all true; 0x7E608F69 and 0x7E610129 are I as marked.

## 5. Measured accuracy

A row counts as an **error** when its role states something false (vague but true rows are not errors; see the levels).
- **Sample 1** (`sample.py` seed 5150, build before the rule fixes): **2 / 30 = 6.7 %.**
  - 0x7E548A62 was "slot 0 and slot 6 of table 0x7E747314"; it is slot 1 and slot 8 (the word at 0x7E747314 is 0x7E548941). Cause: the slot number was the position in the run of function words, which skips words that are not function starts. **Rule fixed** (slot = (word − base) / stride); 158 rows changed text.
  - 0x7E46C246 had "calls 0x7E46C20C with d0=1, d0=10"; d0 = 1 is stored to 0x6041A464 first, only d0 = 10 is the argument. **Rule fixed** (absolute stores are reported, overwritten registers dropped, stores through `(off,aN)` end the thunk shape).
- **Sample 2** (seed 9090, final build, 30 fresh rows): **0 / 30.** D5 rows checked in the code: 0x7E50F6AB, 0x7E454305, 0x7E5AEE53, 0x7E5F3F6E, 0x7E502DD6, 0x7E5BFE19; mechanical rows: 0x7E528FDF and 0x7E461C81 (table bytes), 0x7E511171 (`close` in 0x7E73616C), 0x7E55F0E3, 0x7E512F7C, 0x7E50578B. Levels in the sample: 22 A, 5 B, 3 C.
- **Combined after the fixes: 0 / 30 (< 5 %).** Cross-check: the fat and dpof reads overlap on 15 rows (0x7E5BE156–0x7E5BE7A1) and agree on all of them; the fat and eyefi reads give the same FAT/FILE op names.

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

## 7. Known rule errors and limits

Fixed in D5 (rules, with the TSV regenerated): (a) FS heap pair named as request alloc/submit; (b) prm get/set2 names; (c) data-word slot numbering; (d) thunk rule reading stores as arguments; (e) section anchors citing the 16x indexes themselves; (f) curated short names (e.g. `key-matrix scan`) winning over newer reads in caller references.

Still open:
- **Callback rule (13):** any function whose address is loaded by `mov imm32` is called a callback. Most are, but a task entry or a table seed reads the same; the "next call" names the consumer, not the event.
- **Curated rows not re-read in D5** (586 primary) can still hold old errors; D5 found more than 20 of them in the platform range (§6).
- **I rows:** 256 D5 rows are I, mostly the large C-AF/IAF engine bodies (0x7E5F41B1, 0x7E604068, 0x7E605F6C, 0x7E607180, 0x7E612316, 0x7E614C8F, 0x7E616F61, 0x7E618502) and float helpers.
- **Leaf summary** shows first-pass values inside loops and does not track stack arguments beyond `stack(+off)`.
- **Context-only rows:** 2,537 rows are B/C, mainly in IMG, lens, TAKE, BC and the kernel (not targeted in this cycle).

## 8. How to classify a new function in this range

1. Look it up in the TSV (component, role, rule).
2. For an extra start inside a row, use that row and the signatures in §2.
3. A function that allocates from 0x7E5C8497, fills +4 and calls 0x7E5B6233/0x7E5BB51A/0x7E5CBA12 issues the FS op named in §2 for that class/op.
4. A callback row with a `next call` is a completion or event callback for that service (lens submit 0x7E51F98E → req+4; MEC 0x7E512AE0/0x7E512A57; CamCommand 0x7E628303 → +40/+44; SC_TTIMER 0x7E506FF6 / tmr_start 0x7E4650A2 → timer).

## 9. Open questions

1. What runs at 0x7E401400 (below block 0), the flash service used by the BML/STL API when 0x600011DC is 0.
2. FS media ops 9/13/14 and whether op 2 (ALLOW) is a real unmount; the SD driver command meanings (cmd 2/3/4/10/13/14) are I.
3. dcfnum cmd 6 name; DCF drive ids 2–6 (0x7E5B2092, 0x7E5B0FF5); prm 0x4091, 0x85C1, 0x8A41, 0x36C1.
4. The C-AF phase codes 0x1D00, 0x1D20, 0x1500, 0x1F00, 0x2706 and the time unit of 0x7E626E79.
5. The prm element-size rules: layout from tag & 3 but typed get/set from tag & 7; whether any tag hits the mismatch.
6. 0x7E45D444 ("backup-register write"): the UI code uses its d0 as the power-key state byte; recheck.
7. Strobe req+83 values 3/5 (RC level selector) and the area statistics in 0x7E5D7471/0x7E5D7828/0x7E5D70E9/0x7E5D893D.
