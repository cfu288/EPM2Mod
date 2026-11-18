import { films } from '@epm2mod/ui'
import { FilmCarousel } from '../FilmCarousel'

export function Films() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8 lg:py-16">
      <h1 className="font-display text-4xl font-extrabold tracking-tight sm:text-5xl">Film Simulations</h1>

      <div className="mt-10">
        <FilmCarousel />
      </div>

      <section aria-labelledby="all-films" className="mt-20">
        <h2 id="all-films" className="section-title">
          Available film simulations
        </h2>
        <p className="text-ink-soft mt-4">
          Install any of them in place of the 12 art filters Olympus provides by default.
        </p>
        <table className="mt-6 w-full text-left text-sm">
          <thead className="text-muted border-ink border-b">
            <tr>
              <th className="py-2 pr-4 font-normal">Menu name</th>
              <th className="py-2 pr-4 font-normal">Film</th>
              <th className="py-2 font-normal">Type</th>
            </tr>
          </thead>
          <tbody>
            {films.map((film) => (
              <tr key={film.id} className="border-rule border-b">
                <td className="py-2 pr-4 font-bold">{film.name}</td>
                <td className="py-2 pr-4">{film.film}</td>
                <td className="text-muted py-2">{film.kind}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}
