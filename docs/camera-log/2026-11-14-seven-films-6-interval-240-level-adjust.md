# 2026-11-14: seven-films-6-interval-240-level-adjust

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-14 | the specs of `seven-films-6-interval-240-level-adjust` + `patches/peaking-direct-4.json` (`builds/peaking-direct-4.json`) | `eea187a958de410bca0448367408998099fde177548d0b9010baf510a3452482` | **OK. Focus peaking works.** User: "works with focus peaking". So code runs from the kernel range 0x7E4C9200 (first code there: proven). Later report: Velvia in the quick menu does not crash; the lines are "a little weak". Not yet tested: sleep and wake. Before the flash: Same routines and hooks as direct-3; the code is now in the kernel range 0x7E4C9200–0x7E4C93A3 (first code there) and at 0x7EBF1F28. Scenarios S6 (picture mode onto ART 7) and S7 (sleep routine) fail on direct-3 and pass on this build and on the pinned build. Boot test equal to pinned. |
