"""Emulator check of films-twelve-off: which 12-region table each film code gets. Research code.

    OMP_NUM_THREADS=2 uv run python experiments/2026-11-20-model-calibration/scripts/emucheck_off.py

The selector 0x7E56E661 (worker + builder) is run in om-emu, as the twelve-region probe's emucheck, on:
  * the build's image: the eight film-only codes must get OFFDESC's table with mask 0; the four in-place codes and 43
    stock codes the same table as on the pinned build (films-look-exif);
  * the image with the in-place entries' switch words in their film state (as the loader writes them for a loaded
    film): the in-place codes must get mask 0 too, the stock codes still their pinned tables.
Exit status 1 on any mismatch.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "experiments", "2026-11-20-twelve-region", "scripts"), os.path.join(ROOT, "emulator")]
import omemu, patchblock  # noqa: E402
import emucheck as E  # noqa: E402

FILM_ONLY, IN_PLACE = [75, 94, 92, 125, 98, 144, 156, 159], [79, 71, 72, 85]


def image(build):
    _, img, _ = patchblock.patched_block0(json.load(open(os.path.join(ROOT, "data", "builds", build + ".json")))["specs"])
    return bytearray(img)


def switched(img):
    lay = json.load(open(os.path.join(ROOT, "build", "stock-films", "layout.json")))
    n = 0
    for e in lay["entries"]:
        for w in e["switch"]:
            if "12-region" in w["note"]:
                a = w["address"] - omemu.BASE
                assert img[a:a + 4].hex() == w["stock"], w
                img[a:a + 4] = bytes.fromhex(w["film"]); n += 1
    assert n == len(IN_PLACE)
    return img


def selections(img, tag):
    path = os.path.join(ROOT, "build", f"off-{tag}.block0.bin")
    open(path, "wb").write(img)
    out = {}
    with omemu.Emu() as emu:
        emu.load(path)
        for code in FILM_ONLY + IN_PLACE + E.STOCK_CODES:
            for cs in (0, 1):
                for mode in (2, 4):
                    tab, mask, errs = E.check(emu, bytes(img), code, cs, mode)
                    out[(code, cs, mode)] = (tab, mask, errs)
    return out


def main():
    os.chdir(ROOT)
    pinned = selections(image("films-look-exif"), "pinned")
    new = image("films-twelve-off")
    plain, film = selections(new, "plain"), selections(switched(bytearray(new)), "film")
    bad = 0
    for state, sel in (("no film", plain), ("film loaded", film)):
        for (code, cs, mode), (tab, mask, errs) in sorted(sel.items()):
            if code in FILM_ONLY or (code in IN_PLACE and state == "film loaded"):
                want = "mask 0"
                ok = mask == 0 and not errs
            else:
                want = "pinned table %#x" % pinned[(code, cs, mode)][0]
                ok = tab == pinned[(code, cs, mode)][0] and mask == pinned[(code, cs, mode)][1] and not errs
            bad += not ok
            if code in FILM_ONLY + IN_PLACE or not ok:
                print(f"{state:11s} code {code:3d} P+82 {cs} P+83 {mode}: table {tab:#x} mask {mask:#05x} "
                      f"(want {want}) {'OK' if ok else 'FAIL ' + '; '.join(errs)}")
    print(f"stock codes ({len(E.STOCK_CODES)}) x 2 colour spaces x 2 modes, both states: "
          f"{'same tables as pinned' if not bad else 'see FAIL lines'}")
    print("RESULT", "PASS" if not bad else f"FAIL ({bad})")
    return bad


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
