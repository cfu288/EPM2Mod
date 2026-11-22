"""Write data/specs/pana-ring-probe.json: the probe of what a Panasonic lens sends (NOTES.md in this folder).

    uv run python experiments/2026-11-22-pana-aperture-ring/scripts/mkspec.py WORKDIR [LISTING.txt]
    WORKDIR  scratch folder for the assembler files (outside the repository)

Research code, after experiments/2026-11-19-movie-sampling/scripts/mkspec_movtime.py. A delta on the pinned build
data/builds/peaking-mf.json: every `expect` is a byte string of that build, and every hook site is in stock bytes.
Events (data/logdict/events.json): pana_stat and pana_func through log-menu-3's log_chg; pana_pk84_0/1 and
pana_pk34_0/1 (16 bytes of the status packet around stat) through log_put, on a change and at most once per 0.5 s.
Four hooks in segment 1, their routines in segment 1 (the free part of lss-core's area), gates and keys in the free
tail of the log's state block, two timer words at 0x7E4FD300.
It puts the build id of data/logdict/events.json into the flush task of log-menu-3.
"""

import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "gen", "log-menu"))
sys.path.insert(0, os.path.join(ROOT, "cli", "src"))
import mkspec_log as L  # noqa: E402
from epm2mod.container import parse  # noqa: E402
from epm2mod.spec import BytesOp, load_spec  # noqa: E402

SPEC = "pana-ring-probe"
BUILD = "peaking-mf"                 # the pinned build this spec is a delta on
BASE = L.BASE
AREA = (0x7E69EC6B, 0x7E69EEAF)      # segment 1: auto-iso-min-shutter NOTES section 9, free after lss-core
FLUSH = (0x7EBF2BE4, 0x7EBF2DF8)     # log-menu-3's flush task (.uc): the two words of the build id
OLD_ID = "afe27672d672fc95"          # data/specs/log-menu-3.json
SITES = {   # site: (bytes, routine, what)
    0x7E5234D7: (6, "T_PS", "set_stat_pana 0x7E5234D7, entry: `movhu d0,(0x604f88ce)` (the next instruction, btst, "
                 "sets the flags)"),
    0x7E523495: (6, "T_PF", "set_func_flag_pana 0x7E523495, entry: `movhu d0,(0x604f8888)` (then exthu d0, btst)"),
    0x7E523A5B: (8, "T_PKA", "status parser 0x7E523915 (command 84), the read of stat: `mov a2,a0` / "
                 "`call 0x7E507F65` (a2 = stat in the packet; then exthu d0, call set_stat_pana)"),
    0x7E521343: (8, "T_PKB", "status parser 0x7E52128F (command 34), the read of stat after `add 3,a2`: `mov a2,a0` / "
                 "`call 0x7E507F65` (a2 = stat in the packet; then exthu d0, call set_stat_pana)"),
}
EVENTS = ["pana_func", "pana_pk34_0", "pana_pk34_1", "pana_pk84_0", "pana_pk84_1", "pana_stat"]

ASM = """
.equ G_PS,   PST+104         # gate of pana_stat {u32 last arg0, u8 budget 0}; PST+104..119 are free, cleared at start
.equ G_PF,   PST+112         # gate of pana_func
.equ L_STAT, 0x604f88ce      # u16 l_stat_pana
.equ L_FUNC, 0x604f8888      # u16 l_func_flag_pana
.equ L_FLAG, 0x604f7f64      # u8 Panasonic flags: 0x01 private data, 0x02 a function, 0x04 stat bit 0
.equ AV_EFF, 0x604f658c      # u16 av_effect: lens_info_get(0) 0x604F657C + 0x10, 1/256 EV
.equ LENSID, 0x604f67b0      # word read by the lens maker test 0x7E522622 (via 0x7E5223D6)
.equ K84,    PST+120         # u32 key of the last logged 16-byte window of command 84 (cleared at start)
.equ K34,    PST+124         # the same for command 34
.equ KT,     0x248           # key + KT: u32 timer value of that record, at 0x7E4FD300 / 0x7E4FD304 (not cleared)
.equ GAP,    500000          # microseconds: at most one record pair per window in this time
.section .pn,"ax"

T_PS:                        # d0 = the new l_stat_pana; every register is kept, the flags are not needed
%(d_T_PS)s
    movm [d2,other],(sp)
    exthu d0
    movhu (AV_EFF),d1
    asl 16,d1
    or d0,d1                 # arg0: stat | av_effect << 16 (the gate compares it)
    movbu (L_FLAG),d2
    asl 16,d2
    movhu (L_FUNC),d0
    or d0,d2
    mov d2,a0                # arg1: func | flags << 16
    mov G_PS,a1
    mov %(pana_stat)d,d0
    call log_chg,[],0
    movm (sp),[d2,other]
    jmp %(b_T_PS)s

T_PF:                        # d0 = the new l_func_flag_pana; every register is kept
%(d_T_PF)s
    movm [other],(sp)
    exthu d0
    mov d0,d1                # arg0: func
    mov (LENSID),a0          # arg1: the lens id word
    mov G_PF,a1
    mov %(pana_func)d,d0
    call log_chg,[],0
    movm (sp),[other]
    jmp %(b_T_PF)s

T_PKA:                       # command 84: the window is stat and the 14 bytes after it; every register is kept
    movm [other],(sp)
    mov a2,a0
    mov K84,a1
    mov %(pana_pk84_0)d,d0
    call pk_core,[d2,d3,a2,a3],28
    movm (sp),[other]
%(d_T_PKA)s
    jmp %(b_T_PKA)s

T_PKB:                       # command 34: the window is the 3 skipped bytes, stat and the 11 bytes after it
    movm [other],(sp)
    mov a2,a0
    add -3,a0
    mov K34,a1
    mov %(pana_pk34_0)d,d0
    call pk_core,[d2,d3,a2,a3],28
    movm (sp),[other]
%(d_T_PKB)s
    jmp %(b_T_PKB)s

# a0 = the window (16 bytes, any alignment), a1 = its key, d0 = the id of its first event (the second is id + 1).
# A record pair when the key of the window differs from the last logged one and GAP has passed since that record; a
# skipped change keeps the old key, so it is logged at the next packet after GAP. Frame 28: the four registers at
# (12,sp)-(27,sp) (the call's frame size includes them, as in the firmware's own frames), (0,sp) the return slot of the
# calls made here, (4,sp) id, (8,sp) key.
pk_core:
    mov d0,(4,sp)
    call 0x7e507f7d,[d2],4   # the firmware's byte-wise u32 read (little endian); a0 += 3
    mov d0,d2                # w0
    inc a0
    call 0x7e507f7d,[d2],4
    mov d0,d3                # w1
    inc a0
    call 0x7e507f7d,[d2],4
    mov d0,a2                # w2
    inc a0
    call 0x7e507f7d,[d2],4
    mov d0,a3                # w3
    mov d2,d0                # key = ((w0 * 3 + w1) * 3 + w2) * 3 + w3: odd factors, a change of one word changes it
    mov d0,d1
    add d0,d0
    add d1,d0
    add d3,d0
    mov d0,d1
    add d0,d0
    add d1,d0
    mov a2,d1
    add d1,d0
    mov d0,d1
    add d0,d0
    add d1,d0
    mov a3,d1
    add d1,d0
    mov (a1),d1
    cmp d0,d1
    beq 9f                   # the window is as last logged
    mov d0,(8,sp)
    mov (KT,a1),d1
    mov (TIMER),d0
    sub d0,d1
    and 0x3fffffff,d1        # microseconds since the last record pair (the timer counts down, 30 bits)
    cmp GAP,d1
    bcs 9f
    mov d0,(KT,a1)
    mov (8,sp),d0
    mov d0,(a1)
    mov (4,sp),d0
    mov d2,d1
    mov d3,a0
    call log_put,[],0        # bytes 0-7
    inc d0
    mov a2,d1
    mov a3,a0
    call log_put,[],0        # bytes 8-15
9:  ret [d2,d3,a2,a3],28
"""


def base_image(work):
    """Block 0 of the pinned build, written to WORK/block0_0100.bin."""
    specs = json.load(open(os.path.join(ROOT, "data", "builds", BUILD + ".json")))["specs"]
    blk = bytearray(parse(open(os.path.join(ROOT, L.STOCK), "rb").read()).blocks[0].payload)
    for s in specs:
        for o in load_spec(Path(ROOT, s)).ops:
            if isinstance(o, BytesOp) and o.block == 0:
                assert bytes(blk[o.offset:o.offset + len(o.expect)]) == o.expect, s
                blk[o.offset:o.offset + len(o.new)] = o.new
    path = os.path.join(work, "block0_0100.bin")
    open(path, "wb").write(blk)
    return bytes(blk), path


def main():
    """Assemble the routines and the hooks, check every site, write the spec."""
    work = sys.argv[1]
    listing = sys.argv[2] if len(sys.argv) > 2 else None
    os.makedirs(work, exist_ok=True)
    blk, blk_path = base_image(work)
    get = lambda a, n: blk[a - BASE:a - BASE + n]
    stock = parse(open(os.path.join(ROOT, L.STOCK), "rb").read()).blocks[0].payload
    d = json.load(open(os.path.join(ROOT, "data/logdict/events.json")))
    ids = {e["name"]: e["id"] for e in d["events"] if e["spec"] == SPEC}
    assert sorted(ids) == EVENTS, ids
    bid = L.build_id(d["events"])
    # log_chg of log-menu-3: the first of three entries `movm [d2,d3,a2,a3],(sp)` / `mov psw,d2` at the start of the
    # kernel run (log_chg, log_cnt, log_put); log_put is followed by the switch `movbu (LOGON),d3`
    lo = 0x7E4C9514
    head = bytes.fromhex("cff0f2e6")
    at = [lo + i for i in range(0x40) if get(lo + i, 4) == head]
    assert len(at) == 3 and at[0] == lo and get(at[2] + 4, 6) == bytes.fromhex("fcab42d04fbe"), at
    bad = L.branch_targets_inside([(s, n) for s, (n, _, _) in SITES.items()], blk, work)
    assert not bad, bad
    val = dict(ids)
    for site, (n, routine, _) in SITES.items():
        assert get(site, n) == stock[site - BASE:site - BASE + n], "site 0x%X is not in stock bytes" % site
        val["d_" + routine] = L.displaced(blk_path, site, n)
        val["b_" + routine] = "0x%08x" % (site + n)

    asm = L.SYMS + ASM % val
    args = ["--defsym=log_chg=%#x" % at[0], "--defsym=log_put=%#x" % at[2]]
    args += ["--defsym=s_%s=0x%s" % (a, a) for a in sorted(set(re.findall(r"(?:jmp|call)\s+0x([0-9a-f]{8})", asm)))]
    asm = re.sub(r"((?:jmp|call)\s+)0x([0-9a-f]{8})", r"\1s_\2", asm)
    for site, (n, routine, _) in SITES.items():
        asm += '\n.section .s%x,"ax"\n    jmp %s\n' % (site, routine) + "    nop\n" * (n - 5)
        args.append("--section-start=.s%x=%#x" % (site, site))
    args.append("--section-start=.pn=%#x" % AREA[0])
    s, o, e, sb = (os.path.join(work, "pana." + x) for x in ("s", "o", "elf", "bin"))
    open(s, "w").write(asm)
    L.run(L.BIN + "/mn10300-elf-as", "-o", o, s)
    L.run(L.BIN + "/mn10300-elf-ld", *args, "-e", "%#x" % AREA[0], "-o", e, o)

    def sect(name):
        L.run(L.BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", name, e, sb)
        return open(sb, "rb").read()

    def sym(name):
        m = re.search(r"^([0-9a-f]{8}) .*\s%s$" % name, L.run(L.BIN + "/mn10300-elf-objdump", "-t", e), re.M)
        return int(m.group(1), 16)

    ops = []

    def op(addr, new, note):
        expect = get(addr, len(new))
        assert expect != new, note
        ops.append({"type": "bytes", "block": 0, "offset": "0x%X" % (addr - BASE), "expect": expect.hex(),
                    "new": new.hex(), "_addr": "0x%08X" % addr, "_note": note})

    code = sect(".pn")
    a, hi = AREA
    assert a + len(code) <= hi, "%d B, %d free" % (len(code), hi - a)
    assert get(a, hi - a) == stock[a - BASE:hi - BASE], "the area is in use"
    if code[-1] == get(a + len(code) - 1, 1)[0]:
        code += b"\xcb"                      # the free-space ledger counts only changed bytes: end on a nop
    op(a, code, "new code, segment 1 (free part of lss-core's area): T_PS, T_PF, T_PKA, T_PKB, pk_core (%d B)" % len(code))
    print("routines: %d B at 0x%X-0x%X, %d B free after" % (len(code), a, a + len(code), hi - a - len(code)))
    for site, (n, routine, what) in SITES.items():
        h = sect(".s%x" % site)
        assert len(h) == n and h[0] == 0xDC
        ev = {"T_PS": "pana_stat", "T_PF": "pana_func", "T_PKA": "pana_pk84_0/1", "T_PKB": "pana_pk34_0/1"}[routine]
        op(site, h, "hook (%s): jmp %s%s. %s" % (ev, routine, " + nop" * (n - 5), what))
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
        "description": "Structured log, probe of what a Panasonic lens sends (GitHub issue #3, aperture ring): event "
                       "pana_stat at set_stat_pana 0x7E5234D7, a record when l_stat_pana or the lens's av_effect "
                       "changes (with l_func_flag_pana and the Panasonic flag byte 0x604F7F64); event pana_func at "
                       "set_func_flag_pana 0x7E523495, a record when l_func_flag_pana changes (with the lens id word "
                       "0x604F67B0). Both through log-menu-3's log_chg, gates at 0x7E4FD0A8 and 0x7E4FD0B0 in the "
                       "log's state block. Events pana_pk84_0/1 (status parser 0x7E523915, command 84: stat and the "
                       "14 bytes after it) and pana_pk34_0/1 (parser 0x7E52128F, command 34: the 3 skipped bytes, stat "
                       "and the 11 bytes after it): a record pair when the 16 bytes change, at most one pair per 0.5 s "
                       "per command, keys at 0x7E4FD0B8 and 0x7E4FD0BC, times at 0x7E4FD300 and 0x7E4FD304. Four hooks "
                       "in stock bytes of segment 1, their routines in segment 1. Needs "
                       "the specs of data/builds/peaking-mf.json before it: every expect is a byte string of that "
                       "build. It puts the build id %s of data/logdict/events.json into the block header. DEBUG "
                       "builds only. See experiments/2026-11-22-pana-aperture-ring/NOTES.md and "
                       "docs/reference/logging.md." % bid.hex(),
        "base": L.STOCK, "base_sha256": hashlib.sha256(open(os.path.join(ROOT, L.STOCK), "rb").read()).hexdigest(),
        "status": "candidate: emulator-checked, not flashed",
        "_delta_on": "data/builds/peaking-mf.json",
        "_build_id": bid.hex(),
        "_ram": "24 bytes at 0x7E4FD0A8 (uncached alias 0xBE4FD0A8, PST+104 to PST+127): two log gates and two window "
                "keys in the log's state block, cleared at every start by log-menu-3's T_BOOT; 8 bytes at 0x7E4FD300 "
                "(uncached 0xBE4FD300, after the log's block buffer, log-movie-time's RAM before): the timer value of "
                "the last record pair per command, not cleared at start",
        "_symbols": {k: "0x%08X" % sym(k) for k in ("T_PS", "T_PF", "T_PKA", "T_PKB", "pk_core")},
        "ops": ops,
    }, open(out, "w"), indent=1)
    open(out, "a").write("\n")
    print("wrote", os.path.relpath(out, ROOT), len(ops), "ops; build id", bid.hex())
    if listing:
        txt = L.run(L.BIN + "/mn10300-elf-objdump", "-d", "-j", ".pn", *sum((["-j", ".s%x" % x] for x in SITES), []), e)
        open(listing, "w").write(re.sub(r"/[^\s:]*pana\.elf", "pana.elf", txt))


if __name__ == "__main__":
    main()
