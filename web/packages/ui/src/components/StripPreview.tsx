import { filmById, slots } from '../lib/films'
import { previewUrl } from '../lib/previews'

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
  return (
    <figure>
      <div
        role="img"
        aria-label={`The camera's ART menu with ART ${String(art)}, ${shown.name}, selected`}
        className="relative overflow-hidden bg-black"
      >
        <img
          src={previewUrl(`menu/art${String(art)}`)}
          alt=""
          width={STRIP.width}
          height={STRIP.height}
          className="block w-full [image-rendering:pixelated]"
        />
        <img
          src={previewUrl(`name/${shown.id}`)}
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
      <figcaption className="text-muted mt-2 text-sm">ART {art} as the camera will show it.</figcaption>
    </figure>
  )
}
