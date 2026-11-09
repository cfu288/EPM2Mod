# Audit batch 12

## 12-35 (sections/12-exposure-af-files.md, line 35)

| Corner resolver | 0x7E6940C6 / 0x7E694181 / 0x7E6941DA → 0x7E694412 | Sentinels (verified): 0x9B00 → user value (0x7E69561E, or 0x7E6A30B0 when byte +40 = 4); 0x6400 → max (field +16); 0x9C00 → min (field +14). Every result is clamped to [min, max] by 0x7E6A8EA4. 0x7E6941DA also has cases for the art codes 69–181 | verified |

## 12-39 (sections/12-exposure-af-files.md, line 39)

| APEX → Exif rational | 0x7E69B184 (Tv), 0x7E69B1D9 (Av), 0x7E69B31E (bias) | Called by the Exif filler. Each has three variants for step 256 / 128 / other. Small lookup tables at 0x7E7E1xxx | verified calls; tables not decoded |

## 12-78 (sections/12-exposure-af-files.md, line 78)

- **The still result holds every metering candidate.** The capture block +60 is printed by 0x7E69EDF3 (`exp_cal_still[bv]`). It holds `bv_cntr, bv_arnd, bv_ave, bv_ave2, bv_esp, bv_spot`, then `face_num, gyako` (backlight), `mode` and `bv_std` at +200/+201/+202 (verified field offsets).

## 12-123 (sections/12-exposure-af-files.md, line 123)

- **Unnamed codes:** 0x504, 0x50D, 0x50E, 0x90A, 0x90B and 0x1402 have no help line; `com 10` is unused (verified).

## 12-176 (sections/12-exposure-af-files.md, line 176)

- **Lens commands** (verified function strings): `fcs_lens_mfts_scan_lens` 0x7E60D90F (variants `(2Ri)`, `(2Rr)`, `(2Rm)`), `scan_only_lens` 0x7E60DFF4, `scan_lens_wob` 0x7E60E308, `move_lens` 0x7E60E648, `move_lens_ofset(_vd)(_sim)` 0x7E60EAB7–0x7E60EF1E, `stop_lens(_wob/_force)` 0x7E60C919–0x7E60D5B9, `scan_chg_speed(_multi)` 0x7E60BC39 / 0x7E60B908, `chk_lens_stop(2)` 0x7E60F2DC / 0x7E60F7ED.

## 12-187 (sections/12-exposure-af-files.md, line 187)

- The spot dump 0x7E5E6063 prints `area_no`, the spot, still and AF centres, `bayer_af_w/h`, and `single_area[i].hs/vs/hw/vw` (verified).

## 12-213 (sections/12-exposure-af-files.md, line 213)

- **How an IFD is written:** each one comes from a pointer list of 12-byte tag templates `{u16 tag, u16 type, u32 byte_length, u32 struct_offset}`. The templates are at 0x7E84EF20–0x7E850438 and the lists at 0x7E850434–0x7E851510. The generic writer 0x7E708AAB copies from struct+offset. Tags 256–37500 that hold offsets get special cases (verified).

## 12-223 (sections/12-exposure-af-files.md, line 223)

- **Type 0 and 1 variants:** the first list of each pair is used when struct+16478 = 1. For type 0 the 17-tag IFD0 adds WhitePoint, PrimaryChromaticities and YCbCrCoefficients. The filler then writes 0.313/0.329, the primaries 0.64/0.33, 0.21/0.71, 0.15/0.06, Gamma 2.2 (0xA500) and InteropIndex `R03` instead of `R98` (verified). This is the **Adobe RGB** marking (the primaries are Adobe RGB 1998; external).

## 12-224 (sections/12-exposure-af-files.md, line 224)

- **Fixed strings:** ExifVersion `0230`, FlashpixVersion `0100`, ImageDescription `OLYMPUS DIGITAL CAMERA`, Software template `Version x.x`, and PrintIM `0300` (0x7E70948C) (verified).

## 12-225 (sections/12-exposure-af-files.md, line 225)

- **MakerNote header:** `OLYMPUS\0` `II` 0x0003, written at 0x7E708A45 (verified). This is the "new" Olympus format with sub-IFDs (external).

## 12-249 (sections/12-exposure-af-files.md, line 249)

- **ORF IFD0 values** (0x7E71969F, verified constants):

## 12-260 (sections/12-exposure-af-files.md, line 260)

- **Sensor capture packing:** the cam debug at 0x7E62F370 offers "12 = 12bit" and "pack up / pack down" (verified strings). This is the in-memory format, not the file format.

