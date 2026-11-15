# Olympus M.ZUIKO DIGITAL 17mm F2.8

Date: 2026-11-15. Status: initial static assessment. No patch or flash.

## Finding

Firmware changes are worth investigating. A faster or quieter focus drive is
**unknown**, not proven. The motor control routines have not been identified.

## Stock image: verified

- Official [download page](https://support.jp.omsystem.com/en/support/imsg/digicamera/download/software/pana/dl/m_17_dl.html).
- [ZIP](https://support.jp.omsystem.com/en/support/imsg/digicamera/download/software/pana/panafw/m17/MZD17V11.zip):
  21,593 bytes; contains `OL100211.BIN`, 196,672 bytes, version 1.1.
- SHA256: `990d94c8578da7a1c041aa3c7300e78a5b4d0d0a8fe548b3c6acdb685d0be7dc`.
- The maker's [release notes](https://support.jp.omsystem.com/jp/support/cs/DI/fwdl/e1/mft/m_17.html)
  say v1.1 improves AF operation. They do not specify the algorithm or a noise change.
- A 32-byte `OL` header, 196,608-byte payload, and 32-byte trailer.
  Header load address: `0xFFFC0000`. Trailer repeats the first 28 header bytes.
  The sum of all little-endian 32-bit words is zero, with the payload as stored.
  The camera's permutation and inversion are not needed for this image.
- No extra signature block is present in this file. Lens-side acceptance checks
  are unknown.

## Code and data

**Inferred:** Renesas R32C instruction set. Fifteen aligned call stubs at payload
offsets `0x04` through `0x74` match `JSR.A; RTS; NOP; NOP; NOP`.
Their relative targets are inside the image. The encodings and displacement rule
match the [Renesas software manual](https://www.renesas.com/en/document/mas/r32c100-series-software-manual),
printed pages 97, 234, 256 and 266. The exact MCU part is unknown.

**Verified bytes:** populated pages are near offsets `0x00000–0x093FF` and
`0x28000–0x2AFFF`, plus a final non-FF byte at `0x2FFFF`. Much of the file is FF.
This is not proof of usable code space.

**Candidate references:** the bytes for `0xFFFE8800` occur at offsets `0x38DC`,
`0x38FA`, `0x7062`. The bytes for `0xFFFE9800` occur at `0x8479`, `0x84B7`,
`0x84F4`, `0x852F`. These correspond to data at payload offsets `0x28800` and
`0x29800` under the header's address map. Their purpose is unknown. Do not treat
them as motor tables without tracing their readers.

**Unknown:** the execution map. Some apparent calls inside the code point outside
the payload under the header's address map. Decode their callers and startup
copies before choosing a hook. This assessment does not include a full disassembly.

## Paths to test

| Candidate | Expected benefit: inferred | What must be established |
|---|---|---|
| Fewer camera-commanded corrections | Less hunting and fewer noisy movements | Log focus commands and correlate them with movement |
| Lens speed and acceleration profile | Different speed/noise balance | Trace focus command handler to motor output |
| Drive waveform or current | Possible reduction in noise during a single move | Identify driver hardware and its settings |

The camera map already has candidate speed and wobble interfaces:
[section 02, lens communication](../2026-11-08-feature-map/sections/02-lens-power-firmup-take.md).
Their names do not prove support in this lens. `ASKDATA` speed entries are queries;
they are not established writable speed settings.

## Next evidence needed

1. Complete the R32C decoder and runtime map. Trace a focus request from the
   communication handler to the driver. Separate focus from aperture control.
2. Record the installed lens version and a stock baseline: fixed camera and
   microphone positions, fixed light and target, 20 near-to-far and 20 far-to-near
   focus attempts. Keep still AF and movie AF separate. Measure focus time,
   failed locks, sharpness, sound peaks and total sound duration.
3. Change one identified control and repeat. Less sound with slower focus is a
   tradeoff; lower noise with equal or better time and accuracy is an improvement.

The downloaded package is published for Panasonic bodies. The E-PM2 lens updater
acceptance and recovery path need separate verification. Camera body recovery
experience does not establish lens recovery.

## Reproduce

Download the ZIP above and extract it into `out/`, then run from the repository:

```bash
python3 experiments/2026-11-15-lens-17mm/inspect_image.py \
  experiments/2026-11-15-lens-17mm/out/OL100211.BIN
```

The script verifies the stock hash, container checksum, and call stub patterns.
It does not write firmware.
