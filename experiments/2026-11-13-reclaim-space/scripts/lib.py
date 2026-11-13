"""Helpers on top of reach.py: load the pickle, list references into a range, run cut experiments."""
import bisect, os, pickle, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reach
from reach import seg_of, BASE


class DB:
    def __init__(self, pkl):
        d = pickle.load(open(pkl, "rb"))
        self.A, self.M, self.T, self.roots, self.raw, self.fstart = d["A"], d["M"], d["T"], d["roots"], d["raw"], d["fstart"]
        self.data = open(reach.BLK, "rb").read()
        self.by_t = sorted((t, s, k) for k, s, t in self.raw)
        self.dec = sorted([(t, s, "dec") for s, ts in self.T.items() for t in ts] + [(t, s, "dec") for s, t in self.roots])
        self._live = {}

    def live(self, kinds=("win",), **kw):
        key = (kinds, repr(sorted(kw.items())))
        if key not in self._live:
            self._live[key] = reach.run(self.A, self.M, self.T, self.roots, self.raw, kinds, **kw)
        return self._live[key]

    def is_live(self, a, live):
        i = bisect.bisect_right(self.A, a) - 1
        return bool(live[i]) if seg_of(a) else True

    def refs(self, lo, hi, kinds=("win", "dec", "ph")):
        """All references with target in [lo, hi): (target, source, kind)."""
        out = []
        for lst in (self.by_t, self.dec):
            i = bisect.bisect_left(lst, (lo,))
            while i < len(lst) and lst[i][0] < hi:
                if lst[i][2] in kinds:
                    out.append(lst[i])
                i += 1
        return sorted(out)

    def dead_bytes(self, live, lo=None, hi=None):
        return [(a, b) for a, b, i, j in reach.dead_runs(self.A, live) if (lo is None or a >= lo) and (hi is None or b <= hi)]

    def fn_of(self, a):
        s = sorted(self.fstart) if not hasattr(self, "_fs") else self._fs
        self._fs = s
        return s[bisect.bisect_right(s, a) - 1]

    def rd(self, a, n=4):
        return self.data[a - BASE:a - BASE + n]
