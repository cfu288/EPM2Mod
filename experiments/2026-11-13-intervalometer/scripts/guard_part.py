# ---- time-lapse-movie guard flag (E-PL6 RAM 0x602B4B20; its 4 sites 0x7ECDA8C1 set, 0x7ECDA4B3 / 0x7ECDA4DD clear,
#      0x7ECDA5CA test). E-PM2 flag = the unused row-1 slot of the value-list pointer table (see README section 12)
FLAG = 0x602BE878
assert struct.unpack_from('<I', D, FLAG + K - B)[0] == 0            # .data initial value 0 (stock; the v2 edit starts at slot 12)
PRINTG, PRE, CHECKEND = 0x7ECE631E, 0x7ECD50DE, 0x7ECDA7D1
absf = struct.pack('<I', FLAG)
T3, T4, T5, T6 = 0x7ECB0E80, 0x7ECB0E98, 0x7ECB0EB0, 0x7ECB0EC8
callp = bytes.fromhex('dd')                                        # all four hooks replace a call (re-issued in the trampoline)
# T3 set: createTimeLapseMovie success path. Hook the print call at 0x7ECDA56C (7 B); `mov 1,d2; bra 0x7ECDA5AE` after it
H = 0x7ECDA56C; assert rd(D, H, 11) == b'\xdd' + struct.pack('<i', PRINTG - H) + bytes.fromhex('300c') + bytes.fromhex('8a01ca39')
t, _ = assemble(T3, [('call', PRINTG, 0x30, 12), b'\x8a\x01', b'\xfc\x89' + absf, ('jmp', 0x7ECDA5AE)])
edit(T3, t, 'movie guard T3: print call, mov 1,d2, flag = d2 (E-PL6 0x7ECDA8C1), jmp 0x7ECDA5AE')
edit(H, b'\xdc' + struct.pack('<i', T3 - H), 'createTimeLapseMovie 0x7ECDA56C: jmp T3 (6 bytes after it unreachable)')
# T4 / T5 clear: receiveEndCreateMovie 0x7ECDA1B2, receiveErrorCreateMovie 0x7ECDA1D5 (print calls, 7 B each)
for T, H, why in ((T4, 0x7ECDA1B2, 'receiveEndCreateMovie'), (T5, 0x7ECDA1D5, 'receiveErrorCreateMovie')):
    assert rd(D, H, 7) == b'\xdd' + struct.pack('<i', PRINTG - H) + bytes.fromhex('300c')
    t, _ = assemble(T, [('call', PRINTG, 0x30, 12), b'\x00', b'\xfc\x81' + absf, ('jmp', H + 7)])
    edit(T, t, 'movie guard: print call, clr d0, flag = 0 (as E-PL6 %s), jmp back' % why)
    edit(H, b'\xdc' + struct.pack('<i', T - H), '%s %#x: jmp trampoline (2 bytes after it unreachable)' % (why, H))
# T6 test: receiveEndMediaMountForEndWait 0x7ECDA2A7 `call 0x7ECD50DE,[],0` (5 B, cd form); then skip the end check
H = 0x7ECDA2A7; assert rd(D, H, 5) == b'\xcd' + struct.pack('<h', PRE - H) + b'\x00\x00'
t, _ = assemble(T6, [('call', PRE, 0x00, 0), b'\xfc\xa1' + absf, b'\xb5\x00', ('b', 'ne', 'SKIP'), ('jmp', H + 5),
                     ('L', 'SKIP'), ('jmp', 0x7ECDA2B3)])
edit(T6, t, 'movie guard T6: call 0x7ECD50DE, mov (flag),a1, cmp 0,a1, bne -> ret 0x7ECDA2B3 else back (E-PL6 0x7ECDA5CA)')
edit(H, b'\xdc' + struct.pack('<i', T6 - H), 'receiveEndMediaMountForEndWait 0x7ECDA2A7: jmp T6')
assert T6 + len(t) <= FREE_HI
print('guard trampolines end', hex(T6 + len(t)))
