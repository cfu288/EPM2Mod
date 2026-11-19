"""Write data/specs/movie-ab.json: the 1920-wide 1080 frame for Full HD Fine only, the stock frame otherwise.

    uv run python experiments/2026-11-19-movie-sampling/scripts/mkspec_ab.py BASE_DIR WORKDIR [LISTING.txt]
    BASE_DIR  `uv run python tools/oetool.py unpack build/debug-log-movie-bitrate.BIN BASE_DIR`
    WORKDIR   scratch folder for the assembler files (outside the repository)

Research code (NOTES.md section 16). A delta on data/builds/debug-log-movie-bitrate.json: every hook site is in stock
bytes. It replaces the fixed values of movie-wide-frame.json and movie-wide-writer.json by a choice at run time:

  W = 1 when the movie record mode is Full HD Fine (setting 34145 = 6, MOV 1920x1080, and setting 33105 index 7 = 1,
  Fine), else 0. SETW reads both settings with the firmware's getter 0x7E457C75, stores W (one byte of the probe RAM,
  uncached) and logs mv_set. It runs where the frame is set up: the TAKE request builder's HSHR case (T_TAKE), the
  writer request for mode code 517 (T_REQ) and the movie mode table of Through Start (T_TAB). The readers that run
  later (Movie IS crop and shift, the two IMG divisors, art_get_bayer_size) read W.

  With W = 0 every value is the stock one. With W = 1 the values are those of the two wide specs.
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

SPEC = "movie-ab"
BASE = L.BASE
OLD_ID = "34775ddcf8f5f0af"          # data/specs/log-movie-time.json
FLUSH = (0x7EBF2BE4, 0x7EBF2E80)
AREAS = {   # section: (start, end, what)
    ".a1": (0x7E69EE0B, 0x7E69EEAF, "segment 1, the free end of lss-core's area after log-movie-time"),
    ".a2": (0x7E880F5C, 0x7E880FE4, "segment 1, the free run before peaking-direct-3's bytes"),
    ".a3": (0x7EBF2E9F, 0x7EBF2F40, "segment 2, a free run of the listed area (readers that run only in movie frames with Movie IS and in art jobs)"),
}
SITES = {   # site: (bytes, routine, section of the routine, what)
    0x7E59EE7E: (6, "T_TAKE", ".a1", "TAKE request builder 0x7E59EE0A, HSHR case: `mov 1662,d0` / `movhu d0,(6,a0)`; the routine sets +6, +8, +10"),
    0x7E5A8A90: (5, "T_REQ", ".a2", "writer request builder 0x7E5A897F, after the resize block: `mov 1,d0` / `movhu d0,(38,a3)`"),
    0x7E6C438B: (9, "T_TAB", ".a2", "movie mode table 0x7E6C410A, after the HSHR record: `mov 992,d1` / `movhu d1,(0x605B08A0)`"),
    0x7E6CB8B3: (6, "T_ISC", ".a3", "Movie IS crop 0x7E6CB860, HSHR: `mov 1414,d0` / `movhu d0,(116,a2)`"),
    0x7E6CB981: (6, "T_ISD", ".a1", "Movie IS shift 0x7E6CB90B, HSHR: `mov 91750,d2`"),
    0x7E54A2CE: (5, "T_IMG1", ".a3", "IMG resize builder 0x7E54A0D0, IMG mode 5 (Dramatic Tone branch): `mov 1646,d0` / `divu d0,d1`"),
    0x7E54A5E9: (5, "T_IMG2", ".a3", "IMG resize builder 0x7E54A468, IMG mode 5: `mov 1646,d0` / `divu d0,d2`"),
    0x7E7290F4: (8, "T_ABS", ".a3", "art_get_bayer_size 0x7E7290B5, its end: `mov d2,a0` / `add 0x7E85B38C,a0`"),
}

ASM = """
.equ W,        0xbe4fd31c    # u8: 1 = the wide frame (Full HD Fine), 0 = stock; byte 28 of log-movie-time's 32 bytes

.section .a1,"ax"
SETW:                        # call SETW,[],0. Sets W, logs mv_set with the return address (the site).
                             # Changes d0, d1, a0, a1, d2, d3, mdr and the flags (the callers save what they need)
    mov mdr,d0               # `call` left the return address in mdr
    mov d0,d3
    add -8,sp                # the getter's return address goes to (sp): keep ours above it
    clr d2
    mov 34145,d0             # record mode: 6 = 1920x1080 MOV
    clr d1
    mov 0,a0
    call 0x7e457c75,[d2,d3],12   # the settings getter (d0 = id, d1 = index)
    exthu d0
    cmp 6,d0
    bne 1f
    mov 33105,d0             # index 7: 1 = Fine
    mov 7,d1
    mov 0,a0
    call 0x7e457c75,[d2,d3],12   # the settings getter (d0 = id, d1 = index)
    exthu d0
    cmp 1,d0
    bne 1f
    mov 1,d2
1:  movbu d2,(W)
    mov d2,d1
    mov d3,a0
    mov %(mv_set)d,d0
    call log_put,[],0
    add 8,sp
    ret [],0

T_TAKE:                      # a0 = d3 = the request; d0 is set again after the replaced bytes; the flags are not used
    movm [d2,d3,other],(sp)
    call SETW,[],0
    movm (sp),[d2,d3,other]
    movbu (W),d0
    cmp 0,d0                 # Z = stock; the movs and stores below keep the flags
    mov 1662,d0
    beq 1f
    mov 1938,d0
1:  movhu d0,(6,a0)
    mov 1312,d0
    movhu d0,(8,a0)
    mov 1646,d0
    beq 2f
    mov 1920,d0
2:  movhu d0,(10,a0)
    jmp 0x7e59ee90

T_ISD:                       # d2 = the divisor; the flags are set again before they are used
    movbu (W),d2
    cmp 0,d2
    mov 91750,d2
    beq 1f
    mov 78643,d2
1:  jmp 0x7e6cb987

.section .a2,"ax"
T_REQ:                       # a3 = the request; (16,sp) = the mode code; d0 is loaded again after the site
%(d_T_REQ)s
    mov (16,sp),d0
    cmp 517,d0
    bne 9f
    movm [d2,d3,other],(sp)
    call SETW,[],0
    movm (sp),[d2,d3,other]
    movbu (W),d0
    cmp 0,d0
    beq 9f
    mov 1960,d0              # the written line
    movhu d0,(4,a3)
    mov 1433,d0              # the phases
    movhu d0,(48,a3)
    movhu d0,(52,a3)
    mov 4915,d0              # the step, 1.2 in Q12
    movhu d0,(54,a3)
9:  jmp 0x7e5a8a95

T_TAB:                       # the movie mode table, after the stock HSHR record (0x605B0882) is complete
    movm [d2,d3,other],(sp)
    call SETW,[],0
    movbu (W),d0
    cmp 0,d0
    beq 9f
    mov 0x605b0882,a0
    mov 1960,d0
    movhu d0,(a0)            # stride
    mov 1938,d0
    movhu d0,(2,a0)          # width
    mov 1920,d0
    movhu d0,(6,a0)          # effective width
    movhu (10,a0),d0
    add 138,d0               # centre x: 831 + x/2 -> 969 + x/2
    movhu d0,(10,a0)
    mov 1650,d0
    movhu d0,(18,a0)         # Movie IS crop width
9:  movm (sp),[d2,d3,other]
%(d_T_TAB)s
    jmp 0x7e6c4394

.section .a3,"ax"
T_ISC:                       # d1 is kept; d0 ends as the stored crop width, as in stock
    movm [other],(sp)
    movbu (W),d1
    cmp 0,d1
    mov 1414,d0
    beq 1f
    mov 1650,d0
1:  movhu d0,(116,a2)
    movm (sp),[other]
    movhu (116,a2),d0        # d0 as the replaced `mov` leaves it
    jmp 0x7e6cb8b9

T_IMG1:
    movbu (W),d0
    cmp 0,d0
    mov 1646,d0
    beq 1f
    mov 1920,d0
1:  divu d0,d1
    jmp 0x7e54a2d3

T_IMG2:
    movbu (W),d0
    cmp 0,d0
    mov 1646,d0
    beq 1f
    mov 1920,d0
1:  divu d0,d2
    jmp 0x7e54a5ee

T_ABS:                       # d2 = 16 x index; the function restores d2 with its `ret [d2],8`
    mov d2,a0
    add 0x7e85b38c,a0
    cmp 80,d2
    bne 1f
    movbu (W),d2
    cmp 0,d2
    beq 1f
    mov WIDEBAYER,a0
1:  jmp 0x7e7290fc
    .balign 4
WIDEBAYER:                   # art_get_bayer_size entry 5 of movie-wide-frame.json
    .hword 1960, 1938, 1312, 0, 1920, 1296, 969, 656
"""


def main():
    """Assemble, check every site and area, write the spec."""
    base, work = sys.argv[1:3]
    listing = sys.argv[3] if len(sys.argv) > 3 else None
    os.makedirs(work, exist_ok=True)
    blk_path = os.path.join(base, "block0_0100.bin")
    blk = open(blk_path, "rb").read()
    get = lambda a, n: blk[a - BASE:a - BASE + n]
    stock = open(os.path.join(ROOT, "build/blocks", os.path.basename(L.STOCK) + ".block0.bin"), "rb").read()
    d = json.load(open(os.path.join(ROOT, "data/logdict/events.json")))
    ids = {e["name"]: e["id"] for e in d["events"] if e["spec"] == SPEC}
    assert sorted(ids) == ["mv_set"], ids
    bid = L.build_id(d["events"])
    lo = 0x7E4C9514                                  # log_put of log-menu-2 (as mkspec_movtime.py finds it)
    head = bytes.fromhex("cff0f2e6")
    at = [lo + i for i in range(0x40) if get(lo + i, 4) == head]
    assert len(at) == 3 and get(at[2] + 4, 6) == bytes.fromhex("fcab42d04fbe"), at
    bad = L.branch_targets_inside([(s, n) for s, (n, _, _, _) in SITES.items()], blk, work)
    assert not bad, bad
    val = dict(ids)
    for site, (n, routine, _, _) in SITES.items():
        assert get(site, n) == stock[site - BASE:site - BASE + n], "site 0x%X is not in stock bytes" % site
        val["d_" + routine] = L.displaced(blk_path, site, n)
    asm = L.SYMS + ASM % val
    args = ["--defsym=log_put=%#x" % at[2]]
    args += ["--defsym=s_%s=0x%s" % (a, a) for a in sorted(set(re.findall(r"(?:jmp|call)\s+0x([0-9a-f]{8})", asm)))]
    asm = re.sub(r"((?:jmp|call)\s+)0x([0-9a-f]{8})", r"\1s_\2", asm)
    for site, (n, routine, _, _) in SITES.items():
        asm += '\n.section .s%x,"ax"\n    jmp %s\n' % (site, routine) + "    nop\n" * (n - 5)
        args.append("--section-start=.s%x=%#x" % (site, site))
    args += ["--section-start=%s=%#x" % (k, a) for k, (a, _, _) in AREAS.items()]
    s, o, e, sb = (os.path.join(work, "ab." + x) for x in ("s", "o", "elf", "bin"))
    open(s, "w").write(asm)
    L.run(L.BIN + "/mn10300-elf-as", "-o", o, s)
    L.run(L.BIN + "/mn10300-elf-ld", *args, "-e", "%#x" % AREAS[".a1"][0], "-o", e, o)

    def sect(name):
        L.run(L.BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", name, e, sb)
        return open(sb, "rb").read()

    ops = []

    def op(addr, new, note):
        expect = get(addr, len(new))
        assert expect != new, note
        ops.append({"type": "bytes", "block": 0, "offset": "0x%X" % (addr - BASE), "expect": expect.hex(),
                    "new": new.hex(), "_addr": "0x%08X" % addr, "_note": note})

    for name, (a, hi, what) in AREAS.items():
        code = sect(name)
        assert a + len(code) <= hi, "%s: %d B, %d free" % (name, len(code), hi - a)
        assert get(a, hi - a) == stock[a - BASE:hi - BASE], "%s is in use" % name
        if code[-1] == get(a + len(code) - 1, 1)[0]:
            code += b"\xcb"
        routines = ", ".join(r for _, (_, r, sec, _) in SITES.items() if sec == name) + (", SETW" if name == ".a1" else "")
        op(a, code, "new code, %s: %s (%d B)" % (what, routines, len(code)))
        print("%s: %d B at 0x%X-0x%X, %d B free after" % (name, len(code), a, a + len(code), hi - a - len(code)))
    for site, (n, routine, _, what) in SITES.items():
        h = sect(".s%x" % site)
        assert len(h) == n and h[0] == 0xDC
        op(site, h, "hook: jmp %s%s. %s" % (routine, " + nop" * (n - 5), what))
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
        "description": "1080 movie frame by record mode: Full HD Fine (setting 34145 = 6 and 33105[7] = 1) uses the "
                       "1920-wide Bayer frame of movie-wide-frame.json and movie-wide-writer.json (written lines of "
                       "1960 px at a 1.2 resize, 1938 x 1296, 1920 effective); every other record mode, 720 included, "
                       "keeps the stock frame. The choice is made where the frame is set up (the TAKE request builder's "
                       "HSHR case, the writer request for mode code 517, the movie mode table of Through Start) and "
                       "stored in one RAM byte that the later readers (Movie IS crop and shift, the IMG divisors, "
                       "art_get_bayer_size) read. Event mv_set records each choice. Eight hooks in stock bytes; the "
                       "set-up routines and the IS shift in segment 1; the IS crop, the IMG divisors and "
                       "art_get_bayer_size in segment 2 (they run only in movie frames with Movie IS and in art jobs; "
                       "emulator/hookcheck-allow.tsv). Needs data/builds/debug-log-movie-bitrate.json's specs before it. It puts the build id "
                       "%s of data/logdict/events.json into the block header. DEBUG builds only. See "
                       "experiments/2026-11-19-movie-sampling/NOTES.md section 16." % bid.hex(),
        "base": L.STOCK, "base_sha256": hashlib.sha256(open(os.path.join(ROOT, L.STOCK), "rb").read()).hexdigest(),
        "status": "candidate: emulator-checked, not flashed",
        "_delta_on": "data/builds/debug-log-movie-bitrate.json",
        "_build_id": bid.hex(),
        "_ram": "1 byte at 0x7E4FD31C (uncached 0xBE4FD31C), byte 28 of log-movie-time's 32 bytes",
        "ops": ops,
    }, open(out, "w"), indent=1)
    open(out, "a").write("\n")
    print("wrote", os.path.relpath(out, ROOT), len(ops), "ops; build id", bid.hex())
    if listing:
        txt = L.run(L.BIN + "/mn10300-elf-objdump", "-d", *sum((["-j", k] for k in AREAS), []),
                    *sum((["-j", ".s%x" % x] for x in SITES), []), e)
        open(listing, "w").write(re.sub(r"/[^\s:]*ab\.elf", "ab.elf", txt))


if __name__ == "__main__":
    main()
