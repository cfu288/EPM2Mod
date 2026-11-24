# Spot metering at the AF target (gen/spot-core/mkspec.py writes data/specs/spot-core-2.json from this file).
# Entered by `jmp STUB` at 0x7E690920 (in place of `call 0x7E690A62,[d2,d3,a2,a3],56`), in the frame of the zone
# builder 0x7E6908CE. There: d0 = spot-zone output (also at (4,sp)), a0 = clipped 18x18 grid, a1 = 4x4 map.
# d3, a2, a3 are free (0x7E6908CE's `ret [d3,a2,a3],20` restores them); d2 is the caller's and is kept.
# Settings: one On/Off u8 per variant (TAGS, indexed by the HI/SH value prm 0x9699), the rows of the page Spot Metering:
# Spot 0x94D1 (info 593), Spot HI 0x9F91 (info 660), Spot SH 0x9821 (info 621).
# SMODE = 0x605A7254, exp's current sensor mode (writers 0x7E697B60, 0x7E69969B; 0x7E68F947 checks a CAM_AE_SETTING
# against it); HS3D = 0x7E6A2680, the test by which 0x7E68FF9B gives HSSC the HS3D crop area; CLIP = 0x7E5871C0, the
# test by which the AF geometry 0x7E593894 uses the clip (magnified) view (byte 0x60515E24). TFP = 0x60515FA8 points
# to TAKE_FOCUS: +54 u8 the special AF frame is on (a touch on the screen, or the MAGNIFY key's frame), +58 x, +60 y
# (s16, -100..+100 over the AF frame). See experiments/2026-11-24-af-spot-metering/NOTES.md, "Build spot-af-2".
#
# The window: a point X, Y of the 640x480 AF frame gives the top-left cell c0 = (3X - 10)/100 - 2 and
# r0 = (4Y - 8.4)/100 - 2 (the grid covers x 20..620, y 14.6..464.7 of the AF frame: 33.3 x 25 px per cell), each kept
# in 0..14 so that the 4x4 window stays in the grid. CELL takes the numerator times 100. AF target k (col = k / 5,
# row = k % 5): X = 103 + 72 col, Y = 95 + 72 row. Special frame: X = (x + 100) * 3.19, Y = (y + 100) * 2.39, as the
# AF geometry 0x7E593894 maps it.
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
        call    CLIP,[],0               # the clip (magnified) view, as the AF geometry tests it: keep the centre
        cmp     0,d0
        bne     GO
        mov     0x80A1-0x10000,d0      # metering: 1 = spot (Spot, HI, SH); GETP takes the low 16 bits
        call    GETP,[],4
        cmp     1,d0
        bne     GO
        mov     0x9699-0x10000,d0       # 0 = Spot, 1 = HI, 2 = SH
        call    GETP,[],4
        cmp     3,d0
        bcc     GO
        add     d0,d0
        mov     TAGS,a0
        movhu   (d0,a0),d0              # the On/Off setting of this variant
        call    GETP,[],4
        beq     GO
        mov     0x6761,d0               # 1 = C-AF+TR (tracking)
        call    GETP,[],4
        bne     GO
        mov     (TFP),a0
        movbu   (54,a0),d0              # the special frame is on: it wins over the AF target, as in the AF geometry
        cmp     0,d0
        bne     TOUCH
        mov     0x84D1-0x10000,d0       # AF target mode: 0 = single target
        call    GETP,[],4
        bne     GO
        mov     0x88B2-0x10000,d0       # the selected target k = col * 5 + row
        call    GETP,[],4
        cmp     35,d0
        bcs     TARGET
GO:     mov     (4,sp),d0
        mov     a2,a0
        mov     a3,a1
        call    SPOTZ,[d2,d3,a2,a3],56
        ret     [d3,a2,a3],20

TOUCH:                                  # a0 = TAKE_FOCUS
        movhu   (60,a0),d0
        exth    d0
        add     100,d0
        mov     956,d1                  # 4 * 2.39 * 100
        mul     d1,d0
        add     -840,d0
        mov     d0,a1                   # row numerator
        movhu   (58,a0),d0
        exth    d0
        add     100,d0
        mov     957,d1                  # 3 * 3.19 * 100
        mul     d1,d0
        add     -1000,d0                # column numerator
        bra     MAP
TARGET:                                 # d0 = k
        clr     d1
        mov     d1,mdr
        mov     5,d1
        divu    d1,d0                   # d0 = col, mdr = row
        mov     mdr,d1
        mov     d0,a0
        mov     28800,d0
        mul     d1,d0
        add     37160,d0
        mov     d0,a1                   # row numerator: (371.6 + 288 row) * 100
        mov     a0,d1
        mov     21600,d0
        mul     d1,d0
        add     29900,d0                # column numerator: (299 + 216 col) * 100
MAP:                                    # d0 = column numerator, a1 = row numerator
        call    CELL,[],0
        mov     d0,a0                   # c0
        mov     a1,d0
        call    CELL,[],0               # r0
        mov     18,d1
        mul     d1,d0
        add     a0,d0
        add     -133,d0                 # cells from the stock window (row 7, col 7)
        add     d0,d0
        add     d0,a2
        bra     GO

# d0 = numerator -> d0 = d0 / 10000 - 2, kept in 0..14 (leaf; d1 and mdr change)
CELL:
        ext     d0
        mov     10000,d1
        div     d1,d0
        add     -2,d0
        cmp     0,d0
        bge     1f
        clr     d0
1:      cmp     14,d0
        ble     2f
        mov     14,d0
2:      ret     [],0

# d0 = tag -> d0 = the stored value, zero-extended, and the flags of `cmp 0,d0` (the getter of the settings store;
# a2, a3 survive it)
GETP:
        exthu   d0
        mov     0,a0
        clr     d1
        call    PRM,[d2,d3],12
        exthu   d0
        cmp     0,d0
        ret     [],4

TAGS:   .hword  0x94D1, 0x9F91, 0x9821
