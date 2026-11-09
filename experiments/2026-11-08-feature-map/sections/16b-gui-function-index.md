# 16b. GUI and CA_MAIN function index 0x7ECCB800–0x7EE02094 (E-PM2 v1.6, rounds D4–D5)

Scope: one row per function for the GUI, the GUI toolkit and the camera app (CA_MAIN / appCaller) code before it. It builds on 13d (toolkit, Ss engine, registries), 14e (slots, DC, shapes) and 15a (pages, panels, touch). The index is `16b-gui-function-index.tsv`.

- **Labels:** **V** = read in code, bytes or a decoded table; **I** = inferred (position, callers, name order).
- **Scratch:** `$S/d5/gui/` (D4 copy plus D5 changes). Build order: `core.py` → `api.py` (OlyApi vtables; names from `apiname.py`) → `vt.py`, `cls.py`, `fact.py` → `ca.py`, `ca2.py` → `tables.py` → `drawobj.py` (draw-object types) → `idx.py` (rules; effects `eff.py`, names `known.py`, D5 structures `d5rules.py`, small-code describer `micro.py`) → `mktsv.py OUT`. Metric: `classify.py TSV`.

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

## 5. Open questions
1. 283 Ss handlers return a value the rules do not resolve (unchanged).
2. Draw-object types other than 0x200C: what effect each slot-15 callee draws (I labels in §2.2) and which widgets the property types animate.
3. GPI layer-driver ops 0–11 and the GE queue internals (0x7ECE74D7–0x7ECE80C5) have no roles (48 % context).
4. CA state names: no per-state name table; GUI codes 0x84/0x85 in Misc rows (unchanged).
5. The display-variant values 0/1/2 of RAM 0x602B61F4 (I: output device).

## Known rule errors (open)
- **Behavioural rule (10):** the sentence lists inputs and sinks, not their order or conditions; on big functions it is a summary, not a role.
- **Draw-object slot roles** for types without the `asr 15` signature come from slot position only (I).
- **Partial-to-context drift:** rows longer than 340 characters lose their trailing `does:` part in the TSV.
- Fixed in D5 and removed from this list: the `hsw` rule (§3 rule 4), the OlyApi name-order rule (§2.8), "returns N" for stored constants, the "merged 1 unreachable stub" undercount, and Ss rows without callee effects (rule 1). Context-only "private method"/"helper of" rows for panels and pages are reduced (panels 12 → 7 %) but remain where no effect is visible.
