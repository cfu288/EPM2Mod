import type { Looks } from '../lib/useLooks'
import { SLOT_COUNT } from '../lib/selection'
import { FilmLibrary } from './FilmLibrary'
import { SlotList } from './SlotList'

/** The two sections that choose the films of the ART menu: the twelve rows in order, and the films to add. */
export function MenuEditor({ looks, liked }: { looks: Looks; liked?: readonly string[] }) {
  const filled = looks.items.filter((item) => item.filmId !== null).length
  return (
    <div className="space-y-14">
      <section aria-labelledby="menu-heading">
        <div className="section-title flex flex-wrap items-baseline justify-between gap-x-4">
          <h2 id="menu-heading">Your camera&apos;s ART menu</h2>
          <span className="text-muted font-sans text-sm font-normal tracking-normal">
            {filled} of {SLOT_COUNT} film simulations
          </span>
        </div>
        <p className="text-ink-soft mt-2 text-sm">Drag ☰ to reorder. Select a row to see its name on the camera.</p>
        <div className="mt-4">
          <SlotList
            items={looks.items}
            selected={looks.selected}
            onMove={looks.move}
            onRemove={looks.remove}
            onSelect={looks.select}
            liked={liked}
          />
        </div>
      </section>

      <section aria-labelledby="more-heading">
        <h2 id="more-heading" className="section-title">
          More film simulations
        </h2>
        {looks.empty < 0 ? (
          <p className="mt-2 text-sm font-bold">The menu is full. Remove a film simulation (×) to add one.</p>
        ) : (
          <p className="text-ink-soft mt-2 text-sm">Add puts a film simulation into ART {looks.empty + 1}.</p>
        )}
        <div className="mt-4">
          <FilmLibrary films={looks.unused} canAdd={looks.empty >= 0} onAdd={looks.add} liked={liked} />
        </div>
      </section>
    </div>
  )
}
