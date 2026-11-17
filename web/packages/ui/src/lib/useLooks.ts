import { useState } from 'react'
import { films, type Film } from './films'
import { addFilm, builtInSlots, firstEmpty, moveSlot, removeFilm, type SlotItem } from './selection'

/** The films chosen for ART 1 to 12 and the selected row: the state of the ART-menu editor. */
export interface Looks {
  items: SlotItem[]
  /** The selected row, 0 to 11: the one the preview shows. */
  selected: number
  select: (index: number) => void
  move: (from: number, to: number) => void
  remove: (index: number) => void
  /** Put a film into the first empty row. */
  add: (film: Film) => void
  /** Go back to the films built into the firmware, in their order. */
  reset: () => void
  /** The first empty row, or -1. */
  empty: number
  /** The films that are in no row. */
  unused: readonly Film[]
}

/** The state of the ART-menu editor; it starts with the films built into the firmware. */
export function useLooks(): Looks {
  const [items, setItems] = useState<SlotItem[]>(builtInSlots)
  const [selected, setSelected] = useState(0)
  const empty = firstEmpty(items)
  return {
    items,
    selected,
    select: setSelected,
    move: (from, to) => {
      setItems((all) => moveSlot(all, from, to))
      setSelected(to)
    },
    remove: (index) => {
      setItems((all) => removeFilm(all, index))
      setSelected(index)
    },
    add: (film) => {
      if (empty < 0) return
      setItems((all) => addFilm(all, empty, film.id))
      setSelected(empty)
    },
    reset: () => {
      setItems(builtInSlots())
      setSelected(0)
    },
    empty,
    unused: films.filter((film) => !items.some((item) => item.filmId === film.id)),
  }
}
