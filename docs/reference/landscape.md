# Olympus Custom Firmware

![A timeline of Olympus and OM SYSTEM cameras that have custom firmware projects, from the E-PL3 in 2011 to the OM-5 Mark II in 2025](../images/landscape.png)

The list holds the Olympus custom firmware projects we know of: those on GitHub, in the [OM Firmware Atlas](https://github.com/xulfr/om-firmware-atlas) and in a [43rumors roundup](https://www.43rumors.com/new-mft-hacking-roundup-e-pm2-gains-focus-peaking-e-p7-gets-150mbps-4k-and-more-om-3-upgrades/), on 2026-11-21.

| Announced | Camera | Projects |
|---|---|---|
| 2011 | E-PL3 | [E-PL3 research](https://github.com/sympho-ru/olympus-e-pl3-research) (research only) |
| 2012 | E-PM2 | **EPM2Mod** |
| 2016 | PEN-F | [PEN-F HSL](https://github.com/fishcu/oly_fw_analysis/releases) |
| 2019 | E-M1X | [db firmware](https://github.com/azqeurio/om-c-firmware/releases) |
| 2019 | E-M5 Mark III | [E-M5 III notes](https://github.com/nsud-dev/olympus-firmware-notes) (research only) |
| 2021 | E-P7 | [Caduceus](https://github.com/cakelesscoder/caduceus-ep7/releases), [db firmware](https://github.com/azqeurio/om-c-firmware/releases) |
| 2022 | OM-1 | [db firmware](https://github.com/azqeurio/om-c-firmware/releases) |
| 2022 | OM-5 | [db firmware](https://github.com/azqeurio/om-c-firmware/releases) |
| 2024 | OM-1 Mark II | [db firmware](https://github.com/azqeurio/om-c-firmware/releases) |
| 2025 | OM-3 | [Caduceus](https://github.com/androidfanman/caduceus-om3/releases), [db firmware](https://github.com/azqeurio/om-c-firmware/releases) |
| 2025 | OM-5 Mark II | [Caduceus](https://github.com/xulfr/caduceus-om5/releases), [db firmware](https://github.com/azqeurio/om-c-firmware/releases), [OMKit](https://github.com/necrostaz/omkit/releases) |

Sources for the years: [E-PL3](https://petapixel.com/2011/06/30/olympus-announces-three-new-pens-the-e-p3-e-pl3-and-e-pm1/), [E-PM2](https://www.bgr.com/general/olympus-pen-e-pl5-and-e-pm2-release-date-october/), [PEN-F](https://old.imaging-resource.com/news/2016/01/27/brains-meets-beauty-new-olympus-pen-f-offers-premium-design-with-a-healthy), [E-M1X](https://www.sansmirror.com/newsviews-2/newsviews/2019-mirrorless-camera/jan-mar-2019-mirrorless/olympus-introduces-pro-e.html), [E-M5 Mark III](https://newsshooter.com/2019/10/17/olympus-releases-om-d-e-m5-mark-iii), [E-P7](https://old.imaging-resource.com/news/2021/06/09/olympus-announces-pen-e-p7-camera-for-international-markets), [OM-1](https://petapixel.com/2022/02/14/om-digital-unveils-om-1-camera-with-a-new-sensor-and-quad-pixel-af), [OM-5](https://www.photographyblog.com/news/om_system_om_5), [OM-1 Mark II](https://www.capturemag.com.au/news/om-system-announces-om-1-mark-ii), [OM-3](https://petapixel.com/2025/02/05/om-system-om-3-is-a-stylish-more-fun-om-1-ii-with-nearly-all-the-performance), [OM-5 Mark II](https://petapixel.com/2025/06/16/the-om-system-om-5-mark-ii-is-a-refined-compact-travel-camera).

## Why EPM2Mod Is Not a Fork

The other projects change newer bodies. Their edits do not carry over to the E-PM2
([Caduceus review](../../experiments/2026-11-11-caduceus-review/01-methods-safety.md#2-what-applies-to-the-e-pm2)):

- **Different code.** The E-PM2's code is about 14 MB and runs at 0x7E421020. The E-P7's code is about 26 MB and
  runs at 0x60020020. An edit is made at an address in one firmware, so no edit is at the same place in the other
  ([model matrix](model-matrix.md)).
- **Edits do not carry over even to close bodies.** Caduceus's own byte-pattern check finds 36 % of its E-P7 edits
  in the E-M5 Mark III, which has the same processor generation (TruePic VIII). The E-PM2 is two generations older
  (TruePic VI).
- **No Colour Profiles.** Caduceus's looks and its colour editor change the COLOR 1–4 Colour Profiles. The E-PM2
  has no Colour Profiles, so EPM2Mod puts each film simulation in an ART entry
  ([colour pipeline](../dev/colour-pipeline.md#2-from-a-menu-entry-to-the-stages)).
- **No colour wheel in live view or movies.** The E-PM2's 12-colour stage works on photos only
  ([feasibility](../dev/feasibility.md#colour-wheel-and-twelve-colour-editors)).
