# The candidate `films-start-texts` (2026-11-21)

Items 1 to 3 of [plan.md](plan.md). Build `data/builds/films-start-texts.json`, sha256
`d8eef426227be0f7fc4925626f519afe33178e12205fad97d6701a56bcb39ba0`. Not flashed. Labels: V verified in the emulator
or by reading, I inferred, U unknown.

Flash: `epm2flash films-start-texts d8eef426227be0f7fc4925626f519afe33178e12205fad97d6701a56bcb39ba0`
Go back: `epm2flash films-twelve-off 600041b3d24c67116004f7869d001a9b342599f0c081cf444afc572fcfac09ec`

## What changed against films-twelve-off

1,613 bytes of block 0: 101 in segment 2, 1,512 in segment 3. None in the pre-reset range, the kernel range,
segment 1, the data image or blocks 1 to 3 (V, byte diff).

- **`card-looks-8`** (`gen/stock-films/loader.s`):
  - `STORED` (segment 3, 0x7EE538F5): verify the stored film file, apply the tables and the switch lists, refresh
    the stage caches. `C_START` calls it and goes on to the original constructor.
  - The task at the first GUI state verifies and applies the stored file again, as films-twelve-off does (the same
    bytes), then writes the texts and names. A first version skipped this when the early apply had passed; the
    review showed that it then trusted a store nobody had checked again, so the camera-tested path stays.
  - The text table has 8 rows, was 4: string ids 1505 Peaking, 1506 its help, 1500 White, 1503 Lowest S/S Setting,
    1504 its help, in English, from block 0. The language's own Off and colour names stay.
  - `FLAGS` and `T_END` are no longer fixed addresses; the spec's `_symbols` gives them to the log's generator.
- **`log-menu-3`** (`gen/log-menu/mkspec.py`): `T_CTOR` (segment 2, 0x7EBF2E68, 47 B). The last word of segment 3's
  constructor table (0x7F033B78, was 0x7EEC05FF) points at it. It records `seg_loaded`, calls `STORED`, records
  `film_applied` with the result, restores the registers and MDR and jumps to 0x7EEC05FF. Dictionary id
  `afe27672d672fc95`; events 1801 and 1802.
- **`tools/freespace.py`**: a spec that edits an earlier version of a spec in place is no claim against the later
  version (the owner's decision, 2026-11-21). `movie-ab` and `log-movie-time` edit the id bytes of `log-menu-2`.

## Emulator results (V)

- `boot-test` and `update-path-test` against films-twelve-off: PASS (empty store).
- `boot-test` with twelve film simulations stored: 24 time stamps later by 16.7 to 19.0 ms, and three counts lower
  (S-GIOTIMER 3213 to 3195, S-GIOIN 3173 to 3155, idle 9109 to 9005). Read by a person, as criterion K1 asks: this is
  the early apply's work, about 17 ms, inside task Usr1. The application starts that much later. Accepted for the
  camera test; the sheet asks if the start feels as before.
- `filmcheck.py`: PASS. `hookcheck.py`: the same 7 waived hooks as films-twelve-off. `freespace.py check`: PASS.
- Six start-up scenarios (twelve films loaded; restart with no card; a partial file; an empty file; a bad file;
  nothing stored): every end state equals films-twelve-off's.
- Order at a start with a stored file, lab ms: constructor 20.57, early apply 21.98 to 39.28, application init 39.28,
  first GUI state 53.08, the task 60.23 to 78.89. films-twelve-off applies at 38.8 to 61.6, after its first GUI state.
- 14 corrupt stores, and garbage written into a valid store after the early apply: stock tables, clean names, as
  films-twelve-off.
- Stack: 128 B of Usr1's 0x800. One exit, the jump to 0x7EEC05FF.
- Menu crawl: English is byte-equal to films-twelve-off. German and Japanese differ only in the two rows: "Peaking"
  with Aus / White / Rot / Gelb / Blau, and "Lowest S/S Setting"; both help texts in English; nothing cut off.
- Decoded log of an emulator start: `seg_loaded` 18.9 ms, `film_applied store_ok 1` 37.7 ms.

## Only the camera can show (U)

- Whether the settings bank is in memory at the constructor. If it is not, the early apply finds no file and the
  first GUI state applies it, as today.
- The order of `film_applied` and the first `film_stage` event (S1), and the margin between `seg_loaded` and the
  first colour stage job (R1). The emulator has no live view.
- A stage job on the other processor while the switch lists are written; sleep and wake; the quick start with the
  application about 17 ms later.

## Known and accepted

- "White" and both rows' labels and help texts are English in every language.
- Each start adds 4 records to the log's ring with Debug Log Off (2 before). They reach the card only when the
  Debug Log is On before the start.
- `hookcheck.py` does not see `T_CTOR`: the table word is a data pointer. Its three targets were read by hand: the
  log's record routine (kernel area), `STORED` (segment 3) and 0x7EEC05FF, all after both segment copies.
- `docs/reference/logging.md` describes the pinned build's log spec and id. It changes when this build is pinned.

## Camera result (2026-11-21)

Flashed by the owner. `docs/camera-log/2026-11-21-films-start-texts.md` has the row. Labels here: C camera.

| Event, three starts with 12 film simulations stored | Time after power-on |
|---|---|
| `seg_loaded` (the segment copies have ended) | 362 to 365 ms |
| `film_applied`, `store_ok 1` | 430 to 433 ms |
| first `film_stage` (CPU 1) | 1,646 to 1,647 ms |
| first GUI state | 1,703 to 1,763 ms |
| the loader's task at the first GUI state | 2,161 to 2,577 ms |

- **S1 holds (C).** The stored file is applied 1.2 s before the first colour stage job. In films-twelve-off the
  loader ran at about 2.2 s, after the first stage job at about 1.7 s.
- **The settings bank is in memory at the constructor (C)**: `store_ok 1` in every start.
- **R1 (C): the margin of the 7 film hooks from segment 1 into segment 2 is 1.28 s** in these three starts, lever
  start, mode P. Not measured: a start with the shutter held, a start from sleep.
- The apply takes 68 ms on the camera (17 ms in the emulator).
- **T1, T2 in Chinese (C):** no unrelated Olympus text. Peaking, White and Load Looks are English, as built. The
  owner counts that as incomplete: a translation is a new piece of work.
- Three photos after power-on have the film simulation's look and name.
