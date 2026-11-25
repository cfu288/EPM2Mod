"""Print the specs of each release tag's pinned build, and what each release added.

Run from the repository root: uv run python experiments/2026-11-24-slow-boot/scripts/release_specs.py
"""

import json
import subprocess


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


tags = git("tag", "--sort=creatordate").split()
prev: list[str] = []
prev_blobs: dict[str, str] = {}
for tag in tags:
    files = git("ls-tree", "--name-only", "-r", tag).split()
    pin = "data/pinned-build.json" if "data/pinned-build.json" in files else "pinned-build.json"
    build = json.loads(git("show", f"{tag}:{pin}"))["build"]
    desc = json.loads(git("show", f"{tag}:{build}"))
    specs = desc.get("specs", [])
    date = git("log", "-1", "--format=%ci", tag).strip()
    print(f"== {tag} {date} {build}")
    print("   added:", [s for s in specs if s not in prev])
    print("   removed:", [s for s in prev if s not in specs])
    # same spec name, other content: a changed spec counts as added
    blobs = {s: git("rev-parse", f"{tag}:{s}").strip() for s in specs}
    print("   changed:", [s for s in specs if s in prev_blobs and prev_blobs[s] != blobs[s]])
    prev_blobs = blobs
    prev = specs
