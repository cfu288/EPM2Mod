#!/usr/bin/env python3
"""Print the job tables of the E-PM2 still sequence (cam_still_func.c), fw 1.6.

A still phase (Ready, Take, ...) is described by a 12-byte record
{mask of job bits, pointer to table A, pointer to table B} at 0x7E7BD3B4-0x7E7BD47F.
Table A has one row per job bit: {bit, pointer to a list of step functions, count}.
A step function sends one request (sensor set command, shutter magnet, charge motor,
aperture, timer). Table B holds {bit, mask, kind} rows (links between jobs, not decoded).
This script prints table A of every record and names the steps that were decoded by
hand (NOTES.md, section 1).

Usage: still_steps.py BLOCK0
"""
import struct
import sys

BASE = 0x7E421020
NAMES = {
    0x7E657940: "SET abort(17)", 0x7E657952: "SET sleep(18)", 0x7E657964: "COM_SET list A", 0x7E657976: "COM_SET list B",
    0x7E657985: "SENSOR EXP_START(83)", 0x7E657997: "SENSOR EXP_START(83)b", 0x7E6579A9: "COM_SET list C",
    0x7E6579BB: "COM_SET list D", 0x7E6579CD: "SENSOR EXP_STOP(84)", 0x7E6579DF: "COM_SET list E",
    0x7E6579F1: "SET wakeup(19)", 0x7E657A00: "COM_SET list F", 0x7E657A0F: "SENSOR EXP_STBY(88)",
    0x7E657A1E: "SENSOR EXP_STBY(88)b", 0x7E657A2D: "SENSOR EXP_CANCEL(89)", 0x7E657A3C: "SENSOR CONT_EXP_START(87)",
    0x7E657A4E: "set 92", 0x7E657A5D: "set 91", 0x7E657A6F: "SET wakeup(19)b", 0x7E657A7E: "SET wakeup(19)c",
    0x7E657A8D: "set 93", 0x7E657A9F: "set 94", 0x7E657AB1: "set 95", 0x7E657ACD: "set 96", 0x7E657ADF: "set 97",
    0x7E657AF1: "MOTOR OPENRDY (MI 6)", 0x7E657B03: "TIMER 4", 0x7E657B1D: "MOTOR OPENCHG (MI 5)",
    0x7E657B2F: "MOTOR OPENCHG (MI 5)b", 0x7E657B41: "MOTOR F_OPCHG (MI 150)", 0x7E657B53: "MOTOR F_READY (MI 149)",
    0x7E657B65: "MOTOR (MI 146)", 0x7E657B77: "MAGNET ON (SH 147)", 0x7E657B89: "MAGNET MG3_CHG (SH 149)",
    0x7E657B9B: "MAGNET SET or START (SH 7/11)", 0x7E657C19: "TIMER 5", 0x7E657C2E: "TIMER 5b",
    0x7E657873: "MAGNET STOP if curtain flag (SH 12) + flag 0x400", 0x7E6578E3: "MAGNET STOP if curtain flag (SH 12)",
    0x7E657928: "default: error 15492", 0x7E65793C: "nop",
}


def main():
    d = open(sys.argv[1], "rb").read()

    def words(a, n):
        return struct.unpack_from("<%dI" % n, d, a - BASE)

    for rec in range(0x7E7BD3B4, 0x7E7BD480, 12):
        mask, ta, tb = words(rec, 3)
        print("record %08x  mask %08x  table A %08x  table B %08x" % (rec, mask, ta, tb))
        a = ta
        while True:
            bit, lst, cnt = words(a, 3)
            if bit == 0xFFFFFFFF:
                break
            steps = words(lst, cnt) if cnt else ()
            txt = "; ".join("%08x %s" % (w, NAMES.get(w, "")) if w else "0" for w in steps)
            print("  bit %08x  %s" % (bit, txt.strip()))
            a += 12


main()
