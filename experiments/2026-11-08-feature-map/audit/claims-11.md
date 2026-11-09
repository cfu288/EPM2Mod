# Audit batch 11

## 11-15 (sections/11-version-history.md, line 15)

| 1.2 (May 9 2013) | Touch-panel stability in playback; VF-4 support | **VF-4: verified.** A new accessory ID 0x0322 = "Evf3", a new I²C bus configuration, an init write, and the VF-4 display path. Large rebuild (≈1,400 code functions differ). Touch fix **not isolated** | VF-4 **yes**; touch **unresolved** |

## 11-19 (sections/11-version-history.md, line 19)

| 1.6 (Oct 23 2018) | AF with Panasonic H-ES200 / H-ES50200 | **Focus-position variables widened from 16 to 32 bits** across the AF code (0x7E5E3000–0x7E627000). A new saturating clamp to [−32768, 32767] at 39 sites. AF structs grow. Code after 0x7E626937 shifts by +0x2AC | **Yes** (code verified; the link to these lenses inferred) |

## 11-31 (sections/11-version-history.md, line 31)

- **Function-boundary artifacts.** A new call target or pointer splits or merges database functions. `region.py`/`cdiff.py` therefore diff whole code streams of each gap. Several "changed" playback functions in 1.3 (0x7EB6318E, 0x7EB638FC) turn out to be byte-identical code that was only split differently (verified).

## 11-85 (sections/11-version-history.md, line 85)

- **Undocumented in 1.2 (verified strings, purpose inferred):** I²C "ACC" debug commands (0x7E458938, 0x7E458B28), GUI LOWAPI area traces and `sdk dbggrid`. The rest of the rebuild (C++ app about 400, GUI about 130, camera core about 170 changed) was not attributed.

## 11-112 (sections/11-version-history.md, line 112)

- **What the value is (partly inferred).** All six sites build a request for 0x7F0A4A20(d0=0, d1=13 read / 14 write, a1=iSDIO register address such as 0x603/0x440, stack = length, **stack+8 = 19/18**). 0x7F0A4A20 stores that value at request +24, then queues the request through 0x7E5CBA12 to the card driver (verified). What field +24 means to the SD driver was not traced.

## 11-119 (sections/11-version-history.md, line 119)

| New `is_type` classifier | — | 0x7E523C09: returns 0 if the lens record's (+6632) bit 1 is clear; 1 if 0x7E52260A()=1 (lens-ID byte0 = 0, byte1 ≠ 0); 2 if 0x7E522622()=1 (byte0 = 2 or 3, byte1 ≠ 0); else 3 | verified code; "1 = Olympus, 2 = Panasonic/Leica" inferred from ExifTool make codes |

## 11-120 (sections/11-version-history.md, line 120)

| Lens-OIS state test | 0x7E522323: returned bit 1 of 0x604F7F64 | 0x7E5223DF: returns it **only if 0x7E522622() = 1** | verified |

## 11-121 (sections/11-version-history.md, line 121)

| IS decision that uses `is_type` | 0x7E5A6535 (no lens-type test) | 0x7E5A59EA: when 0x7E598A60()=1 and `is_type`=1, it applies a different condition (0x7E598A72) before writing byte +735 | verified code; "body/lens IS choice" inferred |

## 11-122 (sections/11-version-history.md, line 122)

| Lens-info pages | list up to 025, `cmp 26` (0x7E526343) | adds 030 `LENS_INFO_ENABLE`, 033 `CURRENT_CONSUMPTION`; `cmp 34` (0x7E5266BC); `lens current` 0x7E524117/0x7E524134 | verified |

## 11-127 (sections/11-version-history.md, line 127)

- **Windows 10:** **not found.** The overlay diff is small: one call in `SetDevicePropValue` (0x7F08B56E) and the version constants. No USB descriptor or MTP string changed (verified). Probably host-side or very minor (inferred).

## 11-137 (sections/11-version-history.md, line 137)

- The block-0 diff is **not** "≈ relocation". 358 code functions change, almost all in the AF code 0x7E5E3000–0x7E627000 (about 300) (verified).

## 11-143 (sections/11-version-history.md, line 143)

- **No H-ES200/H-ES50200 lens ID** (0x21036/0x21037, i.e. ExifTool `2 36 10`/`2 37 10`) appears in v1.5 or v1.6, as an immediate or as table bytes (verified). The fix is generic.

