#!/usr/bin/env python3
"""Differential test: the E-PM2 with patches/lss-core.json against the PEN-F 3.1's own exposure code.

    uv run python experiments/2026-11-17-auto-iso-min-shutter/scripts/lss_compare.py PENF_BLOCK0 [--show N]

Both routines run in the function harness (expcal.py, penf_expcal.py) on the same inputs. A row passes when Tv and Av
are equal and Sv differs only by the PEN-F's fixed offset (376 = 1.47 EV, the same in every stock row).
Rows where the feature is off compare the patched E-PM2 with the stock E-PM2 instead (nothing may change).
Known body differences that are not part of this feature are reported as their own class (see NOTES.md section 9).
"""
import argparse, itertools, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "emu"))
sys.path.insert(0, HERE)
import omemu, patchblock, expcal, penf_expcal as pf  # noqa: E402
from expcal import tv_str, fno_str, s16  # noqa: E402

SV_OFF = 376
expcal.K_ADDR = 0x60413225      # setting 653 (tag 0x9F11), the byte lss.s reads


def lss_q8(k):
    return 0x7FFF if k == 0 else int(256 * (k - 19) / 3)


def rows(quick=False):
    for mode, focal, slow, k, limit, flash, step in itertools.product(
            (3, 4), (34, 300) if quick else (18, 34, 90, 300), (0x0600,) if quick else (0x0600, 0x0800), (0, 1, 13, 25, 31, 37, 40, 43, 49, 55), (0x0900, 0x0B00),
            (0, 1), (85, 128, 256)):
        if (flash or step != 85) and (focal != 34 or slow != 0x0600 or limit != 0x0B00):
            continue
        for bv in range(-0x0600, 0x0B00, 0x00AA if quick else 0x0055):
            yield dict(mode=mode, focal=focal, slow=slow, k=k, limit=limit, stb_onoff=flash, strobe=flash, step=step,
                       bv=bv)
    for k in (0, 31, 43):                                   # manual ISO 800: no change
        for bv in range(-0x0400, 0x0A00, 0x0080):
            yield dict(mode=3, k=k, sv_set=0x0800, bv=bv)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("block0")
    ap.add_argument("--show", type=int, default=20)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    R = list(rows(a.quick))
    tmp = "/dev/shm/lss-core.block0.bin"
    open(tmp, "wb").write(patchblock.patched_block0([os.path.join(ROOT, "patches", "lss-core.json")])[1])
    with omemu.Emu() as e:
        e.load(omemu.check_stock())
        stock = [expcal.run(e, r)[1] for r in R]
    with omemu.Emu() as e:
        e.load(tmp)
        new = [expcal.run(e, r)[1] for r in R]
    with omemu.Emu() as e:
        pf.load(e, a.block0)
        ref = []
        for r in R:
            p = dict(r, lss=lss_q8(r["k"]), fast=0x0800)
            p.pop("k")
            ref.append(pf.run(e, p)[1])
    os.unlink(tmp)
    stats, shown = {}, 0
    for r0, s, n, p in zip(R, stock, new, ref):
        r = dict(expcal.D, **r0)
        key = lambda o, off=0: (s16(o["tv"]), s16(o["av"]), s16(o["sv"]) + off)
        active = r["k"] and not r.get("stb_onoff") and not r.get("sv_set")
        if not active:
            cls = "off: same as stock" if key(n) == key(s) else "off: CHANGED"
        elif key(n) == key(p, SV_OFF):
            cls = "on: same as PEN-F"
        elif s16(n["tv"]) == 3072 and s16(p["tv"]) > 3072:
            cls = "on: PEN-F faster than 1/4000 (its top speed is 1/8000)"
        else:
            cls = "on: DIFFERENT"
        stats[cls] = stats.get(cls, 0) + 1
        if ("CHANGED" in cls or "DIFFERENT" in cls) and shown < a.show:
            shown += 1
            print(f"{cls:22} mode {r['mode']} f{r['focal']} slow {tv_str(r['slow'])} k {r['k']} ({tv_str(lss_q8(r['k'])) if r['k'] else 'Auto'}) "
                  f"lim {r['limit']:#x} fl {r.get('stb_onoff',0)} step {r['step']} bv {s16(r['bv'])/256:+.2f} | "
                  f"stock {tv_str(s['tv'])} {fno_str(s['av'])} {s16(s['sv'])} | new {tv_str(n['tv'])} {fno_str(n['av'])} "
                  f"{s16(n['sv'])} | PEN-F {tv_str(p['tv'])} {fno_str(p['av'])} {s16(p['sv'])+SV_OFF}")
    for k, v in sorted(stats.items()):
        print(f"{v:6d}  {k}")
    print(f"{len(R):6d}  rows")


if __name__ == "__main__":
    main()
