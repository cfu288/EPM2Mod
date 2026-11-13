"""Build and check custom firmware for the Olympus PEN E-PM2.

The package is the production side of this repository. It reads the maker's
firmware container, applies patch specs to it, and makes the firmware builds
that are described in ``builds/``. The research code under ``experiments/``
is not part of it.

Modules:
    errors: the exception types that the package raises.
    paths: where the repository's files are.
    hashing: SHA-256 helpers.
    container: the "OE" firmware container (parse, serialize, checksums).
    spec: patch specs and how they are applied.
    stock: the stock firmware (download, check).
    builds: build descriptions and the pinned build.
    pipeline: the steps that make a build.
    readme: the generated parts of ``README.md``.
    looks: the generator of the film-look patch specs (needs numpy).
    cli: the ``epm2mod`` command.
"""

__version__ = "0.1.0"
