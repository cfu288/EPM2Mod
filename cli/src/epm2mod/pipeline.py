"""The work of the commands: plain functions that the command line, the installer page's server and the tests call.

Each function gets its data through a locator (``catalogue.Locator``), never from a repository path of its own, and
returns what it did as data; the command line only formats it.

For camera owners (work from the release folder):

- ``install``: make the firmware in memory and write it, with a film file if films are chosen, to an SD card
  (``cardio``).
- ``set_films``: write only the film file.
- ``restore``: write Olympus's original firmware: the stock firmware of the pinned build.
- ``inspect_file``, ``inspect_card``: say what a firmware file, a film file or a card holds.

For developers (need a checkout for the checks of a new build):

- ``make``: make a build into the output folder.
- ``record_test``: record a passed camera test and pin the build.

How ``make`` and ``install`` make the firmware (``firmware``):

1. the stock firmware is read (downloaded first if it is absent) and its SHA-256 is checked;
2. for a candidate (a build with no recorded SHA-256), the free-space check runs on the spec list;
3. the patch specs are applied, in memory;
4. the SHA-256 of the result is compared with the recorded one (tested build) or reported (candidate);
5. the result is written: by ``make`` to ``NAME.BIN`` and ``DCOLYMP/`` in the output folder, by ``install``
   to the card.

What ``make`` guarantees about files: the outputs of an earlier run for the same build, and the whole ``DCOLYMP``
folder of the output folder, are removed before anything else is done. After a failed run they are absent; they
never hold another build. A file gets its final name only when all of it is written, flushed and read back
(``fileio.write_bytes``). These guarantees hold when a step fails and when the run is stopped by Ctrl-C or by a
termination signal that the command line turns into an interrupt (``cli.interruptible``). They cannot hold when the
process is killed outright or the power fails: then a ``.part`` file can stay, and the next run removes it.

With ``dry_run`` a function checks what it can without the network (the build, the choices, the card) and returns
what it would write; the SHA-256 of a firmware is then the recorded one, or None for a candidate.

No function chooses for the caller: the films are the choices given (none: no film file), the stock firmware is the
one the build description names, and ``restore`` writes the stock firmware of the pinned build.
"""

from __future__ import annotations

import datetime
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import cardio, catalogue
from .builds import BuildDescription, check_test_date, pin
from .camera_steps import Step, copy_text, film_steps, firmware_reads, flash_steps
from .cardio import FILMS, FIRMWARE, Content, Planned, planned_file
from .catalogue import Locator
from .container import parse
from .errors import (
    BuildCheckError,
    BuildError,
    CardError,
    ContainerError,
    LookFileError,
    NotFoundError,
)
from .fileio import Log, describe_os_error, part_path, read_bytes, silent, write_bytes
from .hashing import sha256_bytes
from .label import with_label
from .looks import lookfile
from .paths import RepoPaths
from .spec import Applied, PatchSpec, apply_specs, load_spec
from .stock import CARD_FOLDER, obtain_stock, read_stock

_CHECK_OUTPUT_LIMIT = 3000

#: The number of steps of ``make`` and ``install``; ``step`` reports each one when it ends.
STEPS = 5


def no_step(number: int) -> None:
    """Ignore the end of a step."""


def load_specs(paths: Locator, description: BuildDescription) -> list[PatchSpec]:
    """Read the patch specs of a build, in order.

    The label spec gets the build's label in place of its placeholder
    (``label.with_label``).

    Raises:
        SpecError: if a spec is missing or not valid.
        BuildError: if the label cannot be written.
    """
    specs = []
    for relative in description.specs:
        path = paths.spec_file(relative)
        spec = load_spec(path)
        if path == paths.label_spec and description.label is not None:
            spec = with_label(spec, description.label)
        specs.append(spec)
    return specs


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
        BuildCheckError: if the build has a recorded SHA-256 and the result has another.
    """
    applied = apply_specs(stock_data, specs)
    digest = sha256_bytes(applied.image)
    if description.sha256 is not None and digest != description.sha256:
        raise BuildCheckError(
            f"{description.name}: the result is not the recorded build.\n"
            f"  expected {description.sha256}\n  got      {digest}\n"
            "Nothing was written."
        )
    return applied, digest


def check_free_space(paths: RepoPaths, description: BuildDescription) -> str:
    """Run the free-space check on a build's spec list.

    The check is the project's free-space tool: ``TOOL check SPEC...``. It fails if two specs
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
                "missing. A new build needs it: see "
                f"{paths.relative(paths.free_space_tool)}."
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

    The checks are the project's emulator checks, each run as ``CHECK IMAGE``: the
    normal start and the update path. An image that does not start as the
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
            f"{tool.name}: SKIPPED, the emulator is not set up (see {paths.relative(tool.parent)}). "
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


def firmware(
    paths: Locator,
    description: BuildDescription,
    log: Log = silent,
    step: Callable[[int], None] = no_step,
    emulator_image: Path | None = None,
) -> tuple[bytes, str]:
    """Make a build's firmware in memory: steps 1 to 4 of the module text, from the stock firmware it names.

    A candidate needs a checkout for its checks (the free-space check, and the emulator for ``emulator_image``, a
    path where the image is written for the emulator; None: a temporary file).

    Returns:
        The firmware file and its SHA-256.

    Raises:
        Epm2ModError: with a message for the user, if a step fails.
    """
    specs = load_specs(paths, description)
    checkout = None if description.tested else paths.checkout()
    stock_data = obtain_stock(paths, description.stock_firmware, log)
    log("1/5 stock firmware: ok")
    step(1)
    if checkout is None:
        log(
            "2/5 free-space check: not needed, the result is compared with the "
            "recorded sha256"
        )
    else:
        log("2/5 free-space check: " + check_free_space(checkout, description))
        if description.first_code:
            log(
                "    FIRST CODE: this build runs code in an area that has never "
                "run code on a camera. The flash is the test of that area."
            )
    step(2)
    applied, digest = build_image(description, specs, stock_data)
    log(
        f"3/5 applied {len(description.specs)} patch specs "
        f"({applied.changed_bytes} bytes changed)"
    )
    step(3)
    if checkout is None:
        log(
            f"4/5 sha256 {digest}: this is the build that was tested on "
            f"{description.camera_tested}"
        )
    else:
        log(
            f"4/5 sha256 {digest}\n    CANDIDATE: this build is NOT camera-tested. "
            "Write the sha256 in the camera log before you flash it."
        )
        if emulator_image is not None:
            lines = check_in_emulator(checkout, emulator_image)
        else:
            with tempfile.TemporaryDirectory() as folder:
                image = Path(folder) / f"{description.name}.BIN"
                write_bytes(image, applied.image, BuildError)
                lines = check_in_emulator(checkout, image)
        for line in lines:
            log("    " + line)
    step(4)
    return applied.image, digest


# ---------------------------------------------------------------------------
# For camera owners


@dataclass(frozen=True)
class Outcome:
    """What a command for camera owners wrote (or, with ``dry_run``, would write).

    Attributes:
        files: the files, in the order they are written.
        removed: the extra files of ``DCOLYMP`` that are removed.
        steps: the steps on the camera that follow.
        dry_run: True if nothing was written.
        card: the card, or None for a write to a file.
        ejected: True if the card was ejected.
        build: the build of the firmware, or None.
        looks: the looks of the film file, if one is written.
        eject_error: why the card was not ejected when an eject was asked for, or None. The write is done.
    """

    files: tuple[Planned, ...]
    removed: tuple[Path, ...] = ()
    steps: tuple[Step, ...] = ()
    dry_run: bool = False
    card: Path | None = None
    ejected: bool = False
    build: BuildDescription | None = None
    looks: tuple[lookfile.Look, ...] = field(default=())
    eject_error: str | None = None

    def file_data(self) -> dict[str, bytes]:
        """Return the files' bytes by their path on the card (for the installer page's zip)."""
        names = {"firmware": FIRMWARE, "films": FILMS}
        return {
            names.get(planned.role, planned.path.name): planned.content.data
            for planned in self.files
            if planned.content.data is not None
        }


def _film_file(
    paths: Locator, choices: Sequence[str]
) -> tuple[bytes, list[lookfile.Look]]:
    """Return the film file of choices like ``ART2=velvia``, and its looks.

    Raises:
        UsageError: if a choice is wrong.
    """
    from .looks import records

    return records.pack_choices(paths, choices)


def _write_card(
    card: Path,
    files: dict[str, Content],
    eject: bool,
    is_card: Callable[[Path], bool],
) -> tuple[cardio.Plan, bool, str | None]:
    """Write files to a card that ``cardio.plan`` accepts, and eject it if asked.

    An eject that fails does not undo the write: its reason is returned.

    Returns:
        The plan that was done, True if the card was ejected, and why an eject failed (or None).
    """
    done = cardio.plan(card, files, is_card)
    cardio.write(done)
    if not eject:
        return done, False, None
    try:
        cardio.eject(done.card)
    except CardError as error:
        return done, False, str(error)
    return done, True, None


def _finish(
    card: Path | None,
    files: dict[str, Content],
    dry_run: bool,
    eject: bool,
    is_card: Callable[[Path], bool],
) -> tuple[tuple[Planned, ...], tuple[Path, ...], bool, str | None]:
    """Check (dry run) or write the files of a card; return them, the removed files, the eject and its error."""
    assert card is not None
    if dry_run:
        planned = cardio.plan(card, files, is_card)
        return planned.files, planned.removed, False, None
    done, ejected, eject_error = _write_card(card, files, eject, is_card)
    return done.files, done.removed, ejected, eject_error


def install(
    paths: Locator,
    card: Path | None,
    choices: Sequence[str],
    build: str | None = None,
    allow_untested: bool = False,
    dry_run: bool = False,
    eject: bool = False,
    log: Log = silent,
    step: Callable[[int], None] = no_step,
    is_card: Callable[[Path], bool] = cardio.is_card,
) -> Outcome:
    """Make the firmware and write it, and the film file of the choices, to a card (``epm2mod install``).

    Args:
        paths: the locator.
        card: the card's top folder, or None to make the files in memory only (the installer page's zip).
        choices: choices like ``ART2=velvia``: only those slots get a film, the others keep their Olympus art
            filter. An empty list: no film file, only the firmware.
        build: the name of the build, or None for the pinned one.
        allow_untested: True to accept a build without a passed camera test.
        dry_run: True to check and return what would be written, and write nothing.
        eject: True to eject the card after the write.
        log: where progress lines go.
        step: called with 1 to ``STEPS`` as each step ends.
        is_card: says whether a folder is an SD card (``cardio.is_card``).

    Raises:
        Epm2ModError: with a message for the user, if a step fails. The card then holds the files it had before,
            except a file that a failed write had already replaced in full.
    """
    description = catalogue.build_to_install(paths, build, allow_untested)
    load_specs(paths, description)
    stock = description.stock_firmware
    films: bytes | None = None
    looks: list[lookfile.Look] = []
    if choices:
        films, looks = _film_file(paths, choices)
    expected = Content(stock.size, description.sha256)
    planned_files: dict[str, Content] = {FIRMWARE: expected}
    if films is not None:
        planned_files[FILMS] = Content.of(films)
    if card is not None:
        cardio.plan(card, planned_files, is_card)
    if not dry_run:
        image, _ = firmware(paths, description, log, step)
        cardio.check_model(image)
        planned_files[FIRMWARE] = Content.of(image)
    eject_error = None
    if card is not None:
        files, removed, ejected, eject_error = _finish(
            card, planned_files, dry_run, eject, is_card
        )
        if not dry_run:
            log(f"5/5 on the card: {card}  (written, flushed and read back)")
    else:
        files = tuple(
            Planned(Path(name), cardio.ROLES[name], content, False)
            for name, content in planned_files.items()
        )
        removed, ejected = (), False
    step(5)
    names = [CARD_FOLDER] + ([lookfile.CARD_NAME] if films is not None else [])
    steps = flash_steps(
        films=films is not None,
        firmware=firmware_reads(description.label),
        art_shows=catalogue.art_check(looks),
        copy=copy_text(names, "the zip") if card is None else None,
        ejected=ejected,
    )
    return Outcome(
        files,
        removed,
        tuple(steps),
        dry_run,
        card,
        ejected,
        description,
        tuple(looks),
        eject_error,
    )


def set_films(
    paths: Locator,
    choices: Sequence[str],
    card: Path | None = None,
    out: Path | None = None,
    dry_run: bool = False,
    eject: bool = False,
    is_card: Callable[[Path], bool] = cardio.is_card,
    looks: Sequence[lookfile.Look] | None = None,
) -> Outcome:
    """Write only the film file, to a card or a file (``epm2mod films set``, ``films pack``).

    ``choices`` as for ``install``. ``looks``, if given, are written in place of the choices (``films pack``: a look
    list of fit files, for developers). With neither ``card`` nor ``out``, the file is only returned (the installer
    page's zip).

    Raises:
        Epm2ModError: with a message for the user, if a step fails.
    """
    if looks is None:
        data, looks = _film_file(paths, choices)
    else:
        data = lookfile.pack(looks)
    art_shows = catalogue.art_check(looks)
    content = {FILMS: Content.of(data)}
    eject_error = None
    if card is not None:
        files, removed, ejected, eject_error = _finish(
            card, content, dry_run, eject, is_card
        )
        copy = None
    elif out is not None:
        files, removed, ejected = (
            (planned_file(out, "films", content[FILMS]),),
            (),
            False,
        )
        if not dry_run:
            write_bytes(out, data, read_back=True)
        copy = (
            copy_text([out.name])
            if out.name == lookfile.CARD_NAME
            else (f"Copy {out.name} to the top of the SD card as {lookfile.CARD_NAME}.")
        )
    else:
        files = (Planned(Path(FILMS), "films", content[FILMS], False),)
        removed, ejected = (), False
        copy = copy_text([FILMS], "the zip")
    steps = film_steps(art_shows=art_shows, copy=copy, ejected=ejected)
    return Outcome(
        files,
        removed,
        tuple(steps),
        dry_run,
        card,
        ejected,
        None,
        tuple(looks),
        eject_error,
    )


def restore(
    paths: Locator,
    card: Path | None = None,
    out: Path | None = None,
    dry_run: bool = False,
    eject: bool = False,
    log: Log = silent,
    step: Callable[[int], None] = no_step,
    is_card: Callable[[Path], bool] = cardio.is_card,
) -> Outcome:
    """Write Olympus's original firmware to a card or a file, to remove EPM2Mod (``epm2mod restore``).

    The file is the stock firmware of the pinned build. It is downloaded if absent and checked by its SHA-256
    (``obtain_stock``). It does not remove the film file or the films kept in the camera. ``step`` is called with 1
    when the file is checked and 2 when it is written. With neither ``card`` nor ``out``, the file is only returned
    (the installer page's zip).

    Raises:
        Epm2ModError: with a message for the user, if a step fails.
    """
    stock = paths.pinned_build().stock_firmware
    content = Content(stock.size, stock.sha256)
    if card is not None:
        cardio.plan(card, {FIRMWARE: content}, is_card)
    if not dry_run:
        content = Content.of(obtain_stock(paths, stock, log))
        log("1/2 original firmware: ok")
    step(1)
    copy = None
    eject_error = None
    if card is not None:
        files, removed, ejected, eject_error = _finish(
            card, {FIRMWARE: content}, dry_run, eject, is_card
        )
        if not dry_run:
            log(f"2/2 on the card: {card}  (written, flushed and read back)")
    elif out is not None:
        files, removed, ejected = (planned_file(out, "firmware", content),), (), False
        if not dry_run and content.data is not None:
            write_bytes(out, content.data, read_back=True)
        copy = f"Copy {out.name} to the SD card as {FIRMWARE}."
    else:
        files = (Planned(Path(FIRMWARE), "firmware", content, False),)
        removed, ejected = (), False
        copy = copy_text([CARD_FOLDER], "the zip")
    step(2)
    steps = flash_steps(
        films=False,
        firmware=firmware_reads(None),
        art_shows=catalogue.art_check(()),
        copy=copy,
        ejected=ejected,
    )
    return Outcome(
        files, removed, tuple(steps), dry_run, card, ejected, eject_error=eject_error
    )


def _picture(look: lookfile.Look) -> str:
    """Return what a look makes: ``colour`` or ``black-and-white``.

    A black-and-white film is a colour record with saturation gain 0 (the look file format), so the record's kind
    alone does not say it.
    """
    colour = isinstance(look, lookfile.ColourLook) and look.gain != 0
    return "colour" if colour else "black-and-white"


@dataclass(frozen=True)
class FileReport:
    """What ``inspect`` found in one file.

    Attributes:
        path: the file.
        kind: ``firmware`` or ``films``.
        size: its size in bytes.
        sha256: its sha256.
        model: the camera model of a firmware file (``E-PM2``, ``E-PL5``, or the model bytes), else None.
        build: the build a firmware file is: a build name, ``Olympus original``, or None if it is not known.
        version: the firmware's version: the build's label, ``1.6`` for Olympus's file, or None.
        checksums_ok: for a firmware file, True if every block's checksum is right.
        films: the looks of a film file: ART number, name and kind.
        problem: what is wrong with the file, or None.
    """

    path: Path
    kind: str
    size: int
    sha256: str
    model: str | None = None
    build: str | None = None
    version: str | None = None
    checksums_ok: bool | None = None
    films: tuple[dict[str, Any], ...] = ()
    problem: str | None = None

    def to_json(self) -> dict[str, Any]:
        """Return the report for ``--json``."""
        return {
            "path": str(self.path),
            "kind": self.kind,
            "size": self.size,
            "sha256": self.sha256,
            "model": self.model,
            "build": self.build,
            "version": self.version,
            "checksums_ok": self.checksums_ok,
            "films": list(self.films),
            "problem": self.problem,
        }


@dataclass(frozen=True)
class Inspection:
    """What ``inspect`` found: the files, and what will not work.

    Attributes:
        files: one report per file.
        problems: what will not work, in words for the user.
        card: the card, for ``inspect --card``.
    """

    files: tuple[FileReport, ...]
    problems: tuple[str, ...] = ()
    card: Path | None = None


#: The model names of the model bytes of a firmware block header.
MODELS = {b"\x10\x10": "E-PM2", b"\x10\x00": "E-PL5"}


def _stock_files(paths: Locator) -> set[str]:
    """Return the sha256 of each stock firmware that a build of the locator names."""
    return {build.stock_firmware.sha256 for build in paths.all_builds()}


def _firmware_report(paths: Locator, path: Path, data: bytes) -> FileReport:
    """Return the report of a firmware file."""
    container = parse(data)
    digest = sha256_bytes(data)
    models = {block.header[2:4] for block in container.blocks}
    model = ", ".join(MODELS.get(code, code.hex(" ")) for code in sorted(models))
    build = version = None
    if digest in _stock_files(paths):
        build, version = "Olympus original", "1.6"
    else:
        for description in paths.all_builds():
            if description.sha256 == digest:
                build, version = description.name, description.label
                break
    problem = None
    if not container.checksums_ok:
        problem = "a block's checksum is wrong: the file is damaged"
    elif models != {cardio.MODEL_BYTES}:
        problem = f"the firmware is for the {model}, not the E-PM2"
    return FileReport(
        path,
        "firmware",
        len(data),
        digest,
        model=model,
        build=build,
        version=version,
        checksums_ok=container.checksums_ok,
        problem=problem,
    )


def _films_report(path: Path, data: bytes) -> FileReport:
    """Return the report of a film file; a damaged one gets a problem."""
    digest = sha256_bytes(data)
    try:
        looks = lookfile.unpack(data)
    except LookFileError as error:
        return FileReport(
            path,
            "films",
            len(data),
            digest,
            problem=f"the film file is damaged: {error}. The camera shows Bad file",
        )
    films = tuple(
        {
            "art": look.slot + 1,
            "name": look.name,
            "kind": _picture(look),
        }
        for look in looks
    )
    return FileReport(path, "films", len(data), digest, films=films)


def inspect_file(paths: Locator, path: Path) -> Inspection:
    """Say what a firmware file or a film file is (``epm2mod inspect FILE``).

    Raises:
        NotFoundError: if the file is missing or is neither a firmware file nor a film file.
    """
    if not path.is_file():
        raise NotFoundError(f"{path}: no such file")
    data = read_bytes(path, NotFoundError)
    if data.startswith(lookfile.MAGIC):
        report = _films_report(path, data)
    else:
        try:
            report = _firmware_report(paths, path, data)
        except ContainerError:
            raise NotFoundError(
                f"{path}: is not a firmware file or a film file"
            ) from None
    return Inspection((report,), (report.problem,) if report.problem else ())


def inspect_card(paths: Locator, card: Path) -> Inspection:
    """Say what is on a card, and what will not work (``epm2mod inspect --card``).

    What will not work: a damaged firmware or film file, firmware for another model, extra files in ``DCOLYMP``,
    and a film file beside Olympus's original firmware (which does not load it).

    Raises:
        NotFoundError: if the folder is missing or holds neither file.
    """
    if not card.is_dir():
        raise NotFoundError(f"{card}: no such folder")
    reports: list[FileReport] = []
    problems: list[str] = []
    firmware_file, films_file = card / FIRMWARE, card / FILMS
    if firmware_file.is_file():
        data = read_bytes(firmware_file, NotFoundError)
        try:
            reports.append(_firmware_report(paths, firmware_file, data))
        except ContainerError:
            problems.append(f"{firmware_file}: is not a firmware file")
    if films_file.is_file():
        reports.append(_films_report(films_file, read_bytes(films_file)))
    if not reports and not problems:
        raise NotFoundError(f"{card}: holds no firmware file and no film file")
    problems += [
        f"{report.path}: {report.problem}" for report in reports if report.problem
    ]
    folder = card / CARD_FOLDER
    if folder.is_dir():
        extra = sorted(e.name for e in folder.iterdir() if e.name != firmware_file.name)
        if extra:
            problems.append(
                f"{folder} holds other files ({', '.join(extra[:4])}): the camera's updater needs the firmware to "
                "be the only file there. 'epm2mod install' removes them."
            )
    kinds = {report.kind: report for report in reports}
    if (
        "films" in kinds
        and kinds.get("firmware")
        and kinds["firmware"].build == "Olympus original"
    ):
        problems.append(
            f"{films_file}: Olympus's original firmware does not load the film file: install EPM2Mod first"
        )
    return Inspection(tuple(reports), tuple(problems), card)


# ---------------------------------------------------------------------------
# For developers


@dataclass(frozen=True)
class MakeResult:
    """What ``make`` produced (or, with ``dry_run``, would produce).

    Attributes:
        description: the build that was made.
        image: the firmware file, ``NAME.BIN`` in the output folder.
        card_copy: the copy under the camera's file name, in the output folder's ``DCOLYMP``.
        sha256: SHA-256 of the firmware file (for a dry run of a candidate: None).
        files: every file written.
    """

    description: BuildDescription
    image: Path
    card_copy: Path
    sha256: str | None
    files: tuple[Planned, ...] = ()


def image_path(paths: Locator, name: str) -> Path:
    """Return where the firmware file of the build called ``name`` is written."""
    return paths.output_folder() / f"{name}.BIN"


def card_folder(paths: Locator) -> Path:
    """Return the camera's folder in the output folder, as on the SD card."""
    return paths.output_folder() / CARD_FOLDER


def clear_outputs(paths: Locator, name: str | None) -> None:
    """Remove what an earlier run left: the card folder and one build's image.

    A caller that may fail before ``make`` runs (for example while it reads
    the build description) calls this first. The card folder, which is what a
    user copies to the SD card, is then never the one of an earlier run. The
    image of a build is removed only if the caller knows the build's name.

    Args:
        paths: the locator.
        name: the build whose image is removed, or None for the card folder only.

    Raises:
        BuildError: if something cannot be removed.
    """
    stale_files = []
    if name is not None:
        image = image_path(paths, name)
        stale_files = [image, part_path(image)]
    card = card_folder(paths)
    try:
        for stale in stale_files:
            if stale.exists() or stale.is_symlink():
                stale.unlink()
        if card.is_symlink():
            card.unlink()
        elif card.exists():
            shutil.rmtree(card)
    except OSError as error:
        raise BuildError(
            "cannot remove the outputs of an earlier run: "
            f"{describe_os_error(error)}"
        ) from None


def make(
    paths: Locator,
    description: BuildDescription,
    log: Log = silent,
    output: Path | None = None,
    step: Callable[[int], None] = no_step,
    dry_run: bool = False,
) -> MakeResult:
    """Make a firmware build into the output folder (``epm2mod make``).

    It writes ``NAME.BIN`` and ``DCOLYMP/E1019999.BIN`` in the output folder, and one more copy to the file
    ``output`` if given. It writes no film file.

    Raises:
        Epm2ModError: with a message for the user, if any step fails. Then
            ``NAME.BIN`` and ``DCOLYMP`` do not exist in the output folder. The same holds
            if the run is interrupted (see the module text).
    """
    image = image_path(paths, description.name)
    stock = description.stock_firmware
    card_copy = paths.output_folder() / FIRMWARE
    if dry_run:
        load_specs(paths, description)
        content = Content(stock.size, description.sha256)
        targets = [image, card_copy] + ([output] if output is not None else [])
        planned = [planned_file(path, "firmware", content) for path in targets]
        return MakeResult(
            description, image, card_copy, description.sha256, tuple(planned)
        )
    clear_outputs(paths, description.name)
    try:
        data, digest = firmware(paths, description, log, step, emulator_image=None)
        written = [image, card_copy] + ([output] if output is not None else [])
        planned = [planned_file(path, "firmware", Content.of(data)) for path in written]
        for path in written:
            write_bytes(path, data, BuildError, read_back=True)
    except BaseException:
        clear_outputs(paths, description.name)
        raise
    log(
        f"5/5 {description.name}: {description.what}\n"
        f"    firmware: {paths.relative(image)}    "
        f"for the card: {paths.relative(card_folder(paths))}"
    )
    step(5)
    return MakeResult(description, image, card_copy, digest, tuple(planned))


def current_date() -> datetime.date:
    """Return today's date on this computer's clock."""
    return datetime.date.today()


def record_test(
    paths: RepoPaths,
    description: BuildDescription,
    sha256: str,
    date: str,
    log: Log = silent,
    today: datetime.date | None = None,
    dry_run: bool = False,
) -> BuildDescription:
    """Record a passed camera test and make the build the pinned one.

    ``sha256`` is the SHA-256 of the firmware file that was on the camera, as
    written in the camera log before the flash. The build is made again in
    memory, and the test is recorded only if the result has that SHA-256. So a
    spec that changed after the flash cannot be recorded as tested.

    A description that already holds this record is only pinned again. A
    description with another record is refused.

    Args:
        paths: the checkout.
        description: the build that was tested.
        sha256: SHA-256 of the firmware file that was flashed.
        date: the date of the test, YYYY-MM-DD; not in the future.
        log: where progress lines go.
        today: the current date; for tests.
        dry_run: True to check everything and write nothing.

    Returns:
        The description with the test record.

    Raises:
        BuildError: if the date or the SHA-256 is wrong, the build has another
            record, or the build no longer gives that SHA-256.
        StockError: if the stock firmware is missing or wrong.
    """
    check_test_date(date, today or current_date())
    tested = description.as_tested(sha256, date)
    stock_data = read_stock(paths, tested.stock_firmware)
    _, digest = build_image(tested, load_specs(paths, tested), stock_data)
    if dry_run:
        log(f"would pin: {tested.name}, camera-tested {date}, sha256 {digest}")
        return tested
    pin(paths, tested)
    log(
        f"pinned: {tested.name}, camera-tested {date}, sha256 {digest}. "
        "Run 'epm2mod generate', write the result in the camera log, and commit."
    )
    return tested
