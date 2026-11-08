# Verification notes (2026-11-08)

- **Where the stock file comes from:** ep5-fw-reverse says it took the E-PM2 v1.1–v1.6 files from an xdel.ru `pre_fix/` folder. That folder is not in xdel.ru's current listing, and Wayback has no E-PM2 BIN, so there is no direct independent copy. Indirect checks:
  - The repo's E-PL5 v1.6 is byte-identical to xdel.ru's live `original/penepl5/` copy (sha256 `1355c2b8…0c01`).
  - E-PM2 v1.6 blocks 1–3 are byte-identical to that independent E-PL5 file.
  - The OM tail differs from the E-PL5's only in the model ID and checksum.
  - Block 0 has no independent reference. The camera now runs it, and stock behaviour looks normal.
- **Tool:** `oetool` unpack→pack reproduces all six stock files exactly. An independently written decoder agreed on every checksum of the PoC build.
- **PoC build:** 52 bytes differ from stock (48 bytes of text, 4 of checksum). All 16 copies are complete, null-terminated UTF-16 strings in per-language tables.
- **Camera:** see [camera-log.md](camera-log.md). Modified firmware is accepted.
