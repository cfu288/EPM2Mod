"""The generated parts of the documents.

Some facts in the documents repeat data that the repository holds elsewhere:
the pinned build and its SHA-256, the list of builds, the list of film looks.
Those parts are generated, so they cannot go out of date. Each one sits between
two marker comments, in one of the files listed in ``DOCUMENTS``::

    <!-- BEGIN GENERATED: name -->
    ...
    <!-- END GENERATED: name -->

``update`` replaces what is between the markers. Text outside them is never
touched. Each block must be there once, in any one of the documents. A test
fails if a document is not up to date.
"""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Callable
from pathlib import Path

from .builds import all_descriptions, pinned_description
from .errors import BuildError
from .fileio import read_text, write_text
from .looks.films import Film, load_bw_films, load_films, load_more_films
from .paths import RepoPaths
from .stock import EPM2_V16

_BLOCK = re.compile(
    r"(<!-- BEGIN GENERATED: (?P<name>[a-z-]+) -->\r?\n)(?P<body>.*?)"
    r"(<!-- END GENERATED: (?P=name) -->)",
    re.DOTALL,
)
_MARKER = re.compile(r"<!-- (?:BEGIN|END) GENERATED: [^>]*-->")


def cell(text: str) -> str:
    """Return ``text`` made safe for one cell of a Markdown table.

    White space becomes single spaces, ``|`` is escaped, and ``<`` and ``>``
    become entities, so the text cannot end the cell or hold a marker comment.
    """
    escaped = " ".join(text.split()).replace("&", "&amp;")
    return escaped.replace("<", "&lt;").replace(">", "&gt;").replace("|", "\\|")


def pinned_block(paths: RepoPaths) -> str:
    """Return the text that names the pinned build and gives the two SHA-256 values."""
    pinned = pinned_description(paths)
    what = cell(pinned.what[:1].lower() + pinned.what[1:]).rstrip(".")
    return (
        f"The pinned build is **`{pinned.name}`**: {what}. "
        f"We tested this build on a real E-PM2 on {pinned.camera_tested} "
        "([camera log](camera-log.md)).\n\n"
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


#: The art-filter entries in the order of the stock menu.
_STOCK_ORDER = (
    "Pop Art",
    "Soft Focus",
    "Pale&Light Color",
    "Light Tone",
    "Grainy Film",
    "Pin Hole",
    "Diorama",
    "Cross Process",
    "Gentle Sepia",
    "Dramatic Tone",
    "Key Line",
    "Watercolor",
)
#: Specs of the twelve-film builds: the one that names the first Portra entry "Portra 400", and the loader of
#: the build with Olympus's filters, whose default look file holds the same twelve films.
_TWELVE_SPECS = ("patches/films12bw-names.json", "patches/card-looks-5.json")


def pinned_films(paths: RepoPaths) -> list[tuple[str, Film]]:
    """Return the film looks of the pinned build: (menu name, film), in menu order.

    A build with the first seven films takes them from ``looks/films.json``.
    A twelve-film build adds the films of ``looks/more-films.json`` as
    ``looks/films-12-bw.json`` arranges them: the black-and-white film is in
    its entry, the colour film of that entry is in ``moved_to``, and the film
    that ``moved_to`` had is not in the build.
    """
    seven = load_films(paths).films
    if not set(_TWELVE_SPECS) & set(pinned_description(paths).specs):
        return [(film.label, film) for film in seven]
    more = {film.entry: film for film in load_more_films(paths).films}
    black_and_white = load_bw_films(paths)
    by_entry = {film.entry: film for film in seven}
    displaced = more.pop(black_and_white.mono.entry)
    more[black_and_white.moved_to] = dataclasses.replace(
        displaced, entry=black_and_white.moved_to
    )
    by_entry.update(more)
    by_entry[black_and_white.mono.entry] = black_and_white.mono
    rows = []
    for entry in _STOCK_ORDER:
        film = by_entry[entry]
        label = "Portra 400" if film.label == "Portra" else film.label
        rows.append((label, film))
    return rows


def films_block(paths: RepoPaths) -> str:
    """Return the table of film looks: menu name, film, the entry it replaces."""
    rows = [
        f"| {cell(label)} | {cell(film.film)} ({cell(film.medium)}) "
        f"| {cell(film.entry)} |"
        for label, film in pinned_films(paths)
    ]
    return "| Menu name | Film | Replaces |\n|---|---|---|\n" + "\n".join(rows) + "\n"


#: The files that may hold generated blocks, relative to the repository root.
DOCUMENTS = (
    "README.md",
    "docs/install.md",
    "docs/guide/film-looks.md",
    "builds/README.md",
)
#: Text that separates the documents when they are checked as one.
_JOIN = "\n\x00next document\x00\n"

#: The generated blocks, by marker name.
BLOCKS: dict[str, Callable[[RepoPaths], str]] = {
    "pinned-build": pinned_block,
    "builds": builds_block,
    "films": films_block,
}


def update(text: str, paths: RepoPaths) -> str:
    """Return document text with every generated block made fresh.

    Raises:
        BuildError: if a marker names a block that does not exist, a block has
            no markers or more than one pair, or a marker has no partner.
    """
    seen: list[str] = []

    def replace(match: re.Match[str]) -> str:
        """Return the block of one marker pair, made fresh."""
        name = match.group("name")
        if name not in BLOCKS:
            raise BuildError(f"documents: unknown generated block '{name}'")
        seen.append(name)
        return match.group(1) + BLOCKS[name](paths) + match.group(4)

    result = _BLOCK.sub(replace, text)
    for name in BLOCKS:
        if seen.count(name) != 1:
            raise BuildError(
                f"documents: the generated block '{name}' must be there once, "
                f"found {seen.count(name)} times"
            )
    if len(_MARKER.findall(text)) != 2 * len(seen):
        raise BuildError("documents: a GENERATED marker has no partner")
    return result


def _files(paths: RepoPaths) -> list[Path]:
    """Return the documents that hold generated blocks and are present."""
    found = [paths.resolve(relative) for relative in DOCUMENTS]
    return [path for path in found if path.exists()]


def generated_text(paths: RepoPaths) -> str:
    """Return the text of all documents with generated blocks, joined.

    Raises:
        BuildError: if none of the documents is there.
    """
    files = _files(paths)
    if not files:
        raise BuildError("none of the documents with generated parts was found")
    return _JOIN.join(read_text(path) for path in files)


def is_current(paths: RepoPaths) -> bool:
    """Return True if the generated blocks of all documents are up to date."""
    text = generated_text(paths)
    return update(text, paths) == text


def rewrite(paths: RepoPaths) -> bool:
    """Bring the documents up to date. Return True if a file changed."""
    files = _files(paths)
    before = generated_text(paths).split(_JOIN)
    after = update(_JOIN.join(before), paths).split(_JOIN)
    changed = False
    for path, old, new in zip(files, before, after):
        if old != new:
            write_text(path, new)
            changed = True
    return changed
