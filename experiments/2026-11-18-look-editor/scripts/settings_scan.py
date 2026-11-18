"""Find dormant camera settings (info ids) that a look-editor menu row could use.

    uv run python experiments/2026-11-18-look-editor/scripts/settings_scan.py > experiments/2026-11-18-look-editor/out/scan.tsv

Reads the stock v1.6 block 0 (build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin) and
experiments/2026-11-08-feature-map/sections/07-settings.tsv. For each info id it lists every mode-controller
table and GUI list that names it (layouts: feature map 13e sections 2-3, 07 section 2).
"""
import collections
import csv
import struct
import sys

BLK = "build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin"
TSV = "experiments/2026-11-08-feature-map/sections/07-settings.tsv"
B = open(BLK, "rb").read()
BASE = 0x7E421020


def rd(a, n):
    return B[a - BASE : a - BASE + n]


def u16(a):
    return struct.unpack("<H", rd(a, 2))[0]


def s16(a):
    return struct.unpack("<h", rd(a, 2))[0]


def u32(a):
    return struct.unpack("<I", rd(a, 4))[0]


hits = collections.defaultdict(list)  # id -> list of "where" strings


def add(i, what):
    hits[i].append(what)


# value-list records (13e 3.1)
VL = {}
for k in range(505):
    a = 0x7E84A0B8 + 20 * k
    info, var, raw, gui, tot, es, cl, ty, _ = struct.unpack("<HHIIHHBBH", rd(a, 20))
    n = tot // es if es else 0
    fmt = {1: "B", 2: "b", 3: "h", 4: "h", 5: "H"}.get(ty)
    vals = list(struct.unpack("<%d%s" % (n, fmt), rd(raw, n * es))) if fmt else []
    VL.setdefault(info, []).append((a, var, ty, n, vals))

# operation records (13e 3.2): slots that hold a function
OP = {}
for k in range(250):
    a = 0x7E814864 + 60 * k
    info = u16(a)
    slots = [off for off in range(4, 60, 4) if u32(a + off)]
    OP[info] = slots
    if slots:
        add(info, "op-hooks+" + "/".join(str(s) for s in slots))

# conflict table (13e 2.2)
for k in range(92):
    a = 0x7E825DA8 + 20 * k
    tgt, alt, blocks, nblk = struct.unpack("<HHIH", rd(a, 10))
    add(tgt, "conflict-target")
    if alt != 2000:
        add(alt, "conflict-alt")
    for b in range(nblk):
        conds, ncond = struct.unpack("<IH", rd(blocks + 16 * b, 6))
        for c in range(ncond):
            add(u16(conds + 8 * c), "conflict-cond(t%d)" % tgt)

# dependency table 0x7E8266C4: {u16 cond, pad, ptr targets, u16 n, pad}
for k in range(86):
    a = 0x7E8266C4 + 12 * k
    cond, _, tp, n = struct.unpack("<HHIH", rd(a, 10))
    add(cond, "dep-cond")
    for t in range(n):
        add(u16(tp + 2 * t), "dep-target(c%d)" % cond)

# bank save lists: table 0x7E83EF4C {u16 k1, u16 k2, ptr list, u16 n, pad} ended by k2 = 2000
lists = set()
a = 0x7E83EF4C
while True:
    k1, k2, lp, n = struct.unpack("<HHIH", rd(a, 10))
    if k2 == 2000 or lp == 0:
        break
    lists.add((lp, n))
    a += 12
bank = collections.defaultdict(set)
for lp, n in lists:
    for e in range(n):
        bank[u16(lp + 4 * e)].add(rd(lp + 4 * e + 2, 1)[0])
for i, bs in bank.items():
    add(i, "bank-lists(b%s)" % ",".join(map(str, sorted(bs))))

# id lists of u16
for name, a, n in (
    ("boot-reset16", 0x7E84D830, 16),  # 0x7E7068A2, run at every start when info 10017 = 0 (V emulator)
    ("reset2", 0x7E84E18A, 2),  # 0x7E7068B2
    ("reset3", 0x7E84E18E, 3),  # 0x7E7068C2
    ("full-reset", 0x7E84D850, 881),
    ("std-reset", 0x7E84DF32, 300),
    ("restore-A", 0x7E84E194, 415),
    ("restore-B", 0x7E84E4D2, 428),
):
    for e in range(n):
        add(u16(a + 2 * e), name)

# mode presets 0x7E834794 {u16, u16, ptr, u32 n}; entries {u16 id, pad, u32 value}
a = 0x7E834794
pre = collections.Counter()
while u32(a + 4) and 0x7E800000 < u32(a + 4) < 0x7E900000:
    lp, n = u32(a + 4), u32(a + 8)
    for e in range(n):
        pre[u16(lp + 8 * e)] += 1
    a += 12
for i, c in pre.items():
    add(i, "mode-preset(x%d)" % c)

# region defaults 0x7E84EDF0 {u16 area, u16 n, ptr ids, ptr values}
a = 0x7E84EDF0
while 0 < u16(a) < 64 and 0x7E800000 < u32(a + 4) < 0x7E900000:
    n, ip = u16(a + 2), u32(a + 4)
    for e in range(n):
        add(u16(ip + 2 * e), "region-default")
    a += 12

# composite id lists 0x7E8182FC: 68 x 34 B of u16 ids ended by 2000
for k in range(68):
    for e in range(17):
        v = u16(0x7E8182FC + 34 * k + 2 * e)
        if v in (0, 2000):
            continue
        add(v, "composite")

# GUI list descriptors {u16 setting, u16 count, u32 0, u32 1, ptr items} (28-B items, value u32 at +16)
DESC = collections.defaultdict(list)
for a in range(0x7EF00000, 0x7F030000, 4):
    s, c, z, o, p = struct.unpack("<HHIII", rd(a, 16))
    if z == 0 and o == 1 and 0 < c < 200 and 0x7EE00000 <= p < 0x7F100000:
        vals = [u32(p + 28 * j + 16) for j in range(c)]
        DESC[s].append((a, c, vals))

rows = {}
for r in csv.reader(open(TSV), delimiter="\t"):
    if r[0].startswith("#") or r[0] == "tag_hex":
        continue
    for ent in r[10].split(","):
        if not ent:
            continue
        i = int(ent.split("[")[0])
        code = sum(int(r[c] or 0) for c in (7, 8, 9, 11, 12, 13, 14))
        rows[i] = dict(tag=r[0], dev=r[2], count=r[3], type=r[4], default=r[5], code=code, menu=r[15], ent=ent)

out = csv.writer(sys.stdout, delimiter="\t")
out.writerow(["id", "tag", "dev", "type", "prm_default", "mcon_default", "code_refs", "menu", "mcon_lists", "gui_lists", "tables"])
for i in sorted(rows):
    r = rows[i]
    mdef = u32(0x7E84C82C + 4 * i) if i <= 700 else ""
    vl = ";".join("%s:n%d:%s" % (hex(a), n, ",".join(map(str, v[:20]))) for a, var, ty, n, v in VL.get(i, []))
    gl = ";".join("%s:n%d:%s" % (hex(a), c, ",".join(map(str, v[:20]))) for a, c, v in DESC.get(i, []))
    out.writerow([i, r["tag"] + ("" if "[" not in r["ent"] else "[" + r["ent"].split("[")[1]), r["dev"], r["type"], r["default"], mdef, r["code"], r["menu"], vl, gl, " ".join(hits.get(i, []))])
