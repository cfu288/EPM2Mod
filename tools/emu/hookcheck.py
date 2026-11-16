#!/usr/bin/env python3
"""S0: boot-order check of a patch spec's hooks. Static, no emulator.

    python3 tools/emu/hookcheck.py SPEC.json [SPEC.json ...] [--allow 0xSITE=reason ...]

Why: the boot code copies block 0 to RAM in steps (docs/code-space-map.md, load map). The kernel and segment 1 are
in RAM first; segment 2, segment 3 and usr1-third arrive later, from the Usr1 task, and never on the firmware-update
path. A hook in early code that jumps to late code crashes when the hooked function runs before the copy. This
happened: the hook of peaking-direct-2 in the heap mode chooser 0x7E714833 (segment 1) jumped to 0x7EBF1F74
(segment 2), and the boot task calls that function before Usr1 loads segment 2.

What it does: for every block-0 op that starts with a jump or call (a hook), and for every op that such a jump
reaches (new code), it lists each jmp / call / branch with its source and target segment. A transfer from the
pre-reset range, the kernel or segment 1 to anything loaded later, or to a range that no boot copy loads, FAILS,
unless --allow names the instruction's address with a reason (for example proof that the function cannot run
before Usr1). Exit status 1 on any FAIL.

Limits: only control transfers with a constant target are seen (not `jmp (a0)`, not data pointers, not RAM
reads of late data). The classes come from tools/freespace.py's load model. It says nothing about the order of
tasks after the copies.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bootmem  # noqa: E402

BASE = 0x7E421020
EARLY = ("pre-reset", "kernel", "data-image", "sram-image", "segment-1")
OBJDUMP = os.environ.get("OM_OBJDUMP") or os.path.join(os.path.dirname(os.path.dirname(HERE)), "build", "toolchain", "bin", "mn10300-elf-objdump")
XFER = re.compile(r"^\s*([0-9a-f]+):\s+(?:[0-9a-f]{2} )+\s*\t(jmp|call|b[a-z]{1,2}|l[a-z]{2})\t(?:0x)?([0-9a-f]{8})\b")


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
        out = subprocess.run([OBJDUMP, "-D", "-b", "binary", "-m", "am33-2", "-EL", "--adjust-vma=%#x" % addr, p],
                             capture_output=True, text=True, check=True).stdout
    finally:
        os.unlink(p)
    res = []
    for line in out.splitlines():
        m = XFER.match(line)
        if m:
            res.append((int(m.group(1), 16), m.group(2), int(m.group(3), 16)))
    return res


def check(spec_paths, allow=None, out=print):
    allow = allow or {}
    ops = []
    for p in spec_paths:
        for op in json.load(open(p))["ops"]:
            if op.get("block") == 0 and op.get("type") == "bytes":
                ops.append((BASE + int(op["offset"], 16), bytes.fromhex(op["new"]), os.path.basename(p)))
    def op_at(a):
        return next((o for o in ops if o[0] <= a < o[0] + len(o[1])), None)
    todo = [o for o in ops if o[1][:1] in (b"\xdc", b"\xdd", b"\xcc", b"\xcd") and len(o[1]) <= 8]     # hook sites
    seen, fails, rows = set(), 0, 0
    while todo:
        o = todo.pop(0)
        if o[0] in seen:
            continue
        seen.add(o[0])
        hook = len(o[1]) <= 8
        for ia, mn, tgt in transfers(o[0], o[1]):
            if hook and ia != o[0]:
                continue                                  # a hook is one jump; the padding after it is not decoded
            if o[0] <= tgt < o[0] + len(o[1]):
                continue                                  # inside the same op
            s, t = segment(ia), segment(tgt)
            bad = s in EARLY and t not in EARLY
            why = allow.get(ia)
            verdict = "ok" if not bad else ("allowed: " + why if why else "FAIL")
            fails += verdict == "FAIL"
            rows += 1
            out("%-5s %s 0x%08X (%s) %s -> 0x%08X (%s)%s  [%s]" % (
                verdict.split(":")[0].upper() if bad else "ok", "hook" if hook else "code", ia, s, mn, tgt, t,
                "" if verdict in ("ok", "FAIL") else "  " + verdict, o[2]))
            nxt = op_at(tgt)
            if nxt and nxt[0] not in seen:
                todo.append(nxt)
    out("S0 boot-order check: %d transfers, %d FAIL%s" % (rows, fails, "" if fails else
        " (every transfer from early-loaded code stays in early-loaded code)"))
    return fails == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("specs", nargs="+")
    ap.add_argument("--allow", nargs="*", default=[], metavar="0xADDR=reason")
    a = ap.parse_args()
    allow = {int(x.split("=", 1)[0], 16): x.split("=", 1)[1] for x in a.allow}
    sys.exit(0 if check(a.specs, allow) else 1)


if __name__ == "__main__":
    main()
