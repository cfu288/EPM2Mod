# 2026-11-24: data/builds/slow-boot-probe.json

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-24 | `data/builds/slow-boot-probe.json`, a DEBUG build (not for use): peaking-mf + `slow-boot-probe` (Debug Log events `lv_first`: the first live-view struct refresh of each start, with a word of peaking-mf's T_MF in segment 2 and a word of segment 3, read at that moment; `start_kind`: the power-on factor, the wake reason and the quick start's state after the segment copies; GitHub issue #6, `experiments/2026-11-24-slow-boot/NOTES.md`). hookcheck, boot-test, update-path-test and the T_LV check `scripts/emu_tlv.mjs` pass | `e783fbe686fc774a17b64590c8bd986ff1259bb84d189b703c5efc478aa675ca` | **Candidate, not flashed.** |
