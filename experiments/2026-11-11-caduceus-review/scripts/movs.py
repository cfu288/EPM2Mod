import sys, struct
img = open(sys.argv[1],'rb').read()
BASE=0x7E421020
def movs(v):
    n = struct.pack('<I', v); c=[]; p=img.find(n)
    while p>=0:
        if p>=2 and img[p-2]==0xfc and ((img[p-1]&0xfc)==0xcc or (img[p-1]&0xfc)==0xdc): c.append(BASE+p-2)
        p=img.find(n,p+1)
    return c
def raw(v):
    n=struct.pack('<I',v); c=0; p=img.find(n)
    while p>=0: c+=1; p=img.find(n,p+1)
    return c
for v in [0x97000000,0x9BB80000,0x8FE00000,0x9C000000,0x9C100000,0x9A900000,0x9AA00000,0x8FF00000,0x99200000,0x99300000]:
    m=movs(v); print(hex(v), 'movimm32', len(m), 'raw', raw(v), [hex(x) for x in m[:6]])
print(len(img), hex(len(img)))
print(img[:32].hex())
