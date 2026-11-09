# Audit batch 2: claims to check

## 03-81  (from sections/03-camera-core-rec-art.md, line 81)

| cam_damage.c | 0x7E62EA55, 0x7E62EAF3 | §5 (verified) |

## 03-82  (from sections/03-camera-core-rec-art.md, line 82)

| `cam` debug shell | 0x7E62EB8E, table 0x7E7AC414 | §6 (verified) |

## 03-92  (from sections/03-camera-core-rec-art.md, line 92)

| cam_still_func.c | 0x7E656B1D–0x7E656F6F | §4 (verified tables) |

## 03-98  (from sections/03-camera-core-rec-art.md, line 98)

- **Still-func command filter (verified, 0x7E656D64):** it takes only cmd 7 (COM_SET) and cmd 80 (COM_MOVIE_EXPOSE). Anything else gives "STL_FUNC_COM NOT SUPPORT". **Live bulb (verified, 0x7E65DA2B)** takes only COM_SET.

## 03-103  (from sections/03-camera-core-rec-art.md, line 103)

- `cam still` test help (0x7E62F370, verified strings): Mode 7 = Zengaso. Depth 8/9/10/12/14/16 bit. Option1 bits: dark, pack up, pack down, antishock. Option2 bits: continue, fpn, bulb_manual, bulb_auto, abort_ready, abort_take. Matching sequences: "Still Normal" 0x7E62F6EB, "Still Continue" 0x7E62FC0C, "High (speed)" 0x7E630201, "Bulb" 0x7E6307C0, "LB" 0x7E630C25 (LB turns AWB off: "AWB OFF!!!!!").

## 03-281  (from sections/03-camera-core-rec-art.md, line 281)

- **Verified:** the frame effect decodes JPEG frame resources (`art_frame_*` 0x7E721294…, `ART_FRAME_MOVIE_SD/HD/FHD`).

## 04-71  (from sections/04-movie.md, line 71)

- **Display.** `api_movie_CalculateQualityTime_Record_Movie` 0x7E681D87 returns (40) × 600 / fps(30,ctx). `api_movie_Get_Time_Record_Movie` 0x7E681DC7 returns elapsed (552,ctx). `0x7E6EDF9D` adds 600 to (552) each second and posts `RECMOVIE_UPDATE` 0x04070100. **Verified.**

## 04-105  (from sections/04-movie.md, line 105)

| MOVART_TASK | 0x7E6CBEBC | img_exec + `mov_kdg_exec` (movie effects). **Verified** |

## 04-133  (from sections/04-movie.md, line 133)

- QT user data (0x7E6D5F55) writes an `OLYM` atom with `prms` (ArtFilterMode, ExposureMode, PictureMode, Scene, WB shift, iAuto). A `thmb` thumbnail and a `scrn` screennail come from 0x7E6D6438 (JPEG encode of a frame). **Verified** 4CC constants and strings.

## 04-139  (from sections/04-movie.md, line 139)

- States: idle/aud_wait/first_frame 0x7E6EF3D6, record_normal 0x7E6EF5E7, userstop (+ `_for_edit`) 0x7E6EF7F7, finish_1 0x7E6EF958, errorstop/fullstop. **Verified** strings and state pointers.

## 04-152  (from sections/04-movie.md, line 152)

- `mov_image_process` 0x7E6C6853 prints "Effect OFF", "toyphoto ON for 1st", "filter ON for 1st" and "simple & Frame ON for 1st". These are the art *effects* (Pin Hole/Toy, filter, Frame) applied to the first frame. **Verified** strings.

## 04-224  (from sections/04-movie.md, line 224)

- **Task names vs content.** The entry named MOV_PLAY_AVF (0x7E6E324B) prints `[MOV_PLAY_AVCHD_FILE]`, and MOV_PLAY_AVI (0x7E6E38AC) prints `[MOV_PLAY_AVCHD_IMG]`. These names still hold in the corrected tasks.tsv, so they look like internal abbreviations: AVF = AVCHD file reader, AVI = AVCHD image/decode. That reading is **inferred**; the strings are **verified**.

