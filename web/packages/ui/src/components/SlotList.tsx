import {
  closestCenter,
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type Announcements,
  type DragEndEvent,
  type UniqueIdentifier,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Bars3Icon, XMarkIcon } from '@heroicons/react/20/solid'
import { filmById, slots } from '../lib/films'
import type { SlotItem } from '../lib/selection'

interface RowProps {
  item: SlotItem
  index: number
  selected: boolean
  onSelect: () => void
  onRemove: () => void
}

function SlotRow({ item, index, selected, onSelect, onRemove }: RowProps) {
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, transform, transition, isDragging } = useSortable({
    id: item.key,
  })
  const art = index + 1
  const film = item.filmId ? filmById(item.filmId) : null
  // The selected row is filled like the active tab of the OM SYSTEM gallery; its secondary texts turn light.
  const sub = selected ? 'text-rule' : 'text-muted'
  const icon = `p-1 focus-visible:outline-2 ${selected ? 'text-rule hover:text-white focus-visible:outline-white' : 'text-muted hover:text-ink focus-visible:outline-ink'}`
  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      onFocusCapture={onSelect}
      onPointerDown={onSelect}
      className={`flex items-center gap-x-3 py-3 pr-2 pl-1 ${selected ? 'bg-ink-soft text-white' : 'bg-white'} ${isDragging ? 'outline-ink relative z-10 outline' : ''}`}
    >
      <button
        type="button"
        ref={setActivatorNodeRef}
        {...attributes}
        {...listeners}
        aria-label={`Move ART ${String(art)}${film ? `, ${film.film}` : ', empty'}`}
        className={`cursor-grab touch-none ${icon}`}
      >
        <Bars3Icon aria-hidden="true" className="size-5" />
      </button>
      <span className="w-14 shrink-0 text-sm font-bold">ART {art}</span>
      {film ? (
        <>
          <span className="min-w-0 flex-auto">
            <span className="block truncate">{film.film}</span>
            <span className={`block truncate text-xs ${sub}`}>{film.kind}</span>
          </span>
          <button
            type="button"
            onClick={onRemove}
            aria-label={`Remove ${film.film} from ART ${String(art)}`}
            title="Remove"
            className={icon}
          >
            <XMarkIcon aria-hidden="true" className="size-5" />
          </button>
        </>
      ) : (
        <span className="min-w-0 flex-auto">
          <span className={`block truncate ${sub}`}>Empty</span>
          <span className={`block truncate text-xs ${sub}`}>{slots[index]?.entry}</span>
        </span>
      )}
    </li>
  )
}

interface Props {
  items: readonly SlotItem[]
  selected: number
  onMove: (from: number, to: number) => void
  onRemove: (index: number) => void
  onSelect: (index: number) => void
}

/** The camera's ART menu, ART 1 to 12: drag (or the keyboard) to reorder, remove a film. */
export function SlotList({ items, selected, onMove, onRemove, onSelect }: Props) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )
  const place = (id: UniqueIdentifier | undefined) => {
    const index = items.findIndex((item) => item.key === id)
    const filmId = items[index]?.filmId
    return { art: `ART ${String(index + 1)}`, name: filmId ? filmById(filmId).film : 'The empty place' }
  }
  const announcements: Announcements = {
    onDragStart: ({ active }) => `Picked up ${place(active.id).name} from ${place(active.id).art}.`,
    onDragOver: ({ active, over }) =>
      over ? `${place(active.id).name} is over ${place(over.id).art}.` : `${place(active.id).name} is over no place.`,
    onDragEnd: ({ active, over }) =>
      over ? `${place(active.id).name} dropped at ${place(over.id).art}.` : `${place(active.id).name} not moved.`,
    onDragCancel: ({ active }) => `Move cancelled. ${place(active.id).name} stays at ${place(active.id).art}.`,
  }
  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return
    const from = items.findIndex((item) => item.key === active.id)
    const to = items.findIndex((item) => item.key === over.id)
    if (from >= 0 && to >= 0) onMove(from, to)
  }
  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      accessibility={{ announcements }}
      onDragEnd={onDragEnd}
    >
      <SortableContext items={items.map((item) => item.key)} strategy={verticalListSortingStrategy}>
        <ul className="divide-rule border-rule divide-y border-y">
          {items.map((item, index) => (
            <SlotRow
              key={item.key}
              item={item}
              index={index}
              selected={index === selected}
              onSelect={() => {
                onSelect(index)
              }}
              onRemove={() => {
                onRemove(index)
              }}
            />
          ))}
        </ul>
      </SortableContext>
    </DndContext>
  )
}
