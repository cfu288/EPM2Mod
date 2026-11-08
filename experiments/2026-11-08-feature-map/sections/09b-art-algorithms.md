# 09b. Hidden art-filter algorithms: Composite, Watercolor (pastel_art), Star light, Pin Hole III

Source: E-PM2 v1.6 block 0, runtime = 0x7E421020 + offset. Labels: **verified** = read in the code or bytes;
**inferred** = a reading of what the code means, not proved. In this file, `udf00/udf01/udfu01` are read as
multiply. That reading is a strong inference from several sites, and every formula with `*` below depends on it.

Terms: `req` = the art request (pass argument a0). `ctx` = the persistent art object (pass argument a1;
`art_call_filterfunc` 0x7E72A997 passes obj+4 to every slot). In ctx, +8 = req, +12 = done mask,
+28/+32 = module buffers, +36 = **current image** (the output of the previous chain stage).

## 1. Composite (menu 118, code 153) = "Fragmented" (Magic Filter) — single-image tile scatter

**Correction to the brief (verified):** the source pointer is `ctx+36`, not `req+36`.
- `art_set_filter` 0x7E72A443 sets `ctx+36 = req+56` (the input image). Later stages overwrite it with their output.
- pass 2 0x7E7272A9 sets `ctx+36 = req+76` after the kernel runs.
- So the kernel reads the **current image** and writes the **output buffer** `req+76`. It does not blend two
  photos. There is one source image.

**Hypothesis "118 = Fragmented": supported (inferred from the algorithm).** The kernel cuts the image into a
grid, shrinks and jitters each piece, gives it a random soft mask and a random mode, and pastes the pieces in
random order onto black.

**CompositeData record** (`art_composite_set_CompositeData` 0x7E7274AB, verified):
+0 src = ctx+36; +4 dst = req+76; +8 mask buffer (art_buff_alloc, line 365); +12/+14 = W,H (req+80/+82);
+16 = stride = 2W; +20 = req+96 (byte). The buffer size is `w*h*4*2`, with (w,h) from table 0x7E74A518[req+96].

Table 0x7E74A518 (verified): idx0 128×96, 1 128×96, 2 128×86, 3 128×72, 4 96×96, 5 120×96, 6 112×96,
7 116×96, 8 128×92, 9 72×96. **Inferred:** req+96 is the **aspect-ratio code** (1=4:3, 2=3:2, 3=16:9, 4=1:1, 9=3:4).
So the kernel test "(100,sp)==3" means "16:9 aspect".

**Pass table 0x7E85A6D4 (verified):**
1. 0x7E727174: if req+0 is 3 or 4, it marks passes 2+3 done (skipped).
2. 0x7E7271F7: allocates the record (0x7E5072ED, then memset 24), calls set_CompositeData, then `art_cpu_exec(5, 0x20000)`.
3. 0x7E7272DA: frees the mask buffer, the record, and also req+56 when req+0==1.
4. 0x7E72738C: no work.

**Kernel 0x7E547A7A (verified, via art_cpu_sub_exec 0x7E722914 with a0 = record):**
```
seed = clock()[6]            // 0x7E5083B5 = local date/time (tz*60 adjust); byte 6 likely seconds (inferred)
rng_state(0x60504140) = seed
fill(dst, W,H, Y=0,Cb=128,Cr=128)          // 0x7E55EBF6 -> image-engine op 30 (fill); black (inferred from YCbCr)
for i in 0..3: make_mask(i, buf+i*128*96*2, 128,96)   // always table idx 1, NOT req+96
if aspect==3: cols,rows=16,9; Hused=W*9/16 else cols,rows=8,6; Hused=H
top=(H-Hused)/2; cw=stride/cols (bytes); ch=Hused/rows
order = FisherYates(0..cols*rows-1)        // loop 0x7E547C19, rand%(k+1) swap
for t in order:
   m    = rand % 4                          // which mask
   mode = [6,7,8,5][rand & 3]               // desc+284; meaning unknown (rotation/flip? blend?)
   tw = cw - cw/8 + rand%(cw/8);  th = ch - ch/8 + rand%(ch/8)      // 87.5..100 % of the cell
   x = (t%cols)*cw;  y = (t/cols)*ch + top
   x' = x - cw/16 + rand%(cw/8);  y' = y - ch/16 + rand%(ch/8)       // jitter ±1/16 cell
   clamp x,x' to [0,stride-tw]; y,y' to [top, top+Hused... H-top - th]  // 0x7E547A67
   imgop21(src=src+y*stride+x, size cw×ch, dst=dst+y'*stride+x', size tw×th,
           mask=masks[m] 128×96, mode)      // 0x7E548351 -> 0x7E544BB5
```
- **Verified:** the RNG 0x7E54594F is xorshift32 (`x^=x<<13; x^=x>>17; x^=x<<5`), and a state of 0 becomes 1.
- **Verified:** op type 21 (desc+194) is the same image-engine job that `[movp]copy` 0x7E6E3161 uses. So it is a
  copy/resize job. **Inferred:** the extra fields (desc+64 mask pointer, 128/96 at desc+183/184, desc+275=153,
  desc+238..248=128) turn it into a masked (alpha) resize-paste. The result is that each piece is shrunk slightly
  and pasted with a soft edge.
- **Masks (`make_mask` 0x7E548626 → 0x7E54846F, verified).** Each mask is radially symmetric:
  r² = dx²·k + dy²·k, with k = 1625702400/((w/2)²+(h/2)²). This puts the corner at profile index ≈24.2.
  The code interpolates a 64-entry profile (knots i<<18), adds 7, and saturates at 1031. Values are written in
  4-fold mirror, in an 8-row interleaved layout.
- **Mask profiles (verified):**
  - mask 0 (0x7E74C1F0) = all 1024: a hard rectangle.
  - mask 1 (0x7E74C270): 709 at idx15, 190 at idx24.
  - mask 2 (0x7E74C2F0): 52 at the corner.
  - mask 3 (0x7E74C370): 0 at the corner.
  - So masks 1–3 are Gaussian-like vignettes that get stronger from 1 to 3.
  - A 5th profile at 0x7E74C3F0 is used by the other callers (0x7E5485E8 / 0x7E5486B4).
- **Possible bug (verified arithmetic; the consequence is inferred).**
  - The buffer is sized from table[req+96], but the kernel always writes 4×128×96×2 = 98,304 bytes.
  - For 16:9 (idx3) the buffer is 73,728 bytes, and for 1:1 it is also 73,728. That is an overflow, unless
    art_buff_alloc rounds the size up.
- **Verified:** `art_chk_type` 0x7E71C0E1 accepts 151/153 only when req+2==3 (block 0x7E71C1BA). They are
  rejected for req+2==1, 2, 4 and 5.

## 2. Pastel Art (menu 120, codes 181/182) = shipped **Watercolor I/II**

Module 0x7E7275D4, pass table 0x7E85A998 (verified). The work record W (16 bytes, at ctx+32) is
{+0 src YC, +4 developed YC, +8 branch-A out, +12 branch-B out}.
Helpers: `img_ctrl` = `art_get_img_ctrl_addr` 0x7E728639. P = img_ctrl+96 = the parameter block.
`art_set_img_ctrl_param` 0x7E728A02 is generic. It copies req+92..167 (tone/colour fields of the request) into
P, and it copies **req+6 (code) into P+79**. It contains no per-filter constants.

| # | fn | What it does (verified unless marked) |
|---|---|---|
| 1 | 0x7E727645 | Allocates W and sets W+0 = ctx+36. Chooses which passes run (masks below). |
| 2 | 0x7E727797 | RAW develop. Uses bayer size and set_ctrl_bayer, with P+90=7 and desc type 4. The output goes to W+4 (w*h*2). Calls `art_nr_create_param` 0x7E72AFA1; the NR object is stored at 0x605C0C6C[req+42]. Runs it (flag 0x20000). |
| 3 | 0x7E72799a | Runs NR stage 2 (NR object +196), flag 0x40000. |
| 4 | 0x7E727a38 | Alternative develop into W+4 with **art_set_DT** 0x7E729149 (P+90=7). It is skipped if an NR object exists. |
| 5 | 0x7E727c54 | Runs NR object +588 (stage 3), flag 0x100000. |
| 6 | 0x7E727cf3 | **Branch A**: W+0 → W+8, op 21, **P+89 = 11 (I) / 13 (II)**, P+90 = 6. |
| 7 | 0x7E727ea0 | **Branch B**: frees NR YC, then W+4 → W+12, op 21, P+90 = 8. It has the same requirement mask as pass 6, so the two can run in parallel. |
| 8 | 0x7E72803d | **imgdma merge** of W+8 and W+12 into req+76. Parameters +12=0x10000000, +32=256, +34=0xFF00, +37=0. Frees W+4 when req+0==1. Allocates req+76 if it is null. |
| 9 | 0x7E72820e | Short path: W+0 → req+76 in one op, **P+89 = 10 (I) / 12 (II)**. |
| 10 | 0x7E728338 | Frees buffers (art_pastel_art_free, stl2ycc_free_yc). Sets ctx+36 = req+76. |
| 11 | 0x7E7283eb | No work (finalize; logs and sets its done bit). |

**Pass selection in pass 1 (verified masks):**

| Request | Mask | Passes that run |
|---|---|---|
| req+0==1, req+4==1 | 0x1110000 | 2,3,4,6,7,8 |
| req+0==1, req+4==2 | 0x1010000 | 2–8 |
| req+0==1, other req+4 | 0x1170000 | 4,6,7,8 (DT develop, no NR) |
| req+2==2 | 0xFF0000 | only 9 |
| req+0==2, req+4 in 6..9 | 0xFF0000 | only 9 |
| req+0==2, other req+4 | 0x11F0000 | 6,7,8; W+4 = req+60 |
| req+0==3/4 | 0x3FF0000 | nothing (pass 11 only) |

```
A = isp(current_YC, preset = I?11:13, stage 6)
B = isp(develop(RAW, strong NR or DT), stage 8)
out = imgdma_merge(A, B, w=256, mask=0xFF00)   // inferred: per-byte select/mix, e.g. Y from one, C from other
```
- **Watercolor I vs II (verified):**
  - Inside the module, the only difference is the preset index P+89: 11/13 in pass 6 and 10/12 in pass 9.
  - In the image-engine driver, codes 181/183 and 182/184 take separate paths at 0x7E5659EB (in fn 0x7E565598),
    0x7E566813 and 0x7E56826A/0x7E5689A6 (in the 13 kB fn 0x7E566C94). 183/184 are inferred to be the
    movie/other variants.
  - I dumped one table set from the first path (I: 0x7E765EBC/ED4/EE0, 0x7E765F1C…; II: 0x7E765F7C…, 0x7E765FDC…).
    The I and II tables are **identical and flat**: 12×1023, 12×64, 12×0.
  - So the real I/II difference is in the P+89 presets and in fn 0x7E566C94. Neither has been decoded.
- **Comparison (verified pass/callee shapes):**
  - **Key Line** (table 0x7E859E90, 13 passes): an op+fill pass, a free pass, then develop with **set_DT** (pass 4,
    the same as Watercolor pass 4). Then two parallel ops (7/8), an imgdma merge (9), and two post-merge ops (10/11).
    Its P+89 preset is 8 and P+90 is 3.
  - **Dramatic Tone** (table 0x7E859584, 12 passes): four ops, a **CPU kernel** (pass 6 cpu_exec), then DT+NR (7),
    then three ops.
  - Watercolor has the same topology as Key Line: develop → two branches → imgdma merge.
  - **Inferred look:** a colour/tone-preset version of the photo, merged with a heavily smoothed (NR) second
    develop. This fits a "soft wash" watercolour, with the second branch possibly giving soft edges or lines.
    It is not a CPU effect.
- **Complete, not stubbed (verified):** passes 1–10 all do real work. Pass 11 is the normal empty finalize pass;
  Composite pass 4 and Key Line pass 13 are the same kind.

## 3. Star light as a stand-alone filter (code 118, menu 115 ≈ "Sparkle")

- **Verified:** the filter hash entry for 118 (table 0x7E85C45C, key 0x2E) → case 0x7E72A635 → 0x7E71E705. This
  is the **same entry** that `art_set_func_effect` installs for effect flag 0.
- The only difference in the chain is the slot state byte: **2 for a filter slot** (0x7E72A665) and **3 for an
  effect slot**.
- **Verified:** the star module range 0x7E71E705–0x7E72032F contains no compare with 118. Its `(6,aX)` reads are
  size fields of records, not the request code.
- **Verified:** for 118, slot 0 is the normal `art_stl2ycc`, not stl2ycc2.
- **Verified:** I searched the image-engine driver (0x7E54xxxx–0x7E56xxxx) for compares on P+79. It branches
  on 96/97/165/166, 151/152 and 181–184. It does **not** branch on 118.
- **Inferred:** the filter configures nothing different. "Crystal/Sparkle" = the base picture + the star effect,
  and no extra base look is applied in code. Any base look would have to come from request tone fields
  (req+92..167) that the camera side fills. `rec_art_set_artmode` has not been traced.
- **Open:** whether code 118 together with effect flag 0 runs the module twice.
- **Verified:** `art_chk_type` accepts 118 for req+2 = 1 and 3, but not 2.

## 4. Pin Hole III (code 108) vs I/II (73/106)

- **Verified:** 73, 106 and 108 all go to case 0x7E72A615 → `art_effect_20_pinhole` 0x7E720332.
- **Verified:** no art code tells them apart. Every compare treats {73,106,108} as one group: `art_chk_type`
  0x7E71C132…, and `art_set_func_effect` 0x7E72A743, which drops the pinhole effect for these codes.
- **Verified:** the only other `cmp 108` sites are a numeric threshold at 0x7E551E93 and printf `%l` at 0x7F0A3479.
- **Pinhole module (verified):**
  - The gain map is made by **CPU kernel 3** (`art_cpu_exec(3, 0x20000)` in pass 2 0x7E720441) on the MAIN TASK.
  - The map size comes from table 0x7E550BB4, indexed by req+96 (modes 1/2/3/8/9) or by constants 1/3 (modes 4/5/7).
  - The map is cached in ctx+28: it is computed once and then reused.
- **Inferred:** the I/II/III differences are not in code compares. They must come from (a) the request tone/colour
  fields filled by the camera side, (b) the request fields the kernel-3 gain-map code reads (vignette strength), or
  (c) code-indexed parameter tables in the image engine through P+79.
- **Open:** decode kernel 3. It is reached through 0x7E729E59 and was not read. Also trace `rec_art_set_artmode`
  0x7E70E222 for 108.

## Open questions
1. Composite desc+284 modes 5–8: rotation/flip or blend mode? Find the image-engine consumer of desc+284, which
   only 0x7E548351 and 0x7F0687C4 write.
2. Does the composite mask buffer really overflow for 16:9 and 1:1? Check how art_buff_alloc 0x7E7293DE rounds sizes.
3. Watercolor presets P+89 = 10–13: find the table that P+89 indexes in the image-engine driver. Decode the
   181/182 branches in fn 0x7E566C94.
4. imgdma merge parameters (+32=256, +34=0xFF00): read `art_set_imgdma_ctrl_param` 0x7E728E14 and the IMGDMA
   driver to confirm Y/C select vs mix.
5. What req+0 (1..4), req+2 and req+4 mean (still/live-view/movie, RAW source type?). They decide which passes
   run, and live-view types 3/4 skip both Composite and Watercolor work.
