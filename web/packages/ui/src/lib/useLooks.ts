import { useState } from 'react'
import { films, type Film } from './films'
import { addFilm, firstEmpty, moveSlot, removeFilm, type SlotItem } from './selection'

/** The films chosen for ART 1 to 12 and the selected row: the state of the ART-menu editor. */
export interface Looks {
  items: SlotItem[]
  /** The selected row, 0 to 11: the one the preview shows. */
  selected: number
  select: (index: number) => void
  move: (from: number, to: number) => void
  remove: (index: number) => void
  /** Put a film into the selected row if it is empty, else into the first empty row. */
  add: (film: Film) => void
  /** Go back to the rows the editor started with. */
  reset: () => void
  /** The row that Add fills: the selected row if it is empty, else the first empty row, or -1. */
  empty: number
  /** The films that are in no row. */
  unused: readonly Film[]
}

/** The state of the ART-menu editor; it starts with the rows that `initial` returns (the app's own choice). */
export function useLooks(initial: () => SlotItem[]): Looks {
  const [items, setItems] = useState<SlotItem[]>(initial)
  const [selected, setSelected] = useState(0)
  const empty = items[selected]?.filmId === null ? selected : firstEmpty(items)
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
      setItems(initial())
      setSelected(0)
    },
    empty,
    unused: films.filter((film) => !items.some((item) => item.filmId === film.id)),
  }
}
