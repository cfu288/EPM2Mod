"""All six colour stages for every art code that a menu entry can produce. Uses tools/emu (function harness).

    .venv/bin/python experiments/2026-11-16-films-max/scripts/stage_check.py build/NAME.BIN [--base build/peaking-fast.BIN]
                                                                             [--stock-entries N ...] [--json OUT]

A sibling of experiments/2026-11-14-focus-peaking/scripts/scen_direct4.py S6 (which runs the six-axis dispatch
alone). For the image NAME it does, with the firmware's own code in the emulator:

1. Codes. For every stored Picture Mode value of the value list of setting 111 (and the lists of 509 and 510):
   art_GetFilterType (types 1 to 3), and the stub of each of the four live-view tables (still and movie table of
   the two functions 0x7E6CBFD3 and 0x7E6DBA95), run from the table entry to the function's tail. FAIL if the
   three "still" answers of a value differ (type 1; the cause of three live-view freezes, film notes sections 34
   to 37), or the two movie answers differ (the movie freeze, section 47).
2. Stages. For every code found (still and movie), each stage's dispatch:
   (a) base gamma 0x7E56B790 (whole function, seven input variants), (b) look curve 0x7E56E837 from its range
   test, (c) saturation pair 0x7E56DC71 from its range test, (d) six-axis 0x7E56D1C3 from its range test,
   (e) art matrix from the compare chain 0x7E56C6A5, (f) chroma curves 0x7E5662D9 from its table lookup.
   Each run ends at the stage's common tail; the tables that the code leaves there are read back.
   FAULT = the CPU left the code of block 0 or did not reach a tail.
3. Intended look. For a film entry (looks/films.json, looks/more-films.json) the bytes of those tables are
   compared with the bytes that the production generator makes from the film's fit: three tone tables (stills
   variant), the identity look table, the saturation pair, the six-axis records, the matrix and the chroma record.
   For a movie code the matrix, the saturation pair and the six-axis records must be the film's; its tone tables
   and chroma record are reported (the first seven films use straight chroma curves in movies, by design).
   For an entry that is still a stock filter, every address and content must be what the stock image gives.
4. Classes. For every stored value: the record code's class by Picture Mode (0x7E70DBDE), and for every code its
   class in the two by-code tables (0x7E70DBB6, 0x7E70E298). Static reads of the image: the code is in no
   effect list of art_chk_type (0x7E71C0E1, 0x7E71C28B), has no effect program (hash 0x7E85C45C), and is in none
   of the movie-art tables (jump table 0x7E7FF0B0, hashes 0x7E7FF668 and 0x7E7FF568).
6. ART shooting mode (static read of the image): the preset of each ART filter sets setting 111 to a stored
   value; it must be the value that the Picture Mode list has at the same place, so the entry gives the same
   film in ART mode. (That the camera applies the preset: emulator, screens.sh step 3.)
5. With --base: the same run on the base image; every stored value that both images have must give the same
   codes, tables and table contents (a film that was there before is not changed).

Exit status 1 on any FAIL or FAULT. No pixel is computed: the stages' arithmetic is not run, only their choice
of tables. What the camera does with the tables is measured on the camera.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "emu"))
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import omemu  # noqa: E402
from cases import CASES  # noqa: E402

from epm2mod.container import parse  # noqa: E402
from epm2mod.looks import generate, slots  # noqa: E402
from epm2mod.looks.films import load_films, load_more_films  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

BASE = omemu.BASE
SP = omemu.SP0
BUF = omemu.DATA + 0x1000
NEW_CODE = [slots.EXTRA_CODE_AREA, slots.EXTRA_DATA_AREA]
VARIANTS = ((0, 1, 0), (0, 0, 0), (1, 1, 0), (0, 4, 0x80), (1, 7, 0xC0), (0, 1, 0x24), (0, 1, 7))  # d0, d1, variant byte
STILLS = (0, 1, 0)
EFFECT_LISTS = (0x7E71C0E1, 0x7E71C28B, 0x7E71C4DC)  # art_chk_type_rec, art_chk_type_mov: compare lists up to the next function
EFFECT_HASH = (0x7E85C45C, 72)
MOVIE_ART_JUMP = (0x7E7FF0B0, 69, 184)
MOVIE_ART_HASHES = ((0x7E7FF668, 68), (0x7E7FF568, 68))
OUT = print


def block0(path: str) -> str:
    """Return the path of a block-0 file for an image (.BIN container or block-0 file)."""
    data = Path(path).read_bytes()
    if len(data) == 0xD7FFC0:
        return path
    payload = parse(data).blocks[0].payload
    fd, name = tempfile.mkstemp(suffix=".block0.bin", prefix="stage-check-")
    os.write(fd, payload)
    os.close(fd)
    return name


class Image:
    """One block-0 image in the emulator."""

    def __init__(self, path: str) -> None:
        self.path = block0(path)
        self.b = Path(self.path).read_bytes()
        self.emu = omemu.Emu()
        self.emu.__enter__()
        self.emu.load(self.path)
        self.faults: list[str] = []

    def close(self) -> None:
        self.emu.__exit__(None, None, None)

    def u32(self, address: int) -> int:
        return struct.unpack_from("<I", self.b, address - BASE)[0]

    def read(self, address: int, length: int) -> bytes:
        return self.b[address - BASE : address - BASE + length]

    def inside(self, address: int, length: int = 1) -> bool:
        return BASE <= address and address + length <= BASE + len(self.b)

    def piece(self, what: str, start: int, regs: dict[str, int], stops: list[int], stack: dict[int, int] | None = None) -> dict[str, int] | None:
        """Run from `start` to one of `stops`. Return the registers there, or None (and note a fault)."""
        emu = self.emu
        for offset, value in (stack or {}).items():
            emu.write(SP + offset, struct.pack("<I", value))
        emu.req("reset", regs={"pc": start, "sp": SP, "mdr": 0, "psw": 0, **regs})
        try:
            result = emu.req("cont", stops=stops)
        except omemu.EmuError as error:
            self.faults.append(f"{what}: {error}")
            return None
        got = emu.regs_of(result)
        if result["stop"] != "break" or got["pc"] not in stops:
            self.faults.append(f"{what}: stop {result['stop']} at pc {got['pc']:#010x}")
            return None
        return got

    # ---- menu entry -> art code -------------------------------------------------------------------
    def stored_values(self) -> list[list[int]]:
        """The stored values of the three Picture Mode value lists (19 entries each)."""
        return [[self.b[table - BASE + slots.VALUE_LIST_STEP * k] for k in range(19)] for table in slots.VALUE_LISTS]

    def filter_type(self, value: int, kind: int) -> int:
        case = CASES["filter_type"]
        result = self.emu.call(case.entry, {"d0": value, "d1": kind}, stubs=case.stubs({}))
        stray = [pc for pc in result["pcs"] if not any(lo <= pc < hi for lo, hi in case.ranges + NEW_CODE + HARNESS)]
        if stray:
            self.faults.append(f"art_GetFilterType({value}, {kind}): code ran at {stray[0]:#010x}")
        return result["regs"]["d0"] & 0xFFFF

    def live_view(self, value: int) -> dict[str, int | None]:
        """The art code of each of the four live-view tables for a stored value."""
        out: dict[str, int | None] = {}
        for name, (still, movie, tail) in zip("AB", slots.LIVE_VIEW):
            for kind, table in (("still", still), ("movie", movie)):
                stub = self.u32(table + 4 * (value - slots.FIRST_ART_VALUE))
                got = self.piece(f"live-view table {name} {kind}, value {value}", stub, {"d2": 0xEEEE}, [tail])
                out[f"{name} {kind}"] = None if got is None else got["d2"] & 0xFFFF
        return out

    # ---- the six stages ---------------------------------------------------------------------------
    def gamma(self, code: int) -> dict[tuple[int, int, int], list[int]] | None:
        out = {}
        case = CASES["gamma_select"]
        for d0, d1, variant in VARIANTS:
            try:
                got = case.run(self.emu, {"art": code, "d0": d0, "d1": d1, "s1": variant})
            except (omemu.EmuError, RuntimeError) as error:
                self.faults.append(f"gamma, code {code}, variant {(d0, d1, variant)}: {error}")
                return None
            stray = [pc for pc in got["_r"]["pcs"] if not any(lo <= pc < hi for lo, hi in case.ranges + NEW_CODE + HARNESS)]
            if stray:
                self.faults.append(f"gamma, code {code}: code ran at {stray[0]:#010x}")
            out[(d0, d1, variant)] = [int(text, 16) for text in got["tables"]]
        return out

    def look(self, code: int) -> int | str | None:
        got = self.piece(f"look, code {code}", 0x7E56E854, {"d1": code}, [0x7E56EB0F, 0x7E56E9F4])
        if got is None:
            return None
        return got["a0"] if got["pc"] == 0x7E56EB0F else "default"

    def saturation(self, code: int) -> int | None:
        got = self.piece(f"saturation, code {code}", 0x7E56DC71, {"d1": code}, [0x7E56DD79, 0x7E56DD28])
        if got is None:
            return None
        return got["a3"] if got["pc"] == 0x7E56DD79 else -1

    def six_axis(self, code: int) -> tuple[int, int] | str | None:
        stops = [0x7E56D8D8, 0x7E56D76A, 0x7E56D92D, 0x7E56D9DA, 0x7E56D9E4, 0x7E56D5F5]  # 0x7E56D5F5: after the two loads of the Cross Process handler
        got = self.piece(f"six-axis, code {code}", 0x7E56D2AB, {"d3": code, "a2": 0x10000, "a3": BUF}, stops)
        if got is None:
            return None
        if got["pc"] == 0x7E56D8D8:
            return (got["a3"], got["a2"])
        if got["pc"] == 0x7E56D5F5:
            # the Cross Process handler: it loads its two records and goes on to the scene statistics (which
            # patches/xp-adaptive-hue-off.json makes without effect). The records are in a3 and a2 here too.
            return ("statistics", got["a3"], got["a2"])
        return {0x7E56D76A: "default"}.get(got["pc"], f"tail {got['pc']:#x}")

    def matrix(self, code: int) -> int | str | None:
        case = CASES["matrix_choice"]
        try:
            got = case.run(self.emu, {"art": code})
        except (omemu.EmuError, RuntimeError) as error:
            self.faults.append(f"matrix, code {code}: {error}")
            return None
        stray = [pc for pc in got["_r"]["pcs"] if not any(lo <= pc < hi for lo, hi in case.ranges + NEW_CODE + HARNESS)]
        if stray:
            self.faults.append(f"matrix, code {code}: code ran at {stray[0]:#010x}")
        if got["exit"] == "apply":
            return int(got["a1"], 16)
        return {"table1": 0x7E768F46, "table2": 0x7E768F58}.get(got["exit"], got["exit"])

    def chroma(self, code: int) -> int | str | None:
        self.emu.write(BUF, b"\0" * 24)
        got = self.piece(f"chroma, code {code}", 0x7E5662EE, {}, [0x7E566810, 0x7E56677A], stack={4: BUF, 8: code})
        if got is None:
            return None
        if got["pc"] == 0x7E56677A:
            return "default"
        words = list(struct.unpack("<5I", self.emu.read(BUF, 20))) + [got["d0"]]
        steps = [b - a for a, b in zip(words, words[1:])]
        if steps != [16, 16, 17, 16, 16]:
            return "other shape " + " ".join(f"{w:#x}" for w in words)  # Dramatic Tone: three arrays, twice
        return words[0]

    def stages(self, code: int) -> dict[str, object]:
        return {
            "gamma": self.gamma(code),
            "look": self.look(code),
            "saturation": self.saturation(code),
            "six_axis": self.six_axis(code),
            "matrix": self.matrix(code),
            "chroma": self.chroma(code),
        }

    # ---- contents ---------------------------------------------------------------------------------
    def content(self, stage: dict[str, object]) -> dict[str, object]:
        """The bytes behind the tables of a stage result (as short hashes, and raw for the comparison)."""
        raw: dict[str, object] = {}
        gamma = stage["gamma"]
        if isinstance(gamma, dict):
            raw["tone"] = {key: [self.read(t, 512) if self.inside(t, 512) else None for t in tables] for key, tables in gamma.items()}
        look = stage["look"]
        raw["look"] = self.read(look, 512) if isinstance(look, int) and self.inside(look, 512) else look
        sat = stage["saturation"]
        raw["saturation"] = self.read(sat, 4) if isinstance(sat, int) and sat > 0 and self.inside(sat, 4) else sat
        six = stage["six_axis"]
        pair = six[-2:] if isinstance(six, tuple) else None
        raw["six_axis"] = self.read(pair[0], 12) + self.read(pair[1], 12) if pair and all(self.inside(a, 12) for a in pair) else six
        matrix = stage["matrix"]
        raw["matrix"] = self.read(matrix, 18) if isinstance(matrix, int) and self.inside(matrix, 18) else matrix
        chroma = stage["chroma"]
        raw["chroma"] = self.read(chroma, 97) if isinstance(chroma, int) and self.inside(chroma, 97) else chroma
        return raw

    # ---- classes ----------------------------------------------------------------------------------
    def kind_by_value(self, value: int) -> int:
        result = self.emu.call(0x7E70DBDE, {"d0": value})
        return result["regs"]["d0"] & 0xFFFF

    def kind_by_code(self, code: int) -> tuple[int, int]:
        self.emu.write(BUF, b"\0" * 0x4100)
        self.emu.write(BUF + 16456, struct.pack("<H", code))
        self.emu.write(BUF + 16460, struct.pack("<H", code))
        first = self.emu.call(0x7E70DBB6, {"a0": BUF})["regs"]["d0"] & 0xFFFF
        second = self.emu.call(0x7E70E298, {"a0": BUF})["regs"]["d0"] & 0xFFFF
        return first, second

    def effect_codes(self) -> set[int]:
        """The art codes that art_chk_type compares with (read from the code bytes)."""
        codes: set[int] = set()
        code = self.read(EFFECT_LISTS[0], EFFECT_LISTS[2] - EFFECT_LISTS[0])
        index = 0
        while index < len(code) - 4:
            if code[index] in (0xA0, 0xA5) and code[index + 2] in (0xC8, 0xC9) and code[index + 1] >= 67:
                codes.add(code[index + 1])
                index += 2
            elif code[index] == 0xFA and code[index + 1] in (0xC8, 0xC9) and code[index + 3] == 0:
                codes.add(code[index + 2])
                index += 4
            else:
                index += 1
        return codes

    def hash_keys(self, table: int, first: int) -> set[int]:
        keys = set()
        for index in range(32):
            key = self.u32(table + 8 * index)
            if key:
                keys.add(key + first)
        return keys

    def art_presets(self) -> dict[int, int]:
        """{ART mode code: the stored Picture Mode value that the code's preset sets}."""
        out = {}
        row = slots.MODE_PRESETS
        while True:
            code, kind, address, count = struct.unpack("<HHIH", self.read(row, 10))
            if code == 0:
                return out
            if kind == slots.ART_PRESET_KIND:
                for index in range(count):
                    setting, value = struct.unpack("<2I", self.read(address + 8 * index, 8))
                    if setting == slots.PICTURE_MODE_SETTING:
                        out[code] = value
            row += slots.MODE_PRESET_ROW

    def movie_art_special(self) -> set[int]:
        table, first, last = MOVIE_ART_JUMP
        entries = {code: self.u32(table + 4 * (code - first)) for code in range(first, last + 1)}
        default = max(set(entries.values()), key=list(entries.values()).count)
        special = {code for code, target in entries.items() if target != default}
        for hash_table, key_base in MOVIE_ART_HASHES:
            special |= self.hash_keys(hash_table, key_base)
        return special


HARNESS = [(omemu.TRAMP, omemu.TRAMP + 16), (omemu.PADS, omemu.PADS + 0x100)]


def short(data: object) -> str:
    """A short text for a table content."""
    if isinstance(data, bytes):
        return hashlib.sha256(data).hexdigest()[:10]
    return str(data)


def intended(paths: RepoPaths, stock: Image) -> dict[int, dict[str, object]]:
    """Per stored value: the look that the film lists intend, as the bytes the generator writes.

    Returns {stored value: {"film", "tone" (3 tables), "look", "saturation", "six_axis", "matrix", "chroma"}}.
    """
    program = generate.Program(stock.b)
    grid = np.arange(slots.CURVE_POINTS, dtype=np.float64)
    stills = program.table(program.record(slots.DEFAULT_RECORD)[slots.STILLS_TABLE])
    seven_values = {"Pop Art": 100, "Soft Focus": 101, "Pale&Light Color": 102, "Light Tone": 103, "Pin Hole": 105, "Diorama": 106, "Cross Process": 107}
    wanted: dict[int, dict[str, object]] = {}

    def add(value: int, film: object, fit: dict[str, np.ndarray]) -> None:
        curves = np.asarray(fit["G"], dtype=np.float64)
        gain = int(fit["gain"])
        wanted[value] = {
            "film": film.film,  # type: ignore[attr-defined]
            "tone": [generate.pack_table(np.interp(stills, grid, curves[channel])) for channel in range(3)],
            "look": stock.read(slots.IDENTITY_LOOK, 512),
            "saturation": struct.pack("<2H", gain, gain),
            "six_axis": struct.pack("<6h", *[int(v) for v in fit["S"]]) + struct.pack("<6h", *[int(v) for v in fit["H"]]),
            "matrix": struct.pack("<9h", *[int(v) for v in np.asarray(fit["A"]).ravel()]),
            "chroma": generate.chroma_record(fit, film.fit),  # type: ignore[attr-defined]
        }

    for film in load_films(paths).films:
        add(seven_values[film.entry], film, generate.load_fit(paths.resolve(film.fit)))
    if paths.more_films.exists():
        for film, slot in zip(load_more_films(paths).films, slots.EXTRA_SLOTS):
            add(slot.value, film, generate.load_fit(paths.resolve(film.fit)))
    return wanted


def survey(image: Image) -> dict[str, object]:
    """Codes and stage results of one image."""
    lists = image.stored_values()
    values = [v for v in lists[0] if v >= slots.FIRST_ART_VALUE]
    entries = {}
    codes: set[int] = set()
    for value in values:
        types = [image.filter_type(value, kind) for kind in (1, 2, 3)]
        live = image.live_view(value)
        entries[value] = {"types": types, "live": live, "kind": image.kind_by_value(value)}
        codes |= {c for c in types if c != 0xFFFF} | {c for c in live.values() if c is not None}
    stage = {code: image.stages(code) for code in sorted(codes)}
    return {"lists": lists, "values": values, "entries": entries, "stage": stage,
            "by_code": {code: image.kind_by_code(code) for code in sorted(codes)}}


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("image")
    parser.add_argument("--base", help="an image whose entries must be unchanged in IMAGE where IMAGE still has them")
    parser.add_argument("--stock", default=str(ROOT / "build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin"))
    parser.add_argument("--json")
    args = parser.parse_args()
    paths = RepoPaths(ROOT)
    fails: list[str] = []
    image, stock = Image(args.image), Image(args.stock)
    wanted = intended(paths, stock)
    mine = survey(image)
    names = {100: "Pop Art", 101: "Soft Focus", 102: "Pale&Light Color", 103: "Light Tone", 104: "Grainy Film", 105: "Pin Hole",
             106: "Diorama", 107: "Cross Process", 108: "Gentle Sepia", 109: "Dramatic Tone", 119: "Key Line", 120: "Watercolor"}
    names.update({slot.value: slot.entry for slot in slots.EXTRA_SLOTS})

    OUT(f"image {args.image}")
    lists = mine["lists"]
    OUT(f"1. Picture Mode value lists (111, 509, 510): {lists[0]}")
    if not lists[0] == lists[1] == lists[2]:
        fails.append("the three value lists differ")
    effect, special = image.effect_codes(), image.movie_art_special()
    program = image.hash_keys(*EFFECT_HASH)
    OUT(f"   effect codes of art_chk_type: {sorted(effect)}; effect programs: {sorted(program)}")
    OUT(f"   codes with an entry of their own in the movie-art tables (type II / III lookups; not a class): {sorted(special)}")
    for value in mine["values"]:
        entry = mine["entries"][value]
        types, live = entry["types"], entry["live"]
        still, movie = {types[0], live["A still"], live["B still"]}, {live["A movie"], live["B movie"]}
        film = wanted.get(value)
        OUT(f"   value {value:3d} ({names.get(value, '?')}{' = ' + str(film['film']) if film else ', stock filter'}): art_GetFilterType types 1-3 "
            f"{types}; live view A/B still {live['A still']}/{live['B still']}, movie {live['A movie']}/{live['B movie']}; class by value {entry['kind']}")
        if len(still) != 1 or None in still:
            fails.append(f"value {value}: art_GetFilterType and the live-view still tables disagree: {sorted(map(str, still))}")
        if len(movie) != 1 or None in movie:
            fails.append(f"value {value}: the two live-view movie tables disagree")
        if film:
            if entry["kind"] != 1:
                fails.append(f"value {value}: a film entry with class {entry['kind']} by Picture Mode (1 = colour only)")
            for code in still | movie | set(types):
                if code in effect or code in program:
                    fails.append(f"value {value}: film code {code} is an effect code (art_chk_type list or effect program)")
            if len({code for code in types if code != 0xFFFF}) != 1:
                fails.append(f"value {value}: the filter types give different codes {types}")

    OUT("2. Stages per art code (address of the table each stage ends with; tone = stills variant R, G, B)")
    for code, stage in mine["stage"].items():
        gamma = stage["gamma"]
        tone = [hex(t) for t in gamma[STILLS]] if isinstance(gamma, dict) else gamma
        fmt = lambda v: hex(v) if isinstance(v, int) and v > 0 else (str([hex(x) if isinstance(x, int) else x for x in v]) if isinstance(v, tuple) else str(v))
        OUT(f"   code {code:3d}: tone {tone}; look {fmt(stage['look'])}; saturation {fmt(stage['saturation'])}; six-axis {fmt(stage['six_axis'])}; "
            f"matrix {fmt(stage['matrix'])}; chroma {fmt(stage['chroma'])}; class by code {mine['by_code'][code]}")

    OUT("3. Intended looks")
    stock_survey: dict[str, object] | None = None
    for value in mine["values"]:
        entry = mine["entries"][value]
        film = wanted.get(value)
        still_code, movie_code = entry["types"][0], entry["live"]["A movie"]
        if film is None:
            if stock_survey is None:
                stock_survey = survey(stock)
            theirs = stock_survey["entries"].get(value)
            same = theirs is not None and theirs["types"] == entry["types"] and theirs["live"] == entry["live"]
            why = "" if same else " (codes)"
            for code in {c for c in entry["types"] if c != 0xFFFF} | set(entry["live"].values()):
                if not same:
                    break
                a, b = mine["stage"][code], stock_survey["stage"][code]
                ca, cb = image.content(a), stock.content(b)
                parts = [k for k in a if a[k] != b[k]] + [k + " content" for k in ca if ca[k] != cb[k]]
                same = not parts
                why = "" if same else f" (code {code}: {', '.join(parts)})"
            OUT(f"   value {value} ({names.get(value)}): stock filter, {'same codes, tables and contents as the stock firmware' if same else 'DIFFERS from the stock firmware' + why}"
                + ("" if entry["kind"] == (theirs or {}).get("kind") else "; class by value differs"))
            if not same:
                fails.append(f"value {value}: a stock filter that differs from stock")
            continue
        for what, code in (("still", still_code), ("movie", movie_code)):
            if code is None or code == 0xFFFF:
                continue
            got = image.content(mine["stage"][code])
            bad = []
            tone = got.get("tone", {}).get(STILLS) if isinstance(got.get("tone"), dict) else None
            keys = ["matrix", "saturation", "six_axis"] + (["look", "chroma"] if what == "still" else [])
            for key in keys:
                if got.get(key) != film[key]:
                    bad.append(key)
            if what == "still" and tone != film["tone"]:
                bad.append("tone")
            extra = ""
            if what == "movie":
                is_film_tone = tone == film["tone"]
                linear = got.get("chroma") == stock.read(0x7E74B858, 97)
                extra = (f" (movie: tone tables {'the film' if is_film_tone else 'not the film'}s; chroma "
                         f"{'the film' if got.get('chroma') == film['chroma'] else 'straight' if linear else 'other'}; look "
                         f"{'identity' if got.get('look') == film['look'] else 'other'})")
            OUT(f"   value {value} ({names.get(value)} = {film['film']}), {what} code {code}: {'all tables are the film' if not bad else 'NOT the film: ' + ', '.join(bad)}{extra}")
            if bad:
                fails.append(f"value {value} {what} code {code}: {', '.join(bad)} not the film {film['film']}")

    OUT("6. ART shooting mode: the preset of each ART filter (table 0x7E834794, kind 1) sets setting 111")
    art_codes = list(image.read(0x7E849784, 12))  # the value list of setting 281, in list order
    presets = image.art_presets()
    for place, art_code in enumerate(art_codes):
        value = presets.get(art_code)
        listed = mine["values"][place]
        entry = mine["entries"].get(value) if value is not None else None
        film = wanted.get(value) if value is not None else None
        code = entry["types"][0] if entry else None
        OUT(f"   ART list place {place + 1} (mode code {art_code}): stores {value}; the Picture Mode list has {listed} there; "
            f"art code {code}{' = ' + str(film['film']) if film else ''}")
        if value != listed:
            fails.append(f"ART mode place {place + 1}: the preset stores {value}, the Picture Mode list {listed}")
        if entry is None:
            fails.append(f"ART mode place {place + 1}: the preset's value {value} is not in the Picture Mode list")

    if args.base:
        base = Image(args.base)
        theirs = survey(base)
        OUT(f"5. Against {args.base}")
        for value in mine["values"]:
            if value not in theirs["entries"]:
                OUT(f"   value {value}: not in the base image's list")
                continue
            a, b = mine["entries"][value], theirs["entries"][value]
            same = a == b
            for code in {c for c in a["types"] if c != 0xFFFF} | {c for c in a["live"].values() if c is not None}:
                if same:
                    same = mine["stage"][code] == theirs["stage"].get(code) and image.content(mine["stage"][code]) == base.content(theirs["stage"][code])
            OUT(f"   value {value} ({names.get(value)}): {'same codes, tables and contents' if same else 'DIFFERS'}")
            if not same:
                fails.append(f"value {value}: differs from the base image")
        gone = [v for v in theirs["values"] if v not in mine["values"]]
        OUT(f"   stored values of the base list that the image's list no longer has: {gone}")
        fails += [f"base image: {text}" for text in base.faults]
        base.close()

    for text in image.faults:
        fails.append("FAULT " + text)
    OUT("")
    for text in fails:
        OUT("FAIL  " + text)
    OUT(f"stage check: {'PASS' if not fails else 'FAIL'} ({len(mine['values'])} stored values, {len(mine['stage'])} art codes, {len(fails)} failures)")
    if args.json:
        Path(args.json).write_text(json.dumps({
            "values": mine["values"], "entries": {str(k): v for k, v in mine["entries"].items()},
            "stage": {str(code): {k: (v if not isinstance(v, dict) else {str(kk): vv for kk, vv in v.items()}) for k, v in st.items()} for code, st in mine["stage"].items()},
            "fails": fails}, indent=1, default=str))
    image.close()
    stock.close()
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
