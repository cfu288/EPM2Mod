# Film simulation data

- `catalogue.json`: every fitted film that a look pack for the SD card can hold, with the short id that
  `epm2mod install --film ART2=velvia` and `epm2mod films set --film ART2=velvia` use and the name the camera shows (`epm2mod films`).
- `card-looks.json`: a developer look list of fit files, one per ART entry, the input of `epm2mod films pack`.
- `film-records.json`: each film of the catalogue with its look record, and the Olympus art filter of each ART entry.
  `epm2mod install`, `epm2mod films set`, the local app and the web site make look packs from it, without numpy. Made from the fits
  by `uv run python web/scripts/export_films.py`; a test fails when it is out of date.
- `fits/*.npz`: the fitted values of each look. One file holds three tone curves of 1,024 points, a
  saturation gain, six saturation values and six hue values, a 3 × 3 matrix, and two chroma curves.
  `fits/doublex3.npz` is Double-X as a colour look: saturation gain 0, the art matrix sets the grey mix, one tone
  curve for the three channels (`experiments/2026-11-17-card-looks/design.md`).
  `fits/*-n2.npz` are the fits the catalogue uses: corrected for the camera without the 12-region stage
  (`films-twelve-off`) and measured on it (2026-11-21, `experiments/2026-11-20-model-calibration/NOTES.md` §9-11).
  The other files are earlier fits that a spec, a test or a list still names (the specs of older builds in
  `data/specs/` were made from them); earlier fits that nothing names were removed on 2026-11-21
  (`docs/dev/moved-paths.md`).

How the fits were made: `experiments/2026-11-09-film-portra/`, `experiments/2026-11-16-films-max/` and
`experiments/2026-11-18-more-films/`.

Except the ten fits listed below, the fit data is derived from [spektrafilm](https://github.com/andreavolpato/spektrafilm) by Andrea
Volpato, licensed CC BY-SA 4.0. We modified it: we fitted it to the stages of the Olympus E-PM2
that can be adjusted. See `NOTICE.md`.
`fits/doublex.npz`, `fits/doublex2.npz` and `fits/doublex3.npz` are derived from the profiles `kodak_doublex` and `kodak_2302` of spektrafilm's `dev` branch
(commit `6cd00c8d4f30b5b550f50f4bbd3753c9f2a48507`, CC BY-SA 4.0). Modified: fitted to this camera.
`fits/trix-n3.npz` is derived from the profile `kodak_trix` (Tri-X Reversal 7266) of the same commit, rendered as a
reversal film with no print (`experiments/2026-11-18-more-films/NOTES.md`). Modified: fitted to this camera.

`fits/velvia-50.npz`, `fits/natura-1600.npz`, `fits/pro-160s.npz`, `fits/superia-reala.npz`, `fits/agfa-vista-100.npz`, `fits/vericolor-iii.npz`, `fits/aerocolor-iv.npz`, `fits/eterna-500.npz`, `fits/exr-200t.npz`, `fits/fp-100c.npz` are derived from film simulations of [Spectral Film LUT](https://github.com/JanLohse/spectral_film_lut) by
Jan Lohse (version 0.18.14), MIT License, Copyright (c) 2026 Jan Lohse (`third_party/spectral_film_lut/LICENSE`).
Modified: fitted to this camera (`experiments/2026-11-19-film-sources/NOTES.md`). Their catalogue entries say
"simulated with Spectral Film LUT".
