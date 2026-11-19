# 2026-11-19: builds/debug-log-movie-bitrate.json

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-19 | `builds/debug-log-movie-bitrate.json`: DEBUG build, `debug-log-movie-time` + `specs/movie-bitrate-32.json` (MOV 1080 Fine 32 Mb/s, 1080 Normal 24, 720 Fine 20, 720 Normal 16; encoder cap 50 Mb/s; in-camera playback check 50 Mb/s) | `09dd21ca6aa8a100a0b43b9a9d336a8f5523c262e06bb9c0be285c55c7e61375` | **Candidate, not flashed.** Test sheet: experiments/2026-11-19-movie-sampling/NOTES.md section 10. |
| 2026-11-19 | flashed by the owner; three handheld clips and one photo | same | **Works, small gain.** HRD 32.77 / 24.58 Mb/s accepted; Fine clip 18.7 Mb/s at QP mostly 22 (was 22–26 at 20 Mb/s); every clip played in the camera; no stop, no freeze. Owner: "similar to pre mod". Results: experiments/2026-11-19-movie-sampling/NOTES.md section 11 |
