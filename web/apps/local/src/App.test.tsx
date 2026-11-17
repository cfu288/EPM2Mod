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
      if (path === '/api/make') {
        const body = JSON.parse(init?.body as string) as { choices: string[]; card: string | null }
        made.push(body)
        const files = ['DCOLYMP/E1019999.BIN', ...(body.choices.length ? ['EPM2LOOK.BIN'] : [])]
        job = {
          job: made.length,
          lines: ['1/5 stock firmware: ok'],
          step: 5,
          steps: 5,
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

describe('the local app', () => {
  it('makes the firmware alone onto the card that is plugged in', async () => {
    const made = server()
    const user = userEvent.setup()
    render(<App />)
    expect(await screen.findByText(/card-looks-4/)).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: 'Write to' })).toHaveValue(CARD.path)
    })
    await user.click(screen.getByRole('button', { name: 'Build custom firmware' }))
    expect(made).toEqual([{ choices: [], card: CARD.path }])
    const steps = await screen.findByRole('region', { name: 'Update the camera' })
    expect(steps).toHaveTextContent('Camera off: hold OK and switch it on.')
    expect(steps).not.toHaveTextContent('Load Looks')
    expect(steps).not.toHaveTextContent('from the zip')
  })

  it('adds the chosen films and gives a zip', async () => {
    const made = server([])
    const user = userEvent.setup()
    render(<App />)
    expect(await screen.findByRole('combobox', { name: 'Write to' })).toHaveValue('')
    await user.click(screen.getByRole('checkbox', { name: 'Customize the films in the ART menu' }))
    await user.click(screen.getByRole('button', { name: 'Remove Kodak Ektachrome 100 from ART 2' }))
    await user.click(screen.getByRole('button', { name: 'Add Fujifilm C200' }))
    await user.click(screen.getByRole('button', { name: 'Build custom firmware' }))
    await waitFor(() => {
      expect(made).toHaveLength(1)
    })
    const [first] = made as { choices: string[]; card: null }[]
    expect(first?.card).toBeNull()
    expect(first?.choices.slice(0, 3)).toEqual(['ART1=portra-400', 'ART2=c200', 'ART3=pro-400h'])
    expect(first?.choices).toHaveLength(12)
    expect(await screen.findByRole('button', { name: 'Download EPM2Mod-card.zip' })).toBeInTheDocument()
    const steps = screen.getByRole('region', { name: 'Update the camera' })
    expect(steps).toHaveTextContent('Copy DCOLYMP and EPM2LOOK.BIN from the zip to the card.')
    expect(steps).toHaveTextContent('MENU → Custom Menu → J → Load Looks → Load.')
  })
})
