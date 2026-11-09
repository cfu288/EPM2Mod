# 13e. Mode controller (mcon), TAKE release sequencer, strobe exposure (E-PM2 v1.6, block 0)

Labels: **V** = verified (read in code or bytes), **I** = inferred. Runtime addresses (base 0x7E421020).
Scratch: `$S/d1/mcon-sequencers/` (`rec60.py` op records, `conf.py` conflict table, `take.py`/`tgraph.py` TAKE states, `hooks.txt` hook catalogue, `mcon.dis`, `takeseq.dis`).
Earlier detail: 07 §2.1–2.2, 09a §1, 10a §1–3, 02 §4–5, 12 §1. This section replaces their mcon guesses (see §4).

## 1. Area and boundaries

| Component | Code | Data (ROM) | Basis |
|---|---|---|---|
| mcon (mode controller) | **0x7E6FCA60–0x7E70787F** | strings 0x7E813F22–0x7E814856; tables 0x7E814864–0x7E84EE67 | V: 0x7E6FCA3C is the FACE_PT1 task loop (01 table); 0x7E707880 dispatches through table 0x7E84EE68 and is called only from movie/REC code (0x7E6DADB9, 0x7E7172B4, 0x7E71C7BE). PrintIM/Exif starts at 0x7E708312 |
| TAKE_MAIN sequencer engine | 0x7E58204D–0x7E582601 (last `ret` at 0x7E5825FF; 0x7E582602 starts the `take` debug-command function) | state table 0x7E790860 (27 × 20 B), names 0x7E790758 | V (A4 2026-11-09) |
| TAKE sequencer states/handlers | ~0x7E59A24C–0x7E5AB7FF (entries 0x7E59A332…0x7E5AB405; shared handlers 0x7E5A4192–0x7E5A46CE) | event tables 0x7E78F530–0x7E7906B8 | V (table pointers) |
| Strobe exposure (`stb_expose`) | ~0x7E5D036C–0x7E5D8E94 | strings 0x7E79B06A–0x7E79CD9F | V strings / I bounds |
| Light-source selection (strobe assist) | 0x7E5E2258–0x7E5E22FF: availability 0x7E5E2258 and F011 0x7E5E22A6 (+ 0x7E5E1B11, 0x7E5DEBAD). The rest of the range, 0x7E5E2300–0x7E5E2418, holds the four light-exec callbacks (§2.4), not selection code | – | V (A4 2026-11-09) |

mcon internal layout (V by callers/strings; one row per block):

| Range | Contents |
|---|---|
| 0x7E6FCA60–0x7E6FCD3C | exported `mcon_if_*` API veneers (8–27 B each) |
| 0x7E6FCD3D–0x7E6FD10A | busy-guarded wrappers (camera_start/set/end, mymode, custom, resets) |
| 0x7E6FD10B–0x7E6FE250 | `mcon` debug shell 0x7E6FDCAE, help 0x7E6FDB25, dumps (modeinfo, enumlist, modeconftbl, `MODE0DT%1dDAT` log 0x7E6FDA31) |
| 0x7E6FE251–0x7E6FE444 | **0x7E6FE251 = mcon module init** (only caller Usr0 0x7E503DD4; it calls 15 functions across the module, e.g. 0x7E706905, 0x7E70097E, 0x7E6FF6C2, 0x7E7002E4) (C2 2026-11-09). Language-list code 0x7E6FE2C6–~0x7E6FE3FA (`Warning Language error` 0x7E6FE2C6, `AllocMemory error LanguageInfo` 0x7E6FE32F and their helpers) (I role); then small back-ends 0x7E6FE3FB–0x7E6FE444 called from the `mcon_if_*` veneers (C2 2026-11-09) |
| 0x7E6FE445–0x7E6FE764 | small record callbacks (§3.2: +52 writers, +20/+44 selectors, +40 index) |
| 0x7E6FE765–0x7E6FF5F0 | get / set / step engine (§2.1) |
| 0x7E6FF5F1–0x7E6FF9CD | composite records, dependency propagation, post-write notify |
| 0x7E6FF9CE–0x7E6FFDF7 | 20-entry change log 0x605B4CB8, first +48 hooks, hook batch runner 0x7E6FFD6A, change-notify callback |
| 0x7E6FFDF8–0x7E700992 | override slots 0x605B4C1C, mode-preset apply 0x7E6FFE55, **mode-conflict engine** 0x7E7002FF |
| 0x7E700993–0x7E701177 | mode load / camera_start / set / end, mymode, custom, standard/full reset |
| 0x7E701178–0x7E704701 | +4/+8/+16 step callbacks and +24 hooks (interleaved with their helpers) |
| 0x7E704702–0x7E706835 | helpers and +48 hooks (W-plane twins) |
| 0x7E706836–0x7E706F79 | reset lists, bank save/restore (0x7E706B75 / 0x7E706BDB) |
| 0x7E706FA3–0x7E70787F | value-list engine and the two ROM→RAM hash tables |

## 2. Components

### 2.1 mcon: value planes and API (V unless marked)

**Four value planes for each info id** (accessors in the info module, section 07):
- *current* (effective): Get/Set_CameraInfo 0x7E67F822 / 0x7E67F882;
- *user* (what the user chose): prm **0x8B54**[info], 0x7E67FC52 / 0x7E67FC78 (ids 0–700);
- *bank*: prm **0x8B64**[bank·701 + info], 0x7E67FBFD get / 0x7E67FC26 set (2 banks; 0x7E7077C4 returns 701);
- *W* (working copy): RAM u32 array 0x605A38E0 by id range, 0x7E67FCB8 get / 0x7E67FD72 set. Used when conflicts are evaluated with flag 0x605B6BAE = 1 (I: a scratch copy for mode loads).

**GUI value vs raw value.** mcon converts between GUI values and stored raw values with the 505 value lists (§3.1). The `_Simple` shell commands use GUI values: `Set_CameraInfo_Simple` = 0x7E6FCC72, `Get_CameraInfo_Simple` = 0x7E6FCC91.

**Main entry points** (veneer → body; caller counts from calls.tsv):

| Veneer | Body | Role |
|---|---|---|
| 0x7E6FCABA, **0x7E6FCC91** (101 callers) | **0x7E6FEA5F** | get GUI value. kind = 0x7E7073E3(id): 0 = no list → raw; 2 = simple list; 1 = composite (0x7E6FED4C reads all member ids). If op-record slot +20 exists, its result picks the list variant (0x7E707369), else 0x7E70708D |
| 0x7E6FCAC3, **0x7E6FCC72** (164 callers; refuses while busy byte 0x605A5B50 = 1) | **0x7E6FEAE0** | set GUI value: gui→raw (0x7E7070B4, or 0x7E707397 with the +20 variant), then full write 0x7E6FF3ED |
| – | 0x7E6FEB2A / 0x7E6FEB74 / 0x7E6FEBBE / 0x7E6FEC08 | the same with writers 0x7E6FF46F (current+user, no propagation) / 0x7E6FF4C7 (current only, quiet) / 0x7E6FF507 (current only, full side effects; used by the conflict engine) / 0x7E6FF56D (user only, full) |
| 0x7E6FCAA8 / 0x7E6FCA9F | 0x7E6FE8B2 / 0x7E6FE765 | step to the next / previous value. Uses op slot +4 / +8 when present (note: 0x7E6FE8B2 tests +8 but calls +4). Default: walk the list (0x7E706FDE / 0x7E706FA3), skip values for which the conflict check returns 256, reverse when the walk is stuck, then 0x7E6FF3ED. Returns 128 if the setting is locked |
| 0x7E6FCAB1 | 0x7E6FEA00 | locked check, then op slot +12 (empty in all 250 records) or step-next (I: "cycle") |
| 0x7E6FCC32 (30 callers, mostly GUI 0x7E9E8xxx) | **0x7E7007F4**(id, mode, value) | selectability. mode 0 → 0 = allowed or 256 = not allowed; mode 2 → non-zero = setting forced/locked; mode 1 → apply the rules (§2.2) |
| 0x7E6FCB15, 0x7E6FCAD6, 0x7E6FCACC, 0x7E6FCAFA | 0x7E6FF741, 0x7E6FEE8E, 0x7E6FEE02, 0x7E6FEF7F | list count / item by index / value→index / index of a raw value (override slots 0x605B4C1C are checked first, 0x7E6FFFF5) |
| 0x7E6FCB29 | 0x7E6FFDDF | register the change-notify callback (pointer 0x602AE200; only registrar 0x7E9E6F81, the HFW layer) |

**Write path 0x7E6FF3ED(id, raw)** (the "full" write; V):
1. Writer: op slot +52 if present, else composite fan-out 0x7E6FED15, else 0x7E6FEA37 (Set_CameraUserInfo then Set_CameraInfo).
2. **Dependency propagation** 0x7E6FF833: look up the id (or each composite member) in the 86-record table 0x7E8266C4 `{u16 cond_id, pad, ptr u16 targets[], u16 n}` (290 targets in all). For each target, run the conflict rules (`0x7E7007F4(t, 1, 2000)`), then notify (step 4). The table is the inverted index of the conflict table: for example, cond 24 (exposure mode) → 24 targets {428, 10, 4, 157, 35, 2074, …}, and 64 (EV step) → {4}.
3. Op slot **+24 hook** (side effect). The gate 0x7E70098E always returns 1.
4. Change notify 0x7E6FFDE8 (callback at 0x602AE200), then 0x7E6FF997 → 0x7E704ABD for each id. 0x7E704ABD is an empty `retf` stub in v1.6.

**Mode controller proper** (V call graph; I meaning):
- **camera_start** 0x7E700C2E(dial, …). If already started (byte 0x605B7716), it goes to camera_set. Otherwise it reads infos 41, 26 and 109. When the mode changed (0x7E700B8C), it saves the old mode's settings with 0x7E706B75(old26, old109). Then it loads the mode (0x7E700993) and finishes with 0x7E700B95.
- **camera_set** 0x7E700D13 does the same without the start flag.
- **camera_end** 0x7E700CF9 clears 0x605B7716, calls 0x7E70212B and 0x7E7021F2, then runs **F021 0x7E7000BA**:
  - api_comm_Communication_Remote(0) through 0x7E70202E;
  - 0x7E701D0D;
  - strobe-off step **0x7E701D27**: api_rec_Charge_Strobe(0) 0x7E6885B2, api_rec_Control_Strobe(0) 0x7E6885A0, 0x7E704AC0(4), and SERV notice 0x03010007 through 0x7E68CCBD when a notify callback is registered;
  - **save** 0x7E706B75(info26, info109).
- **Mode load** 0x7E700993:
  1. mymode load 0x7E700E89;
  2. bank switch through infos 43/109/280/281/162 (Get/SetBank, 0x7E702095);
  3. restore 0x7E706BDB;
  4. preset apply 0x7E706EAA;
  5. 0x7E68025D(1) (busy) and 0x7E67FF81;
  6. re-apply all 92 conflict rules on the W plane (0x7E7008AD(1, 2000));
  7. hook batches 0x7E6FFD6A(1) and (0);
  8. dependency re-runs for 2239 and 158.
- **Bank save 0x7E706B75(k1, k2)** walks the 57-entry table 0x7E83EF4C `{u16 k1 = info 26 mode code, u16 k2 = info 109 group, ptr list, u16 n = 440, pad}`, ended by {0, 2000}. The list entries are `{u16 info, u8 bank, pad}`. For each entry it does `Set_CameraBankInfo(info, bank, Get_CameraUserInfo(info))`. There are 25 distinct lists:
  - P/A/S/M (3–6, group 0) put almost all ids in bank 0;
  - scene, ART (69–74, 85, 86, 91, 96, 163, 181) and movie P/A/S/M (76/77/89/90) put 52–150 ids in bank 1.
  - I: bank 1 holds the per-scene/ART values, so that they do not overwrite the P/A/S/M values.
- **Restore 0x7E706BDB** walks a 415- or 428-id list (0x7E84E194 or 0x7E84E4D2, chosen by 0x7E6FFF86). For each id: `Set_CameraUserInfo(id, Get_CameraBankInfo(id, bank))`, with bank 0 when the id is not in the mode list.
- **Mode presets**: table 0x7E834794 `{u16 info26, u16 info109, ptr {u16 id, u32 value}[], u16 n}`. Examples: P/A/S/M have 19 entries (24 := mode, 26, 43, …); scenes have 142–145; ART has 103. They are applied through mcon set by 0x7E6FFE55 (caller 0x7E70496B).
- **Resets.** Both resets set the busy byte with 0x7E68025D(1) and load ROM defaults with 0x7E67FF81 / 0x7E6801C8.
  - standard_reset 0x7E7010AC then resets 300 ids at 0x7E84DF32 (0x7E7068E3 → 0x7E706AC3).
  - full_reset 0x7E7010D6 also resets 26 and 109 to their ROM defaults (0x7E706F04; table 0x7E84C82C), restores the banks, resets 881 ids at 0x7E84D850 (0x7E7068F4), and reloads mymode.
  - Both end in the region-default loader 0x7E700F96. It reads info 4009 (destination area) and walks table 0x7E84EDF0 `{u16 area, u16 n, ptr ids, ptr values}`. Each value goes to the W plane, the current plane and both banks; ids 1009/1010 are skipped.
- mymode / custom: load_custom 0x7E6FCE7C → 0x7E700DAE then 0x7E6FF3ED for 3 ids; save 0x7E700E3A; clear 0x7E700F12 (resets 490–493 and 1000–1007).

**Callers outside mcon** (V, calls.tsv):
- HFW settings adaptor 0x7E9E7xxx: get 0x7E9E76BE, set 0x7E9E7D6C, step 0x7E9E7DC4/7DEF, `changeModeConflict` 0x7E9E7445.
- HIGHLEVEL live guide / shooting service 0x7E982579, 0x7E988693, 0x7E98955B.
- MyMode/Custom class 0x7EB92769–0x7EB929FB (`mcon_if_load_custom fail`, vtable method 0x7EB927AE → camera_end).
- CmpSqp 0x7EA8xxxx and 0x7E5037DF.

### 2.2 mcon: mode-conflict engine ("Search_Mode_Conflict") (V)
- Table **0x7E825DA8**: 92 records of 20 bytes `{u16 target, u16 alt_id (2000 = none), ptr blocks, u16 nblk, u16 0, ptr getter, ptr setter}`. It is hashed into 32 buckets at 0x605B6BB4 by 0x7E700907.
  - Each block is 16 bytes: `{ptr conds, u16 ncond, u16 0, ptr map, u16 nmap, u16 0}`.
  - A condition is 8 bytes: `{u16 id, s16 value, ptr getter}`. All conditions must be equal (AND). The getter, or Get_CameraInfo (or the W getter when 0x605B6BAE = 1), supplies the value.
  - A map entry is `{u16 from_gui, u16 to_gui}`. 965 blocks in all.
- **Pseudo-ids in conditions** (0x7E7002FF):
  - 2085 = 0x7E68E9F4(0x02021215);
  - 2059 = api_rec_Get_External_Strobe_State 0x7E688673;
  - 2334 = (0x7E68AE54() == 2); 2339 = (0x7E6886A0() == 1);
  - 2214 = 16;
  - 2236/2237 = counts from 0x7E683B75 over info 23;
  - 2238 = 0x7E6FFE4C; 2239/2242 = flags 0x7E704AC9/0x7E704AF5.
- **mode 1 (apply).** The first block whose conditions all hold rewrites the target's *current* value: map[user GUI value] → to (0x7E6FEBBE, current only). When no block holds, the current value is reset to the user value. So the user value is never lost.
- **mode 0 / 2.** mode 0: is `value` one of the map `to` values? mode 2: do all map entries force one value (locked)?
- After the rules, 0x7E70077A runs the per-id extra checks in table 0x7E818DC8 (3 × 12 B: ids 111, 509, 510 → 0x7E7002BA) and the gate info 15199.
- Examples (V bytes):
  - target 428: {44 = 1 or 4 = BULB/TIME → 1,2→2} {24 ∈ 115/36/37 → 0};
  - target 10: 21 blocks (ART BKT 406 = 1, ART 109 = 1 & 279 = 1, 324 = 1..5, 111 = 100..120 → value 0 becomes 15);
  - target 32: 669 = 1 or 482 = 1 (interval) or 2239 = 1 → 0.
  - All 92 targets: 4, 6, 10, 16, 19, 27, 28, 32 … 544, 592, 692, 2074 (`conf.py`).

### 2.3 TAKE_MAIN release sequencer (F007) (V engine; I meanings)
- **State variables:** current 0x60515DE0, next 0x60515DE2 (255 = none), argument 0x60515DE4, previous 0x60515DE8, source-enable mask 0x60515DEC, debug flag 0x60515DF0 (1 → `.exec(%d)` / `.post(%d)`).
- **Event loop:** TAKE_MAIN waits on the event flag with the id at 0x7E43EBE8. It has three sources:
  - bit 1: internal post list (0x7E5A0DD0) → B table;
  - bit 2: command queue **0x7E43ED96** (16-byte messages, event = msg+8) → **A table** (state +12);
  - bit 4: notification queue **0x7E43EDA8** (12-byte messages) → **B table** (state +16).
- **Tables and handlers:** each table is `{u32 event, ptr handler}` and ends at event 0xFFFF. A handler gets a0 = message and returns 0 for OK. 0xFFFF means "no entry" (0x7E59A294 logs it); other non-zero values log error 0x25000E02–07. The ignore handlers are 0x7E582546 (A) and 0x7E58254A (B), both `clr d0; retf`.
- **Transition:** 0x7E5823CC(state ≤ 26, arg) sets "next" (error 0x25000E08 if state > 26). 0x7E582414 applies it: previous = current, current = next, then the entry function (state +8) is called with (previous, arg). It repeats while the entry function sets another next state. The mask helpers are 0x7E5824DF (or) and 0x7E5824CC (clear).
- **Sends.** 0x7E582857(queue, cmd, payload) → Oimf 0x7E50689F. The queues are: 0x7E43ED98 = TAKE_EXPOSE, 0x7E43ED9C = TAKE_FOCUS, 0x7E43ED9E = TAKE_FUNC, 0x7E43EDA0 = TAKE_FUNC_CP (V by the readers 0x7E5829E8, 0x7E5881D9, 0x7E595527, 0x7E5996F8).
- **The 27 states** of 0x7E790860 `{u32 id, ptr name, ptr entry, ptr A, ptr B}`, with the sends verified at the given addresses. Command names use the corrected numbering of §4.2.

| Group | States (id) | Verified behaviour |
|---|---|---|
| idle | Idle 0, Damage 1 | Idle: A0/A2 → RdyStart. Damage: 8 of its 14 A events (A0, 2, 6, 7, 8, 9, b, c) go to the reject handler 0x7E59A3AD; A5, Ae, Af, A10, A11, A13 go to the ignore handler 0x7E582546 (A5 2026-11-09) |
| release-ready (half press, I) | RdyStart 2 → RdyFcsRdy1 3 → RdyFcsRdy2 4 → RdyFcsRdy3 5 | Rdy1 sends FUNC 0x35. Rdy2 sends FCS 0x403 `release_idle_ready`; its B-e handler goes to 5, or to 7 when byte 0x60517D48 ≠ 0 (0x7E5AAB0F). Rdy3 sends EXP 0x500 and FCS 0x400 `release_idle_start` |
| wait for 2nd trigger (I: S2) | RdyTrig2Wait 6, RdyFastTrig2Wait 7 | A8/Ab → RdyFcsTake; A7 → RdyAbort. In state 6, A2 → RdyAbort too. In state 7, A2 maps to 0x7E5AADBC, which returns 0xFFFF and sets no state (A5 2026-11-09), and A6 → 6 |
| take / abort | RdyFcsTake 8, RdyFcsAbort 9, RdyAbort 10, RdyEnd 11 | 8: B9 → EXP 0x600 `release_take_start`. 9: B6 → FUNC 0x35 + EXP 0x401 `release_ready_end` (F007 0x7E5AB1BB). 10: B6 → EXP 0x501 `release_idle_end` |
| still capture | Standby 12 → StlRdy1 13 → StlRdy2 14 → StlTake 15 / StlLiveTake 16 → StlEnd1 17 / StlEnd2 18 | Standby (handler 0x7E5A190C for both): A9 sends EXP 0x601 + FCS 0x501 (`release_take_end`), replies (0x7E582595) and goes to **RdyTrig2Wait 6**; A7 sends EXP 0x701 + FCS 0xE01 (`release_end`) and goes to RdyAbort 10 (A5 2026-11-09). StlRdy2 entry calls 0x7E5A4BA3 → strobe calc F010. StlTake: FCS 0x800 `mf_start`, B20 → 0x801 `mf_end`. StlEnd2: EXP/FCS release_take_end + release_end, FUNC 0x30/0x35. B35–B37 → Damage |
| sequential with AF | ContAfAe 19, ContAf 20, ContAfStop 21, ContWait 22 | 19: B10 → FCS 0x600 `take_continue_start`. 20/21: A7/Ae/A11 → StlEnd1 with EXP 0x801 + FCS 0x601 `take_continue_end` |
| high-speed sequential | HsContTake 23, HsContWait 24, HsContRdy 25, HsContEnd 26 | HsContRdy entry also calls 0x7E5A4BA3 (strobe). A7/Ae/A11 in 24 → HsContEnd |

- **A events** (V where a sender is named):
  - A7 = take-ready abort (api_rec_Take_Abort_Takerdy 0x7E6897F4 sends 7);
  - A0x13 = api_rec_Update_Bulb_Lv 0x7E68C46D (msg+8 = 19);
  - A8 = the event sent by the UI path `RdyTrg2Err` 0x7E503444 (I: full press / trigger 2).
  - A0, A2, A5, A6, A9, Ab, Ac, Ae, Af, A10, A11 are not named (I: half-press, release, mode change and so on).
- **B events** are completions from the TAKE_* tasks. B25 → 0x7E5A4459 and B27 → 0x7E5A31BE appear in almost every state (I: global error and lens events). B2d/2e/30–32 are ignored in most states.
- The half-press AE/AF lock commands (EXP/FCS `lock_start` 0x100) are not sent directly by the state entry functions. They go through helpers in the TAKE_FOCUS module (0x7E587D33, 0x7E587DA8, 0x7E587E5C, 0x7E587ED8; not decoded).
- **Flow summary (I):** S1 → Idle→RdyStart→RdyFcsRdy1–3 (focus and exposure ready, then `release_idle_start`) → RdyTrig2Wait → S2 → RdyFcsTake (`release_take_start`) → Standby → StlRdy1/2 (strobe calc) → StlTake (exposure; focus held with `mf_start`) → StlEnd1/2 (`release_take_end`, `release_end`) → Idle. Sequential shooting uses Cont* and HsCont*.

### 2.4 Strobe exposure (F010) and light-source selection (F011)
- **Light-source mask** bits 1/2/4/8. What the code checks (V): bit 1 needs the internal/clip-on flash to be usable, bit 2 needs an external flash on the hot shoe, bit 4 is always available, and bit 8 is never available. What the bits mean (I): 4 = wireless RC or a non-TTL external unit; 8 = a built-in pop-up flash, which the E-PM2 does not have.
  - **0x7E5E2258(src)** answers availability:
    - src 1 → 0x7E5E1B11() == 0 (internal OK). 0x7E5E1B11 returns an inhibit code: 0 at once when 0x7E5E1CAF() = 1 and 0x7E457C75(0x2981) = 1; otherwise 0x2C50 when 0x7E509CA3(0x1215) **== 1** (`mov 11344,d0; cmp 1,d1; beq exit`), else 0; (A4 2026-11-09)
    - src 2 → 0x7E5DEBAD() == 1 (external state 0x6054AC64 = 2 and 0x6054AA7C = 0);
    - src 0 → either; src 4 → 1; src 8 → 0.
  - **F011 0x7E5E22A6(req)** maps req (0 → 15; 1/2/4/8/16 kept; else &15), clears 0x8, clears 0x1 if internal is inhibited, clears 0x2 if no external flash, then calls 0x7E5E1D38(mask, req).
  - The four functions after it are light-exec callbacks (V `movm` prologues): 0x7E5E2300, 0x7E5E2346 and 0x7E5E2387 are loaded by `strobe_light_exec` 0x7E5E2419 (at 0x7E5E24E6, 0x7E5E2597, 0x7E5E2573/25E6/2661); 0x7E5E23F5 is loaded only inside 0x7E5E2387 (at 0x7E5E23AB). (A4 2026-11-09)
- **Flash selection 0x7E5D1659** (`check_select`; inputs onoff, ae_chg, mode_stb_expose, general, rc_mode, after_movie) (V):
  - It clears and sets the status words 0x6054A3DE (internal), 0x6054A3E0 (external), 0x6054A3E2 and 0x6054A3E4.
  - It reads the external flash state with 0x7E5E2152 / 0x7E5E20E8 (records 0x6054A82C / 0x6054A850).
  - When an external flash is attached, it branches on its type, the u16 at 0x6054A82E:
    - type 64 with input 7 set → 0x6054A3E4 = 2, mask 1;
    - type 1 or 16 → 0x6054A3E0 = 2 (or 1 when 0x7E5E2140() = 2), mask 2;
    - other types → 0x6054A3E0 = 1, mask 4.
  - After that: +1 if the internal flash is usable; types 16 and 32 clear bit 1 and 0x6054A3DE.
  - Then the RC and second-source checks (0x7E5E2258(4/2/8), prm 0x8F31).
  - It returns the mask and logs it when debug mask 0x10000 is set (0x7E5DADCF).
- **F010 0x7E5D4385** (caller 0x7E5A4BA3 from StlRdy2 / HsContRdy) (V flow):
  1. selection (above);
  2. internal flash → 0x7E5D05A2;
  3. external (0x6054A3E0 = 1) → GN calculation 0x7E5D0659 (`mode_stb_quantitiy`, `ext_gv_max(4.3)`, `ext_stb_gv(4.3)` in 4.3 fixed point), light exec 0x7E5D4859 → 0x7E5E2419, and a wait on the strobe event 0x7E5D301B(0x7E43EBCE, 2);
  4. it fills on_time, ext_stb_gv, autosv, stbtv, stbav, check_lamp, over_under, stb_ae_ratio and `teijouhosei` (steady-state correction, I), and prints them when debug mask 0x400000 is set.
- The request block is built just before, by 0x7E5A9324. That function reads about 50 prm tags, for example 0x9B21 = info 180 Flash RC Mode, 0x8892 = info 569, 0x88C2 = 570, ISO 0x810A, and 0x9E01–0x9EB1.
- **Sync and red-eye** (V field names, I wiring):
  - STB_EXPOSE_INFO (dump 0x7E5D4990) has mode_redeye, mode_slow, mode_slow_2nd, mode_stb_sync, mode_stb_rc_fp and stbfp.
  - Red-eye pre-flash runs through the event objects `STB_REDEYE` / `STB_RED_LIGHT` (0x7E5D68D7).
  - The PTP flash mode (F078) comes from infos 16, 544 (strobe on) and 551 (red-eye).
  - Which code writes mode_slow, mode_slow_2nd and mode_stb_sync from the settings was not traced.

## 3. Record formats and patterns

### 3.1 Value-list record, 505 × 20 B at 0x7E84A0B8 (V; replaces 09a §1.1)
- Layout: `+0 u16 info`, `+2 u16 variant key`, `+4 ptr raw[]`, `+8 ptr gui[] (u32, NULL in 426 records → gui = raw)`, `+12 u16 total bytes`, `+14 u16 element size`, `+16 u8 clamp (1 = stop at the ends, 0 = wrap)`, `+17 u8 type`, `+18 u16 0`.
- **Lookups:** 0x7E70760A → 0x7E70782A takes the first record of an id (128-bucket hash 0x605B9750, built by 0x7E7077D3). 0x7E707613 → 0x7E707854 matches id **and** +2.
- **Variant key** (+2): 128 is the default. 11 ids have 3 lists with keys 85/128/256, chosen by the +20 selector = info 64 (I: 1/3, 1/2, 1 EV steps): 2, 3, 4, 5, 6 (85/256), 17, 86, 140, 480, 495, 496. Info 9 has keys 0/1, chosen by info 15129.
- **Types** (from the step dispatcher 0x7E70761C and 0x7E70777F):
  - 1 = u8 (0x7E7074B5); 2 = s8 (0x7E7074FD);
  - 3 = s16 nearest match, midpoint search (0x7E707449; all EV lists);
  - 4 = s16 exact (0x7E7073FD); 5 = u16 (0x7E707547);
  - 6 = composite, 64-byte elements compared with memcmp (0x7E707591, 0x7E707147).
- Counts: 264 / 12 / 26 / 98 / 30 / 75 records of types 1–6.

### 3.2 Per-setting operation record, 250 × 60 B at 0x7E814864 (V)
- The records are hashed into 64 buckets at 0x605B52D8 (nodes 0x605B53D8) by 0x7E6FF6C2. Lookup is 0x7E6FF717(id), which returns the record or 0.
- Slot layout (non-zero records in brackets):

| Off | Use | n | Callers / pattern |
|---|---|---|---|
| +0 | u16 info, +2 = 0 | 250 | |
| +4 / +8 | custom step next / previous | 16 / 16 | ids 2, 3, 4, 6, 9, 17, 86, 99, 140, 459–462, 480, 495, 496; 0x7E7012D3–0x7E703F5A. They call 0x7E707053 / 0x7E707018 (variant list step) and 0x7E7007F4 |
| +12 | cycle override | 0 | 0x7E6FEA00 |
| +16 | index of the current value | 9 | `Get(id); Get(64); call 0x7E707115` (F022 0x7E701B1F) |
| +20 | list selector, current plane | 12 | 15-byte stubs `add -4,sp; mov 64,d0; call 0x7E67F822; ret`: 0x7E6FE6C7 (info 64, 10 ids), 0x7E6FE6E5 (info 141 → id 6), 0x7E6FE705 (info 15129 → id 9) |
| +24 | **post-write hook** (side effects, interlocks) | 218 (97 fns) | called by every full write and by batch 0x7E6FFD6A(0) (all records except id 108) |
| +28–36 | unused | 0 | |
| +40 | index, W plane | 5 | 0x7E6FE64E… (GetW 0x7E67FCB8) |
| +44 | list selector, W plane | 8 | 0x7E6FE6D6 (W info 64), 0x7E6FE6F5 (W 141) |
| +48 | **post-write hook, W plane** | 186 (72 fns) | batch 0x7E6FFD6A(1) after re-applying the conflicts on the W plane (0x7E7000F8, mode load) |
| +52 | custom writer (replaces Set_CameraInfo) | 10 | e.g. 0x7E6FE445 (id 31) / 0x7E6FE482 (id 58): write current and user, then api_disp_Disp_Set_Brightness. 0x7E6FE464 (265) / 0x7E6FE4A1 (307): Disp_Set_ColorTemp. Also 0x7E703AE5 (180), 0x7E7040CD (292), 0x7E70411A (64), 0x7E7042E9 (113), 0x7E6FE4BF/DF (453/452) |
| +56 | read by 0x7E6FF063/0x7E6FF0B5 | 0 | |

- **Record-callback patterns.** Each one is reached only through these data words and starts with `movm` or `add -4,sp`. Classify a new mcon function by its callees:
  - **Exposure recalc hook:** calls 0x7E68781D api_rec_Calculate_Expose (ids 2, 3, 4, 6, 16, 17, 64, 86).
  - **Rec-mode notify hook:** calls 0x7E68AE3B api_rec_Notify_Rec_Mode_Change (26, 111, 268, 398, 406, 444, 216).
  - **Picture-mode parameter mirror:** 23 B, `mGetG(id); call 0x7E70430B`. 0x7E70430B switches on the picture mode (0x7E702A71) and writes ids 59, 308, 130, 131, … (I: contrast, sharpness and so on). 19 hooks for id groups 297–300, 117–119, … 364–381.
  - **Twin copy:** 23 B, `mGetG; call 0x7E702602` → 0x7E701CCD/0x7E701CED + 2 × 0x7E6FF3ED. Pairs 91/133, 92/134 … 642/644, 643/645 (I: still/movie twins).
  - **Group writer:** `mGetG; call 0x7E702E26; 6–8 × mSetG 0x7E6FEAE0` (211, 301–305, 184–204, 635–639).
  - **Interlocks:** mSetG with constant ids. Examples: 268 ↔ 482 (0x7E703986 / 0x7E7039C4), HDR BKT 476 (0x7E703540), AE BKT 480 (0x7E7034DE), FL BKT 140 (0x7E703471), Picture Mode show flags (0x7E703FDA, 17 ids), Live Bulb/Time copy into 436 (0x7E7045C4 via 0x7E7022F0).
  - **+48 twins:** live in 0x7E704E75–0x7E706835 and 0x7E6FFC0A–0x7E6FFD4D. They call the W helpers 0x7E704B75 / 0x7E706420 / 0x7E6FFC0F / 0x7E700861 instead of mGetG / mSetG.
- **mcon veneer pattern:** `1c` (exthu d0) + `cd/dd` call + `df 00 04` (ret [],4), 8–11 bytes, in 0x7E6FCA60–0x7E6FCD3C.
- **Busy-guarded wrapper pattern:** call 0x7E680266 (busy byte), compare with 1, then call 0x7E6FCCF3, then the operation.

### 3.3 Other mcon tables (V)
- 0x7E8182FC: 68 × 34 B composite id lists (09a).
- 0x7E818CC8: ART show-flag hash (09a).
- 0x7E826AFC: picture-mode → flag-id pairs (09a).
- 0x7E84C82C: ROM default per id (0x7E706F04, 18 callers).
- 0x7E834A4C–0x7E83EF4B: 25 bank lists (440 × 4 B each).
- RAM: 0x605B6BAF / 0x605B6BB0 nesting counters for the conflict checks; 0x605B4CB8: 20 × 12 B change log `{u16 id, u16 used, u32 gui, u32 user_gui}` (0x7E6FF9F8).

## 4. Corrections

1. **Section 05 §5:** "SERV_S1 … called through 0x7E68CCBD from the REC (0x7E701D27)" has the wrong module label: 0x7E701D27 is mcon code, not REC. The call edge itself is real: 0x7E701D27 calls 0x7E68CCBD at 0x7E701D50 (d0 = 0x03010007, d1 = 1), and 0x7E68CCBD = `call 0x7E8F91DD` (SERV_S1) (V). (A4 2026-11-09)
   - 0x7E701D27 is mcon code. Its only caller is F021 0x7E7000BA. F021's only caller is camera_end 0x7E700CF9, which is reached from veneer 0x7E6FCD9F (shell `camera_end` and the HFW vtable method 0x7EB927AE).
   - It sends SERV notice 0x03010007 when a change-notify callback is registered, after api_rec_Charge_Strobe(0) and api_rec_Control_Strobe(0).
   - The other mcon caller of 0x7E68CCBD is 0x7E701E42 (external-strobe state, through 0x7E701D68). Coverage review 2 also named the `modedump`/`modeback` commands and loadCustom; only the `camera_end` command and the method next to loadCustom reach it.
2. **Section 02 §4 command tables (V): the "cmd" column is the hash key, and the key is cmd + 1.**
   - 0x7E791478 (TakeExp) and 0x7E7928B0 (TakeFcs) are 32-slot open-addressing hash tables `{u32 key, ptr handler}`. Key 0 is an empty slot → default handler (0x7E582DFC logs 0x25000701).
   - The dispatchers do `inc d1` before the lookup (0x7E582A48, 0x7E588321).
   - Real TakeExp commands: mode_start 0 (key 1 → 0x7E582A71, `[TakeExp]mode_start`), mode_end 1, lock_start 0x100, lock_end 0x101, preview 0x200–0x202, panorama 0x300/0x301, release_ready_start/end 0x400/0x401, release_idle_start/end/ready 0x500/0x501/0x503, release_take_start/end 0x600/0x601, release_end 0x701, take_continue 0x800/0x801, lv 0x900–0x902, iaf 0xA00/0xA01/0xA04, movie 0xB00/0xB01. (A4 2026-11-09)
   - Real TakeFcs commands: mode 0–2, lock_start 0x100, lock_end 0x101, lock_start_end 0x102, panorama 0x200/0x201, release_ready 0x300/0x301, release_idle_start/end/ready 0x400/0x401/0x403, release_take 0x500/0x501, take_continue 0x600/0x601, lv 0x700–0x702, mf 0x800/0x801, iaf_restart 0x900, iaf_pause 0x901, movie 0xA00–0xA03, release_end 0xE01.
   - So **F007's EXP 0x401 is `release_ready_end`**, not `release_ready_start`. The senders confirm it: they send matching pairs (EXP 0x500 + FCS 0x400 = both `release_idle_start`).
3. **Section 07 §2.1:**
   - The 64-bucket entries are the 60-byte operation records (§3.2). Slot +20 is the list-variant selector, not a converter.
   - The 505-record pointers are raw/GUI value arrays, not "per-mode availability matrices". Availability is the separate 92-record conflict table 0x7E825DA8 (§2.2).
4. **Section 10a:** the 60-byte records are per-setting operation records. The cited hooks (0x7E7039C4, 0x7E703986, 0x7E703540) are their **+24** post-write hooks (V).
5. **09a §1.1:** add +2 = variant key, +16 = clamp flag and the type codes of §3.1. The "+17 type 6 = composite" reading is confirmed.
6. **Coverage review 1, F011:** "always clears bit 8" means it clears the value 0x8 (`and -9`), the light-source bit that is never available (V).
7. **Regions:** mcon is 0x7E6FCA60–0x7E70787F (not ~0x7E6FC000–0x7E708000). 0x7E6FC000–0x7E6FCA5F is face code (FACE_EXEC, FaceXX wrappers, FACE_PT0/1).

## 5. Open questions
1. The names of TAKE A events 0, 2, 5, 6, 9, b, c, e, f, 10, 11. A full sender scan of queue 0x7E43ED96 is needed: 0x7E50334B–0x7E50379D and the api_rec_Take_Ready* functions build the message at msg+8 through helper 0x7E67EA30.
2. Why the sequencer sends FCS `mf_start`/`mf_end` around StlTake (I: focus hold during exposure), and the meaning of TAKE_FUNC commands 0x30/0x35/0x3D.
3. The W plane 0x605A38E0: who seeds it before a mode load (0x7E67FC9C copies all 701 user values through 0x7E67F899?), and whether the GUI ever reads it.
4. Which ids use the +12 and +56 slots in other bodies. Both are empty on the E-PM2.
5. Where mode_slow / mode_slow_2nd / mode_stb_sync / mode_redeye are set from infos 16/544/551 (start at 0x7E5A9324 and at the STB_EXPOSE_INFO filler 0x7E5D0F5C).
6. The A/B event semantics of the B25/B27 global handlers (0x7E5A4459, 0x7E5A31BE).
