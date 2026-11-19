"""Write data/specs/peaking-fast.json: a faster colour loop for Red / Yellow / Blue peaking.

Research code. NOTES.md section 17. The spec is a delta on the pinned build data/builds/peaking-colours.json: every
`expect` is a byte string of that build, not of the stock file.

The pinned loop (T_COL of peaking-colours) looks at every row: 3 word reads and 11 instructions for each group of
4 pixels, and for a group with a line pixel 4 byte reads and 3 byte writes per line pixel. All of them go through
the uncached alias of the RAM. The new loop T_FAST:
  - looks at every second row. A group of 4 pixels (12 bytes) is tested with 2 word reads and 7 instructions:
    bytes 0-3 and 8-11 (pixel 0, the first byte of pixel 1, the last byte of pixel 2, pixel 3). The line image
    is grey, so this sees every pixel of the group;
  - when a byte is 64 or more, it writes the colour over the whole group in this row and in the next row:
    6 word writes. So the lines are drawn in blocks of 4 x 2 pixels.
One op replaces the first instructions of the pinned row loop (5 bytes at OLD_L1) with `jmp T_FAST`. The pinned
set-up (colour, buffers, sizes, the checks) and the two exits stay in use. White and Off do not reach this code.

Usage: mkspec_fast.py OUT.json PINNED_DIR WORKDIR [LISTING.txt]
  PINNED_DIR  `python3 tools/oetool.py unpack build/peaking-colours.BIN PINNED_DIR`
  WORKDIR     scratch folder for the assembler files (outside the repository)
"""
import hashlib, json, os, re, struct, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BASE = 0x7E421020
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
PINNED_SHA = "4d6b1f26ed92d66b62b4d7dc32d26168e33fd8b153a7655d6c0d9a58267456f8"
BIN = os.path.join(os.path.abspath(__file__).split("/experiments/")[0], "build", "toolchain", "bin")

THRESHOLD = 64
# T_COL of peaking-colours (results/colours-new-code.txt)
OLD_L1, OLD_L1_BYTES = 0x7E4C9453, "580092f162"     # row loop: mov (sp),d0 / mov a0,a2 / add d0,a2
OLD_DONE = 0x7E4C947E                               # add 8,sp / movm / clr d0 / jmp: usGain2 = 0
OLD_WHITE = 0x7E4C9489                              # add 8,sp / movm / mov 512,d0 / jmp: white lines
# two 0xFF runs of the kernel range that the pinned build and the log specs leave free
AREAS = {".fa": (0x7E4C9184, 0x7E4C9200), ".fb": (0x7E4C90CA, 0x7E4C90FC)}     # between them: the 240-frame list

ASM = """
.section .fa,"ax"
T_FAST:                      # from the pinned T_COL, in place of its row loop. d3 = colour (byte 0 | byte 1 << 8 |
                             # byte 2 << 16), a0 = line image, a1 = picture (both at a multiple of 4), a3 = rows,
                             # d2 = (4,sp) = bytes from the end of the looked-at part of a row to the next row,
                             # (0,sp) = bytes of a row that are looked at (12 per group of 4 pixels, not 0)
    mov (0,sp),d1
    add d2,d1                # bytes from row to row
    mov a3,d0
    lsr 1,d0                 # pairs of rows
    beq 9f
    btst 3,d1
    beq 0f
9:  jmp s_%(white)08x          # one row, or rows that do not start at a multiple of 4: white lines
0:  add -16,sp
    mov d0,(0,sp)            # pairs of rows left
    mov d1,(4,sp)            # bytes from row to row
    mov a1,d2
    mov a0,d0
    sub d0,d2                # picture - line image
    mov d3,d0
    lsr 8,d0
    mov d3,d1
    asl 16,d1
    or d1,d0
    mov d0,(8,sp)            # second word of four pixels of the colour
    mov d3,d0
    lsr 16,d0
    mov d3,d1
    asl 8,d1
    or d1,d0
    mov d0,(12,sp)           # third word
    mov d3,d0
    asl 24,d0
    or d0,d3                 # first word
1:  mov (16,sp),d0
    mov a0,a2
    add d0,a2                # end of the looked-at part of the row
2:  mov (a0),d0              # bytes 0-3 of the group: pixel 0 and the first byte of pixel 1
    mov (8,a0),d1            # bytes 8-11: the last byte of pixel 2 and pixel 3
    or d1,d0
    and %(mask)d,d0          # no byte >= THRESHOLD: no line pixel in this group
    bne 4f
3:  add 12,a0
    cmp a2,a0
    bne 2b
    mov (20,sp),d0
    add d0,a0                # the next row (it is not looked at)
    mov (4,sp),d0
    add d0,a0                # the row after it
    mov (0,sp),d0
    add -1,d0
    mov d0,(0,sp)
    bne 1b
    add 16,sp
T_FAST_END:
    jmp s_%(done)08x           # usGain2 = 0: the combine job writes the picture back as it is
4:  jmp T_HIT
    nop                      # the op must not end in 0xFF bytes: the free-space ledger counts only changed bytes

.section .fb,"ax"
T_HIT:                       # the colour over the 4 pixels of the group, in this row and in the next row
    mov a0,a1
    add d2,a1
    mov (4,sp),d0
    mov a1,a3
    add d0,a3
    mov d3,(a1)
    mov d3,(a3)
    mov (8,sp),d0
    mov d0,(4,a1)
    mov d0,(4,a3)
    mov (12,sp),d0
    mov d0,(8,a1)
    mov d0,(8,a3)
    jmp 3b
    nop
"""


def run(*a):
    return subprocess.run(a, check=True, capture_output=True, text=True).stdout


def main():
    out, pinned, work = sys.argv[1:4]
    listing = sys.argv[4] if len(sys.argv) > 4 else None
    os.makedirs(work, exist_ok=True)
    blk = open(os.path.join(pinned, "block0_0100.bin"), "rb").read()
    get = lambda a, n: blk[a - BASE:a - BASE + n]
    ops = []

    def op(addr, new, note):
        expect = get(addr, len(new))
        assert expect != new, note
        ops.append({"type": "bytes", "block": 0, "offset": "0x%X" % (addr - BASE), "expect": expect.hex(),
                    "new": new.hex(), "_addr": "0x%08X" % addr, "_note": note})

    assert get(OLD_L1, 5).hex() == OLD_L1_BYTES
    assert get(OLD_DONE, 6).hex() == "f8fe08cef000" and get(OLD_WHITE, 8).hex() == "f8fe08cef02c0002"
    asm = ASM % {"mask": -(0x100000000 - 0x01010101 * (256 - THRESHOLD)), "white": OLD_WHITE, "done": OLD_DONE}
    assert THRESHOLD in (64, 128)
    args = ["--defsym=s_%s=0x%s" % (a, a) for a in sorted(set(re.findall(r"s_([0-9a-f]{8})", asm)))]
    asm += '\n.section .hook,"ax"\n    jmp T_FAST\n'
    args += ["--section-start=%s=%#x" % (n, lo) for n, (lo, hi) in AREAS.items()] + ["--section-start=.hook=%#x" % OLD_L1]
    s, o, e, sb = (os.path.join(work, "fast." + x) for x in ("s", "o", "elf", "bin"))
    open(s, "w").write(asm)
    run(BIN + "/mn10300-elf-as", "-o", o, s)
    run(BIN + "/mn10300-elf-ld", *args, "-e", "%#x" % AREAS[".fa"][0], "-o", e, o)
    sym = {l.split()[2]: int(l.split()[0], 16) for l in run(BIN + "/mn10300-elf-nm", e).splitlines() if len(l.split()) == 3}

    def sect(name):
        run(BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", name, e, sb)
        return open(sb, "rb").read()

    report = []
    for name, (lo, hi) in AREAS.items():
        code = sect(name)
        assert lo + len(code) <= hi, "%s: %d bytes, %d free" % (name, len(code), hi - lo)
        assert get(lo, hi - lo) == b"\xff" * (hi - lo) and code[-1] != 0xFF, name
        op(lo, code, "new code, kernel range, 0xFF run: %s (%d B)" % ("T_FAST" if name == ".fa" else "T_HIT", len(code)))
        report.append("%s: %d B at 0x%X-0x%X, %d B free after" % (name, len(code), lo, lo + len(code), hi - lo - len(code)))
    hook = sect(".hook")
    assert len(hook) == 5 and hook[0] == 0xDC and sym["T_FAST"] == AREAS[".fa"][0]
    op(OLD_L1, hook, "T_COL of peaking-colours, the first instructions of its row loop (`mov (sp),d0` / `mov a0,a2` / "
       "`add d0,a2`) -> `jmp T_FAST`")
    spec = {
        "name": "peaking-fast",
        "description": "Focus peaking in colour, a faster colour loop. The pinned loop looks at every row and writes "
                       "each line pixel byte by byte. The new loop T_FAST looks at every second row with 2 word reads "
                       "per group of 4 pixels, and writes the colour over the whole group in that row and the next "
                       "one with 6 word writes: the lines are drawn in blocks of 4 x 2 pixels. About 3 times fewer "
                       "instructions and bus reads for a frame without lines, and about 10 times fewer bus accesses "
                       "for the lines. White and Off do not change. A delta on data/builds/peaking-colours.json: every "
                       "expect is a byte string of that build. See experiments/2026-11-14-focus-peaking/NOTES.md "
                       "section 17.",
        "base": STOCK,
        "base_sha256": hashlib.sha256(open(os.path.join(ROOT, STOCK), "rb").read()).hexdigest(),
        "status": "candidate: emulator-checked, not flashed",
        "_delta_on": "data/builds/peaking-colours.json (sha256 %s)" % PINNED_SHA,
        "_ram": "no new RAM; 16 more bytes of the ART task's stack (40 in all)",
        "_symbols": {k: "0x%08X" % sym[k] for k in ("T_FAST", "T_FAST_END", "T_HIT")},
        "ops": ops,
    }
    json.dump(spec, open(out, "w"), indent=1)
    open(out, "a").write("\n")
    print("wrote", out, len(ops), "ops")
    print("\n".join(report))
    if listing:
        txt = run(BIN + "/mn10300-elf-objdump", "-d", "-j", ".fa", "-j", ".fb", "-j", ".hook", e)
        open(listing, "w").write(re.sub(r"/[^\s:]*fast\.elf", "fast.elf", txt))


main()
