# Film looks: the data behind the patch specs

- `films.json`: which film goes in which art-filter menu entry, the name shown in the menu, and the
  fit file of the film. It also names the three patch specs that are generated from this data.
- `fits/*.npz`: the fitted values of each look. One file holds three tone curves of 1,024 points, a
  saturation gain, six saturation values and six hue values, a 3 × 3 matrix, and two chroma curves.

Do not edit the three film patch specs in `patches/` by hand. Change the data here, then run:

```bash
uv run epm2mod looks --write
```

The command makes the three specs again from the data and the stock firmware. It needs numpy
(`uv run` installs it) and the stock firmware file (`uv run tools/fetch_stock.py`).
`uv run epm2mod looks --check` only compares and changes nothing.

If the operations of a spec change, the command marks the spec "built, NOT camera-tested". A tested
build that uses the spec then no longer gives its recorded sha256, and `epm2mod make` refuses it.
Make a build description with a new name and test it on a camera.

How the fits were made: `experiments/2026-11-09-film-portra/`.

The fit data is derived from [spektrafilm](https://github.com/andreavolpato/spektrafilm) by Andrea
Volpato, licensed CC BY-SA 4.0. We modified it: we fitted it to the stages of the Olympus E-PM2
that can be adjusted. See `NOTICE.md`.
