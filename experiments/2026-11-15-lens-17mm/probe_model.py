#!/usr/bin/env python3
"""Compare stock and proposed changes in memory; never write a firmware image."""

import argparse
import hashlib
import json
from pathlib import Path

from inspect_image import EXPECTED, inspect
from leaf_machine import LeafMachine

PROPOSALS = {
    'stock': [],
    'fast-high-adc': [(0x2AE28, b'\x0a', b'\x0b')],
    'lower-drive-high-adc': [(0x2AE3A, b'\x05', b'\x04')],
    'timing-400': [(0x59F2, b'\x4d\x01', b'\x90\x01')],
}


def compare(path):
    inspect(path)
    payload = path.read_bytes()[32:-32]
    results = []
    for name, changes in PROPOSALS.items():
        data = bytearray(payload)
        for offset, before, after in changes:
            assert data[offset:offset+len(before)] == before
            data[offset:offset+len(after)] = after
        cases = []
        for adc in (220,250,320,400):
            for steps in (1,100,1000):
                for direction in (0,1):
                    machine = LeafMachine(data)
                    machine.adc = adc
                    machine.reg('R0',steps)
                    machine.reg('R1L',direction)
                    words = machine.run(0x59D0)
                    low = next(w & 1023 for w in words if w >> 10 == 1)
                    high = next(w & 1023 for w in words if w >> 10 == 2)
                    assert (high << 10) | low == steps*32
                    assert words[-1] == 0x3E00
                    cases.append({
                        'adc':adc, 'steps':steps, 'direction':direction,
                        'selected_timing':machine.memory(0x5FC,2),
                        'driver_words':[f'{w:04x}' for w in words],
                        'executed_instructions':len(machine.trace),
                    })
        results.append({
            'name':name,
            'changes':[{'payload_offset':hex(o),'file_offset':hex(o+32),
                        'before':b.hex(),'after':a.hex()} for o,b,a in changes],
            'cases':cases,
        })
    return {'stock_sha256':EXPECTED,
            'modeled_entry':'0x59d0',
            'hooks':{'0x650':'fixed ADC result', '0x6ca4':'capture serial word; R2R0=1',
                     '0x6e88':'short delay omitted'},
            'limitations':['No motor, interrupt or acoustic model',
                           'No claim about achieved focus speed, torque or sound',
                           'Proposals are not flashable builds'],
            'results':results}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('image',type=Path)
    args = ap.parse_args()
    print(json.dumps(compare(args.image),indent=2))
