# 10 — Second pass: every "hidden" feature re-checked

The first pass named features from their strings and assumed whether they could be reached. Section 09 (art filters) showed that this produced confident errors. This pass re-checks every feature that `docs/firmware-map.md` marked hidden, dormant, stub, unknown or "active (inferred)". Each one went through the same steps:
1. read the code;
2. trace reachability (menu tables, mode-controller value lists, setting writes, model and hardware gates, debug shells);
3. compare it across 8 bodies;
4. use external sources only as corroboration;
5. give each earlier claim a verdict.

Detail is in 10a–10f. Coordinator spot checks are in `../NOTES.md`.

**Status words:**
- **Active**: a user can reach it in normal use.
- **Hidden (debug-only)**: complete code that only debug shells can reach.
- **Dormant-complete**: complete code with no route on this body.
- **Hardware-gated**: needs an accessory or lens.
- **Stub**: the entry point does nothing.
- **Absent**: the name exists but there is no code.

**Bodies compared:**
- TruePic VI: E-PM2 1.6, E-PL5 1.6, E-PL6 1.4, E-P5 1.8.
- TruePic VII: E-M10 1.4, E-PL7 1.4, E-M5 II 4.1, PEN-F 3.1.

## Verdicts

### Shooting (10a, 10b)

| Feature | First pass | Now | Evidence (key) |
|---|---|---|---|
| Interval shooting + time-lapse movie | Dormant (inf) | **Dormant-complete (verified).** It shipped on E-PL6, E-P5, E-M10 and E-PL7 | E-PM2 top menu: `… 182 Multiple Exposure, 526 RC Mode …`. E-PL6 inserts 1357 "Time Lapse Settings" between them (both checked by hand). The E-PL5 code is byte-identical to the E-PM2's |
| HDR BKT (info 476) | "not offered" | **Probably Active (inferred).** No code hides the row. Shoots exposures only; there is no HDR merge | The Bracketing panel row filter does not touch group 15 (10a). Worth a 5-second check on the camera |
| AE/WB/FL/ISO/ART BKT, Live Bulb/Time, multiple exposure, anti-shock, custom self-timer | Active / not listed | **Active (verified)** | Live Bulb interval = setting 436 × 500 ms |
| Live Composite, keystone, focus bracketing | — | **Absent** | Only orphan `dummy` name strings |
| 3D Photo | Dormant (inf) | **CORRECTED.** SCN 115 is selectable. **Hardware-gated:** complete with a 3D lens. The two-shot mode is a **stub** (three empty functions) | SCN list 0x7E84976D ends `110, 111, 112, 115` (checked by hand) |
| Panorama | Active (inf) | **Active** (PC-assist). In-camera stitching: **Absent** | SCN 14 on all 8 bodies |
| e-Portrait | Active | **Active** (shooting and playback edit). "Beauty Fix" variants: **stub/absent**, never shipped | |
| Smile detection | "stubbed" | **CORRECTED → Absent** (orphan name string) | |
| SCN list | 12 iAuto types (inf) | **23 fixed SCN entries, all selectable.** 8 SCENE_PROGRAM entries (Party, Self Portrait, Cooking, 3× Underwater, Animal, Snow) are never offered on any of the 8 bodies | |
| Art effects | Active (inf) | **Active (verified selection).** One effect at a time from a per-filter list. The step from the setting to the `art_effect_*` module is inferred (10b §6) | Values at **0x7EFE866C** (12-byte records; 0x7EFE8664 is inside the last "Filter Type" row 0x7EFE8660) (A10 2026-11-09) |

### Movie (10c)

| Feature | First pass | Now | Evidence (key) |
|---|---|---|---|
| AVCHD | Unknown | **CORRECTED → Hidden (debug-only), code complete.** In no body's movie-quality list | info-45 list = 6 entries {quality, format, Fine/Normal}: 1080/720 MOV F/N, 720 MJPEG, VGA MJPEG; no format 2 (checked by hand) |
| Movie effects | Active (inf) | **Active (inferred).** Gated by Custom Menu "Movie Effect" (info 444); handlers verified; trigger probably the touch icons | |
| "PSP" | Unknown | **CORRECTED → Dormant (inf).** The background layer of a 4-window "multi-through" live view. Probably the first form of **Photo Story** (shipped from the E-PL7 on) | |
| Movie tele-converter | "absent" (section 04) | **CORRECTED → code exists** in the app/GUI layers (reachability not traced) | |
| QVGA/160×120 MJPEG, 60 fps, `mov set`/`ansh` | advertised | **Not reachable** (no GUI value / not implemented) | |
| Movie art filters | 100–120 accepted | **Only the 12 shipped**; the movie art check rejects the hidden codes | |

### Connectivity and accessories (10e)

| Feature | First pass | Now | Evidence (key) |
|---|---|---|---|
| Bluetooth/PENPAL | Dormant; gate = I/O pin 0x1709 | **Hardware-gated, complete: active with a PENPAL attached** (the E-PM2 has the port). 0x1709 is the "Cube" bit of the external-device byte, set only when an accessory with ID 0x0103 answers | |
| "E-PM2 has no accessory port" | product knowledge | **WRONG (corrected 2026-11-09).** The firmware could not decide it, since the E-PL5 tables are identical, but Olympus's v1.2 release notes add VF-4 EVF support, so the port exists | Top menu table (370 B) and accessory ID tables (148 B) found byte-identical in the E-PL5 (checked by hand) |
| Accessory-port menu | Dormant | **CORRECTED → hidden by a setting default** (info 394 = 0), as on the E-PL5 | |
| EVF / mic / accessory strobe | Dormant | **Hardware-gated**: one accessory-ID scan decides all of them | |
| Eye-Fi, FlashAir SPC | Active (inf) | **Code complete.** SPC is a Playback-menu row; show/hide rules not traced | |
| USB modes | types 0–6 open | **Resolved:** Storage → 0, Print → 1, MTP → 4, PTP → 5. X3C (types 2/3) has no requester: Dormant (inf) | |
| IEEE 1394 | Stub | **Stub (confirmed)** | |
| Firmware-update files | 9 types | **Card update only in the boot-time update mode** (power-on cause + the "OK" key status). The menu loads lens/flash files only | |

### Playback (10d)

| Feature | First pass | Now | Evidence (key) |
|---|---|---|---|
| Photo Surfing, Event View, Collection, Collage, person/GPS search | Stub | **Stub backend AND no GUI path** (verified). Fails safe. None of the 8 bodies has a real backend or English text | No API interface, operation class, sdk group or GUI string |
| Light box | Active (inf) / unknown | **CORRECTED → Active**: a full single-play sub-state with 23 GUI call sites (menu entry inferred) | |
| Calendar, index, select, print order (DPOF), protect, erase | Active (inf) | **Active (verified GUI calls)** | |
| Edit: aspect, colour, trim, resize, shadow, red-eye, e-Portrait, RAW, image overlay | Active (most) | **Active (verified, 9 interfaces)** | |
| EditCalendar, CopyPicture, PlayPanorama, PlayContinuous, PlayCw, EventView components | unknown | **Dormant**: no requester | |
| 23 edit modes | Active (most) | **Partly corrected**: 4 Bluetooth modes Dormant; picture registration a Stub; 2 unresolved | |
| 3D (MPO) playback | Dormant | **CORRECTED → Partial, likely Active on a 3D HDMI TV** (MPO loader, 3D slideshow type, HDMI 3D query, "3D Show" panel verified) | |
| BGM import | Active | **Active (confirmed)**: menu flow "BGM Import"; only Olympus-authenticated WAVs | |
| Slideshow, transitions | inferred | **Active (verified)** | |
| Opening screen (registered picture) | inferred | **CORRECTED → Stub** (dummy registration API) | |
| Audio DSP | Active (inf) | **Split**: wind cut is user-switched (Custom Menu "Wind Noise Reduction", prm 0x7871; checked by hand). ReTune/EQ/notches/DRC are fixed tables | |

### Debug and service (10f)

| Feature | First pass | Now | Evidence (key) |
|---|---|---|---|
| S_SHELL | serial port; "CPU0 regs" | **Hidden; started every boot.** CORRECTED: 0x9870/0x9830 are two serial *ports* chosen by a config byte, not two CPUs. Only physical UART access is needed | |
| U_SHELL (54 families) and the shells behind it (`prmdbg`, `app`, `sdk api`, `mov`, `lens`, `cam`) | Hidden | **Confirmed.** Reached only via the S_SHELL `:` mode or USB | |
| U_SHELL over USB (ADJ 0x902B) | reachable | **Confirmed, gate traced.** No model, setting or password gate: it needs only a Storage/PTP connection type and an ADJ session. Accept table of 22 {op, flag} pairs includes 0x902B (checked by hand); identical on 7 bodies | ADJ op 0x900D also writes settings directly |
| BASIC + RCU scripts | card load, flash autoload | **Confirmed. Trigger:** the card load comes from the GUI debug menu or `sdk api`, not at boot. A script saved in flash with the `ucr.` header runs at every BAS_RCU_SRV start | |
| BASIC overlay "loaded on demand" | on demand | **CORRECTED (inferred strong)**: loaded in normal use (the same step starts the movie tasks) | |
| ADJSLF / self-adjust menu | trigger unknown | **Gated by the factory flag** PRM_MODE_SHIPS_ENABLE (prm 0x0DB1) = 0 plus wake reason SELF_ADJUST. Dormant on a shipped camera (inferred) | |
| SS_DEBUGMENU | entry unknown | **Contents found** (Life Test, BASIC script register/erase, Color setting). **Entry found but gated** (13d §4.3 (D1 2026-11-09)): key sequence in HIDE_MODE, behind getShippingInfo(4); retail pass unknown | |
| Version-check menu | "hidden" | **CORRECTED (10f §4.3)**: not the Firmware screen (that item starts CAM_MISC_FIRMUP). The CA VERCHK sub-app is requested by the same hidden gate that opens HIDE_MODE (PostEventToCA(11, 11) at 0x7EDFD69E, after getShippingInfo(4) = 1) | (A10 2026-11-09) |
| USRTEST_A–D | dormant | **Dormant (confirmed)**: nothing starts them | |

## What changed overall

About 20 earlier claims were wrong or incomplete. They fall into three kinds:

1. **"Dormant/hidden" that is really reachable or hardware-gated:**
   - 3D Photo (selectable; needs a 3D lens);
   - 3D playback (HDMI 3D);
   - light box;
   - the accessory-port menu (a setting default, not removed);
   - HDR BKT (probably offered).
2. **"Unknown" or "active" that is really hidden:**
   - AVCHD (no menu value on any body);
   - "PSP", the precursor of Photo Story;
   - the opening-screen registration (stub);
   - the X3C USB mode (no requester).
3. **Wrong mechanism or detail:**
   - the PENPAL gate is an accessory-ID bit, not a raw pin;
   - the S_SHELL ports;
   - smile detection is absent, not stubbed;
   - the movie tele-converter exists;
   - the BASIC overlay is loaded in normal use;
   - section 06's "menu code" range is the shooting state controller.

**Confirmed as hidden or dormant, with the reason now known:**

| Feature | Why it is hidden |
|---|---|
| Interval shooting / time-lapse | Only the menu row is missing; it shipped on E-PL6/E-P5/E-M10/E-PL7 |
| Art Magic Filters | Section 09 |
| Picture-database modes | No backend and no GUI on any body |
| Bluetooth/PENPAL, EVF | Accessory gate |
| Self-adjust | Factory flag |
| USRTEST tasks | Nothing starts them |

**What the firmware cannot settle:**
- ~~Whether the E-PM2 has an accessory port.~~ Answered later: yes (v1.2 release notes add VF-4 support).
- **Whether HDR BKT appears on the camera.**
- ~~**How SS_DEBUGMENU is entered.**~~ Found (13d §4.3); what the firmware cannot settle is whether a retail body passes the getShippingInfo(4) gate (D1 2026-11-09).

## Open questions (cross-section)

1. Is HDR BKT visible in Shooting Menu 2 › Bracketing on a real E-PM2? (A 5-second check on the camera.)
2. ~~How is SS_DEBUGMENU entered~~ (found, 13d §4.3 (D1 2026-11-09)), and which power-on cause gives wake reason 9 (self-adjust)?
3. What is the X3C PTP mode? (The opcode set is known; it has no requester.)
4. Which key or event opens light box, 3D Show and BGM Import (GUI handler tables 0x7EFD5E00 / 0x7EFD6754 / 0x7EFD7AA4)? Answered in 13d §4.3; 0x7EFD6754/0x7EFD7AA4 are entry-function arrays (D1 2026-11-09).
5. Custom Menu A–J item lists: the record table at 0x7EFF8250 (10d) is a candidate. Answered: the table starts at 0x7EFF7E80; 0x7EFF8250 is page H (13d §5) (D1 2026-11-09).
