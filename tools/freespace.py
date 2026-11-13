#!/usr/bin/env python3
"""Verify candidate free areas in E-PM2 v1.6 block 0 (read-only; standard library only).

    python3 tools/freespace.py map                    # regenerate docs/code-space-map.md and .tsv
    python3 tools/freespace.py check SPEC [SPEC ...]  # verify the bytes that specs add in free areas
    python3 tools/freespace.py area 0x7E4C9100        # all checks for the area that holds an address
    python3 tools/freespace.py selftest               # known facts; a few seconds

Where each fact comes from:
  derived  = read from the bytes of stock block 0 by this tool. Each boot copy, clear loop and stack
             pointer is a SITE: an address, the instruction bytes expected there, and the fields to
             read from its immediates. If the bytes at a site differ, the tool stops with an error.
  hand     = listed in a file under docs/ (candidates, bounds, pointer waivers, superseded specs).
             Each hand row that names a site also gives expected bytes, and the tool checks them.
  optional = build/map/linear.txt and build/map/functions.tsv (objdump sweep and function DB from
             tools/fwmap.py). Without them, the checks that need a decode return UNKNOWN.

Limit of every check: this is a static scan of constants. A pointer or a write address that the
firmware computes at run time (base + index, heap, memory test) is invisible to it.

This tool never writes under build/ and never changes firmware. It writes docs/code-space-map.*
only in `map`.
"""
import argparse, bisect, glob, hashlib, json, mmap, os, re, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOCK_FW = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
STOCK_BLOCK0 = "build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin"
STOCK_BLOCK0_SHA256 = "1b7c4bb187e5e0b6e76ef362a4095a5b3fcf92917367999d32d6b6404b71468d"
LINEAR = "build/map/linear.txt"
FUNCTIONS = "build/map/functions.tsv"
CANDIDATES = "docs/space-candidates.tsv"
BOUNDS = "docs/space-bounds.tsv"
WAIVERS = "docs/space-pointer-waivers.tsv"
SUPERSEDED = "docs/space-superseded.tsv"
CAMERA_LOG = "docs/camera-log.md"
MAP_MD = "docs/code-space-map.md"
MAP_TSV = "docs/code-space-map.tsv"
SPEC_GLOBS = ["patches/*.json", "patches/history/*.json", "experiments/*/patches/*.json",
              "tools/emu/specs/*.json"]

BASE = 0x7E421020            # runtime address of block-0 file offset 0
FLASH0 = 0x402C0020          # flash address (cached alias) of block-0 file offset 0; checked below
M32 = 0xFFFFFFFF
PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"


class SiteError(SystemExit):
    pass


def die(msg):
    raise SiteError("freespace: FATAL: " + msg)


def rel(p):
    return os.path.join(ROOT, p)


def h(a):
    return "0x%08X" % a


def rng(lo, hi):
    return "%s-%s" % (h(lo), h(hi))


def canon(a):
    """Cached address of an uncached alias (helper 0x7E45DAEF: 0x8.., 0xA.., 0xB.. -> 0x4.., 0x6.., 0x7..)."""
    return (a & 0x3FFFFFFF) | 0x40000000 if a & 0x80000000 else a


# ----------------------------------------------------------------------------- stock block 0

def load_block0():
    p = rel(STOCK_BLOCK0)
    if os.path.exists(p):
        data = open(p, "rb").read()
    else:                                   # fall back to the container; nothing is written
        sys.path.insert(0, rel("tools"))
        import oetool
        data = oetool.parse(open(rel(STOCK_FW), "rb").read())[0][0]["payload"]
    if hashlib.sha256(data).hexdigest() != STOCK_BLOCK0_SHA256:
        die("stock block 0 has sha256 %s, expected %s" % (hashlib.sha256(data).hexdigest(), STOCK_BLOCK0_SHA256))
    return data


def container_flash_base():
    """Flash address of block-0 offset 0 from the update container header (addr @8 + 32-byte header)."""
    p = rel(STOCK_FW)
    if not os.path.exists(p):
        return None
    hd = open(p, "rb").read(32)
    if hd[:2] != b"OE":
        die("stock firmware does not start with an OE block header")
    return struct.unpack_from("<I", hd, 8)[0] + 32


# ----------------------------------------------------------------------------- sites (derived)

TOKEN = re.compile(r"\{(\w+)(?::(\d))?\}")


def match_site(b, name, addr, template):
    """Compare the bytes at addr with a hex template. {x} is a 4-byte and {x:2} a 2-byte LE field."""
    off, pos, out = addr - BASE, 0, {}
    for m in TOKEN.finditer(template):
        lit = bytes.fromhex(template[pos:m.start()])
        if b[off:off + len(lit)] != lit:
            die("site %s at %s: bytes are %s, expected %s" % (name, h(BASE + off), b[off:off + len(lit)].hex(), lit.hex()))
        off += len(lit)
        n = int(m.group(2) or 4)
        out[m.group(1)] = int.from_bytes(b[off:off + n], "little")
        off += n
        pos = m.end()
    lit = bytes.fromhex(template[pos:])
    if b[off:off + len(lit)] != lit:
        die("site %s at %s: bytes are %s, expected %s" % (name, h(BASE + off), b[off:off + len(lit)].hex(), lit.hex()))
    return out


VEC7 = "".join("fccf{v%d}0f%02x80" % (i, 4 * i) for i in range(7)) + "0d1c80"
SYSF = "fcdc{dst}fcdd{src}fccc{end}fcc0{neg}2d0301dd%sffa04c"   # Usr1/Usr2 read request to SYSFMEM 0x7E451306

SITES = {   # name: (address, template)
    # reset stub: three clears, 7 vector registers, initial SP, jump to the reset main
    "reset_stub": (0x7E421042,
                   "fccd{c1e}fccc{c1s}dda9030000f050fafe0001fafe00ff"
                   "fccd{c2e}fccc{c2s}dd8e030000f050fafe0001fafe00ff"
                   "fccd{c3e}fccc{c3s}dd73030000f050fafe0001"
                   "f8fe9cdd5e5200008008f8fe64" + VEC7 +
                   "fccf{spbase}2e{spsize:2}fcc604000000ebf1eff2fc" "fcdc{entry}f0f4"),
    "reset_wcopy1": (0x7E421125, "fcdc{end}fcdd{start}fcde{dst}f1d0f114c80c850479516a52f104c1fa"),
    "reset_wcopy2": (0x7E421192, "fcdc{end}fcdd{start}fcde{dst}f1d0f114c80c850479516a52f104c1fa"
                                 "fccc{cs}82fccc{ce}8188cd3402f050"),
    # reset main: flash reads through 0x7E4217E6 (a0 = flash source, a1 = destination, d1 = size)
    "reset_loads": (0x7E4211F5,
                    "fccc{dend}fc8184a44d60" "fccc{kend}81fc8580a44d60" "0042048004420800"
                    "fcdc{ksrc}fcdd{kdst}fcc1{kneg}cdbe05f028"
                    "fca584a44d60" "0042048004420800"
                    "fcdc{dsrc}fcdd{ddst}fcc1{dneg}cd9905f028"
                    "0042048001420800" "fcdc{ssrc}fcdd{sdst}2d{ssize:2}cd7d05f028"),
    "reset_data_copy": (0x7E4212B8, "fccc{start}81fccc{end}3e220c460cfcce{ram}4a10f1044214004218f8921cf8921d98cdc84ce018"),
    "reset_load_ext": (0x7E42134E, "fcdc{src}fcdd{dst}fccd{size}cd8604f028"),
    # CPU1 start: SP, 7 vector registers, jump
    "cpu1_start": (0x7E4267DA, "fcdc{sp}f2f0"
                   "2faa2a0f808a2f01010f40892f01110f44892f01210f48892f01310f4c892f01410f50892f01510f54892f01610f5889"
                   + VEC7 + "fcdc{entry}f0f4"),
    "cpu1_clears": (0x7E426938, "fccc{s1}fccd{e1}cd1902f050fccc{s2}fccd{e2}cd0802f050"),
    "kernel_start_sp": (0x7E432974, "24{sz0:2}fcd0{b0}f2f0ca10" "24{sz1:2}fcd0{b1}f2f0cceb0e"),
    "vector_save_cpu0": (0x7E430020, "fc91fcffffff5800fc81{s0}5804fc81{s1}fcb4fcffffffdc0c260000"),
    "nmi_entries": (0x7E44B670, "5800fc81{s0}5804fc81{s1}fcdd{sp0}f2f4fcff51860100f0fd"
                                "5800fc81{s2}5804fc81{s3}fcdd{sp1}f2f4fcff31860100f0fd"),
    # boot task (CPU0 task 1)
    "boot_load_seg1": (0x7E44A060, "0042048004420800fcdc{src}fcdd{dst}fccd{end}fcc1{neg}dd6677fdfff028"),
    "boot_sram_copy": (0x7E44A109, "fcdd{src}fcdc{dst}04db7151605044fac9{cnt:2}d4"),
    # Usr1 (task 0x52) and Usr2
    "usr1_load_seg2": (0x7E504BF2, "fcce{end}18fcc2{neg}850cddccbbf2fff01888fcdc{dst}fcdd{src}2d0301ddeec6f4ffa04c"),
    "usr1_load_data": (0x7E504D0C, "fcdc{dst}fcdd{src}2c{size:2}2d0101dde8c5f4ffa04c"),
    "usr1_load_seg3": (0x7E504D50, SYSF % "9bc5f4"),
    "usr1_load_third": (0x7E504FB2, SYSF % "39c3f4"),
    "usr2_load_ovl_a": (0x7E50503D, SYSF % "aec2f4"),
    "usr2_load_ovl_b": (0x7E5050BC, SYSF % "2fc2f4"),
    # alias helper: (addr & 0x3FFFFFFF) | 0x40000000 for 0x80000000-0x80FFFFFF and 0xA0000000-0xBFFFFFFF
    "alias_helper": (0x7E45DAEF, "cf8082fccd00000080f204a4c80588ca34a6c40c8501fcca00000081c415fcca000000a0c40c8501"
                                 "fcca000000c0c4030488fce0ffffff3ffce400000040a501c80388de8004"),
    # kernel configuration words (their meaning is inferred, see write ranges)
    "kcfg0_pool": (0x7E43EF24, "{pool}{size}"),
    "kcfg0_stacks": (0x7E43EF60, "{kstk}{kstksz}{sram}{sramsz}16000000{tasktab}"),
    "kcfg1_pool": (0x7E43F0B0, "{pool}{size}"),
    "kcfg1_stacks": (0x7E43F0EC, "{kstk}{kstksz}{sram}{sramsz}16000000{tasktab}"),
    # kernel start: store the configuration root in the per-CPU slot {slot} + 4 * cpu
    "percpu_root_cpu0": (0x7E4329A1, "305080fccf{slot}54fccd{root}f1ecf350"),
    "percpu_root_cpu1": (0x7E433889, "305080fccf{slot}54fccd{root}f1ecf350"),
}


class Rng:
    def __init__(self, name, lo, hi, site, note="", **kw):
        self.name, self.lo, self.hi, self.site, self.note = name, lo, hi, site, note
        self.__dict__.update(kw)


class Model:
    """Load map, copy sources, write ranges and task tables, all read from the bytes."""

    def __init__(self, b):
        self.b, self.end = b, BASE + len(b)
        f = self.f = {n: match_site(b, n, a, t) for n, (a, t) in SITES.items()}
        sa = lambda n: SITES[n][0]
        fb = container_flash_base()
        if fb is not None and fb != FLASH0:
            die("container header gives flash base %s, tool has %s" % (h(fb), h(FLASH0)))
        self.flash_base_src = "container header (addr @8 + 32)" if fb is not None else "not checked (stock BIN absent)"
        self.loads, self.reads, self.writes = [], [], []

        def load(name, lo, hi, dst, src, site, phase, order, who, cond=""):
            if canon(dst) != lo:
                die("load %s: destination %s is not the alias of %s" % (name, h(dst), h(lo)))
            if not lo < hi:
                die("load %s: empty range %s" % (name, rng(lo, hi)))
            if canon(src) != FLASH0 + (lo - BASE):
                die("load %s: flash source %s does not follow flash = %s + offset" % (name, h(src), h(FLASH0)))
            self.loads.append(Rng(name, lo, hi, site, src=src, dst=dst, phase=phase, order=order, who=who, cond=cond))

        r = f["reset_loads"]
        load("kernel", -r["kneg"] & M32, r["kend"], r["kdst"], r["ksrc"], 0x7E421228, "reset", 1, "reset main")
        load("data-image", -r["dneg"] & M32, r["dend"], r["ddst"], r["dsrc"], 0x7E42124D, "reset", 2, "reset main")
        s_lo = canon(r["sdst"])
        load("sram-image", s_lo, s_lo + r["ssize"], r["sdst"], r["ssrc"], 0x7E421269, "reset", 3, "reset main")
        r = f["boot_load_seg1"]
        load("segment-1", -r["neg"] & M32, r["end"], r["dst"], r["src"], 0x7E44A080, "boot task", 4, "boot task (CPU0 task 1)")
        r = f["usr1_load_seg2"]
        load("segment-2", -r["neg"] & M32, r["end"], r["dst"], r["src"], 0x7E504C18, "Usr1", 5, "Usr1 (task 0x52)")
        r = f["usr1_load_seg3"]
        load("segment-3", -r["neg"] & M32, r["end"], r["dst"], r["src"], 0x7E504D6B, "Usr1", 6, "Usr1 (task 0x52)")
        r = f["usr1_load_third"]
        load("usr1-third", -r["neg"] & M32, r["end"], r["dst"], r["src"], 0x7E504FCD, "Usr1", 7, "Usr1 (task 0x52)")
        r = f["usr2_load_ovl_a"]
        load("overlay-A", -r["neg"] & M32, r["end"], r["dst"], r["src"], 0x7E505058, "Usr2", 8, "Usr2 bit 0", "on demand")
        r = f["usr2_load_ovl_b"]
        load("overlay-B", -r["neg"] & M32, r["end"], r["dst"], r["src"], 0x7E5050D7, "Usr2", 9, "Usr2 bit 1", "on demand")
        self.loads.sort(key=lambda x: x.lo)
        for x, y in zip(self.loads, self.loads[1:]):
            if x.hi > y.lo:
                die("load ranges %s and %s overlap" % (x.name, y.name))
        self.kernel_lo = next(x.lo for x in self.loads if x.name == "kernel")

        # The reset code runs at BASE.. and reads tables there before the first copy in block 0.
        st = f["reset_stub"]
        if not BASE <= st["entry"] < self.kernel_lo:
            die("reset stub jumps to %s, outside the pre-reset range" % h(st["entry"]))
        self.pre = Rng("pre-reset", BASE, self.kernel_lo, sa("reset_stub"),
                       "in memory before the reset code runs (it executes here: absolute jump to %s; it reads %s). "
                       "The loader is outside block 0; the extent is inferred from the first copy start"
                       % (h(st["entry"]), h(f["reset_wcopy1"]["start"])))

        # copy sources inside block 0 (their bytes are data that some code reads)
        def read(name, lo, hi, site, note):
            self.reads.append(Rng(name, lo, hi, site, note))

        w1, w2, dc, sr = f["reset_wcopy1"], f["reset_wcopy2"], f["reset_data_copy"], f["boot_sram_copy"]
        read("reset word copy 1", w1["start"], w1["end"], sa("reset_wcopy1"), "copied to %s" % h(w1["dst"]))
        read("reset word copy 2", w2["start"], w2["end"], sa("reset_wcopy2"), "copied to %s (conditional)" % h(w2["dst"]))
        read(".data image copy", dc["start"], dc["end"], sa("reset_data_copy"), "copied to RAM %s" % h(dc["ram"]))
        read("SRAM code copy", canon(sr["src"]), canon(sr["src"]) + 4 * sr["cnt"], sa("boot_sram_copy"),
             "%d words copied to SRAM %s" % (sr["cnt"], h(sr["dst"])))

        # constant-destination writes (canonical addresses)
        def write(name, lo, hi, site, basis, note=""):
            self.writes.append(Rng(name, canon(lo), canon(hi), site, note, basis=basis))

        for L in self.loads:
            write("load " + L.name, L.lo, L.hi, L.site, "derived", "flash read")
        e = f["reset_load_ext"]
        write("reset flash read (source outside block 0)", e["dst"], e["dst"] + e["size"], sa("reset_load_ext"), "derived")
        write("reset word copy 1", w1["dst"], w1["dst"] + w1["end"] - w1["start"], sa("reset_wcopy1"), "derived")
        write("reset word copy 2", w2["dst"], w2["dst"] + w2["end"] - w2["start"], sa("reset_wcopy2"), "derived")
        write(".data in RAM", dc["ram"], dc["ram"] + dc["end"] - dc["start"], sa("reset_data_copy"), "derived")
        write("SRAM code copy", sr["dst"], sr["dst"] + 4 * sr["cnt"], sa("boot_sram_copy"), "derived")
        u = f["usr1_load_data"]
        write("Usr1 flash read to RAM", u["dst"], u["dst"] + u["size"], sa("usr1_load_data"), "derived")
        for i in (1, 2, 3):
            write("reset clear %d (0x7E4213F7)" % i, st["c%ds" % i], st["c%de" % i], sa("reset_stub"), "derived")
        write("reset clear 4 (conditional)", w2["cs"], w2["ce"], sa("reset_wcopy2"), "derived")
        c = f["cpu1_clears"]
        write("CPU1 boot clear 1 (0x7E426B5D)", c["s1"], c["e1"], sa("cpu1_clears"), "derived")
        write("CPU1 boot clear 2 (0x7E426B5D)", c["s2"], c["e2"], sa("cpu1_clears"), "derived")
        write("reset stack (initial SP = base + size - 4)", st["spbase"], st["spbase"] + st["spsize"], sa("reset_stub"), "derived")
        c1 = f["cpu1_start"]
        write("CPU1 start stack (initial SP %s; extent inferred: the 2 KiB below SP + 4)" % h(c1["sp"]),
              c1["sp"] + 4 - 0x800, c1["sp"] + 4, sa("cpu1_start"), "derived SP, inferred size")
        k = f["kernel_start_sp"]
        write("kernel start stack CPU0 (SP = base + size)", k["b0"], k["b0"] + k["sz0"], sa("kernel_start_sp"), "derived")
        write("kernel start stack CPU1 (SP = base + size)", k["b1"], k["b1"] + k["sz1"], sa("kernel_start_sp"), "derived")
        n = f["nmi_entries"]
        if n["sp0"] != n["sp1"]:
            die("the two NMI entries set different stack pointers")
        write("NMI entry stack (SP %s; extent inferred: 4 KiB below)" % h(n["sp0"]), n["sp0"] - 0x1000, n["sp0"],
              sa("nmi_entries"), "derived SP, inferred size")
        v = f["vector_save_cpu0"]
        for a in sorted({v["s0"], v["s1"], n["s0"], n["s1"], n["s2"], n["s3"]}):
            write("vector entry save word", a, a + 4, sa("vector_save_cpu0"), "derived")
        for cpu, pn, sn in ((0, "kcfg0_pool", "kcfg0_stacks"), (1, "kcfg1_pool", "kcfg1_stacks")):
            p, s = f[pn], f[sn]
            write("kernel config CPU%d: {address, size} pair, read as the kernel memory pool (dynamic task stacks)" % cpu,
                  p["pool"], p["pool"] + p["size"], sa(pn), "derived words, inferred meaning")
            write("kernel config CPU%d: {address, size} pair before the task table pointer" % cpu,
                  s["kstk"], s["kstk"] + s["kstksz"], sa(sn), "derived words, inferred meaning")
            write("kernel config CPU%d: second {address, size} pair (SRAM)" % cpu,
                  s["sram"], s["sram"] + s["sramsz"], sa(sn), "derived words, inferred meaning")

        # vector entry stubs (addresses loaded into the vector registers 0x8000..0x8018)
        self.vectors = [("CPU0", [st["v%d" % i] for i in range(7)], sa("reset_stub")),
                        ("CPU1", [c1["v%d" % i] for i in range(7)], sa("cpu1_start"))]

        self.percpu = [(c, f[n]["slot"], f[n]["root"], sa(n)) for c, n in ((0, "percpu_root_cpu0"), (1, "percpu_root_cpu1"))]
        for c, slot, root, _ in self.percpu:
            if self.load_of(root) is None or self.load_of(root).name != "kernel":
                die("per-CPU root %s of CPU%d is not in the kernel image" % (h(root), c))

        # task tables: the kernel configuration gives their addresses
        self.tasks = []
        for cpu, sn in ((0, "kcfg0_stacks"), (1, "kcfg1_stacks")):
            t = f[sn]["tasktab"]
            off, rows = t - BASE, []
            while True:
                rec = struct.unpack_from("<7I", b, off)
                if rec == (0,) * 7:
                    break
                if not BASE <= rec[3] < self.end or rec[5] == 0 or rec[5] > 0x100000:
                    die("task table CPU%d at %s: record at %s is not a task record" % (cpu, h(t), h(BASE + off)))
                rows.append(rec)
                off += 28
            self.tasks.append((cpu, t, rows))
            for tid, attr, exinf, entry, pri, stksz, stk in rows:
                if stk:
                    write("task %s stack (CPU%d table)" % (hex(tid), cpu), stk, stk + stksz, t, "derived")
        if [len(r) for _, _, r in self.tasks] != [147, 30]:
            die("task tables have %s records, expected [147, 30]" % [len(r) for _, _, r in self.tasks])
        boot = [r for r in self.tasks[0][2] if r[1] & 2]
        if len(boot) != 1 or not SITES["boot_load_seg1"][0] - 0x40 < boot[0][3] <= SITES["boot_load_seg1"][0]:
            die("CPU0 task table: the TA_ACT task is not the boot task that holds the segment-1 copy")
        self.boot_entry = boot[0][3]
        self.entries = {"reset": st["entry"], "boot task": self.boot_entry,
                        "Usr1": next(r[3] for r in self.tasks[0][2] if r[0] == 0x52), "Usr2": 0x7E505005}
        self.writes.sort(key=lambda x: (x.lo, x.hi, x.name))

    def load_of(self, a):
        for L in self.loads:
            if L.lo <= a < L.hi:
                return L
        return None

    def aliases(self):
        return [("runtime", 0), ("uncached", 0x40000000), ("flash", (FLASH0 - BASE) & M32),
                ("flash-uncached", (FLASH0 - BASE + 0x40000000) & M32)]


# ----------------------------------------------------------------------------- optional decode

INS_TERMINAL = {"ret", "retf", "rets", "rti", "jmp", "bra"}
BCC = {"beq", "bne", "bgt", "bge", "ble", "blt", "bhi", "bcc", "bls", "bcs", "bvc", "bvs", "bnc", "bns", "bra"}
NUM = re.compile(r"-?0x[0-9a-f]+|-?\d+")


class Linear:
    """build/map/linear.txt (objdump -D of block 0), searched in place. Optional."""

    def __init__(self):
        self.ok = os.path.exists(rel(LINEAR)) and os.path.exists(rel(FUNCTIONS))
        self.fn_lo, self.fn_hi = [], []
        if not self.ok:
            return
        self.fh = open(rel(LINEAR), "rb")
        self.m = mmap.mmap(self.fh.fileno(), 0, access=mmap.ACCESS_READ)
        self.n = len(self.m)
        rows = []
        with open(rel(FUNCTIONS)) as fh:
            next(fh)
            for line in fh:
                c = line.rstrip("\n").split("\t")
                if c[8] == "0":
                    rows.append((int(c[0], 16), int(c[0], 16) + int(c[2])))
        rows.sort()
        self.fn_lo = [r[0] for r in rows]
        self.fn_hi = [r[1] for r in rows]

    def in_function(self, a):
        i = bisect.bisect_right(self.fn_lo, a) - 1
        return i >= 0 and a < self.fn_hi[i]

    def _addr_line(self, pos):
        s = self.m.rfind(b"\n", 0, pos) + 1
        while s < self.n:
            if self.m[s + 8:s + 9] == b":":
                try:
                    return s, int(self.m[s:s + 8], 16)
                except ValueError:
                    pass
            e = self.m.find(b"\n", s)
            if e < 0:
                return None
            s = e + 1
        return None

    def _seek(self, addr):
        lo, hi = 0, self.n
        while hi - lo > 8192:
            mid = (lo + hi) // 2
            r = self._addr_line(mid)
            if r is None or r[1] > addr:
                hi = mid
            else:
                lo = r[0]
        return lo

    def instrs(self, start, stop):
        """Yield (addr, end, mnemonic, operands) for instructions that start in [start - 16, stop)."""
        s = self._seek(start - 16)
        cur = None
        while s < self.n:
            e = self.m.find(b"\n", s)
            if e < 0:
                e = self.n
            if self.m[s + 8:s + 9] == b":":
                c = self.m[s:e].decode("latin-1").split("\t")
                try:
                    a = int(c[0][:8], 16)
                except ValueError:
                    a = None
                if a is not None and len(c) >= 2:
                    nb = len(c[1].split())
                    if len(c) >= 3:
                        if cur:
                            yield tuple(cur)
                        if a >= stop:
                            return
                        cur = [a, a + nb, c[2].strip(), c[3].strip() if len(c) > 3 else ""]
                    elif cur and a == cur[1]:
                        cur[1] = a + nb
            s = e + 1
        if cur:
            yield tuple(cur)

    def code_run_to(self, addr, span=0x2000):
        """(instruction that holds addr, function start) if the sweep decodes from a function start in the DB
        to addr with no `break`/unknown instruction and no skipped bytes; else (None, None)."""
        i = bisect.bisect_right(self.fn_lo, addr) - 1
        if i < 0 or addr - self.fn_lo[i] > span:
            return None, None
        fn, nxt = self.fn_lo[i], None
        for ins in self.instrs(fn, addr + 1):
            if ins[0] < fn:
                continue
            if (nxt is None and ins[0] != fn) or (nxt is not None and ins[0] != nxt) or ins[2] in ("break", "unknown"):
                return None, None
            nxt = ins[1]
            if ins[0] <= addr < ins[1]:
                return ins, fn
        return None, None

    def instr_at(self, addr):
        for ins in self.instrs(addr, addr + 1):
            if ins[0] <= addr < ins[1]:
                return ins
        return None

    @staticmethod
    def operands(ins):
        return {int(x, 0) & M32 for x in NUM.findall(ins[3])}

    def cannot_skip(self, entry, site):
        """True if no decoded branch between entry and site leaves [entry, site] (so the site always runs)."""
        seen = False
        for a, e, mn, ops in self.instrs(entry, site):
            if a < entry:
                continue
            seen = True
            if mn in ("ret", "retf", "rets", "rti", "jmp"):
                return False, "%s at %s before the site" % (mn, h(a))
            if mn in BCC:
                t = [int(x, 16) for x in re.findall(r"0x([0-9a-f]+)", ops)]
                if not t or not entry <= t[0] <= site:
                    return False, "%s at %s leaves the range" % (mn, h(a))
        return (True, "no branch between %s and the site leaves that range" % h(entry)) if seen else (False, "no decode")

    def operand_refs(self, ranges):
        """Hex operands (branch/call targets, absolute addresses) that fall in any of ranges [(lo, hi)].
        Returns [(value, site, mnemonic)]. One pass over the file."""
        pref = {}
        for lo, hi in ranges:
            for d in (0, 0x40000000):
                for pg in range((lo + d) >> 12, ((hi + d - 1) >> 12) + 1):
                    pref.setdefault("%04x" % (pg >> 4), set()).add("%x" % (pg & 15))
        if not pref:
            return []
        alt = "|".join("%s[%s]" % (k, "".join(sorted(v))) for k, v in sorted(pref.items()))
        rx = re.compile(("0x(?:%s)[0-9a-f]{3}(?![0-9a-f])" % alt).encode())
        los = sorted(ranges)
        out = []
        for m in rx.finditer(self.m):
            v = canon(int(m.group()[2:], 16)) if m.group()[2:3] in b"b" else int(m.group()[2:], 16)
            i = bisect.bisect_right(los, (v, M32)) - 1
            if i < 0 or not los[i][0] <= v < los[i][1]:
                continue
            s = self.m.rfind(b"\n", 0, m.start()) + 1
            c = self.m[s:m.start()].decode("latin-1").split("\t")
            try:
                out.append((v, int(c[0][:8], 16), c[2].strip() if len(c) > 2 else "?"))
            except ValueError:
                pass
        return out


# ----------------------------------------------------------------------------- pointer windows

class Windows:
    """Every 4-byte little-endian value at every byte offset of a blob, looked up by its high 16 bits."""

    def __init__(self, blob):
        self.b, self.cache = blob, {}

    def page(self, hi16):
        if hi16 not in self.cache:
            pat, b, out = struct.pack("<H", hi16), self.b, []
            i = b.find(pat, 2)
            while i >= 0:
                out.append((b[i - 2] | b[i - 1] << 8 | hi16 << 16, i - 2))
                i = b.find(pat, i + 1)
            out.sort()
            self.cache[hi16] = out
        return self.cache[hi16]

    def in_range(self, lo, hi):
        """[(value, file offset)] for lo <= value < hi."""
        out = []
        for p in range(lo >> 16, ((hi - 1) >> 16) + 1):
            pg = self.page(p)
            i = bisect.bisect_left(pg, (lo, -1))
            while i < len(pg) and pg[i][0] < hi:
                out.append(pg[i])
                i += 1
        return out


# ----------------------------------------------------------------------------- hand files

def read_tsv(path, ncol):
    rows = []
    p = rel(path)
    if not os.path.exists(p):
        return rows
    for n, line in enumerate(open(p, encoding="utf-8"), 1):
        line = line.rstrip("\n")
        if not line.strip() or line.startswith("#"):
            continue
        c = line.split("\t")
        if len(c) != ncol:
            die("%s line %d: %d columns, expected %d" % (path, n, len(c), ncol))
        rows.append(c)
    return rows


def expect_bytes(b, where, site, hexs, what):
    exp = bytes.fromhex(hexs)
    got = b[site - BASE:site - BASE + len(exp)]
    if got != exp:
        die("%s: %s at %s has bytes %s, expected %s" % (where, what, h(site), got.hex(), exp.hex()))


# ----------------------------------------------------------------------------- specs and ledger

class Op:
    def __init__(self, spec, idx, lo, expect, new):
        self.spec, self.idx, self.off, self.expect, self.new = spec, idx, lo, expect, new
        ch = [i for i in range(len(new)) if expect[i] != new[i]]
        self.clo = BASE + lo + ch[0] if ch else None           # changed span, runtime addresses
        self.chi = BASE + lo + ch[-1] + 1 if ch else None


class Spec:
    def __init__(self, path, d=None):
        self.path = path.replace(os.sep, "/")
        d = d if d is not None else json.load(open(rel(path)))
        self.name = d.get("name", os.path.basename(path)[:-5])
        self.ops, self.other = [], 0
        for i, o in enumerate(d["ops"]):
            if o.get("type") != "bytes" or o.get("block") != 0:
                self.other += 1
                continue
            off = int(o["offset"], 0) if isinstance(o["offset"], str) else o["offset"]
            self.ops.append(Op(self, i, off, bytes.fromhex(o["expect"]), bytes.fromhex(o["new"])))
        self.history = "/history/" in self.path

    def spans(self):
        return [(o.clo, o.chi) for o in self.ops if o.clo is not None]

    def rel_targets(self):
        """Targets of relative jmp/call opcodes (dc, dd, cc, cd) that start a short changed run (<= 8 B): [(site, target)].
        A pattern match on the spec bytes, not a decode."""
        out = []
        for o in self.ops:
            if o.clo is None:
                continue
            n, a0 = o.new, BASE + o.off
            i = o.clo - a0                       # only an opcode at the first changed byte of an op counts
            for opc, dl in ((b"\xdc", 4), (b"\xdd", 4), (b"\xcc", 2), (b"\xcd", 2)):
                if n[i:i + 1] == opc and i + 1 + dl <= len(n) and o.chi - o.clo <= 8:
                    d = int.from_bytes(n[i + 1:i + 1 + dl], "little", signed=True)
                    out.append((a0 + i, (a0 + i + d) & M32))
        return out


def all_specs():
    paths = []
    for g in SPEC_GLOBS:
        paths += sorted(glob.glob(rel(g)))
    return [Spec(os.path.relpath(p, ROOT)) for p in paths]


def camera_tested():
    """Spec names that appear in an OK row of docs/camera-log.md -> first such row's date."""
    out = {}
    p = rel(CAMERA_LOG)
    if not os.path.exists(p):
        return out
    for line in open(p, encoding="utf-8"):
        c = [x.strip() for x in line.split("|")]
        if len(c) < 6 or not c[4].startswith("**OK"):
            continue
        for name in re.findall(r"[A-Za-z0-9][A-Za-z0-9_.-]*[A-Za-z0-9]", c[2]):
            out.setdefault(name[:-5] if name.endswith(".json") else name, c[1])
    return out


# ----------------------------------------------------------------------------- areas and checks

class Area:
    def __init__(self, lo, hi, source, kind, status="", note="", region=None):
        self.lo, self.hi, self.source, self.kind, self.status, self.note, self.region = lo, hi, source, kind, status, note, region
        self.checks, self.verdict, self.failing = {}, None, []
        self.used, self.used_hist, self.free_runs = [], [], []

    @property
    def size(self):
        return self.hi - self.lo

    def region_name(self):
        return self.region.name if self.region else "not loaded"


class Space:
    def __init__(self, min_run=32, use_linear=True, other_blocks=False):
        self.b = load_block0()
        self.others = []
        if other_blocks and os.path.exists(rel(STOCK_FW)):
            sys.path.insert(0, rel("tools"))
            import oetool
            blocks, tail = oetool.parse(open(rel(STOCK_FW), "rb").read())
            self.others = [("block %d" % i, Windows(x["payload"])) for i, x in enumerate(blocks) if i] + [("tail", Windows(tail))]
        self.m = Model(self.b)
        self.lin = Linear() if use_linear else None
        if self.lin is not None and not self.lin.ok:
            self.lin = None
        self.win = Windows(self.b)
        self.min_run = min_run
        self.specs = all_specs()
        self.tested = camera_tested()
        self.superseded = {}
        for spec, by, ev in read_tsv(SUPERSEDED, 3):
            if not os.path.exists(rel(spec)):
                die("%s: spec %s does not exist" % (SUPERSEDED, spec))
            self.superseded[spec] = (by, ev)
        self.bounds = []
        for obj, bound, site, exp, ev in read_tsv(BOUNDS, 5):
            o, bd, s = int(obj, 16), int(bound, 16), int(site, 16)
            expect_bytes(self.b, BOUNDS, s, exp, "reader site")
            self.bounds.append((o, bd, s, ev))
        self.waivers = []
        for site, end, exp, ev in read_tsv(WAIVERS, 4):
            expect_bytes(self.b, WAIVERS, int(site, 16), exp, "waived site")
            self.waivers.append((int(site, 16), int(end, 16), ev))
        self._build_areas()
        self._lin_refs = {}

    # ---- discovery
    def _build_areas(self):
        m, b = self.m, self.b
        cuts = sorted({m.pre.lo, m.pre.hi} | {x for L in m.loads for x in (L.lo, L.hi)}
                      | {x for r in m.reads for x in (r.lo, r.hi)})
        self.areas, self.listed = [], []
        for mt in re.finditer(b"\xff{%d,}" % self.min_run, b):
            lo, hi = BASE + mt.start(), BASE + mt.end()
            pts = [lo] + [c for c in cuts if lo < c < hi] + [hi]
            for s, e in zip(pts, pts[1:]):
                reg = m.load_of(s) or (m.pre if m.pre.lo <= s < m.pre.hi else None)
                self.areas.append(Area(s, e, "0xFF run", "ff", region=reg))
        for start, end, kind, status, src, note in read_tsv(CANDIDATES, 6):
            lo, hi = int(start, 16), int(end, 16)
            if not lo < hi or status not in ("checked", "auto"):
                die("%s: bad row %s %s" % (CANDIDATES, start, end))
            L = m.load_of(lo)
            if L is None or hi > L.hi:
                die("%s: %s is not inside one load range" % (CANDIDATES, rng(lo, hi)))
            a = Area(lo, hi, "listed: " + src, kind, status, note, L)
            self.areas.append(a)
            self.listed.append(a)
        self.areas.sort(key=lambda a: a.lo)
        for x, y in zip(self.areas, self.areas[1:]):
            if x.hi > y.lo:
                die("areas %s and %s overlap" % (rng(x.lo, x.hi), rng(y.lo, y.hi)))
        self._los = [a.lo for a in self.areas]

    def area_at(self, addr):
        i = bisect.bisect_right(self._los, addr) - 1
        return self.areas[i] if i >= 0 and addr < self.areas[i].hi else None

    def in_listed(self, addr):
        return any(a.lo <= addr < a.hi for a in self.listed)

    # ---- pointer windows
    def classify(self, value, off):
        """Return (class, text). Classes 'operand' and 'raw' count as hits; the others are explained noise."""
        site, b = BASE + off, self.b
        for lo, hi, ev in self.waivers:
            if lo <= site < hi:
                return "waived", ev
        if self.in_listed(site):
            return "from-listed", "the site is inside a listed (reclaimed) area"
        if self.lin and self.lin.in_function(site):
            ins = self.lin.instr_at(site)
            if ins is not None:
                if value in Linear.operands(ins) or canon(value) in {canon(x) for x in Linear.operands(ins)}:
                    return "operand", "%s %s at %s" % (ins[2], ins[3], h(ins[0]))
                near = [struct.unpack_from("<I", b, o)[0] for o in (off - 4, off + 4) if 0 <= o <= len(b) - 4]
                if site % 4 or not any(BASE <= canon(x) < self.m.end for x in near):
                    return "code-nonoperand", "bytes inside or across `%s %s` at %s, not its operand" % (ins[2], ins[3], h(ins[0]))
                return "raw", "4-aligned, next to another block-0 address (table inside a function range?), not the operand of `%s %s` at %s" % (
                    ins[2], ins[3], h(ins[0]))
        if site % 4 == 0 and off + 8 <= len(b):
            d = struct.unpack_from("<d", b, off)[0]
            if d == d and 1e-9 < abs(d) < 1e9 and len(repr(d)) <= 9:
                return "double", "low word of the double constant %r" % d
        def dbl(c):                                         # an 8-byte cell that is a double with a full mantissa
            if not 0 <= c <= len(b) - 8:
                return False
            q = struct.unpack_from("<Q", b, c)[0]
            lo32 = q & M32                                  # not a small integer and not itself an address of block 0
            return (0x3D0 <= (q >> 52) & 0x7FF <= 0x430 and 5 <= bin(lo32).count("1") <= 27
                    and not any(BASE <= (lo32 - d) & M32 < self.m.end for _, d in self.m.aliases()))
        for ph in (0, 4):                                   # window inside a run of doubles?
            c0 = ((off - ph) & ~7) + ph                     # cell that holds the first window byte
            last = ((off + 3 - ph) & ~7) + ph               # cell that holds the last window byte
            for start in range(last - 16, c0 + 8, 8):       # 3 consecutive cells that cover the window
                if start <= c0 and last <= start + 16 and all(dbl(start + 8 * k) for k in range(3)):
                    return "double-table", "inside three consecutive doubles at %s: %s" % (h(BASE + start), ", ".join(
                        "%.6g" % struct.unpack_from("<d", b, start + 8 * k)[0] for k in range(3)))
        if site % 4:
            w2 = struct.unpack_from("<I", b, (off & ~3) + 4)[0] if (off & ~3) + 8 <= len(b) else 0
            if BASE <= canon(w2) < self.m.end:
                return "straddle", "crosses into the 4-aligned word %s at %s, itself a block-0 address" % (h(w2), h(BASE + (off & ~3) + 4))
        return "raw", "%s data word: %s" % ("4-aligned" if site % 4 == 0 else "unaligned", b[max(0, off - 4):off + 8].hex())

    def windows(self, lo, hi):
        """All windows into [lo, hi) through each alias: [(alias, runtime value, site, class, text)]."""
        out = []
        for name, d in self.m.aliases():
            for v, off in self.win.in_range((lo + d) & M32, (hi + d) & M32):
                cls, text = self.classify(v, off)
                out.append((name, (v - d) & M32, BASE + off, cls, text))
        return sorted(out, key=lambda x: (x[1], x[2], x[0]))

    def nearest_refs(self, a):
        """Nearest referenced addresses before and after the area, from non-noise windows (runtime and uncached)."""
        before, after = None, None
        for name, d in self.m.aliases()[:2]:
            for p in {(a.lo - 1 + d) >> 16, (a.lo + d) >> 16}:
                pg = self.win.page(p & 0xFFFF)
                i = bisect.bisect_left(pg, ((a.lo + d) & M32, -1)) - 1
                while i >= 0:
                    v, off = pg[i]
                    if self.classify(v, off)[0] in ("operand", "raw"):
                        if before is None or v - d > before[0]:
                            before = (v - d, [])
                        break
                    i -= 1
            for p in {(a.hi + d) >> 16, (a.hi - 1 + d) >> 16}:
                pg = self.win.page(p & 0xFFFF)
                i = bisect.bisect_left(pg, ((a.hi + d) & M32, -1))
                while i < len(pg):
                    v, off = pg[i]
                    if self.classify(v, off)[0] in ("operand", "raw"):
                        if after is None or v - d < after[0]:
                            after = (v - d, [])
                        break
                    i += 1
        for ref in (before, after):
            if ref:
                for name, d in self.m.aliases()[:2]:
                    for v, off in self.win.in_range((ref[0] + d) & M32, (ref[0] + d + 1) & M32):
                        if self.classify(v, off)[0] in ("operand", "raw"):
                            ref[1].append(BASE + off)
                ref[1].sort()
        return before, after

    # ---- ledger
    def ledger(self, a):
        cur, hist, rows = [], [], []
        for s in self.specs:
            seg = [(max(lo, a.lo), min(hi, a.hi)) for lo, hi in s.spans() if lo < a.hi and hi > a.lo]
            if not seg:
                continue
            seg = merge(seg)
            old = s.history or s.path in self.superseded
            (hist if old else cur).extend(seg)
            rows.append((s.path, "history" if s.history else "superseded" if old else "current", seg))
        cur = merge(cur)
        free, p = [], a.lo
        for lo, hi in cur:
            if lo > p:
                free.append((p, lo))
            p = max(p, hi)
        if p < a.hi:
            free.append((p, a.hi))
        return rows, cur, merge(hist), free

    # ---- code evidence
    def code_evidence(self, a):
        """Camera-tested specs with a relative jmp/call from outside the area into it."""
        out = []
        for s in self.specs:
            if s.name not in self.tested:
                continue
            hooks = [(site, t) for site, t in s.rel_targets() if a.lo <= t < a.hi and not a.lo <= site < a.hi
                     and any(lo <= t < hi for lo, hi in s.spans())]
            if hooks:
                out.append("%s (camera log %s): jump at %s to %s" % (s.path, self.tested[s.name], h(hooks[0][0]), h(hooks[0][1])))
        return out

    # ---- all checks for one area
    def analyse(self, a, lin_refs=None):
        if a.verdict:
            return a
        m, b, ck = self.m, self.b, a.checks
        L = a.region if a.region is not m.pre else None

        # 1 loaded
        if L is None and a.region is m.pre:
            ck["loaded"] = (UNKNOWN, m.pre.note)
        elif L is None:
            ck["loaded"] = (FAIL, "outside every boot copy; the flash bytes never reach this runtime address")
        else:
            text = "%s copy at %s (%s), %s; boot order %d (%s)" % (L.name, h(L.site), rng(L.lo, L.hi), L.who, L.order, L.phase)
            st = PASS
            if L.cond:
                st, text = UNKNOWN, text + "; loaded only on demand"
            elif self.lin:
                ok, why = self.lin.cannot_skip(m.entries[L.phase], L.site)
                text += "; " + why
                if not ok:
                    st = UNKNOWN
            else:
                st, text = UNKNOWN, text + "; path to the copy not checked (no decode)"
            if L.phase == "Usr1" and st == PASS:
                text += "; hand note: Usr0 starts Usr1 on a normal boot only. On the firmware-update reboot path it does not, " \
                        "and this range is then not loaded (and no segment-2/3 code runs)"
            ck["loaded"] = (st, text)

        # 2 content
        body = b[a.lo - BASE:a.hi - BASE]
        rd = [r for r in m.reads if r.lo < a.hi and r.hi > a.lo]
        if rd:
            ck["content"] = (FAIL, "inside the source of the %s at %s (%s): these bytes are data" % (rd[0].name, h(rd[0].site), rd[0].note))
        elif a.kind == "ff":
            ck["content"] = (PASS, "all 0xFF in stock") if body.count(0xFF) == len(body) else (FAIL, "not all 0xFF")
        elif a.status == "checked":
            ck["content"] = (PASS, "listed as reclaimed %s, checked by hand (%s)" % (a.kind, a.source[8:]))
        else:
            ck["content"] = (UNKNOWN, "listed as reclaimed %s by the automatic rule only, not checked by hand (%s)" % (a.kind, a.source[8:]))

        # 3 pointers
        ws = self.windows(a.lo, a.hi)
        ends = {r.hi: r for r in m.reads}
        ws = [(w[0], w[1], w[2], "end-constant", "exclusive end of the %s source, read at its site" % ends[w[1]].name)
              if w[1] == a.lo and w[1] in ends and 0 <= w[2] - ends[w[1]].site < 0x40 else w for w in ws]
        hits = [w for w in ws if w[3] in ("operand", "raw")]
        noise = {}
        for w in ws:
            if w[3] not in ("operand", "raw"):
                noise[w[3]] = noise.get(w[3], 0) + 1
        ntext = ", ".join("%d %s" % (n, k) for k, n in sorted(noise.items())) or "none"
        a.hits, a.noise = hits, noise
        if hits:
            ck["pointers"] = (FAIL, "%d hit(s): %s%s; explained noise: %s" % (
                len(hits), "; ".join("%s at %s via %s [%s]" % (h(w[1]), h(w[2]), w[0], w[4]) for w in hits[:4]),
                " ..." if len(hits) > 4 else "", ntext))
        else:
            ck["pointers"] = (PASS, "no unexplained window in block 0 (4 aliases, every byte offset); explained noise: %s" % ntext)

        if self.others:
            cnt = [(n, sum(len(wn.in_range((a.lo + d) & M32, (a.hi + d) & M32)) for _, d in m.aliases())) for n, wn in self.others]
            a.other = ", ".join("%s %d" % x for x in cnt)
            ck["pointers"] = (ck["pointers"][0], ck["pointers"][1] + "; windows in the other blocks (reported, not counted: "
                              "resource blocks, not classified): " + a.other)

        # 4 objdump operands (optional)
        if self.lin is None:
            ck["operands"] = (UNKNOWN, "build/map/linear.txt or functions.tsv not present")
        else:
            refs = lin_refs if lin_refs is not None else self.lin.operand_refs([(a.lo, a.hi)])
            mine = sorted(r for r in refs if a.lo <= r[0] < a.hi)
            real = [r for r in mine if self.lin.in_function(r[1]) and not self.in_listed(r[1]) and not a.lo <= r[1] < a.hi]
            listed = sum(1 for r in mine if self.in_listed(r[1]))
            other = len(mine) - len(real) - listed
            tail = "; %d from listed areas, %d outside the function DB (data decoded as code) ignored" % (listed, other)
            if real:
                ck["operands"] = (FAIL, "%d operand(s) in functions: %s%s%s" % (
                    len(real), "; ".join("%s %s at %s" % (r[2], h(r[0]), h(r[1])) for r in real[:4]), " ..." if len(real) > 4 else "", tail))
            else:
                ck["operands"] = (PASS, "no branch target or absolute operand in a function points here" + tail)

        # 5 written at run time
        wr = [w for w in m.writes if w.lo < a.hi and w.hi > a.lo and not (L and w.name == "load " + L.name)]
        vec = [(c, v) for c, vs, _ in m.vectors for v in vs if a.lo <= v < a.hi]
        if wr:
            ck["written"] = (FAIL, "overlaps %s %s (site %s)" % (wr[0].name, rng(wr[0].lo, wr[0].hi), h(wr[0].site)))
        elif vec:
            ck["written"] = (FAIL, "holds the %s vector entry %s" % (vec[0][0], h(vec[0][1])))
        elif L is None:
            ck["written"] = (UNKNOWN, "not in a block-0 load; this address range is RAM whose owner the tool does not know")
        else:
            ck["written"] = (PASS, "outside all %d known constant-destination write ranges (task stacks, start stacks, "
                                   "clears, copies, kernel config pairs, vector save words) and both vector tables" % len(m.writes))

        # 6 predecessor and bounds
        ck["predecessor"] = self._predecessor(a)

        # ledger
        a.ledger_rows, a.used, a.used_hist, a.free_runs = self.ledger(a)
        a.used_bytes = sum(hi - lo for lo, hi in a.used)
        a.free_bytes = sum(hi - lo for lo, hi in a.free_runs)
        a.code = self.code_evidence(a)
        a.allowed = "code" if a.code else "data"

        # verdict
        st = {k: v[0] for k, v in ck.items()}
        rej = [k for k in ("loaded", "content", "written") if st[k] == FAIL]
        dec = [k for k in ("loaded", "content", "pointers", "operands", "written", "predecessor") if st[k] != PASS and k not in rej]
        if rej:
            a.verdict, a.failing = "REJECT", rej
        elif dec:
            a.verdict, a.failing = "NEEDS-DECISION", dec
        elif a.free_bytes == 0:
            a.verdict = "USED"
        else:
            a.verdict = "USABLE-CODE" if a.code else "USABLE-DATA"
        return a

    def _predecessor(self, a):
        m, b = self.m, self.b
        before, after = self.nearest_refs(a)
        a.ref_before, a.ref_after = before, after

        def refs(r):
            if not r:
                return "none found in the same 64 KiB page"
            return "%s (from %s%s)" % (h(r[0]), ", ".join(h(s) for s in r[1][:3]), " ..." if len(r[1]) > 3 else "")
        info = "; nearest referenced address before: %s; after: %s" % (refs(before), refs(after))
        prev = self.area_at(a.lo - 1)
        if prev is not None and prev.kind == "ff" and a.kind == "ff":
            rd = [r for r in m.reads if r.hi == a.lo]
            if rd:
                return PASS, "follows the end of the %s source (end constant at site %s)%s" % (rd[0].name, h(rd[0].site), info)
            return PASS, "continues the 0xFF run of %s%s" % (rng(prev.lo, prev.hi), info)
        tailb = b[max(0, a.lo - BASE - 8):a.lo - BASE]
        if self.lin:
            ins, fn = self.lin.code_run_to(a.lo - 1)
            if ins and ins[1] == a.lo and ins[2] in INS_TERMINAL:
                selfbr = ins[2] == "bra" and ("0x%x" % ins[0]) in ins[3]
                return PASS, "code ends just before: `%s %s` at %s%s (decoded without a gap from the function start %s); " \
                             "execution cannot fall in%s" % (ins[2], ins[3], h(ins[0]), " (branch to itself)" if selfbr else "", h(fn), info)
        elif tailb[-3:-2] in (b"\xde", b"\xdf") or tailb[-2:] in (b"\xf0\xfc", b"\xf0\xfd", b"\xca\x00"):
            return UNKNOWN, "bytes before look like a return (%s) but no decode is available%s" % (tailb.hex(), info)
        # data before the area: a reader's bound must be proven
        if before:
            for o, bd, s, ev in self.bounds:
                if o <= before[0] < bd <= a.lo:
                    return PASS, "data before (%s); bound of the object at %s proven by hand entry: reader %s stops at %s (%s)%s" % (
                        tailb.hex(), h(o), h(s), h(bd), ev, info)
            s = a.lo - BASE - 1
            if b[s] == 0:
                while s > 0 and (0x20 <= b[s - 1] < 0x7F or b[s - 1] in (9, 10, 13)):
                    s -= 1
                if BASE + s == before[0] and a.lo - BASE - 1 - s >= 2:
                    return PASS, "data before is the NUL-terminated string at %s, which is the nearest referenced address " \
                                 "(a C-string reader stops at the NUL; assumption)%s" % (h(before[0]), info)
        return UNKNOWN, "data before (%s); bound not proven: nothing shows where the reader of the object before stops%s" % (tailb.hex(), info)

    def analyse_all(self):
        refs = self.lin.operand_refs([(a.lo, a.hi) for a in self.areas if a.region is not None]) if self.lin else None
        for a in self.areas:
            self.analyse(a, refs)
        return self.areas


def merge(segs):
    out = []
    for lo, hi in sorted(segs):
        if out and lo <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], hi))
        else:
            out.append((lo, hi))
    return out


# ----------------------------------------------------------------------------- check

def check_specs(sp, specs, out=print):
    """Verify the bytes that specs add in free areas. Returns the number of FAIL lines."""
    img = bytearray(sp.b)
    owner = []                                   # (lo, hi, spec) changed by the specs applied so far
    given = {s.path for s in specs}
    targets = [t for s in specs for _, t in s.rel_targets()]
    fails = 0
    for s in specs:
        n_add = 0
        for o in s.ops:
            cur = bytes(img[o.off:o.off + len(o.expect)])
            where = "%s op %d at %s" % (s.path, o.idx, h(BASE + o.off))
            if cur != o.expect:
                fails += 1
                out("FAIL  %s: expect bytes do not match the image after the earlier specs "
                    "(the bytes are not free or the spec order is wrong)" % where)
                continue
            img[o.off:o.off + len(o.new)] = o.new
            if o.clo is None:
                continue
            prior = [(max(lo, o.clo), min(hi, o.chi), w) for lo, hi, w in owner if lo < o.chi and hi > o.clo]
            owner.append((o.clo, o.chi, s))
            p = o.clo
            while p < o.chi:
                a = sp.area_at(p)
                if a is None:
                    nxt = bisect.bisect_right(sp._los, p)
                    p = min(o.chi, sp.areas[nxt].lo) if nxt < len(sp.areas) else o.chi
                    continue
                lo, hi = p, min(o.chi, a.hi)
                p = hi
                n_add += 1
                sp.analyse(a)
                seg = "%s: %d B %s in area %s (%s)" % (where, hi - lo, rng(lo, hi), rng(a.lo, a.hi), a.region_name())
                ov = [(x, y, w) for x, y, w in prior if x < hi and y > lo]
                stacked = sp.b[lo - BASE:hi - BASE] != cur[lo - BASE - o.off:hi - BASE - o.off]
                kind = "code" if any(lo <= t < hi for t in targets) else "data"
                verdict = a.verdict if a.verdict != "USED" else ("USABLE-CODE" if a.code else "USABLE-DATA")
                problems = []
                if verdict not in ("USABLE-DATA", "USABLE-CODE"):
                    problems.append("area verdict %s (%s)" % (verdict, ", ".join(
                        "%s: %s" % (k, a.checks[k][1]) for k in a.failing)))
                elif kind == "code" and verdict != "USABLE-CODE":
                    problems.append("a relative jump or call of the given specs targets these bytes, but the area allows data only")
                for path, cls, segs in a.ledger_rows:
                    if path in given or not any(x < hi and y > lo for x, y in segs):
                        continue
                    if cls == "current":
                        problems.append("overlaps ledgered spec %s" % path)
                notes = []
                if ov and stacked:
                    notes.append("edits bytes of %s in place (expect matches its output)" % ", ".join(sorted({w.path for _, _, w in ov})))
                old = sorted({path for path, cls, segs in a.ledger_rows if cls != "current" and path not in given
                              and any(x < hi and y > lo for x, y in segs)})
                if old:
                    notes.append("%d history/superseded spec(s) used these bytes" % len(old))
                note = (" [" + "; ".join(notes) + "]") if notes else ""
                if problems:
                    fails += 1
                    out("FAIL  %s, as %s: %s%s" % (seg, kind, "; ".join(problems), note))
                else:
                    out("PASS  %s, as %s, verdict %s%s" % (seg, kind, verdict, note))
        if not n_add:
            out("PASS  %s: no byte added in a free area (%d block-0 byte ops, all edits of existing content; %d other ops)"
                % (s.path, len(s.ops), s.other))
    return fails


# ----------------------------------------------------------------------------- map output

CHECKS = ["loaded", "content", "pointers", "operands", "written", "predecessor"]


def write_map(sp):
    m = sp.m
    areas = sp.analyse_all()
    md = []
    w = md.append
    w("# Code and data space map: E-PM2 v1.6 block 0")
    w("")
    w("Generated by `python3 tools/freespace.py map`. Do not edit; edit the hand files and run it again.")
    w("")
    w("- Stock block 0 sha256 `%s`, runtime address = %s + file offset." % (STOCK_BLOCK0_SHA256, h(BASE)))
    w("- **Limit of every check here:** this is a static scan of constants in the firmware. A pointer or a write "
      "address that the firmware computes at run time (base + index, heap, memory test) is invisible to it. "
      "A PASS means \"no constant found\", not \"proven unused\".")
    w("- **Before a build:** run `python3 tools/freespace.py check SPEC [SPEC ...]` with the same specs, in the same "
      "order, that go to `tools/build.py`. It exits non-zero if a spec adds bytes in an area that is not usable, or in "
      "bytes that another current spec claims. `tools/build.py` does not call it.")
    w("- **Sources.** *Derived*: read from the block-0 bytes at a checked site (the tool stops if a site's bytes differ). "
      "*Hand*: `%s` (reclaimed areas), `%s` (proven table bounds), `%s` (explained pointer windows), `%s`. "
      "*Optional decode*: `%s`, `%s` (%s)." % (CANDIDATES, BOUNDS, WAIVERS, SUPERSEDED, LINEAR, FUNCTIONS,
                                              "present" if sp.lin else "ABSENT: checks that need a decode are UNKNOWN"))
    w("")
    w("## 1. Load map (derived)")
    w("")
    w("| Runtime range | Size | Name | Copy site | Flash source | Destination | When | Evidence that the copy always runs |")
    w("|---|---|---|---|---|---|---|---|")
    w("| %s | %d | pre-reset | - | - | - | before reset | %s |" % (rng(m.pre.lo, m.pre.hi), m.pre.hi - m.pre.lo, m.pre.note))
    for L in sorted(m.loads, key=lambda x: x.order):
        if L.cond:
            ev = "on demand (%s)" % L.who
        elif sp.lin:
            ev = sp.lin.cannot_skip(m.entries[L.phase], L.site)[1]
        else:
            ev = "not checked (no decode)"
        w("| %s | %d | %s | %s | %s | %s | %d: %s | %s |" % (rng(L.lo, L.hi), L.hi - L.lo, L.name, h(L.site), h(L.src), h(L.dst), L.order, L.who, ev))
    w("")
    w("Hand notes on the order (not checked by the tool): Usr0 (in the boot task) starts Usr1 on a normal boot only. On the "
      "firmware-update reboot path Usr1 does not run, so segment-2, segment-3 and usr1-third are not loaded there (and none of "
      "their code runs). Data that segment-1 or kernel code must read belongs in the kernel or segment-1 range "
      "(`experiments/2026-11-13-intervalometer/trace-frames-list-location.md` section 1.3).")
    w("")
    w("Address aliases used by the pointer scan (all four are scanned for every area):")
    w("")
    w("| Alias | Rule | Basis |")
    w("|---|---|---|")
    w("| runtime | %s + file offset | every copy destination and source above agrees |" % h(BASE))
    w("| uncached | runtime + 0x40000000 | helper 0x7E45DAEF (bytes checked): `(a & 0x3FFFFFFF) \\| 0x40000000` for 0x8.., 0xA.., 0xB.. |")
    w("| flash | %s + file offset | %s; each of the %d copies has source = this rule (checked) |" % (h(FLASH0), m.flash_base_src, len(m.loads)))
    w("| flash, uncached | flash + 0x40000000 | the Usr1 and Usr2 copies use it |")
    w("")
    w("Bytes of block 0 that code copies elsewhere (derived). A 0xFF run inside one of these is data, not free space:")
    w("")
    w("| Source range | What | Site |")
    w("|---|---|---|")
    for r in m.reads:
        w("| %s | %s, %s | %s |" % (rng(r.lo, r.hi), r.name, r.note, h(r.site)))
    w("")
    w("## 2. Known run-time write ranges")
    w("")
    w("An area fails the `written` check if it overlaps one of these (cached addresses). Block 0's runtime span is %s." % rng(BASE, m.end))
    w("")
    w("| Range | What | Site | Basis |")
    w("|---|---|---|---|")
    for x in m.writes:
        if not x.name.startswith("task "):
            w("| %s | %s | %s | %s |" % (rng(x.lo, x.hi), x.name, h(x.site), x.basis))
    for cpu, t, rows in m.tasks:
        st = [r for r in rows if r[6]]
        dyn = [r for r in rows if not r[6]]
        w("| %s | CPU%d task table at %s: %d static stacks `[stk, stk+stksz)` | %s | derived |" % (
            rng(min(r[6] for r in st), max(r[6] + r[5] for r in st)), cpu, h(t), len(st), h(t)))
        w("| (not known) | CPU%d: %d tasks with `stk` = 0 (total stksz %d B). Their stacks come from the kernel at run time; "
          "the kernel-config pool above is the likely place (inferred) | %s | derived count |" % (cpu, len(dyn), sum(r[5] for r in dyn), h(t)))
    inside = [x for x in m.writes if x.lo < m.end and x.hi > BASE and not x.name.startswith("load ")]
    w("")
    w("Vector entry stubs (addresses that the start code loads into the vector registers 0x8000-0x8018; derived): "
      + "; ".join("%s %s-%s (site %s)" % (c, h(min(v)), h(max(v)), h(s)) for c, v, s in m.vectors) + ".")
    w("")
    w("Per-CPU kernel pointer (derived): the kernel start stores the address of its configuration table in the slot "
      + "; ".join("%s for CPU%d = %s (site %s)" % (h(slot + 4 * c), c, h(root), h(site)) for c, slot, root, site in m.percpu)
      + ". Both tables are constant data in the kernel copy; every RAM address in them is 0x60.. / 0xA0.. / 0x47.. "
        "(the pointer scan covers their words). That the kernel does not write through them into 0x7E.. is inferred.")
    w("")
    w("Write ranges, other than loads, that overlap block 0's runtime span: %s." % (
        "; ".join("%s %s" % (x.name, rng(x.lo, x.hi)) for x in inside) or "none"))
    w("")
    w("## 3. Verdicts")
    w("")
    w("| Verdict | Meaning |")
    w("|---|---|")
    w("| USABLE-DATA | every check is PASS; free bytes may hold tables |")
    w("| USABLE-CODE | as USABLE-DATA, and a camera-tested spec already runs code in this area (a relative jump from outside into its bytes; `%s`) |" % CAMERA_LOG)
    w("| USED | every check is PASS, no free byte left (current specs) |")
    w("| NEEDS-DECISION | a check is UNKNOWN, or `pointers`, `operands` or `predecessor` did not pass; a person must decide or add evidence |")
    w("| REJECT | `loaded`, `content` or `written` failed |")
    w("")
    w("Checks: **loaded** (inside a boot copy), **content** (all 0xFF, or listed as reclaimed), **pointers** (no 4-byte value at any "
      "byte offset of block 0 equals an address in the area, in any of the 4 aliases), **operands** (no branch target or absolute "
      "operand that objdump prints inside a function), **written** (section 2), **predecessor** (what ends before the area, and "
      "whether the reader of the object before it is known to stop).")
    w("")
    w("Windows in blocks 1-3 and the tail of the update file are counted per area in `%s` (column `pointers_evidence`) but do "
      "not change a verdict: those blocks are resources, the tool has no decode for them, and it cannot classify a window there." % MAP_TSV)
    w("")
    w("Pointer windows that are explained and do not count as hits: `code-nonoperand` (not 4-aligned, inside a function, and not "
      "the operand of the decoded instruction: depends on the decode), `straddle` (not 4-aligned in data, and the window runs "
      "into a 4-aligned word that is itself a block-0 address), `double` (the 8 bytes are a short decimal constant), `double-table` (the window lies in three consecutive 8-byte cells that are all doubles: exponent between 2^-47 and 2^49, 5 to 27 bits set in the low word, low word not a block-0 address), "
      "`from-listed` (the site is inside a listed reclaimed area), `end-constant` (the exclusive end of a known copy source, at its site), `waived` (hand file). Everything else is a hit.")
    w("")

    tot = {}
    byreg = {}
    for a in areas:
        byreg.setdefault(a.region_name(), []).append(a)
    order = ["pre-reset"] + [L.name for L in sorted(m.loads, key=lambda x: x.lo)] + ["not loaded"]
    n = 0
    for reg in order:
        rows = byreg.get(reg, [])
        if not rows:
            continue
        n += 1
        L = next((x for x in m.loads if x.name == reg), None)
        w("### 3.%d %s%s" % (n, reg, " (%s)" % rng(L.lo, L.hi) if L else ""))
        w("")
        if reg == "not loaded":
            w("0xFF runs outside every boot copy. All REJECT: the bytes exist in flash only. The address range is RAM at run time.")
            w("")
            w("| Range | Size | Verdict |")
            w("|---|---|---|")
            for a in rows:
                w("| %s | %d | REJECT (loaded) |" % (rng(a.lo, a.hi), a.size))
            w("")
            tot[reg] = {"REJECT": sum(a.size for a in rows)}
            continue
        w("| Range | Size | Source | Verdict | Use | Used | Free | L | C | P | O | W | B | Failing check: evidence |")
        w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        t = tot.setdefault(reg, {})
        for a in rows:
            c = a.checks
            sym = lambda k: {PASS: "ok", FAIL: "FAIL", UNKNOWN: "?"}[c[k][0]]
            why = "; ".join("**%s**: %s" % (k, c[k][1]) for k in a.failing) or "-"
            if a.code:
                why = (why + "; " if why != "-" else "") + "code evidence: " + a.code[0]
            w("| %s | %d | %s | %s | %s | %d | %d | %s | %s |" % (
                rng(a.lo, a.hi), a.size, a.source if a.kind == "ff" else "%s (%s, %s)" % (a.source, a.kind, a.status),
                a.verdict, a.allowed, a.used_bytes, a.free_bytes, " | ".join(sym(k) for k in CHECKS), why.replace("|", "\\|")))
            if a.verdict in ("USABLE-DATA", "USABLE-CODE", "USED"):
                t["USED"] = t.get("USED", 0) + a.used_bytes
                if a.free_bytes:
                    t[a.verdict] = t.get(a.verdict, 0) + a.free_bytes
            else:
                t[a.verdict] = t.get(a.verdict, 0) + a.size
        w("")
        led = [a for a in rows if a.ledger_rows]
        if led:
            w("Ledger (bytes that specs change inside an area; `history` and `superseded` do not reduce the free count):")
            w("")
            for a in led:
                w("- %s: free %s" % (rng(a.lo, a.hi), ", ".join("%s (%d)" % (rng(x, y), y - x) for x, y in a.free_runs) or "none"))
                for path, cls, segs in a.ledger_rows:
                    w("  - `%s` (%s): %d B in %s" % (path, cls, sum(y - x for x, y in segs), ", ".join(rng(x, y) for x, y in segs)))
            w("")
    w("## 4. Totals (bytes)")
    w("")
    w("USABLE columns count free bytes only. USED counts bytes of current specs in areas that pass every check.")
    w("")
    cols = ["USABLE-DATA", "USABLE-CODE", "USED", "NEEDS-DECISION", "REJECT"]
    w("| Region | " + " | ".join(cols) + " |")
    w("|---|" + "---|" * len(cols))
    for reg in order:
        if reg in tot:
            w("| %s | %s |" % (reg, " | ".join(str(tot[reg].get(c, 0)) for c in cols)))
    w("| **all** | %s |" % " | ".join(str(sum(t.get(c, 0) for t in tot.values())) for c in cols))
    w("")
    w("## 5. Hand files")
    w("")
    w("| File | Rows | Columns |")
    w("|---|---|---|")
    w("| `%s` | %d | start, end (exclusive), kind, status (`checked` or `auto`), source, note |" % (CANDIDATES, len(sp.listed)))
    w("| `%s` | %d | object, bound (exclusive), reader site, expected bytes at the site, evidence |" % (BOUNDS, len(sp.bounds)))
    w("| `%s` | %d | first site, end (exclusive), expected bytes at the first site, evidence |" % (WAIVERS, len(sp.waivers)))
    w("| `%s` | %d | spec, superseded by, evidence |" % (SUPERSEDED, len(sp.superseded)))
    w("")
    w("The full evidence text of every check is in `%s`." % MAP_TSV)
    open(rel(MAP_MD), "w", encoding="utf-8").write("\n".join(md) + "\n")

    with open(rel(MAP_TSV), "w", encoding="utf-8") as fh:
        fh.write("\t".join(["start", "end", "size", "region", "source", "kind", "verdict", "failing", "allowed_use",
                            "used_bytes", "free_bytes", "free_runs", "history_bytes"]
                           + [x for k in CHECKS for x in (k, k + "_evidence")] + ["code_evidence", "ledger", "note"]) + "\n")
        for a in areas:
            fh.write("\t".join(str(x).replace("\t", " ") for x in [
                h(a.lo), h(a.hi), a.size, a.region_name(), a.source, a.kind, a.verdict, ",".join(a.failing), a.allowed,
                a.used_bytes, a.free_bytes, " ".join(rng(x, y) for x, y in a.free_runs), sum(y - x for x, y in a.used_hist)]
                + [x for k in CHECKS for x in a.checks[k]]
                + [" / ".join(a.code), " / ".join("%s[%s]=%d" % (p, c, sum(y - x for x, y in s)) for p, c, s in a.ledger_rows), a.note]) + "\n")
    return tot


# ----------------------------------------------------------------------------- self-test

def selftest():
    sp = Space()
    ok = True

    def t(name, cond, extra=""):
        nonlocal ok
        ok = ok and bool(cond)
        print("%s  %s%s" % ("ok  " if cond else "FAIL", name, (" -- " + extra) if extra and not cond else ""))

    a = sp.analyse(sp.area_at(0x7E4C9100))
    t("240-frame list area 0x7E4C9100-0x7E4C917F is inside one area", a.lo <= 0x7E4C9100 and a.hi >= 0x7E4C9180)
    t("  it is loaded (reset copy)", a.checks["loaded"][0] == PASS and a.region.name == "kernel", a.checks["loaded"][1])
    t("  it is blank in stock", a.checks["content"][0] == PASS and sp.b[0x7E4C9100 - BASE:0x7E4C9180 - BASE] == b"\xff" * 128)
    t("  it has no pointer", a.checks["pointers"][0] == PASS and not [x for x in a.hits if 0x7E4C9100 <= x[1] < 0x7E4C9180], a.checks["pointers"][1])
    s3 = sp.analyse(sp.area_at(0x7F033B7C))
    t("segment-3 tail is used by seven-films-5", any(p == "patches/seven-films-5.json" and c == "current" and sum(y - x for x, y in s) == 1024
                                                      for p, c, s in s3.ledger_rows), str(s3.ledger_rows))
    quiet = lambda *x: None
    base = {"base": STOCK_FW}
    fake = Spec("selftest/overlap.json", dict(base, name="fake-overlap", ops=[
        {"type": "bytes", "block": 0, "offset": hex(0x7F033C00 - BASE), "expect": "ff" * 16, "new": "00" * 16}]))
    t("a fake spec that overlaps seven-films-5 FAILs (alone: ledger overlap)", check_specs(sp, [fake], quiet) == 1)
    lines = []
    films = [s for s in sp.specs if s.path == "patches/history/four-neutral.json"]      # applies on stock; writes the same tail
    t("the same fake spec FAILs after a spec that wrote those bytes (expect mismatch)",
      len(films) == 1 and check_specs(sp, films + [fake], lines.append) >= 1
      and any(x.startswith("FAIL") and "selftest/overlap.json" in x and "expect bytes" in x for x in lines), "\n".join(lines))
    fake2 = Spec("selftest/unloaded.json", dict(base, name="fake-unloaded", ops=[
        {"type": "bytes", "block": 0, "offset": hex(0x7E881100 - BASE), "expect": "ff" * 8, "new": "11" * 8}]))
    u = sp.analyse(sp.area_at(0x7E881100))
    t("0x7E881100 is 0xFF but not loaded (REJECT)", u.verdict == "REJECT" and u.failing == ["loaded"])
    t("a fake spec that writes there FAILs", check_specs(sp, [fake2], quiet) == 1)
    fake3 = Spec("selftest/free.json", dict(base, name="fake-free", ops=[
        {"type": "bytes", "block": 0, "offset": hex(0x7E4C9200 - BASE), "expect": "ff" * 8, "new": "11" * 8}]))
    t("a fake spec in free loaded padding passes when its area is usable",
      (check_specs(sp, [fake3], quiet) == 0) == (a.verdict in ("USABLE-DATA", "USABLE-CODE", "USED")))
    bad = dict(SITES)
    try:
        match_site(sp.b, "selftest", bad["boot_load_seg1"][0] + 1, bad["boot_load_seg1"][1])
        t("a site with different bytes stops the tool", False)
    except SiteError:
        t("a site with different bytes stops the tool", True)
    print("selftest: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


# ----------------------------------------------------------------------------- CLI

def show_area(sp, a):
    sp.analyse(a)
    print("%s  %d B  %s  %s  verdict %s%s" % (rng(a.lo, a.hi), a.size, a.region_name(), a.source, a.verdict,
                                              (" (" + ", ".join(a.failing) + ")") if a.failing else ""))
    for k in CHECKS:
        print("  %-11s %-7s %s" % (k, a.checks[k][0], a.checks[k][1]))
    print("  allowed use %s%s" % (a.allowed, "".join("\n    " + c for c in a.code)))
    print("  used %d B, free %d B: %s" % (a.used_bytes, a.free_bytes, ", ".join(rng(x, y) for x, y in a.free_runs) or "-"))
    for p, c, s in a.ledger_rows:
        print("    %s (%s): %s" % (p, c, ", ".join(rng(x, y) for x, y in s)))
    for wv in a.hits:
        print("  hit %s at %s via %s: %s" % (h(wv[1]), h(wv[2]), wv[0], wv[4]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min-run", type=int, default=32, help="shortest 0xFF run that is a candidate (default 32)")
    ap.add_argument("--no-decode", action="store_true", help="do not use build/map (decode-dependent checks become UNKNOWN)")
    ap.add_argument("--no-other-blocks", action="store_true", help="map: do not count windows in blocks 1-3 and the tail")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("map")
    c = sub.add_parser("check")
    c.add_argument("specs", nargs="+")
    c = sub.add_parser("area")
    c.add_argument("addr")
    sub.add_parser("selftest")
    a = ap.parse_args()
    if a.cmd == "selftest":
        return selftest()
    sp = Space(a.min_run, not a.no_decode, other_blocks=(a.cmd == "map" and not a.no_other_blocks))
    if a.cmd == "map":
        tot = write_map(sp)
        print("wrote %s and %s (%d areas)" % (MAP_MD, MAP_TSV, len(sp.areas)))
        for reg, t in tot.items():
            print("  %-12s %s" % (reg, "  ".join("%s %d" % kv for kv in sorted(t.items()))))
        return 0
    if a.cmd == "area":
        ar = sp.area_at(int(a.addr, 0))
        if ar is None:
            print("%s is not in a candidate area" % a.addr)
            return 1
        show_area(sp, ar)
        return 0
    specs = []
    for p in a.specs:
        ap_ = os.path.abspath(p)
        specs.append(Spec(os.path.relpath(ap_, ROOT)))
    fails = check_specs(sp, specs)
    print("check: %s (%d FAIL)" % ("FAIL" if fails else "PASS", fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
