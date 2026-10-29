const {test, expect} = require('@playwright/test')

test.beforeEach(async ({page}) => {
  await page.route('https://tile.openstreetmap.org/**', route => route.fulfill({status: 200, contentType: 'image/png', body: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9sAAAAASUVORK5CYII=', 'base64')}))
})

test('renders actual Leaflet map and honest missing-data state', async ({page}) => {
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/')
  await expect(page.getByText('Real road data has not been loaded.')).toBeVisible()
  await expect(page.locator('.leaflet-container')).toBeVisible()
  await expect(page.getByRole('button', {name: 'Run A* →'})).toBeDisabled()
  await expect(page.getByRole('checkbox', {name: 'BFS'})).toBeChecked()
  await page.getByRole('checkbox', {name: 'BFS'}).uncheck()
  await expect(page.getByRole('checkbox', {name: 'BFS'})).not.toBeChecked()
  await page.getByText('Custom scenario studio').click()
  await page.getByRole('button', {name: 'Duplicate active'}).click()
  await expect(page.getByLabel('Name', {exact: true})).toHaveValue('Normal Day copy')
  await expect(page.getByLabel('Scenario traffic', {exact: true})).toHaveValue('0')
  await page.getByLabel('Scenario traffic', {exact: true}).selectOption('1')
  await expect(page.getByLabel('Scenario traffic', {exact: true})).toHaveValue('1')
  await page.screenshot({path: 'test-results/missing-data-desktop.png', fullPage: true})
  expect(errors).toEqual([])
})

test('remains usable at a narrow viewport', async ({page}) => {
  await page.setViewportSize({width: 390, height: 844})
  await page.goto('/')
  await expect(page.getByText('Real road data has not been loaded.')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({path: 'test-results/missing-data-mobile.png', fullPage: true})
})


test('does not send unavailable dataset requests while panning or attempting to search', async ({page}) => {
  const datasetRequests = []
  page.on('request', request => {if (/\/api\/(roads|places)(\?|$)/.test(request.url())) datasetRequests.push(request.url())})
  await page.goto('/')
  await expect(page.getByRole('region', {name: 'Dataset setup'})).toBeVisible()
  await expect(page.getByLabel('Start', {exact: true})).toBeDisabled()
  await expect(page.getByLabel('Destination', {exact: true})).toBeDisabled()
  await page.getByRole('button', {name: 'Zoom in', exact: true}).click()
  await page.getByRole('button', {name: 'Zoom out', exact: true}).click()
  await page.getByRole('button', {name: 'Check dataset status'}).click()
  await expect(page.getByText('Road layers unavailable until the dataset is loaded')).toBeVisible()
  await page.screenshot({path: 'test-results/dataset-recovery.png', fullPage: true})
  expect(datasetRequests).toEqual([])
  const icon = await page.request.get('/favicon.svg')
  expect(icon.ok()).toBe(true)
  expect(icon.headers()['content-type']).toContain('image/svg+xml')
})
