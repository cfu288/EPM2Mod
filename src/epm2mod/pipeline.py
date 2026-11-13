"""The steps that make a firmware build.

``make`` is the one way firmware is made in this repository, for a user who
installs the pinned build and for a developer who tries a new one:

1. the stock firmware is found, or downloaded, and its SHA-256 is checked;
2. for a candidate (a build with no recorded SHA-256), the free-space check
   runs on the spec list;
3. the patch specs are applied;
4. the SHA-256 of the result is compared with the recorded one (tested build)
   or reported (candidate);
5. the firmware is written to ``build/NAME.BIN`` and, under the name the
   camera looks for, to ``build/card/DCOLYMP/``; optionally also to an SD card.

A wrong result is never left on disk under a name that looks usable.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, List, Optional

from .builds import BuildDescription, pin
from .errors import BuildError
from .hashing import sha256_bytes, sha256_file
from .paths import RepoPaths
from .spec import PatchSpec, apply_specs, load_spec
from .stock import CARD_FOLDER, EPM2_V16, StockFirmware, fetch, is_stock, stock_path

Log = Callable[[str], None]


@dataclass(frozen=True)
class MakeResult:
    """What ``make`` produced.

    Attributes:
        description: the build that was made; after ``pin_date`` it holds the test record.
        image: the firmware file, ``build/NAME.BIN``.
        card_copy: the copy under the camera's file name, in ``build/card``.
        on_card: the copy on the SD card, or None if no card was given.
        sha256: SHA-256 of the firmware file.
    """

    description: BuildDescription
    image: Path
    card_copy: Path
    on_card: Optional[Path]
    sha256: str


def load_specs(paths: RepoPaths, description: BuildDescription) -> List[PatchSpec]:
    """Read the patch specs of a build, in order.

    Raises:
        BuildError: if a spec path is absolute or has '..' in it.
        SpecError: if a spec is missing or not valid.
    """
    specs = []
    for relative in description.specs:
        parts = PurePosixPath(relative).parts
        if PurePosixPath(relative).is_absolute() or ".." in parts or "\\" in relative:
            raise BuildError(
                f"{description.name}: '{relative}' must be a path inside the "
                "repository, written with forward slashes and without '..'"
            )
        specs.append(load_spec(paths.resolve(relative)))
    return specs


def ensure_stock(paths: RepoPaths, stock: StockFirmware, log: Log) -> Path:
    """Return the path of the checked stock firmware; download it if it is absent."""
    path = stock_path(paths, stock)
    if not path.exists():
        log("the stock firmware is not here: downloading it")
        return fetch(paths, stock, log)
    if not is_stock(path, stock):
        return fetch(paths, stock, log)  # raises: another file is in the way
    return path


def check_free_space(paths: RepoPaths, description: BuildDescription) -> str:
    """Run the free-space check on a build's spec list.

    The check is ``tools/freespace.py check SPEC...``. It fails if two specs
    put bytes in the same place, or a spec puts bytes where the camera does
    not load the firmware.

    Returns:
        The last line of the check's output.

    Raises:
        BuildError: if the check fails or cannot run.
    """
    command = [sys.executable, str(paths.free_space_tool), "check", *description.specs]
    try:
        done = subprocess.run(
            command, cwd=paths.root, capture_output=True, text=True, check=False
        )
    except OSError as error:
        raise BuildError(f"the free-space check cannot run: {error}") from None
    output = (done.stdout + done.stderr).strip()
    if done.returncode != 0:
        hint = ""
        if not paths.firmware_map.exists():
            hint = (
                f"\nThe firmware map ({paths.relative(paths.firmware_map)}) is missing. "
                "A new build needs it: see tools/fwmap.py and tools/freespace.py."
            )
        raise BuildError(
            f"{output[-3000:]}\nthe free-space check failed: nothing was built{hint}"
        )
    return output.splitlines()[-1] if output else "ok"


def copy_to_card(image: Path, sha256: str, card: Path, stock: StockFirmware) -> Path:
    """Copy the firmware to an SD card and check the copy.

    The file goes to ``CARD/DCOLYMP/<camera's file name>``. The camera's updater
    needs it to be the only file in that folder, so other files there are an
    error; they are not deleted.

    Raises:
        BuildError: if ``card`` is not a folder, other files are in the way,
            the copy fails, or the copy differs from the firmware.
    """
    if not card.is_dir():
        raise BuildError(
            f"{card}: no such folder. Give the place where the SD card is mounted."
        )
    folder = card / CARD_FOLDER
    target = folder / stock.card_name
    try:
        folder.mkdir(exist_ok=True)
        others = sorted(
            entry.name
            for entry in folder.iterdir()
            if not entry.name.startswith(".") and entry.name != stock.card_name
        )
        if others:
            raise BuildError(
                f"{folder} holds other files ({', '.join(others[:4])}). The firmware "
                "must be the only file there. Remove them and run this again."
            )
        shutil.copyfile(image, target)
        copied = sha256_file(target)
    except OSError as error:
        raise BuildError(f"cannot write to the card: {error}") from None
    if copied != sha256:
        target.unlink()
        raise BuildError(
            "The copy on the card was not the same as the firmware and was removed. "
            "Try again, or try another card."
        )
    return target


def make(
    paths: RepoPaths,
    description: BuildDescription,
    card: Optional[Path] = None,
    pin_date: Optional[str] = None,
    log: Optional[Log] = None,
    stock: StockFirmware = EPM2_V16,
) -> MakeResult:
    """Make a firmware build.

    Args:
        paths: the repository.
        description: the build to make.
        card: mount point of an SD card to copy the firmware to, or None.
        pin_date: ISO date of a passed camera test. If given, the SHA-256 and
            the date are recorded in the description and it becomes the pinned
            build.
        log: where progress lines go; None for silence.
        stock: the stock firmware the build starts from.

    Returns:
        The paths of what was written, and the SHA-256.

    Raises:
        Epm2ModError: with a message for the user, if any step fails. No
            firmware file is left behind then.
    """
    say = log or (lambda line: None)
    if card is not None and not card.is_dir():
        raise BuildError(
            f"{card}: no such folder. Give the place where the SD card is mounted."
        )
    specs = load_specs(paths, description)
    stock_file = ensure_stock(paths, stock, say)
    say("1/5 stock firmware: ok")

    if description.tested:
        say(
            "2/5 free-space check: not needed, the result is compared with the recorded sha256"
        )
    else:
        say("2/5 free-space check: " + check_free_space(paths, description))

    applied = apply_specs(stock_file.read_bytes(), specs)
    say(f"3/5 applied {len(specs)} patch specs ({applied.changed_bytes} bytes changed)")

    digest = sha256_bytes(applied.image)
    if description.sha256 is not None and digest != description.sha256:
        raise BuildError(
            "The result is not the recorded build.\n"
            f"  expected {description.sha256}\n  got      {digest}\nNothing was written."
        )
    if description.tested:
        say(
            f"4/5 sha256 {digest}: this is the build that was tested on {description.camera_tested}"
        )
    else:
        say(
            f"4/5 sha256 {digest}\n    CANDIDATE: this build is NOT camera-tested. "
            "Write the sha256 in docs/camera-log.md before you flash it."
        )

    image = paths.output / f"{description.name}.BIN"
    card_copy = paths.card / CARD_FOLDER / stock.card_name
    image.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes(applied.image)
    if paths.card.exists():
        shutil.rmtree(paths.card)
    card_copy.parent.mkdir(parents=True)
    shutil.copyfile(image, card_copy)
    say(
        f"5/5 {description.name}: {description.what}\n"
        f"    firmware: {paths.relative(image)}    for the card: {paths.relative(card_copy)}"
    )

    on_card = copy_to_card(image, digest, card, stock) if card is not None else None
    if on_card is not None:
        say(
            f"on the card: {on_card}  (checked)\n"
            "Eject the card. Then, with the camera off, hold OK and switch the camera on."
        )

    if pin_date is not None:
        description = description.as_tested(digest, pin_date)
        pin(paths, description)
        say(
            f"pinned: {description.name} (camera-tested {pin_date}). "
            "Run 'epm2mod readme' and commit."
        )
    return MakeResult(description, image, card_copy, on_card, digest)
