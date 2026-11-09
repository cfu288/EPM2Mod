# Audit A5 batch 2

## 13c-11 (sections/13c-cpp-framework.md, line 11)

| 0x7E966000–~0x7E96998A | HIGHLEVEL_MAIN entry, HLS OS wrapper, growable array, logger (section 06) | verified (06); end moved from 0x7E96B000 by the `Tra*` string tags (A4 2026-11-09) |

## 13c-14 (sections/13c-cpp-framework.md, line 14)

| 0x7EB7FC91–~0x7EB854FF | `CmpSts_SingleStillShootingSequence_NEW` statechart (`rcv3dShootingFinishIn_END_WAIT` …) | verified (class directory, strings) |

## 13c-18 (sections/13c-cpp-framework.md, line 18)

| 0x7EBA0AA9–0x7EBA4867 | `Dev*` device classes, part 2: anti-shake, image handle, HDMI/CEC, histogram, Exif, picture files, `DevBlu_Bluetooth`, **USB-communication device**, DPS-T, DPS, pixel mapping, picture-file creation (§5.4) | verified |

## 13c-20 (sections/13c-cpp-framework.md, line 20)

| 0x7EBA7BC1–0x7EBABF8D | **Not OXF: OKAO Smart Skin** (13b §2.2; data from ~0x7EBAC000). A string-less library called only from the FACE task code (0x7E6FB836, 0x7E6FB8BF, 0x7E6FBBCD, 0x7E6FBC17). It calls 0x7E72D0BA–0x7E72D95E (OKAO area) and the soft-float helpers 0x7E5010xx. Error codes 0x0CA000xx. | verified call edges; "OKAO" by role (13b) (A4 2026-11-09) |

## 13c-37 (sections/13c-cpp-framework.md, line 37)

| Framework events | ids −5 (0x7EBA6E24), −6 (0x7EBA6E50), −1 (0x7EBA6E7C), −9 (0x7EBA6EAD); vtables 0x7EC92080–0x7EC921A0 | verified ids |

## 13c-140 (sections/13c-cpp-framework.md, line 140)

| 11772 | sent to the requester when a request is registered (0x7EB86C21) | verified call; "ack" inferred |

## 13d-14 (sections/13d-gui-toolkit.md, line 14)

| 0x7ECA1020–0x7ECCB7FF | Mostly data: ramp/LUT tables (0x7ECA1020–0x7ECB1000, from 0x7ECA6000…), then `de 00 00` (a `retf`) at 0x7ECB1000 and **108,541 bytes of 0xFF erased fill** (0x7ECB1003–0x7ECCB7FF), which is padding, not a table. The DB's "function" 0x7ECAD443 (15 KB, calls only itself) is probably data | verified bytes; the role of the ramp data is inferred (A4 2026-11-09) |

## 13d-23 (sections/13d-gui-toolkit.md, line 23)

| 0x7ED82820–0x7ED86DA0 | `Ss*` handlers of SS_BTRECEIVE, SS_BTSEND, SS_COMMON (§4) | verified |

## 13d-64 (sections/13d-gui-toolkit.md, line 64)

- The two parent types the panel builders test are **257/258** (screen / sub-screen). For those parents the builders scale each child rect by 4.12 fixed-point factors at 0x602B6204/6206 and add offsets at 0x602B6208/620A (verified, 0x7ED37E90…). **Inferred:** this rescales layouts for HDMI/EVF output.

## 13d-125 (sections/13d-gui-toolkit.md, line 125)

- **Helper layer 0x7EDC17FB–0x7EDC2000 (verified; "set only if changed"):** 0x7EDC1851 `setVisible(w, b)` (2,641 call sites, the most called GUI function; vt+80 then vt+76); 0x7EDC1875 `setListIndex(w, i)` (453; range-checked); 0x7EDC189F set list item resource; 0x7EDC1B15 set list item value; 0x7EDC18C8 / 0x7EDC1972 move/resize (vt+52 get rect, +44 set rect, +168 invalidate); 0x7EDC181B text by string id + show. C1 F065 0x7ED61C13 is a panel-level "show item n−2 or hide" helper built on these.

## 13d-135 (sections/13d-gui-toolkit.md, line 135)

- **Resource record (44 bytes, verified):** `{u16 type, u16 k+1, u32 rects → 0x7EF0D7F0 + 16·k, u16 7, …, u16 layer (1/2/3), 0xFFFE, …, 100, 100}`. Field +20 is 0xFFFE in 98 records and 0xFFFF in 16. Records exist for k = 0…113 only (indices 114–159 are not records). The rect pair is two `{x, y, w, h}` rects (720×480 ×65, 800×600 ×37, 640×480 ×7, …), and in all 114 records the two rects are identical, so nothing in the data supports the inferred "two outputs" reading. (A4 2026-11-09)

## 13d-156 (sections/13d-gui-toolkit.md, line 156)

- Panel **signature (verified, majority form):** 93 of the 115 callers of 0x7ED23C27 use `call 0x7ED23C27 ; mov a0,a2 ; mov VT,d0 ; mov d0,(a2) ; …zero the child array at +792… ; [call 0x7ED01DFD ; call 0x7ED01F7C/0x7ED01FBA]`. Variants: 17 store the vtable through (a0), zero +792 and return with no tail calls (e.g. 0x7ED7A79F); 4 zero from +796 (e.g. 0x7ED40F26); 0x7ED230C2 only does `mov d0,(792,a0)`. (A4 2026-11-09)

