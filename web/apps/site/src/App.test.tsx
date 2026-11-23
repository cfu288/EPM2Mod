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
  it('starts on the home page with the five camera features', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('EPM2Mod')
    expect(within(screen.getByRole('region', { name: 'Features' })).getAllByRole('listitem')).toHaveLength(5)
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

  it('has no ART-menu editor or look-file download', () => {
    render(<App />)
    expect(screen.queryByText(/EPM2LOOK/)).toBeNull()
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

    unmount()
    render(<App />)
    expect(filmButton()).toHaveTextContent('liked')
    await user.click(within(carousel()).getByRole('button', { name: 'Like Portra 400' }))
    expect(filmButton()).not.toHaveTextContent('liked')
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

  it('lists all 32 film simulations', () => {
    render(<App />)
    expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(33)
  })
})
