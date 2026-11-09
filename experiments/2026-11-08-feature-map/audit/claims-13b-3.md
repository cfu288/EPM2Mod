# Audit A5 batch 3

## 13e-132 (sections/13e-mcon-sequencers.md, line 132)

- **The 27 states** of 0x7E790860 `{u32 id, ptr name, ptr entry, ptr A, ptr B}`, with the sends verified at the given addresses. Command names use the corrected numbering of §4.2.

## 13e-161 (sections/13e-mcon-sequencers.md, line 161)

- **Flash selection 0x7E5D1659** (`check_select`; inputs onoff, ae_chg, mode_stb_expose, general, rc_mode, after_movie) (V):

## 13e-236 (sections/13e-mcon-sequencers.md, line 236)

1. **Section 05 §5:** "SERV_S1 … called through 0x7E68CCBD from the REC (0x7E701D27)" has the wrong module label: 0x7E701D27 is mcon code, not REC. The call edge itself is real: 0x7E701D27 calls 0x7E68CCBD at 0x7E701D50 (d0 = 0x03010007, d1 = 1), and 0x7E68CCBD = `call 0x7E8F91DD` (SERV_S1) (V). (A4 2026-11-09)

## 13e-249 (sections/13e-mcon-sequencers.md, line 249)

4. **Section 10a:** the 60-byte records are per-setting operation records. The cited hooks (0x7E7039C4, 0x7E703986, 0x7E703540) are their **+24** post-write hooks (V).

## 13f-81 (sections/13f-drivers.md, line 81)

| 0x98100000, 0x98100400 | Two identical small units. Regs +0, +8, +10, +44, +48. **Not identified** | Toggled bit 0x10 in the SRAM standby code. Also used by 0x7E95EFC8 (no strings; it sits just before the `aud_tool_ac3_*` functions, so the audio label is a neighbourhood guess (I); only caller 0x7E94E1FE), by its twin **0x7E95F008** (+0x444/+0x448 of the 0x98100400 unit; callers 0x7E6D80B3, 0x7E6D8900, 0x7E6E0857, 0x7E6E08F1, movie/CPU1 image-engine code) and by 0x7EEC6822 (V) | – | – (A4 2026-11-09) |

## 13f-86 (sections/13f-drivers.md, line 86)

| 0x98C00000 | ADC (`per_adc`) | Strings (V) | 117 | 0x7E45AB01–0x7E45B49D |

## 13f-97 (sections/13f-drivers.md, line 97)

| 0x99900000 | Camera-core unit: 3 buffer channels, 197 registers. **Identity open** (the candidates are agents SSG, PRO or FSC) | 92 accesses, all in 0x7E653AB1–0x7E65663A. Followed by the `SH_RES`/`SH_MEM` objects (V) | 4, 5, 6, 7 | init 0x7E653AB1, ISRs 0x7E655548/C6/644, 0x7E65628B |

## 13f-100 (sections/13f-drivers.md, line 100)

| 0x99C00000 | AF evaluation (agent AF) | `CAMAFD`, `AFDRV` (V) | 12 | ISR 0x7E62A9D3 |

## 13f-105 (sections/13f-drivers.md, line 105)

| 0x9A200000 | Strobe (flash) controller | `STB_REG_FLS_ARST/SRST/CAUSE…` (V) | 1 | 0x7E5DB655–0x7E5DBFDE |

## 13f-111 (sections/13f-drivers.md, line 111)

| 0x9A900000 | Display controller (VSC, I) | Users 0x7E6B75C2–0x7E6B990E (V) | 14, 15 | ISR 0x7E6B749A |

