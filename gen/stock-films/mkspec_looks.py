"""Write patches/card-looks.json and builds/card-looks.json: film looks loaded from the SD card and kept in the camera.

    uv run python experiments/2026-11-17-card-looks/scripts/mkspec_looks.py [--v2] [LISTING.txt]

--v2 writes patches/card-looks-2.json and builds/card-looks-2.json instead: the same loader for twelve colour slots
(mkspec_slots.LAYOUT, Grainy Film a colour slot) with the menu row of patches/looks-menu.json as its trigger: when the
GUI leaves the menu (not to power-off) with setting 449 at Load (0), T_GUI sets it back to Off (1) with the GUI's
setSetting, as the menu does, and starts the task in mode 1. The firmware writes 1 into the setting at every start, so
a camera shows Off. There is no load at the first menu.

Needs build/films-12d.BIN (uv run epm2mod make films-12d) and the toolchain (tools/setup.sh).
The design is design.md sections 2-5 and 9.3; the file format is docs/look-file-format.md.

What the spec adds to films-12d (no debug log):
  * T_GUI, a hook on the GUI state setter's last trace call (0x7ECDF6E4, task CA_MAIN; the site log-core used,
    camera-tested): at the first GUI state of a session it starts task USRTEST_A in mode 0; at the first menu or
    playback state of a session, when the card is not being written, in mode 1.
  * T_TASK, the entry of the dormant task USRTEST_A (id 0x90; the log's flush task, camera-tested): mode 1 reads
    C:\\EPM2LOOK.BIN into a scratch area of the EEROM bank's unused tail, checks it (VERIFY) and copies it into the
    store area of the tail; when a byte changed, it calls the bank save API (0x7E680272). Both modes then check the
    store and write its looks into the slots (APPLY), and make the look stages recompute.
  * The slot table: for each of the 12 menu entries, the kind of look it takes and a list of operations (copy N bytes
    of the record to an address, or make a tone table from a curve of the record and a stock default table), in two
    data areas of segment 3.

The script checks its own tables with a Python model of VERIFY and APPLY: the look file of looks/card-looks.json
applied to films-12d leaves every byte as it is (the built-in looks are the same looks), and another file changes
only the slot tables.
"""

import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import zlib
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from epm2mod.container import parse  # noqa: E402
from epm2mod.looks import lookfile, lookpack, slots  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

BIN = os.path.join(ROOT, "build", "toolchain", "bin")
BASE = slots.BLOCK0_BASE
SPEC = "card-looks"
BASE_BUILD = "builds/films-12d.json"
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"

# where the code goes: free runs of the segment-2 code areas (docs/code-space-map.md; the runs of the persistence
# probe log-card-keep, which this spec supersedes, and the free end of the area 0x7ECB0888-0x7ECB1000)
RUNS = {
    ".tk": (0x7ECB0EE8, 0x7ECB1000),
    ".tb": (0x7EBF2888, 0x7EBF2900),
    ".vf": (0x7EBF2A8C, 0x7EBF2B00),
    ".vc": (0x7EBF2B90, 0x7EBF2C00),
    ".ap": (0x7EBF1090, 0x7EBF10FC),
    ".aq": (0x7EBF29C0, 0x7EBF2A00),
    ".ds": (0x7EBF3B10, 0x7EBF3B52),
}
# where the slot table goes: two data areas of segment 3 (reclaim-space rows 4 and 3, USABLE-DATA)
DATA = [(0x7EE40B18, 0x7EE411F6), (0x7EE541B4, 0x7EE548B1)]

HOOK = (0x7ECDF6E4, 5, bytes.fromhex("cd4f6cb010"))     # GUI state setter 0x7ECDF5E9, its last trace call
TASK_ENTRY = 0x7E439C80                                   # CPU0 task table, row of id 0x90 (USRTEST_A): the entry word
TASK_ENTRY_STOCK = 0x7E501C5B
STORE = 0x603F8000                                        # the stored look file, in the EEROM bank's unused tail
SCRATCH = 0x603FD040                                      # the file read from the card (uncached alias 0xA03FD040)
TAIL = (0x603F74B8, 0x60404668)                           # the unused tail (design.md section 3)
MAXREAD = lookfile.MAX_FILE_BYTES + 4                     # a longer file is read short and refused
REFRESH_WORDS = (0xA07500B4, 0xA07500B8)                  # the IMG library's builder words: 0 = clear the stage cache
REFRESH_BYTES = (0x60510CD5, 0x60511305)                  # the gamma states' art-code bytes: 0xFF = rebuild
MONO_MATRIX = 0x7EBF2F5A                                  # films12bw-doublex: the matrix behind its chain tail
assert TAIL[0] <= STORE and STORE + lookfile.MAX_FILE_BYTES <= SCRATCH and SCRATCH + MAXREAD <= TAIL[1]

ASM = r"""
.equ MAGIC,    0x4b4c5045        # "EPLK"
.equ STORE,    %(store)#x        # the stored look file (cached address)
.equ SCRU,     %(scratch)#x + 0x40000000   # the scratch area, uncached: what the file layer wrote into RAM
.equ MAXREAD,  %(maxread)d
.equ SLOTTAB,  %(slottab)#x      # 12 pointers to the slots' operation lists (segment 3)
.equ CRCT,     %(crct)#x         # CRC-32 nibble table, 16 words (segment 3)
.equ FLAGS_U,  FLAGS + 0x40000000   # the flags through the uncached alias (they start at 0: segment 2 is loaded
.equ BUSY,     FLAGS_U           #   from flash at every start). BUSY: the task runs
.equ APPLIED,  FLAGS_U + 1       # the task was started in mode 0 in this session
.equ CARDDONE, FLAGS_U + 2       # the task was started in mode 1 in this session
.equ MODE,     FLAGS_U + 3       # 0: apply the stored looks; 1: load the card file first

.section .tk,"ax"
%(gui)sT_TASK:                          # task USRTEST_A (id 0x90), started by T_GUI; it ends when it returns
    movm [d2,d3,a2,a3],(sp)
    add -32,sp                   # (0,sp) is the return slot of every call: no locals here
%(reset)s    movbu (MODE),d0
    cmp 0,d0
    beq 6f
    mov PATH,a0
    mov RMODE,a1
    call 0x7e5c52dc,[],20        # fileif_fopen(path, "r") -> a0 = handle or 0
    mov a0,a3
    cmp 0,a3
    beq 6f                       # no card or no file: the stored looks
    mov SCRU,a0
    mov 1,d0
    mov MAXREAD,d1
    mov a3,a1
    call 0x7e5c536f,[],24        # fileif_fread(a0 = buffer, d0 = 1, d1 = bytes, a1 = handle) -> bytes read
    mov d0,d2
    mov a3,a0
    call 0x7e5c5308,[],12        # fileif_fclose(a0 = handle)
    mov SCRU,a0
    mov d2,d0
    calls VERIFY                 # d0 = 0: a valid look file
    cmp 0,d0
    bne 6f                       # a bad file: nothing is written, the stored looks stay
    jmp T_KEEP
6:  jmp T_STORED

.section .tb,"ax"
T_KEEP:
    mov SCRU,a0                  # copy it into the store; d2 counts the bytes that change
    mov STORE,a1
    mov (8,a0),d3
    clr d2
1:  movbu (a0),d0
    movbu (a1),d1
    cmp d0,d1
    beq 2f
    inc d2
    movbu d0,(a1)
    movbu d0,(0x40000000,a1)
2:  inc a0
    inc a1
    add -1,d3
    bne 1b
    cmp 0,d2
    beq T_STORED
SAVE:
    call 0x7e680272,[],48        # the bank save API: the changed bank goes to flash now
T_STORED:
    mov STORE,a0                 # the stored looks: just loaded, or kept from an earlier session
    mov (8,a0),d0                # its length stands for the bytes read
    calls VERIFY
    cmp 0,d0
    bne T_END                    # nothing stored (or a bad copy): the flashed looks stay
    mov STORE,a0
    calls APPLY
    clr d0                       # make the look stages recompute, as the boot init 0x7E560AC0 does
    mov d0,(%(rw0)#x)
    mov d0,(%(rw1)#x)
    mov 0xff,d0
    movbu d0,(%(rb0)#x)
    movbu d0,(%(rb1)#x)
T_END:
    clr d0
    movbu d0,(BUSY)
    ret [d2,d3,a2,a3],48

.section .vf,"ax"
VERIFY:                          # a0 = a look file, d0 = bytes read -> d0 = 0 when it is valid (format section "Checks")
    movm [d2,d3,a2,a3],(sp)
    mov a0,a2
    mov d0,d3
    mov (a2),d0
    cmp MAGIC,d0
    bne 8f
    mov (4,a2),d0
    and 0xffff00ff,d0
    cmp 0x06ac0001,d0            # version 1, record size 1708
    bne 8f
    mov (8,a2),d0
    cmp d0,d3
    bne 8f                       # the bytes read are not the length
    movbu (5,a2),d1
    cmp 12,d1
    bhi 8f
    mov 1708,d2
    mulu d1,d2
    add 32,d2
    cmp d2,d3
    bne 8f                       # the length is not 32 + count x 1708
    mov a2,a0                    # CRC-32 of bytes 16 to the end, 4 bits a step
    add 16,a0
    add -16,d3
    mov -1,d0
    mov CRCT,a1
1:  movbu (a0),d1
    xor d1,d0
    mov d0,d1
    and 15,d1
    asl2 d1
    mov (d1,a1),d1
    lsr 4,d0
    xor d1,d0
    mov d0,d1
    and 15,d1
    asl2 d1
    mov (d1,a1),d1
    lsr 4,d0
    xor d1,d0
    inc a0
    add -1,d3
    bne 1b
    jmp V_REC
8:  jmp V_BAD

.section .vc,"ax"
V_REC:                           # the CRC; then every record: slot 0-11, no slot twice, the kind of the slot
    not d0
    mov (12,a2),d1
    cmp d1,d0
    bne V_BAD
    mov (16,a2),d0
    cmp 0x01600101,d0            # E-PM2, firmware 1.6
    bne V_BAD
    movbu (5,a2),d3
    mov a2,a3
    add 32,a3
    clr d2                       # the slots seen, one bit each
2:  cmp 0,d3
    beq V_OK
    movbu (a3),d0
    cmp 12,d0
    bcc V_BAD
    mov 1,d1
    asl d0,d1
    mov d1,a0
    and d2,d1
    bne V_BAD
    mov a0,d1
    or d1,d2
    asl2 d0
    mov SLOTTAB,a0
    mov (d0,a0),a0
    mov (a0),d0                  # the kind the slot takes
    movbu (1,a3),d1
    cmp d0,d1
    bne V_BAD
    add 1708,a3
    add -1,d3
    bra 2b
V_OK:
    clr d0
    bra 9f
V_BAD:
    mov 1,d0
9:  movm (sp),[d2,d3,a2,a3]
    rets

.section .ap,"ax"
APPLY:                           # a0 = a valid look file: each record's operations
    movm [d2,d3,a2,a3],(sp)
    add -16,sp                   # (4,sp) records left, (8,sp) the operation, (12,sp) the end of a tone table
    movbu (5,a0),d0
    mov d0,(4,sp)
    mov a0,a3
    add 32,a3
1:  mov (4,sp),d0
    cmp 0,d0
    beq 9f
    add -1,d0
    mov d0,(4,sp)
    movbu (a3),d0
    asl2 d0
    mov SLOTTAB,a2
    mov (d0,a2),a2
    add 4,a2
2:  mov (a2),d0                  # an operation {u16 offset in the record, u16 count, u32 address, u32 default}
    cmp 0,d0
    beq 8f
    mov d0,d1
    exthu d1
    mov a3,a0
    add d1,a0
    lsr 16,d0
    mov (4,a2),a1
    mov (8,a2),d1
    cmp 0,d1
    bne 4f
3:  movbu (a0),d1                # default 0: copy count bytes (cached address and uncached alias)
    movbu d1,(a1)
    movbu d1,(0x40000000,a1)
    inc a0
    inc a1
    add -1,d0
    bne 3b
    bra A_OPNEXT
4:  jmp A_TONE
A_OPNEXT:
    add 12,a2
    bra 2b
8:  add 1708,a3
    bra 1b
9:  add 16,sp
    movm (sp),[d2,d3,a2,a3]
    rets

.section .aq,"ax"
A_TONE:                          # a tone table of count entries: entry k = the curve at default[k], at most 1023
    mov a2,(8,sp)
    mov d1,a2
    mov a1,d1
    add d0,d1
    add d0,d1
    mov d1,(12,sp)
    movhu (a0),d0                # the curve's value at index d1
    add 2,a0                     # its steps, 4 bits each, low nibble first
    clr d1
A_K:
    movhu (a2),d2
    add 2,a2
6:  cmp d2,d1
    bcc 10f
    movbu (a0),d3
    btst 1,d1
    beq 11f
    lsr 4,d3
    inc a0
    bra 12f
11: and 15,d3
12: add d3,d0
    inc d1
    bra 6b
10: jmp A_PUT

.section .ds,"ax"
A_PUT:
    mov d0,d3
    cmp 1023,d3
    bls 13f
    mov 1023,d3
13: movhu d3,(a1)
    movhu d3,(0x40000000,a1)
    add 2,a1
    mov (12,sp),d3
    cmp d3,a1
    bne A_NEXT
    mov (8,sp),a2
    jmp A_OPNEXT
A_NEXT:
    jmp A_K
"""

GUI_V1 = r"""
T_GUI:                           # the "state =" trace call of the GUI state setter, d0 = new state (task CA_MAIN)
    movm [d2,other],(sp)
    mov psw,d2                   # this routine changes the flags: keep them
    mov d0,d1
    movbu (BUSY),d0
    cmp 0,d0
    bne 9f
    movbu (APPLIED),d0
    cmp 0,d0
    bne 1f
    mov 1,d0
    movbu d0,(APPLIED)
    clr d0                       # mode 0, at the first GUI state of the session
    bra 5f
1:  movbu (CARDDONE),d0
    cmp 0,d0
    bne 9f
    mov d1,d0
    lsr 8,d0
    cmp 0x57,d0                  # 0x57xx: the menus
    beq 2f
    lsr 4,d0
    cmp 3,d0                     # 0x3xxx: playback
    bne 9f
2:  call 0x7ecd360a,[d2],8       # the GUI's isMediaWriting(): 1 while the card is written
    cmp 0,d0
    bne 9f
    mov 1,d0
    movbu d0,(CARDDONE)          # mode 1, once per session
5:  movbu d0,(MODE)
    mov 1,d0
    movbu d0,(BUSY)
    mov 0x90,d0
    call 0x7e449541,[d2,d3],12   # OlyTaSt(USRTEST_A)
9:  mov d2,psw
    nop
    nop
    movm (sp),[d2,other]
%(displaced)s
    jmp %(back)#x

"""

GUI_V2 = r"""
T_GUI:                           # the "state =" trace call of the GUI state setter, d0 = new state (task CA_MAIN)
    movm [d2,d3,other],(sp)
    mov psw,d2                   # this routine changes the flags: keep them
    mov d0,d3                    # the new state
    movbu (BUSY),d0
    cmp 0,d0
    bne 9f
    movbu (APPLIED),d0
    cmp 0,d0
    bne 1f
    mov 1,d0
    movbu d0,(APPLIED)
    clr d0                       # mode 0, at the first GUI state of the session
    bra 5f
1:  mov d3,d0
    lsr 8,d0
    cmp 0x57,d0                  # 0x57xx: still in the menus
    beq 9f
    lsr 4,d0
    cmp 2,d0                     # 0x2xxx: power off, sleep
    beq 9f
    mov 0xd7b1,d0                # setting 449, the row "Load Looks" (patches/looks-menu.json): 0 = Load, 1 = Off
    mov 0,a0
    clr d1
    call 0x7e457c75,[d2,d3],12   # prm_get(tag, 0, 0)
    cmp 0,d0
    bne 9f
    call 0x7ecd360a,[d2],8       # the GUI's isMediaWriting(): 1 while the card is written (then: at a later state)
    cmp 0,d0
    bne 9f
    mov 449,d0                   # the row back to Off, as the menu sets a value: the GUI's setSetting(449, 1)
    mov 1,d1
    call 0x7ee01d4e,[d2,d3,a2],32
    mov 1,d0                     # mode 1: load the card file
5:  movbu d0,(MODE)
    mov 1,d0
    movbu d0,(BUSY)
    mov 0x90,d0
    call 0x7e449541,[d2,d3],12   # OlyTaSt(USRTEST_A)
9:  mov d2,psw
    nop
    nop
    movm (sp),[d2,d3,other]
%(displaced)s
    jmp %(back)#x

"""

STRINGS = r"""
.section .tk,"ax"
    .balign 4
FLAGS: .byte 0, 0, 0, 0
PATH:  .asciz "C:\\EPM2LOOK.BIN"
RMODE: .asciz "r"
"""


def run(*a):
    return subprocess.run(a, check=True, capture_output=True, text=True).stdout


def block0(path):
    """Block 0's payload of a firmware file."""
    c = parse(open(path, "rb").read())
    return bytearray(c.blocks[0].payload)


def word(b, a):
    return struct.unpack_from("<I", b, a - BASE)[0]


def slot_ops(b, v2=False):
    """The operation list of each menu entry: (kind, [(offset, count, address, default)]).

    films-12d (v2 False): Grainy Film is the black-and-white slot. v2: twelve colour slots (mkspec_slots.LAYOUT)."""
    defaults = [word(b, slots.DEFAULT_RECORD + 4 * i) for i in range(slots.RECORD_TABLES)]
    colour = {s.entry: s for s in slots.SLOTS}
    extra = {s.entry: s.look for s in slots.EXTRA_SLOTS}
    # films-12d: Grainy Film holds the black-and-white film; Gentle Sepia stores Grainy Film's hidden value, so its
    # colour film uses the tables of the first extra slot (looks/films-12-bw.json, "moved_to")
    where = {**colour, "Gentle Sepia": extra["Grainy Film"], "Dramatic Tone": extra["Dramatic Tone"],
             "Key Line": extra["Key Line"], "Watercolor": extra["Watercolor"]}
    if v2:
        where.update({"Grainy Film": extra["Grainy Film"], "Gentle Sepia": extra["Gentle Sepia"]})
    out = []
    for entry in lookfile.MENU_ENTRIES:
        if entry == slots.MONO_SLOT.entry and not v2:
            grain = slots.MONO_SLOT.spare_tables[0][0]         # films12bw-doublex2 points the grain load at it
            assert word(b, slots.MONO_SLOT.grain_load + 2) == grain
            out.append((lookfile.KIND_MONO, [(46, 18, MONO_MATRIX, 0), (164, 512, grain, 0),
                                             (676, 512, slots.MONO_SLOT.live_look, 0)]))
            continue
        s = where[entry]
        ops = [(20, 2, s.saturation, 0), (20, 2, s.saturation + 2, 0), (22, 12, s.six_axis[0], 0),
               (34, 12, s.six_axis[1], 0), (46, 18, s.matrix, 0), (64, 97, s.chroma, 0)]
        for ch in range(3):
            src = 164 + ch * lookfile.CURVE_BYTES
            if isinstance(s.tone, slots.Tables):
                ops.append((src, 256, s.tone.addresses[ch], defaults[slots.STILLS_TABLE]))
            else:
                rec = s.tone.addresses[ch]
                ops += [(src, 256, word(b, rec + 4 * i), defaults[i]) for i in range(slots.RECORD_TABLES)]
        out.append((lookfile.KIND_COLOUR, ops))
    # no two operations write the same byte
    spans = sorted((a, a + (2 * n if d else n)) for _, ops in out for _, n, a, d in ops)
    for (a0, a1), (b0, b1) in zip(spans, spans[1:]):
        assert a1 <= b0, "operations overlap at %#x" % b0
    return out


def crc_table():
    t = []
    for n in range(16):
        c = n
        for _ in range(4):
            c = (c >> 1) ^ (0xEDB88320 if c & 1 else 0)
        t.append(c)
    return t


def model_verify(data, kinds):
    """VERIFY in Python, as the camera does it: True when the camera would take the file."""
    if len(data) < 32 or data[:4] != b"EPLK" or data[4] != 1 or data[6:8] != struct.pack("<H", 1708):
        return False
    count, length, crc = data[5], *struct.unpack_from("<II", data, 8)
    if length != len(data) or count > 12 or length != 32 + count * 1708 or data[16:20] != bytes.fromhex("01016001"):
        return False
    t, c = crc_table(), 0xFFFFFFFF
    for x in data[16:]:
        c ^= x
        c = (c >> 4) ^ t[c & 15]
        c = (c >> 4) ^ t[c & 15]
    if c ^ 0xFFFFFFFF != crc:
        return False
    assert crc == zlib.crc32(data[16:])
    seen = 0
    for r in range(count):
        slot, kind = data[32 + r * 1708], data[33 + r * 1708]
        if slot >= 12 or seen & (1 << slot) or kind != kinds[slot]:
            return False
        seen |= 1 << slot
    return True


def model_apply(b, data, table):
    """APPLY in Python, on a block-0 image."""
    for r in range(data[5]):
        rec = data[32 + r * 1708: 32 + (r + 1) * 1708]
        for off, n, addr, default in table[rec[0]][1]:
            if not default:
                b[addr - BASE: addr - BASE + n] = rec[off:off + n]
                continue
            v, i, p, out = struct.unpack_from("<H", rec, off)[0], 0, off + 2, []
            for k in range(n):
                target = struct.unpack_from("<H", b, default - BASE + 2 * k)[0]
                while i < target:
                    v += (rec[p] >> 4) if i & 1 else (rec[p] & 15)
                    p += i & 1
                    i += 1
                out.append(min(v, 1023))
            b[addr - BASE: addr - BASE + 2 * n] = struct.pack("<%dH" % n, *out)


def data_area(table):
    """The bytes of the two data areas: the slot table and the CRC table first, then the operation lists."""
    blobs = [struct.pack("<I", kind) + b"".join(struct.pack("<HHII", off, n, a, d) for off, n, a, d in ops)
             + bytes(4) for kind, ops in table]
    areas = [bytearray(), bytearray()]
    head = 48 + 64
    areas[0] += bytes(head)
    where = []
    for blob in sorted(range(12), key=lambda i: -len(blobs[i])):
        k = 0 if len(areas[0]) + len(blobs[blob]) <= DATA[0][1] - DATA[0][0] else 1
        where.append((blob, k, len(areas[k])))
        areas[k] += blobs[blob]
        assert len(areas[k]) <= DATA[k][1] - DATA[k][0], "the slot table does not fit"
    ptr = [0] * 12
    for blob, k, at in where:
        ptr[blob] = DATA[k][0] + at
    areas[0][:head] = struct.pack("<12I", *ptr) + struct.pack("<16I", *crc_table())
    return areas, DATA[0][0], DATA[0][0] + 48


def displaced(blk_path, site, n):
    """The replaced call at the hook site, by its target."""
    txt = run(BIN + "/mn10300-elf-objdump", "-D", "-b", "binary", "-m", "mn10300", "--adjust-vma=%#x" % BASE,
              "--start-address=%#x" % site, "--stop-address=%#x" % (site + n), blk_path)
    m = re.search(r"call\s+0x([0-9a-f]{8}),(\[[^\]]*\]),(\d+)", txt)
    assert m, txt
    return "    call 0x%s,%s,%s            # the replaced instruction" % m.groups()


def main():
    global SPEC
    v2 = "--v2" in sys.argv
    argv = [a for a in sys.argv[1:] if a != "--v2"]
    paths = RepoPaths(Path(ROOT))
    work = os.path.join(ROOT, "build", "card-looks")
    os.makedirs(work, exist_ok=True)
    if v2:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import mkspec_slots
        SPEC = "card-looks-2"
        base_specs = mkspec_slots.LAYOUT + ["patches/looks-menu.json"]
        fw = os.path.join(work, "base-2.BIN")
        subprocess.run(["uv", "run", "epm2mod", "apply", *base_specs, "--from", "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN", "-o", fw], cwd=ROOT, check=True,
                       capture_output=True)
        blk_name, delta_on = "base-2.block0.bin", "the specs of builds/card-looks-2.json before it"
    else:
        build = json.load(open(os.path.join(ROOT, BASE_BUILD)))
        base_specs = build["specs"]
        fw = os.path.join(ROOT, "build", "films-12d.BIN")
        assert hashlib.sha256(open(fw, "rb").read()).hexdigest() == build["sha256"], "epm2mod make films-12d first"
        blk_name, delta_on = "films-12d.block0.bin", BASE_BUILD
    b = block0(fw)
    blk_path = os.path.join(work, blk_name)
    open(blk_path, "wb").write(b)
    table = slot_ops(b, v2)
    kinds = [k for k, _ in table]

    # the model: the built-in looks give the bytes of the base; a file with other looks changes only slot tables
    items = json.load(open(paths.card_looks))["looks"]
    if not v2:      # films-12d: Double-X in its black-and-white slot (the fit with A, T, L)
        items = [dict(i, fit="looks/fits/doublex2.npz") if i["entry"] == "Grainy Film" else i for i in items]
    listing_json = os.path.join(work, "list-%s.json" % SPEC)
    json.dump({"looks": items}, open(listing_json, "w"))
    looks = lookpack.load_list(paths, Path(listing_json))
    data = lookfile.pack(looks)
    assert model_verify(data, kinds)
    same = bytearray(b)
    model_apply(same, data, table)
    assert same == b, "the built-in looks as a look file do not give the base's bytes"
    other = lookfile.pack([lookpack.look_of_fit(lookpack.load_fit(paths.resolve("looks/fits/c200.npz")), e, "C200",
                                                "c200") for e in lookfile.MENU_ENTRIES if v2 or e != "Grainy Film"])
    assert model_verify(other, kinds)
    changed = bytearray(b)
    model_apply(changed, other, table)
    spans = [(a, a + (2 * n if d else n)) for _, ops in table for _, n, a, d in ops]
    diff = [BASE + i for i in range(len(b)) if b[i] != changed[i]]
    assert diff and all(any(lo <= a < hi for lo, hi in spans) for a in diff)
    for bad in (data[:-1], data[:12] + b"\0" + data[13:], data[:32] + b"\x04" + data[33:]):
        assert not model_verify(bad, kinds)
    print("model: the built-in looks give the base's bytes; C200 in %d slots changes %d bytes, all in slot tables"
          % (len(other) // 1708, len(diff)))

    areas, slottab, crct = data_area(table)
    subs = {"store": STORE, "scratch": SCRATCH, "maxread": MAXREAD, "slottab": slottab, "crct": crct,
            "rw0": REFRESH_WORDS[0], "rw1": REFRESH_WORDS[1], "rb0": REFRESH_BYTES[0], "rb1": REFRESH_BYTES[1],
            "displaced": displaced(blk_path, HOOK[0], HOOK[1]), "back": HOOK[0] + HOOK[1]}
    asm = ASM.replace("%(gui)s", GUI_V2 if v2 else GUI_V1).replace("%(reset)s", "") % subs + STRINGS
    args = ["--defsym=s_%s=0x%s" % (x, x) for x in sorted(set(re.findall(r"(?:jmp|call)\s+0x([0-9a-f]{8})", asm)))]
    asm = re.sub(r"((?:jmp|call)\s+)0x([0-9a-f]{8})", r"\1s_\2", asm)
    asm += '\n.section .hs,"ax"\n    jmp T_GUI\n'
    args += ["--section-start=.hs=%#x" % HOOK[0]] + ["--section-start=%s=%#x" % (k, a) for k, (a, _) in RUNS.items()]
    s, o, e, sb = (os.path.join(work, "looks." + x) for x in ("s", "o", "elf", "bin"))
    open(s, "w").write(asm)
    run(BIN + "/mn10300-elf-as", "-o", o, s)
    run(BIN + "/mn10300-elf-ld", *args, "-e", "%#x" % RUNS[".tk"][0], "-o", e, o)
    syms = {m.group(2): int(m.group(1), 16) for m in
            re.finditer(r"^([0-9a-f]{8}) \w\s+\S+\s+\S+\s+(\w+)$", run(BIN + "/mn10300-elf-objdump", "-t", e), re.M)}

    def sect(name):
        run(BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", name, e, sb)
        return open(sb, "rb").read()

    stock = block0(os.path.join(ROOT, STOCK))
    ops = []

    def op(addr, new, note):
        expect = bytes(b[addr - BASE: addr - BASE + len(new)])
        assert expect != new, note
        ops.append({"type": "bytes", "block": 0, "offset": "0x%X" % (addr - BASE), "expect": expect.hex(),
                    "new": new.hex(), "_addr": "0x%08X" % addr, "_note": note})

    total = 0
    for name, (lo, hi) in RUNS.items():
        code = sect(name)
        assert lo + len(code) <= hi, "%s: %d B do not fit %d B" % (name, len(code), hi - lo)
        assert b[lo - BASE: hi - BASE] == stock[lo - BASE: hi - BASE], "%s: the run is in use" % name
        if code[-1] == b[lo - BASE + len(code) - 1]:
            code += b"\xcb"                      # the free-space ledger counts only changed bytes: end on a nop
        op(lo, code, "new code, segment 2 (%d B)" % len(code))
        total += len(code)
        print("%s: %3d B at %#x, %3d B free after" % (name, len(code), lo, hi - lo - len(code)))
    for k, blob in enumerate(areas):
        lo = DATA[k][0]
        assert b[lo - BASE: lo - BASE + len(blob)] == stock[lo - BASE: lo - BASE + len(blob)]
        op(lo, bytes(blob), "the slot table%s, segment 3 data (%d B)" % (
            " (12 pointers, the CRC-32 nibble table, operation lists)" if k == 0 else ": more operation lists",
            len(blob)))
        print("data %d: %4d B at %#x" % (k, len(blob), lo))
    h = sect(".hs")
    assert len(h) == HOOK[1] and h[0] == 0xDC and bytes(b[HOOK[0] - BASE: HOOK[0] - BASE + 5]) == HOOK[2]
    op(HOOK[0], h, "hook: jmp T_GUI. GUI state setter 0x7ECDF5E9, its last trace call (task CA_MAIN)")
    assert word(b, TASK_ENTRY) == TASK_ENTRY_STOCK
    op(TASK_ENTRY, struct.pack("<I", syms["T_TASK"]),
       "CPU0 task table, row of id 0x90 (USRTEST_A, dormant in stock): entry 0x7E501C5B -> T_TASK")
    print("code %d B; T_TASK %#x, T_GUI %#x" % (total, syms["T_TASK"], syms["T_GUI"]))
    keep = {k: syms[k] for k in ("T_TASK", "T_GUI", "T_STORED", "T_END", "SAVE", "V_OK", "V_BAD", "APPLY", "FLAGS")}
    json.dump({**keep, "STORE": STORE, "SCRATCH": SCRATCH}, open(os.path.join(work, "syms%s.json" % ("-2" if v2 else "")), "w"))
    json.dump([[a, 2 * n if d else n] for _, ops in table for _, n, a, d in ops],
              open(os.path.join(work, "spans%s.json" % ("-2" if v2 else "")), "w"))

    out = os.path.join(ROOT, "patches", SPEC + ".json")
    if not v2:      # the pinned spec: check that it is what this script makes; its notes (status) stay
        have = json.load(open(out))["ops"]
        assert have == ops, "patches/card-looks.json differs from what this script makes"
        print("patches/card-looks.json: unchanged (%d ops)" % len(ops))
    else:
        spec = {
            "name": SPEC,
            "description": (
                "Film looks loaded from the SD card with the menu row 'Load Looks', kept in the camera, for twelve "
                "colour slots (every art-filter entry takes any look). A look file C:\\EPM2LOOK.BIN "
                "(docs/look-file-format.md) holds up to 12 looks. When the GUI leaves the menu (not to power-off) "
                "with setting 449 (prm tag 0xD7B1, the row of patches/looks-menu.json) at Load (0) and the card is not "
                "being written, the dormant task USRTEST_A reads the file into the "
                "EEROM settings bank's unused tail (0x%08X), checks it (magic, version, lengths, CRC-32, camera and "
                "firmware, slots and kinds), copies it into the store at 0x%08X and, when a byte changed, calls the "
                "bank save API 0x7E680272. At every start (the first GUI state) and after a load the task checks the "
                "store and writes its looks into the slots' tables (both aliases): saturation pair, six-axis values, "
                "art matrix, chroma record, and each tone table made from the look's curve and the stock default "
                "table, as the film generator does. Then the look stages recompute (the boot init's refresh stores). "
                "Before the load, T_GUI sets setting 449 back to Off (1) with the GUI's setSetting 0x7EE01D4E, as the "
                "menu does; the firmware writes 1 into it at every start, so a camera shows Off. "
                "A bad file changes nothing; without a file the stored looks stay. The hook on the GUI state "
                "setter's trace call 0x7ECDF6E4, the task, the code runs and the data areas of "
                "patches/card-looks.json (camera-tested 2026-11-17), whose place it takes. Every expect is a byte "
                "string of %s. See experiments/2026-11-17-card-looks/design.md section 9.5." % (SCRATCH, STORE, delta_on)),
            "base": STOCK,
            "base_sha256": hashlib.sha256(open(os.path.join(ROOT, STOCK), "rb").read()).hexdigest(),
            "status": "candidate: emulator-checked, not flashed",
            "_ram": "the EEROM bank's unused tail: store 0x%08X-0x%08X, scratch 0x%08X-0x%08X (design.md section 3); "
                    "4 flag bytes in the spec's own code run (segment 2 is loaded again at every start)"
                    % (STORE, STORE + lookfile.MAX_FILE_BYTES, SCRATCH, SCRATCH + MAXREAD),
            "ops": ops,
        }
        with open(out, "w") as f:
            json.dump(spec, f, indent=1)
            f.write("\n")
        desc = {
            "what": "Film simulations in the twelve art filter entries, each of which takes any look; film looks "
                    "loaded from the SD card with the menu row Load Looks and kept in the camera; interval shooting "
                    "with up to 240 frames, a level gauge with calibration, and focus peaking",
            "specs": base_specs + ["patches/%s.json" % SPEC],
        }
        with open(os.path.join(ROOT, "builds", SPEC + ".json"), "w") as f:
            json.dump(desc, f, indent=1)
            f.write("\n")
        print("wrote patches/%s.json (%d ops) and builds/%s.json" % (SPEC, len(ops), SPEC))
    if argv:
        txt = run(BIN + "/mn10300-elf-objdump", "-d", *sum((["-j", k] for k in RUNS), []), "-j", ".hs", e)
        open(argv[0], "w").write(re.sub(r"/[^\s:]*looks\.elf", "looks.elf", txt))


if __name__ == "__main__":
    main()
