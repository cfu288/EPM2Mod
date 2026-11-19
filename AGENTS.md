# Working rules for AI agents on this repository

These rules are for any coding agent and for people who
direct one.

Read [docs/feasibility.md](docs/feasibility.md) first. It lists the real limits of the camera and
the resources the firmware has, with evidence.

The open work is in [docs/todo.md](docs/todo.md). Add an item there when the owner asks for one,
and remove an item when it is done.

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
5. **Write test instructions that the owner can follow without a guess.** The owner reads them with
   the camera in hand. Before you give a menu path:
   - look it up in the camera manual or in the firmware's own menu text. Do not write it from
     memory;
   - name each screen as the camera shows it, in order, one step per line (for example: MENU →
     gears tab → group **D** → **Info Settings** → **LV-Info** → **Level Gauge** → OK);
   - say what is on the screen before the change and what is new;
   - say how to switch on anything the path needs (for example Setup Menu → Menu Display for the
     Custom Menu);
   - give the expected result and what each different result means.

   On 2026-11-14 an agent wrote "Custom Menu → D (Disp/PC) → Info Settings" from memory. The owner
   could not match "Disp/PC" to the screen and had to ask three times.
6. **Keep what the user reads short, and show it.** This covers the README, the guides and your own
   messages to the owner. Say each thing once. A menu path is one line (MENU → Custom Menu → D →
   Info Settings → LV-Info → Level Gauge), with a screenshot from the emulator beside it. No
   background, no history and no "how it works" in user instructions: link to the notes for that.
   On 2026-11-14 the owner said of the README: "Very verbose instructions with no visible
   screenshots. You could cut user facing instructions and docs by 70% and lose nothing."
7. **When a feature passes its camera test, update the user documents in the same piece of work:**
   pin the build (`uv run epm2mod pin ...`), run `uv run epm2mod generate`, write or update the
   feature's guide in `docs/guide/` (how to switch it on and use it, emulator screenshots, limits),
   add one line with a link to the feature list in `README.md`, and update the camera log and
   `docs/feasibility.md`. The root `README.md` is an index with the short install steps: it does not explain how to use a
   feature. A feature that works but has no guide is not finished.
8. **Keep the real safety steps:** make firmware only with `epm2mod make` or `epm2mod install` from a build
   description, log each flash in `docs/camera-log.md` before and after, keep the stock file at
   hand, change one thing per flash.
9. **Do not polish while a feature question is open.** Fit accuracy and tooling reviews come after
   the feature works on the camera.
10. **Look things up.** Read the firmware, the notes in `experiments/` and other projects (sweep
   GitHub with `gh search`) before you answer from memory.
11. **Writing:** short plain sentences, define terms. In files, use placeholders for machine paths and
   hosts (`/path/to/...`, `USER@HOST`, `/tmp/scratch`). The pre-commit hook refuses real ones.
12. **Code:** `src/epm2mod/` is production code (black, `mypy --strict`, docstrings, tests).
   `experiments/` is research code and may be rough. See [docs/conventions.md](docs/conventions.md).
13. **Before you offer a build that adds or moves a hook, check where its code is loaded.** A hook
    in the kernel or in segment 1 must jump only to code in the kernel or segment 1 (see
    `docs/feasibility.md`). Run `tools/emu/hookcheck.py`, `tools/emu/boot-test builds/NAME.json` and
    `tools/emu/update-path-test builds/NAME.json` on the build (exit status 0 = pass), and for a menu
    change the emulator's screenshot comparison (`docs/feasibility.md`, "The emulator"). A build that
    can crash at start-up is the one kind of failure with no known way back.
14. **Commit and push your work.** After a commit, push to `origin main` without asking the owner.
    Do not force-push and do not rewrite history unless the owner tells you to.
15. Another session may work in this repository at the same time. Do not change or delete files
    that you did not make without a reason, and say so when you change a shared file.
