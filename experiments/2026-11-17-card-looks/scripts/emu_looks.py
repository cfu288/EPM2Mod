"""The card-looks build in the emulator: five sessions that share the camera's flash.

    uv run python experiments/2026-11-17-card-looks/scripts/emu_looks.py [--v2]

--v2: builds/card-looks-2.json (twelve colour slots, the menu row Load Looks). TEST has C200 in all 12 slots, and a
load is MENU -> Custom Menu -> J -> Load Looks -> Load, then out of the menu. Its sessions start from the settings
state build/emu/state/card-looks-2-p.json (emulator/mkstate builds/card-looks-2.json ... p); screenshots go to
build/card-looks/emu/shots-2/.

Needs build/card-looks.BIN (uv run epm2mod make card-looks) and the files that mkspec_looks.py writes
into build/card-looks/ (syms.json, spans.json, films-12d.block0.bin). Each session boots the build, and each dump
compares the slot tables in RAM with what they must hold:

  1. card with TEST (C200 in the 11 colour slots, a changed black-and-white look): at start the flashed looks;
     after MENU the TEST looks, stored and saved to flash
  2. no look file, the RAM banks taken out of the state (only the flash brings the store back): TEST at start
  3. card with BAD (TEST with one byte changed): refused; TEST stays, nothing saved
  4. no card: TEST at start
  5. card with DEFAULT (the looks of looks/card-looks.json): after MENU the flashed looks again
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import mkspec_looks as mk  # noqa: E402
from epm2mod.looks import lookfile, lookpack  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

WORK = os.path.join(ROOT, "build", "card-looks")
EMU = os.path.join(WORK, "emu")
RTC = "2026-11-17T12:00:00"


V2 = "--v2" in sys.argv
SUF = "-2" if V2 else ""
BUILD = "builds/card-looks%s.json" % SUF
NAV = ("key:MENU key:RIGHT key:OK key:DOWN key:DOWN key:DOWN key:RIGHT " + "key:DOWN " * 9 + "key:RIGHT " +
       "key:DOWN " * 4).split()
LOAD = NAV + ["shot:row", "key:RIGHT", "key:DOWN", "key:OK", "shot:load", "key:MENU", "key:MENU", "w:2000"]


def files():
    """The three look files."""
    paths = RepoPaths(Path(ROOT))
    if V2:
        items = json.load(open(paths.card_looks))["looks"]
        default = lookpack.load_list(paths, paths.card_looks)
    else:           # films-12d's looks: Double-X in its black-and-white slot
        lst = os.path.join(WORK, "list-card-looks.json")
        default = lookpack.load_list(paths, Path(lst))
    fit = lookpack.load_fit(paths.resolve("looks/fits/c200.npz"))
    test = [lookpack.look_of_fit(fit, e, "C200", "c200") for e in lookfile.MENU_ENTRIES if V2 or e != "Grainy Film"]
    if not V2:
        mono = default[4]
        test.append(lookfile.MonoLook(4, "Mono+40", mono.matrix, tuple(min(v + 40, 1023) for v in mono.grain),
                                      mono.live))
    t = lookfile.pack(test)
    bad = bytearray(t)
    bad[5000] ^= 0x01
    return {"TEST": t, "BAD": bytes(bad), "DEFAULT": lookfile.pack(default)}


def expected(b, data, table, spans):
    """The slot tables after a look file is applied to films-12d, as one hex string."""
    img = bytearray(b)
    if data is not None:
        mk.model_apply(img, data, table)
    return "".join(bytes(img[a - mk.BASE: a - mk.BASE + n]).hex() for a, n in spans)


def session(n, card, state, steps, drop_ram=False):
    """Run one session; return its dump lines by name."""
    env = dict(os.environ, E101_STATE=state, E101_RTC=RTC, SPANS=os.path.join(WORK, "spans%s.json" % SUF),
               SYMS=os.path.join(WORK, "syms%s.json" % SUF), SHOTS=os.path.join(EMU, "shots%s" % SUF, "s%d" % n))
    if drop_ram and os.path.exists(state):
        doc = json.load(open(state))
        doc.pop("ram", None)
        json.dump(doc, open(state, "w"))
    if card is not None:
        folder = os.path.join(EMU, "card%d" % n)
        shutil.rmtree(folder, ignore_errors=True)
        os.makedirs(folder)
        for name, data in card.items():
            open(os.path.join(folder, name), "wb").write(data)
        env["E101_CARD"] = folder
    else:
        env.pop("E101_CARD", None)
    out = subprocess.run([os.path.join(ROOT, "emulator/emu-run"), BUILD,
                          os.path.join(HERE, "emu_looks.mjs"), *steps], cwd=ROOT, env=env, capture_output=True,
                         text=True)
    lines = [json.loads(l) for l in out.stdout.splitlines() if l.startswith("{")]
    if out.returncode:
        print(out.stdout[-3000:], out.stderr[-3000:])
        raise SystemExit("session %d: exit %d" % (n, out.returncode))
    return {l["dump"]: l for l in lines if "dump" in l}, lines[-1]


def main():
    b = bytes(open(os.path.join(WORK, "base-2.block0.bin" if V2 else "films-12d.block0.bin"), "rb").read())
    blk = bytearray(b)
    table = mk.slot_ops(blk, V2)
    spans = json.load(open(os.path.join(WORK, "spans%s.json" % SUF)))
    f = files()
    want = {"flashed": expected(b, None, table, spans), "TEST": expected(b, f["TEST"], table, spans)}
    assert want["flashed"] == expected(b, f["DEFAULT"], table, spans)
    os.makedirs(EMU, exist_ok=True)
    state = os.path.join(EMU, "state%s.json" % SUF)
    if os.path.exists(state):
        os.remove(state)
    if V2:
        shutil.copy(os.path.join(ROOT, "build/emu/state/card-looks-2-p.json"), state)
    plan = [
        (1, {"EPM2LOOK.BIN": f["TEST"]}, False, ["dump:start", "key:MENU", "w:2000", "dump:menu", "key:MENU", "w:500"],
         {"start": "flashed", "menu": "TEST"}),
        (2, {}, True, ["dump:start", "key:MENU", "w:1500", "dump:menu"], {"start": "TEST", "menu": "TEST"}),
        (3, {"EPM2LOOK.BIN": f["BAD"]}, True, ["dump:start", "key:MENU", "w:2000", "dump:menu"],
         {"start": "TEST", "menu": "TEST"}),
        (4, None, True, ["dump:start", "key:MENU", "w:1500", "dump:menu"], {"start": "TEST", "menu": "TEST"}),
        (5, {"EPM2LOOK.BIN": f["DEFAULT"]}, True, ["dump:start", "key:MENU", "w:2000", "dump:menu"],
         {"start": "TEST", "menu": "flashed"}),
    ]
    if V2:
        plan = [
            (1, {"EPM2LOOK.BIN": f["TEST"]}, False,
             ["dump:start", "key:MENU", "key:RIGHT", "key:OK", "key:MENU", "w:1500", "dump:menu"] + LOAD + ["dump:load"],
             {"start": "flashed", "menu": "flashed", "load": "TEST"}),
            (2, {}, True, ["dump:start"] + NAV + ["shot:row-off"], {"start": "TEST"}),
            (3, {"EPM2LOOK.BIN": f["BAD"]}, True, ["dump:start"] + LOAD + ["dump:load"], {"start": "TEST", "load": "TEST"}),
            (4, None, True, ["dump:start"] + LOAD + ["dump:load"], {"start": "TEST", "load": "TEST"}),
            (5, {"EPM2LOOK.BIN": f["DEFAULT"]}, True, ["dump:start"] + LOAD + ["dump:load"],
             {"start": "TEST", "load": "flashed"}),
        ]
    ok = True
    for n, card, drop, steps, checks in plan:
        dumps, last = session(n, card, state, steps, drop)
        for name, what in checks.items():
            d = dumps[name]
            good = d["tables"] == want[what]
            ok &= good
            ev = " ".join("%s@%s%s" % (e[1], e[0], "(mode %d)" % e[2] if len(e) > 2 else "") for e in d["events"])
            print("session %d %-5s %-7s tables %s | store %s | flash ops %d | errors %d | %s" % (
                n, name, what, "OK" if good else "DIFFER", d["store"][:16], d["flash"], d["errors"], ev))
        print("session %d end: lab ms %s, problems %s, firmware errors %d" % (
            n, last.get("done"), last.get("problems"), len(last.get("errors", []))))
    print("ALL PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
