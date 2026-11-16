"""Stage check of a build with the black-and-white film in the Grainy Film entry. Uses tools/emu (function harness).

    .venv/bin/python experiments/2026-11-16-doublex/scripts/stage_check_bw.py IMAGE.BIN [--films12 build/films-12.BIN] [--refit N]

--refit N: the image has the Nth later fit of looks/films-12-bw.json (its grain table, in a spare table).

1. Runs experiments/2026-11-16-films-max/scripts/stage_check.py on IMAGE (with --base, the twelve-film image). That
   check knows no black-and-white film: it must report one failure only, "value 104: a stock filter that differs
   from stock", and the difference must be the matrix of codes 74 and 83.
2. The entry (stored value 104), IMAGE against the stock firmware: art_GetFilterType and the four live-view tables
   give 74 / 104 (types I / II) and 74 / 83 (still / movie) as stock; the classes by value and by code, the effect
   lists and the effect program entries of 74, 83, 104, 105 are those of stock (the grain program is routed as stock).
3. Stages of 74 and 83: tone, saturation, six-axis, chroma as stock; the art matrix is the fit's table A; the look
   stage gives the stock tables for still pictures (0x7E75B8F0 / 0x7E75B6F0) and table 0x7E7620F0 = the fit's L
   for the variants 3, 5, 7 and 4 (live view, movie); the look stage of the grain program's jobs (op class 2)
   gives 0x7E75EEF0 = the fit's T. Codes 104 and 105 (Grainy Film II): every stage as stock.
4. The whole colour-matrix function 0x7E56C603 for a job of op class 0 with the monochrome flag (job+192 = 1), art
   code 74 and the camera's 5300 K matrix: the nine values it writes for the hardware, stock against IMAGE. This
   shows that the art matrix acts in the monochrome path (the picture becomes monochrome after this stage).
Exit status 1 on any failure.
"""
import argparse, struct, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments" / "2026-11-16-films-max" / "scripts"))
import stage_check as sc  # noqa: E402
import numpy as np  # noqa: E402
from epm2mod.looks import generate, slots  # noqa: E402
from epm2mod.looks.films import load_bw_films  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

BUF = sc.BUF
STILL_LOOKS = {1: 0x7E75B8F0, 0: 0x7E75B6F0}  # by the flag in d3
M5300 = (209, -70, -11, -28, 180, -24, 7, -66, 187)  # the camera's matrix at 5300 K, x128


def look_variant(image, code, variant, d3):
    got = image.piece(f"look, code {code}, variant {variant}", 0x7E56E854, {"d1": code, "d3": d3}, [0x7E56EB0F, 0x7E56E9F4], stack={16: variant})
    return None if got is None else got["a0"] if got["pc"] == 0x7E56EB0F else "default"


def grain_look(image, code):
    """The look table of an art code in a job of op class 2 with the art flag (P+20 bit 0x100) set."""
    image.emu.write(BUF, struct.pack("<I", 0x100)); image.emu.write(BUF + 16, struct.pack("<I", 0))
    got = image.piece(f"grain look, code {code}", 0x7E56EF47, {"d2": code, "d1": 0, "a3": BUF, "a2": BUF + 16}, [0x7E56F041])
    return None if got is None else got["d1"]


def matrix_function(image, code, mono):
    """Run 0x7E56C603 whole. Returns the nine values (x128) it writes, or None."""
    job, prm, out = BUF + 0x100, BUF + 0x400, BUF + 0x800
    image.emu.write(job, b"\0" * 0x300); image.emu.write(prm, b"\0" * 0x200); image.emu.write(out, b"\0" * 64)
    image.emu.write(job + 96, struct.pack("<I", prm)); image.emu.write(job + 192, bytes([mono])); image.emu.write(job + 194, bytes([0]))
    image.emu.write(prm + 24, struct.pack("<9h", *M5300)); image.emu.write(prm + 79, bytes([code]))
    try:
        image.emu.call(0x7E56C603, {"a0": job, "a1": out, "d0": 0})
    except Exception as error:  # noqa: BLE001
        image.faults.append(f"matrix function, code {code}: {error}")
        return None
    w = struct.unpack("<5I", image.emu.read(out, 20))
    vals = [w[0] & 0xFFFF, w[0] >> 16, w[1] & 0xFFFF, w[1] >> 16, w[2] & 0xFFFF, w[2] >> 16, w[3] & 0xFFFF, w[3] >> 16, w[4] & 0xFFFF]
    return [v - 0x10000 if v & 0x8000 else v for v in vals]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("image"); ap.add_argument("--films12", default=str(ROOT / "build/films-12.BIN")); ap.add_argument("--refit", type=int, default=0)
    ap.add_argument("--stock", default=str(ROOT / "build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin"))
    a = ap.parse_args(); fails = []
    paths = RepoPaths(ROOT); fit = generate.load_fit(paths.resolve(load_bw_films(paths).mono.fit))
    A = struct.pack("<9h", *[int(v) for v in np.asarray(fit["A"]).ravel()])
    P128 = [int(round(v * 128)) for v in np.asarray(fit["P"]).ravel()]
    T, L = (struct.pack("<256H", *[int(v) for v in fit[k]]) for k in ("T", "L"))
    grain_at = slots.MONO_SLOT.grain_table
    if a.refit:
        refit = generate.load_fit(paths.resolve(load_bw_films(paths).refits[a.refit - 1][0]))
        T = struct.pack("<256H", *[int(v) for v in refit["T"]]); grain_at = slots.MONO_SLOT.spare_tables[a.refit - 1][0]
        print(f"refit {a.refit}: the grain table is expected at {grain_at:#x}")

    print("1. stage_check.py of the twelve-film work on this image")
    done = subprocess.run([sys.executable, str(Path(sc.__file__)), a.image, "--base", a.films12], capture_output=True, text=True)
    lines = done.stdout.splitlines(); print("\n".join("   | " + line for line in lines))
    bad = [line for line in lines if "DIFFERS" in line or "NOT the film" in line or "FAULT" in line or "FAIL:" in line]
    last = lines[-1] if lines else ""
    if not ("1 failures" in last and any("value 104" in b and "code 74: matrix" in b or "value 104" in b and "code 83: matrix" in b for b in bad)):
        fails.append("stage_check.py: not exactly the one expected difference (value 104, the matrix)")
    print("   expected there: one failure, value 104 differs from stock in the matrix ->", "as expected" if not fails else "NOT as expected")

    image, stock = sc.Image(a.image), sc.Image(a.stock)
    print("2. the entry, against stock")
    for name, fn in (("art_GetFilterType types 1-3", lambda im: [im.filter_type(104, k) for k in (1, 2, 3)]), ("live-view tables", lambda im: im.live_view(104)),
                     ("class by value", lambda im: im.kind_by_value(104)), ("class by code 74, 83, 104, 105", lambda im: [im.kind_by_code(c) for c in (74, 83, 104, 105)]),
                     ("effect lists", lambda im: sorted(im.effect_codes())), ("effect program entries", lambda im: {c: im.u32(sc.EFFECT_HASH[0] + 8 * i + 4) for i in range(32) for c in [im.u32(sc.EFFECT_HASH[0] + 8 * i) + 72] if c in (74, 104)}),
                     ("movie-art table entries", lambda im: sorted(im.movie_art_special())), ("stored value at place 11 of the three lists", lambda im: [l[11] for l in im.stored_values()])):
        x, y = fn(image), fn(stock); print(f"   {name}: {x if not isinstance(x, list) or len(x) < 12 else str(len(x)) + ' codes'} -> {'as stock' if x == y else 'DIFFERS from stock ' + str(y)}")
        if x != y: fails.append(name)
    print("3. stages")
    for code in (74, 83, 104, 105):
        mine, theirs = image.stages(code), stock.stages(code); cm, ct = image.content(mine), stock.content(theirs)
        keys = [k for k in mine if k != "matrix"] if code in (74, 83) else list(mine)
        diff = [k for k in keys if mine[k] != theirs[k]] + [k + " content" for k in cm if k != ("matrix" if code in (74, 83) else None) and cm[k] != ct[k]]
        print(f"   code {code}: {', '.join(keys)}: {'as stock' if not diff else 'DIFFER: ' + ', '.join(diff)}")
        if diff: fails.append(f"code {code}: {diff}")
        if code in (74, 83):
            ok = cm["matrix"] == A; print(f"   code {code}: art matrix at {mine['matrix']:#x} {'= the fit' if ok else 'NOT the fit'} (stock: {theirs['matrix']})")
            if not ok: fails.append(f"code {code}: matrix")
        for variant in (0, 1, 3, 5, 7, 4, 0x24, 0x84):
            for d3 in (1, 0):
                got, ref = look_variant(image, code, variant, d3), look_variant(stock, code, variant, d3)
                live = isinstance(ref, int) and ref not in STILL_LOOKS.values()
                want = (L if code in (74, 83) else stock.read(ref, 512)) if live else stock.read(ref, 512)
                good = got == ref and image.read(got, 512) == want
                if not good: fails.append(f"code {code} look variant {variant:#x} d3 {d3}")
                if d3: print(f"   code {code}: look, variant {variant:#04x}: {got:#x} {'(live view / movie) ' if live else ''}{'ok' if good else 'WRONG'}{': the fit L' if live and code in (74, 83) and good else ''}")
        got, ref = grain_look(image, code), grain_look(stock, code)
        want = T if code in (74, 83) else stock.read(ref, 512)
        good = got == (grain_at if code in (74, 83) else ref) and image.read(got, 512) == want
        print(f"   code {code}: look table of the grain program's jobs {got:#x}: {'ok' if good else 'WRONG'}{', the fit T' if code in (74, 83) and good else ', as stock'}")
        if not good: fails.append(f"code {code} grain table")
    print(f"   the fit's matrix after the firmware's row step (model, x128): {P128}")
    print("4. the colour-matrix function 0x7E56C603, whole, job of op class 0, camera matrix 5300 K; values x128 written for the hardware")
    for code, mono in ((74, 1), (74, 0), (83, 1), (104, 1), (0, 1)):
        x, y = matrix_function(image, code, mono), matrix_function(stock, code, mono)
        print(f"   art code {code}, monochrome flag {mono}: stock {y}; this image {x}{'' if x != y else ' (same)'}")
        if code in (74, 83) and (x == y or x != P128): fails.append(f"matrix function: code {code} is not the fit's matrix")
        if code in (104, 0) and x != y: fails.append(f"matrix function: code {code} changed")
    for im in (image, stock):
        fails += im.faults; im.close()
    print(f"\nstage check, black-and-white entry: {'PASS' if not fails else 'FAIL'} ({len(fails)} failures)")
    for f in fails: print("  FAIL:", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
