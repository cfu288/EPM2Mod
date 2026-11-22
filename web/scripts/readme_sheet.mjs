// Make docs/images/film-sim-comparison.jpg, the README's comparison sheet, in the site's style.
//
//     node web/scripts/readme_sheet.mjs
//
// Rows: the site's nine scenes (web/apps/site/src/filmPhotos.json, made by film_photos.py) in Natural and the
// first seven film simulations of the catalogue. Below: the gallery scene in every other film simulation.
// The page is drawn by Chromium (Playwright) with the site's fonts, then saved as a JPEG.
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'

const WEB = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const ROOT = path.resolve(WEB, '..')
const OUT = path.join(ROOT, 'docs/images/film-sim-comparison.jpg')
const COLUMNS = 8
const WIDTH = 2400

const scenes = JSON.parse(fs.readFileSync(path.join(WEB, 'apps/site/src/filmPhotos.json'), 'utf8'))
const films = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/films/catalogue.json'), 'utf8')).films
const looks = [{ id: 'natural', name: 'Natural', film: '' }, ...films]
const top = looks.slice(0, COLUMNS)
const rest = looks.slice(COLUMNS)
for (const scene of scenes)
  for (const look of looks) if (!scene.looks[look.id]) throw new Error(`${scene.id} has no ${look.id}`)

const photo = (scene, id) => `file://${path.join(WEB, 'apps/site/public', scene.looks[id])}`
const font = (file) => `file://${path.join(WEB, 'node_modules/@fontsource', file)}`
const label = (look) => `<div class="name">${look.name}</div><div class="film">${look.film}</div>`

const html = `<!doctype html><html><head><style>
@font-face { font-family: Sora; font-weight: 800; src: url(${font('sora/files/sora-latin-800-normal.woff2')}); }
@font-face { font-family: Arimo; font-weight: 400; src: url(${font('arimo/files/arimo-latin-400-normal.woff2')}); }
@font-face { font-family: Arimo; font-weight: 700; src: url(${font('arimo/files/arimo-latin-700-normal.woff2')}); }
body { margin: 0; width: ${WIDTH}px; background: #fff; color: #000; font-family: Arimo, sans-serif; }
main { padding: 48px 60px 60px; }
h1 { border-top: 18px solid #000; margin: 0; padding-top: 30px; font: 800 44px Sora, sans-serif; letter-spacing: -0.02em; }
.grid { display: grid; grid-template-columns: repeat(${COLUMNS}, 1fr); gap: 18px; }
.head { margin-top: 36px; padding-bottom: 14px; border-bottom: 1px solid #ccc; }
.rows { margin-top: 18px; }
.rest { margin-top: 36px; padding-top: 36px; border-top: 1px solid #ccc; row-gap: 30px; }
img { display: block; width: 100%; }
.name { font-weight: 700; font-size: 20px; }
.film { color: #787878; font-size: 16px; margin-top: 4px; min-height: 19px; }
.rest .name { margin-top: 12px; }
</style></head><body><main>
<h1>Film Simulations</h1>
<div class="grid head">${top.map((look) => `<div>${label(look)}</div>`).join('')}</div>
<div class="grid rows">${scenes.map((scene) => top.map((look) => `<img src="${photo(scene, look.id)}">`).join('')).join('')}</div>
<div class="grid rest">${rest.map((look) => `<div><img src="${photo(scenes[0], look.id)}">${label(look)}</div>`).join('')}</div>
</main></body></html>`

const page_file = path.join(ROOT, 'build/readme-sheet.html')
fs.mkdirSync(path.dirname(page_file), { recursive: true })
fs.writeFileSync(page_file, html)
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: WIDTH, height: 1000 } })
await page.goto(`file://${page_file}`)
await page.evaluate(() => document.fonts.ready)
await page.waitForFunction(() => [...document.images].every((im) => im.complete && im.naturalWidth > 0))
await page.screenshot({ path: OUT, fullPage: true, type: 'jpeg', quality: 82 })
await browser.close()
console.log(
  `wrote ${path.relative(ROOT, OUT)}: ${scenes.length} scenes x ${top.length} looks, then ${rest.length} more`,
)
