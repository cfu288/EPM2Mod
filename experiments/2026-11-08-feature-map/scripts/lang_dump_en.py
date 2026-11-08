# Dump each body's English UI strings (block 1) to <out>/<body>.en.tsv : id \t text
# Block-1 directory: 16-byte records {container addr, size, 0, 0}; each language blob is
# {u32 A, u32 B} header, UTF-16 pool, pointer array [A..B) (runtime addrs, load base RT), footer OlympusLanguage_<code>.
import sys, struct, re, os
sys.path.insert(0, sys.argv[1] + '/tools'); import oetool
out = sys.argv[2]
FOOT = 'OlympusLanguage_enu'.encode('utf-16le')
for f in sys.argv[3:]:
    blocks, _ = oetool.parse(open(f, 'rb').read())
    blk = blocks[1]; d = blk['payload']; base = blk['addr']; body = os.path.basename(f)[6:14]
    done = False
    for i in range(1, 200):
        a, sz = struct.unpack_from('<2I', d, 16 * i)
        o = a - base
        if not (0 < o < len(d)) or sz == 0: break
        fp = d.find(FOOT, o, o + sz + 0x200)
        if fp < 0: continue
        for hdr in range(max(0, o - 0x200), o + 0x200, 2):
            A, B = struct.unpack_from('<2I', d, hdr)
            if A >> 24 != B >> 24 or A >> 28 < 0x8 or not 0 < B - A < 0x20000 or (B - A) % 4: continue
            for pad in range(0, 0x80, 2):
                RT = B - (fp - pad - hdr)
                arr = hdr + A - RT
                if hdr < arr < fp and struct.unpack_from('<I', d, arr)[0] == RT + 8:
                    n = (B - A) // 4
                    ptrs = struct.unpack_from('<%dI' % n, d, arr)
                    with open(f'{out}/{body}.en.tsv', 'w') as w:
                        for k, p in enumerate(ptrs):
                            s = hdr + p - RT; e = s
                            while e < len(d) - 1 and d[e:e+2] != b'\0\0': e += 2
                            t = d[s:e].decode('utf-16le', 'replace').replace('\t', ' ').replace('\r', '').replace('\n', '\\n')
                            w.write(f'{k}\t{t}\n')
                    print(body, 'entry', i, 'strings', n, 'load', hex(RT)); done = True; break
            if done: break
        if done: break
    if not done: print(body, 'not found')
