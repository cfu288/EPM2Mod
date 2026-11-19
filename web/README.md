# The site and the local app

Two pages share one package of components and data:

| Folder                        | What it is                                                                                                                           | Served by                                                                                                |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| `packages/ui` (`@epm2mod/ui`) | the ART-menu editor (`MenuEditor`, `useLooks`), the preview (`StripPreview`), the page frame, the film data and the look-file packer | both apps                                                                                                |
| `apps/site`                   | the public page: features, film comparison, install steps                                                                            | GitHub Pages, https://cfu288.github.io/EPM2Mod/ (`.github/workflows/web.yml`, on every change to `main`) |
| `apps/local`                  | the local app: make the firmware, add film looks, write to an SD card or download a zip                                              | `epm2mod serve` (`src/epm2mod/serve.py`), from the build in `src/epm2mod/app/` (not in git)              |

Rules (the lint refuses a break of them): an app imports shared code only from `@epm2mod/ui` and
`@epm2mod/ui/theme.css`, never from another app and never from a path inside `packages/ui`. Code that both apps need
goes into `packages/ui` and is exported from its `src/index.ts`. Each app keeps only its own layout and text.

- React, Vite, Tailwind CSS, dnd-kit (drag and drop, with the keyboard too). The look follows the OM SYSTEM gallery
  pages: black and white, square buttons that invert on hover, sections under a thick black rule
  (`packages/ui/src/theme.css`). Fonts: Sora (headings) and Arimo (text), the free fonts nearest to that site's Neue
  Machina and Helvetica Neue (glyph overlap); computers with Helvetica Neue use it.
- `../looks/film-records.json`: the films and their look records, the same file that `epm2mod films set` reads. Made
  by `uv run python web/scripts/export_films.py` from `looks/catalogue.json` (a test of the Python suite fails when it
  is out of date).
- `packages/ui/src/previews/`: the camera's Picture Mode strip, drawn by the emulator, in two layers: `menu/art<N>.png`
  (the strip at ART N, name box empty) and `name/<film>.png` (the film's name). The preview stacks the name of a row's
  film on the strip of the row's position. The pictures are bundled as assets, so each app serves them under its own
  base path. Made by `uv run python web/scripts/render_previews.py`, which checks the split.
- `apps/site/public/404.html` and the script in `apps/site/index.html`: the GitHub Pages redirect back to the page for
  any path.

Work on it with Node 26 (`.nvmrc`), from `web/`:

```sh
npm ci
npm run dev        # the site, local server
npm run build:app  # the local app, into src/epm2mod/app; then: uv run epm2mod serve
npm run check      # format, lint, type check, unit tests, both builds
npm run e2e        # browser tests of both apps (Playwright; once: npx playwright install chromium)
```

CI runs `check` and `e2e`. The local app's browser tests answer the API calls themselves; the server and the real
firmware build are tested in Python (`tests/test_serve.py`).

To work on the local app against a real server: `uv run epm2mod serve --no-browser --port 8765`, then
`EPM2MOD_API=http://127.0.0.1:8765 npm run dev:app`, and open the dev address with the server's `#token=...`.

The packed look file is byte-equal to `uv run epm2mod films set -o FILE` with the same `--film` choices (`packages/ui/src/lib/lookfile.test.ts`).
