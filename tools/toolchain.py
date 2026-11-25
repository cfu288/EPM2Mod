"""Where the MN103 binutils are. Standard library only.

`uv run epm2mod init` builds them from the submodule third_party/binutils-gdb into build/toolchain/.
Nothing is looked for in fixed places of a home folder. (Node for the emulator: emulator/emuenv.py.)

    EPM2_BINUTILS   folder with mn10300-elf-objdump, -as and -ld. Default: build/toolchain/bin.

The checks decode firmware with this objdump, so its origin decides their results. A program of the same name on
PATH is never used. With EPM2_BINUTILS set, each run says so on stderr.
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREFIX = "mn10300-elf-"
SETUP_HINT = "run uv run epm2mod init"


class ToolchainError(Exception):
    """A program is missing. The text says what to do."""


def binutils_dir():
    """Return the folder that holds the MN103 binutils programs."""
    folder = os.environ.get("EPM2_BINUTILS")
    if folder:
        print(f"note: EPM2_BINUTILS is set: the MN103 binutils are those of {folder}, not the ones `epm2mod init` builds", file=sys.stderr)
    else:
        folder = os.path.join(REPO, "build", "toolchain", "bin")
    if os.path.exists(os.path.join(folder, PREFIX + "objdump")):
        return folder
    raise ToolchainError(f"no MN103 binutils in {folder}: {SETUP_HINT}")


def binutils(tool):
    """Return the path of one MN103 binutils program: "objdump", "as" or "ld"."""
    return os.path.join(binutils_dir(), PREFIX + tool)
