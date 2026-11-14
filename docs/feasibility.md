# What is feasible on the E-PM2, and what the real limits are

Date: 2026-11-14. Evidence: [experiments/2026-11-14-feasibility/](../experiments/2026-11-14-feasibility/).

## Why this file exists

For the first week this project changed only tables that the stock code reads. That was a choice,
not a limit. The choice was made before anyone measured the hardware, the free space or the stock
routines. This file records what the measurements show, so that nobody repeats the assumption.

**The rule: a limit counts only if a measurement, a datasheet or the firmware itself proves it.**
"It could be risky" and "we have not tried" are not limits. They are tasks.

## What the evidence says about risk

- **A bad flash has always been recoverable here.** Two builds froze live view (`slots7-kind`,
  `remap7-code`). A normal card update put the camera back each time, in minutes.
- **New code works.** Three patch specs with new machine code are in the pinned build and passed
  camera tests (`remap7b-code`, `seven-fixes-1`, `interval-timelapse-v2`).
- **Others went much further on the same family.** The Caduceus mods for the OM-3 and the E-P7 add an
  on-camera editor, files loaded from the card and new menu entries. Their first camera-tested
  editor was 8.2 KB of code. They report one boot loop on each body, both recovered by a normal card
  update, and no permanent brick.
- **One real gap:** this body has no recorded recovery from a boot loop. Code and hooks that stay in
  segments 2 and 3 do not run on the update path (inferred from the load map), so the updater stays
  reachable. A deliberate boot-loop test needs the owner's agreement.

## Real limits

| Limit | Kind | Basis |
|---|---|---|
| 1/4000 s shutter, 1/250 s flash sync | Hardware | Manual |
| 2-axis stabiliser: no 5-axis, no high-res shot | Hardware | Manual, firmware strings |
| No radio, no viewfinder, no microphone jack | Hardware | Manual |
| No 4K, no RAW video | Hardware | Sensor modes in the firmware (table 0x7E7BA370); card path about 25 to 28 MB/s (measured on the E-M5) |
| 1080p at 30 fps only; the 60, 120 and 240 fps modes drop most lines | Hardware, as far as known | Sensor mode table; no sensor register map found |
| No 3D lookup table; the hue stage has six axes | Image processor | Firmware search; measured stages |
| A look is a set of ROM tables chosen by art-filter number | Firmware design | Read from the firmware. Tables at a RAM address are **untested**, not impossible |
| 128 rows in one menu list | Firmware | Camera-tested |
| No emulator boots this body; `tools/emu` runs single functions | Tooling | om-emu has no E101 model |

## What the body has

| Resource | Finding | Label |
|---|---|---|
| Processor | Two MN103 cores, uITRON; hardware face detector; GPU | Verified from the firmware |
| RAM | 512 MiB | Inferred from address use |
| Accelerometer | 3-axis, with a driver task and a roll/pitch interface | Verified |
| Code space proven on the camera | 320 bytes, and since 2026-11-14 the area at 0x7EBF1F00 (the first area that had only passed the static checks: code ran there at the first attempt) | Verified |
| Code space that passes every static check | 17,578 bytes, never executed | Verified by scan; needs a camera probe |
| More candidates | 7.2 KB dead 3D helpers; 124 KB debug handlers; 579 KB 3D and slideshow stack; 1.59 MB of the main block that is never loaded | Static only |
| Data space | Blank tails in blocks 1, 2 and 3: 11.1 MB, 130 KB, 677 KB (flash only) | Verified bytes; updater behaviour unknown |
| Memory allocator | `scheap` pools, table 0x7E7348E4; 16 KB blocks: alloc 0x7E507325, free 0x7E507333 | Verified |
| File routines | open 0x7E5C52DC, write 0x7E5C5339, seek 0x7E5C53A5, close 0x7E5C5308, read 0x7E5C536F | Verified from a stock caller (read: argument order inferred) |
| Load a card file by name pattern | 0x7E5437F0, used by the lens update for `DCOLYMP/L???????BIN` on a normally booted camera | Verified |
| Menus | Data tables (list table 0x7F00D710); value records can be re-pointed | Camera-tested for one setting |
| Hidden art-filter numbers | 110 to 118 exist in the pipeline switches, with no menu value | Verified in code; untested on the camera |
| Add Effects (Soft Focus, Pin-Hole, White Edge, Frame, Star Light) | Per-filter data lists at 0x7E849E2B to 0x7E849E5A | Verified; on a film slot untested |

## What is feasible

**Low effort: data edits, one camera check each**

- Add Effects on a film look (glow, vignette, white edge, frame).
- More film entries through the hidden numbers 110 to 118.
- Higher video bitrate and no 29-minute limit (`experiments/2026-11-12-hardware/`, patches written,
  not flashed).

**Medium effort: new code, method known**

- Looks loaded from a file on the card.
- ~~Level gauge~~ **Done on 2026-11-14 with three data edits and no code.** The whole feature was in
  the firmware; only a menu row was missing. Lesson: compare with the E-PL6 first. It shares 58,642
  identical functions with this body (the E-P5: 21,940).
- The other E-PL6 additions (small AF target, ISO LOW), ported as interval shooting was.
- A simple on-camera editor made from existing menu lists.

**High effort: port or write**

- Focus peaking, from the E-P5 (same processor generation; an art-engine live-view effect there).
  In work since 2026-11-14: `experiments/2026-11-14-focus-peaking/NOTES.md`.
- Zero-second anti-shock (electronic first curtain).
- Colour grain, halation.
- A custom editor screen.
- Live Composite.

Not in this firmware at all (no text, no code): focus peaking, Color Creator, keystone, focus
bracketing, zebra, silent shutter. These must be ported or written. They are not hidden features.

## Unknowns, and the probe that settles each

| Unknown | Probe |
|---|---|
| Does code run from the statically checked free areas, and from RAM? | A small routine there that writes a marker to a card file |
| Which task and moment are safe for file reads? | Start with the half-press event, as Caduceus does. Never at start-up, never during capture |
| Does the image engine accept tables at a RAM address? | Point one film slot at a RAM copy of its own table |
| Can the load range be made longer to reach the unloaded 1.59 MB? | The Caduceus method: move the end word in steps, with a pattern and a checksum reported to a card file |
| Does the updater write the blank tails of blocks 1 to 3? | Write a marker there, read it back with 0x7E6756B5 |
| Does this body recover from a boot loop by card update? | Owner's decision |

## Order of work

1. A half-press hook that does nothing.
2. A file write, for a log channel.
3. A file read.
4. The code-space and RAM-table probes, reported through the log.
5. Features, one per flash.

## Rules for people and agents who work on this

1. Do not call something impossible or unsafe without the evidence. Say what is verified, what is
   inferred and what is unknown.
2. When something is unknown, propose the smallest camera probe that settles it. Do not route around
   it.
3. New code is normal here. Use it when it is the direct way to the feature.
4. The owner flashes and decides. Give the build, the sha256, what the test checks and how to go
   back. Do not hold back a build because it adds code.
5. Keep the real safety steps: the camera log before and after each flash, the stock file at hand,
   the free-space check for a candidate, one change per flash.
6. Do not spend rounds on polish (fit accuracy, tooling reviews) while a feature question is open.
