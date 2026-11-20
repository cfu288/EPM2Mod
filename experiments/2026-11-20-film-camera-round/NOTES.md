# Camera round of the untested films: an extra contrast curve in the card path (2026-11-20)

Labels: **V** = measured or read in the firmware, **I** = inferred. Nothing was flashed for this round: the owner
loaded two film files on the pinned build `gauge-info-3` and developed the synthetic test RAW in each entry.

## 1. What was done

- Film files: `uv run epm2mod films set -o build/films-batch1/EPM2LOOK.BIN --film ART1=provia ... --film
  ART12=vision3-50d` (sha256 `706fd70f…`) and batch 2 (Vis 200T, Tri-X and the ten Spectral Film LUT films,
  `d3d4fc08…`). 24 films that had no camera reading of the test RAW.
- On the camera: Load Looks; `PB130001.ORF` (`../2026-11-09-film-portra/testraw/`) developed with RAW Data Edit,
  [Current], once per ART entry. WB was Auto (Keep Warm Color Off), not the 5300 K preset of the earlier rounds;
  Noise Filter and Shading Comp. Off; everything else in the EXIF equal to the F5 round (**V**, exiftool diff).
- Copies: `../2026-11-09-film-portra/shots/newfilms1/N1_<film>.JPG`, `shots/newfilms2/N2_<film>.JPG` (not in
  git: the experiment ignores `shots/`). Files mapped to films by the EXIF ColorMatrix, which equals each film's
  fitted matrix with no difference (**V**). Duplicates: batch 1 PB200011 = PB200012, batch 2 Superia Reala developed
  twice (pixel-equal readings: the camera is repeatable, **V**).
- Readings: `read_mock.py` → `out/mock/read_N1_*.npz`, `read_N2_*.npz`; layout mock2a, 6590 of 6912 patches usable
  (F5: 6591).

## 2. The fault (**V**)

Camera minus model (`model2.render` with each shipped fit), mean ΔL* by the model's L*, the same for all 25
developments within 0.2, Tri-X included; a*, b* offsets near 0:

| L* | 0–15 | 15–30 | 30–45 | 45–60 | 60–75 | 75–90 |
|---|---|---|---|---|---|---|
| batch 1 and 2 | −3.3 | −5.1 | −3.5 | +1.4 | +5.5 | +6.1 |
| F5 round (compiled films, 2026-11-12) | −0.2 | −0.2 | 0.0 | +0.1 | 0.0 | −0.1 |

Mean ΔE camera vs model 3.2–3.5 (F5: 0.87–0.92). Not the white balance: the 2026-11-16 gallery photo, developed with
Auto WB on the compiled build `debug-log-films-12d`, tracks the model at every lightness (used for this diagnosis
only, not for a correction). Not a film applied twice or on top of another: that would differ per film (computed:
Provia −0.0…−3.8, Velvia 50 −4.0…−9.2, FP-100C +2.9…+13.2).

## 3. Cause (**V** in the firmware, **I** for the camera until the check)

The film codes' look-stage entry is `slots.IDENTITY_LOOK_HANDLER` = 0x7E56E94A. That handler is Cross Process I's
look handler (`mov 0x7E75F2F0,a0; jmp 0x7E56EB0F`); 0x7E75F2F0 is Cross Process I's luma table. The compiled
builds copied the identity table 0x7E75B8F0 over it (`seven-structure-extra`), so the name was true there. The
card path (`stock-films-structure`, since 2026-11-18) keeps the stock Cross Process table, so every film gets its
S-curve (64 → 209 instead of 256, 192 → 838 instead of 768). The emulator gate `equal_tables.py` compares every
film table except the look table, so it did not see it.

The model with that table predicts the measurement: −2.9 / −4.9 / −3.4 / +1.0 / +5.1 / +6.1; after it, every film
is within 0.3 L* (mean of the bins −0.2…+0.1), as in the F5 round.

## 4. Fix

A stub `LKID: mov 0x7E75B8F0,a0; jmp 0x7E56EB0F` in the shared area of the structure, and the film codes' look
entries (8 static, 4 switched by the loader) pointing at it. Stock filters without a film are unchanged. Built in a
scratch copy: free space, boot-test, update-path-test PASS; the emulator's look selector (case 0x7E56E837) picks
0x7E75B8F0 for all 12 film codes. Being made in the repository as new spec versions together with the film-name
EXIF change (`../2026-11-20-film-name-exif/`).

Camera check: one development of the test RAW with one film after the flash; pass = camera minus model within
±0.3 L* in every bin.

## 5. Then

The 25 readings stay valid: the corrections of these films use them with the anchor build modelled with the Cross
Process look, or after a second development on the fixed build.
