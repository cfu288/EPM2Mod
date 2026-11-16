"""The ``epm2mod`` command.

::

    epm2mod make [BUILD.json] [--out DIR]         make a firmware build
    epm2mod pin BUILD.json --date D --sha256 H    record a passed camera test; pin the build
    epm2mod fetch-stock                           download and check the stock firmware
    epm2mod builds                                list the build descriptions
    epm2mod apply SPEC... -o OUT.BIN              apply patch specs (no build description)
    epm2mod info FIRMWARE.BIN                     describe a firmware file
    epm2mod readme [--check]                      refresh the generated parts of the documents
    epm2mod looks [--check | --write]             check or write the film-look patch specs
    epm2mod log FILE [--dict EVENTS.json] [--summary]
                                                  decode a camera log file to JSON lines

Exit status: 0 for success, 1 for an error that is reported as one message (or,
for ``info``, ``readme --check`` and ``looks``, a check that failed), 2 for a
wrong command line, 130 if the run was interrupted.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import signal
import sys
from pathlib import Path
from typing import Any
from collections.abc import Callable, Iterator, Sequence

from . import __version__, readme
from .builds import (
    BuildDescription,
    all_descriptions,
    load_description,
    pinned_description,
    pinned_path,
)
from .container import describe, parse
from .errors import BuildError, ContainerError, Epm2ModError
from .eventlog import Dictionary, decode, load_dictionary, name_films
from .fileio import read_bytes, read_json, write_bytes
from .hashing import sha256_bytes
from .logsummary import summarize
from .paths import RepoPaths, repo_paths
from .pipeline import clear_outputs, make, record_test
from .spec import apply_specs, load_spec
from .stock import EPM2_V16, fetch, read_stock, stock_path

Handler = Callable[[argparse.Namespace, RepoPaths], int]


def _description(paths: RepoPaths, argument: str) -> BuildDescription:
    """Return the build description that a command-line argument names.

    The argument is a path to a file in the repository's ``builds/`` folder,
    relative to the current folder or absolute. Symbolic links are followed
    before the comparison, so the file itself must be in that folder.
    """
    try:
        path = Path(argument).resolve()
    except (OSError, RuntimeError) as error:
        raise BuildError(f"{argument}: cannot be used as a path: {error}") from None
    if not argument or path.parent != paths.builds.resolve():
        raise BuildError(
            f"{argument}: a build description must be a file in "
            f"{paths.relative(paths.builds)}/"
        )
    return load_description(path)


def _make(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod make``.

    What an earlier run left is removed before a description is read: first
    the card folder, then the image of the build. Its name comes from the
    argument, or from the pointer to the pinned build.
    """
    clear_outputs(paths, None)
    named = Path(args.build) if args.build is not None else pinned_path(paths)
    clear_outputs(paths, named.stem)
    if args.card == "":
        raise BuildError("--out needs a folder")
    description = (
        pinned_description(paths)
        if args.build is None
        else _description(paths, args.build)
    )
    card = None if args.card is None else Path(args.card)
    make(paths, description, card=card, log=print, stock=EPM2_V16)
    return 0


def _pin(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod pin``."""
    description = _description(paths, args.build)
    record_test(paths, description, args.sha256, args.date, log=print, stock=EPM2_V16)
    return 0


def _fetch_stock(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod fetch-stock``."""
    fetch(paths, EPM2_V16, log=print)
    return 0


def _builds(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod builds``."""
    pinned = pinned_description(paths).name
    for build in all_descriptions(paths):
        state = f"tested {build.camera_tested}" if build.tested else "candidate"
        mark = " (pinned)" if build.name == pinned else ""
        print(f"{build.name}{mark}: {build.what} [{state}, {len(build.specs)} specs]")
    return 0


def _apply(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod apply``."""
    specs = [load_spec(Path(spec)) for spec in args.specs]
    applied = apply_specs(read_stock(paths, EPM2_V16), specs)
    if args.verbose:
        print("\n".join(applied.log))
    digest = sha256_bytes(applied.image)
    expected = specs[0].expected_sha256 if len(specs) == 1 else None
    if expected is not None and expected != digest:
        raise BuildError(
            f"{specs[0].name}: the result has sha256 {digest}, "
            f"the spec expects {expected}; nothing was written"
        )
    out = Path(args.out)
    try:
        is_stock = out.resolve() == stock_path(paths, EPM2_V16).resolve()
    except (OSError, RuntimeError) as error:
        raise BuildError(f"{out}: cannot be used as a path: {error}") from None
    if is_stock:
        raise BuildError(f"{out} is the stock firmware file; give another name")
    write_bytes(out, applied.image, read_back=True)
    print(f"wrote {out} ({applied.changed_bytes} bytes differ from stock)")
    print(f"sha256 {digest}")
    return 0


def _info(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod info``."""
    data = read_bytes(Path(args.firmware))
    try:
        container = parse(data)
    except ContainerError as error:
        raise ContainerError(f"{args.firmware}: {error}") from None
    print(f"{args.firmware}  size={len(data)}  sha256={sha256_bytes(data)}")
    print("\n".join("  " + line for line in describe(container)))
    return 0 if container.checksums_ok else 1


def _readme(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod readme``."""
    if args.check:
        if readme.is_current(paths):
            print("the generated parts of the documents are up to date")
            return 0
        print("the generated parts are out of date; run 'epm2mod readme'")
        return 1
    print("documents: updated" if readme.rewrite(paths) else "documents: no change")
    return 0


def _looks(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod looks``."""
    try:
        from .looks import generate
    except ModuleNotFoundError as error:
        if error.name != "numpy":
            raise
        raise BuildError(
            "numpy is needed for the film specs. In a checkout, 'uv run epm2mod "
            "looks' installs it."
        ) from None
    if args.write:
        changed = generate.write(paths, EPM2_V16)
        print("\n".join(f"wrote {path}" for path in changed) or "no spec changed")
        if changed:
            print(
                "If the operations of a spec changed, the spec is now marked 'NOT "
                "camera-tested' and a tested build that uses it no longer gives its "
                "recorded sha256. 'epm2mod make' tells you."
            )
        return 0
    stale = generate.stale(paths, EPM2_V16)
    if stale:
        print("\n".join(f"{path}: differs from the generated spec" for path in stale))
        print("run 'epm2mod looks --write'")
        return 1
    print("the film-look specs are the generated ones")
    return 0


def _dictionaries(args: argparse.Namespace, paths: RepoPaths) -> list[Dictionary]:
    """Return the dictionaries for ``epm2mod log``, the main one first.

    Without ``--dict`` these are ``logs/events.json`` and, for the logs of
    older builds, every ``logs/events-*.json``. The art codes of the film
    slots get the film labels of ``looks/films.json``, if that file is there.
    """
    folder = paths.root / "logs"
    source = Path(args.dict) if args.dict else folder / "events.json"
    words = load_dictionary(read_json(source))
    if paths.films.is_file():
        words = name_films(words, read_json(paths.films))
    found = [words]
    if not args.dict:
        for other in sorted(folder.glob("events-*.json")):
            found.append(load_dictionary(read_json(other), inherit=words))
    return found


def _log(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod log``: print a camera log as JSON lines or as a summary."""
    words, *older = _dictionaries(args, paths)
    others = {other.build_id: other for other in older}
    lines = decode(read_bytes(Path(args.file)), words, others)
    if args.summary:
        print("\n".join(summarize(lines)))
        return 0
    for line in lines:
        print(json.dumps(line))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser of the ``epm2mod`` command."""
    parser = argparse.ArgumentParser(
        prog="epm2mod",
        description="Build and check custom firmware for the Olympus PEN E-PM2.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    def command(name: str, handler: Handler, text: str) -> argparse.ArgumentParser:
        """Add a sub-command with its handler and return its parser."""
        sub = commands.add_parser(name, help=text, description=text)
        sub.set_defaults(run=handler)
        return sub

    make_cmd = command("make", _make, "Make a firmware build: download, patch, check.")
    make_cmd.add_argument(
        "build",
        nargs="?",
        help="build description (builds/NAME.json); default: the pinned build",
    )
    make_cmd.add_argument(
        "-o",
        "--out",
        "--card",
        dest="card",
        metavar="DIR",
        help="also copy the firmware to DIR/DCOLYMP/E1019999.BIN: DIR is the top "
        "folder of the SD card, or any folder that exists (--card is the same)",
    )

    pin_cmd = command(
        "pin", _pin, "Record a passed camera test and make the build the pinned one."
    )
    pin_cmd.add_argument("build", help="the build description that was tested")
    pin_cmd.add_argument(
        "--date", required=True, metavar="YYYY-MM-DD", help="the date of the test"
    )
    pin_cmd.add_argument(
        "--sha256",
        required=True,
        metavar="HEX",
        help="sha256 of the firmware file that was flashed (from the camera log)",
    )

    command("fetch-stock", _fetch_stock, "Download and check the stock firmware.")
    command("builds", _builds, "List the build descriptions.")

    apply_cmd = command(
        "apply", _apply, "Apply patch specs to the stock firmware (for experiments)."
    )
    apply_cmd.add_argument(
        "specs", nargs="+", help="patch spec files, in the order to apply"
    )
    apply_cmd.add_argument(
        "-o", "--out", required=True, help="the firmware file to write"
    )
    apply_cmd.add_argument(
        "-v", "--verbose", action="store_true", help="print every operation"
    )

    info_cmd = command("info", _info, "Describe a firmware file.")
    info_cmd.add_argument("firmware", help="a firmware file")

    readme_cmd = command(
        "readme", _readme, "Refresh the generated parts of the documents."
    )
    readme_cmd.add_argument(
        "--check", action="store_true", help="only say if they are up to date"
    )

    looks_cmd = command(
        "looks", _looks, "Check or write the generated film-look patch specs."
    )
    looks_mode = looks_cmd.add_mutually_exclusive_group()
    looks_mode.add_argument(
        "--check", action="store_true", help="compare only; this is the default"
    )
    looks_mode.add_argument(
        "--write", action="store_true", help="write the generated specs to patches/"
    )

    log_cmd = command(
        "log", _log, "Decode a camera log file (EPM2LOG.BIN) to JSON lines."
    )
    log_cmd.add_argument("file", help="the log file from the SD card")
    log_cmd.add_argument(
        "--dict",
        metavar="EVENTS.json",
        help="the event dictionary; default: logs/events.json of the repository, "
        "and logs/events-BUILDID.json for a log of an older build",
    )
    log_cmd.add_argument(
        "--summary",
        action="store_true",
        help="print a short report in place of the JSON lines",
    )
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


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``epm2mod`` command and return its exit status."""
    args = build_parser().parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        # A console that cannot show a character must not stop a run half-way.
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(errors="backslashreplace")
    handler: Handler = args.run
    try:
        with interruptible():
            return handler(args, repo_paths())
    except Epm2ModError as error:
        print(f"epm2mod: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("epm2mod: interrupted; no file was left half-written", file=sys.stderr)
        return 130
