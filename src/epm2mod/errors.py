"""Exception types of the package.

Every error that a user can cause or meet (a wrong file, a failed download, a
spec that does not fit the firmware, a full disk) is an ``Epm2ModError``. The
command-line interface prints its message and exits with the error's
``exit_status``; with ``--json`` it also prints the error's ``code`` and
``override``. Any other exception is a programming error: the command line
exits with ``INTERNAL``.

Exit statuses (the command line's table): 1 a check found a difference or a
problem, 2 wrong usage, 3 not found or not recognised, 4 refused (a named flag
overrides it), 5 not safe (a checksum, a read-back or a download sha256
differs, firmware for another model), 6 the environment (no network, no
checkout, a card that is not a camera card, not writable or full), 7 failed (an
input is wrong: a build description, a patch spec, a fit, a file that does not
fit), 70 an internal error, 130 interrupted.
"""

#: The exit status of each kind of failure.
DIFFERS, USAGE, NOT_FOUND, REFUSED, NOT_SAFE, ENVIRONMENT, FAILED = 1, 2, 3, 4, 5, 6, 7
#: The exit status of an uncaught exception, and of an interrupted run.
INTERNAL, INTERRUPTED = 70, 130


class Epm2ModError(Exception):
    """Base class of the errors that the package reports to the user.

    Attributes:
        exit_status: the exit status of the command line.
        code: a stable name of the kind of error, for ``--json``.
        override: the flag that overrides a refusal, or None.
    """

    exit_status = FAILED
    code = "failed"
    override: str | None = None


class UsageError(Epm2ModError):
    """An argument is wrong: a malformed choice, a slot named twice, an unknown film."""

    exit_status = USAGE
    code = "usage"


class NotFoundError(Epm2ModError):
    """Nothing was found, or a file is not one that the package knows."""

    exit_status = NOT_FOUND
    code = "not_found"


class RefusedError(Epm2ModError):
    """A refusal that a named flag overrides (``override``)."""

    exit_status = REFUSED
    code = "refused"

    def __init__(self, message: str, override: str) -> None:
        """Keep the message and the flag that overrides the refusal."""
        super().__init__(message)
        self.override = override


class CheckError(Epm2ModError):
    """Not safe: a checksum or a read-back differs, or the firmware is for another camera model."""

    exit_status = NOT_SAFE
    code = "check_failed"


class UnavailableError(Epm2ModError):
    """The environment cannot do the work: no network, no checkout, a card that cannot take the files."""

    exit_status = ENVIRONMENT
    code = "environment"


class RepositoryError(UnavailableError):
    """The command needs a checkout of the repository, and there is none."""

    code = "no_checkout"


class CardError(UnavailableError):
    """The SD card is not a camera card, cannot be written, is full, or cannot be ejected."""

    code = "card"


class FileError(Epm2ModError):
    """A file cannot be read or written (missing, no permission, disk full)."""

    code = "file"


class ContainerError(Epm2ModError):
    """The data is not a firmware container that this package can read or write."""

    exit_status = NOT_FOUND
    code = "not_firmware"


class SpecError(Epm2ModError):
    """A patch spec is malformed or does not fit the firmware it is applied to."""

    code = "spec"


class StockError(Epm2ModError):
    """The stock firmware is missing, is the wrong file, or cannot be downloaded."""

    exit_status = NOT_SAFE
    code = "stock_differs"


class StockMissingError(StockError):
    """The stock firmware has not been downloaded yet."""

    exit_status = NOT_FOUND
    code = "stock_missing"


class DownloadError(StockError):
    """The stock firmware cannot be downloaded (no network, or the maker's server fails)."""

    exit_status = ENVIRONMENT
    code = "download"


class BuildError(Epm2ModError):
    """A build cannot be made, written or recorded.

    This covers a malformed build description or film list, a fit file that
    cannot be used, a failed free-space check, an SD card that cannot take the
    firmware, and a README whose generated parts cannot be found.
    """

    code = "build"


class BuildCheckError(BuildError):
    """A build is not the one it should be: its sha256 is not the recorded or stated one."""

    exit_status = NOT_SAFE
    code = "sha256_differs"


class LogError(Epm2ModError):
    """A camera log file or the event dictionary cannot be decoded."""

    code = "log"


class LookFileError(Epm2ModError):
    """A look file for the SD card, or a look in it, is not valid."""

    code = "film_file"
