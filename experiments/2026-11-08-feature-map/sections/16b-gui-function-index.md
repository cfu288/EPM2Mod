# 16b. GUI and CA_MAIN function index 0x7ECCB800–0x7EE02094 (E-PM2 v1.6, rounds D4–D6)

Scope: one row per function for the GUI, the GUI toolkit and the camera app (CA_MAIN / appCaller) code before it. It builds on 13d (toolkit, Ss engine, registries), 14e (slots, DC, shapes) and 15a (pages, panels, touch). The index is `16b-gui-function-index.tsv`.

- **Labels:** **V** = read in code, bytes or a decoded table; **I** = inferred (position, callers, name order).
- **Scratch:** `$S/d6/gui/` (D5 copy plus the D6 precision changes, §6; D5 state in `$S/d5/gui/`). Build order: `core.py` → `api.py` (OlyApi vtables; names from `apiname.py`) → `vt.py`, `cls.py`, `fact.py` → `ca.py`, `ca2.py` → `tables.py` → `drawobj.py` (draw-object types) → `idx.py` (rules; effects `eff.py`, names `known.py`, D5 structures `d5rules.py`, small-code describer `micro.py`; D6: path enumerator `emu.py`, Ss results `ssemu.py`, CA ctx stores `cactx.py`) → `mktsv.py OUT`. Metric: `classify.py TSV`. Row checks: `check*/` (briefs, samples, results).

## 1. Area and boundaries (V unless marked)

| Range | Component | Basis |
|---|---|---|
| 0x7ECCB800–~0x7ECCFFFF | CA_MAIN OSD layer (`[OSD_CONTROL]`/`[OSDDRAW]` strings, debug shell 0x7ECCBA45; end is a round bound, I) | strings |
| ~0x7ECD0000–0x7ECD257E | CA application core: `applicationChanger` 0x7ECD0002, sub-app loop 0x7ECD0DC7, function table 0x7EED0BBC (44 entries) | strings, tables |
| 0x7ECD257F–0x7ECE39B9 | **CA sub-app handlers** (all 489 CA row handlers), sub-app classes, **boot-warning chooser 0x7ECD6031** (§2.4) | CA tables |
| 0x7ECE39BA–~0x7ECE6E04 | appCaller (getInstance 0x7ECE39D2, RAM 0x602B4BF4, vt 0x7EEEC80C), CA trace print 0x7ECE631E | code |
| 0x7ECE6E05–0x7ECEC798 | GuiCallerImp (vt 0x7EEF4AE4), GE message layer (0x7ECE7597 build / 0x7ECE75C3 post), **GPI display layer** (§2.6) | 13d §1 |
| 0x7ECEC799–0x7ECEE1D4 | GUI pools, UTF-16 helpers, CTouchPnl (getInstance 0x7ECED84E) | 13d §1 |
| 0x7ECEE1D5–0x7ECFF982 | toolkit core (root, **data model** §2.3, generic list, screen, container), widget base, C/D parts, renderers, DC, geometry | 14e §1 |
| 0x7ECFF983–0x7ED16F17 | GUI controller singletons CCommon … CRec (16b D4 table; ranges = [ctor, next ctor), I) | strings |
| 0x7ED16C72–0x7ED17B8A | **panel layout path**: post-create layout, display-variant change, layout tables A/B (§2.5) | code |
| 0x7ED16F18–0x7ED37DA9 | factory, CreatePanel, app window, widgets, **draw-object family** 0x7ED1F4F4–0x7ED22E5C (§2.2), drawing engine | vtables |
| 0x7ED37DAA–0x7ED82275 | 114 panel classes, class k = [ctor_k, ctor_k+1) over the factory table 0x7EF0F3B0 | factory table |
| 0x7ED82276–0x7EDC15AF | statechart engine, WinMain, Ss handlers, IGui_Controler, Actuator/Viewer objects | 13d §4 |
| 0x7EDC15B0–0x7EE02094 | guiUtility (with the **trace ring buffer** §2.7), menu-page framework, pages, GuiTouch, USB-connect screen | 15a §1 |

## 2. Tables and structures (V unless marked)

### 2.1 Unchanged from D4
- **Ss descriptor matrices** 0x7EFB8BCC (17 descriptors, 2,912 cells, 1,360 handlers). Action = handler return (13d return rule; one level of Ss callees; controller callees below 0x1200).
- **CA sub-app tables:** descriptors `{state, rows, count}`, rows `{event, GUI code, next, handler}`; event names 0x7EEEF378; six common tables (Boot 0x7EED8D4C, Misc 0x7EED92DC, Pc 0x7EEDA340, Play 0x7EEDB0C0, PlayHdmi 0x7EEDBB08, Shooting* 0x7EEEAF04). 4,177 + 190 rows, 489 handlers.
- Vtables (574 runs, 442 ctor-stored), C++ ctor table 0x7F033AC8, openPage cases, list registry 0x7EFE180C, Actuator/Viewer registry 0x7EFC5408, 15a touch rows.

### 2.2 GUI draw-object family (new)
- **Factory** 0x7ED1AFF9 = app window vt slot 197: type d0 0x2000–0x2012 → jump table 0x7EF0FF30 → `operator new` 0x7ED1F597 (GUI pool with the app-window pool bytes) → ctor → channel mask (slot 10) and layer bytes (slot 12) → import track (slot 1). Deleter 0x7ED1F5BE.
- **Base** ctor 0x7ED1F4F4, vt 0x7EF10EA4 (19 slots). Fields: +4, +8 pointers; +12 channel mask; +16..+18 bytes (layer ids +17/+18, registered with app window vt+248). Derived effect objects add +20 track array, +24 value (<<15 fixed point), +28 per-tick step.
- **Slot dictionary** (base / derived): 0 returns the deleter (derived calls base first); **1 import track(count d0, resource a1)**: pool-allocate +20 and copy the records whose mask matches +12 (base returns 1); 2 returns 1; **3 release track** (pool free); **4 apply keyframe d1** (effect types: +24 = key<<15, step +28 from 20-B time records; widget-property types such as 0x2003 set the target widget a1, which must be type 0x8003); **5 tick**: +24 += +28, returns 1 if +24>>15 changed (base returns 0); 6/7 set/get +4; 8/9 set/get +8; 10/11 set/get mask +12; 12/13 set/get layer bytes; 14 pre-draw, **15 draw on surface a1 in rect d0**, 16 post-draw (base: return 1); 17 message filter (−1); 18 empty notify map (`cmp 0x18FF`, −1). V on the base and on type 0x200C; the other types' slot roles are I where the byte signature (`asr 15`, pool free) is not checked.
- **Types** (type: size, ctor, vt): 0x2000 100 B 0x7ED22306 0x7EF11448 (own 56-slot class, I: container); 0x2001 56 0x7ED20484; 0x2002 36 0x7ED20D18; 0x2003 24 0x7ED1FC5F; 0x2004 24 0x7ED221E1; 0x2005 76 0x7ED21440; 0x2006 68 0x7ED21D58; 0x2007 36 0x7ED20FD1; 0x2008 40 0x7ED211DA; 0x2009 32 0x7ED1F600; 0x200A 32 0x7ED21783; 0x200B 36 0x7ED2009F; **0x200C 32 0x7ED202AF = keyframed 4-neighbour blur** (slot 15 → 0x7ED362AA, N = +24>>15; C6 F058/F059); 0x200D 40 0x7ED21937; 0x200E–0x2010 28 B (0x7ED1FF71, 0x7ED1FD98, 0x7ED1F7D5); 0x2011 64 0x7ED1F987; 0x2012 28 0x7ED21C09. Effect callees of slot 15 (I where unread): 0x200B 0x7ED360BB, 0x200D 0x7ED3655A, 0x200F 0x7ED3571D, 0x2010 0x7ED359D6, 0x2011 0x7ED36A6F, 0x2012 colour fill via 0x7ECFE9CF, 0x2009 empty 0x7ED359D3.

### 2.3 GUI data model singleton (new; links 07 §5)
- getInstance **0x7ECEF5DC** → RAM **0x602B5EB8** (28 B, ctor 0x7ECEF685, vt 0x7EEF54C8, dtor 0x7ECEF6A6/0x7ECEF6A9). Fields: u16 +4 capacity 16; +8 slot table of 16-B slots `{get hook, set hook, buffer, size}`; u16 +12 block count; +16 listener list.
- init 0x7ECEF608/0x7ECEF6DF (count ≤ 256, once), shutdown 0x7ECEF622, **get body 0x7ECEF760** (behind the 07 get 0x7ECEF64F), **set body 0x7ECEF7D9** (behind set 0x7ECEF667: copy, mark the block dirty in every listener 0x7ECEFDEF, optional notify 0x7ECEF8A7 → GM 0x1900 to each listener window 0x7ECEFE24). Hooks in RAM 0x602B5728/572C (init/term) and 0x602B5730/5734 (lock/unlock).
- Generic doubly linked list (12-B nodes {next, prev, item}, GUI pool 5): init 0x7ECEF905, destroy 0x7ECEF911, append 0x7ECEF932, remove 0x7ECEF99F, begin 0x7ECEFACB, next 0x7ECEFAE9.

### 2.4 CA_MAIN boot-warning chooser (new)
- **0x7ECD6031** tests in order card 0x7ECD63D7, date 0x7ECD64B7, lens 0x7ECD64F0, AVCHD 0x7ECD654A; logs `error Card/Date/Lens/AVCHD`, else `error none` and clears the **warning code RAM 0x605EFDCC** (reset 0x7ECD6018 also clears 0x605EFDD0).
- Codes: 6/7 card state (MediaCtrl::getMediaStateInfo queries through 0x7ECD3583), 10 `movie full`, 11 `movie full_still`, 8 `still full`; 9 date not set (unless the date screen 0x7ECD5D42 is opened, gated by 0x7ECD636E = C6 F055); 1–4 lens/mirror (`isMirrorSetup`, lens state vt+76, getSetting(26) = 115); 12 AVCHD error.

### 2.5 Panel layout tables (new; C6 F061)
- **Table A 0x7EF03C08**: 114 rows `{u32 panel type 0x6000+k, fn(variant d0)}` (53 distinct fns): per-type layout set-up of RAM layout blocks. **Table B 0x7EF03F98**: 114 rows `{type, fn(variant d0, panel a0)}` (63 fns): re-layout of a live panel.
- 0x7ED16C72(panel index, panel) runs A[index] at post-create with the **display variant** RAM 0x602B61F4; 0x7ED16CB1(0..2) changes the variant and re-lays out the top panel (0x7ED16CEF) and all panels (0x7ED16D58); lookups 0x7ED16EAB (A) / 0x7ED16EC8 (B); panel type = vt+8 + 0x5FFF (0x7ED16EE5). The variant is set from CCommon output-change paths (I: TFT/EVF/HDMI).

### 2.6 GPI display layer (new, partial)
- 0x7ECE842E (from 0x7ECE83E9 ← WinMain) builds a 16-entry layer-driver op table and 3 layer descriptors at RAM **0x605F56D0** (160 B each: u16 id, 720 × 480, bpp, stride at +144, ops copied to +76). Ops present: 0 0x7ECE879F, 1 0x7ECE87DD, 2 0x7ECE9168, 4 0x7ECE893D, 5 0x7ECE882B, 7 0x7ECE8CE4, 9 0x7ECE89D7, 11 0x7ECE92BD, 12 0x7ECE91DD (`GPISetPalette`), 14 0x7ECE932D, 15 0x7ECE935A. What ops 0–11 do is open.

### 2.7 GUI trace ring buffer (new; C6 F066)
- 120 records × 16 B at *RAM 0x6069FCCC, index 0x6069FCD0: init 0x7EDC42C0 (480 words), next record 0x7EDC42F7, address (i mod 120)×16 0x7EDC430D. Kind 1 {1, d0, d1, a0} = state change (0x7EDC4606 from hook 0x7EDC4205); kind 2 {2, tag, d1, a0} 0x7EDC461D with caller tags 1 WinMain RDSTDoEvent, 2 PostEventToCA, 3 ShowPanel, 4 palette, 6 BackGroundCtrl, 7 JPEG/black-screen, 8 CGuiDrawCtrl, 9 guiEventFilter (tag 5 = 0x7EDC6F56). Dump 0x7EDC4323 (`[ChgStat]`, `[Main] RDSTDoEvent`, …).

### 2.8 OlyApi names (fixed rule)
- Each OlyApi slot function passes its id `0xGGCCMM` to **0x7E96E5F0**, which returns the name from a 3-level table at RAM **0x602B1F10** (`.data`): group G−1 → class C−1 → method M−1. The index now reads the name there (V). The old rule ("M-th `Class::method` string in string order") was off for **MediaCtrl only**: the string `MediaCtrl::unmountMedia ` has a trailing space, so the regex skipped it and every later MediaCtrl name moved one place. 16 MediaCtrl slots changed name (e.g. vt+40 = unlockProtectAll, **vt+44 = transferImageAll**, vt+60 = cancelTransferImageAll). This settles the D4 open question: 15a is right. CustomPrint was already right (vt+60 canPrint 0x5031D, vt+84 getPrintCount 0x50320).

## 3. Rules (first match gives the primary role; effects and returns are appended)
1. **ss / ss-entry / ss-merged / ss-body**: Ss handler, entry, exit, or the body behind a handler pointer entry. **D5:** the row adds one level of non-Ss callee effects (`via 0xT: …`), e.g. 0x7EDB4CBC `via 0x7ED07A1D: getSetting(100), setSetting, PlaySound::setVolume`.
2. **ca / ca-merged / ca-body**: CA row handler; **D5:** the body behind a 3–5-byte handler pointer entry gets "body of CA row handler 0xA" (78 rows).
3. **struct** (D5): a role from §2.2–2.8 or a C6 review row (`d5rules.py`, 90 rows).
4. **hsw** (fixed): a case block only if (a) the table user ends with `jmp (aN)` (in itself or the next DB function), (b) the target does not start with `movm`, (c) the table is cut at the user's `cmp END,aN` bound. The row gives the switch value when the user subtracts a bias (`mov −N,dX; add`), e.g. 0x7EED5254 keys are value − 21. A key-0 row is the empty-slot/default target. **ftab**: a `{key, fn}` table whose targets are called (`calls (aN)`) or have a prologue gives "function-table entry" (no row needs it now: its only target 0x7EE01FF5 has a struct role).
5. **doc / touch / jtab / ctortab** as in D4.
6. **vt**: `<class> vt slot k = <slot role>`; D5 adds the draw-object dictionary (§2.2), class names for the data model, appCaller and GuiCallerImp, and **"body of … vt slot k (its pointer entry is 0xA)"**.
7. **pentry** (D5, 511 rows): a DB function of ≤ 4 instructions that only does `movm`/`add −N,sp`/stack stores and falls into the next function is the **pointer entry** of that body (direct `call`s enter the body; pointers enter at the `movm`).
8. **layout** (D5): table A/B entries (§2.5), also through pointer entries (115 rows).
9. openpage / listreg / actreg / 15a, ctor, str, shape, api wrapper, pmf/imm/dataw as in D4.
10. **synth** (D5, 1,693 rows; only when no rule above gave a role): a behaviour sentence from the verified call effects: `updates child widgets (visibility, label text, …) from <DM blocks / settings / OlyApi>`, `read-modify-write of DM block N`, `setSetting(id)`, `ShowPanelEx(n)`, `post GM x`, `PostEventToCA(code)`, `draws with the DC (…)`, and for functions ≤ 160 B `predicate on <inputs>: returns 0/1` or `reads <inputs>`.
11. **code** (D5, 280 rows): exact behaviour of straight-line code (≤ 14 instructions, no conditional branch), e.g. `sets a0+108 = d0; sets a0+120 (u16) = d1; calls 0x7E500D33; returns 1`.
12. range / ctrl-range / caller as in D4; the caller's text is now in brackets.
- **Return values (fixed):** a constant that is also stored to memory just before `ret` is reported only if some caller reads d0 after the call (fixes "returns 4000" on 0x7ED89B73 and the C6 F061 "returns 403" class; 227 rows changed).
- **Split-off exit blocks (D5):** a 1–2-instruction `ret` fragment with no callers, no vtable use and no pointer entry is "split-off exit block of the preceding code", not "empty method" (0x7ECD7D5B, 0x7ED11E9F).
- **Merged vtable methods (fixed):** a DB function that contains other vtable targets says "also holds N more vtable method(s) merged by fwmap" with their slots (334 rows), e.g. 0x7ED1F53A holds 7 base draw-object methods (C6 F057).

## 4. Coverage, error rate, corrections

### 4.1 Coverage (measured with `classify.py` on all 11,586 function rows; 0 blank)
| Class | D4 TSV | D5 TSV |
|---|---|---|
| **specific** (table, slot role, string name, documented/decoded structure, exact shape) | 6,298 (54.4 %) | 7,038 (60.7 %) |
| **behavioural** (rule 10, role sentence from verified calls) | — | 1,693 (14.6 %) |
| **exact code** (rule 11) | — | 280 (2.4 %) |
| partial (own effects/returns/logs, no role) | 2,954 (25.5 %) | 960 (8.3 %) |
| **context only** (caller, class range, unnamed slot, address taken) | 2,334 (20.1 %) | 1,615 (13.9 %) |

- Specific + behavioural + exact code: 54.4 % → **77.8 %**. V/I: 8,820/2,766 → 9,205/2,381.
- Context share by area (D4 → D5): toolkit core–geometry 47 → 28 %, factory/widgets/draw objects 40 → 26 %, controllers 23 → 14 %, panels 12 → 7 %, pages/guiUtility 16 → 12 %, CA_MAIN 15 → 13 %; **GE/GPI 55 → 48 % and pools/UTF-16 60 → 59 % are still the weakest**.
- Diff against the D4 TSV: 5,175 rows changed text (truncation ignored): 584 context → specific, 1,693 partial/context → behavioural, 280 → exact code, 159 partial → specific; 21 partial → context and 1 specific → partial are measurement effects of longer rows, not lost content.

### 4.2 Measured error rate (error = any false claim, read in the disassembly)
| Sample | Rows | Errors |
|---|---|---|
| D5 spot check of changed rows (seed 5150) | 10 | 1: 0x7ECEFD68 said "a dirty bitmap"; it allocates two (+12, +16). Fixed |
| **D5 final, fresh random (seed 90210)** | 30 | **1 (3.3 %)**: 0x7ED89B73 "returns 4000" (stored to +76; no caller reads d0). Fixed by the return rule above. Not false but thin: 6 context-only rows |
| D5 confirmation after the fix (seed 31337) | 10 | 0 |

- One more defect found and fixed during the check: the small-code describer split `mov d0,(108,a0)` at the wrong comma and missed stores (no false claim had resulted).

### 4.3 Corrections to older sections
1. **16b D4 row/md 0x7ED16C72:** the table is **0x7EF03C08** (not 0x7EF04808) and there is a second table B 0x7EF03F98 (§2.5).
2. **16b D4 OlyApi names (and 13d §6.2 if it uses the name order):** MediaCtrl names were one slot off (§2.8). 15a §2.2 (pages 511/513 call vt+44 = transferImageAll) is right.
3. **16b D4 hsw rows:** 0x7EE01FF5 is a real function (setting-id redirect of 0x7EE01F66, C6 F070); 0x7ECD7D5B is past the table bound of 0x7EED5254. The other 56 hsw rows were re-checked by rule 4.
4. **07 §5 data model:** add getInstance 0x7ECEF5DC, ctor, slot layout, get/set bodies, listener bitmaps and the GM 0x1900 notify (§2.3).
5. **13d §2.2 / 14e:** WinMain slot 197 is the draw-object factory, not an unnamed slot (§2.2).
6. **16b D4 §1 "draw-object family (19 classes, ctors 0x7ED1F4F4–0x7ED221E1)":** 18 classes derive from 0x7EF10EA4; type 0x2000 (ctor 0x7ED22306) has its own 56-slot vtable.
7. **15a page-class spans (D6):** 51 page-class rows end before their last method; 81 functions follow them (§6.1 item 4). Page 422 runs to 0x7EDD7C31 (15a gives 0x7EDD7A57; C7 F066); the live-guide controller (getInstance 0x7EDD7C32, RAM 0x602BD5E4) starts there.
8. **16b D5 CA rows "→ same state":** of the 489 CA handlers, 45 set the next state themselves on every path, 36 on some code path and 266 never; 142 could not be fully enumerated and carry a hedge (§6.1 item 1); e.g. Pc 0x6004 CBK_DEVLINK_REQ_FIRMUP → 0x6000 with SUB_EVENT_START_FIRMUP (C7 F054).

## 5. Open questions
1. 283 Ss handlers return a value the rules do not resolve (unchanged).
2. Draw-object types other than 0x200C: what effect each slot-15 callee draws (I labels in §2.2) and which widgets the property types animate.
3. GPI layer-driver ops 0–11 and the GE queue internals (0x7ECE74D7–0x7ECE80C5) have no roles (48 % context).
4. CA state names: no per-state name table; GUI codes 0x84/0x85 in Misc rows (unchanged).
5. The display-variant values 0/1/2 of RAM 0x602B61F4 (I: output device).

## 6. D6 precision cycle (2026-11-09)

Goal: precision, not coverage. Every rule (`basis`, first code) with more than 50 rows was sampled at random and each row was read in the disassembly and the table bytes by a checker that saw only the row (`check/`, `check2/`, `check3/`, `check4/`). Error = any false claim in the row. THIN = true but context only (not an error).

### 6.1 Named rule errors, fixed
1. **CA next state.** The rows read only the table's static next field. D6 runs each CA handler through a path enumerator (`emu.py`) with a symbolic ctx in a1 and sentinels at ctx+92 (next state), +100 (next-state slot the runner uses when ctx+104 = 1), +76 (sub-event request) and +28 (GUI code), and reads their final values on every path. Callees that receive ctx are entered. Results: "→ next state 0x6000 (set by the handler; the table says same state)" when every path sets it; "same state (a code path in the handler sets 0x5108; path feasibility not checked)" when some do; when the enumeration does not finish, a hedge ("table next: same state (the handler was not fully analysed; it may change ctx+92)" or "the handler code … contains stores ctx+92 = …; whether they run on these events is not checked"). Example: 0x7ECE10CB → next state 0x6000, sub-event 0x09000000 SUB_EVENT_START_FIRMUP, GUI code 0x85; 0x7ECE0E37/0x7ECE0E3C → 0x6000 and 0x0900000F. The static scan alone missed stores in 5 of 280 "same state" handlers (e.g. 0x7ECE35F8 through 0x7ECDCFB0), so it is used only as a hedge.
2. **Tail call read as a return.** `micro.py` reports "returns d0 of X" only if a caller reads d0; it names call targets by their slot role and constant argument ("calls 0x7ED6F7D9 = getChild(i) with d0 = 136" for 0x7ED719EB).
3. **Text cut at a fixed length.** All cuts now go through `cut()` (word boundary, never inside a number, marked "…"; the TSV cap is 420 characters). 0x7EDDBCA2 now reads "RAM 0x602BDA2C".
4. **Class spans that end early.** A 15a page-class span is extended over the following functions while each has evidence: an own vtable method, a caller that passes the class getInstance result in a0 (same basic block, callee keeps a0), all callers already in the class, or a read of the class singleton. 81 functions moved into 51 page classes; page 422 now runs to 0x7EDD7C32 (the live-guide helpers start there). Two contradictions now override a range: all callers lie in one other panel/page class (31 rows, e.g. 0x7ED4A845 is panel 53 code, not panel 94), or callers pass another singleton's getInstance result (6 rows, e.g. 0x7ED01DDD is a CCommon getter of +292); a function called only by another getInstance is the ctor of the object it allocates (0x7ED01DF2).
5. **Ss destination built in a callee.** The Ss action now comes from path enumeration of the handler: the callees that write the (SS, state) outputs through pointers, Ss-range callees, tail calls, switches with a constant selector and (when the budget allows) every GUI callee are entered; RAM stores are tracked. 0x7EDA4C16 → "switch to SS_MENU_LV state 9 ANIMATION" (0x0409, via 0x7EDD7C9D case 0x7EDD7CD7); 0x7EDB4B11 → 0x0104 BLACK_SCREEN; 0x7EDA2E42 → 0x0104. Of 1,360 handlers, 1,081 resolve completely, 139 partly ("… / other paths not resolved"); the rest keep the D5 fact text or a hedge ("possible results (static scan; paths not checked)"). The enumeration also corrected D5 result sets that included dead branches (0x7EDA2FBD: only 0x0104; 0x7EDA2DD3: 23 or 0x0104).
6. **Dispatcher rows.** A switch with a constant selector is entered, so only its taken case adds effects ("0x7EDD7C9D takes case 0x7EDD7CD7 (jump table)"). The switch's own row says "switch through its jump table 0x7EFE9068 (25 entries, M distinct targets)" and "its code calls (all cases together): …" instead of a behaviour sentence; jump-table cases are no longer listed as "merged vtable methods" (123 of the 132 ctor-less tables are jump tables).

### 6.2 Other rules fixed after a wrong sample row
| Rule | Defect found | Fix |
|---|---|---|
| returns (all rules) | constants written to the return register on other paths (0x7ED02833 "returns 1/4", 4 is a divisor); leftovers that no caller reads (0x7ECF6779, 0x7ED9E93D, layout functions) | values from path enumeration; reported only if a caller reads d0 (callers that return d0 unchanged pass the test to their callers; a following call does not count as a read); for functions reached only through pointers only constants loaded into d0 just before `ret` |
| ss-table | handler entries inside a merged function copied the containing function's row | the entry is described on its own |
| shape | "short wrapper" for an endless task loop (0x7ECE7DDD); "A then B" for exclusive branches | needs a return and no backward `bra`; calls after a conditional branch → "short function; calls (conditionally) …" |
| hsw | "merged unreachable stub(s)" were other case blocks; key-0 rows claimed a jump | reachability text checks table/pointer targets; key-0 rows now say "target word of the empty (key 0) slots …; not checked", label I; bias also read from `add −N,dX` |
| str | "named X" from a callee or enum in the message (0x7ED0BA20 "guiUtility::getReserveEventStatusForSync()", "CPlaySingleFrame::NEXT_REC"); "logs" for compared strings | a name must open the message or be the whole [tag], be used by one function only, not be ALL-CAPS; "references strings" instead of "logs" |
| synth | "reads" for command calls (PlaySelect::start); "from"/"then" implied data flow | API calls count as reads only for get/is/can/has/check methods; sentences list setters, reads and outputs without order |
| vt | "(own slot)" when the base vtable was not linked; container slot 104 "child-list accessor" (0x7ECF319B compares and sets a 16-B field) | "(own slot)" only with a known base chain; slot 104 name removed |
| ctor/class names | "class userGuiBTSelectWizard::init" from a log string before the vtable | strings with "::" or shared by several vtables are not class names |
| pmf | "static initialiser" for a ctor that stores a pointer-to-member in the object (0x7ED8C1DA) | "stored into the object by ctor …" |
| openpage | getInstance result paired across switch cases | basic-block pairing (see 6.1 item 4) |
| struct/known | 0x7ECD654A "returns 1" (0 or 1); 0x7ECD3583 query offsets; 0x7EDCCC9E "greyed test" (it is the enabled test) | texts corrected |
| ca-body | the bracket used only 2 table rows (dropped state 0x5C02) | all rows |
| ss | action list cut at 6 values (0x7EDA5073 lost 0x0406) | up to 10, then "+N more results" |
| Ss/caller effects | callee effects listed for branches the handler's constants exclude (0x7ED83821 getPairingResult) | effects come from the enumerated paths; callees not entered are listed as "0xT (not analysed) may call …" |

### 6.3 Rule precision (fresh random samples; R1–R3 = successive rounds, each after the fixes of the round before; R4 = re-sample of the rules fixed after R3)
| Rule (basis) | Rows | V / I | R1 checked/wrong | R2 | R3 | R4 | Last sample: precision | THIN in R3 |
|---|---|---|---|---|---|---|---|---|
| vt | 2901 | 2901 / 0 | 10/1 | 10/0 | 10/0 | – | 10/10 = 100 % | 1 |
| ca-table | 2336 | 2336 / 0 | 10/0 | 10/0 | 10/1 | 10/0 | 10/10 = 100 % | 0 |
| synth | 1707 | 536 / 1171 | 10/2 | 10/2 | 10/0 | – | 10/10 = 100 % | 1 |
| ss-table | 1484 | 1484 / 0 | 10/2 | 10/0 | 10/0 | – | 10/10 = 100 % | 0 |
| ss | 1158 | 1155 / 3 | 10/4 | 10/0 | 10/0 | 10/0 | 10/10 = 100 % | 0 |
| shape | 1013 | 1013 / 0 | 10/2 | 10/0 | 10/1 | 10/0 | 10/10 = 100 % | 2 |
| caller | 794 | 0 / 794 | 10/0 | 10/0 | 10/0 | – | 10/10 = 100 % | 10 |
| str | 589 | 589 / 0 | 10/1 | 10/1 | 10/0 | – | 10/10 = 100 % | 1 |
| pentry | 512 | 512 / 0 | 10/0 | 10/1 | 10/0 | – | 10/10 = 100 % | 3 |
| ca | 489 | 489 / 0 | 10/0 | 10/0 | 10/1 | 10/0 | 10/10 = 100 % | 0 |
| ctor | 430 | 430 / 0 | 10/0 | 10/1 | 10/0 | – | 10/10 = 100 % | 0 |
| ss-entry | 284 | 279 / 5 | 10/0 | 10/0 | 10/0 | – | 10/10 = 100 % | 0 |
| code | 271 | 199 / 72 | 10/0 | 10/4 | 10/1 | 10/0 | 10/10 = 100 % | 0 |
| range | 223 | 0 / 223 | 10/1 | 10/0 | 10/0 | – | 10/10 = 100 % | 8 |
| openpage | 179 | 179 / 0 | 10/0 | 10/4 | 10/0 | – | 10/10 = 100 % | 0 |
| pmf | 161 | 161 / 0 | 10/1 | 10/1 | 10/0 | – | 10/10 = 100 % | 5 |
| api | 127 | 127 / 0 | 10/0 | 10/1 | 10/0 | – | 10/10 = 100 % | 0 |
| layout | 115 | 115 / 0 | 10/2 | 10/0 | 10/0 | – | 10/10 = 100 % | 0 |
| ctrl-range | 104 | 0 / 104 | 10/3 | 10/0 | 10/0 | – | 10/10 = 100 % | 9 |
| struct | 90 | 83 / 7 | 10/1 | 10/1 | 10/0 | – | 10/10 = 100 % | 0 |
| ca-body | 78 | 78 / 0 | 10/0 | 10/0 | 10/2 | 10/0 | 10/10 = 100 % | 0 |
| touch | 64 | 64 / 0 | 10/0 | 10/0 | 10/0 | – | 10/10 = 100 % | 0 |
| hsw | 56 | 41 / 15 | 10/5 | 10/2 | 10/2 | 10/1 | 9/10 = 90 % | 0 |
| **all** | | | 230/25 | 230/18 | 230/8 | 70/1 | | |

- 23 rule groups have more than 50 rows (the Ss and CA table-decode rows are counted as two groups). 760 sampled rows in four rounds, 52 wrong; every wrong row led to a fix (§6.1, §6.2) or a demotion (§6.4) before the next round. R1 checked the D6 build after the six named fixes; R4 re-sampled only the rules fixed after R3.
- The checkers were blind (row text only) and decoded tables, names and literals from the block-0 bytes themselves. One R1 verdict was a checker error (0x7ED7FF55 "returns e.g. 33/59": the copied halfwords at 0x7EF9CC2A/0x7EF9CC32 are 33 and 59); it is counted as wrong anyway, because the value was a leftover no caller reads.
- THIN (true, context only) is common in the I rules: caller 10/10, ctrl-range 9/10, range 8/10 in R3. These rules give position, not roles.

### 6.4 Demoted rules
- **hsw key-0 rows** (15 rows) → I, reworded "target word of the empty (key 0) slots …; whether the switch jumps there or returns on an empty slot is not checked" (R3: two key-0 targets are never reached by the jump).
- **"fwmap merged code after an unconditional exit … (no branch, table or pointer … found)"** clause (11 rows) → those rows are I. The R4 error (0x7ED09CC7: the switch user jumps to the "merged" blocks) is fixed (branch targets from all functions are now checked), but the clause was not re-sampled.
- **CA next state when path enumeration does not finish** (142 handlers): only hedges ("table next: … (the handler was not fully analysed …)", "… contains stores ctx+92 = …; whether they run on these events is not checked"); stores reached only on some paths say "a code path … can set …; path feasibility not checked".
- **Ss result sets from the static scan** (36 rows): "possible results (static scan; paths not checked): …".
- **Return values:** cut to values a caller reads (1,892 rows with "returns" in D5 → about 1,290 in D6).
- **Callee effects not on enumerated paths:** "0xT (not analysed) may call …".
- Rules already labelled I (caller, range, ctrl-range, synth on I bases) stay I; their sampled rows were true but mostly thin.

### 6.5 Final check
- **40 fresh random rows of the final TSV** (seed 271828, none sampled before; `check4/final40.tsv`), checked blind against code and bytes: **36 OK, 4 THIN, 0 WRONG; 0 wrong among the V rows.** One of the 40 rows (0x7EDFBD79) changed text after the check: it lost a true clause (a later fix limits the "called only by getInstance" override to callers in another class).
- Earlier final checks of intermediate builds: R2 build 2 wrong in 40 (leftover "returns"; fixed by the recursive d0-use test), R3 build 1 wrong in 40 (Ss result list cut at 6 values; fixed).

### 6.6 Shares (classify.py, 11,586 function rows; D5 → D6)
| Class | D5 | D6 |
|---|---|---|
| specific | 7,038 (60.7 %) | 7,024 (60.6 %) |
| behavioural | 1,693 (14.6 %) | 1,707 (14.7 %) |
| exact code | 280 (2.4 %) | 271 (2.3 %) |
| partial | 960 (8.3 %) | 995 (8.6 %) |
| context only | 1,615 (13.9 %) | 1,589 (13.7 %) |

- V/I: 9,205/2,381 → 9,180/2,406. Rows changed: 5,449 of 11,586 function rows and 2,214 of 3,820 table-decode rows.
- The shares hardly move: D6 removed false text (return values, merged-stub claims, "reads" for commands) about as often as it added resolved destinations. Ss rows with a resolved destination: 837 → 1,017 (878 complete, 139 partial; rows, not handlers).

## Known rule errors (open)
- **Path feasibility.** The enumerator forks on every unknown condition, so a value from an infeasible path can appear in a result set or a "code path can set …" clause (the CA wording says so). Checked samples found no false Ss result set after the R3 fixes, but the over-approximation is structural.
- **Unanalysed handlers.** 37 Ss handlers exceed the budget and 103 have no constant result; 142 of 489 CA handlers keep the static hedge. Their rows give facts or hedges, not destinations.
- **Callee effects not path-checked.** "0xT (not analysed) may call …" lists the callee's own calls on all its branches.
- **Behavioural rule (10):** lists setters, reads and outputs; on big functions it is a summary, not a role.
- **Draw-object slot roles** for types without the `asr 15` signature come from slot position only (I).
- **Slot-role dictionaries** (ROOT/CONT/WIDG/SCREEN/PGB/LISTP in `idx.py`) were hand-made in D4; one wrong entry (CONT 104) was found and removed in D6. Entries are not all re-verified.
- **Rows longer than 420 characters** end in "…" (cut at a word boundary).
- Fixed in D6 and removed from this list: the static next-state rule, tail-call returns, fixed-length cuts, early page-class span ends, Ss destinations built in callees, dispatcher unions, and the rule errors of §6.2.
