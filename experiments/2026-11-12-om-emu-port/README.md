# om-emu port to the E-PM2 (2026-11-12)

om-emu (github.com/flatpanda/om-emu, a JavaScript emulator of Olympus/OM firmware) now runs single E-PM2 v1.6 functions, stock against patched.

- **Tool:** `tools/emu/`. Setup and usage are in tools/emu/README.md; the cases are in tools/emu/cases.py. It uses om-emu installed at `~/opt/om-emu` and Node 26.13.1 at `~/opt/node26`. Both live outside the repo, and Node is not on the shared PATH.
- **om-emu changes:** `om-emu-changes.diff`, the same changes as tools/emu/om-emu-E101.patch:
  - a local **E101** model on the E118-family board, with image base 0x7E421020 and 512 MiB DRAM;
  - the compositor and OSD models moved off 0x9C000000, which is a per-CPU window on the E-PM2;
  - a function-only mode.
- **Results:** `results/`, the emulator output saved at the time of the port:
  - **`rec_limit.diff.json`:** the recording-limit routine 0x7E6EDE08. 48 rows; a 1740 → 3600 edit changes exactly the 6 rows stock clamps at 1740 s.
  - **`curve_select.film-portra.json` and `curve_select.film-portra-xp.json`:** the tone-curve selector 0x7E56E837. `film-portra.json` also changes art codes 9/13/55/129/133.

  Later cases (the QP set-up and rate control, the bitrate table, the parameter check) are in tools/emu/cases.py. Their reports are in experiments/2026-11-12-hardware/05-qp-floor.md and 06-bitrate-and-limit.md.
- **Limits:**
  - single functions only: no boot, no kernel, no second core;
  - no IMG engine or codec hardware;
  - RAM starts at zero, with no `.data` copy.

  A passing case is evidence, not proof of safety on the camera.
- **How it began:** the review that led to it is experiments/2026-11-11-caduceus-review/03-emulator.md. Using om-emu was approved by the user on 2026-11-12 for private use.
