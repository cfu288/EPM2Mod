import { films, PRESET } from '@epm2mod/ui'
import { packSlots } from './likes'

const ids = (liked: string[]) => packSlots(liked).map((slot) => slot.filmId)

describe('packSlots', () => {
  it('is the defaults with no likes', () => {
    expect(ids([])).toEqual(PRESET)
  })

  it('puts the liked first, in site order, and pushes the last defaults out', () => {
    const extra = films.map((f) => f.id).filter((id) => !PRESET.includes(id))
    const liked = [extra[1] ?? '', extra[0] ?? '', PRESET[3] ?? '', 'no-such-film']
    expect(ids(liked)).toEqual([PRESET[3], extra[0], extra[1], ...PRESET.filter((id) => id !== PRESET[3]).slice(0, 9)])
  })

  it('takes the first 12 liked in site order when more are liked', () => {
    const all = films.map((f) => f.id)
    expect(ids([...all].reverse())).toEqual(all.slice(0, 12))
  })
})
