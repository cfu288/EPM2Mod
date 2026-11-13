#!/usr/bin/env python3
"""Emulator check (om-emu, tools/emu): the two readers of the 30-entry command table 0x7EBF0FA0 never
read the unreferenced name list 0x7EBF1090-0x7EBF3BAD that follows it.

    python3 emu_sdktable.py            # needs the om-emu setup of tools/emu/README.md

Lookup 0x7E99BAE5(d0 = argc, a0 = argv) runs natively with strcmp/memset; print, sprintf, sscanf, the
object getter and the 30 handlers are stubs. Help 0x7E99CF3A runs the same way. A logging read watch
covers the candidate; a second one covers the table itself as a positive control.
"""
import os, struct, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "emu"))
import omemu

TABLE, N = 0x7EBF0FA0, 30
CAND = (0x7EBF1090, 0x7EBF3BAD)
LOOKUP, HELP = 0x7E99BAE5, 0x7E99CF3A
STUBS = (0x7E4FFDE3, 0x7E4263E5, 0x7E4FFDFE, 0x7E9A0317)   # sprintf, print, sscanf, object getter


class Emu(omemu.Emu):
    """Handlers are reached by `calls (a1)`: no register list, no frame, so the stub returns with retf [],0."""
    indirect = set()

    def _return_form(self, stub, mdr):
        return (0, 0) if stub in self.indirect else super()._return_form(stub, mdr)


def main():
    omemu.check_stock()
    img = open(omemu.STOCK_BLOCK0, "rb").read()
    B = 0x7E421020
    ents = [struct.unpack_from("<II", img, TABLE - B + 8 * i) for i in range(N)]
    names = [img[s - B:img.index(b"\0", s - B)].decode() for s, _ in ents]
    extra = ["M71", "getReleaseSetting", "A**:", "B**: SettingController", "", "zzz", "t09", "dbggri", "dbggridx"]
    hit = []
    stubs = {a: (lambda e, r: {"d0": 0, "a0": 0}) for a in STUBS}
    for _, f in ents:
        stubs[f] = lambda e, r, f=f: hit.append(f) or {"d0": 0}
    Emu.indirect = {f for _, f in ents}
    with Emu() as e:
        e.load(omemu.STOCK_BLOCK0)
        e.req("watch", list=[{"id": 1, "addr": CAND[0], "len": CAND[1] - CAND[0], "kind": "r", "action": "log"},
                             {"id": 2, "addr": TABLE, "len": 8 * N, "kind": "r", "action": "log"}])
        bad = 0
        for k, name in enumerate(names + extra):
            argv, s0, s1 = omemu.DATA, omemu.DATA + 0x100, omemu.DATA + 0x200
            e.write(s0, b"sdk\0")
            e.write(s1, name.encode() + b"\0")
            e.write(argv, struct.pack("<II", s0, s1))
            del hit[:]
            e.call(LOOKUP, regs={"d0": 2, "a0": argv}, stubs=stubs)
            want = [ents[names.index(name)][1]] if name in names else []
            if hit != want:
                bad += 1
                print("MISMATCH", name, [hex(h) for h in hit], [hex(w) for w in want])
        e.call(HELP, regs={"d0": 1, "a0": omemu.DATA}, frame=(0, 0), stubs=stubs)
        log = e.req("watchLog")
        ents_l = log["entries"]
        c1 = sum(1 for x in ents_l if x["id"] == 1)
        c2 = sum(1 for x in ents_l if x["id"] == 2)
        print(f"inputs: {len(names)} table names + {len(extra)} others + help; dispatch mismatches: {bad}")
        print(f"reads logged in the table 0x{TABLE:08X}+{8 * N}: {c2}; reads in the candidate "
              f"0x{CAND[0]:08X}-0x{CAND[1]:08X}: {c1}; dropped {log.get('dropped')}, more {log.get('more')}")
        return 1 if (bad or c1 or not c2) else 0


if __name__ == "__main__":
    sys.exit(main())
