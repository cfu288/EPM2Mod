# Plan after the firmware review (2026-11-21)

From [NOTES.md](NOTES.md). The owner's rules: what is flashed and works is not moved; new code goes in segments 2
and 3; the kernel range gets nothing new. Labels: V verified, I inferred, U unknown.

## What is addressed, and why

| # | Accident | Effect | Kind of work |
|---|---|---|---|
| 1 | Two ways of setting menu texts. Peaking and Lowest S/S Setting patch the English blob only | In 33 languages both rows show unrelated Olympus texts (V emulator, NOTES §5) | Firmware, one flash |
| 2 | The film loader starts at the first GUI state, because each earlier attempt moved a `boot-test` time stamp | For about half a second after power-on the selected entry is its Olympus filter (V camera log) | Firmware, the same flash |
| 3 | The waiver of the 7 film hooks from segment 1 into segment 2 states a reason that the camera log contradicts | A crash at power-on is possible if live view starts before the segment copy ends; margin U | Measure in the same flash; correct the waiver now |
| 4 | `filmcheck.py` looks at 7 colour stages of at least 16 | A third fault of the kind of 2026-11-18 and 2026-11-20 would go unseen | Emulator, no flash |
| 5 | `boot-test` fails a build on a time stamp that moves by more than 0.2 ms | A test rule decided where the loader runs | Emulator tool, no flash |
| 6 | The log's generator hooks the film loader at two fixed addresses (`FLAGS`, `T_END`) | Every later loader must keep them | Generators, no flash, same bytes |

Not addressed (works; a change costs a flash and a re-test for nothing a photographer sees): code in 88 runs, the
30 ART BKT hooks, 24 tone tables per entry, 1,906 dead menu bytes, what sits in the kernel area.

## Acceptance criteria for the flash (build `films-start-texts`)

- **T1.** With the camera language set to German, and to Japanese, Custom Menu A shows the row **Peaking**, and its
  values read Off, White, Red, Yellow, Blue in that language's own words or in English. No unrelated text.
- **T2.** The same for **Lowest S/S Setting** in Custom Menu E, its value texts and its help text.
- **T3.** In English both rows read as in `films-twelve-off`.
- **S1.** With film simulations stored, the stored file is applied before the first colour stage job after
  power-on: the Debug Log shows the apply's end before the first `film_stage` event.
- **S2.** Load Looks → Load, an empty file, a bad file, no card, and a restart behave as in `films-twelve-off`
  (film criteria F1, F2, F4, F5 of `experiments/2026-11-18-stock-filters/design.md`; names in the menus; EXIF name).
- **R1.** The Debug Log holds the time at which the segment copies ended and the time of the first colour stage job
  of the same start. The margin of item 3 is the difference.
- **K1.** No byte changes in the pre-reset range, the kernel range or segment 1. `emulator/hookcheck.py` reports no
  new failure; `boot-test`, `update-path-test`, `filmcheck.py`, `tools/freespace.py check` and the menu crawl pass.
  A `boot-test` time-stamp difference is read by a person and written down.

## Design

- **Start point (items 2, 3).** Segment 3's constructor table (0x7F033AC8, 45 entries, walker 0x7E44B6B0, called by
  Usr1 at 0x7E504D81 after the segment-3 copy; V emulator). Its last entry 0x7EEC05FF is re-pointed at a routine in
  segment 2 or 3 that (a) writes a log event "segments loaded", (b) applies the stored film file if it passes the
  loader's own checks (tables and switch lists; no card, no GUI call, no text), (c) runs the original entry.
  Context: task Usr1, stack 0x800. The first GUI state then does only what needs the GUI (names, texts).
  A fault in this routine stops a normal start. The update start does not run Usr1, so a card update recovers it.
- **Texts (item 1).** The loader already re-points string ids in the loaded language's RAM table and does it again
  after a language change. The Peaking and Lowest S/S ids join that list, with their English texts in block 0.
- **No skip switch.** The "OK held at power-on" byte (NOTES §2) is not used: the update start already skips Usr1.

## Order

1. No flash: items 4, 5, 6, and the waiver file's reasons (item 3).
2. The candidate build for items 1, 2, 3; every gate of K1; an adversarial review of the assembly.
3. The owner flashes it once. The sheet lists T1–T3, S1–S2 and R1 with the menu paths.
