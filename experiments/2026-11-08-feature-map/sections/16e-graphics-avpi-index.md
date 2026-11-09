# 16e. GL, 3D engine, image decoders, libpng/zlib, C3D and AVPI 0x7EE02095–0x7EECE318: generated function index

Round D5, cycle 1 (2026-11-09). E-PM2 v1.6, block 0, runtime = 0x7E421020 + offset. This range had no per-function index. Before this round, 5 of the 20 round-6 batch-4 functions (F071–F075) fell in it and had no row.

- **Labels:** **V** = read in code or bytes. **I** = inferred from names, order, position or outside knowledge. libpng and zlib names come from matching against the public sources. They are **I** unless a string or constant proves them. GL enum names are outside knowledge (I).
- **Index:** `16e-graphics-avpi-index.tsv` has **one row for each of the 6,459 database functions** in the range. The range has 6,464 functions in `build/map/functions.tsv`; the 5 with `data_page` = 1 or `suspect` = 1 are left out. The columns are:
  - `addr`, `size`;
  - `component`: the component, then `>` and the family (§1);
  - `role`;
  - `basis`: the rule or table that gave the role;
  - `V/I`;
  - `level`: S = specific role, P = own facts only (codes, callees, strings) or a named call-graph context, C = context only.
- **Scratch:** `$S/d5/gfx/` (S = `/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad`). Run `python3 -I idx.py`; it writes `16e.tsv` and `rows.pkl`. The modules are:
  - `db.py`: the loader, the code-immediate index and the GL entry table;
  - `jt.py`: linear jump tables;
  - `hsw.py`: GL hash switches;
  - `c3d.py`: the C3D registry, ctor and vtinit chains, and vtable fills;
  - `avpi.py`: AVPI vtables, plug-in groups and the registry;
  - `curated.py`: hand roles, with the section or read cited;
  - `glenum.py`: GL enum names.

  `rd.py` and `q.py` are readers. `sample1–7.txt` and `verdicts.txt` hold the accuracy samples.

## 1. Area and boundaries

The component edges are those of 14a §1 and 13b §1. This round did not move them. The sub-family edges below are the ones the `component` column uses.

| Range | Component › families | Rows | S share |
|---|---|---|---|
| 0x7EE02095–0x7EE294B4 | **DMP GL**: library init + DVOJ (to 0x7EE0357F; it includes the GPU register helpers 0x7EE02D0C–0x7EE02DD5), EGL 0x7EE08680–0x7EE09129, back end 0x7EE10B33–0x7EE19609, float internals 0x7EE1B436–0x7EE1E8DF, texture internals 0x7EE2245D–0x7EE24292, and GL API + internals elsewhere | 672 | 64 % |
| 0x7EE294B5–0x7EE5B5BB | **3D engine core**: MC* loaders, GL render back end 0x7EE2FF5E–0x7EE32698, stream, resource loaders, MB/MT loaders, type modules 0x7EE36D26–, maths 0x7EE5AC2B– | 949 | 17 % |
| 0x7EE5B5BC–0x7EE5D00C | **Image decoders**: BMP, GIF89a (pixel converters 0x7EE5C4D6–), PNG glue 0x7EE5C8CD– | 31 | 71 % |
| 0x7EE5D00D–0x7EE5F5F2 | **libpng 1.2.37** (read side) | 80 | 100 % |
| 0x7EE5F5F3–0x7EE619C6 | **zlib 1.2.3** (crc32, inflate) | 14 | 100 % |
| 0x7EE619C7–0x7EE8F4F3 | **C3D framework**: API to 0x7EE61E54, context/registry/stream to 0x7EE62C0F, class code, helpers 0x7EE8F081– | 2,584 | 60 % |
| 0x7EE8F4F4–0x7EECE318 | **AVPI**: OSAL, framework classes 0x7EE90235–, plug-ins 0x7EE9C332–, SCA 0x7EEC1B72–, C++ support 0x7EEC5F32–, kernel message glue 0x7EEC62B9–, codec hardware driver 0x7EEC673F–, codec task + DFS glue 0x7EECC670– | 2,129 | 65 % |

**Families by position (I):**
- **C3D class blocks.** A C3D class-code row gets `in the code block of class id N` when the nearest registered ctor, fini, vtinit, own level or own-slot function on **both** sides belongs to class N. The two anchors must also be less than 0x1800 bytes apart.
- **Engine type blocks.** An engine type-module row gets `engine type T` by the same test. The anchors are the type-table functions and the `alloc(T)` creators; the limit is 0x2000 bytes.
- **Plug-in code ranges.** An AVPI plug-in row gets `<plug-in> code` when it lies between the lowest and highest own (unshared) slot target of that plug-in's 65-slot vtable.

## 2. Rules (in priority order)

Each row has a primary fact, up to two more own facts, and then a call-graph context when the role is weak. The `basis` column names every rule used.

| # | Rule | Source / byte signature | S rows |
|---|---|---|---|
| 1 | **curated** | 348 roles (rows in the DB) copied from 14a, 13b, 13f and the coverage reviews (rounds 1–6), plus D5 reads of the most-called unnamed functions. The libpng/zlib catalogue is in §3 | 347 |
| 2 | **GL table** | `14a-gl-entry-points.tsv`: an entry row is "table entry (prologue only; the body is the next DB function)" or "table entry; the body lies inside this function"; a body row is "body (direct-call target)" | 327 |
| 3 | **switch case blocks** | (a) **GL hash switches** (`hsw.py`): 27 tables of rows `{u32 key, code}`. The dispatcher does `(x − bias) & mask`, probes linearly, then `mov (4,a0),a0; jmp (a0)`. The key is pname − bias (0xB0F for the enable caps, 0xAFF for glGet*). Fwmap split the case labels into "functions" (§4.1). (b) Linear jump tables (`mov TAB,aN; mov (dX,aN),aN; jmp (aN)`); only 2 of their targets are DB starts | 78 + 1 |
| 4 | **C3D registry and vtinit fills** | `regs.json` (D2: 55 registrations of 0x7EE642F3) gives the class ctor, fini and vtinit. The ctor and vtinit chains give the level ctors and level fills: a level used by one class is "own", otherwise "base level shared by ids …". Each fill (`mov IMM,d0; mov d0,(off,a0)` …, `mov 1,d0; retf`) gives "vtable slot +off of class N / base level". Slots +0/+4/+8/+12 are size/write/read/copy (14a). An override whose first call is a root method gets the override-chain note | 710 |
| 5 | **AVPI vtables** | A vtable is a code-loaded rodata address in 0x7F02F684–0x7F034000 whose words are AVPI code. It runs to the next loaded address and excludes jump tables (§4.2). Slot k gives "vtable slot k of class vt X". 65-slot vtables are the 11 plug-in main classes (`plug-in interface slot k`). Slot 1 `mov K,d0; retf` gives GetTypeId. A slot word inside a DB function gives "contains the entry of slot k". A non-slot-0 loader is "ctor (stores the vtable)", or "destructor body" if it ends with `mov 0x7EE8FEF7,a0`. The 12 registry factories come from .data 0x7E8EFA18 | 1,069 + 12 |
| 6 | **engine tables** | Type table 0x7F02AA14 (28 × {size, dtor, +8, +12, +16, slot +20, +24}); format-loader table 0x7F027C4C; MCM chunk jump table 0x7F027BFC; pixel-converter table 0x7F02B1F8; .data function tables 0x7E8EF20C–0x7E8EF8BC (P only) | 68 |
| 7 | **pointer entry** | ≤ 6 bytes of `movm`/`add` followed by a DB start. The row takes the next function's name unless its own table role is already set | 4 |
| 8 | **shape** (bytes) | `retf` alone = empty; `mov K,d0; retf` = constant (a function or rodata address is named); getter or setter (see below); `mov (abs),d0; retf` = global getter; virtual-call stub = one `calls (aR)` after `mov (N,aV),aR` and a vptr load, with the slot and the member offset given; C3D stream helper = ≥ 2 calls of the stream argument's vt+8/+12 (vt+8 = u32, vt+12 = bytes); AVPI destructor = `mov 0x7EE8FEF7,a0; ret`; access to the plug-in registry 0x602BF558; a wrapper (≤ 8 insns, one call) takes its callee's name | 992 |
| 9 | **own strings** | Strings loaded. 4-char MP4 box names in MP4 Mux/Demux become "MP4 Mux (writer)/Demux (parser) code for box `X`" (the side is by position, I) | 40 |
| 10 | **error codes** | GL: `mov 0x50N,d0; call 0x7EE097DA` gives `raises GL_INVALID_*`. C3D: `mov 1,d0; mov N,d1; call 0x7EE62AD7` gives `C3D error N`. AVPI: the 0x9A/0xAA/0xAB/0xCA/0xCB/0x8000000x constants (P) | — |
| 11 | **service calls** | Constant arguments (tracked back to the previous call or branch; the last write to the register decides): engine alloc(type), C3D create(class id), AVPI malloc(n), new(n); the GL entries called; MMIO (codec 0x9940/0x9950, GPU 0x9AB0, 0x9810, 0x98B0); the soft-float and libc callees (13a names) as "float computation: n ops (fmul×…)" (P) | — |
| 12 | **code pointer** | A function with no callers whose address is loaded by code: "code pointer loaded by X (stored at +off)" (P) | — |
| 13 | **call graph** | One caller gives `helper of X (name)` plus the nearest named ancestor (BFS, ≤ 4 levels). Several callers give `shared helper, n callers` with named examples. The named callees are listed too | — |

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

| Level | First build | Final |
|---|---|---|
| S specific | 2,887 (44.7 %) | **3,648 (56.5 %)** |
| P own facts / named context | 2,902 (44.9 %) | 2,457 (38.0 %) |
| C context only | 670 (10.4 %) | 354 (5.5 %) |

The final build has **6,344 V rows and 115 I rows**. The component and family positions are I where §1 says so.

**Accuracy.** Each sample is 30 random rows. Every claim in the row was checked against the disassembly, the call edges and the rodata words (`verdicts.txt`). An error is a false statement; a vague but true context does not count.

| Sample (seed) | Build | Errors | Rule fixed |
|---|---|---|---|
| 1 (2026) | first | 2 | getter on a list walk; slot entry inside another DB function |
| 2 (99) | +fixes | 0 | — |
| 3 (4242) | +stream/box rules | 2 | constant-argument tracker kept a stale `clr d0` (`new(0)`); GL "prologue only" on an entry that holds its body |
| 4 (777) | | 1 | 0x7EE7F08D was named "object name set"; it sets any string field |
| 5 (31337) | | 3 | error-state compare read as a range; a multi-call reader called a "stub"; a getter that returns a compare result |
| 6 (8080) | | 1 | constant stores reported as `= d0` |
| **7 (2468)** | **final** | **0** | — |

**All samples together: 9 / 210 = 4.3 %. The final fresh sample: 0 / 30.**

**Rule-fix diffs** (TSV before → after):
- the sample-1 fixes changed 141 rows: 72 slot rows, 39 getter/setter rows and 30 context names;
- the argument fix changed 8 rows;
- the constant-store and alias fixes changed 96 rows, of which 30 changed their own role.

10 changed rows of each fix were spot-checked against the code. All the new versions are correct (for example 0x7EE7ADB5 "+0 = a1, +4 = 0, +8 = 0" and 0x7EE1E868, which now has no setter claim because it writes through the global object at 0x602BEADC).

**Specific share by component:** libpng/zlib 100 %, image decoders 71 %, AVPI 65 %, GL 64 %, C3D 60 %, engine core **17 %**.

## 4.1 Known rule errors and limits (open, I)

1. **AVPI vtable extents.** A vtable runs to the next code-loaded address. A secondary vtable that code never loads is merged into the one before it. Example: vt 0x7F02F958 has 40 slots, and slot 30 is a destructor. The slot numbers in such tails are offsets in the merged block.
2. **AVPI loaders.** "ctor (stores the vtable)" also catches copy ctors. A non-deleting destructor that does not end with `mov 0x7EE8FEF7,a0` can land there too. When a ctor stores two vtables, the row names the first one, which is the base.
3. **Virtual-call stub "of the object".** The text means the object in a0. It can be an argument, not `this`.
4. **Hash-switch case rows** list every key whose case label lies inside the DB function. The function is one or more case blocks of the dispatcher, not a callable function.
5. **Wrapper rows** take their callee's name. A wrapper that shifts the field (for example +16 instead of +12) is described only by its callee.
6. **Position families** (C3D class block, engine type block, plug-in range, MP4 writer/parser side) are I.

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

## 6. How to classify a new function here

1. Look it up in the TSV. A function the database does not have usually lies inside a row: a case label, or a second slot entry ("contains the entry of slot k").
2. **By bytes:**
   - `fc a? 94 e9 2b 60` (`mov (0x602BE994),aN`) means GL;
   - `udf00 28,d0; add 0x7F02AA14` means the engine type table;
   - `mov IMM,d0; mov d0,(off,a0)` … `mov 1,d0; retf` is a C3D vtable fill;
   - `mov 0x7EE8FEF7,a0; ret` is an AVPI destructor;
   - `mov 1,d0; mov N,d1; call 0x7EE62AD7` is C3D error N;
   - `mov 0x9A00xxxx/0xAB01xxxx,d0` is an AVPI result code.

## 7. Open questions

1. The names of the 65 plug-in interface slots and of the C3D slots from +16 up. Each name would turn about 11 or about 26 rows into named methods.
2. **The engine core is 17 % specific.** Engine types 3–27 and most type-module functions have only float-op and call-graph context. Naming the types (14a open question 2) is the next step.
3. The codec hardware driver 0x7EEC673F–0x7EECC66F (118 P rows) needs the 0x9940xxxx register map.
4. The non-plug-in AVPI classes (types 0x0202, 0x0401–0x0403, 0x0603, 0x0705, 0x0903, 0x0905, 0x0A03, 0x0B03/0x0B04, 0x0C02/0x0C03, 0x0D03) need names; only CMutex, CAutoLock, the format descriptors and the sample pool are named.
