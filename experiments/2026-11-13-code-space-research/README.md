# Where camera firmware mods find memory for code, and what applies to the E-PM2 (2026-11-13)

Read-only research. Nothing was built, flashed or committed, and no external code was run or copied.
External repositories were downloaded as tarballs of their default branch on 2026-11-13, read as text
in the session scratch directory (`/tmp/scratch/ext2`) and deleted afterwards.

Labels on every E-PM2 statement: **V** = read in our stock v1.6 block-0 bytes or in `docs/code-space-map.md`
today; **X** = stated by an external source (file:line in that repository, or URL); **I** = inferred.
Addresses of other bodies are never E-PM2 addresses.

Sources (short names used below):

| Short | Repository | Body |
|---|---|---|
| EP7 | github.com/cakelesscoder/caduceus-ep7 | E-P7 1.1 |
| OM3 | github.com/androidfanman/caduceus-om3 (and its cited fork fernandezk26/camera-stuff) | OM-3 |
| OFA | github.com/fishcu/oly_fw_analysis | PEN-F, OM-3, E-M10 notes |
| EM10 | github.com/cmdada/em10-fw (cited by OFA) | E-M10 Mark I 1.4 |
| ML | github.com/reticulatedpines/magiclantern_simplified `src/boot-d45.c`, `boot-d45-ch.c`, `boot-d678.c` | Canon EOS |

Not usable: `azqeurio/om-c-firmware` holds only a one-line README. `nikonhacker.com`, `chdk.fandom.com` and
`magiclantern.fm` returned HTTP 403 from the sandbox (network policy); CHDK, Nikon and Panasonic rows below
are from general knowledge and are marked "not fetched". `EDITS.BIN` (OM3) is a data file with the user's
per-film changes (OM3 `CHANGELOG.md:301`); it holds no code.

## 1. Our starting point (V)

- Block 0 is copied to RAM in 9 pieces; 1,586,842 B of 0xFF between the pieces are never copied
  (`docs/code-space-map.md` §3.11, §4). Usable today: 17,578 B data, 320 B code.
- The E-M10 Mark I is the closest relative found: same CPU family, runtime base 0x7D991020 (ours 0x7E421020),
  same task names (FILEFGND, Usr0), same "copy block 0 by sections and skip the 0xFF padding" boot (X: EM10
  `tools/patch.py:17-23`). Its results carry more weight for us than the E-P7 / OM-3 ones (I).
- Six of the unloaded gaps start with the 3 bytes `de 00 00` (`retf [],0`, I for the decode) at the
  old load end: 0x7E881000, 0x7ECB1000, 0x7F034000, 0x7F06B000, 0x7F0EB800, 0x7F119000 (V). Leave them.

## 2. Techniques

| # | Project | Technique | Where the bytes come from | How it was proved safe | Size | Failure stories | E-PM2 equivalent |
|---|---|---|---|---|---|---|---|
| 1 | EP7, OM3, OFA, ours | 0xFF tail inside a section's loaded range | ROM padding that the boot copy already loads | Read the loader's start/end; pointer scan on 4 aliases at every byte offset; rel-branch scan; build re-checks it (EP7 `docs/SD_BUNDLES_V2.md:81-85`; OFA `docs/safety/CODE_SPACE.md:7-21`) | EP7 8.8 KB in all (`docs/CODE_SPACE_SURVEY.md:49-50`); OM3 7,492 B in 10 tails (`research/NOTES.md:679-682`); PEN-F one tail | OM3: slider code put in 0xFF *outside* the load; the emulator mapped the whole image and hid it (`research/NOTES.md:723-727`). EM10: same mistake, 3 builds, one boot loop (`notes/plugins.md:305-316`) | **Yes, in use** (V): 28 + 292 B code left. This is the technique that ran out |
| 2 | EP7 | Overwrite tables of a feature the body lacks ("dead EVF gamma tables") | Stock data of absent hardware | Only reference is one pointer word per table, build-checked; argument "no EVF on this body" is I (EP7 `docs/CODE_SPACE_MAP.md:35-50`) | Several KB in 256 B tables, used for code and data | None reported; camera-proven since their test 11 (`docs/CODE_SPACE_SURVEY.md:185-186`) | **Partly** (V): our dead 3D-engine helpers (7,237 B, 7 pieces, segment 3) and reclaimed debug strings are the same class; they are USABLE-DATA, not yet code-proven |
| 3 | EP7 | Make a debug feature dead by construction: point the shell's `sdk api` table word at a `ret0` stub, reuse the 1,138 handlers | Stock code of a serial-console-only command | Reference scan of the range (code immediates, rel branches, data words), then 3 data-word edits so no input can enter it (`docs/CODE_SPACE_SURVEY.md:63-134`) | 205,733 B code + 13.6 KB table (`:37-39`); 8 KB + 64 KB claimed (`docs/CODE_SPACE_MAP.md:231,237`) | Code placed there ran on the camera (loader re-laid in that claim, readout `7/0`: `docs/PLUGINS.md:294,319`). Section loads 6th, so no early hooks (`CODE_SPACE_SURVEY.md:127-129`) | **Yes** (V): our `sdk` sub-command table 0x7EBF0FA0 entry 18 `api` → dispatcher 0x7E9A074B; the word at 0x7EBF1034 is the only reference to it on all 4 aliases at any alignment. Handlers 0x7E9A171D–0x7E9BFA7E = 123,745 B in segment 2. Not triaged: 1,363 raw windows into that range from outside it and outside 0x7EBFxxxx |
| 4 | OM3 | Grow a section's load: raise the loader's end immediate so more of the 0xFF gap is copied | ROM padding that stock leaves in flash | Static: the immediate is the only reference to the end value (`research/NOTES.md:683-685`). Camera probes GX1–GX4: pattern in the new range + checksums of the other gaps written to a card file at every half-press | +4 KiB, +64 KiB, +256 KiB, then the whole 1,006,208 B gap; 0 bad words over photos, bursts, 4K video, Wi-Fi (`research/NOTES.md:795-827, 2437-2442, 2955-2977`) | None after the probes. The unloaded gaps hold leftover RAM, not 0xFF (`:803-806`) | **Yes** (V), see §3 |
| 5 | EM10 | Same, through a section descriptor table: 2 changed bytes end section 1 at 0x7DD00000 | ROM padding | Emulator rebuilt to load memory as the camera does; camera boots (`tools/patch.py:17-23`; `notes/plugins.md:271`, build adabit18) | 403,456 B (OFA `docs/tooling/e-m10/PLUGINS.md:39-41`) | As row 1 | **Yes** (V): ours are immediates, not a table |
| 6 | EP7 (proposal) | Same idea, not probed | ROM padding | Static only; "risk HIGH: boot path" (`docs/CODE_SPACE_SURVEY.md:136-181`) | 128–272 KB | Found a stock boot staging buffer inside image-span RAM after the last section (`:150`) | Our tail 0x7F14B820–0x7F1A0FE0 has the same unknown (I) |
| 7 | EP7 | Code file on the card → heap block → run (`EP7MOD/PLUGIN.BIN`) | Card file read into one 16 KB malloc block at the first half-press; executed through the cached alias | Emulator verifier; header magic, firmware id, size, CRC-32; camera stage readout on the Firmware screen (`docs/PLUGINS.md:12-21, 81-90, 287-294`) | 16,384 B (pool block size) | Loader camera-proven; the features built on it were shelved (`docs/PLUGINS.md:3`). Stubbed malloc hid pool exhaustion; a stale "ready" mark in a fresh heap block (`:267-275`) | **Parts exist** (V): scheap `large` pool 16,384 B × 40 at 0x6009A540, alloc 0x7E507325 / free 0x7E507333; file clients fopen 0x7E5C52DC, fread 0x7E5C536F, fclose 0x7E5C5308 (FILECLBK). No loader exists; it needs ~0.4–0.7 KB of resident code first (I) |
| 8 | OM3 | Relocatable code block appended to a card file (`GUIDES.BIN`), resident stubs call into it | Card file in a malloc block; relocation list applied at load | Tag = part of the image SHA; emulator compare with a direct link (`docs/DEVELOPER_NOTES.md:279-291`) | Block 3.7–6.6 KB inside a 16,448 B malloc cap (`research/NOTES.md:681, 3471-3473`) | Heap is small (~45 KB pool) and ran out (`docs/DEVELOPER_NOTES.md:311-314`); a return word overwrote the block's own code (`:315-316`). They later moved to row 4 | As row 7 |
| 9 | EM10 | Plugin loader: up to 6 relocated `.EMP` files from the card into an *unloaded gap used as a RAM arena* | Card files; the arena is image-span RAM that stock never loads or writes (0x7E600000–0x7E6A0000) | "No code refers to either range; emulator sees no writes through boot, live view, menus" (`notes/plugins.md:214-218`); filled through the uncached alias, run from the cached one (`plugins/loader/loader.c:33-37`) | 640 KiB arena; a 128 KB plugin with a TLS stack runs (`notes/network.md:222`) | File calls from a GUI callback froze the camera, moved to FILEFGND (`notes/plugins.md:267`, OFA `PLUGINS.md:32-35`); word writes at unaligned relocation sites killed the camera, the emulator did not fault (`notes/plugins.md:318-327`); the gap at the end of block 0 is a firmware buffer (`:218-219`) | **Yes** (V for the RAM: §3.11 of our map says the ranges are RAM; V that no known write range overlaps block 0's span, map §2). Needs a resident loader (row 7) |
| 10 | OM3 | Load at power-on from a worker task instead of a user action | – | Emulator + camera | – | Rare freeze at start-up; removed in v0.27.1 (`docs/SD_LOADER.md:3-8`). EP7 rejected boot-time triggers for the same reason (`docs/SD_BUNDLES_V2.md:26-31`) | Do not copy. Trigger on a user action after boot |
| 11 | EP7, OM3 | Runtime state in a kept heap block or proven-writable .bss padding, never in the loaded image | RAM allocated at run time | EP7: a byte store into loaded section RAM crashed on the first half-press; the same path storing to .bss passed (`docs/SD_V2_CRASH.md:55-56`, `docs/SD_BUNDLES_V3.md:12-28`) | 1 KiB block (EP7), same on OM3 | See left. EM10 and PEN-F do store into loaded padding through the uncached alias (EM10 `notes/plugins.md:214`; OFA `layout.ld:9,31`), so this is body- or cache-specific | Unknown for the E-PM2 (I). Keep our rule: state in heap or .bss |
| 12 | ML (Canon) | `autoexec.bin` from the card; the boot code relocates the start of the firmware, patches the copy so the OS heap starts after ML's BSS (or the resource pool ends earlier), then starts Canon's init | RAM taken from the firmware's own allocator before it is initialised | Per-model constants; size check before patching (`boot-d45.c:41-51`, `boot-d45-ch.c:45-90`, `boot-d678.c:165-200`) | Hundreds of KB | Needs a boot flag in ROM and a card boot path that Olympus bodies do not have | **No card boot path** (I: the only power-on card read we know is the OK+power updater). The idea "shrink a pool" maps to the scheap table 0x7E7348E4 `{base, payload, count, magic}` (V bytes), but that only yields RAM, which rows 7/9 already have |
| 13 | CHDK (Canon; not fetched) | `DISKBOOT.BIN` loaded by the stock loader; heap start moved up (`MEMISOSTART`), later Canon's ExMem pool | As row 12 | Per-model | 100s of KB | – | No |
| 14 | Nikon Hacker, Panasonic PTool (not fetched) | In-place byte and parameter patches of the update file; no new code area | Existing bytes | Checksums; emulator (Nikon) | 0 | – | That is our data-patch mode |
| 15 | Samsung NX, Sony OpenMemories (READMEs fetched), Fujihack | Linux shell scripts / Android apps / USB code injection | A general-purpose OS on the body | – | – | – | No OS. Nearest thing: row 16 |
| 16 | E-PM2 stock | BASIC interpreter + `.RCU` scripts with `api(code,a,b)` | Script text from `RCUOLYMP/R0240001.RCU` (≤ 16 KiB), stored in flash, auto-run when it starts with `ucr.` | – | 16 KiB of script | – | Exists (V, feature map 01 §4, 10f §2), but the card load is reachable only from the gated debug menu or the shell, it writes flash, and it runs at every start of overlay A. **Not recommended** |

## 3. The load-extension facts for the E-PM2 (V unless marked)

Each load computes `size = end − start` from two immediates and calls the flash reader:

| Load | End immediate (file bytes) | Other references to the end value (4 aliases, any alignment) | Gap after it | New read size if the whole gap is added |
|---|---|---|---|---|
| kernel (reset code) | 0x7E421203 = 0x7E4C9800 | none | 215,040 B | – (do not touch) |
| segment 1 (boot task) | 0x7E44A076 = 0x7E881000 | one data hit 0x7E4B470E (flash-uncached alias) | 364,544 B | 0x3DC000 |
| segment 2 (Usr1) | 0x7E504BF4 = 0x7ECB1000 (`mov` at 0x7E504BF2) | one data hit 0x7E7ABF3A (flash-uncached alias) | 108,544 B, ends at segment 3's start | 0x3D6000 |
| segment 3 (Usr1) | 0x7E504D5E = 0x7F034000 | none | 163,840 B, ends at overlay A's start | 0x390800 |
| usr1-third (Usr1) | 0x7E504FC0 = 0x7F119000 | none | 204,800 B, ends at the SRAM image | 0x4B000 |

- The three Usr1 loads call 0x7E451306 with d0 = size, d1 = 0x103, a0 = uncached destination, a1 = flash
  source; the function sends a request to a service task and waits. Its size limit was not traced.
- **The largest stock read is segment 2 itself (0x3BB800).** Any growth of segment 2 asks the reader for more than
  stock ever does; growing segment 3 by its whole gap, or usr1-third, stays below that size.
- The flash source of every copy follows one rule (map §1), so the gap bytes come from the same block-0 offsets
  of the update file. That the updater writes those offsets to flash is I (the block is one checksummed unit).
- Usr1 runs on a normal boot only; on the firmware-update reboot path it does not run (map §1 hand note, not
  tool-checked). The updater code is in segment 1 (0x7E5434EA–0x7E544A9F, 0x7E8808C0–0x7E880E84). So a changed
  Usr1 immediate is a byte in segment 1 that the recovery path loads but does not execute (I).
- Segment 2's gap has 20 untriaged pointer windows (map TSV row 0x7ECB1003); segment 3's and usr1-third's gaps
  were not scanned one by one here.

## 4. Ranked recommendations for more code space

**1. Promote the dead 3D-engine code to code space (7.2 KB, segment 3).** Technique 2. The bytes are stock
code, so the memory is executable; all checks already pass as data (map §3.6, 7 areas).
Next step: one camera test of a spec that jumps from an existing, camera-tested hook into a few bytes placed in
one area (for example 0x7EE541B3–0x7EE548B1) and returns; then `freespace.py` can mark the area USABLE-CODE.
Risk: low. No boot-path byte changes; segment 3 loads 6th, so only hooks that run after Usr1 may call it. If
the "dead" proof is wrong, a 3D GUI effect crashes, not the boot.

**2. Cut `sdk api` and reuse its handlers (up to 123 KB, segment 2).** Technique 3; EP7 ran code in the
equivalent space on the camera. We already reuse this shell's help strings for data.
Next step (static only): (a) triage the 1,363 raw windows into 0x7E9A171D–0x7E9BFA7E the way the map does
(operand / straddle / noise); (b) find the 635-entry api table and its switch tables and confirm the dispatcher
is their only reader; (c) settle open item 8 of feature-map 06 (a second `Class::method` dispatcher through the
.data copy at 0x602B0EF0); (d) design the single data edit at 0x7EBF1034 → a `clr d0; rets` stub and check the
caller's call form. Then claim a small aligned slice (8 KB) with stock guards, as EP7 did.
Risk: low to medium. No boot-path change. The shell is reachable from UART and from USB ADJ op 0x902B (feature
map 10f §1), so a missed entry is a crash only for someone driving the debug shell. Segment 2 loads 5th.

**3. Grow a Usr1 load into its 0xFF gap (108–205 KB).** Techniques 4/5; camera-proven on the OM-3 and E-M10,
unproven here. Prefer **segment 3's end (0x7E504D5E, +163,840 B)** for the first probe: one reference, and the
read stays smaller than the largest stock read. Segment 2's gap (the "one immediate at 0x7E504BF2") is next to
our current code but makes the reader's largest request larger still.
Next steps: (a) static: trace 0x7E451306's service for a length or chunk limit and alignment (all stock sizes
are multiples of 0x800); triage the pointer windows into the chosen gap; confirm from the update-file layout
that the gap offsets are written to flash; (b) decide the readout, since we have no card-write diagnostic: the
simplest is a stock string pointer redirected to text placed in the new range, visible in a menu; (c) probe
+0x800 only, keeping `de 00 00` and a 16 B guard, one change per flash, then exercise stills, movie, playback,
art filters, USB, long sessions; (d) only then place code.
Risk: **high, boot path.** The edit is in Usr1, which every normal boot runs before the GUI exists. A reader
fault or a RAM owner in the gap means a boot loop or a late crash. Recovery by OK + power should still work
because that path does not run Usr1 (I), but recovery from a boot loop has never been tested on the E-PM2
(`docs/flashing.md`; only a text-patch state was recovered). Do not touch the kernel or segment-1 end
immediates: both run on the recovery path, and segment 1 holds the updater.

**4. Code from the SD card into RAM (16 KB per heap block, or 100+ KB in an unloaded gap).** Techniques 7–9.
This adds space without loading more flash, and a bad file is fixed by deleting it.
Next steps: (a) it needs resident code first (EP7's loader is 564–688 B, OM3's worker 391 B), so do rank 1 or 2
first; (b) choose the trigger: a user action after boot, in a task that may block on FILECLBK. Find which task
runs our camera-tested hook 0x7E56C6A5 and whether stock code calls the fileif clients from that task; (c)
static check that the scheap `large` pool has free blocks at that moment (40 blocks; count the peak users), or
use a gap as the arena (0x7ECB1010–0x7ECCB800, nothing loads or is known to write it); (d) fill through the
uncached alias and run from the cached one, byte-wise relocation only, and add a stage readout.
Risk: medium, none at boot if the trigger is a user action. Known traps from others: file calls from the wrong
task hang the camera; a boot-time trigger froze the OM-3; stubbed services in an emulator hide pool exhaustion;
unaligned word stores fault on the camera but not in emulators. A plugin is unrestricted code: it must never
reach flash-write or updater services.

**5. Not recommended:** the BASIC/RCU route (flash write, gated entry, runs at every start); pool shrinking
(yields RAM only); the 40 KB of kernel-area 0xFF and the pre-reset area for code (they execute on the reset
and recovery path); any card read at power-on.

## 5. Limits

- External camera results are author reports; none was reproduced here. E-PM2 "V" items are static reads of
  stock bytes; nothing in §3 or §4 was run on a camera or in the emulator.
- CHDK, Nikon Hacker, PTool and Ricoh rows are from memory because the sites were blocked; treat them as leads.
- Whether rodata or heap RAM is executable on the E-PM2 has no direct evidence. EP7 and EM10 run code from heap
  and gap RAM on sibling bodies with no MMU set-up reported (X), which makes it likely (I).
