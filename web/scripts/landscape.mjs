// Make docs/images/landscape.png, the timeline of Olympus custom firmware, and docs/images/features-by-generation.png,
// the feature grid, from the two tables in docs/reference/landscape.md.
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
    const [year, camera, , projects] = line
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
main { padding: 64px 80px 48px; position: relative; }
.line + .line { margin-top: 70px; }
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
    (line) => `<div class="line"><div class="years">${line.map((y) => `<div class="year">${y}</div>`).join('')}</div>
<div class="years" style="margin-top: 0">${line
      .map(
        (y) =>
          `<div class="column">${rows
            .filter((r) => r.year === y)
            .map(cell)
            .join('')}</div>`,
      )
      .join('')}</div></div>`,
  )
  .join('')}
<svg id="bends" style="position: absolute; left: 0; top: 0; overflow: visible" width="1" height="1"></svg>
<div class="legend">${legend}</div>
</main></body></html>`

const pageFile = path.join(ROOT, 'build/landscape.html')
fs.mkdirSync(path.dirname(pageFile), { recursive: true })
fs.writeFileSync(pageFile, html)
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: WIDTH, height: 800 } })
await page.goto(`file://${pageFile}`)
await page.evaluate(() => document.fonts.ready)
// one timeline: each line runs off its right end, back across the gap below it, and into the next line's start
await page.evaluate(() => {
  const main = document.querySelector('main').getBoundingClientRect()
  const lines = [...document.querySelectorAll('.line')]
  const R = 36
  const G = 44
  let d = ''
  for (let i = 0; i + 1 < lines.length; i++) {
    const end = [...lines[i].querySelectorAll('.year')].at(-1).getBoundingClientRect()
    const start = lines[i + 1].querySelector('.year').getBoundingClientRect()
    const x1 = end.right - main.left
    const y1 = end.bottom - 2 - main.top
    const x2 = start.left - main.left
    const y2 = start.bottom - 2 - main.top
    const mid = (lines[i].getBoundingClientRect().bottom + lines[i + 1].getBoundingClientRect().top) / 2 - main.top
    d += `M ${x1} ${y1} H ${x1 + G - R} A ${R} ${R} 0 0 1 ${x1 + G} ${y1 + R} V ${mid - R} A ${R} ${R} 0 0 1 ${x1 + G - R} ${mid}`
    d += ` H ${x2 - G + R} A ${R} ${R} 0 0 0 ${x2 - G} ${mid + R} V ${y2 - R} A ${R} ${R} 0 0 0 ${x2 - G + R} ${y2} H ${x2}`
  }
  // an arrow at the end of the last line: the timeline goes on
  const last = [...lines.at(-1).querySelectorAll('.year')].at(-1).getBoundingClientRect()
  const ax = last.right - main.left
  const ay = last.bottom - 2 - main.top
  const arrow = `M ${ax} ${ay} H ${ax + 30} M ${ax + 14} ${ay - 14} L ${ax + 32} ${ay} L ${ax + 14} ${ay + 14}`
  document.getElementById('bends').innerHTML =
    `<path d="${d}" fill="none" stroke="#000" stroke-width="4"/>` +
    `<path d="${arrow}" fill="none" stroke="#000" stroke-width="4" stroke-linecap="square"/>`
})
await page.screenshot({ path: OUT, fullPage: true })

// the feature grid: one row per feature, one column per generation; each cell starts with its status
const md = fs.readFileSync(SOURCE, 'utf8').split('\n')
const head = md.findIndex((line) => line.startsWith('| Feature |'))
if (head < 0) throw new Error(`no feature table in ${SOURCE}`)
const gens = md[head]
  .split('|')
  .slice(2, -1)
  .map((c) => c.trim())
const grid = []
for (let i = head + 2; md[i]?.startsWith('|'); i++) {
  const cells = md[i]
    .split('|')
    .slice(1, -1)
    .map((c) => c.trim())
  grid.push({ feature: cells[0], cells: cells.slice(1) })
}
const STATUSES = [
  ['stock', 'Stock', 'the camera has it'],
  ['mod', 'Mod', 'a mod adds it'],
  ['notdone', 'Not done', 'the parts are there, nobody built it'],
  ['impossible', 'Not possible', 'a needed part is missing'],
  ['unknown', 'Unknown', 'no source settles it'],
]
const statusOf = (text) => {
  const first = text.split(';')[0]
  if (/^Stock/.test(first)) return 'stock'
  if (/^Mod/.test(first)) return 'mod'
  if (/^Not done/.test(first)) return 'notdone'
  if (/^Not possible/.test(first)) return 'impossible'
  return 'unknown'
}
const plain = (text) => text.replace(/`/g, '').replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
const gridHtml = `<!doctype html><html><head><style>
@font-face { font-family: Sora; font-weight: 800; src: url(${font('sora/files/sora-latin-800-normal.woff2')}); }
@font-face { font-family: Arimo; font-weight: 400; src: url(${font('arimo/files/arimo-latin-400-normal.woff2')}); }
@font-face { font-family: Arimo; font-weight: 700; src: url(${font('arimo/files/arimo-latin-700-normal.woff2')}); }
body { margin: 0; width: ${WIDTH}px; background: #fff; color: #000; font-family: Arimo, sans-serif; }
main { padding: 64px 80px 48px; }
h1 { border-top: 24px solid #000; margin: 0; padding-top: 40px; font: 800 58px Sora, sans-serif; letter-spacing: -0.02em; }
table { border-collapse: separate; border-spacing: 6px; width: 100%; margin-top: 40px; table-layout: fixed; }
th { font: 800 30px Sora, sans-serif; text-align: left; padding: 0 12px 10px; }
th.feature { width: 360px; }
td { font-size: 19px; line-height: 1.3; padding: 12px; vertical-align: top; }
td.feature { font-weight: 700; font-size: 21px; padding-left: 0; }
.stock { background: #000; color: #fff; }
.mod { background: #fff; border: 3px solid #000; }
.notdone { background: #e4e4e4; }
.impossible { background: repeating-linear-gradient(135deg, #fff 0 8px, #d0d0d0 8px 10px); color: #333; }
.unknown { background: #fff; border: 3px dashed #aaa; color: #777; }
.legend { display: flex; flex-wrap: wrap; gap: 18px 50px; margin-top: 30px; font-size: 22px; color: #333; }
.legend span.chip { display: inline-block; width: 40px; height: 26px; vertical-align: middle; margin-right: 12px; box-sizing: border-box; }
</style></head><body><main>
<h1>Features by Generation</h1>
<table><tr><th class="feature"></th>${gens.map((g) => `<th>TruePic ${g}</th>`).join('')}</tr>
${grid
  .map(
    (row) =>
      `<tr><td class="feature">${row.feature}</td>${row.cells
        .map((c) => `<td class="${statusOf(c)}">${plain(c)}</td>`)
        .join('')}</tr>`,
  )
  .join('\n')}</table>
<div class="legend">${STATUSES.map(([cls, name, what]) => `<div><span class="chip ${cls}"></span><b>${name}</b>: ${what}</div>`).join('')}</div>
</main></body></html>`
const GRID_OUT = path.join(ROOT, 'docs/images/features-by-generation.png')
const gridFile = path.join(ROOT, 'build/features-by-generation.html')
fs.writeFileSync(gridFile, gridHtml)
await page.goto(`file://${gridFile}`)
await page.evaluate(() => document.fonts.ready)
await page.screenshot({ path: GRID_OUT, fullPage: true })
console.log(`wrote ${path.relative(ROOT, GRID_OUT)}: ${grid.length} features x ${gens.length} generations`)
await browser.close()
console.log(`wrote ${path.relative(ROOT, OUT)}: ${rows.length} cameras in ${years.length} years`)
