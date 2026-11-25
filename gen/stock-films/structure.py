"""Write data/specs/stock-films-structure-3.json and build/stock-films/layout.json: what the stock-filters firmware
flashes for film simulations (experiments/2026-11-18-stock-filters/design.md, "One mechanism for all 12 entries").

    uv run python gen/stock-films/structure.py WORKDIR [LISTING.txt]

Versions: 1 the structure; 2 the film codes' look on LKID (the stock identity look table) and the EXIF case "no art
filter" (experiments/2026-11-20-film-name-exif/NOTES.md); 3 no 12-region table for the film codes
(experiments/2026-11-20-model-calibration/NOTES.md §6). This file makes version 3; versions 1 and 2 are committed
spec files, made by this file at earlier commits.

Flashed, and reached only through a film code or a hidden stored value (so no stock filter changes):
  * one film code per menu entry; for each: a tone stub with three records that point at the entry's RAM block,
    saturation, six-axis and chroma stubs that point at it, and three value stubs (art_GetFilterType and the two
    live-view functions) that give the code;
  * the stage-table entries of the eight film codes that no stock entry reaches (75, 92, 125, 94, 98, 144, 156, 159),
    and tone-hash entries for them and for 79 (target: the stock default; the loader switches it);
  * the art-matrix chain at the stock compare 0x7E56C6A5: film codes take their RAM matrix; the in-place codes 71, 72,
    79, 85 take a RAM pointer, 0 = the stock path; every other code goes through the stock compares unchanged;
  * the hidden stored values 111, 112, 114, 115, 118: their routes to the film codes and their hash keys;
  * codes 75 and 125: the four compares of the job block that treat them get an immediate no byte matches;
  * the 12-region stage: a case OFFCASE of the selector's worker 0x7E56E495 returns a descriptor whose table has enable
    mask 0 (a record that is off has no effect, camera-tested with the twelve-region probe's OVERLAP entry); the eight
    codes no stock entry reaches get a 12-region hash entry -> OFFCASE, the four in-place codes an entry with the
    worker's default case, which the loader switches to OFFCASE while the entry has a film.
layout.json lists, per entry, the words the loader switches (address, size, film bytes, stock bytes) and the RAM
layout. Every expect is a byte of the stock firmware (the feature specs do not touch these bytes: checked).
"""

import hashlib
import json
import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "cli", "src"))
from epm2mod.container import parse  # noqa: E402
from epm2mod.looks import slots  # noqa: E402

# The version this generator makes. A camera-tested version stays as its committed spec file (a pinned build names it);
# the generator that made it is in git history.
SPEC = "stock-films-structure-3"
OUT = "stock-films"   # build/OUT/layout.json
LOOK_TAIL = 0x7E56EB0F          # the look stage's tail: a0 = the look table
EXIF_OFF = 0x7E70DF1B           # rec_art_set_exif_data's default case: no ArtFilter written (Off)
BASE = 0x7E421020
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import toolchain  # noqa: E402

BIN = toolchain.binutils_dir()

# Menu entries in menu order: (stock name, stock value, stored value with a film, film code, kind)
# kind: "inplace" = the entry's own stock code (its stage entries are switched), "route" = a code no stock entry
# reaches (value routes switched), "hidden" = a hidden stored value (the stored value is switched).
ENTRIES = [
    ("Pop Art", 100, 100, 79, "inplace"),
    ("Soft Focus", 101, 101, 75, "route"),
    ("Pale&Light Color", 102, 102, 71, "inplace"),
    ("Light Tone", 103, 103, 72, "inplace"),
    ("Grainy Film", 104, 111, 94, "hidden"),
    ("Pin Hole", 105, 105, 92, "route"),
    ("Diorama", 106, 106, 125, "route"),
    ("Cross Process", 107, 107, 85, "inplace"),
    ("Gentle Sepia", 108, 112, 98, "hidden"),
    ("Dramatic Tone", 109, 114, 144, "hidden"),
    ("Key Line", 119, 115, 156, "hidden"),
    ("Watercolor", 120, 118, 159, "hidden"),
]

# RAM: one block per entry (cached addresses; the image library reads them through the cache)
# Tone: 8 tables per channel (record member order: column 0..3 x member 0 / 1), each the film's curve read at the stock
# default table of the same place (as the record slots Light Tone and Cross Process of the film firmware).
FILM_RAM, BLOCK = 0x7E4D1000, 0x3200   # after the loader's status and names (0x7E4D0000-0x7E4D0800); ends 0x7E4F6800
TONE, SAT, SIX_S, SIX_H, CHROMA, MATRIX = 0x0000, 0x3000, 0x3010, 0x301C, 0x3030, 0x30A0
MATPTR = 0x7E4C9FC0              # RAM: u32 matrix pointer per in-place code (the film matrix's address = film,
                                 # anything else = stock), read uncached
INPLACE_PTR = {79: 0, 71: 4, 72: 8, 85: 12}

# Stock code that the structure jumps to
GAMMA_PICK, GAMMA_TAIL = 0x7E56B732, 0x7E56B852
SAT_COMMON, SIX_COMMON, CHROMA_TAIL = 0x7E56DD79, 0x7E56D8D8, 0x7E566810
MATRIX_HOOK, MATRIX_HOOK_BYTES = 0x7E56C6A5, bytes.fromhex("a046c811a04f")
MATRIX_STOCK_70, MATRIX_STOCK_REST, MATRIX_USE = 0x7E56C6B8, 0x7E56C6AD, 0x7E56C764
WB_PAIRS = 0x7E768DB8            # five pairs (u16, u16); code 71 / mode 102 -> pair 0, type II -> pair 2
NEUTRAL_75 = [(0x7E54B532, 0x4B), (0x7E54B536, 0x7D), (0x7E54B5F7, 0x4B), (0x7E54B5FB, 0x7D),   # imm8 bytes
              (0x7E54BF60, 0x4B), (0x7E54BF6B, 0x7D)]

# Free space: code in segment 2, data in segment 3 (code-space-map USABLE areas, free in the stock-filters build)
SHARED_AREA = (0x7ECB0888, 0x7ECB0BA0)     # (0x7ECB0BA0-0x7ECB0EE7 is interval-timelapse-v2's)
# the ART bracket routines: one 26-byte slot each, in free runs of segment 2 that no spec of the build uses
# (osd-battery, a candidate, keeps 0x7EBF1F50-0x7EBF1FF0 and 0x7EBF2560-0x7EBF2600)
BRACKET_RUNS = [(0x7EBF2512, 0x7EBF2560), (0x7EBF27FC, 0x7EBF2890), (0x7EBF28C8, 0x7EBF2900), (0x7EBF3A70, 0x7EBF3B10),
                (0x7EBF3B38, 0x7EBF3BAD), (0x7EBF1090, 0x7EBF10FC), (0x7EBF2DF8, 0x7EBF2E80)]
BRACKET_SLOT = 24     # segment 2: the shared tone part, the chroma helper, the matrix chain, and
                                           # the stubs of the first six entries
CODE_AREA = (0x7EBF38BC, 0x7EBF3B10)       # segment 2: the stubs of the other six (after the log's probes)
DATA_AREA = (0x7EE541B4, 0x7EE548B0)
TWELVE_DATA = (0x7EE40728, 0x7EE40877)     # segment 3, reclaim-space row 8 (version 3: the off descriptor)


# the 12-region stage (experiments/2026-11-20-twelve-region/NOTES.md §3): hash by art code (key = code - 8, 64
# entries {key, case}, linear probing, key 0 = empty) -> a case of the worker that returns a descriptor
# {table, 12 ISO-weight pointers}; the table's enable mask is the u16 at +3024
TWELVE_HASH, TWELVE_HASH_N, TWELVE_KEY_BASE, TWELVE_MASK_AT = 0x7E78C6E4, 64, 8, 3024
TWELVE_DEFAULT_CASE = 0x7E56E5DC   # the worker's default: the table by picture mode (empty slots hold it too)
TWELVE_FLAT_DESC = 0x7E78BA8C   # a stock descriptor whose 12 ISO weights are flat 256: OFFDESC uses its pointers

HUE_SITE, HUE_BYTES = 0x7E546160, bytes.fromhex("a002c80b8501")   # Cross Process: `cmp 2,d0; beq; mov 1,d1`
HUE_APPLY, HUE_SKIP = 0x7E54616D, 0x7E546215


_BLOCK_FILE = {}


def _block_file(blk):
    """A file with the bytes of block 0, for objdump: written once per run from the block in memory."""
    if "path" not in _BLOCK_FILE:
        import tempfile
        f = tempfile.NamedTemporaryFile(suffix=".block0.bin", delete=False)
        f.write(bytes(blk))
        f.close()
        _BLOCK_FILE["path"] = f.name
    return _BLOCK_FILE["path"]


def site_insns(blk, a, n):
    """Whole instructions from a, at least n bytes: [(address, bytes, mnemonic, operands)]."""
    out = subprocess.run([BIN + "/mn10300-elf-objdump", "-D", "-b", "binary", "-m", "mn10300",
                          "--adjust-vma=%#x" % BASE, "--start-address=%#x" % a, "--stop-address=%#x" % (a + n + 8),
                          _block_file(blk)],
                         capture_output=True, text=True, check=True).stdout
    rows = []
    for l in out.splitlines():
        m = re.match(r"^\s*([0-9a-f]{8}):\t((?:[0-9a-f]{2} )+)\s*(?:\t(\S+)\s*(.*))?$", l)
        if m:
            if m.group(3) is None:
                rows[-1][1] += bytes.fromhex(m.group(2).replace(" ", ""))
            else:
                rows.append([int(m.group(1), 16), bytes.fromhex(m.group(2).replace(" ", "")), m.group(3),
                             (m.group(4) or "").strip()])
    taken, size = [], 0
    for r in rows:
        if size >= n:
            break
        taken.append(r)
        size += len(r[1])
    return taken


def bracket_hooks(blk, extra):
    """The ART bracket sites of the hidden entries: (site, length, asm of the routine) for each.
    A compare `cmp V,dN; beq T` skips the entry also at its hidden value; a value `mov V,dN` loads the entry's current
    stored value from its byte in the value list of setting 111 (the loader switches that byte)."""
    hooks = []
    for x in extra:
        list_byte = slots.VALUE_LISTS[0] + slots.VALUE_LIST_STEP * x.place
        for a in x.bracket.addresses:
            ins = site_insns(blk, a - 1, 5)
            first = ins[0]
            body = []
            if first[2] == "cmp":
                reg = first[3].split(",")[1]
                assert first[3] == "%d,%s" % (x.stock_value, reg) and ins[1][2] == "beq", ins
                target = int(ins[1][3], 16)
                body += ["cmp %d,%s" % (x.stock_value, reg), "beq 5f", "cmp %d,%s" % (x.value, reg), "beq 5f"]
                rest = ins[2:]
                tail = ["5:  jmp %#x" % target]
            else:
                reg = first[3].split(",")[1]
                assert first[2] == "mov" and first[3] == "%d,%s" % (x.stock_value, reg), ins
                body += ["movbu (%#x),%s" % (list_byte + 0x40000000, reg)]
                rest = ins[1:]
                tail = []
            n = sum(len(r[1]) for r in ins)
            for r in rest:
                assert not re.match(r"^(b[a-z]{1,2}|jmp|call|calls|ret|retf|rets)$", r[2]), r
                body.append(".byte " + ", ".join("0x%02x" % c for c in r[1]) + "    # " + r[2] + " " + r[3])
            body.append("jmp %#x" % (a - 1 + n))
            body += tail
            hooks.append((a - 1, n, body, "%s %s" % (x.entry, first[2])))
    return hooks


def run(*a):
    return subprocess.run(a, check=True, capture_output=True, text=True).stdout


def main():
    work = sys.argv[1]
    listing = sys.argv[2] if len(sys.argv) > 2 else None
    os.makedirs(work, exist_ok=True)
    blk = parse(open(os.path.join(ROOT, STOCK), "rb").read()).blocks[0].payload
    get = lambda a, n: blk[a - BASE:a - BASE + n]
    word = lambda a: struct.unpack("<I", get(a, 4))[0]

    # ---- data: triples and records (segment 3)
    data = bytearray()
    triples, records = {}, {}
    rec_base = (DATA_AREA[0] + 3) & ~3
    off = 0
    for i, (name, _, _, code, _) in enumerate(ENTRIES):
        blockaddr = FILM_RAM + BLOCK * i
        recs = []
        for ch in range(3):
            words = [blockaddr + TONE + 512 * (slots.RECORD_TABLES * ch + idx) for idx in range(slots.RECORD_TABLES)]
            recs.append(rec_base + off)
            data += struct.pack("<8I", *words)
            off += 32
        records[code] = recs
    for i, (_, _, _, code, _) in enumerate(ENTRIES):
        triples[code] = rec_base + off
        data += struct.pack("<3I", *records[code])
        off += 12
    assert rec_base + len(data) <= DATA_AREA[1], "data area too small"

    # ---- code (segment 2)
    asm = [".section .sk,\"ax\""]
    asm.append("""GCOMMON:                         # a1 = three record addresses (as remap7b-code's shared part)
    extbu d2
    movbu (28,sp),d3
    mov d2,d0
    mov d3,d1
    mov (a1),a0
    call %#x,[d2,d3],8
    mov a0,(a2)
    mov d2,d0
    mov d3,d1
    mov (4,a1),a0
    call %#x,[d2,d3],8
    mov a0,(a3)
    mov (8,a1),a0
    jmp %#x""" % (GAMMA_PICK, GAMMA_PICK, GAMMA_TAIL))
    asm.append("""CGEN:                            # d1 = a 97-byte chroma record: the six pointers of a stock chroma handler
    mov (4,sp),a0
    mov d1,(a0)
    mov d1,d0
    add 16,d0
    mov d0,(4,a0)
    add 16,d0
    mov d0,(8,a0)
    add 17,d0
    mov d0,(12,a0)
    add 16,d0
    mov d0,(16,a0)
    add 16,d0
    add 20,a0
    jmp %#x""" % CHROMA_TAIL)
    for i, (name, _, _, code, _) in enumerate(ENTRIES):
        b = FILM_RAM + BLOCK * i
        asm.append(".section %s,\"ax\"" % (".sk" if i < 6 else ".sc"))
        asm.append("""G%(c)d: mov %(tr)#x,a1
    jmp GCOMMON
S%(c)d: mov %(sat)#x,a3
    jmp %(satc)#x
X%(c)d: mov %(sixs)#x,a3
    mov %(sixh)#x,a2
    jmp %(sixc)#x
C%(c)d: mov %(chr)#x,d1
    jmp CGEN
VF%(c)d: mov %(c)d,d2
    jmp %(tf)#x
VL%(c)d: mov %(c)d,d2
    jmp %(t1)#x
VM%(c)d: mov %(c)d,d2
    jmp %(t2)#x""" % {"c": code, "tr": triples[code], "sat": b + SAT, "satc": SAT_COMMON, "sixs": b + SIX_S,
                     "sixh": b + SIX_H, "sixc": SIX_COMMON, "chr": b + CHROMA, "tf": slots.FILTER_TYPE_TAIL,
                     "t1": slots.LIVE_VIEW[0][2], "t2": slots.LIVE_VIEW[1][2]})
    chain = [".section .sk,\"ax\"", "CHAIN:                           # d0 = art code (the stock compare chain 0x7E56C6A5 jumps here)"]
    for i, (_, _, _, code, kind) in enumerate(ENTRIES):
        chain.append("    cmp %d,d0\n    beq M%d" % (code, code))
    chain.append("""STOCKM:
    cmp 70,d0
    beq 1f
    cmp 79,d0
    beq 1f
    jmp %#x
1:  jmp %#x
MUSE:
    mov d3,a0
    jmp %#x""" % (MATRIX_STOCK_REST, MATRIX_STOCK_70, MATRIX_USE))
    for i, (_, _, _, code, kind) in enumerate(ENTRIES):
        if kind == "inplace":
            # only the exact film matrix address counts: RAM that held anything else (stale, changed bits) is stock
            chain.append("M%d: mov (%#x),a1\n    cmp %#x,a1\n    bne STOCKM\n    bra MUSE" %
                         (code, MATPTR + 0x40000000 + INPLACE_PTR[code], FILM_RAM + BLOCK * i + MATRIX))
        else:
            chain.append("M%d: mov %#x,a1\n    bra MUSE" % (code, FILM_RAM + BLOCK * i + MATRIX))
    asm += chain
    # Cross Process's scene-adaptive hue: off while the entry has a film (the matrix pointer holds the film address)
    xp = [i for i, e in enumerate(ENTRIES) if e[3] == 85][0]
    asm.append(""".section .sk,"ax"
HUE: mov (%#x),a1
    cmp %#x,a1
    beq 1f
    cmp 2,d0
    beq 2f
    mov 1,d1
    cmp 4,d0
    beq 2f
1:  jmp %#x
2:  jmp %#x""" % (MATPTR + 0x40000000 + INPLACE_PTR[85], FILM_RAM + BLOCK * xp + MATRIX, HUE_SKIP, HUE_APPLY))
    asm.append(".section .hu,\"ax\"\n    jmp HUE\n    nop")
    # the film codes' look: the stock identity table (at the end of .sk: nothing else moves)
    asm.append(""".section .sk,"ax"
LKID: mov %#x,a0
    jmp %#x""" % (slots.IDENTITY_LOOK, LOOK_TAIL))
    # no 12-region table for the film codes: the case at the end of .sk (nothing of version 2 moves),
             # the descriptor in segment 3 (.td)
    iso = struct.unpack("<12I", get(TWELVE_FLAT_DESC + 4, 48))
    assert all(get(a, 24) == struct.pack("<12H", *[256] * 12) for a in iso)
    asm.append(""".section .sk,"ax"
OFFCASE: .byte 0xfc, 0xdc            # mov OFFDESC,a0 (as the stock cases)
    .long OFFDESC
    .byte 0xde, 0xf0, 0x14           # retf [d2,d3,a2,a3],20: the worker's own return
.section .td,"a"
OFFDESC: .long OFFZERO - %d          # the table: of it only the enable mask (OFFZERO, 0) acts
    .long %s
OFFZERO: .long 0""" % (TWELVE_MASK_AT, ", ".join("%#x" % a for a in iso)))
    extra = [x for x in slots.EXTRA_SLOTS if x.entry in {e[0] for e in ENTRIES if e[4] == "hidden"}]
    bhooks = bracket_hooks(blk, extra)
    slots_at = []
    for lo, hi in BRACKET_RUNS:
        slots_at += list(range(lo, hi - BRACKET_SLOT + 1, BRACKET_SLOT))
    assert len(slots_at) >= len(bhooks), "too few slots for the bracket routines"
    for k, (site, n, body, what) in enumerate(bhooks):
        asm.append(".section .q%d,\"ax\"\nBK%d:  # %s at %#x\n    " % (k, k, what, site) + "\n    ".join(body))
        asm.append(".section .b%d,\"ax\"\n    jmp BK%d\n" % (k, k) + "    nop\n" * (n - 5))
    asm.append(".section .hk,\"ax\"\n    jmp CHAIN\n    nop")
    src = "\n".join(asm) + "\n"
    calls = sorted(set(re.findall(r"(?:jmp|call)\s+0x([0-9a-f]{8})", src)))
    src = re.sub(r"((?:jmp|call)\s+)0x([0-9a-f]{8})", r"\1s_\2", src)
    args = ["--defsym=s_%s=0x%s" % (a, a) for a in calls]
    args += ["--section-start=.sc=%#x" % CODE_AREA[0], "--section-start=.sk=%#x" % SHARED_AREA[0],
             "--section-start=.hk=%#x" % MATRIX_HOOK, "--section-start=.hu=%#x" % HUE_SITE]
    args += ["--section-start=.td=%#x" % TWELVE_DATA[0]]
    args += ["--section-start=.b%d=%#x" % (k, site) for k, (site, _, _, _) in enumerate(bhooks)]
    args += ["--section-start=.q%d=%#x" % (k, slots_at[k]) for k in range(len(bhooks))]
    s, o, e = (os.path.join(work, "structure." + x) for x in ("s", "o", "elf"))
    open(s, "w").write(src)
    run(BIN + "/mn10300-elf-as", "-o", o, s)
    run(BIN + "/mn10300-elf-ld", *args, "-e", "%#x" % CODE_AREA[0], "-o", e, o)
    sym = {l.split()[2]: int(l.split()[0], 16) for l in run(BIN + "/mn10300-elf-nm", e).splitlines()
           if len(l.split()) == 3}

    def sect(name):
        b = os.path.join(work, "sect.bin")
        run(BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", name, e, b)
        return open(b, "rb").read()

    code = sect(".sc")
    assert CODE_AREA[0] + len(code) <= CODE_AREA[1], "code area too small: %d" % len(code)
    shared = sect(".sk")
    assert SHARED_AREA[0] + len(shared) <= SHARED_AREA[1], "shared area too small: %d" % len(shared)
    hook = sect(".hk")
    assert len(hook) == 6 and get(MATRIX_HOOK, 6) == MATRIX_HOOK_BYTES

    ops = []

    def op(addr, new, note):
        expect = get(addr, len(new))
        if expect == new:
            return
        ops.append({"type": "bytes", "block": 0, "offset": "0x%X" % (addr - BASE), "expect": expect.hex(),
                    "new": new.hex(), "_addr": "0x%08X" % addr, "_note": note})

    op(CODE_AREA[0], code, "new code, segment 2: tone, saturation, six-axis, chroma and value stubs of the film "
       "codes of the last six entries (%d B)" % len(code))
    op(SHARED_AREA[0], shared, "new code, segment 2: the shared tone part, the chroma helper, the stubs of the first "
       "six entries, the art-matrix chain (%d B)" % len(shared))
    op(rec_base, bytes(data), "data, segment 3: three tone records per film code (8 tables each, in the entry's RAM block) "
       "and the record triples (%d B)" % len(data))
    td = sect(".td")
    assert TWELVE_DATA[0] + len(td) <= TWELVE_DATA[1] and len(td) == 56
    op(TWELVE_DATA[0], td, "data, segment 3: OFFDESC, the 12-region descriptor of the film codes: table = OFFZERO - "
       "3024, the 12 stock flat ISO-weight pointers, then OFFZERO (u32 0: the table's enable mask, every record off)")
    op(MATRIX_HOOK, hook, "hook: the stock art-matrix compare chain jumps to CHAIN (film codes first, then the stock "
       "compares of 70 / 79 / 102 / 103 unchanged)")
    hu = sect(".hu")
    assert len(hu) == 6 and get(HUE_SITE, 6) == HUE_BYTES
    op(HUE_SITE, hu, "hook: Cross Process's adaptive-hue test (`cmp 2,d0; beq; mov 1,d1`) -> HUE: no hue while the "
       "entry has a film, else the stock tests")
    for k in range(len(bhooks)):
        q = sect(".q%d" % k)
        assert len(q) <= BRACKET_SLOT, (k, len(q))
        op(slots_at[k], q, "new code, segment 2: ART bracket routine BK%d (%d B)" % (k, len(q)))
    for k, (site, n, body, what) in enumerate(bhooks):
        h = sect(".b%d" % k)
        assert len(h) == n and h[0] == 0xDC
        op(site, h, "hook: ART bracket, %s of the entry's stored value -> BK%d (the value-list byte of setting 111)"
           % (what, k))

    # ---- tone hash: entries for 79 and the route / hidden codes (target: stock default; static targets for the
    # codes no stock entry reaches)
    H, N = slots.GAMMA_HASH, slots.GAMMA_HASH_ENTRIES
    entries = [list(struct.unpack_from("<iI", get(H, 8 * N), 8 * k)) for k in range(N)]

    def place_of(key):
        p = key & 31
        for _ in range(N):
            if entries[p][0] == key:
                return p
            if entries[p][0] == 0:
                return None
            p = (p + 1) % N

    switch = {name: [] for name, *_ in ENTRIES}
    gamma_place = {}
    for name, _, _, c, kind in ENTRIES:
        key = c - slots.GAMMA_KEY_BASE
        p = place_of(key)
        if p is None:
            p = key & 31
            while entries[p][0] != 0:
                p = (p + 1) % N
            stock_target = slots.GAMMA_DEFAULT_HANDLER
            target = sym["G%d" % c] if kind != "inplace" else stock_target
            entries[p] = [key, target]
            op(H + 8 * p, struct.pack("<iI", key, target), "tone hash: code %d (key %d) -> %s" %
               (c, key, "its tone stub" if kind != "inplace" else "the stock default (the loader switches it)"))
        gamma_place[c] = p
        if kind == "inplace":
            switch[name].append((H + 8 * p + 4, struct.pack("<I", sym["G%d" % c]),
                                 struct.pack("<I", entries[p][1]), "tone hash target of code %d" % c))

    # ---- stage tables of the film codes
    for name, _, _, c, kind in ENTRIES:
        look = sym["LKID"]
        for (table, first), target, what in ((slots.LOOK_JUMP, look, "look"),
                                             (slots.SATURATION_JUMP, sym["S%d" % c], "saturation"),
                                             (slots.SIX_AXIS_JUMP, sym["X%d" % c], "six-axis"),
                                             (slots.CHROMA_JUMP, sym["C%d" % c], "chroma")):
            a = table + 4 * (c - first)
            if kind == "inplace":
                switch[name].append((a, struct.pack("<I", target), get(a, 4), "%s entry of code %d" % (what, c)))
            else:
                op(a, struct.pack("<I", target), "%s entry of code %d -> %s" % (what, c,
                   "the identity look" if what == "look" else "its stub"))

    # ---- 12-region hash (version 3): the film codes get OFFCASE. Every film code gets a permanent entry; an in-place
    # code's entry holds the worker's default case (0x7E56E5DC, where a key that is not found also goes, with the same
    # d0, d1 and stack: the only state it reads) until the loader switches it to OFFCASE.
    TH, TN = TWELVE_HASH, TWELVE_HASH_N
    tents = [list(struct.unpack_from("<II", get(TH, 8 * TN), 8 * k)) for k in range(TN)]
    assert sym["OFFZERO"] == sym["OFFDESC"] + 52 and sym["OFFZERO"] % 4 == 0
    for name, _, _, c, kind in ENTRIES:
        key = c - TWELVE_KEY_BASE
        p = key & (TN - 1)
        while tents[p][0] != 0:
            assert tents[p][0] != key, "code %d has a stock 12-region entry" % c
            p = (p + 1) % TN
        assert tents[p][1] == TWELVE_DEFAULT_CASE           # an empty slot holds the default case
        target = TWELVE_DEFAULT_CASE if kind == "inplace" else sym["OFFCASE"]
        op(TH + 8 * p, struct.pack("<II", key, target), "12-region hash slot %d: code %d (key %d) -> %s" % (
           p, c, key, "the default case (the loader switches it)" if kind == "inplace" else "OFFCASE: no 12-region table"))
        if kind == "inplace":
            switch[name].append((TH + 8 * p + 4, struct.pack("<I", sym["OFFCASE"]), struct.pack("<I", TWELVE_DEFAULT_CASE),
                                 "12-region case of code %d: OFFCASE (no table) / the default case" % c))
        tents[p] = [key, target]
    assert sum(1 for k, _ in tents if k == 0) >= 8          # lookups of absent keys still end at an empty slot

    # ---- value routes
    tails = [("VF", slots.FILTER_TYPE_JUMP, None)] + [("VL", s, m) for s, m, _ in slots.LIVE_VIEW[:1]] + \
        [("VM", s, m) for s, m, _ in slots.LIVE_VIEW[1:]]
    for name, stock_value, value, c, kind in ENTRIES:
        row = 4 * (value - slots.FIRST_ART_VALUE)
        words = [(slots.FILTER_TYPE_JUMP + row, sym["VF%d" % c], "art_GetFilterType row of value %d" % value)]
        for (still, movie, _), stub in zip(slots.LIVE_VIEW, ("VL", "VM")):
            words.append((still + row, sym["%s%d" % (stub, c)], "live-view still row of value %d" % value))
            words.append((movie + row, sym["%s%d" % (stub, c)], "live-view movie row of value %d" % value))
        if kind == "hidden":
            words += [(slots.KIND_JUMP + row, slots.KIND_COLOUR_ONLY, "record kind of value %d" % value),
                      (slots.EXIF_JUMP + row, EXIF_OFF, "EXIF case of value %d" % value),
                      (slots.IS_ART_JUMP + row, slots.IS_ART_YES, "'is art' of value %d" % value)]
            for a, w, note in words:
                op(a, struct.pack("<I", w), note + " (hidden value: flashed)")
        else:
            if kind == "route":
                words.append((slots.KIND_JUMP + row, slots.KIND_COLOUR_ONLY, "record kind of value %d" % value))
            words.append((slots.EXIF_JUMP + row, EXIF_OFF, "EXIF case of value %d" % value))
            for a, w, note in words:
                if word(a) != w:
                    switch[name].append((a, struct.pack("<I", w), get(a, 4), note))

    # ---- hash keys of the hidden values (as films12-structure)
    def hash_add(table, key, like, note):
        raw = get(table, 8 * slots.VALUE_HASH_ENTRIES)
        ents = [list(struct.unpack_from("<2I", raw, 8 * k)) for k in range(slots.VALUE_HASH_ENTRIES)]
        for o in ops:
            a = int(o["_addr"], 16)
            if table <= a < table + 8 * slots.VALUE_HASH_ENTRIES:
                k = (a - table) // 8
                ents[k] = list(struct.unpack("<2I", bytes.fromhex(o["new"])))

        def find(k):
            p = k & 31
            for _ in range(32):
                if ents[p][0] == k:
                    return p
                if ents[p][0] == 0:
                    return None
                p = (p + 1) % 32
        src = find(like)
        assert src is not None and find(key) is None, (hex(table), key)
        p = key & 31
        while ents[p][0] != 0:
            p = (p + 1) % 32
        op(table + 8 * p, struct.pack("<2I", key, ents[src][1]), note)

    for name, stock_value, value, c, kind in ENTRIES:
        if kind == "hidden":
            hash_add(slots.COLOUR_TONE_HASH, value, stock_value, "colour-tone name hash: key %d as %d" % (value, stock_value))
            hash_add(slots.MOVIE_TAG_HASH, value, slots.POP_ART_VALUE, "movie tag hash: key %d as 100" % value)
            hash_add(slots.RECORD_CLASS_HASH, value, slots.POP_ART_VALUE, "record class hash: key %d as 100" % value)

    # ---- codes 75 and 125: the job-block compares
    for a, imm in NEUTRAL_75:
        assert get(a, 1)[0] == imm, hex(a)
        op(a, b"\xff", "job block compare of code %d: immediate -1, no art code matches (75 and 125 are film codes)"
           % imm)

    # ---- hidden entries: the stored value in the value lists, the "is art" lists and the ART-mode preset (data; the
    # ART bracket constants are code: the loader's hook handles them)
    extra = {x.entry: x for x in slots.EXTRA_SLOTS}
    for name, stock_value, value, c, kind in ENTRIES:
        if kind != "hidden":
            continue
        x = extra[name]
        assert (x.stock_value, x.value, x.art_code) == (stock_value, value, c), name
        addrs = [t + slots.VALUE_LIST_STEP * x.place for t in slots.VALUE_LISTS]
        addrs += [t + slots.ART_VALUE_LIST_STEP * (x.place - slots.FIRST_ART_PLACE) for t in slots.ART_VALUE_LISTS]
        assert get(x.preset_value - 4, 4) == struct.pack("<I", slots.PICTURE_MODE_SETTING), name
        addrs.append(x.preset_value)
        for a in addrs:
            assert get(a, 1)[0] == stock_value, (name, hex(a))
            switch[name].append((a, bytes((value,)), bytes((stock_value,)), "stored value of the entry"))

    # ---- in-place extras: WB pairs of Pale&Light; RAM matrix pointer (the loader writes it)
    for name, _, _, c, kind in ENTRIES:
        if name == "Pale&Light Color":
            for k in (0, 2):
                a = WB_PAIRS + 4 * k
                switch[name].append((a, struct.pack("<2H", 256, 256), get(a, 4), "white-balance pair %d -> 1.0" % k))
        if kind == "inplace":
            i = [e[0] for e in ENTRIES].index(name)
            switch[name].append((MATPTR + INPLACE_PTR[c], struct.pack("<I", FILM_RAM + BLOCK * i + MATRIX),
                                 b"\0\0\0\0", "RAM matrix pointer of code %d" % c))

    stock_sha = hashlib.sha256(open(os.path.join(ROOT, STOCK), "rb").read()).hexdigest()
    json.dump({
        "name": SPEC,
        "description": (
            "Film looks on the stock filters, the flashed part (experiments/2026-11-18-stock-filters/design.md): one "
            "film code per art-filter entry (Pop Art 79, Soft Focus 75, Pale&Light 71, Light Tone 72, Grainy Film 94, Pin "
            "Hole 92, Diorama 125, Cross Process 85, Gentle Sepia 98, Dramatic Tone 144, Key Line 156, Watercolor 159) "
            "with tone, saturation, six-axis, chroma and matrix in the entry's RAM block at 0x7E4D1000 + 0x3200 x entry; "
            "the stage entries of the codes that no stock entry reaches, the art-matrix chain, the hidden stored values "
            "111, 112, 114, 115, 118 and their hash keys, and the four job-block compares of 75 / 125. Nothing here is "
            "reached while no entry has a film: the loader switches the entry's words. Every expect is a stock byte." +
            (" Version 2 (experiments/2026-11-20-film-name-exif/NOTES.md): the film codes' look entry -> LKID, the "
             "stock identity look table 0x7E75B8F0; the EXIF case of an entry with a film -> 0x7E70DF1B (ArtFilter "
             "Off).") +
            (" Version 3 (experiments/2026-11-20-model-calibration/NOTES.md §6): no 12-region table for the film "
             "codes: OFFCASE returns a descriptor whose table has enable mask 0; the eight codes no stock entry "
             "reaches get a hash entry 0x7E78C6E4 -> OFFCASE; the in-place codes' entries hold the default case, "
             "switched to OFFCASE by the loader.")),
        "base": STOCK, "base_sha256": stock_sha,
        "ops": ops,
    }, open(os.path.join(ROOT, "data", "specs", SPEC + ".json"), "w"), indent=1)
    open(os.path.join(ROOT, "data", "specs", SPEC + ".json"), "a").write("\n")
    layout = {"film_ram": FILM_RAM, "block": BLOCK,
              "offsets": {"tone": TONE, "sat": SAT, "six_s": SIX_S, "six_h": SIX_H,
                          "chroma": CHROMA, "matrix": MATRIX},
              "matptr": MATPTR,
              "entries": [{"name": n, "stock_value": sv, "value": v, "code": c, "kind": k,
                           "switch": [{"address": a, "film": f.hex(), "stock": s.hex(), "note": note}
                                      for a, f, s, note in switch[n]]}
                          for n, sv, v, c, k in ENTRIES]}
    os.makedirs(os.path.join(ROOT, "build", OUT), exist_ok=True)
    json.dump(layout, open(os.path.join(ROOT, "build", OUT, "layout.json"), "w"), indent=1)
    print("wrote data/specs/%s.json: %d ops; code %d B at %#x, data %d B at %#x" %
          (SPEC, len(ops), len(code), CODE_AREA[0], len(data), rec_base))
    for n, *_ in ENTRIES:
        print("  %-18s switches %2d words" % (n, len(switch[n])))
    if listing:
        open(listing, "w").write(run(BIN + "/mn10300-elf-objdump", "-d", "-j", ".sc", "-j", ".sk", "-j", ".hk", e))


if __name__ == "__main__":
    main()
