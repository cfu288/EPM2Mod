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

## 3. Open (each needs a camera probe)

1. The read on the camera: a debug build that reads a small file at a key press and logs the bytes.
2. A look table changed in RAM at run time takes effect at the next shot (I: the tables are at fixed
   RAM addresses in segment 1, `docs/art-filter-slots.md`; U: whether a store into loaded section RAM is
   safe here, it crashed on the E-P7). The emulator does not model the picture, so only a shot can tell.
3. Code space for a loader (today 320 B of code space; the 7.2 KB dead 3D-engine area needs its own
   camera test, `experiments/2026-11-13-code-space-research/` recommendation 1).
