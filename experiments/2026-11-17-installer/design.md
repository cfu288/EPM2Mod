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
3. With no films chosen, the camera keeps Olympus's art filters, effects included (needs the firmware of criterion
   F1 below).
4. "Add film looks" (off by default) shows the public site's list: up to 12 films, in ART slots the user orders. The
   preview follows the order.
5. Output: a plugged-in SD card picked from a list, or "Download zip" with the same files, laid out as on the card.
6. The CLI makes byte-identical files for the same choices: `make_firmware.py --card DIR` and
   `epm2mod looks pack ART2=velvia ... --card DIR`.
7. Writing to a card changes only `DCOLYMP/E1019999.BIN` and `EPM2LOOK.BIN`. Fixed disks are never listed. A card
   whose `DCOLYMP` holds other files gets the same warning as from the CLI.
8. The local page can't be reached from other computers or driven by other websites.
9. Nothing that works today breaks: the CLI, the public site, every camera feature of the pinned build.

Firmware criteria (point 2, agreed earlier):

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
| Look file | `looks pack`, from the film records in `looks/films.json` | the same Python function | TypeScript packer from the same records (byte-equal test) |
| Film list and UI | none | shared React components (SlotList, FilmLibrary, StripPreview) | the same components |

- No projection or flat patch file. The zip carries the package, `pinned-build.json`, the pinned build description
  and its specs. The app runs the same `make` as the CLI.
- `looks pack` reads the film records (made from the fit files by `export_films.py`) instead of the fits. Then
  users need no numpy, and the zip is standard library only. The fits stay a developer step, and a test fails when
  the records are stale.
- `epm2mod serve` is a CLI command: the launcher runs it, and developers run it the same way.
- `epm2mod cards` lists removable volumes. The app's card list uses the same function.

## Steps

1. Look records as the single source: move `web/src/data/films.json` to `looks/films.json`; `looks pack` packs from
   it without numpy.
2. `epm2mod cards` (removable volumes on macOS, Windows, Linux).
3. `epm2mod serve`: stdlib `http.server` on 127.0.0.1, a random token in the URL, Host check. Endpoints: build
   (progress), cards, write, zip.
4. The app page: a second Vite entry in `web/` that reuses the components, built into the package's static folder.
5. Firmware point 2 (F1-F5): emulator study, one camera run, pin. Then the site and app default to Olympus's
   filters, with name previews for them.
6. Release zip from CI: launchers (pinned uv version, sha256-checked), package, pinned build's specs, built app
   page; a CI test that unpacks the zip and makes the pinned build from it.

## Notes for whoever implements this

- **Owner's rules for this work:** agree criteria before building (done: the owner said "Yes" on 2026-11-17).
  Every UI sentence must answer "what am I telling the user?" and "is it helpful?", and new text gets a blind
  reviewer agent. No text that says what something is *not*. Questions to the owner go on their own line at the
  end. A camera run costs about 1000: use the emulator for everything it can settle, and plan one run for all open
  items.
- **Firmware point 2 (F1-F5):** the pinned `card-looks-4` flashes films over the stock art filters. Slots 1-7 are
  the hard part: `remap7b-code` and `seven-films-5` overwrite the stock tables; slots 8-12 come from `films12-*`
  specs. Study in the emulator first: which stock tables and effect settings must stay, and whether Built-in
  (`card-looks-4` mode 2, a RAM snapshot taken at start) can snapshot the stock tables instead. Card-looks design and
  addresses: `experiments/2026-11-17-card-looks/design.md`. After it is pinned: the site's and app's default rows
  become "Olympus <filter>" (`slots[i].entry` in films.json is the Olympus name), and the preview needs name images
  for the 12 Olympus names (`web/scripts/render_previews.py`, name box NAME = (160, 12, 560, 44) of the strip).
- **`looks pack` without numpy:** today `lookpack.looks_of_choices` loads fits (numpy). Change it to decode the
  records of `looks/films.json` (`lookfile.decode_record`, set slot and name) and keep the fit path only in
  `export_films.py`. Keep the Python test that fails when films.json is stale, and the TS byte-equal vectors in
  `web/src/lib/lookfile.test.ts`.
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
- **Web build:** Node 26 (`web/.nvmrc`); `npm run check` and `npm run e2e` in
  `web/`. dnd-kit tests need waits on its announcements. Style: OM SYSTEM gallery look, fonts Sora and Arimo
  (`web/README.md`).
