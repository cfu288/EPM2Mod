"""Write patches/log-core.json and patches/log-probes.json: the structured log (NOTES.md in this folder).

Research code. Both specs are deltas on the pinned build builds/peaking-colours.json: every `expect` is a byte
string of that build. The event ids come from logs/events.json, which the decoder (`epm2mod log`) also reads.
The build id in each block header is the first 8 bytes of a sha256 of the dictionary's events (id, name, level, args).

log-core:   log_put / log_chg / log_cnt (kernel range), the firmware-error hook, the boot hook, the flush task
            (the dormant task USRTEST_A gets a new entry) and the GUI-state hook that starts it.
log-probes: one hook and one small routine per event of the features.

A hook replaces whole instructions with `jmp routine` (+ nop). The routine saves d0, d1, a0, a1, mdr, lir, lar
(`movm [other],(sp)`), loads the arguments, calls the log core, restores, runs the replaced instructions and
jumps back. It leaves every register and the flags as they were: it uses only instructions that keep the flags,
or it saves the PSW in d2 (T_BOOT, T_GUI). A replaced `call` is assembled again for its new address; every other replaced instruction is copied
as bytes and must not be pc-relative.

Usage: mkspec_log.py PINNED_DIR WORKDIR [LISTING.txt]
  PINNED_DIR  `python3 tools/oetool.py unpack build/peaking-colours.BIN PINNED_DIR`
  WORKDIR     scratch folder for the assembler files (outside the repository)

       mkspec_log.py --peaking-time BASE_DIR WORKDIR [LISTING.txt]
  Writes patches/log-peaking-time.json only: the timing probe of the build debug-log-peaking-fast (event pk_stats).
  It is a delta on the specs of that build before it (the pinned specs, peaking-fast, log-core, log-probes), and
  it does not write log-core or log-probes. It also puts the build id of logs/events.json into the flush task,
  in place of the id that log-core carries.
  BASE_DIR    unpacked image of builds/debug-log-peaking-fast.json without its last spec

       mkspec_log.py --peaking-guard BASE_DIR WORKDIR [LISTING.txt]
  Writes patches/log-peaking-guard.json only: event pk_guard of the build debug-log-peaking-fast-2. It is a delta
  on the specs of that build before it (the pinned specs, peaking-save-guard, log-core, log-probes,
  log-peaking-time). Its one hook is in stock bytes. It puts the build id of logs/events.json into the flush task, in place of the id that
  log-peaking-time left there.
  BASE_DIR    a folder with block0_0100.bin of that build without its last spec (tools/emu/patchblock.py -o)

       mkspec_log.py --card-read BASE_DIR WORKDIR [LISTING.txt]
  Writes patches/log-card-read.json only: the card-read probe of the build debug-log-card-read (event card_read;
  experiments/2026-11-17-card-looks/NOTES.md). It is a delta on builds/debug-log-films-12d.json. Its hook
  is the flush task's entry (log-core's code), its routine in a free run of segment 2's listed area. It puts the build
  id of logs/events.json into the flush task, in place of the id that log-peaking-guard left there.
  BASE_DIR    unpacked image of builds/debug-log-films-12d.json (block0_0100.bin)

       mkspec_log.py --card-look BASE_DIR WORKDIR [LISTING.txt]
  Writes patches/log-card-look.json only: probe 2 of the build debug-log-card-look (events card_read, card_look):
  the card-read probe that also copies an art matrix from the file into the table of codes 71 and 80 (Pro 400H)
  in RAM. It takes the place of log-card-read (the same base, BASE_DIR as for --card-read).

       mkspec_log.py --card-probe BASE_DIR WORKDIR [LISTING.txt]
  Writes patches/log-card-probe.json only: the probe harness of the build debug-log-card-probe (events card_read,
  card_rec, card_done): the card file holds records {address, length, bytes}, each written only when it lies inside
  one of the tables of the Pro 400H slot, and a flag that forces the look stages to recompute. It takes the place
  of log-card-look (the same base, BASE_DIR as for --card-read).

       mkspec_log.py --card-keep BASE_DIR WORKDIR [LISTING.txt]
  Writes patches/log-card-keep.json only: the persistence probe of the build debug-log-card-keep (events card_read,
  card_keep, bank_tail, bank_look): a look file sets the Pro 400H matrix and is kept in the EEROM bank's tail, and
  every start applies the kept matrix at its first GUI state. In place of log-card-look (BASE_DIR as for --card-read).
"""
import hashlib, json, os, re, struct, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BASE = 0x7E421020
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
PINNED = "builds/peaking-colours.json"
PINNED_SHA = "4d6b1f26ed92d66b62b4d7dc32d26168e33fd8b153a7655d6c0d9a58267456f8"
BIN = os.path.join(os.path.abspath(__file__).split("/experiments/")[0], "build", "toolchain", "bin")
MAPS = [os.path.join(ROOT, "build/map", f) for f in ("functions.txt", "linear.txt")]

# Code areas (tools/freespace.py area: both USABLE-CODE, camera-tested code in each).
AREAS = {
    ".kc": (0x7E4C9514, 0x7E4C9630, "log-core", "kernel range: log_put, log_chg, log_cnt, T_ERR, T_BOOT"),
    ".kp": (0x7E4C9630, 0x7E4C9800, "log-probes", "kernel range: routines of the hooks in segment 1 and the kernel"),
    ".uc": (0x7EBF2C00, 0x7EBF3000, "log-core", "segment 2: flush task, T_GUI, file name"),
    ".up": (0x7EBF3780, 0x7EBF3BAD, "log-probes", "segment 2: routines of the hooks in segments 2 and 3"),
}
TASK_ENTRY = 0x7E439C80          # CPU0 task table 0x7E438CD0, row of id 0x90 (USRTEST_A): the entry word
TASK_ENTRY_OLD = 0x7E501C5B
RING_RECORDS = 512
BLOCK_RECORDS = 30               # (512 - 32) / 16: one block is one sector of the file

SYMS = """
.equ MAGIC,  0x314c5045      # "EPL1": the ring header is valid
.equ RING0,  0xbe4f9000      # CPU0 ring: 32-byte header + 512 records of 16 bytes (uncached alias of 0x7E4F9000)
.equ RING1,  0xbe4fb020      # CPU1 ring, same layout
.equ PST,    0xbe4fd040      # state of the flush and of the probes, 128 bytes, cleared at every start
.equ BUSY,   PST+0           # u8: the flush task was started and has not ended
.equ RESULT, PST+1           # u8: result of the last flush (0 ok, 1 no file, 2 write failed, 3 file full, 4 not saved)
.equ TRIG,   PST+4           # GUI state that started the flush
.equ SHGUI,  PST+8           # last GUI state logged
.equ IVN,    PST+12          # frames counted since iv_start
.equ G_LATCH, PST+16         # gates: {u32 last arg0, u8 budget}
.equ G_HEAP,  PST+24
.equ G_PK9,   PST+32
.equ G_ART,   PST+40
.equ G_STAGE, PST+48
.equ G_MATRIX, PST+56
.equ G_CURVE, PST+64
.equ EXPECT, PST+80          # file size that the last flush should have left, 0 = nothing to check
.equ TIMER,  0x98900074      # timer channel 9, counts down in microseconds (stock now_us 0x7E4262CD)
.equ CPUNO,  0x8050          # CPU number register (stock boot mark 0x7E426511 chooses its buffer by it)
.equ PKW,    0x602be8c4      # peaking bytes L, R, L2, C (focus-peaking NOTES 11.3, 15.3)
.equ LVW,    0x605b1cd4      # live-view struct +4: byte +5 is the art filter type
.equ IVST,   0x602b0cdc      # intervalShootingState word
.equ PWRF,   0x604154e6      # u16 power-on factor (getter 0x7E45D407)
.equ WAKE,   0x604154e9      # u8 wake reason (getter 0x7E45D893)
.equ LVX,    0x603f4c22      # level gauge working set, entry 0: x, y, z, temperature (level-gauge NOTES 12.1)
.equ BUF,    PST+128         # one 512-byte block for fileif_fwrite
.equ FCAP,   0x400000        # stop appending when the file has 4 MiB
"""

CORE_K = """
.section .kc,"ax"
# d0 = event id, d1 = arg0, a0 = arg1. Every register and the flags are kept. No call, no wait.
log_chg:                         # a1 -> gate: log when arg0 differs from the last one, or the gate has budget
    movm [d2,d3,a2,a3],(sp)
    mov psw,d2
    mov (a1),d3
    cmp d1,d3
    mov d1,(a1)
    bne lp_body
    bra lc_budget
log_cnt:                         # a1 -> gate: log while the gate has budget
    movm [d2,d3,a2,a3],(sp)
    mov psw,d2
lc_budget:
    movbu (4,a1),d3
    cmp 0,d3
    beq lp_done
    add -1,d3
    movbu d3,(4,a1)
    bra lp_body
log_put:
    movm [d2,d3,a2,a3],(sp)
    mov psw,d2
lp_body:
    and 0xf7ff,psw               # interrupts off on this CPU (kernel idiom 0x7E43292A)
    nop
    nop
    mov RING0,a2
    mov (CPUNO),d3
    cmp 0,d3
    beq 1f
    mov RING1,a2                 # one ring per CPU: no lock between the CPUs
1:  mov (a2),d3
    cmp MAGIC,d3
    beq 2f
    mov MAGIC,d3                 # RAM was clear (or never used): start an empty ring
    mov d3,(a2)
    clr d3
    mov d3,(4,a2)
    mov d3,(8,a2)
    mov d3,(12,a2)
    mov d3,(16,a2)
2:  mov (4,a2),d3                # w: records written since the ring was started
    mov d3,a3
    inc d3
    mov d3,(4,a2)
    mov a3,d3
    and %(mask)d,d3
    asl 4,d3
    add d3,a2
    movhu d0,(32,a2)             # id
    mov a3,d3
    movhu d3,(34,a2)             # sequence number
    mov (TIMER),d3
    mov d3,(36,a2)
    mov d1,(40,a2)
    mov a0,(44,a2)
lp_done:
    mov d2,psw
    nop
    nop
    movm (sp),[d2,d3,a2,a3]
    retf [],0

T_ERR:                           # entry of the error recorder 0x7E426D4B(d0 = code, (48,sp) = count, (52,sp).. = arguments)
    movm [other],(sp)
    mov d0,d1
    mov mdr,d0
    mov d0,a0
    mov %(fw_error)d,d0
    call log_put,[],0
    mov (80,sp),d1
    mov (84,sp),a0
    mov %(fw_error_args)d,d0
    call log_put,[],0
    movm (sp),[other]
%(displaced_ERR)s
    jmp %(back_ERR)s

T_BOOT:                          # entry of Usr0 0x7E503DD4 (boot task, CPU0)
    movm [d2,other],(sp)
    mov psw,d2                   # this routine changes the flags: keep them
    mov PST,a0
    clr d0
    mov 32,d1
1:  mov d0,(a0)
    inc4 a0
    add -1,d1
    bne 1b
    movbu (WAKE),d1
    asl 16,d1
    movhu (PWRF),d0
    or d0,d1
    mov d1,a0
    clr d1                       # session 0: the ring was not in RAM
    mov (RING0),d0
    cmp MAGIC,d0
    bne 2f
    mov (RING0+16),d1
    inc d1
    mov d1,(RING0+16)
2:  mov %(boot)d,d0
    call log_put,[],0
    mov d2,psw
    nop
    nop
    movm (sp),[d2,other]
%(displaced_BOOT)s
    jmp %(back_BOOT)s
"""

CORE_U = """
.section .uc,"ax"
FLUSH:                           # task USRTEST_A (id 0x90, priority 11, stack 0x800): started by T_GUI, runs once
    movm [d2,d3,a2,a3],(sp)
    add -64,sp                   # (36,sp) (40,sp) file size words, (44,sp) size, (48,sp) loop count, (52,sp) tries, (56,sp) blocks
    clr d0
    mov d0,(36,sp)
    mov d0,(40,sp)
    mov PATH,a0
    mov sp,a1
    add 36,a1
    mov a1,d0
    add 4,d0
    call 0x7e5c54fd,[],20        # fileif_filesize_get(a0 = path, a1, d0 -> two words) -> 0 when the size was read
    mov d0,d3
    mov (36,sp),d0
    mov (40,sp),d1
    add d1,d0                    # the size (one of the two words is the high word, 0 for this file)
    mov d0,(44,sp)
    mov (EXPECT),d1              # the size that the last flush should have left (0: nothing to check)
    cmp 0,d1
    beq 2f
    mov 1,d2
    cmp 0,d3
    bne f_result                 # the size cannot be read now: try again at the next flush
    cmp d1,d0
    bcc 1f
    mov 4,d0                     # the file did not keep the blocks of the last flush (fclose does not report
    movbu d0,(RESULT)            # a failed directory update): write its records again
    mov RING0,a2
    mov (20,a2),d0
    mov d0,(8,a2)
    mov RING1,a2
    mov (a2),d0
    cmp MAGIC,d0
    bne 1f
    mov (20,a2),d0
    mov d0,(8,a2)
1:  clr d0
    mov d0,(EXPECT)
2:  movbu (RESULT),d0
    mov d0,a0                    # result of the flush before this one
    mov %(flush)d,d0
    mov (TRIG),d1
    call log_put,[],0
    mov 3,d2
    mov (44,sp),d0
    cmp FCAP,d0
    bcc f_result
    clr d0
    mov d0,(56,sp)               # blocks written in this flush
    mov PATH,a0
    mov MODE,a1
    call 0x7e5c52dc,[],20        # fileif_fopen(path, "a") -> a0 = handle or 0
    mov a0,a3
    mov 1,d2
    cmp 0,a3
    beq f_result                 # no card, card full or write-protected: nothing to do
    mov RING0,a2
f_ring:
    mov (a2),d0
    cmp MAGIC,d0
    bne f_next
    mov (4,a2),d2                # w
    mov (8,a2),d3                # f: records already in the file
    mov d2,d0
    sub d3,d0
    cmp %(n)d,d0
    bls 8f
    add -%(n)d,d0                # the ring wrapped over records that were not flushed
    mov (12,a2),d1
    add d0,d1
    mov d1,(12,a2)               # drop count
    mov d2,d3
    add -%(n)d,d3
    mov d3,(8,a2)
8:  mov d3,(20,a2)               # f before this flush: the next flush puts it back if the file did not keep the blocks
f_block:                         # one block = one 512-byte sector: header, up to %(per)d records, zeros
    cmp d2,d3
    beq f_next
    mov BUF,a0
    clr d0
    mov 128,d1
1:  mov d0,(a0)
    inc4 a0
    add -1,d1
    bne 1b
    mov BUF,a0
    mov 0x474c5045,d0            # "EPLG"
    mov d0,(a0)
    mov 0x20001001,d0            # version 1, record size 16, cpu 0, header size 32
    mov d0,(4,a0)
    cmp RING0,a2
    beq 2f
    mov 1,d0
    movbu d0,(6,a0)
2:  mov %(bid0)d,d0              # build id: sha256 of the event list of logs/events.json, first 8 bytes
    mov d0,(8,a0)
    mov %(bid1)d,d0
    mov d0,(12,a0)
    mov d3,(16,a0)               # number of the first record of the block (its low 16 bits = its sequence number)
    mov d2,d0
    sub d3,d0
    cmp %(per)d,d0
    bls 3f
    mov %(per)d,d0
3:  mov d0,(20,a0)               # records in the block
    mov d0,(48,sp)
    mov (12,a2),d1
    mov d1,(24,a0)
    mov (16,a2),d1
    mov d1,(28,a0)
    add 32,a0
4:  mov d3,d0                    # copy one record from the ring
    and %(mask)d,d0
    asl 4,d0
    mov a2,a1
    add d0,a1
    mov (32,a1),d0
    mov d0,(a0)
    mov (36,a1),d0
    mov d0,(4,a0)
    mov (40,a1),d0
    mov d0,(8,a0)
    mov (44,a1),d0
    mov d0,(12,a0)
    add 16,a0
    inc d3
    mov (48,sp),d0
    add -1,d0
    mov d0,(48,sp)
    bne 4b
    mov 3,d0
    mov d0,(52,sp)               # at most 3 tries
5:  mov BUF,a0
    mov 1,d0
    mov 512,d1
    mov a3,a1
    call 0x7e5c5339,[],24        # fileif_fwrite(a0 = buffer, d0 = 1, d1 = bytes, a1 = handle) -> bytes written
    cmp 512,d0
    beq 7f
    cmp 0,d0
    bne f_fail                   # a part of the block was written (card full): stop
    mov (52,sp),d0
    add -1,d0
    mov d0,(52,sp)
    beq f_fail
    mov 100,d0
    call 0x7e449605,[d2],8       # OlyTaDl: sleep 100 ms, then write the same block again
    bra 5b
7:  mov d3,(8,a2)                # the block is in the file
    mov (56,sp),d0
    inc d0
    mov d0,(56,sp)
    bra f_block
f_next:
    cmp RING0,a2
    bne 6f
    mov RING1,a2
    bra f_ring
6:  clr d2
    bra f_close
f_fail:
    mov 2,d2                     # the records of this block stay in the ring for the next flush
f_close:
    mov a3,a0
    call 0x7e5c5308,[],12        # fileif_fclose
    mov (56,sp),d0
    cmp 0,d0
    beq f_result
    asl 9,d0
    mov (44,sp),d1
    add d1,d0
    mov d0,(EXPECT)              # the next flush checks that the file has this size
f_result:
    movbu d2,(RESULT)
    clr d0
    movbu d0,(BUSY)
    ret [d2,d3,a2,a3],80
PATH:
    .asciz "C:\\\\EPM2LOG.BIN"
MODE:
    .asciz "a"

T_GUI:                           # the "state =" trace of the GUI state setter 0x7ECDF5E9, d0 = new state (task CA_MAIN)
    movm [d2,other],(sp)
    mov psw,d2                   # this routine changes the flags: keep them
    mov d0,d1
    mov (SHGUI),d0
    cmp d0,d1
    beq 9f
    mov d1,(SHGUI)
    mov d0,a0
    mov %(gui_state)d,d0
    call log_put,[],0
    mov d1,d0
    lsr 8,d0
    cmp 0x57,d0                  # 0x57xx: the menus
    beq 5f
    lsr 4,d0
    cmp 2,d0                     # 0x2xxx: power off, sleep
    beq 5f
    cmp 3,d0                     # 0x3xxx: playback
    bne 9f
5:  movbu (BUSY),d0
    cmp 0,d0
    bne 9f
    mov d1,(TRIG)
    call 0x7ecd360a,[d2],8       # the GUI's isMediaWriting(): 1 while the card is written
    cmp 0,d0
    bne 9f
    mov 1,d0
    movbu d0,(BUSY)
    mov 0x90,d0
    call 0x7e449541,[d2,d3],12   # OlyTaSt(USRTEST_A)
9:  mov d2,psw
    nop
    nop
    movm (sp),[d2,other]
%(displaced_GUI)s
    jmp %(back_GUI)s
"""

LATCH = "    mov (PKW),d1\n"
PROBES_K = """
.section .kp,"ax"
T_LATCH:                         # entry of the live-view expose setter 0x7E6C610B (mov task, every frame)
    movm [other],(sp)
    mov (PKW),d1
    mov (LVW),a0
    mov G_LATCH,a1
    mov %(pk_latch)d,d0
    call log_chg,[],0
    movm (sp),[other]
%(displaced_LATCH)s
    jmp %(back_LATCH)s

T_HEAP:                          # entry of the image-work heap mode setter 0x7E578C60(d0 = mode)
    movm [other],(sp)
    mov d0,d1
    mov mdr,d0
    mov d0,a0
    mov G_HEAP,a1
    mov %(pk_heap_mode)d,d0
    call log_chg,[],0
    movm (sp),[other]
%(displaced_HEAP)s
    jmp %(back_HEAP)s

T_PK9:                           # Key Line pass 9 0x7E7266D9 after the gain is chosen (ART task): d0 = usGain2
    movm [other],(sp)
    movbu (G_PK9+4),d1
    cmp 0,d1
    beq 1f
    mov d0,d1
    asl 16,d1
    mov (44,sp),a0               # pass 9's second argument
    mov (32,a0),a0               # Key Line context
    mov (20,a0),a1               # line image
    movbu (1,a1),d0
    or d0,d1
    mov (16,a0),a1               # picture
    mov d1,a0
    mov a1,d1
    mov G_PK9,a1
    mov %(pk_pass9)d,d0
    call log_cnt,[],0
1:  movm (sp),[other]
%(displaced_PK9)s
    jmp %(back_PK9)s

T_ART:                           # six-axis stage: dispatch by art code, d3 = art code, d0 = 4 x (code - 9)
    movm [other],(sp)
    mov d3,d1
    mov 0x7e78c254,a0
    mov (d0,a0),a0
    mov G_ART,a1
    mov %(art_sixaxis)d,d0
    call log_chg,[],0
    movm (sp),[other]
%(displaced_ART)s
    jmp %(back_ART)s

T_STAGE:                         # colour-matrix stage before the art-matrix choice, a3 = job parameters
    movm [other],(sp)
    movbu (79,a3),d1
    mov (20,a3),a0
    mov G_STAGE,a1
    mov %(film_stage)d,d0
    call log_chg,[],0
    movm (sp),[other]
%(displaced_STAGE)s
    jmp %(back_STAGE)s

T_MATRIX:                        # art matrix apply, a1 = table
    movm [other],(sp)
    mov a1,d1
    mov d3,a0
    mov G_MATRIX,a1
    mov %(film_matrix)d,d0
    call log_chg,[],0
    movm (sp),[other]
%(displaced_MATRIX)s
    jmp %(back_MATRIX)s

T_CURVE:                         # tone-curve selector 0x7E56E837: dispatch by art code, d1 = 4 x (code - 8)
    movm [other],(sp)
    mov 0x7e78c8e4,a0
    mov (d1,a0),a0
    movbu (52,sp),d1             # the art code: the selector's (20,sp)
    mov G_CURVE,a1
    mov %(film_curve)d,d0
    call log_chg,[],0
    movm (sp),[other]
%(displaced_CURVE)s
    jmp %(back_CURVE)s

T_ADJ:                           # entry of api_adj_Set_Slope_Adjust 0x7E676261(d0 = mode, d1 = rotate)
    movm [other],(sp)
    mov d1,a0
    mov d0,d1
    mov %(lv_adjust)d,d0
    call log_put,[],0
    movm (sp),[other]
%(displaced_ADJ)s
    jmp %(back_ADJ)s

T_LVV:                           # entry of the accelerometer table reload 0x7E459A5F
    movm [other],(sp)
    movhu (LVX+36),d1
    asl 16,d1
    movhu (LVX+24),d0
    or d0,d1
    mov d1,a0
    movhu (LVX+12),d1
    asl 16,d1
    movhu (LVX),d0
    or d0,d1
    mov %(lv_values)d,d0
    call log_put,[],0
    movm (sp),[other]
%(displaced_LVV)s
    jmp %(back_LVV)s
"""

PROBES_U = """
.section .up,"ax"
T_MFON:                          # CmpSts_MfAssist::entryMfAssistOn, a2 = state object
    movm [other],(sp)
    mov 3,d0
    movbu d0,(G_PK9+4)           # log the next 3 passes 9
    mov (PKW),d1
    mov a2,a0
    mov %(pk_mf_start)d,d0
    call log_put,[],0
    movm (sp),[other]
%(displaced_MFON)s
    jmp %(back_MFON)s

T_MFOFF:                         # CmpSts_MfAssist::entryMfAssistOff
    movm [other],(sp)
    mov (PKW),d1
    mov a2,a0
    mov %(pk_mf_end)d,d0
    call log_put,[],0
    movm (sp),[other]
%(displaced_MFOFF)s
    jmp %(back_MFOFF)s

T_CBS:                           # entry of the shooting callback 0x7E995A0B(a0 = this, d0 = CBS number, d1 = result)
    movm [other],(sp)
    mov d1,a0
    mov d0,d1
    mov 1,d0
    movbu d0,(G_ART+4)           # one record of each pipeline probe after this callback
    movbu d0,(G_STAGE+4)
    movbu d0,(G_MATRIX+4)
    movbu d0,(G_CURVE+4)
    mov %(shoot_cbs)d,d0
    call log_put,[],0
    movm (sp),[other]
%(displaced_CBS)s
    jmp %(back_CBS)s

T_IVSET:                         # setIntervalShootingState, at its trace call: d2 = bits
    movm [other],(sp)
    mov d2,d1
    mov (IVST),a0
    mov %(iv_state_set)d,d0
    call log_put,[],0
    movm (sp),[other]
%(displaced_IVSET)s
    jmp %(back_IVSET)s

T_IVCLR:                         # clearIntervalShootingState, at its trace call: d2 = bits
    movm [other],(sp)
    mov d2,d1
    mov (IVST),a0
    mov %(iv_state_clear)d,d0
    call log_put,[],0
    movm (sp),[other]
%(displaced_IVCLR)s
    jmp %(back_IVCLR)s

T_IVSTART:                       # startIntervalShooting, at its last trace call: d2 = result
    movm [other],(sp)
    mov 0,a0
    mov a0,(IVN)
    mov d2,d1
    mov (IVST),a0
    mov %(iv_start)d,d0
    call log_put,[],0
    movm (sp),[other]
%(displaced_IVSTART)s
    jmp %(back_IVSTART)s

T_IVEND:                         # endIntervalShooting, at its last trace call: d2 = result
    movm [other],(sp)
    mov d2,d1
    mov (IVN),a0
    mov %(iv_end)d,d0
    call log_put,[],0
    movm (sp),[other]
%(displaced_IVEND)s
    jmp %(back_IVEND)s

T_IVFRAME:                       # entry of recordingDone_interval 0x7EA997E5
    movm [other],(sp)
    mov (IVN),a0
    inc a0                       # an address register: the flags stay
    mov a0,(IVN)
    mov a0,d1
    mov (IVST),a0
    mov %(iv_frame)d,d0
    call log_put,[],0
    movm (sp),[other]
%(displaced_IVFRAME)s
    jmp %(back_IVFRAME)s
"""

# name: (spec, site, replaced bytes, events, what)
HOOKS = {
    "ERR":     ("log-core", 0x7E426D4B, 8, "fw_error fw_error_args", "error recorder 0x7E426D4B, entry (pre-reset range; both CPUs)"),
    "BOOT":    ("log-core", 0x7E503DD4, 6, "boot", "Usr0 0x7E503DD4, entry (boot task)"),
    "GUI":     ("log-core", 0x7ECDF6E4, 5, "gui_state", "GUI state setter 0x7ECDF5E9, its last trace call (task CA_MAIN)"),
    "LATCH":   ("log-probes", 0x7E6C610B, 6, "pk_latch", "live-view expose setter 0x7E6C610B, entry (mov task)"),
    "HEAP":    ("log-probes", 0x7E578C60, 6, "pk_heap_mode", "image-work heap mode setter 0x7E578C60, entry"),
    "PK9":     ("log-probes", 0x7E72676D, 7, "pk_pass9", "Key Line pass 9 0x7E7266D9, after T_K (ART task)"),
    "ART":     ("log-probes", 0x7E56D2BF, 6, "art_sixaxis", "six-axis stage, dispatch by art code"),
    "STAGE":   ("log-probes", 0x7E56C68B, 7, "film_stage", "colour-matrix stage, before the art-matrix choice"),
    "MATRIX":  ("log-probes", 0x7E56C764, 6, "film_matrix", "colour-matrix stage, art matrix apply"),
    "CURVE":   ("log-probes", 0x7E56E860, 6, "film_curve", "tone-curve selector 0x7E56E837, dispatch by art code"),
    "ADJ":     ("log-probes", 0x7E676261, 10, "lv_adjust", "api_adj_Set_Slope_Adjust 0x7E676261, entry"),
    "LVV":     ("log-probes", 0x7E459A5F, 5, "lv_values", "accelerometer table reload 0x7E459A5F, entry"),
    "MFON":    ("log-probes", 0x7EB7D47D, 6, "pk_mf_start", "CmpSts_MfAssist::entryMfAssistOn, after T_ON and the trace call"),
    "MFOFF":   ("log-probes", 0x7EB7D44C, 5, "pk_mf_end", "CmpSts_MfAssist::entryMfAssistOff, after T_OFF and the trace call"),
    "CBS":     ("log-probes", 0x7E995A0B, 8, "shoot_cbs", "shooting callback 0x7E995A0B, entry"),
    "IVSET":   ("log-probes", 0x7E969E2F, 5, "iv_state_set", "setIntervalShootingState 0x7E969E1E, trace call"),
    "IVCLR":   ("log-probes", 0x7E9698FD, 5, "iv_state_clear", "clearIntervalShootingState 0x7E9698EC, trace call"),
    "IVSTART": ("log-probes", 0x7E988670, 7, "iv_start", "startIntervalShooting 0x7E98849B, last trace call"),
    "IVEND":   ("log-probes", 0x7E982E8E, 7, "iv_end", "endIntervalShooting 0x7E982DF3, last trace call"),
    "IVFRAME": ("log-probes", 0x7EA997E5, 7, "iv_frame", "recordingDone_interval 0x7EA997E5, entry"),
}
# The timing probe of peaking (focus-peaking NOTES section 17). Its own spec: log-core and log-probes stay the
# flashed ones. Its two hooks are in stock bytes of Key Line pass 9 0x7E7266D9 (segment 1), before and after the
# hooks K (peaking) and PK9 (log-probes), so it changes no byte of another spec's code.
TIME_SPEC = "log-peaking-time"
TIME_AREAS = {".tk": (0x7E4C97BD, 0x7E4C9800, "T_TICK"),      # free runs of the kernel range: the end of the area
              ".t0": (0x7E4C90EA, 0x7E4C90FC, "T_TIME0"),     # of log-probes, after T_HIT of peaking-fast, and
              ".t1": (0x7E4C9621, 0x7E4C9630, "T_TIME0B")}    # between log-core and log-probes
TIME_SITES = {                # site: (bytes, routine, what)
    0x7E72675C: (5, "T_TIME0", "Key Line pass 9, `mov 2,d0` / `movbu d0,(37,a3)` (ucMode), before hook K"),
    0x7E726774: (5, "T_TICK", "Key Line pass 9, `mov 16,d0` / `movbu d0,(36,a3)` (ucBit), after the gain is stored"),
}
TIME_ASM = """
.equ T_ST, PST+88            # {u32 timer value at T_TIME0, u32 sum, u8 passes}
.section .t0,"ax"
T_TIME0:                     # every Key Line pass 9 (the art filter, White, a colour), before the gain is chosen.
                             # d0 is set by the replaced instruction; the flags are not in use
    mov (TIMER),d0
    mov d0,(T_ST)
    jmp T_TIME0B
.section .t1,"ax"
T_TIME0B:
%(displaced_a)s
    jmp %(back_a)s

.section .tk,"ax"
T_TICK:                      # the same pass, after hook K (T_K, and the colour loop for Red, Yellow, Blue) and the
                             # probe PK9. d1, a0, a1 are free here: the stock code loads them again before it
                             # uses them (0x7E726779-0x7E726784), and d0 after the replaced instructions. MDR is
                             # free: the function calls on and returns with ret
%(displaced_b)s
    mov T_ST,a1
    mov (a1),d1
    mov (TIMER),d0
    sub d0,d1                # the timer counts down: microseconds from T_TIME0 to here
    mov (4,a1),d0
    add d0,d1
    mov d1,(4,a1)            # sum over the passes
    movbu (8,a1),d0
    inc d0
    movbu d0,(8,a1)
    and %(every)d,d0
    bne 2f                   # one record per %(n)d passes
    mov d0,(4,a1)
    movhu (34,a3),d0         # usGain2 of this pass
    mov d0,a0
    mov %(pk_stats)d,d0
    call log_put,[],0
2:  jmp %(back_b)s
"""
TIME_EVERY = 8


def peaking_time():
    """Write patches/log-peaking-time.json (see the usage text)."""
    base, work = sys.argv[2:4]
    listing = sys.argv[4] if len(sys.argv) > 4 else None
    os.makedirs(work, exist_ok=True)
    blk_path = os.path.join(base, "block0_0100.bin")
    blk = open(blk_path, "rb").read()
    get = lambda a, n: blk[a - BASE:a - BASE + n]
    d = json.load(open(os.path.join(ROOT, "logs/events.json")))
    mine = [e for e in d["events"] if e["spec"] == TIME_SPEC]
    assert [e["name"] for e in mine] == ["pk_stats"]
    bid = build_id(d["events"])
    old = bytes.fromhex(json.load(open(os.path.join(ROOT, "patches/log-core.json")))["_build_id"])
    # log_put: the third entry of the log core, found by its first instructions after log_chg and log_cnt
    lo = AREAS[".kc"][0]
    head = bytes.fromhex("cff0f2e6")                           # movm [d2,d3,a2,a3],(sp) / mov psw,d2
    at = [lo + i for i in range(0x40) if get(lo + i, 4) == head]
    assert len(at) == 3 and get(at[2] + 4, 4) == bytes.fromhex("fafcfff7"), at     # and 0xf7ff,psw
    (site_a, (n_a, _, _)), (site_b, (n_b, _, _)) = TIME_SITES.items()
    bad = branch_targets_inside([(site, n) for site, (n, _, _) in TIME_SITES.items()], blk, work)
    assert not bad, bad
    asm = SYMS + TIME_ASM % {
        "every": TIME_EVERY - 1, "n": TIME_EVERY, "pk_stats": mine[0]["id"],
        "displaced_a": displaced(blk_path, site_a, n_a), "back_a": "0x%08x" % (site_a + n_a),
        "displaced_b": displaced(blk_path, site_b, n_b), "back_b": "0x%08x" % (site_b + n_b)}
    args = ["--defsym=log_put=%#x" % at[2]]
    args += ["--defsym=s_%s=0x%s" % (a, a) for a in sorted(set(re.findall(r"(?:jmp|call)\s+0x([0-9a-f]{8})", asm)))]
    asm = re.sub(r"((?:jmp|call)\s+)0x([0-9a-f]{8})", r"\1s_\2", asm)
    for site, (n, routine, _) in TIME_SITES.items():
        asm += '\n.section .s%x,"ax"\n    jmp %s\n' % (site, routine) + "    nop\n" * (n - 5)
        args.append("--section-start=.s%x=%#x" % (site, site))
    args += ["--section-start=%s=%#x" % (n, a) for n, (a, _, _) in TIME_AREAS.items()]
    s, o, e, sb = (os.path.join(work, "logtime." + x) for x in ("s", "o", "elf", "bin"))
    open(s, "w").write(asm)
    run(BIN + "/mn10300-elf-as", "-o", o, s)
    run(BIN + "/mn10300-elf-ld", *args, "-e", "%#x" % TIME_AREAS[".tk"][0], "-o", e, o)

    def sect(name):
        run(BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", name, e, sb)
        return open(sb, "rb").read()

    ops = []

    def op(addr, new, note):
        expect = get(addr, len(new))
        assert expect != new, note
        ops.append({"type": "bytes", "block": 0, "offset": "0x%X" % (addr - BASE), "expect": expect.hex(),
                    "new": new.hex(), "_addr": "0x%08X" % addr, "_note": note})

    for name, (a, hi, what) in TIME_AREAS.items():
        code = sect(name)
        assert a + len(code) <= hi, "%s: %d bytes, %d free" % (name, len(code), hi - a)
        assert get(a, len(code)) == b"\xff" * len(code) and code[-1] != 0xFF, name
        op(a, code, "new code, kernel range, 0xFF run: %s (%d B)" % (what, len(code)))
        print("%s: %d B at 0x%X-0x%X, %d B free after" % (what, len(code), a, a + len(code), hi - a - len(code)))
    stock = open(os.path.join(ROOT, "build/blocks", os.path.basename(STOCK) + ".block0.bin"), "rb").read()
    for site, (n, routine, what) in TIME_SITES.items():
        h = sect(".s%x" % site)
        assert len(h) == n and h[0] == 0xDC and get(site, n) == stock[site - BASE:site - BASE + n], hex(site)
        op(site, h, "hook (pk_stats): jmp %s. %s" % (routine, what))
    if bid != old:
        for half in (0, 4):                  # the two `mov imm32,d0` of the flush task that hold the build id
            word = b"\xfc\xcc" + old[half:half + 4]
            i = blk.find(word)
            assert i >= 0 and blk.find(word, i + 1) < 0 and AREAS[".uc"][0] <= BASE + i < AREAS[".uc"][1], half
            new = bid[half:half + 4]
            diff = [k for k in range(4) if new[k] != old[half + k]]
            op(BASE + i + 2 + diff[0], new[diff[0]:diff[-1] + 1], "flush task, block header: build id bytes %d-%d %s -> %s "
               "(logs/events.json)" % (half, half + 3, old[half:half + 4].hex(), new.hex()))
    out = os.path.join(ROOT, "patches", TIME_SPEC + ".json")
    json.dump({
        "name": TIME_SPEC,
        "description": "Structured log, timing probe of peaking: event pk_stats, one record per %d runs of Key Line "
                       "pass 9 (the Key Line art filter, White peaking and colour peaking): the microseconds from "
                       "before the peaking hook of the pass to after it, summed over these passes (for a colour that "
                       "is the colour loop), and usGain2 of the last pass. The time between two records is %d frame "
                       "periods. Two hooks in stock bytes of pass 9 and their routines in the kernel range; no byte "
                       "of the peaking code changes. Needs log-core and log-probes before it: every expect is a byte "
                       "string of that build. It puts the build id %s of logs/events.json into the block header. "
                       "DEBUG builds only. See experiments/2026-11-14-focus-peaking/NOTES.md section 17 and "
                       "docs/logging.md." % (TIME_EVERY, TIME_EVERY, bid.hex()),
        "base": STOCK, "base_sha256": hashlib.sha256(open(os.path.join(ROOT, STOCK), "rb").read()).hexdigest(),
        "status": "candidate: emulator-checked, not flashed",
        "_delta_on": "builds/debug-log-peaking-fast.json without this spec",
        "_build_id": bid.hex(),
        "_ram": "9 bytes of the log's state block (PST+88)",
        "ops": ops,
    }, open(out, "w"), indent=1)
    open(out, "a").write("\n")
    print("wrote", os.path.relpath(out, ROOT), len(ops), "ops; build id", bid.hex())
    if listing:
        txt = run(BIN + "/mn10300-elf-objdump", "-d", *sum((["-j", n] for n in list(TIME_AREAS) + [".s%x" % x for x in TIME_SITES]), []), e)
        open(listing, "w").write(re.sub(r"/[^\s:]*logtime\.elf", "logtime.elf", txt))


# The probe of the save guard of peaking (focus-peaking NOTES section 18). Its own spec, as the timing probe.
# The guard (patches/peaking-save-guard.json) writes 2 to the latch byte L while it holds the lines back. The
# kernel range of the debug builds has no free run left, and a hook inside the guard's own bytes would make the
# free-space check of every build without the log fail. So the probe is in stock bytes of segment 2: the handler
# that the MF Assist state object runs for each focus-ring event while MF Assist is on. It reads L there.
GUARD_SPEC = "log-peaking-guard"
GUARD_AREA = (0x7EBF2510, 0x7EBF2600)        # segment 2, the listed area 0x7EBF1090-0x7EBF3BAD, used by no spec
GUARD_SITE = (0x7EB7DE46, 7, "CmpSts_MfAssist::rcvStartMFAssistIn_MFAssistOn 0x7EB7DE46, entry: `mov a0,a3` / "
                             "`mov imm32,d0` (a focus-ring event while MF Assist is on; GUI task, segment 2)")
GUARD_ASM = """
.equ HMODE,  0x605157cc      # u16 heap mode, u16 mode at the last allocation
.equ POOL02, 0x602ac45c      # pointer to the pool of the heap modes 0 and 2
.equ GRD_ST, PST+100         # u8: a record was written for this hold
.section .gu,"ax"
T_GRD:
    movm [d2,other],(sp)
    mov psw,d2
    movbu (PKW),d0           # L: 2 = the guard holds the lines back
    cmp 2,d0
    beq 1f
    clr d0
    movbu d0,(GRD_ST)
    bra 9f
1:  movbu (GRD_ST),d0
    cmp 0,d0
    bne 9f                   # one record per hold
    mov 1,d0
    movbu d0,(GRD_ST)
    mov (POOL02),a0
    movhu (16,a0),d0
    movhu (76,a0),d1
    sub d1,d0
    mov d0,a0                # arg1: units in use in the pool that is in the way
    mov (HMODE),d1           # arg0
    mov %(pk_guard)d,d0
    call log_put,[],0
9:  mov d2,psw
    nop
    nop
    movm (sp),[d2,other]
%(displaced)s
    jmp %(back)s
"""


def peaking_guard():
    """Write patches/log-peaking-guard.json (see the usage text)."""
    base, work = sys.argv[2:4]
    listing = sys.argv[4] if len(sys.argv) > 4 else None
    os.makedirs(work, exist_ok=True)
    blk_path = os.path.join(base, "block0_0100.bin")
    blk = open(blk_path, "rb").read()
    get = lambda a, n: blk[a - BASE:a - BASE + n]
    d = json.load(open(os.path.join(ROOT, "logs/events.json")))
    mine = [e for e in d["events"] if e["spec"] == GUARD_SPEC]
    assert [e["name"] for e in mine] == ["pk_guard"]
    bid = build_id(d["events"])
    old = bytes.fromhex(json.load(open(os.path.join(ROOT, "patches", TIME_SPEC + ".json")))["_build_id"])
    lo = AREAS[".kc"][0]
    head = bytes.fromhex("cff0f2e6")                           # movm [d2,d3,a2,a3],(sp) / mov psw,d2
    at = [lo + i for i in range(0x40) if get(lo + i, 4) == head]
    assert len(at) == 3 and get(at[2] + 4, 4) == bytes.fromhex("fafcfff7"), at     # log_put: and 0xf7ff,psw
    site, n, what = GUARD_SITE
    stock = open(os.path.join(ROOT, "build/blocks", os.path.basename(STOCK) + ".block0.bin"), "rb").read()
    assert get(site, n) == stock[site - BASE:site - BASE + n], hex(site)
    bad = branch_targets_inside([(site, n)], blk, work)
    assert not bad, bad
    asm = SYMS + GUARD_ASM % {"pk_guard": mine[0]["id"], "displaced": displaced(blk_path, site, n),
                              "back": "0x%08x" % (site + n)}
    args = ["--defsym=log_put=%#x" % at[2]]
    args += ["--defsym=s_%s=0x%s" % (x, x) for x in sorted(set(re.findall(r"(?:jmp|call)\s+0x([0-9a-f]{8})", asm)))]
    asm = re.sub(r"((?:jmp|call)\s+)0x([0-9a-f]{8})", r"\1s_\2", asm)
    asm += '\n.section .hs,"ax"\n    jmp T_GRD\n' + "    nop\n" * (n - 5)
    args += ["--section-start=.hs=%#x" % site, "--section-start=.gu=%#x" % GUARD_AREA[0]]
    s, o, e, sb = (os.path.join(work, "logguard." + x) for x in ("s", "o", "elf", "bin"))
    open(s, "w").write(asm)
    run(BIN + "/mn10300-elf-as", "-o", o, s)
    run(BIN + "/mn10300-elf-ld", *args, "-e", "%#x" % GUARD_AREA[0], "-o", e, o)

    def sect(name):
        run(BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", name, e, sb)
        return open(sb, "rb").read()

    ops = []

    def op(addr, new, note):
        expect = get(addr, len(new))
        assert expect != new, note
        ops.append({"type": "bytes", "block": 0, "offset": "0x%X" % (addr - BASE), "expect": expect.hex(),
                    "new": new.hex(), "_addr": "0x%08X" % addr, "_note": note})

    code = sect(".gu")
    a, hi = GUARD_AREA
    assert a + len(code) <= hi and get(a, hi - a) == stock[a - BASE:hi - BASE], "the area is in use"
    if code[-1] == get(a + len(code) - 1, 1)[0]:
        code += b"\xcb"                      # the free-space ledger counts only changed bytes: end on a nop
    op(a, code, "new code, segment 2: T_GRD (%d B)" % len(code))
    print("T_GRD: %d B at 0x%X-0x%X, %d B free after" % (len(code), a, a + len(code), hi - a - len(code)))
    h = sect(".hs")
    assert len(h) == n and h[0] == 0xDC
    op(site, h, "hook (pk_guard): jmp T_GRD%s. %s" % (" + nop" * (n - 5), what))
    assert bid != old
    for half in (0, 4):                      # the two `mov imm32,d0` of the flush task that hold the build id
        word = b"\xfc\xcc" + old[half:half + 4]
        i = blk.find(word)
        assert i >= 0 and blk.find(word, i + 1) < 0 and AREAS[".uc"][0] <= BASE + i < AREAS[".uc"][1], half
        op(BASE + i + 2, bid[half:half + 4], "flush task, block header: build id bytes %d-%d %s -> %s (logs/events.json)"
           % (half, half + 3, old[half:half + 4].hex(), bid[half:half + 4].hex()))
    out = os.path.join(ROOT, "patches", GUARD_SPEC + ".json")
    json.dump({
        "name": GUARD_SPEC,
        "description": "Structured log, probe of the save guard of peaking: event pk_guard. The guard of "
                       "patches/peaking-save-guard.json writes 2 to the latch byte L while it holds the lines back. "
                       "The probe reads L at each focus-ring event while MF Assist is on (the handler "
                       "rcvStartMFAssistIn_MFAssistOn of the MF Assist state object) and writes one record per hold: "
                       "the heap mode, and the units in use in the pool of the heap modes 0 and 2, which is the "
                       "reason for the hold. A hold with no ring event after its start gives no pk_guard record; "
                       "pk_latch shows every hold (L = 2). One hook in stock bytes of segment 2 and its routine in "
                       "segment 2; no byte of the peaking code changes. Needs log-core, log-probes and "
                       "log-peaking-time before it: every expect is a byte string of that build. It puts the build "
                       "id %s of logs/events.json into the block header. DEBUG builds only. See "
                       "experiments/2026-11-14-focus-peaking/NOTES.md section 18 and docs/logging.md." % bid.hex(),
        "base": STOCK, "base_sha256": hashlib.sha256(open(os.path.join(ROOT, STOCK), "rb").read()).hexdigest(),
        "status": "candidate: emulator-checked, not flashed",
        "_delta_on": "builds/debug-log-peaking-fast-2.json without this spec",
        "_build_id": bid.hex(),
        "_ram": "1 byte of the log's state block (PST+100)",
        "ops": ops,
    }, open(out, "w"), indent=1)
    open(out, "a").write("\n")
    print("wrote", os.path.relpath(out, ROOT), len(ops), "ops; build id", bid.hex())
    if listing:
        txt = run(BIN + "/mn10300-elf-objdump", "-d", "-j", ".gu", "-j", ".hs", e)
        open(listing, "w").write(re.sub(r"/[^\s:]*logguard\.elf", "logguard.elf", txt))


PCREL = re.compile(r"^(b[a-z]{1,2}|jmp|calls|call|ret|retf|rets|rti|l[a-z]{2}|setlb|trap)$")


def run(*a):
    return subprocess.run(a, check=True, capture_output=True, text=True).stdout


def build_id(events):
    """First 8 bytes of the sha256 of the id, name, level and args of every event (the decoder computes the same
    value; the other keys are notes)."""
    text = json.dumps([{k: e.get(k) for k in ("id", "name", "level", "args")} for e in events], sort_keys=True,
                      separators=(",", ":"))
    return hashlib.sha256(text.encode()).digest()[:8]


def displaced(blk_path, site, n):
    """The replaced instructions as assembler text: a `call` by its target, everything else as bytes."""
    txt = run(BIN + "/mn10300-elf-objdump", "-D", "-b", "binary", "-m", "mn10300", "--adjust-vma=%#x" % BASE,
              "--start-address=%#x" % site, "--stop-address=%#x" % (site + n + 8), blk_path)
    out, addr = [], site
    rows = []
    for l in txt.splitlines():
        m = re.match(r"^\s*([0-9a-f]{8}):\t((?:[0-9a-f]{2} )+)\s*(?:\t(\S+)\s*(.*))?$", l)
        if m:
            rows.append([int(m.group(1), 16), bytes.fromhex(m.group(2).replace(" ", "")), m.group(3), (m.group(4) or "").strip()])
    insns = []
    for a, b, mn, ops in rows:               # objdump wraps long instructions: join the continuation rows
        if mn is None:
            insns[-1][1] += b
        else:
            insns.append([a, b, mn, ops])
    for a, b, mn, ops in insns:
        if a >= site + n:
            break
        assert a == addr, "0x%X: not on an instruction boundary" % site
        if mn == "call":
            m = re.match(r"^0x([0-9a-f]{8}),(\[[^\]]*\]),(\d+)$", ops)
            assert m, ops
            out.append("    call 0x%s,%s,%s            # replaced instruction" % m.groups())
        else:
            assert not PCREL.match(mn), "0x%X: %s is pc-relative" % (a, mn)
            out.append("    .byte %s    # replaced: %s %s" % (", ".join("0x%02x" % x for x in b), mn, ops))
        addr += len(b)
    assert addr == site + n, "0x%X: %d bytes do not end on an instruction boundary" % (site, n)
    return "\n".join(out)


def branch_targets_inside(ranges, blk, work):
    """Addresses inside the replaced ranges (not their first byte) that an instruction of the function map or of
    the linear sweep names, or that a 4-byte word of block 0 holds. One `grep -F` pass per listing."""
    inner = sorted({a for site, n in ranges for a in range(site + 1, site + n)})
    pat = os.path.join(work, "targets.txt")
    open(pat, "w").write("".join("%08x <\n0x%08x\n" % (a, a) for a in inner))
    hits = []
    for fn in MAPS:
        r = subprocess.run(["grep", "-F", "-f", pat, fn], capture_output=True, text=True)
        hits += [l.strip()[:90] for l in r.stdout.splitlines()]
    for a in inner:
        i = blk.find(struct.pack("<I", a))
        if i >= 0:
            hits.append("word 0x%08X at 0x%X" % (a, BASE + i))
    return hits


def main():
    pinned, work = sys.argv[1:3]
    listing = sys.argv[3] if len(sys.argv) > 3 else None
    os.makedirs(work, exist_ok=True)
    blk_path = os.path.join(pinned, "block0_0100.bin")
    blk = open(blk_path, "rb").read()
    d = json.load(open(os.path.join(ROOT, "logs/events.json")))
    assert d["record_size"] == 16
    ev = {e["name"]: e["id"] for e in d["events"]}
    assert len(ev) == len(d["events"]) == len({e["id"] for e in d["events"]})
    bid = build_id(d["events"])
    val = dict(ev, mask=RING_RECORDS - 1, n=RING_RECORDS, per=BLOCK_RECORDS, bid0=struct.unpack("<i", bid[:4])[0],
               bid1=struct.unpack("<i", bid[4:])[0])
    used = set()
    for name, (spec, site, n, events, _) in HOOKS.items():
        val["displaced_" + name] = displaced(blk_path, site, n)
        val["back_" + name] = "0x%08x" % (site + n)
        for e in events.split():
            assert [x for x in d["events"] if x["name"] == e][0]["spec"] == spec, e
            used.add(e)
    other = {e["name"] for e in d["events"] if e["spec"] in (TIME_SPEC, GUARD_SPEC)}
    assert used | {"flush"} | other == set(ev), sorted(set(ev) - used)
    asm = SYMS + (CORE_K + CORE_U + PROBES_K + PROBES_U) % val
    args = ["--defsym=s_%s=0x%s" % (a, a) for a in sorted(set(re.findall(r"(?:jmp|call)\s+0x([0-9a-f]{8})", asm)))]
    asm = re.sub(r"((?:jmp|call)\s+)0x([0-9a-f]{8})", r"\1s_\2", asm)
    label = {"ERR": "T_ERR", "BOOT": "T_BOOT", "GUI": "T_GUI"}
    for name, (_, site, n, _, _) in HOOKS.items():
        asm += '\n.section .h%s,"ax"\n    jmp %s\n' % (name, label.get(name, "T_" + name)) + "    nop\n" * (n - 5)
        args.append("--section-start=.h%s=%#x" % (name, site))
    for name, (lo, _, _, _) in AREAS.items():
        args.append("--section-start=%s=%#x" % (name, lo))
    s, o, e = (os.path.join(work, "log." + x) for x in ("s", "o", "elf"))
    open(s, "w").write(asm)
    run(BIN + "/mn10300-elf-as", "-o", o, s)
    run(BIN + "/mn10300-elf-ld", *args, "-e", "%#x" % AREAS[".kc"][0], "-o", e, o)
    sym = {l.split()[2]: int(l.split()[0], 16) for l in run(BIN + "/mn10300-elf-nm", e).splitlines() if len(l.split()) == 3}

    def sect(name):
        b = os.path.join(work, "sect.bin")
        run(BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", name, e, b)
        return open(b, "rb").read()

    def op(addr, new, note):
        off = addr - BASE
        expect = blk[off:off + len(new)]
        assert expect != new
        return {"type": "bytes", "block": 0, "offset": "0x%X" % off, "expect": expect.hex(), "new": new.hex(),
                "_addr": "0x%08X" % addr, "_note": note}

    bad = branch_targets_inside([(site, n) for _, site, n, _, _ in HOOKS.values()], blk, work)
    assert not bad, bad
    ops = {"log-core": [], "log-probes": []}
    report = []
    for name, (lo, hi, spec, what) in AREAS.items():
        b = sect(name)
        assert lo + len(b) <= hi, "%s: %d bytes, %d free" % (name, len(b), hi - lo)
        if b[-1] == blk[lo - BASE + len(b) - 1]:
            b += b"\xcb"                     # the free-space ledger counts only changed bytes: end on a nop
        if name.startswith(".k"):
            assert blk[lo - BASE:lo - BASE + len(b)] == b"\xff" * len(b), name
        ops[spec].append(op(lo, b, "new code, %s (%d B)" % (what, len(b))))
        report.append("%s %s: %d B at 0x%X-0x%X, %d B free after" % (spec, name, len(b), lo, lo + len(b), hi - lo - len(b)))
    for name, (spec, site, n, events, what) in HOOKS.items():
        h = sect(".h" + name)
        assert len(h) == n and h[0] == 0xDC, (name, h.hex())
        ops[spec].append(op(site, h, "hook %s (%s): jmp %s%s. %s" % (name, events, label.get(name, "T_" + name),
                                                                     " + nop" * (n - 5), what)))
    assert struct.unpack_from("<I", blk, TASK_ENTRY - BASE)[0] == TASK_ENTRY_OLD
    ops["log-core"].append(op(TASK_ENTRY, struct.pack("<I", sym["FLUSH"])[:3],
                              "CPU0 task table, row of id 0x90 (USRTEST_A, dormant in stock): entry 0x%08X -> FLUSH 0x%08X"
                              % (TASK_ENTRY_OLD, sym["FLUSH"])))
    stock_sha = hashlib.sha256(open(os.path.join(ROOT, STOCK), "rb").read()).hexdigest()
    text = {
        "log-core": "Structured log, core: log_put / log_chg / log_cnt write 16-byte records {u16 id, u16 sequence, "
                    "u32 time, u32 arg0, u32 arg1} into one RAM ring per CPU (512 records each, in RAM that no load or "
                    "clear touches, 0x7E4F9000-0x7E4FD2C0 through the uncached alias). They never call the file system. "
                    "Events: boot, firmware error (the recorder 0x7E426D4B), GUI state. The dormant task USRTEST_A becomes "
                    "the flush task: when the GUI enters a menu, playback or power-off state and the card is not being "
                    "written, it appends the new records to C:\\EPM2LOG.BIN in 512-byte blocks (stops at 4 MiB). DEBUG builds only.",
        "log-probes": "Structured log, probes of the features: peaking (MF Assist start and end, the L / R / L2 / C bytes, "
                      "heap mode, pass 9), six-axis art code, level gauge (Adjust mode and values), interval shooting "
                      "(start, frames, end, state bits), film looks (matrix stage, matrix table, curve handler), shooting "
                      "callbacks. Each probe is a hook and a small routine that calls the log core. Needs log-core. "
                      "DEBUG builds only.",
    }
    for spec in ops:
        out = os.path.join(ROOT, "patches", spec + ".json")
        json.dump({
            "name": spec,
            "description": text[spec] + " The event ids are in logs/events.json (build id %s). A delta on %s: every "
                           "expect is a byte string of that build. See experiments/2026-11-15-log/NOTES.md and "
                           "docs/logging.md." % (bid.hex(), PINNED),
            "base": STOCK, "base_sha256": stock_sha,
            "status": "candidate: emulator-checked, not flashed",
            "_delta_on": "%s (sha256 %s)" % (PINNED, PINNED_SHA),
            "_build_id": bid.hex(),
            "ops": ops[spec],
        }, open(out, "w"), indent=1)
        open(out, "a").write("\n")
        print("wrote", os.path.relpath(out, ROOT), len(ops[spec]), "ops")
    print("build id", bid.hex())
    print("\n".join(report))
    order = sorted((v, k) for k, v in sym.items() if re.match(r"^(T_|log_|FLUSH|PATH)", k))
    ends = {".kc": AREAS[".kc"][0] + len(sect(".kc")), ".kp": AREAS[".kp"][0] + len(sect(".kp")),
            ".uc": AREAS[".uc"][0] + len(sect(".uc")), ".up": AREAS[".up"][0] + len(sect(".up"))}
    for i, (a, k) in enumerate(order):
        nxt = order[i + 1][0] if i + 1 < len(order) else None
        end = min([x for x in list(ends.values()) + ([nxt] if nxt else []) if x > a])
        print("  %-10s 0x%08X %4d B" % (k, a, end - a))
    if listing:
        secs = sum((["-j", n] for n in list(AREAS) + [".h" + n for n in HOOKS]), [])
        txt = run(BIN + "/mn10300-elf-objdump", "-d", *secs, e)
        open(listing, "w").write(re.sub(r"/[^\s:]*log\.elf", "log.elf", txt))


CARD_SPEC = "log-card-read"
CARD_AREA = (0x7EBF2888, 0x7EBF2900)         # segment 2, the listed area 0x7EBF1090-0x7EBF3BAD: a run no spec ledgers (120 B)
CARD_SITE = (0x7EBF2C00, 5, "the flush task's entry (log-core): `movm [d2,d3,a2,a3],(sp)` / `add -64,sp`; task "
                            "USRTEST_A, started by T_GUI when the GUI enters a menu, playback or the power-off state")
CARD_ASM = """
.equ CRDONE, PST+104         # u8: the card file was read in this session (T_BOOT clears PST at every start)
.section .cr,"ax"
T_CRD:                       # the flush task's entry: once per session, read the first 16 bytes of C:\\EPM2LOOK.BIN
%(displaced)s
    movbu (CRDONE),d0
    cmp 0,d0
    bne 9f
    mov 1,d0
    movbu d0,(CRDONE)
    mov CRPATH,a0
    mov CRMODE,a1
    call 0x7e5c52dc,[],20    # fileif_fopen(path, "r") -> a0 = handle or 0
    mov a0,a3
    mov -1,d2                # bytes read; -1: the file did not open
    cmp 0,a3
    beq 8f
    mov BUF,a0
    mov 1,d0
    mov 16,d1
    mov a3,a1
    call 0x7e5c536f,[],24    # fileif_fread(a0 = buffer, d0 = 1, d1 = bytes, a1 = handle) -> bytes read
    mov d0,d2
    mov a3,a0
    call 0x7e5c5308,[],12    # fileif_fclose(a0 = handle)
8:  mov d2,d1                # arg0: bytes read
    mov (BUF),a0             # arg1: bytes 0-3 of the file (not the file's when it did not open)
    mov %(card_read)d,d0
    call log_put,[],0
9:  jmp %(back)s             # the flush task goes on (BUF is its block buffer: it fills it again)
CRPATH: .asciz "C:\\\\EPM2LOOK.BIN"
CRMODE: .asciz "r"
"""
LOOK_AREAS = {".cr": (0x7EBF2888, 0x7EBF2900), ".ca": (0x7EBF2B90, 0x7EBF2C00)}   # segment 2, runs no spec ledgers
LOOK_TABLE = 0x7ECB0988      # the art matrix of codes 71 and 80 (Pro 400H in films-12d), 9 x s16 (rows sum to 256)
LOOK_ASM = """
.equ CRDONE, PST+104         # u8: the card file was read in this session (T_BOOT clears PST at every start)
.equ LOOKMAGIC, 0x4b4f4f4c   # "LOOK", bytes 0-3 of the file
.equ TABLE,  %(table)s       # the art matrix in RAM (cached address); +0x40000000 its uncached alias
.section .cr,"ax"
T_CRD:                       # the flush task's entry: once per session, read the first 32 bytes of C:\\\\EPM2LOOK.BIN
%(displaced)s
    movbu (CRDONE),d0
    cmp 0,d0
    bne 9f
    mov 1,d0
    movbu d0,(CRDONE)
    mov CRPATH,a0
    mov CRMODE,a1
    call 0x7e5c52dc,[],20    # fileif_fopen(path, "r") -> a0 = handle or 0
    mov a0,a3
    mov -1,d2                # bytes read; -1: the file did not open
    cmp 0,a3
    beq 8f
    mov BUF,a0
    mov 1,d0
    mov 32,d1
    mov a3,a1
    call 0x7e5c536f,[],24    # fileif_fread(a0 = buffer, d0 = 1, d1 = bytes, a1 = handle) -> bytes read
    mov d0,d2
    mov a3,a0
    call 0x7e5c5308,[],12    # fileif_fclose(a0 = handle)
8:  jmp T_APL                # d2 = bytes read
9:  jmp %(back)s             # the flush task goes on (BUF is its block buffer: it fills it again)
CRPATH: .asciz "C:\\\\EPM2LOOK.BIN"
CRMODE: .asciz "r"
.section .ca,"ax"
T_APL:                       # log the read; a file of 26 bytes or more that starts with "LOOK": its bytes 8-25 are
    mov d2,d1                # the 9 matrix values. arg0: bytes read
    mov (BUF),a0             # arg1: bytes 0-3 of the file (not the file's when it did not open)
    mov %(card_read)d,d0
    call log_put,[],0
    clr d3                   # values written
    cmp 26,d2
    blt 7f
    mov (BUF),d0
    cmp LOOKMAGIC,d0
    bne 7f
    mov BUF+8,a0
    mov TABLE,a1
    mov 9,d3
1:  movhu (a0),d0
    movhu d0,(a1)            # the cached address: what this CPU's cache holds
    mov a1,a2
    add 0x40000000,a2
    movhu d0,(a2)            # the uncached alias: what is in RAM
    add 2,a0
    add 2,a1
    add -1,d3
    bne 1b
    mov 9,d3
7:  mov d3,d1                # arg0: values written (0: the file is not a look)
    mov (TABLE+0x40000000),a0    # arg1: values 0 and 1 of the table, read back through the uncached alias
    mov %(card_look)d,d0
    call log_put,[],0
    jmp %(back)s
"""


LOOK_SPEC = "log-card-look"
LOOK_DESCRIPTION = ("Structured log, probe 2 of looks loaded from the card: at the first flush of a session (the GUI "
                    "enters a menu, playback or the power-off state) the flush task reads the first 32 bytes of "
                    "C:\\EPM2LOOK.BIN and writes card_read (bytes read, -1 when the file did not open; bytes 0-3). "
                    "When the file has 26 bytes or more and starts with LOOK, its bytes 8-25 (9 x s16) are written "
                    "into the art matrix of codes 71 and 80 (Pro 400H) at 0x7ECB0988, through the cached address and "
                    "its uncached alias, and card_look gives the number of values written and values 0 and 1 read "
                    "back from RAM. The colour stage that reads the table runs on CPU 1. Then the flush runs as "
                    "before. One hook at the flush task's entry (log-core's code) and two routines in free runs of "
                    "segment 2. In place of log-card-read, on the specs of builds/debug-log-films-12d.json. It puts "
                    "the build id %s of logs/events.json into the block header. DEBUG builds only. See "
                    "experiments/2026-11-17-card-looks/NOTES.md.")


PROBE_SPEC = "log-card-probe"
PROBE_DESCRIPTION = ("Structured log, the probe harness of looks loaded from the card: at the first flush of a session "
                     "(the GUI enters a menu, playback or the power-off state) the flush task reads up to 2 KB of "
                     "C:\\EPM2LOOK.BIN (card_read). A file that starts with LKP1 holds a count, flags and records "
                     "{u32 address, u16 length, u16 0, bytes, padded to 4}; a record is written (cached address and "
                     "uncached alias) only when it lies inside one of the tables of the Pale&Light Color slot (Pro "
                     "400H: three tone tables, saturation pair, six-axis records, art matrix, chroma record), and "
                     "card_rec logs each record (address, length | status << 16: 0 written, 1 refused). Flag bit 0 "
                     "stores 0 into the IMG library's builder words 0xA07500B4 / 0xA07500B8 and 0xFF into the "
                     "gamma states' art-code bytes, as the boot init does, so the look stages recompute. card_done "
                     "gives the records written and the flags. Then the flush runs as before. In place of "
                     "log-card-look, on the specs of builds/debug-log-films-12d.json. It puts the build id %s of "
                     "logs/events.json into the block header. DEBUG builds only. See "
                     "experiments/2026-11-17-card-looks/design.md section 8.")
# runs of segment 2 that no spec ledgers (docs/code-space-map.md; the segment-3 tail is for data only)
PROBE_AREAS = {".cr": (0x7EBF2888, 0x7EBF2900), ".ca": (0x7EBF2B90, 0x7EBF2C00), ".p3": (0x7EBF2A8C, 0x7EBF2B00),
               ".p4": (0x7EBF3B10, 0x7EBF3B52), ".p5": (0x7EBF1090, 0x7EBF10FC)}   # segment 2 only: code space
# the tables of the Pale&Light Color slot (Pro 400H, codes 71 and 80; src/epm2mod/looks/slots.py): start, length
PROBE_ALLOW = [(0x7F033B7C, 512), (0x7F033D7C, 512), (0x7E75E8F0, 512), (0x7E7696A4, 4), (0x7E76949E, 24),
               (0x7ECB0988, 18), (0x7E74B91C, 97)]
PROBE_ASM = """
.equ CRDONE, PST+104         # u8: the card file was read in this session (T_BOOT clears PST at every start)
.equ PBUF,   0xbe4fd400      # 2 KB read buffer: the end of the RAM gap 0x7E4C9800-0x7E4FE000 that the log uses
.equ PBUFN,  2048
.equ PMAGIC, 0x31504b4c      # "LKP1"
.equ BUILDER_STILL, 0xa07500b4   # the IMG library's builder words: 0 makes the next job clear the stage cache
.equ BUILDER_LV,    0xa07500b8   # (the boot init 0x7E560AC0 writes 0 into both)
.equ GAMMA_STILL,   0x60510cd5   # the art-code byte of the two gamma states (0x605106A8 + 1581, 0x60510CD8 + 1581):
.equ GAMMA_LV,      0x60511305   # 0xFF makes the next job rebuild the gamma copy
# Frame slots (the flush task's 64-byte frame, which it fills itself after this code; not (0,sp), which every `call`
# overwrites with its return address): (16,sp) end of the data read, (20,sp) records left while a record is copied,
# (24,sp) the file's flags
.section .cr,"ax"
T_CRD:                       # the flush task's entry: once per session, read up to 2 KB of C:\\\\EPM2LOOK.BIN
%(displaced)s
    movbu (CRDONE),d0
    cmp 0,d0
    bne 9f
    mov 1,d0
    movbu d0,(CRDONE)
    mov CRPATH,a0
    mov CRMODE,a1
    call 0x7e5c52dc,[],20    # fileif_fopen(path, "r") -> a0 = handle or 0
    mov a0,a3
    mov -1,d2                # bytes read; -1: the file did not open
    cmp 0,a3
    beq 8f
    mov PBUF,a0
    mov 1,d0
    mov PBUFN,d1
    mov a3,a1
    call 0x7e5c536f,[],24    # fileif_fread(a0 = buffer, d0 = 1, d1 = bytes, a1 = handle) -> bytes read
    mov d0,d2
    mov a3,a0
    call 0x7e5c5308,[],12    # fileif_fclose(a0 = handle)
8:  jmp T_HDR
9:  jmp %(back)s
CRPATH: .asciz "C:\\\\EPM2LOOK.BIN"
CRMODE: .asciz "r"

.section .ca,"ax"
T_HDR:                       # log the read; check the header: "LKP1", u16 count, u16 flags (bit 0: force a refresh)
    mov d2,d1
    mov (PBUF),a0
    mov %(card_read)d,d0
    call log_put,[],0
    clr d3                   # records written
    clr d0
    mov d0,(24,sp)
    cmp 8,d2
    blt 7f
    mov (PBUF),d0
    cmp PMAGIC,d0
    bne 7f
    movhu (PBUF+6),d0
    mov d0,(24,sp)
    mov PBUF,d0
    add d2,d0
    mov d0,(16,sp)
    movhu (PBUF+4),d0
    mov d0,a3
    mov PBUF+8,a2
T_NEXT:                      # a record: u32 address, u16 length, u16 0, the bytes, padded to 4
    cmp 0,a3
    beq 7f
    mov a2,d0
    add 8,d0
    mov (16,sp),d1
    cmp d1,d0
    bhi 7f                   # its head runs past the data read: stop
    movhu (4,a2),d1
    add d1,d0
    mov (16,sp),d2
    cmp d2,d0
    bhi 7f                   # its bytes run past the data read: stop
    jmp T_CHK
7:  jmp T_FIN

.section .p3,"ax"
T_CHK:                       # inside one allowed table? length <= L and (address - start) <= L - length, unsigned
    mov ALLOW,a1
1:  mov (4,a1),d2            # L; 0 ends the list
    cmp 0,d2
    beq T_BAD
    cmp d1,d2
    bcs 2f                   # L < length
    sub d1,d2                # L - length
    mov (a2),d0
    mov (a1),a0
    sub a0,d0                # address - start (a huge value when the address is below the table)
    cmp d2,d0
    bls 6f
2:  add 8,a1
    bra 1b
6:  jmp T_OK
T_BAD:
    mov 1,d2                 # status 1: outside every allowed table, not written
    jmp T_LOG
    .balign 4                # word loads must be aligned
ALLOW:
%(allow)s
    .long 0, 0

.section .p4,"ax"
T_OK:                        # write the bytes through the cached address and its uncached alias
    mov a3,(20,sp)
    mov (a2),a0
    mov a0,a3
    add 0x40000000,a3
    mov a2,a1
    add 8,a1
3:  cmp 0,d1
    beq 4f
    movbu (a1),d0
    movbu d0,(a0)
    movbu d0,(a3)
    inc a0
    inc a1
    inc a3
    add -1,d1
    bra 3b
4:  mov (20,sp),a3
    inc d3
    clr d2                   # status 0: written
    jmp T_LOG

.section .p5,"ax"
T_LOG:                       # card_rec(address, length | status << 16); then the next record
    movhu (4,a2),d1
    mov d2,d0
    asl 16,d0
    or d1,d0
    mov d0,a0
    mov (a2),d1
    mov %(card_rec)d,d0
    call log_put,[],0
    movhu (4,a2),d0
    add 11,d0
    and 0xfffffffc,d0
    add d0,a2
    add -1,a3
    jmp T_NEXT
T_FIN:                       # flag bit 0: make the look stages recompute, as the boot init does
    mov (24,sp),d0
    and 1,d0
    beq 5f
    clr d0
    mov d0,(BUILDER_STILL)
    mov d0,(BUILDER_LV)
    mov 0xff,d0
    movbu d0,(GAMMA_STILL)
    movbu d0,(GAMMA_LV)
5:  mov d3,d1                # card_done(records written, the file's flags)
    mov (24,sp),a0
    mov %(card_done)d,d0
    call log_put,[],0
    jmp %(back)s
"""


KEEP_SPEC = "log-card-keep"
KEEP_AREAS = {".cr": (0x7EBF2888, 0x7EBF2900), ".ca": (0x7EBF2B90, 0x7EBF2C00), ".p3": (0x7EBF2A8C, 0x7EBF2B00),
              ".p4": (0x7EBF1090, 0x7EBF10FC), ".p5": (0x7EBF3B10, 0x7EBF3B52), ".p6": (0x7EBF29C0, 0x7EBF2A00)}
KEEP_LABELS = {".cr": "T_CRD", ".ca": "T_APL", ".p3": "T_KEEP", ".p4": "T_BANK", ".p5": "T_BSUM", ".p6": "T_BAPPLY"}
# the second hook: the entry of log-core's T_GUI (`movm [d2,other],(sp)` / `mov psw,d2` / `mov d0,d1`), which the GUI
# state setter's last trace call 0x7ECDF6E4 reaches (task CA_MAIN) at every GUI state
KEEP_HOOK2 = (0x7EBF2E0F, 5, "T_BANK", "log-core's T_GUI entry: at every GUI state (task CA_MAIN)")
KEEP_DESCRIPTION = ("Structured log, the persistence probe of looks loaded from the card. (1) At the first flush of a "
                    "session the flush task reads C:\\EPM2LOOK.BIN; a file that starts with LOOK (26 bytes or more) "
                    "sets the art matrix of Pro 400H (0x7ECB0988) as probe 2 did, stores a record LKB1 {u16 18, u16 sum "
                    "of the 18 bytes, the matrix} at 0x603FC000 in the unused tail of the EEROM settings bank, and calls "
                    "the bank save API 0x7E680272 (card_keep: its result, the sum). (2) At the first GUI state of every "
                    "session (log-core's T_GUI, task CA_MAIN), when the tail holds a valid LKB1 record, it writes its "
                    "matrix into the table (bank_look: status 0 applied, 1 no record, 2 bad length or sum; the table's "
                    "first two values). At the first flush, before the card file, it logs bank_tail (the number of nonzero "
                    "words in the unused tail 0x603F74B8-0x60404668, the first word of the record). The firmware saves the bank to flash itself (power-off, sleep, every start). In "
                    "place of log-card-look, on the specs of builds/debug-log-films-12d.json. It puts the build id %s "
                    "of logs/events.json into the block header. DEBUG builds only. See "
                    "experiments/2026-11-17-card-looks/design.md section 8 (P4, P5).")
KEEP_ASM = """
.equ CRDONE, PST+104         # u8: the card file was read in this session (T_BOOT clears PST at every start)
.equ BANKDONE, PST+105       # u8: the stored look was looked at in this session
.equ LOOKMAGIC, 0x4b4f4f4c   # "LOOK"
.equ KEEPMAGIC, 0x31424b4c   # "LKB1"
.equ TABLE,  0x7ecb0988      # the art matrix of codes 71 and 80 (Pro 400H), 9 x s16; +0x40000000 its uncached alias
.equ TAIL,   0x603fc000      # the record in the EEROM bank's tail (RAM image 0x603F4674-0x60404674)
.equ TAIL0,  0x603f74b8      # the unused tail: 0x603F74B8-0x60404668 (53,680 bytes)
.equ TAILN,  13420           # its words
.section .cr,"ax"
T_CRD:                       # the flush task's entry: once per session, read the first 32 bytes of C:\\\\EPM2LOOK.BIN
%(displaced)s
    movbu (CRDONE),d0
    cmp 0,d0
    bne 9f
    mov 1,d0
    movbu d0,(CRDONE)
    mov CRPATH,a0
    mov CRMODE,a1
    call 0x7e5c52dc,[],20    # fileif_fopen(path, "r") -> a0 = handle or 0
    mov a0,a3
    mov -1,d2                # bytes read; -1: the file did not open
    cmp 0,a3
    beq 8f
    mov BUF,a0
    mov 1,d0
    mov 32,d1
    mov a3,a1
    call 0x7e5c536f,[],24    # fileif_fread(a0 = buffer, d0 = 1, d1 = bytes, a1 = handle) -> bytes read
    mov d0,d2
    mov a3,a0
    call 0x7e5c5308,[],12    # fileif_fclose(a0 = handle)
8:  jmp T_SCAN
9:  jmp %(back)s
CRPATH: .asciz "C:\\\\EPM2LOOK.BIN"
CRMODE: .asciz "r"

.section .ca,"ax"
T_APL:                       # log the read; a look file: write the matrix (cached and uncached), then keep it
    mov d2,d1
    mov (BUF),a0
    mov %(card_read)d,d0
    call log_put,[],0
    cmp 26,d2
    blt 7f
    mov (BUF),d0
    cmp LOOKMAGIC,d0
    bne 7f
    mov BUF+8,a0
    mov TABLE,a1
    mov 9,d3
1:  movhu (a0),d0
    movhu d0,(a1)
    mov a1,a2
    add 0x40000000,a2
    movhu d0,(a2)
    add 2,a0
    add 2,a1
    add -1,d3
    bne 1b
    jmp T_KEEP
7:  jmp %(back)s

.section .p3,"ax"
T_KEEP:                      # the record LKB1 {u16 18, u16 sum, 18 bytes} into the tail, then the bank save
    mov BUF+8,a0
    mov TAIL+8,a1
    clr d2                   # the sum of the 18 bytes, 16 bits
    mov 18,d3
1:  movbu (a0),d0
    movbu d0,(a1)
    add d0,d2
    inc a0
    inc a1
    add -1,d3
    bne 1b
    mov 18,d0
    movhu d0,(TAIL+4)
    movhu d2,(TAIL+6)
    mov KEEPMAGIC,d0
    mov d0,(TAIL)            # the magic last: a record without it is never applied
    call 0x7e680272,[],48    # the bank save API (EEROM and MODE): the firmware writes the changed bank to flash
    mov d0,d1                # card_keep(the save's result, the sum)
    mov d2,a0
    mov %(card_keep)d,d0
    call log_put,[],0
    jmp %(back)s
T_BLOG:
    mov (TABLE+0x40000000),a0
    mov %(bank_look)d,d0
    call log_put,[],0        # bank_look(status, the table's first two values from RAM)
T_BEND:
    mov d2,psw
    nop
    nop
    movm (sp),[d2,d3,a2,a3,other]
%(displaced2)s
    jmp %(back2)s

.section .p4,"ax"
T_BANK:                      # at the first GUI state of a session: apply a stored look (RAM only: no file, no scan)
    movm [d2,d3,a2,a3,other],(sp)
    mov psw,d2
    movbu (BANKDONE),d0
    cmp 0,d0
    bne 9f
    mov 1,d0
    movbu d0,(BANKDONE)
    mov 1,d1                 # status 1: no record
    mov (TAIL),d0
    cmp KEEPMAGIC,d0
    bne 8f
    mov 2,d1                 # status 2: bad length or sum
    movhu (TAIL+4),d0
    cmp 18,d0
    bne 8f
    jmp T_BSUM
8:  jmp T_BLOG
9:  jmp T_BEND
T_SCAN:                      # the flush task, first flush of a session, before the card file is looked at: the tail
    mov TAIL0,a0             # nonzero words in the tail (d2, the bytes read, is kept)
    mov TAILN,d3
    clr d1
1:  mov (a0),d0
    cmp 0,d0
    beq 2f
    inc d1
2:  inc4 a0
    add -1,d3
    bne 1b
    mov (TAIL),a0
    mov %(bank_tail)d,d0
    call log_put,[],0        # bank_tail(nonzero words, the record's first word)
    jmp T_APL

.section .p5,"ax"
T_BSUM:
    mov TAIL+8,a0
    clr d3
    mov 18,a3
3:  movbu (a0),d0
    add d0,d3
    inc a0
    add -1,a3
    bne 3b
    movhu (TAIL+6),d0
    exthu d3
    cmp d0,d3
    bne 8f
    jmp T_BAPPLY
8:  jmp T_BLOG

.section .p6,"ax"
T_BAPPLY:
    mov TAIL+8,a0            # apply: the 9 values into the table, cached and uncached
    mov TABLE,a1
    mov 9,d3
4:  movhu (a0),d0
    movhu d0,(a1)
    mov a1,a2
    add 0x40000000,a2
    movhu d0,(a2)
    add 2,a0
    add 2,a1
    add -1,d3
    bne 4b
    clr d1                   # status 0: applied
    jmp T_BLOG
"""


def card_read(spec=CARD_SPEC, asm_text=CARD_ASM, areas={".cr": CARD_AREA}, events=("card_read",), extra=None, hook2=None):
    """Write patches/log-card-read.json, or with the other arguments patches/log-card-look.json (see the usage text)."""
    base, work = sys.argv[2:4]
    listing = sys.argv[4] if len(sys.argv) > 4 else None
    os.makedirs(work, exist_ok=True)
    blk_path = os.path.join(base, "block0_0100.bin")
    blk = open(blk_path, "rb").read()
    get = lambda a, n: blk[a - BASE:a - BASE + n]
    d = json.load(open(os.path.join(ROOT, "logs/events.json")))
    mine = {e["name"]: e["id"] for e in d["events"] if e["name"] in events}
    assert sorted(mine) == sorted(events), mine
    bid = build_id(d["events"])
    old = bytes.fromhex(json.load(open(os.path.join(ROOT, "patches", GUARD_SPEC + ".json")))["_build_id"])
    lo = AREAS[".kc"][0]
    head = bytes.fromhex("cff0f2e6")
    at = [lo + i for i in range(0x40) if get(lo + i, 4) == head]
    assert len(at) == 3 and get(at[2] + 4, 4) == bytes.fromhex("fafcfff7"), at     # log_put: and 0xf7ff,psw
    site, n, what = CARD_SITE
    assert get(site, n) == bytes.fromhex("cff0f8fec0"), get(site, n).hex()           # log-core's flush entry
    assert struct.unpack("<I", get(TASK_ENTRY, 4))[0] == site                        # USRTEST_A's entry word
    sites = [(site, n)] + ([hook2[:2]] if hook2 else [])
    bad = branch_targets_inside(sites, blk, work)
    assert not bad, bad
    subs = {**mine, **(extra or {}), "displaced": displaced(blk_path, site, n), "back": "0x%08x" % (site + n)}
    if hook2:                                # (site, bytes, routine, what): the second hook's displaced code and return
        subs.update(displaced2=displaced(blk_path, hook2[0], hook2[1]), back2="0x%08x" % (hook2[0] + hook2[1]))
    asm = SYMS + asm_text % subs
    args = ["--defsym=log_put=%#x" % at[2]]
    args += ["--defsym=s_%s=0x%s" % (x, x) for x in sorted(set(re.findall(r"(?:jmp|call)\s+0x([0-9a-f]{8})", asm)))]
    asm = re.sub(r"((?:jmp|call)\s+)0x([0-9a-f]{8})", r"\1s_\2", asm)
    asm += '\n.section .hs,"ax"\n    jmp T_CRD\n' + "    nop\n" * (n - 5)
    args += ["--section-start=.hs=%#x" % site] + ["--section-start=%s=%#x" % (k, a) for k, (a, _) in areas.items()]
    if hook2:
        asm += '\n.section .h2,"ax"\n    jmp %s\n' % hook2[2] + "    nop\n" * (hook2[1] - 5)
        args += ["--section-start=.h2=%#x" % hook2[0]]
    s, o, e, sb = (os.path.join(work, "logcard." + x) for x in ("s", "o", "elf", "bin"))
    open(s, "w").write(asm)
    run(BIN + "/mn10300-elf-as", "-o", o, s)
    run(BIN + "/mn10300-elf-ld", *args, "-e", "%#x" % areas[".cr"][0], "-o", e, o)

    def sect(name):
        run(BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", name, e, sb)
        return open(sb, "rb").read()

    ops = []

    def op(addr, new, note):
        expect = get(addr, len(new))
        assert expect != new, note
        ops.append({"type": "bytes", "block": 0, "offset": "0x%X" % (addr - BASE), "expect": expect.hex(),
                    "new": new.hex(), "_addr": "0x%08X" % addr, "_note": note})

    stock = open(os.path.join(ROOT, "build/blocks", os.path.basename(STOCK) + ".block0.bin"), "rb").read()
    for name, (a, hi) in areas.items():
        code = sect(name)
        label = (KEEP_LABELS if spec == KEEP_SPEC else
                 {".cr": "T_CRD", ".ca": "T_HDR" if spec == PROBE_SPEC else "T_APL", ".p3": "T_CHK", ".p4": "T_OK",
                  ".p5": "T_LOG"})[name]
        assert a + len(code) <= hi and get(a, hi - a) == stock[a - BASE:hi - BASE], "the area is in use"
        if code[-1] == get(a + len(code) - 1, 1)[0]:
            code += b"\xcb"                  # the free-space ledger counts only changed bytes: end on a nop
        op(a, code, "new code, segment 2: %s (%d B)" % (label, len(code)))
        print("%s: %d B at 0x%X-0x%X, %d B free after" % (label, len(code), a, a + len(code), hi - a - len(code)))
    h = sect(".hs")
    assert len(h) == n and h[0] == 0xDC
    op(site, h, "hook (card_read): jmp T_CRD. %s" % what)
    if hook2:
        h2 = sect(".h2")
        assert len(h2) == hook2[1] and h2[0] == 0xDC
        op(hook2[0], h2, "hook: jmp %s. %s" % (hook2[2], hook2[3]))
    assert bid != old
    for half in (0, 4):                      # the two `mov imm32,d0` of the flush task that hold the build id
        word = b"\xfc\xcc" + old[half:half + 4]
        i = blk.find(word)
        assert i >= 0 and blk.find(word, i + 1) < 0 and AREAS[".uc"][0] <= BASE + i < AREAS[".uc"][1], half
        op(BASE + i + 2, bid[half:half + 4], "flush task, block header: build id bytes %d-%d %s -> %s (logs/events.json)"
           % (half, half + 3, old[half:half + 4].hex(), bid[half:half + 4].hex()))
    out = os.path.join(ROOT, "patches", spec + ".json")
    json.dump({
        "name": spec,
        "description": (LOOK_DESCRIPTION % bid.hex()) if spec == LOOK_SPEC else (PROBE_DESCRIPTION % bid.hex()) if spec == PROBE_SPEC else (KEEP_DESCRIPTION % bid.hex()) if spec == KEEP_SPEC else ("Structured log, the card-read probe: at the first flush of a session (the GUI enters a menu, "
                       "playback or the power-off state) the flush task opens C:\\EPM2LOOK.BIN with mode r, reads its "
                       "first 16 bytes with fileif_fread (0x7E5C536F), closes it, and writes the event card_read "
                       "(bytes read, -1 when the file did not open; bytes 0-3 of the file). Then the flush runs as before. One hook at the flush task's entry (log-core's "
                       "code, not stock) and its routine after the flush task. Needs the specs of "
                       "builds/debug-log-films-12d.json before it: every expect is a byte string of that build. It "
                       "puts the build id %s of logs/events.json into the block header. DEBUG builds only. See "
                       "experiments/2026-11-17-card-looks/NOTES.md and docs/logging.md." % bid.hex()),
        "base": STOCK, "base_sha256": hashlib.sha256(open(os.path.join(ROOT, STOCK), "rb").read()).hexdigest(),
        "status": "candidate: emulator-checked, not flashed",
        "_delta_on": "builds/debug-log-films-12d.json",
        "_build_id": bid.hex(),
        "_ram": "1 byte of the log's state block (PST+104); the flush task's block buffer for the read",
        "ops": ops,
    }, open(out, "w"), indent=1)
    open(out, "a").write("\n")
    print("wrote", os.path.relpath(out, ROOT), len(ops), "ops; build id", bid.hex())
    if listing:
        txt = run(BIN + "/mn10300-elf-objdump", "-d", *sum((["-j", k] for k in areas), []), "-j", ".hs", *(["-j", ".h2"] if hook2 else []), e)
        open(listing, "w").write(re.sub(r"/[^\s:]*logcard\.elf", "logcard.elf", txt))


if len(sys.argv) > 1 and sys.argv[1] == "--peaking-time":
    peaking_time()
elif len(sys.argv) > 1 and sys.argv[1] == "--card-read":
    card_read()
elif len(sys.argv) > 1 and sys.argv[1] == "--card-probe":
    card_read(PROBE_SPEC, PROBE_ASM, PROBE_AREAS, ("card_read", "card_rec", "card_done"),
              {"allow": "\n".join("    .long %#x, %d" % a for a in PROBE_ALLOW)})
elif len(sys.argv) > 1 and sys.argv[1] == "--card-keep":
    card_read(KEEP_SPEC, KEEP_ASM, KEEP_AREAS, ("card_read", "card_keep", "bank_tail", "bank_look"), None, KEEP_HOOK2)
elif len(sys.argv) > 1 and sys.argv[1] == "--card-look":
    card_read(LOOK_SPEC, LOOK_ASM, LOOK_AREAS, ("card_read", "card_look"), {"table": "%#x" % LOOK_TABLE})
elif len(sys.argv) > 1 and sys.argv[1] == "--peaking-guard":
    peaking_guard()
else:
    main()
