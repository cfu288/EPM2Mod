# Generic film-slot helpers, second code area (NOTES §32). Linked at 0x7ECB0888: 1,912 bytes of 0xFF at the end of
# the range 0x7E8F5800-0x7ECB1000 that Usr1 loads at start-up. External addresses come from build_slots.py.
        .text
        .global g4, g5, g6, g7, gcommon, matrix7, t4, t5, t6, t7, recs, tabA, tabB, endc
# --- base gamma: one stub per slot loads a1 = that slot's three record addresses, then the common part
g4:     mov     tri4,a1                 # Pale&Light I   71 / 80
        bra     gcommon
g5:     mov     tri5,a1                 # Soft Focus     69 / 78
        bra     gcommon
g6:     mov     tri6,a1                 # Pin Hole I     73 / 82
        bra     gcommon
g7:     mov     tri7,a1                 # Diorama        86 / 88
gcommon:extbu   d2                      # as the stock handler 0x7E56B82A; PICK does not touch a1
        movbu   (28,sp),d3
        mov     d2,d0
        mov     d3,d1
        mov     (a1),a0
        call    PICK,[d2,d3],8
        mov     a0,(a2)
        mov     d2,d0
        mov     d3,d1
        mov     (4,a1),a0
        call    PICK,[d2,d3],8
        mov     a0,(a3)
        mov     (8,a1),a0
        jmp     GTAIL
# --- art matrix: entered by a jump from 0x7E56C6A5 with the art code in d0; d1, d2, d3 are not changed
matrix7:cmp     85,d0
        beq     h1
        cmp     87,d0
        beq     h1
        cmp     72,d0
        beq     h2
        cmp     81,d0
        beq     h2
        cmp     70,d0
        beq     h3
        cmp     79,d0
        beq     h3
        cmp     71,d0
        beq     h4
        cmp     80,d0
        beq     h4
        cmp     69,d0
        beq     h5
        cmp     78,d0
        beq     h5
        cmp     73,d0
        beq     h6
        cmp     82,d0
        beq     h6
        cmp     86,d0
        beq     h7
        cmp     88,d0
        beq     h7
        jmp     M_NONE
h1:     mov     T1,a1
        bra     mtail
h2:     mov     T2,a1
        bra     mtail
h3:     mov     T3,a1
        bra     mtail
h4:     mov     t4,a1
        bra     mtail
h5:     mov     t5,a1
        bra     mtail
h6:     mov     t6,a1
        bra     mtail
h7:     mov     t7,a1
mtail:  mov     d3,a0
        jmp     M_APPLY
        .balign 4, 0xff
endc:
# --- data
t4:     .hword  256,0,0, 0,256,0, 0,0,256
t5:     .hword  256,0,0, 0,256,0, 0,0,256
t6:     .hword  256,0,0, 0,256,0, 0,0,256
t7:     .hword  256,0,0, 0,256,0, 0,0,256
        .balign 4, 0xff
tri4:   .long   recs + 0*32, recs + 1*32, recs + 2*32
tri5:   .long   recs + 3*32, recs + 4*32, recs + 5*32
tri6:   .long   recs + 6*32, recs + 7*32, recs + 8*32
tri7:   .long   recs + 9*32, recs + 10*32, recs + 11*32
# 12 records of 8 table pointers (4 columns x 2 members). Member 1 of every column is the film's own table (the
# film curve on the base that raw stills use; the other columns' stock bases differ from it by 2-4 %, and they
# serve YC-input, view and movie jobs: P+99 = 0xC0 / 0xC2 / 5, NOTES 32). Member 0 stays the stock default table.
        .macro  rec own
        .long   0x7E74E7BC, \own, 0x7E7517BC, \own, 0x7E7547BC, \own, 0x7E7577BC, \own
        .endm
recs:   rec     G4R
        rec     G4G
        rec     G4B
        rec     G5R
        rec     G5G
        rec     G5B
        rec     G6R
        rec     G6G
        rec     G6B
        rec     G7R
        rec     G7G
        rec     G7B
tabA:   .fill   512, 1, 0xff            # two gamma tables live here (written by the film patches)
tabB:   .fill   512, 1, 0xff
