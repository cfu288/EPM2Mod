# Audit A10 batch 2

## 11-16 (sections/11-version-history.md, line 16)

| 1.3 (Oct 9 2014) | AF precision with the 40-150 F2.8 PRO | **One real code change** (0x7E6232ED): a lens-ID and lens-protocol test picks a different AF parameter set. Plus version constants | **Yes** (code verified; the 40-150 link inferred) |

## 11-19 (sections/11-version-history.md, line 19)

| 1.6 (Oct 23 2018) | AF with Panasonic H-ES200 / H-ES50200 | **AF position variables widened from 16 to 32 bits** across the AF code (~0x7E5E3000–~0x7E627000, page-rounded (L1 2026-11-09)); "focus position" is inferred from the `fcs_*` names. A new saturating clamp at 39 sites: 38 clamp to [−32768, 32767], one (0x7E60A5EE) to [0, 32767]. AF structs grow. Code from 0x7E626937 to about 0x7E76EA1F shifts by +0x2AC; code from 0x7E8F1C68 on does not move (audit 2026-11-09) | **Yes** (code verified; the link to these lenses inferred) |

## 11-115 (sections/11-version-history.md, line 115)

- **What the value is (partly inferred).** All six sites build a request for 0x7F0A4A48 (v1.3/v1.4; 0x7F0A4A20 in v1.5/v1.6) with d0=0, d1=13 read / 14 write (13 at 5 sites, 14 at 1, in the write command), a1=iSDIO register address such as 0x603/0x440, stack = length, **stack+8 = 19/18**. The builder stores that value at request +24, then queues the request through 0x7E5CB393 (v1.3/v1.4; 0x7E5CBA12 in v1.5/v1.6) to the card driver (verified) (audit 2026-11-09). What field +24 means to the SD driver was not traced.

## 11-132 (sections/11-version-history.md, line 132)

- In v1.4, 0x7F08CC99 (46 bytes) copies the host-supplied string (length byte × 2 bytes, bounded only by the 8-bit length) to RAM 0x602C1A98 with memcpy 0x7E5081FA, then returns 0x2001. In v1.5 it is `mov 0x2001,d0; retf`: it answers OK and stores nothing (verified). The 40-byte shrink shifts the later overlay code by −0x28; the call at 0x7F08B5DE differs only in its register-save operands.

## 11-174 (sections/11-version-history.md, line 174)

- **Candidate only:** Windows 10 (1.5): the stubbed PTP property 0xD406 handler (code verified, link inferred) (audit 2026-11-09).

## 12-36 (sections/12-exposure-af-files.md, line 36)

| Exposure-mode switch | 0x7E6945EF | Program code 6 or 58 → 0x7E69464B (manual path). Any other code → 0x7E6947C1 (auto path). Then 0x7E694F5D, 0x7E6951A6, 0x7E695591. Mode byte 90 → 0x7E69474D | verified |

## 12-78 (sections/12-exposure-af-files.md, line 78)

- **The still result holds every metering candidate.** The block printed by 0x7E69EDF3 (`exp_cal_still[bv]`; capture block +60) holds the six BVs at +0…+10 (spot, esp, ave, ave2, cntr, arnd), then face_num (u8 +200), mode (u8 +201) and bv_std (u16 +202). `gyako` (逆光, backlight — translation, inferred) is a byte from capture block +336, passed in d0 (audit 2026-11-09; verified offsets).

## 12-213 (sections/12-exposure-af-files.md, line 213)

- **How an IFD is written:** each one comes from a pointer list of 12-byte tag templates `{u16 tag, u16 type, u32 byte_length, u32 struct_offset}`. The templates are at 0x7E84EF20–0x7E8503FB (445 × 12 bytes) and the lists at 0x7E8503FC–0x7E851663; the last list (FocusInfo, 85 entries) starts at 0x7E851510 (audit 2026-11-09). The generic writer 0x7E708AAB copies from struct+offset. Tags 256–37500 that hold offsets get special cases (verified).

## 12-249 (sections/12-exposure-af-files.md, line 249)

- **ORF values** (0x7E71969F, verified constants). Most are IFD0; CFAPattern is Exif tag 0xA302 (struct+2407) and ValidBits is ImageProcessing 0x0611 (struct+4360) (audit 2026-11-09). "12-bit in 16-bit containers" is inferred from ValidBits 12 and BitsPerSample 16:

## 12-260 (sections/12-exposure-af-files.md, line 260)

- **Sensor capture packing:** the cam debug at 0x7E62F370 offers "12 = 12bit" and "pack up / pack down" (verified strings). This is probably the in-memory format, not the file format (inferred; audit 2026-11-09).

