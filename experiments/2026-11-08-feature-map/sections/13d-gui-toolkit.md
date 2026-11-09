# 13d. GUI toolkit, panels, state handlers, Custom Menu tables (E-PM2 v1.6, round D1)

Scope: how the C++ GUI in 0x7ECA–0x7EE0 is built. The topics are the widget framework, the panel classes, the object registries, the generated `Ss*` state handlers, the Custom Menu tables and the OlyApi interfaces.

- **Labels:** **verified** = read in code or bytes; **inferred** = from names, order or layout.
- **Addresses:** runtime addresses.
- **Earlier detail:** settings and menus are in section 07, light box / 3D / BGM in 10d, and the debug menu in 10f.
- **Scratch:** scripts and dumps are in `$S/d1/gui-toolkit/`: `cases.txt` (factory), `vt.txt` (classes), `panelno.txt`, `panels.txt`, `olyapi.txt`, `custmenu/`, `ss/`.

## 1. Area and boundaries

| Range | Contents | Basis |
|---|---|---|
| 0x7ECA1020–0x7ECCB7FF | Mostly data: ramp/LUT tables up to ~0x7ECB083B (the ramps start before 0x7ECA1020, from at least 0x7EC9F000; 13b gives the OKAO Smart Skin LUTs as 0x7EC92318–0x7ECAFF3C, which covers most of them) (A5 2026-11-09); the Smart Skin LUTs run to 0x7ECB083B and cover all of them (14d §3.5) (D2 2026-11-09); then **19 ascending code pointers 0x7ECB083C–0x7ECB0887** to 0-caller functions that construct globals (e.g. 0x7E969F02 → mutex 0x605E1638; inferred: the C++ static-constructor table) (A5 2026-11-09); verified: it is the segment-2 constructor table, 76 bytes, walked by 0x7E44B6B0(2) (14d §1) (D2 2026-11-09); then 0xFF fill 0x7ECB0888–0x7ECB0FFF; then `de 00 00` (a `retf`) at 0x7ECB1000 and **108,541 bytes of 0xFF erased fill** (0x7ECB1003–0x7ECCB7FF), which is padding, not a table. The DB's "function" 0x7ECAD443 (15 KB; it calls itself, 0x7ECAD43E and two targets outside the image) is probably data (A5 2026-11-09) | verified bytes; the role of the ramp data is inferred (A4 2026-11-09) |
| 0x7ECCB800–~0x7ECE4000 (a round bound: `setCameraAppData` 0x7ECE3DCD crosses it (L1 2026-11-09)) | CA_MAIN "camera app" (code restarts at 0x7ECCB800; **0x7ECCB800 is the first GUI function** `[OSD_CONTROL]`, the start of segment-3 code, 14d §1 (D2 2026-11-09)): OSD_CONTROL/OSDDRAW (0x7ECCBA45…), `*SubAppMdl*` modules, `*SubAppState*` states (ShootingFuncDirect, ModeDirect, Misc) | verified strings (A4 2026-11-09) |
| ~0x7ECE4000–0x7ECEC798 (L1 2026-11-09) | GUI↔CA bridge `GuiCallerImp::sendEvent` (0x7ECE6E27); "Genifa" GE event layer (message build 0x7ECE7597, post 0x7ECE75C3, task GPI_TIM_TASK); GPI display layer (`GPISetPalette`, `cw_updateDisplay`, `GPISetOsdOrder`), including 0x7ECEBE26 (962 B) and 0x7ECEC1E8 (1,457 B), which call the GPI functions 0x7ECEA7ED…0x7ECEAD0A | verified strings and code (A4 2026-11-09) |
| 0x7ECEC799–0x7ECEE1D5 | GUI memory pools (from 0x7ECEC799; alloc 0x7ECEC905, free 0x7ECEC9CB, pool lookup 0x7ECEC854, 20-byte header); UTF-16 helpers (`wcscpy` 0x7ECED793, `wcslen` 0x7ECED7BB, compare 0x7ECED75C); CTouchPnl (0x7ECEDE30). The GUI data-model get/set 0x7ECEF64F/0x7ECEF667 (section 07) sits just after the root class | verified code (A4 2026-11-09) |
| **0x7ECEE1D5–~~0x7ED00000~~ 0x7ECFF982** (CCommon starts at 0x7ECFF983, next row (L1 2026-11-09)) | **Widget framework core:** the root object, container, screen and widget base classes, and the drawing engine (**0x7ECF6BDB–0x7ECFEF32**), then geometry/resource helpers to 0x7ECFF982 (14e §1) (D2 2026-11-09) | verified (§2) |
| ~~0x7ED00000~~ 0x7ECFF983 (D2 2026-11-09)–~0x7ED17000 (L1 2026-11-09) | GUI-side controller classes `CCommon` (from its ctor **0x7ECFF983**, not 0x7ED00000; getInstance 0x7ECFFAC6 has 775 callers; 14e §1 (D2 2026-11-09)), `CGuiDrawCtrl`, `CPlayIndex`, `CPlaySingleFrame`, `CRec`, `CPlayZoom`. They wrap the OlyApi interfaces (`OlyApiPlay*`, `OlyApiShooting` strings) | verified strings |
| **~0x7ED17000–~~0x7ED37DAA~~ 0x7ED37DA9** (0x7ED37DAA is the first panel class, 15a §1; 0x7ED16FE7 crosses 0x7ED17000 (L1 2026-11-09)) | **Object factory** 0x7ED17DB8, panel creation by number 0x7ED19D3F, top window (WinMain class) 0x7ED1B48C…, the widget classes 0x80xx/0xC0xx/0xD0xx and their drawing parts (~0x7ED2F000–~~0x7ED37DAA~~ 0x7ED37DA9 (L1 2026-11-09)) | verified |
| **0x7ED37DAA–~0x7ED82025** | **114 panel classes** (`GCPnl_*`, type ids 0x6000–0x6071), one per screen layout | verified |
| ~0x7ED82200–~~0x7ED82820~~ 0x7ED8281F (the next row starts at 0x7ED82820 (L1 2026-11-09)) | Statechart engine: default handlers 0x7ED82276, init 0x7ED82282, dispatch 0x7ED822FE, evmap 0x7ED8243C; WinMain 0x7ED8249F (`WinMain called` / `messageloop start`, "Start Gui Task") | verified |
| 0x7ED82820–0x7ED86DA5 | `Ss*` handlers of SS_BTRECEIVE, SS_BTSEND, SS_COMMON (§4). The last handler 0x7ED86DA0 (`mov 516,d0; retf`) ends at 0x7ED86DA5; the DB merges it into 0x7ED86D73 (A5 2026-11-09) | verified |
| 0x7ED86DA6–0x7EDA0410 (A5 2026-11-09) | Live-view controller `IGui_Controler` (0x7ED87077, 0x7ED87397); Actuator/Viewer objects of the registry 0x7EFC5408 (`Func_Scp_Actuator`, `Input_String_Actuator`, `Rec_View_Viewer`) | verified strings |
| 0x7EDA0410–0x7EDC15B0 | `Ss*` handlers of DEBUGMENU, DPS, MENU_LV, MENU_MAIN, SS12, PLAY_INDEX, PLAY_MOVIE_SLIDE, PLAY_SINGLE, REC, SELFADJ, SPC, USB, in that order (`doCmd_<Ss>_<St>_<Evt>`; FuncMenu strings at 0x7EDA4…) | verified (fork ranges) |
| 0x7EDC15B0–~~about 0x7EDE0000~~ ~~~0x7EDE161C~~ (C3 2026-11-09) 0x7EDE15ED (L1 2026-11-09) | Actuator objects (0x7EDC15E0…), guiUtility (ShowPanelEx 0x7EDC5D2D, PostEventToCA 0x7EDC5C47, self-post 0x7EDC5BF5), guiEventFilter, widget helpers 0x7EDC17FB–, BT wizard, DPS GUI helpers 0x7EDCE9B9–≥0x7EDD08D2 (the last one, moveCurrent 0x7EDD07F9, is 218 B), ~~the self-adjust UI 0x7EDD8–0x7EDDF~~ the focal-length entry page 0x7EDDAF6A–0x7EDDB050 (`Init/Increase/DecreaseFocalLength`), the **"return-to (SS, state)" singleton 0x7EDDBC06–0x7EDDBD4F** (§6.3) (L1 2026-11-09), the language-resource loader 0x7EDDBD50, the self-adjust UI **0x7EDDBF31–0x7EDDD1E5** (only these use the `[GUI-SelfAdjust]`/`userGuiSelfAdjust::` strings; its page object is page 523, class 0x7EDDB051–0x7EDDBBEB (D3 2026-11-09)), then **GuiTouch ~~~0x7EDDD21D–~0x7EDE161C~~ 0x7EDDD21D–~~0x7EDE161C~~ 0x7EDE15ED** (D3 2026-11-09; end (L1 2026-11-09)): touch-action handlers (~~table 0x7EFED8F4~~ the live panel-26 table is **0x7EFE4058**, reached through the panel-26 descriptor (`.data` word 0x7E8ED184); 0x7EFED8F4 is an identical copy of its 13 slots with no pointer to it found (D3 2026-11-09); 13 entries 0x7EDE12C5, 0x7EDDDE22…0x7EDDE967; e.g. 0x7EDDDF93 posts EVT_LVBAR_CHG_VALUE 0x9ACB), `checkSlideAreaPos` 0x7EDE13B4 (35 callers 0x7EDDD22C–0x7EDE033E), last helpers 0x7EDE15A3–~~0x7EDE15EE~~ 0x7EDE15ED (C3 2026-11-09; the last helper is 0x7EDE15DA, 20 B; 0x7EDE15EE is the getInstance of the USB-connect screen (L1 2026-11-09)). **15a §1 (D3 2026-11-09)** gives a finer table for 0x7EDC7DBA–0x7EE02094: menu-page classes start at 0x7EDC7EAA and are interleaved with the components above (getListPage 0x7EDC7DBA, BT wizard screens 0x7EDC9D1C–0x7EDCB01B, the openPage functor 0x7EDCBE97–0x7EDCCA5C, the menu-page framework 0x7EDCCA5D–0x7EDCDAF0, …) | verified strings |
| ~~~0x7EDE161D~~ 0x7EDE15EE–0x7EE01FF5 (start moved from about 0x7EDE0000: GuiTouch comes first; `userGuiUsbConnectCallBack` 0x7EDE1D0A follows it) (C3 2026-11-09) | **USB-connect screen 0x7EDE15EE–0x7EDE1DD8 first (L1 2026-11-09):** getInstance 0x7EDE15EE (RAM 0x602BDF48, 172 B), ctor 0x7EDE161D (page base 0x7EDCD621, vtable 0x7EFEF47C), show 0x7EDE1649 (panels 82/103), callback `userGuiUsbConnectCallBack` 0x7EDE1D0A; its 14 callers are all SS_USB handlers 0x7EDC0D90–0x7EDC156F (§4.4), not openPage (15a page-class row). Then: **Not the only page code (D3 2026-11-09):** page classes run from 0x7EDC7EAA (userCommonSecondWizard), interleaved with the components of the row above; this row holds 179 of them (15a §1, §2.2). Menu pages: the generic list pages, the Custom Menu panel (0x7EDE9AA6…, §5), the `userMenu*` special pages, and the setting wrappers 0x7EE01D38 / 0x7EE01D4E | verified |
| **0x7EE02095–~0x7EE294B4** (C2 2026-11-09) | **Not GUI.** This is a DMP ("Digital Media Professionals, Inc." 0x7EE0877E) OpenGL-ES-style 3D library: `gl_ModelViewMatrix`, and shader-object tags `DVOJ`/`DVPE`. Its only callers are ~~C3D (0x7EE2–0x7EE3)~~ the 3D engine's GL back end 0x7EE2FF5E–0x7EE32698 (14a §5 item 4) (D2 2026-11-09) and the overlay C3D bridges (0x7F09/0x7F0A); no call comes from 0x7ECA–0x7EE01. **It runs to ~0x7EE294B4, not 0x7EE21020** (C2 2026-11-09): the `{name, fn}` table ~~0x7F023C74~~ **0x7F023B8C**–0x7F024283 (223 slots: 29 `egl*` first, then 194 `gl*` with `glDeleteQueriesDMP` twice, so 193 unique `gl*` names; 14a §5 item 3 (D2 2026-11-09)) has 89 entries at or above 0x7EE21020, up to glPointSize 0x7EE29468; the last GL function 0x7EE2946D ends at 0x7EE294B4, and an `MCM_/MCA_/MCT_` module starts at 0x7EE294B5. The outside callers are in 0x7EE2F000–0x7EE32xxx (after the library) and 0x7F09E/0x7F0A3 (C2 2026-11-09) | verified call edges; that it is the GPU driver of C3D is inferred |

Rodata: the GUI tables and vtables run from 0x7EEF5000 to ~0x7F01xxxx. **A class's strings come just before its vtable** (verified for the 11 named panels, §3).

## 2. Widget framework (a Win32-like toolkit)

### 2.1 Message model (verified)
- **Message names.** The table at **0x7EFDFDA8** holds `{u32 id, char* name}` pairs and ends at 0x7EFDFF78. It names the `GM_*` messages:
  - 0x1000 CREATE, 0x1001 DELETE, 0x1002 PAINT, 0x1003 ONDRAW, 0x1006 USER, 0x1007/8 SET/KILLFOCUS;
  - 0x100B–0x1010 SET/GETVISIBLE, ENABLE, CONSUMABLE; 0x1011 ADDREFRESHRECT; 0x1014 GETCLIENTRECT;
  - 0x1100 SHOWPANEL, 0x1101 SETSTATUS, 0x1102–0x1105 ADD/DELETECHILD…, 0x1106 CREATEINSTANCE, 0x1107 CREATECHILDREN, 0x1109 ATTACHPANEL, 0x110A DRAWBACKGROUND;
  - 0x1800–0x1813 CB_ON* callbacks (PRESS, RELEASE, CLICK, KEYPRESS, TIMER, SELECTCHANGE, SCROLLFINISH, NEXTFRAME, CHANGEPAGE …);
  - 0x1900–0x1902 DB_* (data-model update).
- **Message object.** 0x7ECE7597 (373 callers) builds a 32-byte message: `d0 = id`, −2, `a0 = target`, `d1 = param`, `a1 = data`. 0x7ECE75C3 (251 callers) posts it to the GE queue. That function drops GM_PAINT while the flag 0x605F569C = 1.
- **The app is "WinMain"-style.** 0x7ED8249F logs `WinMain called` and then `WinMain messageloop start`.
- **ShowPanelEx is a message.** ShowPanelEx 0x7EDC5D2D posts GM_SHOWPANEL (`mov 4352,d0` at 0x7EDC5DE8).

### 2.2 Class hierarchy and type ids (verified from constructors)
Every object stores its **vtable at +0** and a **u16 type id at +4**.

| Type id | Class (role) | Ctor | Vtable | Base |
|---|---|---|---|---|
| 0x0001 | root object (68 B) | 0x7ECEE1D5 | 0x7EEF5328 (104 slots) | — |
| 0x0100 | container / window | 0x7ECF3083 | 0x7EEF5AE0 | root |
| 0x0101 | top-level screen ("desktop") | 0x7ECEFED5 | 0x7EEF5520 | root |
| 0x0101 | **application window**, created in WinMain. Its ctor chain is 0x7ED24DD0 → 0x7ECEFED5 and 0x7ED230C2. Slot +148 = ChangePanel 0x7ED1B4FF. **Inferred:** it is the object at RAM 0x602B6200 (getter 0x7ED17DA1, 565 callers), which CreatePanel uses as parent | 0x7ED1B48C | 0x7EF1017C | screen |
| 0x0102 | sub-screen | 0x7ECF2CBA | 0x7EEF5880 | container |
| 0x0103 / 0x0105 | 0x0105 is a 784 B factory class derived from 0x0103 | 0x7ED171FF / 0x7ED16F18 | 0x7EF04570 / 0x7EF04328 | sub-screen |
| 0x0104 | 88 B object | 0x7ECF5ECF | 0x7EEF6338 | root |
| — | panel base (no own type) | 0x7ED23C27 (115 callers) | 0x7EF11778 | container |
| 0x6000–0x6071 | `GCPnl_*` panels (§3) | 0x7ED37DAA… | 0x7EF1544C–0x7EFA0278 | panel base |
| 0x8000 | widget base | 0x7ECF4C68 | 0x7EEF5D18 (143 slots) | root |
| 0x8001–0x8013 | 15 widget classes (§2.4); 0x8009 is an abstract base | | 0x7EF104A8–0x7EF14A00 | widget base |
| 0xC000 / 0xC001–C005 | drawable part, family C | 0x7ECF563A | 0x7EEF6110 | root |
| 0xD000 / 0xD001–D003 | drawable part, family D | 0x7ECF5451 | 0x7EEF5F54 | root |

- The two parent types the panel builders test are **257/258** (screen / sub-screen). No static writer of the factors 0x602B6204–0x602B620A exists (14e §2.8) (D2 2026-11-09). For those parents the builders scale only the **origin** (x1, y1) of each child rect by 4.12 fixed-point factors at 0x602B6204/6206 and add offsets at 0x602B6208/620A; width and height are kept (x2 = x1′ + w − 1, y2 = y1′ + h − 1; two multiplies per builder, all 61 builders) (verified, e.g. 0x7ED37EA5–0x7ED37EE7 inside fn 0x7ED37E2D) (A5 2026-11-09). **Inferred:** this relocates child positions (for HDMI/EVF output); it is not a full rescale (A5 2026-11-09).
- **Geometry (verified):** a rect is `{s16 x1, y1, x2, y2}`, inclusive (x2 = x1 + w − 1 in the builders). Point set 0x7ECFF349; rect from coordinates (normalised) 0x7ECFF899; copy 0x7ECFF422; equal 0x7ECFF431; offset rect/point 0x7ECFF561/0x7ECFF266; overlap test 0x7ECFF6A6 (133 callers).
- **Pools (verified):** GUI pool alloc/free 0x7ECFF1D8/0x7ECFF1E4 (→ 0x7ECEC905/0x7ECEC9CB) take two pool bytes. Root-family objects keep them at +28/+29 (slot +244 sets, +248 reads), but of the 205 call sites only about 24 load +28/+29 directly and about 13 use slot-248 results; the rest pass constants ((1,0) ×57, (5,0) ×21, (8,0) ×10) or bytes +17/+18 of another structure (×36). (A4 2026-11-09)

### 2.3 Root vtable 0x7EEF5328: slot map (verified unless marked)
Object fields: +4 type, +6 id, +8/+10 x/y, +12/+14 w/h, +16 status bits, +20 parent, +24 handler/owner, +28/+29 pool, +30 layer, +40 mask, +44, +48 (8 B).

| Slots (+offset) | Role |
|---|---|
| 0 (+0) | ~~returns a constant (class info)~~ **destructor**: it returns the GUI-pool deleter 0x7ECEEFC3 in a0 (`fc dc c3 ef ce 7e`, 0x7ECEE21F), which the caller then calls (14e §2.1) (D2 2026-11-09) |
| 1–4 (+4…+16) | get type (+4), id (+6), x (+8), y (+10) |
| 5–10 | position and size getters (+8…+14), as a point via 0x7ECFF349 |
| 14–16 | rect getters (via 0x7ECFF899) |
| 19/20 (+76/+80) | setVisible / isVisible (status bit 1) |
| 21/22 (+84/+88) | setEnable / isEnable (bit 2) |
| 23–28 (+92…+112) | bits 4, 8, 16. The bit-8 and bit-16 setters invalidate. **Inferred:** CONSUMABLE / focus-like. Bit 16 **is** focus: OnSetFocus/OnKillFocus (+220/+224) set or clear it on the object and every ancestor (14e §2.1) (D2 2026-11-09) |
| 29/30 (+116/+120) | setStatusBits(mask, on) / testStatus(mask) on +16 |
| 31/32 (+124/+128) | setParent / getParent (+20; getParent 0x7ECEEA74 has 86 callers) |
| 33/34 (+132/+136) | set/get +24 (handler) |
| 39 (+156) | OnPaint: asks the manager (vt+680), then calls **+160 = OnDraw** |
| 42 (+168) | invalidate(rect a1, d0) |
| 61/62 (+244/+248) | set/get pool bytes |
| 64–67 (+256…+268) | status bits 0x2000 and 0x1000 |
| 102 (+408) | **OnMessage(d0 = id, d1, a1)**. Hashes the id (`id & 31`) into the 32 × `{id, case}` table at 0x7EEF5228. Cases: 0x100/0x101/0x102 (point events → +172 / +384→+184 / +388→+196), 0x200/0x201 (→ +372→+208 / +376→+212), 1, 2, 0x1002 PAINT (→ +392→+156), 0x1006 USER, 0x1103, 0x1300–0x1302, 0x1901/0x1902. **Inferred:** 0x100–0x102 are touch press/release/move and 0x200/0x201 are key press/release. **Corrected (D2 2026-11-09):** the order is 0x100 move, 0x101 press, 0x102 release (the widget handlers post CB_ONMOUSEMOVE/ONPRESS/ONRELEASE, then CB_ONCLICK; 14e §2.2). +140/+144 are import/export properties and +252 selects one of 4 layouts (14e §2.1) |
| 103 (+412) | returns −1 for message 6399. It is **OnNotify**, the per-class notification map (empty map: sentinel 0x18FF, always −1; 6 classes have real maps) (14e §2.1, §5 shape E) (D2 2026-11-09) |

**Signature of a toolkit method (verified pattern):**
- Getters are 2–3 instructions: `movhu (N,a0),d0 ; [exth d0] ; retf`.
- Setters compare first: `call vt+get ; cmp ; beq out ; call vt+116 (set bit) ; mov 0,a1 ; mov 1,d0 ; call vt+168 (invalidate)`.
- **DB caveat:** many 2–6-byte getters sit right after another method and are vtable targets. fwmap merges them into the previous function, for example the slot-18 target 0x7ECEE75A inside 0x7ECEE72F.

### 2.4 Factory and widget classes (verified)
**Factory `Create(d0 = type, d1 = parent, a1 = resource)` 0x7ED17DB8 (8 KB, 132 callers) → a0 = object or NULL.**
1. It asks the parent for its pool bytes (vt+248).
2. It looks the type up in the 256-entry hash table **0x7EF0F3B0** (`{u32 id, u32 case}`, index `id & 0xFF`, linear probe).
3. The case runs `mov SIZE,d0 ; call 0x7ECEEF9A` (operator new from the GUI pool), then the class ctor, then `0x7ECEEF80` (store pool), then the class's create/import routine with a1. For example, panels use 0x7ECF31EB and C parts use 0x7ECF575F.

There are 140 type ids: 1, 0x104, 0x105, 0x6000–0x6071, 0x8001–0x8008, 0x800A, 0x800E–0x8013, 0xC001–C005 and 0xD001–D003.

| Type | Size | Ctor → vtable | What is known |
|---|---|---|---|
| 0x8001 | 128 | 0x7ED1C4C1 → 0x7EF104A8 | overrides 15 base slots (+0, +148…+232, +408, +412); its OnDraw 0x7ED1C533 is a 13-byte wrapper of the base |
| 0x8002 | 260 | 0x7ED1C5ED → 0x7EF106E4 (175 slots) | slot 161 = C1 F063: setter of a 24-byte style/property at +196 that redraws on change; its getter tail is 0x7ED1CA54 |
| 0x8003 | 300 | 0x7ED290AD → 0x7EF12830 | **item list / selector:** +131 count, +132 current index, +140 u16 item values, +172 item pointers. Methods: count 0x7ED29244, index get/set 0x7ED29AAC / 0x7ED29A6F, item value get/set 0x7ED29F00 / 0x7ED29ECA, set item 0x7ED29CCB |
| 0x8004 | 156 | 0x7ED26E84 → 0x7EF12034 | — |
| 0x8005 | 204 | 0x7ED2D7BD → 0x7EF146F4 | base of 0x8011 |
| 0x8006 | 384 | 0x7ED27484 → 0x7EF122CC | embeds a part (ctor 0x7ED2D740, vt 0x7EF1459C) and a 0x800E |
| 0x8007 / 0x8008 / 0x800A | 184 / 180 / 176 | 0x7ED1E868 / 0x7ED2A3C8 / 0x7ED29F1E | — |
| 0x800E | 180 | 0x7ED2B700 → 0x7EF133E8 | derived from 0x8009 (ctor 0x7ED2B12A, vt 0x7EF13184), which the factory never creates |
| 0x800F | 228 | 0x7ED2538F → 0x7EF11D1C | — |
| 0x8010 | 176 | 0x7ED2CD1A → 0x7EF14308 | **text label:** +130 string id (set 0x7ED2CE0C), +132 text style (set 0x7ED2CE6A), +156/+160 UTF-16 buffer and length. setText(wchar*) is 0x7ED2D510 (257 callers); C1 F064 is its buffer setter (vt word 0x7EF1456C) |
| 0x8011 | 216 | 0x7ED2F97A → 0x7EF14A00 | derived from 0x8005 |
| 0x8012 / 0x8013 | 188 / 152 | 0x7ED1DB7B / 0x7ED28829 | 0x8013: u16 property +128 (set 0x7ED28CDD → re-layout → redraw) |
| 0xC001–C005 | 88–104 | 0x7ED2CB68, 0x7ED2C7D2, 0x7ED2C880, 0x7ED2C9D4, 0x7ED2CC18 | **these draw.** Their OnDraw (+160) calls renderers 0x7ECFB5F9, 0x7ED319B4, 0x7ED34FE9, 0x7ED35160, 0x7ED3534D |
| 0xD001–D003 | 80–92 | 0x7ED2C31C, 0x7ED2C605, 0x7ED2AFD8 | draw through 0x7ECFE523/0x7ECFE796 or 0x7ED303F9 |

- ~~14 of the 15 0x80xx widgets keep the empty base OnDraw 0x7ECF4DA2 (verified). **Inferred:** they are controls that own C/D drawable parts, and the pixels come from the parts.~~ **Corrected (D2 2026-11-09):** the base OnDraw 0x7ECF4DA2 is not empty. Unless status bit 0x20 is set, it calls **DrawSelf (+568)**, then posts CB_ONDRAW 0x1802. 14 of the 15 widgets (all except 0x8001, which keeps the empty DrawSelf 0x7ECF5442) override DrawSelf with DC drawing (V: vtable slot +568 of each class) (14e §2.2–2.3).
- **Drawing engine (verified call graph):** about 0x7ECF5000–0x7ECFF000 (exactly: renderers 0x7ECF6BDB–0x7ECFE7B7 and the DC / pixel-format layer 0x7ECFE7B8–0x7ECFEF32; 14e §1, §3 (D2 2026-11-09)) and 0x7ED2F000–~~0x7ED37DAA~~ 0x7ED37DA9 (L1 2026-11-09) (both are round bounds: 0x7ECFEF32 crosses 0x7ECFF000 and 0x7ED2EF75 crosses 0x7ED2F000). Outside the GUI it calls memcpy 0x7E500D33 and memset 0x7E500D73, and one ~~rotation routine~~ slope/cotangent helper for slanted fills (14e §6 item 3) (D2 2026-11-09), **0x7ED3231E** (angles 900/1800/2700/3600, constants π and 1800.0), calls 11 C-runtime float routines: fabs 0x7E4FE251, tan 0x7E501AAC, and the soft-float helpers 0x7E500F62, 0x7E501390, 0x7E50160E, 0x7E5017EC, 0x7E501860, 0x7E5018CF, 0x7E5018D6, 0x7E5018E8, 0x7E501986 (13a §2.2). Resource lookups (outside these ranges) (A4 2026-11-09):
  - 0x7ECFF3E9 (69 callers) indexes RAM tables by the current layer byte 0x602B6034;
  - 0x7ECFF3C3 indexes ROM records of 884 bytes at 0x7EFB1034 (sub-records of 52 bytes).
- **Roles not identified:** of 0x8001/04/05/07/08/0A/0E/0F/12/13 and the C/D parts. Text, image and frame parts are likely (inferred).
- **Helper layer 0x7EDC17FB–~0x7EDC1B36 (verified; most helpers "set only if changed"):** 0x7EDC17FB is a static initializer (stores −1/0x7EDC178A at 0x602BC588), not a helper (A5 2026-11-09); 0x7EDC1851 `setVisible(w, b)` (2,641 call sites, the most called GUI function; vt+80 then vt+76); 0x7EDC1875 `setListIndex(w, i)` (453; range-checked); 0x7EDC189F set list item resource (no "only if changed" check) (A5 2026-11-09); 0x7EDC1B15 set list item value; 0x7EDC18C8 move/resize (vt+52 get rect, +44 set rect, +168 invalidate); 0x7EDC1972 the same but gets the rect through vt+48 (A5 2026-11-09); 0x7EDC181B set text by string id (0x7ED2CE0C), or hide when the id is 0 (A5 2026-11-09); it never shows the widget again. The layer ends at **0x7EDC1B36**; more helpers: 0x7EDC1835, 0x7EDC19F4, 0x7EDC1A45, 0x7EDC1A96, 0x7EDC1AB4 (14e §2.7) (D2 2026-11-09). 0x7EDC2000 is inside the 1,333-byte fn 0x7EDC1B37 (to 0x7EDC206B) (A5 2026-11-09). C1 F065 0x7ED61C13 is a panel-level "show item n−2 or hide" helper built on these.

## 3. Panels (`GCPnl_*`) and panel numbers (verified)
- **Create by number.** `CreatePanel(this = manager, d0 = no 0..159)` is 0x7ED19D3F.
  1. It switches through the jump table 0x7EF0FBB0 (160 words).
  2. Each case calls the factory with type 0x6000+k and the resource record **0x7EF0DF10 + 0x2C·k**.
  3. It takes one of two panel slots (bytes at this+1374; pool id 6 + slot), so an old and a new panel can coexist.

  It is reached from the manager's vt slot +148 (0x7ED1B4FF, word 0x7EF10210). ShowPanelEx's GM_SHOWPANEL message leads there (inferred link).
- **Number → class.** 98 numbers map to a class and 62 are empty (`panelno.txt`). 16 classes have no number; they are created directly by type.
- **Resource record (44 bytes, verified):** `{u16 type, u16 k+1, u32 rects → 0x7EF0D7F0 + 16·k, u16 7, …, u16 layer (1/2/3), 0xFFFE, …, 100, 100}`. Field +20 is 0xFFFE in 98 records and 0xFFFF in 16. Records exist for k = 0…113 only (indices 114–159 are not records). The rect pair is two `{x, y, w, h}` rects (720×480 ×65, 800×600 ×37, 640×480 ×7, …), and in all 114 records the two rects are identical, so nothing in the data supports the inferred "two outputs" reading. (A4 2026-11-09)
- **Children.** Each panel's child-builder (a vtable slot, e.g. 0x7ED37E2D) loops over a per-class RAM table of resource pointers (e.g. 0x602B6218 / 0x602B7758). It calls the factory with type = the first u16 of each record. The compact property data is in ROM 0x7EF047B8–0x7EF0CDF0, indexed by `{key, ptr}` pairs at 0x7EF0CDF0, where key 0x60xx starts a panel (layout verified; field meaning not decoded).
- **Code and rodata order (verified).**
  - Code of class k = [ctor_k, ctor_k+1).
  - Rodata of class k = (vt_k−1, vt_k]: the strings come first, then the vtable.
  - Ctor and vtable addresses rise together.
  - **Inferred:** the 11 class names found are in alphabetical order, so the link order is alphabetical.

**Named panels (verified class-name strings in their rodata or code):**

| Name | Type | No. | Ctor | Name | Type | No. | Ctor |
|---|---|---|---|---|---|---|---|
| GCPnl_Art_Bkt_Rec | 0x6032 | 66 | 0x7ED3E485 | GCPnl_Index | 0x6025 | 53 | 0x7ED4AC23 |
| GCPnl_Calender | 0x6026 | 54 | 0x7ED3F53E | GCPnl_Menu | 0x6034 | 80 | 0x7ED53D35 |
| GCPnl_CompScale | 0x6030 | 64 | 0x7ED418F5 | GCPnl_Move | 0x602C | 60 | 0x7ED56907 |
| GCPnl_Custom_Btn | 0x6035 | 81 | 0x7ED42679 | GCPnl_Play | 0x6022 | 50 | 0x7ED5A7AB |
| debug menu (`gdbDebugMenu`) | 0x6066 | 150 | 0x7ED488AA | GCPnl_Play_Overall | 0x6023 | 51 | 0x7ED5D55A |
| GCPnl_Zoom | 0x6027 | 55 | 0x7ED7932E | | | | |

- Panel 81 is shown by the Custom Menu page (§5). GCPnl_Custom_Btn and GCPnl_Menu are the two ~3.9 KB menu-list panels (inferred).
- The debug-menu draw routine 0x7ED48BBA (sections 07, 10f) is in panel 0x6066's code.
- Panel **signature (verified, majority form):** 93 of the 115 callers of 0x7ED23C27 use `call 0x7ED23C27 ; mov a0,a2 ; mov VT,d0 ; mov d0,(a2) ; …zero the child array at +792… ; [call 0x7ED01DFD ; call 0x7ED01F7C/0x7ED01FBA]`. Variants: 16 store the vtable through (a0), zero +792 and return with no tail calls (e.g. 0x7ED7A79F); 0x7ED7E533 uses (a2), zeroes +792 and calls 0x7EDC65C5 with no 0x7ED01DFD; 4 use other child-array offsets: +796 (0x7ED40F26), +808 (0x7ED5313E), +824 (0x7ED488AA), +888 (0x7ED410EB) (A5 2026-11-09); 0x7ED230C2 only does `mov d0,(792,a0)`. (A4 2026-11-09)
- **Page classes named in 15a (D3 2026-11-09; class-name strings in `initMenu` logs, V):** userCommonSecondWizard 0x7EDC7EAA, userCommonTimeAdjust 0x7EDC8692, userCommonWizard1NRightAligned 0x7EDED9DD, userCommon1CNLWizard 0x7EDEE169, userMenuMainReset code 0x7EDECDC0–0x7EDED8D6, userMenuTopMenu 0x7EDFDA2A. They are menu pages, not panels.
- Panel virtuals log `[GUI App   ] GCPnl_X::CheckRecView/CheckIndexBtn/CheckImageArea/CheckAllArea() called`. These are the touch hit tests.

## 4. Generated state handlers (Ss*)
Source: a fork that decoded all 17 descriptors (`ss/handlers.tsv`, 3,137 (SS, state, event) rows). I re-checked the descriptor table, the SS10 counts and the debug-menu entry bytes myself.

### 4.1 Engine (verified)
- **Context.** RAM 0x6069FAC8: +0 current SS, +1 current state (both 1-based), +2 SS count 17, +4 the descriptor table, +16 dispatch 0x7ED822F9. Getter 0x7ED8226D.
- **Init.** 0x7ED82282 starts at SS 1 state 2 (POWER_ON); WinMain calls it.
- **WinMain loop.**
  - Messages ≥ 0x8000 are statechart events: event filter 0x7EDC4DBC → dispatch 0x7ED822FE(ctx, d0 = event, d1 = param, a1 = data) → state-change hook 0x7EDC4205.
  - Messages < 0x8000 are GM_* messages, which go to the window (vt+588).
- **Descriptor table.** 0x7EFB8BCC holds 17 pointers (index ss−1). Each 32-byte descriptor is `{u8 nstates; u16 nevents; u16 nhandlers; u16 nevents; u8 matrix[nevents][nstates] @+8; handler fn[] @+12; {u32 event, u32 row}[] @+16; entry fn[nstates] @+20; exit fn[nstates] @+24}`.
  - Handler indexes 0–2 are default `clr d0; retf` stubs.
  - Example: SS10 at 0x7EFD1F94 = 4 states, 10 events, 22 handlers, verified bytes `04 00 0a 00 16 00 0a 00`.
- **Dispatch.** row = evmap(event) (linear search, 0x7ED8243C); idx = matrix[row·nstates + state−1]; r = handler(a0 = ctx, d0, d1, a1).
- **Return convention.** 0 = consumed, stay. 1–255 = go to that state in the same SS. `(ss<<8)|state` = switch super-state. The engine runs exit[old] then entry[new].
- **`0x7EDC5C47(code, param)` is PostEventToCA,** a request to the camera app. **CA code 23 = GUI touch result (D3 2026-11-09, 15a §2.4; V for the calls, I for the name):** the app-window handler posts PostEventToCA(23, result) after every GuiTouch panel action (0x7ED1C489), and the live-view touch-mode dispatcher 0x7ECEDEB6 posts (23, 27) / (23, 39). It is **not** a GUI state change (corrects 10f). The GUI posts events to itself with 0x7EDC5BF5 (218 sites).
- **Name tables (debug only).**
  - SS names: 0x7EFDD2D8 `{ss, name, state-name table}`.
  - Event names: 0x7EFDEF78–0x7EFDFA20, 339 `{id, name}`.
  - Event-id groups: 0x90xx keys/dials, 0x91 touch, 0x92 HDMI-CEC, 0x96xx CA→GUI requests (`EVT_REQ_*`, `EVT_START/END_*_PRINT`), 0x97 rec display, 0x9Axx GUI-internal, 0xA0xx debug/self-adjust, 0xA1/A2 BT, 0xA3 print.

**Signature of a generated handler (verified bytes):**
1. Prologue `cf f0` (movm [d2,d3,a2,a3]) and `f8 fe fc`.
2. `mov d1,d3 ; mov a1,a3 ; mov d0,d2 ; mov a0,a2`.
3. `call guard ; exthu d0 ; cmp 1,d0 ; beq … ; cmp 2,d0 ; beq …`.
4. Each branch calls an action with (a0, d0, d1, a1), then `exthu d0 ; ret [d2,d3,a2,a3],20`.

Actions end `mov N,d0 ; ret` or build `asl 8 ; or` for an SS change; the shared "stay" action is 0x7EDA2654 `clr d0; retf` (113 callers). Entry/exit functions take the same arguments; their result is ignored. Many handlers log `doCmd_<Ss>_<St>_<Evt>`. **Tool note:** 213 handler entry points are not function starts in map-test (`ss/handler_starts.txt`).

### 4.2 Super-states (verified; code ranges are the handler code)
| SS | Name | Descriptor | States/events/handlers | Handler code |
|---|---|---|---|---|
| 1 | SS_COMMON | 0x7EFC4038 | 9/37/41 | 0x7ED8612D–0x7ED86DA5 (A5 2026-11-09) |
| 2 | SS_REC | 0x7EFD8A78 | 4/26/20 | 0x7EDBE595–0x7EDBEE11 |
| 3 | SS_MENU_MAIN | 0x7EFD40C4 | 12/71/211 | 0x7EDA8BB6–0x7EDB3239 |
| 4 | SS_MENU_LV | 0x7EFD30F8 | 10/45/181 | 0x7EDA46B7–0x7EDA8BA0 |
| 5 | SS_MENU_PLAY | 0x7EFD5230 | 2/2/3 (empty placeholder) | — |
| 6 | SS_PLAY_SINGLE | 0x7EFD7BAC | 40/78/200 | 0x7EDB6DC4–0x7EDBE531 |
| 7 | SS_PLAY_MOVIE_SLIDE | 0x7EFD6808 | 30/69/126 | 0x7EDB4B9E–0x7EDB6DB0 |
| 8 | SS_PLAY_INDEX | 0x7EFD598C | 13/64/75 | 0x7EDB345D–0x7EDB4B45 |
| 9 | SS_SELFADJ | 0x7EFD8E70 | 9/26/60 | 0x7EDBEE1C–0x7EDC0097 |
| 10 | SS_DEBUGMENU | 0x7EFD1F94 | 4/10/22 | 0x7EDA0410–0x7EDA098D |
| 11 | SS_USB | 0x7EFD9B98 | 6/23/37 | 0x7EDC0D90–0x7EDC15B0 |
| 12 / 13 | unnamed stubs | 0x7EFD5278 / 0x7EFC1884 | 2/2/3, 1/26/3 | 12 has only an entry 0x7EDB3448 (`USB_Connect_Print`) |
| 14 | SS_DPS | 0x7EFD28D0 | 26/33/202 | 0x7EDA09C0–0x7EDA4694 |
| 15 / 16 | SS_BTSEND / SS_BTRECEIVE | 0x7EFC3C78 / 0x7EFC1E6C | 35/24/111, 19/36/89 | 0x7ED8459B–0x7ED860E7 / 0x7ED82820–0x7ED8453D |
| 17 | SS_SPC (FlashAir pairing) | 0x7EFD91D4 | 15/18/27 | 0x7EDC00BD–0x7EDC0D7B |

- Handler code is ordered alphabetically by SS name (inferred from the ranges). Other GUI code sits in 0x7ED87–0x7ED9F.
- **Entries from SS_COMMON (verified return constants, as SS.state):** 0x962A START_SELF_ADJUST → 9.1; 0x9630 START_USB_SELECT → 11.1; START_MEDIA_SETUP → 11.1/11.3; 0x9632/0x9634 START_EASY/CUSTOM_PRINT → 14.1; START_LV_CONTROL → 4.1; LV_GUIDE → 4.9; ART_SELECT → 3.7; SCN_SELECT → 3.8; DIRECT_SELECT → 2.1; START_SLIDE_SHOW → 7.11; START_MENU → 0x300|state; START_PLAY → the chooser 0x7ED05440.

### 4.3 Which event opens which screen
- **Light box (verified code; menu label inferred).**
  - In SS_PLAY_SINGLE display states, INFO-key release (0x7EDBACD3) returns `CPlaySingleFrame::getJumpState` 0x7ED09135.
  - getJumpState reads info 27 (prm 0x8301) and the ▶Info enables, info 253–257 (prm 0x9171[0..4]).
  - It returns state 15 `ID_ST_DISP_LIGHTBOX_PREPARE` when the mode is 11 and info 257 = 1. The **entry** function of that state is 0x7EDB8C08.
  - So the light box is one stop of the INFO display cycle, enabled by ▶Info "@A021@" (sub-item group 191).
- **3D Show (verified code; the API meanings are inferred).**
  - 0x7EDB61FE is the **entry** of SS7 state 16 `ID_ST_3D_IMG_SEL_MENU`. It builds the "Sel. Image: All / 3D Show" panel.
  - The play-start chooser 0x7ED05440 picks 7.16 when CameraCommon vt+104 ≠ 0 (inferred: 3D output available) and MediaCtrl reports 3D/MPO images.
- **BGM Import (verified structure).** No Ss row handles it. A menu item with vtable 0x7F00095C (32 code slots; "userMenu item" is inferred: no class string, base slots shared with `userMenu*` classes): slot 2 = 0x7EDF26B2 loads string 1782 and calls ShowPanelEx(111). 0x7EDF2BA1, which logs `OlyApiSoundCtrl::registImportSound()`, is slot 40 of a **different** 45-slot class (vtable 0x7F0010B4, ctor 0x7EDF2A08, created by 0x7EDF2A25, factory id 0x20D at 0x7EFE20B8); that the item reaches it is inferred. It runs inside SS_MENU_MAIN (Slideshow > BGM, inferred). (A4 2026-11-09)
- **SS_DEBUGMENU (verified; resolves 10f's open question).**
  1. A Setup dialog method 0x7EDFD665 checks the key code 4 and then `IOlyApiMaintenance` (0x7E99E423) vt+12, logged as getShippingInfo(4).
     - Only if the result is 1 does it post EVT_REQ_START_VERSION_CHECK 0x9628.
     - **Inferred:** the dialog is Monitor Adjust (it toggles info 432 and logs `showMonitorMenu`), and selector 4 is API_SHIPPING_INFO_MENU_BUTTON.
  2. SS_MENU_MAIN state 4 `ID_ST_WIZARD_MENU_ENTRY` (the Setup-menu page state) maps 0x9628 to state 6 `ID_ST_HIDE_MODE` (handler 0x7EDAB90A = `mov 6,d0; retf`). No other SS state has a non-default handler for 0x9628 (SS_COMMON has a row, with default handlers only), and EVT_REQ_END_VERSION_CHECK 0x9629 has no row (descriptor scan). (A4 2026-11-09)
  3. In HIDE_MODE a counter at RAM 0x602BC480 steps on **Up → Down → Left → Right → shutter half-press → shutter full-press** (0→1→2→3→7→8; e.g. 0x7EDAB980 is the Down step).
  4. **OK with counter 8 returns 0x0A01 = SS 10 state 1.** Bytes 0x7EDABA14–0x7EDABA54 checked: `cmp 8,d0 ; mov 10,d2 ; mov 1,d3 ; … asl 8,d2 ; or d3,d2`.
  5. Whether a retail body passes the getShippingInfo(4) gate is **not known**. External corroboration only: the widely cited Olympus hidden-menu sequence (Monitor adjust, Up, Down, Left, Right, shutter) matches.
  6. **Second sequence.** A second counter 0x602BC482 (OK-long / MENU-long) reaching 10 makes the same OK call 0x7EDED19A(4,0), which is in `userMenuMainReset`, and then settings slot +40. **Inferred:** a hidden reset. **Corrected (D2 2026-11-09):** OK-long sets the counter to 14 (or to 10 if it was 15) and MENU-long sets it to 15 (or to 10 if it was 14), so the sequence is OK held 2 s and MENU held 2 s in either order, then OK. The 2 s long-press times come from the HIDE_MODE entry function 0x7EDABA6F (`setLongPressKey(8, 2000)`, `(9, 2000)`), which this section omitted (14e §4.4).
- **0x9628 and the "version-check menu" of 10f §4.3 are two different paths (verified unless marked).** (A4 2026-11-09)
  - The only immediate 0x9628 in block 0 is the GUI self-post at 0x7EDFD68D (step 1). The CA could also deliver it: GuiCallerImp::sendEvent 0x7ECE6E27 turns CA code k (1..167) into a GUI event through the table 0x7EEF3434 (`{k, event}`), where k = 0x75 → 0x9628. No CA_MAIN code (0x7ECCB800–~0x7ECE4000 (L1 2026-11-09)) loads 0x75 as an immediate, so no CA sender was found. (A4 2026-11-09)
  - The 10f path is the CA sub-app CAM_MISC_VERCHK_MENU (`startVersionCheckMenuSubAppStateMisc` 0x7ECE0653, event 0x0600000A). CA `startShooting` 0x7ECDCB10 reads rcv_info.info from the **second** word of the CA event (a1+4) and maps info 11 → VERCHK (12) and info 12 → CAM_MISC_FIRMUP (13). (A4 2026-11-09)
  - The Firmware OK path, `doCmd_SsMenuMain_StWizardMenu_EvtKeyOKOn` 0x7EDA9D03, calls PostEventToCA(11, 12) for item 43 and logs `F/W Version up start`. PostEventToCA sends {code, param}. The sender 0x7ECE3A9E maps code 11 to the CA event 0x0400000B `GUI_START_SHOOTING_SERVICE` (table 0x7EEEBB28) and keeps param 12 as the second word. So item 43 carries info **12 = CAM_MISC_FIRMUP** (firmware update), not VERCHK. The step from the 0x0400000B handler (0x7ECDCF0D → 0x7ECD27A7) to startShooting was not traced (inferred). No PostEventToCA call passes the constants (11, 11), so the trigger of VERCHK is not known. (A4 2026-11-09)
  - So EVT_REQ_START_VERSION_CHECK 0x9628 is the debug-menu entry event (HIDE_MODE), and it is not the Firmware screen. The shared name suggests that the CA VERCHK sub-app is the intended sender of k = 0x75 (inferred). (A4 2026-11-09)
- **Inside the debug menu:** state 1 = item list (OK → action dispatcher 0x7EDA05EC, 10f); 2 = life test running; 3/4 = Color setting/result. Exits return 3.6 (HIDE_MODE). EVT_DEBUG_MENU 0xA000 is posted only by the LifeTest callback 0x7EDCB035 ("test ended → back to the menu"); it is not an entry.

### 4.4 DPS (SS 14) and USB (SS 11) (verified; DPS state roles inferred)
- **C1 F066 0x7EDA3AB5** = SS_DPS state 20, event EVT_END_CUSTOM_PRINT 0x9635. Its 24 siblings are the same generated handler for the other states.
  - Guard 0x7EDA3095: `[GUI] Abort custom print!` through IOlyApiCustomPrint (0x7E9C0BA2) vt+112. It always returns 1.
  - Action 0x7EDA301D: vt+116 → PostEventToCA(20, 0) → returns 0x0104 = SS_COMMON `ID_ST_BLACK_SCREEN`.
  - EVT_END_EASY_PRINT 0x9633 has a parallel set (0x7EDA3DAE…) using the EasyPrint interface.
- **DPS states:** 1 = start (0xA306/0xA307 → 2 or 26); 2–4 and 9–21 = selection/setting screens (entry functions at a 15-byte stride from 0x7EDA09EC, each draws screen n through 0x7EDCED5A); 17 = image selection (~~all arrow,~~ the only state with the arrow OFF and long-press keys and EXPANSION (zoom) keys; arrow ON handlers also exist in states 4, 6, 7 and 9–21: UP/DOWN in 4 and 10–18, LEFT in 6, 7, 9 and 11–21, RIGHT in 9, 11–13, 16, 17, 19, 20; e.g. state 20 LEFT 0x7EDA19EC moves the print-image cursor through `moveCurrent(3)`) (C3 2026-11-09); 23/24 = printing (EVT_PRINT_END 0xA303 → 1.4). DPS GUI helpers 0x7EDCE9B9–~~0x7EDD07F9~~ ≥0x7EDD08D2 (0x7EDD07F9 is the start of moveCurrent, 218 B) (C3 2026-11-09).
- **USB states.** USB_MENU, USB_WARNING, MEDIA_SETUP, USB_PRINT_READY (entry 0x7EDC0FE9), USB_PRINT_SEL (entry 0x7EDC0ED1, `USB Print Key Right -> Easy Print`; left/right/OK choose Easy or Custom print), BUSY.

## 5. Custom Menu A–J item lists (verified bytes; fork result checked in bytes for 4 rows)
- **Row table.** 0x7EFF7E80–0x7EFF835F holds 78 rows of 16 bytes: `{u16 page 0..9 = A..J, u16 label, u16 info, 0, u16 idx, u16 help, u16 x, u16 flag}`. info 2000 = submenu, 2047 = action (Pixel Mapping); the help string goes to GUI data block 45. Section 10d's 0x7EFF8250 is page **H**'s first row (Quick Erase), not the table start.
- **Code.**

| Role | Address |
|---|---|
| Page object singleton (1,264 B, RAM 0x602BE3A4, vt 0x7EFF8A20) | 0x7EDE9AA6 |
| Key handler (up/down walk all 78 rows, wrap at 77, skip hidden rows) | 0x7EDE9C38 |
| Draw (7 rows per screen) | 0x7EDE9F56 |

  It shows panel 81. The page is the current row's page, so the cursor crosses pages.
- **Status array:** RAM 0x606A3118[78], 0 normal / 1 greyed / 2 hidden, filled from `{item_id, check_info}` × 78 at 0x7EFF8E4C. Hidden comes from 0x7EDCD103 (runtime hide lists at RAM 0x602BCE98, **not resolved statically**); greyed from 0x7EDCCC9E → ModeCheck slot 0.
- **Items.** Format: label(string id) info. "sub" = submenu.
  - **A AF/MF:** AF Mode(51) sub; Full-time AF(539) 98; AEL/AFL(44) 68; Reset Lens(224) 81; BULB/TIME Focusing(1462) 169; Focus Ring(139) 38; MF Assist(172) 285; Set Home(47) 238; AF Illuminat.(50) 62; Face Priority(130) 241.
  - **B Button/Dial:** Button Function(96) sub; Dial Function(99) sub; Dial Direction(98) sub; Lock(100) 386.
  - **C Release/Drive:** Rls Priority S(222) 79; Rls Priority C(221) 80; L fps(1161) 430; H fps(1321) 431; +IS Off(1472) 441; Lens I.S. Priority(1766) 494.
  - **D Disp/Sound/PC:** HDMI(1662) sub; Video Out(273) 1010; Control Settings(80) sub; Info Settings(149) sub; Displayed Grid(797) 155; Picture Mode Settings(204) sub; Histogram Settings(144) sub; Mode Guide(174) 311; Live View Boost(184) 36; Frame Rate(1367) 272; Art LV Mode(59) 387; Flicker reduction(1750) 464; LV Close Up Mode(1476) 344; Backlit LCD(72) 161; Sleep(261) 32; beep(75) 18; USB Mode(272) 82.
  - **E Exp/Metering/ISO:** EV Step(125) 64; Noise Reduct.(189) 35; Noise Filter(188) 143; ISO(153) 6; ISO Step(158) 141; ISO-Auto Set(155) sub; ISO-Auto(154) 239; Metering(169) 1; AEL Metering(45) 103; BULB/TIME Timer(1464) 173; Live BULB(1466) 437; Live TIME(1468) 438; Anti-Shock(57) 167.
  - **F Flash Custom:** X-Sync.(137) 114; Slow Limit(136) 174; flash+EV(164) 113.
  - **G Quality/Color/WB:** Record-mode Set(214) sub; Pixel Count(206) sub; Shading Comp.(254) 61; WB(281) 9; All WB(56) sub; Keep Warm Color(542) 429; flash+WB(543) 318; Color Space(88) 60.
  - **H Record/Erase:** Quick Erase(215) 142; RAW+JPEG Erase(216) 139; File Name(133) 21; Edit Filename(116) sub; Priority Set(210) 83; dpi Settings(109) 178 (the parallel list has 179); Copyright Settings(93) sub.
  - **I Movie:** Movie Mode(94) 162; Movie mic(180) 102; Movie Effect(1492) 444; Wind Noise Reduction(1087) 434; Recording Volume(1373) 435.
  - **J Utility:** Pixel Mapping(207) action; Exposure Shift(129) sub; Battery Warning Level(73) 278; Touch Screen Settings(544) 427; Eye-Fi(1447) 404.
- **Caution:** like the sub-item table, this may be a superset. The runtime hide lists can remove rows, e.g. Frame Rate, Flicker reduction or Lens I.S. Priority (inferred).
- **Sub-item table.** It is 0x7EFEF4FC–0x7EFF044B, 196 records of 20 bytes: `{group, title, info, 0, kind, 0, 7, 1, label, 0}`.
  - The label is at +16 of the same record. Section 07 read the table 16 bytes out of phase.
  - The "second table at 0x7EFEFE04" is the same table continued.
  - For submenus, group = the parent row's item id. Examples: G152 WB presets; G191 ▶Info = Image Only / Overall / @A021@ / Highlight&Shadow; G42 Menu Display = info 283/394.
- **Menu-page registry.** ~~The table 0x7EFE190C–0x7EFE21CB holds 280 `{u16 page, 0, create}` entries with 90 factories.~~ **Corrected (D3 2026-11-09, 15a §4):** the table is **0x7EFE180C–0x7EFE21CB, 312 `{u16 list id, 0, create}` entries with 101 factories** (it starts right after a string at 0x7EFE1804; getListPage 0x7EDC7DBA loops `cmp 312` from `add 2130581516` = 0x7EFE180C). It is keyed by **list id**, not page id: openPage 0x7EDCBE97 maps a page id to a list id through three hash tables 0x7EFE5A14 / 0x7EFE5614 / 0x7EFE4E14 before calling 0x7EDC7DBA (e.g. page ids 547–551 → lists 95–99). There is no table at 0x7EFE1914 (D3 2026-11-09). The generic list page is 0x7EDC7ECB (vt 0x7EFE221C). The lookup is 0x7EDC7DBA, which caches 50 pages.
  - So 0x7EDCBE97 → 0x7EDC7DBA (section 07) creates **menu pages**, not panels.
- **`userMenu*` classes** (0x7EDE7835–0x7EE00F8D) are special pages: WbRev, MainReset, PlayWiz_*, Play_CompScale/ImageCompose/DPOF…, Rec2_WBBKT, TopMenu. They do not build the A–J lists.
- **Accessory-port menu.** 12-byte rows at 0x7EFF6870: PENPAL Share/Album, EVF Adjust (info 58).

## 6. Object registries and GUI↔app interfaces

### 6.1 Actuator/Viewer registry 0x7EFC5408 (verified)
- **Table:** 31 entries `{u32 id 0..30, create(owner)}` (C1 said 0x7EFC5470, which is entry 13).
- **Lookup:** 0x7ED8BBDF(d0 = id, a0 = owner) is a linear search. id 31 = none.
- **Callers:** `IGui_Controler` 0x7ED87077 (`internal_control_id / actuator_id / viewer_id` logs) and 0x7ED87397, which pick an Actuator and a Viewer per control. The lookup is also called by 0x7ED996F6 (id 18) and by C1's F069 0x7EDC15FF (id 19 child).
- **Objects:** allocated with operator new 0x7EBA62DB; sizes 4–1,608 bytes.

| Ids | Object, from nearby strings (inferred) |
|---|---|
| 0, 1, 4 | live-view superimpose |
| 6, 8–10, 17 | USB print / Warning_Viewer area |
| 11, 28, 29 | Func_Scp_Actuator (Super Control Panel) |
| 12, 13, 26, 27 | Input_String_Actuator (SPC text entry) |
| 23–25 | Rec_View_Viewer area; section 10f's "debug-menu factories" (params 3/4/5) |
| 20–22 | **Panel-112 message viewer** (L1 2026-11-09) (V code; role I). Creators 0x7ED97886/0x7ED978A2/0x7ED978BF allocate 40 B and call the ctor 0x7ED978DC with d0 = 0/1/2 (stored at +36; base 0x7ED8BBA6, vtable 0x7EFCE794). The Update slot 0x7ED97907 sets RAM 0x602BB7C8 = panel 112, reads data-model blocks 88/16/0, calls 4 member functions (pairs stored by the static initialiser 0x7ED97A49) and ShowPanelEx. Message tables by d0: title 0x7EFCE764 {0→1719 "Connection to Smartphone", 1/2→1726 "Connection Settings"}, result 0x7EFCE77C {0→1721 "Card configured by another device. Can not change the setting.", 1→1728 "Initial setting completed", 2→1733 "Password has been changed"}. Inferred: the title and result message of the smartphone/FlashAir connection set-up (review C4 F062) |

### 6.2 OlyApi interfaces (verified getters; names from class strings and link order)
- **Getter pattern (signature):** `mov (0x602B24xx),a0 ; cmp 0,a0 ; bne ; mov 2,d0 ; call 0x7E99A33A (lock) ; call 0x7E96E86E ; … mov 4,d0 ; call 0x7EBA62DB ; call ctor ; …`.
- **Object:** a 4-byte object whose ctor stores its vtable.
- **API id:** each method passes a constant `0xGGCCMM`, where GG.CC is the class and MM the method.
- **Order:** the 39 getters 0x7E9BFA7E–0x7E9CDEBE (RAM 0x602B2478–0x602B2510) are in alphabetical class order. That order and 20 `OlyApiX::` strings fix the names.
- **GUI column:** call sites in 0x7ECA–0x7EE2.

| Getter | Class | API class | GUI | Getter | Class | API class | GUI |
|---|---|---|---|---|---|---|---|
| 7E9BFA7E | BackGroundCtrl | 01.03 | 10 | 7E9C524D | PixelMapping | 01.08 | 2 |
| 7E9BFDA3 | Bluetooth | 05.04 | 81 | 7E9C5389 | PlayCalendar | 03.1E | 19 |
| 7E9C0BA2 | CustomPrint | 05.03 | 66 | 7E9C5850 | PlayCommon | 03.01 | 148 |
| 7E9C1A8D | DateCtrl | 01.07 | 9 | 7E9C5FF8 | PlayIndex | 03.03 | 20 |
| 7E9C1F38 | DeviceLink | 05.01 | 5 | 7E9C667F | PlayLightBox | 03.1D | 46 |
| 7E9C2147 | EasyPrint | 05.02 | 21 | 7E9C6D18 | PlayMovie | 03.05 | 18 |
| 7E9C25B8 | EditAspect | 03.1A | 12 | 7E9C71C5 | PlayRecord | 03.06 | 10 |
| 7E9C290C | EditBeautyAdjust | 03.0D | 6 | 7E9C7424 | PlaySelect | 03.1C | 57 |
| 7E9C2BDB | EditColor | 03.09 | 28 | 7E9C794C | PlaySingleFrame | 03.02 | 124 |
| 7E9C2E87 | EditImageOverlay | 03.0A | 17 | 7E9C8579 | PlaySlideShow | 03.0F | 17 |
| 7E9C34D1 | EditRaw | 03.1B | 43 | 7E9C8947 | PlaySound | 03.17 | 50 |
| 7E9C396C | EditRedEyeAdjust | 03.0B | 8 | 7E9C8BD4 | Relocate | 04.03 | 1 |
| 7E9C3B7D | EditResize | 03.07 | 4 | 7E9C8D07 | ReservePrint | 03.10 | 40 |
| 7E9C3D89 | EditShadowAdjust | 03.0C | 8 | 7E9C93F1 | SelectOverlay | 03.1F | 9 |
| 7E9C3F9A | EditTrimming | 03.08 | 11 | 7E9C97C0 | SelfAdjust | 04.01 | 20 |
| 7E9C4351 | (3 methods; OSDEffect?) | 01.12 | 4 | 7E9C9E9A | SettingController | 01.02 | 706 |
| 7E9C458C | FlashAir | 05.06 | 19 | 7E9CADB5 | Shooting | 02.01 | 98 |
| 7E9C4970 | KeyCtrl | 01.0E | 4 | 7E9CD7B0 | SoundCtrl | 01.05 | 39 |
| 7E9C4DC8 | LevelCtrl | 01.0F | 7 | 7E9CDEBE | TouchPanel | 05.05 | 3 |
| 7E9C503D | LifeTest | 04.02 | 2 | | | | |

- **Second getter series (verified, same pattern; RAM 0x602B239C–0x602B23BC):** CameraCommon 0x7E99D2DD (01.01, 209 GUI sites), Maintenance 0x7E99E423 (04.04, 15), MediaCtrl 0x7E99E95E (01.0C, 145), ModeCheck 0x7E99F203 (01.09, 49), PowerSupplyControl 0x7E99FF14 (01.0A, 10). So 10d's "39 interfaces" is the first series only. Other names in the API name table (SystemCommon, OSDControl, ShootingMovie, …) have no getter of this shape (not searched further).
- **Component mapping:** each interface reaches the C++ component through its `OlyHfwOpe*` class (10d §2 table: the Play/Edit ids 0x201xx and their requester getters).
- API class 03.0A is EditImageOverlay (link order); the GUI uses no EditCalendar interface (agrees with 10d).

### 6.3 "Return-to (SS, state)" singleton 0x7EDDBC06 (L1 2026-11-09)
- **getInstance 0x7EDDBC06** (V): lazy `new 52` → RAM 0x602BDA2C, ctor 0x7EDDBC2E (+0 = 0; u16 +4/+8/+12 = 0xFFFF; other fields 0). **445 call sites in 167 functions**, most of them in the Ss handlers (0x7EDA8xxx–0x7EDBAxxx) and the page classes (0x7EDE4xxx–0x7EE00xxx), the rest in the CCommon/CPlay* controllers 0x7ED01xxx–0x7ED0Fxxx and the SS_BT handlers 0x7ED83xxx–0x7ED84xxx.
- **Accessors 0x7EDDBC64–0x7EDDBD4F** (V): 4–6-byte set/get pairs: +0 flag (set 0x7EDDBC64, get 0x7EDDBC68), u16 +4 (0x7EDDBC6C/0x7EDDBC72), +6, +8 (0x7EDDBC84/0x7EDDBC8A), +10, +12, … **Reset 0x7EDDBCA8** (32 callers) clears +0, +16, +32, +36, u16 +40/+42 and sets u16 +4/+8/+12 = 0xFFFF; unlike the ctor it leaves +6, +10, +20, +24, +44 and +48.
- **Use** (V for two handlers, review C4 F063/F068): the SS_MENU_MAIN wizard-tick handler 0x7EDB0BC5, on "exit", reads the flag, +4 = SS and +8 = state and goes to that `(SS<<8)|state`; the page-326 key slot 0x7EDF2D66 pops the nav stack twice when the flag is 0 and returns "exit menu" when it is set.
- **Inferred:** the place to return to after a menu or wizard closes (+0 = a target is set, +4 SS, +8 state). The other fields are not decoded.

## 7. Corrections
1. **Region table:** 0x7EE02095–~0x7EE294B4 (not 0x7EE21020; C2 2026-11-09) is a DMP GL/shader library used by C3D, not GUI. 0x7ECA1020–0x7ECCB7FF is data and padding (108,541 bytes of 0xFF from 0x7ECB1003); CA_MAIN code starts at 0x7ECCB800. (A4 2026-11-09)
2. **Section 07 §3.2:** the sub-item table is 0x7EFEF4FC–0x7EFF044B (196 × 20 bytes, label at +16), and 0x7EFEFE04 is not a second table. 0x7EDCBE97/0x7EDC7DBA create menu pages; panels are created by 0x7ED19D3F (0..159).
3. **Section 10d §6:** the Custom Menu table starts at 0x7EFF7E80. 0x7EFF8250 is page H, and group 8 is page I. The "mic level" row is labelled Recording Volume.
4. **C1 review:** the registry is at 0x7EFC5408, and 0x7EFC5470 is its entry for id 13. F069 is an Actuator/Viewer object (id 17). The 0x7ED17DB8 callers are the panel child-builders and CreatePanel, not "widget" constructors.
5. **Section 10d:** 39 OlyApi getters is the first series only; at least 5 more exist at 0x7E99D2DD–0x7E99FF14.
6. **C1 F066:** it is SS_DPS state 20 / EVT_END_CUSTOM_PRINT. Return 260 = 0x0104 = go to SS_COMMON BLACK_SCREEN. 0/1/23 are "stay", "state 1" and "state 23".
7. **Section 10f §4.1:**
   - The SS_DEBUGMENU entry is found (§4.3).
   - 0x7EDC5C47 is PostEventToCA, so "(9,7) for item 598" and "(3,0) exit" are CA requests.
   - 0x000A0004/0x000A0016 are descriptor counts. 0x7EFD1EA4 is the event map and 0x7EFD1EF4 the handler array.
8. **Section 10d:** 0x7EDB8C08 (light box) and 0x7EDB61FE (3D Show) are state **entry** functions, not handler-table rows.
9. **Section 07 §5:** there are 17 SS ids; 12 and 13 are stubs, 17 = SPC and 5 is empty.
10. **Section 10f §4.3:** the Firmware item (43) posts PostEventToCA(11, 12) = GUI_START_SHOOTING_SERVICE with info 12, which `startShooting` maps to CAM_MISC_FIRMUP, not to VERCHK (link to startShooting inferred). EVT_REQ_START_VERSION_CHECK 0x9628 is a different, GUI-side event that leads to HIDE_MODE (§4.3). (A4 2026-11-09)

## 8. Open questions
1. Roles of most 0x80xx widgets and of the C/D parts. A pass over the panel resource data (0x7EF047B8–0x7EF0CDF0) would give each child's type, rect and string id.
2. Names of 103 of the 114 panel classes. The alphabetical order bounds them between the 11 anchors.
3. The Custom Menu hide lists (RAM 0x602BCE98): which rows the E-PM2 hides at run time.
4. API class 01.12 (3 methods): is it OSDEffect?
5. Does getShippingInfo(4) return 1 on a retail E-PM2? This decides whether the debug menu is reachable. Also: which physical key is code 4 in the Monitor Adjust dialog, and what the second (OK-long/MENU-long) sequence resets.
6. What 0x7ED009D6 / 0x7ED00A1D test (they gate the play-start chooser and the light box). There are no state-name tables for DPS, SELFADJ, DEBUGMENU or SPC.
