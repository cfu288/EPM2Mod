# 16b. GUI and CA_MAIN function index 0x7ECCB800–0x7EE02094 (E-PM2 v1.6, round D4)

Scope: one row per function for the GUI, the GUI toolkit and the camera app (CA_MAIN / appCaller) code before it. It builds on 13d (toolkit, Ss engine, registries), 14e (slots, DC, shapes) and 15a (pages, panels, touch). The index is `16b-gui-function-index.tsv`.

- **Labels:** **V** = read in code, bytes or a decoded table; **I** = inferred (position, callers, name order).
- **Scratch:** `$S/d4/gui/`. Build order: `core.py` (map DB) → `api.py` (OlyApi vtables) → `vt.py`, `cls.py`, `fact.py` (vtables, ctor chains, factory types) → `ca.py`, `ca2.py` (CA tables) → `tables.py` (15a TSV, registries, settings, strings) → `idx.py` (rules, effects in `eff.py`, names in `known.py`) → `mktsv.py OUT`. Verification dumps: `ver.py`, `final_sample.txt`, `final2.txt`, `final3.txt`, `final4.txt`.

## 1. Area and boundaries (V unless marked)

| Range | Component | Basis |
|---|---|---|
| 0x7ECCB800–~0x7ECCFFFF | CA_MAIN OSD layer: `[OSD_CONTROL]`/`[OSDDRAW]`/`[OSDDBG]` strings in 32 functions 0x7ECCB8F9–0x7ECCF9C2, debug shell 0x7ECCBA45, MMIO 0x9AA000xx writes (end is a round bound, I) | strings |
| ~0x7ECD0000–0x7ECD257E | CA application core: `applicationChanger` 0x7ECD0002, sub-app loop 0x7ECD0DC7, function table 0x7EED0BBC (44 entries, loaded by 0x7ECD1886; its entries log key-judge strings such as `KEY_1ST_JUDGE_NG`, I), two classes with vt 0x7EED02AC / 0x7EED03BC (ctors 0x7ECD05B3 / 0x7ECD11F2; strings `StartProc`, `PcApp:sub-app start proc`) | strings, tables |
| 0x7ECD257F–0x7ECE39B9 | **CA sub-app handlers**: all 489 CA row handlers lie here, mixed with `*SubAppMdl*`/`*SubAppModule*` modules and the sub-app classes (§2.2) | CA tables |
| 0x7ECE39BA–~0x7ECE6E04 | appCaller: getInstance 0x7ECE39D2 (RAM 0x602B4BF4, 128 B, ctor 0x7ECE3A0A, vt 0x7EEEC80C, 21 slots: `startThrough`, `stopThrough`, `getExposeMode`, …), `setCameraAppData` 0x7ECE3DCD, CA trace print 0x7ECE631E | code, strings |
| 0x7ECE6E05–0x7ECEC798 | GuiCallerImp (ctor 0x7ECE6E05, vt 0x7EEF4AE4; sendEvent 0x7ECE6E27), GE message layer (0x7ECE7597/0x7ECE75C3), GPI display layer | 13d §1 |
| 0x7ECEC799–0x7ECEE1D4 | GUI pools, UTF-16 helpers, CTouchPnl; touch singleton getInstance 0x7ECED84E (RAM 0x602B5EB4, 64 B, 267 callers) | 13d §1 |
| 0x7ECEE1D5–0x7ECFF982 | toolkit core, widget base, C/D parts, renderers, DC, geometry | 14e §1 |
| 0x7ECFF983–0x7ED16F17 | **GUI controller singletons** (getInstance + strings): CCommon 0x7ECFF983 (RAM 0x602B6038); 92-B singleton 0x7ED01D91 (RAM 0x602B6040); CGuiDrawCtrl 0x7ED01DFD (0x602B6044); BackGroundCtrl wrapper 0x7ED022EE (0x602B6048); CPlayCalendar 0x7ED02438 (0x602B6050); CPlayIndex 0x7ED02C53 (0x602B6054, 3,300 B); play-start chooser 0x7ED053D9 (0x602B6058); CPlayLightBox 0x7ED0595E (0x602B605C); **CPlayMovie 0x7ED07225** (0x602B6060); CPlaySingleFrame 0x7ED08FA7 (0x602B6064); CPlayZoom 0x7ED0F04C (0x602B606C); CRec 0x7ED0FF47 (0x602B6070) | ranges = [ctor, next ctor) (I) |
| 0x7ED16F18–0x7ED37DA9 | factory class 0x0105, factory, CreatePanel, app window, widgets, **draw-object family** (19 classes, ctors 0x7ED1F4F4–0x7ED221E1, base vt 0x7EF10EA4, 19 slots each; slot 18 has the empty-notify-map shape `cmp 0x18FF → −1`) | vtables |
| 0x7ED37DAA–0x7ED82275 | 114 panel classes. Class k = [ctor_k, ctor_k+1) over **all 114** factory ctors (table 0x7EF0F3B0), not only the 98 numbered ones (§4.1) | factory table |
| 0x7ED82276–0x7EDC15AF | statechart engine, WinMain, Ss handlers, IGui_Controler, Actuator/Viewer objects | 13d §4 |
| 0x7EDC15B0–0x7EE02094 | guiUtility, menu-page framework, pages, GuiTouch, USB-connect screen | 15a §1 |

## 2. Tables decoded completely (V)

### 2.1 Ss descriptor matrices (13d §4.1 format)
- All 17 descriptors at 0x7EFB8BCC: 2,912 non-default (SS, state, event) cells, 1,360 handler functions, 224 entry and 105 exit slots. 203 handler entry points are not DB function starts; their containing DB function says "contains / also contains Ss handler(s) merged by fwmap".
- **Action** = the handler's return value (13d return rule: 0 stay, 1–255 state, `(ss<<8)|state` switch). The rules, in order:
  1. a constant in d0 at a reachable `ret`;
  2. the constants written to the register that is moved to d0 before `ret` (only if every write to it is a constant);
  3. for `call X ; [ext] ; ret` or `call X ; bra L ; L: [ext] ; ret`, the result of X: for X in the Ss range, X's constants (one level); for X in a controller class, X's constants below 0x1200;
  4. `asl 8 ; or` before `ret` gives "(SS<<8)|state assembled from locals" (constants stored to those stack slots, when they are found).
- The shared stay action 0x7EDA2654 (`clr d0; retf`) counts as "stay".
- Effects are listed after `does:`: ShowPanelEx(n), PostEventToCA(code, info) with names from 0x7EEEFFD0 / 0x7EEF05E4, self-post events (names 0x7EFDEF78), DM get/set block, get/setSetting(id, label from 07-settings.tsv), page key calls (current page RAM 0x602BCF04 vt+12, d0 = key), openPage, OlyApi `Class::method`, posted GM ids (names 0x7EFDFDA8).
- Result over the handler rows: 946 give constant actions, 53 a named callee result, 283 only "a state computed in the handler" (open, §5).
- TSV rows `SS_x[states]/0xEVENT` (1,484): one row per (SS, event, handler), states grouped.

### 2.2 CA sub-app state tables
- **Descriptor arrays** `{u32 state, u32 rows, u32 count}` (12 B), registered by the sub-app classes. **Rows** `{u32 event, u32 GUI code, u32 next state, u32 handler}` (16 B).
  - next = 1 means "no change";
  - GUI code 0/1 = none; any other code k is mapped to a GUI event through `{k, event}` 0x7EEF3434 (0x7FFF = none);
  - handler may be NULL (pure GUI-code forwarding).
- **CA event names:** the 392 `{u32 event, char*}` pairs at 0x7EEEF378–0x7EEEFFB7 (OLY_* keys/devices 0x01, TOUCH_* 0x02, CBK_* callbacks 0x03, GUI_* codes 0x04, MNG_* 0x05, CAM_START_* 0x06, SUB_EVENT_* 0x09, …).
- **Sub-app names:** from the `search X` cases of 0x7ECE29C6 and the `command XCommon` classes.

| Id | Sub-app | States | Rows | Id | Sub-app | States | Rows |
|---|---|---|---|---|---|---|---|
| 0x10 | Boot (0x7EED8F2C) | 5 | 12 | 0x55 | Shooting3D | 2 | 65 |
| 0x20 | Misc (0x7EED9DBC) | 9 | 157 | 0x56 | ShootingAssist | 1 | 22 |
| 0x30 | Play (0x7EEDB990) | 7 | 107 | 0x57 | ShootingMenu (0x7EEE10B4) | 6 | 134 |
| 0x40 | PlayHdmi (0x7EEDC7E8) | 8 | 175 | 0x58 | ShootingModeDirect | 14 | 554 |
| 0x50 | ShootingCommon | 6 | 74 | 0x59 | ShootingFuncDirect | 21 | 415 |
| 0x51 | ShootingStill | 10 | 331 | 0x5A | ShootingLvMagnify | 13 | 808 |
| 0x52 | ShootingPanorama | 3 | 97 | 0x5B | ShootingInterval | 5 | 204 |
| 0x53 | ShootingMovie | 6 | 318 | 0x5C | ShootingMvTelecon (0x7EEEAE98) | 9 | 501 |
| 0x54 | ShootingLvGuide | 1 | 65 | 0x60 | Pc (0x7EEDAD70) | 13 | 138 |

- **Six "common" row tables** apply in any state of a sub-app. The count is loaded by the class's command function.

  | Sub-app | Table | Rows | Loaded by |
  |---|---|---|---|
  | Boot | 0x7EED8D4C | 18 | 0x7ECDF7A1 |
  | Misc | 0x7EED92DC | 17 | 0x7ECE0056 |
  | Pc | 0x7EEDA340 | 25 | 0x7ECE07DE |
  | Play | 0x7EEDB0C0 | 34 | 0x7ECE1370 |
  | PlayHdmi | 0x7EEDBB08 | 31 | 0x7ECE1B03 |
  | all Shooting* | 0x7EEEAF04 | 65 | 0x7ECE2341, ShootingCommon class vt 0x7EEEB740 |

- Totals: 4,177 state rows + 190 common rows; 489 handler functions (2,425 rows with a handler).
- TSV rows `CA Sub[states]/0xEVENT` (2,336): one per (sub-app, event, handler, next, code), states grouped.

### 2.3 Other tables used
- **Vtables:** 574 function-pointer runs referenced by code immediates. 442 of them are stored by a ctor (`mov VT,dN ; mov dN,(aX)`). A run is cut at the next stored vtable.
  - Slot role = the dictionary of the class that introduces the slot (root, container, screen, widget, panel base, page grand-base / base / list page); ctor chains come from the ctor's first call.
  - Class names come from the factory types (0x7EF0F3B0), the 15a panel/page rows, `X::` strings in own slots, `command X`, or the string before the vtable.
- **Function tables without a ctor:** jump tables (the referencing function has `jmp (aN)` and the targets have no callers) give "switch case k". `{key, case}` hash switches (e.g. 0x7EED5254 in 0x7ECD7A61) give "case block (key k)". Other runs give "function table entry k".
- **Others:** C++ ctor table 0x7F033AC8 (33 static initialisers; their `{-1, fn}` member records give "member fn: pmf record RAM X"); openPage cases and the list registry 0x7EFE180C; the Actuator/Viewer registry 0x7EFC5408; the 15a touch-action rows; ptrs.tsv data words.
- **OlyApi** (44 getters, 13d §6.2): ctor → vtable → each slot's `0xGGCCMM` constant → MM-th `Class::method` string. The method names are **I** (name-order rule; see §4.3).

## 3. Rules (first match gives the primary role; effects and returns are appended)
1. **ss / ss-entry / ss-merged:** a Ss handler, entry or exit (§2.1).
2. **ca / ca-merged:** a CA row handler (§2.2). The handler's own name is added when its first string is a unique identifier (CA functions log their own name through 0x7ECE631E).
3. **ctortab / jtab / hsw:** a static initialiser; a switch case block split off by fwmap.
4. **doc:** a function named in 13d/14e/15a/10f or read here (`known.py` ROLEDESC, 124 entries).
5. **touch:** a 15a touch-action row.
6. **vt:** `<class> vt slot k (+4k) = <slot role>`, with "shared by n vtables".
   - Root slots added here (V, from the OnMessage case table 0x7EEF5228): msg 1 → +228 then **+396 (slot 99)**; msg 2 → **+216 (54)**; 0x1006 GM_USER → +232 (58); 0x1103 GM_DELETECHILD → **+240 (60)**; 0x1300/0x1301/0x1302 → **+324/+328/+332 (81–83)**; 0x1901/0x1902 GM_DB_* → **+400 (100) OnDBUpdate**.
   - Panel slots: 91 = post-create init (114 of 116 override it; it binds the resource table through 0x7ED16C72 and fetches children); 129 = getChild(i) (bounds-checked +792 array; V).
   - Actuator/Viewer-type objects (ctor calls 0x7ED8BBA6): slot 0 = Update (I).
7. **openpage / listreg / actreg / 15a:** page getters, list factories, registry creators, 15a fn rows.
8. **ctor:** stores vtable V (ctor or dtor of the class).
9. **str:** `named X` (the first `Class::method`, `doCmd_*` or unique identifier string, skipping OlyApi names) or `logs '…'`.
10. **shape** (from reachable code only):

    | Shape | Bytes / instructions |
    |---|---|
    | field getter / setter | `mov(hu) (N,a0),d0 ; retf` / `mov d0,(N,a0) ; retf` |
    | RAM getter / setter | `mov (60xxxxxx),d0 ; retf` / store to 0x60xxxxxx |
    | constant return | `mov N,d0 ; retf`, `clr d0 ; retf` |
    | thunk | `jmp X` |
    | this-adjust thunk | `mov (N,a0),a0 ; jmp X` |
    | getInstance | `fc a0 RAM ; cmp 0,a0 ; bne ; mov SIZE,d0 ; call 0x7EBA62DB ; call ctor ; store` |
    | creator | `new SIZE ; ctor ; ret` |
    | short wrapper | ≤ 12 insns, 1–2 calls (log calls ignored) |
    | OlyApi wrapper | `call getter ; mov (a0),a1 ; mov (NN,a1),a1 ; calls (a1)`, ≤ 40 insns |

11. **pmf / imm / dataw:** a pointer-to-member target; address taken by code; listed in a data table.
12. **range / ctrl-range:** a private method of the panel, page class or controller class whose code range contains it, with its caller's role.
13. **caller:** `helper of 0xC (<C's role>)`; chains of helpers are followed to the first non-helper (3 passes).
- **fwmap notes:** "fwmap merged n unreachable stub(s) after its return" marks code after an unconditional return that no branch reaches (DB merges; 14e §5 D). It is not applied to functions with an indirect `jmp (aN)`.

## 4. Coverage, error rate, corrections

### 4.1 Coverage (measured on the final TSV)
- 11,586 function rows (all non-data, non-suspect functions in the range); **0 blank**.
- Primary rule counts:

  | Rule | Rows | Rule | Rows |
  |---|---|---|---|
  | vt | 3,121 | ca | 489 |
  | shape | 1,406 | ctor | 433 |
  | caller | 1,334 | pmf | 298 |
  | range | 1,167 | ss-entry | 284 |
  | ss | 1,158 | ctrl-range | 257 |
  | str | 773 | other | 866 |

- **Specific** (table, vtable, string, shape or documented): **74 %**. **Weak** (caller / range / data-word / address-taken only): 26 %.
- Weak share by area: pools 64 %, renderers/DC/geometry 58 %, panels 47 %, GE/GPI 47 %, controllers 38 %, guiUtility 36 %, page framework 34 %, toolkit core 22 %, pages 21 %, GuiTouch 17 %, IGui 15 %, CA_MAIN 11 %, Ss areas 2–3 %.
- V 8,820 / I 2,766.
- Weak rows still give the class, the caller's role and the verified effects (`does:`).

### 4.2 Measured error rate (30 random function rows per sample, read in the disassembly; error = any false claim)
| Sample | Rule set | Errors | Errors found (all fixed) |
|---|---|---|---|
| dev 1+2 (30) | early | 3 | a vtable treated as a jump table; vtables cut at every immediate (0x7F0032B8); unnumbered panel classes put in panel 55 |
| A (seed 4242) | after dev fixes | 4/30 = 13 % | wrong own name (OlyApi log taken as name, 0x7ED00250); "returns 0" for a 0/1 register; wrong result source for an Ss handler; a trace-log call shown as "short wrapper" |
| B (seed 777) | after A fixes | 1/30 = 3.3 % | 0x7EDC3BCC printf argument wrongly described |
| C (seed 2026) | final, before 2 small fixes | 1/30 = 3.3 % | a call argument counted as a stored state constant (0x7EDB5A18) |

- Found while checking Ss actions (spot check): following every Ss callee added constants that are not returned (0x7EDA968C). The fix is to follow only callees whose result is returned (§2.1), and it was re-checked on 6 handlers.
- **Final measured rate: 1/30 (3.3 %) on sample C.** Its error is fixed, but no new sample was drawn after that fix.
- About a quarter of all rows are weak (correct but generic).

### 4.3 Corrections
1. **15a panel rows:** the row "panel 55 GCPnl_Zoom 0x7ED7932E–0x7ED7F6D4" also holds the 16 unnumbered panel classes. GCPnl_Zoom is 0x7ED7932E–0x7ED7A79E. The unnumbered classes (type: ctor) are 0x605B: 0x7ED7A79F, 0x605D: 0x7ED7B07A, 0x6062: 0x7ED7B250, 0x6008: 0x7ED7B4B3, 0x6060: 0x7ED7B8CC, 0x605E: 0x7ED7BBEB, 0x605C: 0x7ED7BE74, 0x6003: 0x7ED7C0C5, 0x6007: 0x7ED7C5B7, 0x601E: 0x7ED7C93E, 0x6033: 0x7ED7E21A, 0x6070: 0x7ED7E533, 0x605F: 0x7ED7E77B, 0x6061: 0x7ED7E98D, 0x6001: 0x7ED7ED04 and 0x6071: 0x7ED7F445 (factory table 0x7EF0F3B0). The end of the last one is 0x7ED7F6D4.
2. **14e §4.3:** the RAW-edit page vtable is **0x7F0032C0** (ctor 0x7EDF779C, base userCommonWizard1NRightAligned 0x7EDED9DD). 0x7F0032B8 is a separate 2-slot object (ctor 0x7EDF6295, base ctor 0x7ED8BBA6; slot 0 0x7EDF6447 writes DM blocks 37/29/30).
3. **15a page-class rows:** `end` is exclusive (the next class's ctor). For example, 0x7EDC8AD0 is the list-base ctor, not part of the pages-639 class.
4. **13d §1 CA_MAIN:** add the CA table catalogue (§2.2), the six common tables and the handler span 0x7ECD257F–0x7ECE39B9. The appCaller object is at 0x7ECE39D2/0x7ECE3A0A, below the "~0x7ECE4000" bound.
5. **13d §1 controller row:** add CPlayCalendar, CPlayLightBox, **CPlayMovie** (review C5 weakest 1), the play-start chooser and the 92-B singleton, with the RAM slots of §1.
6. **13d §2.3 / 14e §2.1:** add root slots 54, 58, 60, 81–83, 91, 99 and 100 (rule 6), and panel slot 129.
7. **New helpers** (V):
   - 0x7ECE631E: CA trace print, 447 callers; the module word is at a0 and the text in a1; it is gated by 0x7ECE6408;
   - 0x7EDC3BCC: GUI printf; the format is the first stack argument; it prints when RAM 0x602BC60C ≥ 2 (0x7EDC3A50 prints at ≥ 1);
   - 0x7ED16C72: per-panel resource initialiser, table 0x7EF04808;
   - 0x7ED8BC18: `{key, value}` table search.
8. **13d §4.1 tool note:** 203 (not 213) Ss handler entry points are not function starts in the current map.

## 5. Open questions
1. 283 Ss handlers return a value that the rules do not resolve (stack or second-register paths). Their TSV row lists the calls involved.
2. **OlyApi names are I.** For MediaCtrl the name-order rule gives vt+40 = 0x10C11 transferImageAll and vt+44 = 0x10C12 **cancelTransferImageAll**. But pages 511/513 call vt+44 with (2, 4, callback), which fits transferImageAll (15a §2.2). Either 15a or the name order is off by one for this class.
3. About 600 own vtable slots (widgets, screen, draw-object family, page own slots) have no role beyond their effects. The draw-object family 0x7EF10EA4 and the image table 0x7EFB13BC (round-4 weakest 1) need a slot dictionary.
4. CA state names: only sub-app and event names exist (no per-state name table was found). The meaning of "GUI code" values 0x84/0x85 in Misc rows (no GUI event in 0x7EEF3434) is open.
5. The GE/GPI layer, the renderers and the pools are still 47–64 % weak (no strings; callers only).

## Known rule errors found by coverage round C6 (2026-11-09)

Rows fixed in the TSV: 0x7EE01FF5, 0x7ED16C72 and 0x7ECEF6A6.
- **The `hsw` hash-switch rule:** it labelled a whole function (own prologue, called through `calls (a0)`) as a case block. Its table 0x7F01170C is a linear {key, fn} table. Treat other `hsw` rows marked V as unconfirmed until rerun.
- **The OlyApi "slot vt+N = (N/4+1)-th name" order rule:** it fails for CustomPrint (vt+60 is canPrint, vt+84 is getPrintCount). Read the API id inside the slot target instead. The MediaCtrl vt+44 doubt (transferImageAll vs cancelTransferImageAll) has the same cause.
- **Rows that are context only:** "private method" and "helper of X" rows for panel and page code give context, not a role.
- **Undescribed structures:** the GUI draw-object family (factory 0x7ED1AFF9, types 0x2000–0x2012; e.g. 0x200C is an animated blur effect) and the GUI trace ring buffer (120 × 16 B) have no descriptions.
