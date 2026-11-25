#!/usr/bin/env python3
"""S0: boot-order check of a build's patched code. Static, no emulator.

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
jump or call is decoded from that instruction's start. Each jmp / call / branch that leaves its run is listed. A
transfer to anything loaded later, or to a range that no boot copy loads, FAILS, unless
emulator/hookcheck-allow.tsv names the instruction's address and this target, with a reason (for example proof that
the function cannot run before Usr1). The same address with another target FAILS. Exit status 1 on any FAIL.

A word of an op that points into early-loaded code or data in stock and into
late-loaded space in the build is listed as a `pointer` (a case of a switch table, a table address) and FAILS in the
same way.

Limits: only control transfers with a constant target and changed stock pointers are seen (not `jmp (a0)`, not a
pointer in new code or a new table, not RAM reads of late data). A data op in early-loaded space is decoded as code too: a FAIL there is a false alarm, to be
named in the allow list. The classes come from tools/freespace.py's load model. It says nothing about the order of
tasks after the copies.
"""
import argparse, json, os, re, subprocess, sys, tempfile

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


def transfers(addr, code):
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


CLASSES = ("proof", "inferred", "timing")
#: The build descriptions, beside the pinned one, that use entries of the allow list. A test holds that every entry
#: is used by the pinned build or one of these; an entry that none uses is removed.
USED_BY = ("data/builds/debug-log-movie-ab.json",)


class Allowed(str):
    """Why a transfer is accepted (the text that check() prints), with the row of the allow list: its number in the
    file (row), its class (cls) and its reason."""

    def __new__(cls, text, row=0, klass="", reason=""):
        self = super().__new__(cls, text)
        self.row, self.cls, self.reason = row, klass, reason
        return self


def read_allow(path=None):
    """{(address, target): Allowed} of emulator/hookcheck-allow.tsv. The first column of a row lists its words as
    ADDRESS>TARGET, separated by spaces. An entry accepts that one transfer: another target at the address FAILS."""
    allow = {}
    path = path or os.path.join(HERE, "hookcheck-allow.tsv")
    for number, line in enumerate(open(path, encoding="utf-8"), 1):
        if line.strip() and not line.startswith("#"):
            words, _date, cls, reason = line.rstrip("\n").split("\t")
            if cls not in CLASSES:
                sys.exit("hookcheck-allow.tsv: line %d: the class is %r, not one of %s" % (number, cls, ", ".join(CLASSES)))
            for word in words.split():
                address, _, target = word.partition(">")
                key = (int(address, 16), int(target, 16))
                if key in allow:
                    sys.exit("hookcheck-allow.tsv: line %d: %s is listed twice" % (number, word))
                allow[key] = Allowed("%s, line %d of emulator/hookcheck-allow.tsv" % (cls, number), number, cls, reason)
    return allow


def spec_list(paths):
    """The spec paths: a build description (a JSON file with "specs") stands for its specs."""
    res = []
    for p in paths:
        res += json.load(open(_rooted(p))).get("specs") or [p]
    return [_rooted(p) for p in res]


def _rooted(path):
    """A path as given, or under the repository root when it is relative and not there under the working folder:
    the result does not depend on where the command runs."""
    return path if os.path.isabs(path) or os.path.exists(path) else os.path.join(os.path.dirname(HERE), path)


def transfers_of(spec_paths):
    """{address: (mnemonic or "pointer", target, spec names)} of the transfers that leave the patched early-loaded
    bytes of a build (its specs, in order)."""
    spec_paths = spec_list(spec_paths)
    stock, image, _ = patchblock.patched_block0(spec_paths)
    cut = lambda blk, lo, hi: blk[lo - BASE:hi - BASE]
    ops = []
    for p in spec_paths:
        for op in json.load(open(p))["ops"]:
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


def check(spec_paths, allow=None, out=print, used=None):
    """List the transfers that leave the build's patched early-loaded code. True when none FAILS.
    allow: {(address, target): reason}, as read_allow() returns. A transfer to late-loaded space passes only when its
    address and its target are both those of an entry. The entries that match nothing in the build are counted in the
    last line: they belong to other builds, or they are stale.
    used: a list that gets (address, target, the entry) of each accepted transfer."""
    allow = allow or {}
    found = transfers_of(spec_paths)
    listed = {}
    for address, target in allow:
        listed.setdefault(address, []).append(target)
    fails, matched = 0, set()
    for ia, (mn, tgt, name) in sorted(found.items()):
        s, t = segment(ia), segment(tgt)
        bad = t not in EARLY
        why = allow.get((ia, tgt)) if bad else None
        fails += bad and not why
        note = ""
        if why:
            matched.add((ia, tgt))
            note = "  allowed: " + why
            if used is not None:
                used.append((ia, tgt, why))
        elif bad and ia in listed:
            note = "  the allow list accepts this address only for the target %s" % ", ".join("0x%08X" % x for x in listed[ia])
        out("%-5s 0x%08X (%s) %s -> 0x%08X (%s)%s  [%s]" % (
            ("ALLOWED" if why else "FAIL") if bad else "ok", ia, s, mn, tgt, t, note, name))
    unused = sorted(set(allow) - matched)
    out("S0 boot-order check: %d transfers, %d FAIL, %d allowed%s; %d entries of the allow list match nothing in this build%s" % (
        len(found), fails, len(matched), "" if fails else
        " (every transfer from early-loaded code stays in early-loaded code, or is in the allow list)", len(unused),
        ": " + " ".join("%08X>%08X" % x for x in unused[:8]) + (" ..." if len(unused) > 8 else "") if unused else ""))
    return fails == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("specs", nargs="+", help="a build description, or the specs of a build in its order")
    a = ap.parse_args()
    try:
        sys.exit(0 if check(a.specs, read_allow()) else 1)
    except toolchain.ToolchainError as error:
        sys.exit("hookcheck: cannot run: %s" % error)


if __name__ == "__main__":
    main()
