// Make docs/images/landscape.png, the timeline of Olympus custom firmware, from the table in docs/reference/landscape.md.
//
//     node web/scripts/landscape.mjs
//
// Each row of the table (Announced | Camera | Projects) is one camera under its year. A project marked "(research
// only)" is drawn with a dashed camera, EPM2Mod (bold in the table) as a black cell. PEN bodies (E-P..., PEN-F) get the
// flat-top camera, the others the one with a prism hump. The page is drawn by Chromium (Playwright) with the site's
// fonts, then saved as a PNG.
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
    const [year, camera, projects] = line
      .split('|')
      .slice(1, 4)
      .map((cell) => cell.trim())
    const names = projects.split(/,\s*(?![^[]*\])/).map((p) => ({
      name: p
        .replace(/\*\*/g, '')
        .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
        .replace(/\s*\(research only\)/, ''),
      research: /\(research only\)/.test(p),
      ours: /^\*\*/.test(p),
    }))
    return { year, camera, projects: names }
  })
if (rows.length === 0) throw new Error(`no rows in ${SOURCE}`)
const years = [...new Set(rows.map((r) => r.year))]
// at most PER_LINE years side by side; more years go on a second timeline below
const PER_LINE = 7
const lines = []
for (let i = 0; i < years.length; i += PER_LINE) lines.push(years.slice(i, i + PER_LINE))

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

const font = (file) => `file://${path.join(WEB, 'node_modules/@fontsource', file)}`
const html = `<!doctype html><html><head><style>
@font-face { font-family: Sora; font-weight: 800; src: url(${font('sora/files/sora-latin-800-normal.woff2')}); }
@font-face { font-family: Arimo; font-weight: 400; src: url(${font('arimo/files/arimo-latin-400-normal.woff2')}); }
@font-face { font-family: Arimo; font-weight: 700; src: url(${font('arimo/files/arimo-latin-700-normal.woff2')}); }
@font-face { font-family: Arimo; font-weight: 400; font-style: italic; src: url(${font('arimo/files/arimo-latin-400-italic.woff2')}); }
body { margin: 0; width: ${WIDTH}px; background: #fff; color: #000; font-family: Arimo, sans-serif; }
main { padding: 64px 80px 48px; }
h1 { border-top: 24px solid #000; margin: 0; padding-top: 40px; font: 800 58px Sora, sans-serif; letter-spacing: -0.02em; }
.years { display: grid; grid-template-columns: repeat(${Math.min(years.length, PER_LINE)}, 1fr); margin-top: 52px; }
.year { font: 800 48px Sora, sans-serif; padding-bottom: 14px; border-bottom: 4px solid #000; position: relative; }
.year::after { content: ''; position: absolute; left: 0; bottom: -12px; width: 4px; height: 24px; background: #000; }
.column { padding: 34px 24px 0 0; }
.cell { border-top: 2px solid #ddd; padding: 32px 0 26px; }
.cell.ours { background: #000; color: #fff; border-top-color: #000; margin: 0 -2px 0 -12px; padding-left: 12px; padding-right: 2px; }
.camera { font-weight: 700; font-size: 30px; margin-top: 18px; }
.project { font-size: 26px; color: #444; margin-top: 10px; }
.ours .project { color: #fff; font-weight: 700; }
.project.research { font-style: italic; color: #888; }
.legend { display: flex; gap: 70px; margin-top: 40px; padding-top: 34px; border-top: 2px solid #ddd; font-size: 26px; color: #333; }
.key { display: flex; align-items: center; gap: 20px; }
.mini svg { width: 76px; height: 47px; display: block; }
.mini.ours svg { background: #000; }
</style></head><body><main>
<h1>Olympus Custom Firmware</h1>
${lines
  .map(
    (line) => `<div class="years">${line.map((y) => `<div class="year">${y}</div>`).join('')}</div>
<div class="years" style="margin-top: 0">${line
      .map(
        (y) =>
          `<div class="column">${rows
            .filter((r) => r.year === y)
            .map(cell)
            .join('')}</div>`,
      )
      .join('')}</div>`,
  )
  .join('')}
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
console.log(`wrote ${path.relative(ROOT, OUT)}: ${rows.length} cameras in ${years.length} years`)
