"""Emulator check of step A (emulator driver, single function).

Runs the stock sub-item list builder (E-PM2 0x7EDE2192, E-PL6 0x7EDE2F8F; a0 = panel object with the
panel number at +3296, a1 = output list) for a few panels on several block-0 images and prints the list
the menu would show: title text, row count and, per row, the text id and the setting read for it.
The visibility test 0x7EDE29B3 runs natively. The other callees are stubs (getSetting returns 0).
Then it reads panel records with the stock lookup (record walk in Python, same bytes) for the child list.

Usage: emu_step_a.py NAME=BLOCK0 [NAME=BLOCK0 ...]   (a name that starts with "pl6" uses the E-PL6 addresses)
"""
import os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, "emulator"))
from omemu import Emu  # noqa: E402

BASE = 0x7E421020
ADDR = {  # role: (E-PM2, E-PL6); pairs from the normalised comparison (all strict-identical)
    "build": (0x7EDE2192, 0x7EDE2F8F), "get": (0x7EE01D38, 0x7EE02BCC), "init": (0x7EDCDAAB, 0x7EDCE8A8),
    "state": (0x7EDE2AAB, 0x7EDE38A8), "fmt": (0x7EDE2776, 0x7EDE3573), "pm": (0x7EDE2838, 0x7EDE3635),
    "flag": (0x7EDCD32C, 0x7EDCE129), "flag2": (0x7EDCD335, 0x7EDCE132), "fin": (0x7EDE2FE6, 0x7EDE3DE3),
    "x": (0x7EDE2E3D, 0x7EDE3C3A),
}
THIS, OUT = 0x7D200000, 0x7D220000
PANELS = (191, 192, 193, 594)


def run(emu, body, panel):
    A = {k: v[body] for k, v in ADDR.items()}
    emu.write(THIS, b"\0" * 3400)
    emu.write(OUT, b"\0" * 4096)
    emu.write(THIS + 3296, struct.pack("<H", panel))
    ids = []

    def get(e, r):
        ids.append(r["d0"] & 0xFFFF)
        e.write(r["a0"], struct.pack("<I", 0))
        return {"d0": 0}
    zero = lambda e, r: {"d0": 0}
    stubs = {A["get"]: get}
    for k in ("init", "state", "fmt", "pm", "flag", "flag2", "fin", "x"):
        stubs[A[k]] = zero
    r = emu.call(A["build"], {"a0": THIS, "a1": OUT}, stubs=stubs)
    o = emu.read(OUT, 82 + 38 * 12)
    n = struct.unpack_from("<H", o, 78)[0]
    title = struct.unpack_from("<H", o, 0)[0]
    rows = [struct.unpack_from("<H", o, 82 + 38 * i + 4)[0] for i in range(n)]
    return title, n, rows, ids


def kids(img, panel):
    for o in range(0, len(img) - 80, 4):
        if struct.unpack_from("<5I", img, o) == (1, 0xFFFFFFF1, 0, 1, 2):
            break
    while struct.unpack_from("<I", img, o)[0] not in (0, panel):
        o += 40
    p = struct.unpack_from("<I", img, o + 20)[0]
    out = []
    while p and struct.unpack_from("<I", img, p - BASE)[0]:
        out.append(struct.unpack_from("<2I", img, p - BASE))
        p += 8
    return out


res = {}
for arg in sys.argv[1:]:
    name, path = arg.split("=", 1)
    body = 1 if name.startswith("pl6") else 0
    img = open(path, "rb").read()
    with Emu() as emu:
        emu.load(path)
        for p in PANELS:
            res[(name, p)] = run(emu, body, p) + (kids(img, p),)
for p in PANELS:
    print("panel %d" % p)
    for arg in sys.argv[1:]:
        name = arg.split("=", 1)[0]
        t, n, rows, ids, k = res[(name, p)]
        print("  %-14s title %4d rows %d texts %s settings read %s children %s" % (name, t, n, rows, ids, k))
names = [a.split("=", 1)[0] for a in sys.argv[1:]]
pl6 = [n for n in names if n.startswith("pl6")]
if pl6:
    for n in names:
        same = [p for p in (192,) if res[(n, p)] == res[(pl6[0], p)]]
        print("%-14s panel 192 equals %s: %s" % (n, pl6[0], bool(same)))
