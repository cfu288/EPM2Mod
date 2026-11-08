# Firmware binaries (not in git)

The BINs are git-ignored. `SHA256SUMS` is tracked. Check with:

```bash
cd firmware && sha256sum -c SHA256SUMS
```

| Path | Source |
|---|---|
| `stock/E-PM2/OLY_E_101_{1101,1203,1300,1400,1501,1600}_0000_0000.BIN` | github.com/thrains0220-byte/ep5-fw-reverse `firmware/pre_fix/*.BIN.lzma` (said to come from xdel.ru `pre_fix/`). Hashes match that repo's MANIFEST.sha256. |

The official source is the updater catalog `fw01.om-digitalsolutions.net/ww_inform/fcache.do` (hard_code `OLYE101000000000`). It now returns CloudFront-signed URLs. See [../docs/verification.md](../docs/verification.md) for how the files were checked.

## Removed: E-PL5 v1.6 reference

The E-PL5 v1.6 file (`OLY_E_100_1600_0000_0000.BIN`) was kept only to cross-check the E-PM2 files (see [../docs/verification.md](../docs/verification.md)). It was deleted on 2026-11-08 so that no `E100…` file sits next to flashable builds. To repeat the cross-check, download it again from xdel.ru `downloads/olympus-firmware/original/penepl5/` into a directory outside `build/` and check sha256 `1355c2b8beaaae348654a208e1c0220a9a9273bd88dac408fd6fd01a0ccd0c01`. Never copy it to the camera's card.
