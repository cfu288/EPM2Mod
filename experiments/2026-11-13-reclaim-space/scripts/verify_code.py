#!/usr/bin/env python3
"""For each dead code run of results/dead_decoded.tsv (>= MIN bytes): list every raw reference into it
and say where the source is (read-only).   python3 verify_code.py PKL [MIN] > ../results/dead_code_refs.tsv

Source classes: dead = inside a dead run (does not count); mid-insn = inside a live instruction, not at
its first byte (cannot execute as an instruction unless something jumps into the middle of that
instruction; such a jump would itself be a reference); insn = a live instruction starts there (a real
reference: must not occur); data = outside the code runs (a call/jmp opcode byte in data is not code).
"""
import bisect, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reach
from lib import DB


def main():
    db = DB(sys.argv[1])
    minlen = int(sys.argv[2]) if len(sys.argv) > 2 else 64
    live = db.live()
    runs = [(a, b) for a, b, i, j in reach.dead_runs(db.A, live)]
    starts = [a for a, _ in runs]

    def in_dead(x):
        k = bisect.bisect_right(starts, x) - 1
        return k >= 0 and x < runs[k][1]

    print("run_start\trun_end\tsize\tkind\tsource\ttarget\tsource_class")
    tot = {}
    for a, b in sorted(runs, key=lambda r: r[0] - r[1]):
        if b - a < minlen:
            continue
        refs = db.refs(a, b)
        n = {"dead": 0, "mid-insn": 0, "insn": 0, "data": 0}
        lines = []
        for t, s, k in refs:
            if in_dead(s):
                c = "dead"
            elif not reach.seg_of(s):
                c = "data" if k != "dec" else "insn"
            else:
                i = bisect.bisect_right(db.A, s) - 1
                c = "insn" if (db.A[i] == s and k != "win") else "mid-insn"
                if k == "win":                      # an immediate inside a live instruction is a real pointer
                    c = "insn"
            n[c] += 1
            if c != "dead":
                lines.append(f"{a:08x}\t{b:08x}\t{b - a}\t{k}\t{s:08x}\t{t:08x}\t{c}")
        print(f"{a:08x}\t{b:08x}\t{b - a}\tSUMMARY\t-\t-\t{n}")
        for l in lines:
            print(l)


if __name__ == "__main__":
    main()
