"""Second-generation synthetic test RAWs (NOTES §27). Two files, same patch geometry as make_mock.py
(96 x 72 patches of 48 x 48 raw pixels, white position markers every 8th row / column).

Colours are defined in scene-linear sRGB v (18 % gray = 264) for the white balance the camera applies
to these files (520 / 470, 5300 K matrix), so neutral patches are neutral in the output.

A  out/mock/PB130001.ORF  "objective" image: the exact colours the fit is scored on
     kind 6  GRKit gray ramp (120) + 12 grays up to sensor clipping       weight 150
     kind 7  ColorChecker x 5 exposures (-2..+2 EV), three copies         weight 20 (skin patches 60)
     kind 8  skin series between the two ColorChecker skin patches (45)
     kind 5  the fit's random natural colours, fl.natural(4000, 1) (3,535) weight 1
     kind 9  hold-out natural colours, fl.natural(3000, 2) (first 1,000)
     kind 3  near-neutrals: 12 levels x 12 hues x 4 chroma (576)
     kind 2  dense gray ramp, 256 raw levels twice (512)
     kind 4  identical mid grays (25; uniformity check)
     kind 10 bright saturated colours near the gamut edge: 100 cyan / green, 200 yellow, orange, magenta, blue (300)
     kind 1  coarse 7^3 cube over white-balanced camera RGB (343)
   Expendable kinds (cube, part of the hold-out) go to the border, which the lens correction crops.
B  out/mock/PB130002.ORF  "blue scene" image: 2/3 of the frame is sky / sea blue (kind 11), so the
   Cross Process scene statistics (CODE_DIG §2: dominant bin B or C) are at their maximum; the rest
   repeats patches of A (same raw values, `sid` = index in A), including every blue / cyan one.
   If the look is scene-independent, the repeated patches render the same in A and B.
Layouts: out/mock/mock2a_layout.npz, mock2b_layout.npz (pos, raw_rgb, kind, sid, weight).
   ../../.venv/bin/python -I make_mock2.py
"""
import json, os, struct, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import orfcodec
from mocklib import fl, M5300

DONOR = "shots/testraw/PB090221.ORF"
H, W, P, X0, Y0, NC, NR = 3472, 4640, 48, 16, 8, 96, 72
BLACK, UMAX, VG = 255, 3790.0, fl.V_GRAY
WB = np.array([520 / 256, 1.0, 470 / 256]); MINV = np.linalg.inv(M5300)
v2u = lambda v: v @ MINV.T
hue_d = lambda h: np.stack([np.cos(h), np.cos(h - 2.094), np.cos(h + 2.094)], -1)

def colours_a():
    rng = np.random.default_rng(20261113)
    cc = fl.colorchecker_linear(); S = []                       # (kind, weight, u)
    add = lambda kind, w, u: S.extend((kind, wi, ui) for wi, ui in zip(np.broadcast_to(w, len(u)), u))
    gray = 0.18 * 2 ** np.concatenate([np.linspace(-5, 2.5, 120), np.linspace(2.7, 3.95, 12)])
    add(6, 150.0, v2u(np.repeat(gray[:, None], 3, 1) / 0.18 * VG))
    chart = np.concatenate([cc * 2.0 ** e for e in (-2, -1, 0, 1, 2)]); wch = np.tile(np.where(np.arange(24) < 2, 60.0, 20.0), 5)
    for copy in range(2): add(7, wch, v2u(chart / 0.18 * VG))
    add(7, wch[:96], v2u(chart[:96] / 0.18 * VG))
    skin = np.array([((1 - t) * cc[0] + t * cc[1]) * 2.0 ** e for t in (0, .25, .5, .75, 1) for e in np.arange(-2, 2.01, 0.5)])
    add(8, 0.0, v2u(skin / 0.18 * VG))
    rnd = fl.natural(4000, 1); rnd = rnd[rnd.max(1) <= 0.18 * 2 ** 2.6]; add(5, 1.0, v2u(rnd / 0.18 * VG))
    hold = fl.natural(3000, 2); hold = hold[hold.max(1) <= 0.18 * 2 ** 2.6][:1000]; add(9, 0.0, v2u(hold / 0.18 * VG))
    near = np.array([0.18 * 2 ** e * (1 + ch * hue_d(h)) for e in np.linspace(-4, 2.5, 12) for h in np.arange(12) * np.pi / 6 for ch in (0.03, 0.06, 0.10, 0.16)])
    add(3, 0.0, v2u(near / 0.18 * VG))
    ramp = UMAX * (np.arange(256) / 255.0) ** 2; add(2, 0.0, np.repeat(np.concatenate([ramp, ramp])[:, None], 3, 1))
    add(4, 0.0, np.full((25, 3), 0.18 * UMAX))
    hi = rng.uniform(0.35, 1.0, (100, 2)) * UMAX; lo = rng.uniform(0.0, 0.3, 100) * hi.min(1)          # cyan / green: R low, G and B high
    edge = [np.stack([lo, hi[:, 0], hi[:, 1]], 1)]
    # warm and other gamut-edge mixes (first channel highest, second next); more of the warm ones so that the frame's
    # scene statistics are not blue / cyan dominated (the adaptive stage must stay idle for this image even on stock code)
    for (a, b, c), n in (((0, 1, 2), 70), ((0, 2, 1), 40), ((2, 0, 1), 20), ((1, 0, 2), 70)):
        top = rng.uniform(0.4, 1.0, n) * UMAX; x = np.zeros((n, 3)); x[:, a] = top; x[:, b] = top * rng.uniform(0.3, 1.0, n); x[:, c] = top * rng.uniform(0, 0.15, n); edge.append(x)
    add(10, 0.0, np.concatenate(edge))
    lv = UMAX * (np.arange(7) / 6.0) ** 2; add(1, 0.0, np.array([[r, g, b] for r in lv for g in lv for b in lv]))
    kind = np.array([s[0] for s in S]); w = np.array([s[1] for s in S]); u = np.clip(np.array([s[2] for s in S]), 0, UMAX)
    return kind, w, u, rng

def place(kind, u, border_first, rng):
    """Returns pos (n, 2) for each sample: samples flagged border_first fill the cropped border zone first."""
    free = [(r, c) for r in range(NR) for c in range(NC) if (r % 8 or c % 8)]
    isb = np.array([r < 2 or r >= NR - 2 or c < 3 or c >= NC - 3 for r, c in free])
    border = [f for f, b in zip(free, isb) if b]; inner = [f for f, b in zip(free, isb) if not b]
    assert len(free) == len(kind), (len(free), len(kind))
    bi = rng.permutation(np.flatnonzero(border_first)); oi = rng.permutation(np.flatnonzero(~border_first))
    nb = min(len(bi), len(border)); order = np.concatenate([bi[:nb], oi[:len(border) - nb], bi[nb:], oi[len(border) - nb:]])
    slots = [border[i] for i in rng.permutation(len(border))] + [inner[i] for i in rng.permutation(len(inner))]
    pos = np.zeros((len(kind), 2), int); pos[order] = slots
    return pos

def write(name, pos, raw_rgb, extra):
    lat = np.array([(r, c) for r in range(0, NR, 8) for c in range(0, NC, 8)]); white = np.round(UMAX / WB).astype(np.int32)
    apos = np.concatenate([lat, pos]); araw = np.concatenate([np.tile(white, (len(lat), 1)), raw_rgb])
    img = np.full((H, W), BLACK, np.int32)
    for (r, c), v in zip(apos, araw):
        blk = img[Y0 + r * P:Y0 + (r + 1) * P, X0 + c * P:X0 + (c + 1) * P]
        blk[0::2, 0::2] = BLACK + v[0]; blk[0::2, 1::2] = BLACK + v[1]; blk[1::2, 0::2] = BLACK + v[1]; blk[1::2, 1::2] = BLACK + v[2]
    enc = orfcodec.encode(img); assert (orfcodec.decode(enc, H, W) == img).all()
    e = json.loads(subprocess.run(["exiftool", "-j", "-n", "-StripOffsets", "-StripByteCounts", DONOR], capture_output=True, text=True).stdout)[0]
    off, ln = e["StripOffsets"], e["StripByteCounts"]; donor = open(DONOR, "rb").read(); assert off + ln == len(donor)
    enc[:7] = np.frombuffer(donor[off:off + 7], np.uint8); head = bytearray(donor[:off])
    ifd = struct.unpack("<I", head[4:8])[0]; n = struct.unpack("<H", head[ifd:ifd + 2])[0]; done = False
    for i in range(n):
        ent = ifd + 2 + 12 * i; tag, typ, cnt, val = struct.unpack("<HHII", head[ent:ent + 12])
        if tag == 0x0117: assert typ == 4 and cnt == 1 and val == ln; head[ent + 8:ent + 12] = struct.pack("<I", len(enc)); done = True
    assert done
    open(f"out/mock/{name}.ORF", "wb").write(bytes(head) + enc.tobytes())
    nl = len(lat); z = lambda a, fill: np.concatenate([np.full((nl,) + a.shape[1:], fill, a.dtype), a])
    np.savez(f"out/mock/{extra['tag']}_layout.npz", pos=apos, raw_rgb=araw, kind=z(extra["kind"], 0), sid=z(extra["sid"], -1), weight=z(extra["weight"], 0.0),
             P=P, X0=X0, Y0=Y0, NC=NC, NR=NR, WB=WB, M=M5300)
    return len(head) + len(enc)

def scene_stats(raw_rgb):
    """The six rank-order bins of the Cross Process scene statistics (CODE_DIG §2), on white-balanced patch values."""
    u = raw_rgb * WB; o = np.argsort(-u, 1); s = np.take_along_axis(u, o, 1); bins = np.zeros(6)
    sec = np.array([[-1, 3, 5], [3, -1, 4], [5, 4, -1]])
    np.add.at(bins, o[:, 0], s[:, 0] - s[:, 1]); np.add.at(bins, sec[o[:, 0], o[:, 1]], s[:, 1] - s[:, 2])
    rank = np.argsort(-bins); dom = rank[0]; msg = "dominant " + "RGBYCM"[dom]
    if dom in (2, 4):
        nb = {2: (4, 5), 4: (1, 2)}[dom]; other = bins[rank[2]] if rank[1] in nb else bins[rank[1]]
        k = min(256, (bins[dom] - other) / max(other / 128, 1)); msg += f", added hue units {k / 16:.1f} of 16"
    else: msg += ", no adaptive shift"
    return "bins R G B Y C M = " + " ".join(f"{b / bins.sum():.2f}" for b in bins) + "; " + msg

def main():
    kind, w, u, rng = colours_a(); raw = np.clip(np.round(u / WB), 0, UMAX).astype(np.int32)
    hold_idx = np.flatnonzero(kind == 9); bf = (kind == 1); bf[hold_idx[600:]] = True
    pos = place(kind, u, bf, rng)
    n = write("PB130001", pos, raw, dict(tag="mock2a", kind=kind, sid=np.arange(len(kind)), weight=w))
    print("A: PB130001.ORF", n, "bytes;", {int(k): int((kind == k).sum()) for k in np.unique(kind)}); print("   scene statistics:", scene_stats(raw))
    # B: repeated patches + sky filler
    ua = raw * WB; blueish = (ua[:, 2] > ua[:, 0] * 1.1) & (ua[:, 2] >= ua[:, 1] * 0.9) | ((ua[:, 1] > ua[:, 0] * 1.15) & (ua[:, 2] > ua[:, 0] * 1.15))
    c7 = np.flatnonzero(kind == 7)[:120]
    rep = np.concatenate([np.flatnonzero(kind == 6), c7, np.flatnonzero(kind == 8), np.flatnonzero(kind == 4), np.flatnonzero((kind == 5) & blueish)])
    rest = np.setdiff1d(np.flatnonzero(kind == 5), rep); rep = np.concatenate([rep, rng.permutation(rest)[:max(0, 2200 - len(rep))]])
    nf = len(kind) - len(rep)
    L = 0.18 * 2 ** rng.uniform(-1.5, 1.6, nf); t = rng.uniform(0, 1, nf)[:, None]                 # deep sky blue ... cyan-blue sea
    base = (1 - t) * np.array([0.22, 0.42, 1.0]) + t * np.array([0.18, 0.62, 0.95]); base = base / (base @ np.array([.2126, .7152, .0722]))[:, None]
    sky = np.clip(v2u(L[:, None] * base * (1 + rng.normal(0, 0.03, (nf, 3))) / 0.18 * VG), 0, UMAX)
    kb = np.concatenate([kind[rep], np.full(nf, 11)]); rb = np.concatenate([raw[rep], np.clip(np.round(sky / WB), 0, UMAX).astype(np.int32)])
    sid = np.concatenate([rep, np.full(nf, -1)]); wb_ = np.concatenate([w[rep], np.zeros(nf)])
    posb = place(kb, None, kb == 11, rng)
    n = write("PB130002", posb, rb, dict(tag="mock2b", kind=kb, sid=sid, weight=wb_))
    print("B: PB130002.ORF", n, "bytes; repeated from A:", len(rep), f"(blue / cyan among the fit colours: {int(((kind == 5) & blueish).sum())}); sky filler:", nf)
    print("   scene statistics:", scene_stats(rb))

if __name__ == "__main__":
    main()
