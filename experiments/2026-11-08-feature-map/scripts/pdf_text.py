# usage: python3 -I pdf_text.py SPEC.pdf > SPEC.txt   (used for the ERTL uITRON 4.0 spec in out/specs/)
# Minimal text extractor for PDF 1.3 (Standard security R2/V1, empty user password).
# Decrypts each stream with RC4, inflates it, and pulls strings from Tj/TJ operators.
import hashlib, re, sys, zlib
PAD = bytes.fromhex('28BF4E5E4E758A4164004E56FFFA01082E2E00B6D0683E802F0CA9FE6453697A')
data = open(sys.argv[1], 'rb').read()

def lit(b):  # unescape a PDF literal string body
    out, i = bytearray(), 0
    while i < len(b):
        c = b[i]
        if c == 0x5C and i + 1 < len(b):
            n = b[i + 1]
            if 0x30 <= n <= 0x37:
                j = i + 1; v = 0
                while j < len(b) and j < i + 4 and 0x30 <= b[j] <= 0x37: v = v * 8 + b[j] - 0x30; j += 1
                out.append(v & 0xFF); i = j; continue
            out.append({0x6E: 10, 0x72: 13, 0x74: 9, 0x62: 8, 0x66: 12}.get(n, n)); i += 2; continue
        out.append(c); i += 1
    return bytes(out)

def rc4(key, b):
    S = list(range(256)); j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) & 0xFF; S[i], S[j] = S[j], S[i]
    out = bytearray(); i = j = 0
    for c in b:
        i = (i + 1) & 0xFF; j = (j + S[i]) & 0xFF; S[i], S[j] = S[j], S[i]; out.append(c ^ S[(S[i] + S[j]) & 0xFF])
    return bytes(out)

key = None
m = re.search(rb'/Encrypt\s+(\d+)\s+0\s+R', data)
if m:
    enc = re.search(rb'[\r\n]' + m.group(1) + rb'\s+0\s+obj(.*?)endobj', data, re.S).group(1)
    O = lit(re.search(rb'/O\s*\((.*?)\)\s*[\r\n/]', enc, re.S).group(1))
    P = int(re.search(rb'/P\s+(-?\d+)', enc).group(1))
    ID0 = bytes.fromhex(re.search(rb'/ID\s*\[\s*<([0-9A-Fa-f]+)>', data).group(1).decode())
    key = hashlib.md5(PAD + O[:32] + (P & 0xFFFFFFFF).to_bytes(4, 'little') + ID0).digest()[:5]

pages = []
for om in re.finditer(rb'[\r\n](\d+)\s+(\d+)\s+obj', data):
    num, gen = int(om.group(1)), int(om.group(2))
    s0 = data.find(b'stream', om.end()); e0 = data.find(b'endobj', om.end())
    if s0 < 0 or s0 > e0: continue
    st = s0 + 6
    if data[st:st + 2] == b'\r\n': st += 2
    elif data[st:st + 1] in (b'\r', b'\n'): st += 1
    en = data.find(b'endstream', st); raw = data[st:en].rstrip(b'\r\n')
    if key:
        k = hashlib.md5(key + num.to_bytes(3, 'little') + gen.to_bytes(2, 'little')).digest()[:10]
        raw = rc4(k, raw)
    try: s = zlib.decompress(raw)
    except Exception: continue
    if b'Tj' not in s and b'TJ' not in s: continue
    page = []
    for t in re.finditer(rb'\[((?:\\.|[^\]])*)\]\s*TJ|\(((?:\\.|[^)])*)\)\s*Tj|(T\*|Td|TD|ET)', s, re.S):
        if t.group(3): page.append('\n'); continue
        chunk = t.group(1) if t.group(1) is not None else b'(' + t.group(2) + b')'
        for p in re.finditer(rb'\(((?:\\.|[^)])*)\)|(-?\d+\.?\d*)', chunk, re.S):
            if p.group(1) is not None: page.append(lit(p.group(1)).decode('latin-1'))
            elif p.group(2) and float(p.group(2)) < -200: page.append(' ')
    pages.append(''.join(page))
sys.stdout.write('\n\f\n'.join(pages))
