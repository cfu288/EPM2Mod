# The structured log

For developers. A debug build of the firmware writes event records to the file `EPM2LOG.BIN` on the SD
card. `epm2mod log` turns the file into JSON lines. The design notes, the evidence and the camera test
are in [experiments/2026-11-15-log/NOTES.md](../experiments/2026-11-15-log/NOTES.md).

The log is in the build `builds/debug-log.json` only: the pinned specs, then `patches/log-core.json` and
`patches/log-probes.json`. The pinned build has no log code.

## The parts

| Part | Where | What it does |
|---|---|---|
| Dictionary | `logs/events.json` | The id, name, level and argument formats of each event. The camera stores no text |
| Generator | `experiments/2026-11-15-log/scripts/mkspec_log.py` | Reads the dictionary and writes the two patch specs |
| Log core | `patches/log-core.json` | `log_put`, `log_chg`, `log_cnt`, the flush task, and the events boot, firmware error and GUI state |
| Probes | `patches/log-probes.json` | One hook and one small routine per event of a feature |
| Decoder | `src/epm2mod/eventlog.py`, command `epm2mod log` | Reads the file and the dictionary, prints JSON lines |

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
calls the file system and never waits.

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
| 28 | 4 | restarts that found the ring in RAM |

The flush runs when the GUI enters a menu, playback or the power-off state, and only if the GUI's
`isMediaWriting` says that the card is idle. It stops when the file has 4 MiB: delete the file to go on.

Why whole 512-byte blocks: the stock `fileif_fwrite` reads a sector before it changes a part of it, and that
read fails for a sector that is past the end of the file. An append that starts and ends on a sector boundary
needs no read. A write that gives 0 is tried three times, 100 ms apart. `fileif_fclose` does not report a
failed directory update, so the next flush checks the file size and writes the records again if the file did
not keep them (`flush` then shows `not_saved`).

## How to read a log

```sh
cp /path/to/card/EPM2LOG.BIN /tmp/scratch/
uv run epm2mod log /tmp/scratch/EPM2LOG.BIN > /tmp/scratch/log.jsonl
```

One line is one record:

```json
{"seq": 5, "cpu": 0, "session": 1, "time_us": 41806, "event": "fw_error", "level": "error", "args": {"code": "0x2A001001", "caller": "0x7E579DCC"}, "build": "d1ddd46b4dac2414"}
```

- `seq` is the record's number on its CPU. `session` counts the `boot` events in the file.
- `time_us` starts near 0 at power-on. Both CPUs read the same timer.
- `recovered: true`: the record was still in RAM after a restart and the next session wrote it. These are
  the last events before a crash.
- A record with an id that is not in the dictionary has `unknown: true` and its two raw arguments.
- A line with `marker` is not a record: `gap` (records were lost, with the count), `ring_restart` (RAM was
  clear at a start), `repeat` (records that are in the file twice; they are given once), `truncated`,
  `garbage`, `dictionary_mismatch` (the file comes from a firmware with another dictionary: use the
  `logs/events.json` of that commit, `--dict FILE`).

To filter, use `jq`: `jq -c 'select(.level == "error")' /tmp/scratch/log.jsonl`.

## How to add an event and a probe

1. **Add the event to `logs/events.json`.** Take the next id in the range of the feature (1 to 255 core,
   256 peaking, 512 picture mode, 768 level gauge, 1024 interval, 1280 film looks, 1536 shooting; a new
   feature takes the next multiple of 256). Give `name`, `level`, `spec`, `doc` and at most two `args`. An
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
   python3 tools/oetool.py unpack build/peaking-colours.BIN /tmp/scratch/pinned
   uv run python experiments/2026-11-15-log/scripts/mkspec_log.py /tmp/scratch/pinned /tmp/scratch/asm
   uv run epm2mod make builds/debug-log.json
   python3 tools/emu/opcheck.py builds/debug-log.json
   python3 tools/emu/hookcheck.py patches/log-core.json patches/log-probes.json
   ```

   Then run the emulator checks of the notes. The generator refuses a site that is not on an instruction
   boundary, a pc-relative instruction other than `call`, and a branch target inside the replaced bytes.
5. A change of an id, name, level or argument gives a new build id, and the decoder marks a file from
   another build id. The `doc` texts do not count. A test fails when the two specs were not generated from
   the dictionary in the repository.

A probe costs 31 to 66 bytes for its routine and 5 to 10 bytes at its site, and no RAM, or 8 bytes of RAM for
a gate. One `log_put` call runs about
40 instructions with the interrupts off on its CPU.
