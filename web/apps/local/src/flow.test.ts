import type { Job } from './api'
import { canGo, initial, onTimeline, reduce, type Action, type State } from './flow'

const run = (...actions: Action[]) => actions.reduce(reduce, initial)
const CARD = { path: '/media/u/CARD', name: 'CARD', size: 32e9, free: 31e9, label: 'CARD' }
const job = (over: Partial<Job>): Job => ({
  job: 1,
  firmware: 'epm2mod',
  lines: [],
  step: 0,
  steps: 5,
  done: false,
  error: null,
  sha256: null,
  card: CARD.path,
  files: [],
  camera_steps: [],
  ...over,
})
const atFilms: State = run(
  { type: 'cards', cards: [CARD] },
  { type: 'go', step: 'firmware' },
  { type: 'go', step: 'films' },
)

describe('the installer flow', () => {
  it('needs a card or the zip before it leaves the first step', () => {
    expect(run({ type: 'go', step: 'firmware' }).step).toBe('start')
    expect(run({ type: 'zip', zip: true }, { type: 'go', step: 'firmware' }).step).toBe('firmware')
    expect(run({ type: 'cards', cards: [CARD, { ...CARD, path: '/b' }] }).card).toBe('')
  })

  it('goes back two steps and forward again without doing them again', () => {
    const back = reduce(atFilms, { type: 'go', step: 'start' })
    expect(back.step).toBe('start')
    expect(reduce(back, { type: 'go', step: 'films' }).step).toBe('films')
  })

  it('does not skip a step that was never reached', () => {
    const atFirmware = run({ type: 'cards', cards: [CARD] }, { type: 'go', step: 'firmware' })
    expect(canGo(reduce(atFirmware, { type: 'go', step: 'start' }), 'films')).toBe(false)
    // Next goes on, but the timeline offers only steps the user has been on
    expect([canGo(atFirmware, 'films'), onTimeline(atFirmware, 'films')]).toEqual([true, false])
    expect(onTimeline(reduce(atFilms, { type: 'go', step: 'start' }), 'films')).toBe(true)
  })

  it('does not go forward once the card is gone', () => {
    const back = reduce(reduce(atFilms, { type: 'go', step: 'start' }), { type: 'cards', cards: [] })
    expect(reduce(back, { type: 'go', step: 'films' }).step).toBe('start')
  })

  it('has no film step for the original firmware', () => {
    const original = reduce(reduce(atFilms, { type: 'go', step: 'firmware' }), {
      type: 'firmware',
      firmware: 'original',
    })
    expect(canGo(original, 'films')).toBe(false)
  })

  it('stays on the progress page while a job runs, and goes back after it fails', () => {
    const building = reduce(atFilms, { type: 'make', custom: true })
    const running = reduce(building, { type: 'job', job: job({}) })
    expect(reduce(running, { type: 'go', step: 'films' }).step).toBe('build')
    const failed = reduce(running, { type: 'job', job: job({ done: true, error: 'The card is full.' }) })
    expect(failed.step).toBe('build')
    expect(reduce(failed, { type: 'go', step: 'films' }).step).toBe('films')
  })

  it('shows the camera steps when the job ends, and Start over keeps the choices', () => {
    const building = reduce({ ...atFilms, customizing: true }, { type: 'make', custom: true })
    const done = reduce(building, { type: 'job', job: job({ done: true }) })
    expect(done.step).toBe('install')
    expect(canGo(done, 'films')).toBe(false)
    const again = reduce(done, { type: 'restart' })
    expect([again.step, again.job, again.customizing, again.card]).toEqual(['start', null, false, CARD.path])
    expect(reduce(again, { type: 'go', step: 'films' }).step).toBe('films')
  })

  it('goes back to the first step when the server refuses the job', () => {
    const refused = reduce(reduce(atFilms, { type: 'make', custom: false }), {
      type: 'refused',
      problem: 'Put the SD card back in this computer, then select Refresh.',
    })
    expect([refused.step, refused.problem]).toEqual([
      'start',
      'Put the SD card back in this computer, then select Refresh.',
    ])
  })

  it('keeps the broken-stabilizer option only with the EPM2Mod firmware', () => {
    const on = reduce(atFilms, { type: 'noStabilizer', on: true })
    expect(initial.noStabilizer).toBe(false)
    expect(on.noStabilizer).toBe(true)
    expect(reduce(on, { type: 'go', step: 'firmware' }).noStabilizer).toBe(true)
    expect(reduce(on, { type: 'firmware', firmware: 'epm2mod' }).noStabilizer).toBe(true)
    const films = reduce(on, { type: 'firmware', firmware: 'films' })
    expect(films.noStabilizer).toBe(false)
    expect(reduce(films, { type: 'noStabilizer', on: true }).noStabilizer).toBe(false)
    expect(reduce(on, { type: 'restart' }).noStabilizer).toBe(true)
  })
})
