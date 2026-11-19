# Feasibility and real limits

Evidence: [experiments/2026-11-14-feasibility/](../../experiments/2026-11-14-feasibility/).

Other Olympus generations, and what each can be modded to do: [model-matrix.md](../reference/model-matrix.md).

## Why this file exists

**The rule: a limit counts only if a measurement, a datasheet or the firmware itself proves it.**
"It could be risky" and "we have not tried" are not limits. They are tasks.

## What the evidence says about risk

- **A bad flash has always been recoverable here.** Five builds failed (three froze live view: `slots7-code`,
  `slots7-kind`, `remap7-code`, and two crashed: `peaking-direct-1`, `peaking-direct-3`). A normal card update
  recovered each.
- **New code works.** Nine patch specs with new machine code are in the pinned build and passed
  camera tests (`interval-timelapse-v2`, `peaking-direct-4`, `peaking-colours`, `peaking-fast`,
  `peaking-save-guard`, `stock-films-structure`, `card-looks-5`, `log-menu-2`, `lss-core`).
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
| No colour wheel in live view or movies: the 12-region hue, saturation and lightness stage runs for stills only | Image processor | Stage at 0x7E76C3C8, pipe A only ([caduceus review 05 §4](../../experiments/2026-11-11-caduceus-review/05-imaging-pipeline-and-limits.md#4-the-12-region-stage)) |
| A film simulation is a set of tables chosen by art-filter number | Firmware design | Read from the firmware. The tables are in RAM, and a Load writes them (camera-tested 2026-11-17) |
| 128 rows in one menu list | Firmware | Camera-tested |
| The emulator shows no camera picture | Tooling | It has no image processor, no sensor and no mechanism. Since 2026-11-14 it does boot the firmware from reset and draws the shooting screens and the whole menu system, with keys, saved settings and an SD card (see "The emulator" below) |

## What the body has

| Resource | Finding | Label |
|---|---|---|
| Processor | Two MN103 cores, uITRON; hardware face detector; GPU | Verified from the firmware |
| RAM | 512 MiB | Inferred from address use |
| Accelerometer | 3-axis, with a driver task and a roll/pitch interface | Verified |
| Code space proven on the camera | 320 bytes, and since 2026-11-14 the area at 0x7EBF1F00 (the first area that had only passed the static checks: code ran there at the first attempt), and the blank run in the kernel range at 0x7E4C9200 (420 bytes of focus-peaking code; 0x7E4C90CA–0x7E4C9800 is the area) | Verified |
| Code space that passes every static check | [code-space-map.md §4](../reference/code-space-map.md#4-totals-bytes) | Verified by scan; needs a camera probe |
| More candidates | 7.2 KB dead 3D helpers; 124 KB debug handlers; 579 KB 3D and slideshow stack; 1.59 MB of the main block that is never loaded | Static only |
| Data space | Blank tails in blocks 1, 2 and 3: 11.1 MB, 130 KB, 677 KB (flash only) | Verified bytes; updater behaviour unknown |
| Memory allocator | `scheap` pools, table 0x7E7348E4; 16 KB blocks: alloc 0x7E507325, free 0x7E507333 | Verified |
| File routines | open 0x7E5C52DC, write 0x7E5C5339, seek 0x7E5C53A5, close 0x7E5C5308, read 0x7E5C536F | Verified from a stock caller (read: argument order inferred) |
| Load a card file by name pattern | 0x7E5437F0, used by the lens update for `DCOLYMP/L???????BIN` on a normally booted camera | Verified |
| Menus | Data tables (list table 0x7F00D710); value records can be re-pointed | Camera-tested for one setting |
| Menu texts at run time | The loaded language's text table is in RAM (blob 0xBFF3D000, its pointer array at the address in its first word); re-pointing a string id changes the text on screen, also after a language change when written again | Camera-tested 2026-11-17 (`card-looks-4`: loaded film simulations show their own names) |
| A dormant setting as an own menu row, kept after power-off | Setting 447 with the stock Off / On panel 608 (Custom Menu J, Debug Log); the firmware never writes it at start | Camera-tested 2026-11-18 (`log-menu`: On kept after power-off and after a flash) |
| RAM kept across power-off | The log's ring RAM 0x7E4F9000 keeps its content; bits can turn from 0 to 1 while the camera is off (seen twice, both before a start from USB) | Camera-tested 2026-11-18; the ring has a check word since `log-menu` |
| Settings memory for own data | The EEROM settings bank's unused tail, 53,680 bytes, saved by the firmware and by the bank save API 0x7E680272 | Camera-tested 2026-11-17 (looks kept after power-off without the card) |
| Hidden art-filter numbers | 110 to 118 exist in the pipeline switches, with no menu value | Camera-tested 2026-11-18 (`stock-films`: 111, 112, 114, 115, 118 carry film simulations in stills, live view, movie and ART BKT) |
| Art filters switched at run time | Olympus's 12 filters stay in flash; a Load writes each entry's routing words and its RAM tables (0x7E4D1000, 0x3200 per entry); 30 hooks make ART BKT follow | Camera-tested 2026-11-18 (`stock-films`). For about 0.5 s at power-on, before the loader runs, the selected entry uses its Olympus code (code 88 seen once) |
| Add Effects (Soft Focus, Pin-Hole, White Edge, Frame, Star Light) | Per-filter data lists at 0x7E849E2B to 0x7E849E5A | Verified; on a film slot untested |

## What is feasible

**Low effort: data edits, one camera check each**

- Add Effects on a film simulation (glow, vignette, white edge, frame).
- Higher video bitrate and no 29-minute limit (`experiments/2026-11-12-hardware/`, patches written,
  not flashed).

**Medium effort: new code, method known**

- ~~Looks loaded from a file on the card~~ **Done on 2026-11-17** (`docs/guide/film-looks.md`): our own task
  reads the file when Load Looks → Load runs, keeps it in the EEROM settings bank's unused tail (53,680 bytes,
  empty on this camera, saved by the firmware) and writes each listed entry's tables into its RAM block. Every
  start applies the stored copy.
- ~~Lowest shutter speed for Auto ISO~~ **Done on 2026-11-19** (`lss-menu`, `lss-core`; GitHub issue #2). A copy of
  the PEN-F 3.1's logic in 641 B of segment-1 code; it matches the PEN-F's own code in the function harness and was
  camera-tested in P and A (`experiments/2026-11-17-auto-iso-min-shutter/NOTES.md` sections 11 and 12).
- ~~Level gauge~~ **Done on 2026-11-14 with three data edits and no code.** The whole feature was in
  the firmware; only a menu row was missing. Lesson: compare with the E-PL6 first. It shares 58,642
  identical functions with this body (the E-P5: 21,940).
- ~~Shooting information on the level gauge screen~~ **Done on 2026-11-19** (`gauge-info`, `gauge-bar-left-2`; GitHub
  issue #1). Data edits only: eleven layout lists of the live-view producers get the gauge's layout, and the bar's
  position when the camera is held vertically moves inward, as the PEN-F places it
  (`experiments/2026-11-19-gauge-info/NOTES.md`).
- The other E-PL6 additions (small AF target, ISO LOW), ported as interval shooting was.
- A simple on-camera editor made from existing menu lists.

**High effort: port or write**

- Focus peaking, from the E-P5: done 2026-11-14 (`experiments/2026-11-14-focus-peaking/NOTES.md`).
- Colour grain, halation.
- A custom editor screen.
- Live Composite.

Not in the stock firmware (no text, no code): focus peaking, Color Creator, keystone, focus
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

**What this means for the E-PM2 (TruePic VI).** TruePic VI has a 12-region hue, saturation and lightness stage
for stills. Table A is at 0x7E76C3C8 and table B at 0x7E76CF9C: 12 records of 28 bytes each, with an enable mask
at +3024 (builder 0x7E56E186). The stage runs in pipe A only: stills and RAW Data Edit. Live view and standard
movie use pipe B, which has no 12-region stage. Every film code falls back to Natural's table A. EPM2Mod does not
write this table. Evidence: [caduceus review 05 §4](../../experiments/2026-11-11-caduceus-review/05-imaging-pipeline-and-limits.md#4-the-12-region-stage).
A 12-colour editor for stills is possible in principle. It is not built. It would not show in live view or
movies.

**What is possible here:**

- A six-colour editor: hue and saturation for red, yellow, green, cyan, blue and magenta, written into the
  six-axis stage. It is coarser than a colour wheel (60 degrees per axis, not 30), and green, cyan and magenta are
  only approximate in our model of the stage (section 5 of `experiments/2026-11-14-feasibility/firmware.md`).
- A Color Creator-like control (one hue turn and one saturation for the whole picture) through the 3x3 colour
  matrix, which every film simulation already sets.
- Lightness per colour is not possible in live view or movies.
- In-camera edits on the stages we have, and look import fitted to those stages: requirements and limits in
  `experiments/2026-11-18-look-editor/NOTES.md`.

## Unknowns and their probes

| Unknown | Probe |
|---|---|
| Does code run from the statically checked free areas, and from RAM? | A small routine there that writes a marker to a card file |
| ~~Which task and moment are safe for file reads?~~ | **Answered 2026-11-17 (camera):** the dormant task USRTEST_A, started from the GUI state hook at the first menu or playback screen, reads a 20 KB file (`data/builds/card-looks.json`) |
| ~~Does the image engine accept tables at a RAM address?~~ | **Answered 2026-11-17 (camera):** tables written in RAM at run time take effect in the next photo and in live view, after the boot init's cache refresh (`experiments/2026-11-17-card-looks/design.md` section 9.2) |
| Can the load range be made longer to reach the unloaded 1.59 MB? | The Caduceus method: move the end word in steps, with a pattern and a checksum reported to a card file |
| Does the updater write the blank tails of blocks 1 to 3? | Write a marker there, read it back with 0x7E6756B5 |
| Does this body recover from a boot loop by card update? | Owner's decision |
| Can the E-PM2 have zero-second anti-shock (electronic first curtain)? | Needs a sensor probe (`experiments/2026-11-17-anti-shock/NOTES.md`). Deferred by the owner |

## Where code may go

The firmware loads in steps. The kernel and segment 1 are in RAM first. Segments 2 and 3 are copied
later, by the task Usr1, and on the update path they are not copied at all.

**A hook in the kernel or in segment 1 must jump only to code in the kernel or in segment 1**, unless
you have proof that the hooked function runs only after Usr1. The build `peaking-direct-2` broke this
rule: a hook in a segment-1 function that the boot task calls jumped into segment 2. The emulator
showed a crash at start-up before anyone flashed it. On the camera that is a boot loop, and it could
also break the update path, which is the only way back.

Check every build that adds a hook with the boot test of the emulator before a flash:
`emulator/boot-test data/builds/NAME.json` and `emulator/update-path-test data/builds/NAME.json`.

## The emulator

om-emu boots the E-PM2 firmware, stock or patched, from its reset vector on both cores. om-emu is
the git submodule `emulator/om-emu`: our fork ([github.com/cfu288/om-emu](https://github.com/cfu288/om-emu),
branch `e101`, MIT licence) of upstream om-emu, with the E-PM2's boot lab added in upstream's layout
(`emu/src/boot/`, `emu/bin/boot.mjs`). Set up once with `emulator/setup.sh`. How it works, the
stand-ins and the limits are in
[emulator/om-emu/docs/e101-boot-spec.md](../../emulator/om-emu/docs/e101-boot-spec.md); our checks
and scripts in [emulator/boot/README.md](../../emulator/boot/README.md). Upstream lists this camera
generation as "no work planned".

IMAGE is `stock`, `data/builds/NAME.json` or a `.BIN` file. No firmware is in the repository.

| Check | Command (from the repository root) | What it proves |
|---|---|---|
| Boot test | `emulator/boot-test IMAGE` | The image starts like stock: loader copies, both kernels, all tasks, the application. Exit status 0 = pass. It caught a build that would have crashed at every start |
| Update path | `emulator/update-path-test IMAGE` | With OK held and an update file on the card, the image finds the file as stock does |
| Menu screenshots | `emulator/emu-run IMAGE play.mjs OUTDIR STEP...` | The firmware's own menus, drawn by its own code, in English, as PNG files |
| Screenshot comparison | `emulator/boot/shotdiff.sh IMAGE_A IMAGE_B OUTDIR STEP...` | Which screens a patch changes |
| Menu crawl | `emulator/boot/crawl-all.sh CONFIG IMAGE...`, then `crawldiff.py` or `crawlcmp.py` | Every menu screen of two images, compared |
| Card | `E101_CARD=FOLDER emulator/emu-run IMAGE play.mjs ...` | A FAT card from a host folder mounts; the stock file routines work |

In this repository, `emulator/` has the scenario tests (whole call chains with real initial memory)
and `emulator/hookcheck.py` (the load-order check).

Trust it for: start-up, menus, lists, labels, the INFO screens, settings, card mount. Do not trust it
for: live view, the picture, capture, movies, timing, anything the mechanism or the sensor does. A
pass is evidence, not proof.

**Use it before every flash that changes a hook or a menu.** It also gives exact menu paths and
screen texts for the test instructions.

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
7. Tell users only what is measured. A feature's text matches its evidence: the stage, the range, the measured
   error. No "any LUT", "exact" or "matches the film" without a measurement behind it.
