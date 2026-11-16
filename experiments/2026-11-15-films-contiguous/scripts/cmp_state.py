"""cmp_state.py DIR_A DIR_B START.json...: compare the settings states (E101_STATE files) of two folders by name.

A state file has the flash writes of the settings store and the RAM images of the settings banks. Two states are
equal when every part is byte-equal. The START files are the states the runs began with: a state that is equal
to its start state means the keys changed nothing, and it is reported. Exit 0 = all pairs equal.
"""

import base64
import json
import sys
from pathlib import Path


def parts(path: Path) -> dict[str, bytes]:
    """Return the named byte strings of a state file."""
    state = json.loads(path.read_text())
    out = {f"ram:{k}": base64.b64decode(v) for k, v in state["ram"].items()}
    for address, data in state["flash"]:
        out[f"flash:{address:#x}"] = base64.b64decode(data)
    return out


def main() -> int:
    """Compare and print."""
    a, b = Path(sys.argv[1]), Path(sys.argv[2])
    starts = [parts(Path(p)) for p in sys.argv[3:]]
    names = sorted(p.name for p in a.glob("*.json"))
    differ = unchanged = 0
    for name in names:
        pa, pb = parts(a / name), parts(b / name)
        bad = [k for k in sorted(set(pa) | set(pb)) if pa.get(k) != pb.get(k)]
        if bad:
            differ += 1
            detail = [f"{k} {sum(x != y for x, y in zip(pa.get(k, b''), pb.get(k, b'')))} bytes" for k in bad]
            print(f"DIFFERENT {name}: {', '.join(detail)}")
        if any(pa["ram:mode"] == s["ram:mode"] for s in starts):
            unchanged += 1
            print(f"no change from the start state: {name}")
    print(f"{len(names)} pairs: {differ} differ; {unchanged} runs changed nothing")
    return 1 if differ else 0


if __name__ == "__main__":
    sys.exit(main())
