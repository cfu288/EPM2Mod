#!/usr/bin/env python3
"""Write data/specs/raw-edit-art-bkt.json: an ART BKT row in RAW Data Edit (NOTES.md section 8).

    uv run python experiments/2026-11-20-raw-edit-art-bkt/scripts/mkspec_artbkt.py [WORKDIR]

Research code. The source below (ASM) is assembled with the MN103 binutils into the free run 0x7EBB2AC4-0x7EBB2FEC
(segment 2, reclaim-space row 2). Ops:
  1. the code and data;
  2. list 320 (RAW Data Edit): count 4 -> 5 (0x7F00D564), items -> ITEMS (0x7F00D568);
  3. H1, 0x7EDF7DF3 in the list's OK handler 0x7EDF7DDD: `mov 1744,a0; add a3,a0` -> `jmp ROWS`;
  4. H2, 0x7EDF812C in RawEditProcessCallback 0x7EDF7F60 (command 47, status 164 = job done):
     `mov d2,d0; mov d0,d1; call 0x7EDC712F` -> `jmp CBDONE; nop x 4`.
The expect bytes are stock: no spec of data/builds/films-look-exif.json changes these bytes (asserted).
FILMNAME is card-looks-6's routine (experiments/2026-11-20-film-name-exif/NOTES.md section 3); its first bytes are
checked in card-looks-6's op.
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import disasm, oetool  # noqa: E402

BASE = 0x7E421020
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
BUILD = "data/builds/films-look-exif.json"
AREA, AREA_END = 0x7EBB2AC4, 0x7EBB2FEC          # free in the ledger (tools/freespace.py area 0x7EBB2AC4)
H1, H2 = 0x7EDF7DF3, 0x7EDF812C
COUNT, ITEMS_PTR = 0x7F00D564, 0x7F00D568
STOCK_ITEMS = 0x7F00D368                          # Current 1760, Custom1 1761, Custom2 1762, No 496 (12 B each)
FILMNAME = 0x7EE53BFE
FILMNAME_HEAD = bytes.fromhex("cff0f8fef4fccc81940000")   # movm [d2,d3,a2,a3],(sp); add -12,sp; mov 0x9481,d0
TEXT_ART_BKT = 1699                               # the title of the ART BKT screen (NOTES.md section 8.1)

EXT = {
    "OK_DISPATCH": 0x7EDF7DFA,   # clr d3; clr d2; then the stock dispatch on d0 (a0 = the row byte)
    "OK_CURRENT": 0x7EDF7E14,    # the [Current] path: startCurrent(0, RawEditProcessCallback)
    "CB_RESULT": 0x7EDF8135,     # the callback after 0x7EDC712F: cmp 0,a2 (the job's result)
    "CB_DONE_UI": 0x7EDC712F,    # the callback's call at a done job (displaced by H2)
    "RAWCB": 0x7EDF7F60,         # RawEditProcessCallback
    "PAGE_KEY": 0x7EDCDABF,      # (a0 page, a1 transition record): store the record, as the Custom path does
    "PV_ARG0": 0x602BA97C,       # previewCurrent's d0 and a1, as page 611 loads them (the picture being edited)
    "PV_ARG1": 0x602BA978,
    "API": 0x7E9C34D1,           # OlyApiEditRaw getter -> a0; vtable +8 endCurrent(d0), +24 saveCurrent, +32 startCurrent(d0, a1)
    "PRM_GET": 0x7E457C75,       # (d0 tag, a0 0, d1 0) -> d0
    "PRM_SET": 0x7E457CED,       # (d0 tag, a0 0, d1 0, a1 value), the form of play_edit_raw_main 0x7E940F1A
    "COMPOSE": 0x7E5A75AE,       # the ART bracket composer after its On/Off gate; a2 = take
    "ALLOC": 0x7E507325,         # scheap large pool: a 16 KB block -> a0, or 0
    "FREE": 0x7E507333,          # a0 = the block
    "FILMNAME": FILMNAME,
}

ASM = r"""
        .text
        .global _start
        .equ PM_TAG, 0x9481             # the stored Picture Mode
        .equ NMAX, 31                   # frames kept from the composer's list (it makes at most 1 + 26)
_start:

# H1 (0x7EDF7DF3, the OK handler of list 320; a3 = the page). Rows 0 Current, 1 Custom1, 2 Custom2, 3 ART BKT, 4 No.
# The handler's (12,sp) holds the page's transition record (read by 0x7EDCDAAB at its start); its byte +5, (17,sp),
# is the key the GUI leaves the page with: the row, and 4 for Custom1 / Custom2 (set by the stock Custom path).
ROWS:   mov     1744,a0
        add     a3,a0
        movbu   (a0),d0                 # the row
        clr     d1
        movbu   d1,(ACT)                # an OK on the list ends an earlier run
        cmp     3,d0
        beq     2f
        cmp     4,d0
        bne     1f
        mov     3,d0                    # No: key 3 and the stock row 3 path, as the stock No
        call    KEY,[],4
        mov     3,d0
1:      jmp     OK_DISPATCH
2:      call    SETUP,[d2,d3,a2,a3],20
        clr     d0                      # key 0: the GUI goes on as for [Current] (to page 611, which starts the preview)
        call    KEY,[],4
        clr     d3
        clr     d2
        jmp     OK_CURRENT              # frame 0 is the current Picture Mode: a stock [Current] edit

# KEY(d0): the handler's transition key = d0 (called from ROWS: the handler's frame is at sp + 4)
KEY:    movbu   d0,(21,sp)
        mov     (12,sp),a1
        mov     a3,a0
        call    PAGE_KEY,[],4
        ret     [],4

# SETUP: the frame list as an ART bracket shot makes it, the Picture Mode to restore, the run state
SETUP:  mov     PM_TAG,d0
        mov     0,a0
        clr     d1
        call    PRM_GET,[d2,d3],12
        mov     d0,(PM0)
        mov     LIST,a1
        movbu   d0,(a1)                 # no block: the current Picture Mode only
        clr     d1
        movbu   d1,(1,a1)
        call    ALLOC,[],4
        cmp     0,a0
        beq     8f
        mov     a0,d3                   # the composer keeps d2, d3, a2, a3
        mov     a0,a2
        add     -16446,a2               # it reads take +16446..+17145 and writes 18-byte frames from +17154
        call    COMPOSE,[d2,d3,a2,a3],20
        mov     d3,a0
        add     708,a0                  # frame 0 (17154 - 16446); byte 0 = the Picture Mode, 0 ends the list
        mov     LIST,a1
        mov     NMAX,d1
1:      movbu   (a0),d0
        movbu   d0,(a1)
        cmp     0,d0
        beq     2f
        add     18,a0
        inc     a1
        add     -1,d1
        bne     1b
        clr     d0
        movbu   d0,(a1)
2:      mov     d3,a0
        call    FREE,[],4
8:      clr     d0
        movbu   d0,(K)
        movbu   d0,(PH)
        mov     1,d0
        movbu   d0,(ACT)
        ret     [d2,d3,a2,a3],20

# H2 (0x7EDF812C, RawEditProcessCallback, command 47 status 164: a job is done; a2 = its result)
CBDONE: mov     d2,d0
        mov     d0,d1
        call    CB_DONE_UI,[],4         # displaced
        movbu   (ACT),d0
        cmp     0,d0
        beq     9f
        mov     a2,d0
        call    STEP,[d2,d3,a2,a3],20
        cmp     0,d0
        beq     9f
        ret     [d2,d3,a2,a3],132       # the run took the event: return as the callback does
9:      jmp     CB_RESULT

# STEP(d0 = result) -> d0 = 1: the run goes on (no stock screen), 0: the stock handles the event
STEP:   cmp     0,d0
        bne     STOP                    # an error (a full card, ...): the stock shows it
        movbu   (PH),d0
        cmp     1,d0
        beq     SAVE
        cmp     2,d0
        beq     NEXT
        mov     2,d0                    # phase 0: frame 0's preview; the stock asks Yes / No once
        movbu   d0,(PH)
        clr     d0
        bra     9f
SAVE:   call    API,[],4                # our preview is done: save it without Yes / No
        mov     (a0),a1
        mov     (24,a1),a1
        calls   (a1)
        mov     2,d0
        movbu   d0,(PH)
        mov     1,d0
        bra     9f
NEXT:   movbu   (K),d0                  # a save is done: the next frame
        inc     d0
        movbu   d0,(K)
        mov     LIST,a0
        movbu   (d0,a0),d0
        cmp     0,d0
        beq     STOP                    # the last frame: the stock shows Reset / No
        call    PMSET,[],4
        call    API,[],4                # end the edit as Reset does, then [Current] again
        mov     (a0),a1
        mov     (8,a1),a1
        mov     1,d0
        calls   (a1)
        call    API,[],4
        mov     (a0),a2
        mov     RAWCB,a1
        mov     (32,a2),a2
        clr     d0
        calls   (a2)
        cmp     0,d0
        bne     STOP
        call    API,[],4                # and the preview, as page 611 (0x7EDFA754) starts it for [Current]
        mov     (a0),a2
        mov     (PV_ARG1),a1
        mov     (16,a2),a2
        mov     (PV_ARG0),d0
        calls   (a2)
        cmp     0,d0
        bne     STOP
        mov     1,d0
        movbu   d0,(PH)
        bra     9f
STOP:   mov     (PM0),d0                # the Picture Mode back, the run ends
        call    PMSET,[],4
        clr     d0
        movbu   d0,(ACT)
9:      ret     [d2,d3,a2,a3],20

# PMSET(d0 = value): the stored Picture Mode, and the EXIF ImageDescription for it (FILMNAME)
PMSET:  mov     d0,a1
        mov     PM_TAG,d0
        mov     0,a0
        clr     d1
        call    PRM_SET,[d2,d3,a2],16
        calls   FILMNAME
        ret     [],4

        .balign 4
ITEMS:  .short 2, 1760, 0, 0, 0, 0      # Current, Custom1, Custom2 (the stock items), ART BKT, No
        .short 2, 1761, 0, 0, 0, 0
        .short 2, 1762, 0, 0, 0, 0
        .short 2, %(art)d, 0, 0, 0, 0
        .short 2, 496, 0, 0, 0, 0
PM0:    .long 0
ACT:    .byte 0                         # 1 while a run is on
PH:     .byte 0                         # 0 frame 0's preview, 1 our preview, 2 a save
K:      .byte 0                         # the frame being made
        .balign 4
LIST:   .space NMAX + 1
"""


def asm(work, name, src, addr, ext):
    bindir = os.path.dirname(disasm.objdump_path())
    s, o, elf, out = (os.path.join(work, name + x) for x in (".s", ".o", ".elf", ".bin"))
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


def main():
    work = sys.argv[1] if len(sys.argv) > 1 else "/dev/shm/artbkt-asm"
    os.makedirs(work, exist_ok=True)
    raw = open(os.path.join(ROOT, STOCK), "rb").read()
    b0 = oetool.parse(raw)[0][0]["payload"]

    def stock(addr, n):
        return b0[addr - BASE:addr - BASE + n]

    code, syms = asm(work, "artbkt", ASM % {"art": TEXT_ART_BKT}, AREA, EXT)
    if AREA + len(code) > AREA_END:
        sys.exit(f"{len(code)} bytes do not fit in {AREA_END - AREA}")
    hdr = "        .text\n        .global _start\n_start:\n"
    h1, _ = asm(work, "h1", hdr + "        jmp ROWS\n", H1, {"ROWS": syms["ROWS"]})
    h2, _ = asm(work, "h2", hdr + "        jmp CBDONE\n        nop\n        nop\n        nop\n        nop\n", H2,
                {"CBDONE": syms["CBDONE"]})

    # the stock bytes each op replaces, and their meaning
    assert stock(H1, 7).hex() == "24d006f17cf040", stock(H1, 7).hex()          # mov 1744,a0; add a3,a0; movbu (a0),d0
    assert stock(H2, 9).hex() == "8881dd01f0fcff0004", stock(H2, 9).hex()   # mov d2,d0; mov d0,d1; call 0x7EDC712F,[],4
    assert stock(COUNT, 8) == (4).to_bytes(4, "little") + STOCK_ITEMS.to_bytes(4, "little")
    assert len(h1) == 5 and h1[0] == 0xDC and len(h2) == 9 and h2[0] == 0xDC, (h1.hex(), h2.hex())
    stock_items = stock(STOCK_ITEMS, 48)
    items = code[syms["ITEMS"] - AREA:syms["ITEMS"] - AREA + 60]
    assert items[:36] == stock_items[:36] and items[48:] == stock_items[36:], items.hex()

    # nothing of the base build changes these bytes; FILMNAME is where card-looks-6 puts it
    ranges = [(AREA, AREA + len(code)), (H1, H1 + 5), (H2, H2 + 9), (COUNT, COUNT + 8)]
    found = False
    for path in json.load(open(os.path.join(ROOT, BUILD)))["specs"]:
        for op in json.load(open(os.path.join(ROOT, path)))["ops"]:
            if op.get("block", 0) != 0:
                continue
            a, new = BASE + int(op["offset"], 16), bytes.fromhex(op["new"])
            assert not any(a < hi and a + len(new) > lo for lo, hi in ranges), (path, hex(a))
            if a <= FILMNAME < a + len(new):
                found = new[FILMNAME - a:FILMNAME - a + len(FILMNAME_HEAD)] == FILMNAME_HEAD and path.endswith("card-looks-6.json")
    assert found, "FILMNAME is not at %#x in card-looks-6" % FILMNAME

    def op(addr, new, note):
        return {"type": "bytes", "block": 0, "offset": "%#x" % (addr - BASE), "expect": stock(addr, len(new)).hex(),
                "new": new.hex(), "_addr": "%#X" % addr, "_note": note}

    spec = {
        "name": "raw-edit-art-bkt",
        "description": "An ART BKT row in RAW Data Edit (Current, Custom1, Custom2, ART BKT, No). It develops the RAW once "
                       "per frame of the camera's ART BKT selection, as an ART bracket shot lists them: the current "
                       "Picture Mode first, then each entry that is On. Frame 0 is a stock [Current] edit with its "
                       "Yes / No; each later frame is a stock [Current] edit started and saved by the callback, with "
                       "the stored Picture Mode (prm 0x9481) and the EXIF film name (FILMNAME) set first. The Picture "
                       "Mode comes back at the end and at any error. Needs card-looks-6 (FILMNAME) and the stock-films "
                       "composer hooks. See experiments/2026-11-20-raw-edit-art-bkt/NOTES.md section 8.",
        "base": STOCK, "base_sha256": hashlib.sha256(raw).hexdigest(),
        "status": "candidate: emulator-checked, not flashed",
        "_symbols": {k: "%#X" % v for k, v in sorted(syms.items()) if k[0].isalpha() and v >= AREA},
        "ops": [
            op(AREA, code, f"new code and data, {len(code)} B of {AREA_END - AREA} (reclaim-space row 2, segment 2)"),
            op(COUNT, (5).to_bytes(4, "little") + syms["ITEMS"].to_bytes(4, "little"),
               "list 320 (RAW Data Edit): 5 items at ITEMS"),
            op(H1, h1, "H1: the list's OK handler dispatches rows 0-4 in ROWS"),
            op(H2, h2, "H2: a done job of RawEditProcessCallback goes through CBDONE (the displaced call is in it)"),
        ],
    }
    p = os.path.join(ROOT, "data", "specs", "raw-edit-art-bkt.json")
    json.dump(spec, open(p, "w"), indent=1)
    print("wrote", os.path.relpath(p, ROOT), len(code), "bytes;", spec["_symbols"])


if __name__ == "__main__":
    main()
