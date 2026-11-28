// Make docs/images/landscape.png, the timeline of Olympus custom firmware, from the table in docs/reference/landscape.md.
//
//     node web/scripts/landscape.mjs
//
// Each row of the table (Announced | Camera | TruePic | Projects) is one camera, drawn in its TruePic generation's
// lane under its year. A project marked "(research only)" is drawn with a dashed camera, EPM2Mod (bold in the table)
// as a black cell. PEN bodies (E-P..., PEN-F) get the flat-top camera, the others the one with a prism hump. The page
// is drawn by Chromium (Playwright) with the site's fonts, then saved as a PNG.
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'

const WEB = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const ROOT = path.resolve(WEB, '..')
const SOURCE = path.join(ROOT, 'docs/reference/landscape.md')
const OUT = path.join(ROOT, 'docs/images/landscape.png')
const WIDTH = 2560

const rows = fs
  .readFileSync(SOURCE, 'utf8')
  .split('\n')
  .filter((line) => /^\| \d{4} \|/.test(line))
  .map((line) => {
    const [year, camera, gen, projects] = line
      .split('|')
      .slice(1, 5)
      .map((cell) => cell.trim())
    const names = projects.split(/,\s*(?![^[]*\])/).map((p) => ({
      name: p
        .replace(/\*\*/g, '')
        .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
        .replace(/\s*\(research only\)/, ''),
      research: /\(research only\)/.test(p),
      ours: /^\*\*/.test(p),
    }))
    return { year, camera, gen, projects: names }
  })
if (rows.length === 0) throw new Error(`no rows in ${SOURCE}`)
const years = [...new Set(rows.map((r) => r.year))]

const pen = (camera) => /^(E-P|PEN)/.test(camera)
const icon = (camera, style) => {
  const dash = style === 'research' ? 'stroke-dasharray="7 5"' : ''
  const fill = style === 'ours' ? '#fff' : 'none'
  const stroke = style === 'ours' ? '#fff' : '#000'
  const top = pen(camera)
    ? `<rect x="10" y="4" width="22" height="9" fill="${fill}" stroke="${stroke}" stroke-width="4" ${dash}/>`
    : `<path d="M 56 15 L 62 4 L 86 4 L 92 15" fill="${fill}" stroke="${stroke}" stroke-width="4" ${dash}/>`
  const lens = style === 'ours' ? '#000' : 'none'
  return `<svg width="150" height="92" viewBox="0 0 150 92">${top}
<rect x="4" y="15" width="142" height="70" rx="5" fill="${fill}" stroke="${stroke}" stroke-width="4" ${dash}/>
<circle cx="75" cy="50" r="22" fill="${lens}" stroke="${style === 'ours' ? '#000' : stroke}" stroke-width="4" ${dash}/>
<circle cx="75" cy="50" r="12" fill="none" stroke="${style === 'ours' ? '#fff' : stroke}" stroke-width="4" ${dash}/></svg>`
}
const styleOf = (row) =>
  row.projects.some((p) => p.ours) ? 'ours' : row.projects.every((p) => p.research) ? 'research' : 'release'
const cell = (row) => {
  const style = styleOf(row)
  const names = row.projects.map((p) => `<div class="project${p.research ? ' research' : ''}">${p.name}</div>`).join('')
  return `<div class="cell ${style}">${icon(row.camera, style)}<div class="camera">${row.camera}</div>${names}</div>`
}
const legend = [
  ['ours', 'EPM2Mod'],
  ['release', 'Mod'],
  ['research', 'Research only'],
]
  .map(([style, text]) => `<div class="key"><div class="mini ${style}">${icon('E-P', style)}</div>${text}</div>`)
  .join('')

// the lanes, oldest first (docs/reference/model-matrix.md, section 1)
const GENS = [
  ['VI', '2011–13'],
  ['VII', '2013–16'],
  ['VIII', '2016–21'],
  ['IX', '2020–25'],
  ['X', '2022–25'],
]
const first = Number(years[0])
const last = Number(years.at(-1))
const allYears = Array.from({ length: last - first + 1 }, (_, i) => first + i)
const small = (s) => s.replace('<svg width="150" height="92"', '<svg width="96" height="59"')
const lanes = GENS.map(([g, span]) => {
  const here = rows.filter((r) => r.gen === g)
  const cols = allYears
    .map(
      (y) =>
        `<div class="slot">${here
          .filter((r) => r.year === String(y))
          .map((r) => small(cell(r)))
          .join('')}</div>`,
    )
    .join('')
  return `<div class="lane"><div class="label"><div class="gen">TruePic ${g}</div><div class="span">${span}</div></div>${cols}</div>`
}).join('')
const font = (file) => `file://${path.join(WEB, 'node_modules/@fontsource', file)}`
const COLS = `220px repeat(${allYears.length}, 1fr)`
const html = `<!doctype html><html><head><style>
@font-face { font-family: Sora; font-weight: 800; src: url(${font('sora/files/sora-latin-800-normal.woff2')}); }
@font-face { font-family: Arimo; font-weight: 400; src: url(${font('arimo/files/arimo-latin-400-normal.woff2')}); }
@font-face { font-family: Arimo; font-weight: 700; src: url(${font('arimo/files/arimo-latin-700-normal.woff2')}); }
@font-face { font-family: Arimo; font-weight: 400; font-style: italic; src: url(${font('arimo/files/arimo-latin-400-italic.woff2')}); }
body { margin: 0; width: ${WIDTH}px; background: #fff; color: #000; font-family: Arimo, sans-serif; }
main { padding: 64px 80px 48px; }
h1 { border-top: 24px solid #000; margin: 0; padding-top: 40px; font: 800 58px Sora, sans-serif; letter-spacing: -0.02em; }
.axis, .lane { display: grid; grid-template-columns: ${COLS}; }
.axis { margin-top: 48px; border-bottom: 4px solid #000; position: relative; }
.axis::after { content: ''; position: absolute; right: -28px; bottom: -14px; border: 12px solid transparent; border-left: 22px solid #000; }
.year { font: 800 30px Sora, sans-serif; padding-bottom: 10px; }
.lane { border-bottom: 2px solid #ddd; min-height: 150px; }
.lane:nth-child(odd) { background: #f4f4f4; }
.label { padding: 22px 24px 18px 0; }
.gen { font: 800 30px Sora, sans-serif; }
.span { font-size: 20px; color: #444; margin: 4px 0 8px; }
dl { display: grid; grid-template-columns: 190px 1fr; gap: 3px 10px; margin: 0; font-size: 17px; line-height: 1.25; }
dt { color: #222; font-weight: 700; }
dd { margin: 0; color: #555; }
.slot { padding: 20px 6px 14px 0; }
.cell { padding: 0 0 14px; }
.cell.ours { background: #000; color: #fff; padding: 8px 8px 12px; margin: -8px 0 6px -8px; }
.camera { font-weight: 700; font-size: 20px; margin-top: 8px; }
.project { font-size: 16px; color: #444; margin-top: 4px; }
.ours .project { color: #fff; font-weight: 700; }
.project.research { font-style: italic; color: #888; }
.legend { display: flex; gap: 70px; margin-top: 36px; font-size: 26px; color: #333; }
.key { display: flex; align-items: center; gap: 20px; }
.mini svg { width: 76px; height: 47px; display: block; }
.mini.ours svg { background: #000; }
</style></head><body><main>
<h1>Olympus Custom Firmware</h1>
<div class="axis"><div></div>${allYears.map((y) => `<div class="year">${y}</div>`).join('')}</div>
<div class="lanes">${lanes}</div>
<div class="legend">${legend}</div>
</main></body></html>`
const pageFile = path.join(ROOT, 'build/landscape.html')
fs.mkdirSync(path.dirname(pageFile), { recursive: true })
fs.writeFileSync(pageFile, html)
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: WIDTH, height: 800 } })
await page.goto(`file://${pageFile}`)
await page.evaluate(() => document.fonts.ready)
await page.screenshot({ path: OUT, fullPage: true })
await browser.close()
console.log(`wrote ${path.relative(ROOT, OUT)}: ${rows.length} cameras in ${GENS.length} generations`)
