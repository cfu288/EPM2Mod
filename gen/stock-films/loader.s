# The film loader (card-looks): the task, the GUI hook's routine and the EXIF name. loader.py fills the
# named fields (addresses of the tables it places, texts, the layout of structure.py) and assembles the result.
# A literal per-cent sign is written twice.
.equ MAGIC,    0x4b4c5045        # "EPLK"
.equ STORE,    %(store)#x        # the stored look file (cached address)
.equ SCRU,     %(scratch)#x + 0x40000000
.equ MAXREAD,  %(maxread)d
.equ SLOTTAB,  %(slottab)#x
.equ CRCT,     %(crct)#x
.equ NAMEIDS,  %(nameids)#x      # 36 u16: three string ids per slot (0: none)
.equ SWTAB,    %(swtab)#x        # 12 pointers: each entry's switch list {u32 count, count x {u32 address,
                                 # u8 size, 3 x 0, 4 film bytes, 4 stock bytes}}
.equ BLOCKS,   %(blocks)#x       # 12 u32: each entry's RAM block
.equ PMSET,    %(pmset)#x        # u16 info ids, 0 at the end
.equ PMMAP,    %(pmmap)#x        # 5 x {u8 stock value, u8 hidden value, u16 0, u32 the entry's byte in list 111}
.equ TXTTAB,   %(txttab)#x       # 4 x {u16 id, u16 0, u32 text}: the row's texts
.equ TXT_LABEL, %(txt_label)#x
.equ S_LOADED, %(s_loaded)#x
.equ S_NOFILE, %(s_nofile)#x
.equ S_BAD,    %(s_bad)#x
.equ S_BUILTIN, %(s_builtin)#x
.equ S_WORK,   %(s_work)#x
.equ LANG,     %(lang)#x         # word: the pointer array of the loaded language
.equ RAMU,     %(ram)#x + 0x40000000
.equ RSTAT,    RAMU              # u32: the status text (0: the language's Off)
.equ RORIG,    RAMU + 0x10       # 36 u32: the language's own strings of the name ids
.equ RNAMES,   RAMU + 0x100      # 36 x 48 B: the names
.equ FLAGS_U,  FLAGS + 0x40000000
.equ BUSY,     FLAGS_U           # the task runs
.equ APPLIED,  FLAGS_U + 1       # mode 0 was started in this session
.equ STOREOK,  FLAGS_U + 2       # the store held a valid look file at the last check
.equ MODE,     FLAGS_U + 3       # 0 start, 1 load, 3 texts and names
.equ REMAP,    FLAGS_U + 4       # 1: the task switched entries; T_GUI maps the Picture Mode settings

.section .tk,"ax"
T_GUI:                           # the "state =" trace call of the GUI state setter, d0 = state (task CA_MAIN); the
    movm [d2,d3,other],(sp)      # GUI calls it at every key, also when the state stays the same
    mov psw,d2
    mov d0,d3
    movbu (BUSY),d0
    cmp 0,d0
    bne 9f
    calls GUIEXTRA               # the Picture Mode remap after a Load, then the film's name
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
    .org %(flags_org)d
FLAGS: .byte 0, 0, 0, 0, 0
    .balign 4
PATH:  .asciz "C:\\EPM2LOOK.BIN"
RMODE: .asciz "r"

.section .ap,"ax"
T_TASK:                          # task USRTEST_A (id 0x90), started by T_GUI; it ends when it returns
    movm [d2,d3,a2,a3],(sp)
    add -32,sp                   # (0,sp) is the return slot of every call: no locals here
    movbu (MODE),d0
    cmp 3,d0
    beq T_NAMES
    cmp 0,d0
    bne T_LOAD
    clr d0                       # mode 0, the first GUI state: the stored looks
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
    mov STORE,a0
    calls MASK                   # d0: the entries the file lists
    bra 2f
1:  clr d0
    movbu d0,(STOREOK)
2:  calls SWITCH                 # film words for those entries, stock words for the others
    movbu (MODE),d0              # after a Load only: the Picture Mode settings take the switched values (at a start
    cmp 1,d0                     # they hold them already: saved after the Load)
    bne 3f
    movbu d0,(REMAP)
3:
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
    mov 3,d3
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
APPLY:                           # a0 = a valid look file: each record's operations, into the entry's block
    movm [d2,d3,a2,a3],(sp)
    add -20,sp                   # (16,sp) the entry's RAM block                   # (4,sp) records left, (8,sp) the operation, (12,sp) the end of a tone table
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
    mov BLOCKS,a2
    mov (d0,a2),d1
    mov d1,(16,sp)
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
    mov (16,sp),d1
    add d1,a1
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
9:  add 20,sp
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

.section .ap,"ax"
MASK:                            # a0 = a valid look file -> d0 = bit n for each entry n it lists
    movm [d2,d3],(sp)
    movbu (5,a0),d1
    add 32,a0
    clr d0
1:  cmp 0,d1
    beq 9f
    movbu (a0),d2
    mov 1,d3
    asl d2,d3
    or d3,d0
    add 1708,a0
    add -1,d1
    bra 1b
9:  movm (sp),[d2,d3]
    rets

SWITCH:                          # d0 = the entries with a film
    movm [d2,d3,a2,a3],(sp)
    add -8,sp
    mov d0,d3
    clr d2
1:  mov d2,d0
    asl2 d0
    mov SWTAB,a2
    mov (d0,a2),a2
    mov (a2),d0
    mov d0,(4,sp)                # words left in the entry's list
    add 4,a2
2:  mov (4,sp),d0
    cmp 0,d0
    beq 6f
    add -1,d0
    mov d0,(4,sp)
    mov (a2),a0                  # the address
    mov a2,a1
    add 8,a1                     # the film bytes
    mov d3,d0
    lsr d2,d0
    btst 1,d0
    bne 3f
    add 4,a1                     # no film: the stock bytes
3:  movbu (4,a2),d1
    cmp 4,d1
    bne 4f
    mov (a1),d0                  # a word: one write, so no reader sees half of it
    mov d0,(a0)
    mov d0,(0x40000000,a0)
    bra 5f
4:  movbu (a1),d0
    movbu d0,(a0)
    movbu d0,(0x40000000,a0)
    inc a0
    inc a1
    add -1,d1
    bne 4b
5:  add 16,a2
    bra 2b
6:  inc d2
    cmp 12,d2
    bne 1b
    add 8,sp
    movm (sp),[d2,d3,a2,a3]
    rets

PMREMAP:                         # GUI task, after a Load: the Picture Mode settings follow the entries' stored values
    movm [d2,d3,a2,a3],(sp)
    add -28,sp                   # (8) setting list, (12) id, (16) value, (20) map, (24) left
    mov PMSET,a0
    mov a0,(8,sp)
1:  mov (8,sp),a0
    movhu (a0),d0
    cmp 0,d0
    beq 9f
    add 2,a0
    mov a0,(8,sp)
    mov d0,(12,sp)
    call 0x7e67f822,[],4         # Get_CameraInfo(id) -> d0
    mov d0,(16,sp)
    mov PMMAP,a0
    mov a0,(20,sp)
    mov 5,d0
    mov d0,(24,sp)
2:  mov (20,sp),a0
    mov (4,a0),a1
    movbu (a1),d1                # the entry's stored value now (its byte in the value list)
    mov (16,sp),d0
    movbu (a0),d2                # stock
    movbu (1,a0),d3              # hidden
    cmp d2,d0
    bne 3f
    cmp d3,d1
    bne 5f
    mov d3,d1                    # the stock value, and the entry has a film: the hidden value
    bra 4f
3:  cmp d3,d0
    bne 5f
    cmp d2,d1
    bne 5f
    mov d2,d1                    # the hidden value, and the entry has no film: the stock value
4:  mov (12,sp),d0
    call 0x7e67f882,[d2,d3],12   # Set_CameraInfo(id, value)
    bra 1b
5:  mov (20,sp),a0
    add 8,a0
    mov a0,(20,sp)
    mov (24,sp),d0
    add -1,d0
    mov d0,(24,sp)
    bne 2b
    bra 1b
9:  add 28,sp
    movm (sp),[d2,d3,a2,a3]
    rets

.section .ap,"ax"
GUIEXTRA:                        # T_GUI, while the task does not run
    add -8,sp                    # (0,sp): the return slot of the calls below; T_GUI's return address at (8,sp)
    movbu (REMAP),d0
    cmp 0,d0
    beq 1f
    clr d0
    movbu d0,(REMAP)
    calls PMREMAP
1:  calls FILMNAME
    add 8,sp
    rets

FILMNAME:                        # T_GUI (task CA_MAIN): ImageDescription = the selected entry's film name, else stock
    movm [d2,d3,a2,a3],(sp)
    add -12,sp
    mov 0x9481,d0                # the stored Picture Mode
    mov 0,a0
    clr d1
    call 0x7e457c75,[d2,d3],12   # prm_get(tag, 0, 0) -> d0
FN_PM:
    add -100,d0
    cmp 19,d0
    bcc 8f                       # not 100..118: no film
    mov FNSLOT,a0
    movbu (d0,a0),d2             # the entry's slot, 0xff: no film
    cmp 0xff,d2
    beq 8f
    movbu (STOREOK),d0
    cmp 0,d0
    beq 8f
    mov STORE,a2                 # the stored file's record of that slot
    movbu (5,a2),d3
    add 32,a2
1:  cmp 0,d3
    beq 8f
    movbu (a2),d0
    cmp d2,d0
    beq 2f
    add 1708,a2
    add -1,d3
    bra 1b
2:  movbu (4,a2),d0
    cmp 0,d0
    beq 8f                       # a film without a name: Olympus's text, as the menu keeps the entry's name
    mov FNBUF,a0                 # 31 spaces and a NUL, then the name (16 B, NUL-padded) over the first 16
    mov FNNUL,a1
    mov 32,d0
    mov 1,d1
    call 0x7e70b0f6,[d2,d3,a2,a3],20
    mov a2,a1
    add 4,a1
    mov FNBUF,a0
    mov 16,d0
    clr d1
    call 0x7e70b0f6,[d2,d3,a2,a3],20
    bra 9f
8:  mov FNBUF,a0                 # Olympus's text, as the boot writes it
    mov %(stock)#x,a1
    mov 32,d0
    mov 1,d1
    call 0x7e70b0f6,[d2,d3,a2,a3],20
9:  mov FNBUF,a0                 # into the template as 8 words (a reader never sees a half-written word),
    mov %(desc)#x,a1             # cached and uncached
    mov 8,d1
3:  mov (a0),d0
    mov d0,(a1)
    mov d0,(0x40000000,a1)
    add 4,a0
    add 4,a1
    add -1,d1
    bne 3b
    add 12,sp
    movm (sp),[d2,d3,a2,a3]
    rets
FNSLOT: .byte %(slots)s
FNNUL:  .byte 0
    .balign 4
FNBUF:  .space 32
