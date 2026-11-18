# Code space from the PENPAL (PP-1 Bluetooth) code

Question (owner, 2026-11-18): can we remove the PENPAL transmit code and reuse its bytes for the look editor?
Labels: V camera-verified, E emulator-checked, R read in code, I inferred, U unknown.
Scratch output: `out/penpal-core.txt`, `out/penpal-patchram.txt`, `out/penpal-operands.txt`, `out/btc-api.s`,
`out/stack-callers.txt`. Sources: `build/map/` (function DB and calls), `tools/freespace.py` (run with a scratch
copy of the candidates file; no tracked file changed).

## Answer in short

- The Bluetooth code is one block in segment 2, 272,381 bytes, with few doors from the rest of the firmware (R).
- **Step 1, ready to build:** the Broadcom patch-RAM download, 57,523 contiguous bytes (0x7E904B2E-0x7E912BE1).
  It has exactly 2 callers. Two 7-byte NOP patches and a 1-byte gate patch close it. That is 85 times the
  679 B proven today (R).
- **Step 2, more work:** the rest of the stack (about 210 KB more). It has 91 call sites from the BT_CTRL task,
  a boot call and 29 API entry points. It needs stubs and an emulator trace first (R, I).
- An E-PM2 owner without a PP-1 loses nothing. With a PP-1, Bluetooth sharing stops. EVF, SEMA-1, flash,
  FlashAir and Eye-Fi do not use this code (R).

## 1. Where the code is

All in segment 2 (loaded at boot by Usr1, the same segment that runs the card-looks code, V).

| Range | Bytes | What | Called from outside the BT block |
|---|---|---|---|
| 0x7E8F926F-0x7E9035A8 | 41,785 | BT_CTRL task, `[btc api]` 0x7E8FD075-0x7E8FD899 (29 functions), pairing, OPP/BIP | Boot 0x7E5053B7; `api_cube_*` (segment 1); ADJ overlay 0x7F083BFF, 0x7F08440D |
| 0x7E9035A8-0x7E904B2E | 5,510 | `bt` debug shell | 3 shell tables (pointers) |
| **0x7E904B2E-0x7E912BE1** | **57,523** | **27 Write_RAM chunks + Launch_RAM + `bt_config_set` 0x7E9126CC** | **none** (2 callers, both in the BT block) |
| 0x7E912BE1-0x7E913984 | 3,491 | HCI vendor commands, UART transport, gate `cube_enabled` 0x7E91367A | inside only |
| 0x7E913984-0x7E91D29F | 39,195 | BTAPI glue, Blue SDK part 1, Apple iAP | task table (BTIAP) |
| 0x7E91D29F-0x7E937CDE | 109,119 | Blue SDK part 2: L2CAP, ME/SEC, OBEX, RFCOMM, SDP, SPP | task table |
| 0x7E937CDE-0x7E93BA6C | 15,758 | OBEX-ACP glue, OBEX and OBEX_ACP tasks | task table, 2 shell entries |
| **Total** | **272,381** | 1,531 functions | |

Outside the block, kept: `play_cube_*` (inside the playback engine), `api_cube_*` 0x7E676693-0x7E6772E0
(segment 1), `DevBlu_Bluetooth` 0x7EBA29E3-0x7EBA3243, and the BT strings and tables near 0x7EBAD000-0x7EBB6000
(size not measured, U).

Separation from playback and audio: clean. No playback, audio, SERV_MAIN or EFFECT function calls into the
block. Nothing in the block is called by them (R, `calls.tsv`). SERV_MAIN ends with `ret` at 0x7E8F926C. The
playback engine starts at 0x7E93BA6C.

## 2. Doors into the block

| Door | Kind | When it runs |
|---|---|---|
| 0x7E5053B7 → 0x7E8FAE8B | call at boot | Every boot: it starts tasks BT_CTRL (0x61) and BTIAP (0x62), then waits 700 ticks (R) |
| `api_cube_*` → `[btc api]` (33 call sites) | calls | GUI PENPAL pages; Reset (`Delete_All_BT_Infomation` from 0x7E9E7AD1); PENPAL Album copy (`app_media_copy_cube_copy` 0x7EB0A78E) |
| 0x7F083BFF, 0x7F08440D | calls from the ADJ overlay | USB factory op 0x902A only; both targets check the gate first (R) |
| Shell tables 0x7E7327C8, 0x7E7333D8, 0x7EBCC3E0 | pointers `bt`, `obex`, `acp` | UART or USB ADJ debug shell only |
| Task table 0x7E4397E8-0x7E4398AC | 8 task entries | Only BT_CTRL and BTIAP are started at boot. The other 6 are started by the stack init 0x7E92F0FE, which runs only after the gate (R) |
| .data 0x7E8DF674-0x7E8DF6A0 | OBEX state table | Read by OBEX code (I) |

The gate: `cube_enabled` 0x7E91367A returns 1 only when status 0x1709 ("Cube") reads 0. That bit is set
only when accessory ID 0x0103 answers on the accessory bus (R, section 10e). Only the gate and the ADJ status
packet read 0x1709 (R).

**If the gate always returns 0, is all BT code unreachable? No.** Of the 29 `[btc api]` functions, only 7
check the gate. 10 post a request to the BT_CTRL queue (0x7E8FD025, `OlyQeWr` with no timeout) and the task
handles it. Some are plain getters (R). So with the gate closed, BT_CTRL, `[btc api]` and their request handlers
still run when a PENPAL page opens. The radio bring-up 0x7E8FE4B0 checks the gate at 0x7E8FE506 **before**
HCI reset, patch-RAM download and BD_ADDR (R). Everything behind the bring-up is dead with the gate closed.

### Step 1 patch (closes the patch-RAM block)

| Address | Stock | New | Why |
|---|---|---|---|
| 0x7E913685 | `80 01` (mov 1,d0) | `80 00` | `cube_enabled` always returns 0. On a body without a PP-1 this is already the stock result |
| 0x7E8FE23D | `dd 8f 44 01 00 00 04` (call bt_config_set) | 7 x `cb` (nop) | return value not used; only reached after the gate |
| 0x7E903A4F | `dd 7d ec 00 00 00 04` | 7 x `cb` | `bt` shell sub-command; next instruction is `jmp` to the epilogue |

After this, 0x7E904B2E-0x7E912BE1 has no caller (R). The bytes before it end with `ret` at 0x7E904B2B (tool
check `predecessor` PASS).

### Step 2 (whole block): what it needs

- Replace the boot call 0x7E5053B7 with a stub that keeps the 700-tick wait.
- Replace the 29 `[btc api]` entries with stubs that return what the stock code returns with the gate closed.
  The 10 queue posts need an emulator trace: what BT_CTRL replies and which GUI events it posts. Keep
  0x7E8FD857 working (memset of 60 B): the PENPAL Album copy path calls it.
- Point the 3 shell entries (3 tables) and the 2 ADJ calls at stubs.
- Then the stubs are about 300 B (I), and about 270 KB is free in two runs (15 KB before `[btc api]`, 255 KB after).

## 3. Space and how the tools classify it

`freespace.py` result for 0x7E904B2E-0x7E912BE1 (scratch candidates row, `out/penpal-patchram.txt`):

| Check | Result |
|---|---|
| loaded | PASS: segment 2, Usr1 copy, every normal boot |
| content | PASS when listed as `code checked` |
| pointers | FAIL: 10 windows, all explained by hand (below) |
| operands | FAIL: the 2 calls that Step 1 removes |
| written | PASS |
| predecessor | PASS: `ret` at 0x7E904B2B |

The 10 pointer windows (all noise, R from the bytes):

| Site | Why it is not a pointer |
|---|---|
| 0x7E765199, 0x7E766A23, 0x7E766F57, 0x7E76748B | byte ramp `7a7a7a7a7a7a7a80`, through the flash-uncached alias |
| 0x7E43C3B2, 0x7E43DC5A | unaligned window across RAM addresses 0xA075xxxx / 0xA076xxxx |
| 0x7F0DFB30 | low word of a double (0x407AF4A5BEA0BA1F, about 431) |
| 0x7E51C3B8 | inside instructions `add -4,sp; mov a0,a2; mov (a2),d2` |
| 0x7EBCA6F1, 0x7EBCA847 | unaligned window in a halfword table |

Tool changes (proposed; not made):

1. A row in `docs/space-candidates.tsv`: `7E904B2E 7E912BE1 code checked`, evidence this file.
2. Rows in `docs/space-pointer-waivers.tsv` for the sites above.
3. The `operands` check has no notion of a call that a spec removes. Proposal: a hand file of cut call sites
   (site, stock bytes, new bytes, evidence). `check` accepts an operand from such a site only when a spec in the
   same build writes the new bytes there.
4. The area stays NEEDS-DECISION until then. It becomes USABLE-CODE after a camera-tested spec runs code in it.

## 4. What an E-PM2 owner loses

| Feature | After Step 1 | After Step 2 |
|---|---|---|
| PENPAL Share (Bluetooth send, pairing, receive) | Off: same as a body with no PP-1 attached (R) | Off |
| PENPAL Album | U: its copy path does not call the gate. With the gate closed it may still work, or may not | U: stubs decide |
| Accessory-port menu (hidden by default, info 394) | Opens; PENPAL pages behave as with no PP-1 (I) | Same, if the stubs are right (E needed) |
| EVF VF-2/VF-3/VF-4, SEMA-1, accessory flash | Unchanged: own status bits, detection code in segment 1 (R) | Unchanged (R) |
| Serial port shared with EVF and S_SHELL (SIO ch1) | Unchanged: the driver and BT UART code are outside the reclaimed range (R) | BT UART code removed; the SIO driver stays (R) |
| FlashAir, Eye-Fi, USB, HDMI | Unchanged: no calls into the block (R) | Unchanged (R) |
| Reset | Unchanged: gated call returns as on stock (R) | Stub must match (E needed) |
| Boot | Unchanged | Stub must keep the 700-tick wait |

Few owners have a PP-1. It was discontinued, and later bodies (E-M5 II, PEN-F) dropped the code.

## 5. Probe plan

### Emulator (before any flash)

1. `hookcheck.py`, `boot-test` and `update-path-test` on a build with the 3 patches, and with the range filled
   by a trap pattern.
2. A PC watch on 0x7E904B2E-0x7E912BE1 and a read watch on the same range during boot and through these menus:
   Setup → Menu Display → accessory-port menu on → PENPAL Share, PENPAL Album, Electronic Viewfinder; Reset;
   playback. Pass: no execute and no read in the range.
3. `freespace.py check` with the new rows.
4. For Step 2 only: trace each `api_cube_*` call in stock with no accessory. Record return values, queue posts
   and GUI events. These are the stub specifications.

### Camera (one flash)

Build: the 3 patches plus a small test routine placed in the range (for example 0x7E904B40), called from the
card-looks poll hook. It writes a marker to the debug log.

| Check | Pass |
|---|---|
| Boot, live view, take a photo | as stock |
| Marker in the log | code runs from the reclaimed range: makes it USABLE-CODE |
| Accessory-port menu on, open PENPAL Share | no freeze (an error message is fine) |
| Reset | completes |
| VF-4 or VF-2, if the owner has one | live view in the EVF |

The flash cannot settle the PENPAL Album question without a PP-1.

## Confidence

| Claim | Label |
|---|---|
| Patch-RAM block has only 2 callers, both behind the gate or in the debug shell | R (function DB plus constant scan, 4 aliases) |
| No computed calls into the block (its 27 chunks are called directly by `bt_config_set`) | R for the direct calls; computed calls I |
| Step 1 changes nothing for a body without a PP-1 | I (strong): the gate already returns 0 on such a body |
| Segment 2 runs added code | V (card-looks) |
| Step 2 size and stubs | I |
