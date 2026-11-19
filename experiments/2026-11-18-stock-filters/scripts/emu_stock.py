"""data/builds/stock-films.json in the emulator: what the loader does to the switched words and the entries' RAM blocks
(design.md, F1 and F2). Research code.

    uv run python experiments/2026-11-18-stock-filters/scripts/emu_stock.py

Needs build/stock-films.BIN (epm2mod make stock-films), build/stock-films/{layout,syms}.json and the state
build/emu/state/stock-films-p.json. Sessions share the camera's flash; each dump is compared with a model:
  switch words: for each entry the film bytes when the stored file lists it, else the stock bytes (F1, F2);
  RAM blocks: each listed entry's block equals APPLY of its record (Python model) on a zero block;
  names: listed entries show the film's name, the others the stock name; the row's status text.

  1  F12 (the 12 default films) on the card: at start nothing is stored (all stock); Load: all 12 film
  2  no file, RAM banks dropped: the stored file is applied at start (all 12 film)
  3  PART (Velvia in Pop Art, C200 in Key Line): Load: only those two entries film
  4  EMPTY (a file with no film): Load: all stock again
  5  BAD (PART with one byte changed): refused, still all stock
  6  no card, RAM banks dropped: all stock
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
CL = os.path.join(ROOT, "experiments", "2026-11-17-card-looks", "scripts")
sys.path.insert(0, CL)
sys.path.insert(0, os.path.join(ROOT, "src"))
_argv, sys.argv = sys.argv, [sys.argv[0], "--v4"]
import mkspec_looks as mk  # noqa: E402
import mkspec_looks3 as m3  # noqa: E402
import emu_looks3 as e3  # noqa: E402
sys.argv = _argv
from epm2mod.container import parse  # noqa: E402
from epm2mod.looks import lookfile, lookpack, slots  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

WORK = os.path.join(ROOT, "build", "stock-films")
EMU = os.path.join(WORK, "emu")
BUILD = "data/builds/stock-films.json"
RTC = "2026-11-18T12:00:00"


def main():
    layout = json.load(open(os.path.join(WORK, "layout.json")))
    syms = json.load(open(os.path.join(WORK, "syms.json")))
    stock = parse(open(os.path.join(ROOT, "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"), "rb").read()).blocks[0].payload
    get = lambda a, n: stock[a - mk.BASE:a - mk.BASE + n]
    eng = e3.texts_of(os.path.join(ROOT, "build", "stock-films.BIN"))
    ids = syms["IDS"]
    paths = RepoPaths(Path(ROOT))

    # the operation list relative to a block, as gen/stock-films/loader.py builds it
    off = layout["offsets"]
    defaults = [struct.unpack("<I", get(slots.DEFAULT_RECORD + 4 * i, 4))[0] for i in range(slots.RECORD_TABLES)]
    ops = [(20, 2, off["sat"], 0), (20, 2, off["sat"] + 2, 0), (22, 12, off["six_s"], 0), (34, 12, off["six_h"], 0),
           (46, 18, off["matrix"], 0), (64, 97, off["chroma"], 0)]
    for ch in range(3):
        src = 164 + ch * lookfile.CURVE_BYTES
        ops += [(src, 256, off["tone"] + 512 * (8 * ch + i), defaults[i]) for i in range(8)]

    def block_of(look):
        """The entry's RAM block after APPLY of one look (a zero block before)."""
        img = bytearray(stock) + bytearray(0x40000)
        rec = lookfile.pack([look])[32:]
        base = len(stock)
        for o, n, a, d in ops:
            if not d:
                img[base + a: base + a + n] = rec[o:o + n]
                continue
            v, i, p, out = struct.unpack_from("<H", rec, o)[0], 0, o + 2, []
            for k in range(n):
                target = struct.unpack_from("<H", stock, d - mk.BASE + 2 * k)[0]
                while i < target:
                    v += (rec[p] >> 4) if i & 1 else (rec[p] & 15)
                    p += i & 1
                    i += 1
                out.append(min(v, 1023))
            img[base + a: base + a + 2 * n] = struct.pack("<%dH" % n, *out)
        return hashlib.sha256(bytes(img[base: base + layout["block"]])).hexdigest()

    words = [(w["address"], len(bytes.fromhex(w["film"]))) for e in layout["entries"] for w in e["switch"]]

    def expect_words(listed):
        out = ""
        for k, e in enumerate(layout["entries"]):
            for w in e["switch"]:
                out += w["film"] if k in listed else w["stock"]
        return out

    f12 = lookpack.load_list(paths, paths.card_looks)
    assert [x.slot for x in f12] == list(range(12))
    velvia = lookpack.load_fit(paths.resolve("data/films/fits/velvia100.npz"))
    c200 = lookpack.load_fit(paths.resolve("data/films/fits/c200.npz"))
    part = [lookpack.look_of_fit(velvia, "Pop Art", "Velvia T", "v"), lookpack.look_of_fit(c200, "Key Line", "C200 T", "c")]
    files = {"F12": lookfile.pack(f12), "PART": lookfile.pack(part), "EMPTY": lookfile.pack([])}
    bad = bytearray(files["PART"])
    bad[2000] ^= 1
    files["BAD"] = bytes(bad)

    spans_file = os.path.join(WORK, "spans.json")
    json.dump([[a, n] for a, n in words], open(spans_file, "w"))
    hash_env = ",".join("b%d:%d:%d" % (k, layout["film_ram"] + layout["block"] * k + 0x40000000, layout["block"])
                        for k in range(12))
    text_ids = [t for s in range(12) for t in ids[s]] + [1495]
    os.makedirs(EMU, exist_ok=True)
    state = os.path.join(EMU, "state.json")
    shutil.copy(os.path.join(ROOT, "build/emu/state/stock-films-p.json"), state)
    syms_file = os.path.join(WORK, "syms-emu.json")
    json.dump({k: syms[k] for k in ("T_TASK", "V_BAD", "V_OK", "SAVE", "APPLY", "T_END", "FLAGS", "STORE")},
              open(syms_file, "w"))

    def session(n, card, steps, drop_ram):
        env = dict(os.environ, E101_STATE=state, E101_RTC=RTC, SPANS=spans_file, SYMS=syms_file,
                   SHOTS=os.path.join(EMU, "shots", "s%d" % n), TEXTS=",".join(map(str, text_ids)), HASH=hash_env)
        if drop_ram:
            doc = json.load(open(state))
            doc.pop("ram", None)
            json.dump(doc, open(state, "w"))
        if card is not None:
            folder = os.path.join(EMU, "card-%d" % n)
            shutil.rmtree(folder, ignore_errors=True)
            os.makedirs(os.path.join(folder, "DCIM", "100OLYMP"))
            for name, data in card.items():
                open(os.path.join(folder, name), "wb").write(data)
            env["E101_CARD"] = folder
        else:
            env.pop("E101_CARD", None)
        out = subprocess.run([os.path.join(ROOT, "emulator/emu-run"), BUILD, os.path.join(CL, "emu_looks.mjs"), *steps],
                             cwd=ROOT, env=env, capture_output=True, text=True)
        lines = [json.loads(l) for l in out.stdout.splitlines() if l.startswith("{")]
        if out.returncode:
            print(out.stdout[-3000:], out.stderr[-3000:])
            raise SystemExit("session %d: exit %d" % (n, out.returncode))
        return {l["dump"]: l for l in lines if "dump" in l}, lines[-1]

    ok = True

    def check(n, name, d, looks, status):
        nonlocal ok
        listed = {x.slot: x for x in looks}
        names = {}
        for s in range(12):
            for tid in ids[s]:
                orig = eng[tid]
                if s in listed and listed[s].name:
                    tag = orig[:orig.index("@", 1) + 1] if orig.startswith("@") else ""
                    names[str(tid)] = tag + listed[s].name
                else:
                    names[str(tid)] = orig
        got_names = {k: v for k, v in d["texts"].items() if k in names}
        res = {"switch words": d["tables"] == expect_words(set(listed)),
               "blocks": all(d["hashes"]["b%d" % s] == block_of(listed[s]) for s in listed),
               "names": got_names == names, "status": d["texts"]["1495"] == status}
        good = all(res.values())
        ok &= good
        bad = [k for k, v in res.items() if not v]
        ev = " ".join("%s@%s" % (e[1], e[0]) for e in d["events"])
        print("s%d %-6s %s | listed %s | status %r | %s" % (n, name, "PASS" if good else "FAIL " + ",".join(bad),
                                                          sorted(listed), d["texts"]["1495"], ev))
        if "switch words" in bad:
            want, got, at = expect_words(set(listed)), d["tables"], 0
            for (a, sz) in words:
                if want[at:at + 2 * sz] != got[at:at + 2 * sz]:
                    print("   %#x: %s, model %s" % (a, got[at:at + 2 * sz], want[at:at + 2 * sz]))
                at += 2 * sz

    load, pmode = e3.LOAD, e3.PMODE
    # the quick menu's Picture Mode: from Natural, 7 to the right is ART 3, 15 is ART 11 (Key Line)
    pick_kl = ["key:OK", "w:300", "key:UP"] + ["key:RIGHT"] * 15 + ["shot:kl-before", "key:OK", "w:500"]
    show_pm = ["key:OK", "w:300", "key:UP", "w:300", "shot:pm-now", "key:OK", "w:500"]
    plan = [
        (1, {"EPM2LOOK.BIN": files["F12"]}, False, ["dump:start"] + load + ["dump:load"] + pmode,
         [("start", [], "Off"), ("load", f12, "Loaded")]),
        (2, {}, True, ["dump:start"] + pmode, [("start", f12, "Off")]),
        (3, {"EPM2LOOK.BIN": files["PART"]}, True, ["dump:start"] + pick_kl + load + ["dump:load"] + show_pm,
         [("start", f12, "Off"), ("load", part, "Loaded")]),
        (4, {"EPM2LOOK.BIN": files["EMPTY"]}, True, show_pm[:-2] + ["shot:pm-start", "key:OK", "w:500"] + load +
         ["dump:load"] + show_pm, [("load", [], "Loaded")]),
        (5, {"EPM2LOOK.BIN": files["BAD"]}, True, load + ["dump:load"], [("load", [], "Bad file")]),
        (6, None, True, ["dump:start"], [("start", [], "Off")]),
    ]
    for n, card, drop, steps, checks in plan:
        dumps, last = session(n, card, steps, drop)
        for name, looks, status in checks:
            check(n, name, dumps[name], looks, status)
        print("s%d end: lab ms %s, problems %s, firmware errors %d" % (
            n, last.get("done"), last.get("problems"), len(last.get("errors", []))))
    print("ALL PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
