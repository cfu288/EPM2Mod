"""The ``epm2mod`` command.

::

    epm2mod make [BUILD.json] [--out FILE] [--card DIR]   make the firmware
    epm2mod pin BUILD.json --date D --sha256 H    record a passed camera test; pin the build
    epm2mod fetch-stock                           download Olympus's firmware and check it
    epm2mod builds                                list the build descriptions and the pinned one
    epm2mod cards                                 list the SD cards in this computer
    epm2mod restore [--card DIR] [-o FILE]        put Olympus's original firmware on the SD card
    epm2mod serve [--port N] [--no-browser]       open the installer page
    epm2mod release [-o DIR] [--version V]        write the release zip
    epm2mod apply SPEC... -o OUT.BIN              apply patch specs, without a build description
    epm2mod info FIRMWARE.BIN                     describe a firmware file
    epm2mod readme [--check]                      update the generated parts of the documents
    epm2mod looks [--check | --write]             check or write the film-look patch specs
    epm2mod looks list                            list the films for looks pack
    epm2mod looks pack [ART2=velvia ... | LIST.json] [-o FILE | --card DIR]
                                                  write the film choice for the SD card
    epm2mod looks show FILE [--json]              check a look file and list its films
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
        raise BuildError("--card needs the top folder of the SD card")
    if args.out == "":
        raise BuildError("--out needs a path")
    description = (
        pinned_description(paths)
        if args.build is None
        else _description(paths, args.build)
    )
    card = None if args.card is None else Path(args.card)
    output = None if args.out is None else Path(args.out)
    make(paths, description, card=card, log=print, stock=EPM2_V16, output=output)
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


def _numpy_needed(error: ModuleNotFoundError) -> BuildError:
    """Return the error to report when numpy is missing, or raise ``error``."""
    if error.name != "numpy":
        raise error
    return BuildError(
        "numpy is needed for the film looks. In a checkout, 'uv run epm2mod "
        "looks' installs it."
    )


def _looks_pack(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod looks pack``: write a look file from choices or a look list.

    Choices, and no argument (each slot's built-in film), pack the film records; a look list packs fit files and
    needs numpy.
    """
    from .looks import lookfile, records

    items = list(args.items)
    if all(records.is_choice(item) for item in items):
        choices = items or records.built_in_choices(records.load(paths))
        data, looks = records.pack_choices(paths, choices)
    elif len(items) == 1:
        try:
            from .looks import lookpack
        except ModuleNotFoundError as error:
            raise _numpy_needed(error) from None
        looks = lookpack.load_list(paths, Path(items[0]))
        data = lookfile.pack(looks)
    else:
        raise BuildError("give choices like ART2=velvia, or one look list")
    if args.card:
        out = records.write_to_card(Path(args.card), data)
    else:
        out = Path(args.out) if args.out else paths.output / lookfile.CARD_NAME
        if out.is_dir():
            out = out / lookfile.CARD_NAME
        write_bytes(out, data)
    print(f"wrote {out}: {len(data)} bytes, sha256 {sha256_bytes(data)}")
    for look in looks:
        print(f"  ART {look.slot + 1:2}  {look.name}")
    if not args.card:
        print(f"copy it to the top folder of the SD card as {lookfile.CARD_NAME}")
    print("on the camera: MENU -> Custom Menu -> J -> Load Looks -> Load")
    return 0


def _looks_list(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod looks list``: the films a look file can hold."""
    from .looks import records

    for film in records.load(paths).films.values():
        note = f"  ({film.note})" if film.note else ""
        print(f"{film.id:<14} {film.name:<13} {film.film}, {film.medium}{note}")
    return 0


def _looks_show(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod looks show``: check a look file and describe it."""
    from .looks import lookfile

    looks = lookfile.unpack(read_bytes(Path(args.file)))
    if args.json:
        print(json.dumps([lookfile.look_to_json(look) for look in looks], indent=1))
        return 0
    print(f"{args.file}: a valid look file with {len(looks)} looks")
    for look in looks:
        kind = "colour" if isinstance(look, lookfile.ColourLook) else "black-and-white"
        entry = lookfile.MENU_ENTRIES[look.slot]
        print(
            f"  ART {look.slot + 1:2}  {look.name:<17} {kind:<15} (stock entry {entry})"
        )
    return 0


def _looks(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod looks``."""
    if args.action == "pack":
        return _looks_pack(args, paths)
    if args.action == "list":
        return _looks_list(args, paths)
    if args.action == "show":
        return _looks_show(args, paths)
    try:
        from .looks import generate
    except ModuleNotFoundError as error:
        raise _numpy_needed(error) from None
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


def _restore(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod restore``: Olympus's original firmware to the card or a file."""
    from .pipeline import restore

    if args.card is None and args.out is None:
        raise BuildError("give --card DIR (the SD card) or -o FILE")
    data = restore(paths, None if args.card is None else Path(args.card), log=print)
    if args.out is not None:
        out = Path(args.out)
        if out.is_dir():
            out = out / "E1019999.BIN"
        write_bytes(out, data)
        print(f"wrote {out}: copy it to the card as DCOLYMP/E1019999.BIN")
    print("Then, with the camera off, hold OK and switch the camera on.")
    return 0


def _cards(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod cards``: the SD cards plugged into this computer."""
    from .cards import cards, describe

    found = cards()
    for card in found:
        print(describe(card))
    if not found:
        print("no SD card found: plug one in, or give its folder to --card")
    return 0


def _serve(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod serve``: the local app, until the process is stopped."""
    from .serve import serve

    serve(paths, port=args.port, browser=not args.no_browser)
    return 0


def _release(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod release``: write the release zip."""
    from .release import make_release, today_version

    out = make_release(
        paths,
        Path(args.out) if args.out else paths.output,
        args.version or today_version(),
    )
    print(
        f"wrote {out}: {out.stat().st_size} bytes, sha256 {sha256_bytes(out.read_bytes())}"
    )
    return 0


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
        description="Make EPM2Mod, firmware for the Olympus PEN E-PM2, and put it on an SD card.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    def command(name: str, handler: Handler, text: str) -> argparse.ArgumentParser:
        """Add a sub-command with its handler and return its parser."""
        sub = commands.add_parser(name, help=text, description=text)
        sub.set_defaults(run=handler)
        return sub

    make_cmd = command(
        "make",
        _make,
        "Make the firmware: download Olympus's firmware, add EPM2Mod, check the result.",
    )
    make_cmd.add_argument(
        "build",
        nargs="?",
        help="a build description, builds/NAME.json; default: the pinned build",
    )
    make_cmd.add_argument(
        "-o",
        "--out",
        metavar="FILE",
        help="also write the firmware to FILE (into a folder: as E1019999.BIN)",
    )
    make_cmd.add_argument(
        "--card",
        metavar="DIR",
        help="also write the firmware to the SD card at DIR, as DIR/DCOLYMP/E1019999.BIN",
    )

    pin_cmd = command(
        "pin",
        _pin,
        "Record a passed camera test and make the build the default of make.",
    )
    pin_cmd.add_argument("build", help="the tested build description")
    pin_cmd.add_argument(
        "--date", required=True, metavar="YYYY-MM-DD", help="the day of the camera test"
    )
    pin_cmd.add_argument(
        "--sha256",
        required=True,
        metavar="HEX",
        help="the sha256 of the flashed file, from the camera log",
    )

    command("fetch-stock", _fetch_stock, "Download Olympus's firmware and check it.")
    command("builds", _builds, "List the build descriptions and the pinned one.")
    command("cards", _cards, "List the SD cards in this computer.")
    restore_cmd = command(
        "restore",
        _restore,
        "Put Olympus's original firmware on the SD card, to remove EPM2Mod.",
    )
    restore_cmd.add_argument(
        "--card", metavar="DIR", help="write it to the SD card at DIR"
    )
    restore_cmd.add_argument("-o", "--out", metavar="FILE", help="write it to FILE")
    serve_cmd = command("serve", _serve, "Open the installer page in the browser.")
    serve_cmd.add_argument(
        "--port", type=int, default=0, help="the port on 127.0.0.1; default: a free one"
    )
    serve_cmd.add_argument(
        "--no-browser",
        action="store_true",
        help="print the page's address in place of opening the browser",
    )
    release_cmd = command(
        "release",
        _release,
        "Write the release zip: the installer, its launchers and the pinned build.",
    )
    release_cmd.add_argument(
        "-o", "--out", metavar="DIR", help="the folder for the zip; default: build/"
    )
    release_cmd.add_argument(
        "--version",
        metavar="V",
        help="the calendar version, like 2026.11.18 or 2026.11.18-rc.1; default: today",
    )

    apply_cmd = command(
        "apply",
        _apply,
        "Apply patch specs to Olympus's firmware, without a build description.",
    )
    apply_cmd.add_argument("specs", nargs="+", help="patch spec files, in order")
    apply_cmd.add_argument(
        "-o", "--out", required=True, help="the firmware file to write"
    )
    apply_cmd.add_argument(
        "-v", "--verbose", action="store_true", help="print each change"
    )

    info_cmd = command("info", _info, "Describe a firmware file.")
    info_cmd.add_argument("firmware", help="the firmware file")

    readme_cmd = command(
        "readme", _readme, "Update the generated parts of the documents."
    )
    readme_cmd.add_argument(
        "--check",
        action="store_true",
        help="report whether they are up to date and change nothing",
    )

    looks_cmd = command(
        "looks",
        _looks,
        "Check or write the film-look patch specs that the fit files generate.",
    )
    looks_mode = looks_cmd.add_mutually_exclusive_group()
    looks_mode.add_argument(
        "--check",
        action="store_true",
        help="compare the generated specs with patches/ (the default)",
    )
    looks_mode.add_argument(
        "--write", action="store_true", help="write the generated specs to patches/"
    )
    looks_actions = looks_cmd.add_subparsers(dest="action")
    looks_actions.add_parser(
        "list",
        help="list the films for looks pack",
        description="List the films for looks pack: the name to use, the name the camera shows, "
        "and the ART number that holds each film by default.",
    )
    pack_cmd = looks_actions.add_parser(
        "pack",
        help="write the film choice for the SD card",
        description="Write EPM2LOOK.BIN, which sets the film of each ART number. Give "
        "ART<n>=<film> for each ART number to change, with names from 'epm2mod looks "
        "list'. The other ART numbers keep their default film. With no choices: the 12 "
        "default films. The camera loads the file from Custom Menu J, Load Looks.",
    )
    pack_cmd.add_argument(
        "items",
        nargs="*",
        help="ART<n>=<film> choices, or one look list file; none: the 12 default films",
    )
    where = pack_cmd.add_mutually_exclusive_group()
    where.add_argument(
        "-o",
        "--out",
        metavar="FILE",
        help="write it to FILE (into a folder: as EPM2LOOK.BIN); default: "
        "build/EPM2LOOK.BIN",
    )
    where.add_argument(
        "--card",
        metavar="DIR",
        help="write it to the SD card at DIR",
    )
    show_cmd = looks_actions.add_parser(
        "show",
        help="check a look file and list its films",
        description="Check a look file as the camera does, and list its films.",
    )
    show_cmd.add_argument("file", help="the look file")
    show_cmd.add_argument("--json", action="store_true", help="print the looks as JSON")

    log_cmd = command(
        "log", _log, "Decode a camera log file (EPM2LOG.BIN) to JSON lines."
    )
    log_cmd.add_argument("file", help="the log file from the SD card")
    log_cmd.add_argument(
        "--dict",
        metavar="EVENTS.json",
        help="the event dictionary; default: logs/events.json, or "
        "logs/events-BUILDID.json for a log of an older build",
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
