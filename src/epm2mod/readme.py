"""The generated parts of ``README.md``.

Some facts in the README repeat data that the repository holds elsewhere: the
pinned build and its SHA-256, the list of builds, the list of film looks. Those
parts are generated, so they cannot go out of date. Each one sits between two
marker comments::

    <!-- BEGIN GENERATED: name -->
    ...
    <!-- END GENERATED: name -->

``update`` replaces what is between the markers. Text outside them is never
touched. A test fails if the README is not up to date.
"""

from __future__ import annotations

import re
from typing import Callable

from .builds import all_descriptions, pinned_description
from .errors import BuildError
from .fileio import read_text, write_text
from .looks.films import load_films
from .paths import RepoPaths
from .stock import EPM2_V16

_BLOCK = re.compile(
    r"(<!-- BEGIN GENERATED: (?P<name>[a-z-]+) -->\n)(?P<body>.*?)"
    r"(<!-- END GENERATED: (?P=name) -->)",
    re.DOTALL,
)
_MARKER = re.compile(r"<!-- (?:BEGIN|END) GENERATED: [^>]*-->")


def cell(text: str) -> str:
    """Return ``text`` made safe for one cell of a Markdown table."""
    return " ".join(text.split()).replace("|", "\\|")


def pinned_block(paths: RepoPaths) -> str:
    """Return the text that names the pinned build and gives the two SHA-256 values."""
    pinned = pinned_description(paths)
    what = pinned.what[:1].lower() + pinned.what[1:]
    return (
        f"The pinned build is **`{pinned.name}`**: {what}. "
        f"We tested this build on a real E-PM2 on {pinned.camera_tested} "
        "([camera log](docs/camera-log.md)).\n\n"
        "| | sha256 |\n|---|---|\n"
        f"| Stock firmware, `{EPM2_V16.file_name}` | `{EPM2_V16.sha256}` |\n"
        f"| Pinned build, `{pinned.name}` | `{pinned.sha256}` |\n"
    )


def builds_block(paths: RepoPaths) -> str:
    """Return the table of all tested builds, the pinned one first."""
    pinned = pinned_description(paths)
    tested = [build for build in all_descriptions(paths) if build.tested]
    tested.sort(key=lambda build: (build.name != pinned.name, build.name))
    rows = [
        f"| `{build.name}`{' (pinned)' if build.name == pinned.name else ''} "
        f"| {cell(build.what)} | {len(build.specs)} | {build.camera_tested} "
        f"| `{build.sha256}` |"
        for build in tested
    ]
    head = (
        "| Build | What | Patch specs | Camera-tested | sha256 |\n"
        "|---|---|---|---|---|\n"
    )
    return head + "\n".join(rows) + "\n"


def films_block(paths: RepoPaths) -> str:
    """Return the table of film looks: menu name, film, the entry it replaces."""
    rows = [
        f"| {cell(film.label)} | {cell(film.film)} ({cell(film.medium)}) "
        f"| {cell(film.entry)} |"
        for film in load_films(paths).films
    ]
    return "| Menu name | Film | Replaces |\n|---|---|---|\n" + "\n".join(rows) + "\n"


#: The generated blocks, by marker name.
BLOCKS: dict[str, Callable[[RepoPaths], str]] = {
    "pinned-build": pinned_block,
    "builds": builds_block,
    "films": films_block,
}


def update(text: str, paths: RepoPaths) -> str:
    """Return README text with every generated block made fresh.

    Raises:
        BuildError: if a marker names a block that does not exist, a block has
            no markers or more than one pair, or a marker has no partner.
    """
    seen: list[str] = []

    def replace(match: re.Match[str]) -> str:
        name = match.group("name")
        if name not in BLOCKS:
            raise BuildError(f"README: unknown generated block '{name}'")
        seen.append(name)
        return match.group(1) + BLOCKS[name](paths) + match.group(4)

    result = _BLOCK.sub(replace, text)
    for name in BLOCKS:
        if seen.count(name) != 1:
            raise BuildError(
                f"README: the generated block '{name}' must be there once, "
                f"found {seen.count(name)} times"
            )
    if len(_MARKER.findall(text)) != 2 * len(seen):
        raise BuildError("README: a GENERATED marker has no partner")
    return result


def is_current(paths: RepoPaths) -> bool:
    """Return True if the README's generated blocks are up to date."""
    text = read_text(paths.readme)
    return update(text, paths) == text


def rewrite(paths: RepoPaths) -> bool:
    """Bring the README up to date. Return True if the file changed."""
    text = read_text(paths.readme)
    fresh = update(text, paths)
    if fresh == text:
        return False
    write_text(paths.readme, fresh)
    return True
