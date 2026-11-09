# 16d. Camera core, playback/audio/Bluetooth and overlays A/B: generated per-function index

Round D7, cycle 3 (2026-11-09; builds on D6). **This round turns context-only rows into roles without losing precision.** A new rule writes an exact behaviour summary for short functions (§3, rule M), 32 hand rows were read in the code (§2.7), the named rule errors of round 8 are fixed (§4.3), and every rule with more than 50 rows was sampled again (§4.2). Scope: block 0 of E-PM2 v1.6, three ranges:
- camera core, movie, rec, face: 0x7E6211E1–0x7E731584 (8,935 functions; the first 27 KB, to 0x7E627E9E, are the fcs/AF code tail, not camera core);
- playback, audio, Bluetooth: 0x7E8F5800–0x7E965FD0 (2,486 functions);
- overlays A and B, code parts: 0x7F05C000–0x7F0F0000 (2,273 functions).

The 65 functions with `data_page` = 1 or `suspect` = 1 are skipped. CapImg and OlyHfwLowApiWrap are outside these ranges (16a rows); only the Apical code is here.

- **Labels:** (V) = read in code or bytes; (I) = inferred. **In the TSV, a row marked I starts with "probably"**: it comes from a demoted rule (§4.2) and is a hedged reading, not a checked fact.
- **Index file:** `16d-core-play-overlay-index.tsv`, **one row per function, 13,694 rows**. Columns: `addr`, `size`, `role`, `basis` (rule or table), `V/I`, `class` (S = specific role, P = specific facts only, C = context only), `component` (smallest named range, §1).
- **Exact-summary rows** (basis `micro-summary`) start with "exact summary:". Register names d0/d1/a0/a1 mean the value at entry; `u8/u16/u32[X]` is a memory access; `result(F)` is what F returned; `calls F(…)` lists the argument registers the function set since entry or the previous call; `exit d0 = v` is the last of d0/a0 written before the return; `tN` names a value loaded before a later store or call; `if C { … } else { … }` gives every path. The old row follows after `|| context:`.
- **Scratch:** `$S/d7/core/` (copied from `$S/d6/core/`; paths point to d7). Run with `python3 -I`, in this order:
  1. `db.py`, `ment.py`, `ranges.py`, `strnames.py`, `ptab2.py`, `immref.py`, `shells.py` (D7 changed `strnames.py` and `ptab2.py`, so `immref.py` and `shells.py` must run again after them);
  2. `cat roles_head.py roles_main.py > roles2.py; python3 -I roles2.py` → `index.tsv` (it imports `micro.py` and reads `hand_d7.tsv`);
  3. `measure.py` (class shares against the D6 TSV `pub_d6.tsv`), `final_stats.py` (rows, V/I and class per rule group, `rgrp.py`), `prec7.py` (checks and errors per rule group and round).
- **Samples and verdicts:** `v7/batch{A,B,F}N.tsv` (rows as sampled) and `v7/res*.tsv` (verdicts, one line per row, with the instruction addresses). Instructions to the readers: `v7/VERIFY.md` (D6 text plus the exact-summary notation).
- **Hand and decode inputs:** `comps_hand.tsv`, `hand.tsv`, `handnames.tsv` (D4); `hand_d5.tsv` (D5; 9 rows re-read in D6); **`hand_d7.tsv` (32 rows, D7, each read in the code)**; and the decode files `exp/hand_exp.tsv` (872 rows), `bt/hand_bt.tsv` (284), `mcon/hand_mcon.tsv` (698). Their tables and signatures are in `exp|bt|mcon/notes.md`.

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
| **D7:** 0x7E6211E1–0x7E627E9E | fcs/AF code tail (unchanged here). The regions table calls this part "camera core"; the code is AF: 0x7E626BE3 is the AF trace init (only caller AF/FCS init 0x7E5E2988), 0x7E625123 an IAF per-area gate (only caller 0x7E614C8F), 0x7E6212B5 logs `fcs_sub_iaf_set_lens_pos_info` | V (§2.7) |
| **D7:** 0x7E6DAF9A–0x7E6DCB0D | `mov_kdg.c` (as 04 §3.2): 0x7E6DAF9A is `mov_kdg_init`. modules.tsv is fixed (its `mov_img.c` row on this function is removed) | V |
| **D7:** 0x7E91367B–0x7E913753 | BT UART transport (`bt_sio` 0x7E91369B, UART open config 0x7E9136E5) | V |
| **D7:** 0x7E913754–0x7E913821 | BT `[SALLOC]` semaphore-guarded heap alloc/free wrappers (4 functions) | V |
| **D7:** 0x7E913822–0x7E913983 | BT pairing/security glue: callbacks of the security-event handler 0x7E913F1E (numeric value formatter 0x7E913835, name copies, events 53/61 through 0x7E913984). D6 called 0x7E91367B–0x7E913983 "BT UART/patch tail" | V |
| **D7:** 0x7E94D27A–0x7E94D72E | audio DSP-parameter override ops (save / override / restore; context 0x602AF410), §2.7. 05 had "audio-side (inferred)" | V |

## 2. Components and decoded tables (D5; D6 additions in §2.6; D7 in §2.7)

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
  - The loader 0x7F0C6FEC (only caller: the white-source test step 0x7F0C6059, which logs «R_/G_/B_src_white_test»; D7: not a name) copies table 1 column by column to three 321-double arrays at a0+31108/+33836/+36564, then copies table 2 (loop `add 88`, `cmp 321`). The meaning of the 3 and 11 columns is not decoded (I: spectral reference data for the `WL_Peak_*ref_BPF%d` white-source test).
  - The GUI exposure-step table 0x7EFE9622 (6-B rows) is outside this index's ranges.
- **Overrides of source rows** (`hand_d5.tsv`, D6 verifier): 0x7E666C98 copies the 20-byte EMS2 state 0x6056F170 *out* to the caller buffer (15b says "clear"); 0x7E65FC9B stores the error first and then posts event 8 (15b had the order reversed); 0x7E92C429 fills an *outgoing* OBEX Body/End-of-Body packet (bt decode had the direction reversed); 0x7E9338F4 is an RFCOMM credit advance, not a modem-status setter.

**2.7 New in D7 (V; rows in `hand_d7.tsv`, each read in the code).**
- **MOVDISP state machine** (round8 F026). The runner 0x7E6E6130 takes state u16[0x605B1B3E + 2·d0] → table word[0x7E80C220 + 4·state], and event row u16[0x605B1B3C + 2·d0] → 8-B cell {action, post}. It calls action(a0) (default result 14086), then post(d0 = result, a0). Both calls (in 0x7E6E608B) pass d0 = 0: the first sets the row to the message word when it is 0 or 1 (else it keeps the old row), the second sets it to 2.

  | Table | Row | Action | Post |
  |---|---|---|---|
  | state 0, 0x7E80C1F0 | 0 | 0x7E6E6172: if sound plays, polls 0x7E6E768F (once, then ≤ 120 times after 0x7E6DD9BB(16)); returns 14086 | 0x7E6E627F: state = 1 |
  | state 0 | 1 | 0x7E6E61D8: reply 14087 | – |
  | state 1, 0x7E80C208 | 0 | 0x7E6E61D8: reply 14087 | – |
  | state 1 | 1 | 0x7E6E61E7: show frame (0x7E6EBC90), stop sound if playing (0x7E6E7886), reply 0 | 0x7E6E628A: state = 0 |
  | state 1 | 2 | 0x7E6E6215: r = 0x7E6EBAE9(); r = 0 → like row 1; else reply 14089 (0x7E6E74F2 gives NULL) or 14086 | 0x7E6E6294: state = 0 if result = 0 |

  Replies go through the reply sender 0x7E6E62A8: {u16 result, obj+88, obj+96} sent with 0x7E4307CD, checked with the tag «mov_dsp».
- **Movie KDG and playback** (F023–F025): 0x7E6DB43E returns the KDG effect code 0–5 from the state bytes 0xA0751F98 (type) / 0xA0751F99; it is the source of `api_movie_Get_MovieEffect_Type`. The playback AVSCA callback 0x7E6E0F79 (`P>O ApiUSRScaCb`) **locks the CPU and loops forever at 0x7E6E11A0 on A_ERR_SEVERE 0x80000004**. The AVCHD step-buffer update 0x7E6E310A sets the index to 1 if it was 2, else to 0 (its twin 0x7E6E1E3C is a plain 3-slot decrement); the intent is open.
- **BT pairing glue and SEC records** (F028, F029): 0x7E9138EB (event 61) and 0x7E9138A1 (event 53) copy a name to 0x605CD344, set 0x605C601C / 0x602AEBFC and post the event through 0x7E913984 (16-B message to queue id u16 0x7E43EDF0, flag u16 0x7E43EC4E pattern 8). 0x7E929A40 / 0x7E929AB4 register / unregister a record on the list 0x7DAC4A10 under the BT stack lock (status 0, 1, 5, 18, 22; the names `SEC_Register` / `SEC_Unregister` are I).
- **Audio DSP-parameter override ops** (F031): 0x7E94D27A op 2/3/4 allocates the context 0x602AF410 and runs the op switch 0x7E94D2F1 with mode 0 (save + override); op 1 runs it with mode 1 (restore) and frees the context. Context layout: +0 prm 30338 (DF1 enable, set to 0), +8 prm 30034 (SE1 3D, set to 0), +52 prm 56004 (wind cut: each of its 11 entries gets the 3 LHPF values of prm 30018), +188 prm 30354 (zoom notch: indexes 0–7 set to the ROM default {0,0,0,4096,0,0,0,4096}), +320/+452 prms 14353/14369 (PGA volumes: each third of the 33 entries set to entry 6, 17 or 28). Op 3 = wind cut + PGA; op 4 = all five. Why the camera does this (a mode that needs the plain filter) is I.
- **ADJSLF work area** (round8-review4 F080): the step `UnitCodeBody` 0x7F0B55FD stores the buffer 0x7F0A9EAB() = **0xA6545E00 (1 MB; the getter writes 1,048,576 to *a0)** in RAM **0xA06E1734**, and passes +524,208 to 0x7F0CE0B6. The reset 0x7F0B6C9D clears the first 352,064 B (0x7F0C910E; words +28…+40 = −1), then u16 +353,924…+353,930 and u8 +524,204/+524,205. 11 functions reference 0xA06E1734 (0x7F0B55FD … 0x7F0B883D).
- **AF tail** (F012, F013): see §1. 0x7E626BE3 copies prm 0x2AF4 (two words) and 0x2B04 to the trace masks 0x6054C7A4/A8/AC and sets up the 128-record ring 0x6054C79C.
- **`aud` shell table:** 12-B records {char *name, fn, char *help} at **0x7EBBEC7C** (27 rows; `read_reg` … `test`), walked by 0x7E94F73A. D6 read it as {fn, name} at 0x7EBBEC80 and gave the help text as the name. The `mdet` table 0x7E7C053C has the same layout.

## 3. The rules (priority order)

A function gets the role of the highest-priority rule that fires; up to two lower rules are appended after `;`. Rows = rows whose primary basis is that rule (the D6 counts are kept in the older rows of this table; §4.2 has the D7 counts). **D6** and **D7** mark the changes of those rounds; §4 has the measured precision of each rule.

| # | Rule (basis value) | Source or signature | Rows | V/I |
|---|---|---|---|---|
| 0 | **`hand (D7, read in code)`** | **D7:** `hand_d7.tsv`, 32 rows, each read in the code (§2.7); they come first | 32 | V |
| 0 | `hand`, `hand (D5, read in code)` | `hand.tsv`, `hand_d5.tsv`. **D7:** the D4 `hand.tsv` rows and the 9 D6 re-read `hand_d5` rows are demoted to I too (one wrong detail each in round D); rows re-read in D7 keep V. **D6:** `hand_d5.tsv` rows are demoted to I ("probably: …") except the 9 rows re-read in D6 (V/I contains "D6") | 23 + 132 | V; hand_d5 I (9 V) |
| 0 | `D5 exp/BT/mcon decode` | `exp|bt|mcon/hand_*.tsv`. **D6:** demoted to I ("probably: …"); 6 rows corrected (§2.6, §5) | 872 + 284 + 698 | I (2 BT rows re-read in D6: V) |
| 1 | `15b/15d tsv …` | single-address rows of the 15b/15d TSVs. **D6:** demoted to I ("probably: …"). The step-event names of cam.c's factor table are removed from the still/live-bulb rows (`posts step event 0x10000`, not `0x10000 PRO_EMS`); slot and I rows are no longer ancestor labels | 732 + 328 | I |
| 1 | `tasks (fwmap.py tasks)`, `hand name` | task entries; logger, heap and lock names. **D7:** the task rows come from `fwmap.py tasks` (both CPUs, v1.6 tables; saved as `tasks_fw.txt`), not from the stale build/map/tasks.tsv; `cam_ev object set-up` is renamed `cam_ev entry add`. **D6:** the names of task IDs above 0x84 and of ID 1 are shifted in the name table (01 §1), so those entries are "uITRON task entry (cfg N); the label «X» is probably shifted" (I) and are not ancestor labels (`BOOT_CPU0` 0x7E53A4A4 is the standby task) | 73 + 58 | V (shifted IDs I) |
| 2 | `shell decode` | strcmp chains (shells.py). **D6:** demoted to I and reworded: "probably a `fam … sub` shell subcommand handler (it is called after a string compare with «sub» in F; the full command path is not traced)". Nested shells now show the known path (`obex dmy snd`) or `…` | 159 | I |
| 2 | `shell … (shared callee)`, `U_SHELL table`, `shell table (ptab2)` | **D7:** a table row wins over the strcmp guess of the same function; a U_SHELL body behind a prologue entry says so; caller counts are "at least N". Otherwise as D5 | 18 + 22 + 15 | V |
| 3 | `section name` | backticked identifier next to the address. **D6:** not a name when it is a plain word (`Seikou`), a shell command (`cam`), an all-capital tag (`V_DROP_FLG`, `REC_MAKE_IMAGE`), one of the function's own strings passed to a non-print call (`mov_dsi` → 0x7E44AD02), or an identifier that appears only in the strings of another function (04 gives `sound_chunk_int` to the helper 0x7E6F3E9B; the string is in 0x7E6F3EA4). The quoted section text is no longer appended | 157 | V |
| 3 | `own string (io/brk/call/tio/tcall/tagfld)` | the function's own name string. **D7:** the `[tag]func_name …` format names the function: `tio` when an in/out word follows (`[MOV_KDG] mov_kdg_init() in`), `tcall` when `()` ends the string, `tagfld` when other words follow (only when the name is used by this function alone, appears in ≥ 2 of its strings, and every `[tag]X` string of the function starts with the same X); an error word after the name makes it a callee (`[MOV_FILE] queue_write error:`). **D6:** (a) "N error/err/NG/failed/ret/result/status" names a **callee** and is never a name (0x7E8FF8A0 is not `iap_cmd_prc`; 0x7E900560 is not `bt_ctrl_inquiry_cancel`); (b) `[TAG]` in capitals is a trace tag (`[SC_RT]`); (c) `[x] text` is a module tag or a name with a field (`[adj_slf] DispErrInfo`, `[init_memory] top:`), not a name; (d) a function with several different identifier strings gets no name unless the others are parts of it (`api_rec_X` / `X`) or it dominates (≥ 3 uses and 3× each other) | 427 + 73 + 9 | V |
| 3 | `own string (bare)` | a bare identifier string. **D6:** rules (d) above; no bare name when the function also has a `[x] text` string | 810 | V |
| 3 | `ADJSLF constants (D5)` | d0 constants at the ADJSLF API calls. **D7:** a call that is a join point (a branch lands between the d0 write and the call) may get other constants, so its list says "including" (0x7F0AB034: fail codes 3000/3001/3002 reach the 3200 call). **D6:** MDN = op 0x9029, MDI = op 0x902A (was one "MDN/MDI 0x9029" entry); any other write to d0 kills the constant (0x7F0B7002 recorded test "0"; 0x7F0C2B6B recorded the fail code 3002 as a test) | 83 | V |
| 4 | `callback by consumer (D5)` | code immediate passed in a known register to a known API. **D6:** the cam_sem post-job text no longer says "queued on MI_RES/MI_CLS" (the queue object is a0: CAMLNS, FDRV …) | 233 | V (28 I) |
| 4 | `sec NN line L` | section phrase holding the address. **D6:** worded "probably as a section says (not checked here): “…”" | 489 | I |
| 5 | `jump/hash table` | case → handler. **D6:** (a) the switch value is read from the code: `add -k`, `sub k`, `mov k,dX; sub dX,dN`, `mov -k,dX; add dN,dX`, `inc`, register copies; the bound compares cut the table (§4.3); (b) hash keys compared after an adjustment (`mov -1,d0; add a2,d0` in 0x7E939461) get the real value; (c) the first call of a case arm follows a leading `bra` (0x7E63D3FC branches to the 0x7E63D407 arm; jt.py read the next arm); (d) more than 6 cases are written `…/… (N cases)` | 398 + 42 | V |
| 6 | `data pointer table` | ptab2 runs. **D7:** a 12-B run with strings at −4 and +4 is {name, fn, help} (`aud` 0x7EBBEC7C, `mdet` 0x7E7C053C; D6 took the help text as the name); short names that ptrs.tsv does not type as strings are read from the ROM. **D6:** cut to the certain fact "its address is stored in the data word W". The run start, its length and its "user" were wrong in 8 of 11 checks (runs that start mid-table, {key, fn} hash pairs, users that only compare against the end) | 418 | V |
| 7 | `jump/hash table owner`, `code immediate` | **D6:** owner rows say "contains a jump through switch table(s) T" (a switch is not always a dispatcher: 0x7F08E1F9 decodes hex digits); code-immediate rows say "address loaded as an immediate by F" without the "passed to/stored to" detail (it named the wrong call for 0x7E6AF4B9) | 104 + 625 | V |
| 8 | `shape:*` | byte shapes. **D6:** a struct writer names the base register of each store (`(a0)+0, (a0)+2, (a1)+0 …`; it said "through a pointer" for three pointers) | 1,192 | V |
| 9 | `own strings (gist)` | up to 3 own strings | 970 | V |
| 10 | `features+call graph` | facts + nearest labelled ancestor. **D7:** 0x7E457C52 gives "gets the data pointer of prm N" and 0x7E457C62 "gets the element count of prm N" (D6 wrote "pointer/count" for both; round8 F013). **D6:** prm pointer/count getters (0x7E457C52/62) give "gets the storage pointer/count of prm N", not "reads prm N" | 3,438 | V |
| 11 | `call graph (unnamed callers)`, `(no callers)` | as D4 | 789 + 20 | V |
| **M** | **`micro-summary (D7: every path read by rule)`** | **D7, new.** `micro.py` runs a function of ≤ 32 instructions symbolically over every forward path (≤ 4 leaves; no loops, no stack-slot or `mdr` access, no indirect call, no `udf*`); any instruction it does not model drops the whole function. The text is the full decision tree (§ header notation), ≤ 300 characters. It replaces rows of rules 6–11 and `shape:wrapper` that are C or P; the old text stays after `|| context:`. Class S when every callee has a name, else P | 2,008 | V |

**Ancestor and callee labels ("under X", "calls X", "registered by X"; D6).** A label is used only when it is a name: hand names, library names, task names (not the shifted IDs), section names that pass rule 3, own-string names that pass rule 3, and V rows of the decode files and TSVs that are not slot rows. Not used: log tags (`LENS_MAIN`, `PRE_ACTION_ON`, `CAM_CL`), names from callee error strings (`BT_SrvInitialize`, `bt_sio_sem_get`), I rows (`CEC RX setup`), 15b slot-row text, and string names of functions longer than 1,500 B (`WOB_lens_wait` is one state message of the 4.7 KB 0x7E5F9AED; `g_g_fcs_expse_tv` is a variable that 0x7E5EA6BD prints). Long labels are cut at a word boundary (a cut "infos 6…" read as "info 6"). 0x7E5F8BE4 is labelled "C-AF scan-route decision (16c)", not `SC_RT`.

**Rule C1 (15b callback rows, D5).** The D5 rule (`cb/cbfix.py`) is unchanged: a callback is a function whose address is a code immediate or a data word and that has no direct caller; functions with direct callers are "sequence function, not a callback". In D6 the 15b rows are demoted to I with the other 15b rows, and their step-event names are removed.

**Class P:** a C row that also contains a specific fact after `;` (issues/posts/sends/registers/reads prm/records ADJSLF test …) is P.

## 4. Measured precision and coverage (D7)

### 4.1 Method

- **Readers:** independent agents with the code tools and `v7/VERIFY.md` (the D6 rubric plus the exact-summary notation). Each row gets CORRECT, CONTEXT (true but says nothing about the function), MINOR (one false detail) or WRONG (false role or name). **Errors = MINOR + WRONG.** The reader names the false clause, so each error is traced to the rule that wrote it.
- **Rounds:**
  - A: 10 rows per rule group with more than 50 rows (20 for the new micro-summary rule, 12 for the new `[tag]name` names, 10 of the 32 D7 hand rows); 262 rows.
  - B: 10 per rule fixed after A, 10 more `features` and micro rows, the other 19 D7 hand rows and 10 task rows; 69 rows.
  - C: 12 hand-group rows and 5 cam_ev callback rows after the B fixes; 17 rows.
  - D: 10 rows with case lists and 10 hand-group rows after the C fixes; 20 rows.
  - F: 40 fresh random rows of the whole index (§4.4).
  - 408 rows in all. No row was checked twice, and no row checked in D6 was drawn again. Tally: `prec7.py`.
- **Baseline:** audit A13 found 0 wrong of 50 in the D6 build. Round A (the D7 build before its B fixes) gave **7 errors in 187 V rows (3.7 %)** and 10 in 75 I rows.

### 4.2 Precision per rule

A rule keeps V only when its checks after its last fix have 0 errors in ≥ 10 rows; the exceptions are named in the last column. "(context)" = rows that were true but CONTEXT.

| Rule group (basis) | Rows (V / I) | A: errors / checked (context) | B–D: errors / checked | Errors found (rule that wrote the false clause) | D7 result |
|---|---|---|---|---|---|
| features+call graph | 2,746 (2746 / 0) | 0 / 10 (9) | 0 / 10 | — (the F013 "count" wording was fixed before A) | **V** |
| **micro-summary (new)** | 2,008 (2008 / 0) | 0 / 20 (0) | 1 / 12 | D: one error, in the old `|| context:` part (the jt case count, see jump/hash table); no error in a summary clause in 39 checks (A 20, B 10, D 2, F 7) | **V** (new) |
| exp decode | 872 (0 / 872) | 0 / 10 (0) | – | — | I (D6 demotion stands; 0/15 here) |
| own strings (gist) | 828 (828 / 0) | 0 / 10 (9) | – | — | V (context) |
| own string (bare) | 810 (810 / 0) | 0 / 10 (0) | – | — | V |
| 15b TSV | 732 (0 / 732) | 0 / 10 (0) | – | — | I (D6 demotion stands) |
| mcon decode | 698 (0 / 698) | 0 / 10 (0) | – | — | I (D6 demotion stands) |
| shape:* (not wrapper) | 603 (603 / 0) | 0 / 10 (0) | – | — | V |
| own string (io/brk/call) | 506 (506 / 0) | 0 / 10 (0) | – | — | V |
| section text | 475 (0 / 475) | 1 / 10 (1) | – | A: "samples the face into an 80×80 patch" (it sums 2×2/4×4/8×8 boxes) | I |
| call graph (unnamed/no callers) | 445 (445 / 0) | 0 / 10 (10) | – | — | V (context) |
| jump/hash table (case) | 411 (411 / 0) | 0 / 10 (4) | 0 / 7 | C: "(116 cases)" for a 65-slot table with 47 matching cases, and a case listed twice (fixed: distinct values of one table). D (in a micro row's context): "(6 cases)" for 9 hash values (jt.py misses arms). Fixed after D: **no case count is written any more** ("/… (more cases)"); the case values themselves were right in every check | V (last fix removes a clause; not re-sampled) |
| code immediate | 392 (392 / 0) | 0 / 10 (5) | – | — | V (context) |
| 15d TSV | 328 (0 / 328) | 2 / 10 (0) | – | A: copy direction and count in an ISR helper; a hedged "RX buffer control" that is the CEC logical address | I |
| hand.tsv, hand names, tasks, U_SHELL, `hand_d5` | 324 (170 / 154) | 3 / 10 (0) | 6 / 43 | A: stale task cfg id (build/map/tasks.tsv); U_SHELL row on the body, not the table word. B: `cam_ev object set-up` (it adds an event entry); an unhedged 15d extra clause; "81 other callers" (82). D: a D4 `hand.tsv` row (EFFECT cmd 5 picks its path by the effect type, not by mask 3); a D6 `hand_d5` row (`R_src_white_test` is a step name, not the caller's name). All fixed | split: tasks (from `fwmap.py tasks`, 15/15), U_SHELL and hand names stay **V**; D4 `hand.tsv` and all `hand_d5.tsv` rows are now **I** except rows re-read in D7 |
| BT decode | 284 (2 / 282) | 3 / 10 (0) | – | A/F: incomplete error list; "events to each of the 18 channels"; "resends GET 0x83" (it sends Abort 0xFF); F: "RequestPortSettings" (it answers an RPN request) | I |
| callback by consumer | 233 (205 / 28) | 0 / 10 (0) | 0 / 5 | — (the cam_ev wording follows the renamed 0x7E635701; C 0/5) | V |
| data pointer table, shell table | 215 (215 / 0) | 0 / 10 (8) | – | — (the `aud`/`mdet` {name, fn, help} layout was fixed before A) | V |
| shape:wrapper | 214 (214 / 0) | 0 / 10 (3) | – | — | V |
| section name | 155 (155 / 0) | 0 / 10 (0) | – | — | V |
| shell decode | 142 (10 / 132) | 2 / 10 (0) | – | A: `tpc info` for the header printer of that branch; `usb fifo6` for the shared `usb fifo[0-6]` handler | I |
| jt owner | 102 (102 / 0) | 0 / 10 (10) | – | — | V (context) |
| ADJSLF constants | 83 (83 / 0) | 4 / 10 (0) | 0 / 10 | A: fail-code list incomplete at a join point; "ADJSLF step" for a 17-caller helper; MDI callee label "op 0x9029" (×2, from `hand_d5.tsv`). Fixed before B | **V** (B 0/10) |
| **own string, `[tag]name` format (new)** | 56 (56 / 0) | 0 / 12 (0) | – | — | **V** (new) |
| **hand (D7)** | 32 (32 / 0) | 2 / 10 (0) | 2 / 19 | A: MOVDISP row setting ("1 or 2"); reply sender called `mov_dsi` (an error-check tag). B: 0xA6550000 for 0xA6545E00; "120 polls" (121). All 4 fixed | V (fixed; 29 of 32 checked) |

**Demoted in D7:** the 22 D4 `hand.tsv` rows and the 9 `hand_d5.tsv` rows that D6 had re-read are now "probably: …" (I), except the rows re-read in D7. An extra clause from a demoted source (15b/15d TSV, decode files, `hand_d5`, section text) now starts with "probably:" even inside a V row (0x7E6B9B19 carried the 15d "write wrapper" as a fact).

**I rows: 3,701** (decode files 1,852, 15b/15d TSV 1,060, section text 475, hand group 154, shell 132, callback by consumer 28).

### 4.3 Named rule errors fixed in D7

- **features+call graph (round8 F013):** "gets the storage pointer/count of prm N" was written for every call of 0x7E457C52 or 0x7E457C62. The data-pointer getter and the element-count getter are now named apart. 0x7E626BE3 itself is a D7 hand row (AF trace init). Rounds A and B: 0 errors in 20 checks of this rule, but 16 of them were CONTEXT: the rule is true, yet rarely a role.
- **`[tag]func_name field` names (same fix as 16a; round8-review2 side finding 4):** `[MOV_KDG] mov_kdg_init() in` gave no name, because the bracket was read as a module tag and the rest was skipped. 56 functions now get their name from this format; 0 errors in 12 checks.
- **`aud` / `mdet` shell tables:** these are 12-B {name, fn, help} records. ptab2 took the +4 help string as the name and started the table 4 B late. 34 rows are fixed. The `aud` subcommand rows are now V table rows (`aud ld_clear` = entry 11 of 0x7EBBEC7C), not I strcmp guesses.
- **Task names and ids:** build/map/tasks.tsv is stale (cfg ids one too high, shifted names). The task rows now come from `fwmap.py tasks` (93 rows; 15 of 15 checked rows right).
- **ADJSLF constants:** a fail call reached from a shared tail got only the fall-through code (now "fail codes include …"); a 17-caller helper was called a "step" (now "shared function"); the stale MDI label "op 0x9029" is fixed in `hand_d5.tsv`. Round B: 0 / 10.
- **U_SHELL rows:** a function whose table word is a prologue entry a few bytes earlier is now "body of the U_SHELL `aud` entry 0x7E94F735".
- **Counts:** "N other callers" is now "called by at least N other functions" (calls.tsv misses some call sites). Switch case lists keep the distinct values of one table and give **no count**: jt.py's count was wrong twice (116 for 47, 6 for 9). The listed case values were right in every check.
- **Hand rows:** `cam_ev object set-up` 0x7E635701 is renamed `cam_ev entry add` (it adds an event entry and returns its id); EFFECT cmd 5 0x7E8F7090 is re-read; the `R_src_white_test` "caller name" is removed from 0x7F0C6FEC; four D7 hand rows were corrected after their checks (0xA6545E00, not 0xA6550000; 121 polls; the MOVDISP row setting; `mov_dsi` is a tag).
- **Empty component text:** the wrapper rule no longer writes "(in )" when the target has no component.

### 4.4 Final check (fresh rows)

40 fresh random rows of the D7 build (seed `D7-final`, drawn after the round-A fixes; batches `v7/batchF1-2.tsv`):

| Sample | V rows: errors / rows | I rows: errors / rows | Errors |
|---|---|---|---|
| F (seed D7-final) | **0 / 29** | 1 / 11 | I row only: BT decode `RFCOMM_RequestPortSettings` 0x7E9337AA answers a remote RPN request (WRONG) |

The 29 V rows: 7 micro-summary, 6 features, 5 own-string names, and 11 rows of 10 other rules. 21 were CORRECT and 8 CONTEXT. **The target is met for this sample: 0 wrong among 29 V rows.** Over the D7 rounds, V-row errors went from 7 / 187 (A) to 5 / 69 (B, mostly old hand rows), 1 / 12 (C), 3 / 20 (D: hand rows and a case count) and 0 / 29 (F). Every error was fixed or its rows were demoted. The fixes after round D (no case counts, demoted D4/D6 hand rows) only remove or hedge clauses; they were not re-sampled.

### 4.5 Coverage

**13,694 / 13,694 rows have a role.** Shares by class, D6 → D7:

| Range | Rows | S: D6 → D7 | P: D6 → D7 | C: D6 → D7 |
|---|---|---|---|---|
| camera core / movie / rec / face | 8935 | 4684 (52 %) → 5302 (59 %) | 1049 (12 %) → 1618 (18 %) | 3202 (36 %) → 2015 (23 %) |
| playback / audio / BT | 2486 | 1197 (48 %) → 1312 (53 %) | 126 (5 %) → 300 (12 %) | 1163 (47 %) → 874 (35 %) |
| overlays A + B | 2273 | 887 (39 %) → 1004 (44 %) | 252 (11 %) → 505 (22 %) | 1134 (50 %) → 764 (34 %) |
| all | 13694 | 6768 (49 %) → 7618 (56 %) | 1427 (10 %) → 2423 (18 %) | 5499 (40 %) → 3653 (27 %) |

- **Final shares:** specific (S) **56 %** (V 29 %, hedged I 27 %), partial (P) **18 %**, context only (C) **27 %**. D6 had 49 % / 10 % / 40 %. Of the 13,694 rows, 9,993 are V and 3,701 are I.
- **Where the gain comes from:** the micro-summary rule turned 2,008 rows into exact summaries (762 S; 1,246 P, where a callee has no name). 1,199 rows moved C → P, 647 C → S and 204 P → S. The `[tag]name` names, the `aud` table rows and the 32 D7 hand rows give the rest.
- **Still context only:** 3,653 rows, mostly `features+call graph` (1,909), own strings (666), call graph (445), code immediate (347) and data words (158). Most are functions over 32 instructions, or functions with loops, stack slots, `udf*` multiplies or indirect calls, which rule M does not model.

## 5. Corrections to earlier sections

**New in D7 (V; the other sections are not edited here):**
- **modules.tsv (edited here):** the `mov_img.c` row on 0x7E6DAF9A is removed; `mov_kdg.c` starts at 0x7E6DAF9A (`mov_kdg_init`), as 04 §3.2 says. The name string `mov_img.c` (0x7E806F06) exists, but no function is placed in that file (its code, if any, is probably just before 0x7E6DAF9A, I). modules.tsv now has 179 file rows (the README says 165 source files).
- **firmware-map.md regions table / 15b §1:** 0x7E6211E1–0x7E627E9E is the fcs/AF code tail; camera core (cam.c) starts at 0x7E627E9F (03, round8-review1).
- **05 / 15d:** 0x7E913822–0x7E913983 is BT pairing/security glue, not UART or patch code (§1). 0x7E929A40 / 0x7E929AB4 register / unregister records on the SEC list 0x7DAC4A10. 0x7E94D27A–0x7E94D72E (05: "audio-side, inferred") is the DSP-parameter override block (§2.7).
- **04 §5.1:** the playback AVSCA callback 0x7E6E0F79 hangs on A_ERR_SEVERE (§2.7). `mov_dsi` / `mov_dsp` are error-check tags passed to 0x7E44AD02, not the name of the reply sender 0x7E6E62A8.
- **build/map/tasks.tsv is stale:** its cfg ids are one too high and some names are shifted (0x7E6D4597 is MOV_EDIT, id 0x0084, not «IMG0_LOCAL» 0x008e). `fwmap.py tasks` reads the v1.6 tables of both CPUs; the 16d task rows now use it (93 rows), including the CPU1 and 0x80xx tasks that tasks.tsv lacks.
- **16d D6 rows:** the `aud` table is {name, fn, help} at 0x7EBBEC7C (27 rows said "{fn,name} at 0x7EBBEC80" and gave the help text as the name; 7 `mdet` rows the same); "gets the storage pointer/count of prm N" named both getters at once (F013 is the AF trace init); the `hand_d5.tsv` label of 0x7F0A98E9 said op 0x9029 (it sends 0x902A), and ADJSLF rows that call MDI carried that label; the `aud` U_SHELL row was on 0x7E94F73A, but the table word is the prologue entry 0x7E94F735.

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
8. **(D7)** The MOVDISP event rows (0x605B1B3C = 0/1 from the message word, 2 from the second call) and the replies 14086/14087/14089 are not named. Why the audio override (op 3/4) sets the wind cut to the plain LHPF and flattens the PGA tables, and which camera mode calls it through 0x7E95C47A, is open. 0x7E6E310A's net effect (index 1 only after 2) may be a firmware bug.
9. **(D7)** Rule M could cover more with stack-slot locals, `udf*` multiplies and bounded loops; about 1,600 context rows are longer than 32 instructions.


## Known rule errors

Fixed in D7 (removed from this list): "storage pointer/count" prm wording; `[tag]func_name` names missed; the {name, fn, help} shell tables read as {fn, name}; stale task ids and names from build/map/tasks.tsv; ADJSLF constant lists cut at join points, "step" for shared helpers and the stale MDI label; U_SHELL rows on the body instead of the prologue entry; exact caller counts and case counts; unhedged extra clauses from demoted sources; empty "(in )" text. Fixed in D6: jt slot as case value, names from callee error strings, trace tags as names or labels, names on multi-string switches, shifted task names, tag/word section names, pointer-table runs, "passed to" details, cam_sem queues, ADJSLF MDI op, step-event names, "dispatcher" on any switch, struct-writer wording, cut labels.

Still open:
- **Fixes after round D are not re-sampled:** no case counts, the demoted D4/D6 hand rows, the renamed 0x7E635701. They remove or hedge clauses, so they cannot add a false one, but no sample measures them. The D7 hand rows had 4 errors in 29 checks; all 4 are fixed, and 3 of the 32 rows were not checked.
- **Demoted rules ("probably", I; 3,701 rows):** decode files, 15b/15d TSV rows, `hand_d5.tsv`, D4 `hand.tsv`, section text and shell paths. In D7, 10 of 75 checked I rows (13 %) and 1 of 11 in the final sample had a wrong detail (error lists, directions, a request that is a response, command paths). Use them as leads, not facts.
- **Exact summaries (rule M) describe mechanics, not purpose.** They are complete and checked (0 errors in 39 summaries), but a reader must still infer the role ("calls 0x7E65D1FD(a1=u32[0x6056EBB8])"). `exit d0 = …` is the last of d0/a0 written, so a void function shows a scratch value. A function the map splits too early (0x7E68920A, 0x7E926FA1 continue past their map size) is summarised only when its fragment ends in a return; the readers found no such summary.
- **Case lists** show the cases whose arm calls the function first, and only some of them: jt.py misses arms of some hash switches (0x7E708AAB: 9 values, 6 found). No count is written.
- **"Under X" context** is a location (nearest labelled ancestor within 3 levels), not a role.
- **Context-only rows are 27 %** (3,653). They are mostly functions over 32 instructions; the readers' evidence columns (`v6/res*.tsv`, `v7/res*.tsv`) hold roles for about 30 of them (SCSI sense builder 0x7F09729C, TPC node pool 0x7F08F386, 0x7E6A756A COM_SET cycle).
- **The function map splits some case arms into separate functions** (0x7E913DD6, 0x7F08A18B, 0x7F08A1E7, 0x7F05D8EE in the BASIC key table); their rows describe the arm.
