"""Named E-PM2 function cases for emurun.py.

Each case: entry, the code ranges allowed to run (anything else executed is an error), the stubs, the input rows,
run(emu, row) -> outputs, and model(row, image) -> the outputs the code should give (an independent Python
reading of the disassembly / notes), or None where no model is given.
Addresses: E-PM2 v1.6 runtime addresses.
"""
import hashlib, struct
from omemu import BASE, DATA

U32 = 0xFFFFFFFF


def img_u8(image, addr):
    return image[addr - BASE]


class Case:
    name = ""
    doc = ""
    entry = 0
    ranges = []            # [(lo, hi)) of code that may run
    stubs_doc = []         # (addr, what the stub does)

    def stubs(self, row):
        return {}

    def rows(self):
        return []

    def run(self, emu, row):
        raise NotImplementedError

    def model(self, row, image):
        return None


# ---- C runtime helpers (map section 13a) ---------------------------------------------------------------------
class Memcpy(Case):
    name, entry = "memcpy", 0x7E5081FA
    doc = "memcpy(a0 dst, a1 src, d0 n) in the sc library; byte, halfword or word loop by alignment"
    ranges = [(0x7E5081FA, 0x7E508256)]
    SRC, DST = DATA, DATA + 0x1000

    def rows(self):
        return [dict(dst_off=d, src_off=s, n=n) for d, s, n in
                [(0, 0, 16), (0, 0, 0), (1, 0, 13), (2, 2, 6), (0, 0, 64), (3, 1, 7), (0, 4, 12)]]

    def run(self, emu, row):
        emu.write(self.SRC, bytes(range(128)))
        emu.write(self.DST, b"\xaa" * 96)
        r = emu.call(self.entry, {"a0": self.DST + row["dst_off"], "a1": self.SRC + row["src_off"], "d0": row["n"],
                                  "d2": 0x22222222, "a2": 0xA2A2A2A2})
        g = r["regs"]
        return {"dst": emu.read(self.DST, 96).hex(), "d2_kept": g["d2"] == 0x22222222, "a2_kept": g["a2"] == 0xA2A2A2A2,
                "_r": r}

    def model(self, row, image):
        dst = bytearray(b"\xaa" * 96)
        src = bytes(range(128))
        d, s, n = row["dst_off"], row["src_off"], row["n"]
        dst[d:d + n] = src[s:s + n]
        return {"dst": dst.hex(), "d2_kept": True, "a2_kept": True}


class Strlen(Case):
    name, entry = "strlen", 0x7E508346
    doc = "strlen(a0) -> d0 in the sc library"
    ranges = [(0x7E508346, 0x7E508358)]
    STRS = [b"Hello", b"", b"\x80\xffA", b"A" * 300, b"E-PM2 v1.6"]

    def rows(self):
        return [dict(s=s.hex()) for s in self.STRS]

    def run(self, emu, row):
        emu.write(DATA, bytes.fromhex(row["s"]) + b"\0")
        r = emu.call(self.entry, {"a0": DATA})
        return {"d0": r["regs"]["d0"], "_r": r}

    def model(self, row, image):
        return {"d0": len(bytes.fromhex(row["s"]))}


# ---- movie recording time limit (map section 04 §1.2; experiments/2026-11-08-disassembly/NOTES.md) -----------
class RecLimit(Case):
    name, entry = "rec_limit", 0x7E6EDE08
    doc = ("movie time-limit computation at record start: d0 quality (u16), d1 free space (sectors); "
           "settings 33105/7 (rate hi/lo) and 26225/0 (format 3 MOV, 2 AVCHD) from the settings getter; "
           "writes ctx+32/+36 (free-space frames), ctx+40 (max frames); returns free-space time x600")
    ranges = [(0x7E6EDE08, 0x7E6EDF9D)]
    CTX = DATA + 0x2000
    S_CTX, S_SET, S_DBG, S_ERR = 0x7E6ED536, 0x7E457C75, 0x7E6D13E0, 0x7E6D1429
    stubs_doc = [
        (S_CTX, "movie context getter (42 callers): returns a0 = a 256-byte zeroed buffer (CTX)"),
        (S_SET, "settings getter (d0 id, d1 index, a0 0): returns d0 = row's value for 33105/7 (hi) and 26225/0 (format); any other id is an error"),
        (S_DBG, "debug print (d0 mask 16, a0 format, d1 value): no output; logged. Natively it returns at once while the mask word 0xA07511E0 is 0"),
        (S_ERR, "error print (d0 -1, a0 format, d1 value): no output; logged"),
    ]
    FREE = [500, 2_097_152, 134_217_728]            # sectors: <= reserve, 1 GiB, 64 GiB

    def rows(self):
        rows = []
        for fmt, qs in ((3, (6, 3, 4, 7)), (2, (5, 3, 4)), (1, (6,))):
            for q in qs:
                for hi in (1, 0):
                    for free in self.FREE:
                        rows.append(dict(fmt=fmt, q=q, hi=hi, free=free))
        return rows

    def stubs(self, row):
        def ctx(emu, r):
            return {"a0": self.CTX}

        def setting(emu, r):
            key = (r["d0"] & 0xFFFF, r["d1"] & 0xFFFF)
            if key == (33105, 7):
                return {"d0": row["hi"]}
            if key == (26225, 0):
                return {"d0": row["fmt"]}
            raise RuntimeError(f"settings getter: unexpected id {key}")

        def prn(emu, r):
            return {}
        return {self.S_CTX: ctx, self.S_SET: setting, self.S_DBG: prn, self.S_ERR: prn}

    def run(self, emu, row):
        emu.write(self.CTX, b"\0" * 256)
        r = emu.call(self.entry, {"d0": row["q"], "d1": row["free"]}, stubs=self.stubs(row))
        ctx = emu.read(self.CTX, 48)
        prints = []
        for c in r["stub_calls"]:
            if c["stub"] in (self.S_DBG, self.S_ERR):
                prints.append(f"{emu.cstr(c['args']['a0']).strip()} {c['args']['d1']}")
        out = {"ret": r["regs"]["d0"], "free_frames": struct.unpack_from("<I", ctx, 32)[0],
               "free_frames2": struct.unpack_from("<I", ctx, 36)[0], "max_frames": struct.unpack_from("<I", ctx, 40)[0],
               "prints": prints, "_r": r}
        out.update(self.fill(emu.image, row, out["max_frames"]))
        return out

    # Constants of 0x7E6EDE08, read from the image (stock values in comments). imm16 sites: `mov imm16,dN` (2c..2f,
    # sign-extended), `mov imm16,aN` (24..27, zero-extended); `mov imm8,d0` (80, sign-extended) for the AVCHD overhead.
    RATE = {(3, 6, 1): 0x7E6EDEB9, (3, 6, 0): 0x7E6EDEC3,          # 4883 / 4151 sectors/s
            (3, 3, 1): 0x7E6EDECA, (3, 3, 0): 0x7E6EDED4,          # 3174 / 2442
            (3, 4, 1): 0x7E6EDEDB, (3, 4, 0): 0x7E6EDEDB,          # 977 (one rate)
            (2, 5, 1): 0x7E6EDF00, (2, 5, 0): 0x7E6EDF0A,          # 5860 / 4711
            (2, 3, 1): 0x7E6EDF11, (2, 3, 0): 0x7E6EDF1B}          # 4711 / 4045
    RESERVE = {(3, 6): 0x7E6EDE6B, (3, 3): 0x7E6EDE6B, (3, 4): 0x7E6EDE70}   # 832, 832, 2624; AVCHD 400 at 0x7E6EDE8A
    # The bitrate table 0x7E6EE4A2: the peak (0xA0753564) each mode gets, `mov imm32,d0` (fc cc imm32)
    PEAK = {(3, 6, 1): 0x7E6EE583, (3, 6, 0): 0x7E6EE58B, (3, 3, 1): 0x7E6EE59A, (3, 3, 0): 0x7E6EE5A2,
            (3, 4, 1): 0x7E6EE5AA, (3, 4, 0): 0x7E6EE5AA, (2, 5, 1): 0x7E6EE510, (2, 5, 0): 0x7E6EE52C,
            (2, 3, 1): 0x7E6EE52C, (2, 3, 0): 0x7E6EE540}
    FILECAP = 8388608                                               # 4 GiB in 512-byte sectors (0x7E6EDE57)

    @staticmethod
    def imm16(image, addr, ops):
        o = addr - BASE
        assert image[o] in ops, f"0x{addr:08x}: opcode {image[o]:02x} is not one of {ops}"
        v = struct.unpack_from("<H", image, o + 1)[0]
        return v - 0x10000 if image[o] >= 0x2C and v & 0x8000 else v       # 2c..2f sign-extend; 24..27 zero-extend

    @classmethod
    def limit_at(cls, image, addr):
        """The imm16 of `mov imm16,a3` (27 lo hi) at addr."""
        return cls.imm16(image, addr, (0x27,))

    @classmethod
    def consts(cls, image, fmt, q, hi):
        """(rate, overhead, reserve, limit) of a mode, from the image; None for a mode the routine rejects."""
        key = (fmt, q, 1 if hi == 1 else 0)
        if key not in cls.RATE:
            return None
        rate = cls.imm16(image, cls.RATE[key], (0x2C,))
        if fmt == 3:
            ov = cls.imm16(image, 0x7E6EDE50, (0x2C,))
            res = cls.imm16(image, cls.RESERVE[(fmt, q)], (0x26,))
            lim = cls.limit_at(image, 0x7E6EDEE0 if q == 4 else 0x7E6EDF20)
        else:
            assert image[0x7E6EDE86 - BASE] == 0x80
            ov = struct.unpack("b", image[0x7E6EDE87 - BASE:0x7E6EDE88 - BASE])[0]
            res = cls.imm16(image, 0x7E6EDE8A, (0x26,))
            lim = cls.limit_at(image, 0x7E6EDF20)
        return rate, ov, res, lim

    @classmethod
    def fill(cls, image, row, max_frames):
        """Consistency of the stop point with the bitrate table: the file size at max_frames if video ran at exactly
        the table peak, plus the routine's audio overhead and reserve, as a share of 4 GiB. Inputs: the emulated
        max_frames and constants read from the image (not emulated)."""
        c = cls.consts(image, row["fmt"], row["q"], row["hi"])
        if c is None or max_frames == 0:
            return {}
        rate, ov, res, _ = c
        o = cls.PEAK[(row["fmt"], row["q"], 1 if row["hi"] == 1 else 0)] - BASE
        assert image[o:o + 2] == b"\xfc\xcc"
        peak = struct.unpack_from("<I", image, o + 2)[0]
        t = max_frames // 30
        size = t * (peak // 8 + ov * 512) + res * 512
        return {"peak": peak, "rate_in_step": rate == -(-peak // 4096), "fill_4g": round(size / (cls.FILECAP * 512), 4),
                "fits_4g": size <= cls.FILECAP * 512}

    def model(self, row, image):
        fmt, q, hi, free = row["fmt"], row["q"], row["hi"], row["free"]
        c = self.consts(image, fmt, q, hi)
        if c is None:                      # rejected quality or format: rate 0, limit 0
            rate, limit = 0, 0
            ov = 375 if fmt == 3 else 47
            a2 = 0 if fmt == 3 else 400    # MOV: the caller's a2 (0 in this harness), as no reserve is set
        else:
            rate, ov, a2, limit = c
        if free <= a2:
            t_free = clamped = 0
        else:
            t_free = (free - a2) // (rate + ov)
            t_cap = ((self.FILECAP - a2) & U32) // (rate + ov)
            clamped = min(limit, t_cap, t_free)
        out = {"ret": (t_free * 600) & U32, "free_frames": (t_free * 30) & U32, "free_frames2": (t_free * 30) & U32,
               "max_frames": (clamped * 30) & U32}
        out.update(self.fill(image, row, out["max_frames"]))
        return out


# ---- tone-curve selector (film-portra NOTES §11.1; reader of 0x7E75D6F0) ------------------------------------
class CurveSelect(Case):
    name, entry = "curve_select", 0x7E56E837
    doc = ("IMG library tone-curve selector: returns a0 = one 256 x u16 table. Register args d0, d1, a0, a1 "
           "(flags); stack args at caller sp+4.. : flag byte, art code, gradation, picture mode, contrast "
           "(the builder 0x7E56EB95's call at 0x7E56ED5B). Output: the pointer and the 512 bytes it points at")
    ranges = [(0x7E56E837, 0x7E56EB12), (0x7E56E80F, 0x7E56E837)]
    TABLE = 0x7E763F14             # per-mode contrast offset bytes (modes 1..5 -> index 0..4, else 1)
    SHARED = [0x7E75CCF0, 0x7E75CEF0, 0x7E75D0F0, None, 0x7E75D2F0, 0x7E75D4F0]   # contrast -3..+2 (0: identity)
    PORTRAIT = [0x7E75D6F0, 0x7E75D8F0, 0x7E75DAF0, 0x7E75DCF0, 0x7E75DEF0]    # contrast -2..+2

    def rows(self):
        rows = []
        for mode in (1, 2, 3, 4, 5, 0, 6):
            for c in range(-3, 4):
                rows.append(dict(art=0, grad=0, mode=mode, contrast=c, flag=0, d1=0))
        rows += [dict(art=0, grad=g, mode=1, contrast=0, flag=0, d1=0) for g in (1, -1)]
        rows += [dict(art=0, grad=0, mode=1, contrast=0, flag=0, d1=1)]
        rows += [dict(art=a, grad=0, mode=1, contrast=0, flag=0, d1=0) for a in range(8, 185)]
        return rows

    def run(self, emu, row):
        b = lambda v: v & 0xFF
        stack = [row["flag"], b(row["art"]), b(row["grad"]), b(row["mode"]), b(row["contrast"]), 0]
        r = emu.call(self.entry, {"d0": 0, "d1": row["d1"], "a0": 0, "a1": 0}, stack=stack)
        p = r["regs"]["a0"]
        t = emu.read(p, 512) if BASE <= p < BASE + 0xD7FFC0 else b""
        return {"table": f"0x{p:08x}", "sha": hashlib.sha256(t).hexdigest()[:16],
                "first8": list(struct.unpack_from("<8H", t)) if t else None, "_r": r, "_reads": [(p, 512)]}

    def model(self, row, image):
        if row["art"] != 0:
            return None                 # art codes: jump table 0x7E78C8E4, not modelled here
        if row["grad"] in (1, -1):
            return {"table": "0x7e75e0f0" if row["grad"] == 1 else "0x7e75e2f0"}
        m = row["mode"]
        idx = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4}.get(m, 1)
        off = struct.unpack("b", bytes([img_u8(image, self.TABLE + idx)]))[0]
        c = row["contrast"] + off
        ident = 0x7E75B8F0 if row["d1"] else 0x7E75B6F0
        if m == 4:
            p = self.PORTRAIT[max(-2, min(2, c)) + 2]
        else:
            p = self.SHARED[max(-3, min(2, c)) + 3] or ident
        return {"table": f"0x{p:08x}"}


# ---- base-gamma selector and art-matrix choice (film-portra NOTES §14.1, §26.1, §29-30) ----------------------
def gamma_lookup(image, code):
    """Python reading of 0x7E56B7A3-0x7E56B7E5: the handler the hash table gives an art code, or None (default)."""
    lo = img_u8(image, 0x7E56B7A7)
    if code < lo or code > 170:
        return None
    T = 0x7E78C154
    u = lambda a: struct.unpack_from("<I", image, a - BASE)[0]
    d3 = (code - 70) & U32
    a0 = T + 8 * (d3 & 31)
    for _ in range(64):
        d1 = u(a0)
        if d1 == d3:
            return u(a0 + 4)
        if d1 == 0:
            return None
        a0 += 8
        if a0 >= T + 0x100:
            a0 = T
    raise RuntimeError("hash probe does not end")


def gamma_pick(image, rec, member, variant):
    """Python reading of 0x7E56B732: one of the record's 8 table pointers (4 columns x 2 members)."""
    u = lambda a: struct.unpack_from("<I", image, a - BASE)[0]
    lo, x = variant & 7, variant & 0xE0
    if lo in (4, 5):
        off = 8 if x in (0x80, 0xA0, 0xC0) else 24
    elif lo == 7:
        off = 16
    else:
        off = 8 if x in (0x80, 0xA0, 0xC0) else 0
    return u(rec + off + (4 if member & 0xFF else 0))


class GammaSelect(Case):
    name, entry = "gamma_select", 0x7E56B790
    doc = ("IMG library base-gamma selector: writes three table pointers (R, G, B). Register args d0 (flag), d1 (pair "
           "member), a0 / a1 (where to store R / G); stack args at caller sp+4..: flag byte, variant byte, art code, -, "
           "where to store B. Output: the three table pointers; the model reads the hash table, the handler's records "
           "and the pick routine from the image")
    ranges = [(0x7E56B790, 0x7E56B886), (0x7E56B732, 0x7E56B790), (0x7E880F5C, 0x7E880F8D), (0x7ECB0888, 0x7ECB0A00)]
    OUT = DATA
    HANDLER = {0x7E56B7F8: [0x7E78B41C, 0x7E78B43C, 0x7E78B45C], 0x7E56B82A: [0x7E78B49C, 0x7E78B4BC, 0x7E78B4DC],
               0x7E880F5C: [0x7E78B3DC, 0x7E78B3FC, 0x7E78B47C], 0x7E56B7E7: [0x7E78B3DC] * 3,
               0x7E56B7F0: [0x7E78B3FC] * 3, 0x7E56B822: [0x7E78B47C] * 3, 0x7E56B85F: [0x7E78B39C] * 3}

    def rows(self):
        rows = []
        for d0, d1, s1 in ((0, 1, 0), (0, 0, 0), (1, 1, 0), (0, 4, 0x80), (1, 7, 0xC0), (0, 1, 0x24), (0, 1, 7)):
            rows += [dict(art=a, d0=d0, d1=d1, s1=s1) for a in [0] + list(range(60, 190))]
        return rows

    def run(self, emu, row):
        emu.write(self.OUT, b"\0" * 12)
        r = emu.call(self.entry, {"d0": row["d0"], "d1": row["d1"], "a0": self.OUT, "a1": self.OUT + 4},
                     stack=[0, row["s1"], row["art"], 0, self.OUT + 8])
        ptrs = list(struct.unpack("<3I", emu.read(self.OUT, 12)))
        return {"tables": [f"0x{p:08x}" for p in ptrs],
                "sha": [hashlib.sha256(emu.read(p, 512)).hexdigest()[:12] if BASE <= p < BASE + 0xD7FFC0 else None for p in ptrs],
                "_r": r, "_reads": [(p, 512) for p in ptrs]}

    def records(self, image, h):
        if h in self.HANDLER:
            return self.HANDLER[h]
        code = image[h - BASE:h - BASE + 6]                      # a slot stub: mov <triple>,a1
        if code[:2] != b"\xfc\xdd":
            raise RuntimeError(f"handler 0x{h:08x} is not known")
        tri = struct.unpack("<I", code[2:6])[0]
        return list(struct.unpack_from("<3I", image, tri - BASE))

    def model(self, row, image):
        h = gamma_lookup(image, row["art"])
        if h is None or h == 0x7E56B861:
            rec = [0x7E78B3BC if row["d0"] else 0x7E78B39C] * 3
        else:
            rec = self.records(image, h)
        return {"tables": [f"0x{gamma_pick(image, x, row['d1'], row['s1']):08x}" for x in rec]}


class MatrixChoice(Case):
    name, entry = "matrix_choice", 0x7E56C6A5
    doc = ("Art-matrix choice inside the colour-matrix stage: entered at the compare chain 0x7E56C6A5 with the art "
           "code in d0; reports which of the four continuations is reached (table 1 block, table 2 block, apply with "
           "a1 = table, or no matrix). Not a function call: run from the chain to the first continuation")
    ranges = [(0x7E56C6A5, 0x7E56C6B8), (0x7E880F8D, 0x7E880FC2), (0x7ECB0888, 0x7ECB0A00)]
    EXITS = {0x7E56C6B8: "table1", 0x7E56C6C3: "table2", 0x7E56C764: "apply", 0x7E56C76B: "none"}

    def rows(self):
        return [dict(art=a) for a in range(256)]

    def run(self, emu, row):
        import json as _json, os as _os, tempfile as _tf
        from omemu import SP0, EmuError
        emu.req("reset", regs={"pc": self.entry, "sp": SP0, "mdr": 0, "psw": 0, "d0": row["art"], "d3": 0x55AA})
        fd, tfile = _tf.mkstemp(suffix=".jsonl", prefix="omemu-trace-")
        _os.close(fd)
        emu.req("trace", exec=tfile, format="jsonl")
        try:
            r = emu.req("cont", stops=list(self.EXITS))
        finally:
            emu.req("trace", off=True)
        rg = emu.regs_of(r)
        pcs = {int(_json.loads(l)["pc"], 16) for l in open(tfile)}
        _os.unlink(tfile)
        if r["stop"] != "break" or rg["pc"] not in self.EXITS:
            raise EmuError(f"stop {r['stop']} at pc 0x{rg['pc']:08x}")
        pcs.discard(rg["pc"])
        out = {"exit": self.EXITS[rg["pc"]], "d0": rg["d0"], "sp_ok": rg["sp"] == SP0, "_r": {"pcs": pcs}}
        if out["exit"] == "apply":
            out["a1"] = f"0x{rg['a1']:08x}"
            out["a0"] = f"0x{rg['a0']:08x}"
        return out

    T3 = 0x7E880FC2
    SLOTS7 = {(85, 87): 0x7E768F46, (72, 81): 0x7E768F58, (70, 79): 0x7E880FC2}           # + the tables of code area 2, read from the image

    @staticmethod
    def decode_chain(image, pc):
        """{art code: matrix table} of a chooser made of `cmp imm,d0 / beq stub` runs, each ended by a jump to the next
        run or to M_NONE; a stub is `mov <table>,a1` (then a branch to the common tail)."""
        out = {}
        for _ in range(8):                                   # at most 8 chained runs
            while True:
                o = pc - BASE
                if image[o] == 0xA0:                         # cmp imm8,d0
                    code, n = image[o + 1], 2
                elif image[o:o + 2] == b"\xfa\xc8":          # cmp imm16,d0
                    code, n = struct.unpack_from("<H", image, o + 2)[0], 4
                else:
                    break
                assert image[o + n] == 0xC8, "beq expected"
                stub = pc + n + struct.unpack_from("<b", image, o + n + 1)[0]
                assert image[stub - BASE:stub - BASE + 2] == b"\xfc\xdd", "stub is not mov imm32,a1"
                out[code] = struct.unpack_from("<I", image, stub - BASE + 2)[0]
                pc += n + 2
            o = pc - BASE
            if image[o] == 0xCA:                             # bra rel8 to the next run
                pc = pc + struct.unpack_from("<b", image, o + 1)[0]
            elif image[o] == 0xDC:                           # jmp rel32: next run or M_NONE
                pc = (pc + struct.unpack_from("<i", image, o + 1)[0]) & U32
            else:
                raise RuntimeError(f"chooser: unexpected byte at 0x{pc:08x}")
            if pc == 0x7E56C76B:
                return out
        raise RuntimeError("chooser does not end at M_NONE")

    def model(self, row, image):
        a = row["art"]
        if img_u8(image, self.entry) == 0xDC:               # patched: a jump to matrix3 or matrix7
            target = (self.entry + struct.unpack_from("<i", image, self.entry - BASE + 1)[0]) & U32
            if target == 0x7E880F8D:                        # matrix3 (three films)
                if a in (85, 87):
                    return {"exit": "table1", "d0": a, "sp_ok": True}
                if a in (72, 81):
                    return {"exit": "table2", "d0": a, "sp_ok": True}
                if a in (70, 79):
                    return {"exit": "apply", "a1": "0x7e880fc2", "a0": "0x000055aa", "d0": a, "sp_ok": True}
                return {"exit": "none", "d0": a, "sp_ok": True}
            # a generated chooser (matrix7 / matrix12): decode its compare chains from the image
            tabs = self.decode_chain(image, target)
            if a in tabs:
                return {"exit": "apply", "a1": f"0x{tabs[a]:08x}", "a0": "0x000055aa", "d0": a, "sp_ok": True}
            return {"exit": "none", "d0": a, "sp_ok": True}
        t1 = (img_u8(image, 0x7E56C6A6), img_u8(image, 0x7E56C6AA)); t2 = (img_u8(image, 0x7E56C6AE), img_u8(image, 0x7E56C6B2))
        return {"exit": "table1" if a in t1 else "table2" if a in t2 else "none", "d0": a, "sp_ok": True}


# ---- menu entry -> art code (film-portra NOTES §33) -----------------------------------------------------------
class FilterType(Case):
    name, entry = "filter_type", 0x7E71BD94
    doc = ("art_GetFilterType: d0 = stored picture mode (100..120), d1 = type (1..3) -> d0 = internal art code, or "
           "0xFFFF. Its three log / trace helpers are stubbed")
    ranges = [(0x7E71BD94, 0x7E71BEC7), (0x7ECB0888, 0x7ECB0A00)]
    STOCK = {100: (70, 102), 101: (69,), 102: (71, 145), 103: (72,), 104: (74, 104), 105: (73, 106, 108), 106: (86,),
             107: (85, 167), 108: (91,), 109: (96, 165), 110: (145,), 111: (75,), 112: (84,), 113: (69,), 114: (117,),
             115: (118,), 116: (119,), 117: (151,), 118: (153,), 119: (163, 169), 120: (181, 182)}
    ONE_TYPE = (101, 103, 106, 108, 110, 111, 112, 113, 114, 115, 116, 117, 118)        # the type is not looked at
    STOCK_SHA = "361e4c7ae09f5575"                                # the function and its jump table in stock v1.6
    _seen = [None, None]

    def stubs(self, row):
        nop = lambda emu, r: {}
        return {0x7E71C634: nop, 0x7E71CB30: nop, 0x7E71CB08: nop}

    def rows(self):
        return [dict(mode=m, type=t) for m in range(98, 123) for t in (1, 2, 3)]

    def run(self, emu, row):
        r = emu.call(self.entry, {"d0": row["mode"], "d1": row["type"]}, stubs=self.stubs(row))
        return {"code": r["regs"]["d0"] & 0xFFFF, "_r": r}

    def model(self, row, image):
        if self._seen[0] is not image:                    # hash once per image: the whole function and its jump table
            self._seen[:] = [image, hashlib.sha256(image[0x7E71BD94 - BASE:0x7E71BEC7 - BASE] + image[0x7E854A24 - BASE:0x7E854A24 - BASE + 84]).hexdigest()[:16]]
        if self._seen[1] != self.STOCK_SHA:
            return None                                   # patched mapping: compare by diff
        m, t = row["mode"], row["type"]
        if m not in self.STOCK:
            return {"code": 0xFFFF}
        c = self.STOCK[m]
        if m in self.ONE_TYPE:
            return {"code": c[0]}
        return {"code": c[t - 1] if t <= len(c) else 0xFFFF}


# ---- record-side filter classification (film-portra NOTES §34) ------------------------------------------------
class ArtKind(Case):
    name, entry = "art_kind", 0x7E70DBDE
    doc = ("Record code: how a picture is handled, by stored picture mode (0x7E70DBDE, d0 = mode) and by art code "
           "(0x7E70DBB6 reads the halfword at ctx+16456, 0x7E70E298 the one at ctx+16460). Output: the three values")
    ranges = [(0x7E70DBB6, 0x7E70DC05), (0x7E70E298, 0x7E70E2E2)]
    CTX = DATA

    def rows(self):
        return [dict(kind="mode", v=m) for m in range(98, 123)] + [dict(kind="code", v=c) for c in range(60, 190)]

    def run(self, emu, row):
        if row["kind"] == "mode":
            r = emu.call(0x7E70DBDE, {"d0": row["v"]}, frame=(0, 0))
            return {"by_mode": r["regs"]["d0"] & 0xFFFF, "_r": r}
        emu.write(self.CTX + 16456, struct.pack("<H", row["v"]))
        emu.write(self.CTX + 16460, struct.pack("<H", row["v"]))
        r1 = emu.call(0x7E70DBB6, {"a0": self.CTX}, frame=(0, 0))
        r2 = emu.call(0x7E70E298, {"a0": self.CTX}, frame=(0, 0))
        return {"by_code": r1["regs"]["d0"] & 0xFFFF, "by_code2": r2["regs"]["d0"] & 0xFFFF, "_r": {"pcs": r1["pcs"] | r2["pcs"]}}


class SixHandler(Case):
    name, entry = "six_handler", 0x7E56D1C3
    doc = ("Six-axis stage, per-art-code handler only: entered at the jump-table target (0x7E78C254, code - 9) of each "
           "code that has a record handler, with d3 = art code; runs to the common tail 0x7E56D8D8 (reports the two "
           "record addresses in a3 / a2) or to the Cross Process statistics path 0x7E56D5F5, which goes on to read "
           "image planes through the pointer at P+16 (set by stock code only for picture modes 104 and 107)")
    ranges = [(0x7E56D1C3, 0x7E56D9E8), (0x7E880FD4, 0x7E881000)]
    TAIL, STATS, JT = 0x7E56D8D8, 0x7E56D5F5, 0x7E78C254

    def rows(self):
        return [dict(art=a) for a in (69, 70, 71, 72, 73, 79, 80, 81, 85, 86, 87, 91, 102, 103, 145, 146, 167, 168)]

    def run(self, emu, row):
        import json as _json, os as _os, tempfile as _tf
        from omemu import SP0, EmuError
        h = struct.unpack_from("<I", emu.image, self.JT + 4 * (row["art"] - 9) - BASE)[0]
        emu.req("reset", regs={"pc": h, "sp": SP0, "mdr": 0, "psw": 0, "d3": row["art"], "d2": 0, "a3": 0, "a2": 0})
        fd, tfile = _tf.mkstemp(suffix=".jsonl", prefix="omemu-trace-")
        _os.close(fd)
        emu.req("trace", exec=tfile, format="jsonl")
        try:
            r = emu.req("cont", stops=[self.TAIL, self.STATS])
        finally:
            emu.req("trace", off=True)
        rg = emu.regs_of(r)
        pcs = {int(_json.loads(l)["pc"], 16) for l in open(tfile)}
        _os.unlink(tfile)
        if r["stop"] != "break" or rg["pc"] not in (self.TAIL, self.STATS):
            raise EmuError(f"stop {r['stop']} at pc 0x{rg['pc']:08x}")
        pcs.discard(rg["pc"])
        return {"handler": f"0x{h:08x}", "exit": "tail" if rg["pc"] == self.TAIL else "statistics (reads P+16)", "records": [f"0x{rg['a3']:08x}", f"0x{rg['a2']:08x}"],
                "d3_kept": rg["d3"] == row["art"], "sp_ok": rg["sp"] == SP0, "_r": {"pcs": pcs}}


CASES = {c.name: c for c in (Memcpy(), Strlen(), RecLimit(), CurveSelect(), GammaSelect(), MatrixChoice(), FilterType(), ArtKind(), SixHandler())}


# ---- H.264 QP bounds and the software QP choice (experiments/2026-11-12-hardware/05-qp-floor.md) ----------------
from omemu import SP0  # noqa: E402
QP_CTX, QP_OBJ, QP_VT, QP_FAKE, QP_OUT, QP_DRV = DATA + 0x10000, DATA + 0x11000, DATA + 0x11100, DATA + 0x11200, DATA + 0x12000, DATA + 0x13000
QP_RC = [(0x7EEA6B37, 0x7EEA7266), (0x7EEA726B, 0x7EEA7995)]          # the two software QP functions


def qp_ctx(emu, hist, frame=3, first_flag=0):
    """Engine context: 1920x1080, 20 Mb/s, 29.97 fps, rate mode ctx+96 = 1, QP history bytes at ctx+635..638.
    ctx+68 -> an object whose vtable entries all point at QP_FAKE (`clr d0; rets`)."""
    ctx = bytearray(0x1000)
    for off, fmt, v in ((68, "<I", QP_OBJ), (28, "<I", 20_000_000), (48, "<I", 2997), (12, "<I", 1920), (16, "<I", 1080),
                        (108, "<H", 1), (52, "<I", frame), (96, "<I", 1), (104, "<I", first_flag)):
        struct.pack_into(fmt, ctx, off, v)
    ctx[634] = 1
    ctx[635:639] = bytes(hist)
    emu.write(QP_CTX, ctx)
    emu.write(QP_OBJ, struct.pack("<I", QP_VT))
    emu.write(QP_VT, struct.pack("<32I", *([QP_FAKE] * 32)))
    emu.write(QP_FAKE, b"\x00\xf0\xfc")


def qp_mean(hist, frame):
    """0x7EEA6B37 with ctx+634 = 1: frame 0 -> the default 33 (out+25); else the integer mean of the non-zero
    history bytes (33 if none), clamped to 51 (0x7EEA725A)."""
    h = [q for q in hist if q]
    q = 33 if frame == 0 or not h else sum(h) // len(h)
    return min(q, 51)


class QpSetup(Case):
    name, entry = "qp_setup", 0x7EEA57D4
    doc = ("Encoder frame set-up: 0x7EEA57D4 (first frame after start, ctx+104 = 0) and 0x7EEA5C4C (every later frame) "
           "build the parameter struct for codec-driver vtable+20 / +24. Output: max QP, min QP, the frame QP and the "
           "byte after it, read back from the struct on the stack (sp+164+36/37/172/173 and sp+176+44/45/248/249)")
    ranges = [(0x7EEA57D4, 0x7EEA5C4A), (0x7EEA5C4C, 0x7EEA618F), (0x7EEA6A0B, 0x7EEA6AF3), (QP_FAKE, QP_FAKE + 3)] + QP_RC
    stubs_doc = [(QP_FAKE, "every codec-driver vtable entry (+56, +64, +20, +24): scratch code `clr d0; rets`, "
                           "so the driver and the hardware are not run; the struct stays on the dead stack")]
    BUILDERS = {"first": (0x7EEA57D4, 356, 164, (36, 37, 172, 173), 0x7EEA5A1F),
                "frame": (0x7EEA5C4C, 436, 176, (44, 45, 248, 249), 0x7EEA5EBB)}
    MIN_IMM = {"first": 0x7EEA5A20, "frame": 0x7EEA5EBC}
    MAX_IMM = {"first": 0x7EEA5A1B, "frame": 0x7EEA5EC1}

    def rows(self):
        return [dict(builder=b, hist=h) for b in ("first", "frame")
                for h in ([0, 0, 0, 0], [20, 20, 20, 20], [16, 17, 16, 18], [26, 28, 30, 32])]

    def run(self, emu, row):
        entry, frame, base, offs, min_pc = self.BUILDERS[row["builder"]]
        qp_ctx(emu, row["hist"], first_flag=0 if row["builder"] == "first" else 1)
        emu.write(DATA, b"\0" * 64)
        r = emu.call(entry, {"a0": QP_CTX, "a1": DATA})
        st = emu.read(SP0 - 16 - frame + base, 260)
        reads = [(min_pc + 1, 1)] if min_pc in r["pcs"] else []
        return {"ret": r["regs"]["d0"], "max_qp": st[offs[0]], "min_qp": st[offs[1]], "qp": st[offs[2]],
                "qp_b": st[offs[3]], "ctx104": emu.u32(QP_CTX + 104), "_r": r, "_reads": reads}

    def model(self, row, image):
        b = row["builder"]
        return {"ret": 0, "max_qp": img_u8(image, self.MAX_IMM[b]), "min_qp": img_u8(image, self.MIN_IMM[b]),
                "qp": qp_mean(row["hist"], 3), "qp_b": 16, "ctx104": 1 if b == "first" else 2}


class QpRc(Case):
    name, entry = "qp_rc", 0x7EEA6B37
    doc = ("Software QP choice 0x7EEA6B37(a0 ctx, a1 out): out+16 = the next frame QP proposed to the hardware. "
           "It averages the last 4 QPs the hardware reported (ctx+635..638); it reads no frame size and no QP floor")
    ranges = [QP_RC[0]]

    def rows(self):
        return [dict(hist=h, frame=f) for h in ([0, 0, 0, 0], [20, 20, 20, 20], [16, 17, 16, 18], [25, 20, 20, 20],
                                                [26, 28, 30, 32], [60, 60, 60, 60], [12, 0, 0, 0]) for f in (0, 3)]

    def run(self, emu, row):
        qp_ctx(emu, row["hist"], frame=row["frame"])
        out = bytearray(32)
        out[25] = 33                                         # the caller's default QP (0x7EEA58D8 / 0x7EEA5356)
        emu.write(QP_OUT, out)
        r = emu.call(self.entry, {"a0": QP_CTX, "a1": QP_OUT})
        o = emu.read(QP_OUT, 32)
        return {"ret": r["regs"]["d0"], "qp": o[16], "_r": r, "_reads": [(lo, hi - lo) for lo, hi in self.ranges]}

    def model(self, row, image):
        return {"ret": 0, "qp": qp_mean(row["hist"], row["frame"])}


class QpSizeModel(Case):
    name, entry = "qp_size_model", 0x7EEA3E0A
    doc = ("Codec-driver status getter (vtable+28) 0x7EEA3E0A(a0 drv, a1 out, d0 1): after a frame it re-estimates the "
           "driver's first-frame QP byte drv+218 from the frame size: smallest q with Qstep[q] > Qstep[qp]*(size>>10)/168 "
           "(table 0x7F03026C), or qp+15 (max 51) on an overflow flag. Called here with `call [],0`")
    ranges = [(0x7EEA3E0A, 0x7EEA3FE7)]
    S_STAT, S_WAIT = 0x7EEC6B01, 0x7EEC684A
    stubs_doc = [(S_STAT, "hardware status read (MMIO 0x994043xx): writes the row's size word at +4, overflow flag at "
                          "+28 and reported QP 20 at +12 into the buffer at a0; returns 301"),
                 (S_WAIT, "codec wait: returns 300")]
    QSTEP = 0x7F03026C

    def rows(self):
        return [dict(qp=q, size=s, ovf=0) for q in (20, 33) for s in (0, 20_000, 75_000, 200_000, 600_000, 2_000_000)] + \
               [dict(qp=q, size=75_000, ovf=1) for q in (20, 36, 40)]

    def stubs(self, row):
        def stat(emu, r):
            st = bytearray(36)
            struct.pack_into("<I", st, 4, row["size"])
            st[12] = 20
            struct.pack_into("<I", st, 28, row["ovf"])
            emu.write(r["a0"], st)
            return {"d0": 301}
        return {self.S_STAT: stat, self.S_WAIT: lambda emu, r: {"d0": 300}}

    def run(self, emu, row):
        drv = bytearray(0x400)
        drv[218] = row["qp"]
        emu.write(QP_DRV, drv)
        emu.write(QP_OUT, b"\0" * 32)
        r = emu.call(self.entry, {"a0": QP_DRV, "a1": QP_OUT, "d0": 1}, frame=(0, 0), stubs=self.stubs(row))
        return {"new_qp": emu.read(QP_DRV + 218, 1)[0], "reported_qp": emu.read(QP_OUT + 8, 1)[0], "_r": r,
                "_reads": [(self.QSTEP, 104)] + [(lo, hi - lo) for lo, hi in self.ranges]}

    def model(self, row, image):
        q = row["qp"]
        if row["ovf"]:
            return {"new_qp": 51 if q > 36 else q + 15, "reported_qp": 20}
        t = struct.unpack_from("<52H", image, self.QSTEP - BASE)
        lim = t[q] * (row["size"] >> 10) // 168
        return {"new_qp": next((i for i in range(52) if t[i] > lim), 51), "reported_qp": 20}


CASES.update({c.name: c for c in (QpSetup(), QpRc(), QpSizeModel())})


# ---- movie bitrate: the table, the encoder's parameter check, the derived encoder fields ------------------------
# (experiments/2026-11-12-hardware/06-bitrate-and-limit.md)
def imm32_at(image, addr, prefix):
    o = addr - BASE
    assert image[o:o + 2] == prefix, f"0x{addr:08x}: {image[o:o + 2].hex()} is not {prefix.hex()}"
    return struct.unpack_from("<I", image, o + 2)[0]


class RateTable(Case):
    name, entry = "rate_table", 0x7E6EE4D5
    doc = ("Bitrate table inside the record-request builder 0x7E6EE4A2: entered at 0x7E6EE4D5 with a2 = the record "
           "descriptor {format, quality, fine} (0x605B1CC4 on the camera) and a0 = a buffer whose byte 3 is the art mode; "
           "run to 0x7E6EE5E3 (table done) or 0x7E6EE5DC (the error print). Output: peak 0xA0753564 and average "
           "0xA0753568. Not a function call")
    ranges = [(0x7E6EE4D5, 0x7E6EE5E3)]
    DESC, ART = DATA, DATA + 0x100
    REQ = 0xA0753560
    EXITS = {0x7E6EE5E3: "ok", 0x7E6EE5DC: "error"}
    SITES = (0x7E6EE510, 0x7E6EE51C, 0x7E6EE52C, 0x7E6EE538, 0x7E6EE540, 0x7E6EE54C, 0x7E6EE583, 0x7E6EE58B,
             0x7E6EE59A, 0x7E6EE5A2, 0x7E6EE5AA)                  # every `mov imm32,d0` of the table
    MOV = {(6, 1): 0x7E6EE583, (6, 0): 0x7E6EE58B, (3, 1): 0x7E6EE59A, (3, 0): 0x7E6EE5A2, (4, 1): 0x7E6EE5AA,
           (4, 0): 0x7E6EE5AA}
    AVCHD = {(5, 1): (0x7E6EE510, 0x7E6EE51C), (5, 0): (0x7E6EE52C, 0x7E6EE538), (3, 1): (0x7E6EE52C, 0x7E6EE538),
             (3, 0): (0x7E6EE540, 0x7E6EE54C)}

    def rows(self):
        return [dict(fmt=f, q=q, fine=h) for f, qs in ((3, (6, 3, 4, 5, 7)), (2, (5, 3, 4)), (1, (6,)))
                for q in qs for h in (1, 0)]

    def run(self, emu, row):
        import json as _json, os as _os, tempfile as _tf
        from omemu import SP0, EmuError
        emu.write(self.DESC, bytes([row["fmt"], row["q"], row["fine"], 0]))
        emu.write(self.ART, b"\0" * 8)
        emu.write(self.REQ, b"\xee" * 16)
        emu.req("reset", regs={"pc": self.entry, "sp": SP0, "mdr": 0, "psw": 0, "a0": self.ART, "a2": self.DESC})
        fd, tfile = _tf.mkstemp(suffix=".jsonl", prefix="omemu-trace-")
        _os.close(fd)
        emu.req("trace", exec=tfile, format="jsonl")
        try:
            r = emu.req("cont", stops=list(self.EXITS))
        finally:
            emu.req("trace", off=True)
        rg = emu.regs_of(r)
        pcs = {int(_json.loads(l)["pc"], 16) for l in open(tfile)}
        _os.unlink(tfile)
        if r["stop"] != "break" or rg["pc"] not in self.EXITS:
            raise EmuError(f"stop {r['stop']} at pc 0x{rg['pc']:08x}")
        pcs.discard(rg["pc"])
        req = emu.read(self.REQ, 12)
        return {"exit": self.EXITS[rg["pc"]], "fmt_q": [req[0], req[1]], "peak": struct.unpack_from("<I", req, 4)[0],
                "avg": struct.unpack_from("<I", req, 8)[0], "_r": {"pcs": pcs},
                "_reads": [(a, 6) for a in self.SITES if a in pcs]}    # the table instructions this row ran

    def model(self, row, image):
        f, q, h = row["fmt"], row["q"], row["fine"]
        none = {"exit": "error", "fmt_q": [f, q], "peak": 0xEEEEEEEE, "avg": 0xEEEEEEEE}
        k = (q, 1 if h == 1 else 0)
        if f == 3 and k in self.MOV:
            v = imm32_at(image, self.MOV[k], b"\xfc\xcc")
            return {"exit": "ok", "fmt_q": [f, q], "peak": v, "avg": v}
        if f == 2 and k in self.AVCHD:
            pk, av = self.AVCHD[k]
            return {"exit": "ok", "fmt_q": [f, q], "peak": imm32_at(image, pk, b"\xfc\xcc"),
                    "avg": imm32_at(image, av, b"\xfc\xcc")}
        return none


class EncParamCheck(Case):
    name, entry = "enc_param_check", 0x7EEA338C
    doc = ("Video Encode parameter check 0x7EEA338C(a0 engine; struct by value at caller sp+4: fps u16, width, height, "
           "average b/s, flag, peak b/s, mode), called from 0x7EEA8DCD. d0 = 0 accepted, 0xAB010002 rejected. "
           "Engine limits: +132 width 1920, +136 height 1088, +140 fps 6000")
    ranges = [(0x7EEA338C, 0x7EEA3420)]
    OBJ = DATA + 0x3000
    CAP_AT = 0x7EEA33CB                      # cmp imm32,d0 (fc c8 imm32): the peak cap
    REJECT = 0xAB010002
    BASE_ROW = dict(fps=2997, w=1920, h=1080, flag=0, mode=1)

    def rows(self):
        rows = [dict(self.BASE_ROW, avg=p, peak=p) for p in
                (4_000_000, 10_000_000, 16_000_000, 17_000_000, 20_000_000, 24_000_000, 24_000_001, 32_000_000,
                 49_999_999, 50_000_000, 50_000_001, 62_500_000, 0xFFFFFFFF)]
        rows += [dict(self.BASE_ROW, avg=20_000_000, peak=32_000_000), dict(self.BASE_ROW, avg=32_000_001, peak=32_000_000),
                 dict(self.BASE_ROW, avg=24_000_000, peak=24_000_000, flag=1), dict(self.BASE_ROW, avg=1, peak=1, flag=2),
                 dict(self.BASE_ROW, avg=20_000_000, peak=20_000_000, mode=0),
                 dict(self.BASE_ROW, avg=20_000_000, peak=20_000_000, mode=3),
                 dict(self.BASE_ROW, avg=20_000_000, peak=20_000_000, fps=99),
                 dict(self.BASE_ROW, avg=20_000_000, peak=20_000_000, fps=6001),
                 dict(self.BASE_ROW, avg=20_000_000, peak=20_000_000, w=1921),
                 dict(self.BASE_ROW, avg=20_000_000, peak=20_000_000, h=63)]
        return rows

    def run(self, emu, row):
        obj = bytearray(256)
        for off, v in ((132, 1920), (136, 1088), (140, 6000)):
            struct.pack_into("<I", obj, off, v)
        emu.write(self.OBJ, obj)
        r = emu.call(self.entry, {"a0": self.OBJ},
                     stack=[row["fps"], row["w"], row["h"], row["avg"], row["flag"], row["peak"], row["mode"]])
        # no _reads: every row reads the cap, but only peaks between the old and new cap change; the per-image model
        # (which reads the cap from the image) is the check
        return {"d0": r["regs"]["d0"], "accepted": r["regs"]["d0"] == 0, "_r": r}

    def model(self, row, image):
        cap = imm32_at(image, self.CAP_AT, b"\xfc\xc8")
        bad = (row["fps"] < 100 or row["fps"] > 6000 or row["w"] > 1920 or row["h"] > 1088 or row["w"] < 64
               or row["h"] < 64 or row["peak"] > cap or row["peak"] < row["avg"] or row["flag"] not in (0, 1)
               or row["mode"] not in (1, 2, 3))
        return {"d0": self.REJECT if bad else 0, "accepted": not bad}


class EncRateFields(Case):
    name, entry = "enc_rate_fields", 0x7EEA57D4
    doc = ("Rate fields the encoder set-ups 0x7EEA57D4 (first frame) and 0x7EEA5C4C (later frames) derive from the "
           "average bitrate ctx+28 (= the table value on MOV): the target in kb/s, the two HRD-style kb/s - 1 fields and "
           "the 6/2 class (>= 15,500,000). Same context and stubs as qp_setup, ctx+28 = the row's rate")
    ranges = QpSetup.ranges
    stubs_doc = QpSetup.stubs_doc
    # builder: (entry, frame, struct base, offsets of kb/s, class, hrd1, hrd2)
    BUILDERS = {"first": (0x7EEA57D4, 356, 164, 32, 112, 184, 188), "frame": (0x7EEA5C4C, 436, 176, 40, 92, 252, 256)}
    RATES = (4_000_000, 10_000_000, 13_000_000, 15_499_999, 15_500_000, 16_000_000, 17_000_000, 20_000_000,
             24_000_000, 32_000_000, 50_000_000)

    def rows(self):
        return [dict(builder=b, rate=r) for b in ("first", "frame") for r in self.RATES]

    def run(self, emu, row):
        entry, frame, base, o_kb, o_cls, o_h1, o_h2 = self.BUILDERS[row["builder"]]
        qp_ctx(emu, [20, 20, 20, 20], first_flag=0 if row["builder"] == "first" else 1)
        emu.write(QP_CTX + 28, struct.pack("<I", row["rate"]))
        emu.write(DATA, b"\0" * 64)
        r = emu.call(entry, {"a0": QP_CTX, "a1": DATA})
        st = emu.read(SP0 - 16 - frame + base, 264)
        u = lambda o: struct.unpack_from("<I", st, o)[0]
        return {"ret": r["regs"]["d0"], "kbps": u(o_kb), "cls": u(o_cls), "hrd_m1": [u(o_h1), u(o_h2)],
                "hrd_bps_x1024": (u(o_h1) + 1) << 10, "_r": r}

    def model(self, row, image):
        kb = row["rate"] // 1000
        return {"ret": 0, "kbps": kb, "cls": 6 if row["rate"] >= 15_500_000 else 2, "hrd_m1": [kb - 1, kb - 1],
                "hrd_bps_x1024": kb << 10}


CASES.update({c.name: c for c in (RateTable(), EncParamCheck(), EncRateFields())})


# ---- interval shooting / time-lapse menu row and guards (experiments/2026-11-13-intervalometer) ----------------
DATA_ROM = 0x1E6304C0             # ROM image of .data = RAM + this (0x7E8DA000 -> 0x602A9B40, map section 01)
TOP_TABLE = 0x7EFFE13C            # top-menu rows {u16 item, label, help, kind, param}, 1-based global row numbers
TAB_ROWS, TAB_COUNT, TAB_HELP = 0x602BE3CE, 0x602BE446, 0x602BE44C   # .data: 6 x 20-byte row lists, 6 counts, tab helps
CUR_TAB, CUR_ROW, HELP_TOGGLE = 0x602BE48C, 0x602BE490, 0x602BE4AC   # u16 current tab, current row (-1 = tab bar)
TAB_PAGES = 0x7EFF8BAC            # page 1 child list {u32 page, u32 kind}: tab -> page 2..7
PAGE_RECS = 0x7EFFA44C            # 40-byte page/panel records {id, -15, type, 1, 1|2, children*, ...}, id 0 ends


def load_data(emu, ram, n):
    """Copy the image's .data initial bytes for RAM [ram, ram+n) into emulator RAM (.data is not preloaded)."""
    o = ram + DATA_ROM - BASE
    emu.write(ram, emu.image[o:o + n])


def tab_rows(image, tab):
    o = TAB_ROWS + DATA_ROM - BASE
    n = image[TAB_COUNT + DATA_ROM - BASE + tab]
    return list(image[o + 20 * tab:o + 20 * tab + n])


def top_row(image, row):
    return struct.unpack_from("<5H", image, TOP_TABLE - BASE + 10 * (row - 1))


def page_child(image, page, idx):
    """child panel id of entry idx of the page's 12-byte child list (pages 2..7)."""
    a = PAGE_RECS
    while True:
        rid = struct.unpack_from("<I", image, a - BASE)[0]
        if rid == 0:
            return None
        if rid == page:
            kids = struct.unpack_from("<I", image, a - BASE + 20)[0]
            return struct.unpack_from("<H", image, kids - BASE + 12 * idx)[0]
        a += 40


def menu_rows():
    return [dict(tab=t, row=-1) for t in range(6)] + [dict(tab=t, row=r) for t, n in enumerate((6, 5, 6, 10, 3, 6))
                                                      for r in range(n)]


class MenuHelp(Case):
    name, entry = "menu_help", 0x7EDEC745
    doc = ("main-menu help/DM writer: from the current tab (0x602BE48C) and row (0x602BE490), takes the help "
           "string of the top-menu row (tab row list in .data -> 1-based global row -> TOP_TABLE+10*(row-1)+4) or the "
           "tab's own help (row -1), and stores {toggle, 0, help} as DM block 45")
    ranges = [(0x7EDEC745, 0x7EDEC7C3)]
    S_MEMSET, S_DM = 0x7E500D73, 0x7ECEF667
    stubs_doc = [(S_MEMSET, "memset(a0, d0, d1): done in Python"),
                 (S_DM, "DM set (d0 block 45, d1 size 4, a0 buffer, a1 1): the buffer is captured")]

    def rows(self):
        return menu_rows()

    def run(self, emu, row):
        load_data(emu, TAB_ROWS, 0x90)
        emu.write(CUR_TAB, struct.pack("<H", row["tab"]))
        emu.write(CUR_ROW, struct.pack("<h", row["row"]))
        emu.write(HELP_TOGGLE, b"\0\0")
        cap = {}

        def memset(e, r):
            e.write(r["a0"], bytes([r["d0"] & 0xFF]) * (r["d1"] & 0xFFFF))
            return {}

        def dm(e, r):
            cap["blk"], cap["buf"] = r["d0"], e.read(r["a0"], 4)
            return {"d0": 0}
        r = emu.call(self.entry, stubs={self.S_MEMSET: memset, self.S_DM: dm})
        g = tab_rows(emu.image, row["tab"])[row["row"]] if row["row"] >= 0 else 0
        out = {"block": cap.get("blk"), "help": struct.unpack_from("<H", cap["buf"], 2)[0], "_r": r}
        if g:
            out["_reads"] = [(TOP_TABLE + 10 * (g - 1) + 4, 2)]
            out["grow"] = g
        else:
            out["_reads"] = []
        return out

    def model(self, row, image):
        if row["row"] < 0:
            return {"block": 45, "help": struct.unpack_from("<H", image, TAB_HELP + DATA_ROM - BASE + 2 * row["tab"])[0]}
        g = tab_rows(image, row["tab"])[row["row"]]
        return {"block": 45, "help": top_row(image, g)[2], "grow": g}


class MenuChild(Case):
    name, entry = "menu_child", 0x7EDEC618
    doc = ("main-menu current item: tab -> page (page-1 child list 0x7EFF8BAC), page record lookup 0x7EDCCA8C, "
           "then the page's 12-byte child list [row] -> the panel that OK / right opens (0 for the tab bar)")
    ranges = [(0x7EDEC618, 0x7EDEC663), (0x7EDCCA8C, 0x7EDCCABB)]

    def rows(self):
        return menu_rows()

    def run(self, emu, row):
        emu.write(CUR_TAB, struct.pack("<H", row["tab"]))
        emu.write(CUR_ROW, struct.pack("<h", row["row"]))
        r = emu.call(self.entry)
        out = {"panel": r["regs"]["d0"] & 0xFFFF, "_r": r}
        if row["row"] >= 0:
            page = struct.unpack_from("<I", emu.image, TAB_PAGES - BASE + 8 * row["tab"])[0]
            a = PAGE_RECS
            while struct.unpack_from("<I", emu.image, a - BASE)[0] != page:
                a += 40
            kids = struct.unpack_from("<I", emu.image, a - BASE + 20)[0]
            out["_reads"] = [(kids + 12 * row["row"], 2)]
        else:
            out["_reads"] = []
        return out

    def model(self, row, image):
        if row["row"] < 0:
            return {"panel": 0}
        page = struct.unpack_from("<I", image, TAB_PAGES - BASE + 8 * row["tab"])[0]
        return {"panel": page_child(image, page, row["row"])}


class MenuValue(Case):
    name, entry = "menu_value", 0x7EDEC2C0
    doc = ("main-menu right-column value of a global row (d0): reads the row's setting through getSetting 0x7EE01D38 "
           "and maps it to a string id with 0x7EE01DDA (per-row {value, string} lists through the .data pointer table "
           "0x602BE874); writes the string id to (a3 = d1)")
    ranges = [(0x7EDEC2C0, 0x7EDEC50E), (0x7EE01DDA, 0x7EE01E1E)]
    S_GET = 0x7EE01D38
    PTRS = 0x602BE874
    stubs_doc = [(S_GET, "getSetting(d0 id, a0 out): writes the row's value to *a0; the id is logged")]
    ROWS = (3, 5, 6, 7, 10, 11, 13, 32)       # row 8 (IS) has a NULL value list in .data: the formatter reads address 0
    IMM = {3: 0x7EDEC2D1, 5: 0x7EDEC2E5, 7: 0x7EDEC2FA, 8: 0x7EDEC30F, 10: 0x7EDEC324, 11: 0x7EDEC339,
           6: 0x7EDEC34E, 13: 0x7EDEC362, 32: 0x7EDEC424}

    def rows(self):
        return [dict(grow=g, value=v) for g in self.ROWS for v in (0, 1)]

    def run(self, emu, row):
        load_data(emu, self.PTRS, 4 * 40)
        emu.write(DATA, b"\x01" + b"\0" * 63)
        ids = []

        def get(e, r):
            ids.append(r["d0"] & 0xFFFF)
            e.write(r["a0"], struct.pack("<I", row["value"]))
            return {"d0": 0}
        r = emu.call(self.entry, {"d0": row["grow"], "a1": DATA, "d1": DATA + 0x20}, stubs={self.S_GET: get})
        return {"setting": ids, "string": struct.unpack_from("<H", emu.read(DATA + 0x20, 2))[0], "_r": r,
                "_reads": [(self.IMM[row["grow"]], 3)]}

    def model(self, row, image):
        a = self.IMM[row["grow"]]
        o = a - BASE
        assert image[o] in (0x2C, 0x80, 0xFA), hex(image[o])
        info = image[o + 1] if image[o] == 0x80 else struct.unpack_from("<H", image, o + 1)[0]
        p = struct.unpack_from("<I", image, self.PTRS + DATA_ROM - BASE + 4 * row["grow"])[0]
        s = 0
        while p:
            v, sid = struct.unpack_from("<2I", image, p - BASE)
            if v == 0xFFFFFFF1:
                break
            if v == row["value"]:
                s = sid & 0xFFFF
                break
            p += 8
        return {"setting": [info], "string": s}


class IvlGuard(Case):
    name, entry = "ivl_guard", 0x7E969C11
    doc = ("isStartIntervalShootingEnable (guard=start, 0x7E969C11) and isCreateTimeLapseMovieEnable (guard=movie, "
           "0x7E969ACE): read info 482 and the shooting-state words; 1 = allowed")
    ENTRIES = {"start": 0x7E969C11, "movie": 0x7E969ACE}
    ranges = [(0x7E969ACE, 0x7E969B43), (0x7E969C11, 0x7E969C87), (0x7E96998B, 0x7E9699AA), (0x7E969A6A, 0x7E969A73)]
    S_GET, S_ST, S_PRN = 0x7E6FCC91, 0x7E96A499, 0x7E9670E9
    STATE, FLAG = 0x602B0CDC, 0x602B0D08
    stubs_doc = [(S_GET, "setting getter (d0 id): returns the row's 482; any other id is an error"),
                 (S_ST, "state test (d0 = 18 or 9): returns the row's s18 / s9"),
                 (S_PRN, "debug print: no output")]

    def rows(self):
        return [dict(guard=g, i482=a, s18=b, s9=c, flag=d, state=s) for g in ("start", "movie") for a in (0, 1)
                for b in (0, 1) for c in (0, 1) for d in (0, 1) for s in (0, 2, 4, 8, 6, 32)]

    def run(self, emu, row):
        emu.write(self.STATE, struct.pack("<I", row["state"]))
        emu.write(self.FLAG, struct.pack("<I", row["flag"]))
        ids = []

        def get(e, r):
            ids.append(r["d0"] & 0xFFFF)
            if r["d0"] & 0xFFFF != 482:
                raise RuntimeError(f"getter: unexpected id {r['d0']}")
            return {"d0": row["i482"]}

        def st(e, r):
            return {"d0": {18: row["s18"], 9: row["s9"]}[r["d0"] & 0xFFFF]}
        r = emu.call(self.ENTRIES[row["guard"]], frame=(0, 8),
                     stubs={self.S_GET: get, self.S_ST: st, self.S_PRN: lambda e, r: {}})
        return {"ok": r["regs"]["d0"], "ids": ids, "_r": r}

    def model(self, row, image):
        a, s = row["i482"], row["state"]
        if row["guard"] == "start":
            ok = a != 0 and row["s18"] != 1 and row["s9"] == 0 and row["flag"] != 1 and not s & 14
        else:
            ok = a != 0 and row["s18"] != 1 and not s & 32 and row["flag"] != 1 and (not s & 2 or bool(s & 12))
        return {"ok": int(ok), "ids": [482]}


CASES.update({c.name: c for c in (MenuHelp(), MenuChild(), MenuValue(), IvlGuard())})
