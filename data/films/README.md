# Film simulation data

- `films.json`: for the older builds that replace art filters in the firmware (the pinned build keeps Olympus's
  filters and loads films from the card): which film goes in which art-filter menu entry, the name shown in the menu, and the
  fit file of the film. It also names the three patch specs that are generated from this data.
- `catalogue.json`: every fitted film that a look file for the SD card can hold, with the short id that
  `epm2mod install --film ART2=velvia` and `epm2mod films set --film ART2=velvia` use and the name the camera shows (`epm2mod films`).
- `card-looks.json`: a developer look list of fit files, one per ART entry, the input of `epm2mod films pack`.
- `film-records.json`: each film of the catalogue with its look record, and the Olympus art filter of each ART entry.
  `epm2mod install`, `epm2mod films set`, the local app and the web site pack look files from it, without numpy. Made from the fits
  by `uv run python web/scripts/export_films.py`; a test fails when it is out of date.
- `fits/*.npz`: the fitted values of each look. One file holds three tone curves of 1,024 points, a
  saturation gain, six saturation values and six hue values, a 3 × 3 matrix, and two chroma curves.
  `fits/doublex3.npz` is Double-X as a colour look: saturation gain 0, the art matrix sets the grey mix, one tone
  curve for the three channels (`experiments/2026-11-17-card-looks/design.md`).
  `fits/*-c1.npz` are the fits corrected from the camera round of 2026-11-20; the catalogue uses them, and the older
  file of the same film stays because firmware specs of older builds are generated from it.

- `more-films.json`: the films beyond the first seven (used by the older builds `films-12` to `films-12d`): which film goes in
  which of the five other art-filter entries, its menu name and its fit file, and the names of the specs
  that are generated from it: `films12-structure` (code and table entries), `films12-looks` (the looks)
  and one `films12-entry-*` spec per menu entry. Leave an entry spec out of a build and that entry is the
  stock art filter again. `fits/` also holds fits that no firmware list uses (C200, Portra 800, UltraMax 400,
  Verita 200D, Vision3 50D and 200T, Portra 800 pushed 1 and 2 stops, Tri-X); every fit is in `catalogue.json`.

- `films-12-bw.json`: a variant of `more-films.json` with a black-and-white film (used by the older builds
  `films-12-bw`, `films-12c` and `films-12d`). The entry Grainy Film keeps its stored value, its art codes and its grain program and holds
  Kodak Double-X 5222 on 2302 print film; the colour film of that entry in `more-films.json` moves to the entry
  named in `moved_to`. It makes two specs, both deltas on the specs of `more-films.json`:
  `films12bw-doublex` (the look) and `films12bw-entry-gentle-sepia`. `fits/doublex.npz` holds the art matrix
  `A` (how colours turn into grey), the tone curve `D`, and the two tables made from it: `T` (the grain
  program's contrast table) and `L` (the look table for live view and movies). Its names spec is
  `data/specs/films12bw-names.json` (`experiments/2026-11-16-doublex/scripts/names_bw.py`); the notes in that
  folder say how the camera makes the entry monochrome and how the fit was made.
  `refits` lists later fits of the film, made after a camera measurement (`fits/doublex2.npz`): each makes a
  spec (`films12bw-doublex2`) that goes after `films12bw-doublex` in a build and changes the grain table only.

The menu names of `more-films.json` in all 34 languages are a spec of their own, `data/specs/films12-names.json`.
`experiments/2026-11-16-films-max/scripts/names_spec.py` makes it; the notes in that folder say how the
slots work and how the fits were made.

Do not edit the generated film patch specs in `data/specs/` by hand. Change the data here, then run:

```bash
uv run epm2mod generate
```

The command makes the specs of both lists again from the data and the stock firmware. It needs numpy
(`uv run` installs it) and the stock firmware file (`uv run epm2mod fetch-stock`).
`uv run epm2mod generate --check` only compares and changes nothing.

If the operations of a spec change, the command marks the spec "built, NOT camera-tested". A tested
build that uses the spec then no longer gives its recorded sha256, and `epm2mod make` refuses it.
Make a build description with a new name and test it on a camera.

How the fits were made: `experiments/2026-11-09-film-portra/`, `experiments/2026-11-16-films-max/` and
`experiments/2026-11-18-more-films/`.

Except the ten fits listed below, the fit data is derived from [spektrafilm](https://github.com/andreavolpato/spektrafilm) by Andrea
Volpato, licensed CC BY-SA 4.0. We modified it: we fitted it to the stages of the Olympus E-PM2
that can be adjusted. See `NOTICE.md`.
`fits/doublex.npz`, `fits/doublex2.npz` and `fits/doublex3.npz` are derived from the profiles `kodak_doublex` and `kodak_2302` of spektrafilm's `dev` branch
(commit `6cd00c8d4f30b5b550f50f4bbd3753c9f2a48507`, CC BY-SA 4.0). Modified: fitted to this camera.
`fits/trix.npz` is derived from the profile `kodak_trix` (Tri-X Reversal 7266) of the same commit, rendered as a
reversal film with no print (`experiments/2026-11-18-more-films/NOTES.md`). Modified: fitted to this camera.

`fits/velvia-50.npz`, `fits/natura-1600.npz`, `fits/pro-160s.npz`, `fits/superia-reala.npz`, `fits/agfa-vista-100.npz`, `fits/vericolor-iii.npz`, `fits/aerocolor-iv.npz`, `fits/eterna-500.npz`, `fits/exr-200t.npz`, `fits/fp-100c.npz` are derived from film simulations of [Spectral Film LUT](https://github.com/JanLohse/spectral_film_lut) by
Jan Lohse (version 0.18.14), MIT License, Copyright (c) 2026 Jan Lohse (`third_party/spectral_film_lut/LICENSE`).
Modified: fitted to this camera (`experiments/2026-11-19-film-sources/NOTES.md`). Their catalogue entries say
"simulated with Spectral Film LUT".
