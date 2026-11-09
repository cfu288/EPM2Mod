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
| A4 | Claim audit, D1 sections 13a–13f | 46 claims, seed 20261112 | 26 correct, 16 minor, **5 wrong**: 13a-166 (IRQ numbers called objects), 13a-189 (defect-correction table layout), 13a-196 (job copy, not execute), 13d-121 (drawing engine calls soft-double math), and 13a §5 #4 "no hardware registers" (rejected by the corrections pass; checked by coordinator: writes 0x99400008 / 0x99400000). Fix, then resample |
| A5 | Claim audit, D1 sections after the A4 fixes | 34 claims, seed 20261113 | 17 correct, 17 minor, **0 wrong**. Most minors are range ends or counts; 5 of 6 re-sampled A4-corrected lines still had a detail wrong (`audit/check-13b-1..3.md`) |
| F1 | Corrections pass after D1 | 52 items | 11 section-11 fixes + 41 D1 fixes applied, 1 rejected (13a no-registers claim); log `audit/fixes-D1.md` |
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
- **Libraries without strings:** C runtime 0x7E4F8000–0x7E501C5B (incl. soft-float 0x7E5010EA–0x7E5019ED); Omron OKAO face library ~0x7E72CFA1–0x7E732000; a library in overlay A 0x7F0645C1–0x7F0691C5 called only from FACE_MAIN cmd 5 (checked by coordinator). **D1 (13b): it is red-eye correction, not face scoring**; image/colour-curve library ~0x7E54D000–0x7E578000; AVPI AV middleware ~0x7EE8F000–0x7EEA0000 and strings/vtables at 0x7F021020–0x7F034000.
- **C++ layer:** 1,273 event vtables (not ~930; checked by coordinator), most outside the range section 06 gives; the Com_ framework 0x7EB855C7–; the OXF runtime holds `getCurrentEvent` 0x7EBA6D64 (12,693 callers; checked). **D1 (13b/13c): OXF ends ~0x7EBA7BB5; 0x7EBA7BC1– is OKAO Smart Skin**; classes missing from the map (CapPls_PlayState, CapBlu_Bluetooth, Cmp_PictBridgeComponent, a USB-communication device class); no event-id dictionary.
- **GUI:** widget toolkit, GCPnl panels, object-type registry (D1 13d: really 0x7EFC5408; 0x7EFC5470 is entry 13), Ss* handler tables.
- **mcon:** 60-byte per-setting operation records at 0x7E814864; region ~0x7E6FC000–0x7E708000.
- **Drivers/state machines:** SIO, jog-dial hardware 0x9A600000, unit at 0x99900000, the FAT layer, IRQ handlers; TAKE release sequencer (state table 0x7E7908C0); strobe exposure calculation.
