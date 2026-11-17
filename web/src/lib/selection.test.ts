import { addFilm, builtInSlots, moveSlot, removeFilm, SLOT_COUNT } from './selection'

describe('the slots', () => {
  it('start with the twelve built-in films', () => {
    const slots = builtInSlots()
    expect(slots).toHaveLength(SLOT_COUNT)
    expect(slots[2]?.filmId).toBe('pro-400h')
  })

  it('move a film to another place; the ones between shift by one', () => {
    const slots = moveSlot(builtInSlots(), 0, 2)
    expect(slots.map((s) => s.filmId).slice(0, 4)).toEqual(['ektachrome', 'pro-400h', 'portra-400', 'kodachrome'])
  })

  it('empty a slot and put another film in, each film once', () => {
    let slots = removeFilm(builtInSlots(), 4)
    expect(slots[4]?.filmId).toBeNull()
    slots = addFilm(slots, 4, 'c200')
    expect(slots[4]?.filmId).toBe('c200')
    expect(addFilm(slots, 4, 'velvia')).toEqual(slots)
  })
})
