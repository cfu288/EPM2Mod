# 2026-11-11: patches/history/film-portra-xp.json

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-11 (time not recorded) | `patches/history/film-portra-xp.json` + `patches/history/label-portra.json` (`build/film-portra-xp-labelled.BIN`) | `6a35cb3b…ed367837` (checked on the card) | **OK. First look patch.** Lamp solid, then blinking (durations not recorded). Booted and shoots. RAW Data Edit of PB090221 as Cross Process I (PB090223.JPG) matches the model's prediction: gray row 1.5–2.0 codes rms per channel, colour patches ΔE2000 1.64 mean (the model's own accuracy on stock Natural is 1.56). So the 24 per-channel base-gamma tables, the look curve 0x7E75F2F0 and the saturation pair 0x7E7696B4 are the right locations, and nothing else in Cross Process I differs measurably. Label change not yet confirmed by the user. Details: `experiments/2026-11-09-film-portra/NOTES.md` §14–15. |
