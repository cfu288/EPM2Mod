#!/usr/bin/env python3
"""Cut experiments: remove chosen references (a hypothesis such as "nobody types shell commands") and list
the code that only they kept alive. Class B evidence, not class A.   python3 cut.py PKL > ../results/class_b.tsv"""
import collections, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reach
from lib import DB

CUTS = [
    # name, source ranges whose references are dropped, single edges dropped
    ("U_SHELL: the three 54-entry command tables (shell 0x7E503C7E, dbgall 0x7E501F0D, 0x7E963243)",
     [(0x7E7332B4, 0x7E7332B4 + 432), (0x7E7326A4, 0x7E7326A4 + 432), (0x7EBCC2BC, 0x7EBCC2BC + 432)], ()),
    ("sdk sub-command table 0x7EBF0FA0 (30 entries)", [(0x7EBF0FA0, 0x7EBF1090)], ()),
    ("AVCHD clip-info parser: call at 0x7E6DECC4 (file node type 4 with attribute bit 32)", [], {(0x7E6DECC4, 0x7E6E22BA)}),
    ("AVCHD bitrate arm in CMD_RECORD_INIT: fall-through of bne 0x7E6EE4F7 (format byte == 2)", [], {(0x7E6EE4F7, None)}),
]


def main():
    db = DB(sys.argv[1])
    base = {(a, b) for a, b, i, j in reach.dead_runs(db.A, db.live())}
    print("cut\tstart\tend\tsize\tsegment")
    for name, cut, edges in CUTS:
        lv = reach.run(db.A, db.M, db.T, db.roots, db.raw, ("win",), cut=cut, cut_edges=edges)
        new = sorted(((a, b) for a, b, i, j in reach.dead_runs(db.A, lv) if (a, b) not in base), key=lambda r: r[0] - r[1])
        c = collections.Counter()
        for a, b in new:
            c[reach.seg_of(a)] += b - a
        print(f"# {name}: total per segment {dict(c)}, runs {len(new)}")
        for a, b in new:
            if b - a >= 256:
                print(f"{name[:24]}\t{a:08x}\t{b:08x}\t{b - a}\t{reach.seg_of(a)}")


if __name__ == "__main__":
    main()
