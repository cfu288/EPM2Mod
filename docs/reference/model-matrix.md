# Olympus generations and what each can be modded to do

Written 2026-11-18, updated 2026-11-27. Labels: **V** = read in firmware, measured or in a maker manual, **X** = stated by another project or source,
**I** = inferred, **?** = unknown.

Sources:
- `emulator/om-emu/docs/model-survey.md`: 32 firmware files from OM's update server, E100 to E148.
- `emulator/om-emu/docs/a53-spec.md`: the second processors.
- `experiments/2026-11-15-feature-survey/mods-and-web.md`: other mods, sweep of 2026-11-15.
- `experiments/2026-11-11-caduceus-review/05-imaging-pipeline-and-limits.md`: limits of the E-PM2 pipeline.

The hardware rows (video, shutter, Wi-Fi) come from manuals and reviews, not from the firmware.

All 32 surveyed files (2012 to 2025) use one container format and one main CPU family, Panasonic MN103/AM33 (V).
The differences that matter for mods are in the columns below.

## 1. The generations

| Generation (years) | Bodies (firmware code) | Firmware size and layout | Processors | Imaging pipeline | Video and sensor | Mods that exist |
|---|---|---|---|---|---|---|
| **TruePic VI** (2011–13) | E-PL5 (E100), **E-PM2 (E101)**, E-PL6 (E112), E-P5 (E108), STYLUS 1 (E111), TG-2 (E106). E-P3, E-PL3, E-PM1 and E-M5 are not in the survey | 13.5–15 MiB main block. Load address differs per body (E-PM2 0x7E421020). Not compressed. No OSD graphics engine (V) | Two MN103 cores (V on E-PM2: the log has CPU 0 and CPU 1). Clock 162 or 324 MHz (I). No network processor | Tone curves, saturation, 6-axis colour. A 12-region colour stage that only stills use, not live view (V). No 3D LUT (V). Effects only through the art-filter chain. E-P5 has Color Creator in its menus (X) | 1080 30p, H.264 at 20 Mb/s, no file splitting (V). Mechanical shutter only. No Wi-Fi, except the E-P5 (X) | This project (E-PM2). fenykl: card loader, peaking, on-screen data (E-PL3). An AF patch on the E-P5 |
| **TruePic VII** (2013–16) | E-M1 (E109), E-M10 (E113), E-PL7 (E115), E-PL8 (E126), TG-4 (E121), A01 (E117). **E-M5 II (E118), E-M10 II (E120), PEN-F (E122)** | 17–20.4 MiB. The three in bold share the OM-1's load address, 0x60021020: the first bodies whose code resembles today's (V). OSD engine present | MN103. The PEN-F runs everything on the MN, networking included (X) | PEN-F: Color and Mono Profiles with a 12-colour editor (X) | 1080 60p (the E-M5 II adds 77 Mb/s intra-frame) (X). Electronic shutter on the later bodies (X). Wi-Fi (X) | PEN-F 12-colour HSL (fishcu). E-M10 plugin loader (em10-fw). E-M10 looks with HSL (om10mi-mods). Movie-limit patches (ABel) |
| **TruePic VIII** (2016–21) | E-M1 II (E125), E-M1X (E134), E-M10 III (E130), E-M10 IV (E140), E-PL9 (E133), E-M5 III (E137), E-P7 (E142), TG-5 (E129) | 22–26 MiB. Load address 0x60021020, 0x60020020 or 0x60400020 (V) | MN103 plus a Cortex-A9 for networking (ITRON on the E-M1 II and E-M10 III, Linux on the rest) (X) | E-P7: colour profile engine, with a hidden log curve that a mod exposed (X). Pro Capture and focus stacking on the E-M1 II and E-M1X (X) | 4K 30p (X). Fast electronic readout (X) | Caduceus E-P7, the most complete look mod. Live ND port and focus stacking on the E-M5 III. db firmware. Movie limit |
| **TruePic IX** (2020–25) | E-M1 III (E139), OM-5 (E144), OM-5 II (E148), TG-7 (E145) | 19.5–26 MiB. The E-M1 III and OM-5 store compressed code sections (V), which makes patching harder (I) | MN103 plus a Cortex-A9 running Linux (X) | Live ND, handheld high-res, OM-Log (X) | 4K, OM-Log (X) | caduceus-om5: emulator only, and its builds put the camera in a restart loop three times. db firmware |
| **TruePic X** (2022–25) | OM-1 (E143), OM-1 II (E146), OM-3 (E147) | 32 MiB. Resources compressed. New hardware register map (V) | MN103 plus a Cortex-A53 running Linux 4.14: Wi-Fi and the handheld high-res maths, with NEON (X) | Color and Mono Profiles with Color Creator. Hardware grain that a mod can reuse (X) | Stacked sensor, 4K 60p 10-bit, OM-Log400 (X) | Caduceus OM-3 (loads a code block from the card). USB tethering. Games. db firmware |

## 2. Features by generation

What each feature needs, and for each generation whether the stock firmware has it, a mod adds it, or what stops it.
Stock values for the E-PL3, E-PM2, E-M10, E-M5 II, E-M10 II, PEN-F, E-M1 II, E-M10 III, E-PL9, E-M1X, E-M5 III, E-P7,
E-M1 III, OM-5, OM-5 II, OM-1, OM-1 II and OM-3 come from a survey of their manuals and reviews of 2026-11-27. The
E-M5 is counted as TruePic VI (I).

**Key.** **Stock** (on: the bodies, if only some) · **Mod:** project (body) · **Not done:** the parts are present
and no mod has it; what a port needs · **Not possible:** a part is missing, with the evidence · **Unknown:** no
source settles it; the smallest test. Where the bodies of a generation differ, a cell gives a second value for the
other bodies. Each value ends with its label (V, X or I).

| Feature | Needs | VI | VII | VIII | IX | X |
|---|---|---|---|---|---|---|
| Film simulations | Data edits to tone, saturation and colour tables; a menu entry that holds them | **Mod:** EPM2Mod (E-PM2), in the ART entries (V) | **Mod:** [om10mi-mods][om10mi], [em10-fw][em10fw] (E-M10) (X) | **Mod:** [Caduceus][cad-ep7] (E-P7) (X). [epl9-lab][epl9]: not camera-tested (X) | **Mod:** [Caduceus OM-5 II][cad-om5], [OMKit][omkit] (OM-5 II) (X) | **Mod:** [Caduceus OM-3][cad-om3], [Nostalgia-OM][nostalgia] (OM-3); [db firmware][db] Quasi LUT (OM-1, OM-1 II, OM-3) (X) |
| 12-colour editing in photos | A 12-region hue, saturation and lightness stage; data for it or an editor | **Not done:** needs per-film 12-region data or an editor; the stage is camera-tested with test tables ([feasibility](../dev/feasibility.md)) (V) | **Stock on:** PEN-F, saturation only (V). **Mod:** [PEN-F HSL][penf] (PEN-F), [om10mi-mods][om10mi] (E-M10) (X) | **Stock on:** E-P7, saturation only (V). **Mod:** [Caduceus][cad-ep7] adds hue and lightness (E-P7) (X) | **Mod:** [Caduceus OM-5 II][cad-om5]; [OMKit][omkit] saturation (OM-5 II). No stock Color Profile on the OM-5 II ([Caduceus OM-5 II][cad-om5]) (X) | **Stock on:** OM-3 (X, [BODIES][bodies]). **Mod:** [Caduceus OM-3][cad-om3]; [db firmware][db] Quasi LUT (OM-1, OM-1 II, OM-3) (X) |
| 12-colour editing in live view and movie | The 12-region stage in the live-view and movie pipe | **Not possible:** missing the stage in live view and movie; it runs in the stills pipe only (stage 0x7E76C3C8, pipe A) ([feasibility](../dev/feasibility.md)) (V) | **Stock on:** PEN-F (V). **Mod:** [om10mi-mods][om10mi], live view and JPEG (E-M10) (X) | **Stock on:** E-P7 (V). **Mod:** [Caduceus][cad-ep7] hue and lightness in live view, its own movie profile (E-P7) (X) | **Mod:** [OMKit][omkit], stills, live view and video from the still modes (OM-5 II) (X) | **Stock on:** OM-3 (X). **Mod:** [Caduceus OM-3][cad-om3], live view (OM-3) (X) |
| Looks or code loaded from the card | File routines, a hook at a safe moment, free code space | **Mod:** EPM2Mod look pack (E-PM2) (V); [fenykl][fenykl-epl3] code loader (E-PL3, frozen branch) (X) | **Mod:** [fenykl][fenykl] code loader (E-M10 II); [em10-fw][em10fw] plugins (E-M10) (X) | **Mod:** [Caduceus][cad-ep7] looks (E-P7); [emudojo][em1ii] looks, no release (E-M1 II) (X) | **Mod:** [OMKit][omkit] code modules and presets; [Caduceus OM-5 II][cad-om5] looks (OM-5 II) (X) | **Mod:** [Caduceus OM-3][cad-om3] looks and a code block (OM-3); [db firmware][db] 8 LUT slots (OM-1, OM-1 II, OM-3) (X) |
| Focus peaking | CPU access to the live-view buffer, an overlay, CPU time per frame | **Stock on:** E-P5 ([feasibility](../dev/feasibility.md)) (X). **Mod:** EPM2Mod (E-PM2) (V); [fenykl][fenykl-epl3] (E-PL3) (X) | **Stock** (V) | **Stock** (V) | **Stock** (V) | **Stock** (V) |
| Live ND | A continuous series of electronically read frames, an averaging buffer, RAM | **Unknown:** whether the sensor ends an exposure by read-out. Test: two RAW pictures of a plain wall, Live Time 0.5 s against a normal 0.5 s ([anti-shock notes][antishock]) (I) | **Not done:** needs averaging of an electronic-shutter frame series; electronic shutter is stock on the E-M5 II, E-M10 II and PEN-F (I) | **Stock on:** E-M1X (V). **Mod:** [Caduceus][cad-ep7] ND3, ND4 by Multiple Exposure, one press per frame (E-P7); [olympus-firmware-notes][em5iii] ND2–ND16, end of capture hangs (E-M5 III) (X) | **Stock** (V). **Mod:** [Caduceus OM-5 II][cad-om5] ND32, ND64 (OM-5 II) (X) | **Stock** (V) |
| Silent (electronic) shutter | The sensor starts and ends the exposure by read-out | **Unknown:** the same wall test as Live ND. The read-out takes 24.3 ms, so a strong rolling effect (V, [modern features][modern]) | **Stock on:** E-M5 II, E-M10 II, PEN-F (V). E-M10: **Not done** (I) | **Stock** (V). **Mod:** [db firmware][db] Hybrid shutter, mechanical to 1/8000 s then electronic (E-M1X, E-P7) (X) | **Stock** (V). **Mod:** [db firmware][db] Hybrid shutter (E-M1 III, OM-5, OM-5 II) (X) | **Stock** (V). **Mod:** [db firmware][db] Hybrid shutter, shutter sounds (OM-1, OM-1 II, OM-3) (X) |
| Pro Capture | An electronic-shutter burst, a ring buffer in RAM, a half-press hook | **Unknown:** the same wall test as Live ND (I) | **Mod:** [fenykl][fenykl] pre-capture, 6 frames (E-M10 II) (X). Others: **Not done:** needs a ring buffer of electronic frames (I) | **Stock on:** E-M1 II, E-M1X, E-M5 III (V). Others: **Not done** (I) | **Stock** (V) | **Stock** (V). **Mod:** [db firmware][db] extra SH2 rates (OM-1) (X) |
| High Res Shot | A sensor-shift unit that holds sub-pixel offsets, electronic shutter, merge code | **Unknown:** the IS is 2-axis (V, manual). Test: command a static IS offset through the H8 stabiliser controller and measure the shift on a tripod target ([modern features][modern]) (I) | **Stock on:** E-M5 II, PEN-F (V) | **Stock on:** E-M1 II, E-M1X (handheld too), E-M5 III (I) | **Stock** (V). **Mod:** [E-M1 III Mod Builder][em1iii] handheld with manual and fill flash (E-M1 III) (X) | **Stock** (V) |
| Longer movie limit | Timer constants; file splitting past 4 GiB | **Not done:** patches for 7200 s and higher bit rates written, not flashed. One file only, at most 4 GiB (FAT32) ([hardware][hw]) (V) | **Mod:** [om10mi-mods][om10mi] 59:50 (E-M10); patches of the mu-43 thread (PEN-F, E-M5 II) ([analysis][hacks]) (X) | **Mod:** [Caduceus][cad-ep7] 9 h (E-P7); [em1x-mod][em1x] (E-M1X); mu-43 patch (E-M1 II) ([analysis][hacks]) (X) | **Mod:** [E-M1 III Mod Builder][em1iii] (E-M1 III) (X) | **Stock:** 3 h per file on SDXC, then more files ([OM-1 II manual][om1ii-movie]) (V) |
| Log or flat movie profile | A tone curve that the movie pipe applies | **Not done:** no hidden log curve (V); film simulations apply in movie (V, `stock-films`), so a flat curve in an ART entry is a data edit, in 8-bit H.264 (I) | **Mod:** [em10-fw][em10fw] FLAT (E-M10) (X) | **Stock on:** E-M1 II (fw 3.0), E-M1X (V). **Mod:** [Caduceus][cad-ep7] hidden 8-bit log curve (E-P7) (X) | **Stock** OM-Log400 (V) | **Stock** OM-Log400 (V) |
| 10-bit movie | 10-bit read-out path, a 10-bit encoder (H.265 or H.264 High 10), card speed | **Unknown:** the stream is 8-bit H.264 High at Level 4.1; the encoder's ceiling is not known ([hardware][hw]) (V). Test: search the encoder set-up for a bit-depth or High 10 field (I) | **Unknown:** no body records 10-bit (V). Same firmware search (I) | **Unknown:** as VII | **Unknown:** as VII | **Stock:** 10-bit H.265 (V) |
| Per-pixel effects (grain, halation, glow) | CPU time per photo, or a hardware stage; a hook after development | **Not done:** the Grainy Film art filter is stock (V); its grain on a film simulation is about 40 bytes (I); CPU grain about 1.5–4.5 s and halation 1–2.5 s per photo ([Caduceus review 05][cad05]) (I) | **Stock on:** PEN-F, grain in Monochrome Profiles ([modern features][modern]) (V). **Mod:** [em10-fw][em10fw] film looks with grain, 3–16 s per photo (E-M10) (X) | **Mod:** [Caduceus][cad-ep7] grain, a few seconds per photo; halation, 1–2 s (E-P7) (X) | **Mod:** [OMKit][omkit] grain, bloom, halation on stills (OM-5 II) (X) | **Stock on:** OM-3, hardware grain in mono, no delay (X). **Mod:** [Caduceus OM-3][cad-om3]; [db firmware][db] colour grain (OM-1, OM-1 II, OM-3) (X) |
| Wi-Fi features | A radio; a network processor on VIII and later | **Stock on:** E-P5 (X). Others: **Not possible:** missing a radio (V, E-PM2 manual); FlashAir card transfer works (V) | **Stock** (V) | **Stock** (V). **Mod:** [db firmware][db] 5 GHz (E-M1X) (X) | **Stock** (V). **Mod:** [db firmware][db] 5 GHz (E-M1 III, OM-5) (X) | **Stock** (V). **Mod:** [db firmware][db] 5 GHz (OM-1, OM-1 II), phone LUT editing (X) |
| Tethered shooting | USB with PTP capture handlers | **Not done:** USB 2.0 device present; PTP has no capture handler ([mods and web][survey]) (V) | **Stock on:** E-M1 (fw 2.0), E-M5 II ([OM Capture][omcapture]) (X) | **Stock on:** E-M1 II, E-M1X ([OM Capture][omcapture]) (X) | **Stock on:** E-M1 III ([OM Capture][omcapture]) (X) | **Stock on:** OM-1, OM-1 II ([OM Capture][omcapture]) (X). **Mod:** V22 patch, USB live view (OM-3) ([analysis][tether]) (X) |
| Star tracking | An IBIS that can be steered, roll included; a gyro; the sky's position (plate solving) | **Unknown:** the 2-axis IS has no roll axis (V, manual). Test: the static IS offset of High Res Shot (I) | **Not done:** needs a port of the tracking code; 5-axis IS on the E-M5 II, E-M10 II, PEN-F (I) | **Not done:** as VII; the A9 network processor runs Linux except on the E-M1 II and E-M10 III (I) | **Not done:** as VIII (I) | **Mod:** [OM Startrack][startrack] (OM-1, OM-1 II), uses the A53 Linux, Bluetooth and a phone plate solver (X) |
| Aperture ring of Panasonic lenses ([issue #3][i3]) | Parse the lens's ring report; feed it to exposure in A and M | **Mod:** [db firmware][db] (E-PL5, E-PL6, E-P5) (X). E-PM2: **Unknown:** the probe of 2026-11-22 did not show the ring ([notes][pana]) (V). Test: the same probe with an aperture-ring lens on this body | **Mod:** [db firmware][db] (E-M1, E-M10, E-M10 II, E-M5 II, PEN-F, E-PL7, E-PL8) (X) | **Mod:** [db firmware][db] (all VIII bodies) (X) | **Mod:** [db firmware][db] (E-M1 III, OM-5, OM-5 II) (X) | **Mod:** [db firmware][db] (OM-1, OM-1 II, OM-3) (X) |
| Image stabiliser switched off at start ([issue #7][i7]) | The start-up value that tells the firmware a stabiliser is fitted | **Mod:** a 3-byte patch, tested by the issue's reporter (E-PM2) (X); EPM2Mod build `no-ibis` not yet camera-tested (V) | **Not done:** needs the same start-up value found in each body (I) | **Not done:** as VII (I) | **Not done:** as VII (I) | **Not done:** as VII (I) |
| Extra aspect ratios (XPan 65:24, 21:9) | Crop tables for sensor, live view and playback | **Not done:** the aspect codes exist; every crop table needs new geometry (I) | **Not done:** no project (I) | **Mod:** [Caduceus][cad-ep7] (E-P7); [emudojo][em1ii], no release (E-M1 II) (X) | **Mod:** [E-M1 III Mod Builder][em1iii] XPan (E-M1 III) (X) | **Mod:** [Caduceus OM-3][cad-om3] XPan, 21:9, 5:4 (OM-3) (X) |
| In-camera focus stacking with any lens | The stock stacker and its lens list, or focus bracketing plus a merge | **Not done:** needs focus bracketing and a merge; neither is in the stock firmware ([feasibility](../dev/feasibility.md)) (V) | **Stock on:** E-M1 (fw 4.0) (X, [mods and web][survey]); Olympus lenses only. **Mod:** mu-43 patch (E-M5 II) ([analysis][hacks]) (X) | **Stock on:** E-M1 II, E-M1X (I). **Mod:** mu-43 patch and [emudojo][em1ii] (E-M1 II); [em1x-mod][em1x], untested (E-M1X); [olympus-firmware-notes][em5iii] (E-M5 III) (X) | **Mod:** [E-M1 III Mod Builder][em1iii] (E-M1 III) (X) | **Not done:** stock on Olympus lenses only; needs the lens-list branch removed, as on VIII (I) |
| Infrared red/blue swap | The hardware 3×3 colour matrix | **Mod:** [db firmware][db] (E-PL5, E-PL6, E-P5, E-M5); [fenykl][fenykl-epl3] (E-PL3) (X) | **Mod:** [db firmware][db] (all VII bodies it lists); [fenykl][fenykl] (E-M10 II) (X) | **Mod:** [db firmware][db] (all VIII bodies) (X) | **Mod:** [db firmware][db] (E-M1 III, OM-5, OM-5 II) (X) | **Not done:** [db firmware][db] leaves out TruePic X; needs the colour matrix found (I) |
| Lowest shutter speed for Auto ISO | Exposure code and a menu row | **Mod:** EPM2Mod (E-PM2) (V); [db firmware][db] (E-M5) (X) | **Stock on:** PEN-F (fw 2.0) ([feasibility](../dev/feasibility.md)) (V). **Mod:** [db firmware][db] (E-M10, E-M10 II, E-M5 II) (X) | **Mod:** [db firmware][db] (E-M10 III, E-M10 IV, E-P7); [Caduceus][cad-ep7] (E-P7) (X) | **Unknown:** test: the ISO-Auto settings page of the E-M1 III and OM-5 manuals | **Unknown:** as IX, OM-1 manual |
| Subject detection (neural network) | CPU time per live-view frame on a spare core or processor; an AF hook | **Mod:** [fenykl][fenykl] bird detector on the second MN103 core, experimental (E-PL3) (X) | **Unknown:** no project; CPU time per frame not measured | **Stock on:** E-M1X ([PetaPixel][em1x-bird]) (X) | **Unknown:** no stock body (X, [PetaPixel][em1x-bird] for the E-M1 III); time per frame on the A9 not measured | **Stock** (V) |

[antishock]: ../../experiments/2026-11-17-anti-shock/NOTES.md
[modern]: ../../experiments/2026-11-19-modern-features/NOTES.md
[survey]: ../../experiments/2026-11-15-feature-survey/mods-and-web.md
[hw]: ../../experiments/2026-11-14-feasibility/hardware.md
[cad05]: ../../experiments/2026-11-11-caduceus-review/05-imaging-pipeline-and-limits.md
[pana]: ../../experiments/2026-11-22-pana-aperture-ring/NOTES.md
[i3]: https://github.com/cfu288/EPM2Mod/issues/3
[i7]: https://github.com/cfu288/EPM2Mod/issues/7
[db]: https://github.com/azqeurio/om-c-firmware
[fenykl]: https://github.com/atx/fenykl
[fenykl-epl3]: https://github.com/atx/fenykl/commit/02e0f1ecc8
[em10fw]: https://github.com/cmdada/em10-fw
[om10mi]: https://github.com/Meghnus/om10mi-mods
[penf]: https://github.com/fishcu/oly_fw_analysis
[hacks]: https://github.com/fishcu/oly_fw_analysis/blob/main/docs/features/HISTORICAL_HACKS.md
[tether]: https://github.com/fishcu/oly_fw_analysis/blob/main/docs/protocols/om-3/TETHERING.md
[cad-ep7]: https://github.com/cakelesscoder/caduceus-ep7
[bodies]: https://github.com/cakelesscoder/caduceus-ep7/blob/main/docs/BODIES.md
[em1ii]: https://github.com/emudojo/caduceus/tree/omdem12-implement-colors-more
[epl9]: https://github.com/RemeraLl1/epl9-lab
[em1x]: https://github.com/bk2gf59w5d-ui/em1x-mod
[em5iii]: https://github.com/nsud-dev/olympus-firmware-notes
[em1iii]: https://github.com/dfeldt91-blip/E-M1-Miii
[cad-om5]: https://github.com/xulfr/caduceus-om5
[omkit]: https://github.com/necrostaz/omkit
[cad-om3]: https://github.com/androidfanman/caduceus-om3
[nostalgia]: https://github.com/SengokuCola/Nostalgia-OM
[startrack]: https://github.com/kingoflolz/om-startrack
[omcapture]: https://software.omsystem.com/omcapture/
[om1ii-movie]: https://learning.omsystem.com/OM-1MarkII/zz_html_manual/en/memory_card_capacity_movies_332.html
[em1x-bird]: https://petapixel.com/2020/11/17/olympus-adds-bird-detection-af-and-raw-video-support-to-e-m1x

## 3. What this means for the E-PM2

- **Proven on TruePic VI:** looks from data, a card loader, new menu rows, code in segment 2.
- **Possible but unbuilt:**
  - 12-colour data per film, which would show in stills only.
  - Alternative aspect ratios: the codes exist, but every crop table needs new geometry.
  - A log-like movie curve.
  - Slow per-pixel effects on stills.
- **Decided by one camera probe:** whether the sensor can end an exposure by readout. That single test settles
  silent shutter, Live ND and Pro Capture.
- **Hard limits:** live view never gets the 12-region colour stage, movie gets no per-pixel effect, and there is
  no Wi-Fi (no radio; section 2).
- **Best sources of code to port:** the E-PL6 and E-P5 share the sensor and TruePic VI. Of what the E-PL6 has,
  interval shooting and the level gauge are already rebuilt here. The E-P5 has peaking on a button. Focus peaking
  is already rebuilt here.

## 4. Gaps

- **Free code space and settings memory per body:** measured only for the E-PM2 (code space:
  [code-space-map.md §4](code-space-map.md#4-totals-bytes); a 53,680-byte unused tail in the settings memory, see [feasibility.md](../dev/feasibility.md)). The same
  free-space scan could run on all 32 firmware files.
- **RAM per body:** unknown. The 512 MiB for the E-PM2 is the emulator's setting, not a measurement.
- **CPU clock:** inferred, not measured. A timing probe on the camera would settle it.
- **Hardware rows (video, shutter, Wi-Fi):** from manuals and reviews, not checked in the firmware.
