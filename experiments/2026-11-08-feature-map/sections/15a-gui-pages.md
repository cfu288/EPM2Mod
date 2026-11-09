# 15a. GUI app ~~0x7ED40000~~ 0x7ED37DAA–0x7EE02094 (L1 2026-11-09): pages, panels, Ss screens, touch (E-PM2 v1.6, round D3)

Scope: a function-level index of the GUI app code. This section answers coverage C3: round3-review3 weakest area 4 (F053 touch dispatcher, F054 layer insertion, F059 Ss screens) and round3-review4 weakest areas 1 and 2 (no per-page index, GuiTouch missing, F061–F068 and the CONTRADICTED F064). It builds on 13d (classes, panels, Ss engine) and 14e (methods).

- **Labels:** **V** = verified (read in code or bytes); **I** = inferred.
- **Addresses:** runtime addresses. "vt+N" = the virtual at byte offset N.
- **Index:** `15a-gui-pages.tsv` (~~1,181~~ 1,184 rows (L1 2026-11-09)). Look up a random function there in this order: by address in the `region`, `class`, `page-class`, `panel` and `touch-action` rows, then by id in the `page N`, `SS_x.n`, `registry N` and `page-key N` rows.
- **Scratch:** `$S/d3/gui/`:
  - `pages.py` → `pages_raw.txt` (functor cases);
  - `idx.py` / `pcls.py` / `gaps.py` / `api.py` → `pcls.txt`, `order.pkl` (page classes);
  - `spx.py` (ShowPanelEx sites);
  - `touch.py` → `touch.txt`;
  - `ss.py` → `ss.txt`;
  - `keys.py` → `keys.txt`;
  - `gen.py` / `gen2.py` / `hand.tsv` (TSV builder).

## 1. Area and boundaries (V unless marked)

This table replaces 13d §1 rows "~~0x7EDC15B0–~0x7EDE0000~~" and "~~~0x7EDE0000–0x7EE01FF5~~" (L1 2026-11-09) for the part from 0x7EDC7DBA.

| Range | Contents |
|---|---|
| 0x7ED37DAA–0x7ED82275 | 114 `GCPnl_*` panel classes. The TSV `panel` rows give, for each of the 98 numbered panels: ctor range, type, vtable, resource record and who shows it (§2.3) |
| 0x7ED82276–0x7EDC15B0 | Statechart engine and WinMain; Ss handlers; live-view controller and Actuator/Viewer objects (13d). Per-state screens: §2.6 |
| 0x7EDC15B0–0x7EDC7DB9 | Actuator/Viewer creators for ids 6, 8, 9, 10, 17 (the viewer of ids 8/9 is at 0x7EDC288E–0x7EDC2DE7, §2.7), the widget helper layer 0x7EDC17FB–0x7EDC1B36, and guiUtility (ShowPanelEx 0x7EDC5D2D, PostEventToCA 0x7EDC5C47, self-post 0x7EDC5BF5) |
| 0x7EDC7DBA–0x7EDC9D1B | `getListPage` 0x7EDC7DBA and the list-page base classes (§2.1) |
| 0x7EDC9D1C–0x7EDCB01B | BT wizard screen classes: userGuiBTAnimation, userGuiBTSelectWizard and userGuiBTWizard (§2.5) |
| 0x7EDCB035–0x7EDCBE96 | Callbacks: LifeTest 0x7EDCB035, the BT dispatcher 0x7EDCB0C5 and JpegEdit 0x7EDCB328. Also the touch binding 0x7EDCBA98 (§2.4) and the BT wizard base 0x7EDCBBD5–0x7EDCBE96 |
| 0x7EDCBE97–0x7EDCCA5C | **Page-open functor** `openPage(id)` (3,014 B, §2.1) |
| 0x7EDCCA5D–0x7EDCDAF0 | **Menu-page framework:** the grand-base and page-base classes, the nav stack and the guide labels (§2.1) |
| 0x7EDCDB13–0x7EDCE9B8 | Helpers. Most callers are SS_MENU_LV handlers (I: LV-menu support) |
| 0x7EDCE9B9–0x7EDD13D6 | DPS GUI helpers to 0x7EDD08D2 (the DPS screen drawer 0x7EDCED5A(n) is 5,113 B). Then the DPS and printer callbacks, `initGuiFwUp` 0x7EDD0C89 and `notifyCurrentLanguage` 0x7EDD109C |
| 0x7EDD13D7–0x7EDDBBEB | Page classes for pages 524, 423–430, 422, 434 and 523. Two larger blocks in this range: the helpers 0x7EDD7A57–0x7EDDA607, which SS_MENU_LV handlers call (I: live guide), and the methods without strings of the 423–430 class (0x7EDD1E7D, 0x7EDD2D82, 0x7EDD41C9, 4–5 KB each) |
| 0x7EDDBC06–0x7EDDBD4F | **"Return-to (SS, state)" singleton** (L1 2026-11-09): getInstance 0x7EDDBC06 (RAM 0x602BDA2C, 52 B, ctor 0x7EDDBC2E; 445 call sites in 167 functions), field set/get pairs 0x7EDDBC64–0x7EDDBD4F (+0 flag, +4 SS, +8 state, …), reset 0x7EDDBCA8. The SS_MENU_MAIN "exit" path and the page-326 key slot branch on it (13d §6.3) |
| 0x7EDDBD50 | `getLanguageLoadResource` / `loadLanguageData` |
| **0x7EDDBF31–0x7EDDD1E5** | **Self-adjust UI `userGuiSelfAdjust`.** This is the only code that uses the `[GUI-SelfAdjust]` strings. Its page object is page 523 (class 0x7EDDB051–0x7EDDBBEB) |
| **0x7EDDD21D–~~0x7EDE161C~~ 0x7EDE15ED** (L1 2026-11-09) | **GuiTouch** (§2.4). It has three parts: the action handlers 0x7EDDD21D–~~0x7EDE0383~~ 0x7EDE03CE (0x7EDE0384 is inside the last handler 0x7EDE033E (L1 2026-11-09)), the gesture listener and dispatcher 0x7EDE03CF–0x7EDE0ACF, and the common actions and context accessors 0x7EDE0AD2–~~0x7EDE161C~~ 0x7EDE15ED (L1 2026-11-09) |
| **0x7EDE15EE–0x7EDE1DD8** (L1 2026-11-09) | **USB-connect screen** (not an openPage page): getInstance 0x7EDE15EE (RAM 0x602BDF48, 172 B), ctor 0x7EDE161D (page base 0x7EDCD621, vtable 0x7EFEF47C, own slots 0/2/3), show 0x7EDE1649 (panels 82/103), callback `userGuiUsbConnectCallBack` 0x7EDE1D0A. All 14 callers of the getInstance are SS_USB handlers 0x7EDC0D90–0x7EDC156F (page-class row in the TSV) |
| ~~0x7EDE161D~~ 0x7EDE1DD9–0x7EE02094 (L1 2026-11-09) | Page classes (179 `page-class` rows; the TSV now has 180 with the USB-connect screen (L1 2026-11-09)) and their private code. The userMenuMainReset code is at 0x7EDECDC0–0x7EDED8D6, the userMenuTopMenu code at 0x7EDFDA2A, the RAW-edit private code at 0x7EDF4977–0x7EDF779B, `getListDescriptor` at 0x7EDFD9AF, and the setting wrappers at 0x7EE01D38/0x7EE01D4E |

## 2. Components

### 2.1 Menu-page framework (V)
- **`openPage(id)` 0x7EDCBE97.** Callers do not call it directly. They allocate a 4-byte functor, store the vtable 0x7EFD51D0 (byte signature `fc cc d0 51 fd 7e`) and call vt[0] with the page id (22 sites).
  - The body is three chained hash switches of `{u32 key, u32 case}`. Each switch is tried only if the one before it misses:
    1. 0x7EFE5A14: 256 entries, key = id, index `id & 255`, ids 1..651;
    2. 0x7EFE5614: 128 entries, key = id − 16, ids 17..606;
    3. 0x7EFE4E14: 256 entries, key = id − 17, ids 18..659.
  - Each case does one of two things:
    - it calls a **page getter** (191 ids, 79 getters);
    - it does `mov N,d0` → **`getListPage(N)` 0x7EDC7DBA** (313 ids). N = id, except that ids 547–551 use lists 95–99.
  - The result is stored in RAM **0x602BCF04 = current page**. Then the function calls 0x7EDCCABB(page, id) and 0x7EDCD0A3(page, 25/48/49). The value 48 is for the Custom Menu page and 49 for the 0x7EDE30E3 page.
  - Three list ids have no registry row: 185, 603 and 604.
- **`getListPage(N)` 0x7EDC7DBA.** It keeps a 50-entry cache: ids at RAM 0x602BC880, objects at 0x602BC7B8, next slot at 0x602BC8E4. On a miss it scans the **registry 0x7EFE180C–0x7EFE21CB** (312 × `{u16 list id, u16 0, create(id)}`, 101 factories) and evicts the oldest page through its slot-0 deleter.
- **Class tree.** Each page object stores its vtable at +0.
  - The grand-base is 0x7EDCCA5D (vt 0x7EFE6214, 30 slots). The **page base** is 0x7EDCD621 (vt 0x7EFE79FC, 32 slots, 96 callers).
  - Intermediate bases (the class name comes from the string just before the vtable):

  | Base ctor | Name | Vtable | Size | Users |
  |---|---|---|---|---|
  | 0x7EDC7EAA | **userCommonSecondWizard**: the generic list page. +168 = list id, +172 = list descriptor | 0x7EFE221C | 1,748 B | factory 0x7EDC7ECB: 111 registry ids (110 reachable from openPage; list 110 is not, because page 110 is the object page 0x7EDE1E3D); 28 derived classes (A8 2026-11-09) |
  | 0x7EDC8692 | userCommonTimeAdjust | 0x7EFE235C | 608 B | — |
  | 0x7EDC8AD0 | list base that logs `GetTableData() error` | 0x7EFE241C | 432 B | 26 lists, 16 derived classes |
  | 0x7EDC8F62 / 0x7EDC9231 / 0x7EDC9669 | other list bases | — | — | — |
  | 0x7EDED9DD | userCommonWizard1NRightAligned | 0x7EFFE768 | 1,756 B | the play/edit wizards |
  | 0x7EDEE169 | userCommon1CNLWizard | 0x7EFFEA34 | 1,744 B | — |
  | 0x7EDFFB83 | — | 0x7F00F600 | — | — |
  | 0x7EDCCA5D (direct) | main-menu tab page 0x7EDEB923 (pages 1–7) ~~and 0x7EDE1649~~ (0x7EDE1649 is the show method of the USB-connect screen, whose ctor 0x7EDE161D calls the page base 0x7EDCD621 (L1 2026-11-09)) | — | — | — |

- **Page-base slots** (vt 0x7EFE79FC):

  | Slot | Role | Basis |
  |---|---|---|
  | 0 | dtor | V |
  | 2 (+8) | enter/redraw(d0 = mode byte). 113 call sites through the current page | V |
  | **3 (+12)** | **key(d0 = page key code, d1 = parameter)**. 84 call sites. Returns 0 = not handled and 1 = handled; Edit › Aspect returns 1 for MENU and 2 for OK; 3 = "exit menu" (Firmware) | V for the call sites; I for the meaning of the return values |
  | 4 | 0x7EDCCCC9 → 0x7EDCCCD8(d0, d1, 1), 29 callers | V; role I |
  | 8–11 | event stubs; 10 and 11 return 0x104 = BLACK_SCREEN | V |
  | 15 | MediaCtrl vt+4 = 4 → 0x104 | V |
  | 18/19 | call slot 29 (+116) | V |
  | 27/28 | cursor in data-model block 57 (1,564 B) | V |
  | 30 | copies 234 bytes to 0x7EDCBBCD | V |

  The list page adds slots 32–44. Slot 43 = 0x7EDC85E7 stores `getListDescriptor(+168)` at +172.
- **Page key codes** (V from the Ss handlers, `keys.txt`):

  | Code | Key or event |
  |---|---|
  | 0 / 1 / 2 / 3 | UP / DOWN / LEFT / RIGHT |
  | 4 / 5 | OK / MENU |
  | 7 / 8 | shutter half / full |
  | 9 | PLAY or INFO (I) |
  | 10 | MOVIE (d1 = 0 on) |
  | 13 | warning |
  | 14 | OK long (14e) |
  | 17 / 18 / 21 / 24 | expansion / INDEX / DELETE / Fn2 |
  | 23 / 25 | 1 s / 10 ms wizard timers |
  | 26 | END_DIRECT 0x9AB8 (SS_MENU_MAIN state 4 handler 0x7EDB0EDA) and END_ART_MENU 0x9AC3 (state 7 handler 0x7EDB00BE): both call the page key slot with d0 = 26. The ART BKT On/Off pages (key slot 0x7EDFE82D) store the selected row on code 26 (L1 2026-11-09) |
  | 27 / 28 | POPUP / mode dial |
  | 11 / 12 | dials, with the count in d1 (I, C3 F066) |
  | 6 | INFO release or dial (I) |

- **`getListDescriptor(N)` 0x7EDFD9AF.** It searches 312 × `{u16 list id, u16 pad 0, u32 desc}` (8-byte entries) at **0x7F00D710**. (A8 2026-11-09)
  - Descriptor: `{u16 info id, u16 item count, u32, u32, u32 items}`. Each item has 28 bytes: `{u16 kind, u16 label, …, +12 info or 2000, +16 value, +20/+22/+24 guide string ids}` (V layout).
  - **The info id ties a list page to its setting (V).** Examples: list 167 → info 162, items P/A/S/M, Custom Menu label "@A00C@ Mode"; 101 → info 98, Full-time AF Off/On; 104 → 81, Reset Lens; 169 → 102, Movie mic. The TSV page rows give the info id and the matching Custom Menu label (I as a title).
- **Data-model blocks seen here (V for the writes).**
  - block 16 (12 B) = guide-bar labels, written by **`setGuide(d0, d1, a1)` 0x7EDCCEB8** (103 callers; string ids such as 194 "Cancel" and 197 "Set");
  - block 57 = list content;
  - block 76 = Firmware screen record;
  - block 59 = LV bar;
  - blocks 87/88/90 = BT wizard texts.
- **Titles (I).**
  - The sub-item table group (13d §5) equals a page id for 38 pages. Its title field gives, for example, page 9 "Reset/Myset" and page 10 "Picture Mode".
  - For list pages, the title comes through the info id (above).
  - Singleton pages write their own record. Page 43 puts 134 "Firmware" first in block 76.

### 2.2 Page index (TSV `page N`, `page-class` rows)
504 page ids resolve: 191 to singleton/object getters and 313 to list ids. They resolve to 180 classes (179 class code ranges). Each `page-class` row gives the code range ~~[lo, end of the last own method]~~ [lo, end), where `end` is **exclusive**: in 179 of the 180 rows it is the start of the next class (its ctor; e.g. 0x7EDC8AD0 is the next class's ctor, not part of the pages-639 class 0x7EDC8692) (D4 2026-11-09), ctor, vtable, slot count, base, own slots, panels shown (ShowPanelEx immediates in its own code), OlyApi interfaces called and the first string.

**Byte signatures (V).**

| Part | Bytes | Instructions |
|---|---|---|
| Singleton getter | `fc a0 RAM ; b0 00 ; c9 .. ; 2c SIZE ; dd → 0x7EBA62DB ; … cd → ctor ; fc 81 RAM ; fc a0 RAM ; df 00 04` | `mov (RAM),a0 ; cmp 0 ; bne ; mov SIZE,d0 ; call new ; call ctor ; store ; reload ; ret` |
| Page ctor | `dd → 0x7EDCD621 ; fc cc VT ; 60 ; df 00 04` | — |
| Page dtor | `f8 fe fc dd → 0x7EDCD664 ; 90 00 ; df 00 04` | — |
| List factory | `mov SIZE ; call new ; call ctor(d0 = list id)` | — |

**Known examples placed (V unless marked).**

| Page(s) | Class (getter → ctor, vtable) | What it is |
|---|---|---|
| 43 | 0x7EDFD804 → 0x7EDFD833, 0x7F0052AC (172 B) | **Firmware version** (see the notes below) |
| 346–349 | 0x7EDEA9D7 → 0x7EDEAA06, 0x7EFFDDB8 | Edit › Aspect. Panel 58; key 0x7EDEAA4D |
| 472, 473, 506, 508 | 0x7EDE893E → 0x7EDE896D, 0x7EFF7D80 (1,184 B) | Text page. Panel 106; dial translator 0x7EDE8A19 |
| 511 / 513 | 0x7EDE437F / 0x7EDE4632 (168 B each) | P2S / S2P all-image transfer: MediaCtrl vt+44 = `transferImageAll` (name id 0x10C12) with (2,4) / (4,2); panel 4. **I:** a PENPAL album ↔ card copy (C3 F065; which medium is 2 and which is 4 is not proven). The sibling pages 515, 519, 521 and 493 are also 168-B MediaCtrl pages (A8 2026-11-09) |
| 466 | 0x7EDFB664, vt 0x7F004DC0 | `userMenuRec2_CompScale`. Panel 64; moveCurrent 0x7EDFB968 |
| 261 | 0x7EDEFCB6 | `userMenuPlay_CompScale` |
| 262 | 0x7EDF2164 | `userMenuPlay_ImageCompose`. **Not** BT wizard screen 262 (§2.5) |
| 25–34 | 0x7EDE9AA6 | Custom Menu A–J |
| 1–7 | 0x7EDEB923 | Main-menu tab pages, shown on GCPnl_Menu (panel 80) |
| 620/621 | — | RAW Data Edit |
| 625/626 | — | BGM item and import list |
| 611–624 | — | EditRaw pages |
| 323–365 | — | One small page per Edit function. The classes call EditColor, EditRedEyeAdjust, EditResize, EditShadowAdjust, EditTrimming and EditBeautyAdjust |

Notes on page 43 (Firmware):
- slot 2 0x7EDFD858 → 0x7EDFD8E6 writes block 76 = {134 "Firmware", versions from Maintenance vt+16 with d0 = 1, 6, 10, 8};
- key slot 0x7EDFD86F: key 10 with d1 = 0 sets the flag +168, and any other d1 clears it; OK returns 3 only if the flag is set **and** `IOlyApiMaintenance` vt+40 = 1. vt+40 is `Maintenance::canUpdateFirmwareCard` (name id 0x4040C); (A8 2026-11-09)
- the C3 F061 handler (SS_MENU_MAIN.4, OK-off) then pops the nav stack.

### 2.3 Panels (TSV `panel` rows, V)
Each numbered panel's ctor range comes from the CreatePanel case table (13d §3). "Shown by" lists the owners of the `ShowPanelEx(n)` immediate sites: a page class, an Ss super-state or a CPlay* controller. Examples:

| Panel | Shown by |
|---|---|
| 4 (type 0x6004) | CCommon `setDbWarningInfo`, SS_USB and many pages (I: the generic message/busy panel) |
| 6 | SS_COMMON BLACK_SCREEN |
| 10 (0x600A) | SS_REC OSD_OFF; it has a touch table (I: the live-view shooting screen) |
| 24 | Firmware page |
| 25 / 26 | SS_MENU_LV live-guide top / LV bar |
| 50 / 51 | CPlaySingleFrame code 0x7ED05642, 0x7ED083AD, 0x7ED0B25D, 0x7ED0B7E0 / 0x7ED0C0FD |
| 53 / 54 | SS_PLAY_INDEX index / calendar |
| 80 / 81 | menu tabs / Custom Menu |
| 85 | pages 9–11 and the list pages 136/528 |
| 106 | text page |
| 112 / 113 / 116 | BT wizard |
| 147 / 148 | HIDE_MODE pages and Custom Menu |
| 150–159 | debug menu and self-adjust |

~~The 16 unnumbered panel classes sit inside the ranges of their numbered neighbours.~~ The 16 unnumbered panel classes all follow GCPnl_Zoom (panel 55, 0x7ED7932E–0x7ED7A79E). Their ctors (type: ctor) are 0x605B: 0x7ED7A79F, 0x605D: 0x7ED7B07A, 0x6062: 0x7ED7B250, 0x6008: 0x7ED7B4B3, 0x6060: 0x7ED7B8CC, 0x605E: 0x7ED7BBEB, 0x605C: 0x7ED7BE74, 0x6003: 0x7ED7C0C5, 0x6007: 0x7ED7C5B7, 0x601E: 0x7ED7C93E, 0x6033: 0x7ED7E21A, 0x6070: 0x7ED7E533, 0x605F: 0x7ED7E77B, 0x6061: 0x7ED7E98D, 0x6001: 0x7ED7ED04 and 0x6071: 0x7ED7F445; the last class ends at 0x7ED7F6D4. Each is created by type through the factory table 0x7EF0F3B0 (V: each factory entry calls its ctor) (D4 2026-11-09).

### 2.4 GuiTouch (V; corrects 13d §1 and C3 F064)
1. **Binding.** ShowPanelEx 0x7EDC5D2D calls 0x7EDCBA98(panel no.), which looks the panel up in **0x7EFE42EC** (16 × `{u16 panel, u16 type, make, RAM descriptor}`). The 16 touch panels are 10, 11, 12, 13, 14, 17, 18, 19, 23, 24, 25, 26, 27, 29, 30 and 66; 17 and 18 share one descriptor. On a match:
   - it replaces the **gesture listener** at RAM 0x602BCDC4. The listener is made by 0x7EDE03F3 and is a 4-B object with vt **0x7EFEEF04**. Its slots: 1 TOUCH 0x7EDE040E, 2 LONG TOUCH 0x7EDE0482, 3 RELEASE 0x7EDE053F, 4 TAP 0x7EDE05F9, 5 DOUBLE TAP 0x7EDE06A5, 6 SLIDE 0x7EDE0751, 7 doTouchAction 0x7EDE07AA;
   - it creates or updates the 44-B **GuiTouch context** at RAM 0x602BCDC8 (ctor 0x7EDE085B; 0x7EDE0975 stores the descriptor).
2. **Delivery.** The app-window handler 0x7ED1BEE2 (0x7ED1C38D–0x7ED1C4B7) works as follows:
   - If the context's panel is the current panel, it calls listener slot *gesture* (1–6), then `PostEventToCA(23, result)`.
   - Otherwise it calls CTouchPnl's `Touch Main Loop` 0x7ECED947. That function handles live-view touch: it calls 0x7ECEDB53 and the **touch-mode dispatcher 0x7ECEDEB6** (C3 F053; a switch on the touch object's byte +52, cases 1–15, table 0x7EEF50E8, which posts `PostEventToCA(23, 27/39)` or EVT_REC_REFRESH 0x971D).
   - So **CA code 23 = "GUI touch result"** (V for the call; I for the name).
3. **Descriptor** (RAM, in `.data`; ROM = RAM + 0x1E6304C0): `{+0 area-table array (one per sub-screen), +4 map array (one per gesture pattern), +8 action-handler table, +12 u16 first area id, +16 optional update fn}`. The layout is V from the bytes. The use is V for +8 (0x7EDE0970 → `mov (8,a0),a0` → `handlers[a]`) and for the first-area subtraction; the other field names are I.
   - Area tables: 10-byte rects `{x1, y1, x2, y2, u16 area}` in 720×480 coordinates, ended by area 0xFF.
   - Maps: `{u16 area, u16 action}`, ended by 0xFF.
   - In the handler table, slot 0 = **0x7EDE12C5, "no action"**.
4. **doTouchAction 0x7EDE07AF** loops on **getTouchActionIndex 0x7EDE0983**, which hit-tests through 0x7ECFF6A6 and reads `map[pattern][area − first]`:
   - 255 → result 25 (no action), stop;
   - 254 → the common action 0x7EDE0AD2;
   - otherwise → `handlers[a](a0 = &result, point)`, until a handler returns ≠ 0.
   - Handlers end `mov N,d0 ; mov d0,(a2) ; mov 1,d0 ; ret`, where N = 27 (handled) or 25 (none).
5. **Handler tables and events (69 TSV `touch-action` rows):**

   | Panel | Handlers | Events and data |
   |---|---|---|
   | 10 | 12 handlers 0x7EDDEC28–0x7EDDF527 | EVT_REC_REFRESH 0x971D, data model 31/98, CA (13,3) |
   | 11 | 0x7EDDFB7C | — |
   | 12 | 0x7EDDFC2E–0x7EDDFE29 | — |
   | 13 | 0x7EDDF5AA–0x7EDDF96B | — |
   | 14 | 8 handlers 0x7EDDD498–0x7EDDDA8F | data model 63; synthetic OK 0x900C / MENU 0x900E |
   | 17/18 | 0x7EDDFF2B–0x7EDE01FE | `touchPanel_Scn_Art_Wiz_Change_Page`, EVT_GUI_SCP_REFRESH 0x9A45 |
   | 19 | 0x7EDDD22C/0x7EDDD33A | block 40 |
   | 23 | 0x7EDDEBB2 | `PostEventToCA(7,0)` |
   | 24 | 0x7EDDEA16–0x7EDDEB21 | MENU/OK keys |
   | 25 | 0x7EDDDAFC–0x7EDDDDBF | block 58 |
   | **26** | **12 handlers 0x7EDDDE22–0x7EDDE967, table 0x7EFE4058** | **EVT_LVBAR_CHG_VALUE 0x9ACB** (1–3), **EVT_LVBAR_CHG_BAR 0x9ACA** (4, 5, 8, 9), block 59 (6, 7), MENU (10), OK (11), INFO_OFF 0x9015 (12). C3 F064 = handler 2 |
   | 27 | 0x7EDDD3FC | — |
   | 29/30 | 0x7EDE029E/0x7EDE033E | 0x9A45 |
   | 66 | 0x7EDDD3B2 | — |

   - The LV-bar handlers keep their state at RAM 0x602BDCFC (item) and 0x602BDCFE (level).
   - **0x7EFED8F4 holds a copy of the panel-26 set, not of a longer table.** Its first 13 words (slot 0 + the 12 handlers) equal 0x7EFE4058 word for word, and the area tables and maps before it (0x7EFED634–0x7EFED8F3) equal panel 26's 0x7EFE3D98–0x7EFE4057 byte for byte. From the 14th word on, the bytes differ (0x7EFE408C starts other rect data; 0x7EFED928 is zeros). No reference to 0x7EFED8F4 was found (raw byte scan of block 0). Its area tables 0x7EFED634/0x7EFED6D4 are pointed to from `.data` 0x7E8EE180 (RAM 0x602BDCC0), not from the panel table (I: unused or second copy). (A8 2026-11-09)
6. **checkSlideAreaPos 0x7EDE13B4** (35 callers, all in 0x7EDDD22C–0x7EDE033E) rejects a slide that leaves its area. The context accessors 0x7EDE1448–~~0x7EDE161C~~ 0x7EDE15ED (L1 2026-11-09) are 17–47-byte "get context 0x7EDE12CF (253 callers), then store" shapes.

### 2.5 BT wizard screens (V; corrects C3 F059's "page 262")
`userGuiBTWizard::init(d0)` 0x7EDCABE2 takes a **wizard screen id 256–265**. This id space is separate from menu page ids.

| Screen id | Panel | Data-model block | Notes |
|---|---|---|---|
| 256 | 116 | 90 (70 B) | device list (Bluetooth vt+100) |
| 257–261 | 112 | 88 (8 B) | — |
| 262–265 | 113 | 87 (24 B) | — |

- Show 0x7EDCBC44 (57 callers) writes the blocks and calls ShowPanelEx.
- SS_BTSEND uses: 17 PAIRING_SEARCH → 262; 22 PAIRING_BUSY → 264; 31 RESTART_BUSY → 263; 26 PAIRING_NG → 258; 28 PAIRING_OK → 256; 3/10 MAKE_NG/NG → 257.
- SS_BTRECEIVE uses: 1 → 259; 3/16/17 → 265; 5/9 → 264; 14 → 260/261.

### 2.6 Ss state → screen (TSV `SS_x.n` rows: the entry fn at descriptor +20, scanned 2 call levels)
| SS | What the entries show (V) |
|---|---|
| SS_COMMON | 4 BLACK_SCREEN → panel 6 |
| SS_REC | 3 OSD_OFF → panel 10; 1 DIRECT_PREPARE → CA(14,3) |
| SS_MENU_MAIN | 1 TOP_MENU → panel 24 (I: `userMenuTopMenu` 0x7EDFDA2A); 2 TAB / 3 LIST → main-menu page + panel 80 + openPage; 6 HIDE_MODE → panels 147/148 (14e §4.4) |
| SS_MENU_LV | 6 GUIDE_TOP → 25; 7 GUIDE_BAR → 26 (LV-bar touch); 8 HINT → 14; 9 ANIMATION → 25; 10 → WB-compensation page 243… + panel 96 |
| SS_PLAY_INDEX | 6 INDEX_DISPLAY → 53 GCPnl_Index; 8 CALENDAR_DISPLAY → 54 GCPnl_Calender |
| SS_PLAY_MOVIE_SLIDE | 19 3D_INDEX → 53. Other states draw through the CPlay* controllers (panels 50/51 from 0x7ED05642…; I) |
| SS_PLAY_SINGLE | entry fns call the CPlaySingleFrame/OlyApi layer, outside the scan; panels 50/51 (I) |
| SS_SELFADJ | 1 → 151, 2/7 → 153, 3/8/9 → 154, 4 → 152, 5 → 158, 6 → 159 |
| SS_DEBUGMENU | 1 → 150 (debug list), 2 → 155, 3 → 156, 4 → 157 |
| SS_USB | 1 USB_MENU / 3 MEDIA_SETUP → 103; 5 PRINT_SEL → 4; 6 → CA(17) |
| SS_DPS | entries at a 15-byte stride from 0x7EDA09EC each call the DPS drawer 0x7EDCED5A(n): 2→8, 3→14, 9→21, 10→2, 11→4, 12→22, 13→23, 14→1, 15→3, 16→5, 17→20, 18→6, 19/20→11, 21→7 |
| SS_BTSEND / SS_BTRECEIVE | §2.5 |
| SS_SPC (17) | 15 states; entries self-post 0xA501/0xA502 only (no screen found) |

### 2.7 Viewer of Actuator/Viewer registry ids 8 and 9 (V; C3 F062)
- Creators 0x7EDC288E (+1600 = 0) and 0x7EDC28AF (+1600 = 1) build the same 1,604-B object, vt 0x7EFDA378.
- Update (slot 0) 0x7EDC28FB reads data-model blocks 0/16/48, runs three member pointers (set by the static init 0x7EDC2B3A: 0x7EDC29C6, 0x7EDC29D5, F062 0x7EDC2AF6) and calls ShowPanelEx(61). F062 writes the guide ids 194/197 ("Cancel"/"Set") into block 16.
- All 31 registry creators are in the TSV (`registry N`).

### 2.8 Layer-ordered child insertion (V; C3 F054)
**0x7ECF1D00 is slot +544 of the screen class 0x0101** (vtable word 0x7EEF5740 = 0x7EEF5520 + 544); its direct entry is 0x7ECF1D05. It works as follows:
- If vt+680 returns 1, it counts the children whose layer (vt+320 → u16 +30) is ≤ the new child's layer and inserts the child at that index (0x7ECF2C74 → list insert).
- Otherwise it appends the child through the +416 list's vt+428.

The caller 0x7ED2533C is called by the app-window methods 0x7ED1A6EA (panel holder, 14e §2.5), 0x7ED1A9D2 and 0x7ED1AC8C. So panel holders are kept in layer order (I: z-order of the 1/2/3 panel layers from the resource record).

## 3. How to classify a new function here
1. **Address in 0x7ED37DAA–0x7ED82275:** find the `panel` row by range.
   - 14e §5 gives the panel shapes: ctor, OnNotify, child builder (+424) and draw.
   - The panel's role comes from the "shown by" column.
2. **Address in a `page-class` range:** the function is a method of that page. Check the vtable:
   - vt+8 is enter/redraw and vt+12 is key;
   - own slots ≥ 32 belong to the list bases;
   - a non-vtable function in the range is a private helper of that page.
3. **Address in 0x7EDDD21D–~~0x7EDE0383~~ 0x7EDE03CE (L1 2026-11-09):** find the `touch-action` row.
   - Signature: `cf ..` prologue; it reads the GuiTouch context (0x7EDE12CF) and calls a context setter 0x7EDE14xx/15xx;
   - it often calls checkSlideAreaPos 0x7EDE13B4;
   - it ends with `mov 27|25,d0 ; mov d0,(a2) ; mov 1,d0`.
4. **Ss handler or entry:** see the `SS_x.n` rows and 13d §4.
5. **Otherwise** use the `region` rows.

## 4. Corrections
1. **13d §1:**
   - "the self-adjust UI 0x7EDD8–0x7EDDF" is wrong. Self-adjust is 0x7EDDBF31–0x7EDDD1E5, plus the page-523 class 0x7EDDB051–0x7EDDBBEB.
   - **GuiTouch** is 0x7EDDD21D–~~0x7EDE161C~~ 0x7EDE15ED (C3 F064; end (L1 2026-11-09), C4 F066: 0x7EDE15EE is the USB-connect screen getInstance).
   - The "menu pages from ~0x7EDE0000" row is wrong. Page classes run from 0x7EDC7EAA, interleaved with the components of §1.
2. **13d §5:** the menu-page registry is **0x7EFE180C–0x7EFE21CB, 312 entries, 101 factories**, keyed by **list id**, not 0x7EFE190C / 280 / 90.
   - Page ids go through openPage's three hash tables, **0x7EFE5A14 / 0x7EFE5614 / 0x7EFE4E14**.
   - C3 review 4's "hash table 0x7EFE1914" is wrong.
   - ids 547–551 map to lists 95–99.
3. **C3 F059:** "page 262" is a **BT wizard screen id** (panel 113). Menu page 262 is `userMenuPlay_ImageCompose`.
4. **C3 F064:** the live touch-action table is 0x7EFE4058, reached through the panel-26 descriptor. 0x7EFED8F4 holds a copy of the 13-word handler table (and of its area tables and maps); the words after those 13 differ, and no pointer to it was found. (A8 2026-11-09)
5. **C3 F053:** CA code 23 is the touch result sent after every panel touch action (0x7ED1C489), as well as the result of the touch-mode dispatcher.
6. **14e §4.3:** "registry 0x7EFE190C" should read 0x7EFE180C. The rows for 620/621 at 0x7EFE2114 are inside it.
7. **13d §3 name list:** add the class names found here:
   - userCommonSecondWizard 0x7EDC7EAA;
   - userCommonTimeAdjust 0x7EDC8692;
   - userCommonWizard1NRightAligned 0x7EDED9DD;
   - userCommon1CNLWizard 0x7EDEE169;
   - userMenuMainReset code 0x7EDECDC0–0x7EDED8D6;
   - userMenuTopMenu 0x7EDFDA2A.

## 5. Open questions
1. Titles of most singleton pages. They are written as records into data-model blocks. The menu-item → page link (the item field that names a target page) is not decoded, so the "title = parent item label" join was not made.
2. The roles of pages 423–430 (three large methods without strings, panel 20) and of the LV-menu helpers 0x7EDD7A57–0x7EDDA607 (I: live guide).
3. Whether the second touch-table set (0x7EFED518–0x7EFED924, `.data` 0x7E8EE148–0x7E8EE1DC) is ever used.
4. The meaning of the page key return values (1/2/3) and of base slot 4.
5. The SS_PLAY_SINGLE / SS_PLAY_MOVIE_SLIDE screens: they need a scan of the CPlay* controllers 0x7ED0xxxx.
6. The gesture pattern → map index (6 maps, 7 per-pattern flags per descriptor; the order is assumed to follow the listener slots).
