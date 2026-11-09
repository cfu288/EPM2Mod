# 13a. C runtime, soft-float and the IMG image-job library (E-PM2 v1.6)

Round D1 deep dive for the string-less libraries that coverage round C1 flagged (F003, F005, F006, F043, F070).

- **Labels:** **verified** = read in the code or bytes; **inferred** = from usage, names, order or layout.
- **Database:** improved build `--out $S/map-test` (74,554 functions). "Sites" = call sites in calls.tsv; "fns" = distinct calling functions.
- **Scratch:** `$S/d1/libraries-runtime/` (`crt.dis` = disassembly of the whole runtime; `graph.py`, `comp.py`, `ext.py`, `feat.py`, `head.py` = call-graph and feature helpers, run with `python3 -I`).

## 1. Area and boundaries

| Range | Contents | Basis |
|---|---|---|
| 0x7E4C90CA–0x7E4FDFFF | **0xFF padding** (erased flash), no code | verified (bytes) |
| **0x7E4FE000–0x7E501C5A** | **C runtime**: libm, stdio (printf/scanf), stdlib, string, setjmp, double and single float helpers | verified (first byte = `tolower`; next function 0x7E501C5B is the USRTEST task A, strings `TskA_WF`) |
| 0x7E544A6F and earlier | Firmware update (last firmup helpers 0x7E544A09–0x7E544AA5 are called from 0x7E5436D1 / 0x7E8808C0) | verified (callers) |
| **0x7E544AA9–~0x7E576D58** | **IMG library**: the image-engine *job* library (job API, job tasks, per-operation parameter builders, tone/colour curve maths, pixel-defect correction, JPEG header, colour fill) | verified for the anchors in §3; whole-range membership inferred from the call graph |
| inside it: 0x7E546973–0x7E548755 | CPU pixel kernels called only by art code (0x7E72Cxxx, 0x7E722868, ART_IMG_CF 0x7E7297FF); the last kernel 0x7E5486B4 is 162 B | verified (callers) (A4 2026-11-09) |
| ~0x7E576D59–0x7E579A7F | Buffer-pool manager `buff` (shell 0x7E5776A2, `buff_recfile.c` 0x7E5793F0, pool names PRIM/THUM/…/PLAY_WORK) | verified (strings, modules.tsv) |
| 0x7E579C34 → | TAKE / WB_MOV code (callers 0x7E57E8F8, 0x7E580E54…) | verified (callers) |

**Bounds correction:** C1 gave 0x7E4F8000 for the runtime start; 0x7E4F8000–0x7E4FDFFF is padding. C1 gave ~0x7E54D000–0x7E578000 for the image library; it starts at 0x7E544AA9 (IMG init, called from Usr0 0x7E503DD4) and its last own code is near 0x7E576D58. The `buff` manager after it is a separate module.

**Note (inferred):** 0x7E4FE000 is also the start of the region that section 01 says boot copies from flash (0x7E4FE000–0x7E881000). The runtime is the first module in that image.

## 2. C runtime (0x7E4FE000–0x7E501C5A)

### 2.1 Compiler and calling convention

Evidence in the code (all **verified**):
- A double is passed in a register pair: the first in **d0:d1**, the second in **a0:a1**. The result comes back in d0:d1 (example: `pow` 0x7E4FE4CE reads x from d0:d1 and y from a0:a1).
- Variadic functions take the first argument in a register and the rest on the stack (`sprintf` 0x7E4FFDE3: buf in a0, format at (16,sp)).
- **Double compares return their result in PSW.** 0x7E50130D ends with `mov d0,psw`, and callers branch straight after the call (`call 0x7E50130D; ble …`).
- There is one global `errno` at 0xA0728B84. Values: **EDOM = 1, ERANGE = 2**. A byte search finds the address only inside the runtime, so no firmware code reads errno.
- **HUGE_VAL = DBL_MAX** (0x7FEFFFFF_FFFFFFFF), not infinity. Examples: `log(0)` returns −DBL_MAX with ERANGE; `ldexp` and `exp` overflow return ±DBL_MAX.
- **libm uses simple algorithms, not fdlibm:**
  - `atan` is a 19-term continued fraction;
  - `exp` is a continued fraction plus `ldexp`;
  - `sqrt` is 20 Newton steps on `frexp`/`ldexp`;
  - `log` uses (m−1)/(m+1) with a coefficient table, plus e·ln2.
- **Single-precision ops** are 7-byte wrappers around one F6-group opcode: `f6 XY` + `81 e5 de 00 00` (`mov d0,d1; add d1,d1; retf`). Float→int and int→float use the opcodes `fb e0 80 00` and `f9 4x` (objdump prints these as `udf02`, `mcst9`, `udf05`, `mcst48`, `fadd fd8,fd0,fd0`). So the CPU has a float unit that is reached through these opcodes (verified that the opcodes are used; that the unit exists is inferred).

**Conclusion (inferred):** this is **not** GCC libgcc and not Cygnus newlib:
- GCC's mn10300 ABI does not pass doubles in d0:d1/a0:a1;
- libgcc's `__cmpdf2` returns an int, not flags;
- newlib uses EDOM 33 / ERANGE 34 and fdlibm.

It looks like a vendor runtime: the minimal ANSI library of the Panasonic MN103 C compiler. No string names the compiler.

**Link order (verified):** math → stdio → stdlib → string → setjmp → conversion helpers → double ops → single ops. Then `tan`, `atof` and `strtok` follow at the end, out of that order. They may come from a second library object (inferred).

### 2.2 Function catalogue

Columns: address | size | sites/fns | name | notes. Every name is identified by behaviour (verified unless marked I = inferred).

**math.h** (doubles; static data at 0x7E73719C–0x7E737204):

| Addr | Size | Sites/fns | Name | Notes |
|---|---|---|---|---|
| 0x7E4FE000 | 22 | 6/4 | `tolower` | ctype pointer 0x7E731698 → table 0x7E731588; `(tab+1)[c] & 1` → c+32 |
| 0x7E4FE016 | 139 | 1/1 | `asin` | \|x\|>1 → EDOM, 0; atan(x/√(1−x²)); ±π/2 |
| 0x7E4FE0A1 | 254 | 5/4 | `atan` | \|x\|>1 → π/2−atan(1/x); continued fraction i=19…1 |
| 0x7E4FE19F | 153 | 5/2 | `atan2(y,x)` | x=y=0 → EDOM; quadrant fix with ±π |
| 0x7E4FE238 | 25 | 4/4 | `cos` | sin(x+π/2) |
| 0x7E4FE251 | 25 | 11/6 | `fabs` | clears the sign byte |
| 0x7E4FE26A | 358 | 61/18 | `log` | 0 → −DBL_MAX, ERANGE; <0 → EDOM; frexp, √2 split, table 0x7E73719C, +e·ln2 |
| 0x7E4FE3D0 | 58 | 2/2 | `frexp(x, int*a0)` | |
| 0x7E4FE40A | 116 | 5/4 | `ldexp` core (n in d0, x in a0:a1) | overflow → ±DBL_MAX, ERANGE; underflow → 0, ERANGE |
| 0x7E4FE47E | 80 | 4/3 | `log10` | log(x)·0.4342944819 |
| 0x7E4FE4CE | 453 | 37/13 | `pow(x,y)` | integer y < 32768 → square-and-multiply; else exp(y·log\|x\|); limits ±709.78 |
| 0x7E4FE693 | 314 | 7/2 | `exp` | |
| 0x7E4FE7CD | 144 | 6/4 | `modf(x, double*a0)` | |
| 0x7E4FE85D | 242 | 4/4 | `sin` | fmod 2π, quadrant, polynomial table 0x7E7371CC |
| 0x7E4FE94F | 136 | 3/3 | `fmod` | y=0 → EDOM |
| 0x7E4FE9D7 | 156 | 34/10 | `sqrt` | <0 → EDOM |
| 0x7E4FFD72 / 0x7E4FFDA2 | 48 / 65 | 2/2 each | `ceil` / `floor` | ceil(x) = −floor(−x); 0x7E72D779 (OKAO) calls `ceil` |
| 0x7E501AAC | 272 | 1/1 | `tan` | continued fraction; only caller is GUI 0x7ED3231E |

**stdio, locale** (tables 0x7E73170C–0x7E731904):

| Addr | Size | Sites/fns | Name | Notes |
|---|---|---|---|---|
| 0x7E4FEA73 | 26 | 8/4 | `printf` | engine mode 0: output through putc 0x7E5007E0 → 0x7E44B65C |
| 0x7E4FEA8D | 621 | 3/3 | `_doprnt` engine (d0 = 0 stdout / 1 buffer, a0 = fmt, a1 = va) | conversion jump table 0x7E731714 indexed c−'E': c d e E f g G i n o p s u x X |
| 0x7E4FECFA, 0x7E4FEDD9, 0x7E4FEDFB | 223, 34, 60 | — | padding / emit-n / emit-char | "0x"/"0X" prefix strings 0x7E73170C |
| 0x7E4FEE37, 0x7E4FEEBF | 136, 196 | — | parse flags (table 0x7E7317E4: `- 0 # + space`) / width, `*`, precision, h l L | width parsed with `strtol` |
| 0x7E4FEF83 | 205 | 3/3 | `localeconv` | builds a 48-byte `struct lconv` at 0xA0728840 from LC_NUMERIC (index 0x7E7318B8) and LC_MONETARY (index 0x7E7318B4) tables |
| 0x7E4FF050 | 394 | — | %d %i %u %o %x %X %p formatter | digits via 0x7E4FF88E / 0x7E4FF8C2 / 0x7E4FF8F8 (utoa variants), reverse 0x7E4FF92C |
| 0x7E4FF1DA, 0x7E4FF2BA, 0x7E4FF383, 0x7E4FF508, 0x7E4FF709 | | — | float front end / %f / %e %E / %g %G / mantissa+exponent assembly | |
| 0x7E4FF947, 0x7E4FF9E6 | 159, 826 | — | round digit string / double → decimal digits (dtoa; 10ⁿ table 0x7E7318D0) | |
| **0x7E4FFDE3** | 27 | **1664/643** | **`sprintf`** | the debug-text formatter used everywhere |
| **0x7E4FFDFE** | 27 | **907/438** | **`sscanf`** | |
| 0x7E4FFE19 | 1256 | 1/1 | `_doscan` engine | converters 0x7E500301 (numbers, via strtol/strtod), 0x7E50042D/0x7E50052D (token read), 0x7E50068A, 0x7E500745 (I: %c/%s/whitespace) |
| 0x7E5007C1 | 21 | 14/14 | `vsprintf(a0 buf, a1 fmt, d0 va)` | |
| 0x7E5007D6 / 0x7E5007E0 | 10 / 10 | | getc / putc glue → 0x7E44B63A / 0x7E44B65C | 0x7E44B64B = ungetc (I) |
| 0x7E5007EA | 60 | 1/1 | `fwrite`-style (ptr, size, n, stream) | putc loop |

**stdlib, string, setjmp, ctype:**

| Addr | Size | Sites/fns | Name | Notes |
|---|---|---|---|---|
| 0x7E4FFD20 / 0x7E4FFD35 | | | HUGE constant (0x7E7318E4) / DBL_MAX getter | used by the strtod scaler 0x7E500BD5 |
| 0x7E500826 / 0x7E500A1E | 12 | 10/6, 1/1 | `abs` / `labs` | |
| 0x7E500832 / 0x7E500A0D | 17 | **200/39**, 1/1 | `atoi` / `atol` | strtol core with base 10 |
| 0x7E500843 | 458 | 4/4 | strtol/strtoul core (a0 s, a1 endptr, d0 base 0/2–36, d1 &overflow) | uses `tolower` |
| 0x7E500CF7 | 30 | 22/10 | `strtol` | sets ERANGE on overflow |
| 0x7E500A2A / 0x7E500A50 | 38 / 15 | 1/1 | `rand` / `srand` | state 0x602A9B40/44, `& 0x7FFF`; only the BASIC overlay calls them |
| 0x7E500A5F / 0x7E500A81 / 0x7E500BD5 | 34 / 340 / 290 | | `strtod` / strtod core / power-of-10 scaler | |
| 0x7E501BBC | 15 | 1/1 | `atof` | caller 0x7F0AA056 (ADJ `Calib.prm` reader) |
| 0x7E500D15 | 30 | 87/37 | `memcmp(a0,a1,d0)` | |
| **0x7E500D33** | 19 | **767/457** | **`memcpy(a0 dst, a1 src, d0 n)`** | |
| 0x7E500D46 | 45 | 12/12 | `memmove` | |
| **0x7E500D73** | 17 | **1367/823** | **`memset(a0, d0 c, d1 n)`** | |
| 0x7E500D84 / 0x7E500DAA | 38 / 32 | 62/25, 8/3 | `strcat` / `strchr` | |
| **0x7E500DCA** | 31 | **1170/146** | **`strcmp`** | |
| 0x7E500DE9 / 0x7E500E01 | 24 / 22 | 127/90, 185/94 | `strcpy` / `strlen` | |
| 0x7E500E17 / 0x7E500E40 / 0x7E500E64 | 41 / 36 / 34 | 3, 16, 29 | `strncat` / `strncmp` / `strncpy` (zero-pads) | |
| 0x7E500E86 / 0x7E500EAB / 0x7E500EF0 | 37 / 69 / 60 | 5, 2, 66 | `strrchr` / `strspn` (256-byte set on stack) / `strstr` | 59 of the `strstr` sites are in 0x7E90xxxx |
| 0x7E501BCB | 144 | 16/1 | `strtok` (C1 F003) | save pointer 0xA0728B88; only caller is `sdk api GET_HISTOGRAM` 0x7E9ADC78 |
| 0x7E500F2C / 0x7E500F46 | 26 / 28 | 1/1, 30/19 | `setjmp` / `longjmp` | buffer {d2,d3,a2,a3,sp,ret}; longjmp(v=0) returns 1. **Only the BASIC overlay (0x7F05xxxx) uses them** |

**Float helpers** (hand-written assembly; not reached through pointers, no `movm`):

| Addr | Size | Sites/fns | Op | Basis |
|---|---|---|---|---|
| 0x7E500F62 | 176 | 54/18 | double → float | V (NaN 0x7FC00000) |
| 0x7E501012 / 0x7E50106D / 0x7E50107C / 0x7E50108C | | 50, 63, 70, 102 | double → short / int / ushort / uint (core 0x7E501022) | V |
| 0x7E5010DE / **0x7E5010EA** | 12 / 547 | 307, 244 | `dsub` = d0:d1 − a0:a1 (flips the a1 sign, falls into add) / `dadd` | V |
| 0x7E50130D / 0x7E501379 | 108 / 23 | 238, 137 | `dcmp(d0:d1, a0:a1)` → PSW / double test against 0 → PSW | V |
| **0x7E501390** | 622 | 489 | `ddiv` = d0:d1 / a0:a1 | V (`divu` loops; `atan` calls it as 1.0/x) |
| 0x7E5015FE / **0x7E50160E** | 16 / 411 | 24, 635 | `dneg` / `dmul` | V |
| 0x7E5017A9 / 0x7E501942 | | internal | unpack double / float (class code in d3: 1 inf, 2 zero, 4 NaN) | V |
| 0x7E5017EC | 108 | 110 | float → double | V |
| 0x7E501858 / 0x7E501860 / 0x7E501867 / 0x7E50186F | | 25, 165, 49, 87 | float → short / int / ushort / uint | V for the code; the op of `fb e0 80 00` is I |
| **0x7E5018BC** (`f6 34`) | 7 | 445 | **fsub** | I, strong: a 3×3 determinant (0x7E52A079) uses the signs + − − + + − in this order; rounding at 0x7EE5B287 does x>0 ? 0.5+x : x−0.5 |
| **0x7E5018C3** (`f6 24`) | 7 | 1223 | **fadd** | I, strong (same two sites) |
| 0x7E5018CA (`f6 61`) / 0x7E5018CF | 5 / 7 | 564, 405 | fcmp(d0,d1) → PSW / fcmp(d0, 0.0) | V that the result is in flags |
| 0x7E5018D6 (`f6 54`) | 7 | 430 | **fdiv** | I (`(a−b)/2.0f + 0.5f → int` at 0x7EE69203) |
| 0x7E5018DD | 11 | 107 | fneg | V |
| **0x7E5018E8** | 90 | **2260** | **fmul** | V for the structure (exponent add, `f6 44`, mantissa `udf01`/`udf15`, round) |
| 0x7E501983 / 0x7E50198D / 0x7E5019EA / 0x7E5019F4 | | 89, 172, 164, 184 | short / int / ushort / uint → double | V |
| 0x7E501986 / 0x7E5019E4 / 0x7E5019ED / 0x7E501A2C | | 106, 496, 90, 69 | short / int / ushort / uint → float | V for uint (manual path for ≥ 2³¹) |

**Recognising runtime code by its bytes:**
- double helpers start with `42 00 46 04 43 08 47 0c` (`mov d0,(sp); mov d1,(4,sp); mov a0,(8,sp); mov a1,(12,sp)`), then `and 0xFFFFF,d1; lsr 20; and 2047`;
- single-float ops: `f6 XY 81 e5 de 00 00`;
- string functions are tight `setlb … lcs/lne/leq` loops (MN103 loop buffer) with no frame;
- libm functions are chains of `call 0x7E5010EA/0x7E50160E/0x7E501390` with IEEE constants (π/2 = 0x3FF921FB_54442D18, ln2 = 0x3FE62E42_FEFA39EF) and stores to 0xA0728B84.

## 3. IMG image-job library (0x7E544AA9–~0x7E576D58)

**What it is (inferred from the anchors below):** the CPU-side half of the TruePic image engine. Clients (REC_*, MOV_*, ART, PLAY, TAKE, the PTP overlay) fill a job descriptor; the library computes parameter blocks for the job's *operation type*, then queues the job to the image-engine worker tasks. Most of the range computes RAM parameter blocks, but the library also **programs the image engine directly** (verified, constant scan of 0x7E544AA9–0x7E576D58): 57 accesses to the engine registers 0x99400000–0x99405800 in 0x7E54DA7F (the body of the IRQ 102 handler 0x7E545269: reads 0x99404010, writes 0x99400008), 0x7E5574F7, 0x7E5576C2 and 0x7E55776E; and direct writes to the SYSCLK clock gates 0x988000D0/D4 (on) and 0x988000DC/E0 (off) in 0x7E54CE46, 0x7E54CE61, 0x7E54D07C, 0x7E54D44D and 0x7E54D475. How the RAM parameter blocks (job+572/+2592/+3904) reach the engine was not traced. Only the debug shells have strings (`img buff`, `img_l0`, `IMG_SYSTEM_ERR!!!`, `YC2 Recview RGB gamma…`). (A4 2026-11-09)

### 3.1 The job descriptor (verified field uses; meanings inferred)

| Field | Use |
|---|---|
| +84 | flag word: 0x2 = special path; 0x10000000 = CPU1 / sub lane; 0x800000 = extra geometry; 0x200000; read by every stage |
| +96 | pointer **P** to the image-parameter block, the same P = img_ctrl+96 as in section 09b. **P+79 = art/picture code**, P+81, P+88–90 (presets), P+97 |
| +178, +180, +182, +191 | status and result bytes |
| **+194** | **operation type 0–33**: the index into three dispatch tables. 09b: op 21 = copy/resize, op 30 = fill |

### 3.2 Components

| Range | Component | Entry points (callers) | Basis |
|---|---|---|---|
| 0x7E544AA9 | IMG init | ← Usr0 0x7E503DD4. Attaches interrupt handlers for **IRQs** 105, 106, 107, 108 and 102 at level 5 (0x7E463C8E → 0x7E44B57F, which rejects IRQ ≥ 125 with `!!Wrong IRQ Number`; ISRs 0x7E5451CB / 0x7E5451EB / 0x7E54520B / 0x7E54523A / 0x7E545269), then zeroes the control words of IRQs 107 and 108 (0x7E44B5E7). Its six IMG_END "create" calls (0x7E55EB2D) reach 0x7E449000 = `clr d0; retf`, a no-op, so those flags are not created at run time. Then buffers (0x7E54D59A) and two task starts (0x7E449541) | V (A4 2026-11-09) |
| **0x7E544BB5** | **`img_exec(job)`** | 28 sites in mov/rec/mcon/take/art/play. Picks the local lane (`img_l0` 0x7E575C72 → IMG0_LOCAL), the CPU1 twin (CPU id at 0x8050, job+84 bit 28) or a special path (op 11/12 → 0x7E545605) | V |
| 0x7E544CE5 | aligned-buffer `img_exec` wrapper; retries on results 11632/11633 | ← MOV 0x7E6D1464/0x7E6D664A/0x7E6D687E/0x7E6EFAB5, REC 0x7E7166A7, PLAY 0x7E945371 | V |
| 0x7E544D78 | wrapper → 0x7E564C35/0x7E564C88 | ← REC 0x7E717FE9, ART 0x7E72AFA1 | V |
| 0x7E545092, 0x7E545103 | job dumps (`%04X * %04X`, `SF,SIZE`) | ← MOV 0x7E6D1464, REC 0x7E7111BD/0x7E71121E | V |
| 0x7E5451CB–0x7E545275, 0x7E55EB2D–0x7E55EB65 | 0x7E5451CB…0x7E545269 = the five IMG ISRs (IRQ 105/106/107/108: a status helper 0x7E54D815 / 0x7E54D903 / 0x7E54D97C / 0x7E54DA0F, then IMG_END set; IRQ 102: 0x7E54DA7F); 0x7E55EB2D = IMG_END "create" (calls the no-op 0x7E449000), 0x7E55EB40 = wait (OlyEvWt 0x7E4490AF), 0x7E55EB5B = set (OlyEvSt 0x7E449083) | IRQ table (ISRs); internal | V (A4 2026-11-09) |
| 0x7E545276, 0x7E5453CA, 0x7E545590 | job builders: fill a 320-byte descriptor (0x20000000 flag, sizes, 2048, 100…) → **0x7E54D5E4** | internal | V |
| **0x7E54D5E4** | **job preparation**: work area (0x7E5503E8: one of 5 RAM areas 0x6050xxxx/0x6072xxxx by CPU, flags and op), then the **three op-type dispatches**: | | V |
| | (a) 0x7E5704ED → table **0x7E78D028** (31 builders 0x7E57302D–0x7E574EE7); | | V |
| | (b) 0x7E560ACF → table **0x7E789604** (34 entries, ops 0–33: op-type parameter-block handlers; the colour/tone role is inferred); | | V (dispatch); role I (A4 2026-11-09) |
| | (c) 0x7E550434 → table **0x7E74A3C8** (34 entries: geometry, 0x7E55044D default); | | V |
| | then 0x7E54880E | | V |
| 0x7E54880E–0x7E54CD97 | block builder A: one sub-builder per mask bit of the job flags (0x80000000, 0x40, 0x100000, 0x80004, 0x4010000, 0x2000, 0x10, 0x4000, 0x20000) | ← 0x7E54D5E4 | V (structure) |
| 0x7E546973–0x7E548755 | art CPU kernels (e.g. 0x7E5475FC = the ART_IMG_CF kernel of section 03; 0x7E548351 = mask-job builder of 09b) | art only | V (A4 2026-11-09) |
| 0x7E54875A–0x7E54880D | **IMG_ART_P task** (cfg 0x9006, CPU1) | task table 0x7E43D4F4 | V: it loops `ART_PROC_Q_R` and answers each message with code 0x1000 through `ART_PROC_Q_W`; it does no work itself |
| 0x7E54CE46–0x7E54D4B2 | **SYSCLK clock-gate writes**: 0x988000D0 (0x7E54CE46 ← buffer init 0x7E54D59A; 0x7E54CE61), 0x988000DC (0x7E54D07C), gate on 0x988000D0/D4 (0x7E54D44D ← 0x7E5574F7) and gate off 0x988000E0/DC (0x7E54D475). They write the registers directly, not through `clk_gate` 0x7E46A6FA (13f §2) | internal | V (bytes) (A4 2026-11-09) |
| 0x7E54D4B3–0x7E54E1xx | `img buff` shell (help text at 0x7E54D4F2; dump/alloc) and IMG buffer bookkeeping. It also holds **0x7E54DA7F**, the IRQ 102 handler body, which reads the engine status 0x99404010 and writes 0x99400008 (14 engine-register accesses), and the callers 0x7E54DE90 / 0x7E54DFF7 of the engine programmer 0x7E5574F7 | U_SHELL tables 0x7E7327B0/0x7E7333C0 → 0x7E54D4D9; ISR 0x7E545269 → 0x7E54DA7F | V (A4 2026-11-09) |
| 0x7E5508FA–0x7E550D36, 0x7E55871C | **constant/table getters**: `mov imm32,a0|d0; retf` (3 instructions), or a clamped index into a {u16,u16} table (0x7E550B1D → 0x7E74A518, the 09b aspect table) | rec, mov, art (fade times 500/2000 ms at 0x7E550CDF…), mcon | V |
| 0x7E550DFD–0x7E551182 | request validator/dispatcher (errors 0x7301/0x7303) | play 0x7E93DDAA/0x7E94439F, take 0x7E5BE9B9, PTP overlay 0x7F08B75D… | V (role I) |
| **0x7E5512A5–0x7E5562D3** | **tone/colour curve maths**; see §3.3 | 0x7E560B40/0x7E560B61 (REC_IMAGE 0x7E71274B, MOV_COLOR_CALC1 0x7E6D0E51); **0x7E5562D3** (4.4 kB, ← MOV_COLOR_HYST 0x7E6D10E7) | V |
| 0x7E557410–0x7E55749A | calc work-area alloc and free (0x7E507325 / 0x7E507333; 512+512+3028-byte split) | MOV 0x7E6D0C03/0x7E6D0D73, REC 0x7E7125C3/0x7E71274B | V |
| 0x7E5574F7–0x7E5577A5 | **image-engine register programming**: 0x7E5574F7 (22 accesses, e.g. 0x7E557514 `mov d0,(0x99400000)`; calls the clock-gate helper 0x7E54D44D) with 0x7E5576C2 (8) and 0x7E55776E (6); registers 0x99400000–0x99405800 (0x994000xx, 0x994040xx–0x994041BC, 0x99405200–0x99405800) | 0x7E54DE90, 0x7E54DFF7 | V (bytes); unit meaning I (A4 2026-11-09) |
| 0x7E5577A6–0x7E55807A | **JPEG header writer**: FF D8, two 64-byte DQT tables from the caller, DHT tables 0x7E74A6E8…, 654/660-byte header; two variants (0x7E5577C2 / 0x7E557915) | 12 sites: mov, rec, play, PTP overlay | V (bytes FF D8; DHT per §08) |
| 0x7E55866A–0x7E55E97D | Exif-writer helper: fills three tagged records (magic 0x4F494D43, ids 0xDC090001–3) in the writer's work area +10420; large table-driven fillers (0x7E558BE6, 0x7E559BE5, 0x7E55D8C4) | ← Exif writer 0x7E708F24 only | V (structure); content I |
| 0x7E55EB66, 0x7E55EBE2, 0x7E55EBF6 | **colour fill**: 0x7E55EB66 converts R,G,B → Y,Cb,Cr with BT.601 coefficients (`udf00` 19595/38470/7471, −11056/21712/32768, 32768/−27440/−5328) and fills; 0x7E55EBF6 = fill op 30 (09b) | art 0x7E71EB36…, play 0x7E94516D; 0x7E55EBE2 ← api 0x7E68DB89/0x7E68DF91, mov 0x7E6EC40C, rec 0x7E715B0D, play 0x7E8F7616 | V (the coefficients also prove `udf00 imm` = multiply) |
| **0x7E55ECD8–0x7E55F97C** | **pixel-defect correction kernels**: replace a pixel from its same-colour Bayer neighbours (±2 columns, ±2 rows). 0x7E55ECD8 picks the table by bit depth (24,a2): 16 → 0x7E7892B0, 12 (packed, 10 px per 16 B, unpacker 0x7E55F524) → 0x7E789270, others → 0x7E789230 (8-bit); 9/10/14 log an error. Each table has 16 slots: 15 kernels and an empty `retf` stub in slot 15 (0x7E55F1E7, 0x7E55F521, 0x7E55F97A; the database misses all three). The slot index is a 4-bit mask of missing neighbours (0x7E55EF52: x<2 → 4, x+3>w → 1, y<2 → 2, y+3>h → 8), so the mean of all 4 neighbours is slot 0 only; other slots use the neighbours that exist. Lists from prm 0x70C4/0x70D4 (ROM) and **0x7044 `PRM_CCD_FIRST_PIXELDEFECT_ADDRESS`**, 0x7052 `…_SIZE`, **0x7144 `…_ADDRESS2`**, 0x7084/0x7092 (iterator 0x7E55ED89) | ← IMG_PRECON cmd 0 (0x7E55FAE8), MOV 0x7E6D0805 | V (A4 2026-11-09) |
| 0x7E55F97D, **0x7E55F9B6** | **IMG_PRECON** start / task: commands 0–4 → 0x7E55FAE8 (defect correction), 0x7E55FE1E, 0x7E55FF91, 0x7E55FFA3, 0x7E580A54 | task table 0x7E43905C; REC 0x7E7188D2 calls 0x7E55FA55 directly | V; corrects 03's "pre-conditioning (inferred)" to **pixel-defect (Pixel Mapping) correction** |
| **0x7E560ACF–0x7E5625xx** | **op-type colour/tone handlers**, table 0x7E789604; see §3.4 | via 0x7E54D5E4 | V (dispatch); the colour/tone role is I (A4 2026-11-09) |
| 0x7E5625DC–0x7E56BA7A | **parameter-block setters** (two families of 17, called by 0x7E56224C and 0x7E562404). F006 = 0x7E56B4F5 | internal | V |
| 0x7E564C35–0x7E56DA08 | per-unit computations, e.g. 0x7E565598 / 0x7E566C94 (art-code branches 181–184, 09b), 0x7E56DA08 **YC2 Recview RGB gamma** (checks R=G=B; ← setter 0x7E56B6D1 under mask 0x10) | internal | V for the call edges |
| 0x7E56E495–0x7E5700xx | value-mapping switches: {value, label} tables 0x7E78C6F0 and 0x7E78CE34 jump to small label stubs (0x7E56E4FD…, 0x7E56FE95…) | internal | V (tables); the database lists the stubs as functions |
| 0x7E574F49–0x7E575C09 | rec/movie/playback helpers (0x7E574F49 ← REC 0x7E70D737; 0x7E574FA4/AC ← MOV 0x7E6CBC2C; 0x7E574FB4 ← PLAY 0x7E93BFA3) | | V (callers) |
| 0x7E575C3F–0x7E575F7B | poll helper 0x7E575C3F; `img_l0` post 0x7E575C72 (send/receive 0x7E436467 / 0x7E434C5C, a mailbox by call shape (I); error `IMG_SYSTEM_ERR!!!`); the **IMG0_LOCAL task** 0x7E575D41 (CPU0): receive job → marshal it into shared RAM 0xA07500BC… (0x7E575E13 copies 196 B and the +100/+96 sub-blocks and fixes the pointers; no callees) → send it on 0x7E43EE94 to the **CPU1 twin 0x7E575DB8**, which runs `img_exec` 0x7E544BB5 and replies on 0x7E43EE96 → relay the twin's result on 0x7E43ECBA | task tables 0x7E438DBC (IMG0_LOCAL), 0x7E43D5F0 (twin, cfg 0x900F) | V (A4 2026-11-09) |
| 0x7E575F92–0x7E576D00 | float-heavy curve and colour helpers (`log`, `pow`, soft-float) under op handler 0x7E561A9F → 0x7E56BA97 → 0x7E576B1F | internal | V (edges) |

### 3.3 Tone-curve maths (C1 F005)

All verified unless marked:
- **0x7E5524CA** sets up a **natural cubic spline**: knot spacing h, slopes `((y[i+1]−y[i])<<10)/h`, then forward elimination and back substitution of the tridiagonal system into a work array.
- **0x7E5525F0 (F005)** evaluates it. It binary-searches x in the u16 knot table, evaluates the cubic in 20-bit fixed point and rounds (`+0x80000 >> 20`) to a u16.
- **0x7E553271** builds a **10-bit curve**:
  - the endpoints are 0 and 1023 (knots at ctx+3832 for x and ctx+3842 for y);
  - the interior knots come from bytes ctx+3939…3962 (scale 384, offsets 17/25/37 chosen by a byte at +40);
  - it calls the spline, and its caller clamps the result to 0..1023.
- **0x7E55408B** (1.9 kB) applies signed −128..127 adjustments (fields +3967…3972) through the same spline.
- **0x7E555DF4** (← 0x7E560B40) and **0x7E556155** (← 0x7E560B61) drive the getters 0x7E5512A5–0x7E551375 and the builders above.

**Reading (inferred):** 0x7E560B40 builds the gradation/tone curve for still development (REC_IMAGE) and for the movie i-Finish colour task (MOV_COLOR). 0x7E560B61 is the lighter variant used by MOV_COLOR only. Which picture-mode setting fills bytes +3939…3964 was not traced.

### 3.4 Op-type colour/tone handlers (table 0x7E789604) and F006

- **Dispatch (verified):** `0x7E560ACF: movbu (194,a1),d0; mov 0x7E789604,a2; asl2 d0; mov (d0,a2),a2; calls (a2)`. The two sibling dispatchers have the same shape: 0x7E550434 (table 0x7E74A3C8, exactly 34 entries) and 0x7E5704ED (table 0x7E78D028).
- **Handlers by op type (verified):**

  | Op types | Handler |
  |---|---|
  | 0, 1, 2, 4 | 0x7E560B85 |
  | 3, 32 | 0x7E560DDB |
  | 5 | 0x7E560FE3 |
  | 6 | 0x7E5610BA |
  | 7, 8 | 0x7E56112E |
  | 9, 10 | 0x7E5614D7 |
  | 11 | 0x7E5617B4 |
  | 12 | 0x7E561824 |
  | 13, 19, 20, 21, 23, 28 | 0x7E561A9F |
  | 15 | 0x7E561851 |
  | 16 | 0x7E561978 |
  | 22 | 0x7E561EB7 |
  | 24 | 0x7E561F90 (empty) |
  | 25 | 0x7E5621B5 |
  | 26 | 0x7E56210F |
  | 33 | 0x7E562032 |
  | **14, 17, 18, 27, 29, 30 (fill), 31** | **0x7E560B82 = `retf`**: no colour parameters |

- **Handler pattern (verified for 0x7E560B85):**
  1. The handler starts with `movm [d3,a2,a3],(sp); add -2xx,sp`.
  2. It builds an enable mask from P fields. P+79 ∉ {96, 97, 165, 166} sets 0x80. In 09, 96/165 are Dramatic Tone I/II; 97/166 are inferred to be its variants. P+79 ∉ {117, 121} sets 0x800. P+90 and P+81 also set bits.
  3. For each job flag it calls a block builder on a fixed RAM block and copies the block into the job:

     | Job flag | Builder | RAM block | Copied to |
     |---|---|---|---|
     | 0x40 | **0x7E56224C** | 0x6050E08C | job+572 (487 words) |
     | 0x100000 | **0x7E562404** | 0x6050E828 | job+3904 (418 words) |
     | 0x80 | 0x7E5625DC | 0x6050FCD4 | job+2592 (91 words) |

     The previous-block pointers are cached at 0xA07500B4/B8, so a rebuild can be skipped.
- **Block setters (verified pattern):** 0x7E56224C and 0x7E562404 each call 17 small setters in 0x7E56B3EA–0x7E56BA7A. Each setter:
  - tests one bit of the enable mask;
  - fills its sub-block (often through a helper);
  - compare-and-stores fixed words;
  - **returns 1 if anything changed** (a dirty flag).

  **F006 = 0x7E56B4F5** is one of them. Mask 0x2000 → sub-block +140 (0x7E56BDE9). It then forces +188 = 0x03FF0000, +192 = 0x100D, +196 = 0x1FFE2, +200 = 0x0FA00040, +204 = 0.
- **Inferred:** each sub-block is the register image of one image-engine unit, and the mask bits are unit enables (example: 0x10 = RGB gamma, from the gamma setter 0x7E56B6D1). No unit other than RGB gamma has a name.

### 3.5 Relation to picture modes and art filters (section 09)

- The library sees picture mode and art filter only through **P** (job+96):
  - the art code at P+79 (same field as 09b `art_set_img_ctrl_param`);
  - the presets at P+88–90 (09b: Watercolor P+89 = 10–13).
- Code compares on art codes 96/97/165/166 and 117/121 (0x7E560B85). 09b lists compares on 181–184 (0x7E5659EB, 0x7E566813, 0x7E56826A, 0x7E5689A6) (verified). The table that P+89 indexes is still not found.
- Contrast, sharpness, saturation and gradation of the normal picture modes probably reach the curve bytes ctx+3939… and the setters (inferred; the writers of those fields were not traced).

## 4. Other small blocks next to these

- **Pixel-defect (Pixel Mapping) correction** inside IMG (§3.2). It is the CPU half of the menu item "Pixel Mapping" (string id 207), inferred from the prm names.
- **RGB→YCbCr** BT.601 fixed-point converter 0x7E55EB66 (§3.2).
- **Cubic spline** 0x7E5524CA / 0x7E5525F0: the only spline code found in this area.
- The C runtime has **no** CRC, sort (`qsort`, `bsearch`), `div`/`ldiv` or 64-bit integer helpers. Integer division is native `div`/`divu` (verified: absent from the catalogue; not searched for elsewhere in block 0).
- Next to the runtime: 0x7E501C5B–0x7E501E8C USRTEST tasks A–D and 0x7E501F0D `dbgall` (already in section 01).

## 5. Corrections

1. **firmware-map C1 block:**
   - The C runtime is **0x7E4FE000**–0x7E501C5A, not 0x7E4F8000.
   - The image library is **0x7E544AA9–~0x7E576D58**, not ~0x7E54D000–0x7E578000. It contains IMG_PRECON, IMG_ART_P, IMG0_LOCAL and art CPU kernels.
   - 0x7E576D59–0x7E579A7F is the separate `buff` manager.
2. **Map regions table:** the row 0x7E4E0000–0x7E521020 does not mention the C runtime. The row 0x7E521020–0x7E621020 ("firmup … TAKE") misses the IMG library and the `buff` manager. 0x7E4C90CA–0x7E4FDFFF is padding.
3. **Section 03 / 02 (IMG_PRECON):** the role is pixel-defect correction from the PIXELDEFECT prm lists (verified), not generic "pre-conditioning".
4. **Section 09b** calls 0x7E54xxxx–0x7E56xxxx the "image-engine driver". Most of it is parameter computation in RAM, but the IMG library also programs the image engine at 0x99400000–0x994058xx (functions such as 0x7E54DA7F and 0x7E5574F7) and writes the SYSCLK clock gates 0x988000D0/D4/DC/E0 (§3, §3.2). So "driver" is right for part of the range; 09b needs no change. (A4 2026-11-09)
5. **Section 08** gives the float helpers as 0x7E5018BC–0x7E501972. The full set is 0x7E500F62–0x7E501AAB (§2.2; the last helper 0x7E501A2C ends with `retf` at 0x7E501AA9, and `tan` starts at 0x7E501AAC). The names "fadd = 0x7E5018BC" or similar must not be assumed: **0x7E5018BC is fsub and 0x7E5018C3 is fadd** (inferred, strong). (A4 2026-11-09)
6. **C1 F070** described 0x7E5018E8 as "the float helper": it is fmul (confirmed).

## 6. Open questions

1. The exact semantics of opcodes `f6 2x/3x/4x/5x/6x`, `fb e0 80 00` and `f9 4x`: which unit executes them, and how does it round?
2. The names of IMG op types 0–33 beyond 21 (copy) and 30 (fill), and what each of the 31 builders in table 0x7E78D028 programs.
3. Which unit each block-setter mask bit (0x10, 0x2000, …) controls; where the RAM parameter blocks (job+572/+2592/+3904) are handed to hardware.
4. Which settings fill the tone-curve bytes ctx+3939…3972, and how the picture-mode contrast/gradation map onto them.
5. The meaning of the three Exif records (magic 0x4F494D43, 0xDC09000n) built by 0x7E55866A.
6. IMG_PRECON commands 1–4 (0x7E55FE1E, 0x7E55FF91, 0x7E55FFA3, 0x7E580A54).
7. Whether another copy of a runtime exists in the overlays (0x7F0CA6B8 is a separate hex/decimal `atoi` wrapper that calls 0x7E500832).
