"""Write data/specs/raw-edit-art-bkt-3.json: the ART BKT row of RAW Data Edit.

    uv run python gen/raw-edit-art-bkt/mkspec.py [WORKDIR]

RAW Data Edit then lists Current, Custom1, Custom2, ART BKT, No. ART BKT develops the
RAW once per frame of the camera's ART BKT selection, as an ART bracket shot lists the
frames: the current Picture Mode first, then each entry that is On. Each frame is a
stock [Current] edit. Design and emulator runs:
experiments/2026-11-20-raw-edit-art-bkt/NOTES.md section 8. The code is artbkt.s.

A [Current] edit (also each ART BKT frame) records the ImageDescription that a capture
in the current Picture Mode records: the film name that card-looks' FILMNAME writes into
the EXIF template, or Olympus's text. Stock copies the RAW's text.
experiments/2026-11-24-artbkt-production/NOTES.md.

The spec is the last spec of data/builds/artbkt.json; the specs before it are the base.
FILMNAME is found in the base by its first bytes (card-looks-8 moved it once, and a
call to the old address crashed the camera: docs/camera-log/2026-11-21-films-start-
texts-artbkt.md). Every byte this spec changes must be stock in the base.

Ops:
  1. the code and data in the free run 0x7EBB2AC4-0x7EBB2FEC (segment 2);
  2. list 320 (RAW Data Edit): count 4 -> 5 (0x7F00D564), items -> ITEMS;
  3. H1, 0x7EDF7DF3 in the list's OK handler 0x7EDF7DDD: `mov 1744,a0; add a3,a0`
     -> `jmp ROWS`;
  4. H2, 0x7EDF812C in RawEditProcessCallback 0x7EDF7F60 (command 47, status 164, a
     job is done): `mov d2,d0; mov d0,d1; call 0x7EDC712F` -> `jmp CBDONE; nop x 4`;
  5. H3, 0x7E9411AD in play_edit_raw_set_exif_default 0x7E94113F:
     `mov (a2),a2; movbu (16479,a2),d0` -> `jmp FIXDESC; nop`.

Needs the MN103 binutils (uv run epm2mod init) and Olympus's firmware
(uv run epm2mod fetch-stock).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "cli" / "src"))
sys.path.insert(0, str(ROOT / "tools"))
import toolchain  # noqa: E402
from epm2mod import container  # noqa: E402
from epm2mod.spec import apply_specs, load_spec  # noqa: E402

BASE = 0x7E421020
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
BUILD = "data/builds/artbkt.json"
SPEC = "data/specs/raw-edit-art-bkt-3.json"
SOURCE = Path(__file__).resolve().parent / "artbkt.s"
AREA, AREA_END = 0x7EBB2AC4, 0x7EBB2FEC  # free in the ledger (freespace.py area)
H1, H2, H3 = 0x7EDF7DF3, 0x7EDF812C, 0x7E9411AD
COUNT = 0x7F00D564  # list 320: u32 count, then u32 items
STOCK_ITEMS = 0x7F00D368  # Current 1760, Custom1 1761, Custom2 1762, No 496 (12 B each)
#: The stock bytes at each hook: what the hook replaces.
H1_OLD = "24d006f17cf040"  # mov 1744,a0; add a3,a0; movbu (a0),d0
H2_OLD = "8881dd01f0fcff0004"  # mov d2,d0; mov d0,d1; call 0x7EDC712F,[],4
H3_OLD = "f00afa425f40"  # mov (a2),a2; movbu (16479,a2),d0
#: FILMNAME's first instructions: movm [d2,d3,a2,a3],(sp); add -12,sp; mov 0x9481,d0.
FILMNAME_HEAD = bytes.fromhex("cff0f8fef4fccc81940000")

#: The firmware addresses that artbkt.s names (FILMNAME is added from the base).
EXTERNAL = {
    "OK_DISPATCH": 0x7EDF7DFA,  # clr d3; clr d2; the stock dispatch on d0
    "OK_CURRENT": 0x7EDF7E14,  # the [Current] path: startCurrent(0, callback)
    "CB_RESULT": 0x7EDF8135,  # the callback after 0x7EDC712F: cmp 0,a2
    "CB_DONE_UI": 0x7EDC712F,  # the callback's call at a done job (displaced by H2)
    "RAWCB": 0x7EDF7F60,  # RawEditProcessCallback
    "PAGE_KEY": 0x7EDCDABF,  # store the page's transition record
    "PV_ARG0": 0x602BA97C,  # previewCurrent's d0 and a1, as page 611 loads them
    "PV_ARG1": 0x602BA978,
    "API": 0x7E9C34D1,  # OlyApiEditRaw getter -> a0
    "PRM_GET": 0x7E457C75,  # (d0 tag, a0 0, d1 0) -> d0
    "PRM_SET": 0x7E457CED,  # (d0 tag, a0 0, d1 0, a1 value)
    "COMPOSE": 0x7E5A75AE,  # the ART bracket composer after its On/Off gate
    "ALLOC": 0x7E507325,  # scheap large pool: a 16 KB block -> a0, or 0
    "FREE": 0x7E507333,  # a0 = the block
    "H3_BACK": H3 + 6,  # play_edit_raw_set_exif_default after H3
    "DESC": 0xA05BAEC0,  # the EXIF template's ImageDescription, uncached alias
}


def block0(raw: bytes) -> bytes:
    """Return block 0's payload of a firmware file."""
    return container.parse(raw).blocks[0].payload


def find_filmname(base: bytes, stock: bytes) -> int:
    """Return FILMNAME's address: the one place where new code starts with FILMNAME_HEAD.

    Args:
        base: block 0 with the base specs applied.
        stock: Olympus's block 0.

    Raises:
        ValueError: if the base has no such place, or more than one.
    """
    hits, at = [], base.find(FILMNAME_HEAD)
    while at >= 0:
        if base[at : at + len(FILMNAME_HEAD)] != stock[at : at + len(FILMNAME_HEAD)]:
            hits.append(BASE + at)
        at = base.find(FILMNAME_HEAD, at + 1)
    if len(hits) != 1:
        raise ValueError(f"FILMNAME found {len(hits)} times in the base, not once")
    return hits[0]


def check_stock(base: bytes, stock: bytes, ranges: list[tuple[int, int]]) -> None:
    """Check that the base keeps Olympus's bytes in each range [lo, hi) of addresses.

    Raises:
        ValueError: naming the first range that a base spec changed.
    """
    for lo, hi in ranges:
        if base[lo - BASE : hi - BASE] != stock[lo - BASE : hi - BASE]:
            raise ValueError(f"a base spec changes bytes in {lo:#x}-{hi:#x}")


def assemble(
    work: Path, name: str, source: str, addr: int, symbols: dict[str, int]
) -> tuple[bytes, dict[str, int]]:
    """Assemble MN103 source at an address.

    Args:
        work: a folder for the intermediate files.
        name: the base name of those files.
        source: the assembler source.
        addr: the address of its first byte.
        symbols: the outside addresses it names.

    Returns:
        The code bytes, and the address of each label.
    """
    s, o, elf, out = (work / f"{name}{x}" for x in (".s", ".o", ".elf", ".bin"))
    s.write_text(source, encoding="utf-8")
    subprocess.run([toolchain.binutils("as"), "-o", str(o), str(s)], check=True)
    defs = [f"--defsym={k}={v:#x}" for k, v in symbols.items()]
    ld = [toolchain.binutils("ld"), f"-Ttext={addr:#x}", *defs, "-o", str(elf), str(o)]
    subprocess.run(ld, check=True)
    objcopy = str(Path(toolchain.binutils_dir()) / "mn10300-elf-objcopy")
    subprocess.run([objcopy, "-O", "binary", str(elf), str(out)], check=True)
    nm = str(Path(toolchain.binutils_dir()) / "mn10300-elf-nm")
    labels = {}
    for line in subprocess.run(
        [nm, str(elf)], check=True, capture_output=True, text=True
    ).stdout.splitlines():
        value, kind, label = line.split()
        if kind != "A":
            labels[label] = int(value, 16)
    return out.read_bytes(), labels


def bytes_op(stock: bytes, addr: int, new: bytes, note: str) -> dict[str, Any]:
    """Return a spec's bytes op that writes ``new`` at a block-0 address over stock."""
    old = stock[addr - BASE : addr - BASE + len(new)]
    return {
        "type": "bytes",
        "block": 0,
        "offset": f"{addr - BASE:#x}",
        "expect": old.hex(),
        "new": new.hex(),
        "_addr": f"{addr:#X}",
        "_note": note,
    }


def make_spec(raw: bytes, base: bytes, work: Path) -> dict[str, Any]:
    """Return the spec for a base.

    Args:
        raw: Olympus's firmware file.
        base: block 0 with the base specs applied.
        work: a folder for the assembler's files.

    Raises:
        ValueError: if FILMNAME is not found once, the code does not fit, a hook site
            or the list is not stock, or a base spec changes a byte this spec changes.
    """
    stock = block0(raw)

    def at(addr: int, n: int) -> bytes:
        return stock[addr - BASE : addr - BASE + n]

    for addr, old in ((H1, H1_OLD), (H2, H2_OLD), (H3, H3_OLD)):
        if at(addr, len(old) // 2).hex() != old:
            raise ValueError(f"{addr:#x} is not the stock code this spec hooks")
    if at(COUNT, 8) != (4).to_bytes(4, "little") + STOCK_ITEMS.to_bytes(4, "little"):
        raise ValueError("list 320 is not the stock list of 4 items")
    symbols = dict(EXTERNAL, FILMNAME=find_filmname(base, stock))
    source = SOURCE.read_text(encoding="utf-8")
    code, labels = assemble(work, "artbkt", source, AREA, symbols)
    if AREA + len(code) > AREA_END:
        raise ValueError(f"{len(code)} bytes do not fit in {AREA_END - AREA}")
    header = "        .text\n        .global _start\n_start:\n"
    h1, _ = assemble(work, "h1", header + "jmp ROWS\n", H1, {"ROWS": labels["ROWS"]})
    jump2 = header + "jmp CBDONE\n" + "nop\n" * 4
    h2, _ = assemble(work, "h2", jump2, H2, {"CBDONE": labels["CBDONE"]})
    jump3 = header + "jmp FIXDESC\nnop\n"
    h3, _ = assemble(work, "h3", jump3, H3, {"FIXDESC": labels["FIXDESC"]})
    if (len(h1), len(h2), len(h3)) != (5, 9, 6):
        raise ValueError(f"hook sizes {len(h1)}, {len(h2)}, {len(h3)}")
    items = code[labels["ITEMS"] - AREA : labels["ITEMS"] - AREA + 60]
    stock_items = at(STOCK_ITEMS, 48)
    if items[:36] != stock_items[:36] or items[48:] != stock_items[36:]:
        raise ValueError("ITEMS does not copy the stock items")
    check_stock(
        base,
        stock,
        [(AREA, AREA + len(code)), (H1, H1 + 5), (H2, H2 + 9), (H3, H3 + 6)]
        + [(COUNT, COUNT + 8)],
    )
    count = (5).to_bytes(4, "little") + labels["ITEMS"].to_bytes(4, "little")
    return {
        "name": Path(SPEC).stem,
        "description": "An ART BKT row in RAW Data Edit (Current, Custom1, Custom2, "
        "ART BKT, No). It develops the RAW once per frame of the camera's ART BKT "
        "selection, as an ART bracket shot lists them: the current Picture Mode "
        "first, then each entry that is On. Frame 0 is a stock [Current] edit with "
        "its Yes / No; each later frame is a stock [Current] edit started and saved "
        "by the callback, with the stored Picture Mode (prm 0x9481) and the EXIF "
        "film name (FILMNAME) set first. The Picture Mode comes back at the end and "
        "at any error. A [Current] edit records the EXIF template's ImageDescription "
        "(the film name of the current Picture Mode), not the RAW's. Needs "
        "card-looks-8 (FILMNAME) and the stock-films composer hooks. See "
        "experiments/2026-11-20-raw-edit-art-bkt/NOTES.md section 8 and "
        "experiments/2026-11-24-artbkt-production/NOTES.md.",
        "base": STOCK,
        "base_sha256": hashlib.sha256(raw).hexdigest(),
        "_symbols": {
            k: f"{v:#X}"
            for k, v in sorted(labels.items())
            if k[0].isalpha() and v >= AREA
        },
        "ops": [
            bytes_op(
                stock,
                AREA,
                code,
                f"new code and data, {len(code)} B of {AREA_END - AREA} (segment 2)",
            ),
            bytes_op(stock, COUNT, count, "list 320 (RAW Data Edit): 5 items at ITEMS"),
            bytes_op(
                stock, H1, h1, "H1: the list's OK handler dispatches rows 0-4 in ROWS"
            ),
            bytes_op(
                stock,
                H2,
                h2,
                "H2: a done job of RawEditProcessCallback goes through CBDONE (the displaced call is in it)",
            ),
            bytes_op(
                stock,
                H3,
                h3,
                "H3: the EXIF defaults of a RAW edit go through FIXDESC (the displaced code is in it)",
            ),
        ],
    }


def main(argv: list[str]) -> int:
    """Write the spec; argv[0] is an optional work folder. Return the exit status."""
    work = Path(argv[0]) if argv else ROOT / "build" / "raw-edit-art-bkt"
    work.mkdir(parents=True, exist_ok=True)
    specs = [str(s) for s in json.loads((ROOT / BUILD).read_text())["specs"]]
    if specs[-1] != SPEC:
        print(f"{BUILD}: its last spec must be {SPEC}", file=sys.stderr)
        return 1
    raw = (ROOT / STOCK).read_bytes()
    base_specs = [load_spec(ROOT / s) for s in specs[:-1]]
    spec = make_spec(raw, block0(apply_specs(raw, base_specs).image), work)
    (ROOT / SPEC).write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {SPEC}: {len(spec['ops'][0]['new']) // 2} B; {spec['_symbols']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
