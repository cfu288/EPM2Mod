"""Write data/specs/peaking-mf.json and data/builds/peaking-mf.json: focus peaking whenever the focus mode is MF.
Research code (NOTES.md).

    uv run python experiments/2026-11-21-peaking-mf/scripts/mkspec.py

Peaking shows when T_R (custom-menu-rows-3, called by the latch T_A at the end of the per-frame struct refresh
0x7E6ECCAF) returns 1: today when R (MF Assist On, set by the focus-ring events) is 1 and the Peaking setting is not
Off. This spec adds a second trigger: R = 0 but the focus mode in use is MF. The focus mode in use is prm 0xC021
(info 25; the mode controller copies AF Mode > Still Picture into it), MF = 1. The first three instructions of T_R
(`movbu (R),d0 / cmp 0,d0 / beq 2f`, 10 bytes) become `jmp T_MF`; T_MF (segment 2) does the same test and, when R is
0, reads prm 0xC021 with the getter 0x7E457C75 (as T_R reads the Peaking setting) and goes on to T_R's test of the
Peaking setting only when it is 1. Every other condition of the latch stays: no movie, live-view kind not 2 or 5,
T_GUARD. The build is the pinned films-twelve-off with this spec.
"""
import hashlib, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "gen", "peaking"))
from base import BIN, ROOT as _R, STOCK, payloads  # noqa: E402

BASE = 0x7E421020
PINNED = "data/builds/films-twelve-off.json"
SPEC, BUILD = "data/specs/peaking-mf.json", "data/builds/peaking-mf.json"
T_R, T_R_OLD = 0x7E4C93A4, "fca8c5e82b60a000c829"     # movbu (0x602be8c5),d0 / cmp 0,d0 / beq 0x7e4c93d5
T_R_CONT, T_R_RET0 = 0x7E4C93AE, 0x7E4C93D5           # T_R: its test of setting 458; its `ret [],4` (d0 = 0)
AREA = (0x7EBF2E68, 0x7EBF2E9A)                       # a free run of segment 2 (tools/freespace.py area 0x7EBF1090)

ASM = """
.equ RFLAG, 0x602be8c5       # R: the MF Assist state object is On (peaking-direct-4)
.equ LV,    0x605b1cd0       # live-view parameter struct: a1 at T_R's call site
.section .mf,"ax"
T_MF:                        # from T_R, in place of `movbu (R),d0 / cmp 0,d0 / beq 2f`
    movbu (RFLAG),d0
    cmp 0,d0
    bne 1f                   # MF Assist On: T_R as before
    mov 0xc021,d0            # prm 0xC021: the focus mode in use (info 25); MF = 1
    mov 0,a0
    clr d1
    call s_7e457c75,[d2,d3],12
    mov LV,a1                # a1 and d1 as T_R's caller had them
    clr d1
    cmp 1,d0
    beq 1f
    clr d0
    jmp s_%(ret0)x           # not MF: T_R's `ret [],4`, no lines
1:  jmp s_%(cont)x           # T_R's test of the Peaking setting (Off = no lines)
    nop                      # the op must not end in a 0xFF byte (the free-space ledger counts changed bytes only)
.section .hr,"ax"
    jmp T_MF
    nop
    nop
    nop
    nop
    nop
""" % {"ret0": T_R_RET0, "cont": T_R_CONT}


def run(*a):
    return subprocess.run(a, check=True, capture_output=True, text=True).stdout


def main():
    os.chdir(ROOT)
    build = json.load(open(PINNED))
    names = [os.path.basename(p)[:-5] for p in build["specs"]]
    blk = payloads(names)[0]
    get = lambda a, n: blk[a - BASE:a - BASE + n]
    assert get(T_R, 10).hex() == T_R_OLD, get(T_R, 10).hex()
    work = os.path.join(ROOT, "build", "peaking-mf"); os.makedirs(work, exist_ok=True)
    s, o, e = (os.path.join(work, "mf." + x) for x in ("s", "o", "elf"))
    src = ASM
    calls = sorted(set(re.findall(r"(?:jmp|call)\s+s_([0-9a-f]{8})", src)))
    open(s, "w").write(src)
    run(BIN + "/mn10300-elf-as", "-o", o, s)
    run(BIN + "/mn10300-elf-ld", *["--defsym=s_%s=0x%s" % (a, a) for a in calls],
        "--section-start=.mf=%#x" % AREA[0], "--section-start=.hr=%#x" % T_R, "-e", "%#x" % AREA[0], "-o", e, o)

    def sect(name):
        b = os.path.join(work, "sect.bin")
        run(BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", name, e, b)
        return open(b, "rb").read()
    code, hook = sect(".mf"), sect(".hr")
    assert AREA[0] + len(code) <= AREA[1], len(code)
    assert len(hook) == 10                            # the area is reclaimed stock code, not 0xFF (freespace)
    open(os.path.join(work, "listing.txt"), "w").write(run(BIN + "/mn10300-elf-objdump", "-d", e))
    ops = [{"type": "bytes", "block": 0, "offset": "%#x" % (AREA[0] - BASE), "expect": get(AREA[0], len(code)).hex(),
            "new": code.hex(), "_addr": "%#010x" % AREA[0], "_note": "new code, segment 2: T_MF (%d B)" % len(code)},
           {"type": "bytes", "block": 0, "offset": "%#x" % (T_R - BASE), "expect": T_R_OLD, "new": hook.hex(),
            "_addr": "%#010x" % T_R, "_note": "T_R (custom-menu-rows-3): `movbu (R),d0 / cmp 0,d0 / beq` -> `jmp T_MF` + nop"}]
    spec = {"name": "peaking-mf",
            "description": "Focus peaking whenever the focus mode in use is MF (prm 0xC021 = 1), with any lens and "
                           "without the magnified view; the focus-ring trigger (MF Assist) as before. T_R's test of R "
                           "goes through T_MF in segment 2. experiments/2026-11-21-peaking-mf/NOTES.md.",
            "base": STOCK, "base_sha256": hashlib.sha256(open(STOCK, "rb").read()).hexdigest(), "ops": ops}
    json.dump(spec, open(SPEC, "w"), indent=1); open(SPEC, "a").write("\n")
    b = {"what": "TEST ONLY, not for use: films-twelve-off where focus peaking also shows whenever the focus mode is MF, "
                 "with any lens and without the magnified view (experiments/2026-11-21-peaking-mf/NOTES.md)",
         "stock": build["stock"], "specs": build["specs"] + [SPEC], "first_code": True, "label": build["label"]}
    json.dump(b, open(BUILD, "w"), indent=1); open(BUILD, "a").write("\n")
    print(f"{SPEC}: T_MF {len(code)} B at {AREA[0]:#x}; hook at {T_R:#x}")


if __name__ == "__main__":
    main()
