# Lowest S/S Setting for the E-PM2, as the PEN-F 3.1 does it (NOTES.md section 4.1, 9).
# Placed in the space of the exp debug printers 0x7E69E9EA-0x7E69EEAF (segment 1; reached only from the shell
# command "exp still info", which is cut at 0x7E69E92A). Entry points:
#   NEWTH   replaces the call of tv_th 0x7E694001 at 0x7E693D4B (PEN-F 0x605B97B0)
#   NEWAUTO replaces the call of the auto path 0x7E6947C1 at 0x7E694610 (PEN-F 0x605BA4B9 segments 5 and 6)
#   GATE    PEN-F 0x605BB441 + 0x605D344E: the limit in Q8 Tv, or 0x7FFF when it does not apply
        .text
        .global _start
        .equ SETTING, 0x60413225        # setting 653 (tag 0x9F11): 0 Auto, 1 = 60 s ... 55 = 1/4000 (1/3 EV)
        # LOG2: --defsym in mkspec.py # 256 * log2(d0)
        # PRM: --defsym in mkspec.py # settings read (d0 = tag, a0 = 0, d1 = 0)
        # F_SV: --defsym in mkspec.py # per-ISO correction f(Sv) (a0 = mode block, d0 = Sv)
        # BUILD: --defsym in mkspec.py # 8 breakpoints of the program line
        # AUTO: --defsym in mkspec.py # stock auto path
        # SEG_T: --defsym in mkspec.py # stock segment: shutter falls at Sv c16, Av c10
        # SEG_S: --defsym in mkspec.py # stock segment: ISO rises at hold c24, Av c10
_start:

# NEWTH(a0 = mode block, d0 = focal length, a2 = argument list of exp_cal_still) -> d0 = tv_th (the STOCK corner)
NEWTH:
        mov     (4,a2),a1               # set block
        mov     a1,(12,sp)
        mov     a0,a2
        asl     14,d0
        call    LOG2,[d2,d3],12
        exth    d0
        mov     d0,d2                   # t = 1/(2 x focal length)
        movhu   (24,a2),d1              # Flash Slow Limit
        exth    d1
        cmp     d1,d2
        bge     1f
        mov     d1,d2
1:      cmp     1280,d2                 # not slower than 1/30; no cap below it
        bgt     2f
        mov     1280,d2
        bra     4f
2:      movbu   (6,a2),d0               # flash on: the sync speed of the flash (+16)
        cmp     1,d0
        bne     3f
        movhu   (16,a2),d1
        bra     5f
3:      mov     0x94BA,d0               # flash off: the X-Sync setting
        mov     0,a0
        clr     d1
        call    PRM,[d2,d3],12
        mov     d0,d1
5:      exth    d1
        cmp     d1,d2
        ble     4f
        mov     d1,d2
4:      mov     a2,a0
        mov     (12,sp),a1
        call    GATE,[],4
        exth    d0
        cmp     32767,d0
        beq     6f
        cmp     d0,d2                   # active: at least the Lowest S/S
        bge     6f
        mov     d0,d2
6:      mov     d2,d0
        ret     [d2,d3,a2,a3],32

# GATE(a0 = mode block, a1 = set block) -> d0. Leaf; returns with ret (div and ext overwrite MDR).
GATE:
        movbu   (6,a0),d0               # stb_onoff
        cmp     0,d0
        bne     9f
        movbu   (3,a0),d0               # mode: P or A
        cmp     3,d0
        beq     1f
        cmp     4,d0
        bne     9f
1:      movhu   (2,a1),d0               # sv: 0 = ISO Auto
        cmp     0,d0
        bne     9f
        movbu   (SETTING),d0
        cmp     0,d0
        beq     9f
        cmp     55,d0
        bhi     9f
        add     -19,d0                  # Q8 Tv = trunc(256 (i - 19) / 3): the PEN-F 1/3 EV table
        asl     8,d0
        mov     3,d1
        ext     d0
        div     d1,d0
        movhu   (10,a1),d1              # exposure step: 1/2 EV or 1 EV rounds up to the step
        cmp     128,d1
        beq     2f
        cmp     256,d1
        bne     3f
2:      add     -1,d1
        add     d1,d0
        not     d1
        and     d1,d0
3:      ret     [],4
9:      mov     32767,d0
        ret     [],4

# NEWAUTO(a0 = result, a1 = mode block, d0 = set block, d1 = corner block); called as [d2,d3,a2,a3],76 (registers at 60..75)
# Corner block: +2 BV, +10 Av, +16/+18 Sv, +22 fastest Tv, +24 hold (STOCK), +26 slowest Tv.
# Locals: (20) set, (28..43) breakpoints, (44) flag, (48) Lc, (50) BP5', (52) saved field, (54) f(c16)
NEWAUTO:
        mov     a0,d3
        mov     a1,a3
        mov     d1,a2
        mov     d0,(20,sp)
        mov     a3,a0
        mov     d0,a1
        call    GATE,[],4
        exth    d0
        cmp     32767,d0
        bne     1f
        jmp     STOCK
1:      movhu   (26,a2),d1              # Lc = clamp(L, slowest, fastest)
        exth    d1
        cmp     d1,d0
        bge     2f
        mov     d1,d0
2:      movhu   (22,a2),d1
        exth    d1
        cmp     d1,d0
        ble     3f
        mov     d1,d0
3:      movhu   d0,(48,sp)
        mov     sp,a0                   # breakpoints with the hold STOCK
        add     28,a0
        mov     a0,d0
        mov     sp,a0
        add     44,a0
        mov     a0,d1
        mov     a3,a0
        mov     a2,a1
        call    BUILD,[d2,d3,a2,a3],52
        movhu   (2,a2),d2               # BV
        exth    d2
        movhu   (36,sp),d0              # BP4
        exth    d0
        cmp     d0,d2
        bgt     STOCK
        mov     a3,a0                   # f(c16)
        movhu   (16,a2),d0
        exth    d0
        call    F_SV,[d2],8
        exth    d0
        movhu   d0,(54,sp)
        movhu   (10,a2),d1              # BP5' = c10 + Lc - c18 - f(c16)
        exth    d1
        movhu   (48,sp),d0
        exth    d0
        add     d0,d1
        movhu   (18,a2),d0
        exth    d0
        sub     d0,d1
        movhu   (54,sp),d0
        exth    d0
        sub     d0,d1
        exth    d1
        movhu   d1,(50,sp)
        cmp     d1,d2
        ble     SEG6
        movhu   (16,a2),d0              # segment 5: shutter falls at the base ISO c18
        movhu   d0,(52,sp)
        movhu   (18,a2),d0
        movhu   d0,(16,a2)
        mov     d3,d0
        mov     a2,a1
        mov     a3,a0
        call    SEG_T,[d2,d3,a2,a3],32
        movhu   (52,sp),d0
        movhu   d0,(16,a2)
        ret     [d2,d3,a2,a3],76
SEG6:   movhu   (10,a2),d1              # BP6' = c10 + Lc - c16 - f(c16)
        exth    d1
        movhu   (48,sp),d0
        exth    d0
        add     d0,d1
        movhu   (16,a2),d0
        exth    d0
        sub     d0,d1
        movhu   (54,sp),d0
        exth    d0
        sub     d0,d1
        exth    d1
        cmp     d1,d2
        ble     STOCK
        movhu   (24,a2),d0              # segment 6 (PEN-F 0x605BAB3D): ISO rises at Lc
        movhu   d0,(52,sp)
        movhu   (48,sp),d0
        movhu   d0,(24,a2)              # hold := Lc
        mov     1,d0
        movhu   d0,(56,sp)              # fake set block at sp+42: its +14 is not 0, so 0x7E694ED1 does not round
        mov     a2,(4,sp)
        mov     d3,(8,sp)
        mov     sp,a0
        add     28,a0
        mov     a0,d1
        mov     sp,a1
        add     42,a1
        movhu   (44,sp),d0
        mov     a3,a0
        call    SEG_S,[d2,d3,a2,a3],44
        movhu   (52,sp),d0
        movhu   d0,(24,a2)
        # the PEN-F rounding of Sv to 1/3 EV, 0x605BABE3-0x605BACE0. Result: +2 Tv, +4 Sv, +8 Av
        clr     d2                      # e = (BP5' == BP4)
        movhu   (50,sp),d0
        movhu   (36,sp),d1
        cmp     d1,d0
        bne     1f
        mov     1,d2
1:      movbu   d2,(58,sp)
        mov     d3,a1
        movhu   (4,a1),d2               # Sv before
        mov     d2,d0
        and     255,d0                  # fraction
        movbu   (3,a3),d1               # P with e: round up; else to the nearest
        cmp     3,d1
        bne     NEAR
        movbu   (58,sp),d1
        cmp     0,d1
        beq     NEAR
        clr     d1
        cmp     0,d0
        beq     RND
        mov     85,d1
        cmp     d1,d0
        ble     RND
        mov     170,d1
        cmp     d1,d0
        ble     RND
        mov     256,d1
        bra     RND
NEAR:   clr     d1
        cmp     42,d0
        blt     RND
        mov     85,d1
        cmp     127,d0
        blt     RND
        mov     170,d1
        cmp     212,d0
        blt     RND
        mov     256,d1
RND:    mov     d2,d0
        and     0xFF00,d0
        add     d1,d0
        movhu   d0,(4,a1)
        exth    d0
        exth    d2
        sub     d2,d0                   # d0 = the change of Sv
        movbu   (58,sp),d1
        cmp     0,d1
        beq     SHUT
        movbu   (3,a3),d1
        cmp     4,d1
        bne     PE
SHUT:   mov     (20,sp),a0              # 1/3 EV steps: keep the change within 42 by moving Sv back
        movhu   (10,a0),d1
        cmp     85,d1
        bne     TV
        cmp     0,d0
        bge     2f
        cmp     -42,d0
        bge     TV
        movhu   (4,a1),d1
        add     42,d0
        sub     d0,d1
        movhu   d1,(4,a1)
        mov     -42,d0
        bra     TV
2:      cmp     42,d0
        ble     TV
        movhu   (4,a1),d1
        add     -42,d0
        sub     d0,d1
        movhu   d1,(4,a1)
        mov     42,d0
TV:     movhu   (48,sp),d1              # the shutter takes the change
        add     d0,d1
        movhu   d1,(2,a1)
        ret     [d2,d3,a2,a3],76
PE:     movhu   (50,sp),d1              # P, BP5' = BP4
        exth    d1
        movhu   (34,sp),d2              # BP3
        exth    d2
        cmp     d2,d1
        bge     3f
        asr     1,d0                    # BP5' < BP3: half to the aperture, half to the shutter
        movhu   (10,a2),d1
        add     d0,d1
        movhu   d1,(8,a1)
        movhu   (48,sp),d1
        add     d0,d1
        movhu   d1,(2,a1)
        ret     [d2,d3,a2,a3],76
3:      bne     AV
        movhu   (32,sp),d2              # BP5' = BP3 and BP5' < BP2 and flag 1: the shutter
        exth    d2
        cmp     d2,d1
        bge     AV
        movhu   (44,sp),d1
        cmp     1,d1
        beq     TV
AV:     movhu   (10,a2),d1              # else the aperture
        add     d0,d1
        movhu   d1,(8,a1)
        ret     [d2,d3,a2,a3],76
STOCK:  mov     d3,a0
        mov     a3,a1
        mov     (20,sp),d0
        mov     a2,d1
        call    AUTO,[d2,d3,a2,a3],60
        ret     [d2,d3,a2,a3],76
