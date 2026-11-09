# Audit batch 3: claims to check

## 05-13  (from sections/05-playback-audio-bt.md, line 13)

| 0x7E8F904F–0x7E8F926E | SERV_MAIN: a service that broadcasts state notices | verified |

## 05-17  (from sections/05-playback-audio-bt.md, line 17)

| 0x7E91D000–0x7E937FFF | iAnywhere-style "Blue SDK" stack (`OLYMPUS BlueSDK a4`), RFCOMM, tasks BTSTK/BTTIM/BTEVU/BTAPL | inferred stack identity; task entries verified |

## 05-153  (from sections/05-playback-audio-bt.md, line 153)

| AUD_BRIDGE | 0x7E94D880 | 9 | Reads packets from queue 0x7E43E966 (via 0x7E95FF4C) into the buffer at 0xA07542D8, then runs `aud_bridge_recv_packet_analysis` 0x7E94D8A8 → `aud_bridge_exec_message` 0x7E94D968 or `aud_bridge_post_message` 0x7E94DACD (verified). Inferred: the packet entry point for other tasks (`res_qname` = reply queue). |

## 05-156  (from sections/05-playback-audio-bt.md, line 156)

| AUD_COPY_DATA | 0x7E94E4D8 | 9 | Waits on flags 0x33. Bits 0x30 → `aud_copy_data_main_play_copy` 0x7E94EBF3; bits 0x03 → `_rec_copy` 0x7E94E729. Copies PCM between the file buffer and the DMA ring (verified). |

## 05-158  (from sections/05-playback-audio-bt.md, line 158)

| AUD_LATE_RISER | 0x7E9502CE | 11 | Debug test: reads setting **10442** index 0/1/2 (action, wait_time, work_info), sleeps, then plays `HOGE.WAV`, records, or changes the volume (verified). Inferred: a "start late after boot" test hook; no effect on normal use. |

## 05-228  (from sections/05-playback-audio-bt.md, line 228)

- `bt_config_set` 0x7E9126CC calls 27 functions (0x7E904B2E–0x7E911EFD). Each one stores bytes into the TX buffer at 0x605CD215 and sends it with 0x7E912E84. The first is `01 4C FC 8B 58 75 08 00 …` = **HCI vendor 0xFC4C Write_RAM** at 0x00087558. The last (0x7E912680) is `01 4E FC 04 FF FF FF FF` = **0xFC4E Launch_RAM**. This is the **Broadcom patch-RAM** format, so the PENPAL controller is a Broadcom chip and the camera stores its patch (inferred vendor; the opcodes are verified).

## 06-57  (from sections/06-app-components.md, line 57)

| `Cmp_PlayComponentBase` | base constructor **0x7EB0A5E7**; 58-slot vtable **0x7EC6F70C** (slots 52–57: `sound_state`, `playsound_set_volume`) | **verified**: 10 derived constructors call it (next row) |

## 06-92  (from sections/06-app-components.md, line 92)

| Interval shooting and time-lapse movie | Inside SequencePartsBase: `rcvStartIntervalShootingIn_active` 0x7EA98808, `setIntervalShootingNextTime` 0x7EA98F94, `rcvCreateTimeLapseMovieIn_active` 0x7EA991DD, `startIntervalShooting_First` 0x7EA99881. Guard `isStartIntervalShootingEnable` 0x7E969C11. API entry `OlyHfwOpeShoot::startIntervalShooting` 0x7E98849B. | **Verified:** the guard reads mode **482** through 0x7E6FCC91 (its log calls this `MODE_INTERVAL_SHOOTING_ONOFF`), plus take-status flags 18 and 9 and bit 14 of the interval state. 0x7E98849B calls the guard and then constructs event id 12047 (vtable 0x7EBDE7B0, constructor 0x7E971CB7). **Inferred:** the camera sleeps between shots (`CBS_START_INTERVAL_SHOOTING_SLEEP`, `API_SHUTDOWN_REASON_INTERVAL_SHOOTING = 0x07`, `API_WUI_INTERVAL_SHOOTING` wake reason). The movie is built by `api_play_Create_TimeLapseMovie` (0x7E686E96). Menu-side code is at 0x7ECD1BC1–0x7ECDA5C6. | Complete code. Whether the E-PM2 menu exposes it is **unknown** (open question). |

## 06-96  (from sections/06-app-components.md, line 96)

| 3D photo | `CmpSts_3dImageController.cpp` 0x7EA6E566 (events `Start3dCombine`, `Start3dOverlap`, `StartMpoRecording`); 3D path in `CmpShc_ShootingSequenceBase.cpp` 0x7EA6A6CF | Two takes, then combine, then MPO. **Verified:** `start3dCombine` 0x7EA4D845 calls `api_rec_dummy_Execute_3D_Still` (0x7E68C72F). That stub logs and then calls 0x7E880EFF(0xF00F0000, 1), probably to raise a done event. `Record_3D_Still`, `Make_YC_3D_Still` and `RecView_3d_Comb` are also stubs. The real `api_rec_Start_Take_3d` (0x7E68B98A, caller 0x7EA4D25F) exists. | The combine step is stubbed, so it is probably dormant (**inferred**). Separate: `start3DLensShooting` (3D-lens path, API M69). |

## 06-133  (from sections/06-app-components.md, line 133)

| CmpPPnr_PlayPanoramaComponent | 0x7EB3ECB8; `CapPPnr_PlayPanorama` 0x7EA653AB; 5 Notify*Observer classes | Scrolls a stitched wide image. **Verified:** `CapImg_ImagePlayer` 0x7E9FE7AB calls `api_play_dummy_Alloc_Panorama_PlayHandle`. | dormant (**inferred**) |

## 06-138  (from sections/06-app-components.md, line 138)

| CmpEBea_EditBeautyComponent | 0x7EABC982 | Beauty fix: face detect, compare, clear skin preview (`BEAUTY_CLEAR_SKIN / SHINY_EYE / DRAMATIC_EYE`). **Verified** stubs: `api_play_dummy_Alloc_Clear_Skin_Preview_Handle` (caller 0x7EA0A574) and `Get_Beauty_Edit_Eye_Point` (caller 0x7EA01A5F). | e-Portrait edit visible; eye options probably dormant (**inferred**) |

## 06-159  (from sections/06-app-components.md, line 159)

- Example call chain (**verified**): `chls_oldb_Get_DB_Existence` (0x7EA245F0) calls `0x7E67F822(23)`, then the stub 0x7E682EC3(d0, 1), and returns the stub result as a u16.

