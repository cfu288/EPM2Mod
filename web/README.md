# Film looks web app

A static page where users choose which films are in the camera's ART menu (ART 1 to 12) and in which order, by drag
and drop, and download `EPM2LOOK.BIN`, without the command line. It is published at https://cfu288.github.io/EPM2Mod/ by
`.github/workflows/web.yml` on every change to `main`.

- React, Vite, Tailwind CSS, dnd-kit (drag and drop, with the keyboard too). The look follows the OM SYSTEM gallery
  pages: black and white, square buttons that invert on hover, sections under a thick black rule. Fonts: Sora
  (headings) and Arimo (text), the free fonts nearest to that site's Neue Machina and Helvetica Neue (glyph overlap);
  computers with Helvetica Neue use it.
- `src/data/films.json`: the films and their look records, made by `uv run python web/scripts/export_films.py`
  from `looks/catalogue.json` (a test of the Python suite fails when it is out of date).
- `public/previews/`: the camera's Picture Mode strip, drawn by the emulator, in two layers: `menu/art<N>.png` (the
  strip at ART N, name box empty) and `name/<film>.png` (the film's name). The app stacks the name of a row's film on
  the strip of the row's position. Made by `uv run python web/scripts/render_previews.py`, which checks the split.
- `public/404.html` and the script in `index.html`: the GitHub Pages redirect back to the app for any path.

Work on it with Node 26 (`.nvmrc`):

```sh
cd web
npm ci
npm run dev      # local server
npm run check    # format, lint, type check, unit tests, build
npm run e2e      # browser tests of drag and drop and the download (Playwright; once: npx playwright install chromium)
```

CI runs both.

The packed file is byte-equal to `uv run epm2mod looks pack` (`src/lib/lookfile.test.ts`).
