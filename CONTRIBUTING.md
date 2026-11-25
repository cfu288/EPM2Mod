# Contributing

How to go from a clone to a firmware build of your own that passes every check. The rules of the project are in
[docs/dev/conventions.md](docs/dev/conventions.md). The limits of the camera are in
[docs/dev/feasibility.md](docs/dev/feasibility.md).

## Set up

You need [uv](https://docs.astral.sh/uv/getting-started/installation/), git, gcc, make, m4, bison and flex, and
[nvm](https://github.com/nvm-sh/nvm) or Node of the version in `.nvmrc`. Linux or macOS. Keep 3 GB of disk free.

```sh
git clone https://github.com/cfu288/EPM2Mod.git && cd EPM2Mod
tools/setup.sh           # the MN103 assembler, Node, the emulator, Olympus's firmware, the firmware map, the commit hooks
tools/setup.sh --check   # says what is present, and the command for each thing that is missing
```

`tools/setup.sh` takes about 3 minutes. It puts everything inside the repository, but a Node version through nvm.
On Debian and Ubuntu it gets a missing bison or flex by itself.

## Check your clone

These are the commands that CI runs. A fresh clone passes each of them.

```sh
uv run python -m unittest discover -s cli/tests
uv run --directory cli mypy
uv run epm2mod generate --check
gen/run.sh --check
```

## Add a patch

A feature is one or more patch specs in `data/specs/` and a build description in `data/builds/` that lists them.

1. **Find the code.** `uv run python tools/disasm.py ADDRESS` disassembles the firmware.
   [docs/reference/firmware-map.md](docs/reference/firmware-map.md) says where things are. A spec's `offset` is the
   address minus 0x7E421020.
2. **Write the spec.** The format is in the first lines of
   [cli/src/epm2mod/spec.py](cli/src/epm2mod/spec.py). Each operation gives the bytes that it expects and the new
   bytes. For new code, [docs/reference/code-space-map.md](docs/reference/code-space-map.md) lists the free space.
   A spec with more than a few bytes gets a generator in [gen/](gen/README.md).
3. **Write the build description.** `uv run epm2mod builds` names the pinned build. Copy its description to `data/builds/NAME.json`, remove
   `sha256` and `camera_tested`, and add your spec at the end of `specs`.
4. **Make it and check it.**

   ```sh
   uv run epm2mod make NAME
   uv run python tools/checks.py data/builds/NAME.json
   uv run python emulator/hookcheck.py data/builds/NAME.json
   ```

   `make` runs the free-space check and starts the result in the emulator. A build that fails is not written.

The free-space check keeps a ledger of the bytes that every spec in `data/specs/` uses. Two specs that change the
same byte fail with "overlaps ledgered spec", unless `tools/space-ledger/superseded.tsv` says that one replaces
the other.

## The camera test

The emulator has no sensor and no live view. A build that passes every check is a candidate. It becomes the pinned
build only after a flash on an E-PM2, with the result in [docs/camera-log/](docs/camera-log/README.md):
[conventions](docs/dev/conventions.md#making-firmware), steps 3 to 5. A pull request without a camera test says so.

## The web installer

See [web/README.md](web/README.md).
