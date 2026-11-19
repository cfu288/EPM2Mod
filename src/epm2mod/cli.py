"""The ``epm2mod`` command: it parses the arguments, calls the package's functions and formats their results.

The commands are in ``COMMANDS``, grouped by who uses them; ``epm2mod --help`` shows the groups, and
``readme.cli_reference`` writes the CLI reference page from the same definitions. The rules that every command
follows:

1. Destinations: ``--card DIR`` is the top folder of an SD card; ``-o PATH`` is a file, or an existing folder (or a
   path that ends in a slash) that gets the usual file name.
2. Results go to stdout; progress, hints and the camera steps go to stderr.
3. ``--json`` prints one document on stdout, with ``schema`` (``SCHEMA``).
4. Exit statuses: 0 done, 1 failed, 2 wrong usage, 3 nothing found or not recognised, 4 a check failed, 5 the
   environment (``errors``); 130 if the run was interrupted.
5. ``--dry-run`` on every command that writes: what would be written; nothing is written.
6. No prompts.

This module holds no knowledge of where the data is: it asks the locator (``catalogue.locate``) for everything.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import signal
import sys
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import __version__, camera_steps, catalogue, readme
from .builds import BuildDescription, pinned_path
from .cardio import Planned, output_path
from .catalogue import Locator
from .container import describe, parse
from .errors import (
    BuildCheckError,
    BuildError,
    Epm2ModError,
    NotFoundError,
    UsageError,
)
from .eventlog import Dictionary, decode, load_dictionary, name_films
from .fileio import read_bytes, read_json, write_bytes
from .hashing import sha256_bytes
from .logsummary import summarize
from .paths import RepoPaths
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
from .stock import EPM2_V16, fetch, read_stock, stock_path

#: The version of the ``--json`` documents. A change that breaks a reader raises it.
SCHEMA = 1


class Context:
    """What a command gets besides its arguments: the locator, found when it is first needed."""

    def __init__(self, find: Callable[[], Locator] = catalogue.locate) -> None:
        """Keep the function that finds the locator."""
        self._find = find
        self._found: Locator | None = None

    @property
    def locator(self) -> Locator:
        """The locator of the data (``catalogue.locate``).

        Raises:
            RepositoryError: if there is no source of the data.
        """
        if self._found is None:
            self._found = self._find()
        return self._found

    def checkout(self) -> RepoPaths:
        """Return the checkout, for a developer or release command.

        Raises:
            RepositoryError: outside a checkout (exit status 5).
        """
        return self.locator.checkout()


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
        examples: one or two command lines.
        json: the keys of its ``--json`` document (beside ``schema`` and ``command``), or {} for no ``--json``.
        exits: what each exit status other than 0, 1 and 2 means for it.
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
#: The exit statuses of every command.
EXIT_STATUSES = {
    0: "done",
    1: "failed",
    2: "wrong usage",
    3: "nothing found, or a file that is not recognised",
    4: "a check failed: a checksum, a read-back, the camera model, an untested build",
    5: "the environment: no network, no checkout, a card that is not writable or full",
    130: "interrupted; no file was left half-written",
}
_DOWNLOAD = "when Olympus's firmware is not downloaded yet"
_FILES = "each file written (path, role, size, sha256, replaced)"
_STEPS = "the steps on the camera (id, text)"

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
            {"cards": "the cards (path, name, size, free, label)"},
            {3: "no SD card found"},
        ),
        Command(
            "install",
            OWNERS,
            "Make the firmware and write it and the film file to the SD card.",
            "the firmware and the film file on the card; then the camera steps",
            False,
            _DOWNLOAD,
            (
                "epm2mod install --card /path/to/card",
                "epm2mod install --card /path/to/card ART1=portra-400 ART2=velvia",
            ),
            {
                "dry_run": "true if nothing was written",
                "card": "the card",
                "build": "the build (name, what, sha256, tested, label)",
                "files": _FILES,
                "removed": "the extra files removed from DCOLYMP",
                "films": "the films of the film file (art, name)",
                "ejected": "true if the card was ejected",
                "camera_steps": _STEPS,
            },
            {
                4: "a check failed (an untested build without --untested, a read-back, the model)",
                5: "no network, or the card is not a camera card, not writable or full",
            },
        ),
        Command(
            "films",
            OWNERS,
            "List the film simulations.",
            "a line per film: menu name, command-line name, film, type",
            False,
            "",
            ("epm2mod films",),
            {"films": "the films (id, name, film, kind, medium, note, default_art)"},
        ),
        Command(
            "films set",
            OWNERS,
            "Write only the film file.",
            "the film file on the card or at PATH; then the camera steps",
            False,
            "",
            (
                "epm2mod films set --card /path/to/card ART2=velvia ART6=double-x",
                "epm2mod films set -o EPM2LOOK.BIN",
            ),
            {
                "dry_run": "true if nothing was written",
                "card": "the card, or null",
                "files": _FILES,
                "films": "the films of the film file (art, name)",
                "ejected": "true if the card was ejected",
                "camera_steps": _STEPS,
            },
            {5: "the card is not a camera card, not writable or full"},
        ),
        Command(
            "restore",
            OWNERS,
            "Write Olympus's original firmware, to remove EPM2Mod.",
            "the original firmware on the card or at PATH; then the camera steps",
            False,
            _DOWNLOAD,
            ("epm2mod restore --card /path/to/card", "epm2mod restore -o ./"),
            {
                "dry_run": "true if nothing was written",
                "card": "the card, or null",
                "files": _FILES,
                "removed": "the extra files removed from DCOLYMP",
                "ejected": "true if the card was ejected",
                "camera_steps": _STEPS,
            },
            {
                4: "a check failed (the download, a read-back)",
                5: "no network, or a card problem",
            },
        ),
        Command(
            "inspect",
            OWNERS,
            "Say what a firmware file, a film file or an SD card holds.",
            "a report per file (model, build, version, sha256, films) and what will not work",
            False,
            "",
            ("epm2mod inspect --card /path/to/card", "epm2mod inspect E1019999.BIN"),
            {
                "card": "the card, or null",
                "files": "a report per file (path, kind, size, sha256, model, build, version, checksums_ok, films, "
                "problem)",
                "problems": "what will not work, in words",
            },
            {
                3: "no such file, a file it does not know, or a card with neither file",
                4: "something will not work (see problems)",
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
            "NAME.BIN and card/ (DCOLYMP and the film file) in the output folder",
            True,
            _DOWNLOAD,
            ("epm2mod make", "epm2mod make debug-log -o ./"),
            {
                "dry_run": "true if nothing was written",
                "build": "the build (name, what, sha256, tested, label)",
                "sha256": "the firmware's sha256 (null for a dry run of a candidate)",
                "files": _FILES,
            },
            {4: "the result is not the recorded build"},
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
                "builds": "the builds (name, what, sha256, tested, label, specs)",
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
            {4: "the build does not give that sha256"},
        ),
        Command(
            "apply",
            DEVELOPERS,
            "Apply patch specs without a build description.",
            "the firmware file at PATH",
            True,
            "",
            ("epm2mod apply SPEC -o test.BIN",),
            {},
            {
                3: "Olympus's firmware is not downloaded (and no --from)",
                4: "the result is not the sha256 the spec states",
            },
        ),
        Command(
            "fetch-stock",
            DEVELOPERS,
            "Download Olympus's firmware and check it.",
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
            {4: "the download is not the right file", 5: "no network"},
        ),
        Command(
            "looks",
            DEVELOPERS,
            "Compare (default) or write the film patch specs that the fit files make.",
            "which specs differ; with --write, the specs",
            True,
            "",
            ("epm2mod looks", "epm2mod looks --write"),
            {},
            {1: "a spec differs from the one the fit files make"},
        ),
        Command(
            "log",
            DEVELOPERS,
            "Decode a camera log file (EPM2LOG.BIN).",
            "a JSON line per event, or a short report with --summary",
            True,
            "",
            ("epm2mod log EPM2LOG.BIN --summary",),
        ),
        Command(
            "docs",
            DEVELOPERS,
            "Compare (default) or write the generated parts of the documents and the CLI reference.",
            "which documents differ; with --write, the documents",
            True,
            "",
            ("epm2mod docs", "epm2mod docs --write"),
            {},
            {1: "a document is not up to date"},
        ),
        Command(
            "package",
            RELEASES,
            "Write the release zip.",
            "EPM2Mod-VERSION.zip in the output folder",
            True,
            "",
            ("epm2mod package --version 2026.11.19-dev",),
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
            "Check and tag the next release; without --yes, only check.",
            "the release notes; with --yes, a tag",
            True,
            "the network for the checks of CI and with --push",
            ("epm2mod release", "epm2mod release --final --yes --push"),
            {},
            {1: "the repository is not ready for a release"},
        ),
    )
}


def _progress(line: str) -> None:
    """Print a progress line on stderr."""
    print(line, file=sys.stderr, flush=True)


def _hint(text: str) -> None:
    """Print a hint on stderr."""
    print(text, file=sys.stderr)


def _print_steps(steps: Sequence[camera_steps.Step]) -> None:
    """Print the camera steps on stderr, numbered."""
    if steps:
        _hint("On the camera:")
        for number, item in enumerate(steps, 1):
            _hint(f"  {number}. {item.text}")


def _document(args: argparse.Namespace, **values: Any) -> None:
    """Print the ``--json`` document of a command on stdout."""
    document = {"schema": SCHEMA, "command": args.command_name, **values}
    print(json.dumps(document, indent=1))


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
        verb = (
            ("would replace" if planned.replaces else "would write")
            if dry_run
            else ("replaced" if planned.replaces else "wrote")
        )
        sha = planned.content.sha256 or "not known before it is made"
        lines.append(f"{verb} {planned.path} ({planned.role}, sha256 {sha})")
    return lines


def _choices(items: Sequence[str]) -> list[str] | None:
    """Return the film choices of the command line; None for none (the 12 default films)."""
    return list(items) or None


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
            "camera_steps": [item.to_json() for item in outcome.steps],
        }
        keys = COMMANDS[args.command_name].json
        _document(args, **{key: value for key, value in values.items() if key in keys})
    else:
        verb = "would remove" if outcome.dry_run else "removed"
        lines = [f"{verb} {path}" for path in outcome.removed]
        lines += _file_lines(outcome.files, outcome.dry_run)
        lines += [f"  ART{look.slot + 1:<2} {look.name}" for look in outcome.looks]
        print("\n".join(lines))
    if outcome.ejected:
        _hint(f"ejected {outcome.card}")
    if not outcome.dry_run:
        _print_steps(outcome.steps)
    return 0


def _cards(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod cards``: the SD cards plugged into this computer."""
    from .cards import cards, describe

    found = cards()
    if args.json:
        _document(
            args,
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
        return 3
    return 0


def _install(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod install``."""
    outcome = install(
        ctx.locator,
        _card(args.card),
        _choices(args.choices),
        build=args.build,
        untested=args.untested,
        dry_run=args.dry_run,
        eject=args.eject,
        log=_progress,
        stock=EPM2_V16,
    )
    return _report_outcome(args, outcome)


def _films(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod films`` (the list) or ``epm2mod films set``."""
    if args.action == "set":
        return _films_set(args, ctx)
    films = catalogue.films(ctx.locator)
    default = {slot.built_in: slot.art for slot in films.slots}
    if args.json:
        _document(
            args,
            films=[
                {
                    "id": film.id,
                    "name": film.name,
                    "film": film.film,
                    "kind": film.kind,
                    "medium": film.medium,
                    "note": film.note,
                    "default_art": default.get(film.id),
                }
                for film in films.films.values()
            ],
        )
        return 0
    print(f"{'Menu name':<17} {'Command-line name':<18} {'Film':<34} Type")
    for film in films.films.values():
        print(f"{film.name:<17} {film.id:<18} {film.film:<34} {film.kind}")
    return 0


def _films_set(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod films set``: write only the film file."""
    from .looks.lookfile import CARD_NAME

    args.command_name = "films set"
    out = None if args.out is None else output_path(args.out, CARD_NAME)
    outcome = set_films(
        ctx.locator,
        _choices(args.choices),
        card=_card(args.card),
        out=out,
        dry_run=args.dry_run,
        eject=args.eject,
    )
    return _report_outcome(args, outcome)


def _restore(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod restore``: Olympus's original firmware to the card or a file."""
    out = None if args.out is None else output_path(args.out, EPM2_V16.card_name)
    outcome = restore(
        ctx.locator,
        card=_card(args.card),
        out=out,
        dry_run=args.dry_run,
        eject=args.eject,
        log=_progress,
        stock=EPM2_V16,
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
        inspect_file(ctx.locator, Path(args.file), EPM2_V16)
        if args.file is not None
        else inspect_card(ctx.locator, Path(args.card), EPM2_V16)
    )
    if args.json:
        _document(
            args,
            card=None if found.card is None else str(found.card),
            files=[report.to_json() for report in found.files],
            problems=list(found.problems),
        )
    else:
        print(
            "\n".join(line for report in found.files for line in _report_lines(report))
        )
        for problem in found.problems:
            print(f"will not work: {problem}")
    return 4 if found.problems else 0


def _serve(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod serve``: the local app, until the process is stopped."""
    from .serve import serve

    serve(ctx.locator, port=args.port, browser=not args.no_browser)
    return 0


def _make(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod make``.

    What an earlier run left is removed before a description is read: first
    the card folder, then the image of the build. Its name comes from the
    argument, or from the pointer to the pinned build.
    """
    checkout = ctx.checkout()
    if not args.dry_run:
        clear_outputs(checkout, None)
        clear_outputs(checkout, args.build or pinned_path(checkout).stem)
    description = (
        checkout.pinned_build() if args.build is None else checkout.build(args.build)
    )
    output = None if args.out is None else output_path(args.out, EPM2_V16.card_name)
    result: MakeResult = make(
        checkout,
        description,
        log=_progress,
        stock=EPM2_V16,
        output=output,
        dry_run=args.dry_run,
    )
    if args.json:
        _document(
            args,
            dry_run=args.dry_run,
            build=_build_json(description),
            sha256=result.sha256,
            files=[planned.to_json() for planned in result.files],
        )
    else:
        print("\n".join(_file_lines(result.files, args.dry_run)))
    if not args.dry_run:
        _hint(
            "To write a card: epm2mod install --card DIR"
            + ("" if args.build is None else f" --build {description.name}")
            + ("" if description.tested else " --untested")
        )
    return 0


def _builds(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod builds``."""
    checkout = ctx.checkout()
    pinned = checkout.pinned_build().name
    found = checkout.all_builds()
    if args.json:
        _document(
            args,
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


def _pin(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod pin``."""
    checkout = ctx.checkout()
    record_test(
        checkout,
        checkout.build(args.build),
        args.sha256,
        args.date,
        log=print,
        stock=EPM2_V16,
        dry_run=args.dry_run,
    )
    return 0


def _apply(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod apply``."""
    checkout = ctx.checkout()
    specs = [load_spec(Path(spec)) for spec in args.specs]
    source = (
        read_stock(checkout, EPM2_V16)
        if args.source is None
        else read_bytes(Path(args.source), NotFoundError)
    )
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
    out = output_path(args.out, EPM2_V16.card_name)
    try:
        is_stock = out.resolve() == stock_path(checkout, EPM2_V16).resolve()
    except (OSError, RuntimeError) as error:
        raise BuildError(f"{out}: cannot be used as a path: {error}") from None
    if is_stock:
        raise BuildError(f"{out} is the stock firmware file; give another name")
    if args.dry_run:
        print(f"would write {out} (sha256 {digest})")
        return 0
    write_bytes(out, applied.image, read_back=True)
    print(f"wrote {out} ({applied.changed_bytes} bytes differ from stock)")
    print(f"sha256 {digest}")
    return 0


def _fetch_stock(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod fetch-stock``."""
    checkout = ctx.checkout()
    path = stock_path(checkout, EPM2_V16)
    there = path.exists()
    if args.dry_run:
        if there:
            read_stock(checkout, EPM2_V16)
    else:
        fetch(checkout, EPM2_V16, log=_progress)
    if args.json:
        _document(
            args,
            path=str(path),
            sha256=EPM2_V16.sha256,
            downloaded=not there and not args.dry_run,
            dry_run=args.dry_run,
        )
    else:
        verb = "would download to" if args.dry_run and not there else "kept at"
        print(f"{verb} {path}")
    return 0


def _numpy_needed(error: ModuleNotFoundError) -> BuildError:
    """Return the error to report when numpy is missing, or raise ``error``."""
    if error.name != "numpy":
        raise error
    return BuildError(
        "numpy is needed for the film looks. In a checkout, 'uv run epm2mod "
        "looks' installs it."
    )


def _looks(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod looks``: compare or write the film patch specs."""
    checkout = ctx.checkout()
    try:
        from .looks import generate
    except ModuleNotFoundError as error:
        raise _numpy_needed(error) from None
    if args.write:
        changed = generate.write(checkout, EPM2_V16)
        print("\n".join(f"wrote {path}" for path in changed) or "no spec changed")
        if changed:
            _hint(
                "If the operations of a spec changed, the spec is now marked 'NOT "
                "camera-tested' and a tested build that uses it no longer gives its "
                "recorded sha256. 'epm2mod make' tells you."
            )
        return 0
    stale = generate.stale(checkout, EPM2_V16)
    if stale:
        print("\n".join(f"{path}: differs from the generated spec" for path in stale))
        _hint("run 'epm2mod looks --write'")
        return 1
    print("the film-look specs are the generated ones")
    return 0


def _dictionaries(args: argparse.Namespace, checkout: RepoPaths) -> list[Dictionary]:
    """Return the dictionaries for ``epm2mod log``, the main one first.

    Without ``--dict`` these are the locator's event dictionaries: the current one and, for the logs of older
    builds, the older ones. The art codes of the film slots get the film labels of the film list, if it is there.
    """
    sources = [Path(args.dict)] if args.dict else checkout.event_dictionaries()
    words = load_dictionary(read_json(sources[0]))
    if checkout.films.is_file():
        words = name_films(words, read_json(checkout.films))
    found = [words]
    for other in sources[1:]:
        found.append(load_dictionary(read_json(other), inherit=words))
    return found


def _log(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod log``: print a camera log as JSON lines or as a summary."""
    words, *older = _dictionaries(args, ctx.checkout())
    others = {other.build_id: other for other in older}
    lines = decode(read_bytes(Path(args.file)), words, others)
    if args.summary:
        print("\n".join(summarize(lines)))
        return 0
    for line in lines:
        print(json.dumps(line))
    return 0


def _docs(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod docs``: compare or write the generated parts of the documents."""
    checkout = ctx.checkout()
    if args.write:
        changed = readme.rewrite(checkout)
        print("\n".join(f"wrote {path}" for path in changed) or "documents: no change")
        return 0
    problems = readme.feature_problems(checkout)
    for problem in problems:
        print(f"feature list: {problem}")
    stale = readme.stale(checkout)
    for path in stale:
        print(f"{path}: the generated parts are out of date")
    if stale:
        _hint("run 'epm2mod docs --write'")
    if stale or problems:
        return 1
    print("the generated parts of the documents are up to date")
    return 0


def _package(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod package``: write the release zip."""
    from .release import (
        check_version,
        make_release,
        release_files,
        today_version,
        zip_path,
    )

    checkout = ctx.checkout()
    version = args.version or today_version()
    check_version(version)
    label = checkout.pinned_build().label
    if (
        label is not None
        and not version.startswith(label)
        and not version.endswith("-dev")
    ):
        raise BuildError(
            f"the version {version} does not match the pinned build's label {label}: "
            "start the release with 'epm2mod release'"
        )
    folder = Path(args.out) if args.out else checkout.output_folder()
    contents = [name for name, _ in release_files(checkout, version)]
    if args.dry_run:
        out, digest = zip_path(folder, version), None
    else:
        out = make_release(checkout, folder, version)
        digest = sha256_bytes(out.read_bytes())
    if args.json:
        _document(
            args, dry_run=args.dry_run, zip=str(out), sha256=digest, contents=contents
        )
    elif args.dry_run:
        print(f"would write {out}: {len(contents)} files")
    else:
        print(f"wrote {out}: {out.stat().st_size} bytes, sha256 {digest}")
    return 0


def _release(args: argparse.Namespace, ctx: Context) -> int:
    """Run ``epm2mod release``: check the repository, then tag the next release."""
    from .releasing import plan, tag

    checkout = ctx.checkout()
    release, problems = plan(checkout, final=args.final)
    if release is None:
        for problem in problems:
            print(f"not ready: {problem}")
        return 1
    print(release.notes)
    if not args.yes:
        _hint(
            f"ready: {release.tag} on {release.commit[:7]}. Run again with --yes to tag it."
        )
        return 0
    tag(checkout, release, push=args.push)
    print(
        f"tagged {release.tag}"
        + (
            " and pushed it"
            if args.push
            else "; push it with: git push origin " + release.tag
        )
    )
    return 0


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
    "pin": _pin,
    "apply": _apply,
    "fetch-stock": _fetch_stock,
    "looks": _looks,
    "log": _log,
    "docs": _docs,
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
        lines.append(
            "--json: one document with schema, command, "
            + ", ".join(command.json)
            + "."
        )
    return "\n".join(lines)


def _epilog(command: Command) -> str:
    """Return the examples at the end of a command's ``--help``."""
    return "examples:\n" + "\n".join(f"  {line}" for line in command.examples)


def _top_help() -> str:
    """Return the list of commands of ``epm2mod --help``, by group."""
    blocks = []
    for group, note in GROUPS.items():
        lines = [f"{group} ({note}):"]
        for command in COMMANDS.values():
            if command.group == group:
                lines.append(f"  {command.name:<12} {command.summary}")
        blocks.append("\n".join(lines))
    blocks.append("examples:\n  epm2mod install --card /path/to/card\n  epm2mod films")
    return "\n\n".join(blocks)


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


def _add_choices(parser: argparse.ArgumentParser) -> None:
    """Add the film choices ``ARTn=FILM``."""
    parser.add_argument(
        "choices",
        nargs="*",
        metavar="ARTn=FILM",
        help="a film for an ART entry: ART1 (Pop Art) to ART12 (Watercolor), names from 'epm2mod films'. "
        "Only the named entries get a film; the others keep their Olympus art filter. None: the 12 default films",
    )


def _add_destination(parser: argparse.ArgumentParser, usual: str) -> None:
    """Add ``--card DIR`` and ``-o PATH``, one of which is needed."""
    where = parser.add_mutually_exclusive_group(required=True)
    where.add_argument("--card", metavar="DIR", help="the top folder of the SD card")
    where.add_argument(
        "-o",
        "--out",
        metavar="PATH",
        help=f"a file, or a folder (or a path that ends in /) for {usual}",
    )


def _arguments(name: str, parser: argparse.ArgumentParser) -> None:
    """Add the arguments of one command."""
    if name == "cards":
        _add_json(parser)
    elif name == "install":
        parser.add_argument(
            "--card", metavar="DIR", required=True, help="the top folder of the SD card"
        )
        _add_choices(parser)
        parser.add_argument(
            "--build",
            metavar="BUILD",
            help="the name of another build; default: the pinned build",
        )
        parser.add_argument(
            "--untested",
            action="store_true",
            help="accept a build that has no passed camera test",
        )
        _add_dry_run(parser)
        _add_eject(parser)
        _add_json(parser)
    elif name == "films":
        _add_json(parser)
        actions = parser.add_subparsers(dest="action", metavar="ACTION")
        command = COMMANDS["films set"]
        sub = actions.add_parser(
            "set",
            prog="epm2mod films set",
            help=command.summary,
            description=_text(command),
            epilog=_epilog(command),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        _add_destination(sub, "EPM2LOOK.BIN")
        _add_choices(sub)
        _add_dry_run(sub)
        _add_eject(sub)
        _add_json(sub)
    elif name == "restore":
        _add_destination(parser, "E1019999.BIN")
        _add_dry_run(parser)
        _add_eject(parser)
        _add_json(parser)
    elif name == "inspect":
        parser.add_argument(
            "file", nargs="?", metavar="FILE", help="a firmware file or a film file"
        )
        parser.add_argument(
            "--card", metavar="DIR", help="the top folder of the SD card"
        )
        _add_json(parser)
    elif name == "serve":
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
    elif name == "make":
        parser.add_argument(
            "build",
            nargs="?",
            metavar="BUILD",
            help="the name of a build; default: the pinned build",
        )
        parser.add_argument(
            "-o",
            "--out",
            metavar="PATH",
            help="also write the firmware to PATH (a folder: as E1019999.BIN)",
        )
        _add_dry_run(parser)
        _add_json(parser)
    elif name == "builds":
        _add_json(parser)
    elif name == "pin":
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
        _add_dry_run(parser)
    elif name == "apply":
        parser.add_argument(
            "specs", nargs="+", metavar="SPEC", help="patch spec files, in order"
        )
        parser.add_argument(
            "-o",
            "--out",
            required=True,
            metavar="PATH",
            help="the firmware file to write",
        )
        parser.add_argument(
            "--from",
            dest="source",
            metavar="FILE",
            help="the firmware to start from; default: Olympus's firmware",
        )
        parser.add_argument(
            "-v", "--verbose", action="store_true", help="print each change"
        )
        _add_dry_run(parser)
    elif name == "fetch-stock":
        _add_dry_run(parser)
        _add_json(parser)
    elif name in ("looks", "docs"):
        parser.add_argument(
            "--write", action="store_true", help="write them; default: compare only"
        )
    elif name == "log":
        parser.add_argument(
            "file", metavar="FILE", help="the log file from the SD card"
        )
        parser.add_argument(
            "--dict",
            metavar="FILE",
            help="the event dictionary; default: the current one, and those of older builds",
        )
        parser.add_argument(
            "--summary",
            action="store_true",
            help="print a short report in place of the JSON lines",
        )
    elif name == "package":
        parser.add_argument(
            "-o",
            "--out",
            metavar="DIR",
            help="the folder for the zip; default: the output folder",
        )
        parser.add_argument(
            "--version",
            metavar="V",
            help="the calendar version, like 2026.11.18 or 2026.11.18-rc.1; default: today",
        )
        _add_dry_run(parser)
        _add_json(parser)
    elif name == "release":
        parser.add_argument(
            "--final",
            action="store_true",
            help="a release for everyone (vYYYY.MM.DD); default: a test release (-rc.N)",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="create the tag; without it, only check and show",
        )
        parser.add_argument(
            "--push",
            action="store_true",
            help="push the tag, which starts the publishing",
        )


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser of the ``epm2mod`` command."""
    parser = argparse.ArgumentParser(
        prog="epm2mod",
        usage="epm2mod [--version] COMMAND [ARGS]",
        description="Make EPM2Mod, firmware for the Olympus PEN E-PM2, and put it on an SD card. "
        "'epm2mod COMMAND --help' describes a command.",
        epilog=_top_help(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(
        dest="command",
        required=True,
        metavar="COMMAND",
        help="one of the commands below",
    )
    for name, handler in HANDLERS.items():
        command = COMMANDS[name]
        sub = commands.add_parser(
            name,
            prog=f"epm2mod {name}",
            description=_text(command),
            epilog=_epilog(command),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        sub.set_defaults(run=handler, command_name=name)
        _arguments(name, sub)
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


def main(argv: Sequence[str] | None = None, context: Context | None = None) -> int:
    """Run the ``epm2mod`` command and return its exit status."""
    args = build_parser().parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        # A console that cannot show a character must not stop a run half-way.
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(errors="backslashreplace")
    handler: Handler = args.run
    try:
        with interruptible():
            return handler(args, context or Context())
    except Epm2ModError as error:
        print(f"epm2mod: {error}", file=sys.stderr)
        return error.exit_status
    except KeyboardInterrupt:
        print("epm2mod: interrupted; no file was left half-written", file=sys.stderr)
        return 130
