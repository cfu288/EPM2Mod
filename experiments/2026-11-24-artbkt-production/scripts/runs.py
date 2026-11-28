"""ART BKT runs in the emulator for NOTES.md section 3: n = 0, 1, 3, a Picture Mode row, the end screens.

    uv run python experiments/2026-11-24-artbkt-production/scripts/runs.py WORK [NAME...]

Research code. Each run: the build's P state (build/emu/state/artbkt-p.json, emulator/mkstate), the card of
emulator/artbkt-test (WORK/card: PB130001.ORF with a marker ImageDescription, ART 1 Portra 400, ART 2 Velvia), Load
Looks, the ART BKT rows set through Shooting Menu 2 > Bracketing > ART BKT, then RAW Data Edit > ART BKT > Yes.
Prints the run's events and each JPEG's ImageDescription; screenshots and logs in WORK/NAME/.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "emulator"))
import importlib.machinery  # noqa: E402

test = importlib.machinery.SourceFileLoader("artbkt_test", os.path.join(ROOT, "emulator", "artbkt-test")).load_module()

DEFAULT_ON = set(range(12))  # an empty settings store: the 12 ART entries On, the 7 Picture Mode rows Off
TO_SCREEN = "key:MENU key:RIGHT key:OK key:DOWN key:RIGHT key:DOWN key:DOWN key:RIGHT" + " key:DOWN" * 4 + " key:RIGHT key:DOWN key:RIGHT"
RUNS = {  # name: (rows On, 0 = Pop Art ... 11 = Watercolor, 12 = i-Enhance ... 18 = Custom; extra steps at the end)
    "n0": (set(), "shot:end"),
    "n1": ({11}, "shot:end key:UP w:300 shot:end-up key:OK w:1500 shot:after-reset"),
    "n3": ({1, 5, 17}, "shot:end"),
    "natural": ({0, 14}, "shot:end"),
}
# plain RAW Data Edit runs (no ART BKT): name -> steps after Load Looks
EDIT = "w:500 key:PLAY w:1500 key:OK w:800 key:OK w:1500"
PLAIN = {
    # Picture Mode ART 1 (Portra 400: from Natural 5 to the right in the live control strip), then Current
    "current-portra": "key:OK w:300 key:UP" + " key:RIGHT" * 5 + " shot:pm key:OK w:500 " + EDIT + " key:OK w:8000 key:OK w:15000",
    "custom1": EDIT + " key:DOWN w:300 key:OK w:8000 key:OK w:15000",
}


def rows(on):
    """Return the steps that set the ART BKT rows from the defaults to ``on``, with screenshots."""
    steps = TO_SCREEN.split() + ["shot:bkt-0"]
    for i in range(19):
        if (i in on) != (i in DEFAULT_ON):
            steps += ["key:RIGHT", "key:DOWN" if i in on else "key:UP", "key:OK"]
        if i < 18:
            steps.append("key:DOWN")
    return steps + ["shot:bkt-1", "key:MENU", "shot:bracketing", "key:MENU", "shot:bracketing-closed", "key:MENU", "key:MENU", "w:500", "shot:live"]


def main(argv):
    work = os.path.abspath(argv[0])
    card = os.path.join(work, "card")
    if not os.path.isdir(card):
        sys.exit(f"{card}: run emulator/artbkt-test data/builds/artbkt.json --keep {work} first")
    spec = os.path.join(ROOT, "data", "specs", "raw-edit-art-bkt-3.json")
    for name in argv[1:] or [*RUNS, *PLAIN]:
        on, end = RUNS.get(name, (set(), ""))
        out = os.path.join(work, name)
        shutil.rmtree(out, ignore_errors=True)
        os.makedirs(out)
        shutil.copy(os.path.join(ROOT, "build", "emu", "state", "artbkt-p.json"), os.path.join(out, "state.json"))
        env = {"E101_STATE": os.path.join(out, "state.json"), "E101_CARD": card, "E101_RTC": test.RTC, "SYMS": spec,
               "STANDIN": "1", "HEADS": os.path.join(out, "heads"), "SHOTS": out}
        steps = ["w:500", *test.LOAD, *(PLAIN[name].split() if name in PLAIN else rows(on) + test.RUN + end.split())]
        done = test.emuenv.run_tool("artbkt.mjs", os.path.join(ROOT, "build", "artbkt.BIN"), steps, env)
        open(os.path.join(out, "run.log"), "w").write(done.stdout + done.stderr)
        print(f"== {name}: rows On {sorted(on)}, exit {done.returncode}")
        for line in done.stdout.splitlines():
            if any(k in line for k in ("CB cmd", "SETUP list", "STOP", "PRM_SET 0x9481", "save_current_start", '"end"')):
                print("  " + line[:300])
        heads = os.path.join(out, "heads")
        for f in sorted(os.listdir(heads)) if os.path.isdir(heads) else []:
            print(f"  {f}: {test.image_description(open(os.path.join(heads, f), 'rb').read())!r}")


if __name__ == "__main__":
    main(sys.argv[1:])
