# 2026-11-16: peaking-fast

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-16 (desk result) | `peaking-fast` and every build with its peaking code | – | **Cause of the crash at a focus-ring turn after a shot.** Error 0x34000002 at 0x7E72A277 is the ART task's command check: the art session was told to end when it was not started. In the emulator, when peaking switches the image-work heap to mode 1 while a block of the other pool is in use, the heap is divided again under that block, the art buffers are refused in every frame and each frame sends an art end/start pair. The published `peaking-fast` has the fault (scenario S19 fails on it). Fix: `patches/peaking-save-guard.json` (97 bytes): the latch waits while that pool is in use, and the heap stays in mode 1 at the end while it is in use. Details: `experiments/2026-11-14-focus-peaking/NOTES.md` §18. |
