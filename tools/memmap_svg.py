#!/usr/bin/env python3
"""Draw block 0 of the E-PM2 v1.6 firmware as a memory map (SVG), in address order.

    python3 tools/memmap_svg.py [-o docs/memory-map.svg] [SPEC.json ...]

Each cell is 256 bytes; each row is 64 KiB. A cell takes the colour of the most important thing in it:
patched bytes > verified free space > unproven blank space > code / data / blank.
Inputs: the stock block 0, build/map/functions.tsv (code vs data), docs/code-space-map.tsv (free-space verdicts,
made by tools/freespace.py map) and the patch specs given on the command line (default: the current stack).
Code vs data is the function database's page classification plus the known rodata ranges, so small tables inside
code pages show as code.
"""
import argparse, csv, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 0x7E421020
BLOCK0 = "build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin"
CELL, COLS, PX = 256, 256, 4

# (start, end, name, when it is in RAM) - from docs/code-space-map.md section 1
LOADS = [
    (0x7E421020, 0x7E430000, "reset code", "before reset"),
    (0x7E430000, 0x7E4C9800, "kernel, drivers", "reset"),
    (0x7E4FE000, 0x7E881000, "segment 1", "boot task"),
    (0x7E8DA000, 0x7E8F3114, ".data image", "reset"),
    (0x7E8F5800, 0x7ECB1000, "segment 2", "Usr1"),
    (0x7ECCB800, 0x7F034000, "segment 3", "Usr1"),
    (0x7F05C000, 0x7F06B000, "overlay A", "on demand"),
    (0x7F080000, 0x7F0EB800, "overlay B", "on demand"),
    (0x7F100000, 0x7F119000, "third Usr1 load", "Usr1"),
    (0x7F14B000, 0x7F14B820, "SRAM image", "reset"),
]
# (start, what is there) - from docs/firmware-map.md, "Address regions of block 0"
MODULES = [
    (0x7E421020, "reset code, kernel"),
    (0x7E44B000, "drivers, debug shell, peripheral tasks"),
    (0x7E4C9800, "blank, never loaded"),
    (0x7E4FE000, "C runtime, start-up tasks"),
    (0x7E521133, "firmware update, lens, stabiliser, image library, AF"),
    (0x7E6211E1, "exposure, HDMI, movie, face detection, mode controller"),
    (0x7E70B3F8, "still recording, art filters"),
    (0x7E731588, "segment-1 data: tone curves, colour tables, strings"),
    (0x7E881000, "blank, never loaded"),
    (0x7E8DA000, ".data image"),
    (0x7E8F5800, "playback, Bluetooth, audio"),
    (0x7E965FD1, "C++ app layer: shooting sequences, sdk shell"),
    (0x7EBA0AA9, "device classes, Smart Skin"),
    (0x7EBABF90, "segment-2 data"),
    (0x7ECB1000, "blank, never loaded"),
    (0x7ECCB800, "GUI code: menus, live view, playback screens"),
    (0x7EE02095, "3D graphics stack (GL, 3D engine, png, zlib)"),
    (0x7EE8F4F4, "video plug-ins (H.264, MP4)"),
    (0x7EECE319, "segment-3 data: menu tables, GUI strings"),
    (0x7F034000, "blank, never loaded"),
    (0x7F05C000, "overlay A: BASIC, PictBridge, red-eye"),
    (0x7F080000, "overlay B: factory adjustment, USB (PTP/MTP)"),
    (0x7F100000, "third start-up load, SRAM image"),
]
RODATA = [(0x7E731588, 0x7E8808C0), (0x7EBABF90, 0x7ECB083C), (0x7EECE319, 0x7F034000)]
DATA_IMAGE = (0x7E8DA000, 0x7E8F3114)

# class -> (priority, colour, legend)
CLASSES = {
    "interval": (9, "#00b4d8", "changed by the interval patches"),
    "film":     (8, "#e0409f", "changed by the film patches"),
    "freecode": (7, "#7CFC00", "free, verified for code"),
    "freedata": (6, "#2e9e44", "free, verified for data"),
    "unproven": (5, "#f2c200", "blank or reclaimable, not proven"),
    "code":     (2, "#3566b8", "code"),
    "data":     (2, "#d9822b", "read-only data"),
    "dataimg":  (2, "#8e5bc0", ".data image (copied to RAM variables)"),
    "blankld":  (1, "#b9c2cc", "blank, loaded (small gaps)"),
    "flash":    (1, "#7a6f66", "content never loaded to RAM"),
    "blank":    (0, "#2a2d31", "blank, never loaded"),
}
DEFAULT_SPECS = ["patches/remap7b-code.json", "patches/seven-fixes-1.json", "patches/seven-movie-1.json",
                 "patches/seven-structure-extra.json", "patches/seven-films-5.json",
                 "patches/xp-adaptive-hue-off.json", "patches/seven-labels.json",
                 "experiments/2026-11-13-intervalometer/patches/interval-timelapse-v2.json",
                 "experiments/2026-11-13-intervalometer/patches/interval-frames-240.json"]


def classify(specs):
    b = open(os.path.join(ROOT, BLOCK0), "rb").read()
    n = len(b)
    cls = [None] * n

    def span(lo, hi, name, only=None):
        for o in range(max(0, lo - BASE), min(n, hi - BASE)):
            if only is None or cls[o] in only:
                cls[o] = name

    loaded = bytearray(n)
    for lo, hi, _, _ in LOADS:
        for o in range(max(0, lo - BASE), min(n, hi - BASE)):
            loaded[o] = 1
    # code / data from the function database
    rows = list(csv.reader(open(os.path.join(ROOT, "build/map/functions.tsv")), delimiter="\t"))[1:]
    starts = [int(r[0], 16) - BASE for r in rows]
    isdata = [r[7] == "1" or (len(r) > 8 and r[8] == "1") for r in rows]
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else n
        name = "data" if isdata[i] else "code"
        for o in range(s, e):
            cls[o] = name
    for lo, hi in RODATA:
        span(lo, hi, "data")
    span(DATA_IMAGE[0], DATA_IMAGE[1], "dataimg")
    for o in range(n):
        if not loaded[o]:
            cls[o] = "blank" if b[o] == 0xFF else "flash"
        elif b[o] == 0xFF and cls[o] != "dataimg":
            # a blank byte counts as a gap only inside a run of 32+ blank bytes
            pass
    o = 0
    while o < n:
        if b[o] == 0xFF and loaded[o]:
            e = o
            while e < n and b[e] == 0xFF and loaded[e]:
                e += 1
            if e - o >= 32:
                for k in range(o, e):
                    if cls[k] != "dataimg":
                        cls[k] = "blankld"
            o = e
        else:
            o += 1
    # free-space verdicts
    verdicts = {"USABLE-CODE": "freecode", "USABLE-DATA": "freedata", "NEEDS-DECISION": "unproven", "USED": None}
    path = os.path.join(ROOT, "docs/code-space-map.tsv")
    if os.path.exists(path):
        for r in csv.DictReader(open(path), delimiter="\t"):
            name = verdicts.get(r["verdict"])
            lo, hi = int(r["start"], 16), int(r["end"], 16)
            if r["verdict"] == "USED":
                name = "freecode" if r.get("allowed_use") == "code" else "freedata"
            if name and loaded[min(n - 1, max(0, lo - BASE))]:
                span(lo, hi, name)
    # patched bytes
    for sp in specs:
        d = json.load(open(os.path.join(ROOT, sp)))
        name = "interval" if "interval" in os.path.basename(sp) else "film"
        for op in d["ops"]:
            if op.get("type") != "bytes" or op.get("block", 0) != 0:
                continue
            off = int(op["offset"], 16)
            new, exp = bytes.fromhex(op["new"]), bytes.fromhex(op["expect"])
            for i in range(len(new)):
                if new[i] != exp[i] and off + i < n:
                    cls[off + i] = name
    return b, cls


def render(cls, out):
    n = len(cls)
    rows = (n + CELL * COLS - 1) // (CELL * COLS)
    left, top, right = 96, 150, 400
    W, H = left + COLS * PX + right, top + rows * PX + 120
    prio = {k: v[0] for k, v in CLASSES.items()}
    totals = dict.fromkeys(CLASSES, 0)
    for c in cls:
        totals[c] += 1
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
           f'font-family="Helvetica,Arial,sans-serif" font-size="11">',
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
           f'<text x="{left}" y="22" font-size="16" font-weight="bold">Olympus E-PM2 v1.6, firmware block 0 '
           f'({n / 1048576:.1f} MiB) with the current patch stack</text>',
           f'<text x="{left}" y="40" fill="#444">Address order, left to right, top to bottom. One cell = 256 bytes; '
           f'one row = 64 KiB. A cell shows the most important thing inside it, so small patches are visible. '
           f'Black bars: ranges copied to RAM.</text>']
    # legend
    x, y = left, 58
    for i, (k, (_, col, label)) in enumerate(CLASSES.items()):
        cx, cy = x + (i % 3) * 350, y + (i // 3) * 20
        size = totals[k]
        txt = f"{label}: {size / 1024:,.1f} KiB" if size >= 10240 else f"{label}: {size:,} B"
        svg.append(f'<rect x="{cx}" y="{cy}" width="12" height="12" fill="{col}" stroke="#555" stroke-width="0.5"/>'
                   f'<text x="{cx + 18}" y="{cy + 10}">{txt}</text>')
    # cells, merged into runs
    for r in range(rows):
        run_c, run_x = None, 0
        for c in range(COLS + 1):
            cell = None
            if c < COLS:
                lo = (r * COLS + c) * CELL
                if lo < n:
                    seg = cls[lo:lo + CELL]
                    best = max(set(seg), key=lambda k: (prio[k], seg.count(k)))
                    cell = best
            if cell != run_c:
                if run_c is not None:
                    svg.append(f'<rect x="{left + run_x * PX}" y="{top + r * PX}" width="{(c - run_x) * PX}" '
                               f'height="{PX}" fill="{CLASSES[run_c][1]}"/>')
                run_c, run_x = cell, c
    # address labels every 1 MiB
    for r in range(0, rows, 16):
        a = BASE + r * COLS * CELL
        svg.append(f'<text x="{left - 6}" y="{top + r * PX + 9}" text-anchor="end" fill="#333">0x{a:08X}</text>'
                   f'<line x1="{left - 4}" y1="{top + r * PX}" x2="{left}" y2="{top + r * PX}" stroke="#333"/>')
    # right side: black bars = ranges copied to RAM; labels = what is there (docs/firmware-map.md)
    xr = left + COLS * PX + 8
    for lo, hi, name, when in LOADS:
        r0 = (lo - BASE) // (CELL * COLS)
        r1 = (min(hi, BASE + n) - 1 - BASE) // (CELL * COLS)
        if r0 < rows:
            svg.append(f'<line x1="{xr}" y1="{top + r0 * PX}" x2="{xr}" y2="{top + (r1 + 1) * PX}" '
                       f'stroke="#222" stroke-width="3"/>')
    last = 0
    for a, name in MODULES:
        y0 = top + (a - BASE) // (CELL * COLS) * PX
        y = max(y0 + 4, last + 13)
        last = y
        svg.append(f'<polyline points="{xr + 4},{y0 + 1} {xr + 14},{y - 3} {xr + 20},{y - 3}" fill="none" '
                   f'stroke="#888" stroke-width="0.7"/>'
                   f'<text x="{xr + 24}" y="{y}">{name} <tspan fill="#777">0x{a:08X}</tspan></text>')
    # totals bar
    by = top + rows * PX + 30
    svg.append(f'<text x="{left}" y="{by - 8}" font-weight="bold">Share of block 0</text>')
    x = left
    width = COLS * PX
    for k, (_, col, label) in sorted(CLASSES.items(), key=lambda kv: -totals[kv[0]]):
        w = totals[k] / n * width
        if w <= 0:
            continue
        svg.append(f'<rect x="{x:.2f}" y="{by}" width="{w:.2f}" height="26" fill="{col}"/>')
        if w > 70:
            svg.append(f'<text x="{x + 4:.2f}" y="{by + 17}" fill="#fff">{totals[k] / n * 100:.1f}%</text>')
        x += w
    svg.append(f'<text x="{left}" y="{by + 46}" fill="#444">Free and unproven areas come from docs/code-space-map.tsv '
               f'(tools/freespace.py). Code vs data follows the function database, so tables inside code pages '
               f'show as code.</text>')
    svg.append("</svg>")
    open(out, "w").write("\n".join(svg))
    return totals


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("specs", nargs="*")
    ap.add_argument("-o", "--out", default=os.path.join(ROOT, "docs/memory-map.svg"))
    a = ap.parse_args()
    _, classes = classify(a.specs or DEFAULT_SPECS)
    t = render(classes, a.out)
    for k, v in sorted(t.items(), key=lambda kv: -kv[1]):
        print(f"{CLASSES[k][2]:42} {v:>10,} B")
    print("wrote", os.path.relpath(a.out, ROOT))
