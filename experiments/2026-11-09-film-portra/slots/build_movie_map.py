"""patches/seven-movie-1.json: movie mode for the three remapped entries (NOTES §47), on top of remap7b-code + seven-fixes-1.

The live-view code has its own menu-entry -> art-code tables, one pair for stills and one for movies, in two functions
(0x7E6CBFD3: 0x7E7FF05C / 0x7E7FF008; 0x7E6DBA95: 0x7E807880 / 0x7E80782C). remap7b changed the stills pair for Soft
Focus (101), Pin Hole (105) and Diorama (106) and left the movie pair stock, so in movie mode art_GetFilterType said
102 / 145 / 167 (colour only) while the movie tables said 78 / 82 / 88 (effects): the display froze.
Now the movie entries give the movie codes that belong to the same colour-only filters: 103, 146, 168
(stock pairs: 102/103, 145/146, 167/168 share every per-code handler; 110 -> 145 / 146 is a stock menu entry).
168's six-axis entry gets the same plain handler as 167 (seven-fixes-1), for the same reason: Cross Process's handler
reads statistics through a pointer that is only set for picture modes 104 and 107.
      ../../.venv/bin/python -I slots/build_movie_map.py"""
import json, os, struct, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..", ".."); B = 0x7E421020
sys.path.insert(0, os.path.join(ROOT, "tools", "emu")); import patchblock
BIN = os.path.expanduser("~/opt/mn10300/bin/mn10300-elf-")
stock, cur, _ = patchblock.patched_block0([os.path.join(ROOT, "patches", n) for n in ("remap7b-code.json", "seven-fixes-1.json")])
def op(a, new): return {"type": "bytes", "block": 0, "offset": hex(a - B), "expect": cur[a - B:a - B + len(new)].hex(), "new": bytes(new).hex()}
u32 = lambda img, a: struct.unpack_from("<I", img, a - B)[0]
CAVE, SIX_JT, SIX_STUB = 0x7ECB0B80, 0x7E78C254, 0x7E880FD4
TABLES = ((0x7E7FF008, 0x7E6CC14E, "a"), (0x7E80782C, 0x7E6DBBC4, "b"))          # movie table, the function's common tail
asm = "        .text\n" + "".join(f"        .global m{t}_soft, m{t}_dio\nm{t}_soft: mov 103,d2\n        jmp TAIL_{t.upper()}\nm{t}_dio: mov 168,d2\n        jmp TAIL_{t.upper()}\n" for _, _, t in TABLES)
with tempfile.TemporaryDirectory() as d:
    open(os.path.join(d, "s.s"), "w").write(asm); run = lambda *a: subprocess.run(a, cwd=d, check=True, capture_output=True, text=True)
    run(BIN + "as", "-o", "s.o", "s.s"); run(BIN + "ld", f"-Ttext={CAVE:#x}", "-e", "ma_soft", *[f"--defsym=TAIL_{t.upper()}={tail:#x}" for _, tail, t in TABLES], "-o", "s.elf", "s.o")
    run(BIN + "objcopy", "-O", "binary", "-j", ".text", "s.elf", "s.bin"); code = open(os.path.join(d, "s.bin"), "rb").read()
    sym = {l.split()[2]: int(l.split()[0], 16) for l in run(BIN + "nm", "s.elf").stdout.splitlines() if len(l.split()) == 3}
assert set(cur[CAVE - B:CAVE - B + len(code) + 8]) == {0xFF} and CAVE + len(code) <= 0x7ECB1000, "destination not blank"
ops = [op(CAVE, code)]
for tab, tail, t in TABLES:
    def stub_code(a):
        o = a - B; return stock[o + 1] if stock[o] == 0x8A else struct.unpack_from("<H", stock, o + 1)[0]
    assert [stub_code(u32(stock, tab + 4 * i)) for i in (1, 5, 6, 10)] == [78, 82, 88, 146] and all(u32(cur, tab + 4 * i) == u32(stock, tab + 4 * i) for i in (1, 5, 6))
    ops += [op(tab + 4 * 1, struct.pack("<I", sym[f"m{t}_soft"])), op(tab + 4 * 5, struct.pack("<I", u32(stock, tab + 4 * 10))), op(tab + 4 * 6, struct.pack("<I", sym[f"m{t}_dio"]))]
assert u32(cur, SIX_JT + 4 * (167 - 9)) == SIX_STUB and u32(cur, SIX_JT + 4 * (168 - 9)) == 0x7E56D5CF
ops.append(op(SIX_JT + 4 * (168 - 9), struct.pack("<I", SIX_STUB)))
json.dump(dict(name="seven-movie-1", description="On top of remap7b-code + seven-fixes-1: in movie mode the Soft Focus, Pin Hole and Diorama entries give the colour-only movie codes 103 / 146 / 168 "
               "(they gave the stock effect codes 78 / 82 / 88 while art_GetFilterType gave 102 / 145 / 167, which froze the display); art code 168 gets the plain six-axis handler of 167. NOTES §47.",
               status="built, NOT camera-tested", base="firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN", base_sha256="34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300", ops=ops),
          open(os.path.join(ROOT, "patches", "seven-movie-1.json"), "w"), indent=1)
print("ops", len(ops), "; stubs", {k: hex(v) for k, v in sorted(sym.items()) if k.startswith("m")}, code.hex())
