"""The bytes that the peaking generators patch: Olympus's firmware with earlier specs of the pinned build applied."""
import os, sys
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "cli", "src"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import disasm  # noqa: E402
from epm2mod import container  # noqa: E402
from epm2mod.spec import apply_specs, load_spec  # noqa: E402

STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
BIN = os.path.dirname(disasm.objdump_path())
# data/builds/films-look-exif.json, the specs before peaking-colours, in the build's order
EARLIER = ["interval-timelapse-v2", "interval-frames-240", "level-gauge-lvinfo-row", "level-adjust-row",
           "peaking-direct-4", "peaking-gain-2x", "custom-menu-rows-3"]


def payloads(names=()):
    """The block payloads of the stock file with the specs data/specs/NAME.json applied in the given order."""
    raw = open(os.path.join(ROOT, STOCK), "rb").read()
    if names:
        raw = apply_specs(raw, [load_spec(Path(ROOT, "data", "specs", n + ".json")) for n in names]).image
    return [b.payload for b in container.parse(raw).blocks]
