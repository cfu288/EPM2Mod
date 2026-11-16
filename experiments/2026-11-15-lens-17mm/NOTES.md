# Olympus 17mm F2.8: focus drive

Updated: 2026-11-16. Static tracing and a limited execution model. No lens flash.

## Result

There are concrete speed and drive-level controls in this firmware. Two separate
one-byte proposals have measured effects on the words sent to the driver:

| Proposal | Software result at ADC 400 | Physical result |
|---|---|---|
| Faster in the highest ADC bucket | Timing field 46 → 43; same drive word, direction and count | Unknown; about 7% higher programmed steady rate, not measured AF improvement |
| Lower drive in the highest ADC bucket | Register-13 field 320 → 256; same timing, direction and count | Unknown; possible less noise, with possible loss of torque |

These are proposals evaluated in memory, not flashable builds. Speed, sound,
settling and missed steps must be measured on the lens. Do not combine the two
for the first hardware comparison.

## Stock image and sources

Official [download page](https://support.jp.omsystem.com/en/support/imsg/digicamera/download/software/pana/dl/m_17_dl.html)
and [ZIP](https://support.jp.omsystem.com/en/support/imsg/digicamera/download/software/pana/panafw/m17/MZD17V11.zip).
The [release notes](https://support.jp.omsystem.com/jp/support/cs/DI/fwdl/e1/mft/m_17.html)
say v1.1 improves AF operation, without naming the change.

OL100211.BIN: 196,672 bytes. SHA256:
990d94c8578da7a1c041aa3c7300e78a5b4d0d0a8fe548b3c6acdb685d0be7dc.

Verified: 32-byte OL header, 196,608-byte payload, 32-byte trailer. Header address
0xFFFC0000. The raw little-endian u32 sum is zero. Camera-style scrambling is not
needed. No extra signature block is present; lens acceptance checks are unknown.

The decoder follows the [Renesas R32C software manual](https://www.renesas.com/en/document/mas/r32c100-series-software-manual).
Its tests also use actual assembler output from
[jbkim/R32C-Web-Server](https://github.com/jbkim/R32C-Web-Server/blob/master/Webserver/Debug/ncrt0.lst).
Continuous instruction decoding, branch targets and peripheral addresses now
support R32C. The exact chip is unknown. Renesas's
[R32C/111 comparison](https://www.renesas.com/en/document/apn/differences-between-m16c29-and-r32c11164-pin-ver)
places ADC result AD00 at 0x380, the address sampled here.

The earlier instruction conflicts were decoder errors: 67 is BTST:S, 23 is JNE,
and 3F 31 starts EXTZ.BL. They do not establish encryption or an unknown ISA.

## Evidence and limits

- r32c.py: partial instruction decoder. Unsupported instructions stop the walk.
- flow.py: branches, calls and seven bounded switch tables from 90 entry stubs.
  Result: 11,313 instructions, 32,763 bytes, 21 unsupported points, no overlaps.
  This is coverage of those entry paths, not proof every byte is code.
- leaf_machine.py: executes selected driver-programming routines from the image.
  It is not a complete R32C MCU emulator.
- Explicit hooks: ADC routine 0x650 returns a supplied sample; serial writer
  0x6CA4 records its input word and returns R2R0 = 1; delay 0x6E88 is omitted.
- probe_model.py: 96 executions over four variants, four ADC samples, three move
  lengths and two directions. The changes exist only in memory.
- test_research.py: nine tests pass. Checks include independent encoding examples,
  operand order, an independent timing calculation, proposal scope, the ADC
  boundary, the low-ADC inhibit, and the E-PM2 focus-command link.

No physical timing, acoustic output, torque or achieved focus accuracy was tested.

## Traced focus path

All lens addresses below are **payload offsets**, not established execution
addresses. Add 32 for a byte's position in the BIN.

The E-PM2 independently identifies these focus commands. Its table at 0x7E741368
uses key = focus mode + 1:

| Body focus mode | Body handler | Command byte | Lens handler |
|---|---|---|---|
| PLS_ABS, mode 2 | 0x7E52D3D4 | A2 | 0x3CD8 |
| DST_ABS, mode 3 | 0x7E52D3DF | A3 | 0x3D60 |
| PLS_OFST, mode 4 | 0x7E52D3EA | A4 | 0x3E14 |

The body writes A2/A3/A4 into its request buffer. The lens dispatcher at 0x3BE4
tests the command at RAM 0x539 and calls these handlers. This identifies focus,
rather than aperture, without relying on a guessed table name.

The absolute pulse path is:

~~~text
A2 → 0x3CD8 → 0x5820 → 0x5988 → 0x59D0
                                  ├─ 0x5D44: ADC-based inhibit
                                  ├─ 0x5CC8: timing floor and drive field
                                  ├─ 0x5D74: timing/profile words
                                  ├─ 0x5E78: movement count
                                  └─ 0x6CA4: serial word output
~~~

Verified RAM use: 0x530 receives the requested position; 0x560 is updated by
motion accounting; 0x604/0x606 are checked as travel bounds; 0x565 selects the
sign of position updates; 0x5FC is the timing parameter; 0x5DC is the ADC sample.

0x5E78 multiplies the requested movement by 32 and sends its low and high 10-bit
portions with prefixes 0x0400 and 0x0800. That proves the firmware's count
conversion, not the motor's physical microstep mode. 0x6CA4 sends the high byte
and then the low byte of a word. The movement sequence ends with 0x3E00 and
a busy wait. Its role as start is inferred; the driver datasheet is not identified.

## Timing and acceleration

0x59EF writes 333 to RAM 0x5FC. 0x5CC8 can raise it before 0x5D74 programs the
driver. Changing 333 alone therefore does not always change the selected timing.

0x5D74 computes ticks = floor(min(timing, 32767) × 130208 / 1000000).
Below timing 1667, it starts one field at 217, writes the final tick value to
another, and derives three intermediate values by repeated halving of their
difference. At timing 1667 or above, five timing fields receive the same value.
The acceleration interpretation is inferred; the values and branches are verified.

For timing 333, the modeled serial words are:

~~~text
0CD9 242B 1882 1C57 2042 1290 1480 2830
~~~

The driver chip, clock and physical units remain unknown. The parameter looks
like a time value; these notes do not equate it to a measured pulse period.

## ADC-dependent limits and drive field

0x650 takes six ADC readings, drops the minimum and maximum and averages four.
0x5D44 inhibits this path at samples ≤186, with clearing at ≥210. Supply-voltage
compensation is inferred; volts per ADC code are unknown.

| Payload offset | Verified use |
|---|---|
| 0x2AE00 | ADC bucket count: 4 |
| 0x2AE01 | Thresholds: 377, 301, 237 |
| 0x2AE0F | Timing column count: 12 |
| 0x2AE10 | Values: 1667, 1250, 1000, 833, 714, 625, 556, 500, 455, 417, 357, 333 |
| 0x2AE28 | Lowest timing column per bucket: 10, 10, 9, 6 |
| 0x2AE30 | Four rows of 12 drive-field codes |

0x5CC8 chooses a timing column, reads a byte from the corresponding row, shifts
it left six bits and ORs it with 0x3400 before serial output. It is a drive-level
candidate; the electrical meaning of those bits needs verification.

Stock modeled results for a 100-unit positive move:

| ADC | Selected timing | Final timing field | Drive word |
|---|---|---|---|
| 400 | 357 | 46 | 3540 |
| 320 | 357 | 46 | 35C0 |
| 250 | 417 | 54 | 3640 |
| 220 | 556 | 72 | 36C0 |

## Concrete proposals

| Proposal | Payload offset | File offset | Old → new | Modeled effect |
|---|---|---|---|---|
| fast-high-adc | 0x2AE28 | 0x2AE48 | 0A → 0B | Only ADC >377: timing 357 →333; same drive word |
| lower-drive-high-adc | 0x2AE3A | 0x2AE5A | 05 →04 | Highest bucket at stock fast column: 3540 →3500 |
| timing-400 | 0x59F2 | 0x5A12 | 4D01 →9001 | ADC 320/400: 357 →400; ADC 220/250 unchanged |

The fast proposal selects an existing column whose drive code remains 5 in the
highest ADC row. **Do not extend it blindly to other rows:** the next column in
the second row is zero. The stock limits may reflect a real torque or resonance
constraint. Only a lens test can establish the margin.

The lower-drive proposal changes the field code by 20%, not necessarily current
or sound by 20%. Check stalls, lost position and focus accuracy. The slower
proposal is a separate noise/settling experiment, not a speed improvement.

## Tables that should not be used as speed controls

0x8464 reads 0xFFFE9800 + 32 × row + 2 × column and computes a reciprocal using
focus position. 0x84DC implements the inverse conversion. The DST_ABS handler
calls these. This is a distance/position conversion table, not the demonstrated
driver timing table.

## What remains before a lens test

1. Identify the driver chip and its bit meanings from a readable board image and
   datasheet. Noise may come from excitation, gears, repeated corrections, or a mix.
2. Verify lens-update format handling and recovery on the E-PM2. The production
   builder accepts OE body images, not this OL lens image. The official package
   here is published for Panasonic bodies. No flashable lens build is offered.
3. Record the installed lens version and a stock baseline. Fix the light, target,
   microphone position and camera position. Repeat 20 near-to-far and 20 far-to-near
   moves. Measure focus time, failures, sharpness, sound peaks and sound duration.
4. Compare one proposal at a time, with the same target and direction sequence.
   Separate still AF, movie AF and manual focus. Physical tests decide improvement.

Calls outside the update image remain unresolved. flow.py reports them; they do
not justify inventing a ROM alias or assuming lens recovery from body recovery.

## Reproduce

Extract the official ZIP into this experiment's out/ folder. From the repository:

~~~bash
python3 experiments/2026-11-15-lens-17mm/inspect_image.py experiments/2026-11-15-lens-17mm/out/OL100211.BIN
python3 experiments/2026-11-15-lens-17mm/flow.py experiments/2026-11-15-lens-17mm/out/OL100211.BIN --out experiments/2026-11-15-lens-17mm/out/flow.json
python3 experiments/2026-11-15-lens-17mm/probe_model.py experiments/2026-11-15-lens-17mm/out/OL100211.BIN > experiments/2026-11-15-lens-17mm/out/probe-results.json
python3 experiments/2026-11-15-lens-17mm/test_research.py
~~~

None of these commands writes modified firmware.
