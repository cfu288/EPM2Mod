# E-PM2 hardware: public sources (2026-11-12, page-checked)

The aim is to find what physical limits set the E-PM2's video bitrate and quality.

## Changes after page checks

1. **Our 1080 and 720 MOV rates match Olympus.** Olympus's own E-PM2 table gives 20/17/13/10 Mb/s, all 30p (29.97).
2. **The MOV file limit was wrong.** It is "4 GB or 29 min" for MOV and 2 GB for Motion JPEG. The draft's
   "4GB (AVCHD)" came from a manual mirror that I could not open; Olympus's table does not say it.
3. **The AVCHD history is corrected.** The earlier TruePic VI bodies (E-P3, E-PL3, E-PM1) record AVCHD: on the E-P3,
   1080 60i at 20/17 Mb/s and 720 60p at 17/13 Mb/s (IR, average rates). The draft's E-PM1 figures (17/13 and 17) are unverified.
4. **The E-M5 records 1080 60i in MOV**, "from 30 frames per second sensor output". It is not 30p and not AVCHD.
   The E-PM2 and E-PL5 record 30p.
5. **New: Olympus says the E-PM2 is "UHS-I compatible"**, and IR lists "UHS Support: UHS-I".
6. **New: the E-M5 card write limit is 28.6 MB/s.** Even a 45 MB/s card reaches 26.6 MB/s, so the camera is the limit.
7. **New: AVCHD and H.264 ceilings.** Panasonic AVCHD encoders use High Profile at Level 4.0. Level 4.0 allows 20 Mb/s
   (Main profile, VCL; Wikipedia lists only that column). AVCHD 1.0 allows up to 24 Mb/s; our "AVCHD peak 24" sits at that ceiling.
8. **New: lightsnowdev saw "System running: uITRON" in E-M10 firmware strings, and calls the E-M5 CPU a "Matshi-MN103".**
   Wikipedia says MN103 = MN10300 = **AM33**. This confirms our firmware reading.
9. **"Dual-core" is only a journalist's phrase.** The 2011 Olympus press release (reprinted by Gizmodo) does not say it,
   and the dpreview E-PL5/E-PM2 preview does not say it.
10. **E-PM2 rolling shutter is "pretty pronounced"** (IR). IR says the E-M5's lower rolling shutter comes from a faster
    readout. The sensor feed is "clocked off the image sensor at 30 frames per second".
11. **The E-M1 sensor code is corrected** to "Panasonic 34231 (MN34230 die markings)", per Chipworks via IR.
12. **The Wikipedia "TruePic" article no longer exists** on en.wikipedia (the API reports it missing). The MN103 claim
    survives only in the "Image processor" list article.
13. **GH1 "overall bitrate = card controller peak" is unverified.** The cited EOSHD URL is a different (42 Mbit GH2) article.
14. **No source found** gives the E-PM2 encoder profile or level, an E-PM2/E-PL5 card test, a board teardown, or an Olympus bitrate hack.

## Access log
- **Read directly:** support.jp.omsystem.com, www.imaging-resource.com, en.wikipedia.org.
- **Read through WebFetch:** www.dpreview.com (curl gets a Cloudflare 403).
- **Read as web.archive.org copies** (the live hosts still return "Approval required" 403): cameramemoryspeed.com,
  lightsnowdev.blogspot.com, eoshd.com, personal-view.com, dvinfo.net, dc.watch.impress.co.jp, sansmirror.com,
  gizmodo.com, petapixel.com, expertreviews.co.uk, neocamera.com, kimletkeman.blogspot.com, getolympus.com,
  photoreview.com.au, photographyblog.com, savazzi.net, ifixit.com, zeroonevisuals.blogspot.com, 0l.de, helpguide.sony.net (ilc page).
- **Still not readable:**
  - Live hosts that still need approval: old.imaging-resource.com, manualshive.com, imaging-resource.com (no www).
  - Live hosts blocked by policy: wikimili.com, 43rumors.com, dvxuser.com (archive copy is a Cloudflare page),
    engadget.com (archive copy is empty), reviewed.com (archive 403), sonyalpharumors.com.
  - manualslib.com: Cloudflare challenge.
  - No archive copy: manualshive pages, personal-view comment 157537, eoshd topics 324/462/1286,
    the 43rumors post, the dpreview forum thread, the ipfs mirror.
- Labels: CONFIRMED = the page says it; CORRECTED = the page says something else, and the fix is shown;
  UNVERIFIED = the page could not be read, or it does not say it.
  Source types: [official] Olympus; [measured] a test; [teardown] die analysis; [community] forum or blog.

## 1. Official specs

**Cards.** The E-PM2 takes "SD / SDHC / SDXC cards (UHS-I compatible)", Eye-Fi ("Endless mode is not supported") and FlashAir.
"Class 6 or higher cards are recommended for movie shooting." CONFIRMED [official]
https://support.jp.omsystem.com/en/support/imsg/digicamera/qa/products/epm2/
IR's spec sheet says "Usable Memory Types: SD / SDHC / SDXC; UHS Support: UHS-I". CONFIRMED
https://www.imaging-resource.com/PRODS/olympus-epm2/olympus-epm2DAT.HTM
- No source says which UHS-I bus mode the camera uses. For the E-M5 II, the tester writes "It would seem the
  E-M5 II card controller does not support SDR104" (all UHS-I cards stayed below 40 MB/s). CONFIRMED [measured, other body]
  https://cameramemoryspeed.com/olympus-e-m5-ii/sd-card-comparison (archive copy)

**Movie modes: the Olympus E-PM2 table** (https://support.jp.omsystem.com/en/support/imsg/digicamera/qa/products/epm2/), CONFIRMED [official]

| Record mode | Size | Rate | Format | Bitrate | Max time | Ours |
|---|---|---|---|---|---|---|
| Full HD Fine | 1920x1080 | 30p (29.97) | MOV (MPEG-4AVC/H.264) | 20 Mb/s | 22 min | 20 |
| Full HD Normal | 1920x1080 | 30p | MOV | 17 Mb/s | 29 min | 17 |
| HD Fine | 1280x720 | 30p | MOV | 13 Mb/s | 29 min | 13 |
| HD Normal | 1280x720 | 30p | MOV | 10 Mb/s | 29 min | 10 |
| HD | 1280x720 | 30 fps | AVI (Motion JPEG) | - | 7 min | - |
| SD | 640x480 | 30 fps | AVI (Motion JPEG) | - | 14 min | - |

- Footnotes on that page: "The maximum file size of a movie is 4 GB or 29 min" (MOV). Motion JPEG is "2 GB, 7 min (HD) or 14 min (SD)".
  "Depending on the memory card, the recording may stop without recording to the maximum time." CONFIRMED
- **AVCHD is not offered.** The E-PM2-vs-E-PM1 table lists "MOV (MPEG-4AVC/H.264), AVI Motion JPEG" for the E-PM2,
  and "AVCHD full HD, AVI Motion JPEG" for the E-PM1. CONFIRMED. The E-PL5 page says the same against the E-PL3:
  https://support.jp.omsystem.com/en/support/imsg/digicamera/qa/products/epl5/
- The same E-PM2 page gives "Effective pixels 16.5 million". The E-PL5 page says 16.05 million. This is probably a typo on Olympus's page.
- IR measured the same modes. MJPEG compression is 1:12 (720p) and 1:8 (VGA). "The actual data is clocked off the image
  sensor at 30 frames per second." Video uses digital IS; "sensor-shift stabilizer mechanism is disabled for movies". CONFIRMED [review]
  https://www.imaging-resource.com/cameras/olympus-e-pm2-review/ (the old PRODS/...A6.HTM URLs redirect here)
- The draft cited a manual mirror for "4GB (AVCHD)" and "supports UHS-I": **CORRECTED/UNVERIFIED**. manualshive returns 404
  in the archive; Olympus's table says the 4 GB limit is for MOV.
- Neocamera lists "1920x1080 @ 30 FPS Video using AVCHD codec". This contradicts Olympus, which says MOV. https://www.neocamera.com/camera/olympus/epm2/review

**AVCHD in older TruePic VI bodies** (this explains the AVCHD code in our firmware):
- E-P3: AVCHD (.MTS) at 1920x1080 59.94i, 20/17 Mb/s average, and at 1280x720 59.94p, 17/13 Mb/s. "Clocked off the image
  sensor at 30 frames per second." CONFIRMED [review] https://www.imaging-resource.com/cameras/olympus-e-p3-review/
- E-PM1: "AVCHD full HD / AVI Motion JPEG HD (30 frames per second)"; IR says 1080 60i. CONFIRMED. Its bitrates (17/13) are UNVERIFIED.
  https://support.jp.omsystem.com/en/support/imsg/digicamera/qa/products/epm1/ , https://www.imaging-resource.com/cameras/olympus-e-pm1-review/
- AVCHD ceilings: Sony states "28 Mbps (Maximum), 24 Mbps (Maximum) or 17 Mbps (Average)". The AVCHD system data rate is
  "up to 24 Mbit/s", or up to 28 Mbit/s for AVCHD 2.0 progressive. CONFIRMED
  https://helpguide.sony.net/ilc/1530/v1/en/contents/TP0001093162.html (archive), https://en.wikipedia.org/wiki/AVCHD
- **Reading:** our "1080i peak 24" equals the AVCHD 1.0 maximum, and "720p 19.3" lies above the E-P3's 17 Mb/s average.
  Both look like peak caps on the E-P3-era AVCHD modes. (This is inference.)

**Recording limits.** 22 min (Full HD Fine) or 29 min (others), and 4 GB per MOV file. CONFIRMED [official]
4 GB at 20 Mb/s is about 27 min, so at Fine the 22 min timer stops the clip first. (This is arithmetic.)

**Buffer and burst.**
- dpreview: "Up to 8fps continuous shooting (fixed focus and exposure with I.S. off)"; L = 1-3.5 fps, H = 4-8 fps. CONFIRMED (WebFetch)
  https://www.dpreview.com/reviews/olympus-e-pm2
- IR measured 7.98 fps RAW. The buffer was 16 large JPEG, 16 RAW and 15 RAW+JPEG. With the buffer full it fell to 2.14 fps (JPEG),
  1.78 fps (RAW) and 0.97 fps (RAW+JPEG). Clearing took 7 s, 9 s and 25 s, on a "SanDisk Extreme Pro 95MB/sec UHS-I SDHC". The fps with tracking AF is 3.5 (Olympus spec, not tested). CONFIRMED [measured]
  https://www.imaging-resource.com/cameras/olympus-e-pm2-review/
- Expert Reviews: 8 fps "for 19 frames before slowing to 2.9fps", and "for 14 raw frames". CONFIRMED (archive)
  https://www.expertreviews.co.uk/digital-cameras/compact-system-cameras/52989/olympus-pen-e-pm2-review
- Neocamera: "8 FPS Continuous drive, 12 RAW or JPEG". CONFIRMED (archive). **The three sources disagree: 12, 14 or 16 RAW frames.**
- Estimate: about 1.78 RAW fps with the buffer full, times about 14-15 MB per RAW, is about 25-27 MB/s to the card.
  This is consistent with the E-M5's 28 MB/s (section 5). (This is inference.)

## 2. The image processor (TruePic VI)

- The 2011 Olympus press release (E-P3, E-PL3, E-PM1) says "new TruePic VI Image Processing Engine". It gives no chip details. CONFIRMED (archive)
  https://gizmodo.com/olympus-new-pen-e-p3-dual-cores-in-a-camera-yes-pleas-5816928/
- **"Dual-core": UNVERIFIED as an Olympus claim.** Only the Gizmodo writer says "yes two processing cores ... photos are chomped
  in parallel". The dpreview E-PL5/E-PM2 preview lists just "TruePic VI processor" (WebFetch).
  The 43rumors "separate processors" post: UNVERIFIED (no archive copy).
  https://www.dpreview.com/reviews/olympus-pen-e-pl5-e-pm2
- It is the same engine as the E-M5. IR says "Although it's the same processor used in the E-M5" (E-PM2), and that the E-PL5
  "shares the exact same pairing of image sensor and processor". dpreview says the E-PM2 "shares the same essential 'guts' with the E-PL5". CONFIRMED
  https://www.imaging-resource.com/cameras/olympus-e-pl5-review/ , https://www.dpreview.com/reviews/olympus-e-pm2
- Wikipedia lists "Olympus - TruePic (based on Panasonic MN103/MN103S)" and "Panasonic - Venus Engine (based on Panasonic MN103/MN103S)". CONFIRMED [community]
  https://en.wikipedia.org/wiki/Image_processor
- MN103 "(also called MN10300 or AM33) is a 32-bit microprocessor series developed by Matsushita ... Most variants include a
  media processor". CONFIRMED [community] https://en.wikipedia.org/wiki/MN103
- lightsnowdev wrote "The processor of the E-M5 is a 'Matshi-MN103'. The other cpus are unknown yet." CONFIRMED (archive) [community]
  https://lightsnowdev.blogspot.com/2014/09/how-to-start-your-own-hacks.html
- E-M10 (TruePic VII) firmware strings include "System running: uITRON", "USF debugging shell Version 1.10" and a Broadcom Wi-Fi driver.
  "The camera does not support 25fps video." CONFIRMED (archive) https://lightsnowdev.blogspot.com/2014/07/olympus-om-d-e-m10-firmware-hack.html
- The GH1 used the "Panasonic AM32-4 MN103 processor", and the GH2 was "expected to use the faster AM32-5". EOSHD also says the
  GH1 firmware is "based on a custom ... Red Hat Linux". That differs from Olympus's uITRON. CONFIRMED (archive) [community]
  https://www.eoshd.com/news/panasonic-gh1-firmware-hacked
- The GH2's "Venus Engine FHD ... uses three CPUs". CONFIRMED https://www.imaging-resource.com/cameras/panasonic-gh2-review/
- Venus Engine "was based on UniPhier products" (Wikipedia, for some generations). CONFIRMED https://en.wikipedia.org/wiki/Venus_Engine
- **UNVERIFIED (no source):** the TruePic VI part number, the fab, the process node, the core count, and whether Panasonic makes it
  or it shares a die with any Venus Engine. The evidence for a Panasonic-made SoC is the AM33 ISA together with uITRON. That is strong but indirect.
- **H.264 encoder:** no source gives the profile, level or VBV for TruePic VI. Context:
  - Panasonic AVCHD camcorders "use AVC with High Profile @ Level 4.0", with a 24 Mbit/s cap on AVCCAM. CONFIRMED https://en.wikipedia.org/wiki/AVCHD
  - H.264 Level 4 allows a maximum VCL bitrate of 20,000 kbit/s (Main/Baseline), and Level 4.1 allows 50,000. CONFIRMED
    https://en.wikipedia.org/wiki/Advanced_Video_Coding
  - The E-M1 (TruePic VII) lists Full HD Fine 24 Mb/s and Normal 16 Mb/s. CONFIRMED (archive) https://learnandsupport.getolympus.com/support/e-m1
  - EOSHD: "only a slight increase from the muddy 20Mbit's on the E-M5 ... lots of banding and blockiness". CONFIRMED (archive)
    https://www.eoshd.com/news/new-olympus-e-m1-with-moire-reduction-but-no-24p
- **E-M5 frame rate is CORRECTED: it is 60i, not 30p.** IR: "1,920 x 1,080 ... 60 interlaced fields per second from 30 frames per second sensor
  output ... saved in a MOV container", 20/17 Mb/s, and 720 at 13/10 Mb/s. Photo Review gives "1920 x 1080, 60i at 20Mbps". dpreview gives
  "1920 x 1080 (60i from 30p output)". Olympus lists "MOV (MPEG-4AVC/H.264)". The E-M5 spec-transcription thread is UNVERIFIED (dpreview forum: Cloudflare, no archive copy).
  https://www.imaging-resource.com/cameras/olympus-e-m5-review/ , https://www.photoreview.com.au/reviews/advanced-compact-cameras/interchangeable-lens/olympus-om-d-e-m5/ ,
  https://support.jp.omsystem.com/en/support/imsg/digicamera/qa/products/em5/

## 3. Teardowns and board photos

- **No board-level teardown** of the E-PM2, E-PL5 or E-M5 was found. Nothing names the SoC, DRAM, IS MCU, HDMI transmitter or touch controller.
  The iFixit pages that exist cover the E-M10 and E-M10 II only. "Motherboard Replacement" shows removal steps and no chip IDs. CONFIRMED (archive)
  https://www.ifixit.com/Guide/Olympus+OM-D+E-M10+Mark+II++Motherboard+Replacement/126254
- The E-PM2 IR-conversion pages cover only the filter stack. savazzi's camera was "converted ... by eBay seller eeassa". CONFIRMED (archive)
  https://savazzi.net/photography/e-pm2.html
- The E-M1 sensor is CORRECTED: Chipworks found "a Panasonic 34231 (MN34230 die markings) CMOS Image Sensor with on-chip phase detection".
  The same article says "The E-M5 ... definitely used a Sony part". CONFIRMED [teardown, other body]
  https://www.imaging-resource.com/news/2014/02/10/olympus-om-d-em-1-sensor-is-made-by-panasonic-not-sony
- The 2012 anonymous claim: "The OM-D has a clean HDMI 4:2:2 but locked by Olympus", and "The debugger mode is available". CONFIRMED as a claim;
  it was never verified. https://petapixel.com/2012/10/16/hacker-reportedly-finds-hidden-features-in-the-olympus-om-d-em-5/ (archive)
- ADV7511 HDMI and Cypress PSoC: **still neither confirmed nor contradicted** by any public source.

## 4. The sensor

- 4608x3456, 16.1 MP effective, 3.75 micron pitch, 12-bit RAW. IR lists "Sensor Manufacturer: Sony" and "Anti Aliasing Filter: Fixed". CONFIRMED
  https://www.imaging-resource.com/PRODS/olympus-epm2/olympus-epm2DAT.HTM
- **Sony is the maker.** On 2012-07-02, Olympus president 笹宏行 (Hiroyuki Sasa) said 「OLYMPUS OM-D E-M5の撮像素子はソニー製」 ("the E-M5's image sensor
  is made by Sony"). Olympus PR told DC Watch 「申し上げたことは事実」 ("what he said is true"). The sensor is "4/3型の有効1,605万画素". CONFIRMED (archive) [official statement]
  https://dc.watch.impress.co.jp/docs/news/544400.html , https://www.imaging-resource.com/news/2012/07/06/olympus-ceo-identifies-sensor-supplier-for-flagship-mirrorless-camera
- The earlier guesses are now superseded. dpreview: "may well be the same one seen in Panasonic's DMC-G3" (WebFetch).
  sansmirror: "Live MOS ... means Panasonic-supplied" (archive). Both CONFIRMED as quotes and SUPERSEDED.
  https://www.dpreview.com/reviews/olympusem5 , https://sansmirror.com/newsviews/2012-newsviews/february-2012/olympus-goes-hindu-welcomes.html
- E-PM2 = E-M5 sensor: dpreview says "borrows the Olympus OM-D E-M5's proven 16MP CMOS sensor". IR says the E-PL5 has "the identical sensor as far as we know". CONFIRMED
- **The Sony part number is UNVERIFIED** (no source).
- GH3 sharing the sensor: CORRECTED to a blogger's question, "makes me wonder of they really do share a sensor".
  The G5 "uses a variation of the GH2 sensor". CONFIRMED as opinion (archive). The SonyAlphaRumors post is UNVERIFIED (404).
  https://kimletkeman.blogspot.com/2012/11/olympus-om-d-e-m5-versus-panasonic-gh3.html
- **Readout:**
  - The sensor runs at 240 fps for C-AF, "but with reduced accuracy", and at 120 fps for S-AF (E-PM2).
    For the E-M5: "achieving this speed means that the E-P3 can't read out as many pixel locations". CONFIRMED
  - Video is "clocked off the image sensor at 30 frames per second". CONFIRMED
  - **Binning vs line skipping: still UNVERIFIED.** The reviewed.com "pixel binning" quote could not be read (archive 403).
    On Personal View, a user said of the **E-M5 II** "Line skipping doesn't cut it anymore", and another asked "Are you sure it is line skipping?". CORRECTED: this is the wrong body, and it is a claim only.
    https://personal-view.com/talks/discussion/comment/191575 (archive)
- **Rolling shutter:** on the E-PM2 it is "pretty pronounced ... heavily distorted and 'wobbly'" in H.264 and MJPEG. For the E-M5, IR reports "much lower
  levels of rolling shutter ... achieved simply by increasing the readout speed (no precise numbers)". CONFIRMED [measured/review]
  So the E-PM2 video readout is probably slower than the E-M5's. (This is inference.)
- Stills: the E-PM2 shows "demosaicing errors and aliasing artifacts ... low pass filter is fairly weak"; aliasing starts at about 2,300 lines (the page prints "2,30"). CONFIRMED
  https://www.imaging-resource.com/cameras/olympus-e-pm2-review/

## 5. Measured performance

- **E-M5 card write test** (RAW bursts; bytes divided by the time the card access light is on), "maximum write speed is around 28MB/s":
  SanDisk Extreme Pro 95 MB/s 28.6, Extreme Plus 80 MB/s 27.7, Toshiba Exceria 27.4, Samsung PRO 27.4, Sony 94 MB/s 27.2, SanDisk Extreme 45 MB/s 26.6.
  "All cards we test are recent UHS-I Class 10". "The camera is not able to approach the maximum write speed". CONFIRMED (archive) [measured]
  https://cameramemoryspeed.com/olympus-e-m5/fastest-sd-card-tests
- E-M10: about 31-32 MB/s (top results 32.1, 31.7, 31.7, 31.4). E-M5 II: 82.3 MB/s with UHS-II, and UHS-I below 40 MB/s. CONFIRMED (archive)
  https://cameramemoryspeed.com/olympus-e-m10/fastest-sd-card-tests
- The site's index lists only the E-M1, E-M1 II, E-M5, E-M5 II, E-M10 and PEN-F. **There is no E-PM2 or E-PL5 test.** CONFIRMED (archive) https://cameramemoryspeed.com/camera-tests
- **Card vs video (inference):** 28 MB/s is about 224 Mb/s, roughly 11 times the 20 Mb/s Fine rate. Olympus's Class 6 floor is 6 MB/s, about 48 Mb/s.
- **Video quality (E-PM2):** "Heavy compression artifacts can be seen at all video resolutions, especially in 1080p ... Moiré patterns are also prevalent";
  for MJPEG, "Moiré patterns are quite pronounced"; "the video image quality ... leaves a lot to be desired". CONFIRMED [review]
  https://www.imaging-resource.com/cameras/olympus-e-pm2-review/
- E-M10 review: "Compared to the very disappointing video quality of some Olympus cameras like the E-PL5 or E-PM2". CONFIRMED
  https://www.imaging-resource.com/cameras/olympus-e-m10-review/ (the draft's field-test URL is only an image page: CORRECTED)
- reviewed.com: "grainy and soft" UNVERIFIED (archive 403). EOSHD "Olympus video stupid" thread and Personal View "forest/water" claim: UNVERIFIED (no archive copy).

## 6. Bitrate hacks

**Olympus: no released bitrate hack was found.**
- lightsnowdev's Firmware Control Tool: "Version 0.4d //20.08.14 support for E-P5, E-PL3, E-PL5, E-PM2 & STYLUS 1". A commenter asked: "Does anybody have an
  experience of hacking the firmware of E-PM2? Any success or improvement regarding video quality?" (no answer). Others wished for "30-40 Mbps". CONFIRMED (archive)
  https://lightsnowdev.blogspot.com/2014/08/firmware-control-tool-to-flash-any.html
- Flashing: "There is a python script available to emulate the Olympus server ... We can flash any firmware". Also the DCOLYMP folder plus OK-button
  method. The E-M5 "experiment" was built from E-M10 files, and the links were later pulled ("I think its do dangerous"). CONFIRMED (archive)
  https://lightsnowdev.blogspot.com/2014/09/om-d-e-m5-firmware-experiment.html
- 0l.de (stv0g) documents only the E-M10 Wi-Fi protocol and UDP live view. CONFIRMED (archive) https://0l.de/projects/omd/
- "Kiselev won't do OM-D": UNVERIFIED (personal-view 157537 has no archive copy). The E-M5 firmware 1.2 pull (sansmirror): UNVERIFIED (archive 404).

**Panasonic GH1/GH2 (PTool):**
- Kiselev "managed to dissect the GH2 (and GH1) firmware ... have the camera's built-in ASIC use different settings". CONFIRMED (archive)
  https://www.sansmirror.com/cameras/frequentely-asked-mirrorles/whats-this-hacked-panasonic.html
- Stock rates: GH2 24 Mb/s AVCHD ("the maximum 24 Mbps the standard supports"); "The GH1 maxed-out at 17 Mbps". CONFIRMED
  https://www.imaging-resource.com/cameras/panasonic-gh2-review/
- Hacked: "an average of 42Mbit – almost double the original Panasonic specification"; the GH2 encoder has B-frames, "unlike the GH1's".
  Then "AVCHD Intra at 176Mbit ... far higher than the 24Mbit Long GOP factory setting". CONFIRMED (archive)
  https://www.eoshd.com/news/vitaliy-hacks-photographic-looking-42mbit-108024p-avchd-out-of-gh2 , https://www.eoshd.com/news/gh2-gets-avchd-intra-at-176mbit/
- **Limits users hit** (all CONFIRMED as forum reports, read through archive copies):
  - The card: over the card's rate the camera "stop recording and say ... recording cancelled due to card write speed" and "locked the camera" (88 Mb/s patch, 45 MB/s card).
    https://www.eoshd.com/comments/topic/791-gh2-unified-hack-88mbs-on-a-sandisk-extreme-45-mbs
    Another user: "my card can go max 130Mbits without crashing", and "100mbps is only 12.5MB/s".
    https://www.personal-view.com/talks/discussion/comment/118203
  - Content: the 176 patch measured "~40M/s to ~105Mb/s, never to the full capacity"; another user saw "doesn't go over 80Mbps". "Some hacks crash with
    high detail scenes. The encoders choke". https://dvinfo.net/forum/panasonic-lumix-s-g-gf-gh-gx-series/513524-maximizing-driftwood-176mbit-hack.html
  - Rate control: "The AVCHD encoder works at a constant QP by default, which is 20". Users test quantizer, AQ and "Frame Limit" settings. QP 12-14
    "topped out at ~65mbps ... clearly hitting a ceiling". Raising the bit-rate limit costs "spanning" (recording past the 4 GB file split).
    https://personal-view.com/talks/discussion/comment/43279
  - The encoder buffer: PTool exposes a per-mode "Video buffer" (tested at 0x2400000 and 36000000). "Bitrate has been king"; the alternative lets "buffering ... vary".
    The draft's "Bottom Setting" and "underruns/overruns" quotes are UNVERIFIED on this page. https://personal-view.com/talks/discussion/comment/17160
  - GH1: the "overall bitrate = card controller peak write" claim is UNVERIFIED (the cited URL is the GH2 42 Mbit article). The dvxuser 75 Mb/s patch page
    could not be read (Cloudflare).

## Summary of limits (inference)
1. The card is not the first limit. The TruePic VI generation writes about 28 MB/s (about 224 Mb/s), against 20 Mb/s stock. On the GH2, failures came from content peaks and real card speed.
2. The encoder's maximum (profile, level, VBV) is unknown. 24 Mb/s AVCHD peaks fit H.264 Level 4.0. The GH1/GH2 MN103 encoders ran at 2-7 times stock, but that is a different encoder block.
3. Readout runs at 30 fps with reduced pixel sampling (method unknown), and the camera has strong rolling shutter and a weak AA filter. Moiré and aliasing do not depend on bitrate.
4. MOV stops at 4 GB or 29 min. 4 GB lasts about 13 min at 40 Mb/s and about 5 min at 100 Mb/s.

## Open items
- Profile, level and GOP: run `ffprobe` on our own E-PM2 MOV. IR's sample-clip links (`/PRODS/olympus-epm2/FULLRES/*.MOV`) now redirect to the review page. Board IDs need a teardown of our own body.
- Hosts still to approve: old.imaging-resource.com, manualshive.com, wikimili.com, 43rumors.com, dvxuser.com, reviewed.com, sonyalpharumors.com, engadget.com.
