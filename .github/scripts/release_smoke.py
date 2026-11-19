"""Check an unpacked release folder the way a user starts it: the launcher of this system.

    python release_smoke.py FOLDER EXPECTED_SHA256

A folder with a DCIM folder stands in for the SD card (EPM2MOD_TEST_CARDS lists it as a card).

1. `LAUNCHER install --card CARD --dry-run --json` names the pinned build's sha256 and writes nothing.
2. `LAUNCHER install --card CARD --json` gets uv and Python, downloads OM's firmware, makes the pinned build and
   writes it to the card (no --film: no film file): its sha256 must be the expected one.
3. `LAUNCHER inspect --card CARD --json` finds that build and nothing that will not work.
4. `LAUNCHER cards --json` lists the stand-in card. `LAUNCHER make BUILD` refuses with exit 6: no checkout.
5. `LAUNCHER serve --no-browser` serves the page, and the API answers with the token and refuses without it.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

folder, expected = Path(sys.argv[1]).resolve(), sys.argv[2]
if sys.platform == "win32":
    # run the batch file directly, as a double-click does (cmd /c would mangle the parentheses in its name)
    launcher = [str(folder / "Start (Windows).bat")]
elif sys.platform == "darwin":
    launcher = [str(folder / "Start (Mac).command")]
else:
    launcher = [str(folder / "start.sh")]

card = Path(tempfile.mkdtemp()) / "CARD"
(card / "DCIM").mkdir(parents=True)
env = {**os.environ, "EPM2MOD_TEST_CARDS": str(card)}


def run(*args: str, status: int = 0) -> str:
    done = subprocess.run(launcher + list(args), cwd=folder, env=env, capture_output=True, text=True, timeout=900)
    print(done.stdout + done.stderr)
    if done.returncode != status:
        sys.exit(f"{' '.join(args)}: exit {done.returncode}, expected {status}")
    return done.stdout


def document(*args: str) -> dict:
    found = json.loads(run(*args, "--json"))
    if found.get("schema") != 2 or found.get("ok") is not True:
        sys.exit(f"{' '.join(args)}: not a schema 2 document of a success")
    return found


planned = document("install", "--card", str(card), "--dry-run")
if planned["files"][0]["sha256"] != expected or list(card.rglob("*.BIN")):
    sys.exit("install --dry-run: the wrong sha256, or it wrote a file")
installed = document("install", "--card", str(card))
if installed["files"][0]["sha256"] != expected:
    sys.exit(f"install: the sha256 is not {expected}")
if not (card / "DCOLYMP/E1019999.BIN").is_file() or (card / "EPM2LOOK.BIN").exists():
    sys.exit("install: the card does not hold the firmware only")
inspected = document("inspect", "--card", str(card))
if inspected["files"][0]["sha256"] != expected or inspected["problems"]:
    sys.exit(f"inspect: {inspected}")
if [found["path"] for found in document("cards")["cards"]] != [str(card)]:
    sys.exit("cards: the stand-in card is not listed")
run("make", installed["build"]["name"], status=6)

server = subprocess.Popen(
    launcher + ["serve", "--no-browser", "--port", "8765"],
    cwd=folder,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
try:
    line = ""
    deadline = time.time() + 300
    while "token=" not in line and time.time() < deadline:
        line = server.stdout.readline()
        print(line, end="")
        if not line and server.poll() is not None:
            sys.exit("serve ended before it printed its address")
    token = re.search(r"#token=([\w-]+)", line).group(1)

    def get(path: str, token: str) -> int:
        request = urllib.request.Request(f"http://127.0.0.1:8765{path}", headers={"X-EPM2-Token": token})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status
        except urllib.error.HTTPError as error:
            return error.code

    results = {"page": get("/", ""), "build": get("/api/build", token), "no token": get("/api/build", "")}
    print(results)
    if results != {"page": 200, "build": 200, "no token": 403}:
        sys.exit("serve: wrong answers")
finally:
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(server.pid)], capture_output=True)
    else:
        server.terminate()
    server.wait(timeout=60)
print("release smoke test: PASS")
