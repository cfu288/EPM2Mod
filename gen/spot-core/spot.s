# Spot metering at the AF target (gen/spot-core/mkspec.py writes data/specs/spot-core.json from this file).
# Entered by `jmp STUB` at 0x7E690920 (in place of `call 0x7E690A62,[d2,d3,a2,a3],56`), in the frame of the zone
# builder 0x7E6908CE. There: d0 = spot-zone output (also at (4,sp)), a0 = clipped 18x18 grid, a1 = 4x4 map.
# d3, a2, a3 are free (0x7E6908CE's `ret [d3,a2,a3],20` restores them); d2 is the caller's and is kept.
# Settings: one On/Off u8 per variant (TAGS, indexed by the HI/SH value prm 0x9699), the rows of the page Spot Metering:
# Spot 0x94D1 (info 593), Spot HI 0x9F91 (info 660), Spot SH 0x9821 (info 621).
# SMODE = 0x605A7254, exp's current sensor mode (writers 0x7E697B60, 0x7E69969B; 0x7E68F947 checks a CAM_AE_SETTING
# against it); HS3D = 0x7E6A2680, the test by which 0x7E68FF9B gives HSSC the HS3D crop area (experiments/2026-11-24-af-spot-metering/NOTES.md, build spot-af).
        .text
        .global _start
_start:
STUB:
        mov     a0,a2                   # grid
        mov     a1,a3                   # 4x4 map
        mov     MAPB,d0                 # variant B (2x tele-converter, I): keep the centre
        cmp     d0,a3
        beq     GO
        mov     (SMODE),d0              # exp's sensor mode (CAM_SENSOR_MODE: 0 HS, 1 HSSC, 2 MSSC, 3 LSSC, 4 HSHR, 5 CLIP)
        cmp     2,d0
        bhi     GO                      # LSSC, movie (HSHR 18x14), CLIP crops, any other: keep the centre
        cmp     1,d0
        bne     MODEOK
        call    HS3D,[a2],8             # HSSC: 1 = 0x7E68FF9B uses the HS3D crop area: keep the centre
        cmp     0,d0
        bne     GO
MODEOK:
        mov     0x80A1,d0               # metering: 1 = spot (Spot, HI, SH)
        call    GETP,[],4
        cmp     1,d0
        bne     GO
        mov     0x9699,d0               # 0 = Spot, 1 = HI, 2 = SH
        call    GETP,[],4
        cmp     3,d0
        bcc     GO
        add     d0,d0
        mov     TAGS,a0
        movhu   (d0,a0),d0              # the On/Off setting of this variant
        call    GETP,[],4
        cmp     0,d0
        beq     GO
        mov     0x84D1,d0               # AF target mode: 0 = single target
        call    GETP,[],4
        cmp     0,d0
        bne     GO
        mov     0x6761,d0               # 1 = C-AF+TR (tracking)
        call    GETP,[],4
        cmp     0,d0
        bne     GO
        mov     0x88B2,d0               # the selected target k = col * 5 + row
        call    GETP,[],4
        cmp     35,d0
        bcc     GO
        mov     TABLE,a0
        movbu   (d0,a0),d1
        extb    d1
        add     d1,d1                   # cells -> bytes
        add     d1,a2
GO:     mov     (4,sp),d0
        mov     a2,a0
        mov     a3,a1
        call    SPOTZ,[d2,d3,a2,a3],56
        ret     [d3,a2,a3],20

# d0 = tag -> d0 = the stored value, zero-extended (the getter of the settings store; a2, a3 survive it)
GETP:
        exthu   d0
        mov     0,a0
        clr     d1
        call    PRM,[d2,d3],12
        exthu   d0
        ret     [],4

# cell offset of the moved window, indexed by k: (r0 - 7) * 18 + (c0 - 7), with the grid field of
# results/field-aeparam.txt: r0 = 1, 4, 7, 10, 13 by row, c0 = 0, 3, 5, 7, 9, 11, 13 by column
TAGS:   .hword  0x94D1, 0x9F91, 0x9821
TABLE:
        .byte   -115,  -61,   -7,   47,  101
        .byte   -112,  -58,   -4,   50,  104
        .byte   -110,  -56,   -2,   52,  106
        .byte   -108,  -54,    0,   54,  108
        .byte   -106,  -52,    2,   56,  110
        .byte   -104,  -50,    4,   58,  112
        .byte   -102,  -48,    6,   60,  114
