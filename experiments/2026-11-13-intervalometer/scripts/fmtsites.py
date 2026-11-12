# fmtsites.py LINEAR FMT1,FMT2,... : for each call to a row formatter, the row constant last loaded into d0
import sys, re
lines=[l.rstrip('\n').split('\t') for l in open(sys.argv[1])]
tg=[t.lower() for t in sys.argv[2].split(',')]
for i,p in enumerate(lines):
    if len(p)<4 or p[2]!='call': continue
    t=p[3].split(',')[0]
    if t not in tg: continue
    row=None
    for q in reversed(lines[max(0,i-12):i]):
        if len(q)>=4 and q[2]=='mov' and q[3].endswith(',d0'):
            row=q[3][:-3]; break
        if len(q)>=4 and q[2] in ('call','calls','ret','retf','jmp','bra'): break
    print(p[0].rstrip(':'),t,'row-arg',row)
