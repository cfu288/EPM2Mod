"""Independent encoding examples and driver-word checks for the lens research."""

import unittest
from pathlib import Path

from leaf_machine import LeafMachine
from probe_model import compare
from r32c import Decoder, Unknown
import struct

IMAGE = Path(__file__).parent/'out/OL100211.BIN'


class EncodingTests(unittest.TestCase):
    def test_vendor_listing(self):
        # jbkim/R32C-Web-Server, Debug/ncrt0.lst, lines 154,155,219,236.
        vectors = [
            ('b28c0010fdff','MOV.L','#0xfffd1000, A0'),
            ('b2a80004','MOV.L','#0x400, A1'),
            ('cf','REIT',''),
        ]
        for raw,mn,args in vectors:
            ins = Decoder(bytes.fromhex(raw)).decode(0)
            self.assertEqual((ins.size,ins.mnemonic,ins.args),(len(bytes.fromhex(raw)),mn,args))

    def test_conflicting_formats(self):
        # REJ09B0267-0100: BTST:S p195; JCnd p232; EXTZ p227.
        vectors = [('67c103','BTST','6, [0x3c1]'),
                   ('2304','JNE','0x5'),
                   ('3f3109f8','EXTZ.BL','-0x8[FB], R2R0'),
                   ('a400','INDEX1.B','R0L')]
        for raw,mn,args in vectors:
            ins = Decoder(bytes.fromhex(raw)).decode(0)
            self.assertEqual((ins.mnemonic,ins.args),(mn,args))

    def test_source_then_destination_displacements(self):
        ins = Decoder(bytes.fromhex('a5b1036005')).decode(0)
        self.assertEqual(ins.args,'+0x3[A0], [0x560]')
        ins = Decoder(bytes.fromhex('b4ad60053d05')).decode(0)
        self.assertEqual(ins.args,'[0x560], [0x53d]')

    def test_unknown_does_not_advance(self):
        with self.assertRaises(Unknown):
            Decoder(bytes.fromhex('3fffff')).decode(0)


@unittest.skipUnless(IMAGE.exists(),'download the stock image first')
class DriverTests(unittest.TestCase):
    def test_low_adc_gate_still_prevents_start(self):
        payload = IMAGE.read_bytes()[32:-32]
        for offset,new in ((None,None),(0x2AE28,11),(0x2AE3A,4)):
            data = bytearray(payload)
            if offset is not None:
                data[offset] = new
            machine = LeafMachine(data)
            machine.adc = 180
            machine.reg('R0',100)
            machine.reg('R1L',1)
            self.assertEqual(machine.run(0x59D0),[0x30])
            self.assertTrue(machine.memory(0x5FE,1) & 1)

    def test_high_adc_boundary(self):
        payload = IMAGE.read_bytes()[32:-32]
        for adc,timing in ((377,357),(378,333)):
            data = bytearray(payload)
            data[0x2AE28] = 11
            machine = LeafMachine(data)
            machine.adc = adc
            machine.reg('R0',100)
            machine.reg('R1L',1)
            machine.run(0x59D0)
            self.assertEqual(machine.memory(0x5FC,2),timing)

    def test_timing_profile_against_independent_calculation(self):
        payload = IMAGE.read_bytes()[32:-32]
        for timing in (300,333,400,1000,1667,2000,40000):
            machine = LeafMachine(payload)
            machine.reg('R0',timing)
            words = machine.run(0x5D74)
            ticks = (min(timing,32767)*130208)//1000000
            if timing >= 1667:
                expected = [base|ticks for base in (0xC00,0x1800,0x1C00,0x2000,0x2400)]
                expected += [0x1290,0x2830]
            else:
                delta = (217-ticks)//2
                p6 = 217-delta
                delta //= 2
                p7 = p6-delta
                delta //= 2
                p8 = p7-delta
                expected = [0xCD9,0x2400|ticks,0x1800|p6,0x1C00|p7,
                            0x2000|p8,0x1290,0x1480,0x2830]
            self.assertEqual(words,expected)

    def test_proposals_change_only_the_expected_fields(self):
        report = compare(IMAGE)
        self.assertEqual(sum(len(x['cases']) for x in report['results']),96)
        stock = report['results'][0]['cases']
        for variant in report['results'][1:]:
            for before,after in zip(stock,variant['cases']):
                self.assertEqual(before['driver_words'][-3:],after['driver_words'][-3:])
                if variant['name'] in ('fast-high-adc','lower-drive-high-adc') and before['adc']<=377:
                    self.assertEqual(before['driver_words'],after['driver_words'])
                if variant['name']=='lower-drive-high-adc':
                    self.assertEqual(before['selected_timing'],after['selected_timing'])
                    changed=[i for i,(a,b) in enumerate(zip(before['driver_words'],after['driver_words'])) if a!=b]
                    self.assertEqual(changed,[1] if before['adc']>377 else [])


class BodyLinkTests(unittest.TestCase):
    def test_body_focus_modes_emit_matching_lens_commands(self):
        path = Path(__file__).resolve().parents[2]/'build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin'
        if not path.exists():
            self.skipTest('unpack the E-PM2 stock body firmware first')
        data = path.read_bytes()
        base = 0x7E421020
        table = 0x7E741368-base
        entries = dict(struct.unpack_from('<II',data,table+8*i) for i in range(64))
        for key,handler,code in ((3,0x7E52D3D4,0xA2),(4,0x7E52D3DF,0xA3),
                                 (5,0x7E52D3EA,0xA4)):
            self.assertEqual(entries[key],handler)
            self.assertEqual(data[handler+2-base:handler+5-base],bytes((0x2C,code,0)))


if __name__ == '__main__':
    unittest.main()
