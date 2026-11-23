import { expect, test } from '@playwright/test'

test('every page loads from its own URL', async ({ page }) => {
  for (const [path, heading] of [
    ['./', 'EPM2Mod'],
    ['./features', 'Features'],
    ['./films', 'Film Simulations'],
    ['./install', 'Install'],
  ] as const) {
    await page.goto(path)
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(heading)
  }
})

test('the film carousel shows a loaded photo and follows the arrow keys', async ({ page }) => {
  await page.goto('./films')
  const carousel = page.getByRole('region', { name: 'Film simulation comparison' })
  const photo = carousel.getByRole('img', { name: 'Scene 1 in Portra 400' })
  await expect(photo).toHaveJSProperty('complete', true)
  await expect(photo).not.toHaveJSProperty('naturalWidth', 0)
  await carousel.getByRole('button', { name: 'Portra 400', exact: true }).focus()
  await page.keyboard.press('ArrowRight')
  await page.keyboard.press('ArrowDown')
  await expect(carousel.getByRole('img', { name: 'Scene 2 in Ektachrome' })).toBeVisible()
})
