# 14b. Unlabelled code between named modules: platform and camera core (E-PM2 v1.6)

Round D2 deep dive for the string-less blocks that coverage round C2 (review 1: F002–F006, F009–F011, F013, F015–F017) found without a label.

- **Labels:** (V) = read in the code or bytes; (I) = inferred from usage, names, order or layout.
- **Database:** build/map (74,554 functions). "Sites" = call sites in calls.tsv.
- **Scratch:** `$S/d2/platform/` (`dump.py LO HI` = disassembly of a function range with hex constants; `graph.py LO HI` = per-function internal/external callers and callees; `rd.py` = block-0 byte reader; `*.dis` = dumps).

## 0. Two structural findings used below

1. **The camera core is linked in alphabetical file order (V for the anchors, I for the rule).** The ten file-name anchors of modules.tsv are in ASCII order (`cam.c` < `cam_contrast.c` < `cam_damage.c` < `cam_debug_monitor.c` < `cam_ev.c` < `cam_frame.c` < `cam_frame_sync.c` < `cam_imgdev.c` < `cam_sem.c` < `cam_set.c` < `cam_still_func.c` < `cam_still_live_bulb.c` < `cam_timer.c`). E-PL7 1.4 (`$S/map-115_1400`, `cam dbglog` table at 0x7DBAA517) lists the full file set of this code family: `cam_aedrv/afdrv/aperture/bright/contrast/cpm/defect*/expcal/frame*/imgdev*/lens/list/mec_ctrl/mem/mirror/param/pfp/port/prepro/rap/serial/set/sg/shutter/stl*/strobe/timer/watchdog_timer.c` (V strings). Fitting that list into the gaps by alphabetical order gives the file names below. They agree with the object names (AE_SEM, CAMAFD, APT_*, CAMLNS, MI_*, SH_*) and with the error-code module byte (item 2).
2. **Camera error codes carry a module byte (V).** cam_damage codes are 0x0A_MM_xxxx. MM groups by address range: 0x10 cam.c (0x7E628161–0x7E628CD5), 0x18 aperture, 0x03 contrast, 0x26 cam shell, 0x2A debug monitor, **0x15 0x7E6369CA only**, **0x12 0x7E636A04–0x7E63B766** (frame + frame_sync), 0x17 imgdev, 0x25 CAMLNS, **0x28 0x7E640F3E**, **0x16 0x7E641C2E–0x7E642097**, **0x1E MI 0x7E642325**, 0x1B SPRDRV, 0x27 cam_sem, 0x1A shutter 0x7E6557CE, 0x13 still/live bulb, 0x24 cam_timer. The ids are per subsystem, not strictly per file (0x12 covers frame and frame_sync).
3. **Rodata rule (V on two cases):** in one object file, strings come in code order and `switch` jump tables come **after** all the strings. Example: imgdev's tables 0x7E7AF1E0/0x7E7AF27C (used at 0x7E63D44D/0x7E63D3F0) follow the strings of 0x7E63E4B2. This places 0x7E636AAB (jump table 0x7E7AE744, right after `cam_frame.c`/`+ pwr.client` at 0x7E7AE71F–0x7E7AE743) inside cam_frame.c.

## 1. Area and boundaries

| Range | Component | Basis |
|---|---|---|
| 0x7E506BEF–0x7E506CAD | firmware-package helpers (word sum, header getters, section parser, maker check; callers 0x7E543DDE, PTP overlay 0x7F09xxxx). Section 02 covers them | V |
| **0x7E506CB0–0x7E508DA6** | **`sc` system-common library**: `sc` shell, SC_TTIMER soft timers, `scheap` fixed-block heaps + guard checker, utility/string library, RTC/calendar library | V (strings `sc …`, `ttmr_*`, `scheap_*`; call graph) |
| 0x7E508DA7–0x7E508F81 | UI side: beep request layer 0x7E508DA7–0x7E508ED9 (last function 0x7E508EAE; callers: the UI_OUT init 0x7E50D7CD ← Usr0 0x7E503DD4, and 0x7E50D88B/0x7E50D93A ← UI_OUT task 0x7E50D858) (A6 2026-11-09), `ui` shell `beep` 0x7E508EDA and `help` 0x7E508F14 (table 0x7E734DEC: led 0x7E50D6F0, beep, key 0x7E50AD9C, jog 0x7E50996C, remo 0x7E50917F, help) | V |
| 0x7E579AB7–0x7E579C33 | still `buff`: 7 pointer-only methods of a pool object (128-id bitmap at +52), vtable 0x7E78EEBC–0x7E78EEE0 | V |
| **0x7E579C34–0x7E581FAF** | **WB (white balance / colour) module**, no file name; holds the **WB_MOV task 0x7E57F914** and IMG_PRECON's cmd 1–4 back-ends | V (task table; call graph) |
| 0x7E581FB0 → | TAKE: 0x7E581FB0 is the TAKE module init (only caller Usr0 0x7E503DD4; inits 0x7E58287B, 0x7E587D08, 0x7E59A23C, 0x7E5A0863 …). TAKE_MAIN 0x7E58204D follows | V |
| 0x7E5AB878–0x7E5ABE5A | **Eye-Fi device/request layer** (REQM/REQC/RSPC device files, `Request timed out...`), between the TAKE sequencer (ends 0x7E5AB877) and Eye-Fi card control 0x7E5ABE5B; callers 0x7E5ABE5B and 0x7E5AC0B8…0x7E5AC67F (D4 2026-11-09) | V (strings, callers) |
| 0x7E5E2988 → | **AF/FCS init** 0x7E5E2988 (only caller Usr0 0x7E503DD4; calls 0x7E610887 `FCS MOVIE INIT END`, 0x7E611D3A, 0x7E626BE3). One more Usr0 module init, like the TAKE init 0x7E581FB0 above. 0x7E5E28D8–0x7E5E297F before it are strobe helpers (callers mostly strobe 0x7E5D9640… and TAKE 0x7E5A1A27…, plus a few others such as 0x7E539EA4 and 0x7E695302); 0x7E5E29CE (`fMS/`, `fME/`) follows (D4 2026-11-09) | V |
| 0x7E635A08–0x7E635F4A | cam_ev.c (unchanged) | V |
| **0x7E635F4B–0x7E636A03** | **cam_expcal.c**: exposure → sensor-timing calculator ("sensor-mode parameter builder", F015) | V code; name I (§0) |
| **0x7E636A04–…** | **cam_frame.c starts here**, not at the 0x7E63790D anchor | V (error id 0x12 starts at 0x7E636A04; rodata rule) |
| ~~about 0x7E63E5xx~~ ~~**~0x7E640200**~~ **0x7E640200**–0x7E640857 (D3 2026-11-09) | cam_lens.c (`CAMLNS` 0x7E640200; id 0x25; last function 0x7E640844) (D3 2026-11-09). The code before it, up to ~~~0x7E6401FF~~ 0x7E6401FF (last function 0x7E640186, 122 B) (D3 2026-11-09), is still the imgdev driver: 0x7E64015E is called only from 0x7E63E3FB/0x7E63E443 (← cam_imgdev.c 0x7E63CF71/0x7E63D027), its callee 0x7E63EB3F returns the imgdev code 0x8481, and the last 0x0A17xxxx code is at 0x7E63E658 while the first 0x0A25xxxx code is at 0x7E640307 (C3 2026-11-09) | V anchors; ~~start not fixed~~ start V by error codes and callers (C3 2026-11-09) |
| **0x7E640858–0x7E640F52** | **cam_list.c**: list/queue library (id 0x28) | V code; name I |
| **0x7E640F53–0x7E641BB7** | **cam_mec_ctrl.c**: mechanical-control sequences | V code; name I |
| **0x7E641BB8–0x7E642324** | **cam_mem.c**: camera heap and named request pools (id 0x16) | V code; name I |
| 0x7E642325–0x7E643932 | cam_mirror.c (`MI_*`; id 0x1E; last function 0x7E6438E9 `mirror_dummy_post_isen_err`; 0x7E643933 ← 0x7E6463F6 is not placed) | V code; name I (A6 2026-11-09) |

## 2. The `sc` library (0x7E506CB0–0x7E508DA6)

**Components (V):**
- **`sc` shell** 0x7E506D76 (U_SHELL table entries 0x7E732740/0x7E733350): `heapshow`, `heaplist [count|small|large|middle|custom|apim|napim]`, `timing show/start/stop/clear`, `time_m`. Help 0x7E506CB0. The seven heap-debug back-ends 0x7E50796D–0x7E5079CD are stubs that print `NotSupport ... DEVELOP_PHASE => MP` (debug code compiled out of the production build).
- **SC_TTIMER soft timers**: register 0x7E506FF6 (a0 callback, a1 arg, d1 period index → slot 1–31, else `[ttmr]No Resource` and 0xFFFF); unregister 0x7E50708F; reset 0x7E5070EF. The task loop 0x7E507115 waits 25 (0x7E449605) per tick and calls the active slots (table 0x604F3468, 16 B per slot; masks 0x604F3658/0x604F365C). Wrappers 0x7E507270/0x7E50727A (← api 0x7E68E776); WB_MOV uses it too (§3).
- **scheap**: six fixed-block bitmap pools. The pool table 0x7E7348E4 = 6 × {base, payload, count, guard magic}:

| Pool | Base | Payload × count | alloc / free wrapper (sites) |
|---|---|---|---|
| small | 0x60001FC0 | 128 × 3200 | 0x7E5072ED (334) / 0x7E5072FB (346) |
| small2 | 0xA0097FC0 (uncached) | 128 × 50 | 0x7E507309 / 0x7E507317 |
| large | 0x6009A540 | 16384 × 40 | **0x7E507325 (116) / 0x7E507333 (133)** |
| large2 | 0xA013AF40 (uncached) | 16384 × 27 | 0x7E507341 (109) / 0x7E50734F (125) |
| middle | 0x601A7600 | 2048 × 490 | 0x7E50735D / 0x7E50736B |
| middle2 | 0xA02A4080 (uncached) | 2048 × 11 | 0x7E507379 / 0x7E507387 |

  - **Pattern (V):** each wrapper is 14 bytes, `mov imm32,a0` (alloc) or `a1` (free), then `call 0x7E507395` (alloc) or `0x7E5073B8` (free) and `ret [],4`. Both lock with 0x7E436593 and 0x7E431316/0x7E4313FE and call the pool function by pointer.
  - **The allocators take no size argument.** One call returns one fixed block. The block stride is payload + 64.
  - Next-fit bit search 0x7E50781E (shared rover 0x602A9B68). Bit test 0x7E507898, bit clear 0x7E5078AC.
  - Errors print `no more …_heap` or `bad pointer` / `not allocated pointer` and dump the task (0x7E507777). `small_free2` 0x7E50759A prints the wrong pool names (a copy-paste slip).
- **Guard checker (V):** init 0x7E507284 (← boot 0x7E44A043) calls 0x7E5079F1. That fills the 64-byte trailer of every block with `magic|index` (magics 0xDEB10000–0xDEB60000). The task **SCHEAPDBG** (0x1003, CPU1, 0x7E5079DD) runs 0x7E507A3A every 200 ticks. On a bad trailer it stores {pool, base, addr} at 0xA074FA34 and calls 0x7E44EE29(3) (I: a fatal-error report).

**Function catalogue: utility and string library.** All roles are matched by behaviour (V). "Sites" are from the range listing.

| Addr | Sites | Role |
|---|---|---|
| 0x7E507D18 | 5 | `sqrt(double)` by Heron iteration from 1.0 (dadd/ddiv/dcmp of 13a); returns 0.0 for x ≤ 0 |
| 0x7E507D60 / 0x7E507D75 | 36 / 2 | 16.16 fixed-point `65536·2^(x/256)` (x = s16 in 1/256 EV; table 0x7E734A48 = 2^(i/256) fractions) |
| 0x7E507DFD / 0x7E507E28 | 11 / 1 | `256·log2(x) − 14·256` (floor −2048) / `256·log2(x) − 20·256`. They use the msb index 0x7E505A17 (via 0x7E507E4B) and the table 0x7E734C48 = 256·log2(1+i/64). These are APEX conversions (I) |
| 0x7E507E54, 0x7E507E5E | 1, 8 | `abs`; u32 → n zero-padded decimal digits (no NUL) |
| 0x7E507E81 / 0x7E507EAE | 73 / 76 | decimal / hex digits → int, at most n chars (a0 str, d0 n) |
| 0x7E507F03 | 1 | byte copy with **(a0 src, a1 dst, d0 n)**; returns dst |
| 0x7E507F17, 0x7E507F43 | 1, 2 | case-insensitive compare of n bytes (0/1); `toupper` |
| 0x7E507F52 | 9 | copy 11 bytes + NUL (I: an 8.3 name) |
| 0x7E507F65/F72/F7D/F9A | 227/194/148/196 | get/put LE16, get/put LE32 (unaligned) |
| 0x7E507FB1/FBE/FC9/FE6 | 60/87/93/44 | get/put BE16, get/put BE32 |
| 0x7E507FFD, 0x7E50802E, 0x7E50808A | 2, 2, 1 | u16 → 4 hex chars; u16 → decimal; 8.8 version → "M.m" |
| 0x7E508108 / 0x7E50811A | 10 / 42 | BCD → binary / binary → BCD |
| 0x7E508131 / 0x7E508150 | 4 / 11 | UCS-2 → ASCII (stops at 0 or 0xFF) / ASCII → UCS-2 |
| 0x7E508170 | 8 | right-aligned decimal of width n (blank or zero fill) |
| **0x7E5081FA** | **380** | **`memcpy(a0 dst, a1 src, d0 n)`**, word/half/byte by alignment |
| 0x7E508256 / 0x7E508270 | 80 / 27 | `strcpy(a0, a1)` / `strcat` |
| 0x7E508294 | 66 | `memcmp(a0, a1, d0)` |
| **0x7E5082B6** | **667** | **`memset(a0, d0 c, d1 n)`**, word fill when aligned |
| 0x7E50831A / **0x7E508346** / 0x7E508358 | 354 / 48 / 5 | `strcmp` / **`strlen`** / `strupr` in place |

These are a second copy of the string functions, separate from 13a's C runtime (whose memcpy 0x7E500D33 and memset 0x7E500D73 are plain byte loops).

**RTC and calendar** (date struct `{u16 year; u8 mon, day, hour, min, sec, pad; u16 status}`; errors 0x2901–0x2905) (V):
- **RTC wrappers:** 0x7E50837E init (RTC driver 0x7E4675EA, clears tz); 0x7E5083B5 **local time** (22 sites: RTC read 0x7E508D19 → 0x7E467617; if tz flag 0x604F3848 = 1, then 0x7E508D23 adds tz minutes 0x604F384C × 60); 0x7E508397 set the clock (validates, then 0x7E467608).
- **Defaults and checks:** 0x7E5083E6 default date 2012-01-01 00:00 (14 sites); 0x7E508406 compare (a ≥ b); 0x7E508472 valid date-time (year 2000–2099); 0x7E5084BF valid date; 0x7E5084EE days in month (table 0x7E734C88, Gregorian leap rule).
- **FAT timestamps:** 0x7E50852C date → FAT/DOS packed u32 (year−1980 <<25 …, sec/2); 0x7E50859F FAT → date; 0x7E508605 / 0x7E508686 validity checks.
- **Exif text:** 0x7E508733 parses `YYYY:MM:DD HH:MM:SS` (Exif DateTime) with 0x7E5087DC.
- **Date/time text formatter 0x7E508810 (F004), 8 sites:** (a0 buf, a1 date, d0 flags). It copies a validated **caller date** through 0x7E508859; it does not read the clock (this corrects review F004). Flags:
  - 0x7000 date part: 0x4000 = 4-digit year, 0x2000 = `'YY`, neither = YY;
  - low nibble = order: 0 Y-M-D, 1 D-M-Y, else M-D-Y; 0x8000 drops the separator before the year;
  - separator `: . / , - :` from 0x7E734C94[(flags>>4)&7];
  - 0x300 time part: HH:MM, plus :SS if 0x200.
- **Epoch arithmetic:** 0x7E5089FF date → seconds since 1970 (cumulative-days table 0x7E734CA0); 0x7E508A6F seconds → date; 0x7E508B36 date → **seconds since 1904** (adds 2082844800: the QuickTime/MP4 epoch, I); 0x7E508B4A days between dates; 0x7E508B5C add years/months/days; 0x7E508BCA weekday (Zeller); 0x7E508C1D / 0x7E508C6C date ↔ Modified Julian Day (−678912).

## 3. WB module (0x7E579C34–0x7E581FAF)

**Role (V for edges and data, I for the colour meaning):** white balance and colour calibration. It is shared by stills, movie, iAuto and IMG_PRECON.

| Entry | Role | Callers outside |
|---|---|---|
| 0x7E57F3F0 → 0x7E57F3FF | boot init: reads prm 0x0AFA and the per-preset gain tables 0xC7E2 (CPRAM 4×u16, default 260,237,128,128 = R, B, G, G gains ×128) and 0xCBF2 (ROM ×256 corrections) | Usr0 0x7E503DD4 |
| **0x7E57F914** | **WB_MOV task** (CPU0, pri 11): receives 16-byte messages on queue var 0x7E43EDCE (0x7E5808EB). The mode word 0x60515C2A picks handler set 0x7E57FD8F or 0x7E57FE37. Its periodic tick is an SC_TTIMER slot (0x7E580862 → 0x7E506FF6; callback 0x7E5808A1 posts to the queue via 0x7E5808FE). It sends through Oimf 0x7E50689F | task table |
| 0x7E57F9BE | movie WB request | movie 0x7E6C5A23, 0x7E6D7F01 |
| 0x7E57F9AB, 0x7E57FC61 | WB state getters | SDET 0x7E6631E2, 0x7E6634F7, 0x7E663663 |
| **0x7E580E54** | **WB gain API**: per WB mode (prm 0x8062/0x800A EEROM; preset tables) returns gains, clamped ≤ 1023 | REC 0x7E7096DC, 0x7E715769, 0x7E718EDA; movie 0x7E6C8BB3; EXP_MOVIE 0x7E699CBF; SDET 0x7E6631E2…; strobe area 0x7E5D45A5 |
| 0x7E579E7F, 0x7E579F3F, 0x7E57A028, 0x7E57A0DC | gain and colour getters for development | IMG 0x7E55FAE8, 0x7E560588, 0x7E5606B6; REC 0x7E7103D4, 0x7E712BB8, 0x7E718D44, 0x7E7190AE, 0x7E71A9A5, 0x7E71B45F |
| 0x7E57A20E → 0x7E57A28C, 0x7E57AE08 (14.5 KB), 0x7E57A91A, 0x7E57AB28, 0x7E57E6D8, 0x7E57E8F8 | AWB estimation core: double-precision maths (log, ddiv, dadd); work area from scheap `large` | internal (I: auto-WB) |
| **0x7E580A54** | **IMG_PRECON cmd 4: spectral colour calibration** (below) | IMG_PRECON 0x7E55FA0A |
| 0x7E580D84 | resets the 13 gain tags to default (0x7E457DA8) and re-copies the working sets | IMG_PRECON start 0x7E55F97D |
| 0x7E581268 | writes the EEROM slot d2 of 0x8042/0x8052/0x8062/0x800A (I: custom / one-touch WB store) | IMG_PRECON cmd 2 0x7E55FF91 |
| 0x7E581210 | | TAKE 0x7E59E5A9 |

**IMG_PRECON cmd 4 (V for data flow, I for physics).** 0x7E580A54 allocates a `large` block. It loads prm **0xAA92/0xAAA2/0xAAB2 = `PRM_CAM_SPECTRUM_STL_R/G/B`** (FLASH, 65 × u16; per-body measured sensor spectral response, V names) into +124/+128/+132, and the lens/optics transmission 0xAC81 (CPRAM 65 × u8, hint `STATE_LENS`) into +164.
- **Step 1:** for each of **13 illuminant spectra** (ROM 0xAB81…0xAC41, 65 × u8; table 0x7E78F170), **F009 0x7E581385** integrates S_c = Σ L(λ)·T(λ)·SPEC_c(λ). It writes the gains R = S_G·128/S_R and B = S_G·128/S_B (G = 128, 128) to prm **0xC5F2…0xC6B2**. These are the per-preset WB gains: the default of 0xC5F2 = {159, 448} is tungsten-like, 0xC6B2 = {299, 192} is shade-like (I). On a zero sum it writes 13 and fails with 0x7102.
- **Step 2:** it copies them to the working set 0xC752… (table 0x7E78F35E, 26 pairs).
- **Step 3:** for 26 entries (13 illuminants × 2 targets 0xAC92/0xACA2; table 0x7E78F1F2), 0x7E58173E and 0x7E581AA5 use three 65-point patch spectra 0xAC51/0xAC61/0xAC71 (+148/+152/+156; I: test-chart reflectances). They compute **3×3 colour matrices** into **0xA19A…0xA32A** (9 × s16; rows sum to about 256, like the ROM matrix 0xAA4A {243,40,−27; −1,236,21; 0,8,248}).
- **Step 4:** 0x7E581E40 post-processes; 0x7E78F3C6 copies the matrices to 0xA3CA….
- Failure codes are reported via 0x7E579DBF(0x2A001001, code).

So IMG_PRECON is **pixel-defect correction (cmd 0) plus WB/colour preparation (cmds 1–4)**, not defect correction only.

## 4. cam_expcal.c (0x7E635F4B–0x7E636A03): exposure → sensor timing (F015)

- **0x7E635F4B init** (← 0x7E649558): caches prm pointers to 0x2F52 (ROM 256 × u16 curve), **PRM_CCD_DBGAIN_STANDARD** 0x712A, **PRM_CCD_SUBTRACT_OB_LEVEL** 0x703A and **PRM_MG5_KNEE** 0x7284 (+4048, +7920) in 0x60554668–0x60554680 (V).
- **0x7E635FB5 build(req)** (callers: cam shell 0x7E632889, still-func 0x7E65D763, live bulb 0x7E661B28, 0x7E649C2C, 0x7E649D34):
  - allocates a 112-byte context from the cam heap (0x7E641C2E) and looks up the **68-byte sensor-mode record** by id (req+4) via 0x7E64B325 (table 0x7E7BA370, 8 records);
  - dispatches on req+0: type 0 → 0x7E636020, 1 → 0x7E636317, 2 → 0x7E636513, else error 740/0x7E80 through 0x7E6369CA (module 0x15) (V).
- **Sensor-mode records (V bytes):** ids 0–7 with frame rates 30/60/120/240/30/30/10/1 (+6); (3,5), (2,2) or (1,1) at +8/+10 (I: line/pixel skip); 4:3 sizes 3072×2304 at +60/+62/+64/+66. Reading (I): 0–3 = the HS/HSSC/MSSC/LSSC live-view modes, 4 = HSHR, 5–7 = full readouts.
- **Leaves (V mechanics):**
  - 0x7E636079: width rounded to 16, clamped 256–4480;
  - 0x7E6360A1: exposure → line count via the APEX helper 0x7E69B34C and the record's line time (+12/+14/+16);
  - 0x7E6360FB / 0x7E636178: shutter start line and frame length;
  - 0x7E636206: remainder in EV via 0x7E640FFB / 0x7E69B37C;
  - 0x7E636240 (F015): line offset rec+6 (+ ctx+108 unless flag 0x400), clamped to the record's [+62, +60];
  - gain and OB: 0x7E6362AF–0x7E6369B3, using rodata 0x7E7AE584–0x7E7AE6C8.
- **Pattern for classifying a function:** no strings; a0/a1 = (request, context); reads fields at ctx+80…+108 and record +12…+66. It is a 17–267-byte leaf, called from one of the five type dispatchers 0x7E636020/0x7E636046/0x7E636298/0x7E6362AF/0x7E636306 (or the type 1/2 twins 0x7E636317/0x7E636513).

**cam_frame.c head (0x7E636A04–0x7E6378FF), V:**
- 0x7E636A04 is the frame init (← 0x7E65046F): it registers callback 0x7E637605 with cam_timer 0x7E6629C7 (parameter block {2, 0x7E637605, 0x3B83, 0x0A122018, 3}).
- **0x7E636AAB is the frame-command dispatcher** (← 0x7E651483): cmd 1–85 through jump table 0x7E7AE744 to about 40 handlers.
- **Handler pattern:** a 57–128-byte "start" allocates a 120-byte request (0x7E641C2E), initialises it as a frame object (0x7E637B39), stores its 45-byte "done" function at +112 and the client at +116, and starts it through the object's vtable +32. The "done" (`mov (116,a2),a3; call 0x7E637C39; call 0x7E641D60; calls (12,client)`) has 0 callers. Example pairs: 0x7E636BE9/0x7E636C47, 0x7E637166/0x7E63719F.

## 5. Camera mechanics (0x7E640858–0x7E642324) and what "mirror" means

- **cam_list.c 0x7E640858–0x7E640F52 (V code; name I (A6 2026-11-09)):** list library. Create 0x7E640858 (← cam.c init 0x7E628161, frame-sync 0x7E63A0EE); push/pop/peek 0x7E640961, 0x7E6409B7, 0x7E640A0D, 0x7E640A51, 0x7E640A79, 0x7E640B0B … (← cam.c packet lists, frame sync); error helper 0x7E640F3E (id 0x28).
- **cam_mec_ctrl.c 0x7E640F53–0x7E641BB7 (V):**
  - 0x7E640F63 / 0x7E640FB9: fixed-point 2^x tables 0x7E7B0590–0x7E7B11B8 (APEX → linear);
  - 0x7E640FFB: mode-clock scaling (sensor-mode record +32, /1000). These three are used by cam_expcal;
  - 0x7E641044 / 0x7E641048: `return 0` stubs (← cam.c);
  - **0x7E64104C dispatches CamCommand codes** 15 COM_SETUP, 16 COM_SETDOWN, 13 COM_READY_ON, 0x90/0x91 COM_MEC_POWERON/OFF, 0x92/0x93 COM_MEC_SETUP/SETDOWN_HIGH_SPEED to seven arm functions 0x7E6410AE–0x7E6411EC. Each arms event object 2 (0x7E635701/0x7E635781/0x7E63589A) with one **sequence**.
- **Sequence pattern (0x7E641221, 0x7E6412CA, 0x7E641394, 0x7E641473, 0x7E6414F0, 0x7E64156D, 0x7E641654):** `movm [a2],(sp); add -12,sp; mov a0,a2; mov 2,d0; call 0x7E635865`. Each step re-arms event 2 with the next mask and **itself** as callback, then posts one 12-byte request {cmd, param, done} (table 0x7E7B15B8–0x7E7B1670). The request goes to MI via 0x7E641A9A (open MI 0x7E642398, dispatch 0x7E642459, close 0x7E6423F1) or to the shutter (SH) via 0x7E641B30 (0x7E655834 / 0x7E6558AD / 0x7E655869). The done handlers 0x7E64173B–0x7E641A88 (56–61 B, 0 callers) set the event bit (0x7E63589A, 0x7E635B84).
- **cam_mem.c 0x7E641BB8–0x7E642324 (V code; name I (A6 2026-11-09)):**
  - heap init 0x7E641BB8 (← cam.c init): 230 × 128 B at 0x6055578C and 12 × 512 B at 0x6055CA9C (free lists 0x605553C4 / 0x6055575C);
  - **alloc 0x7E641C2E(d0 size) → a0** (≤ 128 small, ≤ 512 large, else error 0x0A162001…; 203 sites); **free 0x7E641D60(a0)** (188 sites); usage stats 0x605553B2–BE; dumps 0x7E641E4C/0x7E641F0F/0x7E641F48 (`Used Block`, ← cam shell 0x7E6321B8);
  - named request pools: register by name 0x7E642035 (max 8; ← MI 0x7E642325, SH 0x7E6557CE, STL 0x7E656D91, LB 0x7E65DAC7), take n blocks 0x7E642097 (18 sites, e.g. MI init takes 11 × 32 B), release 0x7E6421C2.

**What the MI ("mirror") module does on the E-PM2.** It is **not a stub**: it is the **shutter-charge motor client** (V for requests, I for the physics).
- MI init 0x7E6433B0 builds eleven 32-byte MEC request objects at MI+48…+88 with MOT request codes: +48/+68 MOT ON, +52/+72 MOT OFF, +56 INTIAL, +60 OPENRDY, +64 OPENCHG, +76 F_READY, +80 F_OPCHG, +84 N_READY, +88 code 6 (no name).
- The MI command table 0x7E7B18B8 maps the commands:
  - 9 / 10 → MOT ON / OFF (ref-counted);
  - 6 → OPENRDY, 5 → OPENCHG, 0x91 → INTIAL (each with cam timers 13–16 as timeouts);
  - 0x93/0x94 → MOT ON/OFF (power variant), 0x95/0x96/0x97 → F_READY/F_OPCHG/N_READY, 0x98 → code 6;
  - 1/2 → plain timers.
- Every MOT handler is the 24-byte pattern `mov (0x6055E2B4),a1; mov a0,a2; mov (N,a1),a0; mov a2,(28,a0); call 0x7E51787B`.
- **Sequences built from this (V):**
  - COM_SETUP: SH 0x10093 + MOT ON → OPENRDY → SH 0x1000B(−1);
  - COM_SETDOWN: SH 0x1000C → OPENCHG → MOT OFF;
  - COM_READY_ON: MOT ON → INTIAL → MOT OFF;
  - MEC_POWERON/OFF: MOT ON/OFF;
  - MEC_SETUP_HS: MOT ON → code 6 → MOT OFF;
  - MEC_SETDOWN_HS: MOT ON → N_READY → MOT OFF.
- **Reading (I):** a mirrorless body keeps its focal-plane shutter open for live view. The motor must drive it to "open-ready" for live view and close/charge it before a capture. The DSLR code's mirror motor did the same charge job. So the still and live-bulb `MIRROR_DOWN*` phases on this body are the shutter charge/close steps before exposure, and MI open (0x7E642398) powers the MEC timing unit (0x7E51783A → 0x7E50F8F3) for them. The five `mirror_dummy_post_pi/pinext/bound/brake/isen_err` functions 0x7E6436F1–0x7E6438E9 (0 callers; mirror code ends at 0x7E643932) are error loggers for the photo-interrupter, bound, brake and isen posts; the isen one also calls the MI_RES function 0x7E642FAE (A6 2026-11-09).

## 6. Driver and service roles named only by unit (review 1, item 2)

| Unit | Entry points and role |
|---|---|
| **MEC command layer** (MAG_COM / MOT_COM), 0x7E517791–0x7E518C61 at least (0x7E518BBA is a 20-B function start; 0x7E518BCE and 0x7E518BF2 after it use the layer state 0x604F63A0) (A6 2026-11-09) (V) | Init 0x7E517791 creates the locks `ANY_USE`/`MAG_COM`/`MOT_COM` (0x7E516C32). Open/close 0x7E51783A/0x7E51785A are ref-counted: the first open → MEC timing unit 0x7E50F8F3, the last close → 0x7E50F96F. **Submit 0x7E51787B(a0 req)**: dispatches on the code alone (u16 +0, 0–18); the class (0 MOT, 0x200 PWR, else MAG) is `(word +8) & 0xFF00`, read only by the printer (A6 2026-11-09); jump table 0x7E7379C0; a bad code → 0x1500A001. Names from the printer 0x7E51256F: **MOT** 0 ON, 1 OFF, 2 OPENRDY, 3 OPENCHG, 4 CLOSCHG, 5 INTIAL, 7 F_READY, 8 F_OPCHG, 9 N_READY, 16 ABORT; **MAG** 10 ON, 11 OFF, 12 SET, 13 START (NML/DRK, TV, TIME), 14 STOP, 15 MG3_CHG; **PWR** 17 ON, 18 OFF. Handlers (through the 8-byte case blocks 0x7E51789C–0x7E517930 of the jump table inside 0x7E51787B; they are not separate functions (L1 2026-11-09)): 0 0x7E517952, 1 0x7E5179FA, 2 0x7E517A9D, 3 0x7E517B95, 4 0x7E517C8D, 5 0x7E517D7F, 6 0x7E518271, 7 0x7E517E81, 8 0x7E518123, 9 0x7E517FCF, 10 0x7E5183EB, 11 0x7E5184ED, 12 0x7E51856B, 13 0x7E518664, 14 0x7E518769, 15 0x7E5187DF, 16 0x7E5183C5, 17 0x7E518A6E, 18 0x7E518ABE; in address order codes 7, 9, 8, 6, 16 are out of sequence, and the unnamed MOT code 6 has its own handler (A6 2026-11-09). Each builds a driver request with "done" and "event" callbacks (e.g. MAG START 0x7E518664 → 0x7E518684, callbacks **0x7E5186EA = F006** and 0x7E518731). The done callback releases the lock by name (0x7E516D50) and calls the client's +16. `Shutter Client [0x%02x]` 0x7E518BBA ← `mec` monitor 0x7E510C3A. The `mec` shell has `mec shutter set [expose_time us]`, `mec still [num] [time]`, `mec lsnc …` (0x7E510943). Reading (I): MAG = curtain-hold magnets, MOT = charge motor |
| **EMS1/EMS2** (`per_ems`), 0x7E45F2D8–0x7E46134D (V edges) | 0x7E45F2D8 init (IRQs, ← Usr0). EMS1: 0x7E45F2EA/0x7E45F309/0x7E45F333(+0x7E45F406 register program)/0x7E45F9F3 ← TAKE 0x7E59E203…0x7E59E2B3 (AF side); ISR 0x7E45FB1F → 0x7E45FCDE; result getters 0x7E45FDFA/0x7E45FE53/0x7E45FEB5 ← ~~SDET algorithm block~~ the mdet motion-detection / AF-tracking library (03 §7b) (C3 2026-11-09) 0x7E66C9A8/0x7E66DA1D (0x7E66C9A8 = mdet's EMS1 AF-area motion per-frame step, ← 0x7E66C72B; 0x7E66DA1D = the EMS1 read of the tracking core 0x7E66D66B; 15b §4) (D3 2026-11-09). EMS2: set-up 0x7E460030…0x7E46012D (+0x7E4601A4 register program), start 0x7E460810, ISR 0x7E4608F9 → 0x7E4609E6; **result decoders 0x7E460DB8, 0x7E460FC2 (F002), 0x7E46118C** ← `mdet` code 0x7E670FB8, 0x7E671208…0x7E671E92 (192-byte records, 17-bit fields, signed 9/13-bit pairs = vectors, I). Shell 0x7E46134D |
| **IOE serial callbacks** (V, review F003) | SIO ch3 config 0x7E463DB8 (← 0x7E464526, 0x7E46480D): 400 kHz, write-done **0x7E464177**, read-done **0x7E4641A5**. Request ring 0x604168B0 (8 × 32 B, head 0x60416DF9). Advance 0x7E464138 starts the next GIOSEQ (0x7E464050) or releases ch3 (0x7E4699F9(3)) |
| **External-strobe serial wait** (V, review F013) | 0x7E5DE91F(step): waits on the caller's flag with a 10 s timeout. At state ≤ 1 and step 6 it waits on flag 0x7E43EBD2 bits 1\|2. On timeout it logs 0x23000222. 14 sites (detect 0x7E5DD358, video light 0x7E5DDAD8, mode events, firmup 0x7E5DF13A…). `sio time out` handler 0x7E5DE8AE precedes it |
| **DCF file-type scanner** (V) | 0x7E5AF95D classifies a directory entry by its 8.3 extension: JPG 17, TIF 18, ORF 19, MOV 20, MP4 21, AVI 22 (gated by mask byte 0x6053C544), MPO 23, WAV 0x102. Callers: DCF scan 0x7E5AFE23, 0x7E5B014C, 0x7E5B47BA, 0x7E5B4B35; DPOF side 0x7E5BEBE1, 0x7E5BED03. Later bodies name this file `dcfscan.c` (I) |
| **exFAT formatter** (V mechanics; file `sdmem_format.c` in later bodies, I) | Format sequence 0x7E5B9DD7 (← 0x7E5B8524): 0x7E5B9D93; boot region 0x7E5B9EBB → boot sector 0x7E5BA075 (`EXFAT   `); 0x7E5BA317 (I: bitmap/up-case/root); FAT writer **0x7E5BA1FE (F011)** once per FAT copy (entries 0/1 = 0xFFFFFFF8/0xFFFFFFFF, contiguous chains, 16 KB uncached buffer from `large2`). Sector writer 0x7E5B9D07 (≤ 32 sectors, 12 sites) |

## 7. iAuto scene ids (F017)

The `dbgscnmode` help in SDET's shell 0x7E6637F2 prints the scene-type values (V):

| id | 3 | 8 | 9 | 11 | 12 | 17 | 18 | 21 | 23 | 50 | 156 | 157 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| scene | PROGRAM | SPORTS | PORTRAIT | SCENERY | NIGHT_SHOT | SCENERY_PORTRAIT | NIGHT_SHOT_PORTRAIT | EVENING_SUN | MACRO | UNDERWATER_SNAP | NIGHT_SHOT_MACRO | SPOT_LIGHT |

So F017 0x7E664A8F chooses **MACRO (23)** if the distance field is ≤ 325, else **PROGRAM (3)** (V); that the field is in mm is I.

**Main decision 0x7E663EC4** (1706 B, ← 0x7E663EAB ← 0x7E663D68 / 0x7E6652D7). Verified constants:
- distance +0 (−1 or 0x80000000 → 100000);
- word +12 = 0 → UNDERWATER_SNAP (meaning of +12: I);
- BV +20 ≤ −805 → night branch: a face list at +92/+96 (14-byte records) against size thresholds, then NIGHT_SHOT_PORTRAIT (18) if byte +209 = 1, else PORTRAIT (9), else NIGHT_SHOT (12); distance ≤ 325 with BV > −1083 is tested there too;
- daylight branch: PORTRAIT, SCENERY_PORTRAIT (17), EVENING_SUN (21; thresholds 1700/917/416), SCENERY (11; 2094, 200), SPOT_LIGHT (157; byte +69 = 1 and +209 = 0);
- the sub-flags +2…+6 of the 10-byte result come from 0x7E6657B3 (4.9 KB, 14 sites; ≥ 1785 test) and from "+68 = 2 and BV > 1000" (I: the `aozora`/`highsat`/`up_portrait` dump fields).
- Debug overrides `dbgscn`/`dbggyakkou`/`dbgaozora`/`dbghighsat`/`dbgnear`/`dbgupport` live at 0x6056F118–0x6056F130.

## 8. Corrections

- **Section 01:**
  - Region row 0x7E4E0000–0x7E521020: insert "**`sc` library 0x7E506CB0–0x7E508DA6** (sc shell, SC_TTIMER soft timers, scheap 6 fixed-block pools + SCHEAPDBG guard checker, memcpy 0x7E5081FA / memset 0x7E5082B6 / strlen 0x7E508346 and string helpers, RTC/calendar)".
  - SC_TTIMER row: the soft-timer dispatcher is V (32 slots, 25-tick loop, register 0x7E506FF6). scheap is a separate part of `sc`, and SCHEAPDBG (0x1003) is its guard checker.
- **Section 02:**
  - WB_MOV "not mapped" → WB_MOV 0x7E57F914 belongs to the WB module 0x7E579C34–0x7E581FAF (§3).
  - TAKE starts at its init 0x7E581FB0.
- **Section 03:**
  - §2 "the mirror code is a stub" → **wrong**: MI is the shutter-charge motor client (MOT_* requests); `MIRROR_DOWN` = charge/close before exposure (I).
  - Module table: add cam_expcal.c 0x7E635F4B–0x7E636A03 (exposure → sensor timing), cam_frame.c from 0x7E636A04 (frame-command dispatcher 0x7E636AAB), cam_lens.c, cam_list.c 0x7E640858, cam_mec_ctrl.c 0x7E640F53, cam_mem.c 0x7E641BB8 (cam heap 0x7E641C2E/0x7E641D60).
  - cam_ev.c ends at 0x7E635F4A.
  - §7b SDET: add the scene-id table (§7).
- **Section 13a:**
  - Row "0x7E579C34 → TAKE / WB_MOV code" → WB module 0x7E579C34–0x7E581FAF.
  - `buff` ends 0x7E579C33, not 0x7E579A7F.
  - IMG_PRECON is "pixel-defect correction (cmd 0) + WB/colour preparation (cmds 1–4: 0x7E55FE1E/0x7E55FF91/0x7E55FFA3 call WB; cmd 4 = spectral WB-gain and colour-matrix calibration)". Also correct firmware-map D1 note, inventory row "Pixel Mapping" and open question 4.
- **Section 13f:**
  - UI/keys start at 0x7E508DA7 (beep requests); the `ui` shell `beep`/`help` are at 0x7E508EDA/0x7E508F14.
  - Add the MEC request layer and code table, the EMS entry points, IOE callbacks, DCF scanner and exFAT formatter (§6).
- **Review C2 batch 1 itself:**
  - F004's formatter formats a caller-supplied date; it does not read the clock.
  - F009: "lens spectral table" is the sensor response × illuminant × 0xAC81; it runs 13 times, once per illuminant.
- **modules.tsv rows to add or change (not edited here):**
  - `7e635f4b 7e6369ca cam_expcal.c 0 inferred(alpha+E-PL7)`;
  - change cam_frame.c first_fn to `7e636a04`;
  - `7e640200 cam_lens.c (CAMLNS)`; last_fn `7e640844` (range 0x7E640200–0x7E640857, 15b §7) (D3 2026-11-09);
  - `7e640858 7e640f3e cam_list.c`;
  - `7e640f53 7e641ba1 cam_mec_ctrl.c`;
  - `7e641bb8 7e642301 cam_mem.c`;
  - `7e642325 7e6438e9 cam_mirror.c` (A6 2026-11-09);
  - `7e6557ce cam_shutter.c`;
  - `7e629854 cam_aedrv.c`, `7e62a962 cam_afdrv.c`, `7e62b4dd cam_aperture.c`, `7e62f6eb cam_debug.c` (all inferred by the same rule);
  - unnamed modules `sc` (7e506cb0–7e508da6) and `wb` (7e579c34–7e581faf).

## 9. Open questions

1. The physical meaning of MOT code 6 (unnamed) and of shutter (SH) commands 0x10093/0x1000B/0x1000C. Whether OPENRDY/OPENCHG mean "open for live view" / "close and charge" needs the shutter module 0x7E6557CE read in full.
2. 0xAC51/0xAC61/0xAC71 (patch spectra?) and the targets 0xAC92/0xACA2: which colour targets and which two colour modes the 26 matrices serve.
3. The file names inside ~0x7E643800–0x7E64F2A1 (L1 2026-11-09) (param, pfp, port, prepro, rap) and whether SPRDRV (id 0x1B) is cam_prepro or cam_pfp.
4. The SDET input record (what fills +12, +68, +69, +208, +209) and the full daylight order of tests in 0x7E663EC4.
5. Which UI path reaches IMG_PRECON cmds 1/2 (I: one-touch WB) and the slot count of 0x8042/0x8052.
