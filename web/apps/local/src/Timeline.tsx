import { CheckIcon } from '@heroicons/react/20/solid'

interface Props {
  steps: readonly string[]
  /** The step shown now, from 0. */
  current: number
  /** Go back to an earlier step; null while that is not allowed. */
  onBack: ((step: number) => void) | null
}

/** The installer's steps in a row: done ones with a tick (and a link back), the current one filled. */
export function Timeline({ steps, current, onBack }: Props) {
  return (
    <nav aria-label="Steps">
      <ol className="flex items-center">
        {steps.map((label, index) => {
          const done = index < current
          const mark = (
            <>
              <span
                className={`flex size-7 shrink-0 items-center justify-center border text-xs ${
                  index <= current ? 'border-ink bg-ink text-white' : 'border-rule text-muted'
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
              {done && onBack ? (
                <button
                  type="button"
                  onClick={() => {
                    onBack(index)
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
