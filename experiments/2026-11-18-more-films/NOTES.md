# More spektrafilm films (2026-11-18)

Owner: "iterate through any spektrafilm luts we haven't already, and fit them and make them available".
Labels: V checked (byte compare, test run), I inferred. **Nothing here is camera-tested; nothing was flashed.**

## 1. Which films were new

spektrafilm `main` (3bb2c2d, 0.3.4) has 21 film profiles; `dev` and `experimental` add `kodak_doublex`,
`kodak_trix` and the print `kodak_2302`. Against `looks/catalogue.json` (19 films), three stocks were new:

| Profile | Film | Branch |
|---|---|---|
| `kodak_portra_800_push1` | Portra 800 pushed 1 stop | main |
| `kodak_portra_800_push2` | Portra 800 pushed 2 stops | main |
| `kodak_trix` | Kodak Tri-X Reversal Film 7266 (black-and-white **positive**) | dev 6cd00c8 |

Not done: other print papers for stocks we have (for example Portra 400 on 2383, a LUT that exists in `out/lut`,
or on Supra, Ultra or Ektacolor Edge paper). They are variants of a stock, not new stocks.
**Owner's decision (2026-11-18): skip print-paper variants; they are duplicates of stocks we have.** With this,
every spektrafilm film stock (main and dev) is in the catalogue.

## 2. A wrong film under the name Portra 800 (found and fixed)

`spektrafilm-lut` gives `kodak_portra_800`, `_push1` and `_push2` the same bundle name
(`spektrafilm_v034_portra800_portraendura_1lut_vlog_srgb`). The last build (2026-11-12) was push 2 and replaced the
others. The fit `looks/fits/portra800.npz` (2026-11-16) was made from that folder, so the look listed as
**Portra 800 was Portra 800 pushed 2 stops** (V: the cube header says `Film: kodak_portra_800_push2`; the fit's
`lut` field names that folder; the cube predates the fit). This is why it was the one fit marked "approximate
colours". All other LUTs in `out/lut` name the profile their folder names (V: headers listed).

Fix: the old fit is kept, unchanged except its `lut` path, as `fits/portra800push2.npz`; the LUT folders are now
`..._portra800_...`, `..._portra800push1_...` and `..._portra800push2_...` (built with `--name`, so they cannot
collide again); `fits/portra800.npz` is a new fit of the real Portra 800.

## 3. Reproducibility checks

- spektrafilm `main` 3bb2c2d, installed in a Python 3.13 environment outside the repository: rebuilding a LUT gives
  the expected film (the push 2 discovery came from this check).
- spektrafilm `dev` 6cd00c8: rebuilding Double-X on 2302 gives a cube byte-identical to the one Double-X was fitted
  from (V, sha256 of the data lines).

## 4. Fits (model only, as the 2026-11-16 extra films)

Colour films: `fit_film2.py --edge-weight 0.25` (n1) and `films-max/scripts/fit_starts.py --starts
superia400,pro400h,velvia100` (n2); the lower weighted error is kept. Mean dE2000 against the target, predicted by
the camera model:

| Look | Fit | Natural | Skin | ColorChecker x5 | Greys |
|---|---|---|---|---|---|
| Portra 800 (real) | n1 | 0.71 | 1.01 | 1.32 | 0.32 |
| Portra 800 +1 | n2 | 1.00 | 1.64 | 2.16 | 0.40 |
| Portra 800 +2 (the old Portra 800) | n2 of 2026-11-16 | 1.20 | 1.96 | 2.58 | 0.49 |

For comparison the other model-only films are 0.64 to 0.93 natural and 1.41 to 1.76 ColorChecker.

Tri-X: spektrafilm's profile is a reversal (positive) film. Printed on 2302 like Double-X it comes out as a
negative (grey ramp 227 down to 26). Baked as a slide film instead (`bake_slide.py`: the film is scanned, no
print; grey ramp 9 up to 201, neutral). Fitted as a colour look with saturation 0, as Double-X's card look
(`scripts/fit_bw_other.py`, which runs `card-looks/scripts/fit_bw_colour.py` with this LUT): natural 0.74, skin
0.59, ColorChecker 1.36, greys 0.09; 18 % grey 117.1 against 116.7.

## 5. Labels in the catalogue

Rule used: a ColorChecker error above 2.0 dE gets "approximate colours" in the kind and "less accurate than the
others" in the note. That marks Portra 800 +1 and +2. Portra 800 (real) loses the mark.

Menu names: "Portra 800 +1", "Portra 800 +2", "Tri-X". Whether the camera font draws "+" in a look name is not
tested (I: the stock number pickers draw "+").

## 6. What changed

`looks/fits/portra800.npz` (new fit), `portra800push1.npz`, `portra800push2.npz`, `trix.npz`;
`looks/catalogue.json` and `looks/film-records.json` (22 films); counts in the README, the card-looks guide and the
tests; licence notes in `NOTICE.md` and `looks/README.md`. Python tests (243) and the web checks and browser tests
pass. The LUTs and spektrafilm itself stay out of the repository.

## 7. Not checked on the camera

None of the four looks has been developed on the camera. A check is a Load Looks of a look file with them and one
RAW Data Edit of the test RAW each (`docs/film-emulation.md` section 3).
