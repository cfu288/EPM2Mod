"""Exception types of the package.

Every error that a user can cause or meet (a wrong file, a failed download, a
spec that does not fit the firmware, a full disk) is an ``Epm2ModError``. The
command-line interface prints its message and exits with the error's
``exit_status``. Any other exception is a programming error; it is not caught
and shows a traceback.

Exit statuses (rule 4 of the command line): 1 failed, 2 wrong usage, 3 nothing
found or not recognised, 4 a check failed (checksum, read-back, model, untested
build), 5 the environment (no network, no checkout, card not writable or full).
"""

#: The exit status of each kind of failure.
FAILED, USAGE, NOT_FOUND, CHECK_FAILED, ENVIRONMENT = 1, 2, 3, 4, 5


class Epm2ModError(Exception):
    """Base class of the errors that the package reports to the user."""

    exit_status = FAILED


class UsageError(Epm2ModError):
    """An argument is wrong: a malformed choice, a slot named twice, an unknown film."""

    exit_status = USAGE


class NotFoundError(Epm2ModError):
    """Nothing was found, or a file is not one that the package knows."""

    exit_status = NOT_FOUND


class CheckError(Epm2ModError):
    """A check failed: a checksum, a read-back, the camera model, an untested build."""

    exit_status = CHECK_FAILED


class UnavailableError(Epm2ModError):
    """The environment cannot do the work: no network, no checkout, a card that cannot take the files."""

    exit_status = ENVIRONMENT


class RepositoryError(UnavailableError):
    """The command needs a checkout of the repository, and there is none."""


class CardError(UnavailableError):
    """The SD card is not a camera card, cannot be written, is full, or cannot be ejected."""


class FileError(Epm2ModError):
    """A file cannot be read or written (missing, no permission, disk full)."""


class ContainerError(Epm2ModError):
    """The data is not a firmware container that this package can read or write."""

    exit_status = NOT_FOUND


class SpecError(Epm2ModError):
    """A patch spec is malformed or does not fit the firmware it is applied to."""


class StockError(Epm2ModError):
    """The stock firmware is missing, is the wrong file, or cannot be downloaded."""

    exit_status = CHECK_FAILED


class StockMissingError(StockError):
    """The stock firmware has not been downloaded yet."""

    exit_status = NOT_FOUND


class DownloadError(StockError):
    """The stock firmware cannot be downloaded (no network, or the maker's server fails)."""

    exit_status = ENVIRONMENT


class BuildError(Epm2ModError):
    """A build cannot be made, written or recorded.

    This covers a malformed build description or film list, a fit file that
    cannot be used, a failed free-space check, an SD card that cannot take the
    firmware, and a README whose generated parts cannot be found.
    """


class BuildCheckError(BuildError):
    """A build is not the one it should be: another sha256, or no camera test where one is needed."""

    exit_status = CHECK_FAILED


class LogError(Epm2ModError):
    """A camera log file or the event dictionary cannot be decoded."""


class LookFileError(Epm2ModError):
    """A look file for the SD card, or a look in it, is not valid."""
