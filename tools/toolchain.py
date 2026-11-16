"""Where the MN103 binutils are. Standard library only.

`tools/setup.sh` builds them from the submodule third_party/binutils-gdb into build/toolchain/.
Nothing is looked for in fixed places of a home folder. (Node for the emulator: tools/emu/emuenv.py.)

    EPM2_BINUTILS   folder with mn10300-elf-objdump, -as and -ld. Default: build/toolchain/bin, else PATH.
"""

import os
import shutil

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREFIX = "mn10300-elf-"
SETUP_HINT = "run tools/setup.sh"


class ToolchainError(Exception):
    """A program is missing. The text says what to do."""


def binutils_dir():
    """Return the folder that holds the MN103 binutils programs."""
    candidates = [os.environ.get("EPM2_BINUTILS"), os.path.join(REPO, "build", "toolchain", "bin")]
    on_path = shutil.which(PREFIX + "objdump")
    if on_path:
        candidates.append(os.path.dirname(on_path))
    for folder in candidates:
        if folder and os.path.exists(os.path.join(folder, PREFIX + "objdump")):
            return folder
    raise ToolchainError(f"the MN103 binutils are not built: {SETUP_HINT}")


def binutils(tool):
    """Return the path of one MN103 binutils program: "objdump", "as" or "ld"."""
    return os.path.join(binutils_dir(), PREFIX + tool)
