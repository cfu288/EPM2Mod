# Audit A9 batch 1 (15b)

## 15b-58 (sections/15b-camera-core-index.md, line 58)

| cam_set.c | 0x7E650607 | hash 0x7E7BB094 (§2.2) |

## 15b-82 (sections/15b-camera-core-index.md, line 82)

| 93–97 | 0x7E650BCB … 0x7E650BFF (13 B each) | FC72, 73, 74, 75, 76 (95 = COM_MOVIE_ENABLE) |

## 15b-93 (sections/15b-camera-core-index.md, line 93)

- **Callback stubs:** per-module completions 0x7E651839–0x7E6519A2 (10 × ~40 B: decrement the list count +42, call one module's finish, then 0x7E651B0E); list-done 0x7E6515C0–0x7E651644 (7 × 22 B: release the list, set bit 2/4 of the sequence object); frame-done 0x7E65165A–0x7E65181E (21 × 27 B, pointer-only: free the request, set bit 2/4/8 of objects 32–40, 54–56).

## 15b-125 (sections/15b-camera-core-index.md, line 125)

- The bits are the module's own step events. The still/LB monitor prints phase names (0x7E656B1D), not the cam.c factor names, so the cam factor table (03 §1) does not name them (V).

## 15b-136 (sections/15b-camera-core-index.md, line 136)

| cam_set sequence | `mov a0,a2; mov ID,d0; clr d1; mov 1,a0; call 0x7E635665; …; mov STEP,a0; call 0x7E6359B1; mov ID,d0; mov 1,d1; call 0x7E63589A` (55 B) | start sequence STEP on cam_ev object ID |

## 15b-160 (sections/15b-camera-core-index.md, line 160)

| EMS1 AF-area motion | 0x7E66C501–0x7E66CE89 | start 0x7E66C501 (← TAKE `ems_start`); per-frame 0x7E66C72B → 0x7E66C9A8 (EMS1 results 0x7E45FDFA/FE53/FEB5); offset getter 0x7E66CE6E (← FCS_MOVIE 0x7E5E85A0) |

## 15b-169 (sections/15b-camera-core-index.md, line 169)

- *ems2 callback* (0x7E670FB8, 0x7E671208, 0x7E67132B, 0x7E671506, 0x7E671683, 0x7E671E92, 0x7E6725C6, 0x7E67287A): `movm`, 0 callers, a result decoder 0x7E460DB8/0x7E460FC2/0x7E46118C, then a direct call to the next start.

## 15b-170 (sections/15b-camera-core-index.md, line 170)

- *debug logger* (0x7E66827C, 0x7E66C6C3, 0x7E66D60D, 0x7E6727BC): prints `datsz:` and calls 0x7E66723C.

## 15b-216 (sections/15b-camera-core-index.md, line 216)

| 0x7E52FE8C | — (start; fw_kind from 0x7E530524: P→2, Q→4, S→1) | 7 | 0x6610 (protocol type unknown) |

## 15b-244 (sections/15b-camera-core-index.md, line 244)

- **Channels (V):** 4 and 13 = battery/power, 15 = ccd_temp, 34 = per_acc accelerometer (its I²C check `ACC:I2C NG?`), 38 = MEC layer 0x7E5175C9. Channels 21, 22, 39 and 41 have no user found. ADC-key callers 0x7E50B1B4…0x7E50B877 set callback F002 0x7E50B724.

