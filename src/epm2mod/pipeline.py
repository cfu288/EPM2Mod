"""The steps that make a firmware build.

``make`` is the one way firmware is made in this repository, for a user who
installs the pinned build and for a developer who tries a new one:

1. the stock firmware is read (downloaded first if it is absent) and its
   SHA-256 is checked;
2. for a candidate (a build with no recorded SHA-256), the free-space check
   runs on the spec list;
3. the patch specs are applied, in memory;
4. the SHA-256 of the result is compared with the recorded one (tested build)
   or reported (candidate);
5. the firmware is written to ``build/NAME.BIN`` and, under the name the camera
   looks for, to ``build/card/DCOLYMP/``; optionally also to an SD card.

What ``make`` guarantees about files:

* The outputs of an earlier run for the same build, and the whole ``build/card``
  folder, are removed before anything else is done. After a failed run they are
  absent; they never hold another build. Two limits: if no build is named and
  the pointer to the pinned build cannot be read, the name of the image is not
  known, so only ``build/card`` is removed; and a command line that is not
  accepted (exit status 2) removes nothing.
* A firmware file gets its final name only when all of it is written, flushed
  and read back (``fileio.write_bytes``). No final name ever holds part of a
  file.
* On the SD card the new file replaces an older one only when it is complete
  and was read back from the card. The card is never given a part of a file
  under the camera's file name.
* ``--out`` takes any folder that exists (the top folder of the SD card, or
  another folder). A path that does not exist is an error, so a mistyped path
  is not reported as a copy.

These guarantees hold when a step fails and when the run is stopped by Ctrl-C
or by a termination signal that the command line turns into an interrupt
(``cli.interruptible``). They cannot hold when the process is killed outright
or the power fails: then a ``.part`` file can stay, and the next run removes it.

``record_test`` is the separate step that turns a candidate into a tested build
after a camera test.
"""

from __future__ import annotations

import datetime
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .builds import BuildDescription, check_test_date, pin
from .errors import BuildError
from .fileio import (
    Log,
    describe_os_error,
    part_path,
    silent,
    sync_folder,
    write_bytes,
)
from .hashing import sha256_bytes
from .paths import RepoPaths
from .spec import Applied, PatchSpec, apply_specs, load_spec
from .stock import CARD_FOLDER, EPM2_V16, StockFirmware, obtain_stock, read_stock

_CHECK_OUTPUT_LIMIT = 3000


@dataclass(frozen=True)
class MakeResult:
    """What ``make`` produced.

    Attributes:
        description: the build that was made.
        image: the firmware file, ``build/NAME.BIN``.
        card_copy: the copy under the camera's file name, in ``build/card``.
        on_card: the copy on the SD card, or None if no card was given.
        sha256: SHA-256 of the firmware file.
    """

    description: BuildDescription
    image: Path
    card_copy: Path
    on_card: Path | None
    sha256: str


def load_specs(paths: RepoPaths, description: BuildDescription) -> list[PatchSpec]:
    """Read the patch specs of a build, in order.

    Raises:
        SpecError: if a spec is missing or not valid.
    """
    return [load_spec(paths.resolve(relative)) for relative in description.specs]


def build_image(
    description: BuildDescription, specs: list[PatchSpec], stock_data: bytes
) -> tuple[Applied, str]:
    """Apply a build's specs to the stock firmware, in memory, and check the result.

    Args:
        description: the build.
        specs: the build's patch specs, as ``load_specs`` returns them.
        stock_data: the checked bytes of the stock firmware.

    Returns:
        The applied result and the SHA-256 of its image.

    Raises:
        SpecError: if a spec does not fit the firmware.
        BuildError: if the build has a recorded SHA-256 and the result has another.
    """
    applied = apply_specs(stock_data, specs)
    digest = sha256_bytes(applied.image)
    if description.sha256 is not None and digest != description.sha256:
        raise BuildError(
            f"{description.name}: the result is not the recorded build.\n"
            f"  expected {description.sha256}\n  got      {digest}\n"
            "Nothing was written."
        )
    return applied, digest


def check_free_space(paths: RepoPaths, description: BuildDescription) -> str:
    """Run the free-space check on a build's spec list.

    The check is ``tools/freespace.py check SPEC...``. It fails if two specs
    put bytes in the same place, or a spec puts bytes where the camera does
    not load the firmware, or a spec puts code in an area where no
    camera-tested build runs code yet. The last rule is waived for a
    description with ``first_code``: its flash is the test of that area.
    It also fails if code that runs in SRAM calls into the bytes of a spec, or
    if a hook in early-loaded code jumps to code that is loaded later.

    Returns:
        The last line of the check's output.

    Raises:
        BuildError: if the check fails or cannot run.
    """
    command = [sys.executable, str(paths.free_space_tool), "check", *description.specs]
    if description.first_code:
        command.append("--first-code")
    try:
        done = subprocess.run(
            command,
            cwd=paths.root,
            capture_output=True,
            text=True,
            errors="backslashreplace",
            check=False,
        )
    except OSError as error:
        raise BuildError(f"the free-space check cannot run: {error}") from None
    output = (done.stdout + done.stderr).strip()
    if done.returncode != 0:
        hint = ""
        if not paths.firmware_map.exists():
            hint = (
                f"\nThe firmware map ({paths.relative(paths.firmware_map)}) is "
                "missing. A new build needs it: see tools/fwmap.py and "
                "tools/freespace.py."
            )
        shown = output[-_CHECK_OUTPUT_LIMIT:]
        if len(output) > len(shown):  # start the cut text at a whole line
            shown = shown.partition("\n")[2]
        raise BuildError(
            f"{shown}\n" f"the free-space check failed: nothing was built{hint}"
        )
    return output.splitlines()[-1] if output else "ok"


_EMULATOR_NOT_SET_UP = 3


def check_in_emulator(paths: RepoPaths, image: Path) -> list[str]:
    """Start a firmware image in the emulator: the normal start and the update path.

    The checks are ``tools/emu/boot-test IMAGE`` and
    ``tools/emu/update-path-test IMAGE``. An image that does not start as the
    stock firmware does, or does not find an update file with OK held, could
    leave the camera with no way back.

    Returns:
        One line for each check: its result, or that it was skipped because
        the emulator is not set up on this computer.

    Raises:
        BuildError: if a check fails.
    """
    lines = []
    for tool in paths.emulator_checks:
        skipped = (
            f"{tool.name}: SKIPPED, the emulator is not set up (tools/emu/setup.sh). "
            "Do not flash this build before the check has passed."
        )
        if not tool.exists():
            lines.append(skipped)
            continue
        try:
            done = subprocess.run(
                [sys.executable, str(tool), str(image)],
                cwd=paths.root,
                capture_output=True,
                text=True,
                errors="backslashreplace",
                check=False,
            )
        except OSError as error:
            raise BuildError(f"{tool.name} cannot run: {error}") from None
        output = (done.stdout + done.stderr).strip()
        if done.returncode == _EMULATOR_NOT_SET_UP:
            lines.append(skipped)
        elif done.returncode != 0:
            raise BuildError(
                f"{output[-_CHECK_OUTPUT_LIMIT:]}\n"
                f"{tool.name} failed: the build was removed. Do not flash it."
            )
        else:
            lines.append(output.splitlines()[-1] if output else f"{tool.name}: PASS")
    return lines


def card_target(card: Path, stock: StockFirmware) -> Path:
    """Return where the firmware file goes on an SD card mounted at ``card``."""
    return card / CARD_FOLDER / stock.card_name


def is_volume(folder: Path) -> bool:
    """Return True if ``folder`` is the top folder of a mounted volume."""
    return os.path.ismount(folder)


def check_card(card: Path, stock: StockFirmware) -> list[str]:
    """Check the folder that the firmware goes to, before any work is done.

    ``card`` is the top folder of the SD card, or any folder that stands for
    it: the firmware is written to ``card/DCOLYMP/``. The folder must exist. A
    card that is read-only or full is found later, when the file is written.

    The camera's updater needs the firmware to be the only file in its folder.
    Other files there are an error; they are not deleted. Names that start with
    a dot (which some computers add and hide) are reported, not refused. A
    temporary file that an interrupted run left is ours and is ignored.

    Args:
        card: the top folder of the card, or another folder.
        stock: the stock firmware, for the camera's file name.

    Returns:
        The names in the firmware folder that start with a dot.

    Raises:
        BuildError: if ``card`` is not a folder, or the firmware folder cannot
            be read or holds other files.
    """
    try:
        is_folder, exists = card.is_dir(), card_target(card, stock).parent.exists()
    except OSError as error:
        raise BuildError(
            f"{card}: cannot be read: {describe_os_error(error)}"
        ) from None
    if not is_folder:
        raise BuildError(f"{card}: no such folder")
    target = card_target(card, stock)
    folder = target.parent
    if not exists:
        return []
    ours = {target.name, part_path(target).name}
    try:
        names = sorted(entry.name for entry in folder.iterdir())
    except OSError as error:
        raise BuildError(
            f"{folder}: cannot be read: {describe_os_error(error)}"
        ) from None
    others = [name for name in names if name not in ours and not name.startswith(".")]
    if others:
        raise BuildError(
            f"{folder} holds other files ({', '.join(others[:4])}). The firmware "
            "must be the only file there. Remove them and run this again."
        )
    return [name for name in names if name.startswith(".")]


def copy_to_card(image: bytes, card: Path, stock: StockFirmware) -> Path:
    """Write the firmware to an SD card and check what was written.

    The data goes to a temporary name in the firmware folder, is flushed to the
    card and read back, and only then takes the camera's file name
    (``fileio.write_bytes`` with ``read_back``). If a step before the rename
    fails, the temporary file is removed and a firmware file that was on the
    card before is still there, unchanged. If the last step fails (the flush
    of the folder, after the rename), the card holds the new file but the
    write is not confirmed. The error message says which of the two happened.

    Args:
        image: the firmware file.
        card: the folder where the card is mounted.
        stock: the stock firmware, for the camera's file name.

    Returns:
        The path of the file on the card.

    Raises:
        BuildError: if the card cannot take the file (see ``check_card``), the
            write fails, or the data read back differs.
    """
    check_card(card, stock)
    target = card_target(card, stock)
    try:
        write_bytes(target, image, BuildError, read_back=True, flush_folder=False)
    except BuildError as error:
        raise BuildError(
            f"{error}\nThe new firmware is NOT on the card. If the card holds "
            f"a {target.name}, it is an older file: do not update the camera "
            "from it unless you know that it is the build you want."
        ) from None
    try:
        sync_folder(target.parent)
    except OSError as error:
        raise BuildError(
            f"{target}: is the new firmware, but the card did not confirm the "
            f"write ({describe_os_error(error)}). The card's state is not "
            "certain. Do not use the card. Run this again."
        ) from None
    return target


def image_path(paths: RepoPaths, name: str) -> Path:
    """Return where the firmware file of the build called ``name`` is written."""
    return paths.output / f"{name}.BIN"


def clear_outputs(paths: RepoPaths, name: str | None) -> None:
    """Remove what an earlier run left: the card folder and one build's image.

    A caller that may fail before ``make`` runs (for example while it reads
    the build description) calls this first. The card folder, which is what a
    user copies to the SD card, is then never the one of an earlier run. The
    image of a build is removed only if the caller knows the build's name.

    Args:
        paths: the repository.
        name: the build whose image is removed, or None for the card folder only.

    Raises:
        BuildError: if something cannot be removed.
    """
    stale_files = []
    if name is not None:
        image = image_path(paths, name)
        stale_files = [image, part_path(image)]
    try:
        for stale in stale_files:
            if stale.exists() or stale.is_symlink():
                stale.unlink()
        if paths.card.is_symlink():
            paths.card.unlink()
        elif paths.card.exists():
            shutil.rmtree(paths.card)
    except OSError as error:
        raise BuildError(
            "cannot remove the outputs of an earlier run: "
            f"{describe_os_error(error)}"
        ) from None


def make(
    paths: RepoPaths,
    description: BuildDescription,
    card: Path | None = None,
    log: Log = silent,
    stock: StockFirmware = EPM2_V16,
) -> MakeResult:
    """Make a firmware build.

    Args:
        paths: the repository.
        description: the build to make.
        card: a folder to copy the firmware to (the top folder of the SD card,
            or another folder), or None.
        log: where progress lines go.
        stock: the stock firmware the build starts from.

    Returns:
        The paths of what was written, and the SHA-256.

    Raises:
        Epm2ModError: with a message for the user, if any step fails. Then
            ``build/NAME.BIN`` and ``build/card`` do not exist. The same holds
            if the run is interrupted (see the module text). The SD card then
            holds the firmware file it had before; only if the failure came
            after the new file took its name does it hold the complete new file.
    """
    image = image_path(paths, description.name)
    card_copy = card_target(paths.card, stock)
    clear_outputs(paths, description.name)
    if card is not None:
        card = card.absolute()
    hidden = check_card(card, stock) if card is not None else []
    specs = load_specs(paths, description)

    stock_data = obtain_stock(paths, stock, log)
    log("1/5 stock firmware: ok")

    if description.tested:
        log(
            "2/5 free-space check: not needed, the result is compared with the "
            "recorded sha256"
        )
    else:
        log("2/5 free-space check: " + check_free_space(paths, description))
        if description.first_code:
            log(
                "    FIRST CODE: this build runs code in an area that has never "
                "run code on a camera. The flash is the test of that area."
            )

    applied, digest = build_image(description, specs, stock_data)
    log(
        f"3/5 applied {len(description.specs)} patch specs "
        f"({applied.changed_bytes} bytes changed)"
    )
    if description.tested:
        log(
            f"4/5 sha256 {digest}: this is the build that was tested on "
            f"{description.camera_tested}"
        )
    else:
        log(
            f"4/5 sha256 {digest}\n    CANDIDATE: this build is NOT camera-tested. "
            "Write the sha256 in docs/camera-log.md before you flash it."
        )

    try:
        write_bytes(image, applied.image, BuildError, read_back=True)
        if not description.tested:
            for line in check_in_emulator(paths, image):
                log("    " + line)
        write_bytes(card_copy, applied.image, BuildError, read_back=True)
        on_card = copy_to_card(applied.image, card, stock) if card is not None else None
    except BaseException:
        clear_outputs(paths, description.name)
        raise
    log(
        f"5/5 {description.name}: {description.what}\n"
        f"    firmware: {paths.relative(image)}    "
        f"for the card: {paths.relative(card_copy)}"
    )
    if on_card is not None:
        log(f"copied to: {on_card}  (written, flushed and read back)")
        if hidden:
            log(
                f"    note: {on_card.parent} also holds {', '.join(hidden[:4])}. "
                "If the camera does not start the update, remove them."
            )
        if card is not None and is_volume(card):
            log(
                "Eject the card. Then, with the camera off, hold OK and switch the "
                "camera on."
            )
        else:
            log(
                f"Copy the folder {CARD_FOLDER} to the top folder of the SD card. "
                "Then, with the camera off, hold OK and switch the camera on."
            )
    return MakeResult(description, image, card_copy, on_card, digest)


def current_date() -> datetime.date:
    """Return today's date on this computer's clock."""
    return datetime.date.today()


def record_test(
    paths: RepoPaths,
    description: BuildDescription,
    sha256: str,
    date: str,
    log: Log = silent,
    stock: StockFirmware = EPM2_V16,
    today: datetime.date | None = None,
) -> BuildDescription:
    """Record a passed camera test and make the build the pinned one.

    ``sha256`` is the SHA-256 of the firmware file that was on the camera, as
    written in the camera log before the flash. The build is made again in
    memory, and the test is recorded only if the result has that SHA-256. So a
    spec that changed after the flash cannot be recorded as tested.

    A description that already holds this record is only pinned again. A
    description with another record is refused.

    Args:
        paths: the repository.
        description: the build that was tested.
        sha256: SHA-256 of the firmware file that was flashed.
        date: the date of the test, YYYY-MM-DD; not in the future.
        log: where progress lines go.
        stock: the stock firmware the build starts from.
        today: the current date; for tests.

    Returns:
        The description with the test record.

    Raises:
        BuildError: if the date or the SHA-256 is wrong, the build has another
            record, or the build no longer gives that SHA-256.
        StockError: if the stock firmware is missing or wrong.
    """
    check_test_date(date, today or current_date())
    tested = description.as_tested(sha256, date)
    _, digest = build_image(tested, load_specs(paths, tested), read_stock(paths, stock))
    pin(paths, tested)
    log(
        f"pinned: {tested.name}, camera-tested {date}, sha256 {digest}. "
        "Run 'epm2mod readme', write the result in docs/camera-log.md, and commit."
    )
    return tested
