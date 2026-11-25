"""Where the MN103 binutils are. Standard library only.

`uv run epm2mod init` builds them from the submodule third_party/binutils-gdb into build/toolchain/.
Nothing is looked for in fixed places of a home folder. (Node for the emulator: emulator/emuenv.py.)

    EPM2_BINUTILS   folder with mn10300-elf-objdump, -as and -ld. Default: build/toolchain/bin.

The checks decode firmware with this objdump, so its origin decides their results:
- a program of the same name on PATH is never used;
- the built binutils must come from the source commit that the repository pins (`epm2mod init` records it in
  build/toolchain/source-commit); another commit, or no record, is an error;
- with EPM2_BINUTILS set, each run says so on stderr, a folder without the programs is an error (there is no
  fall-back), and when the environment has CI (tools/ci.sh sets it) the override itself is an error.
"""

import os
import subprocess
import sys

DEFAULT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build", "toolchain", "bin")
SOURCE = "third_party/binutils-gdb"

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREFIX = "mn10300-elf-"
SETUP_HINT = "run uv run epm2mod init"


class ToolchainError(Exception):
    """A program is missing. The text says what to do."""


def binutils_dir():
    """Return the folder that holds the MN103 binutils programs."""
    folder = os.environ.get("EPM2_BINUTILS")
    if folder:
        if os.environ.get("CI"):
            raise ToolchainError(f"EPM2_BINUTILS is set ({folder}): the hard checks use only the binutils that `epm2mod init` builds. Unset it")
        print(f"note: EPM2_BINUTILS is set: the MN103 binutils are those of {folder}, not the ones `epm2mod init` builds", file=sys.stderr)
        if not os.path.exists(os.path.join(folder, PREFIX + "objdump")):
            raise ToolchainError(f"EPM2_BINUTILS: no MN103 binutils in {folder}")
        return folder
    folder = os.path.join(REPO, "build", "toolchain", "bin")
    if not os.path.exists(os.path.join(folder, PREFIX + "objdump")):
        raise ToolchainError(f"no MN103 binutils in {folder}: {SETUP_HINT}")
    built, pinned = source_commit(), pinned_commit(SOURCE)
    if built != pinned:
        raise ToolchainError(f"the MN103 binutils in {folder} are built from the source commit {built or 'unknown'}, "
                             f"and the repository pins {pinned or 'none'}: {SETUP_HINT}")
    return folder


def source_commit():
    """Return the source commit that `epm2mod init` recorded for the built binutils, or ""."""
    try:
        with open(os.path.join(REPO, "build", "toolchain", "source-commit"), encoding="utf-8") as record:
            return record.read().strip()
    except OSError:
        return ""


def pinned_commit(submodule):
    """Return the commit that the repository pins for a submodule path, or "" when git cannot say."""
    done = subprocess.run(["git", "ls-files", "-s", submodule], cwd=REPO, capture_output=True, text=True)
    fields = done.stdout.split()
    return fields[1] if done.returncode == 0 and len(fields) > 1 else ""


def binutils(tool):
    """Return the path of one MN103 binutils program: "objdump", "as" or "ld"."""
    return os.path.join(binutils_dir(), PREFIX + tool)
