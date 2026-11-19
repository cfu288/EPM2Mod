# 2026-11-12: patches/remap7b-code.json

| Date (UTC) | Build | sha256 | Result |
|---|---|---|---|
| 2026-11-12 (time not recorded) | films + `patches/remap7b-code.json` + remap7-neutral (`build/seven-slots-remap2-neutral.BIN`) | `bf5ee5c1…6d17da29` | **OK: live view no longer freezes** in Soft Focus, Pin Hole, Diorama. The fix was to make the live-view code's own menu-entry → number tables (0x7E7FF05C, 0x7E807880) agree with `art_GetFilterType`. Appearance of live view and test-image developments still to come. NOTES §37.5. |
