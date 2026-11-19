"""Write data/specs/gauge-info.json: the Level Gauge screen keeps the shooting information of the histogram screen.

    uv run python experiments/2026-11-19-gauge-info/scripts/mkspec_gauge_info.py

The rec-view producers (0x7ED99847 runs 77 of them) fill the data that the live-view panel shows. Each one runs only
when the current layout (viewer +764) is in its list of layouts. The layout selector 0x7ED99ABF gives the histogram
screen layout 8 and the Level Gauge screen layout 22. This spec gives each list that holds 8 and not 22 a copy with 22
added, in free space, and points its code at the copy: the address in its `mov imm32,aN` and the length in its `cmp` or
`mov` byte. The histogram's own list {8, 9} and the gauge's lists {1, 22, 23} do not change. Data edits only, no code.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "cli" / "src"))
from epm2mod import container  # noqa: E402

BASE = 0x7E421020
STOCK = ROOT / "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
OUT = ROOT / "data/specs/gauge-info.json"
HIST, GAUGE = 8, 22
#: Free data space for the new lists: segment 3 (loaded with the lists' readers), tools/freespace.py USABLE-DATA.
AREA = (0x7EE46DC0, 0x7EE4709D)

#: (list address, pc of `mov imm32,aN` that loads it, pc of the length byte's instruction, length, producer it gates)
SITES = [
    (0x7EFCEC64, 0x7ED9A154, 0x7ED9A164, 10, "0x7ED9E737"),
    (0x7EFCEFBC, 0x7ED9A4A5, 0x7ED9A4BB, 5, "producer 0x7ED9A474"),
    (0x7EFCEFF8, 0x7ED9A524, 0x7ED9A544, 7, "producer 0x7ED9A4EA"),
    (0x7EFCF06C, 0x7ED9A642, 0x7ED9A648, 8, "ISO, ISO-A (0x7ED9A574, +204 = 1)"),
    (0x7EFCF050, 0x7ED9A64C, 0x7ED9A652, 7, "ISO, ISO-A (0x7ED9A574)"),
    (0x7EFCF2E0, 0x7ED9A969, 0x7ED9A96F, 7, "slot 37 +22 (0x7ED9A887)"),
    (0x7EFCF6C0, 0x7ED9D050, 0x7ED9D060, 4, "0x7ED9CFAE (viewer +772), first list"),
    (0x7EFCF6D0, 0x7ED9D071, 0x7ED9D081, 3, "0x7ED9CFAE (viewer +772), second list"),
    (0x7EFCF6DC, 0x7ED9AEF0, 0x7ED9AF02, 8, "producer 0x7ED9AD90"),
    (0x7EFCF9C8, 0x7ED9B4A4, 0x7ED9B4B4, 6, "movie time and frame count (0x7ED9EA46)"),
    (0x7EFCF9E0, 0x7ED9B4E8, 0x7ED9B4F6, 8, "0x7ED9EA82 (gate 0x7ED9B4C4)"),
]


def main() -> None:
    img = container.parse(STOCK.read_bytes()).blocks[0].payload
    at = lambda a, n: img[a - BASE : a - BASE + n]  # noqa: E731
    word = lambda a: int.from_bytes(at(a, 4), "little")  # noqa: E731
    ops, free = [], AREA[0]
    for lst, mov, cnt, n, what in SITES:
        values = [word(lst + 4 * i) for i in range(n)]
        assert HIST in values and GAUGE not in values, (hex(lst), values)
        # the mov imm32,aN: fc dc (a0) or fc dd (a1), then the list address
        code = at(mov, 6)
        assert code[:2] in (b"\xfc\xdc", b"\xfc\xdd") and int.from_bytes(code[2:], "little") == lst, (hex(mov), code.hex())
        # the length: `cmp imm8,dN` (a4-a7, af) or `mov imm8,dN` (80-8f) with the length as its byte
        length = at(cnt, 2)
        assert length[1] == n and (length[0] & 0xF0 in (0x80, 0xA0)), (hex(cnt), length.hex())
        new = b"".join(v.to_bytes(4, "little") for v in values + [GAUGE])
        assert free + len(new) <= AREA[1]
        ops.append(op(free, at(free, len(new)), new, f"layouts of {what}: {values} and {GAUGE}"))
        ops.append(op(mov + 2, code[2:], free.to_bytes(4, "little"), f"{what}: the list at {free:#x}"))
        ops.append(op(cnt + 1, bytes([n]), bytes([n + 1]), f"{what}: {n + 1} layouts"))
        free += len(new)
    stock_sha = __import__("hashlib").sha256(STOCK.read_bytes()).hexdigest()
    spec = {
        "name": "gauge-info",
        "description": "Level Gauge screen with the shooting information: the producers of the information that the "
        "histogram screen shows (layout 8) also run on the Level Gauge screen (layout 22), so ISO, S-IS, the movie time, "
        "the frame count and the touch icon stay on the gauge screen. Eleven layout lists get a copy with 22 added in free "
        "data space (segment 3); their code points at the copy. See experiments/2026-11-19-gauge-info/NOTES.md.",
        "base": "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN",
        "base_sha256": stock_sha,
        "status": "candidate: emulator-checked, not flashed",
        "ops": ops,
    }
    OUT.write_text(json.dumps(spec, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(ops)} ops, lists {AREA[0]:#x}-{free:#x} ({free - AREA[0]} bytes)")


def op(addr: int, expect: bytes, new: bytes, note: str) -> dict[str, str]:
    return {
        "type": "bytes",
        "block": 0,
        "offset": f"{addr - BASE:#X}".replace("0X", "0x"),
        "expect": expect.hex(),
        "new": new.hex(),
        "_addr": f"{addr:#X}".replace("0X", "0x"),
        "_note": note,
    }


if __name__ == "__main__":
    main()
