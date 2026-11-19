# Build label on the Firmware screen

Date: 2026-11-19. Goal: each release shows its name on the camera, for example "EPM2Mod 2026.11.19", made by
`epm2mod make` from the build description. The version number stays 1.6.

Labels: **V** = verified (code, bytes or emulator), **I** = inferred, **U** = unknown.

Scripts: `scripts/fwplay.mjs` (play steps, plus `HDR=1`, `wstr:`, `hex:`, `wset:`), `gen/build-label/mkspec.py`
(writes `patches/build-label-proto.json`). Screenshots: `results/`.

## 1. The Firmware screen

Path on the camera: MENU → wrench tab (**Setup Menu**) → **Firmware** → OK. The screen shows the title
"Firmware", the line "Body : 1.6", and, when the device is there, "Lens", "Flash" and "Acc" lines. Back with OK.

| Fact | Where | Label |
|---|---|---|
| Page 43, page class 0x7EDFD804; slot 0x7EDFD8E6 writes data-model block 76 (14 B): u16 title id 134 "Firmware", four u16 versions, four "present" bytes | `fwmap fn 0x7EDFD8E6` | V |
| The versions come from `IOlyApiMaintenance` vt+16 (`getSystemVersion`, proxy 0x7E99E80B → 0x7E96F37F → 0x7E9E6E3A) with kind 1 Body, 6 Lens, 10 Flash, 8 Acc | disassembly, jump table 0x7EC1B518 | V |
| Kind 1 = low 16 bits of word +104 of the system-info record 0x7E68CD1D = prm tag 0xC082 (CPRAM, ROM default 0) | disassembly; `07-settings.tsv` | V |
| At every start the boot task stores the word at 0x7E421010 into prm 0xC082 (0x7E504B7D `mov (0x7e421010),a1` → prm set 0x7E457CED) | disassembly | V |
| 0x7E421010 = block 0's container header + 16, the field "internal build" = 0x1600 (the header sits just before the payload at 0x7E421020) | `docs/firmware-format.md`; the emulator shows 1.6 when that header is put there | I (strong): the camera's first-stage loader is not in the update file and not modelled |
| The emulator does not place that header: its screen shows "Body : 0.0". With `HDR=1` (the 32 header bytes at 0x7E421000) it shows "Body : 1.6" | `results/lss-firmware-emulator-0.0.png`, `results/lss-firmware.png` | V emulator |
| Panel 99 (type 0x6047, code 0x7ED788C0–0x7ED78E4B, object 936 B) draws it. Per line: label by text id (u16 table 0x7EF93DC8: 1642 Body, 336 Lens, 337 Flash, 1645 Acc), the colon L":" 0x7EF93DD0, and the value: `swprintf(obj+928, L"%X.%X" 0x7EF93DD4, v>>12 & 15, v>>8 & 15)` | 0x7ED78B23, 0x7ED37429 | V |
| The value buffer obj+928 is the object's last field: 8 bytes, 4 UTF-16 characters, exactly "1.6" and its end mark | `mov 936,d0` at 0x7ED1936E before `call 0x7ED788C0` | V |
| The title is set by id (0x7ED78E0D → 0x7EDC181B). Id 134 is the only "Firmware" text, so the Setup Menu row uses it too | English table of block 1 | I |

**Who else reads the version** (all through prm 0xC082, the only direct reader of 0x7E421010 is the boot task):

| Reader | What it does | Label |
|---|---|---|
| Firmware screen (above) | "%X.%X" of the high byte | V |
| Exif writer 0x7E708F24 | Software tag: copies "Version x.x" into a 32-byte space-padded field, then puts the 1st and 2nd hex digits of 0xC082 at +8 and +10: "Version 1.6" | V |
| 0x7E7090xx (same writer, 0x7E70912C) | stores the u16 0x1600 in the record at +2712 (a MakerNote number) | V (field name U) |
| Debug shells: System Info 0x7E99CAF9, `sdk api` 0x7E9B801E | print it | V |
| PTP/USB device info, the card updater's own check | no constant load of 0xC082 and no call of 0x7E68CD1D or getSystemVersion found outside the above (static scan of block 0 incl. overlay B) | U: not traced through computed pointers |
| Look loader (card-looks-5) | does not read it, see section 2 | V |

None of these change with the label: the label work does not touch the header field or prm 0xC082.

## 2. The look loader and 0x0160

`patches/card-looks-5.json` at 0x7EBF2B9D: `fc c8 01 01 60 01` = `cmp 0x01600101,d0` on the file's word +16 (u16 model
0x0101, u16 firmware 0x0160). The 0x0160 is a constant in our own loader code
(`experiments/2026-11-17-card-looks/scripts/mkspec_looks.py`, "E-PM2, firmware 1.6"); it is not compared with the
camera's version. **V.** A label does not affect look files; a changed version number would not either, unless the
loader constant were changed with it.

## 3. The smallest way to show the label

Options, smallest first:

1. **Value text of the Body line (chosen, no code).** Four byte edits, `patches/build-label-proto.json`:
   - 0x7ED1936E: `mov 936,d0` → `mov 1024,d0`. The panel object grows; only its last field, the value buffer at
     +928, gets larger (4 → 48 UTF-16 characters). Without it the longer text overruns the heap object.
   - 0x7ED78BD6: the Body line's format pointer 0x7EF93DD4 → 0x7EBB2FEC. Lens, Flash and Acc keep L"%X.%X".
   - 0x7EF938A4: both copies of the Body value's box (640-wide coordinates, screen x = x + 40) from
     (369, 170, 100, 32) to (331, 170, 341, 32). The box clips and centres its text: with the stock box the label
     shows as "2Mod 2(" (`results/proto-v1-unwidened-clipped.png`).
   - 0x7EBB2FEC–0x7EBB304C (96 B): L"%X.%X  EPM2Mod 2026.11.19", in unreferenced Bluetooth debug strings of segment
     2 (`docs/space-candidates.tsv`, reclaim-space row 2; `lss-menu` uses 0x7EBB1F4C–0x7EBB2AC4).
   The GUI runs only after Usr1 has loaded segments 2 and 3, and no hook is added (hookcheck: 0 transfers).
   Language-independent: the value text is a pointer, not a text id.
2. **Title.** The title is a text id (record +0 = 134, set at 0x7EDFD8FA; drawn by id 0x7ED78E0D → 0x7EDC181B). A
   label there needs a spare id with a new text in each of the 34 languages (block 1), or a 20-byte code change in a
   19-byte function. More work, no gain.
3. **A line of its own (Acc or Flash).** Needs a code edit to force the line on, and hides that device's version.

Widget table found on the way (V): panel 99's boxes at 0x7EF93804, 14 widgets × 2 copies × {x, y, w, h}: 0 guide
bar, 1 title (20, 11, 600, 32), 2–5 labels (191, y), 6–9 colons (311, y, 18), 10–13 values (369, y, 100);
y = 170, 206, 242, 278. Widget descriptors (92 bytes each) from 0x7EF93914 (widget 1): {u16 0x8010, u16 widget id,
box pointer, 9, pointer, 2, text id, ...}; the field at +36 is the alignment: 0x100 left (labels), 0x101 centred
(title, colons, values). Section 6 uses it.

This section describes the first version (camera-tested 2026-11-19, "Works!"). Section 6 replaces the box edit.

**Exif Software tag (report only, not built).** The writer copies "Version x.x" (0x7E8517D9, 12 bytes, the next
string follows) into a 32-byte field. A label fits: "Version 1.6 EPM2Mod 2026.11.19" is 30 characters of 31. It
needs a pointer change at 0x7E708FC6 (`mov 0x7E8517D9,a1`) and a new text; the two digits are still written at +8 and
+10, so the text must keep "Version 1.6" first. Cheap (2 edits), but every photo then carries it: ExifTool and
Lightroom show Software as text and do not parse it; Olympus software (OI.Workspace, Olympus Viewer) may read it,
**U**. Not recommended until someone checks OI.Workspace with such a file; it also makes photos identify the mod.

## 4. Prototype

`gen/build-label/mkspec.py [LABEL]` writes `patches/build-label-proto.json`. `builds/build-label-proto.json` = the 16
specs of `builds/lss.json` + the proto.

| Check | Result | Label |
|---|---|---|
| `uv run epm2mod make builds/build-label-proto.json` | free-space check PASS (0 FAIL); sha256 `5c284fd8030fee224187f09169faa150c1060f342119f704049b1334e940e506` | V |
| `emulator/boot-test builds/build-label-proto.json` | exit 0 | V emulator |
| `emulator/update-path-test builds/build-label-proto.json` | exit 0 | V emulator |
| `emulator/hookcheck.py patches/build-label-proto.json` | exit 0, 0 transfers. The whole build list gives the same 7 FAIL lines as the pinned `lss` (all in `stock-films-structure.json`) | V |
| Firmware screen, lss (`HDR=1`) | "Body : 1.6" (`results/lss-firmware.png`); without `HDR=1` "Body : 0.0" (`results/lss-firmware-emulator-0.0.png`) | V emulator |
| Firmware screen, proto | "Body : 1.6  EPM2Mod 2026.11.19", text x 387–694 in the box 371–712 (`results/proto-firmware.png`) | V emulator |
| Longer dates (text written in RAM with `wset:`) | 2026.12.31: x 385–697 (`results/proto-firmware-2026.12.31.png`); 2028.08.08 (widest digits): x 377–705 (`results/proto-firmware-2028.08.08.png`) | V emulator |
| Setup Menu and the screen after Back | the same PNG bytes as lss (`results/proto-setup-menu.png`) | V emulator |

Command for the screenshots (from the repository root; STATE = a copy of `build/emu/state/lss-p.json`):

```
HDR=1 E101_RTC=2026-11-19T12:00:00 E101_STATE=STATE emulator/emu-run builds/build-label-proto.json \
  $PWD/experiments/2026-11-19-build-label/scripts/fwplay.mjs /tmp/scratch/shots w:500 key:MENU key:RIGHT key:OK \
  key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:RIGHT key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:OK w:500 \
  shot:firmware
```

Not checked: a lens attached (the emulator has none). The Lens value stays in its stock box, centred at screen x 459,
so its "1.x" no longer lines up under the Body "1.6" (cosmetic, I). Nothing on a camera yet.

## 5. Determinism plan (not built)

The label must be a function of the build description only: the release zip makes the pinned build again on the
user's computer and compares the sha256 with `pinned-build.json`'s description. So the label is fixed when the
candidate is made, before the flash, and the camera test covers it.

- **Where the date comes from:** a new field `"label": "2026.11.19"` in `builds/NAME.json`, written by hand (or by a
  future `epm2mod new`) when the candidate is made. Not the clock, not the pin date (that comes after the flash and
  would change the sha256), not the CI tag. The release tag should then use the same date (CI may check
  `pinned_description().label == tag date`).
- **Bytes:** a committed spec `patches/build-label.json` holds the three fixed edits (object size, format pointer,
  box) and reserves the 96-byte text area with a placeholder, so `tools/freespace.py check` sees the area.
  `src/epm2mod/builds.py`: `BuildDescription.label: str | None`, added to `_KEYS`, `description_from_json`,
  `to_json`; checked with `^[0-9]{4}\.[0-9]{2}\.[0-9]{2}$` (and a real date). New `src/epm2mod/label.py`:
  `label_op(label) -> BytesOp` (UTF-16-LE of "%X.%X  EPM2Mod " + label, padded with zeros to 96 bytes, block 0
  offset 0x791FCC, `expect` = the placeholder). `src/epm2mod/pipeline.py`: `load_specs` (or `build_image`) appends
  that op when `description.label` is set and the build lists `patches/build-label.json`; `apply_specs` stays as it
  is. UTF-16 encoding of ASCII is the same on every platform; no locale, no time.
- **Tests (`tests/test_package.py`):** the op's bytes for "2026.11.19" equal a literal hex string; a label that is
  not a date, or too long, is refused; a description with a label and without `patches/build-label.json` is
  refused; two runs give the same sha256; changing only the label changes the sha256 (so `pin` refuses a changed
  label, as it does for a changed spec); the stock-firmware test group makes the labelled build and checks its
  recorded sha256.

## 6. The four values start at one x (2026-11-19, after the camera test)

On the camera, with the 17 mm lens, the Lens "1.1" stayed centred in its stock box while the Body text started
further left (`results/before-align-four-lines.png`, emulator with faked Lens, Flash and Acc versions: Body at x 387,
Lens 446, Flash 440, Acc 443).

**Method (data only, `patches/build-label.json`, from `gen/build-label/mkspec.py`):** the box edit now covers all four
value widgets 10–13 (both copies, 0x7EF938A4–0x7EF938E3): (369, y, 100, 32) → (337, y, 335, 32), screen x 377–712;
and the four value descriptors' alignment field (0x7EF93C74, 0x7EF93CD0, 0x7EF93D2C, 0x7EF93D88) goes from 0x101
(centred) to 0x100 (left, the labels' value). The other edits and the placeholder are unchanged.

**Emulator check:** `FAKEVER=6:1100,10:2000,8:1000` in `scripts/fwplay.mjs` makes the page's Lens, Flash and Acc
version reads succeed (hooks after each read at 0x7EDFD930, 0x7EDFD94D, 0x7EDFD96A: d0 = 0 and the u16 in the page's
record). First lit pixel of each value text:

| Screenshot | Body | Lens | Flash | Acc |
|---|---|---|---|---|
| `results/aligned-four-lines-2026.11.19.png` | 378 (ends 685) | 378 | 378 | 378 |
| `results/aligned-four-lines-2028.08.08.png` | 378 (ends 706, box ends 712) | 378 | 378 | 378 |
| `results/aligned-body-lens-2026.11.19.png` | 378 | 378 | – | – |
| `results/aligned-body-lens-2028.08.08.png` | 378 (ends 706) | 378 | – | – |

The 2028.08.08 text is written in RAM with `wset:`, over the made build's text.
`uv run epm2mod make builds/epm2mod-2026.11.19.json`: free-space check PASS, boot-test PASS, update-path-test PASS,
sha256 `6441130e9cc6cd5f06dc70e35950e05b0401f9a3f606694cf2c806a0bc209f62`. hookcheck of the spec: 0 transfers.
`uv run python -m unittest tests.test_label`: OK.

Change from stock: the values now start at screen x 378, right after the colon (x 357–362). Stock starts them about
x 440 (centred). Not checked: the real lens, flash and accessory reads (faked here); the camera.
