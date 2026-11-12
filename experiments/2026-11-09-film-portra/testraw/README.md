# Synthetic test RAWs for the Olympus E-PM2

Hand-made Olympus ORF files (12-bit, compressed, written with our own encoder `../orfcodec.py`).
Each is a grid of flat colour patches whose raw values we chose, so every picture the camera
develops from it can be compared patch by patch with what was asked for. Copy one to the card as
`DCIM/100OLYMP/<name>.ORF`, then use Playback → Edit → RAW Data Edit with the picture mode or art
filter to test.

| File | Made by | Contents |
|---|---|---|
| `PB130001.ORF` | `../make_mock2.py` | The main test image: gray ramp, GRKit grays, ColorChecker at five exposures, a skin series, 3,500 natural colours, hold-out colours, near-neutrals, gamut-edge colours. Layout: `mock2a_layout.npz`. |
| `PB130002.ORF` | `../make_mock2.py` | "Blue scene": the same patches repeated inside a frame that is two-thirds sky and sea blue, to test whether the camera's rendering depends on scene content. Layout: `mock2b_layout.npz`. |
| `PB120001.ORF` | `../make_mock.py` | First-generation test image (superseded). Layout: `mock_layout.npz`. |

The layout files hold, per patch, its position, its raw RGB, its group (`kind`) and its weight in
the fit. `../read_mock.py` reads a camera JPEG back into patch values with them; it looks for the
layouts in `../out/mock/`, so copy them there first.

sha256:

```
5f7f498a1f8df0177264ddf1940db5db225c6b4ee323bd5e0727a4ad989701c0  PB120001.ORF
11ffbe414de2448fc2b8d408eb083a230188159d2613ef62e9aae685c08bcf77  PB130001.ORF
6ccc083639801bf4e55480c7959b9755f4068a849fb813b9bafaea78286a0c6f  PB130002.ORF
```

Things to know:

- The header (EXIF and maker notes, including white balance 5300 K and the colour matrix) comes from
  a real E-PM2 photo of a displayed colour chart. The embedded preview and thumbnail still show that
  chart photo, not the patch grid; only the raw data is ours.
- The owner name and the body, internal and lens serial numbers were blanked in these copies (same
  length, in place). The raw data is bit-identical to the files used for the measurements in
  `../NOTES.md`. **The blanked copies have not yet been developed on a camera.**
- The files are for the E-PM2 (16 MP, 4640 × 3472 raw). Other models will likely refuse them.
- They are test patterns, not photographs; no rights are claimed beyond the repository's licence.
  The header layout and field contents are the camera's.
