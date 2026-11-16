# Prototype: the tail of 0x7E694001 (the tv_th function of exp_cal_still), from 0x7E69400C.
# In: d0 = 256 * log2(35 mm-equivalent focal length) from 0x7E507DFD, a2 = the mode block.
# Out: d0 = tv_th. Stock: min(X-Sync, max(d0, 1/30, Flash Slow Limit)).
# New: max(d0, Flash Slow Limit, 1/30 * 2^k), k = the byte of setting 447; the X-Sync cap only with the flash on.
        .am33_2
        .text
        .global _start
_start:
        movhu   (24,a2),d1              # Flash Slow Limit (tag 0x9ABA)
        exth    d1
        cmp     d1,d0
        bge     1f
        mov     d1,d0
1:      movbu   (0x60413275),d1         # setting 447 (tag 0xD791): 0 Auto, 1 = 1/60 ... 7 = 1/4000
        and     7,d1
        asl     8,d1
        add     0x500,d1                # k = 0 gives 1/30, the stock floor
        cmp     d1,d0
        bge     2f
        mov     d1,d0
2:      movbu   (6,a2),d1               # stb_onoff = 1: keep the X-Sync cap
        cmp     1,d1
        bne     3f
        movhu   (16,a2),d1
        exth    d1
        cmp     d1,d0
        ble     3f
        mov     d1,d0
3:      ret     [d2,a2],12
