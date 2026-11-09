# 11 — What each official E-PM2 update changed in block 0 (v1.1 → v1.6)

- **Labels:** **verified** = read in the disassembly or bytes; **inferred** = from names, order, layout or outside sources.
- **Inputs:** `firmware/stock/E-PM2/OLY_E_101_{1101,1203,1300,1400,1501,1600}_0000_0000.BIN`, block 0 only (blocks 1–3 and the OM tail are identical, checked earlier). Base 0x7E421020 for all six. Function databases: `$S/map-101_*` and `build/map` (v1.6).
- **Primary source for intent:** Olympus release notes, `$S/dl-notes/1010_i06.txt`.
- **Scripts:** `$S/version/` (`$S` = the session scratchpad). `parse.py` normalises each function. `match2.py` aligns the versions. `classify.py`, `analyze2.py` and `junk.py` classify the changes. `region.py` and `cdiff.py` diff code streams while ignoring where function boundaries fall. `sem.py` diffs constants and calls. `strdiff4.py` diffs strings, and `bdiff.py` diffs bytes.
- **Addresses** are runtime addresses in the version named. "old → new" means the earlier and later version of that pair.
- **No v1.0 image is available**, so the v1.1 changes cannot be diffed. The five pairs are 1.1→1.2, 1.2→1.3, 1.3→1.4, 1.4→1.5 and 1.5→1.6.

## Summary table

| Release (build date in block 0) | Release note | What the code shows | Ties to the note? |
|---|---|---|---|
| 1.1 (Nov 21 2012) | Exposure with non-communicating lenses | Nothing to compare: no v1.0 image | **Not checkable** |
| 1.2 (May 9 2013) | Touch-panel stability in playback; VF-4 support | **VF-4: verified.** A new accessory ID 0x0322 = "Evf3", a new I²C bus configuration, an init write, and the VF-4 display path. Large rebuild (≈1,400 code functions differ). Touch fix **not isolated** | VF-4 **yes**; touch **unresolved** |
| 1.3 (Oct 9 2014) | AF precision with the 40-150 F2.8 PRO | **One real code change** (0x7E6232ED): a lens-ID and lens-protocol test picks a different AF parameter set. Plus version constants | **Yes** (code verified; the 40-150 link inferred) |
| 1.4 (May 11 2015) | FlashAir W-03 smartphone connection | **Only 6 instructions change** in the whole block: iSDIO register-access requests pass 18 instead of 19. Plus version and date | **Yes** (verified as the only change; meaning of 18/19 inferred) |
| 1.5 (Nov 4 2015) | Lens IS support (not Sync IS); Windows 10 | Large rebuild (≈570 code functions differ). New lens-IS classifier `is_type`. The lens-OIS path is now limited to one lens family. New lens-info pages 030/033. New `lens current` shell command. In the PTP overlay, the handler for property 0xD406 (0x7F08CC99) now discards the host string (audit 2026-11-09) | Lens IS **yes** (inferred mechanism). Windows 10: **best code-level candidate** = the 0xD406 change (verified code; the link is inferred) (audit 2026-11-09) |
| 1.6 (Oct 23 2018) | AF with Panasonic H-ES200 / H-ES50200 | **AF position variables widened from 16 to 32 bits** across the AF code (~0x7E5E3000–~0x7E627000, page-rounded (L1 2026-11-09)); "focus position" is inferred from the `fcs_*` names. A new saturating clamp at 39 sites: 38 clamp to [−32768, 32767], one (0x7E60A5EE) to [0, 32767]. AF structs grow. Code from 0x7E626937 to about 0x7E76EA1F shifts by +0x2AC; code from 0x7E8F1C68 on does not move (audit 2026-11-09) | **Yes** (code verified; the link to these lenses inferred) |

## 1. Method and counts

**Matching (verified procedure).**
1. Every function is turned into a list of normalised instructions: call/branch targets, ROM addresses and RAM addresses are masked, and local branches become offsets from the function start.
2. A sequence alignment over all ~66k functions (in address order, which keeps link order) pairs the identical ones.
3. Each pair is checked again. Callees and code references must map consistently (by containing function + offset), string references must have the same text, and RAM references must follow the majority mapping.
4. The leftovers in each gap are paired by instruction-multiset similarity (≥ 0.4, monotone order) as "changed". The rest count as added or removed.

**Two kinds of noise have to be removed by hand.**
- **Data pages decoded as code** ("junk": raw out-of-range branch targets, `unknown` opcodes).
- **Function-boundary artifacts.** A new call target or pointer splits or merges database functions. `region.py`/`cdiff.py` therefore diff whole code streams of each gap. Several "changed" playback functions in 1.3 (0x7EB6318E, 0x7EB638FC) turn out to be the same code, only split differently: v1.2 0x7EB6318E + 0x7EB637F2 + 0x7EB63833 become one v1.3 function 0x7EB6318E, and v1.2 0x7EB638FC is split into 0x7EB638FC + 0x7EB63939. The code is not byte-identical: 7 call displacements change by +0x80 because their callees moved (verified) (audit 2026-11-09).

| Pair | Unchanged (same address, same bytes) | Relocated only | Relocated, ref flagged¹ | Changed (all / real code²) | Added (all / code) | Removed (all / code) |
|---|---|---|---|---|---|---|
| 1.1→1.2 | 1,612 | 61,526 | 518 | 1,843 / 1,373 | 610 / 568 | 844 / 768 |
| 1.2→1.3 | 53,828 | 11,914 | 1 | 351 / 26 | 40 / 27 | 15 / 7 |
| 1.3→1.4 | 66,125 | 0 | 0 | 9 / 6 | 0 | 0 |
| 1.4→1.5 | 15,458 | 49,380 | 56 | 1,008 / 567 | 265 / 256 | 232 / 225 |
| 1.5→1.6 | 49,282 | 15,935 | 135 | 764 / 358 | 53 / 39 | 51 / 37 |

¹ Same masked code, but the mapper could not confirm one reference. Spot checks show these are mostly prediction noise for pointers into data (inferred), not real changes.
² Not junk. "Code" add/remove counts still contain boundary artifacts, so they are upper bounds.

**Where the code moves (verified, from the pairs):**
- **1.2→1.3:** +0x80 from 0x7E623521 to 0x7E8F1C48 (that is the size growth of 0x7E6232ED, 564→692 bytes). Identical elsewhere.
- **1.3→1.4:** no shift at all.
- **1.5→1.6:** +0x2AC from 0x7E626937; the shifted code ends at about 0x7E76EA1F. The data after it moves by +0x2AC…+0x2B0, then by +0x288/+0x280 after the removed string at 0x7E7A80FB. From 0x7E8F1C68 on the delta is 0, except about 0x7EF2C000–0x7F030000, which moves by +4…+0x10. Identical before 0x7E626937. The +0x2AC matches the ep5-fw-reverse note (audit 2026-11-09).
- **1.1→1.2 and 1.4→1.5:** dozens of different deltas (e.g. +0x24F at 0x7E51B7BA and +0xFE6 at 0x7E6C92B1 in 1.2; +0x606 at 0x7E53F270 and +0x67F at 0x7E5A6A83 in 1.5). These are full rebuilds.

## 2. String-set changes (verified)

Comparing "clean tails" (pointer bytes stripped, absent as NUL-terminated text in the other version) gives these changes:
- **1.1→1.2, +about 80 strings.**
  - Accessory and EVF: `OUT-EVF3!`, `display_open_evf_vf4`, `\noutevf_vf4_setup`, `V_DROP_FLG`, `VDROP EvFlgWai Error.`, `[VSC]App<=>PerIOE ID UnMached.`, `[Display] Evf Driver open/close failed!`.
  - Accessory-key driver: `ui_key_set_edev_init_0`, `ui_edev_mode_chg`, `ui_key_edev_on__io_ctl`, `ui_key_edev_off_io_ctl`, `ui_key_edev_chk mode : `, `KEY_POLL_TYPE_IOE KEY CANSEL`, `per_gio_ioe_read :`.
  - I²C "ACC" device: `ACC:I2C NG? LIFE:` (runtime health check, §3), and `rreset`, `rdump`, `Who am I?:` (new subcommands of the existing ACC shell command; `ACC: Who am I?:` already exists in v1.1) (audit 2026-11-09).
  - GUI debug traces (`###### [LOWAPI]RecView…`, `calculateRecViewArea`, `pMainArea …`, `faceArea …`) and an `sdk dbggrid` command.
  - **Removed:** `ui_edev_sleep_chg`.
  - `Evf3`/`Ef3C` are new too (4-char names, see §3).
- **1.2→1.3 and 1.3→1.4:** no string changes apart from version and date.
- **1.4→1.5:**
  - `lens current [dbgmode]`, `LENS_INFO_CURRENT_CONSUMPTION(_NO_DATA)`, `current_consumption(still/movie) = %d00[mA]`, `wob_possible`.
  - New lens-info list lines `029 ------`, `030 LENS_INFO_ENABLE`, `031/032 reserved`, `033 LENS_INFO_CURRENT_CONSUMPTION`.
  - ` is_type = %d`.
  - The `g_lens_is_*` and `g_ois_sw_info` prints are re-padded, not new.
  - `OLYMPUS CORPORATION    `.
- **1.5→1.6: only one string is removed, `**fcs_lens_mfts_move_lens_ofset_target()*`** (0x7E7A80FB in v1.5). Nothing is added.

## 3. v1.2 — VF-4 (verified unless marked)

| Item | v1.1 | v1.2 (v1.6) | Change |
|---|---|---|---|
| Accessory-ID probe (PER_IOE, `PerSEFm`) | 0x7E46445A | 0x7E464850 (same) | The loop over bus configs goes 3 → **4** (`cmp 3`→`cmp 4`). New path for config type 3: read the ID; if `(id & 0xF0) == 0x20`, write reg 59 (0x3B) = 0x81 and re-read. The probed bus config is now also saved to 0x60416E62 |
| Bus-config table (12-byte records) | 0x7E4C6828: {1,0x88},{2,0x12},{2,0x1C} | 0x7E4C6FB0 (0x7E4C7294): **{3,0x68}** inserted second | New I²C target 0x68 (inferred: the VF-4's controller) |
| Chip-ID → device-ID pairs | 0x7E4C6804: 9 pairs | 0x7E4C6F88 (0x7E4C726C): 10 pairs, **+0x0322→0x0322** | New accessory ID 0x0322 |
| edev match records (16 B) | 0x7E733A24: 6 records (0x0101, 0x0102, 0x0103, 0x0202, 0x0204/0x0205, 0x023E) | 0x7E734A4C (0x7E7353F8): 7 records; **0x0322 added as bit 2, debounce 50/1**; EVFs reordered to bits 0–2 | — |
| edev status items | 0x7E7339F4: 0x1706, 0x1708, 0x1709, 0x170A, 0x170C | 0x7E734A14 (0x7E7353C0): 0x1706, 0x170A, **0x170E**, 0x1708, 0x1709, 0x170C | `Evf3` (0x170E) and `Ef3C` (0x170F) added to the status-name table at 0x7E8DA278/0x7E8DA280; absent in v1.1 |
| VF-4 display code | — | `display_open_evf_vf4` fn 0x7E6B2E03 (0x7E6B37AE); `OUT-EVF3!` 0x7E502DD6; `[VSC]…ID UnMached` 0x7E6B518E; `V_DROP_FLG` 0x7E6BBD3A (0x7E6BC6E5) | New |

- **So Evf3 = the VF-4 (verified by `OUT-EVF3!` together with `display_open_evf_vf4` being added in the same release).** This answers section 10e's open question. `EVF_TYPE_VF4` exists in **no** E-PM2 version (verified). The E-PM2 has only `EVF_TYPE_VF2/VF3`; the VF-4 is handled by the `…_vf4` functions instead.
- **Touch-panel stability (release note):** **unresolved.**
  - Peripheral code at ~0x7E512000–~0x7E51C000 (page-rounded (L1 2026-11-09)) (EV_SEM, MOT_COM/MAG_COM, TM_SEM, `TP_SEM` 0x7E51BDAC) was heavily restructured: about 50 changed, about 45 removed and about 35 added functions. That makes it a candidate (inferred).
  - The only touch-named change found, 0x7E51BDAC, is a boundary artifact.
  - `sdk api … ctrl touch.x touch.y` (0x7E9AC32E) grew by 35 instructions. Its role was not traced.
- **Undocumented in 1.2 (verified unless marked):**
  - **0x7E458938 is a new runtime I²C health check, not a debug command.** It is a timer callback (0x7E458A2C stores its pointer in the descriptor at 0x60414928). It checks the "ACC" device through 0x7E46144E(174). On failure it decrements a life counter at 0x60414958 (reset to 10), prints `ACC:I2C NG? LIFE:`, and re-initialises the device through 0x7E4650A2; when the counter goes below 0 it marks the device dead (state 2 at 0x604148F4) (audit 2026-11-09).
  - 0x7E458B28 is the ACC shell command. It already existed in v1.1 (0x7E458AAB, `otbl_all`); v1.2 only adds the subcommands `rreset`, `rdump` and `Who am I?:`. "ACC" = accelerometer is inferred from its x/y/z tables at 0/90/270° (audit 2026-11-09).
  - GUI LOWAPI area traces and `sdk dbggrid` (strings verified, purpose inferred). The rest of the rebuild (C++ app about 400, GUI about 130, camera core about 170 changed) was not attributed.

## 4. v1.3 — 40-150 F2.8 PRO (verified code; attribution inferred)

- **The only real code change is in 0x7E6232ED** (v1.2/1.3; v1.5 0x7E62396C, v1.6 0x7E623C09). Its caller is 0x7E60F5D7 in the movie/contrast AF code. The function picks one of three AF parameter sets (stack 72/76 = base + 0/+12/+24, with a double coefficient of 1.0 or 0.5) by a mode byte.
  - **v1.2:** mode 1 always used the "+24, ×1.0" set.
  - **v1.3:** mode 1 first calls 0x7E5222E2(0). This reads the u16 at 0x604F0A54[0] and maps 0x0B0A→0x1000; it is probably the lens protocol version (inferred). If the result is ≥ 0x1200, the 4-byte lens ID at +564 of the lens record is checked; it is assembled as `u16(b0,b1)<<16 | u16(b2,b3)`.
  - If the ID is **not** one of 0x1019, 0x1021, 0x1022, 0x21021, 0x21022, 0x21023, the **base (+0) set** is used. Otherwise the old "+24" set is used.
- **Lens names (external, ExifTool `Olympus.pm` LensType "make model release"):**
  - 0x1019 = 12-40 F2.8 PRO, 0x1021 = 14-42 EZ, 0x1022 = 25 F1.8;
  - 0x21021 = Nocticron 42.5, 0x21022 = Leica 15 F1.7, 0x21023 = 35-100 F4-5.6.
  - The 40-150 F2.8 PRO is 0x1020, which is **not** in the list. So the 40-150 PRO, and any other lens with protocol ≥ 0x1200 outside the list, now takes the new path. This fits the release note (inferred).
- **The other 1.2→1.3 code diffs are artifacts** (verified):
  - boundary splits at 0x7E57A802, 0x7E59521C, 0x7E5A4831, 0x7E640B45→0x7E640BC5+0x7E640C0C, 0x7E938731, 0x7EB54F46 and 0x7EB6318E;
  - data pages;
  - the version constant 0x1203→0x1300 at 0x7F09261F, 0x7F0A8EB7 and 0x7F0A9C30.

## 5. v1.4 — FlashAir W-03 (verified)

The whole 1.3→1.4 diff is 27 bytes: the version byte at 0x7E7BFB8D, two date strings (0x7E85BBB4, 0x7EBF4F1E), the version constant 0x1300→0x1400 (three sites), and:

| Function (v1.4 = v1.3) | v1.6 | Change |
|---|---|---|
| `isdio_read_register` 0x7F0A4B1C | 0x7F0A4AF4 | `mov 19,d0`→`mov 18,d0` (1 site) |
| `isdio_write_command` 0x7F0A4C62 | 0x7F0A4C3A | 19→18 (3 sites) |
| response/status reader 0x7F0A500F | 0x7F0A4FE7 | 19→18 (2 sites) |

- **What the value is (partly inferred).** All six sites build a request for 0x7F0A4A48 (v1.3/v1.4; 0x7F0A4A20 in v1.5/v1.6) with d0=0, d1=13 read / 14 write (13 at 5 sites, 14 at 1, in the write command), a1=iSDIO register address such as 0x603/0x440, stack = length, **stack+8 = 19/18**. The builder stores that value at request +24, then queues the request through 0x7E5CB393 (v1.3/v1.4; 0x7E5CBA12 in v1.5/v1.6) to the card driver (verified) (audit 2026-11-09). What field +24 means to the SD driver was not traced.
- **Conclusion.** The W-03 support is this one parameter change in the SPC/FlashAir overlay. The menu row and the SPC flow already existed in v1.3, because the GUI code is byte-identical (verified).

## 6. v1.5 — lens IS, Windows 10 (mixed)

| Item | v1.4 | v1.5 | Basis |
|---|---|---|---|
| New `is_type` classifier | — | 0x7E523C09: returns 0 if 0x7E51FD09(0) returns NULL or the lens record's (+6632) bit 0 (mask 1) is clear; 1 if 0x7E52260A()=1 (lens-ID byte0 = 0 **and byte1 = 0**); 2 if 0x7E522622()=1 (byte0 = 2 or 3, **byte1 = 0**); else 3. The ID bytes at +564 are make-lo, make-hi, model, release, so byte1 = 0 means make < 256 (audit 2026-11-09) | verified code; "1 = Olympus, 2 = Panasonic/Leica" inferred from ExifTool make codes |
| Panasonic-private-lens test (name inferred; earlier "Lens-OIS state test" had no support) (audit 2026-11-09) | 0x7E522323: returned bit 0 (mask 1) of 0x604F7F60 (record +6632; record base 0x604F6578 in v1.4) (audit 2026-11-09) | 0x7E5223DF: returns bit 0 of 0x604F7F64 **only if 0x7E522622() = 1**. The two callers that print (v1.5 0x7E528A8C/0x7E528B4D) use it to choose the `LENS_INFO_PANA_PRIVATE`(_STATE) page over the `OLY_PRIVATE` page; 4 other callers were not traced, and the `LENS OIS INFO` dump does not call it (audit 2026-11-09) | verified |
| IS decision that uses `is_type` | 0x7E5A6535: decided inline (prm 39057 / +731 / 39297 / 39089 → 1/2/3, stored to +3860; no lens-type test) | New 0x7E5A59EA + 0x7E5A5A5A write a **new** byte +735 (the old +735 field moved to +736), and 0x7E5A6D0A copies it to +3860. When 0x7E598A60()=1, 0x7E598A72()=1 sets the value to 1 in both branches, except that with `is_type`=1 a non-zero value from 0x7E5A5A5A is kept. When 0x7E598A60()≠1, the value is cleared if prm 33681 = 1 and prm 26865 = 1 (audit 2026-11-09) | verified code; "body/lens IS choice" inferred |
| Lens-info pages | list up to 025, `cmp 26` (0x7E526343) | adds 030 `LENS_INFO_ENABLE`, 033 `CURRENT_CONSUMPTION`; `cmp 34` (0x7E5266BC); `lens current` 0x7E524117/0x7E524134 | verified |
| Lens command set (`LENS_ASKDATA_MODE_*` 0x00–0x62) | — | **identical list** | verified (debug strings only) |

- **Answer to "new lens-communication commands?":** no new ASKDATA modes appear (verified). Two new lens-info pages appear (030, 033: enable flags and current draw; verified). Lens-IS cooperation is done mostly in body logic: the new type classifier, and the old OIS path gated by lens family (verified code, intent inferred).
- **Not Sync IS:** consistent with no new IS-sync command (inferred).
- **Windows 10: best code-level candidate found (link inferred) (audit 2026-11-09).**
  - The one functional change in the overlays is in the PTP stack. `SetDevicePropValue` (0x7F08B56E) accepts only property **0xD406** (`cmp 54278,a3`; any other code gets 0x2002) and calls 0x7F08CC99 for it.
  - In v1.4, 0x7F08CC99 (46 bytes) copies the host-supplied string (length byte × 2 bytes, bounded only by the 8-bit length) to RAM 0x602C1A98 with memcpy 0x7E5081FA, then returns 0x2001. In v1.5 it is `mov 0x2001,d0; retf`: it answers OK and stores nothing (verified). The 40-byte shrink shifts the later overlay code by −0x28; the call at 0x7F08B5DE differs only in its register-save operands.
  - 0xD406 is the MTP "Session Initiator Version Info" property, which the Windows MTP driver sets when it connects (outside knowledge, inferred). So this change is the best candidate for the Windows 10 item; the link is inferred.
  - Otherwise: overlay A does not change; overlay B has the three version constants 0x1400→0x1501; no USB descriptor or MTP string changed (verified).
- **Undocumented in 1.5 (verified):**
  - BGM WAV authentication `aud_tool_wav_judge_OLYMPUS_authentication` (0x7E960C93) now accepts `OLYMPUS CORPORATION    ` as well as `OLYMPUS IMAGING CORP.  ` (a second compare). This follows Olympus's 2015 company-name change (inferred).
  - Lens current-consumption readout.
  - A broad rebuild: lens about 85, files/DCF about 90, camera core about 160, body IS (BC) about 17 changed functions. These were not attributed.

## 7. v1.6 — H-ES200 / H-ES50200 AF (verified code; attribution inferred)

- **The prior claim (ep5-fw-reverse) is CONFIRMED for strings but CORRECTED for code.**
  - The only string change is indeed the removal of `**fcs_lens_mfts_move_lens_ofset_target()*`. But that string had **no code reference already in v1.5**: no 32-bit absolute reference anywhere in block 0 (verified). So its removal is dead-text cleanup, not the fix.
  - The block-0 diff is **not** "≈ relocation". The pipeline counts 358 changed code functions: 295 in the AF code ~0x7E5E3000–~0x7E627000 (page-rounded (L1 2026-11-09)) and 63 outside it. Most of the 63 are data decoded as code or boundary splits. Outside the AF range the only real changes are the three version constants and one constant in 0x7E63A20F (v1.5; v1.6 0x7E63A4BB, `cam_frame_sync.c`: `mov 1146,d0` → `mov 1151,d0`) (verified) (audit 2026-11-09).
- **What changed (verified):**
  1. **New clamp helper 0x7E626BD4** = `clamp(d0, lo=a0, hi=d1)`. It has 39 call sites in 16 AF functions. All 39 pass hi = 32767; 38 pass lo = −32768, and one (0x7E60A5EE in 0x7E60A3DE) passes lo = 0 (audit 2026-11-09). Example: `fcs_lens_mfts_move_lens` 0x7E60E5A9 → 0x7E60E648 now clamps the target to the s16 range before the `movhu` store into the lens-command buffer. v1.5 stored the int truncated.
  2. **16→32-bit widening.** In the AF range, `movhu` drops 10,257→9,734, `exth` drops 1,785→1,359 and word `mov` rises 44,771→45,391. Example: CAF helper 0x7E6261FA → 0x7E626497 reads a 32-bit field (+1804) where v1.5 read a u16 (+1792) and sign-extended it.
  3. **Sentinels change** from `cmp 0x8000`/`cmp 0` to `cmp −32768`/`cmp 0x80000000` in about 30 functions (e.g. 0x7E5EC7BD→0x7E5EC799, 0x7E605F9F→0x7E605F6C).
  4. **AF structs grow:** field offsets +8 (564→572, 692→700), +12 (1084→1096, 1120→1132), +24 (37048→37072); one block grows by 1,052 (14956→16008).
- **No H-ES200/H-ES50200 lens ID** (0x21036/0x21037, i.e. ExifTool `2 36 10`/`2 37 10`) appears in v1.5 or v1.6, as an immediate or as table bytes (verified). The fix is generic.
- **Interpretation (inferred, strong):** focus positions or pulse counts overflowed 16 bits with these long Panasonic lenses. v1.6 computes them in 32 bits and saturates only when it writes the lens command.

## 8. Key addresses per version (verified)

| Release | What | Old address (prev. version) | New address |
|---|---|---|---|
| 1.2 | Accessory-ID probe / ID-pair table / bus-config table | 0x7E46445A / 0x7E4C6804 / 0x7E4C6828 | 0x7E464850 / 0x7E4C6F88 / 0x7E4C6FB0 |
| 1.2 | edev records / status items / `Evf3` name record | 0x7E733A24 / 0x7E7339F4 / — | 0x7E734A4C / 0x7E734A14 / 0x7E8DA278 |
| 1.2 | Version constant 0x1101→0x1203 | 0x7F0A9BF9 (fn) | 0x7F0A9C30 |
| 1.3 | AF parameter-set chooser (lens-ID test) | 0x7E6232ED (564 B) | 0x7E6232ED (692 B); v1.6 0x7E623C09 |
| 1.3 | Lens-protocol getter it calls | — | 0x7E5222E2 |
| 1.4 | iSDIO read / write / response (19→18) | 0x7F0A4B1C / 0x7F0A4C62 / 0x7F0A500F | same; v1.6 0x7F0A4AF4 / 0x7F0A4C3A / 0x7F0A4FE7 |
| 1.4 | Version byte; date strings | 0x7E7BFB8D; 0x7E85BBB4, 0x7EBF4F1E | same |
| 1.5 | `is_type` / Panasonic-private-lens test (audit 2026-11-09) / IS decision | — / 0x7E522323 / 0x7E5A6535 | 0x7E523C09 / 0x7E5223DF / 0x7E5A59EA + 0x7E5A5A5A |
| 1.5 | Lens OIS dump / lens-info list / WAV auth | 0x7E523BED / 0x7E526343 / 0x7E960C93 | 0x7E523EA2 / 0x7E5266BC / 0x7E960C93 |
| 1.6 | `move_lens` / CAF helper / clamp | 0x7E60E5A9 / 0x7E6261FA / — | 0x7E60E648 / 0x7E626497 / 0x7E626BD4 |
| 1.5 | PTP property 0xD406 handler (stubbed) (audit 2026-11-09) | 0x7F08CC99 (46 B) | 0x7F08CC99 (6 B) |
| 1.6 | Removed dead string; start of +0x2AC shift | 0x7E7A80FB; 0x7E626937 | —; 0x7E626BE3… |
| 1.6 | Overlay-B version constant 0x1501→0x1600 (three sites) (L1 2026-11-09) | same addresses in v1.5 | **`mov 0x1600,d0` at 0x7F0A8F06** in the ADJSLF CSV identity-record writer 0x7F0A8E8F (it prints the value with `%04X`); the getter 0x7F0A9C08 (`mov 0x1600,d0; retf`, 2 callers 0x7F0B3E9E/0x7F0B8D18); `mov 0x1600,d2` at 0x7F0926F8 in the digit formatter 0x7F0925F7. The v1.3 addresses in §4 (0x7F09261F, 0x7F0A8EB7, 0x7F0A9C30) are not the v1.6 ones |

## 9. Release-note items vs code

- **Found in code:** VF-4 (1.2); 40-150 PRO AF (1.3, attribution inferred); W-03 (1.4); lens IS (1.5, mechanism inferred); H-ES200 AF (1.6, attribution inferred).
- **Candidate only:** Windows 10 (1.5): the stubbed PTP property 0xD406 handler (code verified, link inferred) (audit 2026-11-09).
- **Not found:** the 1.1 exposure fix (no v1.0 image); the 1.2 playback touch-panel fix (not isolated within the large peripheral rework).
- **Undocumented changes:**
  - 1.2: an I²C "ACC" health check with a life counter (runtime code) and new ACC shell subcommands (audit 2026-11-09), GUI LOWAPI traces and `sdk dbggrid`, plus a full rebuild.
  - 1.5: WAV-BGM maker string, lens current-consumption page and `lens current`, plus a full rebuild of lens, DCF and camera core.
  - 1.6: removal of a dead debug string.

## Open questions

1. What does request field +24 (19 vs 18) mean in the card driver behind 0x7E5CBA12 (v1.3/v1.4 0x7E5CB393)? Is it a timeout, a function number or a retry count?
2. Which function in the 1.2 peripheral rework (~0x7E512000–~0x7E51C000 (L1 2026-11-09)) is the playback touch fix?
3. What do the outputs of the 1.5 IS decision (byte +735, `is_type` 1 vs 2) select downstream: body IS, lens IS or both?
4. The 1.1→1.2 and 1.4→1.5 rebuilds have about 1,400 and about 570 changed code functions; most are unattributed. A per-module pass with `region.py` would sort refactors from fixes.
