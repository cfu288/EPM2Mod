# Looks from the SD Card

The camera comes with the Olympus art filters. A file on the SD card puts a film in each ART entry it lists. The
camera keeps them, with their names, after power-off and without the card.

## Make a file

The installer always writes the file, with the 12 default film simulations or your choice. On the command line, change any film simulation in this command (the names are in the [film table](film-looks.md#available-film-simulations) and in `uv run epm2mod looks list`, and
`uv run epm2mod cards` shows the card's folder):

```sh
uv run epm2mod looks pack ART1=portra-400 ART2=ektachrome ART3=pro-400h ART4=kodachrome ART5=double-x ART6=vision3-250d ART7=velvia ART8=superia-400 ART9=provia ART10=portra-160 ART11=gold-200 ART12=vision3-500t --card /path/to/card
```

It writes `EPM2LOOK.BIN` to the top folder of the card. Without the card, use `-o FILE` and copy the file there.

## Load

MENU → Custom Menu → J → **Load Looks** → **Load** → OK. The row reads Loading, then **Loaded** at the next key.

<img src="../images/ui/load-looks-list.png" width="320" alt="Load Looks with Off and Load">
<img src="../images/ui/load-looks-loaded.png" width="320" alt="Load Looks reads Loaded">

The entry shows the look's name everywhere the camera shows a film name.

<img src="../images/ui/picture-mode-loaded.png" width="320" alt="The Picture Mode strip with Portra 800">

Each Load replaces the last one: an entry the file leaves out goes back to its Olympus art filter. You can delete
the file. **No file** or **Bad file** means nothing changed. No Custom Menu tab (gears icon): enable it in **Setup Menu → Menu Display**.

## Limits

- The row's texts are English in every menu language.
- No look has grain. Double-X has had none since this build.

File format, for a program that writes looks: [look-file-format.md](../look-file-format.md). Design and tests:
[card-looks design](../../experiments/2026-11-17-card-looks/design.md).
