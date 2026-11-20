"""Emulator check of the probe: the stage entry 0x7E56E661 (worker 0x7E56E495 + builder 0x7E56E186) run in om-emu.

    OMP_NUM_THREADS=2 uv run python experiments/2026-11-20-twelve-region/scripts/emucheck.py

For each film code, colour-space byte P+82 = 0 / 1 and picture mode P+83 = 2 (Natural) / 4: the real code selects a
descriptor and builds the engine block. Checked against the Python reading of the builder: the 12 x 24 B record
words at out+568, the mask at out+856 and the ten curve pointers at out+884..920 (table + 336 ...). The same rows on
the base build (films-look-exif-artbkt) and for 40 stock codes: every stock code must select the same table as
before. Exit status 1 on any mismatch.
"""
import json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "emulator"))
import omemu, patchblock  # noqa: E402
import tables as T  # noqa: E402

ENTRY = 0x7E56E661
JOB, P, KEY, OUT = omemu.DATA, omemu.DATA + 0x400, omemu.DATA + 0x800, omemu.DATA + 0x1000
PTRS = [(884, 336), (892, 720), (896, 1104), (908, 1296), (916, 1488), (888, 1680), (900, 2064), (904, 2448),
        (912, 2640), (920, 2832)]
TABLE_A, TABLE_B = 0x7E76C3C8, 0x7E76CF9C
STOCK_CODES = [3, 9, 13, 19, 21, 25, 29, 31, 32, 36, 37, 44, 45, 50, 55, 56, 57, 63, 69, 70, 88, 91, 93, 119, 123,
               129, 133, 134, 136, 137, 139, 141, 142, 143, 148, 149, 162, 167, 168, 181, 182, 183, 184]


def run(emu, code, cs, mode):
    emu.write(JOB, bytes(0x400)); emu.write(P, bytes(0x400)); emu.write(KEY, bytes(0x100)); emu.write(OUT, bytes(0x400))
    emu.write(JOB + 96, struct.pack("<I", P))
    emu.write(P + 79, bytes([code])); emu.write(P + 82, bytes([cs])); emu.write(P + 83, bytes([mode]))
    r = emu.call(ENTRY, {"a0": JOB, "a1": KEY, "d0": 0, "d1": OUT}, trace=False)
    out = emu.read(OUT, 0x400)
    tab = struct.unpack_from("<I", out, 884)[0] - 336
    return r["regs"]["d0"], tab, out


def expected(image, tab):
    t = image[tab - omemu.BASE:tab - omemu.BASE + T.TABLE_BYTES]
    words = []
    for i in range(12):
        h = struct.unpack_from("<6H3h", t, 28 * i)
        b = t[28 * i + 20:28 * i + 26]
        words += [h[0] | h[1] << 16, h[2] | h[3] << 16, h[4] | h[5] << 16, b[0] | b[1] << 8 | b[2] << 16 | b[3] << 24,
                  b[4] | b[5] << 8 | (h[6] & 0xFFFF) << 16, (h[7] & 0xFFFF) | (h[8] & 0xFFFF) << 16]
    return words, struct.unpack_from("<H", t, 3024)[0], [tab + o for _, o in PTRS]


def check(emu, image, code, cs, mode, want_table=None):
    ret, tab, out = run(emu, code, cs, mode)
    words = list(struct.unpack_from("<72I", out, 568))
    mask = struct.unpack_from("<I", out, 856)[0]
    ptrs = [struct.unpack_from("<I", out, o)[0] for o, _ in PTRS]
    ew, em, ep = expected(image, tab)
    errs = []
    if ret != 1:
        errs.append(f"return {ret}")
    if (words, mask, ptrs) != (ew, em, ep):
        errs.append("engine block differs from the Python reading of the builder")
    if want_table is not None and image[tab - omemu.BASE:tab - omemu.BASE + T.TABLE_BYTES] != want_table:
        errs.append("selected table is not the expected one")
    return tab, mask, errs


def main():
    os.chdir(ROOT)
    build = json.load(open("data/builds/twelve-region-probe.json"))
    _, probe, _ = patchblock.patched_block0(build["specs"])
    _, base, _ = patchblock.patched_block0(build["specs"][:-1])
    paths = {}
    for name, img in (("base", base), ("probe", probe)):
        paths[name] = os.path.join(ROOT, "build", f"twelve-{name}.block0.bin")
        open(paths[name], "wb").write(img)
    bad = 0
    sel = {}
    for name in ("base", "probe"):
        img = open(paths[name], "rb").read()
        with omemu.Emu() as emu:
            emu.load(paths[name])
            for n, entry, code, tname, film, what in T.ENTRIES:
                for cs in (0, 1):
                    for mode in (2, 4):
                        want = None
                        if name == "probe":
                            if tname is None:
                                want = img[TABLE_A - omemu.BASE:TABLE_A - omemu.BASE + T.TABLE_BYTES] if cs == 0 else \
                                    img[TABLE_B - omemu.BASE:TABLE_B - omemu.BASE + T.TABLE_BYTES]
                            else:
                                tn = T.__dict__  # noqa
                                want = T.table({"HUEMAP": "MARKER"}.get(tname, tname) if cs else tname)
                        tab, mask, errs = check(emu, img, code, cs, mode, want)
                        sel[(name, code, cs, mode)] = tab
                        if errs:
                            bad += 1
                        print(f"{name:5s} ART {n:2d} code {code:3d} P+82 {cs} P+83 {mode}: table {tab:#x} mask {mask:#05x}"
                              f" {'OK' if not errs else 'FAIL ' + '; '.join(errs)}")
            for code in STOCK_CODES:
                for cs in (0, 1):
                    tab, mask, errs = check(emu, img, code, cs, 2)
                    sel[(name, code, cs, 2)] = tab
                    bad += bool(errs)
    for code in STOCK_CODES:
        for cs in (0, 1):
            if sel[("base", code, cs, 2)] != sel[("probe", code, cs, 2)]:
                print(f"stock code {code} P+82 {cs}: table {sel[('base', code, cs, 2)]:#x} -> {sel[('probe', code, cs, 2)]:#x}"
                      " (pointer changed)")
                bad += 1
    changed_content = [c for c in STOCK_CODES if any(
        base[sel[("base", c, cs, 2)] - omemu.BASE:][:T.TABLE_BYTES] != probe[sel[("probe", c, cs, 2)] - omemu.BASE:][:T.TABLE_BYTES]
        for cs in (0, 1))]
    print(f"stock codes ({len(STOCK_CODES)}): same table pointer on both builds; codes whose table content is a probe "
          f"table in this build: {changed_content}")
    print("RESULT", "PASS" if not bad else f"FAIL ({bad})")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
