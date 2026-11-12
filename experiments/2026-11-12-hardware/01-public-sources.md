# E-PM2 hardware: public sources (2026-11-12)

The aim is to find what physical limits set the E-PM2's video bitrate and quality.

## Method and caveats (read first)

- The sandbox firewall blocked every direct page fetch: WebFetch and curl both got
  HTTP 403 "Approval required for <host>". This covered imaging-resource.com, dpreview.com,
  wikipedia.org, manualslib.com, support.jp.omsystem.com, cameramemoryspeed.com,
  personal-view.com and web.archive.org. Only github.com was reachable, and `gh` has no auth.
- So **every fact below comes from WebSearch result summaries, not from reading the pages.**
  Each URL is the page the search engine quoted. Check the key numbers against the pages
  once the hosts are approved (see "Open items").
- Labels: **[official]** = Olympus spec or manual, **[measured]** = a reviewer or tester measured it,
  **[teardown]** = chip or die analysis, **[community]** = forum, blog, rumour or wiki claim.

## 1. Official specs

### Cards
- SD, SDHC, SDXC and Eye-Fi cards are supported. The manual says "supports UHS-I". **[official]**
  https://manualshive.com/en/manual/olympus/e-pm2-1442/4252758?page=7 , https://www.manualslib.com/manual/504949/Olympus-E-Pm2.html?page=116
- Olympus recommends Class 6 or faster cards for movies. Eye-Fi "Endless mode" is not supported. **[official]**
  https://support.jp.omsystem.com/en/support/imsg/digicamera/qa/products/epm2/
- No source says which UHS-I bus mode the E-PM2 uses (SDR50 or SDR104). The later E-M5 II
  caps every UHS-I card below 40 MB/s, and the tester blames missing SDR104 support. **[measured, other body]**
  https://cameramemoryspeed.com/olympus-e-m5-ii/sd-card-comparison

### Movie formats (official) compared with our firmware

| Mode | Official E-PM2 / E-PL5 | Our firmware |
|---|---|---|
| MOV 1080 Fine | 1920x1080 30p (29.97), H.264, 20 Mb/s, about 22 min | 20 Mb/s |
| MOV 1080 Normal | 17 Mb/s, about 29 min | 17 Mb/s |
| MOV 720 Fine / Normal | 13 / 10 Mb/s | 13 / 10 Mb/s |
| AVI Motion JPEG | 1280x720 30 fps, 640x480 30 fps | - |
| AVCHD | **not offered** on E-PL5 / E-PM2 | 1080i peak 24, 720p 19.3 Mb/s |

- E-PL5 1080 Fine 20 Mb/s (22 min) and Normal 17 Mb/s (29 min), MOV (MPEG-4 AVC/H.264). **[official]**
  https://support.jp.omsystem.com/en/support/imsg/digicamera/qa/products/epl5/
- E-PM2 1080 30p 20/17 Mb/s, 22/29 min. **[official]**
  https://support.jp.omsystem.com/en/support/imsg/digicamera/qa/products/epm2/
- 720p 13/10 Mb/s. **[official, via a spec transcription]**
  https://www.dpreview.com/forums/threads/full-ep5-specs.3483844
- Both bodies record 1080 at 29.97p (30p) only. **[official / review]**
  https://old.imaging-resource.com/PRODS/olympus-epl5/olympus-epl5VIDEO.HTM
- E-PL5 has "no AVCHD", and clips are MOV files in DCIM. **[community]**
  https://www.eoshd.com/comments/topic/324-is-olympus-video-stupid
- The previous generation (E-PM1, TruePic VI too) had AVCHD: 1080 60i at 17 and 13 Mb/s,
  and 720 60p at 17 Mb/s. **[official]**
  https://manualshive.com/en/manual/olympus/e-pm1-1442/4252522?page=5
- **Inference:** our firmware's AVCHD code is most likely carried over from the E-P3/E-PL3/E-PM1
  platform. 24 Mb/s is the AVCHD 1.0 ceiling for 1080i; AVCHD 2.0 (1080/60p) allows 28 Mb/s.
  https://helpguide.sony.net/ilc/1530/v1/en/contents/TP0001093162.html , https://helpguide.sony.net/gbmig/45310731/v1/en/contents/TP0000241966.html , https://Www.Wikipedia.org/wiki/AVCHD
- The E-PM2 spec text still says "4GB (AVCHD), 2GB (Motion-JPEG)" for the file size limit,
  although the body has no AVCHD. This looks like a leftover from the older spec sheet. **[official, inconsistent]**
  https://manualshive.com/en/manual/olympus/e-pm2-1442/4252758?page=7

### Recording limits
- A clip stops at about 29 min, or at about 22 min in 1080 Fine. **[official]**
  https://support.jp.omsystem.com/en/support/imsg/digicamera/qa/products/epl5/
- A MOV file stops at 4 GB. The E-PL5 page states this. **[review]**
  https://old.imaging-resource.com/PRODS/olympus-epl5/olympus-epl5VIDEO.HTM
- Arithmetic check: 4 GB at 20 Mb/s is about 27 min, so at Fine the 22 min limit comes first.

### Buffer and continuous shooting
- Up to 8 fps with focus and exposure fixed and IS off. **[official, via dpreview]**
  https://www.dpreview.com/reviews/olympus-e-pm2
- 3.5 fps with tracking AF. **[measured]**
  https://imaging-resource.com/PRODS/olympus-epm2/olympus-epm2A6.HTM
- RAW buffer: 16 frames (IR), 15 RAW+JPEG (IR), 14 (Expert Reviews), 12 (Neocamera).
  **Sources disagree.** **[measured]**
  https://imaging-resource.com/PRODS/olympus-epm2/olympus-epm2A6.HTM , https://www.expertreviews.co.uk/digital-cameras/compact-system-cameras/52989/olympus-pen-e-pm2-review , https://www.neocamera.com/camera/olympus/epm2/review
- With the buffer full: about 1.78 fps RAW (IR) and 2.9 fps (Expert Reviews). The buffer cleared
  in about 9 s after 16 RAW frames on a 95 MB/s UHS-I card. RAW+JPEG clearing was slow. **[measured]**
  https://imaging-resource.com/PRODS/olympus-epm2/olympus-epm2A6.HTM
- Rough inference: a 16 MP RAW is about 14-15 MB, so 16 frames in about 9 s is roughly
  25 MB/s to the card. This is close to the E-M5's measured 28 MB/s cap (section 5).

## 2. The image processor (TruePic VI)

- Olympus names TruePic VI in the E-P3, E-PL3, E-PM1, TG-1, XZ-2, OM-D E-M5, E-PL5 and E-PM2.
  It was introduced with the E-P3 on 2011-06-30. **[official / community list]**
  https://www.engadget.com/2011/06/30/olympus-reveals-pen-e-p3-pen-e-pl3-and-pen-e-pm1-interchangeab/ , https://ipfs.ssi.eecc.de/ipns/en.wikipedia-on-ipfs.org/wiki/TruePic
- The E-PL5/E-PM2 use "the same 16-megapixel Live MOS sensor, processor and FAST AF system as the E-M5". **[review]**
  https://www.dpreview.com/reviews/olympus-pen-e-pl5-e-pm2
- "Dual core": reviews say the E-PL5's TruePic VI is "dual-core ... the same as the E-M5's".
  43rumors says it has separate processors for recording and for live view. Gizmodo's 2011
  headline says "dual cores". **Olympus's own wording was not found.** **[community]**
  https://www.dpreview.com/reviews/olympus-pen-e-pl5-e-pm2 , https://www.43rumors.com/?p=29006 , https://gizmodo.com/olympus-new-pen-e-p3-dual-cores-in-a-camera-yes-pleas-5816928/
- The architecture: Wikipedia says TruePic is "based on the Panasonic MN103 architecture" (also MN103S).
  Panasonic's Venus Engine is listed with the same base. **[community]**
  https://ipfs.ssi.eecc.de/ipns/en.wikipedia-on-ipfs.org/wiki/TruePic , https://wikimili.com/en/Image_processor
- A 2014 firmware hacker (lightsnowdev) reports that the E-M5 processor is a "Matshi-MN103"
  (Matsushita), and that "the other CPUs are unknown yet". **[community]**
  https://lightsnowdev.blogspot.com/2014/09/how-to-start-your-own-hacks.html
- MN103 is a Matsushita/Panasonic 32-bit line, mostly used in media processors, including digital cameras. **[community]**
  https://en.wikipedia.org/wiki/MN103
- The GH1's Venus Engine HD uses the "Panasonic AM32-4 MN103 processor". **[community]**
  https://www.eoshd.com/news/panasonic-gh1-firmware-hacked
- Wikipedia says the Venus Engine is based on Panasonic UniPhier. **[community]**
  https://en.wikipedia.org/wiki/Venus_Engine
- **Not found:** the manufacturer's part number, the process node or the core count of the TruePic VI die.
  No source says that Panasonic fabricates it, and no source says it is the same die as any
  Venus Engine. The evidence for a Panasonic-made SoC is the shared MN103 ISA together with
  our firmware's AM33 code and uITRON 4.0. That is consistent but indirect.
- **H.264 encoder:** no source gives the profile, the level or the maximum encoder bitrate for
  TruePic VI. The highest official figures for the platform are 20 Mb/s (MOV) and 24 Mb/s peak
  (AVCHD 1080i on earlier TruePic VI bodies, through the format's ceiling). The next platform,
  the E-M1 with TruePic VII, offers 24 Mb/s MOV Fine. **[official]**
  https://learnandsupport.getolympus.com/support/e-m1
- E-M5 frame-rate conflict: imaging-resource and photoreview describe E-M5 1080 as 60i
  ("60i from 30p capture"), while a spec transcription says 30p. The E-PL5/E-PM2 are 30p. **Sources disagree.**
  https://old.imaging-resource.com/PRODS/omd-em5/omd-em5VIDEO.HTM , https://www.photoreview.com.au/reviews/advanced-compact-cameras/interchangeable-lens/olympus-om-d-e-m5/

## 3. Teardowns and board photos

- **No public board-level teardown was found** for the E-PM2, E-PL5 or E-M5. No source names
  their SoC marking, DRAM part or size, IS MCU, HDMI transmitter or touch controller.
  - E-PL5/E-PM2 teardown query: no results. https://www.dpreview.com/reviews/olympus-pen-e-pl5-e-pm2
  - E-M5: iFixit has guides only for the E-M10 and E-M10 II (motherboard removal, with no chip IDs).
    https://www.ifixit.com/Guide/Olympus+OM-D+E-M10+Disassembly/75236 , https://www.ifixit.com/Guide/Olympus+OM-D+E-M10+Mark+II++Motherboard+Replacement/126254
  - ADV7511 + Olympus: no hits. Cypress PSoC / TrueTouch + E-PM2/E-PL5: no hits.
  - DRAM (Elpida/Samsung LPDDR): no camera-specific hits.
- IR-conversion guides open the body only to the sensor and filter stack:
  https://www.lifepixel.com/tutorials/infrared-diy-tutorials , https://savazzi.net/photography/e-pm2.html
- The only die-level analysis nearby is Chipworks on the **E-M1** sensor: a Panasonic sensor, code MN34231. **[teardown, other body]**
  https://old.imaging-resource.com/news/2014/02/10/olympus-om-d-em-1-sensor-is-made-by-panasonic-not-sony , https://www.photographyblog.com/news/chipworks_finds_panasonic_sensor_inside_e-m1
- An unverified 2012 claim (anonymous, through 43rumors) says that firmware tricks unlock
  "clean HDMI 4:2:2" and a debugger mode on the E-M5. 43rumors itself could not confirm it. **[community]**
  https://petapixel.com/2012/10/16/hacker-reportedly-finds-hidden-features-in-the-olympus-om-d-em-5/
- So our firmware-derived IDs (ADV7511-family HDMI, Cypress PSoC touch) are **not
  corroborated or contradicted** by any public source.

## 4. The sensor

- 16.1 MP effective (16.05 MP), Four Thirds (17.3 x 13 mm) Live MOS, the same as the E-M5. **[official / review]**
  https://www.dpreview.com/reviews/olympusem5 , https://zeroonevisuals.blogspot.com/2013/02/olympus-e-pm2-has-same-sensor-of-om-d.html
- **Who makes it:** Olympus president Hiroyuki Sasa said on 2012-07-02 that the E-M5 sensor is
  made by Sony. **[official statement, reported]**
  https://dc.watch.impress.co.jp/docs/news/544400.html , https://old.imaging-resource.com/news/2012/07/06/olympus-ceo-identifies-sensor-supplier-for-flagship-mirrorless-camera
- Before that statement, DPReview and sansmirror guessed it was Panasonic (G3-like). **Superseded.** **[community]**
  https://www.dpreview.com/reviews/OlympusEM5/11/ , https://sansmirror.com/newsviews/2012-newsviews/february-2012/olympus-goes-hindu-welcomes.html
- **The Sony part number is not public.** IMX109 or any other number is unconfirmed. No Chipworks E-M5 report was found.
- The GH3 shares the E-M5 sensor: this is a rumour and reviewer opinion, and Panasonic never confirmed it.
  The G5 uses an older Panasonic 16 MP sensor (a GH2 derivative), so it is a **different** sensor. **[community]**
  https://www.sonyalpharumors.com/?p=14377 , https://kimletkeman.blogspot.com/2012/11/olympus-om-d-e-m5-versus-panasonic-gh3.html
- **How video is read out:** no official or measured source. Reviewed.com says the E-M5 uses
  "pixel binning for HD downsampling" that "creates loads of moiré". Forum users guess line
  skipping or binning rather than oversampling as on the GH2. **[community]**
  https://www.reviewed.com/cameras/content/olympus-om-d-e-m5-digital-camera-review-updated , https://personal-view.com/talks/discussion/comment/191575
- Readout speed: no measured figure for the E-M5 or E-PM2. Reviewers note a "very intense rolling
  shutter" when panning on the E-M5. **[review]**
  https://camcorders.reviewed.com/content/olympus-om-d-e-m5-digital-camera-reivew
- The E-PM2 still images show "demosaicing errors and aliasing" and a "fairly weak" low-pass filter. **[measured]**
  https://www.imaging-resource.com/PRODS/olympus-epm2/olympus-epm2A5.HTM

## 5. Measured performance

### Card write speed
- **E-M5 (the same TruePic VI generation):** the maximum in-camera write speed is about 28 MB/s
  (best 28.6 MB/s), even with a 90 MB/s-capable SanDisk Extreme Pro. **[measured]**
  https://cameramemoryspeed.com/olympus-e-m5/fastest-sd-card-tests
- E-M10 (TruePic VII): about 32 MB/s. E-M5 II: UHS-I below 40 MB/s, and 82 MB/s with UHS-II. **[measured, later bodies]**
  https://cameramemoryspeed.com/olympus-e-m10/fastest-sd-card-tests , https://cameramemoryspeed.com/olympus-e-m5-ii/sd-card-comparison
- No E-PM2 or E-PL5 test was found on cameramemoryspeed. The index lists E-M1, E-M1 II, E-M5, E-M5 II, E-M10 and PEN-F.
  https://cameramemoryspeed.com/camera-tests
- **Inference:** 28 MB/s is about 224 Mb/s, more than 10 times the 20 Mb/s MOV rate. In video, the card
  interface is unlikely to be the first limit on a fast UHS-I card. Class 6 (6 MB/s, about 48 Mb/s)
  is the floor Olympus guarantees.

### Video quality
- E-PL5 (same pipeline as the E-PM2): "only mediocre video quality". Heavy compression artifacts at all
  resolutions, worst in 1080p with motion or pans. Motion JPEG is cleaner but shows obvious moiré. **[measured/review]**
  https://old.imaging-resource.com/PRODS/olympus-epl5/olympus-epl5VIDEO.HTM
- E-PM2 video looked "grainy and soft". **[review]**
  https://www.reviewed.com/cameras/content/olympus-pen-e-pm2-digital-camera-review
- IR's E-M10 review calls the E-PM2/E-PL5 video "very disappointing" by comparison. **[review]**
  https://old.imaging-resource.com/PRODS/olympus-e-m10/olympus-e-m10-field-test-part-iii.htm
- E-M5 moiré and aliasing were widely reported. The E-M1 (TruePic VII) was marketed with moiré reduction. **[review/community]**
  https://www.eoshd.com/news/new-olympus-e-m1-with-moire-reduction-but-no-24p
- E-M5 users say the codec "crashes" on foliage and water, and they asked for a higher bitrate. **[community]**
  https://personal-view.com/talks/discussion/comment/157537

## 6. Bitrate hacks

### Olympus
- **No released bitrate hack for any TruePic VI body was found.**
- lightsnowdev (2014) unpacked OM-D firmware with "oly_fw_tools", rebuilt an experimental E-M10
  firmware ("highly likely to brick"), and wrote a flashing tool that supports the E-P5, E-PL3,
  E-PL5, **E-PM2** and Stylus 1 (v0.4d, 2014-08-20). The author asked readers whether hacking
  the E-PM2 improved video quality, and no result was reported. **[community]**
  https://lightsnowdev.blogspot.com/2014/07/olympus-om-d-e-m10-firmware-hack.html , https://lightsnowdev.blogspot.com/2014/08/firmware-control-tool-to-flash-any.html , https://lightsnowdev.blogspot.com/2014/09/om-d-e-m5-firmware-experiment.html
- 0l.de documents the OM-D (E-M10) Wi-Fi protocol and internals. Nothing there is about bitrate. **[community]**
  https://0l.de/projects/omd/
- Forum claim: Vitaliy Kiselev said he would not work on OM-D hacks. **[community, unverified]**
  https://personal-view.com/talks/discussion/comment/157537
- Olympus pulled E-M5 firmware 1.2 after it bricked some cameras. This shows the risk of the flash path. **[review]**
  https://sansmirror.com/newsviews-2/newsviews/2012-newsviews/october-2012/from-11-to-12-to-11-to-15.html

### Panasonic GH1/GH2 (PTool, Vitaliy Kiselev), the closest public evidence
- PTool patched the GH1 and GH2 firmware (MN103-based Venus Engine) to change the encoder settings. **[community]**
  https://www.sansmirror.com/cameras/frequentely-asked-mirrorles/whats-this-hacked-panasonic.html
- The stock GH2 maximum was 24 Mb/s AVCHD (Cinema 24p). The early hack gave an average of 42 Mb/s
  1080/24p, "almost double" stock. **[official / community]**
  https://imaging-resource.com/PRODS/DMCGH2/DMCGH2VIDEO.HTM , https://www.eoshd.com/news/vitaliy-hacks-photographic-looking-42mbit-108024p-avchd-out-of-gh2
- Later patches: 44, 66, 88 and 100 Mb/s, then Driftwood's 176 Mb/s intra (GOP 1). **[community]**
  https://www.eoshd.com/news/gh2-gets-avchd-intra-at-176mbit/
- **Limits users hit:**
  - The card: 176 Mb/s stopped after about 10 s with "write speed" errors even on 95 MB/s cards.
    About 88 Mb/s worked on 45 MB/s cards. One user saw a ceiling near 130 Mb/s. **[community]**
    https://dvinfo.net/forum/panasonic-lumix-s-g-gf-gh-gx-series/513524-maximizing-driftwood-176mbit-hack.html , https://www.eoshd.com/comments/topic/791-gh2-unified-hack-88mbs-on-a-sandisk-extreme-45-mbs , https://www.personal-view.com/talks/discussion/comment/118203
  - Content: the measured bitrate varied from about 40 to 105 Mb/s with a 176 setting and never reached
    the target. High ISO and detailed scenes caused card errors. A shorter GOP (6) helped 100 Mb/s
    run reliably. **[community]**
    https://eoshd.com/comments/topic/462-simple-question , https://eoshd.com/comments/topic/1286-iso-setting-effects-write-speed-gh2
  - The encoder buffer: PTool exposed per-mode buffer limits ("Bottom Setting"). Going too far over
    the default frame limit caused buffer underruns and overruns. **[community]**
    https://personal-view.com/talks/discussion/comment/17160
  - Rate control: the quantizer (Q) and the matrices were patched separately from the bitrate
    (for example, Driftwood set Q=13 on all modes). Bitrate alone did not set quality. **[community]**
    https://personal-view.com/talks/discussion/comment/43279
  - GH1: an "overall bitrate" parameter was found to control the card controller's peak write rate
    rather than the encoder bitrate. Two patches were needed for the AVCHD settings to take effect.
    Patches ran to 75 and 110 Mb/s GOP-1. **[community]**
    https://www.eoshd.com/?p=3463 , https://www.dvxuser.com/threads/75mbps-gh1-peak-reliability-patch-v2-update.257237/
  - Very high-bitrate AVCHD files may not play back in the camera. **[community]**
    https://www.dvxuser.com/threads/75mbps-gh1-peak-reliability-patch-v2-update.257237/

## Summary of the physical limits (inference from the above)

1. The card bus is not the first limit. The E-M5-generation write speed is about 28 MB/s (about 224 Mb/s),
   against 20 Mb/s stock. The GH2 experience suggests that the real sustained card speed and the
   peaks (I-frames, high ISO, detail) fail first once the rate goes above about 1/2 of the card speed.
2. The encoder's own maximum (profile, level, VBV size) is undocumented for TruePic VI. GH1/GH2
   (MN103 Venus Engine) encoders ran at 4-7 times their stock rate, but they are a different
   encoder block, so that headroom does not transfer automatically.
3. Readout (binning or skipping) and the weak low-pass filter cause moiré and aliasing that no bitrate can fix.
4. The 4 GB MOV file limit and the 22/29 min clip timers cap the clip length. 4 GB lasts about 27 min at 20 Mb/s,
   about 13 min at 40 Mb/s and about 5 min at 100 Mb/s.

## Open items (need fetch approval or hardware)

- Approve the hosts in the sandbox (`sbx policy approval ls`) and re-read the IR, dpreview and Olympus
  pages, to replace the search-summary citations with direct quotes.
- Profile, level and GOP: run `ffprobe`/`mediainfo` on our own E-PM2 MOV clips (no public source has them).
- Board IDs (SoC, DRAM, ADV7511, PSoC, IS MCU): only a physical teardown of our own body will settle them.
