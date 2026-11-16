"""Dynamic inventory of the readers of the Picture Mode and of the art code, and the comparison with readers.py.

    .venv/bin/python experiments/2026-11-16-films-max/scripts/readers_dynamic.py builds/films-12.json BLOCK0 OUTDIR

BLOCK0 is block 0 of the same build (for the live-view rig). OUTDIR is a scratch folder outside the repository.
Needs results/readers.tsv (run readers.py first), the settings states of screens.sh
(build/emu/films-max/NAME/state/pinned-{p,art,movie}.json) and the emulators (tools/emu/setup.sh).

1. Full boot (tools/emu/boot/play.mjs with scripts/watch_reads.mjs): read watchpoints on the stored Picture Mode
   and the ART mode code in the settings bank. Sessions: mode P live control strip over all 19 values with OK on
   a new entry, Shooting Menu 1 -> Picture Mode list with OK on a new entry, Picture Mode Settings, INFO and
   PLAY; ART mode: the ART list, OK on a new entry, the ART BKT list; movie mode: the strip with OK on a new
   entry. A reader = the first code address on the stack outside the settings store (0x7E455000-0x7E459000; only the two Picture Mode bytes are
   compared, the ART mode code bytes are several settings that the static list does not try to cover):
   the store reads the byte for every caller.
2. Live-view rig (tools/emu/liveview.py): read watchpoints on the mov layer's bytes 0x605B1CD2 / 0x605B1CD3 /
   0x605B091C / 0xA07507CC (both aliases); three frames for each of the twelve stored values and 119, then three
   with the MF Assist request. A reader = the pc of the reading instruction.
3. Comparison. A static call site of readers.py (kind A) counts as executed if a stack of step 1 holds its
   return address (the site plus 3 to 8 bytes). A static read of kind C with an absolute address counts as
   executed if step 2 saw its pc. A dynamic reader with no static site on its stack, or a dynamic pc that is
   not in the static list, is a gap of the static method.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PEAKING = ROOT / "experiments" / "2026-11-14-focus-peaking" / "scripts"
sys.path.insert(0, str(ROOT / "tools" / "emu"))
sys.path.insert(0, str(PEAKING))
STORE = (0x7E455000, 0x7E459000)
#: Where block 0 holds code (the rest is tables and text: a table address on the stack is not a caller).
CODE = ((0x7E430000, 0x7E4C9800), (0x7E4FE000, 0x7E731584), (0x7E8F5800, 0x7EBA0000), (0x7ECCB800, 0x7EF00000))
MOV_BYTES = (0x605B1CD2, 0x605B1CD3, 0x605B091C, 0xA07507CC)


def rep(count: int, key: str) -> list[str]:
    return [key] * count


def sessions() -> dict[str, tuple[str, list[str]]]:
    """name -> (state mode, play.mjs steps)."""
    menu = ["w:500", "key:MENU", "key:RIGHT", "key:OK"]
    return {
        "p-strip": ("p", ["w:500", "key:OK", "w:500", "key:UP"] + rep(19, "key:RIGHT") + rep(7, "key:LEFT") + ["key:OK", "w:800", "key:INFO", "w:300", "key:INFO", "w:300"]),
        "p-menu": ("p", menu + ["key:RIGHT", "key:DOWN", "key:RIGHT"] + rep(15, "key:DOWN") + ["key:OK", "w:800", "key:MENU", "w:300"]),
        "p-settings": ("p", menu + rep(3, "key:DOWN") + ["key:RIGHT"] + rep(3, "key:DOWN") + ["key:RIGHT"] + rep(5, "key:DOWN") + ["key:RIGHT"] + rep(18, "key:DOWN") + ["w:300"]),
        "p-play": ("p", ["w:500", "key:OK", "w:500", "key:UP"] + rep(9, "key:RIGHT") + ["key:OK", "w:500", "key:PLAY", "w:1500", "key:INFO", "w:500", "key:PLAY", "w:800"]),
        "art-list": ("art", ["w:500"] + rep(4, "key:DOWN") + ["key:OK", "w:1000", "key:OK", "w:500"] + rep(6, "key:RIGHT") + ["w:300"]),
        "art-bkt": ("art", ["w:500"] + rep(12, "key:DOWN") + ["key:RIGHT"] + rep(14, "key:DOWN") + ["w:300"]),
        "movie-strip": ("movie", ["w:500", "key:OK", "w:500", "key:UP"] + rep(19, "key:RIGHT") + rep(3, "key:LEFT") + ["key:OK", "w:800"]),
    }


def full_boot(build: str, out: Path, reuse: bool) -> dict[str, list[dict[str, object]]]:
    """Run the sessions; return name -> records {pc, what, stack, n}."""
    name = Path(build).stem
    env = dict(os.environ, E101_RTC="2026-11-14T12:00:00", SETUP=str(HERE / "watch_reads.mjs"))
    results = {}
    for session, (mode, steps) in sessions().items():
        state = out / f"{session}.json"
        shutil.copy(ROOT / f"build/emu/films-max/{name}/state/pinned-{mode}.json", state)
        env.update(E101_STATE=str(state), WATCH_OUT=str(out / f"reads-{session}.json"))
        if reuse and (out / f"reads-{session}.json").exists():
            run = None
        else:
            run = subprocess.run([str(ROOT / "tools/emu/emu-run"), build, "play.mjs", str(out / "shots")] + steps, cwd=ROOT, env=env, capture_output=True, text=True)
        if run is not None and "done at" not in run.stdout:
            print(f"RUN FAILED {session}: {run.stdout[-300:]} {run.stderr[-300:]}")
        records = []
        for item in json.loads((out / f"reads-{session}.json").read_text()):
            parts = item["key"].split(" ")
            stack_at = next(k for k, part in enumerate(parts[1:], 1) if part.startswith("0x"))
            records.append({"pc": int(parts[0], 16), "what": " ".join(parts[1:stack_at]), "stack": [int(p, 16) for p in parts[stack_at:]], "n": item["n"]})
        results[session] = records
    return results


def live_view(block0: str) -> set[int]:
    """Run the rig with read watchpoints on the mov layer's bytes; return the reading pcs."""
    src = (PEAKING / "scen_menu.py").read_text().rstrip()
    assert src.endswith("\nmain()")
    helpers: dict[str, object] = {"__file__": str(PEAKING / "scen_menu.py"), "__name__": "scen_menu"}
    argv, sys.argv = sys.argv, sys.argv[:1]
    exec(compile(src[: -len("main()")], "scen_menu.py", "exec"), helpers)
    sys.argv = argv
    open_lv, request, tag = helpers["open_lv"], helpers["request"], helpers["TAG"]
    pcs: set[int] = set()
    reads = []
    for k, address in enumerate(MOV_BYTES):
        for alias in (address, address ^ 0xC0000000):
            reads.append({"id": 2000 + len(reads), "lo": alias, "hi": alias + 1, "kind": "r", "action": "log"})
    for value in (100, 101, 102, 103, 111, 105, 106, 107, 112, 114, 115, 118, 119):
        with open_lv(block0, "films", value) as lv:  # type: ignore[operator]
            emu = lv.sc.emu
            plain = emu.req

            def req(op: str, _plain=plain, **kw: object) -> object:
                if op == "watch":
                    kw["list"] = list(kw.get("list", [])) + reads  # type: ignore[call-overload]
                return _plain(op, **kw)

            emu.req = req
            lv.settings[tag] = 3
            lv.start()
            frames = [lv.frame() for _ in range(3)]
            request(lv, True)  # type: ignore[operator]
            frames += [lv.frame() for _ in range(3)]
            for frame in frames:
                pcs |= {pc for _, _, _, pc in frame.writes}
    return pcs


def main() -> int:
    build, block0, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    reuse = "--reuse" in sys.argv  # take the records of an earlier run in OUTDIR
    out.mkdir(parents=True, exist_ok=True)
    static = list(csv.DictReader((ROOT / "experiments/2026-11-16-films-max/results/readers.tsv").open(), delimiter="\t"))
    sites = {int(row["address"], 16): row for row in static if row["kind"] == "A"}
    byte_reads = {int(row["address"], 16): row for row in static if row["kind"] == "C" and row["what"].startswith("mov layer")}

    boot = full_boot(build, out, reuse)
    readers: dict[int, set[str]] = {}
    executed: set[int] = set()
    gaps: dict[int, set[str]] = {}
    others: set[int] = set()
    for session, records in boot.items():
        for record in records:
            if not str(record["what"]).startswith("picture mode"):
                others.add(record["pc"])  # type: ignore[arg-type]
                continue
            outside = [
                a
                for a in record["stack"]  # type: ignore[union-attr]
                if not STORE[0] <= a < STORE[1] and any(lo <= a < hi for lo, hi in CODE)
            ]
            if not outside:
                continue
            reader = outside[0]
            readers.setdefault(reader, set()).add(f"{session}: {record['what']}")
            hit = {site for site in sites for a in record["stack"] if 3 <= a - site <= 8}  # type: ignore[union-attr]
            executed |= hit
            if not hit:
                gaps.setdefault(reader, set()).add(f"{session}: {record['what']}")
    cache = out / "rig-pcs.json"
    if reuse and cache.exists():
        pcs = set(json.loads(cache.read_text()))
    else:
        pcs = live_view(block0)
        cache.write_text(json.dumps(sorted(pcs)))
    seen_bytes = {pc for pc in pcs if pc in byte_reads}
    lines = [
        f"full boot, {len(boot)} sessions: {sum(len(r) for r in boot.values())} distinct (pc, stack) reads of the watched bytes; Picture Mode bytes: {len(readers)} distinct readers (first code address on the stack outside the settings store)",
        f"static call sites (readers.py kind A): {len(sites)}; executed in the full boot: {len(executed)}; never executed: {len(sites) - len(executed)}",
        f"dynamic readers with no static call site on the stack (gap of the static list): {len(gaps)}",
    ]
    lines += [f"    gap {reader:#010x}: {'; '.join(sorted(what)[:3])}" for reader, what in sorted(gaps.items())]
    lines += [
        f"live-view rig: {len(pcs)} distinct instructions read the mov layer's mode and code bytes",
        f"static reads of those bytes (kind C, absolute address): {len(byte_reads)}; executed in the rig: {len(seen_bytes)}; never executed: {len(byte_reads) - len(seen_bytes)}",
        f"dynamic reads that the static list does not have: {len(pcs - set(byte_reads))}: " + " ".join(f"{pc:#010x}" for pc in sorted(pcs - set(byte_reads))),
        "static call sites never executed: " + " ".join(f"{site:#010x}" for site in sorted(set(sites) - executed)),
        "static byte reads never executed: " + " ".join(f"{pc:#010x}" for pc in sorted(set(byte_reads) - seen_bytes)),
    ]
    text = "\n".join(lines)
    print(text)
    (ROOT / "experiments/2026-11-16-films-max/results/readers-dynamic.txt").write_text(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
