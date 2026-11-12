# E-PM2 video hardware: what limits bitrate and quality (2026-11-12)

| Report | Source |
|---|---|
| [01-public-sources.md](01-public-sources.md) | Specs, reviews, community work, re-checked on the real pages or archive.org copies (2026-11-12); each fact marked confirmed / corrected / unverified |
| [02-sd-and-encoder.md](02-sd-and-encoder.md) | Firmware: the SD host driver and the H.264 encoder set-up |
| [03-sensor-pipeline-memory.md](03-sensor-pipeline-memory.md) | Firmware: sensor readout modes, the movie image path, DRAM |
| [04-mov-clip-analysis.md](04-mov-clip-analysis.md) | **A real clip: High@4.1, CAVLC, custom 4×4 matrices, QP pinned at 20 while using 41 % of the 20.48 Mb/s budget. The QP floor (0x7EEA5A1F) is the binding limit** |

Labels: **V** read in our bytes; **I** inferred; **X** external source.

## Limits, from loosest to tightest

| Limit | What we found | Binding? |
|---|---|---|
| **SD card path** | UHS-I SDR50 (CMD11 + CMD6, divider 1), 4-bit, DMA, 1 MiB synchronous writes. About 20–40 MB/s sustained (I); the E-M5 measured about 28 MB/s (X). The highest stream today is about 3 MB/s | **No.** About 6–10× headroom |
| **Per-frame size limit** | W·H·3/8 per frame (V): 783 KB at 1920×1088, about 188 Mb/s at 30 fps | No |
| **Buffers** | 20 MiB AV heap; a 19-frame input ring (59.5 MB, V); output buffer about 1 s at the target rate (I). Overflow → RECMOVIE_BUFFER_LIMIT, and recording stops (V) | Only if the card stalls |
| **Encoder parameter check** | `cmp 24000000,d0; bhi reject` at 0x7EEA33CB (V): a peak above 24 Mb/s is refused. Also rejected: peak < average, < 1 fps, size < 64 | **Yes, in software.** 24 Mb/s = the AVCHD 1.0 ceiling |
| **Bitrate table** | MOV 1080 Fine/Normal 20/17 Mb/s, 720 13/10 (0x7E6EE4A2, V) | Yes, in software |
| **Rate control** | GOP 15 (the engine allows ≤ 60), no B-frames, max QP 51, and a second QP-like value of 20 whose role is unknown (V/I). If 20 is a QP floor, extra bitrate cannot buy quality below QP 20. On the Panasonic GH2 the encoder's default was a constant QP of 20 (X, confirmed on forum pages), so this may be the same parameter (I) | **Unknown, possibly the real quality ceiling** |
| **Encoder hardware** | Registers at 0x9940xxxx, not traced; profile, level and entropy mode unknown (no SPS template in the firmware) | **Unknown** |

## What bitrate cannot fix

- **The 1080 frame is upscaled.** The source is 1646×1296 effective (2304 ÷ 1.4, Q16 91750), stretched to 1920 (V). That alone explains much of the softness.
- **Readout:** HSHR, 2×2 over a 16:9 band at 30 fps (V). Whether the sensor skips lines or bins pixels is not visible in the bytes. Reviewers report moiré and strong rolling shutter (X).
- **Frame rates:** MOV is 29.97 fps only. There is no sensor record for 1080p60 (HSMR is a name with no record) and nothing for 24p (V).
- **AVCHD:** the AVCHD path is in the firmware but not offered on this body (X: official specs; V: set-up strings with no code reference).

## Next steps

1. **ffprobe one of your own E-PM2 MOV clips.** It gives the H.264 profile, level and entropy mode, and the real bitrate per GOP, which tells us how close the encoder runs to its target. No camera change is needed.
2. **Trace the role of the "QP 20" value and the HRD buffer fields** in the encoder set-up (0x7EEA57D4). The emulator can evaluate this set-up code.
3. **First test build, inside every existing check:** raise MOV 1080 Fine from 20 to 24 Mb/s in the table only. Gain: +20 %.
4. **Beyond 24 Mb/s:** raise the 0x7EEA33CB constant together with the HRD fields, then a camera ladder at 28 → 36 → 50 Mb/s, checking for RECMOVIE_BUFFER_LIMIT stops. The encoder hardware is the unknown.
5. **For image quality,** look at the ÷1.4 resize and the movie noise reduction (temporal reference, `kedge`) before bitrate.
