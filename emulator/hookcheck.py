#!/usr/bin/env python3
"""Load-order check of a build's patched code. Static, no emulator.

    python3 emulator/hookcheck.py data/builds/NAME.json
    python3 emulator/hookcheck.py SPEC.json [SPEC.json ...]        # all specs of a build, in the build's order

Why: the boot code copies block 0 to RAM in steps (docs/reference/code-space-map.md, load map). The kernel and segment 1 are
in RAM first; segment 2, segment 3 and usr1-third arrive later, from the Usr1 task, and never on the firmware-update
path. Early code that jumps to late code crashes when it runs before the copy. This happened twice: the hook of
peaking-direct-2 in the heap mode chooser 0x7E714833 (segment 1) jumped to 0x7EBF1F74 (segment 2), and the boot task
calls that function before Usr1 loads segment 2; and peaking-mf's `jmp` at 0x7E4C93A4 (kernel range, in code of an
earlier spec) to 0x7ECB0B81 (segment 2) ran at the first live-view refresh of a cold start (GitHub issue #6).

What it does: it makes the build's block 0 (stock with the specs applied in order) and decodes the built bytes of
every op that lies in the pre-reset range, the kernel or segment 1. Ops that overlap are decoded as one run, so a
jump that a later spec writes into an earlier spec's code is seen. An op that changes only the target of a stock
jump or call is decoded from that instruction's start. A word that points into early-loaded code or data in stock and
into late-loaded space in the build counts too (`pointer`: a case of a switch table, a table address).

A transfer (its address and its target) to anything loaded later, or to a range that no boot copy loads, is a FAIL
when the pinned build does not have it. Exit status 1 on any FAIL. Nothing else is printed but the count. The
transfers that the pinned build has are in docs/dev/load-order.md, section 5: they are known risks, not proven safe.

Limits: only control transfers with a constant target and changed stock pointers are seen (not `jmp (a0)`, not a
pointer in new code or a new table, not RAM reads of late data). A data op in early-loaded space is decoded as code
too. The classes come from tools/freespace.py's load model. It says nothing about the order of tasks after the copies.
"""
import argparse, functools, json, os, re, subprocess, sys, tempfile
import pathlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bootmem  # noqa: E402
import patchblock  # noqa: E402

BASE = 0x7E421020
EARLY = ("pre-reset", "kernel", "data-image", "sram-image", "segment-1")
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
import toolchain  # noqa: E402


XFER = re.compile(r"^\s*([0-9a-f]+):\s+(?:[0-9a-f]{2} )+\s*\t(jmp|calls?|b[a-z]{1,2}|l[a-z]{2})\t(?:0x)?([0-9a-f]{8})\b")


def segment(a):
    m = bootmem.model()
    if m.pre.lo <= a < m.pre.hi:
        return "pre-reset"
    L = m.load_of(a)
    if L is not None:
        return L.name
    return "not loaded" if BASE <= a < m.end else "outside block 0"


@functools.lru_cache(maxsize=None)
def transfers(addr, code):  # cached: a build and the pinned build share most of their ops
    """[(insn address, mnemonic, target)] of the constant-target transfers in code at addr."""
    fd, p = tempfile.mkstemp(suffix=".bin")
    os.write(fd, code)
    os.close(fd)
    try:
        out = subprocess.run([toolchain.binutils("objdump"), "-D", "-b", "binary", "-m", "am33-2", "-EL", "--adjust-vma=%#x" % addr, p],
                             capture_output=True, text=True, check=True).stdout
    finally:
        os.unlink(p)
    res = []
    for line in out.splitlines():
        m = XFER.match(line)
        if m:
            res.append((int(m.group(1), 16), m.group(2), int(m.group(3), 16)))
    return res


def spec_list(paths):
    """The spec paths: a build description (a JSON file with "specs") stands for its specs."""
    root, res = os.path.dirname(HERE), []
    for p in paths:
        given = p if os.path.isabs(p) or os.path.exists(p) else os.path.join(root, p)  # an argument: as the caller wrote it
        inside = json.loads(pathlib.Path(given).read_text(encoding="utf-8")).get("specs")
        # the specs that a description names are paths of the repository, wherever the command runs
        res += [os.path.join(root, s) for s in inside] if inside else [given]
    return res


def transfers_of(spec_paths):
    """{address: (mnemonic or "pointer", target, spec names)} of the transfers that leave the patched early-loaded
    bytes of a build (its specs, in order)."""
    spec_paths = spec_list(spec_paths)
    stock, image, _ = patchblock.patched_block0(spec_paths)
    cut = lambda blk, lo, hi: blk[lo - BASE:hi - BASE]
    ops = []
    for p in spec_paths:
        for op in json.loads(pathlib.Path(p).read_text(encoding="utf-8"))["ops"]:
            lo = BASE + int(op.get("offset", "0"), 16)
            if op.get("block") == 0 and op.get("type") == "bytes" and segment(lo) in EARLY:
                ops.append((lo, lo + len(op["new"]) // 2, os.path.basename(p)))
    runs = []                                             # overlapping ops are one run of built bytes
    for lo, hi, name in sorted(ops):
        if runs and lo < runs[-1][1]:
            names = runs[-1][3] if name in runs[-1][3] else runs[-1][3] + " + " + name
            runs[-1] = (runs[-1][0], max(hi, runs[-1][1]), runs[-1][2] + [lo], names)
        else:
            runs.append((lo, hi, [lo], name))
    found = {}                                            # address -> (mnemonic, target, specs)
    for lo, hi, starts, name in runs:
        for a, end in zip(starts, starts[1:] + [hi]):     # every op start is an instruction start
            for ia, mn, tgt in transfers(a, cut(image, a, hi)):
                if ia < end and not lo <= tgt < hi:       # not inside the same run
                    found[ia] = (mn, tgt, name)
        for back in range(1, 7):                          # the op starts inside a stock jump or call: its new target
            old, now = (transfers(lo - back, cut(b, lo - back, lo - back + 8))[:1] for b in (stock, image))
            if old and now and old[0][0] == now[0][0] == lo - back and old[0][2] != now[0][2] and segment(old[0][2]) in EARLY:
                found[lo - back] = (now[0][1], now[0][2], name)
        for a in range(lo - 3, hi):                       # a table word: a pointer to early code or data in stock.
            # Every word that overlaps the run: an op that changes only the upper bytes of a stock pointer moves it too
            old, now = (int.from_bytes(cut(b, a, a + 4), "little") for b in (stock, image))
            if old != now and segment(old) in EARLY and segment(now) not in EARLY + ("outside block 0",):
                found[a] = ("pointer", now, name)
    return found


def late(spec_paths):
    """{(address, target): (mnemonic or "pointer", spec names)} of the build's transfers to code that is not in RAM
    when the early-loaded code runs."""
    found = transfers_of(spec_paths) if spec_paths else {}
    return {(a, tgt): (mn, name) for a, (mn, tgt, name) in found.items() if segment(tgt) not in EARLY}


def pinned_specs():
    """The specs of the pinned build. None is pinned: no specs, so a build is compared with the stock firmware."""
    pointer = pathlib.Path(os.path.dirname(HERE), "data", "pinned-build.json")
    return spec_list([json.loads(pointer.read_text(encoding="utf-8"))["build"]]) if pointer.exists() else []


def compare(spec_paths):
    """(late() of the build, the sorted (address, target) of it that the pinned build does not have)."""
    mine, known = late(spec_paths), late(pinned_specs())
    return mine, sorted(set(mine) - set(known))


def check(spec_paths, out=print):
    """True when the build has no transfer (address and target) to late-loaded code that the pinned build has not.
    Each new one is a FAIL line; the last line is the summary."""
    mine, new = compare(spec_paths)
    for ia, tgt in new:
        mn, name = mine[ia, tgt]
        out("FAIL  0x%08X (%s) %s -> 0x%08X (%s): not in the pinned build  [%s]" % (ia, segment(ia), mn, tgt, segment(tgt), name))
    out("load-order check: %d transfers from early-loaded to late-loaded code, %d of them not in the pinned build%s" % (
        len(mine), len(new), ". The rule and the ways out: docs/dev/load-order.md, section 2" if new else ""))
    return not new


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("specs", nargs="+", help="a build description, or the specs of a build in its order")
    a = ap.parse_args()
    try:
        sys.exit(0 if check(a.specs) else 1)
    except toolchain.ToolchainError as error:
        sys.exit("hookcheck: cannot run: %s" % error)


if __name__ == "__main__":
    main()
