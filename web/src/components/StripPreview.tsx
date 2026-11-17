import { filmById, slots } from '../lib/films'

interface Props {
  art: number
  filmId: string | null
}

/**
 * The camera's Picture Mode strip for one ART place, as the emulator draws it with the film loaded
 * (web/scripts/render_previews.py). An empty place shows the film the camera has there now.
 */
export function StripPreview({ art, filmId }: Props) {
  const shown = filmById(filmId ?? slots[art - 1]?.builtIn ?? '')
  const src = `${import.meta.env.BASE_URL}previews/${shown.id}/art${String(art)}.png`
  return (
    <figure>
      <div className="overflow-hidden rounded-md bg-black">
        <img
          src={src}
          alt={`ART ${String(art)} on the camera screen, named ${shown.name}`}
          width={720}
          height={124}
          className="block w-full [image-rendering:pixelated]"
        />
      </div>
      <figcaption className="mt-2 text-sm text-gray-500 dark:text-gray-400">
        ART {art} on the camera screen. This shows the menu name, not the colours.
      </figcaption>
    </figure>
  )
}
