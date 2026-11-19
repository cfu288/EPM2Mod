"""Write patches/card-looks-3.json and builds/card-looks-3.json: the looks loader for the acceptance criteria of
design.md section 10.

    uv run python experiments/2026-11-17-card-looks/scripts/mkspec_looks3.py [LISTING.txt]

On top of the loader of card-looks-2 (the card file, its checks, the store in the EEROM tail, APPLY):
  * names (criterion 5): the menu shows a loaded look's name. The loaded language's text table is in RAM (blob at
    0xBFF3D000, its pointer array at the address in its first word); each of the 30 string ids that show an entry's
    name is pointed at a copy of the language's string with the look's name after the icon tag (@A043@ ...).
    After a language change (the table is loaded again) T_GUI sees that the row's label is not ours and runs the
    task in mode 3, which writes the texts and names again.
  * the row (criterion 6, 10): Load Looks / Load / Built-in / the help, in every language; when the row is Off it
    shows the result of the last action (text 1495): the language's "Off", Loaded, No file, Bad file, Built-in.
  * Built-in (criterion 7): at the first GUI state the task keeps a copy of every table a look writes (the built-in
    looks); Built-in empties the store, saves the bank and copies the built-in tables back; a load also starts from
    them, so the entries a file does not list have their built-in look.
  * live view (criterion 8): the ten slots with three tables get member-0 tables (live view) of their own, made from
    the slot's stills table and the stock member-0 defaults (an interpolation; exact within 7 of 1023 for the
    fits), for the built-in looks too; their three records point at them.
  * trigger: at every GUI state call (also in the menu, so the row changes at the next key), except power-off:
    setting 449 at Load (0) -> mode 1 (when the card is not being written), at Built-in (2) -> mode 2; T_GUI sets the
    row back to Off (1) with the GUI's setSetting first.
RAM: the gap 0x7E4D0000-0x7E4F0000 (block-0 bytes that no load or clear touches; the debug log's ring is at
0x7E4F9000; zero through a session in the emulator), and the EEROM tail as before. Code: the runs of card-looks-2 and
a reclaimed code area of segment 3 (0x7EE53830: first code there; this build's flash is its test).
"""

import hashlib
import json
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import mkspec_looks as mk  # noqa: E402
import mkspec_slots  # noqa: E402
from epm2mod.container import parse  # noqa: E402
from epm2mod.looks import lookfile, lookpack, slots  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

V4 = "--v4" in sys.argv          # card-looks-4: the Custom Menu of patches/custom-menu-rows.json (an added row)
SPEC = "card-looks-4" if V4 else "card-looks-3"
MENU_SPEC = "patches/looks-menu-3.json" if V4 else "patches/looks-menu-2.json"
BASE = mk.BASE
BIN = mk.BIN
RUNS = dict(mk.RUNS)
RUNS[".x1"] = (0x7EE53830, 0x7EE53D6A)       # segment 3, reclaim-space row 5 (code, checked): first code
if V4:
    RUNS[".tb"] = (0x7EBF2890, 0x7EBF2900)   # the child list of custom-menu-rows ends at 0x7EBF2890
DATA = [mk.DATA[0], (mk.DATA[1][0], mk.DATA[1][1])]
LANG = 0xBFF3D000           # the loaded language's blob; its first word: the address of its pointer array
LANG_SPAN = 0x43000
T_LABEL, T_LOAD, T_HELP, T_BUILTIN, T_STATUS, T_OFF = 1498, 1496, 1497, 1503, 1495, 1371
RAM = 0x7E4D0000            # the RAM gap (cached address); the code uses the uncached alias
RAM_END = 0x7E4F0000
ENGLISH = (0x38B758, 0xBFBC4E20)   # pointer array of the English blob in block 1, and its load bias

# English texts of block 1 by id (stock firmware), to find the ids that show an entry's name
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"


def stock_texts():
    b1 = parse(open(os.path.join(ROOT, STOCK), "rb").read()).blocks[1].payload
    out = []
    for i in range(1970):
        p = struct.unpack_from("<I", b1, ENGLISH[0] + 4 * i)[0] - ENGLISH[1]
        e = p
        while b1[e:e + 2] != b"\0\0":
            e += 2
        out.append(b1[p:e].decode("utf-16-le"))
    return out


def name_ids():
    """For each menu entry, the ids whose stock English text is the entry's name, with or without an icon tag."""
    texts = stock_texts()
    ids = []
    for entry in lookfile.MENU_ENTRIES:
        found = [i for i, t in enumerate(texts) if re.sub(r"^@[^@]*@", "", t) == entry]
        assert 2 <= len(found) <= 3, (entry, found)
        ids.append(found)
    return ids


def live_records(b):
    """For each slot, the three tone records (cached addresses) whose member 1 is the slot's stills table; 0 for the
    two slots with records of their own (all eight tables of a record are written by APPLY already)."""
    w = lambda a: struct.unpack_from("<I", b, a - BASE)[0]
    where = {s.entry: s for s in slots.SLOTS}
    extra = {s.entry: s.look for s in slots.EXTRA_SLOTS}
    where.update({e: extra[e] for e in ("Grainy Film", "Gentle Sepia", "Dramatic Tone", "Key Line", "Watercolor")})
    out = []
    for entry in lookfile.MENU_ENTRIES:
        s = where[entry]
        if not isinstance(s.tone, slots.Tables):
            out.append([0, 0, 0])
            continue
        recs = []
        for t in s.tone.addresses:
            hits = [BASE + i for i in range(0, len(b) - 32, 4) if b[i:i + 4] == struct.pack("<I", t)]
            cand = [h - 4 for h in hits if all(w(h - 4 + 4 * k) == t for k in (1, 3, 5, 7))]
            assert len(cand) == 1, (entry, hex(t), [hex(c) for c in cand])
            recs.append(cand[0])
        out.append(recs)
    return out


def interp(t1, d1, d0):
    """INTERP in Python: the member-0 table from the stills table t1 (made at the default d1) and the default d0."""
    out, j = [], 0
    for x in d0:
        while j < 255 and d1[j + 1] <= x:
            j += 1
        if j == 255 or x <= d1[j]:
            out.append(t1[j])
        else:
            dx = d1[j + 1] - d1[j]
            out.append(t1[j] + ((t1[j + 1] - t1[j]) * (x - d1[j]) + dx // 2) // dx)
    return out


def u16s(s):
    return s.encode("utf-16-le") + b"\0\0"


ASM_HEAD = r"""
.equ MAGIC,    0x4b4c5045        # "EPLK"
.equ STORE,    %(store)#x        # the stored look file (cached address)
.equ SCRU,     %(scratch)#x + 0x40000000
.equ MAXREAD,  %(maxread)d
.equ SLOTTAB,  %(slottab)#x
.equ CRCT,     %(crct)#x
.equ NAMEIDS,  %(nameids)#x      # 36 u16: three string ids per slot (0: none)
.equ LIVEREC,  %(liverec)#x      # 36 u32: three tone records per slot (0: none)
.equ TXTTAB,   %(txttab)#x       # 4 x {u16 id, u16 0, u32 text}: the row's texts
.equ TXT_LABEL, %(txt_label)#x
.equ S_LOADED, %(s_loaded)#x
.equ S_NOFILE, %(s_nofile)#x
.equ S_BAD,    %(s_bad)#x
.equ S_BUILTIN, %(s_builtin)#x
.equ S_WORK,   %(s_work)#x
.equ DEFREC,   %(defrec)#x       # the stock default tone record: 4 columns x (member 0, member 1)
.equ LANG,     %(lang)#x         # word: the pointer array of the loaded language
.equ RAMU,     %(ram)#x + 0x40000000
.equ RSTAT,    RAMU              # u32: the status text (0: the language's Off)
.equ RORIG,    RAMU + 0x10       # 36 u32: the language's own strings of the name ids
.equ RNAMES,   RAMU + 0x100      # 36 x 48 B: the names
.equ RSNAP,    RAMU + 0x800      # the built-in tables, %(snapn)d B
.equ RLIVE,    %(rlive)#x        # 36 x 4 x 512 B: member-0 tables (cached address: records hold cached addresses)
.equ FLAGS_U,  FLAGS + 0x40000000
.equ BUSY,     FLAGS_U           # the task runs
.equ APPLIED,  FLAGS_U + 1       # mode 0 was started in this session
.equ STOREOK,  FLAGS_U + 2       # the store held a valid look file at the last check
.equ MODE,     FLAGS_U + 3       # 0 start, 1 load, 2 built-in, 3 texts and names

.section .tk,"ax"
T_GUI:                           # the "state =" trace call of the GUI state setter, d0 = state (task CA_MAIN); the
    movm [d2,d3,other],(sp)      # GUI calls it at every key, also when the state stays the same
    mov psw,d2
    mov d0,d3
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
    lsr 12,d0
    cmp 2,d0                     # 0x2xxx: power off, sleep
    beq 9f
    mov (LANG),a0                # a language table that does not have our texts yet: mode 3
    mov a0,d0
    add %(lang_neg)#x,d0
    cmp %(lang_span)#x,d0
    bcc 9f                       # no language table yet: nothing now
    mov (%(label_off)d,a0),d0
    cmp TXT_LABEL,d0
    beq 2f
    mov 3,d0
    bra 5f
2:  mov 0xd7b1,d0                # setting 449, the row Load Looks: 1 Off, 0 Load, 2 Built-in
    mov 0,a0
    clr d1
    call 0x7e457c75,[d2,d3],12   # prm_get(tag, 0, 0)
    cmp 2,d0
    beq 3f
    cmp 0,d0
    bne 9f
    call 0x7ecd360a,[d2],8       # the GUI's isMediaWriting(): 1 while the card is written
    cmp 0,d0
    bne 9f
    mov 1,d0
3:  movbu d0,(MODE)              # 1 load, 2 built-in
    mov 449,d0                   # the row back to Off, as the menu sets a value: setSetting(449, 1)
    mov 1,d1
    call 0x7ee01d4e,[d2,d3,a2],32
    mov (LANG),a0                # the row shows "Loading" until the task's result
    mov S_WORK,d0
    mov d0,(%(status_off)d,a0)
    bra 6f
5:  movbu d0,(MODE)
6:  mov 1,d0
    movbu d0,(BUSY)
    mov 0x90,d0
    call 0x7e449541,[d2,d3],12   # OlyTaSt(USRTEST_A)
9:  mov d2,psw
    nop
    nop
    movm (sp),[d2,d3,other]
%(displaced)s
    jmp %(back)#x
    .balign 4
FLAGS: .byte 0, 0, 0, 0
PATH:  .asciz "C:\\EPM2LOOK.BIN"
RMODE: .asciz "r"

.section .x1,"ax"
T_TASK:                          # task USRTEST_A (id 0x90), started by T_GUI; it ends when it returns
    movm [d2,d3,a2,a3],(sp)
    add -32,sp                   # (0,sp) is the return slot of every call: no locals here
    movbu (MODE),d0
    cmp 3,d0
    beq T_NAMES
    cmp 2,d0
    beq T_BUILT
    cmp 0,d0
    bne T_LOAD
    clr d0                       # mode 0: keep the built-in tables before anything changes them
    calls COPYALL
    clr d0
    mov d0,(RSTAT)
    bra T_STORED
T_LOAD:
    mov PATH,a0
    mov RMODE,a1
    call 0x7e5c52dc,[],20        # fileif_fopen(path, "r") -> a0 = handle or 0
    mov a0,a3
    mov S_NOFILE,d0
    cmp 0,a3
    beq 8f
    mov SCRU,a0
    mov 1,d0
    mov MAXREAD,d1
    mov a3,a1
    call 0x7e5c536f,[],24        # fileif_fread -> bytes read
    mov d0,d2
    mov a3,a0
    call 0x7e5c5308,[],12        # fileif_fclose
    mov SCRU,a0
    mov d2,d0
    calls VERIFY
    cmp 0,d0
    mov S_BAD,d0
    bne 8f
    jmp T_KEEP                   # store it, save the bank; back at T_LOADED
8:  mov d0,(RSTAT)               # nothing changes but the status
    bra T_NAMES
T_LOADED:
    mov S_LOADED,d0
    mov d0,(RSTAT)
    bra 7f
T_BUILT:                         # mode 2: the store is no longer a look file; the built-in tables back
    clr d0
    mov d0,(STORE)
    mov d0,(STORE + 0x40000000)
    call 0x7e680272,[],48        # the bank save API
    mov S_BUILTIN,d0
    mov d0,(RSTAT)
7:  mov 1,d0                     # the built-in tables back (a load starts from them)
    calls COPYALL
T_STORED:
    mov STORE,a0
    mov (8,a0),d0
    calls VERIFY
    movbu d0,(STOREOK)           # 0 valid: reversed below
    cmp 0,d0
    bne 1f
    mov 1,d0
    movbu d0,(STOREOK)
    mov STORE,a0
    calls APPLY
    bra 2f
1:  clr d0
    movbu d0,(STOREOK)
2:  calls LIVE
    clr d0                       # make the look stages recompute, as the boot init 0x7E560AC0 does
    mov d0,(%(rw0)#x)
    mov d0,(%(rw1)#x)
    mov 0xff,d0
    movbu d0,(%(rb0)#x)
    movbu d0,(%(rb1)#x)
T_NAMES:
    calls NAMES
T_END:
    clr d0
    movbu d0,(BUSY)
    ret [d2,d3,a2,a3],48

COPYALL:                         # d0 = 0: every table of every slot -> RSNAP; 1: RSNAP -> the tables (both aliases)
    movm [d2,d3,a2,a3],(sp)
    add -8,sp
    mov d0,(4,sp)
    mov RSNAP,a3
    clr d3
1:  mov d3,d0
    asl2 d0
    mov SLOTTAB,a2
    mov (d0,a2),a2
    add 4,a2
2:  mov (a2),d0
    cmp 0,d0
    beq 6f
    lsr 16,d0
    mov (8,a2),d1
    cmp 0,d1
    beq 3f
    add d0,d0                    # a tone table: 2 bytes an entry
3:  mov (4,a2),a1
    mov (4,sp),d1
    cmp 0,d1
    bne 4f
5:  movbu (0x40000000,a1),d1
    movbu d1,(a3)
    inc a1
    inc a3
    add -1,d0
    bne 5b
    bra 7f
4:  movbu (a3),d1
    movbu d1,(a1)
    movbu d1,(0x40000000,a1)
    inc a1
    inc a3
    add -1,d0
    bne 4b
7:  add 12,a2
    bra 2b
6:  inc d3
    cmp 12,d3
    bne 1b
    add 8,sp
    movm (sp),[d2,d3,a2,a3]
    rets

NAMES:                           # the row's texts and the entries' names in the loaded language's table
    movm [d2,d3,a2,a3],(sp)
    add -20,sp
    mov (LANG),a2
    mov a2,d0
    add %(lang_neg)#x,d0
    cmp %(lang_span)#x,d0
    bcc N_END
    mov (%(label_off)d,a2),d0
    cmp TXT_LABEL,d0
    beq 2f
    mov NAMEIDS,a0               # a fresh table: keep its strings of the name ids, put in the row's texts
    mov RORIG,a1
    mov 36,d3
1:  movhu (a0),d0
    asl2 d0
    mov (d0,a2),d1
    mov d1,(a1)
    add 2,a0
    add 4,a1
    add -1,d3
    bne 1b
    mov TXTTAB,a0
    mov 4,d3
3:  movhu (a0),d0
    asl2 d0
    mov (4,a0),d1
    mov d1,(d0,a2)
    add 8,a0
    add -1,d3
    bne 3b
2:  mov (RSTAT),d1               # the status (0: the language's own "Off")
    cmp 0,d1
    bne 4f
    mov (%(off_off)d,a2),d1
4:  mov d1,(%(status_off)d,a2)
    mov NAMEIDS,a0               # every name id back to the language's string
    mov RORIG,a1
    mov 36,d3
5:  movhu (a0),d0
    cmp 0,d0
    beq 6f
    asl2 d0
    mov (a1),d1
    mov d1,(d0,a2)
6:  add 2,a0
    add 4,a1
    add -1,d3
    bne 5b
    jmp N_LOOKS
N_END:
    add 20,sp
    movm (sp),[d2,d3,a2,a3]
    rets

N_LOOKS:                         # the stored looks' names
    movbu (STOREOK),d0
    cmp 0,d0
    beq N_END
    mov STORE,a3
    movbu (5,a3),d0
    mov d0,(4,sp)                # records left
    add 32,a3
7:  mov (4,sp),d0
    cmp 0,d0
    beq N_END
    add -1,d0
    mov d0,(4,sp)
    movbu (4,a3),d0
    cmp 0,d0
    beq 12f                      # no name: the entry keeps the language's
    movbu (a3),d0
    mov d0,d1
    add d0,d0
    add d1,d0
    mov d0,(8,sp)                # i = slot x 3
    mov 3,d0
    mov d0,(12,sp)
8:  mov (8,sp),d0
    mov NAMEIDS,a0
    add d0,a0
    add d0,a0
    movhu (a0),d1
    cmp 0,d1
    beq 11f
    asl2 d1
    mov d1,(16,sp)               # id x 4
    mov d0,d2                    # d2 = i x 48
    asl 4,d2
    mov d2,d1
    add d2,d2
    add d1,d2
    mov RNAMES,a0
    add d2,a0
    asl2 d0
    mov RORIG,a1
    add d0,a1
    mov (a1),a1                  # the language's string
    movhu (a1),d0
    cmp 0x40,d0                  # an icon tag "@...@" first: copy it
    bne 10f
9:  movhu (a1),d0
    movhu d0,(a0)
    add 2,a1
    add 2,a0
    movhu (a1),d0
    cmp 0x40,d0
    bne 9b
    movhu d0,(a0)
    add 2,a0
10: mov a3,a1                    # the name: up to 16 ASCII bytes
    add 4,a1
    mov 16,d3
13: movbu (a1),d0
    cmp 0,d0
    beq 14f
    movhu d0,(a0)
    add 2,a0
    inc a1
    add -1,d3
    bne 13b
14: clr d0
    movhu d0,(a0)
    mov RNAMES,d0                # the id shows it
    add d2,d0
    mov (16,sp),d1
    mov d0,(d1,a2)
11: mov (8,sp),d0
    inc d0
    mov d0,(8,sp)
    mov (12,sp),d0
    add -1,d0
    mov d0,(12,sp)
    bne 8b
12: add 1708,a3
    bra 7b

LIVE:                            # member-0 tables (live view) of the slots with three tables
    movm [d2,d3,a2,a3],(sp)
    add -24,sp
    clr d0
    mov d0,(4,sp)                # i = slot x 3 + channel
1:  mov (4,sp),d0
    asl2 d0
    mov LIVEREC,a0
    mov (d0,a0),a3
    cmp 0,a3
    beq 5f
    clr d0
    mov d0,(8,sp)                # m: the column
2:  mov (4,sp),d0
    asl2 d0
    mov (8,sp),d1
    add d1,d0
    asl 9,d0
    add RLIVE,d0
    mov d0,(12,sp)               # the new table
    asl 3,d1
    mov d1,(16,sp)               # the record's member-0 entry of column m
    mov DEFREC,a0
    mov (d1,a0),a2               # the stock member-0 default of column m
    mov (4,a3),a0                # the stills table
    mov (DEFREC + 4),a1          # the stock stills default
    calls INTERP
    mov (16,sp),d1
    mov (12,sp),d0
    mov d0,(d1,a3)
    mov a3,a0
    add 0x40000000,a0
    mov d0,(d1,a0)
    mov (8,sp),d0
    inc d0
    mov d0,(8,sp)
    cmp 4,d0
    bne 2b
5:  mov (4,sp),d0
    inc d0
    mov d0,(4,sp)
    cmp 36,d0
    bne 1b
    add 24,sp
    movm (sp),[d2,d3,a2,a3]
    rets

INTERP:                          # a0 = stills table t1, a1 = its default d1, a2 = a default d0, d0 = the new table:
    movm [d2,d3,a2,a3],(sp)      # entry k = t1 read at d0[k] on the axis d1 (linear, rounded)
    add -16,sp
    mov d0,a3
    mov 255,d3
    mov 256,d0
    mov d0,(4,sp)
1:  movhu (a2),d0                # x
2:  cmp 0,d3
    beq 4f
    movhu (2,a1),d1
    cmp d1,d0
    bcs 3f                       # x < d1[j + 1]
    add 2,a1
    add 2,a0
    add -1,d3
    bra 2b
3:  movhu (a1),d1
    cmp d1,d0
    bls 4f                       # x <= d1[j]: t1[j]
    sub d1,d0
    movhu (2,a1),d2
    sub d1,d2
    mov d2,(8,sp)                # dx
    movhu (2,a0),d1
    movhu (a0),d2
    sub d2,d1                    # dy
    mul d1,d0
    mov (8,sp),d1
    mov d1,d2
    lsr 1,d2
    add d2,d0
    clr d2
    mov d2,mdr
    divu d1,d0
    movhu (a0),d2
    add d2,d0
    bra 5f
4:  movhu (a0),d0
5:  movhu d0,(a3)
    movhu d0,(0x40000000,a3)
    add 2,a3
    add 2,a2
    mov (4,sp),d0
    add -1,d0
    mov d0,(4,sp)
    bne 1b
    add 16,sp
    movm (sp),[d2,d3,a2,a3]
    rets

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
    beq 3f
SAVE:
    call 0x7e680272,[],48        # the bank save API: the changed bank goes to flash now
3:  jmp T_LOADED
"""


def tail_asm():
    """VERIFY, V_REC, APPLY, A_TONE, A_PUT of the card-looks-2 loader (mkspec_looks.ASM), unchanged."""
    s = mk.ASM
    return s[s.index('.section .vf,"ax"'):]


def main():
    paths = RepoPaths(Path(ROOT))
    work = os.path.join(ROOT, "build", "card-looks")
    os.makedirs(work, exist_ok=True)
    base_specs = (mkspec_slots.LAYOUT4 if V4 else mkspec_slots.LAYOUT) + [MENU_SPEC]
    fw = os.path.join(work, "base-%s.BIN" % ("4" if V4 else "3"))
    subprocess.run(["uv", "run", "epm2mod", "apply", *base_specs, "--from", "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN", "-o", fw], cwd=ROOT, check=True,
                   capture_output=True)
    b = mk.block0(fw)
    blk_path = os.path.join(work, "base-%s.block0.bin" % ("4" if V4 else "3"))
    open(blk_path, "wb").write(b)
    table = mk.slot_ops(b, True)
    kinds = [k for k, _ in table]
    spans = [(a, 2 * n if d else n) for _, ops in table for _, n, a, d in ops]
    snapn = sum(n for _, n in spans)
    ids = name_ids()
    recs = live_records(b)
    rlive = (RAM + 0x800 + snapn + 0xFFF) & ~0xFFF
    assert rlive + 36 * 4 * 512 <= RAM_END, hex(rlive + 36 * 4 * 512)

    # the model: the built-in looks give the base's bytes; the live tables are within 7 codes of exact
    looks = lookpack.load_list(paths, paths.card_looks)
    data = lookfile.pack(looks)
    assert mk.model_verify(data, kinds)
    same = bytearray(b)
    mk.model_apply(same, data, table)
    assert same == b
    w = lambda a: struct.unpack_from("<I", b, a - BASE)[0]
    tbl = lambda a: list(struct.unpack_from("<256H", b, a - BASE))
    dr = [w(slots.DEFAULT_RECORD + 4 * i) for i in range(8)]
    worst = 0
    for s, look in enumerate(looks):
        for ch, rec in enumerate(recs[s]):
            if not rec:
                continue
            t1 = tbl(w(rec + 4))
            for m in range(4):
                approx = interp(t1, tbl(dr[1]), tbl(dr[2 * m]))
                exact, top = [], 0
                for x in tbl(dr[2 * m]):
                    top = max(top, look.curves[ch][min(x, 1023)])
                    exact.append(top)
                worst = max(worst, max(abs(p - q) for p, q in zip(approx, exact)))
    assert worst <= 8, worst
    print("model: built-in looks give the base's bytes; live tables within %d codes of exact; snapshot %d B" % (
        worst, snapn))

    # data: the slot table (as card-looks-2) and, after it in the second area, the tables of this loader
    areas, slottab, crct = mk.data_area(table)
    d1 = DATA[1][0] + len(areas[1])
    d1 = (d1 + 3) & ~3
    extra = bytearray()
    at = lambda: d1 + len(extra)
    pad = lambda: extra.extend(bytes(-len(extra) % 4))
    nameids = at()
    for s in range(12):
        extra += struct.pack("<3H", *(ids[s] + [0] * (3 - len(ids[s]))))
    pad()
    liverec = at()
    for s in range(12):
        extra += struct.pack("<3I", *recs[s])
    strings = {}
    for key, text in (("label", "Load Looks"), ("load", "Load"),
                      ("help", "Load film looks from\r\nEPM2LOOK.BIN on the card."), ("builtin", "Built-in"),
                      ("loaded", "Loaded"), ("nofile", "No file"), ("bad", "Bad file"), ("work", "Loading")):
        pad()
        strings[key] = at()
        extra += u16s(text)
    pad()
    txttab = at()
    for tid, key in ((T_LABEL, "label"), (T_LOAD, "load"), (T_HELP, "help"), (T_BUILTIN, "builtin")):
        extra += struct.pack("<HHI", tid, 0, strings[key])
    areas[1] = bytes(areas[1]) + bytes(d1 - DATA[1][0] - len(areas[1])) + bytes(extra)
    assert DATA[1][0] + len(areas[1]) <= DATA[1][1], "the data do not fit"

    subs = {"store": mk.STORE, "scratch": mk.SCRATCH, "maxread": mk.MAXREAD, "slottab": slottab, "crct": crct,
            "nameids": nameids, "liverec": liverec, "txttab": txttab, "txt_label": strings["label"],
            "s_loaded": strings["loaded"], "s_nofile": strings["nofile"], "s_bad": strings["bad"],
            "s_builtin": strings["builtin"], "s_work": strings["work"], "defrec": slots.DEFAULT_RECORD, "lang": LANG,
            "lang_neg": (-LANG) & 0xFFFFFFFF, "lang_span": LANG_SPAN, "label_off": 4 * T_LABEL,
            "off_off": 4 * T_OFF, "status_off": 4 * T_STATUS, "ram": RAM, "snapn": snapn, "rlive": rlive,
            "rw0": mk.REFRESH_WORDS[0], "rw1": mk.REFRESH_WORDS[1], "rb0": mk.REFRESH_BYTES[0],
            "rb1": mk.REFRESH_BYTES[1], "displaced": mk.displaced(blk_path, mk.HOOK[0], mk.HOOK[1]),
            "back": mk.HOOK[0] + mk.HOOK[1]}
    asm = ASM_HEAD % subs + tail_asm() % subs
    args = ["--defsym=s_%s=0x%s" % (x, x) for x in sorted(set(re.findall(r"(?:jmp|call)\s+0x([0-9a-f]{8})", asm)))]
    asm = re.sub(r"((?:jmp|call)\s+)0x([0-9a-f]{8})", r"\1s_\2", asm)
    asm += '\n.section .hs,"ax"\n    jmp T_GUI\n'
    args += ["--section-start=.hs=%#x" % mk.HOOK[0]] + ["--section-start=%s=%#x" % (k, a) for k, (a, _) in RUNS.items()]
    s, o, e, sb = (os.path.join(work, "looks3." + x) for x in ("s", "o", "elf", "bin"))
    open(s, "w").write(asm)
    mk.run(BIN + "/mn10300-elf-as", "-o", o, s)
    mk.run(BIN + "/mn10300-elf-ld", *args, "-e", "%#x" % RUNS[".x1"][0], "-o", e, o)
    syms = {m.group(2): int(m.group(1), 16) for m in
            re.finditer(r"^([0-9a-f]{8}) \w\s+\S+\s+\S+\s+(\w+)$", mk.run(BIN + "/mn10300-elf-objdump", "-t", e), re.M)}

    def sect(name):
        mk.run(BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", name, e, sb)
        return open(sb, "rb").read()

    stock = mk.block0(os.path.join(ROOT, STOCK))
    ops = []

    def op(addr, new, note):
        expect = bytes(b[addr - BASE: addr - BASE + len(new)])
        assert expect != new, note
        ops.append({"type": "bytes", "block": 0, "offset": "0x%X" % (addr - BASE), "expect": expect.hex(),
                    "new": new.hex(), "_addr": "0x%08X" % addr, "_note": note})

    total = 0
    for name, (lo, hi) in RUNS.items():
        code = sect(name)
        if not code:
            continue
        assert lo + len(code) <= hi, "%s: %d B do not fit %d B" % (name, len(code), hi - lo)
        assert b[lo - BASE: hi - BASE] == stock[lo - BASE: hi - BASE], "%s: the run is in use" % name
        if code[-1] == b[lo - BASE + len(code) - 1]:
            code += b"\xcb"
        op(lo, code, "new code, %s (%d B)" % ("segment 3, reclaimed code area: first code" if name == ".x1"
                                             else "segment 2", len(code)))
        total += len(code)
        print("%s: %4d B at %#x, %4d B free after" % (name, len(code), lo, hi - lo - len(code)))
    for k, blob in enumerate(areas):
        lo = DATA[k][0]
        assert b[lo - BASE: lo - BASE + len(blob)] == stock[lo - BASE: lo - BASE + len(blob)]
        op(lo, bytes(blob), "data, segment 3 (%d B): %s" % (len(blob), "the slot table (12 pointers, the CRC-32 "
           "nibble table, operation lists)" if k == 0 else "operation lists, name ids, tone records, texts"))
        print("data %d: %4d B at %#x" % (k, len(blob), lo))
    h = sect(".hs")
    assert len(h) == mk.HOOK[1] and h[0] == 0xDC and bytes(b[mk.HOOK[0] - BASE: mk.HOOK[0] - BASE + 5]) == mk.HOOK[2]
    op(mk.HOOK[0], h, "hook: jmp T_GUI. GUI state setter 0x7ECDF5E9, its last trace call (task CA_MAIN)")
    assert mk.word(b, mk.TASK_ENTRY) == mk.TASK_ENTRY_STOCK
    op(mk.TASK_ENTRY, struct.pack("<I", syms["T_TASK"]),
       "CPU0 task table, row of id 0x90 (USRTEST_A, dormant in stock): entry 0x7E501C5B -> T_TASK")
    prio = mk.TASK_ENTRY + 4
    assert b[prio - BASE: prio - BASE + 4] == struct.pack("<I", 11)
    op(prio, b"\x0d", "CPU0 task table, row of id 0x90 (USRTEST_A): priority 11 -> 13, the lowest that stock tasks "
       "use (one does; 91 have 11): the start-up work of the loader (the built-in tables, the live tables) waits for "
       "the firmware's own tasks")
    print("code %d B; T_TASK %#x, T_GUI %#x; RAM: snapshot %#x-%#x, live tables %#x-%#x" % (
        total, syms["T_TASK"], syms["T_GUI"], RAM + 0x800, RAM + 0x800 + snapn, rlive, rlive + 36 * 4 * 512))
    keep = {k: syms[k] for k in ("T_TASK", "T_GUI", "T_STORED", "T_END", "SAVE", "V_OK", "V_BAD", "APPLY", "FLAGS",
                                 "NAMES", "LIVE", "COPYALL")}
    json.dump({**keep, "STORE": mk.STORE, "SCRATCH": mk.SCRATCH, "RAM": RAM, "RLIVE": rlive, "SNAPN": snapn,
               "IDS": ids, "RECS": recs, "STRINGS": strings}, open(os.path.join(work, "syms-%s.json" % ("4" if V4 else "3")), "w"))
    json.dump([[a, n] for a, n in spans], open(os.path.join(work, "spans-%s.json" % ("4" if V4 else "3")), "w"))

    spec = {
        "name": SPEC,
        "description": (
            "Film looks loaded from the SD card with the menu row 'Load Looks' (patches/looks-menu-2.json), kept in "
            "the camera, for twelve colour slots. Load (setting 449 = 0) reads C:\\\\EPM2LOOK.BIN into the EEROM "
            "bank's unused tail, checks it (magic, version, lengths, CRC-32, camera and firmware, slots and kinds), "
            "keeps it in the store at 0x%08X (bank save when a byte changed), puts back the built-in tables and "
            "applies its looks: every table of each listed entry, the names of the looks in the menu (the string ids "
            "of each entry in the loaded language's table in RAM), and member-0 tables (live view) for the ten "
            "slots with three tables. Built-in (2) empties the store and puts back the built-in tables, kept at the "
            "first GUI state of the session in RAM 0x7E4D0800. When Off the row shows the result: Off, Loaded, No "
            "file, Bad file, Built-in. The row's texts are written into every language's table. Every start applies "
            "the stored looks. The hook on the GUI state setter's trace call 0x7ECDF6E4, the task USRTEST_A, the "
            "code runs of card-looks-2 and new code in the reclaimed code area 0x7EE53830 of segment 3. Every "
            "expect is a byte string of the specs of builds/card-looks-3.json before it. See "
            "experiments/2026-11-17-card-looks/design.md section 10." % mk.STORE).replace(
            "patches/looks-menu-2.json", MENU_SPEC).replace("builds/card-looks-3.json", "builds/%s.json" % SPEC),
        "base": STOCK,
        "base_sha256": hashlib.sha256(open(os.path.join(ROOT, STOCK), "rb").read()).hexdigest(),
        "status": "candidate: emulator-checked, not flashed",
        "_ram": "the EEROM bank's unused tail: store 0x%08X, scratch 0x%08X; the RAM gap: status, names 0x%08X-"
                "0x%08X, built-in tables 0x%08X-0x%08X, live tables 0x%08X-0x%08X; 4 flag bytes in the code"
                % (mk.STORE, mk.SCRATCH, RAM, RAM + 0x800, RAM + 0x800, RAM + 0x800 + snapn, rlive,
                   rlive + 36 * 4 * 512),
        "ops": ops,
    }
    with open(os.path.join(ROOT, "patches", SPEC + ".json"), "w") as f:
        json.dump(spec, f, indent=1)
        f.write("\n")
    desc = {
        "what": "Film simulations in the twelve art filter entries, each of which takes any look; film looks "
                "loaded from the SD card with the menu row Load Looks in Custom Menu J, shown under their own names and kept in "
                "the camera; interval shooting with up to 240 frames, a level gauge with calibration, and focus "
                "peaking",
        "specs": base_specs + ["patches/%s.json" % SPEC],
        "first_code": True,
    }
    with open(os.path.join(ROOT, "builds", SPEC + ".json"), "w") as f:
        json.dump(desc, f, indent=1)
        f.write("\n")
    print("wrote patches/%s.json (%d ops) and builds/%s.json" % (SPEC, len(ops), SPEC))
    argv = [a for a in sys.argv[1:] if a != "--v4"]
    if argv:
        txt = mk.run(BIN + "/mn10300-elf-objdump", "-d", *sum((["-j", k] for k in RUNS), []), "-j", ".hs", e)
        open(argv[0], "w").write(re.sub(r"/[^\s:]*looks3\.elf", "looks3.elf", txt))


if __name__ == "__main__":
    main()
