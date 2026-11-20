import { CheckIcon } from '@heroicons/react/20/solid'

interface Props {
  steps: readonly string[]
  /** The step shown now, from 0. */
  current: number
  /** Whether a step other than the current one can be opened now: an earlier one, or a later one already reached. */
  canGo: (step: number) => boolean
  onGo: (step: number) => void
}

/** The installer's steps in a row: done ones with a tick, the current one filled; the ones it can open are buttons. */
export function Timeline({ steps, current, canGo, onGo }: Props) {
  return (
    <nav aria-label="Steps">
      <p className="mb-3 text-sm font-bold sm:hidden">
        Step {current + 1} of {steps.length}: {steps[current]}
      </p>
      <ol className="flex items-center">
        {steps.map((label, index) => {
          // a later step that can be opened was done before the user went back
          const done = index < current || (index > current && canGo(index))
          const mark = (
            <>
              <span
                className={`flex size-7 shrink-0 items-center justify-center border text-xs ${
                  done || index === current ? 'border-ink bg-ink text-white' : 'border-rule text-muted'
                }`}
              >
                {done ? <CheckIcon aria-hidden="true" className="size-4" /> : index + 1}
              </span>
              <span className={`hidden text-sm sm:inline ${index === current ? 'font-bold' : 'text-muted'}`}>
                {label}
              </span>
            </>
          )
          return (
            <li
              key={label}
              aria-current={index === current ? 'step' : undefined}
              className="flex flex-1 items-center gap-x-2 last:flex-none"
            >
              {index !== current && canGo(index) ? (
                <button
                  type="button"
                  aria-label={label}
                  onClick={() => {
                    onGo(index)
                  }}
                  className="flex items-center gap-x-2"
                >
                  {mark}
                </button>
              ) : (
                <span className="flex items-center gap-x-2">{mark}</span>
              )}
              {index < steps.length - 1 && (
                <span aria-hidden="true" className={`mx-2 h-px flex-1 ${done ? 'bg-ink' : 'bg-rule'}`} />
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
