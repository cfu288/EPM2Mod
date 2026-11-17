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
        <p className="text-ink-soft mt-2 text-sm">Drag ☰ to reorder. Select a row to preview it.</p>
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
        {looks.empty < 0 && <p className="text-ink-soft mt-2 text-sm">Remove a film (×) to add one.</p>}
        <div className="mt-4">
          <FilmLibrary films={looks.unused} canAdd={looks.empty >= 0} onAdd={looks.add} />
        </div>
      </section>
    </div>
  )
}
