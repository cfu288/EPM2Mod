"""The generated parts of ``README.md``.

Some facts in the README repeat data that the repository holds elsewhere: the
pinned build and its SHA-256, the list of builds, the list of film looks. Those
parts are generated, so they cannot go out of date. Each one sits between two
marker comments::

    <!-- BEGIN GENERATED: name -->
    ...
    <!-- END GENERATED: name -->

``update`` replaces what is between the markers. Text outside them is never
touched. ``tests/test_package.py`` fails if the README is not up to date.
"""

from __future__ import annotations

import re
from typing import Callable, Dict

from .builds import all_descriptions, pinned_description
from .errors import BuildError
from .looks.films import load_films
from .paths import RepoPaths
from .stock import EPM2_V16, StockFirmware

_BLOCK = re.compile(
    r"(<!-- BEGIN GENERATED: (?P<name>[a-z-]+) -->\n)(?P<body>.*?)"
    r"(<!-- END GENERATED: (?P=name) -->)",
    re.DOTALL,
)


def pinned_block(paths: RepoPaths, stock: StockFirmware = EPM2_V16) -> str:
    """Return the text that names the pinned build and gives the two SHA-256 values."""
    pinned = pinned_description(paths)
    return (
        f"The pinned build is **`{pinned.name}`**: {_lower_first(pinned.what)}. "
        f"It was flashed and tested on a real E-PM2 on {pinned.camera_tested} "
        "([camera log](docs/camera-log.md)).\n\n"
        "| | sha256 |\n|---|---|\n"
        f"| Stock firmware, `{stock.file_name}` | `{stock.sha256}` |\n"
        f"| Pinned build, `{pinned.name}` | `{pinned.sha256}` |\n"
    )


def builds_block(paths: RepoPaths, stock: StockFirmware = EPM2_V16) -> str:
    """Return the table of all tested builds, the pinned one first."""
    pinned = pinned_description(paths)
    tested = [build for build in all_descriptions(paths) if build.tested]
    tested.sort(key=lambda build: (build.name != pinned.name, build.name))
    rows = [
        f"| `{build.name}`{' (pinned)' if build.name == pinned.name else ''} "
        f"| {build.what} | {len(build.specs)} | {build.camera_tested} "
        f"| `{build.sha256}` |"
        for build in tested
    ]
    head = "| Build | What | Patch specs | Camera-tested | sha256 |\n|---|---|---|---|---|\n"
    return head + "\n".join(rows) + "\n"


def films_block(paths: RepoPaths, stock: StockFirmware = EPM2_V16) -> str:
    """Return the table of film looks: menu name, film, the entry it replaces."""
    rows = [
        f"| {film.label} | {film.film} ({film.medium}) | {film.entry} |"
        for film in load_films(paths).films
    ]
    return "| Menu name | Film | Replaces |\n|---|---|---|\n" + "\n".join(rows) + "\n"


#: The generated blocks, by marker name.
BLOCKS: Dict[str, Callable[[RepoPaths, StockFirmware], str]] = {
    "pinned-build": pinned_block,
    "builds": builds_block,
    "films": films_block,
}


def _lower_first(text: str) -> str:
    """Return ``text`` with a lower-case first letter."""
    return text[:1].lower() + text[1:]


def update(text: str, paths: RepoPaths, stock: StockFirmware = EPM2_V16) -> str:
    """Return README text with every generated block made fresh.

    Raises:
        BuildError: if a marker names a block that does not exist, or a block
            that should be there has no markers.
    """
    seen = set()

    def replace(match: "re.Match[str]") -> str:
        name = match.group("name")
        if name not in BLOCKS:
            raise BuildError(f"README: unknown generated block '{name}'")
        seen.add(name)
        return match.group(1) + BLOCKS[name](paths, stock) + match.group(4)

    result = _BLOCK.sub(replace, text)
    missing = sorted(set(BLOCKS) - seen)
    if missing:
        raise BuildError(
            f"README: no markers for generated block(s): {', '.join(missing)}"
        )
    return result


def is_current(paths: RepoPaths, stock: StockFirmware = EPM2_V16) -> bool:
    """Return True if the README's generated blocks are up to date."""
    text = paths.readme.read_text(encoding="utf-8")
    return update(text, paths, stock) == text


def rewrite(paths: RepoPaths, stock: StockFirmware = EPM2_V16) -> bool:
    """Bring the README up to date. Return True if the file changed."""
    text = paths.readme.read_text(encoding="utf-8")
    fresh = update(text, paths, stock)
    if fresh == text:
        return False
    paths.readme.write_text(fresh, encoding="utf-8")
    return True
