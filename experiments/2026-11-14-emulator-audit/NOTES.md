# Emulator audit of the camera-tested builds (2026-11-14)

The boot emulator (docs/feasibility.md, "The emulator") was used to look for unintended effects of the
patches in the pinned build `seven-films-6-interval-240-level`. Nothing was flashed. No repo file other
than this one was changed.

Labels: **V** = VERIFIED-in-emulator (the firmware's own code ran and the result was read from its
screen, its log or a probe). **I** = INFERRED. **U** = UNKNOWN. "Static" = read from the image bytes.

All scripts, screenshots and logs are outside the repo in `~/opt/om-emu-e101-boot-work/audit/`; the
emulator's own notes are `~/opt/om-emu-e101-boot-work/NOTES.md` (section 13 is this session). Commands
below run in `~/opt/om-emu-e101-boot-work` after `. ./env.sh`; `$SCRATCH/<name>` is an unpacked image.

## Result in short

| # | Check | Verdict |
|---|---|---|
| 1 | Menu crawl, stock against pinned | **OK.** Every differing screen is an intended change. No row is lost, no cursor difference, no new firmware error |
| 2 | Time Lapse Settings grey in the emulator | **OK, emulator state only.** The gate is the clock (in P) or iAUTO. With a clock model the row works and all sub-screens open; values survive a restart. Two things to look at: "Card Full" and the defaults (below) |
| 3 | Hook at 0x7E56C6A5 jumps to segment 2 | **OK, not a real exposure** (V for the three start paths, I for "never before the load") |
| 4 | Boot test of every tested build | **OK.** All four equal stock |
| 5 | Film names everywhere | **DEFECT (cosmetic): complete only in English.** Other languages show the old names or a mix. One wrong rename in French |
| 6 | Level Gauge | **OK** for the row, the INFO cycle and "off = stock". Panel 594 through a viewfinder: **U** |
| 7 | Anything else | Settings store identical. Reset was not executed: **U** |

## Findings that need a decision

1. **Film names are complete only in English (V).** `patches/seven-labels.json` replaces a text only
   where it is exactly the English name. The ART list of the pinned image reads:
   - English: Portra, Ektachrome, Pro 400H, Kodachrome, Grainy Film, Vis 250D, Velvia, Superia 400. Whole, not clipped.
   - German: Portra, Soft Fokus, Blasse Farben, Weiches Licht, Monochrom Film, Lochkamera, Velvia, Crossentwicklung.
   - French: Portra, Ektachrome, Ton Neutre&Lumineux, Tonalité Lumineuse, Grain Noir&Blanc, Sténopé, Velvia, Traitement Croisé.
   - Spanish: Portra, Enfoque Suave, Color Pálido, Tono Claro, B/N Antiguo, Estenopeico, Velvia, Proceso Cruzado.
   - Greek: Portra, old, old, old, old, Vis 250D, old ("Διόραμα"), Superia 400.
   - Japanese, Chinese (simplified), Russian, Thai, Korean, Bulgarian: all seven old names, as stock.
   Counts of replaced strings (static): Pop Art 10 languages, Cross Process 10, Diorama 21, Pin Hole 7,
   Soft Focus 3, Pale&Light Color 1, Light Tone 1. No text is clipped or garbled in any language looked at.
   Either say "English only" in the README or add the other languages' strings to the spec.
2. **One unintended rename, French only (static V, where it shows is I).** The French text block has a
   second plain string "Soft Focus" at block-1 offset 0x3D5550. Its neighbours are "Effet
   supplémentaire", "Sténopé", "Effet Fondu Bords Blancs", "Encadré": it is the name of the soft-focus
   *effect* in the Add Effects list, not the filter. The spec replaces it with "Ektachrome". Fix: drop
   that one op from `seven-labels.json`.
3. **Time Lapse Settings is not offered in every mode (V).** P: selectable (needs the clock). iAUTO:
   grey. ART mode and movie mode: the row is hidden (ART shows drive, Image Stabilizer, Bracketing, RC
   Mode). The same rules hide or grey the stock rows Bracketing and Multiple Exposure, so this is the
   firmware's rule set, which is the E-PL6's (I). The README should say: use P/A/S/M, and pick a film
   look there through Shooting Menu 1 → Picture Mode (the list has the film names).
4. **"Card Full" with Time Lapse On (V in the emulator, cause U).** Emulated card: 64 MiB, 16 shots
   left; Frame 230. After Time Lapse Settings → On, leaving the menu shows a full-screen "Card Full".
   After a restart it shows again; the first MENU press removes it, and the row then reads Off (the
   four values are kept). Whether the firmware compares the frame count with the shots left was not
   followed. Camera probe: a nearly full card, Frame above the shots left, switch On, leave the menu.
5. **Defaults (U).** On an empty settings store the pinned image shows Frame 99, Start Waiting Time
   00:00:01, Interval Time 00:00:01, not the spec's 10 frames and 5 s. The patched default bytes are in
   the image (static V: 0x0A at block-0 0xA2E98, 0x05 at 0xA2EA8). The MODE bank that the emulator's
   first boot builds is byte-identical for stock and pinned. So the edited records are not what fills
   these values on that path (I). The emulator's first boot starts from erased flash, which no camera
   does; the camera probe is a full reset and a look at the three values.

## 1. Menu crawl

Crawler: at each cursor position one PNG named by its path, RIGHT opens the child, DOWN to the end of
the list. It never presses OK. Screens are compared byte by byte.

| Configuration | Screens stock / pinned | Differ | Only on pinned |
|---|---|---|---|
| P, card, clock set, every sub-screen (`p-card-full`) | 3548 / 4255 | 170 | 707 |
| P, no card, first sub-screen (`p-nocard-shallow`) | 304 / 304 | 25 | 0 |
| iAUTO, no card (`iauto-nocard-shallow`) | 235 / 235 | 9 | 0 |
| ART, card (`art-card-shallow`) | 237 / 237 | 0 | 0 |
| Movie, card (`movie-card-shallow`) | 229 / 229 | 12 | 0 |

Every differing screen, by place (all **intended**, V):

| Where | Screens | Cause |
|---|---|---|
| Shooting Menu 2 page, and every pop-up drawn over it (drive, Image Stabilizer, Bracketing, Multiple Exposure, RC Mode) | 12 + tab view | the new row Time Lapse Settings; RC Mode one row lower |
| Shooting Menu 2 → Time Lapse Settings and below | 701, pinned only | the new screens |
| Shooting Menu 2 → Bracketing → ART BKT list | 43 | film names |
| Shooting Menu 1 → Picture Mode list | 12 | film names |
| Custom Menu D → Info Settings → LV-Info | 9 + 3 pinned only (seen twice, the list wraps) | the row Level Gauge and its Off/On |
| Custom Menu D → Picture Mode Settings | 42 (seen twice) | film names |

- Rows on one image only: Time Lapse Settings, Level Gauge. No stock row is missing on pinned (V).
- Cursor: the crawler's notes (end of list, wrap, a child that leaves two levels) are the same on both
  images in every unit (V).
- Firmware error log: the same two boot-time entries (0x2A001001) on both; none during any crawl (V).
- ART mode: no difference at all, because the Time Lapse row is hidden there and the Picture Mode row
  is grey. Movie mode: only the Picture Mode list.
- Not walked: the rest of a row's sub-screens after 150 screens (three Custom Menu chunks and the
  clock editor; same on both); SCN mode; A, S and M; the Playback Menu with pictures on the card (the
  card is empty: one selectable row); the top mode menu and the live control (they sit on pictures
  that are not in the update file); the super control panel. The Accessory Port Menu was walked; its
  row Electronic Viewfinder is grey without a viewfinder.

```sh
audit/crawl-all.sh p-card-full          # also: p-nocard-shallow iauto-nocard-shallow art-card-shallow movie-card-shallow
python3 audit/crawldiff.py audit/crawl/p-card-full/stock audit/crawl/p-card-full/pinned audit/diff/p-card-full
```

## 2. Time Lapse Settings

- Row-enable source (V): per row the menu calls `app_check_mode` 0x7E9E8CCD; each setting has a list
  of checks from the table 0x7EC1C368. For setting 482: iAUTO fails check 26 (0x7E9E914D), which also
  greys Bracketing and Multiple Exposure; in P the only failing check was 78 (0x7E9E9B85): the real-time
  clock is not set. Multiple Exposure in P fails check 39: no card.
- The emulator had no clock. A register model of the clock was added (seconds counter, "initialised"
  marker; Unix time, V). With the clock set the row is black and selectable in P (V). So the grey
  state was emulator-only, and it confirms the README's "set date and time first".
- Screens (V): Off/On → Frame, Start Waiting Time, Interval Time, Time Lapse Movie, each with its help
  text. Frame list: 99 values going down from 99f to 1f in steps of 1 (the list stops at 1f), and
  going up 100, 105, … 240 (29 values); UP at 240 does nothing. Total 128.
- Persistence (V): Frame 230, 00:01:01, 00:02:01, Movie On were set, the menu left, the emulator
  restarted with the saved store: all four values are kept.

```sh
export E101_RTC=2026-11-14T12:00:00 E101_CARD=$SCRATCH/cardsrc-audit
BLOCKS=$SCRATCH/pinned E101_STATE=/tmp/scratch/p.json $NODE audit/canexec.mjs w:500 key:MENU key:RIGHT key:OK key:DOWN
# (state: a copy of audit/state/pinned-p.json) prints "mode 482 check 78 ... status 1" when E101_RTC is not set
# key script for the screens: ~/opt/om-emu-e101-boot-work/NOTES.md section 13.3
```

## 3. The hook at 0x7E56C6A5 (remap7b-code)

- The hook is in function 0x7E56C603, the art colour-matrix step. Its callers are 0x7E56B594,
  0x7E56B5BB and 0x7E56B5E3; these are reached only through the image-job table 0x7E789604, entry =
  job type, used by the dispatcher 0x7E560ACF in the IMG job driver (static V). The callers of that
  driver are still capture, RAW edit, art processing and movie recording.
- Normal boot (V): segment 2 is loaded at 16.8 ms (call 0x7E504C18). 0x7E56C603 did not run in 3 s.
- Quick start, `E101_FAST=1` (V): load at 25.8 ms; the function did not run. The emulated quick
  start stops before live view.
- Menus (V): each menu screen runs one IMG job of type 27, whose table entry is an empty function.
- Update path (V as far as it goes): power-on with OK held. Without an update file: mount error, then
  the normal boot, segment 2 loaded at 18.7 ms. With `DCOLYMP/E1019999.BIN` on the emulated card: file
  found, five parts descrambled, then the body-controller update starts and the emulator cannot go
  on. Segment 2 was not loaded and no IMG job ran up to there.
- Verdict: the hooked code needs a develop job, which needs a capture or an edit. No such job can
  start in the first 26 ms or on the update path (I). The hookcheck FAIL is a true statement about
  load order and not a boot risk here. If it is to be made clean anyway: the 219 bytes at
  0x7ECB08AE–0x7ECB0988 need a segment-1 home. The padding 0x7E880F5C–0x7E881000 is full (3 bytes
  free); a dead segment-1 function is needed, as `peaking-direct-3` uses (0x7E50A201 and 0x7E53A55C
  are taken by it).

```sh
BLOCKS=$SCRATCH/pinned $NODE probe.mjs 3000 7e56c603,7e56c6a5,7e504c18 8          # add E101_FAST=1 for the quick start
BLOCKS=$SCRATCH/pinned $NODE audit/update-boot.mjs 3000                            # OK held, no card
BLOCKS=$SCRATCH/pinned E101_CARD=/tmp/scratch/updcard $NODE audit/update-boot.mjs 4000
```

## 4. Boot test and hookcheck

| Build | sha256 of the rebuilt file = builds/*.json | `stage2-boot.mjs 2000` | hookcheck |
|---|---|---|---|
| seven-films-6 | yes | PASS, output equal to stock | 13 transfers, 1 FAIL (0x7E56C6A5, see 3) |
| seven-films-6-interval | yes | PASS, equal | the same |
| seven-films-6-interval-240 | yes | PASS, equal | the same |
| seven-films-6-interval-240-level (pinned) | yes | PASS, equal | the same |
| pinned, `E101_FAST=1` | | equal to stock with `E101_FAST=1` | |

"Equal" = the whole report (console, task states, instruction counts, events) with the wall time
removed (V). With `E101_FAST=1` the script prints FAIL for stock too: the quick start waits for live
view, which the emulator does not have.

## 5. Film names

See finding 1 and 2. Other facts:

- English, pinned (V): ART list titles, ART BKT list, Picture Mode list, Picture Mode Settings list
  all show the seven names whole. Filter Type and Add Effects screens show icons only.
- Old English names still in the pinned image (static V): only "Add Soft Focus Effect", which is the
  effect and is right. Help texts were not searched for descriptions of the old filters (U).
- The shooting screen in ART mode shows the icon ART 1…12, no name (V). Playback info: not reached.
- There is no right-to-left language. The grid has 34 languages; 11 were set and looked at.

```sh
audit/lang-art.sh        # pinned: en ja de fr es zh ru el th ko bg; stock: en de ja
```

## 6. Level Gauge

- LV-Info has four rows on pinned, three on stock (V). Level Gauge Off/On sets and persists (V).
- INFO cycle with Level Gauge on, in iAUTO, P, movie and ART (V): information → histogram → image only
  → gauge → information. Playback INFO is the same as stock (no card: "No Card").
- With Level Gauge off the INFO cycle and playback INFO are byte-equal to stock in all four modes (V,
  8 screens each).
- Tilt stand-in: level gives two green bars; x or z moves one bar. With x = 1 g (camera on its side)
  the roll bar only goes to its end mark; the display does not turn. What the camera does: U.
- Panel 594: no menu of either image shows it in any crawl (V). The Accessory Port Menu has OLYMPUS
  PENPAL Share, OLYMPUS PENPAL Album and Electronic Viewfinder; the last is grey because none of the
  accessory keys 0x1706 / 0x170A / 0x170E is on (check 87, 0x7E9E9C89). A stand-in that sets the first
  key makes an accessory icon appear on the shooting screen, and then the emulated camera takes no key
  any more. So the viewfinder screens were not reached: U.
- The text "Level Adjust" is in the image once per language on stock and pinned; no menu row shows it (V).

```sh
audit/info-cycle.sh
```

## 7. Other

- Settings store (V): the MODE and EEROM banks of a first boot are byte-identical on stock and
  pinned, same size. The new rows use settings that stock already stores (273, 482–486).
- Reset/Myset and the Custom Menu reset: the screens are the same on both images (crawl); a reset was
  not executed, so what it does to 273 and 482–486 is U.
- The crawler found no fault and no firmware error on either image.

## Limits

The emulator has no sensor, live view, capture, lens or real card timing. Background pictures are
missing. A pass here is not proof on the camera. Findings 4 and 5 may be emulator artefacts; each has
a camera probe above.
