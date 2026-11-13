# Round D1 deep-dive brief

**Target:** Olympus PEN E-PM2 v1.6, block 0 (MN103/AM33, uITRON 4.0-style), runtime = 0x7E421020 + offset.
**Goal:** UNDERSTANDING. A blind coverage test (random functions, judged against the map) showed that the map places code in roughly the right module but rarely explains individual functions. Your area was flagged as a gap. Your job is to make the functions in your area **explainable from the map**:
- name the components and patterns;
- give each function or function family a role;
- fix the region boundaries.

The next coverage round draws NEW random functions and checks your section against the code, so be precise and honest.

**Rules:**
- Never modify firmware.
- Write ONE file, the section path in your assignment. No other repo edits, no git commits, no `fwmap.py build`, no network, no questions to the user.
- Scratch: /tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/d1/<topic>/. Run Python with `-I`.
- Label every claim **verified** (read in code or bytes) or **inferred**.
- MN103 facts:
  - `btst/bset/bclr imm,Dn` take a MASK, not a bit number;
  - `udfu01 N,dX` and `udf00`/`udf01` behave as multiply (inferred);
  - args in d0, d1, then the stack; a0/a1 are pointers; the result is in d0/a0;
  - `call target,[regs],N` (the callee frame is set up by the caller's `call`); functions reached through pointers start with `movm`.

**Tools** (run from /path/to/EPM2Mod). USE THE IMPROVED DATABASE: add `--out $S/map-test` to every fwmap command (S=/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad). It has 74,554 functions, including callbacks, IRQ and state handlers that the old build/map merges.
- `python3 tools/fwmap.py --out $S/map-test fn ADDR [--dis] | str REGEX | range LO HI [-n K] | xref ADDR`
- `python3 tools/disasm.py ADDR --len N [--before N]`
- $S/map-test/functions.txt (grep only), calls.tsv, strrefs.tsv, ptrs.tsv
- block-0 bytes: build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin
- Other bodies, for cross-checks (strings often survive in another body or version): $S/map-<body>; see $S/hidden/BRIEF.md for the table. E-PM2 v1.1–v1.5: $S/map-101_<ver>.

**Read first:**
- docs/firmware-map.md (including the "Corrections … from coverage round C1" block);
- experiments/2026-11-08-feature-map/CONFIDENCE.md (round C1 findings);
- the coverage reviews experiments/2026-11-08-feature-map/coverage/round1-review*.md — the rows in your area show what was missing;
- the earlier sections for your area.

**Output section structure (under ~300 lines):**
1. **Area and boundaries:** verified start/end addresses of each component.
2. **Components:** for each one, its role, its entry points, its key data structures and its callers outside the area.
3. **Function catalogue or recurring patterns:**
   - for libraries, a table of functions with their identified roles (e.g. libc names, matched by behaviour);
   - for generated or framework code, a pattern description, written so that a reader can classify a new function of that pattern by its bytes (give byte or instruction signatures).
4. **Corrections** to the existing map or sections.
5. **Open questions.**

Reply with a 10-line summary.
