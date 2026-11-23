import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { choicesOf, lookFile, PRESET, presetSlots } from '@epm2mod/ui'
import App from './App'
import type { Job } from './api'

const BUILD = { name: 'card-looks-4', what: 'Film simulations', sha256: 'ab'.repeat(32) }
const DEFAULT = choicesOf(presetSlots())
const CARD = {
  path: '/media/u/CARD',
  name: 'CARD',
  size: 32e9,
  free: 31e9,
  label: 'CARD, 32.0 GB (31.0 GB free), /media/u/CARD',
}
const OTHER = { ...CARD, path: '/media/u/OTHER', name: 'OTHER', label: 'OTHER' }

async function sha256(bytes: Uint8Array): Promise<string> {
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes as BufferSource))
  return Array.from(digest, (b) => b.toString(16).padStart(2, '0')).join('')
}

interface MakeBody {
  firmware: string
  choices: string[]
  card: string | null
}

/** Camera steps as `epm2mod serve` sends them (cli/src/epm2mod/camera_steps.py), cut to the ones the tests read. */
function cameraSteps(body: MakeBody) {
  const films = body.choices.length > 0
  const first = body.choices[0]?.split('=')
  const art = first ? `${first[1] ?? ''} in ART ${(first[0] ?? '').slice(3)}.` : 'the art filters, such as Pop Art.'
  if (body.firmware === 'films')
    return [
      ...(body.card === null
        ? [{ id: 'copy', text: 'Copy EPM2LOOK.BIN from the zip to the top of the SD card.' }]
        : []),
      { id: 'eject', text: 'Eject the card (Mac: ⏏ in Finder. Windows: right-click → Eject) and take it out.' },
      { id: 'insert', text: 'Put the card in the camera and switch it on.' },
      { id: 'load-films', text: 'MENU → SETUP → gears tab → J → Load Looks → Load → OK.' },
      { id: 'check-art', text: `Check that MENU → ART shows ${art}` },
    ]
  return [
    ...(body.card === null
      ? [{ id: 'copy', text: `Copy DCOLYMP${films ? ' and EPM2LOOK.BIN' : ''} to the top of the SD card.` }]
      : []),
    { id: 'eject', text: 'Eject the card (Mac: ⏏ in Finder. Windows: right-click → Eject) and take it out.' },
    {
      id: 'flash',
      text: 'Hold OK (middle of the arrow pad) and ON/OFF together until the orange lamp on the front stays lit, then let go.',
    },
    ...(films ? [{ id: 'load-films', text: 'MENU → SETUP → gears tab → J → Load Looks → Load → OK.' }] : []),
    { id: 'check-art', text: `Check that MENU → ART shows ${art}` },
  ]
}

/** A fake `epm2mod serve`: it records the calls to /api/make and ends each job at once. */
function server(cards = [CARD]) {
  const made: unknown[] = []
  let job: Job | null = null
  const reply = (value: unknown) => Promise.resolve(new Response(JSON.stringify(value), { status: 200 }))
  vi.stubGlobal(
    'fetch',
    vi.fn((path: string, init?: RequestInit) => {
      expect(new Headers(init?.headers).get('X-EPM2-Token')).toBe('secret')
      if (path === '/api/build') return reply(BUILD)
      if (path === '/api/cards') return reply(cards)
      if (path === '/api/job') return reply(job)
      if (path === '/api/quit') return reply({ ok: true })
      if (path === '/api/make') {
        const body = JSON.parse(init?.body as string) as MakeBody
        made.push(body)
        const firmware = body.firmware as Job['firmware']
        const files = [
          ...(firmware === 'films' ? [] : ['DCOLYMP/E1019999.BIN']),
          ...(body.choices.length ? ['EPM2LOOK.BIN'] : []),
        ]
        const steps = { epm2mod: 5, original: 2, films: 1 }[firmware]
        job = {
          job: made.length,
          firmware,
          lines: ['1/5 stock firmware: ok'],
          step: steps,
          steps,
          done: true,
          error: null,
          sha256: BUILD.sha256,
          card: body.card,
          files,
          camera_steps: cameraSteps(body),
        }
        return reply(job)
      }
      return Promise.resolve(new Response('{"error":"no such call"}', { status: 404 }))
    }),
  )
  return made
}

beforeEach(() => {
  window.location.hash = '#token=secret'
})
afterEach(() => {
  vi.unstubAllGlobals()
})

async function next(user: ReturnType<typeof userEvent.setup>) {
  await waitFor(() => {
    expect(screen.getByRole('button', { name: 'Next' })).toBeEnabled()
  })
  await user.click(screen.getByRole('button', { name: 'Next' }))
}

describe('the local app', () => {
  it('writes EPM2Mod with the default films to the card', async () => {
    const made = server()
    const user = userEvent.setup()
    render(<App />)
    expect(screen.getByRole('heading', { name: 'Where to put the files' })).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: 'Card' })).toHaveValue(CARD.path)
    })
    await next(user)
    expect(screen.getByRole('radio', { name: 'EPM2Mod' })).toBeChecked()
    await next(user)
    expect(screen.getByRole('heading', { name: 'Film simulations' })).toBeInTheDocument()
    expect(screen.getByText(/derived from/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Use the default film simulations' }))
    expect(made).toEqual([{ firmware: 'epm2mod', choices: DEFAULT, card: CARD.path }])
    expect(await screen.findByRole('heading', { name: 'Install on the camera' })).toBeInTheDocument()
    const steps = screen.getByRole('list', { name: 'Install steps' })
    expect(steps).toHaveTextContent(
      'Hold OK (middle of the arrow pad) and ON/OFF together until the orange lamp on the front stays lit, then let go.',
    )
    expect(steps).toHaveTextContent('MENU → SETUP → gears tab → J → Load Looks → Load → OK.')
    expect(steps).toHaveTextContent('Check that MENU → ART shows portra-400 in ART 1.')
    expect(steps).not.toHaveTextContent('Copy')
    expect(screen.getByText(/do step 2 again/)).toBeInTheDocument()
    expect(screen.queryByText(/derived from/)).toBeNull()
    const close = vi.spyOn(window, 'close').mockImplementation(() => undefined)
    await user.click(screen.getByRole('button', { name: 'Close the installer' }))
    expect(await screen.findByRole('heading', { name: 'The installer is finished' })).toBeInTheDocument()
    expect(close).toHaveBeenCalledOnce()
  })

  it('writes only the film simulations, for a camera that runs EPM2Mod', async () => {
    const made = server()
    const user = userEvent.setup()
    render(<App />)
    await next(user)
    await user.click(screen.getByRole('radio', { name: 'Film simulations only' }))
    expect(screen.getByRole('navigation', { name: 'Steps' })).toHaveTextContent('Load')
    await user.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByRole('heading', { name: 'Choose the film simulations' })).toBeInTheDocument()
    expect(screen.getByText('This list replaces the film simulations on the camera.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Remove Kodak Ektachrome 100 from ART 2' }))
    await user.click(screen.getByRole('button', { name: 'Add Fujifilm C200' }))
    await user.click(screen.getByRole('button', { name: 'Write to the card' }))
    await waitFor(() => {
      expect(made).toHaveLength(1)
    })
    const [first] = made as MakeBody[]
    expect([first?.firmware, first?.card, first?.choices[1]]).toEqual(['films', CARD.path, 'ART2=c200'])
    expect(await screen.findByRole('heading', { name: 'Load on the camera' })).toBeInTheDocument()
    expect(screen.getByText('The film simulations are on the SD card CARD.')).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Install steps' })).toHaveTextContent('Load Looks → Load → OK.')
    expect(screen.getByText(/If there is no Load Looks row, install EPM2Mod first./)).toBeInTheDocument()
    expect(screen.queryByText(/do step/)).toBeNull()
    await user.click(screen.getByRole('button', { name: 'Start over' }))
    await next(user)
    await next(user)
    await user.click(screen.getByRole('button', { name: 'Back' }))
    expect(screen.getByRole('heading', { name: 'Choose what to install' })).toBeInTheDocument()
  })

  it('restores the original firmware without the film step', async () => {
    const made = server()
    const user = userEvent.setup()
    render(<App />)
    await next(user)
    await user.click(screen.getByRole('radio', { name: 'Olympus original' }))
    expect(screen.getByRole('navigation', { name: 'Steps' })).not.toHaveTextContent('Film simulations')
    await user.click(screen.getByRole('button', { name: 'Next' }))
    expect(made).toEqual([{ firmware: 'original', choices: [], card: CARD.path }])
    expect(await screen.findByRole('heading', { name: 'Install on the camera' })).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Install steps' })).toHaveTextContent('such as Pop Art')
  })

  it('keeps its default film simulations: the look file of the repository tool', async () => {
    expect(PRESET).toHaveLength(12)
    expect(await sha256(lookFile(presetSlots()))).toBe(
      'f0e433aed9ca93a143582aa06decf57b6c172a8ac6ed77b2da9f92669d3b93e4',
    )
  })

  it('chooses a card only when one card is plugged in', async () => {
    const made = server([CARD, OTHER])
    const user = userEvent.setup()
    render(<App />)
    const select = await screen.findByRole('combobox', { name: 'Card' })
    expect(select).toHaveValue('')
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
    await user.selectOptions(select, OTHER.path)
    await next(user)
    await next(user)
    await user.click(screen.getByRole('button', { name: 'Use the default film simulations' }))
    expect(made).toEqual([{ firmware: 'epm2mod', choices: DEFAULT, card: OTHER.path }])
  })

  it('asks for a card when none is plugged in', async () => {
    server([])
    render(<App />)
    expect(await screen.findByText(/Insert the camera's SD card./)).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
    })
  })

  it('writes the default films when the customized films are left as they are', async () => {
    const made = server()
    const user = userEvent.setup()
    render(<App />)
    await next(user)
    await next(user)
    await user.click(screen.getByRole('button', { name: 'Customize' }))
    expect(screen.getByText(/12 of 12 film simulations/)).toBeInTheDocument()
    expect(screen.getByText('The menu is full. Remove a film simulation (×) to add one.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Write to the card' }))
    await waitFor(() => {
      expect(made).toEqual([{ firmware: 'epm2mod', choices: DEFAULT, card: CARD.path }])
    })
  })

  it('customizes the films and gives a zip', async () => {
    const made = server([])
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('radio', { name: /Download a zip/ }))
    await next(user)
    await next(user)
    await user.click(screen.getByRole('button', { name: 'Customize' }))
    await user.click(screen.getByRole('button', { name: 'Remove Kodak Ektachrome 100 from ART 2' }))
    expect(screen.getByText(/11 of 12 film simulations/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Add Fujifilm C200' }))
    await user.click(screen.getByRole('button', { name: 'Make the zip' }))
    await waitFor(() => {
      expect(made).toHaveLength(1)
    })
    const [first] = made as { choices: string[]; card: null }[]
    expect(first?.card).toBeNull()
    expect(first?.choices.slice(0, 3)).toEqual(['ART1=portra-400', 'ART2=c200', 'ART3=pro-400h'])
    expect(await screen.findByRole('button', { name: 'Download EPM2Mod-card.zip' })).toBeInTheDocument()
    const steps = screen.getByRole('list', { name: 'Install steps' })
    expect(steps).toHaveTextContent('Copy DCOLYMP and EPM2LOOK.BIN to the top of the SD card.')
    expect(steps).toHaveTextContent('MENU → SETUP → gears tab → J → Load Looks → Load → OK.')
    expect(screen.getByText(/do step 3 again/)).toBeInTheDocument()
  })
})
