# In-camera look editing and look import: requirements and limits

The owner's ask, kept here so work does not drift from it. Change this file first when the ask changes.
Labels: V verified on the camera, I inferred, U unknown.

## The ask (owner, 2026-11-18)

With the E-PM2's hardware as it is, can EPM2Mod give users what the newer-body mods (Caduceus on the E-P7 and OM-3,
oly_fw_analysis on the PEN-F, om10mi-mods on the E-M10 I) give theirs:

1. **In-camera edits:** change a film simulation in the camera's own menus and see the result in live view.
2. **Look import:** load a look made from a LUT onto the camera.

Not a copy of their 12-colour wheel (the E-PM2 has no 12-colour stage, `docs/feasibility.md`), but the same kind
of experience on the stages this camera has.

## Conditions

1. Sort each feature by evidence: confirmable deterministically at low effort, needs a planned camera round with
   pass marks fixed beforehand, or research.
2. Ask for camera work only when it settles a named question; say what it cannot settle.
3. Tell users only what is measured (rule 7 in `docs/feasibility.md`). No "any LUT", "exact", "matches the film".
4. Write the limits down plainly.

## Out of scope

Not asked; do not plan or build without a new ask here: an editor or preview in the installer or the browser,
Lightroom `.xmp` import, Add Effects options, the hunt for a hidden colour stage, a 12-colour wheel.

## The camera's colour stages

One look sets these, in this order. All of them are tables that a look file replaces at run time (V, card-looks-4),
and a forced refresh updates the next photo and live view (V, `experiments/2026-11-17-card-looks/design.md`
section 9.2.1).

| Stage | What it can do |
|---|---|
| 3x3 colour matrix | Mix red, green and blue: white balance shift, tint, colour mix, a global hue turn |
| Six-axis hue and saturation (R, Y, G, C, B, M) | Hue and saturation in 6 broad colour regions, about 60 degrees each |
| Tone curve per channel (R, G, B) | Contrast, Blacks, Whites, fade, split toning |
| Saturation and saturation by brightness | Overall saturation, and saturation in shadows or highlights |

Absent as far as known: a 3D LUT, 12-colour control, lightness per colour, any stage where a colour change depends
on both hue and brightness.

## 1. In-camera edits

### What the stages allow

| Edit | On the E-PM2 |
|---|---|
| Hue and saturation per colour | 6 colours, not 12 (coarser than the colour-wheel mods) |
| Lightness per colour | No: no stage |
| Contrast, Blacks, Whites, fade, split toning | Yes: tone curves |
| White balance shift, tint, colour mix | Yes: matrix |
| Overall saturation | Yes |
| Live view shows the edit | Yes: the refresh mechanism works (V) |

The camera renders its own result, so the accuracy of our computer model does not matter for this feature.

### Limits (firmware, not image processing)

| Limit | Status |
|---|---|
| No editor screen exists and no slider widget is known. An editor is built from menu rows; each added row needs a relocated copy of the menu table (done before for Load Looks, Peaking, Debug Log) | V for rows; slider U |
| Each edited value needs a setting to store it. Only setting 448 is known free; an editor needs about 15 values | U: more dormant settings not searched |
| Code space: 679 B of code and about 1.4 KB of segment 3 are proven free; an editor needs several KB. The large areas (95 KB, 123 KB) are not proven on the camera | U |
| Menu rows run no code when their value changes; code polls at each key, as Load Looks does | V |
| 128 rows per menu list | V |

### Feasibility

Image processing: feasible, with 6 colours and no per-colour lightness. Firmware: unknown. Code space and value
storage are the blockers. Settling them needs emulator work and one probe flash (questions: free settings for
about 15 values; a proven code area of 2 KB or more; live-view lag after an edit). Highest cost and risk of the two.

### Next steps (owner chose this first, 2026-11-18)

| Step | Settles | Where | Status |
|---|---|---|---|
| 1 | The editor's controls (provisional below; the owner may change them) | owner | provisional |
| 2 | Settings for the rows to show values: about 15 that no stock code uses. They are scratch values only; the edit is stored in the look store, which already persists | emulator and code reading, `settings.md` | running |
| 3 | Rows with numbers (for example -7 to +7), reusing stock value lists if possible; acting on a change; live view behind the menu | emulator and code reading, `rows.md` | running |
| 4 | Code size of a minimal editor against free space; more space from the PENPAL (PP-1 Bluetooth) code if needed (owner's idea) | code reading, `space-penpal.md` | running |
| 5 | One probe flash: code from a new area, live view after a row change and its lag, the edit after a restart | camera, after 2 to 4 | not started |

Provisional controls (step 1): edits apply to the film simulation in use. Hue and saturation for each of the 6
colours (12 rows), contrast, Blacks, Whites, warmth, tint and saturation (6 rows). Each about -7 to +7.

## 2. Look import

### What carries over from a LUT

There is no LUT stage, so a LUT is approximated by the four stages above (the fit runs on a computer; the result
is a look file for Load Looks, V).

| What the LUT does | Carries over |
|---|---|
| Global colour shift, contrast, film-like tone | Yes |
| Different tone per channel (tinted shadows or highlights) | Yes |
| Broad hue or saturation shifts | Yes, in 6 regions |
| Per-colour lightness, hue changes that depend on brightness, narrow edits (skin only) | No, approximate at best |

### Evidence

The 19 film simulations are LUT imports: fitted from spektrafilm LUTs, then measured on the camera
(`docs/film-emulation.md` section 4): natural colours 1.06 to 1.44 dE, ColorChecker 1.36 to 1.96 dE, out-of-range
colours 12 to 17 dE. Film-like LUTs: V. Other creative LUTs: U, and the stronger the LUT the worse the fit.

### Limits

| Limit | Status |
|---|---|
| A `.cube` file does not state its input encoding (sRGB, V-Log, a camera log). A wrong guess gives a wrong look: the user must choose, or only LUTs with a known input are accepted | V (format fact) |
| The fitter is an experiment script that needs numpy and scipy (`experiments/2026-11-09-film-portra/fit_film2.py`); it runs on a computer | V |
| Fit quality differs per LUT; it must be shown per LUT, not promised | condition 3 |

### Feasibility

Feasible for film-like LUTs with a known input encoding (done 19 times). Other LUTs: per-LUT quality, offered only
with that LUT's fit error shown.

## Open questions

Add here; answer with a label and a source.

1. In-camera edits: which dormant settings can hold editor values? (emulator)
2. In-camera edits: is 2 KB or more of the large code areas usable? (one probe flash)
3. Look import: fit error for creative LUTs that are not film-like? (desk: fit a set of LUTs)
