# Feature survey: other mods, other brands, newer Olympus bodies

Date: 2026-11-15. Question from the owner: "what other oly camera features exist in other firmware mods or other
newer models stock firmware that dont exist here?" This file is the web, manual and GitHub part. The firmware
comparison is in `firmware-diff.md` in this folder.

No code and no build came out of this work. Nothing here was run on a camera.

**Labels.** *verified* = seen in a cited page, manual or repo file. *inferred* = reasoned from cited facts.
*unknown* = no evidence; the smallest probe is named. "from memory, not verified" and "(fm)" mark statements with no
source. `hardware.md` means `experiments/2026-11-14-feasibility/hardware.md`.

**Contents**

- (a) Olympus / OM System mods and what they add
- (b) Ideas from other brands' mods, mapped to E-PM2 building blocks
- (c) Features of newer Olympus / OM System bodies
- (d) Community wish list
- (e) Top 15 worth trying on the E-PM2
- Not verified
- Link keys

**Three findings that change earlier notes**

1. **The E-PM2 manual already lists a small single AF target** (p.35: "Single Target (Standard size, small size)").
   `hardware.md` §7 and `docs/feasibility.md` list "small AF target" as an E-PL6 addition to port. Check on the
   camera (AF target screen → INFO → up/down) before any port work. The E-PL6 item may be a different, smaller size.
2. **A mod already runs on a TruePic VI body.** [atx/fenykl](https://github.com/atx/fenykl) on the E-PL3 loads code
   from the card and draws battery %, focus distance, depth of field and peaking. The earlier review knew it only as
   "a code loader".
3. **A new E-M10 I mod** ([Meghnus/om10mi-mods](https://github.com/Meghnus/om10mi-mods)) ships a 12-sector
   hue/saturation/lightness editor and looks in RAW Data Edit on a TruePic VII body with no Color Profile Control. It
   is the closest published relative of this project's film looks.

## (a) Olympus / OM System mods and what they add

Found by reading the checkouts and by a direct GitHub sweep on 2026-11-15 (`gh search repos`, 35 word sets; `gh search
code`, 8 word sets). State labels: **camera** = the project reports it on a real body; **emulator** = only run in an
emulator; **research** = notes only. I did not run any of them.

### Released or camera-tested

| Project | Body (processor) | Features it adds | State |
|---|---|---|---|
| [cakelesscoder/caduceus-ep7](https://github.com/cakelesscoder/caduceus-ep7) | E-P7 (TruePic VIII) | 29 film looks from a card file; on-camera look editor on the Color Profile wheel (hue, saturation, light for 12 colours); tone per look with Blacks and Whites; bloom and clarity; WB shift per look; Art Effects (Star Light, Pin Hole) on a colour profile; colour film grain (CPU pass, 3 to 5 s per photo); tinted halation; sharpening off, noise filter and lens-shading correction per profile; mono film presets; **"true log video"** (a log curve that was hidden in the firmware); **XPan 65:24 and 21:9** stills with matching live view; own colour for Movie and AP modes; a **Live ND** made from stock Multiple Exposure; **Lowest S/S** (minimum shutter speed for auto ISO); vertical video; **more button functions** and arrow-key remaps; **LCD colour fix** (green-magenta slider for the rear screen); look name in EXIF; record limit 29 min → 9 h | camera (most rows); some rows "new, please report" |
| [androidfanman/caduceus-om3](https://github.com/androidfanman/caduceus-om3) | OM-3 (TruePic X) | FILM 1–20 in the Picture Mode list; hue and luminance for 12 colours; split toning (shadows, highlights); Blacks/Whites; WB grid per film; sharpness, noise filter, vignette correction, shading rows; glow/clarity; **fast colour grain** (reuses the Grainy Film texture, no delay); halation; edits kept in camera memory and on the card; button and Creative Dial remaps; EXIF recipe; debug log to the card | camera |
| [WaltNara/om3-minigame](https://github.com/WaltNara/om3-minigame) | OM-3, on top of Caduceus | Four games in Picture Mode → Games: 2048, Minesweeper, a runner, Breakout | emulator; release r2 "passed a user on-camera check" |
| [fishcu/oly_fw_analysis](https://github.com/fishcu/oly_fw_analysis) | PEN-F (TruePic VII) | The first 12-colour HSL patch (hue and luminance added to the stock Color Profile); ready-to-install packages of 13 and 17 Oct 2026. Also documents the patches below | camera (PEN-F HSL); the rest is analysis |
| [azqeurio/om-c-firmware](https://github.com/azqeurio/om-c-firmware) ("db firmware", closed binary tool, v0.4.0 of 11 Nov 2026) | OM-1, OM-1 II, OM-3, OM-5, OM-5 II, E-P7, E-M1 II, E-M1X, PEN-F and others | Korean menu language with font choice; **Panasonic lens aperture ring works** on Olympus bodies; E-P7: minimum shutter speed, AF Home, D-pad and button remaps; OM-1: 12.5 and 16.7 fps added to SH2 / Pro Capture SH2; **shutter sound from the speaker with the electronic shutter**; 5 GHz camera hotspot; E-M1X ISO limit raised to 25600; **OM-1 gets the OM-1 II feature set** (all but ND128 and the larger buffer) | camera on the author's OM-1, OM-5 II and a PEN; other bodies by user reports ([status page](https://db-firmware-support.vercel.app/overview)). Two E-P5 1.8 reports failed (see the earlier Caduceus review in this repo) |
| ABel's patches, [mu-43 thread "Modified firmware looking for users"](https://www.mu-43.com/threads/modified-firmware-looking-for-users.99804/) (2018–2019); files mirrored at [xdel.ru](http://xdel.ru/downloads/olympus-firmware/); byte-level analysis in [fishcu HISTORICAL_HACKS.md](https://github.com/fishcu/oly_fw_analysis/blob/main/docs/features/HISTORICAL_HACKS.md) | E-M1, E-M1 II, E-M1 III, E-M5 II, E-M5 III, E-M10 II, E-M10 III, E-PL9, PEN-F | **Movie time limit removed** (29 min → as many 4 GB parts as the body allows); **in-camera focus stacking with any AF lens** (the lens allow-list branch removed). 4 to 14 changed bytes per body | camera (thread reports); on the E-M1 the time-limit part "does not work" |
| kred's V22 patch, [mu-43 post](https://www.mu-43.com/threads/modified-firmware-looking-for-users.99804/page-34#post-1886195), analysed in [fishcu TETHERING.md](https://github.com/fishcu/oly_fw_analysis/blob/main/docs/protocols/om-3/TETHERING.md) | OM-3 | **USB tethering**: live view and image transfer to OM Capture, ported from the OM-1 II (3,555 changed bytes) | camera (author's report) |
| [nsud-dev/olympus-firmware-notes](https://github.com/nsud-dev/olympus-firmware-notes) | E-M5 III (TruePic VIII) | **Focus stacking with any lens** (camera); **Live ND** ND2–ND16 ported from the OM-5 (merged photos work, the clean end of capture still hangs); **USB webcam** (the camera enumerates and streams, live view not yet); handheld high-res, Starry Sky AF, PEN-F profiles, OM-Log400, 29:59 limit: built or traced, not finished. Its [ideas page](https://github.com/nsud-dev/olympus-firmware-notes/blob/main/docs/features/ideas.md) lists tripod multi-frame NR, 9-frame AE bracket, focus-stack count, exposure ramp for time-lapse, raw zebras and histogram, trap focus, motion trigger | mixed: see each item |
| [atx/fenykl](https://github.com/atx/fenykl) | **E-PL3 (TruePic VI, the E-PM2's generation)**; E-M10 II in work | A loader that runs `FENYKL.BIN` from the card (no reflash per change). Its main plugin: **battery percentage, focus distance, depth of field, focus meter** on the INFO screen, **screenshot on Fn**, **red/blue channel swap** (for infrared), **focus peaking** (red edges, Off/Low/Medium/High), a settings page in the Custom Menu with settings saved to the card, a log file. E-M10 II: **pre-capture**. A **bird detector** (a small neural network on the second CPU core that steers the face frame) | "early stage experimental"; E-PL3 is the supported body |
| [cmdada/em10-fw](https://github.com/cmdada/em10-fw) | E-M10 I (TruePic VII, the same 16 MP sensor family) | A plugin loader (`C:\PLUGINS\*.EMP`) with a "Homebrew" page in Setup. Plugins: **partial colour** (keep one colour), **raw monochrome** (no demosaic), **film looks with grain and split toning**, **hardware colour key** (works in live view), flat colour for video, **focus bracketing** (runs, the lens does not move), system dump, an **Immich uploader** over Wi-Fi (not working on the camera). Also: GUI theme, fonts and icons; menu background; extra Picture Mode entries; replacement Wi-Fi web pages; movie limit; a FreeRTOS port (emulator only); `em10emu` | camera for loader, capture plugins (3 to 16 s per photo), colour key, theme; rest as noted |
| [Meghnus/om10mi-mods](https://github.com/Meghnus/om10mi-mods) (found by the sweep, new) | E-M10 I | 14 film looks each with its own colour matrix and tone curve, 4 new Picture Mode entries; **12-sector hue/saturation/lightness editor**; a per-look editor; looks in RAW Data Edit; record limit 29:59 → 59:50 | released as "version 56" with camera samples |
| [thrains0220-byte/ep5-fw-reverse](https://github.com/thrains0220-byte/ep5-fw-reverse) | E-P5 (TruePic VI) | A 4-byte patch that lifts an AF step limit; a "Soft Chrome" look by table edits. Holds 12 archived community patches from xdel.ru | camera (AF patch, one user); project closed 2026-10-23 |
| lightsnowdev, [2014 blog](https://lightsnowdev.blogspot.com/2014/08/firmware-control-tool-to-flash-any.html) | E-M10, E-M5, tool lists E-P5, E-PL3, E-PL5, **E-PM2** | A tool that flashes any firmware file through a fake update server. The E-M10 "hack" changed the INFO screen, the camera name and a few ISO values (as summarised in [cmdada/em10-fw notes](https://github.com/cmdada/em10-fw/blob/main/notes/improvements.md)). No bitrate hack was ever released | historic; see `experiments/2026-11-12-hardware/01-public-sources.md` |

### Research, emulator-only, or host-side

| Project | Body | What it documents or plans |
|---|---|---|
| [xulfr/caduceus-om5](https://github.com/xulfr/caduceus-om5) (new) | OM-5 II, OM-5 | Colour and Monochrome Profile entries in Picture Mode, HSL for 12 colours, tone curve, **Live ND32 and ND64**. Emulator only; three earlier builds left the owner's camera in a restart loop (recovered from the card each time) |
| [RemeraLl1/epl9-lab](https://github.com/RemeraLl1/epl9-lab), fork [JuiceLee999/caduceus-epl9](https://github.com/JuiceLee999/caduceus-epl9) | E-PL9 | Gold 200 and Portra 400 looks in the Watercolor art-filter slots (the same idea as this project's film slots); research on **open-gate 4:3 movie** and a **gyro logger**. Not camera-tested |
| [ZakuZakuu/ep7-film-hack](https://github.com/ZakuZakuu/ep7-film-hack) | E-P7 | HSL looks; a **Wi-Fi protocol to write recipes into the camera** from a desktop client |
| [przestaw/OM-5-firmware-patches](https://github.com/przestaw/OM-5-firmware-patches) | OM-5 | Notes on lens communication and image stabilisation. No patches published |
| [nivag8899/olympus-em1m3-research](https://github.com/nivag8899/olympus-em1m3-research) | E-M1 III | Goal: a custom LUT (as 1D LUT + 3×3 matrix + 1D LUT) loaded from the card. Phase 0 |
| [matozoid/em10_1](https://github.com/matozoid/em10_1) | E-M10 I | Full documentation of firmware, USB PTP, Wi-Fi; a replacement desktop app. Owner does not flash |
| [sympho-ru/olympus-e-pl3-research](https://github.com/sympho-ru/olympus-e-pl3-research) | E-PL3 | Evidence database of the 1.6 firmware; modified images booted |
| [flatpanda/om-emu](https://github.com/flatpanda/om-emu), [nsud-dev/ghidra-mn103](https://github.com/nsud-dev/ghidra-mn103) | many | Emulator; Ghidra processor module |
| fishcu notes: [silent burst and Pro Capture rates](https://github.com/fishcu/oly_fw_analysis/blob/main/docs/features/om-5/BURST.md), [external flash](https://github.com/fishcu/oly_fw_analysis/blob/main/docs/features/FLASH.md), [Panasonic aperture ring](https://github.com/fishcu/oly_fw_analysis/blob/main/docs/features/pen-f/APERTURE_RING.md) | OM-5, E-M1 II/III, PEN-F, E-P7 | Rate lists for silent burst are menu data (60 fps accepted by the menu code in a test fixture; sensor not proven); flash protocol; how the aperture-ring patch works |
| Host-side, no flash: [n0p/om-tether](https://github.com/n0p/om-tether), [HolmHaensel/omcap](https://github.com/HolmHaensel/omcap), [aglotero/NINA.Plugin.OMCamera](https://github.com/aglotero/NINA.Plugin.OMCamera), [dpolarov/olympus-view-and-delete](https://github.com/dpolarov/olympus-view-and-delete), [philogicae/olympus-connect](https://github.com/philogicae/olympus-connect), [iKenndac/om-1-manual-firmware-install](https://github.com/iKenndac/om-1-manual-firmware-install) | Wi-Fi and USB bodies | Tethering, remote control, astrophotography driver, file manager, live-view relay, manual update. All need a radio or PTP capture, which the E-PM2 does not have (`hardware.md` §4) |
| Hidden service screens, [apotelyt E-PM2 shutter count](https://apotelyt.com/camera-find/olympus-e-pm2-actuation-count), [PetaPixel 2015](https://petapixel.com/2015/08/20/use-this-secret-code-to-view-hidden-info-on-olympus-cameras) | most Olympus bodies | A key sequence shows shutter count, flash count and IS count. No flash needed. I did not open the E-PM2 step list (from search snippets) |

### What these mods have that this mod does not

1. A **loader for code from the card** (fenykl on TruePic VI, em10-fw on TruePic VII). It ends the flash-per-change cycle.
2. **On-screen data**: battery %, focus distance, depth of field, focus meter (fenykl, on the E-PL3).
3. **Screenshot to the card** (fenykl).
4. **Looks from a card file and an on-camera editor** (Caduceus, om10mi-mods).
5. **Grain, halation, glow, split toning, Blacks/Whites, WB shift per look** (Caduceus).
6. **Extra aspect ratios** (XPan 65:24, 21:9) (Caduceus E-P7).
7. **Log or flat video curve** (Caduceus E-P7; em10-fw FLAT).
8. **Live ND from Multiple Exposure averaging** (Caduceus E-P7 research; a real Live ND port on the E-M5 III).
9. **Movie time limit** (nearly every project). This project has the patch written, not flashed.
10. **Button remaps** (Caduceus, db firmware).
11. **Minimum shutter speed for auto ISO** (Caduceus E-P7, db firmware).
12. **Focus bracketing by lens steps** (em10-fw: not working yet), **focus stacking any lens** (needs the stock stacker; the E-PM2 has none).
13. **Partial colour, raw monochrome, R/B swap, colour key** (em10-fw, fenykl).
14. **Subject detector** (fenykl bird detector on the second core).
15. **Pre-capture** (fenykl, E-M10 II only).
16. **Games** (OM-3).
17. **EXIF look name / recipe** (Caduceus).
18. **LCD colour correction** (Caduceus E-P7).
19. **Speaker shutter sound, menu language** (db firmware).

Nobody else publishes a mod for the E-PM2, E-PL5, E-PL6 or E-M5 (sweep of 2026-11-15; verified for GitHub only).

## (b) Ideas from other brands' mods, mapped to E-PM2 building blocks

Features only. One row per feature. Duplicates across brands are merged. 120 rows. Rows marked "Low priority", "No step" or "none" are the first to drop.

### How to read the tables

- **Source**: a page or repo file that was opened for this survey. Link keys are at the end.
- **E-PM2 block**: the known building block that could carry the feature. "unknown" means no evidence yet; the last column then names the smallest probe.
- **(fm)** = from memory, not verified from a source in this survey. It is used mostly for statements about stock E-PM2 behaviour that were not in the given fact list.
- "LV buffer" = the live-view buffer that the coloured focus peaking already reads and writes from the CPU.
- "Card blob" = machine code or data loaded from a card file with the proven loader.
- Checked after the table was written: the E-PM2 manual confirms these stock items that some rows mark "(fm)": Live
  View Boost (p.73), ISO-Auto Set with High Limit and Default (p.74), Digital Tele-converter (p.64), the Grainy Film, Soft
  Focus and Pin Hole art filters (p.28), RAW Data Edit (p.65-66), Noise Reduct. (p.74), Edit Filename (p.76), Pixel Mapping,
  Eye-Fi (p.78), Super Fine. Still from memory: that Grainy Film has a separate grain stage, the frame effect as a
  bitmap, the speaker path, 12-bit lossless ORF.
- Stock Multiple Exposure takes 2 frames, and its Overlay option adds a stored RAW, so 3 or more frames are already
  possible by hand (E-PM2 manual p.63). Image Overlay in playback combines up to 3 RAW files (p.67).

### b1. Exposure aids

| Feature | Mod / brand | What it does | Source | E-PM2 block | First probe or step |
|---|---|---|---|---|---|
| Zebras with a set threshold | Magic Lantern (ML), CHDK, Wonder Lantern Z30/Z5 (photo zebra), Gritty (GR II), Koma (GR DIGITAL) | Stripes or blink on areas over or under a luma level. | [ML-OV], [CHDK-INTRO], [WL-Z30], [Z5X], [GRITTY], [KOMA] | Stock highlight/shadow blink in live view. LV buffer pass for real stripes. | Find the two threshold constants of the stock blink display. Make them menu rows. |
| False colour | ML | Paints each exposure band in a fixed colour. | [ML-OV] | LV buffer pass in the art-filter pipeline, same hook as peaking. | Replace the peaking write with a 6-band luma-to-colour table. Measure the frame rate. |
| RGB and per-channel histogram | ML, CHDK | Live histogram per channel, also in log scale. | [ML-OV], [CHDK-INTRO] | Stock luma histogram. AE statistics block. OSD plane. | Dump the AE statistics block to a card file. See if it holds R, G, B separately. |
| Waveform monitor | ML | Luma per image column, drawn as a graph. | [ML-OV] | LV buffer column pass. OSD plane. | Time a column pass on every 8th pixel inside the peaking hook. |
| Vectorscope | ML | Plot of chroma of all pixels. | [ML-OV] | LV buffer, if it holds chroma. OSD plane. | Unknown pixel format. Dump one LV frame to card and decode it on the PC. |
| Spotmeter | ML | Shows the brightness of a small spot in percent or IRE. | [ML-OV] | LV buffer mean of a 32x32 block. Touch screen picks the spot. OSD text. | Print the mean luma of the centre block on the OSD. |
| Auto ETTR | ML (`ettr` module) | Shifts exposure after each shot until highlights just do not clip. | [ML-ETTR] | Stock histogram data. Exposure compensation variable. | Find the routine that sets exposure compensation. Call it from a post-capture hook. |
| Histogram and level on one page | Wonder Lantern Z30, Z5 Extensions | One DISP page shows both. | [WL-Z30], [Z5X] | Stock histogram and stock level gauge. DISP page table. | Find the DISP page dispatcher. Enable both draw calls on one page. |
| Histogram of the RAW data | CHDK (`shot_histogram`, `raw_ev_histo`), ML | Histogram from sensor data, not from the JPEG preview. | [CHDK-MOD] | Unknown: RAW buffer address at capture. | Write 64 bytes from the suspected RAW buffer to a card file at capture end. |
| Exposure override past stock limits | CHDK (65 s to 1/10000 s), ML (Exp.Override), Koma (240 s), Wonder Lantern Z30 (M mode 900 s) | Shutter, aperture and ISO values outside the menu range. | [CHDK-INTRO], [ML-EXPO], [KOMA], [WL-Z30] | Shutter speed table. Live Time timer. 1/4000 s is a mechanical limit. | Find the shutter table. Add one entry longer than 60 s and test. |
| Auto-ISO ceiling and slowest shutter | Koma, Gritty, BetterManual (Sony) | User sets the Auto-ISO limit and the minimum shutter speed. | [KOMA], [GRITTY], [SONY-BM] | AE program line table. Menu rows. | Find the program table. Stock has an ISO limit (fm); add the minimum shutter value. |
| Programmable auto exposure | ML (`autoexpo`) | The user draws the curves that P mode follows. | [ML-AUTOEXPO] | Same AE program table. Card blob for the curve. | After the row above works, load the table from a card file. |
| Live-view gain for dark scenes | ML (LV display gain), Iride 6D | Brighter live view in the dark, with slower refresh. | [ML-DISP], [IRIDE] | Stock Live View Boost (fm). Sensor frame timing is unknown. | Find where the live-view frame time is set. Double it and see if the image gets brighter. |
| DOF and focus distance readout | ML, CHDK | Shows subject distance, DOF, hyperfocal. | [ML-FOCUS], [CHDK-INTRO] | Lens status data. OSD text. | Unknown if lenses report distance. Dump the lens status struct to card at two focus positions. |
| Cropmarks, grids and frame lines from card | ML (cropmarks), CHDK (grid files), Wonder Lantern Z6, GRKit, Gritty | User-drawn overlays: 2.35:1, XPan, golden ratio, own bitmaps. | [ML-OV], [CHDK-GRIDS], [WL-Z6], [GRKIT], [GRITTY] | OSD plane. Loader for card files. | Draw a 1-bit bitmap from a card file on the OSD plane. |

### b2. Focus aids

| Feature | Mod / brand | What it does | Source | E-PM2 block | First probe or step |
|---|---|---|---|---|---|
| Magic Zoom | ML | A small magnified box inside the full live view. Split-screen and green-bar focus confirmation. | [ML-OV] | LV buffer. The OSD plane may not hold image data. The GPU is a second route. | Copy a 64x64 LV block to another LV position in the peaking hook. |
| Peaking outside MF Assist | Koma, ML, 6D II peaking build | Peaking always on, also during AF and movie recording. | [KOMA], [ML-OV] | Existing peaking hook. | Call the peaking pass when MF Assist is off. Then test during movie recording. |
| Focus stacking / focus bracketing | ML (Stack focus), CHDK (focus bracket), NX-KS, Sony FocusBracket, Sony WebControl | Takes a series with the lens moved one step each frame. | [ML-FOCUS], [CHDK-WIKI], [NX], [SONY-FB], [SONY-WEB] | Lens focus drive routine (focus-by-wire uses it). Interval shooting sequencer. | Find the focus-by-wire step routine. Call it with a fixed step count from a hook. |
| Rack focus, follow focus, stored focus points | ML, Samsung NX (`focus_buttons`) | Moves focus between saved points at a set speed. Recalls a saved infinity point. | [ML-FOCUS], [NX] | Same lens drive routine. Touch screen buttons. | Read back the lens focus position. Save and restore it once. |
| Snap focus | Koma, Gritty | Lens goes to a preset distance. Full press fires without AF. | [KOMA], [GRITTY] | Lens drive routine and position readback. | After position readback works, drive to a stored position on full press. |
| Trap focus | ML | With a manual lens, fires when the subject comes into focus. | [ML-FOCUS] | AF statistics block gives contrast per frame. Software release. | Log the AF statistics contrast value per frame to a card file while turning the ring. |
| Numeric focus meter for stars | Iride 6D ("Fuoco stelle") | A number that peaks at best focus on a star. | [IRIDE] | AF statistics block. OSD text. | Print the contrast value and its session maximum on the OSD. |
| Remote manual-focus stepping | Sony WebControl, NX remote controller | Focus steps sent from a PC or phone. | [SONY-WEB], [NX-RC] | Lens drive routine. USB debug shell or AP2 UART as the channel. | See the UART and USB rows in section 7. |
| AF micro-adjust (Dot-Tune) | ML (`dot_tune`) | Tunes phase-detect AF offset. | [ML-DOT] | none: contrast-detect AF has no offset to tune. | - |

### b3. Shooting automation

| Feature | Mod / brand | What it does | Source | E-PM2 block | First probe or step |
|---|---|---|---|---|---|
| Intervalometer with ramping | ML (`adv_int`, bulb ramping), Sony TimeLapse (AE lock, bracket per interval), NX-KS | Keyframes change shutter, ISO, focus over a time-lapse. Day-to-night ramp. | [ML-ADVINT], [ML-SHOOT], [SONY-TL], [NX] | Stock interval shooting. Hook between frames. | Change the shutter speed by 1/3 EV from a hook between two interval frames. |
| Screen off during interval shooting | Sony TimeLapse (DOFF), ML powersave | Display off between frames. | [SONY-TL], [ML-PREFS] | LCD backlight control. | Find the backlight routine. Call it in the interval wait state. |
| Bulb timer | ML (to 8 h), Wonder Lantern Z6 (extended slow shutter with countdown), pktriggercord (Pentax bulb timer setting) | Timed long exposure without a remote. Countdown shown. | [ML-SHOOT], [WL-Z6], [PKTC] | Live Time start/stop. A timer hook. OSD countdown. | Find the Live Time stop call. Call it after N seconds. |
| Bracketing with more frames and wider steps | ML (HDR bracketing), CHDK (bracketing in continuous mode) | Up to 9 frames, large steps, ISO or shutter. | [ML-SHOOT], [CHDK-WIKI] | Stock AE bracketing table. | Find the bracketing frame-count and step table. Add one row. |
| Exposure fusion preview | ML | Blends bracketed frames on the playback screen. | [ML-SHOOT] | Playback buffer and CPU. Unknown cost. | Low priority. First find the playback image buffer. |
| Motion detection trigger | ML, CHDK | Fires when the scene changes (lightning, wildlife). | [ML-SHOOT], [CHDK-MOD] | AE statistics block or LV buffer difference. Software release (interval shooting has one). | Call the interval-shooting release routine when the AE block sum changes by more than a threshold. |
| Sound trigger | ML (Audio RemoteShot) | Fires on a loud sound. | [ML-SHOOT] | Internal microphone. Unknown if audio samples flow outside movie mode. | Find the audio level variable in movie mode. Check if it is live in photo mode. |
| Touch-free trigger | ML (LCD sensor remote) | Hand near the sensor fires the shutter. | [ML-SHOOT] | 3-axis accelerometer (tap), touch screen, or face detector. | Read the face detector result. Fire when a face appears. |
| Silent picture from live view | ML (`silent`), NX500 (silent shutter), Sony TimeLapse (SS) | Saves a frame without a shutter cycle. | [ML-SILENT], [NX], [SONY-TL] | Two levels. (a) LV buffer to a card file. (b) Full sensor read with the shutter open, as Live Bulb does (24.3 ms readout). No electronic shutter code exists. | Write one LV buffer frame to a card file from a half-press hook. |
| RAW sum / average of several frames | CHDK (`raw_merge`) | Adds or averages RAW frames in camera. | [CHDK-MOD] | Stock multiple exposure (2 frames). Live Bulb accumulation. | Find the frame limit of multiple exposure. Try 3. |
| Pixel-shift merge | NikonFirmwarePatch (Z8) | Merges a sensor-shift series into one file in camera. | [Z8] | 2-axis sensor-shift IS. Unknown: commanded sub-pixel offsets. | Find the IS position command. Shift by a fixed offset between two shots and measure on a chart. |
| Pre-capture | NikonFirmwarePatch (Z8 C15/C30 RAW pre-capture) | Keeps frames from before the full press. | [Z8] | none at full resolution: mechanical shutter only. A ring of LV frames is possible. | After the LV frame dump works, keep the last N frames in RAM. |
| Flash tweaks | ML (flash compensation -10..+3 EV, flash/no-flash pairs), GR Mod (Direct Flash: fixed power from distance and guide number) | Wider flash control. | [ML-SHOOT], [GRMOD] | Flash compensation limits table. Clip-on flash on AP2. | Find the flash compensation limit constants. |
| Astro planning screens | Iride 6D (NPF rule, sky calendar, polar alignment) | Calculators for max star exposure and moon data. | [IRIDE] | Menu rows and OSD text. Clock. IS focal length setting as input (fm). | Show the NPF time for the current focal length on the OSD. |
| Film-roll mode | M-Film (Canon) | No review after a shot. Frame counter. Develop the roll later. | [MFILM] | Rec View off. OSD counter. Stock RAW edit for later development. | Draw a frame counter on the OSD. |

### b4. Video

| Feature | Mod / brand | What it does | Source | E-PM2 block | First probe or step |
|---|---|---|---|---|---|
| Bitrate and quantiser control | Panasonic PTool (GH1/GH2/GF1/GF2: 44 to 100 Mbit and more), ML (Bit Rate), Nikon Hacker (36/54/64 Mbit), NX-KS and nx-patch, Wonder Lantern Z30, Z8 patch | Higher or user-set video bitrate. | [EOSHD], [DVX], [ML-MOVIE], [NH], [NX], [WL-Z30], [Z8] | QP floor and rate table are software. Patch is written. Card writes about 28 MB/s. | Flash the written patch. Record a high-detail scene. Check for buffer overflow. |
| GOP length and intra-only | PTool (GOP 1, 3, 15) | Shorter GOP or all-I frames. | [EOSHD], [DVX] | H.264 encoder setup. Unknown where the GOP value is set. | Find the encoder init parameter block. Compare it with the stream's real GOP. |
| Record-time limit removal | PTool, Sony OpenMemories Tweak, Nikon Hacker, NX-KS, fujihack, CHDK, Wonder Lantern Z30 (slow motion) | No 29 min stop. | [EOSHD], [SONY-TW], [NH], [NX], [FUJIHACK], [CHDK-WIKI], [WL-Z30] | 29-min timer is software. Patch is written. | Flash and record 35 min. Note what happens at the 4 GB file size. |
| Auto restart of recording | ML (Movie Restart), NX (`log_watcher`) | Starts a new clip when the file limit stops the first. | [ML-MOVIE], [NX] | Hook on record stop. Software record start. | Find the record-start routine. Call it from the stop event when the stop reason is the size limit. |
| Frame rate override, native 24p/25p | ML (FPS override, down to 0.2 fps), PTool (native 24p/25p on GH1), Nikon Hacker (variable frame rate) | Other frame rates than stock. | [ML-MOVIE], [DVX], [NH] | Stock is 30p only. Sensor frame timing registers: unknown. | Find the sensor timing writes at movie start. Change the frame period by 20 % and check the file. |
| HDR video | ML | Alternates two ISO values frame by frame. | [ML-MOVIE] | Per-frame sensor gain. Unknown. | After the timing writes are found, toggle gain in a per-frame hook. |
| Clean HDMI live view | Nikon Hacker (Clean HDMI and LCD, HDMI full screen), ML (Force HDMI-VGA), AXIOM (HDMI with overlay plane) | Live image on HDMI without overlays. | [NH], [ML-DISP], [AXIOM] | HDMI is playback only in stock. Live view over HDMI is unknown. | Plug HDMI in shooting mode. Log the display-route variable. Find the code that blocks it. |
| Audio meters and manual gain | ML | Level meters on screen, AGC off, gain control. | [ML-AUDIO] | Internal mic path. OSD. No mic jack. | Find the audio peak value in the movie encoder path. Draw it as a bar. |
| Sensor crop movie mode | ML (`crop_rec`, 1:1 3x crop) | Reads a centre window 1:1 for more detail. | [ML-CROP] | Sensor readout window registers. Unknown. | Compare sensor register writes with and without the stock digital tele-converter (fm). |
| RAW video | ML (`mlv_lite`), eos-m10-raw (CHDK module, 10-bit lossless MLV), AXIOM (raw over HDMI, raw stills) | Stores sensor data frames, not H.264. | [ML-RAWV], [M10RAW], [AXIOM] | Unknown: where live-view sensor data sits before demosaic. Card speed allows about 1280x720 10-bit at 24 fps. | Search for the pre-demosaic live-view buffer. Dump one frame. |
| Log or flat movie profile | NikonFirmwarePatch (N-Log, S-Log3, Log3G10), Z5 plan (flat tone) | Low-contrast curve for grading. | [Z8], [Z5X] | Per-look tone curves. An art-filter slot can carry a flat curve. | Record a movie in a film-look slot. Check that the look's curve applies to the movie. |
| Anamorphic desqueeze | NikonFirmwarePatch (desqueeze preview and playback), PTool patches (anamorphic MJPEG modes) | Shows squeezed footage unsqueezed. | [Z8], [EOSHD] | LV scaler or GPU. Unknown. Cropmarks give a cheap version. | Low priority. Start with cropmarks. |
| Movie metadata log | ML (Movie Logging) | Writes lens and exposure data beside each clip. | [ML-MOVIE] | Stock file write. Hook on record start and stop. | Write a text file with shutter, aperture, ISO at record start. |
| Record with the shutter button | ML (Movie REC key), NX (`shutter_to_rec`) | Half-press or full-press starts and stops video. | [ML-MOVIE], [NX] | Button function table. | Map full press to the record routine in movie mode. |
| Video rotation tag | Wonder Lantern Z30 | Writes orientation into new clips. | [WL-Z30] | Accelerometer. MOV header write. | Find the MOV header builder. Unknown location. |
| Image effects in video | ML (Image Effects: desaturate, negative and others from DIGIC registers) | Register-level looks while recording. | [ML-MOVIE] | Art-filter pipeline and the per-look tables. | Same test as the log profile row. |

### b5. Image pipeline and looks

| Feature | Mod / brand | What it does | Source | E-PM2 block | First probe or step |
|---|---|---|---|---|---|
| Looks loaded from the card | GRKit (effects and recipes), Gritty (text recipes), Recipe Lab (Sony), XPan Digital (`.fs` recipes), Koma | New looks without a new firmware build. | [GRKIT], [GRITTY], [RECIPELAB], [XPAN], [KOMA] | Loader for card files. Per-look matrix, tone curves, chroma curves, six-axis hue. | Load one 3x3 matrix from a card file when a film slot is selected. |
| More look slots | GR Mod (up to 20 added slots), gr3-film-mods (new Image Control entries, no stock mode lost), M-Film (72), XPan Digital (84) | Many looks in one list. | [GRMOD], [GR3FILM], [MFILM], [XPAN] | Art-filter slot table. With card loading, one slot can page through many looks. | Add a sub-menu row that picks the card file for a slot. |
| 3D LUT import | Sony LUT Camera (full `.cube` on the saved JPEG), GRKit (own LUTs), GR Mod and gr-custom-tool (fit `.cube`/`.xmp` to camera parameters) | Use a LUT made on a PC. | [SONYLUT], [GRKIT], [GRMOD], [GRCT] | No 3D LUT stage. Fit the LUT on the PC to matrix + curves + six-axis hue, as GR Mod does. | Write the PC-side fitter. Report the mean colour error per look. |
| Per-look hue sectors and colour wheel editor | GR Mod and gr3-film-mods (12 hue sectors), XPan Digital (12-wedge colour creator on the camera) | Edits saturation, hue and luma per hue sector. | [GRMOD], [GR3FILM], [XPAN] | Six-axis hue table. Touch screen. Menu rows. | Change one hue-axis value from a menu row and see live view follow. |
| Look strength | Film Studio NEX-6 (30/50/70/100 %) | Blends the look toward neutral. | [NEX6] | Interpolate matrix and curves toward identity before loading. | Add a strength row that scales (matrix - identity). |
| Film grain | GRKit, chdk-film, XPan Digital, Koma | Adds grain, with size and amount. | [GRKIT], [CHDKFILM], [XPAN], [KOMA] | The stock grain stage of the Grainy Film filter (fm). | Find the grain stage flag. Turn it on in a colour film slot. |
| Halation and glow | GRKit (Glow), GR Mod (halation, red/white, 3 strengths), XPan Digital | Bloom around bright lights. | [GRKIT], [GRMOD], [XPAN] | Soft-focus blur stage (fm) plus the RGB combine pass. | Blend the soft-focus image into the red channel only. |
| Vignette | chdk-film, Koma | Darkens corners per look. | [CHDKFILM], [KOMA] | Pin Hole filter shading stage (fm). | Find the shading table. Enable it in a film slot at low strength. |
| Date imprint | GRKit, GR Mod, Wonder Lantern Z30, FRAME (GR II) | Burns a film-style date into the JPEG. | [GRKIT], [GRMOD], [WL-Z30], [FRAME] | Art-filter frame effect draws a bitmap into the image (fm). Clock. | Find the frame-effect bitmap. Replace it with a rendered date string. |
| Border | GRKit | White or black border, photo scaled inside. | [GRKIT] | Same frame effect. | Same probe. |
| Custom aspect ratios (XPan 65:24 and others) | GRKit, GR Mod (custom ratio lists, full-frame RAW kept), Wonder Lantern Z30/Z6, XPan Digital, Gritty (frame lines) | New crop ratios with a masked live view. | [GRKIT], [GRMOD], [WL-Z30], [WL-Z6], [XPAN], [GRITTY] | Stock aspect table. OSD mask. | Find the aspect table. Add a 65:24 row. |
| Crop to fixed focal lengths | GRKit (35/40/50/70/90 mm) | Stepped digital crop. | [GRKIT] | Stock digital tele-converter factor (fm). | Find the 2x factor constant. Try 1.4x. |
| Look applied to stored photos | IXFilm OS (re-develops JPEGs in a queue), M-Film (develop the roll), GR IIIx HDR (Multi RAW Development over the whole card) | Batch processing in camera. | [IXFILM], [MFILM], [GR3XHDR] | Stock RAW Data Edit for one file (fm). File routines. | Call the RAW edit routine on the next file in a loop. |
| RAW noise reduction off | gr3-film-mods (Bayer NR off to ISO 8000), Nikon Hacker (Disable Star Eater, True Dark Current) | Removes hidden RAW-domain filtering. | [GR3FILM], [NH] | Unknown if the E-PM2 filters ORF data. | Shoot a 60 s dark frame with NR off. Look for a median-filter pattern in the ORF. |
| Dark-frame subtraction control | CHDK (dark frame off), BetterManual (long-exposure NR off), Pentax debug mode (not opened, see end) | Skips the second exposure. | [CHDK-INTRO], [SONY-BM] | Stock Noise Reduction Off/On/Auto (fm). Extension: reuse one stored dark frame. | Low priority. Stock covers the basic case. |
| Dual ISO | ML (`dual_iso`) | Alternate line pairs at two ISOs for about 3 stops more range. | [ML-DUAL] | Sensor gain registers. Unknown if gain can change per line. | Find the sensor gain write. Read the register map near it. |
| HDR JPEG with gain map, Display P3 | Ricoh GR IIIx HDR | Writes HDR gain-map JPEGs and P3 colour. | [GR3XHDR] | JPEG writer and file routines. Heavy work. | Add one custom APP segment to a JPEG at file close. |
| Creative RAW effects | Mirror Worlds, Bayer Drift (ML modules, Canon EOS M) | Mirrors or shifts Bayer samples before the RAW is saved. | [MIRROR], [BAYER] | RAW buffer at capture. Unknown address. | Same probe as the RAW histogram row. |
| Selective colour and B&W filter looks | Koma (SELECT: one colour kept), chdk-film (B&W stocks) | One hue kept, rest mono. | [KOMA], [CHDKFILM] | Six-axis hue and chroma curves. | Set five of six chroma axes to zero in a slot. |
| Live preview that matches the saved look | Sony LUT Camera (fitted preview), XPan Digital, GRKit | Live view shows the final look. | [SONYLUT], [XPAN], [GRKIT] | Already true for art-filter slots. | - |

### b6. RAW and files

| Feature | Mod / brand | What it does | Source | E-PM2 block | First probe or step |
|---|---|---|---|---|---|
| RAW where stock has none or a worse one | CHDK (RAW/DNG), Leica M8 patch (14-bit DNG in camera), Nikon Hacker (NEF compression off or lossless), Wonder Lantern Z30 (NEF compression menu) | Full sensor data saved. | [CHDK-INTRO], [M8], [NH], [WL-Z30] | Stock ORF is already 12-bit lossless (fm). | No step. An untouched-sensor dump is the RAW histogram probe. |
| DNG output | CHDK (`dng`), Leica M8 patch | Writes a DNG that opens without a converter. | [CHDK-MOD], [M8] | File routines. RAW buffer (unknown). | Only after the RAW buffer is found. |
| Lens data for manual lenses | Leica M8 patch (lens code in MakerNote), Sony LegacyLenses (not opened) | Stores the adapted lens in EXIF. | [M8] | EXIF writer. The IS focal-length setting (fm). | Find the EXIF FocalLength write. Feed it the IS focal length when no lens answers. |
| File and folder name control | ML (`img_name`) | Custom prefix and numbers. | [ML-IMGNAME] | Stock Edit Filename (fm). | No step. |
| File browser, text reader, picture viewer | ML (`file_man`, `pic_view`), CHDK (file browser, text reader) | Browse the card, read text, delete files. | [ML-FILEMAN], [CHDK-INTRO] | Stock file routines. OSD text. A directory-list routine is not yet located. | Find the directory read routine. List the card root on the OSD. |
| Settings backup to card | ML (config file), Koma (backup, restore, copy to another body), Gritty (export presets), NX-KS (profiles) | Saves all settings as a file. | [ML-PREFS], [KOMA], [GRITTY], [NX] | File write. Settings block in RAM. | Dump the settings block to a card file. Diff two dumps. |
| Deflicker sidecar | ML (`deflick`) | Writes XMP exposure corrections for time-lapse frames. | [ML-DEFLICK] | File write. AE statistics per frame. | Write the mean of the AE block to a text line per interval frame. |
| Card speed test and SD overclock | ML (`bench`, `sd_clock`), CHDK (benchmark) | Measures and raises card write speed. | [ML-BENCH], [ML-SDCLK], [CHDK-MOD] | SD host at about 28 MB/s. Clock setup is unknown. | Time a 32 MiB write with the stock file routines. Then find the SD clock divider. |
| Bad pixel list | CHDK (`badpixel.bin`) | Maps dead pixels in RAW. | [CHDK-MOD] | Stock Pixel Mapping (fm). | No step. |
| Faster USB file listing | Wonder Lantern Z30 (`mtp-fast`) | Speeds the MTP object list. | [WL-Z30] | USB MTP code. | Low priority. |

### b7. Remote, USB and scripting

| Feature | Mod / brand | What it does | Source | E-PM2 block | First probe or step |
|---|---|---|---|---|---|
| Modules loaded from the card | ML (modules), Z5 Extensions (`Z5APP.BIN` from card, firmware only has small entries), GRKit (`.GRM` modules, no firmware write), CHDK (`.flt` modules) | Features live on the card. Remove the card and the camera is stock. | [ML-MODS], [Z5X], [GRKIT], [CHDK-MOD] | Loader for card files by name pattern. Free code space for a small stub. scheap allocator. About 512 MiB RAM. | Load a position-independent blob from a card file and call it from one hook. |
| Scripting | CHDK (uBASIC and Lua), ML (`lua`) | User scripts drive keys, exposure, shooting and drawing. | [CHDK-SCRIPTS], [ML-LUA] | Card blob with a small interpreter. Stock file routines. | After the module row works, port a tiny bytecode interpreter with 5 calls: key press, release, wait, set shutter, print. |
| Script library: intervalometer, HDR, motion, countdown | CHDK (`interval.lua`, `hdr.lua`, `motion.lua`) | Ready scripts for common jobs. | [CHDK-SCRIPTS] | Same. | Same. |
| PTP extension and tethered capture | CHDK (`ptp.c`, remote capture), Koma (tethered shooting with live view), pktriggercord (Pentax USB control), fujihack (read/write/exec over USB), NX (enable PTP) | PC changes settings, fires the shutter, pulls files and live view. | [CHDK-CORE], [KOMA], [PKTC], [FUJIHACK], [NX] | USB PTP exists but has no capture. Factory vendor debug shell over USB. | List the debug shell commands. Look for key-event or release commands. |
| Webcam mode | Koma (via OBS) | Live view to the PC as a video source. | [KOMA] | LV buffer. USB bulk endpoint. Unknown throughput. | Read one LV frame over the debug shell memory-read command, if one exists. |
| USB cable as a trigger | CHDK (`usb_remote`, multi-camera sync) | 5 V pulses on USB fire the camera. | [CHDK-CORE] | USB VBUS detect or the AP2 UART RX line. | Find the USB-connect event. Fire the release from it when a menu flag is set. |
| Serial console | AXIOM (shell and register tools), CHDK (`uartr.lua`) | Text commands over a UART. | [AXIOM], [CHDK-LUALIB] | AP2 accessory port UART. | Send a fixed string on the AP2 UART from a hook. Capture it with a 3.3 V adapter. |
| Wi-Fi remote and web control | NX remote controller (browser control, screen mirror), Sony WebControl (MJPEG live view, focus stacking, JSON-RPC), fuji-cam-wifi-tool, OpenMemories Tweak (telnet, adb) | Phone or browser controls the camera. | [NX-RC], [SONY-WEB], [FUJIWIFI], [SONY-TW] | none on board: no Wi-Fi. A small Wi-Fi module on the AP2 UART could bridge the serial console. | Do the serial console probe first. |
| GPS tagging | CHDK (`gps.c`) | Position in EXIF. | [CHDK-CORE] | none on board. A GPS module on the AP2 UART is possible. EXIF writer. | After UART receive works, parse one NMEA line. |
| Wireless SD card tricks | ML (EyeFi Trick), CHDK (`eyefi`) | Controls upload of an Eye-Fi card. | [ML-SHOOT], [CHDK-MOD] | Stock Eye-Fi support (fm). | Low priority: those cards are obsolete. |
| Screenshot | ML (Screenshot), NX (LCD capture) | Saves the screen to the card. | [ML-DEBUG], [NX] | OSD plane and LV buffer. File write. | Dump the OSD plane to a card file. Useful for the mod's own docs. |
| Run code and read memory from a PC | fujihack (USB exec), NX (telnet, gdb, memory poker), OpenMemories (telnet, adb), Lumix research (service USB reads) | Fast development loop without flashing. | [FUJIHACK], [NX], [SONY-TW], [LUMIX] | Factory vendor debug shell over USB. | Check if the shell has memory read, write and call commands. Then load test code to RAM. |

### b8. UI and misc

| Feature | Mod / brand | What it does | Source | E-PM2 block | First probe or step |
|---|---|---|---|---|---|
| Own menu page and quick menu | ML (custom menus), CHDK (user menu), GRKit (ADJ page), Gritty (TTY menu), Koma (own tab) | A user-built list of the most used items. | [ML-FEAT], [CHDK-MOD], [GRKIT], [GRITTY], [KOMA] | Menu tables take new rows. | Already proven. Add a "favourites" page built from a card file. |
| Button and dial remap | fujihack (button remap), NX-KS (EV + key shortcuts), ML (arrow/SET shortcuts), Leica M8 patch (EV and ISO on the rear dial) | New functions on existing controls. | [FUJIHACK], [NX], [ML-PREFS], [M8] | Button function table. | Find the Fn/REC assignment table. Add one new function ID that calls a hook. |
| Camera stats screen | Leica M8 patch (shots, battery, temperature, lens code), ML (shutter count, CMOS temperature), NX (shutter and power-on count), Wonder Lantern Z50 (shutter count) | Shows counters and sensors. | [M8], [ML-DEBUG], [NX], [WL-Z50] | Counters in the settings block. OSD text. | Find the shutter counter in the settings dump. Show it on an info page. |
| Always-on battery and card readout | CHDK (battery indicator, free space), chdk-film (one status pill) | Exact battery voltage or percent at all times. | [CHDK-INTRO], [CHDKFILM] | Battery ADC value. OSD text. | Find the battery voltage variable. Print it. |
| Display presets | ML (LV Display Presets) | Four sets of overlay settings, cycled with one key. | [ML-PREFS] | DISP page table. | After new overlays exist, store their on/off flags per DISP page. |
| Full-screen custom shooting UI | M-Film (film camera HUD), CamDesk (large exposure readout), Iride 6D, Film Studio NEX-6 (3-stage overlay) | Replaces the stock info screen. | [MFILM], [CAMDESK], [IRIDE], [NEX6] | OSD plane. Possibly the GPU. | Draw one large shutter/aperture readout on the OSD. |
| Portrait-orientation UI | Wonder Lantern Z30 | Info layout turns when the camera is held upright. | [WL-Z30] | Accelerometer. OSD. | Low priority. |
| Custom power-on or power-off image | GR Mod, gr-custom-tool, CHDK (logo) | User picture at start or shutdown. | [GRMOD], [GRCT], [CHDK-INTRO] | OSD or playback draw at boot. Card file. | Find the start-up screen draw call. |
| Custom shutter sound | Z5 Extensions, Wonder Lantern Z6/Z30/Z50 | Plays a WAV from the card at each shot. | [Z5X], [WL-Z6], [WL-Z30], [WL-Z50] | Speaker and beep path (fm). The shutter is mechanical, so the value is low. | Find the beep routine. Play a different tone. |
| Games and toys | CHDK (Tetris, Snake, Sudoku, Reversi, Sokoban and more; calendar, stopwatch), ML (Arkanoid), DOOM ports | Fun. | [CHDK-GAMES], [ML-ARK] | OSD plane, buttons, touch screen. The GPU is there too. | Only as a test of the module loader. |
| Object detection | ML (`yolo`) | Detects objects on the live image. | [ML-YOLO] | Hardware face detector gives faces only. | Read the face detector result struct. |
| Fix old-firmware limits | Koma (clock kept, SDHC/SDXC cards, battery log) | Repairs age-related faults. | [KOMA] | Not needed on the E-PM2. A battery log to card is possible. | - |
| Safe-start design | Gritty (hold a key to boot stock, auto fallback), Z5 Extensions (no card module = stock path), GRKit (card only) | The mod can always be bypassed. | [GRITTY], [Z5X], [GRKIT] | Hook at start. Button read. | Read one button at boot. Skip all hooks when it is held. |

### b9. Unlocks

| Feature | Mod / brand | What it does | Source | E-PM2 block | First probe or step |
|---|---|---|---|---|---|
| Menu language unlock | Sony OpenMemories Tweak, PTool patches (all languages), Lumix research (GM5 Japanese unlock), Nikon Hacker (multi-language) | Opens all languages on region-locked bodies. | [SONY-TW], [EOSHD], [LUMIX], [NH] | Region flag and language table. | Find the language list and the flag that hides entries. |
| PAL/NTSC switch | Sony OpenMemories Tweak, PTool (GH1) | Unlocks the other video standard. | [SONY-TW], [DVX] | Stock is 30p only. This is the frame-rate row in section 4. | - |
| ISO range extension | PTool patches (GH2 ISO to 12800) | Opens ISO values that the menu hides. | [EOSHD] | ISO table. | Find the ISO table. Check for entries below 200 or above the menu maximum. |
| Third-party battery | Nikon Hacker, PTool (from search snippet, see end) | Accepts batteries without the maker's chip. | [NH] | Unknown if the E-PM2 checks the battery. | No step unless a battery is refused. |
| Live-view and sleep timeouts | Nikon Hacker (15 min live view to 3 h, no display auto-off) | Longer timers. | [NH] | Sleep timer table. | Find the sleep timer values. |
| JPEG quality | Nikon Hacker (JPEG compression: quality over size) | Larger, less compressed JPEGs. | [NH] | JPEG quantiser tables. Stock has Super Fine (fm). | Low priority. |
| Hidden factory modes made usable | Leica M8 patch (hidden service RAW mode kept on), Wonder Lantern Z30 (factory 900 s path), NX (DEV mode), pktriggercord (hidden Pentax settings) | Turns existing dormant code into a menu choice. | [M8], [WL-Z30], [NX], [PKTC-SET] | Factory debug shell. Service menu. | List every command of the factory shell and every hidden menu row. |
| Firmware version rules | gr-custom-tool (allow downgrade), Lumix research (updater policy) | Lets the user flash any version, also back to stock. | [GRCT], [LUMIX] | Updater version compare. | Confirm that a same-version reflash is accepted. |
| Wi-Fi 5 GHz | Wonder Lantern Z30 | Opens the 5 GHz band. | [WL-Z30] | none: no Wi-Fi. | - |
| More RAM for the OS | GR IV research (Linux booted with 1 GiB offline) | Repartitions memory. | [GR4] | Not needed: about 512 MiB is there. | - |

### b10. Local checkouts: status

| Upstream repo | Camera | Features it adds | Status per its README |
|---|---|---|---|
| [chasedson/chdk-film][CHDKFILM] | Canon PowerShot A570 IS | 11 film stocks applied to the RAW buffer before Canon's JPEG pipeline. Grain, vignette, film picker, RAW saved clean. | Working build, card only. |
| [BjornB2/ixfilm-os][IXFILM] | Canon IXUS 120 IS | 18 film looks. Re-develops the camera's JPEGs in a background queue. | Works. Full-size modes are experimental. |
| [HNGSeries/mfilm-canon-film-simulation][MFILM] | Canon EOS with Magic Lantern | Film-camera UI, 72 stocks, roll and frame counter, develop in camera, contact sheet. | Released (0.2.1). 8 cameras work, 6 with a problem, 2 in test. |
| [DangLamTung/XPan-Digital-Canon-6D][XPAN] | Canon EOS 6D | ML module. Film look written into the JPEG at the shutter, 84 looks, 65:24 framing, 12-wedge colour creator, recipe entry, `.cube` export. | Author's camera. Experimental. |
| [idontknownihil/gr3-film-mods][GR3FILM] | Ricoh GR III 2.10 | Film looks as new Image Control entries, 12 hue sectors, RAW NR off to ISO 8000, RAW development with films. | v16 tested on one camera. Later notes are research. |
| [DoYitNow/gr-custom-tool][GRCT] | Ricoh GR IV | Browser editor: crop ratios, shutdown image, filter and XMP fitting, version and downgrade policy. | Generates files. README says no full on-camera acceptance yet. |
| [ahonn/GRKit][GRKIT] | Ricoh GR III, IIIx, IV | Card-only runtime: film looks, LUTs, crops, guides, date imprint, glow, border, grain, recipes, modules. | Released. Tested firmware versions listed. Experimental. |
| [Maxwooow/Ricoh-GRMod][GRMOD] | Ricoh GR IV, GR III, GR IIIx | Desktop tool: `.cube`/`.xmp` into Image Control, up to 20 slots, hue sectors, halation, date imprint, soft focus, custom ratios, power-off image, Direct Flash. | Released (0.8.6). Camera-tested per feature. |
| [jhihhe/Jhih-FilmLab][FILMLAB] | Sigma fp 5.02 | 82 colour recipes switched by button, HUD. RAM-loaded. | Offline checks only. 0 of 82 recipes accepted on camera. |
| [gasdevmco/leica-m8-firmware][M8] | Leica M8 2.014 | Hidden 14-bit RAW mode kept on, 14-bit DNG written in camera, camera stats on INFO, EV and ISO on the dial. | Tested on the author's camera (v0.9.0). Archived. |
| [XinmiaoZhao/NikonFirmwarePatch][Z8] | Nikon Z8 C 3.11 | Open-gate 3:2 N-RAW, desqueeze, N-RAW quality tiers, ProRes and H.265 bitrate tiers, extra log curves, RAW pre-capture, pixel-shift merge in camera. | Released (v0.4.0). Experimental. |
| [honokaoshi83-max/z5-extensions][Z5X] | Nikon Z 5 C 1.50 | Card module: custom shutter sound, histogram with level, 3x3 and 2x2 grids, photo zebra. | Tested on one camera. |
| [EnglandLobster/sony-lut-camera][SONYLUT] | Sony PMCA bodies (27 models) | Android app in camera: full 3D LUT on the saved JPEG, original kept, `.cube` import, fitted live preview. | v0.9.1 beta. Verified on A6300 only. |
| [leyteris/sony-nex6-film-studio][NEX6] | Sony NEX-6 1.03 | 17 looks from runtime camera parameters, 4 strengths, own overlay. | Alpha. No readable hardware logs yet. |

### b11. GitHub sweep: other repos found (README opened unless marked)

- Nikon: [WonderLantern/wonder-lantern-z30][WL-Z30], [WonderLantern/WonderLantern-z6][WL-Z6], [ha1vk/wonder-lantern-z50-firmware][WL-Z50], [simeonpilgrim/nikon-firmware-tools][NH] (Nikon Hacker patch source).
- Ricoh: [overscanindustries/koma][KOMA], [robbcocco/gritty][GRITTY], [Lyle-xub/FRAME-GR2][FRAME], [crciuperca/Ricoh-GR-IIIX-HDR][GR3XHDR], [radium-wang/ricoh-gr4-firmware-analysis-and-feature-expansion][GR4], BangBOOM/gr3-film-sim-firmware (four film slots with nine sliders each).
- Ricoh, description line only, README not opened: cqkking/ricoh-gr4-4k-mod, cqkking/ricoh-gr4-ai-af-mod, caioluders/gr3x-lain-edition (DOOM and a Game Boy emulator), tinyblckc0000al/gr3x-fw-play, botnick/GRKU, judgem00/gr3-look-editor.
- Canon: [m-a-x-s-e-e-l-i-g/mirror-worlds][MIRROR], [m-a-x-s-e-e-l-i-g/bayer-drift][BAYER], [voncapel/eos-m10-raw][M10RAW], [vugpgbwefwq47397-debug/camdesk-ml][CAMDESK], [GodEater58/Iride-6D][IRIDE]. Description only: lauris-nl/doom550d, GrongBrangost/soup-film-1100d, thebakers-club/souper7d, ShogunBP/SmoothAF, Premax6d/Canon-eos-6D-mark-II-focus-peaking.
- Sony: [ma1co/OpenMemories-Tweak][SONY-TW], [jonasjuffinger/TimeLapse][SONY-TL], [obs1dium/FocusBracket][SONY-FB], [obs1dium/BetterManual][SONY-BM], [hhb/sony-pmca-webcontrol][SONY-WEB], [voxivoid/recipe-lab-sony-pmca][RECIPELAB], masterflai/pmca-community-sources. Description only: lngyneric/xpan-overlay-sony-pmca, qwqFranzFox/better-timelapse, bonyback1/sony-pmca-ricoh-mod.
- Samsung: [ottokiksmaler/nx500_nx1_modding][NX], [mewlips/nx-remote-controller-mod][NX-RC], ge0rg/samsung-nx-hacks (NX300/NX30 root and scripts), RayforLoy/NX_mini_evo (shoot without lens contacts, selfie flash menu; experimental).
- Panasonic: [flickering-star/lumix-firmware-research][LUMIX] (GM1/GM5/GX9 service USB, updater, GM5 language unlock; also MN103 emulation, the same CPU family as the E-PM2).
- Fuji: [fujihack/fujihack][FUJIHACK], [hkr/fuji-cam-wifi-tool][FUJIWIFI]. Description only: EnglandLobster/fujifilm-firmware-tools (firmware unpacking).
- Pentax: [asalamon74/pktriggercord][PKTC]. Description only: i-am-shodan/PentaxFirmwareTool (K-30).
- Sigma: [jhihhe/Jhih-FilmLab][FILMLAB].
- Search terms that returned nothing: "fujifilm firmware hack", "pentax firmware hack", "samsung nx mod", "ricoh gr firmware", "sony camera firmware hack", "canon film simulation firmware", "panasonic lumix firmware hack", "sigma fp firmware", "nx500 mod", "pentax debug mode". Single-topic terms ("ricoh gr", "magic lantern", "sony pmca", "samsung nx", "fujifilm firmware", "lumix firmware") found the repos above. Several more terms hit the GitHub search rate limit and were not rerun.

## (c) Features of newer Olympus / OM System bodies

Scope: stock, user-visible features of bodies from the E-P5 (2013) to the OM-5 II (2025), checked against the E-PM2 manual. 21 maker manuals were downloaded and searched as text.

### How to read the table

- **First judgement** is one of: SOFTWARE-ONLY, NEEDS-PROBE, HARDWARE-BLOCKED, ALREADY-HAS.
- Each judgement carries a confidence word: *verified* (seen in a cited page), *inferred* (reasoned from cited facts), *unknown*.
- "Sister" names a body with the same 16 MP sensor family that has the feature in stock code. E-PL6, E-P5 and E-M5 use TruePic VI like the E-PM2. E-M10 and E-PL7 use TruePic VII; the same sensor is reported, not verified.
- "hw s.N" means `hardware.md` section N. The rows use the facts of that file as summarised for this survey.
- Manual page numbers are PDF page indices. They matched the printed page number in every manual I spot-checked.
- The E-PM2 manual describes firmware 1.0. I did not find release notes that add features in 1.1 to 1.6.

### Sources (manual keys)

| Key | Document | URL |
|---|---|---|
| E-PM2 man. | E-PM2 instruction manual (fw 1.0) | not online; cited by page only |
| E-M5 man. | E-M5 manual (fw 1.0) | https://download.omsystem.com/pages/inst/em5/manual_em5_ENU.pdf |
| E-PL6 man. | E-PL6 manual | https://download.omsystem.com/pages/inst/epl6/manual_epl6_ENU.pdf |
| E-P5 man. | E-P5 manual | https://download.omsystem.com/pages/inst/ep5/manual_ep5_ENU.pdf |
| E-M1 man. | E-M1 manual with fw 2.0 / 3.0 / 4.0 addenda (p.166-179) | https://learning.omsystem.com/E-M1/zz_pdf/M1_ENU.pdf |
| E-M10 man. | E-M10 manual | https://download.omsystem.com/pages/inst/em10/manual_em10_ENU.pdf |
| E-PL7 man. | E-PL7 manual | https://learning.omsystem.com/E-PL7/zz_pdf/PL7_ENU.pdf |
| E-M5II man. | E-M5 II manual with fw 2.0 / 3.0 / 4.0 addenda (p.172-180) | https://download.omsystem.com/pages/inst/em5m2/manual_em5m2_ENU.pdf |
| E-M10II man. | E-M10 II manual | https://download.omsystem.com/pages/inst/em10m2/manual_em10m2_ENU.pdf |
| PEN-F man. | PEN-F manual with fw 2.0 / 3.0 addenda (p.179-182) | https://download.omsystem.com/pages/inst/penf/manual_penf_ENU.pdf |
| E-M1II man. | E-M1 II manual with fw 2.0 / 3.0 addenda (p.190-212) | https://download.omsystem.com/pages/inst/em1m2/manual_em1m2_ENU.pdf |
| E-M10III man. | E-M10 III manual | https://download.omsystem.com/pages/inst/em10m3/manual_em10m3_ENU.pdf |
| E-M1X man. | E-M1X manual (fw 2.0) | https://learning.omsystem.com/E-M1X/zz_pdf/E-M1X_ENU_02_FW200.pdf |
| E-M5III man. | E-M5 III manual | https://download.omsystem.com/pages/inst/em5m3/manual_em5m3_ENU.pdf |
| E-M1III man. | E-M1 III manual | https://download.omsystem.com/pages/inst/em1m3/manual_em1m3_ENU.pdf |
| E-M10IV man. | E-M10 IV manual | https://download.omsystem.com/pages/inst/em10m4/manual_em10m4_ENU.pdf |
| E-P7 man. | E-P7 manual | https://learning.omsystem.com/E-P7/zz_pdf/E-P7_ENU_00.pdf |
| OM-1 man. | OM-1 manual (fw 1.7) | https://learning.omsystem.com/OM-1/zz_pdf/OM-1_ENU_02_FW170.pdf |
| OM-5 man. | OM-5 manual | https://learning.omsystem.com/OM-5/zz_pdf/OM-5_ENU_00.pdf |
| OM-1II man. | OM-1 II manual (fw 1.2) | https://learning.omsystem.com/OM-1MarkII/zz_pdf/OM-1Mk2_ENU_03_FW120.pdf |
| OM-3 man. | OM-3 manual | https://learning.omsystem.com/OM-3/zz_pdf/OM-3_ENU_01.pdf |
| OM-5II man. | OM-5 II manual | https://learning.omsystem.com/OM-5MarkII/zz_pdf/OM-5Mk2_ENU_00.pdf |

Other pages opened:

- [IR-2.0] E-M1 fw 2.0 change list: https://old.imaging-resource.com/news/2014/09/19/firmware-friday-olympus-e-m1-update-lands-ahead-of-schedule-leica-updates-s
- [IR-4.0] E-M1 fw 4.0 and E-M5 II fw 2.0: https://www.imaging-resource.com/news/2015/09/15/olympus-breathes-new-life-into-e-m1-with-big-firmware-update-e-m5-ii-ga
- [EG-hist] E-M1 line firmware history thread: https://www.e-group.uk.net/forum/forum/cameras-lenses-and-system-accessories/camera-conference/802785-firmware-update-history-for-em-1-line-cameras-what-can-we-expect-now
- [PB-EP5] E-P5 fw 1.4 (14 May 2014): https://www.photographyblog.com/news/olympus_e_p5_firmware_update_1.4
- [SM-2014] E-M10 fw 1.1 and E-M1 fw 1.4 (21 May 2014): https://sansmirror.com/newsviews/2014-newsviews/april-june-2014-newsviews/olympus-firmware-updates.html
- [EPZ-2017] E-M1 II 1.2, E-M5 II 3.0, PEN-F 2.0 (8 May 2017): https://www.ephotozine.com/article/major-olympus-firmware-updates--30928
- [43R-2.0] E-M5 fw 2.0 (29 Jan 2014): https://www.43rumors.com/e-m5-special-kit-announced-and-new-e-m5-firmware-adds-iso-100/
- [DPR-EPM2] DPReview E-PM2 review, conclusion: https://www.dpreview.com/reviews/olympus-e-pm2/7
- [WP] Wikipedia: https://en.wikipedia.org/wiki/Olympus_PEN_E-P5 , https://en.wikipedia.org/wiki/Olympus_OM-D_E-M1 , https://en.wikipedia.org/wiki/Olympus_OM-D_E-M5_Mark_II , https://en.wikipedia.org/wiki/Olympus_OM-D_E-M10

### Headline findings

1. **The E-PL6 is the best donor.** It has the same sensor and TruePic VI. Its stock firmware has interval shooting with time-lapse movie, a level gauge with calibration, Movie Tele-converter, Release Lag-Time [Short] and ISO LOW (E-PL6 man. p.23, 65, 74, 80, 87-88, 120). The mod has already rebuilt two of these.
2. **The E-P5 is the second donor.** Same sensor, TruePic VI. It has peaking on a button, Photo Story, and Anti-Shock 0 s from fw 1.4 (E-P5 man. p.34, 84, 86; [PB-EP5]).
3. **One probe unlocks a family.** If the sensor can end an exposure by readout with the shutter open, then silent shutter, 1/16000 s, Live ND, Flicker Scan and Pro Capture become software work.
4. **Hard blocks are few and physical:** 1/8000 s shutter, 5-axis IS, on-sensor PDAF, 4K at video rates, 10-bit video, radios, USB charging, second card slot, dials and levers.

5. **Conflict to settle on the camera:** the row "Small single AF target" says ALREADY-HAS from E-PM2 manual p.35.
   `hardware.md` §7 lists it as an E-PL6 addition. See the note at the top of this file.

Columns: Feature | First body (year or firmware) | What it does | Hardware it needs | On the E-PM2? (hardware) | First judgement | Source.

### A1. Exposure and shutter

| Feature | First body | What it does | Hardware it needs | On the E-PM2? (hardware) | First judgement | Source |
|---|---|---|---|---|---|---|
| Live Bulb / Live Time | E-M5 (2012) | Shows the exposure building up on the screen. | Sensor read with shutter open. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.27, 74 |
| Anti-Shock 0 s (electronic first curtain) | E-M1 fw 1.3 (Mar 2014); E-M10 fw 1.1 and E-P5 fw 1.4 (May 2014); E-PL7 at launch | Starts the exposure without first-curtain shock. | Electronic exposure start on the sensor; mechanical rear curtain. | Same sensor as E-P5, so the sensor can do it (hw s.3, inferred). No code in the E-PM2. Stock Anti-Shock is a delay only (E-PM2 man. p.74). | NEEDS-PROBE. Probe: open the shutter as Live Time does, reset the sensor electronically, close the rear curtain after 1/100 s, check the frame exposure. Sister: E-P5 fw 1.4 (TruePic VI), E-M10, E-PL7. Note: some users say the 0 s mode is a short delay, not true EFC (search snippet, not verified). | [PB-EP5]; [SM-2014]; [EG-hist]; E-PL7 man. p.89 |
| Silent shutter (fully electronic) | E-M5 II (2015); E-M1 fw 4.0; E-M10 II | No shutter movement, no sound. | Electronic exposure start and end by sensor readout. | No body with this sensor shipped it. Live Time proves readout with the shutter open. Rolling readout about 1/40 s (hw s.3). | NEEDS-PROBE (unknown). Probe: end a Live Time exposure by sensor readout without closing the shutter and check the frame. No sister. | E-M5II man. p.59; E-M1 man. p.171; E-M10II man. p.58 |
| 1/8000 s mechanical | E-P5 (2013) | Faster top speed. | Faster shutter unit. | 1/4000 s unit (hw s.4). | HARDWARE-BLOCKED (verified). | E-P5 man. p.28, 132; E-PM2 man. p.116 |
| 1/16000 s electronic | E-M1 fw 4.0; E-M5 II | Short exposure by sensor timing. | Electronic shutter. | See silent shutter. | NEEDS-PROBE (same probe as silent shutter; exposure time is set by reset-to-read delay, inferred). | E-M1 man. p.172; [WP] E-M5 II |
| 1/32000 s electronic | E-M1X (2019) in the manuals I opened. E-M1 II: from memory, not verified. | Same, shorter. | Electronic shutter. | See silent shutter. | NEEDS-PROBE (same probe). | E-M1X man. p.94; E-M5III man. p.41 |
| Live Composite | E-M10 (2014); E-M1 fw 2.0; E-PL7 | Lighten-blend of repeated exposures with live preview. | Readout with shutter open; one accumulation buffer. | Live Time path exists. About 512 MiB RAM (hw s.2). Code absent, hardware inferred sufficient (hw s.3). | SOFTWARE-ONLY (inferred). Sister: E-M10, E-PL7. Not in E-P5 or E-PL6 (verified, no hit in their manuals). Building blocks: Live Time, 2-frame multiple exposure. | E-M10 man. p.42; E-M1 man. p.41, 166; E-PL7 man. p.36 |
| Live ND | E-M1X (2019) | Averages many short frames to imitate ND2 to ND32. OM-1 II goes to ND128. | Continuous electronic-shutter frames; RAM. | Depends on the silent-shutter probe. | NEEDS-PROBE (silent-shutter probe first; then it is Live Composite with a mean instead of a maximum, inferred). | E-M1X man. p.197; OM-1II man. p.244 |
| Live GND | OM-1 II (2024) | Graduated ND computed from a frame series, with soft/medium/hard edge. | Fast electronic readout; fast SoC for preview. | Depends on the silent-shutter probe. Preview speed unknown. | NEEDS-PROBE (same probe; preview frame rate unknown). | OM-1II man. p.246-247; OM-3 man. p.250 |
| High Res Shot (tripod) | E-M5 II (2015) | Eight shots with sub-pixel sensor shifts, merged. | Sensor-shift unit that can hold sub-pixel offsets; electronic shutter. | 2-axis IS with a separate H8 controller (hw s.4). | NEEDS-PROBE (unknown). Probe: command a static IS offset through the H8, shoot a tripod target twice, measure the shift in pixels. Merge time on MN103 is a second unknown. | E-M5II man. p.60 |
| High Res Shot (handheld) | E-M1X (2019); E-M1 III | Sixteen frames aligned from hand shake. | Fast burst, large RAM, fast SoC. | 10 fps full readout (hw s.3); 512 MiB RAM (hw s.2). | NEEDS-PROBE (unknown). Probe: hold 8 raw frames in RAM and time an align-and-merge on one MN103 core. | E-M1X man. p.152, 210; E-M1III man. p.83, 158 |
| Pro Capture | E-M1 II (2016) | Buffers frames from half-press, saves the ones before full press. | Electronic shutter at burst rate; ring buffer. | Depends on the silent-shutter probe. Movie pool 302 MiB (hw s.2). | NEEDS-PROBE (silent-shutter probe; rolling skew of about 1/40 s would limit use). | E-M1II man. p.46-48, 192 |
| In-camera HDR (HDR1 / HDR2) | E-M1 (2013); E-M10; E-PL7 | Four shots merged into one HDR JPEG. | Burst and merge buffer. None beyond a 2012 body (inferred). | AE bracketing and HDR BKT exist. | SOFTWARE-ONLY (inferred). Sister: E-M10, E-PL7. Not in E-P5 (verified, HDR BKT only). | E-M1 man. p.60-61; E-M10 man. p.81; E-PL7 man. p.78; E-P5 man. p.66 |
| HDR bracketing | E-PL5 / E-PM2 (2012) | Bracket series for HDR software. | None. | Present. Frame options not listed in the manual. | ALREADY-HAS (stock, verified; frame counts not verified). | E-PM2 man. p.63, 79 |
| AE bracketing up to 7 frames | E-PM2 (2012) | 2, 3, 5 or 7 frames. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.62 |
| WB / FL / ISO / ART bracketing | E-PM2 (2012) | Other bracket types. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.61-63 |
| Interval shooting | E-PL6 and E-P5 (2013): 99 frames. E-M1: 999. OM-1: 9999. | Timed series. | None. | Added by the mod. | ALREADY-HAS (mod). Sister: E-PL6. | E-PL6 man. p.65, 115; E-P5 man. p.69, 126; E-M1 man. p.85; OM-1 man. p.167 |
| Time-lapse movie | E-PL6 and E-P5 (2013) | Builds a movie from the series. | None. | Added by the mod. | ALREADY-HAS (mod). | E-PL6 man. p.65 |
| 4K time-lapse movie | E-M1 fw 4.0; E-M5 II fw 2.0; E-M10 II | 4K movie at 5 fps from stills. | Encoder path that accepts 3840x2160 frames at low rate. | Encoder ceiling unknown (hw s.5). | NEEDS-PROBE. Probe: feed one 3840x2160 frame to the time-lapse movie encoder path and see if it encodes. | E-M1 man. p.174; E-M10II man. p.87-88; [IR-4.0] |
| Multiple exposure (2 frames, overlay) | E-PM2 (2012) | Two frames, or RAW overlay. Newer bodies are the same. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.63-64 |
| ISO LOW (about ISO 100) | E-P5 and E-PL6 (2013); E-M5 fw 2.0 (Jan 2014) | Pulled ISO 200 for bright light. | None. | E-PM2 range is 200 to 25600. | SOFTWARE-ONLY (verified on sister). Sister: E-PL6, E-M5 fw 2.0. | E-PL6 man. p.120; [43R-2.0]; E-PM2 man. p.55, 116 |
| Auto ISO in M with exposure compensation | E-M1 II (fw addendum); E-M1X | Exposure compensation shifts auto ISO in M. | None. | Auto ISO in M exists ([ISO-Auto] = All). Exposure compensation is disabled in M. | SOFTWARE-ONLY (inferred). No sister. | E-M1II man. p.196; E-M1X man. p.103; E-PM2 man. p.32, 74 |
| Lowest shutter speed for auto ISO | PEN-F fw 2.0 (May 2017); E-M1 II | Sets the speed at which ISO starts to rise. | None. | Only [High Limit] and [Default]. | SOFTWARE-ONLY (inferred). No sister. | PEN-F man. p.181; E-M1II man. p.117; [EPZ-2017]; E-PM2 man. p.74 |
| Exposure compensation +/-5 EV | E-M1 (2013); E-M10 | Wider range. | None. | +/-3 EV. | SOFTWARE-ONLY (inferred). Sister: E-M10. | E-M1 man. p.152; E-M10 man. p.144; E-PM2 man. p.116 |
| Release Lag-Time [Short] | E-PL6 and E-P5 (2013) | Shorter delay from full press to exposure. | None. | Absent. | SOFTWARE-ONLY (verified on sister). Sister: E-PL6. | E-PL6 man. p.74, 117 |
| Spot highlight / spot shadow metering | E-PM2 (2012) | Spot metering biased up or down. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.53 |
| Spot metering linked to AF target | E-M5 II fw 3.0; PEN-F | Meters at the chosen AF target. | None. | Absent. | SOFTWARE-ONLY (inferred). No sister. | E-M5II man. p.179; PEN-F man. p.109 |
| Anti-flicker shooting | E-M1 II (fw addendum); E-M1X | Times the release to the peak of mains flicker. | Flicker phase from sensor or AE statistics. | AE statistics block exists (hw s.1). Live-view flicker reduction exists. | NEEDS-PROBE. Probe: sample the AE statistics block fast enough to see 100/120 Hz phase. | E-M1II man. p.201; E-M1X man. p.191; E-PM2 man. p.73 |
| Flicker Scan | E-M1 II fw 2.0 | Fine shutter-speed steps to remove LED banding. | Electronic shutter. | Depends on the silent-shutter probe. | NEEDS-PROBE (silent-shutter probe). | E-M1II man. p.194 |
| Flash RC mode, Super FP high-speed sync | E-PM2 (2012) | Wireless flash control; sync above X speed. | Supported flash. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.64, 109-110 |
| Custom self-timer with AF for each frame | E-M1 fw 2.0 | Refocus between self-timer frames. | None. | Custom self-timer exists without per-frame AF. | SOFTWARE-ONLY (inferred). | [IR-2.0]; E-PM2 man. p.61 |

### A2. Focus

| Feature | First body | What it does | Hardware it needs | On the E-PM2? (hardware) | First judgement | Source |
|---|---|---|---|---|---|---|
| Focus peaking (white / black) | E-P5 (2013) | Edge highlight for manual focus. | None. | Added by the mod with four colours, during MF Assist. | ALREADY-HAS (mod). Sister: E-P5. | E-P5 man. p.79, 84 |
| Peaking colours and intensity, image dimming | E-M5 II (2015); E-M1 fw 4.0 | Red and yellow, three strengths, darker live view under the edges. | None. | Colours done. Intensity and dimming absent. | SOFTWARE-ONLY (inferred). | E-M5II man. p.103, 155; E-M1 man. p.175-176, 179 |
| Peaking on a button, for any lens and AF mode | E-P5 (2013) | Toggle peaking without turning the focus ring. Works with adapted lenses. | None. | Mod shows peaking only in MF Assist. | SOFTWARE-ONLY (inferred). Sister: E-P5. | E-P5 man. p.86 |
| Peaking while recording video | E-M1 II (2016) in the manuals I opened. E-M5 II: from memory, not verified. | Peaking in movie mode. | Live-view processing during encode. | Art-engine live-view pipeline exists. CPU budget during encode unknown. | NEEDS-PROBE. Probe: leave the peaking hook on during REC and count dropped frames. | E-M1II man. p.66; OM-1 man. p.67 |
| Magnify / zoom frame AF (5x to 14x) | E-PM2 (2012) | Enlarged view and small-area AF. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.85 |
| 3x magnify; level and histogram in magnified view | E-M1 fw 2.0 | Lower zoom step; aids stay on screen. | None. | Absent. | SOFTWARE-ONLY (inferred). | [IR-2.0] |
| Small single AF target | E-PL5 / E-PM2 (2012); E-M5 fw 2.0 | Smaller AF box. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.35; [43R-2.0] |
| Group target | E-PM2 (2012) | Camera picks inside a group. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.35 |
| 5 / 9 / 25-point and custom AF target modes | E-M1 II (2016); custom shapes E-M1X (2019) | User-sized AF areas. | On-sensor PDAF grid in the bodies that ship it. | Contrast AF, 35 areas. AF statistics block (hw s.1). | NEEDS-PROBE. Probe: check if the AF statistics block accepts an arbitrary window size and position. | E-M1II man. p.39, 196; E-M1X man. p.125 |
| AF Targeting Pad | E-M10 II (2015) | Drag the AF point on the screen while using the EVF. | Touch screen and EVF. | Touch screen yes. EVF only as VF-2/3/4 (hw s.4). | SOFTWARE-ONLY (inferred). Useful only with a VF accessory. | E-M10II man. p.100 |
| Touch AF and touch shutter | E-PM2 (2012) | Tap to focus or shoot. | Touch screen. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.42-43 |
| Face and eye priority (near / left / right eye) | E-PM2 (2012) | Face and pupil detection AF. | Face detector. | Hardware face detector (hw s.1). Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.55 |
| Face selection button | E-M1 III (2020) | Choose which detected face to focus. | Face detector that reports several faces. | Face detector present. Multi-face output not verified. | SOFTWARE-ONLY (inferred). | E-M1III man. p.93, 122 |
| Subject detection AF (cars, trains, aircraft, birds, animals; humans on OM-1 II) | E-M1X (2019); birds by fw 2.0 | Neural-network subject detection and tracking. | Fast SoC. Olympus shipped it only on dual TruePic VIII and later (from memory, not verified). | Two MN103 cores, an OpenGL ES 1.1 GPU, a face-only detector (hw s.1). | NEEDS-PROBE (unknown, low expectation). Probe: time a very small classifier on one live-view frame on one MN103 core. | E-M1X man. p.149; OM-1 man. p.90; OM-1II man. p.120; [EG-hist] |
| C-AF and C-AF+TR tracking | E-PM2 (2012) | Continuous and tracking AF. | Contrast AF. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.54 |
| C-AF Lock / C-AF sensitivity | E-M1 (2013) | Sets how fast C-AF reacts to distance jumps. | Tuned for PDAF. | Contrast AF only. | SOFTWARE-ONLY (inferred; benefit on contrast AF unknown). | E-M1 man. p.93 |
| AF Focus Adjust (PDAF micro-adjust) | E-M1 (2013) | Per-lens PDAF calibration. | On-sensor PDAF. | No on-sensor PDAF (hw s.3). | HARDWARE-BLOCKED (verified; not needed for contrast AF). | E-M1 man. p.110 |
| AF Limiter | E-M1 II (2016) | Restricts the focus range. | Lens distance reporting. | Lens protocol reports focus position (inferred). | SOFTWARE-ONLY (inferred). No sister. | E-M1II man. p.69, 111 |
| Preset MF | E-M1 II (2016) | Jumps to a stored focus distance. | Lens focus drive. | [Reset Lens] already drives focus to infinity. | SOFTWARE-ONLY (inferred). No sister. | E-M1II man. p.44, 112; E-PM2 man. p.71 |
| MF Clutch disable | E-M1 fw 4.0; E-M5 II fw 2.0 | Ignores the snap-focus ring on some lenses. | Lens firmware support. | Absent. | SOFTWARE-ONLY (inferred). | E-M1 man. p.175; [IR-4.0] |
| Focus Ring Lock | E-M1 III (2020) | Button disables the focus ring. | None. | Absent. | SOFTWARE-ONLY (inferred). | E-M1III man. p.122 |
| Starry Sky AF | E-M1 III (2020) | Autofocus on stars. | Enough live-view signal on stars; scan algorithm. | CPU access to the live-view buffer; Live View Boost exists. | NEEDS-PROBE. Probe: grab the live-view buffer on a star field at f/1.8 with boost on and check that stars rise above noise. | E-M1III man. p.64, 66; OM-5 man. p.121 |
| Focus bracketing | E-M10 II (2015); E-M1 fw 4.0; E-M5 II fw 2.0 | Steps focus between shots, 3 to 999 frames. | Lens focus stepping. | Contrast AF already steps the lens. AE bracketing loop exists. | SOFTWARE-ONLY (inferred). No TruePic VI sister. | E-M10II man. p.88; E-M1 man. p.173; E-M5II man. p.174 |
| In-camera focus stacking | E-M1 fw 4.0 | Eight focus steps merged into one JPEG. | Electronic shutter in stock; merge buffer and CPU. | 512 MiB RAM (hw s.2). | NEEDS-PROBE. Probe: time an 8-frame sharpness merge at 16 MP on the MN103. Bracketing alone does not need this. | E-M1 man. p.174; E-M5II man. p.180 |
| BULB/TIME focusing, focus ring direction, Full-time AF | E-PM2 (2012) | Small focus options. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.71 |
| Focus distance indicator | E-M1X fw 2.0 | Shows the focus distance on screen. | Lens distance reporting. | Not shown. | SOFTWARE-ONLY (inferred). | [EG-hist] |

### A3. Computational and geometry

| Feature | First body | What it does | Hardware it needs | On the E-PM2? (hardware) | First judgement | Source |
|---|---|---|---|---|---|---|
| Keystone compensation | E-M1 fw 2.0 (Sep 2014) | Live perspective correction, saved in the JPEG. | Image warp stage. | GPU and art engine (hw s.1). Lens distortion correction implies a warp stage (inferred). | NEEDS-PROBE. Probe: load a projective map into the distortion-correction table and check live view and the JPEG. | E-M1 man. p.86, 174; [IR-2.0] |
| Fisheye compensation | E-M1 II fw 2.0 | De-fishes the 8 mm f/1.8. | Image warp stage. | As above. | NEEDS-PROBE (same warp probe). | E-M1II man. p.194 |
| Digital Tele-converter (2x stills) | E-PM2 (2012) | Centre crop, upscaled. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.64 |
| Hand-Held Starlight scene | E-M1 / E-M10 (2013-14) | Eight frames merged for low noise. | Burst and merge. | Not in the E-PM2 scene list. | SOFTWARE-ONLY (inferred; merge time unknown). Sister: E-M10, E-PL7. | E-M1 man. p.22; E-M5III man. p.51; E-PM2 man. p.29 |
| In-camera panorama stitch | E-M10 III (2017) | Sweeps and stitches. | Burst and stitch CPU. | E-PM2 panorama is framing assist only. | NEEDS-PROBE. Probe: time a strip stitch on the MN103. | E-M10III man. p.38; E-PM2 man. p.29-30 |
| e-Portrait | E-PM2 (2012) | Skin smoothing. | Face detector. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.29, 66 |
| Handheld Assist | OM-1 (2022); OM-5 II | Shows camera motion against the IS limit during a long exposure. | Gyro or IS position readable by the main CPU; OSD. | IS runs on a separate H8 (hw s.4). OSD plane (hw s.1). | NEEDS-PROBE. Probe: read gyro or IS position from the H8 at live-view rate. | OM-1 man. p.139; OM-5II man. p.217 |
| Computational Modes menu / CP button | OM-1 (menu, 2022); OM-3 and OM-5 II (CP button, 2025) | One place for High Res, Live ND, stacking, HDR, multi exposure. | None. | Menu tables take new rows. | SOFTWARE-ONLY (inferred). Only useful after the features exist. | OM-1 man. p.63, 156; OM-3 man. p.350, 381; OM-5II man. p.340 |

### A4. Looks and colour

| Feature | First body | What it does | Hardware it needs | On the E-PM2? (hardware) | First judgement | Source |
|---|---|---|---|---|---|---|
| Twelve art filters (Pop Art to Watercolor) | E-PM2 (2012) | Stock filter set. | Art engine. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.28 |
| Seven film looks | Mod | Colour matrix, tone and chroma curves, six-axis hue. | Art engine. | Added by the mod. | ALREADY-HAS (mod). | this repo, README |
| Vintage art filter | E-PL7 (2014); E-M1 fw 2.0 | Faded print look. | Art engine. | Curves and matrix are in the mod. | SOFTWARE-ONLY (inferred). Sister: E-PL7. | E-PL7 man. p.44; E-M1 man. p.44, 166 |
| Partial Color art filter | E-PL7 (2014); E-M1 fw 2.0 | Keeps one hue, rest monochrome, hue chosen on a ring. | Hue-selective saturation. | Six-axis hue is in the mod. | SOFTWARE-ONLY (inferred). Sister: E-PL7. | E-PL7 man. p.44-45 |
| Bleach Bypass art filter | E-M10 III (2017); PEN-F fw 3.0; E-M1 II fw 2.0 | Low saturation, high contrast. | Art engine. | Curves are in the mod. | SOFTWARE-ONLY (inferred). | E-M10III man. p.43; PEN-F man. p.182 |
| Instant Film art filter | E-M1 II (fw addendum); E-M10 IV | Instant-print tones. | Art engine. | Curves are in the mod. | SOFTWARE-ONLY (inferred). | E-M1II man. p.196; E-M10IV man. p.52 |
| Color Creator | E-M1 (2013); E-M10 | Global hue and saturation on a colour ring. | Colour matrix. | Engine present; no UI. | SOFTWARE-ONLY (inferred). Sister: E-M10. Not in E-P5 or E-PL7 (verified). | E-M1 man. p.60; E-M10 man. p.54 |
| Color Profile Control | PEN-F (2016); E-P7; OM-3 | Saturation of twelve hues, +/-5 each, three stored profiles. | Twelve-sector hue control. | Mod uses a six-axis hue control. | NEEDS-PROBE. Probe: check if the colour engine has more than six hue sectors or a 3D LUT stage. | PEN-F man. p.39; E-P7 man. p.51-52; OM-3 man. p.225 |
| Monochrome Profile Control | PEN-F (2016); E-P7; OM-3 | Colour filter strength, shading and grain for B&W. | None new. | B&W filter, Pin Hole and Grainy Film exist. | SOFTWARE-ONLY (inferred). | PEN-F man. p.40; E-P7 man. p.46-49; E-PM2 man. p.28, 60 |
| Film Grain Effect (off / low / medium / high) | PEN-F (2016) | Grain overlay as a picture-mode option. | Grain generator. | Grainy Film filter exists. | SOFTWARE-ONLY (inferred). | PEN-F man. p.66; E-P7 man. p.107 |
| Shading Editor (vignette, + and -) | PEN-F (2016); extended in fw 3.0 | Adjustable edge darkening or brightening. | Shading stage. | Pin Hole filter and Shading Comp. exist. | SOFTWARE-ONLY (inferred). | PEN-F man. p.40, 182; E-PM2 man. p.28, 75 |
| Highlight & Shadow control | E-PM2 (2012) | Two-point tone control on the screen. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.32 |
| Midtone control | PEN-F (2016); E-M5 II fw 3.0 | Third tone point. | None. | Tone curves are in the mod. | SOFTWARE-ONLY (inferred). | PEN-F man. p.39; E-M5II man. p.179 |
| Creative dial | PEN-F (2016); OM-3 (2025) | Front dial for mono, colour, art, Color Creator. | Physical dial. | No such dial. | HARDWARE-BLOCKED for the dial (verified). The functions behind it are the rows above. | PEN-F man. p.38; OM-3 man. p.219 |
| Photo Story | E-P5 (2013) | Multi-frame collage in camera. | None. | Absent. | SOFTWARE-ONLY (verified on sister). Sister: E-P5 (TruePic VI). | E-P5 man. p.34-35 |
| Flat picture mode for video | E-M5 II fw 2.0 | Low-contrast look for grading. | None. | Tone curves are in the mod. | SOFTWARE-ONLY (inferred). | [IR-4.0] |
| OM-Log400 | E-M1X (2019); E-M1 II fw 3.0 | Log curve for grading. | None for the curve. | 8-bit H.264 at 20 Mb/s limits the gain (hw s.5, inferred). | SOFTWARE-ONLY (inferred). | E-M1X man. p.393; [EG-hist] |
| HLG / 10-bit H.265 | OM-1 (2022) | 10-bit HDR video. | 10-bit HEVC encoder. | H.264 High profile, 8-bit (hw s.5). | HARDWARE-BLOCKED (inferred from the encoder profile). | OM-1 man. p.144 |
| OM-Cinema1 / OM-Cinema2 | OM-3 and OM-5 II (2025) | Movie looks. | None for the curve. | Tone curves are in the mod. | SOFTWARE-ONLY (inferred). | OM-3 man. p.78, 165; OM-5II man. p.176 |
| sRGB / AdobeRGB, Keep Warm Color, Pict. Tone, B&W filter | E-PM2 (2012) | Colour options. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.60, 76 |

### A5. Video

| Feature | First body | What it does | Hardware it needs | On the E-PM2? (hardware) | First judgement | Source |
|---|---|---|---|---|---|---|
| 1080p60 / 50 | E-M5 II (2015) | Double frame rate. | 1080-line sensor mode at 60 fps; encoder throughput. | 1080 window at 30 fps. Decimated 60 fps mode exists for AF. No 1080p60 record (hw s.3). | NEEDS-PROBE. Probe: route the 60 fps AF sensor mode into the movie path, read its line count, see if the encoder keeps up. 720p60 is the likelier result. | E-M5II man. p.19-20, 44 |
| 24p / 25p | E-M5 II (2015); E-M1 fw 4.0 | Cinema and PAL rates. | Sensor frame timing; encoder timebase. | 30 fps only. | NEEDS-PROBE. Probe: change the sensor frame period in the 1080 window mode to 1/25 s and 1/24 s; check AE and the file timebase. | [IR-4.0]; E-M1 man. p.170; [WP] E-M5 II |
| All-Intra | E-M5 II (2015) | Intra-only H.264. | Encoder GOP setting and bitrate headroom. | I+P encoder; limits are software; ceiling unknown (hw s.5). Card about 28 MB/s (hw s.6). | NEEDS-PROBE. Probe: set GOP length 1 and raise the rate target; watch for overflow. | E-M5II man. p.39, 108 |
| Higher bitrate (up to 77 Mb/s) | E-M5 II (2015) | Less compression. | Encoder and card speed. | 20 Mb/s nominal, QP floor 20 (hw s.5). | NEEDS-PROBE. Probe: lower the QP floor and raise the rate target in steps. | [WP] E-M5 II; E-M5II man. p.108 |
| No 29-minute limit | Later OM bodies; first body: from memory, not verified | Longer clips. | Heat margin. | Timer is a software limit (hw s.5). Heat unknown. | SOFTWARE-ONLY (inferred; heat behaviour unknown). | E-PM2 man. p.52 |
| 4K / C4K video | E-M1 II (2016) | 3840x2160 and 4096x2160. | 4K sensor readout at 24 to 30 fps; 4K encoder. | Full readout at 10 fps; no 4K mode (hw s.3). | HARDWARE-BLOCKED at video rates (verified from the sensor mode list). | E-M1II man. p.36; E-M10III man. p.53, 75 |
| High-speed movie 120 fps | E-M10 II (2015), at SD quality | Slow motion. | 120 fps sensor mode routed to the encoder. | Decimated 120 and 240 fps AF modes exist (hw s.3). | NEEDS-PROBE. Probe: route the 120 fps AF mode to the encoder at 640x480 and check the image. | E-M10II man. p.44 |
| Slow / quick motion | E-M5 II (2015) | Records at one rate, plays at another. | None for quick motion. | Time-lapse movie is in the mod. | SOFTWARE-ONLY for quick motion (inferred). Slow motion depends on the two probes above. | E-M5II man. p.44 |
| Movie Tele-converter | E-PL6 and E-P5 (2013) | 1:1 crop zoom at a touched position during recording. | Sensor window. | Absent. | SOFTWARE-ONLY (verified on sister). Sister: E-PL6 (TruePic VI). | E-PL6 man. p.87-88; E-P5 man. p.29-30 |
| Movie effects: Multi Echo, One Shot Echo, Art Fade | E-PM2 (2012) | Live effects. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.86 |
| Old Film movie effect | E-M1 fw 2.0 | Scratches and flicker. | None. | Absent. | SOFTWARE-ONLY (inferred). | [IR-2.0] |
| My Clips | E-M5 II (2015) | Short clips joined in camera. | None. | Absent. | SOFTWARE-ONLY (inferred). | E-M5II man. p.42-43 |
| P / A / S / M movie exposure | E-PM2 (2012) | Manual movie exposure. | None. | Present. No auto ISO in movie M. | ALREADY-HAS (stock, verified). | E-PM2 man. p.48 |
| Time code | E-M5 II (2015); E-M1 fw 4.0 | Time code in the file, drop or non-drop. | None. | Absent. | SOFTWARE-ONLY (inferred). | E-M5II man. p.108; E-M1 man. p.177 |
| Histogram and audio meters during recording | E-M5 II (2015); E-M1 fw 4.0 | Overlays while recording. | OSD. | OSD plane (hw s.1). | SOFTWARE-ONLY (inferred). | E-M5II man. p.20; [IR-4.0] |
| Zebra pattern | OM-1 (2022) | Stripes over two luminance thresholds in movie mode. | Live-view processing. | Highlight & Shadow blink display exists for stills live view. | SOFTWARE-ONLY for live view (inferred). During REC it shares the peaking-in-video probe. | OM-1 man. p.184; E-PM2 man. p.84 |
| Sensor-shift movie IS | E-M5 (2012); first body from memory, not verified | Mechanical IS while recording. | IS unit rated for continuous use. | E-PM2 movie IS is electronic and crops. 2-axis unit (hw s.4). | NEEDS-PROBE. Probe: keep the H8 IS loop running during REC; check heat, battery drain and motor noise. | [DPR-EPM2]; E-PM2 man. p.46, 48; E-M5II man. p.57 |
| 5-axis IS / 5-axis Sync IS | E-M5 (2012) for 5-axis: from memory, not verified. Sync IS improved in E-M5 II fw 3.0. | Roll and shift correction; lens and body together. | 5-axis VCM unit. | 2-axis, no roll (hw s.4). | HARDWARE-BLOCKED (verified). | [EPZ-2017]; [WP] E-P5 |
| External mic | E-M1 (2013) with a jack | Better audio. | Mic jack. | Only by SEMA-1 on the accessory port (hw s.4). Recording volume and wind filter exist. | ALREADY-HAS (accessory, stock). | E-M1 man. p.76; E-PM2 man. p.77 |
| Headphone monitoring | E-M5 II (2015, on the HLD-8G grip); E-M1 II (jack) | Audio monitoring. | Headphone jack. | None (hw s.4). | HARDWARE-BLOCKED (verified). | E-M5II man. p.101; E-M1II man. p.10 |
| PCM recorder link and slate tone | E-M1 fw 4.0; E-M5 II fw 2.0 | Controls an LS-100 over USB and writes a sync tone. | USB host. | USB device only (hw s.4). | HARDWARE-BLOCKED for the link (verified). A slate tone alone is SOFTWARE-ONLY (inferred). | E-M1 man. p.175, 177; E-M5II man. p.175 |
| HDMI output while shooting (monitor or record mode) | E-M1 II (2016) in the manuals I opened. E-M5 II: from memory, not verified. | Live picture on an external monitor or recorder. | HDMI transmitter fed from live view. | HDMI micro, playback only in stock (hw s.4). | NEEDS-PROBE. Probe: switch the HDMI transmitter on in shooting mode and route the live-view plane to it. | E-M1II man. p.100-101 |
| RAW video over HDMI | E-M1X fw 2.0; E-M1 III fw 1.2; OM-1 | 4K ProRes RAW on a recorder. | 4K sensor readout at video rates. | No 4K mode (hw s.3). | HARDWARE-BLOCKED (verified from the sensor mode list). | E-M1X man. p.686-687; E-M1III man. p.326; OM-1 man. p.182 |
| Vertical video | OM-5 (2022) | Stores the orientation so the clip plays upright. | Orientation sensor. | 3-axis accelerometer (hw s.4). | SOFTWARE-ONLY (inferred: write the rotation in the MOV header). | OM-5 man. p.82 |
| Electronic zoom speed | E-M1 fw 2.0 | Speed of power-zoom lenses. | Power-zoom lens. | Absent. | SOFTWARE-ONLY (inferred). | [IR-2.0]; E-M1II man. p.100 |

### A6. Display aids

| Feature | First body | What it does | Hardware it needs | On the E-PM2? (hardware) | First judgement | Source |
|---|---|---|---|---|---|---|
| Level gauge with calibration | E-M5 (2012); E-PL6 (2013) | Two-axis level. | Accelerometer. | Added by the mod, with calibration. | ALREADY-HAS (mod). Sister: E-PL6 has stock code. | E-M5 man. p.39; E-PL6 man. p.23, 80 |
| Histogram with highlight and shadow limits | E-PM2 (2012) | Live and playback histogram. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.73, 84 |
| Highlight & Shadow blink display | E-PM2 (2012) | Red and blue clipping overlay. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.84 |
| Displayed grid | E-PM2 (2012) | Framing grids. Later bodies add colour and more patterns. | None. | Present; extras absent. | ALREADY-HAS (stock). Extras: SOFTWARE-ONLY (inferred). | E-PM2 man. p.73 |
| Live View Boost | E-PM2 (2012) | Bright view that ignores exposure settings. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.73 |
| Live View Boost II (On2) | E-M5 II (2015); E-M1 fw 4.0 | Long live-view integration for very dark scenes; slower response. | Longer live-view exposure; noise reduction. | Temporal NR block (hw s.1). | NEEDS-PROBE. Probe: set a live-view exposure longer than one frame period and see if the sensor mode accepts it. | E-M5II man. p.102, 155; E-M1 man. p.176 |
| Night Vision | OM-1 (2022); OM-3; OM-5 II | Dim red display for dark-adapted eyes. | None. | Display colour is under mod control (inferred). | SOFTWARE-ONLY (inferred). | OM-1 man. p.225; OM-5II man. p.355 |
| S-OVF | E-M1 fw 4.0; E-M10 II | Wide-range live view without exposure simulation. | None; made for the EVF. | No built-in EVF. Works on the LCD or a VF accessory (inferred). | SOFTWARE-ONLY (inferred). | E-M1 man. p.178; E-M10II man. p.66 |
| Preview and Test Picture | E-PM2 (2012) | Stop-down preview; shot shown but not saved. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.79 |
| Aperture lock on preview | E-M1 fw 2.0 | Preview stays on after release of the button. | None. | Absent. | SOFTWARE-ONLY (inferred). | [IR-2.0] |
| Bulb/Time monitor brightness | E-M1 (2013) | Dims the screen during long exposures. | None. | Absent. | SOFTWARE-ONLY (inferred). | E-M1 man. p.41; PEN-F man. p.109 |
| Live SCP / Live Control | E-PM2 (2012) | On-screen control panels. | None. | Present. Touch cannot change SCP values. | ALREADY-HAS (stock, verified). | E-PM2 man. p.83; [DPR-EPM2] |
| Touch control on the Super Control Panel | E-M1 fw 2.0 (double tap) | Set SCP items by touch. | Touch screen. | Touch screen present. | SOFTWARE-ONLY (inferred). | [IR-2.0] |
| Selfie assist | E-PL7 (2014) | Flip-screen self-portrait UI. | Flip screen. | Fixed screen. | HARDWARE-BLOCKED (verified). | E-PL7 man. p.19; [DPR-EPM2] |

### A7. UI and customisation

| Feature | First body | What it does | Hardware it needs | On the E-PM2? (hardware) | First judgement | Source |
|---|---|---|---|---|---|---|
| Mysets (four) | E-PM2 (2012) | Saved setting sets, recalled by menu or by holding a button. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.59, 79 |
| Custom modes C1 to C4 on the mode dial | PEN-F (2016) | Mysets as shooting modes. | Mode dial. | No mode dial; modes are chosen on screen. | SOFTWARE-ONLY (inferred: add Mysets to the on-screen mode menu). | PEN-F man. p.33, 180; [DPR-EPM2] |
| Save settings to a computer | E-M5 II fw 3.0; PEN-F fw 2.0 | Backup and restore of all settings. | USB app in stock. | Card file read/write is a mod building block. | SOFTWARE-ONLY (inferred: save to a card file). | [EPZ-2017] |
| My Menu | E-M1X (2019) | User-built menu tab. | None. | Menu tables take new rows. | SOFTWARE-ONLY (inferred). | E-M1X man. p.477; E-M1III man. p.179 |
| Menu Recall | E-M1 fw 4.0 | Menu reopens at the last item. | None. | Absent. | SOFTWARE-ONLY (inferred). | E-M1 man. p.176; [IR-4.0] |
| Multi Function button | E-M5 (2012); E-M1 | One button cycles tone control, Color Creator, ISO/WB, magnify, aspect. | None. | Absent. | SOFTWARE-ONLY (inferred). Sister: E-M5. | E-M5 man. p.93; E-M1 man. p.23 |
| Extra button functions (Peaking, AE BKT, ART BKT) | E-P5 (2013) | More choices for Fn buttons. | None. | E-PM2 list lacks them. | SOFTWARE-ONLY (inferred). Sister: E-P5. | E-P5 man. p.86; E-PM2 man. p.79 |
| L-Fn lens button | E-PM2 (2012) | Lens button role. | Lens with L-Fn. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.78 |
| Dial function and direction | E-PM2 (2012) | Role of the one control dial. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.71-72 |
| 2x2 lever | E-P5 (2013) | Lever swaps dial and button roles. | Physical lever. | No lever. | HARDWARE-BLOCKED for the lever (verified). A button toggle is SOFTWARE-ONLY (inferred). | E-P5 man. p.86; E-M1 man. p.105 |
| Lens Info Settings | PEN-F (2016) | Stores name, focal length and aperture for ten legacy lenses; writes EXIF. | None. | Absent. | SOFTWARE-ONLY (inferred). | PEN-F man. p.114, 129; E-M1II man. p.132 |
| IS focal length input for legacy lenses | E-PM2 (2012) | 8 to 1000 mm. | IS unit. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.46 |
| Copyright info, dpi setting, edit filename | E-PM2 (2012) | EXIF and file options. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.76-77 |
| Pixel mapping, dust reduction | E-PM2 (2012) | Sensor maintenance. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.77, 103 |
| World time / time zone | E-M1X (2019) | Time zone and daylight saving. | None. | Absent. | SOFTWARE-ONLY (inferred). | E-M1X man. p.46; OM-1 man. p.257 |
| Quick Sleep Mode | E-M5 II (2015) | Aggressive sleep while using the viewfinder. | None. | Sleep and backlight timers exist. | SOFTWARE-ONLY (inferred). | E-M5II man. p.110; E-PM2 man. p.73 |
| Night-friendly power options (eco mode) | OM-1 (2022) | Lower power draw. | None. | Absent. | SOFTWARE-ONLY (inferred; not checked in detail). | OM-1 man. p.254-255 |

### A8. Connectivity and power

| Feature | First body | What it does | Hardware it needs | On the E-PM2? (hardware) | First judgement | Source |
|---|---|---|---|---|---|---|
| Built-in Wi-Fi remote and transfer (OI.Share) | E-P5 (2013) | Phone remote with live view; image transfer. | Wi-Fi radio. | No radio (hw s.4). | HARDWARE-BLOCKED (verified). | E-P5 man. p.103-105 |
| FlashAir / Eye-Fi transfer | E-PM2 (2012) | Card-based Wi-Fi transfer. | Wi-Fi card. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.68, 78 |
| Remote release through a FlashAir card | None (mod idea) | Phone triggers the shutter. | Card that lets a script write a file the camera can poll. | Card file read/write is a mod building block. | NEEDS-PROBE. Probe: have a FlashAir script write a trigger file; poll it from the mod; measure the delay. | E-PM2 man. p.68 |
| PENPAL Bluetooth image sharing | E-PM2 (2012) | Classic Bluetooth transfer on the accessory port. | PENPAL unit. | Present. | ALREADY-HAS (accessory, stock). | E-PM2 man. p.88 |
| Bluetooth LE (wake, power-off standby) | E-M1X and E-M5 III (2019) | Phone wakes the camera. | BLE radio. | None (hw s.4). | HARDWARE-BLOCKED (verified). | E-M5III man. p.26; E-M1X man. p.586 |
| GPS tag from a phone log | E-P5 (2013) | Adds position from a phone track. | Wi-Fi in stock. | No radio. | HARDWARE-BLOCKED as shipped. Reading a track file from the card is SOFTWARE-ONLY (inferred). | E-P5 man. p.105 |
| Field sensors (GPS, barometer, compass, thermometer) | E-M1X (2019) | Logs position and climate data. | The sensors. | None (hw s.4). | HARDWARE-BLOCKED (verified). | E-M1X man. p.568 |
| Tethered shooting (OLYMPUS Capture, OM Capture) | E-M1 fw 2.0 | PC controls the camera and receives files. | USB capture protocol. | USB 2.0 device, PTP without capture, vendor debug shell (hw s.4). | NEEDS-PROBE. Probe: fire the shutter from a PC through the vendor debug shell; then try a PTP capture opcode handler. | [IR-2.0]; E-M1 man. p.167; E-M1X man. p.582 |
| Webcam (UVC) | OM-5 (2022); OM-1 II; OM-3; OM-5 II | Camera appears as a USB webcam. | USB device controller with a video-class interface. | USB 2.0 device controller; endpoint limits unknown. | NEEDS-PROBE. Probe: present a UVC descriptor and stream live-view JPEG frames on a bulk endpoint. | OM-5 man. p.339, 374; OM-1II man. p.405, 466 |
| USB charging | E-M5 III (2019); E-M10 IV (2020). Not on E-M10 III. | Charges the battery in the body. | Charge circuit. | None; BLS-5 with an external charger (hw s.4). | HARDWARE-BLOCKED (verified). | E-M5III man. p.18; E-M10IV man. p.17; E-M10III man. p.14 |
| USB Power Delivery | E-M1X (2019) | Runs the camera from USB PD. | PD controller, USB-C. | None (hw s.4). | HARDWARE-BLOCKED (verified). | E-M1X man. p.34, 625 |

### A9. Playback and files

| Feature | First body | What it does | Hardware it needs | On the E-PM2? (hardware) | First judgement | Source |
|---|---|---|---|---|---|---|
| In-camera RAW Data Edit | E-PM2 (2012) | Develop RAW with current or custom settings. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.65 |
| RAW edit with mod looks | Mod idea; E-P5 "enhanced in-camera RAW conversion" | Re-develop a RAW with a film look. | None. | Depends on whether the playback develop path uses the art-engine hooks. | NEEDS-PROBE. Probe: run RAW Data Edit with a film-look slot selected and compare the output. | [WP] E-P5 |
| JPEG Edit (shadow, red-eye, crop, aspect, B&W, sepia, saturation, resize, e-Portrait) | E-PM2 (2012) | Retouch in camera. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.66 |
| Image overlay (up to 3 RAW) | E-PM2 (2012) | Blend RAW files with gain. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.67 |
| Voice memo (30 s) | E-PM2 (2012) | Audio note on a picture. | Mic. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.40 |
| Star ratings | OM-1 (2022) | One to five stars written to the file. | None. | Absent. | SOFTWARE-ONLY (inferred). | OM-1 man. p.196-197 |
| Movie trimming | E-M10 III (2017); E-M1 II | Cut the ends of a clip. | None. | Absent. | SOFTWARE-ONLY (inferred: cut at I-frames). | E-M10III man. p.104-106; E-M1II man. p.108 |
| In-movie image capture | E-M1 II (2016) | Save a 4K frame as a still. | 4K video. | No 4K. | HARDWARE-BLOCKED for 4K. A 1080 frame grab is SOFTWARE-ONLY (inferred). | E-M1II man. p.107 |
| Dual card slots | E-M1 II (2016) | Backup or overflow recording. | Second slot. | One slot. | HARDWARE-BLOCKED (verified). | E-M1II man. p.15, 132 |
| Quick Erase, RAW+JPEG erase, slideshow with BGM | E-PM2 (2012) | Playback options. | None. | Present. | ALREADY-HAS (stock, verified). | E-PM2 man. p.41, 76 |
| 14-bit RAW | OM-1 II (2024) | Deeper RAW in High Res mode. | Sensor and pipeline bit depth. | Not in hardware.md. | Unknown. No judgement. | OM-1II man. p.240 |


Counts: ALREADY-HAS 46, SOFTWARE-ONLY 63, NEEDS-PROBE 34, HARDWARE-BLOCKED 19, no judgement 1 (some rows hold more than one feature).

## (d) Community wish list (2012 to 2015 bodies)

### What I could open

Most forums refused the fetch (HTTP 403): dpreview forums, getdpi, cambridgeincolour, fredmiranda, petapixel. For those I used search-result snippets and say so. I found **no thread about E-PM2 or E-PL5 firmware wishes** on dpreview, mu-43 or reddit. The evidence below is mostly about the E-M5 and E-M1, which share the sensor generation.

Opened:

- [W1] EOSHD forum, "Olympus E-M1 firmware update to address video mode - but will we get 24p and higher bitrates?" (15 Feb 2014), page 1: https://www.eoshd.com/comments/topic/5035-olympus-e-m1-firmware-update-to-address-video-mode-but-will-we-get-24p-and-higher-bitrates/
- [W2] Same thread, page 2: https://www.eoshd.com/comments/topic/5035-olympus-e-m1-firmware-update-to-address-video-mode-but-will-we-get-24p-and-higher-bitrates/page/2
- [W3] 43rumors, E-M5 firmware 2.0 post (29 Jan 2014; 141 comments, comment text not served): https://www.43rumors.com/e-m5-special-kit-announced-and-new-e-m5-firmware-adds-iso-100/
- [W4] CY Leow blog, "FOCUS PEAKING feature HIDDEN in OM-D EM-5!" (26 Oct 2012), the Key Line art-filter workaround: https://cyleow.blogspot.com/2012/10/focus-peaking-feature-hidden-in-om-d-e.html
- [W5] e-group.uk.net, E-M1 line firmware history and wishes (to 2021): https://www.e-group.uk.net/forum/forum/cameras-lenses-and-system-accessories/camera-conference/802785-firmware-update-history-for-em-1-line-cameras-what-can-we-expect-now
- [W6] talkphotography.co.uk OM-D owners thread, page 426: https://www.talkphotography.co.uk/threads/olympus-om-d-e-m5-e-m1-e-m10-mk1-mk2-mk3-owners-thread.395080/page-426
- [W7] DPReview E-PM2 review conclusion: https://www.dpreview.com/reviews/olympus-e-pm2/7
- [W8] ePHOTOzine, May 2017 firmware list (shows which wishes Olympus later granted): https://www.ephotozine.com/article/major-olympus-firmware-updates--30928

Snippet only (fetch blocked or page not served):

- [S1] getdpi, "E-M5 firmware update": https://www.getdpi.com/forum/4-3rds-cameras/49964-e-m5-firmware-update.html
- [S2] Cambridge in Colour threads: https://www.cambridgeincolour.com/forums/thread35057.htm and https://cambridgeincolour.com/forums/thread35389.htm
- [S3] dpreview, "What's next for the Mama Bear of the OM-D series?": https://www.dpreview.com/forums/thread/3615717
- [S4] dpreview, "Wish list for OMD-E-M6": https://www.dpreview.com/forums/post/50493695
- [S5] fredmiranda threads: https://www.fredmiranda.com/forum/topic/1169553/1 and https://www.fredmiranda.com/forum/topic/1144967/
- [S6] PetaPixel, "Hacker Reportedly Finds Hidden Features in the Olympus OM-D EM-5" (16 Oct 2012): https://petapixel.com/2012/10/16/hacker-reportedly-finds-hidden-features-in-the-olympus-om-d-em-5/
- [S7] 43rumors, "Olympus E-M5 hack: Clean Hdmi 4:2:2 and focus peaking possible?" (listing page; the post was not on the page when fetched): https://www.43rumors.com/page/2004/?id=67
- [S8] Softpedia, "Olympus E-M5 Will Receive Focus Peaking Function via Firmware Update": https://news.softpedia.com/news/Olympus-E-M5-Will-Receive-Focus-Peaking-Function-via-Firmware-Update-422195.shtml
- [S9] lightsnowdev blog, firmware flashing tool that listed E-PM2 support; a commenter asked about E-PM2 video-quality hacks (page now 404): https://lightsnowdev.blogspot.com/2014/08/firmware-control-tool-to-flash-any.html
- [S10] reddit r/OlympusCamera thread on manual lenses with the E-M5 (mirror link in search results; not fetched).

### Ten most-asked features

| # | Wish | How often it came up | Threads | State on the E-PM2 |
|---|---|---|---|---|
| 1 | Focus peaking | The most frequent. In every stills wish source: S1, S2 (two threads), S3, S6, S7, S8, S10, and W4. Three posters asked for it in video in W1 and W2. | W1, W2, W4, S1, S2, S3, S6, S7, S8, S10 | Mod has it. Not on a button, not in video. |
| 2 | 24p / 25p (PAL) video | 6 posters on W1, 5 on W2. The top video wish. | W1, W2 | NEEDS-PROBE. |
| 3 | Higher bitrate, better codec, intra-frame | 3 posters on W1, 4 on W2, plus 2 asking for a better codec. S9 asks the same for the E-PM2. | W1, W2, S9 | NEEDS-PROBE. |
| 4 | 1080p50 / 60 and faster rates | 4 posters on W1; one asked for 48p and 72p. | W1 | NEEDS-PROBE. |
| 5 | Electronic first curtain or electronic shutter (shutter-shock cure) | One wish-list poster in S4; one poster each in W2 and W6. Olympus answered with Anti-Shock 0 s in 2014. | S4, W2, W6 | NEEDS-PROBE. |
| 6 | Exposure compensation in M with auto ISO | One strong request in S5 (Dec 2012). Granted later on the E-M1 II and E-M1X. | S5 | SOFTWARE-ONLY. |
| 7 | Mysets on the mode dial (custom modes) | Asked in S1 and S2. | S1, S2 | SOFTWARE-ONLY as on-screen modes. |
| 8 | Clean HDMI output | The 2012 "hidden feature" claim in S6 and S7. Never confirmed. | S6, S7 | NEEDS-PROBE. |
| 9 | Small AF target and ISO 100 | Granted for the E-M5 in fw 2.0 (W3). I did not see the earlier requests. | W3 | Small target present. ISO LOW is SOFTWARE-ONLY. |
| 10 | Better audio control and IBIS control in video | 2 posters on W2 (audio); 1 on W1 (IBIS lock and pan detection, white-balance lock). | W1, W2 | Recording volume present. IBIS in video is NEEDS-PROBE. |

Also seen, less often: 1/8000 s shutter and a better EVF (S2, S3; hardware), a lowest shutter speed for auto ISO (granted in 2017, W8; I found no request thread), subject tracking for birds on older bodies (4 posters in W5), menu tidy-up (S4), built-in viewfinder, mode dial and sensor-shift video IS for the E-PM2 (reviewer, W7). I found no request for an intervalometer, Live Composite or a level gauge for the E-PM2 or E-PL5.

## (e) Top 15 worth trying on the E-PM2

Ranked by value for effort. Value comes from the wish list (d), from what other mods ship (a, b) and from what newer
bodies have (c). Effort is judged from the building blocks in `docs/feasibility.md`. Every judgement here is
*inferred* unless it says otherwise. "First step" is the smallest action that gives new evidence.

| # | Feature | Why it is worth it | Effort | First probe or first step |
|---|---|---|---|---|
| 1 | **Higher video bitrate, lower QP floor, no 29-minute stop** | Wish 3 in (d). Almost every Olympus mod ships the time limit. The patches are written (`experiments/2026-11-12-hardware/`). | Low: flash and test | Flash the written patches one at a time. Record 35 min. Note what happens at 4 GB (ABel's builds split files; the E-M10 I reports stop with a card error, see (a)). Then add auto-restart of recording (Magic Lantern "Movie Restart", (b) b4). |
| 2 | **E-PL6 items: ISO LOW, Release Lag-Time Short, Movie Tele-converter** | Verified in the E-PL6 manual (p.65, 74, 80, 120) on the same board. The same port method gave interval shooting and the level gauge. | Low to medium | Take the E-PL6 menu rows and settings ids from `firmware-diff.md`. Check each on the emulator menu walk. One feature per flash. Check the small AF target on the camera first: the manual says it is already there. |
| 3 | **Log channel, then code and looks from the card** | fenykl (E-PL3, same processor generation) and em10-fw load code from the card. Caduceus and GRKit load looks from the card. It ends one flash per change. It is steps 1 to 4 of "Order of work" in `docs/feasibility.md`. | Medium, method known | A half-press hook that writes one line to a card file. Then the RAM-table probe: point one film slot at a RAM copy of its own table. Then load one 3×3 matrix from a card file. |
| 4 | **Flat (log-like) look for video** | Caduceus E-P7 "true log video" and em10-fw FLAT are popular. Here it is one more tone curve in a film slot. | Low: data only | Record a movie with a film slot selected. Check that the slot's curve is in the file. If yes, build a flat curve with the existing look tools. |
| 5 | **Peaking on a button, without the zoom, and during movie recording** | Wish 1 in (d). The E-P5 has it on a button (E-P5 manual p.84). Already an open item in `docs/todo.md`. | Medium | Pair the E-P5 state object as planned (peaking NOTES §15.5). For movies: leave the hook on during REC and count dropped frames. |
| 6 | **Zebra, false colour, spot meter from the peaking hook** | Magic Lantern's most used overlays ((b) b1). The OM-1 has zebra only in movie mode. CPU access to the live-view buffer is proven. | Medium | Replace the peaking write with "luma over threshold → stripes". Measure the live-view frame rate. Then a 6-band luma-to-colour table. |
| 7 | **On-screen data: battery %, focus distance, depth of field, shutter count** | fenykl shows all of them on the E-PL3. E-M1X added a focus distance indicator. Needs OSD text, which many later items need too. | Medium | Find the OSD text draw routine and print one fixed string in live view. Then dump the lens status struct at two focus positions. Then find the battery ADC value. |
| 8 | **Add Effects on film looks, and film slots 110 to 118** | Grain-like, vignette, white edge and frame are what Caduceus users ask for most. Both are data edits already listed in `docs/todo.md`. | Low: data only | One film slot with the Pin-Hole and White Edge lists enabled. One hidden number given a menu value. |
| 9 | **Anti-Shock 0 s (electronic first curtain)** | Wish 5 in (d): the cure for shutter shock. The E-P5 got it by firmware 1.4 on the same sensor (hw s.3). | High: new exposure sequence | In `firmware-diff.md`, find the E-P5 anti-shock sequence (`STB_CURTAIN1_RUN` is the E-M10 name, per em10-fw notes). Camera probe: open the shutter as Live Time does, reset the sensor, close the rear curtain after 1/100 s, check the frame. |
| 10 | **Frame averaging by Multiple Exposure with more than 2 frames ("Live ND lite", tripod noise reduction)** | Caduceus E-P7 found that stock Multiple Exposure with Auto Gain averages N frames, so ND2 to ND4 needs only data there. nsud-dev has ND2 to ND16 on the E-M5 III. | Low if the limit is data; unknown | Find the frame-count limit of Multiple Exposure. Try 3 and 4 with Auto Gain on. Compare noise with one frame. |
| 11 | **Live Composite** | A signature Olympus feature. E-M10 and E-PL7 have it with the same sensor family. Live Time already reads the sensor with the shutter open. | High: port or write | After item 10: the same loop with "lighten" in place of "mean". First find the Live Time accumulation buffer and the E-M10 `Start_TakeComposite` path. |
| 12 | **Focus bracketing by lens steps** | Wish of every macro user. Sony FocusBracket, CHDK, Magic Lantern have it. E-M10 II got it in stock. The interval sequencer can drive the series. | Medium to high; one unknown | Find the lens step routine (E-M10 I name: `fcs_lens_mfts_move_lens_ofset`). Call it with a fixed count from the half-press hook. Warning: em10-fw's plugin runs and the lens does not move. |
| 13 | **Auto-ISO and exposure limits: lowest shutter speed for Auto ISO, exposure compensation in M with Auto ISO, AE bracket beyond stock counts, Bulb/Time over 30 min** | Wish 6 in (d). Caduceus E-P7 and db firmware added the minimum shutter speed. em10-fw lists the bulb limit as a 2-byte edit. | Low for table edits, medium for AE logic | Find the Bulb/Time timer list and add 60 min. Find the Auto-ISO program line and add one minimum-shutter value as a menu row. |
| 14 | **Extra aspect ratios: 65:24 (XPan), 21:9** | Camera-tested on the E-P7. Popular in Ricoh, Nikon and Canon mods. | Medium | Find the aspect table (stock: 4:3, 16:9, 3:2, 1:1, 3:4; manual p.50). Look for unused rows as on the E-P7. Change one row to 4608×1702 and check live view mask, JPEG and playback. |
| 15 | **Electronic-shutter probe (silent shutter)** | One result decides a family: silent shutter, 1/16000 s, real Live ND, flicker scan, pre-capture. No body with this sensor shipped it, so the answer is unknown. | One probe, then high | End a Live Time exposure by sensor readout without closing the shutter. Look at the frame. Expect about 1/40 s rolling skew (hw s.3). |

**Next in line**

- **24p / 25p video** (wish 2): change the frame period of the 1080 sensor record by 20 % and check the file (hw s.3 says no record exists yet).
- **Screenshot to the card** (fenykl, Magic Lantern): dump the OSD plane to a file. Useful for this project's own guides.
- **Photo Story** (verified in the E-P5, same processor) and **in-camera HDR** (E-M10).
- **Color Creator** or a small look editor from stock menu lists (om10mi-mods did it on the E-M10 I).
- **Look name in EXIF** (Caduceus): one hook on the EXIF fill.
- **USB debug shell as a development channel**: list its commands (hw s.4); a memory read and a call would cut the flash cycle, as on Fuji and Samsung.
- **Live view over HDMI** (wish 8): plug HDMI in shooting mode and find the code that blocks it.
- **Keystone** by the distortion-correction warp table. **Settings backup to a card file.** **Motion or lightning trigger** from the AE statistics. **Games**, as a test of the loader only.

**Not worth a start now** (with the evidence): 4K and RAW video (no sensor mode, card path about 28 MB/s, hw s.3 and s.6);
5-axis IS and Sync IS (2-axis unit, hw s.4); PDAF features; Wi-Fi, Bluetooth, tethering as the OM bodies do it (no
radio, no PTP capture, hw s.4); 1/8000 s mechanical; in-camera focus stacking with any lens (the patch only removes a
lens check in a stacker that the E-PM2 does not have).

## Not verified

### Olympus mods (a)

- No mod was run. "camera" states repeat each project's own report.
- The db firmware status page did not load its table; the feature list is from the v0.4.0 release notes.
- lightsnowdev pages now return 404; the row repeats this repo's earlier archive notes and the em10-fw summary.
- The PetaPixel and apotelyt service-menu pages were read as search snippets only. The E-PM2 key sequence is not checked.
- The GitHub sweep covers GitHub only. Gitee, GitLab, Korean and Russian forums were not searched. mu-43 has one thread opened (page 1).
- No released Olympus bitrate patch was found on any body (E-M5 II and E-M1 II included). The xdel.ru patches change the time limit and the stacking lens check only.
- OM-3 = TruePic X and E-P7 = TruePic VIII: from memory, not verified.

### Other brands (b)

- Magic Lantern web site and wiki returned HTTP 403. ML rows come from the user-guide source files (`doc/MN-*.txt`, `doc/FEATURES.txt`) and module READMEs. They were read in the ML tree bundled in [DangLamTung/XPan-Digital-Canon-6D][XPAN]. The same file names exist in the upstream repo (checked by directory listing), but the upstream file contents were not compared.
- CHDK wiki returned HTTP 402. CHDK rows come from the CHDK source tree in [chasedson/chdk-film][CHDKFILM] (`doc/1_intro.txt`, `modules/`, `core/`, `CHDK/SCRIPTS/`) and the Wikipedia article. CHDK curves and edge overlay were seen only as module file names (`curves.c`, `edgeoverlay.c`); they have no row.
- PTool: the Personal View pages returned 404. Verified from other pages: bitrate, GOP, native 24p/25p, PAL/NTSC, ISO limit, all languages, 29-min limit, anamorphic MJPEG modes. From a search snippet only: "Third-party battery" and "Prevent version compare" check boxes. From memory, not verified: audio bitrate and per-mode quantiser settings; GH3 and later bodies were never opened by PTool.
- Nikon Hacker: the wiki returned 404. Patch names come from `patches.c` in the project's own repo. Per-model coverage was not listed here.
- Pentax: pentax-hack.info and the forum threads returned 403/404 or empty pages. That debug mode can turn off dark-frame subtraction on some bodies comes from search snippets only. pktriggercord was opened.
- Apertus AXIOM: the manual wiki page was opened. LUT and PLR HDR are listed there without details.
- Samsung NX-KS: its own page is gone; features come from the summary in the nx500_nx1_modding README.
- Sony LegacyLenses and the OpenMemories app list file were not opened.
- Every "(fm)" statement about stock E-PM2 behaviour: Live View Boost, Auto-ISO limit, digital tele-converter, Grainy Film grain stage, soft-focus and Pin Hole stages, art-filter frame effect, RAW Data Edit, Noise Reduction menu, Edit Filename, Pixel Mapping, Eye-Fi support, speaker, Super Fine JPEG, 12-bit lossless ORF, IS focal-length setting.
- The 1280x720 10-bit 24 fps RAW video figure is arithmetic from the 28 MB/s card speed, not a measurement.

### Newer bodies and wish list (c, d)

- Forum counts above cover only the pages that opened. Threads S1 to S10 were read as search snippets only.
- No mu-43.com thread was found by search. No reddit r/M43 thread was fetched.
- E-M10, E-PL7 and E-M10 II sharing the exact E-PM2 sensor is reported, not verified.
- E-P5 ISO LOW: Wikipedia lists ISO 100; I did not find the line in the E-P5 manual text. E-PL6 ISO LOW is verified.
- E-M1 II 1/32000 s, E-M5 II peaking in video, E-M5 II HDMI live output, first body with sensor-shift movie IS and 5-axis IS, first body without the 29-minute limit: from memory, not verified.
- The claim that Anti-Shock 0 s is a true electronic first curtain rests on news reports and a forum history list. One search snippet disputes it.
- HDR BKT frame options on the E-PM2 are not listed in its manual.
- E-PM2 firmware 1.1 to 1.6 release notes were seen only as search snippets (bug fixes and lens support).
- Page numbers are PDF page indices. Text extraction of the manuals was automatic; an absent search hit in a sister manual is strong but not absolute proof of absence.
- The E-M1X, OM-1, OM-1 II, OM-3, OM-5, OM-5 II, E-P7 and E-M10 IV manuals exceed the page-fetch size limit and were downloaded directly from the maker's server instead.
- dpreview feature pages, imaging-resource reviews, Robin Wong and mirrorlesscomparison were not used for the table. The maker manuals covered every row.
- The wish list has no E-PM2 or E-PL5 thread. It is built from E-M5 and E-M1 threads of the same years.

### Top 15 (e)

- Every effort estimate is a judgement, not a measurement.
- Item 4 assumes that a film slot's tone curve applies to movies. Item 10 assumes that the E-PM2 Multiple Exposure combiner loops over N frames as the E-P7 one does. Item 12 assumes a callable lens step routine. Each first step tests its own assumption.

## Link keys

[ML-FEAT]: https://github.com/reticulatedpines/magiclantern_simplified/blob/dev/doc/FEATURES.txt
[ML-OV]: https://github.com/reticulatedpines/magiclantern_simplified/blob/dev/doc/MN-OVERLAY.txt
[ML-EXPO]: https://github.com/reticulatedpines/magiclantern_simplified/blob/dev/doc/MN-EXPO.txt
[ML-SHOOT]: https://github.com/reticulatedpines/magiclantern_simplified/blob/dev/doc/MN-SHOOT.txt
[ML-FOCUS]: https://github.com/reticulatedpines/magiclantern_simplified/blob/dev/doc/MN-FOCUS.txt
[ML-MOVIE]: https://github.com/reticulatedpines/magiclantern_simplified/blob/dev/doc/MN-MOVIE.txt
[ML-DISP]: https://github.com/reticulatedpines/magiclantern_simplified/blob/dev/doc/MN-DISPLAY.txt
[ML-PREFS]: https://github.com/reticulatedpines/magiclantern_simplified/blob/dev/doc/MN-PREFS.txt
[ML-DEBUG]: https://github.com/reticulatedpines/magiclantern_simplified/blob/dev/doc/MN-DEBUG.txt
[ML-AUDIO]: https://github.com/reticulatedpines/magiclantern_simplified/blob/dev/doc/MN-AUDIO.txt
[ML-MODS]: https://github.com/reticulatedpines/magiclantern_simplified/tree/dev/modules
[ML-ETTR]: https://github.com/reticulatedpines/magiclantern_simplified/tree/dev/modules/ettr
[ML-AUTOEXPO]: https://github.com/reticulatedpines/magiclantern_simplified/tree/dev/modules/autoexpo
[ML-ADVINT]: https://github.com/reticulatedpines/magiclantern_simplified/tree/dev/modules/adv_int
[ML-SILENT]: https://github.com/reticulatedpines/magiclantern_simplified/tree/dev/modules/silent
[ML-DUAL]: https://github.com/reticulatedpines/magiclantern_simplified/tree/dev/modules/dual_iso
[ML-CROP]: https://github.com/reticulatedpines/magiclantern_simplified/tree/dev/modules/crop_rec
[ML-RAWV]: https://github.com/reticulatedpines/magiclantern_simplified/tree/dev/modules/raw_video
[ML-LUA]: https://github.com/reticulatedpines/magiclantern_simplified/tree/dev/modules/lua
[ML-FILEMAN]: https://github.com/reticulatedpines/magiclantern_simplified/tree/dev/modules/file_man
[ML-IMGNAME]: https://github.com/reticulatedpines/magiclantern_simplified/tree/dev/modules/img_name
[ML-DEFLICK]: https://github.com/reticulatedpines/magiclantern_simplified/tree/dev/modules/deflick
[ML-BENCH]: https://github.com/reticulatedpines/magiclantern_simplified/tree/dev/modules/bench
[ML-SDCLK]: https://github.com/reticulatedpines/magiclantern_simplified/tree/dev/modules/sd_clock
[ML-DOT]: https://github.com/reticulatedpines/magiclantern_simplified/tree/dev/modules/dot_tune
[ML-ARK]: https://github.com/reticulatedpines/magiclantern_simplified/tree/dev/modules/arkanoid
[ML-YOLO]: https://github.com/reticulatedpines/magiclantern_simplified/tree/dev/modules/yolo
[CHDK-INTRO]: https://github.com/chasedson/chdk-film/blob/main/doc/1_intro.txt
[CHDK-MOD]: https://github.com/chasedson/chdk-film/tree/main/modules
[CHDK-CORE]: https://github.com/chasedson/chdk-film/tree/main/core
[CHDK-SCRIPTS]: https://github.com/chasedson/chdk-film/tree/main/CHDK/SCRIPTS
[CHDK-LUALIB]: https://github.com/chasedson/chdk-film/tree/main/CHDK/LUALIB
[CHDK-GRIDS]: https://github.com/chasedson/chdk-film/tree/main/CHDK/GRIDS
[CHDK-GAMES]: https://github.com/chasedson/chdk-film/tree/main/modules/games
[CHDK-WIKI]: https://en.wikipedia.org/wiki/CHDK
[CHDKFILM]: https://github.com/chasedson/chdk-film
[IXFILM]: https://github.com/BjornB2/ixfilm-os
[MFILM]: https://github.com/HNGSeries/mfilm-canon-film-simulation
[XPAN]: https://github.com/DangLamTung/XPan-Digital-Canon-6D
[MIRROR]: https://github.com/m-a-x-s-e-e-l-i-g/mirror-worlds
[BAYER]: https://github.com/m-a-x-s-e-e-l-i-g/bayer-drift
[M10RAW]: https://github.com/voncapel/eos-m10-raw
[CAMDESK]: https://github.com/vugpgbwefwq47397-debug/camdesk-ml
[IRIDE]: https://github.com/GodEater58/Iride-6D
[NH]: https://github.com/simeonpilgrim/nikon-firmware-tools/blob/main/Nikon-Patch-JS/src/nikon_patch/patches.c
[Z8]: https://github.com/XinmiaoZhao/NikonFirmwarePatch
[Z5X]: https://github.com/honokaoshi83-max/z5-extensions
[WL-Z30]: https://github.com/WonderLantern/wonder-lantern-z30
[WL-Z6]: https://github.com/WonderLantern/WonderLantern-z6
[WL-Z50]: https://github.com/ha1vk/wonder-lantern-z50-firmware
[SONY-TW]: https://github.com/ma1co/OpenMemories-Tweak
[SONY-TL]: https://github.com/jonasjuffinger/TimeLapse
[SONY-FB]: https://github.com/obs1dium/FocusBracket
[SONY-BM]: https://github.com/obs1dium/BetterManual
[SONY-WEB]: https://github.com/hhb/sony-pmca-webcontrol
[SONYLUT]: https://github.com/EnglandLobster/sony-lut-camera
[NEX6]: https://github.com/leyteris/sony-nex6-film-studio
[RECIPELAB]: https://github.com/voxivoid/recipe-lab-sony-pmca
[EOSHD]: https://www.eoshd.com/gh2-patch-vault
[DVX]: https://www.dvxuser.com/threads/100mbps-max-latitude-native-24-25p-patch.251670/
[LUMIX]: https://github.com/flickering-star/lumix-firmware-research
[NX]: https://github.com/ottokiksmaler/nx500_nx1_modding
[NX-RC]: https://mewlips.github.io/nx-remote-controller-mod
[GR3FILM]: https://github.com/idontknownihil/gr3-film-mods
[GRCT]: https://github.com/DoYitNow/gr-custom-tool
[GRKIT]: https://github.com/ahonn/GRKit
[GRMOD]: https://github.com/Maxwooow/Ricoh-GRMod
[KOMA]: https://github.com/overscanindustries/koma
[GRITTY]: https://github.com/robbcocco/gritty
[FRAME]: https://github.com/Lyle-xub/FRAME-GR2
[GR3XHDR]: https://github.com/crciuperca/Ricoh-GR-IIIX-HDR
[GR4]: https://github.com/radium-wang/ricoh-gr4-firmware-analysis-and-feature-expansion
[FUJIHACK]: https://github.com/fujihack/fujihack
[FUJIWIFI]: https://github.com/hkr/fuji-cam-wifi-tool
[PKTC]: https://github.com/asalamon74/pktriggercord
[PKTC-SET]: https://github.com/asalamon74/pktriggercord/blob/master/pentax_settings.json
[M8]: https://github.com/gasdevmco/leica-m8-firmware
[FILMLAB]: https://github.com/jhihhe/Jhih-FilmLab
[AXIOM]: https://apertus.org/wiki/index.php?title=AXIOM_Beta/Manual
