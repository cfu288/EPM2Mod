# Audit A6 batch 1

## 14a-15 (sections/14a-c3d-graphics.md, line 15)

| **0x7EE02095–0x7EE294B4** | **DMP EGL/GL library** (OpenGL ES 1.1 + OES + DMP extensions) | 672 | verified. The previous function 0x7EE01FF5 is GUI code (it reads info 109/279/44; 10 data words 0x7F011710…). 0x7EE02095 is the library init, called only from the overlay port 0x7F0A3838. The last function 0x7EE2946D is the body of `glPointSize` and ends at 0x7EE294B4. All 1,055 loads of the GL context pointer 0x602BE994 lie in 0x7EE026DC–0x7EE2946F |

## 14a-16 (sections/14a-c3d-graphics.md, line 16)

| **0x7EE294B5–0x7EE5B5BB** | **3D engine core** (file loaders, GL render backend, 28-type ref-counted object runtime, maths) | ~950 | verified layer edges (§2.2). Its object release 0x7EE47412 and type table 0x7F02AA14 are used only here (and by 20 C3D call sites) |

## 14a-18 (sections/14a-c3d-graphics.md, line 18)

| **0x7EE5D00D–0x7EE5F5F2** | **libpng 1.2.37** (read side) | 80 | verified. 0x7EE5D00D uses the `read_data_fn`/`write_data_fn` string. 0x7EE5F5AB (memcmp-like) and 0x7EE5F5EC (getter of +308) are called only by libpng or PNG glue |

## 14a-19 (sections/14a-c3d-graphics.md, line 19)

| **0x7EE5F5F3–0x7EE619C6** | **zlib 1.2.3** (crc32 0x7EE5F5F3 → table 0x7F02BE7C; inflate 0x7EE5FE61; `zmemcpy` 0x7EE619AC; stubs 0x7EE619BF/0x7EE619C4) | 14 | verified. crc32 starts with `buf == NULL → 0` and the `endian = 1` test |

## 14a-219 (sections/14a-c3d-graphics.md, line 219)

- **Context heap** (verified): 0x7EE8F212 sets up an allocator pair. alloc **0x7EE8F248** calls `allocator->vt[0](size + 4)` and keeps a 4-byte tag; free **0x7EE8F269** calls `vt[2]`. Small helpers 0x7EE8F081–0x7EE8F4F3: memory copy 0x7EE8F3A9, string 0x7EE8F46C/0x7EE8F488, LUT user 0x7EE8F321.

## 14a-257 (sections/14a-c3d-graphics.md, line 257)

- **Not C3D:** `play_gpu_draw` (`play_gpu.c`, 0x7E943DDE), the playback GPU resize and rotate, and the `set_effect_3d_overlap` transition. Neither calls GL or C3D (verified for GL: no caller). How they reach the GPU is an open question.

## 14a-321 (sections/14a-c3d-graphics.md, line 321)

8. **13b §1, the AVPI row.** "0x7EE63000 to 0x7EE8F4F3 … callers only in the C3D API (0x7EE61A–0x7EE62F)". This is true in substance, but that code is the C3D class system itself, from 0x7EE619C7. Its outside callers are only overlay-B functions (verified with `pages.py`).

## 14b-12 (sections/14b-unlabelled-platform-camera.md, line 12)

2. **Camera error codes carry a module byte (V).** cam_damage codes are 0x0A_MM_xxxx. MM groups by address range: 0x10 cam.c (0x7E628161–0x7E628CD5), 0x18 aperture, 0x03 contrast, 0x26 cam shell, 0x2A debug monitor, **0x15 0x7E6369CA only**, **0x12 0x7E636A04–0x7E63B766** (frame + frame_sync), 0x17 imgdev, 0x25 CAMLNS, **0x28 0x7E640F3E**, **0x16 0x7E641C2E–0x7E642097**, **0x1E MI 0x7E642325**, 0x1B SPRDRV, 0x27 cam_sem, 0x1A shutter 0x7E6557CE, 0x13 still/live bulb, 0x24 cam_timer. The ids are per subsystem, not strictly per file (0x12 covers frame and frame_sync).

## 14b-21 (sections/14b-unlabelled-platform-camera.md, line 21)

| 0x7E508DA7–0x7E508F81 | UI side: beep request layer 0x7E508DA7–0x7E508EAE (callers UI_OUT 0x7E50D7CD/0x7E50D88B/0x7E50D93A), `ui` shell `beep` 0x7E508EDA and `help` 0x7E508F14 (table 0x7E734DEC: led 0x7E50D6F0, beep, key 0x7E50AD9C, jog 0x7E50996C, remo 0x7E50917F, help) | V |

## 14b-32 (sections/14b-unlabelled-platform-camera.md, line 32)

| 0x7E642325–0x7E6437F1+ | cam_mirror.c (`MI_*`; id 0x1E) | V |

## 14b-50 (sections/14b-unlabelled-platform-camera.md, line 50)

- **Pattern (V):** each wrapper is 14 bytes, `mov imm32,a0` (alloc) or `a1` (free), then `call 0x7E507395` (alloc) or `0x7E5073B8` (free) and `ret [],4`. Both lock with 0x7E436593 and 0x7E431316/0x7E4313FE and call the pool function by pointer.

## 14b-144 (sections/14b-unlabelled-platform-camera.md, line 144)

- **cam_list.c 0x7E640858–0x7E640F52 (V):** list library. Create 0x7E640858 (← cam.c init 0x7E628161, frame-sync 0x7E63A0EE); push/pop/peek 0x7E640961, 0x7E6409B7, 0x7E640A0D, 0x7E640A51, 0x7E640A79, 0x7E640B0B … (← cam.c packet lists, frame sync); error helper 0x7E640F3E (id 0x28).

## 14b-151 (sections/14b-unlabelled-platform-camera.md, line 151)

- **cam_mem.c 0x7E641BB8–0x7E642324 (V):**

## 14b-177 (sections/14b-unlabelled-platform-camera.md, line 177)

| **MEC command layer** (MAG_COM / MOT_COM), 0x7E517791–0x7E518BBA (V) | Init 0x7E517791 creates the locks `ANY_USE`/`MAG_COM`/`MOT_COM` (0x7E516C32). Open/close 0x7E51783A/0x7E51785A are ref-counted: the first open → MEC timing unit 0x7E50F8F3, the last close → 0x7E50F96F. **Submit 0x7E51787B(a0 req)**: code = u16 +0, class = byte +9 (0 MOT, 2 PWR, else MAG); jump table 0x7E7379C0; a bad code → 0x1500A001. Names from the printer 0x7E51256F: **MOT** 0 ON, 1 OFF, 2 OPENRDY, 3 OPENCHG, 4 CLOSCHG, 5 INTIAL, 7 F_READY, 8 F_OPCHG, 9 N_READY, 16 ABORT; **MAG** 10 ON, 11 OFF, 12 SET, 13 START (NML/DRK, TV, TIME), 14 STOP, 15 MG3_CHG; **PWR** 17 ON, 18 OFF. Handlers 0x7E517952 … 0x7E518ABE in that order. Each builds a driver request with "done" and "event" callbacks (e.g. MAG START 0x7E518664 → 0x7E518684, callbacks **0x7E5186EA = F006** and 0x7E518731). The done callback releases the lock by name (0x7E516D50) and calls the client's +16. `Shutter Client [0x%02x]` 0x7E518BBA ← `mec` monitor 0x7E510C3A. The `mec` shell has `mec shutter set [expose_time us]`, `mec still [num] [time]`, `mec lsnc …` (0x7E510943). Reading (I): MAG = curtain-hold magnets, MOT = charge motor |

