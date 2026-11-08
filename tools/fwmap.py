#!/usr/bin/env python3
"""Build a function database for a firmware block (mapping only; nothing here writes firmware).

    python3 tools/fwmap.py build                 # all stages, results in build/map/
    python3 tools/fwmap.py fn 0x7E6EDE08 [--dis] # one function: strings, callers, callees (+ disassembly)
    python3 tools/fwmap.py str 'firmup'          # strings matching a regex, with the functions that use them
    python3 tools/fwmap.py range 0x7E6C3000 0x7E6CB000   # functions in a range with their first strings
    python3 tools/fwmap.py xref 0x7E80E86F       # code and data references to an address
    python3 tools/fwmap.py tasks                 # uITRON task table (v1.6 offsets)
    python3 tools/fwmap.py --fw OTHER.BIN --base 0x7E101020 --out DIR build   # another body (any command)

Stages:
1. Function starts from two sources:
   - "call": targets of direct `call` instructions decoded in a linear objdump sweep
     (`call` on MN103 sets up the callee frame, so its target is a function entry);
   - "task": entries of the uITRON task tables;
   - "ptr": aligned data words that point into code at a function prologue. Functions reached
     only through pointers (vtables, callbacks, task entries) set up their own frame, so they start
     with `movm [regs],(sp)` (0xCF). One-instruction stubs (`retf`/`ret`) and `add -N,sp` entries
     are accepted too, unless the word sits in a jump table (neighbouring words point nearby).
2. Assemble an ELF where each start is a function symbol (.incbin slices), then objdump -d it.
   objdump restarts decoding at every symbol, so each function decodes from a true boundary.
3. Index: functions.tsv, calls.tsv (caller->callee), strrefs.tsv (function -> string it loads),
   ptrs.tsv (aligned data word -> function or string it points to), fnidx.tsv (offsets into functions.txt).

Pages (4 KiB, aligned to runtime addresses: overlays such as BASIC start on runtime 4 KiB boundaries,
and the base is 0x...020) whose bytes are mostly NUL-terminated printable strings, or whose aligned words are mostly
small integers and addresses (pointer tables, vtables), are "data" pages.
Calls decoded inside data pages are discarded.
"""
import argparse, bisect, collections, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import disasm  # noqa: E402  (objdump path, block cache, BASE)

OUT = os.path.join(ROOT, "build", "map")
FW = disasm.DEFAULT_FW   # --fw, --base and --out override these three for other bodies or versions
BASE = disasm.BASE
BIN = os.path.expanduser("~/opt/mn10300/bin")
PAGE = 0x1000
INSN = re.compile(r"^\s*([0-9a-f]+):\t(?:[0-9a-f ]+\t)?(\S+)\s*(.*)$")  # raw bytes column optional
SYM = re.compile(r"^([0-9a-f]{8}) <(\w+)>:$")
STR = re.compile(rb"[\x20-\x7e\t\n\r]{4,}\x00")
NUM = re.compile(r"(?<![\w(<])(-?0x[0-9a-f]+|-?\d+)(?![\w)>])")


def block():
    cache = None if FW == disasm.DEFAULT_FW else os.path.join(OUT, "blocks")
    path = disasm.block_file(FW, 0, cache)
    return path, open(path, "rb").read()


def string_index(data, base=None):
    """Map offset -> string for every NUL-terminated printable run of 4+ chars, and the data pages.
    Pages are numbered by runtime address (addr // PAGE)."""
    base = BASE if base is None else base
    strings, cover = {}, collections.Counter()
    for m in STR.finditer(data):
        strings[m.start()] = m.group()[:-1].decode("latin-1")
        lo_a, hi_a = base + m.start(), base + m.end()
        for p in range(lo_a // PAGE, (hi_a - 1) // PAGE + 1):
            cover[p] += min(hi_a, (p + 1) * PAGE) - max(lo_a, p * PAGE)
    data_pages = {p for p, c in cover.items() if c > PAGE // 2} | table_pages(data, base)
    return strings, data_pages


def table_pages(data, base=None, share=0.6):
    """Pages where most aligned words look like table data: small ints, -1..-0xFFFF, or addresses in
    block 0, RAM (0x60..) or uncached RAM (0xA0..). Code pages score about 0.08 (median); 0.6 is safe."""
    base = BASE if base is None else base
    pages = set()
    for p in range(base // PAGE, (base + len(data) - 1) // PAGE + 1):
        lo, hi = max(0, p * PAGE - base), min(len(data) - 3, (p + 1) * PAGE - base)
        words = [int.from_bytes(data[o:o + 4], "little") for o in range(lo, hi, 4)]
        hits = sum(1 for v in words if v < 0x10000 or v >= 0xFFFF0000 or base <= v < base + len(data)
                   or 0x60000000 <= v < 0x62000000 or 0xA0000000 <= v < 0xA2000000)
        if words and hits > share * len(words):
            pages.add(p)
    return pages


def iter_insns(lines):
    for line in lines:
        m = INSN.match(line)
        if m:
            yield int(m.group(1), 16), m.group(2), m.group(3)


def stage_linear(path, base):
    out = os.path.join(OUT, "linear.txt")
    if not os.path.exists(out):
        with open(out, "w") as f:
            subprocess.check_call([disasm.objdump_path(), "-D", "-b", "binary", "-m", "am33-2", "-EL",
                                   f"--adjust-vma={base:#x}", path], stdout=f)
    return out


def call_target(op, arg):
    if op in ("call", "calls"):
        m = re.match(r"(?:0x)?([0-9a-f]+)\b", arg)
        if m:
            return int(m.group(1), 16)
    return None  # indirect: calls (a0)


def stage_starts(linear, base, size, data_pages):
    callers = collections.defaultdict(set)
    with open(linear) as f:
        for a, op, arg in iter_insns(f):
            t = call_target(op, arg)
            if t is not None and base <= t < base + size and a // PAGE not in data_pages:
                callers[t].add(a)
    return {t for t in callers if t // PAGE not in data_pages}


PROLOGUE = (b"\xcf",)                       # movm [regs],(sp)
WEAK_ENTRY = (b"\xde", b"\xdf", b"\xf8\xfe", b"\xfa\xfe")  # retf, ret, add -imm8/-imm16,sp


def stage_ptr_starts(data, base, code_pages):
    size, starts = len(data), set()
    words = [int.from_bytes(data[o:o + 4], "little") for o in range(0, size - 3, 4)]

    def codeptr(v):
        return base <= v < base + size and v // PAGE in code_pages

    for i, v in enumerate(words):
        if not codeptr(v):
            continue
        head = data[v - base:v - base + 2]
        if head.startswith(PROLOGUE):
            starts.add(v)
        elif head.startswith(WEAK_ENTRY) and (base + i * 4) // PAGE not in code_pages:
            near = [w for w in words[max(0, i - 1):i + 2] if w != v and codeptr(w) and abs(w - v) < 0x800]
            if not near:
                starts.add(v)
    return starts


def task_starts(data, base):
    """Entries of the CPU0 and CPU1 uITRON task tables (v1.6 offsets, see cmd_tasks)."""
    u32 = lambda o: int.from_bytes(data[o:o + 4], "little")
    starts = set()
    for o in (TASK_CFG, TASK_CFG_CPU1):
        while u32(o):
            starts.add(u32(o + 12))
            o += 28
    return starts


def data_run_starts(base, data_pages):
    """First address of each run of data pages, so no function runs on into data."""
    return {max(base, p * PAGE) for p in data_pages if p - 1 not in data_pages}


def stage_elf(path, base, size, starts):
    asm = os.path.join(OUT, "fn.s")
    edges = sorted({base, base + size} | {s for s in starts if base < s < base + size})
    with open(asm, "w") as f:
        f.write("\t.am33_2\n\t.text\n")
        for lo, hi in zip(edges, edges[1:]):
            name = f"f_{lo:08x}"
            f.write(f"\t.globl {name}\n\t.type {name},@function\n{name}:\n"
                    f"\t.incbin \"{path}\",{lo - base:#x},{hi - lo:#x}\n\t.size {name},{hi - lo:#x}\n")
    obj, elf = os.path.join(OUT, "fn.o"), os.path.join(OUT, "fn.elf")
    subprocess.check_call([f"{BIN}/mn10300-elf-as", "-o", obj, asm])
    subprocess.check_call([f"{BIN}/mn10300-elf-ld", "-Ttext", f"{base:#x}", "-e", f"{base:#x}", "-o", elf, obj])
    dis = os.path.join(OUT, "functions.txt")
    with open(dis, "w") as f:
        subprocess.check_call([disasm.objdump_path(), "-d", "-m", "am33-2", "--no-show-raw-insn", elf], stdout=f)
    return dis


def stage_index(dis, base, size, strings, data_pages):
    soffs = sorted(strings)
    funcs, cur = {}, None
    calls, refs = [], []
    with open(dis, "rb") as f:
        pos = 0
        for raw in f:
            line, here, pos = raw.decode("latin-1"), pos, pos + len(raw)
            m = SYM.match(line)
            if m:
                cur = int(m.group(1), 16)
                funcs[cur] = {"n": 0, "data": cur // PAGE in data_pages, "pos": here}
                continue
            m = INSN.match(line)
            if not m or cur is None:
                continue
            a, op, arg = int(m.group(1), 16), m.group(2), m.group(3)
            funcs[cur]["n"] += 1
            if funcs[cur]["data"] or a // PAGE in data_pages:
                continue
            t = call_target(op, arg)
            if t is not None:
                calls.append((cur, a, t))
                continue
            for tok in NUM.findall(arg):
                v = int(tok, 0) & 0xFFFFFFFF
                if base <= v < base + size and (v - base) in strings:
                    refs.append((cur, a, v))
    with open(os.path.join(OUT, "calls.tsv"), "w") as f:
        f.write("caller_fn\tsite\tcallee\n")
        f.writelines(f"{c:08x}\t{s:08x}\t{t:08x}\n" for c, s, t in calls)
    with open(os.path.join(OUT, "strrefs.tsv"), "w") as f:
        f.write("fn\tsite\tstr_addr\ttext\n")
        for c, s, v in refs:
            txt = strings[v - base].replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")
            f.write(f"{c:08x}\t{s:08x}\t{v:08x}\t{txt}\n")
    ncall = collections.Counter(t for _, _, t in calls)
    nout = collections.Counter(c for c, _, _ in calls)
    nref = collections.Counter(c for c, _, _ in refs)
    keys = sorted(funcs)
    with open(os.path.join(OUT, "functions.tsv"), "w") as f:
        f.write("addr\toffset\tsize\tinsns\tcallers\tcallees\tstrrefs\tdata_page\n")
        for i, k in enumerate(keys):
            end = keys[i + 1] if i + 1 < len(keys) else base + size
            f.write(f"{k:08x}\t{k - base:06x}\t{end - k}\t{funcs[k]['n']}\t{ncall[k]}\t{nout[k]}\t{nref[k]}\t"
                    f"{int(funcs[k]['data'])}\n")
    with open(os.path.join(OUT, "fnidx.tsv"), "w") as f:
        f.writelines(f"{k:08x}\t{funcs[k]['pos']}\n" for k in keys)
    return len(keys), len(calls), len(refs)


def stage_ptrs(data, base, strings, starts, code_pages):
    """Aligned words outside code pages that hold the address of a function start or a string."""
    starts = set(starts)
    with open(os.path.join(OUT, "ptrs.tsv"), "w") as f:
        f.write("word_addr\ttarget\tkind\n")
        for o in range(0, len(data) - 3, 4):
            if (base + o) // PAGE in code_pages:
                continue
            v = int.from_bytes(data[o:o + 4], "little")
            if v in starts:
                f.write(f"{base + o:08x}\t{v:08x}\tfn\n")
            elif base <= v < base + len(data) and (v - base) in strings:
                f.write(f"{base + o:08x}\t{v:08x}\tstr\n")


def cmd_build(a):
    os.makedirs(OUT, exist_ok=True)
    base = BASE
    path, data = block()
    strings, data_pages = string_index(data)
    print(f"strings {len(strings)}, data pages {len(data_pages)}/{len(data) // PAGE + 1}")
    linear = stage_linear(path, base)
    call_starts = stage_starts(linear, base, len(data), data_pages)
    # Every page that is not data counts as code: pages holding only pointer-reached functions
    # (task entries, vtable methods) have no call targets of their own.
    code_pages = set(range(base // PAGE, (base + len(data) - 1) // PAGE + 1)) - data_pages
    ptr_starts = stage_ptr_starts(data, base, code_pages)
    tsk_starts = task_starts(data, base) if FW == disasm.DEFAULT_FW else set()  # tables are v1.6 offsets
    starts = sorted(call_starts | ptr_starts | tsk_starts | data_run_starts(base, data_pages))
    with open(os.path.join(OUT, "starts.tsv"), "w") as f:
        f.write("addr\tsource\n")
        for t in starts:
            src = "+".join(k for k, ss in (("call", call_starts), ("ptr", ptr_starts), ("task", tsk_starts))
                           if t in ss) or "data"
            f.write(f"{t:08x}\t{src}\n")
    print(f"function starts {len(starts)} (call {len(call_starts)}, ptr {len(ptr_starts)}, "
          f"ptr-only {len(ptr_starts - call_starts)})")
    dis = stage_elf(path, base, len(data), starts)
    n, c, r = stage_index(dis, base, len(data), strings, data_pages)
    stage_ptrs(data, base, strings, starts, code_pages)
    print(f"functions {n}, call edges {c}, string refs {r} -> {OUT}")


def load_tsv(name):
    with open(os.path.join(OUT, name)) as f:
        next(f)
        return [l.rstrip("\n").split("\t") for l in f]


def fn_starts():
    return [int(r[0], 16) for r in load_tsv("functions.tsv")]


def containing(addrs, a):
    return addrs[bisect.bisect_right(addrs, a) - 1]


def disassembly(fn):
    pos = next(int(p) for k, p in load_tsv("fnidx.tsv") if int(k, 16) == fn)
    out = []
    with open(os.path.join(OUT, "functions.txt"), "rb") as f:
        f.seek(pos)
        for raw in f:
            line = raw.decode("latin-1")
            if out and SYM.match(line.rstrip("\n")):
                break
            out.append(line)
    return "".join(out)


def cmd_fn(a):
    addrs = fn_starts()
    fn = containing(addrs, int(a.addr, 0))
    row = next(r for r in load_tsv("functions.tsv") if int(r[0], 16) == fn)
    print("addr offset size insns callers callees strrefs data_page:", " ".join(row))
    for r in load_tsv("strrefs.tsv"):
        if int(r[0], 16) == fn:
            print(f"  str  {r[1]} -> {r[2]}  {r[3]}")
    calls = load_tsv("calls.tsv")
    callers = sorted({r[0] for r in calls if int(r[2], 16) == fn})
    callees = sorted({r[2] for r in calls if int(r[0], 16) == fn})
    ptr = [r[0] for r in load_tsv("ptrs.tsv") if int(r[1], 16) == fn]
    print(f"  callers ({len(callers)}): {' '.join(callers[:200])}")
    print(f"  callees ({len(callees)}): {' '.join(callees[:200])}")
    if ptr:
        print(f"  data words pointing here ({len(ptr)}): {' '.join(ptr[:50])}")
    if a.dis:
        print(disassembly(fn), end="")


def cmd_str(a):
    rx = re.compile(a.regex, 0 if a.case else re.I)
    _, data = block()
    strings, _ = string_index(data)
    users = collections.defaultdict(set)
    for r in load_tsv("strrefs.tsv"):
        users[int(r[2], 16)].add(r[0])
    tables = collections.defaultdict(set)
    for r in load_tsv("ptrs.tsv"):
        if r[2] == "str":
            tables[int(r[1], 16)].add(r[0])
    n = 0
    for off in sorted(strings):
        t = strings[off]
        if rx.search(t):
            addr = BASE + off
            u = " ".join(sorted(users[addr])[:12])
            d = " ".join(sorted(tables[addr])[:6])
            print(f"{addr:08x}  {t[:120]!r}  fn: {u or '-'}" + (f"  data: {d}" if d else ""))
            n += 1
            if n >= a.limit:
                print(f"... (limit {a.limit})")
                break


def cmd_range(a):
    lo, hi = int(a.lo, 0), int(a.hi, 0)
    first = collections.defaultdict(list)
    for r in load_tsv("strrefs.tsv"):
        f = int(r[0], 16)
        if lo <= f < hi and len(first[f]) < a.n:
            first[f].append(r[3][:60])
    for r in load_tsv("functions.tsv"):
        f = int(r[0], 16)
        if lo <= f < hi:
            print(f"{r[0]} size {r[2]:>5} callers {r[4]:>4} callees {r[5]:>3}  " + " | ".join(first[f]))


def cmd_xref(a):
    t = int(a.addr, 0)
    for r in load_tsv("strrefs.tsv"):
        if int(r[2], 16) == t:
            print(f"code  fn {r[0]} site {r[1]}")
    for r in load_tsv("calls.tsv"):
        if int(r[2], 16) == t:
            print(f"call  fn {r[0]} site {r[1]}")
    for r in load_tsv("ptrs.tsv"):
        if int(r[1], 16) == t:
            print(f"data  word {r[0]} ({r[2]})")
    _, data = block()
    needle = t.to_bytes(4, "little")
    i = data.find(needle)
    while i >= 0:
        print(f"raw   bytes at {BASE + i:08x} (offset {i:#x}{', unaligned' if i % 4 else ''})")
        i = data.find(needle, i + 1)


TASK_NAMES = 0x4D222   # v1.6 block-0 offset: records of u16 id + char[24], sorted by name
TASK_CFG = 0x17CB0     # v1.6 block-0 offset: CPU0 records {id, attr, exinf, entry, pri, stack size, stack}
TASK_CFG_CPU1 = 0x1C490  # same layout; ids with bit 12 set run on the second core
# Where the boot code's own OlyTaSt() check label disagrees with the name table (see feature-map section 01).
TASK_LABELS = {0x8085: "DBG_OUT (name table: PWR_STANDBY)", 0x0001: "boot task (name table: DBG_OUT)",
               # CPU1 has no name table; these are the boot code's check labels.
               0x9004: "DBG_MESS1", 0x9005: "TSK_FACE_PT1", 0x9006: "IMG_ART_P", 0x9007: "MOV_AVCHD",
               0x9008: "MOV_AVCHDI", 0x900B: "ART_SUB", 0x900C: "MOV_ENCODE", 0x900D: "C3D_BRG_C0L_C1P",
               0x900E: "C3D_BRG_C1P_C0L", 0x1001: "CPU1 boot task", 0x1002: "C3D_EXE", 0x1003: "SCHEAPDBG",
               0x1010: "CPUCONN1"}


def cmd_tasks(a):
    """Name = name_table[(id & 0x7FFF) - 1], checked against OlyTaSt labels in the boot code.
    attr 2 = TA_ACT (started at boot). A record with id 0 ends each table."""
    _, b = block()
    u32 = lambda o: int.from_bytes(b[o:o + 4], "little")
    names, p = {}, TASK_NAMES
    while all(32 < c < 127 for c in b[p + 2:p + 4]):
        names[int.from_bytes(b[p:p + 2], "little")] = b[p + 2:p + 26].split(b"\0")[0].decode()
        p += 26
    print("cpu\tid\tname\tentry\tpri\tstack\tattr")
    for cpu, o in ((0, TASK_CFG), (1, TASK_CFG_CPU1)):
        while u32(o):
            tid, attr, entry, pri, stk = u32(o), u32(o + 4), u32(o + 12), u32(o + 16), u32(o + 20)
            name = TASK_LABELS.get(tid) or (names.get((tid & 0x7FFF) - 1, "?") if cpu == 0 else "?")
            print(f"{cpu}\t{tid:#06x}\t{name}\t{entry:08x}\t{pri}\t{stk:#x}\t{attr}")
            o += 28


def main():
    global FW, BASE, OUT
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fw", default=disasm.DEFAULT_FW, help="firmware .BIN (default: stock E-PM2 v1.6)")
    ap.add_argument("--base", default=hex(disasm.BASE), help="runtime base of block 0")
    ap.add_argument("--out", default=OUT, help="database directory")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    sub.add_parser("tasks")
    p = sub.add_parser("fn")
    p.add_argument("addr")
    p.add_argument("--dis", action="store_true")
    p = sub.add_parser("str")
    p.add_argument("regex")
    p.add_argument("--case", action="store_true", help="case-sensitive")
    p.add_argument("--limit", type=int, default=200)
    p = sub.add_parser("range")
    p.add_argument("lo")
    p.add_argument("hi")
    p.add_argument("-n", type=int, default=3, help="strings shown per function")
    p = sub.add_parser("xref")
    p.add_argument("addr")
    a = ap.parse_args()
    FW, BASE, OUT = os.path.abspath(a.fw), int(a.base, 0), os.path.abspath(a.out)
    {"build": cmd_build, "fn": cmd_fn, "str": cmd_str, "range": cmd_range, "xref": cmd_xref,
     "tasks": cmd_tasks}[a.cmd](a)


if __name__ == "__main__":
    main()
