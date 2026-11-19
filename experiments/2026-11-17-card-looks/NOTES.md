# Looks loaded from the card: feasibility probes (2026-11-17)

Question: can the firmware read a look file from the SD card at run time, so that looks change without a
reflash (as Caduceus does on the E-P7)? Labels: V = run or read in our bytes, I = inferred, U = unknown.

## 1. The read call (V, static)

`0x7E5C536F` is `fileif_fread`: a wrapper of the same shape as `fileif_fwrite` (0x7E5C5339), with
a0 = buffer, d0 = 1, d1 = bytes, a1 = handle, d0 = bytes read. It sends command 0x10005 to the task
FILECLBK (fwrite: 0x10003). Its callers name it: the stock "read test in %s len(%d) pos(%d)
whence(%d)" routine 0x7E5C6188 and the QuickTime reader ("[QT_FILE] fileif_fread erro..." at
0x7E6D723D). `0x7E5C53A5` (command 0x10008) is `fileif_fseek` ("fileif_fseek err" in its callers).

## 2. The read in the emulator (V)

`scripts/probe.s` (assembled at 0x13000 in the emulator's low RAM; the calls and frames are the
camera-tested log code's) opens `C:\LOOKS.BIN` with mode "r", reads 512 bytes, closes. `scripts/run.mjs`
boots stock in the om-emu fork's boot lab with a card holding a 600-byte LOOKS.BIN, presses INFO at
3000 ms, and runs the probe once in the application's event-loop task (its registers saved and put back).

Result: handle returned, 512 bytes read, equal to the file's first 512 bytes, fclose 0, 5.3 ms of lab
time; FILECLBK took 0x10001, 0x10005, 0x10002; no error-log entry, no refused MMIO access; MENU works
after it; the card is unchanged.

    OM_EMU_MODEL=E101 OM_EMU=$PWD/emulator/om-emu BIN=firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN \
      CARD=/tmp/scratch/card PROBE=/tmp/scratch/probe.bin node experiments/2026-11-17-card-looks/scripts/run.mjs

(probe.bin: `mn10300-elf-as probe.s`, `ld -Ttext=0x13000 --defsym FOPEN=0x7e5c52dc --defsym
FCLOSE=0x7e5c5308 --defsym FREAD=0x7e5c536f`, `objcopy -O binary`.)

## 3. Probe 1 on the camera: the build (V in the emulator; camera pending)

`builds/debug-log-card-read.json` = `debug-log-films-12d` (flashed 2026-11-16) + `patches/log-card-read.json`
(`mkspec_log.py --card-read`; event `card_read`, id 1792, dictionary build id `3cc5e33e95b6de52`; the flashed
dictionary is kept as `logs/events-da49b2f5e7e62ca7.json`). The hook is the log's flush task entry
(0x7EBF2C00, log-core's code, not stock); its routine (116 B at 0x7EBF2888, a run no spec ledgers) runs the two
replaced instructions, then once per session (flag PST+104) `fileif_fopen(C:\EPM2LOOK.BIN, "r")`,
`fileif_fread` of 16 bytes into the flush buffer, `fileif_fclose`, and logs `card_read` (bytes read, -1 when the
file did not open; bytes 0-3). The flush then runs as before. It runs in the flush task (USRTEST_A, its own task,
the camera-tested home of the log's file writes), when the GUI enters a menu, playback or the power-off state.

sha256 `1297f288a69138d7b10fab1f37553a65fea82d2013ecc141445e194528689cab`. Checks: free space PASS, op check 0
FAIL, load order: the one allowed failure of the base build only, boot-test PASS, update-path-test PASS.
Emulator (`emulator/emu-run builds/debug-log-card-read.json logplay.mjs ...`, MENU, MENU, PLAY), decoded with
`epm2mod log`:

| Card | card_read | After it |
|---|---|---|
| `EPM2LOOK.BIN` = `LOOK0001xxx...` | bytes 16, first4 0x4B4F4F4C ("LOOK") | flush ok; later flushes ok, no second read |
| no such file | bytes -1 | flush ok |
| no card | (no log file) | no fault; only the two error entries every start has |

Flash: `epm2flash debug-log-card-read 1297f288a69138d7b10fab1f37553a65fea82d2013ecc141445e194528689cab`.
Go back: `epm2flash films-12d 2cdd18e7004821b2e443ec4f08db06ab9a0d4f0f700ab53db8c4bbc1dad93e32`.

Camera result (2026-11-17, V, `docs/camera-log.md`): log session 15 has `card_read` bytes 16, first4
`0x4B4F4F4C` ("LOOK") at 2.48 s, 30 ms after MENU, then flush ok; a shot, a second menu and the power-off
followed with every flush ok and no new error record. **Probe 1 passed.** The same log shows where probe 2
must write: the colour stage of the film in use (Pro 400H, art 71) runs on CPU 1, for live view and for the
shot, and reads its art matrix from 0x7ECB0988 (codes 71 and 80; segment 2, plain RAM) in every pass.

## 5. Probe 2: a look value written in RAM at run time (V in the emulator; camera pending)

`builds/debug-log-card-look.json` = `debug-log-films-12d` + `patches/log-card-look.json` (`mkspec_log.py
--card-look`, in place of log-card-read; `docs/space-superseded.tsv`). The same hook; T_CRD (104 B at
0x7EBF2888) reads 32 bytes, T_APL (95 B at 0x7EBF2B90) logs `card_read` and, for a file of 26 bytes or more
that starts with "LOOK", writes its bytes 8-25 (9 x s16) into the art matrix of codes 71 and 80 (Pro 400H,
0x7ECB0988) through the cached address and the uncached alias, then logs `card_look` (values written; values
0 and 1 read back from RAM). Event `card_look` id 1794, dictionary build id `f412b3f66f1c1b6b`; the flashed
`3cc5e33e95b6de52` is kept in `logs/`. sha256 `d6955aac7bd33660f37ebe39d259b6282edb6da99bcc8707c3c00dba9df27f73`.

The test file (`build/EPM2LOOK-grey.BIN`, 26 B): "LOOK0002" and the matrix [77 150 29] in all three rows
(every output channel the same luma: a black-and-white picture). Stock Pro 400H in films-12d is
[202 68 -14; -5 254 7; -8 7 257].

| Card file | Emulator log |
|---|---|
| the grey look file | card_read bytes 26, LOOK; card_look written 9, first2 0x0096004D (77, 150) |
| probe 1's 16-byte file | card_read bytes 16; card_look written 0, first2 0x004400CA (202, 68: the table unchanged) |

The emulator has no caches and makes no picture, so it cannot answer the question of this probe: the colour
stage runs on CPU 1 and reads the table in every pass (the probe-1 log), and the write comes from CPU 0. A
photo before MENU and photos after it tell whether CPU 1 uses the new values at once, later, or never.

Camera, first try (2026-11-17, `docs/camera-log.md`): the write works (V: `card_look` written 9, read back
0x0096004D), but the photos cannot tell its effect. (1) The load ran at 3.34 s, when the GUI entered live
control (state 0x5705: OK, which is a 0x57xx state and starts the flush), before the first photo, so there
is no photo before it. (2) The scene was a dim room with white walls and black-and-white prints: colour spread
at equal brightness 0.5 levels in all three photos, which a grey matrix gives, but which this scene may give
anyway. New finding (V): the still's colour stage ran on CPU 0 (stack 0x6047D2E4, at 12.2 s, art 71, table
0x7ECB0988); only live view's runs on CPU 1. So for stills the writer and the reader are the same CPU. Session 16
(the start after the flash) has garbage records: the known ring-header defect (`docs/todo.md`), not the probe.
Retake: a colourful scene in good light, photo A before any OK, MENU or PLAY, then MENU, MENU, photo B.

**Retake: probe 2 passed (V, 2026-11-17).** A striped colour picture on a screen, Pro 400H: photo A before
any menu has mean colour 75.7 and a colour spread of 53.9 at equal brightness; photo B after MENU, MENU has
4.9 and 1.0, black and white as the grey matrix gives. The owner saw live view turn black and white right
after the menu: live view's colour stage on CPU 1 took the values CPU 0 wrote at once (no cache step needed in
this test). Log session 19: `card_read` 26 bytes, `card_look` written 9, read back 0x0096004D. Session 18 (a
start that went to power-off in 0.5 s) has records with flipped bits: the RAM defect of `docs/todo.md`.

Flash: `epm2flash debug-log-card-look d6955aac7bd33660f37ebe39d259b6282edb6da99bcc8707c3c00dba9df27f73`.
Go back: `epm2flash films-12d 2cdd18e7004821b2e443ec4f08db06ab9a0d4f0f700ab53db8c4bbc1dad93e32`.

## 4. Open (each needs a camera probe)

1. ~~The read on the camera~~: passed (section 3).
2. ~~A look table changed in RAM at run time takes effect~~: passed, at once, in photos and live view (section
   5). The E-P7's crash on a store into loaded section RAM did not happen here (V: one table, 9 values).
3. Code space for a real loader. Probe 2's read and copy of one table took 199 B in two free runs of segment 2.
   The look data itself needs no new space: a loaded look replaces the values in its slot's existing tables. The
   code for the whole feature (checks, curve decode, all slots, menu and start hooks) is about 1 KB (I,
   `design.md` section 6), more than the free runs hold. The 3D-engine area is a candidate whose "dead" status is
   static evidence only (`experiments/2026-11-13-reclaim-space/review-3d-cluster.md` section 6), not proven.

The full design (menu row, the EEROM-tail store, the stage caches, the file format, the probes) and the final plan:
`design.md` (section 9: the probe harness and the persistence probe; both passed on the camera on 2026-11-17:
a loaded look takes effect at once with the refresh, and stays in the camera without the card).
