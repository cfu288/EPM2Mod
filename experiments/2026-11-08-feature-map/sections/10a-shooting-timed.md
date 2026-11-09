# 10a. Timed and sequence shooting features: re-check (E-PM2 v1.6)

Scope: interval shooting / time-lapse movie, the six bracketing modes (including HDR BKT), Live Bulb / Live Time, multiple exposure, and the other timed or sequence features found in the shooting code.

- **Labels:** **verified** = read in the code or bytes; **inferred** = from names, order or layout; **external** = product knowledge, not from the code.
- **Addresses:** E-PM2 v1.6 runtime addresses (base 0x7E421020) unless a body is named.
- **Scripts:** `/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/hidden/shooting-timed/`: `top.py` and `top24.py` (top menu tables), `sub4.py` (sub-item table), `ptree.py` (GUI panel tree), `norm.py` (compares functions across bodies). The mcon dumps use `art-gui/mcon.py` and `art-gui/comp.py`.

## Verdict table

| Feature | Prior claim | Verdict | Real status on E-PM2 | Shipped on (menu row or UI text) |
|---|---|---|---|---|
| Interval shooting + time-lapse movie (info 482–486) | Dormant (inf); complete code; no menu sets 482 | **CONFIRMED, now verified.** The only difference from the E-PL6 is one missing top-menu row | **Dormant-complete.** Reachable only through debug shells | **E-PL6 1.4, E-P5 1.8, E-M10 1.4, E-PL7 1.4** (verified top-menu rows). E-M5 II / PEN-F: UI text only. **Not** E-PL5 or E-PM2 |
| HDR BKT (info 476) | "Sub-item table is a superset; the E-PM2 does not offer HDR BKT" | **CORRECTED.** I found no code that hides it | **Active (inferred, strong).** It is listed in the Bracketing page. It shoots bracketed exposures only; the E-PM2 has no HDR merge code | Same panel data in E-PL6. In-camera HDR1/HDR2 merge is a top-menu "HDR" item from the E-M10 / E-PL7 on |
| AE / WB / FL / ISO / ART BKT (480, 90, 140, 216, 406) | Visible (inf) | **CONFIRMED** | **Active** (verified tables) | all bodies checked |
| Live Bulb / Live Time | Active; "update-interval code not found" | **CONFIRMED; interval found** | **Active** (verified: Custom Menu item, mcon list, TAKE reads it) | all |
| Multiple exposure (268–270) | Active; a stub call plus the real `api_rec_Bayer_MultiExp` | **CONFIRMED** | **Active** (verified top-menu row, panel 16, real API) | all |
| Anti-shock drive modes | (none) | new | **Active** (verified: 6 anti-shock entries in the drive-mode list) | all |
| Custom self-timer (473–475) | (none) | new | **Active** (verified: panel 629 and drive-list entries) | all |
| Live Composite | (none) | new | **Absent.** No UI text; only 3 unreferenced `api_rec_dummy_*TakeComposite` name strings | E-M10, E-PL7 ("Composite Settings" text) |
| Keystone compensation | (none) | new | **Absent** (no strings, no code found) | E-M5 II, PEN-F (text) |
| Focus bracketing | (none) | new | **Absent** in all 8 bodies (no strings) | none of the 8 |

## 1. Interval shooting / time-lapse movie

### 1.1 Code (verified)
- **Settings.**
  - 482 → prm 0xDE11 (u8, default 0), the on/off switch.
  - 483 → 0xDE21, frames (u8, default **0**).
  - 484 → 0xDE34, start waiting time (u32, 0).
  - 485 → 0xDE44, interval time (u32, 0).
  - 486 → 0xDE51, make the time-lapse movie (u8, 0).
- **mcon value lists** (records at 0x7E84A0B8):
  - 482 = [0, 1] (record 0x7E84C5E8).
  - 483 = 1..99 (record 0x7E84C5FC).
  - 486 = [0, 1] (record 0x7E84C610).
  - 484 and 485 have no list. Their GUI panels 639 and 640 are of type 39, which is a time editor (the "time editor" meaning is inferred).
- **mcon interlock rules** (60-byte records at 0x7E814864; these are the per-setting operation records, and the hooks below sit in their **+24** post-write slot, 13e §3.2 (D1 2026-11-09)):
  - Record 0x7E817618 (482) has hook 0x7E7039C4: when 482 = 1, multiple exposure (268) is cleared.
  - Record 0x7E8175DC (268) has hook 0x7E703986: when 268 ≠ 0, 482 is cleared through the mcon setter 0x7E6FEAE0.
  - So interval shooting and multiple exposure exclude each other.
- **Guards and sequence.**
  - The guards `isStartIntervalShootingEnable` 0x7E969C11, `isCreateTimeLapseMovieEnable` 0x7E969ACE and `isEndIntervalShootingEnable` 0x7E969B43 all read 482.
  - `OlyHfwOpeShoot::startIntervalShooting` 0x7E98849B.
  - The SequencePartsBase interval states: 0x7EA98808, 0x7EA98DF4, 0x7EA98F94 (next time), 0x7EA99881 (first shot), 0x7EA997E5 (shot done).
- **Movie builder.** `mov_edit_check_param` 0x7E6D493D accepts only quality 3 (720p), sound disabled, MJPEG, and fps ∈ {1, 2, 3, 5, 6, 10, 15, 30}. Otherwise it returns 0xFF01. This confirms the prior claim.
- **GUI shooting controller** (0x7ECD1BC1–0x7ECDA5C6). This is the GUI's shooting state controller, not menu code.
  - `0x7ECD2D50` reads 482.
  - The mode-change path `0x7ECD5270` at 0x7ECD5598 tests the setting. If the check `0x7ECD5E61` fails, it writes 482 = 0; otherwise it enters the interval state (`0x7ECD2D75`).
  - `0x7ECD9F05` (vtable 0x7EEE8968) starts interval shooting. `0x7ECD9F4B` and the functions after it handle completion, cancel, sleep and wake.
  - The GUI state flag is RAM 0x605EFD78 (`0x7ECD2D2C` sets it, `0x7ECD2D35` reads it).
- **Debug strings.** `sdk dbgseq set INTERVAL_SHOOTING 15` (0x7E99B118) only turns on a log category. It does not start the feature.

### 1.2 Reachability (verified unless marked)
- **Top menu.** The E-PM2 top table (0x7EFFE13C) goes from Multiple Exposure straight to Flash RC Mode. The E-PL5 table (0x7EFFEA28) is identical. The **E-PL6 1.4 table (0x7EFFF864)** has one extra row between them: `Time Lapse Settings` (label 1357, help 1358, kind 0x102).
- **The panel layer is present and identical in E-PM2 and E-PL6.** The GUI panel tree is made of 40-byte records `{id, -15, type, 1, 1, children*}`; 222 records in each body; the parsed records match. Two panels matter here:
  - Panel 628 has the children (636, 637).
  - **Panel 637** has the children (638, info 483), (639, 484), (640, 485) and (641, 486). Its record is at 0x7EFFDB74 and its child list at 0x7EFFA3C4.
  - Panel 637 is in the panel factory hash 0x7EFE5814 and opens the generic sub-item panel 0x7EDE1E3D (verified).
  - **No panel lists 628 as a child** in either body. On the E-PL6 the only way in is the extra top-menu row. On the E-PM2 nothing opens 628 or 637 (verified for the panel tree and the top table).
- **Constant writes of 482 all store 0** (verified). These are:
  - the 7 GUI `setSetting(482, 0)` calls listed in section 07;
  - the mcon hook 0x7E703997, which section 07 missed.
- **The "info tables" 0x7EFF8DF4 and 0x7F019004 named in section 07 are not settings paths.**
  - 0x7EFF8DF4 is the child list of **GUI panel 91** (record 0x7EFFAB2C). The values 482 and 483 there are panel ids, not info ids (verified).
  - 0x7F019004 is part of a 12-byte-record list (0x7F016CF4–0x7F019160) with the same 477…498 id run. It is probably also a panel-id list (inferred).
- **Myset:** not traced. Myset only stores and restores current values. 482 is never 1 to begin with, so Myset cannot be a separate way in (inferred).
- **PTP:** not traced. No PTP code reading 0xDE11 was found.
- **Debug:** `app Set_CameraInfo 482 1` or `prmdbg setval 0xDE11 1` would set the switch.
  - The GUI reacts to the value through 0x7ECD5270.
  - The frame count (483) still defaults to 0, and the GUI prints ` IntervalShooting Count ZERO ` (0x7ECD2DC2). So 483–485 would also need prmdbg. Whether the camera would then shoot was not tested.

### 1.3 Cross-body (verified)
- **E-PL5 1.6:** identical guard and identical `startIntervalShooting` (0 differences after address normalisation). Its top table is the same as the E-PM2's, so the feature is dormant there too.
- **E-PL6 1.4:**
  - The guard 0x7E96AA4B and `IntervalShooting valid` 0x7ECD30A6 are identical.
  - `startIntervalShooting` 0x7E98948E has **one extra call** (to 0x7E998F12) after the next-shot-time check. This may be a fix (inferred).
  - It adds the top-menu row. Shipped. External: the E-PL6 is known as the E-PL5 successor that added interval / time-lapse.
- **E-P5 1.8:**
  - It uses a 24-byte menu record format. Its menu table at 0x7EDB5884 contains `Time Lapse Settings` bound to info 482.
  - Its guard differs in 5 lines and its `startIntervalShooting` is shorter (113 vs 168 instructions), so it is a different code branch.
  - Shipped.
- **E-M10 1.4 and E-PL7 1.4:** a top-menu `Time Lapse Settings` row. The info is renumbered to **478**: the E-M10 guard 0x7DFC1741 reads 478. Shipped.
- **E-M5 II and PEN-F:** UI text only ("Takes specified number of photos…", PEN-F "Intrvl. Sh./Time Lapse"). Their menus were not checked.

## 2. Bracketing, HDR BKT, and HDR merging

### 2.1 Value lists (verified, mcon type-6 records; values are {count, step in 1/256 EV})
- **AE BKT (480)** has three variants, chosen by the record's +2 field. That field is the EV step setting: 0x55 = 1/3 EV, 0x80 = 1/2 EV, 0x100 = 1 EV. The variants are verified by the step value stored in each entry.
  - 1/3 EV step: 2/3/5 frames at 0.3, 0.7 and 1.0 EV, and 7 frames at 0.3 and 0.7 EV.
  - 1/2 EV step: 2/3/5/7 frames at 0.5 and 1.0 EV (7 frames at 0.5 EV only).
  - 1 EV step: 2/3/5 frames at 1.0 EV.
  - So the +2 field is **not a model gate** (section 09a left it undecoded).
- **WB BKT (90 + 613/561):** 3 settings (2, 4, 6 steps).
- **FL BKT (140 + 608)** and **ISO BKT (216 + 646):** 3 frames at 1/3, 2/3 and 1 EV.
- **ART BKT (406):** on/off, plus the 19 flags 407–424 and 469 (section 09).
- **HDR BKT (476 + 478):** GUI 25–29 = 3, 5 or 7 frames at 2.0 EV, and 3 or 5 frames at 3.0 EV.
- **HDR BKT interlock.** The mcon hook 0x7E703540 (record 0x7E818158, +24 post-write slot (D1 2026-11-09)) runs when 476 is set non-zero:
  - it clears AE (480), FL (140), 609, WB (90), 146, ISO (216) and ART (406) bracketing;
  - it copies the value to 477.
- **Shot count.** SequenceParts `0x7EA94F7A` sets `_bracketMaxShootCount` from AE (480), FL (140) or HDR (476). The `HDR_BKT MEDIA_FULL` check is at 0x7EA92502.

### 2.2 Reachability (verified for the code below)
- **The top menu has a `Bracketing` row** (kind 0x100). It leads to GUI panel 15, whose child list is (452, 480), (453, 90), (454, 140), (455, 216), (456, 406) and **(634, 476)**. Panel 15 is opened by the generic sub-item panel 0x7EDE1E3D: a 3308-byte singleton with the current group at +3296.
- **The row filter has no rule for group 15.** The generic list builder `0x7EDE2192` drops a row only when `0x7EDE29B3` returns 0. That function has rules for only three groups:
  - group **274** (picture-mode parameters, which depend on info 211);
  - group **10** (Picture Mode show flags);
  - group **152** (info 15129).

  Every other group, including 15 (Bracketing) and 637 (Time Lapse), always returns 1. So all six bracketing rows, HDR BKT included, are built.
- **Greying.** Each row's enabled state comes from the per-row flag array copied by `0x7EDCDAAB` (234 bytes from RAM 0x602B3ADE; source not traced). This can grey a row out but does not remove it.
- The labels "HDR BKT" (1950 in the sub-item table, 1746 elsewhere) are referenced by GUI data tables, just as the other BKT labels are (inferred support).
- **Verdict:** the prior claim had no code basis. I found nothing that hides HDR BKT on the E-PM2. On-camera confirmation and a manual check are still needed (no network here).

### 2.3 HDR merging (verified by string and API search)
- The E-PM2 has **no** HDR merge code: no `HDR_COMBINE`, no `*_HDR` API names, and no "composite into a high contrast image" text. HDR BKT only shoots a series of exposures.
- The E-P5 has the API names `api_rec_dummy_Record_Media_HDR` and `..._Get_HDR_Combine_Progress` and the guard text `… Interval or HDR_COMBINE`. It also has the texts 2221/2222 ("4 picture are taken… Composited automatically").
- The E-M10, E-PL7, E-M5 II and PEN-F have a top-menu **HDR** item (verified rows at 0x7E5B1CA6 for the E-M10 and 0x7E5DAACE for the E-PL7) and `MODE_HDR1_HDR2_JUDGE_NG`.

## 3. Live Bulb / Live Time (verified)
- **Settings.** Info 437 (Live BULB, prm 0xD732, default 0) and info 438 (Live TIME, prm 0xD752, default 1). Both mcon lists are u16 [0, 1, 2, 4, 8, 16, 30, 60, 120].
- **Units.** Read as Off, 0.5 s, 1, 2, 4, 8, 15, 30 and 60 s: the value is in 0.5 s units (the unit is inferred from the ×500 below and matches the product's list).
- **Menu.** The custom-menu item lists (panels 25–34 and 582; panel identity inferred) contain (588, info 437) and (589, info 438). Panels 588 and 589 are type 37, beside the bulb timer and bulb focusing items. So the settings are reachable from the Custom Menu.
- **Selection.** The mcon hook `0x7E7045C4` copies one of them into **info 436** (prm 0xD712):
  - shutter (info 4) = 0x8000 (BULB) → copies 437;
  - shutter = 0x7FFF (TIME) → copies 438.
- **Gate.** `0x7E96AA41` makes Live Bulb active when the exposure mode (info 24) = 6 (M), the shutter = BULB, and 436 ≠ 0.
- **Interval (answers section 03, open question 6).** The TAKE function `0x7E5A5295` reads prm 0xD712 and stores **value × 500 (ms)** in u16 field +30 of the take parameter block, through `udfu01 500`. The same function stores another setting × 60000 at +24; this is probably the bulb timer in minutes (inferred). Other readers of 0xD712: 0x7E5A0FA9, 0x7E5A5BF9, 0x7E5A6631, 0x7E5A9DC5.

## 4. Multiple exposure (verified)
- **Top menu.** The `Multiple Exposure` row (kind 0x102, info 268) leads to panel 16: (462, 268 Frame), (463, 269 Auto Gain), (464, 270 Overlay).
- **mcon lists.** 268 = [0, 2], so the only choices are Off and 2 frames. 269 and 270 = [0, 1].
- **Stub versus real.** `CapMex_MultiExposure` 0x7EA44886 calls both:
  - `api_rec_dummy_MultiExp_Start` 0x7E68C70B, which is only `mov 15,d0`, a log call (0x7E678422) and `ret`;
  - the real `api_rec_Bayer_MultiExp` 0x7E689C04, which logs and passes multi_num, ulHandle[0..4], usMode and usMultiNum to the REC job.
- **Interlock.** Multiple exposure and interval shooting exclude each other (§1.1).

## 5. Other timed or sequence features
- **SequenceParts classes found:** Base (interval, self-timer), MultiExposure, Panorama, Eportrait, PictBkt (ART BKT) and Otwb (one-touch WB). I found no other SequenceParts class (by string search).
- **Anti-shock (verified).**
  - The drive-mode list is mcon composite 2074 = {549, 555, 625, info 0, 87, 568, 166}, 12 entries.
  - Six of them have info **166 = 1**, the anti-shock flag (GUI 25, 16, 17, 23, 13, 12). That 166 is the anti-shock flag is inferred: it is set on exactly the entries that would carry the "Anti-Shock" drive labels.
  - Camera core: `cam still` option bit 3 antishock and "Setting AntiShock Ready" (0x7E62F370). Active.
- **Custom self-timer (verified).** Panel 629 holds Frame 473 (1–10), Timer 475 (1–30 s) and Interval 474 (5, 10, 20, 30; units inferred as 0.1 s). It is used by the drive-list entries with info 0 = 5 (GUI 24, 25). `KIND_CUSTOM_INTERVAL` is at 0x7EA981DB. Active.
- **"COMPOSITE" in `MODE_EXPOSE_COMPOSITE` (0x7E7FE1A4) is the Fragmented art filter**, not Live Composite. It sits in the art "expose mode" name list with FISH_EYE, DRAWING and the others (section 09).
- **Live Composite: Absent.** The only traces are the orphan strings `api_rec_dummy_Start/End/Get_Count_TakeComposite` (0x7E7D592C…), which nothing references (xref: none), and there is no UI text.
  - The E-M10 has the same orphan strings, yet it shipped the feature ("Composite Settings" 2332, "BULB/TIME/COMP"). So these strings say nothing about whether a body has the feature (verified for both bodies).
- **Keystone compensation:** the text exists only in the E-M5 II and PEN-F. The E-PM2 has no "keystone" strings. Absent.
- **Focus bracketing:** no text or strings in any of the 8 bodies. Absent.
- **`MODE_AUTO_HORIZONTAL_CORRECTION`** is an `executeMode` case in the GUI shooting controller (0x7ECD8022, string 0x7EED4EFC). It is a button-function mode; what it does and whether it can be reached were not traced.

## 6. Audit of prior claims

| Claim (section) | Verdict | Evidence |
|---|---|---|
| Guard 0x7E969C11 reads info 482 (prm 0xDE11) (06, 07) | CONFIRMED | Bytes are identical to the E-PL5 and E-PL6 guards; the info table maps 482 → 0xDE11 |
| `startIntervalShooting` 0x7E98849B and the SequencePartsBase functions (06) | CONFIRMED | §1.1 |
| The time-lapse movie builder is MOV_EDIT 0x7E6D4597, 720p MJPEG only (04) | CONFIRMED | `mov_edit_check_param` 0x7E6D493D |
| "Menu code at 0x7ECD1BC1–0x7ECDA5C6" (06) | CORRECTED | It is the GUI shooting state controller (release and mode change), not a menu. The time-lapse menu panel is 637 (generic panel 0x7EDE1E3D) |
| "No menu record sets 482" (07) | CONFIRMED and explained | The E-PM2 top table lacks the row that the E-PL6 adds. Panel 628/637 has no parent |
| "Every constant write of 482 stores 0" (07) | CONFIRMED (+1 site) | Also the mcon hook 0x7E703997 |
| "Time Lapse Settings (group 637, infos 483–486) exists in the sub-item table" (07) | CONFIRMED | It is also a complete GUI panel (637 → 638–641) |
| The info tables 0x7EFF8DF4 / 0x7F019004 list 482 and 483 (07) | CORRECTED / UNRESOLVED | 0x7EFF8DF4 is panel 91's child list (panel ids). 0x7F019004 is probably a panel-id list too (inferred) |
| Interval shooting is "Dormant (inf)" | CONFIRMED, now verified | §1.2 |
| "The sub-item table is a superset; HDR BKT not offered" (07) | CORRECTED | §2.2: the HDR row is built; no filter applies to group 15 |
| Live Bulb is Active; "update-interval code not found" (03) | CONFIRMED; interval found | 0x7E5A5295 (×500 ms), 0x7E7045C4, 0x7E96AA41 |
| Multiple exposure: "one stub call but the real function is used" (06) | CONFIRMED | §4 |

## 7. Open questions
1. Is HDR BKT really selectable on an E-PM2? This needs an on-camera check or the manual. Where does the per-row grey-out array (copied by `0x7EDCDAAB`) come from?
2. With 482 and 483–485 set through prmdbg, does the E-PM2 complete an interval run and build the time-lapse AVI?
3. The PTP set-property path and Myset load (`loadCustom`, 0x7ECD9145) were not traced for 482.
4. What does the extra E-PL6 call (0x7E998F12) in `startIntervalShooting` fix?
5. The meaning of info 166's delay setting, and how the anti-shock delay ("1s…30s") is stored.
6. What `MODE_AUTO_HORIZONTAL_CORRECTION` does, and what panel 91 (children 482, 483, 258, 259, …) is.
