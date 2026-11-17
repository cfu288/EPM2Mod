import { useEffect, useState } from 'react'
import { ArrowDownTrayIcon, ArrowUturnLeftIcon } from '@heroicons/react/20/solid'
import { InformationCircleIcon } from '@heroicons/react/20/solid'
import { FilmSelect } from './components/FilmSelect'
import { NameField } from './components/NameField'
import { StripPreview } from './components/StripPreview'
import { slots } from './lib/films'
import { CARD_NAME } from './lib/lookfile'
import {
  builtInChoices,
  choicesValid,
  fromSearch,
  isChanged,
  lookFile,
  toSearch,
  withFilm,
  type SlotChoice,
} from './lib/selection'

function download(bytes: Uint8Array) {
  const url = URL.createObjectURL(new Blob([bytes as BlobPart], { type: 'application/octet-stream' }))
  const link = document.createElement('a')
  link.href = url
  link.download = CARD_NAME
  link.click()
  URL.revokeObjectURL(url)
}

export default function App() {
  const [choices, setChoices] = useState<SlotChoice[]>(() => fromSearch(window.location.search))
  const [focus, setFocus] = useState(() => choices.find(isChanged)?.art ?? 1)

  // the URL holds the changes, so a choice can be shared or bookmarked
  useEffect(() => {
    window.history.replaceState(null, '', `${window.location.pathname}${toSearch(choices)}`)
  }, [choices])

  const update = (art: number, change: (choice: SlotChoice) => SlotChoice) => {
    setChoices((all) => all.map((choice) => (choice.art === art ? change(choice) : choice)))
    setFocus(art)
  }
  const changed = choices.filter(isChanged).length
  const valid = choicesValid(choices)
  const focused = choices.find((choice) => choice.art === focus) ?? choices[0]

  return (
    <div className="min-h-full">
      <header className="border-b border-gray-200 bg-white dark:border-white/10 dark:bg-gray-900">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">E-PM2 film looks</h1>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Choose a film for each art filter (ART 1 to 12) and download {CARD_NAME} for the camera.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          <section aria-labelledby="slots-heading" className="lg:col-span-2">
            <h2 id="slots-heading" className="sr-only">
              Art filters
            </h2>
            <ul className="divide-y divide-gray-200 dark:divide-white/10">
              {choices.map((choice) => {
                const slot = slots[choice.art - 1]
                if (!slot) return null
                return (
                  <li
                    key={choice.art}
                    className="grid grid-cols-1 gap-4 py-5 sm:grid-cols-[5rem_1fr_1fr]"
                    onFocusCapture={() => {
                      setFocus(choice.art)
                    }}
                  >
                    <div>
                      <p className="text-sm font-semibold text-gray-900 dark:text-white">ART {choice.art}</p>
                      {isChanged(choice) && (
                        <span className="mt-1 inline-flex items-center rounded-md bg-indigo-50 px-2 py-1 text-xs font-medium text-indigo-700 inset-ring inset-ring-indigo-700/10 dark:bg-indigo-400/10 dark:text-indigo-400 dark:inset-ring-indigo-400/30">
                          Changed
                        </span>
                      )}
                    </div>
                    <FilmSelect
                      art={choice.art}
                      value={choice.filmId}
                      builtIn={slot.builtIn}
                      onChange={(film) => {
                        update(choice.art, (c) => withFilm(c, film))
                      }}
                    />
                    <NameField
                      art={choice.art}
                      value={choice.name}
                      onChange={(name) => {
                        update(choice.art, (c) => ({ ...c, name }))
                      }}
                    />
                  </li>
                )
              })}
            </ul>
          </section>

          <aside className="order-first space-y-6 lg:sticky lg:top-8 lg:order-none lg:self-start">
            {focused && <StripPreview choice={focused} />}

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                disabled={changed === 0 || !valid}
                onClick={() => {
                  download(lookFile(choices))
                }}
                className="inline-flex items-center gap-x-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-xs hover:bg-indigo-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-indigo-500 dark:shadow-none dark:hover:bg-indigo-400"
              >
                <ArrowDownTrayIcon aria-hidden="true" className="-ml-0.5 size-5" />
                Download {CARD_NAME}
              </button>
              <button
                type="button"
                disabled={changed === 0}
                onClick={() => {
                  setChoices(builtInChoices())
                }}
                className="inline-flex items-center gap-x-1.5 rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-xs inset-ring inset-ring-gray-300 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white/10 dark:text-white dark:shadow-none dark:inset-ring-white/5 dark:hover:bg-white/20"
              >
                <ArrowUturnLeftIcon aria-hidden="true" className="-ml-0.5 size-5" />
                Built-in looks
              </button>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {changed === 0
                ? 'Every art filter holds its built-in film. Choose a film to change one.'
                : `${String(changed)} of 12 art filters change. The others keep their built-in film.`}
            </p>

            <div className="rounded-md bg-blue-50 p-4 dark:bg-blue-500/10 dark:outline dark:outline-blue-500/20">
              <div className="flex">
                <div className="shrink-0">
                  <InformationCircleIcon aria-hidden="true" className="size-5 text-blue-400" />
                </div>
                <div className="ml-3 text-sm text-blue-700 dark:text-blue-300">
                  <h3 className="font-medium text-blue-800 dark:text-blue-200">On the camera</h3>
                  <ol className="mt-2 list-decimal space-y-1 pl-5">
                    <li>Copy {CARD_NAME} to the top folder of the SD card.</li>
                    <li>MENU → Custom Menu → J → Load Looks → Load → OK.</li>
                    <li>The row reads Loaded. Built-in in the same row brings the built-in films back.</li>
                  </ol>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </main>

      <footer className="mx-auto max-w-7xl px-4 pb-8 text-xs text-gray-500 sm:px-6 lg:px-8">
        For the E-PM2 with the EPM2Mod firmware (build card-looks-4 or later). Film look data derived from{' '}
        <a className="underline" href="https://github.com/andreavolpato/spektrafilm">
          spektrafilm
        </a>{' '}
        by Andrea Volpato, CC BY-SA 4.0, fitted to the camera.
      </footer>
    </div>
  )
}
