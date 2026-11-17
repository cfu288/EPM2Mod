# Looks from the SD Card

Load your own film looks from a file on the SD card. The camera keeps them after power-off and without the card,
until you load another file.

## Make a file

List one look per menu entry (`entry` is the stock name in [Film Simulations](film-looks.md), column "Replaces"):

```json
{"looks": [
  {"entry": "Pale&Light Color", "name": "Portra 800", "fit": "looks/fits/portra800.npz"},
  {"entry": "Diorama", "name": "Ektar 100", "fit": "looks/fits/ektar100.npz"}
]}
```

Then run `uv run epm2mod looks pack MYLOOKS.json -o EPM2LOOK.BIN`. Entries that the file does not list have their
built-in look from the next power-on. Without a list, the command writes the built-in looks.

## Load

1. Copy the file to the top folder of the card as **EPM2LOOK.BIN**.
2. Turn the camera on, press **MENU**, then **MENU** again. The looks change at once.
3. You can delete the file. The looks stay.

Check it in **OK → Picture Mode** (scroll right past Custom).

<img src="../images/ui/quick-menu-portra.png" width="320" alt="The quick menu with Picture Mode on a film look">

## Limits

- The menu keeps each entry's own name (for example "Pro 400H"), whatever look you load there.
- Grainy Film (Double-X) takes only a black-and-white look. The other eleven entries take colour looks.
- While EPM2LOOK.BIN is on the card, the camera reads it at the first menu or playback screen after power-on.
- A damaged file, or a file for another camera or firmware, changes nothing.
- As with the built-in looks, live view shows the tone curve only with the shutter half pressed.

File format: [look-file-format.md](../look-file-format.md). Design and tests: [card-looks design](../../experiments/2026-11-17-card-looks/design.md).
