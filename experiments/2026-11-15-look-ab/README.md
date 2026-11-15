# Film look A/B

A small web page that finds which film look you prefer. It shows one photo in two looks, side by
side and without names. You pick one. After a number of choices it ranks the looks, overall and
by situation.

## Build and serve

```sh
../../.venv/bin/python -I build.py /path/to/photos
../../.venv/bin/python -I serve.py
```

`/path/to/photos` holds each photo developed with each look in the camera (Playback → RAW Data
Edit). `build.py` finds the scene from the capture time and the look from the art filter in the
EXIF data. It writes the page to `out/`, with smaller copies of the photos that have no metadata.

`serve.py` serves `out/` on port 8765 and keeps the votes of every device in `votes/`. Open
`http://HOST:8765/` on each screen. The page also works from a plain file server; the votes then
stay in that browser.

For a new set of photos, write the name and the situation tags of each scene in `scenes.json`,
oldest photo first. A tag that two or more scenes share gives a better answer than a tag with one
scene.

## Screen types

A look can win on one screen and lose on another, so each vote is recorded for the screen type
it was made on. The screen type is a hash of the display's traits: size in CSS pixels, pixel
ratio, colour gamut, high dynamic range and bit depth. It has no device name. Two devices with
the same kind of screen are one screen type. A laptop panel and a monitor on one computer are two.

The result shows the ranking of each screen type and says if the top pick differs. A screen type
needs 12 choices before it is compared. "Start over" erases the votes of the screen type in use
only. "Stop, show results" gives the result at any time.

## Files

| File | Contents |
|---|---|
| `build.py` | makes `out/` from a photo folder and `scenes.json` |
| `serve.py` | serves `out/` and stores the votes of all devices; tests in `test_serve.py` |
| `scenes.json` | names and situation tags of the eight scenes of the README photos |
| `page/index.html` | the page: layout and styles |
| `page/ranking.js` | the maths, with no page code: Bradley–Terry strengths, the next pair, the verdict, the screen type and the comparison of screens |
| `page/app.js` | the page code: pairs, stored votes, the result |
| `test_ranking.mjs` | tests of `ranking.js`: `node --test test_ranking.mjs` |

## How the result is made

- Each choice is one match between two looks. "No preference" is half a win for each.
- The strength of a look is its Bradley–Terry score, shown as the chance that it beats an average
  look. A small prior keeps a look with few matches near 50%.
- The next pair comes from the scene with the fewest choices, and from the looks that have the
  fewest matches and the closest strengths.
- A situation with fewer than 6 choices is marked as a weak signal.
- "Copy results as text" gives the ranking, the screen types and every vote.

## Limits

- Eight scenes are a small sample. Some tags have one scene.
- The page compares looks on photos that exist. It does not predict a look on a new subject.
