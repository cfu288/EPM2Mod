"""Scenario runs: a top-level firmware routine with its real callees, stock against patched.

A scenario calls a routine and lets it call down through the firmware's own code. Only what the emulator cannot
give is replaced: hardware registers, uITRON services, and whatever else the scenario names. Between calls the
RAM is kept, so a sequence of calls ("frames") sees the state that the calls before it left.

    from scenario import Scenario
    sc = Scenario("/tmp/scratch/pinned.block0.bin")        # boot copies applied (bootmem.py)
    sc.settings[(38017, 0)] = 2                             # a value for the settings getter 0x7E457C75
    sc.stub(0x7E6D144F, name="error print")                 # returns at once; every call is logged
    sc.stub(0x7E44B36F, lambda sc, g: {"d0": 0}, "loc_cpu")
    r = sc.call(0x7E6C6853, frame=(0xF0, 16), label="frame 1", log_writes=RAM)
    r.fault            # None, or text with the fault pc, the reason and a backtrace
    r.pcs              # every executed pc of this call
    r.writes           # [(addr, size, value, pc)] of the logged write watch
    r.stubs            # [(addr, name, args, ret)]
    r.mmio             # [(dir, addr, value, size, pc)] of device accesses

Parts:
  boot memory   Scenario(bootmem=True) gives RAM its `.data` values (emulator/bootmem.py).
  stubs         a breakpoint at a function entry. The handler gets the registers and returns the registers to set;
                the CPU then returns through the return form of the call that reached the stub (retf for `call`,
                rets for `calls`). stub(addr) with no handler returns d0 = 0.
  settings      the settings getter 0x7E457C75 (d0 = id, d1 = index) answers from sc.settings; an id that the
                scenario did not set is answered with sc.settings_default and listed in sc.settings_missing.
  MMIO          om-emu faults on a read of a device page it does not model. on_mmio_read(sc, addr, size, pc)
                may return the value; the faulting load is then done by the harness (see _mmio_fix for the
                instruction forms it knows). Without a handler the fault ends the call and is reported.
  watches       log_writes=[(lo, hi)...] logs every CPU write in the ranges (om-emu watchpoints, action log);
                stop_writes=[(lo, hi)...] stops the call at the first write and reports pc and backtrace.
  traces        r.pcs is the set of executed pcs. diff_pcs(a, b, ...) prints which pcs ran only in one image.
  faults        a fault, the instruction limit or a stop watch ends the call; r.fault holds the reason and a
                backtrace (return addresses found on the stack: a word is listed when the instruction before it
                is a call; plus MDR, the last return address).
"""
import bisect, json, os, re, struct, sys, tempfile
import omemu, bootmem
from omemu import Emu, EmuError, BASE, TRAMP, PADS, SP0

SETTINGS_GETTER = 0x7E457C75
RAM = [(0x40000000, 0x7D000000), (0x7D200000, 0x7E421020), (0x80000000, 0xBD000000), (0xBD200000, 0x100000000)]
"""Write-watch ranges for "all memory but the harness scratch (trampoline, pads, stack) and block 0 itself"."""
RAM_AND_IMAGE = [(0x40000000, 0x7D000000), (0x7D200000, 0x100000000)]
sys.path.insert(0, os.path.join(omemu.ROOT, "tools"))
import toolchain  # noqa: E402

os.environ["OM_OBJDUMP"] = toolchain.binutils("objdump")  # om-emu's name for it: always the project's objdump   # for the disasm op
MAP_DIR = os.path.join(omemu.ROOT, "build", "map")


BLOCK = object()
"""A stub handler returns BLOCK when the service would make the task wait. The run ends there (Result.blocked)."""
CONTINUE = object()
"""A probe handler returns CONTINUE: the instruction at the breakpoint then runs as stock code (Scenario.probe)."""


class Task:
    def __init__(self, name, entry, frame, sp_top, stack_size):
        self.name, self.entry, self.frame, self.sp_top, self.stack_size = name, entry, frame, sp_top, stack_size
        self.regs, self.stack_args = {}, ()
        self.started = self.done = False
        self.blocked = None


class Result:
    def __init__(self):
        self.label = ""
        self.regs = {}
        self.fault = None
        self.backtrace = []
        self.pcs = set()
        self.writes = []
        self.stubs = []
        self.mmio = []
        self.insns = 0
        self.stderr = []
        self.blocked = None
        self.stack_used = 0
        self.notes = []
        self.div0 = []
        self.calls = []

    @property
    def d0(self):
        return self.regs.get("d0")

    def stub_calls(self, addr):
        return [s for s in self.stubs if s[0] == addr]

    def summary(self):
        return "%s: %s, %d insns, %d pcs, %d stub calls, %d writes, %d mmio" % (
            self.label, "FAULT " + self.fault if self.fault else ("blocked in %s" % self.blocked[1] if self.blocked else
                                                                  "returned d0=0x%X" % self.regs.get("d0", 0)),
            self.insns, len(self.pcs), len(self.stubs), len(self.writes), len(self.mmio))


class Functions:
    """Function starts of build/map/functions.tsv (optional; used for names in backtraces and pc summaries)."""

    def __init__(self):
        self.starts = []
        p = os.path.join(MAP_DIR, "functions.tsv")
        if os.path.exists(p):
            with open(p) as f:
                next(f)
                self.starts = sorted(int(l.split("\t", 1)[0], 16) for l in f)

    def of(self, pc):
        i = bisect.bisect_right(self.starts, pc) - 1
        return self.starts[i] if i >= 0 else None

    def name(self, pc):
        f = self.of(pc)
        return "0x%08X" % pc if f is None else "0x%08X (0x%08X+0x%X)" % (pc, f, pc - f)


FUNCS = None


def funcs():
    global FUNCS
    if FUNCS is None:
        FUNCS = Functions()
    return FUNCS


class Scenario:
    def __init__(self, image, name=None, boot=True, insn_limit=3_000_000, clear_unloaded=True):
        self.name = name or os.path.basename(image)
        self.emu = Emu(insn_limit=0)
        self.emu.load(image)
        self.image = self.emu.image
        self.insn_limit = insn_limit
        self.boot_report = bootmem.apply(self.emu, clear_unloaded=clear_unloaded) if boot else []
        self._stubs = {}
        self.settings = {}
        self.settings_default = 0
        self.settings_missing = {}
        self.settings_log = []
        self.mmio = "skip"                              # "skip": do refused device accesses in the harness; "fault"
        self.on_mmio_read = None
        self.on_device_write = None                     # fn(sc, addr, value, size, pc), called at each dropped write
        self.mmio_values = {}
        self.mmio_default = 0
        self.div0 = "skip"                              # "skip": go on after a division by zero as the MN103 does
        self.results = []
        self._pads = {}
        self._ntasks = 0
        self.current = None
        self.stub(SETTINGS_GETTER, self._settings_stub, "settings getter")

    def close(self):
        self.emu.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    # --- memory helpers
    def w8(self, a, v):
        self.emu.write(a, bytes([v & 0xFF]))

    def w16(self, a, v):
        self.emu.write(a, struct.pack("<H", v & 0xFFFF))

    def w32(self, a, v):
        self.emu.write(a, struct.pack("<I", v & 0xFFFFFFFF))

    def r8(self, a):
        return self.emu.read(a, 1)[0]

    def r16(self, a):
        return struct.unpack("<H", self.emu.read(a, 2))[0]

    def r32(self, a):
        return self.emu.u32(a)

    def read(self, a, n):
        return self.emu.read(a, n)

    def write(self, a, data):
        for i in range(0, len(data), 0x8000):
            self.emu.write(a + i, data[i:i + 0x8000])

    # --- stubs
    def stub(self, addr, fn=None, name=None):
        """Replace the function at addr. fn(sc, regs) -> dict of registers to set (None: d0 = 0)."""
        self._stubs[addr] = (fn, name or "0x%08X" % addr)

    def probe(self, addr, fn, name=None):
        """Call fn(sc, regs) each time the CPU reaches addr, then run the code there as stock. Use it to read
        registers or memory at a point of the real path (any instruction address, not only function entries)."""
        def handler(sc, g):
            fn(sc, g)
            return CONTINUE
        self._stubs[addr] = (handler, name or "probe 0x%08X" % addr)

    def stub_module(self, lo, hi, name, fn=None):
        """Stub every function in [lo, hi) that code outside the range calls (from build/map/calls.tsv).
        Use it for a whole module that the scenario does not test (for example the white-balance module).
        Returns the list of entries."""
        entries = set()
        with open(os.path.join(MAP_DIR, "calls.tsv")) as f:
            next(f)
            for line in f:
                c, _, t = line.split("\t")
                t, c = int(t, 16), int(c, 16)
                if lo <= t < hi and not lo <= c < hi:
                    entries.add(t)
        for e in sorted(entries):
            self.stub(e, fn, "%s 0x%08X" % (name, e))
        return sorted(entries)

    def unstub(self, addr):
        self._stubs.pop(addr, None)

    def stack_arg(self, rg, k):
        """Stack argument k (0 = the first) of the call that reached the stub whose registers are rg."""
        key = self._return_form(rg["pc"], rg)
        return self.emu.u32(rg["sp"] + (0 if key == "rets" else key[1]) + 4 + 4 * k)

    def _settings_stub(self, sc, g):
        key = (g["d0"] & 0xFFFF, g["d1"] & 0xFFFF)
        if key in self.settings:
            v = self.settings[key]
        elif (key[0], None) in self.settings:
            v = self.settings[(key[0], None)]
        else:
            v = self.settings_default
            self.settings_missing[key] = self.settings_missing.get(key, 0) + 1
        v = v(key) if callable(v) else v
        self.settings_log.append((key, v, g["mdr"]))
        return {"d0": v}

    def frame_at(self, site):
        """(regs byte, imm) of the call instruction at site (a stock call site of the function you want to call)."""
        c = self.emu.read(site, 7)
        if c[0] == 0xDD:
            return (c[5], c[6])
        if c[0] == 0xCD:
            return (c[3], c[4])
        raise EmuError("0x%08X is not a call instruction (%s)" % (site, c.hex()))

    def call_site(self, site, **kw):
        """Call the function that the call instruction at site calls, with that instruction's frame."""
        c = self.emu.read(site, 7)
        rel = struct.unpack_from("<i", c, 1)[0] if c[0] == 0xDD else struct.unpack_from("<h", c, 1)[0]
        return self.call((site + rel) & 0xFFFFFFFF, frame=self.frame_at(site), **kw)

    # --- calls and tasks
    def call(self, entry, regs=None, stack=(), frame=None, label=None, **kw):
        """Call the function at entry on the harness stack and run until it returns (or a fault, a limit, a stop watch,
        or a stub that blocks). frame: (regs byte, imm) of the call instruction; default: read from a call site."""
        t = Task("call", entry, frame, SP0, 0)
        t.regs = dict(regs or {})
        t.stack_args = stack
        return self.run(t, label=label or "0x%08X" % entry, **kw)

    def piece(self, start, stops, regs=None, label=None, **kw):
        """Run from the instruction at start until the CPU reaches one of the addresses in stops (a code piece,
        not a call: no frame is made). Result.regs holds the registers at the stop; Result.fault is set when the
        piece ends anywhere else."""
        t = Task("piece", start, None, SP0 - 0x400, 0)
        t.started = True
        t.regs = {"pc": start, "sp": t.sp_top, "mdr": 0, "psw": 0, "d0": 0, "d1": 0, "d2": 0, "d3": 0, "a0": 0, "a1": 0,
                  "a2": 0, "a3": 0, "lir": 0, "lar": 0}
        t.regs.update(regs or {})
        added = [a for a in stops if a not in self._stubs]
        for a in added:
            self._stubs[a] = (lambda sc, g: BLOCK, "piece stop 0x%08X" % a)
        try:
            r = self.run(t, label=label or "piece 0x%08X" % start, **kw)
        finally:
            for a in added:
                del self._stubs[a]
        if not r.fault and not (r.blocked and r.regs["pc"] in stops):
            r.fault = "piece ended at pc 0x%08X, not at a stop" % r.regs["pc"]
        r.blocked = None
        return r

    def task(self, name, entry, frame=(0, 0), stack_size=0x1000, regs=None):
        """A firmware task: its own stack, its own saved registers. run(task) starts it; a stub that returns BLOCK
        parks it at that stub, and the next run(task) calls the stub's handler again and goes on from there."""
        self._ntasks += 1
        t = Task(name, entry, frame, SP0 - 0x10000 * self._ntasks, stack_size)
        t.regs = dict(regs or {})
        return t

    def run(self, t, label=None, trace=True, log_writes=(), stop_writes=(), insn_limit=None, mmio_trace=True,
            calltrace=False):
        """calltrace: also keep Result.calls, the ordered list of (function start, sp) for every function entered
        (function starts from build/map/functions.tsv). print_calls() shows it as an indented tree."""
        emu, res = self.emu, Result()
        res.label = label or t.name
        self.current = t
        ret_pc = TRAMP + 7
        if not t.started:
            regs_byte, imm = t.frame if t.frame else emu.frame_of(t.entry)
            emu.write(TRAMP, b"\xdd" + struct.pack("<I", (t.entry - TRAMP) & 0xFFFFFFFF) + bytes([regs_byte, imm]))
            emu.write(ret_pc, b"\xca\x00")
            for k, w in enumerate(t.stack_args):
                emu.write(t.sp_top + 4 + 4 * k, struct.pack("<I", w & 0xFFFFFFFF))
            init = {"pc": TRAMP, "sp": t.sp_top, "mdr": 0, "psw": 0}
            init.update(t.regs)
            emu.req("reset", regs=init)
            t.started = True
        elif t.done:
            raise EmuError("task %s has returned" % t.name)
        else:
            emu.req("setRegs", regs={k: v for k, v in t.regs.items() if k not in ("insns", "fault")})
        t.blocked = None
        insns0 = emu.regs_of(emu.req("regs"))["insns"]
        files = {}
        if trace:
            files["exec"] = self._tmp("exec")
        if mmio_trace:
            files["mmio"] = self._tmp("mmio")
        if files:
            emu.req("trace", format="jsonl", **files)
        watches = [{"id": 1000 + i, "lo": lo, "hi": hi, "kind": "w", "action": "log"} for i, (lo, hi) in enumerate(log_writes)]
        watches += [{"id": i, "lo": lo, "hi": hi, "kind": "w", "action": "stop"} for i, (lo, hi) in enumerate(stop_writes)]
        emu.req("watch", list=watches)
        emu.req("watchLog")                              # drop old entries
        limit = insn_limit or self.insn_limit
        try:
            while True:
                stops = [ret_pc] + list(self._stubs)
                r = emu.req("cont", stops=stops, budget=limit)
                rg = emu.regs_of(r)
                res.stderr += r.get("stderr", [])
                self._drain(res)
                if r["stop"] == "break":
                    pc = rg["pc"]
                    if pc == ret_pc:
                        t.done = True
                        break
                    fn, name = self._stubs[pc]
                    try:
                        ret = fn(self, rg) if fn else {"d0": 0}
                    except Exception as e:             # a stub that cannot answer ends the call with its reason
                        if e.__class__.__name__ != "Stuck":
                            raise
                        res.fault = "stub %s: %s" % (name, e)
                        res.backtrace = self.backtrace(rg, t.sp_top)
                        break
                    if ret is BLOCK:
                        t.blocked = (pc, name)
                        res.blocked = t.blocked
                        res.backtrace = self.backtrace(rg, t.sp_top)
                        break
                    if ret is CONTINUE:                  # a probe: step over the breakpoint, then go on
                        r = emu.req("step")
                        if r["stop"] != "break":
                            rg = emu.regs_of(r)
                            if not (r["stop"] == "fault" and (self._mmio_fix(rg, r, res) or self._div0_fix(rg, r, res))):
                                res.fault = "%s %s at pc %s (after a probe)" % (r["stop"], r.get("fault"), funcs().name(rg["pc"]))
                                res.backtrace = self.backtrace(rg, t.sp_top)
                                break
                        continue
                    ret = ret or {}
                    res.stubs.append((pc, name, {k: rg[k] for k in ("d0", "d1", "a0", "a1", "mdr")}, dict(ret)))
                    if "pc" in ret:                      # the handler redirects (e.g. into the real function body)
                        emu.req("setRegs", regs=ret)
                        continue
                    key = self._return_form(pc, rg)
                    if key not in self._pads:
                        self._pads[key] = PADS + 4 * len(self._pads)
                        emu.write(self._pads[key], b"\xf0\xfc" if key == "rets" else b"\xde" + bytes(key))
                    emu.req("setRegs", regs={**ret, "pc": self._pads[key]})
                    continue
                if r["stop"] == "fault" and (self._mmio_fix(rg, r, res) or self._div0_fix(rg, r, res)):
                    continue
                if r["stop"] == "watch":
                    w = r["watch"]
                    res.fault = "stop watch: write of %d bytes at %s (value %s) by pc %s" % (w["size"], w["addr"], w["value"], funcs().name(int(w["pc"], 16)))
                elif r["stop"] == "paused":
                    res.fault = "instruction limit (%d) at pc %s" % (limit, funcs().name(rg["pc"]))
                    emu.req("halt")
                else:
                    res.fault = "%s %s at pc %s: %s" % (r["stop"], r.get("fault"), funcs().name(rg["pc"]), " | ".join(r.get("stderr", [])[-3:]))
                res.backtrace = self.backtrace(rg, t.sp_top)
                break
        finally:
            if files:
                emu.req("trace", off=True)
            emu.req("watch", list=[])
            self.current = None
        t.regs = dict(rg)
        res.regs = rg
        res.insns = rg["insns"] - insns0
        min_sp = t.sp_top
        if "exec" in files:
            starts = set(funcs().starts) if calltrace else ()
            with open(files["exec"]) as f:
                for line in f:
                    i = line.index('"pc":"0x')
                    pc = int(line[i + 8:i + 16], 16)
                    res.pcs.add(pc)
                    j = line.index('"sp":"0x', i)
                    sp = int(line[j + 8:j + 16], 16)
                    if sp < min_sp and sp > t.sp_top - 0x10000:
                        min_sp = sp
                    if pc in starts:
                        k = line.index('"d0":"0x', j)
                        res.calls.append((pc, sp, int(line[k + 8:k + 16], 16)))
            os.unlink(files["exec"])
        res.stack_used = t.sp_top - min_sp
        if "mmio" in files:
            with open(files["mmio"]) as f:
                for line in f:
                    m = json.loads(line)
                    res.mmio.append((m["dir"], int(m["addr"], 16), int(m["value"], 16), m["size"], int(m["pc"], 16) if m.get("pc") else None))
            os.unlink(files["mmio"])
        if not res.fault and t.done and rg["sp"] != t.sp_top:
            res.fault = "sp after return 0x%08X != 0x%08X" % (rg["sp"], t.sp_top)
        if res.div0:
            res.notes.append("%d divisions by zero skipped, at %s" % (len(res.div0), ", ".join("0x%08X" % p for p in sorted(set(res.div0))[:6])))
        if t.stack_size and res.stack_used > t.stack_size:
            res.notes.append("stack use %d bytes is above the task's stack size %d" % (res.stack_used, t.stack_size))
        self.results.append(res)
        return res

    def _tmp(self, kind):
        fd, p = tempfile.mkstemp(suffix=".jsonl", prefix="scen-%s-" % kind, dir=os.environ.get("EMU_TMP"))
        os.close(fd)
        return p

    def _drain(self, res):
        while True:
            r = self.emu.req("watchLog")
            for e in r["entries"]:
                res.writes.append((int(e["addr"], 16), e["size"], int(e["value"], 16), int(e["pc"], 16)))
            if r.get("dropped"):
                res.stderr.append("watch log dropped %d entries" % r["dropped"])
            if not r.get("more"):
                break

    def _return_form(self, stub, rg):
        mdr = rg["mdr"]
        code = self.emu.read(mdr - 7, 7)
        if code[0] == 0xDD and (mdr - 7 + struct.unpack_from("<i", code, 1)[0]) & 0xFFFFFFFF == stub:
            return (code[5], code[6])
        if code[2] == 0xCD and (mdr - 5 + struct.unpack_from("<h", code, 3)[0]) & 0xFFFFFFFF == stub:
            return (code[5], code[6])
        if (code[5] == 0xF0 and 0xF0 <= code[6] <= 0xF3) or code[1:3] == b"\xfc\xff" or code[3:5] == b"\xfa\xff":
            if self.emu.u32(rg["sp"]) == mdr:
                return "rets"
        raise EmuError("stub 0x%08X: the instruction before mdr 0x%08X is not a call to it (%s)" % (stub, mdr, code.hex()))

    # --- device accesses that om-emu refuses
    DENIED = re.compile(r"lab-stub DENIED (read|write) 0x([0-9a-f]+) size (\d+)(?: value 0x([0-9a-f]+))?")

    def _mmio_fix(self, rg, r, res):
        """om-emu faults (reason 2) on an access to a device page it does not model. The harness then does the
        access itself and goes on: a write is logged and dropped; a read gets its value from on_mmio_read(sc, addr,
        size, pc) -> value, or from mmio_values[addr], or mmio_default. Only plain loads and stores are known
        (mov, movbu, movhu, movb, movh between memory and a register, and bset/bclr, whose store is dropped);
        any other instruction leaves the fault in place."""
        if self.mmio == "fault":
            return False
        m = None
        for line in r.get("stderr", []):
            m = self.DENIED.search(line) or m
        if not m:
            return False
        direction, addr, size = m.group(1), int(m.group(2), 16), int(m.group(3))
        pc = rg["pc"]
        line = self.emu.req("disasm", addr=pc, n=1)["lines"][0].split("\t")
        length, mnem, ops = len(line[1].split()), line[2].strip(), line[3].strip() if len(line) > 3 else ""
        new = {"pc": pc + length, "fault": 0}
        if direction == "write":
            if mnem not in ("mov", "movbu", "movhu", "movb", "movh", "bset", "bclr"):
                return False
            res.mmio.append(("w*", addr, int(m.group(4) or "0", 16), size, pc))
            if self.on_device_write:
                self.on_device_write(self, addr, int(m.group(4) or "0", 16), size, pc)
        else:
            dst = ops.rsplit(",", 1)[-1]
            if mnem in ("bset", "bclr"):                  # the read half of a read-modify-write: drop the whole thing
                res.mmio.append(("r*", addr, 0, size, pc))
                self.emu.req("setRegs", regs=new)
                return True
            if mnem not in ("mov", "movbu", "movhu") or dst not in ("d0", "d1", "d2", "d3", "a0", "a1", "a2", "a3"):
                return False
            v = self.on_mmio_read(self, addr, size, pc) if self.on_mmio_read else None
            if v is None:
                v = self.mmio_values.get(addr, self.mmio_default)
            if v is None:
                return False
            v &= 0xFFFFFFFF >> (32 - 8 * size)
            res.mmio.append(("r*", addr, v, size, pc))
            new[dst] = v
        self.emu.req("setRegs", regs=new)
        return True

    def _div0_fix(self, rg, r, res):
        """om-emu traps (reason 6) on a division by zero. The MN103 does not: it sets the V flag and goes on with
        an undefined result. With div0 = "skip" the harness does that (quotient left as it was) and notes it."""
        if self.div0 != "skip" or r.get("fault") != 6:
            return False
        c = self.emu.read(rg["pc"], 2)
        if c[0] != 0xF2 or (c[1] & 0xE0) != 0x60:         # div Dm,Dn (f2 6x) / divu Dm,Dn (f2 7x)
            return False
        if rg["d%d" % ((c[1] >> 2) & 3)] != 0:
            return False
        res.div0.append(rg["pc"])
        self.emu.req("setRegs", regs={"pc": rg["pc"] + 2, "psw": rg["psw"] | 8, "fault": 0})
        return True

    # --- backtrace
    def backtrace(self, rg, sp_top=SP0, words=400):
        """Return addresses on the stack, innermost first: MDR, then every stack word that follows a call instruction."""
        out = ["pc  %s" % funcs().name(rg["pc"]), "mdr %s" % funcs().name(rg["mdr"])]
        sp = rg["sp"]
        if not (TRAMP <= sp <= sp_top):
            return out + ["sp 0x%08X is outside the harness stack" % sp]
        n = min(words, (sp_top + 16 - sp) // 4)
        data = self.emu.read(sp, 4 * n) if n > 0 else b""
        for i in range(n):
            v = struct.unpack_from("<I", data, 4 * i)[0]
            if BASE + 7 <= v < BASE + len(self.image) or TRAMP <= v < TRAMP + 16:
                c = self.emu.read(v - 7, 7)
                if c[0] == 0xDD or c[2] == 0xCD or (c[5] == 0xF0 and 0xF0 <= c[6] <= 0xF3) or c[1:3] == b"\xfc\xff":
                    out.append("sp+0x%03X ret %s" % (4 * i, funcs().name(v)))
        return out


def print_calls(res, lo=0, hi=0xFFFFFFFF, names=None, out=print, limit=400):
    """Print Result.calls as a tree (indent by stack depth). Only functions in [lo, hi) are shown.
    names: {addr: text} to print after an address."""
    names = names or {}
    shown = [c for c in res.calls if lo <= c[0] < hi]
    if not shown:
        return
    top = max(sp for _, sp, _ in shown)
    for pc, sp, d0 in shown[:limit]:
        out("%s0x%08X(d0=0x%X) %s" % ("  " * min(40, (top - sp) // 24), pc, d0, names.get(pc, "")))
    if len(shown) > limit:
        out("... %d more" % (len(shown) - limit))


# --- comparing two runs
def in_ranges(a, ranges):
    return any(lo <= a < hi for lo, hi in ranges)


def diff_pcs(a, b, new_code=(), hook_sites=()):
    """Compare the executed-pc sets of the same call on two images (a: base, b: patched).
    new_code: [(lo, hi)] ranges that exist only in the patched image (the new routines);
    hook_sites: [(lo, hi)] the replaced bytes in stock code.
    Returns dict: only_base, only_patched_new (pcs in new_code), only_patched_stock (stock code that ran only in the
    patched image), skipped_at_hooks (base pcs inside hook sites: replaced, expected)."""
    oa, ob = a - b, b - a
    return {"only_base": sorted(p for p in oa if not in_ranges(p, hook_sites)),
            "skipped_at_hooks": sorted(p for p in oa if in_ranges(p, hook_sites)),
            "only_patched_new": sorted(p for p in ob if in_ranges(p, new_code)),
            "only_patched_stock": sorted(p for p in ob if not in_ranges(p, new_code) and not in_ranges(p, hook_sites)),
            "hooks_entered": sorted(p for p in ob if in_ranges(p, hook_sites))}


def by_function(pcs):
    """{function start: count of pcs} for a list of pcs."""
    out = {}
    for p in pcs:
        f = funcs().of(p)
        out[f] = out.get(f, 0) + 1
    return out


def fmt_funcs(pcs, limit=12):
    d = by_function(pcs)
    items = sorted(d.items(), key=lambda kv: kv[0] or 0)
    s = ", ".join("0x%08X (%d)" % (f or 0, n) for f, n in items[:limit])
    return s + (", ... %d more functions" % (len(items) - limit) if len(items) > limit else "")


def final_writes(writes, skip=()):
    """{byte address: value} after a write log (little endian), without the bytes in skip ranges.
    Uncached aliases (0x8.., 0xA.., 0xB..) are folded onto the cached address."""
    mem = {}
    for addr, size, value, pc in writes:
        if addr & 0x80000000 and (addr & 0x3FFFFFFF | 0x40000000) < 0x80000000 and not 0x8C000000 <= addr < 0xA0000000:
            addr = addr & 0x3FFFFFFF | 0x40000000
        for i in range(size):
            if not in_ranges(addr + i, skip):
                mem[addr + i] = (value >> (8 * i)) & 0xFF
    return mem


def diff_writes(a, b, skip=()):
    """Bytes whose final written value differs between two write logs: {addr: (base or None, patched or None)}."""
    ma, mb = final_writes(a, skip), final_writes(b, skip)
    return {k: (ma.get(k), mb.get(k)) for k in sorted(set(ma) | set(mb)) if ma.get(k) != mb.get(k)}


def patch_ranges(base_image, patched_image, min_new=10):
    """(new_code, hook_sites) runtime ranges from two block-0 images: a changed run of min_new bytes or more is
    new code (a hook is a 5-byte jump plus at most a few nop); every shorter changed run is a hook site."""
    import patchblock
    runs = []
    for lo, hi in patchblock.ranges(base_image, patched_image):
        if runs and lo - runs[-1][1] <= 3:
            runs[-1][1] = hi
        else:
            runs.append([lo, hi])
    new, hooks = [], []
    for lo, hi in runs:
        old = base_image[lo:hi]
        (new if hi - lo >= min_new else hooks).append((BASE + lo, BASE + hi))
    return new, hooks
