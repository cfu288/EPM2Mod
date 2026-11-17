import { filmById, slots } from './films'
import { decodeBase64, packLooks } from './lookfile'

/** One of the twelve ART slots in order: a film, or empty (the camera keeps its own look there). */
export interface SlotItem {
  /** Stable key for drag and drop: the film's id, or a key of its own for an empty slot. */
  key: string
  filmId: string | null
}

export const SLOT_COUNT = 12

/** The films the camera holds without a look file, in ART order. */
export function builtInSlots(): SlotItem[] {
  return slots.map((slot) => ({ key: slot.builtIn, filmId: slot.builtIn }))
}

let emptyCount = 0
function emptySlot(): SlotItem {
  emptyCount += 1
  return { key: `empty-${String(emptyCount)}`, filmId: null }
}

/** Move the slot at `from` to `to`; the slots between shift by one. */
export function moveSlot(items: readonly SlotItem[], from: number, to: number): SlotItem[] {
  const next = [...items]
  const [moved] = next.splice(from, 1)
  if (!moved) return next
  next.splice(to, 0, moved)
  return next
}

/** Empty the slot at `index`. */
export function removeFilm(items: readonly SlotItem[], index: number): SlotItem[] {
  return items.map((item, i) => (i === index ? emptySlot() : item))
}

/** The first empty slot, or -1. */
export function firstEmpty(items: readonly SlotItem[]): number {
  return items.findIndex((item) => item.filmId === null)
}

/** Put a film into the slot at `index` (a film is in at most one slot). */
export function addFilm(items: readonly SlotItem[], index: number, filmId: string): SlotItem[] {
  if (items.some((item) => item.filmId === filmId)) return [...items]
  return items.map((item, i) => (i === index ? { key: filmId, filmId } : item))
}

/** The look file of the filled slots: slot i holds ART i + 1. */
export function lookFile(items: readonly SlotItem[]): Uint8Array {
  return packLooks(
    items.flatMap((item, index) => {
      if (!item.filmId) return []
      const film = filmById(item.filmId)
      return [{ record: decodeBase64(film.record), art: index + 1, name: film.name }]
    }),
  )
}

/** The command-line choices of the filled slots, for example `ART2=velvia` (`epm2mod looks pack`, `epm2mod serve`). */
export function choicesOf(items: readonly SlotItem[]): string[] {
  return items.flatMap((item, index) => (item.filmId ? [`ART${String(index + 1)}=${item.filmId}`] : []))
}
