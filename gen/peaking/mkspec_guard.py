"""Write data/specs/peaking-save-guard.json: peaking waits while another owner has blocks in the image-work heap.

Research code. NOTES.md section 18. The spec is a delta on the pinned build data/builds/peaking-fast.json: every
`expect` is a byte string of that build, not of the stock file.

Two rules, both read the heap's own counters (the test of the stock setter 0x7E578C60, 0x7E578FC0 -> 0x7E577016:
blocks in use of a pool = u16 (pool + 16) - u16 (pool + 76)):
  T_GUARD  in the latch T_A, after every stock condition for L = 1 has passed: when the heap is not in mode 1
           and the pool of the modes 0 and 2 has a block in use (a still that is being developed), L becomes 2
           in place of 1. Every reader of L and L2 compares with 1, so 2 is "no peaking": MF Assist magnifies as
           with Peaking Off. T_A runs again in every frame, so the lines start in the first frame in which the
           pool is empty.
  T_M2     in the heap-mode hook T_M, when peaking does not ask for mode 1: when the stock choice is not mode 1,
           the heap is in mode 1 and the pool of mode 1 still has a block in use, the mode stays 1. The next
           call of the chooser with an empty pool gives the stock mode.

No free byte is left in the kernel range of the debug builds, so the new code takes the place of code that
peaking-fast left without a reader: the row loop of peaking-colours (0x7E4C9496-0x7E4C94F8). The generator checks
that no instruction and no word of the image names an address inside the bytes it replaces. One byte of that loop
is 0xFF as in the stock file (0x7E4C94F4, in a jump displacement). `epm2mod make` lets no later spec change such a
byte, so the code is placed with its end at 0x7E4C94F8 and a 0xFF byte of its own on that address.

Usage: uv run python gen/peaking/mkspec_guard.py WORKDIR [LISTING.txt]
  WORKDIR     scratch folder for the assembler files (outside the repository)
Writes data/specs/peaking-save-guard.json. Copied from experiments/2026-11-14-focus-peaking/scripts/mkspec_guard.py, which read the
unpacked build data/builds/peaking-fast.json. This copy patches the specs of data/builds/films-look-exif.json that come
before peaking-save-guard (base.py, EARLIER): the bytes it reads are the same in both.
"""
import hashlib, json, os, re, struct, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import BIN, EARLIER, ROOT, STOCK, payloads  # noqa: E402
BASE = 0x7E421020
PINNED_SHA = "0e8a25b9578b8119b14b4895be7d2a0b70d7315e5e817758699777f0f31d917e"

DEAD = (0x7E4C9496, 0x7E4C94F8)      # peaking-colours: the per-pixel part of its row loop. Its one entry was the
                                     # `bne` at 0x7E4C9469, in the loop that peaking-fast cut off at 0x7E4C9453
DEAD_ENTRY = (0x7E4C9469, "c92d")    # that `bne 0x7E4C9496`
CUT = (0x7E4C9453, 0xDC)             # `jmp T_FAST` of peaking-fast, in place of the loop head
HOOK_A = (0x7E4C923F, "4400f85104")             # T_A: inc d1 / clr d0 / movbu d0,(4,a1), before `inc d0`
HOOK_M = (0x7E4C9346, "c910fca4d0035b60")       # T_M: bne 0x7E4C9356 / mov (0x605B03D0),d0
A_HOLD, A_GO, M_ONE, M_STOCK = 0x7E4C9248, 0x7E4C9244, 0x7E4C9354, 0x7E4C9356

ASM = """
.equ HMODE,  0x605157cc      # u16 heap mode (0, 1 = art work buffers, 2)
.equ POOL1,  0x602ac458      # pointer to the pool of mode 1
.equ POOL02, 0x602ac45c      # pointer to the pool of the modes 0 and 2
.equ MOVSM,  0x605b03d0      # mov state number
.macro j16 target             # `jmp d16`, 3 bytes: the assembler gives the 5-byte form for a far symbol
    .byte 0xcc
    .hword \\target - . + 1
.endm
.section .g,"ax"
T_GUARD:                     # from T_A: R is set, the setting is not Off, no movie, live-view kind not 2 / 5.
                             # d1 = 0, a1 = live-view struct. Out: to A_GO with d1 = 1, d0 = 0 and struct +4 = 0,
                             # or to A_HOLD with d1 = 2 (T_A stores d1 in L)
    movhu (HMODE),d0
    cmp 1,d0
    beq 1f                   # the heap is in the art mode already: nothing will be re-divided
    mov (POOL02),a0
    movhu (16,a0),d0
    movhu (76,a0),d1
    sub d1,d0                # blocks in use in the pool that the switch to mode 1 would leave
    beq 1f
    mov 2,d1                 # held: d0 = the number of blocks
G_HOLD:
    j16 s_%(a_hold)08x
1:  mov 1,d1
    clr d0
    movbu d0,(4,a1)
    j16 s_%(a_go)08x
T_M2:                        # from T_M: d1 = the stock mode, the flags are those of getL (Z: L is 1)
    bne 2f
    mov (MOVSM),d0
    add -1,d0
    cmp 2,d0
    bhi 2f
M_FORCE:
    j16 s_%(m_one)08x          # peaking asks for mode 1, as before
2:  cmp 1,d1
    beq 3f
    movhu (HMODE),d0
    cmp 1,d0
    bne 3f
    mov (POOL1),a0
    movhu (16,a0),d0
    mov d1,a1
    movhu (76,a0),d1
    sub d1,d0                # blocks in use in the pool of mode 1
    mov a1,d1                # mov keeps the flags
    beq 3f
M_HOLD:
    j16 M_FORCE              # another owner still has a block there: the heap stays in mode 1. This jump goes
                             # back, so its last byte is 0xFF: it lies on the 0xFF byte that peaking-colours keeps
3:  j16 s_%(m_stock)08x
"""


def run(*a):
    return subprocess.run(a, check=True, capture_output=True, text=True).stdout


def targets_inside(lo, hi, blk, work):
    """4-byte words of block 0 that name an address in lo..hi-1. The experiment's script also looked for
    instructions that name one in the listings build/map/functions.txt and linear.txt (no hit); those are build
    output, so this copy does not read them."""
    hits = []
    for a in range(lo, hi):
        i = blk.find(struct.pack("<I", a))
        if i >= 0:
            hits.append("word 0x%08X at 0x%X" % (a, BASE + i))
    return hits


def main():
    out = os.path.join(ROOT, "data", "specs", "peaking-save-guard.json")
    work = sys.argv[1]
    listing = sys.argv[2] if len(sys.argv) > 2 else None
    os.makedirs(work, exist_ok=True)
    blk = payloads(EARLIER + ["peaking-colours", "peaking-fast"])[0]
    get = lambda a, n: blk[a - BASE:a - BASE + n]
    ops = []

    def op(addr, new, note):
        expect = get(addr, len(new))
        assert expect != new, note
        ops.append({"type": "bytes", "block": 0, "offset": "0x%X" % (addr - BASE), "expect": expect.hex(),
                    "new": new.hex(), "_addr": "0x%08X" % addr, "_note": note})

    # the bytes that get new code have no reader: their one entry is in the loop that peaking-fast cut off
    assert get(*CUT[:1], 1)[0] == CUT[1] and get(DEAD_ENTRY[0], 2).hex() == DEAD_ENTRY[1]
    assert get(HOOK_A[0], 5).hex() == HOOK_A[1] and get(HOOK_M[0], 8).hex() == HOOK_M[1]
    assert get(M_ONE, 3).hex() == "850184" and get(A_GO, 4).hex() == "40f85105"
    stock = payloads()[0]
    assert stock[DEAD[0] - BASE:DEAD[1] - BASE] == b"\xff" * (DEAD[1] - DEAD[0])
    refs = targets_inside(DEAD[0], DEAD[1], blk, work) + targets_inside(HOOK_A[0] + 1, HOOK_A[0] + 5, blk, work) + \
        targets_inside(HOOK_M[0] + 1, HOOK_M[0] + 8, blk, work)
    assert not refs, refs
    asm = ASM % {"a_hold": A_HOLD, "a_go": A_GO, "m_one": M_ONE, "m_stock": M_STOCK}
    asm += '\n.section .ha,"ax"\n    jmp T_GUARD\n'
    asm += '\n.section .hm,"ax"\n    jmp T_M2\n' + "    nop\n" * 3
    args = ["--defsym=s_%s=0x%s" % (a, a) for a in sorted(set(re.findall(r"s_([0-9a-f]{8})", asm)))]
    s, o, e, sb = (os.path.join(work, "guard." + x) for x in ("s", "o", "elf", "bin"))
    open(s, "w").write(asm)
    run(BIN + "/mn10300-elf-as", "-o", o, s)

    def link(start):
        run(BIN + "/mn10300-elf-ld", *args, "--section-start=.g=%#x" % start, "--section-start=.ha=%#x" % HOOK_A[0],
            "--section-start=.hm=%#x" % HOOK_M[0], "-e", "%#x" % start, "-o", e, o)
        return {l.split()[2]: int(l.split()[0], 16) for l in run(BIN + "/mn10300-elf-nm", e).splitlines() if len(l.split()) == 3}

    def sect(name):
        run(BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", name, e, sb)
        return open(sb, "rb").read()

    link(DEAD[0])
    start = DEAD[1] - len(sect(".g"))            # the code ends where the old loop ends
    assert start >= DEAD[0], "%d bytes, %d free" % (DEAD[1] - start, DEAD[1] - DEAD[0])
    sym = link(start)

    code = sect(".g")
    kept = [start + i for i in range(len(code)) if get(start + i, 1) == stock[start + i - BASE:start + i - BASE + 1]]
    assert all(code[a - start] == 0xFF for a in kept), kept      # a byte that an earlier spec keeps as stock stays
    op(start, code, "new code in place of the row loop of peaking-colours that peaking-fast left without a reader: "
       "T_GUARD, T_M2 (%d B)" % len(code))
    ha, hm = sect(".ha"), sect(".hm")
    assert len(ha) == 5 and len(hm) == 8 and ha[0] == hm[0] == 0xDC
    op(HOOK_A[0], ha, "T_A, after the last stock condition: `inc d1` / `clr d0` / `movbu d0,(4,a1)` -> `jmp T_GUARD`")
    op(HOOK_M[0], hm, "T_M, after `call getL`: `bne` / `mov (0x605B03D0),d0` -> `jmp T_M2` + 3 nop")
    spec = {
        "name": "peaking-save-guard",
        "description": "Focus peaking waits while another owner has blocks in the image-work heap. (1) The latch: when "
                       "the heap is not in mode 1 and the pool of the modes 0 and 2 has a block in use (a photo that is "
                       "being developed and saved), the latch byte L gets 2 in place of 1: MF Assist magnifies at once, "
                       "as with Peaking Off, and the lines start in the first frame in which the pool is empty. (2) The "
                       "heap-mode hook: when peaking ends and the pool of mode 1 still has a block in use, the heap "
                       "stays in mode 1 until a later call finds the pool empty. Before, the heap was re-divided under "
                       "those blocks, the art buffers were refused in every frame, and the camera restarted (firmware "
                       "error 0x34000002, camera log of 2026-11-16). A delta on data/builds/peaking-fast.json: every expect "
                       "is a byte string of that build. See experiments/2026-11-14-focus-peaking/NOTES.md section 18.",
        "base": STOCK,
        "base_sha256": hashlib.sha256(open(os.path.join(ROOT, STOCK), "rb").read()).hexdigest(),
        "_delta_on": "data/builds/peaking-fast.json (sha256 %s)" % PINNED_SHA,
        "_ram": "no new RAM. L (0x602BE8C4) and its copy L2 can now hold 2 = held by the guard; reads the heap mode "
                "0x605157CC and the two pool objects named at 0x602AC458 / 0x602AC45C",
        "_symbols": {k: "0x%08X" % sym[k] for k in ("T_GUARD", "G_HOLD", "T_M2", "M_HOLD")},
        "ops": ops,
    }
    json.dump(spec, open(out, "w"), indent=1)
    open(out, "a").write("\n")
    print("wrote", os.path.relpath(out, ROOT), len(ops), "ops; new code %d B at 0x%X-0x%X, %d B of the old loop left before it" % (
        len(code), start, start + len(code), start - DEAD[0]))
    if listing:
        img = bytearray(blk)
        for x in ops:
            off = int(x["offset"], 16)
            img[off:off + len(x["new"]) // 2] = bytes.fromhex(x["new"])
        open(sb, "wb").write(img)                 # the listing is made from the patched bytes: `.byte` jumps
        txt = ""
        for a, n in ((start, len(code)), (HOOK_A[0], 5), (HOOK_M[0], 8)):
            txt += run(BIN + "/mn10300-elf-objdump", "-D", "-b", "binary", "-m", "mn10300", "--adjust-vma=%#x" % BASE,
                       "--start-address=%#x" % a, "--stop-address=%#x" % (a + n), sb).split("<.data", 1)[-1]
        open(listing, "w").write("T_GUARD 0x%08X, T_M2 0x%08X, hook in T_A, hook in T_M\n" % (sym["T_GUARD"], sym["T_M2"]) + txt)
        os.remove(sb)

main()
