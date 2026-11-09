# Audit A8 batch 2 (15b)

## 15b-54 (sections/15b-camera-core-index.md, line 54)

| cam.c | `CamCommand` 0x7E628303 | 0x7E7AC020 (3–147; 03 §1) |

## 15b-55 (sections/15b-camera-core-index.md, line 55)

| cam_frame.c | 0x7E636AAB | jump 0x7E7AE744 (frame commands 1–85, 33 handled) |

## 15b-91 (sections/15b-camera-core-index.md, line 91)

- **Run set list** 0x7E65156C(d0 list type, a1 done): list of FrameType d0 (0x7E65210C), kept in the 20-slot table 0x6055EEF8, executed by 0x7E6513CF, finished by 0x7E651B0E or by FC 7.

## 15b-174 (sections/15b-camera-core-index.md, line 174)

- 0 INT_LANG 0x7E67510C; 1 EXT_LANG (returns NULL); 2 SOUND 0x7E67534F; 3 PIC 0x7E6753CC;

## 15b-220 (sections/15b-camera-core-index.md, line 220)

| 0x7E530103 | 4 | 5 | 0x6605 |

## 15b-222 (sections/15b-camera-core-index.md, line 222)

| 0x7E53023E | 6 | next packet → 4; last → 1 | 0x6607 |

## 15b-235 (sections/15b-camera-core-index.md, line 235)

- **Descriptor 0x6054AABC (V):** +0 timeout handler 0x7E5DE8AE, +4 tx buffer, +8 u16 command, +10 tx length, +12 rx length, +14 sync byte 0x55, +15 command echo. Send 0x7E5DC0F7, wait 0x7E5DE91F.

## 15b-243 (sections/15b-camera-core-index.md, line 243)

- **Request (52 B, V):** +0 channel, +1 type (0xF1 special), +4 1500, +8 5, +12 result buffer, +32 async callback, +40 sync marker. **Completion 0x7E45CCA1 (V):** calls +32 if set; otherwise copies the request to 0x6041538C and sets event flag 0x7E43EBB2.

## 15b-275 (sections/15b-camera-core-index.md, line 275)

- **03 §4 still phases are one too high (V).** The name lookup 0x7E656B1D does `inc d0` before its hash lookup (key = phase + 1). The phase values are therefore 0 READY, 1 TAKE, 2 STOP, 3 ABORT, 4 TERMINATE, 5 CONTINUE_READY, 6 CONTINUE_PAUSE, 7 CONTINUE_RESTART, 8/9 PRE_ACTION_ON/OFF, 10 MIRROR_DOWN, 11 CAPTURE_ENABLE, 12 FORCE_CAPTURE, 13 APERTURE_ENABLE; 0x100–0x10C BULB_*; 0xFFFF PHASE_NONE. This agrees with cam.c's still item 0x7E62952E (phase 0 → STL/RDY; 1 or 11 → STL/TAK; 5 → STL/CRDY).

