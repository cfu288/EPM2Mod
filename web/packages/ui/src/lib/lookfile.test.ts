import { filmById, slots } from './films'
import { crc32, decodeBase64, nameProblem, packLooks, RECORD_BYTES } from './lookfile'
import { builtInSlots, lookFile } from './selection'

async function sha256(bytes: Uint8Array): Promise<string> {
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes as BufferSource))
  return Array.from(digest, (b) => b.toString(16).padStart(2, '0')).join('')
}

describe('the look file', () => {
  it('packs the twelve built-in films to the bytes of the repository tool (docs/look-file-format.md)', async () => {
    expect(await sha256(lookFile(builtInSlots()))).toBe(
      '5d5df335dc14100a3fb7c90265ca07470419f12f52f806cc6b80f1bc09cae7ad',
    )
  })

  it('packs twelve slots as `epm2mod films set` does with the same choices', async () => {
    const mix: Record<number, string> = { 1: 'velvia', 5: 'double-x', 11: 'vision3-500t' }
    const items = builtInSlots().map((item, i) => ({ ...item, filmId: mix[i] ?? item.filmId }))
    expect(await sha256(lookFile(items))).toBe('13599e2d1ad67ee54bf591473199f5a1af18be55661c7a20fb4698855ed4ef1a')
  })

  it('writes the header fields and a CRC-32 of bytes 16 to the end', () => {
    const film = filmById('c200')
    const file = packLooks([{ record: decodeBase64(film.record), art: 3, name: film.name }])
    const view = new DataView(file.buffer)
    expect(file.length).toBe(32 + RECORD_BYTES)
    expect(String.fromCharCode(...file.subarray(0, 4))).toBe('EPLK')
    expect(view.getUint32(12, true)).toBe(crc32(file.subarray(16)))
    expect(file[32]).toBe(2)
    expect(String.fromCharCode(...file.subarray(36, 40))).toBe('C200')
    expect(file[40]).toBe(0)
  })

  it('refuses names the camera cannot show and two looks for one slot', () => {
    expect(nameProblem('')).not.toBeNull()
    expect(nameProblem('x'.repeat(17))).not.toBeNull()
    expect(nameProblem('Portra é')).not.toBeNull()
    const record = decodeBase64(filmById('c200').record)
    expect(() =>
      packLooks([
        { record, art: 1, name: 'a' },
        { record, art: 1, name: 'b' },
      ]),
    ).toThrow()
  })

  it('packs only the filled slots', () => {
    const items = builtInSlots().map((item, i) => (i === 0 ? { ...item, filmId: null } : item))
    const file = lookFile(items)
    expect(file[5]).toBe(11)
    expect(file[32]).toBe(1)
  })

  it('every slot names a known film', () => {
    for (const slot of slots) expect(() => filmById(slot.builtIn)).not.toThrow()
  })
})
