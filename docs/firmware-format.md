# E-PM2 firmware format

The file is `OLY_E_101_<ver>_0000_0000.BIN`, 43,319,360 bytes. It holds four "OE" blocks followed by an opaque tail.

## OE block

| Offset | Size | Field |
|---|---|---|
| 0 | 2 | `OE` |
| 2 | 2 | model, bytes `10 10` (E-PL5: `10 00`) |
| 8 | 4 LE | container load address |
| 12 | 4 LE | payload length (a multiple of 16) |
| 16 | 2 LE | internal build |
| 20 | 2 LE | kind |
| 32 | len | scrambled payload |
| 32+len | 32 | trailer: header[0:28] + checksum word |

- **Scrambling:** each 16-byte group of the payload is permuted with `LANES = (1,3,0,2,6,4,7,5,11,10,9,8,13,14,12,15)` (decoded byte `o` comes from encoded byte `LANES[o]`), and every byte is XORed with 0xFF.
- **Checksum:** the sum of all little-endian u32 words of header + **decoded** payload + trailer is 0 mod 2^32. There is **no signature**.

## E-PM2 v1.6 blocks

| # | Kind | Addr | Length | Contents | Same across v1.1–v1.6? | Same as E-PL5 v1.6? |
|---|---|---|---|---|---|---|
| 0 | 0x100 | 0x402C0000 | 14,155,712 | main code (MN103, uITRON); runtime base 0x7E421020 (verified, see experiments/2026-11-08-disassembly) | no | no |
| 1 | 0x101 | 0x43C40000 | 22,937,536 | languages and fonts (UTF-16LE string tables, one per language) | yes | **yes** |
| 2 | 0x106 | 0x45220000 | 2,490,304 | "ARTFIL": 6-bit noise texture for the Grainy Film art filter | yes | yes |
| 3 | 0x104 | 0x45480000 | 3,669,952 | "FRAME": 8 JPEG frame overlays, one per aspect and size | yes | yes |
| tail | `OM` | — | 65,600 | Renesas H8 firmware of the image-stabiliser controller ("BC") | yes | model ID + checksum differ |

## Useful locations (v1.6)

- Block 0 at 0x3250xx: the `[firmup]` updater strings and `DCOLYMP`. At 0x324d88: the pattern table `S101????BIN … E101????BIN … E100????BIN …`.
- Block 0 at 0x2CCEC0 and 0x2CCF00: `mov 7200,a3` and `mov 1740,a3` in the movie recording-limit routine (0x2CCDE8–0x2CCF7C; confirmed from the code).
- Block 1, English table near 0x379000: menu labels such as "Pixel Mapping" (0x37928a).

## Provenance

See [../firmware/README.md](../firmware/README.md) and [verification.md](verification.md).

Block contents and the updater's checks: see [firmware-map.md](firmware-map.md) and `experiments/2026-11-08-feature-map/sections/02-*.md`, `08-*.md`.
