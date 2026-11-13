# Film looks: the data behind the patch specs

- `films.json`: which film goes in which art-filter menu entry, the name shown in the menu, and the
  fit file. It also names the three patch specs that are generated from it.
- `fits/*.npz`: the fitted values of each look (three tone curves of 1,024 points, saturation gain,
  six saturation and six hue values, a 3 × 3 matrix, two chroma curves).

`uv run --extra looks epm2mod looks --check` regenerates the three patch specs from these files and
the stock firmware, and compares them with the specs in `patches/`. `--write` writes them.

How the fits were made: `experiments/2026-11-09-film-portra/`.

The fit data is derived from [spektrafilm](https://github.com/andreavolpato/spektrafilm) by Andrea
Volpato, licensed CC BY-SA 4.0, modified by fitting it to the Olympus E-PM2. See `NOTICE.md`.
