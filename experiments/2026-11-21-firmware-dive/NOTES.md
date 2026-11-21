# What in the firmware we had not explored (2026-11-21)

Seven read-only reviews of stock firmware 1.6 and the pinned build `films-twelve-off`, one per area, and two
verifier passes that tried to refute the strongest claims by other means. Nothing was flashed. No build was made.

Labels: V verified (bytes, disassembly or an emulator run), I inferred, U unknown. "Emulator" is never a camera
result: it has no live view, no capture, no sleep, no NMI, and its flash copies take about 1 ms.

## 1. Space

Proven code space left: 528 B (code-space map §4). The pinned build's 24,046 changed bytes sit in 88 runs.

Rank by what a mistake costs, not by size (`docs/dev/feasibility.md`, "Where code may go"). The kernel range and
segment 1 are in memory on the update start; segments 2 and 3 are not. A wrong "free" verdict in segment 2 or 3 is
recovered by a card update. In the kernel range it may not be. So of the areas below, the `sdk` handlers come first,
and G2 and the load-range words are a last resort for code that must be loaded early.

- **G2, 0x7E440010–0x7E448000, 32,752 B of 0xFF, in the kernel range the reset code copies.**
  - V emulator (two independent scripts; data watch in all four aliases and an executed-pc check, both cores): no
    access in stock boot, the update path, and menus and playback.
  - V: its five "pointer hits" are bytes inside the touch-controller image 0x7E7F0F78–0x7E7FAB33 and the face-detection
    model data 0x7E85CEFC–0x7E86DD5F. A pattern in the whole run passes `boot-test` and `update-path-test`.
  - I, the one risk: it is the low part of CPU1's 64 KiB vector page (base word written at 0x7E426851; CPU1's stubs
    are at 0x7E448000). The page start 0x7E440000 holds 16 zero bytes. If a CPU1 NMI or trap enters at page + 8, it
    runs into 0x7E440010. Leave 0x7E440010–0x7E440020 as 0xFF and the behaviour is stock's.
  - U: whether CPU1 ever takes an NMI, and sleep and wake.
- **The debug shell's `sdk` handlers, 0x7E9A171D–0x7E9BFA7E, 123,745 B, segment 2.** V: every aligned pointer into it
  is in the `sdk` tables 0x7EBF103C–0x7EBF9F4C. It is dead after those table words point at a stub. Cost: the shell's
  `sdk api` commands, which run in the emulator (§7).
- **The load ranges can grow.** V emulator: the kernel copy's end is one word at 0x7E421203 (0x7E4C9800), segment 2's
  end one word at 0x7E504BF4 (0x7ECB1000); each occurs once; a raised end loaded a marker. Free for code in the
  kernel gap: 0x7E4C9800–0x7E4D0000 (26,624 B). The rest of that gap is the mod's RAM (film tables, log ring), which a
  raised end would fill with 0xFF at each reset. U: the real flash readers (0x7E4217E6, 0x7E451306) were not followed.
  The kernel word is in the reset code: a fault there is a boot loop.
- No run-time checksum of the code was found (V emulator: no read of any blank range; I for the rest).

## 2. Start-up and lifecycle

- **A start point with no jump over code.** V emulator: after each segment copy, Usr1 calls the constructor walker
  0x7E44B6B0. Segment 3's table is 0x7F033AC8, 45 pointers (base and count are immediates). The last entry
  0x7EEC05FF does not depend on order. Pointed at a routine that chains to it, the routine ran after the segment-3
  copy and before the application init; `boot-test` and `update-path-test` pass. Context: task Usr1, priority 11,
  stack 0x800, banks loaded (I), no card yet. It never runs on the update path.
- **The waived film hooks rest on timing.** V static: Usr0 sets "Flg-ThroughStart" at 0x7E504A47 before it starts
  Usr1; USR_FAST (priority 6) starts live view at once and preempts Usr1 (priority 11), which copies segments 2
  and 3; nothing waits for the copies. The quick-start check 0x7E502674 refuses ART and SCN mode but never reads
  Picture Mode, so P with a film simulation takes the fast path. The art-matrix hook 0x7E56C6A5 is on the main path
  of 0x7E56C603, and the camera log shows that stage ran at power-on for live view. So the reason in
  `emulator/hookcheck-allow.tsv` for that row ("did not run before segment 2 was loaded") is a test result on one
  path. The pinned build has 7 such hooks. The camera has not failed yet. U: the margin.
  Probe, no new hook: write the firmware's boot-mark buffer (0x604DE534, count 0x604DEB74) and the first stage time
  to the Debug Log.
- **The half second with the Olympus filter at power-on.** V notes (`2026-11-17-card-looks/design.md` line 374): the
  loader task has priority 13, lowered from 11 because `boot-test` time stamps came 5.5 ms late (tolerance 0.2 ms);
  the work is about 15 ms. The task starts from the first GUI state. U: how the half second splits between that wait
  and the task. The constructor start point above would run before both.
- **An unused "OK held at power-on" byte.** V emulator: 0x7E505694 clears 0x602A9B54 when OK is held; with no update
  file the start goes on normally with the byte 0. A start routine can test it in about 10 B.
- The update path runs the reset code, the kernel, all of Usr0, the updater (0x7E5434EA–0x7E544A9F,
  0x7E8808C0–0x7E880E84) and the file system (V static). A fault in anything Usr0 runs makes the updater unreachable.

## 3. Hooks

82 jumps over stock code: films 32 (30 in ART BKT), log 24, peaking 16. The firmware has no registration mechanism
that replaces most of them (V static: task tables full except USRTEST_C and _D; no cyclic or alarm rows; the shell
needs UART or USB).

- The app trace function 0x7E9670E9 (11,491 call sites): one hook keyed on the return address could replace 8
  (interval and MF Assist probes). Cost: a compare on every trace call, not measured.
- The art pass table 0x7E859E94 (12 B rows `{fn, mask, bit}`): two words could replace 5 peaking hooks, with about
  700 B of copied code. Not built.

## 4. Film mechanism

- **ART BKT: 30 hooks can become 6** (PARTLY verified, static). The composer 0x7E5A7591 and the list builders
  0x7EA7633A, 0x7EA9528D compare the current mode with each entry's value and write the value into an output list
  (composer: 18 B records at job+17154, one exit 0x7E5A7914; builders: lists at obj+260 and obj+196). Map hidden to
  stock at entry and stock to stored at exit. Details that differ per function: the composer passes d3 to
  0x7E5A791D; the second builder keeps the mode in (4,sp) and its exit hook must move a pc-relative call. One
  behaviour difference when the Picture Mode setting and the value-list byte disagree.
- **Tone tables: 24 per entry hold 15 distinct tables** (V, all 32 films): in the default record 0x7E78B39C
  c0m0 = c1m0 = c3m0 and c1m1 = c3m1, and a film table depends only on the curve and the default. 147,456 B of RAM
  become 92,160 B, and the start-up tone work falls by 37 %. `filmcheck.py` `tone_ok` must change with it.
- No single block holds the stages' table pointers (V): each setter uses its pointer at once. One hook cannot replace
  the per-stage stubs.
- Stages a still passes through that `filmcheck.py` does not cover: knee 0x7E56BDE9, noise and edge 0x7E56CB32,
  sharpening 0x7E56FA27, chroma suppression 0x7E56F113, monotone toning 0x7E56D039, rec-view gamma 0x7E56DA08, the
  pipe B art effects, gamma post-processing 0x7E56AEAF, and a third block 0x7E5625DC. For the film codes the first
  seven give blocks byte-equal to Natural (V, one synthetic job); the last two are U.
- Movies: pipe B differs from pipe A only by the 12-region stage, which films no longer use (I).
- Open, from the block check added to `filmcheck.py` the same day (V emulator, camera U): when the job's u16 at
  P+62 is 0x1000 or more, or bit 11 of P+20 is set, a film code's look word is Natural's table for that job, not the
  identity table. If P+62 is the ISO value (I), a film simulation at high ISO carries Natural's look curve for that
  ISO. Bit 16 of P+20 switches the art code off in every stage, on stock too.

## 5. Menus

The mod uses the stock forms correctly: no numeric editor exists (stock's own 99-frame list is 99 items), and the
Custom Menu table must be copied to grow (its size is in code constants).

- **1,906 dead bytes** (V): `level-adjust-row` writes two table copies (0x7EBF3000, 0x7EBF3500) that
  `custom-menu-rows-3` supersedes. Nothing points into them; with them overwritten, the menu cases and an 83-row
  crawl are identical.
- **Two rows show unrelated Olympus texts in 33 languages** (V, emulator crawl in German and Japanese): Peaking shows
  "Auto Umsch. EVF" with values Aus / "Stil 1" / Rot / Gelb / Blau; Lowest S/S Setting shows "Info Einst." with the
  EVF help. Load Looks and Debug Log are English in every language, because their texts are set in RAM at run time.
  The same run-time method would fix both rows and remove 664 B of block-1 edits.
- Item lists filled in RAM by a loop would save about 5.7 KB of tables (I; needs about 6.5 KB of RAM and 150 B of code).
- Dormant slots not in earlier notes: panel 651 "Mode Dial Function" (settings 490–493, lists 652–655), setting 521
  with list 659, page record 582.

## 6. Settings and state

- No native blob store fits the 20 KB film file; the EEROM tail stays (I: no reset touches it).
- Dormant setting ids that no reset touches: 531, 532, 583, 697 (I: constant scan only).
- `scheap` in the emulator through boot, menus and playback: large pool 16 of 40 in use. Capture and movie peaks: U.
  The film tables stay in the fixed gap.

## 7. Olympus's own debug facilities

- **A card file overrides settings on stock firmware** (V emulator, two independent runs; camera U). Mount
  0x7E5B0C1A calls 0x7E5B108F; a root folder `PARAMDT` with `CP??????.CSV`, lines `NAME,0xTAG,COUNT,VALUE...`
  (parser 0x7E456667), fills a RAM override index 0x603A8E38 that the tag lookup 0x7E45726D reads first. No gate
  found. A power cycle clears it (V emulator); a card swap does not. 703 of 884 tags read before the mount are not
  read again. U: what factory adjustment tags could do; no bound on the worst case was found.
- The debug shell runs in the emulator with two stand-ins for the console (V): `ps`, `sc heapshow`, `prm getval`,
  `exp still info`, `sdk api`. On a camera it needs the UART or a USB op.
- Stock has an error recorder (0x7E426D4B) with a 16 KiB text buffer and a flush to a file in folder `DBG`
  (0x7E53AC6F), gated by byte 0x60503A49 (V static, not run).
- Nothing the mod overwrote is still reachable in stock (V for the exp printers, the `sdk` name list, USRTEST_A).
  The `exp still info` dump is lost as a probe in the pinned build.

## 8. Not determined

Sleep and wake; capture and movie in general; the first-stage loader (not in the update file); CPU1 exceptions; the
real flash readers behind the two copies; whether `PARAMDT` works on the camera.
