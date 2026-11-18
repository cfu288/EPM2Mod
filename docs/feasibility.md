# Feasibility and real limits

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
| No colour wheel: no 12-colour hue, saturation and lightness editor as on the PEN-F, E-P7, OM-3 and the E-M10 I mod | Image processor, as far as known | No 12-record colour table in the firmware. See "Colour wheel and twelve colour editors" below |
| A look is a set of ROM tables chosen by art-filter number | Firmware design | Read from the firmware. Tables at a RAM address are **untested**, not impossible |
| 128 rows in one menu list | Firmware | Camera-tested |
| The emulator shows no camera picture | Tooling | It has no image processor, no sensor and no mechanism. Since 2026-11-14 it does boot the firmware from reset and draws the shooting screens and the whole menu system, with keys, saved settings and an SD card (see "The emulator" below) |

## What the body has

| Resource | Finding | Label |
|---|---|---|
| Processor | Two MN103 cores, uITRON; hardware face detector; GPU | Verified from the firmware |
| RAM | 512 MiB | Inferred from address use |
| Accelerometer | 3-axis, with a driver task and a roll/pitch interface | Verified |
| Code space proven on the camera | 320 bytes, and since 2026-11-14 the area at 0x7EBF1F00 (the first area that had only passed the static checks: code ran there at the first attempt), and the blank run in the kernel range at 0x7E4C9200 (420 bytes of focus-peaking code; 0x7E4C90CA–0x7E4C9800 is the area) | Verified |
| Code space that passes every static check | 17,578 bytes, never executed | Verified by scan; needs a camera probe |
| More candidates | 7.2 KB dead 3D helpers; 124 KB debug handlers; 579 KB 3D and slideshow stack; 1.59 MB of the main block that is never loaded | Static only |
| Data space | Blank tails in blocks 1, 2 and 3: 11.1 MB, 130 KB, 677 KB (flash only) | Verified bytes; updater behaviour unknown |
| Memory allocator | `scheap` pools, table 0x7E7348E4; 16 KB blocks: alloc 0x7E507325, free 0x7E507333 | Verified |
| File routines | open 0x7E5C52DC, write 0x7E5C5339, seek 0x7E5C53A5, close 0x7E5C5308, read 0x7E5C536F | Verified from a stock caller (read: argument order inferred) |
| Load a card file by name pattern | 0x7E5437F0, used by the lens update for `DCOLYMP/L???????BIN` on a normally booted camera | Verified |
| Menus | Data tables (list table 0x7F00D710); value records can be re-pointed | Camera-tested for one setting |
| Menu texts at run time | The loaded language's text table is in RAM (blob 0xBFF3D000, its pointer array at the address in its first word); re-pointing a string id changes the text on screen, also after a language change when written again | Camera-tested 2026-11-17 (`card-looks-4`: loaded looks show their own names) |
| A dormant setting as an own menu row, kept after power-off | Setting 447 with the stock Off / On panel 608 (Custom Menu J, Debug Log); the firmware never writes it at start | Camera-tested 2026-11-18 (`log-menu`: On kept after power-off and after a flash) |
| RAM kept across power-off | The log's ring RAM 0x7E4F9000 keeps its content; bits can turn from 0 to 1 while the camera is off (seen twice, both before a start from USB) | Camera-tested 2026-11-18; the ring has a check word since `log-menu` |
| Settings memory for own data | The EEROM settings bank's unused tail, 53,680 bytes, saved by the firmware and by the bank save API 0x7E680272 | Camera-tested 2026-11-17 (looks kept after power-off without the card) |
| Hidden art-filter numbers | 110 to 118 exist in the pipeline switches, with no menu value | Verified in code; untested on the camera |
| Add Effects (Soft Focus, Pin-Hole, White Edge, Frame, Star Light) | Per-filter data lists at 0x7E849E2B to 0x7E849E5A | Verified; on a film slot untested |

## What is feasible

**Low effort: data edits, one camera check each**

- Add Effects on a film look (glow, vignette, white edge, frame).
- More film entries through the hidden numbers 110 to 118.
- Higher video bitrate and no 29-minute limit (`experiments/2026-11-12-hardware/`, patches written,
  not flashed).

**Medium effort: new code, method known**

- ~~Looks loaded from a file on the card~~ **Done on 2026-11-17** (`docs/guide/card-looks.md`): our own task
  reads the file at the first menu, the looks are kept in the EEROM settings bank's unused tail (53,680 bytes,
  empty on this camera, saved by the firmware) and written into the slot tables in RAM at every start.
- ~~Level gauge~~ **Done on 2026-11-14 with three data edits and no code.** The whole feature was in
  the firmware; only a menu row was missing. Lesson: compare with the E-PL6 first. It shares 58,642
  identical functions with this body (the E-P5: 21,940).
- The other E-PL6 additions (small AF target, ISO LOW), ported as interval shooting was.
- A simple on-camera editor made from existing menu lists.

**High effort: port or write**

- Focus peaking, from the E-P5: done 2026-11-14 (`experiments/2026-11-14-focus-peaking/NOTES.md`).
- Zero-second anti-shock (electronic first curtain).
- Colour grain, halation.
- A custom editor screen.
- Live Composite.

Not in this firmware at all (no text, no code): focus peaking, Color Creator, keystone, focus
bracketing, zebra, silent shutter. These must be ported or written. They are not hidden features.

## Colour wheel and twelve colour editors

Checked 2026-11-18 against the four public mods that have one, after users asked for it for older bodies.

**What the other mods do.** Each one adds new editor code that writes hue, saturation and lightness into a
12-record colour table that the image processor already has. None of them makes 12 colours out of fewer axes.

| Mod | Body (processor) | Stock colour features | What the mod changes |
|---|---|---|---|
| [oly_fw_analysis](https://github.com/fishcu/oly_fw_analysis/blob/HEAD/docs/color/pen-f/HSL_TABLES.md) | PEN-F (TruePic VII) | COLOR profiles: saturation of 12 colours | Hue and lightness written into the stock 12-record table (28 bytes per record) after the stock builder. "The native HSL tables also contain hue and lightness coefficients" |
| [caduceus-ep7](https://github.com/cakelesscoder/caduceus-ep7/blob/HEAD/docs/HSL_PORT.md) | E-P7 (TruePic VIII) | COLOR profiles, Color Creator | The same: "the native HSL tables already carry hue and lightness coefficients; stock firmware just doesn't expose them" |
| [caduceus-om3](https://github.com/androidfanman/caduceus-om3/blob/HEAD/docs/DEVELOPER_NOTES.md) | OM-3 (TruePic X) | COLOR profiles | The same, on the OM-3's colour builder |
| [om10mi-mods](https://github.com/Meghnus/om10mi-mods/blob/HEAD/docs/lookfile/LOOKFILE_SPEC.md) | E-M10 I (TruePic VII) | Color Creator only, no COLOR profiles | A 12-colour editor. "The camera has a 12-region table of hue shift, saturation and lightness per colour region": the table is in the hardware although no stock menu used it |

**What this means for the E-PM2 (TruePic VI).** The 12-colour table is a TruePic VII and later feature as far
as anyone has shown. The E-PM2 firmware has the six-axis hue and saturation stage (red, yellow, green, cyan, blue,
magenta) and no 12-record table, no Color Creator code and no colour-profile text. The PEN-F has a six-axis stage
of its own beside its 12-record table, so the six-axis stage found here does not point to a hidden 12-colour one.
No mod for a TruePic VI body (E-PL3, E-PL5, E-PL6, E-P5, E-M5, E-PM2) has a 12-colour editor. The E-P5 has no
Color Creator either (manual, verified in the 2026-11-15 survey).

**What is possible here:**

- A six-colour editor: hue and saturation for red, yellow, green, cyan, blue and magenta, written into the
  six-axis stage. It is coarser than a colour wheel (60 degrees per axis, not 30), and green, cyan and magenta are
  only approximate in our model of the stage (section 5 of `experiments/2026-11-14-feasibility/firmware.md`).
- A Color Creator-like control (one hue turn and one saturation for the whole picture) through the 3x3 colour
  matrix, which every film simulation already sets.
- Lightness per colour is not possible with the known stages.
- An editor like theirs on the stages we have, and `.cube` import fitted to those stages: research plan with
  probes in `experiments/2026-11-18-look-editor/NOTES.md`.
- A 12-colour editor needs a 12-colour stage in TruePic VI. It is not known whether the hardware has one. The
  probe is in the table below. Until a probe finds one, a 12-colour editor is not possible on this body.

## Unknowns and their probes

| Unknown | Probe |
|---|---|
| Does code run from the statically checked free areas, and from RAM? | A small routine there that writes a marker to a card file |
| ~~Which task and moment are safe for file reads?~~ | **Answered 2026-11-17 (camera):** the dormant task USRTEST_A, started from the GUI state hook at the first menu or playback screen, reads a 20 KB file (`builds/card-looks.json`) |
| ~~Does the image engine accept tables at a RAM address?~~ | **Answered 2026-11-17 (camera):** tables written in RAM at run time take effect in the next photo and in live view, after the boot init's cache refresh (`experiments/2026-11-17-card-looks/design.md` section 9.2) |
| Can the load range be made longer to reach the unloaded 1.59 MB? | The Caduceus method: move the end word in steps, with a pattern and a checksum reported to a card file |
| Does the updater write the blank tails of blocks 1 to 3? | Write a marker there, read it back with 0x7E6756B5 |
| Does this body recover from a boot loop by card update? | Owner's decision |
| Does TruePic VI have a 12-colour hue table that the firmware never uses? | Compare the image-library parameter builders with the PEN-F's COLOR builder (12 records, sectors interleaved as 2(r%6)+r/6). Check the unused art-filter entries: on the E-M10 I one held a hidden YCbCr colour key ([fishcu, e-m10/PROCESSING.md](https://github.com/fishcu/oly_fw_analysis/blob/HEAD/docs/color/e-m10/PROCESSING.md)). A missing string does not prove the hardware lacks it |

## Where code may go

The firmware loads in steps. The kernel and segment 1 are in RAM first. Segments 2 and 3 are copied
later, by the task Usr1, and on the update path they are not copied at all.

**A hook in the kernel or in segment 1 must jump only to code in the kernel or in segment 1**, unless
you have proof that the hooked function runs only after Usr1. The build `peaking-direct-2` broke this
rule: a hook in a segment-1 function that the boot task calls jumped into segment 2. The emulator
showed a crash at start-up before anyone flashed it. On the camera that is a boot loop, and it could
also break the update path, which is the only way back.

Check every build that adds a hook with the boot test of the emulator before a flash:
`tools/emu/boot-test builds/NAME.json` and `tools/emu/update-path-test builds/NAME.json`.

## The emulator

om-emu boots the E-PM2 firmware, stock or patched, from its reset vector on both cores. om-emu is
the git submodule `third_party/om-emu`: our fork ([github.com/cfu288/om-emu](https://github.com/cfu288/om-emu),
branch `e101`, MIT licence) of upstream om-emu, with the E-PM2's boot lab added in upstream's layout
(`emu/src/boot/`, `emu/bin/boot.mjs`). Set up once with `tools/emu/setup.sh`. How it works, the
stand-ins and the limits are in
[third_party/om-emu/docs/e101-boot-spec.md](../third_party/om-emu/docs/e101-boot-spec.md); our checks
and scripts in [tools/emu/boot/README.md](../tools/emu/boot/README.md). Upstream lists this camera
generation as "no work planned".

IMAGE is `stock`, `builds/NAME.json` or a `.BIN` file. No firmware is in the repository.

| Check | Command (from the repository root) | What it proves |
|---|---|---|
| Boot test | `tools/emu/boot-test IMAGE` | The image starts like stock: loader copies, both kernels, all tasks, the application. Exit status 0 = pass. It caught a build that would have crashed at every start |
| Update path | `tools/emu/update-path-test IMAGE` | With OK held and an update file on the card, the image finds the file as stock does |
| Menu screenshots | `tools/emu/emu-run IMAGE play.mjs OUTDIR STEP...` | The firmware's own menus, drawn by its own code, in English, as PNG files |
| Screenshot comparison | `tools/emu/boot/shotdiff.sh IMAGE_A IMAGE_B OUTDIR STEP...` | Which screens a patch changes |
| Menu crawl | `tools/emu/boot/crawl-all.sh CONFIG IMAGE...`, then `crawldiff.py` or `crawlcmp.py` | Every menu screen of two images, compared |
| Card | `E101_CARD=FOLDER tools/emu/emu-run IMAGE play.mjs ...` | A FAT card from a host folder mounts; the stock file routines work |

In this repository, `tools/emu/` has the scenario tests (whole call chains with real initial memory)
and `tools/emu/hookcheck.py` (the load-order check).

Trust it for: start-up, menus, lists, labels, the INFO screens, settings, card mount. Do not trust it
for: live view, the picture, capture, movies, timing, anything the mechanism or the sensor does. A
pass is evidence, not proof.

**Use it before every flash that changes a hook or a menu.** It also gives exact menu paths and
screen texts for the test instructions.

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
