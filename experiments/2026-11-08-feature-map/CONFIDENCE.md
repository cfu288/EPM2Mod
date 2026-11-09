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
| C1 | Coverage, whole block 0 | 80 functions, seed 1109 | *running* |

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
