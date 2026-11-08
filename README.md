# epm2-tools

Custom firmware tooling for the Olympus PEN **E-PM2** (model 1010, TruePic VI, body firmware 1.6).

**Status (2026-11-08):** modified firmware flashes and runs on a real E-PM2 via the SD-card updater. See [docs/camera-log.md](docs/camera-log.md).

## Quick start

```bash
python3 tools/build.py patches/pixel-hacking.json      # -> build/pixel-hacking.BIN
python3 -m unittest discover -s tests                   # round-trip + reproducible builds
```

Flash `build/<name>.BIN` as `DCOLYMP/E1019999.BIN`, hold OK and power on. Full steps: [docs/flashing.md](docs/flashing.md).

## Layout

| Path | What |
|---|---|
| `tools/oetool.py` | OE container: `info`, `unpack`, `pack`, `patch` (recomputes checksums) |
| `tools/build.py` | applies JSON patch specs to a stock BIN → `build/` |
| `patches/` | one spec per mod, with a status and expected hash once camera-tested |
| `firmware/` | stock and reference BINs (git-ignored), `SHA256SUMS`, provenance |
| `docs/` | [flashing](docs/flashing.md), [camera log](docs/camera-log.md), [format](docs/firmware-format.md), [verification](docs/verification.md), [conventions](docs/conventions.md) |
| `experiments/` | dated ad-hoc work; promote results into tools/patches/docs |
| `tests/` | unittest suite |

## Patches

| Spec | Status |
|---|---|
| `pixel-hacking` | camera-tested, works (PoC: renames a menu label) |

## Background

Landscape research: `../reports/Olympus firmware modding landscape.md` and `../research_notes/Olympus firmware modding landscape/`.

Commits follow Conventional Commits. Run `git config core.hooksPath .githooks` once. See [docs/conventions.md](docs/conventions.md).
