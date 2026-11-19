"""stored_values.py DIR: print the stored Picture Mode value of every settings state DIR/*.json.

The value is byte 51880 of the mode bank's RAM image in a state file of emulator (found by choosing each entry
on the pinned build: it reads 100 to 109, 119, 120 there). Byte 76 is the art code of ART mode (setting 281).
"""

import base64
import json
import sys
from pathlib import Path

for path in sorted(Path(sys.argv[1]).glob("*.json")):
    bank = base64.b64decode(json.loads(path.read_text())["ram"]["mode"])
    print(f"{path.stem}: Picture Mode value {bank[51880]}, ART mode code {bank[76]}")
