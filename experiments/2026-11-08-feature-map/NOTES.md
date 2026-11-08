# Feature map of E-PM2 v1.6 block 0 (2026-11-08)

**Goal:** map and understand every feature in the main firmware. Mapping only: no patches, nothing flashed.

## Method

- `tools/fwmap.py build` makes a function database in `build/map/` (git-ignored):
  - 66,094 functions. 54,567 start at `call` targets; 11,526 more are pointer targets that start with a `movm` prologue.
  - 305,768 call edges, 42,922 code→string references, and an index of data-table pointers.
- Query commands: `fn ADDR [--dis]`, `str REGEX`, `range LO HI`, `xref ADDR`, `tasks`.
- **Link-order property (verified):** the code of each source file is contiguous, and its strings are laid out in the same order. There are zero inversions across 1,149 file-name references. So a function's strings place it in the link order, and unlabeled functions between two functions of one module belong to that module.
- Runtime base 0x7E421020 (verified: see `../2026-11-08-disassembly/NOTES.md`).

## Fixed points

- **Task names:** block-0 offset 0x4D222. Records of u16 id + char[24], 147 names, sorted by name.
- **Task configuration:** block-0 offset 0x17D9C. Records of 28 bytes `{entry, pri, stack size, stack, cfg_id, attr, exinf}`, 139 tasks.
  - The name id is `cfg_id − 2` up to SPC_TIMER. The last rows are named from their strings; `fwmap.py tasks` applies this.
  - Checked against each entry's strings: e.g. FIRMUP_CLI → `[firmup]Mount Err:`, PLAY_SOUND → `play_regist_bgm in`.
- **Second object table:** block-0 offset 0x1C448. IDs 0x9005–0x900F and 0x1001–0x101E with explicit stacks at 0x604E…. Not decoded yet.
- **Default interrupt vector table:** block-0 offset 0x4CDD0; every entry points to 0x7E44ACB0.
- **OS wrappers:** `OlyTa*` (task), `OlyEv*` (event flag), `OlyQe*` (queue), `OlySm*` (semaphore). The OS is uITRON.
- **Settings getter:** `0x7E457C75(id, a0=0, d1=index)`, with 2,168 call sites. Example: the movie routine reads id 26225 (format) and id 33105/index 7.

## Layout by region (256 KiB buckets; tags = most frequent string prefixes)

See `sections/` for each subsystem. A summary is in `../../docs/firmware-map.md` once compiled.
