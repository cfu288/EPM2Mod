"""Seven film slots, second design (NOTES §35): effect filters are not converted in place. Their MENU ENTRIES are
sent to filter numbers that every part of the firmware already treats as colour-only, and those numbers get the
film tables. Soft Focus -> 102 (Pop Art II's number), Pin Hole -> 145 (Pale&Light II), Diorama -> 167 (Cross Process
II). Numbers 69, 73, 86 and their effect, live-view and movie handling stay stock.
  patches/remap7b-code.json (the working second version; the first, remap7-code, is in patches/history), patches/remap7-neutral.json     python3 -I build_remap7.py"""
import json, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_slots12 as b
B, b0, op, u32 = b.B, b.b0, b.op, b.u32
b.SLOTS = [("palelight1", (71, 80), 0x7E7696A4, (0x7E76949E, 0x7E7694AA), None), ("softfocus", (102, 103), 0x7E7696BC, (0x7E76952E, 0x7E76953A), 101),
           ("pinhole", (145, 146), 0x7E7696B8, (0x7E769516, 0x7E769522), 105), ("diorama", (167, 168), 0x7E7696EC, (0x7E769622, 0x7E76962E), 106)]
b.POOL = [b.RUN3, b.RUN3 + 512, 0x7E75E8F0, 0x7E75FAF0, 0x7E75F8F0, 0x7E7616F0] + b.FREED       # own look tables of the four numbers + tables Pro 400H gives up
_asm = b.asm
def asm():                                                          # two entry snippets for art_GetFilterType's jump table
    s = _asm()
    extra = ["        .global ft_soft, ft_dio, lva_soft, lva_dio, lvb_soft, lvb_dio", "ft_soft: mov 102,d2", "        jmp FT_END", "ft_dio: mov 167,d2", "        jmp FT_END",
             # the movie / live-view code has its own menu-entry -> number tables in two functions (NOTES 37); same form of stub, each function's own tail
             "lva_soft: mov 102,d2", "        jmp LVA_END", "lva_dio: mov 167,d2", "        jmp LVA_END", "lvb_soft: mov 102,d2", "        jmp LVB_END", "lvb_dio: mov 167,d2", "        jmp LVB_END"]
    return s.replace("        .balign 4, 0xff\nendc:", "\n".join(extra) + "\n        .balign 4, 0xff\nendc:", 1)
b.asm = asm
def main():
    import subprocess
    orig = subprocess.run
    def patched(args, **k):
        if args[0].endswith("ld") and "cave12.o" in args: args = list(args[:-3]) + ["--defsym=FT_END=0x7e71bea3", "--defsym=LVA_END=0x7e6cc14e", "--defsym=LVB_END=0x7e6dbbc4"] + list(args[-3:])
        return orig(args, **k)
    b.subprocess.run = patched
    c1, s1, c2, s2 = b.assemble(); b.subprocess.run = orig
    assert len(c2) <= b.CAVE2_LEN and s2["recs"] % 4 == 0
    ops = [op(b.CAVE1, c1), op(b.CAVE2, c2), op(0x7E56C6A5, b"\xdc" + struct.pack("<i", s2["matrix12"] - 0x7E56C6A5)), op(0x7E56B7A7, b"\x46")]     # gamma range check: >= 70 (as in the three-film build)
    T, ent, i70 = b.gamma_hash(s1, s2)
    for i, (k, h) in enumerate(ent):
        if k != u32(T + 8 * i): ops.append(op(T + 8 * i, struct.pack("<I", k)))
        if h != u32(T + 8 * i + 4) and i not in (2, 11): ops.append(op(T + 8 * i + 4, struct.pack("<I", h)))
    for n, codes, *_r in b.SLOTS:
        for c in codes:
            ops.append(op(0x7E78C8E4 + 4 * (c - 8), struct.pack("<I", b.LOOK_SHARED))); ops.append(op(0x7E78AEA4 + 4 * (c - 69), struct.pack("<I", b.CHROMA_LINEAR)))
    ops += [op(0x7E768DB8, struct.pack("<10H", *[256] * 10))]                                                      # all five WB multiplier pairs -> 1.0 (they are chosen by number AND by menu entry: Pin Hole's entry still got 506/424)
    # live view / movie-art: the "still" menu-entry -> number tables of 0x7E6CBFD3 (0x7E7FF05C) and 0x7E6DBA95 (0x7E807880); index = picture mode - 100.
    # Soft Focus -> 102, Diorama -> 167 (new stubs), Pin Hole -> 145 (the stock stub of entry 110). The movie tables (0x7E7FF008, 0x7E80782C) are left stock.
    for tab, soft, dio in ((0x7E7FF05C, s2["lva_soft"], s2["lva_dio"]), (0x7E807880, s2["lvb_soft"], s2["lvb_dio"])):
        ops += [op(tab + 4 * 1, struct.pack("<I", soft)), op(tab + 4 * 5, struct.pack("<I", u32(tab + 4 * 10))), op(tab + 4 * 6, struct.pack("<I", dio))]
    # number 167 / 168 also has entries in one more per-number stage (hash 0x7E78C6E4, 64 entries, key = code - 8, worker 0x7E56E495): send them to its default path
    H2 = 0x7E78C6E4
    for i in range(64):
        k = u32(H2 + 8 * i)
        if k in (167 - 8, 168 - 8): ops.append(op(H2 + 8 * i + 4, struct.pack("<I", 0x7E56E5DC)))
    FT = 0x7E854A24                                                                                                 # art_GetFilterType jump table, index = picture mode - 100
    ops += [op(FT + 4 * 1, struct.pack("<I", s2["ft_soft"])), op(FT + 4 * 5, struct.pack("<I", 0x7E71BE19)), op(FT + 4 * 6, struct.pack("<I", s2["ft_dio"]))]
    KM = 0x7E8522AC                                                                                                 # record-side kind by picture mode -> 1 (colour-only) for the three entries
    ops += [op(KM + 4 * m, struct.pack("<I", 0x7E70DBF4)) for m in (1, 5, 6)]
    for r, tabs in zip(b.PRO_RECS, b.pro_tabs): ops.append(op(r, struct.pack("<8I", b.DEF[0], tabs[1], b.DEF[2], tabs[1], b.DEF[4], tabs[1], b.DEF[6], tabs[1])))
    ops = [o for o in ops if o["expect"] != o["new"]]
    base = dict(base="firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN", base_sha256="34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300", status="built, NOT camera-tested")
    json.dump(dict(name="remap7b-code", description="Seven film slots, remap design, second version (replaces remap7-code): as remap7-code, and the same menu-entry -> number change in the two "
                   "live-view / movie-art tables (0x7E7FF05C, 0x7E807880), all WB multiplier pairs 1.0, and numbers 167 / 168 on the default path of the hash 0x7E78C6E4. NOTES §37.", ops=ops, **base),
              open(os.path.join(b.ROOT, "patches/remap7b-code.json"), "w"), indent=1)
    dflt = b0[0x7E74E9BC - B:0x7E74E9BC - B + 512]; nops = []; lay = {}
    for i, (n, codes, sat, six, mode) in enumerate(b.SLOTS):
        tabs = b.POOL[3 * i:3 * i + 3]; lay[n] = dict(codes=codes, tabs=[hex(t) for t in tabs], sat=hex(sat), six=[hex(x) for x in six], matrix=hex(s2[f"t_{n}"]))
        for t in tabs: nops.append({"type": "bytes", "block": 0, "offset": hex(t - B), "expect": b0[t - B:t - B + 512].hex(), "new": dflt.hex()})
        nops += [op(sat, struct.pack("<2H", 282, 282)), op(six[0], struct.pack("<6h", *[0] * 6)), op(six[1], struct.pack("<6h", *[0] * 6))]
    json.dump(dict(name="remap7-neutral", description="Stock Natural settings in the four new slots of remap7-code (test content). NOTES §35.", ops=[o for o in nops if o["expect"] != o["new"]], **base),
              open(os.path.join(b.ROOT, "patches/remap7-neutral.json"), "w"), indent=1)
    json.dump(dict(slots=lay, s2={k: hex(v) for k, v in s2.items()}), open(os.path.join(b.HERE, "remap7_layout.json"), "w"), indent=1)
    print("code area 2:", len(c2), "B; ops:", len(ops), "; snippets", hex(s2["ft_soft"]), hex(s2["ft_dio"]), "; code 70 at hash entry", i70)
if __name__ == "__main__":
    main()
