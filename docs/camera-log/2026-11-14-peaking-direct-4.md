# 2026-11-14: peaking-direct-4

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-14 | the specs of `peaking-direct-4` + `patches/peaking-gain-2x.json` (`builds/peaking-gain-2x.json`) | `ce1037cda6c9ff87e600272383dfe97b649a5ef24d6928e319b581191b4ca2c8` | **OK.** One byte against `peaking-direct-4`: the gain of the peaking line image is 512, not 256 (0x7E4C9396). User on the line strength: "Perfect". Later report: sleep and wake work. |
