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
        return {"ret": r["regs"]["d0"], "free_frames": struct.unpack_from("<I", ctx, 32)[0],
                "free_frames2": struct.unpack_from("<I", ctx, 36)[0], "max_frames": struct.unpack_from("<I", ctx, 40)[0],
                "prints": prints, "_r": r}

    @staticmethod
    def limit_at(image, addr):
        """The imm16 of `mov imm16,a3` (27 lo hi) at addr."""
        o = addr - BASE
        assert image[o] == 0x27, f"no mov imm16,a3 at 0x{addr:08x}"
        return struct.unpack_from("<H", image, o + 1)[0]

    def model(self, row, image):
        fmt, q, hi, free = row["fmt"], row["q"], row["hi"], row["free"]
        lim_q4, lim_other = self.limit_at(image, 0x7E6EDEE0), self.limit_at(image, 0x7E6EDF20)
        rate, limit, a2 = 0, 0, 0          # a2: the caller's a2 (0 in this harness) where no reserve is set
        if fmt == 3:
            ov = 375
            a2 = {6: 832, 3: 832, 4: 2624}.get(q, 0)
            rate = {6: (4883, 4151), 3: (3174, 2442), 4: (977, 977)}.get(q, (0, 0))[0 if hi == 1 else 1]
            limit = lim_q4 if q == 4 else (lim_other if q in (6, 3) else 0)
        else:
            ov, a2 = 47, 400
            if fmt == 2 and q in (5, 3):
                rate = {5: (5860, 4711), 3: (4711, 4045)}[q][0 if hi == 1 else 1]
                limit = lim_other
        if free <= a2:
            t_free = clamped = 0
        else:
            t_free = (free - a2) // (rate + ov)
            t_cap = ((8388608 - a2) & U32) // (rate + ov)
            clamped = min(limit, t_cap, t_free)
        return {"ret": (t_free * 600) & U32, "free_frames": (t_free * 30) & U32, "free_frames2": (t_free * 30) & U32,
                "max_frames": (clamped * 30) & U32}


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
    ranges = [(0x7E71BD94, 0x7E71BEC7)]
    STOCK = {100: (70, 102), 101: (69,), 102: (71, 145), 103: (72,), 104: (74, 104), 105: (73, 106, 108), 106: (86,),
             107: (85, 167), 108: (91,), 109: (96, 165), 110: (145,), 111: (75,), 112: (84,), 113: (69,), 114: (117,),
             115: (118,), 116: (119,), 117: (151,), 118: (153,), 119: (163, 169), 120: (181, 182)}
    ONE_TYPE = (101, 103, 106, 108, 110, 111, 112, 113, 114, 115, 116, 117, 118)        # the type is not looked at

    def stubs(self, row):
        nop = lambda emu, r: {}
        return {0x7E71C634: nop, 0x7E71CB30: nop, 0x7E71CB08: nop}

    def rows(self):
        return [dict(mode=m, type=t) for m in range(98, 123) for t in (1, 2, 3)]

    def run(self, emu, row):
        r = emu.call(self.entry, {"d0": row["mode"], "d1": row["type"]}, stubs=self.stubs(row))
        return {"code": r["regs"]["d0"] & 0xFFFF, "_r": r}

    def model(self, row, image):
        if image[0x7E71BE39 - BASE:0x7E71BE3B - BASE] != b"\x8a\x4a":
            return None                                   # patched image: compare by diff
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


CASES = {c.name: c for c in (Memcpy(), Strlen(), RecLimit(), CurveSelect(), GammaSelect(), MatrixChoice(), FilterType(), ArtKind())}
