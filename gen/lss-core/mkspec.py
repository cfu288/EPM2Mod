#!/usr/bin/env python3
"""Assemble gen/lss-core/lss.s and write data/specs/lss-core.json: the exposure part of "Lowest S/S Setting".

    uv run python gen/lss-core/mkspec.py [WORKDIR]

Research code (NOTES.md section 9). Four byte edits, all in segment 1:
  1. the code of lss.s over the exp debug printers 0x7E69E9EA-0x7E69EEAF;
  2. 0x7E69E858, in the shell command "exp still info" (0x7E69E772): its call of the printers 0x7E69E92A -> 5 nops;
  3. 0x7E693D4B: the call of tv_th 0x7E694001 gets the frame of NEWTH ([d2,d3,a2,a3],32; 5-byte form kept);
  4. 0x7E694001: tv_th's first 10 bytes become `jmp NEWTH; jmp NEWAUTO` (the new code is out of d16 range);
  5. 0x7E694610: the call of the auto path 0x7E6947C1 becomes a call of 0x7E694006 (jmp NEWAUTO).
"""
import hashlib, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import disasm, oetool  # noqa: E402

BASE = 0x7E421020
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
AREA, AREA_END = 0x7E69E9EA, 0x7E69EEAF
CUT, TH_SITE, AUTO_SITE = 0x7E69E858, 0x7E693D4B, 0x7E694610
TH_FN, J_AUTO = 0x7E694001, 0x7E694006       # the stock tv_th: its first 10 bytes become two jumps (it has no other caller)


EXT = {"LOG2": 0x7E507DFD, "PRM": 0x7E457C75, "F_SV": 0x7E6952D2, "BUILD": 0x7E6948AE, "AUTO": 0x7E6947C1,
       "SEG_T": 0x7E694DDE, "SEG_S": 0x7E694D34}


def asm(work, name, src, addr, ext=EXT):
    bindir = os.path.dirname(disasm.objdump_path())
    s, o, elf, out = (os.path.join(work, name + x) for x in (".s", ".o", ".elf", ".bin"))
    if src is not None:
        open(s, "w").write(src)
    subprocess.check_call([bindir + "/mn10300-elf-as", "-o", o, s])
    subprocess.check_call([bindir + "/mn10300-elf-ld", "-Ttext=%#x" % addr, *("--defsym=%s=%#x" % kv for kv in ext.items()),
                           "-o", elf, o])
    subprocess.check_call([bindir + "/mn10300-elf-objcopy", "-O", "binary", elf, out])
    syms = {}
    for line in subprocess.check_output([bindir + "/mn10300-elf-nm", elf], text=True).splitlines():
        v, kind, n = line.split()
        if kind != "A":
            syms[n] = int(v, 16)
    return open(out, "rb").read(), syms


def call16(site, target, regs, imm):
    """`call target,[regs],imm` in the 5-byte form: cd, d16 from the site, register mask, frame size."""
    rel = target - site
    assert -0x8000 <= rel < 0x8000
    return bytes([0xCD]) + (rel & 0xFFFF).to_bytes(2, "little") + bytes([regs, imm])


def main():
    work = sys.argv[1] if len(sys.argv) > 1 else "/dev/shm/lss-asm"
    os.makedirs(work, exist_ok=True)
    import shutil
    shutil.copy(os.path.join(HERE, "lss.s"), os.path.join(work, "lss.s"))
    code, syms = asm(work, "lss", None, AREA)
    if len(code) > AREA_END - AREA:
        sys.exit(f"{len(code)} bytes do not fit in {AREA_END - AREA}")
    hdr = "        .text\n        .global _start\n_start:\n"
    cut = bytes([0xCB] * 5)                     # nop x 5 over `call 0x7E69E92A,[],4`
    th, au = call16(TH_SITE, TH_FN, 0xF0, 32), call16(AUTO_SITE, J_AUTO, 0xF0, 76)
    jj, _ = asm(work, "jj", hdr + "        jmp NEWTH\n        jmp NEWAUTO\n", TH_FN,
                {"NEWTH": syms["NEWTH"], "NEWAUTO": syms["NEWAUTO"]})
    raw = open(os.path.join(ROOT, STOCK), "rb").read()
    b0 = oetool.parse(raw)[0][0]["payload"]

    def op(addr, new, note):
        old = b0[addr - BASE:addr - BASE + len(new)]
        return {"type": "bytes", "block": 0, "offset": "%#x" % (addr - BASE), "expect": old.hex(), "new": new.hex(),
                "_addr": "%#X" % addr, "_note": note}

    # the stock calls at both sites are the 5-byte form (cd d16 regs imm); keep that length
    assert th[0] == 0xCD and len(th) == 5 and b0[TH_SITE - BASE] == 0xCD, th.hex()
    assert au[0] == 0xCD and len(au) == 5 and b0[AUTO_SITE - BASE] == 0xCD, au.hex()
    assert len(jj) == 10 and jj[0] == jj[5] == 0xDC, jj.hex()
    spec = {
        "name": "lss-core",
        "description": "Lowest S/S Setting, exposure part, as the PEN-F 3.1 does it: in P and A with ISO Auto and no flash, "
                       "the shutter speed where ISO starts to rise is the chosen speed (setting 653, tag 0x9F11, RAM byte 0x60413225: "
                       "0 Auto, 1..55 = 60 s .. 1/4000 in 1/3 EV). Slower than the stock speed, P first lowers the shutter "
                       "at base ISO down to it. Code in the exp debug printers (segment 1). "
                       "See experiments/2026-11-17-auto-iso-min-shutter/NOTES.md section 9.",
        "base": STOCK, "base_sha256": hashlib.sha256(raw).hexdigest(),
        "status": "candidate: harness-checked, not flashed",
        "_symbols": {k: "%#X" % v for k, v in sorted(syms.items()) if k in ("NEWTH", "GATE", "NEWAUTO", "SEG6", "STOCK")},
        "ops": [
            op(AREA, code, f"new code, {len(code)} B of {AREA_END - AREA} (exp debug printers, segment 1)"),
            op(CUT, cut, "shell command 'exp still info' no longer calls the printers 0x7E69E92A (nop x 5)"),
            op(TH_SITE, th, "call 0x7E694001 with the frame of NEWTH"),
            op(TH_FN, jj, "the stock tv_th (one caller) becomes: jmp NEWTH; jmp NEWAUTO"),
            op(AUTO_SITE, au, "call 0x7E694006 (jmp NEWAUTO) in place of the auto path 0x7E6947C1"),
        ],
    }
    p = os.path.join(ROOT, "data", "specs", "lss-core.json")
    json.dump(spec, open(p, "w"), indent=1)
    print("wrote", os.path.relpath(p, ROOT), len(code), "bytes;", spec["_symbols"])


if __name__ == "__main__":
    main()
