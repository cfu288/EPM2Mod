"""Write Light Box as one switch (two specs, no new code) and its dial fix (one spec, no new code).

    uv run python gen/light-box/mkspec.py

data/specs/light-box-row-2.json: the row "Light Box" in Custom Menu D > ▶/Info Settings > ▶ Info (panel 191), as on
the E-PL5. The sub-item table is walked from top to bottom and a panel's rows are its records in that order. The record
119 of the unreachable panel 651 ("Mode Dial Function", Myset4) takes panel 191's first row, and the records 139-142
take panel 191's other three rows and {191, title 150, setting 257, 2, 7, 1, text 868}, so Light Box is the fifth row.
The row's picker is list 655 (panel 651's Myset4 list), its descriptor re-keyed to setting 257 with the stock Off/On
items of 257: the stock picker 198 is Spot's since spot-menu. Panel 191's child list gets the fifth entry (655, 257)
in place: its end entry moves 8 B into panel 192's old list, which nothing points at since level-gauge-lvinfo-row.
The ops are those of light-box-row (the camera-tested build light-box), made on a base without custom-menu-rows-5.

data/specs/light-box-switch.json goes last: CPlaySingleFrame's two INFO-key rules (getJumpState 0x7ED09135 and its
twin 0x7ED09616) go to the Light Box display only when setting 257 (Light Box) is 1 and setting 321 (▶ Close Up Mode)
is 2. Each `bne` after `cmp 2,d1` (0x7ED0940A, 0x7ED09805) becomes two `nop`, so Light Box On alone is enough, as on
the E-M10 and later bodies.

data/specs/light-box-dial.json: in the Light Box zoom view (state 17, the yellow ratio label), the main-dial handler
0x7EDBD84E zooms one step itself and then returns state 20, whose entry 0x7EDBA14F zooms again with the same dial
delta. So a detent was two steps, and at 1x or 14x the second zoom asked for the ratio already shown, the component
answered API_REDUCE_MIN or API_ENLARGE_MAX, and GUI_PLAY_ERROR (handler 0x7EDBCF4B) restarted Light Box with another
pair of pictures. The handler's own zoom call (7 bytes at 0x7EDBD8F5) becomes seven `nop`: the state-20 entry makes
the one step, and the handler's checks (no zoom out at 1x, no zoom in at 14x) stop at the ends. ▲ and ▼ in that view
zoom in their own handlers and go to state 20 too, whose entry then repeats the shown ratio (delta 0): at 1x and 14x
that still restarted Light Box. So GUI_PLAY_ERROR's handler 0x7EDBCF4B also maps state 17 to state 16, as it maps
16 and 18-21: its five compares (20 bytes at 0x7EDBCF76) become one range test.

Every expect is a byte string of the specs before the spec in its build: data/builds/light-box-2.json for the first
two, data/builds/light-box-dial.json for light-box-dial. The earlier versions
custom-menu-rows-5.json and light-box-row.json (the camera-tested build light-box) are committed spec files; this
script made them at an earlier commit and no longer does. experiments/2026-11-19-light-box/NOTES.md.
"""

import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "gen", "lss-menu"))
from mkspec import Ops, image, spec  # noqa: E402  (gen/lss-menu)

BUILD = "data/builds/light-box-2.json"
DIAL_BUILD = "data/builds/light-box-dial.json"
ROW2, SWITCH, DIAL = "light-box-row-2", "light-box-switch", "light-box-dial"

# light-box-row-2
SUBROWS = 0x7EFEF4FC                             # sub-item table: 196 records of 20 B, walked top to bottom
R651, R191 = SUBROWS + 119 * 20, SUBROWS + 139 * 20   # 0x7EFEFE48 (panel 651, Myset4), 0x7EFEFFD8 (panel 191's 4)
LIST191 = 0x7EFF91FC                             # child list of panel 191: 4 entries, then the end entry
PICKER = 655                                     # generic list page of panel 651's Myset4 row; Light Box's stock
DESC655, DESC_OF = 0x7F00C78C, 0x7F00DDD8        # picker 198 is Spot's since spot-menu. {list, descriptor} entry
ITEMS257 = 0x7F008C88                            # the stock Off/On items of setting 257 (list 198's before spot-menu)

# light-box-dial: SS_PLAY_SINGLE state 17's ST_CHANGE_MAIN_DIAL handler 0x7EDBD84E, after its limit checks:
# mov 20,d2; call 0x7ED05980 (a0 = CPlayLightBox); mov d3,d0; call zoomImage; extbu d2; mov d2,d0; exthu d0; ret
DIAL_CALL = 0x7EDBD8F5
DIAL_CODE = "dd6986f4ffb0a8"        # call 0x7ED05F5E,[d2,a2,a3],168
# GUI_PLAY_ERROR 0x9A40's handler 0x7EDBCF4B, d0 = the state: 1, 2 -> 5; 15 -> 2; 16, 18, 19, 20, 21 -> 16 (0x7EDBCF8A);
# any other -> getJumpState(0) (0x7ED09135, at 0x7EDBCF8E), which in state 17 starts Light Box again
ERR_CMP = 0x7EDBCF76
ERR_OLD = "a010c812a012c80ea013c80aa014c806a015c906"   # cmp 16/beq, cmp 18/beq, cmp 19/beq, cmp 20/beq, cmp 21/bne
ERR_NEW = "28f0a005c710ca12" + "cb" * 12                # add -16,d0; cmp 5,d0; bls 0x7EDBCF8A; bra 0x7EDBCF8E; nop

# light-box-switch: in both rules, mov (sp),d1 = 257; cmp 1,d1; bne; mov (sp),d1 = 321; cmp 2,d1; bne; cmp d3,d0
GATES = ((0x7ED09408, "getJumpState 0x7ED09135"), (0x7ED09803, "0x7ED09616, its twin, called by the zoom handlers"))


def subrow(panel, title, setting, text):
    return struct.pack("<HHIIHHHH", panel, title, setting, 2, 7, 1, text, 0)


def kids(pairs):
    return b"".join(struct.pack("<II", p, s) for p, s in pairs)


def light_box_row(specs):
    o = Ops(*image(specs))
    i191 = [(191, 150, 253, 845), (191, 150, 254, 926), (191, 150, 255, 844), (191, 150, 256, 842)]
    assert o.get(R651, 20) == subrow(651, 1353, 493, 607)
    assert o.get(R191, 80) == b"".join(subrow(*r) for r in i191)
    assert o.get(R191 + 80, 2) == struct.pack("<H", 192)
    o.add(R651, subrow(*i191[0]), "sub-item record 119: panel 651 'Mode Dial Function' / setting 493 / text 607 "
          "'Myset4' (no menu reaches panel 651 on the E-PM2) -> panel 191's first row, '▶ Info' / setting 253 / text "
          "845 'Image Only'")
    o.add(R191, b"".join(subrow(*r) for r in i191[1:]) + subrow(191, 150, 257, 868), "sub-item records 139-142: "
          "panel 191's rows 2-4 (settings 254, 255, 256), each one record earlier, and the fifth row: panel 191 '▶ "
          "Info' (title 150) / setting 257 / text 868 'Light Box', equal to the E-PL5 row at 0x7EFF08D0. Panel 191's "
          "rows keep their order")
    assert o.get(LIST191, 40) == kids([(194, 253), (195, 254), (196, 255), (197, 256), (0, 0)])
    assert o.get(LIST191 + 40, 8) == kids([(200, 244)])        # panel 192's old list, unreferenced (V, word scan)
    assert struct.unpack("<II", o.get(DESC_OF, 8)) == (PICKER, DESC655)
    assert struct.unpack("<HHIII", o.get(DESC655, 16)) == (493, 9, 0, 1, 0x7F00BAE8)
    assert struct.unpack("<HHIII", o.get(0x7F00C2FC, 16))[0] == 593, "list 198 is not Spot's picker"
    o.add(DESC655, struct.pack("<HHIII", 257, 2, 0, 1, ITEMS257), "list descriptor of %d (the picker of panel 651's "
          "Myset4 row; no menu reaches panel 651): setting 493, 9 items at 0x7F00BAE8 -> setting 257, the stock Off/On "
          "items 0x%08X of setting 257 (the descriptor of list 198 before spot-menu)" % (PICKER, ITEMS257))
    o.add(LIST191 + 32, kids([(PICKER, 257), (0, 0)]), "child list of panel 191, in place: the fifth entry (list %d, "
          "setting 257) in place of the end entry, and the end entry in place of the first entry of panel 192's old "
          "list 0x7EFF9224 (no pointer to it since level-gauge-lvinfo-row). The E-PL5's list 0x7EFF9AE0 has list 198, "
          "which is Spot's picker here" % PICKER)
    old = json.load(open(os.path.join(ROOT, "data", "specs", "light-box-row.json")))["ops"]
    assert [(x["offset"], x["expect"], x["new"]) for x in old] == [(x["offset"], x["expect"], x["new"]) for x in o.ops]
    spec(ROW2, "Light Box (E-PL6 manual p.86): the row 'Light Box' in Custom Menu D > ▶/Info Settings > ▶ Info "
         "(panel 191, setting 257 = prm tag 0x9171, Off / On), as on the E-PL5. Data only, 4 edits in place, no free "
         "space: the sub-item record 119 of panel 651 ('Mode Dial Function', which no menu reaches on the E-PM2) and "
         "the records 139-142 hold panel 191's four rows in their order and then {191, title 150, setting 257, 2, 7, 1, "
         "text 868}; panel 191's child list gets the fifth entry (655, 257), its end entry moving into panel 192's old "
         "list, which nothing points at since data/specs/level-gauge-lvinfo-row.json. The row's picker is list 655 "
         "(panel 651's Myset4 list), its descriptor re-keyed to setting 257 with the stock Off/On items of 257: the "
         "stock picker 198 is the Spot row's since data/specs/spot-menu.json. The same edits as "
         "data/specs/light-box-row.json (the build light-box), here without custom-menu-rows-5; "
         "data/specs/light-box-switch.json makes the display need this row only. See "
         "experiments/2026-11-19-light-box/NOTES.md, \"Light Box as one switch\".", o.ops)


def light_box_switch(specs):
    o = Ops(*image(specs))
    for a, what in GATES:
        assert o.get(a - 6, 3) == bytes.fromhex("a501c9"), hex(a)     # cmp 1,d1 (257 = On); bne
        assert o.get(a, 4) in (bytes.fromhex("a502c914"), bytes.fromhex("a502c915")), hex(a)   # cmp 2,d1; bne
        o.add(a + 2, bytes.fromhex("cbcb"), "%s: the `bne` after `cmp 2,d1` (setting 321, ▶ Close Up Mode, is mode2) "
              "-> two `nop`: Light Box On (setting 257 = 1) and check 1 (0x7ED009D6) decide alone" % what)
    spec(SWITCH, "Light Box as one switch, as on the E-M10 and later bodies: the INFO key in single-picture playback "
         "goes to the Light Box display when the ▶ Info row Light Box (setting 257) is On, whatever setting 321 "
         "(▶ Close Up Mode, which has no menu row on the E-PM2) holds. CPlaySingleFrame::getJumpState 0x7ED09135 and "
         "its twin 0x7ED09616 test 257 = 1, 321 = 2 and check 0x7ED009D6 before they set display mode 11, the step "
         "before state 15 (ID_ST_DISP_LIGHTBOX_PREPARE); in both the `bne` of the 321 test becomes two `nop`. The "
         "state-15 step itself (0x7ED095E8) reads 257 and check 0x7ED00A1D only. 4 bytes, no new code. Needs "
         "data/specs/light-box-row-2.json for the row. See experiments/2026-11-19-light-box/NOTES.md, \"Light Box as "
         "one switch\".", o.ops)


def light_box_dial(specs):
    o = Ops(*image(specs))
    # mov 20,d2; call 0x7ED05980,[],4; mov d3,d0 | the call | extbu d2; mov d2,d0; exthu d0; ret [d2,d3],12
    assert o.get(DIAL_CALL - 10, 10) == bytes.fromhex("8a14dd9380f4ff00048c")
    assert o.get(DIAL_CALL, 7) == bytes.fromhex(DIAL_CODE)
    assert o.get(DIAL_CALL + 7, 6) == bytes.fromhex("16881cdfc00c")
    o.add(DIAL_CALL, bytes.fromhex("cb") * 7, "0x7EDBD84E, the main-dial handler of the Light Box zoom view (state 17): "
          "its call of CPlayLightBox::zoomImage 0x7ED05F5E -> seven `nop`. The handler still returns state 20 (d2, "
          "set before the call, which the callee saves and restores); the entry of state 20 (0x7EDBA14F) zooms one "
          "step with the dial's delta, and the handler's checks above (no zoom out at 100, no zoom in at 1400) stop at "
          "the ends, so no zoom request repeats the shown ratio and no GUI_PLAY_ERROR restarts Light Box")
    assert o.get(ERR_CMP - 6, 6) == bytes.fromhex("8a02a00fc82a"), "mov 2,d2; cmp 15,d0; beq 0x7EDBCF9E"
    assert o.get(ERR_CMP, 20) == bytes.fromhex(ERR_OLD)
    assert o.get(ERR_CMP + 20, 4) == bytes.fromhex("8a10ca12"), "mov 16,d2; bra 0x7EDBCF9E"
    o.add(ERR_CMP, bytes.fromhex(ERR_NEW), "0x7EDBCF4B, the handler of GUI_PLAY_ERROR 0x9A40 (d0 = the state): the "
          "compares 16, 18, 19, 20, 21 -> 'go to state 16' become one range test 16-21, so state 17, the Light Box zoom "
          "view, also goes to state 16 (the view with the same zoom) instead of getJumpState(0), which starts Light "
          "Box again with another pair. A zoom with ▲ or ▼ to 1x or 14x in that view repeats the shown ratio in the "
          "entry of state 20 and gets API_REDUCE_MIN or API_ENLARGE_MAX. d0 is not read after the test: state 16 "
          "sets d2, the other path clears d0 before getJumpState. The 12 bytes after the `bra` are not reached")
    spec(DIAL, "Light Box zoom with the control dial: one zoom step per dial detent, and no restart at 1x or 14x. In "
         "the Light Box zoom view (SS_PLAY_SINGLE state 17, the yellow ratio label) the main-dial handler 0x7EDBD84E "
         "called CPlayLightBox::zoomImage itself and returned state 20, whose entry 0x7EDBA14F zooms again with the "
         "same delta: two steps per detent (2x, 5x, 10x, 14x), and at the ends the second request repeated the shown "
         "ratio, the play component answered API_REDUCE_MIN or API_ENLARGE_MAX, and GUI_PLAY_ERROR (0x7EDBCF4B, "
         "getJumpState(0) in state 17) restarted Light Box with the right picture moved to the left. The handler's "
         "call (7 bytes) becomes `nop`; the state-20 entry makes the one step, and the handler's own checks stop at "
         "1x and 14x. ▲ and ▼ in that view still repeated the ratio at the ends (the state-20 entry zooms by 0 after "
         "their own step), so GUI_PLAY_ERROR's handler 0x7EDBCF4B now maps state 17 to state 16, as it maps 16 and "
         "18-21 (20 bytes: five compares become one range test). No new code area. See experiments/2026-11-19-light-box/NOTES.md, \"Light Box dial (2026-11-28)\".",
         o.ops)


def main():
    specs = json.load(open(os.path.join(ROOT, BUILD)))["specs"]
    assert specs[-2:] == ["data/specs/%s.json" % ROW2, "data/specs/%s.json" % SWITCH]
    light_box_row(specs[:-2])
    light_box_switch(specs[:-1])
    dial = json.load(open(os.path.join(ROOT, DIAL_BUILD)))["specs"]
    assert dial[-1] == "data/specs/%s.json" % DIAL
    light_box_dial(dial[:-1])


if __name__ == "__main__":
    main()
