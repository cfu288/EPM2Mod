# 2026-11-16: patches/films-contiguous.json

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-16 (not yet flashed) | the pinned specs + `patches/films-contiguous.json` (`builds/films-contiguous.json`) | `78c5b2419e4ac816aa16db6c6e29d36eaac54bd34f326f7c9103924b7dbad33c` | **Pending.** The lists of looks show the seven films first (ART 1 to 7), then Grainy Film (ART 8). Data only: 555 bytes in the list tables, the picture pointers and one character of 8 texts in 34 languages. Stored values, art codes and the picture tables are unchanged. Emulator: start-up and update-path tests pass; the quick menu, the Picture Mode list, the ART list and the movie list show the new order; a stored selection shows the same look (24 of 24); the same choice writes the same settings (71 of 71 states); the crawl differs only in these lists. Not checked off the camera: the names in the ART BKT review. Details: `experiments/2026-11-15-films-contiguous/NOTES.md`. |
