"""The 12-region stage (builder 0x7E56E186): table encoding, the probe's tables, and a forward model of the stage.

Research code. Labels as in NOTES.md: V = read in the firmware bytes or run in the emulator, I = inferred.

Table (3028 B, V: builder 0x7E56E186): 12 records of 28 B; then two groups of five curve arrays (records 0-5 at
+336, records 6-11 at +1680): u32[96], u32[96], u16[96], u16[96], u16[96]; then the enable mask (u16) at +3024.
Record: u16 hue start, hue width, chroma start, chroma width, luma start, luma width; s16 hue shift, saturation,
lightness; bytes 18-19 never read; bytes 20-25 = (mult, shift) of the hue, chroma and luma windows; 26-27 never read.
Each record owns 16 entries of each array: 7 curves of 16 points, a point = (level << 8) | (signed slope & 0xFF).
Curve slots (memory order): c0 = u32 lo, c1 = u32 hi of array 0; c2 = lo, c3 = hi of array 1; c4, c5, c6 = arrays
2, 3, 4. Roles from the stock tables (I, strong; the CURVES entry measures them): c0 hue x saturation,
c3 chroma x saturation, c2 chroma x lightness, c4 chroma x hue shift, c1 / c6 hue x (lightness / hue shift),
c5 luma, shared.
"""
from __future__ import annotations

import struct
import numpy as np

TABLE_BYTES, REC, MASK_AT = 3028, 28, 3024
GROUP = [(336, 720, 1104, 1296, 1488), (1680, 2064, 2448, 2640, 2832)]
HUE_TURN = 32768                     # 360 degrees (I, strong: stock "all hues" = start 0, width 32767)
DEG = HUE_TURN / 360.0
FULL = 63                            # the stock curves' top level

# axis of each slot under the stock-derived hypothesis; effect of each slot
SLOT_AXIS = ("hue", "hue", "chroma", "chroma", "chroma", "luma", "hue")
ROLES = {"S": (0, 3), "L": (1, 2), "H": (6, 4)}        # (hue slot, chroma slot); luma slot 5 shared
ROLES_SWAPPED = {"S": (0, 3), "L": (6, 2), "H": (1, 4)}


def ms(width: int) -> tuple[int, int]:
    """(mult, shift) with width * mult >> shift ~ 256, as the stock tables pick them (largest shift with mult < 256)."""
    if width == 0:
        return 0, 0
    best = (0, 0)
    for s in range(0, 24):
        m = round((256 << s) / width)
        if m <= 255:
            best = (m, s)
    return best


# ---- curve shapes: 17 values at p = 0, 16, ..., 256 ------------------------------------------------------------
FLAT = [FULL] * 17
TRAP = [0] + [FULL] * 15 + [0]                                   # 0 -> 63 in the first 16th, back to 0 in the last
RAMP = [round(FULL * i / 15) for i in range(16)] + [0]           # rises over the window, drops in the last 16th
ZERO = [0] * 17


def points(values, slopes=None):
    """16 curve points from 17 values (slope = next - this), or explicit (inconsistent) slopes."""
    v = [int(x) for x in values]
    sl = [v[i + 1] - v[i] for i in range(16)] if slopes is None else [int(s) for s in slopes]
    assert all(0 <= x <= 255 for x in v[:16]) and all(-128 <= s <= 127 for s in sl)
    return [((v[i] & 0xFF) << 8) | (sl[i] & 0xFF) for i in range(16)]


class Rec:
    """One record. Windows are (start, width) in record units; shapes per axis; per-slot overrides."""

    def __init__(self, hue=(0, 32767), chroma=(0, 1023), luma=(0, 1023), dh=0, ds=0, dl=0,
                 shapes=None, slot=None, msov=None, note=""):
        self.hue, self.chroma, self.luma = hue, chroma, luma
        self.dh, self.ds, self.dl = int(dh), int(ds), int(dl)
        sh = {"hue": FLAT, "chroma": FLAT, "luma": FLAT}
        sh.update(shapes or {})
        self.curves = [points(sh[SLOT_AXIS[k]]) for k in range(7)]
        for k, pts in (slot or {}).items():
            self.curves[k] = pts
        self.msov = msov or {}
        self.note = note

    def ms(self):
        out = []
        for ax, (s, w) in (("hue", self.hue), ("chroma", self.chroma), ("luma", self.luma)):
            out += list(self.msov.get(ax, ms(w)))
        return out


def deg(a: float) -> int:
    return int(round(a * DEG)) % HUE_TURN


def hue_win(lo: float, hi: float) -> tuple[int, int]:
    return deg(lo), int(round((hi - lo) * DEG))


def encode(recs: list[Rec | None], mask: int) -> bytes:
    t = bytearray(TABLE_BYTES)
    for i, r in enumerate(recs):
        if r is None:
            continue
        struct.pack_into("<6H3h", t, REC * i, r.hue[0], r.hue[1], r.chroma[0], r.chroma[1], r.luma[0], r.luma[1],
                         r.dh, r.ds, r.dl)
        t[REC * i + 20:REC * i + 26] = bytes(r.ms())
        g, j = divmod(i, 6)
        a0, a1, a2, a3, a4 = GROUP[g]
        c = r.curves
        for k in range(16):
            e = 16 * j + k
            struct.pack_into("<I", t, a0 + 4 * e, c[0][k] | (c[1][k] << 16))
            struct.pack_into("<I", t, a1 + 4 * e, c[2][k] | (c[3][k] << 16))
            struct.pack_into("<H", t, a2 + 2 * e, c[4][k])
            struct.pack_into("<H", t, a3 + 2 * e, c[5][k])
            struct.pack_into("<H", t, a4 + 2 * e, c[6][k])
    struct.pack_into("<H", t, MASK_AT, mask)
    return bytes(t)


def decode(t: bytes) -> dict:
    """-> dict(mask, recs=[dict(win=(3, 2) start/width, ms=(3, 2), eff=(dh, ds, dl), curves=(7, 16, 2) level/slope)])."""
    mask = struct.unpack_from("<H", t, MASK_AT)[0]
    recs = []
    for i in range(12):
        f = struct.unpack_from("<6H3h", t, REC * i)
        b = t[REC * i + 20:REC * i + 26]
        g, j = divmod(i, 6)
        a0, a1, a2, a3, a4 = GROUP[g]
        cur = np.zeros((7, 16, 2), int)
        for k in range(16):
            e = 16 * j + k
            w0 = struct.unpack_from("<I", t, a0 + 4 * e)[0]
            w1 = struct.unpack_from("<I", t, a1 + 4 * e)[0]
            hs = [w0 & 0xFFFF, w0 >> 16, w1 & 0xFFFF, w1 >> 16] + [struct.unpack_from("<H", t, a + 2 * e)[0] for a in (a2, a3, a4)]
            for s, x in enumerate(hs):
                cur[s, k] = (x >> 8, ((x & 0xFF) ^ 0x80) - 0x80)
        recs.append(dict(win=np.array(f[:6]).reshape(3, 2), ms=np.array(list(b)).reshape(3, 2),
                         eff=np.array(f[6:9]), curves=cur, on=bool(mask >> i & 1)))
    return dict(mask=mask, recs=recs)


# ---- the probe's tables ---------------------------------------------------------------------------------------
def sectors(values, kind, width=30.0, start=0.0, note=""):
    """12 adjacent hue sectors, one effect each: kind in 'dh', 'ds', 'dl'."""
    out = []
    for k, v in enumerate(values):
        out.append(Rec(hue=hue_win(start + width * k, start + width * (k + 1)), shapes={"hue": TRAP},
                       note=f"{note} sector {start + width * k:g}-{start + width * (k + 1):g} deg {kind} {v}", **{kind: v}))
    return out


def t_ctrl():
    return [None] * 12, 0x000


def t_huemap():
    recs = [Rec(hue=hue_win(30 * k + 10, 30 * k + 20), shapes={"hue": TRAP}, dl=-(40 + 10 * k),
                note=f"hue window {30 * k + 10}-{30 * k + 20} deg, L {-(40 + 10 * k)}") for k in range(12)]
    return recs, 0xFFF


def t_marker():
    """The Adobe RGB (table B) variant of HUEMAP: an unmistakable other pattern."""
    recs = [None] * 12
    recs[0] = Rec(hue=hue_win(20, 60), shapes={"hue": TRAP}, ds=-200, note="marker: S -200 at 20-60 deg")
    recs[6] = Rec(hue=hue_win(200, 240), shapes={"hue": TRAP}, dh=deg(30), note="marker: H +30 deg at 200-240 deg")
    return recs, 0x041


MAGL = [-1023, 512, -64, 16, -256, 128, -16, 1023, -128, 64, -512, 256]
MAGS = [-32, 512, -192, -256, 64, 2048, 32, -64, 256, -128, 128, 1024]
MAGH = [-91, 5461, -1365, 455, -16384, 1365, 91, -2730, 10923, -455, 2730, -5461]


def t_magl():
    return sectors(MAGL, "dl", note="MAGL"), 0xFFF


def t_mags():
    return sectors(MAGS, "ds", note="MAGS"), 0xFFF


def t_magh():
    return sectors(MAGH, "dh", note="MAGH"), 0xFFF


def t_curves():
    """Record k (k < 7): slot k has the RAMP shape, every other slot the window shapes; all three effects on."""
    recs = []
    for k in range(7):
        recs.append(Rec(hue=hue_win(50 * k + 2.5, 50 * k + 47.5), shapes={"hue": TRAP}, dh=deg(20), ds=160, dl=-160,
                        slot={k: points(RAMP)}, note=f"CURVES: slot c{k} = ramp, sector {50 * k + 2.5}-{50 * k + 47.5} deg"))
    return recs + [None] * 5, 0x07F


def t_overlap():
    r = [None] * 12
    r[0] = Rec(hue=hue_win(0, 60), shapes={"hue": TRAP}, ds=64, note="O1a S +64 at 0-60")
    r[6] = Rec(hue=hue_win(0, 60), shapes={"hue": TRAP}, ds=64, note="O1b S +64 at 0-60")
    r[1] = Rec(hue=hue_win(60, 120), shapes={"hue": TRAP}, dh=deg(10), note="O2a H +10 deg at 60-120")
    r[7] = Rec(hue=hue_win(60, 120), shapes={"hue": TRAP}, dh=deg(20), note="O2b H +20 deg at 60-120")
    r[2] = Rec(hue=hue_win(120, 180), shapes={"hue": TRAP}, dl=-64, note="O3a L -64 at 120-180")
    r[8] = Rec(hue=hue_win(120, 180), shapes={"hue": TRAP}, dl=-64, note="O3b L -64 at 120-180")
    r[3] = Rec(hue=hue_win(180, 240), shapes={"hue": TRAP}, ds=-128, note="O4a S -128 at 180-240")
    r[9] = Rec(hue=hue_win(210, 270), shapes={"hue": TRAP}, dl=128, note="O4b L +128 at 210-270")
    r[4] = Rec(hue=hue_win(270, 330), shapes={"hue": TRAP}, ds=-256, note="mask bit 4 OFF: S -256 at 270-330")
    r[5] = Rec(hue=hue_win(270, 300), shapes={"hue": TRAP}, dl=-64, note="M5 L -64 at 270-300 (bit 5 on)")
    r[10] = Rec(hue=hue_win(330, 360), shapes={"hue": TRAP}, dl=256, note="mask bit 10 OFF: L +256 at 330-360")
    r[11] = Rec(hue=hue_win(330, 345), shapes={"hue": TRAP}, ds=128, note="M11 S +128 at 330-345 (bit 11 on)")
    return r, 0xFFF & ~(1 << 4 | 1 << 10)


def t_window():
    r = [None] * 12
    h, w = hue_win(10, 40)
    r[0] = Rec(hue=(h, w), shapes={"hue": TRAP}, msov={"hue": (ms(2 * w)[0], ms(2 * w)[1])}, dl=-100,
               note="W2 hue 10-40 deg, mult/shift for half: p = 128 at the window end")
    h, w = hue_win(90, 130)
    r[1] = Rec(hue=(h, w), shapes={"hue": TRAP}, msov={"hue": ms(w // 2)}, dl=-100,
               note="W3 hue 90-130 deg, mult/shift for double: p = 256 at 110 deg")
    r[2] = Rec(hue=hue_win(150, 180), luma=(0, 0), shapes={"hue": TRAP}, ds=-128,
               note="W4 luma (0, 0), mult 0: expect every luma")
    r[3] = Rec(hue=hue_win(350, 370), shapes={"hue": TRAP}, dl=100, note="W5 hue 350-10 deg, through 0")
    r[4] = Rec(hue=hue_win(200, 240), shapes={"hue": TRAP}, dl=-160,
               note="W6 luma slot c5: levels 32, slopes +16 (inconsistent): a sawtooth along luma if the slope is used")
    r[4].curves[5] = points([32] * 17, [16] * 16)
    r[5] = Rec(hue=hue_win(250, 280), chroma=(0, 0), shapes={"hue": TRAP}, ds=128,
               note="W7 chroma (0, 0), mult 0: expect every chroma")
    r[6] = Rec(hue=hue_win(290, 320), dl=-64, note="W8 hue slots level 126 (twice the stock top)")
    for s in (0, 1, 6):
        r[6].curves[s] = points([0] + [126] * 15 + [0])
    r[7] = Rec(hue=hue_win(322, 346), chroma=(40, 120), luma=(256, 384), dl=-96,
               note="W1 every slot flat 63 (ends not 0), hue 322-346, chroma 40-160, luma 256-640")
    return r, 0x0FF


def t_box():
    r = [None] * 12
    r[0] = Rec(luma=(192, 128), shapes={"luma": TRAP}, dl=80, note="B luma 192-320 L +80")
    r[1] = Rec(luma=(704, 128), shapes={"luma": TRAP}, dl=-80, note="B luma 704-832 L -80")
    r[2] = Rec(luma=(448, 128), shapes={"luma": TRAP}, ds=-128, note="B luma 448-576 S -128")
    r[3] = Rec(hue=hue_win(200, 230), shapes={"hue": TRAP}, dh=deg(20), note="B hue 200-230 H +20 deg")
    r[4] = Rec(hue=hue_win(280, 330), shapes={"hue": TRAP}, dh=-int(round(20 * DEG)),
               note="B hue 280-330 H -20 deg")
    for i, (lo, hi, sgn) in enumerate(((24, 56, 1), (96, 160, -1), (224, 320, 1), (400, 560, -1))):
        r[6 + i] = Rec(hue=hue_win(0, 180), chroma=(lo, hi - lo), shapes={"hue": TRAP, "chroma": TRAP},
                       dh=sgn * int(round(15 * DEG)), note=f"B chroma {lo}-{hi} at hue 0-180, H {sgn * 15:+d} deg")
    return r, 0x3DF


TABLES = {"CTRL": t_ctrl, "HUEMAP": t_huemap, "MARKER": t_marker, "MAGL": t_magl, "MAGS": t_mags, "MAGH": t_magh,
          "CURVES": t_curves, "OVERLAP": t_overlap, "WINDOW": t_window, "BOX": t_box}


def table(name: str) -> bytes:
    recs, mask = TABLES[name]()
    return encode(recs, mask)


def notes(name: str) -> list[str]:
    recs, mask = TABLES[name]()
    return [f"r{i}{'' if mask >> i & 1 else ' (off)'}: {r.note}" for i, r in enumerate(recs) if r is not None]


# Menu entry (ART n), film code, table (None = the default path: table A, as every film gets on the pinned build),
# film, what it answers
ENTRIES = [
    (1, "Pop Art", 79, "CTRL", "clear", "control: every record off (mask 0)"),
    (2, "Soft Focus", 75, None, "clear", "Natural's table A, as films get it now"),
    (3, "Pale&Light Color", 71, "HUEMAP", "clear", "hue zero, direction and scale; table B (MARKER) in Adobe RGB"),
    (4, "Light Tone", 72, "MAGL", "clear", "lightness units, linearity, both signs, clipping"),
    (5, "Grainy Film", 94, "MAGS", "clear", "saturation units, add or multiply, both signs, extremes"),
    (6, "Pin Hole", 92, "MAGH", "clear", "hue-shift units, both signs, wrap at 180 deg"),
    (7, "Diorama", 125, "CURVES", "clear", "which curve slot shapes which effect along which axis"),
    (8, "Cross Process", 85, "OVERLAP", "clear", "overlapping records; the enable mask"),
    (9, "Gentle Sepia", 98, "WINDOW", "clear", "window ends, mult/shift, width 0, wrap, slopes, levels > 63, hard edge"),
    (10, "Dramatic Tone", 144, "BOX", "clear", "luma, chroma and hue window edges: the units"),
    (11, "Key Line", 156, "BOX", "stage6", "order against the saturation gain and the chroma curves"),
    (12, "Watercolor", 159, "BOX", "clear", "order against the look curve (this entry has Cross Process I's look)"),
]


# ---- forward model of the stage (hypotheses as options) --------------------------------------------------------
NOMINAL = dict(sign=1.0, h0=0.0, kc=4.0, ky=4.0, kl=0.25, ks=1 / 256, kh=360 / HUE_TURN, window="hard",
               sat="mul", roles="stock", norm=FULL, chroma_metric="euclid")


def curve_eval(cur, p):
    """cur (16, 2) level/slope; p array 0..256 -> value (interpolated with the slope, I)."""
    p = np.nan_to_num(p)
    i = np.clip(p // 16, 0, 15).astype(int)
    f = p - 16 * i
    return cur[i, 0] + cur[i, 1] * f / 16.0


def positions(x, start, width, mult, shift, window, wrap=None):
    """x in record units -> (inside, p)."""
    d = x - start
    if wrap:
        d = np.mod(d, wrap)
    p = np.floor(np.maximum(d, 0) * mult / 2.0 ** shift)
    if window == "hard":
        inside = (d >= 0) & ((d < width) | (width == 0))
    else:
        inside = np.ones_like(d, bool)
    return inside, np.clip(p, 0, 256)


def coords(Y, Cb, Cr, o):
    """8-bit Y and signed Cb, Cr -> record units (hue, chroma, luma) and the angle in degrees."""
    th = np.degrees(np.arctan2(Cr, Cb))
    hue = np.mod(o["sign"] * th + o["h0"], 360.0) * DEG
    if o.get("chroma_metric") == "l1":
        c = np.abs(Cb) + np.abs(Cr)
    elif o.get("chroma_metric") == "max":
        c = np.maximum(np.abs(Cb), np.abs(Cr))
    else:
        c = np.hypot(Cb, Cr)
    return hue, c * o["kc"], Y * o["ky"], th


def weights(t, hue, chroma, luma, o):
    """-> dict effect -> (n_rec, n) weights and the record effects."""
    roles = ROLES if o.get("roles", "stock") == "stock" else ROLES_SWAPPED
    out = {e: [] for e in "HSL"}
    effs = []
    for r in t["recs"]:
        (hs, hw), (cs, cw), (ys, yw) = r["win"]
        (hm, hsh), (cm, csh), (ym, ysh) = r["ms"]
        ih, ph = positions(hue, hs, hw, hm, hsh, o["window"], wrap=HUE_TURN)
        ic, pc = positions(chroma, cs, cw, cm, csh, o["window"])
        iy, py = positions(luma, ys, yw, ym, ysh, o["window"])
        inside = (ih & ic & iy) & r["on"]
        wy = curve_eval(r["curves"][5], py) / o["norm"]
        for e in "HSL":
            sh, sc = roles[e]
            w = curve_eval(r["curves"][sh], ph) / o["norm"] * curve_eval(r["curves"][sc], pc) / o["norm"] * wy
            out[e].append(np.where(inside, w, 0.0))
        effs.append(r["eff"])
    return {e: np.array(v) for e, v in out.items()}, np.array(effs, float)


def apply(t, Y, Cb, Cr, o=None):
    """The stage on 8-bit Y and signed Cb, Cr (floats). t = decode(table)."""
    o = {**NOMINAL, **(o or {})}
    hue, chroma, luma, th = coords(Y, Cb, Cr, o)
    W, E = weights(t, hue, chroma, luma, o)
    dh = (W["H"] * E[:, 0:1]).sum(0)
    ds = (W["S"] * E[:, 1:2]).sum(0)
    dl = (W["L"] * E[:, 2:3]).sum(0)
    c = np.hypot(Cb, Cr)
    if o["sat"] == "mul":
        c2 = c * np.maximum(1 + o["ks"] * ds, 0)
    else:
        c2 = np.maximum(c + o["ks"] * ds, 0)
    th2 = np.radians(th + o["sign"] * o["kh"] * dh)
    Y2 = np.clip(Y + o["kl"] * dl, 0, 255)
    return Y2, np.clip(c2 * np.cos(th2), -128, 127), np.clip(c2 * np.sin(th2), -128, 127)


if __name__ == "__main__":
    for n in TABLES:
        t = table(n)
        d = decode(t)
        assert encode(*TABLES[n]()) == t and len(t) == TABLE_BYTES
        print(n, "mask %#05x" % d["mask"], "records on", sum(r["on"] for r in d["recs"]))
        for line in notes(n):
            print("   ", line)
    # self-check: re-decode Natural-style curve points round trip
    p = points(RAMP)
    assert [(x >> 8) for x in p] == RAMP[:16]
    print("ok")
