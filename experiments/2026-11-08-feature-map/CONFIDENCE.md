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
| A6 | Claim audit, D2 sections 14a–14e | 35 claims, seed 20261114 | 21 correct, 12 minor, **2 wrong, both in 14c**: 14c-134 (teardown 0x7EA17103 belongs to the class after CapMed_MediaInfo), 14c-145 (the Live Bulb TAKE step: message 19 → 0x7E5A2A27 → request 268, not the event table). 14a, 14b, 14d, 14e: 0 wrong (`audit/check-14-1..3.md`). Fix, then resample 14c |
| A7 | Claim audit, 14c resample after A6 fixes | 12 claims, seed 20261115 | 6 correct, 6 minor, **0 wrong**. Minors: range starts (0x7E966000, Cap* at 0x7E9EB318), event 11805 is a blocking wait (not a trace record), mask-vs-bit wording, 13 of 22 records non-null (`audit/check-14c-A7.md`). Fixes pending (next fix pass) |
| A8 | Claim audit, D3 sections 15a–15d | 36 claims, seed 20261116 (sampler now inherits "(V)" headings) | 26 correct, 8 minor, **2 wrong**: 15b-235 (serial descriptor: tx frame is inline at +14, +4 is an owner pointer, +0 a completion callback), 15c-166 (Com_ActiveTransitionManagerBufferd does accept 13361 via states 7/8). 15a, 15d: 0 wrong (`audit/check-15-1..4.md`). Fix, then resample 15b/15c |
| A9 | Claim audit, 15b + 15c resample after A8 fixes | 20 claims, seed 20261117 | 14 correct, 3 minor, **3 wrong**: 15b-169 (3 of 8 "ems2 callbacks" don't fit the pattern), 15b-244 ("no user" for ADC channels 22/39/41 is false), 15c-140 (PictBridge composite is state 33, not 34; ≥ 8 request→state rows missing). The failures are pattern-for-a-family, absence and completeness claims in the dense D3 indexes (`audit/check-A9.md`) |
| A10 | Claim audit: first audit of 09/10, resample of 11/12/15b/15c | 62 claims, seed 20261118 | 34 correct, 23 minor, **5 wrong**: 09a-78 (info 111 *is* written with constant ids, via mcon), 09b-161 (40 `cmp 108` sites, not 2), 10d-109 (the edit-mode jump table does not map every mode), 10e-87 (status reads are ADJ op 0x9005, not 0x902A), 15b-60 (two of the "MEC submit or timer" handlers are stubs). **11, 12, 15c: 0 wrong.** New finding (checked by coordinator): after the getShippingInfo(4) gate, 0x7EDFD69B posts PostEventToCA(11, 11), the VER_MENU → VerCheck trigger that 10f/13d called unknown (`audit/check-A10-1..4.md`) |
| F1 | Corrections pass after D1 | 52 items | 11 section-11 fixes + 41 D1 fixes applied, 1 rejected (13a no-registers claim); log `audit/fixes-D1.md` |
| C5 | Coverage, whole block 0, after the L1 boundary cleanup | 80 functions never used in C1–C4, seed 5109 | **Breadth and contradiction criteria MET; explained not met.** 26 explained (32.5 %), 54 partly, 0 unexplained, **0 contradicted**, 0 not-code. Explained+partly **100 %**. Side errors found in neighbouring map text (not counted): the CA misc sub-app table is `{event, flag, next_state, handler}` from 0x7EED93EC, so VERCHK = 0x06000009 (10f/13d gave wrong event ids); CA code 11 = GUI_END_MENU; 13f SIO hook tables; 04 strh/strf field lists; event 3344 has a second use; the BTTIM row. `coverage/round5-review1..4.md` |
| C4 | Coverage, whole block 0, after D3 | 80 new functions, seed 4109 (one C1–C3 overlap replaced) | **FAIL.** 24 explained (30 %), 50 partly, 1 unexplained, **3 contradicted**, 2 not-code (both already in 14d-false-functions). Explained+partly 92.5 %. Contradictions: the "Exif writer" at 0x7E707880 is the IMGDMA add-job module (checked: caller prints `IMGDMA_ADD_YC/BAYER/RGB`, table 0x7E84EE68); a 15c class range swallows a helper singleton (0x7E96C7F9); the GuiTouch end is one function late (0x7EDE15EE is the USB-connect screen getInstance). `coverage/round4-review1..4.md` |
| L1 | Boundary lint, all sections and the map | every code range ≥ 64 B | 1,302 ranges; **242 start or end inside a function** (`scripts/boundary_lint.py`, `audit/boundary-lint-1.tsv`). Many are round-number approximations written as exact. This explains most coverage contradictions since C2 |
| C3 | Coverage, whole block 0, after D2 | 80 new functions, seed 3109 | **FAIL.** 20 explained (25 %), 54 partly, 1 unexplained, **4 contradicted**, 1 not-code. Explained+partly 92.5 %. Contradictions are all region labels: 14b's cam_lens.c start (imgdev runs to ~0x7E640200); the 03/14b "SDET algorithm library" 0x7E666EB9–0x7E675000 is mainly the mdet motion-detection library used by TAKE AF (checked: F015's outside callers are 0x7E59BBD0/0x7E59BCD9); 13d's "self-adjust UI" range is mostly GuiTouch. Weakest: function-level roles (GUI pages, HCI, play-component notifications, camera-core command tables). `coverage/round3-review1..4.md` |
| C2 | Coverage, whole block 0, after D1 | 80 new functions, seed 2109 | **FAIL (better).** 23 explained (29 %), 49 partly, 4 unexplained, **2 contradicted**, 2 not-code. Explained+partly 90 % (criterion met); explained < 50 % and contradicted > 0 (not met). Contradictions: zlib/C3D-API ranges overlap in 08 (zlib ends at zmemcpy 0x7EE619AC); 13c Dev*→Ctg boundary is ~0x7EB93423, not ~0x7EB93A80. Also found: the GL library ends ~0x7EE294B4, not 0x7EE21020 (checked: 194-entry name table 0x7F023C74); a string-scanner bug ('~' from a 0x7E pointer byte, fixed in fwmap, +900 string refs); a touch-panel firmware image at 0x7E7F0F78. `coverage/round2-review1..4.md` |
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

## Coverage by region, rounds C4 + C5 (160 functions, after D3 and the L1 boundary cleanup)

| Region | n | Explained | Partly | Unexpl. | Contra. | Not-code | E % | E+P % |
|---|---|---|---|---|---|---|---|---|
| 0x7E42–0x7E52 platform, drivers, libs | 5 | 0 | 5 | 0 | 0 | 0 | 0 | 100 |
| 0x7E52–0x7E62 lens, firmup, IMG, WB, TAKE | 17 | 5 | 12 | 0 | 0 | 0 | 29 | 100 |
| 0x7E62–0x7E73 camera core, movie, rec, face | 25 | 10 | 14 | 0 | 1 | 0 | 40 | 96 |
| 0x7E73–0x7E8F rodata, .data | 2 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| 0x7E8F–0x7E96 playback, audio, BT | 11 | 3 | 8 | 0 | 0 | 0 | 27 | 100 |
| 0x7E96–0x7EBA C++ app layer | 54 | 24 | 29 | 0 | 1 | 0 | 44 | 98 |
| 0x7ECC–0x7EE0 GUI | 30 | 4 | 24 | 1 | 1 | 0 | 13 | 93 |
| 0x7EE0–0x7EE8 3D / GL / C3D | 5 | 1 | 4 | 0 | 0 | 0 | 20 | 100 |
| 0x7EE8–0x7EEC AVPI | 4 | 1 | 3 | 0 | 0 | 0 | 25 | 100 |
| 0x7F05–0x7F0F overlays A/B | 7 | 2 | 5 | 0 | 0 | 0 | 28 | 100 |

**Reading (C4 + C5):**
- **Placement:** explained+partly is ≥ 93 % in every code region. C5 alone is 100 %, with 0 contradicted.
- **Explained share (function-level role):** highest in the C++ app layer (44 %) and the camera core (40 %), where the shape catalogues and indexes apply; lowest in the GUI (13 %) and the platform drivers (0 of 5).
- **The two C4/C5 contradictions** (camera core, app layer) were both range labels and are fixed. The GUI contradiction (C4, GuiTouch end) is fixed too.
- **Samples are small:** per-region n is 2–54.

## Coverage by region, rounds C2 + C3 (159 functions, after D1)

| Region | n | Explained | Partly | Unexpl. | Contra. | Not-code | E % | E+P % |
|---|---|---|---|---|---|---|---|---|
| 0x7E42–0x7E52 platform, drivers, libs | 7 | 1 | 5 | 1 | 0 | 0 | 14 | 86 |
| 0x7E52–0x7E62 lens, firmup, IMG, WB, TAKE | 15 | 5 | 9 | 1 | 0 | 0 | 33 | 93 |
| 0x7E62–0x7E73 camera core, movie, rec, art, face | 24 | 8 | 11 | 2 | 3 | 0 | 33 | 79 |
| 0x7E73–0x7E8F rodata, .data | 3 | 1 | 0 | 0 | 0 | 2 | — | — |
| 0x7E8F–0x7E96 playback, audio, BT | 6 | 3 | 3 | 0 | 0 | 0 | 50 | 100 |
| 0x7E96–0x7EBA C++ app layer | 48 | 16 | 30 | 1 | 1 | 0 | 33 | 96 |
| 0x7ECC–0x7EE0 GUI | 29 | 5 | 23 | 0 | 1 | 0 | 17 | 97 |
| 0x7EE0–0x7EE8 3D / GL / C3D | 12 | 1 | 10 | 0 | 1 | 0 | 8 | 92 |
| 0x7EE8–0x7EEC AVPI | 7 | 1 | 6 | 0 | 0 | 0 | 14 | 100 |
| 0x7F05–0x7F0F overlays A/B | 8 | 2 | 6 | 0 | 0 | 0 | 25 | 100 |

**Reading.**
- **Placement:** breadth (E+P ≥ 80 %) holds in every region except the camera core (79 %, contradictions).
- **Explained:** "explained" (a function-level role) stays near 25–33 % after two deep-dive rounds. The map places code correctly but does not give each function's role.
- **Contradictions:** they are now all region-label errors, not wrong behaviour claims.
- **Sample size:** per-region samples are small (7–48), so per-region rates are rough.

## Round C1 findings driving round D1 (deep dives)

- **Tool:** function starts were missed for code reached only via `mov imm32` (callbacks, IRQ handlers, state handlers) and for vtable getters next to each other. `fwmap.py` now adds "imm" starts and frame-after-return starts. A test build gives 74,554 functions (+8,385), with no existing start lost.
- **Libraries without strings:** C runtime 0x7E4F8000–0x7E501C5B (incl. soft-float 0x7E5010EA–0x7E5019ED); Omron OKAO face library ~0x7E72CFA1–0x7E732000; a library in overlay A 0x7F0645C1–0x7F0691C5 called only from FACE_MAIN cmd 5 (checked by coordinator). **D1 (13b): it is red-eye correction, not face scoring**; image/colour-curve library ~0x7E54D000–0x7E578000; AVPI AV middleware ~0x7EE8F000–0x7EEA0000 and strings/vtables at 0x7F021020–0x7F034000.
- **C++ layer:** 1,273 event vtables (not ~930; checked by coordinator), most outside the range section 06 gives; the Com_ framework 0x7EB855C7–; the OXF runtime holds `getCurrentEvent` 0x7EBA6D64 (12,693 callers; checked). **D1 (13b/13c): OXF ends ~0x7EBA7BB5; 0x7EBA7BC1– is OKAO Smart Skin**; classes missing from the map (CapPls_PlayState, CapBlu_Bluetooth, Cmp_PictBridgeComponent, a USB-communication device class); no event-id dictionary.
- **GUI:** widget toolkit, GCPnl panels, object-type registry (D1 13d: really 0x7EFC5408; 0x7EFC5470 is entry 13), Ss* handler tables.
- **mcon:** 60-byte per-setting operation records at 0x7E814864; region ~0x7E6FC000–0x7E708000.
- **Drivers/state machines:** SIO, jog-dial hardware 0x9A600000, unit at 0x99900000, the FAT layer, IRQ handlers; TAKE release sequencer (state table 0x7E7908C0); strobe exposure calculation.
