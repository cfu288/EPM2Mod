"""Function harness: the parts of MOV_TASK's live-view frame pass that follow the routes, with segments 2 and 3 not
copied (0xFF): 0x7E6C5A23 (called at 0x7E6C3433) and the live-view start 0x7E6C410A (called from 0x7E6C3FD8, which
0x7E6C3447 calls next). For Picture Mode 1 (Natural), 100 and the five hidden values: how each run ends and which of
MARKS it reached. The state is the harness's, not a live view's: a run that returns proves only the code it reached.

    uv run python experiments/2026-11-25-film-tables/scripts/frame_pass.py BUILD...
"""
import json, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "emulator")]
import bootmem  # noqa: E402
import patchblock  # noqa: E402
from scenario import Scenario  # noqa: E402

LV, LATE = 0x605B1CD0, [(x.lo, x.hi) for x in bootmem.model().loads if x.name in ("segment-2", "segment-3", "usr1-third")]
MARKS = {0x7E6CBFD3: "mov_art", 0x7E6DBA95: "0x7E6DBA95", 0x7E71BD94: "art_GetFilterType", 0x7E57A028: "0x7E57A028",
         0x7E56C6A5: "matrix hook", 0x7E546160: "hue hook", 0x7E56B790: "tone stage"}

os.chdir(ROOT)
for build in sys.argv[1:]:
    _, blk, _ = patchblock.patched_block0(json.load(open(f"data/builds/{build}.json"))["specs"])
    with tempfile.NamedTemporaryFile(suffix=".block0.bin") as f:
        f.write(blk)
        f.flush()
        for entry, regs, frame in ((0x7E6C5A23, {"a0": 0x605B0584}, (0xF0, 16)), (0x7E6C410A, {"a0": 0x605B03CC}, (0, 0))):
            for v in (1, 100, 111, 112, 114, 115, 118):
                with Scenario(f.name, name=build) as sc:
                    for lo, hi in LATE:
                        sc.write(lo, b"\xff" * (hi - lo))
                    sc.w8(LV + 2, 0)
                    sc.w8(LV + 3, v)
                    sc.w32(LV + 32, 0)
                    x = sc.call(entry, regs, frame=frame, insn_limit=400000)
                    seen = [MARKS[pc] for pc in dict.fromkeys(x.pcs) if pc in MARKS]
                    late = sum(any(lo <= pc < hi for lo, hi in LATE) for pc in x.pcs)
                    end = str(x.fault or x.blocked or "returned")[:60]
                    print(f"{build} 0x{entry:08X} mode {v}: {end}; late {late}; reached {', '.join(seen)}")
