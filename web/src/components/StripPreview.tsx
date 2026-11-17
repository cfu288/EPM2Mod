import { filmById, slots } from '../lib/films'

interface Props {
  art: number
  filmId: string | null
}

/** The strip and the inside of its name box, in the emulator's pixels (web/scripts/render_previews.py). */
const STRIP = { width: 720, height: 124 }
const NAME = { left: 160, top: 12, width: 400, height: 32 }
const percent = (part: number, whole: number) => `${String((100 * part) / whole)}%`

/**
 * The camera's Picture Mode strip at one ART position with the film of that row, as the emulator draws it: the
 * strip of the position (previews/menu) with the film's name (previews/name) over its name box. An empty row shows
 * the film built in at that position.
 */
export function StripPreview({ art, filmId }: Props) {
  const shown = filmById(filmId ?? slots[art - 1]?.builtIn ?? '')
  const base = `${import.meta.env.BASE_URL}previews`
  return (
    <figure>
      <div
        role="img"
        aria-label={`The camera's ART menu with ART ${String(art)}, ${shown.name}, selected`}
        className="relative overflow-hidden rounded-md bg-black"
      >
        <img
          src={`${base}/menu/art${String(art)}.png`}
          alt=""
          width={STRIP.width}
          height={STRIP.height}
          className="block w-full [image-rendering:pixelated]"
        />
        <img
          src={`${base}/name/${shown.id}.png`}
          alt=""
          width={NAME.width}
          height={NAME.height}
          className="absolute [image-rendering:pixelated]"
          style={{
            left: percent(NAME.left, STRIP.width),
            top: percent(NAME.top, STRIP.height),
            width: percent(NAME.width, STRIP.width),
            height: percent(NAME.height, STRIP.height),
          }}
        />
      </div>
      <figcaption className="mt-2 text-sm text-gray-500 dark:text-gray-400">
        ART {art} as the camera will show it.
      </figcaption>
    </figure>
  )
}
