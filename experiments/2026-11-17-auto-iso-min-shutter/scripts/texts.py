#!/usr/bin/env python3
"""Texts for the menu plan: the items of the stock Slow Limit list, and English strings that match a pattern.

    python3 experiments/2026-11-17-auto-iso-min-shutter/scripts/texts.py [REGEX]

It reads the stock firmware. The text-table reader is the class Blob of
experiments/2026-11-14-emulator-audit/scripts/film_names_spec.py.
"""
import importlib.util, os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import oetool  # noqa: E402

spec = importlib.util.spec_from_file_location("fns", os.path.join(ROOT, "experiments/2026-11-14-emulator-audit/scripts/film_names_spec.py"))
fns = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fns)
BASE = 0x7E421020


def main():
    raw = open(os.path.join(ROOT, "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"), "rb").read()
    blocks, _ = oetool.parse(raw)
    b0, b1 = blocks[0]["payload"], blocks[1]["payload"]
    eng = next(b for b in (fns.Blob(b1, e) for e in range(1, 35)) if b.code.upper().startswith("EN"))
    print("English blob: directory entry", eng.entry, eng.code)
    for name, desc in (("X-Sync (114)", 0x7F00BF5C), ("Slow Limit (174)", 0x7F00BF6C), ("panel 608 (447)", 0x7F00BFCC)):
        setting, count, _, _, items = struct.unpack_from("<HHIII", b0, desc - BASE)
        out = []
        for i in range(count):
            f = struct.unpack_from("<BBHIIIiII", b0, items - BASE + 28 * i)
            out.append(f"{eng.text(f[2])!r}(text {f[2]}, value {f[6]:#x})")
        print(f"{name}: setting {setting}, {count} items at {items:#x}:", ", ".join(out))
    if len(sys.argv) > 1:
        rx = re.compile(sys.argv[1])
        for i in range(fns.N_IDS):
            try:
                t = eng.text(i)
            except Exception:
                continue
            if rx.search(t):
                print(i, repr(t))


if __name__ == "__main__":
    main()
