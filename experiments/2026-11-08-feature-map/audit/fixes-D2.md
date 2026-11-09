# Fix pass D2 (2026-11-09)

Sources: the "Corrections" sections of the round-D2 deep dives `sections/14a-c3d-graphics.md` §5, `14b-unlabelled-platform-camera.md` §8, `14c-app-protocols.md` §4 (+ §1.1, §3), `14d-data-and-blobs.md` §6 and `14e-gui-methods.md` §6, plus the coordinator's brief (firmware-map regions, boundaries and feature rows; modules.tsv).

Method. Before each edit I re-checked the claim in block 0 of v1.6 (runtime = 0x7E421020 + offset) with `fwmap.py fn/range/str/xref`, `disasm.py`, `build/map/calls.tsv`, `functions.tsv`/`functions.txt` and raw byte/word reads (Python `-I`). Scripts and the pre-edit backups are in `/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/fixD2/` (`rd.py` reader, `edits1.py` 01–06/13a/13b/13c/13f, `edits2.py` 07/08/10f/13d, `edits3.py` firmware-map; `backup-*`). Every changed place carries "(D2 2026-11-09)". Superseded text is struck through (`~~…~~`), not deleted. I edited only sections 01, 02, 03, 05, 06, 07, 08, 10f, 13a, 13b, 13c, 13d, 13f, `docs/firmware-map.md` and `modules.tsv`. No 14* file, no coverage file, no git, no build.

**Counts.**
- **Applied:** 80 logged corrections in the sections and the map (§1.1–§1.7), made as 95 text edits (sections 69, firmware-map 26), and 35 modules.tsv changes (22 `first_fn` moves, 13 new rows; §1.8).
- **Rejected:** 2 (§2).
- **Not applied, no target in scope or already present:** 9 (§3).
- **Contradictions found:** 1 between two D2 sections, 6 inside one D2 section or against the bytes (§4).

## 1. Applied

### 1.1 Section 03 (14b, 14d)

| location | old | new | check done |
|---|---|---|---|
| 03 §2 item "Inferred, disputed (C2)" | "the mirror code is a stub left over from Olympus DSLR code" (disputed) | struck; **resolved: not a stub**, MI is the shutter-charge motor client (MOT ON/OFF/INTIAL/OPENRDY/OPENCHG/F_READY/F_OPCHG/N_READY/code 6); `MIRROR_DOWN*` = charge/close before exposure (I) | `fwmap fn 0x7E6433B0 --dis`: MI init (caller MI open 0x7E642398) writes u16 codes 0,1,5,2,(d2),…,7,8,9,6 into the requests at MI+48…+88; MEC printer 0x7E51256F loads `OPENRDY` 0x7E736C85 / `OPENCHG` 0x7E736C8D (coordinator check confirmed); calls.tsv: 10+ MI functions 0x7E642502…0x7E642BF1 call the MEC submit 0x7E51787B; MI command table 0x7E7B18B8 = {0,…,1,…,2,…,0x91,…,0x92,…,5,…,6,…,0x93,…} |
| 03 §3 module table, row "mirror (MI_*)" | "dummy mirror (inferred; disputed)" | struck; "shutter-charge motor client: MOT_* requests" | as above |
| 03 §3 module table, row cam_ev.c | start only | + "ends at 0x7E635F4A" | `fwmap range`: 0x7E635F14 (cam_ev.c string) is the last fn before 0x7E635F4B |
| 03 §3 module table, new row | — | cam_expcal.c 0x7E635F4B–0x7E636A03 (init 0x7E635F4B, build 0x7E635FB5, error byte 0x15) | 0x7E6369CA loads 0x0A150001 (169156609); 5 callers 0x7E635FB5…0x7E6368A8; next fn 0x7E636A04 |
| 03 §3 module table, row cam_frame.c | 0x7E63790D | + "starts at its init 0x7E636A04 (error byte 0x12); 0x7E636AAB = frame-command dispatcher" | 0x7E636A04 loads 0x0A122018/0x0A122010; 0x7E636AAB has 33 callees |
| 03 §3 module table, new row | — | cam_lens.c (CAMLNS 0x7E640200) / cam_list.c 0x7E640858–0x7E640F52 / cam_mec_ctrl.c 0x7E640F53–0x7E641BB7 / cam_mem.c 0x7E641BB8–0x7E642324 | `fwmap fn`: 0x7E640200 loads `CAMLNS`; 0x7E640F3E has 12 list callers; 0x7E641BA1 is called by the 14 done handlers 0x7E64173B…; 0x7E642301 called by 0x7E642035; 0x7E642325 = MI_RES creator |
| 03 §7b SDET | scene names only | + scene ids 3/8/9/11/12/17/18/21/23/50/156/157, decision 0x7E663EC4, F017 rule | `fwmap fn 0x7E6637F2 --dis`: each `mov N,d0` before 0x7E50658F matches the string (e.g. 156 with `NIGHT_SHOT_MACRO` 0x7E7BFB3E) |
| 03 §7b IMG_PRECON | "Overstated (C2) … a D2 deep dive is checking it" | **resolved**: cmd 0 defect correction; cmds 1–4 WB/colour calibration; cmd 4 reads `PRM_CAM_SPECTRUM_STL_R/G/B` | `fwmap fn 0x7E55FE1E/0x7E55FF91/0x7E55FFA3`: callees 0x7E579DCF/0x7E579DE1, 0x7E581268, 0x7E57A140 (all in WB 0x7E579C34–0x7E581FAF); 0x7E580A54 loads table 0x7E78F170 whose rows are {0xAA92, 0xAAA2, 0xAAB2, illuminant, out}; 07-settings.tsv: 0xAA92/0xAAA2/0xAAB2 = `PRM_CAM_SPECTRUM_STL_R/G/B`; string `PRM_CAM_SPECTRUM_%s_R` 0x7F0DEBA8 |
| 03 scope line | rec/FACE/art only | + mcon 0x7E6FCA60–0x7E70787F, Exif writer 0x7E707880–0x7E70B434, OKAO PT, camera-core rodata 0x7E7AB000–0x7E7C10FF (14d) | `fwmap range`: fns 0x7E707880 and 0x7E70B435 exist; mcon row of 13e |
| 03 §8 ORF item | header builder only | + the ORF header path copies the CMIO blob through 0x7E5586B9 (14d) | 0x7E5586B9: `mov 0x7E86DD80,a1`, one caller 0x7E71969F (`REC ORF header`), callee 0x7E544BB5 |

### 1.2 Sections 01, 02, 13a, 13f (14b)

| location | old | new | check done |
|---|---|---|---|
| 01 §4 SC_TTIMER row | "soft timers, together with the scheap allocator" [I] | [V] dispatcher (25-tick loop, slots 1–31, register/unregister); scheap is a separate part of `sc` 0x7E506CB0–0x7E508DA6; SCHEAPDBG = its guard checker | 0x7E507115 `mov 25,d0`; 0x7E506FF6 `cmp 31,d3; bls` else 0xFFFF; strings `ttmr_*` used by 0x7E506FF6/0x7E50708F/0x7E507115; `SCHEAPDBG` used by Usr0 |
| 02 §1 row "Shooting control" | 0x7E58204D–0x7E59A3EC | + TAKE starts at its init 0x7E581FB0 | `fwmap fn 0x7E581FB0`: one caller 0x7E503DD4, callees 0x7E58287B, 0x7E587D08, 0x7E59A23C, 0x7E5A0863 … |
| 02 §1 row "No strings" | "WB_MOV not mapped"; IMG_PRECON disputed | struck; WB_MOV = task of the WB module 0x7E579C34–0x7E581FAF; IMG_PRECON resolved | 0x7E57F914: 0 callers, data word 0x7E439708 (task table); callees 0x7E57FD8F/0x7E57FE37/0x7E5808EB; PRECON as in 1.1 |
| 02 open question 7 | reopened in part | answered (WB/colour; WB_MOV in WB module) | as above |
| 13a §1 row `buff` | ~0x7E576D59–0x7E579A7F | –0x7E579C33 (7 pool methods 0x7E579AB7–0x7E579C17, vtable 0x7E78EEBC) | vtable 0x7E78EEBC mixes 0x7E5797D8…0x7E5797F5 (buff) and 0x7E579AB7/0x7E579ADE/0x7E579B45/0x7E579B8A/0x7E579BB1/0x7E579BFC/0x7E579C17 |
| 13a §5 item 1 (buff) | 0x7E579A7F | 0x7E579C33 | same |
| 13a §1 row 0x7E579C34 | "TAKE / WB_MOV code" | WB module 0x7E579C34–0x7E581FAF; TAKE from 0x7E581FB0 | `fwmap range 0x7E581E00 0x7E582000`: last WB fn 0x7E581F9E (18 B) ends 0x7E581FAF |
| 13a §3.2 IMG_PRECON row | "Disputed, overstated (C2) … D2 deep dive" | resolved | as 1.1 |
| 13a §5 item 3 | disputed until D2 | resolved | as 1.1 |
| 13a open question 6 | IMG_PRECON cmds 1–4 | answered; still open: UI path to cmds 1/2 | as 1.1 |
| 13f §1 driver list | UI/keys 0x7E508F82–0x7E50D6F0 | 0x7E508DA7– (beep layer 0x7E508DA7–0x7E508EAE, `ui` beep 0x7E508EDA, help 0x7E508F14); + `sc` library line | `fwmap range 0x7E508DA7 0x7E508F90`; 0x7E508DA7 caller UI_OUT 0x7E50D7CD; table 0x7E734DEC = led 0x7E50D6F0, beep 0x7E508EDA, key, jog, remo, help 0x7E508F14 |
| 13f §1 driver list | MEC unit and `mec` shell | + MEC command layer 0x7E517791–0x7E518BBA; + one line of 14b §6 entry points (EMS, IOE callbacks, DCF scanner, exFAT formatter) | 0x7E517791 loads `MOT_COM`/`MAG_COM`/`ANY_USE`, caller Usr0; 0x7E51787B 46 callers, 21 handler callees; 0x7E463DB8 loads 0x7E464177/0x7E4641A5; 0x7E5AF95D 6 callers (0x7E5AFE23…0x7E5BED03); 0x7E5B9DD7 → 0x7E5BA1FE, 0x7E5BA317 |

### 1.3 Sections 06 and 13c (14c)

| location | old | new | check done |
|---|---|---|---|
| 06 §1 item 2 "Cap* wrap devices" | right but incomplete | + callers hold the interface at facade+K (getInstance ends with `add K,a0; retf`; CapTak +1700) | 0x7EA32D19 → 0x7EA32FE3 = `fa d0 a4 06` (`add 1700,a0`), `retf` |
| 06 §2 row Cmp_ComponentManager | code 0x7EA7CB15–0x7EA7DBAC | 0x7EA7C89C (ctor) – 0x7EA7E66A | `fwmap fn 0x7EA7C89C` (387 B, 21 data words); 0x7EA7E620 (75 B) ends 0x7EA7E66A; 0x7EA7E66B = Cmp_OutlineController ctor (13c §5) |
| 06 §3 row MF assist | "≤0x7EB7D14B … at or before its ctor" | starts at the ctor 0x7EB7D14B; no getInstance (member of facade 0x7EB7A703) | 0x7EB7D14B: one caller 0x7EB7A703, calls 0x7EBA675E; the previous modules.tsv row ends 0x7EB75808 |
| 13c §1 row Dev part 1 | 0x7EB8C265–~0x7EB93422 | –0x7EB93422 (end verified) | `fwmap range`: 0x7EB93417 (12 B) ends 0x7EB93422; 0x7EB93423 = 59-B getInstance |
| 13c §1 row Categories | ~0x7EB93423– | 0x7EB93423– | same |
| 13c §3 class hierarchy | "CmpSts controllers use `Com_ManagersSubTransition` 0x7EB8573D (15)" | struck in part: 15 callers, 8 CmpSts; general helper; observers 0x7EB85DC3/0x7EB86084 make 3346/3344 | `fwmap fn 0x7EB8573D`: 15 callers incl. CmpCst 0x7EA9D405/0x7EA9F812/0x7EAAA4AF, Outline 0x7EA7E66B, 0x7EB8AD37; updates 0x7EB85DDF → ctor 0x7E9EB1AF (id 3346), 0x7EB860A0 → 0x7E9EB15F (id 3344) per 13c-event-ids.tsv |
| 13c §4 key-id table | no row | + 11776/11777 subscribe, **11779/11780 unsubscribe** | `fwmap fn 0x7E999883 --dis`: 11776/11777 → 0x7E999CA4 (calls new 0x7EBA62DB, topic ctor 0x7E9E5384); 11779/11780 → 0x7E999EC6 (find 0x7E999C10, remove 0x7E9E56C1, count 0x7E9E5527 = 0 → drop topic 0x7E999FB1) |
| 13c open question 3 | three OMThreads unknown | answered: HLS_CALLBACK / HLS_EVENT / HLS_USER | `fwmap fn 0x7E96CA56/0x7E96DB78/0x7E9E762F`: strings `HLS_CALLBACK`/`HLS_EVENT`/`HLS_USER`, all call 0x7EBA708D |
| modules.tsv, 21 rows (+ 06 for the 22nd, Cmp_ComponentManagerWithBoot) | first_fn = first function naming the file | first_fn = getInstance or ctor (§1.6) | each new start is a 59-byte getInstance (new 0x7EBA62DB + ctor) or a ctor calling 0x7EBA675E; for all 21, the previous row's last_fn < new start < old first_fn and no other row lies between; spot checks: CmpPEvc 0x7EB2037C…0x7EB2511F holds only `chls_evcollection_*` strings and the `CmpPEvc_PlayEvcollectionComponent` getName; CmpCst_Function ctor 0x7EA9F812 follows `CmpCst_Communication` |

### 1.4 Sections 05, 06, 08, 13b, 13d and firmware-map (14d)

| location | old | new | check done |
|---|---|---|---|
| 05 §0 row 0x7E8E1020–0x7E8F57FF | "method-name pointers, pointer tables, 0xFF from 0x7E8F3298" | + it is the 2nd part of the `.data` image 0x7E8DA000–0x7E8F3113 (→ RAM 0x602A9B40); 0xFF starts at 0x7E8F3114 | reset code 0x7E4212B8–0x7E4212E0: `mov 0x7E8DA000,d0`, `mov 0x7E8F3114,d0`, `mov 0x602A9B40,d2`, `sub`, `call 0x7E425FA8`; bytes 0x7E8F3114–0x7E8F57FF all 0xFF |
| 05 open question 8 | block unknown | answered (`.data` image, then 0xFF) | same |
| 06 open question 8 | name table "another section's scope" | + it is in the `.data` image, RAM copy 0x602B0EF0+ | 0x7E8E13B0 − 0x1E6304C0 = 0x602B0EF0 |
| 08 §2 TOUCHPANEL | "touch-controller firmware bootloader" (strings) | + TTSP-style host (I), 470 records over SIO ch2 to 0x24, runs only for `disp tp boot_on` (V); image same in E-PM2 1.1–1.6, E-PL5 1.6, E-PL6 1.4 | `fwmap fn 0x7E6BD8B6`: one caller site 0x7E6B2BC1 in `tp` handler 0x7E6B27C4, which loads `boot_on` 0x7E7E430B; `.data` table 0x7E8DD1B8 entry `tp` → 0x7E6B27C4; U_SHELL words 0x7E7327F0/0x7E733400 → `disp` 0x7E6B1402; 470 headers `00 FF 39 00` found; byte search of the 39,950-B image: present in 100_1600, 101_1101…1501, 112_1400; absent in 108, 113, 115, 118, 122 |
| 13b §1 OKAO PT row | models to ~0x7E86DCxx (end inferred) | to **0x7E86DD5F** (atan LUT end), 0xFF to 0x7E86DD7F, CMIO blob 0x7E86DD80–0x7E8808BF | bytes: 0x7E86DD5F = 0xC9, 0x7E86DD60–7F = 0xFF, 0x7E86DD80 = `CMIO 01 00 09 DC`; 0x7E7311AD `mov 0x7E86DC5F,a2` (reader 0x7E7310FE) |
| 13b §2.1 row 0x7E731288 / 0x7E731394 | 0x7E731288 a function | 0x7E73121F / 0x7E731394; 0x7E731288 is inside 0x7E73121F | `disasm 0x7E73125A`: `jmp 0x7E731356` at 0x7E731262; 0x7E731288 `86` (`mov d1,d2`) is mid-loop; functions.tsv: suspect = 1, only caller 0x7E738083 |
| 13b §2.1 row 0x7E731532 | — | + ends at 0x7E731584; DB size 2,766 wrong | bytes 0x7E731582 = `df f0 24` (`ret`), then FF FF FF, `_ctype` at 0x7E731588 |
| 13b §1 Smart Skin row | LUTs to 0x7ECAFF3C | to 0x7ECB083B (14d §3.5) | 0x7ECB083C starts the 19-word constructor table (walker id 2) |
| 13b §2.4 plug-in registry | 0x7E8EFA18 only | + RAM copy **0x602BF558** | 0x7E8EFA18 − 0x1E6304C0 = 0x602BF558; `add 0x602BF558,d0` at 0x7EE99822/0x7EE99841/0x7EE99860 (7 sites) |
| 13b open question 4 | registry reach unknown | answered (0x602BF558) | same |
| 13d §1 first row | 13b gives LUTs to 0x7ECAFF3C, "covers most"; ctor table inferred | LUTs to 0x7ECB083B cover all; the table is the segment-2 constructor table walked by 0x7E44B6B0(2) | walker 0x7E44B6B0: id 2 → `mov 0x7ECB083C,a2`, `mov 76,d2`, `calls (a0)` loop |
| 13d §1 CA_MAIN row | "code restarts at 0x7ECCB800" | + 0x7ECCB800 is the first GUI function `[OSD_CONTROL]` (segment-3 code) | bytes 0x7ECB0888–0x7ECCB7FF are 0xFF except `de 00 00` at 0x7ECB1000; 0x7ECCB800 = `dd 41 bb 83 ff 00 04` (`call`) |
| firmware-map §1 regions rows 0x7E730000–0x7E8E0000, 0x7E8E1020–0x7E8F5800, 0x7EBA1020–0x7ECA0000, 0x7ECA1020–0x7EE21020 | "mostly read-only data … code 0x7E8808C0–0x7E880E84"; "Data (method-name pointer tables, padding)"; "data from about 0x7EBAC000"; "0x7ECA1020–~0x7ECC8000 data, ~0x7ECC8000– GUI" | segment-1 rodata 0x7E731588–0x7E8808BF; CMIO blob; code block 0x7E8808C0–0x7E880F43; ctor table 0x7E880F44; 0xFF; `.data` image 0x7E8DA000–0x7E8F3113 → RAM 0x602A9B40; segment-2 rodata 0x7EBABF90–0x7ECB083B; ctor table 0x7ECB083C–0x7ECB0887; 0xFF to 0x7ECCB7FF; **GUI 0x7ECCB800–0x7EE02094** | walker constants: id 1 0x7E880F44/24 B, id 2 0x7ECB083C/76 B, id 3 0x7F033AC8/180 B, id 4 0x7F06ADC4/0, id 5 0x7F0EB484/0; reset-code constants above; 0x7E8808B0–BF high-entropy bytes then code at 0x7E8808C0 |
| firmware-map §1 regions row 0x7F021020–0x7F034000 | + segment-3 ctor table | 0x7F033AC8–0x7F033B7B (45 pointers) | walker id 3 |
| firmware-map §1 Overlays bullet | Usr1 copies only | + `.data` copy by the reset code and the per-segment constructor walker | as above |
| firmware-map D2 boundary list (new) | — | load segments, `.data` image, 3D stack, GUI start, CMIO blob | as above and §1.5 |

### 1.5 Sections 08, 13b, 13d and firmware-map (14a)

| location | old | new | check done |
|---|---|---|---|
| 08 overview item 8 | "GL driver at about 0x7EE15060" | 0x7EE15060 is only the uniform-table builder; library 0x7EE02095–0x7EE294B4 | `fwmap fn 0x7EE15060` (717 B, 27 strings); 0x7EE2946D (72 B) ends 0x7EE294B4 |
| 08 §4 "What it is" | 3D animation service | + named: the playback GPU slideshow (Effect ≠ 1, not 3D; CapGSld) | strings `PlaySlideShow::canSlideShowGPU`/`startSlideShowGPU` (0x7EBD909A/0x7EBD90B9); 14c §2.7 CapGSld strings |
| 08 §4 "Engine code" | ~0x7EE294B5–0x7EE5B (inferred) | 0x7EE294B5–0x7EE5B5BB + decoders 0x7EE5B5BC–0x7EE5D00C | `fwmap range`: 0x7EE5B56B (81 B) ends 0x7EE5B5BB; format-loader table 0x7F027C4C = {2,0x7EE332C3,…; 2,0x7EE5B5BC,0x7EE32BE3; 4,0x7EE294B5,…; 6,0x7EE5BB2C,…; 8,0x7EE5C962,0x7EE3306E; 0,0} |
| 08 §4 "89 functions call 0x7F0A3819" | C3D helper | free() (193 callers); 0x7F0A3804 = malloc | `fwmap fn 0x7F0A3819`: 193 callers; 0x7F0A3804: 140 callers |
| 08 §4 "vtable-like pointers at 0x7F027C80" | vtable-like | part of the format-loader table 0x7F027C4C–0x7F027CBF | words above |
| 08 §4 "151 incoming calls" | 151 calls | not reproduced: 25 distinct targets (16 API + 9 methods) | calls.tsv: overlay callers → 0x7EE61A4F…0x7EE61E4A (16) and 0x7EE71658, 0x7EE77325/398/3F3, 0x7EE7CE22/EDD, 0x7EE80024/53/9C (9); no caller in 0x7EE8F4F4–0x7EFFFFFF or below 0x7EE619C7 |
| 08 §5 table rows GL, engine, libpng, C3D API | ~0x7EDE–0x7EE29; ~0x7EE294B5–0x7EE5B; 0x7EE5BB–0x7EE5F; 0x7EE619C7–0x7EE63004 | 0x7EE02095–0x7EE294B4; engine core 0x7EE294B5–0x7EE5B5BB; new decoder row; libpng 0x7EE5D00D–0x7EE5F5F2; C3D framework 0x7EE619C7–0x7EE8F4F3 | `fwmap fn 0x7EE5D00D` (first libpng fn, 2 strings), 0x7EE5F5F3 (crc32, 14 callers), 0x7EE619C7, 0x7EE62C10 |
| 08 §5 GL row, `{name, fn}` table | 0x7F023C74, 194 `gl*` | 0x7F023B8C, 223 slots (29 egl + 194 gl) | word walk from 0x7F023B8C: 223 pairs, terminator {0x7F023B89 = "", 0} at 0x7F024284; first name `eglGetError`; 29 `egl*`, 194 `gl*`, 193 unique; 0x7F023C74 = `glActiveTexture` (first gl slot) |
| 08 open question 9 | does the GUI render through GL? | answered in part: the GUI never calls GL | callers of GL are only engine back end and overlay (14a, calls.tsv) |
| 13d §1 GL row | callers "C3D (0x7EE2–0x7EE3)"; table 0x7F023C74 (194) | engine GL back end 0x7EE2FF5E–0x7EE32698; table 0x7F023B8C (223) | same |
| 13b §1 AVPI row | AVPI rodata from 0x7F02F600; "C3D API … one library" | 0x7F02F684; the library is the C3D framework 0x7EE619C7–0x7EE8F4F3, outside callers only overlay B | words 0x7F02F670–0x7F02F680 are small constants, 0x7F02F684 = 0x7EE8FFC8 (AVPI OSAL), then 0x7EE8FFD1… |
| 13b §1 "What 0x7F021020–0x7F034000 holds" | GL pools, libpng/zlib, AVPI from 0x7F02F600 | + unreferenced table tail 0x7F021020–0x7F0229AF, GL rodata 0x7F0229D0–, engine 0x7F027C00–0x7F02B24A, libpng/zlib to 0x7F02EB67, C3D rodata 0x7F02EB68–0x7F02F683, AVPI 0x7F02F684 | 1,061 rows × 12 B from 0x7F01F7F4 to 0x7F0229AF, all `{id, 0 or 3, 0}`; `silhrender…` text at 0x7F0229D0 region |
| firmware-map regions rows 0x7EE21020–0x7EEE1020, 0x7F021020–0x7F034000; D1 boundary bullets GL, zlib/C3D, AVPI, 0x7F02 | "C3D engine from ~0x7EE294B5; C3D API 0x7EE619C7–0x7EE63004"; 0x7F02F600; table 0x7F023C74 (194) | layered 3D stack; C3D framework one module; AVPI rodata 0x7F02F684; table 0x7F023B8C (223) | as above |

### 1.6 Section 13d, 07, 10f and firmware-map (14e)

| location | old | new | check done |
|---|---|---|---|
| 13d §1 rows "0x7ECEE1D5–0x7ED00000" / "0x7ED00000–0x7ED17000" | CCommon from 0x7ED00000 | drawing engine 0x7ECF6BDB–0x7ECFEF32, helpers to 0x7ECFF982; CCommon from ctor 0x7ECFF983 | `fwmap fn 0x7ECFFAC6`: 775 callers, callees new 0x7EBA62DB + 0x7ECFF983; 0x7ECFFB4C = `CCommon::setDbWarningInfo` |
| 13d §2.2 bullet "parent types 257/258" | — | + no static writer of 0x602B6204–0x602B620A | functions.txt: 244 lines name 0x602B6204–0x602B620A, but no instruction stores to them by absolute address (the only absolute stores nearby are to 0x602B6200 at 0x7ED17DAA and 0x602B620E at 0x7ED1BC32/0x7ED1BC3C) |
| 13d §2.3 slot 0 | "returns a constant (class info)" | destructor: returns deleter 0x7ECEEFC3 | vtable 0x7EEF5328 slot 0 = 0x7ECEE21F: `fc dc c3 ef ce 7e` (`mov 0x7ECEEFC3,a0`), `retf`; 0x7ECEEFC3 is a `movm` function that calls 0x7ED17DA1 |
| 13d §2.3 slots 23–28 | "focus-like" (I) | bit 16 is focus with ancestor propagation | `disasm 0x7ECEEE9D`: calls vt+108(1) on itself, then walks parents with vt+128 and calls vt+116(16, 1) on each; 0x7ECEEED6 is the same with vt+108(0) |
| 13d §2.3 slot 102 | 0x100–0x102 = press/release/move (I) | move/press/release + CB_ONCLICK; +140/+144 import/export; +252 layout | strings `GM_CB_ONMOUSEMOVE`/`ONPRESS`/`ONRELEASE`/`ONCLICK` at 0x7EFDFC70–0x7EFDFCA0 in that order |
| 13d §2.3 slot 103 | returns −1 for 6399 | OnNotify map (sentinel 0x18FF = 6399) | 6399 = 0x18FF |
| 13d §2.4 bullet "14 of 15 keep the empty base OnDraw" | struck | base OnDraw 0x7ECF4DA2 calls DrawSelf +568 unless bit 0x20; 14 of 15 override DrawSelf | `disasm 0x7ECF4DA2`: `mov (120,a1)…calls`, `mov (568,a2),a2; calls (a2)`, then `mov 6146,d0` (0x1802), `mov (564,a2)`; vtable +568: 0x8001 → 0x7ECF5442 (`retf`), 0x8002/03/04/05/06/0E/0F/10/11 → own functions 0x7ED1CC1E…0x7ED2FB23 |
| 13d §2.4 drawing-engine bullet | "rotation routine 0x7ED3231E"; range about 0x7ECF5000– | slope/cotangent helper; exact renderer and DC ranges | `fwmap fn 0x7ED3231E --dis`: angle × π/1800 → tan 0x7E501AAC → fabs → × 65536.0f (0x47800000), one caller 0x7ED31C9B |
| 13d §2.4 helper-layer bullet | 0x7EDC181B "or hide when the id is 0" | + never shows; layer ends 0x7EDC1B36; new helpers 0x7EDC1835, 0x7EDC19F4, 0x7EDC1A45, 0x7EDC1A96, 0x7EDC1AB4 | 0x7EDC1B37 (1,333 B) follows (13d already) |
| 13d §4.3 step 6 | counter "reaching 10" | OK-long → 14 (or 10 from 15), MENU-long → 15 (or 10 from 14); entry 0x7EDABA6F sets 2 s long-press for keys 8/9 | `fwmap fn 0x7EDAF544 --dis`: `cmp 15`, calls 0x7EDED0F6/0x7EDED14A, `mov 10`/`mov 14` → (0x602BC482); 0x7EDAFE4B: `cmp 14`, `mov 10`/`mov 15`; 0x7EDABA6F: `mov 8,d0; mov 2000,d1; call 0x7ED00B90` and `mov 9,d0; mov 2000,d1` |
| 07 §5 SS_DEBUGMENU row | "entry key combination not found" | superseded (13d §4.3, 14e §4.4) | 13d §4.3 (D1, verified) and above |
| 10f §4.1 | entry sequence 1 only | + HIDE_MODE entry 0x7EDABA6F and sequence 2 (OK-long + MENU-long + OK) | as 13d §4.3 step 6 |
| firmware-map feature row "GUI debug menu" | sequence 1 only | + second sequence | same |

### 1.7 Brief-only firmware-map items

| location | old | new | check done |
|---|---|---|---|
| firmware-map §1 regions row 0x7E4E0000–0x7E521020 | no `sc` | + `sc` library 0x7E506CB0–0x7E508DA6; UI from 0x7E508DA7 (14b §8, section-01 item; 01 has no regions table) | 0x7E506CB0 loads `sc debug commands`; last `sc` fn 0x7E508D23 (132 B) ends 0x7E508DA6 |
| firmware-map §1 regions row 0x7E521020–0x7E621020 | IMG_PRECON disputed; buff to 0x7E579A7F | IMG_PRECON resolved; buff to 0x7E579C33; WB module; TAKE from 0x7E581FB0 | §1.2 |
| firmware-map §1 regions row 0x7E966000–0x7EBA1020 | ~0x7EB93422 / ~0x7EB93423 | exact | §1.3 |
| firmware-map §1 architecture item 6 (GUI) | ~0x7ECC8000–0x7EE01FF5 | 0x7ECCB800–0x7EE02094 | §1.4; 0x7EE02095 = GL init (14a) |
| firmware-map §1 "Link order" bullet | "places all 152 source-file names" | + D2 changes to modules.tsv | §1.8 |
| firmware-map §3 feature rows | iAuto "12 scene types (inf)"; Pixel Mapping disputed; no GPU-slideshow row; touch panel without detail | scene ids; PRECON resolved; new row **GPU slideshow = C3D**; touch-panel reflash only via `disp tp boot_on` (Hidden) | §1.1, §1.4, §1.5 |
| firmware-map open question 4 | WB_MOV no strings; IMG_PRECON = defect only | WB_MOV in WB module; PRECON + WB/colour | §1.2 |

### 1.8 modules.tsv (columns kept: first_fn, last_fn, source_file, fns_naming_file, placement, name_string; rows re-sorted by first_fn, no first..last overlaps)

| location | old | new | check done |
|---|---|---|---|
| cam_frame.c | first_fn 7e63790d | 7e636a04 | §1.1 (error byte 0x12, rodata rule in 14b §0) |
| CapDpc_DisplayControl.cpp | 7e9ee86c | 7e9ee544 | §1.3 (getInstance, 10 callers) |
| CapThr_ThroughImage.cpp | 7ea1852f | 7ea1831e | ctor (caller facade ctor 0x7EA37FC0) |
| CapTak_Take.cpp | 7ea362f8 | 7ea32d19 | getInstance (RAM 0x602B3004) |
| CapRev_RecView.cpp | 7ea46813 | 7ea46704 | ctor (caller 0x7EA4A5B1) |
| CmpSts_3dImageController.cpp | 7ea6e566 | 7ea6d23c | ctor |
| CmpSts_EPortraitShootingEditer.cpp | 7ea70126 | 7ea6ec03 | ctor |
| CmpSts_LiveViewZoomController.cpp | 7ea71af9 | 7ea70d5b | ctor (caller facade 0x7EB7A703) |
| CmpSts_RecViewController.cpp | 7ea75b1b | 7ea75054 | ctor (caller 0x7EB7A703) |
| CmpCst_Function.cpp | 7eaa7e9e | 7ea9f812 | ctor (42 callees) |
| CmpEAsp_EditAspectComponent.cpp | 7eab9261 | 7eab8802 | getInstance |
| CmpEBea_EditBeautyComponent.cpp | 7eabc982 | 7eabc724 | getInstance |
| CmpPCal_PlayCalendarComponent.cpp | 7eb021f2 | 7eb015ff | getInstance |
| CmpPct_PlayContinuousComponent.cpp | 7eb181c1 | 7eb16ff4 | getInstance |
| CmpPEvc_PlayEvcollectionComponent.cpp | 7eb2511f | 7eb2037c | getInstance |
| CmpPli_PlayIndexComponent.cpp | 7eb2fbb2 | 7eb2ecd0 | getInstance |
| CmpPLgh_PlayLightBoxComponent.cpp | 7eb34d9b | 7eb33b24 | getInstance |
| CmpPPho_PlayPhotosurfComponent.cpp | 7eb47a3b | 7eb423af | getInstance |
| CmpPRec_PlayRecordComponent.cpp | 7eb4c862 | 7eb4b882 | getInstance |
| CmpPSel_PlaySelectComponent.cpp | 7eb517f9 | 7eb4f77f | getInstance |
| CmpPls_PlaySingleComponent.cpp | 7eb5e9aa | 7eb58d49 | getInstance |
| CmpSts_MfAssist.cpp | 7eb7deb9 | 7eb7d14b | ctor (member of facade) |
| new rows, placement `inferred-14b`, fns_naming_file 0, name_string `-` | — | `sc [unnamed]` 7e506cb0–7e508d23; `wb [unnamed]` 7e579c34–7e581f9e; cam_aedrv.c 7e629854; cam_afdrv.c 7e62a962; cam_aperture.c 7e62b4dd; cam_debug.c 7e62f6eb; cam_expcal.c 7e635f4b–7e6369ca; cam_lens.c 7e640200; cam_list.c 7e640858–7e640f3e; cam_mec_ctrl.c 7e640f53–7e641ba1; cam_mem.c 7e641bb8–7e642301; cam_mirror.c 7e642325–7e6437f1; cam_shutter.c 7e6557ce | each address is a DB function start; anchors: AE_SEM 0x7E629854, CAMAFD 0x7E62A962, APT_EXE 0x7E62B4DD, CAMLNS 0x7E640200, MI_RES 0x7E642325, SH_RES 0x7E6557CE; every name is in the E-PL7 1.4 `cam_*.c` list (49 names) except cam_debug.c, which is in the 118_4100 and 122_3101 bodies; the alphabetical order of all cam rows holds. 14b gave end addresses for sc/wb (0x7E508DA6, 0x7E581FAF); I used the last function starts (0x7E508D23, 0x7E581F9E) to match the column. 14b's cam_mec_ctrl last fn 7e641ba1 and cam_mem 7e642301 are function starts, kept |

## 2. Rejected

| location | proposed (source) | why not applied |
|---|---|---|
| 07 (14d §6 "Section 07" addition 2) | "the 505-record table 0x7E84A0B8 is followed by its 20-byte descriptors 0x7E84A0D0 into the sparse per-mode records 0x7E83FD00–0x7E8491FF" | The bytes disagree. 0x7E84A0D0 is not a separate table: it is the +4 field of record 1 of the same 505 × 20-byte table (records at 0x7E84A0B8, 0x7E84A0CC, …; +4/+8 = raw/gui pointers 0x7E83FC40, 0x7E83F204 …, range 0x7E83F204–0x7E84A0B4). The hash builder 0x7E7077D3 loads 0x7E84A0B8. 13e §3.1 (raw/gui value arrays) and 07 §2 already say this correctly |
| 14d §3.1 range end 0x7E7FAB33 for the TP image (implied by 14d's §1/§2/§3.1 rows; the firmware-map row has 0x7E7FAB85) | change the map's image end to 0x7E7FAB33 | The bytes disagree: record 469 starts at 0x7E7FAB31 and the image ends at 0x7E7FAB85 (0x7E7F0F78 + 470 × 85 = 0x7E7FAB86; 14d itself says 39,950 bytes). I kept 0x7E7FAB85 in firmware-map |

## 3. Not applied: no target in my files, or already present

1. 14a §5 item 3 "the C2 notes" and 14b §8 "Review C2 batch 1" (F004, F009), 14e §6 item 9 (F056, F060, F065): the targets are coverage files, outside my edit set.
2. 14c §4 item 3 (Live Bulb slot 0x602BC278 vs 0x602BA478): 0x602BA478 occurs only in `coverage/round2-review*.md`; no section or map text has it.
3. 14c §4 item 1 (Tra start 0x7E9698EC; statechart end 0x7EB84344; Com_EvSenderManager 0x7EB84345–0x7EB85562): already in 13c §1 and the map from A5/C2. The 13c §5.3 "self-contradiction" about 0x7EB938CB is already gone, because 13c §1 puts 0x7EB938CB in the categories (C2).
4. 14c §3 "Correction to 13c §6" (relay observers): already in 13c §6 row 0x7EB85D67 (C2). The extra remark "boot-device methods call Usr2 first" was not added (not a correction).
5. 14d §6 "13b: 103 → 102 functions in 0x7E85CEFC–0x7E86DCFF": no such sentence in 13b (only in the coverage brief).
6. 14d §6 "Section 07" addition 1 (info-id tables inside the api rodata row): not an error, and 07 has no rodata row to extend.
7. 14e §6 item 4 (builders relocate only the origin) and item 5 parts (0x7EDC17FB static initialiser, 0x7EDC189F no compare, 0x7EDC1972 via vt+48): already in 13d from A5; only the remaining parts were added.
8. modules.tsv row for `Cmp_ComponentManagerWithBoot` (14c §1.1's 22nd file): no `.cpp` name string exists (only the class name 0x7EC4BCA8), so it has no modules.tsv row; the start is applied in 06 instead.
9. 03 module table names for AE/aperture/shutter (cam_aedrv/aperture/shutter.c): 14b §8 lists them only for modules.tsv, so 03's rows were left as they are.

## 4. Contradictions and errors found in the D2 sections

1. **14c vs 14d (between sections): segment-3 constructor table.** 14c §2.8 says "C++ ctor table 0x7F033AC4–0x7F033B7B (46 entries)"; 14d §1 says the walker runs 0x7F033AC8 for 180 bytes (45 entries). The walker 0x7E44B6B0 (id 3) loads `mov 0x7F033AC8,a2` and `mov 180,d2`, so 14d is right. The word at 0x7F033AC4 (0x7EECC6C4) is a code pointer that the walker does not call. I used 14d's value in the map.
2. **14d §1 vs 13d and the bytes:** 14d gives 0x7ECB0888–0x7ECCB7FF as all 0xFF. Three bytes `de 00 00` (a `retf`) sit at 0x7ECB1000, as 13d says. The map row now mentions them.
3. **14d §3.1/§2:** the TP image range 0x7E7F0F78–0x7E7FAB33 conflicts with 14d's own 39,950-byte size; the true end is 0x7E7FAB85 (§2).
4. **14d §6 Section-07 addition** conflicts with 13e §3.1 (§2).
5. **14d §3.5 vs 13b:** 14d calls 0x7EC92318–0x7EC924AB a "falling ramp: 0xFF × 26, then 0xFE … 0x00"; 13b calls it a sine LUT. The 404 bytes match 255·cos(i·π/2/403) within ±1, with 28 leading 0xFF, so 13b's reading is right and 14d's count is off by 2. I wrote "cosine table" in 13b.
6. **14b §2 vs §8:** §2 gives soft-timer slots 1–31 (`cmp 31,d3`), §8 says "32 slots". The code agrees with §2 (32-bit masks, slot 0 not used); 01 now says slots 1–31.
7. **14b §8 `cam_debug.c` at 0x7E62F6EB:** §0 cites the E-PL7 1.4 file list, but that list has no cam_debug.c (it occurs in the 118_4100 and 122_3101 bodies). The `cam` shell code starts earlier, at 0x7E62EB8E, right after cam_damage.c. The name is plausible by the alphabetical rule, so I added the row with placement `inferred-14b`. Its first_fn 0x7E62F6EB is 14b's anchor (the `Still Normal Start` test function), not a proven file start.
