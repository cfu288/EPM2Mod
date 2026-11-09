# 16e. GL, 3D engine, image decoders, libpng/zlib, C3D and AVPI 0x7EE02095–0x7EECE318: generated function index

Round D5, cycle 1 (2026-11-09); round D6, cycle 2 (2026-11-09): precision pass (rule precision measured for every rule over 50 rows; 10 rules fixed or rewritten, 2 added; §4.1); **round D7, cycle 3 (2026-11-09): from context to role** (3 new rules, 1 rule fixed during sampling, 1 position family withdrawn, 115 new hand roles read in the code; §4.1, §4.2). E-PM2 v1.6, block 0, runtime = 0x7E421020 + offset. This range had no per-function index. Before this round, 5 of the 20 round-6 batch-4 functions (F071–F075) fell in it and had no row.

- **Labels:** **V** = read in code or bytes. **I** = inferred from names, order, position or outside knowledge. libpng and zlib names come from matching against the public sources. They are **I** unless a string or constant proves them. GL enum names are outside knowledge (I).
- **Index:** `16e-graphics-avpi-index.tsv` has **one row for each of the 6,459 database functions** in the range. The range has 6,464 functions in `build/map/functions.tsv`; the 5 with `data_page` = 1 or `suspect` = 1 are left out. The columns are:
  - `addr`, `size`;
  - `component`: the component, then `>` and the family (§1);
  - `role`;
  - `basis`: the rule or table that gave the role;
  - `V/I`;
  - `level`: S = specific role, P = own facts only (codes, callees, strings) or a named call-graph context, C = context only.
- **Scratch:** D7 builder `$S/d7/gfx/` (`idx.py`; new `leafsum.py`; `curated.py` now also loads the hand reads `hand/*.tsv`; samples in `samples/`, the final check in `samples/final40.txt`). D6 builder `$S/d6/gfx/` (`idx.py`, new `owner.py`; samples in `samples/`, verdicts in `verdicts/`). D5 builder `$S/d5/gfx/` (S = `/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad`). Run `python3 -I idx.py`; it writes `16e.tsv` and `rows.pkl`. The modules are:
  - `db.py`: the loader, the code-immediate index and the GL entry table;
  - `jt.py`: linear jump tables;
  - `hsw.py`: GL hash switches;
  - `c3d.py`: the C3D registry, ctor and vtinit chains, and vtable fills;
  - `avpi.py`: AVPI vtables, plug-in groups and the registry;
  - `curated.py`: hand roles, with the section or read cited;
  - `glenum.py`: GL enum names;
  - `owner.py` (D6): the plug-in that creates each AVPI class, from its ctor callers (§1).

  `rd.py` and `q.py` are readers (`q.py ADDR N`). `sample1–7.txt` and `verdicts.txt` hold the D5 accuracy samples; `samples/*.txt` and `verdicts/*.txt` hold the D6 ones.

## 1. Area and boundaries

The component edges are those of 14a §1 and 13b §1. This round did not move them. The sub-family edges below are the ones the `component` column uses.

| Range | Component › families | Rows | S share |
|---|---|---|---|
| 0x7EE02095–0x7EE294B4 | **DMP GL**: library init + DVOJ (to 0x7EE0357F; it includes the GPU register helpers 0x7EE02D0C–0x7EE02DD5), EGL 0x7EE08680–0x7EE09129, back end 0x7EE10B33–0x7EE19609, texture internals 0x7EE2245D–0x7EE24292, and GL API + internals elsewhere | 672 | 67 % (D6 64 %) |
| 0x7EE294B5–0x7EE5B5BB | **3D engine core**: MC* loaders, GL render back end 0x7EE2FF5E–0x7EE32698, stream, resource loaders, MB/MT loaders, type modules 0x7EE36D26–0x7EE54C92, maths helpers 0x7EE54C93– (D6; was 0x7EE5AC2B, see §5 item 7) | 949 | 30 % (D6 18 %) |
| 0x7EE5B5BC–0x7EE5D00C | **Image decoders**: BMP, GIF89a (pixel converters 0x7EE5C4D6–), PNG glue 0x7EE5C8CD– | 31 | 74 % (D6 71 %) |
| 0x7EE5D00D–0x7EE5F5F2 | **libpng 1.2.37** (read side) | 80 | 100 % |
| 0x7EE5F5F3–0x7EE619C6 | **zlib 1.2.3** (crc32, inflate) | 14 | 100 % |
| 0x7EE619C7–0x7EE8F4F3 | **C3D framework**: API to 0x7EE61E54, context/registry/stream to 0x7EE62C0F, class code, helpers 0x7EE8F081– | 2,584 | 68 % (D6 62 %) |
| 0x7EE8F4F4–0x7EECE318 | **AVPI**: OSAL, framework classes 0x7EE90235–, plug-ins 0x7EE9C332–, SCA 0x7EEC1B72–, C++ support 0x7EEC5F32–, kernel message glue 0x7EEC62B9–, codec hardware driver 0x7EEC673F–, codec task + DFS glue 0x7EECC670– | 2,129 | 65 % (D6 62 %) |

**Families by position (I):**
- **C3D class blocks.** A C3D class-code row gets `in the code block of class id N` when the nearest registered ctor, fini, vtinit, own level or own-slot function on **both** sides belongs to class N. The two anchors must also be less than 0x1800 bytes apart.
- **Engine type blocks.** An engine type-module row gets `engine type T` by the same test. The anchors are the type-table functions and the `alloc(T)` creators; the limit is 0x2000 bytes.
- **Plug-in code ranges.** An AVPI plug-in row gets `<plug-in> code` when it lies between the lowest and highest own (unshared) slot target of that plug-in's 65-slot vtable. The 11 ranges do not overlap.

**Plug-in owner of an AVPI class (V, D6; replaces the D5 string-position group).** D5 gave each non-plug-in vtable the plug-in whose `… Plug-in` name string came before it in rodata. That was false for 383 rows; for example the H.264 engine vtables 0x7F0302D4 and 0x7F0307E8 were labelled "AFile Sink" (coverage r7 F076). D6 walks up the callers of the class's ctors (≤ 10 levels). A walk stops at a plug-in's code (a slot of its main vtable, or its registry factory). When it reaches a slot of another class, it continues from that class's ctors. The row says `created only from <plug-in> code: ctor callers` only when every path ends at plug-in code and at most 3 plug-ins are reached. Example: 0x7F0307E8 ← ctor 0x7EEA4D6C ← 0x7EEA3028 ← 0x7EEA7C7D (Video Encode slot 9). The plug-in main classes are named from the `… Plug-in` string that a slot of the same vtable loads (V). File Source has a 43-slot main vtable 0x7F03123C (factory 0x7EEB6EE2 → ctor 0x7EEB6F1E).

## 2. Rules (in priority order)

Each row has a primary fact, up to two more own facts, and then a call-graph context when the role is weak. The `basis` column names every rule used.

| # | Rule | Source / byte signature | S rows |
|---|---|---|---|
| 1 | **curated** | D7: 472 rows; 115 new hand roles, each read in the code (coverage r8 batch 4 F067–F079, the AVPI plug-in base methods and slot-10/48 targets, and one-line summaries of the most-called context-only functions of the engine, GL, C3D and AVPI framework; files `hand/*.tsv`). D6: 358 roles (11 added, 7 corrected; §4) (rows in the DB) copied from 14a, 13b, 13f and the coverage reviews (rounds 1–6), plus D5 reads of the most-called unnamed functions. The libpng/zlib catalogue is in §3 | 347 |
| 2 | **GL table** | `14a-gl-entry-points.tsv`: an entry row is "table entry (prologue only; the body is the next DB function)" or "table entry; the body lies inside this function"; a body row is "body (direct-call target)" | 327 |
| 3 | **switch case blocks** | (a) **GL hash switches** (`hsw.py`): 27 tables of rows `{u32 key, code}`. D6: the row lists the case **value** (table key + bias) and says so when the bias is not 0. The dispatcher does `(x − bias) & mask`, probes linearly, then `mov (4,a0),a0; jmp (a0)`. The key is pname − bias (0xB0F for the enable caps, 0xAFF for glGet*). Fwmap split the case labels into "functions" (§4.2 item 4). (b) Linear jump tables (`mov TAB,aN; mov (dX,aN),aN; jmp (aN)`); only 2 of their targets are DB starts | 78 + 1 |
| 4 | **C3D registry and vtinit fills** | `regs.json` (D2: 55 registrations of 0x7EE642F3) gives the class ctor, fini and vtinit. The ctor and vtinit chains give the level ctors and level fills: a level used by one class is "own", otherwise "base level shared by ids …". Each fill (`mov IMM,d0; mov d0,(off,a0)` …, `mov 1,d0; retf`) gives "vtable slot +off of class N / base level". Slots +0/+4/+8/+12 are size/write/read/copy (14a). An override whose first call is a root method gets the override-chain note | 710 |
| 5 | **AVPI vtables** | A vtable is a code-loaded rodata address in 0x7F02F684–0x7F034000 whose words are AVPI code. It runs to the next loaded address and excludes jump tables (§5 item 2). Slot k gives "vtable slot k of class vt X"; "shared by n vtables" counts only words equal to the function start (D6). 65-slot vtables are the 11 plug-in main classes (`plug-in interface slot k`). **D7 slot dictionary (I):** slot 10 = accept-format check (d0 = format record, a1 = pin; 1 = accept, 0 = reject; read in Video Decode, Audio Encode, Audio Decode, Video Sink), slot 48 = handler of a notification from the lower driver (code or port in d0; read in Audio Source, Audio Encode, Audio Decode). The other slot rows get the meaning only where their target was read (base methods of slots 3, 15, 16, 28, 38: §5 item 13). Slot 1 `mov K,d0; retf` gives GetTypeId. A slot word inside a DB function gives "contains the entry of slot k". **D6 vptr-store rule:** a loader is tracked symbolically from the entry a0. A store of the vtable at +0 of a0 gives "ctor level: stores the vptr at +0 of a0", or "destructor body" when it ends with `mov 0x7EE8FEF7,a0`. A call to a ctor (or a function that returns its a0) keeps a0 = this, because AVPI ctors return this. Other stores are own facts (P): "into a member sub-object at +K / a stack temporary / the static object at RAM Z / an object that is not its a0". The plug-in owner is from §1. The 12 registry factories come from .data 0x7E8EFA18 | 1,043 + 12 |
| 6 | **engine tables** | Type table 0x7F02AA14 (28 × {size, dtor, +8, +12, +16, slot +20, +24}); format-loader table 0x7F027C4C; MCM chunk jump table 0x7F027BFC; pixel-converter table 0x7F02B1F8; .data function tables 0x7E8EF20C–0x7E8EF8BC (P only) | 68 |
| 7 | **pointer entry** | ≤ 6 bytes of `movm`/`add` followed by a DB start. The row takes the next function's name unless its own table role is already set | 4 |
| 8 | **shape** (bytes) | `retf` alone = empty; `mov K,d0; retf` = constant (a function or rodata address is named); getter or setter (see below; D6: the width u8/u16 is given, and a null-checked getter must be `cmp 0,a0; beq; load; retf` with 0 on the NULL path); `mov (abs),d0; retf` = global getter. **Forwarder (D6, strict):** exactly one indirect call or jmp and no other call (except the C3D class-block getter 0x7EE75DA7); conditional branches only after `cmp 0,X` and only to the return; nothing writes d0/a0 after the call. The target is evaluated from the entry registers: "vtable slot +N of the object in a0 / of the member at +M" (AVPI, C++), "the function pointer at +N of …" (C code), or "C3D virtual-call stub: slot +N of the class block (this+8)". **C3D stream (D6):** a1 is followed through copies and sp spills; the row lists the slots +0/+4/+8/+12 of its vtable that are called and how many of the indirect calls they are (the D5 types "vt+8 = u32, vt+12 = bytes" are dropped). AVPI destructor = `mov 0x7EE8FEF7,a0; ret`; access to the plug-in registry 0x602BF558. A wrapper has ≤ 8 instructions in the whole listing, one call and no early return (D6), and takes its callee's name | 994 |
| 9 | **own strings** | Strings loaded. 4-char MP4 box names in MP4 Mux/Demux become "MP4 Mux (writer)/Demux (parser) code for box `X`" (the side is by position, I) | 40 |
| 10 | **error codes** | GL: `mov 0x50N,d0; call 0x7EE097DA` gives `raises GL_INVALID_*`. C3D: `mov 1,d0; mov N,d1; call 0x7EE62AD7` gives `C3D error N`. AVPI: the 0x9A/0xAA/0xAB/0xCA/0xCB/0x8000000x constants (P) | — |
| 11 | **service calls** | Constant arguments (tracked back to the previous call or branch; the last write to the register decides): engine alloc(type), C3D create(class id), AVPI malloc(n), new(n); the GL entries called; MMIO (codec 0x9940/0x9950, GPU 0x9AB0, 0x9810, 0x98B0); the soft-float and libc callees (13a names) as "float computation: n ops (fmul×…)" (P) | — |
| 12 | **code pointer** | A function with no callers whose address is loaded by code: "code pointer loaded by X (stored at +off)" (P) | — |
| 13 | **call graph** | One caller gives `helper of X (name)` plus the nearest named ancestor (BFS, ≤ 4 levels). Several callers give `shared helper, n callers` with named examples. The named callees are listed too. D6: a quoted name whose row is I reads `(I: name)` | — |
| L | **straight-line leaf** (D7, `leafsum.py`) | A function with no call, no branch and no loop is executed symbolically over the entry registers d0, d1, a0, a1 (and the stack arguments `(N,sp)` when the frame is empty). The row lists the final memory writes and the registers at return: `writes [a0+8] = d1; u16[a0+12] = 0; leaves d0 = [a0+4]`. `[X+n]` = the word at X+n read at that point; `u8[]`/`u16[]` = byte/half-word; `leaves` = the register value at the return (the return value when the function has one). More than 6 writes to one base are summarised: "writes 16 fields of a0 between +0 and +60 (values: …)". Only rows without another S fact | 116 |
| Q | **C3D override-chain step** (D7) | A function called as step k of a bool chain (every call followed by `extbu d0; cmp 1,d0`; the first call is a root slot method +4/+8/+12/+16, 0x7EE75DE0/0x7EE75DF2/0x7EE75DAD/0x7EE75C9A) gets "per-level <write/read/copy> step of the C3D slot +N override chain (step k of n) in <chains>". The last step of every chain it is in gets "own-level <op> body". The chain stops unless it returns 1. Example: F073 0x7EE79186 is the last step of the copy chain 0x7EE78B05 | 147 |
| B | **body of a thin wrapper** (D7) | When every caller (1–4) is a ≤ 8-instruction wrapper with one call, no branch before the call and a0 passed unchanged, and each wrapper has a table role (registry, slot, GL table, curated), the callee is "body of <wrapper role>"; the constant arguments the wrapper sets and any store of the result are listed. Example: F074 0x7EE7B6E8 = body of the class-2 fini 0x7EE7BB68 | 57 |
| M | **merged entries** (D6) | A pc inside a DB function that a vtable word or a code immediate points to, and that no branch of the function reaches, is a separate entry that fwmap kept inside. Own facts (constants, calls, strings) are read only before the first one. The row adds "the DB function also holds a separate entry X = vtable slot k of vt V (`mov K,d0; retf`)". 165 rows. Example: F077 0x7EEC4FAC (slot 34) holds 0x7EEC4FCD (slot 35, `mov 0x80000009,d0; retf`) | — |

**Getter/setter rule (V, after the D5 fixes):**
- The function is at most 48 bytes. It has no loop and no call other than the C3D error setter.
- Every memory access goes through `a0` or an alias made by `mov a0,aX`. An alias is dropped when the register is overwritten.
- **Getter:** one field is loaded into d0/a0 and returned at once (only `ext*`, `bra` or the return may follow).
- **Setter:** the field takes a register value. The row reads "field init (constants)" when the stored value is a constant set in the same straight-line block.
- **Extras:** "NULL-checked" (`cmp 0,a0`), the range bounds (`cmp K,dN`, but not the error-state compare with 0x80000000) and the C3D error codes.

## 3. Tables and catalogues used

- **GL hash switches** (V tables; enum names I):
  - Enable/disable worker 0x7EE09171: table 0x7F02443C, cap = key + 0xB0F. Example: key 0x758E is 0x809D, GL_MULTISAMPLE; its case 0x7EE0940E stores the flag at ctx+14976.
  - `glIsEnabled`: 0x7F02463C.
  - `glGetBooleanv`/`Fixedv`/`Floatv`/`Integerv`: 0x7F024BCC/0x7F0253CC/0x7F025BCC/0x7F0263CC. Each has 256 rows; pname = key + 0xAFF.
  - `glGetTexEnvxv`/`fv`/`iv`: 0x7F027104/0x7F027204/0x7F027304.
  - Also `glRenderbufferStorageOES` (0x7F02483C), `glGetFramebufferAttachmentParameterivOES` (0x7F02490C), `glBlendFuncSeparateOES` (4 tables 0x7F02498C–0x7F024B0C) and `glCompressedTexImage2D` (0x7F027A74).
  - Unnamed dispatchers: 0x7EE1AA3A, 0x7EE1B67F (6 tables), 0x7EE13AFB, 0x7EE19723, 0x7EE272E4 and 0x7EE1EE2B.
- **GPU registers** (V, new; 13f does not list this unit):
  - **0x7EE02D0C** is the control register 0x9AB00010. It returns whether a bit of mask 7 was set, then writes 7 or 0 (22 callers).
  - **0x7EE02D2F** reads and **0x7EE02D70** read-modify-writes the window 0x9AB02000 + (d0 & 0xFFFF), with a 4-bit byte-lane mask.
- **C3D:** 55 classes, 63 vtinit-chain functions, 56 fills and 428 slot targets (`c3d.py`).
  - The **string object** 0x7EE7F272/0x7EE7F08D/0x7EE7F0FE is init/set/get on any string field. The name at +12 uses the wrappers 0x7EE75E01 (set) and 0x7EE75E17 (get).
  - Other helpers named in D5: destroy object **0x7EE622F9** (95 callers: class id 1..59, then entry fini, then heap free); clone **0x7EE62349** (switch 0x7F02EB90, I); list next **0x7EE8EF9D** (74 callers) and remove 0x7EE8EE75; class-block getter 0x7EE75DA7.
  - Virtual-call stubs through the class block, for example **0x7EE74C2A** = slot +24 (50 callers).
- **AVPI:** 107 vtables (`avpi.py`). They include:
  - the 11 plug-in main vtables of 65 slots, with typeid 0x0802 (File Source 0x0803);
  - Video Encode **0x7F030888** and MP4 Demux **0x7F0316F8** (§5 item 1).
  - Helpers named in D5: Release **0x7EE99689** (refcount at +4, then dtor, then deleter; 31 callers); post message 11 to this+136, **0x7EE9DA70** (35 callers).
  - **Inferred:** vt 0x7F02F6F8 (type 0x0202) is the graph object. Its slot 8, 0x7EE91001, is the round-4 graph-walk slot (word 0x7F02F718).
- **libpng/zlib** (rule 1): 91 of the 94 rows in 0x7EE5D00D–0x7EE619C6 have a curated name; the other 3 are 3-byte pointer entries. 39 names are **V** by string or constant, for example:
  - `png_read_info` 0x7EE5D83E, `png_handle_PLTE` 0x7EE5E3B1, `png_read_row` 0x7EE5DA3F;
  - `png_get_PLTE` 0x7EE5D554 (`btst 8` = PNG_INFO_PLTE);
  - `crc32` 0x7EE5F5F3, `inflate` 0x7EE5FE61, `inflate_fast` 0x7EE611F5.

  The other 52 are **I**, matched by call structure, for example `png_crc_read` 0x7EE5E191, `inflateReset` 0x7EE5FC40, `adler32` 0x7EE61063 and `inflate_table` 0x7EE615D3. The PNG glue also holds a copy of `png_set_read_fn` (0x7EE5D00D). It installs the stream read callback 0x7EE5D043 (V).

## 4. Coverage and measured accuracy

**6,459 / 6,459 rows have a role.** 13 rows (0.2 %) say only "no callers, no code references".

| Level | D5 first build | D5 final | D6 final | **D7 final** |
|---|---|---|---|
| S specific | 2,887 (44.7 %) | 3,648 (56.5 %) | 3,634 (56.3 %) | **3,993 (61.8 %)** |
| P own facts / named context | 2,902 (44.9 %) | 2,457 (38.0 %) | 2,469 (38.2 %) | **2,228 (34.5 %)** |
| C context only | 670 (10.4 %) | 354 (5.5 %) | 356 (5.5 %) | **238 (3.7 %)** |

The D7 build has **6,343 V rows and 116 I rows** (D6: 6,345 and 114). Specific share by component, D6 → D7: GL 64 → 67 %, engine core 18 → 30 %, image decoders 71 → 74 %, C3D 62 → 68 %, AVPI 62 → 65 %.

The D6 build had 6,345 V rows and 114 I rows. The component and family positions are I where §1 says so. Specific share by component: libpng/zlib 100 %, image decoders 71 %, GL 64 %, C3D 62 %, AVPI 62 %, engine core 18 %.

**D7 diff against D6:** 1,616 rows changed; in 577 the first fact changed (the rest changed only quoted names in the context). Level moves: P→S 306, C→P 65, C→S 53. 18 rows changed their component (the withdrawn "float-heavy internals" family), 2 their V/I.

**D6 diff against D5:** 2,300 rows changed. In 1,036 the first fact changed; in the rest only quoted names in the call-graph context changed. 65 rows changed their component (the maths edge), 3 their V/I, and 195 their level (S→P 77, P→S 74, C→P 18, S→C 14, P→C 9, C→S 3). The 383 "… Plug-in group, by position" labels are gone.

## 4.1 Rule precision (D7, cycle 3)

D7 adds 3 rules and 115 hand roles. Each new rule was sampled with 10 random rows (seed `d7-<rule>`), every claim checked against the listing, the call edges and the chain or wrapper code. Samples: `$S/d7/gfx/samples/`.

| Rule (`rkey`) | Level | Rows | Checked | Wrong | Precision | Action |
|---|---|---|---|---|---|---|
| leaf-sum (new) | S | 116 | 10 + 10 | 0 + 0 | 20/20 | the first build dropped every store with an offset (`mov d0,(4,a0)` was split at the comma), so those functions were skipped, not described wrongly; fixed (51 → 116 rows) and re-sampled |
| c3d-chain-step (new) | S | 147 | 10 | 0 | 10/10 | the wording "returns a bool" became "the chain stops unless it returns 1" (the chain tests the low byte = 1) |
| wrapper-body (new) | S | 57 | 10 + 10 | **1** + 0 | fixed, 10/10 | 0x7EE93932 was "body of plug-in slot 40 0x7EE94B90", but that slot calls it only when the member +36 is non-NULL and passes the member, not this. The rule now needs no branch before the call and a0 passed unchanged; 1 minor in the re-sample (the slot-4 wrapper 0x7EEAE2AD stores the result at +388) fixed: the row now says so |
| curated (D7 hand roles) | S | 472 (all curated) | 15 | 0 | 15/15 | the 70 engine rows (`hand/engA.tsv`, `hand/engB.tsv`) were written by two reader agents; 15 of them re-read: 0x7EE3B121, 0x7EE4A6ED, 0x7EE3B5F0, 0x7EE4BD3B, 0x7EE4BD45, 0x7EE47520, 0x7EE5B2BD, 0x7EE487A0, 0x7EE36EDD, 0x7EE2E2F7 (engA), 0x7EE4B9B4, 0x7EE295E0, 0x7EE3B6E7, 0x7EE44F36, 0x7EE30B68 (engB). The F067–F079 roles and the GL, C3D and AVPI framework hand roles (`hand/*_me.tsv`) were read directly |
| plug-in slot dictionary | S (hedge I) | slots 10, 48 | 7 targets | 0 | — | inline `(I: slot k = …)`; slot 48 targets differ in detail, so the meaning stays general |

The D6 rules are unchanged; their D6 precision (below) still applies. No rule was demoted: the one rule with an error (wrapper-body) was fixed and re-sampled.

**Withdrawn position family:** "float-heavy internals 0x7EE1B436–0x7EE1E8DF" (DMP GL). Only 3 of its 18 functions call a soft-float routine, and F068 0x7EE1E87E is integer code (coverage r8 F068). The functions are now "GL API + internals".

**Final check (D7 build, 40 fresh rows, seed `d7-final-40-2026-11-09`, rows of earlier samples and of the engine hand list B left out; `samples/final40.txt`):** 38 V rows and 2 I rows (libpng names). **0 wrong** among the 38 V rows; 0 minor. The sample holds rows of 16 rules: call-graph 11, avpi-slot 6, curated 4, c3d-slot 3, c3d-chain-step 2, wrapper-of 2, code-pointer 2, avpi-codes 2 and 1 each of 8 others. The 11 call-graph rows are context only; they are true but give no role. After the last hand reads were merged, 2 sample rows (0x7EE7E89F, 0x7EE66A02) changed only in a quoted callee name; both were re-checked.

## 4.1b Rule precision (D6)

Each rule (the primary fact's rule, `rkey` in `idx.py`) with more than 50 rows was sampled: 10 random rows, every claim of the row checked against the disassembly, the call edges and the rodata words. A false statement is an error; true but incomplete is "minor". Samples are in `$S/d6/gfx/samples/`, verdicts in `verdicts/`. A rule with an error was fixed and re-sampled with 10 fresh rows. Rows = D6 final rows whose primary fact comes from the rule.

| Rule (`rkey`) | Level | Rows | Checked | Wrong | Precision | Action |
|---|---|---|---|---|---|---|
| call-graph (context only) | P/C | 1,683 | 10 | 0 | 10/10 | quoted I names now read `(I: …)` |
| avpi-slot | S | 943 | 10 | 0 | 10/10 | minor fixed: "shared by n" counted a vtable whose word points at a merged inner entry |
| c3d-slot | S | 428 | 10 | 0 | 10/10 | minor fixed: no override-chain note on slot +0 (it sums the level sizes) |
| curated | S | 357 | 10 + 20 | 0 + 0 V (1 I) | 30/30 V | **3 false curated names found outside the samples** (final check and a D6 read), fixed; re-sample of 20: 0 wrong V, 1 wrong I (`png_error` "never returns"), 3 minor; all 4 fixed |
| gl-table | S | 327 | 10 | 0 | 10/10 | — |
| avpi-codes | P | 322 | 10 | 0 | 10/10 | — |
| shape-getter | S | 257 | 10 + 10 | 0 + 0 | 20/20 | 1 wrong row outside the sample (0x7EE75EEC returns (+44)+36): null-checked getter now needs `load; retf` and 0 on the NULL path; re-sampled |
| shape-setter | S | 207 | 10 | 0 | 10/10 | minor fixed: u8/u16 width |
| wrapper-of | S | 206 | 10 + 10 | **1** + 0 | fixed, 10/10 | 0x7EECD604 (382 B) counted only up to an early `ret`: now the whole listing ≤ 8 instructions and no early return; a call behind a non-NULL test is marked "(the call is conditional)" |
| c3d-registry | S | 165 | 10 | 0 | 10/10 | — |
| shape-wrapper | P | 164 | 10 | 0 | 10/10 | same wrapper fix |
| code-pointer | P | 139 | 10 | 0 | 10/10 | — |
| c3d-stream | S | 139 | 10 + 10 | **9** + 0 | rewritten, 10/10 | D5 rule: "1 B" lengths from the return value, field counts that included non-stream loads, "a1" when the stream was d0. Rewritten as symbolic a1 tracking (copies, sp spills); lists the called slots and counts; the D5 type key dropped |
| shape-const | S | 134 | 10 | 0 | 10/10 | — |
| float-ops | P | 125 | 10 | 0 | 10/10 | — |
| c3d-chain | S | 117 | 10 | 0 | 10/10 | minor fixed: the accessor rule now stops on a store through a non-alias register |
| runtime-callees | P | 101 | 10 | 0 | 10/10 | — |
| avpi-loader | S | 100 | 10 + 10 | **4** + 0 | rewritten, 10/10 | D5: "ctor of vt X" on every loader; rows then quoted the wrong class (0x7EE909A6, 0x7EE9C59B store 0x7F02F684 only in a member or temporary) and called a singleton getter a ctor (0x7EE9F37A). Rewritten as the vptr-store rule (§2 rule 5) |
| data-word | P | 86 | 10 | 0 | 10/10 | — |
| error-raise | P | 78 | 10 | 0 | 10/10 | — |
| hsw-case | S | 78 | 10 | 0 | 10/10 | 10 minor fixed: the listed number is the case value (key + bias), not the key |
| service-calls | P | 71 | 10 | 0 | 10/10 | — |
| engine-table | S | 68 | 10 | 0 | 10/10 | — |
| shape-forwarder (new) | S | 34 | 10 | 0 | 10/10 | replaces the D5 "virtual-call stub" (230 rows), which took the first indirect call of any short function: png_free 0x7EE5D693 (a function-pointer field), 0x7EE621B2 (multi-call), 0x7EEB6A8D (member call, §5 item 8) |
| avpi-slot-inner | P | 20 | 10 | 0 | 10/10 | — |
| avpi-dtor-sig, avpi-registry-read, avpi-factory, jt-case | S | 10, 7, 12, 1 | all | 0 | all | "destroys members" reworded to "calls member/base destructors" |

Not sampled (< 50 rows, not S, or already I): mp4-box 40 (I), avpi-vt-store 22 (P, new; 3 rows checked in the final samples), ptr-entry 14, strings 4.

**Demoted:** no rule was left imprecise. The two rules that failed (c3d-stream, avpi-loader) were rewritten instead and re-sampled; the D5 stream type key ("vt+8 = u32, vt+12 = bytes") and the string-position plug-in group were dropped.

**Final checks (fresh rows, all claims):**
- **Final check 1** (40 rows, seed `d6-final-40-2026-11-09`, 39 V): **2 wrong V rows (5.1 %)**, both curated names: 0x7EE090C1 quoted 0x7EE08676 as "EGL display-handle check" (it stores d0 at RAM 0x606A335C and returns 0), and 0x7EEBD61B said "MP4 Demux vt slot 47" (it is slot 24; the review counted from the old wrong base 0x7F03169C). 1 minor (a stack temporary at sp+160 was "an object that is not its a0"). All fixed; the curated rule was re-sampled (20 rows, above).
- **Final check 2** after the fixes (40 new rows, seed `d6-final2-40`, 38 V): **0 wrong**, 2 minor, both fixed (a conditional call in a wrapper; a pointer-entry fact dropped from a slot row).
- **Together: 2 wrong among 77 V rows (2.6 %); 0 / 38 in the build that is in the TSV.**

**D5 history.** The D5 samples (seeds 2026, 99, 4242, 777, 31337, 8080, 2468; 30 rows each) found 9 / 210 errors (4.3 %); `$S/d5/gfx/verdicts.txt` lists them and their fixes.

## 4.2 Known rule errors and limits (open, I)

1. **AVPI vtable extents.** A vtable runs to the next code-loaded address. A secondary vtable that code never loads is merged into the one before it. Example: vt 0x7F02F958 has 40 slots, and slot 30 is a destructor. The slot numbers in such tails are offsets in the merged block.
2. **"ctor level" also covers copy ctors**, and a non-deleting destructor that re-stores the vptr at +0 of a0 would land there too (none found in 20 checks). The return-this tracking is a straight-line scan; it does not merge branch states.
3. **Forwarder "returns at once on NULL"** refers to the NULL-tested register, which can be the function pointer, not the object (0x7EE9BA23, 0x7EE9BA37).
4. **Hash-switch case rows** list every value whose case label lies inside the DB function. The function is one or more case blocks of the dispatcher, not a callable function.
5. **Wrapper rows** take their callee's name. A wrapper that shifts the field (for example +16 instead of +12) or normalises a bool is described only by its callee.
6. **Position families** (C3D class block, engine type block, plug-in range, MP4 writer/parser side) are I.
7. **Curated names** are the least checked source. Outside the first 10-row sample, D6 found 4 false curated statements: 2 in final check 1, 1 in a D6 read (0x7EE02BE5) and 1 in an I row of the re-sample (`png_error`). All are fixed (§5 item 11). Curated entries citing slot numbers from review r2 used the wrong MP4 Demux base; the one such entry is fixed.
8. **C3D code-pointer rows** (functions stored at +0/+12/+44 by 0x7EE66420, 0x7EE656B8 and others) look like vtable fills that `c3d.FILLS` misses; they are described only as code pointers.
9. **D7 rules.** Rule L reads each load at its program point and does not track aliasing between different base registers; `leaves` gives register values, which are not always return values. Rule Q calls the last chain step "own-level body" from the chain order (root first, then each level, 14a). Rule B states what the wrapper adds (constants, a stored result) but not argument shifts in d0/d1 that are not constants.
10. **Plug-in slot dictionary** (I): only slots 10 and 48 have a shared meaning; the other 63 slots are named only where their own target was read.
11. **Fixed in D6** (no longer open): the string-position plug-in group (383 rows); the member call read as a self call (0x7EEB6A8D); the merged slot-35 stub inside 0x7EEC4FAC (now rule M); the maths edge; the D5 stub, stream, loader, wrapper and null-checked-getter rules.

## 5. Corrections to older sections

1. **13b §2.4 plug-in registry table** (V):
   - **Video Encode → vtable 0x7F030860 is wrong.** 0x7F030860 is a 10-entry jump table of the slot-9 function 0x7EEA7C7D (keys 0x03000101–0x0300010A). The main vtable is **0x7F030888**; the ctor 0x7EEA7B6D stores it at 0x7EEA7B82.
   - **MP4 Demux → 0x7F03169C is wrong.** It is the 9-entry jump table of 0x7EEBC9BB (keys 0x03000B01–0x03000B09). The main vtable is **0x7F0316F8** (ctor 0x7EEBC784).
   - **0x7EEBC9BB is not the MP4 Demux ctor.** It is interface slot 9 (word 0x7F03171C).
2. **13b §2.4 "12 plug-ins" layer.** 0x7F02FCD8 (14 words in the Audio Encode group) is the jump table of 0x7EE9DB19 (cases 0–13), not a vtable. The codec-driver "tables" 0x7F0335B4, 0x7F033604, 0x7F033650, 0x7F0336A0, 0x7F033958, 0x7F0339A4 and 0x7F0339F0 are jump tables of 0x7EEC6D26/6FAB/7170/80DC/A34D/A39B/A43C (V).
3. **13b §3 "AVPI GetTypeId = vtable slot 1"** holds for the plug-in main classes and many small classes, but not always. For example, slot 1 of vt 0x7F02F904 is 0x7EE96F23, a 163-byte method (V).
4. **14a §2.4 object layout** "+12 name string (init 0x7EE7F272, set 0x7EE7F08D, get 0x7EE7F0FE)". These three are **string-object** functions used for any string field; 0x7EE68653 calls the setter on +16. The name accessors are 0x7EE75E01 and 0x7EE75E17 (V).
5. **14a §2.1 and §1 GL rodata.**
   - "switch tables from 0x7F02429C (into glLight/glMaterial code)" is incomplete. 0x7F02443C–0x7F027BD7 holds the **27 hash-switch tables** of §3. 72 of the 94 GL "functions" with no callers are their case blocks (V).
   - The GPU register helpers 0x7EE02D0C/0x7EE02D2F/0x7EE02D70 (0x9AB00010, 0x9AB02000) belong in 13f §2.1 as a GPU unit (V addresses; "GPU" is I).
6. **14a §2.4 C3D rodata** "jump tables into 0x7EE61A4F/0x7EE623xx/0x7EE69EEE…". The decoded tables are (V):
   - 0x7F02EB90: the class-id switch (59 cases) of clone 0x7EE62349;
   - 0x7F02ED84/0x7F02EDE0 of 0x7EE69C86, and 0x7F02F020 of 0x7EE7A764;
   - 0x7F02F088/0x7F02F0AC of the object methods 0x7EE7CE22/0x7EE7CEDD;
   - 0x7F02F198 of 0x7EE7F449, and 8 tables 0x7F02F2BC–0x7F02F3B8 of 0x7EE82BCB.

7. **16e (D5) "maths 0x7EE5AC2B–" is too high** (coverage r7). The last engine type-table function is the type-27 destructor 0x7EE54C66 (and its helper 0x7EE54C7F). From 0x7EE54C93 (16.16 fixed → float matrix, constant 2^-16) the code is matrix and vector maths: identity 0x7EE54E83, matrix copy 0x7EE54EEB, 4×4 multiply 0x7EE554AB, rotation 0x7EE57656, float → 1.12 fixed 0x7EE5A857 (F071), sin/cos, clz 0x7EE5B56B (F072). The edge is now 0x7EE54C93 (I).
8. **16e (D5) row 0x7EEB6A8D** "virtual-call stub: calls slot +12 of the vtable of the object" is wrong (audit A12-2 row 23). It calls slot +12 of the **member object at +4**. It returns 2 when the member is NULL or the call returns non-zero; when the call returns 0, it sets +8 = 2 and returns 0. Its DB function also holds a second entry 0x7EEB6AB3 (`mov 2,d0; retf`).
9. **16e (D5) plug-in group labels by string position** (383 rows) are withdrawn. The H.264 engine vtables 0x7F0301CC, 0x7F030218, 0x7F0302D4 and 0x7F0307E8 are created only from Video Encode code (ctor callers; 13b had this right). The vtables 0x7F02FD10–0x7F02FE5C, which the string position put in "Audio Encode", are created from 6–11 plug-ins (shared framework classes).
10. **Coverage r7 roles added** (curated, V unless marked): count leading zeros 0x7EE5B56B (F072); float matrix → 1.12 fixed 0x7EE5A857 (F071); type-3 buffer size 0x7EE4B894 (F070); recursive child-record walk 0x7EE46D87 (F069); class-41 set position 0x7EE7062D (F073; "position" I); timer-entry rescheduler 0x7EE9A6FF (F075; "timer" I); plug-in completion count and listener notify 0x7EE91DBC (F074); H.264 engine slot 18 body 0x7EEA7AE6 (F076); type-6 session slot 34 0x7EEC4FAC (F077).
11. **D5 curated names corrected in D6:** 0x7EE08676 is "store d0 at RAM 0x606A335C, return 0" (not an EGL display-handle check); 0x7EE02BE5 writes 640 to *(d0) and 480 to *(d1) (not an eglGetProcAddress helper); 0x7EEBD61B is MP4 Demux slot 24 (not 47); 0x7EE332C3 is a 3-B pointer entry whose body 0x7EE332C6 does the MB magic memcmp; `png_error` 0x7EE5D2DF returns (it sets png_ptr+308 = 1 and calls the error callback); `png_get_rowbytes` 0x7EE5D45E is I (it also clears png_ptr+308, which 1.2.37 does not).

12. **16e (D6) family "float internals 0x7EE1B436–0x7EE1E8DF"** is withdrawn (coverage r8 F068; §4.1). The texture-name hash insert 0x7EE1E87E is integer code.
13. **Coverage r8 roles added in D7** (curated, each re-read): GL state free 0x7EE02A44 (F067), texture-name hash insert 0x7EE1E87E (F068), mip-level size 0x7EE49058 (F070), textured-quad draw 0x7EE4ED2C (F071, "sprite blit" I), scissor 0x7EE4F97B (F072) with the rectangle store 0x7EE548B1, C3D copy body 0x7EE79186 (F073), class-2 fini body 0x7EE7B6E8 (F074), timer-list fire 0x7EE9AB38 (F076, "timer" I), payload-class assign 0x7EE9E820 (F077), Audio Source slot 48 0x7EEA13FE (F078), Video Decode slot 10 0x7EEB8952 (F079). AVPI plug-in base methods: slot 3 0x7EE9DC15 (stores a1 at +68, then calls slot 49) and slot 38 0x7EE9E477 (+68, then slot 37); slots 15/16/28 0x7EE94C20/0x7EE94C68/0x7EE94BB9 run pin vt+52/+56/+88 over the pin list (+32)+8.

## 6. How to classify a new function here

1. Look it up in the TSV. A function the database does not have usually lies inside a row: a case label, or a second slot entry ("contains the entry of slot k", or "also holds a separate entry X").
2. **By bytes:**
   - `fc a? 94 e9 2b 60` (`mov (0x602BE994),aN`) means GL;
   - `udf00 28,d0; add 0x7F02AA14` means the engine type table;
   - `mov IMM,d0; mov d0,(off,a0)` … `mov 1,d0; retf` is a C3D vtable fill;
   - `mov 0x7EE8FEF7,a0; ret` is an AVPI destructor;
   - `mov 1,d0; mov N,d1; call 0x7EE62AD7` is C3D error N;
   - `mov 0x9A00xxxx/0xAB01xxxx,d0` is an AVPI result code.

## 7. Open questions

1. The names of the 65 plug-in interface slots (D7: only slots 10 and 48 have a shared meaning, and base methods of slots 3, 15, 16, 28, 38 are described) and of the C3D slots from +16 up. The C3D property setters have offsets but no property names; the only named one is class 41 +84..+92 (I: position, F073 of r7).
2. **The engine core is 30 % specific** (D6 18 %; D7 added the leaf summaries and 70 hand roles: growable array 0x7EE53263/0x7EE53368/0x7EE532E3, u16 index iterator 0x7EE50D6A/0x7EE50DF5, vec3 and matrix helpers). Engine types 3–27 and most type-module functions have only float-op and call-graph context. Naming the types (14a open question 2) is the next step.
3. The codec hardware driver 0x7EEC673F–0x7EECC66F (118 P rows) needs the 0x9940xxxx register map.
4. The non-plug-in AVPI classes (types 0x0202, 0x0401–0x0403, 0x0603, 0x0705, 0x0903, 0x0905, 0x0A03, 0x0B03/0x0B04, 0x0C02/0x0C03, 0x0D03) need names; only CMutex, CAutoLock, the format descriptors and the sample pool are named.
