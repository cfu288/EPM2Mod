// The installer's screens and every move between them, as one reducer: the page only renders the state and sends
// actions. Side effects (the server calls) stay in App.
import type { Card, Firmware, Job } from './api'

export type StepId = 'start' | 'firmware' | 'films' | 'build' | 'install'

/** The steps of each choice of firmware: Olympus's own has no film looks. */
export const FLOWS: Record<Firmware, StepId[]> = {
  epm2mod: ['start', 'firmware', 'films', 'build', 'install'],
  original: ['start', 'firmware', 'build', 'install'],
  films: ['start', 'firmware', 'films', 'build', 'install'],
}

const LABELS: Record<StepId, string> = {
  start: 'Start',
  firmware: 'Firmware',
  films: 'Film simulations',
  build: 'Build',
  install: 'Install',
}
/** The film file alone is written and loaded, not built and installed. */
const FILM_LABELS: Partial<Record<StepId, string>> = { build: 'Write', install: 'Load' }

export const labels = (firmware: Firmware) =>
  FLOWS[firmware].map((id) => (firmware === 'films' ? FILM_LABELS[id] : undefined) ?? LABELS[id])

/** The steps the user chooses on, in order; the build and install steps come only from a job. */
const CHOICE_STEPS: StepId[] = ['start', 'firmware', 'films']

export interface State {
  step: StepId
  /** The furthest of CHOICE_STEPS reached: the timeline goes back and forward to any step up to it. */
  reached: number
  firmware: Firmware
  zip: boolean
  /** The chosen card's path, '' for none. */
  card: string
  /** The film editor is open instead of the film step's first page. */
  customizing: boolean
  /** The last job used the edited film simulations, for Try again. */
  lastCustom: boolean
  job: Job | null
  problem: string | null
  finished: boolean
}

export type Action =
  | { type: 'zip'; zip: boolean }
  | { type: 'card'; card: string }
  | { type: 'cards'; cards: Card[] }
  | { type: 'firmware'; firmware: Firmware }
  | { type: 'go'; step: StepId }
  | { type: 'customize'; on: boolean }
  | { type: 'make'; custom: boolean }
  | { type: 'job'; job: Job | null }
  | { type: 'refused'; problem: string }
  | { type: 'problem'; problem: string | null }
  | { type: 'restart' }
  | { type: 'finished' }

export const initial: State = {
  step: 'start',
  reached: 0,
  firmware: 'epm2mod',
  zip: false,
  card: '',
  customizing: false,
  lastCustom: false,
  job: null,
  problem: null,
  finished: false,
}

/** The first step is done: there is a card, or the user wants a zip. */
export const startReady = (state: State) => state.zip || state.card !== ''

/** Whether the user can go to a step now (Next, Back, or the timeline). */
export function canGo(state: State, step: StepId): boolean {
  const target = CHOICE_STEPS.indexOf(step)
  if (target < 0 || step === state.step || !FLOWS[state.firmware].includes(step)) return false
  // while a job runs, or after it made the files, the way back is Start over; a failed job can go back
  if (state.step === 'build' && state.job?.error == null) return false
  if (state.step === 'install') return false
  const flow = FLOWS[state.firmware]
  if (target > state.reached && flow[flow.indexOf(state.step) + 1] !== step) return false
  return target === 0 || startReady(state)
}

/** Whether the timeline offers a step: one the user can go to and has been on before. */
export const onTimeline = (state: State, step: StepId) =>
  canGo(state, step) && CHOICE_STEPS.indexOf(step) <= state.reached

export function reduce(state: State, action: Action): State {
  switch (action.type) {
    case 'zip':
      return { ...state, zip: action.zip }
    case 'card':
      return { ...state, card: action.card }
    case 'cards': {
      // a card is chosen for the user only when it is the only one
      const { cards } = action
      const card = cards.some((c) => c.path === state.card)
        ? state.card
        : cards.length === 1
          ? (cards[0]?.path ?? '')
          : ''
      return card === state.card ? state : { ...state, card }
    }
    case 'firmware':
      return { ...state, firmware: action.firmware }
    case 'go':
      if (!canGo(state, action.step)) return state
      return {
        ...state,
        step: action.step,
        reached: Math.max(state.reached, CHOICE_STEPS.indexOf(action.step)),
        problem: null,
      }
    case 'customize':
      return { ...state, customizing: action.on }
    case 'make':
      return { ...state, step: 'build', job: null, lastCustom: action.custom, problem: null }
    case 'job': {
      const { job } = action
      const made = job?.done === true && job.error === null
      return { ...state, job, step: made && state.step === 'build' ? 'install' : state.step }
    }
    case 'refused':
      return { ...state, step: 'start', problem: action.problem }
    case 'problem':
      return { ...state, problem: action.problem }
    case 'restart':
      return { ...state, step: 'start', job: null, customizing: false, problem: null }
    case 'finished':
      return { ...state, finished: true }
  }
}
