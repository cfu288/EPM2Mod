# List address ranges in the map whose start or end falls inside a function.
# usage: python3 boundary_lint.py [REPO (default: two levels up)] [OUT_TSV]
# A range "0xA–0xB" (code addresses, at least 64 bytes) passes when:
#   - A is a function start (or lies in a data page), and
#   - B+1 or B is a function start, or B is within the last 16 bytes of its function (or in a data page).
# Ranges written with "~" are still checked; struck-through text (~~…~~) is skipped.
# Not flagged (known-acceptable cases, see audit/fixes-L1-b.md §3):
#   - a code range that ends on the last byte of a return (ret/retf DE/DF xx xx, rets/rti F0 FC/FD);
#   - a line that says the range is data, approximate ("~", "about", "round") or a span inside one function.
import bisect, csv, glob, os, re, sys

repo = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
out = sys.argv[2] if len(sys.argv) > 2 else None
blk = open(os.path.join(repo, 'build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin'), 'rb').read()
BASE = 0x7E421020
SOFT = re.compile(r'\b(data|rodata|table|tables|LUTs?|strings?|pool|blob|fill|padding|0xFF|bytes? span|inside one function|call-site span|approx\w*|about|round bound|window)\b|~', re.I)


def ends_at_return(b):
    o = b - BASE
    return 0 <= o - 2 < len(blk) and (blk[o - 2] in (0xDE, 0xDF) or blk[o - 1:o + 1] in (b'\xf0\xfc', b'\xf0\xfd'))


rows = list(csv.reader(open(os.path.join(repo, 'build/map/functions.tsv')), delimiter='\t'))[1:]
starts = sorted(int(r[0], 16) for r in rows)
is_start = set(starts)
data_fn = {int(r[0], 16) for r in rows if r[7] == '1'}
RNG = re.compile(r'(?<![0-9A-Fa-fx])0x(7[EF][0-9A-Fa-f]{6})\s*[–-]\s*~?(?:0x)?(7[EF][0-9A-Fa-f]{6})\b')


def containing(a):
    i = bisect.bisect_right(starts, a) - 1
    return i, starts[i]


hits, total, soft = [], 0, 0
files = sorted(glob.glob(os.path.join(repo, 'experiments/2026-11-08-feature-map/sections/*.md')))
files.append(os.path.join(repo, 'docs/firmware-map.md'))
for path in files:
    for n, line in enumerate(open(path), 1):
        line = re.sub(r'~~.*?~~', '', line)
        for m in RNG.finditer(line):
            a, b = int(m.group(1), 16), int(m.group(2), 16)
            if b - a < 0x40 or a < 0x7E421020 or b > 0x7F100000:
                continue
            total += 1
            _, fa = containing(a)
            j, fb = containing(b)
            nxt = starts[j + 1] if j + 1 < len(starts) else None
            start_ok = a in is_start or fa in data_fn
            end_ok = (b + 1) in is_start or b in is_start or (nxt is not None and nxt - b <= 16) or fb in data_fn or ends_at_return(b)
            if not (start_ok and end_ok) and SOFT.search(line):
                soft += 1
                continue
            if not (start_ok and end_ok):
                fix_a = '' if start_ok else f'start in fn {fa:08X} (next start {starts[bisect.bisect_right(starts, a)]:08X})'
                fix_b = '' if end_ok else f'end in fn {fb:08X} (ends {nxt - 1:08X})' if nxt else 'end in last fn'
                hits.append((os.path.basename(path), n, m.group(0), fix_a, fix_b))
print(f'ranges checked {total}; boundary inside a function: {len(hits)} hard, {soft} on lines marked data/approximate/span')
if out:
    with open(out, 'w') as f:
        f.write('file\tline\trange\tstart_problem\tend_problem\n')
        f.writelines('\t'.join(map(str, h)) + '\n' for h in hits)
