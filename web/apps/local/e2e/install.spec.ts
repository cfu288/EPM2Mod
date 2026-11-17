import { expect, test, type Page } from '@playwright/test'

const CARD = {
  path: '/media/u/CARD',
  name: 'CARD',
  size: 32e9,
  free: 31e9,
  label: 'CARD, 32.0 GB (31.0 GB free), /media/u/CARD',
}

/** Answer the calls of `epm2mod serve`; a job ends at its second poll. Returns the bodies of /api/make. */
async function fakeServer(page: Page) {
  const made: { choices: string[]; card: string | null }[] = []
  let polls = 0
  const job = (done: boolean) => {
    const body = made.at(-1)
    return {
      job: made.length,
      lines: done ? ['1/5 stock firmware: ok', '5/5 card-looks-4'] : ['1/5 stock firmware: ok'],
      step: done ? 5 : 1,
      steps: 5,
      done,
      error: null,
      sha256: 'ab'.repeat(32),
      card: body?.card ?? null,
      files: ['DCOLYMP/E1019999.BIN', ...(body?.choices.length ? ['EPM2LOOK.BIN'] : [])],
    }
  }
  await page.route('/api/**', async (route) => {
    const request = route.request()
    expect(request.headers()['x-epm2-token']).toBe('t0k3n')
    const path = new URL(request.url()).pathname
    if (path === '/api/build')
      return route.fulfill({ json: { name: 'card-looks-4', what: 'Film simulations', sha256: null } })
    if (path === '/api/cards') return route.fulfill({ json: [CARD] })
    if (path === '/api/make') {
      made.push(request.postDataJSON() as { choices: string[]; card: string | null })
      polls = 0
      return route.fulfill({ status: 202, json: job(false) })
    }
    if (path === '/api/job') {
      polls += 1
      return route.fulfill({ json: job(polls >= 2) })
    }
    if (path === '/api/zip') return route.fulfill({ body: 'PK', contentType: 'application/zip' })
    return route.fulfill({ status: 404, json: { error: 'no such call' } })
  })
  return made
}

test('writes the firmware to the card and shows the progress', async ({ page }) => {
  const made = await fakeServer(page)
  await page.goto('/#token=t0k3n')
  await expect(page.getByRole('combobox', { name: 'SD card' })).toHaveValue(CARD.path)
  await page.getByRole('button', { name: 'Make firmware' }).click()
  await expect(page.getByRole('button', { name: 'Making the firmware…' })).toBeDisabled()
  await expect(page.getByText('Done: the files are on the card.')).toBeVisible()
  const progress = page.getByRole('region', { name: 'Progress' })
  await expect(progress.getByRole('listitem').filter({ hasText: 'Write the files' })).toHaveText('✓ Write the files')
  await progress.getByText('Details').click()
  await expect(progress.getByText('5/5 card-looks-4')).toBeVisible()
  expect(made).toEqual([{ choices: [], card: CARD.path }])
})

test('adds film looks and downloads the zip', async ({ page }) => {
  const made = await fakeServer(page)
  await page.goto('/#token=t0k3n')
  await page.getByRole('radio', { name: /Download a zip/ }).check()
  await page.getByRole('checkbox', { name: 'Choose the films in the ART menu' }).check()
  await expect(page.getByRole('img', { name: /ART 1, Portra 400, selected/ })).toBeVisible()
  await page.getByRole('button', { name: 'Make firmware' }).click()
  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Download EPM2Mod-card.zip' }).click()
  expect((await download).suggestedFilename()).toBe('EPM2Mod-card.zip')
  expect(made[0]?.choices).toHaveLength(12)
  await expect(page.getByRole('region', { name: 'Update the camera' })).toContainText('Then load your films')
})
