import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

describe('App', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/EPM2Mod/')
  })

  it('lists the twelve art filters with their built-in films and no download yet', () => {
    render(<App />)
    expect(within(screen.getByRole('region', { name: 'Art filters' })).getAllByRole('listitem')).toHaveLength(12)
    expect(screen.getByRole('button', { name: /^Film of ART 3\b/ })).toHaveTextContent('Fuji Pro 400H')
    expect(screen.getByRole('button', { name: /Download EPM2LOOK.BIN/ })).toBeDisabled()
  })

  it('changes a film, previews it, keeps it in the URL and allows the download', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: /^Film of ART 2\b/ }))
    await user.click(within(screen.getByRole('listbox')).getByText(/Fuji Velvia 100/))
    expect(screen.getByLabelText('Name on the camera', { selector: '#name-2' })).toHaveValue('Velvia')
    expect(window.location.search).toBe('?art2=velvia')
    expect(screen.getByRole('img')).toHaveAttribute('src', `${import.meta.env.BASE_URL}previews/velvia/art2.png`)
    expect(screen.getByRole('button', { name: /Download EPM2LOOK.BIN/ })).toBeEnabled()
  })

  it('refuses a name the camera cannot show', async () => {
    const user = userEvent.setup()
    render(<App />)
    const name = screen.getByLabelText('Name on the camera', { selector: '#name-1' })
    await user.clear(name)
    expect(name).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByRole('button', { name: /Download EPM2LOOK.BIN/ })).toBeDisabled()
  })

  it('reads choices from the URL', () => {
    window.history.replaceState(null, '', '/EPM2Mod/?art12=c200&name12=Fuji+C200')
    render(<App />)
    expect(screen.getByRole('button', { name: /^Film of ART 12\b/ })).toHaveTextContent('Fujifilm C200')
    expect(screen.getByLabelText('Name on the camera', { selector: '#name-12' })).toHaveValue('Fuji C200')
  })
})
