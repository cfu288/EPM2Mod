# sheet.py OUT.png COLS SCALE IN.png...: contact sheet of screenshots (pure python)
import zlib,struct,sys
def rd(p):
    b=open(p,'rb').read(); i=8; w=h=0; dat=b''
    while i<len(b):
        n,t=struct.unpack('>I4s',b[i:i+8]); d=b[i+8:i+8+n]; i+=12+n
        if t==b'IHDR': w,h=struct.unpack('>II',d[:8])
        if t==b'IDAT': dat+=d
    raw=zlib.decompress(dat); rows=[raw[y*(w*3+1)+1:(y+1)*(w*3+1)] for y in range(h)]
    return w,h,rows
def wr(p,w,h,rows):
    raw=b''.join(b'\0'+r for r in rows)
    def ch(t,d): c=struct.pack('>I',len(d))+t+d; return c+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    open(p,'wb').write(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw))+ch(b'IEND',b''))
def sheet(out,files,cols=2,scale=2):
    ims=[rd(f) for f in files]; w,h=ims[0][0]//scale,ims[0][1]//scale
    small=[[b''.join(rows[y*scale][x*scale*3:x*scale*3+3] for x in range(w)) for y in range(h)] for (W,H,rows) in ims]
    nrows=(len(small)+cols-1)//cols; outrows=[]; blank=b'\0'*(w*3)
    for r in range(nrows):
        for y in range(h): outrows.append(b''.join((small[r*cols+c][y] if r*cols+c<len(small) else blank) for c in range(cols)))
    wr(out,w*cols,h*nrows,outrows)
sheet(sys.argv[1],sys.argv[4:],int(sys.argv[2]),int(sys.argv[3]))
