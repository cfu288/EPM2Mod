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


CASES = {c.name: c for c in (Memcpy(), Strlen(), RecLimit(), CurveSelect())}
