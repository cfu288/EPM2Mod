import { addFilm, moveSlot, removeFilm, type SlotItem } from './selection'

const FOUR = ['portra-400', 'ektachrome', 'pro-400h', 'kodachrome']
const rows = (): SlotItem[] => FOUR.map((filmId) => ({ key: filmId, filmId }))

describe('the slots', () => {
  it('move a film to another place; the ones between shift by one', () => {
    const slots = moveSlot(rows(), 0, 2)
    expect(slots.map((s) => s.filmId).slice(0, 4)).toEqual(['ektachrome', 'pro-400h', 'portra-400', 'kodachrome'])
  })

  it('empty a slot and put another film in, each film once', () => {
    let slots = removeFilm(rows(), 3)
    expect(slots[3]?.filmId).toBeNull()
    slots = addFilm(slots, 3, 'c200')
    expect(slots[3]?.filmId).toBe('c200')
    expect(addFilm(slots, 3, 'portra-400')).toEqual(slots)
  })
})
