"""Live-view scenario of the film entries, with and without focus peaking. Uses emulator/liveview.py.

    .venv/bin/python experiments/2026-11-16-films-max/scripts/scen_films.py BLOCK0 [VALUE ...]

BLOCK0 is the block 0 of a films build (tools/oetool.py unpack, or the block-0 file of emulator/patchblock.py).
For each stored Picture Mode VALUE (default: the twelve values of the films-12 lists, and 119, the value that
focus peaking forces) the rig runs the firmware's own live-view tasks (experiments/2026-11-14-focus-peaking,
NOTES section 13.1) for three frames without the MF Assist request and three frames with it (Peaking = White).

Reported per value: the code byte of the mov layer (0xA07507CC; see EXPECT), a picture in every frame, firmware
anomalies (no picture, refused art buffers, heap re-partition under live blocks, error reports, faults), and with
the request: L = 1, the Key Line line job ran (pass 9 gain 0x0200 = white lines, pass 7 ucExpose 3).
PASS = no anomaly, the expected code byte without the request, and lines with it. No pixel is computed.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PEAKING = os.path.join(ROOT, "experiments", "2026-11-14-focus-peaking", "scripts")
sys.path.insert(0, os.path.join(ROOT, "emulator"))
sys.path.insert(0, PEAKING)
sys.path.insert(0, os.path.join(ROOT, "src"))

from liveview import EXPOSE  # noqa: E402

from epm2mod.looks import slots  # noqa: E402

# scen_menu.py runs its main() when it is imported. Take its helpers without that last line.
_src = open(os.path.join(PEAKING, "scen_menu.py")).read().rstrip()
assert _src.endswith("\nmain()")
_sm = {"__file__": os.path.join(PEAKING, "scen_menu.py"), "__name__": "scen_menu"}
_argv, sys.argv = sys.argv, sys.argv[:1]
exec(compile(_src[: -len("main()")], "scen_menu.py", "exec"), _sm)
sys.argv = _argv
open_lv, request, anomalies, flags, TAG, L = (_sm[k] for k in ("open_lv", "request", "anomalies", "flags", "TAG", "L"))
WHITE = 3
# The byte 0xA07507CC after a frame. It is the art code for most entries. For the Soft Focus entry (value 101,
# art code 102; camera-tested in the pinned build) it reads 0 in this rig, and so it does for the new art codes.
EXPECT = {100: 70, 101: 0, 102: 71, 103: 72, 105: 145, 106: 167, 107: 85, 119: 163}
EXPECT.update({slot.value: 0 for slot in slots.EXTRA_SLOTS})


def main():
    path = sys.argv[1]
    values = [int(v) for v in sys.argv[2:]] or [100, 101, 102, 103, 111, 105, 106, 107, 112, 114, 115, 118, 119]
    bad = 0
    for value in values:
        with open_lv(path, "films", value) as lv:
            lv.settings[TAG] = WHITE
            lv.start()
            plain = [lv.frame() for _ in range(3)]
            code = lv.sc.r8(EXPOSE)
            odd = sorted(set(a for f in plain for a in anomalies(lv, f)))
            lv.seen["gain2"], lv.seen["expose7"] = [], []
            request(lv, True)
            lined = [lv.frame() for _ in range(3)]
            odd2 = sorted(set(a for f in lined for a in anomalies(lv, f)))
            gains, exposes = sorted(set(lv.seen["gain2"])), sorted(set(lv.seen["expose7"]))
            code2, latch = lv.sc.r8(EXPOSE), lv.sc.r8(L)
            ok = (not odd and not odd2 and code == EXPECT.get(value, code) and latch == 1 and gains == [0x0200]
                  and exposes == [3] and all(f.state["picture"] for f in plain + lined))
            bad += not ok
            print("%s value %3d: code byte %3d (expected %s), picture in %d of 3 frames, anomalies %s | with the request: "
                  "%s, code byte %d, picture in %d of 3 frames, pass 9 gain %s, pass 7 ucExpose %s, anomalies %s" % (
                      "PASS" if ok else "FAIL", value, code, EXPECT.get(value, "?"), sum(bool(f.state["picture"]) for f in plain),
                      odd or "none", flags(lv), code2, sum(bool(f.state["picture"]) for f in lined),
                      ["0x%04X" % g for g in gains], exposes, odd2 or "none"), flush=True)
    print("live-view scenario: %s (%d values, %d failing)" % ("PASS" if not bad else "FAIL", len(values), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
