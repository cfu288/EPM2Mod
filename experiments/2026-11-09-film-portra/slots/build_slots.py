"""Seven film slots: assemble the code areas and write the patches (NOTES §32).
  patches/slots7-code.json     structure: both code areas, gamma hash, look / chroma / effect dispatch, WB pairs
  patches/slots7-neutral.json  a neutral look (= stock Natural settings) in the four new slots, to test them
Slots: Cross Process I, Light Tone, Pop Art I (as before) + Pale&Light I, Soft Focus, Pin Hole I, Diorama.
   python3 -I build_slots.py"""
import json, os, struct, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..", "..")
BIN = os.path.expanduser("~/opt/mn10300/bin/mn10300-elf-"); B = 0x7E421020
b0 = open(os.path.join(ROOT, "build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin"), "rb").read()
u32 = lambda a: struct.unpack_from("<I", b0, a - B)[0]
def op(addr, new): return {"type": "bytes", "block": 0, "offset": hex(addr - B), "expect": b0[addr - B:addr - B + len(new)].hex(), "new": bytes(new).hex()}
CAVE1, CAVE2, CAVE2_LEN, RUN3 = 0x7E880F5C, 0x7ECB0888, 1912, 0x7F033B7C
# gamma tables of the four new slots (R, G, B each): two in code area 2, two in the third free run, the rest are look
# tables no longer needed (the slots' own, and those of four hidden second types), all in loaded read-only data
NEW = {"palelight1": dict(codes=(71, 80), stub="g4", mat="t4", sat=0x7E7696A4, six=(0x7E76949E, 0x7E7694AA), tabs=["tabA", "tabB", RUN3]),
       "softfocus": dict(codes=(69, 78), stub="g5", mat="t5", sat=0x7E76969C, six=(0x7E76946E, 0x7E76947A), tabs=[RUN3 + 512, 0x7E75E4F0, 0x7E75E8F0]),
       "pinhole1": dict(codes=(73, 82), stub="g6", mat="t6", sat=0x7E7696AC, six=(0x7E7694CE, 0x7E7694DA), tabs=[0x7E75ECF0, 0x7E75F0F0, 0x7E75F8F0]),
       "diorama": dict(codes=(86, 88), stub="g7", mat="t7", sat=0x7E7696B0, six=(0x7E7694E6, 0x7E7694F2), tabs=[0x7E75FAF0, 0x7E7616F0, 0x7E75FCF0])}
LOOK_SHARED = 0x7E56E94A       # Cross Process I's look handler: loads 0x7E75F2F0, which the Portra patch fills with the stock "identity" table
CHROMA_LINEAR = 0x7E5664A0     # Cross Process I's chroma-curve handler (linear set)
HIDDEN_LOOKS = (102, 103, 145, 146, 167, 168, 106)        # second types whose look tables are reused as gamma tables
def assemble():
    run = lambda *a: subprocess.run(a, check=True, capture_output=True, text=True, cwd=HERE).stdout
    slot3 = os.path.join(HERE, "..", "slot3")
    run(BIN + "as", "-o", os.path.join(HERE, "cave1.o"), os.path.join(slot3, "cave.s"))
    ext1 = dict(PICK=0x7E56B732, GTAIL=0x7E56B852, M_T1=0x7E56C6B8, M_T2=0x7E56C6C3, M_APPLY=0x7E56C764, M_NONE=0x7E56C76B)
    run(BIN + "ld", "-Ttext=%#x" % CAVE1, "-e", "gamma3", *[f"--defsym={k}={v:#x}" for k, v in ext1.items()], "-o", "cave1.elf", "cave1.o")
    run(BIN + "objcopy", "-O", "binary", "-j", ".text", "cave1.elf", "cave1.bin")
    s1 = {l.split()[2]: int(l.split()[0], 16) for l in run(BIN + "nm", "cave1.elf").splitlines() if len(l.split()) == 3}
    tabsym = {}
    for nm, s in NEW.items():
        for ch, t in zip("RGB", s["tabs"]): tabsym[f"G{s['stub'][1]}{ch}"] = t
    ext2 = dict(PICK=0x7E56B732, GTAIL=0x7E56B852, M_APPLY=0x7E56C764, M_NONE=0x7E56C76B, T1=0x7E768F46, T2=0x7E768F58, T3=s1["t3"])
    run(BIN + "as", "-o", "cave2.o", "cave2.s")
    # two passes: table symbols that live inside the code area are known only after a first link
    args = lambda extra: [BIN + "ld", "-Ttext=%#x" % CAVE2, "-e", "g4", *[f"--defsym={k}={v:#x}" for k, v in {**ext2, **extra}.items()], "-o", "cave2.elf", "cave2.o"]
    run(*args({k: (0 if isinstance(v, str) else v) for k, v in tabsym.items()}))
    s2 = {l.split()[2]: int(l.split()[0], 16) for l in run(BIN + "nm", "cave2.elf").splitlines() if len(l.split()) == 3}
    tabsym = {k: (s2[v] if isinstance(v, str) else v) for k, v in tabsym.items()}
    run(*args(tabsym)); run(BIN + "objcopy", "-O", "binary", "-j", ".text", "cave2.elf", "cave2.bin")
    s2 = {l.split()[2]: int(l.split()[0], 16) for l in run(BIN + "nm", "cave2.elf").splitlines() if len(l.split()) == 3}
    return open(os.path.join(HERE, "cave1.bin"), "rb").read(), s1, open(os.path.join(HERE, "cave2.bin"), "rb").read(), s2, tabsym
def gamma_hash(s1, s2):
    """New contents of the 32-entry hash 0x7E78C154 (key = code - 70; key 0 = empty, and the first empty entry reached
    from index 0 is the one code 70 matches). Returns [(key, handler)]."""
    T = 0x7E78C154; DEF = 0x7E56B861; ent = [list(struct.unpack_from("<II", b0, T - B + 8 * i)) for i in range(32)]
    def put(code, h):
        k = (code - 70) & 0xFFFFFFFF
        for e in ent:
            if e[0] == k: e[1] = h; return
        i = k & 31
        while ent[i][0] != 0: i = (i + 1) % 32
        ent[i] = [k, h]
    for e in ent:                                                        # Pop Art II, extra Light Tone codes: default record
        if e[0] and e[1] in (0x7E56B822,): e[1] = DEF
        if e[0] in (77, 80) and e[1] == 0x7E56B7F0: e[1] = DEF
    put(72, 0x7E56B82A); put(81, 0x7E56B82A); put(79, s1["gamma3"])
    for s in NEW.values():
        for c in s["codes"]: put(c, s2[s["stub"]])
    i = 0
    while ent[i][0] != 0: i += 1                                          # where key 0 (code 70) lands
    for e in ent:
        if e[0] == 0: e[1] = DEF
    ent[i][1] = s1["gamma3"]
    return T, ent
def main():
    c1, s1, c2, s2, tabsym = assemble()
    assert len(c2) <= CAVE2_LEN and b0[CAVE2 - B:CAVE2 - B + CAVE2_LEN] == b"\xff" * CAVE2_LEN and all(s2[t] % 2 == 0 for t in ("t4", "t5", "t6", "t7")) and s2["recs"] % 4 == 0
    assert b0[0x7E56C6A5 - B:0x7E56C6B8 - B].hex() == "a046c811a04fc80da066c814a067c810ccb600" and b0[0x7E56B7A6 - B:0x7E56B7A8 - B] == b"\xaf\x47"
    ops = [op(CAVE1, c1), op(CAVE2, c2[:s2["tabA"] - CAVE2]),                                    # code, matrices, records (the two tables stay 0xFF here)
           op(0x7E56C6A5, b"\xdc" + struct.pack("<i", s2["matrix7"] - 0x7E56C6A5)),            # matrix compare chain -> matrix7
           op(0x7E56B7A7, b"\x45")]                                                              # gamma range check: code >= 69
    T, ent = gamma_hash(s1, s2)
    for i, (k, h) in enumerate(ent):                     # field by field; entries 2 and 11 (Light Tone -> 0x7E56B82A) belong to the Ektachrome patch
        if k != u32(T + 8 * i): ops.append(op(T + 8 * i, struct.pack("<I", k)))
        if h != u32(T + 8 * i + 4) and i not in (2, 11): ops.append(op(T + 8 * i + 4, struct.pack("<I", h)))
    for s in NEW.values():
        for c in s["codes"]:
            ops.append(op(0x7E78C8E4 + 4 * (c - 8), struct.pack("<I", LOOK_SHARED)))            # look curve: the shared identity table
            ops.append(op(0x7E78AEA4 + 4 * (c - 69), struct.pack("<I", CHROMA_LINEAR)))         # chroma curves: linear
    for c in HIDDEN_LOOKS: ops.append(op(0x7E78C8E4 + 4 * (c - 8), struct.pack("<I", LOOK_SHARED)))
    ops += [op(0x7E768DB8, struct.pack("<4H", 256, 256, 256, 256)),                              # WB multipliers of Pale&Light I and Pin Hole I -> 1.0
            op(0x7E85C45C + 8 * 1 + 4, struct.pack("<I", 0x7E72A665)),                           # Pin Hole I: no effect module
            op(0x7E85C45C + 8 * 14 + 4, struct.pack("<I", 0x7E72A665)),                          # Diorama: no effect module
            op(0x7E72A6F7, b"\xff"), op(0x7E72A739, b"\xff")]                                    # Soft Focus: the two compares that force the blur effect never match
    ops = [o for o in ops if o["expect"] != o["new"]]
    base = dict(base="firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN", base_sha256="34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300", status="built, NOT camera-tested")
    json.dump(dict(name="slots7-code", description="Seven film slots (replaces slot3-code): code areas 0x7E880F5C (120 B) and 0x7ECB0888, gamma hash, look / chroma / effect dispatch, WB pairs. "
                   "Use with the -s3 film patches, film-pro400h-pa*, slot3-chroma-linear and a look for each new slot. NOTES §32.", ops=ops, **base), open(os.path.join(ROOT, "patches/slots7-code.json"), "w"), indent=1)
    # neutral look for the four new slots: default gamma table, saturation gain 282, six-axis zero, identity matrix (already in the code area)
    dflt = b0[0x7E74E9BC - B:0x7E74E9BC - B + 512]; nops = []
    for s in NEW.values():
        for ch in "RGB":
            a = tabsym[f"G{s['stub'][1]}{ch}"]; exp = b0[a - B:a - B + 512]
            nops.append({"type": "bytes", "block": 0, "offset": hex(a - B), "expect": exp.hex(), "new": dflt.hex()})
        nops += [op(s["sat"], struct.pack("<2H", 282, 282)), op(s["six"][0], struct.pack("<6h", *[0] * 6)), op(s["six"][1], struct.pack("<6h", *[0] * 6))]
    json.dump(dict(name="slots7-neutral", description="Test content for the four new film slots: stock Natural settings (default gamma table per channel, saturation 282, six-axis zero). "
                   "With slots7-code each new slot should render like Natural. NOTES §32.", ops=[o for o in nops if o["expect"] != o["new"]], **base), open(os.path.join(ROOT, "patches/slots7-neutral.json"), "w"), indent=1)
    json.dump(dict(s1={k: hex(v) for k, v in s1.items()}, s2={k: hex(v) for k, v in s2.items()}, tables={k: hex(v) for k, v in tabsym.items()},
                   hash=[[hex(k), hex(h)] for k, h in ent]), open(os.path.join(HERE, "slots7_layout.json"), "w"), indent=1)
    print("code area 1:", len(c1), "B; code area 2:", len(c2), "of", CAVE2_LEN, "B (code", s2["endc"] - CAVE2, "B); structural ops:", len(ops))
    print("stubs", {k: hex(s2[k]) for k in ("g4", "g5", "g6", "g7", "gcommon", "matrix7")}, "matrices", {k: hex(s2[k]) for k in ("t4", "t5", "t6", "t7")})
    print("code 70 now matches hash entry", next(i for i, e in enumerate(ent) if e[0] == 0 and e[1] == s1["gamma3"]))
if __name__ == "__main__":
    main()
