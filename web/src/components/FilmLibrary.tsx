import { PlusIcon } from '@heroicons/react/20/solid'
import type { Film } from '../lib/films'

interface Props {
  films: readonly Film[]
  canAdd: boolean
  onAdd: (film: Film) => void
}

/** The films that are not in the menu, each with an Add button. */
export function FilmLibrary({ films, canAdd, onAdd }: Props) {
  if (films.length === 0) return <p className="text-sm text-gray-500 dark:text-gray-400">Every film is in the menu.</p>
  return (
    <ul className="divide-y divide-gray-200 dark:divide-white/10">
      {films.map((film) => (
        <li key={film.id} className="flex items-center gap-x-3 py-3 pr-3 pl-1">
          <span className="min-w-0 flex-auto">
            <span className="block truncate text-sm text-gray-900 dark:text-white">{film.film}</span>
            <span className="block truncate text-xs text-gray-500 dark:text-gray-400">{film.kind}</span>
          </span>
          <button
            type="button"
            disabled={!canAdd}
            onClick={() => {
              onAdd(film)
            }}
            aria-label={`Add ${film.film}`}
            className="inline-flex items-center gap-x-1.5 rounded-md bg-white px-2.5 py-1.5 text-sm font-semibold text-gray-900 shadow-xs inset-ring inset-ring-gray-300 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white/10 dark:text-white dark:shadow-none dark:inset-ring-white/5 dark:hover:bg-white/20"
          >
            <PlusIcon aria-hidden="true" className="-ml-0.5 size-5" />
            Add
          </button>
        </li>
      ))}
    </ul>
  )
}
