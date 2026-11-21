"""Write data/specs/twelve-region-probe.json and data/builds/twelve-region-probe.json. Research code.

    uv run python experiments/2026-11-20-twelve-region/scripts/mkspec.py

Data edits only, no new code (NOTES.md section 3):
  * hash 0x7E78C6E4 (12-region table by art code, key = code - 8, 8-byte entries {key, case}, linear probing,
    key 0 = empty): one entry per film code of the probe, written into empty slots only, so every stock key is
    found as before. Each points at an existing case of the worker 0x7E56E495;
  * each case returns a fixed descriptor {table, 12 ISO-weight pointers} (sRGB; the pair cases a second one when
    P+82 != 0, table B). The probe writes its tables over the tables of those descriptors. Those tables are byte
    copies of table A / B (pair cases) or the stock Key Line table (stills only; peaking uses codes 163 / 164): in this build scene modes
    and those stock filters use the probe tables;
  * the look entry of code 159 (Watercolor's film code): Cross Process I's look handler (0x7E56E94A) in place of
    LKID, so ART 12 has a strong look curve.
"""
import hashlib, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "emulator"))
import tables as T  # noqa: E402
import patchblock  # noqa: E402

BASE = 0x7E421020
HASH, HASH_N = 0x7E78C6E4, 64
LOOK_JUMP, XP1_LOOK, LKID = 0x7E78C8E4, 0x7E56E94A, 0x7ECB0B6D
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
BASE_BUILD = "data/builds/films-look-exif-artbkt.json"
SPEC = "data/specs/twelve-region-probe.json"
BUILD = "data/builds/twelve-region-probe.json"

# case of the worker -> (sRGB descriptor, Adobe descriptor) (V: disassembly 0x7E56E4E6-0x7E56E5D9)
CASES = {"CTRL": (0x7E56E4E6, 0x7E78BA8C, 0x7E78BAC0), "HUEMAP": (0x7E56E4FD, 0x7E78BAF4, 0x7E78BB28),
         "MAGL": (0x7E56E514, 0x7E78BB5C, 0x7E78BB90), "MAGS": (0x7E56E52B, 0x7E78BBC4, 0x7E78BBF8),
         "MAGH": (0x7E56E542, 0x7E78BC2C, 0x7E78BC60), "CURVES": (0x7E56E559, 0x7E78BC94, 0x7E78BCC8),
         "OVERLAP": (0x7E56E570, 0x7E78BCFC, 0x7E78BD30), "WINDOW": (0x7E56E598, 0x7E78BD64, 0x7E78BD98),
         "BOX": (0x7E56E5B8, 0x7E78BE34, None)}
ADOBE = {"HUEMAP": "MARKER"}           # table B of an entry, when not its own table


def u32(b, a):
    return struct.unpack_from("<I", b, a - BASE)[0]


def case_descs(blk, case):
    """The descriptors a case loads: `mov A,a0; extbu d1; cmp 0,d1; beq +5; retf; mov S,a0; retf` (pair: A when
    d1 != 0, S when d1 == 0) or `mov X,a0; retf`."""
    o = case - BASE
    assert blk[o:o + 2] == b"\xfc\xdc", hex(case)
    first = u32(blk, case + 2)
    if blk[o + 6:o + 11] == bytes.fromhex("15a500c805"):
        assert blk[o + 11:o + 16] == bytes.fromhex("def014fcdc") and blk[o + 20:o + 23] == bytes.fromhex("def014")
        return [first, u32(blk, case + 16)]
    assert blk[o + 6:o + 9] == bytes.fromhex("def014"), hex(case)
    return [first]


def make(entries, tables, look_xp1, spec_path, build_path, name, description, what, adobe_names=ADOBE):
    """entries: (art n, entry name, film code, case name or None = no hash entry); tables: case name -> (sRGB table,
    Adobe table[, label]), only the cases used; look_xp1: ART 12's film code takes Cross Process I's look. Writes the spec and
    the build description (base: films-look-exif-artbkt)."""
    os.chdir(ROOT)
    build = json.load(open(BASE_BUILD))
    _, blk, _ = patchblock.patched_block0(build["specs"])        # the base build's block 0
    stock = open("build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin", "rb").read()
    ops, checks = [], []

    def op(addr, new, note):
        old = blk[addr - BASE:addr - BASE + len(new)]
        ops.append({"type": "bytes", "block": 0, "offset": "%#x" % (addr - BASE), "expect": old.hex(), "new": new.hex(),
                    "_addr": "%#010x" % addr, "_note": note})

    # --- tables over the case descriptors' tables
    iso_flat = struct.pack("<12H", *[256] * 12)
    for cname, (case, d_srgb, d_adobe) in CASES.items():
        if cname not in tables:
            continue
        got = case_descs(blk, case)
        want = [d for d in (d_adobe, d_srgb) if d]
        assert sorted(got) == sorted(want), (cname, [hex(x) for x in got])
        lab = tables[cname][2] if len(tables[cname]) > 2 else None             # what the table is, when not the case's name
        for d, tname, tbytes in ((d_srgb, lab or cname, tables[cname][0]), (d_adobe, lab or adobe_names.get(cname, cname), tables[cname][1])):
            if not d:
                continue
            tab = u32(blk, d)
            refs = [i for i in range(0, len(blk) - 3) if blk[i:i + 4] == struct.pack("<I", tab)]
            assert [BASE + i for i in refs] == [d], (cname, hex(tab), [hex(BASE + i) for i in refs])
            for k in range(12):                       # ISO weights flat: the record values reach the engine as written
                assert blk[u32(blk, d + 4 + 4 * k) - BASE:u32(blk, d + 4 + 4 * k) - BASE + 24] == iso_flat, (cname, k)
            assert blk[tab - BASE:tab - BASE + T.TABLE_BYTES] == stock[tab - BASE:tab - BASE + T.TABLE_BYTES]
            op(tab, tbytes, f"12-region table {tname} (descriptor {d:#x}, case {case:#x}; stock: "
               f"{'a copy of table A' if blk[tab - BASE:tab - BASE + T.TABLE_BYTES] == stock[0x7E76C3C8 - BASE:0x7E76C3C8 - BASE + T.TABLE_BYTES] else 'a copy of table B' if blk[tab - BASE:tab - BASE + T.TABLE_BYTES] == stock[0x7E76CF9C - BASE:0x7E76CF9C - BASE + T.TABLE_BYTES] else 'its own table'})")
            checks.append((d, tab, tname))

    # --- hash entries for the film codes
    slots = [(u32(blk, HASH + 8 * i), u32(blk, HASH + 8 * i + 4)) for i in range(HASH_N)]
    for n, entry, code, tname in entries:
        if tname is None:
            continue
        key = code - 8
        assert all(k != key for k, _ in slots), code
        p = key & 63
        while slots[p][0] != 0:
            p = (p + 1) % HASH_N
        slots[p] = (key, CASES[tname][0])
        op(HASH + 8 * p, struct.pack("<II", key, CASES[tname][0]),
           f"12-region hash slot {p}: code {code} (ART {n}, {entry}) -> case {CASES[tname][0]:#x}: table "
           f"{tables[tname][2] if len(tables[tname]) > 2 else tname}")
    assert sum(1 for k, _ in slots if k == 0) >= 8          # lookups of absent keys still end at an empty slot

    # --- ART 12: Cross Process I's look curve
    a = LOOK_JUMP + 4 * (159 - 8)
    assert u32(blk, a) == LKID
    if look_xp1:
        op(a, struct.pack("<I", XP1_LOOK), "look entry of code 159 (ART 12): Cross Process I's look handler (table "
           "0x7E75F2F0) in place of LKID (identity table)")

    spec = {"name": name, "description": description,
            "base": STOCK,
            "base_sha256": json.load(open("data/specs/build-label.json"))["base_sha256"],
            "ops": ops}
    with open(spec_path, "w") as f:
        json.dump(spec, f, indent=1)
        f.write("\n")
    b = {"what": what, "stock": build["stock"], "specs": build["specs"] + [spec_path], "first_code": True,
         "label": build["label"]}
    with open(build_path, "w") as f:
        json.dump(b, f, indent=1)
        f.write("\n")
    print(f"{spec_path}: {len(ops)} ops, {sum(len(o['new']) // 2 for o in ops)} bytes")
    for d, tab, tname in checks:
        print(f"  descriptor {d:#x} -> table {tab:#x}: {tname}")


def main():
    make([(n, entry, code, tname) for n, entry, code, tname, film, what in T.ENTRIES],
         {c: (T.table(c), T.table(ADOBE.get(c, c))) for c in CASES}, True, SPEC, BUILD, "twelve-region-probe",
         "TEST ONLY. Camera probe of the 12-region hue, saturation and lightness stage (builder "
                           "0x7E56E186): each ART entry's film code gets its own 12-region table through the hash "
                           "0x7E78C6E4 (empty slots only), tables written over the stock tables of the descriptors that "
                           "the chosen cases return (byte copies of table A / B, and the stock Key Line still table: "
                           "scene modes and stock Key Line use the probe tables in this build); ART "
                           "12's film code takes Cross Process I's look curve. Data edits only, no code. Needs "
                           "films-look-exif-artbkt before it (the look entry of code 159 is stock-films-structure-2's). "
                           "See experiments/2026-11-20-twelve-region/NOTES.md.",
         "TEST ONLY, not for use: films-look-exif-artbkt with the 12-region probe tables: each ART entry "
         "applies its own 12-region table (a test pattern, not a film simulation), ART 12 has Cross Process I's "
         "look curve. For the one camera run of experiments/2026-11-20-twelve-region/NOTES.md; go back to "
         "films-look-exif after it")


if __name__ == "__main__":
    main()
