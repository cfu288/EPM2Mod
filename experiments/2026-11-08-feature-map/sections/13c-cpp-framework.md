# 13c — C++ framework: Rhapsody OXF runtime, generated statechart code, events, Com_ layer

**Scope:** block 0, the C++ application layer ~~0x7E966000–0x7EBAC000~~ 0x7E966A17–0x7EBA7BC0 (HIGHLEVEL_MAIN to the end of OXF; §1 also covers the neighbours 0x7E965FD1–0x7E966A16 and 0x7EBA7BC1–0x7EBABF8D) (L1 2026-11-09). This section explains the *framework glue* that coverage round C1 found unexplained (12 of 20 sampled app-layer functions). Section 06 has the per-feature detail. The event dictionary is in `13c-event-ids.tsv` (1,270 rows).
**Labels:** **verified** = read in code or bytes; **inferred** = from strings, names, layout or a heuristic.
**Scratch:** `.../scratchpad/d1/cpp-framework/` (`fw.py` loader, `evscan.py` event-vtable scan, `classify.py` shape classifier, `classdir2.py` class directory, `mktsv.py` TSV builder).

## 1. Area and boundaries

| Range | Contents | Basis |
|---|---|---|
| 0x7E965FD1–0x7E966A16 | **Not app layer:** user-shell support code (fn 0x7E965FD1 spans 0x7E966000 and builds ANSI `ESC[` sequences; printf-like 0x7E966355; callers are shell commands from 0x7E9641FB on) (A5 2026-11-09) | verified call edges; role inferred (A5 2026-11-09) |
| 0x7E966A17–0x7E9698EB | HIGHLEVEL_MAIN code (from 0x7E966A17; entry 0x7E966A78), HLS OS wrapper, growable array, logger (section 06). The end is the last function before `clearIntervalShootingState` 0x7E9698EC (A5 2026-11-09) | verified (06); end moved from 0x7E96B000 by the `Tra*` string tags (A4 2026-11-09), then from ~0x7E96998A to 0x7E9698EB (A5 2026-11-09) |
| 0x7E9698EC–~0x7E9EA380 | `Tra*` event package (the `TraShareTakeStatus.cpp` tag is used by 0x7E969F7B, 0x7E96A14E, 0x7E96A422, 0x7E96A52A, 0x7E96AF2A and 0x7E96B048; first function of the package **0x7E9698EC `clearIntervalShootingState`**, which takes the TraShareTakeStatus lock 0x7E969EE6/0x7E969EF4 and clears bits in 0x602B0CDC; the RAM block 0x602B0CB4–0x602B0D18 is used only from here up (A5 2026-11-09)) + `OlyHfwOpe*`/`OlyHfwLowApiWrap` operation classes + event classes they declare; `sdk api` shell and `OlyApi*` (06 §5); the `app_check_*` group 0x7E9E8CCD–0x7E9EA380 | verified (string tags + event scan); both ends approximate (A4 2026-11-09) |
| ~0x7E9EA381–~~0x7EB80000~~ 0x7EB7FC90 (L1 2026-11-09) | `Cap*` capabilities, `CmpSts*`/`CmpSqp*` controllers, `Cmp*` components (one file per class, see §5). **Per-class ranges (D3 2026-11-09):** `15c-class-index.tsv` (start = min(getInstance, ctor)); boundary fixes from 15c §1: `Cmp_PlayComponentBase` 0x7EB0A5E7–0x7EB16FF3, CmpPEvV 0x7EB2887C–0x7EB2BB80, `Cmp_IndxBase` 0x7EB2BB81–0x7EB2ECCF, CmpPLgh 0x7EB33B24–0x7EB39215 (CmpPMov getInstance 0x7EB39216 follows), observers of other classes 0x7EB3D990–0x7EB3DEF6 (e.g. the 8 `Cmp_PlayComponentBase` member observers, ctors 0x7EB3DA46…0x7EB3DE8C ← 0x7EB0A5E7), and the event-method run 0x7EB79137–0x7EB7A6C7 between Shutdown and the shooting facade (D3 2026-11-09) | verified (class directory) (A4 2026-11-09) |
| 0x7EB7FC91–0x7EB84344 | `CmpSts_SingleStillShootingSequence_NEW` statechart (`rcv3dShootingFinishIn_END_WAIT` …). Its last function is 0x7EB83ECB (1,146 B, ends 0x7EB84344) (C2 2026-11-09) | verified (class directory, strings) |
| 0x7EB84345–~~0x7EB8C265~~ 0x7EB8C264 (L1 2026-11-09) | **Com_ framework** (from 0x7EB84345: the `Com_EvSenderManager` static module 0x7EB84345–~0x7EB85562, a 4,143-byte function called only by the `RECV APP_EVENT` handler 0x7E96DD58, its getters 0x7EB85374… and the overflow logger 0x7EB854E0 (`Com_EvSenderManager buffer overflow!`); globals 0x602B48A8–0x602B48E0) (A5 2026-11-09): Com_ reactive base, observers, request/response registry, CmpInit helpers, `Cab_CameraBase` mode machine, `Com_ActiveTransitionManagerBufferd`, events 7001–7020 and 11561–11566 | verified |
| 0x7EB8C265–0x7EB93422 (end verified: 0x7EB93417 ends at 0x7EB93422; 14c §1 (D2 2026-11-09)) | `Dev*` device classes, part 1 (14 device units with ctor, vtable, accessor and API wrappers: 15c §5 (D3 2026-11-09)) (the last `Dev*` string user is `DevSor::stop()` 0x7EB93362; the small helpers up to 0x7EB93422 are called only from Dev code) (C2 2026-11-09): display device (`api_disp_*`, `allocDisplayHandle`), `DevAef_AEAFCtrl`, `DevCls` (clear-skin rec view), effects, LED, `DevMed_MediaControl`, `DevRec` | verified (`api_*` callees, strings) |
| 0x7EB93423 (D2 2026-11-09)–0x7EBA0AA8 | Categories: first the function-mode category (getInstance 0x7EB93423, only caller `Cab_CameraBase::functionModeState` 0x7EB8AA26; ctor 0x7EB9345E; vtable 0x7EC8F144; sub-category 0x7EB937D3/0x7EB9380E/0x7EB938CB) (C2 2026-11-09), then the `Ctg_ComponentSwitcher` categories (5 vtables; ctors 0x7EB93A89, 0x7EB94576, 0x7EB96F97, 0x7EB9D909, 0x7EB9F1D1) | verified (class directory) |
| 0x7EBA0AA9–0x7EBA48BB | `Dev*` device classes, part 2: **face device** (0x7EBA0CA3 `api_rec_Get_Rec_Face_Number`, 0x7EBA0CCA `…Face_Rect_Area`, 0x7EBA0F8B `api_play_Get_FaceDirection`) (A5 2026-11-09), anti-shake, image handle, HDMI/CEC, histogram, Exif, picture files, `DevBlu_Bluetooth`, **USB-communication device**, DPS-T, DPS, pixel mapping, picture-file creation with its six helpers 0x7EBA4868–0x7EBA48BB (callers only 0x7EBA4603/0x7EBA464F/0x7EBA4759) (§5.4) (A5 2026-11-09) | verified |
| **0x7EBA48BC–0x7EBA7BC0** | **Rhapsody OXF runtime** (§2); it starts with the OMEvent ctor 0x7EBA48BC (A5 2026-11-09). Its last function is the 12-byte helper **0x7EBA7BB5–0x7EBA7BC0** (`add 16,a0`; zero the word at this+16 if it is non-zero; `retf`), called only by the class destructor 0x7EBA7B98 (own vtable 0x7EBCDB0C, then base destructor 0x7EBA7B13 with vtable 0x7EC922DC): it fills the clean-up step of the class-dtor shape in §3 (that role is inferred). The base/derived class pair (vtable slots point into 0x7EBA79D8–0x7EBA7B98) has no name string | verified (A4 2026-11-09) |
| 0x7EBA7BC1–0x7EBABF8D | **Not OXF: OKAO Smart Skin** (13b §2.2; data from ~0x7EBAC000). A string-less library called only from the FACE task code (0x7E6FB836, 0x7E6FB8BF, 0x7E6FBBCD, 0x7E6FBC17). It calls 0x7E72D0BA–0x7E72D95E (OKAO area) and the runtime helpers 0x7E4FE9D7 (sqrt), 0x7E500D33 (memcpy), 0x7E500D73 (memset) and soft-double 0x7E500F62–0x7E5019E4 (A5 2026-11-09). **0x0CA00080 is a handle magic, not an error code** (stored in word 0 by 0x7E72D932, checked by 0x7E72D94C, cleared by 0x7E72D95E; 13b §2.2); the return codes are small signed values (mapper 0x7EBA7BC1: 0, −1, −3, −4, 3, −8) (A5 2026-11-09). | verified call edges; "OKAO" by role (13b) (A4 2026-11-09) |
| 0x7EBAC000– | data | verified (no code xrefs) |

**Rodata (verified):** OXF vtables and the RCS markers `//! $Id$` are at 0x7EC919C0–0x7EC922A0. `$Id: ntos.cpp 1.83 2006/02/20 13:52:46 vova Exp $` is at 0x7EC91BBC; this is the Rhapsody OS-adapter file. Event vtables are in 0x7EBCxxxx–0x7EC92xxx (§4).

## 2. The OXF runtime (0x7EBA48BC–0x7EBA7BC0) (A4 2026-11-09) (A5 2026-11-09)

| Part | Addresses | Notes |
|---|---|---|
| OMEvent | vtable 0x7EC919D4; ctor **0x7EBA48BC**(a0=this, d0=id, a1=dest), 593 call sites; copy-ctor 0x7EBA48DB; dtor **0x7EBA490C** (1,282 call sites) | verified |
| Event-gen parameter temporary | ctor **0x7EBA4C8D** (2,823 sites; d0 = from-ISR flag), dtor **0x7EBA4C9E** (2,653), vtable 0x7EC91AB4 | verified shape; OXF name `OMOSEventGenerationParams` inferred |
| Timeout event (id −2) and timer heap | event vtable 0x7EC91B14, ctors 0x7EBA4D97(delay)/0x7EBA4DBC, due-time compare 0x7EBA4D7C; heap 0x7EBA4B0D/0x7EBA4BE8 ("Heap overflow" 0x7EBA4AA9); timer manager 0x7EBA4FF3–0x7EBA5634 | verified calls; roles inferred |
| Main thread singleton | 0x7EBA49CC(create) → 0x7EBA4A63 → ctor 0x7EBA49AE (vtable 0x7EC91A44); `mainThread` 0x7EBA49EA | verified (06) |
| ntos.cpp OS adapter | `BFA_*`, `BSE_*`, `BMQ_*`, `BTM_*`, `BEF_*`, `BTH_*`, `BMT_*` 0x7EBA56EC–0x7EBA6190; error hook 0x7EBA567D | verified (strings) |
| Memory | operator new 0x7EBA62DB (6,006 sites) / 0x7EBA62E3; delete 0x7EBA62EB (963) / 0x7EBA62F3; all go to 0x7EBA797A/0x7EBA7984 → 0x7E6810AE/0x7E6810F0 | verified |
| Mutex | 0x7EBA62FB–0x7EBA6363 (lock 0x7EBA6351, unlock 0x7EBA6363, used around takeEvent) | verified use; name inferred |
| **OMReactive** | ctor 0x7EBA6375, dtor 0x7EBA63DD; **base vtable 0x7EC91FE8, 35 slots**, methods 0x7EBA63D8–0x7EBA6E0E | verified |
| Framework events | ids −5 (0x7EBA6E24), −6 (0x7EBA6E50), −1 (0x7EBA6E7C), −9 (0x7EBA6EAD); vtables 0x7EC92080–0x7EC921A0 | verified ids |
| String class | ctor from `char*` 0x7EBA6F2B (uses strlen 0x7E500E01), copy 0x7EBA6EF3, dtor 0x7EBA6F94, init 0x7EBA6F79 | verified; `OMString` inferred |
| OMThread | base ctor 0x7EBA70E8, ctor 0x7EBA708D (callers 0x7E96CA56, 0x7E96DB78, 0x7E9E762F = three more active objects), vtable 0x7EC92210; event loop **0x7EBA74BB**; dispatch 0x7EBA73FF | verified |
| Start-up | 0x7EBA78B3 (from 0x7E966A17), `mainThread` entry 0x7EBA792C | verified |

**OMEvent layout (verified):** +0 vtable, +4 s16 id, +8 delete-after-consume flag (ctor sets 1; slot 1 0x7EBA492D deletes only when it is set), +12/+16/+20 user fields, +24 destination reactive. Event vtables have **18 slots**: 0 dtor, 1 Delete, 2 isTypeOf(id), 3 getId 0x7E966B30, 4 setId 0x7E966B37, 5–8 get/set +16/+20, 9/10 get/set destination, 11–16 empty stubs, 17 0x7EBA491D.

**OMReactive layout (verified fields, inferred names):** +4 status word: the low 16 bits are the null-config count (`pushNullConfig` 0x7EBA66B3 increments it, with an overflow message at 0xFFFF; `popNullConfig` 0x7EBA6695 decrements it, with an underflow message); bit 0x10000 = terminating. +24 embedded event id −5; +56 embedded event id −9; +96 timeout list; **+104 current event**; +108 event-guard mutex. Size 112 bytes.

**OMReactive vtable slots (verified unless marked):**

| Slot (+off) | Base | Role |
|---|---|---|
| 0 | 0x7EBA63D8 | dtor (generated classes override) |
| 1 (+4) | 0x7EBA66CF → 0x7EBA66D4 | **gen(ev, params)**; it calls send 0x7EBA6CE5, which sets the destination and queues the event on the thread (thread vtbl+8) |
| 6 (+24) | 0x7EBA65B1 → 0x7EBA65B6 | **takeEvent**, called by the thread loop. Under the mutex it calls slot 30 (slot 26 in mode 0x602B4A88). If the event is not consumed, it calls slot 27. It returns 3 when the reactive is terminating. |
| 9 (+36) | 0x7EBA67FF → 0x7EBA6804 | **startBehavior** (111 callers). It calls slot 32 rootState_entDef, then sends the embedded −5 event to itself. |
| 12 (+48) | 0x7EBA6B99 → 0x7EBA6B9E | **scheduleTimeout(delay, 0)**. It makes the −2 event and registers it with 0x7EBA5188; on failure it calls slot 29 ("Could not create timeout. It is lost"). |
| 13 (+52) | 0x7EBA6D5E | getActiveContext (the thread) |
| 15 (+60) | **0x7EBA6D64** | **getCurrentEvent** = `mov (104,a0),a0`. 12,693 direct call sites; generated base-class code also calls it as `mov (a0),a1; mov (60,a1),a1; calls (a1)` |
| 16, 19 | 0x7EBA6449, 0x7EBA6584 | gen variants (ISR flag / explicit params) |
| 17 (+68) | **0x7EBA653C** | For a non-NULL event: 0x7EBA4E2D (`setDestination(NULL)` through 0x7EBA499C, then +28 = 1), then 0x7EBA4DE4, which restores the timeout-event vtable 0x7EC91B14 (`mov 0x7EC91B14,d0`); the event is then freed through the returned pointer (`calls (a1)`) or by operator delete 0x7EBA62EB. 276 aligned words in block 0 point to it, all in vtables of the rodata pages 0x7EBDxxxx…0x7EC9xxxx (16a counts 238 in its own vtables); every reactive class inherits it (V calls). Role: Rhapsody `cancelTimeout` (I) (D4 2026-11-09) |
| 21 (+84) | 0x7EBA6759 → 0x7EBA675E | setActiveContext; **0x7EBA675E is called by every reactive ctor (356 callers)** |
| 27 (+108) | 0x7EBA68B6 | handle-event-not-consumed (inferred from takeEvent) |
| 30 (+120) | 0x7EBA69A4 | consume. It runs the null-transition loop 0x7EBA6B03 ("Infinite Loop of null transitions"), skips id −5, then calls **slot 33** (or slot 31 for a triggered operation). |
| 32 (+128) | 0x7EBA6A8B | **rootState_entDef**: overridden by every generated class |
| 33 (+132) | 0x7EBA6AA8 | **rootState_dispatchEvent**: overridden by every generated class |
| 35–37 | (Com_ only) | added by the Com_ base: 35 = **`dumpState(level)`** 0x7EB87078 (`%s, [%s]` / `%s, state=%d`; CM overrides it with 0x7EA7CB15, which reuses the body at 0x7EB8707D and sends event 14381 to every sub-component and capability), **36 (+144) = getName()**, 37 (+148) = delegate reactive (used by Com_ takeEvent) (C5 2026-11-09) |

**Global 0x602B4A88 (verified use):** when it is non-zero, gen, takeEvent and the thread use alternative slots (26 instead of 30, 23 instead of 6). **Inferred:** this is Rhapsody's animation/instrumented mode; it is normally 0.

## 3. Generated statechart code: how to classify a function by its shape

**Class hierarchy (verified call chain of ctors):** OMReactive 0x7EBA6375 → **Com_ reactive base** 0x7EB8701F (vtable 0x7EC8BD40; +112 name string, +124 trace level, +128 = −1) → 0x7EB88CED → 0x7EB87AC9 → **Cap init base** 0x7E9EF709 (vtable 0x7EC20390; 34 Cap* ctors call it). Components use `Cmp_ComponentManagerWithBoot` 0x7EA7C89C → `Cmp_PlayComponentBase` 0x7EB0A5E7 (10 subclasses) / ~~play-edit bases 0x7EB2BB81 → 0x7EB1DA86 (16) / play-single base 0x7EB54718 (7)~~ **one chain, not siblings (C3 2026-11-09):** 0x7EB0A5E7 → play-single base 0x7EB54718 (7 ctor callers) → **`Cmp_IndxBase` 0x7EB2BB81** (strings `Cmp_IndxBase idx_get_page_info`; 4 ctor callers: the play-edit base 0x7EB1DA86 and 0x7EB01903 / 0x7EB172B0 / 0x7EB2EFD4, which sit in CmpPCal / CmpPct / CmpPli (I by position)) → play-edit base 0x7EB1DA86 (16) (each ctor calls the previous one, V) (C3 2026-11-09). **Members of each level (D3 2026-11-09, 15c §2, V ctor edges):** `Cmp_PlayComponentBase` 0x7EB0A5E7 → PCom 0x7EAAB4B8, Bgc 0x7EAAE3C3, CCom 0x7EAB160C, PCol 0x7EB055F9, PCw 0x7EB1A7E6, PEvV 0x7EB28B48, PPnr 0x7EB3E58B, PPho 0x7EB4264A, PSou 0x7EB6C601 and the play-single base; `Cmp_PlaySingleComponentBase` 0x7EB54718 → PEvc, PLgh, PMov, PRec, Pls, PSld and `Cmp_IndxBase`; `Cmp_IndxBase` 0x7EB2BB81 → PCal, Pct, Pli and the play-edit base; `Cmp_PlayEditComponentBase` 0x7EB1DA86 → CPic, the 12 `CmpE*`, Era, PSel, RPri, SOve (16). **Shutdown is not a CM subclass:** `CmpSdw_ShutdownComponent` 0x7EB781D4 and CM 0x7EA7C89C both call the **Com_ component-manager base 0x7EB87E25** (its only two callers) (D3 2026-11-09). ~~CmpSts controllers use~~ `Com_ManagersSubTransition` 0x7EB8573D has 15 ctor callers, 8 of them CmpSts controllers; the others include the CmpCst_* components, Cmp_OutlineController and Com_ActiveTransitionManagerBufferd. So it is a general sub-transition helper; its observer classes 0x7EB85DC3/0x7EB86084 make events 3346/3344 (updates 0x7EB85DDF/0x7EB860A0 call the event ctors 0x7E9EB1AF/0x7E9EB15F) (14c §4 item 6) (D2 2026-11-09).

**Per-class vtable overrides (verified on 7 classes):** slot 0 dtor, 9 startBehavior wrapper, **32 rootState_entDef, 33 rootState_dispatchEvent, 36 getName**; components also override 3, 35 and 37.

**State-variable layout (verified on 8 classes):** each generated class stores `int` state words after its base data. Entering a state writes the same state constant to two words: the parent's `_subState` and the enclosing region's `_active` word. That is **`rootState_active`**, except inside an orthogonal region, which has its own pair (e.g. CmpCst_Function's OSD sub-machine +880/+876, F050). `rootState_active` is **+212** in Cmp components and Cap classes, +172 in CmpSts controllers (+168 subState) and +172 in CmpCst_Communication (+404 subState). For components, +208 is `rootState_subState`. State constants are per class (e.g. Idle = 49 in Cmp_PlayEditComponentBase, osd_idle = 8 in CmpCst_Function). A timeout handle is a word next to them (e.g. +216).

**Why the same code appears in many files (inferred, strong):** Rhapsody **statechart inheritance**. A derived class's chart includes the base chart's states, and the generator re-emits their code in every derived class. Examples: the "go to Idle on 12067" handler exists 73 times (F053 0x7EB1FBE1 in the base calls getCurrentEvent through the vtable; the copies F054 0x7EB366D0 and F057 0x7EB6B6C1 call 0x7EBA6D64 directly and differ only in offsets and call displacements). The Cap init states (§4.3) are re-emitted in each Cap class. This replaces section 06's "inlined from a header or macro".

**Shape catalogue.** Counts are from `classify.py` over the 32,799 functions in the scan window 0x7E966000–0x7EBA4868 (a count window, not a module edge; app code starts at 0x7E966A17) (heuristic, verified per sample). 72% fall in a pattern class; the remaining 28% is real feature logic.

| Shape (count) | Signature (instructions; bytes where fixed) | Role |
|---|---|---|
| Event ctor (1,029) | `clr d0; mov 0,a1; call BASE; mov VT,d0; mov d0,(a0); mov ID,d0; movhu d0,(4,a0); ret` — bytes `fc cc <VT32> 60 2c <ID16> f8 70 04` | §4 |
| Event isTypeOf (1,199) | `exth d0; cmp ID,d0/d1 (fa c8/c9 <ID16>); …; [call parent isTypeOf]; retf/ret` | hand-made RTTI |
| Event dtor (1,262) | `f8 fe fc dd <rel32> 00 04 90 00 df 00 04` = `call 0x7EBA490C; mov 0,a0; ret` | |
| **State entry** (2,879; 675 are exactly 20 bytes; the 16a index, window 0x7E966A17–0x7EBA7BC0, finds 2,407 functions with this two-word shape in the first 7 insns (D4 2026-11-09)) | `mov K,d0; mov d0,(SUB,a0); mov d0,(ACTIVE,a0); call <entry action / 0x7EB87341 trace / sub-entDef>; ret` — bytes `80 KK fa 10 SS SS fa 10 AA AA` (`2c KK KK` when K > 127) | `<state>_entDef`/`_enter` |
| Composite state entry (1,151 in the 16a index) | `mov K,d0; mov d0,(N,a0)` with N a state word (one store only), then a call, usually the entry of the default sub-state (e.g. 0x7E9D86B2: `mov 2,d0; mov d0,(160,a0); call 0x7E9D9255`) | `state K entry (composite)` (D4 2026-11-09) |
| State exit (1,088 in the 16a index, plus 90 exits that first exit the active sub-state) | `clr d0; mov d0,(N,a0); retf` with N a sub-state word (e.g. 0x7E9D899D, N = 180) | state exit: clears the sub-state word (D4 2026-11-09) |
| Transition step (87) / bool condition in a handler branch (12) | ≤48 B that calls one exit and one entry / a compare-and-return-0/1 called from an isTypeOf branch | exit + enter; guard (D4 2026-11-09) |
| **Single-trigger handler** (910 functions in one 63-byte shape; 2,664 call getCurrentEvent + isTypeOf) | `mov a0,a2; clr d2; call 0x7EBA6D64; cmp 0,a0; beq; … mov ID,d0; mov (8,a1),a1; calls (a1); cmp d2,d0; beq; call <exit>; call <enter>; mov 1,d2; …; [else call <parent handler>]; mov d2,d0; ret` — bytes `92 08 dd <rel32> 00 00 b0 00 c8 25 98 dd <rel32> 00 00 f0 04 2c <ID16> f8 25 08 f0 f1 a8 c8 10` (`call` = `dd rel32 regs imm8`) | `<state>_handleEvent` / `rcv<Ev>In_<state>`: returns 1 = consumed, 0 = not consumed |
| Dispatcher (395) | `mov (ACTIVE,a0),d1; clr d0; cmp k,d1; beq …` chain, or a jump table (CapBlu 0x7EC41158); calls one handler per state | `rootState_dispatchEvent` (slot 33) / `<state>_dispatchEvent` |
| initStatechart (105) | `clr d0` then only `mov d0,(N,a0)` stores, `retf`; only caller is the ctor (e.g. F055 0x7EB3E6AF) | zero all state words |
| Reactive ctor (137) | call base ctor; `mov VT,d0; mov d0,(a2)`; **`call 0x7EBA675E`**; clear fields; call initStatechart | |
| Null transition (211) / transient entry (152) | **calls 0x7EBA6695** (popNullConfig), then enters the next state (often a switch on a sub-state, e.g. F051 0x7EAD203B); a transient state's entry calls **0x7EBA66B3** (pushNullConfig) | completion transitions |
| Timeout | schedule: `mov DELAY,d0; mov 0,a1; mov (a0),a2; mov (48,a2),a2; calls (a2); mov a0,(TM,a3)`; handler: isTypeOf(−2) and `getCurrentEvent() == (TM,a2)` (e.g. 0x7E977BFE / 0x7E977C38) | `tm(delay)` |
| GEN / send (1,568) | `mov SIZE,d0; call 0x7EBA62DB; …; call EVCTOR; …; mov 0,d0; call 0x7EBA4C8D; target->vtbl[+4](ev,params)` **or** `call 0x7EB871B1` (to self); `call 0x7EBA4C9E` | Rhapsody `GEN()` |
| Observer callback (149 in one 75-byte shape) | `movm; mov a0,a3; add 20,a3; mov (a3),d0; cmp 0,d0; beq; new; EVCTOR; GEN to (a3)` (F047 0x7EA6CEE7) | turns a notification into an event for the target at +20 |
| Notify / add observer (146 / 198) | call 0x7EB86ED0 / 0x7EB86DF0 | §6 |
| Class dtor (601) | set own VT; call cleanUpRelations; member dtors (observers: 0x7EB85D75); base dtor; `mov 0,a0; ret` (e.g. F046 0x7EA6A4B6) | |
| getName (75 in one 54-byte shape) | `movm [a2]; add -28,sp; … mov NAME,a1; call 0x7EBA6F2B; call 0x7EBA6EF3; …; call 0x7EBA6F94` | slot 36; gives the class name (§5) |
| Forwarder (5,336) / call chain (264) | only `mov a?,a?` and 1 (or more) `call`, then `ret` | entDef → enter chains, sub-state entry |
| Virtual prologue (1,652) | only `movm [regs],(sp); add -N,sp` (or only `add -N,sp`) | the vtable entry of the **next** function; its body is also called directly with `call body,[regs],N` (e.g. 0x7EBA65B1 → 0x7EBA65B6) |
| Getters/setters (~3,000) | `mov (N,a0),d0/a0; retf` / `mov d0,(N,a0); retf` | attributes (e.g. 0x7EB87703 = `(220,a0)`, 1,070 callers) |

**Decision order for an unknown function:**
1. Does it call 0x7EBA48BC or write `movhu d0,(4,a0)` after a vtable store? Then it is an event ctor; look the id up in the TSV.
2. Does it call 0x7EBA6695 or 0x7EBA66B3? Then it is a null-transition step.
3. Does it call 0x7EBA6D64 (or vtbl+60) and then isTypeOf (`(8,a1)`)? Then it is a state handler for those ids.
4. Does it start by loading one large `(N,a0)` word and compare it with small constants? Then it is a dispatcher.
5. Does it store one constant into two `(N,a0)` words? Then it is a state entry; the larger common offset is `rootState_active`.
6. Does it call 0x7EBA4C8D? Then it sends an event. Does it call 0x7EB86ED0? Then it notifies observers.
7. Otherwise, find its class with §5 and the section-06 feature tables.

## 4. Event classes and the event-id dictionary

**Counts (verified, `evscan.py`):**
- There are **1,273 event vtables** (slot 3 = 0x7E966B30 and slot 4 = 0x7E966B37).
- 1,023 have a constructor that loads the vtable; the other **250 are vtable-only** (declared, never constructed).
- The vtables have 1,268 distinct ids. Ids 24411 and 24412 each have two classes, both in CapBlu.
- **6,245 isTypeOf test sites** cover 1,111 ids.
- **Tool caveat, DB split (C3 2026-11-09):** when an event's `isTypeOf` directly follows its ctor, it has no direct caller and no prologue, so `fwmap.py` does not start a function there and the DB merges it into the ctor (e.g. ctor 0x7EA465CD, id 27207: DB size 40 runs through `isTypeOf` 0x7EA465E7 and its `retf`; the ctor itself is 26 B). This holds for **55** of the 1,022 TSV rows with both addresses (isTypeOf not a DB start and inside the ctor's DB function). 13c-event-ids.tsv lists these isTypeOf addresses correctly; DB sizes and callee lists of those ctors are not (C3 2026-11-09).
- **TSV caveat, "next class" owners (C3 2026-11-09):** the owner of block **7591–7611** is not CmpSht_ShootingComponent_NEW. These are the `evTraCmpPly_*` play-component notifications (`Cmp_PlaySingleComponentBase rcv [evTraCmpPly_NotifySelectDisplayExecuteEnd]` 0x7EB109D3 handles 7604): their ctors 0x7EB79D60–0x7EB79F94 are called by observer updates 0x7EB3D9FB–0x7EB3DEAC whose ctors (0x7EB3DA46…0x7EB3DE8C) are called only by the `Cmp_PlayComponentBase` ctor 0x7EB0A5E7. Event 3613 (owner "Com_ManagersSubTransition") is created only in Cmp_PictBridgeComponent (ctor 0x7EA69837 ← 0x7EAF2FE7, 0x7EAF51C3, 0x7EAF69EB, 0x7EAFBCD4, 0x7EAFBF48); the rest of block 3611–3623 is not checked (C3 2026-11-09).

**Where they are (verified):**
- Vtables: 0x7EBC–0x7EBF 575; 0x7EC1–0x7EC4 561; 0x7EC8 129; 0x7EC9 8 (OXF).
- Ctor functions (counts per window; the windows are the older, page-rounded bounds (L1 2026-11-09)): 0x7E96B000–0x7E9823AB 373; 0x7E9823AB–0x7E9EA000 62; Cap/Cmp 0x7E9EA000–0x7EB80000 559; Com_/Dev 21; OXF 4.
- Each package's events are emitted as one run just **before** that package's classes. The large runs are 0x7E96B13C–~~0x7E96C670~~ 0x7E96C66F (Tra; 0x7E96C670 is the vtable store of the HLS root +0 object, 15c-class-index (L1 2026-11-09)), 0x7E96FA94–0x7E97232D, 0x7E972D4A–0x7E974614, 0x7E9EA6DA–0x7E9EB24E, 0x7EA1722E–0x7EA1831E, 0x7EA69022–0x7EA6A299, 0x7EA84211–0x7EA86666, 0x7EB79137–0x7EB7A6C8 and 0x7EB8BCCB–0x7EB8C265.

**Id allocation (verified pattern, inferred cause):** positive ids come in **84 contiguous blocks, and every block starts at a number ending in 1** (2201, 3141, 7001, 11561, 11761, 12061, 26741…). Each block is one Rhapsody package. So the block tells you the package even when there is no name.

**Intermediate base events (verified ctors):**

| Base id (ctor) | Children | Meaning (inferred) |
|---|---|---|
| 13361 (0x7E96C3D3, 201 derived ctors) | 246 | Request from an Ope/API class to a component. The base stores a **reply-to object at +28** (verified). Examples: 12047 (sent by `OlyHfwOpeShoot::startIntervalShooting`) and 11964 (`startHistogram`); family `evTraReqSht*`. |
| 26741 (0x7E972D4A) | 113 (26742–26861) | `evTraResSht*`: shooting results/callbacks to the API side (e.g. 26759 evTraResShtEndShooting, sent by `RecordController::sendCallBack_CBS_END_RECORD`) |
| 5621 (0x7EA17DE1), 13881 (0x7E991810), 13581 (0x7E978AA8), 12861 (0x7E975F8B), 13605, 13261 | 32 / 24 / 21 / 17 / 9 / 6 | CapThr, `evTraResPrt*` (EasyPrint), OpeLevel, LowApiWrap, … |

**Key ids:**

| Id | Name / meaning | Basis |
|---|---|---|
| −1 / −2 / −5 / −6 / −9 | OXF null / timeout / start-behavior / end-thread / destroy | §2; −1, −2, −6 verified, −5 and −9 inferred |
| **12067** | `evTraCmp_NextState`: generic "step done, go on". 858 creating functions (ComponentManager `startTransition… %d/%d`, every play component), 1,174 tests | creation and test counts verified; name inferred (string in creator 0x7EAC9680) |
| 11761 / 11769 | `evTraStart` / `evTraStop` for capabilities and controllers (240 / 242 tests) | inferred (strings, creators `initialize3dController` / `requestStop`) |
| 11565 / 11562 / 11563 | init request / **init OK** / **init error** ("CmpInitErr") | code shape verified (§4.3); names inferred |
| 11772 | built by 0x7EB86C21 and sent to `requester->vtbl[1]`. Two callers: register+ack 0x7EB868BC, and lookup-and-ack 0x7EB868A6, which only looks up an existing entry (0x7EB867EB) with no registration; a third sender is 0x7E96E40A (vtable word 0x7EBD1384). So it is a general acknowledge-to-requester event, not registration-only (A5 2026-11-09) | verified call; "ack" inferred |
| 11776 / 11777, 11779 / 11780 | EVFW subscribe (code / range) and **unsubscribe**. The EVFW router 0x7E999883 sends 11776/11777 to 0x7E999CA4 (find or create a topic, add the observer) and 11779/11780 to 0x7E999EC6 (remove the observer; drop the topic when it is empty). 11779 is not a send of codes (review F036) (14c §2.4) (D2 2026-11-09) | verified (code) |
| 7009 / 7008 | `evTraCom_OperationSuccess` / `evTraCom_OperationError` | inferred (0x7EA4E032) |
| 26742–26861 | `evTraResSht*` (43 of them named in the TSV) | inferred |

**4.3 The Cap init states (verified shape, 0x7E9ECE18 and copies):** `rootState_dispatchEvent` on +212 has four states. State 1 waits for 11565. State 2 waits for 11562 (notify the +148 observers, go on) or 11563 (log `CmpInitErr`, notify +168). States 3 and 4 handle 11761/11769. This is the base chart that every Cap class inherits; 73 copies create 11562/11565. F058 (0x7EB87C55) is the Com_ copy.

**The TSV (`13c-event-ids.tsv`):**
- Columns: id, vtable, ctor, isTypeOf, parent_id, owner, id_block, n_create_fns, n_test_sites, name, name_source, sender_example, handler_example.
- **Verified columns:** id through n_test_sites. Owner = the package of the ctor (the next class in link order, or the Ope tag before it); it is heuristic. **Use `15c-event-id-fixes.tsv` for owners (D3 2026-11-09):** it re-assigns 1,242 of the 1,268 ids by the receiver rule (owner = the class that tests the id most; a shared base when 5 or more classes test it; else the creator; else the block majority; counts V, choice I; 15c §6). Caveats: the rule names the receiver, so for request/notify ids the sender is in the `sender_example` column, not in the owner; inherited bases (CM, `Cmp_PlayComponentBase`, Com_ bases) stand for every subclass. Headline fixes: 7591–7596 → Cmp_PictBridgeComponent / Cmp_PlayerComponentBase, 7597–7611 → `Cmp_PlayComponentBase` (7601–7603 → CmpPMov), 7071–7109 → Cmp_PictBridgeComponent, 3611–3623 → CapPbr (sent by CmpPbr), 5761 → CapIod, 3951 → CapBlc, 3341–3347 and 12061–12080 → CM (D3 2026-11-09).
- **Names:** 77 rows have a name, 158 have a name, a sender or a handler, and every row has its block. A name comes from an `ev*` string in a function that creates or tests **only** that id, or from the curated list above. Treat single-string names as inferred, because a log line can name another event (e.g. 7011 → `evTraCapRev_Stop` looks doubtful).

## 5. Class directory and the classes the map lacked

**Method (verified):**
- Every Com_-derived class has `getName()` at vtable slot 36. 138 vtables point to such a getter; each getter loads one name string (75 of them have the identical 54-byte shape).
- vtable = (address of the word that holds getName) − 144. The ctor is the function that stores that vtable and calls 0x7EBA675E.
- A file starts with `getInstance()`, a 58–59-byte singleton accessor: `if (!g) { p = new(N); ctor; g = p; register } return g`. Then come the factory, the ctor, the dtor and the methods.
- Classes that do not override getName print the base name (`unknown`, `Cmp_ComponentManagerWithBoot`, `hogehgoe`).

**Named reactive classes (ctor / vtable)** (all verified; 0x prefixes omitted):

| | | |
|---|---|---|
| CapBuf_BufferManager 7E9EB723 / 7EC1FE28, 7E9ED562 | CapDpc_DisplayControl 7E9EE73E | CapDpv_DisplayView 7EA0E3CC |
| CapMed_MediaManager 7EA12D44 | CapThr_ThroughImage 7EA1831E | CapPCM_PlayContinuousManager 7EA20D19 |
| **CapPDB_PlayOLDB 7EA2384A / 7EC34BFC** | **CapPls_PlayState 7EA27FF2 / 7EC373AC** | **CapCam_CameraInformation 7EA2F416 / 7EC3750C** |
| CapTak_Take 7EA331E5 | CapBea_BeautyEdit 7EA393C3 | CapBlc_BlurringCorrection 7EA3B838 |
| CapBoo_BootManager 7EA3C34A | CapCDH_ContinuousDisplayHandle 7EA3CD32 | CapDbm_DispBankManager 7EA3D339 |
| CapFls_Flash 7EA3E057 | CapHis_Histogram 7EA3F95D | CapIod_IODevice 7EA40A09 |
| CapMod_ModeInformation 7EA42172, 7EA42832 | CapMov_MovieRecorderSLR 7EA42F9B | CapMes_MultiExposureScale 7EA44FDA |
| CapRev_RecView 7EA46704, 7EA4A5B1 | CapPow_Power 7EA4980B | CapRec_Record 7EA4ADDC |
| CapT3d_Take3d 7EA4CFB0 | **CapUsr_UserControl 7EA4E4A3 / 7EC40950** | **CapBlu_Bluetooth 7EA4F02C / 7EC4118C** |
| **CapCom_Communication 7EA51DDA / 7EC4151C** | CapFrp_FramePlayer 7EA52F9D | CapGSld_GpuSlideShow 7EA5553D |
| CapOef_EffectManager 7EA57393 | **CapPbr_PictBridgeCommunicate 7EA58D18 / 7EC44074** | CapPic_PictureInfoManager 7EA5FFC8 |
| CapPxm_PixelMapping 7EA60CBF | CapPla_PlayFrameInfo 7EA62685 | CmpSts_3dImageController 7EA6D23C |
| CmpSts_EPortraitShootingEditer 7EA6EC03 | CmpSts_LiveViewZoomController 7EA70D5B | CmpSts_MultiExposureFunctionController 7EA72D1B |
| CmpSts_RecViewController 7EA75054 | CmpSts_RecordController 7EA7822A | Cmp_ComponentManagerWithBoot 7EA7C89C |
| Cmp_OutlineController 7EA7E66B, 7EA7F084 | CmpCst_Communication 7EA9D405 | CmpCst_Function 7EA9F812 |
| CmpCst_MediaMount 7EAAA4AF | CmpEAsp 7EAB8A62, CmpEBea 7EABC94E, CmpEImg 7EAC6C7B | **CmpFnc_FunctionComponent 7EAECA0E / 7EC68F90** |
| **Cmp_PictBridgeComponent 7EAF006B / 7EC6A4F4** | CmpPCal 7EB01903, CmpPct 7EB172B0, CmpPEvc 7EB20617 | CmpPli 7EB2EFD4, CmpPLgh 7EB33E28, CmpPPho 7EB4264A |
| CmpPRec 7EB4BC94, CmpPSel 7EB4FA4E, CmpPls 7EB59169 | Cmp_PlayerComponentBase 7EB6EDA3 | CmpSOve 7EB74828, CmpSdw_ShutdownComponent 7EB781D4 |
| CmpSts_MfAssist 7EB7D14B, CmpSts_MultiThrough 7EB7EC0B | CmpSts_SingleStillShootingSequence_NEW 7EB7FC91 | **Cab_CameraBase 7EB89520 / 7EC8C470**; Com_ActiveTransitionManagerBufferd 7EB8AD37 |

The CmpSqp_* sequence parts (`Base`, `Eportrait`, `MultiExposure`, `Otwb`, `Panorama`, `PictBkt`) and `CmpSht_ShootingComponent_NEW` have getName (0x7EA91BCE, 0x7EA9A148, 0x7EA9B0AE, 0x7EA9CC7B, 0x7EA9CF29, 0x7EA9D17F, 0x7EB7AB2C), but their vtables have a different layout (not resolved). **Resolved (D3 2026-11-09, 15c §7 item 7, V):** they are plain C++ classes, not reactive ones: the base ctor 0x7EA87609 stores vtable 0x7EC550D8 and calls neither a base ctor nor setActiveContext 0x7EBA675E; the part ctors 0x7EA86666 (3D), 0x7EA99DB7 (Eportrait), 0x7EA9A4E5 (MultiExposure), 0x7EA9CA79 (Otwb), 0x7EA9CE2F (Panorama) and 0x7EA9D108 (PictBkt) each call only 0x7EA87609, and 0x7EA8A09E (allocate + base ctor) is the Base's getInstance (D3 2026-11-09).

**5.1 CapPls_PlayState (verified bounds)** — file **0x7EA27EBF–0x7EA2F2CE**:
- getInstance 0x7EA27EBF (callers include 0x7E9EFC03 and 0x7EA23F30), factory 0x7EA27EF9, ctor 0x7EA27FF2, dtor 0x7EA28050, dispatch 0x7EA2EFED, getName 0x7EA2D276.
- **Role (inferred, strings):** the playback-state capability. It holds the calendar cursor (`CapPls::cal_move_cursor_direct`), event/collection/slide-show info setters (`[chls]app_play_set_*`), play info and relevant-picture moves (`[chls]app_playinfo_control_move_relevant`, 0x7EA29ACA), image-overlay picture select, index area, DB open/close errors, and the volume (`PlayState setVolume`).
- Before it: an unnamed helper class (ctor 0x7EA27711, vtable 0x7EC34EA4, 0x7EA275F3–0x7EA27EBE). After it: **CapCam_CameraInformation** ~~0x7EA2F2CF–~0x7EA30749~~ 0x7EA2F2CF–0x7EA2F9E3, then the **CapPls_PlayState interface** 0x7EA2F9E4–0x7EA3074F (ctor 0x7EA2F9E4, only caller the CapPls facade ctor 0x7EA27EF9, stores vtable 0x7EC3760C, 215 slots, 214 of them at 0x7EA2F9F2–0x7EA30731) (D4 2026-11-09). ~~F044 (0x7EA2B2B9, a CapPls method) is called from 0x7EA2FC7E, which is in CapCam (verified call).~~ F044 (0x7EA2B2B9, a CapPls method) has one caller, **0x7EA3021B** (site 0x7EA30221), the interface thunk in slot 134 of 0x7EC3760C; 0x7EA2FC7E is the slot-47 thunk (→ 0x7EA29226). Both are CapPls interface code, not CapCam (D4 2026-11-09). Per F044, the call refreshes the picture count and play state (inferred).

**5.2 CapBlu_Bluetooth (verified bounds)** — events 0x7EA4E847–0x7EA4ECD1, class **0x7EA4ECD2–0x7EA51800**:
- getInstance 0x7EA4ECD2 makes a 1,208-byte singleton at RAM 0x602B3210; its only caller is in CmpCst_Function 0x7EA9FE00.
- ctor 0x7EA4F02C (it also builds DevBlu through 0x7EBA290C), initStatechart 0x7EA4FD33, dispatch 0x7EA4FE28 → 0x7EA500FC (F045; sub-state +808 jump table 0x7EC41158), getName 0x7EA4FAF3.
- **Role (inferred):** the statechart over `DevBlu_Bluetooth` (search, pairing, send/receive image). It drives DevBlu through virtual calls, so it has only 4 strings. Event blocks 4611–4613, 5001–5023, 5501–5522, 5561, 24411–24416 and 25991 (ctors 0x7EA4E847–0x7EA4EC6F) probably belong to it (inferred: a package's events come just before its classes).
- Before it: **CapUsr_UserControl** 0x7EA4E3A3–~0x7EA4E846 (getInstance called by StillShootingComponentBase 0x7EA81975). After it: **CapCom_Communication** 0x7EA51801–~0x7EA52CD9. CapCom has **4 instances** (getInstance 0x7EA51801/0x7EA5183C/0x7EA51877/0x7EA518B2, all called by CmpCst_Communication 0x7EA9D7CD) and drives the USB-communication device (§5.4).

**5.3 Cmp_PictBridgeComponent (verified bounds)** — **0x7EAEEAEF–0x7EB015FE** (≈77 KB):
- getInstance 0x7EAEEAEF (called from the Ctg area 0x7EB97098), ctor 0x7EAF006B, initStatechart 0x7EAF0E25, dispatch 0x7EAF0FEE, getName 0x7EAF08A2.
- Log prefixes `CmpPbr` / `CmpPbr0`. Large state handlers 0x7EAF2AFD–0x7EB004AF: print, continue_print, check_cap_print, index info.
- Its capability is **CapPbr_PictBridgeCommunicate** (0x7EA5890E–; ctor 0x7EA58D18; getName 0x7EA5B2D4). That capability uses the DPS / DPS-T / USB device classes (§5.4).
- API events: 13781–13821 (CustomPrint) and 13881–13905 (`evTraResPrt*`, EasyPrint) in the Ope layer.
- Before it: **CmpFnc_FunctionComponent** 0x7EAEC905–0x7EAEEAEE (picture-DB control: "CmpFunction OLDBControl receive Create/Abort request", 0x7EAED5CE–0x7EAEE00D; getInstance called from Ctg 0x7EB938CB). After it: CmpPCal at 0x7EB015FF.

**5.4 Device classes at 0x7EBA0AA9–0x7EBA48BB (verified API callees and callers; class names inferred) (A5 2026-11-09):**

| Range | Device | Evidence |
|---|---|---|
| 0x7EBA0AA9–0x7EBA28E0 | face information (0x7EBA0CA3/0x7EBA0CCA/0x7EBA0F8B → `api_rec_Get_Rec_Face_Number`/`…Face_Rect_Area`/`api_play_Get_FaceDirection`, the first ~1.7 KB) (A5 2026-11-09), anti-shake, image handle, HDMI 3D/EDID/CEC, histogram (dummy display calls), Exif/picture size, picture-file search/erase/count | `api_rec_Control_Anti_Shake`, `api_tft_*CEC*`, `api_histogram_*`, `api_picfile_*` |
| 0x7EBA28E1–0x7EBA330F | `DevBlu_Bluetooth` (vtable 0x7EC91628, ctor 0x7EBA2987, factory 0x7EBA290C called by the CapBlu ctor) + sub-object vtable 0x7EC916C8 | 39 `DevBlu_Bluetooth::*` strings |
| **0x7EBA3310–0x7EBA36F6** | **USB-communication device**. Accessors 0x7EBA3310/333C/3368/3394 (called by CapPbr 0x7EA58AF3 and CapCom 0x7EA51A8C) lead to ctor **0x7EBA33C0**. The ctor builds 4 mode sub-objects with 9-slot vtables: **DPS 0x7EC916F4, MTP 0x7EC91718, Storage 0x7EC9173C, generic 0x7EC91760**, and 8 observer lists at +48…+188. Slot 2 = `api_comm_End_Communication_<mode>`, slot 6 = `api_comm_Start_Communication_<mode>` (F060 0x7EBA35C2 = DPS start), slots 3/5/7 = `api_media_Initial_Strage` / `Mount_USB_Strage` | verified |
| 0x7EBA36F7–0x7EBA414D | DPS-T device (vtable 0x7EC91784; 16 small methods, then `api_dpst_Dpst_*` Req/Send for DPOF, print, reserve) | verified |
| 0x7EBA414E–0x7EBA43C3 | DPS device (vtable 0x7EC917E8; 25 `api_dps_*` wrappers: capability, job start/abort/continue, status) | verified |
| 0x7EBA43C4–0x7EBA45D7 | pixel mapping (`api_rec_Calculate/Save/Get_Pixelmaping*`; caller CapPxm 0x7EA60BD3) | verified |
| 0x7EBA45D8–0x7EBA48BB | picture-file creation (`api_picfile_Check_Create_PictureFile`; caller 0x7EA52E23, CapFrp), including six field helpers 0x7EBA4868–0x7EBA48BB called only by 0x7EBA4603/0x7EBA464F/0x7EBA4759 (A5 2026-11-09) | verified |

## 6. The Com_ framework (0x7EB84345–~~0x7EB8C265~~ 0x7EB8C264 (L1 2026-11-09)) (A5 2026-11-09)

| Function | Callers | Role |
|---|---|---|
| 0x7EB8701F / 0x7EB8705F | 4 / 4 | Com_ reactive base ctor/dtor (vtable 0x7EC8BD40). Default getName 0x7EB87270 returns `unknown`. | 
| 0x7EB8717D (slot 6) | vtable ×114 | takeEvent override: if slot 37 gives a delegate ≠ this, forward the event to it; else use OMReactive takeEvent |
| **0x7EB871B1** | 1,297 | gen to self = OMReactive gen 0x7EBA66D4; it logs `*****Q OVER?!*****` if the queue refuses |
| **0x7EB86DA1** / **0x7EB86DF0** / **0x7EB86ED0** | 313 / 386 / 606 | observer list ctor / addObserver (`#ERR# addObserver = NULL!`, duplicate warning) / notify-all. Notify iterates the list; for each observer it calls `vtbl[2]()` (filter), then `vtbl[0]()` (update) |
| 0x7EB85D67 / 0x7EB85D75 / 0x7EB85DAB | 272 / 271 / 356 | 24-byte observer member ctor (base 0x7E96E4DA) / dtor / setTarget(+20). The update callbacks of these observers usually have the 75-byte "observer callback" shape (§3). **Exception (C2 2026-11-09):** relay observers, e.g. `CapBlu_BluetoothEv2Observer` (ctor 0x7EA5119D, vtable 0x7EC412F4): its 35-byte update 0x7EA511D1 logs and calls notify-all 0x7EB86ED0 on this+24, and builds no event |
| 0x7EB867EB family | — | **request/response registry keyed by u16 event id**: register 0x7EB86ABF (384; 8-byte {id, requester}) and register+ack 0x7EB868BC (364; sends 11772); answer 0x7EB8693F (36) / answer-and-remove 0x7EB86A2A (109) / 0x7EB868D2 (206; deletes the response if no requester); remove 0x7EB86A8E (236); `ERR:unsubscribeForceDestroy` 0x7EB86B29. Delivery 0x7EB86D73 = `requester->vtbl[1](ev, params)` | verified shape; "request/response" inferred |
| 0x7EB855C7 / 0x7EB85972 | 3 / 1 | `resend event %d`; `handleNotConsumed EvID=%d` (re-queues an unconsumed event) |
| **0x7EB87341** / 0x7EB872DF | 429 / 70 | state trace `*** on state %2d [%s] ***`. It reads a global trace level (0x7E9672EA) and returns early when that level is above this+124. The name comes from getName (slot 36). Called from state-entry functions |
| 0x7EB87AC9 (ctor), 0x7EB878A2, 0x7EB880AC, 0x7EB88A2B, 0x7EB89D57 | 13 / 1–2 each | the class with the init states (vtable 0x7EC8BF08; slot-33 word 0x7EC8BF8C → dispatcher 0x7EB87B44, F058). Cap init base 0x7E9EF709 derives from it. The state functions log `CmpInitErr` |
| 0x7EB89520 … 0x7EB8AA26 | — | `Cab_CameraBase` (getName 0x7EB89694, dispatch 0x7EB89C05) with the top-level **mode machine**: `standbyState` 0x7EB8A332, `shootModeState` 0x7EB8A48C, PLAY 0x7EB8A757, `functionModeState` 0x7EB8AA26 (F059). States send 7002 and create categories (verified strings and calls; owner inferred from position) |
| 0x7EB8AD37– | — | `Com_ActiveTransitionManagerBufferd` (vtable 0x7EC8C708; "bud timing evTraStart") |
| 0x7EB8BCCB–~~0x7EB8C265~~ 0x7EB8C264 (L1 2026-11-09) | — | Com_ events 7001–7020 and 11561–11566 |

## 7. Corrections to section 06 and the map

1. **Event classes:** there are **1,273 vtables / 1,268 ids** (not ~930). Section 06's 930 counted only some data words. 250 of the classes are never constructed.
2. **Event location:**
   - Vtables span **0x7EBC0000–0x7EC92200**, not "mostly 0x7EBCE000–0x7EBF0000" (only 45% are there).
   - Ctors sit in each package's module (559 of them in Cap/Cmp code), not "in TraShareTakeStatus".
3. **"Event constructors ~~0x7E96B000–0x7E9823AB~~" (L1 2026-11-09) is wrong as a range label.**
   - Of the 2,603 functions there, 1,388 are event methods (ctor/isTypeOf/dtor, 26 KB of 95 KB).
   - The rest is operation-class code: `OlyHfwLowApiWrap` 0x7E974E7F–0x7E975704, `OlyHfwOpeLevel` 0x7E9782AF–~~0x7E97858C~~ ≥0x7E9786CE (0x7E97858C is the start of `reset`; `Ope::startLevel` 0x7E9785D3, which calls `api_user_Start_Slope_Event` 0x7E68EC99, follows it and ends at 0x7E9786CE; the exact end is not checked) (C3 2026-11-09), `OlyHfwOpePlyCom` 0x7E97B27A–0x7E97C487, `OlyHfwOpePlyMov` 0x7E981663–0x7E981F92, plus reactive classes such as the one with 1-second timeouts at 0x7E977ADA–0x7E977D6F (class name unknown).
   - The event-code runs are listed in §4.
4. **The OXF reactive base vtable is 0x7EC91FE8**, not 0x7EC6C320. 0x7EC6C320 is a derived component vtable (slot 0 = 0x7EB08A15). Slot 15 = getCurrentEvent; slot 6 = takeEvent; slots 32/33 = rootState_entDef/dispatchEvent.
5. **OXF ends at 0x7EBA7BC0** (the destructor helper 0x7EBA7BB5 is OXF, §1). 0x7EBA7BC1–0x7EBABF8D is OKAO Smart Skin (13b), not OXF. The device classes start at 0x7EBA0AA9 (Ctg ends there), not 0x7EBA1020. (A4 2026-11-09)
6. **chls_oldb "unnamed source file" (06 §4)** is the class **CapPDB_PlayOLDB** (getName 0x7EA26E13, ctor 0x7EA2384A).
7. **"Base methods copied into each file"**: the cause is statechart inheritance (§3), not header inlining (inferred, strong).
8. **"Cmp_ComponentManagerWithBoot 0x7EA7D072"** is the inherited getName that 26 component vtables share, so it does not mark a file.
9. **The transition-manager row (06 §1)** also holds `Cab_CameraBase` and the standby/shoot/play/function mode machine (§6).
10. **Region table:** the row "~~0x7EBA1020–0x7ECA0000~~ OXF runtime, DevBlu" (L1 2026-11-09) should read as in §1. Section 05's "0x7EBA6B03–0x7EBE1020 = strings" was already contradicted by C1.

## 8. Open questions

1. Name more ids: only 77 of 1,268 have a name. The sender/handler columns and the block owners give the package, but most names need a string-free method (e.g. matching `Ope::<method>` API names through the API trace id table, F041).
2. OMReactive slots 3, 10, 26, 31 and 34 are not settled. Neither is the exact meaning of status bit 0x40000 (mask 0x7EC91F18).
3. ~~What are the three other OMThread active objects (thread-ctor callers 0x7E96CA56, 0x7E96DB78, 0x7E9E762F)? Do they own separate event loops or tasks?~~ Answered: `HLS_CALLBACK` 0x7E96CA56, `HLS_EVENT` 0x7E96DB78 and `HLS_USER` 0x7E9E762F (thread-name strings; 14c §2.4) (D2 2026-11-09).
4. Global 0x602B4A88 (alternative vtable slots): who sets it? Is it Rhapsody animation?
5. ~~The vtable layout of the CmpSqp_* sequence parts (getName not at slot 36) is not resolved, and neither are their ctors.~~ Answered: plain C++ classes, ctors listed in §5 (D3 2026-11-09).
6. 0x7EBA7BC1–0x7EBAC000: confirm that it is an OKAO module (compare with the OKAO code at 0x7E72CFA1).
