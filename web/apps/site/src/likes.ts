import { useState } from 'react'
import { films, PRESET, SLOT_COUNT, type SlotItem } from '@epm2mod/ui'

/** The localStorage key of the liked film simulations. */
const LIKES = 'epm2mod-liked-films'

function readLikes(): string[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(LIKES) ?? '[]')
    return Array.isArray(value) ? value.filter((id): id is string => typeof id === 'string') : []
  } catch {
    return []
  }
}

function saveLikes(ids: readonly string[]) {
  try {
    localStorage.setItem(LIKES, JSON.stringify(ids))
  } catch {
    // private mode or blocked storage: the likes last until the page closes
  }
}

/** The ids of the liked film simulations, and a function that likes or unlikes one. */
export function useLikes(): [string[], (id: string) => void] {
  const [liked, setLiked] = useState(readLikes)
  const toggle = (id: string) => {
    const next = liked.includes(id) ? liked.filter((x) => x !== id) : [...liked, id]
    setLiked(next)
    saveLikes(next)
  }
  return [liked, toggle]
}

/**
 * The 12 ART entries of a look pack: the liked film simulations first, in the order the site lists them, then the
 * defaults that are not liked. A like pushes the last default out; with 12 or more likes, the first 12 liked fill it.
 */
export function packSlots(liked: readonly string[]): SlotItem[] {
  const first = films.map((film) => film.id).filter((id) => liked.includes(id))
  return [...first, ...PRESET.filter((id) => !liked.includes(id))]
    .slice(0, SLOT_COUNT)
    .map((filmId) => ({ key: filmId, filmId }))
}
