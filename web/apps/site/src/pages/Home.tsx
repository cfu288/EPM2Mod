import { Chevron } from '@epm2mod/ui'
import { Drawing } from '../Drawing'
import { features } from '../features'
import { Link } from '../Link'
import { asset, href } from '../router'

export function Home() {
  return (
    <>
      <section className="mx-auto grid max-w-7xl items-center gap-12 px-4 pt-12 pb-16 sm:px-6 lg:grid-cols-2 lg:px-8 lg:pt-20">
        <div>
          <h1 className="font-display text-5xl font-extrabold tracking-tight sm:text-6xl">EPM2Mod</h1>
          <p className="text-ink-soft mt-6 max-w-md text-lg">
            Custom firmware for the E-PM2 that adds film simulations, interval shooting, a level gauge, and focus
            peaking.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href={href('install')} className="btn bg-ink hover:text-ink py-3 text-white hover:bg-white">
              Install
              <Chevron />
            </Link>
          </div>
        </div>
        <Drawing className="w-full max-w-xl justify-self-center" />
      </section>

      <section aria-labelledby="features-heading" className="mx-auto max-w-7xl px-4 pb-20 sm:px-6 lg:px-8">
        <h2 id="features-heading" className="section-title">
          Features
        </h2>
        <ol className="mt-8 grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-4">
          {features
            .filter((feature) => feature.id !== 'card-looks')
            .map((feature) => (
              <li key={feature.id} className="border-rule border-t pt-4">
                <h3 className="font-bold">
                  <Link href={href('features', `#${feature.id}`)} className="hover:underline">
                    {feature.name}
                  </Link>
                </h3>
                <p className="text-ink-soft mt-2 text-sm">{feature.summary}</p>
              </li>
            ))}
        </ol>
      </section>

      <Link href={href('films')} className="group relative block bg-black">
        <img
          src={asset('films/scene-3/portra-400.webp')}
          alt="Stairs down to a beach, in Portra 400"
          className="h-[60vh] min-h-80 w-full object-cover opacity-95 transition-opacity group-hover:opacity-80"
        />
        <span className="absolute bottom-0 left-0 p-4 text-white sm:p-8">
          <span className="block text-sm tracking-widest uppercase">Portra 400</span>
          <span className="font-display mt-1 inline-flex items-center gap-x-2 text-2xl font-extrabold sm:text-3xl">
            Compare 12 film simulations
            <Chevron />
          </span>
        </span>
      </Link>
    </>
  )
}
