# The ART BKT row of RAW Data Edit: MN103 source of data/specs/raw-edit-art-bkt-3.json.
# gen/raw-edit-art-bkt/mkspec.py assembles it at 0x7EBB2AC4 (segment 2) and defines the firmware addresses it names
# (OK_DISPATCH ... FILMNAME, DESC) with --defsym. Design: experiments/2026-11-20-raw-edit-art-bkt/NOTES.md section 8.
        .text
        .global _start
        .equ PM_TAG, 0x9481             # the stored Picture Mode
        .equ NMAX, 31                   # frames kept from the composer's list (it makes at most 1 + 26)
_start:

# H1 (0x7EDF7DF3, the OK handler of list 320; a3 = the page). Rows 0 Current, 1 Custom1, 2 Custom2, 3 ART BKT, 4 No.
# The handler's (12,sp) holds the page's transition record (read by 0x7EDCDAAB at its start); its byte +5, (17,sp),
# is the key the GUI leaves the page with: the row, and 4 for Custom1 / Custom2 (set by the stock Custom path).
ROWS:   mov     1744,a0
        add     a3,a0
        movbu   (a0),d0                 # the row
        clr     d1
        movbu   d1,(ACT)                # an OK on the list ends an earlier run
        cmp     3,d0
        beq     2f
        cmp     4,d0
        bne     1f
        mov     3,d0                    # No: key 3 and the stock row 3 path, as the stock No
        call    KEY,[],4
        mov     3,d0
1:      jmp     OK_DISPATCH
2:      call    SETUP,[d2,d3,a2,a3],20
        clr     d0                      # key 0: the GUI goes on as for [Current] (to page 611, which starts the preview)
        call    KEY,[],4
        clr     d3
        clr     d2
        jmp     OK_CURRENT              # frame 0 is the current Picture Mode: a stock [Current] edit

# KEY(d0): the handler's transition key = d0 (called from ROWS: the handler's frame is at sp + 4)
KEY:    movbu   d0,(21,sp)
        mov     (12,sp),a1
        mov     a3,a0
        call    PAGE_KEY,[],4
        ret     [],4

# SETUP: the frame list as an ART bracket shot makes it, the Picture Mode to restore, the run state
SETUP:  mov     PM_TAG,d0
        mov     0,a0
        clr     d1
        call    PRM_GET,[d2,d3],12
        mov     d0,(PM0)
        mov     LIST,a1
        movbu   d0,(a1)                 # no block: the current Picture Mode only
        clr     d1
        movbu   d1,(1,a1)
        call    ALLOC,[],4
        cmp     0,a0
        beq     8f
        mov     a0,d3                   # the composer keeps d2, d3, a2, a3
        mov     a0,a2
        add     -16446,a2               # it reads take +16446..+17145 and writes 18-byte frames from +17154
        call    COMPOSE,[d2,d3,a2,a3],20
        mov     d3,a0
        add     708,a0                  # frame 0 (17154 - 16446); byte 0 = the Picture Mode, 0 ends the list
        mov     LIST,a1
        mov     NMAX,d1
1:      movbu   (a0),d0
        movbu   d0,(a1)
        cmp     0,d0
        beq     2f
        add     18,a0
        inc     a1
        add     -1,d1
        bne     1b
        clr     d0
        movbu   d0,(a1)
2:      mov     d3,a0
        call    FREE,[],4
8:      clr     d0
        movbu   d0,(K)
        movbu   d0,(PH)
        mov     1,d0
        movbu   d0,(ACT)
        ret     [d2,d3,a2,a3],20

# H2 (0x7EDF812C, RawEditProcessCallback, command 47 status 164: a job is done; a2 = its result)
CBDONE: mov     d2,d0
        mov     d0,d1
        call    CB_DONE_UI,[],4         # displaced
        movbu   (ACT),d0
        cmp     0,d0
        beq     9f
        mov     a2,d0
        call    STEP,[d2,d3,a2,a3],20
        cmp     0,d0
        beq     9f
        ret     [d2,d3,a2,a3],132       # the run took the event: return as the callback does
9:      jmp     CB_RESULT

# STEP(d0 = result) -> d0 = 1: the run goes on (no stock screen), 0: the stock handles the event
STEP:   cmp     0,d0
        bne     STOP                    # an error (a full card, ...): the stock shows it
        movbu   (PH),d0
        cmp     1,d0
        beq     SAVE
        cmp     2,d0
        beq     NEXT
        mov     2,d0                    # phase 0: frame 0's preview; the stock asks Yes / No once
        movbu   d0,(PH)
        clr     d0
        bra     9f
SAVE:   call    API,[],4                # our preview is done: save it without Yes / No
        mov     (a0),a1
        mov     (24,a1),a1
        calls   (a1)
        mov     2,d0
        movbu   d0,(PH)
        mov     1,d0
        bra     9f
NEXT:   movbu   (K),d0                  # a save is done: the next frame
        inc     d0
        movbu   d0,(K)
        mov     LIST,a0
        movbu   (d0,a0),d0
        cmp     0,d0
        beq     STOP                    # the last frame: the stock shows Reset / No
        call    PMSET,[],4
        call    API,[],4                # end the edit as Reset does, then [Current] again
        mov     (a0),a1
        mov     (8,a1),a1
        mov     1,d0
        calls   (a1)
        call    API,[],4
        mov     (a0),a2
        mov     RAWCB,a1
        mov     (32,a2),a2
        clr     d0
        calls   (a2)
        cmp     0,d0
        bne     STOP
        call    API,[],4                # and the preview, as page 611 (0x7EDFA754) starts it for [Current]
        mov     (a0),a2
        mov     (PV_ARG1),a1
        mov     (16,a2),a2
        mov     (PV_ARG0),d0
        calls   (a2)
        cmp     0,d0
        bne     STOP
        mov     1,d0
        movbu   d0,(PH)
        bra     9f
STOP:   mov     (PM0),d0                # the Picture Mode back, the run ends
        call    PMSET,[],4
        clr     d0
        movbu   d0,(ACT)
9:      ret     [d2,d3,a2,a3],20

# PMSET(d0 = value): the stored Picture Mode, and the EXIF ImageDescription for it (FILMNAME)
PMSET:  mov     d0,a1
        mov     PM_TAG,d0
        mov     0,a0
        clr     d1
        call    PRM_SET,[d2,d3,a2],16
        calls   FILMNAME
        ret     [],4

# H3 (0x7E9411AD, play_edit_raw_set_exif_default; d3 = the play command, (a2) = the take record, which holds the RAW's
# EXIF). A [Current] edit (command 146; every ART BKT frame is one) takes the ImageDescription a capture would take:
# the template's 32 B, which FILMNAME keeps at the current Picture Mode's film name. Custom1 / Custom2 (147, 148) develop
# with their own Picture Mode and keep the RAW's text. d0, d1, a0, a1 are free here (the next call reads d0 only).
FIXDESC:
        mov     (a2),a2                 # displaced
        mov     d3,a0
        movhu   (16,a0),d0
        cmp     146,d0
        bne     1f
        mov     DESC,a0
        mov     a2,a1
        add     1448,a1                 # ImageDescription in the take record (the template's offset 0x5A8)
        mov     8,d1
2:      mov     (a0),d0
        mov     d0,(a1)
        add     4,a0
        add     4,a1
        add     -1,d1
        bne     2b
1:      movbu   (16479,a2),d0           # displaced
        jmp     H3_BACK

        .balign 4
ITEMS:  .short 2, 1760, 0, 0, 0, 0      # Current, Custom1, Custom2 (the stock items), ART BKT, No
        .short 2, 1761, 0, 0, 0, 0
        .short 2, 1762, 0, 0, 0, 0
        .short 2, 1699, 0, 0, 0, 0
        .short 2, 496, 0, 0, 0, 0
PM0:    .long 0
ACT:    .byte 0                         # 1 while a run is on
PH:     .byte 0                         # 0 frame 0's preview, 1 our preview, 2 a save
K:      .byte 0                         # the frame being made
        .balign 4
LIST:   .space NMAX + 1
