"""Write patches/build-label.json: the Firmware screen shows "Body : 1.6  EPM2Mod <label>". Research code.

    uv run python gen/build-label/mkspec.py [LABEL] [OUT.json]

LABEL defaults to "EPM2Mod 0000.00.00": the placeholder that epm2mod make replaces with the build's label
(src/epm2mod/label.py). The version number stays 1.6: block 0's header and prm tag 0xC082 are not touched. Byte
edits, no new code (NOTES.md sections 3 and 6):
  1. the Firmware panel's (panel 99) object grows from 936 to 928 + 2 * TEXT_CHARS bytes: its last field, at +928, is
     the value text that the panel formats (4 UTF-16 characters in stock, exactly "1.6" and its end);
  2. the Body line formats with a new UTF-16 text "%X.%X  <label>" instead of the shared L"%X.%X" 0x7EF93DD4;
     the Lens, Flash and Acc lines keep the stock text;
  3. the four value boxes (Body, Lens, Flash, Acc) start at one x and are 335 pixels wide (a box clips its text);
  4. the four value widgets are left-aligned (descriptor field +36: 0x101 centred -> 0x100 left, as the labels);
  5. that text, in the Bluetooth debug strings of segment 2 (reclaim-space row 2, docs/space-candidates.tsv), after
     the part that patches/lss-menu.json uses.
"""

import hashlib
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from epm2mod.container import parse  # noqa: E402

STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
BASE = 0x7E421020                       # block 0 run-time base
ALLOC = 0x7ED1936E                      # CreatePanel case of panel 99: mov 936,d0 ; call new ; call ctor 0x7ED788C0
FMT_BODY = 0x7ED78BD4                   # panel 99 draw 0x7ED78B23, line 0 (Body): mov 0x7EF93DD4,d0 ; mov d0,(4,sp)
STOCK_FMT = 0x7EF93DD4                  # L"%X.%X", used by the four lines (4 references, all in 0x7ED78B23)
TEXT = 0x7EBB2FEC                       # reclaim-space row 2 is 0x7EBB1F4C-0x7EBB304C; lss-menu ends at 0x7EBB2AC4
TEXT_CHARS = 48                         # room in the text area and in the value buffer, the end mark included
RECTS = 0x7EF93804                      # panel 99 widget rectangles: 14 widgets x 2 copies x {s16 x, y, w, h}, in
                                        # 640-wide coordinates (screen x = x + 40); widget 10 = the Body value
VALUES = RECTS + 8 * 2 * 10             # 0x7EF938A4: widgets 10-13 (values), (369, y, 100, 32) twice each
LINES_Y = (170, 206, 242, 278)
VALUE_X, VALUE_W = 337, 335             # 8 pixels right of the colon (311 + 18) to 8 pixels before the screen edge
DESC = 0x7EF93914                       # panel 99 widget descriptors, 92 bytes each from widget 1 (title)
ALIGN = 36                              # descriptor field: 0x100 left (the labels), 0x101 centred (title, colons, values)
LABEL_RE = re.compile(r"[A-Za-z0-9 .\-]{1,31}")


def label_ops(block0: bytes, label: str) -> list[dict]:
    """The byte edits for LABEL, checked against the stock bytes of block 0."""
    if not LABEL_RE.fullmatch(label):
        raise SystemExit(f"label {label!r}: 1 to 31 characters of A-Z a-z 0-9 space . -")
    text = ("%X.%X  " + label + "\0").encode("utf-16-le")
    assert len(text) <= 2 * TEXT_CHARS and TEXT + 2 * TEXT_CHARS <= 0x7EBB304C
    padded = text.ljust(2 * TEXT_CHARS, b"\0")

    def op(addr: int, expect: bytes, new: bytes, note: str) -> dict:
        off = addr - BASE
        assert block0[off:off + len(expect)] == expect, (hex(addr), block0[off:off + len(expect)].hex())
        return {"type": "bytes", "block": 0, "offset": "0x%X" % off, "expect": expect.hex(), "new": new.hex(),
                "_addr": "0x%08X" % addr, "_note": note}

    size = 928 + 2 * TEXT_CHARS
    return [
        op(ALLOC, bytes.fromhex("2ca803"), b"\x2c" + struct.pack("<H", size),
           "panel 99 (Firmware screen) object: 936 -> %d bytes; its last field (+928) is the value text, which "
           "grows from 4 to %d UTF-16 characters" % (size, TEXT_CHARS)),
        op(FMT_BODY + 2, struct.pack("<I", STOCK_FMT), struct.pack("<I", TEXT),
           "panel 99, line 0 (Body): the format text 0x%08X instead of the shared L\"%%X.%%X\"" % TEXT),
        op(VALUES, b"".join(struct.pack("<4h", 369, y, 100, 32) * 2 for y in LINES_Y),
           b"".join(struct.pack("<4h", VALUE_X, y, VALUE_W, 32) * 2 for y in LINES_Y),
           "panel 99, widgets 10-13 (the Body, Lens, Flash and Acc values), both copies of each rectangle: x 369 w 100 "
           "-> x %d w %d (640-wide coordinates, screen x = x + 40); a box clips its text" % (VALUE_X, VALUE_W)),
        *[op(DESC + 92 * (w - 1) + ALIGN, struct.pack("<I", 0x101), struct.pack("<I", 0x100),
             "panel 99, widget %d (the %s value): alignment 0x101 (centred) -> 0x100 (left, as the labels), so that "
             "the four values start at one x" % (w, name))
          for w, name in zip(range(10, 14), ("Body", "Lens", "Flash", "Acc"))],
        op(TEXT, block0[TEXT - BASE:TEXT - BASE + len(padded)], padded,
           "the Body line's format text L\"%%X.%%X  %s\" in unreferenced Bluetooth debug strings (reclaim-space "
           "row 2); epm2mod make writes the build's label in place of 0000.00.00" % label.replace("0000.00.00", "YYYY.MM.DD")),
    ]


def main() -> None:
    label = sys.argv[1] if len(sys.argv) > 1 else "EPM2Mod 0000.00.00"
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "patches", "build-label.json")
    data = open(os.path.join(ROOT, STOCK), "rb").read()
    block0 = parse(data).blocks[0].payload
    spec = {
        "name": os.path.splitext(os.path.basename(out))[0],
        "description": ("Build label: the Firmware screen (Setup Menu, Firmware) shows 'Body : 1.6  EPM2Mod YYYY.MM.DD', "
                        "the 'label' of the build description; epm2mod make writes it over the placeholder 0000.00.00 "
                        "(src/epm2mod/label.py). The version number is not changed (block 0 header +16 = 0x1600, prm "
                        "tag 0xC082). Byte edits, no new code: the panel's object grows so that its value text holds "
                        "%d characters; the Body line formats with its own text, in unreferenced debug strings of "
                        "segment 2; the four value texts (Body, Lens, Flash, Acc) are left-aligned in wider boxes that "
                        "start at one x, so they line up as in stock. See experiments/2026-11-19-build-label/NOTES.md."
                        % TEXT_CHARS),
        "base": STOCK,
        "base_sha256": hashlib.sha256(data).hexdigest(),
        "status": "candidate: emulator-checked, not flashed",
        "ops": label_ops(bytes(block0), label),
    }
    with open(out, "w") as f:
        json.dump(spec, f, indent=1)
        f.write("\n")
    print("wrote", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
