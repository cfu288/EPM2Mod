import { ArrowDownTrayIcon } from '@heroicons/react/20/solid'
import {
  CARD_NAME,
  Chevron,
  LoadSteps,
  lookFile,
  MenuEditor,
  PageFrame,
  REPO,
  StripPreview,
  useLooks,
} from '@epm2mod/ui'

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
  const looks = useLooks()

  return (
    <PageFrame subtitle="Film looks">
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
          <div className="lg:col-span-2">
            <MenuEditor looks={looks} />
          </div>

          {/* On a phone the preview comes first and the download after the lists. */}
          <aside className="contents lg:sticky lg:top-8 lg:block lg:space-y-8 lg:self-start">
            <div className="order-first lg:order-none">
              <StripPreview art={looks.selected + 1} filmId={looks.items[looks.selected]?.filmId ?? null} />
            </div>
            <div className="space-y-8">
              <button
                type="button"
                onClick={() => {
                  download(lookFile(looks.items))
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
                <LoadSteps />
              </section>
            </div>
          </aside>
        </div>
      </main>
    </PageFrame>
  )
}
