# Features of other Olympus / OM System bodies that the E-PM2 does not have

Date: 2026-11-15. Body: E-PM2 (E101), firmware 1.6. No firmware was built for this note.

Question: which features are in the stock firmware of other bodies and not in the E-PM2, and how
hard is each to bring over?

Labels: **V** verified here (text table, strings or code read), **I** inferred, **U** unknown,
**R** reported by the maker or reviews (not checked in firmware).

Classes:

- **LATENT**: text, setting and code are in the E-PM2. Only menu data is missing.
- **PORT-EASY**: the donor is the E-PL6 or E-PL5 (same run-time base, 66 to 68% code share). A menu
  row and a small amount of code.
- **PORT-HARD**: the donor is the E-P5 (37% share) or a later body, or new pipeline code is needed.
- **REWRITE**: only the idea is taken. Own code on E-PM2 building blocks.
- **IMPOSSIBLE**: a part is missing. The evidence is named.

"Share" is the last column of the firmware table in section 8: a rough measure of how much E-PM2
code a body still holds. It ranks donors. It is not a count of identical functions.

## 1. Short answer

1. The E-PM2's English text table (1,970 ids) is the same as the E-PL5's, and the E-M5 2.3 table
   has no text that the E-PM2 lacks (**V**). The E-PL6 adds 4 ids, all for the VF-4 eye sensor.
   So against its own generation the E-PM2 lacks menu rows and some code, not text.
2. Against the E-PL5 the E-PM2 lacks three menu rows (**V**): **Light Box**, **Close Up Mode**
   (playback) and Mode Dial Function. This was not known: earlier notes treated the two bodies as
   equal.
3. Against the E-PL6 it also lacks **Release Lag-Time**, **ISO LOW**, the **small AF target** and
   **EVF Auto Switch** for the VF-4. Level Gauge, Level Adjust and Time Lapse are already ported.
4. Everything newer (E-P5 and later) needs a port from a less similar body or own code. The best
   value there: 0-second anti-shock (E-P5), focus bracketing (own code on the interval hook), and
   the later looks (Flat, Bleach Bypass, Vintage, Instant Film, film grain) as look tables.
5. Later text tables are shared between bodies. The E-P5 table holds "HDR1", "Color Creator" and
   "Lens Data" although the E-P5 code has none of them. **A text in a table does not prove a
   feature**; the code columns in `results/feature-matrix.md` decide.

## 2. LATENT

| Feature | First body | Hardware | E-PM2 traces | Missing | Label |
|---|---|---|---|---|---|
| **Light Box** in playback (two pictures side by side, zoom both) | E-PL5 1.6, E-PL6 1.4 | None | Text 868 "Light Box"; setting 257 (prm 0x9171, 42 GUI readers); panel record 198; component `CmpPLgh_PlayLightBoxComponent` 0x7EB34D9B and a full GUI sub-state (feature map 10d) | Sub-item row `{191, title 150, setting 257, 2, 7, 1, text 868}` and child entry (198, 257) in the list of panel 191 (now 4 entries: 253 to 256). The same two edits as Level Gauge step A | Rows **V**; "the code is complete" **I**. Test in the emulator first: it draws menus and playback |
| Add Effects on a film look, hidden art numbers 110 to 118 | (own firmware) | None | Already listed in `docs/feasibility.md` | Data | Known before this survey |

Checked and **not** latent, although the E-PM2 has the text: Release Lag-Time, ISO LOW, Close Up
Mode, EVF Auto Switch (section 3). "Multi Function" (text 1510), "Half Way Rls With IS" (1474)
and the built-in EVF texts (1494 to 1509) are E-M5 text; no E-PM2 code string names them (**V**
strings, reachability **U**).

## 3. PORT-EASY (donor E-PL6 1.4 or E-PL5 1.6)

Complete list of menu differences, from `results/menu-rows-epl5-epl6.txt` and the panel child
lists (`experiments/2026-11-14-level-gauge/results/panel-child-lists-diff.txt`):

| Row | In | E-PM2 state |
|---|---|---|
| Playback Info → Light Box (setting 257) | E-PL5, E-PL6 | Section 2 |
| Custom Menu D → "(magnify icon) Close Up Mode" (setting 321, panel 130) | E-PL5, E-PL6 | Below |
| Custom Menu B → Mode Dial Function (panel 651, settings 490 to 493) | E-PL5, E-PL6 | No mode dial. Not useful |
| Custom Menu C → Release Lag-Time (setting 521, panel 659) | E-PL6 | Below |
| Custom Menu K → Level Adjust; LV-Info → Level Gauge; Shooting Menu 2 → Time Lapse Settings | E-PL6 | Done |
| Accessory-port pages 35 to 37 → entry (panel 596, setting 451) | E-PL6 | EVF Auto Switch (**I** from the 4 new texts and the new eye-sensor code) |
| Sub-item row "Dial Function" (panel 110, setting 342) | E-PM2 only | – |

Settings store: all 728 tag defaults are equal in E-PM2 and E-PL6 (interval notes, **V**).

| Feature | Hardware | E-PM2 traces | To port | Label |
|---|---|---|---|---|
| **Release Lag-Time: Short** | Same shutter and sensor as the E-PL6 (**I**). Costs battery (**R**) | Texts 1768/1769; setting 521 = prm 0xDF91, read at 2 places (0x7E5995A9, 0x7E5A4A49); panel 659 | The E-PL6 reads it at 3 places. One function exists only there (0x7E5A26D2, 654 bytes) and one differs (E-PL6 0x7E5A4F01, 503 bytes; E-PM2 0x7E5A48F1, 498 bytes). Plus one Custom Menu row | **V** addresses; behaviour **U** |
| **ISO LOW** (about ISO 100) | Same sensor; a pull setting (**I**) | Texts 1954 "ISO LOW", 1955 "LOW". "LOW" has 7 data references, the E-PL6 has 21 | Value-list entries for ISO and ISO-Auto, and the exposure code that accepts the value (E-PL6 `stb_expose` 0x7E5D3799 is 64 bytes longer). Not traced | **I** |
| **Small AF target** | Contrast AF window is software (**I**) | One field name `mode_af_target_size` | E-PL6 `[CapThr]Trigger setAfFrame` is 399 bytes, E-PM2 171; AF target value list. Not traced | **I** |
| **Close Up Mode** (playback zoom: mode1 / mode2) | None | Text 208; setting 321 = prm 0x91A1, default 1, 15 GUI readers; panel 130 | Custom Menu row. `CPlayZoom::setDbZoomInfo` is 1,884 bytes in the E-PL6 and 1,230 in the E-PM2; the E-PL5 holds the long form (387 of 622 byte windows match, the E-PM2 38). So mode2 is probably cut from the E-PM2 | Row **V**; code **I** |
| **EVF Auto Switch** with a VF-4 | Needs a VF-4 on the accessory port (port **V**, VF-4 support since 1.2 **R**) | Old text 1505; `PER_EYE_SENSOR` names for the built-in type only | E-PL6: texts 1970 to 1973, task `PER_EYE` (`EYES_*`, about 10 functions), `api_user_Get_ExternalEyeSensor_State`, `ctrlExternalEyeSensor`, setting 451 | **V** strings |

## 4. PORT-HARD

Donor shares: E-P5 37%, STYLUS 1 30%, E-M10 22%, E-PL7 21%, E-M1 19%, E-M5 II 16%, PEN-F 16%.
The E-P5 is TruePic VI with the same sensor; from the E-M10 on the processor is another one, so
logic must be re-written and only the method is taken.

| Feature | First body (in the set) | Hardware | E-PM2 traces | Donor and notes | Label |
|---|---|---|---|---|---|
| **Anti-shock 0 s** (electronic first curtain) | E-P5 1.8 (added in 1.4, **R**) | Same sensor as the E-P5 (**R**). The shutter must open and wait; the E-PM2 does that for live view (**I**) | Anti-shock delay only; no `EFS` string | E-P5: `SET_COM_EFS_EXP_START`, `_EXP_STOP`, `_LONG_EXP_START`, `_SLEEP`, `Setting efs` (**V**). E-M10: states `STILL_EFS_EXPOSE*`. Sensor command set plus a new still sequence. Highest value: shutter shock is the known weak point of this body | **I** |
| **Power-zoom control** (zoom by arrow keys, Electronic Zoom Speed) | E-P5 | Needs an electronic-zoom lens | `Ez_Zoom` names partly present (46 strings, E-P5 71) | E-P5 | **I** |
| **C-AF Lock**, AF Area Pointer on/off | E-P5 text | None | None | E-P5. Small | **U** (no code names found) |
| **Photo Story** | E-P5 | Touch screen: yes | Dormant 4-window "PSP" multi-through live view | E-P5 (`Photo_Story Mode case 1..4`, `PhotoSession`). Large | **V** strings |
| **Art BKT RAW edit in playback** | E-P5 | None | Art BKT at capture: yes | E-P5 `EditArtBktRaw_PlayPicture`, `CmpERaw…artbkt` | **V** strings |
| **In-camera HDR (HDR1 / HDR2)** | E-M10 1.4, E-M1 | 4 frames merged in RAM; 512 MiB is enough (**I**) | HDR BKT only; `api_rec_dummy_*HDR*` name stubs | Not the E-P5: its HDR API is also the dummy (**V**). E-M10 `recordMediaHdr … combine`. Needs alignment code | **I** |
| **Live Composite** | E-M10 1.4 | Repeated read-out with the shutter open: Live Time does it (**V**) | `api_rec_dummy_*TakeComposite` stubs | E-M10 states `COMP_READY`, `COMP_CAPTURE_ENABLE`, `COMP_CONTINUE_*`. Needs a lighten blend of RAW frames. Unknown whether the image processor has a "maximum" operation. Probe: time a CPU loop over one 16 MP frame | **I**, blend **U** |
| **Art filters with new processing**: Partial Color; Blur / Shade effects (top-bottom, left-right) | E-PL7 1.4, E-M1 4.6 | None | Diorama (band blur), six-axis hue stage, Add Effects lists | E-PL7 for the method. Partial Color needs saturation per hue axis: **U**, probe with one table | **I** |
| **e-Portrait as a picture mode** | E-M10 (text in E-P5) | None | e-Portrait SCN and playback edit are active (**V**) | E-M10 `COLORTONE_E_PORTRAIT`. Low value | **I** |
| **Hand-Held Starlight** (8 frames merged), **Panning** SCN | E-M10 / E-PL7 | Burst 8 fps: yes | None | Multi-frame merge with alignment. Low value | **I** |
| **Keystone Compensation** | E-M1 4.6 (2.0, **R**), E-PL7 | GPU and the distortion resampler exist (**V**) | None | E-M1 (19%): about 90 code strings. Large | **I** |
| **Movie**: time code, 24p/25p/50p/60p, ALL-Intra, Clips, slow/fast, Movie+Photo, Flat for movie | E-M1 4.6, E-M5 II 4.1 | 30 fps sensor records only; no sensor register map; I+P encoder with 4×4 blocks (hardware notes) | Bit-rate patches written | Frame rates: **U** (new sensor register sets). Time code and Clips: file-writer work, low value | **I** |

## 5. REWRITE (own code; the building blocks are named)

Sorted by value for effort.

| Feature | Seen first in | E-PM2 building blocks | Open point | Label |
|---|---|---|---|---|
| **Flat, Bleach Bypass, Vintage, Instant Film as looks** | E-M5 II 4.1 (Flat, Bleach Bypass), E-PL7 (Vintage), E-M1 II 3.7 (Instant Film) | The film-look tables of this mod (gamma, matrix, hue, art kind) in an art-filter slot | Data only. Light leaks and frames of the originals are not copied | **I** |
| **Focus Bracketing** (no in-camera stack) | E-M1 4.6 (4.0, **R**) | Interval shooting (ported), the lens focus-drive commands used by MF and the `lens` shell, the bracketing menu | Which call moves focus by a fixed step between frames. Probe: one drive call from the interval hook | **I** |
| **Peaking options**: colours, intensity, image brightness | E-M1 4.6 | Own peaking code at 0x7E4C9200 | Menu rows only for colour (done); brightness needs a live-view gain | **I** |
| **Midtone** in Highlight&Shadow | E-M5 II 4.1 | Stock tone editor: settings 319/320, spline 0x7E558466 | A third control point and a third dial page | **I** |
| **Monochrome extras**: film grain Low/Medium/High, shading | PEN-F 3.1 | Grainy Film grain module, B&W filter of Monotone (stock), Pin-Hole and shading effects | Whether the grain stage runs outside the art filter | **U** |
| **Colour profile editor** (PEN-F Color Profile Control, Color Creator) | PEN-F 3.1; E-M1 / E-M10 | Hue stage with six axes, saturation, the look tables, the stock H&S dial screen as UI | Six axes, not twelve. Tables at a RAM address are untested (feasibility probe) | **I** |
| **Lens Info Settings** (name, focal length, aperture of adapted lenses into EXIF) | PEN-F 3.1, E-M1 4.6 | Manual IS focal length (stock), text entry screen (Edit Filename, Copyright), EXIF writer | Where the lens fields of the MakerNote are filled | **I** |
| **Spot metering at the AF target** | E-M5 II 4.1 | AE area records (`pre1_area…`), AF target position | AE window is a table or code? | **U** |
| **Lowest shutter speed for ISO-Auto** | PEN-F 3.1 | ISO-Auto Set, Flash Slow Limit (stock) | Place of the program line in the AE code | **U** |
| **BULB/TIME Monitor** brightness; level gauge on half-press or on a button | E-P5 | Backlight control, ported level gauge | Small | **I** |
| **Exposure smoothing**, more interval frames | OM-1; E-M10 II | Ported interval code (240 frames done) | AE lock between frames | **I** |
| **ND by averaging** (Live ND idea with the mechanical shutter) | E-M1 III 1.6 | Multiple Exposure with Auto Gain and RAW overlay (stock, 2 to 3 frames) | Raise the frame count; blur between frames differs from a real ND | **I** |
| **Remote release from a PC** | E-M1 (tethering, **R**) | USB debug channel: ADJ op 0x902B runs shell commands without a gate (feature map 10f, **V**), `sdk api` shooting calls | A host program, no firmware change. Untested | **I** |
| **My Menu**, Menu Recall, press-and-hold times, frame count limiter, World Time | E-M1 III; E-M1; E-M1 II; STYLUS 1 | Menu list tables (128 rows per list) | Low value | **I** |
| **Zebra** | OM-1 1.9 | Own peaking hook (mark by level, not by edge). Live view already has the Highlight&Shadow warning | Low value | **I** |
| **Silent (electronic) shutter**, then Pro Capture, Live ND, Flicker Scan | E-M1 4.6; E-M1 II 3.7 | Live Time proves read-out with the shutter open. Full read-out takes 24.3 ms (hardware notes) | No body with this sensor shipped it. Needs an exposure start and end by sensor commands: the EFCS work comes first | **U** |
| **LV Boost On2 / Night Vision**, Starry Sky AF | E-M1 4.6; OM-1; E-M1 III | Live View Boost, contrast AF | Slow live-view sensor mode: **U** | **U** |
| **High Res Shot** | E-M5 II 4.1 | The stabiliser moves the sensor in X and Y | Whether its H8 controller takes a fixed offset of half a pixel: **U**. Then an 8-frame merge. Lowest rank | **U** |
| **Keystone, Fisheye Compensation, Focus Stacking, in-camera panorama** | E-M1 4.6, E-M1 II, E-PL9 | GPU, distortion resampler | Large. Better done on a PC | **I** |

## 6. IMPOSSIBLE (hardware)

| Feature | First body | Evidence |
|---|---|---|
| Built-in Wi-Fi, Bluetooth, phone remote, GPS log, field sensors | E-P5; E-PL9; E-M1 III | No radio (manual; **V**). The E-P5 has a radio module with its own tasks. FlashAir transfer works on the stock body |
| EVF functions (S-OVF, EVF style, AF Targeting Pad for a built-in finder), Fn lever, second dial, mode-dial custom modes C1 to C5, Selfie Assist | E-M1 and later | No finder, lever, mode dial or tilting screen (manual; **V**). Mysets stay available |
| 5-axis and Sync IS, Handheld Assist, hand-held High Res | E-M5; OM-1 | 2-axis unit (manual; **V**) |
| 1/8000 s, 1/320 s sync | E-P5 | 1/4000 shutter unit (manual; **V**) |
| 4K, C4K, 10-bit, H.265, OM-Log / HLG with real gain, 120 fps Full HD | E-M1 II and later | Sensor records and encoder (hardware notes; **I** strong) |
| Phase-detect AF functions: AF Focus Adjust, C-AF sensitivity and tracking of that kind, subject detection | E-M1; OM-1 | No phase-detect pixels (**R**); subject detection runs on a later processor (**I**) |
| Dual card slots, USB charging, USB PD, webcam mode, headphone output, microphone jack options | E-M1 II and later | One slot, no charge circuit, no jacks (manual; **V**). Webcam needs a USB video class device: **U**, not checked |
| STYLUS 1 items: ND filter, step zoom, zoom framing assist | STYLUS 1 | Lens parts of that body |

## 7. Method

1. Download: `scripts/fetch_fw.py OUT CODE…` asks the maker's update catalog (the request of
   `tools/fetch_stock.py`, model code only). Unpack: `tools/oetool.py unpack`.
2. Expand: the E-M1 III and OM-5 main blocks and the E-M1 III, OM-1, OM-5 and OM-3 resource blocks
   hold olycompress containers (LZ4). `scripts/expand.py` expands them (own code; the format is
   described in the om-emu project).
3. Text: `scripts/lang_enu.py` finds the English blob by its footer `OlympusLanguage_enu`, walks
   back over the pointer array and takes the run-time base from the first pointer. It needs no
   constants per body and read all 22 tables. Its E-PM2 output equals the table that the level
   gauge work used.
4. Diff: `scripts/first_seen.py` lists the strings that are not in the E-PM2 table, by first body
   in release order (icon escapes folded). About 2,550 strings; they drove the feature list.
5. Evidence per feature: `scripts/feature_matrix.py` counts matching UI strings and main-block
   strings (`strings -n 5`; `dummy` names left out) per body → `results/feature-matrix.md`. Use
   `--show FEATURE CODE` to read the hits.
6. E-PL5 and E-PL6 in full: `scripts/menu_rows_diff.py` (Custom Menu rows, sub-item rows) →
   `results/menu-rows-epl5-epl6.txt`; panel child lists with the level-gauge scripts; settings by
   prm tag in the linear listings (`mov 57233,d0` = prm 0xDF91); function sizes from the E-PL6
   pairing of the level-gauge work.
7. Donor rank: `scripts/code_share.py` → `results/code-share.txt`.

Limits of this survey:

- The firmware versions are the latest ones. "First body" means first in this set; the version
  that added a feature comes from release notes where marked **R**.
- No function pairing was made for the E-PL5 or for any body later than the E-P5.
- ISO LOW and the small AF target are located by size differences and reference counts only.
- Not fetched (the server offers them): E-M1X, E-M5 III, OM-1 II, OM-5 II, the TG bodies, E-PM1,
  E-PL3, E-P3. Every body that was asked for was served.

## 8. Firmware files examined

Kept outside the repository (`/tmp/scratch/survey/fw/`). "Share" = E-PM2 code windows found
(`scripts/code_share.py`).

| Body | File | Size | sha256 | English ids | Share |
|---|---|---|---|---|---|
| E-M5 | `OLY_E_097_2300_0000_0000.BIN` | 46596096 | `cb158dbdd8092856e8060354b008369f7d33dff32a1204e966ef0d5bce85e535` | 1695 | 39.7% |
| E-PL5 | `OLY_E_100_1600_0000_0000.BIN` | 43319360 | `1355c2b8beaaae348654a208e1c0220a9a9273bd88dac408fd6fd01a0ccd0c01` | 1970 | 67.7% |
| E-PM2 | `OLY_E_101_1600_0000_0000.BIN` | 43319360 | `34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300` | 1970 | 100.0% |
| E-P5 | `OLY_E_108_1800_0000_0000.BIN` | 44826624 | `cc59a4e13b3bf6c46405bd396975cb9c93a7634b7a4a36822259b1fc498b5cfd` | 2317 | 36.8% |
| E-M1 | `OLY_E_109_4600_0000_0000.BIN` | 69206016 | `0fa4b14cb6361eddfbe6f9e94b4f5e3ded428a522fda79d2ce747bab34b21339` | 2573 | 18.6% |
| STYLUS 1 | `OLY_E_111_2004_0000_0000.BIN` | 75235328 | `48557bf653b1fff945ce4e5815f16cb904e05df2bd787e7f285ed9e17ac7bdef` | 1123 | 30.2% |
| E-PL6 | `OLY_E_112_1400_0000_0000.BIN` | 43319360 | `f7b76ac82d545148bfc1c00bc165fb855b2e7d044dcaae1033601496e1bd116f` | 1974 | 66.5% |
| E-M10 | `OLY_E_113_1400_0000_0000.BIN` | 70254592 | `84d81b2dbd80ea2e94ec70e35acbba0e3193ccee8b51db14976fd0d9c4e3590c` | 2391 | 22.2% |
| E-PL7 | `OLY_E_115_1400_0000_0000.BIN` | 66060288 | `cd9b09af9705e31570252fd7501f92fc11c1e6fd555e30e103f4f05e9944501b` | 2426 | 20.6% |
| E-M5 II | `OLY_E_118_4100_0000_0000.BIN` | 89522176 | `c03050db130b051e446fa08dec1ad6f29afc890308888383428f4938a57edef0` | 2699 | 16.2% |
| E-M10 II | `OLY_E_120_1400_0000_0000.BIN` | 69599232 | `ff9d302318ecf6e06c0b31c181fc6a185e93623e819749db31cec7977fa92052` | 2667 | 16.5% |
| PEN-F | `OLY_E_122_3101_0000_0000.BIN` | 87031808 | `77398610b379f80238117f31a6d5bbf65d608b49ec563666c64d84367e969f2c` | 2892 | 15.6% |
| E-M1 II | `OLY_E_125_3700_0000_0000.BIN` | 93050944 | `691a8a8e90af75b3848b70856a3a49ef24d72394cdfd2766fa37bdfe6325de70` | 3384 | 13.1% |
| E-PL8 | `OLY_E_126_1100_0000_0000.BIN` | 66060288 | `923aab3d8e761c3b4a3108bcc6059b10ff6a9055a0630e0aea8a4707c59daeeb` | 2536 | 20.4% |
| E-M10 III | `OLY_E_130_1200_0000_0000.BIN` | 91445280 | `a2283338a79f8d0fa212d9a6d2677b9b686f6a9cd4bd664fd9b0709af63f94e1` | 3426 | 13.4% |
| E-PL9 | `OLY_E_133_1101_0000_0000.BIN` | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` | 3506 | 13.4% |
| E-M1 III | `OLY_E_139_1600_0000_0000.BIN` | 109838336 | `4f9ea315a2f2280dd5746abc39b5e4b038f183836eadfbe9d96b266e49a09aac` | 3929 | 11.1% |
| E-M10 IV | `OLY_E_140_1100_0000_0000.BIN` | 111017984 | `73b42ea52db8d7cd59b4450e93175529438b0bce6baa793ce009d5bc73d212cd` | 3612 | 11.5% |
| E-P7 | `OLY_E_142_1100_0000_0000.BIN` | 111017984 | `9d1610124ad98f6edae4540182205f06c9c703d9033ef0c4f19847193f95eaeb` | 3645 | 11.5% |
| OM-1 | `OLY_E_143_1900_0000_0000.BIN` | 240779264 | `342954a48b60bb900614791d6c44d2ba88a67e7a0e03a065069160daa5fbd75a` | 4702 | 10.4% |
| OM-5 | `OLY_E_144_1200_0000_0000.BIN` | 92274688 | `a0c91f3ac7caaf0925b2af609e711183cf3b5982b3333224bcef26c0c5943d11` | 4013 | 11.0% |
| OM-3 | `OLY_E_147_1100_0000_0000.BIN` | 240517120 | `8c133084414533159f587bf46bfb4152714c4074312a47c8d8503e33d605696d` | 4848 | 9.9% |
