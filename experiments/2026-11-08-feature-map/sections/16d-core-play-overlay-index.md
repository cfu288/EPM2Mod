# 16d. Camera core, playback/audio/Bluetooth and overlays A/B: generated per-function index

Round D4 (2026-11-09). Scope: block 0 of E-PM2 v1.6, three ranges:
- camera core, movie, rec, face: 0x7E6211E1–0x7E731584 (8,935 functions);
- playback, audio, Bluetooth: 0x7E8F5800–0x7E965FD0 (2,486 functions);
- overlays A and B, code parts: 0x7F05C000–0x7F0F0000 (2,273 functions).

The database has 65 more functions in these ranges with `data_page` = 1 or `suspect` = 1. They are skipped.

- **Labels:** (V) = read in code or bytes; (I) = inferred.
- **Index file:** `16d-core-play-overlay-index.tsv`. It has **one row per function, 13,694 rows**, and these columns:
  - `addr`, `size`;
  - `role`;
  - `basis`: the rule or table that produced the role;
  - `V/I`;
  - `class`: S = specific role, P = specific facts only, C = context only (§4);
  - `component`: the smallest named range that contains the function (§1).
- **Scratch:** `$S/d4/core/`. Run with `python3 -I` in this order:
  1. `db.py`: loads functions, calls, strings, pointers and the linear disassembly.
  2. `ment.py`: finds section mentions and names.
  3. `ranges.py`: finds the section range rows.
  4. `strnames.py`: finds names in the function's own strings.
  5. `ptab2.py`: decodes data pointer tables.
  6. `immref.py`: finds code immediates that point at functions.
  7. `shells.py`: decodes the debug shells.
  8. `cat roles_head.py roles_main.py > roles2.py; python3 -I roles2.py`: writes `index.tsv`.

  Helper modules: `shape.py`, `feats.py`. Hand inputs: `comps_hand.tsv`, `hand.tsv` and `handnames.tsv`. The jump tables come from the D3 scanner `$S/d3/cam/jt.py`, run on all three ranges (`jt_*.out`).

## 1. Area and boundaries

The components come from three sources, and the most specific range wins:
- the `modules.tsv` file rows;
- every range row of sections 03–15d;
- the hand list `comps_hand.tsv`.

Earlier sections fixed most edges: 15b §1 (camera core), 15d §1/§2.1/§4.1 (HDMI/CEC, Blue SDK layers, overlay A), 13e (mcon), 05 (playback) and 01 §7 (ADJ). Edges new in this round:

| Range | Component | Basis |
|---|---|---|
| 0x7E961C5B–**0x7E962FE8** | `fsc_drv` audio DMA driver (MMIO 0x9A800000; IRQ attach 0x7E962EAD; dispatcher `fsc_drv_iocontrol` 0x7E962F41, jump table 0x7EBCB2F4, cases 1–4, 16, 0x100, 0x300, 0x1000, 0x2000) | V: own string; table |
| **0x7E962FE9**–0x7E965FD0 | user shell. It starts with the U_SHELL `shell` family entry 0x7E962FE9, not at 0x7E9630D4. It holds the command reader 0x7E9630D4 (`Command Error`, `HIST`), the UART line editor (0x7E9633D7…), the Func Select list (0x7E964558), the command window 0x7E9648A8, help 0x7E96429B, and the memory dump/fill/verify commands 0x7E965402/0x7E96570C/0x7E96585E (`-B` 0x7E965965, `-L` 0x7E965AF1) | V: table word, strings |
| 0x7F085270–0x7F0A7CA4 | overlay B, split at the task entries (tasks.tsv): ADJSLF 0x7F087004, SAICAS 0x7F0870D7, DPS_MAIN 0x7F087807, TPC 0x7F088F64, TPC_DATA 0x7F089E59, TPC_LANG 0x7F08AF19, PTPASYNC 0x7F08E6FE, PTPCOM 0x7F08E88C, PC_EVENT 0x7F0969C3, PC_HOSTCOM 0x7F096DB8, PC_I1394/1394PNP 0x7F097DDF/0x7F097E25, PC_USBSRV 0x7F097F43, PC_PTP 0x7F098010, PC_UAM 0x7F098BDA, PC_USB 0x7F098DE5, PC_XXX 0x7F09A66F, PC_USBPNP 0x7F09CDCA, C3D 0x7F0A3E60, SPC_MAIN 0x7F0A7AF7 | entries V; that each module runs from its entry to the next entry is I |
| 0x7F0A7CA5–0x7F0D257C | ADJSLF steps and CSV/test helpers (01 §7). The test-result writer 0x7F0A89F0 has 58 callers; the CSV/status printers are 0x7F0A8DDB (`ST:%04X`/`BC:%04X`), 0x7F0A8ACC and 0x7F0A8A91 | V callers; roles I |

## 2. Components and decoded tables (new in this round)

**EFFECT / EFFECT_EXE bit map (V; answers 05 open question 9 except the names).**
- **How a transition starts.** The EFFECT task 0x7E8F5D04 handles cmd 1 in 0x7E8F6E64. That function reads the effect type byte 0x602AE54E and calls one start stub per type. Each stub sets one bit of the EFFECT_EXE flag (0x7E449030). The stub addresses are below.
- **What runs each frame.** EFFECT_EXE 0x7E8F6A60 waits on the flag 0x7E43EC62 and calls the step function for the bit:

| Type | Start stub | Bit | Frame step |
|---|---|---|---|
| 11 | 0x7E8F7923 | 0x8 | 0x7E8F793D |
| 10 | 0x7E8F7BBE | 0x10 | 0x7E8F7BD8 |
| 27 | 0x7E8F768B | 0x20 | 0x7E8F76A5 |
| 6 | 0x7E8F795F | 0x40 | 0x7E8F7979 |
| 28 | 0x7E8F7C11 | 0x80 | 0x7E8F7C33 |
| 29 | 0x7E8F80A5 (also sets mask 1 of 0x605C22D8) | 0x100 | 0x7E8F80C7; the continue variant is 0x7E8F88F2, used when mask 2 of 0x605C22D8 is set |
| 30 | 0x7E8F8340 (also sets masks 4 and 16) | 0x200 | 0x7E8F8369; the continue variant is 0x7E8F8A89 (mask 8) |

- **Finish.** Bit 0x80000000 = finish: 0x7E8F5DA2 + 0x7E8F7199, then the semaphore 0x7E43EAF0 is signalled.
- **Unknown codes.** Any other type gives error 0x35002004; any other bit gives 0x35002001 (both to the error recorder 0x7E426D4B).
- **Continue start.** Cmd 5 (0x7E8F7090) starts the continue variants: 0x7E8F88D0 for bit 0x100 and 0x7E8F8A60 for bit 0x200.
- **Image jobs.** The image-job routine 0x7E8F733C switches on the same type byte (0x605C22D9) and calls `img_exec` 0x7E544BB5.
- **Inferred.** The two types that have continue variants (29, 30) are the touch-panel slide and scroll (shell `tpslc`/`tpscc`). Which of the two is which, and the names of 6, 10, 11, 27 and 28, are not proven.

**Debug shells in the ranges (V).**
- **Family table.** The U_SHELL family table 0x7E7332B4 holds 54 {name, handler} records. A byte-identical copy of the handler list sits at 0x7E7326A4 (names at +0, handlers at +4). The 15b rows "slot N of fn-pointer table 0x7E7326A8" refer to this copy.
- **Families whose handler is in these ranges:**
  - `shell` 0x7E962FE9, `aud` 0x7E94F735, `cam` 0x7E62EB8E, `bas` 0x7F05DC8B, `res` 0x7E675B1E, `app` 0x7E67811B, `usb` 0x7F09ABD1, `rec` 0x7E710EB9, `exp` 0x7E69B75D;
  - `sdet` 0x7E6637F2, `mov` 0x7E6D15A0, `movp` 0x7E6E3D18, `mdet` 0x7E666EB9, `face` 0x7E6F4D77, `play` 0x7E93EBB5, `movc` 0x7E6D09DE;
  - `bt` 0x7E9035A8, `obex` 0x7E93B9BF, `acp` 0x7E9393BE, `md3d_dmp` 0x7F05E951, `md3d_hi` 0x7F05E8D4, `disp` 0x7E6B1402, `tpc` 0x7F08910E, `efct` 0x7E8F5E9E;
  - `api` 0x7E67816E, `c3d` 0x7F09D8DB, `sync` 0x7E6C1579, `art` 0x7E71C9D4, `spc` 0x7F0A6E59, `mcon` 0x7E6FE1FE.
- **Three dispatch idioms.** `shells.py` decodes all three. The result is one row per subcommand handler: 233 from compare chains and 15 from tables; the `face` table gives 20 rows through `ptab2`.
  - **Compare chain:** `mov STR,a0|a1; call CMP; cmp 0,d0; bne next; … call HANDLER`. CMP is one of `strcmp` 0x7E500DCA, `strncmp` 0x7E500E40, 0x7E50831A or 0x7E44AD02.
  - **Table loop:** `mov TAB,a2; mov (k,a2),a1; call strcmp; … mov (h,a2),a1; calls (a1); add STRIDE,a2; cmp N,dX`. Examples: `aud` 0x7E94F73A uses the 27 × 12-B table 0x7EBBEC7C; `mdet` uses 9 × 12 B at 0x7E7C053C.
  - **Interpreter call:** `mov TAB,a0; mov N,d0; call 0x7E62F0E3`. Example: `cam`, with the 19 {name, handler} records at 0x7E7AC414.
- **Families with no decoded subcommands.** `exp` is a jump table (0x7E7E0078; it has jt rows but no names). `play`, `disp` and `art` were not decoded.

**Level-gated debug loggers (V, read in code).** Each module has 1–5 small wrappers. Each tests a global debug level or mask against d0 and then prints with 0x7E4263E5, 0x7E5064A1 (`%s %s`) or 0x7E50652F/0x7E50658F (str + hex):

| Module | Logger wrappers | Level or mask global |
|---|---|---|
| api | 0x7E678422 (623 callers), 0x7E678447 (1,373 callers) | 0x602AC750/54 |
| art | 0x7E71C634/0x7E71C64D, plus the trace ring 0x7E71CB08 with its code packer 0x7E71CB30 (511 callers each) | |
| playback | 0x7E93ED1C/0x7E93ED30 | byte 0x605D6F3C |
| audio | 0x7E94F781 (mask test), 0x7E9504D9/0x7E95051C | 0x605D86D8 |
| rec | 0x7E710C83 | |
| mov | 0x7E6D13BD/13E0/1406/1429/144F | 0xA07511E0 |
| movp | 0x7E6E5406/0x7E6E547A | 0xA0752468 |

So when a function passes a string to one of these wrappers, the string is the function's own debug text. That is the basis of the own-string rule.

## 3. The rules (priority order) and the signatures they use

A function gets the role of the highest-priority rule that fires. Up to two lower rules are appended after `;`. Counts are rows whose primary basis is that rule.

| # | Rule (basis value) | Source or signature | Rows | V/I |
|---|---|---|---|---|
| 0 | `hand` | `hand.tsv`: the EFFECT rows above | 23 | V |
| 1 | `15b/15d tsv …` | single-address rows; slot and cell rows give their handler | 1,076 | as in the TSV |
| 1 | `tasks.tsv` | task entry, name and cfg id | 76 | V |
| 1 | `hand name` | `handnames.tsv`: the logger wrappers above, heaps (camera heap 0x7E641C2E/0x7E641D60, scheap 0x7E5072ED/FB, large 0x7E507325/33/41/4F), byte-order helpers 0x7E507F72…FC9, BT list utilities, OBEX/BT locks, cam_ev/still/live-bulb posters | 62 | V |
| 2 | `shell …`, `U_SHELL table` | §2 | 274 | V |
| 3 | `section name` | a backticked identifier next to the address in any section; file names are excluded | 237 | V |
| 3 | `own string (io/brk/bare/call)` | the function's own string has its name, in one of these forms: `name In/Out/start/end/ERR/NG`, `[name]`, a bare `name` (module prefix such as `api_`, `play_`, `aud_`, `mov_`, or 2 or more `_`), or `name()`, `name status =`. The name must be used by 3 functions or fewer. Bare all-capital names and `…_ERR` names are written as "log tag", not as the function name | 1,532 | V |
| 4 | `sec NN line L` | the phrase that holds the address in sections 01–15d and in the 15b/15d TSV texts. A table cell that holds only the address gives the whole row. It is dropped when the address comes after `←`/"called by" (a caller list) | 863 | I |
| 5 | `jump/hash table` | case label → first `call` (jt.py); the role is "case K of the switch in OWNER (table T)" | 419 | V |
| 6 | `data pointer table` | runs of `fn` words in ptrs.tsv outside code: stride = most common gap; record name = a string at a fixed offset; owner = code that loads the table base | 528 | V |
| 7 | `jump/hash table owner`, `code immediate` | the function owns a switch table; or its address is loaded by `mov IMM,dN/aN` (then "stored to …" or "passed to X") | 968 | V |
| 8 | `shape:*` | byte shapes (below) | 1,505 | V |
| 9 | `own strings (gist)` | up to 3 of the function's own strings | 971 | V |
| 10 | `features+call graph` | facts read from the code, plus the nearest labelled ancestor within 3 levels ("under X (2 levels up)"); see the list below | 3,963 | V |
| 11 | `call graph (unnamed callers)`, `(no callers)` | "helper called by A (A's own role), B"; orphans | 1,194 | V |

The facts for rule 10:
- constant-argument calls with their meaning:
  - `prm get/set` 0x7E457C75/0x7E457CED with the tag (names and menu labels from 07-settings.tsv);
  - `Get/Set_CameraInfo` with the info id;
  - error codes passed to 0x7E426D4B;
  - HDMI/ch3/CEC register numbers (d1 before 0x7E6AC903/0x7E6AC8E6/0x7E6BA7F9/0x7E6B9B19/2A);
  - templates: cam_set frame command (0x7E651483, d0), set list (0x7E65156C), cam_ev mask post (0x7E63589A, d0/d1), still/live-bulb step post (0x7E65D41A/0x7E6617F4, d0), camera-heap size (0x7E641C2E, d0), `res_read` type, HCI opcode (0x7E925704), PTP op (0x7F08E975), mcon record (0x7E6FEA5F), queue read/write, `img_exec`, lens submit 0x7E51F98E;
- MMIO operands 0x98000000–0x9FFFFFFF;
- soft-float calls;
- `setlb` loops: "block-copy loop from table T" when the loop body is one load through aX, one store through aY and no call;
- named callees.

**Shape signatures (`shape.py`; V):**

| Shape | Instructions (the whole function) | Meaning |
|---|---|---|
| ret-only | one `ret`/`retf` | empty stub |
| ret0 / retconst / retptr | `clr d0` or `mov N,d0` or `mov IMM,a0`, then `ret` | returns a constant |
| getter / fieldget | `mov|movhu|movbu (ABS)|(N,a0),d0|a0; ret` | returns a global or a field |
| setter / setconst | `mov dN|a0,(ABS); ret`, or a constant then the store | sets one global |
| multistore / fieldstore | only `mov/movbu/movhu/clr/ext*` to ≥ 2 absolute or ≥ 2 `(N,aX)` targets, then `ret` | initialiser, struct writer |
| prologue | 3–5 B `movm [..],(sp)` (+ `add -N,sp`) right before the next DB function | pointer entry of that function (15b §3) |
| wrapper / thunk | ≤ 8 instructions, one `call X`, no conditional branch; or a single `jmp/bra X` | the row gives X and the constant d0/d1/a0/a1 |
| tableget | ≤ 7 instructions with `asl`/`udf*`, a 32-bit table immediate, no call | indexed table entry |
| logger | ≤ 14 instructions; a global loaded in the first 3; `cmp`/`and` in the first 5; only calls to known print functions | a level-gated logger (§2) |

## 4. Coverage and measured accuracy

**Coverage (rows with a role / all): 13,694 / 13,694.** 60 rows are orphans with no caller and no pointer found; they get the role "orphan …", so no row is blank.

Classes:
- **S (specific):** a name, a table slot or case with its owner, a shell subcommand, a TSV/hand/task row, a section phrase, or a semantic shape.
- **P (specific facts, purpose not stated):** for example "reads prm 0x0A5A, 0x0A6A" or "issues cam_set frame command 76".
- **C (context only):** callers, callees, features, a slot with no named owner, a callback site, or a string gist.

| Range | Rows | S | P | C |
|---|---|---|---|---|
| camera core / movie / rec / face | 8,935 | 3,641 (41 %) | 916 (10 %) | 4,378 (49 %) |
| playback / audio / BT | 2,486 | 1,052 (42 %) | 63 (3 %) | 1,371 (55 %) |
| overlays A + B | 2,273 | 866 (38 %) | 160 (7 %) | 1,247 (55 %) |
| **all** | **13,694** | **5,559 (41 %)** | **1,139 (8 %)** | **6,996 (51 %)** |

Best components (S share): mdet 100 % (15b TSV), playback engine 81 %, DPS engine 80 %, `api_*` 77 %, art 76 %, TPC services 75 %, OKAO PT 65 %.

Weakest components (S share): RFCOMM 4 %, L2CAP 8 %, ADJSLF 9 %, cam_param/pfp/port/prepro/rap.c 2 % (but 56 % S+P: register-block copy loops and prm reads), cam_*.c aedrv…frame_sync 12 %, BASIC 14 %, mcon 15 %, touch panel 16 %, EXP_MOVIE 21 % (1,124 rows, the largest gap).

**Accuracy (V, by reading the code).** I drew three uniform random samples of 30 rows each, and read each sampled function in `fwmap.py fn --dis` against its row:
- Sample 1 (seed 101, rules v1): 0 false claims.
- Sample 2 (seed 2026, v2): 0 false claims, 1 misleading row. 0x7E9321E8 got the phrase "← RFCOMM 0x7E9321E8 and SDP …", which describes it only as a caller. The `←` filter now looks at the whole phrase before the address.
- Sample 3 (seed 909, v3): 0 false claims, 1 misleading row. 0x7E6DDBE5 was "named" `mov_paint.c` from the modules table. File names are now excluded.

**Measured error rate: 2 / 90 = 2.2 % misleading, 0 / 90 false; both causes are fixed.** The samples' class mix (S 39, P 5, C 46 of 90) matches the whole index.

A C row is a true statement but not a role. Typical C rows:
- "under `api_rec_…` (direct caller)";
- "hardware loop (setlb)";
- "helper called by 0x7E647EDC".

The most common weak pattern in samples 1–3 is a register-block initialiser in cam_param…rap.c. Example: 0x7E646C9B copies 14 halfwords from 0x7E7A..1C to a block at (12,a1)+520, then ORs 0x1000 into a register. The block-copy rule now marks these as P.

## 5. Corrections to earlier sections

- **05 table and §6:**
  - `fsc_drv` ends at 0x7E962FE8, and the user shell starts at 0x7E962FE9, the U_SHELL `shell` family entry (§1).
  - The EFFECT_EXE bit → type → step map is now decoded (§2). 05's "Which bit runs which effect is not mapped" is answered, except for the effect names.
- **U_SHELL table (10f, firmware-map):** there are two identical handler lists, 0x7E7332B4 and 0x7E7326A4 (V, all 54 handlers compared). The 15b "slot N of 0x7E7326A8" rows are the second copy's handler words.
- **The `cam` shell** is table-driven: entry 0x7E62EB8E → interpreter 0x7E62F0E3(a0 table, d0 count) → {name, handler} table 0x7E7AC414, 19 records; unknown → `==> UNKNOWN COMMAND`. **The `aud` shell** 0x7E94F735 → 0x7E94F73A uses a 27 × 12-B table at 0x7EBBEC7C; when argc < 2 or there is no match it calls 0x7E950275 (V).
- **Own-string naming caveat (for all sections):** strings like `REC_APICAL_CALC_UNB`, `HDMI_AV` and `Create_HNDL_ERR` are log tags. 0x7E6FBCB0 is the OKAO handle-create routine, and its `OKAO_Delete*`/`Free*` strings name the OKAO functions it calls on error. Do not read such strings as the function's own name.
- **Pointer-entry prologues:** the shape rule found 9 more 3–5-B DB "functions" that are prologues of the next function. Examples: 0x7E6FF22D (slot 11 of the mcon table 0x7E826D2C) and 0x7E688DA2. This agrees with 15b's database note.
- **The coordinator's "user shell 0x7E9630D4–0x7E965FD0":** 0x7E9630D4 is the command reader inside the shell, not the start of the shell.

## 6. Open questions

1. EXP_MOVIE (1,124 functions) is mostly unnamed AE maths. Its message code names (15b §8 Q6) and the 14 `exp` shell subcommand names (jump table 0x7E7E0078) would let the index name its cases.
2. The Blue SDK interior (L2CAP 139, RFCOMM 96, SDP 74, ME + SEC 204) has few names. The iAnywhere SDK sources would match it by layout (not done: no external code).
3. The names of effect types 6, 10, 11 and 27–30, and the slide/scroll assignment of 29/30.
4. ADJSLF steps: the sequence dispatcher 0x7F0AAD2B (word 0x7E8F2124) runs steps that are selected through CSV block names. A decoder of those step lists would turn the 347 ADJSLF rows into named steps.
5. Cross-body matching (E-PL5 1.6 has the same code family; later bodies keep more strings) could name the C rows. It is not done here: the index uses only E-PM2 data.
6. The `play`, `disp` and `art` shells use another subcommand idiom. They are not decoded yet.

## Known rule errors found by coverage round C6 (2026-11-09)

- **Pool allocators labelled as callbacks:** the 16 rows 0x7E65C6A1–0x7E65C8FB (`STILL` pool) and 0x7E660C21–0x7E660E7B (`S_LB_M` pool) were copied from a 15b rule that turned "immediates before a call" into "step callback". They are start-up pool allocators with one direct caller. Fixed here and in 15b.
- **glSetErrorFuncDMP:** 0x7F09E9EE was named `glSetErrorFuncDMP`; it is the C3D scene start that calls it. Fixed, along with the "under …" rows that inherited the name.
- **The BASIC command table** is {name, token, fn}, starting at 0x7F069338 (F076 = `run`). Rows built from the earlier reading of this table may give the wrong command.
- **Rows that are context only:** overlay-B rows are mostly strings, MMIO and ancestor names. The USB endpoint-1 OUT handler, the ADJSLF helpers (e.g. the `MNF99991.JPG` card-write check; `cam poweroff` via ADJ op 0x902B sub-op 15) and the C3D scene code can be named from 01/13f but are not yet.
- **Not covered:** 0x7EE02095–0x7EECE318 (GL, 3D engine, C3D, AVPI) is outside every 16x index.
