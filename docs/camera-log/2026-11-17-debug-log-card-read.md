# 2026-11-17: builds/debug-log-card-read.json

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-17 | `builds/debug-log-card-read.json` (`debug-log-films-12d` + `patches/log-card-read.json`: the card-read probe) | `1297f288a69138d7b10fab1f37553a65fea82d2013ecc141445e194528689cab` | **OK. Probe 1 passed: the firmware reads a card file on the camera.** Log session 15 (build id `3cc5e33e95b6de52`): MENU at 2.45 s, `card_read` bytes 16, first4 `0x4B4F4F4C` ("LOOK", the file's first word) at 2.48 s, then flush ok; a shot, a second menu and the power-off followed, every flush ok; no error record but the eight DMA records of every start. Lamp timings not recorded. |
