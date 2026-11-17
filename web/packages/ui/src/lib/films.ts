import data from '../../../../../looks/film-records.json'

/** A fitted film the look file can hold (looks/film-records.json in the repository, made from looks/catalogue.json). */
export interface Film {
  id: string
  /** The name the camera shows, at most 16 characters. */
  name: string
  film: string
  /** What kind of film it is, in a few words, for example "Slide". */
  kind: string
  note: string
  /** The 1,708-byte look record for slot 0 under `name`, base64. */
  record: string
}

/** An art-filter entry of the camera: ART 1 to 12. */
export interface Slot {
  art: number
  /** The entry's stock Olympus name. */
  entry: string
  /** The film the entry holds when no look is loaded. */
  builtIn: string
}

export const films: readonly Film[] = data.films
export const slots: readonly Slot[] = data.slots

const byId = new Map(films.map((film) => [film.id, film]))

/** The film of an id; throws for an unknown id (the data is generated, so this is a programming error). */
export function filmById(id: string): Film {
  const film = byId.get(id)
  if (!film) throw new Error(`no film '${id}'`)
  return film
}
