import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

const nav = () => screen.getByRole('navigation', { name: 'Main' })
const carousel = () => screen.getByRole('region', { name: 'Film simulation comparison' })
const pressed = (group: string) =>
  within(within(carousel()).getByRole('group', { name: group })).getByRole('button', { pressed: true })

beforeEach(() => {
  window.history.replaceState(null, '', import.meta.env.BASE_URL)
  window.scrollTo = () => undefined
})

describe('App', () => {
  it('starts on the home page with the seven camera features', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('EPM2Mod')
    expect(within(screen.getByRole('region', { name: 'Features' })).getAllByRole('listitem')).toHaveLength(7)
    expect(within(nav()).getByRole('link', { name: /GitHub/ })).toHaveAttribute(
      'href',
      'https://github.com/cfu288/EPM2Mod',
    )
  })

  it('goes to each page from the menu', async () => {
    const user = userEvent.setup()
    render(<App />)
    for (const [name, path] of [
      ['Features', 'features'],
      ['Film Simulations', 'films'],
      ['Install', 'install'],
    ] as const) {
      await user.click(within(nav()).getByRole('link', { name }))
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(name)
      expect(within(nav()).getByRole('link', { name })).toHaveAttribute('aria-current', 'page')
      expect(window.location.pathname).toBe(`${import.meta.env.BASE_URL}${path}`)
    }
  })
})

describe('Films', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', `${import.meta.env.BASE_URL}films`)
  })

  it('changes the film with left and right, the scene with up and down', async () => {
    const user = userEvent.setup()
    render(<App />)
    expect(pressed('Film simulation')).toHaveTextContent('Portra 400')
    expect(pressed('Scene')).toHaveAccessibleName('Scene 1')

    pressed('Film simulation').focus()
    await user.keyboard('{ArrowRight}')
    expect(pressed('Film simulation')).toHaveTextContent('Ektachrome')
    await user.keyboard('{ArrowLeft}{ArrowLeft}')
    expect(pressed('Film simulation')).toHaveTextContent('Natural')
    await user.keyboard('{ArrowDown}')
    expect(pressed('Scene')).toHaveAccessibleName('Scene 2')
    await user.keyboard('{ArrowUp}{ArrowUp}')
    expect(pressed('Scene')).toHaveAccessibleName('Scene 9')
  })

  it('likes a film simulation, marks its button and keeps it after a reload', async () => {
    const user = userEvent.setup()
    localStorage.clear()
    const { unmount } = render(<App />)
    const filmButton = () =>
      within(within(carousel()).getByRole('group', { name: 'Film simulation' })).getByRole('button', {
        name: /Portra 400/,
      })
    expect(filmButton()).not.toHaveTextContent('liked')
    await user.click(within(carousel()).getByRole('button', { name: 'Like Portra 400' }))
    expect(within(carousel()).getByRole('button', { name: 'Like Portra 400' })).toHaveAttribute('aria-pressed', 'true')
    expect(filmButton()).toHaveTextContent('liked')

    await user.keyboard('l')
    expect(filmButton()).not.toHaveTextContent('liked')
    await user.keyboard('l')
    expect(filmButton()).toHaveTextContent('liked')

    unmount()
    render(<App />)
    expect(filmButton()).toHaveTextContent('liked')
    await user.click(within(carousel()).getByRole('button', { name: 'Like Portra 400' }))
    expect(filmButton()).not.toHaveTextContent('liked')
    localStorage.clear()
  })

  it('puts a liked film simulation first in the look pack and downloads it', async () => {
    const user = userEvent.setup()
    localStorage.clear()
    const saved: Blob[] = []
    URL.createObjectURL = (blob: Blob) => {
      saved.push(blob)
      return 'blob:pack'
    }
    URL.revokeObjectURL = () => undefined
    render(<App />)
    const pack = () => screen.getByRole('region', { name: 'Create a Look Pack' })
    expect(within(pack()).queryByRole('button', { name: /^Move ART/ })).toBeNull()
    await user.click(within(pack()).getByRole('button', { name: 'Choose film simulations' }))
    expect(await within(pack()).findByRole('button', { name: /^Move ART 1,/ })).toHaveAccessibleName(
      'Move ART 1, Kodak Portra 400',
    )

    await user.click(within(carousel()).getByRole('button', { name: 'Ektar 100' }))
    await user.click(within(carousel()).getByRole('button', { name: 'Like Ektar 100' }))
    expect(await within(pack()).findByRole('button', { name: /^Move ART 1,/ })).toHaveAccessibleName(
      'Move ART 1, Kodak Ektar 100',
    )
    expect(within(pack()).getAllByText(', liked')).toHaveLength(1)

    await user.click(within(pack()).getByRole('button', { name: 'Download EPM2LOOK.BIN' }))
    expect(saved).toHaveLength(1)
    localStorage.clear()
  })

  it('shows the installer first and the command line on a click', async () => {
    const user = userEvent.setup()
    window.history.replaceState(null, '', `${import.meta.env.BASE_URL}install`)
    render(<App />)
    expect(screen.getByRole('tab', { name: 'Installer' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.queryByText(/git clone/)).not.toBeInTheDocument()
    await user.click(screen.getByRole('tab', { name: 'Command line' }))
    expect(screen.getByText(/git clone/)).toBeInTheDocument()
    expect(screen.getByText(/epm2mod restore/)).toBeInTheDocument()
    expect(window.location.hash).toBe('#command-line')
  })

  it('lists all 32 film simulations in the look pack: 12 in the ART menu, the rest to add', async () => {
    render(<App />)
    const pack = screen.getByRole('region', { name: 'Create a Look Pack' })
    await userEvent.click(within(pack).getByRole('button', { name: 'Choose film simulations' }))
    expect(await within(pack).findAllByRole('button', { name: /^Move ART/ })).toHaveLength(12)
    expect(within(pack).getAllByRole('button', { name: /^Add / })).toHaveLength(20)
  })
})
