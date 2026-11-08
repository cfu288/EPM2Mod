# 10c — Movie: re-examination of the "hidden" movie features (E-PM2 v1.6)

This section checks the movie claims in [04-movie.md](04-movie.md) and docs/firmware-map.md §3 "Movie" again, with the method of section 09: code, then reachability, then other bodies.

- **Labels:** **verified** = I read it in code or bytes; **inferred** = from names, order or layout; **external** = product knowledge, used only as support.
- **Addresses:** E-PM2 v1.6 runtime addresses (base 0x7E421020) unless a body is named.
- **Scripts:** `$S/hidden/movie/` (S = the session scratchpad). `rawq.py` finds {quality, format, fine} composite records; `mrec.py` walks mcon records; `lbltab.py`/`xlbl2.py` decode GUI label lists; `opt32.py`, `cust.py` and `sub.py` decode the menu option, Custom-menu and sub-item tables.

## Verdict table

| # | Feature | Prior claim | Verdict | Real status on E-PM2 | Shipped on (bodies checked) |
|---|---|---|---|---|---|
| 1 | AVCHD recording | Unknown; menu reachability open | **CORRECTED** | **Hidden / debug-only, code complete.** The GUI cannot select format 2 (verified). Only the debug shells can store it (verified path, end result not run) | None of the 8 bodies has AVCHD in its info-45 movie-quality list (verified). External: AVCHD shipped on the 2011 PENs (E-P3/E-PL3/E-PM1), none of which is in the set |
| 2 | Movie effects (multi echo, one-shot echo, art fade) | Active (inferred for the menu) | **CONFIRMED with corrections** | **Active (inferred)**. The on/off gate "Movie Effect" (info 444) is a Custom Menu I item (verified table). The effect ids 2335/2336/2337 have complete handlers in the GUI key dispatcher (verified). They are **not** assignable to any button (verified mcon lists), so the trigger must be another input, most likely the touch icons (not traced; external) | Same code and strings in E-PL5, E-PL6, E-P5 (verified strings); later bodies have the English text (verified) |
| 3 | "PSP" multi-window live view | Unknown | **CORRECTED** | **Dormant / debug-only (inferred).** PSP is the background layer (JPEG/fill/black) of a 4-window "multi-through" live view. The types are MAGIC_FILTER 0, WB 1, EXPOSE 2 (verified). App and API code exist and the `sdk api` shell exposes them (verified). No GUI caller was found (not fully traced) | Becomes **Photo Story**: E-P5 1.8 and E-M10 1.4 already have `Photo_Story Mode` code (verified strings). English "Photo Story" text exists only from the E-PL7 on (verified) |
| 4 | `mov` shell: `set QUALITY FPS`, `ansh` x/y, `w` | Advertised, not implemented | **CONFIRMED** | Help text only. QVGA (320×240) exists only as an MJPEG code path; no 60 fps record path was found | — |
| 5 | MJPEG sizes 1280×720, 640×480, 320×240, 160×120 | All in code | **CONFIRMED + reachability** | **1280×720 and 640×480 are reachable** (GUI 4/5). 320×240 and 160×120 have no GUI value (verified) | Same 6-entry list in all 8 bodies (verified) |
| 6 | Time limit / file size | Verified earlier | **No discrepancy** in the limit. One refinement to 04 §1.3 (art-code frame budget, see §6) | Active | — |
| 7 | Movie art filters | mov_art accepts 100–120 incl. hidden ids | **CONFIRMED, narrowed** | **12 shipped filters only.** Movie uses the same Picture Mode setting (prm 0x9481) and the same 19-entry GUI list. No movie-only list exists. `art_chk_type_mov` accepts only shipped codes (verified) | As section 09 |

## 1. AVCHD

**Code (verified, 04).** The full record path exists: MOV_AVCHD/MOV_BRIDGE, the rate table at 0x7E6EDE08 and the `/PRIVATE/AVCHD/BDMV/STREAM/%05d.MTS` path builder 0x7E5C1164. The full playback path also exists (CLPI parser 0x7E6E2323/0x7E6E2582).

**What the GUI can select (verified):**
- The movie-quality item is **info 45**. Its mcon record 0x7E84A554 is type 6 (composite), with gui[] 0x7E83F890 = [0..5] and raw[] 0x7E846500 (6 × 64 bytes).
- The composite id list 0x7E8189E4 is **{45, 405, 694}**: info 45 = prm 34145 (quality), info 405 = prm 26225 (format), and info 694 = prm 33105[7] (Fine/Normal).

| GUI | 34145 quality | 26225 format | 33105[7] | Label (GUI label list 0x7EFC674C, owner record 0x7EFC8BF0 `{info 45, ptr, n = 6}`) |
|---|---|---|---|---|
| 0 | 6 | 3 MOV | 1 | MOV 1920×1080 Fine (1705) |
| 1 | 6 | 3 MOV | 2 | MOV 1920×1080 Normal (1706) |
| 2 | 3 | 3 MOV | 1 | MOV 1280×720 Fine (1707) |
| 3 | 3 | 3 MOV | 2 | MOV 1280×720 Normal (1708) |
| 4 | 3 | 1 MJPEG | 2 | Motion JPEG 1280×720 (1700) |
| 5 | 4 | 1 MJPEG | 2 | Motion JPEG 640×480 (1701) |

- **The list never contains format 2 (AVCHD) or quality 5 (AVCHD 1080).** It also never contains MOV quality 4, the 4 Mb/s VGA MOV of 04 §1.1, so that mode is unreachable too.
- Under the 09a write fallback, the GUI cannot store any other combination.
- Info 405 appears in no other composite record and has no mcon record of its own (verified: `compall.py`, `mcon.py`).
- **Other writers (verified, static):** 07-settings.tsv lists 0 constant prm sets and 0 Set_CameraInfo calls for 26225 or 34145. I checked the 31 constant loads of 26225/34145 in code: all are reads (getter 0x7E457C75, or the address getter 0x7E457C52 at 0x7E6B39A3).
- **Debug path:** `app Set_CameraInfo 405 2` (09a: no range check) or `prmdbg` could store AVCHD. The record path would then take the AVCHD branch at 0x7E6ED571. That branch is complete, but I did not run it. Status: **Hidden-debug-only, complete code**.
- The AVCHD strings (591 "AVCHD 1920×1080 Normal", 1099–1101, and 1016 "Cannot take the movie with AVCHD mode.") are in block 1. Block 1 is shared, so they prove nothing about E-PM2 support. They are also used in display tables at 0x7EFEA79C and 0x7F01D8B0, whose purpose I did not decode (probably playback information; inferred).

**Cross-body (verified):**
- `rawq.py` finds the same 6-record {quality, format, fine} list in every body: E-PL5 0x7E84765C, E-PL6 0x7E84735C, E-P5 0x7E543518, E-M10 0x7DC4230C, E-PL7 0x7DCB316C, E-M5 II 0x603A6A60 and PEN-F 0x603D7A78.
- `own.py` shows that in each body the record pointing at that list is **info 45**, type 6, gui [0..5].
- No body has any run of these records with format 2.
- The E-PL5, E-PL6 and E-P5 label lists name the same six strings (E-PL5 0x7EFC6F8C, E-PL6 0x7EFC7B7C; E-P5 uses a 24-byte layout at 0x7EDA7EB8).
- Limit: the E-M5 II and PEN-F have extra movie modes (ALL-Intra, Super Fine, 60p strings 2617–2636). Those must be selected through other info ids, which I did not decode. My "no AVCHD" result for them covers only the info-45 list.
- The CPU1 AVCHD strings (`[AVCHD]`, 169 of them) exist in the E-PL5, E-PL6 and E-P5. The E-M10 and later bodies strip debug strings, so this test cannot show whether their AVCHD code is present.

## 2. Movie effects (KDG)

**Engine (verified, 04 §3.2):** `mov_kdg_exec` 0x7E6DB6D1.

**API layer (verified):**
- `OlyHfwOpeShoot::ctrlMovieEffect` 0x7E982787 and `rcvShtCtrlMovieEffectIn_active` 0x7EA7A7A0 both call `isCtrlMovieEffectEnable` **0x7E96A6B1**.
- The control codes are 0 MULTIECHO_START, 1 MULTIECHO_END, 2 ONESHOT, 3 ABORT, 4 ART_SELECT_START, 5 ART_SELECT_ABORT and 6 ART_EFFECT_START. The names come from the enum printer 0x7E9AB845 (code order inferred from string order).
- `api_movie_Get_MovieEffect_Type` 0x7E682B09 returns the running effect, 0..5.

**Gates in 0x7E96A6B1 (verified):**
- The mcon GUI value of **info 44** (prm 34129) must be ≠ 0.
- The mcon GUI value of **info 444** (prm 26817, u8, mcon list [0, 1]) must be ≠ 0.
- Then come through-image, recording and AF-state checks, followed by a per-ctrl table of the allowed current effect types.

**The "Movie Effect" setting is a menu item:**
- The Custom Menu item table at 0x7EFF7E80–0x7EFF8360 has 16-byte rows `{group, label, info, 0, pos, help, …}`. Group 8 (= Custom Menu I "Movie") holds:
  - Movie Mode (94, info 162)
  - Movie sound (180, info 102)
  - **Movie Effect (1492, info 444, help 1493 "Enable or disable movie effect in movie mode")**
  - Wind Noise Reduction (1087, info 434)
  - Recording Volume (1373, info 435)
- The table is read by the menu code 0x7EDE9B9B… (`mov 0x7EFF7E80,a0`).
- **Verified:** the layout and labels.
- **Inferred:** that the E-PM2 shows every row. Duplicate `pos` values suggest that the table is a superset.

**GUI triggers (verified code, unverified input source):**
- `getKeyState`/key → function: 0x7ECD14F9 maps a key to its button info through the {key, info} table 0x7EED0400. Then 0x7ECD3975 reads that info's assigned function value.
- The dispatcher 0x7ECD7A61 (hash table 0x7EED5254, key = id − 21) sends **2336 One Shot Echo** and **2335 Multi Echo** to 0x7ECD908E. That function calls ctrlMovieEffect: 2 for 2336, and 0/1 (start/end toggle) for 2335.
- The recording-state variant 0x7ECD7DCD (`pressCutomKeyRecording` 0x7ECDD76D → 0x7ECD7A34) does the same.
- **2337 Art Fade** goes through the "ModeDirect" substate. 0x7ECDCFB0 matches the direct-mode table 0x7EED7830 {6, 2074, 16, 9, 2254, 85, 296, 384, 271, 451, 2337} and calls ctrlMovieEffect(4) for 2337. The fade end is handled by 0x7ECDD0C3/0x7ECDD307.
- The option-label table 0x7EFF0460… (32-byte rows `{info, value, kind, label}`) pairs 2337 with Fn (info 47, "Art Fade" 1716), 2336 with ▷ (info 53, 1513) and 2335 with ▽ (info 51, 1514).
- **But the mcon value lists for the button infos do not contain them** (verified, `mrec.py`):
  - info 47 (21 values)
  - info 48 (REC button, 23 values)
  - info 51 [2254, 16, 2074, 6, 9, 386, 15130]
  - info 53 [2254, 16, 2074, 6, 9, 386]
  - info 56 (21 values)
- The E-P5 lists (0x7E5488D0…) do not contain them either. So no button can be set to an effect through the menu. The label table is a superset, as section 07 warned for the sub-item table.

**Conclusion:**
- The engine, the API, the menu gate and the GUI handlers are complete (verified).
- The input that produces ids 2335–2337 on the E-PM2 was not found. It is not a button assignment (verified), so it is most likely the on-screen touch icons (inferred).
- External: the E-PL5/E-PM2 manuals describe movie effects started by touching on-screen icons in movie mode.
- Status stays **Active (inferred)**. Its basis changes: before it was string-only; now the gate and handlers are verified, and the input is still not traced.

**Side finding:** the movie digital tele-converter code exists in the app and GUI layers: `OlyHfwOpeShoot::ctrlMovieTelecon` 0x7E982845, the GUI `ctrlMovieTelecon` 0x7ECDE069, and `MV_TELECON_ACTION_STATE_*`. Section 04 §3.2 searched only the mov* range and called it absent. No English "Movie Tele-converter" string exists in any body (verified), so it is probably dormant on this body (inferred). Not traced further.

## 3. "PSP" = background of the 4-window "multi-through" live view

**Code (verified):**
- `mov_func_PSP.c` 0x7E6D75F5–0x7E6D7F01 implements three background types, MOV_PSP_BG_TYPE_JPEG, FILL and black, plus a per-window layout.
- The app side is CapThr_ThroughImage:
  - `setupMultiSetting` 0x7EA1B41B logs `_quadRangleArray[0..3]`, `_isActivePspJpeg`, `_pspJpegResourceId` and `_pspJpegBufferId`;
  - `allocPspJpegBufferHandle` 0x7EA1C6BF;
  - `moveMultiExporse` 0x7EA1CC1A and `moveMultiWB` 0x7EA1CCE8.
- The API `OlyHfwOpeShoot::startMultiThrough` **0x7E988CDB** requires `windowNum == 4` and a quad-rangle array.
- The API types are `MULTI_THROUGH_MAGIC_FILTER = 0, WB = 1, EXPOSE = 2` (0x7E9AA10B), with "MultiWindow BackGround Jpeg" enable/disable (0x7E9AA1AE).
- So it is a 4-window live view. Each window shows a different WB, exposure or (compact-style) Magic Filter, over an optional JPEG background. "PSP" names that background layer; I could not expand the abbreviation (inferred).

**Reachability:**
- `startMultiThrough` has two callers, 0x7E9CB473 and 0x7E9CC4D3. Both are vtable methods of the API controller (vtable 0x7EC0F494, slots +0x2C and +0xD4), and the `sdk api` shell names `setMultiThroughMode`, `startMultiThrough` and `getMultiThroughCursor` (0x7EBF88F8…). So the feature is reachable from the `sdk api` debug shell (verified table; not run).
- GUI-side names exist: EVT_START_PSP = 38697, EVT_END_PSP, GUI_END_PSP = 18, the touch states STATE_TAP_*_MULTI and CBK_MULTI_THROUGH.
- But no code loads 38697 as an immediate. The only hit, 0x7E8738D6, is data decoded as code. I found no GUI call of vtable slot +0xD4 that is clearly this object.
- No English menu label for a multi view exists.
- Status: **Dormant (inferred)**, debug-reachable.

**Cross-body (verified strings in block 0):**

| Body | PSP source names | MULTI_THROUGH types | `Photo_Story` code strings | English "Photo Story" text |
|---|---|---|---|---|
| E-PL5, E-PL6 | yes | MAGIC_FILTER/WB/EXPOSE | none | none |
| E-P5 1.8 | yes | **WB = 0, EXPOSE = 1** (Magic Filter dropped) | `Photo_Story Mode case 1–4`, `PHOTO_STORY_DETAIL_INFO 19`, `create_focus_info case Photo_Story` (0x7E97AC50…) | none |
| E-M10 1.4 | stripped | WB/EXPOSE | `Photo_Story Mode case 1–5`, `ucPhotoStory` | none |
| E-PL7 1.4, E-M5 II 4.1, PEN-F 3.1 | stripped | WB/EXPOSE | yes, `Wizard_Photo_Story_End_Viewer`, GUI_END_PSP | **string 1168** "…during a Photo Story session…" |

- **Reading (inferred):** the E-PM2 multi-window composite is the first form of **Photo Story**. The `PspJpeg` background buffer and GUI_END_PSP survive unchanged into the E-PL7. The PSP name fits "Photo Story P…", but that is unproven.
- The E-PL7 has English Photo Story text. External: the E-PL7 shipped Photo Story, and the E-M10 also had it (its English text may be icon-only).

## 4. `mov` debug shell (0x7E6D15A0, help 0x7E8008B6) — CONFIRMED

- **Help text (verified bytes):** `set QUALITY FPS … QUALITY 1: QVGA 2: VGA 3: HD; FPS 15 / 30 / 60`, `ansh <flag> <x> <y>`, `w - write`.
- **The compare chain (verified, every string operand read):** debug, exec, get, w, ansh, os, dump, dbginfo, img, kdg, effect, mf, gdisp, sdisp, face, through, fps, bit, interval, time, print. **There is no "set"**.
  - `w` (0x7E6D1606) returns at once.
  - `ansh` stores only the flag and prints "shift_x,shift_y:unsupported".
- **Frame rates in code (verified):**
  - MOV writes 2997 (29.97 fps) for every quality (04).
  - The MJPEG frame rate is set by **0x7E6EF13A** → 0x605B1FC2 (the fps used by `bytes_per_s` 0x7E6F08A8). For movie art codes 82 (Pin Hole), 83 (Grainy Film) and 88 (Diorama) it is a constant: 30, 15, 10 or 2 (§6). Otherwise it is **prm 39281** (info 15002, ROM default 0, no mcon record, no constant writer).
  - The time-lapse override 0x7E6ECFD4 can set 1–30 fps (dormant feature, 04 §5.3).
  - No 60 fps value for a record path was found in the functions I read. 59.94p appears only as an AVCHD clip-parser string (04).
- **QVGA:** 320×240 exists only as MJPEG quality 1 in `capture_start` (04). Nothing selects quality 1 (§5).

## 5. Motion JPEG sizes

- **Reachable (verified, §1 table):** GUI 4 = quality 3, format 1 → **1280×720**; GUI 5 = quality 4, format 1 → **640×480**.
- **Not reachable from the GUI (verified):**
  - quality 2 (640×480 by another code);
  - quality 1 (320×240);
  - any other value (160×120).
  - The time-lapse builder `mov_edit_check_param` 0x7E6D493D accepts only quality 3 (04).
  - Only the debug shells could store quality 1/2/other (path as §1, not run).

## 6. Time limit and file size — spot check

- No discrepancy with 04 §1.2 or §1.3 in the H.264 limit chain.
- **Refinement to 04 §1.3 (verified, 0x7E6EF1FB / 0x7E6EF13A):**
  - The "art code 83 multiplies the MJPEG frame budget ×3 (q3) / ×2" rule applies only when the edit mode is off **and not** (prm 26817 == 1 and prm 34129 == 1).
  - It goes together with the reduced frame rate set in 0x7E6EF13A. Under the same condition, code 83 gives 10 fps (q3) or 15 fps, so the ×3/×2 budget keeps the bytes per second about the same (inferred).
  - Code 82 gives 2 fps (q3) or 15 fps. Code 88 always gives 15 fps. When 26817 == 1 and 34129 == 1, codes 82/83 run at 30 fps.
  - prm 26817 = info 444 (Movie Effect); prm 34129 = info 44.
  - **Inferred:** why the Movie Effect setting restores 30 fps, and what info 44 means. The 2 fps value for Pin Hole 720p is odd; see open questions.

## 7. Movie art filters

- **Mapping (verified):** `mov_art` 0x7E6CBFD3 reads **prm 38017 = 0x9481** (Picture Mode) and **prm 49169**. It maps with two jump tables, 0x7E7FF05C (still codes) and 0x7E7FF008 (movie codes; the movie path calls it through 0x7E6CBFC7 with bit 0 set). The movie-code table is:

  100→79, 101→78, 102→80, 103→81, 104→83, 105→82, 106→88, 107→87, 108→93, 109→97, 110→146, 111→125, 112→124, 113→78, 114→121, 115→122, 116→123, 117→152, 118→154, 119→164, 120→183.

  The prm 49169 value is overwritten by the mapping, so variant I/II does not change the movie code (verified in this function).
- **Selection:** movie has no own art list. Picture Mode in movie is the same prm 0x9481. Its only GUI write path is the 19-entry info-111 list (09a; also E-PL5/E-P5), which offers the 12 shipped filters. So the hidden ids 110–118 cannot be chosen for movie either (verified by the absence of any other mcon list holding 100–120, 09a `scan.py`).
- **Movie acceptance:** `art_chk_type_mov` **0x7E71C28B** (called from `art_chk_type` 0x7E71C075) accepts only the shipped still codes 69, 73, 74, 86, 91, 96, 104, 106, 108, 163, 165, 169, 181 and 182 in its processing-type branches. It never accepts 118 (Sparkle), 151 (Reflection) or 153 (Fragmented) (verified, all compares read). An injected hidden id would not get module processing in movie (inferred; ISP-only fallback not traced).
- **Exposed in movie only:** none (verified for the GUI tables above).

## Open questions

1. Which input produces the effect ids 2335/2336/2337 on the E-PM2? I would trace the touch area table of the movie live-view screen (`[GuiTouch] getTouchActionIndex` 0x7EDE0983) into `TouchToCAParam` 0x7ED1BEE2.
2. What info 44 (prm 34129) is. It gates movie effects and, together with Movie Effect, the art frame rate. Is "MJPEG Pin Hole at 2 fps (720p)" real? Check the GUI's movie-mode screen and the meaning of 0x605B1FC2 in `capture_start` 0x7E6F0009.
3. The runtime value of prm 39281 (the MJPEG frame rate when no special art code is set; ROM default 0). It needs the boot settings blob (0x7E457152).
4. A GUI caller of `startMultiThrough` (vtable 0x7EC0F494 +0x2C/+0xD4), and whether EVT_START_PSP has a dispatcher entry. Does the E-P5's Photo Story code have a menu entry?
5. The movie tele-converter: reachability on the E-PM2 (`checkStartMvTelecon` 0x7ECDE68D) and its gating info.
6. For the E-M5 II/PEN-F: decode the extra movie-mode info ids to confirm that AVCHD is absent there too.
