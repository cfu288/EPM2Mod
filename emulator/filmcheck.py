#!/usr/bin/env python3
"""The film check: which table each colour stage selects, for every art code, on a build with the film structure.

    uv run python emulator/filmcheck.py data/builds/NAME.json [--layout build/stock-films/layout.json]

Two states of the build's block 0 are checked in om-emu. Exit status 1 on any mismatch.
  * as flashed (no film loaded): every art code that an Olympus filter can have selects what it selects on the stock
    firmware, in each stage of STAGES;
  * every entry loaded (the layout's film words written, as the loader writes them): each film code selects the
    entry's RAM block in the tone, matrix, six-axis, saturation and chroma stages, the identity table in the look
    stage, and a table with no record on in the 12-region stage.
A stage that is not in STAGES is not checked: add a stage here when the firmware is found to have one more
(docs/dev/colour-pipeline.md, section 1). The layout is the file that gen/stock-films/structure.py writes; it must
be the layout of the build's structure spec (the stock bytes of each switched word are checked against the image).
"""
import argparse
import json
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import omemu  # noqa: E402
import patchblock  # noqa: E402

BASE = omemu.BASE
OUT = omemu.DATA
IDENTITY_LOOK = 0x7E75B8F0
TONE_ENTRY, LOOK_ENTRY, MATRIX_CHAIN, TWELVE_ENTRY = 0x7E56B790, 0x7E56E837, 0x7E56C6A5, 0x7E56E661
MATRIX_EXITS = {0x7E56C6B8: "table 1", 0x7E56C6C3: "table 2", 0x7E56C764: "film matrix", 0x7E56C76B: "none"}
# Jump tables of u32 handler addresses: (table, the art code of entry 0, the stage's common tail)
SIX_JUMP, SAT_JUMP, CHROMA_JUMP = (0x7E78C254, 9, 0x7E56D8D8), (0x7E78C514, 69, 0x7E56DD79), (0x7E78AEA4, 69, 0x7E566810)
TWELVE_MASK_AT, TWELVE_BYTES = 3024, 3028
ART_CODES = range(69, 185)          # the codes that art_GetFilterType gives are in this range (stage range tests)


def word(image, addr):
    return struct.unpack_from("<I", image, addr - BASE)[0]


def tone(emu, code):
    """The three tone table pointers (R, G, B) of the stills pair member."""
    emu.write(OUT, bytes(12))
    emu.call(TONE_ENTRY, {"d0": 0, "d1": 1, "a0": OUT, "a1": OUT + 4}, stack=[0, 0, code, 0, OUT + 8], trace=False)
    return struct.unpack("<3I", emu.read(OUT, 12))


def look(emu, code):
    """The look table pointer, for both values of the flag d1."""
    return tuple(emu.call(LOOK_ENTRY, {"d0": 0, "d1": d1, "a0": 0, "a1": 0}, stack=[0, code, 0, 1, 0, 0],
                          trace=False)["regs"]["a0"] for d1 in (0, 1))


def run_to(emu, pc, stops, regs):
    """Run from pc to one of stops; return the registers there."""
    init = {"pc": pc, "sp": omemu.SP0, "mdr": 0, "psw": 0}
    init.update(regs)
    emu.req("reset", regs=init)
    r = emu.req("cont", stops=list(stops))
    rg = emu.regs_of(r)
    if r["stop"] != "break" or rg["pc"] not in stops:
        raise omemu.EmuError(f"stop {r['stop']} at pc 0x{rg['pc']:08x}")
    return rg


def matrix(emu, code):
    """Which continuation the art-matrix chain reaches, and the matrix address when it is a film matrix."""
    rg = run_to(emu, MATRIX_CHAIN, MATRIX_EXITS, {"d0": code, "d3": 0})
    kind = MATRIX_EXITS[rg["pc"]]
    return (kind, rg["a1"]) if kind == "film matrix" else (kind,)


def handler(emu, jump, code):
    table, first, _ = jump
    return word(emu.image, table + 4 * (code - first))


def six_axis(emu, code):
    """The saturation and hue records of the code's handler, or the handler when it does not reach the tail."""
    h = handler(emu, SIX_JUMP, code)
    try:
        rg = run_to(emu, h, [SIX_JUMP[2]], {"d3": code, "d2": 0, "a3": 0, "a2": 0})
    except omemu.EmuError:
        return ("handler", h)                 # a handler with its own path (statistics, default): compared as it is
    return (rg["a3"], rg["a2"])


def saturation(emu, code):
    h = handler(emu, SAT_JUMP, code)
    try:
        return (run_to(emu, h, [SAT_JUMP[2]], {"a3": 0})["a3"],)
    except omemu.EmuError:
        return ("handler", h)


def chroma(emu, code):
    """The first of the six pointers the code's handler stores (the start of its chroma record)."""
    h = handler(emu, CHROMA_JUMP, code)
    emu.write(OUT, bytes(32))
    emu.write(omemu.SP0 + 4, struct.pack("<I", OUT))
    try:
        run_to(emu, h, [CHROMA_JUMP[2]], {})
    except omemu.EmuError:
        return ("handler", h)
    return (emu.u32(OUT),)


def twelve(emu, code):
    """The 12-region table the selector gives (sRGB, Natural): its address, enable mask and bytes."""
    job, p, key, out = OUT, OUT + 0x400, OUT + 0x800, OUT + 0x1000
    for a, n in ((job, 0x400), (p, 0x400), (key, 0x100), (out, 0x400)):
        emu.write(a, bytes(n))
    emu.write(job + 96, struct.pack("<I", p))
    emu.write(p + 79, bytes([code, 0, 0, 0, 2]))        # P+79 art code, P+82 colour space, P+83 picture mode
    emu.call(TWELVE_ENTRY, {"a0": job, "a1": key, "d0": 0, "d1": out}, trace=False)
    tab = emu.u32(out + 884) - 336
    data = emu.read(tab, TWELVE_BYTES)
    return (tab, struct.unpack_from("<H", data, TWELVE_MASK_AT)[0], data)


# Jump-table stages take only the codes of their table; the others test the range themselves.
STAGES = [("tone", tone, ART_CODES), ("look", look, ART_CODES), ("matrix", matrix, ART_CODES),
          ("six-axis", six_axis, ART_CODES), ("saturation", saturation, ART_CODES),
          ("chroma", chroma, range(69, 169)), ("12-region", twelve, ART_CODES)]


def selections(image, codes):
    """{(stage, code): what the stage selects} on a block-0 image."""
    fd, path = tempfile.mkstemp(suffix=".block0.bin", prefix="filmcheck-")
    os.write(fd, image)
    os.close(fd)
    out = {}
    try:
        with omemu.Emu() as emu:
            emu.load(path)
            for name, fn, limit in STAGES:
                for code in codes:
                    if code in limit:
                        try:
                            out[name, code] = fn(emu, code)
                        except (omemu.EmuError, RuntimeError) as error:
                            out[name, code] = ("error", str(error))
    finally:
        os.unlink(path)
    return out


def loaded(image, layout):
    """The image with every entry's switched words in their film state."""
    data = bytearray(image)
    for entry in layout["entries"]:
        for w in entry["switch"]:
            a, film, stock = w["address"] - BASE, bytes.fromhex(w["film"]), bytes.fromhex(w["stock"])
            ram = layout["matptr"] <= w["address"] < layout["matptr"] + 16    # RAM: its stock bytes are not flashed
            if not ram and data[a:a + len(stock)] != stock:
                raise SystemExit(f"{entry['name']}: {w['note']}: the image does not hold the layout's stock bytes "
                                 "(the layout is not this build's)")
            data[a:a + len(film)] = film
    return bytes(data)


def film_wants(layout, k):
    """What each stage must select for entry k with a film."""
    off, b = layout["offsets"], layout["film_ram"] + layout["block"] * k
    tone_ok = lambda got: all(b + off["tone"] + 4096 * ch <= p < b + off["tone"] + 4096 * (ch + 1) and
                              (p - b) % 512 == 0 for ch, p in enumerate(got))
    return {"tone": tone_ok, "look": lambda got: got == (IDENTITY_LOOK, IDENTITY_LOOK),
            "matrix": lambda got: got == ("film matrix", b + off["matrix"]),
            "six-axis": lambda got: got == (b + off["six_s"], b + off["six_h"]),
            "saturation": lambda got: got == (b + off["sat"],),
            "chroma": lambda got: got == (b + off["chroma"],),
            "12-region": lambda got: got[0] != "error" and got[1] == 0}


def show(got):
    return " ".join(f"0x{v:08x}" if isinstance(v, int) else str(v) for v in got if not isinstance(v, bytes))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("build", help="a build description (data/builds/NAME.json)")
    ap.add_argument("--layout", default=os.path.join(ROOT, "build", "stock-films", "layout.json"))
    args = ap.parse_args()
    os.chdir(ROOT)
    layout = json.load(open(args.layout))
    stock, image, _ = patchblock.patched_block0(json.load(open(args.build))["specs"])
    films = {e["code"]: k for k, e in enumerate(layout["entries"])}
    in_place = {e["code"] for e in layout["entries"] if e["kind"] == "inplace"}
    olympus = [c for c in ART_CODES if c not in films or c in in_place]
    bad = 0

    before, after = selections(stock, olympus), selections(image, olympus)
    for key in sorted(before, key=lambda k: (k[1], k[0])):
        if before[key] != after[key]:
            bad += 1
            print(f"as flashed: code {key[1]} {key[0]}: stock {show(before[key])}, build {show(after[key])}")
    print(f"as flashed: {len(before)} selections of {len(olympus)} Olympus codes in {len(STAGES)} stages compared "
          "with the stock firmware")

    got = selections(loaded(image, layout), sorted(films))
    for code, k in sorted(films.items(), key=lambda x: x[1]):
        wants = film_wants(layout, k)
        wrong = [f"{name}: {show(got[name, code])}" for name, _, _ in STAGES if not wants[name](got[name, code])]
        bad += len(wrong)
        print(f"loaded: {layout['entries'][k]['name']:18s} code {code:3d}: " +
              ("every stage selects the film's place" if not wrong else "WRONG " + "; ".join(wrong)))
    print("RESULT", "PASS" if not bad else f"FAIL ({bad})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
