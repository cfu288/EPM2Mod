import { features } from '../features'
import { asset } from '../router'

export function Features() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8 lg:py-16">
      <h1 className="font-display text-4xl font-extrabold tracking-tight sm:text-5xl">Features</h1>

      {features.map((feature) => (
        <section
          key={feature.id}
          id={feature.id}
          aria-labelledby={`${feature.id}-heading`}
          className="mt-16 scroll-mt-28 sm:scroll-mt-20"
        >
          <h2 id={`${feature.id}-heading`} className="section-title">
            {feature.name}
          </h2>
          <div className="mt-6 grid gap-8 lg:grid-cols-2">
            <div>
              <p className="text-lg">{feature.summary}</p>
              <ol className="mt-6 space-y-3">
                {feature.steps.map((step, n) => (
                  <li key={step} className="flex gap-x-4">
                    <span className="bg-ink flex size-6 shrink-0 items-center justify-center text-xs font-bold text-white">
                      {n + 1}
                    </span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            </div>
            <div className="grid grid-cols-2 gap-4 self-start">
              {feature.screens.map((screen) => (
                <img
                  key={screen.src}
                  src={asset(screen.src)}
                  alt={screen.alt}
                  width={720}
                  height={480}
                  loading="lazy"
                  className={`border-ink w-full border-4 ${feature.screens.length === 1 ? 'col-span-2 max-w-md' : ''}`}
                />
              ))}
            </div>
          </div>
        </section>
      ))}
    </div>
  )
}
