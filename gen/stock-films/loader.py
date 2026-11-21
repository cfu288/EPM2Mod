"""Write data/specs/looks-menu-4.json and data/specs/card-looks-7.json: the loader of film simulations for the
stock-filters firmware (experiments/2026-11-18-stock-filters/design.md). Needs build/stock-films/layout.json
(gen/stock-films/structure.py).

    uv run python gen/stock-films/loader.py WORKDIR [LISTING.txt]

Versions: 5 the loader; 6 FILMNAME, which writes the EXIF template's ImageDescription (the film's name, or Olympus's
text when the entry has no film; experiments/2026-11-20-film-name-exif/NOTES.md); 7 the switch lists of
stock-films-structure-3 (experiments/2026-11-20-model-calibration/NOTES.md §6). This file makes version 7; versions 5
and 6 are committed spec files, made by this file at earlier commits.

The camera-tested loader of card-looks-4 (experiments/2026-11-17-card-looks/scripts/mkspec_looks3.py), changed:
  * no snapshot, no live-table interpolation, no Built-in (the row is Off / Load: looks-menu-4);
  * APPLY writes each listed entry into the entry's RAM block: one operation list for all twelve entries, with
    addresses relative to the block (tone: 8 tables per channel, the curve read at each stock default table);
  * SWITCH: for each entry its words of layout.json, the film bytes when the file lists the entry, else the stock
    bytes (words are written as words);
  * PMREMAP, from T_GUI after a Load: the info ids 111 (Picture Mode), 509, 510 (Get/Set_CameraInfo) that hold the
    stock value of an entry that now has a film get its hidden value, and the other way round.
"""

import hashlib
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CL = HERE  # mkspec_looks, mkspec_looks3, mkspec_slots: copies of experiments/2026-11-17-card-looks/scripts/
sys.path.insert(0, CL)
sys.path.insert(0, os.path.join(ROOT, "cli", "src"))
_argv, sys.argv = sys.argv, [sys.argv[0], "--v4"]
import mkspec_looks as mk  # noqa: E402
import mkspec_looks3 as m3  # noqa: E402
sys.argv = _argv
from epm2mod.container import parse  # noqa: E402
from epm2mod.looks import lookfile, slots  # noqa: E402

# The version this generator makes. A camera-tested version stays as its committed spec file (a pinned build names it);
# the generator that made it is in git history.
SPEC, MENU = "card-looks-7", "looks-menu-4"
OUT = "stock-films"   # build/OUT: layout.json in, syms.json out
FLAGS_V1, T_END_V1 = 0x7ECB0FCC, 0x7EE5392B   # card-looks-5's FLAGS and T_END: version 6 keeps them
EXIF_DESC = 0x605BAEC0        # the EXIF template's ImageDescription, 32 B (template 0x605BA918 + 0x5A8)
EXIF_DESC_STOCK = 0x7E8517C2  # "OLYMPUS DIGITAL CAMERA", which the boot copies there with 0x7E70B0F6
BASE, BIN = mk.BASE, mk.BIN
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
RUNS = dict(m3.RUNS)
RUNS[".ap"] = RUNS[".x1"]                     # APPLY grows: with the rest in the reclaimed area of segment 3
del RUNS[".x1"]
DATA = [(0x7EE40B18, 0x7EE411F6), (0x7F033B7C, 0x7F034000), (0x7EE546C4, 0x7EE548B0)]
PMSETTINGS = (111, 509, 510)                  # info ids that hold a stored Picture Mode value

HEAD_REPLACE = [
    # equates: no snapshot, no live tables, the switch table; REMAP is a fifth flag byte in the code (0 at boot)
    (""".equ LIVEREC,  %(liverec)#x      # 36 u32: three tone records per slot (0: none)
""", """.equ SWTAB,    %(swtab)#x        # 12 pointers: each entry's switch list {u32 count, count x {u32 address,
                                 # u8 size, 3 x 0, 4 film bytes, 4 stock bytes}}
.equ BLOCKS,   %(blocks)#x       # 12 u32: each entry's RAM block
.equ PMSET,    %(pmset)#x        # u16 info ids, 0 at the end
.equ PMMAP,    %(pmmap)#x        # 5 x {u8 stock value, u8 hidden value, u16 0, u32 the entry's byte in list 111}
"""),
    (""".equ DEFREC,   %(defrec)#x       # the stock default tone record: 4 columns x (member 0, member 1)
""", ""),
    (""".equ RSNAP,    RAMU + 0x800      # the built-in tables, %(snapn)d B
.equ RLIVE,    %(rlive)#x        # 36 x 4 x 512 B: member-0 tables (cached address: records hold cached addresses)
""", ""),
    (""".equ MODE,     FLAGS_U + 3       # 0 start, 1 load, 2 built-in, 3 texts and names
""", """.equ MODE,     FLAGS_U + 3       # 0 start, 1 load, 3 texts and names
.equ REMAP,    FLAGS_U + 4       # 1: the task switched entries; T_GUI maps the Picture Mode settings
"""),
    ("FLAGS: .byte 0, 0, 0, 0\n", "FLAGS: .byte 0, 0, 0, 0, 0\n    .balign 4\n"),
    # T_GUI: the remap first, in the GUI task
    ("""    movbu (BUSY),d0
    cmp 0,d0
    bne 9f
    movbu (APPLIED),d0
""", """    movbu (BUSY),d0
    cmp 0,d0
    bne 9f
    movbu (REMAP),d0
    cmp 0,d0
    beq 4f
    clr d0
    movbu d0,(REMAP)
    calls PMREMAP
4:  movbu (APPLIED),d0
"""),
    # T_TASK: no mode 2, no snapshot
    ("""    cmp 2,d0
    beq T_BUILT
    cmp 0,d0
    bne T_LOAD
    clr d0                       # mode 0: keep the built-in tables before anything changes them
    calls COPYALL
    clr d0
""", """    cmp 0,d0
    bne T_LOAD
    clr d0                       # mode 0, the first GUI state: the stored looks
"""),
    ("""T_LOADED:
    mov S_LOADED,d0
    mov d0,(RSTAT)
    bra 7f
T_BUILT:                         # mode 2: the store is no longer a look file; the built-in tables back
    clr d0
    mov d0,(STORE)
    mov d0,(STORE + 0x40000000)
    call 0x7e680272,[],48        # the bank save API
    mov S_BUILTIN,d0
    mov d0,(RSTAT)
7:  mov 1,d0                     # the built-in tables back (a load starts from them)
    calls COPYALL
T_STORED:""", """T_LOADED:
    mov S_LOADED,d0
    mov d0,(RSTAT)
T_STORED:"""),
    ("""    mov STORE,a0
    calls APPLY
    bra 2f
1:  clr d0
    movbu d0,(STOREOK)
2:  calls LIVE
""", """    mov STORE,a0
    calls APPLY
    mov STORE,a0
    calls MASK                   # d0: the entries the file lists
    bra 2f
1:  clr d0
    movbu d0,(STOREOK)
2:  calls SWITCH                 # film words for those entries, stock words for the others
    movbu (MODE),d0              # after a Load only: the Picture Mode settings take the switched values (at a start
    cmp 1,d0                     # they hold them already: saved after the Load)
    bne 3f
    movbu d0,(REMAP)
3:
"""),
    # the row's texts: Load Looks, Load, the help (no Built-in)
    ("""    mov TXTTAB,a0
    mov 4,d3
""", """    mov TXTTAB,a0
    mov 3,d3
"""),
]

NEW_ASM = r"""
.section .x2,"ax"
MASK:                            # a0 = a valid look file -> d0 = bit n for each entry n it lists
    movm [d2,d3],(sp)
    movbu (5,a0),d1
    add 32,a0
    clr d0
1:  cmp 0,d1
    beq 9f
    movbu (a0),d2
    mov 1,d3
    asl d2,d3
    or d3,d0
    add 1708,a0
    add -1,d1
    bra 1b
9:  movm (sp),[d2,d3]
    rets

SWITCH:                          # d0 = the entries with a film
    movm [d2,d3,a2,a3],(sp)
    add -8,sp
    mov d0,d3
    clr d2
1:  mov d2,d0
    asl2 d0
    mov SWTAB,a2
    mov (d0,a2),a2
    mov (a2),d0
    mov d0,(4,sp)                # words left in the entry's list
    add 4,a2
2:  mov (4,sp),d0
    cmp 0,d0
    beq 6f
    add -1,d0
    mov d0,(4,sp)
    mov (a2),a0                  # the address
    mov a2,a1
    add 8,a1                     # the film bytes
    mov d3,d0
    lsr d2,d0
    btst 1,d0
    bne 3f
    add 4,a1                     # no film: the stock bytes
3:  movbu (4,a2),d1
    cmp 4,d1
    bne 4f
    mov (a1),d0                  # a word: one write, so no reader sees half of it
    mov d0,(a0)
    mov d0,(0x40000000,a0)
    bra 5f
4:  movbu (a1),d0
    movbu d0,(a0)
    movbu d0,(0x40000000,a0)
    inc a0
    inc a1
    add -1,d1
    bne 4b
5:  add 16,a2
    bra 2b
6:  inc d2
    cmp 12,d2
    bne 1b
    add 8,sp
    movm (sp),[d2,d3,a2,a3]
    rets

PMREMAP:                         # GUI task, after a Load: the Picture Mode settings follow the entries' stored values
    movm [d2,d3,a2,a3],(sp)
    add -28,sp                   # (8) setting list, (12) id, (16) value, (20) map, (24) left
    mov PMSET,a0
    mov a0,(8,sp)
1:  mov (8,sp),a0
    movhu (a0),d0
    cmp 0,d0
    beq 9f
    add 2,a0
    mov a0,(8,sp)
    mov d0,(12,sp)
    call 0x7e67f822,[],4         # Get_CameraInfo(id) -> d0
    mov d0,(16,sp)
    mov PMMAP,a0
    mov a0,(20,sp)
    mov 5,d0
    mov d0,(24,sp)
2:  mov (20,sp),a0
    mov (4,a0),a1
    movbu (a1),d1                # the entry's stored value now (its byte in the value list)
    mov (16,sp),d0
    movbu (a0),d2                # stock
    movbu (1,a0),d3              # hidden
    cmp d2,d0
    bne 3f
    cmp d3,d1
    bne 5f
    mov d3,d1                    # the stock value, and the entry has a film: the hidden value
    bra 4f
3:  cmp d3,d0
    bne 5f
    cmp d2,d1
    bne 5f
    mov d2,d1                    # the hidden value, and the entry has no film: the stock value
4:  mov (12,sp),d0
    call 0x7e67f882,[d2,d3],12   # Set_CameraInfo(id, value)
    bra 1b
5:  mov (20,sp),a0
    add 8,a0
    mov a0,(20,sp)
    mov (24,sp),d0
    add -1,d0
    mov d0,(24,sp)
    bne 2b
    bra 1b
9:  add 28,sp
    movm (sp),[d2,d3,a2,a3]
    rets
"""

FILMNAME_ASM = r"""
.section .ap,"ax"
GUIEXTRA:                        # T_GUI, while the task does not run
    add -8,sp                    # (0,sp): the return slot of the calls below; T_GUI's return address at (8,sp)
    movbu (REMAP),d0
    cmp 0,d0
    beq 1f
    clr d0
    movbu d0,(REMAP)
    calls PMREMAP
1:  calls FILMNAME
    add 8,sp
    rets

FILMNAME:                        # T_GUI (task CA_MAIN): ImageDescription = the selected entry's film name, else stock
    movm [d2,d3,a2,a3],(sp)
    add -12,sp
    mov 0x9481,d0                # the stored Picture Mode
    mov 0,a0
    clr d1
    call 0x7e457c75,[d2,d3],12   # prm_get(tag, 0, 0) -> d0
FN_PM:
    add -100,d0
    cmp 19,d0
    bcc 8f                       # not 100..118: no film
    mov FNSLOT,a0
    movbu (d0,a0),d2             # the entry's slot, 0xff: no film
    cmp 0xff,d2
    beq 8f
    movbu (STOREOK),d0
    cmp 0,d0
    beq 8f
    mov STORE,a2                 # the stored file's record of that slot
    movbu (5,a2),d3
    add 32,a2
1:  cmp 0,d3
    beq 8f
    movbu (a2),d0
    cmp d2,d0
    beq 2f
    add 1708,a2
    add -1,d3
    bra 1b
2:  movbu (4,a2),d0
    cmp 0,d0
    beq 8f                       # a film without a name: Olympus's text, as the menu keeps the entry's name
    mov FNBUF,a0                 # 31 spaces and a NUL, then the name (16 B, NUL-padded) over the first 16
    mov FNNUL,a1
    mov 32,d0
    mov 1,d1
    call 0x7e70b0f6,[d2,d3,a2,a3],20
    mov a2,a1
    add 4,a1
    mov FNBUF,a0
    mov 16,d0
    clr d1
    call 0x7e70b0f6,[d2,d3,a2,a3],20
    bra 9f
8:  mov FNBUF,a0                 # Olympus's text, as the boot writes it
    mov %(stock)#x,a1
    mov 32,d0
    mov 1,d1
    call 0x7e70b0f6,[d2,d3,a2,a3],20
9:  mov FNBUF,a0                 # into the template as 8 words (a reader never sees a half-written word),
    mov %(desc)#x,a1             # cached and uncached
    mov 8,d1
3:  mov (a0),d0
    mov d0,(a1)
    mov d0,(0x40000000,a1)
    add 4,a0
    add 4,a1
    add -1,d1
    bne 3b
    add 12,sp
    movm (sp),[d2,d3,a2,a3]
    rets
FNSLOT: .byte %(slots)s
FNNUL:  .byte 0
    .balign 4
FNBUF:  .space 32
"""

# APPLY: the destination is relative to the entry's RAM block
APPLY_REPLACE = [
    ("""APPLY:                           # a0 = a valid look file: each record's operations
    movm [d2,d3,a2,a3],(sp)
    add -16,sp""", """APPLY:                           # a0 = a valid look file: each record's operations, into the entry's block
    movm [d2,d3,a2,a3],(sp)
    add -20,sp                   # (16,sp) the entry's RAM block"""),
    ("""    movbu (a3),d0
    asl2 d0
    mov SLOTTAB,a2
    mov (d0,a2),a2
    add 4,a2
""", """    movbu (a3),d0
    asl2 d0
    mov BLOCKS,a2
    mov (d0,a2),d1
    mov d1,(16,sp)
    mov SLOTTAB,a2
    mov (d0,a2),a2
    add 4,a2
"""),
    ("""    mov (4,a2),a1
    mov (8,a2),d1
""", """    mov (4,a2),a1
    mov (16,sp),d1
    add d1,a1
    mov (8,a2),d1
"""),
    ("""9:  add 16,sp
    movm (sp),[d2,d3,a2,a3]
    rets

.section .aq""", """9:  add 20,sp
    movm (sp),[d2,d3,a2,a3]
    rets

.section .aq"""),
]


def cut(text, start, end):
    """Remove text[start label : end label)."""
    i, j = text.index(start), text.index(end)
    assert i < j and text.count(start) == 1 and text.count(end) == 1, (start, end)
    return text[:i] + text[j:]


def stock_block_file():
    """A file with block 0 of Olympus's firmware, for objdump (a temporary file made from the stock firmware)."""
    import tempfile
    stock = os.path.join(ROOT, "firmware", "stock", "E-PM2", "OLY_E_101_1600_0000_0000.BIN")
    f = tempfile.NamedTemporaryFile(suffix=".block0.bin", delete=False)
    f.write(bytes(parse(open(stock, "rb").read()).blocks[0].payload))
    f.close()
    return f.name


def main():
    work = sys.argv[1]
    listing = sys.argv[2] if len(sys.argv) > 2 else None
    os.makedirs(work, exist_ok=True)
    layout = json.load(open(os.path.join(ROOT, "build", OUT, "layout.json")))
    stock_blk = parse(open(os.path.join(ROOT, STOCK), "rb").read()).blocks[0].payload
    get = lambda a, n: stock_blk[a - BASE:a - BASE + n]

    # ---- looks-menu-4: Off / Load
    old = json.load(open(os.path.join(ROOT, "data", "specs", "looks-menu-3.json")))
    mops = []
    for o in old["ops"]:
        a = o.get("_addr")
        if a == "0x7F00BFEE" or "1503" in o["_note"]:
            continue                                  # the list stays two items; no "Built-in" text
        n = dict(o)
        if a == "0x7EE46D88":
            n["new"], n["expect"] = o["new"][:2 * 56], o["expect"][:2 * 56]
            n["_note"] = "the two items of panel 610: Off (value 1, the value the firmware gives setting 449 at every " \
                         "start) and Load (value 0, text 1496)"
        if a == "0x7EE46D28":
            items = bytes.fromhex(o["new"])
            new = items[:48] + items[72:96]
            n["new"], n["expect"] = new.hex(), o["expect"][:2 * len(new)]
            n["_note"] = "value -> text list of the row: 1 the status text 1495, 0 Load, end mark -15"
        mops.append(n)
    sha = hashlib.sha256(open(os.path.join(ROOT, STOCK), "rb").read()).hexdigest()
    json.dump({"name": MENU, "description": "The list, texts and status of the menu row 'Load Looks' (Custom Menu J, "
               "added by data/specs/custom-menu-rows-2.json): Off / Load. As data/specs/looks-menu-3.json without Built-in. "
               "Its value is the dormant setting 449 (prm tag 0xD7B1); Off is 1, Load 0. When Off the row shows text "
               "1495, which the loader points at the result of the last load.",
               "base": STOCK, "base_sha256": sha, "ops": mops},
              open(os.path.join(ROOT, "data", "specs", MENU + ".json"), "w"), indent=1)
    open(os.path.join(ROOT, "data", "specs", MENU + ".json"), "a").write("\n")

    # ---- the operation list (relative to a block) and the tables
    off = layout["offsets"]
    defaults = [struct.unpack("<I", get(slots.DEFAULT_RECORD + 4 * i, 4))[0] for i in range(slots.RECORD_TABLES)]
    ops = [(20, 2, off["sat"], 0), (20, 2, off["sat"] + 2, 0), (22, 12, off["six_s"], 0), (34, 12, off["six_h"], 0),
           (46, 18, off["matrix"], 0), (64, 97, off["chroma"], 0)]
    for ch in range(3):
        src = 164 + ch * lookfile.CURVE_BYTES
        ops += [(src, 256, off["tone"] + 512 * (8 * ch + i), defaults[i]) for i in range(8)]
    oplist = struct.pack("<I", lookfile.KIND_COLOUR) + b"".join(struct.pack("<HHII", *x) for x in ops) + bytes(4)
    blocks = [layout["film_ram"] + layout["block"] * i for i in range(12)]
    ids = m3.name_ids()

    areas = [bytearray() for _ in DATA]

    def place(blob, align=4, area=None):
        for k in ([area] if area is not None else range(len(DATA))):
            pad = -(DATA[k][0] + len(areas[k])) % align
            if DATA[k][0] + len(areas[k]) + pad + len(blob) <= DATA[k][1]:
                areas[k] += bytes(pad)
                at = DATA[k][0] + len(areas[k])
                areas[k] += blob
                return at
        raise SystemExit("data does not fit: %d B" % len(blob))

    slottab = place(bytes(48), area=0)
    crct = place(struct.pack("<16I", *mk.crc_table()), area=0)
    opl = place(oplist, area=0)
    areas[0][0:48] = struct.pack("<12I", *([opl] * 12))
    blocks_at = place(struct.pack("<12I", *blocks))
    lists = []
    for e in layout["entries"]:
        blob = struct.pack("<I", len(e["switch"]))
        for w in e["switch"]:
            film, stock = bytes.fromhex(w["film"]), bytes.fromhex(w["stock"])
            assert len(film) == len(stock) in (1, 4)
            blob += struct.pack("<IB3x", w["address"], len(film)) + film.ljust(4, b"\0") + stock.ljust(4, b"\0")
        lists.append(place(blob))
    swtab = place(struct.pack("<12I", *lists))
    nameids = place(b"".join(struct.pack("<3H", *(ids[s] + [0] * (3 - len(ids[s])))) for s in range(12)))
    strings = {}
    for key, text in (("label", "Load Looks"), ("load", "Load"),
                      ("help", "Load film looks from\r\nEPM2LOOK.BIN on the card."), ("loaded", "Loaded"),
                      ("nofile", "No file"), ("bad", "Bad file"), ("work", "Loading"), ("builtin", "")):
        strings[key] = place(m3.u16s(text))
    txttab = place(b"".join(struct.pack("<HHI", tid, 0, strings[k]) for tid, k in
                            ((m3.T_LABEL, "label"), (m3.T_LOAD, "load"), (m3.T_HELP, "help"))))
    pmset = place(struct.pack("<%dH" % (len(PMSETTINGS) + 1), *PMSETTINGS, 0))
    pm = b""
    for e in [e for e in layout["entries"] if e["kind"] == "hidden"]:
        x = [x for x in slots.EXTRA_SLOTS if x.entry == e["name"]][0]
        pm += struct.pack("<BBHI", e["stock_value"], e["value"], 0, slots.VALUE_LISTS[0] + slots.VALUE_LIST_STEP * x.place)
    pmmap = place(pm)

    # ---- the assembly
    head = m3.ASM_HEAD
    for a, b in HEAD_REPLACE:
        assert head.count(a) == 1, a[:60]
        head = head.replace(a, b)
    head = cut(head, "\nCOPYALL:", "\nNAMES:")
    head = cut(head, "\nLIVE:", "\n.section .tb")
    tail = m3.tail_asm().replace('.section .ap,"ax"', '.section .ap,"ax"')
    for a, b in APPLY_REPLACE:
        assert tail.count(a) == 1, a[:60]
        tail = tail.replace(a, b)
    hook = mk.HOOK
    subs = {"store": mk.STORE, "scratch": mk.SCRATCH, "maxread": mk.MAXREAD, "slottab": slottab, "crct": crct,
            "nameids": nameids, "swtab": swtab, "blocks": blocks_at, "pmset": pmset, "pmmap": pmmap, "txttab": txttab,
            "txt_label": strings["label"], "s_loaded": strings["loaded"], "s_nofile": strings["nofile"],
            "s_bad": strings["bad"], "s_builtin": strings["builtin"], "s_work": strings["work"], "lang": m3.LANG,
            "lang_neg": (-m3.LANG) & 0xFFFFFFFF, "lang_span": m3.LANG_SPAN, "label_off": 4 * m3.T_LABEL,
            "off_off": 4 * m3.T_OFF, "status_off": 4 * m3.T_STATUS, "ram": m3.RAM, "rw0": mk.REFRESH_WORDS[0],
            "rw1": mk.REFRESH_WORDS[1], "rb0": mk.REFRESH_BYTES[0], "rb1": mk.REFRESH_BYTES[1],
            "displaced": mk.displaced(stock_block_file(), hook[0], hook[1]),
            "back": hook[0] + hook[1]}
    asm = head % subs + tail % subs + NEW_ASM
        # T_GUI calls GUIEXTRA in place of its remap block; FLAGS and T_END stay where card-looks-5 has them
        # (log-menu-2 hooks T_END and repeats its `movbu d0,(BUSY)`)
    for a, b in (("""    movbu (REMAP),d0
    cmp 0,d0
    beq 4f
    clr d0
    movbu d0,(REMAP)
    calls PMREMAP
4:  movbu (APPLIED),d0
""", """    calls GUIEXTRA               # the Picture Mode remap after a Load, then the film's name
    movbu (APPLIED),d0
"""), ("    .balign 4\nFLAGS: ", "    .org %d\nFLAGS: " % (FLAGS_V1 - RUNS[".tk"][0]))):
        assert asm.count(a) == 1, a
        asm = asm.replace(a, b)
    # stored Picture Mode - 100 -> the entry's slot while the value means "this entry with its film", else 0xff
    # (the stock value of a hidden-value entry means the entry has no film)
    slot_of = [0xFF] * 19
    for k, e in enumerate(layout["entries"]):
        slot_of[e["value"] - 100] = k
    asm += FILMNAME_ASM % {"desc": EXIF_DESC, "stock": EXIF_DESC_STOCK,
                           "slots": ", ".join("%#x" % v for v in slot_of)}
    RUNS[".x2"] = RUNS[".ap"]
    asm = asm.replace('.section .x1,"ax"', '.section .ap,"ax"').replace('.section .x2,"ax"', '.section .ap,"ax"')
    del RUNS[".x2"]
    args = ["--defsym=s_%s=0x%s" % (x, x) for x in sorted(set(re.findall(r"(?:jmp|call)\s+0x([0-9a-f]{8})", asm)))]
    asm = re.sub(r"((?:jmp|call)\s+)0x([0-9a-f]{8})", r"\1s_\2", asm)
    asm += '\n.section .hs,"ax"\n    jmp T_GUI\n'
    args += ["--section-start=.hs=%#x" % hook[0]] + ["--section-start=%s=%#x" % (k, a) for k, (a, _) in RUNS.items()]
    s, o, e, sb = (os.path.join(work, "loader." + x) for x in ("s", "o", "elf", "bin"))
    open(s, "w").write(asm)
    mk.run(BIN + "/mn10300-elf-as", "-o", o, s)
    mk.run(BIN + "/mn10300-elf-ld", *args, "-e", "%#x" % RUNS[".ap"][0], "-o", e, o)
    syms = {m.group(2): int(m.group(1), 16) for m in
            re.finditer(r"^([0-9a-f]{8}) \w\s+\S+\s+\S+\s+(\w+)$", mk.run(BIN + "/mn10300-elf-objdump", "-t", e), re.M)}

    def sect(name):
        mk.run(BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", name, e, sb)
        return open(sb, "rb").read()

    assert (syms["FLAGS"], syms["T_END"]) == (FLAGS_V1, T_END_V1), (hex(syms["FLAGS"]), hex(syms["T_END"]))
    out = []

    def op(addr, new, note):
        expect = bytes(get(addr, len(new)))
        assert expect != new, note
        out.append({"type": "bytes", "block": 0, "offset": "0x%X" % (addr - BASE), "expect": expect.hex(),
                    "new": new.hex(), "_addr": "0x%08X" % addr, "_note": note})

    for name, (lo, hi) in RUNS.items():
        code = sect(name)
        if not code:
            continue
        assert lo + len(code) <= hi, "%s: %d B do not fit %d B" % (name, len(code), hi - lo)
        if code[-1] == get(lo + len(code) - 1, 1)[0]:
            code += b"\xcb"
        op(lo, code, "new code, %s (%d B)" % ("segment 3, reclaimed code area" if lo >= 0x7EE00000 else "segment 2",
                                             len(code)))
        print("%s: %4d B at %#x, %4d B free after" % (name, len(code), lo, hi - lo - len(code)))
    for k, blob in enumerate(areas):
        if blob:
            op(DATA[k][0], bytes(blob), "data (%d B): the loader's slot table, CRC table, operation list, RAM blocks, "
               "switch lists, name ids, texts, Picture Mode settings" % len(blob))
            print("data %d: %4d B at %#x" % (k, len(blob), DATA[k][0]))
    h = sect(".hs")
    assert len(h) == hook[1] and h[0] == 0xDC and get(hook[0], 5) == hook[2]
    op(hook[0], h, "hook: jmp T_GUI. GUI state setter 0x7ECDF5E9, its last trace call (task CA_MAIN)")
    op(mk.TASK_ENTRY, struct.pack("<I", syms["T_TASK"]),
       "CPU0 task table, row of id 0x90 (USRTEST_A, dormant in stock): entry 0x7E501C5B -> T_TASK")
    op(mk.TASK_ENTRY + 4, b"\x0d", "CPU0 task table, row of id 0x90 (USRTEST_A): priority 11 -> 13")
    keep = {k: syms[k] for k in ("T_TASK", "T_GUI", "T_STORED", "T_END", "SAVE", "V_OK", "V_BAD", "APPLY", "FLAGS",
                                 "NAMES", "MASK", "SWITCH", "PMREMAP", "FILMNAME", "FN_PM")}
    json.dump({**keep, "STORE": mk.STORE, "SCRATCH": mk.SCRATCH, "RAM": m3.RAM, "IDS": ids, "STRINGS": strings,
               "BLOCKS": blocks}, open(os.path.join(ROOT, "build", OUT, "syms.json"), "w"))
    json.dump({"name": SPEC, "description": (
        "Film looks loaded from the SD card onto the stock art filters (experiments/2026-11-18-stock-filters/"
        "design.md), with the menu row Load Looks (data/specs/looks-menu-4.json: Off / Load). Load reads C:\\\\EPM2LOOK.BIN, "
        "checks it as card-looks-4 does, keeps it in the EEROM bank's unused tail (store 0x%08X) and applies it: each "
        "listed entry's tables go into its RAM block (data/specs/stock-films-structure.json), then each entry's switch "
        "list is written, its film words when the file lists it and its stock words otherwise; the Picture Mode "
        "settings 111, 509, 510 follow the stored values of the entries with a hidden value. Every start applies the "
        "stored file. The hook on the GUI state setter's trace call 0x7ECDF6E4, the task USRTEST_A. Every expect is a "
        "stock byte." % mk.STORE + (" Version 6 (experiments/2026-11-20-film-name-exif/NOTES.md): the switch lists of "
        "data/specs/stock-films-structure-2.json; at each GUI state T_GUI calls FILMNAME, which writes the EXIF "
        "template's ImageDescription (0x%08X): the film's name when the stored Picture Mode is an entry with a film, "
        "else Olympus's text." % EXIF_DESC) + (" Version 7 (experiments/2026-11-20-model-calibration/"
        "NOTES.md §6): the switch lists of data/specs/stock-films-structure-3.json, where an in-place entry with a film "
        "also gets no 12-region table.")),
        "base": STOCK, "base_sha256": sha,
        "_ram": "the EEROM bank's unused tail: store 0x%08X, scratch 0x%08X; RAM: status, names 0x%08X-0x%08X; the "
                "entries' blocks 0x%08X-0x%08X; 5 flag bytes in the code" % (mk.STORE, mk.SCRATCH, m3.RAM, m3.RAM + 0x800,
                                                                         blocks[0], blocks[-1] + layout["block"]),
        "ops": out}, open(os.path.join(ROOT, "data", "specs", SPEC + ".json"), "w"), indent=1)
    open(os.path.join(ROOT, "data", "specs", SPEC + ".json"), "a").write("\n")
    print("wrote data/specs/%s.json (%d ops), data/specs/%s.json; T_GUI %#x, T_TASK %#x, T_END %#x" % (
        SPEC, len(out), MENU, syms["T_GUI"], syms["T_TASK"], syms["T_END"]))
    if listing:
        open(listing, "w").write(mk.run(BIN + "/mn10300-elf-objdump", "-d", *sum((["-j", k] for k in RUNS), []),
                                        "-j", ".hs", e))


if __name__ == "__main__":
    main()
