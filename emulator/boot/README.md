# Full boot of the E-PM2 firmware

The emulator is our om-emu fork, the submodule `emulator/om-emu`
([github.com/cfu288/om-emu](https://github.com/cfu288/om-emu), branch `e101`). Its **boot lab** boots the
E-PM2 firmware (v1.6, stock or patched) from its reset vector on both cores; the firmware's own kernel,
tasks, GUI and menu code run. How it works, every stand-in with its evidence, the keys and the limits:
[emulator/om-emu/docs/e101-boot-spec.md](../om-emu/docs/e101-boot-spec.md).

This folder holds only what this repository adds: the two checks, wrappers with the earlier names, and
our scripts.

## Set up

```sh
emulator/setup.sh          # initialises emulator/om-emu at the pinned commit
```

Node 26 or newer (`tools/setup.sh`; override: `OM_EMU_NODE`). No firmware is in the repository: an
IMAGE argument is `stock`, `data/builds/NAME.json` (its file `build/NAME.BIN`) or a `.BIN` file.

## The two checks

```sh
emulator/boot-test data/builds/NAME.json
emulator/update-path-test data/builds/NAME.json
```

Exit status of both: **0** pass, **1** fail (one line says why, then the lines that differ), **2** wrong
arguments, **3** not set up or the image is missing. `--out DIR` keeps the raw reports. `--ref IMAGE`
changes the reference (default `stock`).

**`boot-test`** boots the image and stock for 2000 ms of lab time and compares the two reports line by
line. `boot-test --rule` prints the rule (code: `emulator/bootcheck.py`). A patch that changes the
start-up on purpose fails it: read the printed lines and decide by hand. Do not widen the rule.

**`update-path-test`** starts both with OK held and a card that holds `DCOLYMP/E1019999.BIN`. The image
passes when it finds the file as stock does and does not load segment 2.

## Tools

`emulator/emu-run IMAGE TOOL ARGS...` runs a tool on an image. The first five run the fork's
`emu/bin/boot.mjs` (`forkcli.mjs` turns the variables below into its options).

| File | What it does |
|---|---|
| `stage2-boot.mjs [LABMS]` | Boot report (`boot.mjs report`). Exit 0 = both kernels run, Usr0 to Usr4 done, no fault |
| `update-boot.mjs [LABMS]` | Power-on with OK held (`boot.mjs update`). `WATCH=hex:name,...` adds pcs |
| `play.mjs OUTDIR STEP...` | Keys and screenshots (`boot.mjs play`; steps below) |
| `shot.mjs LABMS OUT.png` | One screenshot after LABMS |
| `crawl.mjs OUTDIR NAME STEP...` | Menu crawler (`boot.mjs crawl`): one PNG per cursor position. It never presses OK |
| `../mkstate IMAGE OUT.json [MODE]` | A settings state through the menus: English, Custom Menu and Accessory Port Menu shown, mode iauto, p, art, scn or movie |
| `shotdiff.sh A B OUTDIR STEP...` | The same key script on two images; lists the screenshots that differ. Exit 0 = none |
| `crawl-all.sh CONFIG IMAGE...` | All crawl units of one configuration, for example `p-nocard-shallow` |
| `crawldiff.py A B OUT`, `crawlcmp.py A B OUT` | Compare two crawls by name; `crawlcmp.py` also by content |
| `lang-all.sh IMAGE [LANG...]`, `sheets.py RUN OUT`, `sheet.py` | The Picture Mode and ART lists in all 34 languages, and contact sheets |
| `logplay.mjs OUTDIR STEP...` | `play.mjs` for the debug-log builds: ring headers, bursts, the card's files copied back |
| `canexec.mjs STEP...`, `rtcpeek.mjs` | Why a menu row is grey; the clock driver's date record |

Steps: `w:MS`, `key:NAME[:MS]`, `shot:NAME`, `pin:HEX:LEVEL`, `adc:CH:VALUE`, `port:HEX`,
`tilt:X:Y:Z`, `tilt:off`. The first step runs after 1500 ms (`BOOTMS`). Keys: MENU, INFO, OK, PLAY,
ERASE, MAGNIFY, UP, DOWN, LEFT, RIGHT, CUSTOM1, CUSTOM2, POWER, S1, S2.

| Variable | Meaning |
|---|---|
| `E101_STATE=file` | Settings state, loaded at the start and saved at the end of `play.mjs` |
| `E101_CARD=folder` | An SD card, a 64 MiB FAT16 image made from the folder (8.3 names) |
| `E101_RTC=2026-11-14T12:00:00` | Sets the clock. Without it the clock is "not set" (date prompt, grey rows) |
| `E101_FAST=1`, `E101_TAKEFAKE`, `E101_APIFAKE`, `E101_CAM`, `E101_IMG`, `E101_TILT` | Single stand-ins on or off (the spec, section 5) |
| `GUILOG=1` or `2`, `FLASHLOG`, `CARDLOG=N` | More output from `play.mjs` |
| `EMU_OUT`, `EMU_STATE` | Output and state folders of the `.sh` scripts (default `build/emu/out`, `build/emu/state`) |

Example, the Peaking list of the pinned build:

```sh
emulator/mkstate data/builds/peaking-colours.json build/emu/state/peaking-colours-p.json p
cp build/emu/state/peaking-colours-p.json /tmp/scratch/s.json
E101_STATE=/tmp/scratch/s.json emulator/emu-run data/builds/peaking-colours.json play.mjs /tmp/scratch/shots \
  w:500 key:MENU key:RIGHT key:OK key:DOWN key:DOWN key:DOWN key:RIGHT key:RIGHT \
  key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:RIGHT shot:peaking-list
```

Screenshots of the camera's screens go to `docs/images/ui/` only, and only the ones a guide shows.

`../e101/` keeps the module names the earlier drivers had (`createBoot`, `press`, `screenshot`, ...) for
the scripts in `experiments/`; they import the fork. New code imports `emulator/om-emu/emu/src/boot/`.

## What to trust

Trust it for: start-up, the update path up to the body-controller step, the INFO screens, the menu
system, saved settings, card mount, format and file writes. Do not trust it for: live view, the
picture, exposure, AF, capture, movies, the mechanism, timing. A pass is evidence, not proof. The open
points are in the spec, section 8.

## History

The port was made on 2026-11-14 outside this repository and came in on 2026-11-15 as two patches and
drivers here (`experiments/2026-11-15-emulator-in-repo/`). On 2026-11-16 it moved into the om-emu fork
as the boot lab, in upstream's layout; the outputs, PNG bytes included, are the same.
