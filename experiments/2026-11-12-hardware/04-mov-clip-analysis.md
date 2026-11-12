# What a real E-PM2 movie shows about the encoder (2026-11-12)

**Clip:** `experiments/2026-11-09-film-portra/shots/PB120161.MOV`, sha256 `e9c17418b902720b…`. It is 17.8 MB, 1920×1080, 29.97 fps, 420 frames (14.0 s), recorded at MOV 1080 Fine.

**Method:** our own parsers in `scripts/`, run with `python3 -I`:
- `atoms.py` lists the boxes;
- `h264.py` decodes the avcC, SPS (including the scaling lists and the VUI/HRD) and PPS, plus the sample table;
- `qp.py` reads the slice header of every frame and computes QP = pic_init_qp + slice_qp_delta.

Usage: `python3 -I scripts/atoms.py CLIP atoms.pkl`, then `h264.py CLIP atoms.pkl params.pkl`, then `qp.py CLIP atoms.pkl params.pkl scripts/`.

## Encoder settings, read from the stream (V)

| Item | Value |
|---|---|
| Profile / level | **High (100) @ 4.1**: the level allows up to 62.5 Mb/s, 1.25 × 50 Mb/s for High |
| Entropy coding | **CAVLC** (CABAC not used) |
| 8×8 transform | **off** (`transform_8x8_mode_flag` 0) |
| Scaling lists | **custom 4×4 lists, in the SPS and repeated in the PPS.** Intra Y 7…38; intra Cb/Cr 7…50; inter Y 8…34; inter Cb/Cr 10…34. High frequencies are quantised hard, chroma most of all |
| Structure | I + P only, GOP 15, 1 reference frame, POC type 2, 1 slice per frame, frame_mbs_only (progressive) |
| HRD (VUI) | bit_rate 20,480,000 b/s, cpb_size 20,480,000 bits (**1.0 s**), VBR, for both NAL and VCL |
| Timing | 2002/120000 → 29.97 fps, fixed |

The scaling lists are **not** in block 0 as a plain table (bytes, 16- or 32-bit words, zigzag or raster). They probably come from the encoder hardware or microcode (I).

## What the encoder actually did (V)

- **Average 8.37 Mb/s.** Per-second rates range from 5.1 to 16.1 Mb/s. The declared target is 20.48 Mb/s, so the encoder used 41 % of it.
- **I-frames** average 74.8 KB (max 129.5 KB); **P-frames** 32.0 KB (max 98.0 KB).
- **QP is pinned at 20.** 27 of 28 I-frames and 391 of 392 P-frames are at QP 20. The exceptions are frame 1 (QP 25) and one P-frame (QP 22).

## Why: a QP floor in the encoder set-up

The encoder parameter builder writes the QP limits as bytes into its configuration (V):

```
7eea5a1a:  80 33        mov 51,d0
7eea5a1c:  f8 92 c8     movbu d0,(200,sp)     ; QP ceiling 51
7eea5a1f:  80 14        mov 20,d0             ; QP floor 20 (I, see below)
7eea5a21:  f8 92 c9     movbu d0,(201,sp)
```

The software rate control (0x7EEA6B37 / 0x7EEA726B) clamps QP to 51 (V).

**Why we read 20 as the floor (I, strong):**
- the clip never goes below QP 20 while using only 41 % of its bit budget;
- an initial QP alone would drift down when bits are plentiful;
- the GH2's Panasonic encoder had the same default constant QP of 20 (X, 01-public-sources.md).

**What follows:** at this setting the E-PM2 is not bitrate-limited. It stops spending bits once every frame reaches QP 20. Raising the bitrate table or the 24 Mb/s cap would change nothing on scenes like this one. Only scenes busy enough to need more than 20.48 Mb/s at QP 20 would push QP above 20.

## Levers, in order

1. **The QP floor:** the `80 14` immediate at 0x7EEA5A1F, so block-0 offset **0xA84A00** holds 0x14. A lower floor (16, 14, 12) lets rate control spend the existing 20.48 Mb/s budget. As a rule of thumb, −6 QP roughly doubles the bits. The HRD buffer and the bitrate target still bound the result. **The emulator can test it:** run the rate-control function with the stock and the lowered floor.
2. **More budget:** the bitrate table (0x7E6EE4A2) up to 24 Mb/s, within the existing check, and past that the 24 Mb/s check at 0x7EEA33CB. Only useful after lever 1.
3. **Not changeable as data:** CAVLC versus CABAC, the 8×8 transform, and the scaling lists. These are probably set by the encoder hardware; they are not found as tables.
4. **Bigger image-quality causes are upstream of the encoder:** the 1646×1296 source upscaled to 1920 (03-sensor-pipeline-memory.md).

**Caveat:** this is one short and fairly static clip. A busy scene (foliage, water, panning) would show whether QP ever rises above 20 at the stock settings.
