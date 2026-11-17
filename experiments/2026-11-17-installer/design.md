# One-click installer: design (2026-11-17)

The owner's goal: a user who doesn't code downloads one zip for any platform, double-clicks a launcher and gets a local
page. The page downloads and patches the firmware, adds film looks if the user wants (up to 12, as on the public
site), and either writes to an SD card that the user picks or gives a zip. Olympus's art filters stay the default.
Films replace them only when the user chooses. The CLI stays the default way to install and test.

## Acceptance criteria (user level)

1. On macOS, Windows or Linux, with no Python or uv installed: unzip, double-click the launcher, and the page opens.
   Nothing else is installed by hand.
2. "Make firmware" downloads OM's file, patches it and checks it, and shows each step. The result's sha256 is the
   pinned build's.
3. With no films chosen, the camera keeps what the pinned firmware has in each slot, and the page says what that
   is (from the data, not hard-coded). Olympus's art filters as that default belong to a separate project, below.
4. "Add film looks" (off by default) shows the public site's list: up to 12 films, in ART slots the user orders. The
   preview follows the order.
5. Output: a plugged-in SD card picked from a list, or "Download zip" with the same files, laid out as on the card.
6. The CLI makes byte-identical files for the same choices: `make_firmware.py --card DIR` and
   `epm2mod looks pack ART2=velvia ... --card DIR`.
7. Writing to a card changes only `DCOLYMP/E1019999.BIN` and `EPM2LOOK.BIN`. Fixed disks are never listed. A card
   whose `DCOLYMP` holds other files gets the same warning as from the CLI.
8. The local page can't be reached from other computers or driven by other websites.
9. Nothing that works today breaks: the CLI, the public site, every camera feature of the pinned build.

## Separate project: Olympus's art filters by default

The owner split this out on 2026-11-17: the installer doesn't wait for it. When its firmware is pinned, regenerate
`looks/film-records.json` and the previews, and the installer and the site show Olympus's filters by default with no code change.
Its criteria (agreed earlier):

- F1. After the flash, all 12 entries are Olympus's art filters.
- F2. Loading a film changes only that slot.
- F3. Built-in brings back the stock filters, effects included.
- F4. Every existing criterion holds.
- F5. Movies and ART bracket behave as stock, or as the loaded film, slot by slot.

## One pipeline: what is shared

| Step | CLI | Local app | Public site |
|---|---|---|---|
| Firmware | `epm2mod make` (pipeline.make) | the same `make`, called by `epm2mod serve` | none |
| Stock download | `stock.fetch` | the same | none |
| Card checks and write | `pipeline.check_card`, `copy_to_card` | the same | none |
| Look file | `looks pack`, from the film records in `looks/film-records.json` | the same Python function | TypeScript packer from the same records (byte-equal test) |
| Film list and UI | none | shared React components (SlotList, FilmLibrary, StripPreview) | the same components |

- No projection or flat patch file. The zip carries the package, `pinned-build.json`, the pinned build description
  and its specs. The app runs the same `make` as the CLI.
- `looks pack` reads the film records (made from the fit files by `export_films.py`) instead of the fits. Then
  users need no numpy, and the zip is standard library only. The fits stay a developer step, and a test fails when
  the records are stale.
- `epm2mod serve` is a CLI command: the launcher runs it, and developers run it the same way.
- `epm2mod cards` lists removable volumes. The app's card list uses the same function.

## Steps

1. Look records as the single source: `web/src/data/films.json` moved to `looks/film-records.json`; `looks pack`
   packs from it without numpy (`epm2mod.looks.records`). Done 2026-11-17.
2. `epm2mod cards` (removable volumes on macOS, Windows, Linux): `epm2mod.cards`, done 2026-11-17. Only FAT and
   exFAT volumes count. The Linux rule is tested on this computer; the macOS and Windows rules are tested with sample
   data only, so the release CI of step 5 runs on macOS and Windows runners too.
3. `epm2mod serve`: stdlib `http.server` on 127.0.0.1, a random token in the URL, Host check. Endpoints: build
   (progress), cards, write, zip. Done 2026-11-17 (`epm2mod.serve`): the token is in the URL's fragment (`#token=`)
   and goes in the header `X-EPM2-Token`; a write goes only to a card that `cards()` lists; a test makes the pinned
   build with looks through the app and through the CLI and compares the card files byte for byte. The page is
   served from `src/epm2mod/app/` (git-ignored, built by step 4).
4. The app page: a second Vite entry in `web/` that reuses the components, built into the package's static folder.
   Done 2026-11-17: `web/` is an npm workspace, `packages/ui` (shared: `MenuEditor`, `useLooks`, `StripPreview`,
   `PageFrame`, `LoadSteps`, film data, packer), `apps/site` (public) and `apps/local` (this page, built into
   `src/epm2mod/app/` by `npm run build:app`). Lint rules keep the apps from importing each other.
5. Release zip from CI: launchers (pinned uv version, sha256-checked), package, pinned build's specs, built app
   page; a CI test that unpacks the zip and makes the pinned build from it.
   Built 2026-11-17: `epm2mod release` (`src/epm2mod/release.py`) writes `EPM2Mod-<build>.zip` from the pinned
   build description; launchers in `release/` (uv 0.13.6, sha256 per system; uv's Python 3.12 and its cache stay in
   the folder's `.uv`). The package needs only the standard library, so the launchers run it from `src` with
   `uv run --no-project`: no install step, no `uv.lock` needed. `.github/workflows/release.yml` unpacks the zip with
   each system's own tool on Linux, macOS and Windows and runs `.github/scripts/release_smoke.py` (make with the
   pinned sha, cards, serve); a tag `v*` publishes the zip. The README links the zip once a release exists.
   Checked in the emulator: a Mac hidden file (short name `_E101~1.BIN`) beside the firmware in `DCOLYMP` leaves the
   update path as stock (update-path-test PASS); the long-name entry and the hidden attribute are not emulated.

## Notes for whoever implements this

- **Owner's rules for this work:** agree criteria before building (done: the owner said "Yes" on 2026-11-17).
  Every UI sentence must answer "what am I telling the user?" and "is it helpful?", and new text gets a blind
  reviewer agent. No text that says what something is *not*. Questions to the owner go on their own line at the
  end. A camera run costs about 1000: use the emulator for everything it can settle, and plan one run for all open
  items.
- **Separate project, Olympus's filters by default (F1-F5):** the pinned `card-looks-4` flashes films over the stock art filters. Slots 1-7 are
  the hard part: `remap7b-code` and `seven-films-5` overwrite the stock tables; slots 8-12 come from `films12-*`
  specs. Study in the emulator first: which stock tables and effect settings must stay, and whether Built-in
  (`card-looks-4` mode 2, a RAM snapshot taken at start) can snapshot the stock tables instead. Card-looks design and
  addresses: `experiments/2026-11-17-card-looks/design.md`. After it is pinned: the site's and app's default rows
  become "Olympus <filter>" (`slots[i].entry` in `looks/film-records.json` is the Olympus name), and the preview needs name images
  for the 12 Olympus names (`web/scripts/render_previews.py`, name box NAME = (160, 12, 560, 44) of the strip).
- **`looks pack` without numpy (done):** `records.looks_of_choices` decodes the records of `looks/film-records.json`
  and sets the slot. `looks pack` with choices or no argument, and `looks list`, need no numpy; only a look list
  (`looks pack LIST.json`) reads fits. `looks/films.json` is another file: the firmware's seven-film list.
- **Cards:** macOS `/Volumes/*` checked with `diskutil info -plist` (Removable/Ejectable or Internal false);
  Windows drive letters with `GetDriveTypeW == DRIVE_REMOVABLE` (ctypes); Linux `lsblk -J -o NAME,RM,HOTPLUG,
  MOUNTPOINT` with RM or HOTPLUG = 1. Show the volume name and size. `pipeline.check_card` already warns about other
  files in `DCOLYMP`.
- **serve:** stdlib `http.server.ThreadingHTTPServer` bound to 127.0.0.1 on a free port. A random token in the
  opened URL and on every API call; reject a Host header that is not `127.0.0.1:PORT` or `localhost:PORT` (DNS
  rebinding). Open the browser with `webbrowser.open`. Progress via polling or server-sent events from `make`'s
  `log` callback.
- **Launchers:** `Start (Mac).command`, `Start (Windows).bat`, `start.sh`. Download a pinned uv release from
  GitHub, check its sha256, keep it in the folder, then `uv run --python 3.12 epm2mod serve` (pin Python; lock
  with `uv.lock`). Expect the first-run warnings: macOS right-click → Open, Windows SmartScreen.
- **Web build:** Node 26 (`.nvmrc`); `npm run check` and `npm run e2e` in
  `web/`. dnd-kit tests need waits on its announcements. Style: OM SYSTEM gallery look, fonts Sora and Arimo
  (`web/README.md`).
