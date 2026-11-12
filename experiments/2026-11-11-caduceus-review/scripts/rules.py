import sys,struct
img=open(sys.argv[1],'rb').read(); B=0x7E421020
u32=lambda o: struct.unpack_from('<I',img,o)[0]
hits=[o for o in range(0,0x400-8) if img[o]==0xfc and img[o+1]==0xdc and img[o+6]==0xf0 and img[o+7]==0xf4]
print('imageBase hits',[(hex(o),hex(u32(o+2))) for o in hits], 'base', [hex((u32(o+2)&~0xfff)|0x20) for o in hits])
# vectorPage
def pairAt(o,level):
    n=img[o+1]-0xcc
    return n if (img[o]==0xfc and 0<=n<4 and img[o+6]==0x03+4*n and img[o+7]==4*level and img[o+8]==0x80) else -1
runs=[]
for o in range(len(img)-70):
    if img[o]!=0xfc: continue
    regs=[pairAt(o+l*9,l) for l in range(7)]
    if -1 in regs: continue
    last=o+63; n=regs[6]
    if img[last]==0x01+4*n and img[last+1]==0x1c and img[last+2]==0x80:
        runs.append((hex(B+o),[hex(u32(o+l*9+2)) for l in range(7)]))
print('vector runs',runs[:4], len(runs))
# coreByte
cb=[]
for o in range(len(img)-9):
    if img[o]==0xfc and img[o+1]==0xa8 and img[o+6]==0xde and img[o+7]==0 and img[o+8]==0:
        a=u32(o+2)
        if 0x8FF00000<=a<0x8FF01000: cb.append((hex(B+o),hex(a)))
print('coreByte getters',cb)
for s in [b'[CHG] CHG MAIN S',b'Menu_ListMenu_Tab_Menu_',b'ScpuBkupW',b'OlyTaWu',b'OlyTaSt',b'OlyEvWt',b'OlyQeWr',b'OlyQeRd',b'uITRON',b'[GuiTouch]',b'UI_IN',b'CA_MAIN',b'[GUI App]',b'PER_SCPU',b'SCPU',b'[OSD_CONTROL]',b'OSD_DRV',b'[Display]',b'DISPLAY',b'CHG MAIN']:
    print(s.decode(), img.count(s))
