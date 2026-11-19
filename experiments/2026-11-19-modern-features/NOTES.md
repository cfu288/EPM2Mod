# Features of newer Olympus and OM SYSTEM bodies: software or hardware

Date: 2026-11-19. Desk work only. Nothing was built or flashed.

Question: which features of the bodies from the E-P5 (2013) to the OM-5 Mark II (2025) does the E-PM2 lack, and
is each one blocked by hardware or only missing from the software?

This note brings together and updates:

- `experiments/2026-11-15-feature-survey/mods-and-web.md` section (c): 21 maker manuals, E-P5 to OM-5 II.
- `experiments/2026-11-15-feature-survey/firmware-diff.md`: the text tables and code of 22 stock firmware files.
- `experiments/2026-11-14-feasibility/hardware.md`: the hardware facts (sensor modes, encoder, card path).
- Later findings: `experiments/2026-11-17-anti-shock/NOTES.md`, `docs/dev/feasibility.md` (the 12-region colour
  stage, 2026-11-18), `experiments/2026-11-17-auto-iso-min-shutter/NOTES.md`, `experiments/2026-11-17-osd-info/NOTES.md`.

Labels: **V** verified (manual, firmware bytes or a measurement), **I** inferred, **U** unknown.

## 1. Short answer

1. **Few features are blocked by hardware, and each block is a physical part:** the shutter unit, the 2-axis
   stabiliser, the sensor's read-out speed, the 8-bit H.264 encoder, the card path, radios, the screen, dials and
   connectors.
2. **Most features are software.** About 40 need only code or data on parts that the E-PM2 has. Several have a
   donor: the E-PL6 has the same firmware base (66% shared code), and the PEN-F was the donor for the lowest
   shutter speed.
3. **One probe decides a family of about ten features.** If the sensor can end an exposure by read-out while the
   shutter is open, then silent shutter, 1/16000 s, Live ND, Live GND, Pro Capture, Flicker Scan and anti-flicker
   become software work. The read-out takes 24.3 ms (**V**), so a silent shutter would have a strong rolling
   effect, as on the E-M5 II.
4. **Changed since 2026-11-15:**
   - Done: lowest shutter speed for ISO Auto, peaking colours, film simulations loaded from the card.
   - The E-P5 is not a donor for Anti-Shock 0 s. The E-PM2 is in the other sensor family (with the E-M5 and the E-PL6),
     which sends different register programs to the sensor (**V**, anti-shock notes section 2.2).
   - Color Profile Control (12 colours) is possible for stills only. The 12-region stage runs in pipe A (stills
     and RAW Data Edit), not in live view or movies (**V**, feasibility).
   - Exposure compensation in M with ISO Auto: the block is 2 bytes at 0x7E5878AF (**I**, not run).

## 2. Done by EPM2Mod

| Feature | First body | Done |
|---|---|---|
| Interval shooting and time-lapse movie (240 frames) | E-PL6 (2013) | 2026-11-13 |
| Level gauge with calibration | E-M5 (2012), E-PL6 | 2026-11-14 |
| Focus peaking, four colours | E-P5 (2013), colours E-M5 II | 2026-11-14, 2026-11-15 |
| Film simulations in the ART menu | Own feature; compare the OM-3's Color and Monochrome profiles | 2026-11-12 onward |
| Film simulations from the SD card | Own feature | 2026-11-17 |
| Lowest shutter speed for ISO Auto | PEN-F fw 2.0 (2017) | 2026-11-19 |

## 3. Software: the parts are in the E-PM2

"Donor" is a body whose code can be copied or followed. "Own code" means the idea only.

### 3.1 Small: a menu row, data or a short patch

| Feature | First body | Why it is software | Donor | Label |
|---|---|---|---|---|
| Light Box (two pictures side by side in playback) | E-PL5 | Text, setting and component are in the E-PM2; only the menu row is missing | E-PL5, E-PL6 | **V** row, **I** code |
| Close Up Mode (playback zoom mode 2) | E-PL5 | Setting and text are in the E-PM2; the long playback-zoom code may be cut | E-PL6 | **I** |
| Release Lag-Time: Short | E-PL6, E-P5 | Same shutter; setting 521 is read in 2 places, the E-PL6 reads it in 3 | E-PL6 | **V** addresses |
| ISO LOW (about ISO 100) | E-PL6, E-P5, E-M5 fw 2.0 | A pulled setting on the same sensor; text is in the E-PM2 | E-PL6 | **I** |
| Exposure compensation in M with ISO Auto | E-M1 II | A 2-byte block in the exposure code | Own | **I** |
| Exposure compensation ±5 EV | E-M1, E-M10 | Range limit in the value list | E-M10 (method) | **I** |
| Add Effects on a film simulation (glow, vignette, white edge, frame) | Own | Per-filter data lists at 0x7E849E2B | – | **V** lists |
| More looks: Flat, Bleach Bypass, Vintage, Instant Film, OM-Cinema, Partial Color | E-M5 II to OM-3 | Our colour tables (curves, matrix, six hue axes) in an ART slot. Partial Color needs a strong per-axis saturation cut | Own | **I** |
| Midtone in Highlight & Shadow | PEN-F, E-M5 II fw 3.0 | A third control point on the stock tone spline 0x7E558466 | Own | **I** |
| Film grain Off/Low/Medium/High | PEN-F | The Grainy Film module exists. Stock-strength grain on a film simulation: about 40 bytes (TODO) | Own | **I** |
| Shading (vignette + and −) | PEN-F | Pin-Hole shading and Shading Comp. exist | Own | **I** |
| Vertical video flag | OM-5 | Accelerometer exists; a rotation field in the MOV header | Own | **I** |
| Higher video bit rate, no 29-minute limit | E-M5 II (77 Mb/s) | The limits are firmware tables; patches are written | Own | **V** patches written, not flashed |
| Bulb/Time Monitor brightness | E-M1 | Backlight control exists | E-P5 | **I** |
| Night Vision (dim red screen) | OM-1 | Display colour is under firmware control | Own | **I** |
| Menu Recall, My Menu, World Time, press-and-hold times | E-M1 fw 4.0 to E-M1X | Menu lists take new rows (128 per list, **V**) | Own | **I** |
| Mysets as on-screen modes C1 to C4 | PEN-F (mode dial) | Mysets exist; the dial does not | Own | **I** |
| Extra button functions (peaking, AE BKT, ART BKT on a button) | E-P5 | Button tables | E-P5 | **I** |
| Star ratings in playback | OM-1 | A field in the file | Own | **I** |
| Battery percentage, focus distance, shutter count on screen | Own (OM-1 shows more) | Values readable (**V**); candidate `osd-battery` exists | Own | **V** values |

### 3.2 Larger: new code on parts the E-PM2 has

| Feature | First body | Why it is software | Open point | Label |
|---|---|---|---|---|
| Focus bracketing (3 to 999 frames) | E-M10 II, E-M1 fw 4.0 | Interval code (done) plus the lens focus-drive calls of MF | Which call moves focus by a fixed step | **I** |
| Live Composite | E-M10 (2014) | Live Time reads the sensor with the shutter open (**V**); RAM is enough | A lighten blend of 16 MP RAW frames: CPU loop or image-processor op | **I**, blend **U** |
| In-camera HDR (HDR1/HDR2) | E-M1, E-M10 | Bracketing exists; four frames fit in RAM | Merge and alignment code | **I** |
| Hand-Held Starlight (8-frame merge) | E-M1, E-M10 | Burst and RAM exist | Merge time on the MN103 | **I** |
| Color Profile Control (12 colours) | PEN-F, E-P7, OM-3 | The 12-region hue, saturation and lightness stage exists (**V**) | Stills only: the stage is not in live view or movies (**V**) | **V** stage |
| Color Creator (one hue turn and saturation) | E-M1, E-M10 | The 3×3 colour matrix that every film simulation sets | UI | **I** |
| Monochrome profile (filter, shading, grain) | PEN-F | The B&W filter of Monotone, Pin-Hole, Grainy Film exist | Grain outside the art filter **U** | **I** |
| Lens Info Settings (legacy lens EXIF) | PEN-F | IS focal length entry, text entry screen and EXIF writer exist | Where the lens fields are filled | **I** |
| Spot metering at the AF target | E-M5 II fw 3.0 | AE area records and AF position exist | AE window is a table or code **U** | **I** |
| Peaking on a button, any lens and AF mode | E-P5 | Own peaking code (done) | Trigger outside MF Assist needs the E-P5 state object (focus-peaking NOTES §15.5) | **I** |
| Peaking intensity, live-view dimming | E-M5 II | Own peaking code | Dimming needs a live-view gain | **I** |
| Zebra (stills live view) | OM-1 | Own peaking hook, marking by level not by edge | – | **I** |
| Photo Story | E-P5 | A dormant 4-window live view exists | Large port from 37% shared code | **V** strings |
| Movie Tele-converter (1:1 crop zoom while recording) | E-PL6, E-P5 | The CLIP 1:1 sensor mode exists (**V**) | Port from the E-PL6 | **I** |
| My Clips, time code, movie trimming, Old Film effect | E-M5 II, E-M10 III | File-writer and playback work | Low value | **I** |
| Lighter AF and focus helpers: AF Limiter, Preset MF, Focus Ring Lock, focus distance display | E-M1 II to E-M1X | The lens reports and drives focus (**I**) | – | **I** |
| Face selection button | E-M1 III | Face detector exists | Multi-face output **U** | **I** |
| Settings backup to the card | E-M5 II fw 3.0 | Card read/write and the settings bank are mod building blocks (**V**) | – | **I** |
| Remote release from a computer | E-M1 (tethering) | USB debug channel runs shell commands (**V**) | Host program | **I** |
| Keystone and fisheye compensation | E-M1 fw 2.0, E-M1 II | GPU and a distortion resampler exist (**V**) | Whether the resampler takes a projective map | **I** |

## 4. Software if a probe passes

| Feature | First body | What decides it | Probe | Label |
|---|---|---|---|---|
| Anti-Shock 0 s (electronic first curtain) | E-M1 fw 1.3, E-P5 fw 1.4 | Not a port: the E-PM2's sensor family has no 0 s program. A stock exposure with the sensor started about 30 ms after the first curtain | Two RAW pictures of a wall: Live Time 0.5 s against normal 0.5 s (no build) | **U** |
| Silent shutter, 1/16000 s, 1/32000 s | E-M5 II, E-M1 fw 4.0, E-M1X | Electronic exposure end by read-out with the shutter open. Rolling read-out 24.3 ms (**V**) | The same wall test, then end a Live Time exposure by read-out | **U** |
| Live ND, Live GND | E-M1X, OM-1 II | Silent shutter, then an average of frames (Live Composite with a mean) | After the silent-shutter probe | **U** |
| Pro Capture | E-M1 II | Silent shutter at burst rate and a ring buffer. Full read-out allows at most about 40 frames per second in theory (**I**); stock records 10 fps | After the silent-shutter probe | **U** |
| Flicker Scan, anti-flicker shooting | E-M1 II, E-M1X | Silent shutter for Flicker Scan; AE statistics fast enough to see 100/120 Hz | Sample the AE statistics block | **U** |
| Starry Sky AF | E-M1 III | Stars must rise above noise in live view | Grab the live-view buffer on a star field | **U** |
| Live View Boost II (very dark scenes) | E-M5 II | A live-view exposure longer than one frame | Set it and see if the sensor mode accepts it | **U** |
| 720p60, 120 fps slow motion | E-M5 II, E-M10 II | 60 and 120 fps sensor modes exist but drop most lines (**V**); the encoder's speed is unknown | Route the 60 fps mode to the encoder | **U**; 1080p60 needs a sensor register set nobody has |
| 24p, 25p | E-M5 II, E-M1 fw 4.0 | Sensor frame period and file timebase | Change the frame period | **U** |
| All-Intra, bit rates above 24 Mb/s | E-M5 II | Encoder ceiling **U** | Raise the rate target in steps | **U** |
| Peaking and zebra while recording | E-M1 II, OM-1 | CPU budget during encoding | Leave the hook on during REC | **U** |
| Live view over HDMI | E-M1 II | Stock blocks shooting with HDMI attached (a rule, **V**); routing the live-view plane **U** | Switch the transmitter on in shooting mode | **U** |
| Sensor-shift IS during movies | E-M5 | The 2-axis unit exists; heat and noise **U** | Keep the IS loop running during REC | **U** |
| High Res Shot (tripod) | E-M5 II | Whether the 2-axis unit holds a half-pixel offset | Command a static offset, shoot twice, measure | **U** |
| High Res Shot (handheld), focus stacking, panorama stitch | E-M1X, E-M1 fw 4.0, E-M10 III | Merge time on the MN103 | Time an 8-frame merge | **U** |
| Subject detection (birds, animals, vehicles, people) | E-M1X | Neural networks on a 2012 processor; face detector only (**V**) | Time a small classifier on one frame | **U**, low expectation |
| Custom AF target sizes (5, 9, 25 points) | E-M1 II | Whether the contrast-AF window takes any size | Set an arbitrary window | **U** |
| Webcam (UVC) | OM-5 | USB 2.0 device controller; endpoint limits **U** | Present a UVC descriptor | **U** |
| Phone remote through a FlashAir card | Own | A card script writes a trigger file | Poll the file, measure delay | **U** |
| Handheld Assist | OM-1 | The IS runs on a separate H8 controller | Read the IS position at live-view rate | **U** |

## 5. Hardware: no firmware can add these

| Feature | First body | Missing part | Label |
|---|---|---|---|
| 1/8000 s mechanical shutter, 1/320 s flash sync | E-P5 | 1/4000 s shutter unit, 1/250 s sync | **V** manual (E-PM2); E-P5 sync **I** |
| 5-axis IS, Sync IS | E-M5 | 2-axis unit, no roll axis | **V** manual |
| 4K and C4K video, 4K time-lapse at video rates, 4K frame grab | E-M1 II | The only full-width read-out runs at 10 fps; the encoder is made for 1080 | **V** sensor mode table, **I** encoder |
| 10-bit video, H.265, HLG, OM-Log with real latitude | E-M1X, OM-1 | 8-bit H.264 encoder (the curve alone is software) | **I** strong |
| RAW video, RAW over HDMI | E-M1X fw 2.0 | Card path about 25 to 28 MB/s; no 4K read-out | **V** arithmetic |
| 14-bit RAW | OM-1 II | 12-bit sensor output | **V** manual |
| Phase-detect AF, AF Focus Adjust, PDAF-based C-AF tuning | E-M1 | No phase-detect pixels | **V** |
| High-speed electronic burst (50 to 120 fps) | E-M1 II, OM-1 | Full read-out 24.3 ms: at most about 40 fps in theory, before the image processor | **I** |
| Wi-Fi, Bluetooth, phone remote with live view, GPS and field sensors | E-P5, E-M1X | No radio or sensors. FlashAir and PENPAL work on the stock body | **V** |
| Built-in EVF functions, eye sensor | E-M5 | No finder (the VF-2/3/4 accessories work) | **V** |
| Tilting or flip screen, Selfie Assist | E-PL7 | Fixed screen | **V** |
| Mode dial, second dial, 2×2 lever, Creative dial, CP button | E-P5 to OM-3 | Not on the body. The functions behind them are software (section 3) | **V** |
| USB charging, USB PD, USB-C | E-M5 III, E-M1X | No charge circuit | **V** |
| Microphone and headphone jacks | E-M1 | SEMA-1 on the accessory port only | **V** |
| Dual card slots | E-M1 II | One slot | **V** |
| Weather sealing | E-M5 | Body construction | **V** |

## 6. Next steps, by value for effort

1. Light Box and Release Lag-Time: rows and small ports from the E-PL6, as the level gauge was.
2. The silent-shutter wall test with the stock firmware: two RAW pictures, no build. It decides section 4's
   largest family.
3. More looks and Add Effects: data only.
4. Focus bracketing on the interval code.
5. Live Composite: time a lighten blend of one 16 MP frame on the CPU first.
