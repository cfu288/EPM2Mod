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

## 5. Camera result of the first probe (2026-11-21, sha256 `7ddccc78…`, on films-twelve-off) [C]

Peaking White, MF Assist Off, focus mode MF: white lines in the normal live view, no zoom (criterion 1, with a lens
that has contacts; no manual lens at hand). Digital Tele-converter on: lines (2). S-AF, C-AF: no lines (3). S-AF+MF
with MF Assist On: the focus ring zooms with lines, as before (3). Movie: no lines in any focus mode (4). Live view
smooth enough (5). After a shot the saved picture has no lines, but **the short preview after the shot shows them**:
with the MF trigger nothing ends peaking at the shot, whereas MF Assist's internal ZoomOff did.

## 6. Moved for CI (2026-11-21)

The other session pinned films-start-texts the same day; its `log-menu-3` uses the run 0x7EBF2E68 too, so the
pinned build's free-space check failed with this spec in `data/specs/`. T_MF is now two parts: T_MF (21 B,
0x7ECB0B81, the test of R) and T_MF2 (39 B, 0x7ECB0FD8, the focus mode), each ending in a nop; the build is the
pinned films-start-texts + `peaking-mf`, sha256 `18aaffabd7b7f15c9d75738f6b5206407b3887c119906e32f15fb3215552194f`.
`scripts/emu_tr.py` PASS on it (12 cases, against the pinned build); the pinned build's free-space check PASS.

## 7. The record-view fix (2026-11-21)

The camera's log of §5 (session 155): with the MF trigger L stays 1 through the half-press, the capture and the record
view; with MF Assist, `pk_mf_end` and L = 0 come at the half-press, before GUI state 0x5101 [C]. GUI state 0x5100 =
live view; 0x5101 from about 10 ms after shoot callback 210 (half-press) through capture (214, 209, 233) and the
record view, until after 211; then 0x5000 and 0x5100; 0x57xx = menus [C, log].

No fixed global holds the GUI state (the setter 0x7ECDF5E9 stores it at dst + 76 of a heap object; U for a pointer).
At the setter's hook 0x7ECDF6E4, d0 = the new state, on every call [R]. So:
- **T_GS** (12 B, 0x7EBF2F20): the hook's `jmp` (log-menu-3's T_GUI) now goes to T_GS, which stores d0 as a u16 at
  0xBE4F67F0 (uncached; the last film RAM block's unused tail, +0x31F0: the loader writes up to +0x30B2) and jumps on
  to T_GUI. Written at every GUI state change, with Debug Log On or Off.
- **T_MF3** (23 B, 0x7EBF3B94): in MF, no lines while that word is 0x5101, as MF Assist ends at the half-press.
  Only 0x5101 is tested (the meaning of 0x5103 and 0x5105 is not known).
- T_MF2 (39 B) now jumps to T_MF3 when the focus mode is MF.

The firmware's TAKE_FUNC_RECVIEW flag (word 0x602B0DD0, which stock MF Assist checks before it starts) would cover
the record view only, and when the latch runs in that window is not known: not used.

| Check | Result |
|---|---|
| build, free space (the build and the pinned build) | sha256 `6a47806dfafce15d281358eae2beffe397132e5999c50b28c69b2a2467efcf39`; PASS, PASS |
| `scripts/emu_tr.py` | PASS: 24 latch cases (GUI 0x5100: as §4; GUI 0x5101: R = 0 and MF give no lines, R = 1 as pinned) and T_GS for 0x5100, 0x5101, 0x5705 (word written, registers kept, on to T_GUI) |
