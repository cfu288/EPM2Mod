"""Write patches/peaking-menu.json: the menu row "Peaking" (Off / White / Black) for the focus-peaking build.

Research code. NOTES.md section 15. The spec is a delta on the pinned build builds/peaking-gain-2x.json: every
`expect` is a byte string of that build, not of the stock file.

What it writes:
  (a) Custom Menu item table: an 80-row copy at ITEMS (the pinned 79-row table 0x7EBF3000 of level-adjust-row with the
      row {group 0, text 1505, setting 458, order 7, help 1506, value list 607, 0} at index 7, after "MF Assist"),
      and the 10 address loads of the page code point to it;
  (b) child list: an 80-entry copy at KIDS with (panel 607, setting 458) at index 7; the 11 page records point to it;
  (c) row constants: last index 78 -> 79 (5 sites), count 79 -> 80 (3 sites), row-state array 158 -> 160 bytes;
  (d) rows in group 0 (A) in the .data image: 10 -> 11;
  (e) list descriptor of panel 607 (an Off/On list of the dormant setting 446, in no menu): setting 458, 3 items,
      items at ROWS = Off (value 1), White (3), Black (2); and the value -> text list number 607 for the row
      (table 0x7F014614, a null pointer in stock) at NAMES;
  (f) code: T_A asks T_R in place of reading R. T_R: R and setting 458 (prm tag 0x8971) is not 1 (Off); it keeps the value
      in the new RAM byte C. T_K takes the gain from T_K2: C = 2 -> the stock Key Line gain 0xFF00 (black lines,
      the E-P5 value), else 512 (white lines, as pinned);
  (g) English texts (block 1): 1505 "Peaking", 1506 its help, 1500 "White", 1501 "Black".

Usage: mkspec_menu.py OUT.json PINNED_DIR WORKDIR [LISTING.txt]
  PINNED_DIR  `python3 tools/oetool.py unpack build/peaking-gain-2x.BIN PINNED_DIR`
  WORKDIR     scratch folder for the assembler files (outside the repository)
"""
import hashlib, json, os, re, struct, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BASE = 0x7E421020
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
PINNED_SHA = "ce1037cda6c9ff87e600272383dfe97b649a5ef24d6928e319b581191b4ca2c8"
BIN = os.path.join(os.path.abspath(__file__).split("/experiments/")[0], "build", "toolchain", "bin")

OLD_ITEMS, OLD_KIDS, N = 0x7EBF3000, 0x7EBF3500, 79   # tables of level-adjust-row
ITEMS, KIDS, ROWS = 0x7EBF2000, 0x7EBF2600, 0x7EBF2900  # new item table (1,282 B), child list (648 B), list items (84 B)
NAMES = 0x7EBF2960                                     # value -> text list for the row (96 B)
FORMATS = 0x7F014614                                   # table of 660 value -> text lists, by "value list" number
AT = 7                                                 # index of the new row: after "MF Assist" (6)
SETTING, TAG = 458, 0x8971                             # dormant setting "Built-in EVF Style": values 1, 2, 3
PANEL = 607                                            # dormant generic list panel (Off/On of setting 446)
T_LABEL, T_HELP, T_WHITE, T_BLACK, T_OFF = 1505, 1506, 1500, 1501, 1371
V_WHITE, V_BLACK, V_OFF = 3, 2, 1                      # 3 is the value after a full reset (mcon default table 0x7E84C82C)
ROW = struct.pack("<HHIHHHH", 0, T_LABEL, SETTING, 7, T_HELP, PANEL, 0)
KID = struct.pack("<II", PANEL, SETTING)
PAGES = 0x7EFFA44C
SIZE_A = 0x7E8DA000 + (0x602BE390 - 0x602A9B40)        # .data image: rows in group 0 (RAM 0x602BE390)
DESC = 0x7F00BFBC                                      # list descriptor of panel 607 (list table 0x7F00D710)
ITEM_LOADS = (0x7EDE9B9D, 0x7EDE9CDD, 0x7EDE9D85, 0x7EDE9F19, 0x7EDEA02A, 0x7EDEA035, 0x7EDEA2F2, 0x7EDEA392,
              0x7EDEA3A1, 0x7EDEA3F5)
CONSTS = (
    (0x7EDE9AE5, "2d9e00", "2da000", "constructor: clear the row-state array, 158 -> 160 bytes"),
    (0x7EDE9B85, "a54e", "a54f", "open: cmp last index 78 -> 79"),
    (0x7EDE9B92, "aa4f", "aa50", "open: cmp row count 79 -> 80"),
    (0x7EDE9CBA, "854e", "854f", "UP: wrap to last index 78 -> 79"),
    (0x7EDE9D10, "804e", "804f", "UP, skip a greyed row: wrap to last index 78 -> 79"),
    (0x7EDE9D26, "aa4f", "aa50", "UP: cmp row count 79 -> 80"),
    (0x7EDE9D6B, "a04e", "a04f", "DOWN: cmp last index 78 -> 79"),
    (0x7EDE9DBF, "a54e", "a54f", "DOWN, skip a greyed row: cmp last index 78 -> 79"),
    (0x7EDE9DCC, "aa4f", "aa50", "DOWN: cmp row count 79 -> 80"),
)
# English texts: (text id, block-1 offset, old string, new string). The new string must not be longer.
TEXTS = (
    (T_LABEL, 0x38872C, "EVF Auto Switch", "Peaking"),
    (T_HELP, 0x38874C, "Switch automatically from\r\nmonitor display to EVF display\r\nwhen an eye is detected at EVF.",
     "Show white or black lines\r\non sharp edges while\r\nMF Assist magnifies."),
    (T_WHITE, 0x38862A, "Style 1", "White"),
    (T_BLACK, 0x38863A, "Style 2", "Black"),
)

T_A_SITE, T_A_OLD = 0x7E4C9226, "fca8c5e82b60"      # T_A: movbu (R),d0
T_K_SITE, T_K_OLD = 0x7E4C9394, "2c0002"            # T_K: mov 512,d0
CODE = 0x7E4C93A4                                   # first free byte after T_K in the kernel-range 0xFF run
ASM = """
.equ RFLAG, 0x602be8c5       # R: the MF Assist state object is On (peaking-direct-4)
.equ CFLAG, 0x602be8c7       # new byte C: the value of setting 458 when T_R last read it (same unused slot as L, R, L2)
.equ LV,    0x605b1cd0       # live-view parameter struct
.section .k2,"ax"
T_R:                         # called from T_A with `call T_R,[],4` in place of `movbu (R),d0`. d0 = 1: show the lines.
                             # Not a leaf: it returns with ret (from the stack), not retf (from MDR)
    movbu (RFLAG),d0
    cmp 0,d0
    beq 2f
    mov %d,d0                # prm tag of setting 458. The struct refresh 0x7E6ECCAF reads its tags the same way
    mov 0,a0
    clr d1
    call s_7e457c75,[d2,d3],12
    movbu d0,(CFLAG)
    mov LV,a1                # a1 and d1 as they were at the call site
    clr d1
    cmp %d,d0                # Off
    beq 1f
    mov 1,d0
    ret [],4
1:  clr d0
2:  ret [],4

T_K2:                        # jumped to from T_K in place of `mov 512,d0`
    movbu (CFLAG),d0
    cmp %d,d0                # Black: the stock Key Line gain 0xFF00 (E-P5 black: -2048 after the shift by 3)
    bne 1f
    jmp s_7e4c9399
1:  mov 512,d0               # White, as pinned (peaking-gain-2x)
    jmp s_7e4c939f
    nop                      # the op must not end in 0xFF bytes: the free-space ledger counts only changed bytes
""" % (TAG, V_OFF, V_BLACK)


def run(*a):
    return subprocess.run(a, check=True, capture_output=True, text=True).stdout


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

    # (a) item table
    old = get(OLD_ITEMS, N * 16 + 2)
    assert struct.unpack_from("<H", old, N * 16)[0] == 98
    assert struct.unpack_from("<HHI", old, (AT - 1) * 16) == (0, 172, 285)     # MF Assist
    assert struct.unpack_from("<HHI", old, AT * 16) == (0, 47, 238)
    items = old[:AT * 16] + ROW + old[AT * 16:]
    op(ITEMS, items, "new Custom Menu item table, 80 rows + the end group 98: the 79-row table 0x7EBF3000 with the row "
       "{group 0, text 1505 'Peaking', setting 458, order 7, help 1506, value list 607, 0} at index 7, after MF Assist")
    # (b) child list
    oldk = get(OLD_KIDS, N * 8 + 8)
    assert oldk[-8:] == bytes(8) and struct.unpack_from("<II", oldk, (AT - 1) * 8) == (107, 285)
    kids = oldk[:AT * 8] + KID + oldk[AT * 8:]
    op(KIDS, kids, "new Custom Menu child list, 80 entries + zero entry: the list 0x7EBF3500 with (panel 607, "
       "setting 458) at index 7")
    for a in ITEM_LOADS:
        assert get(a, 4) == struct.pack("<I", OLD_ITEMS)
        op(a - 2, get(a - 2, 2) + struct.pack("<I", ITEMS), "item-table address 0x7EBF3000 -> 0x%08X" % ITEMS)
    for page in range(24, 35):
        a = PAGES + 40 * page + 20
        assert get(a, 4) == struct.pack("<I", OLD_KIDS)
        op(a, struct.pack("<I", KIDS), "page record %d: child list 0x7EBF3500 -> 0x%08X" % (page, KIDS))
    assert blk.count(struct.pack("<I", OLD_KIDS)) == 11 and blk.count(struct.pack("<I", OLD_ITEMS)) == len(ITEM_LOADS)
    # (c) row constants
    for a, was, new, note in CONSTS:
        assert get(a, len(was) // 2) == bytes.fromhex(was), "%08X" % a
        op(a, bytes.fromhex(new), note)
    # (d) group size
    assert get(SIZE_A, 20) == struct.pack("<10H", 10, 4, 6, 17, 13, 3, 8, 7, 5, 6)
    op(SIZE_A, struct.pack("<H", 11), ".data image (RAM 0x602BE390): rows in group 0 (A), 10 -> 11")
    # (e) list of panel 607
    d = struct.unpack("<HHIII", get(DESC, 16))
    assert d[:4] == (446, 2, 0, 1), d
    it = get(d[4], 56)
    off, on = it[:28], it[28:]
    assert struct.unpack("<BBH6I", off) == (0, 2, T_OFF, 0, 0, 2000, 0, 192, 197)
    assert struct.unpack_from("<BBH", on) == (0, 2, 198)

    def item(text, value):   # {u8 0, u8 kind 2 = one label, u16 text, 0, 0, 2000, value, footer texts 192, 197}
        return struct.pack("<BBH4I", 0, 2, text, 0, 0, 2000, value) + off[20:]

    op(ROWS, item(T_OFF, V_OFF) + item(T_WHITE, V_WHITE) + item(T_BLACK, V_BLACK),
       "list items of panel 607: Off (value 1), White (3), Black (2); 28 B each, the layout of the stock Off/On items")
    op(DESC, struct.pack("<HHIII", SETTING, 3, 0, 1, ROWS), "list descriptor of panel 607: setting 446, 2 items at "
       "0x%08X -> setting 458, 3 items at 0x%08X" % (d[4], ROWS))
    # the row shows its value through the value -> text list number 607 (the row's field +12). The stock table has
    # no list there (a null pointer: the row builder 0x7EE01E1E would read address 0)
    assert get(FORMATS + 4 * PANEL, 4) == bytes(4) and get(FORMATS + 4 * 107, 4) == struct.pack("<I", 0x7F012724)
    assert get(0x7F012724, 72) == struct.pack("<iI16x", 0, 2)[:8] + struct.pack("<H14x", T_OFF) + \
        struct.pack("<iIH14x", 1, 2, 198) + struct.pack("<i20x", -15)
    name = lambda value, text: struct.pack("<iIH14x", value, 2, text)   # {value, kind 2 = one label, text}, 24 B
    op(NAMES, name(V_OFF, T_OFF) + name(V_WHITE, T_WHITE) + name(V_BLACK, T_BLACK) + struct.pack("<i20x", -15),
       "value -> text list of the row: 1 Off, 3 White, 2 Black, end mark -15 (24 B each, the layout of the stock "
       "Off/On list 0x7F012724)")
    op(FORMATS + 4 * PANEL, struct.pack("<I", NAMES), "value -> text list 607: null -> 0x%08X" % NAMES)
    # (f) code
    asm = ASM
    args = []
    for a in sorted(set(re.findall(r"s_([0-9a-f]{8})", asm))):
        args.append("--defsym=s_%s=0x%s" % (a, a))
    s, o, e, sb = (os.path.join(work, "menu." + x) for x in ("s", "o", "elf", "bin"))
    open(s, "w").write(asm)
    run(BIN + "/mn10300-elf-as", "-o", o, s)
    run(BIN + "/mn10300-elf-ld", *args, "--section-start=.k2=%#x" % CODE, "-e", "%#x" % CODE, "-o", e, o)
    run(BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", ".k2", e, sb)
    code = open(sb, "rb").read()
    sym = {l.split()[2]: int(l.split()[0], 16) for l in run(BIN + "/mn10300-elf-nm", e).splitlines() if len(l.split()) == 3}
    assert sym["T_R"] == CODE and get(CODE, len(code)) == b"\xff" * len(code)
    assert get(T_A_SITE, 6) == bytes.fromhex(T_A_OLD) and get(T_K_SITE, 3) == bytes.fromhex(T_K_OLD)
    op(CODE, code, "new code, kernel range, 0xFF run after T_K: T_R, T_K2 (%d B)" % len(code))
    d16 = sym["T_R"] - T_A_SITE
    assert 0 < d16 < 0x8000
    op(T_A_SITE, b"\xcd" + struct.pack("<H", d16) + b"\x00\x04\xcb", "T_A: `movbu (R),d0` -> `call T_R,[],4` + nop")
    d16 = sym["T_K2"] - T_K_SITE
    assert 0 < d16 < 0x8000
    op(T_K_SITE, b"\xcc" + struct.pack("<H", d16), "T_K: `mov 512,d0` -> `jmp T_K2`")
    # (g) texts
    for tid, off1, was, new in TEXTS:
        w, n = was.encode("utf-16-le"), new.encode("utf-16-le")
        assert b1[off1:off1 + len(w) + 2] == w + b"\0\0" and b1[off1 - 2:off1] == b"\0\0", tid
        assert len(n) <= len(w) and b1.count(w + b"\0\0") >= 1
        op(off1, n + bytes(len(w) - len(n)), "English text %d: %r -> %r" % (tid, was, new), block=1)
    spec = {
        "name": "peaking-menu",
        "description": "Focus peaking gets a setting: Custom Menu A, row 'Peaking' after MF Assist, with Off / White / "
                       "Black. Off: MF Assist magnifies as on the build without peaking. White: as the pinned build "
                       "(gain 512). Black: Key Line's own gain 0xFF00, the E-P5 value for black lines. The value is the "
                       "dormant setting 458 (prm tag 0x8971, MODE bank; 1 Off, 2 Black, 3 White; 3 is its value after a full "
                       "reset, and every value but 1 and 2 gives White); its list "
                       "is the dormant panel 607. A delta on builds/peaking-gain-2x.json: every expect is a byte "
                       "string of that build. See experiments/2026-11-14-focus-peaking/NOTES.md section 15.",
        "base": STOCK,
        "base_sha256": hashlib.sha256(open(os.path.join(ROOT, STOCK), "rb").read()).hexdigest(),
        "status": "candidate: emulator-checked, not flashed",
        "_delta_on": "builds/peaking-gain-2x.json (sha256 %s)" % PINNED_SHA,
        "_ram": "one new byte 0x602BE8C7 (C), the fourth byte of the unused slot 20 of table 0x602BE874 that holds L, "
                "R, L2; the row-state array of the Custom Menu page grows by 2 bytes into 0x606A31B6-B7",
        "ops": ops,
    }
    json.dump(spec, open(out, "w"), indent=1)
    print("wrote", out, len(ops), "ops;", "code %d B at 0x%X-0x%X" % (len(code), CODE, CODE + len(code)))
    for o_ in ops:
        if o_["block"] == 1:
            print("  block 1 offset %s, %d B: %s" % (o_["offset"], len(o_["new"]) // 2, o_["_note"]))
    if listing:
        txt = run(BIN + "/mn10300-elf-objdump", "-d", "-j", ".k2", e)
        open(listing, "w").write(re.sub(r"/[^\s:]*menu\.elf", "menu.elf", txt))


main()
