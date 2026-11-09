# Audit batch 13-3

## 13e-12 (sections/13e-mcon-sequencers.md, line 12)

| TAKE_MAIN sequencer engine | 0x7E58204D–0x7E582602 | state table 0x7E790860 (27 × 20 B), names 0x7E790758 | V |

## 13e-15 (sections/13e-mcon-sequencers.md, line 15)

| Light-source selection (strobe assist) | 0x7E5E2258–0x7E5E2418 (+ 0x7E5E1B11, 0x7E5DEBAD) | – | V |

## 13e-132 (sections/13e-mcon-sequencers.md, line 132)

- **The 27 states** of 0x7E790860 `{u32 id, ptr name, ptr entry, ptr A, ptr B}`, with the sends verified at the given addresses. Command names use the corrected numbering of §4.2.

## 13e-161 (sections/13e-mcon-sequencers.md, line 161)

- **Flash selection 0x7E5D1659** (`check_select`; inputs onoff, ae_chg, mode_stb_expose, general, rc_mode, after_movie) (V):

## 13e-236 (sections/13e-mcon-sequencers.md, line 236)

1. **Section 05 §5:** "SERV_S1 … called through 0x7E68CCBD from the REC (0x7E701D27)" is **wrong** (V).

## 13e-249 (sections/13e-mcon-sequencers.md, line 249)

4. **Section 10a:** the 60-byte records are per-setting operation records. The cited hooks (0x7E7039C4, 0x7E703986, 0x7E703540) are their **+24** post-write hooks (V).

## 13f-81 (sections/13f-drivers.md, line 81)

| 0x98100000, 0x98100400 | Two identical small units. Regs +0, +8, +10, +44, +48. **Not identified** | Toggled bit 0x10 in the SRAM standby code. Also used by 0x7E95EFC8 (`aud_tool_ac3`) and 0x7EEC6822 (V) | – | – |

## 13f-82 (sections/13f-drivers.md, line 82)

| 0x98200000, 0x98300000, 0x98400000, 0x98500000, 0x98600000, 0x98700000 | **SIO / UART channels**, logical ch 0, 1, 4, 2, 3, 5 (see 2.3) | ROM table 0x7E4C7F48 (V) | 77–90 | 0x7E467D99–0x7E469BD1 |

## 13f-88 (sections/13f-drivers.md, line 88)

| 0x98E00000 | **System controller**, always-on domain | See 2.6 (V) | 120, 121 | 0x7E45D1F3–0x7E45D9F1, 0x7E425F44 |

## 13f-90 (sections/13f-drivers.md, line 90)

| 0x99000000 | **SD card host** (agent SD) | `SDERR cmd`, `CBSY`, register dump `IRQ02_STATUS … MIC_CONFIG0` (V) | 93, 95 | 0x7E5CBD83–0x7E5CC42F |

## 13f-95 (sections/13f-drivers.md, line 95)

| 0x99700000 | DBGS debug support (NMI address watch) | `SHOW DBGS SETTING`, `[ADDRESS SETTING]` (V) | – | 0x7E45EA87–0x7E45ED2A |

## 13f-105 (sections/13f-drivers.md, line 105)

| 0x9A200000 | Strobe (flash) controller | `STB_REG_FLS_ARST/SRST/CAUSE…` (V) | 1 | 0x7E5DB655–0x7E5DBFDE |

## 13f-106 (sections/13f-drivers.md, line 106)

| 0x9A300000 | **MEC** timing unit, 2 channels (`ch_1/ch_2 reset/start/abort`) | Callers in the `mec` code 0x7E51339A, 0x7E514434, 0x7E5167EC (V) | 2 | 0x7E50F7F2–0x7E5107D9 |

## 13f-230 (sections/13f-drivers.md, line 230)

| FILEFGND task 0x7E5C4E90 | — | A generic job runner (V). It waits on queue (0x7E43EB7E) and drains a 32-entry ring of 12-byte `{fn, arg, u16 d0, u16 kind}` jobs at 0x60545454: kind 0 `fn()`, 1 `fn(a0)`, 2 `fn(a0,d0)`. Jobs are posted by 0x7E5C4E2C/37/42. Job thunks 0x7E5C4EBC… unpack `{ret, a0, d0, d1, a1}` and call the file-wrapper layer |

