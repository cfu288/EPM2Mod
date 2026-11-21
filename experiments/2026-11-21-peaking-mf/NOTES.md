# Focus peaking whenever the focus mode is MF (2026-11-21)

Labels: [C] camera, [R] read from the firmware, [I] inferred, V verified here (emulator or computation).
Goal (owner): parity with the bodies of the same generation; peaking with manual lenses (GitHub issue #4: "focus
peaking with manual lenses ... while in 2x"). The owner's trigger: manual focus mode, always on.

## 1. Acceptance criteria (agreed 2026-11-21)

1. Focus mode MF and Peaking set to a colour: the lines show in the normal, unzoomed live view, the whole time, with
   any lens, a lens without contacts too; no focus-ring turn needed.
2. The same with the Digital Tele-converter on (2x).
3. S-AF and C-AF as today; in S-AF+MF the focus ring starts MF Assist with peaking as today.
4. No peaking while a movie records, in playback or in menus; shooting as today, peaking back after a shot (no crash).
5. Live view usable; the frame rate with peaking on the whole time is measured.

## 2. Firmware facts (static, block 0 of stock 1.6)

| Fact | Label |
|---|---|
| The focus mode in use is prm 0xC021 (info 25). The mode controller copies AF Mode > Still Picture (291, prm 0x5021) into it (0x7E704085; movie 292 at 0x7E7040A9); the focus code reads it (0x7E5930FB -> the fcs packet's mode_focus). MF = 1, C-AF = 2, S-AF = 0 (S-AF+MF is S-AF with prm 0x5011 = 1, C-AF+TR is C-AF with 0x6771 = 1) | R |
| The live-view code reads prm 0xC021 with the settings getter 0x7E457C75 (0x7E6CAAA7, the mov layer of the latch) | R |
| Nothing changes the focus mode for a lens: the only conflict rule of 291 is Time Lapse (C-AF -> S-AF); the only writers of 0xC021 are the two copies and a lens-init swap that puts the value back. So MF stays MF with a lens without contacts | R / I |
| The latch refuses live-view kinds 2 and 5: record +4 values 1, 2 -> 2 and 3 -> 5 (getter 0x7E6CFF23). Record +4 is the sensor mode (0 HS 30 fps, 1 HSSC 60, 2 MSSC 120, 3 LSSC 240, 4 HSHR, 5 CLIP), so kinds 2 and 5 are the high-frame-rate readouts | R for the map, I for the meaning |
| The Digital Tele-converter is a zoom factor (prm 0x8372 -> the mov scale word 0x605B0916), not a sensor mode: it should not give kind 2 or 5 | I |

## 3. Design: `peaking-mf` (`scripts/mkspec.py`)

T_R (custom-menu-rows-3, kernel range, called by the latch T_A at the end of the per-frame struct refresh
0x7E6ECCAF) returns 1 when R (MF Assist On) is set and Peaking is not Off. Its first three instructions
(`movbu (R),d0 / cmp 0,d0 / beq`, 10 B at 0x7E4C93A4) become `jmp T_MF`. T_MF (49 B, segment 2, 0x7EBF2E68, a free
run of reclaimed stock code): R set -> back to T_R's setting test; R clear -> read prm 0xC021 with the getter,
restore a1 = the live-view struct and d1 = 0 as T_R's caller has them, and go on to the setting test only when the
value is 1 (MF), else return 0. Every other latch condition stays (no movie, kind not 2 or 5, T_GUARD).
Build `peaking-mf` = films-twelve-off + `peaking-mf`.

The jump from the kernel range to segment 2 is safe at run time: T_R runs only from the latch, in live view, long
after the boot task loaded segment 2 [R]; boot-test and update-path-test check the starts.

## 4. Checks

| Check | Result |
|---|---|
| `uv run epm2mod make peaking-mf` | sha256 `7ddccc78e0e92ff98da84a25efd05a92e541bb48e6c65b86073825926be98ab4`; free space PASS |
| `scripts/emu_tr.py` (the latch T_A with the firmware's settings getter, probe against pinned; R 0 / 1, Peaking Off / White, focus S-AF / MF / C-AF) | PASS, 12 cases: R = 1 as pinned; R = 0 and MF as pinned with R = 1 (L = 1, Key Line forced); R = 0 and S-AF / C-AF as pinned with R = 0; registers and sp kept, no fault (V) |
| `emulator/hookcheck.py` | 0 transfers for `peaking-mf`: the patched site is code of another spec (T_R), not stock code, so the static boot-order check does not see the jump to segment 2. The run-time argument of §3 and the boot / update-path tests stand for it |
| `tools/checks.py --tier full` | free space, op-check, boot-test, update-path-test PASS; save-guard S24 / S25 PASS for the build (the "FAIL" is the reference's, as every build of this line); peaking S4 R = 0 at the end, S5 as pinned, S7 PASS |
| `scen_direct4.py s6` against the pinned films-twelve-off | PASS: 0 FAULT, no art code whose six-axis result differs |
