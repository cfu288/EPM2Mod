# E-PM2 firmware feature map (2026-11-08)

A static study of the Olympus PEN E-PM2 main firmware, v1.6, to learn what it contains and how it is organised. Mapping only: nothing was patched or flashed.

**The compiled map is [`docs/firmware-map.md`](../../docs/firmware-map.md).** Read it first. This folder holds the detail behind it.

## What we learned, in short

- **Structure.**
  - Two CPU cores run the uITRON OS: 147 tasks on CPU0 and 30 on CPU1.
  - On top of the OS sit service tasks (lens, shooting, recording, movie, playback, audio, art filters, USB), then a C camera API of about 640 functions, then a C++ application generated from statecharts (IBM Rhapsody runtime, inferred), then the GUI.
  - The linker kept each source file's code together, and its strings in the same order. That is what made the mapping possible.
- **Firmware blocks.**
  - Block 0 is the code.
  - Block 1 holds 34 languages × 1,970 strings, plus fonts.
  - Block 2 is the Grainy Film noise texture.
  - Block 3 holds 8 frame overlays.
  - The `OM` tail is the image stabiliser's own microcontroller firmware.
- **The updater** checks a maker byte, the model id, a header copy and a 32-bit sum. It has no version or downgrade check. It accepts the **E-PL5** model id for main packages, so only you keep E-PL5 files off the card.
- **Hidden:**
  - debug shells, one of them reachable over USB;
  - a BASIC interpreter that runs card scripts able to call the camera API;
  - a settings debugger for all 1,800 settings;
  - factory self-calibration from card files.
- **Dormant (complete code, no known way in on this body):**
  - interval shooting and time-lapse;
  - four art-filter code modules that the menu does not list (star light, mirror, composite, pastel art), plus a third Pin Hole variant;
  - Bluetooth/PENPAL, gated on a hardware input;
  - 3D photo.
- **Stubbed:** the picture database behind Photo Surfing, Event View and person/GPS search.
- **Movie limit.** It is computed once at record start, from rates in 512-byte sectors per second with 48 kHz PCM audio as the overhead. It is then checked every frame (0x7E6EE006). There is no file splitting.

## Files here

| File | What it is |
|---|---|
| [`NOTES.md`](NOTES.md) | Method, fixed points (task tables, settings getter, …), and the **hand spot checks** of each section's key claims |
| [`sections/01-platform.md`](sections/01-platform.md) | Boot, OS and task tables, debug shells, BASIC, peripherals, flash memory, factory adjustment |
| [`sections/02-lens-power-firmup-take.md`](sections/02-lens-power-firmup-take.md) | Firmware updater (fully traced), lens, battery, stabiliser, shooting control (TAKE_*), strobe, files |
| [`sections/03-camera-core-rec-art.md`](sections/03-camera-core-rec-art.md) | Camera core, camera API, exposure, still pipeline, art filters, face detection |
| [`sections/04-movie.md`](sections/04-movie.md) | Movie modes and bitrates, time limit, effects, `mov` shell, time-lapse |
| [`sections/05-playback-audio-bt.md`](sections/05-playback-audio-bt.md) | Playback engine, edit modes, BGM, audio codec and DSP, Bluetooth/PENPAL |
| [`sections/06-app-components.md`](sections/06-app-components.md) | C++ app layer, shooting and playback components, picture database |
| [`sections/07-gui-menus-settings.md`](sections/07-gui-menus-settings.md) | Settings system, menu tables, language-string format, hidden menus |
| [`sections/07-settings.tsv`](sections/07-settings.tsv) | All 1,800 settings tags: storage class, type, count, default |
| [`sections/08-connectivity-libs-blocks.md`](sections/08-connectivity-libs-blocks.md) | USB/PTP/MTP/PictBridge, HDMI, Eye-Fi/FlashAir, libraries, blocks 2/3, stabiliser MCU |
| [`tasks.tsv`](tasks.tsv) | All 177 tasks (both CPUs): id, name, entry, priority, stack. Made by `fwmap.py tasks` |
| [`modules.tsv`](modules.tsv) | The 152 source files in link order, with their code ranges |
| [`regions.txt`](regions.txt) | Strings and tasks per 256 KiB region. Made from the **first** database, before the task-table and data-page fixes, so its task names are out of date. Use it as a rough guide only |

Related: [`../2026-11-08-disassembly/NOTES.md`](../2026-11-08-disassembly/NOTES.md) (base address check and first reading of the movie time-limit routine) and [`docs/firmware-format.md`](../../docs/firmware-format.md) (container format).

## How to read the sections

- **verified** means the code or bytes were read and show the claim; **inferred** means it comes from strings, names or layout only. Section 01 uses **[V]**/**[I]**.
- Addresses are runtime addresses. Block-0 offset = address − 0x7E421020.
- The sections were written by eight parallel investigators against the first function database. `NOTES.md` records what changed afterwards. All but 3 of the 1,354 function addresses they cite are still function starts, and those 3 are in ranges the sections themselves call data.

## Reproducing and exploring

```bash
scripts/build-binutils-mn10300.sh      # once: GNU objdump for MN10300/AM33
python3 tools/fwmap.py build           # about 40 s; writes build/map/ (not committed)
python3 tools/fwmap.py fn 0x7E6EDE08 --dis
python3 tools/fwmap.py str 'firmup'
python3 tools/fwmap.py tasks
```

Several sections name helper scripts (for example `lang.py`, `menutab3.py`, `ptptab.py`) that the investigators wrote in the session's temporary scratch folder. **They are not in this repo.**

## Open questions

See [`docs/firmware-map.md` §6](../../docs/firmware-map.md#6-main-open-questions) and the end of each section.
