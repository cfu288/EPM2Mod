# The H.264 QP floor: what the byte at 0xA84A00 does (2026-11-12)

Labels: **V** = read in the code or run in the emulator; **I** = inferred. Runtime addresses are block 0 (offset + 0x7E421020).
Scratch: `/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/qp/`.

## Answer

- **0xA84A00 is a minimum QP, but only for the first frame of a recording.** It is the immediate of `mov 20,d0` at 0x7EEA5A1F, in the first-frame set-up 0x7EEA57D4. **V**
- **Every later frame gets its floor from a second copy:** `80 14` at **0x7EEA5EBB (offset 0xA84E9C)**, in the per-frame set-up 0x7EEA5C4C. **V**
- **A one-byte patch at 0xA84A00 leaves the floor at 20 from frame 2 on.** Shown in the emulator (V); the effect on the camera is **I**. A floor-16 test needs both bytes.
- The floor goes to a codec hardware register, and the hardware chooses each frame's QP. No software code clamps QP from below. **V** for the code; that the hardware enforces the floor is **I** (strong).

## 1. Where the floor byte goes

| Step | First frame (0xA84A00) | Later frames (0xA84E9C) |
|---|---|---|
| Set-up function | 0x7EEA57D4, run when ctx+104 = 0; it sets ctx+104 = 1 (V, emulator) | 0x7EEA5C4C, run when ctx+104 ≠ 0; it sets ctx+104 = 2 (V) |
| Selected at | 0x7EEA54CA in 0x7EEA527B: `(104,ctx) == 0` → 57D4, else → 5C4C (V) | same |
| Parameter struct | sp+164: +36 max QP 51, **+37 min QP 20**, +172 frame QP, +173 = 16, +32 kb/s | sp+176: +44 max 51, **+45 min 20**, +248 frame QP, +249 = 16 |
| Driver entry | vtable+20 = 0x7EEA3A4E copies these into drv+216..219 (V) | vtable+24 = 0x7EEA40A7 copies them into drv+478..481 (V) |
| Register image | 0x7EEC95EB: word = max<<8 \| min (6-bit fields) (V) | 0x7EEC9AF7: the same packing (V) |
| MMIO write | 0x7EEC87AD writes that word to **0x994043A8** (pointer table 0x7F032400; +0x400 per channel) (V) | same register (writer mode 2, the same branch) (V) |

- The frame QP and the byte 16 are packed the same way into **0x994043A4**: QP in bits 13:8, 16 in bits 5:0. Bits 5:0 are written only when status bit 15 is set (V). What the 16 means is unknown (I).
- ctx+104 is reset to 0 at stream start (0x7EEA4FE9) and, when ctx+984 = 1, at 0x7EEA53E9 (V). When ctx+984 is set was not traced.
- On the external-rate-control path (ctx+120 ≠ 0), both builders replace the max QP with the callback's value but keep the min (V). On the camera ctx+120 is probably 0 (I).

## 2. How the per-frame QP is chosen

- **Software proposes a QP; the hardware decides.**
  1. After each frame, the hardware status register 0x99404390 (low byte) gives the frame's QP (0x7EEC8CD8 → 0x7EEC6B01 → 0x7EEA3E0A out+8) (V).
  2. Frame-done 0x7EEA6194 → 0x7EEA7AE6 stores that QP in a 4-entry history at ctx+635..638, only when ctx+96 = 1 (V).
  3. The "rate control" 0x7EEA6B37 (and its twin 0x7EEA726B) sets the next proposed QP to the integer mean of the non-zero history bytes, or 33 at the start. It clamps to 51 at 0x7EEA725A (V, emulator).
  4. The rest of that function selects quantiser tables (ctx+560, from 0x7F030328 etc.) by a quality metric with thresholds 35/40–48. It does not read frame sizes against the target (V).
- **No other floor:** the encoder module (0x7EE80000–0x7EEE0000) has no `cmp 20`, and no lower clamp near any QP field (V). The other `cmp 20` hits (0x7EE8B9xx) are in unrelated code (I).
- **Frame-size model:** the status getter 0x7EEA3E0A turns the frame size into a new first-frame QP (drv+218):
  - normally the smallest q with Qstep[q] > Qstep[qp]·(size>>10)/168, using the table at 0x7F03026C (H.264 Qstep ×8);
  - on an overflow flag, min(qp+15, 51).
  - It has **no lower bound** (it returns 0 for tiny frames) and does not read the floor (V, emulator). The per-frame path does not use drv+218 (V), so this matters only when the first-frame registers are reprogrammed (I).
- **Mode: VBR with a QP floor, not constant QP** (I, strong):
  - the VUI says VBR (cbr_flag 0, 04);
  - the hardware gets the target in kb/s (struct+32 → drv+216 → 0x7EEC95EB) and the [min, max] pair;
  - the clip's first frame came out at QP 25 while software proposed 33 (V: the builder in the emulator gives 33 with an empty history; 04 gives frame 1 = 25), so the hardware picks its own QP;
  - one P-frame is at 22.

## 3. Emulator tests (tools/emu, cases `qp_setup`, `qp_rc`, `qp_size_model`)

- **Stubs:**
  - every codec-driver vtable entry points at scratch code `clr d0; rets`, and the struct is read from the dead stack;
  - for `qp_size_model`, 0x7EEC6B01 (hardware status) returns the row's size and overflow flag with reported QP 20, and 0x7EEC684A returns 300;
  - the rate control and 0x7EEA6A0B run natively.
- Context: 1920×1080, 20 Mb/s, 29.97 fps, ctx+96 = 1.
- All 37 rows match the Python models on stock. No stray code ran, and sp was balanced (V).
- Patched images (`specs/qp-floor-16.json` = 0xA84A00 only; `specs/qp-floor-16-both.json` = both bytes) were built in scratch and run with `emurun.py diff CASE --image`. tools/build.py and patchblock were not run.

| Case (rows) | 0xA84A00 only | Both bytes |
|---|---|---|
| `qp_setup` (8: first/later builder × history none, 20s, 16–18, 26–32) | first builder min 20 → **16**; **later builder stays 20**; 4 changed, 0 flagged | all 8: min 20 → 16 |
| `qp_rc` (14: histories none/20/16–18/25,20,20,20/26–32/60/12; GOP frame 0 and 3) | 0 changed | 0 changed |
| `qp_size_model` (15: qp 20/33 × size 0…2 M, plus 3 overflow rows) | 0 changed | 0 changed |

- **Under, at and over target** (V, the same on stock and patched):
  - At the floor: history [20,20,20,20] → proposed QP 20.
  - Under target: if the hardware reports 16–18, the next proposal is 16. Software passes values below 20 through unchanged; on stock they never appear, because the register floor is 20 (I).
  - Over target: [26,28,30,32] → 29, and [60…] → 51.
  - Size model, qp 20: size 75,000 → 14, 200,000 → 22, 2,000,000 → 42. With overflow: 20 → 35, 36 → 51.
- **The emulator cannot show** that the hardware will encode below QP 20. Rate control and QP selection are in the codec at 0x9940xxxx, which om-emu does not model. The tests show only that the floor-16 value reaches the struct that is packed into 0x994043A8, and that nothing in software brings it back to 20.

## 4. Risks once QP can drop to 16

- **Per-frame size limit:**
  - ulMaxCodeSize = 777,600 B (W·H·3/8; 02 B2, V).
  - At QP 20 the clip's largest frame is 129.5 KB (04). At QP 16 it would be about 1.6× (2^(4/6)), so about 210 KB: far below the limit (I).
  - Exceeding the limit only logs `AVSCA_INF_CODESIZE_OVER`; the QT callback does not act on it (02 B3, V). What the hardware does with a frame larger than its buffer is unknown (I).
- **Overflow:**
  - `AVSCA_INF_OVERFLOW` → RECMOVIE_BUFFER_LIMIT, and recording stops (02 B4, V).
  - In the driver, an overflow flag raises the reprogrammed QP by 15 (V, `qp_size_model`).
  - At about 13–20 Mb/s (1.6–2.6 MB/s) the SD path has 5× headroom or more (02 A5, I). A stop is likely only with a card that stalls.
- **The 20.48 Mb/s target and the 1 s HRD buffer:** the hardware gets the target (V). The clip never reached it, so we have **not seen** the hardware raise QP to hold the target (I). If it holds the target, the HRD stays valid.
  If it does not, a busy scene at QP 16 could exceed 20 Mb/s:
  - the declared HRD would be violated (players rarely check it, I);
  - the time limit (0x7E6EDE08) assumes the nominal rate, so the 4 GiB file cap would arrive earlier than predicted. What happens at 4 GiB was not traced (I).
- **200 KiB chunking:** frame-done (0x7EEA65CC) and 0x7EEA548F compare an output counter with 204,800 and call driver vtable+52 to fill the rest of a 200 KiB chunk (V). Its role (stream-buffer padding?) is **I**. A frame above 200 KiB at QP 16 would take this path more often; not tested.

## 5. Expected bitrate with both bytes at 16 (I)

- **Assumptions:** bits scale with about 2^(−ΔQP/6), giving ×1.4–1.6 for QP 20 → 16 (CAVLC with these matrices: not measured). The hardware keeps to the target when it is reached.
- **Static scene like PB120161:**
  - stock: 8.4 Mb/s (GOPs 5.1–16.3, 04);
  - expected: **about 12–14 Mb/s on average**;
  - GOPs that were above about 13 Mb/s would reach the 20.48 Mb/s target, so QP 17–20 there.
- **Busy scene** (one that already needs more than 20 Mb/s at QP 20): **no change, about 20 Mb/s.** The floor does not bind there.
- **A mid scene** at 13–20 Mb/s on stock → about 20 Mb/s.
- **Patching only 0xA84A00:** the first frame may come out at a lower QP, and the rest of the clip is unchanged (I). A camera test of that build would show "no effect" and could be misread as the floor not mattering.

## 6. Open items

- What QP the 0x99404390 status reports (slice QP or mean MB QP). Whether the hardware varies QP per macroblock: `qp.py` reads only slice QP.
- The 16 at struct+173/+249 (0x994043A4 bits 5:0): possibly another QP bound.
- Where ctx+96 (rate mode; it must be 1 for the history) is set for MOV. When ctx+984 restarts the first-frame path.
- A camera check: record the same static scene with the both-byte build, then run `qp.py` and the per-GOP rates. QP below 20 on P-frames after frame 1 would confirm the register reading.

## Files

- `tools/emu/cases.py`: the new cases `qp_setup`, `qp_rc` and `qp_size_model`, appended at the end.
- `tools/emu/specs/qp-floor-16.json`: the requested 0xA84A00-only spec.
- `tools/emu/specs/qp-floor-16-both.json`: both floor bytes.
- `tools/emu/README.md` was not updated.
