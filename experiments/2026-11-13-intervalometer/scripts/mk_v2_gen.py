s=open('mkspec_awake.py').read()
def rep(a,b):
    global s
    assert s.count(a)>=1, a[:70]; s=s.replace(a,b,1)
rep("# mkspec_awake.py (= mkspec_insert.py + awake_part.py): build","# mkspec_v2.py (mkspec_insert.py + awake_part.py, relocated to the segment-2 padding, + guard_part.py): build")
rep("patches/interval-timelapse-insert-awake.json","patches/interval-timelapse-v2.json")
rep('"name":"interval-timelapse-insert-awake"','"name":"interval-timelapse-v2"')
rep("open(SC+'insert_desc.txt').read().strip()+' '+open(SC+'awake_desc.txt').read().strip()","open(SC+'v2_desc.txt').read().strip()")
rep("""FREE_LO, FREE_HI = 0x7F033C00, 0x7F034000
assert rd(D,0x7F033B7C,FREE_HI-0x7F033B7C)==b'\\xff'*(FREE_HI-0x7F033B7C)
NEW_TOP, NEW_P3, CAVE = 0x7F033C00, 0x7F033D80, 0x7F033DE0""",
"""# v2: segment-2 padding (Usr1 copy 0x7E8F5800-0x7ECB1000), after the film specs' code that ends at 0x7ECB0B9E
FREE_LO, FREE_HI = 0x7ECB0BA4, 0x7ECB1000
assert rd(D,0x7ECB0888,FREE_HI-0x7ECB0888)==b'\\xff'*(FREE_HI-0x7ECB0888)
FILMS=open(SC+'films.block0.bin','rb').read()
assert rd(FILMS,0x7ECB0B9E,FREE_HI-0x7ECB0B9E)==b'\\xff'*(FREE_HI-0x7ECB0B9E)
NEW_TOP, NEW_P3, CAVE = 0x7ECB0BA4, 0x7ECB0D24, 0x7ECB0D78""")
rep("""PT=0x602BE874+K; ptrs=list(struct.unpack_from('<40I',D,PT-B)); assert ptrs[39]==0
onoff=ptrs[11]
newp=ptrs[:11]+[onoff]+ptrs[11:39]
edit(PT,struct.pack('<40I',*newp),'.data row value-list pointers renumbered (+ Off/On at row 11)')""",
"""# the table has 37 slots (rows 0-36; 0x602BE908 is another variable): only slots 12..35 change (11 already = Off/On)
PT=0x602BE874+K; ptrs=list(struct.unpack_from('<37I',D,PT-B)); assert ptrs[35]==0 and ptrs[36]==0
onoff=ptrs[11]
newp=ptrs[:11]+[onoff]+ptrs[11:36]; assert len(newp)==37
lo=min(i for i in range(37) if newp[i]!=ptrs[i]); hi=max(i for i in range(37) if newp[i]!=ptrs[i])
edit(PT+4*lo,struct.pack('<%dI'%(hi-lo+1),*newp[lo:hi+1]),'.data row value-list pointers: slots %d-%d renumbered (37-slot table)'%(lo,hi))""")
rep("T1, T2 = 0x7F033E20, 0x7F033E40\nassert rd(D, 0x7F033E13, FREE_HI - 0x7F033E13) == b'\\xff' * (FREE_HI - 0x7F033E13)","T1, T2 = 0x7ECB0DB0, 0x7ECB0DC8")
rep("# ops with 4 context bytes", open('guard_part.py').read()+"\n# ops with 4 context bytes")
open('mkspec_v2.py','w').write(s)
