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
| Each row needs a setting and its own picker panel. 23 settings are free, but only 3 free setting/panel pairs exist, so a row per control is not possible without moving the panel table | R, E (`settings.md`, `rows.md`) |
| Code space: an editor needs about 450-600 B of code and 2.7 KB of data (I); the proven space fits it tightly. The PENPAL radio patch code (57,523 B) can be freed with 3 patches (R, `space-penpal.md`) | I, R |
| The menu covers live view: an edit shows only after leaving the menu | E |
| Menu rows run no code when their value changes; code polls at each key, as Load Looks does | V |
| 128 rows per menu list | V |

### Feasibility

Image processing: feasible, with 6 colours and no per-colour lightness. Firmware: feasible as two menu rows
("Look Edit" picks a control, "Value" sets -7..+7), not yet tried on the camera. The experience is the weak part:
about 10 presses per control, no live view while editing, the result seen after leaving the menu.

**Status: paused by the owner (2026-11-18).** Compared with the other mods: the PEN-F, E-P7 and OM-3 mods add their
controls to a stock colour screen that is drawn over live view; the only TruePic VI mod (fenykl, E-PL3) uses menu
rows as this design does. Not explored: whether a stock live-view screen of this body (iAUTO Live Guide sliders,
Highlight & Shadow) could host the edits. Resume from step 5 below or from that question.

### Next steps (owner chose this first, 2026-11-18)

| Step | Settles | Where | Status |
|---|---|---|---|
| 1 | The editor's controls (provisional below; the owner may change them) | owner | provisional |
| 2 | Settings for the rows to show values: about 15 that no stock code uses. They are scratch values only; the edit is stored in the look store, which already persists | emulator and code reading, `settings.md` | done: 23 free settings (R, E). The limit is picker panels: each row needs its own, and only 3 free setting/panel pairs exist (448/609, 442 and one more; `settings.md`) |
| 3 | Rows with numbers (for example -7 to +7), reusing stock value lists if possible; acting on a change; live view behind the menu | emulator and code reading, `rows.md` | done: a -7..+7 row with stock glyphs works (E). The menu covers live view: the edit shows after leaving the menu (E). Recommended: two rows, "Look Edit" (which control) and "Value" (-7..+7) |
| 4 | Code size of a minimal editor against free space; more space from the PENPAL (PP-1 Bluetooth) code if needed (owner's idea) | code reading, `space-penpal.md` | done: editor about 450-600 B code and 2.7 KB data (I), fits proven space tightly. PENPAL: a 57,523 B chunk (the PP-1 radio's patch code) frees with 3 small patches (R); no loss without a PP-1 attached |
| 5 | One probe flash: code from a new area, live view after a row change and its lag, the edit after a restart | camera, after 2 to 4 | not started |

Decision for the owner: two rows (works with the free pairs found; one control at a time) or a row per control
(needs about 18 new picker panels, which means moving the 312-entry panel table: cost U).

Provisional controls (step 1): edits apply to the film simulation in use. Hue and saturation for each of the 6
colours (12 rows), contrast, Blacks, Whites, warmth, tint and saturation (6 rows). Each about -7 to +7.

## 2. Look import

**Status: next (owner, 2026-11-18).**

### What it is

A user brings a `.cube` LUT, a computer turns it into one EPM2Mod look, and the camera loads it with Load Looks
into an ART slot under the look's own name (names show in the menus: V, camera log, card-looks-3 and -4,
"Cyan Test").

### What carries over from a LUT

There is no LUT stage, so a LUT is approximated by the four stages above.

| What the LUT does | Carries over |
|---|---|
| Global colour shift, contrast, film-like tone | Yes |
| Different tone per channel (tinted shadows or highlights) | Yes |
| Broad hue or saturation shifts | Yes, in 6 regions |
| Per-colour lightness, hue changes that depend on brightness, narrow edits (skin only) | No, approximate at best |
| Black-and-white | Yes, as a black-and-white record (kind 2) |

### Two kinds of LUT

| Kind | What its input is | How the fit uses it | Status |
|---|---|---|---|
| Log LUT (film emulation, "technical" LUTs) | A camera log encoding: V-Log, LogC3, S-Log3, F-Log, ... | The scene's linear light is encoded to the LUT's input, the LUT's output is the target. This is how the 19 films were made (V-Log) | V for V-Log; other log curves: encodings to add, formulas are published |
| Display LUT (most "creative" LUTs) | An image that is already rendered: Rec.709 or sRGB | The target is the LUT applied to the camera's own Natural rendering of the scene. The model renders Natural to about 0.9 dE (stock modes it was not fitted on: 0.86-0.92) | I: not yet done |

The file does not say which kind it is. The user chooses; there is no reliable automatic guess.

### End-to-end flow

1. The user has a `.cube` file and chooses its input (a list: Rec.709/sRGB, V-Log, LogC3, S-Log3, ...).
2. The fit runs on the user's computer (section "Where the fit runs") and gives a report: the colour error on
   natural colours, greys, skin and the ColorChecker; which colours it cannot reach; a good / fair / poor mark.
3. The user picks an ART slot and a name (up to 16 characters).
4. The look is written to the card as `EPM2LOOK.BIN` (with the other slots' looks kept as they are).
5. On the camera: MENU, Custom Menu J, Load Looks, Load. The slot shows the new name (V).

### Where the fit runs

| Part | Needs | Status |
|---|---|---|
| The fitter and the camera model (`fit_film2.py`, `model2.py`) | numpy, scipy; move into the package with tests | V as experiment code |
| The stock tables the model reads (`mocklib.py`, 0x7E74E9BC and the default tone tables) | Read from the user's own downloaded firmware (the installer already downloads it); never shipped by us | I |
| A command first: `epm2mod looks import FILE.cube --input rec709 --slot ARTn --name NAME` | `uv run` gets numpy and scipy for the command | I |
| The installer page later | The release is standard library only: add the fit's packages at first use, or a small solver of our own | out of scope until the command works |

### Claims (condition 3)

| Can say | Evidence |
|---|---|
| "Film-like LUTs in V-Log work well" | V: 19 films, camera-measured |
| "This LUT's fit: N dE on natural colours (computed)" | The fit's own number, shown per LUT, marked as computed |
| "Measured on the camera within N dE of the fit" | Only after round R2 below |
| Never | "Any LUT", "exact", "matches the original LUT" |

Fit values that go beyond the range the 19 films span are not measured on the camera. Until R2, the fitter keeps
the parameters inside that range and says so when a LUT needs more.

### Limits

| Limit | Status |
|---|---|
| A `.cube` file does not state its input encoding; a wrong choice gives a wrong look | V (format fact) |
| Strong creative LUTs (narrow hue edits, per-colour lightness) fit poorly | I, measured by step L2 |
| Movies get only part of a look (the film curves only in Kodachrome and Superia 400) | V (`docs/film-emulation.md` section 7) |
| Other white balance presets than daylight: untested | U |
| Only `.cube`. `.xmp`, Hald PNG and other formats: out of scope | owner |

### Steps

| Step | Settles | Where | Camera? |
|---|---|---|---|
| L1 | Fitter and model in the package, same results as the experiment code | desk | no |
| L2 | How well LUTs fit: a test set of free LUTs (film emulations and creative LUTs, log and display), each fitted; the error spread per kind. Used only for testing, not shipped | desk | no |
| L3 | Display LUTs: the target built on the model's Natural rendering; its fit error | desk | no |
| L4 | Log encodings other than V-Log (LogC3, S-Log3, F-Log) | desk | no |
| L5 | The `looks import` command with the report and the clamp to the films' range | desk | no |
| R2 | Camera check: 3 to 5 imported looks (one film-like, one display LUT, one strong creative LUT), one RAW Data Edit of the test RAW each. Pass: camera within 1 dE of the fit's own prediction on natural colours | camera, no flash (pinned build) | **yes**, about 10 minutes |

L2 decides if the feature is worth offering beyond film-like LUTs: if most creative LUTs fit poorly, the feature
is "film-like LUTs only" and says so.

## Open questions

Add here; answer with a label and a source.

1. In-camera edits (paused): could iAUTO Live Guide or Highlight & Shadow host edits over live view? (emulator)
2. In-camera edits (paused): code from the PENPAL chunk on the camera? (one probe flash)
3. Look import: fit error for creative and display LUTs? (L2, L3)
4. Look import: camera vs fit for imported looks? (R2)
