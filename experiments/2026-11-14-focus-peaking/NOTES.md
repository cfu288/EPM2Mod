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

## 13. Scenario tests

Date: 2026-11-14. Status: `specs/peaking-direct-3.json` is a draft. Scenario-tested and boot-tested in emulation.
Not flashed. `peaking-direct-2` is withdrawn (never flashed).
Labels: **V** verified (ran in the emulator or read from the bytes), **I** inferred, **U** unknown.

### 13.1 The method

`tools/emu` can now run whole call chains (`tools/emu/README.md`, "Scenario runs"). The live-view rig
`tools/emu/liveview.py` runs as real firmware code: the static constructors of segments 1 to 3, 12 module init
functions, and the task bodies MOV_TASK, MOV_SUB_TASK, MOVART_TASK, ART, ART_IMG_CM, ART_IMG_CS, ART_IMG_CF,
MOVDISP_TASK, MOVCOLOR, MOVCOLOR_SUB from their entries. RAM starts with the firmware's `.data`. One frame event
runs the mov task loop 0x7E6C33B5 → struct refresh 0x7E6ECCAF → `mov_image_process` 0x7E6C6853 → expose setter →
heap → frame builder → art request → ART task → Key Line passes 1, 7, 8, 9, 10 → combine job → display update. A
Key Line frame is about 175,000 instructions and 4,500 device register writes.

Replaced in every scenario (so not tested): device registers (writes dropped, reads 0), the uITRON kernel (a
Python model without pre-emption), "the image processor finished" (met at once), the settings store (ids not set
read 0), the white-balance module, the CPU cache control, the soft-float multiply. No pixel is computed. No
live-view geometry is given, so the mov layer prints `[mov]img_ctrl_size err` in every frame on every image.
Settings used: Picture Mode 38017 (2 Natural, 119 Key Line; 100, 103, 107 film entries; 104, 108, 113 effect
filters) and the art filter type 17601 index 0 (1 = type I).

Script: `scripts/scen_peaking.py`. Outputs: `results/scen-s1.txt` … `scen-s5.txt`. Images: pinned (ten specs),
pinned + direct-1, pinned + direct-2, pinned + direct-3.

### 13.2 Results

| Scenario | pinned | direct-1 | direct-2 | direct-3 |
|---|---|---|---|---|
| **S0** boot order of the hooks (`tools/emu/hookcheck.py`, static) | 1 FAIL: `remap7b-code` hook 0x7E56C6A5 (segment 1) → 0x7ECB08CD (segment 2). Camera-tested and boots; the hooked code runs only when a picture is developed (**I**) | not run | **14 FAIL** of 47: every segment-1 hook jumps to segment 2, and T_G (segment 1) calls `getL` in segment 2 | **0 FAIL** of 47 |
| **S1** request clear, Natural and Key Line, 3 frames each | reference | not run | same RAM writes (apart from L and L2, written 0), same device writes in the same order, no stock pc lost outside the hook sites, no stock pc gained | the same |
| **S2** Natural, request set, art type 1 | picture in every frame | **no picture in any frame**: heap mode 0 → check 0x7E6CADD8 refuses → free all → `art_buff alloc error` → return 1; `mov_art_exec_init` and an ART round trip in every frame | picture in every frame: heap mode 1, 4 buffers granted, line job, passes 1, 7, 8, 9, 10; pass 9 `usGain2` 0x0100, pass 7 `ucExpose` 3 (pinned Key Line: 0xFF00 and 163) | as direct-2 |
| **S2** the same with art type 0 | – | no picture (same fault) | **no picture in any frame** (new defect, §13.3) | picture in every frame |
| **S3** Key Line with the request, 13 Picture Mode changes | no anomaly (stock frees the buffers, then re-partitions with 0 live blocks) | **heap re-partitioned under 4 live blocks** at each of the 5 changes to a film entry or to Natural; in that frame the line job and passes 1 and 7 still start on those blocks; then no picture and refused buffers until an effect filter is chosen (10 frames) | no anomaly: the heap stays in mode 1, lines stay | no anomaly |
| **S4** R through the state functions | – | R is left 1 after the internal zoom-off handler 0x7EB7DEB9 | R written once per entry: 0, 1, 0, 1, then 0 by `entryMfAssistOff` | as direct-2 |
| **S5** Through End with the request, then the chooser | mode 0 | as pinned | as pinned: mov state 0, 0 live blocks, chooser gives the stock mode, pass 9 gain for a still packet 0xFF00. L stays 1 until the next live-view refresh | as direct-2 |

How much of the real path ran:

- S1, S2, S3: everything in §13.1. The part under test (getter, setter, latch, heap chooser and heap, job setup, line job
  parameters, art packet, Key Line passes, combine job set-up) is real code. Not real: what the image processor does
  with the jobs.
- S4: the two entry functions run whole, on stand-in objects (virtual calls return 0). The handler 0x7EB7DEB9 runs
  with 12 direct callees stubbed. The state framework that decides which entry follows which event did **not** run.
  That an internal zoom-off leads to the Off state, and so to `entryMfAssistOff`, is **I**.
- S5: only the mov command Through End and the chooser. The TAKE_* and REC_* tasks, the sensor read-out and the art
  passes of a still did **not** run. The count "new-code pcs" in `scen-s5.txt` uses direct-2's addresses.

### 13.3 What the tests say about direct-1

- **The delay and the missing picture are reproduced (V).** S2 gives the fault of §12.2 on direct-1 in every frame and
  on no other image.
- **The crash is not reproduced as a crash (U), but its candidate cause is shown (V).** The emulator has no image
  processor, so a write into a wrong buffer cannot happen here. What S3 shows on direct-1 and on no other image: a
  Picture Mode change away from a mode-1 filter while the request is set makes the chooser re-partition the heap
  (0x7E5789ED) while the art picture buffer (4,147,200 B) and three 614,400 B buffers are still allocated, and the
  same frame then starts the Key Line line job and art passes 1 and 7 on those buffers. Stock never does this
  (pinned: 0 live blocks at every re-partition).

### 13.4 Two defects of direct-2

1. **Boot order (V, from the full-boot emulation of the main session; S0 finds it statically).** Hook M in the heap
   mode chooser (segment 1) jumps to segment 2. The boot task runs the chooser before Usr1 copies segment 2. The
   other segment-1 hooks have the same exposure.
2. **Art filter type (V in the scenario; the value on the camera is U).** The forced picture mode 119 needs art type 1
   or 2. `art_GetFilterType` 0x7E71BD94 returns 0xFFFF for (119, 0); `art_IsSupportType` 0x7E71BC93 then refuses the
   request, the art init answers 0x9A04, and the frame ends with no picture. The type comes from setting 17601 index 0
   through byte +5 of the live-view struct. What that setting holds while the Picture Mode is Natural is not known.
   Indexes 1 to 8 of the same id are read as per-filter values, which suggests that index 0 is "the type of the
   current filter" (**I**). With type 2 the art side would run Key Line II (169) against the forced art code 163.

### 13.5 direct-3

| Change | Bytes |
|---|---|
| Every routine that a segment-1 hook reaches is now in segment 1: `getL`, T_A, T_B, T_C, T_D1/T_D2, T_H, T_I at 0x7E50A201 (235 B); T_E1, T_E2, T_F, T_M, T_J, T_K at 0x7E53A55C (179 B); T_G stays at 0x7E880FE4 (26 B). Both new areas are reclaimed dead functions with verdict USABLE-DATA and all six static checks ok (`docs/code-space-map.md` §3.3). No code has run there | moved |
| T_ON and T_OFF stay in segment 2 (0x7EBF1F00, 39 B): their hook sites are in segment 2 | – |
| The latch T_A writes 1 to struct +5 (art type I) when it sets L | +4 B |
| The areas 0x7ECB0EE3 and 0x7ECB0F16 are no longer used | – |

479 bytes of new code, 16 hooks at the same sites as direct-2. Generator: `scripts/mkspec_direct3.py`.

| Check | Result |
|---|---|
| `uv run epm2mod apply specs/peaking-direct-3.json -o /tmp/scratch/a.BIN` | applies on stock, 567 bytes differ, sha256 `689d8b1680c902eded99acd08e29a0a93f4a02979a2aa6bdabc7ff6717ef1d5b` |
| the same after the ten pinned specs | applies, sha256 `5330c0b80149aabbaaf578dbed6cc6592929f4e2b2f914005593a30262c4c325` (the ten alone: `3e7f793e…`) |
| `python3 tools/freespace.py check` (ten + this) `--first-code` | 24 PASS, 0 FAIL (`results/direct3-freespace-check.txt`); the three code areas are "first code" |
| `python3 tools/emu/hookcheck.py specs/peaking-direct-3.json` | 47 transfers, 0 FAIL (`results/direct3-s0-hookcheck.txt`) |
| Boot from reset in the other session's om-emu copy (`stage2-boot.mjs 2000`, used read-only) | pinned + direct-3: STAGE 2: PASS, the same summary as pinned |
| S1 to S5 | table above |
| `scripts/emu_direct2.py` single-function cases | not re-run on direct-3 (the routines are direct-2's text at new addresses; S1 and S2 run all of them but T_F's CLIP branch and T_H's a2 = 0 row) |

### 13.6 What remains untested (camera)

- Code running from 0x7E50A201 and 0x7E53A55C (first code in both areas).
- The value of setting 17601 index 0 in Natural (direct-3 no longer depends on it).
- The picture itself: lines, brightness, frame rate (85 ms frame time).
- Fast filter flipping with real timing and pre-emption; a race between tasks cannot show in the model.
- MF Assist through the real state framework: that R is cleared after a capture or a movie start.
- A capture and a movie start while the lines show.
- Dramatic Tone: the rig cannot finish its art passes even on pinned, so it was left out of S3.

### 13.7 Notes on the tools

- A stray `pkill` of this session ended every `debug.mjs --serve` process of the machine once (about 16:50). Another
  session's emulator run may have stopped then.
- om-emu was not changed. Requests for it are listed in `tools/emu/README.md`.

## 14. The crash at Velvia (ART 7) on direct-3, and direct-4

Date: 2026-11-14. Status: `patches/peaking-direct-4.json`, build `builds/peaking-direct-4.json`. Checked in emulation.
Not flashed. Labels: **V** verified (bytes, or ran in the emulator), **I** inferred, **U** unknown.

### 14.1 Camera report (direct-3, sha256 `5330c0b8…c325`)

- P mode, OK, Picture Mode strip: the camera crashed when the cursor came to ART 7 (Velvia), from ART 6 and from ART 8.
- The peaking lines show in the magnified view with Portra (ART 1) and with Key Line. They are thin.

### 14.2 Cause 1: one byte of another spec was overwritten (V)

| Fact | Evidence |
|---|---|
| ART 7 is picture mode 106. Its art code is 167 in live view and 168 in a movie | `art_GetFilterType` table 0x7E854A24 and getter tables 0x7E7FF05C / 0x7E7FF008, entries 6 (set by `remap7b-code`, `seven-movie-1`). S6: the mov layer gives 167 after the change to 106 |
| Codes 167 and 168 are the only users of the six-axis handler at 0x7E880FD4 | table 0x7E78C254, entries 158 and 159 (`seven-fixes-1`, `seven-movie-1`); no other word in block 0 holds 0x7E880FD4 |
| That handler is 17 bytes, 0x7E880FD4–0x7E880FE4. Its last instruction is `jmp 0x7E56D8D8` = `dc f8 c8 ce ff`. The last byte, **0xFF at 0x7E880FE4**, is the top byte of the displacement | `seven-fixes-1` op 0 |
| direct-1, -2 and -3 put T_G at 0x7E880FE4. Its first byte 0xDD replaced that 0xFF. The jump became `jmp 0x5C56D8D8` | disassembly of the direct-3 image |
| 0x5C56D8D8 is not code. The stage runs when the colour parameters for code 167 are made (**I**: at the moment the look is chosen, and for a photo or a movie with Velvia) | S6: fault at pc 0x5C56D8D8 for 167 and 168 on direct-3 only |

ART 6 (code 145), ART 8 (85) and all other codes use other handlers: S6 gives the same result as pinned for the other
174 codes. So this fault is in the Velvia entry only, with or without MF Assist, in the quick menu and in ART mode.

**The base build does not have this fault (V).** In `seven-films-6-interval-240-level-adjust` the byte is 0xFF and the
jump is whole; S6 passes. No patch for the base is needed.

**Why the checks missed it.** The generator makes `expect` from the stock file, where the byte is 0xFF, the same value
that `seven-fixes-1` writes. `tools/freespace.py` counts only the bytes of an op that differ from stock, so its ledger
ends `seven-fixes-1` at 0x7E880FE4 ("16 B") and `docs/code-space-map.md` lists 0x7E880FE4 as free. S1 to S5 give the
IMG library no colour work, so the six-axis stage never ran. The full-boot emulator reaches the strip and shows
"Velvia" on direct-3 without a fault: it runs neither the mov layer's expose setter nor the colour stage (0 hits).

direct-1 had the same byte. Its two crashes "at a different filter each time" may be this one or the heap fault of
§12.3 (**U**).

### 14.3 Cause 2, found on the way: the sleep routine was overwritten (V static; the effect on the camera is I)

`docs/space-candidates.tsv` row 10 lists 0x7E50A201 and 0x7E53A55C as "unreferenced function". They are not:

- 0x7E53A55C is "[pwr_standby]:start" (it calls 0x7E50A201) and 0x7E53A60E is "[pwr_standby]:end" (it calls 0x7E50A2AB).
- Their caller is the code that the reset copies from flash 0x7F14B000 to SRAM 0x47001000: `call 0x7E53A55C` at SRAM
  0x470010F7 and `call 0x7E53A60E` at 0x4700114E. The calls are pc-relative to the SRAM address, so the function map,
  decoded at the flash address, did not see them. The full-boot emulator has these bytes at 0x470010F7 (**V**).
- The chain: `OlyHfwPower::sleepForSystem` 0x7E998910 → 0x7E68CB5E → queue "QPWRSTANDBY" → task BOOT_CPU0 0x7E53A4A4
  → SRAM 0x470010DE.

direct-3 put T_E1 … T_K over 0x7E53A55C–0x7E53A60E and `getL`, T_A … T_I over 0x7E50A201–0x7E50A2EB. S7: on direct-3
the call of 0x7E53A55C runs T_E1 and jumps into the middle of `mov_art_set_line_yc_param`. So direct-3 should crash
or hang when the camera goes to sleep (**I**: that `sleepForSystem` is the Sleep timer; not seen in a report).

### 14.4 direct-4

| Change | Bytes |
|---|---|
| `getL`, T_A, T_B, T_C, T_D1/T_D2, T_H, T_I, T_G, T_E1, T_E2, T_F, T_M, T_J, T_K are in the 0xFF run of the kernel range, 0x7E4C9200–0x7E4C93A3. The reset code loads this range with the kernel, before any task and also on the update path. `interval-frames-240` keeps data in the same run (0x7E4C9100) and the camera reads it. First code in this run | 420 |
| T_ON, T_OFF at 0x7EBF1F28 (segment 2, as their hook sites; inside the range where direct-1's code ran on the camera) | 39 |
| 0x7E880FE4, 0x7E50A201 and 0x7E53A55C are not touched | – |
| The 16 hooks, the three RAM bytes and the text of every routine are direct-3's. Calls of `getL` are shorter because it is near | – |
| Base: the pinned build with `level-adjust-row` | – |

New static check `tools/emu/opcheck.py BUILD.json`: (1) a byte that an earlier spec covers and keeps, changed by a later
spec; (2) a call from the SRAM code into an op. direct-3: 7 FAIL (the byte at 0x7E880FE4, four context bytes of
`interval-frames-240` at 0x7EBF1F00, the two SRAM calls). Pinned and direct-4: 0 FAIL.

### 14.5 Checks

| Check | Result |
|---|---|
| `.venv/bin/epm2mod make builds/peaking-direct-4.json` | sha256 `eea187a958de410bca0448367408998099fde177548d0b9010baf510a3452482`; free-space check PASS (first code) |
| `.venv/bin/epm2mod make` (pinned) | `e93d1589…7b66`, as tested |
| `tools/freespace.py check` (12 specs) `--first-code` | PASS, 0 FAIL (`results/direct4-freespace-check.txt`) |
| `tools/emu/hookcheck.py patches/peaking-direct-4.json` | 37 transfers, 0 FAIL (`results/direct4-s0-hookcheck.txt`) |
| `tools/emu/opcheck.py` | direct-4 0 FAIL, direct-3 7 FAIL (`results/direct4-opcheck.txt`, `direct3-opcheck.txt`) |
| Boot from reset, `stage2-boot.mjs 2000` | STAGE 2: PASS; the summary equals pinned line for line except wall time and idle counts. T_M and `getL` run at 0x7E4C9340 / 0x7E4C9200 at 16.4 ms (boot task, before segment 2 is loaded); the jump at 0x7E880FE0 reads `dc f8 c8 ce ff` |
| Full-boot emulator, P mode, OK → Picture Mode strip → ART 6, 7, 8, 7, 6 | pinned, direct-3, direct-4: no fault, the strip shows "Velvia". Not a test of the fault (§14.2) |
| S1 to S5 on direct-4 against the new pinned image | as direct-3 in §13.2: S1 same, S2 picture in every frame (art type 1 and 0), S3 no anomaly, S4 R = 0 at the end, S5 as pinned (`results/scen-direct4-s1.txt` … `s5.txt`) |
| **S6** Picture Mode 105 → 106 → 107 → 106 → 105, then the six-axis dispatch for the frame's art code and its movie code, then for all codes 9–184 | pinned PASS; **direct-3 FAIL** (167, 168: pc 0x5C56D8D8); direct-4 PASS (`results/scen-s6.txt`) |
| **S7** `pwr_standby start` called with the SRAM call's frame | pinned PASS; **direct-3 FAIL**; direct-4 PASS (`results/scen-s7.txt`) |

S6 runs the dispatch as a code piece (from 0x7E56D2AB, d3 = the art code), not the whole colour job. Codes 85 and 87
(Cross Process handler) need job data that a piece does not have; they are not judged, and are the same on all images.

Not checked: the picture; code running from 0x7E4C9200 on the camera; sleep and wake on the camera; the Velvia
photo and movie paths (the same handler, so the same byte); real timing.

### 14.6 Lines that are easier to see

| Fact | Label |
|---|---|
| The line image is added in pass 9 with `usGain2` 256. The dispatcher shifts it left by 3: 2048. The E-P5 uses 2048 with the no-shift flag. So the strength already equals the E-P5's white | V (§11.2) |
| E-P5 black lines are −2048: the stock Key Line value 0xFF00. White lines on a bright edge have little contrast; dark lines there have more | V for the values, I for the look |
| The E-P5 line job uses `ucArtLpf` 15 and `ucProcCount` 11. `ucProcCount` 11 needs IMG-library code that the E-PM2 does not have (§11.2). Key Line I uses `ucArtLpf` 8, Key Line II uses 9 (0x7E6CDA67, 0x7E6CDAC4), the only difference between their line jobs. What 8 and 9 select in the IMG library was not traced | V for the values, U for the look |

Option, one byte: `specs/peaking-direct-4-gain2.json` = direct-4 with gain 512 (2 × the line image). S2 shows pass 9
`usGain2` 0x0200. Whether the combine stage clips cleanly at 2 × is **U**. Generator: `mkspec_direct4.py … --gain 512
--name peaking-direct-4-gain2`. It is not in `patches/`: test direct-4 first (one change per flash). Next options
if 2 × is not enough: `ucArtLpf` 9 in T_E2 (one byte), or dark lines chosen by a setting.

### 14.7 Camera test (direct-4)

Setup as §12.7 steps 1 to 3 (MF Assist On, AF mode MF). Shooting mode P.

1. Press OK. The live control shows at the right. Press UP or DOWN until the second icon from the top (Picture Mode)
   is yellow; the strip at the bottom shows the looks and the name ("Natural"). (Screen names from the full-boot
   emulator.)
2. Press RIGHT, slowly, through Custom to ART 1 … ART 6 ("Vis 250D"), ART 7 ("Velvia"), ART 8. Then LEFT back over
   ART 7 to ART 6. **Expected:** no crash; the name "Velvia" shows at ART 7.
3. On ART 7 press OK. Take a photo. **Expected:** live view goes on; a Velvia photo.
4. With Velvia chosen, turn the focus ring. **Expected:** the view magnifies and shows the light lines, as with Portra
   on direct-3.
5. Leave the camera untouched until the screen goes off (sleep). Press the shutter button halfway. **Expected:** live
   view comes back.

| Result | Meaning |
|---|---|
| Crash at ART 7 again | another cause exists. Report whether the focus ring was turned since power-on, then repeat step 2 with MF Assist Off |
| Black screen or freeze from power-on | code does not run from 0x7E4C9200. Card update with the pinned build; report |
| Step 5: no wake-up, or a restart | a sleep fault that is not the one of §14.3. The same check on the pinned build tells whether it is ours |
| Lines too thin | the 2 × gain option of §14.6 is the next build |

One question for direct-3, if it is still on the camera: does it freeze or restart when left untouched until it
should sleep (§14.3)?

Flash: `epm2flash peaking-direct-4 eea187a958de410bca0448367408998099fde177548d0b9010baf510a3452482`.
Go back: `epm2flash seven-films-6-interval-240-level-adjust e93d1589b3406ec991e3f32225acf6e2c2074aa58fc5394ca06a93da83797b66`.

### 14.8 Files added

| Path | Contents |
|---|---|
| `patches/peaking-direct-4.json`, `builds/peaking-direct-4.json` | the spec and the build description |
| `specs/peaking-direct-4-gain2.json` | the 2 × gain option |
| `scripts/mkspec_direct4.py` | generator: `mkspec_direct4.py OUT.json /tmp/scratch/asm [LISTING.txt] [--gain N] [--name NAME]` |
| `scripts/scen_direct4.py` | S6 and S7: `scen_direct4.py all PINNED_BLOCK0 direct-3=BLOCK0 direct-4=BLOCK0` |
| `tools/emu/opcheck.py` | the two static checks of §14.4 |
| `results/direct4-*.txt`, `results/direct3-opcheck.txt`, `results/scen-s6.txt`, `scen-s7.txt`, `scen-direct4-s*.txt` | outputs |

## 15. A menu setting for peaking: Off / White / Black (`peaking-menu`)

Date: 2026-11-15. Status: `patches/peaking-menu.json`, build `builds/peaking-menu.json`, sha256
`07f25fd8b7e2cce65a311a48c475c9d28558954f0c16ca18df771fc26221ce58`. Checked in emulation. **Not flashed.**
The pinned build `peaking-gain-2x` still rebuilds to `ce1037cd…a2c8`. Labels: **V** verified (bytes, or ran in the
emulator), **I** inferred, **U** unknown.

### 15.1 Design

MENU → Custom Menu → A → **Peaking** (the row after MF Assist): **Off / White / Black**.

| Value | Live view while MF Assist magnifies |
|---|---|
| White | as the pinned build: light lines, gain 512 |
| Black | dark lines: Key Line's own gain 0xFF00, which is the E-P5 value for black (−2048 after the shift by 3, §14.6). The picture below the lines stays plain |
| Off | the latch L stays 0, so every hook gives the stock result: MF Assist magnifies as on the build without peaking |

MF Assist must still be On: the lines show only while MF Assist magnifies.

Why one row with three values, and not the E-P5's two rows (MF Assist → Magnify / Peaking): see §15.5.

### 15.2 Where the value is kept

| Fact | Label |
|---|---|
| The E-P5 peaking setting is info 567 → prm tag 0xE2D1. The E-PM2 info table ends at 700 with other tags from 533 on, and has no tag 0xE2D1. Ids 0–532 are the same on both bodies; the E-PL6 table equals the E-PM2 table | V (tables 0x7E4BDBA8 / 0x7E7C95B4 / 0x7E7CA014) |
| The E-PM2 text table has no "Peaking", "White" or "Black" (1,970 English strings). "Magnify" is text 1102 | V |
| **Setting 458** ("Built-in EVF Style", texts 1498–1502) is used: prm tag **0x8971**, MODE bank, one byte. Its value list in the mode controller is 1, 2, 3 (record 0x7E84C584), so three values need no change there | V |
| Nothing reads it: no call of the prm getter or setter, of `Get/Set_CameraInfo` or of the GUI's `getSetting` with this id or tag as a constant; in the mode controller's tables the id is only in its own value-list record and in the full-reset list 0x7E84D850. It is in no bank list, no restore list, no conflict rule. Its only page (panel 593) is in no menu. The body has no built-in viewfinder | V for the scans, I for "no reader with a computed id" |
| The value after a full reset is **3** (mode controller default table 0x7E84C82C). The prm default list says 1 (record 0x7E4C1114). The emulator's first-boot settings bank holds 3 | V |
| So: **3 = White, 2 = Black, 1 = Off**, and the code takes every value but 1 and 2 as White. A camera that was never set shows White, as the pinned build does | V for the code, I for the value on the owner's camera |
| Row-enable checks of setting 458 (table 0x7EC1E184): number 2 (the mode controller's lock test, 0x7E9E8DF7) and 84 (bit 4 of info 4013, 0x7E9E9C41). Wind Noise Reduction has both among its five. What sets that bit was not traced. MF Assist has no check at all. In the emulator the row is selectable in P, iAUTO, ART and movie mode (§15.4) | V |
| Rejected: info 670 (tag 0x18B1, values 0–2): it is in every bank list and in the standard reset list, and its meaning is unknown. Infos 446–449 (EVF Info Settings, Off/On): two values only; a third needs a new value list in the mode controller | V for the tables |

### 15.3 What the patch changes

44 edits, 2,578 bytes in the edited windows, 2,180 bytes changed. A delta on the pinned build: every `expect` is a
byte string of `peaking-gain-2x`. Generator: `scripts/mkspec_menu.py`.

| Part | Edit |
|---|---|
| Item table | 80-row copy at **0x7EBF2000** (1,282 B): the 79-row table 0x7EBF3000 of `level-adjust-row` with `{group 0, text 1505, setting 458, order 7, help 1506, value list 607, 0}` at index 7. The 10 address loads point to it |
| Child list | 80-entry copy at **0x7EBF2600** (648 B) with (panel 607, setting 458) at index 7. The 11 page records 24–34 point to it |
| Row constants | last index 78 → 79 (5 sites), count 79 → 80 (3 sites), row-state array 158 → 160 bytes (0x7EDE9AE5); rows in group A in the `.data` image 0x7E8EE850: 10 → 11 |
| The list | Panel 607 is a generic list page (factory 0x7EDC7ECB, as MF Assist's panel 107) of the dormant setting 446, in no menu. Its descriptor 0x7F00BFBC now says setting 458, 3 items at **0x7EBF2900** (84 B): Off (1), White (3), Black (2) |
| The value shown in the row | The row's field +12 is a number in the table 0x7F014614 of value → text lists (660 pointers; **not** the panel number, though both are 107 for MF Assist). Entry 607 was null: the row builder 0x7EE01E1E read address 0 and the emulator stopped with a fault at the first try. Entry 607 now points to a new list at **0x7EBF2960** (96 B) |
| Code | 76 B at **0x7E4C93A4** (kernel range, after T_K): `T_R`, `T_K2`. T_A: `movbu (R),d0` → `call T_R,[],4`. T_K: `mov 512,d0` → `jmp T_K2` |
| Texts (block 1, English only) | 0x38872C (30 B) text 1505 "EVF Auto Switch" → "Peaking"; 0x38874C (180 B) text 1506 → "Show white or black lines / on sharp edges while / MF Assist magnifies."; 0x38862A (14 B) text 1500 "Style 1" → "White"; 0x38863A (14 B) text 1501 "Style 2" → "Black". "Off" is the stock text 1371 |

- `T_R` runs in the mov task, at the end of the struct refresh 0x7E6ECCAF (hook A). When R is 1 it reads tag 0x8971
  with the prm getter 0x7E457C75, as the same function does for five other tags (0x7E6ECDA1 …), keeps the value in
  the RAM byte **C = 0x602BE8C7** and answers 0 for Off. It is not a leaf, so it returns with `ret`, not `retf`.
- `T_K2` runs in the ART task (hook K). It reads only C: 2 → the stock `mov 65280,d0`, else `mov 512,d0`.
- New RAM: C, the fourth byte of the unused slot 20 that holds L, R and L2 (§11.3). The row-state array of the Custom
  Menu page grows into 0x606A31B6–B7 (same argument as level-gauge NOTES §12.2; zero through the emulator run).
- The tables 0x7EBF3000 and 0x7EBF3500 of `level-adjust-row` stay in place without a reader (1.9 KB). They are not
  edited in place because the 80-row table would run 2 bytes into the child list.
- The old readers of the changed texts: panel 596 (EVF Auto Switch) and panel 593 (Built-in EVF Style). Both are in
  no menu. Other languages keep their old strings for these four ids, so the row is labelled correctly only in
  English.
- `film-names-all-languages` (another spec of the same day) changes other block-1 offsets: no overlap.

### 15.4 Checks

| Check | Result | Label |
|---|---|---|
| `.venv/bin/epm2mod make builds/peaking-menu.json` | sha256 `07f25fd8…ce58`; free-space check PASS, 0 FAIL, no `first_code` (`results/menu-freespace-check.txt`) | V |
| `tools/emu/hookcheck.py` | this spec: 5 transfers, 0 FAIL. All 14 specs: 55 transfers, the 1 known FAIL (0x7E56C6A5, remap7b-code) | V |
| `tools/emu/opcheck.py builds/peaking-menu.json` | 0 FAIL | V |
| Boot, `stage2-boot.mjs 2000` | PASS; the report equals the pinned build's except the wall time | V |
| Menu crawl, P mode, card, clock set, every sub-screen (4,236 screens) against the crawl of `seven-films-6-interval-240-level-adjust` (the pinned build differs from it only in the peaking code; its block 1 is the same file) | outside the Custom Menu rows 1,875 screens, all byte-equal. Custom Menu rows as sets: 1,500 in both; 9 gone = page 2 of group A with 3 rows; 13 new = the same 9 with 4 rows, the cursor on Peaking, the list on Off, White, Black. Firmware error log and crawler notes equal (`results/menu-emu-crawl-p-card-full-vs-leveladj.txt`) | V |
| The same full crawl of the pinned build itself | finished 2026-11-15: 4,250 screens against 4,236; other units 1,875 equal; Custom Menu 9 lost, 13 new, the same sets as above; error log and notes equal | V |
| Shallow crawls of the pinned build and this build: P without card, iAUTO, ART, movie | only the pages of group A differ, one new cursor position in each mode; the row can be selected in every mode (`results/menu-emu-crawl-shallow.txt`) | V |
| Screens | `~/opt/om-emu-e101-boot-work/peaking-menu/screens/04-a-peaking-white.png`, `05-peaking-list-white.png`, `06-peaking-list-black.png`, `07-peaking-list-off.png`, `09-a-peaking-off.png`, `10-a-peaking-black.png` | V |
| The value over a restart | Black, Off and White each read back after a restart, in the row and in the tag (`results/menu-emu-persist.txt`); the value stays through P → iAUTO → P → ART (`results/menu-emu-modes.txt`). The emulator carries the bank's RAM image over in place of the power-off save | V for the load, I for the save |
| Row-state array | zero after the 160 bytes through start-up, menus, INFO and playback (`results/menu-emu-ramcheck.txt`) | V |
| S1 (request clear) | this build = the build without peaking in every frame | V |
| **S8** Off with the request set, Natural and Key Line | same memory writes but the four flag bytes, same device accesses in the same order, no stock pc lost, L = 0: equal to the build without peaking | V |
| **S9** White (value 3, and 0) | equal to the pinned build but the byte C; pass 9 gain 0x0200, pass 7 `ucExpose` 3 | V |
| **S10** Black | a picture in every frame; pass 9 gain 0xFF00, pass 7 `ucExpose` 3 | V |
| **S11** T_A and T_K alone with the firmware's own settings getter | 10 + 20 rows as the model; sp and d2, d3, a2, a3 kept | V |
| S2 to S7 on this build | see `results/scen-menu-s*.txt`; a file that is missing was not finished when this section was written | U until read |

Not checked: the picture (black lines on the camera); the help text on screen (the emulator did not show a help
text for any row); the value 3 on the owner's camera; the row in languages other than English.

### 15.5 Peaking without the zoom: not in this build

| Fact | Label |
|---|---|
| The picture path does not need the magnified view. The latch asks for: R, no movie, live-view kind not 2 and not 5. Hooks F, G and I exist only to make the line job run in the magnified kind; the plain kind is Key Line's stock path (S2 runs it) | V |
| The trigger does. R is set in `entryMfAssistOn` of the MF Assist state object. The GUI starts that object from the focus-ring events only when MF Assist is On, and its start handler 0x7EB7DC93 asks for the zoom through a chain of virtual calls | V for the code, I for which call is the zoom |
| What a build needs: either a second trigger (the two focus-ring handlers 0x7ECE362D / 0x7ECE36A3 set R, and a timer clears it), or a skip of the zoom request and of its counterpart at the end when a setting says so. The E-P5's `startMfAssist` has a colour argument (§11.1); its state object was not paired | I |
| The emulator cannot test either: the scenario rig does not run the state framework (§13.2, S4), and the full-boot emulator has no lens that sends focus-ring events | V |

So the E-P5 layout (MF Assist → Magnify, Peaking) would show a "Magnify Off" that this build cannot honour. One row
with three values says what the build does. Next step, if wanted: pair the E-P5 `CmpSts_MfAssist` start handler
(strings "rcvStartMFAssistIn_MFAssistOff") with 0x7EB7DC93 and find the zoom call.

### 15.6 Camera test

Setup: MENU → Custom Menu → A → MF Assist → On. OK → AF mode → MF. A lens with a focus ring.

1. MENU → Custom Menu → A → DOWN past MF Assist. New: the row **Peaking**, value **White**.
2. Leave the menu, turn the focus ring. Expected: magnified view with light lines, as before.
3. Peaking → **Black** → OK. Turn the ring. Expected: dark lines on sharp edges over a normal picture.
4. Peaking → **Off** → OK. Turn the ring. Expected: magnified view at once, no lines.
5. Power off, power on. Expected: the row still says Off. Set White again.
6. OK → Picture Mode strip → RIGHT through all looks and back. Expected: no crash.
7. Set Home, AF Illuminat. and Face Priority (the rows after Peaking) open; group J still has six rows.

| Result | Meaning |
|---|---|
| The row shows Off or Black at step 1 | the stored value of setting 458 is not 3 on this camera. Report it; choose White |
| The row shows no value | the stored value is outside 1 to 3; the lines are white. Choose a value once |
| Black lines too thin | gain 0xFE00 in T_K2 is the next build |
| The Custom Menu stops or a row opens the wrong screen | an error in the insert. Flash the pinned build |

Flash: `epm2flash peaking-menu 07f25fd8b7e2cce65a311a48c475c9d28558954f0c16ca18df771fc26221ce58`.
Go back: `epm2flash peaking-gain-2x ce1037cda6c9ff87e600272383dfe97b649a5ef24d6928e319b581191b4ca2c8`.

### 15.7 Files added

| Path | Contents |
|---|---|
| `patches/peaking-menu.json`, `builds/peaking-menu.json` | the spec and the build description |
| `scripts/mkspec_menu.py` | generator: `mkspec_menu.py OUT.json PINNED_DIR /tmp/scratch/asm [LISTING.txt]` |
| `scripts/scen_menu.py` | S8 to S11: `scen_menu.py all BASE_BLOCK0 PINNED_BLOCK0 MENU_BLOCK0` |
| `scripts/menu-emu/` | drivers of the full-boot emulator checks (copies; see its README.txt) |
| `results/menu-*.txt`, `results/scen-menu-*.txt` | listing, free-space check, hook check, op check, scenario outputs, emulator outputs |

## 16. Coloured lines: Off / White / Red / Yellow / Blue (`peaking-colours`)

Date: 2026-11-15. Status: `patches/peaking-colours.json`, build `builds/peaking-colours.json`, sha256
`4d6b1f26ed92d66b62b4d7dc32d26168e33fd8b153a7655d6c0d9a58267456f8`. Checked in emulation. **Not flashed.** The pinned build
`peaking-menu-names` still rebuilds to `4ea4ffd7…bc30`. Labels: **V** verified (bytes, or ran in the emulator),
**I** inferred, **U** unknown.

Camera report on the pinned build (2026-11-15): the row works, but white and black lines blend with the picture.

### 16.1 How the pass-9 combine handles colour

| Fact | Label |
|---|---|
| The combine job has three modes. The firmware prints their names: 0 `IMGDMA_ADD_YC`, 1 `IMGDMA_ADD_BAYER`, 2 `IMGDMA_ADD_RGB` (0x7E6DADB9). Key Line pass 9 uses mode 2 | V |
| Mode 2 (handler 0x7E707A1B) multiplies every width of the job by 3: the two inputs and the output are 3 bytes per pixel. In live view they are 640 × 480 × 3 = 921,600 bytes each | V (scenario) |
| The job has **one gain per input** (`usGain1`, `usGain2`), written to one register word (0x7E561FEF: `usGain1` \| `usGain2` << 16). No gain or offset per plane. The five words beside it are set to 0 for every job | V |
| So the job cannot give a colour: it adds the same share of the line image to all three bytes of a pixel | V |
| Pass 7 makes the picture (IMG job, `ucType` 23, stages 1, 3, 16, 27) and pass 8 the line image (`ucType` 23, stages 8, 9, 23, 30) in this format. Pass 9 adds them in place. Pass 10 turns the result back into YC (`ucType` 15, stages 8, 24, 25, 30) | V (scenario) |
| The three bytes are R, G, B. Basis: the name ADD_RGB against ADD_YC for the 2-byte format. The order of the three bytes was not found in the firmware | I for RGB, **U** for the order |
| The line image is grey (three equal bytes), 0 away from edges. Basis: white lines on the camera with + 2 × line, clean dark lines in Key Line with − 1 × line | I |
| The buffers have addresses 0xB5……: the image-work heap gives the 0xA0000000 alias of RAM. 0x7E45DB37 turns 0x6……… into 0xA……… before a record goes to the other CPU, so this alias is the one without the CPU cache | V for the alias, I for "no cache" |
| The art task queues the job and the pass returns (0x7E722610). The next pass starts when the job's bit is set in the pass word. One pass = one job | V |

Later bodies: the E-M1 4.6 and the E-M10 II 1.4 firmware (white, black, red, yellow) were unpacked. Both have
`PEAKING_COLOR_RED :3` and `PEAKING_COLOR_YELLOW :4`, and no `ART_EXPOSE_PEAKING`, no `IMGDMA_ADD_*`, no
`artclearline` text. Their peaking fields (`PeakingColor`, `PeakingLevel`, `PeakingHighlight`) are in a display
status dump beside `VscUpdate`, and the image parameters are another structure (`IMGPRO_MDL_IMAGE_PARAM`). So they
do not colour the lines in this art engine (**I**), and there is nothing to copy. The E-P5 1.8 has white and black
only (§3.1).

### 16.2 Design

For Red, Yellow and Blue, new code in pass 9 (`T_COL`, 292 bytes with its table) writes the colour into the
picture buffer where the line image is 64 or more. Then the combine job runs with `usGain2` = 0, so it writes
the picture back as it is. White is the pinned build's pass (gain 512) and Off is as before.

- The loop reads the line image 12 bytes (4 pixels) at a time. A group with no byte of 64 or more is skipped. In
  the other groups the middle byte of each pixel decides. About 940,000 instructions for a 640 × 480 frame (**V**
  in the scenario); the time on the camera is **U**.
- A frame that the loop cannot take (no rows, or a buffer that does not start at a multiple of 4) gets white lines.
- Rejected: two more combine passes (picture − line, line − a constant pattern image, then the add). They need a
  third 921,600-byte buffer that the CPU fills in every frame, and two more jobs. A coloured line image that is only
  added blends with a bright picture, which is the fault that the owner reported.

| Value of setting 458 | Text | Bytes written | Y, Cb, Cr (BT.601 full range, if the bytes are R, G, B) |
|---|---|---|---|
| 1 | Off | – | – |
| 3 (after a full reset) | White | none: picture + 2 × line | – |
| 2 (was Black) | Red | 255, 0, 0 | 76, 85, 255 |
| 4 | Yellow | 255, 255, 0 | 226, 1, 149 |
| 5 | Blue | 0, 80, 255 | 76, 229, 74 |

Blue has some green so that it is as bright as Red. Pass 10 makes the real YC values in the image processor; its
matrix was not read (**U**). Black is gone. A camera that is set to Black shows Red.

### 16.3 What the patch changes

112 edits. A delta on the pinned build. Generator: `scripts/mkspec_colours.py`.

| Part | Edit |
|---|---|
| Mode controller | Record 0x7E84C584 of setting 458: value list 0x7E849F25 (1, 2, 3) → 0x7E849F28, the first 5 bytes of the stock list 1 … 10; count 3 → 5. Two bytes |
| List | Five items at **0x7EBF2A00** (140 B) and the value → text list at **0x7EBF2B00** (144 B); the descriptor 0x7F00BFBC and entry 607 of table 0x7F014614 point to them. The old lists at 0x7EBF2900 and 0x7EBF2960 stay without a reader |
| Code | `T_K3`, `T_COL` and the colour table at **0x7E4C93F0** (kernel range, after `T_K2`). `T_K2` starts with `jmp T_K3`. No new RAM; 24 bytes of the art task's stack |
| Texts, 34 languages | The pointers of the ids 1501, 1502 and 1499 go to the colour names inside the stock texts 122 "R:Red", 124 "Ye:Yellow", 117 "B:Blue" (the B&W filter list), after the colon. No string is changed |
| English help 1506 | "Show lines in that color / on sharp edges while / MF Assist magnifies." |

White (1500) and the row name (1505) are still English only.

### 16.4 Checks

| Check | Result | Label |
|---|---|---|
| `.venv/bin/epm2mod make builds/peaking-colours.json` | sha256 `4d6b1f26…56f8`; free-space check PASS, 0 FAIL, no `first_code` (`results/colours-freespace-check.txt`) | V |
| `tools/emu/opcheck.py builds/peaking-colours.json` | 16 specs, 0 FAIL | V |
| `tools/emu/hookcheck.py` | this spec: 4 transfers, all kernel → kernel, 0 FAIL | V |
| Boot, `stage2-boot.mjs 2000` | PASS; the report equals the pinned build's except the wall time (`results/colours-emu-boot.txt`) | V |
| The list | Off, White, Red, Yellow, Blue; screens `~/opt/om-emu-e101-boot-work/peaking-colours/screens/01` … `09` | V |
| Each value over a restart | Red, Yellow, Blue, Off, White: each is stored (tag 0x8971 = 2, 4, 5, 1, 3) and read back after a restart, in the tag and in the row (`results/colours-emu-persist.txt`). The emulator carries the bank's RAM image over in place of the power-off save | V for the load, I for the save |
| Shallow crawls of the pinned build and this build: P without card, iAUTO, ART with card, movie with card. One more unit, `custA`, opens the lists of group A | in each mode only the Peaking list differs: its 3 old positions, and 2 new ones. All other screens byte-equal (450, 248, 284, 277 screens); logs equal (`results/colours-emu-crawl-shallow.txt`) | V |
| The colour names in the built file | read back for all 34 languages (the generator prints them) | V |
| S1 to S8 on this build (`results/scen-colours-s1-s5.txt`, `-s6-s7.txt`, `-s8-s11.txt`) | pass, with the result lines of the earlier builds | V |
| S9 to S11 of `scen_menu.py` | written for the pair `peaking-gain-2x` / `peaking-menu`. They report FAIL here for three reasons, none a fault: S9 counts the pinned build's own `T_K2` instructions as lost stock code (memory writes and device accesses are equal); S10 and one row of S11 expect black lines for value 2; one row of S11 expects a reference image without `T_R`. S12 to S14 replace them | V |
| **S12** Red, Yellow, Blue on a synthetic frame. The test writes a picture and a line image with an edge into the two pass-9 buffers of a live-view frame; the firmware's code runs on them | every one of the 307,200 pixels equals the model: line byte ≥ 64 → the colour (9,360 pixels), else the old pixel. Line values 32 and 63 leave the pixel, 64, 128 and 255 colour it. `usGain2` 0, registers kept, a picture in every frame. White: both buffers untouched, `usGain2` 0x0200 (`results/scen-colours-s12.txt`) | V |
| The pictures of S12 | `~/opt/om-emu-e101-boot-work/peaking-colours/frames/`: `s12-3-red.png`, `s12-4-yellow.png`, `s12-5-blue.png` (read from emulator memory), `s12-0-picture-before.png`, `s12-1-line-image.png`, `s12-2-white-model.png` (a model of picture + 2 × line: the emulator does not compute the image processor's add) | V, White I |
| **S13** White (values 3, 0, 6) against the pinned build; Off against the build without peaking | 24 frame comparisons, all the same: memory writes, device accesses in order, no stock pc lost (`results/scen-colours-s13.txt`) | V |
| **S14** `T_K` alone on an 8 × 2 frame, packet mode 2 / 0, L2, C = 0 … 6; odd buffer addresses; no rows | 31 rows as the model; sp, d2, d3, a2, a3 kept (`results/scen-colours-s14.txt`) | V |

Not checked, the camera must show it: the colours on the screen (byte order, RGB or not); the speed of the loop;
the line image values (the threshold 64); CPU access to the buffers through the 0xA… alias.

### 16.5 Camera test

Setup: MENU → Custom Menu → A → MF Assist → On. OK → AF mode → MF. A lens with a focus ring.

1. MENU → Custom Menu → A → Peaking. New: the list is Off, White, Red, Yellow, Blue.
2. Choose **Red** → OK. Leave the menu, turn the focus ring. Expected: magnified view, red lines on sharp edges.
3. The same with **Yellow** and **Blue**.
4. **White**: light lines as before. **Off**: no lines.
5. Set Red. Power off, power on. Expected: the row says Red.
6. OK → Picture Mode strip → a film look (for example Velvia) → OK. Turn the ring. Expected: no crash, red lines.

| Result | Meaning | Next build |
|---|---|---|
| Red shows blue, Blue shows orange, Yellow shows cyan | the bytes are B, G, R | the table with the bytes swapped |
| Other tints (green, pink), not the three names | the buffer is not RGB | report each colour seen; the table gets Y, Cb, Cr values |
| The view is slower with a colour than with White | the loop takes too long | read through the cached alias, or every second row |
| No lines with a colour, lines with White | the line image stays below 64 | threshold 32 |
| Coloured dots all over the picture | the line image has noise above 64 | threshold 128 |
| Freeze when the ring turns with a colour | the CPU cannot use the buffers this way | card update with the pinned build; report |

Flash: `epm2flash peaking-colours 4d6b1f26ed92d66b62b4d7dc32d26168e33fd8b153a7655d6c0d9a58267456f8`.
Go back: `epm2flash peaking-menu-names 4ea4ffd773d6f05d16867f55b9fef4bce5d53fc8659a9b16362f7ac771a6bc30`.

### 16.6 Files added

| Path | Contents |
|---|---|
| `patches/peaking-colours.json`, `builds/peaking-colours.json` | the spec and the build description |
| `scripts/mkspec_colours.py` | generator: `mkspec_colours.py OUT.json PINNED_DIR /tmp/scratch/asm [LISTING.txt]` |
| `scripts/scen_colours.py` | S12 to S14: `scen_colours.py all BASE_BLOCK0 PINNED_BLOCK0 COLOURS_BLOCK0 [PNG_DIR]` |
| `scripts/colours-emu/` | drivers of the full-boot emulator checks (copies; see its README.txt) |
| `results/colours-*.txt`, `results/scen-colours-*.txt` | listing, free-space check, hook check, op check, scenario and emulator outputs |

## 17. Speed: where the time goes, and a faster colour loop (`peaking-fast`)

Date: 2026-11-15. Status: `patches/peaking-fast.json`, build `builds/peaking-fast.json`, sha256
`0e8a25b9578b8119b14b4895be7d2a0b70d7315e5e817758699777f0f31d917e`; measuring build `builds/debug-log-peaking-fast.json`,
sha256 `21c811f733e132742f6f75e05282eafeba66c793d28e5a5e2293ea829bb3df49`. Checked in emulation. **Not flashed.** The pinned
build `peaking-colours` still rebuilds to `4d6b1f26…56f8`. Labels: **V** verified (the log, the bytes, or ran in the
emulator), **I** inferred, **U** unknown.

Camera evidence (log evaluation 1, build `debug-log`): 3 to 7 frames per second while coloured lines show.

### 17.1 The time budget

| Fact | Label |
|---|---|
| 72 frame periods, 145 to 342 ms. In one run the period moves smoothly as the ring turns: 342 → 151 → 341 ms (Yellow), 145 → 203 ms (Red, after its first frames). It is not a step of a fixed clock | V (log) |
| From the frame's first record (`film_stage`, plain job) to `pk_pass9`: 131 to 316 ms. `pk_pass9` is written after the colour loop. From `pk_pass9` to the next frame's first record: 22 to 27 ms in all 9 cases | V (log) |
| These 22 to 27 ms hold the combine job (two inputs and one output of 921,600 bytes), pass 10, the display update and the start of the next frame. So one pass of the image processor over the frame takes about 10 ms or less | I |
| The 131 to 316 ms hold the line job, the passes 1, 7 and 8, and the colour loop. If the three passes and the line job cost about 10 to 15 ms each, the pipeline needs 40 to 60 ms and the loop the rest: 70 to 250 ms | I |
| The image processor does the same work for every picture. The colour loop does not: it does more for every line pixel (4 byte reads per group, 3 byte writes per pixel). So the part that moves with the focus, 145 → 342 ms, is the loop (it is slowest when the picture is sharp) | I, strong |
| White has no loop. The owner did not report White as slow | I |
| The firmware plans 85 ms for this frame. 0x7E6C365F estimates a frame time per art code (0x7E6CC18E: Key Line I 85 ms, or 50 ms with bits 0–1 of record +96; Key Line II 85, 150 or 310 ms), rounds it up to 30 / 50 / 85 / 150 / 180 / 310 / 485 / 985 ms, and 0x7E6C35F0 turns that into a rate of 30 / 15 / 10 / 6 / 5 / 3 / 2 / 1 frames per second (table 0x7E7FD9F0; 230 ms gives 4). Peaking asks for 85 ms = 10 per second, as the E-P5 does (hook H) | V |
| What the rate drives (sensor, display, a time-out) | U |
| So the stock Key Line filter is planned for 10 frames per second at most, and peaking cannot be faster than that with this pass list | V for the plan, U for what the camera reaches |
| CPU work of one peaking frame in the scenario rig: 1,013,000 instructions, of which the loop is 849,000 (no line pixel) to 940,000 (the synthetic frame, 3 % line pixels): 84 % or more | V (emulator) |
| Bus accesses of the pinned loop per frame: 230,400 word reads, and for each line pixel 1 byte read and 3 byte writes. All go to the 0xB5… addresses, the alias of the RAM without the CPU cache (§16.1) | V for the code, I for "no cache" |
| What one such access costs. The CPU core clock (clock 0 is 162 MHz: hardware notes, I) | U |
| A scale from the log: `log_put` (about 40 instructions, 8 accesses to uncached RAM, 1 timer read) ran between two records that are 1 to 2 µs apart. So this kind of code runs 20 instructions per µs or more, and 849,000 instructions without line pixels are about 40 ms or less | I |
| The E-P5 has no CPU loop. White and black come from the combine job (mode 3, gains ± 2048), with its own line job (`ucProcCount` 11) and 4-byte passes. These need its IMG library (§11.2). Its picture size in peaking was not compared | V, size U |
| The share of the magnified view, and the frame rate of MF Assist with Peaking Off | U (no record per frame in that state) |
| The debug build's probes: 2 to 3 records per frame, about 150 instructions | V: not a cost |

**What dominates:** with a sharp picture, the colour loop (**I**). At the floor of 145 ms the split between the loop
and Key Line's own passes is **U**. Section 17.5 gives a measurement that needs no flash.

### 17.2 Options

| # | Option | Gain | Risk | Verdict |
|---|---|---|---|---|
| 1 | Loop: every second row; 2 word reads per group of 4 pixels; the colour over the whole group in both rows with 6 word writes | Instructions 849,172 → 309,923 (no lines), 940,434 → 330,175 (synthetic frame). Word reads 230,400 → 76,800. A group with line pixels: 12 to 24 byte writes and 8 byte reads → 6 word writes | The lines are drawn in blocks of 4 × 2 pixels of the 640 × 480 picture. How coarse that looks on the screen is U (S12 picture: a slanted line with small steps) | **built** |
| 2 | As 1, but each pixel tested and written alone | The part without lines as 1. The part with lines stays as slow as pinned | none | not built. The next build if the blocks look coarse |
| 3 | Read the line image through the cached alias | U. The image processor writes the buffer in every frame, so 28,800 cache lines must be invalidated per frame first. The rig has no cache | a stale picture or a fault; no emulator test | not now |
| 4 | Half of the rows on CPU 1 | at most 2 × for the loop | needs a call between the CPUs and a wait in the ART task | only if 1 is not enough |
| 5 | Colour in the image processor: two more combine passes with a constant-colour image | removes the loop, adds about 20 ms (I) | No threshold: the colour is added to the picture and blends with it, which is the fault that led to §16. The constant image needs a 921,600-byte buffer that survives the frames | rejected again |
| 6 | A shorter pipeline: drop a pass, a smaller work image, the E-P5 pass list | U until the pipeline's share is measured | the E-P5 list is not portable (§11.2) | wait for 17.5 |
| 7 | Frame time 50 ms in place of 85 | only if a frame then needs less than 66 ms | low | wait for 17.5 |

### 17.3 What was built

`patches/peaking-fast.json`, a delta on the pinned build, 3 edits (generator `scripts/mkspec_fast.py`):

| Edit | Bytes |
|---|---|
| `T_FAST` at **0x7E4C9184** (117 B) and `T_HIT` at **0x7E4C90CA** (32 B): two 0xFF runs of the kernel range, on both sides of the 240-frame list | new |
| `T_COL` of the pinned build, the first 5 bytes of its row loop at 0x7E4C9453 → `jmp T_FAST` | `expect` is the pinned code |

- The pinned set-up (colour, buffers, sizes, checks) and its two exits stay in use. The old loop stays in place without a reader.
- `T_FAST` tests bytes 0–3 and 8–11 of each group of 12 in every second row. The line image is grey (§16.1, **I**),
  so this sees all four pixels. A byte of 64 or more: `T_HIT` writes the colour over the group in this row and the next.
- With an odd number of rows the last row is left alone. One row, or a row length that is not a multiple of 4 bytes:
  white lines, as for the other frames that the pinned loop cannot take.
- White and Off do not reach the new code. No new RAM; 16 more bytes of the ART task's stack.

The measuring build is `peaking-fast` + `log-core` + `log-probes` + `patches/log-peaking-time.json` (generator
`mkspec_log.py --peaking-time`): event **`pk_stats`**, one record per 8 runs of Key Line pass 9. Two hooks in stock
bytes of pass 9, 0x7E72675C (before hook K) and 0x7E726774 (after the gain is stored), read the microsecond timer. The
record holds the sum of the 8 times and `usGain2`. For a colour the time is the loop. For White and for the Key Line
art filter it is a few microseconds, and the record still gives the frame period: 8 periods between two records. The
spec changes no byte of the peaking code. It puts the new build id `fe2f543f94c74a91` of `logs/events.json` into the
block header; the log of the flashed `debug-log` still decodes with `logs/events-d1ddd46b4dac2414.json`.

### 17.4 Checks

| Check | Result | Label |
|---|---|---|
| `.venv/bin/epm2mod make` for both builds | the two sha256 above; free-space check PASS, 0 FAIL, load order 0 FAIL (`results/fast-freespace-check.txt`) | V |
| `tools/emu/opcheck.py` | 17 and 20 specs, 0 FAIL (`results/fast-opcheck.txt`) | V |
| `tools/emu/hookcheck.py` | `peaking-fast` 5 transfers, `log-peaking-time` 6 transfers, all between the kernel range and segment 1, 0 FAIL (`results/fast-s0-hookcheck.txt`) | V |
| Boot, `stage2-boot.mjs 2000` | PASS. `peaking-fast` = pinned and `debug-log-peaking-fast` = `debug-log` but the wall time (`results/fast-emu-boot.txt`). The boot does not run pass 9 | V |
| **S12** Red, Yellow, Blue on the synthetic frame (`scripts/scen_fast.py`) | every one of the 307,200 pixels equals the block model; the line image is not changed; `usGain2` 0; registers kept. Pinned colours 9,360 pixels, fast 10,800; 1,560 pixels differ (60 coloured only by pinned, 1,500 only by fast). Pictures: `~/opt/om-emu-e101-boot-work/peaking-fast/frames/` | V |
| Instructions from hook K to the next stock instruction | no lines: 849,172 → 309,923. Synthetic frame: 940,434 → 330,175. White: 19 → 19 | V |
| **S13** White (3, 0, 6) = pinned, Off = the build without peaking | 24 frame comparisons, all the same: memory writes, device accesses in order, no stock pc lost (`results/scen-fast-s13.txt`) | V |
| **S14** `T_K` alone on small frames: 28 mode rows; 7 sizes × 3 colours × 6 line images (odd row counts, widths that are not a multiple of 4, 640 × 6); one row, 27-byte rows, unaligned buffers, no rows → white, nothing written | PASS; guard bytes round the picture untouched | V |
| **S18** the timing probe: both routines alone for 20 passes; 18 frames each of Red, White and the Key Line art filter against `peaking-fast` | PASS. Alone: registers kept, the replaced instructions ran, records (180,419 µs, 0xFF00) and (120,419 µs, 0x0200) as the model. Frames: the same gains as `peaking-fast`, the same Red picture, two records each with the gain 0 / 0x0200 / 0xFF00. The emulator's timer goes down by 1 per read, so the frames do not test the times (`results/scen-fast-s18.txt`) | V |
| S15 to S17 of the log (`scen_log.py`) with `peaking-fast` and `debug-log-peaking-fast` | S16 and S17 PASS. S15: in all 16 frame comparisons no byte differs outside the log's RAM and the device accesses are the same but the timer reads; the same gain and `ucExpose`. It prints FAIL for "3 stock pcs lost" in pass 9: they are the replaced instructions 0x7E726770, 0x7E726771 and 0x7E726776. The hook PK9 and the new hook at 0x7E726774 touch, so the rig takes the 12 changed bytes for new code and not for hook sites (`results/scen-fast-log-s15-s17.txt`) | V; which 3 pcs: I, from their number |
| Unit tests, `mypy`, `black` | 168 tests pass | V |

Not checked, the camera must show it: the time of the loop and of the pipeline; the look of the blocks; that the line
image is grey enough for the two-word test (a line pixel whose middle byte alone is 64 or more would be missed in
pixels 1 and 2 of a group).

Side effect: `builds/debug-log.json` no longer passes the free-space check, because `peaking-fast` edits bytes of
`peaking-colours` and `log-peaking-time` edits the build id in `log-core`. It is the same case as `builds/peaking-menu.json`
after `peaking-colours`. `build/debug-log.BIN` is not changed. To build it again, record its sha256 with `epm2mod pin`.

### 17.5 Camera test

Setup for both parts: MENU → Custom Menu → A → MF Assist → On. OK → AF mode → MF. Camera on a table, a page of
text about 1 m away, in focus. A card in the camera.

**A. No flash**, if `debug-log` (`e74f1aec…`) is still on the camera. It tells the loop from the pipeline.

1. MENU → Custom Menu → A → Peaking → **White** → OK. Leave the menu. Turn the focus ring a little to and fro for
   10 s, so that the text stays nearly sharp. Wait until the zoom ends.
2. Peaking → **Red** → OK. The same 10 s.
3. Peaking → **Off** → OK. The same. By eye: is the zoomed view smoother than with White?
4. OK → Picture Mode → **Key Line** → OK. Look at live view. By eye: as fast as White peaking? Then set the look back.
5. MENU. Power off. `uv run epm2mod log /path/to/EPM2LOG.BIN --summary`.

Read the two lines `run at … s, White [3]` and `run at … s, Red [2]`:

| Result | Meaning |
|---|---|
| Red's median frame period is 40 ms or more above White's, and so is "frame start to the end of the colour pass" | the loop is the cost: flash part B |
| Both about equal | the loop is not the cost. The time is Key Line's pipeline; `peaking-fast` will not help much. Options 6 and 7 |
| White itself at 100 ms or less | the pipeline reaches the planned 10 frames per second |

**B. Flash** `debug-log-peaking-fast` (it is `peaking-fast` with the log).

1. Peaking → **Red**. Turn the ring to and fro for 10 s. Expected: red lines in small blocks, the view smoother than before.
2. Peaking → **White**. The same 10 s. Expected: as before.
3. OK → Picture Mode → **Key Line** → OK. Hold live view for 10 s without the ring. Set the look back.
4. MENU. Power off. `uv run epm2mod log /path/to/EPM2LOG.BIN --summary`. Press MENU at least once per 40 s of
   peaking: the log keeps 512 records per CPU between two menus, and each frame still gives one (`film_stage`).

Read the lines under `pass 9 timing`: one for Red, one for White, one for the Key Line art filter, each with the
frame period and the time of the peaking code per frame.

| Result | Meaning | Next |
|---|---|---|
| Red: the code takes 10 ms or less and the period is near White's | the loop is solved | flash `peaking-fast` for use; pin it |
| Red: the code still takes 30 ms or more | the bus accesses are slow even in the short loop | every fourth row, or option 3 |
| White's period = the Key Line filter's period | peaking adds nothing to the stock filter; the rest is the pass list | options 6, 7 |
| The blocks look coarse | | option 2 |
| No coloured lines, or lines only on thick edges | the line image is not grey, or below 64 in the tested bytes | report; test all three words again |
| Freeze when the ring turns with a colour | a fault in the new loop | card update with the pinned build |

Flash: `epm2flash debug-log-peaking-fast 21c811f733e132742f6f75e05282eafeba66c793d28e5a5e2293ea829bb3df49`.
For use, after B: `epm2flash peaking-fast 0e8a25b9578b8119b14b4895be7d2a0b70d7315e5e817758699777f0f31d917e`.
Go back: `epm2flash peaking-colours 4d6b1f26ed92d66b62b4d7dc32d26168e33fd8b153a7655d6c0d9a58267456f8`.

### 17.6 Files added

| Path | Contents |
|---|---|
| `patches/peaking-fast.json`, `builds/peaking-fast.json` | the spec and the build description |
| `patches/log-peaking-time.json`, `builds/debug-log-peaking-fast.json` | the timing probe and the measuring build |
| `scripts/mkspec_fast.py` | generator: `mkspec_fast.py OUT.json PINNED_DIR /tmp/scratch/asm [LISTING.txt]` |
| `experiments/2026-11-15-log/scripts/mkspec_log.py --peaking-time` | generator of the timing probe |
| `scripts/scen_fast.py` | S12 to S14: `scen_fast.py all BASE_BLOCK0 PINNED_BLOCK0 FAST_BLOCK0 [PNG_DIR]`; S18: `scen_fast.py s18 FAST_BLOCK0 DEBUG_FAST_BLOCK0` |
| `logs/events.json`, `src/epm2mod/logsummary.py` | event `pk_stats`; the summary prints one line per peaking run and the lines `pass 9 timing` |
| `results/fast-*.txt` | listings, free-space check, hook check, op check, boot report, scenario outputs |
