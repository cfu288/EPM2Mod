"""Emulator check of peaking-mf: the latch T_A, from its hook at the end of the struct refresh to the return, with
the firmware's own settings getter, on the pinned build and on the probe. Research code.

    uv run python experiments/2026-11-21-peaking-mf/scripts/emu_tr.py

Settings written as the full-boot emulator stores them (an index entry {tag, count, data pointer} per prm tag at
0x603A0E38 + 8 * (tag >> 4), as scen_menu.py S11): 458 (prm 0x8971, Peaking: 1 Off, 3 White) and the focus mode in
use (prm 0xC021: 0 S-AF, 1 MF, 2 C-AF). Pass:
  * R = 1: the probe gives what the pinned build gives (L, C, the struct fields, the kept registers and sp);
  * R = 0 and focus mode MF: the probe gives what the pinned build gives with R = 1;
  * R = 0 and another focus mode: the probe gives what the pinned build gives with R = 0;
  * the GUI state word (T_GS's copy) 0x5101 (half-press to the end of the record view): R = 0 and MF give what the
    pinned build gives with R = 0 (no lines); 0x5100 (live view): as above;
  * T_GS, run from the GUI state setter's hook with d0 = a state: the word holds it, and the run reaches log-menu's
    T_GUI 0x7EBF265B with the registers unchanged.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "emulator"), os.path.join(ROOT, "experiments", "2026-11-14-focus-peaking", "scripts")]
import patchblock  # noqa: E402
import scenario  # noqa: E402
from scenario import Scenario  # noqa: E402

HOOK_A, RET = 0x7E6ECF91, 0x7E6C33F5
LV = 0x605B1CD0
R, L, C = 0x602BE8C5, 0x602BE8C4, 0x602BE8C7
SETTINGS = {0x8971: 0x60410F36, 0xC021: 0x60410F3A}       # tag -> data pointer (0x60410F3A: four bytes after 458's)
OFF, WHITE = 1, 3
FOCUS = {"S-AF": 0, "MF": 1, "C-AF": 2}
GS, GUI_HOOK, GUI_NEXT = 0xBE4F67F0, 0x7ECDF6E4, 0x7EBF265B
STATES = (0x5100, 0x5101)


def image(build, tag):
    _, blk, _ = patchblock.patched_block0(json.load(open(os.path.join(ROOT, "data", "builds", build + ".json")))["specs"])
    p = os.path.join(ROOT, "build", "peaking-mf", f"{tag}.block0.bin")
    open(p, "wb").write(blk)
    return p


def run(path, name):
    out = {}
    with Scenario(path, name=name) as sc:
        sc.unstub(scenario.SETTINGS_GETTER)
        for tag, data in SETTINGS.items():
            idx = 0x603A0E38 + 8 * (tag >> 4)
            sc.w16(idx, tag); sc.w16(idx + 2, 1); sc.w32(idx + 4, data)
        for r, v, (fname, f), gs in ((r, v, ff, gs) for r in (0, 1) for v in (OFF, WHITE) for ff in FOCUS.items() for gs in STATES):
                    sp_ = 0x7D0F0000
                    sc.w16(GS, gs)
                    sc.w8(SETTINGS[0x8971], v); sc.w8(SETTINGS[0xC021], f)
                    sc.w8(R, r); sc.w8(L, 0xEE); sc.w8(C, 0xEE)
                    sc.w32(LV + 32, 0); sc.w8(LV + 4, 0x55); sc.w8(LV + 5, 0x66); sc.w32(LV + 36, 0)
                    sc.w32(sp_ + 32, RET)
                    x = sc.piece(HOOK_A, [RET], {"sp": sp_, "d0": 0x1234, "d2": 0xD2D2, "d3": 0xD3D3, "a2": 0xA2A2, "a3": 0xA3A3})
                    g = x.regs
                    out[(r, v, fname, gs)] = (x.fault, sc.r8(L), sc.r8(C), sc.r8(LV + 4), sc.r8(LV + 5), sc.r32(LV + 36),
                                          g.get("sp", 0) - sp_, g.get("d2"), g.get("d3"), g.get("a2"), g.get("a3"))
        if name == "probe":
            for st in (0x5100, 0x5101, 0x5705):
                sc.w16(GS, 0)
                x = sc.piece(GUI_HOOK, [GUI_NEXT], {"d0": st, "d3": 0xD3D3, "a1": 0xA1A1})
                out[("gs", st)] = (x.fault, sc.r16(GS), x.regs.get("pc"), x.regs.get("d0"), x.regs.get("d3"), x.regs.get("a1"))
    return out


def main():
    os.chdir(ROOT)
    pinned = os.path.basename(json.load(open(os.path.join(ROOT, "data", "pinned-build.json")))["build"])[:-5]
    pin, mf = run(image(pinned, "pinned"), "pinned"), run(image("peaking-mf", "probe"), "probe")
    ok = True
    for key, got in sorted((k, v) for k, v in mf.items() if k[0] != "gs"):
        r, v, fname, gs = key
        rr = 1 if (r or (fname == "MF" and gs != 0x5101)) else 0
        ref = pin[(rr, v, fname, gs)]
        good = got == ref and got[0] is None
        ok &= good
        print(f"R={r} Peaking={'Off' if v == OFF else 'White'} focus={fname:4s} GUI {gs:#06x}: probe L={got[1]} C={got[2]:#04x} "
              f"struct+4={got[3]:#04x} sp+{got[6]} fault={got[0]} | expected (pinned, R={rr}) L={ref[1]} -> {'ok' if good else 'NOT OK'}")
    for st in (0x5100, 0x5101, 0x5705):
        f, word, pc, d0, d3, a1 = mf[("gs", st)]
        good = f is None and word == st and d0 == st and d3 == 0xD3D3 and a1 == 0xA1A1
        ok &= good
        print(f"T_GS d0={st:#06x}: word {word:#06x}, registers kept {d0 == st and d3 == 0xD3D3 and a1 == 0xA1A1}, fault {f} -> {'ok' if good else 'NOT OK'}")
    print("RESULT", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
