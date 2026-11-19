"""The steps on the camera after a write: the one source for the command line, the installer page and the documents.

Each step is a ``Step``: an id that does not change and the text a user reads. The command line prints the texts
(``epm2mod install``, ``films set``, ``restore``) and puts them in ``--json``; the installer page gets them from the
server (``serve.Job.state``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .looks.lookfile import CARD_NAME
from .stock import CARD_FOLDER

#: The menu path that loads the film file into the camera.
LOAD_LOOKS = (
    "MENU → SETUP → gears tab → J → Load Looks → Load → OK. "
    "If there is no gears tab, set wrench tab → Menu Display → Custom Menu to On."
)


@dataclass(frozen=True)
class Step:
    """One step on the camera.

    Attributes:
        id: what the step does, for a program: ``copy``, ``eject``, ``insert``, ``flash``, ``wait``, ``restart``,
            ``check-firmware``, ``load-films``, ``check-art``.
        text: what the user reads.
    """

    id: str
    text: str

    def to_json(self) -> dict[str, Any]:
        """Return the step for ``--json`` and the installer page."""
        return {"id": self.id, "text": self.text}


def _start(copy: str | None, ejected: bool) -> list[Step]:
    """Return the steps that get the card from the computer into the camera's hands."""
    steps = [Step("copy", copy)] if copy is not None else []
    if ejected:
        steps.append(Step("eject", "Take the card out of the computer."))
    else:
        steps.append(
            Step(
                "eject",
                "Eject the card (Mac: ⏏ in Finder. Windows: right-click → Eject) and take it out.",
            )
        )
    return steps


def copy_text(names: list[str], source: str | None = None) -> str:
    """Return the copy step for files that were not written to a card: their names (and where they are), to the top
    of the card."""
    where = f" from {source}" if source else ""
    return f"Copy {' and '.join(names)}{where} to the top of the SD card."


def firmware_reads(label: str | None) -> str:
    """Return what the camera's Firmware screen reads after the flash: the build's label, or ``Body : 1.6``.

    Args:
        label: the build's label (``BuildDescription.label``), or None for a build without one and for Olympus's
            original firmware.
    """
    return "Body : 1.6" if label is None else f"Body : 1.6  EPM2Mod {label}"


def flash_steps(
    *,
    films: bool,
    firmware: str,
    art_shows: str,
    copy: str | None = None,
    ejected: bool = False,
) -> list[Step]:
    """Return the steps that install a firmware file on the camera.

    Args:
        films: True if a film file goes with the firmware: then the steps load it.
        firmware: what the Firmware screen reads after the flash (``firmware_reads``).
        art_shows: what the ART menu shows at the end (``catalogue.art_check``).
        copy: the text of a first step that copies the files to the card, or None if they are on the card.
        ejected: True if the card was ejected already.
    """
    steps = _start(copy, ejected) + [
        Step(
            "insert",
            "Open the cover on the bottom of the camera and put in a charged battery and the card.",
        ),
        Step(
            "flash",
            "Hold OK (middle of the arrow pad) and ON/OFF together until the orange lamp on the front stays lit, "
            "then let go.",
        ),
        Step("wait", "Leave the camera alone until the lamp blinks (1 to 2 minutes)."),
        Step("restart", "Turn the camera off and on."),
        Step(
            "check-firmware",
            f"Check that MENU → SETUP → wrench tab → Firmware reads {firmware}.",
        ),
    ]
    if films:
        steps.append(Step("load-films", LOAD_LOOKS))
    steps.append(Step("check-art", f"Check that MENU → ART shows {art_shows}"))
    return steps


def film_steps(
    *,
    art_shows: str,
    copy: str | None = None,
    ejected: bool = False,
) -> list[Step]:
    """Return the steps that load a film file into a camera that runs EPM2Mod (``films set``)."""
    return _start(copy, ejected) + [
        Step("insert", "Put the card in the camera and switch it on."),
        Step("load-films", LOAD_LOOKS),
        Step("check-art", f"Check that MENU → ART shows {art_shows}"),
    ]


#: The names of the files on the card, for the copy step.
CARD_FILES = (CARD_FOLDER, CARD_NAME)
