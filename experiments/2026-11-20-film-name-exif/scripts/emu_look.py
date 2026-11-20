"""The look stage selector curve_select (0x7E56E837) for the 12 film codes, after a Load of all 12 entries (the
layout's film words written into block 0, as the loader writes them). Research code; from the tone-fault check of
2026-11-20 (the coordinator's scratch emu_look.py), with the images as arguments.

    uv run python experiments/2026-11-20-film-name-exif/scripts/emu_look.py TAG BLOCK0.bin LAYOUT.json [TAG ...]

Each row: the table the stage selects. IDENT = the stock identity table 0x7E75B8F0, XP-I = Cross Process I's own
look table 0x7E75F2F0 (the fault)."""
import hashlib
import json
import sys

sys.path.insert(0, "emulator")
import emurun  # noqa: E402
from cases import CASES  # noqa: E402

B = 0x7E421020
CODES = [79, 75, 71, 72, 94, 92, 125, 85, 98, 144, 156, 159]
case = CASES["curve_select"]
case = case() if isinstance(case, type) else case
case.ranges = case.ranges + [(0x7ECB0888, 0x7ECB0BA0)]
case.rows = lambda: [dict(art=c, grad=0, mode=1, contrast=0, flag=0, d1=d1) for c in CODES for d1 in (0, 1)]
st = open("build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin", "rb").read()
names = {hashlib.sha256(st[a - B:a - B + 512]).hexdigest()[:16]: n
         for a, n in ((0x7E75B8F0, "IDENT"), (0x7E75F2F0, "XP-I"), (0x7E75B6F0, "0x7E75B6F0"))}
args = sys.argv[1:]
bad = 0
for k in range(0, len(args), 3):
    tag, img, lay = args[k:k + 3]
    data = bytearray(open(img, "rb").read())
    for e in json.load(open(lay))["entries"]:
        for w in e["switch"]:
            a = w["address"] - B
            if 0 <= a < len(data):
                f = bytes.fromhex(w["film"])
                data[a:a + len(f)] = f
    out_path = img + ".loaded"
    open(out_path, "wb").write(data)
    for row, out, _, errs in emurun.run_image(case, out_path):
        n = names.get(out.get("sha"), out.get("first8"))
        bad += n != "IDENT"
        print(tag, "code %3d d1=%d" % (row["art"], row["d1"]), out.get("table"), n, errs or "")
print("bad rows:", bad)
