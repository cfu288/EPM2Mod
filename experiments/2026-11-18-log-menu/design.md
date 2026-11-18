# Log as a menu setting: requirements and findings (2026-11-18)

The owner's goal: logging is a setting in the camera's menu, so one firmware can write `EPM2LOG.BIN` when the
user turns it on. Today the log needs a separate debug build for each firmware (`builds/debug-log-*.json`).

Status: investigation done (section "Findings"), plan in section "How to build it". The owner's answers to the
three questions at the end are pending. No build yet.

Labels: V = verified (emulator or the bytes of the image), I = inferred, U = unknown.

## Requirements (draft)

1. One firmware: the release firmware carries the log code, switched by a menu row. No separate debug build.
2. The row: a Custom Menu row with Off / On, kept after power-off. Default Off.
3. Off: no file is written. (Proposed change from "no record is written": see finding 6.)
4. On: the same records and file as the debug builds today (`docs/logging.md`), readable by `epm2mod log`.
5. Every feature of the pinned build keeps working with the log On and Off: film looks from the card, peaking,
   interval shooting, level gauge, menus, the update path.

## Success criteria

- L1. The emulator: boot-test, update-path-test and hookcheck pass with the row Off and On.
- L2. The emulator: the row is in the Custom Menu, its value stays after a restart, and Off writes no file.
- L3. The emulator: with On, a session writes `EPM2LOG.BIN`, and `epm2mod log --summary` decodes it.
- L4. The emulator: Load Looks still loads a file, with the log On and Off (the shared GUI hook).
- L5. The camera, one run: Off, shoot and use the menus, and the card has no `EPM2LOG.BIN`. On, the same, and the
  card has a log that decodes. Film looks, peaking, interval and level gauge work in both.
- L6. The release firmware's sha256 changes (new code); the old pinned build stays the way back.

## Findings

Scripts: `scripts/overlap.py` (each op of a spec against the pinned build), `scripts/free_after.py` (free bytes
after the pinned build and the given specs), `scripts/run_447.sh` with `scripts/prm447.mjs` (setting 447 in the
emulator).

1. **Only two log operations clash with the pinned build (V, overlap.py).** Of `log-core`'s 6 operations and
   `log-probes`' 19, all but two find their expected bytes on `card-looks-4`, in bytes that no pinned spec covers.
   The two: the hook on the GUI state setter's trace call at 0x7ECDF6E4, and the task-table entry of USRTEST_A
   (0x7E439C80). Both are `card-looks-4`'s.
2. **The GUI hook can be shared without changing `card-looks-4`'s code (V, the source of both generators).** Both
   routines end with the displaced trace call and a jump back, and both restore every register they use. Plan: the
   hook jumps to the log's T_GUI; the log's T_GUI ends with `jmp` to card-looks' T_GUI (in place of the displaced
   call and the jump back); card-looks' T_GUI is unchanged and returns as now. The only changed pinned bytes are
   the 5 bytes of the hook (the jump's target). The hook is in segment 2 and both routines are in segments 2 and 3,
   which hookcheck allows.
3. **The flush gets its own task: USRTEST_B (V, task table bytes).** USRTEST_A to D (ids 0x90 to 0x93) are rows of
   the CPU0 task table at 0x7E439C74 + 0x14 n, all with priority 11 and stack 0x800, and nothing in stock starts
   them (feature map 10f, section 6). USRTEST_B's entry word is at 0x7E439C94 (block 0 + 0x18C74), stock
   0x7E501CE7. The log's T_GUI then starts id 0x91. Two tasks can then do file calls at the same moment (a Load in
   the menu while a flush runs); the fileif calls go through the one FILECLBK task (I). The log's T_GUI can also
   skip a flush while card-looks' busy flag is set (one byte read, 8 bytes of code).
4. **RAM does not overlap (V, the generators).** Log: rings 0x7E4F9000-0x7E4FD040, state and block buffer
   0x7E4FD040-0x7E4FD2C0. Card-looks: 0x7E4D0000-0x7E4ED000 and the EEROM bank tail. The log uses no EEROM.
5. **Code space is enough for the core and the probes (V, free_after.py).** After `card-looks-4` + `log-core` +
   `log-probes`: kernel range 107 B free (largest run 67 B), segment 2 code area 819 B in 14 runs (largest 254,
   192, 161 B), segment 3 data over 3 KB (1,008 B at 0x7EE3CBF2, 973 B at 0x7EE544E4). With the core only, the
   kernel range keeps 504 B. The menu row's new code (finding 8) is about 100 B in segment 2.
6. **Gate the file, not the records (proposal, I).** `log_put` runs on both CPUs and in the kernel range, so a
   switch there needs a RAM flag (CPU 1 cannot read a setting) and kernel bytes. If only the flush reads the
   setting, the kernel and CPU-1 code stay as camera-tested, records before the GUI starts (boot, early firmware
   errors) are kept, and a user who turns the log On after a problem gets the last 512 records of each CPU in the
   next flush. With Off, the records stay in RAM and nothing is written to the card. The probes then run with Off
   too, as in every debug build on the camera.
7. **The row's setting: 447 with the stock picker panel 608 (V).**
   - Panel 608's list descriptor 0x7F00BFCC: setting 447 (prm tag 0xD791, MODE bank, one byte), two items: Off
     (text 1371, value 0) and On (text 198, value 1). These texts exist in every menu language (I: stock texts).
   - No stock code reads or writes setting 447 with a constant id (`07-settings.tsv`). Setting 446's panel 607 is
     Peaking's list now; 449 is Load Looks; 448 (panel 609) is the other free one.
   - Emulator, pinned build (`run_447.sh`): 447 reads 0 (Off) at start; a 1 written with the GUI's setSetting, as
     the menu writes it, reads 1 after a restart with the RAM banks kept and after a restart from flash only. The
     start does not write 447 (unlike 449, which the firmware sets to 1 at every start).
8. **The row in the Custom Menu (V for the tables, I for the rest).** As `custom-menu-rows` did: a new spec in its
   place with one row more.
   - Row `{group 9, text LABEL, setting 447, order 7, help HELP, value list 608, 0}` at the end of J, after Load
     Looks; child entry (608, 447); row constants 81 -> 82 rows, last index 81, row-state array 162 -> 164 B; rows
     in group J 7 -> 8.
   - Item table: 82 rows end at 0x7EBF2512; the free run 0x7EBF2502-0x7EBF2600 holds the 16 new bytes (V).
   - **Child list: it does not fit in place.** 82 entries + the zero entry end at 0x7EBF2898, and `card-looks-4`'s
     code starts at 0x7EBF2890. The list moves to segment 3 data (for example 0x7EE3CBF4, 1,008 B free) and the 11
     page records point at it, as `custom-menu-rows` re-pointed them. The page records are in segment 3 already
     (0x7EFFA820), so the menu reads segment 3 data (I).
   - The row's value text: panel 608 has no value -> text list (the word at 0x7F014F94 is 0). New list Off (0) /
     On (1), 72 B in segment 3 data, and the word points at it.
   - Label and help: two unused built-in EVF texts, for example 1502 ("Style 3") and 1499 (the old help of 1498).
     The log's T_GUI points them, in the loaded language's table in RAM, at English strings, as card-looks does
     for its row (about 45 B: it checks its label pointer at each call, so a language change is handled).
9. **The flush reads the setting (plan).** In the log's T_GUI, before it starts the flush: prm_get(0xD791) and no
   flush unless the value is 1 (about 16 B). The power-off flush is the same path.

## How to build it

1. `mkspec_log.py`: parameters for the task (id 0x91, entry 0x7E439C94), the tail of T_GUI (`jmp` card-looks'
   T_GUI), the setting gate and the label texts; regenerate `log-core` and `log-probes` as new specs on the pinned
   build (`log-menu-core.json`, `log-menu-probes.json`), with a new build id in `logs/`.
2. `mkspec_rows.py --log`: `custom-menu-rows-2.json` with the Log row, the child list in segment 3 and panel 608's
   value list.
3. `builds/log-menu.json` = the pinned specs with `custom-menu-rows-2` in place of `custom-menu-rows`, then the two
   log specs, then the 5-byte hook change.
4. Emulator: L1 to L4, the crawls of P and ART against the pinned build (only J differs), screenshots of the row.
5. Then the one camera run (L5) together with the release test in `docs/todo.md`.

## Open questions for the owner

1. Should the release firmware carry the log code, switched Off by default, or stay without it and keep logging in
   separate builds?
2. Where should the log row go: Custom Menu J after Load Looks, or another group?
3. Which events should be logged when On: only the core (start, firmware errors, screens), or also the feature
   probes (peaking, film looks, interval, level gauge)?
