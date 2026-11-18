import { useEffect, useRef } from 'react'
import raw from './assets/epm2-home.svg?raw'
import bits from './assets/mod-bits.txt?raw'
import './drawing.css'

const RAINBOW = 7 // stops in the gradient; drawing.css cycles each through the colours, one step apart
const FLOW = 4 // s: the rainbow's cycle; keep equal to the drawing-rainbow animation in drawing.css
const COLUMNS = 84 // of the bit cloud across the drawing
const SHADES = [0.3, 0.55, 0.85] // the cloud's opacity, from its fringe to its middle
const SPARKS = 1 / 8 // the share of digits that twinkle and flip on hover
const FLIP_EVERY = 140 // ms between bit flips while the pointer is over the drawing

type Box = [number, number, number, number]

/** A fixed random number in [0, 1] for each pair of integers. */
function hash(i: number, j: number): number {
  let h = Math.imul(i, 374761393) + Math.imul(j, 668265263)
  h = Math.imul(h ^ (h >>> 13), 1274126177)
  return ((h ^ (h >>> 16)) >>> 0) / 4294967295
}

/** Smooth noise in [0, 1]: random values on a grid, blended between with smoothstep. */
function noise(x: number, y: number): number {
  const at = hash
  const i = Math.floor(x)
  const j = Math.floor(y)
  const s = (t: number) => t * t * (3 - 2 * t)
  const u = s(x - i)
  const v = s(y - j)
  const top = at(i, j) + (at(i + 1, j) - at(i, j)) * u
  const bottom = at(i, j + 1) + (at(i + 1, j + 1) - at(i, j + 1)) * u
  return top + (bottom - top) * v
}

/**
 * EPM2Mod's own patch bytes as 0s and 1s, in a cloud behind the drawing: thick in the middle, broken up toward the
 * edges by noise. One text per row and shade, each digit placed at its column; the sparks (drawing.css: twinkle,
 * Drawing: flip) are texts of their own.
 */
function bitCloud([x, y, w, h]: Box): string {
  const pitch = w / COLUMNS
  const rows = Math.floor(h / (pitch * 1.6))
  const lineHeight = h / rows
  const texts: string[] = []
  const sparks: string[] = []
  let next = 0
  for (let r = 0; r < rows; r++) {
    const cells = SHADES.map(() => ({ xs: [] as string[], digits: '' }))
    const baseline = (y + (r + 0.8) * lineHeight).toFixed(2)
    for (let c = 0; c < COLUMNS; c++) {
      const dx = (c / (COLUMNS - 1)) * 2 - 1
      const dy = (r / (rows - 1)) * 2 - 1
      const fade = 1 - Math.min(1, Math.hypot(dx, dy))
      const cloud = 0.65 * noise(c / 9, r / 6) + 0.35 * noise(c / 3.5 + 40, r / 2.5 + 40)
      const value = fade * 1.8 * cloud
      if (value < 0.22) continue
      const shade = value < 0.4 ? 0 : value < 0.6 ? 1 : 2
      const digit = bits[next++ % (bits.length - 1)] ?? '0'
      const cx = (x + c * pitch).toFixed(2)
      if (hash(c + 1000, r + 1000) < SPARKS) {
        const period = 4 + 5 * hash(c, r + 2000)
        const delay = -period * hash(c + 3000, r)
        sparks.push(
          `<text class="bit-spark" x="${cx}" y="${baseline}" ` +
            `style="--o:${String(SHADES[shade])};--t:${period.toFixed(2)}s;--d:${delay.toFixed(2)}s">${digit}</text>`,
        )
        continue
      }
      const cell = cells[shade]
      if (!cell) continue
      cell.xs.push(cx)
      cell.digits += digit
    }
    cells.forEach((cell, s) => {
      if (cell.digits)
        texts.push(
          `<text x="${cell.xs.join(' ')}" y="${baseline}" fill-opacity="${String(SHADES[s])}">${cell.digits}</text>`,
        )
    })
  }
  return (
    `<g class="drawing-bits" aria-hidden="true" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" ` +
    `font-size="${(lineHeight * 0.78).toFixed(2)}">${texts.join('')}${sparks.join('')}</g>`
  )
}

/** The drawing inline, so its lines can be styled: grey, and on hover a moving rainbow, a little thicker. */
function decorate(svg: string): string {
  const box = (/viewBox="([^"]+)"/.exec(svg)?.[1] ?? '').split(/[\s,]+/).map(Number)
  const [x = 0, y = 0, w = 100, h = 100] = box
  const stops = Array.from(
    { length: RAINBOW },
    (_, i) => `<stop offset="${String(i / (RAINBOW - 1))}" style="animation-delay:${String((-i / RAINBOW) * FLOW)}s"/>`,
  ).join('')
  const defs =
    `<defs><linearGradient id="drawing-rainbow" gradientUnits="userSpaceOnUse" ` +
    `x1="${String(x)}" y1="${String(y)}" x2="${String(x + w)}" y2="${String(y + h)}">${stops}</linearGradient></defs>`
  // the lines take their colour from drawing.css; a rainbow copy on top of them fades in on hover
  return svg
    .replace(/<g ([^>]*)>/, (_, attrs: string) => {
      const kept = attrs.replace(/\s*stroke(-width)?="[^"]*"/g, '')
      return `<g id="drawing-lines" class="drawing-lines" ${kept}>`
    })
    .replace(/<\/svg>\s*$/, '<use href="#drawing-lines" class="drawing-glow"/></svg>')
    .replace(/<svg /, '<svg class="drawing" role="img" aria-label="The E-PM2, taken apart" ')
    .replace(/(<svg[^>]*>)/, `$1${defs}${bitCloud([x, y, w, h])}`)
}

const html = decorate(raw)

/** While the pointer is over the drawing, a random spark flips 0 <-> 1 with a short dark flash, then flips back. */
function useBitFlips(root: React.RefObject<HTMLDivElement | null>) {
  useEffect(() => {
    const el = root.current
    if (!el) return
    let timer: number | undefined
    const flip = () => {
      const sparks = el.querySelectorAll<SVGTextElement>('.bit-spark')
      const spark = sparks[Math.floor(Math.random() * sparks.length)]
      if (!spark || spark.dataset.flipping) return
      const digit = spark.textContent
      spark.dataset.flipping = '1'
      spark.textContent = digit === '0' ? '1' : '0'
      const flash = spark.animate([{ fill: '#6f6f6f', fillOpacity: 1, fontWeight: 700 }, {}], {
        duration: 1100,
        easing: 'ease-out',
      })
      flash.onfinish = () => {
        spark.textContent = digit
        delete spark.dataset.flipping
      }
    }
    const start = () => {
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
      timer = window.setInterval(flip, FLIP_EVERY)
    }
    const stop = () => {
      window.clearInterval(timer)
    }
    el.addEventListener('pointerenter', start)
    el.addEventListener('pointerleave', stop)
    return () => {
      stop()
      el.removeEventListener('pointerenter', start)
      el.removeEventListener('pointerleave', stop)
    }
  }, [root])
}

export function Drawing({ className = '' }: { className?: string }) {
  const root = useRef<HTMLDivElement>(null)
  useBitFlips(root)
  return <div ref={root} className={className} dangerouslySetInnerHTML={{ __html: html }} />
}
