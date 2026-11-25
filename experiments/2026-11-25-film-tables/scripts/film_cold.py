"""Function harness: the three functions that read the routes of the hidden stored values (111, 112, 114, 115, 118),
with segments 2 and 3 copied and not copied.

    uv run python experiments/2026-11-25-film-tables/scripts/film_cold.py [PINNED_BUILD FIX_BUILD]

Every stored value 100 to 120 through every route: mov_art 0x7E6CBFD3 (the still table and the movie table, the movie
table by its argument and by the live-view struct's movie word; through its wrapper 0x7E6CBFC7; with peaking on, which
hooks mov_art's end), 0x7E6DBA95 (the still and the movie table) and art_GetFilterType 0x7E71BD94 (grades 1, 2, 3).
"Not copied": segment 2, segment 3 and usr1-third are filled with 0xFF, then with random bytes. Pass:
  * the fix, copied: every result as the pinned build, copied; the five values give 94, 98, 144, 156, 159;
  * the fix, not copied: every result as copied, no fault, 0 instructions in late-loaded space;
  * the pinned build, not copied: every route of the five values, and nothing else, faults or runs late-loaded space.
"""
import json, os, random, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "emulator")]
import bootmem  # noqa: E402
import patchblock  # noqa: E402
from scenario import Scenario  # noqa: E402

LV = 0x605B1CD0                     # live-view struct: +3 the picture mode, +32 the movie word
LATCH = 0x602BE8C4                  # L: 1 while peaking shows
HIDDEN = {111: 94, 112: 98, 114: 144, 115: 156, 118: 159}
LATE = [(x.lo, x.hi) for x in bootmem.model().loads if x.name in ("segment-2", "segment-3", "usr1-third")]
# name, function, registers for a stored value, the struct's movie word, the peaking latch
ROUTES = [("mov_art still", 0x7E6CBFD3, lambda v: {"d0": 0, "d1": 0, "a0": 0}, 0, 0),
          ("mov_art movie (argument)", 0x7E6CBFD3, lambda v: {"d0": 1, "d1": 0, "a0": 0}, 0, 0),
          ("mov_art movie (struct)", 0x7E6CBFD3, lambda v: {"d0": 0, "d1": 0, "a0": 0}, 1, 0),
          ("mov_art still (wrapper)", 0x7E6CBFC7, lambda v: {"d0": 0, "d1": 0}, 0, 0),
          ("mov_art still, peaking on", 0x7E6CBFD3, lambda v: {"d0": 0, "d1": 0, "a0": 0}, 0, 1),
          ("0x7E6DBA95 still", 0x7E6DBA95, lambda v: {"d0": v}, 0, 0),
          ("0x7E6DBA95 movie", 0x7E6DBA95, lambda v: {"d0": v}, 1, 0)] + \
         [("art_GetFilterType grade %d" % g, 0x7E71BD94, lambda v, g=g: {"d0": v, "d1": g}, 0, 0) for g in (1, 2, 3)]


def run(build, fill):
    """{(route, value): (fault, returned d0, instructions in late-loaded space)}"""
    _, blk, _ = patchblock.patched_block0(json.load(open(os.path.join(ROOT, "data", "builds", build + ".json")))["specs"])
    out = {}
    with tempfile.NamedTemporaryFile(suffix=".block0.bin") as f:
        f.write(blk)
        f.flush()
        with Scenario(f.name, name=build) as sc:
            for lo, hi in LATE if fill else ():
                sc.write(lo, b"\xff" * (hi - lo) if fill == "ff" else random.Random(1).randbytes(hi - lo))
            for name, entry, regs, movie, latch in ROUTES:
                for v in range(100, 121):
                    sc.w8(LATCH, latch)
                    sc.w8(LV + 2, 0)
                    sc.w8(LV + 3, v)
                    sc.w32(LV + 32, movie)
                    x = sc.call(entry, regs(v), insn_limit=20000)
                    late = sum(any(lo <= pc < hi for lo, hi in LATE) for pc in x.pcs)
                    out[name, v] = (x.fault, None if x.fault else x.regs["d0"], late)
    return out


def main():
    os.chdir(ROOT)
    pinned, fix = sys.argv[1:3] if len(sys.argv) > 2 else ("cold-start-fix", "film-tables-fix")
    pin, new = run(pinned, None), run(fix, None)
    ok = all(v[0] is None for v in list(pin.values()) + list(new.values()))
    same = sum(new[k][1] == pin[k][1] for k in pin)
    ok &= same == len(pin)
    print(f"copied: {fix} gives what {pinned} gives in {same} of {len(pin)} cases ({len(ROUTES)} routes, values 100 to 120)")
    for name, *_, latch in ROUTES:
        got = [new[name, v][1] for v in HIDDEN]
        ok &= latch == 1 or got == list(HIDDEN.values())
        print(f"  {name}: {', '.join(f'{v} -> {c}' for v, c in zip(HIDDEN, got))}")
    ok &= all(v[2] == 0 for v in new.values())
    for fill in ("ff", "random"):
        cold, old = run(fix, fill), run(pinned, fill)
        good = sum(cold[k] == new[k] for k in new)
        ok &= good == len(new)
        print(f"not copied ({fill}): {fix}: {good} of {len(new)} cases as copied, no fault, 0 instructions in late space")
        bad = {k for k in old if old[k][0] or old[k][2]}
        ok &= bad == {k for k in old if k[1] in HIDDEN}
        print(f"not copied ({fill}): {pinned}: {len(bad)} cases fault or run late space, values "
              f"{sorted({v for _, v in bad})} (first: {next((o[0] for o in old.values() if o[0]), None)})")
    print("RESULT", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
