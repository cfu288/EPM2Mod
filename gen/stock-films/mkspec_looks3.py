"""Write data/specs/card-looks-3.json and data/builds/card-looks-3.json: the looks loader for the acceptance criteria of
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

import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "cli", "src"))

import mkspec_looks as mk  # noqa: E402
from epm2mod.container import parse  # noqa: E402
from epm2mod.looks import lookfile, slots  # noqa: E402

V4 = "--v4" in sys.argv          # card-looks-4: the Custom Menu of data/specs/custom-menu-rows.json (an added row)
SPEC = "card-looks-4" if V4 else "card-looks-3"
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
