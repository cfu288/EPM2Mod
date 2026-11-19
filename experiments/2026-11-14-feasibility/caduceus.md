# How Caduceus (OM-3, E-P7) works, and what it implies for the E-PM2

Written 2026-11-14. Read-only study; nothing was built, run or flashed.

**Labels.** VERIFIED = I read it in source code, data or build scripts. REPORTED = the authors' docs or notebook say
so (I read the statement, not the proof). INFERRED = my conclusion.

**Sources read.**
- `OM3:` = androidfanman/caduceus-om3 at `0b1d5cb` (2026-11-13, tag v0.29.1), fresh clone in
  `/tmp/scratch/feas/up/om3`.
- `EP7:` = cakelesscoder/caduceus-ep7 at `fe1977d` (2026-11-13, tag v0.32a), fresh clone in `.../feas/up/ep7`.
  The older local checkouts (`.../scratchpad/repos/…`) stop at OM-3 v0.27.1 and E-P7 v0.31d.
- E-PM2 side: `docs/{film-emulation,art-filter-slots,code-space-map,firmware-map,flashing}.md`,
  `experiments/2026-11-13-intervalometer/README.md`, `experiments/2026-11-11-caduceus-review/*`.
- The earlier review (`experiments/2026-11-11-caduceus-review/`) is still right on method, but it predates OM-3
  v0.28–v0.29.1 (halation, films in camera memory, 660 KiB of new code space) and E-P7 v0.32 (split toning). It also
  predates the E-PM2's own code patches (seven film slots, interval timer), so its "no code patches yet" is out of date.

---

## 1. OM-3: what each feature took

### 1.0 The shape of the mod (applies to every feature)

- **Assembly only, patched into the stock image.** One GNU-as source, `OM3:firmware/src/editor.s` (13,747 lines,
  about 10,000 instruction lines), a linker script that pins 40 hook sections and 12 code areas to stock addresses
  (`OM3:firmware/src/editor.ld:1-52`), and a second source `xblock.s` (2,855 lines, about 2,160 instruction lines)
  for a relocatable block. VERIFIED (line counts, linker script).
- **A hook is a 5–8 byte `call`/`jmp` over a stock instruction.** `build.py` asserts the stock bytes at every hook
  before it writes (`OM3:firmware/build.py:257-258`), asserts each free tail is all 0xFF and starts where expected
  (`:268-269`), and asserts each loader constant it changes occurs exactly once in the image (`:265`, `:271`). VERIFIED.
- **Three places for new code**, found in this order:
  1. *Section tails:* 0xFF padding between the end of a section's data and the end of the range the boot loader
     copies to RAM. Ten tails, 7,492 B in total, 7,372 B used by v0.21 (`OM3:research/NOTES.md:679-682`). REPORTED.
  2. *A relocatable code block loaded from the card:* appended to `OM3MOD/GUIDES.BIN`, linked at 0x10000000 with a
     relocation list, tagged with 3 bytes of the firmware image hash, loaded into one `malloc` block (cap 16,448 B)
     and fixed up by a position-independent relocator; flash stubs jump into it through a heap pointer
     (`OM3:docs/DEVELOPER_NOTES.md:281-291`). Invented at v0.20 because only about 90 B of tail space was left
     (`:279`). REPORTED. From v0.29 the same block is stored inside the firmware image and "loaded" by wrappers
     around the file functions (`:432-435`). REPORTED.
  3. *Extending a section's loaded range.* The flash image has 2.33 MiB of 0xFF between sections that the camera does
     **not** copy to RAM (`NOTES.md:686-688`). Each section's copy end is one `mov imm32` in the loader. They moved
     section 6's end word (0x60045e9c) and proved the new range with a probe build that fills it with a pattern,
     re-checks the pattern and checksums every other gap at each half-press, and writes the result to a card file:
     +4 KiB (GX1), +64 KiB (GX2), +256 KiB (GX3), then to 0x6103f000, +662 KiB (GX4), each run through photos,
     RAW+JPEG bursts and 4K video on the owner's camera (`NOTES.md:795-827`, `:2946-2979`). REPORTED.
- **A mistake on the way:** one test put code in an unloaded gap because om-emu maps the whole image; the camera
  does not (`OM3:CLAUDE.md` "Firmware safety"; `NOTES.md:805-806`). REPORTED.
- **File I/O = the camera's own C-style file API**, found by tracing: `fopen` 0x608d4d22, `fclose`, `fseek`,
  `ftell`, `fread`, `fwrite` 0x608d4da9, `malloc` 0x60024068, `free` (`editor.ld` symbols; `DEVELOPER_NOTES.md:15-19`,
  `:47`). VERIFIED as symbols; REPORTED as camera-proven ("Probe 2").
- **When it runs:** from one hook on the half-press event (`0x60415216`), in the HLS_EVENT task, behind a gate:
  all 10 sections loaded (bit mask 0xa32de590 == 0x3ff), the right task id, a card mounted
  (`DEVELOPER_NOTES.md:14-19`). REPORTED.
- **RAM:** one heap block (1,024 B at first) whose handle is kept in a 16-bit stock variable that was found to be
  boot-cleared and unreferenced (0x62b4dd16) (`DEVELOPER_NOTES.md:13`, `:19`). The heap is small: `malloc` gives at
  most 16,448 B per block from an uncached pool of about 45 KB (`:311-313`; `NOTES.md:2938-2940`). REPORTED.

### 1.1 Feature table (OM-3)

| Feature | Stock mechanism reused | New work | Evidence |
|---|---|---|---|
| **Hue and luminance for 12 colours** | The stock **Color Profile Control** engine (COLOR 1–4). Its builder 0x60518381 already makes 12 output records {hue +18, sat +20, light +22}; stock fills only saturation. One hook after the single call (0x60518615) writes hue and light. Live view uses the same call. | 1 hook + a small routine in a section-1 tail; values in the heap block. UI = the stock colour wheel with extra INFO pages (facade Get/Set words re-pointed; 45 call sites redirected for the wheel outline). | REPORTED `DEVELOPER_NOTES.md:8-11`, `:30-45`, `:74-76` |
| **Blacks / Whites** | The stock luminance-LUT stage of the COLOR tone pipeline (256 × u16 LUT). Hook 0x605197d7 remaps the LUT ends. A port of the E-P7 `tone_ends` patch. | 451 B in a section-5 tail. Tested bit-exact against a Python model in the emulator (127 cases). v0.28: the stock WB fine-tune screen reused as a 2-D grid. | REPORTED `:115-124`, `:478-481` |
| **Split toning** | The job's own R/G/B gamma tables (256 + 64 entries, 12-bit), which the stock tone stage has just built. `st_run` bends them in place at the tone hook's exit; so live view is toned too. | New routine in ext11 + two wheel pages; guides from a picture file. No new ISP stage. | REPORTED `:546-559` |
| **WB shift per film** | The stock WB fine-tune (A-B, G-M) getters: 12 read sites (later +AWB keys) redirected to `wb_get` = stock + film value, clamped ±7. | Routine in a section-1 tail; build asserts each of the call sites by shape. UI v0.25: the stock 2-D WB screen opened from a Picture Mode row. | REPORTED `:89-95`, `:355-356`, `:590-594`; VERIFIED asserts `build.py:288-301` |
| **Sharpness / NR / shading (vignette) rows** | The stock settings reads on the capture path (Sharpness read 0x603e767f, Noise Filter reads 0x603c8038 / 0x603e7891, Shading Comp. key 0x8c21) go through a stub that substitutes the film's value. Rows added to the stock Picture Mode column list by re-pointing its table words. | Stubs + list edits. "Sharp Off" = an index below the menu's range that the stock gain table already accepts. | REPORTED `:286-289`, `:334-335`, `:358-371` |
| **Glow / Clarity** | The stock **Soft Focus art-effect passes**, which the ISP work-list builder adds to *any* job when job flag 0x80 is set. Hook in the Art-Effect→flag converter sets 0x80 on COLOR jobs; the Soft Focus weight getter returns a strength (942…666 = glow; >1024 = unsharp mask = Clarity). | 370 B at first; later in the code block. A port of the E-P7 `bloom` patch. First camera test showed nothing; a later build worked. | REPORTED `:128-140`, `:248-254`, `:288-289` |
| **Colour film grain** | Three attempts. (a) v0.21: switch the COLOR job to the stock **Monochrome-profile grain** pass (key 12 + level): fast, but breaks with Glow/Shading. (b) CPU grain on the developed buffer through a bus window: about 3 s per photo. (c) v0.25, final: attach **Grainy Film's ready-made grain texture** to the COLOR job and answer Grainy Film II's key for the work-list pick only, then restore COLOR's chroma gains in the combiner set-up. As fast as no grain. | 5 hooks (`hook_wl`, `hook_su`, `hook_sel2`, `hook_c1e`, `hook_cl`) + code-block routines. Found by logging the stock Grainy Film path on the camera. | REPORTED `:336-343`, `:575-585`; `NOTES.md:1489-1660` (section titles) |
| **Halation** | No stock stage. A **CPU pass** (`hl_run`) on the reduced buffer after the stock Soft Focus blend: chroma bytes Cb/Cr, weight from cell brightness, two-layer blur (3 + 10 passes). Method after the E-P7. | In ext12. Model bit-exact in om-emu. "Saving with Halation on takes a little longer." | REPORTED `:469-472`; `OM3:CHANGELOG.md:136-138` |
| **FILM 1–20 in the Picture Mode list** | The stock setting 901 (COLOR position) gets 24 value records instead of 4; the three picture lists of menu item 111 are re-pointed. A film is an **alias**: film j loads onto COLOR k = j / 5. Only the list builder and one cell see the film value; everything else sees COLOR k. | Facade Get/Set/selectable wrappers, own pictures drawn at run time, title string hooks. | REPORTED `:624-632`; VERIFIED asserts `build.py:351-363` |
| **Per-film stored edits** | The 18 stock COLOR settings are read and written through the stock settings facade (`SetValue` 0x60b8798b, manager 0x60bb528f). On a film switch, `fl_sw` captures what COLOR k holds and loads the new film. | Records of 64 B per film; `*` = "differs from as built" via 7 wrapped "is default" sites. | REPORTED `:182-197`, `:633-641` |
| **LOOKS.BIN from the card** | Stock file API (above). `LOOKS.BIN` = 1,632 B: header, CRC-32, 20 × 64 B records, 20 × 16 B names. The camera checks size, magic, CRC, version and every byte's range; a bad file is ignored. Writes went to `.NEW`, read back, then `.BIN`. | — | VERIFIED format `OM3:docs/FORMATS.md:5-41` |
| **Films in camera memory (v0.29)** | The stock **settings store "M"** (256 KiB RAM image, two alternating flash slots, 16-bit checksum over the whole image). The camera's own items end at offset 0x39465; Caduceus puts a 3,912 B block at 0x3A000 and sets the stock "changed" byte so the camera's own save writes it (menu exit, power-off). They never call the flash write. | Proven first with a marker probe over two battery pulls on the camera. Writes are held back while the camera's own save is running. Design by an outside contributor (iancw). | REPORTED `:422-431`; `NOTES.md:3581-3664` |
| **Button / dial remaps** | Stock key table → setting id → function table. "Nothing checks which key a function code came from." Arrow rows added to Button Function; Creative Dial positions use setting ids of *other bodies' buttons* that exist in the OM-3's validator table but are unused. | Menu rows, pictures composed at run time from stock pictures (two 64 KiB buffers), 256 KiB of new space. | REPORTED `OM3:research/BUTTONS.md:8-22`; `DEVELOPER_NOTES.md:500-510` |
| **EXIF recipe** | Hook on the per-shot EXIF fill (0x60457578): ImageDescription = "FILM n Name"; UserComment = name + base64url of the 64 B record. | Small. A buffer overrun of 2 B was shipped and fixed in v0.28. | REPORTED `:511-513`; `CHANGELOG.md:111` |
| **Debug log** | Stock file API; on only when `OM3MOD/DEBUG.TXT` exists. `CADLOG.TXT` is always 4,096 B because the camera's `fopen "w"` does not truncate. Written only at shutter-button events. | Needed the first big space extension (256 KiB of section 6). | REPORTED `:514-517` |

### 1.2 What went wrong (OM-3)

| Event | Cause as they state it | Recovery / fix | Evidence |
|---|---|---|---|
| **Boot loop** (v0.20 grain test 1) | A hooked ISP stage in section 2 called code placed in section 8; the stage runs before later sections are loaded → exception. | "Recovered by flashing v0.19" through the normal card update. Rule since: hooks on early paths call only code in sections 1–5. | REPORTED `DEVELOPER_NOTES.md:239-242` |
| **Code in unloaded space** (sliders test) | The emulator maps inter-section gaps, the camera does not. | Rule "only proven space"; GX probes. | REPORTED `CLAUDE.md`; `NOTES.md:805` |
| **"Values move, no effect"** (test 13) | Not found; bisected by flashing the previous test. Feature dropped. | — | REPORTED `:153-157` |
| **Reboot with Film Grain High** (v0.24, withdrawn the same day) | The grain code called the settings getter while the photo was being taken. | v0.24.1 removed the call. | REPORTED `:609-612` |
| **Reboot at half-press** | A WB getter placed in the card-loaded block; "hooks on the capture / AE / WB paths stay in flash". | Moved to flash. | REPORTED `:344-348` |
| **Restart on switching to COLOR** | Dial-list callbacks with deep stack frames; "must be frameless leaves". | Rewritten. | REPORTED `:346-348` |
| **Freeze with grain + RAW+JPEG** (v0.25–v0.26.1) | RAW+JPEG runs a second development job that reset the grain state. | v0.26.2 gates on the job key. | REPORTED `CHANGELOG.md:247-248` |
| **Restart after a drive-mode change** | A hook captured a GUI object from the wrong screen (crash with a0 = 0x20041001). | Gate on GUI state 0x0418. | REPORTED `:560-562` |
| **Settings not saved** | A nested `call` overwrote a saved register: MN103 `call` writes the return address at (0,sp), so a function that calls another must keep that slot free. Found twice. | Frame rule. | REPORTED `:149-150`, `:595-597`, `:436` |
| **Sporadic start-up freeze** (v0.26.2, v0.27) | Suspect: the automatic film load (a new RTOS task polling every 100 ms, then a settings `SetValue` from HLS_EVENT while the GUI builds the start screen). Live view on, nothing else, power switch dead; battery pull. Never reproduced on demand. | v0.27.1 removed the auto-load; films load at the first half-press. Still so in v0.29.1. | REPORTED `NOTES.md:2868-2884`; `OM3:docs/SD_LOADER.md:1-8`; `CHANGELOG.md:44-45` |
| **Opcode forms that misbehave** | `fb`-prefixed AM33 forms "misbehave on the camera and fault in om-emu"; avoided. | Build shows 0 such opcodes. | REPORTED `:344-345` |
| **Open user reports** | Freeze on Creative Dial change (#27), grain + glow crash on save and heat (#28), USB storage option lost (#7, closed). | Partly not reproduced. | VERIFIED issue list via `gh api` |

No permanently bricked OM-3 is recorded in the repo or its issues. VERIFIED by search (grep for brick / bootloop /
recover over docs, notebook and the issue titles); absence of a report is not proof.

### 1.3 Size of the OM-3 mod (question 4)

Computed by me from `OM3:releases/v0.29.1/patch.json` (158 runs, 323,744 run bytes; its own field says 321,631
changed bytes). VERIFIED.

| Region | Run bytes | Of which not zero-filled reservation | What |
|---|---|---|---|
| 10 section tails (ext1–ext10) | about 7,100 | all | first code areas; ext1 is 1,742 of 1,744 B |
| ext11, 0x60f49800 (section 6 + 64 KiB) | 53,408 | 51,762 | sliders, film list, split toning |
| ext12, 0x60f59800 (section 6 + 256 KiB) | 224,320 | 71,617 | buttons, halation, EXIF, log, memory block code; 152,703 B are zero buffers (two 64 KiB diagram buffers, 20 KiB of button pictures) |
| 0x60f99800.. (GX4 reserve) | 36,467 | all | GUIDES / LABELS / TONES built in (pictures + the 16 KiB-class code block) |
| 112 runs of ≤ 16 B, others | about 2,400 | all | hooks, table words |

- So real new code and data is about **170 KB**; the first camera-tested editor (v0.20) was **8.2 KB** in 46 runs, and
  v0.21 8.3 KB. VERIFIED (same computation on `releases/v0.20`, `v0.21`).
- **The file size did not change.** The update file already holds 0xFF between sections; they changed what the boot
  loader copies (one end word), not the container. VERIFIED: `stock_size` 240,517,120 in patch.json and the loader
  word edit `0x60045e9d` is the first run.
- Growth: 8 KB (v0.20–v0.22) → 70 KB (v0.24.1) → 74 KB (v0.26.2) → 322 KB (v0.27). VERIFIED.

---

## 2. E-P7: what differs from the OM-3

This section comes from a delegated agent that read the E-P7 repo at v0.32a; its "V" items were read in
`EP7:releases/v0.32a/edits.json`, build scripts and issues. I did not re-read them, so I mark them **REPORTED
(agent-verified)**. `FG` = `EP7:docs/FIRMWARE_GUIDE.md`.

| Feature | Stock mechanism reused | Hook | New bytes |
|---|---|---|---|
| Hue / luminance, 12 colours | Stock COLOR selector 0x603b0252 and builder 0x603b0068, which already emit 12 records for job key 11. Ported by shape-matching fishcu's PEN-F patch. | jmp at 0x603b02d9; job struct grown 15488→15512 for a marker | 880 B |
| Blacks / Whites | Stock 256 × u16 luminance LUT builder 0x603b0a70, bent in job RAM | call retarget 0x603b14ff | 488 B |
| Split tone (v0.32) | Stock RGB gamma is one ROM pointer ×3; they copy it to three 512 B RAM curves, bend and re-point | chained on 0x603b14ff | 925 + 422 B |
| WB shift | Property getter 0x6005e971 redirected at 14 call sites | rel32 only | 164 B |
| NR / shading off / sharpening off | Same getter-redirect idea | rel32 only | 471 + 328 B |
| Glow, Clarity | Stock Soft Focus job flag 0x80 on key-11 jobs; combiner 11 weight | 2 sites | 286 B |
| Colour grain | The ISP route failed four times. Ships a **CPU pass** on Y of the developed buffer, about 22 instructions per pixel, 3–5 s per 20 MP photo | 3 sites | 3,092 + 231 B |
| Halation | CPU pass on a 64 × 64-pixel-cell grid, on the grain route | via the grain hook | 736 + 426 B |
| Looks from SD, names | Stock file API; label builder kind 4 (string id) swapped for kind 5 (heap text) | 3 sites | 865 + 978 + 672 B |
| On-camera editor | Stock Color Profile wheel editor; mostly data-word re-points | data words | about 5.5 KB |
| Button remaps | Data only: validator lists; "the dispatcher has no per-key check" | 10 edits | about 235 B |
| EXIF look name | One rel32 retarget on the copyright-enable getter | 1 site | 301 B |
| Rec limit, watchdog | Immediate operands | — | 4 + 4 B |
| Debug log | None ships | — | — |

- **Space (E-P7):** image not extended. 0xFF tails in 8 loaded sections (about 8.8 KB), **dead EVF gamma tables**
  (about 23 KB: the body has no EVF), and **dead debug-shell handlers** (205,733 B, made dead by re-pointing three
  command words). Proof = scan for absolute addresses in four aliases plus relative call/jmp decode at every byte
  offset, with 16 B guards (`FG:105-138`, `EP7:docs/CODE_SPACE_SURVEY.md:16-37`). REPORTED (agent-verified).
- **Totals v0.32a:** 505 edits; 77,690 bytes actually differ; new code + tables in free space about **34 KB**; the
  rest is in-place OSD bitmap edits. REPORTED (agent-verified, computed).
- **No code is loaded from the card** in releases; a `PLUGIN.BIN` loader exists but is shelved. REPORTED.
- **Persistence = card files only.** They rejected storing in the camera's settings memory as "brick-adjacent"
  (`EP7:docs/LOOK_EDITOR.md:166-183`). REPORTED. (The OM-3 project later did exactly that, with a probe first.)
- **File API (E-P7):** fopen 0x60634fbc … fseek 0x60635243; each call is a synchronous RPC to a FILECLBK task with
  no timeout; never called at boot, only from the half-press hook in HLS_EVENT (`FG:446-466`). REPORTED.
- **Failures (E-P7), REPORTED:** a **boot loop** on test 3 (seven feature groups in one flash; suspect a patch that
  ran at power-on and stored into section RAM; recovered with battery out, then OK + power with the stock file,
  `EP7:WORKLOG.md:190`, `docs/BOOTLOOP_T3.md`); a crash from a store into loaded-section RAM; a crash from a
  misaligned word read that the emulator does not fault on; a **hardware watchdog (10 s) restart** on heavy CPU
  grain + halation, "fixed" by raising the watchdog to 30 s; keys dead after a grain shot (shared pool of 43 fixed
  16 KB blocks exhausted; v0.32a fix not camera-tested); FAT corruption on one card, never explained; open issue #48
  (crash needing a battery pull).
- **Test method (E-P7):** not om-emu. They use fishcu's `penf_emulator` to run **single firmware functions on
  synthetic fixtures**, patched against stock, comparing registers, stack, MDR and PSW. Stated blind spots: alignment
  faults, key routing, DMA, ISP pixels, file timing (`FG:516-555`). REPORTED.
- **Port order they prescribe:** official file → restore round trip → text change → data edit → no-op hook → one
  feature per flash (`EP7:docs/BODIES.md:22-28`). REPORTED.

---

## 3. What depended on stock features the E-PM2 lacks (question 2)

E-PM2 facts are from this project's docs (cited); I did not re-read E-PM2 bytes for this report.

| Caduceus feature | Relies on stock stage / mechanism | E-PM2 equivalent |
|---|---|---|
| Hue / saturation / luminance for 12 colours | **Color Profile Control engine**: a builder that already outputs 12 records with hue, sat and light fields; stock leaves hue and light at 0. REPORTED both repos. | **None with 12 sectors or with a luminance term.** The E-PM2 has a **six-axis** stage: six saturation and six hue values per mode (`art-filter-slots.md` §2.2 stage d). Already used by the film slots. No per-colour luminance. |
| On-camera editing of those values | The stock COLOR wheel editor, its 48 per-sector settings, the settings facade | **None.** No colour wheel, no per-sector settings. The nearest stock editors are Picture Mode Contrast / Sharpness / Saturation / Gradation. INFERRED from `firmware-map.md` feature list and the earlier review 02 (no COLOR strings in block 0). |
| Blacks / Whites, Highlight & Shadow | A per-job **RAM** luminance LUT built per shot, plus per-profile H/M/S settings | A luma "look curve" stage exists (stage b, 256 × u16 **ROM** tables picked by art code). Data edits work today. A per-shot bend needs a RAM copy and a hook: new reverse engineering. Whether the E-PM2 builds this curve in RAM per job is not in the docs. UNKNOWN. |
| Split toning | Per-job R/G/B gamma tables in RAM (OM-3), or ROM pointers that can be re-pointed per job (E-P7) | Per-channel base gamma exists (stage a, record of 8 pointers to ROM tables). Fixed split tone per slot = data, already done in effect by the per-channel curves. Adjustable split tone needs the E-P7 method (copy to RAM, bend, re-point). |
| WB shift per film | Stock WB fine-tune getters at 12–14 call sites | The E-PM2 has WB compensation A/G as settings (prm store). The call sites are not mapped. Getter-redirect is a generic method. |
| Sharpness / NR / shading per film | Settings getters on the capture path | Same: the settings getter 0x7E457C75 exists (`firmware-map.md` §4); which reads feed capture is not mapped. |
| Glow / Clarity | **Soft Focus as a job flag that the ISP work-list builder honours on any job** (flag 0x80, combiner 11 weight) | **Different architecture.** On the E-PM2, effects are modules in the ART task chain that only art modes reach; the earlier review found no job flag and no blend weight (`02-features-portability.md:64-72`, "What differs in the engine"). The film slots *are* art modes, which helps: Soft Focus's blur module could in principle be run for a film slot. But removing or re-routing effect modules froze live view three times (`film-emulation.md` §6). |
| Colour grain (OM-3 fast route) | Grainy Film's texture object + work-list key swap in the ISP | Grainy Film exists (codes 74/104, texture in block 2) but is "monochrome + grain texture" with "14 more places in record / art code" (`art-slots-evaluation.md:46`). The OM-3 itself found its mono route is luma-only end to end. UNKNOWN whether the E-PM2 grain module can run on a colour buffer. |
| Colour grain / halation (CPU route) | A way to map the developed YCbCr buffer into CPU address space (window mapper + lock + flush), found by tracing; a watchdog that tolerates seconds of CPU work | Not mapped on the E-PM2. The ART chain has a CPU lane (earlier review). The E-PM2 CPU is far slower; 16 MP at ~20 instructions per pixel would be several seconds or more. INFERRED. |
| FILM entries in the Picture Mode list | Alias rows on one stock setting; everything else sees COLOR k | The E-PM2 film slots already are menu rows (art filters renamed). Adding rows to a full menu was done for the interval timer by copying the table to free space and renumbering (31 constants). Feasible, proven class. |
| Per-film stored edits; films in camera memory | Per-profile settings + an unused tail of the settings image that the stock checksum covers | The E-PM2 has a settings store (1,800 prm tags, 6 storage classes). Whether its image has an unused, checksummed tail is not known. UNKNOWN. |
| LOOKS.BIN from the card | Stock C file API + malloc, called from a half-press hook in a known task | The strings `fileif_fopen err.` and `fopen err` and a C runtime with stdio (0x7E4FE000–0x7E501C5A) are in block 0 (`build/map/strrefs.tsv`; `firmware-map.md:32`). Entry points, calling task rules and a half-press hook are **not traced**. Needs new reverse engineering, but nothing suggests it is absent. |
| Button / dial remaps | Key table → setting id → function table, with unused ids from other bodies | Not mapped. The E-PM2 has few buttons (Fn, REC, arrows). UNKNOWN. |
| EXIF recipe | Hook on the per-shot EXIF fill | Not mapped; the E-PM2 writes ImageDescription / UserComment fields like every Olympus. Needs tracing. |
| Creative Dial, COLOR 1–4 slots, Monochrome profile, AP mode, hidden log gamma, hidden aspect ids | Stock on OM-3 / E-P7 | Absent (no dial, no profiles, no AP mode; the earlier review found no log curve; the nine aspect codes do exist). |

**The one-line version.** Almost every Caduceus look feature is "write different numbers into a stage that the stock
Color Profile pipeline already runs per shot from RAM". The E-PM2's pipeline picks **ROM tables by art-filter
number**. That is why this project's film slots are ROM table sets, and why "adjust on the camera" is the hard part
here, not "make the look".

---

## 4. Engineering method, testing, recovery (question 3)

Sections 4.2–4.4 and 5 rest on a delegated GitHub sweep (scratch files in
`/tmp/scratch/feas/sweep/`). Items it read
in source are marked **REPORTED (agent-verified)**; I did not re-read them, except where I say VERIFIED.

### 4.1 The working loop

- **OM-3:** build → om-emu UI session → package for the owner → owner flashes and uses the camera → only then release.
  A release must rebuild the camera-tested bytes exactly (`OM3:CLAUDE.md` "Test order", "Releasing"). REPORTED.
- **One question per test build.** Probe builds answer one thing and report through a card file (GAPTEST.BIN for code
  space, CADLOG.TXT for the settings-memory marker). REPORTED `OM3:research/NOTES.md:694-699`, `:3597-3619`.
- **Bit-exact models.** Each pixel routine (tone ends, split tone, grain, halation) has a Python model, and the
  assembly is run in the emulator against it (`DEVELOPER_NOTES.md:123`, `:341`, `:471`). REPORTED.
- **Status words.** Every note says "camera-tested", "emulator only" or "analysis". REPORTED `OM3:CLAUDE.md`.
- **Build-time checks.** Stock hash, stock bytes at every hook, call-site shape checks, 0xFF proof of each tail,
  size limits per area. VERIFIED `OM3:firmware/build.py:251-325`.
- **E-P7:** single-function emulation only (section 2), plus an edit list in which every edit carries its expected
  stock bytes. REPORTED.

### 4.2 om-emu (https://github.com/flatpanda/om-emu)

- **Models:** 19 entries in `emu/src/fw/models.mjs`: E143 (OM-1, reference), E146, E147 (OM-3), E144, E148, E139,
  E134, E137, E142, E140, E125, E145, E133, E130, E129, E132, E118 (E-M5 II), E122 (PEN-F), E120 (E-M10 II).
  VERIFIED by me in the local checkout (96bf756, 2026-11-11); the agent reports the same list upstream on 2026-11-14.
- **No E101 (E-PM2), E100, E108, E112 or any TruePic VI/VII entry.** They are survey rows only
  (`docs/model-survey.md:69-72`, E101 base 0x7e421020, "not tried"); `docs/ROADMAP.md:149,219` puts them in "Tier D:
  no work planned"; `model-survey.md:87-88` says these bodies lack the OSD engine it models at 0x9c100000.
  REPORTED (agent-verified).
- **Does it boot to a UI?** Not from reset. Kernel init runs with some steps replaced, then a harness task starts the
  display, GUI and camera application. On its 19 bodies it reaches the shooting screen and navigates the camera's
  own menus, half-press, full press and playback. Sensor, AF, shutter and movie are stand-ins; the image pipeline does
  not run. REPORTED (agent-verified, `README.md:3-48`). Caduceus OM-3 confirms the limits: "The capture/LV pipeline
  itself not emulated: camera test" (`OM3:docs/DEVELOPER_NOTES.md:124`), "malloc above 16384 B never returns in the
  emulator" (`:148`), and it maps unloaded gaps that the camera does not (`NOTES.md:805`). REPORTED.
- **Upstream moved** 133 commits since the local checkout: it now replays Caduceus `patch.json` files with a patch
  audit and models which sections the boot loader leaves loaded. No new bodies. REPORTED (agent-verified).
- **Licence: none.** REPORTED (agent-verified); the earlier local review says the same.
- **For the E-PM2 today:** this project already runs single E-PM2 functions in a locally patched om-emu
  (`emulator/README.md:3-28`). A UI session would need a real port. INFERRED: weeks,
  as the earlier review estimated, and upstream will not do it.

### 4.3 Recovery from a bad flash: what is proven where

| Body | Event | Recovery | Strength |
|---|---|---|---|
| OM-3 | Boot loop (v0.20 test 1) | Normal card update with the previous build | REPORTED `OM3:research/NOTES.md:245`; once |
| E-P7 | Boot loop (test 3) | Battery out, OK + power, stock file | REPORTED `EP7:docs/BODIES.md:30`: "proven only on the E-P7, and only once" |
| E-M10 I (TruePic VII) | Boot loop "card in or out" | OK + power with a good file; "one data point on one body" | REPORTED, cmdada/em10-fw `README.md:175-178` |
| E-PL3 | No boot, no USB after a code-table change | Card recovery with official 1.6 worked; steps not recorded | REPORTED, sympho-ru `docs/observations/DEPLOYMENT.md:122-140` |
| **E-P5 (TruePic VI)** | A data patch flashed 2026-11-13, then stock restored; a second build gave a black live view in ART mode only | Restore from a *working* camera | REPORTED, thrains0220-byte/ep5-fw-reverse branch `work/ep5-film` |
| **E-PM2** | Text and data patches, then code patches | Stock reflash from a working camera, 2026-11-08 | VERIFIED in `docs/flashing.md`, `docs/camera-log.md:11` (this project) |

- **No permanent brick from a modified flash is reported in any of these repos or their issues.** REPORTED
  (agent sweep). This is survivorship-prone evidence: five bodies, one event each.
- **Why boot loops were recoverable there:** the faults were in late code. The updater ran before the faulty code.
- **Is there a boot loader that always accepts a card file?** Not established for any TruePic VI body.
  - E-M10 I: cmdada says the updater sits in a second boot stage below main; another author on the same body says
    "Recovery is unproven". REPORTED, conflicting.
  - E-M5 III, E-P7, PEN-F: the updater is in the main image and needs most of the boot; a crash early in boot means
    "service or flash programmer only". REPORTED (nsud-dev `docs/firmware/recovery.md:56-67`; `EP7:FG:77-80`).
  - **E-PM2: the updater is main-firmware code** in block 0, run from Usr0 after about 56–60 tasks start
    (`experiments/2026-11-11-caduceus-review/README.md:44-47`). On the update boot path, Usr1 does not run, so
    segment-2, segment-3 and usr1-third are not loaded and none of their code runs (`docs/code-space-map.md:25`).
    INFERRED from that: a fault confined to segments 2/3 cannot stop the updater; a fault in the kernel, segment-1 or
    the `.data` image can. Recovery from a boot loop has **not** been tried on the E-PM2.
- **Other routes (service mode, special card files `S101????BIN` / `DATE????BIN`, USB updater on a dead body,
  serial pads, flash programmer):** nobody has used one. The special files are hazards, not rescues (they bypass
  checks). REPORTED / speculative.
- **Updater checks:** bad checksum or wrong model is refused before any write; version is not checked. Proven on an
  E-PL9 with a deliberately corrupt file (JuiceLee999/caduceus-epl9). REPORTED. Not yet tried on the E-PM2.

---

## 5. Other projects, and statements about older bodies (question 5)

| Project | Body | State (2026-11-14) |
|---|---|---|
| thrains0220-byte/ep5-fw-reverse, branch `work/ep5-film` (new, 11-10 to 11-13) | E-P5 1.8, TruePic VI | "Soft Chrome": 48 main bytes + 30 language bytes, no added code, flashed and restored on one camera. A code-cave LUT module exists as a model only. A build that zeroed 13 effect pointers gave a black live view in ART mode. |
| same, `main` | E-P5 | 4-byte AF patch, user-verified. Concluded an ART menu entry cannot be *added*. |
| cmdada/em10-fw | E-M10 I, TruePic VII | A code loader flashed; plugins run from the card. Stock stills take a one-pass hardware route, so pixel plugins had to force the e-Portrait route: 7–20 s per picture. |
| azqeurio/om-c-firmware (closed binary) | several | Aperture-ring patch; **E-P5 1.8: two user reports, both failed.** |
| atx/fenykl | E-PL3, E-M10 II | Code loader that runs a file from the card. |
| matozoid/em10_1 (newer) | E-M10 I | Documentation only; owner judges flashing too risky. |
| fishcu/oly_fw_analysis | PEN-F | The original 12-colour HSL patch that Caduceus E-P7 ported. |
| nsud-dev/olympus-firmware-notes, nsud-dev/ghidra-mn103 (new, 11-14) | E-M5 III | Code patches on camera; a Ghidra MN103 processor module. |
| przestaw/OM-5-firmware-patches (new, 11-12) | OM-5 | Documentation only. |
| JuiceLee999/caduceus-epl9 (fork) | E-PL9 | Port in progress; hosts looks in the Watercolor art filter (the same idea as this project's film slots). |
| fernandezk26/camera-stuff | OM-3 | Source of the auto-load task that was later removed for freezing. |

All REPORTED (agent sweep). Searches for "olympus unbrick", "olympus service mode", "E-PL5", "E-M5 firmware hack",
"TruePic firmware" returned nothing relevant.

**Statements about older bodies.**
- **Caduceus E-P7** lists nothing older than the E-M10 II ("has Color Creator, but predates COLOR profiles… research
  only"). It states that without COLOR profiles the look features are "a redesign, not a relocation"
  (`EP7:FG:651-655`), and names as portable on their own: rec limit, LCD tint, aspect tables, version label, button
  lists (`FG:656-657`). Issues #30 (E-P5, E-M10 II, E-M1 II) and #25 (E-M5 II, "too old?") have no maintainer answer.
  REPORTED (agent-verified).
- **Caduceus OM-3:** "Other cameras aren't supported" (`OM3:docs/FAQ.md:9-11`). VERIFIED.
- **om-emu:** TruePic VI bodies are "Tier D: no work planned". REPORTED.
- **E-P5 project:** names as unverified on camera the pixel buffer format and lifetime, cache/DMA and the calling
  rules; says its own emulation gave false passes; found a 32,752-byte 0xFF run and notes "padding does not prove
  nothing uses it at run time". REPORTED. The E-PM2 map has the same-size run (0x7E440010–0x7E448000, 32,752 B,
  NEEDS-DECISION, `docs/code-space-map.md:127`). VERIFIED (both numbers); that they are the same structure is INFERRED.
- **Nobody else targets the E-PM2, E-PL5, E-PL6, E-M5 or E-PL7.** REPORTED. The only E-PM2 hit in code search was
  this project's own repo, public under the owner's account name: worth knowing given the "scrubbed of username" rule.

---

## 6. Transferability table (question 6)

"Has it" is from this project's E-PM2 docs. Verdicts: **Direct** = the method ports as is; **New RE** = same method,
but the E-PM2 sites must be found; **Absent** = needs a stock stage the E-PM2 does not have; **Unknown**.

| Feature | What it needs | Does the E-PM2 plausibly have it | Verdict |
|---|---|---|---|
| A film look as a menu entry | Per-mode colour tables | Yes: six table stages per art code; 7 slots built and camera-tested | **Done** (data + about 900 B code) |
| More FILM rows than stock menu rows | Menu tables that can be copied and extended; alias rows | Menu-row insertion proven (interval timer). Art-code dispatch tables are full or code-bound | **New RE** (each new slot needs its own table set and space) |
| Hue / sat per colour | Per-hue stage | Six axes, hue and sat only, fixed per slot | **Direct** as data (done); 12 sectors and luminance: **Absent** |
| On-camera editing of the look | A stock editor widget + settings + a RAM stage read per shot | No colour editor; stages read ROM tables | **Absent** as designed. A minimal version (a stock ±N setting that selects between pre-built table sets) is **New RE** |
| Blacks / Whites, tone | Luma curve stage | Yes, ROM table per slot | **Direct** as data; adjustable: **New RE** |
| Split toning | Per-channel gamma | Yes, ROM tables per slot (three-record handlers) | **Direct** as data (fixed per film); adjustable: **New RE** |
| WB shift per film | WB fine-tune read sites | Setting exists; sites unmapped | **New RE** (getter redirect) |
| Sharpness / NR per film | Settings reads on the capture path | Settings getter known; sites unmapped | **New RE** |
| Glow / Clarity | Soft Focus as an ISP job flag + blend weight | Soft Focus is an ART-task module; no flag, weight not found | **Absent** in that form; re-using the module on a film slot is **Unknown** (three live-view freezes so far) |
| Colour grain, fast | Grain texture pass usable on a colour job | Grainy Film texture exists; path is monochrome | **Unknown**, likely Absent |
| Colour grain / halation, CPU | CPU access to the developed buffer; watchdog margin; seconds per shot | Unmapped; slower CPU | **New RE**, high risk, slow |
| Films in a card file (LOOKS.BIN) | File API, malloc, a safe task and moment, RAM-resident tables | fopen strings and stdio present; nothing traced; stages read ROM | **New RE** twice over: the loader, and making stages read RAM |
| Films in camera memory | Checksummed settings image with an unused tail, saved by stock code | Settings store exists; layout unknown | **Unknown** |
| Button / dial remaps | Key → setting → function tables | Unmapped; few buttons | **Unknown** |
| EXIF recipe | Per-shot EXIF fill hook | Unmapped | **New RE** (small) |
| Debug log to card | File API | As LOOKS.BIN | **New RE**; valuable early |
| More code space | A loader end word per segment + unused RAM behind it | Yes in structure: 9 copy sites with end constants; 1.59 MB of unloaded 0xFF; today 320 B proven code space, 17.6 KB usable data | **New RE + camera probe** (the GX method) |
| Code block from the card | File API + malloc + relocator | As above | **New RE**; not needed if the loader-end method works |
| Emulated UI test | om-emu model | Function-only local model | **Absent** upstream; own port needed |

---

## 7. The five lessons

1. **Caduceus did not add an image pipeline; it re-parameterised one that was already per-shot and in RAM.** The
   12-colour engine, the tone LUT, the gamma copies and Soft Focus as a job flag were all stock. The E-PM2 selects ROM
   tables by art-filter number, so the transferable part is what this project already does (table sets per slot), and
   the non-transferable part is live adjustment. INFERRED from sections 1–3.
2. **Code space was their first wall and they solved it with a camera probe, not analysis.** Section tails gave
   7.5 KB (OM-3) and 8.8 KB (E-P7). The OM-3 then moved a boot-loader end word and proved 4 KiB, 64 KiB, 256 KiB and
   662 KiB in turn with a pattern-and-checksum probe that reports to a card file. The E-PM2 has the same structure
   (copy sites with end constants, 1.59 MB of unloaded padding, 320 B of proven code space). This is the single most
   valuable method to copy, and it depends on a file-write or other report channel existing first. REPORTED / INFERRED.
3. **Every serious failure was a timing or context fault, not a wrong table.** Code called before its section was
   loaded (boot loop), a settings call during capture (reboot), work at start-up while the GUI builds (the sporadic
   freeze, never reproduced, fixed only by removing the feature), a second development job on RAW+JPEG, the
   watchdog on long CPU passes, a shared memory pool. The emulators caught none of these. Their rule: run new code
   only from the half-press event in a known task, behind a "everything is loaded" gate. REPORTED.
4. **Recovery is one data point per body, and the E-PM2 has none for a boot loop.** Boot loops were recovered by card
   on the OM-3, E-P7, E-M10 and E-PL3, once each, because the fault was late. No unbrick route for a body that fails
   early is known for any Olympus. On the E-PM2, keeping all new code and hooks in segments 2/3 keeps the updater's
   own path untouched. REPORTED / INFERRED.
5. **Scale and order.** The first camera-tested OM-3 editor was 8 KB; the full mod is about 170 KB of real code and
   data and roughly 12,000 lines of assembly, built over about ten days of daily camera tests by an owner with the
   camera in hand, with a booting UI emulator. Their stated port order (restore round trip → text → data → no-op
   hook → one feature per flash) is where this project already is; the next rungs they climbed were a half-press
   hook, a file read, a file write (log), then space. VERIFIED sizes; REPORTED order.

## 8. Limits of this report

- I read the OM-3 repo directly. The E-P7 repo and the GitHub sweep were read by delegated agents; their findings are
  marked as such and were not re-checked by me.
- "REPORTED" camera results are the authors' own statements. I ran none of their code.
- E-PM2 "has it" entries come from this project's docs, not from fresh byte reads. Where the docs are silent I wrote
  Unknown rather than guess.
- OM-3 line references are to `0b1d5cb`; `DEVELOPER_NOTES.md` and `NOTES.md` change daily.
