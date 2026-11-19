# Light Box on the E-PM2

Date: 2026-11-19. Desk work only. Nothing was built or flashed.

Status: the owner agreed to the acceptance criteria (§5) on 2026-11-19 and deferred the work. Release Lag-Time was
deferred the same day.

Labels: **V** verified (firmware bytes, manual), **I** inferred, **U** unknown.

## 1. What Light Box is

A playback display of the E-PL5 and E-PL6 (E-PL6 manual p.86). It shows two pictures side by side. The user keeps one
picture on the left and steps through the others on the right. Both can be zoomed and scrolled together, so two
near-identical shots can be compared for focus or expression. It is one stop of the INFO cycle in single-picture
playback.

## 2. What the E-PM2 has

| Part | E-PM2 | Label |
|---|---|---|
| Light Box screen code | `CmpPLgh_PlayLightBoxComponent` 0x7EB33B24–0x7EB38D5D, `OlyApi PlayLightBox` 15 methods (0x7E9C6BCF start …), `OlyHfwOpePlyLightBox` | **V** (feature map 06, 16a) |
| States | SsPlaySingle 15 `DISP_LIGHTBOX_PREPARE`, 16 `DISP_LIGHTBOX`, 20 `DISP_LIGHTBOX_ZOOM`, and SCROLL, MOVE, SETBASE | **V** (feature map 10d) |
| INFO-cycle step | `CPlaySingleFrame::getJumpState` 0x7ED09135 | **V** (read for this note, §3) |
| Setting 257 (▶ Info → Light Box) | prm 0x9171[4], 42 GUI readers | **V** |
| Setting 321 (▶ Close Up Mode) | prm 0x91A1, default 1 (mode1), read by the playback zoom 0x7ED0F9D0 and by getJumpState | **V** |
| Text 868 "Light Box", text 208 "▶ Close Up Mode" | in the text table | **V** |
| Panel 198 (Light Box On/Off), panel 130 (Close Up Mode) | panel records present | **V** |
| Menu row ▶ Info → Light Box | **missing** | **V** |
| Custom Menu row ▶ Close Up Mode | **missing** | **V** |

## 3. The rule in the code

getJumpState, the INFO key in single-picture playback (**V**, disassembly 0x7ED093D8–0x7ED0941C and
0x7ED095E8–0x7ED0960F):

1. Read setting 257 and setting 321.
2. If 257 = 1 (Light Box On) **and** 321 = 2 (mode2) and the check 0x7ED009D6 passes, set the display mode
   (info 27) to 11 and return.
3. In display mode 11, the next INFO press goes to state 15 `DISP_LIGHTBOX_PREPARE` when 257 = 1 and
   0x7ED00A1D passes.

This is the rule of the E-PL6 manual: "[▶ Close Up Mode] in the custom menu must be set to [mode2] to show this
display." The two checks 0x7ED009D6 and 0x7ED00A1D are not read (**I**: picture count or file type).

So the feature needs both menu rows. No code.

## 4. Plan

Follow Olympus's design: both rows, as on the E-PL5. mode2 is a feature of its own: "Press the zoom button to
display the zoom frame for the specified zoom ratio. Press it again to zoom in" (E-PL6 manual p.75).

A smaller alternative exists and is not chosen: only the Light Box row, plus a 2-byte patch at 0x7ED09408 that drops
the mode2 test. Olympus required mode2 for a reason not yet read; the zoom inside Light Box may depend on it (**U**).

| Spec | What | Method |
|---|---|---|
| `custom-menu-rows-4` | Row ▶ Close Up Mode in Custom Menu D, where the E-PL5 has it (setting 321, panel 130, text 208, group 3) | As `custom-menu-rows-3` (`experiments/2026-11-17-auto-iso-min-shutter/scripts/mkspec_lss_menu.py`): an 84-row copy of the item table, the child list, the row constants, group D +1 |
| `light-box-row` | Row Light Box in Custom Menu D → Info Settings → ▶ Info (panel 191, setting 257, text 868) | As `level-gauge-lvinfo-row`: one sub-item row record re-used from the unreachable panel 594, and a 5-entry child list for panel 191 in free space |

## 5. Acceptance criteria

Each criterion is checked in the emulator (E) where the emulator can show it, else on the camera (C).

**The feature**

1. Custom Menu D has the row **▶ Close Up Mode** with the values **mode1** and **mode2**. A camera that never set it
   shows mode1. (E)
2. Custom Menu D → Info Settings → **▶ Info** has a fifth row, **Light Box**, which can be switched on and off like
   the other rows. It is off at first. (E)
3. With Light Box on and Close Up Mode mode2, pressing INFO in single-picture playback reaches a display with two
   pictures side by side. (C)
4. In that display, the user can choose the picture on each side, zoom in on both, and scroll both. (C)
5. With Close Up Mode mode2, pressing the playback zoom button shows a zoom frame first, and a second press zooms
   in. (C)
6. Both settings are kept after power-off. (C)

**Nothing that works today breaks**

7. Every other Custom Menu row is where it was and works: Peaking, Lowest S/S Setting, Load Looks, Debug Log,
   Level Adjust and the stock rows. (E: menu crawl against the pinned build)
8. The other ▶ Info rows and the LV-Info rows (Level Gauge) are unchanged. (E)
9. With Light Box off, or with Close Up Mode mode1, playback, the INFO cycle and playback zoom behave as today. (C)
10. Shooting, film simulations, peaking, interval shooting and the level gauge work as today. (C, short checks)

## 6. Open points

| Point | How it is settled |
|---|---|
| Whether the emulator can show playback with a picture (needed for criteria 3 to 5 in E) | Try with a card folder holding two E-PM2 JPEGs. Until now no real JPEG was tried in playback |
| Which button zooms in playback on the E-PM2 | The emulator, or the E-PM2 manual's playback page |
| What 0x7ED009D6 and 0x7ED00A1D check | Desk, before the camera test |
| Free space for a 48-byte child list and 16 more bytes of item table | `tools/freespace.py` |
