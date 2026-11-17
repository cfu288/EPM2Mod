# The file-read probe: open C:\LOOKS.BIN, read 512 bytes, close; the results in RES. Runs in a task.
    .equ RES,    0x00013400      # +0 handle, +4 bytes read, +8 fclose result, +12 done magic
    .equ BUF,    0x00013800
    .text
    .global _start
_start:
    movm [d2,d3,a2,a3],(sp)
    add -32,sp
    mov PATH,a0
    mov MODE,a1
    call FOPEN,[],20
    mov a0,a3
    mov a0,(RES)
    cmp 0,a3
    beq done
    mov BUF,a0
    mov 1,d0
    mov 512,d1
    mov a3,a1
    call FREAD,[],24
    mov d0,(RES+4)
    mov a3,a0
    call FCLOSE,[],12
    mov d0,(RES+8)
done:
    mov 0x600D600D,d0
    mov d0,(RES+12)
    add 32,sp
    movm (sp),[d2,d3,a2,a3]
END:
    nop
    bra END
PATH: .asciz "C:\\LOOKS.BIN"
MODE: .asciz "r"
