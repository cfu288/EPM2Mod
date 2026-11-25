"""Function harness: the peaking latch at a live-view refresh, before and after the copies of segments 2 and 3.

    uv run python experiments/2026-11-24-slow-boot/scripts/emu_cold.py [PINNED_BUILD FIX_BUILD]

Runs the latch T_A from its hook 0x7E6ECF91 (end of the struct refresh) to its return, as
experiments/2026-11-21-peaking-mf/scripts/emu_tr.py does, for R 0 / 1, Peaking Off / White, focus S-AF / MF / C-AF and
the GUI state word 0x5100 / 0x5101. Two memory states: "copied" (segments 2 and 3 in RAM) and "not copied" (segment 2,
segment 3 and usr1-third filled with 0xFF, then with random bytes: RAM at a cold start before the task Usr1 copies them).
Pass:
  * the fix, not copied: no fault, no instruction in late-loaded space, and the same result as copied;
  * the fix, copied: the same result as the pinned build, copied (peaking as flashed);
  * the pinned build, not copied: at least one case faults or runs late-loaded space (the defect shows here).
"""
import json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "emulator")]
import bootmem  # noqa: E402
import patchblock  # noqa: E402
import scenario  # noqa: E402
from scenario import Scenario  # noqa: E402

HOOK_A, RET = 0x7E6ECF91, 0x7E6C33F5
LV = 0x605B1CD0
R, L, C = 0x602BE8C5, 0x602BE8C4, 0x602BE8C7
SETTINGS = {0x8971: 0x60410F36, 0xC021: 0x60410F3A}       # prm tag -> data pointer, as emu_tr.py
OFF, WHITE = 1, 3
FOCUS = {"S-AF": 0, "MF": 1, "C-AF": 2}
GS = 0xBE4F67F0
LATE = [(x.lo, x.hi) for x in bootmem.model().loads if x.name in ("segment-2", "segment-3", "usr1-third")]


def image(build):
    _, blk, _ = patchblock.patched_block0(json.load(open(os.path.join(ROOT, "data", "builds", build + ".json")))["specs"])
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    p = os.path.join(HERE, "..", "out", build + ".block0.bin")
    open(p, "wb").write(blk)
    return p


def run(path, name, fill):
    """{case: (fault, L, C, struct+4, struct+5, struct+36, sp change, d2, d3, a2, a3, instructions in late space)}."""
    out = {}
    with Scenario(path, name=name) as sc:
        rnd = random.Random(1)
        for lo, hi in LATE if fill else ():
            sc.write(lo, bytes([0xFF]) * (hi - lo) if fill == "ff" else rnd.randbytes(hi - lo))
        sc.unstub(scenario.SETTINGS_GETTER)
        for tag, data in SETTINGS.items():
            idx = 0x603A0E38 + 8 * (tag >> 4)
            sc.w16(idx, tag); sc.w16(idx + 2, 1); sc.w32(idx + 4, data)
        for r in (0, 1):
            for v in (OFF, WHITE):
                for fname, f in FOCUS.items():
                    for gs in (0x5100, 0x5101):
                        sp_ = 0x7D0F0000
                        sc.w16(GS, gs)
                        sc.w8(SETTINGS[0x8971], v); sc.w8(SETTINGS[0xC021], f)
                        sc.w8(R, r); sc.w8(L, 0xEE); sc.w8(C, 0xEE)
                        sc.w32(LV + 32, 0); sc.w8(LV + 4, 0x55); sc.w8(LV + 5, 0x66); sc.w32(LV + 36, 0)
                        sc.w32(sp_ + 32, RET)
                        x = sc.piece(HOOK_A, [RET], {"sp": sp_, "d0": 0x1234, "d2": 0xD2D2, "d3": 0xD3D3, "a2": 0xA2A2, "a3": 0xA3A3},
                                     insn_limit=20000)
                        g = x.regs
                        late = sum(1 for pc in x.pcs if any(lo <= pc < hi for lo, hi in LATE))
                        out[(r, v, fname, gs)] = (x.fault, sc.r8(L), sc.r8(C), sc.r8(LV + 4), sc.r8(LV + 5), sc.r32(LV + 36),
                                                  g.get("sp", 0) - sp_, g.get("d2"), g.get("d3"), g.get("a2"), g.get("a3"), late)
    return out


def main():
    os.chdir(ROOT)
    pinned, fix = sys.argv[1:3] if len(sys.argv) > 2 else ("spot-af-2", "cold-start-fix")
    pin_img, fix_img = image(pinned), image(fix)
    pin, new = run(pin_img, pinned, None), run(fix_img, fix, None)
    ok = True
    same = sum(new[k][:11] == pin[k][:11] and new[k][0] is None for k in pin)   # all but the late-space count
    ok &= same == len(pin)
    print(f"copied: {fix} gives what {pinned} gives in {same} of {len(pin)} cases, no fault")
    for k in sorted(new):
        r, v, fname, gs = k
        print(f"  R={r} Peaking={'Off' if v == OFF else 'White'} focus={fname:4s} GUI {gs:#06x}: L={new[k][1]} "
              f"(lines {'on' if new[k][1] == 1 else 'off'}), instructions in late space {new[k][11]}")
    for fill in ("ff", "random"):
        cold = run(fix_img, fix, fill)
        good = sum(cold[k] == new[k] and cold[k][0] is None and cold[k][11] == 0 for k in new)
        ok &= good == len(new)
        print(f"not copied ({fill}): {fix}: {good} of {len(new)} cases as copied, no fault, 0 instructions in late space")
        old = run(pin_img, pinned, fill)
        bad = sum(old[k][0] is not None or old[k][11] > 0 for k in old)
        ok &= bad > 0
        print(f"not copied ({fill}): {pinned}: {bad} of {len(old)} cases fault or run late space"
              f" (first: {next((v[0] for v in old.values() if v[0]), None)})")
    print("RESULT", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
