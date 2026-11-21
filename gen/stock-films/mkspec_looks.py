"""Write data/specs/card-looks.json and data/builds/card-looks.json: film looks loaded from the SD card and kept in the camera.

    uv run python experiments/2026-11-17-card-looks/scripts/mkspec_looks.py [--v2] [LISTING.txt]

--v2 writes data/specs/card-looks-2.json and data/builds/card-looks-2.json instead: the same loader for twelve colour slots
(mkspec_slots.LAYOUT, Grainy Film a colour slot) with the menu row of data/specs/looks-menu.json as its trigger: when the
GUI leaves the menu (not to power-off) with setting 449 at Load (0), T_GUI sets it back to Off (1) with the GUI's
setSetting, as the menu does, and starts the task in mode 1. The firmware writes 1 into the setting at every start, so
a camera shows Off. There is no load at the first menu.

Needs build/films-12d.BIN (uv run epm2mod make films-12d) and the toolchain (tools/setup.sh).
The design is design.md sections 2-5 and 9.3; the file format is docs/reference/look-file-format.md.

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

The script checks its own tables with a Python model of VERIFY and APPLY: the look file of data/films/card-looks.json
applied to films-12d leaves every byte as it is (the built-in looks are the same looks), and another file changes
only the slot tables.
"""

import json
import os
import re
import struct
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "cli", "src"))

from epm2mod.container import parse  # noqa: E402
from epm2mod.looks import lookfile, slots  # noqa: E402

BIN = os.path.join(ROOT, "build", "toolchain", "bin")
BASE = slots.BLOCK0_BASE
SPEC = "card-looks"
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"

# where the code goes: free runs of the segment-2 code areas (docs/reference/code-space-map.md; the runs of the persistence
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
STORE = 0x603F8000                                        # the stored look file, in the EEROM bank's unused tail
SCRATCH = 0x603FD040                                      # the file read from the card (uncached alias 0xA03FD040)
TAIL = (0x603F74B8, 0x60404668)                           # the unused tail (design.md section 3)
MAXREAD = lookfile.MAX_FILE_BYTES + 4                     # a longer file is read short and refused
REFRESH_WORDS = (0xA07500B4, 0xA07500B8)                  # the IMG library's builder words: 0 = clear the stage cache
REFRESH_BYTES = (0x60510CD5, 0x60511305)                  # the gamma states' art-code bytes: 0xFF = rebuild
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


def crc_table():
    t = []
    for n in range(16):
        c = n
        for _ in range(4):
            c = (c >> 1) ^ (0xEDB88320 if c & 1 else 0)
        t.append(c)
    return t


def displaced(blk_path, site, n):
    """The replaced call at the hook site, by its target."""
    txt = run(BIN + "/mn10300-elf-objdump", "-D", "-b", "binary", "-m", "mn10300", "--adjust-vma=%#x" % BASE,
              "--start-address=%#x" % site, "--stop-address=%#x" % (site + n), blk_path)
    m = re.search(r"call\s+0x([0-9a-f]{8}),(\[[^\]]*\]),(\d+)", txt)
    assert m, txt
    return "    call 0x%s,%s,%s            # the replaced instruction" % m.groups()
