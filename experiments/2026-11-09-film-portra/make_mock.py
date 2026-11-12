"""Build the synthetic test RAW ("mock image") for RAW Data Edit (NOTES §24).

One ORF with 6,912 flat colour patches (96 x 72, each 48 x 48 raw pixels), written into a copy of a
real ORF (donor: metadata, lens data, preview stay; only the raw strip is replaced). Re-developing
it in the camera gives the build's exact response to every patch colour.

Patch colours are defined as u = white-balanced camera RGB (donor WB 528/256, 1, 460/256), 0..3790
above black, so u_R = u_G = u_B is neutral for the donor WB:
  lattice   108  white patches at every 8th row and column: position fiducials + shading check
  grid     4913  17 x 17 x 17 in u, levels 3790 (i/16)^2
  gray      512  256-step neutral ramp, twice (different places)
  near      162  near-neutral: 9 levels x 6 hues x 3 small chroma
  mid        49  the same mid gray scattered over the frame (uniformity)
  natural  1168  random natural colours as in the fit samples
Layout positions are a fixed pseudo-random permutation, so spatial effects do not line up with colour.
Writes out/mock/PB120001.ORF and out/mock/mock_layout.npz.   ../../.venv/bin/python -I make_mock.py
"""
import json, os, struct, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orfcodec

DONOR = "shots/testraw/PB090221.ORF"
H, W, P, X0, Y0, NC, NR = 3472, 4640, 48, 16, 8, 96, 72
BLACK, UMAX = 255, 3790.0
WB = np.array([528 / 256, 1.0, 460 / 256])
M = np.array([418, -140, -22, -56, 360, -48, 14, -132, 374]).reshape(3, 3) / 256.0

def patch_colours():
    rng = np.random.default_rng(20261112)
    lv = UMAX * (np.arange(17) / 16.0) ** 2
    grid = np.array([[r, g, b] for r in lv for g in lv for b in lv])
    ramp = UMAX * (np.arange(256) / 255.0) ** 2.0
    gray = np.repeat(np.concatenate([ramp, ramp])[:, None], 3, 1)
    near = []
    for lvl in UMAX * np.array([0.01, 0.03, 0.07, 0.13, 0.22, 0.35, 0.5, 0.7, 0.9]):
        for hue in np.arange(6) * np.pi / 3:
            for ch in (0.04, 0.09, 0.16):
                d = np.array([np.cos(hue), np.cos(hue - 2.094), np.cos(hue + 2.094)])
                near.append(lvl * (1 + ch * d))
    mid = np.tile(UMAX * 0.18 * np.ones(3), (49, 1))
    base = 0.18 * 2 ** rng.uniform(-3.5, 2.2, 1168); hue = rng.uniform(0, 2 * np.pi, 1168); chroma = rng.beta(1.2, 3.5, 1168) * 0.9
    dd = np.stack([np.cos(hue), np.cos(hue - 2.094), np.cos(hue + 2.094)], 1)
    vlin = base[:, None] * np.clip(1 + chroma[:, None] * dd, 0.02, None) / 0.18 * 264.0     # v units (18 % gray = 264)
    natural = vlin @ np.linalg.inv(M).T                                                    # v = M u
    cols = np.concatenate([grid, gray, np.array(near), mid, natural])
    kinds = np.concatenate([np.full(len(grid), 1), np.full(len(gray), 2), np.full(len(near), 3), np.full(len(mid), 4), np.full(len(natural), 5)])
    return np.clip(cols, 0, None), kinds, rng

def main():
    cols, kinds, rng = patch_colours()
    lattice = [(r, c) for r in range(0, NR, 8) for c in range(0, NC, 8)]
    free = [(r, c) for r in range(NR) for c in range(NC) if (r % 8 or c % 8)]
    assert len(free) == len(cols), (len(free), len(cols))
    order = rng.permutation(len(free))
    pos = np.zeros((NR * NC, 2), int); u = np.zeros((NR * NC, 3)); kind = np.zeros(NR * NC, int)
    k = 0
    for (r, c) in lattice:
        pos[k] = (r, c); u[k] = UMAX; kind[k] = 0; k += 1
    for j, idx in enumerate(order):
        pos[k] = free[idx]; u[k] = cols[j]; kind[k] = kinds[j]; k += 1
    raw_rgb = np.clip(np.round(u / WB), 0, UMAX).astype(np.int32)            # camera RGB above black, per patch
    u_real = raw_rgb * WB                                                    # what is really in the file
    img = np.full((H, W), BLACK, np.int32)                                   # margins stay black
    # Bayer: (0,0) R, (0,1) G, (1,0) G, (1,1) B
    for (r, c), rgbv in zip(pos, raw_rgb):
        y, x = Y0 + r * P, X0 + c * P
        blk = img[y:y + P, x:x + P]
        blk[0::2, 0::2] = BLACK + rgbv[0]; blk[0::2, 1::2] = BLACK + rgbv[1]; blk[1::2, 0::2] = BLACK + rgbv[1]; blk[1::2, 1::2] = BLACK + rgbv[2]
    enc = orfcodec.encode(img)
    assert (orfcodec.decode(enc, H, W) == img).all()
    e = json.loads(subprocess.run(["exiftool", "-j", "-n", "-StripOffsets", "-StripByteCounts", DONOR], capture_output=True, text=True).stdout)[0]
    off, ln = e["StripOffsets"], e["StripByteCounts"]
    donor = open(DONOR, "rb").read(); assert off + ln == len(donor)
    enc[:7] = np.frombuffer(donor[off:off + 7], np.uint8)
    head = bytearray(donor[:off])
    # StripByteCounts (tag 0x0117, LONG, count 1) in IFD0
    ifd = struct.unpack("<I", head[4:8])[0]; n = struct.unpack("<H", head[ifd:ifd + 2])[0]; done = False
    for i in range(n):
        ent = ifd + 2 + 12 * i; tag, typ, cnt, val = struct.unpack("<HHII", head[ent:ent + 12])
        if tag == 0x0117:
            assert typ == 4 and cnt == 1 and val == ln; head[ent + 8:ent + 12] = struct.pack("<I", len(enc)); done = True
    assert done
    os.makedirs("out/mock", exist_ok=True)
    open("out/mock/PB120001.ORF", "wb").write(bytes(head) + enc.tobytes())
    np.savez("out/mock/mock_layout.npz", pos=pos, raw_rgb=raw_rgb, kind=kind, P=P, X0=X0, Y0=Y0, NC=NC, NR=NR, WB=WB, M=M)
    print("wrote out/mock/PB120001.ORF", len(head) + len(enc), "bytes;", len(pos), "patches;", {int(k): int((kind == k).sum()) for k in np.unique(kind)})

if __name__ == "__main__":
    main()
