"""Scenario check of data/specs/movie-wide-frame.json in the live-view rig (emulator/liveview.py). NOTES.md section 12.

    uv run python experiments/2026-11-19-movie-sampling/scripts/scen_wide.py BASE_BLOCK0 WIDE_BLOCK0
    BASE  block0_0100.bin of build/debug-log-movie-bitrate.BIN (tools/oetool.py unpack)
    WIDE  block0_0100.bin of build/debug-log-movie-wide.BIN

On each image: the mov layer's own start and Through Start (it builds the movie mode table, 0x7E6C410A), Natural,
movie size 6 (1080), then frames with the camera record saying sensor mode HSHR (the camera core is not in the rig,
so the record is written here). Read back: the HSHR record of the movie mode table, and at each run of the IMG
resize builders 0x7E54A0D0 / 0x7E54A468 the HSHR branch (IMG mode 5) with its products and the Q12 steps that it
stores. Pass = the record as the model (stock 1680/1662/1312/1646/1296, centre 831, IS crop 1414; wide
1960/1938/1312/1920/1296, centre 969, IS crop 1650), and no fault in Through Start and three frames. The builders'
steps (stock H 3511, wide H 4096, V 4915) are printed when the rig reaches them; it does not (2026-11-19 run): the
develop job runs on the camera core's path, which the rig does not have. Nor can it show the sensor, the
pre-processor, pixel data or timing.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "emulator"))
from liveview import LiveView  # noqa: E402

PM, NATURAL, MOVIE_SIZE = 38017, 2, 34145
HSHR_REC = 0x605B0882                 # movie mode table, record 3 (HSHR), 30 bytes
CAM_INDEX, CAM_RECORDS = 0x605B10A4, 0x605B0FF4
PROBES = {0x7E54A2CE: "A: IMG mode 5 branch", 0x7E54A5E9: "B: IMG mode 5 branch",
          0x7E54A381: "A: store steps", 0x7E54A697: "B: store steps",
          0x7E54A0D0: "A: entry", 0x7E54A468: "B: entry", 0x7E6C410A: "through start handler",
          0x7E6C7656: "movie request builder", 0x7E6C6853: "mov_image_process (through)"}
MODEL = {"base": ((1680, 1662, 1312, 1646, 1296), 1414, ((1646 - 1) << 12) // (1920 - 1)),
         "wide": ((1960, 1938, 1312, 1920, 1296), 1650, ((1920 - 1) << 12) // (1920 - 1))}
V_STEP = ((1296 - 1) << 12) // (1080 - 1)


def run(path, name):
    """Through Start and three HSHR frames. Returns (record fields, IS crop width, [(probe, regs)], fault text)."""
    seen = []
    with LiveView(path, name=name) as lv:
        lv.settings[PM] = NATURAL
        lv.settings[MOVIE_SIZE] = 6
        for addr, what in PROBES.items():
            lv.sc.probe(addr, lambda sc, g, what=what: seen.append((what, dict(g))), what)
        f = lv.start()
        faults = list(f.faults) if f.faults else []
        idx = lv.sc.r16(CAM_INDEX)
        lv.sc.write(CAM_RECORDS + 136 * idx + 4, struct.pack("<I", 4))        # camera record: sensor mode HSHR
        for _ in range(3):
            f = lv.frame()
            faults += list(f.faults) if f.faults else []
        rec = struct.unpack("<15H", lv.sc.read(HSHR_REC, 30))
        return rec, seen, faults


def main():
    """Run both images and compare with the model."""
    ok_all = True
    for name, path in (("base", sys.argv[1]), ("wide", sys.argv[2])):
        rec, seen, faults = run(path, name)
        geom, is_w, hstep = MODEL[name]
        rec_ok = (rec[0], rec[1], rec[2], rec[3], rec[4]) == geom and rec[9] == is_w
        print("%s: HSHR record stride/width/height/eff w/eff h = %s, centre %d/%d, IS crop %d x %d: %s" % (
            name, rec[:5], rec[5], rec[6], rec[9], rec[10], "as the model" if rec_ok else "NOT as the model %s" % (geom,)))
        steps = [(w, g["d0"], g["d2"]) for w, g in seen if w.startswith("A: store")] + \
                [(w, g["a3"], g["d3"]) for w, g in seen if w.startswith("B: store")]
        branch = [w for w, g in seen if "branch" in w]
        print("  reached:", sorted(set(w for w, g in seen)))
        print("  IMG builders: %d runs of the HSHR branch (%s); steps stored (H, V): %s" % (
            len(branch), ", ".join(sorted(set(branch))) or "none", sorted(set((h, v) for w, h, v in steps)) or "none"))
        st_ok = bool(branch) and all((h, v) in ((hstep, V_STEP), (min(hstep, V_STEP), min(hstep, V_STEP)))
                                     for w, h, v in steps if w.startswith("A") or True) and bool(steps)
        print("  model: H step %d, V step %d -> %s" % (hstep, V_STEP, "as the model" if st_ok else ("not reached in the rig" if not steps else "NOT as the model")))
        if faults:
            print("  faults:", faults)
        # The rig does not reach the IMG resize builders (they run inside img_exec on the camera core's develop path,
        # which the rig does not run): the steps are reported, not required.
        ok_all &= rec_ok and not faults
    print("RESULT: %s" % ("PASS" if ok_all else "FAIL"))
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
