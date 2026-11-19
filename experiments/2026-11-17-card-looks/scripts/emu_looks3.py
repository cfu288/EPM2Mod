"""builds/card-looks-3.json in the emulator: the acceptance criteria that the emulator can see (design.md section 10).

    uv run python experiments/2026-11-17-card-looks/scripts/emu_looks3.py

Needs build/card-looks-3.BIN, the files that mkspec_looks3.py writes into build/card-looks/ and the settings state
build/emu/state/card-looks-3-p.json (emulator/mkstate builds/card-looks-3.json ... p). Sessions share the
camera's flash. Each dump is compared with the model: the slot tables, the live (member-0) tables and the records
that point at them, the names of the 12 entries in the loaded language, the row's texts and its status.

  1  TEST (C200 "C200" in all 12): start = built-in; menu in and out: nothing; Load: TEST, names, status Loaded
  2  no file, RAM banks dropped: TEST at start, status Off
  3  BAD: refused, TEST stays, status Bad file
  4  PART (2 looks): Load: the two entries change, the other ten are built-in again; their names too
  5  Built-in: built-in tables and names, status Built-in, the store emptied
  6  no file: built-in at start (nothing stored)
  7  no card, Load: status No file, nothing changes
Screenshots of the row and of the Picture Mode list go to build/card-looks/emu/shots-3/.
"""

import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import mkspec_looks as mk  # noqa: E402
import mkspec_looks3 as m3  # noqa: E402
from epm2mod.container import parse  # noqa: E402
from epm2mod.looks import lookfile, lookpack, slots  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

WORK = os.path.join(ROOT, "build", "card-looks")
EMU = os.path.join(WORK, "emu")
V4 = "--v4" in sys.argv    # builds/card-looks-4.json: Load Looks is an added row, after Eye-Fi
N = "4" if V4 else "3"
BUILD = "builds/card-looks-%s.json" % N
RTC = "2026-11-17T12:00:00"
NAV = ("key:MENU key:RIGHT key:OK key:DOWN key:DOWN key:DOWN key:RIGHT " + "key:DOWN " * 9 + "key:RIGHT " +
       "key:DOWN " * (5 if V4 else 4)).split()
LOAD = NAV + ["key:RIGHT", "key:DOWN", "key:OK", "shot:row-ok", "w:1000", "key:UP", "key:DOWN", "shot:row", "key:MENU",
              "key:MENU", "w:1500"]
BUILTIN = NAV + ["key:RIGHT", "key:DOWN", "key:DOWN", "key:OK", "shot:row-ok", "w:1000", "key:UP", "key:DOWN",
                 "shot:row", "key:MENU", "key:MENU", "w:1500"]
# the Picture Mode strip: OK, UP (from WB), then RIGHT from the current mode; from Natural ART 3 is 7 to the right
PMODE = ["key:OK", "w:300", "key:UP"] + ["key:RIGHT"] * 7 + ["shot:art3", "key:RIGHT", "key:RIGHT", "shot:art5", "key:OK"]


def texts_of(path):
    """English strings of block 1 by id."""
    b1 = parse(open(path, "rb").read()).blocks[1].payload
    out = {}
    for i in range(1970):
        p = struct.unpack_from("<I", b1, m3.ENGLISH[0] + 4 * i)[0] - m3.ENGLISH[1]
        e = p
        while b1[e:e + 2] != b"\0\0":
            e += 2
        out[i] = b1[p:e].decode("utf-16-le")
    return out


def main():
    syms = json.load(open(os.path.join(WORK, "syms-%s.json" % N)))
    spans = json.load(open(os.path.join(WORK, "spans-%s.json" % N)))
    b = bytes(open(os.path.join(WORK, "base-%s.block0.bin" % N), "rb").read())
    table = mk.slot_ops(bytearray(b), True)
    eng = texts_of(os.path.join(ROOT, "build", "card-looks-%s.BIN" % N))
    ids, recs, rlive = syms["IDS"], syms["RECS"], syms["RLIVE"]
    paths = RepoPaths(Path(ROOT))
    default = lookpack.load_list(paths, paths.card_looks)
    fit = lookpack.load_fit(paths.resolve("looks/fits/c200.npz"))
    test = [lookpack.look_of_fit(fit, e, "C200", "c200") for e in lookfile.MENU_ENTRIES]
    velvia = lookpack.load_fit(paths.resolve("looks/fits/velvia100.npz"))
    part = [lookpack.look_of_fit(velvia, "Pale&Light Color", "Velvia 2", "v"),
            lookpack.look_of_fit(fit, "Grainy Film", "C200 in 4", "c")]
    files = {"TEST": lookfile.pack(test), "PART": lookfile.pack(part)}
    bad = bytearray(files["TEST"])
    bad[5000] ^= 1
    files["BAD"] = bytes(bad)

    w = lambda img, a: struct.unpack_from("<I", img, a - mk.BASE)[0]
    tbl = lambda img, a: list(struct.unpack_from("<256H", img, a - mk.BASE))
    dr = [w(b, slots.DEFAULT_RECORD + 4 * i) for i in range(8)]

    def expect(looks):
        """What the dump must show after the looks (a list, or None for the built-in looks) are applied."""
        img = bytearray(b)
        if looks:
            mk.model_apply(img, lookfile.pack(looks), table)
        tables = "".join(bytes(img[a - mk.BASE: a - mk.BASE + n]).hex() for a, n in spans)
        live = bytearray(36 * 4 * 512)
        rec_hash = {}
        for s in range(12):
            for ch in range(3):
                r = recs[s][ch]
                if not r:
                    continue
                i = 3 * s + ch
                t1 = tbl(img, w(img, r + 4))
                rec = list(struct.unpack_from("<8I", img, r - mk.BASE))
                for m in range(4):
                    live[(4 * i + m) * 512:(4 * i + m + 1) * 512] = struct.pack(
                        "<256H", *m3.interp(t1, tbl(b, dr[1]), tbl(b, dr[2 * m])))
                    rec[2 * m] = rlive + (4 * i + m) * 512
                rec_hash["r%d" % i] = hashlib.sha256(struct.pack("<8I", *rec)).hexdigest()
        names = {}
        by_slot = {look.slot: look for look in looks or []}
        for s in range(12):
            for tid in ids[s]:
                orig = eng[tid]
                if s in by_slot and by_slot[s].name:
                    tag = orig[:orig.index("@", 1) + 1] if orig.startswith("@") else ""
                    names[str(tid)] = tag + by_slot[s].name
                else:
                    names[str(tid)] = orig
        return tables, hashlib.sha256(live).hexdigest(), rec_hash, names

    hash_env = ",".join(["live:%d:%d" % (rlive + 0x40000000, 36 * 4 * 512)] +
                        ["r%d:%d:32" % (3 * s + ch, recs[s][ch] + 0x40000000)
                         for s in range(12) for ch in range(3) if recs[s][ch]])
    text_ids = [t for s in range(12) for t in ids[s]] + [1495, 1496, 1497, 1498, 1503]
    fixed = {"1498": "Load Looks", "1496": "Load", "1497": "Load film looks from\r\nEPM2LOOK.BIN on the card.",
             "1503": "Built-in"}

    os.makedirs(EMU, exist_ok=True)
    state = os.path.join(EMU, "state-%s.json" % N)
    shutil.copy(os.path.join(ROOT, "build/emu/state/card-looks-%s-p.json" % N), state)

    def session(n, card, steps, drop_ram):
        env = dict(os.environ, E101_STATE=state, E101_RTC=RTC, SPANS=os.path.join(WORK, "spans-%s.json" % N),
                   SYMS=os.path.join(WORK, "syms-%s.json" % N), SHOTS=os.path.join(EMU, "shots-%s" % N, "s%d" % n),
                   TEXTS=",".join(map(str, text_ids)), HASH=hash_env)
        if drop_ram:
            doc = json.load(open(state))
            doc.pop("ram", None)
            json.dump(doc, open(state, "w"))
        if card is not None:
            folder = os.path.join(EMU, "card3-%d" % n)
            shutil.rmtree(folder, ignore_errors=True)
            os.makedirs(os.path.join(folder, "DCIM", "100OLYMP"))
            for name, data in card.items():
                open(os.path.join(folder, name), "wb").write(data)
            env["E101_CARD"] = folder
        else:
            env.pop("E101_CARD", None)
        out = subprocess.run([os.path.join(ROOT, "emulator/emu-run"), BUILD, os.path.join(HERE, "emu_looks.mjs"),
                              *steps], cwd=ROOT, env=env, capture_output=True, text=True)
        lines = [json.loads(l) for l in out.stdout.splitlines() if l.startswith("{")]
        if out.returncode:
            print(out.stdout[-3000:], out.stderr[-3000:])
            raise SystemExit("session %d: exit %d" % (n, out.returncode))
        return {l["dump"]: l for l in lines if "dump" in l}, lines[-1]

    ok = True

    def check(n, name, d, looks, status, store_magic=None):
        nonlocal ok
        tables, live, recs_h, names = expect(looks)
        got_names = {k: v for k, v in d["texts"].items() if k in names}
        res = {
            "tables": d["tables"] == tables,
            "live": d["hashes"]["live"] == live,
            "records": all(d["hashes"][k] == v for k, v in recs_h.items()),
            "names": got_names == names,
            "row texts": all(d["texts"][k] == v for k, v in fixed.items()),
            "status": d["texts"]["1495"] == status,
        }
        if store_magic is not None:
            res["store"] = d["store"][:8] == store_magic
        good = all(res.values())
        ok &= good
        bad = [k for k, v in res.items() if not v]
        ev = " ".join("%s@%s%s" % (e[1], e[0], "(%d)" % e[2] if len(e) > 2 else "") for e in d["events"])
        print("s%d %-6s %s%s | status %r | %s" % (n, name, "PASS" if good else "FAIL " + ",".join(bad), "",
                                                 d["texts"]["1495"], ev))
        if "names" in bad:
            for k in names:
                if got_names.get(k) != names[k]:
                    print("   id %s: %r, model %r" % (k, got_names.get(k), names[k]))

    plan = [
        (1, {"EPM2LOOK.BIN": files["TEST"]}, False,
         ["dump:start", "key:MENU", "key:RIGHT", "key:OK", "key:MENU", "w:1500", "dump:menu"] + LOAD + ["dump:load"]
         + PMODE, [("start", None, "Off", None), ("menu", None, "Off", None), ("load", test, "Loaded", "45504c4b")]),
        (2, {}, True, ["dump:start"] + NAV + ["shot:row"], [("start", test, "Off", "45504c4b")]),
        (3, {"EPM2LOOK.BIN": files["BAD"]}, True, ["dump:start"] + LOAD + ["dump:load"],
         [("start", test, "Off", None), ("load", test, "Bad file", None)]),
        (4, {"EPM2LOOK.BIN": files["PART"]}, True, ["dump:start"] + LOAD + ["dump:load"] + PMODE,
         [("start", test, "Off", None), ("load", part, "Loaded", "45504c4b")]),
        (5, {}, True, ["dump:start"] + BUILTIN + ["dump:built"] + PMODE,
         [("start", part, "Off", None), ("built", None, "Built-in", "00000000")]),
        (6, {}, True, ["dump:start"], [("start", None, "Off", "00000000")]),
        (7, None, True, ["dump:start"] + LOAD + ["dump:load"], [("start", None, "Off", None),
                                                               ("load", None, "No file", None)]),
    ]
    for n, card, drop, steps, checks in plan:
        dumps, last = session(n, card, steps, drop)
        for name, looks, status, magic in checks:
            check(n, name, dumps[name], looks, status, magic)
        print("s%d end: lab ms %s, problems %s, firmware errors %d" % (
            n, last.get("done"), last.get("problems"), len(last.get("errors", []))))
    print("ALL PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
