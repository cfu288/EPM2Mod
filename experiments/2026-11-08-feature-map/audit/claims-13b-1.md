# Audit A5 batch 1

## 13a-13 (sections/13a-libraries-runtime.md, line 13)

| 0x7E4C90CA–0x7E4FDFFF | **0xFF padding** (erased flash), no code | verified (bytes) |

## 13a-17 (sections/13a-libraries-runtime.md, line 17)

| inside it: 0x7E546973–0x7E548755 | CPU pixel kernels called only by art code (0x7E72Cxxx, 0x7E722868, ART_IMG_CF 0x7E7297FF); the last kernel 0x7E5486B4 is 162 B | verified (callers) (A4 2026-11-09) |

## 13a-131 (sections/13a-libraries-runtime.md, line 131)

| 0x7E5017A9 / 0x7E501942 | | internal | unpack double / float (class code in d3: 1 inf, 2 zero, 4 NaN) | V |

## 13a-173 (sections/13a-libraries-runtime.md, line 173)

| **0x7E54D5E4** | **job preparation**: work area (0x7E5503E8: one of 5 RAM areas 0x6050xxxx/0x6072xxxx by CPU, flags and op), then the **three op-type dispatches**: | | V |

## 13a-186 (sections/13a-libraries-runtime.md, line 186)

| 0x7E557410–0x7E55749A | calc work-area alloc and free (0x7E507325 / 0x7E507333; 512+512+3028-byte split) | MOV 0x7E6D0C03/0x7E6D0D73, REC 0x7E7125C3/0x7E71274B | V |

## 13a-266 (sections/13a-libraries-runtime.md, line 266)

- Code compares on art codes 96/97/165/166 and 117/121 (0x7E560B85). 09b lists compares on 181–184 (0x7E5659EB, 0x7E566813, 0x7E56826A, 0x7E5689A6) (verified). The table that P+89 indexes is still not found.

## 13b-14 (sections/13b-libraries-face-av.md, line 14)

| **OKAO core + PT** (facial parts) | **0x7E72CFA1–0x7E731584**. After the `ret` at 0x7E731582 come 3 bytes of 0xFF, then the libc `_ctype` table at 0x7E731588 (bytes 0x10/0x30/0xA0/0xC0/0x8C/0x89/0x81). Not ~0x7E732000. | Models and tables 0x7E85CEFC–~0x7E86DCxx (immediates from this code; end inferred). RAM: pool descriptors 0x602AE508 (W) and 0x602AE518 (B) | verified |

## 13b-15 (sections/13b-libraries-face-av.md, line 15)

| **OKAO SS "Smart Skin"** (beauty) | **0x7EBA7BC1–0x7EBABF8D**. It starts right after the last OXF code: the destructor 0x7EBA7B98 (stores vtable 0x7EBCDB0C, calls 0x7EBA7BB5, then the base destructor 0x7EBA7B13) and its 12-byte helper **0x7EBA7BB5–0x7EBA7BC0** (`add 16,a0`; if the word at this+16 is non-zero, store 0; `retf`; only caller 0x7EBA7B98). It ends at the `ret` at 0x7EBABF8B, followed by the strings `CIC_MUTEX`/`CIC_EN…` | LUTs 0x7EC92318–0x7ECAFF3C | verified bounds. Name: see §2.2 (A4 2026-11-09) |

## 13b-16 (sections/13b-libraries-face-av.md, line 16)

| **Red-eye library** (overlay A) | **0x7F0645C1–0x7F0691C5**. It includes the maths helpers 0x7F068F66–0x7F0691C5. The DB marks the page 0x7F069000 as data, but 0x7F069020/0x7F0690A0/0x7F06910C/0x7F069171 are code with callers. After the `ret` at 0x7F0691C3 come `ff ff` and the BASIC keyword table (`list run new bye next…`) at 0x7F0691C8 | 3-byte constants at 0x7F06AD94/97 | verified |

## 13b-18 (sections/13b-libraries-face-av.md, line 18)

| **AVPI AV middleware** | **0x7EE8F4F4–0x7EECE318**. Everything from 0x7EE63000 to 0x7EE8F4F3 has callers only in the C3D API (0x7EE61A–0x7EE62F) and the overlay-B C3D bridges. The first AVPI function, 0x7EE8F4F4, calls the kernel. After the `ret` at 0x7EECE316 come OSD-debug strings (`OSD DBG get`, `osddraw…`), so rodata starts at about 0x7EECE319 | Plug-in names, vtables and codec tables 0x7F02F600–~0x7F033xxx. Plug-in registry 0x7E8EFA18 (data image). Codec tables 0x7F0327DA–0x7F033xxx | verified (caller scan, bytes). Ranges inside AVPI: §2.4 |

## 13b-239 (sections/13b-libraries-face-av.md, line 239)

4. **The overlay-A face library is red-eye correction**, with cmd 5 sent by `play_face_redeye_adjust`. It is not "face scoring". **F076's score is the blue ratio** (byte 0 = B). Overlay-A code ends at **0x7F0691C5**, not 0x7F069000. Verified.

## 13b-250 (sections/13b-libraries-face-av.md, line 250)

10. **§04:** 0x7E6D886A is `MovmidApi_SetMakersInfoPrivateData` (AVSCA message 0x10C), not `USR_ScaCallback`. The QT `USR_ScaCallback` is **0x7E6D8900**. Verified strings.

