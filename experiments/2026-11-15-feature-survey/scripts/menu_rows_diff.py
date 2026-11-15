"""Compare the menu tables of two bodies of the E-PL5 family (E-PL5, E-PM2, E-PL6).

    python3 menu_rows_diff.py A_BLOCK0 A_ENU.json B_BLOCK0 B_ENU.json

Prints the Custom Menu item rows (16-byte records {text, setting, 0, index, help, panel, flag,
group}) and the sub-item rows (20-byte records {panel, title, setting, 2, 7, 1, text, 0}) that
only one of the two has. Both tables are found by their first record, which is the same in the
three bodies. Panel child lists: use ../../2026-11-14-level-gauge/scripts/panels.py and paneldiff.py.
"""
import json, re, struct, sys


def load(block: str, enu: str):
    d, t = open(block, "rb").read(), json.load(open(enu))
    name = lambda i: re.sub("@A0..@", "@", t[i]).replace("\r\n", " ") if i < len(t) else str(i)
    custom, x = set(), d.find(struct.pack("<8H", 51, 2000, 0, 0, 422, 0, 1, 0))
    while True:
        r = struct.unpack_from("<8H", d, x)
        if not (0 < r[0] < len(t) and r[4] < len(t) and r[7] < 30):
            break
        custom.add((name(r[0]), r[1], r[7]))
        x += 16
    sub, x = set(), d.find(struct.pack("<HHIIHHHH", 9, 225, 10003, 2, 7, 1, 223, 0))
    while True:
        r = struct.unpack_from("<HHIIHHHH", d, x)
        if not r[0]:
            break
        sub.add((r[0], name(r[1]), r[2], name(r[6])))
        x += 20
    return custom, sub


ca, sa = load(sys.argv[1], sys.argv[2])
cb, sb = load(sys.argv[3], sys.argv[4])
print("custom rows (text, setting, group):", len(ca), len(cb))
print("  only A:", sorted(ca - cb))
print("  only B:", sorted(cb - ca))
print("sub-item rows (panel, title, setting, text):", len(sa), len(sb))
print("  only A:", sorted(sa - sb))
print("  only B:", sorted(sb - sa))
