# Shoot 1: reference data (manual)

33 shots + 1 RAW Data Edit, about 45–60 min. Purpose and use of each set: [NOTES.md](NOTES.md) §4.
The analysis checks every shot's settings from its EXIF, so a mistake is caught later. If you
notice one, just retake the shot; don't delete anything.

## Before you start

### Monitor
- [ ] Show `out/chart_<W>x<H>.png` for your screen **full screen at 100 %** (no scaling).
  Other sizes: `python3 make_chart.py W H`.
- [ ] Brightness at **maximum**. Turn off auto-brightness, night light / blue-light filter, sleep and
  dimming. Keep the laptop on the charger (battery saver dims the screen).
- [ ] Room dark, no reflections on the screen.

### Camera position
- [ ] Tripod, camera square to the screen and centred on it.
- [ ] Chart fills about 70–80 % of the frame, all four white corner squares visible.
- [ ] Focus on the chart, switch to **MF**, then turn the focus ring very slightly off to soften
  the screen's pixel grid (moiré). Leave zoom and focus unchanged for the whole chart session.

### Camera settings (keep for every shot unless the table says otherwise)
- [ ] Shooting mode **M**, **ISO 200**, aperture **f/8** (fixed for the whole session).
- [ ] Image quality **RAW+JPEG**, largest size, finest JPEG (YSF if enabled in K Set, else YF).
- [ ] WB **5300K preset** (sun icon). Not Auto.
- [ ] Picture Mode **Natural**, Contrast / Sharpness / Saturation **0**, Gradation **Normal**.
- [ ] Highlight&Shadow Control **0**. Colour Space **sRGB**. Aspect **4:3**.
- [ ] Image Stabilizer **Off**. Face priority **Off**. Art effects / frames **Off**.
- [ ] Noise Reduct. **Off** (no dark frames on the slow brackets). Noise Filter **Standard** (default).
- [ ] Shading Comp. **Off** (default).
- [ ] Drive **2 s self-timer** (no shake).

### Find the base shutter speed T0
1. Turn on the Highlight & Shadow live display (INFO; see the manual p. 84). Red = clipped.
2. Change the shutter speed until the **white** gray patch (bottom right) **just** turns red.
3. Go **1 stop faster** (3 clicks). That speed is **T0**. Write it down: T0 = ______
4. T0 must be **1/4 s or slower**, so that the fastest bracket (T0 ÷ 8) is still 1/30 s or slower
   and the screen does not flicker into the picture. If T0 comes out faster than 1/4 s, close the
   aperture (f/11, then f/16) and repeat. Write the aperture down if it is not f/8: ______
5. Flicker check: take one test shot at the fastest speed you will use (T0 ÷ 8, and T0 ÷ 16 for
   I2). Zoom in on playback. If you see horizontal bands, tell me before you go on.

## Shot list

"Base" = everything as above at T0. Each row changes only what it lists. **Put the setting back
to base after each row** unless the next row is in the same group.

| # | Group | Change from base | Shutter |
|---|---|---|---|
| B1 | Tone bracket | — | T0 ÷ 8 (−3 EV) |
| B2 | Tone bracket | — | T0 ÷ 4 (−2 EV) |
| B3 | Tone bracket | — | T0 ÷ 2 (−1 EV) |
| B4 | Tone bracket | — (this is the reference ORF) | **T0** |
| B5 | Tone bracket | — | T0 × 2 (+1 EV) |
| B6 | Tone bracket | — | T0 × 4 (+2 EV) |
| B7 | Tone bracket | — | T0 × 8 (+3 EV) |
| M1 | Modes | Picture Mode **Vivid** | T0 |
| M2 | Modes | Picture Mode **Muted** | T0 |
| M3 | Modes | Picture Mode **Portrait** | T0 |
| M4 | Modes | Picture Mode **Monotone** (B&W Filter: none, Pict. Tone: none) | T0 |
| M5 | Modes | Picture Mode **i-Enhance** (Effect: default) | T0 |
| G1 | Gradation | Natural, Gradation **High Key** | T0 |
| G2 | Gradation | Natural, Gradation **Low Key** | T0 |
| G3 | Gradation | Natural, Gradation **Auto** | T0 |
| N1 | Natural | Contrast **−2** | T0 |
| N2 | Natural | Contrast **+2** | T0 |
| N3 | Natural | Saturation **−2** | T0 |
| N4 | Natural | Saturation **+2** | T0 |
| P1 | Portrait | Picture Mode Portrait, Contrast **−2** | T0 |
| P2 | Portrait | Portrait, Contrast **+2** | T0 |
| P3 | Portrait | Portrait, Saturation **−2** | T0 |
| P4 | Portrait | Portrait, Saturation **+2** | T0 |
| A1 | Art filters | Picture Mode **Pop Art**, option **I** | T0 |
| A2 | Art filters | **Pale&Light Color**, option **I** | T0 |
| A3 | Art filters | **Light Tone**, option **I** | T0 |
| A4 | Art filters | **Cross Process**, option **I** | T0 |
| I1 | ISO | Natural, **ISO 800** | T0 ÷ 4 |
| I2 | ISO | Natural, **ISO 3200** | T0 ÷ 16 |
| W1 | White balance | Natural, ISO 200, WB **3000K preset** (tungsten icon) | T0 |
| W2 | White balance | WB **Auto** | T0 |
| D1 | Drift check | Back to base, WB 5300K (a repeat of B4) | T0 |
| R1 | Test bench | **No shot.** Playback → B4 → OK → **RAW Data Edit → [Current]** (camera at base settings) | — |

Then one real scene (any time; daylight is best, a lamp is fine):

| # | Change | Notes |
|---|---|---|
| S1 | New framing: a still life with a gray card or white paper, a hand (skin), a plant, a sky-blue and a red or orange object. Base settings, but set WB to suit the light and choose the exposure normally. | Smooth areas, nothing clipped. Write down the WB used: ______ |

## Afterwards

- [ ] Copy the whole `DCIM` folder from the card to `out/shoot-1/` (keep the card copy too).
- [ ] Note anything unusual (flicker, a retake, a shot out of order) at the bottom of this file.

Notes from the shoot:
