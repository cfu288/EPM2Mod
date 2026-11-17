import { useState } from 'react'
import { ArrowDownTrayIcon } from '@heroicons/react/20/solid'
import { Chevron } from './components/Chevron'
import { FilmLibrary } from './components/FilmLibrary'
import { SlotList } from './components/SlotList'
import { StripPreview } from './components/StripPreview'
import { films } from './lib/films'
import { CARD_NAME } from './lib/lookfile'
import { addFilm, builtInSlots, firstEmpty, lookFile, moveSlot, removeFilm, type SlotItem } from './lib/selection'

const REPO = 'https://github.com/cfu288/EPM2Mod'
const INSTALL = `${REPO}#install`

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
      <header className="border-rule border-b bg-white">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-x-4 px-4 sm:px-6 lg:px-8">
          <a href={REPO} className="font-display text-xl font-extrabold tracking-tight">
            EPM2Mod
          </a>
          <span className="text-muted text-sm font-light tracking-wider">Film looks</span>
        </div>
      </header>

      <div className="bg-ink text-white">
        <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8 lg:py-16">
          <h1 className="font-display max-w-4xl text-4xl font-extrabold tracking-tight sm:text-5xl">
            Film looks for the Olympus <span className="whitespace-nowrap">PEN E-PM2</span>
          </h1>
          <p className="text-rule mt-6 max-w-3xl text-lg">
            EPM2Mod is an unofficial firmware for the Olympus PEN E-PM2. It puts film looks, such as Kodak Portra and
            Fujifilm Velvia, into the camera's ART menu (the art filters, ART 1 to 12).
          </p>
          <p className="text-rule mt-3 max-w-3xl text-lg">
            Here you choose which films are in that menu and in which order. Then you download one file and load it on
            the camera.
          </p>
          <p className="text-rule mt-8 text-sm">The camera must run the EPM2Mod firmware first.</p>
          <a
            href={INSTALL}
            className="hover:text-ink mt-3 inline-flex items-center gap-x-3 border border-white bg-black/20 px-4 py-2 text-white transition-colors hover:bg-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          >
            How to install EPM2Mod
            <Chevron />
          </a>
        </div>
      </div>

      <main className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-3">
          <div className="space-y-14 lg:col-span-2">
            <section aria-labelledby="menu-heading">
              <h2 id="menu-heading" className="section-title">
                Your camera's ART menu
              </h2>
              <p className="text-ink-soft mt-2 text-sm">
                Drag a row by its handle (☰) to change the order. Select a row to preview it on the camera screen.
              </p>
              <div className="mt-4">
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
              <h2 id="more-heading" className="section-title">
                More films
              </h2>
              <p className="text-ink-soft mt-2 text-sm">
                {empty >= 0
                  ? `Add puts a film into ART ${String(empty + 1)}, the first empty row.`
                  : 'The menu holds 12 films. Remove one (×) to add another.'}
              </p>
              <div className="mt-4">
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
          <aside className="contents lg:sticky lg:top-8 lg:block lg:space-y-8 lg:self-start">
            <div className="order-first lg:order-none">
              <StripPreview art={selected + 1} filmId={items[selected]?.filmId ?? null} />
            </div>
            <div className="space-y-8">
              <button
                type="button"
                onClick={() => {
                  download(lookFile(items))
                }}
                className="btn bg-ink hover:text-ink w-full justify-between py-3 text-base text-white hover:bg-white"
              >
                Download {CARD_NAME}
                <ArrowDownTrayIcon aria-hidden="true" className="size-5" />
              </button>
              <section aria-labelledby="load-heading">
                <h2 id="load-heading" className="section-title border-t-[6px] pt-4 text-lg">
                  Load it on the camera
                </h2>
                <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm">
                  <li>Copy {CARD_NAME} to the top folder of the SD card.</li>
                  <li>
                    On the camera: MENU → Custom Menu (gears tab) → group J → Load Looks → Load → OK. No gears tab? Turn
                    it on in Setup Menu → Menu Display.
                  </li>
                  <li>
                    Load Looks reads Loaded, and the ART menu shows your films. The camera keeps them after power-off.
                  </li>
                </ol>
                <p className="text-ink-soft mt-3 text-sm">To undo: Load Looks → Built-in → OK.</p>
              </section>
            </div>
          </aside>
        </div>
      </main>

      <footer className="border-rule border-t">
        <p className="text-muted mx-auto max-w-7xl px-4 py-6 text-xs sm:px-6 lg:px-8">
          The film looks are fitted from{' '}
          <a className="hover:text-ink underline" href="https://github.com/andreavolpato/spektrafilm">
            spektrafilm
          </a>{' '}
          by Andrea Volpato (CC BY-SA 4.0).
        </p>
      </footer>
    </div>
  )
}
