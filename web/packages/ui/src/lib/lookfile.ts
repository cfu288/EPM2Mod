/**
 * The look file EPM2LOOK.BIN, version 1 (docs/reference/look-file-format.md in the repository).
 *
 * A 32-byte header, then one 1,708-byte record per look. The records come ready-made from the repository's tools
 * (data/films/film-records.json); this module sets each record's slot and name and writes the header with its CRC-32.
 */

export const CARD_NAME = 'EPM2LOOK.BIN'
const MAGIC = [0x45, 0x50, 0x4c, 0x4b] // "EPLK"
const VERSION = 1
const HEADER_BYTES = 32
export const RECORD_BYTES = 1708
const MODEL = 0x0101 // E-PM2
const FIRMWARE = 0x0160 // 1.6
export const NAME_BYTES = 16
const NAME_OFFSET = 4

/** One look of the file: a film's record, the ART slot (1 to 12) and the name the camera shows. */
export interface LookChoice {
  record: Uint8Array
  art: number
  name: string
}

const CRC_TABLE = (() => {
  const table = new Uint32Array(256)
  for (let n = 0; n < 256; n++) {
    let c = n
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1
    table[n] = c >>> 0
  }
  return table
})()

/** CRC-32 as zlib computes it. */
export function crc32(bytes: Uint8Array): number {
  let crc = 0xffffffff
  for (const byte of bytes) crc = (CRC_TABLE[(crc ^ byte) & 0xff] ?? 0) ^ (crc >>> 8)
  return (crc ^ 0xffffffff) >>> 0
}

/** Why a name cannot be used, or null when it can: 1 to 16 printable ASCII characters. */
export function nameProblem(name: string): string | null {
  if (name.length === 0) return 'Give the look a name.'
  if (name.length > NAME_BYTES) return `At most ${String(NAME_BYTES)} characters.`
  if (!/^[\x20-\x7e]+$/.test(name)) return 'Letters, digits and plain symbols only.'
  return null
}

export function decodeBase64(text: string): Uint8Array {
  return Uint8Array.from(atob(text), (c) => c.charCodeAt(0))
}

/** The bytes of a look file holding the given looks, in the given order. */
export function packLooks(looks: readonly LookChoice[]): Uint8Array {
  if (looks.length > 12) throw new Error('at most 12 looks')
  const arts = new Set(looks.map((look) => look.art))
  if (arts.size !== looks.length) throw new Error('two looks for one ART slot')
  const length = HEADER_BYTES + looks.length * RECORD_BYTES
  const file = new Uint8Array(length)
  const view = new DataView(file.buffer)
  looks.forEach((look, index) => {
    if (look.record.length !== RECORD_BYTES) throw new Error('a look record is 1,708 bytes')
    if (look.art < 1 || look.art > 12) throw new Error('ART 1 to 12')
    const problem = nameProblem(look.name)
    if (problem) throw new Error(problem)
    const at = HEADER_BYTES + index * RECORD_BYTES
    file.set(look.record, at)
    file[at] = look.art - 1
    file.fill(0, at + NAME_OFFSET, at + NAME_OFFSET + NAME_BYTES)
    for (let i = 0; i < look.name.length; i++) file[at + NAME_OFFSET + i] = look.name.charCodeAt(i)
  })
  file.set(MAGIC, 0)
  view.setUint8(4, VERSION)
  view.setUint8(5, looks.length)
  view.setUint16(6, RECORD_BYTES, true)
  view.setUint32(8, length, true)
  view.setUint16(16, MODEL, true)
  view.setUint16(18, FIRMWARE, true)
  view.setUint32(12, crc32(file.subarray(16)), true)
  return file
}
