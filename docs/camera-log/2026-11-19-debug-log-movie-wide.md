# 2026-11-19: builds/debug-log-movie-wide.json

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-19 | `builds/debug-log-movie-wide.json`: DEBUG build, `debug-log-movie-bitrate` + `specs/movie-wide-frame.json` (movie Bayer frame 1938×1296, 1920 effective, stride 1960, in place of 1662×1296 / 1646 / 1680; sensor window unchanged; 720p uses the same frame; Movie IS crop scaled 1414 → 1650) | `9fbc9436d0271b2421069689cd6570dab9eb9dab8d4f0a764e4219ff096037a1` | **Candidate, not flashed.** Test sheet and criteria: experiments/2026-11-19-movie-sampling/NOTES.md section 12. |
| 2026-11-19 | flashed by the owner; one clip | same | **Failed criterion 1:** pink vertical bands and a garbled bottom in live view and the clip. The reader used the new 1960 stride, the writer the stock 1680 (band period about 280 px; picture ends at about 1312/1512 of the height). No freeze, 29.8 fps, 23.5 ms per frame. Photos not tried. Results: experiments/2026-11-19-movie-sampling/NOTES.md section 13 |
