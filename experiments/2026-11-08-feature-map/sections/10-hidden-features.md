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
| Art effects | Active (inf) | **Active (verified).** One effect at a time from a per-filter list | Values at 0x7EFE8664 |

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
| Bluetooth/PENPAL | Dormant; gate = I/O pin 0x1709 | **Hardware-gated, complete.** 0x1709 is the "Cube" bit of the external-device byte, set only when an accessory with ID 0x0103 answers | |
| "E-PM2 has no accessory port" | product knowledge | **UNRESOLVED from firmware.** The E-PL5 (which has the port) carries byte-identical menu and accessory tables | Top menu table (370 B) and accessory ID tables (148 B) found byte-identical in the E-PL5 (checked by hand) |
| Accessory-port menu | Dormant | **CORRECTED → hidden by a setting default** (info 394 = 0), as on the E-PL5 | |
| EVF / mic / accessory strobe | Dormant | **Hardware-gated**: one accessory-ID scan decides all of them | |
| Eye-Fi, FlashAir SPC | Active (inf) | **Code complete.** SPC is a Playback-menu row; show/hide rules not traced | |
| USB modes | types 0–6 open | **Resolved:** Storage → 0, Print → 1, MTP → 4, PTP → 5. X3C (types 2/3) has no requester: Dormant (inf) | |
| IEEE 1394 | Stub | **Stub (confirmed)** | |
| Firmware-update files | 9 types | **Card update only in the boot-time update mode** (power-on cause + the "OK" key status). The menu loads lens/flash files only | |

### Playback (10d) and debug/service (10f)

*Pending; added when those sections are finished.*

## What changed overall

*Filled in after all six sections are compiled.*
