# Coverage review brief (adversarial)

You are testing how well a firmware map explains the real code. Assume the map is wrong or incomplete until the bytes show otherwise. The map has already been shown to contain confident errors.

**Target:** Olympus PEN E-PM2 v1.6, block 0 (MN103/AM33, uITRON), runtime address = 0x7E421020 + offset.

**The map** (read what you need):
- /path/to/epm2-tools/docs/firmware-map.md — the regions table and the feature inventory;
- experiments/2026-11-08-feature-map/modules.tsv — source files in link order with code ranges;
- experiments/2026-11-08-feature-map/tasks.tsv;
- experiments/2026-11-08-feature-map/sections/*.md — detail by subsystem.

**Tools** (run from /path/to/epm2-tools):
- `python3 tools/fwmap.py fn ADDR [--dis] | str REGEX | range LO HI | xref ADDR`
- `python3 tools/disasm.py ADDR --len N [--before N]`
- build/map/ (functions.txt is 168 MB: grep only)

MN103 notes:
- args in d0, d1, then the stack; a0/a1 are pointers; the result is in d0/a0;
- `btst imm,Dn` tests a MASK;
- `udfu01 N,dX` behaves as multiply (inferred).

**For each function in your batch, do two steps in this order:**
1. **Predict from the map only.** Using the address, the regions table, modules.tsv and the sections, write what the map says this function should be: its subsystem, its module/source file, and its role if the map is that specific.
2. **Read the code.** Look at the disassembly, its strings, callers and callees, and the strings in neighbouring functions. Judge the map:
   - **EXPLAINED**: the map names the right module and gives a role that fits the code.
   - **PARTLY**: the subsystem or module is right, but the map says nothing about what this function does, or it is only vaguely right.
   - **UNEXPLAINED**: the map has nothing that fits, or the region is labelled only generically ("data", "libraries", "GUI").
   - **CONTRADICTED**: the map says something that the code shows is false.
   - **NOT-CODE**: the "function" is really data or a mis-split. This is a tool error; say why.

   Also write, in one or two lines, **what the function actually does** (verified from the code, or labelled inferred).

**Output.** Write a table: `id | addr | map prediction | verdict | what it actually does | evidence`. Then a short list of every CONTRADICTED item with proof, and of the areas where the map is weakest.

**Rules:**
- Read-only, except your one output file.
- No git commits, no `fwmap.py build`, no network, no questions to the user.
- Put scratch files in /tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/coverage/<batch>/ and run Python with `-I`.
