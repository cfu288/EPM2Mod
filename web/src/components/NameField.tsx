import { ExclamationCircleIcon } from '@heroicons/react/16/solid'
import { nameProblem, NAME_BYTES } from '../lib/lookfile'

interface Props {
  art: number
  value: string
  onChange: (name: string) => void
}

/** The name the camera shows for one ART slot (Tailwind UI input with help text / validation error). */
export function NameField({ art, value, onChange }: Props) {
  const id = `name-${String(art)}`
  const problem = nameProblem(value)
  return (
    <div>
      <label htmlFor={id} className="block text-sm/6 font-medium text-gray-900 dark:text-white">
        Name on the camera
      </label>
      <div className="mt-2 grid grid-cols-1">
        <input
          id={id}
          type="text"
          value={value}
          maxLength={NAME_BYTES}
          spellCheck={false}
          onChange={(event) => {
            onChange(event.target.value)
          }}
          aria-invalid={problem !== null}
          aria-describedby={`${id}-help`}
          className={
            problem
              ? 'col-start-1 row-start-1 block w-full rounded-md bg-white py-1.5 pr-10 pl-3 text-red-900 outline-1 -outline-offset-1 outline-red-300 placeholder:text-red-300 focus:outline-2 focus:-outline-offset-2 focus:outline-red-600 sm:pr-9 sm:text-sm/6 dark:bg-white/5 dark:text-red-400 dark:outline-red-500/50'
              : 'col-start-1 row-start-1 block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-600 sm:text-sm/6 dark:bg-white/5 dark:text-white dark:outline-white/10'
          }
        />
        {problem && (
          <ExclamationCircleIcon
            aria-hidden="true"
            className="pointer-events-none col-start-1 row-start-1 mr-3 size-5 self-center justify-self-end text-red-500 sm:size-4"
          />
        )}
      </div>
      <p
        id={`${id}-help`}
        className={problem ? 'mt-2 text-sm text-red-600 dark:text-red-400' : 'mt-2 text-sm text-gray-500'}
      >
        {problem ?? `Up to ${String(NAME_BYTES)} characters.`}
      </p>
    </div>
  )
}
