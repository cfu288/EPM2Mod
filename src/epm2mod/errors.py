"""Exception types of the package.

Every error that a user can cause or meet (a wrong file, a failed download, a
spec that does not fit the firmware, a full disk) is an ``Epm2ModError``. The
command-line interface prints its message and exits with status 1. Any other
exception is a programming error; it is not caught and shows a traceback.
"""


class Epm2ModError(Exception):
    """Base class of the errors that the package reports to the user."""


class RepositoryError(Epm2ModError):
    """The command was not run inside a checkout of the repository."""


class FileError(Epm2ModError):
    """A file cannot be read or written (missing, no permission, disk full)."""


class ContainerError(Epm2ModError):
    """The data is not a firmware container that this package can read or write."""


class SpecError(Epm2ModError):
    """A patch spec is malformed or does not fit the firmware it is applied to."""


class StockError(Epm2ModError):
    """The stock firmware is missing, is the wrong file, or cannot be downloaded."""


class BuildError(Epm2ModError):
    """A build cannot be made, written or recorded.

    This covers a malformed build description or film list, a fit file that
    cannot be used, a failed free-space check, a result with the wrong SHA-256,
    an SD card that cannot take the firmware, and a README whose generated
    parts cannot be found.
    """


class LogError(Epm2ModError):
    """A camera log file or the event dictionary cannot be decoded."""
