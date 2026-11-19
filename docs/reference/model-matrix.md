# Olympus generations and what each can be modded to do

Written 2026-11-18. Labels: **V** = read in firmware or measured, **X** = stated by another project or source,
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

## 2. What each kind of mod needs, by generation

| Mod | Needs | VI (E-PM2) | VII | VIII | IX / X |
|---|---|---|---|---|---|
| Film simulations from tables (tone, saturation, 6-axis) | Data edits | Done, camera-tested | Done (E-M10) | Done (E-P7) | Done (OM-3) |
| 12-colour HSL per look | A 12-region stage | Stage exists, stills only, not live view (V) | PEN-F: done | E-P7: done | OM-3: done |
| Looks or code loaded from the card | File API plus a hook | Done (this project, fenykl) | Done (em10-fw) | Done | Done |
| Grain, halation, glow (per-pixel CPU work) | CPU time | 1–18 s per still (I). Impossible in movie (V) | ? | Grain 3–5 s per still (X) | Hardware grain, no delay (X) |
| Live ND, silent shutter, Pro Capture | Ending the exposure by sensor readout | Needs a probe: one camera test settles all three (I) | Electronic shutter exists (X) | Stock on some, ported to others | Stock |
| Longer movie limit | Constants, plus file splitting | Small gain only: no file splitting (V) | Patches exist | Patches exist | Patched |
| Log or flat video | A curve | No hidden log curve (V). A log-like curve in an art slot is possible, but 8-bit | ? | Hidden curve exposed (E-P7) | Stock OM-Log |
| 4K, 10-bit, 1/8000 s, 5-axis IS | Hardware | Impossible | Partly | Partly | Yes |
| Wi-Fi, tethering, phone upload | A radio | Impossible (except the E-P5) | Possible | Possible | Tethering done |
| On-device neural network | Spare CPU or ARM cores | Experimental bird detector on the second core (fenykl, E-PL3) | ? | ? | The A53 is the obvious place (I) |

## 3. What this means for the E-PM2

- **Proven on TruePic VI:** looks from data, a card loader, new menu rows, code in segment 2.
- **Possible but unbuilt:**
  - 12-colour data per film, which would show in stills only.
  - Alternative aspect ratios: the codes exist, but every crop table needs new geometry.
  - A log-like movie curve.
  - Slow per-pixel effects on stills.
- **Decided by one camera probe:** whether the sensor can end an exposure by readout. That single test settles
  silent shutter, Live ND and Pro Capture.
- **Hard limits:** live view never gets the 12-region colour stage, movie gets no per-pixel effect, and the
  hardware rows above.
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
