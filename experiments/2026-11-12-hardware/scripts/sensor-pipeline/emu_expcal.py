import sys
sys.path.insert(0, '/path/to/EPM2Mod/tools/emu')
import omemu
e = omemu.Emu()
e.load(omemu.STOCK_BLOCK0)
# 0x7E640FFB(d0 = mode id, d1 = lines) -> lines * rec+32/256 / 1000 ; 0x7E63E675(d0=x) uses current mode from RAM, skip
for mode, lines in ((0,700),(1,700),(2,350),(3,174),(4,1314),(5,1176),(6,3504),(7,3504),(0,2400),(4,4800)):
    r = e.call(0x7E640FFB, regs={'d0': mode, 'd1': lines})
    print('mode', mode, 'lines', lines, '->', r['regs']['d0'])
