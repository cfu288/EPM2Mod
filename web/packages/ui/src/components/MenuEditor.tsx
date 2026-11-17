import type { Looks } from '../lib/useLooks'
import { FilmLibrary } from './FilmLibrary'
import { SlotList } from './SlotList'

/** The two sections that choose the films of the ART menu: the twelve rows in order, and the films to add. */
export function MenuEditor({ looks }: { looks: Looks }) {
  return (
    <div className="space-y-14">
      <section aria-labelledby="menu-heading">
        <h2 id="menu-heading" className="section-title">
          Your camera's ART menu
        </h2>
        <p className="text-ink-soft mt-2 text-sm">
          Drag a row by its handle (☰) to change the order. Select a row to preview it on the camera screen.
        </p>
        <div className="mt-4">
          <SlotList
            items={looks.items}
            selected={looks.selected}
            onMove={looks.move}
            onRemove={looks.remove}
            onSelect={looks.select}
          />
        </div>
      </section>

      <section aria-labelledby="more-heading">
        <h2 id="more-heading" className="section-title">
          More films
        </h2>
        <p className="text-ink-soft mt-2 text-sm">
          {looks.empty >= 0
            ? `Select Add to put a film into ART ${String(looks.empty + 1)}, the first empty row.`
            : 'The menu holds 12 films. Remove one (×) to add another.'}
        </p>
        <div className="mt-4">
          <FilmLibrary films={looks.unused} canAdd={looks.empty >= 0} onAdd={looks.add} />
        </div>
      </section>
    </div>
  )
}
