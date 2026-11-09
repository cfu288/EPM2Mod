# 14a. The 3D/graphics stack: DMP GL, the 3D engine core, image decoders, libpng/zlib, the C3D framework

Round D2 deep dive. E-PM2 v1.6, block 0, runtime = 0x7E421020 + offset. Area: code 0x7EE02095–0x7EE8F4F3, rodata 0x7F021020–0x7F02F683.

- **Labels:** **verified** = read in code or bytes. **inferred** = from names, layout or call shape. **external** = outside knowledge, not checked in this firmware.
- **Scratch:** `/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/d2/c3d/`: `db.py` (DB loader), `summ.py` (per-function callers/callees by layer), `pages.py` (layer-to-layer call matrix), `gltab.py`/`gltsv.py` (GL table), `reg.py`/`tree.py` (class registry), `classify.py` (pattern classifier), `regs.txt` (55 registrations).
- **GL catalogue:** `sections/14a-gl-entry-points.tsv` (223 table slots, name → entry and body address).

## 1. Area and boundaries

Function counts are from `build/map/functions.tsv`.

| Range | Component | Fns | Basis |
|---|---|---|---|
| **0x7EE02095–0x7EE294B4** | **DMP EGL/GL library** (OpenGL ES 1.1 + OES + DMP extensions) | 672 | verified. The previous function 0x7EE01FF5 is GUI code (it reads info 109/279/44; 10 data words 0x7F011710…). 0x7EE02095 is the library init, called only from the overlay port 0x7F0A3838. The last function 0x7EE2946D is the body of `glPointSize` and ends at 0x7EE294B4. All 1,055 references to the GL context pointer 0x602BE994 (1,053 loads and 2 stores: `mov a0,(0x602BE994)` at 0x7EE11BDB and `mov d0,(0x602BE994)` at 0x7EE133AA) lie in 0x7EE026DC–0x7EE2946F (A6 2026-11-09) |
| **0x7EE294B5–0x7EE5B5BB** | **3D engine core** (file loaders, GL render backend, 28-type ref-counted object runtime, maths) | ~950 | verified layer edges (§2.2). Its object release 0x7EE47412 and type table 0x7F02AA14 are used only here (and by 24 C3D call sites in 20 functions, sites 0x7EE68935–0x7EE8ED9E; 156 of the 180 release call sites are in the core) (A6 2026-11-09) |
| 0x7EE5B5BC–0x7EE5D00C | Engine image decoders: BMP (0x7EE5B5BC–0x7EE5BB2B), GIF89a (0x7EE5BB2C–0x7EE5C8CC, incl. pixel converters 0x7EE5C4D6–0x7EE5C8CC from the table at 0x7F02B224), PNG glue (0x7EE5C8CD–0x7EE5D00C) | 31 | verified: magic checkers and loader table (§2.2) |
| **0x7EE5D00D–0x7EE5F5F2** | **libpng 1.2.37** (read side) | 80 | verified. 0x7EE5D00D uses the `read_data_fn`/`write_data_fn` string. 0x7EE5F5AB (memcmp-like) and 0x7EE5F5EC (getter of +308) are called only by libpng or PNG glue |
| **0x7EE5F5F3–0x7EE619C6** | **zlib 1.2.3** (crc32 0x7EE5F5F3 → table 0x7F02BE7C; inflate 0x7EE5FE61; `zmemcpy` 0x7EE619AC; stubs 0x7EE619BF/0x7EE619C4) | 14 | verified. crc32 starts with `buf == NULL → 0` and the `endian = 1` test |
| **0x7EE619C7–0x7EE8F4F3** | **C3D framework**: API, class registry, ~55 classes, heap/string/runtime helpers | 2,585 | verified. Its only outside callers are in overlay B (§2.4). The old split "C3D API 0x7EE619C7–0x7EE63004 / C3D-side code 0x7EE63000–" is not a real boundary |
| 0x7EE8F4F4– | AVPI (13b) | — | 13b |

Sub-ranges inside the engine core (verified from callees and strings; the ends are the last function before the next group):

| Range | Part |
|---|---|
| 0x7EE294B5–0x7EE2FF5D | MC* format loaders (`$Revision: #88 $`, 0x7F027CC4) |
| 0x7EE2FF5E–0x7EE32698 | GL render backend: the only engine code that calls GL entry points |
| 0x7EE32699–0x7EE32BE2 | Decompressing stream object, vtable 0x7F027F2C (inferred role) |
| 0x7EE32BE3–0x7EE332C2 | BMP/GIF/PNG resource loaders (`$Revision: #22 $`) |
| 0x7EE332C3–~0x7EE36D25 | "MB"/"MT" format loaders (`$Revision: #27 $`) |
| ~0x7EE36D26–0x7EE5AC2A | Type modules (§2.2) |
| ~0x7EE5AC2B–0x7EE5B5BB | Maths helpers (extent inferred) |

**Rodata 0x7F021020–0x7F02F683** (verified bytes, refs as given):

| Range | Content |
|---|---|
| 0x7F021020–0x7F0229AF | **Not graphics.** The tail of a 1,061-row `{u32 id, u32 0/3, u32 0}` table that starts at 0x7F01F7F4. No static reference was found (all words searched). Owner unknown; it is GUI-side by position (inferred) |
| 0x7F0229D0–0x7F022E17 | Labels of a DMP stock shader program (`silhrender_*`, `subdrender_main`, `sd_*`, `stockps1000.asm`) and uniforms `gl_SilhScaleDMP`, `gl_SubdLevelDMP`, `gl_AttribOffsetDMP`. Inferred: a silhouette and subdivision geometry shader |
| 0x7F022E18–0x7F023B88 | EGL/GL entry-name strings |
| **0x7F023B8C–0x7F024283** | **`{char *name, fn}` table: 223 slots** (29 `egl*` + 194 `gl*`, with `glDeleteQueriesDMP` twice). Terminator `{0x7F023B89 = "", 0}` at 0x7F024284. Read by `eglGetProcAddress` 0x7EE0912A → 0x7EE02BF5 |
| 0x7F02428C–~0x7F027BFF | GL data: `!!!!assert!!!!`; switch tables from 0x7F02429C (into glLight/glMaterial code); `Digital Media Professionals, Inc.` 0x7F024344 and `1.1 + extension pack` 0x7F024366 (eglQueryString 0x7EE0877E); `glX*` compatibility names 0x7F026BCB; shader tags `DVOJ`/`DVPE` 0x7F026C21; uniform names 0x7F026D08–0x7F026EE8 (builder 0x7EE15060) |
| 0x7F027C00–0x7F027CDB | Engine: MC chunk-factory jump table 0x7F027C00–0x7F027C33; magics `MCM_ MCA_ MCT_ MCE_` 0x7F027C38; **format-loader table 0x7F027C4C–0x7F027CBF** (§2.2); `$Revision: #88 $` |
| 0x7F027CDC–0x7F027E00 | GL backend constants: GL enums 0x404/0x405, 0x8892/0x8893, 0x1700–0x1702, 0x1D00/0x1D01, float matrices. A vendor quirk record `Qualcomm` 0x7F027DBC (word 0x7F027DC8) and `GL_OES_blend_func_separate` 0x7F027DD8 (word 0x7F027DFC) |
| 0x7F027F2C–0x7F028036 | Stream vtable 0x7F027F2C; small-integer tables; `$Revision: #22 $` 0x7F027F94; `MB` 0x7F02800C, `MT` 0x7F02800F; `$Revision: #27 $` 0x7F028036 |
| **0x7F02AA14–0x7F02AD23** | **Engine type table:** 28 rows × 28 bytes (§2.2) |
| 0x7F02B1CC–0x7F02B24A | `BM`, `GIF89a`, pixel-converter table 0x7F02B224–0x7F02B240, PNG signature 0x7F02B244 |
| 0x7F02B24B–0x7F02EB67 | libpng strings and tables, zlib CRC table (0x7F02BE7C, entry 1 = 0x77073096), inflate tables and messages, `1.2.3` |
| **0x7F02EB68–0x7F02F683** | **C3D framework rodata**: jump tables into 0x7EE61A4F/0x7EE623xx/0x7EE69EEE…; `ST_NORMAL` 0x7F02ED4A (used by 0x7EE631E4); `-Title`; `png` 0x7F02F17B (used by 0x7EE7D641); a 90-entry increasing LUT 0x7F02F51C–0x7F02F683 (used by the helper 0x7EE8F321) |
| 0x7F02F684– | AVPI rodata (the first words point to AVPI OSAL 0x7EE8FFC8…; 0x7EE90008 references 0x7F02F690). So AVPI rodata starts at **0x7F02F684**, not 0x7F02F600 |

## 2. Components

### 2.1 DMP EGL/GL library (0x7EE02095–0x7EE294B4)

- **What it is (verified):** an OpenGL ES **1.1** fixed-function API (it has the `x` fixed-point variants) with EGL, the OES extension pack, and the DMP extensions `gl*QueryDMP`, `glSetErrorFuncDMP`, `glLineStippleDMP` and `glBlendColorDMP`. Its version string is `1.1 + extension pack`.
- **Behind the API:** a shader back end that builds `gl_*` uniforms (0x7EE15060) and loads `DVOJ`/`DVPE` shader objects.
- **Hardware (external):** DMP's PICA-family GPUs expose an ES 1.1 API over a shader core in this way.
- **Entry points:** 223 table slots; see the TSV. 89 entries lie at or above 0x7EE21020; the last is `glPointSize` 0x7EE29468.
- **The table shapes the DB** (verified):
  - Each table entry is a pointer entry, `movm`/`add -N,sp` (2–6 bytes), and the DB lists it with 0 callers.
  - Direct calls target the body after that prologue: for example `glBindBuffer` 0x7EE27D5A ← calls to 0x7EE27D5F.
  - So a GL "function" with callers usually starts 5 bytes after a table address.
- **Internal blocks between the entry points** (verified extents; roles inferred from neighbours):

| Range | Content |
|---|---|
| 0x7EE02095–0x7EE0357F | Library init (1,607 B); 316-byte state object at RAM 0x602BE908; GetProcAddress lookup 0x7EE02BF5; `DVOJ` loading |
| 0x7EE050AB–0x7EE0867F | 34 internal functions, between lighting and EGL |
| 0x7EE08680–0x7EE09129 | EGL |
| 0x7EE0E2B2–0x7EE0F366 | 29 functions; `glX*` names; F066 (the 284-byte library object, 0x602BE978) follows at 0x7EE0F3D2 |
| 0x7EE10B33–0x7EE19609 | ~~Shader/uniform back end~~ Back end (70 functions; the shader/uniform role is inferred and does not fit all of it): it also holds the GL state-block creator 0x7EE133B3 (160 B via the allocator hook 0x606A33E8, stored at RAM 0x606A33E4; ← init 0x7EE0EDA7), whose sub-initialisers reach the texture-internal (0x7EE22793) and buffer (0x7EE2843C) areas (C3 2026-11-09) |
| 0x7EE1B436–0x7EE1E8DF | 17 large float-heavy functions |
| 0x7EE2245D–0x7EE24292 | 7 texture-internal functions |

- **Errors (verified):**
  - `glGetError` 0x7EE097CA reads and clears RAM 0x602BE93C.
  - The raise helper **0x7EE097DA(code)** has 129 callers. It sets 0x602BE93C only if it is 0, then calls the hook at 0x602BE940.
  - `glSetErrorFuncDMP` 0x7EE097F9 installs that hook; the overlay calls it from 0x7F09E9EE.
  - The codes are the GL ones: 0x500 = INVALID_ENUM … 0x502 = INVALID_OPERATION (external names).
- **RAM (verified):**
  - 0x602BE908–0x602BECxx: state; 0x602BE994 = current context; 0x602BE9A0 has 128 uses.
  - 0x606A32xx–0x606A38xx; 0x606A33E8 = allocator hook (111 uses).
- **Outside callers (verified, complete):**
  - the engine GL back end 0x7EE2FF5E–0x7EE32698;
  - the overlay port 0x7F0A3838 (EGL bring-up: GetDisplay, Initialize, ChooseConfig, GetConfigAttrib, CreateWindowSurface, QuerySurface, CreateContext, MakeCurrent and library init 0x7EE02095), 0x7F0A3BA2 (teardown: MakeCurrent, DestroyContext, DestroySurface, Terminate), 0x7F0A3BE9 (SwapBuffers), and 0x7F0A3C01/0x7F0A3C3E/0x7F0A3CB4/0x7F0A3CCE (surface switch, create and destroy);
  - the scene code 0x7F09E2FF (`glGetError`) and 0x7F09E9EE (`glSetErrorFuncDMP`).
  - **No GUI, playback or `play_gpu.c` code calls GL.**

### 2.2 3D engine core (0x7EE294B5–0x7EE5B5BB) and image decoders

**Format-loader table 0x7F027C4C** (verified): `{u32 magic_len, check_fn, load_fn}` × 9, terminated by zeros. Each check function is `memcmp(buf, magic, len)` 0x7E500D15.

| magic (len) | check | loader | Notes |
|---|---|---|---|
| `MB` (2) | 0x7EE332C3 | 0x7EE33D09 (8,669 B) | Rev #27 |
| `MT` (2) | 0x7EE332E5 | 0x7EE35EE6 | Rev #27. Creates types 13/14 (animation) |
| `BM` (2) | 0x7EE5B5BC | 0x7EE32BE3 | BMP, Rev #22. Decoder 0x7EE5B5DC/0x7EE5B739 |
| `MCM_` (4) | 0x7EE294B5 | 0x7EE2A285 (1,958 B) | Model chunks 0x7EE2AA2B…0x7EE2DDDA; byte reader 0x7EE2A22E (28 callers) |
| `MCA_` (4) | 0x7EE294D7 | 0x7EE2E32C | Creates type 14; its parser 0x7EE2E4A3 creates type 13 |
| `MCT_` (4) | 0x7EE294F9 | 0x7EE2EC22 | Creates type 12 (0x7EE49851, 0x7EE49905) |
| `MCE_` (4) | 0x7EE2951B | 0x7EE2F006 | No direct creation. The parsers after it (0x7EE2F328, 0x7EE2FA27) create types 20/21 (link inferred) |
| `GIF89a` (6) | 0x7EE5BB2C | 0x7EE32E5E | Rev #22 |
| PNG sig (8) | 0x7EE5C962 | 0x7EE3306E | Rev #22. Glue 0x7EE5C984/0x7EE5CB93 → libpng |

- **Shared helpers:** all three image loaders fill an image descriptor (0x7EE5C8CD: x, y, w, h, format; per-format tables 0x7F02B1xx). Then they create types 11 and 12 (0x7EE488DB, 0x7EE49851).
- **No asset in block 0:** no file of these formats is embedded in block 0 (a byte search finds only the magic strings). The C3D scene files come from outside block 0. Inferred: the `RES_MODE_C3D` resource or the card `D` file (08).
- **Vendor guess (external, not checked):** "MB"/"MT" match the headers of HI Corporation's Mascot Capsule `.mbac`/`.mtra`. No vendor string survives.
- **Object runtime (verified):**
  - **Header:** `{u32 type, u8 +5 pooled, u32 +8 refcount, u32 +12 serial}`.
  - **alloc(type)** 0x7EE4736E: malloc of the row size, init 0x7EE473A8, serial from RAM 0x602BF1A8.
  - **addref** 0x7EE47402.
  - **release** 0x7EE47412 (101 callers): decrement; at 0 call the row's destructor, then the pool or `free`.
  - **virtual slot +20** 0x7EE4745E (types 1–27).
- **Type table** 0x7F02AA14: 28 rows of `{size, dtor, 4 optional slots, slot +20}`.
  - Types 0 and 1 are abstract (size −1).
  - Types 5, 6, 8, 9, 15, 16 and 17 fill all slots. Inferred: these are the scene-node types.

| type | size | creator | dtor | type | size | creator | dtor |
|---|---|---|---|---|---|---|---|
| 2 | 0x558 | 0x7EE4F183 | 0x7EE4F592 | 15 | 0x3B8 | — | 0x7EE3B187 |
| 3 | 0x208 | 0x7EE4B27A | 0x7EE4B779 | 16 | 0x180 | — | 0x7EE4DEA6 |
| 4 | 0x198 | 0x7EE42A79/0x7EE42B0B | 0x7EE42E54 | 17 | 0x170 | — | 0x7EE5286D |
| 5, 6 | 0x150 | — | 0x7EE4A54D | 18 | 0x38 | — | 0x7EE47BF8 |
| 7 | 0x6C | 0x7EE3C3DB | 0x7EE3C5D6 | 19 | 0x20 | 0x7EE3C398 | 0x7EE3C3C5 |
| 8 | 0xE4 | — | 0x7EE4671F | 20 | 0x2B8 | 0x7EE47C1B | 0x7EE484EE |
| 9 | 0xE0 | — | 0x7EE4559D | 21 | 0x3AC | 0x7EE3ED5C | 0x7EE3F338 |
| 10 | 0xF4 | 0x7EE3FD2B/0x7EE3FE18 | 0x7EE3FEA3 | 22 | 0xF0 | 0x7EE41EE3 | 0x7EE42423 |
| 11 | 0x60 | 0x7EE488DB | 0x7EE489C4 | 23 | 0xCB4 | — | 0x7EE5366D |
| 12 | 0x28 | 0x7EE49851 | 0x7EE498BF | 24 | 0x50 | 0x7EE3E308 | 0x7EE3E3B1 |
| 13 | 0x40 | 0x7EE36D26 | 0x7EE36DD3 | 25 | 0x3C | — | 0x7EE4883A |
| 14 | 0x28 | 0x7EE3AD3B | 0x7EE3ADAF | 26 | 0x74 | 0x7EE499B9 | 0x7EE49A93 |
|  |  |  |  | 27 | 0x1CC | — | 0x7EE54C66 |

"—" = created through the generic 0x7EE475E6 (the type is in a register).

**Roles by type** (inferred):
- **Type 2** is the render context. 0x7EE4F183 creates it: singleton at 0x602BF3C8; it sets up the GL back end (0x7EE2FF5E, 0x7EE32638) and swaps through 0x7F0A3BE9 (from 0x7EE4F357).
- **Types 11 and 12** are the texture/image pair. The GL upload 0x7EE3085C (glGenTextures/glTexImage2D/glCompressedTexImage2D) uses 0x7EE49058/0x7EE49778, and 0x7EE48A8C/0x7EE48B6C use overlay surfaces as render targets.
- **Types 13 and 14** are animation data.

**GL render back end** 0x7EE2FF5E–0x7EE32698 (verified callees):
- vertex/normal/colour/texcoord arrays 0x7EE2FF88–0x7EE307F3 and draws 0x7EE303EC/0x7EE305A9/0x7EE30741 (with matrix palettes: `glCurrentPaletteMatrixOES`, `glMatrixIndexPointerOES`);
- texture create/upload/delete 0x7EE3085C–0x7EE30C09; VBO create/bind/update 0x7EE30CA0–0x7EE30D9B;
- viewport/scissor 0x7EE30DD6/0x7EE30E27; render-to-texture copy 0x7EE30E78;
- material 0x7EE310D0, blend/depth/cull state 0x7EE31450, fog 0x7EE31766, lights 0x7EE319D8, matrix load/mult 0x7EE31E10/0x7EE31E4B;
- **capability probe** 0x7EE31E55 (glGetString + glGetIntegerv + memcmp; it uses the `Qualcomm` quirk record, inferred);
- full state reset 0x7EE32085 (1,459 B); back-end create 0x7EE32638 / destroy 0x7EE3268B.

**Maths:**
- Verified: 0x7EE5ACA6 = sin with the angle in turns; 0x7EE5ADA3(x) = 0x7EE5ACA6(x + 0.25) = cos; 0x7EE5B2B3 = vec3 set (24 + 7 callers).
- Inferred: 0x7EE5B300/0x7EE5B3B0/0x7EE5B43D are vector operations. The Euler-angle builders (F068 0x7EE57656 and 5 neighbours) are reached through data-image tables 0x7E8EF4F8….

**Outside callers:** only the C3D framework (83 distinct targets). The heaviest are release 0x7EE47412 (24 sites), vec3 0x7EE5B2B3 (30), sin/cos (14 + 14) and the type-2 and type-11 API. The overlay calls the core only through C3D (verified, `pages.py`).

### 2.3 libpng 1.2.37 and zlib 1.2.3

Read side only, as in 08 (verified strings). libpng is called only by the PNG glue 0x7EE5C984/0x7EE5CB93. zlib is called only by libpng (0x7EE5DA3F, 0x7EE5EE73; crc32 also from 0x7EE5D13A/0x7EE5D14B). The function roles are standard zlib/libpng and were not catalogued here.

### 2.4 C3D framework (0x7EE619C7–0x7EE8F4F3)

**API called from overlay B** (verified call edges; roles inferred from call shape):

| Address | Role |
|---|---|
| 0x7EE61A4F → 0x7EE61A59 | **create(ctx)**: allocates 44 bytes through `ctx->vt[0]`, then init 0x7EE619C7. The init makes the 144-byte context (registry pointer at +4, heap at +36), runs the registry 0x7EE621FD → 0x7EE64322 and 0x7EE64272, and stores ctx at +0 |
| 0x7EE61ABB | destroy |
| 0x7EE61AD5 | set source: 4 parameters at +20…+32, then 0x7EE6CB5B or 0x7EE673DE |
| 0x7EE61BE8 | load: makes the root object at +8 (0x7EE623EB tests class ids 1 and 55), parses it with 0x7EE673DE, then mode +16 = 1 → 0x7EE67B71 or 2 → 0x7EE67BB0, then 0x7EE67E93 |
| 0x7EE61CA8 | unload |
| 0x7EE61CC4 / 0x7EE61CF7 | root methods 0x7EE67BEF / 0x7EE67D4D |
| **0x7EE61D2A** | **find object by name** (a1 = a string such as `P3D_Room`; 41 callers) |
| 0x7EE61D72 | Checks the error state, then calls 0x7EE62B6A on context+4 (30 callers; the role was not resolved) |
| 0x7EE61B8E, 0x7EE61BBD, 0x7EE61D9D, 0x7EE61DD1, 0x7EE61E4A | forwarders to 0x7EE62AFF, 0x7EE62B2F, 0x7EE6D5C2, 0x7EE6D1C9/0x7EE6D452 and 0x7EE6D41D |
| 0x7EE61E35 / 0x7EE61E40 | **platform GL up/down**: 0x7EE4F157 → 0x7F0A3838 (EGL init) and 0x7EE4F169 → 0x7F0A3BA2 |

Object methods called directly by the overlay:
- 0x7EE71658 (bool argument 0/1);
- 0x7EE77325, 0x7EE77398 and 0x7EE773F3: index argument 0..15, error 3 if out of range;
- 0x7EE7CE22 and 0x7EE7CEDD;
- 0x7EE80024, 0x7EE80053 and 0x7EE8009C: they test class id 52, and its children of id 17.

**Error state (verified):** **0x7EE62AD7(set, code)** writes or reads RAM 0x606A5AD4 (259 call sites).
- The idiom is: read; if the value is 0x80000000 ("none", inferred), set the code. So the first error wins.
- Codes: **1** = allocation failed (0x7EE61A59); **2** = null argument (90 sites); **3** = index or size out of range (24 sites); **5** (12 sites) and **6** (1 site) were not resolved.

**Class system (verified):**
- **Registry** 0x7EE64322 (2,605 B): 55 calls to 0x7EE642F3(entry, ctx, d0 = vtable size, d1 = instance size, vtinit, ctor, fini). Each call allocates the class block (the vtable, d0 bytes) from the context heap and runs `vtinit` on it. Entries are 16 bytes: `{class block, instance size, ctor, fini}`.
- **Create** 0x7EE6225E(ctx, id), for **ids 1–59** with entry = id − 1:
  1. allocate the instance size (heap 0x7EE8F248);
  2. obj+8 = class block (0x7EE75ED8);
  3. ctor(obj, ctx);
  4. **obj+36 = class id** (0x7EE75E53).

  On failure it frees the object (0x7EE8F269). Ids 4, 5, 25 and 30 are unused.
- **Object layout:**

| Offset | Field |
|---|---|
| +0/+4 | header, zeroed by **0x7EE8F081** (59 callers) / 0x7EE8F089 |
| +8 | class block |
| +12 | name string (init 0x7EE7F272, set 0x7EE7F08D, get 0x7EE7F0FE) |
| +36 | class id (getter **0x7EE75DFB**, 264 callers) |
| +40 | a serialised u32, default −1 |
| +44 | context (getter 0x7EE75E4D) |

  Root init **0x7EE75D3C** (54 callers) sets these; root fini 0x7EE75D7B.
- **Vtable slots 0–3** are common to every class (verified from 48–51 vtinit fills each):

| Slot | Role | Root implementation |
|---|---|---|
| +0 | serialised size | 0x7EE75DD8 → 0x7EE75CE8: name length + 8 |
| +4 | write | 0x7EE75DE0 → 0x7EE75CF6: +40 and the name to a stream through `stream->vt[2]` |
| +8 | read | 0x7EE75DF2 → 0x7EE75D1D: the inverse |
| +12 | copy | 0x7EE75DAD: id, +40 and name; 53 callers |

  The node-type classes add `accept(visitor)` 0x7EE75C9A → the walk 0x7EE758CD (it recurses over children 0x7EE75599/0x7EE755C9).
- **Context heap** (verified): 0x7EE8F212 sets up an allocator pair. alloc **0x7EE8F248** calls `allocator->vt[0](size + 4)` and keeps a 4-byte tag; free **0x7EE8F269** calls `vt[2]`. Small helpers 0x7EE8F081–0x7EE8F4F3: memory copy 0x7EE8F3A9, string 0x7EE8F46C/0x7EE8F488, LUT user 0x7EE8F321.

**Class tree.** The ctor chains are verified (each level returns a bool; the chain stops at the first 0). The family roles are inferred. Notation: id(ctor, instance size).

- **Root R** = 0x7EE75D3C. vt16 leaf classes directly under R: id 1 (0x7EE67858, 180; the scene/file root made by the API), id 10 (0x7EE6C1CF, 64), id 42 (0x7EE6E64C, 152), id 59 (0x7EE62EF1, 88). Ids 43 and 44 (0x7EE6DF03 and 0x7EE6E9CE) share the base 0x7EE6EAC8.
- **vt28 family**, base 0x7EE7275B: ids 26, 27, 28 (0x7EE6DD39, 0x7EE72BC1, 0x7EE6510D).
- **vt108 family**, base **0x7EE74951**:
  - Under **0x7EE75A31**: ids 2 (156), 3 (424), 33 (108; the base itself), 34 (84; its ctor 0x7EE657D2 calls 0x7EE75A31 directly, with no header or root call), 35, 36, 37, **41 (0x7EE70A04, 560 B; the most-tested id, 109 sites)**, 46 (192) and 57 (192). Ids 35 and 37 also create sub-objects through 0x7EE6225E.
  - Under **0x7EE75CB9** (the node type with children; accept/visitor, inferred):
    - ids 54 and 56 directly;
    - **0x7EE761B4** → 0x7EE7798B → ids 6/38 (final 0x7EE784D4), 7 (0x7EE7881F) and 8/39 (0x7EE79061), all vt168;
    - **0x7EE761B4** → 0x7EE7825B → id 9 (vt160).
  - Under 0x7EE63B7D: ids 53 and 55.
- **vt88 family**, base **0x7EE7F639** (F073: +48 = 1 … +92 = −1); 26 classes:
  - ids 11 and 52 directly (id 52 owns children of id 17);
  - 0x7EE877A5 → ids 12, 13, 14;
  - **0x7EE8D398** → ids 15, 16, 21, 22, 23, 24, 31, 32, 49, 50, 51;
  - **0x7EE8D398** → **0x7EE873AA** → ids 17 and 40 (F074 0x7EE8E5B7);
  - **0x7EE8D398** → **0x7EE873AA** → **0x7EE879EE** → ids 18, 19, 20, 29, 45, 47, 48, 58.

  Inferred: these are the animation and track classes. The scene's `TA_*` and `Act_*` objects are the likely instances; the names come from the scene file, not from the code.

## 3. What C3D does in the camera

**The GPU slideshow** (verified chain, except where marked):
1. **GUI start, 0x7ED081AE.** It reads Effect (info 97), BGM (110), 100/288 and info 101.
   - In 3D mode (0x7ED05422 ≠ 0) it sets Slide (101) = 7 and uses the normal path.
   - Otherwise, if Effect ≠ 1 and `PlaySlideShow::canSlideShowGPU` (vt+0; 0x7E9E00D0 returns 1 when a picture-DB query of kind 6 has more than 0 images), it calls **`startSlideShowGpu`** (API vt+28). The log is `…startSlideShowGpu() = %d`.
   - Else it calls `startSlideShow()`.
   - Which Effect label is value 1 was not resolved.
2. **Hfw and component:** `OlyHfwOpePlySsh::startSlideShowGPU` 0x7E9E0593, then `CmpPSld` `slideshow_start_slide_show_gpu` 0x7EB68E2C.
3. **Slideshow controller** **`CapGSld_GpuSlideShow`** 0x7EA5584B–0x7EA56E19: `initSlide`, `makeGPUImage`, `makeRndPicList`, `gpu_slide_play/skip/idle/end`, and `APPEVENT_STATE_C3D_LOGO_END` handling.
4. **Play API** 0x7E685AA3–0x7E685F4B: `api_play_Exec_C3d_Anime_Logo` (called from `gpu_slide_play` 0x7EA56935), `_Main` (from `state_NotifyGSld_StartDone` 0x7EB678B9), `Notify_C3d_Img_Load_Finish` (photo size, aspect, date), `Skip` (0x7EA56BD8), `End` (0x7EA56E19) and `Abort`.
5. **Across cores (inferred, 08):** the C3D_BRIDGE tasks, then the C3D tasks in overlay B (C3D 0x7F0A3E60, C3D_UPDATE 0x7F0A406C, C3D_EXE_BRIDGE 0x7F09ECDC, C3D_FILE_READ 0x7F09DED5).
6. **Scene code** 0x7F09DFD4/0x7F09E31F–0x7F0A30A9. It drives a photo "room" through name lookups (`P3D_Room`, `Gr_Room_A/B/C`, `P3D_Photo_%02d`, `TA_Camera_%02d`, `TA_Bar_In/Out`, `TA_Logo_In`, `P2D_Logo`, `TA_FadeIn/Out`) and the object methods of §2.4.

Other uses:
- **Debug shell:** `c3d_dbg` 0x7F09DA0E loads `Pho%02d.bmp` (the BMP loader path).
- **Not C3D:** `play_gpu_draw` (`play_gpu.c`, 0x7E943DDE), the playback GPU resize and rotate, and the `set_effect_3d_overlap` transition. Neither calls GL or C3D (verified for GL: no caller). How they reach the GPU is an open question.
- **Other bodies:** the E-PL5 1.6, E-PL6 1.4 and E-P5 1.8 bodies have the same engine strings (`MCM_`, `$Revision: #88`, `Qualcomm`, `GIF89a`, `P3D_Room`). The E-M10 1.4 body has only `api_play_Exec_C3d_Anime_Main` (verified with `fwmap str`).

## 4. Classifying a new function in this area

1. **Address.** Locate the address in §1. Then use these signatures:
2. **GL:**
   - `fc a? 94 e9 2b 60` = `mov (0x602BE994),aN`, the current context;
   - a call to 0x7EE097DA with d0 = 0x500–0x505 (raise a GL error);
   - a 0-caller function that is a table entry, or a body that starts 5 bytes after one. Look the address up in the TSV (`entry` or `body` column).
   - Internal functions without either sign are back end (0x7EE10B33–0x7EE19609 ~~uniforms and shaders~~: shared GL state set-up plus, inferred, uniforms and shaders; §2.1) (C3 2026-11-09).
3. **Engine core:**
   - `call 0x7EE47412` (release) or `mov T,d0; call 0x7EE4736E` (alloc of type T);
   - the type-table index `f9 00 1c … fc d1 14 aa 02 7f` (`udf00 28,d0; add 0x7F02AA14,a1`);
   - globals 0x602BEC00–0x602BF3FF;
   - dense float-helper calls (0x7E5018BC–0x7E5019ED): 22 % of the core's functions, under 1 % in C3D.
   - Format checks are `cmp N,d0; bne; mov magic,a1; mov N,d0; call 0x7E500D15`.
   - A GL call means the back end 0x7EE2FF5E–0x7EE32698.
4. **C3D framework.** Measured shares of its 2,585 functions (`classify.py`):

| Pattern | Share | Signature |
|---|---|---|
| tiny accessor/stub | 21 % | `cmp 0,a0; beq; mov (N,a0),d0/a0; retf`, `clr d0; retf` |
| thunk | 15 % | ≤ 20 B, one call |
| other | 21 % | — |
| override chain | 10 % | `cf 30 f8 fe fc 97 92` (or `cf 20 …`); its first call is a root method: 0x7EE75DD8 = size, 0x7EE75DE0 = write, 0x7EE75DF2 = read, 0x7EE75DAD = copy, 0x7EE75C9A = accept. Then a chain of `14 a0 01 c9` (`extbu d0; cmp 1,d0; bne`) for each ancestor level's same method. These functions have 0 callers in the DB, because vtinit stores them as code immediates |
| leaf | 11 % | no calls |
| release/fini | 7 % | 0x7EE8F269 / 0x7EE622F9 / 0x7EE7F27B |
| serialize helper | 4 % | 0x7EE7F1CF / 0x7EE7F1FE / 0x7EE8EF9D |
| checked API | 3 % | `00 04 cd .. .. 00 00 fc c8 00 00 00 80 c9 .. 80 01 85 NN cd` = `clr d0; clr d1; call 0x7EE62AD7; cmp 0x80000000,d0; bne; mov 1,d0; mov NN,d1; call 0x7EE62AD7`; NN = error code |
| vtable fill | 2.5 % | `mov 0x7EE6xxxx..0x7EE8xxxx,d0; mov d0,(N,a2)` repeated, `mov 1,d0` |
| ctor | 2 % | `cf 30 f8 fe fc 97 92 cd/dd <0x7EE8F081>` then `R 0x7EE75D3C` and level inits |

   - **vtinit** (`A`): `cf 20 f8 fe fc 92 dd <0x7EE75DA2>` (root vtinit = `mov 1,d0; retf`), then the ancestors' vtinits, then the own fills.
   - **fini** (`C`): `f8 fe fc cd <level fini> … 14 df 00 04`.
   - A class's functions sit next to its registered ctor, fini and vtinit (§2.4 tree). Name the function by its slot or level.
5. **Overlay port** (0x7F0A33D9–0x7F0A3D07; allocator wrappers 0x7F0A33D9/0x7F0A33E8/0x7F0A3436):
   - malloc **0x7F0A3804**(d0), 64-byte aligned (140 callers);
   - realloc 0x7F0A380E (copies min(old, new));
   - **free 0x7F0A3819**(a0) (193 callers);
   - display size 0x7F0A3824 (returns 1280 × 720);
   - EGL functions as in §2.1.

## 5. Corrections

1. **Regions table rows 0x7ECA1020–0x7EE21020 and 0x7EE21020–0x7EEE1020.**
   - GL is 0x7EE02095–0x7EE294B4 (agrees with C2).
   - The "C3D engine from ~0x7EE294B5" is the **engine core 0x7EE294B5–0x7EE5B5BB** plus its image decoders 0x7EE5B5BC–0x7EE5D00C.
   - libpng is **0x7EE5D00D–0x7EE5F5F2** and zlib is 0x7EE5F5F3–0x7EE619C6.
   - The **C3D framework is one module, 0x7EE619C7–0x7EE8F4F3**. "C3D API 0x7EE619C7–0x7EE63004" is wrong: the overlay-called API is 0x7EE619C7–0x7EE61E54, and class code starts by 0x7EE62C10 (id 59).
2. **Regions table row 0x7F021020–0x7F034000; 13b §1 "What 0x7F021020–0x7F034000 holds".**
   - 0x7F021020–0x7F0229AF is not GL. It is the tail of an unreferenced table that starts at 0x7F01F7F4.
   - GL rodata is 0x7F0229D0–~0x7F027BFF. The engine has 0x7F027C00–0x7F02B24A (with the type table 0x7F02AA14).
   - libpng/zlib run to 0x7F02EB67. **C3D rodata is 0x7F02EB68–0x7F02F683.**
   - **AVPI rodata starts at 0x7F02F684, not 0x7F02F600.**
3. **The `{name, fn}` table** (firmware-map, 13d §1 row, the C2 notes). It starts at **0x7F023B8C**, not 0x7F023C74. It has 223 slots: 29 EGL slots come first, and `glDeleteQueriesDMP` is listed twice. That gives 194 `gl*` slots but 193 unique names. The 89 entries at or above 0x7EE21020 agree with C2; review 4's "91" is wrong.
4. **13d §1 row "its only callers are C3D (0x7EE2–0x7EE3)".** The callers are the engine's GL back end **0x7EE2FF5E–0x7EE32698** and the overlay port and scene functions listed in §2.1. That covers 08 open question 9 too: the GUI never calls GL.
5. **08 §1 item 8** ("GL driver at about 0x7EE15060"). 0x7EE15060 is only the uniform-table builder; the library is 0x7EE02095–0x7EE294B4.
6. **08 §4 "Engine code".**
   - "0x7EE21020–0x7EE5B" → 0x7EE294B5–0x7EE5B5BB.
   - "89 functions call the C3D helper 0x7F0A3819" → 0x7F0A3819 is the C3D port's **free()** (193 callers); 0x7F0A3804 is malloc.
   - "vtable-like pointers at 0x7F027C80" → part of the **format-loader table 0x7F027C4C** (MB, MT, BMP, MCM/MCA/MCT/MCE, GIF, PNG).
   - The "151 incoming calls into 0x7EE61020–0x7EE81020" could not be reproduced. The overlay calls 25 distinct C3D targets (16 API entries plus 9 object methods, §2.4).
7. **08 §5 table.** Replace the rows 0x7EE21020–0x7EE5B, 0x7EE5BB–0x7EE5F and 0x7EE61C–0x7EE63 with the rows of §1. The first row's "~0x7EDE–0x7EE21" → 0x7EE02095–0x7EE294B4.
8. **13b §1, the AVPI row.** "Everything from 0x7EE63000 to 0x7EE8F4F3 has callers only in the C3D API (functions 0x7EE61A0A–0x7EE62F80) and the overlay-B C3D bridges (0x7F09E31F–0x7F0A30A9)" (full sentence; the outside callers are 49 C3D-API and 15 overlay-B functions) (A6 2026-11-09). This is true in substance, but that code is the C3D class system itself, from 0x7EE619C7. Its outside callers are only overlay-B functions (verified with `pages.py`).
9. **08 §4 "What it is" and "Tasks".** These are correct, but the feature should be named: **the playback GPU slideshow** (§3), selected by Effect ≠ 1 when the slideshow is not 3D.

## 6. Open questions

1. The vendor and product of the engine core and of the C3D framework. No strings survive. "MB"/"MT" fit Mascot Capsule (external); MCM/MCA/MCT/MCE are unknown.
2. The names of the 55 C3D classes, and the engine types 3–27. They could come from a scene file, which is not in block 0 (asset source: `RES_MODE_C3D` or the card `D` file; blocks 2/3 not checked).
3. Which slideshow Effect label is value 1 (the non-GPU path), and what info 100/288 mean in 0x7ED081AE.
4. C3D error codes 5 and 6. The roles of API 0x7EE61D72 and of the second registry table 0x7EE64272.
5. Why the ctor of id 34 (0x7EE657D2) skips the header and root init.
6. How `play_gpu.c` and the 3D-overlap effect reach the GPU without GL.
7. The owner of the 12-byte table 0x7F01F7F4–0x7F0229AF and of the small table 0x7F0229B0–0x7F0229CF.
