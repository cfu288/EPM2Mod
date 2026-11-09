# 15c — C++ app layer: class index, play-notification protocol, statecharts, Dev part 1

**Scope:** block 0, the C++ app layer 0x7E966000–0x7EBA48BB (Tra / Ope / Cap / Cmp / Com / Ctg / Dev). The OXF runtime (0x7EBA48BC–) and OKAO (0x7EBA7BC1–0x7EBABF8D) are out of scope (13c). This section builds on 06, 13c and 14c. It answers the coverage round C3 gaps (round3-review2/3: F041–F050 and the "weakest areas").
**Labels:** **V** = verified (read in code or bytes); **I** = inferred (strings, names, layout, a rule).
**Outputs:** `15c-class-index.tsv` (495 rows: 224 classes/devices + 271 observer classes), `15c-event-id-fixes.tsv` (1,242 owner corrections). **Scratch:** `.../scratchpad/d3/app/`: `cls.py`/`idx.py`/`names.py`/`mkidx.py` (index), `tests.py` (isTypeOf scan, 6,201 sites / 1,095 ids), `evown.py`/`mkfix.py` (owners), `sc.py` (statechart extractor), `ent.py` (state-entry finder), `subs.py` (EVFW subscriptions), `obs.py`.

## 1. Area and boundaries

The full per-class ranges are in `15c-class-index.tsv` (columns start/end). Rule (V as an address rule): a class file starts at `min(getInstance, ctor)` and ends just before the next class start, minus a trailing run of event methods (ctor/isTypeOf/dtor). Ranges in the Tra/Ope area (0x7E966000–0x7E9EB317) are coarse: many Ope/OlyApi classes are not reactive and have no row (13d §6.2 covers OlyApi), so one row can cover several files (e.g. 0x7E99A20E–0x7E9CFDFA).

Boundary fixes found in this round (V unless marked):

| Range | Contents |
|---|---|
| 0x7EB0A5E7–0x7EB16FF3 | `Cmp_PlayComponentBase` (ctor 0x7EB0A5E7 … state entries to 0x7EB16AF0). modules.tsv first_fn 0x7EB0AF9A is late |
| 0x7EB2887C–0x7EB2BB80 | `CmpPEvV_PlayEventViewComponent` (getInstance 0x7EB2887C; `rcv Request` dispatcher 0x7EB2B6C8 is inside) |
| 0x7EB2BB81–0x7EB2ECCF | `Cmp_PlayIndexComponentBase` (`Cmp_IndxBase`): ctor 0x7EB2BB81 to the last function before CmpPli getInstance 0x7EB2ECD0 |
| 0x7EB33B24–0x7EB39215 | `CmpPLgh_PlayLightBoxComponent`; it ends just before the CmpPMov getInstance 0x7EB39216 (the facade ctor 0x7EB39251; the `Cmp_PlayMovieArchitecture createActiveRelations` string user is 0x7EB392F2) |
| 0x7EB3D990–0x7EB3DEF6 | observer classes **of other classes**, linked after CmpPMov: 8 `Cmp_PlayComponentBase` members (ctor callers 0x7EB0A5E7), the 7597 observer of the PlayCom architecture (caller 0x7EB08CA4), 3 CmpPMov-facade observers (caller 0x7EB39251) (§3) |
| 0x7EB79137–0x7EB7A6C7 | event-method run between Shutdown and the shooting facade: Shutdown-package events and the play-package blocks 7591–7611, 8041–8566 (their ctors 0x7EB79CF2–0x7EB7A148) |
| 0x7EB84345–0x7EB85562 / 0x7EB85563– | Com_EvSenderManager (14c) / Com_ framework; `Com_ManagersSubTransition` ctor 0x7EB8573D, base dtor 0x7EB857A1, accept-test 0x7EB857CA (§4.8) |
| 0x7EB8C265–0x7EB93422 | Dev part 1: 14 device units, §5 |

modules.tsv `last_fn` gaps (I2 of review 3): many Cmp/Cap rows end early because last_fn is the last function that *names* the file. The D3 fix pass found that this does **not** hold for the three rows named in the review: their last_fn values were already right, and only the CmpPEvV first_fn and the Cmp_PlayComponentBase row changed (coordinator 2026-11-09, from fixes-D3). Use the class index instead. The three named in the review: **CmpPLgh 0x7EB33B24–0x7EB39215**, **CmpPEvV 0x7EB2887C–0x7EB2BB80**, **Cmp_PlayIndexComponentBase 0x7EB2BB81–0x7EB2ECCF** (V).

## 2. Class index (`15c-class-index.tsv`)

**How it was built (V):** reactive classes = functions that store a vtable and call setActiveContext 0x7EBA675E (140 ctors). Facades = callers of the 2-call wrappers `setActiveContext(this); setActiveContext(this+K)` (e.g. 0x7EA331AE for CapTak, K = 332): 92 facade+reactive pairs. Singletons = the 140 getInstances of 14c `gi.txt`. The name is the getName (vt+144) string, else a `.cpp` string, else a log tag (`X::`), else a hand name (`names.py`); the `label` column says which. Columns `ids_tested` / `ids_created` list the event ids tested / built inside the range. That lets a reader classify a handler by its ids.

**Hierarchy (V, ctor chains):**
- OMReactive 0x7EBA6375 → Com_ base 0x7EB8701F → 0x7EB88CED → **Com_ init-chart base 0x7EB87AC9** → Cap init base 0x7E9EF709. 34 Cap classes derive from 0x7E9EF709 and 12 Cap classes derive directly from 0x7EB87AC9 (CapTak, CapBoo, CapFls, CapIod, CapRec, CapPow, CapThr, CapMed_MediaManager, CapBea, CapHis, CapBuf, CapPPnr).
- 0x7EB88CED → 0x7EB874E7 (`hndNotCsm`) → 0x7EB887E0 → 0x7EB883B2 → **Com_ component-manager base 0x7EB87E25** → {`Cmp_ComponentManagerWithBoot` (CM) 0x7EA7C89C, `CmpSdw_ShutdownComponent` 0x7EB781D4}. 0x7EB883B2 → Ctg_ComponentSwitcher 0x7EB94576. 0x7EB887E0 → Ctg category base 0x7EB95CB1.
- **Play chain (fixes 13c §3):** CM 0x7EA7C89C → `Cmp_PlayComponentBase` 0x7EB0A5E7 (10 subclasses: PCom, Bgc, CCom, PCol, PCw, PEvV, PPnr, PPho, PSou, and the next base) → `Cmp_PlaySingleComponentBase` 0x7EB54718 (7: PEvc, PLgh, PMov, PRec, Pls, PSld, and the next base) → `Cmp_IndxBase` 0x7EB2BB81 (4: PCal, Pct, Pli, and the next base) → `Cmp_PlayEditComponentBase` 0x7EB1DA86 (16: CPic, the 12 `CmpE*`, Era, PSel, RPri, SOve). CM's other subclasses are `CmpFnc_FunctionComponent` and `Cmp_PlayerComponentBase` 0x7EB6EDA3 (→ `Cmp_PictBridgeComponent`). All 38 play classes (9 + base + 6 + base + 3 + base + 16 + base) carry the running handler of §3.3.
- `Com_ManagersSubTransition` 0x7EB8573D has 15 subclasses (§4.8).

**Observer rows (V shape):** each 17-byte ctor `call 0x7EB85D67; mov VT,d0; mov d0,(a0); ret` gives one row: vtable, update function (slot 0), the event it builds, and the owner class (the class whose ctor calls it). 243 of the 271 build an event (most in the 75-byte GEN shape, 13c §3); 28 build none (relays, 14c §3).

## 3. The play-component notification protocol (`evTraCmpPly_*`, 7591–7611)

### 3.1 Mechanism (V)

1. **Members.** The `Cmp_PlayComponentBase` ctor 0x7EB0A5E7 builds 8 observer members (each 24 B, base 0x7EB85D67). It sets the target (+20) of +584/+656/+680/+704/+732 to `this` (0x7EB85DAB).

| Member | Observer ctor / vtable | update() | Event GENed to +20 |
|---|---|---|---|
| +584 | 0x7EB3DA46 / 0x7EC792BC | 0x7EB3DA61 | 7611 |
| +656 | 0x7EB3DBED / 0x7EC79338 | 0x7EB3DC08 | 7607 |
| +680 | 0x7EB3DC53 / 0x7EC79354 | 0x7EB3DC6E | 7604 |
| +704 | 0x7EB3DCB9 / 0x7EC79370 | 0x7EB3DCDA (118 B: reads a progress value first, §3.2) | 7605 |
| +732 | 0x7EB3DD50 / 0x7EC7938C | 0x7EB3DD6B | 7606 |
| +756 / +780 / +804 | 0x7EB3DDB6 / 0x7EB3DE21 / 0x7EB3DE8C | 0x7EB3DDD6 / 0x7EB3DE41 / 0x7EB3DEAC | 7600 / 7599 / 7598 |

   Other users of the same block: the PlayCom architecture facade (ctor caller 0x7EB08CA4) owns the 7597 observer 0x7EB3D9EA/0x7EB3D9FB. The CmpPMov facade 0x7EB39251 owns three observers that build 7603/7601/7602 (0x7EB3DAAC/0x7EB3DB17/0x7EB3DB82). CmpPMov alone tests 7601–7603. 7591–7596 are tested only in `Cmp_PlayerComponentBase` and `Cmp_PictBridgeComponent` (PictBridge states 14–21). 7591, 7592 and 7594–7596 have no ctor (vtable-only), so nothing sends them (V).
2. **Subscription.** `app_select_display_execute` 0x7EB0B054 (`Cmp_PlayComponentBase.cpp`, 81 callers) registers the members with the EVFW router (14c §2.4). +680 is registered with **11775** for a request handle; +656 is subscribed (11776) to APP_EVENT code 0x02020002 and +732 to 0x03010005. +584 is subscribed to 0x04020181 in 0x7EB0ED3C. +756/+780/+804 sit on CapDpv (+828) notification lists: 0x7EB12BD9 (9 callers, the unsubscribe step) removes them via CapDpv iface slots 31/32/33 (vt+124/+128/+132), then calls CM unsubscribe 0x7EA7DB1E.
3. **Delivery.** HLS_EVENT receives the APP_EVENT → EVFW → `observer.update()` → `new` event → GEN to the component (`vtbl[1]`).
4. **Handling.** The id is consumed by the component's running handler (§3.3). That handler usually unsubscribes first (11779 with the same code), then acts.

**11775 is `evHfwReqRegisterEvent`** (V: DevRec 0x7EB92CEB logs `evHfwReqRegisterEvent(APPEVENT_STATE_STEP)` and builds 11775 through ctor 0x7E96B3AB; fields +28 code/handle, +32 observer, +36, +40). 14c called it "register forward".

### 3.2 Ids

| Id | Name | Sent by | What the handler does (V call; meaning I) |
|---|---|---|---|
| 7591–7596 | (PictBridge/Player notifications) | 7593 only: 0x7EAFF4A6, 0x7EB6FDB8 | PictBridge states 14–17 wait for 7591 (→ 13); 19–21 use 7592–7596 |
| 7597 | histogram update | PlayCom facade observer | 0x7EB0F294 `Cmp_Play%s histogram_update` → +848 vt+48 |
| 7598 / 7599 / 7600 | display notifications (CapDpv lists) | members +804 / +780 / +756 | 0x7EB10E85 / 0x7EB10E64 / 0x7EB10E3E → `SEND_AFTERACK_PLAY` 0x7EB0EA1E with (kind, sub, value) = (3, 1, CapDpv slot 29) / (2, 24, 0) / (2, 24, 0xF0000001) |
| 7601–7603 | movie notifications | CmpPMov facade observers | CmpPMov only |
| **7604** | **`evTraCmpPly_NotifySelectDisplayExecuteEnd`** (V: string in its handler) | member +680 (request-handle forward, 11775) | 0x7EB109D3 (1,062 B, `Cmp_PlaySingleComponentBase rcv [...] 1..14`): unsubscribes (11779 ×3), APP_EVENT set-event 0x7E67D2C7, re-subscribes (11776), self-GEN 7606 |
| 7605 | progress notify | member +704; update() reads `api_media_Get_Media_Progress` / `api_play_Get_Beauty_Edit_Progress` / `api_picfile_Get_Create_PictureFile_Progress` by kind (+24) | 0x7EB10DF9 → after-ack (3, 3, progress) when progress ≥ the u16 at +610 |
| 7606 | APP_EVENT 0x03010005 arrived | member +732; also self-GEN by 0x7EB109D3 | unsubscribe 0x03010005, 0x7EB0F68E(0x600), self-GEN 7608 |
| 7607 | APP_EVENT 0x02020002 arrived | member +656 | 0x7EB0CFEA, 0x7E67D5E2, 0x7E67D293 (appevent set) |
| **7608** | **`evTraCmpPly_NotifyDisplayExecuteTimerIdleEnd`** (V: CmpPli 0x7EB3089F tests only 7608 and logs it) | 38 self-GENs (one per running handler) | `after_app_display_select_execute_end` 0x7EB0F0D2 → GEN 7609 |
| **7609** | **`evTraCmpPly_NotifySelectExecuteEnd`** (V: CmpEAsp `save_start_enter` 0x7EABA04C tests only 7609 and logs it) | 0x7EB0F0D2, CmpPLgh 0x7EB33E6E, CmpPSel 0x7EB4FA8E | consumed by the work state that waits for the redraw (138 test sites), e.g. erase state 37 (F045) |
| 7610 | execute-end ack step | 40 creators in the 38 play classes (the erase-state copies) | ACK to the API (0x7EB0EC1E, e.g. code 80, result 0), then self-post 12067 |
| 7611 | APP_EVENT 0x04020181 arrived | member +584 | unsubscribe 0x04020181, 0x7EB0F157. 0x04020181 is also subscribed by PlaySingle `start_effect` 0x7EB60753 (I: display effect end) |

### 3.3 The 1.5 KB running handler (F041 family) (V)

- **Copies:** 38 functions of 1,500–2,200 B, one per play class, each the fall-back (parent) handler of that class's states. Original: 0x7EB14F8E (`Cmp_PlayComponentBase`). The copies are 0x7EAABC33 7EAAEBBC 7EAB2756 7EAB5747 7EAB9261 7EABD816 7EAC29C7 7EAC7D26 7EACCE9A 7EAD0BB9 7EAD4DE5 7EAD8F50 7EADCC78 7EADFF45 7EAE555D 7EAE9CF2 7EB021F2 7EB05D26 7EB181C1 7EB1AF51 7EB1E186 7EB2511F 7EB29279 7EB2CC08 7EB2FBB2 7EB34D9B 7EB3A4C2 7EB3ECB8 7EB47A3B 7EB4C862 7EB517F9 7EB56C81 7EB5E9AA 7EB681FE 7EB6CCF6 7EB70974 7EB751B9. Each carries the class's `.cpp` log string, which is why modules.tsv uses it as first_fn for most play rows.
- **Signature:** the 63-byte single-trigger handler, repeated for exactly these 21 ids: **7597–7600, 7604–7608, 7611** (play half) and **11566, 11761, 11769, 12068, 12069, 12282, 12283, 12962, 13363–13365** (CM half). Some copies add class ids (e.g. CmpPMov 7601–7603, 8521; CmpPSld 8541–8546; CmpPPnr 8561–8565; 7007–7019 in a few).
- **Branch targets:** CM half → 0x7EA7D5xx helpers (11769 → state 6 via 0x7EA7DBDB `Cmp start terminate seqence`; 12069/12068 → 26798/26797 to +484; 13363–13365 → 0x7EA7D5B3/0x7EA7D571/0x7EA7D592 `event transfer %d`; 12962 → 0x7EA7D521). 12283/12282 → the request registry at +220 (getter 0x7EB87703; `syncUpdateScreen()` / `getSyncUpdateScreen()` per review F041). Play half → §3.2.

## 4. Statecharts below the class name

**Method (V):** `sc.py` reads the dispatcher at vtable slot 33 (vt+132). The dispatcher is either a compare chain or a jump table on `rootState_active`. For each state it parses the handler: every `mov ID,d0; mov (8,a1),a1; calls (a1)` starts a branch. The target state is the constant K that the entered function stores into two words. A handler without tests that calls several dispatchers is an AND-state (orthogonal regions). "·" below = no state entry found in the branch: an internal transition, or a target the tool could not resolve. State numbers are per class.

### 4.1 CM base chart (re-emitted in every component; +212) (V)

| State (entry) | Events → next | Entry action |
|---|---|---|
| 3 Idle (0x7EA7E266) | 11761 → 9 | — |
| 9 (0x7EA7E1F1) | 3346 → 8 | GEN 11761 evTraStart to CapBoo iface (+472) |
| 8 (0x7EA7E198) | 12063 → 7 | GEN 4761 boot request to +472 |
| 7 (0x7EA7E089) | 12067 or timeout −2 (+516) → 10; **3346 → 7** (re-enter, new 5 s timeout) | `startTransition... %d/%d`, timeout 5,000 ms |
| 10 (0x7EA7E244) | parent 0x7EA7E00F: 11562 → 4 Running, 11563 → 3 | GEN 11562 to self |
| 4 Running (0x7EA7E30F) | 11769 → 6; the CM half of §3.3 | — |
| 6 (0x7EA7DF61) | 12067 → 5; **3344 → 6** (count stop replies) | `stopTransition... %d/%d` |
| 5 (0x7EA7DF3F) | parent 0x7EA7DEFA: 11565 → 3 | `TerminateEnd`, GEN 11565 to self |

### 4.2 Play base chart (`Cmp_PlayComponentBase`, inherited by the 38 play classes) (V)

States 3–10 are the CM chart, except that 11562 enters **49 Idle** (0x7EB16AF0, `Cmp_Play%s Idle`). In Idle, a request 12281–12290 (built by `OlyHfwOpePlyComSync/AsyncRsb::execute`) is registered with its reply-to (ev+28), the command word of its payload (ev+32 → word) goes to **+572** and a kind to +568 (V for the 12290 branch; the other branches have the same shape, I). It then enters **15** (0x7EB15A20; entry calls vt+32 first). State 15 takes the null event −1 and the choice 0x7EB15A35 maps the command (+572) to a work state. Every work state returns to 49 on 12067 (`evTraCmp_NextState`).

| +572 command → state (entry, log string) |
|---|
| 1 → 39 `play_service_end` 0x7EB1669D · 2 → 31 `get_image_type` 0x7EB16263 · 3 → 23 `get_still_info` 0x7EB15FF7 · 4 → 29 `get_move_info` 0x7EB161EC · 5 → 27 `get_number` 0x7EB16175 · 6 → 33 `get_image_count` 0x7EB162DA · 7 → 35 `get_histogram` 0x7EB16351 |
| 298 → 43 `change_protect_start` 0x7EB16833 · 299 → 47 `can_protect_start` 0x7EB169D4 · 300 → 41 `change_Protect_Selected_start` 0x7EB16714 · 301 → **37 `erase_start`** 0x7EB163C8 · 302 → 17 `is_reserve_print` 0x7EB15C5A · 303 → 21 `is_protect` 0x7EB15EF4 · 304 → 19 `is_recording` 0x7EB15D84 · 305 → 14 `select_current_start` 0x7EB15921 · 306 → 25 `get_select_pic_number_start` 0x7EB1606E · 307 → 12 `transfer_image_start` 0x7EB155C7 · 387 → 45 `state_cancel_selected_all` 0x7EB1695D |

Notable handlers: **12** (transfer/media copy) takes 7609 → 49 with 12067 and logs `APP_MEDIA_COPY_MEDIA_ERROR[_FULL]`. **37** (erase) takes 7609 → self-GEN 7610, then 7610 → 12067 → 49 (the F045 handshake). 48 takes −1 → 49. Each work state's sub-state word is its own field (+876…+944).

### 4.3 LightBox (`CmpPLgh`, extra states over §4.2) (V entries, `ent.py`)

53 `playlightbox_update_image_sta` 0x7EB35F47, 55 `playlightbox_start` 0x7EB3604C, 61 `set_scroll_target` 0x7EB36717, 63 `set_base_start` 0x7EB36877, 67 `move_current_start` 0x7EB36CE9, 71 `get_number_start` 0x7EB36FA1, 75/77 `erase_current_st…` 0x7EB374AF/0x7EB377DF, 81 `can_move_current` 0x7EB37D60. The PLgh copy of erase state 37 is F045 0x7EB386CD: on 7609 it calls CapPls slots 113/135/148 (and 136/115/162 when +620 = 0), clamps a record u16 to 10, then self-posts 7610. On 7610 it ACKs (code 80) and posts 12067. The PLgh running handler is 0x7EB34D9B.

### 4.4 Shutdown (`CmpSdw_ShutdownComponent`, vt 0x7EC88588, dispatcher 0x7EB7853C jump table 0x7EC88558, +212) (V)

Relations (setters called from 0x7EB780F7): +352 CapThr facade, +344 CapPow, +348 CapTak, +336 CapMed, +332 CapIod, +324 CapBlc, +340 CapMod, +328 CapFls.

| State (entry) | Entry action | Events → next |
|---|---|---|
| 1 (0x7EB785F8) | GEN 11565 to self; then 0x7EB783AF (189 B: virtual calls on the relations +352, +344, +348, +336, +332, +324, +340; the counterpart of 0x7EB782C1, which the state-2 entry 0x7EB7864A calls; I: relation unsubscribe) | 11565 → 3 (inline in the dispatcher) (A8 2026-11-09) |
| 3 Idle (0x7EB78E44; the name "Idle" is I, by analogy with the CM chart: the entry logs only `*** on state %2d [%s] ***`) | — | 11761 → 8; 11769 and 11770 (0x7EBA6569) are taken without a state change (A8 2026-11-09) |
| 8 (0x7EB78A3D) | GEN 11769 evTraStop to +328 CapFls | **3344 → 11** (F047 0x7EB78A88 is the state-8 handler; review F047 said "case 12") |
| 11 (0x7EB78C84) | if CapIod (+332) vt+12 says active: GEN **5761** to it; else self 12067 | 12067 → 9 |
| 9 (0x7EB78AC9) | self 12067 | 12067 → 6 |
| 6 (0x7EB787ED) | GEN 11769 to +340 CapMod (`Mode My Shutdown`) | 3344 → 12 |
| 12 (0x7EB78D61) | GEN **3951** to +324 CapBlc; self 12067 | 12067 → 10 |
| 10 (0x7EB78C11) | GEN 11562 to self | parent 0x7EB786C5: 11562 → 4, 11563 → 3 |
| 4 (0x7EB78EEA) | — | 11769 → 1; CM-type ids 13363–13365, 11566, 11761, 12962 |
| 5 / 7 (0x7EB78723 / —) | 5: self 12067 | 5: 12067 → 10; 7: 3344 → 5 |

I: shutdown stops the strobe, powers down I/O (5761), stops the mode manager, then sends 3951 to blur correction (park the stabiliser?), and reports done with 11562.

### 4.5 PictBridge (`Cmp_PictBridgeComponent`, vt 0x7EC6A4F4) (V)

The outer states are the CM chart. **Running (4) = AND-state 0x7EAF1506 with three regions plus the running handler 0x7EAF1566:**
- **Main region +1296** (dispatcher 0x7EAF265D, jump table, states 11–168, 131 cases). **13 = `PictBridgeComponent:idle`** (entry 0x7EAFBBA4). Its handler 0x7EAFBF48 maps CustomPrint requests to work states: 13784→30, 13809→31, 13806→32, 13808→36, 13807→37, 13819→38, 13795→58, 13799→62, 13797→65, 13802→66, 13783→84, 13792→136, 13814→137, 13805→138, 13816→139, 13793→140, 13821→141, 13811→142, 13803→143, 13804→157, 13812→158, 13788→166. Play requests: 12261→14, 12264→15, 12267→16, 12262→17, 12274→19. Composite states keep their own sub-state words +1300…+1364. F042's "state 35 at +1300" is inside composite 34 (entry 0x7EAF2F90 GENs 7094 to self).
- **Region +1280** (0x7EAF1E59): 23 (entry 0x7EAF1E7F GENs **3615** to +1256 = CapPbr) ⇄ 24 on 7079/13791 (`CmpPictBridge Abort Success`).
- **Region +1288** (0x7EAF2092): 26/27 → 28 on −1; 28 = `backgroundctrl_idle start in Pictbridge`; 12281 internal.
- **Events:** 7071–7109 (`CmpPbr` package, 80 creators and 111 tests, all in CmpPbr) are its internal step events. 13781–13821 come from `OlyHfwOpeCustomPrint`. 3611–3623 are its requests to CapPbr (3613 is built only in CmpPbr; CapPbr tests it).

### 4.6 MfAssist (`CmpSts_MfAssist`, vt 0x7EC8AE40, dispatcher 0x7EB7E245, +172) (V)

3 Idle →(11761; builds 3346)→ **7 MfAssistOff** (entry 0x7EB7EA4C, `CmpSts_MfAssist::entryMfAssistOff()`). In 7: 11989 StartMfAssist → forward 11989 (wait); **7009 `evTraCom_OperationSuccess` → 6**; 7008 OperationError, 11988, 27494 → answers (26835). **6 = MfAssistOn** (I; entry 0x7EB7E73F schedules a timeout). Its handler 0x7EB7E77A takes the key notifications 16115–16123 (`evTraCmpSts_NotifyLeftKey`, `…NotifySubDial`, …; 16115 re-enters 6), 12014 / 12015 (scroll / zoom through → forwarded), and −2 (timeout → 26835). Parent 0x7EB7E4AE: 11769 → 3 (builds 3344). Slot 42 = F048 (§4.8).

### 4.7 Record (V)

- **`CmpSts_RecordController`** (vt 0x7EC4B1C4, dispatcher 0x7EA791E7, +172): 1 (`>>>>>end RecordController`) →11565→ 3 Idle →11761→ 2 (`<<<<start RecordController`, GEN 11562 to self) →11562→ 4 (11563 → 3). 4 = region +1140 (0x7EA7966C) + running handler 0x7EA7958D (11769 → 1, GEN 11565). In the region: 9 (recording) →16097 (record-media error; senders `RecordController::MEDIA_ERROR`, `EvRecRecordMediaError`)→ 10 `RecordController::recordingAbort` (0x7EA796E6). 16095 = record-media request (senders `recordMedia`, `recordMediaPictBkt`). The controller sends 5501/5502 to CapRec (`sendRecordMedia … evTraCapRec_RecordMediaPictBkt`; which id is which is not settled).
- **`CapRec_Record`** (vt 0x7EC3FB04, +212): 1 →11565→ 3 →11761→ 2 (GEN 11562) →11562→ 6 (11563 → 3, `CmpInitErr`). 6 takes 5501/5502/5521; 5 →5521→ 6. Parent 0x7EA4B30C = F036 (11769 → 1; 11566/11761 notify +148).

### 4.8 `Com_ManagersSubTransition` request list (+144) (V)

- The base init 0x7EB859ED calls vt+184, caches the EVFW router at +140, then calls **slot 42 (vt+168)**. The slot-42 override fills the array at +144 with prototype events. The base slot is the empty `retf` 0x7EB85924. Exception: `Com_ActiveTransitionManagerBufferd` has a stub slot 42 but fills +144 at run time from its state entries (table below). (A8 2026-11-09)
- **0x7EB857CA = "accepts this request?"**: it works only while the helper's state (+168) is 4. It loops over +144 and tests `ev->isTypeOf(proto->getId())`. Callers: CM 0x7EA7D0AE, `Cmp_ShootingComponentBase` 0x7EA7A1AA, still-shooting 0x7EA80393, Com_ 0x7EB87590, Cab 0x7EB896CA, Ctg 0x7EB9478B/0x7EB95E3B.
- So an owner routes an `evTraReq*` request to the sub-transition whose list holds that id. F049 0x7EB85867 clears the list.

| Subclass (ctor) | Slot 42 | Accepted ids |
|---|---|---|
| CmpSts_LiveViewZoomController 0x7EA70D5B | 0x7EA70FD9 | 12000 startZoomFrame, 12001 endZoomFrame, 12002 zoomThrough, 12003 scrollThrough, 12029 getMovableArea, 12030 `evTraReqShtSetThroughTypeZoom` |
| CmpSts_MultiExposureFunctionController 0x7EA72D1B | 0x7EA7375C | 12017 startMultiExposure, 12019 endMultiExposure, 12020 getMultiExposureCount |
| CmpSts_MfAssist 0x7EB7D14B | 0x7EB7D494 (F048) | 11989, 11988, 12014 `evTraReqShtMfScrollThrough`, 12015 `evTraReqShtMfZoomThrough` |
| CmpSts_MultiThrough 0x7EB7EC0B | 0x7EB7ED19 | 11980, 11979, 11978 (startMultiThrough), 12004, 12005 |
| CmpCst_Communication 0x7EA9D405 | 0x7EA9D87B | 13161, 13162, 13164–13168 |
| CmpCst_Function 0x7EA9F812 | 0x7EAA01DE (2,109 B) | 67 ids: 13481–13543, 12964/12965/12971/12972/12976/12982/12983, 7009, 12077, 11975 |
| CmpCst_MediaMount 0x7EAAA4AF | 0x7EAAA56F | 12981, 12980, 12970, 12967, 12977, 12978, 12984 |
| the other 7 (3D 0x7EA6D23C, EPortrait 0x7EA6EC03, RecView 0x7EA75054, Record 0x7EA7822A, Outline 0x7EA7E66B, the getName-less subclasses 0x7EA6CF32 / 0x7EA77CBA) | 0x7EB85924 (empty `retf`); Outline has its own `retf` stub 0x7EA7E6EB | none (A8 2026-11-09) |
| Com_ActiveTransitionManagerBufferd 0x7EB8AD37 (vt 0x7EC8C708) | stub `retf` 0x7EB8AE46 | **13361** while the helper is in state 4: the entries of states 7 (0x7EB8B66F, region +316) and 8 (0x7EB8B8EA, region +312) push the static prototype 0x605EF18C (a copy of 13361, built by 0x7EB85D2A from ctor 0x7E96C3D3) onto +144 through 0x7E966C01; the exit code 0x7EB8B458 removes it through 0x7E966CCE. Cab_CameraBase uses it: initRelations 0x7EB893EA sets Cab +276 = facade+128 (the Bufferd member built by 0x7EB8924F), and 0x7EB896CA calls 0x7EB857CA on (+276) (A8 2026-11-09) |

Request names come from the `OlyHfwOpeShoot::*` sender strings (I).

## 5. Dev part 1 devices (0x7EB8C265–0x7EB93422) (V calls/strings; class names I unless the string gives them)

| Range | Device | ctor / vtable | Accessor (RAM, size) and users | API wrappers / methods |
|---|---|---|---|---|
| 0x7EB8C265–0x7EB8C5E0 | info base | 0x7EB8C265 / 0x7EC8D7F8 | (base class) | getCurrentAspect 0x7EB8C283, getCurrentDisplaySize 0x7EB8C311, getCurrentOSDSize 0x7EB8C37D, getRealImageSizeAspect 0x7EB8C483; camera-info get 0x7EB8C277 (→0x7E67F822) / set 0x7EB8C5B5 (29 callers) |
| 0x7EB8C5E1–0x7EB8C8D1 | picture/display size | 0x7EB8C5E1 / 0x7EC8D998 | 0x7EB8EF0E (0x602B490C, 4 B; 28 callers) | LOWAPI `Disp_Get_Aspect_Size` ×2, getCurrentPictureSize 0x7EB8C781 |
| 0x7EB8C8D2–0x7EB8D849 + 0x7EB8F5D1–0x7EB8F81A | display device | base 0x7EB8C8D2 / 0x7EC8DEDC; derived 0x7EB8F7FF / 0x7EC8E57C | 0x7EB8F5D1 (420 B; CapDpc, CapTak, CapThr, CapBea, CapDbm, CapIod, CapMes, CapRev) | alloc*Handle 0x7EB8C9B6–0x7EB8CCAC, open/closeDevice 0x7EB8D143/0x7EB8CD01, image update/sync 0x7EB8CD7F–0x7EB8CF55, brightness 0x7EB8D304, colour temp 0x7EB8D39A, paint black (14c §2.5) |
| 0x7EB8D84A–0x7EB8E2B3 | handle holders | e.g. DisplayHandle 0x7EB8D8FE / 0x7EC8E030, play buffer 0x7EB8DD96 / 0x7EC8E074 | — | dtors call `api_play_Free_ImageHandle` / `Free_Playbuf`; stretchBlt 0x7EB8DC37, Play_Picture 0x7EB8DE98, Play_Rom 0x7EB8DF2B |
| 0x7EB8E2B4–0x7EB8EF0D | **DevAef_AEAFCtrl** | 0x7EB8EA40 / 0x7EC8E334 | 0x7EB8E2B4 (0x602B4908, 352 B; CapTak ctor only) | start/end/restartAFLock 0x7EB8E7E2/0x7EB8E4C3/0x7EB8EC9F (`api_rec_AEAF_Lock`), AF status 0x7EB8E465 |
| 0x7EB8EF48–0x7EB8F5D0 | **DevCls** (clear skin) | 0x7EB8F089 / 0x7EC8E518 | 0x7EB8EF48 (260 B) | execute/ready/recview 0x7EB8F136/0x7EB8F2B5/0x7EB8F384 |
| 0x7EB8F81B–0x7EB900EA | display effect | 0x7EB8F90C / 0x7EC8E800 | 0x7EB8F81B (176 B) | setBeauty, setCombineEffect, setIndexZoom, OverlapEffect, effect start/stop/end, multi-exposure effect (0x7EB8F9E1–0x7EB8FF5A) |
| 0x7EB900EB–0x7EB90182 | Exif | 0x7EB90125 / 0x7EC8E86C | 0x7EB900EB (4 B) | `api_play_Get_ExifTag_*`, `api_rec_Get_Record_ExifTag_Data` |
| 0x7EB90183–0x7EB90C17 | **DevLed** | 0x7EB907FA / 0x7EC8E918 | factory 0x7EB90183(type 0..33), 156 B each; 33 slots 0x602B4920–0x602B49A0 + one at 0x605EF2A8 | 13 `api_led_*` wrappers 0x7EB909FC–0x7EB90B6A; 6 observer lists |
| 0x7EB90C18–0x7EB926CF | **DevMed_MediaControl** | 0x7EB90C6D (base 0x7EB910CD / 0x7EC8EAA4) | per slot: 0x7EB90C18 (0..3 → 0x602B49A8–0x602B49B4, 900 B; CapMed controller 0x7EA113E6) | mount/format/erase-all/lock-all/copy-all/transfer 0x7EB91206–0x7EB92039; MountMediaObserver 0x7EB92356 |
| 0x7EB926D0–0x7EB92AA1 | MyMode/custom | 0x7EB92726 / 0x7EC8EE3C | 0x7EB926D0 (48 B) | start/set/end MyMode, loadCustom/Restore/Shortcut (`mcon_if_*`) |
| 0x7EB92AA2–0x7EB930DA | **DevRec** | 0x7EB92BE9 / 0x7EC8F080 | 0x7EB92AA2 (148 B; CapMed, CapRec) | Record_Media 0x7EB92CEB, Reserve_Media, Record_Picture_Bracket 0x7EB92F04, AbortAll 0x7EB92C1A; NotifyChangeObserver 0x7EB92B80 |
| 0x7EB930DB–0x7EB93422 | **DevSor** (sound rec.) | 0x7EB931D5 / 0x7EC8F118 | 0x7EB930DB (176 B) | start 0x7EB932EA, save 0x7EB93272, stop 0x7EB93362, getPastTime 0x7EB93249 |

Common part: most devices embed a 32-byte member (ctor 0x7EB9005F, vt 0x7EC8E840, base 0x7EB856BF; 6 ctor callers) and store the EVFW router (0x7E974D11) in their ctor. Their notifying wrappers end with notify-all 0x7EB86ED0 on a list.

## 6. Event-id owner fixes (`15c-event-id-fixes.tsv`)

- **Rule (counts V, choice I):** new owner = the class that tests the id most (the receiver = the Rhapsody package owner). If 5 or more classes test it, the shared base class is named (CM, Cmp_PlayComponentBase, Com_ bases). With no test site, the creator decides; with neither, the block majority.
- The 13c "next class / ctor package" heuristic disagrees with this rule for 1,242 of 1,268 ids. In most rows the owner is now a receiver instead of a sender or link neighbour.
- **Headline fixes:**
  - 7597–7611 → `Cmp_PlayComponentBase` (inherited, 38 classes);
  - 7601–7603 → CmpPMov;
  - 7591–7596 → Cmp_PictBridgeComponent / Cmp_PlayerComponentBase;
  - 3611–3623 → CapPbr (sent by CmpPbr);
  - 7071–7109 → Cmp_PictBridgeComponent (not CmpSht);
  - 5761 → CapIod;
  - 3951 → CapBlc;
  - 3341–3347, 12061–12080 → CM;
  - 11761–11843 → Com_ init-chart base;
  - 16061–16164 → CmpSts_SingleStillShootingSequence_NEW;
  - 26741–26861 → OlyHfwOpeShootRsbCommon (callback dispatcher 0x7E995C0B);
  - 4581–4602 → CapTak;
  - 5621–5653 → CapMed_MediaManager.

## 7. Corrections

1. **13c §3 / review I1:** the play chain is linear (§2): CM → Cmp_PlayComponentBase → **PlaySingle base 0x7EB54718 → Cmp_IndxBase 0x7EB2BB81 → PlayEdit base 0x7EB1DA86**. 0x7EB2BB81 is the index base, not a play-edit base. Shutdown derives from Com_ component-manager base 0x7EB87E25, not from CM.
2. **13c event TSV owners:** see §6. Block 7591–7611 is the play package, not CmpSht. 3613 is PictBridge → CapPbr.
3. **14c §2.4:** 11775 = `evHfwReqRegisterEvent` (register for one APP_EVENT / request handle).
4. **14c §2.2 step 6 (review I5):** CM state 7 also takes 3346 (re-enter 7 and restart the timeout). State 6 takes 3344 the same way.
5. **Review F047:** 0x7EB78A88 is the handler of Shutdown **state 8** (jump-table index 7), not case 12. It does enter state 11 on 3344.
6. **modules.tsv last_fn** (I2): use the class-index ranges (§1).
7. **13c §5 "CmpSqp_* vtables have a different layout":** the sequence parts are classes with getInstance + ctor (0x7EA86666 3D, 0x7EA87609 Base, 0x7EA99DB7 Eportrait, 0x7EA9A4E5 MultiExposure, 0x7EA9CA79 Otwb, 0x7EA9CE2F Panorama, 0x7EA9D108 PictBkt). They are plain C++ classes: the base ctor 0x7EA87609 stores vtable 0x7EC550D8 and calls no base ctor and no setActiveContext (V).

## 8. Open questions

1. Meaning of the APP_EVENT codes 0x02020002, 0x03010005, 0x04020011, 0x04020181 (who posts them for the play components; 0x04020011 is also used by RAW load, beauty and BT).
2. Names of the play requests 12281–12296 (built by a kind switch in the Rsb execute functions 0x7E97F8E0/0x7E980FC7), and of 7591–7596.
3. Which of 5501/5502 is `evTraCapRec_RecordMediaPictBkt`. What 3951 makes CapBlc do at shutdown.
4. 0x7EBA0AA9–0x7EBA0C6A (between the last Ctg class and the face device) has no API calls and no class; 13c §5.4 puts the face device there, but the face accessors start at the getInstance 0x7EBA0C6B.
5. The 104 small `setActiveContext(this) + (this+K)` wrappers give the embedding offset K of every facade. They are listed through the index, but K is not a column.
