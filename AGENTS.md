# Working Rules for AI Agents on This Repository

Read [docs/dev/feasibility.md](docs/dev/feasibility.md) first: the real limits of the camera and of the firmware's resources,
with evidence. Open work is in [TODO.md](TODO.md): add an item when the owner asks for one, delete it when
it is done.

## Evidence

1. **Do not be more careful than the evidence requires.** New code, menu entries, hooks and files on the card are in
   scope. Do not describe your own caution as a limit of the camera.
2. **A limit counts only if a measurement, a datasheet or the firmware proves it.** Label each claim verified,
   inferred or unknown. For an unknown, propose the smallest camera probe that settles it.
3. **Tell users only what is measured.** A feature or behaviour that is designed but not camera-tested is not stated
   as fact in user documents.
4. **Look things up before you answer from memory:** the firmware, the notes in `experiments/`, and other projects
   (`gh search`).

## The camera

5. **A bad flash has been recoverable every time** (a normal card update). A possible freeze is not a reason to avoid
   an attempt. A deliberate boot-loop test needs the owner's agreement.
6. **The owner flashes the camera, you do not.** For each build give the build description, its sha256, the command
   that writes it to the card, and what to check on the camera.
7. **Before you offer a build that adds or moves a hook,** run `emulator/hookcheck.py`, `emulator/boot-test` and
   `emulator/update-path-test` on it (exit status 0 = pass), and for a menu change the emulator's screenshot
   comparison. A build that can crash at start-up is the one failure with no known way back
   ([feasibility](docs/dev/feasibility.md), "The emulator").
8. **Safety steps:** make firmware only from a build description with the CLI, log each flash in
   `docs/camera-log/` before and after, keep the stock file at hand, change one thing per flash.
9. **Test instructions the owner can follow with the camera in hand:** take each menu path from the camera manual or
   the firmware's menu text, not from memory. Name each screen as the camera shows it, one step per arrow. Say how to
   switch on anything the path needs, the expected result, and what each other result means.

## What users read

10. **Short, and shown.** Say each thing once. No filler, caveats, footnotes or subtext. A sentence that adds nothing
    goes. No background or history in user instructions: link to the notes. A menu path is one line, with an emulator
    screenshot beside it.
11. **Say why, not only what.** A feature line says what it does for the photographer.
12. **Words:** "film simulations" (never "films", "looks" or "film looks" for them; "Load Looks", file names and
    command names are exempt). Use the camera's names for menus and settings.
13. **No support channel.** The firmware is unofficial and used at the user's own risk: do not point users to the
    owner, issues or bug reports.
14. **Write for the reader's layer.** Wording follows what is true for the tool the reader uses (the installer page,
    the command line, the site), not where the data is stored.
15. **When a feature passes its camera test,** in the same piece of work: pin the build, regenerate the generated
    documents, write or update its guide in `docs/guide/` (how to switch it on and use it, screenshots, limits), add
    one linked line to the feature list in `README.md`, and update the camera log and `docs/dev/feasibility.md`. The root
    `README.md` is an index with the short install steps. A feature without a guide is not finished.
16. **Documents match the current state.** Read each changed document as a first-time user, against the current
    build and commands. A generated block that is "up to date" only proves the generator ran: read its content.

## Design and changes

17. **A design review challenges every choice,** including choices carried over from the old version and every
    default. Compare each interface with mainstream tools. A default must have an owner: the component that
    recommends something stores it.
18. **Before you apply a decision, state its scope** (which component, which reader) and check each affected place
    against it. Do not apply a decision as a word replacement.
19. **Do what was asked, and no more.** Settle details by common practice without asking. Bring anything that adds
    scope or changes a decision to the owner first. A renamed command or flag is changed everywhere in the same
    change, with no alias.
20. **Dated notes are records.** Do not edit `experiments/*/NOTES.md`, design notes or `docs/camera-log/` to match
    later changes. Where a path has moved since, [docs/dev/moved-paths.md](docs/dev/moved-paths.md) gives the new one.
21. **Do not polish while a feature question is open.** Fit accuracy and tooling reviews come after the feature works
    on the camera.

## Code and commits

22. `cli/src/epm2mod/` is production code (black, `mypy --strict`, docstrings, tests); `experiments/` is research code. See
    [docs/dev/conventions.md](docs/dev/conventions.md). The command-line reference is [docs/reference/cli.md](docs/reference/cli.md).
23. **Writing in files:** short plain sentences, terms defined. Use placeholders for machine paths and hosts
    (`/path/to/...`, `USER@HOST`). The pre-commit hook refuses real ones.
24. **Commit and push your work** to `origin main` without asking. Do not force-push or rewrite history unless the
    owner says so.
25. **Another session may work here at the same time.** Do not change or delete files you did not make without a
    reason, and say so when you change a shared file.
