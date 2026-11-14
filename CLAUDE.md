# Working rules for AI-assisted sessions on this repository

Read [docs/feasibility.md](docs/feasibility.md) first. It lists the real limits of the camera and
the resources the firmware has, with evidence.

1. **Do not be more careful than the evidence requires.** This project lost about a week because an
   agent changed only data tables and described its own caution as a limit of the camera. The owner
   never asked for that. New code, new menu entries, hooks and files on the card are all in scope.
2. **A limit counts only if a measurement, a datasheet or the firmware proves it.** Label every claim
   as verified, inferred or unknown. For an unknown, propose the smallest camera probe that settles
   it.
3. **A bad flash has been recoverable every time** (a normal card update). Do not treat a possible
   freeze as a reason to avoid an attempt. The one open case is a boot loop, which has no record on
   this body: a deliberate boot-loop test needs the owner's agreement.
4. **The owner flashes the camera. You do not.** For each build give: the build description, the
   sha256, what to check on the camera, and the commands to copy the file to the card.
5. **Keep the real safety steps:** make firmware only with `tools/make_firmware.py` from a build
   description, log each flash in `docs/camera-log.md` before and after, keep the stock file at
   hand, change one thing per flash.
6. **Do not polish while a feature question is open.** Fit accuracy and tooling reviews come after
   the feature works on the camera.
7. **Look things up.** Read the firmware, the notes in `experiments/` and other projects (sweep
   GitHub with `gh search`) before you answer from memory.
8. **Writing:** short plain sentences, define terms. In files, use placeholders for machine paths and
   hosts (`/path/to/...`, `USER@HOST`, `/tmp/scratch`). The pre-commit hook refuses real ones.
9. **Code:** `src/epm2mod/` is production code (black, `mypy --strict`, docstrings, tests).
   `experiments/` is research code and may be rough. See [docs/conventions.md](docs/conventions.md).
10. Another session may work in this repository at the same time. Do not change or delete files
    that you did not make without a reason, and say so when you change a shared file.
