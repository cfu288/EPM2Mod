"""List UI strings that are not in the E-PM2 text table, by the first body that has them.

    python3 first_seen.py ENU_DIR OUT_DIR

ENU_DIR holds <code>_<version>.json from lang_enu.py. Bodies are taken in release order. Icon
escapes (@Axxx@) are replaced by '@' and white space is folded, so a renumbered icon is not a
difference. Writes OUT_DIR/new_<code>.txt (strings first seen in that body; 'N' = name-like,
'H' = help text) and OUT_DIR/all_new.tsv (string, first body, all bodies that have it).
"""
import json, re, sys
from pathlib import Path

ORDER = ["097", "100", "112", "108", "111", "109", "113", "115", "118", "120", "122", "126", "125",
         "130", "133", "139", "140", "142", "143", "144", "147"]
NAMES = {"097": "E-M5", "100": "E-PL5", "101": "E-PM2", "112": "E-PL6", "108": "E-P5", "111": "STYLUS 1",
         "109": "E-M1", "113": "E-M10", "115": "E-PL7", "118": "E-M5 II", "120": "E-M10 II", "122": "PEN-F",
         "126": "E-PL8", "125": "E-M1 II", "130": "E-M10 III", "133": "E-PL9", "139": "E-M1 III",
         "140": "E-M10 IV", "142": "E-P7", "143": "OM-1", "144": "OM-5", "147": "OM-3"}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"@A[0-9A-F]{3}@", "@", s)).strip()


def main() -> None:
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    tables = {p.name[:3]: {norm(s) for s in json.load(open(p)) if s} for p in src.glob("*.json")}
    base = tables["101"]
    seen: dict[str, str] = {}
    for code in ORDER:
        if code not in tables:
            continue
        new = sorted(s for s in tables[code] if s not in base and s not in seen)
        for s in new:
            seen[s] = code
        with open(out / f"new_{code}.txt", "w") as f:
            for s in new:
                f.write(("N " if len(s) <= 34 and not s.endswith(".") else "H ") + s + "\n")
        print(code, NAMES[code], len(tables[code]), "strings,", len(new), "first seen here")
    with open(out / "all_new.tsv", "w") as f:
        for s, code in sorted(seen.items()):
            f.write(f"{s}\t{NAMES[code]}\t{','.join(c for c in ORDER if s in tables.get(c, ()))}\n")
    gone = sorted(base - set().union(*(tables[c] for c in ORDER if c in tables)))
    (out / "only_epm2.txt").write_text("\n".join(gone) + "\n")


main()
