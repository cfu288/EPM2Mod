#!/usr/bin/env python3
"""Runs of unreferenced strings in the rodata of the three loaded segments (read-only).

    python3 deadstr.py [MINLEN] > ../results/dead_strings.tsv

rodata is cut into tokens: a C string (2+ printable bytes and one NUL) or NUL padding. A string is
"referenced" when any 4-byte window of block 0, at ANY byte alignment, holds an address inside it
(its first byte, or any later byte: tail-merged suffixes count). A run is a maximal sequence of
adjacent unreferenced strings. Because every string ends in NUL and the run starts right after a NUL
(or after non-string data), reading a neighbouring string cannot enter the run.
A string token that directly follows binary data is dropped (it may be the printable tail of that data).
Columns: fixed = share of strings in the run whose distance to the next string equals the most common
distance of 8+ bytes (near 1.0 = a fixed-width record array that may be indexed: NOT safe); maxpad = longest NUL
padding inside the run (long padding also means fixed-width records); meanlen = mean string length
(below 5 = binary records that happen to be printable); prev = str when the token before the run is a
referenced string (a string pool), bin when it is binary data (the run may be the string table of a
binary object, such as a shader blob, read by offsets inside that object: NOT safe without a hand check).
Not visible: a reader that walks a packed list of strings from a pointer outside the run.
"""
import collections, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reach, q
B = reach.BASE
RODATA = [(0x7E731588, 0x7E8808C0, 1), (0x7EBABF90, 0x7ECB083C, 2), (0x7EECE318, 0x7F033B7C, 3)]
TOK = re.compile(rb"([\x20-\x7e\t\n\r\x1b]{2,}\x00)|(\x00+)")


def scan(data, minlen):
    rows = []
    for lo, hi, seg in RODATA:
        ref = bytearray(hi - lo)
        for _, v in q.win(lo, hi, data):
            ref[v - lo] = 1
        blob = data[lo - B:hi - B]
        pos, run, prev = 0, [], ['bin']

        def flush():
            if run:
                s, e = run[0][0], run[-1][1]
                e2 = e
                while e2 < len(blob) and blob[e2] == 0 and not ref[e2]:
                    e2 += 1                                   # trailing NUL padding
                if e2 - s >= minlen:
                    starts = [a for a, _ in run]
                    d = collections.Counter(b - a for a, b in zip(starts, starts[1:]) if b - a >= 8)
                    fixed = d.most_common(1)[0][1] / (len(starts) - 1) if len(starts) > 2 and d else 0.0
                    pads = [b[0] - a[1] for a, b in zip(run, run[1:])]
                    mean = sum(b - a - 1 for a, b in run) / len(run)
                    rows.append((lo + s, lo + e2, seg, len(run), fixed, max(pads, default=0), mean, prev[0],
                                 blob[max(0, s - 24):s], blob[s:s + 70]))
                run.clear()

        after_binary = True
        while pos < len(blob):
            m = TOK.match(blob, pos)
            if not m:
                flush()
                pos += 1
                after_binary = True
                continue
            if m.group(1):
                if any(ref[m.start():m.end()]):
                    flush()
                    prev[0] = "str"
                elif not after_binary:
                    run.append((m.start(), m.end()))
                else:
                    prev[0] = "bin"
                after_binary = False
            elif any(ref[m.start():m.end()]):
                flush()                                       # referenced padding (empty string / data)
            pos = m.end()
        flush()
    return rows


def main():
    minlen = int(sys.argv[1]) if len(sys.argv) > 1 else 64
    data = open(reach.BLK, "rb").read()
    rows = sorted(scan(data, minlen), key=lambda r: r[0] - r[1])
    print("start\tend\tsize\tseg\tstrings\tfixed\tmaxpad\tmeanlen\tprev\tbefore\tfirst_bytes")
    tot = collections.Counter()
    for s, e, seg, n, fixed, mp, mean, prev, before, body in rows:
        ok = fixed < 0.5 and mp <= 3 and mean >= 5 and prev == "str"
        tot[(seg, ok)] += e - s
        print(f"{s:08x}\t{e:08x}\t{e - s}\t{seg}\t{n}\t{fixed:.2f}\t{mp}\t{mean:.1f}\t{prev}\t{before!r}\t{body!r}")
    print("# bytes by (segment, packed-not-fixed):", dict(tot), file=sys.stderr)


if __name__ == "__main__":
    main()
