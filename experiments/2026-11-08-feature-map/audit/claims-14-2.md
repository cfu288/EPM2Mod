# Audit A6 batch 2

## 14c-16 (sections/14c-app-protocols.md, line 16)

| **0x7EB84345–0x7EB85562** | **Com_EvSenderManager (static module, no `this`)**: sender 0x7EB84345 (4,143 B; maps APP_EVENT codes to 41 event classes 16070…27522; only caller HLS_EVENT 0x7E96DD58), "set wait code" 0x7EB85398/0x7EB8543C (callers CapThr 0x7EA1D60D/0x7EA1D68E), `Com_EvSenderManager buffer overflow!` 0x7EB854E0. All use globals 0x602B48A8–0x602B48E0 | V |

## 14c-98 (sections/14c-app-protocols.md, line 98)

- **APP_EVENT path (V):** tasks and drivers post `(code, value)` through 0x7E880EFF (118 callers, e.g. the 3D stub's 0xF00F0000). HLS_EVENT 0x7E96DD58 (`RECV APP_EVENT [%08X][%08X]`) takes each one and first offers it to **Com_EvSenderManager** 0x7EB84345 (code → event class, sent to the registered receiver or buffered). If that does not consume it, 0x7E96DE42 forwards it to EVFW subscribers (`EVFW TO`), else keeps it in a backup list (`NOT FOUND EVFW BACKUP`, `EVFW FROM BACKUP`).

## 14c-113 (sections/14c-app-protocols.md, line 113)

| 7 | Black-out ON: 0x7EA97FF5 (`BLACK:ON`, trace 0x04000001, PaintBlack flag **0x602B0D20 = 1** via 0x7E96ADC8) → part+364 = CapDpc iface slot **26** (+104) → 0x7E9EE967 → display device (+256) vt+172 = `startPaintBlack` **0x7EB8D5AD**. BLACK:OFF siblings: 0x7EA8FBBA → slot 24 (+96) → device vt+156 = `setPaintBlackFlag` 0x7EB8D45A; 0x7EA900E6 → slot 14 (+56) → device vt+80 = `endPaintBlack` 0x7EB8CDC1. Display-device vtables 0x7EC8DEDC / 0x7EC8E57C (base/derived) | V |

## 14c-134 (sections/14c-app-protocols.md, line 134)

- **CapMed_MediaInfo** 0x7EA104DE–0x7EA10D3D: per-slot status update 0x7EA10735 (F032), category map 0x7EA1082F, init chart 0x7EA10A66, `pMediaInfo(NULL)` iface guard 0x7EA10C4F, teardown 0x7EA17103 (F033) (V).

## 14c-143 (sections/14c-app-protocols.md, line 143)

- **Mechanism (V):** 22 GUI static initialisers in the C++ ctor table **0x7F033AC4–0x7F033B7B** (46 entries) fill RAM tables of 8-byte pointer-to-member records `{−1, method}`; for 21 of them exactly one other function loads the table base (the dispatcher). Example: 0x7ED98B95 fills **77** records at **0x602BC070–0x602BC2D7**; the dispatcher 0x7ED99847 (vtable word 0x7EFD101C) clears its output fields and calls all 77 in order (`cmp 77,d2` loop), then writes data-model values (0x7ECEF667). Other tables (init → base, n, dispatcher): 0x7ED86DA6 → 0x602BB094 (22, 0x7ED87077, `IGui_Controler`); 0x7ED8ECE2 → 0x602BB7CC (18); 0x7ED8F435 → 0x602BB8DC (59); 0x7ED912E5 → 0x602BBAB4 (42); 0x7ED9319E → 0x602BBCA0 (60); 0x7ED94F0D → 0x602BBE80 (43); 0x7ED9D151 → 0x602BC2D8 (46, 0x7ED9D844); 0x7EDC2829 → 0x602BC5A4 (3, `Warning_Viewer::Update`); 13 smaller ones (1–7 records). fwmap shows 0 callers for all these methods because the only reference is the `mov imm32` inside the initialiser.

## 14c-144 (sections/14c-app-protocols.md, line 144)

- **Live Bulb (V):** record 49 at **0x602BC278** (not 0x602BA478 as F060 says) = 0x7ED9C8FB, which calls `Shooting::getLiveBulbInfo`. That API (OlyHfwOpeShoot 0x7E984DDE) returns minute/second from `api_rec_Get_Bulb_Exp_Time` (TAKE 0x7E5A624F) and `nowcount` = `api_rec_Get_Bulb_Lv_Count` (u16 0x605178BE), `maxcount` = info 696 (prm 0xD721).

## 14c-145 (sections/14c-app-protocols.md, line 145)

- **Update chain (V):** GUI table 0x7EEDE0C0… (16-byte records `{code, 1, 1, handler}`) binds `updateLiveBulb` 0x7ECDF300 to codes 0x01000002 and 0x0200001A → API object slot 66 (+264; I: OlyApiShooting, its vtable word 0x7EC0F59C is next to F028's 0x7EC0F610) → 0x7E9CC9EC → OlyHfwOpeShoot 0x7E98A2B5 → event **12039** → SequencePartsBase 0x7EA8E955: if Live Bulb is running and `info 696 − CapTak slot 42 ≥ 1`, `TAKEPIC_BULB_LV_UPDATE_send` 0x7EA985D7 → CapTak slot 105 (+420) → `api_rec_Update_Bulb_Lv` 0x7E68C46D → TAKE_MAIN message **19** → TAKE event table 0x7E790060 (records `{event, handler}`, end 0xFFFF): event 0x38 → 0x7E5A2C01 increments 0x605178BE and sends 0x0408003A; events 0x1B/0x1C → start 0x7E5A2A6F (copies 4 request words to 0x605178C0–CC); 0x1D → 0x7E5A2B4C (stores a pointer at 0x605178D0, used by the end step 0x7E5A2C31). The result goes back as `evTraResShtUpdateLiveBulb` (0x7EA941E5) / `CBS_UPDATE_LIVEBULB` (254).

## 14d-27 (sections/14d-data-and-blobs.md, line 27)

| **0x7E8DA000–0x7E8F3113** | **`.data` init image, 102,676 bytes.** The reset code first loads it from flash 0x40779000 to 0xBE8DA000 (0x7E421247). Then it copies it to **RAM 0x602A9B40–0x602C2C53** with {src 0x7E8DA000, dst 0x602A9B40, size 0x7E8F3114−0x7E8DA000} → 0x7E425FA8 (0x7E4212B8–0x7E4212E0). **ROM = RAM + 0x1E6304C0.** Code never loads these ROM addresses; only the reset code does. | V |

## 14d-28 (sections/14d-data-and-blobs.md, line 28)

| 0x7E8F3114–0x7E8F57FF | 0xFF | V |

## 14d-31 (sections/14d-data-and-blobs.md, line 31)

| 0x7ECB083C–0x7ECB0887 | Segment-2 static-constructor table (19 pointers). | V |

## 14d-299 (sections/14d-data-and-blobs.md, line 299)

| "0x7EBA1020–0x7ECA0000 … data from about 0x7EBAC000" | Rodata starts at **0x7EBABF90**. The tail 0x7EC92318–0x7ECB083B is the OKAO Smart Skin LUTs, not GUI data (V) |

## 14d-301 (sections/14d-data-and-blobs.md, line 301)

| Map §1 "Overlays: part of block 0 is copied from flash at boot" | Add the `.data` image copy by the reset code (§1) and the constructor walker 0x7E44B6B0 with one table per segment (V) |

## 14d-304 (sections/14d-data-and-blobs.md, line 304)

- The OKAO PT models end at 0x7E86DD5F (§3.6). 0x7E86DD80–0x7E8808BF is the ORF CMIO blob (V).

## 14d-306 (sections/14d-data-and-blobs.md, line 306)

- The DB size of 0x7E731532 (2,766) is wrong. The function ends at 0x7E731584 (V).

