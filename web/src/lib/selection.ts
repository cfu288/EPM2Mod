import { filmById, isFilmId, slots, type Film } from './films'
import { decodeBase64, nameProblem, packLooks } from './lookfile'

/** What the user chose for one ART slot: a film, and the name the camera shows. */
export interface SlotChoice {
  art: number
  filmId: string
  name: string
}

/** Every slot with its built-in film and name: what the camera holds without a look file. */
export function builtInChoices(): SlotChoice[] {
  return slots.map((slot) => ({ art: slot.art, filmId: slot.builtIn, name: filmById(slot.builtIn).name }))
}

/** True if a slot differs from what the camera holds without a look file. */
export function isChanged(choice: SlotChoice): boolean {
  const slot = slots[choice.art - 1]
  if (!slot) return false
  return choice.filmId !== slot.builtIn || choice.name !== filmById(slot.builtIn).name
}

/** The look file of the changed slots; the camera keeps the built-in look in every other slot. */
export function lookFile(choices: readonly SlotChoice[]): Uint8Array {
  return packLooks(
    choices
      .filter(isChanged)
      .map((choice) => ({ record: decodeBase64(filmById(choice.filmId).record), art: choice.art, name: choice.name })),
  )
}

export function choicesValid(choices: readonly SlotChoice[]): boolean {
  return choices.every((choice) => nameProblem(choice.name) === null)
}

/** A choice with another film; a name that was the old film's own becomes the new film's. */
export function withFilm(choice: SlotChoice, film: Film): SlotChoice {
  const keepName = choice.name !== filmById(choice.filmId).name
  return { ...choice, filmId: film.id, name: keepName ? choice.name : film.name }
}

/** The changed slots as URL parameters: art2=velvia, and name2=... when the name is not the film's own. */
export function toSearch(choices: readonly SlotChoice[]): string {
  const params = new URLSearchParams()
  for (const choice of choices.filter(isChanged)) {
    params.set(`art${String(choice.art)}`, choice.filmId)
    if (choice.name !== filmById(choice.filmId).name) params.set(`name${String(choice.art)}`, choice.name)
  }
  const text = params.toString()
  return text ? `?${text}` : ''
}

/** The choices of URL parameters (unknown films and slots are ignored). */
export function fromSearch(search: string): SlotChoice[] {
  const params = new URLSearchParams(search)
  return builtInChoices().map((choice) => {
    const filmId = params.get(`art${String(choice.art)}`)
    if (!filmId || !isFilmId(filmId)) return choice
    const name = params.get(`name${String(choice.art)}`) ?? filmById(filmId).name
    return { ...choice, filmId, name }
  })
}
