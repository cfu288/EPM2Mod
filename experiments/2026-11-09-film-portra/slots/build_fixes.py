"""patches/seven-fixes-1.json: three structural changes on top of remap7b-code (NOTES §43).
  1. Diorama entry (art code 167): its six-axis handler is Cross Process's (0x7E56D5CF), which reads image statistics
     through a buffer pointer that the stock code sets only for the Grainy Film and Cross Process picture modes. Reached
     from the Diorama picture mode the pointer is uninitialised stack. 167 now gets a plain handler (new, 17 bytes in the
     boot segment's free space) that loads its two records and joins the common tail, like every other colour filter.
  2. Chroma curves: each film slot's stills code goes back to its own stock handler and 97-byte record (remap7b had
     pointed 71 / 102 / 145 / 167 at Cross Process I's record); the movie codes that shared those records are pointed at
     Soft Focus's untouched linear record, so movies keep straight chroma curves.
  3. Second filter types: Pop Art II, Pale&Light II and Cross Process II select the same art code as type I
     (three immediates in art_GetFilterType; the live-view tables never looked at the type).
      ../../.venv/bin/python -I slots/build_fixes.py"""
import json, os, struct, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..", ".."); B = 0x7E421020
sys.path.insert(0, os.path.join(ROOT, "tools", "emu")); import patchblock
BIN = os.path.expanduser("~/opt/mn10300/bin/mn10300-elf-")
stock, cur, _ = patchblock.patched_block0([os.path.join(ROOT, "patches", "remap7b-code.json")])       # state these ops are applied to
def op(a, new): return {"type": "bytes", "block": 0, "offset": hex(a - B), "expect": cur[a - B:a - B + len(new)].hex(), "new": bytes(new).hex()}
u32 = lambda img, a: struct.unpack_from("<I", img, a - B)[0]
STUB, TAIL, SIX_S, SIX_H = 0x7E880FD4, 0x7E56D8D8, 0x7E769622, 0x7E76962E
SIX_JT, CHROMA_JT, LINEAR = 0x7E78C254, 0x7E78AEA4, 0x7E566308
with tempfile.TemporaryDirectory() as d:
    open(os.path.join(d, "s.s"), "w").write(f"        .text\n        .global six_dio\nsix_dio: mov {SIX_S:#x},a3\n        mov {SIX_H:#x},a2\n        jmp TAIL\n")
    run = lambda *a: subprocess.run(a, cwd=d, check=True, capture_output=True)
    run(BIN + "as", "-o", "s.o", "s.s"); run(BIN + "ld", f"-Ttext={STUB:#x}", "-e", "six_dio", f"--defsym=TAIL={TAIL:#x}", "-o", "s.elf", "s.o"); run(BIN + "objcopy", "-O", "binary", "-j", ".text", "s.elf", "s.bin")
    stub = open(os.path.join(d, "s.bin"), "rb").read()
assert len(stub) == 17 and set(cur[STUB - B:STUB - B + 20]) == {0xFF}, "stub size / destination not blank"
assert u32(stock, SIX_JT + 4 * (167 - 9)) == 0x7E56D5CF and stock[0x7E56D566 - B:0x7E56D566 - B + 15][12:13] == b"\xcc"          # the handler being replaced; a stock plain handler ends in jmp TAIL
ops = [op(STUB, stub), op(SIX_JT + 4 * (167 - 9), struct.pack("<I", STUB))]
for code in (71, 102, 145, 167):                                   # stills: own stock chroma handler again
    ops.append(op(CHROMA_JT + 4 * (code - 69), struct.pack("<I", u32(stock, CHROMA_JT + 4 * (code - 69)))))
assert u32(stock, CHROMA_JT) == LINEAR                             # code 69's handler; its record 0x7E74B858 is linear and stays stock
for code in (79, 80, 81, 87, 103, 146, 168):                       # movie codes that shared a film slot's record
    ops.append(op(CHROMA_JT + 4 * (code - 69), struct.pack("<I", LINEAR)))
for a, old, new in ((0x7E71BDDB, 102, 70), (0x7E71BDF1, 145, 71), (0x7E71BE0D, 167, 85)):          # type II immediates in art_GetFilterType
    assert stock[a - B] == old and cur[a - B] == old; ops.append(op(a, bytes([new])))
json.dump(dict(name="seven-fixes-1", description="On top of remap7b-code: plain six-axis handler for art code 167 (Diorama entry no longer runs Cross Process's statistics code through an uninitialised pointer); "
               "each film slot's stills code uses its own chroma-curve record, movie codes use a linear one; Pop Art II, Pale&Light II and Cross Process II select the type I code. NOTES §43.",
               status="built, NOT camera-tested", base="firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN", base_sha256="34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300",
               ops=[o for o in ops if o["expect"] != o["new"]]), open(os.path.join(ROOT, "patches", "seven-fixes-1.json"), "w"), indent=1)
print("ops", len(ops), "stub", stub.hex())
