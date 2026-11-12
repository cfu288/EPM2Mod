"""Run E-PM2 block-0 functions in om-emu (bin/debug.mjs --serve, model E101).

The driver starts one `debug.mjs --serve` process and talks its JSON-lines protocol. A function is called through
a real MN10300 `call` instruction written into scratch RAM (a trampoline), so the callee sees a true call frame
and returns with its own `ret`/`retf`. Stubs are breakpoints: when the CPU reaches a stubbed function, Python
decides the return registers, and the CPU returns through a `retf` with the register list and frame size of the
call that reached it (read from the call instruction before MDR).

Environment:
    OM_EMU_DIR   om-emu checkout (default ~/opt/om-emu)
    OM_EMU_NODE  Node >= 26 (default ~/opt/node26/bin/node)
"""
import json, os, struct, subprocess, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = 0x7E421020                      # block-0 runtime base (firmware-map.md section 4)
STOCK_BLOCK0 = os.path.join(ROOT, "build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin")
STOCK_SHA256 = "1b7c4bb187e5e0b6e76ef362a4095a5b3fcf92917367999d32d6b6404b71468d"
OM_EMU_DIR = os.environ.get("OM_EMU_DIR", os.path.expanduser("~/opt/om-emu"))
NODE = os.environ.get("OM_EMU_NODE", os.path.expanduser("~/opt/node26/bin/node"))

# Scratch RAM for the harness (DRAM below the image; nothing else runs, so it is free in the emulator)
TRAMP = 0x7D000000                     # the call instruction; the return lands at TRAMP + 7
PADS = 0x7D000100                      # return pads for stubs (3 bytes each)
SP0 = 0x7D100000                       # caller's stack pointer at the call
DATA = 0x7D200000                      # input / output buffers for cases

REGS = ["d0", "d1", "d2", "d3", "a0", "a1", "a2", "a3", "sp", "pc", "psw", "mdr", "lir", "lar", "fault", "insns"]


class EmuError(RuntimeError):
    pass


def u32(b, o=0):
    return struct.unpack_from("<I", b, o)[0]


def call_frames(image, entry):
    """(regs byte, frame imm) of every `call` (cd d16 / dd d32) in the image that targets entry."""
    found = {}
    for i in range(len(image) - 7):
        op = image[i]
        if op == 0xDD:
            if (BASE + i + struct.unpack_from("<i", image, i + 1)[0]) & 0xFFFFFFFF == entry:
                found.setdefault((image[i + 5], image[i + 6]), []).append(BASE + i)
        elif op == 0xCD:
            if (BASE + i + struct.unpack_from("<h", image, i + 1)[0]) & 0xFFFFFFFF == entry:
                found.setdefault((image[i + 3], image[i + 4]), []).append(BASE + i)
    return found


class Emu:
    def __init__(self, insn_limit=5_000_000):
        if not os.path.exists(NODE):
            raise EmuError(f"no node at {NODE} (set OM_EMU_NODE)")
        env = dict(os.environ, OM_EMU_MODEL="E101")
        self.p = subprocess.Popen([NODE, "emu/bin/debug.mjs", "--serve"], cwd=OM_EMU_DIR, env=env, text=True,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.n = 0
        self.insn_limit = insn_limit
        self.image = None

    def req(self, op, **kw):
        self.n += 1
        self.p.stdin.write(json.dumps({"id": self.n, "op": op, **kw}) + "\n")
        self.p.stdin.flush()
        line = self.p.stdout.readline()
        if not line:
            raise EmuError(f"om-emu exited: {self.p.stderr.read()[-2000:]}")
        r = json.loads(line)
        if not r.get("ok"):
            raise EmuError(f"{op}: {r['error']['type']}: {r['error']['message']}")
        return r

    def close(self):
        try:
            self.req("quit")
        except Exception:
            pass
        self.p.wait(timeout=10)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    # --- machine -------------------------------------------------------------------------------------------
    def load(self, path):
        self.image = open(path, "rb").read()
        self._frames = {}
        self.req("load", image=os.path.abspath(path), insnLimit=self.insn_limit)

    def write(self, addr, data):
        if data:
            self.req("write", addr=addr, hex=bytes(data).hex())

    def read(self, addr, n):
        out = b""
        while n > 0:                       # the debugger reads at most 0x800 bytes per request
            k = min(n, 0x800)
            out += bytes.fromhex(self.req("read", addr=addr, size=k)["hex"])
            addr += k
            n -= k
        return out

    def u32(self, addr):
        return u32(self.read(addr, 4))

    def cstr(self, addr, n=96):
        return self.read(addr, n).split(b"\0")[0].decode("latin-1")

    @staticmethod
    def regs_of(r):
        return {k: int(v, 16) for k, v in r["regs"].items()}

    # --- calling -------------------------------------------------------------------------------------------
    def frame_of(self, entry):
        if entry in self._frames:
            return self._frames[entry]
        f = call_frames(self.image, entry)
        if len(f) != 1:
            raise EmuError(f"0x{entry:08x}: call frames {sorted(f)} in the image; give frame=(regs, imm)")
        self._frames[entry] = next(iter(f))
        return self._frames[entry]

    def call(self, entry, regs=None, stack=(), frame=None, stubs=None, trace=True, max_stub_calls=10000):
        """Call entry; returns dict(regs, stub_calls, pcs, insns). stack: words at caller sp+4, +8, ...
        stubs: {addr: fn(emu, regs) -> dict of return registers}. Raises EmuError on a fault or the insn limit."""
        stubs = stubs or {}
        regs_byte, imm = frame if frame else self.frame_of(entry)
        rel = (entry - TRAMP) & 0xFFFFFFFF
        self.write(TRAMP, b"\xdd" + struct.pack("<I", rel) + bytes([regs_byte, imm]))
        ret_pc = TRAMP + 7
        self.write(ret_pc, b"\xca\x00")                 # bra . (never executed: the breakpoint stops first)
        for k, w in enumerate(stack):
            self.write(SP0 + 4 + 4 * k, struct.pack("<I", w & 0xFFFFFFFF))
        init = {"pc": TRAMP, "sp": SP0, "mdr": 0, "psw": 0}
        init.update(regs or {})
        self.req("reset", regs=init)
        tfile = None
        if trace:
            fd, tfile = tempfile.mkstemp(suffix=".jsonl", prefix="omemu-trace-")
            os.close(fd)
            self.req("trace", exec=tfile, format="jsonl")
        stops = [ret_pc] + list(stubs)
        calls, pads = [], {}
        try:
            while True:
                r = self.req("cont", stops=stops)
                rg = self.regs_of(r)
                if r["stop"] != "break":
                    raise EmuError(f"stop {r['stop']} at pc 0x{rg['pc']:08x} fault {rg['fault']}: "
                                   + " | ".join(r.get("stderr", [])[-6:]))
                pc = rg["pc"]
                if pc == ret_pc:
                    break
                if len(calls) >= max_stub_calls:
                    raise EmuError("too many stub calls")
                ret = stubs[pc](self, rg) or {}
                calls.append({"stub": pc, "args": {k: rg[k] for k in ("d0", "d1", "a0", "a1")}, "ret": dict(ret)})
                key = self._return_form(pc, rg["mdr"])
                if key not in pads:
                    pads[key] = PADS + 4 * len(pads)
                    self.write(pads[key], b"\xde" + bytes(key))     # retf [regs],imm
                self.req("setRegs", regs={**ret, "pc": pads[key]})
        finally:
            if trace:
                self.req("trace", off=True)
        pcs = set()
        if tfile:
            with open(tfile) as f:
                for line in f:
                    pcs.add(int(json.loads(line)["pc"], 16))
            os.unlink(tfile)
        out_regs = rg
        if out_regs["sp"] != SP0:
            raise EmuError(f"sp after return 0x{out_regs['sp']:08x} != 0x{SP0:08x} (frame mismatch)")
        return {"regs": out_regs, "stub_calls": calls, "pcs": pcs, "insns": out_regs["insns"]}

    def _return_form(self, stub, mdr):
        """The (regs, imm) of the call that reached stub, from the instruction that ends at mdr."""
        code = self.read(mdr - 7, 7)
        if code[0] == 0xDD and (mdr - 7 + struct.unpack_from("<i", code, 1)[0]) & 0xFFFFFFFF == stub:
            return (code[5], code[6])
        if code[2] == 0xCD and (mdr - 5 + struct.unpack_from("<h", code, 3)[0]) & 0xFFFFFFFF == stub:
            return (code[5], code[6])
        raise EmuError(f"stub 0x{stub:08x}: the instruction before mdr 0x{mdr:08x} is not a call to it ({code.hex()})")


def check_stock(path=STOCK_BLOCK0):
    import hashlib
    h = hashlib.sha256(open(path, "rb").read()).hexdigest()
    if h != STOCK_SHA256:
        raise EmuError(f"{path}: sha256 {h} is not stock E-PM2 v1.6 block 0")
    return path
