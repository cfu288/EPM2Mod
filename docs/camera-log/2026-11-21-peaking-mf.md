# 2026-11-21: data/builds/peaking-mf.json

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-21 | `data/builds/peaking-mf.json`, a test build (not for use): films-twelve-off + `peaking-mf` (focus peaking whenever the focus mode is MF, without the magnified view; `experiments/2026-11-21-peaking-mf/NOTES.md`) | `7ddccc78e0e92ff98da84a25efd05a92e541bb48e6c65b86073825926be98ab4` | **Flashed (owner, 2026-11-21): works, one defect.** MF + Peaking White: lines in the normal live view without zoom, also with the Digital Tele-converter; S-AF / C-AF no lines; movie no lines; S-AF+MF with MF Assist as before; the saved photo clean, but the preview after the shot shows the lines (NOTES §5). Since rebuilt on films-start-texts with the code moved and the record-view fix (§6–7, sha256 `6a47806d…`, not flashed). Before the flash, emulator: the latch with the firmware's settings getter, 12 cases PASS (MF + a colour: lines; S-AF / C-AF as pinned; MF Assist as pinned). |
