# 2026-11-19: builds/debug-log-movie-time.json

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-19 | `builds/debug-log-movie-time.json`: DEBUG build, the pinned `epm2mod-2026.11.19` + `specs/log-movie-time.json` (timing probe of the movie path: events mv_frame, mv_enc). FIRST CODE line for 0x7E69EC6B-0x7E69EE0B (segment 1, the free part of lss-core's area; lss-core's code in the same area runs on the camera since 2026-11-19) | `c5fcf7142451c97186f846ad4aa4baf302f1d2a7f11ed9d3239bc66b6e58d6fc` | **Candidate, not flashed.** Test sheet: experiments/2026-11-19-movie-sampling/NOTES.md section 6. |
| 2026-11-19 | flashed by the owner; six handheld clips | same | **Ran without a fault.** One timing record per frame; Natural IS off 22.1 ms median, 23.1 ms p95 of 33.4 ms; IS on 20.6 ms. Clips 1 and 7 lost from the log (no playback between clips). Results: NOTES.md section 9 |
