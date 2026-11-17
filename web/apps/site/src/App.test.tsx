import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

/** The picture of a preview layer, without the folder and the hash a build adds. */
const picture = (src: string | null) =>
  src
    ?.match(/(menu|name)\/([\w-]+?)(-[\w]{8})?\.png$/)
    ?.slice(1, 3)
    .join('/')

const menu = () => screen.getByRole('region', { name: "Your camera's ART menu" })
const more = () => screen.getByRole('region', { name: 'More films' })
/** The preview's two layers: the strip of the ART position and the film's name over it. */
const layers = () => [...screen.getByRole('img').querySelectorAll('img')].map((img) => picture(img.getAttribute('src')))
const rows = () => within(menu()).getAllByRole('listitem')

describe('App', () => {
  it('shows the twelve ART places with the built-in films, in order', () => {
    render(<App />)
    expect(rows()).toHaveLength(12)
    expect(rows()[2]).toHaveTextContent('ART 3Fujifilm Pro 400H')
    expect(screen.getByRole('button', { name: 'Move ART 3, Fujifilm Pro 400H' })).toBeInTheDocument()
    expect(within(more()).getAllByRole('listitem')).toHaveLength(7)
    expect(within(more()).getByRole('button', { name: 'Add Kodak Ektar 100' })).toBeDisabled()
    expect(more()).toHaveTextContent('The menu is full. Remove a film (×) to add one.')
    expect(menu()).toHaveTextContent('12 of 12 films')
  })

  it('removes a film, adds another into the empty place and previews it', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Remove Kodak Ektachrome 100 from ART 2' }))
    expect(rows()[1]).toHaveTextContent('Empty')
    expect(rows()[1]).toHaveTextContent('Kodak Ektachrome 100')
    expect(more()).not.toHaveTextContent('Remove a film')
    expect(within(more()).getByRole('button', { name: 'Add Kodak Ektachrome 100' })).toBeEnabled()

    await user.click(within(more()).getByRole('button', { name: 'Add Fujifilm C200' }))
    expect(rows()[1]).toHaveTextContent('ART 2Fujifilm C200')
    expect(within(more()).queryByRole('button', { name: 'Add Fujifilm C200' })).toBeNull()
    expect(layers()).toEqual(['menu/art2', 'name/c200'])
    expect(screen.getByRole('img')).toHaveAccessibleName("The camera's ART menu with ART 2, C200, selected")
  })

  it('previews the selected row', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Move ART 7, Fujifilm Velvia 100' }))
    expect(layers()).toEqual(['menu/art7', 'name/velvia'])
  })
})
