# Third film slot helpers for E-PM2 v1.6 block 0 (NOTES §29-30).
# Linked at 0x7E880F5C: 164 bytes of 0xFF at the end of the boot-loaded range 0x7E4FE000-0x7E881000.
# External addresses (PICK, GTAIL, M_T1, M_T2, M_APPLY, M_NONE) are given to the linker by build_slot3.py.
        .text
        .global gamma3, matrix3, t3
# Base-gamma handler for art codes 70 / 79 (top-level Pop Art): the stock handler 0x7E56B82A with other records.
gamma3: extbu   d2
        movbu   (28,sp),d3
        mov     d2,d0
        mov     d3,d1
        mov     0x7E78B3DC,a0           # R: record of Pale&Light
        call    PICK,[d2,d3],8          # 0x7E56B732: one table out of the record's 8
        mov     a0,(a2)
        mov     d2,d0
        mov     d3,d1
        mov     0x7E78B3FC,a0           # G: record of Light Tone
        call    PICK,[d2,d3],8
        mov     a0,(a3)
        mov     0x7E78B47C,a0           # B: record of Pop Art II
        jmp     GTAIL                   # 0x7E56B852: third pick, store, return
# Art-matrix choice; entered by a jump from 0x7E56C6A5 with the art code in d0.
matrix3:cmp     85,d0                   # Cross Process I still / movie -> stock block for table 0x7E768F46
        beq     m1
        cmp     87,d0
        beq     m1
        cmp     72,d0                   # Light Tone still / movie -> stock block for table 0x7E768F58
        beq     m2
        cmp     81,d0
        beq     m2
        cmp     70,d0                   # Pop Art I still / movie -> table t3
        beq     m3
        cmp     79,d0
        beq     m3
        jmp     M_NONE                  # 0x7E56C76B
m1:     jmp     M_T1                    # 0x7E56C6B8
m2:     jmp     M_T2                    # 0x7E56C6C3
m3:     mov     d3,a0
        mov     t3,a1
        jmp     M_APPLY                 # 0x7E56C764
        .balign 2, 0xff
t3:     .hword  256,0,0, 0,256,0, 0,0,256
