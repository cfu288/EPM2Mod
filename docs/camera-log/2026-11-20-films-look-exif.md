# 2026-11-20: data/builds/films-look-exif.json

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-20 | `data/builds/films-look-exif.json`: gauge-info-3 with `stock-films-structure-2` and `card-looks-6`: a loaded film uses the identity look (not Cross Process I's curve, `experiments/2026-11-20-film-camera-round/NOTES.md`); a photo with a loaded film records ArtFilter Off and the film's name in ImageDescription (`experiments/2026-11-20-film-name-exif/NOTES.md`). Label 2026.11.20 | `af4bcb38df908c3d29b3ef028059a3142cbecc4b66737f7bb2cc2848d6a4bcf4` | **Candidate, not flashed.** Emulator: the look selector picks the identity table for all 12 film codes; the EXIF writer gives Off for film values; ImageDescription correct in P and ART mode; six loader sessions pass; free space, hookcheck (allowed hooks only), boot-test, update-path-test PASS. |
