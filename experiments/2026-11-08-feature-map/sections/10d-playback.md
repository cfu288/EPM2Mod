# 10d. Playback features: re-examination (E-PM2 v1.6)

- **Scope:** picture-database play modes, the play and edit components, 3D (MPO) playback, BGM import, slideshow and transitions, the opening screen, and the audio DSP.
- **Labels:** **verified** = read in the code or bytes. **inferred** = from names, order or layout. **external** = product knowledge, not from the code.
- **Addresses:** E-PM2 runtime addresses (block-0 offset = address − 0x7E421020), unless a body is named.
- **Scratch scripts:** `$S/hidden/playback/`. They are `fw.sh` (fwmap per body), `modetbl.py`, `sdktbl.py`, `singletons.py`, `immcomp.py`, `ctgparse.py` and `mcon.py`.

## Verdict table

| Feature | Prior claim | Verdict | Real status on E-PM2 | Shipped on |
|---|---|---|---|---|
| Photo Surfing, Event View, Event/Collection, Collage, person/GPS/landmark search | Stub: 46 `api_oldb_dummy_*`; UI and components exist | **CONFIRMED, and extended** | **Stub backend, no GUI path.** No API interface, no Ope class, no sdk group and no GUI string (verified). The stub fails safe at play start (verified) | **None of the 8 bodies.** No body has English text or a real backend. E-P5 and later bodies also drop the components |
| Light box | Active (inf) / "unknown" (§06) | **CORRECTED → Active (code path verified; menu entry inferred)** | Full GUI sub-state in single play (`StDispLightBox*`) that drives `OlyApiPlayLightBox` (23 GUI call sites) | all 8 (component present) |
| Calendar | Active (inf) | CONFIRMED (GUI calls verified) | Active | all 8 |
| Index, select, reserve print (DPOF), protect, erase | Active (inf) | CONFIRMED (GUI calls verified for Index, Select, ReservePrint and PlayCommon) | Active. Protect and erase run through PlayCommon / Select / SingleFrame, not through their own components (see §2) | all |
| Edit components: Aspect, Color, Trim, Resize, Shadow, Redeye, Beauty (e-Portrait), RAW edit, Image Overlay | Active (most) | CONFIRMED for these 9 | Active (GUI call sites verified for each interface) | all |
| EditCalendar, CopyPicture, PlayPanorama, PlayContinuous, PlayCw, PlayEventView, ErasePic/EditRotate/EditProtect components | "unknown" / "dormant" | **Dormant (verified: no API interface or Ope requester)** | Code present, no requester found. EditCalendar and Panorama call stubbed APIs | — |
| 23 edit modes (table 0x7EBB8D88) | Active (most) | **Partly CORRECTED** | Color, trim, redeye, shadow, rotate, resize, overlay, aspect, beauty, RAW and save: Active. The 4 cube/BT modes are Dormant. Regist (0x85): Stub at the API. Pocket (0x84) and SNS (0x8F): UNRESOLVED | — |
| 3D (MPO) playback | Dormant (inf) | **CORRECTED → Partial / likely Active on a 3D HDMI TV (inferred)** | MPO loader, a 3D slideshow type, an HDMI 3D-format query and a "Sel. Image: All / 3D Show" panel all exist (verified). Normal play shows the paired JPEG (inferred) | "3D Show" text in all 8 bodies |
| BGM import (`\BGM\*.WAV`, IKEY) | Active | CONFIRMED (code); entry point **inferred** | Active: a GUI flow with "BGM Import" (string 1782) calls the SoundCtrl import API, and only Olympus-authenticated WAVs pass | "BGM Import" text in all 8 bodies |
| Slideshow | inferred | CONFIRMED | Active. Menu rows Start/BGM/Effect/Slide/Slide Interval/Movie Interval (verified); the component reads the settings (verified) | all |
| Playback transitions (EFFECT task) | Active | CONFIRMED (inferred link to info 97) | Active: slideshow Effect info 97 has 4 values, read by the slideshow component | all |
| Opening screen (registered picture kind 5) | inferred | **CORRECTED → Stub (registration)** | `api_play_dummy_Regist_Play_Rom` has no code; `OpeningScreen` has no API interface. The PLAY_IMAGE 0x85 worker is complete but unreachable (inferred) | — |
| Audio DSP | Active (inf for use) | **CORRECTED (split)** | **Wind cut is user-switched:** Custom Menu "Wind Noise Reduction" (info 434 → prm 0x7871) selects windcut or plain HPF (verified). ReTune, 5-band EQ, notches, DF1 and 3D use **fixed ROM-class settings**. The notch pattern follows movie quality. DRC uses 2 CPRAM values | — |

## 1. Picture-database play modes (Photo Surfing, Event View, Collection, Collage)

### 1.1 Code (verified)
- **Backend:** all `api_oldb_*` are `api_oldb_dummy_*`. Example: 0x7E682EC3 = `mov 15,d0; mov name,a0; call log; mov 1,d0; ret`, as in §06.
- **Wrappers:** `chls_oldb_Get_DB_Existence` 0x7EA245F0 calls `Get_CameraInfo(23)` and then the stub, and returns 1.
- **Fail-safe at play start (verified):**
  - `play_service start` 0x7EAAC5E8 (PlayCommon) calls the oldb object's vtable +100 at 0x7EAAC691.
  - The vtable is at 0x7EC34CB8. Slot +100 is 0x7EC34D1C, which points to thunk 0x7EA272D3 and then 0x7EA245F0.
  - If the result is non-zero (`bne 0x7EAAC6D2`), `Open_DB_Info` is skipped and the play service continues normally.
  - So the stub value 1 means "no DB", and normal playback is unaffected.
- **Components:** the components still exist. Examples: `CmpPPho_PlayPhotosurfComponent` 0x7EB47A3B, `CmpPEvV`, `CmpPEvc`, `CmpPCol`.

### 1.2 How a play component is entered (verified)
- **Component-id enum** `{u32 id, char* name}` at **0x7EC1AFE4**, for example:
  - 0x20101 PLAY_COMMON … 0x20107 PLAY_CW, 0x20108 PLAY_EVENT_VIEW;
  - 0x20119 COLLAGE, 0x2011A EVCOLLECTION, 0x2011B PHOTOSURF, 0x2011C CONTINUOUS_SHOTS;
  - 0x20121 LIGHTBOX, 0x20123 CALENDAR;
  - 0x60105 FUNCTION_OLDB_CONTROL.
- **Requests:** `changeMode` 0x7E97691F takes a pointer to a target id. It stores the id through 0x7E976F40 at `(184,obj)`.
- **Event factory:** 0x7E977252 turns the id into a "change component" event through the hash at **0x7EBE24B4**. This table covers every play id, so the factory itself is generic.
- **Switcher:** the idle-state handler 0x7EB97E25 is a statechart that maps each event to a component and a state entry. Photosurf is event **11830**, component 53, entry 0x7EB99784, which sets state 19.
- **The requester is the gate.** Each `OlyHfwOpe*` "start" gets its id from a constant getter, for example `OlyHfwOpeEdtAsp::start` 0x7E9D1528 → getter 0x7E9D13B4 = PLAY_EDIT_ASPECT.

### 1.3 Reachability on the E-PM2

**Verified negatives:**
- **API interfaces.** I listed every lazily built `OlyApi*` singleton getter in ~~0x7E9BF000–0x7E9CE000~~ 0x7E9BFA7E–0x7E9CDEBE (the first and last getter (L1 2026-11-09)) (39 getters; this is the first series only, at least 5 more exist at 0x7E99D2DD–0x7E99FF14, 13d §6.2 (D1 2026-11-09)). Each one matches one `sdk api` letter group, and none is for PhotoSurfing, EventView, EventCollection, Collage, ContinuousShots, CopyPicture, PlayPanorama, EditCalendar, OpeningScreen, OLDBControl or GpsCtrl. These classes exist only as names in the debug name table at 0x7EBD5000.
- **Ope classes.** No `OlyHfwOpe*` class string exists for them. The 43 Ope class names are listed in the scratch output.
- **Component-id constants.** In the Ope region ~0x7E9CD000–~0x7E9E2000 (a page-rounded search window (L1 2026-11-09)), no immediate equals the ids of EVENT_VIEW, COLLAGE, EVCOLLECTION, PHOTOSURF, CONTINUOUS_SHOTS, PLAY_CW, COPY_PICTURE, PANORAMA, EDIT_CALENDAR or EDIT_ROTATE. The only hit is a `cmp` of EVENT_VIEW in a mode-flag routine at 0x7E9E5A97. All edit and play components that the GUI uses do have such getters (§2).
  - Caveat: ERASE_SELECT_PIC and EDIT_PROTECT have no getter either, so ids passed indirectly cannot be ruled out completely.
- **GUI.** No GUI string (0x7EEE–0x7F02) names photosurf, event, collage or collection. The GUI sub-states are SS_REC … SS_BTRECEIVE (0x7EFDD23E), and none of them is a DB mode.
- **English text.** No body's English table has "Photo Surf", "Event", "Collage", "Collection", "Landmark" or "Person" (verified, 8 bodies).

**What a user would see:**
- No path was found.
- If the debug shell forced the mode, the components would get "no DB" or count 0 from every `chls_oldb_*` call (inferred).
- The draw helpers `api_tft_dummy_Draw_Image_*_Composite` are also stubs.

### 1.4 Cross-body (verified)

| Body | `api_oldb` names | Backend | `CmpPPho/PEvV/PEvc/PCol/Pct` components |
|---|---|---|---|
| E-PM2, E-PL5, E-PL6 | 46, all `_dummy_` | stub (log, return 1) | present |
| E-P5, E-M10, E-PL7 | 48, all `_dummy_` (adds Get_Date_Latest/Oldest_By_Date) | stub, e.g. E-PL7 0x7DC1E6D9 = `mov 15,d0 … mov 1,d0; ret` | **absent** (source names gone; the API name table and component ids remain) |
| E-M5 II, PEN-F | names stripped | **compiled out**: `chls_oldb_Get_DB_Existence` (E-M5 II 0x607C1ACD, PEN-F 0x607B20CF) logs and returns constant 1; `Close_DB_Info` 0x607C1452 hard-codes status 1 | absent |

- **Conclusion:** no PEN/OM-D body in this set has a real picture database. The feature is a leftover of the shared code base (the compact origin is inferred, as in §06).

## 2. Play and edit components

Basis for "Active": the GUI calls the component's `OlyApi*` interface (singleton getter callers in 0x7ECA–0x7EE2, verified count), and an Ope class requests the component id (verified getter).

| Component (id) | API getter → GUI call sites | Requester | Status |
|---|---|---|---|
| PlayCommon (N), SingleFrame (O), Index (P), Select (Q) | 0x7E9C5850 → 100, 0x7E9C794C → 94, 0x7E9C5FF8 → 19, 0x7E9C7424 → 27 | getters 0x7E9DECD3 (single), 0x7E9DC31C (index), 0x7E9DD8FA (select) | Active |
| LightBox (X, 0x20121) | 0x7E9C667F → 23 | 0x7E9DCCF5 | Active (see below) |
| Calendar (W, 0x20123) | 0x7E9C5389 → 11 | 0x7E9DB94E | Active |
| SlideShow (U), Movie (R), Record (S), Sound (V) | 8, 9, 7, 15 | 0x7E9E027E, 0x7E981927, 0x7E9DD636, 0x7E9DFD12 | Active |
| ReservePrint (T) | 0x7E9C8D07 → 20 | 0x7E9E13B3 | Active |
| EditResize Y, Trim Z, Aspect a, Color b | 4, 8, 9, 14 | 0x7E9D3F66, 0x7E9D49E7, 0x7E9D13B4, 0x7E9D1F4D | Active |
| Shadow c / Redeye d (by order) | 5 / 5 | 0x7E9D4307 / 0x7E9D3B47 | Active |
| Beauty e (e-Portrait) | 0x7E9C290C → 4 (incl. `userGuiCallBackJpegEdit` 0x7EDCB328) | 0x7E9D1A62 | Active |
| EditRaw f, ImageOverlay g, SelectOverlay h | 24, 13, 5 | 0x7E9D2F67, 0x7E9D25EB, 0x7E9E1909 | Active |
| EditProtect, ErasePic, EditRotate | no interface of their own | none found | Dormant components. The features themselves are Active through `PlayCommon::changeProtect/erase` (N10/N11) and `PlaySingleFrame::rotateImage` (O12), which have GUI callers (inferred mapping) |
| EditCalendar (0x20115) | none | none | Dormant. Its drawing is `api_tft_dummy_Draw_Image_Calendar_Composite` 0x7E68E53A (stub) |
| CopyPicture | none | none | Dormant (also needs a second medium) |
| PlayPanorama | none | none | Dormant (`api_play_dummy_Alloc_Panorama_PlayHandle`, §06) |
| PlayContinuous (0x2011C), PlayCw (0x20107), PlayEventView (0x20108) | none | none | Dormant |

- `GCPnl_Play::CheckContinuousNext` is key-repeat movement, not PlayContinuous (inferred from the name).
- `OSDControl::customDisplay` (r13 → 0x7E98C692) has GUI callers 0x7ECE9C57 / 0x7ED01B0B and calls `api_*` directly, so the OSD custom-window feature does not need CmpPCw (verified call edges).

**Light box (verified GUI code; how it is entered is inferred):**
- The SsPlaySingle state ids at 0x7EFDC50C include `ID_ST_DISP_HIGHLIGHSHAD` = 14 and `ID_ST_DISP_LIGHTBOX_PREPARE` = 15, followed by LIGHTBOX, SCOLL, MOVE, ZOOM and SETBASE.
- The handlers include `doCmd_SsPlaySingle_StDispLightBox_EvtStChgMainDial` 0x7ED0E05B and `…_EvtKeyFn2On` 0x7EDB9FC7.
- The prepare handler 0x7EDB8C08 is reached from the GUI handler table at 0x7EFD7AA4. **Corrected:** 0x7EFD7AA4 is slot 14 of SS_PLAY_SINGLE's entry-function array (0x7EFD7A6C), so 0x7EDB8C08 is the **entry** function of state 15 `ID_ST_DISP_LIGHTBOX_PREPARE`, not a handler-table row. The INFO-key release in the display states returns that state through `CPlaySingleFrame::getJumpState` 0x7ED09135 (13d §4.3) (D1 2026-11-09). It checks the picture count through MediaCtrl, then calls `CPlayLightBox::start` 0x7ED05C54.
- The light-box display sits next to the Highlight&Shadow display. This matches the "▶ Info" display list (Image Only / Overall / Highlight&Shadow / Light Box) that the PENs of this period offer (external). I did not decode which event of the handler table enters it. (Answered in 13d §4.3: one stop of the INFO display cycle, enabled by ▶Info "@A021@" (D1 2026-11-09).)

**Edit modes (table 0x7EBB8D88, §05):**
- 0x01/0x02/0x0C color, 0x07 trim, 0x08 redeye, 0x10 shadow, 0x80 rotate, 0x81 resize, 0x86/0x91 overlay, 0x87 aspect, 0x88 beauty, 0x90 save and 0x92–0x94 RAW back the Active components above (link inferred from the component/edit names).
- 0x89–0x8C `play_cube_*` serve Bluetooth/PENPAL only, so they are Dormant (§05: no accessory port).
- 0x85 regist: see §5.
- 0x84 pocket and 0x8F SNS flag: not traced.
- `api_picfile_Check_Create_PictureFile` 0x7E683DB6 maps API modes 1..33 to these internal modes (jump table 0x7E7CF458; for example → 132, 129, 8, 10, 11, 14, 133, 16, 131, 7, 12, 1, 2). The size check therefore knows every mode, including 0x85 (verified).

## 3. 3D (MPO) playback
- **Code (verified):**
  - `play_load_mpo_exec` 0x7E946CC4 (PLAY_LOAD kind 11) parses APP2/MP-index. DCF knows `FILE_TYPE_MPO` and `FILE_TYPE_MPO_JPEG` (0x7E5C6B6E).
  - `CapImg play_image(PLAY_MPO_3D)` sits in the single-picture drawer 0x7EA0570E.
  - The slideshow treats Slide value **7** as 3D (`APP_DISP_BG_3D_PLAY`, 0x7EA683F8; 0x7EB69367).
  - `Disp_Change_OutputDimensions_Exec … 3D` exists for single frame, one-move and slideshow (0x7EB50118, 0x7EB50481, 0x7EB66B14).
- **HDMI 3D (verified code; meaning external):**
  - `api_disp_Disp_Get_3D_Format_Size` 0x7E6798C5 maps 0/64/128 to 0/6/8, asks the display driver 0x7E6B49CB and tests bit 0 (`btst 1` = mask 0x01) (audit 2026-11-09).
  - 0/6/8 match the HDMI 1.4a 3D_Structure codes: frame packing, top-and-bottom, side-by-side half (external).
  - `CameraCommon::getDisplaySupport3D` is sdk A18.
- **GUI (verified):** 0x7ED054FB builds a panel titled "Sel. Image" (572) with the items "All" (442) and "3D Show" (982). It is called from handler 0x7EDB61FE (table 0x7EFD6754). **Corrected:** 0x7EFD6754 is slot 15 of SS_PLAY_MOVIE_SLIDE's entry-function array (0x7EFD6718), so 0x7EDB61FE is the **entry** function of SS7 state 16 `ID_ST_3D_IMG_SEL_MENU`, not a handler-table row (13d §4.3) (D1 2026-11-09).
  - On the E-PM2 the Slide list (info 101) is only 0/2/3 (mcon, verified), so 3D is not in the normal Slide menu.
- **Reading (inferred):**
  - On a 2D screen the camera shows the JPEG of the JPEG+MPO pair.
  - With a 3D-capable HDMI TV, "3D Show" plays the MPOs.
  - Not traced: which state shows the panel, and the condition that enables it (probably getDisplaySupport3D).
- **Related, for section 03/06:** `rec_3d_make_mpo` 0x7E70C23F and `rec_3d_write_mpo` 0x7E70BF3C are real code (caller chain 0x7E70BD7F), and the GUI has `MODE_EXPOSE_3D_JUDGE_NG`. The §06 claim "3D photo dormant because combine is stubbed" needs a re-check.

## 4. BGM import
- **Code (verified, §05):** `play_rom_chk_bgm` 0x7E94A62D allows ≤ 14 files of ≤ 6,145,024 bytes, and `aud_tool_wav_judge_OLYMPUS_authentication` must return 2. `play_regist_bgm` 0x7E9499A6 writes the WAV to flash and the entry to blob setting 0xE001.
- **API (verified):** `SoundCtrl::start/get…/regist/end/play/stopImportSound` (sdk D04–D11) → `OlyHfwOpeSndCtl::*ImportSound` 0x7E9E3974–0x7E9E3F7E → `OlyHfwOpeSndCtlSoundEvFw` (logs `SLIDESHOW_IMPORT_BGM_SEM`).
- **GUI (verified):** the SoundCtrl getter 0x7E9CD7B0 has 20 GUI call sites. The cluster 0x7EDF26B2–0x7EDF2C5D loads string 1782 "BGM Import", and `ImportBGMProcessCallback` exists (0x7F0042DB).
- **Entry (inferred):**
  - The semaphore name ties import to the slideshow BGM setting (info 110: values 1–4 and 0 = Off, verified mcon).
  - The import is user-driven from the menu. It is not run by the updater or at boot. `play_rom_chk_bgm` has one caller, `play_rom_main_exec` 0x7E94A33D, whose only caller is the PLAY_LOAD task 0x7E9456C5 (verified). The request is built by `api_play_Check_BGM_File` 0x7E686B22. I did not trace which callers reach that function.
  - The menu row that opens it was not decoded.
- **Usability:** the user needs an Olympus-signed WAV (IKEY/`ecor` check). External: Olympus offered BGM downloads for this purpose.

## 5. Slideshow, transitions, opening screen
- **Slideshow rows (verified bytes):** sub-item table group 20 at 0x7EFEFC90 has Start (265, info 1), BGM (1657, 110), **Effect** (1009, 97), Slide (962, 101), Slide Interval (921, 289) and Movie Interval (901, 284). §07 warns that this table is a superset.
- **mcon lists (verified):** 97 = {1,4,5,6}, 101 = {0,2,3}, 289 = {2..10} s, 284 = {0,1}.
- **Use (verified):** `slideshow_start_slide_show` 0x7EB690D5 reads 101 and 97, and the GPU variant 0x7EB68E2C reads them too.
- **Transitions:** the EFFECT task (§05) provides fade, slide, index zoom, 3D overlap and touch scroll. The mapping from Effect values to effect types was not traced. Active (inferred).
- **Opening screen:**
  - The worker `play_regist_regist_pic` 0x7E949741 (edit 0x85, resource kind 5) and the ROM loader for "CONST or REGIST image" (0x7E94A33D) are complete.
  - But `api_play_dummy_Regist_Play_Rom` is a dummy with no code reference.
  - `api_play_dummy_Delete_Play_Rom` 0x7E68704E only logs and returns 0. Its callers are 0x7E9E36D4 and 0x7E9E7AD1.
  - `OpeningScreen::*` has no API interface.
  - **Status: Stub** (verified for the API layer; "the user cannot register a picture" is inferred). The boot logo uses the CONST image.

## 6. Audio DSP: user settings versus fixed values
- **Wind Noise Reduction is a user setting (verified):**
  - A 16-byte record table at 0x7EFF8250 holds `{group, label, info, 0, kind, help, …}`. Group 8 has Movie Effect (1492, info 444), **Wind Noise Reduction (1087, info 434, help 1491)** and the mic level (1373, info 435, help 1490).
  - The layout is inferred. These look like the Custom Menu item lists that §07 did not find.
  - **Corrected (13d §5) (D1 2026-11-09):** the Custom Menu table starts at **0x7EFF7E80** (78 rows, page 0..9 = A..J); 0x7EFF8250 is page **H**'s first row (Quick Erase). Group 8 is page **I** (Movie). The "mic level" row (1373) is labelled **Recording Volume**.
  - Info 434 → prm **0x7871** (mcon values 0/2/6/10, verified).
  - In `cmd_set_dsp_param_on` (0x7E95136C), when the mode at 0x605D8744 is 1 and the argument at (536,sp) is 1, it reads 0x7871. Non-zero → windcut 0x7E951BDE with the value as argument; zero → plain LHPF 0x7E951ADF.
  - The meaning Off/Low/Standard/High is inferred from the 4 values and the external menu.
- **Mic level:** info 435 → prm 0x44A1 {2,6,10}. It is read in `aud_seq_rec_command_rec_init` (07-settings hints). This is a gain, not a DSP block.
- **Fixed values (verified device class in 07-settings.tsv):**
  - ReTune 30162, 5-band EQ 30194, notch 30050–30130, DF1 30290, 3D 30034, LHPF 30018 and windcut 56004 are **ROM-class** tables. None has an info id or a GUI setter.
  - DRC 13393/13409 are CPRAM with no info id, so they are fixed as well.
- **Automatic choice:** the notch pattern follows movie quality (34145 → pattern 5 or 1, §05). So only wind cut and mic level are user choices.

## Open questions
1. Decode the GUI handler tables (0x7EFD5E00…, 0x7EFD6754, 0x7EFD7AA4). That would name the key or event that enters light box, "3D Show" and BGM Import. (Answered in 13d §4.3: 0x7EFD6754/0x7EFD7AA4 are entry-function arrays; light box = INFO display cycle; 3D Show = play-start chooser 0x7ED05440; BGM Import = a `userMenu` item, not an Ss row (D1 2026-11-09).)
2. What edit modes 0x84 (`play_pocket`) and 0x8F (SNS flag) are, and whether any API mode reaches them.
3. Whether E-P5 and later bodies still route light box and calendar the same way (only the component names were compared).
4. 3D shooting: are `rec_3d_make_mpo`/`write_mpo` reached in SCN 3D on the E-PM2? This contradicts the §06 "dormant" reading.
5. The mapping of info 97 Effect values {1,4,5,6} to EFFECT_EXE bits.
6. What 0x605D8744 = 1 (movie record?) and (536,sp) mean in `cmd_set_dsp_param_on`.
