# Audit A6 batch 3

## 14e-15 (sections/14e-gui-methods.md, line 15)

| 0x7ECF4C68–0x7ECF5450 | Widget base 0x8000 (143 slots, §2.2), including the frame-animation engine 0x7ECF50C8–0x7ECF5441 | V |

## 14e-50 (sections/14e-gui-methods.md, line 50)

| 64–68 | bit 0x2000 (+256/+260), bit 0x1000 (+264/+268); +272 clears both | V |

## 14e-88 (sections/14e-gui-methods.md, line 88)

| **0x8005** | 204, 195 | 0x7ED2DF2F (324 instructions) | **key press +208 0x7ED2E94C** (468 instructions, UTF-16 helpers), +216, focus +108 0x7ED2F562 (reselects the image) | **images +160 normal / +164 focused / +168 disabled**, picked by 0x7ED2E363. u16 +128/+130/+184/+186/+188/+190, 8-byte +136, dwords +176/+180, caption +172 (slot 188), **status bits 0x10000–0x1000000** (slots 161–178), text layout slots 185/186 | **Captioned image button / text field.** Bit 16 (focus) selects the image; vt+88 = 0 (disabled) selects +168. Bit **0x1000000**: DrawSelf draws the caption as `*` × length, a **password mask** (V, 0x7ED2E070). Bit **0x10000**: when the widget is not focused, DrawSelf rebuilds the caption with 0x7ED2F453, which uses the UTF-16 digits `0123456789` at 0x7EF146DC (I: a numeric display mode). C2 F058 is slot 163, the 0x10000 setter |

## 14e-102 (sections/14e-gui-methods.md, line 102)

- C-parts: OnDraw (slot 40) calls exactly one renderer each (V): C001 → FillRect 0x7ECFB5F9 (I: a filled rect); C002 → 0x7ED319B4; C003 → 0x7ED34FE9 (slanted fill); C004 → 0x7ED35160 (tests bit 1 of part+64); C005 → 0x7ED3534D.

## 14e-130 (sections/14e-gui-methods.md, line 130)

- Bits 0x20000/0x40000 have the same setter shape; 0x80000 has no invalidate. Container +464 tests parent type 260 = 0x104 (V).

## 14e-254 (sections/14e-gui-methods.md, line 254)

- **F060 0x7ED9C8FB is entry 65, at 0x602BC278.** C2 gave RAM 0x602BA478; that address has no reference in the image (V).

## 14e-266 (sections/14e-gui-methods.md, line 266)

- Slot 38 0x7EDF79A4 passes the constants 913 and 197 (V). Read as string ids, they are "Exit" and "Set" (I: an Exit/Set dialog).

