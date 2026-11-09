# Audit A10 batch 4

## 10c-41 (sections/10c-movie.md, line 41)

- **Other writers (verified, static):** 07-settings.tsv lists 0 constant prm sets and 0 Set_CameraInfo calls for 26225 or 34145. I checked the 31 constant loads of 26225/34145 in code: all are reads (getter 0x7E457C75, or the address getter 0x7E457C52 at 0x7E6B39A3).

## 10c-113 (sections/10c-movie.md, line 113)

- `startMultiThrough` has two callers, 0x7E9CB473 and 0x7E9CC4D3. Both are vtable methods of the API controller (vtable 0x7EC0F494, slots +0x2C and +0xD4), and the `sdk api` shell names `setMultiThroughMode`, `startMultiThrough` and `getMultiThroughCursor` (0x7EBF88F8…). So the feature is reachable from the `sdk api` debug shell (verified table; not run).

## 10c-157 (sections/10c-movie.md, line 157)

- **Refinement to 04 §1.3 (verified, 0x7E6EF1FB / 0x7E6EF13A):**

## 10c-166 (sections/10c-movie.md, line 166)

- **Mapping (verified):** `mov_art` 0x7E6CBFD3 reads **prm 38017 = 0x9481** (Picture Mode) and **prm 49169**. It maps with two jump tables, 0x7E7FF05C (still codes) and 0x7E7FF008 (movie codes; the movie path calls it through 0x7E6CBFC7 with bit 0 set). The movie-code table is:

## 10c-171 (sections/10c-movie.md, line 171)

- **Selection:** movie has no own art list. Picture Mode in movie is the same prm 0x9481. Its only GUI write path is the 19-entry info-111 list (09a; also E-PL5/E-P5), which offers the 12 shipped filters. So the hidden ids 110–118 cannot be chosen for movie either (verified by the absence of any other mcon list holding 100–120, 09a `scan.py`).

## 10d-24 (sections/10d-playback.md, line 24)

| Audio DSP | Active (inf for use) | **CORRECTED (split)** | **Wind cut is user-switched:** Custom Menu "Wind Noise Reduction" (info 434 → prm 0x7871) selects windcut or plain HPF (verified). ReTune, 5-band EQ, notches, DF1 and 3D use **fixed ROM-class settings**. The notch pattern follows movie quality. DRC uses 2 CPRAM values | — |

## 10d-109 (sections/10d-playback.md, line 109)

- `api_picfile_Check_Create_PictureFile` 0x7E683DB6 maps API modes 1..33 to these internal modes (jump table 0x7E7CF458; for example → 132, 129, 8, 10, 11, 14, 133, 16, 131, 7, 12, 1, 2). The size check therefore knows every mode, including 0x85 (verified).

## 10d-130 (sections/10d-playback.md, line 130)

- **Code (verified, §05):** `play_rom_chk_bgm` 0x7E94A62D allows ≤ 14 files of ≤ 6,145,024 bytes, and `aud_tool_wav_judge_OLYMPUS_authentication` must return 2. `play_regist_bgm` 0x7E9499A6 writes the WAV to flash and the entry to blob setting 0xE001.

## 10d-135 (sections/10d-playback.md, line 135)

- The import is user-driven from the menu. It is not run by the updater or at boot. `play_rom_chk_bgm` has one caller, `play_rom_main_exec` 0x7E94A33D, whose only caller is the PLAY_LOAD task 0x7E9456C5 (verified). The request is built by `api_play_Check_BGM_File` 0x7E686B22. I did not trace which callers reach that function.

## 10d-156 (sections/10d-playback.md, line 156)

- Info 434 → prm **0x7871** (mcon values 0/2/6/10, verified).

## 10e-34 (sections/10e-connectivity.md, line 34)

- **What 0x1709 is (verified):** the status-name table at **0x7E8DA174–0x7E8DA330** holds records `{u32 id, char *name}`, e.g. (4, "O  k"), (0x100, "Trg1"). Part of it:

## 10e-87 (sections/10e-connectivity.md, line 87)

- **ADJ:** the service op 0x902A (case code 0x7F080B39–0x7F080BC2 inside the function 0x7F08056A (L1 2026-11-09)) reads 0x1706/0x1708/0x1709/0x170A/0x170C and prints `cube is disable` (factory test, verified reads).

## 10e-111 (sections/10e-connectivity.md, line 111)

- **What decides support:** the accessory-ID scan in §1.2 (verified). Evf1/Evf2/Evf3 are three EVF classes (IDs 0x0101/0x0202/0x0322). Mapping them to VF-2/VF-3/(VF-4) is **inferred** from `EVF_TYPE_VF2/VF3` and `vf-2/vf-3 Version:`.

## 10e-127 (sections/10e-connectivity.md, line 127)

- "Connection to Smartphone" (1719/1720) is a Playback-menu row at **0x7EFFE1DC**, kind 0x100 (verified).

## 10e-195 (sections/10e-connectivity.md, line 195)

| Card update mode (FIRMUP_CLI) | All 9 entries: S, A, M, V, D, T, E/G/H/W/E100, DATE/PICTURE1JPG, N | Boot only. 0x7E544A6F needs a power-on factor of 12 / 0x01000002 / 0x01000001 **and** 0x602A9B54 = 0. 0x7E505694 clears that byte when status 4 reads 0 and 0x7E45D893() ≠ 9. Status 4 is **"O  k"** in the name table (verified), so this is probably the OK key held at power-on (**inferred**). The power-on factor values are not decoded | Hidden / service |

## 10f-69 (sections/10f-debug-service.md, line 69)

- `api_comm_Start_Communication_Storage` 0x7E6763A2 sends type **0** to TPC (verified). DPS sends 1 and MTP sends 4.

## 10f-77 (sections/10f-debug-service.md, line 77)

- The 22-op ADJ accept table is **byte-identical in all 7 bodies** (`adjtbl.py`: E-PL5 0x7F0D25A2, E-P5 0x7EEE01CE, E-M10 0x7E88D356, E-PL7 0x7E8888EA, E-M5 II 0x60D825CE, PEN-F 0x60D624A2) (verified).

## 10f-104 (sections/10f-debug-service.md, line 104)

- **What the info ids are (07-settings.tsv, verified):** info 4012 = prm **0x0DB1 `PRM_MODE_SHIPS_ENABLE`** (FLASH, default 0). Info 4017 = prm 0x5781 (ROM constant, value 0). So the arg ≠ 0 path can never pass on the E-PM2, and the arg 0 path passes only while the ship flag is 0.

## 10f-124 (sections/10f-debug-service.md, line 124)

- **Entry: found (13d §4.3, verified code) (D1 2026-11-09).** A Setup dialog method 0x7EDFD665 (inferred: Monitor Adjust) checks key code 4 and `IOlyApiMaintenance` getShippingInfo(4); only if it returns 1 does it post EVT_REQ_START_VERSION_CHECK 0x9628. SS_MENU_MAIN state 4 maps 0x9628 to state 6 `ID_ST_HIDE_MODE`. There a counter at RAM 0x602BC480 steps on Up → Down → Left → Right → shutter half-press → shutter full-press (0→1→2→3→7→8), and OK with counter 8 returns 0x0A01 = SS 10 state 1 (bytes 0x7EDABA14–0x7EDABA54 inside the handler 0x7EDAB9FE (L1 2026-11-09)). Whether a retail body passes the getShippingInfo(4) gate is **not known**.

## 10f-138 (sections/10f-debug-service.md, line 138)

- **Verified:** `startShooting` 0x7ECDCB10 reads rcv_info.info from the **second** word of the CA event (a3 = a1+4) and maps info **11 → param 12 (VERCHK)** and 12 → param 13 (CAM_MISC_FIRMUP). (A4 2026-11-09)

