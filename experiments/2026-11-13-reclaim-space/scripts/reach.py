#!/usr/bin/env python3
"""Instruction-level live set of E-PM2 v1.6 block 0; reports the bytes NOT in it (read-only, stdlib only).

    python3 reach.py [--out DIR] [--pkl FILE]     # dead_strict.tsv / dead_decoded.tsv in DIR (default ../results)

Candidates: the bytes of the three RAM-loaded code runs (CODE). Their decode is build/map/functions.txt
(objdump restarted at every known function start, so every start is a true instruction boundary).
Always-live sources: every byte outside CODE (boot/kernel area, rodata of all segments, .data image,
0xFF gaps, overlays A/B, everything above 0x7F034000). References found in them are roots.
An instruction becomes live when a live source reaches it; a target inside an instruction marks it.
  seq   the next instruction, unless this one is ret/retf/rets/rti/rtm/jmp/bra/lra or break (0xFF)
  dec   targets printed by objdump (call/calls/jmp/Bcc, abs32 operands); from CODE and from the
        kernel/overlay code; decode of rodata is not trusted (win/ph cover rodata)
  win   every 4-byte little-endian window starting at ANY byte of the source whose value is in CODE
  ph    phantom transfers: any byte read as call d16/d32 (CD/DD), calls d16/d32 (FA FF/FC FF),
        jmp d16/d32 (CC/DC), whether or not an instruction starts there
STRICT = seq+dec+win+ph (ph is nearly all noise, so STRICT under-reports); DECODED = seq+dec+win.
"""
import argparse, array, bisect, collections, os, pickle, re, struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
BLK = os.path.join(ROOT, "build", "blocks", "OLY_E_101_1600_0000_0000.BIN.block0.bin")
DIS = os.path.join(ROOT, "build", "map", "functions.txt")
BASE = 0x7E421020
CODE = [(0x7E4FE000, 0x7E731585, 1), (0x7E8808C0, 0x7E880F44, 1),
        (0x7E8F5800, 0x7EBABF8E, 2), (0x7ECCB800, 0x7EECE318, 3)]
# code outside CODE whose objdump targets are trusted as roots (rodata inside only adds noise roots)
LIVECODE = [(0x7E421020, 0x7E4C5534), (0x7F05C000, 0x7F06B000), (0x7F080000, 0x7F0EB800), (0x7F100000, 0x7F119000)]
STOP = {"ret", "retf", "rets", "rti", "rtm", "jmp", "bra", "lra", "break"}


def seg_of(a):
    for lo, hi, s in CODE:
        if lo <= a < hi:
            return s
    return 0


def in_livecode(a):
    return any(lo <= a < hi for lo, hi in LIVECODE)


def raw_edges(data):
    n = len(data)
    for k in range(4):
        m = (n - k) // 4
        for j, v in enumerate(array.array("I", data[k:k + 4 * m])):
            if 0x7E4FE000 <= v < 0x7EECE318 and seg_of(v):
                yield "win", BASE + k + 4 * j, v
    for pat, fmt, skip in ((b"[\xcd\xcc]", "<h", 1), (b"[\xdd\xdc]", "<i", 1),
                           (b"\xfa\xff", "<h", 2), (b"\xfc\xff", "<i", 2)):
        for m in re.finditer(pat, data[:n - 8]):
            o = m.start()
            t = BASE + o + struct.unpack_from(fmt, data, o + skip)[0]
            if seg_of(t):
                yield "ph", BASE + o, t


def parse():
    """Instruction arrays for CODE (addr, mnemonic, decoded targets) and root targets from LIVECODE."""
    A, M, T, roots, fstart = [], [], {}, [], set()
    sym = re.compile(r"^([0-9a-f]{8}) <f_")
    ins = re.compile(r"^([0-9a-f]{8}):\t(\S+)\s*(.*)$")
    ref = re.compile(r"\b(7[ef][0-9a-f]{6}) <")
    with open(DIS) as f:
        for ln in f:
            m = ins.match(ln)
            if not m:
                m = sym.match(ln)
                if m:
                    fstart.add(int(m.group(1), 16))
                continue
            a = int(m.group(1), 16)
            s = seg_of(a)
            if not s and not in_livecode(a):
                continue
            ts = [int(r, 16) for r in ref.findall(m.group(3))] if "<" in m.group(3) else ()
            if s:
                A.append(a); M.append(m.group(2))
                if ts:
                    T[a] = ts
            else:
                roots.extend((a, t) for t in ts if seg_of(t))
    return A, M, T, roots, fstart


def run(A, M, T, roots, raw, kinds, cut=(), cut_edges=(), align=1):
    """cut: [(lo, hi)] source ranges whose references are ignored (a hypothesis: 'this table/code is dead').
    cut_edges: {(site, target)} single edges to ignore; (site, None) cuts the seq edge after site.
    align: only data windows at addresses that are multiples of this count (sensitivity test)."""
    n = len(A)
    cut_edges = set(cut_edges)
    isc = lambda s: any(lo <= s < hi for lo, hi in cut)
    raw = [(k, s, t) for k, s, t in raw if k in kinds and not isc(s) and (s, t) not in cut_edges
           and (align == 1 or seg_of(s) or k != "win" or s % align == 0)]
    roots = [(s, t) for s, t in roots if not isc(s) and (s, t) not in cut_edges]
    src = sorted((s, t) for k, s, t in raw if seg_of(s))
    skeys = [s for s, _ in src]
    live = bytearray(n)
    work = []

    def hit(t):
        i = bisect.bisect_right(A, t) - 1
        if i >= 0 and seg_of(t) and not live[i]:
            live[i] = 1
            work.append(i)

    for k, s, t in raw:
        if not seg_of(s):
            hit(t)
    for _, t in roots:
        hit(t)
    while work:
        i = work.pop()
        a = A[i]
        e = A[i + 1] if i + 1 < n else a + 1
        if M[i] not in STOP and i + 1 < n and seg_of(e) == seg_of(a) and (a, None) not in cut_edges:
            hit(e)
        for t in T.get(a, ()):
            if (a, t) not in cut_edges:
                hit(t)
        for j in range(bisect.bisect_left(skeys, a), bisect.bisect_left(skeys, e)):
            hit(src[j][1])
    return live


def dead_runs(A, live):
    """Maximal runs of non-live instructions; consecutive in address and inside one code run."""
    out, i, n = [], 0, len(A)
    while i < n:
        if live[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and not live[j + 1] and seg_of(A[j + 1]) == seg_of(A[i]) and A[j + 1] - A[j] < 0x100:
            j += 1
        end = A[j + 1] if j + 1 < n and seg_of(A[j + 1]) == seg_of(A[i]) and A[j + 1] - A[j] < 0x100 else None
        if end is None:
            end = next(hi for lo, hi, _ in CODE if lo <= A[j] < hi)
        out.append((A[i], end, i, j))
        i = j + 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "..", "results"))
    ap.add_argument("--pkl")
    a = ap.parse_args()
    data = open(BLK, "rb").read()
    A, M, T, roots, fstart = parse()
    raw = list(raw_edges(data))
    print(f"instructions in CODE {len(A)}; raw edges {collections.Counter(k for k, _, _ in raw)}; kernel/overlay roots {len(roots)}")
    os.makedirs(a.out, exist_ok=True)
    res = {}
    for name, kinds in (("strict", ("win", "ph")), ("decoded", ("win",))):
        live = run(A, M, T, roots, raw, kinds)
        runs = dead_runs(A, live)
        res[name] = runs
        tot = collections.Counter()
        with open(os.path.join(a.out, f"dead_{name}.tsv"), "w") as f:
            f.write("start\tend\tsize\tsegment\tinsns\tnon_pad_insns\tfirst_mnemonics\n")
            for lo, hi, i, j in sorted(runs, key=lambda r: -(r[1] - r[0])):
                ms = M[i:j + 1]
                real = sum(1 for m in ms if m not in ("break", "nop"))
                tot[seg_of(lo)] += hi - lo
                f.write(f"{lo:08x}\t{hi:08x}\t{hi - lo}\t{seg_of(lo)}\t{j - i + 1}\t{real}\t{' '.join(ms[:6])}\n")
        print(name, "dead runs", len(runs), "bytes per segment", dict(tot))
    if a.pkl:
        pickle.dump(dict(A=A, M=M, T=T, roots=roots, raw=raw, res=res, fstart=fstart), open(a.pkl, "wb"))


if __name__ == "__main__":
    main()
