"""Write patches/log-menu.json and builds/log-menu.json: the structured log in the release firmware, switched by the
Custom Menu row Debug Log (setting 447; patches/custom-menu-rows-2.json). design.md in this folder.

    uv run python experiments/2026-11-18-log-menu/scripts/mkspec_logmenu.py WORKDIR [LISTING.txt]
    WORKDIR: a scratch folder outside the repository

The code is the camera-tested log of experiments/2026-11-15-log/scripts/mkspec_log.py (log-core, log-probes,
log-peaking-time, log-peaking-guard), assembled again in one spec on the pinned build, with these changes:
  * the switch: a byte LOGON in the log's state block, 0 = not read yet (start-up), 1 = On, 2 = Off. log_put,
    log_chg and log_cnt return at once when it is 2: after the first GUI state of a session with the row Off, no
    record is written and the flush never runs. Before that (the start-up) records go to the ring in RAM.
  * T_GUI reads the row at the first GUI state of a session and at every GUI state call in the menu (0x57xx); a
    change to On writes log_setting. It points the texts 1502 and 1499 (the row's label and help) at "Debug Log"
    and its help in the loaded language's table. It skips the flush while card-looks' task runs. It ends with a
    jump to card-looks' T_GUI, which runs the replaced trace call and jumps back: card-looks-4's code is unchanged,
    the hook at 0x7ECDF6E4 jumps here.
  * the flush task is USRTEST_B (id 0x91): card-looks keeps USRTEST_A.
  * a probe at card-looks' T_END: card_task.
  * placement: the kernel routines of log-core, log-probes and log-peaking-time in one run 0x7E4C9514-0x7E4C9800;
    T_GUI, T_GRD, T_CTASK and the texts in 0x7EBF2600-0x7EBF2890 (custom-menu-rows' child list was there).
Every expect is a byte string of builds/log-menu.json's specs before this one.
"""

import hashlib
import json
import os
import re
import struct
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "experiments", "2026-11-15-log", "scripts"))
sys.path.insert(0, os.path.join(ROOT, "src"))
import mkspec_log as L  # noqa: E402
from epm2mod.container import parse  # noqa: E402
from epm2mod.spec import BytesOp, load_spec  # noqa: E402

SPEC = "log-menu"
BUILD = "log-menu"
BASE = L.BASE
STOCK = L.STOCK
BIN = L.BIN
AREAS = {
    ".k": (0x7E4C9514, 0x7E4C9800, "kernel range: log_put, log_chg, log_cnt, T_ERR, T_BOOT, the routines of the "
           "hooks in segment 1 and the kernel, and the timing probe of peaking (T_TIME0, T_TIME0B, T_TICK)"),
    ".uc": (0x7EBF2BE4, 0x7EBF2E80, "segment 2: the flush task and the file name"),
    ".up": (0x7EBF3780, 0x7EBF38BC, "segment 2: routines of the hooks in segments 2 and 3"),
    ".ug": (0x7EBF2600, 0x7EBF2890, "segment 2: T_GUI, T_GRD, T_CTASK, the row's texts"),
}
TASK_ENTRY, TASK_ENTRY_OLD = 0x7E439C9C, 0x7E501CE7      # CPU0 task table, row of id 0x91 (USRTEST_B): the entry word
TASK_ID = 0x91
CL_SYMS = "build/card-looks/syms-4.json"                  # card-looks-4's labels (mkspec_looks3.py --v4)
CL_RSTAT = 0x7E4D0000 + 0x40000000                        # card-looks' status word (uncached)
LANG, LANG_SPAN = 0xBFF3D000, 0x43000
LABEL, HELP = 1502, 1499
TXT_LABEL = "Debug Log"
TXT_HELP = "On: write EPM2LOG.BIN to the\r\ncard, for bug reports."
CTASK_SITE = 7                                            # bytes at card-looks' T_END: `clr d0` / `movbu d0,(BUSY)`

SYMS_EXTRA = """
.equ LOGON,  PST+2           # u8: 0 not read yet (start-up), 1 the row is On, 2 Off
.equ CL_FLAGS, %(cl_flags)#x # card-looks' flags (uncached): busy, applied, store ok, mode
.equ CL_RSTAT, %(cl_rstat)#x # card-looks' status: the text the Load Looks row shows
.equ LANG,   %(lang)#x       # word: the pointer array of the loaded language
"""

GATE = """lp_body:
    movbu (LOGON),d3             # the row is Off: no record
    cmp 2,d3
    beq lp_done
"""

T_GUI = """
.section .ug,"ax"
T_GUI:                           # the "state =" trace of the GUI state setter 0x7ECDF5E9, d0 = new state (task
    movm [d2,d3,other],(sp)      # CA_MAIN). It ends with a jump to card-looks' T_GUI
    mov psw,d2                   # this routine changes the flags: keep them
    mov d0,d3                    # d3: the new state
    movbu (LOGON),d0
    cmp 0,d0
    beq 1f                       # the first GUI state of the session: read the row
    mov d3,d0
    lsr 8,d0
    cmp 0x57,d0                  # in the menu the row can change: read it at every call
    bne 3f
1:  mov 0xd791,d0                # setting 447, the row Debug Log: 0 Off, 1 On
    mov 0,a0
    clr d1
    call 0x7e457c75,[d2,d3],12   # prm_get(tag, 0, 0)
    mov 2,d1
    cmp 1,d0
    bne 2f
    mov 1,d1
2:  movbu (LOGON),d0
    cmp d0,d1
    beq 3f
    movbu d1,(LOGON)
    cmp 1,d1
    bne 3f
    mov d3,a0
    mov %(log_setting)d,d0       # d1 = 1
    call log_put,[],0
3:  mov (LANG),a0                # the row's texts in the loaded language's table
    mov a0,d0
    add %(lang_neg)#x,d0
    cmp %(lang_span)#x,d0
    bcc 4f                       # no language table yet
    mov (%(label_off)d,a0),d0
    cmp S_LABEL,d0
    beq 4f
    mov S_LABEL,d0
    mov d0,(%(label_off)d,a0)
    mov S_HELP,d0
    mov d0,(%(help_off)d,a0)
4:  movbu (LOGON),d0
    cmp 1,d0
    bne 9f                       # Off: nothing more
    mov d3,d1
    mov (SHGUI),d0
    cmp d0,d1
    beq 9f
    mov d1,(SHGUI)
    mov d0,a0
    mov %(gui_state)d,d0
    call log_put,[],0
    mov d1,d0
    lsr 8,d0
    cmp 0x57,d0                  # 0x57xx: the menus
    beq 5f
    lsr 4,d0
    cmp 2,d0                     # 0x2xxx: power off, sleep
    beq 5f
    cmp 3,d0                     # 0x3xxx: playback
    bne 9f
5:  movbu (BUSY),d0
    cmp 0,d0
    bne 9f
    movbu (CL_FLAGS),d0          # card-looks' task runs: no flush now
    cmp 0,d0
    bne 9f
    mov d1,(TRIG)
    call 0x7ecd360a,[d2],8       # the GUI's isMediaWriting(): 1 while the card is written
    cmp 0,d0
    bne 9f
    mov 1,d0
    movbu d0,(BUSY)
    mov %(task)#x,d0
    call 0x7e449541,[d2,d3],12   # OlyTaSt(USRTEST_B)
9:  mov d2,psw
    nop
    nop
    movm (sp),[d2,d3,other]
    jmp %(cl_gui)#x              # card-looks' T_GUI: the replaced trace call, then back

T_CTASK:                         # card-looks' T_END: its task ends (USRTEST_A)
    movm [other],(sp)
    mov (CL_FLAGS),d1
    mov (CL_RSTAT),a0
    mov %(card_task)d,d0
    call log_put,[],0
    movm (sp),[other]
%(displaced_CTASK)s
    jmp %(back_CTASK)s

    .balign 2
S_LABEL: .short %(s_label)s
S_HELP:  .short %(s_help)s
"""


def u16(text):
    return ", ".join("0x%04x" % c for c in text.encode("utf-16-le")[::2]) + ", 0"


def base_image(work):
    """Block 0 of builds/log-menu.json without this spec, written to WORK/block0_0100.bin."""
    specs = json.load(open(os.path.join(ROOT, "builds", "card-looks-4.json")))["specs"]
    specs = [s.replace("custom-menu-rows.json", "custom-menu-rows-2.json") for s in specs]
    blk = bytearray(parse(open(os.path.join(ROOT, STOCK), "rb").read()).blocks[0].payload)
    for s in specs:
        for o in load_spec(Path(ROOT, s)).ops:
            if isinstance(o, BytesOp) and o.block == 0:
                assert bytes(blk[o.offset:o.offset + len(o.expect)]) == o.expect, s
                blk[o.offset:o.offset + len(o.new)] = o.new
    path = os.path.join(work, "block0_0100.bin")
    open(path, "wb").write(blk)
    return specs, bytes(blk), path


def main():
    work = sys.argv[1]
    listing = sys.argv[2] if len(sys.argv) > 2 else None
    os.makedirs(work, exist_ok=True)
    specs, blk, blk_path = base_image(work)
    stock = parse(open(os.path.join(ROOT, STOCK), "rb").read()).blocks[0].payload
    get = lambda a, n: blk[a - BASE:a - BASE + n]
    d = json.load(open(os.path.join(ROOT, "logs/events.json")))
    ev = {e["name"]: e["id"] for e in d["events"]}
    bid = L.build_id(d["events"])
    cl = json.load(open(os.path.join(ROOT, CL_SYMS)))
    assert get(cl["T_END"], CTASK_SITE) == bytes.fromhex("00fc82") + struct.pack("<I", cl["FLAGS"] + 0x40000000)
    gui_site = L.HOOKS["GUI"][1]
    assert get(gui_site, 1) == b"\xdc" and gui_site + 5 + struct.unpack("<i", get(gui_site + 1, 4))[0] - 5 == \
        cl["T_GUI"], "the hook does not jump to card-looks' T_GUI"

    # name: (site, bytes, events, what); the stock-site hooks of mkspec_log, the timing and guard sites, T_END
    hooks = {n: (site, k, e, w) for n, (_, site, k, e, w) in L.HOOKS.items()}
    (ta, (na, _, wa)), (tb, (nb, _, wb)) = L.TIME_SITES.items()
    hooks["TIME0"] = (ta, na, "pk_stats", wa)
    hooks["TICK"] = (tb, nb, "pk_stats", wb)
    hooks["GRD"] = (L.GUARD_SITE[0], L.GUARD_SITE[1], "pk_guard", L.GUARD_SITE[2])
    hooks["CTASK"] = (cl["T_END"], CTASK_SITE, "card_task", "card-looks' T_END: `clr d0` / `movbu d0,(BUSY)` "
                      "(segment 3, task USRTEST_A)")
    label = {"ERR": "T_ERR", "BOOT": "T_BOOT", "GUI": "T_GUI", "TIME0": "T_TIME0", "TICK": "T_TICK", "GRD": "T_GRD"}
    for name, (site, n, _, _) in hooks.items():
        if name not in ("GUI", "CTASK"):
            assert get(site, n) == stock[site - BASE:site - BASE + n], "%s: not stock bytes" % name
    val = dict(ev, mask=L.RING_RECORDS - 1, n=L.RING_RECORDS, per=L.BLOCK_RECORDS,
               bid0=struct.unpack("<i", bid[:4])[0], bid1=struct.unpack("<i", bid[4:])[0],
               every=L.TIME_EVERY - 1, lang_neg=(-LANG) & 0xFFFFFFFF, lang_span=LANG_SPAN, label_off=4 * LABEL,
               help_off=4 * HELP, task=TASK_ID, cl_gui=cl["T_GUI"], cl_flags=cl["FLAGS"] + 0x40000000,
               cl_rstat=CL_RSTAT, lang=LANG, s_label=u16(TXT_LABEL), s_help=u16(TXT_HELP))
    val["n_time"] = L.TIME_EVERY
    for name, (site, n, _, _) in hooks.items():
        if name != "GUI":
            val["displaced_" + name] = L.displaced(blk_path, site, n)
            val["back_" + name] = "0x%08x" % (site + n)
    val["displaced_a"], val["back_a"] = val["displaced_TIME0"], val["back_TIME0"]
    val["displaced_b"], val["back_b"] = val["displaced_TICK"], val["back_TICK"]
    val["displaced"], val["back"] = val["displaced_GRD"], val["back_GRD"]

    core_k = L.CORE_K.replace(".section .kc,", ".section .k,")
    assert core_k.count("lp_body:\n") == 1
    core_k = core_k.replace("lp_body:\n", GATE)
    probes_k = L.PROBES_K.replace(".section .kp,", ".section .k,")
    core_u = L.CORE_U[:L.CORE_U.index("T_GUI:")]
    core_u = core_u.replace("task USRTEST_A (id 0x90", "task USRTEST_B (id 0x91")
    time_asm = re.sub(r'\.section \.t[01k],"ax"', '.section .k,"ax"', L.TIME_ASM)
    time_asm = time_asm.replace("%(n)d passes", "%(n_time)d passes")
    guard = L.GUARD_ASM.replace(".section .gu,", ".section .ug,")
    asm = L.SYMS + SYMS_EXTRA % val + (core_k + probes_k + core_u + L.PROBES_U + time_asm + guard + T_GUI) % val
    calls = sorted(set(re.findall(r"(?:jmp|call)\s+0x([0-9a-f]{8})", asm)))
    args = ["--defsym=s_%s=0x%s" % (a, a) for a in calls]
    asm = re.sub(r"((?:jmp|call)\s+)0x([0-9a-f]{8})", r"\1s_\2", asm)
    for name, (site, n, _, _) in hooks.items():
        asm += '\n.section .h%s,"ax"\n    jmp %s\n' % (name, label.get(name, "T_" + name)) + "    nop\n" * (n - 5)
        args.append("--section-start=.h%s=%#x" % (name, site))
    args += ["--section-start=%s=%#x" % (name, lo) for name, (lo, _, _) in AREAS.items()]
    s, o, e = (os.path.join(work, "logmenu." + x) for x in ("s", "o", "elf"))
    open(s, "w").write(asm)
    L.run(BIN + "/mn10300-elf-as", "-o", o, s)
    L.run(BIN + "/mn10300-elf-ld", *args, "-e", "%#x" % AREAS[".k"][0], "-o", e, o)
    sym = {l.split()[2]: int(l.split()[0], 16) for l in L.run(BIN + "/mn10300-elf-nm", e).splitlines()
           if len(l.split()) == 3}

    def sect(name):
        b = os.path.join(work, "sect.bin")
        L.run(BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", name, e, b)
        return open(b, "rb").read()

    ops, report = [], []

    def op(addr, new, note):
        expect = get(addr, len(new))
        assert expect != new, note
        ops.append({"type": "bytes", "block": 0, "offset": "0x%X" % (addr - BASE), "expect": expect.hex(),
                    "new": new.hex(), "_addr": "0x%08X" % addr, "_note": note})

    stock_hooks = [(site, n) for name, (site, n, _, _) in hooks.items() if name not in ("GUI", "CTASK")]
    bad = L.branch_targets_inside(stock_hooks, blk, work)
    assert not bad, bad
    for name, (lo, hi, what) in AREAS.items():
        b = sect(name)
        assert lo + len(b) <= hi, "%s: %d bytes, %d free" % (name, len(b), hi - lo)
        assert get(lo, len(b)) == stock[lo - BASE:lo - BASE + len(b)], "%s: the area is in use" % name
        if b[-1] == get(lo + len(b) - 1, 1)[0]:
            b += b"\xcb"                     # the free-space ledger counts only changed bytes: end on a nop
        op(lo, b, "new code, %s (%d B)" % (what, len(b)))
        report.append("%s: %d B at 0x%X-0x%X, %d B free after" % (name, len(b), lo, lo + len(b), hi - lo - len(b)))
    for name, (site, n, events, what) in hooks.items():
        h = sect(".h" + name)
        assert len(h) == n and h[0] == 0xDC, (name, h.hex())
        op(site, h, "hook %s (%s): jmp %s%s. %s" % (name, events, label.get(name, "T_" + name), " + nop" * (n - 5),
                                                    what))
    assert struct.unpack_from("<I", blk, TASK_ENTRY - BASE)[0] == TASK_ENTRY_OLD
    op(TASK_ENTRY, struct.pack("<I", sym["FLUSH"]), "CPU0 task table, row of id 0x91 (USRTEST_B, dormant in stock): "
       "entry 0x%08X -> FLUSH 0x%08X" % (TASK_ENTRY_OLD, sym["FLUSH"]))
    stock_sha = hashlib.sha256(open(os.path.join(ROOT, STOCK), "rb").read()).hexdigest()
    json.dump({
        "name": SPEC,
        "description": (
            "The structured log in the release firmware, switched by the Custom Menu row Debug Log (setting 447, "
            "patches/custom-menu-rows-2.json; default Off). log_put / log_chg / log_cnt write 16-byte records into "
            "one RAM ring per CPU (0x7E4F9000-0x7E4FD2C0) and return at once when the row is Off: from the first GUI "
            "state of a session the log does nothing more with Off, and only the start-up records are in RAM. With "
            "On, the flush task (the dormant task USRTEST_B) appends the records to C:\\\\EPM2LOG.BIN when the GUI "
            "enters a menu, playback or power-off state and neither the card nor card-looks' task is busy (stops at "
            "4 MiB). Events: boot, firmware errors, GUI states, log_setting, the probes of log-probes (peaking, "
            "picture mode, level gauge, interval shooting, film looks, shooting callbacks), pk_stats, pk_guard and "
            "card_task (each run of card-looks' task). The code of log-core, log-probes, log-peaking-time and "
            "log-peaking-guard, placed again; the hook of the GUI state setter jumps to this T_GUI, which ends with "
            "a jump to card-looks' T_GUI. The event ids are in logs/events.json (build id %s). See "
            "experiments/2026-11-18-log-menu/design.md and docs/logging.md." % bid.hex()),
        "base": STOCK, "base_sha256": stock_sha,
        "status": "candidate: emulator-checked, not flashed",
        "_build_id": bid.hex(),
        "_ram": "the log's rings and state 0x7E4F9000-0x7E4FD2C0 (uncached alias); LOGON is PST+2",
        "ops": ops,
    }, open(os.path.join(ROOT, "patches", SPEC + ".json"), "w"), indent=1)
    open(os.path.join(ROOT, "patches", SPEC + ".json"), "a").write("\n")
    pinned = json.load(open(os.path.join(ROOT, "builds", "card-looks-4.json")))
    build = {
        "what": pinned["what"] + "; a Debug Log row in Custom Menu J (Off by default) that writes EPM2LOG.BIN to "
                "the card for bug reports",
        "specs": specs + ["patches/%s.json" % SPEC],
    }
    json.dump(build, open(os.path.join(ROOT, "builds", BUILD + ".json"), "w"), indent=1)
    open(os.path.join(ROOT, "builds", BUILD + ".json"), "a").write("\n")
    print("wrote patches/%s.json (%d ops) and builds/%s.json; build id %s" % (SPEC, len(ops), BUILD, bid.hex()))
    print("\n".join(report))
    if listing:
        secs = sum((["-j", n] for n in list(AREAS) + [".h" + n for n in hooks]), [])
        txt = L.run(BIN + "/mn10300-elf-objdump", "-d", *secs, e)
        open(listing, "w").write(re.sub(r"/[^\s:]*logmenu\.elf", "logmenu.elf", txt))


if __name__ == "__main__":
    main()
