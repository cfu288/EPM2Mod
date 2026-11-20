"""rec_art_set_exif_data (0x7E70DC24) as an emulator piece on a fake shot struct, for stored Picture Mode 100..120.
Research code.

    uv run python experiments/2026-11-20-film-name-exif/scripts/exif_case.py TAG BLOCK0.bin [LAYOUT.json] [TAG ...]

With LAYOUT, the layout's film words are written into the image first (= after a Load of all 12 entries). Per value:
the ArtFilter field (struct+3470, 4 x u16), the first word of ArtFilterEffect (struct+3616), the EXIF Contrast,
Saturation and Sharpness fields (struct+2438 / 2440 / 2442; 0xAAAA = not written, the value the earlier writers left)
and the return value (1 = art case, 0 = default case). The trace call 0x7E710C83 and the memset 0x7E500D73 are stubs.
"""
import json
import struct
import sys

sys.path.insert(0, "emulator")
import omemu  # noqa: E402

B = 0x7E421020
CTX = omemu.DATA
FIELDS = {"art": (3470, 8), "effect0": (3616, 4), "custom": (2416, 2), "contrast": (2438, 2), "saturation": (2440, 2),
          "sharpness": (2442, 2)}
RANGES = [(0x7E70DB00, 0x7E70E500)]


def memset(emu, r):
    emu.write(r["a0"], bytes([r["d0"] & 0xFF]) * r["d1"])
    return {}


def run(tag, img):
    with omemu.Emu() as emu:
        emu.load(img)
        for v in range(100, 121):
            emu.write(CTX, b"\xaa" * 0x4400)                # sentinel: fields keep 0xAA.. unless written
            emu.write(CTX + 0x405F, bytes([v]))
            emu.write(CTX + 16460, struct.pack("<H", 0))   # art code: outside 69..183, so 0x7E70E298 gives 0
            emu.write(CTX + 17139, bytes(8))               # no Add Effects
            r = emu.call(0x7E70DC24, {"a0": CTX}, stubs={0x7E710C83: lambda e, r: {}, 0x7E500D73: memset})
            stray = sorted(p for p in r["pcs"] if not any(lo <= p < hi for lo, hi in RANGES)
                           and not omemu.TRAMP <= p < omemu.PADS + 0x100)
            out = {k: emu.read(CTX + o, n).hex() for k, (o, n) in FIELDS.items()}
            art = struct.unpack("<4H", bytes.fromhex(out["art"]))
            print(tag, v, "ArtFilter", art, "effect0", out["effect0"], "custom", out["custom"], "contrast",
                  out["contrast"], "saturation", out["saturation"], "sharpness", out["sharpness"],
                  "ret", r["regs"]["d0"] & 0xFF, "stray %s" % [hex(p) for p in stray[:4]] if stray else "")


def main():
    a = sys.argv[1:]
    k = 0
    while k < len(a):
        tag, img = a[k], a[k + 1]
        k += 2
        if k < len(a) and a[k].endswith(".json"):
            data = bytearray(open(img, "rb").read())
            for e in json.load(open(a[k]))["entries"]:
                for w in e["switch"]:
                    f = bytes.fromhex(w["film"])
                    data[w["address"] - B:w["address"] - B + len(f)] = f
            img = img + ".loaded"
            open(img, "wb").write(data)
            k += 1
        run(tag, img)


if __name__ == "__main__":
    main()
