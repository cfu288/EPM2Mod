# 2026-11-14: peaking-direct-3

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-14 (desk result for the row above) | `peaking-direct-3` | `5330c0b8…62c4c325` | **Cause of the ART 7 crash found; the build is superseded.** The spec put a routine at 0x7E880FE4, the last byte of the six-axis colour handler that `seven-fixes-1` added (0x7E880FD4, 17 bytes). Only art codes 167 and 168 (Velvia) use that handler; its jump then went to 0x5C56D8D8. The checks missed it: the stock byte is also 0xFF, so `expect` matched and the free-space tool counted the byte as free. Second fault, not seen on the camera: the two "dead" areas 0x7E53A55C and 0x7E50A201 are the sleep routine, called from code that runs in SRAM. New static check: `tools/emu/opcheck.py`. Details: `experiments/2026-11-14-focus-peaking/NOTES.md` §14. |
