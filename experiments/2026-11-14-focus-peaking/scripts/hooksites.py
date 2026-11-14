"""Print every hook site of a spec before (base block 0) and after (patched block 0), with objdump.

Usage: hooksites.py SPEC.json BASE_BLOCK0 PATCHED_BLOCK0
Each site is decoded from its first replaced byte to the end of the first instruction that starts at or
after the last replaced byte, so the listing shows where the stock code continues.
"""
import json, os, re, subprocess, sys
B = 0x7E421020
OD = os.path.expanduser("~/opt/mn10300/bin/mn10300-elf-objdump")


def dis(path, a, n):
    r = subprocess.run([OD, "-D", "-b", "binary", "-m", "am33-2", "-EL", "--adjust-vma=%#x" % B,
                        "--start-address=%#x" % a, "--stop-address=%#x" % (a + n), path],
                       capture_output=True, text=True, check=True).stdout
    return [l.rstrip() for l in r.splitlines() if re.match(r"^\s*[0-9a-f]+:\t", l)]


spec = json.load(open(sys.argv[1]))
for op in spec["ops"]:
    if not op["_why"].startswith("hook"):
        continue
    a, n = B + int(op["offset"], 16), len(op["new"]) // 2
    print("%s  (%d bytes)  %s" % (op["_addr"], n, op["_why"]))
    for tag, path in (("before", sys.argv[2]), ("after", sys.argv[3])):
        print("  " + tag)
        for l in dis(path, a, n + 6):
            if int(l.split(":")[0], 16) <= a + n:
                print("    " + l.strip())
    print()
