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
