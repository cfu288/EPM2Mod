"""The ``epm2mod`` command.

::

    epm2mod make [BUILD.json] [--card PATH]       make a firmware build
    epm2mod pin BUILD.json --date D --sha256 H    record a passed camera test; pin the build
    epm2mod fetch-stock                           download and check the stock firmware
    epm2mod builds                                list the build descriptions
    epm2mod apply SPEC... -o OUT.BIN              apply patch specs (no build description)
    epm2mod info FIRMWARE.BIN                     describe a firmware file
    epm2mod readme [--check]                      refresh the generated parts of README.md
    epm2mod looks [--write]                       check or write the film-look patch specs

Exit status: 0 for success, 1 for an error that is reported as one message (or,
for ``info``, ``readme --check`` and ``looks``, a check that failed), 2 for a
wrong command line.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, Sequence

from . import __version__, readme
from .builds import (
    BuildDescription,
    all_descriptions,
    load_description,
    pinned_description,
)
from .container import describe
from .errors import BuildError, Epm2ModError
from .fileio import read_bytes, write_bytes
from .hashing import sha256_bytes
from .paths import RepoPaths, repo_paths
from .pipeline import make, record_test
from .spec import apply_specs, load_spec
from .stock import EPM2_V16, fetch, read_stock

Handler = Callable[[argparse.Namespace, RepoPaths], int]


def _description(paths: RepoPaths, argument: str) -> BuildDescription:
    """Return the build description that a command-line argument names.

    The argument is a path to a file in the repository's ``builds/`` folder,
    relative to the current folder or absolute.
    """
    path = Path(argument).absolute()
    if path.parent != paths.builds.absolute():
        raise BuildError(
            f"{argument}: a build description must be a file in "
            f"{paths.relative(paths.builds)}/"
        )
    return load_description(path)


def _make(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod make``."""
    description = (
        _description(paths, args.build) if args.build else pinned_description(paths)
    )
    card = Path(args.card) if args.card else None
    make(paths, description, card=card, log=print)
    return 0


def _pin(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod pin``."""
    description = _description(paths, args.build)
    record_test(paths, description, args.sha256, args.date, log=print)
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
    write_bytes(out, applied.image)
    print(f"wrote {out} ({applied.changed_bytes} bytes differ from stock)")
    print(f"sha256 {digest}")
    return 0


def _info(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod info``."""
    data = read_bytes(Path(args.firmware))
    lines = describe(data)
    print(f"{args.firmware}  size={len(data)}  sha256={sha256_bytes(data)}")
    print("\n".join("  " + line for line in lines))
    return 1 if any("checksum=BAD" in line for line in lines) else 0


def _readme(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod readme``."""
    if args.check:
        if readme.is_current(paths):
            print("README.md: the generated parts are up to date")
            return 0
        print("README.md: the generated parts are out of date; run 'epm2mod readme'")
        return 1
    print("README.md: updated" if readme.rewrite(paths) else "README.md: no change")
    return 0


def _looks(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod looks``."""
    try:
        from .looks import generate
    except ImportError:
        raise BuildError(
            "numpy is needed for the film specs: uv run --extra looks epm2mod looks"
        ) from None
    if args.write:
        changed = generate.write(paths)
        print("\n".join(f"wrote {path}" for path in changed) or "no spec changed")
        return 0
    stale = generate.stale(paths)
    if stale:
        print("\n".join(f"{path}: differs from the generated spec" for path in stale))
        print("run 'epm2mod looks --write'")
        return 1
    print("the film-look specs are the generated ones")
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
        "--card",
        metavar="PATH",
        help="mount point of the SD card; the firmware is written to PATH/DCOLYMP/",
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

    readme_cmd = command("readme", _readme, "Refresh the generated parts of README.md.")
    readme_cmd.add_argument(
        "--check", action="store_true", help="only say if they are up to date"
    )

    looks_cmd = command(
        "looks", _looks, "Compare the film-look patch specs with the generated ones."
    )
    looks_cmd.add_argument(
        "--write", action="store_true", help="write the generated specs to patches/"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``epm2mod`` command and return its exit status."""
    args = build_parser().parse_args(argv)
    handler: Handler = args.run
    try:
        return handler(args, repo_paths())
    except Epm2ModError as error:
        print(f"epm2mod: {error}", file=sys.stderr)
        return 1
