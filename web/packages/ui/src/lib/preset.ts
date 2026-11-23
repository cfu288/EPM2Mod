import type { SlotItem } from './selection'

/** The default film simulations, ART 1 to 12: the installer page sends them as 12 choices, and the site fills a look pack with them. */
export const PRESET: readonly string[] = [
  'portra-400',
  'ektachrome',
  'pro-400h',
  'kodachrome',
  'double-x',
  'vision3-250d',
  'velvia',
  'superia-400',
  'provia',
  'portra-160',
  'gold-200',
  'vision3-500t',
]

/** The rows of the ART-menu editor with the default film simulations. */
export function presetSlots(): SlotItem[] {
  return PRESET.map((filmId) => ({ key: filmId, filmId }))
}
