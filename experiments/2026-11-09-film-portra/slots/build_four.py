"""Four film slots (NOTES §36): the three films + Pale&Light I converted in place. Nothing about Soft Focus, Pin Hole,
Diorama or any other effect filter is touched (three attempts to convert those froze live view).
  patches/four-code.json, patches/four-neutral.json      python3 -I build_four.py"""
import json, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_slots12 as b
B, b0, op, u32 = b.B, b.b0, b.op, b.u32
b.SLOTS = [("palelight1", (71, 80), 0x7E7696A4, (0x7E76949E, 0x7E7694AA), None)]
b.POOL = [b.RUN3, b.RUN3 + 512, 0x7E75E8F0]                    # two tables in the third free run + Pale&Light I's own look table
def gamma_hash(s1, s2):                                         # stock table + the three-film entries + Pale&Light I
    T = 0x7E78C154; D = 0x7E56B861; ent = [list(struct.unpack_from("<II", b0, T - B + 8 * i)) for i in range(32)]
    for e in ent:
        if e[1] == 0x7E56B822: e[1] = D                          # Pop Art II (its record is Pro 400H's blue channel): default
        if e[0] in (77, 80) and e[1] == 0x7E56B7F0: e[1] = D     # codes 147, 150
        if e[0] in (2, 11): e[1] = 0x7E56B82A                    # Light Tone -> Cross Process II's handler (the Ektachrome patch owns these two fields)
        if e[0] in (1, 10): e[1] = s2["g_palelight1"]            # Pale&Light I 71 / 80
    ent[8][1] = s1["gamma3"]; ent[9] = [9, s1["gamma3"]]         # Pop Art I: key 0 matches entry 8; movie code 79
    return T, ent
def main():
    c1, s1, c2, s2 = b.assemble()
    ops = [op(b.CAVE1, c1), op(b.CAVE2, c2), op(0x7E56C6A5, b"\xdc" + struct.pack("<i", s2["matrix12"] - 0x7E56C6A5)), op(0x7E56B7A7, b"\x46")]
    T, ent = gamma_hash(s1, s2)
    for i, (k, h) in enumerate(ent):
        if k != u32(T + 8 * i): ops.append(op(T + 8 * i, struct.pack("<I", k)))
        if h != u32(T + 8 * i + 4) and i not in (2, 11): ops.append(op(T + 8 * i + 4, struct.pack("<I", h)))
    for c in (71, 80):
        ops.append(op(0x7E78C8E4 + 4 * (c - 8), struct.pack("<I", b.LOOK_SHARED))); ops.append(op(0x7E78AEA4 + 4 * (c - 69), struct.pack("<I", b.CHROMA_LINEAR)))
    ops.append(op(0x7E768DB8, struct.pack("<2H", 256, 256)))                                   # Pale&Light I's WB multipliers -> 1.0
    ops = [o for o in ops if o["expect"] != o["new"]]
    base = dict(base="firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN", base_sha256="34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300", status="built, NOT camera-tested")
    json.dump(dict(name="four-code", description="Four film slots (replaces slot3-code): the three-film structure plus Pale&Light I (codes 71 / 80) as a generic slot: gamma stub, matrix, "
                   "shared look, linear chroma, WB multipliers 1.0. No effect filter is touched. NOTES §36.", ops=ops, **base), open(os.path.join(b.ROOT, "patches/four-code.json"), "w"), indent=1)
    dflt = b0[0x7E74E9BC - B:0x7E74E9BC - B + 512]
    nops = [{"type": "bytes", "block": 0, "offset": hex(t - B), "expect": b0[t - B:t - B + 512].hex(), "new": dflt.hex()} for t in b.POOL]
    nops += [op(0x7E7696A4, struct.pack("<2H", 282, 282)), op(0x7E76949E, struct.pack("<6h", *[0] * 6)), op(0x7E7694AA, struct.pack("<6h", *[0] * 6))]
    json.dump(dict(name="four-neutral", description="Stock Natural settings in the Pale&Light I slot of four-code (test content). NOTES §36.", ops=[o for o in nops if o["expect"] != o["new"]], **base),
              open(os.path.join(b.ROOT, "patches/four-neutral.json"), "w"), indent=1)
    json.dump(dict(tabs=[hex(t) for t in b.POOL], matrix=hex(s2["t_palelight1"]), stub=hex(s2["g_palelight1"])), open(os.path.join(b.HERE, "four_layout.json"), "w"), indent=1)
    print("code area 2:", len(c2), "B; ops:", len(ops))
if __name__ == "__main__":
    main()
