# 16d. Camera core, playback/audio/Bluetooth and overlays A/B: generated per-function index

Round D5, cycle 1 (2026-11-09; builds on D4). Scope: block 0 of E-PM2 v1.6, three ranges:
- camera core, movie, rec, face: 0x7E6211E1–0x7E731584 (8,935 functions);
- playback, audio, Bluetooth: 0x7E8F5800–0x7E965FD0 (2,486 functions);
- overlays A and B, code parts: 0x7F05C000–0x7F0F0000 (2,273 functions).

The 65 functions with `data_page` = 1 or `suspect` = 1 are skipped. CapImg and OlyHfwLowApiWrap are outside these ranges (16a rows); only the Apical code is here.

- **Labels:** (V) = read in code or bytes; (I) = inferred.
- **Index file:** `16d-core-play-overlay-index.tsv`, **one row per function, 13,694 rows**. Columns: `addr`, `size`, `role`, `basis` (rule or table), `V/I`, `class` (S = specific role, P = specific facts only, C = context only), `component` (smallest named range, §1).
- **Scratch:** `$S/d5/core/` (copied from `$S/d4/core/`). Run with `python3 -I`, in this order:
  1. `db.py`, `ment.py`, `ranges.py`, `strnames.py`, `ptab2.py`, `immref.py`, `shells.py` (as in D4; re-run `ment.py` after any section edit);
  2. `cb/cbfix.py OLD15b NEW15b`: re-derives the 15b "callback" rows (rule C1, §3) and writes the fixed 15b TSV;
  3. `cat roles_head.py roles_main.py > roles2.py; python3 -I roles2.py` → `index.tsv`;
  4. `measure.py [seed ch|all n]`: class shares before/after, changed rows, random samples.
- **Hand and decode inputs:** `comps_hand.tsv`, `hand.tsv`, `handnames.tsv` (D4); new in D5: `hand_d5.tsv` (BASIC, USB, C3D, ADJSLF API, `disp`/`art`/`play` shells), and three decode files whose every row was read in code: `exp/hand_exp.tsv` (872 rows), `bt/hand_bt.tsv` (284), `mcon/hand_mcon.tsv` (698). Their tables and signatures are in `exp|bt|mcon/notes.md`.

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

## 2. Components and decoded tables (new in D5)

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
- **Step events:** posters 0x7E65D41A / 0x7E6617F4 (d0 = bit, names AE_START … EXPOSE_INTERVAL); matchers 0x7E65D497 / 0x7E661851 call the per-step functions of the matching phase request.
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
- **Test records:** start 0x7F0A89F0 (d0 = test id, 283 sites) → result line ctx+8404 (0x7F0A8ACC/0x7F0A8A91) → finish 0x7F0A8C29 (CSV `"%s","%s",%06u,%08u,%u,%s,"%s"`); pass 0x7F0A8D8C, fail 0x7F0A8D96(error d0).
- **Parameter reader:** next CSV token as int 0x7F0AA025 (983 sites) or double 0x7F0AA056 (570).
- **ADJ operations:** `MDO` 0x7F0A99A4 = op 0x902B (sub-op 15 = U_SHELL command string: `cam poweroff` 0x7F0B90F7, `cam poweron` 0x7F0B90CD); `MDN`/`MDI` 0x7F0A9867/0x7F0A98E9 = op 0x9029; `SetPrePro` 0x7F0A9AA3 = op 0x900D; `GetCalibData` 0x7F0A9563 = op 0x9006 (wrapper 0x7F0A961B); SetCalibData wrapper 0x7F0A9626; request builder 0x7F0A934B.
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

## 3. The rules (priority order)

A function gets the role of the highest-priority rule that fires; up to two lower rules are appended after `;`. Rows = rows whose primary basis is that rule (final index).

| # | Rule (basis value) | Source or signature | Rows | V/I |
|---|---|---|---|---|
| 0 | `hand`, `hand (D5, read in code)` | `hand.tsv`, `hand_d5.tsv` (D5 adds 7 rows from the verifier's reading) | 148 | V (I parts marked) |
| 0 | `D5 exp/BT/mcon decode` | `exp|bt|mcon/hand_*.tsv`: tables decoded and each function read | 1,854 | per row (V 1,720, I 134) |
| 1 | `15b/15d tsv …` | single-address rows; slot and cell rows give their handler. **D5:** the 15b `callback` rows are re-derived by C1; a row keyed by a list of functions (15d `0x7F0886AD/BE/C7/E4`) no longer gives "slot" roles to the addresses in its text | 1,064 | as in the TSV |
| 1 | `tasks.tsv`, `hand name` | task entries; logger, heap and lock names | 131 | V |
| 2 | `shell …`, `U_SHELL table` | §2 and D4 §2. **D5:** a "handler" with ≥ 2 callers outside the shell is a shared callee of that branch (priority 7, class C; 15 rows; e.g. `isdio_read_register` 0x7F0A4AF4 is not `spc read_enc`) | 196 + 15 | V |
| 3 | `section name` | backticked identifier next to the address. **D5:** when the sections give one name to several addresses, only the address with the most mentions keeps it (fixes glSetErrorFuncDMP 0x7F09E9EE, UnitCodeCam 0x7F0A8912, glGetError 0x7F09E2FF, art_SendRequest 0x7E70E687) | 231 | V |
| 3 | `own string (io/brk/bare/call)` | the function's own name string. **D5:** `…_ERR/_NG/_OK/_END/_START/_IDLE` tags are never names (priority drops to 8, no label); bare all-capital names are labelled "`X` (log tag)"; a bare string whose next call is not a print function is an argument (object name, compare key): "passes the string «X» to F", class P (92 rows, e.g. `CIC_MUTEX` 0x7E8F58B8) | 1,487 | V |
| 3 | `ADJSLF constants (D5)` | d0 constants at the calls 0x7F0A89F0 (test ids), 0x7F0A8D96 (fail codes), 0x7F0A961B/0x7F0A9626 (calib tags, prm names), 0x7F0A99A4 (MDO sub-ops), 0x7F0A9867/0x7F0A98E9; S when it records tests | 85 | V |
| 4 | `callback by consumer (D5)` | a code immediate passed in a known register to a known API: cam_set frame/set-list done (a1 of 0x7E651483/0x7E65156C), imgdev/sg request (a0 of 0x7E638F34/0x7E6390A6), hook list 0x7E6533F7, tmr_start, sio_request, cam_ev arm/set-up, cam_timer 0x7E66260A, cam_sem job (a1 of 0x7E64F10E), PTP op handler (a0 of ptp_register; op = d0 at the call) | 231 | V |
| 4 | `sec NN line L` | section phrase holding the address. **D5:** phrases with `~~`, "first/last function 0x…", "starts at 0x…", the address after "called (directly) by / passed by / stored by / loaded by", the middle of a `A → X → B` chain, an `A / B` pair, or a table cell naming several functions are dropped; `|` inside a backtick span no longer ends a phrase | 459 | I |
| 5 | `jump/hash table` | case → handler (jt.py). **D5:** (a) a target with ≥ 2 callers outside the switch is a shared callee ("shared function … that case K … calls first", priority 7, class C; 40 rows; e.g. the cam debug printf 0x7E62EBCA); (b) a table without a bound check is cut at the next table base (stacked tables 0x7E7F0988/09C0/09F8 gave false cases 17/31) | 392 + 40 | V |
| 6 | `data pointer table` | ptab2 runs. **D5:** the BASIC run at 0x7F069340 is skipped (read as {name, token, fn} at 0x7F069338 instead) | 414 | V |
| 7 | `jump/hash table owner`, `code immediate` | as D4 | 712 | V |
| 8 | `shape:*` | byte shapes (D4 table). **D5 wrapper fix:** the last write to each argument register wins (0x7F08459E stored 8221 to memory and called with d0 = 0; the old row said d0 = 8221); stores before the call are reported | 1,178 | V |
| 9 | `own strings (gist)` | up to 3 own strings | 789 | V |
| 10 | `features+call graph` | facts + nearest labelled ancestor. **D5:** a block copy whose source is a short printable C string is written "copies the string «…»" (it was "block-copy loop from table"); new call templates: imgdev command N with its COM_ name, sg command N, ADJSLF test N, "reads the mcon GUI value of info N" | 3,610 | V |
| 11 | `call graph (unnamed callers)`, `(no callers)` | as D4 | 655 | V |

**Rule C1 (15b callback rows, `cb/cbfix.py`; also written into `15b-camera-core-index.tsv`).** The D3 `cbx.py` rule called every function that calls the step poster or the damage reporter a "step callback". The fix:
- **Callback:** only a function whose address is loaded as a code immediate or held in a data word (pointer reference) and that has no direct caller. Kind `callback`; the role says where the pointer goes (passed to cam_ev object set-up 0x7E635701, the delayed-step helper, stored at +20/+24/… of a request).
- **Not a callback:** a function with direct callers and no pointer reference becomes kind `action` ("sequence function, not a callback (called directly by …)"), with its effect read from the code (step bit, cam_ev object id, sub-module open/close, request sender, delayed step).
- **Hand roles:** the module API and the state-machine functions (§2.1) get hand roles (kind `function`).
- **Pool allocators:** the 16 allocators get kind `init`.
- **Result:** of 340 rows, 221 are callbacks, 81 actions, 22 functions and 16 init; 324 rows changed text.

**Class P (D5):** a C row that also contains a specific fact after `;` (issues/posts/sends/registers/reads prm/records ADJSLF test …) is now P.

## 4. Coverage and measured accuracy

**Coverage: 13,694 / 13,694 rows have a role** (no blanks; 60 orphans are described as such).

| Range | Rows | S: D4 → D5 | P: D4 → D5 | C: D4 → D5 |
|---|---|---|---|---|
| camera core / movie / rec / face | 8,935 | 3,641 (41 %) → 4,778 (53 %) | 916 (10 %) → 1,034 (12 %) | 4,378 (49 %) → 3,123 (35 %) |
| playback / audio / BT | 2,486 | 1,052 (42 %) → 1,265 (51 %) | 63 (3 %) → 103 (4 %) | 1,371 (55 %) → 1,118 (45 %) |
| overlays A + B | 2,273 | 866 (38 %) → 950 (42 %) | 160 (7 %) → 253 (11 %) | 1,247 (55 %) → 1,070 (47 %) |
| **all** | **13,694** | **5,559 (41 %) → 6,993 (51 %)** | **1,139 (8 %) → 1,390 (10 %)** | **6,996 (51 %) → 5,311 (39 %)** |

- **S share of the flagged components, D4 → D5:** EXP_MOVIE 20 → 78 %; mcon mode controller 15 → 100 %; RFCOMM 4 → 72 %; L2CAP 7 → 46 %; SDP 4 → 51 %; OBEX core 4 → 21 %; OBEX_ACP/tasks 40 → 65 %; BASIC 13 → 49 %; ADJSLF 8 → 31 %.
- **Weakest now:** cam_param/pfp/port/prepro/rap.c 3 % S (56 % S+P); PC_USB driver 12 %; fcs/AF tail 13 %; ADJ helpers 15 %; touch panel 22 %; cam_*.c aedrv…frame_sync 25 %; the 252 EXP_MOVIE functions without a decode row (loop bodies 0x7E6A2BB7–0x7E6A8905).

**Diff against the D4 TSV:** 5,484 rows changed text. Most of these are rewordings: the jt rows now read "work of case K … (the case arm calls it)", and the ancestor labels changed.
- Class moves: C→S 1,603; P→S 206; C→P 112; S→C 249; S→P 127; P→C 1.
- The S→C/P moves are deliberate demotions:
  - shared callees that the D4 jt and shell rules called case or subcommand handlers (55 rows);
  - section phrases that describe a chain, a pair or a shared table cell (about 260 rows);
  - 92 bare strings that are arguments, not own names;
  - the 15b direct-call "callbacks".

**Changed-row checks (V, read in code):**
- Seed 55, 10 rows: 2 misleading (0x7E65AF26, 0x7E65AEF8: "called directly by", taken from the new 15b wording). Fixed by the caller-phrase filter.
- Seed 77, 10 rows: 1 wrong (0x7E93189D said "answers DM"; it sends UA 0x73 to a SABM). Fixed in `bt/hand_bt.tsv`.

**Fresh random samples, each 30 rows, judged by an independent reader against the code** (`sample_d5_fresh{1..4}.tsv`, verdicts in `verify*/results.tsv`). After each sample, every error was traced to its rule, the rule was fixed and the index was rebuilt. So each sample measures the rules as they stood before that sample's fixes.

| Sample (seed) | Correct | Misleading | Wrong | Truly specific (reader) | Rules fixed after it |
|---|---|---|---|---|---|
| 1 (5151) | 26 | 3 | 1 | 4–8 | jt shared callee; `|` inside backticks; 15d list-keyed rows; chain middle |
| 2 (6262) | 25 | 1 | 4 | 11 | wrapper last-write; stacked jt tables; `A / B` and shared cells; bare-string argument; shell shared callee |
| 3 (7373) | 27 | 0 | 3 | 11 | fieldstore at +0; timer wrap value 0x7E46B519 (was "free-run timer read"); DPS host-file test (15d source error) |
| 4 (8484) | 27 | 1 | 2 | 12 | "block copy" excludes in-place arithmetic; mcon 0x7E6FFB28/2D text; DPS 0x7F06029C states (15d source error) |

**Measured error rate: 15 / 120 = 12.5 % before the fixes (wrong 10, misleading 5). The last two samples gave 3 / 30 = 10 % each.** This is above the 5 % target. Two things are behind it:
- the reader in D5 also checks callee names and argument values, which the D4 self-check (2.2 %) did not;
- most errors come from D4-era generic rules (wrapper, jt, section text, fieldstore, copy loop) and from two 15d source rows.

All 15 sampled errors are fixed. No sample was drawn after the last fixes, so **no post-fix rate is claimed**. Of the errors, only one came from a decode file (mcon 0x7E6FFB28); none came from rule C1.

## 5. Corrections to earlier sections

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

## Known rule errors

Fixed in D5 (removed from this list):
- the 15b callback rule (C1);
- the BASIC table reading;
- section names given to callees or arguments (glSetErrorFuncDMP, UnitCodeCam);
- trace tags (FCS_END) used as ancestor names;
- overlay-B context-only rows for the USB ISR, the ADJSLF helpers and the C3D scene;
- "block-copy from table" on strings and on in-place loops;
- jt/shell "handlers" that are shared callees;
- stacked jump tables;
- wrapper arguments overwritten before the call;
- fieldstore missing +0 stores;
- section-phrase cuts at `|` and two-function phrases.

Still open (measured rate 10 % on the last two fresh samples):
- **Wrapper/shape rows describe the body but not the purpose.** Examples: "returns 900", "sets a byte". They are correct but are not roles.
- **`15d tsv dps-fn` rows** carry two known source errors (fixed by hand rows here). The 15d text has not been re-checked as a whole.
- **Bare all-capital labels** (`MOV_IMDF`, `EXP_DATA`) are kept with "(log tag)". Some may be trace tags inside another function.
- **"Under X" context** uses the nearest labelled ancestor within 3 levels. That is a location, not a role.
- **`sec NN line L` (rule 4, I)** still takes the phrase around the address. Phrases with one address but several subjects can still mislead.
- **Decode files (exp/bt/mcon)** were checked on samples only. Their 134 I rows are inferences from call edges and constants.
