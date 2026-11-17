# Film looks web app

A static page where users choose a film for each art filter (ART 1 to 12) of the E-PM2 mod and download
`EPM2LOOK.BIN`, without the command line. It is published at https://cfu288.github.io/EPM2Mod/ by
`.github/workflows/web.yml` on every change to `main`.

- React, Vite, Tailwind CSS, Headless UI; components adapted from Tailwind UI.
- `src/data/films.json`: the films and their look records, made by `uv run python web/scripts/export_films.py`
  from `looks/catalogue.json` (a test of the Python suite fails when it is out of date).
- `public/previews/`: the camera's Picture Mode strip for each film in each slot, drawn by the emulator
  (`uv run python web/scripts/render_previews.py`).
- `public/404.html` and the script in `index.html`: the GitHub Pages redirect back to the app for any path.

Work on it with Node 26 (`.nvmrc`):

```sh
cd web
npm ci
npm run dev      # local server
npm run check    # format, lint, type check, tests, build: what CI runs
```

The packed file is byte-equal to `uv run epm2mod looks pack` (`src/lib/lookfile.test.ts`).
