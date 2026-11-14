"""Write the draft spec for probe A: Key Line live view while Picture Mode is Muted.

Research code. The spec is a draft for the experiment folder. It is not a build input.

Two hooks in the live-view ("mov") layer, and two small routines in free space:

  H1  0x7E6CC031 in mov_art colour-tone getter 0x7E6CBFD3.
      Stock: store the picture mode (d3) through a2, then turn it into an art code.
      New:   if the picture mode is 3 (Muted), use 119 (the stored picture mode of Key Line).
             The stock code that follows then returns art code 163 (164 for the movie variant)
             and the caller's mode byte 0x605B091C holds 119.
  H2  0x7E6C614C in the live-view expose setter 0x7E6C610B.
      Stock: if the picture mode read from the live-view struct is below 100, the art code
             is replaced by the picture mode and the mode byte is rewritten.
      New:   skip that when the picture mode is 3, so the art code from H1 stays.

This mirrors the two E-P5 changes for peaking (E-P5 0x7E3A8A26 and 0x7E3A2473), with
Key Line's numbers (119 / 163) where the E-P5 uses the peaking numbers (201 / 188).

Usage: mkspec_probe_a.py OUT.json
"""
import hashlib, json, os, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BASE = 0x7E421020
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
BLOCK0 = os.path.join(ROOT, "build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin")
NEW = 0x7ECB0EF0          # free run 0x7ECB0EE3-0x7ECB1000 (segment-2 padding, camera-proven area)
TRIGGER_MODE = 3          # low-level picture mode "Muted" (COLORTONE_FLAT)
KEYLINE_MODE = 119        # stored picture mode of Key Line


def jmp(at, target):
    """jmp rel32 (opcode DC, displacement from the instruction address)."""
    return b"\xdc" + struct.pack("<i", target - at)


def main():
    blk = open(BLOCK0, "rb").read()
    t1 = NEW
    c1 = bytes([0xAF, TRIGGER_MODE,      # cmp 3,d3
                0xC9, 0x04,              # bne +4
                0x8F, KEYLINE_MODE,      # mov 119,d3
                0xBA, 0x00,              # cmp 0,a2        (stock 0x7E6CC031)
                0xC8, 0x04,              # beq +4          (stock 0x7E6CC033)
                0xF0, 0x5E])             # movbu d3,(a2)   (stock 0x7E6CC035)
    c1 += jmp(t1 + len(c1), 0x7E6CC037)
    t2 = t1 + len(c1)
    c2 = bytes([0xA0, TRIGGER_MODE,      # cmp 3,d0
                0xC8, 0x0E,              # beq skip
                0xA0, 0x64,              # cmp 100,d0      (stock 0x7E6C614C)
                0xC2, 0x0A,              # bge skip        (stock 0x7E6C614E)
                0xF8, 0x92, 0x0D])       # movbu d0,(13,sp) (stock 0x7E6C6150)
    c2 += jmp(t2 + len(c2), 0x7E6C6153)
    assert len(c2) == 16
    c2 += jmp(t2 + len(c2), 0x7E6C6159)  # skip:
    code = c1 + c2

    def op(addr, new, why):
        off = addr - BASE
        return {"type": "bytes", "block": 0, "offset": hex(off),
                "expect": blk[off:off + len(new)].hex(), "new": new.hex(), "_why": why}

    ops = [
        op(NEW, code, "new code: T1 (%d B) at 0x%X, T2 (%d B) at 0x%X" % (len(c1), t1, len(c2), t2)),
        op(0x7E6CC031, jmp(0x7E6CC031, t1) + b"\xcb",
           "H1: jmp T1; nop. Replaces cmp 0,a2 / beq / movbu d3,(a2); T1 returns to 0x7E6CC037"),
        op(0x7E6C614C, jmp(0x7E6C614C, t2) + b"\xcb\xcb",
           "H2: jmp T2; nop; nop. Replaces cmp 100,d0 / bge / movbu d0,(13,sp); T2 returns to 0x7E6C6153 or 0x7E6C6159"),
    ]
    assert ops[0]["expect"] == "ff" * len(code)
    spec = {
        "name": "peaking-probe-a-keyline-lv",
        "description": "DRAFT, not camera-tested. Probe A of the focus-peaking work: live view runs the Key Line "
                       "effect while Picture Mode is Muted (low-level mode 3). Stills are not changed. "
                       "See experiments/2026-11-14-focus-peaking/NOTES.md.",
        "base": STOCK,
        "base_sha256": hashlib.sha256(open(os.path.join(ROOT, STOCK), "rb").read()).hexdigest(),
        "status": "draft; emulator-checked only",
        "ops": ops,
    }
    json.dump(spec, open(sys.argv[1], "w"), indent=1)
    print("wrote", sys.argv[1], "new code", len(code), "bytes at", hex(NEW), "-", hex(NEW + len(code)))


main()
