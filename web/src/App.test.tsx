import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

const menu = () => screen.getByRole('region', { name: "Your camera's ART menu" })
const more = () => screen.getByRole('region', { name: 'More films' })
const rows = () => within(menu()).getAllByRole('listitem')

describe('App', () => {
  it('shows the twelve ART places with the built-in films, in order', () => {
    render(<App />)
    expect(rows()).toHaveLength(12)
    expect(rows()[2]).toHaveTextContent('ART 3Fujifilm Pro 400H')
    expect(screen.getByRole('button', { name: 'Move ART 3, Fujifilm Pro 400H' })).toBeInTheDocument()
    expect(within(more()).getAllByRole('listitem')).toHaveLength(7)
    expect(within(more()).getByRole('button', { name: 'Add Kodak Ektar 100' })).toBeDisabled()
    expect(more()).toHaveTextContent('The menu holds 12 films.')
  })

  it('removes a film, adds another into the empty place and previews it', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Remove Kodak Ektachrome 100 from ART 2' }))
    expect(rows()[1]).toHaveTextContent('Empty')
    expect(rows()[1]).toHaveTextContent('Kodak Ektachrome 100')
    expect(more()).toHaveTextContent('Add puts a film into ART 2')
    expect(within(more()).getByRole('button', { name: 'Add Kodak Ektachrome 100' })).toBeEnabled()

    await user.click(within(more()).getByRole('button', { name: 'Add Fujifilm C200' }))
    expect(rows()[1]).toHaveTextContent('ART 2Fujifilm C200')
    expect(within(more()).queryByRole('button', { name: 'Add Fujifilm C200' })).toBeNull()
    expect(screen.getByRole('img')).toHaveAttribute('src', `${import.meta.env.BASE_URL}previews/c200/art2.png`)
  })

  it('previews the selected row', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Move ART 7, Fujifilm Velvia 100' }))
    expect(screen.getByRole('img')).toHaveAttribute('src', `${import.meta.env.BASE_URL}previews/velvia/art7.png`)
  })
})
