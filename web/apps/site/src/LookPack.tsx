import { ArrowDownTrayIcon } from '@heroicons/react/20/solid'
import { CARD_NAME, lookFile, MenuEditor, save, StripPreview, useLooks } from '@epm2mod/ui'
import { Link } from './Link'
import { packSlots } from './likes'
import { href } from './router'

/** The ART-menu editor of the installer, started from the liked film simulations, with a download of the look pack. */
export function LookPack({ liked }: { liked: readonly string[] }) {
  const looks = useLooks(() => packSlots(liked))
  return (
    <div className="mt-6 grid gap-x-12 gap-y-10 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] lg:items-start">
      <div className="space-y-5 lg:sticky lg:top-20">
        <div className="max-w-md">
          <StripPreview art={looks.selected + 1} filmId={looks.items[looks.selected]?.filmId ?? null} />
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => {
              save(new Blob([lookFile(looks.items) as Uint8Array<ArrayBuffer>]), CARD_NAME) // packLooks makes a new ArrayBuffer
            }}
            className="btn bg-ink hover:text-ink justify-center px-4 py-3 text-base text-white hover:bg-white sm:px-6"
          >
            <ArrowDownTrayIcon aria-hidden="true" className="-ml-1 size-5" />
            Download {CARD_NAME}
          </button>
          <button
            type="button"
            onClick={() => {
              if (window.confirm('Discard your changes?')) looks.reset()
            }}
            className="btn justify-center px-4 py-3 text-base sm:px-6"
          >
            Reset
          </button>
        </div>
        <ol className="text-ink-soft list-decimal space-y-1 pl-5 text-sm">
          <li>Copy {CARD_NAME} to the top of the SD card.</li>
          <li>On the camera: MENU → SETUP → Custom Menu → J → Load Looks → Load.</li>
        </ol>
        <p className="text-muted text-sm">
          Load Looks needs EPM2Mod on the camera.{' '}
          <Link href={href('install')} className="hover:text-ink underline">
            Install it
          </Link>
          .
        </p>
      </div>
      <div className="min-w-0">
        <MenuEditor looks={looks} liked={liked} />
      </div>
    </div>
  )
}
