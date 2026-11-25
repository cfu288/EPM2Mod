"""The ``epm2mod`` command: it parses the arguments, calls the package's functions and formats their results.

The commands are in ``COMMANDS``, grouped by who uses them; ``epm2mod --help`` shows the groups (outside a checkout
only the commands for camera owners), and ``readme.cli_reference`` writes the CLI reference page from the same
definitions. The rules that every command follows:

1. Destinations: ``--card DIR`` is the top folder of an SD card; ``-o FILE`` is always a file, and never one on a
   listed SD card.
2. Results go to stdout; progress, hints and the camera steps go to stderr.
3. ``--json`` prints one document on stdout, on success and on failure (``SCHEMA``, ``COMMON_JSON``).
4. Exit statuses: ``EXIT_STATUSES`` (``errors``).
5. ``--dry-run`` on every command that writes: what would be written; nothing is written.
6. No prompts.
7. Usage lines, examples and hints name the program as the launcher calls it (``PROG_ENV``).

This module holds no knowledge of where the data is: it asks the locator (``catalogue.locate``) for everything. The
locations come from the project manifest and from the arguments ``--project``, ``--cache``, ``--stock`` and
``--out-dir``.
"""

from __future__ import annotations

import argparse
import datetime
import contextlib
import io
import json
import os
import signal
import subprocess
import sys
import traceback
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NoReturn

from . import __version__, camera_steps, catalogue, readme
from .builds import BuildDescription, check_test_date, description_path
from .cardio import Planned, output_path
from .catalogue import Locator
from .errors import (
    DIFFERS,
    INTERNAL,
    INTERRUPTED,
    BuildCheckError,
    BuildError,
    Epm2ModError,
    NotFoundError,
    RepositoryError,
    UnavailableError,
    UsageError,
)
from .eventlog import Dictionary, decode, load_dictionary
from .fileio import read_bytes, read_json, write_bytes
from .hashing import sha256_bytes
from .logsummary import summarize
from .paths import MANIFEST, RepoPaths
from .pipeline import (
    FileReport,
    Inspection,
    MakeResult,
    Outcome,
    clear_outputs,
    inspect_card,
    inspect_file,
    install,
    make,
    record_test,
    restore,
    set_films,
)
from .spec import apply_specs, load_spec
from .stock import STOCK_FIRMWARE, fetch, read_stock, stock_path

#: The version of the ``--json`` documents. A removed or renamed key, or a changed type, raises it; an added key
#: does not, and readers ignore keys they do not know.
SCHEMA = 2
#: The environment variable by which a launcher gives the name it is called by, for usage lines, examples and hints.
PROG_ENV = "EPM2MOD_PROG"
#: The program's name when no launcher names it.
PROG = "epm2mod"


def prog() -> str:
    """Return the program's name for usage lines, examples and hints: the launcher's (``PROG_ENV``), or ``epm2mod``."""
    return os.environ.get(PROG_ENV) or PROG


def named(text: str, name: str) -> str:
    """Return ``text`` with each command line that starts with ``epm2mod`` started with ``name``."""
    if name == PROG:
        return text
    if text.startswith(PROG + " "):
        text = name + text[len(PROG) :]
    return text.replace(f"'{PROG} ", f"'{name} ")


class Context:
    """What a command gets besides its arguments: the locator, found when it is first needed."""

    def __init__(self, find: Callable[[], Locator] = catalogue.locate) -> None:
        """Keep the function that finds the locator."""
        self._find = find
        self._found: Locator | None = None
        self._locations: dict[str, Path] = {}

    @property
    def locator(self) -> Locator:
        """The locator of the data (``catalogue.locate``), with the locations that the arguments give.

        Raises:
            RepositoryError: if there is no source of the data.
        """
        if self._found is None:
            found = self._find()
            self._found = (
                found.with_locations(**self._locations) if self._locations else found
            )
        return self._found

    def use(self, **locations: str | None) -> None:
        """Use the locations that the arguments give (``cache``, ``stock``, ``out_dir``; None: the manifest's)."""
        self._locations = {
            key: Path(value) for key, value in locations.items() if value is not None
        }
        if self._found is not None and self._locations:
            self._found = self._found.with_locations(**self._locations)

    def checkout(self) -> RepoPaths:
        """Return the checkout, for a developer or release command.

        Raises:
            RepositoryError: outside a checkout (exit status 6).
        """
        return self.locator.checkout()

    def has_checkout(self) -> bool:
        """Return True if the commands run in a checkout (else ``--help`` shows the commands for camera owners only)."""
        try:
            return self.locator.kind == "checkout"
        except RepositoryError:
            return False


Handler = Callable[[argparse.Namespace, Context], int]


@dataclass(frozen=True)
class Command:
    """One command of ``epm2mod``.

    Attributes:
        name: the command's name; a sub-command is ``films set``.
        group: who uses it: one of ``GROUPS``.
        summary: one line for the list of commands.
        output: what it writes or prints by default.
        checkout: True if it needs a checkout of the repository.
        network: when it uses the network, or "" for never.
        examples: one or two command lines, which start with ``epm2mod``.
        json: the keys of its ``--json`` document beside ``COMMON_JSON``, nested keys included (``files[].path``:
            the key ``path`` of each item of the list ``files``; ``build.name``: the key ``name`` of the object
            ``build``), or {} for no ``--json``.
        exits: what each exit status other than 0 and 2 means for it.
    """

    name: str
    group: str
    summary: str
    output: str
    checkout: bool
    network: str
    examples: tuple[str, ...]
    json: dict[str, str] = field(default_factory=dict)
    exits: dict[int, str] = field(default_factory=dict)


OWNERS, DEVELOPERS, RELEASES = (
    "For camera owners",
    "For developers",
    "For releases",
)
#: The groups of commands, in the order ``--help`` shows them.
GROUPS = {
    OWNERS: "work from the release folder, no checkout",
    DEVELOPERS: "need a checkout",
    RELEASES: "need a checkout",
}
#: The exit statuses of every command: what each one means, and what a caller does.
EXIT_STATUSES: dict[int, tuple[str, str]] = {
    0: ("done (also: an empty cards list)", ""),
    1: (
        'a check found a difference or a problem (generate --check, inspect "will not work", '
        "release not ready)",
        "show it; like diff and grep",
    ),
    2: ("wrong usage", "fix the command"),
    3: (
        "not found: no such path, file not recognised, unknown build",
        "fix the name or path",
    ),
    4: (
        "refused; a named flag overrides it (--allow-untested)",
        "ask the user, then pass the flag",
    ),
    5: (
        "not safe: a checksum, read-back or download sha256 differs, firmware for another model",
        "stop; never retry with a flag",
    ),
    6: (
        "environment: no network, no checkout, the card is not a camera card, not writable or full",
        "fix the setup, then retry",
    ),
    7: (
        "failed: an input is wrong (a build description, a patch spec, a fit, a file that does not fit)",
        "fix the input",
    ),
    INTERNAL: ("internal error (an uncaught exception)", "report"),
    INTERRUPTED: ("interrupted (any signal); no file half-written", ""),
}
#: The keys of every ``--json`` document.
COMMON_JSON = {
    "schema": f"the version of the document: {SCHEMA}",
    "command": "the command, like films set (null for a usage error before the command is known)",
    "version": "the tool's version",
    "ok": "true if the command did its work (exit status 0)",
    "error": "only on failure: what went wrong",
    "error.code": "a stable name of the kind of failure",
    "error.exit": "the exit status",
    "error.message": "the message, as on stderr",
    "error.override": "the flag that overrides a refusal (exit status 4), else null",
}
_DOWNLOAD = "when Olympus's firmware is not downloaded yet"
_FILES = {
    "files": "each file written, or with --dry-run to be written",
    "files[].path": "where it goes",
    "files[].role": "firmware or films",
    "files[].size": "its size in bytes",
    "files[].sha256": "its sha256 (null for a dry run of a build that is not camera-tested)",
    "files[].replaced": "true if a different file of that name was there and is replaced",
    "files[].unchanged": "true if that file already held these bytes: it was not written again",
}
_STEPS = {
    "camera_steps": "the steps on the camera",
    "camera_steps[].id": "what the step does, for a program (eject, flash, load-films, ...)",
    "camera_steps[].text": "what the user reads",
}
_BUILD = {
    "build": "the build",
    "build.name": "its name",
    "build.what": "what it gives the user",
    "build.sha256": "the sha256 of its firmware (null if it is not camera-tested)",
    "build.tested": "true if it passed a camera test",
    "build.camera_tested": "the date of that test, or null",
    "build.label": "the label on the camera's Firmware screen, or null",
}
_FILMS = {
    "films": "the films of the look pack",
    "films[].art": "the ART slot, 1 to 12",
    "films[].name": "the name the camera shows",
}
_CARD_WRITE = {
    "dry_run": "true if nothing was written",
    "card": "the card, or null",
}
_EJECT = {
    "ejected": "true if the card was ejected",
    "eject_error": "why the card was not ejected after --eject (the files are written), else null",
}
_REMOVED = {"removed": "the extra files removed from DCOLYMP"}
_FILMS_SET_JSON = {**_CARD_WRITE, **_FILES, **_FILMS, **_EJECT, **_STEPS}
_SET_EXITS = {6: "the card is not a camera card, not writable or full"}

COMMANDS: dict[str, Command] = {
    command.name: command
    for command in (
        Command(
            "cards",
            OWNERS,
            "List the SD cards in this computer.",
            "a line per card: its name, size, free space and folder",
            False,
            "",
            ("epm2mod cards",),
            {
                "cards": "the cards",
                "cards[].path": "the top folder of the card",
                "cards[].name": "the card's name",
                "cards[].size": "its size in bytes",
                "cards[].free": "its free space in bytes",
                "cards[].label": "the line that the text output shows",
            },
        ),
        Command(
            "install",
            OWNERS,
            "Write EPM2Mod to the SD card, and the look pack if --film is given.",
            "the firmware on the card, and the look pack if --film is given; then the camera steps",
            False,
            _DOWNLOAD,
            (
                "epm2mod install --card /path/to/card",
                "epm2mod install --card /path/to/card --film ART1=portra-400 --film ART2=velvia",
            ),
            {
                **_CARD_WRITE,
                **_BUILD,
                **_FILES,
                **_REMOVED,
                **_FILMS,
                **_EJECT,
                **_STEPS,
            },
            {
                3: "no build of that name",
                4: "a build without a passed camera test, without --allow-untested",
                5: "a read-back or the sha256 of the result differs, or the firmware is for another model",
                6: "no network, or the card is not a camera card, not writable or full",
            },
        ),
        Command(
            "films",
            OWNERS,
            "List the film simulations and the 12 ART slots.",
            "a line per film: menu name, command-line name, film, type; then a line per ART slot with its Olympus "
            "art filter",
            False,
            "",
            ("epm2mod films",),
            {
                "films": "the films",
                "films[].id": "the command-line name",
                "films[].name": "the menu name",
                "films[].film": "the film",
                "films[].kind": "the type",
                "films[].medium": "how the film was simulated",
                "films[].note": "a remark, or an empty text",
                "slots": "the 12 ART slots",
                "slots[].art": "the slot, 1 to 12",
                "slots[].entry": "its Olympus art filter",
            },
        ),
        Command(
            "films set",
            OWNERS,
            "Write only the look pack.",
            "the look pack on the card or at FILE; then the camera steps",
            False,
            "",
            (
                "epm2mod films set --card /path/to/card --film ART2=velvia --film ART6=double-x",
                "epm2mod films set -o EPM2LOOK.BIN --film ART1=portra-400",
            ),
            _FILMS_SET_JSON,
            _SET_EXITS,
        ),
        Command(
            "restore",
            OWNERS,
            "Write Olympus's original firmware, to remove EPM2Mod.",
            "the original firmware on the card or at FILE; then the camera steps",
            False,
            _DOWNLOAD,
            (
                "epm2mod restore --card /path/to/card",
                "epm2mod restore -o E1019999.BIN",
            ),
            {**_CARD_WRITE, **_FILES, **_REMOVED, **_EJECT, **_STEPS},
            {
                5: "the download or a read-back differs",
                6: "no network, or a card problem",
            },
        ),
        Command(
            "inspect",
            OWNERS,
            "Say what a firmware file, a look pack or an SD card holds.",
            "a report per file (model, build, version, sha256, films) and what will not work",
            False,
            "",
            ("epm2mod inspect --card /path/to/card", "epm2mod inspect E1019999.BIN"),
            {
                "card": "the card, or null",
                "files": "a report per file",
                "files[].path": "the file",
                "files[].kind": "firmware or films",
                "files[].size": "its size in bytes",
                "files[].sha256": "its sha256",
                "files[].model": "the camera model of a firmware file, else null",
                "files[].build": "the build a firmware file is (a build name, or Olympus original), or null",
                "files[].version": "the firmware's version, or null",
                "files[].checksums_ok": "for a firmware file, true if every block's checksum is right, else null",
                "files[].films": "the films of a look pack",
                "files[].films[].art": "the ART slot",
                "files[].films[].name": "the name the camera shows",
                "files[].films[].kind": "colour or black-and-white",
                "files[].problem": "what is wrong with the file, or null",
                "problems": "what will not work, in words",
            },
            {
                1: "something will not work (see problems)",
                3: "no such file, a file it does not know, or a card with neither file",
            },
        ),
        Command(
            "serve",
            OWNERS,
            "Open the installer page in the browser.",
            "the page's address; the page writes the card",
            False,
            _DOWNLOAD,
            ("epm2mod serve", "epm2mod serve --no-browser --port 8765"),
        ),
        Command(
            "make",
            DEVELOPERS,
            "Make a build into the output folder.",
            "NAME.BIN, and DCOLYMP with the firmware as on the card, in the output folder",
            True,
            _DOWNLOAD,
            (
                "epm2mod make epm2mod-2026.11.19",
                "epm2mod make debug-log -o E1019999.BIN",
            ),
            {
                "dry_run": "true if nothing was written",
                **_BUILD,
                "sha256": "the firmware's sha256 (null for a dry run of a candidate)",
                **_FILES,
            },
            {3: "no build of that name", 5: "the result is not the recorded build"},
        ),
        Command(
            "builds",
            DEVELOPERS,
            "List the build descriptions and the pinned one.",
            "a line per build",
            True,
            "",
            ("epm2mod builds",),
            {
                "pinned": "the name of the pinned build",
                "builds": "the builds",
                **{
                    f"builds[].{key[len('build.'):]}": text
                    for key, text in _BUILD.items()
                    if key != "build"
                },
                "builds[].specs": "the number of its patch specs",
            },
        ),
        Command(
            "init",
            DEVELOPERS,
            "Set up a checkout: the MN103 binutils, Node, the emulator, Olympus's firmware, "
            "the firmware map, the commit hooks.",
            "a line per item; with --check, what is present and what is missing, and nothing is changed",
            True,
            "for what is missing: Olympus's firmware, the git submodules, a Node version through nvm",
            ("epm2mod init", "epm2mod init --check"),
            {},
            {1: "with --check: an item is missing"},
        ),
        Command(
            "lint",
            DEVELOPERS,
            "Print what in a build may be harmful and is not proven safe.",
            "WARN lines: transfers to late-loaded code that are safe by timing or inference only, the "
            "early-loaded space the build uses, first code. Warnings do not change the exit status",
            True,
            "",
            ("epm2mod lint NAME",),
            {},
            {
                6: "the report cannot be made (Olympus's firmware or the MN103 objdump is missing)"
            },
        ),
        Command(
            "pin",
            DEVELOPERS,
            "Record a passed camera test and pin the build.",
            "the build description with the test record, and the pointer to the pinned build",
            True,
            "",
            ("epm2mod pin NAME --date 2026-11-19 --sha256 HEX",),
            {},
            {5: "the build does not give that sha256"},
        ),
        Command(
            "apply",
            DEVELOPERS,
            "Apply patch specs without a build description.",
            "the firmware file at FILE",
            True,
            "",
            ("epm2mod apply SPEC --from OLY_E_101_1600_0000_0000.BIN -o test.BIN",),
            {},
            {
                3: "the --from file is missing",
                5: "the result is not the sha256 the spec states",
            },
        ),
        Command(
            "fetch-stock",
            DEVELOPERS,
            "Download Olympus's firmware of the pinned build and check it.",
            "the firmware in the cache folder, and its path",
            True,
            _DOWNLOAD,
            ("epm2mod fetch-stock",),
            {
                "path": "where the file is kept",
                "sha256": "its sha256",
                "downloaded": "true if it was downloaded now",
                "dry_run": "true if nothing was downloaded",
            },
            {5: "the download is not the right file", 6: "no network"},
        ),
        Command(
            "films pack",
            DEVELOPERS,
            "Write a look pack from a look list of fit files, for films that are not in the catalogue yet.",
            "the look pack on the card or at FILE; then the camera steps",
            True,
            "",
            ("epm2mod films pack LIST --card /path/to/card",),
            _FILMS_SET_JSON,
            _SET_EXITS,
        ),
        Command(
            "generate",
            DEVELOPERS,
            "Write the generated parts of the documents and the CLI reference.",
            "the files it wrote; with --check, the files that differ",
            True,
            "",
            ("epm2mod generate", "epm2mod generate --check"),
            {},
            {1: "with --check: a file differs from the generated one"},
        ),
        Command(
            "log",
            DEVELOPERS,
            "Decode a camera log file (EPM2LOG.BIN).",
            "a short report",
            True,
            "",
            ("epm2mod log EPM2LOG.BIN", "epm2mod log EPM2LOG.BIN --json"),
            {
                "events": "the events in order, each an object with the keys that the event dictionary gives it",
            },
        ),
        Command(
            "package",
            RELEASES,
            "Write the release zip.",
            "EPM2Mod-VERSION.zip in the output folder",
            True,
            "",
            ("epm2mod package --release-version 2026.11.19-dev",),
            {
                "dry_run": "true if nothing was written",
                "zip": "the zip's path",
                "sha256": "the zip's sha256 (null for a dry run)",
                "contents": "the files in the zip",
            },
        ),
        Command(
            "release",
            RELEASES,
            "Check that the repository is ready for the next release, and name it.",
            "the release notes and the tag's name. It creates no tag: the release workflow on GitHub "
            "runs this command, then makes, tests, tags and publishes the release",
            True,
            "the network for the checks of CI",
            (
                "epm2mod release",
                "epm2mod release --final",
                "epm2mod release --build NAME",
            ),
            {
                "ready": "true if the release can be made",
                "problems": "why not, if it cannot",
                "tag": "the tag of the release, like v2026.11.19-rc.1 (null if not ready)",
                "release_version": "the release's version: the tag without its v (null if not ready)",
                "commit": "the commit that the release is made from (null if not ready)",
                "notes": "the release notes (null if not ready)",
                "sha256": "the sha256 of the firmware that the release installs (null if not ready)",
                "day": "the day of the release; give it as --day to plan the same release on a later day "
                "(null if not ready)",
            },
            {1: "the repository is not ready for a release"},
        ),
    )
}


def _progress(line: str) -> None:
    """Print a progress line on stderr."""
    print(line, file=sys.stderr, flush=True)


def _hint(text: str) -> None:
    """Print a hint on stderr, with the program's name in its command lines."""
    print(named(text, prog()), file=sys.stderr)


def _print_steps(steps: Sequence[camera_steps.Step]) -> None:
    """Print the camera steps on stderr, numbered."""
    if steps:
        _hint("On the camera:")
        for number, item in enumerate(steps, 1):
            _hint(f"  {number}. {item.text}")


def _document(command: str | None, ok: bool, **values: Any) -> None:
    """Print a ``--json`` document on stdout."""
    document = {
        "schema": SCHEMA,
        "command": command,
        "version": __version__,
        "ok": ok,
        **values,
    }
    print(json.dumps(document, indent=1))


def _error_json(
    code: str, status: int, message: str, override: str | None = None
) -> dict[str, Any]:
    """Return the ``error`` object of a ``--json`` document."""
    return {"code": code, "exit": status, "message": message, "override": override}


def _build_json(build: BuildDescription | None) -> dict[str, Any] | None:
    """Return a build for ``--json``."""
    if build is None:
        return None
    return {
        "name": build.name,
        "what": build.what,
        "sha256": build.sha256,
        "tested": build.tested,
        "camera_tested": build.camera_tested,
        "label": build.label,
    }


def _file_lines(files: Sequence[Planned], dry_run: bool) -> list[str]:
    """Return a result line per file."""
    lines = []
    for planned in files:
        if planned.unchanged:
            verb = "unchanged"
        elif dry_run:
            verb = "would replace" if planned.replaces else "would write"
        else:
            verb = "replaced" if planned.replaces else "wrote"
        sha = planned.content.sha256 or "not known before it is made"
        lines.append(f"{verb} {planned.path} ({planned.role}, sha256 {sha})")
    return lines


def _card(text: str | None) -> Path | None:
    """Return the card folder of ``--card``.

    Raises:
        UsageError: if the text is empty.
    """
    if text is None:
        return None
    if not text:
        raise UsageError("--card needs the top folder of the SD card")
    return Path(text)


def _out(text: str | None) -> Path | None:
    """Return the file of ``-o FILE`` (``cardio.output_path``), or None."""
    return None if text is None else output_path(text)


def _report_outcome(args: argparse.Namespace, outcome: Outcome) -> int:
    """Print what a command for camera owners did, and the camera steps."""
    if args.json:
        values: dict[str, Any] = {
            "dry_run": outcome.dry_run,
            "card": None if outcome.card is None else str(outcome.card),
            "build": _build_json(outcome.build),
            "files": [planned.to_json() for planned in outcome.files],
            "removed": [str(path) for path in outcome.removed],
            "films": [
                {"art": look.slot + 1, "name": look.name} for look in outcome.looks
            ],
            "ejected": outcome.ejected,
            "eject_error": outcome.eject_error,
            "camera_steps": [item.to_json() for item in outcome.steps],
        }
        keys = COMMANDS[args.command_name].json
        _document(
            args.command_name,
            True,
            **{key: value for key, value in values.items() if key in keys},
        )
    else:
        verb = "would remove" if outcome.dry_run else "removed"
        lines = [f"{verb} {path}" for path in outcome.removed]
        lines += _file_lines(outcome.files, outcome.dry_run)
        lines += [f"  ART{look.slot + 1:<2} {look.name}" for look in outcome.looks]
        print("\n".join(lines))
    if outcome.ejected:
        _hint(f"ejected {outcome.card}")
    if outcome.eject_error is not None:
        _hint(f"warning: {outcome.eject_error}")
    if not outcome.dry_run:
        _print_steps(outcome.steps)
    return 0


def _cards(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod cards``: the SD cards plugged into this computer."""
    from .cards import cards, describe

    found = cards()
    if args.json:
        _document(
            args.command_name,
            True,
            cards=[
                {
                    "path": str(card.path),
                    "name": card.name,
                    "size": card.size,
                    "free": card.free,
                    "label": describe(card),
                }
                for card in found
            ],
        )
    else:
        for card in found:
            print(describe(card))
    if not found:
        _hint("no SD card found: plug one in")
    return 0


def _install(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod install``."""
    outcome = install(
        ctx.locator,
        _card(args.card),
        args.films or [],
        build=args.build,
        allow_untested=args.allow_untested,
        dry_run=args.dry_run,
        eject=args.eject,
        log=_progress,
    )
    return _report_outcome(args, outcome)


def _films(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod films`` (the list), ``films set`` or ``films pack``."""
    if args.action == "set":
        return _films_set(args, ctx)
    if args.action == "pack":
        return _films_pack(args, ctx)
    films = catalogue.films(ctx.locator)
    if args.json:
        _document(
            args.command_name,
            True,
            films=[
                {
                    "id": film.id,
                    "name": film.name,
                    "film": film.film,
                    "kind": film.kind,
                    "medium": film.medium,
                    "note": film.note,
                }
                for film in films.films.values()
            ],
            slots=[{"art": slot.art, "entry": slot.entry} for slot in films.slots],
        )
        return 0
    print(f"{'Menu name':<17} {'Command-line name':<18} {'Film':<34} Type")
    for film in films.films.values():
        print(f"{film.name:<17} {film.id:<18} {film.film:<34} {film.kind}")
    print()
    print(f"{'ART slot':<9} Olympus art filter")
    for slot in films.slots:
        print(f"{'ART' + str(slot.art):<9} {slot.entry}")
    return 0


def _films_pack(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod films pack``: a film file from a look list of fit files (developers)."""
    checkout = ctx.checkout()
    try:
        from .looks import lookpack
    except ModuleNotFoundError as error:
        raise _numpy_needed(error) from None
    args.command_name = "films pack"
    looks = lookpack.load_list(checkout, Path(args.list))
    outcome = set_films(
        ctx.locator,
        [],
        card=_card(args.card),
        out=_out(args.out),
        dry_run=args.dry_run,
        eject=args.eject,
        looks=looks,
    )
    return _report_outcome(args, outcome)


def _films_set(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod films set``: write only the film file."""
    args.command_name = "films set"
    outcome = set_films(
        ctx.locator,
        args.films,
        card=_card(args.card),
        out=_out(args.out),
        dry_run=args.dry_run,
        eject=args.eject,
    )
    return _report_outcome(args, outcome)


def _restore(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod restore``: Olympus's original firmware to the card or a file."""
    outcome = restore(
        ctx.locator,
        card=_card(args.card),
        out=_out(args.out),
        dry_run=args.dry_run,
        eject=args.eject,
        log=_progress,
    )
    return _report_outcome(args, outcome)


def _report_lines(report: FileReport) -> list[str]:
    """Return the lines that describe one file."""
    lines = [
        f"{report.path}: {report.kind}, {report.size} bytes, sha256 {report.sha256}"
    ]
    if report.kind == "firmware":
        build = report.build or "not a build this folder knows"
        lines.append(
            f"  model {report.model}, build {build}, version {report.version or 'not known'}"
        )
    for film in report.films:
        lines.append(f"  ART{film['art']:<2} {film['name']} ({film['kind']})")
    return lines


def _inspect(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod inspect``: say what a file or a card holds."""
    if (args.file is None) == (args.card is None):
        raise UsageError("give a FILE or --card DIR")
    found: Inspection = (
        inspect_file(ctx.locator, Path(args.file))
        if args.file is not None
        else inspect_card(ctx.locator, Path(args.card))
    )
    ok = not found.problems
    if args.json:
        error = (
            {}
            if ok
            else {
                "error": _error_json(
                    "will_not_work", DIFFERS, "; ".join(found.problems)
                )
            }
        )
        _document(
            args.command_name,
            ok,
            card=None if found.card is None else str(found.card),
            files=[report.to_json() for report in found.files],
            problems=list(found.problems),
            **error,
        )
    else:
        print(
            "\n".join(line for report in found.files for line in _report_lines(report))
        )
        for problem in found.problems:
            print(f"will not work: {problem}")
    return 0 if ok else DIFFERS


def _serve(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod serve``: the local app, until the process is stopped."""
    from .serve import serve

    serve(ctx.locator, port=args.port, browser=not args.no_browser)
    return 0


def _make(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod make``.

    What an earlier run left is removed before the description is read: first the card folder, then the image of
    the build.
    """
    checkout = ctx.checkout()
    if not args.dry_run:
        clear_outputs(checkout, None)
        clear_outputs(checkout, args.build)
    description = checkout.build(args.build)
    result: MakeResult = make(
        checkout,
        description,
        log=_progress,
        output=_out(args.out),
        dry_run=args.dry_run,
    )
    if args.json:
        _document(
            args.command_name,
            True,
            dry_run=args.dry_run,
            build=_build_json(description),
            sha256=result.sha256,
            files=[planned.to_json() for planned in result.files],
        )
    else:
        print("\n".join(_file_lines(result.files, args.dry_run)))
    if not args.dry_run:
        _hint(
            f"To write a card: epm2mod install --card DIR --build {description.name}"
            + ("" if description.tested else " --allow-untested")
        )
    return 0


def _builds(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod builds``."""
    checkout = ctx.checkout()
    pinned = checkout.pinned_build().name
    found = checkout.all_builds()
    if args.json:
        _document(
            args.command_name,
            True,
            pinned=pinned,
            builds=[
                {**(_build_json(build) or {}), "specs": len(build.specs)}
                for build in found
            ],
        )
        return 0
    for build in found:
        state = f"tested {build.camera_tested}" if build.tested else "candidate"
        mark = " (pinned)" if build.name == pinned else ""
        print(f"{build.name}{mark}: {build.what} [{state}, {len(build.specs)} specs]")
    return 0


def _init(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod init``: set up the checkout, or with ``--check`` report what is missing."""
    from .init import init

    missing = init(ctx.checkout(), args.check, print)
    if missing:
        _hint("missing: " + ", ".join(missing) + ". To set them up: epm2mod init")
    return DIFFERS if missing else 0


def _lint(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod lint``: the project's lint tool, ``TOOL DESCRIPTION``.

    Warnings do not fail the command. A report that cannot be made does (exit status 6): no warning is not the
    same as no report.
    """
    checkout = ctx.checkout()
    checkout.build(
        args.build
    )  # an unknown or malformed build is an error, not a warning
    tool = checkout.lint_tool
    path = description_path(checkout, args.build)
    try:
        done = subprocess.run(
            [sys.executable, str(tool), str(path)], cwd=checkout.root, check=False
        )
    except OSError as error:
        raise UnavailableError(f"the lint cannot run: {error}") from None
    if done.returncode != 0:
        raise UnavailableError(
            f"{args.build} is not linted: {checkout.relative(tool)} could not make its report "
            "(run 'epm2mod init --check')"
        )
    return 0


def _pin(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod pin``."""
    checkout = ctx.checkout()
    try:
        check_test_date(args.date, datetime.date.today())
    except BuildError as error:
        raise UsageError(str(error)) from None
    record_test(
        checkout,
        checkout.build(args.build),
        args.sha256,
        args.date,
        log=lambda line: print(named(line, prog())),
        dry_run=args.dry_run,
        keep_pinned=args.no_pin,
    )
    return 0


def _apply(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod apply``."""
    checkout = ctx.checkout()
    out = output_path(args.out)
    specs = [load_spec(Path(spec)) for spec in args.specs]
    source = read_bytes(Path(args.source), NotFoundError)
    applied = apply_specs(source, specs)
    if args.verbose:
        _hint("\n".join(applied.log))
    digest = sha256_bytes(applied.image)
    expected = specs[0].expected_sha256 if len(specs) == 1 else None
    if expected is not None and expected != digest:
        raise BuildCheckError(
            f"{specs[0].name}: the result has sha256 {digest}, "
            f"the spec expects {expected}; nothing was written"
        )
    try:
        is_stock = any(
            out.resolve() == stock_path(checkout, stock).resolve()
            for stock in STOCK_FIRMWARE.values()
        )
    except (OSError, RuntimeError) as error:
        raise BuildError(f"{out}: cannot be used as a path: {error}") from None
    if is_stock:
        raise UsageError(f"{out} is the stock firmware file; give another name")
    if args.dry_run:
        print(f"would write {out} (sha256 {digest})")
        return 0
    write_bytes(out, applied.image, read_back=True)
    print(f"wrote {out} ({applied.changed_bytes} bytes differ from stock)")
    print(f"sha256 {digest}")
    return 0


def _fetch_stock(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod fetch-stock``: the stock firmware of the pinned build."""
    checkout = ctx.checkout()
    stock = checkout.pinned_build().stock_firmware
    path = stock_path(checkout, stock)
    there = path.exists()
    if args.dry_run:
        if there:
            read_stock(checkout, stock)
    else:
        fetch(checkout, stock, log=_progress)
    if args.json:
        _document(
            args.command_name,
            True,
            path=str(path),
            sha256=stock.sha256,
            downloaded=not there and not args.dry_run,
            dry_run=args.dry_run,
        )
    else:
        verb = "would download to" if args.dry_run and not there else "kept at"
        print(f"{verb} {path}")
    return 0


def _numpy_needed(error: ModuleNotFoundError) -> UnavailableError:
    """Return the error to report when numpy is missing, or raise ``error``."""
    if error.name != "numpy":
        raise error
    return UnavailableError(
        "numpy is needed to read fit files. In a checkout, 'uv run' installs it."
    )


def _generate(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod generate``: write (or, with ``--check``, compare) the generated parts of the documents."""
    checkout = ctx.checkout()
    if not args.check:
        written = readme.rewrite(checkout)
        print("\n".join(f"wrote {path}" for path in written) or "documents: no change")
        return 0
    problems = readme.feature_problems(checkout)
    for problem in problems:
        print(f"feature list: {problem}")
    stale_documents = readme.stale(checkout)
    for path in stale_documents:
        print(f"{path}: the generated parts are out of date")
    if stale_documents:
        _hint("run 'epm2mod generate'")
    if stale_documents or problems:
        return DIFFERS
    print("the generated parts of the documents are up to date")
    return 0


def _dictionaries(args: argparse.Namespace, checkout: RepoPaths) -> list[Dictionary]:
    """Return the dictionaries for ``epm2mod log``, the main one first.

    Without ``--dict`` these are the locator's event dictionaries: the current one and, for the logs of older
    builds, the older ones. The art codes of the film slots get the film labels of the film list, if it is there.
    """
    sources = [Path(args.dict)] if args.dict else checkout.event_dictionaries()
    words = load_dictionary(read_json(sources[0]))
    found = [words]
    for other in sources[1:]:
        found.append(load_dictionary(read_json(other), inherit=words))
    return found


def _log(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod log``: print a short report on a camera log, or its events as one ``--json`` document."""
    words, *older = _dictionaries(args, ctx.checkout())
    others = {other.build_id: other for other in older}
    lines = list(decode(read_bytes(Path(args.file)), words, others))
    if args.json:
        _document(args.command_name, True, events=lines)
        return 0
    print("\n".join(summarize(lines)))
    return 0


def _package(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod package``: write the release zip."""
    from .release import make_release, release_description, release_files, zip_path

    checkout = ctx.checkout()
    version = args.release_version
    release_description(checkout, version)  # refuses a bad version
    folder = Path(args.out_dir) if args.out_dir else checkout.output_folder()
    contents = [name for name, _ in release_files(checkout, version)]
    if args.dry_run:
        out, digest = zip_path(folder, version), None
    else:
        out = make_release(checkout, folder, version)
        digest = sha256_bytes(out.read_bytes())
    if args.json:
        _document(
            args.command_name,
            True,
            dry_run=args.dry_run,
            zip=str(out),
            sha256=digest,
            contents=contents,
        )
    elif args.dry_run:
        print(f"would write {out}: {len(contents)} files")
    else:
        print(f"wrote {out}: {out.stat().st_size} bytes, sha256 {digest}")
    return 0


def _release(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod release``: check the repository and show the next release. The release workflow makes it."""
    from .releasing import plan

    checkout = ctx.checkout()
    if args.build is not None and args.final:
        raise UsageError(
            "--build makes a test release: a final release holds the pinned build"
        )
    release, problems = plan(checkout, final=args.final, build=args.build, day=args.day)
    if args.json:
        _document(
            args.command_name,
            True,
            ready=release is not None,
            problems=problems,
            tag=release and release.tag,
            release_version=release and release.tag[1:],
            commit=release and release.commit,
            notes=release and release.notes,
            sha256=release and release.sha256,
            day=release and release.day,
        )
    elif release is None:
        for problem in problems:
            print(f"not ready: {problem}")
    else:
        print(release.notes)
        _hint(
            f"ready: {release.tag} on {release.commit[:7]}. To release it: "
            f"gh workflow run release -f kind=rc -f day={release.day} -f dry_run=false "
            "(kind=final for everyone)"
        )
    return DIFFERS if release is None else 0


#: The handler of each command.
HANDLERS: dict[str, Handler] = {
    "cards": _cards,
    "install": _install,
    "films": _films,
    "restore": _restore,
    "inspect": _inspect,
    "serve": _serve,
    "make": _make,
    "builds": _builds,
    "init": _init,
    "lint": _lint,
    "pin": _pin,
    "apply": _apply,
    "fetch-stock": _fetch_stock,
    "generate": _generate,
    "log": _log,
    "package": _package,
    "release": _release,
}


def _text(command: Command) -> str:
    """Return the description of a command's ``--help``: what it does, its output and what it needs."""
    needs = "a checkout of the repository" if command.checkout else "no checkout"
    lines = [
        command.summary,
        "",
        f"Output: {command.output}.",
        f"Needs: {needs}. Network: {command.network or 'never'}.",
    ]
    if command.json:
        top = [key for key in command.json if "." not in key and "[" not in key]
        lines.append(
            "--json: one document with "
            + ", ".join([*(k for k in COMMON_JSON if "." not in k), *top])
            + "."
        )
    return "\n".join(lines)


def _epilog(command: Command, name: str) -> str:
    """Return the examples at the end of a command's ``--help``."""
    return "examples:\n" + "\n".join(
        f"  {named(line, name)}" for line in command.examples
    )


def _top_help(name: str, developer: bool) -> str:
    """Return the list of commands of ``epm2mod --help``, by group; without ``developer``, the owners' group only."""
    blocks = []
    for group, note in GROUPS.items():
        if group != OWNERS and not developer:
            continue
        lines = [f"{group} ({note}):"]
        for command in COMMANDS.values():
            if command.group == group:
                lines.append(f"  {command.name:<12} {command.summary}")
        blocks.append("\n".join(lines))
    blocks.append(f"examples:\n  {name} install --card /path/to/card\n  {name} films")
    return "\n\n".join(blocks)


class _Parser(argparse.ArgumentParser):
    """An argument parser whose usage errors become a ``UsageError`` when the run prints ``--json``."""

    json_errors = False

    def error(self, message: str) -> NoReturn:
        """Raise ``UsageError`` for ``--json``; else print the usage and the error, and exit 2."""
        if self.json_errors:
            raise UsageError(message)
        super().error(message)


def _add_json(parser: argparse.ArgumentParser) -> None:
    """Add ``--json``."""
    parser.add_argument(
        "--json",
        action="store_true",
        help=f"print one JSON document (schema {SCHEMA}) on stdout",
    )


def _add_dry_run(parser: argparse.ArgumentParser) -> None:
    """Add ``--dry-run``."""
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would be written and replaced; write nothing",
    )


def _add_eject(parser: argparse.ArgumentParser) -> None:
    """Add ``--eject``."""
    parser.add_argument(
        "--eject", action="store_true", help="eject the card after the write"
    )


def _add_films(parser: argparse.ArgumentParser, name: str, required: bool) -> None:
    """Add ``--film ARTn=FILM``, which can be given more than once."""
    parser.add_argument(
        "--film",
        dest="films",
        action="append",
        required=required,
        metavar="ARTn=FILM",
        help="a film simulation for an ART slot: ART1 (Pop Art) to ART12 (Watercolor), names from "
        f"'{name} films'. Give it once per slot. The slots that are not named keep their Olympus art filter",
    )


def _add_stock(parser: argparse.ArgumentParser) -> None:
    """Add ``--cache DIR`` and ``--stock FILE``: where Olympus's firmware is."""
    parser.add_argument(
        "--cache",
        metavar="DIR",
        help="the folder that keeps Olympus's firmware; default: the project's cache folder",
    )
    parser.add_argument(
        "--stock",
        metavar="FILE",
        help="use this copy of Olympus's firmware (checked by its sha256); download nothing",
    )


def _add_destination(parser: argparse.ArgumentParser) -> None:
    """Add ``--card DIR`` and ``-o FILE``, one of which is needed."""
    where = parser.add_mutually_exclusive_group(required=True)
    where.add_argument("--card", metavar="DIR", help="the top folder of the SD card")
    where.add_argument(
        "-o",
        "--out",
        metavar="FILE",
        help="the file to write; not on an SD card (use --card)",
    )


def _add_action(
    actions: Any, action: str, name: str, developer: bool
) -> argparse.ArgumentParser:
    """Add the sub-command ``films ACTION``; a developer sub-command is listed only in a checkout."""
    command = COMMANDS[f"films {action}"]
    listed = developer or command.group == OWNERS
    return actions.add_parser(  # type: ignore[no-any-return]
        action,
        prog=f"{name} films {action}",
        description=_text(command),
        epilog=_epilog(command, name),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        **({"help": command.summary} if listed else {}),
    )


def _arguments(
    command: str, parser: argparse.ArgumentParser, name: str, developer: bool
) -> None:
    """Add the arguments of one command."""
    if command == "cards":
        _add_json(parser)
    elif command == "install":
        parser.add_argument(
            "--card", metavar="DIR", required=True, help="the top folder of the SD card"
        )
        _add_films(parser, name, required=False)
        parser.add_argument(
            "--build",
            metavar="BUILD",
            help="the name of another build; default: the pinned build",
        )
        parser.add_argument(
            "--allow-untested",
            action="store_true",
            help="allow a build that has no passed camera test",
        )
        _add_stock(parser)
        _add_dry_run(parser)
        _add_eject(parser)
        _add_json(parser)
    elif command == "films":
        _add_json(parser)
        actions = parser.add_subparsers(dest="action", metavar="[ACTION]")
        sub = _add_action(actions, "set", name, developer)
        _add_destination(sub)
        _add_films(sub, name, required=True)
        _add_dry_run(sub)
        _add_eject(sub)
        _add_json(sub)
        sub = _add_action(actions, "pack", name, developer)
        sub.add_argument("list", metavar="LIST", help="a look list (JSON) of fit files")
        _add_destination(sub)
        _add_dry_run(sub)
        _add_eject(sub)
        _add_json(sub)
    elif command == "restore":
        _add_destination(parser)
        _add_stock(parser)
        _add_dry_run(parser)
        _add_eject(parser)
        _add_json(parser)
    elif command == "inspect":
        parser.add_argument(
            "file", nargs="?", metavar="FILE", help="a firmware file or a look pack"
        )
        parser.add_argument(
            "--card", metavar="DIR", help="the top folder of the SD card"
        )
        _add_json(parser)
    elif command == "serve":
        parser.add_argument(
            "--port",
            type=int,
            default=0,
            help="the port on 127.0.0.1; default: a free one",
        )
        parser.add_argument(
            "--no-browser",
            action="store_true",
            help="print the page's address in place of opening the browser",
        )
    elif command == "make":
        parser.add_argument("build", metavar="BUILD", help="the name of a build")
        parser.add_argument(
            "-o",
            "--out",
            metavar="FILE",
            help="also write the firmware to FILE; not on an SD card",
        )
        parser.add_argument(
            "--out-dir",
            metavar="DIR",
            help="the output folder; default: the project's output folder",
        )
        _add_stock(parser)
        _add_dry_run(parser)
        _add_json(parser)
    elif command == "builds":
        _add_json(parser)
    elif command == "init":
        parser.add_argument(
            "--check",
            action="store_true",
            help="change nothing; say what is present and what is missing, and exit 1 if an item is missing",
        )
    elif command == "lint":
        parser.add_argument("build", metavar="BUILD", help="the name of a build")
    elif command == "pin":
        parser.add_argument(
            "build", metavar="BUILD", help="the name of the tested build"
        )
        parser.add_argument(
            "--date",
            required=True,
            metavar="YYYY-MM-DD",
            help="the day of the camera test",
        )
        parser.add_argument(
            "--sha256",
            required=True,
            metavar="HEX",
            help="the sha256 of the flashed file, from the camera log",
        )
        parser.add_argument(
            "--no-pin",
            action="store_true",
            help="record the camera test; leave the pinned build as it is",
        )
        _add_dry_run(parser)
    elif command == "apply":
        parser.add_argument(
            "specs", nargs="+", metavar="SPEC", help="patch spec files, in order"
        )
        parser.add_argument(
            "-o",
            "--out",
            required=True,
            metavar="FILE",
            help="the firmware file to write; not on an SD card",
        )
        parser.add_argument(
            "--from",
            dest="source",
            required=True,
            metavar="FILE",
            help="the firmware to start from",
        )
        parser.add_argument(
            "-v", "--verbose", action="store_true", help="print each change"
        )
        _add_stock(parser)
        _add_dry_run(parser)
    elif command == "fetch-stock":
        _add_stock(parser)
        _add_dry_run(parser)
        _add_json(parser)
    elif command == "generate":
        parser.add_argument(
            "--check",
            action="store_true",
            help="write nothing; list the files that differ from the generated ones, and exit 1 if any does",
        )
    elif command == "log":
        parser.add_argument(
            "file", metavar="FILE", help="the log file from the SD card"
        )
        parser.add_argument(
            "--dict",
            metavar="FILE",
            help="the event dictionary; default: the current one, and those of older builds",
        )
        _add_json(parser)
    elif command == "package":
        parser.add_argument(
            "--out-dir",
            metavar="DIR",
            help="the folder for the zip; default: the output folder",
        )
        parser.add_argument(
            "--release-version",
            required=True,
            metavar="V",
            help="the calendar version, like 2026.11.18 or 2026.11.18-rc.1; "
            "2026.11.18-NAME.1 holds the build NAME in place of the pinned one",
        )
        _add_dry_run(parser)
        _add_json(parser)
    elif command == "release":
        parser.add_argument(
            "--final",
            action="store_true",
            help="a release for everyone (vYYYY.MM.DD); default: a test release (-rc.N)",
        )
        parser.add_argument(
            "--build",
            metavar="NAME",
            help="a test release of this camera-tested build in place of the pinned one (-NAME.N)",
        )
        parser.add_argument(
            "--day",
            metavar="YYYY.MM.DD",
            help="the day of the release, which is in the version and on the Firmware screen; "
            "default: today in UTC. Give the day of the dry run to make the release that it showed",
        )
        _add_json(parser)


def build_parser(name: str, developer: bool) -> argparse.ArgumentParser:
    """Return the argument parser of the ``epm2mod`` command.

    Args:
        name: the program's name in usage lines and examples (``prog``).
        developer: True to list the commands for developers and releases in ``--help`` (in a checkout).
    """
    parser = _Parser(
        prog=name,
        usage=f"{name} [--version] [--project DIR] COMMAND [ARGS]",
        description="Make EPM2Mod, firmware for the Olympus PEN E-PM2, and put it on an SD card. "
        f"'{name} COMMAND --help' describes a command.",
        epilog=_top_help(name, developer),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--project",
        metavar="DIR",
        help=f"the project folder, which holds {MANIFEST}; default: the nearest folder at or above "
        "the current folder that holds one",
    )
    commands = parser.add_subparsers(
        dest="command",
        required=True,
        metavar="COMMAND",
        help="one of the commands below",
    )
    for command_name, handler in HANDLERS.items():
        command = COMMANDS[command_name]
        sub = commands.add_parser(
            command_name,
            prog=f"{name} {command_name}",
            description=_text(command),
            epilog=_epilog(command, name),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        sub.set_defaults(run=handler, command_name=command_name)
        _arguments(command_name, sub, name, developer)
    return parser


@contextlib.contextmanager
def interruptible() -> Iterator[None]:
    """Turn termination signals into one ``KeyboardInterrupt`` for a block.

    Closing the terminal or stopping the process politely then runs the same
    clean-up as Ctrl-C. After the first signal (Ctrl-C included) further ones
    are ignored until the block ends, so the clean-up itself is not
    interrupted. The handlers that were there before are put back. Outside the
    main thread, where handlers cannot be set, nothing is changed.
    """

    def interrupt(number: int, frame: object) -> None:
        """Ignore further signals and raise the interrupt in the main thread."""
        for other in before:
            signal.signal(other, signal.SIG_IGN)
        raise KeyboardInterrupt

    names = ("SIGINT", "SIGTERM", "SIGHUP", "SIGBREAK")
    signals = [getattr(signal, name) for name in names if hasattr(signal, name)]
    before: dict[int, Any] = {}
    try:
        for number in signals:
            before[number] = signal.signal(number, interrupt)
    except ValueError:
        pass
    try:
        yield
    finally:
        for number, handler in before.items():
            signal.signal(number, handler)


def _project_of(argv: Sequence[str]) -> str | None:
    """Return the folder that ``--project`` names before the command, or None."""
    for index, word in enumerate(argv):
        if word == "--project":
            return argv[index + 1] if index + 1 < len(argv) else None
        if word.startswith("--project="):
            return word.partition("=")[2]
        if not word.startswith("-"):
            return None
    return None


def _command_of(argv: Sequence[str]) -> str | None:
    """Return the command that the arguments name (``films set`` for a sub-command), or None."""
    words = [
        word
        for index, word in enumerate(argv)
        if not word.startswith("-") and (index == 0 or argv[index - 1] != "--project")
    ]
    if not words or words[0] not in HANDLERS:
        return None
    if words[0] == "films" and len(words) > 1 and f"films {words[1]}" in COMMANDS:
        return f"films {words[1]}"
    return words[0]


def main(argv: Sequence[str] | None = None, context: Context | None = None) -> int:
    """Run the ``epm2mod`` command and return its exit status."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    for stream in (sys.stdout, sys.stderr):
        # A console that cannot show a character must not stop a run half-way.
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(errors="backslashreplace")
    if context is None:
        project = _project_of(arguments)
        context = Context(
            lambda: catalogue.locate(project=None if project is None else Path(project))
        )
    ctx = context
    name = prog()
    as_json = "--json" in arguments
    command = _command_of(arguments)

    def failed(code: str, status: int, message: str, override: str | None) -> int:
        """Report a failure on stderr and, with ``--json``, as a document; return its exit status."""
        print(f"{name}: {message}", file=sys.stderr)
        if as_json:
            _document(
                command, False, error=_error_json(code, status, message, override)
            )
        return status

    _Parser.json_errors = as_json
    try:
        try:
            args = build_parser(name, ctx.has_checkout()).parse_args(arguments)
        finally:
            _Parser.json_errors = False
        handler: Handler = args.run
        ctx.use(
            cache=getattr(args, "cache", None),
            stock=getattr(args, "stock", None),
            out_dir=args.out_dir if args.command == "make" else None,
        )
        with interruptible():
            return handler(args, ctx)
    except Epm2ModError as error:
        message = named(str(error), name)
        return failed(error.code, error.exit_status, message, error.override)
    except KeyboardInterrupt:
        return failed(
            "interrupted",
            INTERRUPTED,
            "interrupted; no file was left half-written",
            None,
        )
    except Exception as error:  # an internal error: the caller reports it
        traceback.print_exc()
        return failed("internal", INTERNAL, f"internal error: {error!r}", None)
