"""Write data/specs/peaking-mf.json: focus peaking whenever the focus mode is MF
(experiments/2026-11-21-peaking-mf/NOTES.md).

    uv run python gen/peaking/mkspec_mf.py [WORKDIR]

Peaking shows when T_R (custom-menu-rows-3, called by the latch T_A at the end of the per-frame struct refresh
0x7E6ECCAF) returns 1: today when R (MF Assist On, set by the focus-ring events) is 1 and the Peaking setting is not
Off. This spec adds a second trigger: R = 0 but the focus mode in use is MF. The focus mode in use is prm 0xC021
(info 25; the mode controller copies AF Mode > Still Picture into it), MF = 1. The first three instructions of T_R
(`movbu (R),d0 / cmp 0,d0 / beq 2f`, 10 bytes) become `jmp T_MF`; T_MF (segment 2) does the same test and, when R is
0, reads prm 0xC021 with the getter 0x7E457C75 (as T_R reads the Peaking setting) and goes on to T_R's test of the
Peaking setting only when it is 1. Every other condition of the latch stays: no movie, live-view kind not 2 or 5,
T_GUARD. In MF there are no lines from the half-press to the end of the record view: T_GS, at the GUI state setter's
hook, keeps the GUI state, and T_MF3 refuses 0x5101. The base is the specs that data/builds/peaking-mf.json lists
before this one.
"""
import hashlib, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import BIN, ROOT, STOCK, payloads  # noqa: E402

BASE = 0x7E421020
SPEC, BUILD = "data/specs/peaking-mf.json", "data/builds/peaking-mf.json"
T_R, T_R_OLD = 0x7E4C93A4, "fca8c5e82b60a000c829"     # movbu (0x602be8c5),d0 / cmp 0,d0 / beq 0x7e4c93d5
T_R_CONT, T_R_RET0 = 0x7E4C93AE, 0x7E4C93D5           # T_R: its test of setting 458; its `ret [],4` (d0 = 0)
AREAS = {".ma": (0x7ECB0B81, 0x7ECB0BA0), ".mb": (0x7ECB0FD8, 0x7ECB1000),     # free runs of segment 2
         ".mc": (0x7EBF3B94, 0x7EBF3BAD), ".md": (0x7EBF2F20, 0x7EBF2F40)}     # (tools/freespace.py area)
GUI_HOOK, GUI_OLD, GUI_NEXT = 0x7ECDF6E4, "dc772ff1ff", 0x7EBF265B   # the GUI state setter's hook: `jmp` log-menu's T_GUI
GS = 0x7E4F67F0 + 0x40000000   # u16, uncached: the last film RAM block's unused tail (+0x31F0; the loader writes up to +0x30B2)

ASM = """
.equ RFLAG, 0x602be8c5       # R: the MF Assist state object is On (peaking-direct-4)
.equ LV,    0x605b1cd0       # live-view parameter struct: a1 at T_R's call site
.equ GSTATE, %(gs)#x         # u16: the GUI state, written by T_GS
.section .ma,"ax"
T_MF:                        # from T_R, in place of `movbu (R),d0 / cmp 0,d0 / beq 2f`
    movbu (RFLAG),d0
    cmp 0,d0
    beq 2f
    jmp s_%(cont)x           # MF Assist On: T_R's test of the Peaking setting, as before
2:  jmp T_MF2
    nop                      # an op must not end in a 0xFF byte (the free-space ledger counts changed bytes only)
.section .mb,"ax"
T_MF2:                       # R = 0: peaking only when the focus mode in use is MF
    mov 0xc021,d0            # prm 0xC021: the focus mode in use (info 25); MF = 1
    mov 0,a0
    clr d1
    call s_7e457c75,[d2,d3],12
    cmp 1,d0
    bne T_NO
    jmp T_MF3
T_NO:                        # no lines: a1 and d1 as T_R's caller had them
    mov LV,a1
    clr d1
    clr d0
    jmp s_%(ret0)x           # T_R's `ret [],4`
    nop
.section .mc,"ax"
T_MF3:                       # MF: not from the half-press to the end of the record view (GUI state 0x5101), where
    movhu (GSTATE),d0        # MF Assist ends too
    cmp 0x5101,d0
    beq 1f
    jmp s_%(cont)x           # T_R's test of the Peaking setting (Off = no lines)
1:  jmp T_NO
    nop
.section .md,"ax"
T_GS:                        # from the GUI state setter's hook: d0 = the new GUI state
    movhu d0,(GSTATE)
    jmp s_%(gnext)x          # on to log-menu's T_GUI, as before
    nop
.section .hr,"ax"
    jmp T_MF
    nop
    nop
    nop
    nop
    nop
.section .hg,"ax"
    jmp T_GS
""" % {"ret0": T_R_RET0, "cont": T_R_CONT, "gs": GS, "gnext": GUI_NEXT}


def run(*a):
    return subprocess.run(a, check=True, capture_output=True, text=True).stdout


def main():
    os.chdir(ROOT)
    build = json.load(open(BUILD))
    assert build["specs"][-1] == SPEC
    names = [os.path.basename(p)[:-5] for p in build["specs"][:-1]]
    blk = payloads(names)[0]
    get = lambda a, n: blk[a - BASE:a - BASE + n]
    assert get(T_R, 10).hex() == T_R_OLD, get(T_R, 10).hex()
    assert get(GUI_HOOK, 5).hex() == GUI_OLD, get(GUI_HOOK, 5).hex()
    work = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "peaking-mf")
    os.makedirs(work, exist_ok=True)
    s, o, e = (os.path.join(work, "mf." + x) for x in ("s", "o", "elf"))
    src = ASM
    calls = sorted(set(re.findall(r"(?:jmp|call)\s+s_([0-9a-f]{8})", src)))
    open(s, "w").write(src)
    run(BIN + "/mn10300-elf-as", "-o", o, s)
    run(BIN + "/mn10300-elf-ld", *["--defsym=s_%s=0x%s" % (a, a) for a in calls],
        *["--section-start=%s=%#x" % (k, v[0]) for k, v in AREAS.items()], "--section-start=.hr=%#x" % T_R, "--section-start=.hg=%#x" % GUI_HOOK,
        "-e", "%#x" % AREAS[".ma"][0], "-o", e, o)

    def sect(name):
        b = os.path.join(work, "sect.bin")
        run(BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", name, e, b)
        return open(b, "rb").read()
    parts, hook, ghook = {k: sect(k) for k in AREAS}, sect(".hr"), sect(".hg")
    for k, (lo, hi) in AREAS.items():
        assert lo + len(parts[k]) <= hi, (k, len(parts[k]))
    assert len(hook) == 10 and len(ghook) == 5
    open(os.path.join(work, "listing.txt"), "w").write(run(BIN + "/mn10300-elf-objdump", "-d", e))
    ops = [{"type": "bytes", "block": 0, "offset": "%#x" % (AREAS[k][0] - BASE), "expect": get(AREAS[k][0], len(parts[k])).hex(),
            "new": parts[k].hex(), "_addr": "%#010x" % AREAS[k][0],
            "_note": "new code, segment 2: %s (%d B)" % ({".ma": "T_MF (the test of R)", ".mb": "T_MF2 (the focus mode)",
                                                      ".mc": "T_MF3 (GUI state 0x5101: no lines)", ".md": "T_GS (keeps the GUI state)"}[k],
                                                     len(parts[k]))} for k in AREAS]
    ops += [{"type": "bytes", "block": 0, "offset": "%#x" % (T_R - BASE), "expect": T_R_OLD, "new": hook.hex(),
            "_addr": "%#010x" % T_R, "_note": "T_R (custom-menu-rows-3): `movbu (R),d0 / cmp 0,d0 / beq` -> `jmp T_MF` + nop"},
           {"type": "bytes", "block": 0, "offset": "%#x" % (GUI_HOOK - BASE), "expect": GUI_OLD, "new": ghook.hex(),
            "_addr": "%#010x" % GUI_HOOK, "_note": "the GUI state setter's hook (log-menu-3): `jmp T_GUI` -> `jmp T_GS`, which jumps on to T_GUI"}]
    spec = {"name": "peaking-mf",
            "description": "Focus peaking whenever the focus mode in use is MF (prm 0xC021 = 1), with any lens and "
                           "without the magnified view; the focus-ring trigger (MF Assist) as before. T_R's test of R "
                           "goes through T_MF in segment 2. experiments/2026-11-21-peaking-mf/NOTES.md.",
            "base": STOCK, "base_sha256": hashlib.sha256(open(STOCK, "rb").read()).hexdigest(), "ops": ops}
    json.dump(spec, open(SPEC, "w"), indent=1); open(SPEC, "a").write("\n")
    print(f"{SPEC}: " + ", ".join(f"{k} {len(v)} B at {AREAS[k][0]:#x}" for k, v in parts.items()) + f"; hooks at {T_R:#x}, {GUI_HOOK:#x}")


if __name__ == "__main__":
    main()
