#!/usr/bin/env python3
"""Class-A summary: merges results/dead_decoded.tsv (code) and results/dead_strings.tsv (strings), drops
anything that overlaps a block-0 byte touched by any patch spec in the repo, writes results/class_a.tsv."""
import collections, glob, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RES = os.path.join(HERE, "..", "results")
BASE = 0x7E421020
# runs that follow binary data, cleared by hand (README section 4): the data before them is a bounded pointer table
HAND = {0x7EBF10A2, 0x7EBB1F4C}
# string-pool runs rejected by hand: symbol tables inside 3D shader objects (read by offsets inside the object)
BLOB = {0x7F019206}


def patched():
    out = []
    for pat in ("patches/*.json", "patches/history/*.json", "experiments/*/patches/*.json", "tools/emu/specs/*.json"):
        for f in glob.glob(os.path.join(ROOT, pat)):
            for op in json.load(open(f)).get("ops", []):
                if op.get("type") == "bytes" and op.get("block") == 0:
                    off = int(op["offset"], 0) if isinstance(op["offset"], str) else op["offset"]
                    out.append((BASE + off, BASE + off + len(op["new"]) // 2, os.path.relpath(f, ROOT)))
    return out


def main():
    P = patched()
    rows = []
    for ln in open(os.path.join(RES, "dead_decoded.tsv")).read().split("\n")[1:]:
        if ln:
            c = ln.split("\t")
            if int(c[2]) >= 48:
                rows.append((int(c[0], 16), int(c[1], 16), int(c[3]), "code", "no reference from live code or data"))
    for ln in open(os.path.join(RES, "dead_strings.tsv")).read().split("\n")[1:]:
        if ln:
            c = ln.split("\t")
            size, n = int(c[2]), int(c[4])
            a = int(c[0], 16)
            if float(c[5]) < 0.5 and int(c[6]) <= 3 and n >= 5 and float(c[7]) >= 5 and (c[8] == "str" or a in HAND) and a not in BLOB:
                rows.append((a, int(c[1], 16), int(c[3]), "strings", f"{n} unreferenced strings, first {c[10][:48]}"))
    tot, clash = collections.Counter(), 0
    with open(os.path.join(RES, "class_a.tsv"), "w") as f:
        f.write("start\tend\tsize\tsegment\tkind\tevidence\n")
        for a, b, seg, kind, ev in sorted(rows, key=lambda r: (r[2], r[0] - r[1])):
            hit = [p for p in P if p[0] < b and a < p[1]]
            if hit:
                clash += 1
                continue
            tot[(seg, kind)] += b - a
            tot[(seg, kind, "n")] += 1
            if b - a >= 512:
                tot[(seg, kind, ">=512")] += b - a
            f.write(f"{a:08x}\t{b:08x}\t{b - a}\t{seg}\t{kind}\t{ev}\n")
    print("patched block-0 ranges:", len(P), "bytes", sum(b - a for a, b, _ in P), "candidate runs dropped for overlap:", clash)
    lo = min(a for a, _, _ in P); hi = max(b for _, b, _ in P)
    segs = collections.Counter()
    for a, b, _ in P:
        segs[a >> 16] += b - a
    print("patched 64K pages:", {hex(k << 16): v for k, v in sorted(segs.items())})
    for k in sorted(tot, key=str):
        print(k, tot[k])


if __name__ == "__main__":
    main()
