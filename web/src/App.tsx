import { useState } from 'react'
import { ArrowDownTrayIcon, ExclamationTriangleIcon } from '@heroicons/react/20/solid'
import { FilmLibrary } from './components/FilmLibrary'
import { SlotList } from './components/SlotList'
import { StripPreview } from './components/StripPreview'
import { films } from './lib/films'
import { CARD_NAME } from './lib/lookfile'
import { addFilm, builtInSlots, firstEmpty, lookFile, moveSlot, removeFilm, type SlotItem } from './lib/selection'

const INSTALL = 'https://github.com/cfu288/EPM2Mod#install'

function download(bytes: Uint8Array) {
  const url = URL.createObjectURL(new Blob([bytes as BlobPart], { type: 'application/octet-stream' }))
  const link = document.createElement('a')
  link.href = url
  link.download = CARD_NAME
  link.click()
  URL.revokeObjectURL(url)
}

export default function App() {
  const [items, setItems] = useState<SlotItem[]>(builtInSlots)
  const [selected, setSelected] = useState(0)
  const empty = firstEmpty(items)
  const unused = films.filter((film) => !items.some((item) => item.filmId === film.id))

  return (
    <div className="min-h-full">
      <header className="border-b border-gray-200 bg-white dark:border-white/10 dark:bg-gray-900">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
            Film looks for the Olympus PEN E-PM2
          </h1>
          <p className="mt-2 max-w-3xl text-gray-700 dark:text-gray-300">
            Choose which film looks appear in the camera's ART menu (the art filters, ART 1 to 12) and in which order.
            Then download one file and load it on the camera.
          </p>
          <div className="mt-4 max-w-3xl rounded-md bg-yellow-50 p-4 dark:bg-yellow-500/10 dark:outline dark:outline-yellow-500/15">
            <div className="flex">
              <ExclamationTriangleIcon
                aria-hidden="true"
                className="size-5 shrink-0 text-yellow-400 dark:text-yellow-300"
              />
              <p className="ml-3 text-sm text-yellow-800 dark:text-yellow-200">
                The camera must run the EPM2Mod firmware first.{' '}
                <a className="font-medium underline hover:text-yellow-700 dark:hover:text-yellow-100" href={INSTALL}>
                  How to install EPM2Mod
                </a>
              </p>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          <div className="space-y-10 lg:col-span-2">
            <section aria-labelledby="menu-heading">
              <h2 id="menu-heading" className="text-lg font-semibold text-gray-900 dark:text-white">
                Your camera's ART menu
              </h2>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                Drag a row by its handle (☰) to change the order. Select a row to preview it on the camera screen.
              </p>
              <div className="mt-3">
                <SlotList
                  items={items}
                  selected={selected}
                  onMove={(from, to) => {
                    setItems((all) => moveSlot(all, from, to))
                    setSelected(to)
                  }}
                  onRemove={(index) => {
                    setItems((all) => removeFilm(all, index))
                    setSelected(index)
                  }}
                  onSelect={setSelected}
                />
              </div>
            </section>

            <section aria-labelledby="more-heading">
              <h2 id="more-heading" className="text-lg font-semibold text-gray-900 dark:text-white">
                More films
              </h2>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                {empty >= 0
                  ? `Add puts a film into ART ${String(empty + 1)}, the first empty row.`
                  : 'The menu holds 12 films. Remove one (×) to add another.'}
              </p>
              <div className="mt-3">
                <FilmLibrary
                  films={unused}
                  canAdd={empty >= 0}
                  onAdd={(film) => {
                    setItems((all) => addFilm(all, empty, film.id))
                    setSelected(empty)
                  }}
                />
              </div>
            </section>
          </div>

          {/* On a phone the preview comes first and the download after the lists. */}
          <aside className="contents lg:sticky lg:top-8 lg:block lg:space-y-6 lg:self-start">
            <div className="order-first lg:order-none">
              <StripPreview art={selected + 1} filmId={items[selected]?.filmId ?? null} />
            </div>
            <div className="space-y-6">
              <button
                type="button"
                onClick={() => {
                  download(lookFile(items))
                }}
                className="inline-flex items-center gap-x-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-xs hover:bg-indigo-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 dark:bg-indigo-500 dark:shadow-none dark:hover:bg-indigo-400"
              >
                <ArrowDownTrayIcon aria-hidden="true" className="-ml-0.5 size-5" />
                Download {CARD_NAME}
              </button>
              <section aria-labelledby="load-heading">
                <h2 id="load-heading" className="text-base font-semibold text-gray-900 dark:text-white">
                  Load it on the camera
                </h2>
                <ol className="mt-2 list-decimal space-y-2 pl-5 text-sm text-gray-700 dark:text-gray-300">
                  <li>Copy {CARD_NAME} to the top folder of the SD card.</li>
                  <li>
                    On the camera: MENU → Custom Menu (gears tab) → group J → Load Looks → Load → OK. No gears tab? Turn
                    it on in Setup Menu → Menu Display.
                  </li>
                  <li>
                    Load Looks reads Loaded, and the ART menu shows your films. The camera keeps them after power-off.
                  </li>
                </ol>
                <p className="mt-3 text-sm text-gray-600 dark:text-gray-400">To undo: Load Looks → Built-in → OK.</p>
              </section>
            </div>
          </aside>
        </div>
      </main>

      <footer className="mx-auto max-w-7xl px-4 pb-8 text-xs text-gray-500 sm:px-6 lg:px-8">
        The film looks are fitted from{' '}
        <a className="underline" href="https://github.com/andreavolpato/spektrafilm">
          spektrafilm
        </a>{' '}
        by Andrea Volpato (CC BY-SA 4.0).
      </footer>
    </div>
  )
}
