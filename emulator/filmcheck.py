#!/usr/bin/env python3
"""The film check: what each colour stage selects and what the job builders write, for every art code, on a build
with the film structure.

    uv run python emulator/filmcheck.py data/builds/NAME.json [--layout build/stock-films/layout.json]

Two states of the build's block 0 are checked in om-emu. Exit status 1 on any mismatch. About 35 s.
  * as flashed (no film loaded): every art code that an Olympus filter can have selects what it selects on the stock
    firmware, in each stage of STAGES, and gives the same blocks as the stock firmware;
  * every entry loaded (the layout's film words written, as the loader writes them): each film code selects the
    entry's RAM block in the tone, matrix, six-axis, saturation and chroma stages, the identity table in the look
    stage, and a table with no record on in the 12-region stage; and its blocks differ from the blocks of the same
    job without an art code (Picture Mode Natural) only in the bytes of those seven stages, has in the look word
    Natural's table or the identity table, and does not have Natural's 12-region bytes (unless the job gives the
    film Natural's whole block: PRM+20 bit 16 switches the art code off in every stage, on stock too).

The blocks are what the firmware's builders pack for one job: the gamma buffer G (0x7E56A2E8), block A of a still
(0x7E56224C), the third block of a still (0x7E5625DC) and block B of live view (0x7E562404). Every stage of the
builders writes its choice into one of them, so a stage that nobody listed shows there too (WRITERS says which
builder call writes which bytes). Each is built for the synthetic jobs of JOBS, sRGB.

Not covered:
  * a wrong choice inside a film stage's own bytes shows only in that stage's check of STAGES (one job each),
    except the two block rules for the look word and the 12-region bytes;
  * the films' table contents: the film RAM is not filled here, and blocks A and B of a film get Natural's gamma
    buffer, so that what the builders make from it compares;
  * code that switches on the art code outside the four builders (the effect filters' pixel program, Cross Process's
    hue routine, white balance), and job fields that no job of JOBS sets;
  * the third block's first stage divides by zero on these jobs; the run goes on as the MN103 does, so those bytes
    are compared but are not what a real job gives;
  * RAM that the builders keep between jobs is not reset: every image runs the same jobs in the same order.
A stage that is not in STAGES is not checked on its own: add it when the firmware is found to have one more
(docs/dev/colour-pipeline.md, section 1). The layout is the file that gen/stock-films/structure.py writes; it must
be the layout of the build's structure spec (the stock bytes of each switched word are checked against the image).
"""
import argparse
import concurrent.futures
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


# --- whole blocks -----------------------------------------------------------------------------------------------------
# Buffers of one synthetic job. PRM is the job's parameter record (job+96 points at it): +79 art code, +82 colour
# space, +83 picture mode.
JOB, PRM, BLK, MASK, GAMMA, WORK, KEY = (OUT + 0x1000 * n for n in (16, 18, 20, 22, 23, 25, 26))
FMUL, FMUL_RET = 0x7E5018E8, omemu.PADS       # om-emu's float unit faults on this multiply: done in Python
# (name, builder, registers, stack words, the buffer it fills, bytes). Arguments as at the call sites 0x7E560C98,
# 0x7E560CCC, 0x7E560D6F and 0x7E560D37.
BUILDERS = [("G", 0x7E56A2E8, {"a0": JOB, "a1": MASK, "d0": GAMMA}, (), GAMMA, 1584),
            ("A", 0x7E56224C, {"a0": BLK, "a1": JOB, "d0": MASK, "d1": GAMMA}, (WORK, KEY), BLK, 1948),
            ("3", 0x7E5625DC, {"a0": BLK, "a1": JOB, "d0": MASK, "d1": KEY}, (), BLK, 364),
            ("B", 0x7E562404, {"a0": BLK, "a1": JOB, "d0": MASK, "d1": GAMMA}, (WORK, KEY), BLK, 1672)]
# Job name -> bytes of PRM that differ from the plain job. Each field changes a block of some code, except PRM+99
# and PRM+90 (tone arguments: no code tried shows an effect). The u16 at PRM+62 acts as an ISO level: 0x900 changes
# the chroma suppression bytes and the third block, 0x1000 and above the look word too.
JOBS = {"plain": {}, "P+99 & P+20 bit 0": {99: 1, 20: 1}, "P+87 & P+90 & ISO 0x900": {87: 1, 90: 1, 63: 0x09},
        "ISO 0x2000": {63: 0x20}, "P+20 bit 11": {21: 8}, "P+20 bit 16": {22: 1}}
# Which call of a builder writes which bytes of its block: (first, end, writer). Measured on films-twelve-off with
# every entry loaded: a write watch on the block, read at each return into the builder, for the jobs of JOBS and one
# job per single field, and codes 0, 69 to 184 in steps of 5, 85, 94, 104, 105, 117, 121, 128, 159. A writer with a
# stage's name is the call that hosts that stage; an address is the builder's callee. A flag word that several calls
# write belongs to the first. In G the tone bytes are the six table pointers and G+1581 is the art code itself.
WRITERS = {
    "G": [(8, 32, "tone"), (1581, 1582, "art code"), (0, 1056, "gamma 0x7E56AEAF"), (1568, 1582, "gamma 0x7E56AEAF")],
    "A": [(56, 68, "head 0x7E56B3EA"), (148, 149, "head 0x7E56B3EA"), (136, 151, "0x7E56B421"),
          (212, 364, "knee 0x7E56B446"), (152, 160, "0x7E56B55F"), (160, 180, "matrix"), (180, 204, "six-axis"),
          (924, 1948, "rec-view gamma 0x7E56B6D1"), (204, 208, "saturation"), (132, 136, "0x7E56B8E7"),
          (568, 860, "12-region"), (884, 924, "12-region"), (880, 884, "look"),
          (68, 124, "chroma suppression 0x7E56B9B6"), (356, 360, "chroma suppression 0x7E56B9B6"),
          (124, 132, "sharpening 0x7E56BA1D"), (208, 212, "sharpening 0x7E56BA1D")],
    "3": [(44, 208, "0x7E5653F1"), (208, 344, "chroma"), (344, 364, "0x7E5654F7")],
    "B": [(32, 44, "head 0x7E56B3FD"), (76, 77, "head 0x7E56B3FD"), (64, 79, "0x7E56B42E"),
          (140, 204, "knee 0x7E56B4F5"), (80, 88, "0x7E56B56C"), (88, 108, "matrix"), (108, 132, "six-axis"),
          (648, 1672, "rec-view gamma 0x7E56B6FE"), (132, 136, "saturation"), (60, 64, "0x7E56B909"),
          (644, 648, "look"), (44, 52, "chroma suppression 0x7E56B9E9"), (52, 60, "sharpening 0x7E56BA49"),
          (136, 140, "sharpening 0x7E56BA49"), (408, 544, "chroma"), (544, 624, "art effect 0x7E56BA7A")]}
FILM_WRITERS = {"tone", "art code", "matrix", "six-axis", "saturation", "chroma", "look", "12-region"}


def writer(block, at):
    return next((name for lo, hi, name in WRITERS[block] if lo <= at < hi), "no writer measured")


def build(emu, entry, regs, stack):
    """Call a builder. The float multiply is done in Python; a division by zero goes on as on the MN103 (V set)."""
    end = omemu.TRAMP + 7
    emu.write(omemu.TRAMP, b"\xdd" + struct.pack("<I", (entry - omemu.TRAMP) & 0xFFFFFFFF) +
              bytes(emu.frame_of(entry)) + b"\xca\x00")
    emu.write(FMUL_RET, b"\xde\xc0\x08")                    # retf [d2,d3],8: the frame of every call of FMUL
    emu.write(omemu.SP0 + 4, struct.pack("<14I", *stack, *[0] * (14 - len(stack))))
    emu.req("reset", regs={"pc": omemu.TRAMP, "sp": omemu.SP0, "mdr": 0, "psw": 0, **regs})
    while True:
        r = emu.req("cont", stops=[end, FMUL])
        rg = emu.regs_of(r)
        if r["stop"] == "break" and rg["pc"] == end:
            return
        if r["stop"] == "break":
            x, y = (struct.unpack("<f", struct.pack("<I", rg[k]))[0] for k in ("d0", "d1"))
            emu.req("setRegs", regs={"d0": struct.unpack("<I", struct.pack("<f", x * y))[0], "pc": FMUL_RET})
        elif r["stop"] == "fault" and r.get("fault") == 6 and emu.read(rg["pc"], 1) == b"\xf2":      # div, divu
            emu.req("setRegs", regs={"pc": rg["pc"] + 2, "psw": rg["psw"] | 8, "fault": 0})
        else:
            raise omemu.EmuError(f"stop {r['stop']} at pc 0x{rg['pc']:08x}")


def blocks(emu, code, fields, gamma=None):
    """{builder name: its block, or the error text} of one job. gamma: the gamma buffer that A and B get instead of
    the job's own."""
    for a, n in ((JOB, 0x2000), (MASK, 0x200), (GAMMA, 0x800), (WORK, 0x800)):
        emu.write(a, bytes(n))
    emu.write(KEY, b"\xff" * 0x200)                         # the key of the tables last sent: none
    emu.write(JOB + 96, struct.pack("<I", PRM))
    p = bytearray(0x400)
    struct.pack_into("<9h", p, 24, 256, 0, 0, 0, 256, 0, 0, 0, 256)      # a unit matrix and four unit gains (inferred)
    struct.pack_into("<4H", p, 42, 256, 256, 256, 256)
    struct.pack_into("<H", p, 62, 0x500)
    p[79], p[83] = code, 2                                  # the art code; Picture Mode Natural; sRGB (PRM+82 = 0)
    for at, value in fields.items():
        p[at] = value
    emu.write(PRM, bytes(p))
    out = {}
    for name, entry, regs, stack, buf, size in BUILDERS:
        emu.write(MASK, b"\xff" * 4)                        # the stages to build: all
        emu.write(BLK, bytes(0x800))
        if gamma and name in "AB":
            emu.write(GAMMA, gamma)
        try:
            build(emu, entry, regs, stack)
            out[name] = emu.read(buf, size)
        except (omemu.EmuError, RuntimeError) as error:
            out[name] = f"error: {error}"
    return out


def block_sets(image, codes, neutral_gamma=False):
    """{(job, code): blocks} on a block-0 image, with code 0 (no art code) first in each job."""
    fd, path = tempfile.mkstemp(suffix=".block0.bin", prefix="filmcheck-")
    os.write(fd, image)
    os.close(fd)
    out = {}
    try:
        with omemu.Emu(insn_limit=50_000_000) as emu:
            emu.load(path)
            for job, fields in JOBS.items():
                for code in [0] + list(codes):
                    gamma = out[job, 0]["G"] if neutral_gamma and code else None
                    out[job, code] = blocks(emu, code, fields, gamma if isinstance(gamma, bytes) else None)
    finally:
        os.unlink(path)
    return out


def differences(a, b, block):
    """[(first, end, writer)]: per writer, the span of its bytes that differ between two blocks. A block that could
    not be built is one difference with the error text as its writer."""
    if isinstance(a, str) or isinstance(b, str):
        return [(0, 0, a if isinstance(a, str) else b)]
    out = {}
    for at in (i for i in range(len(a)) if a[i] != b[i]) if a != b else ():
        name = writer(block, at)
        out[name] = (out.get(name, (at,))[0], at + 1)
    return [(lo, hi, name) for name, (lo, hi) in out.items()]


def report(found):
    """Print one line per difference with the jobs that show it; return the number of lines."""
    for (who, block, lo, hi, what), jobs in found.items():
        print(f"{who}: block {block} +{lo}..+{max(lo, hi - 1)} ({what}); jobs: {', '.join(jobs)}")
    return len(found)


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

    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        before, after = pool.map(block_sets, (stock, image), (olympus, olympus))
    found = {}
    for (job, code), want in before.items():
        for block, data in want.items():
            for lo, hi, name in differences(data, after[job, code][block], block):
                key = (f"as flashed: code {code}", block, lo, hi, name + ": not as on stock")
                found.setdefault(key, []).append(job)
    bad += report(found)
    print(f"as flashed: blocks {', '.join(b[0] for b in BUILDERS)} of {len(olympus) + 1} codes in {len(JOBS)} jobs "
          "compared with the stock firmware")

    got = block_sets(loaded(image, layout), sorted(films), neutral_gamma=True)
    found = {}
    for (job, code), have in got.items():
        for block, data in have.items() if code else ():
            who, natural = f"loaded: {layout['entries'][films[code]]['name']} code {code}", got[job, 0][block]
            for lo, hi, name in differences(natural, data, block):
                if name not in FILM_WRITERS:
                    found.setdefault((who, block, lo, hi, name + ": differs from Natural"), []).append(job)
                elif name == "look" and data[lo - lo % 4:hi + -hi % 4] != struct.pack("<I", IDENTITY_LOOK):
                    found.setdefault((who, block, lo, hi, "look: not Natural's, not identity"), []).append(job)
            spans = [(lo, hi) for lo, hi, name in WRITERS[block] if name == "12-region"]
            # the fault of films-look-exif: the art code acts, and the 12-region records are Natural's, all on
            if spans and data != natural and all(data[lo:hi] == natural[lo:hi] for lo, hi in spans):
                found.setdefault((who, block, spans[0][0], spans[-1][1], "12-region: Natural's bytes"), []).append(job)
    bad += report(found)
    print(f"loaded: blocks of {len(films)} film codes in {len(JOBS)} jobs compared with Natural: " +
          ("they differ only in the films' stages" if not found else f"{len(found)} faults"))
    print("RESULT", "PASS" if not bad else f"FAIL ({bad})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
