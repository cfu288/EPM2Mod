# Audit batch 13-1

## 13a-126 (sections/13a-libraries-runtime.md, line 126)

| 0x7E501012 / 0x7E50106D / 0x7E50107C / 0x7E50108C | | 50, 63, 70, 102 | double → short / int / ushort / uint (core 0x7E501022) | V |

## 13a-138 (sections/13a-libraries-runtime.md, line 138)

| 0x7E5018DD | 11 | 107 | fneg | V |

## 13a-166 (sections/13a-libraries-runtime.md, line 166)

| 0x7E544AA9 | IMG init | ← Usr0 0x7E503DD4. Creates objects 102 and 105–108 (0x7E463C8E), the IMG_END flags (0x7E55EB2D) and buffers (0x7E54D59A); starts two tasks (0x7E449541) | V |

## 13a-175 (sections/13a-libraries-runtime.md, line 175)

| | (b) 0x7E560ACF → table **0x7E789604** (colour/tone parameter handlers); | | V |

## 13a-179 (sections/13a-libraries-runtime.md, line 179)

| 0x7E546973–0x7E5486B4 | art CPU kernels (e.g. 0x7E5475FC = the ART_IMG_CF kernel of section 03; 0x7E548351 = mask-job builder of 09b) | art only | V |

## 13a-189 (sections/13a-libraries-runtime.md, line 189)

| **0x7E55ECD8–0x7E55F959** | **pixel-defect correction kernels**: replace a pixel by the mean of its 4 same-colour Bayer neighbours (±2 columns, ±2 rows). 8-bit table 0x7E789230–0x7E7892AC (32 slots; slots 0x7E78926C and 0x7E7892AC point at empty `retf` stubs 0x7E55F1E7 / 0x7E55F521 that the database misses), 16-bit table 0x7E7892B0 (15). Lists from prm 0x70C4/0x70D4 (ROM) and **0x7044 `PRM_CCD_FIRST_PIXELDEFECT_ADDRESS`**, 0x7052 `…_SIZE`, **0x7144 `…_ADDRESS2`**, 0x7084/0x7092 (iterator 0x7E55ED89) | ← IMG_PRECON cmd 0 (0x7E55FAE8), MOV 0x7E6D0805 | V |

## 13a-196 (sections/13a-libraries-runtime.md, line 196)

| 0x7E575C3F–0x7E575E13 | `img_l0` post (mailbox 0x7E436467 / 0x7E434C5C, error `IMG_SYSTEM_ERR!!!`) and the **IMG0_LOCAL task** 0x7E575D41 (receive job → execute 0x7E575E13 → reply); CPU1 twin 0x7E575DB8 | task tables 0x7E43D5F0 (twin) | V |

## 13a-264 (sections/13a-libraries-runtime.md, line 264)

- Code compares on art codes 96/97/165/166 and 117/121 (0x7E560B85). 09b lists compares on 181–184 (0x7E5659EB, 0x7E566813, 0x7E56826A, 0x7E5689A6) (verified). The table that P+89 indexes is still not found.

## 13b-41 (sections/13b-libraries-face-av.md, line 41)

| 0x7E72CFA1 / 0x7E72CFBE | `OKAO_SetWMemoryArea` / `OKAO_SetBMemoryArea`(ptr, size) | They init pool 0x602AE508 / 0x602AE518 through 0x7E72CFED/0x7E72D003 → 0x7E72D01D. Return −3 for NULL/0 and −1 if too small (verified) |

## 13b-42 (sections/13b-libraries-face-av.md, line 42)

| 0x7E72CFDB / 0x7E72CFE4 | `OKAO_FreeWMemoryArea` / `OKAO_FreeBMemoryArea` | Name verified: 0x7E6FBCB0 prints these strings when they fail. They clear the 16-byte pool descriptors |

## 13b-47 (sections/13b-libraries-face-av.md, line 47)

| 0x7E72D9AE / 0x7E72DA05 | `OKAO_CreatePointer` / `OKAO_DeletePointer` | 96-byte handle, magic 0xECBC5054. Create copies 48 default bytes from 0x7E85D08F. The delete name is verified by string |

## 13b-208 (sections/13b-libraries-face-av.md, line 208)

- **Mask & 6** creates PT plus the contour module. The contour create is a stub that returns NULL, so this path always returns 0x8707. **Eye-retouch modules 2 and 4 are therefore dead** (verified: the stubs are 0x7E6FB6E3 and 0x7E6FB71E).

## 13b-237 (sections/13b-libraries-face-av.md, line 237)

2. **A second OKAO block:** 0x7EBA7BC1–0x7EBABF8D is OKAO **Smart Skin**, not OXF. The C1 note "OXF runs on to ~0x7EBA9xxx" is wrong: OXF ends at ~0x7EBA7BC0. Verified.

## 13b-239 (sections/13b-libraries-face-av.md, line 239)

4. **The overlay-A face library is red-eye correction**, with cmd 5 sent by `play_face_redeye_adjust`. It is not "face scoring". **F076's score is the blue ratio** (byte 0 = B). Overlay-A code ends at **0x7F0691C5**, not 0x7F069000. Verified.

## 13b-240 (sections/13b-libraries-face-av.md, line 240)

5. **§09b open question 1** ("0x7F0687C4 writes the art composite descriptor +284") is wrong. 0x7F0687C4 is the red-eye pixel correction, reached only from FACE cmd 5. Verified reachability; role inferred.

## 13b-242 (sections/13b-libraries-face-av.md, line 242)

7. **§03 "PT uses OKAO":** confirmed and extended. FD itself is the hardware engine at 0x99600000, driven by 0x7E6F8062–0x7E6F82C7 (verified addresses). OKAO is used **only** for PT (live eyes), for Smart Skin (cmd 11) and, inferred, for red-eye (cmd 5). **FACE_MAIN cmds 5/11 are now named** (§03 open question 9).

