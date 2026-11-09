# 06 — C++ application layer: shooting and playback components, picture database

**Scope:** block 0, about 0x7E966000–0x7EBA1020 (HIGHLEVEL_MAIN and the C++ code it runs), plus the framework base code at 0x7EBA0000–0x7EBA8000 that this code uses.
**Labels:** **verified** means I read the code or bytes. **inferred** means the claim comes from strings, names or layout only.
Helper scripts are in the scratch dir (`.../scratchpad/app/`: `vt.py` dumps vtables, `cmdtbl.py` finds command tables, `vtref.py` finds code that loads a vtable).

## Overview

- The layer is C++ statechart code built on the **IBM/Telelogic Rhapsody OXF** runtime. **Inferred, strong:** the OXF strings are copied word for word (`"underflow in OMREactive less then 0 0 Config's"` at 0x7EBA6695, `"Could not create timeout. It is lost"` at 0x7EBA68BF, `"\nInternal Error - No last state in history\n\n"` in 6 modules, `rhp_take_over` at 0x7E966AB0). The method names follow the Rhapsody code-generation pattern: `rcv<Ev>In_<STATE>`, `entry<STATE>`/`exit<STATE>`, `guard<Ev>In_<A>_To_<B>`, `transit<Ev>On_<A>_To_<B>`, and events called `evTra…`.
- HIGHLEVEL_MAIN is the OXF main thread: one event loop that sends event objects to "reactive" components (**verified**, see §1).
- There are seven layers (layer order **inferred**; each address range **verified** from string placement):
  1. `api_*` low-level C API (0x7E67xxxx–0x7E68xxxx). This includes `api_*_dummy_*` stubs.
  2. `Cap*` "capabilities", which wrap devices: ImagePlayer, ThroughImage (live view), Take, RecView, MediaInfo, and others.
  3. `CmpSts_*`/`CmpSqp_*` controllers and statechart "sequence parts".
  4. `Cmp_*` components.
  5. `Ctg_*` categories that select components.
  6. `OlyHfwOpe*` "operation" classes, which turn API calls into events.
  7. `OlyApi*Controller`. A large debug shell, `sdk api`, can call this API surface directly (635 commands).
- **Main dormant-code finding (verified bytes, inferred meaning):**
  - The **picture database backend is stubbed.** All 46 `api_oldb_*` entry points are `api_oldb_dummy_*`. Each one logs its name and returns 1.
  - So Photo Surfing, Event View, Event/Collection, Collage and the person/GPS queries have full UI and component code, but no database behind them. They look dormant on the E-PM2.

## 1. Architecture: how HIGHLEVEL_MAIN dispatches

**Task entry 0x7E966A78 (verified):**
- It calls `0x7EBA792C(d0=0)`.
- That function gets a framework singleton through `0x7EBA49CC(1)`:
  - `0x7EBA4A63` creates the object once, as a static object at RAM 0x605EF2F0.
  - The constructor 0x7EBA49AE calls the base constructor 0x7EBA70E8 (base vtable 0x7EC92210), then sets the vtable to **0x7EC91A44**.
  - `0x7EBA78FB` stores the pointer in 0x605EF7E8.
- It then calls vtable slot 3 (+12) = **0x7EBA49EA, which references the string `mainThread`**. If the global 0x602B4A88 is non-zero, it calls slot 14 (+56) instead.
- When the loop returns, the task deletes the object at 0x602B0C74. The destructor is 0x7E967347 (it sets vtable 0x7EBCDBB8), and `0x7EBA62EB` is operator delete.

**Event loop 0x7EBA74BB** (mainThread with d0=0) (**verified** control flow; the names are OXF terms, **inferred**):
- It takes an event from the queue object at `this+64`. First it tries a non-blocking get, `0x7E9675F2` (queue vtbl+4). If the queue is empty, it does a blocking get, `0x7E967673` (queue vtbl+24).
- `id = ev->vtbl[3]()`. If `id == -6`, the loop ends or restarts. This matches an OXF end-thread event; not checked against OXF source.
- `dest = ev->vtbl[9]()`. Then `this->vtbl[4](ev)` = 0x7EBA73FF, which calls `dest->vtbl[6]` (+24, takeEvent). If 0x602B4A88 is set, it calls `dest->vtbl[23]` (+92) instead.
- If the result is 3, it calls `dest->vtbl[4]`.

**Event classes (verified):**
- Each event class has an 18-word vtable. Example: vtable 0x7EBDD058, built by constructor 0x7E970EE8. The constructor writes the event id as a u16 at `+4` (11964 here).
- Slot 2 (0x7E970F1B) is `isTypeOf(id)`. It compares the id with 11964, then calls the parent class's check 0x7E96C3F1. This is a hand-made RTTI.
- Slot 3 is `getId` = 0x7E966B30 (`movhu (4,a0),d0`). ~~930 data words point to 0x7E966B30~~ **1,273 data words point to 0x7E966B30** (each followed by slot 4 = 0x7E966B37), so there are **1,273 event vtables with 1,268 distinct ids**; 250 of the classes are never constructed (13c §4) (D1 2026-11-09).
- ~~Most event vtables are in 0x7EBCE000–0x7EBF0000.~~ The event vtables span **0x7EBC0000–0x7EC92200**; only 45% lie in 0x7EBCE000–0x7EBF0000. The constructors sit in each package's module (559 of them in Cap/Cmp code), not in TraShareTakeStatus. 0x7E96B000–0x7E9823AB is not an "event constructor" range: of its 2,603 functions, 1,388 are event methods; the rest is operation-class code (`OlyHfwLowApiWrap`, `OlyHfwOpeLevel`, `OlyHfwOpePlyCom`, `OlyHfwOpePlyMov` and reactive classes; 13c §4, §7) (D1 2026-11-09). (`Tra` = transition framework, **inferred**.)

**OS wrapper "HLS" (verified strings + code):**
- Functions 0x7E967A99–0x7E9690EE (`HLS_CRE/DLE/SEE/WAE` for events, `HLS_CRQ2/REQ1/WRQ1` for queues, `HLS_*S` for semaphores, `HLS_IST/SLT/WKT` for tasks).
- Logger 0x7E9670E9 (**11,491 callers**, prints the prefix `[HLS]: `). Calling convention: `d0` = level, the format string at (4,sp).
- Growable array 0x7E966C01. Operator new 0x7EBA62E3 and 0x7EBA62DB.

**Class layers and base classes:**

| Layer | Where | Evidence |
|---|---|---|
| OXF reactive base: a 35-slot vtable whose methods are at 0x7EBA6449–0x7EBA6D64 | ~~e.g. vtable 0x7EC6C320~~ The base vtable is **0x7EC91FE8**; 0x7EC6C320 is a derived component vtable (slot 0 = 0x7EB08A15). Slot 15 = getCurrentEvent, slot 6 = takeEvent, slots 32/33 = rootState_entDef/dispatchEvent (13c §7) (D1 2026-11-09) | **verified** slot dump; `OMREactive` strings in slots 7–8 |
| `Cmp_ComponentManager` (`Cmp_ComponentManagerWithBoot`, 0x7EA7D072) | slots 35–51 of the component vtables; code 0x7EA7CB15–0x7EA7DBAC. 0x7EA7D072 is the inherited getName that 26 component vtables share, so it does not mark a file (13c §7) (D1 2026-11-09) | **verified** slot dump of 0x7EC6F70C |
| `Cmp_PlayComponentBase` | base constructor **0x7EB0A5E7**; 58-slot vtable **0x7EC6F70C** (slots 52–57: `sound_state`, `playsound_set_volume`) | **verified**: 10 derived constructors call it (next row) |
| Derived constructors (vtable they load) | 0x7EAAB4B8 (0x7EC59A00), 0x7EAAE3C3 (0x7EC5A360), 0x7EAB160C (0x7EC5B144), 0x7EB055F9 (0x7EC6C1C0), 0x7EB1A7E6 (0x7EC70B48), 0x7EB28B48 (0x7EC74F9C), 0x7EB3E58B (0x7EC7A16C), 0x7EB4264A (0x7EC7DDCC), 0x7EB54718 (0x7EC81A90), 0x7EB6C601 (0x7EC861B8) | **verified** call edges. Which file each belongs to is **inferred**: they sit near the module boundaries of Function, PlayCommon, BackgroundControl, Calendar, Continuous, Evcollection, Panorama (×2), Select and SlideShow. |
| `Cmp_ShootingComponentBase` / `Cmp_StillShootingComponentBase` | 0x7EA7A486 / 0x7EA8001A | **inferred** (strings) |
| Category (`Ctg_ComponentSwitcher` 0x7EB9473A, 5 vtable refs) | 0x7EB94000–0x7EBA0000 | **inferred** |
| Transition manager (`Com_ActiveTransitionManagerBufferd`; strings `newCapabilityStart`, `previousCapabilityEnd`) | 0x7EB8A000–0x7EB8C000. The same area also holds `Cab_CameraBase` and the standby/shoot/play/function mode machine (Com_ framework 0x7EB84345–0x7EB8C265, 13c §6) (D1 2026-11-09) (A5 2026-11-09) | **inferred**: the components start and stop capabilities through "transitions" |

**Caveat:** `vtref.py` counts vtable slots as consecutive code-range words, so packed vtables can make the count too high. Treat the 58/35/288 slot counts as upper bounds.

**The base methods are copied into each file (verified strings, inferred cause):**
- The strings `Cmp_PlayComponentBase::transfer_image_start`, `select_current_start`, `is_protect`, `erase_start`, `change_protect_start` and the `@@@@@ APP_MEDIA_COPY_*` messages are referenced again inside every Play/Edit module. Examples: 0x7EAAC284 (PlayCommon), 0x7EAB98B2 (EditAspect), 0x7EAEA343 (ErasePic).
- So this base code is probably inlined from a header or macro into each component. Expect near-identical functions in every component. **Corrected cause (inferred, strong):** statechart inheritance; each generated class carries copies of its base chart's code (13c §3) (D1 2026-11-09).

## 2. Shooting features

**How the component is chosen (verified):**
- `CtgStl_StillImageShooting::getComponentInstance` is at 0x7EB9D939, reached through the data word 0x7EC90870.
- It hashes the component id (1..73) into a 32-entry `{id, target}` table at **0x7EC90664**.
- Every case logs a name and then calls the **same** constructor 0x7EB7A6C8. That constructor makes one 6,188-byte singleton, stored at 0x602B48A4.
- So the shooting "components" are one object. The modes differ by the **sequence** they select (`changeSequence(nextSeqId)`, 0x7EA800DB).

| Ids | Logged name |
|---|---|
| 1, 2, 7, 11–14, 64, 66–71 | `Cmp_ShootingComponent` |
| 6 | `Cmp_PanoramaShootingPcComponent` |
| 8 | `Cmp_EPortraitShootingComponent` |
| 9 | `COMPO_SHOOT_MOVIE` → `Cmp_ShootingComponentFactory` |
| 10, 65 | `Cmp_MultiExposureShooting` |
| 16, 17 | `Cmp_3dShootingAutoComponentFactory` |
| 72, 73 | `Cmp_PictBracketShootingComponentFactory` |

**Sequence parts:** these are Rhapsody statecharts with states such as STANDBY, READY_TRIG2, SELFTIMER_WAIT, TAKE_PICTURE, SECOND_WAIT, END_WAIT, MOV_READY, MOV_RECORDING and MOV_END.

| Feature | Code (source file, first string ref) | How it works | E-PM2 visibility |
|---|---|---|---|
| Base still/movie sequence | `CmpSqp_SequencePartsBase.cpp` 0x7EA87D37–0x7EA99085 (442 unique strings); vtable 0x7EC556C4 | Half-press/full-press guards; self-timer; movie record states; AE/AF lock; touch-shutter gesture (`NOTIFY_GESTURE_TOUCH`); battery, heat, HDMI and USB app events (`APPEVENT_CAMST_*`, `APPEVENT_PWR_OFFHEAT`) — **inferred** from strings | visible (**inferred**) |
| Interval shooting and time-lapse movie | Inside SequencePartsBase: `rcvStartIntervalShootingIn_active` 0x7EA98808, `setIntervalShootingNextTime` 0x7EA98F94, `rcvCreateTimeLapseMovieIn_active` 0x7EA991DD, `startIntervalShooting_First` 0x7EA99881. Guard `isStartIntervalShootingEnable` 0x7E969C11. API entry `OlyHfwOpeShoot::startIntervalShooting` 0x7E98849B. | **Verified:** the guard reads mode **482** through 0x7E6FCC91 (its log calls this `MODE_INTERVAL_SHOOTING_ONOFF`), plus take-status flags 18 and 9, a RecView/recording check (0x7E969A6A), and mask 0x0E (bits 1–3; `btst 14`) of the interval state 0x602B0CDC (audit 2026-11-09). 0x7E98849B calls the guard and then constructs event id 12047 (vtable 0x7EBDE7B0, constructor 0x7E971CB7). **Inferred:** the camera sleeps between shots (`CBS_START_INTERVAL_SHOOTING_SLEEP`, `API_SHUTDOWN_REASON_INTERVAL_SHOOTING = 0x07`, `API_WUI_INTERVAL_SHOOTING` wake reason). The movie is built by `api_play_Create_TimeLapseMovie` (0x7E686E96). Menu-side code is at 0x7ECD1BC1–0x7ECDA5C6. | Complete code. Whether the E-PM2 menu exposes it is **unknown** (open question). |
| Multiple exposure | `CmpSqp_SequencePartsMultiExposure.cpp` 0x7EA9A614–0x7EA9C881; `CmpSts_MultiExposureFunctionController` (strings at 0x7EA72E43–0x7EA743C9); `Cap_MultiExposureScaleFactory.cpp` 0x7EA44E5E | Keeps take handles, combines them (`entryMesCombineImage`), overlays a saved RAW (`rcvOverlayIn_active`), and shows a play-scale view (`MES_PLAYSCALE_ON/OFF`). **Verified:** `CapMex_MultiExposure` 0x7EA44886 calls the stub `api_rec_dummy_MultiExp_Start/End` **and** the real `api_rec_Bayer_MultiExp` (0x7E689C04). The stub is only a no-op hook. | visible (**inferred**) |
| e-Portrait | `CmpSqp_SequencePartsEportrait.cpp` 0x7EA99F29; `CmpSts_EPortraitShootingEditer.cpp` 0x7EA70126 | After the take: face check (`evTraCmpSts_CheckFace` / `NoFace`), "clear skin" beauty edit, two rec-views, and records both images (**inferred**) | visible as SCN e-Portrait (**inferred**) |
| Panorama (PC stitching) | `CmpSqp_SequencePartsPanorama.cpp` 0x7EA9CEA1–0x7EA9D108 | Counts frames (`_panoramaShootCount`, `getPanoramaCountMax`). **Verified:** the real `api_rec_Start_TakePanorama` (0x7E688C7D) has caller 0x7EA34520. In-camera stitching is a stub: `api_rec_dummy_Record_Media_Panorama` (caller 0x7EB92DF5), `api_rec_dummy_Make_Panorama_*` (no callers). | PC-assist panorama visible; in-camera sweep panorama dormant (**inferred**) |
| 3D photo | `CmpSts_3dImageController.cpp` 0x7EA6E566 (events `Start3dCombine`, `Start3dOverlap`, `StartMpoRecording`); 3D path in `CmpShc_ShootingSequenceBase.cpp` 0x7EA6A6CF | Two takes, then combine, then MPO. **Verified:** `start3dCombine` 0x7EA4D845 calls `api_rec_dummy_Execute_3D_Still` (0x7E68C72F). That stub logs and then calls 0x7E880EFF(0xF00F0000, 1), probably to raise a done event. `Record_3D_Still`, `Make_YC_3D_Still` and `RecView_3d_Comb` are also stubs. The real `api_rec_Start_Take_3d` (0x7E68B98A, caller 0x7EA4D25F) exists. | The combine step is stubbed, so it is probably dormant (**inferred**). Separate: `start3DLensShooting` (3D-lens path, API M69). |
| Art/picture bracketing | factory ids 72/73; `RecordController::recordMediaPictBkt` (0x7EA785CF), `evTraCapRec_RecordMediaPictBkt` | Records several processed images from one take (**inferred**) | visible (ART BKT) (**inferred**) |
| Live-view zoom | `CmpSts_LiveViewZoomController.cpp` 0x7EA71AF9 (strings from 0x7EA70EB5) | States viewIdle, viewFrame and zoomThrough. Handles zoom frame start/end, scroll, rate (`MODE_THROUGH_ZOOM_50..140`; API `ZOOM_RATE_5X..14X`) and touch release (**inferred**) | visible (**inferred**) |
| MF assist | `CmpSts_MfAssist.cpp` ≤0x7EB7D14B–0x7EB7E77A: the class starts at or before its ctor 0x7EB7D14B (13c §5) and includes `evTraReqShtEndMfAssist` 0x7EB7D7E8; 0x7EB7DEB9 is only modules.tsv's first function that names the file (C2 2026-11-09) | `MfAssistOn/Off` states. Magnifies on focus ring, dial and arrow events (`evTraCmpSts_NotifyFucusRing`, …) (**inferred**) | visible (**inferred**) |
| Multi-through (preview grid) | `CmpSts_MultiThrough` 0x7EB7EDC0–0x7EB7F364 | `evTraReqShtStart/EndMultiThrough`, move forward/back. API enum `MULTI_THROUGH_EXPOSE / MAGIC_FILTER / WB` (**inferred**: a live preview of several variants) | **unknown** |
| Rec view | `CmpSts_RecViewController.cpp` 0x7EA75B1B (prepare → standby → view; slide rec-view); `CapRev_RecView.cpp` 0x7EA46813; `CmpSts_RecordController` (strings 0x7EA78491–0x7EA79762) | Shows the post-shot image. RecordController drives media writes (`recordMedia`, `MEDIA_ACCESS_STARTED/FINISHED`) (**inferred**) | visible |
| Movie effects / tele-converter | `rcvShtCtrlMovieEffectIn_active` 0x7EA7A7A0, `rcvShtCtrlMovieTelecon` 0x7EA7AA26 (in `Cmp_ShootingComponentBase.cpp`) | One-shot effect, multi-echo (`CTRL_EFFECT_MULTIECHO_*`), digital tele-converter (**inferred**) | partly (**inferred**) |
| Live Guide, live bulb, touch AF, AE/AF lock | API M80–M85, M66/M67, M58; `setAFLock` 0x7EA7BDCB, `setAELockSync` 0x7EA7B483 | **inferred** | visible |
| USB connection, PC link, pixel mapping, media mount | Inside the Panorama-to-Function span: `CmpCst_Communication` (`connecting: MTP / MassStorage / PC Link`, 0x7EA9E966); `CmpCst_Function.cpp` 0x7EAA7E9E (PixelMapping 0x7EAA8FF9–0x7EAA94A5, `MediaMount Start@Cmp` 0x7EAAACC8) | **inferred** | visible |
| Bluetooth image transfer | `CmpFunction` 0x7EAA259A–0x7EAA4A0B (searchDevice, requestPairing, sendImage, receiveImage); `OlyHfwOpeBluetooth` 0x7E9D03EF | **inferred:** support for the PENPAL PP-1 accessory | The E-PM2 has no accessory port, so this is probably dormant (**inferred**). The same applies to the EVF state API (A15, `EVF_TYPE_VF2/VF3`). |

**Capabilities used by shooting:**
- `CapThr_ThroughImage.cpp` 0x7EA1852F, plus `CapThr_ThroughBuffering` 0x7EA20972 and `CapThr_ThroughImageFacade` 0x7EA384CA. These handle live view: AF frame quads, highlight/shadow display (`highlight_data.hi_thresh`) and buffering.
- `CapTak_Take.cpp` 0x7EA362F8.
- `CapRev_RecView.cpp`.
- These attributions are **inferred** from strings.

## 3. Playback and edit components

**Common pattern:** each component is a reactive subclass of `Cmp_PlayComponentBase`. API "operation" classes `OlyHfwOpePly*` drive it with `evTraCmpPly_*` events (**inferred**). Its debug strings follow `<feature>_<action>_start/end`. Address = first string reference of the source file (**verified**). What each component does is **inferred** from strings unless marked.

| Component (source) | Addr | What it does | E-PM2 |
|---|---|---|---|
| CmpPCom_PlayCommonComponent | 0x7EAABC33 | Starts the play service. `Set_PlayMode`, relevant-pic init, and **opens the OLDB** (`chls_oldb_Get_DB_Existence`, `Open_DB_Info`, 0x7EAAC5E8). | core |
| CmpBgc_BackgroundControlComponent | 0x7EAAEBBC | Background display control | core |
| CmpCCom_CameraCommonComponent | 0x7EAB2756 | USB firmware update (`start_usb_firmup`, `Execute_FirmwareUpdate[_Lens/_Strobe]`, 0x7EAB310B) | visible |
| CmpCPic_CopyPictureComponent | 0x7EAB5747 | Copy one or all pictures between media | probably dormant (needs a second medium) |
| Cmp_PlaySingleComponentBase / CmpPls_PlaySingleComponent | 0x7EB54A65 / 0x7EB5E9AA | Single frame: move, continuous move, zoom/scroll (also by face), touch, body-rotate notify, `start_effect` | visible |
| Cmp_PlayIndexComponentBase / CmpPli_PlayIndexComponent | 0x7EB2CC08 / 0x7EB2FBB2 | Index view: pages, expand animation, rotate, titles | visible |
| CmpPCal_PlayCalendarComponent | 0x7EB021F2 | Calendar: date range, cursor, page, "presence image" per day | visible |
| CmpPLgh_PlayLightBoxComponent | 0x7EB34D9B | Light box: two-image compare with zoom and scroll target (`playlightbox_set_scroll_target`) | **unknown** |
| CmpPMov_PlayMovieComponent | 0x7EB3A4C2 | Movie play, reverse play, FF/REW, frame step, pause, seek, volume | visible |
| CmpPSld_PlaySlideShowComponent | 0x7EB681FE | Slideshow with BGM/data volume, style, GPU slideshow, select collection | visible |
| CmpPSou_PlaySoundComponent / CmpPRec_PlayRecordComponent | 0x7EB6CCF6 / 0x7EB4C862 | Play / record a voice memo attached to a picture (`playrecord_record`) | visible (**inferred**) |
| CmpPSel_PlaySelectComponent | 0x7EB517F9 | Select pictures (single or index) for batch operations | visible |
| CmpPct_PlayContinuousComponent | 0x7EB181C1; `CapPCM` at 0x7EA20DA9–0x7EA21B43 (`chkContinuous`, `getBothEndsPicNo`) | Plays a burst as one group | **unknown**, compact-style |
| CmpPCw_PlayCwComponent | 0x7EB1AF51 | `cw_update_image_layer`, `cw_draw_image_rect`, `cw_copy_area_block`, `cw_start_play_picture`. These match the OSDControl API (r12 copyAreaBlock, r13 customDisplay, r15 updateImageLayer). **Inferred:** "CW" = a custom-window playback canvas that an API client draws into. | **unknown** |
| CmpPPnr_PlayPanoramaComponent | 0x7EB3ECB8; `CapPPnr_PlayPanorama` 0x7EA653AB; 5 Notify*Observer classes | Scrolls a stitched wide image. **Verified:** `CapImg_ImagePlayer` 0x7E9FE7AB calls `api_play_dummy_Alloc_Panorama_PlayHandle`. | dormant (**inferred**) |
| CmpPPho_PlayPhotosurfComponent | 0x7EB47A3B | "Photo Surfing": browse related pictures by date / scene / person / event / collection / position (`start_select_person`, …) | dormant (OLDB stub) |
| CmpPEvV_PlayEventViewComponent / CmpPEvc_PlayEvcollectionComponent | 0x7EB29279 / 0x7EB2511F | Event view; event/collection index (`chls_evcollection_collection_mode`, `event_mode`) | dormant (OLDB stub) |
| CmpPCol_PlayCollageComponent | 0x7EB05D26 | Collage of an event: title, icon, year/month layout (`chls_playcollage_start`) | dormant (OLDB stub) |
| CmpEAsp_EditAspectComponent | 0x7EAB9261 | Aspect crop of a picture | visible |
| CmpEBea_EditBeautyComponent | 0x7EABC982 | Beauty fix: face detect, compare, clear skin preview (`BEAUTY_CLEAR_SKIN / SHINY_EYE / DRAMATIC_EYE`). **Verified** stubs: `api_play_dummy_Alloc_Clear_Skin_Preview_Handle` (caller 0x7EA0A574) and `Get_Beauty_Edit_Eye_Point` (caller 0x7EA01A5F). | e-Portrait edit visible; eye options probably dormant (**inferred**) |
| CmpECol_EditColorComponent | 0x7EAC20C8 | Color edit: compare preview, kinds `KIND_MONOCHROME / SEPIA / VIVID` | visible (B&W / Sepia / Saturation) |
| CmpEImg_EditImageOverlayComponent / CmpSOve_SelectOverlayComponent | 0x7EAC7D26 / 0x7EB751B9 | RAW image overlay. Checks `OBJECT_FILETYPE_RAW` and the camera-type development signature. API `adjustGain`, `canOverlay`. | visible |
| CmpEPro_EditProtectComponent | 0x7EACCE9A | Protect, protect selected, unlock all | visible |
| CmpERaw_EditRawComponent | 0x7EAD0BB9 | RAW data edit: current settings or custom (`start_custom`, `save_current`) | visible |
| CmpERed_EditRedeyeComponent | 0x7EAD4400 | Red-eye fix | visible |
| CmpERes_EditResizeComponent | 0x7EAD8F50 | Resize (`RESIZE_1M / VGA / QVGA`) | visible |
| CmpERot_EditRotateComponent | 0x7EADCC78 | Rotate | visible |
| CmpESha_EditShadowComponent | 0x7EADF598 | Shadow adjust | visible |
| CmpETri_EditTrimmingComponent | 0x7EAE38B5; `CapPlt_PlayTrimming` 0x7EA324F3 | Crop (trim) with size table | visible |
| CmpEra_ErasePicComponent | 0x7EAE9CF2 | Erase single, selected or all | visible |
| CmpRPri_ReservePrintComponent | 0x7EB700AA | DPOF print reservation: count, date, all/single | visible |

`CapImg_ImagePlayer.cpp` (0x7E9F0C66–0x7EA0C62C, 854 unique strings) does the rendering for all of these: thumbnails, GPU paths, trimming, face area, rotate and photosurf layouts (**inferred**).

## 4. Picture database (chls / oldb)

**Layers (verified):**
- `chls_oldb_*` wrappers are at **0x7EA238A1–0x7EA26CBB**. This is ~~an unnamed source file~~ the class **CapPDB_PlayOLDB** (getName 0x7EA26E13, ctor 0x7EA2384A; 13c §7) (D1 2026-11-09), between `CapThr_ThroughBuffering.cpp` and `CapPlt_PlayTrimming.cpp`.
- `chls_` appears to be the playback-library prefix: 277 `chls_oldb_` strings, plus `chls_editbeauty_`, `chls_photsurf_` and `chls_editimageoverlay_` (**inferred**). The UI strings that use it are mostly in 0x7E9F–0x7EA0 (ImagePlayer) and 0x7EA2/0x7EB2/0x7EB4.
- **The backend is a stub (verified):** all 46 `api_oldb_*` names are `api_oldb_dummy_*` (string table 0x7E7CE460–0x7E7CEAE2, code 0x7E682EC3–0x7E683107). No `api_oldb_` name without `dummy` exists. 0x7E682EC3 and 0x7E682F3B both disassemble to `mov 15,d0; mov <name>,a0; call 0x7E678422; mov 1,d0; ret`, which logs the name and returns 1.
- Example call chain (**verified**): `chls_oldb_Get_DB_Existence` (0x7EA245F0) calls `0x7E67F822(23)`, then the stub 0x7E682EC3(d0, 1), and returns the stub result as a u16.

**What it would index (inferred from the 44 `chls_oldb_*` and 46 stub names):**
- **Events:** `Get_Total_Event_Num`, `Get_EventNo_By_Picno/Date`, title and collage pictures per event.
- **Collections:** `Get_CollectionNo_By_Picno`.
- **Persons**, i.e. face recognition: `Get_Total_Person_Num`, `Get_PersonNo_By_Picno`, `Get_Relevant_Pic_Facenum`.
- **Scene mode:** `Get_Target_Scene_Mode_State`.
- **Dates:** `Get_Date_Next_By_Date`, date arrows.
- **GPS areas:** `Get_Picture_Existence_By_GpsArea`, `Search_RelevantPicture_By_GpsArea`, `Search_Next_Contents_By_DirectionGps`; latitude, longitude, x/y resolution.
- **Landmarks:** `Search_Landmark*`.
- **Keyword search.**
- **"PSV" info.** Its meaning is unknown.

**Where it would be stored (inferred):**
- `Create_OLDB`, `Get_Create_OLDB_Progress`, `Commit_DB_Info[_Async]`, `Get_DB_File_Attribute`, `Regist_DB_Copy_Object`, `DB_Write_Before/After` (0x7EA23B59–0x7EA23DF2) and `Get/Delete_DB_PC_Info` suggest a database file on the card that the camera builds and PC software also uses.
- **No file name string was found** (I searched for `.db`/`OLDB.` patterns).

**Who uses it:**
- PlayCommon opens it.
- Photosurf, EventView, Evcollection, Collage and the slideshow "select collection" use it.
- The edit components call `DB_Write_Before/After` so that edits keep the DB in sync (**inferred**).
- The API name table has `OLDBControl::create/abortCreate/existsOLDB` and `GpsCtrl::startGPS…getLandMarkList`, but **no code references those names** (`fn: -`, data refs only at 0x7E8E15FC–0x7E8E168C, outside this scope).

**Conclusion (inferred):**
- This shared code base comes from Olympus compacts (Tough/SH series with GPS and "ib"-style event and person browsing).
- On the E-PM2 the DB is compiled out, so every DB-backed play mode is dormant.

## 5. API enums and the `sdk api` test shell (0x7E99A000–0x7E9C0000)

**Shell structure (verified):**
- The debug shell's `sdk` sub-command table is at **0x7EBF0FA0**: `{name*, fn*}` pairs.
- Sub-commands: `help dbglvl debug dump dbgall dbgstate dbgfw shutdown shutdown_api sleep sleep_api sleep_off charge_sleep power_info canexec mediastatus showtimer ca api starttimer stoptimer dbgseq dbgfunc dbgeyefi dbgbm dbgosd dbgsys olyapi_get dbggrid`.
- `sdk api` = 0x7E9A074B, with help text `sdk api [A-z]`.
- It dispatches through a **635-entry table at 0x7EBF8188**. Each entry is `{handler, "A02", "shutDown"}`, 12 bytes (dumped with `cmdtbl.py`).
- Each handler prints `usage: sdk api %s …` and the enum names (`API_MEDIA_*`, `API_*_KEY`, `DIRECTION_*`, `OLY_TRUE/FALSE`), parses its arguments, and calls the `OlyApi*` layer (0x7E9C–0x7E9D).
- fwmap merges many handlers into one big "function", 0x7E9A1F88 (16.5 KB, 446 strings), because the handler starts are reached only through this table.

**Command groups (inferred):** the letter prefix stands for an API class. For most groups the method count matches the `Class::method` name table at 0x7EBD5000–0x7EBDA000.

| Prefix (count) | API class | Prefix (count) | API class |
|---|---|---|---|
| A (39) | system / power / display out (`shutDown`, `getPenpalState`, `getEvfState`) | O (28) | PlaySingleFrame |
| B (28) | SettingController (`setSetting`, `resetIntervalShooting`) | P (14) / Q (9) | PlayIndex / (an index variant, ?) |
| C (5) | draw / menu area | R (10) | PlayMovie |
| D (11) | SoundCtrl (import sounds) | S (5) / V (4) | PlayRecord / PlaySound |
| E (7) | DateCtrl | T (15) | ReservePrint |
| F (20) | MediaCtrl (`getExistMedia`, `formatMedia`, `changeMedia`, `getAVCHDstate`) | U (8) | PlaySlideShow |
| G / H / I | PixelMapping / ModeCheck / power supply | W (8) | PlayCalendar |
| J (5) | LevelCtrl (`getSlope`, `calibration`) | X (15) | PlayLightBox |
| K (9) | KeyCtrl (long-press, repeat) | Y / Z / a / b | EditResize / EditTrimming / EditAspect / EditColor |
| L (5) | TouchPanel | c, d, e (4, 4, 6) | edit adjust classes (shadow, red-eye, beauty: ?) |
| M (94) | **Shooting** (histogram, zoom frame, multi-exposure, panorama, 3D, live bulb, Live Guide, interval M86–M88, time-lapse M93) | f / g / h | EditRaw / EditImageOverlay / SelectOverlay |
| N (18) | PlayCommon (`getHistogram`, `erase`, `transferImage`) | i / j / l | SelfAdjust / LifeTest / Maintenance (`updateFirmware[Card]`, `getSerialNumber`) |
| m / n | EasyPrint / CustomPrint (PictBridge) | o / p | DeviceLink / **Bluetooth** (34) |
| q (55) | SystemCommon (sc OS, string, malloc, timer) | r / s / t | OSDControl / LV control / **FlashAir** (Wi-Fi SSID, password) |

**Enum values printed by the shell (verified string text):**
- **Media:** `API_MEDIA_INTERNAL = 0x01`, `API_MEDIA_SD_CARD = 0x02`, `API_MEDIA_EXTERNAL = 0x04` (a bitmask); also `API_MEDIA_RESIZE_NONE 0 / _1920_1440 1`.
  - **Inferred:** "internal" is built-in memory, which the E-PM2 does not have. The enum is shared across the platform.
- **Keys** (`API_POWER/UP/DOWN/LEFT/RIGHT/OK/MENU/PLAY/MOVIE/INFO/EVFSW/DEL/CUSTOM/CUSTOM2/EXPAND/INTERNAL_EVFSW/GRIP_CUSTOM1/GRIP_CUSTOM2/LENS_KEY`, `API_1ST/2ND_RELEASE`): printed by 0x7E9A1BCD and 0x7E9A63EC. Matching events are `EV_PRESS_*`/`EV_RELEASE_*` and `EV_CHANGE_{MAIN,SUB}_DIAL[_GRIP*]`, `FOCUS_RING`, `ZOOM_RING`.
  - **Inferred:** the grip keys, the internal-EVF switch and the second dial are for other bodies.
- **Directions:** `DIRECTION_UP/DOWN/LEFT/RIGHT/HORIZONTAL/VERTICAL/FACE/UNKNOWN`. Used for movement in play modes and for panorama direction.
- **Histogram:** Shooting `startHistogram/stopHistogram/getHistogramData/getRecViewHistogram` (M07, M08, M11, M15), Play `getHistogram` (N07), callback `CBS_UPDATE_HISTOGRAM`.
  - **Verified** names: the low-level `api_histogram_*_Display` functions (Y/R/G/B) are `api_histogram_dummy_*`. **Inferred:** histogram display is drawn elsewhere, through `api_histogram_Start_Histogram_CalcData`.
- **Mode dial:** `API_MODE_DIAL_*` includes `BEAUTY`, `ANTISHAKE`, `LOWLIGHT`, `MY_SET1..4`. **Inferred:** a superset across models.
- **Wake/sleep reasons:** `API_WUI_*`, `API_SLP_WUI_*`.
- **Display outputs:** `API_DISP_OUT_*`, including HDMI 480p/576p/720p/1080i, VIDEO NTSC/PAL and EVF VF2/VF3.

**Callback IDs:** `CBC_*` = component callbacks (`CBC_EDIT_ASPECT/COLOR/RESIZE/TRIMMING`, `CBC_PLAY_SELECT/SINGLE_FRAME/SLIDESHOW`, `CBC_ERASE_ALL`, `CBC_PROTECT_ALL`, `CBC_RESERVE_PRINT`, `CBC_SELECT_OVERLAY`, `CBC_SOUND_CTRL`, `CBC_TOUCH_EVENT`, `CBC_TRANSFER_IMAGE`, `CBC_CUSTOM_PRINT`). `CBS_*` = status callbacks to the API client (e.g. the `CBS_*INTERVAL_SHOOTING*` family). **Inferred.**

**AUD_WATCH_DOG** (entry 0x7E96188B, just below this range):
- **Verified** strings: `---Repeat play---`, `---Play end---`, `---Repeat rec---`, `---Rec end---`, with 500/2000/5000 ms waits.
- **Inferred:** an audio play/record soak-test task, not a real watchdog.

## Open questions

1. Is interval shooting / time-lapse reachable on the E-PM2? Check who sets mode 482 (`MODE_INTERVAL_SHOOTING_ONOFF`) and whether the menu code at 0x7ECD1BC1–0x7ECDA5C6 has an E-PM2 menu entry.
2. 3D photo: `Execute_3D_Still`, `Make_YC_3D_Still` and `Record_3D_Still` are stubs, while `api_rec_Start_Take_3d` is real. Does a 3D scene still save an MPO through another path, or is the mode dead? Check what 0x7E880EFF(0xF00F0000, 1) signals.
3. Which `Cmp_*` file owns each of the 10 `Cmp_PlayComponentBase` subclasses? A constructor that sits between two files' first strings is ambiguous. One fix: check the first string of each constructor's callers.
4. Map the event id space: ~~about 930~~ 1,273 event classes with u16 ids (e.g. 11964, 12047). Done in 13c §4 and `13c-event-ids.tsv` (D1 2026-11-09). Dumping `id → vtable → constructor → module` would give an event dictionary. Also confirm that −6 is OXF's end-thread id.
5. Light box (X group), Multi-through, PlayContinuous and the CW canvas: present in the code, but are any user-visible on the E-PM2?
6. What does the stub's return value 1 mean to the `chls_oldb_*` callers ("absent" or "error")? Which UI path checks it before entering Photosurf?
7. Is `Q` (9 commands) the EditCalendar or PlayEventView API? Is `k` (registerCode/eraseCode) a device-registration API?
8. Who calls the 635 `sdk api` handlers apart from the debug shell? The `Class::method` name table at 0x7EBD5000 points into 0x7E8E15FC… (another section's scope). That table may be a second, script- or remote-facing dispatcher.
