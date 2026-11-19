# The structured log

For developers. With Custom Menu J → Debug Log On, the firmware writes event records to the file `EPM2LOG.BIN` on the SD
card. `epm2mod log` turns the file into a short report, or its events into JSON (`--json`). The design notes, the evidence and the camera test
are in [experiments/2026-11-15-log/NOTES.md](../experiments/2026-11-15-log/NOTES.md).

The pinned build has the log in the firmware, switched by the Custom Menu row **Debug Log**
(MENU → SETUP → Custom Menu → J → Debug Log → On; Off by default): `patches/log-menu-2.json`, the code of the four specs below
with an Off switch ([log-menu design](../experiments/2026-11-18-log-menu/design.md)). It was first pinned in
`builds/log-menu.json`.

## The parts

| Part | Where | What it does |
|---|---|---|
| Dictionary | `logs/events.json` | The id, name, level and argument formats of each event, and name tables for values. The camera stores no text |
| Dictionaries of flashed builds | `logs/events-BUILDID.json` | The event list of a build that was on a camera, kept when `events.json` changes |
| Generator | `experiments/2026-11-15-log/scripts/mkspec_log.py` | Reads the dictionary and writes the two patch specs |
| Generator of the release log | `experiments/2026-11-18-log-menu/scripts/mkspec_logmenu.py` | Writes `patches/log-menu-2.json` (with `--stock-films`). It imports `mkspec_log.py` |
| Log core | `patches/log-core.json` | `log_put`, `log_chg`, `log_cnt`, the flush task, and the events boot, firmware error and GUI state |
| Probes | `patches/log-probes.json` | One hook and one small routine per event of a feature |
| Timing probe of peaking | `patches/log-peaking-time.json` | Event `pk_stats`, one record per 8 runs of Key Line pass 9. Written by `mkspec_log.py --peaking-time`. It also puts the build id of `logs/events.json` into the block header |
| Probe of the save guard of peaking | `patches/log-peaking-guard.json` | Event `pk_guard`, one record per hold of the peaking latch after a shot. Written by `mkspec_log.py --peaking-guard`. It puts the build id of `logs/events.json` into the block header |
| Decoder | `src/epm2mod/eventlog.py`, `src/epm2mod/logsummary.py`, command `epm2mod log` | Reads the file and the dictionary, prints a summary, or the events as JSON |

## The record

A record has 16 bytes, little endian:

| Offset | Size | Field |
|---|---|---|
| 0 | 2 | event id |
| 2 | 2 | sequence number: the low 16 bits of the record's number on its CPU |
| 4 | 4 | time: the raw value of timer channel 9 (0x98900074). It counts down, one step per microsecond, 30 bits |
| 8 | 4 | arg0 |
| 12 | 4 | arg1 |

Each CPU has its own ring of 512 records in RAM. A new record replaces the oldest one. `log_put` never
calls the file system and never waits. In `log-menu` the ring header also keeps the complement of its record count
at +24. A ring whose count and complement do not match (cleared RAM, the ring of an older build, bits that changed
while the camera was off) is not trusted: `log_put` starts a new ring and the flush skips it. The ring of the older
builds had only a magic word, and a camera log of 2026-11-18 shows what that let through: after bits changed while
the camera was off, a flush wrote 512 stale slots.

## The file

The flush task appends blocks of 512 bytes: a 32-byte header, at most 30 records, then zero bytes. A flush
writes as many blocks as it needs for each CPU that has new records. The header:

| Offset | Size | Field |
|---|---|---|
| 0 | 4 | `EPLG` |
| 4 | 1 | format version, 1 |
| 5 | 1 | record size, 16 |
| 6 | 1 | CPU number |
| 7 | 1 | header size, 32 |
| 8 | 8 | build id: the first 8 bytes of a sha256 of the dictionary's events (id, name, level, args) |
| 16 | 4 | number of the first record |
| 20 | 4 | number of records |
| 24 | 4 | records lost on this CPU since the ring was started |
| 28 | 4 | how often the boot hook found a ring in RAM (CPU 0; see `boot` below) |

The flush runs when the GUI enters a menu, playback or the power-off state, and only if the GUI's
`isMediaWriting` says that the card is idle and neither the card nor card-looks' task is busy. It stops when the file has 4 MiB: delete the file to go on.

Why whole 512-byte blocks: the stock `fileif_fwrite` reads a sector before it changes a part of it, and that
read fails for a sector that is past the end of the file. An append that starts and ends on a sector boundary
needs no read. A write that gives 0 is tried three times, 100 ms apart. `fileif_fclose` does not report a
failed directory update, so the next flush checks the file size and writes the records again if the file did
not keep them (`flush` then shows `not_saved`).

## How to read a log

```sh
cp /path/to/card/EPM2LOG.BIN /tmp/scratch/
uv run epm2mod log /tmp/scratch/EPM2LOG.BIN
uv run epm2mod log /tmp/scratch/EPM2LOG.BIN --json > /tmp/scratch/log.json
```

`epm2mod log` prints a short report: the sessions, lost records, the firmware's error records, the flushes, the
count of each event, the screens, and one or two lines for peaking, the film simulations, shooting, interval shooting
and the level gauge. Start with it. The evaluation of the first file from a camera is in
[experiments/2026-11-15-log/evaluation-1.md](../experiments/2026-11-15-log/evaluation-1.md).

Without the option, one line is one record:

```json
{"seq": 100, "cpu": 0, "session": 1, "time_us": 34432550, "event": "shoot_cbs", "level": "info", "args": {"cbs": 136, "result": "0x00000000"}, "names": {"cbs": "capture starts (inferred)"}, "build": "d1ddd46b4dac2414"}
```

- `seq` is the record's number on its CPU.
- `session` counts the starts of the camera in the file, from 1. A session begins at its `boot` record, or at
  the records that the same start put before it: the camera's firmware records errors 19 ms after power-on, and
  the boot task runs at 101 ms.
- `time_us` starts near 0 at power-on. Both CPUs read the same timer.
- `names` gives the name of a value where the dictionary has a table for it: GUI states, shooting callbacks,
  art codes (with the film of `looks/films.json`, for the older seven-film builds only), matrix tables, the peaking colour. The key is the argument, or
  `argument.field`. `args` always holds the number.
- `recovered: true`: the record was still in RAM after a restart and the next session wrote it. It has the
  session number of the session that logged it. These are the last events before a crash. The decoder finds
  them like this: they are in the same write as the new session's start, after the old session's last `flush`
  record, and their time is later than the new `boot` record's time (or more than 1 s before it). For CPU 1 the
  border is the record at which the time goes back.
- A record with an id that is not in the dictionary has `unknown: true` and its two raw arguments, when the
  block's build has no dictionary in `logs/`.
- A line with `marker` is not a record: `gap` (records were lost, with the count), `ring_restart` (RAM was
  clear at a start), `repeat` (records that are in the file twice; they are given once), `damaged` (records that
  cannot be real were dropped: the sequence number in the record is not its place in the block, or the id is not in
  the dictionary of the block's build; stale or changed slots of the ring give them), `truncated`,
  `garbage`, `dictionary_mismatch` (the file comes from a firmware whose dictionary is not in `logs/`: use the
  `logs/events.json` of that commit, `--dict FILE`).

`boot` has the argument `ring_found` (`session` in the build `d1ddd46b4dac2414`). It is not the session number.
The boot hook adds 1 when it finds a ring in RAM. On the camera the error records of the same start have
already made the ring, so a power-on gives 1. A restart that kept the RAM gives 2 or more. The ring RAM keeps
its content at power-off, and bits can change while the camera is off: the check word decides whether the ring is
used (section "The record").

To filter, use `jq`: `jq -c '.events[] | select(.level == "error")' /tmp/scratch/log.json`.

## The dictionary, name tables and older builds

`logs/events.json` has three kinds of content:

| Key | Use | Part of the build id |
|---|---|---|
| `events[].id`, `name`, `level`, `args` | what the firmware writes and how the decoder shows it | yes |
| `events[].doc`, `spec`, `feature` | notes | no |
| `events[].names`, `tables`, `film_entries` | names for values | no |

- `tables` maps a table name to `{value: text}`. A value is decimal (`"259"`), hexadecimal (`"0x5B00"`) or a
  group of 256 values (`"0x5Bxx"`, used when the value has no entry of its own).
- `names` of an event maps an argument (`"state"`) or a field (`"latch.C"`) to a table name.
- `film_entries` says which art code belongs to which menu entry of `looks/films.json`, for the older seven-film
  builds only. `epm2mod log` then shows the film: `Velvia (Diorama)`.
- A name that is inferred says so in its text. Correct a name, a `doc` text or a table at any time: the build
  id stays, and old log files decode with the new names.

**When an id, a name, a level or an argument changes, the build id changes.** A camera may still run the build
with the old id. So, before the change, copy the event list to `logs/events-BUILDID.json` (the keys `format`,
`record_size`, `events`; no `tables`: it takes those of `events.json`). `epm2mod log` reads every
`logs/events-*.json` and decodes each block with the dictionary that has the block's build id. A test checks
that the file name is the build id of its content, and that the two patch specs carry the build id of one of the
dictionaries in `logs/`.

The current build id is the one of `logs/events.json` (`33ca8d15f4f1c877`, carried by `patches/log-menu-2.json`).
`logs/events-*.json` hold the dictionaries of older flashed builds.

## How to add an event and a probe

1. **Add the event to `logs/events.json`.** Take the next id in the range of the feature (1 to 255 core,
   256 peaking, 512 picture mode, 768 level gauge, 1024 interval, 1280 film looks, 1536 shooting, 1792 card
   looks; a new feature takes the next multiple of 256). Give `name`, `level`, `spec`, `doc` and at most two
   `args`. An
   argument has a `name`, a `format` (`hex`, `dec`, `sdec`, `addr`) and, for packed values, `fields` (name,
   shift, bits, and if needed `format` or `enum`).
2. **Choose the hook site.** It is 5 or more bytes of whole instructions in the pinned build, with no
   branch into them but at the first byte. A replaced `call` is allowed; no other pc-relative instruction
   is. A site in the kernel or in segment 1 needs its routine in the kernel range (`PROBES_K`); a site in
   segment 2 or 3 uses `PROBES_U`.
3. **Write the routine in `mkspec_log.py`** and add a row to `HOOKS`:

   ```
   T_NAME:
       movm [other],(sp)        # saves d0, d1, a0, a1, mdr, lir, lar
       mov ...,d1               # arg0
       mov ...,a0               # arg1
       mov %(event_name)d,d0
       call log_put,[],0
       movm (sp),[other]
   %(displaced_NAME)s
       jmp %(back_NAME)s
   ```

   The routine must leave every register and the flags as they were. Load the arguments with `mov`, `movbu`
   and `movhu` only (they keep the flags), or save the PSW in d2 as `T_GUI` does. Scenario S17
   (`scripts/scen_log.py`) checks this for every hook: add a case for the new one.

   Use `log_chg` (a1 = gate) for code that runs in every frame: it logs only when arg0 changes. Use
   `log_cnt` (a1 = gate) to log a fixed number of times after another probe gives the gate a budget.
   A gate is 8 bytes of the state block `PST`.
4. **Generate, build, check:**

   ```sh
   python3 tools/oetool.py unpack build/epm2mod-2026.11.19.BIN /tmp/scratch/pinned
   uv run python experiments/2026-11-15-log/scripts/mkspec_log.py /tmp/scratch/pinned /tmp/scratch/asm
   uv run epm2mod make debug-log
   python3 tools/emu/opcheck.py builds/debug-log.json
   python3 tools/emu/hookcheck.py patches/log-core.json patches/log-probes.json
   ```

   `experiments/2026-11-18-log-menu/scripts/mkspec_logmenu.py` (with `--stock-films`) imports `mkspec_log.py`
   and writes `patches/log-menu-2.json`, the log of the pinned build. Then run the emulator checks of the notes. The generator refuses a site that is not on an instruction
   boundary, a pc-relative instruction other than `call`, and a branch target inside the replaced bytes.
5. A change of an id, name, level or argument gives a new build id. If the old build was flashed, keep its
   event list first (section "The dictionary, name tables and older builds"). The `doc` texts, `names` and
   `tables` do not count. A test fails when the two specs carry a build id that no dictionary in `logs/` has.
6. Give the enumerated values of a new event a table, so that the JSON and the summary show names.

A probe costs 31 to 66 bytes for its routine and 5 to 10 bytes at its site, and no RAM, or 8 bytes of RAM for
a gate. One `log_put` call runs about
40 instructions with the interrupts off on its CPU.
