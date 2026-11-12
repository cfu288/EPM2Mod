# mkspec.py: build the ops of interval-timelapse.json from the stock block 0 (4 context bytes each side)
import json, struct, sys
B=0x7E421020
D=open('/path/to/epm2-tools/build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin','rb').read()
SPEC='/path/to/epm2-tools/experiments/2026-11-13-intervalometer/patches/interval-timelapse.json'
EDITS=[  # (runtime addr, stock bytes, new bytes)
 (0x7EFFE1A0, struct.pack('<5H',0,526,403,0x002,180), struct.pack('<5H',0,1357,1358,0x102,1)),
 (0x7EFF8C68, struct.pack('<3I',18,180,0),            struct.pack('<3I',628,482,0)),
 (0x7EDEC339, bytes.fromhex('2cb400'),                bytes.fromhex('2ce201')),
 (0x7E4C3EB8, b'\x00',                                b'\x0a'),
 (0x7E4C3EC8, struct.pack('<I',0),                    struct.pack('<I',5)),
]
ops=[]
for a,old,new in EDITS:
    o=a-B; assert D[o:o+len(old)]==old,(hex(a),D[o:o+len(old)].hex())
    pre,post=D[o-4:o],D[o+len(old):o+len(old)+4]
    ops.append({"type":"bytes","block":0,"offset":hex(o-4).upper().replace('0X','0x'),
                "expect":(pre+old+post).hex(),"new":(pre+new+post).hex()})
s=json.load(open(SPEC)); s['ops']=ops
json.dump(s,open(SPEC,'w'),indent=2); open(SPEC,'a').write('\n')
for op in ops: print(op)
