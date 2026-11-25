"""Write data/specs/looks-menu-4.json and data/specs/card-looks-9.json: the loader of film simulations for the
stock-filters firmware (experiments/2026-11-18-stock-filters/design.md). Needs build/stock-films/layout.json
(gen/stock-films/structure.py).

    uv run python gen/stock-films/loader.py WORKDIR [LISTING.txt]

The assembly is loader.s; this file places the tables, fills the fields of loader.s, assembles and links it, and
writes the two specs. What the code does:
  * C_START, the last entry of segment 3's constructor table (task Usr1, after the segment copies): applies the
    stored file (STORED), then runs the entry's own constructor;
  * T_GUI, at the GUI state setter's trace call: starts the task USRTEST_A for a Load, and after a Load maps the
    Picture Mode settings (PMREMAP) and writes the film's name into the EXIF template (FILMNAME);
  * the task: reads C:\\EPM2LOOK.BIN, checks it (VERIFY), keeps it in the EEROM bank's unused tail, writes each listed
    entry's tables into the entry's RAM block (APPLY) and each entry's switch list (SWITCH): the film bytes when the
    file lists the entry, else the stock bytes. At the first GUI state of a session it writes the texts and names,
    and applies the stored file only if C_START found none;
  * the menu texts: a loaded entry shows its film's name; the row shows Loaded, No file or Bad file. The texts of the
    rows Peaking, Lowest S/S Setting and Spot Metering are written the same way (TEXTS), so they show in every menu
    language.
The spec's key `_symbols` holds the labels that gen/log-menu/mkspec.py hooks.
A camera-tested version stays as its committed spec file (a build names it); this file makes only the current one.
"""

import hashlib
import json
import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "cli", "src"))
from epm2mod.container import parse  # noqa: E402
from epm2mod.looks import lookfile, slots  # noqa: E402

SPEC, MENU = "card-looks-9", "looks-menu-4"
OUT = "stock-films"   # build/OUT: layout.json in, syms.json out
CTOR_ENTRY, CTOR = 0x7F033AC8 + 4 * 44, 0x7EEC05FF   # segment 3's constructor table (45 entries; walker 0x7E44B6B0,
# called by Usr1 at 0x7E504D81 with d0 = 3): its last entry. It stores a pointer and 0 in two globals
EXIF_DESC = 0x605BAEC0        # the EXIF template's ImageDescription, 32 B (template 0x605BA918 + 0x5A8)
EXIF_DESC_STOCK = 0x7E8517C2  # "OLYMPUS DIGITAL CAMERA", which the boot copies there with 0x7E70B0F6
BASE = slots.BLOCK0_BASE
sys.path.insert(0, os.path.join(ROOT, "tools"))
import toolchain  # noqa: E402

BIN = toolchain.binutils_dir()
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
# where the code goes: free runs of the segment-2 code areas, and for APPLY (.ap) the reclaimed code area of
# segment 3 (docs/reference/code-space-map.md)
RUNS = {
    ".tk": (0x7ECB0EE8, 0x7ECB1000),
    ".tb": (0x7EBF2890, 0x7EBF2900),          # after the child list of the Custom Menu, which ends at 0x7EBF2890
    ".vf": (0x7EBF2A8C, 0x7EBF2B00),
    ".vc": (0x7EBF2B90, 0x7EBF2C00),
    ".ap": (0x7EE53830, 0x7EE53D6A),
    ".aq": (0x7EBF29C0, 0x7EBF2A00),
    ".ds": (0x7EBF3B10, 0x7EBF3B52),
}
DATA = [(0x7EE40B18, 0x7EE411F6), (0x7F033B7C, 0x7F034000), (0x7EE546C4, 0x7EE548B0)]
PMSETTINGS = (111, 509, 510)                  # info ids that hold a stored Picture Mode value
HOOK = (0x7ECDF6E4, 5, bytes.fromhex("cd4f6cb010"))     # GUI state setter 0x7ECDF5E9, its last trace call
TASK_ENTRY = 0x7E439C80                                   # CPU0 task table, row of id 0x90 (USRTEST_A): the entry word
STORE = 0x603F8000                                        # the stored look file, in the EEROM bank's unused tail
SCRATCH = 0x603FD040                                      # the file read from the card (uncached alias 0xA03FD040)
TAIL = (0x603F74B8, 0x60404668)                           # the unused tail (experiments/2026-11-17-card-looks/design.md)
MAXREAD = lookfile.MAX_FILE_BYTES + 4                     # a longer file is read short and refused
REFRESH_WORDS = (0xA07500B4, 0xA07500B8)                  # the IMG library's builder words: 0 = clear the stage cache
REFRESH_BYTES = (0x60510CD5, 0x60511305)                  # the gamma states' art-code bytes: 0xFF = rebuild
assert TAIL[0] <= STORE and STORE + lookfile.MAX_FILE_BYTES <= SCRATCH and SCRATCH + MAXREAD <= TAIL[1]
LANG = 0xBFF3D000           # the loaded language's blob; its first word: the address of its pointer array
LANG_SPAN = 0x43000
T_LABEL, T_LOAD, T_HELP, T_STATUS, T_OFF = 1498, 1496, 1497, 1495, 1371      # string ids of the row's texts
# Texts of other specs' rows whose ids the specs set in the English blob only (block 1): the loader writes them into
# the loaded language's table with its own. The colour names 1499, 1501, 1502 and Off are the language's own words.
TEXTS = ((1505, "Peaking"),                                                   # peaking-menu: the row's label
         (1506, "Show lines in that color \r\non sharp edges while\r\nMF Assist magnifies."),   # peaking-colours
         (1500, "White"),                                                     # peaking-menu: no stock text is "White"
         (1503, "Lowest S/S Setting"),                                        # lss-menu: label and help
         (1504, "Choose the shutter speed at\r\nwhich the camera raises\r\nISO in P and A."),
         (1494, "Spot Metering"),                                             # spot-menu: label and help (unused
         (1509, "Spot modes set to On meter\r\nat the selected AF target\r\nin single-target AF."))   # EVF texts)
RAM = 0x7E4D0000            # the RAM gap (cached address); the code uses the uncached alias
ENGLISH = (0x38B758, 0xBFBC4E20)   # pointer array of the English blob in block 1, and its load bias


def run(*a):
    return subprocess.run(a, check=True, capture_output=True, text=True).stdout


def crc_table():
    t = []
    for n in range(16):
        c = n
        for _ in range(4):
            c = (c >> 1) ^ (0xEDB88320 if c & 1 else 0)
        t.append(c)
    return t


def displaced(blk_path, site, n):
    """The replaced call at the hook site, by its target."""
    txt = run(BIN + "/mn10300-elf-objdump", "-D", "-b", "binary", "-m", "mn10300", "--adjust-vma=%#x" % BASE,
              "--start-address=%#x" % site, "--stop-address=%#x" % (site + n), blk_path)
    m = re.search(r"call\s+0x([0-9a-f]{8}),(\[[^\]]*\]),(\d+)", txt)
    assert m, txt
    return "    call 0x%s,%s,%s            # the replaced instruction" % m.groups()


def stock_texts():
    """The English texts of block 1 by id (stock firmware), to find the ids that show an entry's name."""
    b1 = parse(open(os.path.join(ROOT, STOCK), "rb").read()).blocks[1].payload
    out = []
    for i in range(1970):
        p = struct.unpack_from("<I", b1, ENGLISH[0] + 4 * i)[0] - ENGLISH[1]
        e = p
        while b1[e:e + 2] != b"\0\0":
            e += 2
        out.append(b1[p:e].decode("utf-16-le"))
    return out


def name_ids():
    """For each menu entry, the ids whose stock English text is the entry's name, with or without an icon tag."""
    texts = stock_texts()
    ids = []
    for entry in lookfile.MENU_ENTRIES:
        found = [i for i, t in enumerate(texts) if re.sub(r"^@[^@]*@", "", t) == entry]
        assert 2 <= len(found) <= 3, (entry, found)
        ids.append(found)
    return ids


def u16s(s):
    return s.encode("utf-16-le") + b"\0\0"


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
    ids = name_ids()

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
    crct = place(struct.pack("<16I", *crc_table()), area=0)
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
        strings[key] = place(u16s(text))
    rows = [(T_LABEL, strings["label"]), (T_LOAD, strings["load"]), (T_HELP, strings["help"])]
    rows += [(tid, place(u16s(text))) for tid, text in TEXTS]
    txttab = place(b"".join(struct.pack("<HHI", tid, 0, at) for tid, at in rows))
    pmset = place(struct.pack("<%dH" % (len(PMSETTINGS) + 1), *PMSETTINGS, 0))
    pm = b""
    for e in [e for e in layout["entries"] if e["kind"] == "hidden"]:
        x = [x for x in slots.EXTRA_SLOTS if x.entry == e["name"]][0]
        pm += struct.pack("<BBHI", e["stock_value"], e["value"], 0, slots.VALUE_LISTS[0] + slots.VALUE_LIST_STEP * x.place)
    pmmap = place(pm)

    # ---- the assembly: loader.s with its fields filled
    # stored Picture Mode - 100 -> the entry's slot while the value means "this entry with its film", else 0xff
    # (the stock value of a hidden-value entry means the entry has no film)
    slot_of = [0xFF] * 19
    for k, e in enumerate(layout["entries"]):
        slot_of[e["value"] - 100] = k
    hook = HOOK
    subs = {"store": STORE, "scratch": SCRATCH, "maxread": MAXREAD, "slottab": slottab, "crct": crct,
            "nameids": nameids, "swtab": swtab, "blocks": blocks_at, "pmset": pmset, "pmmap": pmmap, "txttab": txttab,
            "txtn": len(rows), "ctor": CTOR,
            "txt_label": strings["label"], "s_loaded": strings["loaded"], "s_nofile": strings["nofile"],
            "s_bad": strings["bad"], "s_builtin": strings["builtin"], "s_work": strings["work"], "lang": LANG,
            "lang_neg": (-LANG) & 0xFFFFFFFF, "lang_span": LANG_SPAN, "label_off": 4 * T_LABEL,
            "off_off": 4 * T_OFF, "status_off": 4 * T_STATUS, "ram": RAM, "rw0": REFRESH_WORDS[0],
            "rw1": REFRESH_WORDS[1], "rb0": REFRESH_BYTES[0], "rb1": REFRESH_BYTES[1],
            "displaced": displaced(stock_block_file(), hook[0], hook[1]),
            "back": hook[0] + hook[1],
            "desc": EXIF_DESC, "stock": EXIF_DESC_STOCK, "slots": ", ".join("%#x" % v for v in slot_of)}
    asm = open(os.path.join(HERE, "loader.s")).read() % subs
    args = ["--defsym=s_%s=0x%s" % (x, x) for x in sorted(set(re.findall(r"(?:jmp|call)\s+0x([0-9a-f]{8})", asm)))]
    asm = re.sub(r"((?:jmp|call)\s+)0x([0-9a-f]{8})", r"\1s_\2", asm)
    asm += '\n.section .hs,"ax"\n    jmp T_GUI\n'
    args += ["--section-start=.hs=%#x" % hook[0]] + ["--section-start=%s=%#x" % (k, a) for k, (a, _) in RUNS.items()]
    s, o, e, sb = (os.path.join(work, "loader." + x) for x in ("s", "o", "elf", "bin"))
    open(s, "w").write(asm)
    run(BIN + "/mn10300-elf-as", "-o", o, s)
    run(BIN + "/mn10300-elf-ld", *args, "-e", "%#x" % RUNS[".ap"][0], "-o", e, o)
    syms = {m.group(2): int(m.group(1), 16) for m in
            re.finditer(r"^([0-9a-f]{8}) \w\s+\S+\s+\S+\s+(\w+)$", run(BIN + "/mn10300-elf-objdump", "-t", e), re.M)}

    def sect(name):
        run(BIN + "/mn10300-elf-objcopy", "-O", "binary", "-j", name, e, sb)
        return open(sb, "rb").read()

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
    op(TASK_ENTRY, struct.pack("<I", syms["T_TASK"]),
       "CPU0 task table, row of id 0x90 (USRTEST_A, dormant in stock): entry 0x7E501C5B -> T_TASK")
    op(TASK_ENTRY + 4, b"\x0d", "CPU0 task table, row of id 0x90 (USRTEST_A): priority 11 -> 13")
    assert get(CTOR_ENTRY, 8) == struct.pack("<I", CTOR) + b"\xff" * 4, "not the last entry of the constructor table"
    op(CTOR_ENTRY, struct.pack("<I", syms["C_START"]), "segment 3's constructor table 0x7F033AC8, entry 44 (the last): "
       "0x%08X -> C_START, which applies the stored looks and then jumps to 0x%08X" % (CTOR, CTOR))
    keep = {k: syms[k] for k in ("T_TASK", "T_GUI", "T_STORED", "T_END", "SAVE", "V_OK", "V_BAD", "APPLY", "FLAGS",
                                 "NAMES", "MASK", "SWITCH", "PMREMAP", "FILMNAME", "FN_PM", "C_START", "STORED")}
    hooked = {k: "0x%08X" % syms[k] for k in ("T_GUI", "T_END", "FLAGS", "C_START", "STORED")}
    json.dump({**keep, "STORE": STORE, "SCRATCH": SCRATCH, "RAM": RAM, "IDS": ids, "STRINGS": strings,
               "BLOCKS": blocks, "TXTTAB": [list(r) for r in rows]}, open(os.path.join(ROOT, "build", OUT, "syms.json"), "w"))
    json.dump({"name": SPEC, "description": (
        "Film looks loaded from the SD card onto the stock art filters (experiments/2026-11-18-stock-filters/"
        "design.md), with the menu row Load Looks (data/specs/looks-menu-4.json: Off / Load). Load reads C:\\\\EPM2LOOK.BIN, "
        "checks it as card-looks-4 does, keeps it in the EEROM bank's unused tail (store 0x%08X) and applies it: each "
        "listed entry's tables go into its RAM block (data/specs/stock-films-structure.json), then each entry's switch "
        "list is written, its film words when the file lists it and its stock words otherwise; the Picture Mode "
        "settings 111, 509, 510 follow the stored values of the entries with a hidden value. Every start applies the "
        "stored file. The hook on the GUI state setter's trace call 0x7ECDF6E4, the task USRTEST_A. Every expect is a "
        "stock byte." % STORE + (" Version 6 (experiments/2026-11-20-film-name-exif/NOTES.md): the switch lists of "
        "data/specs/stock-films-structure-2.json; at each GUI state T_GUI calls FILMNAME, which writes the EXIF "
        "template's ImageDescription (0x%08X): the film's name when the stored Picture Mode is an entry with a film, "
        "else Olympus's text." % EXIF_DESC) + (" Version 7 (experiments/2026-11-20-model-calibration/"
        "NOTES.md §6): the switch lists of data/specs/stock-films-structure-3.json, where an in-place entry with a film "
        "also gets no 12-region table.") + (" Version 8 (experiments/2026-11-21-firmware-dive/plan.md): the last entry "
        "of segment 3's constructor table (0x%08X) points at C_START, which applies the stored file in task Usr1 after "
        "the segment copies and then runs the entry's constructor 0x%08X; the task at the first GUI state writes the "
        "texts and names, and applies the stored file only if C_START found none. The text table also holds the "
        "English texts of the rows Peaking (ids 1505, 1506, 1500) and Lowest S/S Setting (1503, 1504), so both rows "
        "show them in every menu language. FLAGS and T_END are no longer at fixed addresses: `_symbols` gives the "
        "labels that data/specs/log-menu-3.json hooks." % (CTOR_ENTRY, CTOR)) + (" Version 9 (experiments/"
        "2026-11-24-af-spot-metering/NOTES.md, build spot-af): the text table also points the ids 1494 and 1509 "
        "(unused built-in EVF texts) at the label and help of the row Spot Metering (data/specs/spot-menu.json) in "
        "the loaded language.")),
        "base": STOCK, "base_sha256": sha,
        "_symbols": hooked,
        "_ram": "the EEROM bank's unused tail: store 0x%08X, scratch 0x%08X; RAM: status, names 0x%08X-0x%08X; the "
                "entries' blocks 0x%08X-0x%08X; 5 flag bytes in the code" % (STORE, SCRATCH, RAM, RAM + 0x800,
                                                                         blocks[0], blocks[-1] + layout["block"]),
        "ops": out}, open(os.path.join(ROOT, "data", "specs", SPEC + ".json"), "w"), indent=1)
    open(os.path.join(ROOT, "data", "specs", SPEC + ".json"), "a").write("\n")
    print("wrote data/specs/%s.json (%d ops), data/specs/%s.json; T_GUI %#x, T_TASK %#x, T_END %#x" % (
        SPEC, len(out), MENU, syms["T_GUI"], syms["T_TASK"], syms["T_END"]))
    if listing:
        open(listing, "w").write(run(BIN + "/mn10300-elf-objdump", "-d", *sum((["-j", k] for k in RUNS), []),
                                        "-j", ".hs", e))


if __name__ == "__main__":
    main()
