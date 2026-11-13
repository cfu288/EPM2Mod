# Interval shooting and time-lapse movies on the E-PM2

The Olympus PEN E-PM2 has no interval timer. Its sister model, the E-PL6, has one. Both run nearly the same firmware, and the E-PM2's firmware (v1.6) still contains the whole feature: Olympus left out only the menu entry. This work adds the entry and raises the frame limit from 99 to 240.

**Status (2026-11-13):** camera-tested and in use. The latest build is `seven-films-6-interval-240`; the root [README](../../README.md) shows how to build and flash it.

Addresses below are E-PM2 v1.6 runtime addresses (file offset in block 0 + 0x7E421020). Statements are read from the firmware bytes or run in the emulator unless marked *(inferred)*. The full working notes, with every address and table, are in [NOTES.md](NOTES.md).

## 1. What you get

**Shooting Menu 2 → Time Lapse Settings**, between Multiple Exposure and Flash RC Mode, with the E-PL6's own screens and help texts in all 34 languages.

| Setting | Range | Notes |
|---|---|---|
| Time Lapse Settings | Off / On | When On, the shutter button starts a sequence |
| Frame | 1–99 in steps of 1, then 100–240 in steps of 5 | The E-PL6 stops at 99 |
| Start Waiting Time | 0 s to 24 h 59 min 59 s | 0 starts at once |
| Interval Time | 1 s to 24 h 59 min 59 s | Up to 90 s the camera stays in live view; above 90 s it sleeps between frames and wakes by the clock |
| Time Lapse Movie | Off / On | After the last frame the camera makes a movie from the stills |

- The camera holds its sleep and auto-power-off timers during a sequence, so the Sleep setting does not interrupt it.
- MENU, the shutter button or the mode dial ends a sequence (from the code; not yet reported from the camera).
- Set the camera's date and time first. The firmware turns the feature off when the clock is not set.
- Each frame is a mechanical shutter cycle: 240 frames are 240 actuations.

## 2. What was in the firmware, and what was missing

We compared the E-PM2 v1.6 with the E-PL6 v1.4 function by function, after replacing addresses with placeholders.

**Already in the E-PM2, and the same as the E-PL6:**
- the interval engine: start, the timer between frames, the clock-based wake-up for long intervals, the end test, the error and card-full paths (30 functions);
- the time-lapse movie maker;
- the settings (info ids 482–489) and their stored defaults;
- the five menu screens (panels 628 and 636–641) and their editors;
- every text, in all 34 languages.

**Missing in the E-PM2:**

| # | What | Effect |
|---|---|---|
| 1 | The menu row, in four linked tables | No way to reach the feature |
| 2 | Two calls that hold the sleep and power-off timers | The normal Sleep setting can interrupt a sequence |
| 3 | A flag that is set while the time-lapse movie is made | A card-mount event during movie creation can end the sequence early *(inferred)* |

The other differences between the two bodies do not belong to this feature (NOTES §4).

## 3. Implementation

There are two patch specs. Both change block 0 only. The first adds the feature; the second raises the frame limit.

### 3.1 `patches/interval-timelapse-v2.json`: the feature (48 edits, 921 bytes)

**The menu row.** The E-PM2's menu has no spare slot, so the row is inserted the way the E-PL6 has it. The row sits in four structures, and all four change:

| Structure | Change |
|---|---|
| Top-menu table (36 rows of 10 bytes, no room to grow) | A 37-row copy, byte-identical to the E-PL6's, in free space. The 6 instructions that load the table's address now load the new one. The old table stays, unused |
| Tab layout (which rows each tab shows; in the `.data` image) | Renumbered in place: Shooting Menu 2 has 6 rows, and the later tabs move up by one |
| Shooting Menu 2's list of screens that OK opens | A copy with the Time Lapse screen (panel 628, setting 482) added, in free space; one pointer changed |
| The value shown at the right of each row | The per-row value lists are renumbered. The code that picks a setting per row gets one more case, through a 51-byte block of new code |

Adding a row moves every later row number up by one. The E-PL6 changed 31 constants for this (10 in the value code, 20 in the monitor-adjust screens). The spec makes the same 31 changes. We found no other place that holds a row number.

**Keep-awake.** Two hooks reproduce the E-PL6's behaviour with functions the E-PM2 already has:
- `startIntervalShooting` (hook at 0x7E98855F) also calls the hold function 0x7E997E94, which stops the sleep and power-off timers.
- The sleep-timer selector 0x7E997BD9 is replaced by a 177-byte copy of the E-PL6's version. It holds the timers while a sequence runs and restores them when the sequence ends.

**Movie guard.** Four hooks set, clear and test a flag around movie creation, at the same places as the E-PL6. The flag is kept in RAM word 0x602BE878, an entry of a table that no code reads (it starts at 0 on every boot).

**Defaults.** Frame = 10 and Interval Time = 5 s replace the stock zeros. They apply only after a full reset; set the values in the menu.

**Where the new bytes are.** All tables and code that the spec adds (831 bytes) are at 0x7ECB0BA4–0x7ECB0EE2. This is blank padding at the end of the second code segment. The camera loads it at every start, nothing else refers to it, and code of the film patches already runs from the same padding.

### 3.2 `patches/interval-frames-240.json`: up to 240 frames (6 edits, data only)

The 99-frame limit has three causes. The spec removes two of them.

| Cause | In the spec |
|---|---|
| The list of permitted values holds 1–99 | A new 128-value list (1–99, then 100, 105 … 240) at 0x7E4C9100, in blank padding that the reset code loads |
| The Frame screen has one row per value, with its own text "1f" … "99f" | 128 rows at 0x7EBF1100, in an unused block of debug text. The new rows use the "number + unit" row type that the Custom Self-timer screen uses, with an empty unit, so they show "100" … "240" and need no new text |
| The count is stored in one byte | Unchanged: the limit is 255 |

The list cannot be longer than 128 rows, because the screen keeps its position in a signed byte. This is why the values above 99 go in steps of 5. A count of 999, as on later Olympus bodies, needs wider storage and a different editor; this is not planned.

## 4. How it was checked

1. **Against the E-PL6.** Every changed table equals the E-PL6's table byte for byte. Every piece of new code equals the E-PL6's code instruction for instruction, apart from addresses.
2. **In the emulator** (`tools/emu`, single functions). On the patched image, every menu row gives the same help text (43 of 43), the same OK target (43 of 43) and the same value (74 of 74) as the E-PL6 image. The keep-awake code makes the same calls in the same order on all 40 selector inputs and all 14 start paths. The movie guard and the frame list have their own cases. The film patches behave the same with and without the interval specs.
3. **By independent review.** Four reviews by reviewers who did not write the patch: [memory](review-1-memory.md), [code](review-2-code.md), [the final spec](review-3-v2.md) and [the 240-frame spec](review-4-frames240.md). They found two real defects in the first version, which v2 corrects: the new bytes were in space that the film patches already use, and the movie guard was missing. A separate [trace](trace-frames-list-location.md) shows that nothing reads the frame list before the code that needs it is loaded.
4. **With the free-space tool.** `python3 tools/freespace.py check` passes on the full list of specs: no two specs use the same bytes, and every new byte is in memory that the camera loads and that nothing else refers to. Run it before each build.
5. **On the camera.** See the next section.

A static check cannot see an address that the firmware computes while it runs. The emulator runs single functions, not the whole camera. The camera test is the proof.

## 5. Camera results

| Date | Build | Result |
|---|---|---|
| 2026-11-13 | `seven-films-6-interval` (film patches + v2) | Works. Interval shooting to 99 frames |
| 2026-11-13 | `seven-films-6-interval-240` (+ frames-240) | Works. A sequence with the time-lapse movie was tested to 125 frames |

**Not yet reported from the camera:** a full 240-frame run; the frame count after a power cycle and in a Myset; the three ways to cancel; an interval above 90 s; Sleep at 1 min with a 75 s interval; a full card. The test steps are in NOTES §7, §12.5 and §13.7.

## 6. Limits

- **Interval Time cannot be 0.** The firmware uses "timer, 0 ms" to stop the interval timer, so the sequence would stop after the first frame. The menu refuses to store 0 for this reason. For back-to-back frames, use sequential shooting (NOTES §14).
- **More than 240 frames** in one sequence is not possible with this design. Start a second sequence.
- **The debug text under the new Frame rows** (names for the `sdk` debug command) is overwritten. The command itself uses a different copy of the names.
- **Three superseded film specs** in `patches/history/` use the same padding and cannot be combined with v2.

## 7. Risks

- **Battery and heat:** with intervals up to 90 s the sensor and live view stay on, and auto power-off is held for the whole sequence.
- **A sequence that does not end normally** may leave the sleep and power-off timers held until the next sequence or a power cycle *(inferred; the E-PL6 has the same design)*.
- **The time-lapse movie at 240 frames** is not tested; 125 frames is.
- **To go back,** flash a build without the two specs, or the stock firmware.

## 8. How the work went

1. **Replace** (`interval-timelapse.json`, 5 edits). The first spec put the Time Lapse row in the place of Flash RC Mode. It is the smallest change, but it removes a menu row.
2. **Insert** (`interval-timelapse-insert.json`). The row is added as on the E-PL6, and Flash RC Mode stays.
3. **Keep-awake** (`interval-timelapse-insert-awake.json`). The E-PL6's timer hold is added.
4. **v2** (`interval-timelapse-v2.json`). After the reviews, the new bytes move out of the film patches' space and the movie guard is added. This is the first version that was built.
5. **240 frames** (`interval-frames-240.json`). The first answer was "not possible"; the number + unit row type made it possible without new text.

Specs 1–3 are kept for reference only. Do not build spec 2 or 3 with the film patches: they use the same bytes.

## 9. Files

| Path | Contents |
|---|---|
| `patches/interval-timelapse-v2.json`, `patches/interval-frames-240.json` | The two specs in the build |
| `patches/interval-timelapse*.json` (three others) | Superseded specs |
| [NOTES.md](NOTES.md) | Working notes: every table, address, comparison and emulator result |
| `review-1` … `review-4`, `trace-frames-list-location.md` | The independent reviews and the frame-list trace |
| `scripts/` | Spec generators (`mkspec_v2.py`, `mkspec_frames240.py`), cross-body comparison and scan helpers. NOTES "Files" lists each one |
| `results/` | Emulator output, function pairing, scans |
| `tools/emu/cases.py` (repo root) | The emulator cases: `menu_help`, `menu_child`, `menu_value`, `ivl_guard`, `ivl_selector`, `ivl_start`, `ivl_movie_guard`, `ivl_shot_done`, `frames_step`, `frames_editor` |
