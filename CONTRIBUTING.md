# Contributing

How to go from a clone to a firmware build of your own that passes every check. The rules of the project are in
[docs/dev/conventions.md](docs/dev/conventions.md). The limits of the camera are in
[docs/dev/feasibility.md](docs/dev/feasibility.md).

## Set up

You need [uv](https://docs.astral.sh/uv/getting-started/installation/), git, gcc, make, m4, bison and flex, and
[nvm](https://github.com/nvm-sh/nvm) or Node of the version in `.nvmrc`. Linux or macOS. Keep 3 GB of disk free.

```sh
git clone https://github.com/cfu288/EPM2Mod.git && cd EPM2Mod
uv run epm2mod init           # the MN103 assembler, Node, the emulator, Olympus's firmware, the firmware map, the commit hooks
uv run epm2mod init --check   # changes nothing: says what is present and what is missing
```

`uv run epm2mod init` takes about 3 minutes. It puts everything inside the repository, but a Node version through nvm.
On Debian and Ubuntu it gets a missing bison or flex by itself.

## Check your clone

```sh
tools/ci.sh python   # what CI runs: format, types, tests, generators, the pinned build and each build you changed
tools/ci.sh web      # only for a change in web/
```

A fresh clone passes. A check that cannot run fails and names the command that makes what it needs.

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
   uv run epm2mod lint NAME
   ```

   `make` runs the free-space check, which holds the load-order check, and starts the result in the emulator. A
   build that fails, or that cannot be started in the emulator, is not written. `lint` prints what may be harmful
   and is not proven safe; read each warning, it does not fail. The rule behind the load-order warnings is in
   [docs/dev/load-order.md](docs/dev/load-order.md).

The free-space check keeps a ledger of the bytes that every spec in `data/specs/` uses. Two specs that change the
same byte fail with "overlaps ledgered spec", unless `tools/space-ledger/superseded.tsv` says that one replaces
the other.

## The camera test

The emulator has no sensor and no live view. A build that passes every check is a candidate. It becomes the pinned
build only after a flash on an E-PM2, with the result in [docs/camera-log/](docs/camera-log/README.md):
[conventions](docs/dev/conventions.md#making-firmware), steps 3 to 5. A pull request without a camera test says so.

## The web installer

See [web/README.md](web/README.md).
