"""Scenario check of data/specs/movie-ab.json (NOTES.md section 16): both value sets, chosen by the record mode.

    uv run python experiments/2026-11-19-movie-sampling/scripts/scen_ab.py BASE_BLOCK0 AB_BLOCK0
    BASE  block0_0100.bin of build/debug-log-movie-bitrate.BIN (tools/oetool.py unpack)
    AB    block0_0100.bin of build/debug-log-movie-ab.BIN

For each record mode (setting 34145 and setting 33105 index 7, through the firmware's own settings getter): Full HD
Fine (6, 1), Full HD Normal (6, 0), HD Fine (3, 1), each on the AB image, and Full HD Fine on BASE. In order, as one
set-up runs them:
  1. the writer request builder 0x7E5A897F for mode code 517 (T_REQ, which runs SETW): line width, resize block;
  2. the TAKE request builder's HSHR case, as a piece from 0x7E59EE7E to 0x7E59EE90 (T_TAKE): +6, +8, +10;
  3. the movie mode table: Through Start in the live-view rig (T_TAB): the HSHR record;
  4. the readers that use the stored choice, each as a piece: Movie IS crop (+116), Movie IS divisor (d2), the two
     IMG divisors (d0 after `divu`), art_get_bayer_size(5) (its record);
  5. the Debug Log ring: one mv_set per set-up step with the choice.
Pass = Full HD Fine on AB gives every value of movie-wide-frame.json and movie-wide-writer.json; Full HD Normal and HD
Fine on AB give exactly the values of BASE; one mv_set record with the right choice for each of steps 1 to 3.
The rig has no sensor, no pre-processor and no IMG engine: it shows which values the firmware is given, not the picture.
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "emulator"))
sys.path.insert(0, os.path.join(ROOT, "cli", "src"))
from liveview import LiveView  # noqa: E402
from epm2mod.eventlog import decode, load_dictionary  # noqa: E402

RING0, UNCACHED, LOGON = 0x7E4F9000, 0x40000000, 0x7E4FD042
WORDS = load_dictionary(json.load(open(os.path.join(ROOT, "data", "logdict", "events.json"))))
SCR = 0x7D210000
HSHR_REC, CAM_INDEX, CAM_RECORDS = 0x605B0882, 0x605B10A4, 0x605B0FF4
MODES = {"Full HD Fine": (6, 1), "Full HD Normal": (6, 0), "HD Fine": (3, 1)}
WIDE = {"writer": (1960, 1433, 4915), "take": (1938, 1312, 1920), "table": (1960, 1938, 1312, 1920, 969, 1650),
        "is_crop": 1650, "is_div": 78643, "img": 1920, "bayer": (1960, 1938, 1312, 0, 1920, 1296, 969, 656)}
STOCK = {"writer": (1680, 1843, 5734), "take": (1662, 1312, 1646), "table": (1680, 1662, 1312, 1646, 831, 1414),
         "is_crop": 1414, "is_div": 91750, "img": 1646, "bayer": (1680, 1662, 1312, 0, 1646, 1296, 831, 656)}


def ring(sc):
    """mv_set records of the CPU 0 ring, decoded."""
    magic, w = struct.unpack("<2I", sc.read(RING0 + UNCACHED, 8))
    if magic != 0x314C5045 or not w:
        return []
    first = max(0, w - 512)
    data = struct.pack("<4sBBBB8sIIII", b"EPLG", 1, 16, 0, 32, WORDS.build_id, first, w - first, 0, 1)
    data += b"".join(sc.read(RING0 + UNCACHED + 32 + 16 * (i & 511), 16) for i in range(first, w))
    return [e["args"]["wide"] for e in decode(data, WORDS) if e.get("event") == "mv_set"]


def run(path, name, quality, fine):
    """One set-up in the record mode (quality, fine). Returns {value: ...} and the mv_set choices."""
    out = {}
    with LiveView(path, name=name) as lv:
        sc = lv.sc
        lv.settings[38017] = 2                      # Natural
        lv.settings[(34145, 0)] = quality
        lv.settings[(33105, 7)] = fine
        sc.write(RING0 + UNCACHED, struct.pack("<5I", 0x314C5045, 0, 0, 0, 0) + b"\0" * 4 + struct.pack("<I", 0xFFFFFFFF))
        sc.write(LOGON + UNCACHED, b"\x01")         # Debug Log On
        # 1. writer request (mode code 517)
        sc.write(SCR, b"\0" * 64)
        r = sc.call(0x7E5A897F, {"d0": 517, "d1": 0, "a0": SCR, "a1": 0}, frame=(0xF0, 44))
        out["writer"] = (sc.r16(SCR + 4), sc.r16(SCR + 48), sc.r16(SCR + 54))
        out["faults"] = [r.fault] if r.fault else []
        out["regs"] = {"writer": r.regs}
        # 2. TAKE request builder, HSHR case (a0 = d3 = the request)
        sc.write(SCR + 0x100, b"\0" * 32)
        r = sc.piece(0x7E59EE7E, [0x7E59EE90], {"a0": SCR + 0x100, "d3": SCR + 0x100})
        out["take"] = (sc.r16(SCR + 0x106), sc.r16(SCR + 0x108), sc.r16(SCR + 0x10A))
        out["regs"]["take"] = r.regs
        out["faults"] += [r.fault] if r.fault else []
        # 3. movie mode table: Through Start and three HSHR frames
        f = lv.start()
        sc.write(CAM_RECORDS + 136 * sc.r16(CAM_INDEX) + 4, struct.pack("<I", 4))
        for _ in range(3):
            f = lv.frame()
            out["faults"] += list(f.faults or [])
        rec = struct.unpack("<15H", sc.read(HSHR_REC, 30))
        out["table"] = (rec[0], rec[1], rec[2], rec[3], rec[5], rec[9])
        # 4. readers
        sc.write(SCR + 0x200, b"\0" * 128)
        r = sc.piece(0x7E6CB8B3, [0x7E6CB8B9], {"a2": SCR + 0x200})
        out["is_crop"] = sc.r16(SCR + 0x200 + 116)
        r2 = sc.piece(0x7E6CB981, [0x7E6CB987], {})
        out["is_div"] = r2.regs["d2"]
        r3 = sc.piece(0x7E54A2CE, [0x7E54A2D3], {"d1": 3686400, "mdr": 0})
        r4 = sc.piece(0x7E54A5E9, [0x7E54A5EE], {"d2": 3686400, "mdr": 0})
        out["img"] = (r3.regs["d0"], r4.regs["d0"])
        r5 = sc.call(0x7E7290B5, {"d0": 5}, frame=(0x80, 8))
        out["bayer"] = struct.unpack("<8H", sc.read(r5.regs["a0"], 16)) if not r5.fault else None
        out["faults"] += [x.fault for x in (r, r2, r3, r4, r5) if x.fault]
        out["regs"].update({"is_crop": r.regs, "is_div": r2.regs, "img1": r3.regs, "img2": r4.regs, "bayer": r5.regs})
        out["mv_set"] = ring(sc)
    return out


def main():
    """Run the record modes and compare with the two value sets."""
    ok_all = True
    runs = {}
    cases = [("BASE", sys.argv[1], "Full HD Fine")] + [("AB", sys.argv[2], m) for m in MODES]
    for img, path, mode in cases:
        q, fine = MODES[mode]
        o = run(path, img, q, fine)
        runs[(img, mode)] = o
        wide = img == "AB" and mode == "Full HD Fine"
        want = WIDE if wide else STOCK
        got = {k: o[k] for k in want if k != "img"}
        ok = all(got[k] == want[k] for k in got) and o["img"] == (want["img"], want["img"]) and not o["faults"]
        logs_ok = img == "BASE" or o["mv_set"] == [1 if wide else 0] * 3
        ok_all &= ok and logs_ok
        print("%-4s %-15s -> %s set: %s; mv_set %s %s" % (img, mode, "wide" if wide else "stock",
                                                          "as the model" if ok else "NOT as the model", o["mv_set"],
                                                          "ok" if logs_ok else "NOT as expected"))
        for k in ("writer", "take", "table", "is_crop", "is_div", "img", "bayer"):
            print("    %-8s %s" % (k, o[k]))
        if o["faults"]:
            print("    faults:", o["faults"])
    # With the stock choice, every piece and call ends with the registers of BASE (mdr and the flags left out: the
    # routines call SETW or compare). Pass = equal.
    keys = ("pc", "sp", "d0", "d1", "d2", "d3", "a0", "a1", "a2", "a3", "lir", "lar")
    a, b = runs[("BASE", "Full HD Fine")]["regs"], runs[("AB", "Full HD Normal")]["regs"]
    diff = {k: [r for r in keys if a[k][r] != b[k][r]] for k in a}
    regs_ok = not any(diff.values())
    ok_all &= regs_ok
    print("registers at the end of each piece and call, AB Full HD Normal against BASE: %s" % (
        "equal" if regs_ok else "DIFFER %s" % diff))
    print("RESULT: %s" % ("PASS" if ok_all else "FAIL"))
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
