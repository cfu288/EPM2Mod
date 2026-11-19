# 2026-11-17: builds/debug-log-card-keep.json

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-17 | `builds/debug-log-card-keep.json` (`debug-log-films-12d` + `patches/log-card-keep.json`: the persistence probe) | `2771357d4f7debe57fe106209fa65cfeec6d4b8b4cec444d5a36869cb125cefa` | **OK. Persistence passed: a look loaded once from the card stays in the camera without the file.** Log session 30: the EEROM bank's unused tail was empty on this camera (`bank_tail` 0 nonzero words), the grey look loaded at the first menu, stored and saved (`card_keep` result 0, sum 0x300). Sessions 31, 32 (starts that went to power-off) and 33 (the file removed from the card): `bank_look` applied at the first GUI state, the table read back grey (0x0096004D). Photo PB170149 (session 33, before any menu): black and white (mean colour 6.9, colour spread at equal brightness 1.33). No error record. |
