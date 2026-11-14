"""Give emulator RAM the content that the E-PM2 boot code gives it (the load map of docs/code-space-map.md).

om-emu maps the whole block 0 at its runtime address and leaves all other RAM zero. The camera does this instead:
  - the boot code copies only some ranges of block 0 from flash to RAM (kernel, data-image, sram-image, segments 1-3,
    usr1-third; two overlays on demand). The other runtime ranges of block 0 are RAM that the block does not fill;
  - the reset code copies the .data image (0x7E8DA000-0x7E8F3114) to RAM 0x602A9B40, and two word tables to
    0x60000FE0 and 0x60000000;
  - the boot task copies 512 words of the sram-image to SRAM 0x47001000.

apply(emu) does the same with the bytes of the image that the emulator holds (so a patched image gives patched
.data). Every range and address comes from tools/freespace.py's Model, which reads them from the stock block-0
bytes at checked sites; nothing is typed in here. om-emu maps 0x60.. and 0xA0.. (uncached alias) to the same RAM,
so one write serves both.

Not done (reported in the returned list): the SRAM copy (om-emu maps no memory at 0x47000000), the two flash
reads whose source is outside block 0 (0x7FF9A000, 0x604F2ED8), and everything that code writes after the copies
(.bss is zero, as after the reset clears; no task has run).
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
BASE = 0x7E421020
_MODEL = None


def model():
    """tools/freespace.py's load model of the stock block 0 (built once)."""
    global _MODEL
    if _MODEL is None:
        import freespace
        _MODEL = freespace.Model(freespace.load_block0())
    return _MODEL


def plan(image, overlays=True):
    """[(what, dst, bytes)] RAM writes and [(lo, hi)] unloaded runtime ranges, for the block-0 bytes in image."""
    m = model()
    f = m.f
    cut = lambda lo, hi: image[lo - BASE:hi - BASE]
    w1, w2, dc = f["reset_wcopy1"], f["reset_wcopy2"], f["reset_data_copy"]
    copies = [(".data image", dc["ram"], cut(dc["start"], dc["end"])),
              ("reset word copy 1", w1["dst"], cut(w1["start"], w1["end"])),
              ("reset word copy 2 (conditional on the camera)", w2["dst"], cut(w2["start"], w2["end"]))]
    loaded = [(m.pre.lo, m.pre.hi)] + [(L.lo, L.hi) for L in m.loads if overlays or not L.cond]
    loaded.sort()
    gaps, at = [], BASE
    for lo, hi in loaded:
        if lo > at:
            gaps.append((at, lo))
        at = max(at, hi)
    if at < BASE + len(image):
        gaps.append((at, BASE + len(image)))
    return copies, gaps


def apply(emu, clear_unloaded=True, overlays=True):
    """Apply the boot copies to emu's RAM. Returns a list of report lines.
    clear_unloaded: zero the runtime ranges of block 0 that no boot copy fills (code that reads them is then seen:
    it gets zero in place of flash bytes). overlays: keep the two on-demand overlays (Usr2) mapped."""
    copies, gaps = plan(emu.image, overlays)
    rep = []
    for what, dst, data in copies:
        _write(emu, dst, data)
        rep.append("copied %s: %d bytes to 0x%08X" % (what, len(data), dst))
    if clear_unloaded:
        n = 0
        for lo, hi in gaps:
            _write(emu, lo, bytes(hi - lo))
            n += hi - lo
        rep.append("cleared %d runtime ranges of block 0 that no boot copy loads (%d bytes)" % (len(gaps), n))
    sr = model().f["boot_sram_copy"]
    rep.append("not done: SRAM code copy to 0x%08X (om-emu maps no memory there)" % sr["dst"])
    rep.append("not done: flash reads from outside block 0 (0x7FF9A000, 0x604F2ED8); .bss stays zero")
    return rep


def _write(emu, addr, data, chunk=0x8000):
    for i in range(0, len(data), chunk):
        emu.write(addr + i, data[i:i + chunk])


def unloaded(image=None, overlays=True):
    """The runtime ranges of block 0 that no boot copy fills."""
    n = len(image) if image is not None else len(model().b)
    return plan(bytes(n), overlays)[1]
