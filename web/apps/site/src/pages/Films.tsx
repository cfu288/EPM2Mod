import { lazy, Suspense, useState } from 'react'
import { FilmCarousel } from '../FilmCarousel'
import { useLikes } from '../likes'

// the editor and its drag and drop load on the first click
const LookPack = lazy(() => import('../LookPack').then((module) => ({ default: module.LookPack })))

export function Films() {
  const [liked, like] = useLikes()
  const [packOpen, setPackOpen] = useState(false)
  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8 lg:py-16">
      <h1 className="font-display text-4xl font-extrabold tracking-tight sm:text-5xl">Film Simulations</h1>

      <div className="mt-10">
        <FilmCarousel liked={liked} onLike={like} />
      </div>

      <section aria-labelledby="look-pack" className="mt-20">
        <h2 id="look-pack" className="section-title">
          Create a Look Pack
        </h2>
        {packOpen ? (
          <Suspense fallback={<p className="text-muted mt-6">Loading…</p>}>
            {/* a like or unlike rebuilds the pack */}
            <LookPack key={liked.join()} liked={liked} />
          </Suspense>
        ) : (
          <div className="mt-6 space-y-5">
            <p className="text-ink-soft max-w-2xl">
              Choose the film simulations for your camera&apos;s ART menu and download them as a look pack.
            </p>
            <button
              type="button"
              onClick={() => {
                setPackOpen(true)
              }}
              className="btn bg-ink hover:text-ink justify-center px-6 py-3 text-base text-white hover:bg-white"
            >
              Choose film simulations
            </button>
          </div>
        )}
      </section>
    </div>
  )
}
