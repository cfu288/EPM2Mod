# Focus peaking for the E-PM2: how the E-P5 does it, what the E-PM2 has, first probe

Date: 2026-11-14. Status: desk research and one draft patch spec. Nothing was flashed.

Labels: **V** = verified (read from the firmware bytes, or run in the emulator). **I** = inferred.
**U** = unknown; each one has a probe in §8.

Addresses: E-PM2 = firmware 1.6 block 0, runtime base 0x7E421020. E-P5 = firmware 1.8 block 0.
Its runtime base is **0x7E101020** (**V**: 90 of 300 sampled string addresses are the target of an
aligned pointer word at this base; the next best base has 17). The E-P5 notes in
`REPOS/thrains0220-byte_ep5-fw-reverse` use the container address 0x402C0020 and call 0x7E…
"mask ROM". That reading is wrong: 0x7E… is block 0 itself.

Terms:
- **Live view (LV)**: the moving picture on the screen before a shot. The firmware calls it "through".
- **mov layer**: the firmware module (`mov_*.c`) that runs live view and movie frames.
- **IMG library**: the code that drives the image processor. A job has a parameter block `IMG_PARAM`.
- **Art code** (`ucExpose`): one byte in `IMG_PARAM` that names the picture mode or art filter.
  Key Line is 163 (164 in the movie variant).
- **Stage list**: for each job the IMG library writes a list of small numbers. Each number is one
  hardware stage of the image processor.
- **Line image** ("line_yc"): the edge picture that Key Line makes from the frame.

## 1. Short answer

1. E-P5 peaking is **Key Line's edge pipeline with other parameters** (**V**). The edge detection
   is done by the image processor (stage lists and tables), not by CPU code (**V** for the stage
   lists; no pixel loop was found in any peaking branch).
2. The E-PM2 has every layer that peaking uses, in an older state: the live-view art path, the
   Key Line line image, the art task with the Key Line passes, the MF-assist call, the
   live-view update call. The peaking branches are missing in all of them (**V**).
3. A full port touches about 35 functions in five layers (§5). It is new code of about 2.5 to 4 KB,
   or more if whole functions are moved. This is a job of weeks, not days (**I**).
4. The first camera probe is small: 2 hooks and 38 bytes of new code make live view run Key Line
   while the Picture Mode is Muted (§7). It is written as a draft spec, applies, passes the
   free-space check and passes the emulator check. It answers the first open question: can the
   live-view art path run while the camera is not in an art mode?

## 2. Material and method

- E-PM2: `build/map/` (function database), `build/blocks/…block0.bin`.
- E-P5 1.8: `REPOS/thrains0220-byte_ep5-fw-reverse/decoded/00_0100_402c0020.decoded.bin`. A function
  database was built in scratch: `python3 tools/fwmap.py --fw /tmp/scratch/peaking/ep5/EP5.BIN
  --base 0x7E101020 --out /tmp/scratch/peaking/ep5 build` (the decoded block was first copied to
  `/tmp/scratch/peaking/ep5/blocks/EP5.BIN.block0.bin`, which the tool takes as its block cache).
  Result: 81,759 functions.
- Pairing (`scripts/pair.py`): the interval work's method. Each function becomes a fingerprint with
  addresses and large numbers replaced by placeholders. Pairs come from (1) a fingerprint that is
  unique in both bodies, (2) the same unique set of debug strings, (3) the same position in the
  call list of two paired callers. Result: **36,912 pairs** (21,940 identical after normalising,
  4,767 by strings, 10,205 by call order).
- `scripts/fdiff.py EP5_MAP EPM2_MAP P5_FN PM2_FN` prints the instructions that differ.
- `scripts/inventory.py` lists the E-P5 functions that carry a peaking mark, with their pair
  (`results/inventory.txt`).
- GitHub sweep (`gh search code` for `ART_EXPOSE_PEAKING`, `setPeakingInfo`, `startPeaking olympus`,
  `PEAKING_COLOR_WHITE`; `gh search repos` "olympus focus peaking firmware"): no Olympus hit.
  Local repos: `cmdada_em10-fw/notes/focus.md` only says that the E-M10 has `startPeaking` and
  `ucPeakingType`. `nsud-dev_olympus-firmware-notes` shows that on the E-M5 III (a later processor)
  peaking is a block of the display controller (registers PEAK1–14). The E-P5 does it another way
  (this file).

## 3. How E-P5 peaking works

### 3.1 Top: setting and trigger

| Fact | Evidence | Label |
|---|---|---|
| The peaking colour is the third argument of the MF-assist start call: `OlyHfwOpeShoot::startMfAssist(time, rate, color)`; colour 0 none, 1 black, 2 white | E-P5 0x7E64BFF2 (asserts "Param rate Invalid", "Param color Invalid"); debug command `startMFAssist` 0x7E67F1C1 prints "usage: sdk api %s time rage color" and the three colour names | V |
| The E-PM2 call has time and rate only | E-PM2 0x7E9889EB; its debug command prints the zoom rates only | V |
| So peaking belongs to MF Assist: the focus-ring event starts it, as it starts the magnified view | the same API carries both | I |
| The shooting sequence object has three functions: `setPeakingInfo` 0x7E796D0F, `stopPeaking` 0x7E796DA0, `startPeaking` 0x7E796E39 (names from their debug strings) | strings 0x7E953262–0x7E95333C | V |
| `startPeaking` does nothing when the colour is none, when "operation" (info 15) is not 1 ("nop OPERATION_FN"), or when no restriction bit is set for the caller | 0x7E796E39 | V |
| Peaking is held off by "restriction" bits (info 240). Callers pass bit 0x20 and bit 0x10 | 0x7E77666C, 0x7E777E59, 0x7E77F077 and others | V |
| Which state owns which bit (capture, magnified view, movie, playback) | not traced | U |
| The menu item, the setting id and where the colour is stored | not traced | U |
| A button function "Peaking" | the string "nop OPERATION_FN" shows that a Fn operation exists; the table was not traced | I |
| In 1.8 the colours are white and black only | two art codes, two colour values (§3.3) | V |

### 3.2 Middle: the live-view update

| Step | E-P5 | Label |
|---|---|---|
| `CapThr::execUpdateThrough` builds the live-view update request. When the peaking flag of the CapThr object is set (object +388) and no restriction applies (object +392 & 240), it sets bit 0x8000 in the request's mode word and prints "[CapThr]execUpdateThrough() set Peaking" | 0x7E6FF6F4, lines 0x7E6FF72A–0x7E6FF761 | V |
| `api_tft_Update_Through` copies the request into the command block 0x605DE220. Bit 0x8000 becomes bit 0x4000 of the command's mode word | 0x7E36630A, lines 0x7E3664B8–0x7E3664CA | V |
| The mov layer keeps one record per live-view slot. The E-P5 record is 140 bytes; byte +136 is the peaking request. The E-PM2 record is 136 bytes and has no such byte | accessor E-P5 0x7E3AC9B8 (`× 140`) ↔ E-PM2 0x7E6CFFBD (`× 136`); copy function 0x7E3AC9E8 ↔ 0x7E6CFFED | V |
| The path from command bit 0x4000 to record byte +136 | not traced | U |
| Flag setter 0x7E3AD26C sets the byte 0x605E95C2 ("peaking active") to 1 when: the caller's flag bit 0 is clear, word 0x605EA200 is 0, record +136 is 1, the live-view kind is not 2 and not 5, and 0x605EAF3C is not 1 | 0x7E3AD26C; called from 0x7E3CA4B5 | V |
| So peaking is off for some live-view kinds and while flag bit 0 is set. Bit 0 selects the movie variants of the art codes elsewhere in the same file, so "off while a movie records" | the conditions above | I |
| Getter of the flag: 0x7E3AD2B3, 9 callers in the mov layer | call list | V |

### 3.3 Bottom: the picture

While the flag is 1 the mov layer changes these things (all **V**, each is a diff against the paired
E-PM2 function):

| Where (E-P5 ↔ E-PM2) | What peaking changes |
|---|---|
| colour-tone getter 0x7E3A888A ↔ 0x7E6CBFD3 | writes picture mode **201** (colour 1) or **202** (other) to the caller's mode byte (helper 0x7E3AA601) and returns 3 |
| expose setter 0x7E3A243B ↔ 0x7E6C610B | mode byte 201 → art code **188**; 202 → **189**. The mov art table names them `ART_EXPOSE_PEAKING_WHITE` (0x2BC) and `ART_EXPOSE_PEAKING_BLACK` (0x2BD), class 2. Key Line (0x2A3) and Watercolor (0x2B5) are class 2 too |
| job setup 0x7E3A390B ↔ 0x7E6C74BE | the frame's own job gets `ucExpose` = 3 and `ucColor` = 2: the picture below the peaking lines is rendered as a plain picture mode, not as an art filter |
| `mov_art_set_line_yc_param` 0x7E3AA34B ↔ 0x7E6CD9C5 | art code 188 takes Key Line's branch (same line buffers 0x605E91A0/A4, same flags), then sets `ucArtLpf` = 15 and `ucProcCount` = 11 (Key Line: 8 and 3) |
| `mov_art_set_color_yc_param` 0x7E3AA1EA ↔ 0x7E6CD892 | 188/189: `ucProcCount` = 9 and the new field `ucPeak` = 1 (white) or 2 (black) |
| `mov_art_set_artpacket` 0x7E3A94FB ↔ 0x7E6CCBE1, `set_out_area_param` 0x7E3A4036 ↔ 0x7E6C7BB0, frame-time table 0x7E3A8A7A, 0x7E39F729, 0x7E3A1CBD, 0x7E3A9367, `img_param_set_ucType` 0x7E3B7B1C ↔ 0x7E6DAE68 | each has a branch for the flag or for 188/189 (not read line by line) |

`IMG_PARAM` (**V**, from the two debug dump functions 0x7E3AF511 ↔ 0x7E6D2908): every field from
`shSv` on sits 8 bytes higher in the E-P5 (`ucExpose` 87 ↔ 79, `ucArtLpf` 97 ↔ 89, `ucProcCount`
98 ↔ 90, `ucType` 107 ↔ 99). `ucPeak` is at 109 in the E-P5. The E-PM2 has no `ucPeak` text and no
read of such a field; whether byte 101 of its block is free is **U**.

IMG library (E-P5 0x7E2083F4–0x7E23B04F ↔ E-PM2 0x7E544AA9–0x7E576D58; 629 of 816 functions are
identical after normalising). Peaking adds (**V**):

| E-P5 ↔ E-PM2 | Change |
|---|---|
| stage-list builder 0x7E23777D ↔ 0x7E5735A9 (1061 ↔ 957 B) | `ucProcCount` 11: stage 14 is left out (two places) and helper 0x7E234B51 (identical in the E-PM2: 0x7E570B4D) is called with 0 before stage 25 |
| stage-list builder 0x7E2383DA ↔ 0x7E574196 (222 ↔ 94 B) | a new branch for jobs with flag 0x10000000 (stages 8, 9, 23, 30) and `ucProcCount` 10/12 (stage 9 or 3 added) |
| curve chooser 0x7E232FF6 ↔ 0x7E56F113 | `ucProcCount` 11: two 12-byte curves, white 0x7E457998 / 0x7E4579A4, black 0x7E4579B0 / 0x7E4579BC. Both pairs hold the same bytes: `00 02 0a 19 2e 46 60 7f 7f 7f 7f 7f` and `ff f5 e6 d2 be 9b 78 50 50 50 50 50` |
| filter-record chooser 0x7E228AA4 ↔ 0x7E564DB8 | two new indexes, 18 and 19, chosen by `ucPeak`: records `00 20 00 00` (no smoothing) and `00 0c 08 02` (the common 12-8-2 kernel) at 0x7E452C30–3C |
| filter setup 0x7E235DF9 ↔ 0x7E571CAB and 0x7E235BE2 ↔ 0x7E571AEF | `ucArtLpf` 14 is a new case (stage 5 with record 18); the default branch, which 15 takes, is longer (not read line by line) |
| three parameter-cache functions 0x7E22E341, 0x7E2329FD ↔ 0x7E56EB95, 0x7E23353D ↔ 0x7E56F63C | `ucPeak` is one more key of the cache for `ucProcCount` 9–12 |
| new 0x7E21474E (19 B) | returns the line gain: 0x0800 for colour 1, 0xF800 for colour 2 |

The stage numbers that the new branches use (1, 3, 5, 8, 9, 14, 16, 22, 23, 25, 27, 30, 31) are
written by E-PM2 builders too (**V**; stage 23 at 0x7E573A3F and 0x7E574AC0). The function that
runs a stage list is identical in both bodies (0x7E23459A ↔ 0x7E5705F2, **V**). So peaking needs
**no stage that the E-PM2 code never uses** (**V** for the numbers; that each stage accepts the
peaking parameters on this body is **I**).

Art task (`art_filter_19_artclearline.c`, the Key Line module; E-P5 passes 1, 7, 8, 9, 10 ↔ E-PM2
0x7E725A1B, 0x7E7262F1, 0x7E7264A9, 0x7E7266D9, 0x7E7267D9; together +487 B): each pass has a
branch for 188/189 (**V**). Pass 9 (0x7E40765C) is the overlay: for peaking it sets the job's
combine mode (job +37) to **3** and the coefficient (job +32) to **+2048 (white) or −2048 (black)**.
Key Line uses mode 2 and 256. So white and black are the same line image added to or subtracted
from the picture (**V** for the values, **I** for the meaning of mode 3).

`art_GetFilterType` 0x7E3FCB10 ↔ 0x7E71BD94: the E-P5 version accepts picture modes up to 202 and
returns 188 for 201 and 189 for 202 (**V**).

### 3.4 Capture, magnified view, movie

- Capture: "not Start Seq under Peaking" (0x7E7962A1) and "not Start OlyApi under Peaking"
  (0x7E78C673) show that the sequence layer refuses some starts while peaking is on, and
  `stopPeaking` is called with a restriction bit before them (**I**; the order was not traced).
  Stills cannot get peaking lines by accident: the lines exist only for art codes 188/189, which
  only the live-view path produces (**V**).
- Magnified view: the same API call carries the zoom rate and the colour, so both can be on together
  (**I**). Which live-view kinds 2 and 5 are (the two kinds that switch peaking off) is **U**.
- Movie: off while flag bit 0 is set (**I**, §3.2).

## 4. E-P5 ↔ E-PM2 match table

Quality: **same** = identical after normalising; **near** = paired by strings or call order, differs
only by the listed branches and by shifted struct offsets; **none** = E-P5 only.

| Piece | E-P5 | E-PM2 | Quality |
|---|---|---|---|
| `OlyHfwOpeShoot::startMfAssist` | 0x7E64BFF2 | 0x7E9889EB | near (no colour argument) |
| `isMfAssistExec` | 0x7E64D661 | 0x7E98A56F | near |
| `setPeakingInfo` / `stopPeaking` / `startPeaking` | 0x7E796D0F / DA0 / E39 | – | none |
| `CapThr::execUpdateThrough` | 0x7E6FF6F4 | 0x7EA18853 | near |
| `api_tft_Update_Through` | 0x7E36630A | 0x7E68D576 | near |
| command sender behind it | 0x7E36625B | 0x7E68D4C7 | same |
| live-view record accessor | 0x7E3AC9B8 | 0x7E6CFFBD | near (140 ↔ 136 bytes) |
| live-view parameter struct getter | 0x7E3CA39B | 0x7E6ECFB6 | same |
| peaking flag setter / getter | 0x7E3AD26C / 0x7E3AD2B3 | – | none |
| mov colour-tone getter | 0x7E3A888A | 0x7E6CBFD3 | near |
| mov expose setter | 0x7E3A243B | 0x7E6C610B | near |
| mov art table (`MODE_EXPOSE_*` records) | 0x7E4F2D30, 46 rows | 0x7E7FE240, 44 rows | same rows; 2 peaking rows missing |
| art record lookup | – | 0x7E6CC153 | (pair not looked up) |
| `mov_art_set_line_yc_param` | 0x7E3AA34B | 0x7E6CD9C5 | near |
| `mov_art_set_color_yc_param` | 0x7E3AA1EA | 0x7E6CD892 | near |
| `mov_art_set_artpacket` | 0x7E3A94FB | 0x7E6CCBE1 | near |
| Key Line line-buffer allocation | (in 0x7E3A4036) | 0x7E6CD4B7, called from 0x7E6C7BB0 when the art record id is 163 or 164 | near |
| IMG stage-list runner | 0x7E23459A | 0x7E5705F2 | same |
| IMG stage-list builders | 0x7E23777D, 0x7E2383DA | 0x7E5735A9, 0x7E574196 | near |
| IMG curve chooser | 0x7E232FF6 | 0x7E56F113 | near |
| IMG filter-record chooser | 0x7E228AA4 | 0x7E564DB8 | near |
| Key Line art passes 1, 7, 8, 9, 10 | 0x7E40684F, 0x7E407152, 0x7E4073A0, 0x7E40765C, 0x7E4077BD | 0x7E725A1B, 0x7E7262F1, 0x7E7264A9, 0x7E7266D9, 0x7E7267D9 | near |
| `art_GetFilterType` | 0x7E3FCB10 | 0x7E71BD94 | near |
| `IMG_PARAM` dump | 0x7E3AF511 | 0x7E6D2908 | near (`ucPeak` line missing) |

## 5. What is missing in the E-PM2, and how big it is

`results/inventory.txt` is the full list. By layer:

| Layer | Functions to change | Extra bytes in the E-P5 versions | New data |
|---|---|---|---|
| IMG library | 9 (2 builders, curve chooser, record chooser, 2 filter setups, 3 cache functions) + 1 new | about 800 | 48 B curves, 16 B records |
| mov layer | 12 + 3 new small ones (flag setter, getter, mode helper) | about 600 | 2 art-table rows (the 44-row table has no room: move it, 46 × 16 B, or hook the lookup) |
| Art task (Key Line module) and `art_GetFilterType`, art list 0x7E3FD03F | 7 | about 630 | – |
| Live-view update (`CapThr`, `api_tft`) and the peaking byte of the live-view record | 3 | about 100 | one RAM byte in place of record +136 (the record cannot grow) |
| Sequence layer and API (start/stop/set, the colour argument, restriction bits) | 3 new (433 B) + their callers (not counted) | 500 to 1000 | – |
| Menu / button | not sized | – | – |

Sum: about **2.5 to 4 KB** of code (**I**). The "extra bytes" are size differences of paired
functions; they include E-P5 changes that are not peaking (other new art modes), so they are an
upper bound per function and not exact.

How the bytes get in: a changed function cannot grow in place. Either each new branch becomes a
hook (a 5-byte jump to new code and back; about 35 to 45 hooks), or the changed function is copied
whole to free space with the E-P5 text and its callers are re-pointed (the changed functions sum to
about 15 KB). The interval work used both forms.

Space: the camera-proven code area 0x7ECB0888–0x7ECB1000 has 285 bytes left (0x7ECB0EE3–0x7ECB1000).
The port needs one of the 17.5 KB of statically checked areas in `docs/code-space-map.md`. They
have never run code. `docs/feasibility.md` lists the probe for that.

Settings and trigger without menu work (evaluation):

| Option | Work | Verdict |
|---|---|---|
| Peaking on whenever MF Assist magnifies (hook `startMfAssist` / `endMfAssist`, 0x7E9889EB / 0x7E9830E0, to set and clear one RAM byte) | 2 hooks | Best first trigger. It is the E-P5's own trigger point. MF Assist needs a lens that reports the focus ring |
| Replace one Fn-button function | the button-function table was not traced | Possible later; **U** |
| A new menu row, as the interval patch inserted one | four linked tables, 31 row constants (interval README §3.1) | Last; not needed for a working feature |
| A build-time trigger on one Picture Mode (probe A uses this) | none | For probes only |

A shorter route than the full port (**I**, to be decided by probes B and C): write "E-PM2 peaking"
from Key Line's own parts and skip the IMG changes. Key Line's line job already makes the edge
image with the stock stage list (`ucProcCount` 3). Only the overlay pass and the picture below it
change: plain picture mode below (as E-P5 0x7E3A390B does), and pass 9's mode and coefficient
(job +37, +32). That is about 6 hooks and under 300 bytes, and fits the proven area. It gives the
Key Line edge threshold, not the E-P5's tuned one.

## 6. Steps

| Step | Proves | Changes | The user should see |
|---|---|---|---|
| **A** (draft spec ready, §7) | the live-view art path runs outside an art mode, with the line buffers | 2 hooks, 38 B of code | Picture Mode Muted: live view looks like Key Line (flat colours, dark outlines). The photo is a normal Muted photo |
| **B** | the overlay stage accepts a plain picture below the lines | in Key Line pass 9 (0x7E7266D9): job +37 and +32 as the E-P5 sets them (3 and ±2048), and the frame job's `ucExpose` / `ucColor` forced to a plain mode at the place that pairs with E-P5 0x7E3A3AA6 (in 0x7E6C74BE); about 4 hooks, about 80 B | Muted: a normal live-view picture with white (or black) lines on edges. This is already usable peaking with Key Line's threshold |
| **C** | the E-P5 line parameters work on this body | port of the IMG branch for `ucProcCount` 11 (builder 0x7E5735A9: 3 sites; curve chooser 0x7E56F113: 1 site + 48 B) and `ucArtLpf` 15 | finer lines that follow focus more sharply than in B |
| **D** | trigger | `startMfAssist` / `endMfAssist` hooks set a RAM flag that replaces the Muted test | lines appear while the focus ring turns, with or without magnification |
| **E** | full port | the rest of §5 | as the E-P5 |

B and C need code space beyond the 285 proven bytes if they are built together with A's code and
the pinned build. B alone fits.

## 7. Probe A: Key Line live view while Picture Mode is Muted

Draft spec: `specs/peaking-probe-a-keyline-lv.json` (generator `scripts/mkspec_probe_a.py`).
It is **not** in `patches/` and not in a build description.

It copies the E-P5's two peaking changes at the top of the mov layer, with Key Line's numbers
(picture mode 119, art code 163) where the E-P5 has the peaking numbers (201/202, 188/189).

| Op | Address | Stock bytes | New bytes | Meaning |
|---|---|---|---|---|
| 0 | 0x7ECB0EF0, 38 B | `ff` × 38 | T1 (17 B) at 0x7ECB0EF0, then T2 (21 B) at 0x7ECB0F01 | new code in the proven padding |
| 1 | 0x7E6CC031, 6 B | `ba 00 c8 04 f0 5e` (`cmp 0,a2` / `beq` / `movbu d3,(a2)`) | `dc bf 4e 5e 00 cb` (`jmp T1`, `nop`) | H1, in the colour-tone getter 0x7E6CBFD3 |
| 2 | 0x7E6C614C, 7 B | `a0 64 c2 0b f8 92 0d` (`cmp 100,d0` / `bge` / `movbu d0,(13,sp)`) | `dc b5 ad 5e 00 cb cb` (`jmp T2`, 2 × `nop`) | H2, in the expose setter 0x7E6C610B |

```
T1 0x7ECB0EF0: cmp 3,d3 ; bne +4 ; mov 119,d3      ; Muted -> Key Line's picture mode
               cmp 0,a2 ; beq +4 ; movbu d3,(a2)   ; the three stock instructions
               jmp 0x7E6CC037
T2 0x7ECB0F01: cmp 3,d0 ; beq skip                 ; Muted: keep the art code from H1
               cmp 100,d0 ; bge skip ; movbu d0,(13,sp)   ; the three stock instructions
               jmp 0x7E6C6153
        skip:  jmp 0x7E6C6159
```

What then happens with stock code (**V** by reading, not on the camera): the getter returns 163
through its own jump table; the mode byte 0x605B091C holds 119; the expose setter looks up the art
record for 163 (0x7E6CC153) and copies it to 0x605B038C; `set_out_area_param` 0x7E6C7BB0 sees record
id 163 and allocates the line buffers (0x7E6CD4B7); the job's `ucExpose` comes from byte 0xA07507CC,
which the setter writes from the same value.

Checks done:

| Check | Result |
|---|---|
| `uv run epm2mod apply SPEC -o /tmp/scratch/probe-a-alone.BIN` | applies on stock; 52 bytes differ; sha256 `05d029a0dfa7dd2003a2aaaed238aca3481cd8bdd8b516f8276fc3fb5266eef0` |
| the same after the nine specs of the pinned build | applies; sha256 `5aa3dd0a289a17df96748595a4d3c91f1ff78edf7709a9a18ceb9d0bf86433cc` |
| `python3 tools/freespace.py check` (pinned specs + this spec) | PASS, 0 FAIL; the new bytes are in area 0x7ECB0888–0x7ECB1000, verdict USABLE-CODE, and overlap no current spec |
| objdump of the patched block | T1, T2 and both hooks decode as written above |
| no branch enters the replaced bytes | the only one is the stock `beq 0x7E6CC037`, which T1 reproduces |
| emulator (`scripts/emu_probe_a.py`, `results/emu-probe-a-*.txt`): getter 0x7E6CBFD3 called for picture modes 0–6 and 100–120, both flag values; then the piece 0x7E6C6148–0x7E6C6159 of the setter | on stock and on the pinned build: **only mode 3 changes**, and it gives the same art code (163; 164 with the movie flag), the same mode byte (119) and the same expose value as stock Key Line (mode 119) |

Not checked, because the emulator runs single functions: everything after the setter.

On the camera (for the person who flashes; the build must be made by `tools/make_firmware.py`
from a build description that adds this spec to the pinned list, and the flash logged in
`docs/camera-log.md`):

1. P mode, Picture Mode Natural: live view is normal. (Regression check.)
2. Picture Mode Muted: **expected**: live view shows the Key Line drawing.
3. Take a photo in Muted. **Expected**: a normal Muted photo, no outlines.
4. ART mode, Key Line and one film slot: as before.
5. If Muted looks normal, try Vivid, Portrait, Monotone, i-Enhance: the low-level number of Muted
   being 3 is **I** (it is 3 in the `COLORTONE` list and in the IMG code).
6. Do not judge movie in Muted from this probe: the movie variant (164) is forced too.

How to read the result:

| Result | Meaning | Next |
|---|---|---|
| Key Line in live view, photo normal | the live-view art path is independent of the art mode. Go to step B | B |
| Live view normal in every mode | the two functions are not on the live-view path for plain modes, or the struct holds another number | log the mode byte: a probe that writes 0x605B091C to a card file |
| Live view frozen or black in Muted | a function that reads the picture mode straight from the live-view struct (12 read sites, e.g. 0x7E6C263C, 0x7E6C367F, 0x7E6C9FA8, 0x7E6CAB77) disagrees with the forced art code. Leave Muted (or turn the dial to iAUTO) to get live view back; a normal card update removes the probe | hook those sites the way the E-P5 does at its 9 flag sites |

## 8. Real risks and unknowns

Risks with evidence:

1. **A frozen live view in the probe's Picture Mode.** Three earlier builds froze live view when the
   live-view art tables and the art number disagreed (`docs/art-slots-evaluation.md`, 2026-11-12).
   Probe A creates a state the stock firmware never has: plain picture mode in the struct, Key Line
   in the art record. The E-P5 has the same kind of state for peaking and needed branches at 9
   places for it (§3.2). Recovery was a normal card update each time.
2. **Code that runs before segment 2 is loaded would crash.** The new code is in segment 2, the hooks
   in segment 1. The same arrangement (jump at 0x7E56C6A5 to 0x7ECB08CD, in the IMG library) is
   camera-tested. The hooked functions run only when live view starts (**I**).
3. **Frame rate.** Key Line live view runs two image jobs per frame. If E-PM2 live view is slower in
   Key Line than in a plain mode, peaking by this route is as slow. The camera shows this in ART
   mode today; nobody has measured it here (**U**).
4. **The full port changes the IMG library**, which every picture goes through. An error there
   shows in stills too. Steps B and D do not touch it.

Unknowns and the probe for each:

| Unknown | Probe |
|---|---|
| Does the live-view art path run outside an art mode? | probe A |
| Does the overlay accept combine mode 3 and a signed coefficient on this body? | step B: one byte and one halfword in pass 9, seen on the screen |
| Is byte 101 of the E-PM2 `IMG_PARAM` free for `ucPeak`? | desk: list every access to offset 101 in 0x7E544AA9–0x7E576D58 and the mov layer |
| Path from live-view command bit 0x4000 to the record byte +136 in the E-P5 | desk: follow message 29 from 0x7E36630A; not needed for steps A–D |
| E-P5 menu item, setting id, Fn function number for peaking | desk: trace the callers of 0x7E64BFF2 in the GUI and the button-function table |
| Live-view kinds 2 and 5 (peaking off) | desk: 0x7E3AC91E maps record +4 values 1, 2 → 2 and 3 → 5 |
| Low-level number of Muted | probe A, check 5 |

## 9. Effort (honest)

- Probe A: ready to build. One flash.
- Step B (usable peaking with Key Line's threshold, on in one Picture Mode): 1 to 2 days of work and
  2 to 4 flashes, if A passes.
- Step D (MF-assist trigger): 1 day more.
- Step C (E-P5 line parameters): 2 to 3 days; needs a second code area.
- Full E-P5 port with menu and colour setting: 2 to 4 weeks, about 40 change sites, and the
  sequence layer is C++ with virtual calls that have not been matched yet.

## 10. Files

| Path | Contents |
|---|---|
| `scripts/fw.py` | reads the two blocks (set `EP5_BLOCK0`) |
| `scripts/pair.py` | pairs the functions of the two bodies; writes its caches only to the folder given as argument 4 |
| `scripts/fdiff.py` | prints the instructions that differ between two paired functions |
| `scripts/grepfn.py` | grep of the per-function disassembly, grouped by function |
| `scripts/inventory.py` | the list in `results/inventory.txt` |
| `scripts/mkspec_probe_a.py` | writes the draft spec from the stock bytes |
| `scripts/emu_probe_a.py` | the emulator check |
| `specs/peaking-probe-a-keyline-lv.json` | draft spec for probe A |
| `results/` | inventory and emulator output |

Note for tool users: `tools/disasm.py --fw FILE.BIN` writes a block cache under `build/blocks/`.
During this work that made one stray file there, which was removed again. Use
`tools/emu/patchblock.py … -o /tmp/scratch/x.block0.bin` for patched blocks instead.

## 11. Direct build (asked for as "8. Direct build"; the number 8 is taken above)

Date: 2026-11-14. Status: one draft spec, `specs/peaking-direct-1.json`. Emulator-checked. Not flashed.
It replaces the step plan of §6: one flash for the whole feature. It does not use probe A's bytes or hooks
together with probe A (both hook 0x7E6C614C; build one or the other).

### 11.1 What the build does

While MF Assist runs, live view shows a plain picture with **white lines on edges**. The lines are Key
Line's own line image, added to the picture. Without MF Assist every hook gives the stock result.

| Piece | How | Source |
|---|---|---|
| Request | Byte R is 1 from the entry of `startMfAssist` to the entry of `endMfAssist`. The stock word 0x602B0DA8 ("MF Assist is running", setter 0x7E96AFD9, getter 0x7E96A490) must also be set | E-P5: the colour argument of `startMfAssist` |
| Latch | End of the per-frame struct refresh 0x7E6ECCAF: L = R and word and not movie (0x605B039C ≠ 1, struct +32 = 0) and live-view kind not 2 and not 5. When L is 1, struct +4 is cleared | E-P5 0x7E3CA4B5 + 0x7E3AD26C, same conditions. The E-P5 test of 0x605EAF3C has no E-PM2 counterpart and is left out |
| Mode | Getter 0x7E6CBFD3: mode byte 119, return 3. Setter 0x7E6C610B: art code 163 | E-P5 201 / 3 and 188. The E-PM2 has no art record for 188; the E-P5 record for 188 equals Key Line's (§3.3) |
| Plain picture | Job setup 0x7E6C74BE, both exits: `ucExpose` 3, `ucColor` 2, global 0xA07507CC = 3 | E-P5 0x7E3A3AB2, same values |
| Line job | `mov_art_set_line_yc_param`: Key Line's branch is taken, and the copy gets `ucExpose` 163. So the line job is byte for byte a stock Key Line line job (`ucArtLpf` 8, `ucProcCount` 3) | E-P5 takes the same branch, then sets 15 / 11 (not possible here, §11.2) |
| Magnified view ("CLIP") and first frames ("SIMPLE") | Art packet proc kind 0x7E6CCA57 returns 0; `mov_art_set_artpacket` does not skip the line job; `img_param_set_ucType` treats the job like codes 181–184 | E-P5 0x7E3A9391, 0x7E3A979D, 0x7E3B7BF1 |
| Frame time | 0x7E6C365F: 85 | E-P5 0x7E39F946 |
| Overlay | Key Line pass 9: `usGain2` = +256 in place of 0xFF00 (−256) | E-P5 white: gains 2048 / +2048 in mode 3 (§11.2) |
| Colour input of the overlay | Key Line pass 7: `ucExpose` 3 in its image job | E-P5 0x7E407306 |

### 11.2 What could not be ported, with the evidence

1. **Combine mode 3 does not exist on the E-PM2 (V).** The dispatcher of the combine job ("IMGDMA", fields
   `usGain1` +32, `usGain2` +34, `ucBit` +36, `ucMode` +37) is 0x7E707880: `cmp 3,d1 / blt / mov 1,d0`, table
   0x7E84EE68 with three handlers. The E-P5 one (0x7E3E6064) has `cmp 4` and four handlers. On the E-PM2 mode 3
   would run as mode 1. Mode 3 is mode 2 with 4 bytes per pixel in place of 3 (handlers 0x7E3E6281 ↔ 0x7E707A1B).
   The gains mean the same in both: 0x7E70789B shifts the gains left by 3 unless job flag bit 2 is set, and the
   E-P5 sets that flag for peaking. So Key Line's 256 / −256 is "picture − line", and E-P5 white 2048 / +2048 is
   "picture + line". The build keeps mode 2 and changes only the sign: 256 / +256.
2. **The E-P5 line parameters need the IMG library (V).** `ucProcCount` 11 is tested only in the E-P5 builder
   0x7E23777D (three sites) and its curve chooser; the E-PM2 library has no read of `ucProcCount` 9–12. Art passes
   7 and 8 of E-P5 peaking use `ucProcCount` 10 and 12 and 4-byte buffers. The build uses Key Line's passes
   (`ucProcCount` 2 and 4) and Key Line's line job. Result: Key Line's edge threshold and line width.
3. **Not ported, small:** the E-P5 takes the white-balance gains of the peaking job from another source and sets
   `chTone` to 0 (0x7E3A1E4C, 0x7E3A2310; its E-PM2 counterpart was not paired). `ucPeak` and `ucProcCount` 9 of
   the colour job (they only select IMG cache keys and a filter record that the E-PM2 does not have).
4. **`CapThr::execUpdateThrough` is not hooked.** The E-P5 needs bit 0x8000 to carry the request into the mov
   layer. Here the request is a RAM byte that the mov task reads itself in every loop pass (0x7E6C33B5 calls
   0x7E6ECCAF before it dispatches the pending update, 0x7E6C3FD8). The update itself comes from the stock MF
   Assist code: its state machine logs "rcvStartMFAssistIn_MFAssistOff() updateThrough" and
   "rcvEndMFAssistIn_MFAssistOn() setZoomEnd" (**I**: that these reach the expose setter).

### 11.3 Ops (`results/direct-new-code.txt`, `results/direct-hook-sites.txt`)

| Op | Address | Bytes | Purpose |
|---|---|---|---|
| 0 | 0x7ECB0EE3 | 11 | `getL` (reads L) |
| 1 | 0x7ECB0F16 | 230 | T_A latch, T_B getter, T_C setter, T_D1/T_D2 job setup, T_H frame time, T_I ucType |
| 2 | 0x7E880FE4 | 26 | T_G packet proc kind |
| 3 | 0x7EBF1F00 | 182 | T_E1/T_E2 line job, T_F artpacket, T_S/T_N MF Assist entries, T_J pass 7, T_K pass 9 |
| 4–16 | 0x7E6ECF91, 0x7E6CC14E, 0x7E6C614C, 0x7E6C7596, 0x7E6C764E, 0x7E6CD9CF, 0x7E6CDAC6, 0x7E6CCA81, 0x7E6C3868, 0x7E6DAF37, 0x7E6CCE6D, 0x7E726421, 0x7E726767 | 5–7 each | `jmp` to the routine (+ `nop`) |
| 17, 18 | 0x7E9889EB, 0x7E9830E0 | 7, 6 | `jmp` T_S, T_N |

449 bytes of new code, 15 hooks. No branch of the function database enters a replaced range except at its first
byte (checked by the generator).

**Code space.** Ops 0–2 are in camera-proven padding (free-space verdict USABLE-CODE). They hold every routine
that runs in ordinary live view. The 38 bytes of probe A (0x7ECB0EF0–0x7ECB0F16) are left alone because a copy of
that spec is in `patches/`. Op 3 is in 0x7EBF1F00, inside the listed area 0x7EBF1090–0x7EBF3BAD (old `sdk` shell
name text). It was chosen because: it is in segment 2, which the same boot copy loads as the proven padding
(0x7E8F5800–0x7ECB1000); the 240-frame patch already keeps its rows in the same listed area (0x7EBF1100–0x7EBF1F00)
and the camera reads them; every static check passes. No code has run there. The routines in op 3 run only when
the live-view art path handles Key Line or Watercolor, or when MF Assist starts or ends. So Natural, the film
slots and all other art modes do not execute op 3 until MF Assist starts.

**RAM.** Three new bytes, 0x602BE8C4 (L), 0x602BE8C5 (R), 0x602BE8C6 (L2: L at the last live-view update, read by
the art task). They are slot 20 of the 37-slot table of menu value-list pointers at 0x602BE874
(`results/ram-flag-evidence.txt`): the only constant inside the table is its base, in the two formatters; the
formatters get row constants 3, 5–8, 10, 11, 13, 32–34 (stock) or 3, 5–8, 10–12, 14, 33–35 (pinned), never 20;
the `.data` value of slot 20 is 0. The interval patch uses slot 1 by the same argument. Limit: a static scan.

### 11.4 Checks

| Check | Result |
|---|---|
| `uv run epm2mod apply SPEC -o /tmp/scratch/a.BIN` | applies on stock, 510 bytes differ, sha256 `3a3715c604a292c1c7cf1033679c0bc75dafbcc9e6ea0843dd33fcd1df2900f8` |
| the same after the nine pinned specs | applies, sha256 `55754796c090033a02191742f01af6643619946bd8a9441f95426dda4779c477` (the nine alone give the pinned `01837f96…`) |
| `python3 tools/freespace.py check` (nine + this) | **20 PASS, 1 FAIL** (`results/direct-freespace-check.txt`). The FAIL is op 3: "the area allows data only". The tool gives that line for any jump into an area that has no camera-tested code. The two USABLE-CODE areas have 282 free bytes (320 without probe A); the build needs 449. A PASS is not possible for this feature |
| emulator, `scripts/emu_direct.py`, stock pair and pinned pair (`results/emu-direct-*.txt`) | PASS on both. 13 cases, 1,339 input rows. Flag clear: the patched image equals the base image in every row (registers and all memory the case reads back). Flag set: every row gives the model's values |

Emulator cases: A latch (whole function, 576 rows), B getter (whole function; picture modes 0–7 and 100–120,
movie flag, null pointer), C setter piece (the same modes × 5 art codes; also writes L2), D job setup (whole
function, 120 rows), E `set_line_yc_param` (whole function, 12 art codes × buffers present or not: with the flag
the two copies equal the stock Key Line copies), G (whole function), H, I, F, J, K (code pieces), S, N (entries).
The emulator holds the whole block, so it says nothing about op 3 being loaded on the camera.

Stills (**V** by the call lists, **I** for the camera): every mov-layer hook is in a function whose callers are
all in the live-view module (0x7E6C33B5 loop and its handlers). The two art-task hooks act only on packets
with mode 2, which only the live-view packet builder writes (0x7E6CC9E8), and only while L2 is 1.

### 11.5 Camera test

Build: add the spec to the pinned list in a build description, `tools/make_firmware.py`, log the flash.
Setup: Custom Menu A → MF Assist → On. A lens with a focus ring that the body reads. Focus mode MF or S-AF+MF.

1. P mode, Picture Mode Natural, no ring movement: live view, a photo, a short movie. **Expected:** as before.
2. A film slot in ART mode: live view and a photo. **Expected:** as before.
3. ART Key Line: live view. **Expected:** as before (dark lines). This step is the first that runs code from
   0x7EBF1F00.
4. P mode, Natural, MF. Turn the focus ring. **Expected:** the view magnifies and shows white lines on sharp
   edges, on a normal (perhaps flatter) picture. The lines move as focus moves.
5. Stop turning (or half-press). **Expected:** the view returns and the lines go away.
6. Take a photo while the lines show. **Expected:** a normal photo.
7. The same in a film slot (ART mode).

| Result | Meaning | Next |
|---|---|---|
| Freeze or black screen in step 1 or 2 | a routine in the proven padding is wrong (they ran in the emulator only) | card update; report the step |
| Step 1, 2 fine; freeze in step 3 or at the first ring turn | code does not run from 0x7EBF1F00, or the Key Line path is broken by a hook | card update. Test: move op 3 to another area |
| Ring turns, view magnifies, no lines, picture normal | L never became 1 (live-view kind of the magnified view is 2 or 5, or the MF Assist start does not send an update), or the art path does not run for a plain mode | log L, the kind and the art code to the card |
| Lines appear only after a setting change while magnified, or stay after the view returns | the stock MF Assist update does not reach the expose setter | port the update request (E-P5 0x7E6FF72A) |
| Picture under the lines is Key Line's flat colours | the colour job or pass 7 ignores `ucExpose` 3 | read 0x7E56D1C3 and the pass-7 stage list |
| Picture white, grey or wrong colours with correct lines | the line image is not zero away from edges, or its chroma is not zero-based | change the gain (128 in place of 256) or keep −256 (dark lines) |
| Dark lines in place of white | pass 9 hook did not see L2 or packet mode 2 | log both |
| Live view slow | Key Line's two jobs per frame; frame time 85 as on the E-P5 | accept, or tune |

### 11.6 Labels

**Verified** (bytes or emulator): the E-P5 values and sites in §11.1; no mode 3 on the E-PM2; the gain
arithmetic; the art jobs take `ucExpose` from the packet type (0x7E728CEA); the MF Assist word and its five
writers; flag-clear behaviour equals stock for every hook; flag-set values; both images apply.

**Inferred:** the mov task loop runs the latch before each update; MF Assist start and end each cause a live-view
update that runs the expose setter; live-view kind 4 ("CLIP") is the magnified view; `ucExpose` 3 is Muted;
zero curve parameters (0x7E56D1AD) leave the picture unchanged in pass 7; the line image is zero away from edges;
code runs from 0x7EBF1F00.

**Unknown** (the camera test decides): whether the live-view art path runs while the struct holds a plain picture
mode (probe A's question); which live-view kind MF Assist uses; how the picture looks through Key Line's pass 7
with `ucExpose` 3; the frame rate.

### 11.7 Files added

| Path | Contents |
|---|---|
| `specs/peaking-direct-1.json` | the spec |
| `scripts/mkspec_direct.py` | writes the spec: `python3 scripts/mkspec_direct.py specs/peaking-direct-1.json /tmp/scratch/asm results/direct-new-code.txt` (needs the mn10300 `as` and `ld`) |
| `scripts/emu_direct.py` | emulator check: `emu_direct.py BASE_BLOCK0 PATCHED_BLOCK0 NAME` (blocks from `tools/emu/patchblock.py … -o /tmp/scratch/x.block0.bin`) |
| `scripts/hooksites.py`, `scripts/ramflag_check.py` | hook listing before and after; RAM evidence |
| `results/direct-*.txt`, `results/emu-direct-*.txt`, `results/ram-flag-evidence.txt` | outputs |

## 12. Camera result of direct-1, diagnosis, direct-2

Date: 2026-11-14. Status: `specs/peaking-direct-2.json` is a draft. Emulator-checked. Not flashed.
Labels: **V** verified (read from the bytes or run in the emulator), **I** inferred, **U** unknown.

### 12.1 What the camera did with direct-1 (owner's report)

| Observation | Source |
|---|---|
| Normal shooting without manual focus works | owner |
| ART Key Line live view works, so code runs from 0x7EBF1F00 | owner |
| ART Key Line with the focus ring turned: "key line in this mode has sharper edges around the focus peaking areas" | owner |
| Natural with the ring turned: long delay; the magnified view showed only when the ring stopped; no lines seen | owner |
| Two crashes while flipping quickly through the filters in the menu, a different filter each time | owner |
| The pinned build (reflashed for comparison) does not crash on fast flipping, and both filter switching and MF Assist are instant there | owner |

So the delay and the crashes are caused by direct-1. The older camera-log rows about an occasional restart
(2026-11-12) are all at the moment RAW Data Edit saves a file. None is about live view or the filter menu (**V**,
`docs/camera-log.md`). They are a different matter.

### 12.2 Part A: why Natural was slow and showed no lines

**How the mov layer follows a mode change (V).** The mov task loop 0x7E6C33B5 runs one pass per frame event.
Each pass calls the struct refresh 0x7E6ECCAF (it reads the settings again, and direct-1's latch is at its end),
then the state function. In live view that is 0x7E6C48D0 → `mov_image_process` 0x7E6C6853. This function calls
the expose setter 0x7E6C610B **in every frame**. So a new art code needs no live-view command and no restart:
the setter sees that the code differs from the last one (0xA07507C9), frees the old work buffers
(0x7E6C619C–0x7E6C61E3) and tells the art side (0x7E6C6498 → 0x7E6CD1F2 "mov_art_exec_init"). The mov commands
"Through End / Start / ReStart" (1, 2, 3 at 0x7E6C3A0B) are not involved. The E-P5 functions are the same
(0x7E3A2BC6, 0x7E3A243B; `fdiff.py` shows no peaking branch in this part).

**The cause (V for the code, I that it is what the camera did).** The art path needs work buffers from the
"image work" heap: 4,147,200 bytes for the art picture (0x7E6C6532), 2 × 614,400 bytes (0x7E6D4B22) and the Key
Line line buffers (0x7E6CD4B7). Before each of these allocations the code asks 0x7E6CADD8 → 0x7E578D23 whether
the heap is in **mode 1**. The heap mode is chosen by 0x7E714833. That function does not use the hooked getter.
It reads the **settings** itself (picture mode 38017, and nine more) and picks:

| Settings | Heap mode |
|---|---|
| picture mode of art class 2 or higher (0x7E70DBDE), or setting 25089 or 53649 set, or setting 34241 = 115 / 155 | 1 |
| otherwise, by ISO-type limits | 0 or 2 |

In Natural (and in every art entry of class 0 or 1) the mode is 0 or 2. Then, in every frame while L is 1:
`0x7E6CADD8` returns "busy" → `0x7E6CADFE` frees every art buffer and sets 0x605B0609 → the text
"[mov]art_buff alloc error!" → `mov_image_process` returns 1 without a picture → the next frame does the same.
Live view stands still until L is 0 again. In direct-1 L went to 0 at the **entry** of `endMfAssist`, before the
zoom-off update. That is why the magnified view "popped in" for a moment only when the ring had stopped, and why no
lines were seen. In ART Key Line the heap is in mode 1 already and the buffers exist, so nothing fails there. This
matches all three observations.

**How often is `startMfAssist` called (V)?** `OlyHfwOpeShoot::startMfAssist` 0x7E9889EB has one caller, the API
wrapper 0x7E9CB7CD (API 0x20131). The GUI calls it from two event handlers (0x7ECE362D, 0x7ECE36A3), once per
focus-ring event (**I**: the handlers have no timer of their own). Each call sets the word 0x602B0DA8 to 1 before
it sends the request (0x7E988AE7) and puts the old value back if the request fails with 0xF0000001 or 0xF0000058
(0x7E988B33). The state object `CmpSts_MfAssist` then does the real work once: in state Off it runs
"go MFAssist" and `updateThrough(true,false)` (0x7EB7DC93); in state On it only answers
(`rcvStartMFAssistIn_MFAssistOn` 0x7EB7DE46). So the hypothesis "each ring pulse restarts the pipeline" is
**not** what the code does: the repeated calls are harmless in the stock design. The word is cleared by
`endMfAssist` and by the two internal "ZoomOff" handlers (0x7EB7DEB9, 0x7EB7DFB9).

Two weaknesses of direct-1's trigger remain (**V**): (1) R and the word are set at the entry of the call, before
the zoom request is accepted, and a failed first request puts the word back to 0: L can flip 1 → 0 within one
call. (2) R is cleared only by `endMfAssist`. When MF Assist ends by an internal ZoomOff (capture, movie start,
`stopMfAssist` 0x7EA983C2) R stays 1.

**How the E-P5 avoids the stall (V).** It does not avoid the art switch. It makes the heap ready:

| Piece | E-P5 | E-PM2 |
|---|---|---|
| Heap check before an art allocation | 0x7E23E082: any mode other than 0 passes (`cmp 0,d1 / beq`) | 0x7E578D23: only mode 1 passes (`cmp 1,d1 / bne`) |
| Heap mode chooser | 0x7E3F41DD reads four more settings than the E-PM2 one (58161, 58209, 58065, 17665). Setting 58065 set → mode 1; one of the other three set → mode 2 | 0x7E714833 |
| Request | arrives in the same live-view update as the zoom (record +136), so the art code and the live-view kind change in one frame | direct-1: before the zoom at the start, before the zoom-off at the end |

So on the E-P5 the heap mode follows a setting and is in an art-capable mode before the lines are asked for
(**V** for the code; that 58065 is the peaking setting is **I**). `startPeaking` / `stopPeaking` /
`setPeakingInfo` only set and clear "restriction" bits (info 240) and then ask for a live-view update
(virtual call +268); they do not start or stop anything in the mov layer (**V**).

**Options, cheapest first:**

| Option | Verdict |
|---|---|
| (a) Debounce at the trigger | Needed, but not enough: the stall is the heap mode, not the repeated calls. Done in direct-2 by taking R from the state object (set in `entryMfAssistOn`, cleared in `entryMfAssistOff`). A second start while On does not enter the state again, and setting R twice changes nothing |
| (b) Keep the line path armed whenever the AF mode is MF | Not chosen. It costs Key Line's frame rate all the time in MF mode and needs a new read of the AF-mode setting |
| (c) Switch only the overlay pass | Not possible alone: the line job needs the same buffers |
| (d) Port the E-P5 way: heap mode follows the request | **Chosen**, in the small form: one hook at the end of the chooser. Mode 1 while L is 1 and live view runs |

With hook M the switch Natural → lines takes the stock route of a Picture Mode change from Natural to an art
filter in P mode (the manual: "When [Picture Mode] is set to [ART] …"): the setter sees the new code, the
notifier calls 0x7E6CD1F2, this calls the chooser (0x7E6CD342), the heap goes to mode 1, the allocation in the
same frame passes. Back to Natural: the setter frees the buffers first, then the chooser returns the stock mode.

### 12.3 Part B: the crashes

**(1) The three flag bytes in slot 20 of the table 0x602BE874: not the cause (V, static).** The table is read
only. The two formatters 0x7EE01DDA and 0x7EE01E8C compute `base + 4 × row` and load a pointer; they never store.
A scan of block 0 for every `call` to them (both encodings) finds 25 sites, the same 24 + 1 that
`fmtindex.py` lists, each with a constant row; 20 is not among them. No pointer word to either formatter exists.
No 4-byte constant in any of the address aliases points into the table except its base. The word before the table
(0x602BE870) is a scalar (0x7EE01F5D, 0x7EE0203D). `results/direct2-ram-flag-evidence.txt`.

**(2) Hook safety table (V).** "Target inside" = a branch of the function map or of the linear sweep, or a 4-byte
word anywhere in block 0 (jump tables), that points into the replaced bytes after the first one. All hooked
functions return with `ret`, none with `retf` (the helper `getL` is called with `call`, which changes MDR).

| Hook | Site, bytes replaced | Target inside | Live after the site | What the routine keeps | Verdict |
|---|---|---|---|---|---|
| A | 0x7E6ECF91, 6: `mov d0,(0x605B1CF4)` | none | nothing (the `ret` follows; no caller uses d0) | the store | ok |
| B | 0x7E6CC14E, 5: `mov d2,d0 / extbu d0 / ret` | none (the jump table of the function has no entry here) | d0 as result | d0 | ok |
| C | 0x7E6C614C, 7: `cmp 100,d0 / bge / movbu d0,(13,sp)` | none | d0 at 0x7E6C6153; flags are set again at 0x7E6C615C; d1 is loaded again before use | d0, both branch outcomes | ok |
| D1 | 0x7E6C7596, 5: `beq / ret` | none | flags of the instruction before (the `jmp` keeps them) | both outcomes | ok |
| D2 | 0x7E6C764E, 5: `call 0x7E6CDDA3` | none | nothing (the callers ignore d0) | the call | ok |
| E1 | 0x7E6CD9CF, 7: `movbu (79,a1),d0 / cmp 163,d0` | none | Z flag for the `beq` at 0x7E6CD9D6, d0, a1 | all three when L is not 1 | ok |
| E2 | 0x7E6CDAC6, 5: `movbu d0,(89,a3) / mov 3,d0` | none | d0 = 3, a3 | both | ok |
| G | 0x7E6CCA81, 5: `call 0x7E6CFF23` | none | d0 (result) | the call | ok |
| H | 0x7E6C3868, 5: `mov a2,d0 / exthu d0 / cmp 1,d0` | none | flags for `bne` at 0x7E6C386D, d0, d3 | all | ok |
| I | 0x7E6DAF37, 6: `cmp 184,d0 / bne` | none | none (d0 is loaded again at both targets) | both outcomes | ok |
| F | 0x7E6CCE6D, 6: `mov (16,sp),d0 / cmp 4,d0 / bne` | none | none at the targets | both outcomes | ok |
| J | 0x7E726421, 7: `mov (a2),a0 / mov 2,d0 / movbu d0,(90,a0)` | none | none (a0, a1, d0 are loaded again from 0x7E726428 on) | the store; a1 and d0 are changed but dead | ok |
| K | 0x7E726767, 6: `mov 65280,d0` | none | d0 | d0; reads `(a2)`, which is the packet pointer on every path | ok |
| S | 0x7E9889EB, 7: `mov a0,a2 / mov imm,d0` | none | a2, d0 | both | ok |
| N | 0x7E9830E0, 6: `mov imm,d0` | none | d0 | d0 | ok |

No row is violated. Together with the emulator result (flag clear = stock in 1,339 rows) this says: **with L and
L2 not 1 the build behaves as the pinned build. The crashes need L = 1.**

**(3) Ranked causes (I).**

1. **L = 1 while the heap is not in mode 1** (§12.2). In a plain mode this is the loop "allocation refused →
   free everything → error" in every frame, with the hooks E1/E2/F still asking for the line job. In ART mode it
   is worse when the filter changes while MF Assist is on: the forced art code stays 163, so the setter sees no
   change and frees nothing, but the chooser reads the new filter from the settings and, for a filter of class 0
   or 1 (the film entries are of this kind), re-partitions the heap (0x7E578C60 → 0x7E5789ED) under the Key Line
   buffers that the art task is using. Flipping quickly through the filters shortly after the ring was turned
   gives exactly this. A different filter each time fits: the crash is in the step, not in one filter.
2. **R left at 1 after an internal ZoomOff**, which lengthens the time in which cause 1 can happen (L then follows
   the word alone).
3. A cause with the flags clear that the table above and the emulator both miss. No evidence for it.

direct-2 removes 1 and 2. **What the camera will tell:** if fast flipping still crashes in a session in which the
focus ring was never turned since power-on, cause 3 exists, and the next step is to halve the op list (first the
two art-task hooks J and K, the only hooks that run on the filter path of another task).

**Does a direct-1 hook run on every filter change (V)?** Yes, all of the mov hooks run in every live-view frame
(latch, getter, setter, job setup, frame time, `ucType`; the art-packet hooks and E1/E2 in every frame of an art
filter). With L clear each one costs `getL` (3 instructions) and gives the stock values, so they do not make a
filter change heavier. They cannot be entered twice: all are in the mov task except J and K (art task), and R is
written by the task that runs the MF Assist state object. Each flag is one byte.

### 12.4 Part C: what "focus peaking worked on Key Line" was

With direct-1 in ART Key Line and the ring turned, L becomes 1 and (**V**, from the hooks):
- the art code does not change (it is 163 already), so nothing is re-allocated and the view magnifies at once;
- the picture below the lines is rendered as a plain picture (`ucExpose` 3, `ucColor` 2) in place of Key Line's
  flat poster colours (job setup hook and pass 7);
- pass 9 adds the line image in place of subtracting it: **light lines** on edges in place of dark outlines;
- the line job also runs in the magnified view (stock Key Line shows no effect there).

So the owner saw the feature itself, on the one mode in which the heap was ready. Question to ask: "In Key Line,
while you turned the ring: was the view magnified, did the dark outlines turn into light lines, and did the flat
colours turn into a normal picture?"

### 12.5 direct-2: what changes

| Change | Op | Bytes |
|---|---|---|
| New hook **M** at 0x7E7149B6 (7 bytes, the last call of the heap chooser) → `T_M`: when L = 1 and the mov state number 0x605B03D0 is 1, 2 or 3 (live view starting or running), the mode passed to 0x7E578C60 is 1. Otherwise the stock value. State 0 (after "Through End", so capture and playback) and the movie states keep stock | new | 35 B of code |
| R comes from the state object: hook **ON** at 0x7EB7D46C (`entryMfAssistOn`, 7 bytes) sets R = 1, hook **OFF** at 0x7EB7D43B (`entryMfAssistOff`, 7 bytes) sets R = 0. `entryMfAssistOff` also runs when the object is created, so R cannot stay 1 | replace S, N | 2 × 20 B |
| The hooks at `startMfAssist` 0x7E9889EB and `endMfAssist` 0x7E9830E0 are gone (stock bytes) | removed | – |
| The latch no longer reads the word 0x602B0DA8: L = R and not movie and live-view kind not 2 and not 5 | T_A | −10 B |
| Everything else (B, C, D1, D2, E1, E2, G, H, I, F, J, K, `getL`) is byte for byte direct-1's code at shifted addresses | – | – |

Sum: 475 bytes of new code (11 + 220 + 26 + 218), 16 hooks, the same four areas, the same three RAM bytes.
The generator now also refuses a hook when a 4-byte word anywhere in block 0 or a branch of the linear sweep
points into the replaced bytes.

Through End (0x7E6C4ADD) frees every art buffer and clears the last art code (**V**), so the heap is empty
before the stock chooser picks the mode for a capture.

### 12.6 Checks

| Check | Result |
|---|---|
| `uv run epm2mod apply specs/peaking-direct-2.json -o /tmp/scratch/a.BIN` | applies on stock, 542 bytes differ, sha256 `8f219f0584c0f05bd3fb5186ba1e8085cfac0dabb5dd7776dfa94e433da0072a` |
| the same after the ten pinned specs (`builds/seven-films-6-interval-240-level.json`) | applies, sha256 `b5493233ab4bef63fe5ca8f9a230e7f31a843221710ba9432f59da1be8929d78` (the ten alone give the pinned `3e7f793e…`) |
| `python3 tools/freespace.py check` (ten + this) `--first-code` | as the tool is today: 18 PASS, **4 FAIL**, all four "overlaps ledgered spec patches/peaking-direct-1.json". direct-2 reuses direct-1's bytes, and `patches/peaking-direct-1.json` still counts as a current spec. With direct-1 listed as superseded (scratch copy of `docs/space-superseded.tsv`, the file itself was not changed): **22 PASS, 0 FAIL**; ops 0–2 USABLE-CODE, op 3 accepted by `--first-code` (the ledger does not know yet that code ran at 0x7EBF1F00). `results/direct2-freespace-check.txt` |
| objdump | `results/direct2-new-code.txt`, `results/direct2-hook-sites.txt` (16 sites, before and after) |
| emulator `scripts/emu_direct2.py`, stock pair and pinned pair | PASS on both, 14 cases, 1,531 rows. Flag clear: patched = base in every row. Flag set: the model's values. ON: R = 1 from R = 0, 1 and 0xEE with the same registers as the base and L, L2 untouched (a second start while set changes nothing). OFF: R = 0. A: the word 0x602B0DA8 has no effect. M (whole chooser, 192 rows): base modes 0, 1 and 2 all occur; flag set and state 1–3 → mode 1; every other row → the base's mode. `results/emu-direct2-*.txt` |
| `build/blocks/` | unchanged (patched blocks were written to scratch with `tools/emu/patchblock.py`) |

Before a build: move or list `patches/peaking-direct-1.json` as superseded (main session; `patches/` and `docs/`
were not touched here), copy the spec to `patches/`, and use the ten pinned specs + this one.

### 12.7 Camera test

Setup, once. Screen names are from the manual.
1. MENU → **d (Setup Menu)** tab → **c/# Menu Display** → **c Menu Display** → **On** → OK. (This shows the Custom Menu tab.)
2. MENU → **c (Custom Menu)** tab → group **AF/MF** → **MF Assist** → **On** → OK.
3. Leave the menu. Press OK for the live control → **AF mode** → **MF** → OK.

Test, in this order, after switching the camera off and on:
1. Do not touch the focus ring. Choose ART (MENU → shooting mode **ART** → OK: the filter menu shows). Flip up
   and down through all the filters as fast as you can for 20 seconds. **Expected:** no crash.
2. Choose **Key Line**, press OK, turn the focus ring. **Expected:** the view magnifies; light lines on sharp edges.
3. While the view is still magnified or just after, open the filter menu again and flip fast through the filters
   for 20 seconds. **Expected:** no crash.
4. Set P mode, Picture Mode **Natural**. Turn the focus ring. **Expected:** the view magnifies within about half a
   second and shows a normal picture with light lines on sharp edges while you turn.
5. Stop turning. **Expected:** the normal view comes back and the lines go.
6. Take a photo while the lines show. **Expected:** a normal photo.
7. One film entry in ART mode: turn the ring. **Expected:** as step 4.

| Result | Meaning |
|---|---|
| Step 1 crashes | a cause with the flags clear exists (cause 3). Card update; report. Next: a build without hooks J and K |
| Step 1 fine, step 3 crashes | the heap fix does not cover a filter change while the lines are on. Next: clear L while the filter menu is open |
| Step 4 instant, with lines | the heap mode was the cause; the feature works |
| Step 4 instant, magnified, no lines | the line job does not run in the magnified kind for a plain mode. Next: log L, the live-view kind and 0xA07507E1 to the card |
| Step 4 still slow or frozen | the heap went to mode 1 but an allocation still fails (heap too small with the magnified read-out), or the switch itself is slow. Next: log 0x605157CC, 0x605B0609 and 0xA07507E4 |
| Lines only after the view has magnified, about half a second late | the one-time start of the art path (buffers, first frames). Acceptable, or arm earlier (option b) |
| Step 5: lines stay after the view returns | `entryMfAssistOff` is not reached on this path. Report which action ended MF Assist |

### 12.8 Labels

**Verified:** the per-frame call chain; the heap check and the chooser on both bodies; the three stock routes that
clear the MF Assist word; the single caller of `startMfAssist` and the On/Off handling of a repeated start; the
table scan; the hook table; that Through End frees the art buffers; the emulator results; both sha256.

**Inferred:** that the refused allocation is what stalled the camera; the crash mechanism; that `entryMfAssistOn`
is entered once per MF Assist session; that a heap switch to mode 1 in a plain mode is as safe as the stock switch
of the Picture Mode to an art filter; that no user of heap mode 0 or 2 holds a buffer during plain live view.

**Unknown** (the test decides): whether the lines show in the magnified view of a plain mode; the frame rate;
whether E-P5 setting 58065 is the peaking setting.

### 12.9 Files added

| Path | Contents |
|---|---|
| `specs/peaking-direct-2.json` | the spec |
| `scripts/mkspec_direct2.py` | generator: `python3 scripts/mkspec_direct2.py specs/peaking-direct-2.json /tmp/scratch/asm results/direct2-new-code.txt` |
| `scripts/emu_direct2.py` | emulator check: `emu_direct2.py BASE_BLOCK0 PATCHED_BLOCK0 NAME` |
| `results/direct2-*.txt`, `results/emu-direct2-*.txt` | listings, free-space check, RAM evidence, emulator output |
