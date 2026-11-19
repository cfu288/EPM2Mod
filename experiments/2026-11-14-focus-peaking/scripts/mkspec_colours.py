"""Write data/specs/peaking-colours.json: the Peaking list becomes Off / White / Red / Yellow / Blue.

Research code. NOTES.md section 16. The spec is a delta on the pinned build data/builds/peaking-menu-names.json: every
`expect` is a byte string of that build, not of the stock file.

What it writes:
  (a) mode controller: the value list of setting 458 (record 0x7E84C584) is 1, 2, 3 at 0x7E849F25. The record now
      points to the first five bytes of the stock list 1..10 at 0x7E849F28 (setting 473 uses it): 1, 2, 3, 4, 5;
  (b) list of panel 607: five items at ROWS = Off (value 1), White (3), Red (2), Yellow (4), Blue (5); the
      value -> text list number 607 for the row at NAMES;
  (c) code: T_K2 starts with `jmp T_K3`. T_K3: the byte C is 2, 4 or 5 -> T_COL writes the colour over the line
      pixels of the picture (3 bytes per pixel) and gives the combine job usGain2 = 0; any other value -> 512
      (white lines, as pinned);
  (d) texts, all 34 languages: the pointers of the ids 1501, 1502 and 1499 go to the colour names inside the
      stock texts 122 "R:Red", 124 "Ye:Yellow", 117 "B:Blue" (after the colon). English help text 1506.

Usage: mkspec_colours.py OUT.json PINNED_DIR WORKDIR [LISTING.txt]
  PINNED_DIR  `python3 tools/oetool.py unpack build/peaking-menu-names.BIN PINNED_DIR`
  WORKDIR     scratch folder for the assembler files (outside the repository)
"""
import hashlib, json, os, re, struct, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BASE = 0x7E421020
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
PINNED_SHA = "4ea4ffd773d6f05d16867f55b9fef4bce5d53fc8659a9b16362f7ac771a6bc30"
BIN = os.path.join(os.path.abspath(__file__).split("/experiments/")[0], "build", "toolchain", "bin")

SETTING, PANEL = 458, 607
MCON_REC, MCON_OLD, MCON_NEW = 0x7E84C584, 0x7E849F25, 0x7E849F28   # value-list record; lists 1,2,3 and 1..10
OLD_ROWS, OLD_NAMES = 0x7EBF2900, 0x7EBF2960                         # lists of peaking-menu (3 values)
ROWS, NAMES = 0x7EBF2A00, 0x7EBF2B00                                 # new lists: 5 x 28 B, 6 x 24 B
FORMATS, DESC = 0x7F014614, 0x7F00BFBC
T_OFF, T_WHITE, T_RED, T_YELLOW, T_BLUE, T_HELP = 1371, 1500, 1501, 1502, 1499, 1506
V_OFF, V_RED, V_WHITE, V_YELLOW, V_BLUE = 1, 2, 3, 4, 5              # 3 stays the value after a full reset
SOURCE = {T_RED: 122, T_YELLOW: 124, T_BLUE: 117}                    # "R:Red", "Ye:Yellow", "B:Blue" in every language
# colours as the three bytes of a pixel of the art picture buffer (IMGDMA_ADD_RGB; byte order R, G, B is inferred)
COLOURS = {V_RED: (255, 0, 0), V_YELLOW: (255, 255, 0), V_BLUE: (0, 80, 255)}
THRESHOLD = 64                                                       # a line pixel: line image byte >= 64
HELP_OLD = "Show white or black lines\r\non sharp edges while\r\nMF Assist magnifies."
HELP_NEW = "Show lines in that color \r\non sharp edges while\r\nMF Assist magnifies."
# The first line keeps its length and the letter a at index 16: peaking-menu kept that stock byte, and
# `epm2mod make` refuses a later change of a byte that an earlier spec covers and keeps.
HELP_OFF = 0x38874C

T_K2, T_K2_OLD = 0x7E4C93D8, "fca8c7e82b60"         # T_K2: movbu (C),d0
CODE = 0x7E4C93F0                                   # first free byte after T_K2 in the kernel-range 0xFF run
ASM = """
.equ CFLAG, 0x602be8c7       # C: the value of setting 458 when T_R last read it (peaking-menu)
.macro PIX o                 # one pixel of a group of four: line image byte G >= THRESHOLD -> the colour
    movbu (\\o+1,a0),d0
    cmp %(thr)d,d0
    bcs 9f
    mov d3,d1
    movbu d1,(\\o,a1)
    lsr 8,d1
    movbu d1,(\\o+1,a1)
    lsr 8,d1
    movbu d1,(\\o+2,a1)
9:
.endm
.section .k3,"ax"
T_K3:                        # jumped to from the first instruction of T_K2. The frame is Key Line pass 9's:
                             # (12,sp) = its second argument, a2 = art packet, a3 = combine job record
    movbu (CFLAG),d0
    cmp %(red)d,d0
    beq T_COL
    cmp %(yellow)d,d0
    beq T_COL
    cmp %(blue)d,d0
    beq T_COL
    mov 512,d0               # White, as pinned (peaking-gain-2x)
    jmp s_7e4c939f
T_COL:
    movm [d2,d3,a2,a3],(sp)  # 16 bytes
    add -8,sp                # (0,sp) bytes of a row that are looked at, (4,sp) bytes from there to the next row
    asl2 d0
    mov COLTAB,a0
    add d0,a0
    mov (a0),d3              # byte 0 | byte 1 << 8 | byte 2 << 16
    mov (36,sp),a0           # pass 9's second argument
    mov (32,a0),a0           # Key Line context
    mov (16,a0),a1           # colour picture, 3 bytes per pixel (pass 7 made it; the combine job writes it)
    movhu (40,a0),d1         # usInAreaHw: pixels in a row
    lsr 2,d1                 # groups of four pixels
    mov d1,d0
    asl2 d0
    mov d0,d2
    add d0,d0
    add d2,d0                # 12 bytes per group
    mov d0,(0,sp)
    movhu (36,a0),d2         # usInMemHw: pixels from row to row
    mov d2,d1
    add d2,d2
    add d1,d2
    sub d0,d2
    mov d2,(4,sp)
    movhu (42,a0),d1         # usInAreaVw: rows
    mov d1,a3
    mov (20,a0),a0           # line image, 3 bytes per pixel (pass 8 made it)
    cmp 0,d1
    beq 7f
    cmp 0,d0
    beq 7f
    mov a0,d0
    mov a1,d1
    or d1,d0
    btst 3,d0                # both buffers start at a multiple of 4 (the loop reads words)
    bne 7f
1:  mov (0,sp),d0
    mov a0,a2
    add d0,a2                # end of the row in the line image
2:  mov (a0),d0              # 12 bytes = 4 pixels of the line image
    mov (4,a0),d1
    or d1,d0
    mov (8,a0),d1
    or d1,d0
    and %(mask)d,d0          # no byte >= THRESHOLD: no line pixel in this group
    bne 4f
3:  add 12,a0
    add 12,a1
    cmp a2,a0
    bne 2b
    mov (4,sp),d0
    add d0,a0
    add d0,a1
    add -1,a3
    cmp 0,a3
    bne 1b
8:  add 8,sp
    movm (sp),[d2,d3,a2,a3]
    clr d0                   # usGain2 = 0: the combine job writes the picture back as it is
    jmp s_7e4c939f
7:  add 8,sp                 # a frame that the loop cannot take (no rows, or a buffer not at a multiple of 4):
    movm (sp),[d2,d3,a2,a3]  # white lines
    mov 512,d0
    jmp s_7e4c939f
4:  PIX 0
    PIX 3
    PIX 6
    PIX 9
    jmp 3b
    .balign 4,0xcb
COLTAB:                      # by the value of setting 458: three bytes of a pixel
%(table)s
    nop                      # the op must not end in 0xFF bytes: the free-space ledger counts only changed bytes
"""


def run(*a):
    return subprocess.run(a, check=True, capture_output=True, text=True).stdout


class Blob:
    """One language of block 1: a pool of UTF-16LE strings and 1970 pointers (see film_names_spec.py)."""
    LOAD, RUNTIME, N = 0x43C40000, 0xBFF3D000, 1970

    def __init__(self, data, entry):
        address, size = struct.unpack_from("<2I", data, 16 * entry)
        start = address - self.LOAD
        for head in range(start - 0x200, start + 0x200, 2):
            first, end = struct.unpack_from("<2I", data, head)
            if self.RUNTIME < first < end < self.RUNTIME + 0x80000 and end - first == 4 * self.N:
                if struct.unpack_from("<I", data, head + first - self.RUNTIME)[0] == self.RUNTIME + 8:
                    break
        else:
            raise SystemExit("language %d: no text blob" % entry)
        self.data, self.head, self.array = data, head, head + first - self.RUNTIME
        self.pointers = list(struct.unpack_from("<%dI" % self.N, data, self.array))
        foot = data[self.array + 4 * self.N:start + size].decode("utf-16-le", "replace")
        self.code = foot.split("OlympusLanguage_")[1][:3] if "OlympusLanguage_" in foot else "?"

    def text(self, i):
        s = e = self.head + self.pointers[i] - self.RUNTIME
        while self.data[e:e + 2] != b"\0\0":
            e += 2
        return self.data[s:e].decode("utf-16-le")


def main():
    out, pinned, work = sys.argv[1:4]
    listing = sys.argv[4] if len(sys.argv) > 4 else None
    os.makedirs(work, exist_ok=True)
    blk = open(os.path.join(pinned, "block0_0100.bin"), "rb").read()
    b1 = open(os.path.join(pinned, "block1_0101.bin"), "rb").read()
    get = lambda a, n: blk[a - BASE:a - BASE + n]
    ops = []

    def op(addr, new, note, block=0):
        src, off = (blk, addr - BASE) if block == 0 else (b1, addr)
        expect = src[off:off + len(new)]
        assert expect != new, note
        o = {"type": "bytes", "block": block, "offset": "0x%X" % off, "expect": expect.hex(), "new": new.hex()}
        if block == 0:
            o["_addr"] = "0x%08X" % addr
        o["_note"] = note
        ops.append(o)

    # (a) mode controller value list
    assert struct.unpack("<IIIHHBBH", get(MCON_REC, 20)) == (0x00800000 | SETTING, MCON_OLD, 0, 3, 1, 0, 1, 0)
    assert get(MCON_OLD, 13) == bytes([1, 2, 3]) + bytes(range(1, 11))
    op(MCON_REC + 4, struct.pack("<B", MCON_NEW & 0xFF), "mode controller, value list of setting 458: 0x7E849F25 "
       "(1, 2, 3) -> 0x7E849F28 (the stock list 1..10)")
    op(MCON_REC + 12, struct.pack("<B", 5), "mode controller, setting 458: 3 values -> 5 values (1, 2, 3, 4, 5)")
    # (b) lists of panel 607
    d = struct.unpack("<HHIII", get(DESC, 16))
    assert d == (SETTING, 3, 0, 1, OLD_ROWS), d
    old = get(OLD_ROWS, 84)
    assert struct.unpack("<BBH4I", old[:20]) == (0, 2, T_OFF, 0, 0, 2000, V_OFF)
    item = lambda text, value: struct.pack("<BBH4I", 0, 2, text, 0, 0, 2000, value) + old[20:28]
    order = ((T_OFF, V_OFF), (T_WHITE, V_WHITE), (T_RED, V_RED), (T_YELLOW, V_YELLOW), (T_BLUE, V_BLUE))
    op(ROWS, b"".join(item(t, v) for t, v in order), "list items of panel 607: Off (value 1), White (3), Red (2), "
       "Yellow (4), Blue (5); 28 B each")
    op(DESC + 2, struct.pack("<B", 5), "list descriptor of panel 607: 3 items -> 5 items")
    op(DESC + 13, struct.pack("<B", (ROWS >> 8) & 0xFF), "list descriptor of panel 607: items 0x%08X -> 0x%08X" % (OLD_ROWS, ROWS))
    assert get(FORMATS + 4 * PANEL, 4) == struct.pack("<I", OLD_NAMES)
    name = lambda value, text: struct.pack("<iIH14x", value, 2, text)
    op(NAMES, b"".join(name(v, t) for t, v in order) + struct.pack("<i20x", -15),
       "value -> text list of the row: 1 Off, 3 White, 2 Red, 4 Yellow, 5 Blue, end mark -15 (24 B each)")
    op(FORMATS + 4 * PANEL, struct.pack("<H", NAMES & 0xFFFF), "value -> text list 607: 0x%08X -> 0x%08X" % (OLD_NAMES, NAMES))
    # (c) code
    table = "\n".join("    .byte %s" % ", ".join("%d" % x for x in (COLOURS.get(v, (0, 0, 0)) + (0,))) for v in range(6))
    asm = ASM % {"thr": THRESHOLD, "mask": -(0x100000000 - 0x01010101 * (256 - THRESHOLD)), "red": V_RED,
                 "yellow": V_YELLOW, "blue": V_BLUE, "table": table}
    assert THRESHOLD in (64, 128)
    args = ["--defsym=s_%s=0x%s" % (a, a) for a in sorted(set(re.findall(r"s_([0-9a-f]{8})", asm)))]
    s, o, e, sb = (os.path.join(work, "colours." + x) for x in ("s", "o", "elf", "bin"))
    open(s, "w").write(asm)
    run(BIN + "/mn10300-elf-as", "-o", o, s)
    run(BIN + "/mn10300-elf-ld", *args, "--section-start=.k3=%#x" % CODE, "-e", "%#x" % CODE, "-o", e, o)
    run(BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", ".k3", e, sb)
    code = open(sb, "rb").read()
    sym = {l.split()[2]: int(l.split()[0], 16) for l in run(BIN + "/mn10300-elf-nm", e).splitlines() if len(l.split()) == 3}
    assert sym["T_K3"] == CODE and get(CODE, len(code)) == b"\xff" * len(code) and sym["COLTAB"] % 4 == 0
    assert get(T_K2, 6) == bytes.fromhex(T_K2_OLD)
    op(CODE, code, "new code, kernel range, 0xFF run after T_K2: T_K3, T_COL, colour table (%d B)" % len(code))
    op(T_K2, b"\xdc" + struct.pack("<i", sym["T_K3"] - T_K2) + b"\xcb", "T_K2: `movbu (C),d0` -> `jmp T_K3` + nop")
    # (d) texts
    langs = []
    for entry in range(1, 35):
        b = Blob(b1, entry)
        row = []
        for tid in (T_RED, T_YELLOW, T_BLUE):
            src = b.text(SOURCE[tid])
            m = re.match(r"^[A-Za-z]{1,2}:\s*", src)
            assert m and len(src) > m.end(), (b.code, src)
            new = b.pointers[SOURCE[tid]] + 2 * m.end()
            op(b.array + 4 * tid, struct.pack("<I", new), "%s text %d: pointer to %r -> to %r inside text %d %r" % (
                b.code, tid, b.text(tid), src[m.end():], SOURCE[tid], src), block=1)
            row.append(src[m.end():])
        langs.append("%s %s" % (b.code, " / ".join(row)))
    w, n = HELP_OLD.encode("utf-16-le"), HELP_NEW.encode("utf-16-le")
    assert b1[HELP_OFF:HELP_OFF + len(w) + 2] == w + b"\0\0" and len(n) <= len(w)
    lo = min(i for i in range(len(n)) if n[i] != w[i]) & ~1
    hi = (max(i for i in range(len(w)) if (n + bytes(len(w)))[i] != w[i]) | 1) + 1
    op(HELP_OFF + lo, (n + bytes(len(w) - len(n)))[lo:hi], "English text %d: %r -> %r" % (T_HELP, HELP_OLD, HELP_NEW), block=1)
    spec = {
        "name": "peaking-colours",
        "description": "Focus peaking in colour: the list of Custom Menu A > Peaking becomes Off / White / Red / Yellow / "
                       "Blue (setting 458: 1 Off, 3 White, 2 Red, 4 Yellow, 5 Blue; 3 stays the value after a full "
                       "reset; Black is gone, a camera that was set to Black shows Red). White is the pinned build's "
                       "pass. For a colour, new code in Key Line pass 9 writes the colour over the pixels of the "
                       "picture where the line image is 64 or more, and the combine job gets usGain2 = 0. The colour "
                       "names are the stock texts of the B&W filter list in all 34 languages. A delta on "
                       "data/builds/peaking-menu-names.json: every expect is a byte string of that build. See "
                       "experiments/2026-11-14-focus-peaking/NOTES.md section 16.",
        "base": STOCK,
        "base_sha256": hashlib.sha256(open(os.path.join(ROOT, STOCK), "rb").read()).hexdigest(),
        "status": "candidate: emulator-checked, not flashed",
        "_delta_on": "data/builds/peaking-menu-names.json (sha256 %s)" % PINNED_SHA,
        "_ram": "no new RAM; the new code uses 24 bytes of the ART task's stack",
        "ops": ops,
    }
    json.dump(spec, open(out, "w"), indent=1)
    print("wrote", out, len(ops), "ops;", "code %d B at 0x%X-0x%X" % (len(code), CODE, CODE + len(code)))
    print("  colour names:", "; ".join(langs))
    if listing:
        txt = run(BIN + "/mn10300-elf-objdump", "-d", "-j", ".k3", e)
        open(listing, "w").write(re.sub(r"/[^\s:]*colours\.elf", "colours.elf", txt))


main()
