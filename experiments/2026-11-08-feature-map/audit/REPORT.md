# Audit of "verified" claims in sections 01–08 (2026-11-09)

**Method.**
- Sampling: `scripts/audit_sample.py` (seed 20261109) split each of sections 01–08 into candidate claims: table rows or bullets labelled verified that cite an address. It drew 6 per section, 48 in all (`sample.json`, `claims-1..4.md`).
- Checking: four independent checkers verified every assertion in each claim against the bytes (`check-1..4.md`). They saw only the claim text and the section it came from.
- Calibration: the coordinator checked 3 sampled claims beforehand (`calibration.md`). All 3 coordinator verdicts match the checkers' verdicts (01-47 correct, 04-105 correct, 08-59 minor).

## Results

| Section | Pool | Correct | Minor | Wrong | Uncheckable |
|---|---|---|---|---|---|
| 01 platform | 30 | 1 | 5 | 0 | 0 |
| 02 lens/firmup/take | 23 | 5 | 1 | 0 | 0 |
| 03 camera core/art | 30 | 3 | 3 | 0 | 0 |
| 04 movie | 51 | 2 | 4 | 0 | 0 |
| 05 playback/audio/BT | 20 | 2 | 4 | 0 | 0 |
| 06 app components | 12 | 5 | 1 | 0 | 0 |
| 07 GUI/settings | 15 | 4 | 1 | 0 | 1 |
| 08 connectivity/blocks | 20 | 4 | 2 | 0 | 0 |
| **Total** | **201** | **26 (54 %)** | **21 (44 %)** | **0** | **1** |

**What this says about the rest of 01–08.**
- **No sampled claim was wrong in substance.** With 48 samples and 0 failures, the share of substantively wrong "verified" claims is probably below about 6 % (95 % upper bound, rule of three: 3/48).
- **About half the claims have a wrong detail.** The usual kinds:
  - an address that is the middle of a function, or the address of a reference instead of the target (e.g. the USB test packet 9 bytes off; state pointers 5 bytes off);
  - module ranges that cut functions in half;
  - counts off by one (28 vs 27 chunks);
  - wrong command names (`usr fast log`, `get_src`/`set_src`);
  - interpretations marked "verified" that should be inferred.
- **Rule of thumb:** trust the *what* of a "verified" claim. Re-check any exact address, count or range before relying on it.

**A systematic error found by the audit.** On MN103, `btst imm,Dn` ANDs with a **mask**. Claims that read "bit N" from a `btst N` instruction are wrong (06-92: `btst 14` tests bits 1–3). Every such claim in sections 01–10 is re-checked in the fix pass.

**Other errors found outside the sample:**
- Section 01 gives the CPU1 task-record start as 0x1C488; it is 0x1C490 (the tool already uses 0x1C490).
- Section 07 §5 cites 0x7EDA6D93 for the Warning strings; they are in 0x7EDB0847 / 0x7EDC25D4.

## Fixes
The minor errors are corrected in place in sections 01–08; each fix carries an "(audit 2026-11-09)" note. See the fix pass in `fixes.md`.
