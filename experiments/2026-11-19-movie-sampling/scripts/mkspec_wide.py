"""Write data/specs/movie-wide-frame.json (the reader side, NOTES.md section 12) and data/specs/movie-wide-writer.json
(the writer side, section 14): the 1080 movie Bayer frame 1938 x 1296 (effective 1920 x 1296, stride 1960) in place of
1662 x 1296 (effective 1646, stride 1680).

    uv run python experiments/2026-11-19-movie-sampling/scripts/mkspec_wide.py

Research code. Only immediates change, each in an instruction or a table word of stock bytes; no code is added. The
sensor window stays at 2326 px: calc_r(1938, 78643) = calc_r(1662, 91750) (scripts/geom_calc_r.py). Every site is
the HSHR geometry (sensor mode 4), so 720p (the same HSHR record) changes too. The Movie IS crop and its shift divisor
are scaled with the frame (1414 -> 1650, 91750 -> 78643), so IS on keeps the stock field of view (untested).
"""

import hashlib
import json
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
BASE = 0x7E421020
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
STOCK_BLOCK = os.path.join(ROOT, "build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin")
SPEC = "movie-wide-frame"

h16 = lambda v: struct.pack("<H", v)
h32 = lambda v: struct.pack("<I", v)
# (address, stock bytes, new bytes, note)
OPS = [
    (0x7E59EE7E, b"\x2c" + h16(1662), b"\x2c" + h16(1938), "TAKE request builder 0x7E59EE0A, HSHR case: +6 width 1662 -> 1938 (`mov imm16,d0`)"),
    (0x7E59EE8A, b"\x2c" + h16(1646), b"\x2c" + h16(1920), "TAKE request builder, HSHR case: +10 effective width 1646 -> 1920"),
    (0x7E6C42F7, b"\xfa\xc3" + h16(831), b"\xfa\xc3" + h16(969), "movie mode table 0x7E6C410A, HSHR record +10: centre x 831 -> 969 (`add imm16,d3`)"),
    (0x7E6C4304, b"\x2d" + h16(1680), b"\x2d" + h16(1960), "movie mode table, HSHR record +0: stride 1680 -> 1960 (`mov imm16,d1`)"),
    (0x7E6C430D, b"\x2d" + h16(1662), b"\x2d" + h16(1938), "movie mode table, HSHR record +2: width 1662 -> 1938"),
    (0x7E6C431F, b"\x2d" + h16(1646), b"\x2d" + h16(1920), "movie mode table, HSHR record +6: effective width 1646 -> 1920"),
    (0x7E6C435A, b"\x2d" + h16(1414), b"\x2d" + h16(1650), "movie mode table, HSHR record +18: Movie IS crop width 1414 -> 1650 (same field of view)"),
    (0x7E6CB8B3, b"\x2c" + h16(1414), b"\x2c" + h16(1650), "Movie IS crop 0x7E6CB860, HSHR 1080/720: crop width 1414 -> 1650"),
    (0x7E6CB981, b"\xfc\xce" + h32(91750), b"\xfc\xce" + h32(78643), "Movie IS shift 0x7E6CB90B, HSHR: divisor 91750 (1.4) -> 78643 (1.2) (`mov imm32,d2`)"),
    (0x7E54A2CE, b"\x2c" + h16(1646), b"\x2c" + h16(1920), "IMG resize builder 0x7E54A0D0, IMG mode 5 (HSHR): full-readout width 1646 -> 1920"),
    (0x7E54A5E9, b"\x2c" + h16(1646), b"\x2c" + h16(1920), "IMG resize builder 0x7E54A468, IMG mode 5 (HSHR): full-readout width 1646 -> 1920"),
    (0x7E698658, b"\x2c" + h16(1662), b"\x2c" + h16(1938), "AE parameter set HSHR 0x7E698658: use width 1662 -> 1938"),
    (0x7E698694, b"\xfc\xcc" + h32(91750), b"\xfc\xcc" + h32(78643), "AE parameter set HSHR: resize 91750 -> 78643 (calc_r still gives 2326)"),
    (0x7E85B3DC, struct.pack("<8H", 1680, 1662, 1312, 0, 1646, 1296, 831, 656),
     struct.pack("<8H", 1960, 1938, 1312, 0, 1920, 1296, 969, 656), "art_get_bayer_size table 0x7E85B38C, entry 5 (HSHR): stride, width, effective width, centre x"),
]


# The writer: record 7 (mode code 517, HSHR) of the TAKE sensor-mode request table 0x7E793184 (18 records of 48 B,
# lookup 0x7E5A8AD2), copied into the camera-core request by 0x7E5A897F: +8 the written line width (request +4), and
# the pre-processor's horizontal resize block (request +46..+54): step 5734 = 1.4 in Q12, and the phase of the second
# colour of each Bayer pair, 1843 = 1024 + (5734 - 4096) / 2. 1680 x 1.4 = 1960 x 1.2 = 2352 input px.
REC = 0x7E7932D4
WRITER_OPS = [
    (REC + 8, h16(1680), h16(1960), "TAKE sensor-mode request table 0x7E793184, record 7 (code 517, HSHR) +8: written line width 1680 -> 1960 (request +4)"),
    (REC + 40, h16(1843), h16(1433), "record 7 +40: resize phase 1843 -> 1433 = 1024 + (4915 - 4096) / 2 (request +48)"),
    (REC + 44, h16(1843), h16(1433), "record 7 +44: resize phase 1843 -> 1433 (request +52)"),
    (REC + 46, h16(5734), h16(4915), "record 7 +46: horizontal resize step 5734 (1.4 in Q12) -> 4915 (1.2) (request +54)"),
]


def write(spec, op_list, description):
    """Check every site against stock block 0 and write one spec."""
    blk = open(STOCK_BLOCK, "rb").read()
    ops = []
    for addr, old, new, note in op_list:
        assert len(old) == len(new) and blk[addr - BASE:addr - BASE + len(old)] == old, hex(addr)
        diff = [i for i in range(len(old)) if old[i] != new[i]]
        a, b = diff[0], diff[-1] + 1          # only the bytes that change, so the free-space ledger stays exact
        ops.append({"type": "bytes", "block": 0, "offset": "0x%X" % (addr + a - BASE), "expect": old[a:b].hex(),
                    "new": new[a:b].hex(), "_addr": "0x%08X" % (addr + a), "_note": note})
    out = os.path.join(ROOT, "data", "specs", spec + ".json")
    json.dump({
        "name": spec,
        "description": description,
        "base": STOCK, "base_sha256": hashlib.sha256(open(os.path.join(ROOT, STOCK), "rb").read()).hexdigest(),
        "status": "candidate: emulator-checked, not flashed",
        "ops": ops,
    }, open(out, "w"), indent=1)
    open(out, "a").write("\n")
    print("wrote", os.path.relpath(out, ROOT), len(ops), "ops")


def main():
    """Write both specs."""
    write(SPEC, OPS, "1080 movie frame 1920 wide: the HSHR (1080 and 720 movie) Bayer frame becomes 1938 x 1296 with "
                       "an effective 1920 x 1296 and a stride of 1960, in place of 1662 x 1296, 1646 x 1296 and 1680. The "
                       "pre-processor then shrinks the 2326-px sensor line by 1.2 instead of 1.4, and 1080 needs no "
                       "horizontal upscale. Changed: the TAKE request, the movie mode table, the IMG resize builders, "
                       "the AE set (its sensor window stays 2326 px), art_get_bayer_size entry 5, and the Movie IS crop "
                       "(1414 -> 1650) and shift divisor (1.4 -> 1.2). Immediates only. Not conditional: 720p uses the "
                       "same frame. DEBUG builds only. See experiments/2026-11-19-movie-sampling/NOTES.md section 12.")
    write("movie-wide-writer", WRITER_OPS,
          "1080 movie frame 1920 wide, the writer side (with data/specs/movie-wide-frame.json, the reader side): record 7 "
          "(mode code 517, HSHR) of the TAKE sensor-mode request table 0x7E793184, which 0x7E5A897F copies into the "
          "camera-core request. The written line becomes 1960 px (was 1680) and the pre-processor's horizontal resize "
          "step 1.2 (4915 in Q12, was 5734 = 1.4), with the second Bayer phase 1433 (was 1843); the input stays 2352 px "
          "(1680 x 1.4 = 1960 x 1.2). The line count 1312 and the window start 44/11 stay. DEBUG builds only. See "
          "experiments/2026-11-19-movie-sampling/NOTES.md section 14.")


if __name__ == "__main__":
    main()
