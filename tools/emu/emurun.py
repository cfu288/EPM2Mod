#!/usr/bin/env python3
"""Run a named E-PM2 function in om-emu on stock block 0 and on a patched block 0, and diff the outputs.

    python3 tools/emu/emurun.py list
    python3 tools/emu/emurun.py run  CASE [--image BLOCK0]               # one image; checks the Python model
    python3 tools/emu/emurun.py diff CASE (--patch SPEC... | --image BLOCK0) [--json OUT]

diff runs every input row of CASE on both images and reports:
  - model: rows whose emulated output differs from the case's Python model (per image; the model reads the
    image's own constants where the patch changes them, e.g. the 1740 s limit);
  - changed: rows whose output differs between stock and patched;
  - expected-to-change: for cases that report the data they read (_reads), the rows that read patched bytes.
    A changed row that reads no patched byte, or the reverse, is flagged.
Every run also checks that only the case's own code ranges ran (plus the harness trampoline and return pads).
Exit status 1 on any mismatch, fault or stray code.
"""
import argparse, json, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import omemu, patchblock  # noqa: E402
from cases import CASES  # noqa: E402


def public(out):
    return {k: v for k, v in out.items() if not k.startswith("_")}


def run_image(case, path):
    """[(row, outputs, model or None, errors)] for every row of case on the block-0 image at path."""
    res = []
    with omemu.Emu() as emu:
        emu.load(path)
        allowed = case.ranges + [(omemu.TRAMP, omemu.TRAMP + 16), (omemu.PADS, omemu.PADS + 0x100)]
        for row in case.rows():
            errs = []
            try:
                out = case.run(emu, row)
            except (omemu.EmuError, RuntimeError) as e:
                res.append((row, {"error": str(e)}, None, [f"run: {e}"]))
                continue
            stray = sorted(pc for pc in out["_r"]["pcs"] if not any(lo <= pc < hi for lo, hi in allowed))
            if stray:
                errs.append(f"code outside the case ran: {', '.join(f'0x{p:08x}' for p in stray[:8])}")
            want = case.model(row, emu.image)
            if want is not None:
                for k, v in want.items():
                    if out.get(k) != v:
                        errs.append(f"model: {k} = {out.get(k)!r}, expected {v!r}")
            res.append((row, out, want, errs))
    return res


def fmt_row(row):
    return " ".join(f"{k}={v}" for k, v in row.items())


def cmd_run(case, path):
    bad = 0
    for row, out, want, errs in run_image(case, path):
        mark = "FAIL" if errs else ("ok  " if want is not None else "--  ")
        print(f"{mark} {fmt_row(row)} -> {json.dumps(public(out))}")
        for e in errs:
            print(f"     {e}")
        bad += bool(errs)
    print(f"{case.name}: {len(case.rows())} rows, {bad} failing (ok = matches the model, -- = no model)")
    return bad == 0


def cmd_diff(case, stock, patched, ranges, js):
    a, b = run_image(case, stock), run_image(case, patched)
    bad, changed, report = 0, 0, []
    for (row, o1, w1, e1), (_, o2, w2, e2) in zip(a, b):
        p1, p2 = public(o1), public(o2)
        diff = {k: [p1.get(k), p2.get(k)] for k in sorted(set(p1) | set(p2)) if p1.get(k) != p2.get(k)}
        reads = o1.get("_reads")
        touches = None
        if reads is not None:
            touches = any(s < ra + n and ra < e for ra, n in reads for s, e in ranges)
        flags = [f"stock {x}" for x in e1] + [f"patched {x}" for x in e2]
        if touches is not None and touches != bool(diff):
            flags.append("changed without reading patched bytes" if diff else "reads patched bytes but unchanged")
        changed += bool(diff)
        bad += bool(flags)
        report.append({"row": row, "stock": p1, "patched": p2, "diff": diff, "flags": flags})
        if diff or flags:
            print(f"{'FAIL' if flags else 'chg '} {fmt_row(row)}")
            for k, (x, y) in diff.items():
                print(f"     {k}: {json.dumps(x)} -> {json.dumps(y)}")
            for f in flags:
                print(f"     {f}")
    print(f"{case.name}: {len(a)} rows, {changed} changed, {len(a) - changed} identical, {bad} flagged")
    if js:
        json.dump({"case": case.name, "stock": stock, "patched": patched, "rows": report}, open(js, "w"), indent=1)
    return bad == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["list", "run", "diff"])
    ap.add_argument("case", nargs="?")
    ap.add_argument("--image", help="block-0 image (run: instead of stock; diff: the patched one)")
    ap.add_argument("--patch", nargs="+", help="patch specs to build the patched block 0 from")
    ap.add_argument("--json", help="diff: write the full report here")
    a = ap.parse_args()
    if a.cmd == "list":
        for c in CASES.values():
            print(f"{c.name:14s} 0x{c.entry:08x}  {c.doc}")
            for addr, what in c.stubs_doc:
                print(f"{'':14s}   stub 0x{addr:08x}: {what}")
        return 0
    case = CASES[a.case]
    if a.cmd == "run":
        return 0 if cmd_run(case, a.image or omemu.check_stock()) else 1
    stock = omemu.check_stock()
    if a.patch:
        s, new, other = patchblock.patched_block0(a.patch)
        for o in other:
            print(f"note: not emulated: {o}")
        fd, patched = tempfile.mkstemp(suffix=".block0.bin", prefix="emurun-")
        os.write(fd, new)
        os.close(fd)
    elif a.image:
        patched = a.image
        s, new = open(stock, "rb").read(), open(patched, "rb").read()
    else:
        ap.error("diff needs --patch or --image")
    ranges = [(omemu.BASE + x, omemu.BASE + y) for x, y in patchblock.ranges(s, new)]
    print(f"patched bytes: {sum(y - x for x, y in ranges)} in {len(ranges)} runs")
    try:
        return 0 if cmd_diff(case, stock, patched, ranges, a.json) else 1
    finally:
        if a.patch:
            os.unlink(patched)


if __name__ == "__main__":
    sys.exit(main())
