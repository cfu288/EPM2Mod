# ART BKT as a release feature: the film-name fix, the generator, the loop check, the candidate (2026-11-24)

Owner's decisions of 2026-11-24 (`plan.md` section 7): D1 = yes, RAW Data Edit → ART BKT becomes a release feature;
D2 = a, each JPEG records its own film name. Base: the pinned build peaking-mf. Build `data/builds/artbkt.json` =
peaking-mf's specs + `data/specs/raw-edit-art-bkt-3.json`, label 2026.11.24. Not flashed.

Labels: V = verified (firmware bytes, emulator run), I = inferred, U = unknown. Emulator runs use the stand-ins of
`../2026-11-20-raw-edit-art-bkt/NOTES.md` section 8.3 (no image engine: the pictures are empty; the control flow, the
EXIF block and the card writes are the firmware's).

## 1. Film name per JPEG (D2 = a)

| Item | Finding | Label |
|---|---|---|
| Where a RAW edit's ImageDescription comes from | The take record's 32 B at +0x5A8 (the EXIF template's layout: template 0x605BA918, ImageDescription +0x5A8). It holds the RAW's text when play_edit_raw_set_exif_default 0x7E94113F starts (test RAW with the marker text "RAW IMAGE DESCRIPTION" at file offset 0x868, memory search `scripts/findtext.mjs`), and the JPEG carries it | V emulator |
| Which edit runs | The play command at (16,d3): 146 [Current], 147 Custom1, 148 Custom2 (written as 0, 1, 2 to (20,a3); all three run) | V emulator |
| Fix: H3 | 0x7E9411AD (segment 2), `mov (a2),a2; movbu (16479,a2),d0` (6 B) → `jmp FIXDESC; nop`. FIXDESC (44 B, segment 2): for command 146 it copies the template's 32 B from 0xA05BAEC0 (the uncached alias; FILMNAME writes both) over take+0x5A8, then the displaced code. Custom1 and Custom2 keep the RAW's text: they develop with their own Picture Mode, whose name the template does not hold | V code; hookcheck 17 transfers, 0 FAIL |
| The template at each ART BKT frame | PMSET calls FILMNAME after each Picture Mode change (raw-edit-art-bkt), so the template names the frame's entry | V emulator (run log) |
| Size | raw-edit-art-bkt-2 552 B → raw-edit-art-bkt-3 596 B in 0x7EBB2AC4-0x7EBB2FEC (1320 B free run); 6 B hook | V |

Emulator results (`scripts/runs.py`, `emulator/artbkt-test`; look pack ART 1 Portra 400, ART 2 Velvia; P mode, Natural):

| Run | ImageDescription of the JPEGs | Before the fix |
|---|---|---|
| ART BKT, 12 entries On (frames 0-2) | OLYMPUS DIGITAL CAMERA, Portra 400, Velvia | the RAW's text in all |
| ART BKT, Pop Art + Natural row On | OLYMPUS DIGITAL CAMERA, Portra 400 | |
| RAW Data Edit → Current, Picture Mode ART 1 (Portra 400) | Portra 400 | the RAW's text |
| RAW Data Edit → Custom1 | the RAW's text (unchanged) | the RAW's text |
| exiftool on the three ART BKT frames | ArtFilter Off; 0; 0; 0 on all three (Natural, and two film frames): **plan E3 answered, V emulator**. PictureMode Natural on all (as `../2026-11-20-raw-edit-art-bkt/NOTES.md` run C) | |

## 2. The generator and the loop check

- `gen/raw-edit-art-bkt/` (`artbkt.s`, `mkspec.py`) replaces `../2026-11-20-raw-edit-art-bkt/scripts/mkspec_artbkt.py`.
  Without FIXDESC it gives raw-edit-art-bkt-2's ops byte for byte (checked before H3 was added). FILMNAME is the one
  place in the base where new code starts with FILMNAME's first 11 bytes (card-looks-8 has no `_symbols` entry for
  it); every byte the spec changes must be stock in the base. In `gen/run.sh` (last), `mypy --strict`
  (`cli/pyproject.toml`), tests `cli/tests/test_gen_raw_edit_art_bkt.py`.
- `emulator/artbkt-test BUILD.json`, in `tools/checks.py`'s full tier (check `artbkt-loop`) for every build with a
  raw-edit-art-bkt spec: P state, the marked test RAW, a look pack, Load Looks, ART BKT with the 12 entries On, three
  saves, the emulator's save error, the stop. Pass needs no fault, the frame list, 3 JPEGs, the Picture Mode back,
  and with FIXDESC each frame's ImageDescription. On the build that crashed the camera on 2026-11-21 (films-start-texts
  + raw-edit-art-bkt, sha256 `2118fc0a…`, made again for this test and deleted) it FAILS: fault at pc 0x801E after
  frame 0, as on the camera (V).
- The emulator driver is `emulator/boot/artbkt.mjs`, a copy of `../2026-11-20-raw-edit-art-bkt/scripts/artbkt.mjs`
  with the import path changed.

## 3. Emulator runs of the acceptance criteria (`plan.md` section 4)

| # | Run | Result | Label |
|---|---|---|---|
| A1 | ART BKT screen through Shooting Menu 2 → Bracketing → ART BKT → On (no OK) → RIGHT; rows set; MENU | MENU on the ART BKT screen returns to Bracketing with the Off / On panel still open; MENU again closes it; ART BKT reads `--`. The ART BKT screen shows the loaded names (Portra 400, Velvia) | V emulator |
| A2 | Screens of the pinned build and of artbkt, same keys (▶, OK, OK, DOWN × 3, DOWN, MENU, MENU) | Playback, the RAW menu and the screens after MENU equal; only the RAW Data Edit list differs (5 rows: Current, Custom1, Custom2, ART BKT, No) | V emulator |
| A2 | End screen | Reset / No, Reset highlighted. No → playback shows "Picture Error" for the new (empty, stand-in) JPEG; the pinned build shows the same after a stock [Current] edit: an emulator limit | V emulator |
| A3 | n = 0 (every row Off) | List [2]: 1 JPEG (Current), Picture Mode back | V emulator |
| A3 | n = 1 (Watercolor) | List [2, 120]: 2 JPEGs, normal end (Reset / No), Picture Mode back | V emulator |
| A3 | n = 3 (Velvia, Pin Hole, Monotone row) | List [2, 101, 105, 5]; frames 0-2 saved, then the emulator's save error at frame 3: stop, Picture Mode back | V emulator |
| A3 | Pop Art + Natural row On, current Natural | List [2, 100]: Natural once | V emulator |
| A3 | 12 entries (artbkt-test) | List [2, 100 … 109, 119, 120]; frames 0-2 saved, error stop, Picture Mode back | V emulator |
| A5 | EXIF | Section 1 | V emulator |
| A7 | Normal end and error end | Picture Mode back (PRM_SET 0x9481 = the start value) in every run | V emulator |
| A11 | RAW Data Edit list in German, Russian, Chinese (simplified) and one more Cyrillic language | The row reads "ART BKT" in each (stock text 1699) | V emulator |
| — | RAW+JPEG pair (PB130001.ORF + a camera JPEG as PB130001.JPG) | OK in playback opens a menu titled **RAW/JPEG** with RAW Data Edit and JPEG Edit (manual p. 65). ART BKT: frame 0 saved; the preview of frame 1 fails with 0xF0000001; stop, Picture Mode back, no fault. The pinned build fails the same way at its second [Current] edit of a pair: an emulator limit | V emulator; U camera |
| — | An ORF shot in ART mode | Not run: the emulator takes no pictures, and an ORF edited with exiftool (ArtFilter tag) is rewritten, not a camera file | U camera |

Not shown in the emulator (the camera sheet, `test-sheet.md`): the pictures (A4, the Olympus filters ART 10-12), a
full card (A8), power-off during Busy (A7), keys during Busy, the time per JPEG (A12), a run of more than three saves.

## 4. Checks of the candidate

`data/builds/artbkt.json`, sha256 `729e8db67bf303372f32706076c496edd9326b7f54267bfe398a187553463b78`.

| Check | Result |
|---|---|
| `uv run epm2mod make artbkt` (free-space check, boot-test, update-path-test) | PASS, FIRST CODE line (0x7EBB2AC4-0x7EBB2D18: ART BKT code ran there on the camera in test builds, never in a pinned build) |
| `uv run python emulator/hookcheck.py data/specs/raw-edit-art-bkt-3.json` | 17 transfers, 0 FAIL |
| `tools/checks.py data/builds/artbkt.json --tier full` | free-space, op-check, boot-test, update-path-test, artbkt-loop PASS. save-guard FAIL, peaking-s1-s5 REVIEW, peaking-s6-s7 REVIEW with S6 FAIL (art codes 9-184): **the pinned build peaking-mf gives the same results** (run the same day; the outputs differ only in the build's name). These scenarios compare with peaking-fast, a build before the film structure: not a fault of this build (I), and not of this work |
| Screens against the pinned build (section 3, A2) | Only the RAW Data Edit list differs |
| `gen/run.sh --check` | every generated spec as committed |
| `uv run --directory cli mypy`; black on the generator and its test | no issues; formatted |
| `uv run python -m unittest discover -s cli/tests` | 284 OK, 6 skipped (they need the built web app page) |
| `uv run epm2mod generate --check` | up to date |
