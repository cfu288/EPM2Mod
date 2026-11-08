import sys, re, os
sys.path.insert(0, sys.argv[1] + '/tools'); import oetool
cands = ['Pop Art','Soft Focus','Pale&Light Color','Light Tone','Grainy Film','Pin Hole','Diorama','Cross Process',
         'Gentle Sepia','Dramatic Tone','Key Line','Watercolor','Vintage','Partial Color','Bleach Bypass','Instant Film',
         'Pastel','Mirror','Crystal','Star Light','Fisheye','Fish Eye','Drawing','Rock','Tender Light','Composite',
         'Kaleidoscope','Reflection','Fragmented','Miniature','ART12','ART13','ART14','ART15','ART16']
print('body'.ljust(10), ' '.join(c[:9].ljust(9) for c in cands))
for f in sys.argv[2:]:
    blocks, _ = oetool.parse(open(f, 'rb').read())
    allb = b''.join(b['payload'] for b in blocks)
    row = []
    for c in cands:
        n = len(re.findall(re.escape(c.encode('utf-16le')) + b'(?:\x00\x00|@\x00|\r\x00|\n\x00| \x00[IV])', allb))
        row.append(str(n).ljust(9))
    print(os.path.basename(f)[6:14].ljust(10), ' '.join(row))
