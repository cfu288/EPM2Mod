# Decode rec_art_set_exif_data in any body: picture mode -> Exif ArtFilter values. args: repo fw base outdir
import sys, re
sys.path.insert(0, sys.argv[1] + '/tools'); import fwmap
fwmap.FW, fwmap.BASE, fwmap.OUT = sys.argv[2], int(sys.argv[3], 0), sys.argv[4]
_, b = fwmap.block(); B = fwmap.BASE
strings, _ = fwmap.string_index(b, B)
if len(sys.argv) > 5:
    fn = int(sys.argv[5], 0)
else:
    sa = [B + o for o, t in strings.items() if t == 'rec_art_set_exif_data'][0]
    fn = [int(r[0], 16) for r in fwmap.load_tsv('strrefs.tsv') if int(r[2], 16) == sa][0]
ins = []
for l in fwmap.disassembly(fn).splitlines():
    m = re.match(r'\s*([0-9a-f]+):\t(\S+)\s*(.*)', l)
    if m: ins.append((int(m.group(1), 16), m.group(2), m.group(3)))
idx = {a: i for i, (a, _, _) in enumerate(ins)}
# find "cmp LO,d0 ... cmp HI,d0 ... add -LO,d0 ; asl2 ; mov TAB,a0 ; mov (d0,a0),a0 ; jmp (a0)"
for i, (a, op, arg) in enumerate(ins):
    if op == 'jmp' and arg == '(a0)':
        tab = int(re.match(r'(\d+),a0', ins[i-2][2]).group(1)); lo = -int(re.match(r'(-?\d+),d0', ins[i-4][2]).group(1))
        hi = max(int(m.group(1)) for _, o, g in ins[:i] if o == 'cmp' for m in [re.match(r'(\d+),d0$', g)] if m)
        break
print(f'fn {fn:#x} table {tab:#x} modes {lo}..{hi}')
targets = [int.from_bytes(b[tab - B + 4*k:tab - B + 4*k + 4], 'little') for k in range(hi - lo + 1)]
ends = sorted(set(targets)); default = max(set(targets), key=targets.count)
for k, t in enumerate(targets):
    if t == default and targets.count(t) > 2: print(lo + k, 'default'); continue
    i = idx.get(t); reg = {}; a2 = []
    nxt = min([e for e in ends if e > t] + [ins[-1][0]])
    while i is not None and i < len(ins) and ins[i][0] < nxt:
        a, op, arg = ins[i]
        m = re.match(r'(\d+),(d\d)$', arg)
        if op == 'mov' and m: reg[m.group(2)] = int(m.group(1))
        m = re.match(r'(d\d),(d\d)$', arg)
        if op == 'mov' and m and m.group(1) in reg: reg[m.group(2)] = reg[m.group(1)]
        if op == 'clr': reg[arg] = 0
        if op == 'movhu' and arg.endswith(',(a2)'): a2.append(reg.get(arg.split(',')[0]))
        i += 1
    print(lo + k, a2)
