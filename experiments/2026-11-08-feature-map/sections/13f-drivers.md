# 13f — Drivers: MMIO map, interrupts, serial buses, storage stack, power and clocks

Round D1 deep dive. Scope: the driver code in 0x7E421020–0x7E521020, plus the drivers that sit in other modules (camera core, display, audio, files, USB, GPU).
- **Labels:** **V** = verified (read in the code or bytes). **I** = inferred (names, order, layout).
- **Database:** `$S/map-test`. Scripts are in `$S/d1/drivers/`:
  - `scanio.py` collects every I/O-range constant from functions.txt into `io.tsv` (13,533 rows);
  - `grp.py` and `blk.py` group the constants into blocks and list the users;
  - `dataio.py` finds MMIO pointer tables in the bytes;
  - `irqs.py` decodes the IRQ-attach call sites.

## 1. Area and boundaries

**Driver code in 0x7E421020–0x7E521020.** Each start is the first function that has the driver's register or string, so the boundaries are verified to within one function (V).

| Range | Contents |
|---|---|
| 0x7E421020–0x7E4262xx | Reset code. `CPU0!` init 0x7E421115. Flash read 0x7E4217E6. Early writes to 0x98D00000 at 0x7E421AFB/0x7E421B99. WDT time 0x7E425F44. Timer init/read 0x7E4262F0/0x7E4262C5. CPU1 boot 0x7E42691F, CPU1 level dispatchers 0x7E426974–0x7E426AE8 |
| 0x7E430000–0x7E44Axxx | Kernel. Level entry stubs 0x7E430020–0x7E430070, common interrupt entry 0x7E432648, services. Config data: task table 0x7E438CD0, interrupt-handler definitions 0x7E43BEA4 (CPU0) and 0x7E43DB10 (CPU1) |
| 0x7E449823–0x7E44B11E | Bus arbiter and bus measurement (`arbit`, `busmes`, `dqsdelay`), 0x98A/0x98B |
| 0x7E44AD97–0x7E44B0ED | Console UART init (0x7E44AD97 port 0, 0x7E44AE3D port 1) and getc/putc |
| 0x7E44B39C–0x7E44B637 | CPU0 level dispatchers and `irq_register` / `irq_disable` / `irq_restore` |
| 0x7E44D6EF–0x7E44D7FF | Kernel tick timers |
| 0x7E44EE0E–0x7E44EFEA | Inter-CPU reboot IRQ and the NMI flash-guard IRQ |
| 0x7E45824B–0x7E45A80B | Accelerometer `per_acc`/`acc_spi` (SIO ch3) |
| 0x7E45AAD4–0x7E45B67E | ADC `per_adc`, 0x98C00000 |
| 0x7E45CE12–0x7E45CE5B | ADCONV, 0x99800000 (only the debug dump reads it) |
| 0x7E45D120–0x7E45D9F1 | Bus-error IRQ (0x98000000). System controller 0x98E00000 (backup registers, power-on factor, RTC registers, standby). `per backup` 0x7E45D8C2 |
| 0x7E45DBB5–0x7E45E1xx | CCD temperature task |
| 0x7E45E206–0x7E45E834 | `cpudma` (no MMIO immediates found) |
| 0x7E45EA73–0x7E45EEA5 | DBGS debug support / NMI address watch, 0x99700000 |
| 0x7E45F02D–0x7E45F28A | `per` help. A 4-channel unit (IRQ 23–26) with registers at 0x9A1000F4–0x9A100100 |
| 0x7E45F2D8–0x7E46134D | EMS1 0x99E00000 and EMS2 0x99F00000 (`per_ems`) |
| 0x7E46151E–0x7E4628E2 | GIO (GPIO and pad control) 0x9A100000, external interrupts |
| 0x7E4628E2–0x7E4630E9 | HPROC deferred handler |
| 0x7E4639F4–0x7E463CD9 | PER_IN, the IRQ-attach wrappers, and the NMI handler 0x7E463CD9 |
| 0x7E463E70–0x7E46504A | I/O expander (IOE, IOEC) over SIO ch3 |
| 0x7E465583–0x7E465C77 | Soft timers MINTIMER, `per timer`, PER_PCONT |
| 0x7E466887–0x7E467117 | PWM, 0x9A500000 |
| 0x7E467130–0x7E467ABE | PER_ROTATE, RTC |
| 0x7E467D99–0x7E469BD1 | **SIO** driver |
| 0x7E469F91–0x7E46A395 | PER_SLOPE |
| 0x7E46A6FA–0x7E46B123 | SYSCLK clock/reset generator, 0x98800000 |
| 0x7E46B74D–0x7E46BA92 | Hardware timers, 0x98900000 |
| 0x7E46C0DB–0x7E46C308 | `usf`, `water`, `wdt`, PER_WDT |

- Data in this range: PER_IN records, the busmes tables 0x7E46DDC4/0x7E46DDF0, the console port table 0x7E46DEC8, and the ROM driver tables 0x7E4C5534–0x7E4C8A88 (V).
- Driver code above the C runtime:
  - CPUCONN 0x7E505A22;
  - UI/keys 0x7E508F82–0x7E50D6F0;
  - jog dial 0x7E50DAAF–0x7E50DC97 (0x9A600000);
  - MEC timing unit 0x7E50F7F2–0x7E5107D9 (0x9A300000) and the `mec` shell 0x7E510A60.

**Drivers elsewhere** (V for the register users; the module name is I where noted):
- lens controller 0x7E5324B3–0x7E5335BC (0x9A400000);
- strobe 0x7E5DB655–0x7E5DBFDE (0x9A200000);
- SD host 0x7E5CBDB6–0x7E5CE932 (0x99000000);
- camera-core units 0x7E629854–0x7E656640;
- face detector 0x7E6F8077–0x7E6F81F0 (0x99600000);
- display 0x7E6B26E7–0x7E6B990E (0x9A900000);
- CIC 0x7E8F5800–0x7E8F5CB8 (0x9A000000);
- audio interface 0x7E961D99–0x7E962F01 (0x9A800000);
- OSD 0x7ECCD276–0x7ECCDDED (0x9AA00000);
- image engine 0x7E54DA7F–0x7E55776E and 0x7EEC684A–0x7EECC642 (0x99400000);
- GPU 0x7EE02D0C and 0x7F0A41B9 (0x9AB00000);
- TXC 0x7F0A4470–0x7F0A48BC (0x9AC00000);
- USB device 0x7F098C43–0x7F09CB95 (0x98F00000).

## 2. Components

### 2.1 MMIO register map

**What counts as MMIO:** constants that code loads or stores, between 0x98000000 and 0x9AFFFFFF.
- Not MMIO (V): 0x9A0001xx–0x9A000Exx and 0xAB0xxxxx in the AVPI code are status codes, and 0x9999999A is the double 0.1.
- 0x8FF00000–0x8FF000B4 is kernel shared data: the per-CPU control blocks at +4+cpu·4, and the console port byte +0x80.

**Name source.** The `busmes` agent list (strings of 0x7E44A595) names the SoC bus masters: MEC2 FSC CACH0/1 SSG PRO AE AF VSC FMI USB SMCF SD EMS1 IMG_TCPL IMG_YC1/2 CDU_M/Y/C TS IMG_RW2/RW3/FNR/R4/W4/R1/W1/JRA OSD CIC FD EMS2 GPU TXC (V).

| Block | Name / function | Evidence | IRQs | Driver functions |
|---|---|---|---|---|
| 0x98000000 | Address-decoder bus error ("ADDEC") | `[SYS WANA] ADDEC ERROR Hassei!` (Japanese "occurred") plus an address/RW/data dump in handler 0x7E45D164 (V) | 0 | init 0x7E45D120 |
| 0x98100000, 0x98100400 | Two identical small units. Regs +0, +8, +10, +44, +48. **Not identified** | Toggled bit 0x10 in the SRAM standby code. Also used by 0x7E95EFC8 (`aud_tool_ac3`) and 0x7EEC6822 (V) | – | – |
| 0x98200000, 0x98300000, 0x98400000, 0x98500000, 0x98600000, 0x98700000 | **SIO / UART channels**, logical ch 0, 1, 4, 2, 3, 5 (see 2.3) | ROM table 0x7E4C7F48 (V) | 77–90 | 0x7E467D99–0x7E469BD1 |
| 0x98800000 | **SYSCLK** clock/reset generator | `[SYSCLK]mntr` strings. Gate set 0xD0/0xD4, gate clear 0xDC/0xE0 (V) | – | 0x7E46A6FA–0x7E46B123 |
| 0x98900000 | **Timers**, 10 channels | Table 0x7E4C89D4 (V) | 69–76 | 0x7E46B74D–0x7E46BA92 |
| 0x98A00000, 0x98B00000 | SDRAM controller, arbiter and bus monitor | `Arbitration Config Reg`, `LLF_PRIORITY*`, `DQS Delay` (V) | – | 0x7E449823–0x7E44B11E |
| 0x98C00000 | ADC (`per_adc`) | Strings (V) | 117 | 0x7E45AB01–0x7E45B49D |
| 0x98D00000 | Early boot setup (address/mask writes). Purpose unknown | 0x7E421B99 writes 0x98D000F0–0x10C (V) | – | 0x7E421AFB, 0x7E421B99 |
| 0x98E00000 | **System controller**, always-on domain | See 2.6 (V) | 120, 121 | 0x7E45D1F3–0x7E45D9F1, 0x7E425F44 |
| 0x98F00000 | **USB device** core and DMA | `USB_CSR_REG`, `EP0_FIFO`, `usb_dma_in_set` (V) | 91, 92 | 0x7F098C43, 0x7F09AE11–0x7F09CB95 |
| 0x99000000 | **SD card host** (agent SD) | `SDERR cmd`, `CBSY`, register dump `IRQ02_STATUS … MIC_CONFIG0` (V) | 93, 95 | 0x7E5CBD83–0x7E5CC42F |
| 0x99100000 | Display helper (swivel debug) | 0x7E6B31CC only (V) | – | – |
| 0x99200000 / 0x99300000 | **Interrupt controller** of CPU0 / CPU1, plus inter-CPU doorbells | See 2.2 (V) | – | 0x7E44B57F… |
| 0x99400000 (+0x99500000) | Image engine, used by IMG and by the AVPI scaler (AvSca) | Users 0x7E54DA7F/0x7E5574F7 (IMG buffer code), 0x7EEC6D26 (V). The identity (resize/JPEG/YC) is I | 101, 104, 109 | ISRs 0x7EECC621/0x7EECC642/0x7EECC600 |
| 0x99600000 | Face detector (agent FD) | Used only by 0x7E6F8077–0x7E6F81F0 in the FACE task area (V) | 110 | 0x7E6FC745 (the caller passes the handler) |
| 0x99700000 | DBGS debug support (NMI address watch) | `SHOW DBGS SETTING`, `[ADDRESS SETTING]` (V) | – | 0x7E45EA87–0x7E45ED2A |
| 0x99800000 | ADCONV | `[ADC_REG]0x99800000`, ANCTR/IRQMSK/IRQCLR (V) | – | 0x7E45CE5B |
| 0x99900000 | Camera-core unit: 3 buffer channels, 197 registers. **Identity open** (the candidates are agents SSG, PRO or FSC) | 92 accesses, all in 0x7E653AB1–0x7E65663A. Followed by the `SH_RES`/`SH_MEM` objects (V) | 4, 5, 6, 7 | init 0x7E653AB1, ISRs 0x7E655548/C6/644, 0x7E65628B |
| 0x99A00000 | Camera-core unit (before `cam_sem.c`) | 0x7E64DBDB–0x7E64EF47 (V) | 11 | ISR 0x7E64EF47 |
| 0x99B00000 | AE statistics (agent AE) | `AE_SEM` (V) | 8, 9 | ISR 0x7E629EDF |
| 0x99C00000 | AF evaluation (agent AF) | `CAMAFD`, `AFDRV` (V) | 12 | ISR 0x7E62A9D3 |
| 0x99D00000 | `SPRDRV` unit, 3 sub-blocks at +0x000/+0x100/+0x200 | String `SPRDRV` (V); meaning unknown | 10 | ISR 0x7E64B455 |
| 0x99E00000 / 0x99F00000 | EMS1 / EMS2 motion-estimation units | `per_ems`; `mdet_ems2` (motion detection) users 0x7E670D5D… (V names; role I) | 98 / 99 | ISRs 0x7E45FB1F / 0x7E4608F9 |
| 0x9A000000 | CIC compositor (agent CIC), used by playback EFFECT | `CIC_MUTEX`/`CIC_END`, users 0x7E8F59AF… (V) | 100 | ISR 0x7E8F590F |
| 0x9A100000 | **GIO**: GPIO ports, pad/function registers | 275-entry pin table 0x7E4C6014 (V) | 17, 27–40 | 0x7E46151E–0x7E4628E2 |
| 0x9A200000 | Strobe (flash) controller | `STB_REG_FLS_ARST/SRST/CAUSE…` (V) | 1 | 0x7E5DB655–0x7E5DBFDE |
| 0x9A300000 | **MEC** timing unit, 2 channels (`ch_1/ch_2 reset/start/abort`) | Callers in the `mec` code 0x7E51339A, 0x7E514434, 0x7E5167EC (V) | 2 | 0x7E50F7F2–0x7E5107D9 |
| 0x9A400000 | Lens interface controller | Users only in the lens module (V); protocol I | 3 | 0x7E5324B3–0x7E5335BC |
| 0x9A500000 | PWM (LED, backlight) | `PWM_IICWAIT`, table 0x7E4C794C (V) | 118 | 0x7E466887–0x7E46702D |
| 0x9A600000 | Jog-dial counters, 4 channels in 2 pairs (+0x00/+0x80) | C1 F004 (V) | 119 | 0x7E50DAAF–0x7E50DC97 |
| 0x9A800000 | Audio serial interface | `[ERR]ao_intr` (V) | 13 | 0x7E9623C8…, ISR 0x7E962BC6 |
| 0x9A900000 | Display controller (VSC, I) | Users 0x7E6B75C2–0x7E6B990E (V) | 14, 15 | ISR 0x7E6B749A |
| 0x9AA00000 | OSD | `[OSD_DRV] osd_drv_iocontrol()` (V) | 111 | ISR 0x7ECCD638 |
| 0x9AB00000 | GPU (DMP GL / C3D) | GL code 0x7EE02D0C, C3D 0x7F0A41B9 (V) | 112–114 | attach 0x7F0A3723 |
| 0x9AC00000 | TXC (agent TXC), used by C3D | `E_TXC_EXEC_IRQ_WAIT` (V) | 116 | ISR 0x7F0A48BC |

- **CPU-internal registers** (16-bit absolute addresses):
  - (0x8050) = CPU number, with 843 readers (V);
  - 0x8000–0x801C = level vector registers, written at reset (2.2, V);
  - 0x8928 = group-10 level;
  - 0x8940–0x8958 = per-level acknowledge (V for the writes, I for the meaning);
  - 0x8A00 = accepted-interrupt code (V read).
- **Cross-body check:**
  - The agent list is identical in the E-P5 (`map-108_1800`): same SoC (V).
  - The E-M10, E-M5 II and PEN-F list a different set (FSCMEC2, CWD1–6, CODER0/1, ISP, GPU1–3 …): a new SoC generation (V strings).
  - The E-PL5 has byte-identical SIO, timer and GIO tables, and the same IRQ numbers, 8 bytes lower (V).

### 2.2 Interrupt handling

- **CPU level vectors.** The reset code 0x7E421020 writes the 16-bit vector registers 0x8000–0x801C. Their values are 0x7E430020 (level 0) and 0x7E430048, 50, 58, 60, 68, 70 (levels 1–6) (V).
  - The level-0 stub saves two stack words to 0x7E401208/0C.
  - All the stubs jump to the kernel's common entry 0x7E432648.
- **Common entry 0x7E432648** (V):
  1. It gets the per-CPU kernel block from (0x8FF00004 + cpu·4).
  2. It increments the nest count at +28. On the first level it switches to the interrupt stack (+112/+116).
  3. It takes the level from PSW bits 8–10 and calls `handler[level]` from the table at block+88.
  4. On exit it runs the dispatcher 0x7E431A93.
- **Level handlers** come from static `{intno, attr, handler}` records (uITRON DEF_INH style) (V):
  - CPU0 at 0x7E43BEA4: level 6 → 0x7E44B39C, then 5, 4, 3, 2, 1 → 0x7E44B3DA, 418, 456, 494, 4D2; level 0 → 0x7E44B510.
  - CPU1 at 0x7E43DB10: level 6 → 0x7E426974 … level 0 → 0x7E426AE8.
- **Level dispatcher pattern** (seven copies per CPU, 62 bytes each) (V):
  - `call 0x7E44B54E`: if (0x8A00)>>2 = 10, it runs the hook at (0xA074B034) and skips. The hook is set by 0x7E463CAE.
  - Then it loops on `v = (0x99200200 + 4·level)`: `irq = (v>>2) − 1`, `call table[irq]`.
  - It ends with `movhu 0x0101|level<<12,(0x8940+4·level)`.
  - The handler table is RAM 0x6032E79C on CPU0 and 0x60729040 on CPU1.
- **Registration** (V):
  - `irq_register(d0=irq<125, a0=&{level, handler})` 0x7E44B57F. It picks ICU 0x99200000 or 0x99300000 by (0x8050). It writes 0 to `ICU+4·irq`, stores the handler, then writes `1<<min(level,6)` to that register. A shadow copy goes to 0xA0734328 + cpu·500. An irq ≥ 125 prints `!!Wrong IRQ Number`.
  - `irq_disable(irq)` 0x7E44B5E7 writes 0. `irq_restore(irq)` 0x7E44B60A writes the shadow value back.
  - The drivers call **`irq_attach(d0=irq, d1=level, a0=handler)`** 0x7E463C8E (38 callers), or its byte-identical twin 0x7E463C9E (5 callers, all CPU1-side code: e.g. 0x7E45D120 calls 0x7E463C8E when (0x8050) = 0 and 0x7E463C9E otherwise). `irq_detach(irq)` is 0x7E463CC8.
  - So an ICU register (+0..+0x1F0) is a one-hot level mask, and 0 means disabled.
- **ICU registers above the per-IRQ array** (V for the use, I for the names):
  - +0x200…+0x218: per-level pending vector.
  - +0x308: inter-CPU doorbell status (bit 0, bit 1). +0x30C: acknowledge. CPUCONN ISRs 0x7E505F30 (CPU1 side) and 0x7E505FA0 (CPU0 side), IRQ 123.
  - +0x310/+0x314: raise the doorbell on the other core (written by 0x7E43008C and by the NMI-guard code).
  - +0x1F0: written at boot by each CPU.

**IRQ table** (V for the number, level and handler; the device names follow 2.1):

| IRQ | Lvl | Handler | Device | IRQ | Lvl | Handler | Device |
|---|---|---|---|---|---|---|---|
| 0 | 0 | 7E45D164 | ADDEC bus error (each CPU attaches its own) | 69–76 | 5 | 7E46BA37+13·k | timer ch1–8 (ch1 = CPU0 1 ms tick 7E44D74E; ch2 = 2nd tick 7E44D7B8) |
| 1 | 0 | 7E5DBFDE | strobe | 77–90 | 5 | 7E468BE9… | SIO (2.3) |
| 2 | var | 7E50F9C3 | MEC timing | 91 / 92 | 5 | 7F09C51B / 7F09C2E6 | USB DMA end / USB core |
| 3 | var | 7E532713 | lens controller | 93 / 95 | 3 | 7E5CC3A4 / 7E5CC069 | SD host / SD error |
| 4–6 | 2 | 7E655548/5C6/644 | 0x999 unit ch0–2 | 98 / 99 | 5 | 7E45FB1F / 7E4608F9 | EMS1 / EMS2 |
| 7 | 2 | 7E65628B | 0x999 unit | 100 | 5 | 7E8F590F | CIC |
| 8, 9 | 1 | 7E629EDF | AE | 101, 104, 109 | 5 | 7EECC621/642/600 | image engine (CPU1) |
| 10 | 1 | 7E64B455 | SPRDRV | 102, 105–108 | 5 | 7E545269, 7E5451CB/1EB/20B/23A | image engine (IMG) |
| 11 | 2 | 7E64EF47 | 0x99A unit | 110 | 5 | from caller | face detector |
| 12 | 1 | 7E62A9D3 | AF | 111 | 5 | 7ECCD638 | OSD |
| 13 | 3 | 7E962BC6 | audio interface | 112–114 | 5 | from caller | GPU |
| 14, 15 | 5 | 7E6B749A | display | 116 | 5 | 7F0A48BC | TXC |
| 17 | var | 7E4627AA | GIO port interrupt (8 groups, table 0x7E4C6A40) | 117 | 1 or 5 | 7E45B49D | ADC |
| 23–26 | 5, 3, 2, 1 | 7E45F242/25A/272/28A | 4-ch unit at 0x9A1000F4 | 118 / 119 | 5 | 7E46702D / 7E50DC97 | PWM / jog dial |
| 27–40 | var | 7E461C74–7E461D29 | GIO external pins (table 0x7E4C631C) | 120 / 121 | 5 | 7E45D5C7 / 7E45D609 | system controller |
| 122 | 6 | 7E44EE39 | `CPU1 Yo-in De Reboot` ("reboot because of CPU1") | 123 / 124 | 0 / 6 | 7E505F30, 7E505FA0 / 7E44EFBD, 7E44EFEA | CPUCONN doorbell / NMI flash-guard request |

- **Pattern of an interrupt handler (ISR)** (V):
  1. Read the status register, AND it with the mask, and write it back to clear it.
  2. Then either call a per-bit `{fn, u8 arg}` callback table (0x99900000: ROM 0x7E7BB654 and RAM 0x6056EA24), or signal the kernel. The kernel calls are `iset_flg` 0x7E431D20 and `isig_sem` 0x7E431E1F (I from the caller names).
- **Channel stubs.** A one-line stub per channel (12–13 bytes): `f8 fe fc  80 <ch>  cd <rel16> <regs> <n>  df 00 04` = `add -4,sp; mov ch,d0; call common; ret`. Examples: SIO 0x7E468BE9–0x7E468CDC → 0x7E468CE9, and the timers 0x7E46BA37…
- Some ISRs start with `movm` (0x7E655548), others with `add -4,sp` (0x7EECC600).

**Correction to the brief.** The words at block offset 0x4CDD0 (0x7E46DDF0) are **not the interrupt vectors** (V):
- they are 10 pointers to the `busmes through` handler 0x7E44ACB0 (`start:throug`, a 3 s alarm, then `stop :throug`), followed by 16 `{mask, 0x7E44ACB0}` pairs;
- no immediate reference to them was found;
- the preceding table 0x7E46DDC4 is the `busmes slide 1..11` jump table, used at 0x7E44A876.

### 2.3 SIO, the I/O expander, the accessory bus and the sub-CPU links

**SIO hardware table** 0x7E4C7F48: 6 logical channels × 96 bytes of register pointers (V).

| Logical ch | Block | IRQs | Clients (V: the `sio_request` d0 value) |
|---|---|---|---|
| 0 | 0x98200000 | 77, 78 | — (opened only) |
| 1 | 0x98300000 | 79, 80 | **console port 1**, EVF driver 0x7E6B361A (`[Display] Evf Driver`), Bluetooth/PENPAL 0x7E91369B (`bt_sio`) |
| 2 | 0x98500000 (+0x80–0x94) | 81, 82, 83 | audio codec 0x7E94EFB4 and HDMI 0x7E6BA554 (switched by `SIOIIC_SEL > audio/HDMI` through GIO 0x9A100824/864), touch panel 0x7E6BDCD5, display VSC 0x7E6B5917, 0x7E8FC39A |
| 3 | 0x98600000 (+0x80–0x94) | 84, 85, 86 | **I/O expander** 0x7E463ED7/0x7E464138, accelerometer 0x7E45A76E, HDMI 0x7E6BA578, touch 0x7E6BC6E5 |
| 4 | 0x98400000 | 89, 90 | lens 0x7E533978, **BC stabiliser MCU** 0x7E53F156, LCD panel 0x7E6B1126 |
| 5 | 0x98700000 | 87, 88 | **console port 0** (S_SHELL) |

- **Driver layers** (V for the flow, I for the names):
  - **Open and configure** 0x7E467EED (C1 F002). Interrupt attach 0x7E467E1A, from the IRQ tables 0x7E4C8188, 0x7E4C8218 and 0x7E4C8260. Per-channel mode hooks are in table 0x7E4C82F0.
  - **Bus ownership** `sio_request(ch, fn a0, arg a1)` 0x7E469961 (19 callers). If the channel is idle it marks it busy and calls `fn(arg)` at once (returns 0). Otherwise it queues one of 2 slots (returns 2) or refuses (returns 1).
  - `sio_release(ch)` 0x7E4699F9 (21 callers) masks the channel IRQs (0x7E468B97) and runs the next queued `fn`. The state lives at RAM 0x60419F00 + ch·20.
  - The client callback does the transfer. `<<SIO SEM STATUS>>` 0x7E469A9A prints FLAG/Q_READ/Q_WRITE/FUNC/OPEN/CLOSE.
  - Open/close counters: 0x7E469C27 / 0x7E469CDF.
  - **UART (console) mode**:
    - 0x7E46967C attaches IRQs 79/80 (ch1) and 87/88 (ch5) from tables 0x7E4C81D0/0x7E4C82A8.
    - Each port has a 5,152-byte block at 0x6041A6BC: a 1,024-byte TX ring and a 4,096-byte RX ring.
    - `uart_getc` 0x7E46974E, `uart_write(ch,buf,len)` 0x7E4697DD (it sets bit 0x81 in register +0x28 to enable TX), `uart_flush` 0x7E46988A (polls with `dly_tsk(1)`).
    - The direct-polling console getc/putc 0x7E44B040/0x7E44B051 use the 0x7E46DEC8 pointers (10f).
- **The accessory port shares the console's second UART** (I, from the channel numbers). The EVF and PENPAL/Bluetooth drivers both use logical ch1 = 0x98300000, the S_SHELL port selected when (0x8FF00080) = 1 (10f).
- **I/O expander (PER_IOE_CTRL).**
  - The register sequencer 0x7E463ED7 (69 callers; `[IOE]PER_IOE SEQUENTIAL ERR`) and the GIOSEQ read/write 0x7E464050 run on SIO ch3.
  - The accessory-ID scan 0x7E464850 (10e) probes 4 bus/address pairs and maps the chip ID through 0x7E4C726C.
  - The UI side reads cached status bits through `0x7E509CA3(id)` → 0x7E50B0A8. Status group 11 holds the "edev" bits (10e). The UI_IN task fills the cache (section 01).
- **Sub-CPU links.**
  - The BC (H8 stabiliser MCU) shares SIO ch4 with the lens and the LCD panel (V). It also uses `RST/CS/RDY/RQ/TRG` handshake lines (strings, 08).
  - PER_SCPU_POLLING is empty (V, 08).
  - The **second core** is reached through the ICU doorbells (2.2) and the CPUCONN proxy, not over SIO (V).

### 2.4 Storage stack

From the top down. Positions are verified string anchors; the layer roles are I unless marked.

| Layer | Where | Notes |
|---|---|---|
| App/DCF API (`dcf*`, `fileif_*`) | DCF 0x7E5AD055–~0x7E5B5xxx (`DCF_SEM_SM`, `DCFPROC_*`, `%c:\DCIM\%s\%s`); DPOF 0x7E5BEEAE–0x7E5C0903 (`AUTPRINTMRK`); AVCHD paths 0x7E5C1164 | The `fileif_*` names occur only in the `filedbg` test strings 0x7E5C60F8–0x7E5C64AA |
| FILECLBK task 0x7E5C1B4E | — | Dispatches on the high 16 bits of the command (V): 0 → 0x7E5C1BC6; 0x1 → 0x7E5C50DE; 0x2 → 0x7E5C51A8; 0x20 → 0x7E5C0A7B; 0x8/0x10 → DCF 0x7E5AFAA0. Then it replies (0x7E5C1C84) |
| FILEFGND task 0x7E5C4E90 | — | A generic job runner (V). It waits on queue (0x7E43EB7E) and drains a 32-entry ring of 12-byte `{fn, arg, u16 d0, u16 kind}` jobs at 0x60545454: kind 0 `fn()`, 1 `fn(a0)`, 2 `fn(a0,d0)`. Jobs are posted by 0x7E5C4E2C/37/42. Job thunks 0x7E5C4EBC… unpack `{ret, a0, d0, d1, a1}` and call the file-wrapper layer |
| File wrapper / VFS | 0x7E5C920F–0x7E5CB8D2 (`filewrap_dump_all_file_list_item`, `.`/`..` listings) | Job targets 0x7E5C97C1, 0x7E5C9A5F, 0x7E5C9DCC, 0x7E5CA326… (V call targets) |
| FAT | 0x7E5B6233 (`NO_FAT_CHAIN`, 26 callers) – ~0x7E5BDE10 (cluster-cache MRU, C1 F008); type detect 0x7E5B79F4/0x7E5B88F0 (`FAT12/16/32`, `NO NAME`); **exFAT** 0x7E5BA075; DOS date/time 0x7E5C0C76 | Shell `FileSystem Debug Command` 0x7E5C213E. The U_SHELL `file` entry 0x7E5C2139 is the stub just before it |
| Logical-sector layer ("logsec") | 0x7E5CBAA1–0x7E5CBC15 | `LOGSEC_SEM`, ticket semaphores `E_LOGSEC_TCKT2/3` (serialises the card users) |
| SD host driver | 0x7E5CBD83 (init: IRQ 93 → 0x7E5CC3A4, IRQ 95 → 0x7E5CC069) – 0x7E5CE932 (`==== sdphy ====`); register dump 0x7E5CC42F | Block 0x99000000, with a second register bank at +0x2000 (V). Pad set-up through GIO 0x9A101384–0x9A101464 (0x7E5CC87C/0x7E5CC8D6, V). Eye-Fi/FlashAir (iSDIO) commands are layered above (`isdio_read_register` 0x7F0A4AF4) |

### 2.5 Clocks and timers

- **SYSCLK** (V):
  - `clk_gate(id 0–48 or 255 = all, on)` 0x7E46A6FA is reference-counted (counts at 0x60419F00 + 4·id). On: it writes `1<<id` to 0x988000D0 (ids < 32) or `1<<(id−32)` to 0x988000D4. Off: 0x988000DC / 0x988000E0.
  - Twin functions 0x7E46A8DE (0xD4/0xD8) and 0x7E46AA3A (0xE0/0xE4) follow the same shape; that they are reset assert/release is I.
  - `clk_rate(id 0–22)` 0x7E46AB96 uses jump table 0x7E4C8848. The bases are 24 MHz and 32,768 Hz, scaled by the PLL/divider registers 0x98800004–0x98800060.
  - Example: 0x7E46A84B(0,3,1) powers the jog unit (C1).
- **Timers 0x98900000** (V):
  - Per channel n: control +4n (bit 0x40 = load, bit 0x80 = run, with 5 `nop`s between), reload +0x28+4n, count +0x50+4n. IRQ enable at +0x78 and acknowledge at +0x7C (bit n−1).
  - **ch0** is the prescaler: `clk_rate(0)/1,000,000 − 1`, and 161 is written at boot. So timer ticks are 1 µs and clock 0 is 162 MHz (I).
  - **ch9** runs free: reload 0x3FFFFFFF. `now_us()` 0x7E4262CD = 0x3FFFFFFF − (0x98900074).
  - **ch1** = 1 ms system tick (reload 999, IRQ 69, ISR 0x7E44D74E → kernel tick 0x7E431EF8). ch2 is a second 1 ms tick (IRQ 70), the CPU1 tick (I).
  - ch1–8 are available to drivers through 0x7E46B74D (attach) and 0x7E46B7EA (start).

### 2.6 Power, standby and watchdog (system controller 0x98E00000)

- **Watchdog** (V):
  - `wdt_set_time(s)` 0x7E425F44: it waits for +0xA4 to read 0, writes the low 6 bits of +0x8C, then writes commit `0x20041001` to +0xA4.
  - **The kick** is SRAM code 0x47001560 → 0x470011CE (image at 0x7F14B1CE). CPU0 writes the magic 0x19191012 to +0x90, CPU1 writes 0x19450815 to +0x94, then it commits to +0xA4.
  - PER_WDT 0x7E46C29B kicks when the flag 0x6041A464 is set. It then waits on its queue with a 3000 ms timeout.
  - Commands: 0 off (0x7E46C258), 1 on = 10 s (0x7E46C246), 2 = set time (0x7E46C20C).
- **Other system-controller registers** (V users; the names are I):
  - +0x04 = power-on factor (0x7E45D866/7B, read at boot by 0x7E44EE9A).
  - +0x58–+0x68 = five backup registers. They are written by 0x7E45D444 (callers in UI keys, USR_FAST, firmup) and match `per backup` PKEY0–4.
  - +0x6C/+0x74 and +0x7C/+0x84 = RTC (the RTC driver 0x7E467D5A/78 calls 0x7E45D4E1/0x7E45D526).
  - +0x98/+0x9C/+0x50 are read by the SRAM code.
  - IRQs 120/121 → ISRs 0x7E45D5C7/0x7E45D609.
  - **Standby/power-off** 0x7E45D390 is called by `pwr` 0x7E539672, `pwr_standby` 0x7E539EA4 and the firmup end 0x7E880DCD.
- **SRAM low-power code** (2 KiB at 0x47001000, copied from 0x7F14B000 by the boot task). Besides the kick, it touches (V register list; purpose I = it runs while SDRAM is in self-refresh):
  - SDRAM controller 0x98B0001C/0x98B00818/0x98B0009C–A4;
  - SYSCLK 0x9880000C/50/E8/F4–FC (clock switch);
  - PWM 0x9A500028/2C;
  - GIO pads 0x9A100640–0x9A100FD0;
  - the 0x98100000 units;
  - jog counters 0x9A600008/88;
  - ADDEC 0x98000018.

## 3. Recurring patterns (how to classify a driver function by its bytes)

1. **IRQ attach site:** `80 NN 85 LL fc dc <handler32> dd <rel32> 00 0c` = `mov irq,d0; mov lvl,d1; mov handler,a0; call 0x7E463C8E,[],12`. The handler exists only as that imm32, so it is an "imm" start in map-test (e.g. 0x7E653ACF → 0x7E655548).
2. **Per-channel ISR stub:** `f8 fe fc 80 <ch> cd …  df 00 04`, followed by a shared body that indexes a 12- or 20-byte channel record.
3. **Register-pointer tables** (no MMIO immediates in the code):
   - SIO: 24 words/ch at 0x7E4C7F48;
   - timer: 3 words/ch at 0x7E4C89D4;
   - GIO external interrupts: `{pin, cfg reg, irq, isr}` × 14 at 0x7E4C631C;
   - GIO groups: `{reg, irq 17, isr}` at 0x7E4C6A40;
   - PWM: 0x7E4C794C;
   - EMS: 0x7E4C56DC.

   A function that does `udfu01 <stride>,dN; add <table>,dN; mov (dN),aN; mov (aN),…` belongs to that driver.
4. **Lock bracket:** `call 0x7E44B36F` … `call 0x7E44B390` around a register read-modify-write = CPU lock/unlock (I: `loc_cpu`/`unl_cpu`); 0x7E44B36F is called with d0 = 1.
5. **Debug shells.** Each driver has a `per <name>` handler (table 0x7E4C5534) with help strings `-- xxx help --`. The handler pointers in the table are the best anchors for driver boundaries.
6. **Event wrappers:** `PerWEFm`/`PerSEFm`/`PerCEFm` (wait/set/clear event flag) are short functions repeated per driver (0x7E464E9D, 0x7E5CCA5C …).

## 4. Corrections

1. **Vector table (brief):** 0x7E46DDF0 is the `busmes` table, not interrupt vectors. The real path is: vector registers 0x8000–0x801C → stubs 0x7E430020–0x7E430070 → entry 0x7E432648 → the DEF_INH level handlers → `ICU+0x200+4·level` → the RAM handler table (V).
2. **Section 01, console:** the CPU0/CPU1 register reading was already corrected by 10f. The two ports are SIO logical ch5 (0x9870) and ch1 (0x9830), and ch1 is also the EVF/PENPAL UART (V for the table and the client channels).
3. **C1 F015 (0x99900000 = shutter timing, I):** this reading is weakened. The mechanical timing unit used by the `mec` code is **0x9A300000** (2 channels, IRQ 2). 0x99900000 is a camera-core unit with 3 buffer channels (IRQs 4–7) whose name is still open.
4. **Section 08 says the eye sensor is "PER_EYE_SENSOR task over IIC".** The task is an empty `retf` (V, section 01), so no driver activity comes from it.
5. **Firmware map, "Codec WM8946 shares a serial bus with the HDMI chip":** confirmed, and more: SIO ch2 also carries the touch panel and the display VSC, with a GIO mux (V).
6. **Firmware map, region 0x7E421020–0x7E4A0000:** the drivers proper are 0x7E45824B–0x7E46C308. The kernel is 0x7E426xxx–0x7E44Axxx. The ROM driver tables are 0x7E4C5534–0x7E4C8A88 (V).

## 5. Open questions

1. The names of 0x98100000, 0x98D00000, 0x99900000, 0x99A00000, 0x99D00000 (SPRDRV) and the 4-channel unit at 0x9A1000F4 (IRQs 23–26). The agent names SSG, PRO, FSC, MEC2, CDU, TS and IMG_* are not yet matched to register blocks.
2. Missing IRQ numbers (16, 18–22, 41–68, 94, 96, 97, 103, 115): unused, or attached through paths not decoded here. Search for `irq_register` callers with computed d0.
3. The meaning of the 0x8A00 code 10 hook (0xA074B034) and of the 0x8940+ acknowledge write.
4. Whether the accessory UART really is console port 1 on the board (it would make S_SHELL reachable from the accessory port).
5. The SD host register names (the `IRQ02_*`/`MIC_CONFIG*` dump 0x7E5CC42F lists them) and the logsec ticket protocol.
6. `cpudma` (0x7E45E206–0x7E45E834) has no MMIO immediates; its hardware is not found.
