# Full boot of the E-PM2 firmware in om-emu

These tools boot the E-PM2 firmware (v1.6, stock or patched) from its reset vector in
[om-emu](https://github.com/flatpanda/om-emu), on both MN103 cores. The firmware's own kernel, tasks,
GUI and menu code run. The tools press keys, write screenshots, and compare images.

Labels: **V** = ran here or read in the firmware bytes; **I** = inferred; **U** = unknown.
F = a fake answer; M = a model of what the hardware does.

## Set up

```sh
git submodule update --init third_party/om-emu
tools/emu/setup.sh                      # makes build/om-emu: the pinned om-emu plus our patches
```

- **om-emu** is the submodule `third_party/om-emu`, pinned to commit `0819080133f6` (MIT licence). It is
  never edited. `setup.sh` exports it to `build/om-emu/` and applies `tools/emu/om-emu-patches/*.patch`.
  Run `setup.sh` again after a patch or the pin changes; it does nothing when the tree is up to date.
- **Node 26 or newer.** The tools take `node` from PATH when it is new enough, else the newest Node that nvm has
  (`tools/setup.sh`; the version is in `.nvmrc`).
  Override: `OM_EMU_NODE`.
- **Firmware** is never in the repository. The tools unpack an image into `build/emu/NAME-SHA8/` when
  they need it. An IMAGE argument is `stock`, `builds/NAME.json` (its file is `build/NAME.BIN`), a `.BIN`
  file, or a folder made by `tools/oetool.py unpack`.
- The scripts `*.sh` need zsh. `sheets.py` needs Pillow.

## The two checks

```sh
tools/emu/boot-test builds/NAME.json          # or a .BIN file
tools/emu/update-path-test builds/NAME.json
```

Exit status of both: **0** pass, **1** fail (one line says why, then the lines that differ), **2** wrong
arguments, **3** the emulator is not set up or the image file is missing. `--out DIR` keeps the raw
reports. `--ref IMAGE` changes the reference (default `stock`).

**`boot-test`** boots the image and the stock firmware for 2000 ms of lab time (`stage2-boot.mjs`).
The image fails when it does not reach the end of start-up, or when its report differs from stock's.
The rule (`boot-test --rule`, code in `tools/emu/bootcheck.py`): every line must be equal after these
parts are taken out of both reports:

1. the wall time;
2. the instruction counts of the two CPUs;
3. the hit counts of the entries named `idle`;
4. lab time stamps in the four log lines, which may move by 0.2 ms or less.

All other content must be equal: console text, boot marks, task counts, events, API calls, firmware
error entries, stand-in hit counts, transfer counts. A patch that changes the start-up on purpose fails
this rule. Read the printed lines and decide by hand. Do not widen the rule.

**`update-path-test`** starts the image and the stock firmware with OK held and a card that has
`DCOLYMP/E1019999.BIN` (a copy of the stock file). The image passes when it does what stock does: the
update flag is cleared, the update tasks start, the file is found, the console is equal up to the
body-controller step, there is no fault, and segment 2 is not loaded. The emulator cannot go past the
body-controller step.

To call a check from another program, run it as a subprocess and read the exit status:

```python
subprocess.run([sys.executable, "tools/emu/boot-test", "build/NAME.BIN"], cwd=repo_root).returncode
```

## Tools

Run a tool on an image with `tools/emu/emu-run IMAGE TOOL ARGS...`. It unpacks the image and sets
`BLOCKS`, `OM_EMU_DIR` and `EPM2_REPO`.

| File | What it does |
|---|---|
| `stage2-boot.mjs [LABMS]` | Boot report: console, task counts, events, error log, stand-in hits. Exit 0 = both kernels run, Usr0 to Usr4 done, no fault |
| `update-boot.mjs [LABMS]` | Power-on with OK held: the update path. `E101_CARD` gives the card. `WATCH=hex:name,...` adds pcs to report |
| `play.mjs OUTDIR STEP...` | Scripted keys and screenshots (steps below) |
| `shot.mjs LABMS OUT.png` | One screenshot after LABMS |
| `../mkstate IMAGE OUT.json [MODE]` | Makes a settings state through the menus: English, Custom Menu and Accessory Port Menu shown, mode iauto, p, art, scn or movie |
| `shotdiff.sh A B OUTDIR STEP...` | The same key script on two images; lists the screenshots that differ. Exit 0 = none |
| `crawl.mjs OUTDIR NAME STEP...` | Menu crawler: one PNG per cursor position, named by its path. It never presses OK |
| `crawl-all.sh CONFIG IMAGE...` | All crawl units of one configuration, for example `p-nocard-shallow` |
| `crawldiff.py A B OUT`, `crawlcmp.py A B OUT` | Compare two crawls by name; `crawlcmp.py` also by content, for an image with one more Custom Menu row |
| `lang-all.sh IMAGE [LANG...]`, `sheets.py RUN OUT` | The Picture Mode and ART lists in all 34 menu languages, and contact sheets of them |
| `logplay.mjs OUTDIR STEP...` | `play.mjs` for the debug-log builds: ring headers, bursts, the card's files copied back to the host folder |
| `canexec.mjs STEP...`, `rtcpeek.mjs` | Why a menu row is grey (the row-enable checks); the date record of the clock driver |
| `sheet.py OUT.png COLS SCALE IN.png...` | Contact sheet, Python standard library only |

`play.mjs` steps: `w:MS` (run lab time), `key:NAME[:MS]`, `shot:NAME`, `pin:HEX:LEVEL`, `adc:CH:VALUE`,
`port:HEX`, `tilt:X:Y:Z` (accelerometer stand-in, 16384 = 1 g) and `tilt:off`. The first step runs
after 1500 ms (`BOOTMS`). In zsh, pass the steps as an array.

Environment of the drivers:

| Variable | Meaning |
|---|---|
| `E101_STATE=file` | Settings state, loaded at the start and saved at the end of `play.mjs` |
| `E101_CARD=folder` | An SD card with a FAT16 image made from the folder |
| `E101_RTC=2026-11-14T12:00:00` | Sets the clock (below). Without it the clock is "not set" |
| `E101_FAST=1` | Lets the quick start run (default: declined, as with OK held) |
| `E101_TAKEFAKE`, `E101_APIFAKE`, `E101_CAM`, `E101_IMG` | Switch single stand-ins off or add faked commands |
| `GUILOG=1` or `2`, `FLASHLOG`, `CARDLOG=N` | More output from `play.mjs` |
| `EMU_OUT`, `EMU_STATE` | Output and state folders of the `.sh` scripts (default `build/emu/out`, `build/emu/state`) |

Example, the Peaking list of the pinned build:

```sh
tools/emu/mkstate builds/peaking-colours.json build/emu/state/peaking-colours-p.json p
cp build/emu/state/peaking-colours-p.json /tmp/scratch/s.json
E101_STATE=/tmp/scratch/s.json tools/emu/emu-run builds/peaking-colours.json play.mjs /tmp/scratch/shots \
  w:500 key:MENU key:RIGHT key:OK key:DOWN key:DOWN key:DOWN key:RIGHT key:RIGHT \
  key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:RIGHT shot:peaking-list
```

Screenshots of the camera's screens go to `docs/images/ui/` only, and only the ones a guide shows.

## How the port works

om-emu's own bodies run in a "lab" that is written for the OM-1 and starts from a made-up state after
boot. Upstream lists this camera generation as tier D, "no work planned". This port does not use the
lab. It uses om-emu's CPU, memory, interrupt controller, timer and second-core support, and lets the
firmware boot itself.

- `../e101/machine.mjs` builds the machine: 512 MiB of RAM, the flash view (the four container blocks at
  their flash addresses), plain storage for every device register that has no model, pc hooks, and the
  run loop. Only 0x7E421020 to 0x7E430000 is in memory at reset. The firmware's own nine loader copies
  bring in the rest, so a patch in a range that is never loaded is absent here, as on the camera.
- `../e101/boot.mjs` has the function-level stand-ins. `devices.mjs` has the register-level models.
  `osd.mjs` models the OSD engine. `screen.mjs` composes the three OSD planes into a PNG of 720 × 480.
  `keys.mjs` has the keys. `sdcard.mjs` is the card. `kernel.mjs` and `sym.mjs` read task and
  function names from `build/map/` when that exists.
- Lab time: 4 ns per CPU0 instruction (a choice, not the chip's speed). CPU1 runs 2000 instructions
  after every 2000 of CPU0. A run with the same inputs gives the same report and the same PNG bytes.

What the E-PM2 needed from om-emu is in the two patches:

| Patch | Content |
|---|---|
| `0001-e101-function-harness.patch` | The model entry E101 (image base 0x7E421020, board facts on the E118 family, 2 INTC banks, 125 IRQs). The lab refuses to start on it. Used by `tools/emu/omemu.py` |
| `0002-e101-full-boot.patch` | A vector page per core (CPU1's vectors are at 0x7E44xxxx). The kick between cores: bank b's word +0x310 raises IRQ 124 on the other core. Storage for unknown INTC offsets. `S.relax`: a read of undefined flags and a divide by 0 do not fault, because the firmware does both on its normal path (0x7E5018FC, 0x7E581713) |

## Stand-ins

Function-level, in `../e101/boot.mjs`:

| Name | Address | What it does | Kind |
|---|---|---|---|
| S-CONSOLE | 0x7E44B051 | Debug serial output, kept as the console text | M |
| S-OSDFILL | 0x7E4213F7, 0x7E426B5D | The reset's memory clear through the OSD engine | M |
| S-FLASHREAD0 | 0x7E4217E6 | Flash read from the container blocks; other areas read 0xFF | M for the update file's blocks, F for adjustment data and pictures |
| S-FLASHWRITE, S-FLASHERASE | 0x7E451B69, 0x7E4519C5 | The settings store's writes, kept in memory and in the state file | M at the driver seam |
| S-DMA | 0x7E425FA8, 0x7E426045, 0x7E42627B | CPU DMA: the copy is done in the start call | M |
| idle, CPU1 poll | 0x7E436825, 0x7E43683D, 0x7E44966C, 0x7E44EB5B | Lab time jumps to the next event | M |
| S-IIC, S-SIO, S-SIORAW | 0x7E463275, 0x7E469CDF, 0x7E468324 | Every I2C and SIO device reads 0; the hot shoe never answers ("no flash") | F devices |
| S-BC | 0x7E53E792 | The H8 body controller answers every transaction with 0 | F |
| S-BATT, S-PWM | 0x7E53963A, 0x7E466435 | Battery level 100; backlight requests return 0 | F |
| S-GIOIN | 0x7E46144E | Input pins: buttons released, HDMI and video not connected | M |
| S-NOFAST | pin 0x35 at 0x7E5026FE | The quick start is declined | F choice |
| S-CAM | 0x7E628303 | The mechanism sequencer's requests are answered "done" | F |
| S-TAKEAPI | 0x7E67E502 | Live view start (command 0x19) and the PLAY commands 80:5 and 80:1 are answered "done" | F |
| S-IMG | 0x7E5455BF | The IMG engine's job wait is answered "finished" | F |
| S-ACC | 0x7E4585DC, 0x7E4584A4 | Accelerometer samples, only with `tilt:` | F |
| S-SDCMD | 0x7E5CEABB, 0x7E5CE3E1 | SD commands go to the card model, or "no response" without a card | M |
| bank restore | 0x7E4580BD | Writes the saved RAM images of the settings banks back at the next start | F, replaces the power-off save |

Register-level, in `../e101/devices.mjs`: the system controller 0x98E00000 (ports, wake factor, clock),
the ADC 0x98C00000, the SD host bit, the GIO block 0x9A100000 (deferred calls, 15 one-shot timers, the
bit-search unit), the display controller 0x9A900000 (frame interrupt every 16.683 ms), and the OSD
engine 0x9AA00000. Every other register in 0x80000000 to 0x9FFFFFFF is plain storage: it reads what was
written.

## Keys

| Name | Source | Evidence |
|---|---|---|
| MENU, INFO, MAGNIFY, UP, DOWN, LEFT, RIGHT | The key ladder on ADC input 3, with the key-on handler 0x7E50B50D posted | V by the GUI's own log names |
| OK, PLAY, ERASE | GIO pins 0x35, 0x28, 0x41 | V; ERASE is I |
| CUSTOM1, CUSTOM2 | GIO pins 0x32, 0x42 | Fn and the movie button; which is which is U |
| POWER | System-controller port 0 | Starts the power-off sequence |
| S1, S2 | GIO pins 0x72, 0x74 | Named, not tried |

MENU opens the top menu at the current mode. Its order is ART, iAUTO, SCN, movie, P/A/S/M, SETUP. In
the menus MENU goes back one level.

## Settings and card and clock

- **Settings.** The store starts empty: Japanese, Custom Menu hidden, iAUTO. `tools/emu/mkstate` sets
  English through the menu and saves the state. A state belongs to the image that made it.
- **Card.** `E101_CARD=folder` gives an SD v2 card of 64 MiB with MBR and FAT16, made from the folder
  (8.3 names). The firmware's own FAT code mounts it, lists it, formats it and writes files. Without it
  the firmware concludes "no card".
- **Clock, `E101_RTC`.** The RTC is in the system controller: +0x98 is a seconds counter in Unix time,
  +0x9C has the milliseconds, and +0x00 bits 2 to 7 hold the marker 42 for "clock set" (V: the driver's
  own conversion 0x7E508A6F). `E101_RTC=2026-11-14T12:00:00` (or seconds) sets the marker and the
  counter at power-on; the counter then follows lab time. Without it the clock is "not set": the row
  Time Lapse Settings is grey and a start with a card shows the date prompt. The clock is not in the
  state file.

## What to trust

Trust it for: start-up (loader copies, static constructors, both kernels, all tasks, the application),
the update path up to the body-controller step, the shooting information screens, the whole menu
system (rows, labels, lists, help texts, grey rows), saved settings, card mount, format and file
writes. A patch that breaks one of these shows as a fault, a different report, a different PNG or a
firmware error entry.

Do not trust it for: live view, the picture, exposure, AF, capture, movies, the mechanism, timing,
caches, real sensor values. A pass is evidence, not proof of safety on the camera.

## Known limits

- **No live view.** The live view start is faked, so no frame arrives. The video plane is flat grey.
- **Power-off does not finish.** After POWER the application waits for an event that never comes (U
  which). The firmware's own save of the settings banks does not run; the bank restore above replaces it.
- **Grey menu backgrounds.** The background pictures are in a flash area that is not in the update
  file. The top menu shows only its back button.
- **The start-up errors differ from the camera's.** The camera's log has eight records at every start,
  0x19000C02 and 0x19000C03 from the DMA routine 0x7E426045, for transfers with cached addresses
  (`experiments/2026-11-15-log/evaluation-1.md`, section 2.2). S-DMA stands in for that routine, so the
  emulator has none of them. The emulator has two entries 0x2A001001 at about 36 ms instead.
- The power-on factor and the wake byte read 0. Adjustment data is absent (reads 0xFF).
- S1 and S2, a real JPEG in playback, SDHC and FAT32 are not tried. Scaled OSD bitmaps are drawn unscaled.
- The viewfinder screens and the super control panel are not reached.
- The divide by 0 gives −1 with V set. The chip does not trap there; the value it gives is U.

## History

The port was made on 2026-11-14 on om-emu commit 96bf756, outside this repository, because om-emu had
no licence then. It came into the repository on 2026-11-15 on commit 0819080, after upstream added the
MIT licence (commit 18a8162). The checks of that move are in
`experiments/2026-11-15-emulator-in-repo/`. Findings from the port are in
`experiments/2026-11-14-emulator-audit/NOTES.md`.
