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

import re
from collections.abc import Callable
from pathlib import Path

from .builds import all_descriptions, pinned_description
from .errors import BuildError
from .fileio import read_text, write_text
from .looks import records
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
        f"The installer and `make` build the firmware **`{pinned.name}`**: {what}. "
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


def films_block(paths: RepoPaths) -> str:
    """Return the table of every film a look file can hold, with the ART entry it is loaded into by default.

    The firmware keeps Olympus's art filters; the films reach the camera in a look file (``looks/film-records.json``).
    The installer and ``make`` write the twelve default films, one per ART entry; the others can be chosen. The
    command-line name is what ``epm2mod looks pack ART1=NAME`` takes.
    """
    films = records.load(paths)
    default = {slot.built_in: slot for slot in films.slots}
    rows = []
    for film in films.films.values():
        slot = default.get(film.id)
        where = f"ART {slot.art} ({slot.entry})" if slot else ""
        rows.append(
            f"| {cell(film.name)} | `{film.id}` | {cell(film.film)} ({cell(film.medium)}) "
            f"| {cell(film.kind)} | {cell(where)} |"
        )
    return (
        "| Menu name | Command-line name | Film | Type | In the default look file |\n|---|---|---|---|---|\n"
        + "\n".join(rows)
        + "\n"
    )


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


#: The site's id (``web/apps/site/src/features.ts``) of each feature guide in
#: ``docs/guide/``; None for a guide that is deliberately not on the site.
SITE_IDS: dict[str, str | None] = {
    "film-looks": "film-looks",
    "card-looks": "card-looks",
    "interval-shooting": "interval",
    "level-gauge": "level",
    "focus-peaking": "peaking",
    "lowest-shutter-speed": "lowest-ss",
    "debug-log": None,  # a tool for bug reports, not a camera feature
}
#: The site's feature list, relative to the repository root.
SITE_FEATURES = "web/apps/site/src/features.ts"


def feature_problems(paths: RepoPaths) -> list[str]:
    """Return what is missing between the feature guides, the README and the site.

    Every guide in ``docs/guide/`` must be linked from ``README.md`` and be named
    in ``SITE_IDS``; every site id there must be in the site's feature list.
    """
    guides = sorted(p.stem for p in paths.resolve("docs/guide").glob("*.md"))
    readme_text = read_text(paths.resolve("README.md"))
    site_path = paths.resolve(SITE_FEATURES)
    site_ids = (
        set(re.findall(r"\bid: '([^']+)'", read_text(site_path)))
        if site_path.exists()
        else set()
    )
    problems = []
    for guide in guides:
        if f"(docs/guide/{guide}.md)" not in readme_text:
            problems.append(f"README.md does not link docs/guide/{guide}.md")
        if guide not in SITE_IDS:
            problems.append(
                f"docs/guide/{guide}.md is not in readme.SITE_IDS: add its site id, or None"
            )
        elif SITE_IDS[guide] is not None and SITE_IDS[guide] not in site_ids:
            problems.append(f"{SITE_FEATURES} has no feature '{SITE_IDS[guide]}'")
    return problems
