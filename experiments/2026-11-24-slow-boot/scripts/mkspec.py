"""Write data/specs/slow-boot-probe.json: a Debug Log record of the first live-view struct refresh of each start,
with two words that show whether segments 2 and 3 are in RAM at that moment (NOTES.md in this folder).

    uv run python experiments/2026-11-24-slow-boot/scripts/mkspec.py WORKDIR [LISTING.txt]
    WORKDIR  scratch folder for the assembler files (outside the repository)

Research code, after experiments/2026-11-22-pana-aperture-ring/scripts/mkspec.py. A delta on the pinned build
data/builds/peaking-mf.json: every `expect` is a byte string of that build.
Event lv_first (data/logdict/events.json). No new hook site: the peaking hook at 0x7E6ECF91 (peaking-direct-4,
`jmp T_A` + nop, the end of the live-view struct refresh 0x7E6ECCAF) jumps to T_LV, which logs once per start and
jumps on to T_A. T_LV is in segment 1 (the free part of lss-core's area): code that must run before segment 2 is
loaded cannot be in segments 2 or 3. Event start_kind: segment 3's last constructor entry points at T_PW (segment 2),
which logs the power-on factor, the wake reason and the quick start's state, then jumps to log-menu-3's T_CTOR. A flag byte in the free tail of the log's state block (cleared at every start
by log-menu-3's T_BOOT) makes it log once. It puts the build id of data/logdict/events.json into the flush task.
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

SPEC = "slow-boot-probe"
BUILD = "peaking-mf"                 # the pinned build this spec is a delta on
BASE = L.BASE
AREA = (0x7E69EC6B, 0x7E69EEAF)      # segment 1: auto-iso-min-shutter NOTES section 9, free after lss-core
AREA2 = (0x7EBF2E9F, 0x7EBF2F20)     # segment 2: the run of movie-ab's routine (history), between films12bw-doublex and peaking-mf's T_GS
FLUSH = (0x7EBF2BE4, 0x7EBF2DF8)     # log-menu-3's flush task (.uc): the two words of the build id
OLD_ID = "afe27672d672fc95"          # data/specs/log-menu-3.json
HOOK = 0x7E6ECF91                    # peaking-direct-4: `jmp T_A` + nop at the end of the struct refresh 0x7E6ECCAF
T_A = 0x7E4C920B
SEG2W, SEG2V = 0x7ECB0B84, 0xA0602BE8    # a word of peaking-mf's T_MF (segment 2, 1 KB before its end)
SEG3W, SEG3V = 0x7F033B74, 0x7EEBF5E1    # segment 3's constructor table, the entry before the last (stock)
CTOR, T_CTOR = 0x7F033B78, 0x7EBF2E68   # its last entry: log-menu-3's T_CTOR, now T_PW, which jumps on to T_CTOR
PWRF, WAKE, FAST = 0x604154E6, 0x604154E9, 0x604F2178   # power-on factor u16, wake reason u8, USR_FAST state u32

ASM = """
.equ FLAG,   PST+104         # u8: lv_first was written in this start (PST+104..127 are free, cleared at start)
.section .pn,"ax"
T_LV:                        # from the peaking hook 0x7E6ECF91, d0 = T_A's value for struct+36; every register and
    movm [d2,other],(sp)     # the flags are kept
    mov psw,d2
    movbu (FLAG),d0
    cmp 0,d0
    bne 9f
    mov 1,d0
    movbu d0,(FLAG)
    mov (%(seg2)#x),d1        # uncached: what is in RAM, not in the data cache
    mov (%(seg3)#x),a0
    mov %(lv_first)d,d0
    call log_put,[],0
9:  mov d2,psw
    nop
    nop
    movm (sp),[d2,other]
    jmp T_A

.section .pw,"ax"
T_PW:                        # segment 3's last constructor entry (task Usr1, after the copies of segments 2 and 3);
    movm [other],(sp)        # the power-on factor and the wake reason are set by then (0x7E45D1F3, from Usr0)
    movbu (%(wake)#x),d1
    asl 16,d1
    movhu (%(pwrf)#x),d0
    or d0,d1                 # arg0: factor | wake << 16
    mov (%(fast)#x),a0        # arg1: the quick start's state
    mov %(start_kind)d,d0
    call log_put,[],0
    movm (sp),[other]
    jmp T_CTOR
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
    """Assemble T_LV and the new hook target, check the sites, write the spec."""
    work = sys.argv[1]
    listing = sys.argv[2] if len(sys.argv) > 2 else None
    os.makedirs(work, exist_ok=True)
    blk, _ = base_image(work)
    get = lambda a, n: blk[a - BASE:a - BASE + n]
    stock = parse(open(os.path.join(ROOT, L.STOCK), "rb").read()).blocks[0].payload
    d = json.load(open(os.path.join(ROOT, "data/logdict/events.json")))
    ids = {e["name"]: e["id"] for e in d["events"] if e["spec"] == SPEC}
    assert sorted(ids) == ["lv_first", "start_kind"], ids
    bid = L.build_id(d["events"])
    lo = 0x7E4C9514                          # log_put of log-menu-3: the third `movm` / `mov psw,d2` entry
    head = bytes.fromhex("cff0f2e6")
    at = [lo + i for i in range(0x40) if get(lo + i, 4) == head]
    assert len(at) == 3 and get(at[2] + 4, 6) == bytes.fromhex("fcab42d04fbe"), at
    assert int.from_bytes(get(SEG2W, 4), "little") == SEG2V and int.from_bytes(get(SEG3W, 4), "little") == SEG3V
    old_hook = get(HOOK, 6)
    assert old_hook[0] == 0xDC and (HOOK + int.from_bytes(old_hook[1:5], "little", signed=True)) & 0xFFFFFFFF == T_A
    asm = L.SYMS + ASM % dict(ids, seg2=SEG2W + 0x40000000, seg3=SEG3W + 0x40000000, wake=WAKE, pwrf=PWRF, fast=FAST)
    asm += '\n.section .hk,"ax"\n    jmp T_LV\n    nop\n'
    args = ["--defsym=log_put=%#x" % at[2], "--defsym=T_A=%#x" % T_A, "--defsym=T_CTOR=%#x" % T_CTOR, "--section-start=.pn=%#x" % AREA[0], "--section-start=.pw=%#x" % AREA2[0], "--section-start=.hk=%#x" % HOOK]
    s, o, e, sb = (os.path.join(work, "probe." + x) for x in ("s", "o", "elf", "bin"))
    open(s, "w").write(asm)
    L.run(L.BIN + "/mn10300-elf-as", "-o", o, s)
    L.run(L.BIN + "/mn10300-elf-ld", *args, "-e", "%#x" % AREA[0], "-o", e, o)

    def sect(name):
        L.run(L.BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", name, e, sb)
        return open(sb, "rb").read()

    ops = []

    def sym_addr(name):
        m = re.search(r"^([0-9a-f]{8}) .*\s%s$" % name, L.run(L.BIN + "/mn10300-elf-objdump", "-t", e), re.M)
        return int(m.group(1), 16)

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
    op(a, code, "new code, segment 1 (free part of lss-core's area): T_LV (%d B)" % len(code))
    code2 = sect(".pw")
    a2, hi2 = AREA2
    assert a2 + len(code2) <= hi2 and get(a2, hi2 - a2) == stock[a2 - BASE:hi2 - BASE], "AREA2"
    if code2[-1] == get(a2 + len(code2) - 1, 1)[0]:
        code2 += b"\xcb"
    op(a2, code2, "new code, segment 2 (movie-ab's run, history): T_PW (%d B)" % len(code2))
    h = sect(".hk")
    assert len(h) == 6 and h[0] == 0xDC
    op(HOOK, h[:5], "peaking hook at the end of the live-view struct refresh: `jmp T_A` -> `jmp T_LV` (T_LV logs "
       "lv_first once per start, then jumps to T_A)")
    assert int.from_bytes(get(CTOR, 4), "little") == T_CTOR
    tpw = sym_addr("T_PW")
    op(CTOR, tpw.to_bytes(4, "little"), "segment 3's last constructor entry: log-menu-3's T_CTOR -> T_PW (logs "
       "start_kind, then jumps to T_CTOR)")
    old = bytes.fromhex(OLD_ID)
    for half in (0, 4):                      # the two `mov imm32,d0` of the flush task that hold the build id
        word = b"\xfc\xcc" + old[half:half + 4]
        i = blk.find(word)
        assert i >= 0 and blk.find(word, i + 1) < 0 and FLUSH[0] <= BASE + i < FLUSH[1], half
        op(BASE + i + 2, bid[half:half + 4], "flush task, block header: build id bytes %d-%d %s -> %s "
           "(data/logdict/events.json)" % (half, half + 3, old[half:half + 4].hex(), bid[half:half + 4].hex()))
    out = os.path.join(ROOT, "data", "specs", SPEC + ".json")
    json.dump({
        "name": SPEC,
        "description": "Structured log, probe of the slow cold start (GitHub issue #6, "
                       "experiments/2026-11-24-slow-boot/NOTES.md): event lv_first, once per start, at the first run "
                       "of the live-view struct refresh 0x7E6ECCAF, before peaking's latch T_A (whose T_R jumps to "
                       "peaking-mf's T_MF in segment 2). arg0 = the word 0x7ECB0B84 of T_MF, arg1 = the word 0x7F033B74 of "
                       "segment 3's constructor table, both read through the uncached alias: they tell whether the "
                       "copies of segments 2 and 3 have reached them. The peaking hook 0x7E6ECF91 jumps to T_LV "
                       "(segment 1, free part of lss-core's area), which jumps on to T_A; a flag at PST+104 "
                       "(0x7E4FD0A8, cleared at every start by log-menu-3's T_BOOT). Event start_kind: segment 3's last "
                       "constructor entry points at T_PW (segment 2), which logs the power-on factor, the wake reason "
                       "and the quick start's state after the segment copies, then jumps to log-menu-3's T_CTOR "
                       "(seg_loaded follows). Needs the specs of "
                       "data/builds/peaking-mf.json before it. It puts the build id %s of data/logdict/events.json "
                       "into the block header. DEBUG builds only." % bid.hex(),
        "base": L.STOCK, "base_sha256": hashlib.sha256(open(os.path.join(ROOT, L.STOCK), "rb").read()).hexdigest(),
        "status": "candidate: emulator-checked, not flashed",
        "_delta_on": "data/builds/peaking-mf.json",
        "_build_id": bid.hex(),
        "_ram": "1 byte at 0x7E4FD0A8 (uncached alias 0xBE4FD0A8, PST+104) in the log's state block, cleared at every "
                "start by log-menu-3's T_BOOT",
        "ops": ops,
    }, open(out, "w"), indent=1)
    open(out, "a").write("\n")
    print("wrote", os.path.relpath(out, ROOT), len(ops), "ops; T_LV %d B, T_PW %d B; build id %s" % (len(code), len(code2), bid.hex()))
    if listing:
        txt = L.run(L.BIN + "/mn10300-elf-objdump", "-d", "-j", ".pn", "-j", ".pw", "-j", ".hk", e)
        open(listing, "w").write(re.sub(r"/[^\s:]*probe\.elf", "probe.elf", txt))


if __name__ == "__main__":
    main()
