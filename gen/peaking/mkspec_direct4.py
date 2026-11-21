"""Write the patch spec for the fourth direct focus-peaking build (NOTES.md section 14).

Changes from mkspec_direct3.py (direct-3). The routines are the same text; only their places change.

1. No routine at 0x7E880FE4. The spec seven-fixes-1 ends there: its 17th byte, 0xFF, is the top byte of the
   displacement of `jmp 0x7E56D8D8` in the six-axis handler of art codes 167 and 168 (the Velvia entry, ART 7).
   T_G's first byte turned it into `jmp 0x5C56D8D8`: the camera crashed when Velvia was chosen.
2. No routine in the "reclaimed dead code" 0x7E50A201 and 0x7E53A55C. 0x7E53A55C is "pwr_standby start" and
   calls 0x7E50A201; the SRAM copy of the sram-image calls it (0x470010F7) when the camera goes to sleep.
3. All routines that a segment-1 hook reaches are now in the 0xFF run of the kernel range, from 0x7E4C9200
   (loaded by the reset code with the kernel, before every task; the spec interval-frames-240 keeps data at
   0x7E4C9100 in the same run and the camera reads it).
4. T_ON and T_OFF start at 0x7EBF1F28, not 0x7EBF1F00: the op of interval-frames-240 covers 0x7EBF1F00-03, and
   data/specs/peaking-direct-3.json still holds 0x7EBF1F00-0x7EBF1F27 in the free-space ledger. direct-1's code ran
   in 0x7EBF1F00-0x7EBF1FB6 on the camera.
5. The gain of the line image (T_K) is 256 as in direct-3 (data/specs/peaking-gain-2x.json changes it).

Research code. It assembles the new routines with the mn10300 GNU assembler, links every piece at its
runtime address, and writes one spec with the stock bytes that each op replaces.

Usage: uv run python gen/peaking/mkspec_direct4.py WORKDIR [LISTING.txt]
  WORKDIR  scratch folder for the assembler files (outside the repository)
Writes data/specs/peaking-direct-4.json. Copied from experiments/2026-11-14-focus-peaking/scripts/mkspec_direct4.py.
"""
import hashlib, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import BIN, ROOT, STOCK, payloads  # noqa: E402
BASE = 0x7E421020

AREAS = {
    # Kernel range, 0xFF run 0x7E4C90CA-0x7E4C9800 (docs/reference/code-space-map.md 3.2, all six checks ok). The reset code
    # loads it with the kernel, so it is in RAM before any task and on the update path. interval-frames-240 has
    # data at 0x7E4C9100-0x7E4C9180 (its op ends at 0x7E4C9184). No code has run here.
    ".k": (0x7E4C9200, 0x7E4C9800, "kernel range, 0xFF run: getL, T_A, T_B, T_C, T_D1/T_D2, T_H, T_I, T_G, T_E1, T_E2, "
                                   "T_F, T_M, T_J, T_K"),
    # segment 2: only the two routines whose hook sites are in segment 2 themselves
    ".u":  (0x7EBF1F28, 0x7EBF3BAD, "free text area, segment 2, code ran here in the direct-1 flash: "
                                    "T_ON, T_OFF"),
}

SYMS = """
.equ MOVSM,  0x605b03d0   # state number of the mov task state machine (1 start, 2 and 3 live view runs, 4 end)
.equ LFLAG,  0x602be8c4   # new byte L: "peaking is on", set once per frame (unused slot 20 of table 0x602BE874)
.equ RFLAG,  0x602be8c5   # new byte R: 1 from entryMfAssistOn to entryMfAssistOff of the MF Assist state object
.equ L2FLAG, 0x602be8c6   # new byte L2: the value of L when the live-view update last ran (read by the art task)
.equ LV,     0x605b1cd0   # live-view parameter struct (getter 0x7E6ECFB6, index 0)
.equ MOVST,  0x605b039c   # movie state byte (getter 0x7E6CA934)
.equ EXPG,   0xa07507cc   # ucExpose of the live-view job (global copy)
"""

# name: (site, replaced length, section, what)
HOOKS = {
    "A":  (0x7E6ECF91, 6, "latch: end of the live-view struct refresh 0x7E6ECCAF (E-P5 0x7E3CA361 calls 0x7E3CA4B5)"),
    "B":  (0x7E6CC14E, 5, "colour-tone getter 0x7E6CBFD3, exit (E-P5 0x7E3A8A26)"),
    "C":  (0x7E6C614C, 7, "expose setter 0x7E6C610B (E-P5 0x7E3A2482)"),
    "D1": (0x7E6C7596, 5, "job setup 0x7E6C74BE, early exit (E-P5 0x7E3A39F1 -> 0x7E3A3AA6)"),
    "D2": (0x7E6C764E, 5, "job setup 0x7E6C74BE, normal exit (E-P5 0x7E3A3AA6)"),
    "E1": (0x7E6CD9CF, 7, "mov_art_set_line_yc_param 0x7E6CD9C5, art code test (E-P5 0x7E3AA358)"),
    "E2": (0x7E6CDAC6, 5, "mov_art_set_line_yc_param, line-job parameters (E-P5 0x7E3AA403)"),
    "G":  (0x7E6CCA81, 5, "art packet proc kind 0x7E6CCA57 (E-P5 0x7E3A9391)"),
    "H":  (0x7E6C3868, 5, "frame time 0x7E6C365F (E-P5 0x7E39F946)"),
    "I":  (0x7E6DAF37, 6, "img_param_set_ucType 0x7E6DAE68 (E-P5 0x7E3B7BF1)"),
    "F":  (0x7E6CCE6D, 6, "mov_art_set_artpacket 0x7E6CCBE1, CLIP / SIMPLE skip (E-P5 0x7E3A979D)"),
    "J":  (0x7E726421, 7, "Key Line art pass 7 0x7E7262F1 (E-P5 0x7E4072D0: ucExpose 3)"),
    "K":  (0x7E726767, 6, "Key Line art pass 9 0x7E7266D9, gain of the line image (E-P5 0x7E407718)"),
    "ON": (0x7EB7D46C, 7, "CmpSts_MfAssist::entryMfAssistOn (common part after both entry forms): R = 1"),
    "OFF": (0x7EB7D43B, 7, "CmpSts_MfAssist::entryMfAssistOff: R = 0"),
    "M":  (0x7E7149B6, 7, "image-work heap chooser 0x7E714833, its last call: mode 1 while the latch is set (E-P5 0x7E3F41DD chooses by setting)"),
}

ASM_P = """
.section .k,"ax"
getL:                           # d0 = flag, Z set when the flag is 1
    movbu (LFLAG),d0
    cmp 1,d0
    retf [],0

.section .k,"ax"
T_A:                            # d0 = value for struct+36 (stock store)
    mov LV,a1
    mov d0,(36,a1)
    clr d1
    mov (32,a1),d0              # movie variant requested: off (E-P5 0x7E3AD278)
    cmp 0,d0
    bne 1f
    movbu (MOVST),d0            # movie state 1: off (E-P5 0x7E3AD273)
    cmp 1,d0
    beq 1f
    movbu (RFLAG),d0            # request (E-P5: record +136): the MF Assist state object is in state "On"
    cmp 0,d0
    beq 1f
    call 0x7e6cff23,[],0            # live-view kinds 2 and 5: off (E-P5 0x7E3AD288)
    cmp 2,d0
    beq 1f
    cmp 5,d0
    beq 1f
    inc d1
    clr d0
    movbu d0,(4,a1)             # E-P5 0x7E3CA4E5
    inc d0
    movbu d0,(5,a1)             # art filter type 1: art_GetFilterType(119, 1) = 163 (Key Line I), whatever setting 17601 holds
1:  movbu d1,(LFLAG)
    ret [],32

T_B:
    call getL,[],0
    bne 2f
    cmp 0,a2
    beq 1f
    mov 119,d0                  # Key Line's picture mode (E-P5: 201)
    movbu d0,(a2)
1:  mov 3,d2                    # E-P5 helper 0x7E3AA601 returns 3
2:  mov d2,d0                   # stock
    extbu d0
    ret [d2,d3,a2,a3],20

T_C:
    mov d0,d1
    call getL,[],0
    movbu d0,(L2FLAG)           # the art task follows the state of this update (flags are kept)
    bne 1f
    mov 163,d0                  # Key Line's art code (E-P5: 188)
    movbu d0,(13,sp)
2:  jmp 0x7e6c6159
1:  mov d1,d0
    cmp 100,d0                  # stock
    bge 2b
    movbu d0,(13,sp)
    jmp 0x7e6c6153

T_D1:
    bne 3f                      # stock: beq 0x7E6C759B, else return
    jmp 0x7e6c759b
T_D2:
    call 0x7e6cdda3,[d2,a2,a3],16   # stock
3:  call getL,[],0
    bne 4f
    mov 3,d0                    # plain picture below the lines (E-P5 0x7E3A3AB2)
    movbu d0,(EXPG)
    mov (a3),a0
    movbu d0,(79,a0)            # ucExpose
    mov 2,d0
    movbu d0,(83,a0)            # ucColor
4:  ret [d2,d3,a2,a3],48

T_H:
    call getL,[],0
    bne 1f
    mov 85,d3
1:  mov a2,d0                   # stock
    exthu d0
    cmp 1,d0
    jmp 0x7e6c386d

T_I:
    cmp 184,d0                  # stock
    beq 1f
    call getL,[],0
    bne 2f
1:  jmp 0x7e6daf3d
2:  jmp 0x7e6daf57
"""

ASM_P2 = """
.section .k,"ax"
T_G:
    call getL,[],0
    bne 1f
    jmp 0x7e6ccab4              # return 0
1:  call 0x7e6cff23,[],0            # stock
    jmp 0x7e6cca86
"""

ASM_U = """
.section .k,"ax"
T_E1:
    call getL,[],0
    beq 1f                      # flag: take Key Line's branch
    movbu (79,a1),d0            # stock
    cmp 163,d0
1:  jmp 0x7e6cd9d6

T_E2:
    movbu d0,(89,a3)            # stock: ucArtLpf of the line job
    call getL,[],0
    bne 1f
    mov 163,d0                  # the line job stays a stock Key Line line job
    movbu d0,(79,a3)
1:  mov 3,d0                    # stock: ucProcCount 3 follows
    jmp 0x7e6cdacb

T_F:
    call getL,[],0
    bne 1f
    clr d0                      # do not skip the line job
    jmp 0x7e6cce99
1:  mov (16,sp),d0              # stock
    cmp 4,d0
    beq 2f
    jmp 0x7e6cce7e
2:  jmp 0x7e6cce73

.section .u,"ax"
T_ON:                           # CmpSts_MfAssist::entryMfAssistOn
    mov a0,a2                   # stock
    mov 1,d0
    movbu d0,(RFLAG)
    mov 0x7ec8a85c,d0           # stock
    jmp 0x7eb7d473

T_OFF:                          # CmpSts_MfAssist::entryMfAssistOff
    mov a0,a2                   # stock
    clr d0
    movbu d0,(RFLAG)
    mov 0x7ec8a838,d0           # stock
    jmp 0x7eb7d442

.section .k,"ax"
T_M:                            # d0 = heap mode that the stock chooser picked from the settings (0, 1 or 2)
    mov d0,d1
    call getL,[],0
    bne 1f
    mov (MOVSM),d0              # only while live view runs (states 1 to 3); capture and playback keep stock
    add -1,d0
    cmp 2,d0
    bhi 1f
    mov 1,d1                    # the heap mode of the art filters with work buffers
1:  mov d1,d0
    call 0x7e578c60,[d2,d3],24  # stock
    ret [d2,d3,a2,a3],32        # stock

T_J:
    mov (a2),a0                 # stock
    mov 2,d0
    movbu d0,(90,a0)
    mov (32,sp),a1              # art packet
    movhu (a1),d0
    cmp 2,d0                    # live-view packet only
    bne 1f
    movbu (L2FLAG),d0
    cmp 1,d0
    bne 1f
    mov 3,d0
    movbu d0,(79,a0)            # ucExpose of the colour job of pass 7
1:  jmp 0x7e726428

T_K:
    movhu (a2),d0               # art packet: live-view packet only
    cmp 2,d0
    bne 1f
    movbu (L2FLAG),d0
    cmp 1,d0
    bne 1f
    mov GAIN,d0                 # usGain2: 256 = +1.0, add the line image (white lines)
    bra 2f
1:  mov 65280,d0                # stock: usGain2 = -1.0 (dark lines)
2:  jmp 0x7e72676d
"""


def run(*a):
    return subprocess.run(a, check=True, capture_output=True, text=True).stdout


def branch_targets_inside(site, n, blk):
    """Addresses in (site, site+n) that a 4-byte word at any byte offset of block 0 holds (jump tables,
    callbacks). The experiment's script also looked for them in the disassembly listings build/map/functions.txt
    and linear.txt (no hit); those are build output, so this copy does not read them."""
    import struct
    lo, hi = site + 1, site + n
    hits = []
    want = {struct.pack("<I", a) for a in range(lo, hi)}
    for w in want:
        i = blk.find(w)
        if i >= 0:
            hits.append("word at 0x%X" % (BASE + i))
    return hits


def main():
    argv, gain = list(sys.argv[1:]), 256
    assert 0 < gain < 4096, "the dispatcher 0x7E70789B shifts the gain left by 3; it must stay a positive s16"
    out = os.path.join(ROOT, "data", "specs", "peaking-direct-4.json")
    work = argv[0]
    listing = argv[1] if len(argv) > 1 else None
    os.makedirs(work, exist_ok=True)
    blk = payloads()[0]
    asm = SYMS + ".equ GAIN, %d\n" % gain + ASM_P + ASM_P2 + ASM_U
    args = []
    # A numeric operand of jmp/call would be taken as a displacement. Name each stock address and let
    # the linker compute the pc-relative value.
    for a in sorted(set(re.findall(r"(?:jmp|call)\s+0x([0-9a-f]{8})", asm))):
        args.append("--defsym=s_%s=0x%s" % (a, a))
    asm = re.sub(r"((?:jmp|call)\s+)0x([0-9a-f]{8})", r"\1s_\2", asm)
    for hook, (site, n, _) in HOOKS.items():
        asm += '\n.section .h%s,"ax"\n    jmp T_%s\n' % (hook, hook) + "    nop\n" * (n - 5)
        args.append("--section-start=.h%s=%#x" % (hook, site))
    s, o, e = (os.path.join(work, "direct4." + x) for x in ("s", "o", "elf"))
    open(s, "w").write(asm)
    run(BIN + "/mn10300-elf-as", "-o", o, s)
    for name, (lo, _, _) in AREAS.items():
        args.append("--section-start=%s=%#x" % (name, lo))
    run(BIN + "/mn10300-elf-ld", *args, "-e", "0x7e4c9200", "-o", e, o)

    def sect(name):
        b = os.path.join(work, "sect.bin")
        run(BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", name, e, b)
        return open(b, "rb").read()

    def op(addr, new, why):
        off = addr - BASE
        return {"type": "bytes", "block": 0, "offset": hex(off),
                "expect": blk[off:off + len(new)].hex(), "new": new.hex(), "_addr": "0x%08X" % addr, "_why": why}

    ops, sizes = [], []
    for name, (lo, hi, what) in AREAS.items():
        b = sect(name)
        assert lo + len(b) <= hi, "%s overflow: %d bytes, %d free" % (name, len(b), hi - lo)
        ops.append(op(lo, b, "new code, %s (%d B)" % (what, len(b))))
        if name == ".k":
            assert ops[-1]["expect"] == "ff" * len(b)
        sizes.append("%s: %d bytes at 0x%X-0x%X (%d free after)" % (name, len(b), lo, lo + len(b), hi - lo - len(b)))
    for name, (site, n, why) in HOOKS.items():
        h = sect(".h" + name)
        assert len(h) == n and h[0] == 0xDC, (name, h.hex())
        bad = branch_targets_inside(site, n, blk)
        assert not bad, (name, bad)
        ops.append(op(site, h, "hook %s: jmp T_%s%s. %s" % (name, name, " + nop" * (n - 5), why)))
    spec = {
        "name": "peaking-direct-4",       # the loops above reuse the variable `name`
        "description": "DRAFT, not camera-tested. Replaces peaking-direct-3: the same routines at new addresses "
                       "(direct-3 broke the six-axis handler of the Velvia entry and the sleep routine, NOTES section "
                       "14)%s. Focus peaking in live view while the MF Assist state object is On: white edge lines "
                       "(Key Line's line image, added) over a plain picture. The image-work heap is put in the art "
                       "mode while the lines show. Photos are not changed. See "
                       "experiments/2026-11-14-focus-peaking/NOTES.md sections 12 to 14."
                       % ("" if gain == 256 else "; line gain %d in place of 256" % gain),
        "base": STOCK,
        "base_sha256": hashlib.sha256(open(os.path.join(ROOT, STOCK), "rb").read()).hexdigest(),
        "status": "draft; emulator-checked (single functions and scenario tests)",
        "_ram": "three new bytes 0x602BE8C4 (L), 0x602BE8C5 (R), 0x602BE8C6 (L2): slot 20 of the menu value-list "
                "table 0x602BE874, never indexed; reads the mov state number 0x605B03D0",
        "ops": ops,
    }
    json.dump(spec, open(out, "w"), indent=1)
    syms = run(BIN + "/mn10300-elf-nm", "-n", e)
    print("wrote", os.path.relpath(out, ROOT))
    print("\n".join(sizes))
    if listing:
        txt = "Symbols\n" + "\n".join(l for l in syms.splitlines() if " t " in l or " T " in l) + "\n\n"
        txt += run(BIN + "/mn10300-elf-objdump", "-d", "-j", ".k", "-j", ".u", e)
        for name in HOOKS:
            txt += run(BIN + "/mn10300-elf-objdump", "-d", "-j", ".h" + name, e).split("Disassembly of section")[1]
        open(listing, "w").write(re.sub(r"/[^\s:]*direct4\.elf", "direct4.elf", txt))


main()
