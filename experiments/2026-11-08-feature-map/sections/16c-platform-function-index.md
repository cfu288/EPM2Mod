# 16c. Platform, drivers and libraries 0x7E421020–0x7E6211E0: generated function index (E-PM2 v1.6, round D4)

Round D4. Scope: block 0 from the reset entry 0x7E421020 to the end of the fcs function 0x7E620C6F (0x7E6211E0). This covers boot, the kernel, the drivers, the C runtime and `sc` library, UI input, MEC, lens, power, BC, firmup, the IMG library, `buff`, WB, TAKE, the file system, strobe and AF.

- **Labels:** **V** = read in the code or the bytes. **I** = inferred from names, order, layout or call position.
- **Index:** `16c-platform-function-index.tsv`. It has one row for each of the **8,783** database functions in the range (build/map, functions.tsv; the 7 `data_page` rows and 22 `suspect` rows are left out). Columns: `addr`, `size`, `component` (component `>` family), `role`, `basis`, `V/I`.
- **Scripts** in `$S/d4/plat/` (run with `python3 -I`):
  - `mkidx.py` builds the TSV;
  - `lib.py` and `feat.py` load the database and pull out the operands;
  - `anchors.py` collects the roles that the older sections give;
  - `comps.py` holds the component ranges;
  - `curated.py` holds the roles taken from the sections, the names, the MMIO units, the error families and the callee signatures;
  - `q.py ADDR…` is a quick reader;
  - `sample1–3.txt` are the accuracy samples.

## 1. Area and boundaries

The component ranges are in `comps.py`. Each component starts at the first function that has its anchor (a register, string, table or caller) and runs to the start of the next component. The TSV `component` column gives this range and, where the sections give a smaller block, a family after `>` (`curated.py` SUBS: 60 families in IMG, lens, BC, TAKE, MEC, files, strobe and AF). Component membership is **I** where only position supports it. The D4 changes to the old boundaries:

| Range | Component | Basis |
|---|---|---|
| 0x7E4C8E40–~0x7E4C9000 | **Code, not driver-table data:** FLSH flash helpers. 0x7E4C8E40 has the callers CPU0 init 0x7E421115, flash write 0x7E44F197 and 0x7E44F3D0. 0x7E4C8E52 (`ARIENAI`) has the only caller BML erase 0x7E4519C5 | V (callers) |
| 0x7E5AB878–0x7E5ABE5A | **Eye-Fi device/request layer**: open or write a REQM/REQC/RSPC device file (`Failed to open REQM device at: %s`, `Request timed out...`). It sits between the TAKE sequencer (ends 0x7E5AB877) and Eye-Fi card control 0x7E5ABE5B | V (strings; caller 0x7E5ABE5B) |
| 0x7E5BE823 → | **DPOF starts here**, not at 0x7E5BEEAE. 0x7E5BE823 calls the dpofnode functions 0x7E5BF396, 0x7E5BF403 and 0x7E5BF415. 0x7E5BEB99 (← 0x7E5BEAE9) feeds the DPOF request builder 0x7E5BF77E | V edges; start I |
| 0x7E5E2988 → 0x7E6211E0 | **AF / FCS** starts at 0x7E5E2988 (only caller Usr0; it calls the FCS functions 0x7E610887 and 0x7E611D3A). 0x7E5E28D8–0x7E5E2987 are still strobe helpers (callers stbd and TAKE). 0x7E5E29CE (`fMS/ fME/`) waits for the FCS lens flag 0x7E611E49 | V edges |
| 0x7E5704ED–0x7E57302C | IMG **step-list runner 0x7E5705F2 and step functions** (table 0x7E78D0B0). This is not part of the op-type builders 0x7E57302D–0x7E574EE7 | V (table, loop) |

All other ranges are unchanged from the regions table, 01, 13a, 13f, 14b, 15b §1 and 15d §5.

## 2. How the index is built (rules, in priority order)

`mkidx.py` collects every fact it can find for a function. The first fact in the order below is the primary role. Up to two more facts are added after it, then a call-graph context when the role is weak. The `basis` column names the rule of each fact. Names are found in two passes, so that a caller or callee is shown as `0xADDR (name)`.

| # | Rule | Signature / source | Rows (primary) |
|---|---|---|---|
| 1 | **curated** | 622 roles copied from the sections (01, 02, 13a, 13e, 13f, 14b, 15b, 15d, coverage C5) and from D4 reads, with the section cited | 622 |
| 2 | **task** | entries of the CPU0/CPU1 task tables (`fwmap tasks`) | 6 (+60 under curated) |
| 3 | **TAKE tables** | state table 0x7E790860 (27 × {id, name, entry, A, B}); A/B tables {u32 event, fn} up to 0xFFFF; TakeExp 0x7E791478 / TakeFcs 0x7E7928B0 (32 × {key = cmd+1, fn}); the next state from `mov N,d0; call 0x7E5823CC` | 186 |
| 4 | **section anchors** | markdown table rows whose first cell is the address (the role columns found by header: Name/Role/Op/Component/Contents…), rows in the 15b/15d TSVs (their own V/I is kept), and `` `name` 0xADDR `` in prose. Abbreviated rows (`0x7E507F65/F72/F7D/F9A`) are expanded | 269 |
| 5 | **data-word table scan** | every aligned word in rodata (0x7E731588–0x7E8808BF, 0x7E42F020–, 0x7E438BF2–, 0x7E46C458–, `.data` 0x7E880F44–0x7E8F3113) that equals a function start. A run of words is split where code loads an address (imm32, or its `.data` RAM alias −0x1E6304C0). Kinds: {name, fn} (shell tables), {key, fn}, fn arrays | 510 |
| 6 | **linear jump table** | `mov TAB,aN; mov (dX,aN),aN; jmp (aN)` with `add −K,dX` before it. Each case label's first `call` to a callee with ≤ 4 callers is the case handler. Value names are given for MEC submit and FIRMUP_SRV | 177 |
| 7 | **IRQ** | `mov irq,d0; mov lvl,d1; mov H,a0; call 0x7E463C8E/0x7E463C9E` (13f §3.1). The site gets "attaches …" and H gets "ISR for IRQ n (device)" | 22 |
| 8 | **shape** (the body up to the first return) | lone `retf`/`ret` = empty; `clr d0; retf` = returns 0; `mov imm,d0/a0; retf` = constant (string, function, RAM); `mov(abs),d0; retf` = global getter; `mov d0,(abs); retf` = setter; `(off,a0)` field getter/setter; `clr d0; movbu d0,(abs); retf` = clear; `f8 fe fc 80 ch … call … ret` = per-channel stub; ≤ 7 instructions with one `call` = wrapper (with the constant arguments); ≤ 6 bytes of `movm`/`add` only = pointer entry of the next start (two-entry rule, 14e) | 1,068 |
| 9 | **own strings** | strings the function loads; `[tag]name`, `name(`, `name:` count as a name | 992 |
| 10 | **error codes** | `mov CODE,d0` before `call 0x7E426D4B` (the error recorder) or 0x7E579DBF (WB); families in §3 | 306 |
| 11 | **MMIO** | operands in 0x98000000–0x9AFFFFFF, mapped to the 13f §2.1 units | 148 |
| 12 | **callback** | the entry is loaded by `mov imm32` in another function. The row records the site, the store (`+off` / RAM) and the next call (for example `stored at +4, next call 0x7E51F98E (lens request submit)` = the done callback of a lens request) | 689 |
| 13 | **callee signatures** | calls to 60 services with constant arguments: prm getval/set with the tag and its `PRM_*` / menu name (07-settings.tsv), Get_CameraInfo id, EXP command, TAKE send/state/event, CamCommand, MEC, lens pool and submit, bc_stab/ssc, scheap, timers, SIO, ADC, Oimf, Oly* | 750 |
| 14 | **kernel services** | callees among the Oly* wrappers 0x7E449004–0x7E449621 and the 67 kernel rows of 15d | 113 |
| 15 | **call graph** | single caller → `helper of 0xC (name)`, plus the nearest named ancestor (BFS up to 4 levels: `under 0xA (name)`). Several callers → `shared helper, n callers (by component)` with named examples, the named callees and the RAM state (absolute 0x60…/0xA0… operands) | 2,925 |

**Recognising the families by bytes (V):**
- MEC sequence step = `mec_alloc` 0x7E51470B, then `mov imm32` of a completion callback in 0x7E518E91–0x7E51BA08, then `calls (0x604F64xx)`. 151 of the 156 steps get a callback or service-call row.
- Lens request builder = `call 0x7E533AB3` (pool alloc, d0 = size) + `call 0x7E51F98E` (submit). The done callback is stored at request +4.
- FCS lens request = the same, + wait 0x7E611E49.
- TAKE camera-core packet = callback stored at +40/+44, then `call 0x7E628303`.
- scheap wrapper = 14 bytes `mov pool,a0|a1; call 0x7E507395|0x7E5073B8; ret`.
- BC class-2 handler = scheap alloc, `mov N,d0; movhu d0,(a2)`, `call 0x7E5410C7`.
- File-system request = `call 0x7E5C8497` (alloc) … `call 0x7E5C856E` (submit). These two have 135 and 133 callers in DCF/FAT/DPOF/EYEFI.

## 3. Tables and code families used

- **Shell tables {name, fn} (V):**
  - U_SHELL 0x7E7332B4 (54 entries) and its copy 0x7E7326A4;
  - `per` 0x7E4C5534 (26);
  - `ui` 0x7E734DEC;
  - the `mec` sub-tables 0x7E736040, 0x7E7360F0, 0x7E73616C and 0x7E7361F0 (dispatcher 0x7E510943);
  - the GIO/EMS shell tables at 0x7E4C57E8–0x7E4C59D0.
- **Dispatch tables (V):**
  - SIO hooks: 0x7E4C82F0 (open), 0x7E4C82FC (write) and 0x7E4C8308 (interrupt side), indexed by the channel mode byte; SIO IRQ tables 0x7E4C8190/0x7E4C8214; timers 0x7E4C8900/0x7E4C8A50; GIO 0x7E4C6328/0x7E4C6A48;
  - IMG: 0x7E789604 (34), **0x7E78D028 (34 entries, ops 0–33; slots 31–33 are 0x7E570740, 0x7E573B7E and 0x7E574C0D)**, **0x7E78D0B0 (41 step functions)**, 0x7E74A3C8 (34), the pixel-defect tables 0x7E789230/70/B0, and the value maps 0x7E78C6F0/0x7E78CE34;
  - TAKE: 0x7E790860 with 0x7E78F530–0x7E7906B8, 0x7E791478/0x7E7928B0, the TAKE_FUNC job table 0x7E7929DC (61, used by 0x7E59556B), and TAKE_FUNC_CP 0x7E792DC8;
  - BC: 0x7E744C90, 0x7E745C74;
  - FIRMUP_SRV 0x7E7469E0; MEC submit 0x7E7379C0; FILECLBK class 1 0x7E797238; the `lens data` dumpers in `.data` 0x7E8DABA4 (RAM 0x602AA6E4, 41 functions);
  - the IMG block-builder-A sub-tables 0x7E747318/0x7E74737C, and `buff` 0x7E78EE44 (40).
- **Error-code families (V, D4 scan of 112 code groups passed to 0x7E426D4B):**
  - The code format is **0xMM00SSNN**: MM = module, SS = sub-module or file, NN = code.
  - MM owners, by the address range of the users:
    - 0x08 buff; 0x0F AF/FCS (0x0F80SS); 0x10 file system (SS 0x11/0x12 logsec area, 0x42 FAT, 0x85–0x95 DCF, 0xC4/0xC5 request layer); 0x12 IMG;
    - **0x14 lens** (SS 0x10 state, 0x20 LENS_MAIN, 0x30 LENS_FLASH, 0x80 FOCUS_LIMIT, 0x90 pool, 0xB0 firmup, 0xD0 class dispatcher, 0xE0 shell, 0xF0 serial, 0x100 sync/sequence (I)); 0x15 MEC; 0x19 per drivers; 0x1C SYSFMEM; 0x1D battery/power;
    - 0x23 strobe; 0x24 strobe exposure; **0x25 TAKE** (SS 0x07 TakeExp, 0x09 TakeFcs, 0x0A TAKE_FUNC, 0x0E TAKE_MAIN); 0x28 UI; 0x2A WB; 0x2D BC; 0x2E dbg.
  - The camera core uses 0x0A_MM_xxxx (14b §0); no 0x0A code is logged in this range.

## 4. Coverage (rows with a role / all rows)

**8,783 / 8,783 rows have a role (0 blank).** The specificity of the roles, measured on the TSV with the classifier in `mkidx.py`:

| Level | Meaning | Rows | Share |
|---|---|---|---|
| A | own specific role (rules 1–12, a callee signature with constants, or a string name) | 4,209 | 47.9 % |
| B | own facts without a name (only its strings or service calls), or a call-graph role that names a caller, an ancestor or examples | 3,387 | 38.6 % |
| C | call-graph role whose callers are all unnamed (it still lists the callee names, the RAM state and the component) | 1,187 | 13.5 % |

The level-A share per component (high to low):
- 97 % MEC sequence steps; 88 % C runtime; 81 % MEC core; 79 % GIO; 76 % sc; 71 % SIO; 61 % TAKE sequencer; 53 % BC;
- 51 % strobe; 50 % TakeExp; 48 % lens and buff; 46 % IMG; 44 % TakeFcs and WB;
- 31 % STL core; 25 % AF; 23 % FAT; 21 % DCF; 17 % prm; **11 % DPOF**.

V/I: 8,653 rows V (the stated facts were read in code or bytes), 130 I (inferred roles; sections marked I). The component and family columns are I where only position supports them.

## 5. Measured accuracy

Three samples of 30 rows were drawn at random (`random.seed` 2026, 99 and 4242; `sample1–3.txt`). Each role was checked against the disassembly, the call edges and the ROM tables (`q.py`, `fwmap fn`); 14 functions were read in full. A row counts as an **error** when its role states something false.
- **Sample 1 (first version): 2 / 30 = 6.7 %.**
  - (a) 0x7E572519 was called "slot 162 of table 0x7E78CE34". The scanner had merged the value map 0x7E78CE34 with the builder table 0x7E78D028 and the step table 0x7E78D0B0. **Fix:** runs are now split where code loads an address. The row now reads "slot 3 of the IMG step-function table 0x7E78D0B0" (V: the word at 0x7E78D0BC; runner 0x7E5705F2, `cmp 41`).
  - (b) a callee was named "SIO open counter" after 13f §2.3. That name is wrong (§6).
- **Samples 2 and 3 (after the fixes): 0 / 60.**
- **Combined: 2 / 90 = 2.2 %. After the fixes: 0 / 60 (< 5 %).**
- Weak rows (level C) are not counted as errors when they are true. A test that counts "too vague to explain" would score lower; see the levels in §4.

## 6. Corrections to older sections

1. **13f §2.3 "Open/close counters 0x7E469C27 / 0x7E469CDF" (V).**
   - 0x7E469C27 is the **SIO client open(a0 config record)**. It masks the channel IRQs per direction flag (0x7E468B97) and calls open/configure 0x7E467EED. Its callers are lens 0x7E5338ED, BC 0x7E53F16E, LCD/EVF/display 0x7E6B1197/0x7E6B33D1/0x7E6B5988 and audio 0x7E94F128/0x7E94F318.
   - 0x7E469CDF is the **SIO client transfer start(a0 request)**. It clears the channel state 0x6041A0DC + 8·ch, stores the request and calls the write dispatcher 0x7E468324 or 0x7E4686E8. It counts nothing.
2. **15d §5 / 01 §5 "lock pair 0x7E4215A2/0x7E4215B6" (V).** Neither function is a lock.
   - 0x7E4215B6 is `mov (0x600011DC),d0; retf`, the getter of a BML/STL mode flag. Its setter is 0x7E4215AD (only caller CPU0 init 0x7E421115).
   - 0x7E4215A2 is `mov 0x7E401400,a1; calls (a1)`. It forwards the request (for example d0 = 0x50004 from STL close 0x7E421D53) to code at **0x7E401400, below block 0** (I: a loader/boot-ROM flash service).
   - The 13 STL/BML API functions take this path when the flag is 0.
3. **13a §3.2 "(a) 0x7E5704ED → table 0x7E78D028 (31 builders)".** The table has **34 entries** (ops 0–33). A separate 41-entry step table 0x7E78D0B0 follows it and is used by 0x7E5705F2 (V bytes).
4. **Region and component edges (§1):**
   - FLSH code 0x7E4C8E40–~0x7E4C9000 lies inside the "ROM driver tables" area;
   - the Eye-Fi device layer is 0x7E5AB878–0x7E5ABE5A;
   - DPOF starts at 0x7E5BE823 (I);
   - AF starts at 0x7E5E2988.
5. **14b §3 / 02:** 0x7E5E2988 is the FCS/AF init (← Usr0). This adds one more Usr0 init that 01 §2 does not list.
6. **C5 review (round 5 review 1) items, now in the TSV (V):**
   - STL core tree (open/mount 0x7E4543B5 → 0x7E454305, map build 0x7E453B45, maintenance 0x7E4544B1, read/write entries 0x7E4546D4/0x7E4546ED, write path 0x7E4551C1 → 0x7E454B13/0x7E454C23/0x7E454F0E → 0x7E454929, recovery 0x7E455A6D; the roles below the entries are I);
   - SIO hook tables;
   - lens pool;
   - the FAT request list (0x7E5B9145/84, 0x7E5B906C);
   - DCF entry lookup 0x7E5AEF8B;
   - DPOF accessors 0x7E5BF264/90/A9;
   - the TAKE CamCommand callbacks (rule 12: 9 callbacks with `next call 0x7E628303`).
   - **Not covered here:** the SPRDRV ops table (0x7E64ABF6) and the cam_param/pfp/port/prepro/rap split (0x7E643933–0x7E64F084). Both are outside this range (the camera core, from 0x7E6211E1).

## 7. How to classify a new function in this range

1. Look it up in the TSV. Its row gives the component, the role and the rule.
2. For a function the database does not have (an extra start inside a row), use the row that contains it and the byte signatures in §2.
3. A row that only has a callback rule (12) and a `next call` is a completion or event callback for that service:
   - lens submit 0x7E51F98E → done callback at req+4;
   - MEC 0x7E512AE0/0x7E512A57 → MEC phase callbacks;
   - CamCommand 0x7E628303 → packet +40 done or +44 event;
   - SC_TTIMER 0x7E506FF6 / tmr_start 0x7E4650A2 → timer callback.

## 8. Open questions

1. What runs at 0x7E401400 (below block 0)? It is the flash service that the BML/STL API calls when the flag 0x600011DC is 0.
2. The meaning of the three SIO channel modes (hook slots 0/1/2 of 0x7E4C82F0/FC/0x7E4C8308).
3. The FAT request command space. Two request executors read req+4 as class << 12 | 12-bit cmd: 0x7E5B6233 (24 callers) and 0x7E5BB51A (46 callers). The command names are not decoded, and DCF/DPOF/FAT stay at 11–23 % level A.
4. The AF/FCS algorithm functions (0x0F80SS sub-ids; trace tags EL1, LE, cR1, BV, Sb, SR0 …) have strings but no names. 25 % of them are level A.
5. The IMG per-unit setters: which engine unit each mask bit drives (13a open question 3).
