import { filmById, slots } from './films'
import { crc32, decodeBase64, nameProblem, packLooks, RECORD_BYTES } from './lookfile'
import { builtInChoices, fromSearch, isChanged, lookFile, toSearch, withFilm } from './selection'

async function sha256(bytes: Uint8Array): Promise<string> {
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes as BufferSource))
  return Array.from(digest, (b) => b.toString(16).padStart(2, '0')).join('')
}

describe('the look file', () => {
  it('packs the twelve built-in looks to the bytes of the repository tool (docs/look-file-format.md)', async () => {
    const all = builtInChoices().map((c) => ({
      record: decodeBase64(filmById(c.filmId).record),
      art: c.art,
      name: c.name,
    }))
    expect(await sha256(packLooks(all))).toBe('5d5df335dc14100a3fb7c90265ca07470419f12f52f806cc6b80f1bc09cae7ad')
  })

  it('packs a mix as `epm2mod looks pack ART2=velvia ART6=double-x "ART12=vision3-500t:Cinestill 800T"` does', async () => {
    let choices = builtInChoices()
    choices = choices.map((c) => (c.art === 2 ? withFilm(c, filmById('velvia')) : c))
    choices = choices.map((c) => (c.art === 6 ? withFilm(c, filmById('double-x')) : c))
    choices = choices.map((c) =>
      c.art === 12 ? { ...withFilm(c, filmById('vision3-500t')), name: 'Cinestill 800T' } : c,
    )
    expect(await sha256(lookFile(choices))).toBe('823dba8d60cb3d9c93c0c292cb4bab584d522a6fe0b1a60f798c7f12c50e1bad')
  })

  it('writes the header fields and a CRC-32 of bytes 16 to the end', () => {
    const film = filmById('c200')
    const file = packLooks([{ record: decodeBase64(film.record), art: 3, name: 'Test' }])
    const view = new DataView(file.buffer)
    expect(file.length).toBe(32 + RECORD_BYTES)
    expect(String.fromCharCode(...file.subarray(0, 4))).toBe('EPLK')
    expect(view.getUint32(12, true)).toBe(crc32(file.subarray(16)))
    expect(file[32]).toBe(2)
    expect(String.fromCharCode(...file.subarray(36, 40))).toBe('Test')
    expect(file[40]).toBe(0)
  })

  it('refuses names the camera cannot show and two looks for one slot', () => {
    expect(nameProblem('')).not.toBeNull()
    expect(nameProblem('x'.repeat(17))).not.toBeNull()
    expect(nameProblem('Portra é')).not.toBeNull()
    expect(nameProblem('Kodak Portra 160')).toBeNull()
    const record = decodeBase64(filmById('c200').record)
    expect(() =>
      packLooks([
        { record, art: 1, name: 'a' },
        { record, art: 1, name: 'b' },
      ]),
    ).toThrow()
  })
})

describe('the choices', () => {
  it('starts with the built-in films, and a URL holds only the changes', () => {
    const choices = builtInChoices()
    expect(choices).toHaveLength(12)
    expect(choices.some(isChanged)).toBe(false)
    expect(toSearch(choices)).toBe('')
    const changed = choices.map((c) => (c.art === 5 ? { ...withFilm(c, filmById('ektar-100')), name: 'My Ektar' } : c))
    const search = toSearch(changed)
    expect(search).toBe('?art5=ektar-100&name5=My+Ektar')
    expect(fromSearch(search)).toEqual(changed)
    expect(fromSearch('?art3=nofilm&art99=c200')).toEqual(choices)
  })

  it('every slot names a known film', () => {
    for (const slot of slots) expect(() => filmById(slot.builtIn)).not.toThrow()
  })
})
