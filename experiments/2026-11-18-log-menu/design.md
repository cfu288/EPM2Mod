# Log as a menu setting: requirements and first findings (2026-11-18)

The owner's goal: logging is a setting in the camera's menu, so one firmware can write `EPM2LOG.BIN` when the
user turns it on. Today the log needs a separate debug build for each firmware (`builds/debug-log-*.json`).

Status: requirements drafted, owner's answers pending (questions at the end). No build yet.

## What is true today (checked 2026-11-18)

- The pinned build `card-looks-4` has no log code. The log is the specs `patches/log-core.json` (931 bytes
  changed, 6 operations) and `patches/log-probes.json` (820 bytes, 19 operations), added only by debug builds.
  `docs/logging.md` describes the record, the file and the decoder (`epm2mod log`).
- **The log and the pinned build conflict.** `epm2mod apply` of the `card-looks-4` specs plus `log-core.json`
  fails at log-core operation 4: both specs hook the GUI state setter's trace call at 0x7ECDF6E4 (block0+0x8BE6C4).
  Both also use the dormant task USRTEST_A: card-looks loads EPM2LOOK.BIN from it, the log flushes from it.
  `docs/space-superseded.tsv` already says card-looks reuses the free code runs of the log probe build and "the
  two are never in one build".
- RAM: the log rings are at 0x7E4F9000-0x7E4FD2C0. Card-looks keeps the built-in tables at 0x7E4D0800, in the
  same RAM gap 0x7E4C9800-0x7E4FE000. Whether the two ranges overlap is not checked yet.
- Code space is short (docs/todo.md): the kernel code area has 18 bytes left, segment 2 about 722 bytes in runs
  of 120 bytes or less. Card-looks-4 put new code into a reclaimed area of segment 3 (0x7EE53830); how much of it
  is left is not checked yet.
- A menu row can be added: `patches/custom-menu-rows.json` adds Peaking (A) and Load Looks (J) to the Custom
  Menu, and Load Looks keeps its value in the dormant setting 449 (prm tag 0xD7B1), which no stock code reads.

## Requirements (draft)

1. One firmware: the release firmware carries the log code, switched by a menu row. No separate debug build.
2. The row: a Custom Menu row with Off / On, kept after power-off. Default Off.
3. Off: no record is written and no file is written. The camera works as the same firmware without log code.
4. On: the same records and file as the debug builds today (`docs/logging.md`), readable by `epm2mod log`.
5. Every feature of the pinned build keeps working with the log On and Off: film looks from the card, peaking,
   interval shooting, level gauge, menus, the update path.

## Success criteria

- L1. The emulator: boot-test, update-path-test and hookcheck pass with the row Off and On.
- L2. The emulator: the row is in the Custom Menu, its value stays after a restart, and Off writes no file.
- L3. The emulator: with On, a session writes `EPM2LOG.BIN`, and `epm2mod log --summary` decodes it.
- L4. The emulator: Load Looks still loads a file, with the log On and Off (the shared GUI hook and task).
- L5. The camera, one run: Off, shoot and use the menus, and the card has no `EPM2LOG.BIN`. On, the same, and the
  card has a log that decodes. Film looks, peaking, interval and level gauge work in both.
- L6. The release firmware's sha256 changes (new code); the old pinned build stays the way back.

## First steps (after the owner's answers)

1. Check RAM: do the log rings and the card-looks snapshot overlap? Map the free code in segment 3.
2. Design the shared parts: one GUI-state hook that calls the card-looks code and the log code, and one task that
   loads looks and flushes the log.
3. A flag (the new setting) that `log_put` and the flush read first.
4. Build a candidate on `card-looks-4`, run L1-L4 in the emulator, then plan the one camera run (L5) together with
   the release test (`docs/todo.md`).
