"""Set up a checkout (``epm2mod init``): what the build checks and the analysis tools need.

Everything goes inside the checkout, but a Node version through nvm. Safe to
run again: a step whose result is present is not done again.

1. The MN103 disassembler, assembler and linker: GNU binutils, built from the
   project's binutils source (a git submodule) into its toolchain folder.
   Needs gcc, make, m4, bison and flex; on Debian and Ubuntu a missing bison or
   flex is fetched without root.
2. Node of the project's version, for the emulator and the web apps: the
   project's node tool finds it on PATH or in nvm, and installs it with nvm.
3. The emulator: a git submodule, at the commit that the checkout pins.
4. Olympus's firmware of the pinned build: downloaded from Olympus, never
   stored in the repository.
5. The firmware map, for the free-space check (1 minute, 470 MB).
6. The commit hooks of the checkout.

``check`` reports the same items and changes nothing. It also says if the web
apps' packages are installed, which is not a step of this command.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from . import stock
from .errors import Epm2ModError, UnavailableError
from .fileio import Log
from .paths import RepoPaths

#: The folders of the binutils source that objdump, as and ld need (it also holds gdb and the simulators).
_BINUTILS_FOLDERS = (
    "bfd binutils gas ld opcodes include libiberty libsframe libctf zlib config cpu etc "
    "intl texinfo"
).split()
_CONFIGURE = (
    "--target=mn10300-elf --disable-nls --disable-werror --disable-gdb "
    "--disable-gdbserver --disable-sim --disable-gprofng --disable-gold"
).split()
#: The environment variables that replace a pinned tool (the scripts that read them refuse them when CI is set).
OVERRIDES = ("EPM2_BINUTILS", "OM_EMU_DIR", "OM_EMU_NODE")
#: The file of the emulator submodule that shows it is the fork with the E-PM2's boot lab.
_BOOT_LAB = ("emu", "bin", "boot.mjs")


def _run(
    command: Sequence[str | Path],
    cwd: Path,
    what: str,
    env: dict[str, str] | None = None,
) -> str:
    """Run a command and return its output, stripped.

    Raises:
        UnavailableError: if it cannot run or fails; the text holds the end of its output.
    """
    try:
        done = subprocess.run(
            [str(word) for word in command],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            errors="backslashreplace",
            check=False,
        )
    except OSError as error:
        raise UnavailableError(f"{what}: {error}") from None
    if done.returncode != 0:
        output = (done.stdout + done.stderr).strip()
        raise UnavailableError(f"{what} failed:\n{output[-2000:]}")
    return done.stdout.strip()


def _objdump(paths: RepoPaths) -> Path:
    """Return the path of the MN103 objdump in the toolchain folder."""
    return paths.location("toolchain") / "bin" / "mn10300-elf-objdump"


def _source_record(paths: RepoPaths) -> Path:
    """Return the file in the toolchain folder that names the source commit the binutils were built from."""
    return paths.location("toolchain") / "source-commit"


def _pinned_commit(paths: RepoPaths, key: str) -> str:
    """Return the commit that the checkout pins for the submodule at the location ``key``."""
    relative = paths.relative(paths.location(key))
    listed = _run(["git", "ls-files", "-s", relative], paths.root, "git ls-files")
    return listed.split()[1] if listed else ""


def _build_binutils(paths: RepoPaths) -> None:
    """Build the MN103 binutils from the submodule into the toolchain folder."""
    for tool in ("gcc", "make", "m4"):
        if shutil.which(tool) is None:
            raise UnavailableError(f"{tool} is needed to build binutils: install it")
    prefix = paths.location("toolchain")
    env = dict(os.environ)
    if shutil.which("bison") is None or shutil.which("flex") is None:
        # No bison or flex on this computer. Without root: fetch the two packages and unpack them.
        deps = prefix.parent / "hostdeps"
        if not (deps / "usr" / "bin" / "bison").exists():
            if shutil.which("apt-get") is None:
                raise UnavailableError(
                    "bison and flex are needed to build binutils: install them"
                )
            (deps / "debs").mkdir(parents=True, exist_ok=True)
            _run(
                ["apt-get", "download", "bison", "flex"],
                deps / "debs",
                "the download of bison and flex",
            )
            for package in sorted((deps / "debs").glob("*.deb")):
                _run(["dpkg", "-x", package, deps], deps, "dpkg")
        env["PATH"] = f"{deps / 'usr' / 'bin'}{os.pathsep}{env['PATH']}"
        env["BISON_PKGDATADIR"] = str(deps / "usr" / "share" / "bison")
    source = paths.location("binutils_source")
    relative = paths.relative(source)
    _run(
        ["git", "submodule", "update", "--init", "--depth", "1", relative],
        paths.root,
        "git submodule update",
    )
    _run(
        ["git", "sparse-checkout", "set", "--cone", *_BINUTILS_FOLDERS],
        source,
        "git sparse-checkout",
    )
    work = prefix.parent / "toolchain-build"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    jobs = f"-j{os.cpu_count() or 2}"
    _run(
        [source / "configure", f"--prefix={prefix}", *_CONFIGURE],
        work,
        "configure",
        env,
    )
    _run(
        ["make", jobs, "MAKEINFO=true", "all-binutils", "all-gas", "all-ld"],
        work,
        "the build of binutils",
        env,
    )
    _run(
        ["make", "MAKEINFO=true", "install-binutils", "install-gas", "install-ld"],
        work,
        "the install of binutils",
        env,
    )
    shutil.rmtree(work, ignore_errors=True)
    built_from = _run(["git", "rev-parse", "HEAD"], source, "git rev-parse")
    _source_record(paths).write_text(built_from + "\n", encoding="utf-8")


def _node(paths: RepoPaths, install: bool = False) -> str:
    """Return the Node that the project's node tool finds; with ``install``, let it install one with nvm.

    Raises:
        UnavailableError: if there is none; the text names the version.
    """
    env = dict(os.environ, EPM2_NODE_INSTALL="1" if install else "")
    tool = paths.location("node_tool")
    return _run([tool, "node", "-p", "process.execPath"], paths.root, "Node", env)


def _emulator(paths: RepoPaths, update: bool) -> str:
    """Return the emulator's commit; with ``update``, initialise the submodule first.

    Raises:
        UnavailableError: if the submodule is absent or is not at the commit that the checkout pins.
    """
    folder = paths.location("emulator")
    relative = paths.relative(folder)
    if update and not folder.joinpath(*_BOOT_LAB).exists():
        _run(["git", "submodule", "sync", "-q", relative], paths.root, "git submodule")
        _run(
            ["git", "submodule", "update", "--init", relative],
            paths.root,
            "git submodule update",
        )
    if not folder.joinpath(*_BOOT_LAB).exists():
        raise UnavailableError(f"{relative} is not initialised, or has no boot lab")
    want = _pinned_commit(paths, "emulator")
    have = _run(["git", "rev-parse", "HEAD"], folder, "git rev-parse")
    if want != have:
        raise UnavailableError(
            f"{relative} is at {have}, the checkout pins {want}: "
            f"git submodule update --init {relative}"
        )
    changed = _run(["git", "status", "--porcelain"], folder, "git status")
    if changed:
        raise UnavailableError(
            f"{relative} has changes that are not in its commit "
            f"({changed.splitlines()[0].strip()}, ...): undo them"
        )
    return have


def init(paths: RepoPaths, check: bool, log: Log) -> list[str]:
    """Set up the checkout, or with ``check`` only report. Return the names of the items that are missing.

    Raises:
        Epm2ModError: without ``check``, if a step fails.
    """
    for name in OVERRIDES:
        if os.environ.get("CI") and os.environ.get(name):
            raise UnavailableError(
                f"{name} is set ({os.environ[name]}): it replaces a pinned tool, and the hard "
                "checks use only what the checkout pins. Unset it"
            )
    pinned_stock = paths.pinned_build().stock_firmware
    firmware_map = paths.firmware_map
    hooks = paths.relative(paths.location("hooks"))

    def stock_present() -> str:
        """Say that the firmware file is there and has its sha256."""
        if not stock.stock_path(paths, pinned_stock).exists():
            raise UnavailableError("not downloaded")
        stock.read_stock(paths, pinned_stock)
        return "its sha256 is right"

    def objdump_present() -> str:
        """Return the version line of the built objdump."""
        if not _objdump(paths).exists():
            raise UnavailableError("not built")
        record = _source_record(paths)
        built_from = record.read_text().strip() if record.is_file() else "unknown"
        if built_from != _pinned_commit(paths, "binutils_source"):
            raise UnavailableError(
                f"built from the source commit {built_from}, not the one the checkout pins"
            )
        version = _run([_objdump(paths), "--version"], paths.root, "objdump")
        note = ""
        if os.environ.get("EPM2_BINUTILS"):
            note = "; but EPM2_BINUTILS is set, and the tools use that folder"
        return f"{version.splitlines()[0]}, source {built_from[:12]}{note}"

    def map_present() -> str:
        """Return the folder of the firmware map."""
        tool = paths.location("firmware_map_tool")
        try:
            _run([sys.executable, tool, "check"], paths.root, "the check of the map")
        except UnavailableError:
            raise UnavailableError("not made, or not complete") from None
        return paths.relative(firmware_map.parent)

    def hooks_present() -> str:
        """Say that git uses the hooks of the checkout."""
        try:
            now = _run(["git", "config", "core.hooksPath"], paths.root, "git config")
        except UnavailableError:
            now = ""
        if now != hooks:
            raise UnavailableError("off")
        return "on"

    def make_map() -> None:
        """Run the firmware map tool."""
        tool = paths.location("firmware_map_tool")
        _run([sys.executable, tool, "build"], paths.root, "the firmware map")

    steps: list[tuple[str, Callable[[], str], Callable[[], object]]] = [
        ("MN103 binutils", objdump_present, lambda: _build_binutils(paths)),
        ("Node", lambda: _node(paths), lambda: _node(paths, install=True)),
        (
            "the emulator",
            lambda: _emulator(paths, False),
            lambda: _emulator(paths, True),
        ),
        (
            "Olympus's firmware",
            stock_present,
            lambda: stock.fetch(paths, pinned_stock, log=log),
        ),
        ("the firmware map", map_present, make_map),
        (
            "the commit hooks",
            hooks_present,
            lambda: _run(
                ["git", "config", "core.hooksPath", hooks], paths.root, "git config"
            ),
        ),
    ]
    missing = []
    for name, present, make in steps:
        try:
            log(f"{name}: present ({present()})")
            continue
        except Epm2ModError as error:
            if check:
                log(f"{name}: MISSING ({str(error).splitlines()[0]})")
                missing.append(name)
                continue
        log(f"{name}: ...")
        make()
        log(f"{name}: done ({present()})")
    if check:
        web = paths.location("web")
        there = (web / "node_modules").is_dir()
        log(
            "the web apps' packages (only for work on the web apps): "
            + ("present" if there else f"absent; npm ci in {paths.relative(web)}")
        )
    return missing
