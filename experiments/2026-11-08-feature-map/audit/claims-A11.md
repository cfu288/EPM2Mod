# Audit A11 (re-audit of 09a, 09b, 10d, 10e, 15b)

## 09a-12 (sections/09a-art-gui.md, line 12)

- mcon has a value-list table of 505 records of 20 bytes at **0x7E84A0B8**, found by a 128-bucket hash at RAM 0x605B9750 (`0x7E70782A`). The record layout (verified; the users 0x7E707147, 0x7E7071EF, 0x7E7070B4 and 0x7E70708D read +4, +8, +12, +14 and +17 (6 vs not 6); +2 is read by 0x7E707854, the +16 clamp is used by the u8 step 0x7E7074B5, and the type codes come from the dispatcher 0x7E70761C (cases 1–6, `extb` for type 2)) is: `+0 u16 info`, `+2 u16 variant key` (128 = default), `+4 ptr raw[]`, `+8 ptr gui[] (u32)`, `+12 u16 total bytes`, `+14 u16 element size`, `+16 u8 clamp` (1 = stop at the ends, 0 = wrap), `+17 u8 type` (1 = u8, 2 = s8, 3 = s16 nearest match, 4 = s16 exact, 5 = u16, 6 = composite) (13e §3.1) (D1 2026-11-09). (A10 2026-11-09)

## 09a-33 (sections/09a-art-gui.md, line 33)

- GUI value 4 is not used. Info 509 and 510 (tag 0xDF31[0], [1]; composite partners 511 and 512, tag 0xDF41) have **identical** tables, at mcon records 0x7E84A5F4 and 0x7E84A608 (verified). Their prm hints `_current_edit_info` suggest the RAW-edit picture mode (inferred).

## 09a-57 (sections/09a-art-gui.md, line 57)

| ART BKT | info 414–423 → 100–109, 424 → 119, 469 → 120 (coordinator-verified builder 0x7EA7633A / 0x7EA9528D). Each info is a 0/1 flag (mcon records 0x7E84C278…0x7E84C354, raw [0, 1]) | the same 12 filters |

## 09a-63 (sections/09a-art-gui.md, line 63)

- The ART-mode reset check is `0x7E700185`. It maps the code in info 281 to its show flag through the hash 0x7E818CC8 (`0x7E70010D`; it covers codes 69–74, 78–83, 85–88, 91, 93, 96, 97, 163, 164, 181 and 183). If the flag is 0, it resets 281 to **70 (Pop Art)**. Codes 75, 84, 117, 118, 119, 145, 151 and 153 have no flag entry (verified). An unknown code gets the default info 352 (the Pop Art flag) (verified).

## 09a-67 (sections/09a-art-gui.md, line 67)

- **`app Set_CameraInfo <info> <value>` shell** (`0x7E677990`; at 0x7E6780AC it passes both parsed arguments straight to Set_CameraInfo): **yes, it can store any u8 in 0x9481** (verified code path; no range check in Set_CameraInfo). `prmdbg setval` (07 §1.4) can also write the tag. Whether a retail camera exposes these shells (UART) is unknown.

## 09a-68 (sections/09a-art-gui.md, line 68)

- **If 0x9481 holds 110–118** (consequences verified from the code above; end result inferred):

## 09b-56 (sections/09b-art-algorithms.md, line 56)

- **Verified:** the RNG 0x7E54594F is xorshift32 (`x^=x<<13; x^=x>>17; x^=x<<5`), and a state of 0 becomes 1.

## 09b-61 (sections/09b-art-algorithms.md, line 61)

- **Masks (`make_mask` 0x7E548626 → 0x7E54846F, verified).** Each mask is radially symmetric:

## 09b-76 (sections/09b-art-algorithms.md, line 76)

- **Verified:** `art_chk_type_rec` 0x7E71C0E1 (trace id 7; its caller `art_chk_type` 0x7E71C075 is id 6) accepts 151/153 only when req+2==3 (block 0x7E71C1BA). (A10 2026-11-09)

## 09b-148 (sections/09b-art-algorithms.md, line 148)

- **Verified:** I searched the image-engine driver (0x7E54xxxx–0x7E56xxxx) for compares on P+79. It branches

## 09b-154 (sections/09b-art-algorithms.md, line 154)

- **Verified:** `art_chk_type_rec` (0x7E71C0E1) accepts 118 for req+2 = 1 and 3, but not 2. (A10 2026-11-09)

## 09b-158 (sections/09b-art-algorithms.md, line 158)

- **Verified:** 73, 106 and 108 all go to case 0x7E72A615 → `art_effect_20_pinhole` 0x7E720332.

## 10d-24 (sections/10d-playback.md, line 24)

| Audio DSP | Active (inf for use) | **CORRECTED (split)** | **Wind cut is user-switched:** Custom Menu "Wind Noise Reduction" (info 434 → prm 0x7871) selects windcut or plain HPF (verified). ReTune, 5-band EQ, notches, DF1 and 3D use **fixed ROM-class settings**. The notch pattern follows movie quality. DRC uses 2 CPRAM values. Caveat: the 3D tag 30034 and the windcut tag 56004 do have prm sets (2 and 4 sites in 07-settings.tsv; e.g. 0x7E94D577 sets 30034); the A10 audit traces them to a save/restore driven from ADJ (… ← 0x7F082681), so a user still cannot set them | — (A10 2026-11-09) |

## 10d-96 (sections/10d-playback.md, line 96)

- `OSDControl::customDisplay` (r13 → 0x7E98C692) has GUI callers 0x7ECE9C57 / 0x7ED01B0B and calls `api_*` directly, so the OSD custom-window feature does not need CmpPCw (verified call edges).

## 10d-109 (sections/10d-playback.md, line 109)

- **Corrected:** `api_picfile_Check_Create_PictureFile` 0x7E683DB6 maps API modes 1..33 through the jump table 0x7E7CF458 (all 33 words decoded): 1→1, 2→2, 3→0x81, 5→7, 6→0x85, 9→8, 10→0x0A, 11→0x0B, 12→0x0E, 14→0x0C, 15/16→0x84, 17→0x10, 18→0x10 (it also clears the flag at (8,sp)), 19→0x83, 21–25→0x88, 26→0x87, 30→0x89, 31→0x8A, 33→0x82. Mode 20 is computed by 0x7E93FDBB. Modes 4, 7, 8, 13, 27, 28, 29 and 32 fall to the error default 0x7E683E69 (d2 = 1, (8,sp) = 2). So the size check does **not** know every mode: 10 of the 23 modes in 0x7EBB8D88 are never produced as constants (0x80, 0x86, 0x8B, 0x8C, 0x8F, 0x90, 0x91, 0x92, 0x93, 0x94; mode 20 is the only possible source), and it produces 0x0A, 0x0B, 0x0E, 0x82 and 0x83, which are not in that table. Only 0x85 (API mode 6) is known as claimed (verified). (A10 2026-11-09)

## 10d-132 (sections/10d-playback.md, line 132)

- **GUI (verified):** the SoundCtrl getter 0x7E9CD7B0 has 20 GUI call sites. The cluster 0x7EDF26B2–0x7EDF2C5D loads string 1782 "BGM Import", and `ImportBGMProcessCallback` exists (0x7F0042DB).

## 10d-135 (sections/10d-playback.md, line 135)

- The import is user-driven from the menu. It is not run by the updater or at boot. `play_rom_chk_bgm` has one caller, `play_rom_main_exec` 0x7E94A33D, whose only caller is the PLAY_LOAD task 0x7E9456C5 (verified). The request is built by `api_play_Check_BGM_File` 0x7E686B22. I did not trace which callers reach that function.

## 10d-140 (sections/10d-playback.md, line 140)

- **Slideshow rows (verified bytes):** sub-item table group 20 at 0x7EFEFC90 has Start (265, info 1), BGM (1657, 110), **Effect** (1009, 97), Slide (962, 101), Slide Interval (921, 289) and Movie Interval (901, 284). §07 warns that this table is a superset.

## 10e-34 (sections/10e-connectivity.md, line 34)

- **What 0x1709 is (verified):** the status-name table at **0x7E8DA174–0x7E8DA333** (8-byte records; zero terminator at 0x7E8DA334) holds records `{u32 id, char *name}`, e.g. (4, "O  k"), (0x100, "Trg1"). The last 8 records (from 0x7E8DA2F4) are a mode-name list (" P " 1, "iAT" 0x31, "ART" 0x33, "SCN" 0x2A, "MOV" 0xA, " M " 4, " S " 3, " A " 2), so some ids occur twice (4 = "O  k" and " M "). (A10 2026-11-09) Part of it:

## 10e-87 (sections/10e-connectivity.md, line 87)

- **ADJ (corrected):** the status reads are in op **0x9005**, not 0x902A. The ADJ dispatcher 0x7F080284 (op table 0x7F0D2850, key = op − 0x1001: 0x8004 → 0x7F08034A) calls 0x7F080519 → 0x7F08056A, a linear status-packet builder that reads all of 0x1706–0x170C (the seven reads start at 0x7F080B39 and end at 0x7F080BC5). `cube is disable` comes from op **0x902A** (key 0x8029 → 0x7F0803BD → 0x7F082C09), whose sub-op 0x7F083BDD calls the cube routine 0x7E8FED1A, which prints it (factory test, verified). (A10 2026-11-09)

## 10e-111 (sections/10e-connectivity.md, line 111)

- **What decides support:** the accessory-ID scan in §1.2 (verified). Evf1/Evf2/Evf3 are three EVF classes (IDs 0x0101/0x0202/0x0322). Mapping them to VF-2/VF-3/(VF-4) is **inferred** from `EVF_TYPE_VF2/VF3` and `vf-2/vf-3 Version:`.

## 10e-127 (sections/10e-connectivity.md, line 127)

- "Connection to Smartphone" (1719/1720) is a row at **0x7EFFE1DC**, kind 0x100 (row bytes verified). That it is in the Playback tab is inferred from item order (it follows Edit, Print Order and Reset Protect; 07 §3.1). (A10 2026-11-09)

## 10e-189 (sections/10e-connectivity.md, line 189)

- **Active (inferred).** The menu row was not traced, because the Custom Menu D lists are built in code. **Update:** the Custom Menu D lists are the ROM table 0x7EFF7E80 (13d §5), and D has the submenu HDMI (1662); its sub-item group 121 holds "HDMI Control" (700) = **info 306** (verified bytes). So the info 306 = HDMI Control link is now verified (D1 2026-11-09).

## 10e-195 (sections/10e-connectivity.md, line 195)

| Card update mode (FIRMUP_CLI) | All 9 entries: S, A, M, V, D, T, E/G/H/W/E100, DATE/PICTURE1JPG, N | Boot only. 0x7E544A6F needs `table[factor]` to be 12, 0x01000002 or 0x01000001 (table 0x7E73522C read by 0x7E50B1A7; factor = u16 at 0x604154E6, read by 0x7E45D407) **and** 0x602A9B54 = 0. 0x7E505694 clears that byte when status 4 reads 0 and 0x7E45D893() ≠ 9; it is the only writer of 0x602A9B54 and can only clear it. The initial value is not traced, so the role of the key is open. Status 4 is "O  k" in the status part of the name table (verified; the trailing mode-name list of the same array also has id 4 = " M "), so this is probably the OK key held at power-on (**inferred**). The table values partly decode through the name table: 12 = "Powr" (indices 1 and 10); 0x01000002 (index 8) and 0x01000001 (indices 0 and 9) have no name | Hidden / service (A10 2026-11-09) |

## 15b-57 (sections/15b-camera-core-index.md, line 57)

| cam_mirror.c | 0x7E642459 | hash 0x7E7B18B8: 1, 2, 5, 6, 9, 10, 145–152 (roles 14b §5) |

## 15b-125 (sections/15b-camera-core-index.md, line 125)

- The bits are the module's own step events. The still/LB monitor prints phase names (0x7E656B1D), not the cam.c factor names, so the cam factor table (03 §1) does not name them (V).

## 15b-147 (sections/15b-camera-core-index.md, line 147)

| 0x7E666C5B–0x7E674DF4 | **mdet**: motion detection and AF subject tracking on the EMS1/EMS2 motion-estimation units, 160 functions | first function 0x7E666C5B calls EMS2 0x7E4600B0; 0x3100xxxx codes |

## 15b-218 (sections/15b-camera-core-index.md, line 218)

| 0x7E530020 | 0 | 3 | 0x6601 |

## 15b-223 (sections/15b-camera-core-index.md, line 223)

| 0x7E53030A | 1 | — (done) | 0x6602 |

## 15b-244 (sections/15b-camera-core-index.md, line 244)

- **Channels (V):** 4 and 13 = battery/power. 15, 34 and 41 = ccd_temp (0x7E45E206 → 0x7E45E27F with builder 0x7E45E38D = 15, 0x7E45E2B5 with builder 0x7E45E3CF = 34, 0x7E45E556 with builder 0x7E45E411 = 41). 34 is shared with the per_acc accelerometer (builder 0x7E4589DC, `mov 34` at 0x7E458A24, request 0x60414908; its I²C check `ACC:I2C NG?`). 22 = ADC key (0x7E50B1B4 copies the channel from table 0x7E7354CC entry 0, byte +4 = 0x16). 38 = MEC layer 0x7E5175C9. 39 = MEC 0x7E51773D (`mov 39,d0; call 0x7E45BADC`: static request 0x60414BA8, type 0xF1). Only channel 21 has no user found. Callbacks: only the ADC-key init 0x7E50B1B4 sets +32 = 0x7E50B2F5. 0x7E50B356 sets 0x7E50B606 when the u16 at its a2 is 4094, else F002 0x7E50B724. 0x7E50B512/0x7E50B576/0x7E50B5DF/0x7E50B877 resubmit requests without setting +32. (A9 2026-11-09)

