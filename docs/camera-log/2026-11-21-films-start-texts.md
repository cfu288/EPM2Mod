# 2026-11-21: data/builds/films-start-texts.json

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-21 | `data/builds/films-start-texts.json`: films-twelve-off with `card-looks-8` and `log-menu-3` in place of `card-looks-7` and `log-menu-2`. The stored film simulations are applied from the last entry of segment 3's constructor table, right after the segment copies, and again at the first screen as before. The rows Peaking and Lowest S/S Setting get their texts at run time in every menu language. Two new Debug Log events, `seg_loaded` and `film_applied`. No byte differs from films-twelve-off in the pre-reset range, the kernel range or segment 1 (`experiments/2026-11-21-firmware-dive/build.md`) | `d8eef426227be0f7fc4925626f519afe33178e12205fad97d6701a56bcb39ba0` | **Candidate, not flashed.** |
