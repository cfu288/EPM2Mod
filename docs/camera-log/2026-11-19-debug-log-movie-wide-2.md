# 2026-11-19: builds/debug-log-movie-wide-2.json

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-19 | `builds/debug-log-movie-wide-2.json`: DEBUG build, `debug-log-movie-bitrate` + `specs/movie-wide-frame.json` (reader side, as `debug-log-movie-wide`) + `specs/movie-wide-writer.json` (writer side: the pre-processor writes 1960-px lines at a 1.2 resize in place of 1680-px lines at 1.4; record 7 of the TAKE request table 0x7E793184) | `8e644f7e1497082a19d2c66198a84bf22a252bf9c5e5c89c9d9917d34cdb5c9d` | **Candidate, not flashed.** Criteria: experiments/2026-11-19-movie-sampling/NOTES.md section 14. |
| 2026-11-19 | flashed by the owner; five handheld clips | same | **Works.** Clean 1920×1080 pictures, 29.8 fps, 23.7 ms per frame, round objects round, clips play in the camera. Detail gain not yet shown (no fair A/B); 720 and photos not tried. Results: experiments/2026-11-19-movie-sampling/NOTES.md section 15 |
