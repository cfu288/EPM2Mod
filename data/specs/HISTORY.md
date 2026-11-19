# Patch history

The specs below are from the film-look work: superseded, experimental or failed. They sit in this folder with the
current specs; `tools/space-ledger/superseded.tsv` marks each one `history`.
They are a record of what we flashed (see `docs/camera-log/`) and of the steps in
`experiments/2026-11-09-film-portra/NOTES.md`. They are not part of the current build.

Do not flash these specs before you read the camera log. In particular:

- `slots7-*`, `remap7-code`, `remap7-neutral`: live view freezes in Soft Focus, Pin Hole and Diorama.
- `slots12-*`, `film-pro400h-pa2-s12`: never flashed. They use effect-filter numbers that are known
  to freeze live view.

Many of these specs change the same bytes, because each film patch was written to work alone in its
slot. You cannot combine them freely.

The current builds are in [`data/builds/`](../builds/). The top-level `README.md` lists them.

## Development history

The table is a record in the words of the time. "Current build" in a row means the build that was
current on that date. `NOTES` is `experiments/2026-11-09-film-portra/NOTES.md`. Some specs in the
table are still in `data/specs/` because a current build uses them.

| Spec | Status |
|---|---|
| `pixel-hacking` | camera-tested, works (PoC: renames a menu label) |
| `curve-probe-2` | built, **not camera-tested** (Cross Process I := Natural + Saturation +2; verifies the per-channel base-gamma tables, NOTES §14.3) |
| `film-portra-xp` (+ `label-portra`) | **camera-tested 2026-11-11, works** as `build/film-portra-xp-labelled.BIN` (Portra 400 in the Cross Process I slot; NOTES §14.4, §15) |
| `film-portra-xp2` (+ `label-portra`) | built, **not camera-tested** (as above plus a fitted luma look curve; NOTES §16.3) |
| `film-portra-xp` + `label-portra` | camera-tested 2026-11-11, works (first Portra build) |
| + `sixaxis-probe-1` / `sixaxis-portra-1` (xp3) | camera-tested 2026-11-11, work (see docs/camera-log/) |
| `sixaxis-portra-2` (xp4), `sixaxis-portra-3` (xp5) | built, not camera-tested |
| `xp-adaptive-hue-off`, `film-portra-xp7` (xp6 / xp7 builds) | xp7 flashed OK 2026-11-12; first patches that change code bytes (NOTES §22–23) |
| `film-portra-xp8` | flashed OK 2026-11-12; measured with the synthetic test RAW (NOTES §23–25) |
| `film-portra-xp9` | flashed OK 2026-11-12; mock natural colours ΔE 1.31 vs target, as predicted (NOTES §25) |
| `film-ektachrome-pa2` | built, **not camera-tested**; Ektachrome 100 in the Pop Art II slot, data only (NOTES §26) |
| `film-ektachrome-lt`, `label-ektachrome-lt` | flashed OK 2026-11-12; Ektachrome 100 in the Light Tone slot, ΔE 1.55 on mock natural colours (NOTES §26.5–26.6; slot map in `docs/dev/art-filter-slots.md`) |
| `film-ektachrome-lt2` | flashed OK 2026-11-12; ΔE 1.39 on mock natural colours, as predicted (NOTES §26.6) |
| `film-portra-xp10`, `film-ektachrome-lt3` | flashed OK 2026-11-12 (current build); refits against the measured fit objective; scene-independence confirmed with the blue-scene test RAW (NOTES §27–28) |
| `slot3-code`, `film-pro400h-pa1`, `label-pro400h-pa` (+ `…-s3` copies of the two film patches) | flashed OK 2026-11-12 (`three-films-1`): **first new code, works**; third film (Fuji Pro 400H) in the Pop Art entry, look distorted by Pop Art's chroma curves (NOTES §29–30) |
| `slot3-chroma-linear` | flashed OK 2026-11-12 (`three-films-2`, current build): Pro 400H natural colours ΔE 1.20 (NOTES §30.4) |
| `film-pro400h-pa2` | built, **not camera-tested** (`three-films-3`): correction refit of Pro 400H (NOTES §30.4) |
| `slots7-code`, `slots7-neutral` | built, **not camera-tested** (`seven-slots-neutral`): Pale&Light, Soft Focus, Pin Hole and Diorama as film slots with a neutral test look; emulator-checked (docs/dev/art-slots-evaluation.md, NOTES §32) |
| `slots12-code`, `slots12-neutral`, `film-pro400h-pa2-s12` | built, **do not flash** (uses effect numbers 106 / 108; NOTES §35) (`twelve-slots-neutral`): all twelve visible filters as film slots; the five effect filters use the numbers of hidden second types; emulator-checked (docs/dev/art-slots-evaluation.md §4, NOTES §33) |
| `slots7-kind` | flashed 2026-11-12 with slots7-code (`seven-slots-neutral-b`): **live view freezes** in Soft Focus, Pin Hole, Diorama (NOTES §34–35) |
| `remap7-code`, `remap7-neutral` | flashed 2026-11-12 (`seven-slots-remap-neutral`): **live view freezes** in Soft Focus, Pin Hole, Diorama (NOTES §35–36) |
| `four-code`, `four-neutral` | built, **not camera-tested** (`four-slots-neutral`): the three films + Pale&Light as a fourth slot; no effect filter touched (NOTES §36) |
| `remap7b-code` | flashed OK 2026-11-12 (`seven-slots-remap2-neutral`, current build): **live view no longer freezes** in the three remapped entries (NOTES §37) |
| `seven-structure-extra`, `seven-films-1`, `seven-labels` | **camera-tested** (`seven-films-1`, 2026-11-12; `seven-films-2`, corrected fits for the four new films, camera-tested the same day; open: rare restart when RAW Data Edit saves, see camera log): seven films in menu order: Portra 400, Ektachrome 100, Pro 400H, Kodachrome 64, Vision3 250D, Velvia 100, Superia X-tra 400 (NOTES §39) |
| `curve-probe-1`, `film-portra` | superseded drafts, not camera-tested (NOTES §12.5, §13) |
