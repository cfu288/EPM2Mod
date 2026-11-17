// The emulator's pictures of the Picture Mode strip (web/scripts/render_previews.py).

/** The preview pictures, bundled as assets so that each app serves them under its own base path. */
const pictures = import.meta.glob<string>('../previews/*/*.png', { eager: true, query: '?url', import: 'default' })

/** The address of a preview picture: `menu/art3` or `name/velvia`. */
export function previewUrl(name: string): string {
  const url = pictures[`../previews/${name}.png`]
  if (!url) throw new Error(`no preview picture '${name}'`)
  return url
}
