import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import type { Job } from './api'

const BUILD = { name: 'card-looks-4', what: 'Film simulations', sha256: 'ab'.repeat(32) }
const CARD = {
  path: '/media/u/CARD',
  name: 'CARD',
  size: 32e9,
  free: 31e9,
  label: 'CARD, 32.0 GB (31.0 GB free), /media/u/CARD',
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
        const body = JSON.parse(init?.body as string) as { firmware: string; choices: string[]; card: string | null }
        made.push(body)
        const files = ['DCOLYMP/E1019999.BIN', ...(body.choices.length ? ['EPM2LOOK.BIN'] : [])]
        job = {
          job: made.length,
          firmware: body.firmware as 'epm2mod',
          lines: ['1/5 stock firmware: ok'],
          step: body.firmware === 'original' ? 2 : 5,
          steps: body.firmware === 'original' ? 2 : 5,
          done: true,
          error: null,
          sha256: BUILD.sha256,
          card: body.card,
          files,
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
    expect(screen.getByRole('heading', { name: 'Install firmware' })).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: 'Card' })).toHaveValue(CARD.path)
    })
    await next(user)
    expect(screen.getByRole('radio', { name: 'EPM2Mod' })).toBeChecked()
    await next(user)
    expect(screen.getByRole('heading', { name: 'Film looks' })).toBeInTheDocument()
    expect(screen.getByText(/derived from/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Use the default films' }))
    expect(made).toEqual([{ firmware: 'epm2mod', choices: [], card: CARD.path }])
    expect(await screen.findByRole('heading', { name: 'Install on the camera' })).toBeInTheDocument()
    const steps = screen.getByRole('list', { name: 'Install steps' })
    expect(steps).toHaveTextContent(
      'Hold OK (middle of the arrow pad) and ON/OFF together until the orange lamp on the front stays lit, then let go.',
    )
    expect(steps).toHaveTextContent('Check: MENU → ART shows film names, such as Portra 400.')
    expect(steps).not.toHaveTextContent('Load Looks')
    expect(steps).not.toHaveTextContent('zip')
    expect(screen.queryByText(/derived from/)).toBeNull()
    await user.click(screen.getByRole('button', { name: 'Finish' }))
    expect(await screen.findByRole('heading', { name: 'EPM2Mod has stopped' })).toBeInTheDocument()
  })

  it('restores the original firmware without the film step', async () => {
    const made = server()
    const user = userEvent.setup()
    render(<App />)
    await next(user)
    await user.click(screen.getByRole('radio', { name: 'Olympus original' }))
    expect(screen.getByRole('navigation', { name: 'Steps' })).not.toHaveTextContent('Film looks')
    await user.click(screen.getByRole('button', { name: 'Next' }))
    expect(made).toEqual([{ firmware: 'original', choices: [], card: CARD.path }])
    expect(await screen.findByRole('heading', { name: 'Install on the camera' })).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Install steps' })).toHaveTextContent('such as Pop Art')
  })

  it('asks for a card when none is plugged in', async () => {
    server([])
    render(<App />)
    expect(await screen.findByText(/Insert the camera's SD card./)).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
    })
  })

  it('writes no look file when the customized films are left as they are', async () => {
    const made = server()
    const user = userEvent.setup()
    render(<App />)
    await next(user)
    await next(user)
    await user.click(screen.getByRole('button', { name: 'Customize' }))
    expect(screen.getByText(/12 of 12 films/)).toBeInTheDocument()
    expect(screen.getByText('The menu is full. Remove a film (×) to add one.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Write to the card' }))
    await waitFor(() => {
      expect(made).toEqual([{ firmware: 'epm2mod', choices: [], card: CARD.path }])
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
    expect(screen.getByText(/11 of 12 films/)).toBeInTheDocument()
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
    expect(steps).toHaveTextContent('Copy DCOLYMP and EPM2LOOK.BIN from the zip to the top of the SD card.')
    expect(steps).toHaveTextContent('Check: MENU → ART shows C200 in ART 2.')
    expect(steps).toHaveTextContent('MENU → SETUP → gears tab → J → Load Looks → Load → OK.')
  })
})
