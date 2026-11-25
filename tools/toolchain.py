"""Where the MN103 binutils are. Standard library only.

`uv run epm2mod init` builds them from the submodule third_party/binutils-gdb into build/toolchain/.
Nothing is looked for in fixed places of a home folder. (Node for the emulator: emulator/emuenv.py.)

    EPM2_BINUTILS   folder with mn10300-elf-objdump, -as and -ld. Default: build/toolchain/bin.
"""

import os

DEFAULT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build", "toolchain", "bin")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREFIX = "mn10300-elf-"
SETUP_HINT = "run uv run epm2mod init"


class ToolchainError(Exception):
    """A program is missing. The text says what to do."""


def binutils_dir():
    """Return the folder that holds the MN103 binutils programs."""
    folder = os.environ.get("EPM2_BINUTILS") or DEFAULT_DIR
    if not os.path.exists(os.path.join(folder, PREFIX + "objdump")):
        raise ToolchainError(f"no MN103 binutils in {folder}: {SETUP_HINT}")
    return folder


def binutils(tool):
    """Return the path of one MN103 binutils program: "objdump", "as" or "ld"."""
    return os.path.join(binutils_dir(), PREFIX + tool)
