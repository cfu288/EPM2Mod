"""Write the patch spec osd-battery: the battery charge as a percentage on the live-view information screen.

Research code. The spec is a delta on the pinned build builds/films-12d.json: every `expect` is a byte string of
that build (all sites hold stock bytes, or bytes of the listed free area).

What the spec does (NOTES.md in this folder has the evidence):
  1. A new text label (widget class 0x8010) on the live-view panel (class 0x600A). The panel builder makes one
     widget per word of a pointer table and starts at index 1; index 0 of the table is a zero word. The spec
     points index 0 at a new 92-byte resource record and lets the builder start at 0.
  2. One routine, called at the end of the panel's two refresh functions in place of their last call. It reads
     the battery voltage with the stock routine (at most once in 2 s), makes a percentage and sets the label text.

Usage: mkspec_osd_battery.py BLOCK0 WORKDIR OUT.json [LISTING.txt]
  BLOCK0   block 0 of the pinned build (emulator/patchblock.py SPECS -o BLOCK0, or build/emu/NAME-SHA8/block0_0100.bin)
  WORKDIR  scratch folder for the assembler files (outside the repository)
"""
import json, os, re, struct, subprocess, sys

BASE = 0x7E421020
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
STOCK_SHA = "34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300"
PINNED = "builds/films-12d.json"
PINNED_SHA = "2cdd18e7004821b2e443ec4f08db06ab9a0d4f0f700ab53db8c4bbc1dad93e32"
BIN = os.path.join(os.path.abspath(__file__).split("/experiments/")[0], "build", "toolchain", "bin")

CODE = (0x7EBF1F4F, 0x7EBF2000)      # free run of the segment-2 area 0x7EBF1090-0x7EBF3BAD (tools/freespace.py area)
BATT = (0x7EBF2F6C, 0x7EBF3000)      # free run of the same area
DATA = (0x7EBF256C, 0x7EBF2600)      # free run of the same area (even start)

# Model: percentage = (count - EMPTY) * 5 / 8, 0..100. One count is about 9.77 mV of pack voltage (fenykl's
# E-PL3 calibration; the E-PM2 has the same AC threshold 783, so the same divider is inferred).
EMPTY = 680                          # 6.64 V
LABEL_RECT = (8, 8, 76, 32)          # x, y, w, h on the 720 x 480 screen

ASM = r"""
.equ T_LAST, 0x602be8c8      # u32: time of the last battery read, microseconds (free slot 21 of the table 0x602BE874)
.equ RAW,    0x602be8cc      # u16: last battery A/D count, 0 = none yet (free slot 22)
.equ SEMID,  0x7e43ea96      # s16 word: the id (5) of the battery-check semaphore
.equ CHECK,  0x60503a3e      # u8 of the battery module: 1 while its 1 s check runs

.section .c,"ax"
T_INIT:                          # end of the panel's first refresh 0x7ED60A95: the panel is in d2
    mov d2,a2
T_UPD:                           # end of the panel's data-update refresh 0x7ED60F27: the panel is in a2
    add -36,sp                   # locals: (4) format, (8) value, (12) '%%', (16..31) text, (32) result of the replaced call
    call 0x7ecede74,[],8         # the replaced call
    mov d0,(32,sp)
    mov (792,a2),a3              # child slot 0: the new label
    cmp 0,a3
    beq 9f
    mov (1076,a2),a0             # child 71, the shutter speed: the label is visible when it is
    mov (a0),a1
    mov (80,a1),a1
    calls (a1)                   # isVisible
    mov d0,d3
    exth d3
    cmp 0,d3
    beq 8f
    movhu (RAW),d0               # before the first read: nothing in the first 3 s after power-on,
    cmp 0,d0                     # so that the start-up does the same work as before
    bne 7f
    call 0x7e4262cd,[],0         # now, microseconds (30 bits)
    cmp 3000000,d0
    bcc 7f
    clr d3
    bra 8f
7:  call T_BATT,[],4             # d0 = percentage
    mov d0,(8,sp)
    mov '%%',d0
    mov d0,(12,sp)
    mov FMT,d0
    mov d0,(4,sp)
    mov sp,a0
    add 16,a0
    call 0x7ed37429,[d2,d3,a2,a3],116    # the GUI's wide-character sprintf(a0 = text, (4,sp) = format, ...)
    mov sp,a1
    add 16,a1
    mov a3,a0
    call 0x7ed2d510,[d2,d3,a2,a3],24     # setText(label, text): copies the text, redraws when it differs
8:  mov a3,a0
    mov d3,d0
    call 0x7edc1851,[d2,d3,a2],16        # setVisible(label, d0)
9:  mov (32,sp),d0
    ret [],44

.section .b,"ax"
T_BATT:                          # battery charge in percent, 0..100; reads the voltage at most once in 2 s
    call 0x7e4262cd,[],0         # now, microseconds (30 bits)
    mov d0,d2
    movhu (RAW),d1
    cmp 0,d1
    beq 1f
    mov (T_LAST),d1
    sub d1,d0
    and 0x3fffffff,d0
    cmp 2000000,d0
    bcs 2f                       # one read in 2 s
1:  mov d2,(T_LAST)
    movhu (SEMID),d0
    exth d0
    mov 20,d1
    call 0x7e449409,[d2,d3,a2],16    # wait up to 20 ms for the semaphore: the A/D buffer and its event are shared
    cmp 0,d0
    bne 2f                       # busy: keep the last count
    movbu (CHECK),d0             # the A/D read waits for its event without a time limit:
    cmp 0,d0                     # read only while the stock 1 s check is on (it is off in standby)
    beq 5f
    mov 4,d0
    call 0x7e539e6a,[],4         # battery voltage, mean of 4 samples, 10 bits
    movhu d0,(RAW)
5:  movhu (SEMID),d0
    exth d0
    call 0x7e4494a1,[d2,d3],12   # signal
2:  movhu (RAW),d0
    add -%(empty)d,d0
    bge 3f
    clr d0
3:  mov d0,d1
    asl2 d1
    add d1,d0
    lsr 3,d0                     # * 5 / 8
    cmp 100,d0
    ble 4f
    mov 100,d0
4:  ret [],4

.section .d,"a"
RES:                             # resource record of the label, 92 bytes: the stock label id 201 of this panel
    .short 0x8010, 211           # (0x7EF674D0) with a new id, rectangle pointer and alignment
    .long RECT
    .short 9, 0
    .long ZERO8
    .long 2                      # layer 2, as the other information items
    .long 0, 0x16, 0x0f, 0x0f    # no text id, text style 22, 15, 15
    .long 0x%(align)x            # alignment: 0x100 left, 0x101 centre, 0x102 right
    .long 0, 0, 1, 0xffff, 7, 1, 0, 0, 0, 100, 1, 0, 0
RECT:                            # two rectangles, as every stock record has (the second one is used on this screen)
    .short %(x)d, %(y)d, %(w)d, %(h)d
    .short %(x)d, %(y)d, %(w)d, %(h)d
ZERO8:
    .long 0, 0
FMT:
    .short '%%', 'd', '%%', 'c', 0   # the formatter has no "%%%%"
"""

SITES = [  # (address, stock bytes, assembler text of the replacement, note)
    (0x7ED60F1D, "dd57cff8ff0008", "call T_INIT,[],8",
     "live-view panel (class 0x600A), end of the first refresh 0x7ED60A95: `call 0x7ecede74,[],8` -> `call T_INIT,[],8`"),
    (0x7ED61377, "ddfdcaf8ff0008", "call T_UPD,[],8",
     "live-view panel, end of the data-update refresh 0x7ED60F27: `call 0x7ecede74,[],8` -> `call T_UPD,[],8`"),
]
DATA_OPS = [  # (address, stock bytes, new bytes or None = address of RES, note)
    (0x7ED60A45, "8f01", "8f00", "panel builder 0x7ED60A3E: `mov 1,d3` -> `mov 0,d3`: the child loop starts at index 0"),
    (0x7ED60A4F, "8a04", "8a00", "panel builder: `mov 4,d2` -> `mov 0,d2`: table offset of index 0"),
    (0x7E8E8ED4, "00000000", None, "initial value of the RAM word 0x602B8A14, index 0 of the panel's table of widget "
     "resources (a zero word, never read: the stock loop starts at index 1) -> the new record RES"),
]


def run(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode:
        sys.exit("%s failed:\n%s%s" % (a[0], r.stdout, r.stderr))
    return r.stdout


def main(argv):
    if len(argv) not in (3, 4):
        sys.exit(__doc__)
    block0, work, out = argv[:3]
    os.makedirs(work, exist_ok=True)
    img = open(block0, "rb").read()
    x, y, w, h = LABEL_RECT
    asm = ASM % dict(empty=EMPTY, x=x, y=y, w=w, h=h, align=0x0102)
    for addr, _, text, _ in SITES:
        asm += '\n.section .s%x,"ax"\n    %s\n' % (addr, text)
    # an absolute call target becomes a symbol, so that the linker makes the pc-relative displacement
    targets = sorted(set(re.findall(r"call\s+0x([0-9a-f]{8})", asm)))
    asm = re.sub(r"(call\s+)0x([0-9a-f]{8})", r"\1s_\2", asm)
    s, o, e = (os.path.join(work, "osd." + k) for k in "soe")
    open(s, "w").write(asm)
    run(BIN + "/mn10300-elf-as", "-o", o, s)
    args = ["--section-start=.c=%#x" % CODE[0], "--section-start=.b=%#x" % BATT[0], "--section-start=.d=%#x" % DATA[0]]
    args += ["--section-start=.s%x=%#x" % (a, a) for a, _, _, _ in SITES]
    args += ["--defsym=s_%s=0x%s" % (t, t) for t in targets]
    run(BIN + "/mn10300-elf-ld", *args, "-e", "%#x" % CODE[0], "-o", e, o)

    def sect(name):
        b = os.path.join(work, "sect.bin")
        run(BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", name, e, b)
        return open(b, "rb").read()

    syms = {}
    for line in run(BIN + "/mn10300-elf-nm", e).splitlines():
        a, _, n = line.split()
        syms[n] = int(a, 16)
    ops = []

    def op(addr, new, note, expect=None):
        off = addr - BASE
        old = img[off:off + len(new)]
        if expect is not None and old != expect:
            sys.exit("%#x: the base has %s, expected %s" % (addr, old.hex(), expect.hex()))
        ops.append({"type": "bytes", "block": 0, "offset": "0x%X" % off, "expect": old.hex(), "new": new.hex(),
                    "_addr": "0x%08X" % addr, "_note": note})

    code, batt, data = sect(".c"), sect(".b"), sect(".d")
    for (lo, hi), b, name in ((CODE, code, "code"), (BATT, batt, "battery code"), (DATA, data, "data")):
        if lo + len(b) > hi:
            sys.exit("%s: %d bytes, the area has %d" % (name, len(b), hi - lo))
        free = img[lo - BASE:lo - BASE + len(b)]
        if set(free) - {0x00, 0xFF} and len(set(free)) > 1:
            print("note: %s area is not blank in the base: %s..." % (name, free[:16].hex()))
    op(CODE[0], code, "new code in the segment-2 area: T_INIT, T_UPD (%d B)" % len(code))
    op(BATT[0], batt, "new code in the segment-2 area: T_BATT (%d B)" % len(batt))
    op(DATA[0], data, "new data in the segment-2 area: label resource record RES (92 B), its two rectangles, 8 zero bytes, "
       "the format L\"%%d%%c\" (%d B)" % len(data))
    for addr, stock, _, note in SITES:
        op(addr, sect(".s%x" % addr), note, bytes.fromhex(stock))
    for addr, stock, new, note in DATA_OPS:
        op(addr, bytes.fromhex(new) if new else struct.pack("<I", syms["RES"]), note, bytes.fromhex(stock))
    spec = {
        "name": "osd-battery",
        "description": "Battery charge as a percentage on the live-view information screen (top left). A new text "
                       "label on the live-view panel, made by the panel's own builder from a new resource record, "
                       "and one routine at the end of the panel's two refresh functions: it reads the battery "
                       "voltage with the stock A/D routine under the stock semaphore, at most once in 2 s, and "
                       "writes (count - %d) * 5 / 8 percent, 0 to 100, into the label. The scale is inferred from "
                       "the E-PL3 and needs one camera check. A delta on %s: every expect is a byte string of that "
                       "build. See experiments/2026-11-17-osd-info/NOTES.md." % (EMPTY, PINNED),
        "base": STOCK,
        "base_sha256": STOCK_SHA,
        "status": "candidate: emulator-checked, not flashed",
        "_delta_on": "%s (sha256 %s)" % (PINNED, PINNED_SHA),
        "_ram": "T_LAST 0x602BE8C8 (u32) and RAW 0x602BE8CC (u16): slots 21 and 22 of the 37-slot table 0x602BE874, "
                "free by the same static argument as slot 20 (focus-peaking NOTES 11.3). Child slot 0 of the "
                "live-view panel object (panel + 792) holds the label",
        "_symbols": {k: "0x%08X" % v for k, v in sorted(syms.items()) if k in ("T_INIT", "T_UPD", "T_BATT", "RES", "RECT", "FMT")},
        "ops": ops,
    }
    json.dump(spec, open(out, "w"), indent=1)
    open(out, "a").write("\n")
    if len(argv) == 4:
        open(argv[3], "w").write(run(BIN + "/mn10300-elf-objdump", "-d", "-j", ".c", "-j", ".b", e))
    print("wrote", out, len(ops), "ops; code", len(code), "+", len(batt), "B, data", len(data), "B")


if __name__ == "__main__":
    main(sys.argv[1:])
