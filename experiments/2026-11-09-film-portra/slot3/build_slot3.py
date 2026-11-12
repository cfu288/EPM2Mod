"""Assemble slot3/cave.s and write the patches for a three-film build (NOTES §30).
  patches/slot3-code.json   the new routines, the jump to matrix3, the gamma range check, hash entries
  patches/<film>-s3.json     copies of the two installed film patches without their matrix-compare
                             immediates (matrix3 replaces the whole compare chain)
   python3 -I build_slot3.py film-portra-xp10 film-ektachrome-lt3"""
import json, os, struct, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..", "..")
BIN = os.path.expanduser("~/opt/mn10300/bin/mn10300-elf-"); B = 0x7E421020; CAVE = 0x7E880F5C; CAVE_LEN = 164
EXT = dict(PICK=0x7E56B732, GTAIL=0x7E56B852, M_T1=0x7E56C6B8, M_T2=0x7E56C6C3, M_APPLY=0x7E56C764, M_NONE=0x7E56C76B)
b0 = open(os.path.join(ROOT, "build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin"), "rb").read()
def op(addr, new):
    return {"type": "bytes", "block": 0, "offset": hex(addr - B), "expect": b0[addr - B:addr - B + len(new)].hex(), "new": bytes(new).hex()}
def assemble():
    run = lambda *a: subprocess.run(a, check=True, capture_output=True, text=True, cwd=HERE).stdout
    run(BIN + "as", "-o", "cave.o", "cave.s")
    run(BIN + "ld", "-Ttext=%#x" % CAVE, "-e", "gamma3", *[f"--defsym={k}={v:#x}" for k, v in EXT.items()], "-o", "cave.elf", "cave.o")
    run(BIN + "objcopy", "-O", "binary", "-j", ".text", "cave.elf", "cave.bin")
    sym = {l.split()[2]: int(l.split()[0], 16) for l in run(BIN + "nm", "cave.elf").splitlines() if len(l.split()) == 3}
    return open(os.path.join(HERE, "cave.bin"), "rb").read(), sym
def main():
    code, sym = assemble()
    assert len(code) <= CAVE_LEN and b0[CAVE - B:CAVE - B + CAVE_LEN] == b"\xff" * CAVE_LEN and sym["t3"] % 2 == 0
    assert b0[0x7E56C6A5 - B:0x7E56C6B8 - B].hex() == "a046c811a04fc80da066c814a067c810ccb600" and b0[0x7E56B7A6 - B:0x7E56B7A8 - B] == b"\xaf\x47"
    jmp = b"\xdc" + struct.pack("<i", sym["matrix3"] - 0x7E56C6A5)            # jmp (d32,pc): displacement from the instruction's own address
    H = 0x7E78C154; DEF = 0x7E56B861; ptr = lambda a: struct.pack("<I", a)
    ops = [op(CAVE, code), op(0x7E56C6A5, jmp), op(0x7E56B7A7, b"\x46"),
           op(H + 8 * 8 + 4, ptr(sym["gamma3"])),                                # entry 8 (key 0 = code 70): handler field
           op(H + 9 * 8, struct.pack("<II", 9, sym["gamma3"])),                  # entry 9: key 9 = code 79
           # codes whose own record now belongs to film 3: back to the default record
           op(H + 1 * 8 + 4, ptr(DEF)), op(H + 10 * 8 + 4, ptr(DEF)),            # Pale&Light I 71 / 80
           op(H + 0 * 8 + 4, ptr(DEF)), op(H + 3 * 8 + 4, ptr(DEF))]             # Pop Art II 102 / 103
    for i in range(32):                                                          # remaining users of the Light Tone handler 0x7E56B7F0 (keys 77, 80 = codes 147, 150)
        key, h = struct.unpack("<II", b0[H - B + 8 * i:H - B + 8 * i + 8])
        if h == 0x7E56B7F0 and key not in (2, 11): ops.append(op(H + 8 * i + 4, ptr(DEF)))
    base = dict(base="firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN", base_sha256="34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300", status="built, NOT camera-tested")
    json.dump(dict(name="slot3-code", description="Third film slot in the top-level Pop Art entry (codes 70 / 79): 119 bytes of new code at 0x7E880F5C (slot3/cave.s), "
                   "a jump from the matrix compare chain, the gamma range check 71 -> 70 and hash entries. First patch with NEW CODE. NOTES §29-30.", ops=ops, **base),
              open(os.path.join(ROOT, "patches/slot3-code.json"), "w"), indent=1)
    CMP = {hex(a - B) for a in (0x7E56C6A6, 0x7E56C6AA, 0x7E56C6AE, 0x7E56C6B2)}
    for name in sys.argv[1:]:
        s = json.load(open(os.path.join(ROOT, f"patches/{name}.json"))); n0 = len(s["ops"]); s["ops"] = [o for o in s["ops"] if o.get("offset") not in CMP]
        assert n0 - len(s["ops"]) == 2, name
        s["name"] = name + "-s3"; s["description"] += " Without the two matrix-compare immediates: for builds with slot3-code."
        json.dump(s, open(os.path.join(ROOT, f"patches/{name}-s3.json"), "w"), indent=1)
    print("cave", len(code), "bytes;", {k: hex(v) for k, v in sym.items() if k in ("gamma3", "matrix3", "t3")}, "; jump bytes", jmp.hex(), "; ops", len(ops))
if __name__ == "__main__":
    main()
