# Confidence tracking

**Goal:** high confidence in how each part of the firmware works, checked by adversarial review.

## What "high confidence" means here

A region of block 0 counts as understood when all of the following hold:
1. **Breadth (coverage test).** In a fresh random sample of its functions, blind reviewers who start from the map and then read the code judge
   - ≥ 80 % EXPLAINED or PARTLY,
   - ≥ 50 % EXPLAINED, and
   - **0** CONTRADICTED.

   This uses `scripts/coverage_sample.py` with a new seed each round, and the brief at `coverage/BRIEF.md` (a copy of the scratch brief).
2. **Correctness (claim audit).** A random sample of the region's "verified" claims has **0** wrong in substance (`scripts/audit_sample.py`).
3. **Roles.** Every task and major module in the region has a role stated with verified entry points, and its open questions are listed explicitly.
4. **Cross-checks.** Where other bodies or versions apply, the behaviour is compared (sections 09–11).

A region that fails a round gets a deep dive, then a **new** blind sample. The same sample is never reused: the deep-dive author has seen it, so it would no longer be a blind test.

## Rounds

| Round | Test | Sample | Result |
|---|---|---|---|
| A1 | Claim audit, sections 01–08 | 48 claims, seed 20261109 | 26 correct, 21 minor, **0 wrong**, 1 uncheckable (`audit/REPORT.md`); fixed in `audit/fixes.md` |
| A2 | Claim audit, section 12 | 12 claims, seed 20261110 | 6 correct, 5 minor, **1 wrong** (12-35: three corner-resolver helpers merged into one); all fixed |
| A3 | Claim audit, section 11 | 12 claims, seed 20261111 | 3 correct, 7 minor, **2 wrong**: (11-127) v1.5 stubbed the MTP property 0xD406 handler, the best Windows-10 candidate (checked by coordinator: v1.4 copies a host string to 0x602C1A98, v1.5 returns 0x2001 OK); (11-119) is_type gate inverted, and it is a mask test. Pending fix in the corrections pass |
| C1 | Coverage, whole block 0 | 80 functions, seed 1109 | **FAIL.** 10 explained (12.5 %), 51 partly, 17 unexplained, 1 contradicted, 1 not-code. Explained+partly 76 %. Gaps: string-less libraries, C++ framework patterns, GUI toolkit, mcon records, drivers; region-table errors. `coverage/round1-review1..4.md` |

## Region status

| Region (see firmware-map §1) | Coverage | Claims | Roles | Status |
|---|---|---|---|---|
| 0x7E42–0x7E52 platform | — | A1 ok | | pending C1 |
| 0x7E52–0x7E62 lens/firmup/take | — | A1 ok | | pending C1 |
| 0x7E62–0x7E73 camera core, movie, rec, art | — | A1 ok | | pending C1 |
| 0x7E8F–0x7E96 playback/audio/BT | — | A1 ok | | pending C1 |
| 0x7E96–0x7EBA app components | — | A1 ok | | pending C1 |
| 0x7ECA–0x7EE2 GUI | — | A1 ok | | pending C1 |
| 0x7EE2–0x7EEE libraries / C3D | — | not sampled | | pending C1 |
| 0x7F05–0x7F0B BASIC / ADJ / USB / SPC | — | A1 ok | | pending C1 |

## Round C1 findings driving round D1 (deep dives)

- **Tool:** function starts were missed for code reached only via `mov imm32` (callbacks, IRQ handlers, state handlers) and for vtable getters next to each other. `fwmap.py` now adds "imm" starts and frame-after-return starts. A test build gives 74,554 functions (+8,385), with no existing start lost.
- **Libraries without strings:** C runtime 0x7E4F8000–0x7E501C5B (incl. soft-float 0x7E5010EA–0x7E5019ED); Omron OKAO face library ~0x7E72CFA1–0x7E732000; a face-scoring library in overlay A 0x7F0645C1–0x7F069000 (called only from FACE_MAIN cmd 5; checked by coordinator); image/colour-curve library ~0x7E54D000–0x7E578000; AVPI AV middleware ~0x7EE8F000–0x7EEA0000 and strings/vtables at 0x7F021020–0x7F034000.
- **C++ layer:** 1,273 event vtables (not ~930; checked by coordinator), most outside the range section 06 gives; the Com_ framework 0x7EB855C7–; the OXF runtime runs on to ~0x7EBA9xxx (`getCurrentEvent` 0x7EBA6D64, 12,693 callers; checked); classes missing from the map (CapPls_PlayState, CapBlu_Bluetooth, Cmp_PictBridgeComponent, a USB-communication device class); no event-id dictionary.
- **GUI:** widget toolkit, GCPnl panels, object-type registry 0x7EFC5470, Ss* handler tables.
- **mcon:** 60-byte per-setting operation records at 0x7E814864; region ~0x7E6FC000–0x7E708000.
- **Drivers/state machines:** SIO, jog-dial hardware 0x9A600000, unit at 0x99900000, the FAT layer, IRQ handlers; TAKE release sequencer (state table 0x7E7908C0); strobe exposure calculation.
