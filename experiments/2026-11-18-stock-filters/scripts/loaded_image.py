"""Write a block 0 of data/builds/stock-films.json as the loader leaves it after a Load of the 12 default films: every
entry's switch words at their film bytes and every entry's RAM block filled (the model of emu_stock.py). For the
live-view rig (experiments/2026-11-16-films-max/scripts/scen_films.py), which runs on a block-0 image.

    uv run python experiments/2026-11-18-stock-filters/scripts/loaded_image.py BLOCK0_IN BLOCK0_OUT
"""
import json
import os
import struct
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from epm2mod.looks import lookfile, lookpack, slots  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

BASE = 0x7E421020


def main():
    src, dst = sys.argv[1:3]
    img = bytearray(open(src, "rb").read())
    layout = json.load(open(os.path.join(ROOT, "build", "stock-films", "layout.json")))
    off = layout["offsets"]
    defaults = [struct.unpack_from("<I", img, slots.DEFAULT_RECORD + 4 * i - BASE)[0] for i in range(8)]
    ops = [(20, 2, off["sat"], 0), (20, 2, off["sat"] + 2, 0), (22, 12, off["six_s"], 0), (34, 12, off["six_h"], 0),
           (46, 18, off["matrix"], 0), (64, 97, off["chroma"], 0)]
    for ch in range(3):
        ops += [(164 + ch * lookfile.CURVE_BYTES, 256, off["tone"] + 512 * (8 * ch + i), defaults[i]) for i in range(8)]
    paths = RepoPaths(Path(ROOT))
    for look in lookpack.load_list(paths, paths.card_looks):
        rec = lookfile.pack([look])[32:]
        base = layout["film_ram"] + layout["block"] * look.slot - BASE
        for o, n, a, d in ops:
            if not d:
                img[base + a: base + a + n] = rec[o:o + n]
                continue
            v, i, p, out = struct.unpack_from("<H", rec, o)[0], 0, o + 2, []
            for k in range(n):
                target = struct.unpack_from("<H", img, d - BASE + 2 * k)[0]
                while i < target:
                    v += (rec[p] >> 4) if i & 1 else (rec[p] & 15)
                    p += i & 1
                    i += 1
                out.append(min(v, 1023))
            img[base + a: base + a + 2 * n] = struct.pack("<%dH" % n, *out)
    for e in layout["entries"]:
        for w in e["switch"]:
            film = bytes.fromhex(w["film"])
            img[w["address"] - BASE: w["address"] - BASE + len(film)] = film
    open(dst, "wb").write(img)
    print("wrote", dst)


if __name__ == "__main__":
    main()
