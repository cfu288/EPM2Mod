"""The generated parts of the documents (``epm2mod generate``).

Some facts in the documents repeat data that the repository holds elsewhere:
the pinned build and its SHA-256, the list of builds, the list of film looks,
the camera steps. Those parts are generated, so they cannot go out of date.
Each one sits between two marker comments, in one of the files listed in
``DOCUMENTS``::

    <!-- BEGIN GENERATED: name -->
    ...
    <!-- END GENERATED: name -->

``update`` replaces what is between the markers. Text outside them is never
touched. Each block must be there once, in any one of the documents.

The files in ``GENERATED_FILES`` are generated whole: the CLI reference
(``cli_reference``), from the command definitions of ``cli``. A test fails if a
document is not up to date.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from . import camera_steps, catalogue
from .builds import all_descriptions, pinned_description
from .errors import BuildError
from .fileio import read_text, write_text
from .looks import records
from .paths import RepoPaths

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
    stock = pinned.stock_firmware
    what = cell(pinned.what[:1].lower() + pinned.what[1:]).rstrip(".")
    return (
        f"The installer and `install` write the firmware **`{pinned.name}`**: {what}. "
        f"We tested this build on a real E-PM2 on {pinned.camera_tested} "
        "([camera log](camera-log.md)).\n\n"
        "| | sha256 |\n|---|---|\n"
        f"| Stock firmware, `{stock.file_name}` | `{stock.sha256}` |\n"
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
    """Return the table of every film a look file can hold.

    The firmware keeps Olympus's art filters; the films reach the camera in a look file (``looks/film-records.json``).
    The command-line name is what ``epm2mod install --film ART1=NAME`` and ``epm2mod films set --film ART1=NAME``
    take.
    """
    films = records.load(paths)
    rows = [
        f"| {cell(film.name)} | `{film.id}` | {cell(film.film)} ({cell(film.medium)}) "
        f"| {cell(film.kind)} |"
        for film in films.films.values()
    ]
    return (
        "| Menu name | Command-line name | Film | Type |\n|---|---|---|---|\n"
        + "\n".join(rows)
        + "\n"
    )


#: The films of the README's example ``install`` command, whose camera steps ``steps_block`` writes.
STEPS_EXAMPLE = ("ART1=portra-400",)


def steps_block(paths: RepoPaths) -> str:
    """Return the camera steps after ``epm2mod install`` writes the pinned build and films to the card, as a list.

    The films are ``STEPS_EXAMPLE``.
    """
    looks = records.looks_of_choices(records.load(paths), STEPS_EXAMPLE)
    steps = camera_steps.flash_steps(
        films=True,
        firmware=camera_steps.firmware_reads(pinned_description(paths).label),
        art_shows=catalogue.art_check(looks),
    )
    return "".join(f"{number}. {step.text}\n" for number, step in enumerate(steps, 1))


def _code(text: str) -> str:
    """Return ``text`` as inline code for a Markdown table cell."""
    return "`" + text.replace("|", "\\|") + "`"


def cli_reference(paths: RepoPaths) -> str:
    """Return the CLI reference page: every command, its arguments and defaults, its JSON keys and exit statuses.

    It is made from the command definitions (``cli.COMMANDS`` and ``cli.build_parser``), so it cannot go out of
    date.
    """
    import argparse

    from . import cli

    parser = cli.build_parser(cli.PROG, developer=True)
    subparsers = {}
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, sub in action.choices.items():
                subparsers[name] = sub
                for inner in sub._actions:
                    if isinstance(inner, argparse._SubParsersAction):
                        for child, child_parser in inner.choices.items():
                            subparsers[f"{name} {child}"] = child_parser
    lines = [
        "# Command-line reference",
        "",
        "<!-- Generated by `epm2mod generate` from src/epm2mod/cli.py. Do not edit. -->",
        "",
        "Run a command with `uv run epm2mod COMMAND` in a checkout, or with the launcher in the release folder "
        "(`./start.sh COMMAND`, `start.ps1 COMMAND`). `epm2mod COMMAND --help` shows the same text.",
        "",
        "## Rules",
        "",
        "- `--card DIR` is the top folder of an SD card. `-o FILE` is always a file, and never a file on an SD card "
        "that `epm2mod cards` lists (use `--card`).",
        "- Results go to stdout. Progress, hints and the camera steps go to stderr.",
        "- `--json` prints one document on stdout, on success and on failure (usage errors included). A file whose "
        "sha256 on the card is already right is not written again (`unchanged`).",
        "- `--dry-run` prints what would be written and replaced, and writes nothing.",
        "- No command asks a question. A refusal names the flag that overrides it (`--allow-untested`).",
        "- `--film ARTn=FILM` puts one film simulation in one ART slot: ART1 to ART12, as in the camera's ART menu "
        "(ART1 Pop Art ... ART12 Watercolor). A slot named twice is an error. A slot that is not named keeps its "
        "Olympus art filter. With no `--film`, `install` writes the firmware only.",
        "- In the release folder, the launcher's name (`./start.sh`, `.\\start.ps1`) takes the place of `epm2mod` "
        "in usage lines, examples and hints, and `--help` lists the commands for camera owners only.",
        "",
        "| Exit status | Means | What a caller does |",
        "|---|---|---|",
        *(
            f"| {status} | {cell(text)} | {cell(action)} |"
            for status, (text, action) in cli.EXIT_STATUSES.items()
        ),
        "",
        "## JSON documents",
        "",
        f"Every `--json` document has these keys (`schema` {cli.SCHEMA}). An added key does not change `schema`; a "
        "removed or renamed key, or a changed type, does. Ignore the keys you do not know. `a[].b` is the key `b` "
        "of each item of the list `a`; `a.b` is the key `b` of the object `a`.",
        "",
        *(f"- `{key}`: {text}" for key, text in cli.COMMON_JSON.items()),
    ]
    for group, note in cli.GROUPS.items():
        lines += ["", f"## {group}", "", f"These commands {note}."]
        for name, command in cli.COMMANDS.items():
            if command.group != group:
                continue
            sub = subparsers[name]
            usage = " ".join(sub.format_usage().split())
            usage = usage.removeprefix("usage: ")
            needs = "a checkout" if command.checkout else "no checkout"
            lines += [
                "",
                f"### {cli.PROG} {name}",
                "",
                command.summary,
                "",
                "```",
                usage,
                "```",
                "",
                f"- Output: {command.output}.",
                f"- Needs: {needs}. Network: {command.network or 'never'}.",
            ]
            rows = []
            for action in sub._actions:
                if action.help == argparse.SUPPRESS or isinstance(
                    action, (argparse._HelpAction, argparse._SubParsersAction)
                ):
                    continue
                flags = ", ".join(action.option_strings) or (
                    action.metavar or action.dest
                )
                if action.option_strings and action.nargs != 0:
                    flags += f" {action.metavar or action.dest.upper()}"
                default = (
                    ""
                    if action.default in (None, False, argparse.SUPPRESS)
                    else str(action.default)
                )
                rows.append(
                    f"| {_code(str(flags))} | {cell(action.help or '')} | {cell(default)} |"
                )
            if rows:
                lines += ["", "| Argument | What | Default |", "|---|---|---|", *rows]
            if command.json:
                lines += ["", "`--json` keys beside the keys of every document:", ""]
                lines += [f"- `{key}`: {text}" for key, text in command.json.items()]
            if command.exits:
                lines += [""] + [
                    f"- Exit {status}: {text}."
                    for status, text in command.exits.items()
                ]
            examples = [cli.named(line, cli.PROG) for line in command.examples]
            lines += ["", "Examples:", "", "```sh", *examples, "```"]
    return "\n".join(lines) + "\n"


#: The files that are generated whole, relative to the repository root.
GENERATED_FILES: dict[str, Callable[[RepoPaths], str]] = {
    "docs/cli.md": cli_reference,
}

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
    "camera-steps": steps_block,
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


def stale(paths: RepoPaths) -> list[Path]:
    """Return the documents whose generated parts are out of date."""
    files = _files(paths)
    before = generated_text(paths).split(_JOIN)
    after = update(_JOIN.join(before), paths).split(_JOIN)
    found = [path for path, old, new in zip(files, before, after) if old != new]
    for relative, make in GENERATED_FILES.items():
        path = paths.resolve(relative)
        if not path.is_file() or read_text(path) != make(paths):
            found.append(path)
    return found


def is_current(paths: RepoPaths) -> bool:
    """Return True if the generated parts of all documents are up to date."""
    return not stale(paths)


def rewrite(paths: RepoPaths) -> list[Path]:
    """Bring the documents up to date. Return the files that changed."""
    files = _files(paths)
    before = generated_text(paths).split(_JOIN)
    after = update(_JOIN.join(before), paths).split(_JOIN)
    changed = []
    for path, old, new in zip(files, before, after):
        if old != new:
            write_text(path, new)
            changed.append(path)
    for relative, make in GENERATED_FILES.items():
        path = paths.resolve(relative)
        text = make(paths)
        if not path.is_file() or read_text(path) != text:
            write_text(path, text)
            changed.append(path)
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
