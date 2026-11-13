# framecap.py: where the 99-frame cap of info 483 lives (E-PM2 v1.6 block 0); also the list records of the other bodies
import struct, sys, glob
B=0x7E421020
D=open(sys.argv[1],'rb').read()
rec=0x7E84C5FC; info,key,raw,gui,tot,es,cl,ty,z=struct.unpack_from('<HHIIHHBBH',D,rec-B)
lst=D[raw-B:raw-B+tot]
print('mcon value-list record %#x: info %d key %d raw %#x gui %#x total %d elem %d clamp %d type %d (1 = u8)'%(rec,info,key,raw,gui,tot,es,cl,ty))
print('  list = %d..%d, contiguous: %s; byte before %#x (list of 482), byte after %#x (list of 486)'%(lst[0],lst[-1],list(lst)==list(range(1,100)),D[raw-B-1],D[raw-B+tot]))
rows=[]
for o in range(0x7EEE0000-B,0x7F034000-B,4):
    i,v,k,x=struct.unpack_from('<4I',D,o)
    if i==483 and k==2 and 1<=v<=255 and D[o+16:o+32]==b'\0'*16: rows.append((B+o,v,x))
print('GUI option rows {info 483, value, kind 2, id, 16 zero bytes} (32 B each): %d rows, %#x..%#x, values %d..%d, id = value + %#x for all: %s'%(len(rows),rows[0][0],rows[-1][0]+32,rows[0][1],rows[-1][1],rows[0][2]-rows[0][1],all(x-v==rows[0][2]-rows[0][1] for _,v,x in rows)))
nxt=struct.unpack_from('<4I',D,rows[-1][0]+32-B); prv=struct.unpack_from('<4I',D,rows[0][0]-32-B)
print('  row before: info %d value %d; row after: info %d value %d (no slack)'%(prv[0],prv[1],nxt[0],nxt[1]))
# MODE default record of 0xDE21 and 0xDE84
for tag,a in ((0xDE21,0x7E4C3EB4),(0xDE84,0x7E4C3EE4)):
    t,c=struct.unpack_from('<HH',D,a-B); print('prm %#x: record %#x tag %#x count %d, type by low nibble %d (1 = u8, 4 = u32)'%(tag,a,t,c,t&15))
