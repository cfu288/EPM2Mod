import { filmById } from '../lib/films'
import type { SlotChoice } from '../lib/selection'

/**
 * The camera's Picture Mode strip for one ART slot, as the emulator draws it with the film loaded
 * (web/scripts/render_previews.py). A name that is not the film's own is drawn over the name box.
 */
export function StripPreview({ choice }: { choice: SlotChoice }) {
  const film = filmById(choice.filmId)
  const src = `${import.meta.env.BASE_URL}previews/${film.id}/art${String(choice.art)}.png`
  const custom = choice.name !== film.name
  return (
    <figure>
      <div className="@container relative overflow-hidden rounded-md bg-black">
        <img
          src={src}
          alt={`The camera's film strip at ART ${String(choice.art)}, showing ${choice.name}`}
          width={720}
          height={124}
          className="block w-full [image-rendering:pixelated]"
        />
        {custom && (
          <div className="absolute top-[5.65%] left-[21.53%] flex h-[30.65%] w-[56.94%] items-center justify-center bg-[#121212] text-[3.1cqw] tracking-wide text-white">
            {choice.name}
          </div>
        )}
      </div>
      <figcaption className="mt-2 text-sm text-gray-500 dark:text-gray-400">
        Picture Mode strip, ART {choice.art}, as the camera draws it
        {custom ? ' (your name is drawn approximately)' : ''}.
      </figcaption>
    </figure>
  )
}
