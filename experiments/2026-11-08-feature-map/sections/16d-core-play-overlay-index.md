# 16d. Camera core, playback/audio/Bluetooth and overlays A/B: generated per-function index

Round D6, cycle 2 (2026-11-09; builds on D5). **This round is about precision, not coverage:** every rule with more than 50 rows was sampled against the code, wrong rules were fixed or demoted, and the share of specific rows went down where a rule could not be trusted. Scope: block 0 of E-PM2 v1.6, three ranges:
- camera core, movie, rec, face: 0x7E6211E1–0x7E731584 (8,935 functions);
- playback, audio, Bluetooth: 0x7E8F5800–0x7E965FD0 (2,486 functions);
- overlays A and B, code parts: 0x7F05C000–0x7F0F0000 (2,273 functions).

The 65 functions with `data_page` = 1 or `suspect` = 1 are skipped. CapImg and OlyHfwLowApiWrap are outside these ranges (16a rows); only the Apical code is here.

- **Labels:** (V) = read in code or bytes; (I) = inferred. **In the TSV, a row marked I starts with "probably"**: it comes from a demoted rule (§4.2) and is a hedged reading, not a checked fact.
- **Index file:** `16d-core-play-overlay-index.tsv`, **one row per function, 13,694 rows**. Columns: `addr`, `size`, `role`, `basis` (rule or table), `V/I`, `class` (S = specific role, P = specific facts only, C = context only), `component` (smallest named range, §1).
- **Scratch:** `$S/d6/core/` (copied from `$S/d5/core/`; paths point to d6). Run with `python3 -I`, in this order:
  1. `db.py`, `ment.py`, `ranges.py`, `strnames.py`, `ptab2.py`, `immref.py`, `shells.py` (as in D5; D6 changed `strnames.py`, so re-run it);
  2. D6 does not run `cb/cbfix.py` (the 15b TSV is not edited in D6);
  3. `cat roles_head.py roles_main.py > roles2.py; python3 -I roles2.py` → `index.tsv`;
  4. `measure.py` (class shares against the D5 TSV `pub_d5.tsv`), `final_stats.py` (rows, V/I and class per rule group, `rgrp.py`), `prec.py` (checks and errors per rule group and round).
- **Samples and verdicts:** `v6/batch{A,B,C,D}N.tsv` (rows as sampled) and `v6/res*.tsv` (verdicts, one line per row, with the instruction addresses). Instructions to the readers: `v6/VERIFY.md`.
- **Hand and decode inputs:** `comps_hand.tsv`, `hand.tsv`, `handnames.tsv` (D4); `hand_d5.tsv` (D5, with 9 D6 rows marked "D6"), and the decode files `exp/hand_exp.tsv` (872 rows), `bt/hand_bt.tsv` (284), `mcon/hand_mcon.tsv` (698). Their tables and signatures are in `exp|bt|mcon/notes.md`.

## 1. Area and boundaries

D4 boundaries stand (camera core 15b §1; HDMI/CEC, Blue SDK, overlay A 15d; mcon 13e; playback 05; ADJ 01 §7; `fsc_drv` ends 0x7E962FE8; user shell from 0x7E962FE9). New or changed in D5:

| Range | Component | Basis |
|---|---|---|
| 0x7F09AE11–0x7F09CB95 | USB device-controller core (MMIO 0x98F00000): EP0 state machine, endpoint FIFO/DMA, ISR 0x7F09C2E6 and the endpoint services (§2.3). Not "usb_dc4 vendor requests" | V: 13f, code |
| 0x7F09CDCA–0x7F09CE36 | PC_USBPNP task only (`usbpnp_que_read`) | V: tasks.tsv, strings |
| 0x7F09CE37–0x7F09D366 | C3D bridge tasks `C3D_BRG_CPU0L/CPU0P/CPU1L/CPU1P` (queue relays, errors 0x3600xxxx) | V: log tags |
| 0x7F09D367–0x7F09D8DA | C3D scene objects (`Gr_Room_A`; errors 0x36003xxx) | V callers; role I |
| 0x7F09D8DB–0x7F09E2FE | `c3d` shell and BMP loader (`c3d_dbg` 0x7F09DA0E, `Pho%02d.bmp`) | V |
| 0x7F09E2FF–0x7F0A30A9 | C3D scene code (start 0x7F09E9EE, init 0x7F0A13F9, teardown 0x7F09EAAC; 14a §3, 08) | V |
| 0x7E68F07C–0x7E6A935C | EXP_MOVIE, split into API/accel, aeval 0x1302, BV grid and metering, movie program line, task loop, shell, flicker, lights, lock/once/through loops (`exp/notes.md` §4) | V |
| 0x7E6FCA60–0x7E70787F | mcon, split into veneers, shell, engine, conflict engine proper 0x7E7002E4–0x7E70098E, hooks, plane accessors 0x7E704B75/8E/AA, W-plane hook copies, value-list engine 0x7E706FA3– (`mcon/notes.md`) | V |
| 0x7E92BA80 | OBEX client API starts here, so Blue SDK SEC ends at 0x7E92BA7F (not 0x7E92BF5D) | V: call edges |
| ~0x7E9362F5 | SPP starts here (calls RFCOMM register/open); SDP ends 0x7E9362F4 (not 0x7E936A47) | I |

## 2. Components and decoded tables (D5; D6 additions in §2.6)

The D4 tables still hold: the EFFECT/EFFECT_EXE bit map, the U_SHELL family table 0x7E7332B4 and its copy 0x7E7326A4, the three shell idioms and the level-gated loggers.

**2.1 Still and live-bulb modules (cam_still_func.c / cam_still_live_bulb.c; V).** These rows replace the 15b "callback" rule (§3 C1).
- **Module API:**
  - still: init 0x7E656D91 (STLSEM, pool `STILL`), open 0x7E656E00 (open count 0x6056EB5C; first open → pool takes 0x7E65C639, then the sub-module opens 0x7E65C951), close 0x7E656E86, command filter 0x7E656EEB;
  - live bulb: init 0x7E65DAC7, open 0x7E65DB3D, close 0x7E65DBCF, filter 0x7E65DC34;
  - callers: the camera-core module init/open/close/command fan-outs 0x7E656643/0x7E656664/0x7E6566C1/0x7E656730.
- **Open/close chains:** 0x7E65C951 calls the opens of cam_set (×25 requests), MI, shutter, aperture (×11), strobe and lens; 0x7E65CB12 calls the matching closes; live-bulb twins 0x7E660ED1/0x7E661096.
- **State machines:**
  - still: table 0x7E7BD480, 96 B per status, 8-B cells {handler, u16 next status}. 0x7E65D6E6 runs the cell for event column d0; 0x7E65D71E moves to the next status (0 or ≥ 25 → damage 15492).
  - live bulb: table 0x7E7BF220, 88 B per status, status 0x6056ED14; runner 0x7E661AAB, next status 0x7E661AE3.
- **Step events:** posters 0x7E65D41A / 0x7E6617F4 (d0 = bit; cam.c's factor table 0x7E7ABF20 does not name these bits (03 §1 scope note), so D6 rows give only the bit value); matchers 0x7E65D497 / 0x7E661851 call the per-step functions of the matching phase request.
- **Senders** (one-callee wrappers, many callers): to cam_set 0x7E65D1FD, MI 0x7E65D248, shutter 0x7E65D276, aperture 0x7E65D338, lens 0x7E65D3B2; delayed step 0x7E65D3E6 (d1 ≠ 0 → cam_timer 0x7E66260A, else call a1). On failure each one stores the module error (0x7E65D756/0x7E661B1B) and reports damage with a source-line tag (0x7E65D9A6/0x7E661CFF).

**2.2 BASIC (overlay A; V).**
- **Command table** 0x7F069338: {char *name, u32 token, fn}, 12 B per row, 28 rows. The last 6 (`to`, `abs(`, `rand(`, `getkey(`, `api(`, `sctm(`) have token −1 and fn 0.
- **Shared handlers:** `print`/`?` (token 2) → 0x7F05D03C; `if`/`rem`/`'` → 0x7F05CF21; `for`/`next` → 0x7F05D0C7.
- **Statement dispatcher** `do_cmd` 0x7F05CA09: keyword index from 0x7F05CAA0, then calls fn(d0 = token).
- **Parser functions** are named by their own error text (I for the name): `skipEOS`, `checkEOS`, `var`, `vatTestSkip`, `expr_222`, `srch_eq`, `expr_x`, `term` 0x7F05D73C; stack pop/push 0x7F05D3BB/0x7F05D3FA.

**2.3 USB device interrupt chain (overlay B; V).**
- **ISR** 0x7F09C2E6 (attached at 0x7F098C49): saves and restores the endpoint select 0x98F0101C around the decoder 0x7F09C300.
- **Bus status** (0x7F09CAC3): 0x98F01004 bit 0x4000/0x8000/0x2000 → events 0x03010004/0x03010001/0x03010002.
- **Endpoint status** (0x7F09CB06, & enable 0x98F01008): bit 1 → EP0 0x7F09C3B0 (EP0 state machine 0x7F09B8E0); bit 8 → EP3 0x7F09C383; bit 2 → EP1 OUT 0x7F09C420; bit 4 → EP2 0x7F09C494.
- **Events** are queued by `intr_que_write` 0x7F09C4F5.

**2.4 ADJSLF engine API (overlay B; V).**
- **Context:** *(0xA06E1720) (0x7F0A8682); status word ctx+0 (0x7F0A8873 get, 0x7F0A885B set).
- **Test records:** start 0x7F0A89F0 (d0 = test id, 284 call sites) → result line ctx+8404 (0x7F0A8ACC/0x7F0A8A91) → finish 0x7F0A8C29 (CSV `"%s","%s",%06u,%08u,%u,%s,"%s"`); pass 0x7F0A8D8C, fail 0x7F0A8D96(error d0).
- **Parameter reader:** next CSV token as int 0x7F0AA025 (983 sites) or double 0x7F0AA056 (570).
- **ADJ operations:** `MDO` 0x7F0A99A4 = op 0x902B (sub-op 15 = U_SHELL command string: `cam poweroff` 0x7F0B90F7, `cam poweron` 0x7F0B90CD); `MDN` 0x7F0A9867 = op 0x9029, `MDI` 0x7F0A98E9 = op 0x902A (`mov 36906,d0` at 0x7F0A9955; 0x9029 is only in MDI's null-buffer log; D6); `SetPrePro` 0x7F0A9AA3 = op 0x900D; `GetCalibData` 0x7F0A9563 = op 0x9006 (wrapper 0x7F0A961B); SetCalibData wrapper 0x7F0A9626; request builder 0x7F0A934B.
- **Card-write check** 0x7F0A8D30 (`MNF99991.JPG`); vsprintf copy 0x7F0CAA0F.

**2.5 Other decodes (V).**
- **`disp` and `art` shells:** {name, fn} tables in `.data`, read from the ROM image (ROM = RAM + 0x1E6304C0).
  - `disp`: RAM 0x602ACCF8, 21 entries (info, duty, gamma, lpf, get, bg, layer, sio, i2c, histogram, crot, hd, buffer, tp, alc, open, close, ContEvf, nora, swivel, EndOfDebug).
  - `art`: {fn, name} at RAM 0x602AE3CC, 11 entries (tsksts, filtlist, temp, debug, switch, frame, disp, tout, off, dump, dbgall).
- **`play` shell:** a strcmp chain: info 0x7E945822, dbglv (inline), yc 0x7E9458DB, load 0x7E945A11.
- **C3D scene:** start 0x7F09E9EE (it calls glSetErrorFuncDMP 0x7EE097F9 with the GL error hook 0x7F09E2FF, EGL up 0x7EE61E35, init 0x7F0A13F9); state-block clear 0x7F09FB84.
- **EXP_MOVIE** (`exp/notes.md`): every message code is named (name table 0x7E7DFF78, printer 0x7E69BB13); the API 0x7E68F0EA posts to queue 0x7E43ECEA and waits on EXP_MOVIE_POST 0x7E43ECEC (the reply queue); task dispatcher 0x7E69AE04 uses hash 0x7E7DD0C4 (0x7E7DD044 when prm 0x36C1 = 1); `exp` is a strcmp chain, info…farea are `exp movie` subcommands and 0x7E7E0078 is only `com N`; 18×18 BV grid → 7-BV metering set 0x605AA494; flicker result 0x605A79DC; movie program line → prm 0x0AFA/0x0B0A/0x0B1A/0x0B2A.
- **Bluetooth** (`bt/notes.md`): L2CAP state machine 0x7E9223DC (table 0x7EBB1EE0, states 0–9), signalling builders by code byte, 18 × 184-B channels (CIDs 0x40–0x51); RFCOMM FCS table 0x7EBB10C8 (CRC-8, reflected 0xE0), 8 DLC state handlers, MCC builders; SDP PDU dispatcher 0x7E934C41 (2/4/6 → 3/5/7).
  - OBEX task: message types 1–7 (2 open, 3 close, 4/5 client send/receive, 6/7 server receive/send). The per-state table is at RAM **0x602AF1B0** (static `.data`): IDLE +4 0x7E93B3FB, +12 0x7E93B439; SERV +12 0x7E93B5DC, +16 0x7E93B64C; CLIE +4 0x7E93B4C1, +8 0x7E93B528. This task frames OBEX over iAP, not over the Blue SDK.
- **mcon** (`mcon/notes.md`): 0x7E6FEA5F is the GUI-value get of info d0, not a record lookup; accessor table 0x7E826D2C (get/set/write × 2 planes; slot 11 = W-plane GUI set entry); op records 0x7E814864 (250 × 60 B, 230 callbacks named by slot and info id); twin-copy pair table 0x7E818C68 (keyed by the value of info 9).
- **Apical:** REC, MOV and PLAY fill the same 53-byte request and run IMG job type 11 (THM2LUM); IMG 0x7E574FBC computes an 8-knot tone curve. "Dynamic range/tone" is I.

**2.6 New in D6 (V).**
- **iAP link callback and command processor** (round7-review2 F021):
  - 0x7E8FF8A0 is `link_callback(flg)`, the callback that 0x7E900560 passes to `cp_init` 0x7E91A2CF (`mov 0x7E8FF8A0,a0; mov 1,d0; call` at 0x7E9007EE). flg = 0 sets up the iAP context 0x605C5EB0 (+906 = 1, command id 56) and calls `iap_cmd_prc`; flg ≠ 0 can post a 16-byte message to queue id 0x7E43EDF4.
  - `iap_cmd_prc` is **0x7E91C673** (the caller prints « iap_cmd_prc error:» after `call 0x7E91C673` at 0x7E8FF914). It switches on ctx byte +906: 1 → 0x7E91C69D, 2 → 0x7E91C9D7, 3 → 0x7E91CB38.
  - 0x7E900560 (3,079 B, switch table 0x7EBAF374, values 1–18) has no name now. Its strings «bt_ctrl_inquiry err», «bt_ctrl_inquiry_cancel error:», «SEC_SetPin error:» … report its callees.
- **ADJSLF spectral tables** (round7-review4 F080; bytes read):
  - 0x7F0DED34–0x7F0E104F: 321 rows of 28 B {u32 wavelength 380…700 nm, 3 doubles} (row 0 = {380, 46.97, 33.46, 40.54}).
  - 0x7F0E1050–0x7F0E7EA7: 321 rows × 11 doubles (88 B).
  - The loader 0x7F0C6FEC (only caller `R_src_white_test` 0x7F0C6059) copies table 1 column by column to three 321-double arrays at a0+31108/+33836/+36564, then copies table 2 (loop `add 88`, `cmp 321`). The meaning of the 3 and 11 columns is not decoded (I: spectral reference data for the `WL_Peak_*ref_BPF%d` white-source test).
  - The GUI exposure-step table 0x7EFE9622 (6-B rows) is outside this index's ranges.
- **Overrides of source rows** (`hand_d5.tsv`, D6 verifier): 0x7E666C98 copies the 20-byte EMS2 state 0x6056F170 *out* to the caller buffer (15b says "clear"); 0x7E65FC9B stores the error first and then posts event 8 (15b had the order reversed); 0x7E92C429 fills an *outgoing* OBEX Body/End-of-Body packet (bt decode had the direction reversed); 0x7E9338F4 is an RFCOMM credit advance, not a modem-status setter.

## 3. The rules (priority order)

A function gets the role of the highest-priority rule that fires; up to two lower rules are appended after `;`. Rows = rows whose primary basis is that rule (D6 index). **D6** marks the changes of this round; §4 has the measured precision of each rule.

| # | Rule (basis value) | Source or signature | Rows | V/I |
|---|---|---|---|---|
| 0 | `hand`, `hand (D5, read in code)` | `hand.tsv`, `hand_d5.tsv`. **D6:** `hand_d5.tsv` rows are demoted to I ("probably: …") except the 9 rows re-read in D6 (V/I contains "D6") | 23 + 132 | V; hand_d5 I (9 V) |
| 0 | `D5 exp/BT/mcon decode` | `exp|bt|mcon/hand_*.tsv`. **D6:** demoted to I ("probably: …"); 6 rows corrected (§2.6, §5) | 872 + 284 + 698 | I (2 BT rows re-read in D6: V) |
| 1 | `15b/15d tsv …` | single-address rows of the 15b/15d TSVs. **D6:** demoted to I ("probably: …"). The step-event names of cam.c's factor table are removed from the still/live-bulb rows (`posts step event 0x10000`, not `0x10000 PRO_EMS`); slot and I rows are no longer ancestor labels | 732 + 328 | I |
| 1 | `tasks.tsv`, `hand name` | task entries; logger, heap and lock names. **D6:** the names of task IDs above 0x84 and of ID 1 are shifted in the name table (01 §1), so those entries are "uITRON task entry (cfg N); the label «X» is probably shifted" (I) and are not ancestor labels (`BOOT_CPU0` 0x7E53A4A4 is the standby task) | 73 + 58 | V (shifted IDs I) |
| 2 | `shell decode` | strcmp chains (shells.py). **D6:** demoted to I and reworded: "probably a `fam … sub` shell subcommand handler (it is called after a string compare with «sub» in F; the full command path is not traced)". Nested shells now show the known path (`obex dmy snd`) or `…` | 159 | I |
| 2 | `shell … (shared callee)`, `U_SHELL table`, `shell table (ptab2)` | as D5 | 18 + 22 + 15 | V |
| 3 | `section name` | backticked identifier next to the address. **D6:** not a name when it is a plain word (`Seikou`), a shell command (`cam`), an all-capital tag (`V_DROP_FLG`, `REC_MAKE_IMAGE`), one of the function's own strings passed to a non-print call (`mov_dsi` → 0x7E44AD02), or an identifier that appears only in the strings of another function (04 gives `sound_chunk_int` to the helper 0x7E6F3E9B; the string is in 0x7E6F3EA4). The quoted section text is no longer appended | 157 | V |
| 3 | `own string (io/brk/call)` | the function's own name string. **D6:** (a) "N error/err/NG/failed/ret/result/status" names a **callee** and is never a name (0x7E8FF8A0 is not `iap_cmd_prc`; 0x7E900560 is not `bt_ctrl_inquiry_cancel`); (b) `[TAG]` in capitals is a trace tag (`[SC_RT]`); (c) `[x] text` is a module tag or a name with a field (`[adj_slf] DispErrInfo`, `[init_memory] top:`), not a name; (d) a function with several different identifier strings gets no name unless the others are parts of it (`api_rec_X` / `X`) or it dominates (≥ 3 uses and 3× each other) | 427 + 73 + 9 | V |
| 3 | `own string (bare)` | a bare identifier string. **D6:** rules (d) above; no bare name when the function also has a `[x] text` string | 810 | V |
| 3 | `ADJSLF constants (D5)` | d0 constants at the ADJSLF API calls. **D6:** MDN = op 0x9029, MDI = op 0x902A (was one "MDN/MDI 0x9029" entry); any other write to d0 kills the constant (0x7F0B7002 recorded test "0"; 0x7F0C2B6B recorded the fail code 3002 as a test) | 83 | V |
| 4 | `callback by consumer (D5)` | code immediate passed in a known register to a known API. **D6:** the cam_sem post-job text no longer says "queued on MI_RES/MI_CLS" (the queue object is a0: CAMLNS, FDRV …) | 233 | V (28 I) |
| 4 | `sec NN line L` | section phrase holding the address. **D6:** worded "probably as a section says (not checked here): “…”" | 489 | I |
| 5 | `jump/hash table` | case → handler. **D6:** (a) the switch value is read from the code: `add -k`, `sub k`, `mov k,dX; sub dX,dN`, `mov -k,dX; add dN,dX`, `inc`, register copies; the bound compares cut the table (§4.3); (b) hash keys compared after an adjustment (`mov -1,d0; add a2,d0` in 0x7E939461) get the real value; (c) the first call of a case arm follows a leading `bra` (0x7E63D3FC branches to the 0x7E63D407 arm; jt.py read the next arm); (d) more than 6 cases are written `…/… (N cases)` | 398 + 42 | V |
| 6 | `data pointer table` | ptab2 runs. **D6:** cut to the certain fact "its address is stored in the data word W". The run start, its length and its "user" were wrong in 8 of 11 checks (runs that start mid-table, {key, fn} hash pairs, users that only compare against the end) | 418 | V |
| 7 | `jump/hash table owner`, `code immediate` | **D6:** owner rows say "contains a jump through switch table(s) T" (a switch is not always a dispatcher: 0x7F08E1F9 decodes hex digits); code-immediate rows say "address loaded as an immediate by F" without the "passed to/stored to" detail (it named the wrong call for 0x7E6AF4B9) | 104 + 625 | V |
| 8 | `shape:*` | byte shapes. **D6:** a struct writer names the base register of each store (`(a0)+0, (a0)+2, (a1)+0 …`; it said "through a pointer" for three pointers) | 1,192 | V |
| 9 | `own strings (gist)` | up to 3 own strings | 970 | V |
| 10 | `features+call graph` | facts + nearest labelled ancestor. **D6:** prm pointer/count getters (0x7E457C52/62) give "gets the storage pointer/count of prm N", not "reads prm N" | 3,438 | V |
| 11 | `call graph (unnamed callers)`, `(no callers)` | as D4 | 789 + 20 | V |

**Ancestor and callee labels ("under X", "calls X", "registered by X"; D6).** A label is used only when it is a name: hand names, library names, task names (not the shifted IDs), section names that pass rule 3, own-string names that pass rule 3, and V rows of the decode files and TSVs that are not slot rows. Not used: log tags (`LENS_MAIN`, `PRE_ACTION_ON`, `CAM_CL`), names from callee error strings (`BT_SrvInitialize`, `bt_sio_sem_get`), I rows (`CEC RX setup`), 15b slot-row text, and string names of functions longer than 1,500 B (`WOB_lens_wait` is one state message of the 4.7 KB 0x7E5F9AED; `g_g_fcs_expse_tv` is a variable that 0x7E5EA6BD prints). Long labels are cut at a word boundary (a cut "infos 6…" read as "info 6"). 0x7E5F8BE4 is labelled "C-AF scan-route decision (16c)", not `SC_RT`.

**Rule C1 (15b callback rows, D5).** The D5 rule (`cb/cbfix.py`) is unchanged: a callback is a function whose address is a code immediate or a data word and that has no direct caller; functions with direct callers are "sequence function, not a callback". In D6 the 15b rows are demoted to I with the other 15b rows, and their step-event names are removed.

**Class P:** a C row that also contains a specific fact after `;` (issues/posts/sends/registers/reads prm/records ADJSLF test …) is P.

## 4. Measured precision and coverage (D6)

### 4.1 Method

- **Readers:** independent agents with the code tools and `v6/VERIFY.md`. Each row gets CORRECT, CONTEXT (true but says nothing about the function), MINOR (one false detail: a number, offset, case value, callee or ancestor name, condition) or WRONG (false role or name). **Errors = MINOR + WRONG.** The reader names the false clause, so each error is traced to the rule that wrote that clause.
- **Rounds:** A = the D5 TSV (40-row baseline + 10 rows per rule; 230 rows); B = after the A fixes (10 per rule, 20 for `features`; 190 rows); C = after the B fixes (10 per fixed rule + 40 fresh rows; 100 rows); D = after the C fixes (10 for the two rules fixed in C + 40 fresh rows; 60 rows). 580 rows in all, no row checked twice.
- **Baseline (round A, 40 random rows of the D5 TSV):** 20 CORRECT, 16 CONTEXT, 4 MINOR, 0 WRONG: **4 / 40 = 10 % errors**, all in V rows (jt slot as case value ×2, the trace tag `LENS_MAIN`, the I label "CEC RX setup" as an ancestor name).

### 4.2 Precision per rule

"A" counts the D5 rows; "B–D" counts the rows of the D6 builds. A rule keeps V only if its checks after its last measured fix have 0 errors in ≥ 10 rows.

| Rule group (basis) | Rows | A: errors / checked | B–D: errors / checked | Errors found (rule that wrote the false clause) | D6 result |
|---|---|---|---|---|---|
| features+call graph | 3,438 | 3 / 10 | 0 / 36 | A: ancestor labels (log tag, I label, `Seikou`) | **V** |
| own strings (gist) | 970 | 3 / 13 | 2 / 25 | A: ancestor labels and a jt slot; B: labels `BOOT_CPU0` (shifted task ID), `WOB_lens_wait`; fixed before C; C–D 0 / 15 | **V** |
| call graph (unnamed/no callers) | 809 | 0 / 12 | 0 / 7 | — | **V** |
| own string (bare) | 810 | 0 / 13 | 0 / 4 | — (made stricter by rule 3d) | **V** |
| code immediate | 625 | 2 / 14 | 1 / 17 | A: wrong "passed to" call, callee-error label; C: callee label `sound_chunk_int` (section name on the wrong address; fixed after C, D 0 / 1) | **V** (last fix not re-sampled) |
| shape:* (not wrapper) | 604 | 0 / 12 | 0 / 3 | (D: struct-writer wording in a jt row; fixed after D) | **V** (last fix not re-sampled) |
| shape:wrapper | 588 | 0 / 12 | 0 / 2 | — | **V** |
| own string (io/brk/call) | 509 | 0 / 1 | 2 / 38 | C: bracket module tags `[adj_slf]`, `[init_memory]`; fixed before D; D 0 / 13 | **V** |
| jump/hash table (case) | 440 | 0 / 1 (8 more jt clauses wrong in other rows) | 3 / 23 | A: slot given as case value (8 clauses); B: case list cut at 6; D: two extra clauses (struct-writer and prm wording; fixed after D) | **V** (last fix not re-sampled) |
| data pointer table | 418 | 8 / 11 | 0 / 10 | A: run start, entry count, table user | **V** (reworded to the data word) |
| jt owner | 104 | 2 / 10 | 1 / 21 | A: jt case values; B: "dispatcher" on a hex decoder; C–D 0 / 11 | **V** (reworded) |
| section name | 157 | 1 / 9 | 1 / 30 | A: section quote appended; B: `mov_dsi` tag; C–D 0 / 20 | **V** |
| callback by consumer | 233 | 4 / 11 | 0 / 10 | A: "queued on MI_RES/MI_CLS", `V_DROP_FLG` label | **V** |
| ADJSLF constants | 83 | 4 / 10 | 0 / 11 | A: MDI op, test id 0, fail code as test id | **V** |
| hand.tsv, hand names, tasks, U_SHELL | 177 | 2 / 10 (hand group) | 3 / 23 (hand group) | C: two truncated addresses «0x605C...» in `handnames.tsv` (fixed; no other truncated entry); task names of shifted IDs | V (I for shifted task IDs) |
| `hand_d5.tsv` | 132 | (in hand group) | (in hand group) | A: "283 call sites" (284); B: «or unknown» in the `play` usage row | **demoted to I** (9 D6 rows V) |
| section text | 489 | 2 / 11 | 2 / 13 | quoted section claims that are false for this function (13b's retracted "+284"; "27-entry" table has 29; "each called once") | I (worded "probably as a section says") |
| shell decode | 159 | 6 / 11 | 1 / 10 | A: wrong command paths (`mov time print`, `obex dmy snd`, `c3d test Q 0`, shared `usb pipeN`) | **demoted to I** |
| 15b TSV | 732 | 2 / 12 | 4 / 12 | "clear" for a copy-out, reversed order, step-event names from the wrong table (×3), slot 54 for slot 55 | **demoted to I** |
| 15d TSV | 328 | 2 / 11 | 2 / 12 | "CEC interrupt enable" for a disable, call order; jt case values | **demoted to I** |
| exp decode | 872 | 1 / 13 | 6 / 15 | "bit 2" for mask 0x02, error code 0x0E000503 for 0x0E000703, offset +12 for +16, returns the state vs a flag, a range start, "clears" vs "sets 32767" | **demoted to I** |
| mcon decode | 698 | 2 / 12 | 5 / 16 | missing source infos, store order, "drive" for "distance", a cut label | **demoted to I** |
| BT decode | 284 | 3 / 10 | 2 / 11 | reversed packet direction, `oacp` for `acp`, "mux closing" for the responder state, `RFCOMM_SetModemStatus` for a credit advance | **demoted to I** (2 re-read rows V) |

**Demoted rows (I, "probably: …"): 3,715** — decode files 1,852, 15b/15d 1,060, `hand_d5` 123, shifted task IDs 4, section text 489, shell 159, callback-by-consumer rows already I in D5 28.

### 4.3 Named rule errors fixed in D6

- **Jump-table case values.** jt.py read only `add -k` before the index. With `mov k,dX; sub dX,dN` or `mov -k,dX; add dN,dX` it gave the slot as the case. 0x7E6AEAD2 covers values 1..27 at value − 1 (0x7E6B6123 is case 17, not 16); 0x7F08D380 / 0x7F08D49B subtract 0x5001 (0x7F08DAE9 is case 0x5013, not 18). 79 linear tables changed base or length (e.g. 0x7E7FF05C starts at 100, 0x7E81004C at 76, 0x7F069F90 at 257, 0x7F06A0F8 at 0x10000001; 0x7E7FDD9C has 9 entries, not 167), and 10 hash tables changed their key offset (0x7E939461: key 127 is value 128 = OBEX CONNECT; 0x7E7FF300 keys + 77; 0x7EBAF3BC keys + 0x04020010).
- **Names from a callee's error string.** 0x7E8FF8A0 is `link_callback`; `iap_cmd_prc` is 0x7E91C673 (§2.6). The same rule removed `bt_ctrl_inquiry_cancel` from the 3 KB switch 0x7E900560, `BT_SrvInitialize` from 0x7E901EAC and `bt_sio_sem_get` from 0x7E912CF8.
- **Trace tags as ancestor names.** `SC_RT` (0x7E62542E row), `LENS_MAIN`, `PRE_ACTION_ON`, `V_DROP_FLG`, `CAM_CL`, `REC_MAKE_IMAGE` and other capital tags are no longer labels. All "under X" labels were listed and sorted by source (989 distinct labels): slot rows, I rows, shifted task names, long-function string names and capital section names were removed.
- **Names on large switch functions.** Rule 3d: a function with several different identifier strings gets no name (114 functions; e.g. the 5.5 KB `bt` shell 0x7E9035A8 was `sio_read_start`, the 1.6 KB 0x7E6E59CB was `AVSCA_SetVideoParam`).

### 4.4 Final check (fresh rows)

Two fresh random samples of 40 rows, drawn after rounds B and C fixes, rows never checked before:

| Sample | V rows: errors / rows | I rows: errors / rows | Errors in V rows (fixed after the sample) |
|---|---|---|---|
| round C (seed FINAL-D6) | 2 / 31 | 3 / 9 | `[adj_slf]` bracket tag as a name (WRONG); callee label `sound_chunk_int` at the wrong address |
| round D (seed FINAL2-D6) | 2 / 29 | 2 / 11 | "6 fields through a pointer" (three pointers); "reads prm 0xC202" (the code writes it through the prm pointer getter) |
| **both** | **4 / 60 = 6.7 %** | **5 / 20 = 25 %** | |

**The target (0 wrong among V rows) is not met.** All 4 V-row errors were minor or wrong details in a clause, each traced to a rule and fixed after its sample (bracket tags, string-owner check for section names, struct-writer wording, prm pointer wording). No sample was drawn after these last fixes, so **no post-fix rate is claimed**. The I rows ("probably") carry the demoted rules; their measured detail-error rate is 25 % in the fresh samples and 3–40 % per source in §4.2.

### 4.5 Coverage

**13,694 / 13,694 rows have a role.** Shares by class, D5 → D6:

| Range | Rows | S: D5 → D6 | of which V / I in D6 | P: D5 → D6 | C: D5 → D6 |
|---|---|---|---|---|---|
| camera core / movie / rec / face | 8,935 | 4,778 (53 %) → 4,684 (52 %) | 1,931 (22 %) / 2,753 (31 %) | 1,034 (12 %) → 1,049 (12 %) | 3,123 (35 %) → 3,202 (36 %) |
| playback / audio / BT | 2,486 | 1,265 (51 %) → 1,197 (48 %) | 609 (24 %) / 588 (24 %) | 103 (4 %) → 126 (5 %) | 1,118 (45 %) → 1,163 (47 %) |
| overlays A + B | 2,273 | 950 (42 %) → 887 (39 %) | 534 (23 %) / 353 (16 %) | 253 (11 %) → 252 (11 %) | 1,070 (47 %) → 1,134 (50 %) |
| **all** | **13,694** | **6,993 (51 %) → 6,768 (49 %)** | **3,074 (22 %) / 3,694 (27 %)** | **1,390 (10 %) → 1,427 (10 %)** | **5,311 (39 %) → 5,499 (40 %)** |

- **Final shares:** specific 49 % (V 22 %, hedged I 27 %), partial (P) 10 %, context only (C) 40 %. Of the 13,694 rows, 9,979 are V and 3,715 are I.
- **Diff against the D5 TSV:** 8,629 rows changed text. Most changes are ancestor labels, the data-word rewording (418 rows), the "probably" prefix (3,715 rows) and corrected case values. Class moves: S→C 169, S→P 55, P→C 24, C→S 5, P→S 3.
- **D5 history (kept for reference):** D5 measured 15 / 120 errors (12.5 %) on four 30-row samples before its own fixes; the last two gave 3 / 30 each.

## 5. Corrections to earlier sections

**New in D6 (V, from the D6 readers; the other sections are not edited here):**
- **05 / 15d / 16d D5:** 0x7E8FF8A0 is `link_callback(flg)`, and `iap_cmd_prc` is 0x7E91C673 (§2.6). 0x7E900560 is not `bt_ctrl_inquiry_cancel`.
- **15b TSV:** 0x7E666C98 copies the EMS2 state *out* (memcpy 0x7E500D33), it does not clear it. 0x7E65FC9B stores the error before it posts event 8. The still/live-bulb rows name step-event bits with cam.c's factor table (`AE_FPN`, `PRO_EMS`, `MEC_APERTURE_START` …), which 03 §1 says does not name them. Slot rows taken from 0x7E7AF27C miss the leading `bra` of some arms (0x7E7AF27C[54] goes to the 0x7E63D5CB arm; only slot 55 = value 58 calls 0x7E63D4F8).
- **15d TSV:** 0x7E6ADFE3 is a CEC interrupt *disable* (AND 0xC3 on reg 0x95, reg 0xE2 = 1), not an enable. 0x7E6AC4AF calls 0x7E6AC56F *before* it reads 0x42/0xA1.
- **16d D5 §2.4 (fixed here):** MDI 0x7F0A98E9 sends op 0x902A; 0x7F0A89F0 has 284 call sites.
- **16d D5 §2.1 (fixed here):** the step-event posters take bit values; the AE_START … EXPOSE_INTERVAL names belong to cam.c's factor table only.
- **04 line 229:** `sound_chunk_int` is 0x7E6F3EA4 (it logs «[SOUND] sound_chunk_int»), not the 9-byte helper 0x7E6F3E9B.
- **tasks.tsv / 01 §1:** 0x7E53A4A4 is the standby task (`[pwr_standby]`), not BOOT_CPU0; do not use the name-table labels of IDs above 0x84 as names.
- **bt decode:** RFCOMM mux state 3 is the responder state that waits for SABM after the L2CAP connect is accepted, not "mux closing". The `acp` U_SHELL command (module tag OACP) is not `oacp`.
- **exp/mcon decode (fixed here):** 0x7E69D35F tests mask 0x02 (bit 1); 0x7E70277F reads the pair selected by info 25 (66/565, 67/566, 68/567); 0x7E706756 copies 437 or 438 into 436.

**From D5:**

- **15b TSV (edited here):** the 340 `callback` rows are re-derived (rule C1). 119 of them have direct callers and no pointer reference, so they are not callbacks. They are module init/open/close/filter, state-machine runners, open/close chain steps, request senders and step-event completions (§2.1).
- **15b §5.7 / 12 §1.6:** the EXP codes 0x504 AF_END, 0x50D ONCE_PRE, 0x50E ONCE_RE_CALC and 0x90A/0x90B PRE_ONCE_CONTINUE(_AF) have names. 0x502/0x50A/0x50D/0x50E/0x702/0x801/0x1402 go to 0x7E68F2C1, not 0x7E6904C1. EXP_MOVIE_POST 0x7E43ECEC is the reply queue; the command queue is 0x7E43ECEA (V).
- **03 §7b, 15b, D4 §2:** `exp` is a strcmp chain (info, seq, movie, still, call, all, log, time, 120fps, zoom, aperture); 0x7E7E0078 is `exp movie com N` only. The `[exp]:apical` dump prints face/AF-area data, so the "Apical = DR control" guess is not supported there (V).
- **coverage/round6-review2 F022 and 05 §4:** the OBEX per-state table is at 0x602AF1B0 (immediate 1613427120), not 0x602B4BB0. It is static `.data` (ROM 0x7E8DF670) (V).
- **15d / 05:** OBEX starts at 0x7E92BA80, so SEC ends at 0x7E92BA7F (V). SPP starts at about 0x7E9362F5 (I). 15d's "SABM-state strings 0x7E93101B–0x7E9315FD" are the 8 RFCOMM DLC state handlers (V).
- **13e:** 0x7E6FEA5F returns the GUI value of info d0. 16d D4 rows "looks up mcon value-table record N" are now "reads the mcon GUI value of info N". The W plane has two arrays, 0x605A38E0 and 0x605A4A18. The 91/133 … pairs are keyed by the value of info 9, not still/movie twins. The override slots 0x605B4C1C are never filled in v1.6 (V; `mcon/notes.md`).
- **10f:** 0x7F0A8912 is not `UnitCodeCam` (that is the step 0x7F0B8D18). 0x7F0A8912 reads calib tag 0x00ED (20 B) and sets tag 0x8072 (V, rule 3).
- **14a / D4 16d:** 0x7F09E9EE is the C3D scene start, which calls glSetErrorFuncDMP. 0x7F09E2FF is the GL error hook, not glGetError (V).
- **D4 16d component labels:** 0x7F09C420 and its siblings are the USB device ISR/endpoint layer, not "usb_dc4 vendor requests". 0x7F0B90F7 copies a string (`cam poweroff`), not a table (V).
- **D4 16d open question 6:** the `play`, `disp` and `art` shells are decoded (§2.5).

## 6. Open questions

1. Cam-core string-less leaf code (cam_param/pfp/port/prepro/rap.c, cam_*.c aedrv…frame_sync, fcs/AF tail): mostly register-block initialisers and prm readers. They need the per-register meanings (sensor/AFE blocks) to get specific roles.
2. Movie (`mov*.c`, 971 rows, ~40 % S): the movp pointer table 0x7E80C830 (77 pointers, stride 8; state × event layout I) is not decoded.
3. ADJSLF steps: the step list of the sequence dispatcher 0x7F0AAD2B (word 0x7E8F2124) is still not decoded. Test ids give 85 rows, but most step bodies are float maths with no test call.
4. The effect names of EFFECT types 6, 10, 11, 27–30; which of 29/30 is slide and which is scroll.
5. The OBEX core PUT/GET handler names and many RFCOMM user-event names are I (`bt/notes.md`).
6. 0x7EE02095–0x7EECE318 (GL, 3D engine, C3D framework, AVPI) is still outside every 16x index.
7. **(D6)** The demoted sources (exp/BT/mcon decode files, 15b/15d TSV rows, `hand_d5.tsv`) return to V only when each row is re-read, or when a new sample of ≥ 10 rows per source has 0 errors. The D6 readers' evidence columns (`v6/res*.tsv`) hold corrected roles for about 60 rows that are still C or I (e.g. 0x7F08E1F9 hex-digit decoder, 0x7F0A370D strlen, 0x7E6E4E41 the `mov meminfo` printer, 0x7F08D2CA nibble → ASCII).


## Known rule errors

Fixed in D6 (removed from this list): jt slot used as the case value (linear and hash switches) and the leading-`bra` case arms; names from callee error strings; trace and log tags as names or ancestor labels; names on functions with several identifier strings (switches, shells); shifted task names; section names that are tags, plain words, arguments or another function's string; pointer-table run starts, lengths and users; "passed to" details of code immediates; cam_sem "MI_RES/MI_CLS"; ADJSLF MDI op and lost d0 constants; step-event names on still/live-bulb rows; "dispatcher" on any switch; struct-writer and prm-pointer wording; cut labels.

Still open:
- **Fixes made after the last sample are not measured:** bracket tags, the string-owner check for section names, struct-writer wording, prm-pointer wording and cut labels (§4.4). The last two fresh samples gave 4 errors in 60 V rows (6.7 %), all fixed after.
- **Demoted rules ("probably", I; 3,715 rows):** decode files, 15b/15d TSV rows, `hand_d5.tsv`, section text and shell paths. They hold real readings, but 3–40 % of their checked rows had one wrong detail (offset, error code, condition order, direction, command path). Use them as leads, not facts.
- **"Under X" context** is a location (nearest labelled ancestor within 3 levels), not a role. Labels are now names only, but an ancestor's own row may still be I.
- **Case lists** show the cases whose arm calls the function first. A function that a case reaches later, or through shared code, is not listed; the "(N cases)" form cuts lists over 6.
- **Wrapper/shape rows describe the body, not the purpose** ("returns 900", "6 stores (a0)+0 …"). They are true but are not roles.
- **Context-only rows are 40 %.** The readers found a role in many of them (hex-digit decoder 0x7F08E1F9, NULL-safe strlen 0x7F0A370D, iSDIO command writer 0x7F0A4C3A, OBEX packet builder 0x7E92C429); those roles need code reading, not rules.
- **The function map splits some case arms into separate functions** (0x7E913DD6, 0x7F08A18B, 0x7F08A1E7 are arms of their switch, not functions); their rows describe the arm.
