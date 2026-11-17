"""Check an unpacked release folder the way a user starts it: the launcher of this system.

    python release_smoke.py FOLDER EXPECTED_SHA256

1. `LAUNCHER make` gets uv and Python, downloads OM's firmware and makes the pinned build: its sha256 must be the
   expected one.
2. `LAUNCHER cards` lists the cards (the runner has none) without an error.
3. `LAUNCHER serve --no-browser` serves the page, and the API answers with the token and refuses without it.
"""

import os
import re
import subprocess
import sys
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


def run(*args: str) -> str:
    done = subprocess.run(launcher + list(args), cwd=folder, capture_output=True, text=True, timeout=900)
    print(done.stdout + done.stderr)
    if done.returncode:
        sys.exit(f"{' '.join(args)}: exit {done.returncode}")
    return done.stdout


made = run("make")
if f"4/5 sha256 {expected}" not in made:
    sys.exit(f"make: the sha256 is not {expected}")
if not (folder / "build" / "card" / "DCOLYMP" / "E1019999.BIN").is_file():
    sys.exit("make: no build/card/DCOLYMP/E1019999.BIN")
run("cards")

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
