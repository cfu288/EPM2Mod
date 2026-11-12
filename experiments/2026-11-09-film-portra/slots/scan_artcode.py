"""Inventory of every place block 0 treats art codes specially (NOTES §32).
1. Lookup tables indexed by the art code: range check `cmp HI,dN` (HI in 168..184) followed by `add -K,dN` and a
   table address (jump tables), and hash tables (`and` with 31, `asl 3`, table address, key = code - K).
2. Clusters of compare instructions against art-code values (two or more different codes within 48 bytes).
Regions: IMG library, WB module, record / art task code.   python3 -I scan_artcode.py"""
import re, struct, os, sys, json
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
b = open(os.path.join(ROOT, "build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin"), "rb").read(); B = 0x7E421020
REG = [(0x7E544AA9, 0x7E576D58, "IMG"), (0x7E579C34, 0x7E581FAF, "WB"), (0x7E6C0000, 0x7E731584, "movie/rec/art")]
CODES = {69: "Soft Focus", 70: "Pop Art I", 71: "Pale&Light I", 72: "Light Tone", 73: "Pin Hole I", 74: "Grainy I", 85: "Cross Process I", 86: "Diorama", 91: "Gentle Sepia",
         96: "Dramatic I", 163: "Key Line I", 181: "Watercolor I"}
MOVIE = {78: 69, 79: 70, 80: 71, 81: 72, 82: 73, 83: 74, 87: 85, 88: 86, 93: 91, 97: 96, 164: 163, 183: 181}
ALL = set(CODES) | set(MOVIE) | {102, 103, 104, 106, 108, 145, 165, 166, 167, 168, 169, 170, 182, 184, 117, 118, 119, 121, 123, 124, 84, 75, 151, 153}
u32 = lambda a: struct.unpack_from("<I", b, a - B)[0]
def region(a): return next((n for lo, hi, n in REG if lo <= a < hi), None)
out = {"jump": [], "hash": [], "clusters": []}
# --- jump tables: add -K (imm8) then asl2 and mov imm32,aN within 16 bytes
for lo, hi, nm in REG:
    seg = b[lo - B:hi - B]
    for m in re.finditer(rb"[\x28-\x2b]([\x80-\xff])", seg):                       # add imm8(negative),dN
        a = lo + m.start(); K = 256 - m.group(1)[0]
        w = seg[max(0, m.start() - 10):m.start() + 14]
        t = re.search(rb"\xfc[\xdc-\xdf](....)", w, re.S)
        if not t or not re.search(rb"[\x54-\x57]", w[10:]): continue              # needs asl2 after
        tab = struct.unpack("<I", t.group(1))[0]
        if not (0x7E730000 <= tab < 0x7E8E0000) or K < 8 or K > 80: continue
        pre = seg[max(0, m.start() - 40):m.start()]
        hi_m = re.findall(rb"\xfa[\xc8-\xcb](..)", pre, re.S); HI = struct.unpack("<H", hi_m[-1])[0] if hi_m else None
        if HI is None or not (100 <= HI <= 200): continue
        ent = {c: u32(tab + 4 * (c - K)) for c in sorted(set(CODES) | set(MOVIE)) if K <= c <= HI}
        cnt = {}
        for c in range(K, HI + 1): cnt[u32(tab + 4 * (c - K))] = cnt.get(u32(tab + 4 * (c - K)), 0) + 1
        dflt = max(cnt, key=cnt.get)
        out["jump"].append(dict(at=a, region=nm, table=tab, K=K, HI=HI, default=dflt, special={c: h for c, h in ent.items() if h != dflt}))
    # --- hash tables: mov 31,dN ... and ... asl 3 ... table
    for m in re.finditer(rb"\xf8[\xc0-\xc3]\x03", seg):                            # asl 3,dN
        a = lo + m.start(); w = seg[max(0, m.start() - 24):m.start() + 16]
        if b"\x1f" not in w[:26]: continue
        t = re.findall(rb"\xfc[\xd0-\xdf](....)", w, re.S); tabs = [struct.unpack("<I", x)[0] for x in t if 0x7E730000 <= struct.unpack("<I", x)[0] < 0x7E8E0000]
        if not tabs: continue
        pre = seg[max(0, m.start() - 40):m.start()]; km = re.findall(rb"[\x28-\x2b]([\x80-\xff])", pre)
        if not km: continue
        K = 256 - km[-1][0]; tab = tabs[0]; keys = {}
        for i in range(32):
            k, h = struct.unpack_from("<II", b, tab - B + 8 * i)
            if k and k + K < 256: keys[k + K] = h
        if len(keys) >= 3: out["hash"].append(dict(at=a, region=nm, table=tab, K=K, codes=keys))
# --- compare clusters
cmps = []
for lo, hi, nm in REG:
    seg = b[lo - B:hi - B]
    for m in re.finditer(rb"[\xa0\xa5\xaa\xaf](.)", seg, re.S):
        v = m.group(1)[0]
        if v in ALL and v >= 69: cmps.append((lo + m.start(), v, nm))
    for m in re.finditer(rb"\xfa[\xc8-\xcb](..)", seg, re.S):
        v = struct.unpack("<H", m.group(1))[0]
        if v in ALL: cmps.append((lo + m.start(), v, nm))
cmps.sort(); i = 0
while i < len(cmps):
    j = i
    while j + 1 < len(cmps) and cmps[j + 1][0] - cmps[j][0] <= 48: j += 1
    vals = sorted({c[1] for c in cmps[i:j + 1]})
    if len(vals) >= 2 and not (vals[-1] >= 168 and len(vals) == 2 and vals[0] < 90 and False):
        out["clusters"].append(dict(start=cmps[i][0], end=cmps[j][0], region=cmps[i][2], codes=vals))
    i = j + 1
seen = set()
print("JUMP TABLES indexed by art code:")
for t in out["jump"]:
    if t["table"] in seen: continue
    seen.add(t["table"]); print(f"  table {t['table']:#x} (code - {t['K']}, up to {t['HI']}; used at {t['at']:#x}, {t['region']}): default {t['default']:#x}; visible codes with their own entry: "
          + ", ".join(f"{c}" for c in t["special"] if c in CODES) + " | movie: " + ", ".join(f"{c}" for c in t["special"] if c in MOVIE))
print("HASH TABLES keyed by art code:")
seen = set()
for t in out["hash"]:
    if t["table"] in seen: continue
    seen.add(t["table"]); print(f"  table {t['table']:#x} (key = code - {t['K']}; used at {t['at']:#x}, {t['region']}): codes {sorted(t['codes'])}")
print("COMPARE CLUSTERS (>= 2 different art-code values within 48 bytes):")
for c in out["clusters"]: print(f"  {c['start']:#x}..{c['end']:#x} {c['region']:14s} codes {c['codes']}")
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "artcode_inventory.json"), "w"), indent=1, default=lambda x: {str(k): v for k, v in x.items()} if isinstance(x, dict) else x)
