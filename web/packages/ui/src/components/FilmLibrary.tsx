import { PlusIcon } from '@heroicons/react/20/solid'
import type { Film } from '../lib/films'

interface Props {
  films: readonly Film[]
  canAdd: boolean
  onAdd: (film: Film) => void
}

/** The films that are not in the menu, each with an Add button. */
export function FilmLibrary({ films, canAdd, onAdd }: Props) {
  if (films.length === 0) return <p className="text-muted text-sm">Every film simulation is in the menu.</p>
  return (
    <ul className="divide-rule border-rule divide-y border-y">
      {films.map((film) => (
        <li key={film.id} className="flex items-center gap-x-3 py-3 pr-2 pl-2">
          <span className="min-w-0 flex-auto">
            <span className="block truncate">{film.film}</span>
            <span className="text-muted block truncate text-xs">{film.kind}</span>
          </span>
          <button
            type="button"
            disabled={!canAdd}
            onClick={() => {
              onAdd(film)
            }}
            aria-label={`Add ${film.film}`}
            className="btn py-1.5"
          >
            <PlusIcon aria-hidden="true" className="-ml-1 size-4" />
            Add
          </button>
        </li>
      ))}
    </ul>
  )
}
