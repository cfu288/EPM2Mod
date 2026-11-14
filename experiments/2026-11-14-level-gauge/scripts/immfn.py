"""immfn.py MAP_DIR VALUE [VALUE...]: functions that contain an instruction with the immediate VALUE
(as 'mov V,' / 'cmp V,' / 'add V,'), with the lines."""
import sys, re
vals = sys.argv[2:]
pat = re.compile(r"\t(mov|cmp|add|movu?)\t(%s),(\w+)" % "|".join(vals))
cur = None
for l in open(sys.argv[1] + "/functions.txt", errors="replace"):
    if l.endswith(">:\n"): cur = l[:8]; continue
    if pat.search(l): print(cur, l.strip().replace("\t", " "))
