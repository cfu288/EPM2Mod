# Shoot 1: reference data (manual, handheld)

31 shots + 1 RAW Data Edit, about 45 min. Purpose and use of each set: [NOTES.md](NOTES.md) §4.
The analysis reads every shot's settings from its EXIF, so nothing needs writing down and a mistake
is caught later. If you notice one, just retake the shot; don't delete anything.

**Handheld is fine.** The shots do not have to line up: the analysis finds the four white corner
squares in each photo and locates every patch separately, and the actual exposure of each patch is
measured from the RAW. What handheld does require: short times (1/10 or shorter, so no shake),
the stabilizer on, and all four corner squares in every chart shot.

## Before you start

### Monitor
- [ ] Show `out/chart_<W>x<H>.png` for your screen **full screen at 100 %** (no scaling).
  Other sizes: `python3 make_chart.py W H`.
- [ ] Brightness at **maximum**. Turn off auto-brightness, night light / blue-light filter, sleep and
  dimming. Keep the laptop on the charger (battery saver dims the screen).
- [ ] Room dark, no reflections on the screen.

### Holding the camera
- [ ] Stand or sit so the chart fills about **70–80 %** of the frame, with **all four white corner
  squares visible** in every chart shot. Keep the zoom ring where it is for the whole session.
- [ ] Face the screen squarely each time (laptop screens change colour with viewing angle; small
  differences are fine).
- [ ] Brace your elbows on the table and press the shutter gently.
- [ ] Focus: normal AF (S-AF) on the chart is fine.

### Camera settings (keep for every shot unless the table says otherwise)
- [ ] Shooting mode **M**, **ISO 200**, **f/5.6**, **1/40 s** (screen shows `F5.6` and `40`).
  Measured handheld on 2026-11-09 with the procedure under "New screen" below.
- [ ] Image quality **RAW+JPEG**, largest size, finest JPEG (YSF if enabled in K Set, else YF).
- [ ] WB **5300K preset** (sun icon). Not Auto.
- [ ] Picture Mode **Natural**, Contrast / Sharpness / Saturation **0**, Gradation **Normal**.
  The Live Control panel (OK) only picks the mode. For the adjustments: **MENU → Shooting Menu 1 →
  Picture Mode → highlight the mode → press ▶ (right)**, not OK (manual pp. 59–60). Each mode keeps
  its own values. Only in P/A/S/M, not iAUTO/ART/SCN.
- [ ] Highlight&Shadow Control **0**. Colour Space **sRGB**. Aspect **4:3**.
- [ ] Image Stabilizer **S-IS1** (on; manual p. 46). Face priority **Off**. Art effects / frames **Off**.
- [ ] Show the Custom Menu first (hidden by default): **MENU → Setup (wrench) → c/# Menu Display →
  c Menu Display: On** (manual p. 69). A gear tab appears.
- [ ] Noise Reduct. **Off**: **Custom Menu → V Exp/p/ISO → Noise Reduct.** (p. 74). Noise Filter,
  just below it: **Standard** (default).
- [ ] Shading Comp. **Off** (default): **Custom Menu → X K/Color/WB → Shading Comp.** (p. 75).
- [ ] Drive: **single frame**.

### Controls and screen notation
In M: press the **F button** (▲), then **▲/▼ change the shutter time** and **◀/▶ change the
aperture** (manual p. 26). Each press moves **one position** on the scales below (⅓ stop). If one
press jumps further, set Custom Menu → V Exp/p/ISO → EV Step → 1/3EV (that item only sets the
step size; it is not exposure compensation).

The screen shows a fraction as its denominator only (`40` = 1/40 s); whole seconds use a `"` mark.

```
time      brighter ◄  8  10  13  15  20  25  30  40  50  ► darker      (screen 40 = 1/40 s; only 10, 20, 40 are used)
aperture  brighter ◄  F5.6  F6.3  F7.1  F8  F9  F10  F11  F13  F14  F16  F18  F20  F22  ► darker
```

## Shot list

"Base" = all settings above (f/5.6, 1/40, ISO 200, Natural, WB 5300K). Each row changes only what it
lists. **Put the setting back to base after each row** unless the next row is in the same group.
Contrast, Saturation and Gradation are set through MENU → Shooting Menu 1 → Picture Mode → ▶ (see
above); the art filters are in the same Picture Mode list.

| # | Group | Change from base | Aperture | Time | Screen shows |
|---|---|---|---|---|---|
| B1 | Tone bracket | 2 stops darker | f/11 | 1/40 | `F11` `40` |
| B2 | Tone bracket | 1 stop darker | f/8 | 1/40 | `F8.0` `40` |
| B3 | Tone bracket | **base: this is the reference ORF**. Flicker check: zoom in on playback; horizontal bands = pause and tell me | f/5.6 | 1/40 | `F5.6` `40` |
| B4 | Tone bracket | 1 stop brighter | f/5.6 | 1/20 | `F5.6` `20` |
| B5 | Tone bracket | 2 stops brighter | f/5.6 | 1/10 | `F5.6` `10` |
| M1 | Modes | Picture Mode **Vivid** | f/5.6 | 1/40 | |
| M2 | Modes | Picture Mode **Muted** | f/5.6 | 1/40 | |
| M3 | Modes | Picture Mode **Portrait** | f/5.6 | 1/40 | |
| M4 | Modes | Picture Mode **Monotone** (B&W Filter: none, Pict. Tone: none) | f/5.6 | 1/40 | |
| M5 | Modes | Picture Mode **i-Enhance** (Effect: default) | f/5.6 | 1/40 | |
| G1 | Gradation | Natural, Gradation **High Key** | f/5.6 | 1/40 | |
| G2 | Gradation | Natural, Gradation **Low Key** | f/5.6 | 1/40 | |
| G3 | Gradation | Natural, Gradation **Auto** | f/5.6 | 1/40 | |
| N1 | Natural | Contrast **−2** | f/5.6 | 1/40 | |
| N2 | Natural | Contrast **+2** | f/5.6 | 1/40 | |
| N3 | Natural | Saturation **−2** | f/5.6 | 1/40 | |
| N4 | Natural | Saturation **+2** | f/5.6 | 1/40 | |
| P1 | Portrait | Picture Mode Portrait, Contrast **−2** | f/5.6 | 1/40 | |
| P2 | Portrait | Portrait, Contrast **+2** | f/5.6 | 1/40 | |
| P3 | Portrait | Portrait, Saturation **−2** | f/5.6 | 1/40 | |
| P4 | Portrait | Portrait, Saturation **+2** | f/5.6 | 1/40 | |
| A1 | Art filters | Picture Mode **Pop Art**, option **I** | f/5.6 | 1/40 | |
| A2 | Art filters | **Pale&Light Color**, option **I** | f/5.6 | 1/40 | |
| A3 | Art filters | **Light Tone**, option **I** | f/5.6 | 1/40 | |
| A4 | Art filters | **Cross Process**, option **I** | f/5.6 | 1/40 | |
| I1 | ISO | Natural, **ISO 800** (2 stops more sensitive, so 2 stops smaller aperture) | f/11 | 1/40 | `F11` `40` |
| I2 | ISO | Natural, **ISO 3200** (4 stops; afterwards back to ISO 200 and f/5.6) | f/22 | 1/40 | `F22` `40` |
| W1 | White balance | Natural, ISO 200, WB **3000K preset** (tungsten icon) | f/5.6 | 1/40 | |
| W2 | White balance | WB **Auto** | f/5.6 | 1/40 | |
| D1 | Drift check | Back to base, WB 5300K (a repeat of B3) | f/5.6 | 1/40 | |
| R1 | Test bench | **No shot.** Playback → B3 → OK → **RAW Data Edit → [Current]** (camera at base settings) | — | — | |

Then one real scene (any time; daylight is best, a lamp is fine):

| # | Change | Notes |
|---|---|---|
| S1 | New framing: a still life with a gray card or white paper, a hand (skin), a plant, a sky-blue and a red or orange object. Base settings, but set WB to suit the light and choose the exposure normally (1/30 or shorter). | Smooth areas, nothing clipped. |

## Afterwards

- [ ] Copy the whole `DCIM` folder from the card to `out/shoot-1/` (keep the card copy too).
- [ ] Retakes and out-of-order shots are fine: the analysis sorts by the settings in each file.
  If something odd happened, just tell me.

## New screen or different light: finding the base exposure

Only needed if the monitor, its brightness or the room changes. Nothing to write down.
1. Turn on the Highlight & Shadow live display: **Custom Menu → U Disp/8/PC → G/Info Settings →
   LV-Info → tick Highlight & Shadow** (manual pp. 72, 84), then press **INFO** while shooting until
   it shows. Red = clipped.
2. Set **1/40** (`40`). Make the aperture **wider** (◀/▶ towards smaller F numbers), one press at a
   time, until the **white** gray patch (bottom right) **just** turns red.
3. Make the aperture **3 presses smaller** (one stop darker). That is the base aperture.
4. If the white patch is red even at F22, lower the screen brightness one notch and repeat.
5. Shift every aperture in the shot list by the same number of presses.

History (2026-11-09): the tripod version of this procedure gave 1/15 at f/10, then 1/2.5 at f/20.
That predicted 1/30 at f/5.6; measured handheld it was 1/40 at f/5.6 (⅓ stop darker), which is the
base now. The tripod plan used a 7-shot bracket from −3 to +3 stops by
shutter time; the handheld plan uses 5 shots from −2 to +2 because the 36-step gray row already
covers most of the tone curve at the base exposure.

## Shoot 1 log (2026-11-09, checked from EXIF and a contact sheet)

Files are in `shots/` (git-ignored by this folder's `.gitignore`). All chart shots: M, 17 mm,
MF with a deliberate slight defocus (against moiré), 4:3, sRGB, Noise Reduct. off, Noise Filter Standard, Shading Comp. off, Image Stabilizer
**off** (planned on; fine at 1/40 and 17 mm, blur is checked in extraction). LibRaw decodes the
ORFs: 4640×3472, black level 255, **the sensor saturates at 4045** (not the nominal 4095).
`UnknownBlock1` is present (5,764 bytes).

| Shot | File (PB09…) | Settings found | Status |
|---|---|---|---|
| B1–B5 | 0185–0189 | f/11, f/8, f/5.6 at 1/40; f/5.6 at 1/20, 1/10 | OK |
| M1–M5 | 0190–0194 | Vivid, Muted, Portrait, Monotone, i-Enhance | OK |
| G1–G3 | 0195–0197 | High Key; Low Key; Auto (exiftool: "Normal; Auto-Override") | OK |
| N1 | 0198 | Natural, Contrast −2 | OK |
| N2 | 0220 | Natural, Contrast +2 (retake; 0199 is a duplicate of N1, Contrast −2) | OK |
| N3, N4 | 0200, 0201 | Natural, Saturation −2, +2 | OK |
| (extra) | 0202 | Natural, all 0 (a second base shot) | Extra base |
| P1–P4 | 0203–0206 | Portrait, Contrast −2/+2, Saturation −2/+2 | OK |
| A1–A4 | 0207, 0209, 0210, 0211 | Pop Art, Pale&Light Color, Light Tone, Cross Process (option I; exiftool tag `ArtFilterEffect`, not `ArtFilter`) | OK |
| (extra) | 0208 | Soft Focus | Extra |
| I1, I2 | 0212, 0213 | ISO 800 f/11; ISO 3200 f/22 | OK |
| W1 | 0214 | **Custom WB 3200K** (not the 3000K preset) | OK for the purpose (a tungsten-range WB) |
| W2 | 0215 | Auto WB | OK |
| D1 | 0216 | Base repeat | OK |
| (extra) | 0217–0219 | f/16 1/40, f/22 1/40, f/22 1/80 | Extra darker bracket (useful for the curve toe) |
| (extra) | 0221 | Natural, all 0 (a third base shot) | Extra base; source of R1 |
| R1 | 0222 (JPEG only) | RAW Data Edit → [Current] of **0221** (not 0187) | **OK: test bench valid** (below) |
| S1 | PA310087, PA310117 (2026-10-31) | Outdoor, cloudy, **Portrait** mode, Auto WB, 1/400 | Use as the real-scene samples (Portrait is the slot to be replaced) |

Data notes:
- Base exposure (f/5.6, 1/40) saturates the **green** raw channel on 0.1–0.2 % of the chart area
  (the brightest patches); red and blue stay below 2,600. Those patches are excluded at base; the
  darker brackets (0185, 0186, 0217–0219) cover them unclipped.
- The small bright dot on the chart from 0195 on is the **mouse cursor**. It falls inside one
  patch; per-patch medians (or masking that patch) make it harmless. Next time, hide the cursor.
- **Test bench result:** 0222 (RAW Data Edit of 0221's ORF) is **pixel-identical** to 0221's
  in-camera JPEG (4608×3456, max difference 0). All EXIF tags are the same. The files differ only
  in 22,441 bytes of an undecoded binary block from file offset 195 (in 0221 mostly 0x5A filler, in
  0222 data; probably a record of the edit). So **RAW Data Edit reproduces the camera's JPEG
  exactly**: one ORF can be the test input for every later firmware round.
- **Focus:** at full resolution a patch is about 100 px wide with about 10 px of blur at each edge;
  patch centres are flat. No in-focus shot needed; extraction uses the patch centres.
- First visual hint for phase 1e: **Cross Process (0211) renders the black screen surround green**,
  so its shadows are not neutral, which points to channel-dependent curves in the art-filter path.
  To be measured.
