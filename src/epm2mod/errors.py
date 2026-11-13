"""Exception types of the package.

Every error that a user can cause or meet (a wrong file, a failed download, a
spec that does not fit the firmware) is an ``Epm2ModError``. The command-line
interface prints its message and exits with status 1. Other exceptions are
programming errors and are not caught.
"""


class Epm2ModError(Exception):
    """Base class of the errors that the package reports to the user."""


class ContainerError(Epm2ModError):
    """The data is not a firmware container that this package can read or write."""


class SpecError(Epm2ModError):
    """A patch spec is malformed or does not fit the firmware it is applied to."""


class StockError(Epm2ModError):
    """The stock firmware is missing, is the wrong file, or cannot be downloaded."""


class BuildError(Epm2ModError):
    """A build description is malformed, or a build did not give the expected result."""
