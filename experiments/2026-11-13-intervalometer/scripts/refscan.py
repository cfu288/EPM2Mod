# refscan.py BLOCK0 LO-HI...: every 4-byte little-endian value (any alignment) that falls in [LO,HI), with the
# instruction prefix byte(s) before it, so code immediates (fc cc/dc/c0/d0... + imm32) and data words both show
import sys, struct
B=0x7E421020
D=open(sys.argv[1],'rb').read()
rs=[tuple(int(x,16) for x in r.split('-')) for r in sys.argv[2:]]
import array
for o in range(0,len(D)-3):
    v=D[o]|D[o+1]<<8|D[o+2]<<16|D[o+3]<<24
    for lo,hi in rs:
        if lo<=v<hi:
            print('%08x off %06x value %08x pre %s aligned %s'%(B+o,o,v,D[max(0,o-2):o].hex(),o%4==0))
