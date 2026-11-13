#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Make a firmware build from its description: download, patch, check. The one way firmware is made here.

    uv run tools/make_firmware.py                               the pinned build -> build/card/DCOLYMP/E1019999.BIN
    uv run tools/make_firmware.py --card /Volumes/NAME          the same, and copied to that SD card
    uv run tools/make_firmware.py builds/NAME.json              another build (a tested one, or a new candidate)
    uv run tools/make_firmware.py builds/NAME.json --pin DATE   after a camera test on DATE (YYYY-MM-DD): record the
                                                                sha256 and the date, and make this the pinned build

A build description (builds/*.json) names the stock firmware, the patch specs in order and, once the
build has been tested on a camera, the sha256 of the result and the date. pinned-build.json at the top
of the repository names the description of the last build that was tested on a camera.

Steps:
  1. the stock firmware: downloaded from the maker's update catalog if it is not here (tools/fetch_stock.py),
     and its sha256 checked;
  2. for a candidate: tools/freespace.py check on the spec list (two specs on the same bytes, or bytes where
     the camera does not load the firmware, stop the build). It needs the firmware map under build/map/.
     A tested build skips this, because step 4 compares it with the recorded sha256;
  3. the specs applied with tools/build.py;
  4. the sha256 of the result: for a tested build it must be the recorded one, or the result is deleted;
     for a candidate it is printed, with a reminder that the build is not tested;
  5. a copy under the name the camera looks for (DCOLYMP/E1019999.BIN); with --card, also on the SD card,
     and the copy checked.
Python standard library only; `uv run` gets a Python for you, or use `python3` in its place.
"""
import argparse, datetime, hashlib, json, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIN = os.path.join(ROOT, "pinned-build.json")
CARD_NAME = "E1019999.BIN"


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def run(*args):
    return subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser(description="Make a firmware build from its description: download, patch, check.")
    ap.add_argument("build", nargs="?", help="build description (builds/NAME.json); default: the pinned build")
    ap.add_argument("--card", metavar="PATH", help="mount point of the SD card, e.g. /Volumes/NAME; the firmware is copied to PATH/DCOLYMP/" + CARD_NAME)
    ap.add_argument("--pin", metavar="DATE", help="the build passed a camera test on DATE (YYYY-MM-DD): record its sha256 and the date in the description and make it the pinned build")
    a = ap.parse_args()
    if a.pin:
        if not a.build:
            sys.exit("--pin needs the build description that was tested")
        datetime.date.fromisoformat(a.pin)
    desc_rel = a.build or json.load(open(PIN))["build"]
    desc_path = desc_rel if os.path.isabs(desc_rel) else os.path.join(ROOT, desc_rel) if not os.path.exists(desc_rel) else os.path.abspath(desc_rel)
    d = json.load(open(desc_path))
    tested = bool(d.get("sha256")) and bool(d.get("camera_tested"))
    if a.card and not os.path.isdir(a.card):
        sys.exit(f"--card {a.card}: no such folder. Give the place where the SD card is mounted.")
    for spec in d["specs"]:
        if not os.path.exists(os.path.join(ROOT, spec)):
            sys.exit(f"{desc_rel}: spec not found: {spec}")
    base = os.path.join(ROOT, d["base"])
    if not os.path.exists(base):
        print("1/5 the stock firmware is not here: downloading it")
        sys.path.insert(0, os.path.join(ROOT, "tools")); import fetch_stock
        fetch_stock.main()
    if sha256_of(base) != d["base_sha256"]:
        sys.exit(f"{d['base']} is not the stock firmware this build starts from (sha256 differs). Move it away and run this again.")
    print("1/5 stock firmware: ok")
    if tested:
        print("2/5 free-space check: not needed, the result is compared with the recorded sha256")
    else:
        r = run(os.path.join("tools", "freespace.py"), "check", *d["specs"])
        if r.returncode:
            hint = "" if os.path.exists(os.path.join(ROOT, "build", "map", "linear.txt")) else \
                "\nThe firmware map is missing (build/map/). The check needs it for a new build: see tools/fwmap.py and tools/freespace.py."
            sys.exit((r.stdout + r.stderr)[-3000:] + "\n2/5 the free-space check failed: nothing was built" + hint)
        print("2/5 free-space check: " + (r.stdout.strip().splitlines() or ["ok"])[-1])
    out = os.path.join(ROOT, "build", d["name"] + ".BIN")
    r = run(os.path.join("tools", "build.py"), *d["specs"], "-o", out)
    if r.returncode:
        sys.exit((r.stdout + r.stderr)[-3000:] + "\nbuild failed")
    print(f"3/5 applied {len(d['specs'])} patch specs")
    got = sha256_of(out)
    if d.get("sha256") and got != d["sha256"]:
        os.remove(out)
        sys.exit(f"The result is not the recorded build.\n  expected {d['sha256']}\n  got      {got}\nNothing was kept.")
    if tested:
        print(f"4/5 sha256 {got}: this is the build that was tested on {d['camera_tested']}")
    else:
        print(f"4/5 sha256 {got}\n    CANDIDATE: this build is NOT camera-tested. Write the sha256 in docs/camera-log.md before you flash it.")
    card = os.path.join(ROOT, "build", "card", "DCOLYMP")
    shutil.rmtree(os.path.join(ROOT, "build", "card"), ignore_errors=True)
    os.makedirs(card)
    shutil.copyfile(out, os.path.join(card, CARD_NAME))
    print(f"5/5 {d['name']}: {d['what']}\n    firmware: build/{d['name']}.BIN    for the card: build/card/DCOLYMP/{CARD_NAME}")
    if a.card:
        dest = os.path.join(a.card, "DCOLYMP")
        os.makedirs(dest, exist_ok=True)
        others = [f for f in os.listdir(dest) if not f.startswith(".") and f != CARD_NAME]
        if others:
            sys.exit(f"{dest} holds other files ({', '.join(others[:4])}). The firmware must be the only file there. Remove them and run this again.")
        shutil.copyfile(out, os.path.join(dest, CARD_NAME))
        if sha256_of(os.path.join(dest, CARD_NAME)) != got:
            sys.exit("The copy on the card is not the same as the firmware. Do not use the card. Try again, or try another card.")
        print(f"on the card: {os.path.join(dest, CARD_NAME)}  (checked)\nEject the card. Then, with the camera off, hold OK and switch the camera on.")
    if a.pin:
        d["sha256"], d["camera_tested"] = got, a.pin
        with open(desc_path, "w") as f:
            json.dump(d, f, indent=1); f.write("\n")
        with open(PIN, "w") as f:
            json.dump({"build": os.path.relpath(desc_path, ROOT)}, f, indent=1); f.write("\n")
        print(f"pinned: {os.path.relpath(desc_path, ROOT)} (camera-tested {a.pin}). Commit the description and pinned-build.json, and update the README's build name and sha256.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
