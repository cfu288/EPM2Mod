# Pixel Hacking PoC (2026-11-08)

**Question:** does the E-PM2 SD updater accept and run modified firmware?

**Method:**
1. Searched block 1 for visible UTF-16 menu labels. Picked "Pixel Mapping", which has 16 aligned copies, one per language table, plus one inside a French help sentence.
2. Replaced each with the same-length "Pixel Hacking" and recomputed the block checksum.
3. Reflashed stock first to prove the flash path, then flashed the PoC.

**Result:** works. See [../../docs/camera-log.md](../../docs/camera-log.md). Promoted to `patches/pixel-hacking.json`.

**Learned:**
- The camera checks only the container checksum, and block 1 has no internal check on equal-length edits.
- On the E-PM2, the lamp is solid while writing (about 1–1.5 min) and blinking when done.
- The Custom Menu Utility section is **J** on the E-PM2.
- Other candidate labels found while searching, all once in the English table: "Touch Screen Settings", "Copyright Settings".
