"""Write data/specs/log-movie-time.json: the timing probe of the 1080 movie path (NOTES.md in this folder).

    uv run python experiments/2026-11-19-movie-sampling/scripts/mkspec_movtime.py PINNED_DIR WORKDIR [LISTING.txt]
    PINNED_DIR  `uv run python tools/oetool.py unpack build/epm2mod-2026.11.19.BIN PINNED_DIR`
    WORKDIR     scratch folder for the assembler files (outside the repository)

Research code. A delta on the pinned build data/builds/epm2mod-2026.11.19.json: every `expect` is a byte string of
that build, and every hook site is in stock bytes. Events (data/logdict/events.json): mv_frame (CPU 0, one record per
recorded movie frame) and mv_enc (CPU 1, one record per MOV_ENCODE packet). Five hooks, all in segment 1, and their
routines in segment 1 (the free part of lss-core's area). It puts the build id of data/logdict/events.json into the
flush task of log-menu-2.
"""

import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "experiments", "2026-11-15-log", "scripts"))
import mkspec_log as L  # noqa: E402

SPEC = "log-movie-time"
BASE = L.BASE
AREA = (0x7E69EC6B, 0x7E69EEAF)      # segment 1: auto-iso-min-shutter NOTES section 9, free after lss-core
FLUSH = (0x7EBF2BE4, 0x7EBF2E80)     # log-menu-2's flush task: the two words of the build id
OLD_ID = "33ca8d15f4f1c877"          # data/specs/log-menu-2.json
SITES = {   # site: (bytes, routine, what)
    0x7E6C6E46: (5, "T_MVS", "mov_image_process (record) 0x7E6C6E46, entry: `add -512,sp` / `clr d2` (MOV_TASK)"),
    0x7E6C721D: (5, "T_MVE", "mov_image_process (record), end: `exthu d0` / `add 512,sp` before `ret`"),
    0x7E6C7490: (7, "T_DEV", "0x7E6C7225 (built from 0x7E6C8841): the develop job, `call 0x7E6DABAF` (mov img_exec)"),
    0x7E72CC54: (6, "T_ART", "ART_SUB task loop (CPU 1): `mov a2,a0` / `call 0x7E72CD3E`, the handler of a message"),
    0x7E6D55A7: (6, "T_ENCA", "MOV_ENCODE task loop (CPU 1): `mov a2,a0` / `call 0x7E6D5641` (packet command 256)"),
    0x7E6D55AF: (6, "T_ENCB", "MOV_ENCODE task loop (CPU 1): `mov a2,a0` / `call 0x7E6D564D` (other commands)"),
}

ASM = """
.equ MVS,      0xbe4fd300    # 32 bytes after the log's state and block buffer (uncached alias of 0x7E4FD300)
.equ MV_T0,    MVS+0         # timer at the entry of mov_image_process (record)
.equ MV_DEV,   MVS+4         # microseconds in the develop job in this run
.equ MV_TD,    MVS+8         # timer before the develop job
.equ MV_TA,    MVS+12        # CPU 1: timer before the ART_SUB handler
.equ MV_ASUM,  MVS+16        # CPU 1: running sum of ART_SUB microseconds
.equ MV_ALAST, MVS+20        # CPU 1: MV_ASUM at the last mv_enc record
.equ MV_TE,    MVS+24        # CPU 1: timer before the MOV_ENCODE handler
.section .mv,"ax"

T_MVS:                       # entry: the next two instructions set the flags again
    movm [other],(sp)
    mov (TIMER),d0
    mov d0,(MV_T0)
    mov 0,d0
    mov d0,(MV_DEV)
    movm (sp),[other]
%(d_T_MVS)s
    jmp %(b_T_MVS)s

T_MVE:                       # end: d0 = the return value; the flags are not used after this
    movm [d2,other],(sp)
    mov (TIMER),d2
    mov (MV_T0),d1
    sub d2,d1
    and 0x3fffffff,d1        # arg0: microseconds from the entry (the timer counts down, 30 bits)
    mov (MV_DEV),d2
    cmp 0xffff,d2
    bls 1f
    mov 0xffff,d2
1:  exthu d0
    asl 16,d0
    or d0,d2
    mov d2,a0                # arg1: develop_us | ret << 16
    mov %(mv_frame)d,d0
    call log_put,[],0
    movm (sp),[d2,other]
%(d_T_MVE)s
    jmp %(b_T_MVE)s

T_DEV:                       # the develop job; the caller uses d0 after it and no flags
    movm [other],(sp)
    mov (TIMER),d1
    mov d1,(MV_TD)
    movm (sp),[other]
%(d_T_DEV)s
    movm [d2,other],(sp)
    mov (MV_TD),d1
    mov (TIMER),d2
    sub d2,d1
    and 0x3fffffff,d1
    mov (MV_DEV),d2
    add d1,d2
    mov d2,(MV_DEV)
    movm (sp),[d2,other]
    jmp %(b_T_DEV)s

T_ART:                       # ART_SUB (CPU 1): the loop branches back after it
    movm [other],(sp)
    mov (TIMER),d1
    mov d1,(MV_TA)
    movm (sp),[other]
%(d_T_ART)s
    movm [d2,other],(sp)
    mov (MV_TA),d1
    mov (TIMER),d2
    sub d2,d1
    and 0x3fffffff,d1
    mov (MV_ASUM),d2
    add d1,d2
    mov d2,(MV_ASUM)
    movm (sp),[d2,other]
    jmp %(b_T_ART)s
""" + "".join("""
T_ENC%(k)s:                     # MOV_ENCODE (CPU 1): d0 = the handler's result, kept
    movm [other],(sp)
    mov (TIMER),d1
    mov d1,(MV_TE)
    movm (sp),[other]
%%(d_T_ENC%(k)s)s
    movm [d2,other],(sp)
    mov (MV_TE),d1
    mov (TIMER),d2
    sub d2,d1
    and 0x3fffffff,d1
    or %(kind)s,d1             # arg0: microseconds | kind << 31
    mov (MV_ASUM),d2
    mov (MV_ALAST),a0
    mov d2,(MV_ALAST)
    sub a0,d2
    mov d2,a0                # arg1: ART_SUB microseconds since the last record
    mov %%(mv_enc)d,d0
    call log_put,[],0
    movm (sp),[d2,other]
    jmp %%(b_T_ENC%(k)s)s
""" % {"k": k, "kind": kind} for k, kind in (("A", "0"), ("B", "0x80000000")))


def main():
    """Assemble the routines and the hooks, check every site, write the spec."""
    base, work = sys.argv[1:3]
    listing = sys.argv[3] if len(sys.argv) > 3 else None
    os.makedirs(work, exist_ok=True)
    blk_path = os.path.join(base, "block0_0100.bin")
    blk = open(blk_path, "rb").read()
    get = lambda a, n: blk[a - BASE:a - BASE + n]
    stock = open(os.path.join(ROOT, "build/blocks", os.path.basename(L.STOCK) + ".block0.bin"), "rb").read()
    d = json.load(open(os.path.join(ROOT, "data/logdict/events.json")))
    ids = {e["name"]: e["id"] for e in d["events"] if e["spec"] == SPEC}
    assert sorted(ids) == ["mv_enc", "mv_frame"], ids
    bid = L.build_id(d["events"])
    # log_put of log-menu-2: the third of three entries `movm [d2,d3,a2,a3],(sp)` / `mov psw,d2` at the start of the
    # kernel run, followed by the switch `movbu (LOGON),d3`
    lo = 0x7E4C9514
    head = bytes.fromhex("cff0f2e6")
    at = [lo + i for i in range(0x40) if get(lo + i, 4) == head]
    assert len(at) == 3 and get(at[2] + 4, 6) == bytes.fromhex("fcab42d04fbe"), at
    bad = L.branch_targets_inside([(s, n) for s, (n, _, _) in SITES.items()], blk, work)
    assert not bad, bad
    val = dict(ids)
    for site, (n, routine, _) in SITES.items():
        assert get(site, n) == stock[site - BASE:site - BASE + n], "site 0x%X is not in stock bytes" % site
        val["d_" + routine] = L.displaced(blk_path, site, n)
        val["b_" + routine] = "0x%08x" % (site + n)

    asm = L.SYMS + ASM % val
    args = ["--defsym=log_put=%#x" % at[2]]
    args += ["--defsym=s_%s=0x%s" % (a, a) for a in sorted(set(re.findall(r"(?:jmp|call)\s+0x([0-9a-f]{8})", asm)))]
    asm = re.sub(r"((?:jmp|call)\s+)0x([0-9a-f]{8})", r"\1s_\2", asm)
    for site, (n, routine, _) in SITES.items():
        asm += '\n.section .s%x,"ax"\n    jmp %s\n' % (site, routine) + "    nop\n" * (n - 5)
        args.append("--section-start=.s%x=%#x" % (site, site))
    args.append("--section-start=.mv=%#x" % AREA[0])
    s, o, e, sb = (os.path.join(work, "movtime." + x) for x in ("s", "o", "elf", "bin"))
    open(s, "w").write(asm)
    L.run(L.BIN + "/mn10300-elf-as", "-o", o, s)
    L.run(L.BIN + "/mn10300-elf-ld", *args, "-e", "%#x" % AREA[0], "-o", e, o)

    def sect(name):
        L.run(L.BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", name, e, sb)
        return open(sb, "rb").read()

    ops = []

    def op(addr, new, note):
        expect = get(addr, len(new))
        assert expect != new, note
        ops.append({"type": "bytes", "block": 0, "offset": "0x%X" % (addr - BASE), "expect": expect.hex(),
                    "new": new.hex(), "_addr": "0x%08X" % addr, "_note": note})

    code = sect(".mv")
    a, hi = AREA
    assert a + len(code) <= hi, "%d B, %d free" % (len(code), hi - a)
    assert get(a, hi - a) == stock[a - BASE:hi - BASE], "the area is in use"
    if code[-1] == get(a + len(code) - 1, 1)[0]:
        code += b"\xcb"                      # the free-space ledger counts only changed bytes: end on a nop
    op(a, code, "new code, segment 1 (free part of lss-core's area): T_MVS, T_MVE, T_DEV, T_ART, T_ENCA, T_ENCB "
       "(%d B)" % len(code))
    print("routines: %d B at 0x%X-0x%X, %d B free after" % (len(code), a, a + len(code), hi - a - len(code)))
    for site, (n, routine, what) in SITES.items():
        h = sect(".s%x" % site)
        assert len(h) == n and h[0] == 0xDC
        op(site, h, "hook (%s): jmp %s%s. %s" % ("mv_frame" if site < 0x7E6C8000 else "mv_enc", routine,
                                                " + nop" * (n - 5), what))
    old = bytes.fromhex(OLD_ID)
    assert bid != old
    for half in (0, 4):                      # the two `mov imm32,d0` of the flush task that hold the build id
        word = b"\xfc\xcc" + old[half:half + 4]
        i = blk.find(word)
        assert i >= 0 and blk.find(word, i + 1) < 0 and FLUSH[0] <= BASE + i < FLUSH[1], half
        op(BASE + i + 2, bid[half:half + 4], "flush task, block header: build id bytes %d-%d %s -> %s "
           "(data/logdict/events.json)" % (half, half + 3, old[half:half + 4].hex(), bid[half:half + 4].hex()))
    out = os.path.join(ROOT, "data", "specs", SPEC + ".json")
    json.dump({
        "name": SPEC,
        "description": "Structured log, timing probe of the movie path: event mv_frame (CPU 0), one record per run of "
                       "mov_image_process for recording 0x7E6C6E46 (one movie frame): the microseconds from its entry "
                       "to its end, the microseconds of its develop job (img_exec, Bayer to YC) and its return value; "
                       "event mv_enc (CPU 1), one record per packet of the task MOV_ENCODE: the microseconds in its "
                       "handler and the microseconds that the task ART_SUB spent since the last record. Five hooks in "
                       "stock bytes of segment 1, their routines in segment 1, 32 bytes of RAM at 0x7E4FD300. Needs "
                       "the specs of data/builds/epm2mod-2026.11.19.json before it: every expect is a byte string of "
                       "that build. It puts the build id %s of data/logdict/events.json into the block header. DEBUG "
                       "builds only. See experiments/2026-11-19-movie-sampling/NOTES.md and "
                       "docs/reference/logging.md." % bid.hex(),
        "base": L.STOCK, "base_sha256": hashlib.sha256(open(os.path.join(ROOT, L.STOCK), "rb").read()).hexdigest(),
        "status": "candidate: emulator-checked, not flashed",
        "_delta_on": "data/builds/epm2mod-2026.11.19.json",
        "_build_id": bid.hex(),
        "_ram": "32 bytes at 0x7E4FD300 (uncached alias 0xBE4FD300), after the log's block buffer; not cleared at start",
        "ops": ops,
    }, open(out, "w"), indent=1)
    open(out, "a").write("\n")
    print("wrote", os.path.relpath(out, ROOT), len(ops), "ops; build id", bid.hex())
    if listing:
        txt = L.run(L.BIN + "/mn10300-elf-objdump", "-d", "-j", ".mv", *sum((["-j", ".s%x" % x] for x in SITES), []), e)
        open(listing, "w").write(re.sub(r"/[^\s:]*movtime\.elf", "movtime.elf", txt))


if __name__ == "__main__":
    main()
