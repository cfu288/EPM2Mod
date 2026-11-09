# Audit batch 13-2

## 13c-12 (sections/13c-cpp-framework.md, line 12)

| 0x7E96B000–0x7E9EA000 | `Tra*` event package + `OlyHfwOpe*`/`OlyHfwLowApiWrap` operation classes + event classes they declare; `sdk api` shell and `OlyApi*` (06 §5) | verified (string tags + event scan) |

## 13c-16 (sections/13c-cpp-framework.md, line 16)

| 0x7EB8C265–~0x7EB93A80 | `Dev*` device classes, part 1: display device (`api_disp_*`, `allocDisplayHandle`), `DevAef_AEAFCtrl`, `DevCls` (clear-skin rec view), effects, LED, `DevMed_MediaControl`, `DevRec` | verified (`api_*` callees, strings) |

## 13c-18 (sections/13c-cpp-framework.md, line 18)

| 0x7EBA0AA9–0x7EBA4867 | `Dev*` device classes, part 2: anti-shake, image handle, HDMI/CEC, histogram, Exif, picture files, `DevBlu_Bluetooth`, **USB-communication device**, DPS-T, DPS, pixel mapping, picture-file creation (§5.4) | verified |

## 13c-34 (sections/13c-cpp-framework.md, line 34)

| Memory | operator new 0x7EBA62DB (6,006 sites) / 0x7EBA62E3; delete 0x7EBA62EB (963) / 0x7EBA62F3; all go to 0x7EBA797A/0x7EBA7984 → 0x7E6810AE/0x7E6810F0 | verified |

## 13c-37 (sections/13c-cpp-framework.md, line 37)

| Framework events | ids −5 (0x7EBA6E24), −6 (0x7EBA6E50), −1 (0x7EBA6E7C), −9 (0x7EBA6EAD); vtables 0x7EC92080–0x7EC921A0 | verified ids |

## 13c-40 (sections/13c-cpp-framework.md, line 40)

| Start-up | 0x7EBA78B3 (from 0x7E966A17), `mainThread` entry 0x7EBA792C | verified |

## 13c-209 (sections/13c-cpp-framework.md, line 209)

| **0x7EBA3310–0x7EBA36F6** | **USB-communication device**. Accessors 0x7EBA3310/333C/3368/3394 (called by CapPbr 0x7EA58AF3 and CapCom 0x7EA51A8C) lead to ctor **0x7EBA33C0**. The ctor builds 4 mode sub-objects with 9-slot vtables: **DPS 0x7EC916F4, MTP 0x7EC91718, Storage 0x7EC9173C, generic 0x7EC91760**, and 8 observer lists at +48…+188. Slot 2 = `api_comm_End_Communication_<mode>`, slot 6 = `api_comm_Start_Communication_<mode>` (F060 0x7EBA35C2 = DPS start), slots 3/5/7 = `api_media_Initial_Strage` / `Mount_USB_Strage` | verified |

## 13c-210 (sections/13c-cpp-framework.md, line 210)

| 0x7EBA36F7–0x7EBA414D | DPS-T device (vtable 0x7EC91784; 16 small methods, then `api_dpst_Dpst_*` Req/Send for DPOF, print, reserve) | verified |

## 13d-14 (sections/13d-gui-toolkit.md, line 14)

| 0x7ECA1020–~0x7ECC8000 | Mostly data: ramp/LUT tables (0x7ECA6000…) and a 108 KB block at 0x7ECB1000. The DB's "function" 0x7ECAD443 (15 KB) is probably data | verified bytes; the role of the data is inferred |

## 13d-17 (sections/13d-gui-toolkit.md, line 17)

| 0x7ECEC000–0x7ECEE1D5 | GUI memory pools (alloc 0x7ECEC905, free 0x7ECEC9CB); UTF-16 helpers (`wcscpy` 0x7ECED793, `wcslen` 0x7ECED7BB, compare 0x7ECED75C); CTouchPnl (0x7ECEDE30). The GUI data-model get/set 0x7ECEF64F/0x7ECEF667 (section 07) sits just after the root class | verified code |

## 13d-24 (sections/13d-gui-toolkit.md, line 24)

| 0x7ED86DA0–0x7EDA0410 | Live-view controller `IGui_Controler` (0x7ED87077, 0x7ED87397); Actuator/Viewer objects of the registry 0x7EFC5408 (`Func_Scp_Actuator`, `Input_String_Actuator`, `Rec_View_Viewer`) | verified strings |

## 13d-66 (sections/13d-gui-toolkit.md, line 66)

- **Pools (verified):** GUI pool alloc/free 0x7ECFF1D8/0x7ECFF1E4, selected by the bytes at object +28/+29 (slot +244 sets, +248 reads).

## 13d-121 (sections/13d-gui-toolkit.md, line 121)

- **Drawing engine (verified call graph):** 0x7ECF5000–0x7ECFF000 and 0x7ED2F000–0x7ED37DAA. It calls nothing outside the toolkit except memcpy 0x7E500D33, memset 0x7E500D73 and the UTF-16 helpers. Resource lookups:

## 13d-135 (sections/13d-gui-toolkit.md, line 135)

- **Resource record (44 bytes, verified):** `{u16 type, u16 k+1, u32 rects → 0x7EF0D7F0 + 16·k, u16 7, …, u16 layer (1/2/3), 0xFFFE, …, 100, 100}`. The rect pair is two `{x, y, w, h}` rects, e.g. 800×600 or 720×480. **Inferred:** the two rects are for two outputs.

## 13d-156 (sections/13d-gui-toolkit.md, line 156)

- Panel **signature (verified):** the ctor is `call 0x7ED23C27 ; mov VT,d0 ; mov d0,(a2) ; …zero the child array at +792… ; [call 0x7ED01DFD ; call 0x7ED01F7C/0x7ED01FBA]`.

## 13d-218 (sections/13d-gui-toolkit.md, line 218)

- **BGM Import (verified structure).** No Ss row handles it. It is a userMenu item: vtable 0x7F00095C, slot 0x7EDF26B2 loads string 1782 and calls ShowPanelEx(111). Its callback 0x7EDF2BA1 logs `OlyApiSoundCtrl::registImportSound()`. It runs inside SS_MENU_MAIN (Slideshow > BGM, inferred).

