"""Paths and images for the emulator tools. Python standard library only.

    OM_EMU_DIR    the om-emu checkout: the fork with the E-PM2's boot lab. Default: the submodule
                  emulator/om-emu (uv run epm2mod init initialises it).
    OM_EMU_NODE   a Node executable. Default: the Node of the version in .nvmrc, from PATH or nvm
                  (tools/node.sh; uv run epm2mod init installs it).
    EMU_IMAGES    where unpacked images go. Default: build/emu (ignored by git).

An IMAGE argument of the tools is one of:
    stock                the stock firmware, firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN
    data/builds/NAME.json     a build description; its image is build/NAME.BIN (made by `epm2mod make NAME`)
    PATH.BIN             a firmware file
    FOLDER               a folder that `tools/oetool.py unpack` made (it has manifest.json)
No firmware is in the repository: the tools unpack an image into EMU_IMAGES/NAME-SHA8/ when needed.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOT = os.path.join(REPO, "emulator", "boot")
STOCK_BIN = os.path.join(REPO, "firmware", "stock", "E-PM2", "OLY_E_101_1600_0000_0000.BIN")
class EmuSetupError(Exception):
    """The emulator cannot run: no working tree, no Node, no image. The text says what to do."""


def om_emu_dir():
    """Return the om-emu checkout: OM_EMU_DIR, else the submodule emulator/om-emu."""
    env = os.environ.get("OM_EMU_DIR")
    if env:
        return env
    return os.path.join(REPO, "emulator", "om-emu")


def require_om_emu():
    """Return om_emu_dir(), or raise EmuSetupError when there is no om-emu with the boot lab at that place."""
    d = om_emu_dir()
    if not os.path.exists(os.path.join(d, "emu", "bin", "boot.mjs")):
        raise EmuSetupError(f"no om-emu with the boot lab at {d}: run uv run epm2mod init (or set OM_EMU_DIR)")
    return d


def node():
    """Return the Node executable of the version in .nvmrc (tools/node.sh finds it), or raise EmuSetupError.
    OM_EMU_NODE names another one."""
    env = os.environ.get("OM_EMU_NODE")
    if env:
        return env
    found = subprocess.run([os.path.join(REPO, "tools", "node.sh"), "node", "-p", "process.execPath"], capture_output=True, text=True)
    if found.returncode != 0:
        raise EmuSetupError((found.stderr.strip() or "tools/node.sh failed") + " (or set OM_EMU_NODE)")
    return found.stdout.strip()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def image_bin(image):
    """Return (name, path of the .BIN) for an IMAGE argument that names a firmware file."""
    if image == "stock":
        path, name = STOCK_BIN, "stock"
    elif image.endswith(".json"):
        with open(image) as f:
            desc = json.load(f)
        name = os.path.splitext(os.path.basename(image))[0]
        path = os.path.join(REPO, "build", name + ".BIN")
        if not os.path.exists(path):
            raise EmuSetupError(f"{image}: its image {os.path.relpath(path, REPO)} does not exist (make it with `epm2mod make {name}`)")
        want = desc.get("sha256")
        if want and sha256(path) != want:
            raise EmuSetupError(f"{image}: {os.path.relpath(path, REPO)} does not have the sha256 the description gives (make the build again)")
    else:
        path, name = image, os.path.splitext(os.path.basename(image))[0]
    if not os.path.isfile(path):
        raise EmuSetupError(f"no firmware file at {path}")
    return name, path


def blocks(image):
    """Return the folder of unpacked blocks for an IMAGE argument. Unpack the firmware file when needed."""
    if os.path.isdir(image):
        if not os.path.exists(os.path.join(image, "manifest.json")):
            raise EmuSetupError(f"{image}: a folder, but it has no manifest.json (not made by tools/oetool.py unpack)")
        return image
    name, path = image_bin(image)
    root = os.environ.get("EMU_IMAGES") or os.path.join(REPO, "build", "emu")
    out = os.path.join(root, f"{name}-{sha256(path)[:8]}")
    if not os.path.exists(os.path.join(out, "manifest.json")):
        os.makedirs(root, exist_ok=True)
        tmp = f"{out}.tmp{os.getpid()}"
        r = subprocess.run([sys.executable, os.path.join(REPO, "tools", "oetool.py"), "unpack", path, tmp], capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(os.path.join(tmp, "manifest.json")):
            shutil.rmtree(tmp, ignore_errors=True)
            raise EmuSetupError(f"cannot unpack {path}: {(r.stderr or r.stdout).strip()[-300:]}")
        try:
            os.rename(tmp, out)
        except OSError:  # another process unpacked the same image in the meantime
            shutil.rmtree(tmp, ignore_errors=True)
    return out


def tool_command(tool, args=()):
    """Return the command list that runs emulator/boot/TOOL (a .mjs file) with Node."""
    script = tool if os.path.isabs(tool) else os.path.join(BOOT, tool)
    if not os.path.exists(script):
        raise EmuSetupError(f"no tool {script}")
    return [node(), script, *args]


def tool_env(image, extra=None):
    """Return the environment for a tool run on IMAGE: BLOCKS, EMU_BIN (the .BIN, when IMAGE names one), OM_EMU_DIR and
    EPM2_REPO are set."""
    env = dict(os.environ)
    env["BLOCKS"] = blocks(image)
    if not os.path.isdir(image):
        env["EMU_BIN"] = os.path.abspath(image_bin(image)[1])
    env["OM_EMU_DIR"] = require_om_emu()
    env.setdefault("EPM2_REPO", REPO)
    if extra:
        env.update(extra)
    return env


def run_tool(tool, image, args=(), extra_env=None, timeout=900):
    """Run a boot tool on IMAGE and return the CompletedProcess (stdout and stderr captured as text)."""
    return subprocess.run(tool_command(tool, args), env=tool_env(image, extra_env), capture_output=True, text=True, timeout=timeout)
