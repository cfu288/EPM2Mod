# 14e. GUI toolkit and GUI app: per-method roles (E-PM2 v1.6, round D2)

Scope: the GUI code 0x7ECCB800–0x7EE02094, method by method. This section builds on 07 (menus, settings) and 13d (classes, panels, Ss engine). It answers coverage C2 (round2-review3 F055–F058, "weakest area 4"; round2-review4 F061–F065, "weakest area 3") and audit A5 (check-13b-2 rows 13d-64 and 13d-125).

- **Labels:** **V** = verified (read in code or bytes); **I** = inferred.
- **Addresses:** runtime addresses. "vt+N" = the virtual at byte offset N, which is slot N/4.
- **Scratch:** `$S/d2/gui/`. It holds `g.py` (bytes and disassembly helpers), `slots.py` / `desc.py` / `classify.py` (vtable dumps), `classes.txt` (class × slot dump), `wbase.txt` (widget base slots), `bt.txt` (Bluetooth table), `lvtab.txt` (live-view element table), `pf*.txt` (DC layer), `rot.txt`, `helpers.txt`.
- **MN103 entry rule (V):** a method often has two entries. The vtable entry is the `movm` prologue, and direct calls enter 2–5 bytes later, because `call target,[regs],N` saves the registers itself. Examples: container DeleteAllChildren has the vtable entry 0x7ECF3388 and the direct entry 0x7ECF338D (C2 F055). setText has 0x7ED2D50B and 0x7ED2D510. fwmap often splits such a method into a 5-byte stub and a body.

## 1. Area and boundaries (changes to 13d §1 only)

| Range | Contents | Basis |
|---|---|---|
| 0x7ECEE1D5–0x7ECF4C67 | Root class 0x0001 (0x7ECEE1D5–~0x7ECEF64E), GUI data model (0x7ECEF64F/0x7ECEF667), screen 0x0101, sub-screen 0x0102, child-list class (0x7ECF2AB5–0x7ECF2C20), container 0x0100 (0x7ECF3083–0x7ECF4C67) | V, ctors and vtables |
| 0x7ECF4C68–0x7ECF5450 | Widget base 0x8000 (143 slots, §2.2), including the frame-animation engine 0x7ECF50C8–0x7ECF5441 | V |
| 0x7ECF5451–0x7ECF6BDB | D-part and C-part bases, class 0x0104 (§2.5) | V |
| 0x7ECF6BDB–0x7ECFE7B7 | Renderers: text and bitmap blits, fills, shapes (§3.2) | V call graph; I roles |
| 0x7ECFE7B8–0x7ECFEF32 | **Graphics context (DC) and pixel-format layer** (§3.1) | V |
| 0x7ECFEF32–0x7ECFF982 | Geometry and resource helpers: rect/point (13d §2.2), GUI pool 0x7ECFF1D8/0x7ECFF1E4, resource lookup 0x7ECFF3AC/0x7ECFF3C3/0x7ECFF3E9, a 12-byte helper class at 0x7ECFF962 (vt 0x7EEF66AC) | V |
| **0x7ECFF983–** | **`CCommon` starts here, not at 0x7ED00000.** The ctor is 0x7ECFF983 (a 300-byte object). getInstance is 0x7ECFFAC6 (RAM 0x602B6038, **775 callers**). Then come `setDbWarningInfo` 0x7ECFFB4C, `doHdmiConnectChange` 0x7ED001E8 and `setOutputType` 0x7ED00250 | V strings and code |
| 0x7ED98B95–0x7ED9EED6 | Live-view display elements: a static initialiser and 77 element methods (§4.2) | V |
| 0x7EDC17FB–0x7EDC1B36 | Widget helper layer (§2.7). Next comes 0x7EDC1B37 (1,333 B, to 0x7EDC206B) | V |
| 0x7EDCB0C5–0x7EDCB1E0 | Bluetooth callback dispatcher and its 3 matchers (§4.1) | V |

## 2. Widget toolkit: classes and slots

### 2.1 Root slots (vtable 0x7EEF5328, 104 slots). Fields: +4 type, +6 id, +8..+14 x/y/w/h, +16 status, +20 parent, +24 handler, +28/+29 pool, +30 layer, +40 plane mask, +44 paint state, +46/+48 refresh rect, +64 layout table
| Slot (+off) | Role | Basis |
|---|---|---|
| 0 (+0) | **Destructor.** It returns a0 = **0x7ECEEFC3** (GUI-pool delete: it reads the pool bytes through vt+248 and calls 0x7ECFF1E4). The caller then does `mov (a0),a1 ; mov (a1),a1 ; calls (a1) ; mov a0,a1 ; calls (a1)`. Byte signature: `fc dc c3 ef ce 7e` (`mov 0x7ECEEFC3,a0`) just before `ret`, at 149 sites in the GUI region | V. 13d §2.3 says "returns a constant (class info)"; that is wrong |
| 1–10 | type, id, x, y, w, h getters, and point/size as a point (0x7ECFF349) | V |
| 11 (+44) | **setRect(a1 = {x1,y1,x2,y2})**. It stores x, y, w, h (w and h are clipped to 32767) and moves the pending refresh rect +48 by the same delta | V |
| 12 / 13 (+48/+52) | getRect, returned by value / written to a1 | V |
| 14–16 | client rect (0, 0, w−1, h−1) | V |
| 17 (+68) | screen rect: adds the parent offsets up the +20 chain | V |
| 18 (+72) | get the status word +16 | V |
| 19–28 | Status-bit pairs (set, test): bit 1 visible (+76/+80); 2 enabled (+84/+88); 4 (+92/+96); 8 (+100/+104, the setter invalidates); **16 = focus** (+108/+112) | V. For bit 16, see slots 55/56 |
| 29/30 (+116/+120) | setStatusBits(d0 = mask, d1 = on) / testStatus(mask) | V |
| 31–34 | parent +20, handler +24 (set/get) | V |
| 35/36 (+140/+144) | Import / export properties. Import reads the resource record at a1; export writes the fields to a1 | V for the data direction; the names are I (GM_IMPORTPROPERTY 0x1009, EXPORTPROPERTY 0x100A) |
| 37/38 (+148/+152) | OnCreate / OnDelete | V (§2.2) |
| 39/40 (+156/+160) | OnPaint (asks app-window vt+680, then calls OnDraw) / OnDraw | V |
| 42 (+168) | invalidate(d0 = mode, a1 = rect or 0). Mode 1 is used before a move and mode 2 after it (§2.7) | V for the use; the mode meaning (erase / draw) is I |
| 43–51 | Pointer events: +172 → +176 (move), +184 → +188 (press), +196 → +200 (release) | V |
| 52/53 (+208/+212) | key press / key release | V |
| 55/56 (+220/+224) | **OnSetFocus / OnKillFocus.** OnSetFocus calls vt+108(1) on itself and sets bit 16 on **every ancestor**. OnKillFocus clears bit 16 on itself and on every ancestor | V (0x7ECEEE9D, 0x7ECEEED6) |
| 57/58 (+228/+232) | OnTimer(id) / OnUser | V |
| 61/62 (+244/+248) | set/get the pool bytes | V |
| 63 (+252) | **selectLayout(i = 0..3)**: copies rect i of the 4 × 8-byte table at +64 into x/y/w/h | V |
| 64–68 | bit 0x2000 (+256/+260), bit 0x1000 (+264/+268); +272 (0x7ECEF036) clears both (vt+264(0), vt+256(0)) and then zeroes the +40 plane-mask dword (`clr d0; mov d0,(40,a2)`) (A6 2026-11-09) | V |
| 75–78 | Bits of the plane mask +40: (1 << (k−1)) and (0x10000 << (k−1)) | V; the "plane" name is I |
| 79/80 | layer u16 +30 | V |
| 101 (+404) | hit test: gets a rect through its own OnMessage(0x1301), then tests the point | V for the structure |
| 102 (+408) | OnMessage (13d §2.3) | V |
| 103 (+412) | **OnNotify(d0 = code, d1 = child id, a1, stack)**: the per-class notification map (§5, shape E) | V |

### 2.2 Widget base 0x8000 (vtable 0x7EEF5D18, 143 slots)
The widget base adds widget behaviour to the root slots (V, `wbase.txt`):
- **Notify (+564, slot 141).** It sends `parent->vt+412(code, this->id, a1, …)` and returns −1 when there is no parent.
- **Pointer and key handlers.** They post the toolkit callbacks through +564, as `GM_CB_*` messages (names from the table at 0x7EFDFDA8):

| Handler | Callback posted |
|---|---|
| +176 move | 0x1803 CB_ONMOUSEMOVE |
| +188 press | 0x1804 CB_ONPRESS |
| +200 release | 0x1805 CB_ONRELEASE, then 0x1806 **CB_ONCLICK** if the release point is inside the widget (vt+404) |
| +208 / +212 | 0x1807 / 0x1808 KEYPRESS / KEYRELEASE |
| +220 / +224 | 0x1809 / 0x180A SETFOCUS / KILLFOCUS |
| +228 OnTimer | 0x180B. For timer id 0xFFFF it first runs the animation tick +556 |
| +232 | 0x180C ONUSER |

- **OnCreate +148:** root create. It starts the animation if +88 is set. If the key-target flag +68 is 1, it calls `parent->vt+468(this)` (register with the parent). Then it posts 0x1800 CB_ONCREATE.
- **OnDelete +152** is the reverse: stop the animation (+492), `parent->vt+472(this)`, root delete, post 0x1801, then 0x7ECE7FBE (I: purge the queued messages for this object).
- **OnDraw +160 (0x7ECF4DA2).** If status bit **0x20** is clear, it calls **slot 142 (+568) = DrawSelf(a1 = paint info)**. In all cases it then posts 0x1802 CB_ONDRAW. **Status bit 0x20 = "owner-drawn / skip DrawSelf"** (V for the code; the name is I).
- **Paint info:** `paint+8` = the DC (0x7ECF58B2 is `mov (8,a0),a0`, 84 callers).
- **Slots 104–140 (fields):** +80/+84 pointers; +76 byte (its setter invalidates); +69; **+68 key-target flag** (+448 registers or unregisters with the parent's +124 list, §2.4); +120/+124 pointers; +88..+112 the **frame-animation block**.
- **Frame-animation slots (V for the code; the role names are I):** +88 enable; +104 state (0 stopped, 1 running, 2 paused); +488/+492/+496/+500 start/stop/pause/resume (start sets the state, calls `parent->vt+476(this)` to join the timer list, stores the tick time 0x7ECE80B5 at +112 and invalidates); +92/+96/+100/+102/+108 parameters; +556 tick; **+512 = NextFrame** (the tick calls it, and a 0 result makes the tick post a notification); +560 "more frames" (1 in the base). The callbacks are probably 0x180F CB_ONNEXTFRAME / 0x1810 CB_ONSTOPFRAME (I).

### 2.3 Class × slot table (V: `classes.txt`; "own" = slots after 142)
DrawSelf is +568; "base" = the slot is not overridden.

| Class | Size, slots | DrawSelf +568 | Other overrides | Own slots (fields) | Role |
|---|---|---|---|---|---|
| 0x8001 | 128, 143 | base (empty) | +148/+152/+160/+176…+232 are **thunks** to the base bodies | none | plain widget (V that it adds nothing) |
| 0x8002 | 260, 175 | 0x7ED1CC1E (272 instructions: resource lookup 0x7ECFF3E9, slanted fill 0x7ED31C79) | +512 0x7ED1D3C8, +188, +200, +228, +384, +404, focus +108 0x7ED1D326 | four 16-byte blocks +128/+144/+160/+176, u16 +192/+194, a 24-byte style +196 (C1 F063), bytes +220..+225 | I: a multi-state graphic control (4 state blocks) |
| 0x8003 | 300, 164 | 0x7ED2952F (418 instructions) | +512 0x7ED29AB3; no pointer or key override | count +131, index +132, values +140, items +172 (13d) | item list / selector (13d) |
| 0x8004 | 156, 149 | 0x7ED27095 | +512 0x7ED272CD | u16 +128, +130 (set and redraw), struct +132 | I: image by resource id |
| **0x8005** | 204, 195 | 0x7ED2DF2F (446 instructions) (A6 2026-11-09) | **key press +208 0x7ED2E94C** (508 instructions, 1,125 B to `ret` 0x7ED2EDAE; fwmap splits it into 0x7ED2E94C (5 B) + 0x7ED2E951 (A6 2026-11-09); UTF-16 helpers), +216, focus +108 0x7ED2F562 (reselects the image) | **images +160 normal / +164 focused / +168 disabled**, picked by 0x7ED2E363. u16 +128/+130/+186/+188, bytes +184/+190, 24-byte +136, dwords +176/+180, caption buffer +192 (UTF-16; max length +172, default 32; length +200; slot 188 returns both), second buffer +196 (A6 2026-11-09), **status bits 0x10000–0x1000000** (slots 161–178), text layout slots 185/186 | **Captioned image button / text field.** Bit 16 (focus) selects the image; vt+88 = 0 (disabled) selects +168. Bit **0x1000000**: DrawSelf draws the caption as `*` × length, a **password mask** (V, 0x7ED2E070). Bit **0x10000**: when the widget is not focused, DrawSelf rebuilds the caption with 0x7ED2F453, which uses the UTF-16 digits `0123456789` at 0x7EF146DC (I: a numeric display mode). C2 F058 is slot 163, the 0x10000 setter |
| 0x8006 | 384, 183 | 0x7ED27A11 | setRect +44 0x7ED28765, +108, +152, +172, +188, +200, +208, +252 | 40 own slots | embeds a part (vt 0x7EF1459C) and a 0x800E; one of the 6 classes with a real notify map (§5, shape E) |
| 0x8007 | 184, ≥165 | 0x7ED1EBEA | +108, +188, +200, +512 | not bounded (the next vtable has no root signature) | — |
| 0x8008 | 180, 167 | 0x7ED2A775 (slanted shapes 0x7ED31AE5) | +108, +188, +200, +512 0x7ED2AE09 | u16 fields +128…+176 | I: a gauge or bar with slanted ends |
| 0x8009 / 0x800E | —/180, 153/171 | 0x7ED2B2E7 / 0x7ED2B8A8 | +188 (it posts a notification), +200; 0x800E also overrides notify +564 0x7ED2C2E1 | 0x800E adds +152…+176 | 0x8009 is abstract (13d) |
| 0x800A | 176, 153 | 0x7ED2A1BA (setBrush 0x7ECFE8A1, rect 0x7ECFF899) | — | +128, +144, +160, +172 | I: filled box |
| 0x800F | 228, 198 | 0x7ED26792 (lineTo 0x7ECFE523, moveTo 0x7ECFE796) | +108, +152, +188, **+208 key**, +220/+224 focus | 55 own slots | I: an interactive control drawn with lines |
| 0x8010 | 176, 165 | 0x7ED2D009 | — | string id +130, style +132 (8 bytes; +12/+13 = alignment, §2.7), buffer +156/+160, setText 0x7ED2D50B (slot 151) | text label (13d) |
| 0x8011 | 216, 201 | 0x7ED2FB23 | **setVisible +76 0x7ED30302**, key +208/+216 | the 0x8005 slots plus 195–200 | a 0x8005 variant |
| 0x8012 | 188, 156 | 0x7ED1DD3F | re-implements the animation slots 116–141, +148/+152, +228 | 13 own slots, buffer at +128 | I: frame-animation widget |
| 0x8013 | 152, 156 | 0x7ED288ED | +152 | u16 +128 (set → re-layout), +130, +148, text | I: multi-line text |
| 0x0104 | 88, 123 | (root family) | many: see §2.5 | the attached panel +72, +76, bits 0x10000–0x80000 | **panel holder** (§2.5) |

- **Every** factory type (all 140) has its own +412 body (V), and the classes checked also have their own +408 (§5, shape E).
- C-parts: OnDraw (slot 40) calls exactly one renderer each (V): C001 → FillRect 0x7ECFB5F9 (I: a filled rect); C002 → 0x7ED319B4; C003 → 0x7ED34FE9 (I: slanted fill, via 0x7ED31C9B (A6 2026-11-09)); C004 → 0x7ED35160 (called with a0 = DC, a1 = part+88; tests mask 0x1 (bit 0) of the u16 at DC+64 (A6 2026-11-09)); C005 → 0x7ED3534D.
- D-parts: D001/D002 draw lines (0x7ECFE523/0x7ECFE796); D003 draws with 0x7ED303F9 (I: slanted fill, via 0x7ED31C9B (A6 2026-11-09)).

### 2.4 Container 0x0100 (vtable 0x7EEF5AE0, 142 slots)
Fields (V): +92 child-list object (vtable 0x7EEF5834; core at list+4, cursor at list+16; first 0x7ECF2BE2, next 0x7ECF2BFD, clear 0x7ECF2B88); +112/+116 pointer targets (cleared on delete); +120 current child; +124 key-target list (+468 add / +472 remove); +128 animation timer list (+476/+480); +752 (+492/+496); +756 flag (+484 test-and-clear, +488 set); +759 byte.

Methods (V):
- **+428 AddChild(a1)** (0x7ECF3370/0x7ECF3375): inserts into the list.
- **+436 FindChildById(d0) → a0**: walks the list and compares vt+8.
- **+440** returns &list.
- +456 (d0 = 0/1/2): list reorder (I: z-order).
- **+432 DeleteAllChildren (0x7ECF3388; C2 F055).** If the app window's current target (vt+584) is the child at +120, it calls `vt+580(0)`. Then, for each child:
  1. it reads the child's pool bytes (vt+248) and passes them to the app window (vt+244);
  2. it calls child vt+368 (pre-delete hook; empty in root and widget);
  3. it calls child vt+152 (OnDelete);
  4. it destroys the child through slot 0 (the returned deleter).
  
  Last, it clears the list.
- **OnDelete +152 (0x7ECF3342):** +112 = +116 = 0, then DeleteAllChildren, app-window vt+664(this), root delete.
- Panel base +432 is 0x7ED23D62. It calls 0x7ECF338D and then frees the panel (C2).

### 2.5 Class 0x0104 = panel holder (V structure; I name)
- **Created by** an app-window method 0x7ED1A6EA (744 B, vtable target).
  1. It finds an existing holder by id (vt+436 with the ids read from 0x7EF0F2AA, 0x7EF0F2C2, …).
  2. If there is none, it creates type 0x104 with a resource at 0x7EF0F2A8+…, and then a panel (type 0x6002, record 0x7EF0DF68) as its child.
- **Fields:** +72 is the attached panel (set by 0x7ECF6082, get 0x7ECF6098). Slots 92–98 and 100 forward the pre-filters and point events to it.
- **OnSetFocus +220 (0x7ECF67C9)** makes the attached panel the app window's key target (`appWin->vt+580(a1 = +72)`). Then it calls its focus setter **0x7ECF6A50/0x7ECF6A55 (C2 F056)** with 1. That setter changes bit 16 and, **only if bit 0x10000 is set**, computes the frame rect (0x7ECF67F9) and invalidates it.
- So for 0x0104, **bit 0x10000 = "draw a focus frame"** (I).
- Bits 0x20000/0x40000 have the same setter shape as the 0x10000 setter (slots 104/106/108 = 0x7ECF5F6D/0x7ECF5FB8/0x7ECF6003: test, set if changed, then invalidate(1,0) with no further condition; not the shape of the focus setter 0x7ECF6A50) (A6 2026-11-09); 0x80000 (slot 110, 0x7ECF69E4) has no invalidate. Container +464 tests parent type 260 = 0x104 (V).
- **App window vt+580/+584 = set/get the current key target** (V for both uses; this corrects C2 F056, which says "clears").

### 2.6 What the status bits mean (summary)
| Bit | Meaning | Basis |
|---|---|---|
| 1, 2 | visible, enabled | V (13d) |
| 0x10 | **focus**, propagated to all ancestors | V |
| 0x20 | skip DrawSelf in OnDraw | V code; I name |
| 0x1000, 0x2000 | root flags; +272 clears both and zeroes the +40 plane mask (A6 2026-11-09) | V; role open |
| 0x10000+ | **class-specific**. 0x0104: focus-frame enable (I). 0x8005: numeric caption when not focused (I). 0x1000000 on 0x8005: password mask (V) | §2.3, §2.5 |

### 2.7 Helper layer 0x7EDC17FB–0x7EDC1B36 (V; call sites from calls.tsv)
All of these return at once if w = NULL.

| Address | Sites | Role |
|---|---|---|
| 0x7EDC17FB | 0 | static initialiser: stores the pointer-to-member {−1, 0x7EDC178A} at RAM 0x602BC588 |
| 0x7EDC181B | 144 | **setLabelStrId(w, id)**: id = 0 → setVisible(w, 0); otherwise 0x7ED2CE0C (0x8010 string id). It never shows the widget |
| 0x7EDC1835 | 88 | 0x8010: set the style word +132 if it changed (0x7ED2D6A6 / 0x7ED2D67B) |
| 0x7EDC1851 | 2,641 | setVisible(w, b): ignores b > 1; vt+80, then vt+76 |
| 0x7EDC1875 | 453 | setListIndex(w, i): ignores i > count; set only if changed |
| 0x7EDC189F | 146 | **setListItemResource(w, i ≤ 32, resId ≠ 0)**: 0x7ECFF3AC(resId) → 0x7ED29CCB. **No compare** |
| 0x7EDC18C8 | 504 | moveTo(w, coord, axis 0 = x / 1 = y): keeps the size. invalidate(1), vt+44, invalidate(2) |
| 0x7EDC1972 | 253 | **setRectIfChanged(w, a1 = rect)**: gets the rect with **vt+48**, compares (0x7ECFF431), then invalidate(1), setRect, invalidate(2) |
| 0x7EDC19F4 / 0x7EDC1A45 | 6 / 8 | setHeight / setWidth (vt+32 / vt+28; changes y2 / x2) |
| 0x7EDC1A96 | 28 | 0x8013: set u16 +128 if it changed |
| 0x7EDC1AB4 | 8 | **setLabelAlign(w, axis 0/1, 0/1/2)**: writes byte +12 or +13 of the 0x8010 style, then 0x7ED2CE6A |
| 0x7EDC1B15 | 230 | setListItemValue(w, i, v): set only if changed |

### 2.8 Panel child builders: origin-only relocation (V; corrects 13d §2.2 "scales each child rect")
- There are 61 builders, from 0x7ED37E2D to 0x7ED82096. Each is the panel vtable slot 106 (+424 = GM_CREATECHILDREN). The container base returns 1 there.
- **Loop**, for each resource pointer in the class's RAM table (e.g. 0x602B6214+4k, k = 1..11 in 0x7ED37E2D):
  1. `Create(type = *res, this, res)` (0x7ED17DB8);
  2. if this panel's parent has type 257/258: get the rect (vt+52); x1′ = (x1·[0x602B6204] >> 12) + [0x602B6208], and likewise for y1 with 6206/620A; x2 = x1′ + w − 1, y2 = y1′ + h − 1; then setRect;
  3. AddChild (0x7ECF3375), store the child at this+792+4k, child vt+148(this).
- **Byte signature:** `fa c8 01 01 c8 .. fa c8 02 01` (cmp 257 / cmp 258), then `fc ac 04 62 2b 60` (`movhu (0x602B6204),d0`), `f6 04` (`udf00` = multiply, I) and `f8 c8 0c` (`asr 12`).
- **No static code writes 0x602B6204–0x602B620A.** I searched the whole linear disassembly for absolute stores and for the immediates 0x602B6000–0x602B620B. The values must come from initialised data or a block copy (open). With sizes kept, the reading "relocate children for another output" (HDMI/EVF) is more likely than "rescale" (I).

## 3. Drawing engine

### 3.1 Graphics context (DC) and pixel-format layer, 0x7ECFE7B8–0x7ECFEF32 (V; C2 F057)
**Create 0x7ECFE7B8**(d0 = DC id, stored at +0):
- It allocates a 684-byte DC from GUI pool 1 and zeroes it.
- It attaches surface 0 (0x7ECE876A: surfaces 0–2 = 160-byte records at RAM 0x605F2CD0 + 160·i; id −1 = 0x605F2EB0, −2 = 0x605F2F50).
- It sets the bounds +4, clip rects +16/+24, origin +12, pen +32 and scale +40 = (1,1).
- It copies 64 bytes into +84 and 304 bytes into +148 from RAM templates.

**Pixel format** = 3 channel masks and a byte at +661:
- **setPixelFormat 0x7ECFE8FD**(d0 → +661, d1 = R mask, a1 = G mask, stack = B mask) stores the masks at +628/+632/+636.
- **F057 0x7ECFE95E** (mask → (highest set bit + 1) − 8) gives the shifts +662..+664. Example: R5G6B5 gives R shift +8, G +3, B −3.
- It then re-converts every colour.
- Attaching a surface (0x7ECFED61) accepts a bitmap descriptor with **bpp 8, 16 or 24** (+6) and takes the masks from the surface record (+146 flag, +148/+152/+156).

**Colour conversion 0x7ECFE9CF:**
- It converts 0x00RRGGBB to the native format: each 8-bit channel is shifted left (shift ≥ 0) or right, then ANDed with its mask, then ORed.
- It is skipped when +661 = 0 or the colour is −1. −1 = transparent / none (I).

**Colour slots (raw value → converted value):**

| Slot | Setter |
|---|---|
| pen | +640 → +36 (0x7ECFEBD1, **85 callers**) |
| brush foreground | +644 → +56 (0x7ECFEA76) |
| brush background | +648 → +60 (0x7ECFE889) |
| two more colours | +652 (0x7ECFEB2C), +656 (0x7ECFEB0F) |

- +660 enables the conversion (0x7ECFE97F set / 0x7ECFE98A get).
- **setBrush 0x7ECFE991**(d0 = style, d1 = fg, a1 = bg), 36 callers. The style is stored at +54 = style mod 38; negative values are kept. FillRect reads −1 = no fill and −2/−3 = special modes. 0x7ECFE8A1 is the same call with a `{style, fg, bg}` struct.

**Other DC operations:**

| Operation | Address | Notes |
|---|---|---|
| moveTo | 0x7ECFE796 (22 callers) | pen +32 |
| lineTo | 0x7ECFE523 | only if pen ≠ −1 |
| setScale | 0x7ECFEC92 | +40/+42, minimum 1 |
| setFont by id | 0x7ECFECAC (40 callers) | 0x7ECFF393 → font descriptor 0x7ECFEEDB → +76 |
| clip | 0x7ECFE8B2 | intersect into +24 |
| flags | 0x7ECFED55 / 0x7ECFEB02 | set / clear bit 1 of +64 |
| palette op | 0x7ECFEB49 | converts an array of colours, then calls the surface's driver hook (surface +124) |

- The surface record holds driver function pointers at +124/+132 (V that they are called; their targets were not resolved).
- **There is no rotation, blending or scaling in this layer.** The only "scale" is the integer factor +40.

### 3.2 Renderers (V call graph; roles I from the arguments)
- FillRect 0x7ECFB5F9 (49 callers; clip, then brush style +54).
- 0x7ECFB90A (45 callers; uses scale +40, I: a scaled blit).
- Text/glyph layer 0x7ECF6C20 / 0x7ECF788E (1.6 / 1.5 KB; UTF-16 `wcslen` 0x7ECED7BB, font, colours).
- 0x7ECFC16E (1.1 KB; pen and scale).
- 0x7ECFCEF2 / 0x7ECFD3AE (1.2 KB each; brush, call FillRect).
- **0x7ED3231E is not a rotation (corrects 13d §2.4).** It takes d0 = an angle in 0.1° and returns a slope:

| Angle | Result |
|---|---|
| 90° or 270° | vertical edge |
| 180° or 360° | slope 0 |
| other | t = fabs(tan(a·π/1800)) (soft-double dmul 0x7E50160E, ddiv 0x7E501390, tan 0x7E501AAC, then float); the DC field **+624 = (int)(65536/t)** (the 16.16 cotangent), or arg·65536 if t = 0 |

  Then it searches a u16 width table for the start and end span. Its only caller is **0x7ED31C9B** (1,667 B, slanted-edge polygon fill). That routine is called by 0x7ED303F9 (D003 part; and 0x7ED31AE5 for widget 0x8008) and 0x7ED34FE9 (C003 part). **I:** slanted bars and tabs.

## 4. GUI app code without roles

### 4.1 Bluetooth callback → event table 0x7EFE2EF0 (V; C2 F063)
- **Registration.** SsBtSend/SsBtReceive entries call `OlyApiBluetooth` (0x7E9BFDA3) **vt+40(d0 = group, a1 = 0x7EDCB0C5)**; e.g. 0x7ED82906 uses group 12.
- **Dispatch.** The dispatcher 0x7EDCB0C5(a0 = group, d0, d1, a1) finds the group among the 22 `{u32 group, rows, u32 n}` entries. It runs each 20-byte row `{cmd, status, param, kind, u16 event}` through the matcher `kind` (table 0x7EFE2FF8):
  - 0 = cmd + status + param;
  - 1 = cmd + status;
  - 2 = cmd + status, and the callback parameter is passed on.
  
  It stops at the first matcher that returns 1. A match self-posts the event (0x7EDC5BF5).
- **Rows** (status 0x3 = progress; param 0xF0000001 = failure; the event names come from 0x7EFDEF78):

| Groups | cmd | Events |
|---|---|---|
| 0–9 (send) | 0x3B–0x44 | 0xA200 SEND_SUCCESS, 0xA201 SEND_FAIL, 0xA202 SEND_COMPLETE, 0xA203 SEND_UPDISP (kind 2 progress in group 6), 0xA204 SEND_PINCODE |
| 10–11 (receive start/stop) | 0x3B, 0x3C | 0xA100 RCV_WAIT, 0xA102 RCV_END |
| 12–17 (pair/connect) | 0x45–0x4A | 0xA104 PAIRING, 0xA105 CONNECT, 0xA103 ABORT, 0xA106/0xA109 PINCODE_INPUT/FAIL, 0xA107/0xA108 PAIRING_SUCC/FAIL, 0xA10B/0xA10C CONNECT_SUCC/FAIL |
| 18–21 (image receive) | 0x4B, 0x4C, 0x48, 0x4A | 0xA10D IMAGE_START, 0xA110 PROGRESS (kind 2), 0xA10E OK, 0xA10F NG, 0xA111 IMAGE_CANCEL, 0xA103 ABORT |

- Status codes reused across commands: 0xB4 (start), 0xB6 (PIN request), 0xB8 (PIN failure), 0xB9 (connect result), 0xBA (cancel ack), 0xC5 (pairing result) (I from the event names).

### 4.2 Live-view display elements and the Rec_View_Viewer exposure display (C2 F060, F061)
- **Static initialiser 0x7ED98B95** (2,913 B; no callers, no callees in the DB). It writes **77 pointer-to-member entries `{s32 −1, fn}`** to RAM **0x602BC070–0x602BC2D7** (stride 8). The functions are 0x7ED99E1D…0x7ED9EED6, in `$S/d2/gui/lvtab.txt` (V).
- **F060 0x7ED9C8FB is entry 65, at 0x602BC278.** C2 gave RAM 0x602BA478; that address has no reference in the image (V).
- **0x7ED99847** (632 B, vtable target) loads the table base (0x7ED99999) and calls the entries. It uses the data model (0x7ECEF64F/0x7ECEF667) and ShowPanelEx (V callees; I: "refresh every element").
- `Rec_View_Viewer::Iso()` 0x7ED9DF71 is not in this table. Its address appears as an imm32 at 0x7ED9D395, which is a second member-pointer store (V).
- **F061 0x7ED9F685 / 0x7ED9F74E** are picked by 0x7ED9E990. Its callers are 0x7ED8F3B1 and element 0x7ED9B221 (entry 38, 0x602BC1A0).
  - F061 handles A/M (info 24 = 4/77 or 6/90); 0x7ED9F74E handles P/S.
  - They fill the 10-byte record this+188: per-item flags for the Tv and Av fields (C2's reading, V).
  - **I:** the Tv/Av fields of the rec-view (live-view) exposure display. Which flag means "highlight" or "adjustable" is open.

### 4.3 RAW-edit menu page (C2 F065)
- **Page ids:** the menu-page registry 0x7EFE190C has **page 620 → factory 0x7EDF77BD and page 621 → 0x7EDF77BD** (rows at 0x7EFE2114, V). So 620/621 are **page ids**, not menu items (corrects C2). The current page id is RAM 0x602BCFD8 (read by 0x7EDCD7CA).
- **Vtable 0x7F0032B8** (dtor slot 1 stores it). Slots 3–33 are shared menu-page base slots (0x7EDCCCxx–0x7EDCDxxx); own slots are 0, 2, 31, 34–46.
- **Slot 31 (F065)** calls `OlyApiEditRaw` vt+8 (API 0x031B06) for page 620 and vt+12 (0x031B0A) for page 621. **I:** these are the two RAW Data Edit modes of 06 CmpERaw ("current settings" / "custom"), but the order is not known.
- Slot 38 0x7EDF79A4 passes the constants 913 and 197 (V). Read as string ids, they are "Exit" and "Set" (I: an Exit/Set dialog).

### 4.4 HIDE_MODE (SS_MENU_MAIN state 6) and the debug-menu sequences (V unless marked; C2 F062)
**Entry function 0x7EDABA6F:**
- If flag u16 0x602BC7A8 = 1 (get 0x7EDC7D54, set 0x7EDC7D4B), it shows page 0x7EDEA5D8 (singleton RAM 0x602BE3B0) with 0x7EDEA717(0) and clears the flag.
- Otherwise it calls `CCommon` 0x7ECFFAC6 and then **`setLongPressKey(8, 2000)` and `(9, 2000)`** (0x7ED00B90 → `OlyApiKeyCtrl` vt+12, log string 0x7EEF6F5A). Then it shows page 0x7EDEA7B8 with 0x7EDEA815(0).

**Key handlers of state 6** (from the D1 `handlers.tsv`):
- 1st/2nd release, Up/Down/Left/Right, OK, MENU, OK_LONG 0x903E → 0x7EDAF544, MENU_LONG 0x9040 → 0x7EDAFE4B, MOVIE_LONG 0x9041 → `clr d0`, POWER, CHG_OUTPUT_DISPLAY.
- Each step first calls the page's key method 0x7EDEA948 with a page key code: 4 = OK, 5 = MENU, 14 = OK-long.

**Sequence 1 (13d):** counter 0x602BC480 reaches 8, then OK → 0x0A01 = SS_DEBUGMENU state 1.

**Sequence 2 corrects 13d §4.3 step 6.** Counter 0x602BC482:

| Handler | Counter before | Action | Counter after |
|---|---|---|---|
| OK-long | 15 | 0x7EDED0F6, `userMenuMainReset::initMenu` 0x7EDED14A(0) | 10 |
| OK-long | other | — | 14 |
| MENU-long | 14 | the same two calls | 10 |
| MENU-long | other | — | 15 |
| OK | 10 | 0x7EDED0F6, `userMenuMainReset::MenuCursorMove` 0x7EDED19A(4,0), SettingController vt+40 | — |

So the sequence is **OK held 2 s and MENU held 2 s, in either order, then OK**. The 2 s long-press times set by the entry function are what make the OK_LONG/MENU_LONG events arrive in this state. I: this is a hidden reset path; the effect of SettingController vt+40 is not decoded.

**KeyCtrl numbering (I).** The per-screen long-press table at **0x7EEF6CE8** has 20 rows of 7 words `{profile, long ms, repeat ms, key ×4}`. It is applied by 0x7ED00A46 (56 callers), which ends with `unsetAllLongPressKey`. Its common key set {4,5,6,7} with a 50 ms repeat fits the four arrows. So **8 = OK and 9 = MENU** in KeyCtrl numbering. This numbering is offset by 2 from the event order 0x9000+2k (up = 0x9004 … OK = 0x900C).

## 5. Shape catalogue for GUI app functions (V byte signatures)
- **A. Panel ctor** (114 classes):
  - **Byte signature:**

    | Bytes | Instruction |
    |---|---|
    | `dd .. .. .. .. ` | `call 0x7ED23C27,[],4` (no `movm`: entered by `call` from the factory) |
    | `92` | `mov a0,a2` |
    | `fc cc VV VV VV VV` | `mov VT,d0` |
    | `62` | `mov d0,(a2)` |
    | `00 24 18 03 f1 78 db 04 64 40 50 a0 NN d4` | loop that zeroes NN words at +792 |
    | `[dd → 0x7ED01DFD ; 80 01 dd → 0x7ED01F7C/…FBA]` | optional tail calls |
    | `98 df 20 08` | `mov a2,a0 ; ret` |

  - The **dtor** follows at once: `f8 fe fc dd → 0x7ED23C60 fc dc c3 ef ce 7e df 00 04`.
  - 13d §3 has the variants.
- **B. ShowPanelEx call site** (193 sites):
  - **Byte signature:** `80 NN` (`mov panelNo,d0`) `85 01` / `04` (d1 = 1 / 0), then `dd .. .. .. .. f0 58` (`call 0x7EDC5D2D,[d2,d3,a2,a3],88`).
  - It usually follows a data-model set `dd → 0x7ECEF667 ff a0 10` or SetPalette `dd → 0x7EDC64BC 00 f0 1c`.
- **C. OlyApi wrapper** (74 functions ≤ 80 B in the area; e.g. 0x7ED07DCF, 0x7ED16B61):
  - **Byte signature:** `dd .. .. .. .. ` (`call getter,[],4`, getter from 13d §6.2) `f0 04` (`mov (a0),a1`) `f8 25 NN` (`mov (NN,a1),a1`) `f0 f1` (`calls (a1)`).
  - It is followed by one of: a return of d0; a compare against a constant (`a5 0f … 80 01 c8 03 00`: "is the value 15"); or a log `fc cc → string ; 42 04 ; 4a 08 ; dd → 0x7EDC3BCC`.
  - Setting wrappers: 0x7EE01D38 = `getSetting(id, a1)` (SettingController vt+4); 0x7EE01D4E = `setSetting(id, 0, a1)` (vt+0) with a log.
  - Inline uses (706 calls of SettingController 0x7E9C9E9A) have the same 4-instruction core.
- **D. Ss action stubs** (in 0x7ED82820–0x7EDC15B0; byte-pattern counts):

  | Bytes | Instruction | Meaning | Count |
  |---|---|---|---|
  | `00 de 00 00` | `clr d0 ; retf` | stay | 105 |
  | `80 NN de 00 00` | `mov N,d0 ; retf` | go to state N | 144 |
  | `2c LL HH de 00 00` | `mov 0xHHLL,d0 ; retf` | switch SS (0x104, 0x30B, 0x306, 0x304, …) | 16 |

  - The DB merges many of them into the previous function (e.g. into F062's tail).
  - Step handlers of HIDE_MODE: `f8 fe fc dd → 0x7EDEA7B8 80 KK 04 dd → 0x7EDEA948` (page key KK).
- **E. Widget-event handlers = per-class message maps** (all 140 GUI classes; 0x7EF0F3B0 types):
  - **+412 OnNotify, empty map.** Bytes: `f8 fe fc f8 97 00 1c fa c8 ff 18 c9 02 80 ff de 00 04` (`cmp 0x18FF` sentinel; it always returns −1).
  - **Real maps** (6 classes: panels 0x600A, 0x600D, 0x601B, 0x6022 GCPnl_Play, 0x6023 GCPnl_Play_Overall, widget 0x8006) start `cf 80`/`cf a0` and test `{code, child id}` pairs. Example: 0x600A maps (0x1802 CB_ONDRAW, child 196) → 0x7ED624A9, which owner-draws child 196. 0x8006 maps (0x2000, child 1) → 0x7ED28595.
  - **+408 OnMessage.** Bytes: `f8 fe fc 1c fa c8 ff 7f c8 0b dd → base ca 04 80 ff df 00 04` (forward to the base unless the id is 0x7FFF).
  - So in panels the key logic is not in the message maps. Keys go through the Ss handlers (13d §4). The panels mostly display.
- **F. Panel child builder:** §2.8.
- **G. Pointer-to-member static initialisers:** a `movm` prologue, then repeated `mov -1,dX ; mov FN,d0 ; mov RAM,a1 ; mov (a0),d1 ; mov (4,a0),d0 ; mov d1,(a1) ; mov d0,(4,a1)` (e.g. 0x7ED98B95, 0x7EDC17FB). fwmap shows 0 callers and 0 callees for these, and the targets have no data xref.

## 6. Corrections
1. **13d §1:** CCommon starts at 0x7ECFF983, not 0x7ED00000 (getInstance 0x7ECFFAC6 has 775 callers). The drawing engine is 0x7ECF6BDB–0x7ECFEF32, and geometry/resources run to 0x7ECFF982.
2. **13d §2.3:**
   - slot 0 is the destructor, which returns deleter 0x7ECEEFC3;
   - bit 16 is focus (with ancestor propagation);
   - the order of 0x100/0x101/0x102 is move/press/release, plus CB_ONCLICK;
   - +140/+144 are import/export properties; +252 selects one of 4 layouts; +412 is the notify map.
3. **13d §2.4:**
   - "14 of 15 widgets keep the empty base OnDraw; pixels come from the parts" is **wrong**. The base OnDraw calls DrawSelf (+568), and 14 of 15 widgets (all except 0x8001) override it with DC drawing.
   - 0x7ED3231E is a slope/cotangent helper for slanted fills, not a rotation.
   - The roles of 0x8005 and 0x0104 are in §2.3/§2.5.
4. **13d §2.2:** the builders relocate only the child origin (A5 13d-64). No static writer of 0x602B6204–620A exists.
5. **13d §2.4 helper layer** (A5 13d-125 plus this round):
   - 0x7EDC17FB is a static initialiser;
   - 0x7EDC181B hides when id = 0 and never shows;
   - 0x7EDC189F does not compare;
   - 0x7EDC1972 reads the rect through vt+48;
   - the layer ends at 0x7EDC1B36;
   - new helpers: 0x7EDC1835, 0x7EDC19F4, 0x7EDC1A45, 0x7EDC1A96, 0x7EDC1AB4.
6. **13d §4.3 step 6:** the second counter is set to 14 or 15 by OK-long or MENU-long and becomes 10 on the other long press. Then OK runs the reset path (§4.4). The 2 s long-press setup is in the HIDE_MODE entry 0x7EDABA6F. 13d omitted this entry.
7. **Section 07 §6:** the SS_DEBUGMENU row "entry key combination not found" is superseded (13d §4.3, §4.4 here).
8. **Section 10f §4.1:** add the HIDE_MODE entry function and the OK-long + MENU-long + OK reset sequence (§4.4). KeyCtrl keys 8/9 = OK/MENU is inferred.
9. **C2 (round2-review3/4):**
   - F056: vt+580 sets the key target to the attached panel; it does not clear it.
   - F060: the RAM slot is 0x602BC278, not 0x602BA478.
   - F065: 620/621 are menu-page ids (registry rows at 0x7EFE2114), not menu items.

## 7. Open questions
1. The initial values of the layout factors 0x602B6204–0x602B620A (data image or block copy), and whether HDMI output changes them.
2. The surface driver hooks (surface record +124/+132) and the renderers 0x7ED319B4, 0x7ED3534D, 0x7ECFB90A, 0x7ECFC16E: which draw bitmaps, glyphs or rounded shapes.
3. The roles of 0x8002, 0x8004, 0x8007, 0x8008, 0x800A, 0x800F, 0x8012 and 0x8013 beyond their fields. A pass over the panel resource records (13d §8.1) would tie each type to its screens.
4. The meaning of status bits 4, 8, 0x1000 and 0x2000, and of 0x8005's bit 0x10000 (numeric caption?).
5. The F061 record layout (+188..+197): which flag highlights the adjustable Tv/Av field.
6. Which EditRaw method (vt+8 / vt+12) is "current settings" and which is "custom"; and the effect of SettingController vt+40 at the end of the hidden reset sequence.
7. The KeyCtrl key numbering: confirm 8 = OK and 9 = MENU from the KeyCtrl implementation behind `OlyApiKeyCtrl` vt+12.
