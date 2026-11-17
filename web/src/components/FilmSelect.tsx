import { Label, Listbox, ListboxButton, ListboxOption, ListboxOptions } from '@headlessui/react'
import { ChevronUpDownIcon } from '@heroicons/react/16/solid'
import { CheckIcon } from '@heroicons/react/20/solid'
import { films, filmById, type Film } from '../lib/films'

interface Props {
  art: number
  value: string
  builtIn: string
  onChange: (film: Film) => void
}

/** The film of one ART slot (Tailwind UI select menu with secondary text). */
export function FilmSelect({ art, value, builtIn, onChange }: Props) {
  const selected = filmById(value)
  return (
    <Listbox as="div" value={selected} onChange={onChange} by="id">
      <Label className="block text-sm/6 font-medium text-gray-900 dark:text-white">
        Film <span className="sr-only">of ART {art}</span>
      </Label>
      <div className="relative mt-2">
        <ListboxButton className="grid w-full cursor-default grid-cols-1 rounded-md bg-white py-1.5 pr-2 pl-3 text-left text-gray-900 outline-1 -outline-offset-1 outline-gray-300 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-indigo-600 sm:text-sm/6 dark:bg-white/5 dark:text-white dark:outline-white/10 dark:focus-visible:outline-indigo-500">
          <span className="col-start-1 row-start-1 flex w-full gap-2 pr-6">
            <span className="truncate">{selected.film}</span>
            {selected.id === builtIn && <span className="truncate text-gray-500 dark:text-gray-400">built in</span>}
          </span>
          <ChevronUpDownIcon
            aria-hidden="true"
            className="col-start-1 row-start-1 size-5 self-center justify-self-end text-gray-500 sm:size-4 dark:text-gray-400"
          />
        </ListboxButton>

        <ListboxOptions
          transition
          className="absolute z-10 mt-1 max-h-72 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg outline-1 outline-black/5 data-leave:transition data-leave:duration-100 data-leave:ease-in data-closed:data-leave:opacity-0 sm:text-sm dark:bg-gray-800 dark:shadow-none dark:-outline-offset-1 dark:outline-white/10"
        >
          {films.map((film) => (
            <ListboxOption
              key={film.id}
              value={film}
              className="group relative cursor-default py-2 pr-9 pl-3 text-gray-900 select-none data-focus:bg-indigo-600 data-focus:text-white data-focus:outline-hidden dark:text-white dark:data-focus:bg-indigo-500"
            >
              <div className="flex flex-col">
                <span className="truncate font-normal group-data-selected:font-semibold">
                  {film.film}
                  {film.id === builtIn && ' (built in)'}
                </span>
                <span className="truncate text-gray-500 group-data-focus:text-indigo-200 dark:text-gray-400 dark:group-data-focus:text-indigo-100">
                  {film.medium}
                  {film.note && !film.note.startsWith('built in') ? ` · ${film.note}` : ''}
                </span>
              </div>
              <span className="absolute inset-y-0 right-0 flex items-center pr-4 text-indigo-600 group-not-data-selected:hidden group-data-focus:text-white dark:text-indigo-400">
                <CheckIcon aria-hidden="true" className="size-5" />
              </span>
            </ListboxOption>
          ))}
        </ListboxOptions>
      </div>
    </Listbox>
  )
}
