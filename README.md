# EPM2Mod

![Olympus PEN E-PM2](docs/images/epm2.jpg)

Repository containing the current work for creating a custom firmware mod for the Olympus PEN **E-PM2**. The goal is to unlock or add new features to this camera. Currently, we've implemented replacing the default art filters with film simulations like Portra, Ektachrome, etc., enabled interval shooting (up to 240 shots), and added a level gauge.

| Feature | Guide | Status |
|---|---|---|
| Film looks | [docs/guide/film-looks.md](docs/guide/film-looks.md) | Tested on the camera |
| Interval shooting | [docs/guide/interval-shooting.md](docs/guide/interval-shooting.md) | Tested on the camera |
| Level gauge | [docs/guide/level-gauge.md](docs/guide/level-gauge.md) | Tested on the camera |
| Focus peaking | | In work |

**Install:** [docs/install.md](docs/install.md)

See below for an example of the film looks:

![Eight photos, each developed in the camera with stock Natural and the seven film looks](docs/images/film-sim-comparison.jpg)

Each row shows one RAW file. The camera developed the file with each look. The first column shows the standard Natural mode.
Full-resolution sheet: [docs/film-sim-comparison.pdf](docs/film-sim-comparison.pdf).

## For developers

- [docs/conventions.md](docs/conventions.md): layout, builds, tests
- [docs/feasibility.md](docs/feasibility.md): what is possible, the emulator
- [docs/todo.md](docs/todo.md): open work
- [docs/camera-log.md](docs/camera-log.md): every update done on a camera
- [builds/README.md](builds/README.md): the tested builds
- [AGENTS.md](AGENTS.md): rules for AI agents

## Licence

[MIT](LICENSE). The film look data is derived from
[spektrafilm](https://github.com/andreavolpato/spektrafilm) (CC BY-SA 4.0). The firmware and the
camera screens shown here belong to Olympus. Details: [NOTICE.md](NOTICE.md).
