# Audit batch 4: claims to check

## 07-222  (from sections/07-gui-menus-settings.md, line 222)

- Info 482 → prm tag 0xDE11, MODE class, u8, default 0. **(verified)**

## 07-260  (from sections/07-gui-menus-settings.md, line 260)

- **GUI substates:** SS_COMMON, SS_REC, SS_MENU_MAIN, SS_MENU_LV, SS_MENU_PLAY, SS_PLAY_SINGLE, SS_PLAY_MOVIE_SLIDE, SS_PLAY_INDEX, **SS_SELFADJ, SS_DEBUGMENU**, SS_USB, SS_DPS, SS_BTSEND, SS_BTRECEIVE (name table near 0x7EFDD233). **(verified strings)**

## 07-268  (from sections/07-gui-menus-settings.md, line 268)

| `GUI Debug` shell: `DEBUGLEVEL/DBGLVL 0-3, hist, showev, ca on/off, gpi on/off, rec on/off, ev <EventID hex>, TOUCH, CONV, INFO, SHOWEC` | 0x7EDC3D85 | verified strings |

## 07-271  (from sections/07-gui-menus-settings.md, line 271)

| Self-adjust menu `SS_SELFADJ` (`startSelfAdjustMenuSubAppStateMisc` 0x7ECE067B, `SelfAdjust::getMenuItem…turnOnTFT`, `api_adj_Check_Execute_Self_Adjust`) | | verified strings |

## 07-272  (from sections/07-gui-menus-settings.md, line 272)

| Version-check menu (`CAM_MISC_VERCHK_MENU`, `startVersionCheckMenuSubAppStateMisc` 0x7ECE0653, `[GUI App Version]:OkOn called , F/W Version up start`) | 0x7EDA6D93, 0x7EDFD86F | verified strings. The Firmware item can start a firmware update. |

## 07-275  (from sections/07-gui-menus-settings.md, line 275)

| Pixel Mapping: normal Custom Menu J item (CmpCst_Function 0x7EAA8FF9…, api_rec_Calculate/Save_Pixelmaping) | | verified strings |

## 08-17  (from sections/08-connectivity-libs-blocks.md, line 17)

3. **Firmware update over USB** uses ops 0x9117 and 0x9119–0x9125. FirmwareCheck posts the received image to the **FIRMUP_SRV** task queue. (verified)

## 08-47  (from sections/08-connectivity-libs-blocks.md, line 47)

| TPC | 0x7F088F64 | "Transfer to PC" controller: `TPC_ON connection=0x`, `tpc_control:unknown com`, globals gConnectMode/gConnectState | verified (below) |

## 08-52  (from sections/08-connectivity-libs-blocks.md, line 52)

| SAICAS | 0x7F0870D7 | script-file transport for DPS and X3C: `handle_SAICAS_OP_COM_OPEN_SESSION/WRITE_INFO/READ/DELETE…`, file names `HREQUEST.DPS` etc. | **verified**: SAICAS reads queue 0x7E43EE0A, which both the PictBridge and the X3C SendObject handlers write |

## 08-59  (from sections/08-connectivity-libs-blocks.md, line 59)

- LANGID 0x0409, a device-qualifier descriptor, and at 0x7F0D7C61 the 53-byte USB 2.0 `TEST_PACKET` pattern (00…AA…EE…FE FF… 7F BF DF…). (verified)

## 08-203  (from sections/08-connectivity-libs-blocks.md, line 203)

- **Dual core (verified part):** the fatal/NMI handler 0x7E463CD9 reads a CPU id at absolute address 0x8050 and prints `Genba Ha CPU0/CPU1` ("the failure is on CPU0/CPU1"). The object-name table has a CPU1 set (`BOOT_CPU1`, `CPUCONN_CPU1`, `MOV_ENC_VIDEO_CPU1`, `CPU1_MOV_AVCHD`, `IMG_CPU0_TO_CPU1`).

## 08-241  (from sections/08-connectivity-libs-blocks.md, line 241)

- **User (verified):** `art_filter_06_rough_monochrome.c` pass 2 (0x7E722B38) calls the resource loader 0x7E674F44 with type **10**. The jump table at 0x7E7C10A4 sends case 10 to 0x7E675538. That reader takes an 8-byte entry `{size, addr}` from the artfill directory (0x6059CCE8) and reads a window of it. "Rough monochrome" is the internal name of **Grainy Film**.

