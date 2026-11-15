"""Extract the English UI text table of a body from its unpacked resource block.

    python3 lang_enu.py OUT.json BLOCK_0101.bin [BLOCK_0101.expanded.bin ...]

A language blob is {u32 pointer-array address, u32 its end}, a pool of NUL-terminated UTF-16LE
strings, the pointer array (run-time addresses, one per string id), then a footer text that holds
"OlympusLanguage_<code>". This tool finds the footer of the English blob ("enu"), walks back over
the pointer array, derives the run-time base from the first pointer (= base + 8) and reads every id.
It needs no per-body constants. Output: a JSON list, index = string id.
For the bodies with olycompress resources give the expanded data (expand.py) as well.
"""
import json, re, struct, sys

KEY = "OlympusLanguage_enu".encode("utf-16-le")


def table(data: bytes) -> list[str] | None:
    best = None
    for m in re.finditer(re.escape(KEY), data):
        # the footer starts within 0x400 bytes after the pointer array; find the array end
        for end in range(m.start() & ~1, max(m.start() - 0x800, 8), -2):
            # candidate: the 64 u32 before `end` are close run-time addresses
            vals = struct.unpack_from("<64I", data, end - 256)
            lo, hi = min(vals), max(vals)
            if lo > 0x100000 and hi - lo < 0x200000:
                break
        else:
            continue
        for align in (0, 2):
            e = end - align
            start = e
            ref = struct.unpack_from("<I", data, e - 4)[0]
            while start >= 4 and abs(struct.unpack_from("<I", data, start - 4)[0] - ref) < 0x200000:
                start -= 4
            ptrs = struct.unpack_from(f"<{(e - start) // 4}I", data, start)
            if len(ptrs) < 300:
                continue
            base = min(ptrs) - 8
            # header check: u32 at head = base + (start - head)
            head = None
            for h in range(start - 8, max(start - 0x200000, -1), -2):
                if struct.unpack_from("<I", data, h)[0] == base + (start - h):
                    head = h
                    break
            if head is None:
                continue
            n = (struct.unpack_from("<I", data, head + 4)[0] - struct.unpack_from("<I", data, head)[0]) // 4
            ptrs = struct.unpack_from(f"<{n}I", data, start)
            out = []
            for p in ptrs:
                o = head + p - base
                q = o
                while data[q:q + 2] != b"\0\0" and q < start:
                    q += 2
                out.append(data[o:q].decode("utf-16-le", "replace"))
            if best is None or len(out) > len(best):
                best = out
    return best


def main() -> None:
    best = None
    for path in sys.argv[2:]:
        t = table(open(path, "rb").read())
        if t and (best is None or len(t) > len(best)):
            best = t
    if best is None:
        raise SystemExit("no English table found")
    json.dump(best, open(sys.argv[1], "w"), ensure_ascii=False, indent=0)
    print(sys.argv[1], len(best), "ids", sum(1 for s in best if s), "non-empty")


main()
