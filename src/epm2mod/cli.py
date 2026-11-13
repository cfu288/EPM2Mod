"""The ``epm2mod`` command.

::

    epm2mod make [BUILD.json] [--card PATH] [--pin DATE]   make a firmware build
    epm2mod fetch-stock                                    download and check the stock firmware
    epm2mod builds                                         list the build descriptions
    epm2mod apply SPEC... -o OUT.BIN                       apply patch specs (no build description)
    epm2mod info FIRMWARE.BIN                              describe a firmware file
    epm2mod readme [--check]                               refresh the generated parts of README.md
    epm2mod looks [--check | --write]                      regenerate the film-look patch specs

Errors that the user can act on are printed as one message and give exit
status 1. Exit status 2 is a wrong command line.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from . import __version__
from .builds import all_descriptions, load_description, pinned_description
from .container import describe
from .errors import BuildError, Epm2ModError
from .hashing import sha256_bytes
from .paths import RepoPaths, repo_paths
from .pipeline import make
from .spec import apply_specs, load_spec
from .stock import EPM2_V16, fetch, stock_path


def _make(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod make``."""
    if args.pin and not args.build:
        raise BuildError("--pin needs the build description that was tested")
    description = (
        load_description(Path(args.build).resolve())
        if args.build
        else pinned_description(paths)
    )
    if args.build and Path(args.build).resolve().parent != paths.builds.resolve():
        raise BuildError(f"{args.build}: a build description must be a file in builds/")
    card = Path(args.card) if args.card else None
    make(paths, description, card=card, pin_date=args.pin, log=print)
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
    stock = stock_path(paths, EPM2_V16)
    if not stock.is_file():
        raise BuildError(
            f"{EPM2_V16.relative_path} is missing: run 'epm2mod fetch-stock'"
        )
    applied = apply_specs(stock.read_bytes(), specs)
    if args.verbose:
        print("\n".join(applied.log))
    digest = sha256_bytes(applied.image)
    if len(specs) == 1 and specs[0].expected_sha256 not in (None, digest):
        raise BuildError(
            f"{specs[0].name}: the result has sha256 {digest}, "
            f"the spec expects {specs[0].expected_sha256}; nothing was written"
        )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(applied.image)
    print(f"wrote {out} ({applied.changed_bytes} bytes differ from stock)")
    print(f"sha256 {digest}")
    return 0


def _info(args: argparse.Namespace, paths: Optional[RepoPaths]) -> int:
    """Run ``epm2mod info``."""
    data = Path(args.firmware).read_bytes()
    lines = describe(data)
    print(f"{args.firmware}  size={len(data)}  sha256={sha256_bytes(data)}")
    print("\n".join("  " + line for line in lines))
    return 0 if all("checksum=BAD" not in line for line in lines) else 1


def _readme(args: argparse.Namespace, paths: RepoPaths) -> int:
    """Run ``epm2mod readme``."""
    from . import readme

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
    from .looks import generate

    if args.write:
        changed = generate.write(paths)
        print("\n".join(f"wrote {path}" for path in changed) or "no spec changed")
        return 0
    stale = generate.stale(paths)
    if stale:
        print("\n".join(f"{path}: differs from the generated spec" for path in stale))
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

    make_cmd = commands.add_parser(
        "make", help="make a firmware build: download, patch, check"
    )
    make_cmd.add_argument(
        "build",
        nargs="?",
        help="build description (builds/NAME.json); default: the pinned build",
    )
    make_cmd.add_argument(
        "--card",
        metavar="PATH",
        help="mount point of the SD card; the firmware is copied to PATH/DCOLYMP/",
    )
    make_cmd.add_argument(
        "--pin",
        metavar="DATE",
        help="the build passed a camera test on DATE (YYYY-MM-DD): record it and pin the build",
    )
    make_cmd.set_defaults(run=_make)

    fetch_cmd = commands.add_parser(
        "fetch-stock", help="download and check the stock firmware"
    )
    fetch_cmd.set_defaults(run=_fetch_stock)

    builds_cmd = commands.add_parser("builds", help="list the build descriptions")
    builds_cmd.set_defaults(run=_builds)

    apply_cmd = commands.add_parser(
        "apply", help="apply patch specs to the stock firmware"
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
    apply_cmd.set_defaults(run=_apply)

    info_cmd = commands.add_parser("info", help="describe a firmware file")
    info_cmd.add_argument("firmware", help="a firmware file")
    info_cmd.set_defaults(run=_info)

    readme_cmd = commands.add_parser(
        "readme", help="refresh the generated parts of README.md"
    )
    readme_cmd.add_argument(
        "--check", action="store_true", help="only say if it is up to date"
    )
    readme_cmd.set_defaults(run=_readme)

    looks_cmd = commands.add_parser(
        "looks", help="regenerate the film-look patch specs"
    )
    group = looks_cmd.add_mutually_exclusive_group()
    group.add_argument(
        "--check", action="store_true", help="compare with patches/ (default)"
    )
    group.add_argument(
        "--write", action="store_true", help="write the specs to patches/"
    )
    looks_cmd.set_defaults(run=_looks)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the ``epm2mod`` command and return its exit status."""
    args = build_parser().parse_args(argv)
    try:
        paths = repo_paths()
        status: int = args.run(args, paths)
        return status
    except Epm2ModError as error:
        print(f"epm2mod: {error}", file=sys.stderr)
        return 1
    except FileNotFoundError as error:
        print(f"epm2mod: {error}", file=sys.stderr)
        return 1


def run(argv: Optional[List[str]] = None) -> None:
    """Entry point for ``python -m epm2mod``."""
    sys.exit(main(argv))
