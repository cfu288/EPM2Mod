#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Make the pinned firmware of this repository: download, patch, check. One command.

    uv run tools/make_firmware.py                       -> build/card/DCOLYMP/E1019999.BIN
    uv run tools/make_firmware.py --card /Volumes/NAME  -> the same, and copied to that SD card

The pinned build is the last build that was tested on a camera. pinned-build.json at the top of the
repository describes it: the stock firmware it starts from, the patch specs in order, and the sha256
the result must have. This script
  1. downloads the stock firmware from the maker's update catalog if it is not here yet
     (tools/fetch_stock.py), and checks its sha256,
  2. applies the specs with tools/build.py,
  3. compares the result with the pinned sha256, and deletes it if it differs,
  4. writes a copy under the name the camera looks for (DCOLYMP/E1019999.BIN),
  5. with --card, copies that file to the SD card and checks the copy.
Python standard library only; `uv run` gets a Python for you, or use `python3` in its place.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description="Make the pinned firmware: download, patch, check.")
    ap.add_argument("--card", metavar="PATH", help="mount point of the SD card, e.g. /Volumes/NAME; the firmware is copied to PATH/DCOLYMP/E1019999.BIN")
    a = ap.parse_args()
    pin = json.load(open(os.path.join(ROOT, "pinned-build.json")))
    base = os.path.join(ROOT, pin["base"])
    if a.card and not os.path.isdir(a.card):
        sys.exit(f"--card {a.card}: no such folder. Give the place where the SD card is mounted.")
    if not os.path.exists(base):
        print("1/4 the stock firmware is not here: downloading it")
        sys.path.insert(0, os.path.join(ROOT, "tools")); import fetch_stock
        fetch_stock.main()
    if sha256_of(base) != pin["base_sha256"]:
        sys.exit(f"{pin['base']} is not stock E-PM2 v1.6 (sha256 differs). Move it away and run this again.")
    print("1/4 stock firmware: ok")
    out = os.path.join(ROOT, "build", pin["name"] + ".BIN")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build.py"), *pin["specs"], "-o", out], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stdout[-2000:] + r.stderr[-2000:] + "\nbuild failed")
    print(f"2/4 applied {len(pin['specs'])} patch specs")
    got = sha256_of(out)
    if got != pin["sha256"]:
        os.remove(out)
        sys.exit(f"The result is not the pinned build.\n  expected {pin['sha256']}\n  got      {got}\nNothing was kept.")
    print(f"3/4 sha256 {got}: this is the pinned build")
    card = os.path.join(ROOT, "build", "card", "DCOLYMP")
    shutil.rmtree(os.path.join(ROOT, "build", "card"), ignore_errors=True)
    os.makedirs(card)
    shutil.copyfile(out, os.path.join(card, "E1019999.BIN"))
    print(f"4/4 {pin['name']}: {pin['what']} (camera-tested {pin['camera_tested']})")
    if a.card:
        dest = os.path.join(a.card, "DCOLYMP")
        os.makedirs(dest, exist_ok=True)
        others = [f for f in os.listdir(dest) if not f.startswith(".") and f != "E1019999.BIN"]
        if others:
            sys.exit(f"{dest} holds other files ({', '.join(others[:4])}). The firmware must be the only file there. Remove them and run this again.")
        shutil.copyfile(out, os.path.join(dest, "E1019999.BIN"))
        if sha256_of(os.path.join(dest, "E1019999.BIN")) != pin["sha256"]:
            sys.exit("The copy on the card is not the same as the firmware. Do not use the card. Try again, or try another card.")
        print(f"on the card: {os.path.join(dest, 'E1019999.BIN')}  (checked)\nEject the card. Then, with the camera off, hold OK and switch the camera on.")
    else:
        print("ready: build/card/DCOLYMP/E1019999.BIN\nCopy the DCOLYMP folder to the SD card, or run this again with --card and the card's mount point.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
