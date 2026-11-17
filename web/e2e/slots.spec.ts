import { expect, test, type Page } from '@playwright/test'

const row = (page: Page, art: number) =>
  page
    .getByRole('region', { name: "Your camera's ART menu" })
    .getByRole('listitem')
    .nth(art - 1)

/** The preview shows the strip of ART `art` with the name of `film`, and both images loaded. */
async function expectPreview(page: Page, art: number, film: string) {
  const layers = page.getByRole('img').locator('img')
  await expect(layers.nth(0)).toHaveAttribute('src', new RegExp(`previews/menu/art${String(art)}\\.png$`))
  await expect(layers.nth(1)).toHaveAttribute('src', new RegExp(`previews/name/${film}\\.png$`))
  for (const layer of await layers.all()) {
    await expect(layer).toHaveJSProperty('complete', true)
    await expect(layer).not.toHaveJSProperty('naturalWidth', 0)
  }
}

test('moves a film with the keyboard', async ({ page }) => {
  await page.goto('./')
  await page.getByRole('button', { name: 'Move ART 1, Kodak Portra 400' }).focus()
  // dnd-kit measures the rows a frame after pickup; wait for its announcement after each key.
  const status = page.getByRole('status').filter({ hasText: /./ })
  await page.keyboard.press('Space')
  await expect(status).toContainText('Kodak Portra 400 is over ART 1.')
  await page.keyboard.press('ArrowDown')
  await expect(status).toContainText('Kodak Portra 400 is over ART 2.')
  await page.keyboard.press('ArrowDown')
  await expect(status).toContainText('Kodak Portra 400 is over ART 3.')
  await page.keyboard.press('Space')
  await expect(row(page, 1)).toContainText('Kodak Ektachrome 100')
  await expect(row(page, 3)).toContainText('Kodak Portra 400')
  await expectPreview(page, 3, 'portra-400')
})

test('moves a film with the mouse', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 1400 })
  await page.goto('./')
  const handle = page.getByRole('button', { name: 'Move ART 12, Kodak Vision3 500T' })
  const target = row(page, 10)
  const from = await handle.boundingBox()
  const to = await target.boundingBox()
  if (!from || !to) throw new Error('no layout')
  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2)
  await page.mouse.down()
  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2 - 10, { steps: 4 })
  await page.waitForTimeout(100)
  await page.mouse.move(from.x + from.width / 2, to.y + to.height / 2, { steps: 12 })
  await page.waitForTimeout(100)
  await page.mouse.up()
  await expect(row(page, 10)).toContainText('Kodak Vision3 500T')
})

test('adds a film into the place of a removed one', async ({ page }) => {
  await page.goto('./')
  await page.getByRole('button', { name: 'Remove Kodak Gold 200 from ART 11' }).click()
  await page.getByRole('button', { name: 'Add Kodak Ektar 100' }).click()
  await expect(row(page, 11)).toContainText('Kodak Ektar 100')
  await expectPreview(page, 11, 'ektar-100')
})

test('downloads the look file of the slots', async ({ page }) => {
  await page.goto('./')
  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: /Download/ }).click()
  expect((await download).suggestedFilename()).toBe('EPM2LOOK.BIN')
})
