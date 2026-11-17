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

    OM_EMU_MODEL=E101 OM_EMU=$PWD/third_party/om-emu BIN=firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN \
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
Emulator (`tools/emu/emu-run builds/debug-log-card-read.json logplay.mjs ...`, MENU, MENU, PLAY), decoded with
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

## 4. Open (each needs a camera probe)

1. ~~The read on the camera~~: passed (section 3).
2. A look table changed in RAM at run time takes effect at the next shot (I: the tables are at fixed
   RAM addresses in segment 1, `docs/art-filter-slots.md`; U: whether a store into loaded section RAM is
   safe here, it crashed on the E-P7). The emulator does not model the picture, so only a shot can tell.
3. Code space for a loader (today 320 B of code space; the 7.2 KB dead 3D-engine area needs its own
   camera test, `experiments/2026-11-13-code-space-research/` recommendation 1).
